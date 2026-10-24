"""Freshness-watchdog contract (session arena-da8067f5).

The publisher's push-triggered runs live in one concurrency group and GitHub
cancels the single pending run there whenever a newer push is queued, so while
several sessions merge into `main` every few minutes nothing started (verified
2026-10-24: five push runs cancelled while pending and the 06:09Z run never
started within 40 minutes). `.github/workflows/freshness-watchdog.yml` is the
safety net; `workflow_dispatch` runs are in their own group and cannot be
cancelled by pushes.

These tests execute the workflow's own decision code with a stubbed network, so
the rules are checked without a runner:

* fresh snapshot            -> no dispatch;
* stale + run queued        -> no dispatch (never a second publisher);
* stale + nothing running   -> exactly one POST to the dispatch endpoint;
* dry run                   -> no POST at all;
* unreadable snapshot       -> treated as stale (a broken deploy must not look
  fresh), but still subject to the "already running" check.

The workflow is also pinned to what makes it useful: a 30-minute schedule, the
`actions: write` permission it needs to dispatch, and no cancel-in-progress.
"""
from __future__ import annotations

import io
import json
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / '.github' / 'workflows' / 'freshness-watchdog.yml'


def workflow_text():
    return WORKFLOW.read_text()


def script_body():
    """The heredoc body as the runner sees it (YAML strips the block indent)."""
    text = workflow_text()
    start = text.index("python3 - <<'PY'\n") + len("python3 - <<'PY'\n")
    end = text.index('\n          PY', start)
    body = text[start:end]
    indent = min(len(line) - len(line.lstrip()) for line in body.splitlines() if line.strip())
    return '\n'.join(line[indent:] if line.strip() else '' for line in body.splitlines())


class StubResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
        return False


def run_decision(*, snapshot, runs, dry='true', max_age='6'):
    """Execute the workflow's decision code; return (dispatched, output)."""
    posted, printed = [], []

    def urlopen(request, timeout=None):                     # noqa: ARG001
        url = request if isinstance(request, str) else request.full_url
        if 'dispatches' in url:
            posted.append(url)
            return StubResponse(b'{}')
        if 'api.github.com' in url:
            return StubResponse(json.dumps({'workflow_runs': runs}).encode())
        if isinstance(snapshot, Exception):
            raise snapshot
        return StubResponse(json.dumps(snapshot).encode())

    urllib = types.ModuleType('urllib')
    request_module = types.ModuleType('urllib.request')
    request_module.urlopen = urlopen
    request_module.Request = lambda url, data=None, method=None, headers=None: types.SimpleNamespace(
        full_url=url, data=data, method=method, headers=headers)
    urllib.request = request_module

    saved = {name: sys.modules.get(name) for name in ('urllib', 'urllib.request')}
    sys.modules['urllib'] = urllib
    sys.modules['urllib.request'] = request_module
    env = {
        'REPO': 'buffedlizard55-lab/MaltaProj3', 'MAX_AGE_HOURS': max_age, 'DRY_RUN': dry,
        'GH_TOKEN': 'test-token', 'GITHUB_RUN_ID': '1',
    }
    old_env = {}
    import os
    for key, value in env.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        exec(compile(script_body(), 'freshness-watchdog.py', 'exec'), {'__name__': '__main__'})
    except SystemExit as exc:
        printed.append(f'exit={exc.code}')
    finally:
        for module, module_value in saved.items():
            if module_value is None:
                sys.modules.pop(module, None)
            else:
                sys.modules[module] = module_value
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return posted, printed


def snapshot_age(hours):
    when = datetime.now(timezone.utc) - timedelta(hours=hours)
    return {'generated_at': when.strftime('%Y-%m-%dT%H:%M:%SZ')}


def queued(minutes_ago, run_id=42, event='push'):
    when = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return {'id': run_id, 'status': 'queued', 'event': event,
            'created_at': when.strftime('%Y-%m-%dT%H:%M:%SZ')}


class WatchdogContractTests(unittest.TestCase):
    def test_schedule_permission_and_group_are_pinned(self):
        text = workflow_text()
        self.assertIn("cron: '*/30 * * * *'", text)
        self.assertIn('actions: write', text)
        self.assertIn('cancel-in-progress: false', text)
        self.assertIn('workflow_dispatch:', text)

    def test_fresh_snapshot_never_dispatches(self):
        posted, _ = run_decision(snapshot=snapshot_age(1), runs=[])
        self.assertEqual(posted, [])

    def test_stale_snapshot_dispatches_once_when_nothing_is_running(self):
        posted, _ = run_decision(snapshot=snapshot_age(9), runs=[], dry='false')
        self.assertEqual(len(posted), 1)
        self.assertTrue(posted[0].endswith('/actions/workflows/pages.yml/dispatches'))

    def test_stale_snapshot_with_a_freshly_queued_run_does_not_dispatch(self):
        posted, _ = run_decision(snapshot=snapshot_age(9), runs=[queued(2)], dry='false')
        self.assertEqual(posted, [])

    def test_stale_snapshot_with_an_in_progress_run_does_not_dispatch(self):
        posted, _ = run_decision(snapshot=snapshot_age(9),
                                 runs=[{'id': 43, 'status': 'in_progress'}], dry='false')
        self.assertEqual(posted, [])

    def test_a_stuck_queued_run_does_not_block_the_dispatch(self):
        """A pending push run that GitHub will cancel is not a publish."""
        posted, _ = run_decision(snapshot=snapshot_age(9), runs=[queued(40, run_id=44)], dry='false')
        self.assertEqual(len(posted), 1)

    def test_a_queued_dispatch_run_blocks_a_second_dispatch_while_it_can_start(self):
        """Dispatching again would cancel the run this watchdog just queued."""
        posted, _ = run_decision(snapshot=snapshot_age(12),
                                 runs=[queued(20, run_id=46, event='workflow_dispatch')], dry='false')
        self.assertEqual(posted, [])

    def test_a_queued_dispatch_run_stalled_by_a_starved_pool_stops_blocking(self):
        """Verified 2026-10-24: dispatch runs 40074120319/40074984702 sat queued
        for over an hour while every workflow in the repository was also queued.
        A queued run has executed no step, so a fresh dispatch loses no work."""
        posted, _ = run_decision(snapshot=snapshot_age(12),
                                 runs=[queued(90, run_id=46, event='workflow_dispatch')], dry='false')
        self.assertEqual(len(posted), 1)

    def test_a_queued_dispatch_run_without_a_created_at_still_blocks(self):
        posted, _ = run_decision(snapshot=snapshot_age(12),
                                 runs=[{'id': 47, 'status': 'queued', 'event': 'workflow_dispatch',
                                        'created_at': ''}], dry='false')
        self.assertEqual(posted, [])

    def test_queued_run_without_a_parseable_created_at_is_not_a_publish(self):
        posted, _ = run_decision(snapshot=snapshot_age(9),
                                 runs=[{'id': 45, 'status': 'queued', 'created_at': ''}], dry='false')
        self.assertEqual(len(posted), 1)

    def test_dry_run_reports_but_never_dispatches(self):
        posted, _ = run_decision(snapshot=snapshot_age(9), runs=[], dry='true')
        self.assertEqual(posted, [])

    def test_unreadable_snapshot_is_treated_as_stale(self):
        posted, _ = run_decision(snapshot=RuntimeError('network down'), runs=[], dry='false')
        self.assertEqual(len(posted), 1)

    def test_threshold_is_respected(self):
        posted, _ = run_decision(snapshot=snapshot_age(5), runs=[], dry='false', max_age='6')
        self.assertEqual(posted, [])
        posted, _ = run_decision(snapshot=snapshot_age(7), runs=[], dry='false', max_age='6')
        self.assertEqual(len(posted), 1)

    def test_the_workflow_never_publishes_anything_itself(self):
        """It may only ask the verified publisher to run."""
        text = workflow_text()
        for forbidden in ('gh-pages', 'git push', 'upload-pages-artifact', 'deploy-pages@', 'actions/checkout'):
            self.assertNotIn(forbidden, text)
        self.assertIn('actions/workflows/pages.yml/dispatches', script_body())


if __name__ == '__main__':
    unittest.main()
