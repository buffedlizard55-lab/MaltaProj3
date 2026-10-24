"""Internal consistency checks for arena-52212e8e's final-integration dossier.

These tests pin dated review evidence; they do not reprice a fixture or treat a
manifest as a deployment-time original-evidence replay.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import unittest

from scripts import reference_odds

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

    def test_c6b8_reference_entries_join_actual_inventory_not_themselves(self):
        report = load("c6b8-reference-integration-review.json")
        c6b8 = ROOT / "data" / "research" / "c6b8d58b"
        reference = json.loads((c6b8 / "reference-odds.json").read_text(encoding="utf-8"))
        coverage = json.loads((c6b8 / "live-coverage.json").read_text(encoding="utf-8"))
        inventory = {str(row["id"]): row for row in coverage["live_fixtures"]}
        now = datetime(2026, 10, 24, 7, 14, 33, tzinfo=timezone.utc)
        accepted, rejected = [], {}
        for entry in reference["entries"]:
            fixture = inventory[entry["fixture_id"]]
            match = {
                "id": fixture["id"],
                "teams": [{"name": name} for name in fixture["teams"]],
                "starts_at": fixture["starts_at"],
            }
            quote, reason = reference_odds.quote(entry, match, now)
            if quote:
                accepted.append(entry["fixture_id"])
            else:
                rejected[entry["fixture_id"]] = reason
        self.assertEqual(accepted, ["1083122", "1082861", "1082792"])
        self.assertEqual(
            set(rejected), {"1082858", "1082996", "1079198", "1079200"})
        self.assertTrue(all("Start time differs" in reason
                            for reason in rejected.values()))
        self.assertEqual(report["counts"]["exact_inventory_gate_accepts"], 3)
        self.assertEqual(report["counts"]["exact_inventory_gate_rejects"], 4)
        self.assertEqual(report["counts"]["direct_page_price_reverified"], 1)
        self.assertEqual(
            report["counts"]["gate_accepts_whose_linked_page_shows_placeholder"], 2)
        routing = report["current_residual_routing"]
        self.assertEqual(
            routing["direct_page_verified_candidate_not_deployed_by_this_audit"],
            ["1083122"])
        self.assertEqual(routing["exact_index_evidence_required_before_production"],
                         ["1082861", "1082792"])
        self.assertEqual(report["production_impact"]["probabilities_or_picks_changed"], 0)

    def test_c6b8_placeholder_irregularities_and_later_residual_state_are_visible(self):
        report = load("c6b8-reference-integration-review.json")
        rejected = report["rejected_placeholder_review"]
        mismatched = [row["fixture_id"] for row in rejected
                      if row["inventory_identity_differences"]]
        self.assertEqual(
            mismatched, ["1081153", "1081154", "1081156", "1081158", "1082793"])
        self.assertEqual(report["counts"]["rejected_placeholder_rows"], 6)
        self.assertEqual(
            report["counts"]["rejected_placeholder_rows_with_inventory_mismatch"], 5)
        latest = load("latest-31-inventory-review.json")
        later = latest["subsequent_c6b8_integration"]
        self.assertEqual(later["reference_entries"], 7)
        self.assertEqual(later["exact_inventory_gate_accepts"], 3)
        self.assertEqual(later["exact_inventory_gate_rejects"], 4)
        self.assertEqual(later["production_capture_paths_added"], 0)
        self.assertIn("2399914", later["hltv_match_pages_reconciled"])
        flags = load("flags.json")
        self.assertIn("52212e8e-c6b8-reference-start-mismatch",
                      {flag["id"] for flag in flags})
        markdown = (DOSSIER / "c6b8-reference-integration-review.md").read_text(
            encoding="utf-8")
        self.assertIn("only 3 exact-inventory gate accepts", markdown)
        self.assertIn("No production price or capture path was changed", markdown)

    def test_719_missing_card_counts_exclude_the_already_published_fifth_price(self):
        coverage = json.loads(
            (ROOT / "data" / "research" / "719a314a" /
             "live-coverage-2026-10-24.json").read_text(encoding="utf-8"))
        missing = [row for row in coverage["cards"]
                   if not row["in_published_snapshot"]]
        priced = [row for row in missing if row.get("reference_line")]
        unpriced = [row for row in missing if not row.get("reference_line")]
        self.assertEqual(len(missing), 9)
        self.assertEqual([row["hotspawn_id"] for row in priced],
                         ["1079658", "1079659", "1079660", "1079661"])
        self.assertEqual([row["hotspawn_id"] for row in unpriced],
                         ["1081152", "1081153", "1081154", "1081156", "1081158"])
        self.assertTrue(all(row["competition"].endswith("#12") for row in unpriced))
        all_priced = [row for row in coverage["cards"] if row.get("reference_line")]
        self.assertEqual(len(all_priced), 5)
        fifth = next(row for row in all_priced if row["hotspawn_id"] == "1079193")
        self.assertTrue(fifth["in_published_snapshot"])
        report = load("integration-review.json")
        finding = next(item for item in report["integration_findings"]
                       if item["id"] == "S522-COUNTS-001")
        self.assertEqual(finding["verified_details"]["missing_with_reference_line"], 4)
        self.assertEqual(finding["verified_details"]["missing_without_reference_line"], 5)
        flags = load("flags.json")
        self.assertIn("52212e8e-719-count-consistency",
                      {flag["id"] for flag in flags})

    def test_fresh31_retained_replay_has_full_links_but_one_acceptance_blocker(self):
        report = load("fresh-31-replay.json")
        summary = report["summary"]
        self.assertEqual(summary["active"], 31)
        self.assertEqual(summary["with_pick"], 31)
        self.assertEqual(summary["unresolved"], 0)
        self.assertEqual(summary["external_line"], 20)
        self.assertEqual(summary["research_model"], 11)
        self.assertEqual(summary["replay_pass"], 31)
        self.assertEqual(summary["missing_source_links"], 0)
        self.assertEqual(summary["acceptance_problem_rows"], 1)
        self.assertFalse(summary["acceptance_clean"])
        self.assertFalse(summary["deployed"])
        self.assertEqual(report["source_evidence"]["featured_evidence_files"], 75)
        self.assertEqual(report["source_evidence"]["origination_evidence_files"], 69)
        self.assertEqual(report["source_evidence"]["validator_head"],
                         "4b278f4e33499c669d7ab49d7ad9ca0e0cb70e7a")
        self.assertEqual(len(report["rows"]), 31)
        for row in report["rows"]:
            self.assertTrue(row["hotspawn_url"], row["fixture_id"])
            self.assertTrue(row["source_url"], row["fixture_id"])
            self.assertTrue(row["official_source_links"], row["fixture_id"])
            self.assertTrue(row["replay"].startswith("pass:"), row["fixture_id"])
        failed = [row for row in report["rows"] if row["validation_problems"]]
        self.assertEqual([row["fixture_id"] for row in failed], ["1082860"])
        self.assertEqual(failed[0]["raw_quotes"][0]["odds"], [1.001, 12])
        self.assertEqual(failed[0]["raw_quotes"][0]["observed_at"],
                         "2026-10-24T07:24:23Z")
        self.assertIn("every leg must be > 1.01", failed[0]["acceptance"])
        cd37 = load("fresh-31-cd37-reconciliation.json")
        self.assertEqual(cd37["counts"]["candidate_active"], 31)
        self.assertEqual(cd37["counts"]["validation_problem_rows"], 1)
        self.assertEqual(set(cd37["row_problems"]), {"1082860"})
        followup = report["residual_research_followup"]
        self.assertEqual(len(followup["current_model_ids"]), 11)
        self.assertEqual(followup["direct_page_candidate_not_deployed"], ["1083122"])
        old = load("fresh-25-replay.json")
        self.assertEqual(old["superseded_by_fresh_31"]["active"], 31)
        markdown = (DOSSIER / "fresh-31-replay.md").read_text(encoding="utf-8")
        self.assertIn("Acceptance: NOT CLEAN", markdown)
        self.assertIn("raw Thunderpick `1.001 / 12`", markdown)
        self.assertIn("Separate research-model limitations register", markdown)

    def test_inherited_pytest_suite_must_declare_the_runner_dependency(self):
        suite = ROOT / "tests" / "test_b97af12f_reconciliation.py"
        if not suite.is_file() or "import pytest" not in suite.read_text(encoding="utf-8"):
            return  # The suite was not inherited, or its owner made it unittest-only.
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        declared = any(line.strip().startswith("pytest")
                       for line in requirements.splitlines())
        workflow_installs = []
        for name in ("pages.yml", "checks.yml", "origination.yml"):
            text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
            workflow_installs.append(any(
                "pip install" in line and "pytest" in line
                for line in text.splitlines()))
        self.assertTrue(
            declared or all(workflow_installs),
            "B97 imports pytest, but the Pages/checks/origination runners do not install it")

    def test_dependency_blocker_and_local_workaround_are_not_conflated(self):
        flags = load("flags.json")
        flag = next(item for item in flags
                    if item["id"] == "52212e8e-b97-pytest-dependency")
        self.assertEqual(flag["severity"], "notice")
        self.assertIn("broken-check/deploy blocker", flag["detail"])
        self.assertIn("RESOLUTION verified", flag["detail"])
        self.assertEqual(flag["resolution"]["status"], "verified resolved")
        self.assertEqual(flag["resolution"]["head"],
                         "4b278f4e33499c669d7ab49d7ad9ca0e0cb70e7a")
        self.assertIn("no pytest", flag["resolution"]["clean_environment"])
        report = load("integration-review.json")
        finding = next(item for item in report["integration_findings"]
                       if item["id"] == "S522-TESTDEP-001")
        self.assertIn("85 targeted tests", finding["verification"])
        self.assertIn("ignored local virtualenv", finding["verification"])
        self.assertIn("92 targeted tests", finding["resolution"]["verification"])
        self.assertIn("does not resolve the separate 1082860", finding["resolution"]["verification"])

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
