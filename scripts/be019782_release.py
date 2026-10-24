"""Clear only obsolete main Pages runs before a fully guarded recovery release.

Never cancels a PR check, research workflow, feature-branch run, or a publisher
containing the validated original-response replay commit. Requires an explicit
flag and the recovery job's scoped GITHUB_TOKEN. No match/source data is read or
written. A read/permission/ancestry/cancellation uncertainty fails closed. After a normal
cancellation grace, the documented force endpoint may stop an always()-immune
strict ancestor only after its unchanged identity and ancestry are re-proven.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

CORE_COMMIT = '275771bd0470c2a0ed38b00720f18ca353050e74'
ACTIVE = ('queued', 'in_progress', 'pending', 'waiting', 'requested')
EVENTS = {'push', 'schedule', 'workflow_dispatch', 'repository_dispatch'}


class APIError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def gh_api(repo, path, method='GET'):
    result = subprocess.run(
        ['gh', 'api', '--method', method, f'repos/{repo}/{path}'],
        text=True, capture_output=True, timeout=45)
    if result.returncode:
        message = result.stderr.strip()[-700:]
        status = re.search(r'HTTP (\d{3})', message)
        raise APIError(message, int(status[1]) if status else None)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def active_publishers(api):
    found = {}
    for status in ACTIVE:
        for page in range(1, 11):
            payload = api('actions/workflows/pages.yml/runs?branch=main&status='
                          + status + f'&per_page=100&page={page}')
            rows = payload.get('workflow_runs') if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise RuntimeError('Publisher list is not a verified response')
            for row in rows:
                if not isinstance(row, dict):
                    raise RuntimeError('Publisher record is not an object')
                route = row.get('path') or '.github/workflows/pages.yml'
                if not isinstance(route, str):
                    raise RuntimeError('Publisher route is unverified')
                if (row.get('head_branch') != 'main' or row.get('status') not in ACTIVE
                        or row.get('event') not in EVENTS
                        or route.split('@')[0]
                        != '.github/workflows/pages.yml'):
                    continue
                run_id, sha = row.get('id'), row.get('head_sha')
                if (isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0
                        or not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}', sha)):
                    raise RuntimeError('Unverifiable publisher id/commit; nothing may be guessed')
                found[run_id] = row
            if len(rows) < 100:
                break
        else:
            raise RuntimeError('Publisher pagination is incomplete')
    return list(found.values())


def retire_obsolete(api, current_sha, current_run, *, timeout=90, force_timeout=90,
                    clock=time.monotonic, sleep=time.sleep, report=None):
    def progress(event, **fields):
        if report:
            report(dict(event=event, **fields))
        else:
            print(json.dumps(dict(event=event, **fields)), flush=True)

    def await_completion(pending, seconds):
        pending = set(pending)
        deadline = clock() + seconds
        while pending:
            for run_id in list(pending):
                status = api(f'actions/runs/{run_id}').get('status')
                if status == 'completed':
                    pending.remove(run_id)
                    progress('confirmed_completed', run_id=run_id)
                elif status not in ACTIVE:
                    raise RuntimeError('Cancellation completion is unverified')
            if pending:
                if clock() >= deadline:
                    break
                sleep(3)
        return pending

    if not re.fullmatch(r'[0-9a-f]{40}', current_sha or ''):
        raise RuntimeError('Current release commit is missing')
    if api(f'compare/{CORE_COMMIT}...{current_sha}').get('status') not in ('ahead', 'identical'):
        raise RuntimeError('Recovery must contain the validated source-replay commit')
    candidates = active_publishers(api)
    relation, obsolete = {}, {}
    for row in candidates:
        if row['id'] == current_run:
            continue
        sha = row['head_sha']
        if sha not in relation:
            relation[sha] = api(f'compare/{CORE_COMMIT}...{sha}').get('status')
        if relation[sha] in ('ahead', 'identical'):
            continue
        if relation[sha] != 'behind':
            raise RuntimeError('Unknown/divergent publisher ancestry; no unsafe cancellation')
        obsolete[row['id']] = row

    # Prove the whole plan before making any cancellation request.
    progress('verified_plan', obsolete_ids=sorted(obsolete))
    for run_id in obsolete:
        try:
            api(f'actions/runs/{run_id}/cancel', method='POST')
            progress('normal_cancellation_requested', run_id=run_id)
        except RuntimeError as error:
            if api(f'actions/runs/{run_id}').get('status') == 'completed':
                continue
            # A state conflict is not a permission grant failure. Never escalate
            # 401/403/unknown failures; the documented force API needs the same
            # actions:write authorization and only handles unresponsive jobs.
            if not isinstance(error, APIError) or error.status != 409:
                raise
            progress('normal_cancellation_state_conflict', run_id=run_id)
    pending = await_completion(obsolete, timeout)
    for run_id in sorted(pending):
        latest = api(f'actions/runs/{run_id}')
        if latest.get('status') == 'completed':
            continue
        route = latest.get('path')
        if (latest.get('id') != run_id or latest.get('head_branch') != 'main'
                or latest.get('head_sha') != obsolete[run_id]['head_sha']
                or latest.get('event') not in EVENTS
                or not isinstance(route, str)
                or route.split('@')[0] != '.github/workflows/pages.yml'
                or latest.get('status') not in ACTIVE
                or api(f"compare/{CORE_COMMIT}...{latest['head_sha']}").get('status') != 'behind'):
            raise RuntimeError('Publisher identity/ancestry changed; force cancellation refused')
        # GitHub documents this endpoint specifically for normal cancellation
        # defeated by always(). This only follows a normal request + grace, and
        # never applies to any current-code, PR, research or feature-branch run.
        progress('force_cancellation_after_grace', run_id=run_id, sha=latest['head_sha'])
        try:
            api(f'actions/runs/{run_id}/force-cancel', method='POST')
        except RuntimeError:
            if api(f'actions/runs/{run_id}').get('status') != 'completed':
                raise
    if await_completion(pending, force_timeout):
        raise RuntimeError('Obsolete publisher has not stopped; recovery cannot publish')
    return list(obsolete)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clear-obsolete', action='store_true')
    args = parser.parse_args(argv)
    if not args.clear_obsolete:
        parser.error('Cancellation requires explicit --clear-obsolete in the recovery job')
    repo = os.environ.get('GH_REPO', '')
    run = os.environ.get('GITHUB_RUN_ID', '')
    if (not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo)
            or not run.isdigit() or int(run) <= 0):
        parser.error('Authenticated repository/run context is required')
    output = os.environ.get('GITHUB_OUTPUT')
    if not output:
        parser.error('Recovery output context is required before any cancellation')
    try:
        retired = retire_obsolete(lambda path, method='GET': gh_api(repo, path, method),
                                  os.environ.get('GITHUB_SHA', ''), int(run))
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print('::error::Recovery queue safety not established: ' + str(error), flush=True)
        return 1
    with Path(output).open('a') as handle:
        handle.write('safe=true\n')
    print(json.dumps({'core_commit': CORE_COMMIT, 'obsolete_main_publishers_stopped': retired,
                      'queue_safe': True}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
