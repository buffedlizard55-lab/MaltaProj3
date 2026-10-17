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
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from scripts import build as build_module
from scripts.build import coverage, glance, matches_table, picks, shell, summary

# The modules that render time-dependent output. They are re-run with the
# production clock pinned to several absolute times; a module that cannot be
# imported is skipped rather than failing the guard for an unrelated reason.
TIME_SENSITIVE_MODULES = (
    'tests.test_summary',
    'tests.test_build',
    'tests.test_build_hardening',
    'tests.test_summary_navigation',
    'tests.test_briefing',
    'tests.test_pick_presentation_safety',
    'tests.test_twc',
    'tests.test_twc_day4',
    'tests.test_day5',
)

# Absolute reference times, not offsets. A guard that shifted the clock
# relative to "now" would stop detecting a bomb once the real clock had moved
# past it, which is exactly when the bomb has already broken the publisher.
# These four instants bracket the fixture that broke it: before the inventory
# observation, inside the eight-hour window that used to be valid, exactly
# after that window closed, and well after the tournament.
PINNED_CLOCKS = (
    '2026-10-16T12:00:00+00:00',
    '2026-10-17T05:30:00+00:00',
    '2026-10-17T13:00:00+00:00',
    '2026-10-20T12:00:00+00:00',
)


@contextlib.contextmanager
def pinned_production_clock(target):
    """Pin the clock the production code reads, leaving the test's own clock alone.

    `scripts.*` modules import `datetime` directly (`from datetime import
    datetime`), so the class they hold is what has to be replaced. The
    subclass keeps every classmethod except the three that read the current
    time, so parsing and formatting behave exactly as before.
    """
    base = datetime

    class Pinned(base):
        @classmethod
        def now(cls, tz=None):
            return target.replace(tzinfo=None) if tz is None else target.astimezone(tz)

        @classmethod
        def today(cls):
            return target.replace(tzinfo=None).date()

        @classmethod
        def utcnow(cls):
            return target.replace(tzinfo=None)

    modules = [m for name, m in list(sys.modules.items())
               if name == 'scripts' or name.startswith('scripts.')]
    patched = [m for m in modules if getattr(m, 'datetime', None) is base]
    for module in patched:
        module.datetime = Pinned
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


class PinnedClockTests(unittest.TestCase):
    """The repository's own time-sensitive tests must not expire."""

    def run_subset(self, pinned):
        suite = load_time_sensitive_suite()
        if suite.countTestCases() == 0:
            self.skipTest('no time-sensitive test module could be loaded')
        with pinned_production_clock(pinned):
            stream = io.StringIO()
            result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        return result

    def test_the_suite_passes_with_the_clock_pinned_to_several_absolute_times(self):
        """A test whose outcome moves with the clock is a time bomb.

        The same modules are run four times with the production clock pinned
        to four absolute instants that bracket the fixture that broke the
        publisher. The wall-clock-dependent form of the assertion fails at
        three of them; the fixed form passes at all four. Because the instants
        are absolute, this guard keeps working no matter when it runs.
        """
        problems = []
        for raw in PINNED_CLOCKS:
            result = self.run_subset(datetime.fromisoformat(raw))
            for test, text in result.failures + result.errors:
                problems.append(f'{raw} · {test.id()}: {text.strip().splitlines()[-1]}')
            self.assertGreaterEqual(result.testsRun, 20, f'the time-sensitive suite shrank at {raw}')
        self.assertFalse(problems, 'these tests expire against the wall clock:\n' + '\n'.join(problems))


if __name__ == '__main__':
    unittest.main()
