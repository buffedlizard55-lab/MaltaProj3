"""Coverage watchdog: ask the verified publisher to run when Hotspawn lists a card we do not carry.

Why this exists (session arena-24e4d653)
----------------------------------------
The four-hour publisher is correct, but it is a *four-hour* publisher: Hotspawn
adds pick'em cards in batches between publishes. Measured first-hand on
2026-10-26T00:48Z-01:05Z, the live lobby exposed **81** CS2 cards while the
deployed snapshot `2026-10-25T23:03:48Z` carried **72** -- nine playable cards
(NODWIN Clutch Series #13 x4, CCT Europe 2026 Series #12 x5) had no row, no
probability and no pick on the site for up to four hours. Dossier:
`data/research/24e4d653/live-coverage.json`.

The freshness watchdog only reacts to *age* (snapshot older than six hours), so
it cannot see this: a ten-minute-old snapshot can still be missing nine cards.
This watchdog compares the live Hotspawn CS2 scheduled-fixture feed with the
deployed snapshot and dispatches `pages.yml` -- the same fully verified
publisher, which collects, originates, builds, audits and deploys -- as soon as a
live, still-upcoming fixture has no row in the published data.

What it deliberately does not do
--------------------------------
* It never publishes, never commits and never writes a probability, a pick or an
  alias. It has no credentials beyond the workflow's own `GITHUB_TOKEN`.
* It never dispatches while a publish is queued or running, and it stays quiet
  for `--min-run-age-minutes` after any `pages.yml` run started, so a dispatcher
  loop cannot starve the real publisher.
* If either surface is unreadable it says so and does nothing: an unreadable
  feed is not evidence of a gap, and it is not evidence of coverage either.

Usage
-----
    python -m scripts.24e4d653_coverage_watch --decide        # print the decision
    python -m scripts.24e4d653_coverage_watch                  # decide + dispatch
    python -m scripts.24e4d653_coverage_watch --dry-run        # decide, never dispatch
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
SNAPSHOT_URL = 'https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json'
LOBBY_URL = 'https://play.hotspawn.com/lobby'
WORKFLOW = 'pages.yml'
#: A publish that started inside this window is still allowed to close the gap.
MIN_RUN_AGE_MINUTES = 20
#: A queued run younger than this really is going to start (older queued runs are
#: usually ones the push concurrency group will drop -- same rule as the
#: freshness watchdog).
QUEUED_GRACE_MINUTES = 15


def _iso(ms: Any) -> str | None:
    """Hotspawn's ``scheduled_start_time`` is epoch **milliseconds** as a string."""
    try:
        return datetime.fromtimestamp(int(str(ms)) / 1000, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def parse_fixtures(payload: Any) -> list[dict]:
    """Normalise the official fixture array. Never invents a start time."""
    rows: list[dict] = []
    if not isinstance(payload, list):
        return rows
    for record in payload:
        if not isinstance(record, dict) or record.get('sport_alias') not in (None, 'cs2'):
            continue
        identity = record.get('id')
        if identity is None:
            continue
        teams = [record.get('participants0_name'), record.get('participants1_name')]
        rows.append({
            'id': str(identity),
            'teams': [t for t in teams if t],
            'competition': record.get('competition_name'),
            'starts_at': _iso(record.get('scheduled_start_time')),
            'status': record.get('status'),
        })
    return rows


def future_fixtures(fixtures: Iterable[dict], now: datetime) -> list[dict]:
    """Fixtures whose published start is still ahead of ``now`` (ISO-8601, UTC).

    Only future starts matter: a card that already started can no longer carry a
    prematch pick, and the project never manufactures a retrospective one.
    """
    out = []
    for fixture in fixtures:
        start = fixture.get('starts_at')
        if not start:
            continue
        try:
            when = datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if when > now:
            out.append({**fixture, 'starts_in_hours': round((when - now).total_seconds() / 3600, 2)})
    return sorted(out, key=lambda f: (f['starts_at'], f['id']))


def missing_fixtures(live: Iterable[dict], snapshot_ids: Iterable[str], now: datetime) -> list[dict]:
    """Live, still-upcoming fixtures that the deployed snapshot has no row for."""
    known = {str(i) for i in snapshot_ids}
    return [f for f in future_fixtures(live, now) if f['id'] not in known]


def decide(live: Iterable[dict], snapshot: dict, now: datetime,
           runs: Iterable[dict] | None = None) -> dict:
    """Pure decision. ``runs`` is the pages.yml run list (may be empty/None).

    Returns a dict with ``action`` in {'none', 'dispatch'} plus the reason and the
    fixtures that justify it, so the workflow log and the tests read the same
    facts.
    """
    snapshot = snapshot or {}
    snapshot_ids = {str(m.get('id')) for m in snapshot.get('matches') or [] if m.get('id') is not None}
    live = list(live)
    future = future_fixtures(live, now)
    missing = [f for f in future if f['id'] not in snapshot_ids]
    result = {
        'generated_at': snapshot.get('generated_at'),
        'live_records': len(live),
        'live_upcoming': len(future),
        'snapshot_records': len(snapshot_ids),
        'missing': missing,
        'action': 'none',
        'reason': '',
    }
    if not snapshot_ids:
        result['reason'] = ('the deployed snapshot carries no fixture rows; coverage cannot be '
                            'compared, so nothing is dispatched (the freshness watchdog owns an '
                            'unreadable snapshot)')
        return result
    if not live:
        result['reason'] = ('the Hotspawn fixture feed returned no records; an unreadable feed is '
                            'not evidence of a gap, so nothing is dispatched')
        return result
    if not missing:
        result['reason'] = (f'every one of the {len(future)} live upcoming fixtures is already carried '
                            f'by the deployed snapshot ({len(snapshot_ids)} records)')
        return result

    runs = list(runs or [])
    now_utc = now
    for run in runs:
        status = str(run.get('status') or '')
        created = run.get('created_at') or run.get('run_started_at') or ''
        try:
            created_at = datetime.strptime(created, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        except ValueError:
            created_at = None
        if status == 'in_progress':
            result['reason'] = f'a publish is already running (run {run.get("id")})'
            return result
        if status in {'queued', 'pending', 'requested', 'waiting'}:
            if run.get('event') == 'workflow_dispatch':
                result['reason'] = (f'a dispatched publish is already queued (run {run.get("id")}); a second '
                                    'dispatch would cancel it')
                return result
            if created_at and (now_utc - created_at) <= timedelta(minutes=QUEUED_GRACE_MINUTES):
                result['reason'] = f'a publish is queued (run {run.get("id")})'
                return result
        if created_at and (now_utc - created_at) <= timedelta(minutes=MIN_RUN_AGE_MINUTES):
            result['reason'] = (f'a publish started {int((now_utc - created_at).total_seconds() / 60)} minute(s) '
                                f'ago (run {run.get("id")}); letting it finish first')
            return result

    result['action'] = 'dispatch'
    earliest = missing[0]
    result['reason'] = (f'{len(missing)} live Hotspawn card(s) with a future start are absent from the '
                        f'deployed snapshot {snapshot.get("generated_at")!r}; the earliest is '
                        f'{earliest["id"]} ({earliest["starts_at"]}); no publish is queued or running')
    return result


def _get(url: str, headers: dict | None = None, timeout: int = 45) -> Any:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed hosts
        return json.loads(response.read().decode('utf-8'))


def read_runs(repo: str, token: str) -> list[dict]:
    headers = {'Accept': 'application/vnd.github+json', 'Cache-Control': 'no-cache'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    payload = _get(f'https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}/runs?per_page=20',
                   headers)
    return payload.get('workflow_runs') or []


def dispatch(repo: str, token: str) -> int:
    headers = {'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}/dispatches',
        data=json.dumps({'ref': 'main'}).encode(), method='POST', headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310 - fixed host
        return response.status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='decide and report, never dispatch')
    parser.add_argument('--decide', action='store_true', help='print the decision JSON and exit')
    parser.add_argument('--repo', default=os.environ.get('REPO') or os.environ.get('GITHUB_REPOSITORY') or '')
    parser.add_argument('--now', default='', help='ISO-8601 UTC override for tests/replays')
    parser.add_argument('--from-fixtures', default='', metavar='PATH',
                        help='replay a saved Hotspawn fixture array instead of fetching it')
    parser.add_argument('--from-snapshot', default='', metavar='PATH',
                        help='replay a saved snapshot.json instead of fetching the deployed one')
    args = parser.parse_args(argv)

    now = (datetime.strptime(args.now, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
           if args.now else datetime.now(timezone.utc).replace(microsecond=0))
    token = os.environ.get('GH_TOKEN', '')
    stamp = now.strftime('%Y-%m-%dT%H:%M:%SZ')

    live, snapshot, notes = [], {}, []
    try:
        if args.from_fixtures:
            payload = json.loads(Path(args.from_fixtures).read_text())
        else:
            payload = _get(f'{FIXTURES_API}&cb={stamp}', {'Cache-Control': 'no-cache'})
        live = parse_fixtures(payload)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        notes.append(f'fixture feed unreadable ({type(exc).__name__}: {exc})')
    try:
        if args.from_snapshot:
            snapshot = json.loads(Path(args.from_snapshot).read_text())
        else:
            snapshot = _get(f'{SNAPSHOT_URL}?coverage_watch={stamp}', {'Cache-Control': 'no-cache'})
    except (urllib.error.URLError, ValueError, OSError) as exc:
        notes.append(f'deployed snapshot unreadable ({type(exc).__name__}: {exc})')

    runs = []
    if args.repo and not args.decide:
        try:
            runs = read_runs(args.repo, token)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            notes.append(f'run list unreadable ({type(exc).__name__}: {exc})')

    result = decide(live, snapshot, now, runs)
    result['notes'] = notes
    result['checked_at'] = stamp
    print(json.dumps(result, indent=2))
    for note in notes:
        print(f'::warning::{note}')

    if result['action'] != 'dispatch' or args.dry_run or args.decide:
        if result['action'] == 'dispatch':
            print('dry run: a dispatch would have been requested')
        return 0
    if not args.repo or not token:
        print('::warning::no repo/token available; a dispatch is required but was not attempted')
        return 0
    try:
        status = dispatch(args.repo, token)
    except (urllib.error.URLError, OSError) as exc:
        print(f'::error::dispatch failed: {type(exc).__name__}: {exc}')
        return 1
    print(f'dispatched {WORKFLOW} on main (HTTP {status}) for {len(result["missing"])} missing card(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
