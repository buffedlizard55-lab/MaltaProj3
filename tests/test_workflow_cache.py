"""Regression (session c07e1b40): the publisher's snapshot cache must actually be restorable.

actions/cache derives a cache *version* from the exact `path:` list. PR #34 made the
restore list end with `data/origination/` while the save list ended with
`data/origination/evidence/`, so no saved snapshot could ever be restored and the
outage fallback silently degraded to the old checked-in data. A restore of
`data/origination/` would also have overlaid the reviewed alias registry.
"""
import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'pages.yml'


def cache_paths(text: str, action: str) -> list[str]:
    match = re.search(r'uses: actions/cache/' + action + r'@[^\n]+\n\s+with:\n\s+path: \|\n((?:\s{12}\S[^\n]*\n)+)', text)
    if not match:
        raise AssertionError(f'actions/cache/{action} step with a path block not found')
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


class PublisherCacheTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text()

    def test_restore_and_save_use_the_identical_path_list(self):
        self.assertEqual(cache_paths(self.text, 'restore'), cache_paths(self.text, 'save'))

    def test_reviewed_alias_registry_is_never_cached(self):
        for action in ('restore', 'save'):
            paths = cache_paths(self.text, action)
            self.assertNotIn('data/origination/', paths)
            self.assertFalse(any(p.endswith('aliases.json') for p in paths), paths)

    def test_twc_originals_use_a_separate_symmetric_cache(self):
        # Do not alter the core cache path list/version just to retain tournament
        # evidence; otherwise the previously verified outage snapshot disappears.
        self.assertEqual(self.text.count('path: data/research/twc-current/'), 2)
        self.assertIn('id: restore-twc', self.text)
        self.assertIn('key: twc-verified-v1-${{ github.run_id }}-${{ github.run_attempt }}', self.text)
        self.assertIn('key: ${{ steps.restore-twc.outputs.cache-primary-key }}', self.text)

    def test_fallback_restores_twc_originals_as_well_as_the_pick_pair(self):
        self.assertIn('rm -rf site data/evidence data/origination data/research/twc-current', self.text)
        self.assertIn('last-good/data/research/twc-current" data/research/twc-current', self.text)

    def test_runner_exposes_the_actual_replay_exception_as_an_annotation(self):
        self.assertIn('snapshot build failed::{detail}', self.text)
        self.assertIn('run_build fresh', self.text)
        self.assertIn('run_build last-good', self.text)


if __name__ == '__main__':
    unittest.main()


class PublisherScheduleTests(unittest.TestCase):
    def test_a_dropped_slot_still_leaves_a_refresh_inside_the_eight_hour_bound(self):
        text = WORKFLOW.read_text()
        crons = re.findall(r"- cron: '([^']+)'", text)
        slots = []
        for cron in crons:
            minute, hour = cron.split()[:2]
            rng, _, step = hour.partition('/')
            start, _, end = rng.partition('-')
            first = 0 if start == '*' else int(start)
            last = 23 if not end else int(end)
            slots += [h * 60 + int(minute) for h in range(first, last + 1, int(step or 24))]
        slots = sorted(set(slots))
        self.assertGreaterEqual(len(slots), 12)
        # Worst case: any single slot is dropped -> the gap spans two intervals.
        day = slots + [s + 1440 for s in slots]
        worst = max(day[i + 2] - day[i] for i in range(len(slots)))
        self.assertLessEqual(worst, 8 * 60, f'worst single-drop gap {worst} min')


class PublisherStepOrderTests(unittest.TestCase):
    def test_regression_tests_run_on_repository_fixtures_before_the_cache_restore(self):
        text = WORKFLOW.read_text()
        # Accept both the single-line and the block-list form of the step's
        # `run:` (the step adopted the checks.yml FAIL/ERROR annotation wrapper).
        match = re.search(r'run:\s*(?:\|\n\s+)?python -m unittest discover -s tests', text)
        self.assertIsNotNone(match, 'the regression-test step must run the unittest suite')
        tests_at = match.start()
        restore_at = text.index('uses: actions/cache/restore@')
        self.assertLess(tests_at, restore_at, 'fixture-coupled tests must not run against restored runtime data')
    def test_the_regression_step_publishes_fail_and_error_lines_as_annotations(self):
        """A step failure must name its failing test in the official annotations.

        On 2026-10-20 the two failed scheduled runs (39371739014, 39389855311)
        showed only "exit code 1" plus four synthetic SourceError lines from
        patched tests; the real failing test was unreadable without log access.
        """
        text = WORKFLOW.read_text()
        step = text[re.search(r'name: Regression tests \(repository fixtures', text).start():]
        step = step[:step.index('\n      - name:')]
        self.assertIn('grep -E "^(FAIL|ERROR):"', step)
        self.assertIn('::error title=unittest::', step)
        self.assertIn('PIPESTATUS[0]', step, 'a bare pipeline would return tee\u2019s exit code, masking a suite failure')
