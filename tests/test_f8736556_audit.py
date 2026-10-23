"""Session f8736556 audit invariants.

The audit is evidence only: it must not make a stale plain JSON URL pass via a
cache diagnostic, must not mutate the snapshots it reads, must only research
fixtures without an external money line, and must keep an unresolved fixture's
probability and pick blank.
"""
from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.f8736556_audit import (
    extract_page_stamp,
    public_summary_checks,
    publication_checks,
    render_audit_markdown,
    replay_probabilities,
    row_audit,
    select_targets,
)

ROOT = Path(__file__).resolve().parents[1]


class F8736556AuditTests(unittest.TestCase):
    def setUp(self):
        self.latest = json.loads((ROOT / "data/latest.json").read_text())
        self.complete = json.loads((ROOT / "data/origination.json").read_text())
        self.now = datetime.fromisoformat(
            self.latest["generated_at"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)

    def test_checked_in_snapshot_pair_has_plain_parity_at_its_own_clock(self):
        checks = publication_checks(
            self.latest["generated_at"], self.latest, self.complete, self.now
        )
        self.assertEqual([check["status"] for check in checks], ["pass"] * len(checks))

    def test_a_different_plain_latest_snapshot_fails_without_cache_credit(self):
        stale = copy.deepcopy(self.latest)
        stale["generated_at"] = "2026-10-15T08:36:13Z"
        checks = publication_checks(
            "2026-10-23T09:23:57Z", stale, self.complete, self.now
        )
        first = next(
            check
            for check in checks
            if check["key"] == "page_and_plain_latest_are_one_snapshot"
        )
        self.assertEqual(first["status"], "fail")

    def test_page_stamp_is_read_from_the_rendered_body_contract(self):
        stamp = extract_page_stamp(
            b'<body data-snapshot-generated="2026-10-23T09:23:57Z">x</body>'
        )
        self.assertEqual(stamp, "2026-10-23T09:23:57Z")

    def test_checked_in_rows_join_line_by_line_without_mutating_inputs(self):
        latest_before = copy.deepcopy(self.latest)
        complete_before = copy.deepcopy(self.complete)
        audit = row_audit(self.latest, self.complete)
        self.assertEqual(self.latest, latest_before)
        self.assertEqual(self.complete, complete_before)
        self.assertEqual(audit["active_inventory_rows"], 17)
        self.assertEqual(audit["complete_pick_rows"], 17)
        self.assertEqual(audit["directional_picks"], 17)
        self.assertEqual(audit["external_line_rows"], 12)
        self.assertEqual(audit["research_model_rows"], 5)
        self.assertEqual(audit["unresolved_rows"], 0)
        self.assertEqual(audit["probability_replay_pass_rows"], 17)
        self.assertEqual(audit["probability_replay_failed_rows"], 0)
        self.assertEqual(audit["rows_with_problems"], 0)
        self.assertEqual(audit["global_problems"], [])

    def test_probability_replay_recomputes_retained_quotes_and_catches_drift(self):
        bookmaker = next(
            row["origination"]
            for row in self.complete["matches"]
            if (row.get("origination") or {}).get("method") == "bookmaker"
            and (row["origination"].get("quotes") or [{}])[0].get("odds")
        )
        replay = replay_probabilities(bookmaker)
        self.assertEqual(replay["status"], "pass", replay)
        self.assertLessEqual(replay["max_abs_difference"], 2e-6)

        drifted = copy.deepcopy(bookmaker)
        drifted["probabilities"] = [0.51, 0.49]
        drifted["fair_decimal"] = [round(1 / 0.51, 3), round(1 / 0.49, 3)]
        replay = replay_probabilities(drifted)
        self.assertEqual(replay["status"], "fail")
        self.assertTrue(any("retained-evidence replay" in p for p in replay["problems"]))

        model = next(
            row["origination"]
            for row in self.complete["matches"]
            if (row.get("origination") or {}).get("method") == "model"
        )
        self.assertEqual(replay_probabilities(model)["status"], "pass")
        self.assertEqual(replay_probabilities(None)["status"], "not-applicable")

    def test_missing_complete_row_and_identity_drift_are_visible(self):
        missing = copy.deepcopy(self.complete)
        removed = missing["matches"].pop()
        audit = row_audit(self.latest, missing)
        removed_row = next(row for row in audit["rows"] if row["hotspawn_id"] == str(removed["id"]))
        self.assertEqual(removed_row["state"], "unresolved")
        self.assertTrue(any("missing from complete-picks" in p for p in removed_row["problems"]))

        drifted = copy.deepcopy(self.complete)
        drifted["matches"][0]["teams"][0]["name"] = "Invented Name"
        audit = row_audit(self.latest, drifted)
        row = next(
            item
            for item in audit["rows"]
            if item["hotspawn_id"] == str(drifted["matches"][0]["id"])
        )
        self.assertTrue(any(p.startswith("teams differs") for p in row["problems"]))

    def test_unresolved_remains_blank_and_only_non_money_rows_are_targets(self):
        complete = copy.deepcopy(self.complete)
        row = complete["matches"][0]
        row["origination"] = None
        row["pick_index"] = None
        audit = row_audit(self.latest, complete)
        audited = next(item for item in audit["rows"] if item["hotspawn_id"] == str(row["id"]))
        self.assertIsNone(audited["probabilities"])
        self.assertIsNone(audited["pick_index"])
        self.assertIsNone(audited["pick"])
        targets = select_targets(audit)
        self.assertIn(str(row["id"]), {target["id"] for target in targets})
        for target in targets:
            source = next(item for item in audit["rows"] if item["hotspawn_id"] == target["id"])
            self.assertNotEqual(source["state"], "external-line")

    def test_public_summary_contract_requires_exact_glance_ids_and_mobile_pick_link(self):
        html = b"""
        <html><head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"></head>
        <body><section id=\"picks-at-a-glance\">
          <li class=\"glance-row\" data-glance-id=\"1\"></li>
          <li class=\"glance-row\" data-glance-id=\"2\"></li>
        </section><section id=\"unresolved-register\"></section>
        <a href=\"./origination/#picks\">All picks</a>
        <a href=\"./unresolved/\">Unresolved</a>
        <a href=\"./methodology/\">Methodology</a>
        <a href=\"./coverage/\">Coverage</a>
        <a href=\"./review/\">Review</a>
        <nav class=\"mobile-nav\"><a href=\"./origination/#picks\">Picks</a></nav>
        </body></html>
        """
        checks = public_summary_checks(html, ["1", "2"])
        self.assertTrue(checks["glance_ids_match_active_inventory"])
        self.assertTrue(checks["mobile_nav_links_to_all_picks"])
        self.assertTrue(all(checks["links"].values()))

    def test_markdown_names_current_pick_destinations_and_keeps_blanks_blank(self):
        complete = copy.deepcopy(self.complete)
        complete["matches"][0]["origination"] = None
        complete["matches"][0]["pick_index"] = None
        audit = row_audit(self.latest, complete)
        report = {
            "observed_at": "2026-10-23T10:00:00Z",
            "environment": "unit test",
            "publication": {
                "checks": publication_checks(
                    self.latest["generated_at"], self.latest, self.complete, self.now
                )
            },
            "row_audit": audit,
            "findings": [],
        }
        markdown = render_audit_markdown(report)
        self.assertIn("https://buffedlizard55-lab.github.io/MaltaProj3/#picks-at-a-glance", markdown)
        self.assertIn(
            "https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks", markdown
        )
        self.assertIn("blank — unverified", markdown)
        self.assertIn("Unresolved picks & limitations", markdown)

    def test_saved_pages_evidence_is_the_official_legacy_read(self):
        evidence = json.loads((ROOT / "data/research/f8736556/pages-before.json").read_text())
        self.assertEqual(evidence["build_type"], "legacy")
        self.assertEqual(evidence["source"], {"branch": "main", "path": "/"})
        self.assertEqual(evidence["html_url"], "https://buffedlizard55-lab.github.io/MaltaProj3/")

    def test_runner_workflow_never_deploys_and_commits_only_session_research(self):
        workflow = (ROOT / ".github/workflows/f8736556-audit.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("arena/f8736556-maltaproj3", workflow)
        self.assertIn("python -m scripts.f8736556_audit", workflow)
        self.assertIn("git add data/research/f8736556", workflow)
        self.assertNotIn("deploy-pages", workflow)
        self.assertNotIn("upload-pages-artifact", workflow)
        self.assertNotIn("scripts.collect", workflow)
        self.assertNotIn("scripts.originate", workflow)


if __name__ == "__main__":
    unittest.main()
