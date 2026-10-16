"""Tests for session arena-f392649f: HLTV 5-player lineup disambiguation and TWC Day 1–3 verification."""
from __future__ import annotations

import copy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup

from scripts.audit_rows import audit_html
from scripts.lineup_disambiguation import (
    DISAMBIGUATION_PATH,
    TWC_VERIFICATION_PATH,
    VALVE_EVIDENCE_PATH,
    load_disambiguation,
    load_twc_verification,
    render_disambiguation_section,
    validate_disambiguation,
    validate_twc_verification,
    win_probability,
)

ROOT = Path(__file__).resolve().parents[1]


class LineupDisambiguationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.disambig = load_disambiguation(ROOT / DISAMBIGUATION_PATH, ROOT / VALVE_EVIDENCE_PATH)
        cls.twc = load_twc_verification(ROOT / TWC_VERIFICATION_PATH, ROOT / VALVE_EVIDENCE_PATH)

    def test_three_duplicate_name_fixtures_are_uniquely_resolved_by_hltv_core(self):
        by_id = {f["hotspawn_id"]: f for f in self.disambig["fixtures"]}
        expected = {
            "1079170": ("BET-M", 71, 1149, "Just Players", 118, 974, "BET-M"),
            "1081527": ("aimclub", 77, 1113, "BASEMENT BOYS", 102, 1036, "aimclub"),
            "1081532": ("ASTRAL", 91, 1072, "Leo", 112, 1001, "ASTRAL"),
        }
        for hid, (ta, sa, pa, tb, sb, pb, pick) in expected.items():
            fix = by_id[hid]
            self.assertEqual(fix["disambiguation_status"], "resolved_by_hltv_lineup_core")
            self.assertEqual(fix["team_a"]["name"], ta)
            self.assertEqual(fix["team_a"]["selected_valve_standing"], sa)
            self.assertEqual(fix["team_a"]["selected_valve_points"], pa)
            self.assertEqual(fix["team_b"]["name"], tb)
            self.assertEqual(fix["team_b"]["selected_valve_standing"], sb)
            self.assertEqual(fix["team_b"]["selected_valve_points"], pb)
            self.assertEqual(fix["recommended_pick"], pick)
            replayed = win_probability(pa, pb)
            self.assertAlmostEqual(fix["probabilities"][0], replayed[0], places=6)
            self.assertAlmostEqual(fix["probabilities"][1], replayed[1], places=6)

    def test_two_unranked_opponent_fixtures_stay_strictly_null(self):
        by_id = {f["hotspawn_id"]: f for f in self.disambig["fixtures"]}
        for hid, unranked_team in (("1081502", "LOS NINOS"), ("1081526", "Insiders")):
            fix = by_id[hid]
            self.assertEqual(fix["disambiguation_status"], "unresolved_opponent_unranked")
            self.assertEqual(fix["team_b"]["name"], unranked_team)
            self.assertIsNone(fix["team_b"]["selected_valve_standing"])
            self.assertIsNone(fix["team_b"]["selected_valve_points"])
            self.assertIsNone(fix["probabilities"])
            self.assertIsNone(fix["fair_decimal_odds"])
            self.assertIsNone(fix["recommended_pick"])
            self.assertIsNone(fix["pick_index"])

    def test_validator_rejects_invented_pick_on_unranked_fixture(self):
        import json
        valve = json.loads((ROOT / VALVE_EVIDENCE_PATH).read_text(encoding="utf-8"))
        bad = copy.deepcopy(self.disambig)
        bad["fixtures"][3]["recommended_pick"] = "Procyon"
        with self.assertRaises(ValueError):
            validate_disambiguation(bad, valve)

    def test_validator_rejects_tampered_overlap_count(self):
        import json
        valve = json.loads((ROOT / VALVE_EVIDENCE_PATH).read_text(encoding="utf-8"))
        bad = copy.deepcopy(self.disambig)
        bad["fixtures"][0]["team_b"]["valve_candidates"][1]["overlap_count"] = 3
        with self.assertRaises(ValueError):
            validate_disambiguation(bad, valve)

    def test_twc_verification_covers_all_eight_completed_series_and_both_deciders(self):
        self.assertEqual(len(self.twc["day_one_complete"]), 4)
        self.assertEqual(len(self.twc["day_two_complete"]), 4)
        self.assertEqual(len(self.twc["day_three_deciders"]), 2)
        falcons = self.twc["falcons_lineup_resolution"]
        self.assertIn("karrigan", falcons["verified_match_lineup"])
        self.assertEqual(falcons["valve_standing"], 6)
        self.assertEqual(falcons["valve_points"], 1843)

    def test_rendered_section_passes_strict_row_source_audit(self):
        html = render_disambiguation_section(self.disambig, "../")
        soup = BeautifulSoup(html, "html.parser")
        self.assertIsNotNone(soup.find(id="lineup-disambiguation"))
        self.assertEqual(len(soup.select("#lineup-disambiguation tbody tr")), 5)
        report = audit_html(html, "edge/index.html")
        self.assertEqual(report["violation"], 0)
        self.assertEqual(report["ok"], 5)

    def test_historical_partial_roster_scenarios_are_not_second_current_picks(self):
        html = render_disambiguation_section(self.disambig, "../")
        soup = BeautifulSoup(html, "html.parser")
        self.assertNotIn('Recommended pick:', html)
        self.assertNotIn('26 / 31 resolved', html)
        self.assertIn('not accepted canonical picks', html)
        for mid in ['1079170', '1081527']:
            row = soup.find(id='disambig-' + mid)
            self.assertIn('Partial roster overlap', row.get_text())
            self.assertIsNotNone(row.find('a', href='../origination/#unresolved'))
            self.assertNotIn('%', row.find_all('td')[2].get_text())

    def test_historical_replay_does_not_depend_on_live_rating_cache(self):
        self.assertIn('research/6426358d/', VALVE_EVIDENCE_PATH.as_posix())
        from scripts.lineup_disambiguation import load_archived_valve
        self.assertEqual(len(load_archived_valve(ROOT / VALVE_EVIDENCE_PATH)['rows']), 380)

    def test_historical_valve_inputs_must_replay_from_the_original_blob(self):
        import json
        import shutil
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / VALVE_EVIDENCE_PATH.name
            data = json.loads((ROOT / VALVE_EVIDENCE_PATH).read_text())
            data['rows'][0]['points'] += 1
            path.write_text(json.dumps(data))
            original = 'valve-response-2026-10-05.json'
            shutil.copyfile(ROOT / VALVE_EVIDENCE_PATH.parent / original, path.parent / original)
            with self.assertRaisesRegex(ValueError, 'original markdown'):
                load_disambiguation(ROOT / DISAMBIGUATION_PATH, path)

    def test_full_build_publishes_disambiguation_on_edge_and_review_pages(self):
        from scripts.build import build
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            build(ROOT / "data", out)
            edge_html = (out / "edge" / "index.html").read_text(encoding="utf-8")
            review_html = (out / "review" / "index.html").read_text(encoding="utf-8")
            self.assertIn('id="lineup-disambiguation"', edge_html)
            self.assertIn('id="lineup-disambiguation"', review_html)
            self.assertTrue((out / DISAMBIGUATION_PATH).exists())
            self.assertTrue((out / TWC_VERIFICATION_PATH).exists())


if __name__ == "__main__":
    unittest.main()
