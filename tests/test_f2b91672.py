"""Session f2b91672 — regression tests for scoped CCT SA #7 / EU #12 aliases, unranked-floor guidance precedence, and review flags."""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import audit_rows, f2b91672_live_audit, originate

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 22, 9, 12, tzinfo=timezone.utc)


class ScopedAliasRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = originate.load_registry(ROOT / "data" / "origination" / "aliases.json")

    def test_all_session_aliases_resolve_in_scope_and_stay_isolated_outside_scope(self) -> None:
        audit = f2b91672_live_audit.build_audit()
        self.assertEqual(len(audit["alias_checks"]), 8)
        for check in audit["alias_checks"]:
            self.assertTrue(check["matches_expected"], check)
            self.assertTrue(check["isolated_outside_scope"], check)
            self.assertTrue(all(u.startswith("https://") for u in check["evidence_urls"]), check)

    def test_academy_variants_never_match_org_aliases(self) -> None:
        for academy_name in (
            "Procyon Academy",
            "Procyon Gaming Academy",
            "Yawara Academy",
            "Yawara Esports Academy",
            "Grêmio Academy",
            "Grêmio Esports Academy",
            "Gremio Academy",
        ):
            resolved, used = originate.resolve_name(
                academy_name, self.registry, "CCT South America 2026 Series #7"
            )
            self.assertEqual(resolved, originate.name_key(academy_name), academy_name)
            self.assertEqual(used, [], academy_name)


class UnrankedFloorVsGuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = originate.load_registry(ROOT / "data" / "origination" / "aliases.json")
        cls.audit = f2b91672_live_audit.build_audit()
        cls.by_id = {row["id"]: row for row in cls.audit["replayed_fixtures"]}

    def test_inverted_cct_sa7_valve_row_upgrades_to_two_provider_consensus(self) -> None:
        row = self.by_id["1082922"]
        self.assertEqual(row["method"], "consensus")
        self.assertEqual(row["source"], "Polymarket + Pinnacle")
        self.assertEqual(row["pick_team"], "Grêmio")
        self.assertAlmostEqual(row["probabilities"][1], 0.7027, places=3)

    def test_unranked_floor_defers_to_directional_resting_bid_on_1082919(self) -> None:
        row = self.by_id["1082919"]
        self.assertEqual(row["method"], "guidance")
        self.assertEqual(row["source"], "Polymarket")
        self.assertEqual(row["pick_team"], "Projeto do KinGui")
        self.assertAlmostEqual(row["probabilities"][0], 0.665, places=3)

    def test_unranked_floor_still_beats_unquoted_stub_book(self) -> None:
        fixture = {
            "id": "stub-1082919",
            "competition": "CCT South America 2026 Series #7",
            "starts_at": "2026-10-22T13:00:00Z",
            "teams": [{"id": "t-pdkg", "name": "Projeto do KinGui"}, {"id": "t-mar", "name": "Martians"}],
            "source_url": "https://www.hotspawn.com/matches/projeto-do-kingui-vs-martians-cct-south-america-2026-series-7-1082919",
        }
        stub_poly = [
            f2b91672_live_audit._poly_row(
                event_id="1232953",
                market_id="m-1232953",
                slug="cs2-tdkg-mar1-2026-10-22",
                names=["Tropa do KinGui", "Martians"],
                start="2026-10-22T13:00:00Z",
                bid0=0.04,
                ask0=0.96,
            )
        ]
        res = originate.originate_match(
            fixture,
            stub_poly,
            [],
            {},
            {"source_url": "https://github.com/ValveSoftware/counter-strike_regional_standings"},
            self.registry,
            NOW,
            hltv_rank=[{"name": "Martians", "rank": 240, "points": 1.0}],
            hltv_meta={
                "published_at": "2026-10-20T00:00:00Z",
                "observed_at": "2026-10-22T09:05:00Z",
                "source_url": "https://www.hltv.org/ranking/teams",
                "evidence_file": "data/research/f2b91672/live-audit.json#hltv-ranking",
            },
        )
        self.assertEqual(res["origination"]["method"], "model")
        self.assertIn("unranked floor", res["origination"]["label"])
        self.assertEqual(res["pick_index"], 1)

    def test_cct_sa7_single_book_rows_upgrade_to_polymarket_plus_pinnacle_consensus(self) -> None:
        for fid, expected_pick in (("1082920", "Procyon"), ("1082921", "Yawara")):
            row = self.by_id[fid]
            self.assertEqual(row["method"], "consensus", fid)
            self.assertEqual(row["source"], "Polymarket + Pinnacle", fid)
            self.assertEqual(row["pick_team"], expected_pick, fid)

    def test_sokerorg_joins_lfo_10_and_upgrades_once_quoted(self) -> None:
        stub = self.by_id["1081149"]
        self.assertEqual(stub["method"], "model")
        self.assertEqual(stub["pick_team"], "FORZE Reload")
        self.assertIn("Sökerorg -> LFO 10", stub["aliases_used"])

        fixture = {
            "id": "1081149",
            "competition": "CCT Europe 2026 Series #12",
            "starts_at": "2026-10-23T14:00:00Z",
            "teams": [{"id": "t-fr", "name": "FORZE Reload"}, {"id": "t-lfo", "name": "LFO 10"}],
            "source_url": "https://www.hotspawn.com/matches/forze-reload-vs-lfo-10-cct-europe-2026-series-12-1081149",
        }
        quoted_poly = [
            f2b91672_live_audit._poly_row(
                event_id="1233762",
                market_id="m-1233762",
                slug="cs2-forzer-skr2-2026-10-23",
                names=["FORZE Reload", "Sökerorg"],
                start="2026-10-23T14:00:00Z",
                bid0=0.61,
                ask0=0.65,
            )
        ]
        res = originate.originate_match(
            fixture,
            quoted_poly,
            [],
            {},
            {"source_url": "https://github.com/ValveSoftware/counter-strike_regional_standings"},
            self.registry,
            NOW,
        )
        self.assertEqual(res["origination"]["method"], "market")
        self.assertEqual(res["pick_index"], 0)


class ReviewFlagsDiscoveryTests(unittest.TestCase):
    def test_session_flags_load_cleanly_with_official_https_links(self) -> None:
        raw = json.loads((ROOT / "data" / "research" / "f2b91672" / "flags.json").read_text())
        ids = {f["id"] for f in raw}
        expected = {
            "f2b91672-cct-sa7-inverted-model-picks",
            "f2b91672-sokerorg-lfo10-translation-alias",
            "f2b91672-root-publish-data-and-deploy-ordering",
            "f2b91672-hotspawn-stuck-june-2026-rows",
        }
        self.assertEqual(ids, expected)
        for item in raw:
            self.assertIn(item["severity"], {"warning", "notice"})
            self.assertTrue(item["title"] and item["detail"], item["id"])
            self.assertTrue(item["source_urls"], item["id"])
            for url in item["source_urls"]:
                self.assertTrue(url.startswith("https://"), url)
                self.assertTrue(audit_rows.is_official(url), url)


if __name__ == "__main__":
    unittest.main()
