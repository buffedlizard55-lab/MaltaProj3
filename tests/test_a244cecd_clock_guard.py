"""Session a244cecd: no test may hand the root publisher the wall clock.

Background (verified 2026-10-24T05:20Z from the Actions API)
------------------------------------------------------------
The scheduled *Refresh and deploy CS2 dashboard* runs 40028653350,
40037957529, 40048429858 and 40063011446 all failed at "Regression tests
(repository fixtures, before any cache restore)" with three ERRORs in
``tests/test_ca7e10e5_snapshot.py::RootPublisherCarriesTheSnapshot``.
Those tests stamp a fixture ``2026-10-23T09:23:57Z`` and called
``root_publish.build_plan(output, root)`` without ``now=``. The production
guard refuses any snapshot older than twelve hours against the wall clock, so
from 2026-10-23T21:24Z every call raised ``PublishRefused`` and the four-hour
publisher stopped deploying. This is the third such date bomb (see
``tests/test_freshness_determinism.py`` for 2026-10-17 and the
``tests.test_96fbe295`` entry for 2026-10-23).

The production guard is correct and is not relaxed. These tests make the
contract permanent instead:

1. a static check: every call to ``build_plan`` / ``root_publish.main`` inside
   ``tests/`` passes an explicit ``now=`` (or ``allow_stale=``/``**options``);
2. a behavioural check: the fixed module passes with the production clock
   pinned to absolute instants before, inside and long after its window.
"""
from __future__ import annotations

import ast
import io
import unittest
from datetime import datetime
from pathlib import Path

TESTS = Path(__file__).resolve().parent
GUARDED_CALLS = {'build_plan', 'main'}
SAFE_KEYWORDS = {'now', 'allow_stale'}

# Absolute instants, never offsets from "now" (an offset guard stops detecting
# a bomb once the real clock has passed it).
PINNED_CLOCKS = (
    '2026-10-23T10:00:00+00:00',  # inside the fixture's twelve-hour window
    '2026-10-23T21:30:00+00:00',  # just after it closed: when the runs began failing
    '2026-10-24T05:30:00+00:00',  # when this session reproduced the failure
    '2026-12-31T23:00:00+00:00',  # long after the tournament
)


def _root_publish_calls(tree: ast.AST):
    """Yield calls to root_publish.build_plan / root_publish.main (or a bare build_plan)."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in GUARDED_CALLS:
            owner = func.value
            if isinstance(owner, ast.Name) and owner.id == 'root_publish':
                yield node
        elif isinstance(func, ast.Name) and func.id == 'build_plan':
            yield node


class NoTestPassesTheWallClockToTheRootPublisher(unittest.TestCase):
    def test_every_call_pins_its_reference_time(self):
        offenders = []
        for path in sorted(TESTS.glob('test_*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            for call in _root_publish_calls(tree):
                names = {k.arg for k in call.keywords}
                if None in names or names & SAFE_KEYWORDS:  # **options or explicit now/allow_stale
                    continue
                offenders.append(f'{path.name}:{call.lineno}')
        self.assertEqual(
            offenders, [],
            'root_publish refuses snapshots older than 12 h against the wall clock; '
            'pass now=<fixed datetime> so the test cannot expire: ' + ', '.join(offenders))

    def test_the_scan_detects_an_unpinned_call(self):
        tree = ast.parse('root_publish.build_plan(a, b)\nroot_publish.build_plan(a, b, now=x)\n')
        unpinned = [c for c in _root_publish_calls(tree)
                    if not ({k.arg for k in c.keywords} & SAFE_KEYWORDS)]
        self.assertEqual(len(unpinned), 1)

    def test_the_production_guard_is_unchanged(self):
        source = (TESTS.parent / 'scripts/root_publish.py').read_text(encoding='utf-8')
        self.assertIn('max_age_hours: float = 12.0', source)
        self.assertIn('reference = now or datetime.now(timezone.utc)', source)


class TheFixedModulePassesAtAnyClock(unittest.TestCase):
    def test_root_publisher_tests_pass_with_the_production_clock_pinned(self):
        from tests.test_freshness_determinism import pinned_production_clock
        from scripts import root_publish  # noqa: F401  (ensure the module is patched)
        import tests.test_ca7e10e5_snapshot as module

        for value in PINNED_CLOCKS:
            with self.subTest(clock=value):
                suite = unittest.defaultTestLoader.loadTestsFromTestCase(
                    module.RootPublisherCarriesTheSnapshot)
                with pinned_production_clock(datetime.fromisoformat(value)):
                    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
                problems = [str(t) for t, _ in result.failures + result.errors]
                self.assertTrue(result.wasSuccessful(), problems)
                self.assertEqual(result.testsRun, 4)


if __name__ == '__main__':
    unittest.main()
