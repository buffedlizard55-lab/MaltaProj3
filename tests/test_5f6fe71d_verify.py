"""Session arena-5f6fe71d — the independent verifier's own arithmetic is pinned.

`scripts/verify_5f6fe71d.py` re-implements the published methodology formulas a
second time so the published numbers are checked by an independent path. If the
verifier's formulas were wrong, every verdict it prints would be wrong too, so
these tests pin the verifier itself: known-value arithmetic, the featured and
fallback quote shapes, and the row stage's pass/blank/fail verdicts. No network
access, no live evidence.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import verify_5f6fe71d as v


class FormulaTest(unittest.TestCase):
    def test_midpoint_normalisation_matches_the_methodology_example(self):
        # m = (bid + ask) / 2 per outcome, P(A) = mA / (mA + mB), rounded to 8.
        self.assertEqual(v.norm_pair(0.60, 0.40), [0.6, 0.4])
        self.assertEqual(v.recalc_market({'bid': [0.58, 0.38], 'ask': [0.62, 0.42]}), [0.6, 0.4])

    def test_devig_removes_proportional_margin(self):
        self.assertEqual(v.recalc_odds_pair({'odds': [2.0, 2.0]}), [0.5, 0.5])
        # 1/1.5 = 0.666..., 1/2.7 = 0.37037...; sum 1.037 -> normalised pair.
        pair = v.recalc_odds_pair({'odds': [1.5, 2.7]})
        self.assertAlmostEqual(pair[0], (1 / 1.5) / (1 / 1.5 + 1 / 2.7), places=8)
        self.assertAlmostEqual(sum(pair), 1.0, places=8)

    def test_glicko_expectation_is_even_and_monotone(self):
        self.assertAlmostEqual(v.glicko_expectation(1500, 1500), 0.5, places=12)
        self.assertGreater(v.glicko_expectation(1800, 1500), 0.5)
        self.assertLess(v.glicko_expectation(1500, 1800), 0.5)

    def test_hltv_logistic_from_published_points(self):
        quote = {'method': 'model', 'source': 'HLTV world ranking',
                 'inputs': [{'points': 100.0}, {'points': 0.0}]}
        expected, how = v.recalc_model(quote, None)
        self.assertEqual(how, 'hltv')
        self.assertAlmostEqual(expected[0], 1 / (1 + 10 ** (-0.25)), places=9)

    def test_consensus_is_the_componentwise_median(self):
        quotes = [{'probabilities': [0.70, 0.30]}, {'probabilities': [0.60, 0.40]},
                  {'probabilities': [0.66, 0.34]}]
        self.assertEqual(v.recalc_consensus(quotes), [0.66, 0.34])

    def test_featured_shapes(self):
        featured_market = {'method': 'market',
                           'quotes': [{'bid': 0.58, 'ask': 0.62}, {'bid': 0.38, 'ask': 0.42}]}
        self.assertEqual(v.recalc_featured(featured_market), [0.6, 0.4])
        featured_book = {'method': 'bookmaker', 'quotes': [{'odds': [2.0, 2.0]}]}
        self.assertEqual(v.recalc_featured(featured_book), [0.5, 0.5])


def _row(fixture_id, analysis=None, pick_index=None, availability='open'):
    return {'id': fixture_id, 'availability': availability,
            'teams': [{'name': 'Alpha'}, {'name': 'Beta'}],
            'competition': 'Test Cup', 'starts_at': '2026-10-22T12:00:00Z',
            'locks_at': '2026-10-22T11:54:00Z',
            'analysis': analysis, 'pick_index': pick_index}


class StageRowsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = Path(self.tmp.name)

    def _run(self, latest, origination):
        return v.stage_rows(latest, origination, self.data_dir)

    def test_featured_market_row_replays_exactly(self):
        analysis = {'method': 'market', 'label': 'Market-implied estimate',
                    'probabilities': [0.6, 0.4], 'event_id': '42',
                    'quotes': [{'bid': 0.58, 'ask': 0.62}, {'bid': 0.38, 'ask': 0.42}]}
        rows, failures = self._run({'matches': [_row('1', analysis, 0)]}, {'matches': []})
        self.assertEqual(rows[0]['verdict'], 'replay-pass')
        self.assertEqual(rows[0]['pick'], 'Alpha')
        self.assertEqual(failures, [])

    def test_tampered_probability_fails_the_row(self):
        analysis = {'method': 'market', 'probabilities': [0.99, 0.01],
                    'quotes': [{'bid': 0.58, 'ask': 0.62}, {'bid': 0.38, 'ask': 0.42}]}
        rows, failures = self._run({'matches': [_row('1', analysis, 0)]}, {'matches': []})
        self.assertEqual(rows[0]['verdict'], 'replay-fail')
        self.assertTrue(failures)

    def test_blank_row_is_recorded_as_unresolved_never_recomputed(self):
        rows, failures = self._run({'matches': [_row('1', None, None)]}, {'matches': []})
        self.assertEqual(rows[0]['verdict'], 'blank-published-as-unresolved')
        self.assertFalse(rows[0]['has_estimate'])
        self.assertEqual(failures, [])

    def test_researched_fallback_basis_is_selected_like_the_site(self):
        # A featured model estimate with a money-backed, marked upgrade displays
        # the fallback; the independent recompute must use the fallback quote.
        featured_model = {'method': 'model', 'probabilities': [0.55, 0.45],
                          'inputs': [{'points': 1500}, {'points': 1465}]}
        latest = {'matches': [_row('7', featured_model, 0)]}
        devigged = v.recalc_odds_pair({'odds': [2.7, 1.5]})  # [0.35714286, 0.64285714]
        origination = {'matches': [dict(_row('7', None, None),
                                        pick_index=1, upgraded_from_featured_model=True,
                                        origination={'method': 'bookmaker', 'source': 'Thunderpick',
                                                     'probabilities': devigged,
                                                     'quotes': [{'odds': [2.7, 1.5],
                                                                 'probabilities': devigged}]})]}
        rows, failures = self._run(latest, origination)
        self.assertEqual(rows[0]['basis'], 'researched-fallback')
        self.assertEqual(rows[0]['method'], 'bookmaker')
        self.assertEqual(rows[0]['verdict'], 'replay-pass')
        self.assertEqual(rows[0]['pick'], 'Beta')
        self.assertEqual(failures, [])


if __name__ == '__main__':
    unittest.main()
