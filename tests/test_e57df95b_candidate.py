from __future__ import annotations

import hashlib
import json
import math
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import network_model, reference_odds
from scripts import e57df95b_verify_candidate as audit

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "data/research/e57df95b"
UTC = timezone.utc


def read(name: str):
    return json.loads((SESSION / name).read_text(encoding="utf-8"))


class IndependentFormulaChecks(unittest.TestCase):
    def test_valve_expectation_matches_published_rd75_example(self):
        expected = audit.expectation(810, 1015, 75)
        self.assertAlmostEqual(expected[0], 0.24085429, places=8)
        self.assertAlmostEqual(sum(expected), 1.0)
        self.assertAlmostEqual(audit.glicko_g(75), 0.9728209910486895, places=15)

    def test_kalshi_array_books_are_normalized_midpoints(self):
        orig = {"quotes": [{"bid": [0.73, 0.17], "ask": [0.83, 0.24]}]}
        actual, _ = audit.money_replay(orig)
        self.assertAlmostEqual(actual[0], 0.7918781725888325, places=12)
        self.assertAlmostEqual(actual[1], 0.2081218274111675, places=12)

    def test_thunderpick_prices_remove_margin_proportionally(self):
        actual, _ = audit.money_replay({"quotes": [{"odds": [1.61, 2.18]}]})
        self.assertAlmostEqual(actual[0], 0.5751978891820581, places=12)
        self.assertAlmostEqual(actual[1], 0.4248021108179419, places=12)

    def test_crossed_or_wide_books_fail_closed(self):
        for quotes in (
            [{"bid": [0.8, 0.2], "ask": [0.7, 0.3]}],
            [{"bid": [0.1, 0.8], "ask": [0.5, 0.9]}],
        ):
            with self.subTest(quotes=quotes), self.assertRaises(ValueError):
                audit.money_replay({"quotes": quotes})

    def test_nine_series_form_refit(self):
        results = [
            (772, True), (1025, False), (1100, False), (862, False),
            (926, False), (1044, True), (911, False), (772, True), (1100, False),
        ]
        samples = [{"opponent_points": points, "won": won} for points, won in results]
        self.assertEqual(audit.fit_form(samples),
                         {"points": 835, "prior_center": 926, "n": 9, "posterior_sd": 119.1})

    def test_network_refit_parity_and_tamper_refusal(self):
        edges = [
            {"id": "a", "date": "2026-10-20", "a": 1, "b": 2, "winner": 1,
             "a_name": "Anchor A", "b_name": "Anchor B", "url": "https://bo3.gg/matches/a"},
            {"id": "b", "date": "2026-10-21", "a": 2, "b": 3, "winner": 2,
             "a_name": "Anchor B", "b_name": "New Team", "url": "https://bo3.gg/matches/b"},
            {"id": "c", "date": "2026-10-22", "a": 1, "b": 3, "winner": 3,
             "a_name": "Anchor A", "b_name": "New Team", "url": "https://bo3.gg/matches/c"},
        ]
        ratings = [{"name": "Anchor A", "points": 1000}, {"name": "Anchor B", "points": 900}]
        document = network_model.build(edges, ratings, datetime(2026, 10, 24, tzinfo=UTC))
        proof = audit.refit_network(document)
        self.assertEqual(proof["series_refit"], 3)
        document["edges"][0]["weight"] = 0.01
        with self.assertRaisesRegex(ValueError, "hash"):
            audit.refit_network(document)


class RetainedEvidenceChecks(unittest.TestCase):
    def test_official_valve_download_hashes(self):
        metadata = json.loads((SESSION / "evidence/valve-retrieval.json").read_text())
        self.assertGreaterEqual(len(metadata["files"]), 3)
        for row in metadata["files"]:
            payload = (SESSION / "evidence" / row["saved_as"]).read_bytes()
            self.assertEqual(len(payload), row["size"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), row["sha256"])
            self.assertTrue(row["source_url"].startswith(
                "https://github.com/ValveSoftware/counter-strike_regional_standings/"))

    def test_all_25_candidate_rows_pass_and_link_external_sources(self):
        report = read("candidate-audit.json")
        summary = report["summary"]
        self.assertEqual(summary["audited"], 25)
        self.assertEqual(summary["passed"], 25)
        self.assertEqual(summary["failed"], 0)
        self.assertTrue(summary["exact_live_id_set_match"])
        self.assertEqual(summary["featured_unresolved_ids"], ["1081156", "1082858", "1082792"])
        self.assertEqual(len({row["id"] for row in report["rows"]}), 25)
        for row in report["rows"]:
            self.assertTrue(row["source_url"].startswith("https://"))
            self.assertNotIn("hotspawn.com", row["source_url"])
            self.assertLessEqual(row["arithmetic"]["max_abs_delta"], 5.1e-8)
            self.assertGreater(row["probabilities"][row["pick_index"]],
                               row["probabilities"][1 - row["pick_index"]])

    def test_final_integrated_candidate_uses_the_reviewed_reference(self):
        report = read("final-candidate-audit.json")
        self.assertEqual(report["summary"]["failed"], 0)
        self.assertEqual(report["summary"]["methods"],
                         {"bookmaker": 2, "market": 13, "model": 9, "reference": 1})
        row = next(row for row in report["rows"] if row["id"] == "1082858")
        self.assertEqual(row["method"], "reference")
        self.assertEqual(row["pick"], "Off Chops")
        self.assertEqual(row["probabilities"], [0.26495726, 0.73504274])
        self.assertEqual(row["status"], "pass")

    def test_hltv_review_covers_exactly_the_ten_model_rows(self):
        report = read("candidate-audit.json")
        review = read("hltv-review.json")
        model_ids = {row["id"] for row in report["rows"] if row["method"] == "model"}
        self.assertEqual({row["fixture_id"] for row in review["fixtures"]}, model_ids)
        for row in review["fixtures"]:
            self.assertTrue(row["identity_format_verified"])
            self.assertTrue(row["format"].startswith("Best of 3"))
            self.assertFalse(row["fan_vote_used"])
            self.assertIsNone(row["start_display_timezone"])
            self.assertIn("no two-sided bookmaker decimal prices", row["betting_section"])

    def test_line_review_has_nine_placeholders_and_one_real_aggregate(self):
        review = read("line-source-review.json")
        self.assertEqual(len(review["entries"]), 10)
        placeholders = [row for row in review["entries"] if row.get("displayed_decimal_odds") == [1.8, 1.8]]
        self.assertEqual(len(placeholders), 9)
        self.assertTrue(all(not row["qualified"] for row in placeholders))
        lead = next(row for row in review["entries"] if row["fixture_id"] == "1082858")
        self.assertEqual(lead["displayed_decimal_odds"], [3.44, 1.24])
        self.assertFalse(lead["smarkets_crosscheck"]["qualified"])
        self.assertTrue(all(x > 0.15 for x in lead["smarkets_crosscheck"]["spreads"]))

    def test_reference_capture_replays_and_expires(self):
        capture = read("reference-odds.json")["entries"][0]
        self.assertEqual(reference_odds.problems(capture), [])
        match = {"id": "1082858", "starts_at": "2026-10-26T03:00:00Z",
                 "teams": [{"name": "Ground Zero"}, {"name": "Off Chops"}]}
        quote, _ = reference_odds.quote(capture, match, datetime(2026, 10, 24, 6, 35, tzinfo=UTC))
        self.assertIsNotNone(quote)
        self.assertEqual(quote["probabilities"], [0.26495726, 0.73504274])
        reference_odds.replay(capture, quote)
        stale, reason = reference_odds.quote(capture, match, datetime(2026, 10, 24, 14, 30, tzinfo=UTC))
        self.assertIsNone(stale)
        self.assertIn("older than eight hours", reason)
        self.assertAlmostEqual(1 / 3.44 / (1 / 3.44 + 1 / 1.24), quote["probabilities"][0], places=8)


if __name__ == "__main__":
    unittest.main()
