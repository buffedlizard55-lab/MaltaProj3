"""Session 4c972a51 — an exactly even research estimate still gets a side.

The brief asks for a pick on every match Hotspawn lists. Some low-tier fixtures
have no reachable market, no esportsbook price and no Valve roster, so the last
rung is a model built from published ranking points. When both teams carry
exactly the same published points the estimate is exactly 50/50 and the
selection function returns no side.

These tests pin the narrow rule that gives such a row a direction from the
provider's own published order:

* only a research-model quote can be tie-broken (a money line never is);
* only an exactly even estimate can be tie-broken;
* both sides must have a different, positive published rank;
* no probability changes — the estimate stays 50/50 and the pick is labelled;
* a quote without ranks keeps its honest blank side.

No network is contacted and no probability is invented here.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from scripts.originate import originate_match, ranked_tie_break, selection


def hltv_quote(points=(2.0, 2.0), ranks=(215, 229), names=('Isurus', 'Hacha')):
    return {
        'provider': 'HLTV world ranking',
        'family': 'model',
        'probabilities': [0.5, 0.5],
        'fair_decimal': [2.0, 2.0],
        'source_url': 'https://www.hltv.org/ranking/teams',
        'inputs': [
            {'name': names[0], 'points': points[0], 'rank': ranks[0],
             'source_url': 'https://www.hltv.org/ranking/teams'},
            {'name': names[1], 'points': points[1], 'rank': ranks[1],
             'source_url': 'https://www.hltv.org/ranking/teams'},
        ],
    }


def fixture():
    return {
        'id': '1082926',
        'teams': [{'id': '1', 'name': 'Isurus'}, {'id': '2', 'name': 'Hacha'}],
        'competition': 'CCT South America 2026 Series #7',
        'starts_at': '2026-10-22T18:00:00Z',
        'source_url': 'https://www.hotspawn.com/matches/x-1082926',
        'lobby_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1082926',
        'availability': 'open',
    }


def registry():
    return {'aliases': []}


class RankedTieBreak(unittest.TestCase):
    def test_equal_points_use_the_published_order(self):
        result = ranked_tie_break(hltv_quote())
        self.assertIsNotNone(result)
        winner, record = result
        self.assertEqual(winner, 0)  # 215 is ranked above 229
        self.assertEqual(record['ranks'], [215, 229])
        self.assertIn('exactly 50.0%', record['detail'])
        self.assertIn('does not change either probability', record['detail'])

    def test_second_side_wins_when_it_is_ranked_higher(self):
        winner, _ = ranked_tie_break(hltv_quote(ranks=(300, 229)))
        self.assertEqual(winner, 1)

    def test_a_money_line_is_never_tie_broken(self):
        quote = hltv_quote()
        quote['family'] = 'market'
        self.assertIsNone(ranked_tie_break(quote))

    def test_an_uneven_estimate_is_not_touched(self):
        quote = hltv_quote()
        quote['probabilities'] = [0.52, 0.48]
        self.assertIsNone(ranked_tie_break(quote))
        self.assertEqual(selection(quote['probabilities']), 0)

    def test_missing_or_equal_ranks_leave_the_blank(self):
        self.assertIsNone(ranked_tie_break(hltv_quote(ranks=(None, 229))))
        self.assertIsNone(ranked_tie_break(hltv_quote(ranks=(229, 229))))
        quote = hltv_quote()
        quote['inputs'] = []
        self.assertIsNone(ranked_tie_break(quote))

    def test_equal_selection_still_returns_no_side_on_its_own(self):
        # The rule lives beside selection(), not inside it: a raw 50/50 pair has
        # no direction, and every caller that does not opt in stays unchanged.
        self.assertIsNone(selection([0.5, 0.5]))


class OriginateMatchUsesTheTieBreak(unittest.TestCase):
    def run_fixture(self, hltv_rows):
        return originate_match(
            fixture(), poly_rows=[], book_rows=[], ratings=[], valve_meta={},
            registry=registry(), now=datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc),
            hltv=None, hltv_rank=hltv_rows,
            hltv_meta={'snapshot_date': '2026-10-22', 'source_url': 'https://www.hltv.org/ranking/teams'},
            relay=[])

    def test_even_estimate_gets_a_labelled_side(self):
        rows = [
            {'name': 'Isurus', 'points': 2.0, 'rank': 215, 'source_url': 'https://www.hltv.org/ranking/teams'},
            {'name': 'Hacha', 'points': 2.0, 'rank': 229, 'source_url': 'https://www.hltv.org/ranking/teams'},
        ]
        record = self.run_fixture(rows)
        self.assertEqual(record['pick_index'], 0)
        self.assertEqual(record['origination']['probabilities'], [0.5, 0.5])
        self.assertEqual(record['origination']['tie_break']['ranks'], [215, 229])
        stages = [r['stage'] for r in record['research']]
        self.assertIn('Tie-break (published ranking order)', stages)
        self.assertTrue(any('50.0%' in note for note in record['limitations']))

    def test_even_estimate_without_ranks_stays_blank(self):
        rows = [
            {'name': 'Isurus', 'points': 0.0, 'rank': None, 'source_url': 'https://www.hltv.org/ranking/teams'},
            {'name': 'Hacha', 'points': 0.0, 'rank': None, 'source_url': 'https://www.hltv.org/ranking/teams'},
        ]
        record = self.run_fixture(rows)
        self.assertIsNone(record['pick_index'])
        self.assertNotIn('tie_break', record['origination'] or {})


if __name__ == '__main__':
    unittest.main()
