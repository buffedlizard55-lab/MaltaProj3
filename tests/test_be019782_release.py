"""Recovery only retires proved obsolete main publishers; no network/data edits."""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import be019782_release as release

CURRENT = 'b' * 40
OLD = 'a' * 40
REPO = 'buffedlizard55-lab/MaltaProj3'


def run(**changes):
    row = {'id': 42, 'head_sha': OLD, 'head_branch': 'main', 'status': 'queued',
           'event': 'push', 'path': '.github/workflows/pages.yml'}
    return dict(row, **changes)


class API:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []
        self.relations = {CURRENT: 'ahead', OLD: 'behind', release.CORE_COMMIT: 'identical'}
        self.denied = False
        self.never_stops = False
        self.finish_race = False
        self.bad_list = False
        self.all_pages = False

    def __call__(self, path, method='GET'):
        self.calls.append((path, method))
        if path.startswith('compare/'):
            return {'status': self.relations.get(path.split('...')[1], 'ahead')}
        if path.startswith('actions/workflows/'):
            if self.bad_list:
                return {'message': 'not a verified list'}
            rows = self.rows if 'status=queued&' in path else []
            if '&page=1' not in path and not self.all_pages:
                rows = []
            return {'workflow_runs': rows}
        if method == 'POST':
            if self.denied:
                raise RuntimeError('permission denied')
            return {}
        return {'status': 'in_progress' if self.never_stops and not self.finish_race else 'completed'}

    @property
    def cancellations(self):
        return [path for path, method in self.calls if method == 'POST']


class CancellationScope(unittest.TestCase):
    def retire(self, api, **kwargs):
        return release.retire_obsolete(api, CURRENT, 999, sleep=lambda _: None, **kwargs)

    def test_only_confirmed_pre_core_main_run_is_cancelled(self):
        api = API([run(), run(id=43, head_sha=CURRENT), run(id=44, head_sha=release.CORE_COMMIT)])
        self.assertEqual(self.retire(api), [42])
        self.assertEqual(api.cancellations, ['actions/runs/42/cancel'])

    def test_feature_branch_is_never_cancelled(self):
        api = API([run(head_branch='arena/another-session')])
        self.assertEqual(self.retire(api), [])
        self.assertEqual(api.cancellations, [])

    def test_pr_or_other_workflow_is_never_cancelled(self):
        api = API([run(event='pull_request'), run(id=43, path='.github/workflows/checks.yml')])
        self.assertEqual(self.retire(api), [])
        self.assertEqual(api.cancellations, [])

    def test_completed_or_current_run_is_never_cancelled(self):
        api = API([run(status='completed'), run(id=999)])
        self.assertEqual(self.retire(api), [])
        self.assertEqual(api.cancellations, [])

    def test_current_release_must_contain_the_verified_core(self):
        api = API([run()]); api.relations[CURRENT] = 'behind'
        with self.assertRaisesRegex(RuntimeError, 'validated source-replay'):
            self.retire(api)
        self.assertEqual(api.cancellations, [])

    def test_unknown_ancestry_is_not_guessed(self):
        api = API([run()]); api.relations[OLD] = 'diverged'
        with self.assertRaisesRegex(RuntimeError, 'ancestry'):
            self.retire(api)
        self.assertEqual(api.cancellations, [])

    def test_entire_plan_is_proved_before_any_cancel(self):
        api = API([run(), run(id=43, head_sha='c' * 40)])
        api.relations['c' * 40] = 'diverged'
        with self.assertRaises(RuntimeError):
            self.retire(api)
        self.assertEqual(api.cancellations, [])

    def test_invalid_id_or_sha_cannot_become_an_api_path(self):
        for changes in ({'id': '../1'}, {'id': True}, {'id': 0}, {'head_sha': '../../bad'}):
            api = API([run(**changes)])
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                self.retire(api)
            self.assertEqual(api.cancellations, [])

    def test_unverified_list_stops_before_cancellation(self):
        api = API(); api.bad_list = True
        with self.assertRaisesRegex(RuntimeError, 'verified response'):
            self.retire(api)
        self.assertEqual(api.cancellations, [])

    def test_status_duplicate_is_deduplicated(self):
        api = API([run(), run()])
        self.assertEqual(self.retire(api), [42])
        self.assertEqual(len(api.cancellations), 1)

    def test_permission_failure_does_not_emit_success(self):
        api = API([run()]); api.denied = api.never_stops = True
        with self.assertRaisesRegex(RuntimeError, 'permission denied'):
            self.retire(api)

    def test_completed_race_is_safe_but_no_run_is_force_cancelled(self):
        api = API([run()]); api.denied = api.finish_race = True
        self.assertEqual(self.retire(api), [42])
        self.assertFalse(any('force-cancel' in path for path, _ in api.calls))

    def test_cancel_request_is_not_enough_until_completion(self):
        api = API([run()]); api.never_stops = True
        with self.assertRaisesRegex(RuntimeError, 'has not stopped'):
            self.retire(api, timeout=0)

    def test_full_page_is_followed_and_pagination_cannot_be_silently_truncated(self):
        api = API([run()] * 100)
        self.assertEqual(self.retire(api), [42])
        self.assertTrue(any('&page=2' in path for path, _ in api.calls))
        api = API([run()] * 100); api.all_pages = True
        with self.assertRaisesRegex(RuntimeError, 'pagination is incomplete'):
            self.retire(api)
        self.assertEqual(api.cancellations, [])


class CLIRequiresAuthenticatedIntent(unittest.TestCase):
    def env(self, output):
        return {'GH_REPO': REPO, 'GITHUB_RUN_ID': '999', 'GITHUB_SHA': CURRENT,
                'GITHUB_OUTPUT': str(output)}

    def test_no_flag_performs_no_operation(self):
        with patch.object(release, 'gh_api') as api, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                release.main([])
            api.assert_not_called()

    def test_safe_output_is_written_only_after_confirmed_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'
            api = API([run()])
            with patch.dict(os.environ, self.env(output), clear=True), \
                 patch.object(release, 'gh_api', side_effect=lambda repo, path, method: api(path, method)), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(release.main(['--clear-obsolete']), 0)
            self.assertEqual(output.read_text(), 'safe=true\n')

    def test_refusal_never_sets_queue_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'
            with patch.dict(os.environ, self.env(output), clear=True), \
                 patch.object(release, 'retire_obsolete', side_effect=RuntimeError('uncertain')), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(release.main(['--clear-obsolete']), 1)
            self.assertFalse(output.exists())

    def test_missing_output_context_cannot_cancel_anything(self):
        env = self.env(''); env.pop('GITHUB_OUTPUT')
        with patch.dict(os.environ, env, clear=True), patch.object(release, 'gh_api') as api, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                release.main(['--clear-obsolete'])
            api.assert_not_called()


class FullPublisherStillGuardsEverySource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path('.github/workflows/pages.yml').read_text()
        cls.fast, cls.fresh = cls.text.split('  verify-and-deploy:', 1)

    def test_primary_and_catch_up_schedules_are_retained(self):
        self.assertIn("cron: '17 */4 * * *'", self.text)
        self.assertIn("cron: '47 2-22/4 * * *'", self.text)
        self.assertEqual(self.text.count("&& 'macos-14' || 'ubuntu-24.04'"), 2)

    def test_recovery_is_a_separate_serial_group_not_a_new_publisher(self):
        self.assertIn("&& 'recovery' || github.event_name", self.text)
        self.assertIn('cancel-in-progress: false', self.text)
        self.assertIn('needs: [republish-last-verified]', self.fresh)

    def test_action_write_is_scoped_to_the_small_job(self):
        default = self.text.split('jobs:', 1)[0]
        self.assertIn('actions: read', default)
        self.assertNotIn('actions: write', default)
        self.assertIn('actions: write', self.fast)
        self.assertNotIn('actions: write', self.fresh)
        self.assertIn('contents: read', self.fast)

    def test_recovery_requires_confirmed_queue_safety(self):
        self.assertIn("needs['republish-last-verified'].outputs.queue_safe == 'true'", self.fresh)
        self.assertIn('queue_safe: ${{ steps.retire.outputs.safe }}', self.fast)
        self.assertIn('if: always()', self.fresh)
        self.assertIn("github.ref == 'refs/heads/main'", self.fresh)

    def test_regression_still_precedes_cache_and_returns_its_own_failure(self):
        self.assertLess(self.fresh.index('python -m unittest discover -s tests -v'),
                        self.fresh.index('uses: actions/cache/restore@'))
        self.assertIn('status=${PIPESTATUS[0]}', self.fresh)
        self.assertIn('exit "$status"', self.fresh)
        self.assertIn('timeout-minutes: 60', self.fresh)

    def test_source_collection_replay_and_live_verification_are_not_skipped(self):
        for command in ('scripts.collect', 'scripts.originate', 'scripts.build', 'scripts.verify_live'):
            self.assertIn(command, self.fresh)
        self.assertIn('scripts.be019782_release --clear-obsolete', self.fast)


if __name__ == '__main__':
    unittest.main()
