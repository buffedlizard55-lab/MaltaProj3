"""Regression tests for the dated upset review and conservative watch layer."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import contrarian_review
from scripts.contrarian import derive_context, load_review, validate_context, validate_review_shape


class ContrarianReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path("data/latest.json").read_text())
        cls.review = load_review(Path("data/contrarian.json"))
        cls.context = derive_context(cls.data, cls.review)

    def test_historical_upset_and_roster_context_are_source_linked(self):
        historical = self.context["historical"]
        self.assertEqual(historical["result"]["winner"], "9z")
        self.assertEqual(historical["result"]["series_score"], "2-0")
        self.assertEqual(historical["pre_match_pick"], "Aurora")
        self.assertGreaterEqual(len(historical["source_urls"]), 4)
        self.assertIn("kyxsan", self.context["roster"]["new_players"])
        self.assertIn("Jimpphat", self.context["roster"]["new_players"])
        self.assertTrue(self.context["roster"]["source_urls"])

    def test_current_watch_is_an_underdog_context_not_a_pick_override(self):
        # The watch is derived from the checked-in snapshot. When the 9z–Falcons
        # fixture is no longer listed (session 7293b310: the tournament finished)
        # the honest state is "no current watch"; the safety policy is checked
        # either way and never weakened.
        current = self.context["current"]
        validate_context(self.data, self.context)
        self.assertFalse(self.context["policy"]["watch_is_a_pick"])
        self.assertTrue(self.context["policy"]["do_not_flip_primary_pick"])
        if current["status"] == "contrarian-watch":
            self.assertNotEqual(current["watch_team"], current["primary_pick"])
            self.assertLessEqual(current["watch_probability"], 0.25)
            self.assertIn("model", current["primary_method"])
            self.assertEqual(current["match_id"], str(current["match_id"]))
        else:
            self.assertEqual(current["status"], "no-current-watch")
            # No fixture carries the watch in this snapshot: the historical team
            # name may stay as context, but there is no match, no probability and
            # no primary pick, so nothing can be read as a pick override.
            self.assertIsNone(current["match_id"])
            self.assertIsNone(current["watch_probability"])
            self.assertIsNone(current["primary_pick"])
            self.assertEqual(current["teams"], [])

    def test_changed_canonical_probability_cannot_pass_as_a_watch(self):
        if self.context["current"]["status"] != "contrarian-watch":
            self.skipTest("no current watch in this snapshot; the tamper check needs one")
        changed = copy.deepcopy(self.data)
        match = next(m for m in changed["matches"] if m["id"] == self.context["current"]["match_id"])
        match["analysis"]["probabilities"][0] = 0.31
        with self.assertRaises(ValueError):
            validate_context(changed, self.context)

    def test_homepage_section_has_sources_on_every_review_row(self):
        data = copy.deepcopy(self.data)
        data["_contrarian"] = self.context
        soup = BeautifulSoup(contrarian_review(data, "./"), "html.parser")
        rows = soup.select("#contrarian tbody tr")
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertTrue(row.select("a[href^='https://']"), row.get_text(" ", strip=True))
        text = soup.get_text(" ", strip=True)
        current = self.context["current"]
        if current["status"] == "contrarian-watch":
            self.assertIn(f"{current['watch_probability'] * 100:.1f}%", text)
            self.assertIn(f"primary pick remains {current['primary_pick']}", text)
        else:
            self.assertIn("No current exact-pair watch", text)
            self.assertIn("The primary pick engine remains authoritative", text)

    def test_review_shape_rejects_hotspawn_popularity_as_a_signal(self):
        altered = copy.deepcopy(self.review)
        altered["policy"]["hotspawn_popularity_used"] = True
        with self.assertRaises(ValueError):
            validate_review_shape(altered)


if __name__ == "__main__":
    unittest.main()
