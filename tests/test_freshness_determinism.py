"""Freshness must be a function of an explicit reference time, never the clock.

Background
----------
On 2026-10-17 the four-hour publisher stopped deploying. Every scheduled run
failed at "Regression tests (repository fixtures, before any cache restore)"
(runs 39038670350, 39045650525, 39054246287, 39058407711) while the last
successful run was 39031549764 at about 12:20Z. The cause was a single
wall-clock-dependent assertion:

    tests/test_summary.py::InventoryCrosscheckNoticeTests::
        test_unavailable_crosscheck_is_visible_and_does_not_mark_picks_stale

`scripts/build.py::shell` decided staleness with `datetime.now(timezone.utc)`
against a fixture whose `inventory_observed_at` was hard-coded to
`2026-10-17T04:27:55Z`. The eight-hour freshness window therefore closed at
**2026-10-17T12:27:55Z**, which is exactly when the successful run stopped and
the failing runs began. Because the regression tests run *before* the cache
restore and before collection, that one expired assertion froze the whole
refresh: the public site kept serving a frozen snapshot.

The fix is to make the reference time an injected argument, and these tests
make that contract permanent:

1. every time-sensitive renderer must accept an explicit reference time;
2. freshness must follow only that argument;
3. the repository's own time-sensitive test modules must still pass when the
   production clock is moved far into the future — the exact failure mode above.
"""
import contextlib
import inspect
import io
import sys
import unittest
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from scripts import build as build_module
from scripts.build import coverage, glance, matches_table, picks, shell, summary

# The modules that render time-dependent output. They are re-run under a
# shifted production clock; a module that cannot be imported is skipped rather
# than failing the guard for an unrelated reason.
TIME_SENSITIVE_MODULES = (
    'tests.test_summary',
    'tests.test_build',
    'tests.test_build_hardening',
    'tests.test_summary_navigation',
    'tests.test_briefing',
    'tests.test_pick_presentation_safety',
    'tests.test_twc',
    'tests.test_twc_day4',
)

# Far enough ahead that every eight-hour freshness window and every "future
# start" fixture in a fixed-date fixture set is in the past.
FAR_FUTURE_DAYS = 400


@contextlib.contextmanager
def shifted_production_clock(days):
    """Move the clock the production code reads, leaving the test's own clock alone.

    `scripts.*` modules import `datetime` directly (`from datetime import
    datetime`), so the class they hold is what has to be replaced. The
    subclass keeps every classmethod except the three that read the current
    time, so parsing and formatting behave exactly as before.
    """
    base = datetime

    class Shifted(base):
        @classmethod
        def now(cls, tz=None):
            return base.now(tz) + timedelta(days=days)

        @classmethod
        def today(cls):
            return base.today() + timedelta(days=days)

        @classmethod
        def utcnow(cls):
            return base.utcnow() + timedelta(days=days)

    modules = [m for name, m in list(sys.modules.items())
               if name == 'scripts' or name.startswith('scripts.')]
    patched = [m for m in modules if getattr(m, 'datetime', None) is base]
    for module in patched:
        module.datetime = Shifted
    try:
        yield
    finally:
        for module in patched:
            module.datetime = base


def load_time_sensitive_suite():
    """Discover the time-sensitive test modules the same way CI does."""
    tests_dir = str(__import__('pathlib').Path('tests').resolve())
    if tests_dir not in sys.path:
        # `unittest discover -s tests` puts the test directory on the path, so
        # a module that does `import test_x` resolves there.
        sys.path.insert(0, tests_dir)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in TIME_SENSITIVE_MODULES:
        try:
            suite.addTests(loader.loadTestsFromName(name))
        except Exception:  # pragma: no cover - a module that cannot be loaded
            continue
    return suite


class ReferenceTimeInjectionTests(unittest.TestCase):
    """Every time-sensitive renderer must accept an explicit reference time."""

    def test_build_renderers_accept_a_reference_time(self):
        for function in (shell, matches_table, glance, summary, picks, coverage):
            with self.subTest(function=function.__name__):
                self.assertIn('now', inspect.signature(function).parameters)

    def test_pick_presentation_and_origination_accept_a_reference_time(self):
        from scripts.build_origination import page as origination_page
        from scripts.build_origination import pick_row
        from scripts.pick_safety import presentation
        for function in (origination_page, pick_row, presentation):
            with self.subTest(function=function.__name__):
                self.assertIn('now', inspect.signature(function).parameters)

    def test_build_entry_point_accepts_a_reference_time(self):
        self.assertIn('now', inspect.signature(build_module.build).parameters)

    def test_the_default_still_reads_the_wall_clock_for_production(self):
        """Injection is optional; a production build with no `now` still works."""
        data = {'flags': [], 'inventory_observed_at': '2026-10-17T04:27:55Z',
                'generated_at': '2026-10-17T07:16:06Z', 'coverage_complete': True,
                'inventory_crosscheck': 'complete'}
        html = shell(data, 'methodology', '', '../')
        self.assertIn('id="stale-warning"', html)


class StalenessFollowsTheInjectedTimeTests(unittest.TestCase):
    """Freshness must be decided by the injected reference time alone."""

    OBSERVED_AT = '2026-10-17T04:27:55Z'
    FRESH_AT = datetime(2026, 10, 17, 5, 27, 55, tzinfo=timezone.utc)
    STALE_AT = datetime(2026, 10, 17, 13, 27, 55, tzinfo=timezone.utc)

    def data(self, crosscheck='complete'):
        return {'flags': [], 'inventory_observed_at': self.OBSERVED_AT,
                'generated_at': '2026-10-17T07:16:06Z', 'coverage_complete': True,
                'inventory_crosscheck': crosscheck}

    def hidden(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        return 'hidden' in soup.find(id='stale-warning').attrs

    def test_a_snapshot_inside_the_window_is_not_stale(self):
        self.assertTrue(self.hidden(shell(self.data(), 'methodology', '', '../', now=self.FRESH_AT)))

    def test_a_snapshot_outside_the_window_is_stale(self):
        self.assertFalse(self.hidden(shell(self.data(), 'methodology', '', '../', now=self.STALE_AT)))

    def test_rendering_is_reproducible_for_the_same_reference_time(self):
        first = shell(self.data(), 'methodology', '', '../', now=self.FRESH_AT)
        second = shell(self.data(), 'methodology', '', '../', now=self.FRESH_AT)
        self.assertEqual(first, second)

    def test_an_incomplete_inventory_is_stale_at_any_reference_time(self):
        data = self.data()
        data['coverage_complete'] = False
        self.assertFalse(self.hidden(shell(data, 'methodology', '', '../', now=self.FRESH_AT)))


class FarFutureClockTests(unittest.TestCase):
    """The repository's own time-sensitive tests must not expire."""

    def test_time_sensitive_suite_passes_with_the_clock_moved_far_forward(self):
        suite = load_time_sensitive_suite()
        if suite.countTestCases() == 0:
            self.skipTest('no time-sensitive test module could be loaded')
        with shifted_production_clock(FAR_FUTURE_DAYS):
            stream = io.StringIO()
            result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        problems = [f'{test.id()}: {text.strip().splitlines()[-1]}'
                    for test, text in result.failures + result.errors]
        self.assertFalse(problems, 'time-sensitive tests expired against the wall clock:\n' + '\n'.join(problems))
        self.assertGreaterEqual(result.testsRun, 20)


if __name__ == '__main__':
    unittest.main()
