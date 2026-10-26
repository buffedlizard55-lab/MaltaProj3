"""Regression tests for session arena-60019704 verification (60A-2).

The replay script re-derives every published probability of the deployed snapshot from
the inputs the snapshot itself carries, and pins this session's research dossier to the
fixtures the deployed build leaves unpicked.  These tests hold the replay math to the
production formulas, prove the committed snapshot/site/dossier pass cleanly, and prove
that tampering with any of them is caught.
"""
from __future__ import annotations

import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path

verify = importlib.import_module('scripts.60019704_verify')

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / 'snapshot.json'
DOSSIER = ROOT / 'data' / 'research' / '60019704' / 'research.json'
DEPLOYED_AT = '2026-10-25T23:03:48Z'


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding='utf-8'))


class ReplayMathTests(unittest.TestCase):
    def test_valve_expectation_matches_production_formula(self) -> None:
        # Rooster (718) vs Abyssal (734), published as [0.47761494, 0.52238506].
        p0, p1 = verify.valve_expectation(718, 734)
        self.assertAlmostEqual(p0, 0.47761494, places=8)
        self.assertAlmostEqual(p1, 0.52238506, places=8)
        self.assertAlmostEqual(p0 + p1, 1.0, places=12)

    def test_valve_expectation_symmetry_and_ordering(self) -> None:
        a = verify.valve_expectation(1000, 900)
        b = verify.valve_expectation(900, 1000)
        self.assertAlmostEqual(a[0], b[1], places=12)
        self.assertGreater(a[0], 0.5)
        self.assertLess(b[0], 0.5)

    def test_no_vig_matches_published_bookmaker_row(self) -> None:
        # NEXVOID vs Alter Ego, Thunderpick odds 1.61/2.18, published as
        # [0.57519789, 0.42480211].
        inv = [1 / 1.61, 1 / 2.18]
        s = sum(inv)
        self.assertAlmostEqual(inv[0] / s, 0.57519789, places=8)
        self.assertAlmostEqual(inv[1] / s, 0.42480211, places=8)

    def test_midpoint_and_spread_ceiling(self) -> None:
        self.assertAlmostEqual((0.82 + 0.92) / 2, 0.87, places=12)
        self.assertLessEqual(0.92 - 0.82, verify.MAX_SPREAD)


class DeployedBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = verify.verify(SNAPSHOT, ROOT)

    def test_committed_build_passes_cleanly(self) -> None:
        self.assertEqual(self.report['errors'], [])
        self.assertTrue(self.report['ok'])
        # 10 open rows, 9 priced, 1 unresolved, 219+ structural checks.
        self.assertGreaterEqual(self.report['checks'], 200)

    def test_deployed_snapshot_is_the_reviewed_one(self) -> None:
        snap = load_snapshot()
        self.assertEqual(snap['generated_at'], DEPLOYED_AT)
        self.assertEqual(snap['counts']['unresolved'], 1)
        self.assertEqual(snap['counts']['picks'], 9)


class TamperDetectionTests(unittest.TestCase):
    """Each mutation must be caught by the replay (written to a temp copy)."""

    def verify_snapshot(self, mutate) -> list[str]:
        snap = load_snapshot()
        mutate(snap)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshot.json'
            path.write_text(json.dumps(snap), encoding='utf-8')
            site = ROOT  # pages are only checked for ids that still exist
            return verify.verify(path, site)['errors']

    @staticmethod
    def row(snap: dict, mid: str) -> dict:
        return next(m for m in snap['matches'] if str(m['id']) == mid)

    def test_probability_tampering_is_caught(self) -> None:
        def bump(snap):
            row = self.row(snap, '1082858')
            row['analysis']['probabilities'] = [0.3, 0.7]
        errors = self.verify_snapshot(bump)
        self.assertTrue(any('1082858' in e and ('midpoint' in e or 'probability' in e) for e in errors))

    def test_market_spread_ceiling_breach_is_caught(self) -> None:
        def widen(snap):
            row = self.row(snap, '1082858')
            for q in row['analysis']['quotes']:
                q['bid'], q['ask'] = 0.05, 0.95
                q['midpoint'] = 0.5
                q['spread'] = 0.9
            row['analysis']['probabilities'] = [0.5, 0.5]
        errors = self.verify_snapshot(widen)
        self.assertTrue(any('ceiling' in e for e in errors))

    def test_hotspawn_probability_attribution_is_caught(self) -> None:
        def rehost(snap):
            row = self.row(snap, '1082860')
            row['analysis']['source_url'] = 'https://play.hotspawn.com/lobby'
        errors = self.verify_snapshot(rehost)
        self.assertTrue(any('play.hotspawn.com' in e or 'non-official' in e for e in errors))

    def test_crowd_leak_into_analysis_is_caught(self) -> None:
        def leak(snap):
            row = self.row(snap, '1082861')
            row['analysis']['percent_picked'] = [0.91, 0.09]
        errors = self.verify_snapshot(leak)
        self.assertTrue(any('crowd' in e for e in errors))

    def test_dropping_the_unresolved_limitation_is_caught(self) -> None:
        def strip(snap):
            row = self.row(snap, '1082792')
            row['limitations'] = ['Hotspawn best-of format is unverified; left blank.']
        errors = self.verify_snapshot(strip)
        self.assertTrue(any('identity limitation' in e or 'does not state' in e for e in errors))

    def test_pricing_the_unresolved_row_without_a_trail_is_caught(self) -> None:
        def fake(snap):
            row = self.row(snap, '1082792')
            row['analysis'] = {'method': 'market', 'probabilities': [0.87, 0.13],
                               'source_url': 'https://polymarket.com/event/cs2-hotu-the9-2026-10-31',
                               'quotes': [{'bid': 0.82, 'ask': 0.92, 'midpoint': 0.87, 'spread': 0.1},
                                          {'bid': 0.08, 'ask': 0.18, 'midpoint': 0.13, 'spread': 0.1}]}
        errors = self.verify_snapshot(fake)
        # Faking a price breaks the declared counts (unresolved 1 -> 0).
        self.assertTrue(any('counts.unresolved' in e for e in errors))


class DossierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dossier = json.loads(DOSSIER.read_text(encoding='utf-8'))
        cls.snap = load_snapshot()

    def test_covers_exactly_the_unpicked_fixtures(self) -> None:
        covered = {str(f['hotspawn_id']) for f in self.dossier['fixtures']}
        self.assertIn('1082792', covered)
        priced = {str(m['id']) for m in self.snap['matches']
                  if m.get('availability') == 'open' and m.get('analysis')}
        self.assertFalse(covered & priced)
        snapshot_ids = {str(m['id']) for m in self.snap['matches']}
        additions = covered - {'1082792'}
        self.assertEqual(len(additions), 9)
        self.assertFalse(additions & snapshot_ids)

    def test_every_observation_is_sourced_and_timed(self) -> None:
        for f in self.dossier['fixtures']:
            for src, obs in f['findings'].items():
                if isinstance(obs, dict):
                    self.assertTrue(obs.get('url') or obs.get('base') or obs.get('api_url'),
                                    f"{f['hotspawn_id']}/{src} lacks a URL")
                    self.assertRegex(obs.get('observed_at', ''), r'^2026-10-26T\d\d:\d\dZ$',
                                     f"{f['hotspawn_id']}/{src} lacks a UTC read time")

    def test_no_hotspawn_probability_usage(self) -> None:
        # Crowd fields must always be labelled non-probability, and Hotspawn URLs may
        # only appear as inventory evidence, never as a probability source.
        text = json.dumps(self.dossier)
        for key in ('percent_picked', 'picked'):
            for idx in [m.start() for m in __import__('re').finditer(key, text)]:
                window = text[max(0, idx - 200):idx + 200]
                if 'note' not in window and 'NOT' not in window and 'crowd' not in window.lower():
                    self.fail(f'crowd field {key} appears without a non-probability note')
        for f in self.dossier['fixtures']:
            for src, obs in f['findings'].items():
                if isinstance(obs, dict):
                    url = obs.get('url') or ''
                    if 'hotspawn.com' in url:
                        self.fail(f"{f['hotspawn_id']}/{src} attributes evidence to Hotspawn")

    def test_valve_rows_recorded_verbatim_for_model_blocked_teams(self) -> None:
        brute = next(f for f in self.dossier['fixtures'] if str(f['hotspawn_id']) == '1079203')
        rows = brute['findings']['valve']['BRUTE']['rows']
        self.assertEqual([(r['standing'], r['points']) for r in rows], [(75, 1116), (218, 689)])
        huns = next(f for f in self.dossier['fixtures'] if str(f['hotspawn_id']) == '1082792')
        rows = huns['findings']['valve']['The Huns']['rows']
        self.assertEqual([(r['standing'], r['points']) for r in rows], [(122, 944), (213, 701)])

    def test_polymarket_series_books_recorded_for_the_two_key_fixtures(self) -> None:
        mzp = next(f for f in self.dossier['fixtures'] if str(f['hotspawn_id']) == '1079203')
        series = mzp['findings']['polymarket']['series']
        self.assertEqual((series['best_bid'], series['best_ask']), (0.59, 0.60))
        hotu = next(f for f in self.dossier['fixtures'] if str(f['hotspawn_id']) == '1082792')
        series = hotu['findings']['polymarket']['series']
        self.assertEqual((series['best_bid'], series['best_ask'], series['spread']), (0.82, 0.92, 0.1))

    def test_flags_carry_evidence_links(self) -> None:
        for flag in self.dossier['cross_source_flags']:
            self.assertTrue(flag['id'] and flag['title'] and flag['detail'])
            self.assertTrue(all(u.startswith('http') for u in flag['evidence']))


if __name__ == '__main__':
    unittest.main()
