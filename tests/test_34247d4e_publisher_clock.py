"""Session arena-34247d4e: a publisher test must never read the wall clock.

The four-hour publisher stopped on **2026-10-23T21:41Z** and did not publish
again until a human fixed it. Every one of those scheduled runs
(40028653350, 40037957529, 40048429858, 40063011446) failed the *same* step --
"Regression tests (repository fixtures, before any cache restore)" -- with:

    scripts.root_publish.PublishRefused: snapshot 2026-10-23T09:23:57+00:00
    is 21.3h old (limit 12.0h); pass --allow-stale to publish it anyway

`scripts.root_publish.build_plan()` defaults `now` to the wall clock, and
`tests/test_ca7e10e5_snapshot.py` called it with a **fixed** 2026-10-23T09:23:57Z
fixture. The tests therefore passed for twelve hours after they were written and
then failed forever, blocking the whole refresh (nine researched cards went
unpublished for 10.5 hours).

The fix (PR #240) pins `now=` on each of those calls. This module keeps the
class of defect from coming back: no test may call `build_plan` against a fixed
fixture without pinning its reference time, because such a call is a guaranteed
future failure.

Nothing here asserts a probability or a pick; it asserts clock hygiene.
"""
from __future__ import annotations

import ast
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import root_publish

TESTS_DIR = Path(__file__).resolve().parent

# The fixture stamp used by tests/test_ca7e10e5_snapshot.py. It is in the past
# for every future run, which is exactly why an unpinned call must be banned.
FIXTURE_STAMP = "2026-10-23T09:23:57Z"

# The pinned reference time used by that module after PR #240.
PINNED_NOW = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)


def _calls_to_build_plan(source: str):
    """Yield (lineno, has_now_keyword) for every call to build_plan() in source."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", None)
        if name != "build_plan":
            continue
        # ``**options`` is a helper splat: test_96fbe295.py builds
        # ``{"now": NOW}`` before splatting, which is pinned too.
        has_now = any(kw.arg in ("now", None) for kw in node.keywords)
        yield node.lineno, has_now


class NoTestMayCallBuildPlanWithoutPinningTheClock(unittest.TestCase):
    def test_no_test_module_calls_build_plan_without_now(self):
        offenders = {}
        seen = 0
        for path in sorted(TESTS_DIR.glob("test_*.py")):
            # This module calls build_plan() unpinned on purpose: that call is
            # the reproduction of the outage, and it asserts the refusal.
            if path.name == Path(__file__).name:
                continue
            source = path.read_text(encoding="utf-8")
            if "build_plan" not in source:
                continue
            for lineno, has_now in _calls_to_build_plan(source):
                seen += 1
                if not has_now:
                    offenders.setdefault(path.name, []).append(lineno)
        self.assertGreater(seen, 0, "the guard must actually be looking at real calls")
        self.assertEqual(
            offenders, {},
            "these calls use the wall clock against a fixed fixture and will fail "
            f"the publisher once the fixture is stale: {offenders}",
        )

    def test_the_snapshot_module_keeps_its_pinned_reference_time(self):
        # A regression that reverts the pin has to fail here, loudly.
        source = (TESTS_DIR / "test_ca7e10e5_snapshot.py").read_text(encoding="utf-8")
        self.assertIn("now=datetime(2026, 10, 23, 10, 0", source)

    def test_the_splat_helper_still_pins_the_clock(self):
        # The only unpinned-looking call left in the suite is a **splat; it is
        # accepted above only because the dict it splats pins ``now``.
        source = (TESTS_DIR / "test_96fbe295.py").read_text(encoding="utf-8")
        self.assertIn('options = {"now": NOW}', source)


class TheGuardMatchesTheReportedOutage(unittest.TestCase):
    """The behaviour the failing runs hit, reproduced against a fixed fixture."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.output = base / "site"
        self.root = base / "root"
        self.output.mkdir()
        self.root.mkdir()
        (self.output / "data").mkdir()
        snapshot = {
            "schema_version": 1,
            "generated_at": FIXTURE_STAMP,
            "counts": {"inventory": 30, "upcoming": 30, "picks": 30},
        }
        (self.output / "data/latest.json").write_text(json.dumps(snapshot))
        (self.output / "snapshot.json").write_text(json.dumps(snapshot))
        (self.output / "index.html").write_text(
            '<html><body data-snapshot-generated="' + FIXTURE_STAMP + '">'
            + "x" * root_publish.MIN_INDEX_BYTES
            + "</body></html>"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_an_unpinned_call_refuses_a_stale_fixture(self):
        # Deterministic: the fixture is in the past for every future run, so the
        # wall clock always reports an age above the 12h limit.
        with self.assertRaises(root_publish.PublishRefused) as caught:
            root_publish.build_plan(self.output, self.root)
        self.assertIn("old (limit 12.0h)", str(caught.exception))

    def test_the_pinned_reference_time_keeps_the_fixture_publishable(self):
        plan = root_publish.build_plan(self.output, self.root, now=PINNED_NOW)
        self.assertIn("snapshot.json", plan.writes)

    def test_the_pinned_reference_time_is_within_the_publisher_limit(self):
        stamp = datetime.strptime(FIXTURE_STAMP, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        self.assertLess(PINNED_NOW - stamp, timedelta(hours=12))
        self.assertGreaterEqual(PINNED_NOW, stamp)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
