"""Internal consistency checks for arena-52212e8e's final-integration dossier.

These tests pin dated review evidence; they do not reprice a fixture or treat a
manifest as a deployment-time original-evidence replay.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "data" / "research" / "52212e8e"


def load(name: str):
    return json.loads((DOSSIER / name).read_text(encoding="utf-8"))


class ReviewDossierTests(unittest.TestCase):
    def test_saved_evidence_replay_and_candidate_acceptance_are_distinct(self):
        report = load("fresh-25-replay.json")
        self.assertEqual(report["summary"]["replay_pass"], 25)
        self.assertEqual(report["summary"]["acceptance_problem_rows"], 1)
        self.assertFalse(report["summary"]["acceptance_clean"])
        flagged = [row for row in report["rows"] if "acceptance" in row]
        self.assertEqual([row["fixture_id"] for row in flagged], ["1082860"])
        row = flagged[0]
        self.assertEqual(row["raw_decimal_odds"], [1.001, 12])
        self.assertTrue(row["acceptance"].startswith("fail:"))
        self.assertTrue(row["replay"].startswith("pass:"))
        self.assertTrue(row["replay_with_pr237"].startswith("pass:"))

    def test_older_raw_quote_is_not_carried_into_the_31_row_manifest(self):
        report = load("latest-31-inventory-review.json")
        self.assertEqual(report["latest_manifest"]["active"], 31)
        crosscheck = report["price_precision_crosscheck"]
        self.assertEqual(crosscheck["match_id"], "1082860")
        self.assertEqual(crosscheck["raw_decimal_odds"], [1.001, 12])
        self.assertIn("25-row capture only", crosscheck["applies_to"])
        self.assertIn("deployment-time evidence replay", crosscheck["acceptance"])

    def test_regression_results_are_pinned_to_their_exact_heads(self):
        report = load("integration-review.json")
        findings = {item["id"]: item for item in report["integration_findings"]}
        regression = findings["S522-REGRESSION-001"]
        self.assertEqual(regression["head"], "013eed255e3386cf7fd99c56aa150829a75ab292")
        self.assertIn("1362 tests", regression["verification"])
        latest = regression["latest_head_check"]
        self.assertEqual(latest["head"], "8ed62fa2d05746243e981511b2a9b23de8a1abfd")
        self.assertEqual(latest["targeted_tests"], "213 passed, 2 skipped")
        self.assertIn("0 derived-only rows", latest["adversarial_egw"])

    def test_price_flag_requires_both_admission_and_source_fidelity(self):
        flags = load("flags.json")
        flag = next(item for item in flags
                    if item["id"] == "52212e8e-thunderpick-raw-price-is-1-001-not-1-00")
        self.assertEqual(flag["match_ids"], ["1082860"])
        self.assertIn("1.001 and 12", flag["detail"])
        self.assertIn("every decimal leg must be >1.01", flag["detail"])
        self.assertIn("not acceptance-clean", flag["detail"])
        self.assertTrue(any("c1152ed6" in url for url in flag["source_urls"]))

    def test_markdown_keeps_the_acceptance_qualification_visible(self):
        replay = (DOSSIER / "fresh-25-replay.md").read_text(encoding="utf-8")
        verification = (DOSSIER / "verification.md").read_text(encoding="utf-8")
        self.assertIn("not acceptance-clean", replay)
        self.assertIn("ACCEPTANCE FAIL", replay)
        self.assertIn("1,362 tests", verification)
        self.assertIn("213 targeted tests", verification)
        self.assertIn(">1.01", verification)


if __name__ == "__main__":
    unittest.main()
