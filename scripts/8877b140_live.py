"""Live deployment verification for session arena-8877b140 (read-only).

The sandbox egress allow-list exposes only the GitHub API, so the live site
itself (github.io) and workflow artifact/blob logs cannot be fetched here.
This script verifies the running system through the GitHub REST API instead:

* the recent ``pages.yml`` workflow runs and every job/step conclusion;
* the github-pages deployment records and the empirical deploy cadence
  against the project's 4-8 hour refresh requirement;
* the legacy Pages build history (push-triggered) and its error state;
* the scheduled cron declared in the publisher workflow.

It writes a JSON dossier plus a short Markdown summary into
``data/research/8877b140/``. It never mutates a workflow, a feed or the live
site, and it is not imported by the unit suite (no network in unit tests).

    python -m scripts.8877b140_live
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = 'buffedlizard55-lab/MaltaProj3'
OUT_DIR = Path('data/research/8877b140')
MAX_DEPLOY_GAP_MIN = 8 * 60  # the brief's outer refresh bound


def gh_api(path: str):
    out = subprocess.run(['gh', 'api', f'repos/{REPO}/{path}'], check=True,
                         capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def main() -> int:
    now = datetime.now(timezone.utc)
    dossier: dict = {
        'session': 'arena-8877b140',
        'verified_at': now.isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'read_only': True,
        'egress_note': 'Sandbox allows api.github.com only; github.io pages and action artifact/blob downloads are not reachable, so live evidence is the GitHub API record plus the runner-internal verification steps whose conclusions are visible here.',
        'evidence': {},
        'checks': [],
    }

    def check(name: str, ok: bool, detail: dict):
        dossier['checks'].append({'check': name, 'ok': bool(ok), 'detail': detail})

    # 1. Recent publisher runs ------------------------------------------------
    runs = gh_api('actions/workflows/pages.yml/runs?per_page=12')['workflow_runs']
    dossier['evidence']['pages_runs'] = [
        {'id': r['id'], 'status': r['status'], 'conclusion': r['conclusion'],
         'event': r['event'], 'head_sha': r['head_sha'][:7],
         'started_at': r['run_started_at'], 'updated_at': r['updated_at']}
        for r in runs]
    successes = [r for r in runs if r['conclusion'] == 'success']
    latest_success = successes[0] if successes else None
    check('a-pages-workflow-has-a-successful-run', latest_success is not None,
          {'latest_success_id': latest_success['id'] if latest_success else None,
           'runs_inspected': len(runs)})

    # 2. Every step of the latest successful run ------------------------------
    step_rows: list[dict] = []
    if latest_success:
        jobs = gh_api(f'actions/runs/{latest_success["id"]}/jobs')['jobs']
        all_green = True
        for job in jobs:
            for step in job['steps']:
                if step['conclusion'] not in ('success', 'skipped'):
                    all_green = False
                step_rows.append({'job': job['name'], 'name': step['name'],
                                  'conclusion': step['conclusion']})
        required_steps = ('Refresh all Hotspawn CS2 records and supported external lines',
                          'Reconcile every row, replay every probability and build linked pages',
                          'Verify the public site, its complete data and category pages')
        present = {s['name'] for s in step_rows}
        required_ok = all(any(s['name'] == name and s['conclusion'] == 'success'
                              for s in step_rows) for name in required_steps)
        dossier['evidence']['latest_success_steps'] = step_rows
        check('latest-success-run-steps-green-and-verified', all_green and required_ok,
              {'run_id': latest_success['id'], 'steps': len(step_rows),
               'required_verification_steps_present': required_ok})

    # 3. Deployment cadence ----------------------------------------------------
    deployments = gh_api('deployments?per_page=30')
    times = sorted(parse_ts(d['created_at']) for d in deployments)
    gaps_min = [round((times[i + 1] - times[i]).total_seconds() / 60, 1)
                for i in range(len(times) - 1)]
    dossier['evidence']['deployments'] = [
        {'id': d['id'], 'created_at': d['created_at'], 'sha': d['sha'][:7],
         'environment': d['environment']} for d in deployments]
    latest_deployment = deployments[0]
    statuses = gh_api(f'deployments/{latest_deployment["id"]}/statuses')
    state = statuses[0]['state'] if statuses else 'unknown'
    # A queued/in_progress deployment is a transient state, not a failure.
    in_flight = {'queued', 'in_progress', 'waiting', 'pending'}
    failure_states = {'failure', 'error', 'destroyed', 'inactive'}
    # The most recent deployment that actually reached success is the
    # confirmed live state, regardless of what is currently queued.
    latest_success_id = None
    for deployment in deployments:
        dep_statuses = gh_api(f'deployments/{deployment["id"]}/statuses')
        if dep_statuses and dep_statuses[0]['state'] == 'success':
            latest_success_id = deployment['id']
            break
    over_bound = [g for g in gaps_min if g > MAX_DEPLOY_GAP_MIN]
    check('deployment-cadence-within-8-hours', not over_bound,
          {'deployments': len(times), 'span': f'{times[0].isoformat()} .. {times[-1].isoformat()}',
           'gap_minutes': {'min': min(gaps_min), 'median': sorted(gaps_min)[len(gaps_min) // 2],
                           'max': max(gaps_min)}, 'gaps_over_8h': over_bound})
    check('latest-deployment-not-failed', state not in failure_states,
          {'deployment_id': latest_deployment['id'], 'state': state,
           'sha': latest_deployment['sha'][:7], 'created_at': latest_deployment['created_at'],
           'in_flight': state in in_flight,
           'latest_confirmed_success_deployment_id': latest_success_id})

    # 4. Legacy Pages builds ---------------------------------------------------
    builds = gh_api('pages/builds?per_page=10')
    dossier['evidence']['legacy_pages_builds'] = [
        {'created_at': b['created_at'], 'status': b['status'],
         'error': (b.get('error') or {}).get('message')} for b in builds]
    check('latest-legacy-pages-build-not-broken', builds and builds[0]['status'] == 'built',
          {'latest': builds[0] if builds else None})

    # 5. Declared refresh schedule ---------------------------------------------
    workflow = Path('.github/workflows/pages.yml').read_text()
    crons = re.findall(r"cron:\s*'([^']+)'", workflow)
    four_hour_primary = any('*/4' in c for c in crons)
    check('publisher-declares-a-four-hour-schedule', four_hour_primary,
          {'cron': crons, 'requirement': 'refresh every 4-8 hours'})

    all_ok = all(c['ok'] for c in dossier['checks'])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'live-deployment-verification.json').write_text(
        json.dumps(dossier, indent=2, ensure_ascii=False) + '\n')

    lines = ['# Live deployment verification — arena-8877b140', '',
             f'- Verified at: {dossier["verified_at"]} (GitHub API only; see egress note)',
             f'- Overall: **{"PASS" if all_ok else "FAIL"}** ({sum(1 for c in dossier["checks"] if c["ok"])}/{len(dossier["checks"])} checks)', '']
    for c in dossier['checks']:
        lines.append(f'- {"PASS" if c["ok"] else "FAIL"} `{c["check"]}`')
    if latest_success:
        lines += ['', f'Latest successful publisher run: [{latest_success["id"]}]'
                  f'(https://github.com/{REPO}/actions/runs/{latest_success["id"]}) '
                  f'on `{latest_success["head_branch"]}` ({latest_success["event"]})',
                  f'Latest github-pages deployment: `{latest_deployment["id"]}` '
                  f'sha `{latest_deployment["sha"][:7]}` state `{state}` at {latest_deployment["created_at"]}.']
    (OUT_DIR / 'live-deployment-verification.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'all_ok': all_ok,
                      'checks': {c['check']: c['ok'] for c in dossier['checks']}}, indent=2))
    return 0 if all_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
