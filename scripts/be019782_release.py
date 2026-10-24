"""Clear only obsolete main Pages runs before a fully guarded recovery release.

Never cancels a PR check, research workflow, feature-branch run, or a publisher
containing the validated original-response replay commit. Requires an explicit
flag and the recovery job's scoped GITHUB_TOKEN. No match/source data is read or
written. A read/permission/ancestry/cancellation uncertainty fails closed.
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


def gh_api(repo, path, method='GET'):
    result = subprocess.run(
        ['gh', 'api', '--method', method, f'repos/{repo}/{path}'],
        text=True, capture_output=True, timeout=45)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[-700:])
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


def retire_obsolete(api, current_sha, current_run, *, timeout=90,
                    clock=time.monotonic, sleep=time.sleep):
    if not re.fullmatch(r'[0-9a-f]{40}', current_sha or ''):
        raise RuntimeError('Current release commit is missing')
    if api(f'compare/{CORE_COMMIT}...{current_sha}').get('status') not in ('ahead', 'identical'):
        raise RuntimeError('Recovery must contain the validated source-replay commit')
    candidates = active_publishers(api)
    relation, obsolete = {}, []
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
        obsolete.append(row['id'])

    # Prove the whole plan before making any cancellation request.
    for run_id in obsolete:
        try:
            api(f'actions/runs/{run_id}/cancel', method='POST')
        except RuntimeError:
            if api(f'actions/runs/{run_id}').get('status') != 'completed':
                raise
    pending = set(obsolete)
    deadline = clock() + timeout
    while pending:
        for run_id in list(pending):
            status = api(f'actions/runs/{run_id}').get('status')
            if status == 'completed':
                pending.remove(run_id)
            elif status not in ACTIVE:
                raise RuntimeError('Cancellation completion is unverified')
        if pending:
            if clock() >= deadline:
                raise RuntimeError('Obsolete publisher has not stopped; recovery cannot publish')
            sleep(3)
    return obsolete


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
