"""Regression: replay the narrowly sourced 50/50 research-model tie-break.

Live run 39761793313 failed the pre-existing origination validator because
`ranked_tie_break()` correctly chose the higher published HLTV rank on an
exactly even Valve/HLTV model, but `build_origination` compared pick_index to
`selection()` alone. This test ensures the audit accepts only the matching,
replayed source record and never tie-breaks an external money quote.
"""
import unittest

from scripts.build_origination import replay_pick_index
from scripts.originate import ranked_tie_break


class TieBreakReplayTests(unittest.TestCase):
    def quote(self):
        return {
            "provider": "HLTV world ranking",
            "family": "model",
            "method": "model",
            "probabilities": [0.5, 0.5],
            "source_url": "https://www.hltv.org/ranking/teams",
            "inputs": [
                {"name": "Isurus", "rank": 215, "points": 2.0,
                 "source_url": "https://www.hltv.org/ranking/teams"},
                {"name": "Hacha", "rank": 229, "points": 2.0,
                 "source_url": "https://www.hltv.org/ranking/teams"},
            ],
        }

    def test_exact_model_tie_replays_the_published_rank_direction_without_changing_probabilities(self):
        q = self.quote()
        winner, record = ranked_tie_break(q)
        q["tie_break"] = record
        self.assertEqual(replay_pick_index(q), winner)
        self.assertEqual(q["probabilities"], [0.5, 0.5])
        self.assertEqual(record["rule"], "published-rank tie-break")
        self.assertEqual(record["ranks"], [215, 229])

    def test_model_tie_without_the_record_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "tie-break differs"):
            replay_pick_index(self.quote())

    def test_tampered_or_fabricated_tie_record_is_rejected(self):
        q = self.quote()
        _winner, record = ranked_tie_break(q)
        q["tie_break"] = dict(record, winner=1)
        with self.assertRaisesRegex(AssertionError, "tie-break differs"):
            replay_pick_index(q)
        money = self.quote()
        money["family"] = "market"
        money["provider"] = "Polymarket"
        money["tie_break"] = record
        with self.assertRaisesRegex(AssertionError, "Unsupported or fabricated"):
            replay_pick_index(money)

    def test_tied_money_line_stays_without_a_direction(self):
        money = self.quote()
        money["family"] = "market"
        money["provider"] = "Polymarket"
        self.assertIsNone(replay_pick_index(money))


if __name__ == "__main__":
    unittest.main()
