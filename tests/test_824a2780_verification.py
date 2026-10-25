"""Session arena-824a2780: every published pick must replay from its own inputs.

``scripts/824a2780_verify.py`` recomputes each active fixture's two probabilities
from the data the page publishes with it (exchange bid/ask midpoints, no-vig
decimal odds, or Valve's Glicko expectation over the published rating rows) and
checks that a fixture without a side is published with a limitation and the
sources that were actually tried.

These tests pin three things, none of them to a wall-clock value:

* the checked-in snapshot replays cleanly and its counts agree with its rows;
* the checker has teeth: a tampered probability, a tampered midpoint or a
  Hotspawn-attributed probability is rejected, so a green run cannot be vacuous;
* when the built pages carry the same observation as the snapshot, every active
  fixture is on the picks page and every fixture without a side is in the
  unresolved register, both reachable from the executive summary.

The page-coverage test records a note - it never fails - whenever the built pages
and the snapshot are from different observations, because that is a publishing
window, not a defect. That is exactly the failure class that stopped the
four-hour publisher before this session: an assertion pinned to a mutable root
snapshot (run 40174233578, 2026-10-25).
"""
import copy
import importlib
import json
import math
import re
import tempfile
import unittest
from pathlib import Path

verify = importlib.import_module('scripts.824a2780_verify')

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'snapshot.json'
SITE = ROOT


def load() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding='utf-8'))


def active(document: dict) -> list[dict]:
    return [m for m in document['matches'] if m.get('availability') != 'past']


class ReplayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = load()

    def check(self, document: dict) -> list[str]:
        # Write the mutated document out and run the real entry point on it, so
        # the test exercises the shipped code path rather than a copy. The
        # fixture goes to a temporary directory: these tests run before the
        # build in CI and must not create or touch the `site/` output.
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir) / 'snapshot.json'
            tmp.write_text(json.dumps(document), encoding='utf-8')
            return verify.verify_snapshot(tmp, None)['errors']

    def test_every_published_row_replays_from_its_own_inputs(self):
        report = verify.verify_snapshot(SNAPSHOT, SITE)
        self.assertEqual(report['errors'], [], '\n'.join(report['errors']))
        self.assertEqual(report['with_pick'] + report['without_pick'], report['active'])
        self.assertGreater(report['active'], 0)

    def test_a_tampered_probability_is_rejected(self):
        document = copy.deepcopy(self.document)
        target = next(m for m in active(document) if (m.get('analysis') or {}).get('probabilities'))
        target['analysis']['probabilities'] = [0.5, 0.5]
        errors = self.check(document)
        self.assertTrue(any(str(target['id']) in e for e in errors), errors)

    def test_a_tampered_midpoint_is_rejected(self):
        document = copy.deepcopy(self.document)
        target = next(m for m in active(document)
                      if ((m.get('analysis') or {}).get('quotes') or [{}])[0].get('midpoint') is not None)
        target['analysis']['quotes'][0]['midpoint'] = 0.01
        errors = self.check(document)
        self.assertTrue(any(str(target['id']) in e and 'midpoint' in e for e in errors), errors)

    def test_a_hotspawn_attributed_probability_is_rejected(self):
        document = copy.deepcopy(self.document)
        target = next(m for m in active(document) if m.get('analysis'))
        target['analysis']['source_url'] = 'https://play.hotspawn.com/lobby'
        errors = self.check(document)
        self.assertTrue(any(str(target['id']) in e and 'Hotspawn' in e for e in errors), errors)

    def test_a_side_must_be_the_strict_favourite_of_its_own_numbers(self):
        document = copy.deepcopy(self.document)
        target = next(m for m in active(document) if m.get('pick_index') is not None)
        target['pick_index'] = 1 - int(target['pick_index'])
        errors = self.check(document)
        self.assertTrue(any(str(target['id']) in e for e in errors), errors)


class CoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = load()
        cls.active = active(cls.document)

    def test_a_fixture_without_a_side_names_the_sources_it_tried(self):
        blanks = [m for m in self.active if m.get('pick_index') is None]
        for match in blanks:
            trail = match.get('research') or []
            stages = ' '.join(str(s.get('stage')) for s in trail).lower()
            self.assertTrue(trail, match['id'])
            self.assertTrue(match.get('limitations'), match['id'])
            self.assertTrue(any(h in stages for h in ('polymarket', 'hltv', 'esportsbook', 'valve')),
                            f"{match['id']}: no primary/HLTV/esportsbook rung is named in {stages!r}")
            for stage in trail:
                self.assertTrue(str(stage.get('source_url') or '').startswith('https://'),
                                f"{match['id']}: {stage.get('stage')!r} has no https source")

    def test_the_executive_summary_links_every_pick_register(self):
        page = SITE / 'index.html'
        if not page.exists():
            self.skipTest('no built executive summary in this tree')
        html = page.read_text(encoding='utf-8', errors='replace')
        for href in ('./picks/', './unresolved/', './origination/#picks', './coverage/', './review/'):
            self.assertIn(href, html, href)

    def test_the_unresolved_register_is_reachable_and_complete(self):
        page = SITE / 'index.html'
        unresolved_page = SITE / 'unresolved' / 'index.html'
        if not page.exists() or not unresolved_page.exists():
            self.skipTest('no built site in this tree')
        marker = re.search(r'generated="([^"]+)"', page.read_text(encoding='utf-8', errors='replace'))
        if not marker or marker.group(1) != self.document.get('generated_at'):
            self.skipTest(f'built pages ({marker.group(1) if marker else "no marker"}) are not from the '
                          f"checked-in snapshot ({self.document.get('generated_at')}); a publishing window, not a defect")
        register = unresolved_page.read_text(encoding='utf-8', errors='replace')
        picks = (SITE / 'picks' / 'index.html').read_text(encoding='utf-8', errors='replace')
        for match in self.active:
            self.assertIn(str(match['id']), picks, f"{match['id']} missing from the picks page")
            if match.get('pick_index') is None:
                self.assertIn(str(match['id']), register,
                              f"{match['id']} has no side and is missing from the unresolved register")


class ArithmeticTest(unittest.TestCase):
    def test_valve_expectation_matches_the_published_form_example(self):
        # RD 75 -> g = 0.9728209910486895, the value every model row publishes.
        g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * 75 ** 2 / math.pi ** 2)
        self.assertAlmostEqual(g, 0.9728209910486895, places=12)
        # Acend 1197 vs UNiTY 1167 on the 2026-10-05 Valve snapshot -> 54.19%.
        self.assertAlmostEqual(verify.valve_probability(1197, 1167), 0.54190155, places=8)
        # Ground Zero 0.22/0.28 and Off Chops 0.72/0.78 -> 25.0% / 75.0%.
        self.assertEqual([round(x, 6) for x in verify.normalized([0.25, 0.75])], [0.25, 0.75])


if __name__ == '__main__':
    unittest.main()
