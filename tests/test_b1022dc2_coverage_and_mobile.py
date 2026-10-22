"""Regression suite for session arena-b1022dc2:
- Full pick coverage and probability arithmetic verification
- Low-tier fallback ladder (HLTV -> esportsbooks -> Valve/network/ranking)
- Separate unresolved picks & limitations register in the executive summary
- Mobile-first executive summary navigation and pick presentation
- Zero crowd-vote/fan-vote contamination and strict row-source audit
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.audit_rows import audit_site
from scripts.build import build

ROOT = Path(__file__).resolve().parents[1]


class SessionB1022dc2VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        root = Path(cls.tmp.name)
        cls.data_dir = root / "data"
        cls.site_dir = root / "site"
        shutil.copytree(ROOT / "data", cls.data_dir)
        build(cls.data_dir, cls.site_dir)
        cls.latest = json.loads((cls.data_dir / "latest.json").read_text())
        cls.orig = json.loads((cls.data_dir / "origination.json").read_text())
        cls.index_html = (cls.site_dir / "index.html").read_text()
        cls.orig_html = (cls.site_dir / "origination/index.html").read_text()
        cls.review_html = (cls.site_dir / "review/index.html").read_text()
        cls.index_soup = BeautifulSoup(cls.index_html, "html.parser")

    def test_every_active_fixture_has_verified_probabilities_and_official_source_links(self):
        active_latest = [m for m in self.latest["matches"] if m["availability"] != "past"]
        self.assertEqual(len(active_latest), len(self.orig["matches"]))
        for m in self.orig["matches"]:
            with self.subTest(match_id=m["id"]):
                self.assertTrue(str(m.get("source_url") or "").startswith("https://"))
                o = m.get("origination")
                self.assertIsNotNone(o, f"Fixture {m['id']} must be originated in the checked-in snapshot")
                probs = o["probabilities"]
                self.assertEqual(len(probs), 2)
                self.assertAlmostEqual(probs[0] + probs[1], 1.0, places=6)
                self.assertTrue(0.0 < probs[0] < 1.0 and 0.0 < probs[1] < 1.0)
                self.assertEqual(o["fair_decimal"], [round(1.0 / probs[0], 3), round(1.0 / probs[1], 3)])
                self.assertTrue(str(o.get("source_url") or "").startswith("https://"))
                if abs(probs[0] - probs[1]) > 1e-9:
                    expected_pick = 0 if probs[0] > probs[1] else 1
                    self.assertEqual(m["pick_index"], expected_pick)
                else:
                    # An exactly even estimate normally carries no side. Session
                    # 4c972a51's published-rank tie-break may set one, and the
                    # shared audit accepts it only with its documented evidence
                    # (session 7293b310); nothing else may name a side here.
                    from scripts.coverage_audit import documented_tie_break
                    self.assertTrue(documented_tie_break(o, m["pick_index"]))

    def test_low_tier_featured_unresolved_matches_check_hltv_then_esportsbooks(self):
        low_tier = [m for m in self.orig["matches"] if m.get("featured_method") is None]
        self.assertGreaterEqual(len(low_tier), 4)
        for m in low_tier:
            with self.subTest(match_id=m["id"]):
                stages = [r["stage"] for r in m.get("research", [])]
                self.assertTrue(any("HLTV" in s for s in stages), f"HLTV research missing on {m['id']}")
                self.assertTrue(
                    any("Esportsbook" in s or "Thunderpick" in s for s in stages),
                    f"Esportsbook research stage missing on {m['id']}",
                )
                for r in m.get("research", []):
                    self.assertTrue(str(r.get("source_url") or "").startswith("https://"))

    def test_hotspawn_crowd_votes_and_hltv_fan_votes_are_never_used(self):
        self.assertIs(self.orig["policy"]["hotspawn_votes_used"], False)
        self.assertIs(self.orig["policy"]["fan_votes_used"], False)
        for m in self.latest["matches"]:
            self.assertNotIn("participants0_picked_percent", m)
            self.assertNotIn("participants1_picked_percent", m)

    def test_executive_summary_has_links_to_updated_picks_and_separate_unresolved_section(self):
        hrefs = {a.get("href") for a in self.index_soup.find_all("a", href=True)}
        self.assertIn("./origination/#picks", hrefs)
        self.assertIn("./origination/#unresolved", hrefs)
        self.assertIn("./picks/", hrefs)
        self.assertIn("./review/", hrefs)
        unresolved_sec = self.index_soup.find(id="unresolved-register")
        self.assertIsNotNone(unresolved_sec, "Executive summary must contain #unresolved-register")
        text = unresolved_sec.get_text(" ", strip=True)
        self.assertIn("Unresolved picks & limitations", text)
        self.assertIn("Hotspawn participation percentages", text)

    def test_mobile_friendly_viewport_nav_and_picks_at_a_glance(self):
        viewport = self.index_soup.find("meta", attrs={"name": "viewport"})
        self.assertIsNotNone(viewport)
        self.assertIn("width=device-width", viewport.get("content", ""))
        mobile_nav = self.index_soup.find("nav", class_="mobile-nav")
        self.assertIsNotNone(mobile_nav)
        glance = self.index_soup.find(id="picks-at-a-glance")
        self.assertIsNotNone(glance)
        glance_items = glance.select("ol.glance-list > li")
        self.assertEqual(len(glance_items), len(self.orig["matches"]))

    def test_b1022dc2_research_dossiers_and_review_flags_render_with_zero_audit_violations(self):
        flags_path = ROOT / "data/research/b1022dc2/flags.json"
        self.assertTrue(flags_path.exists())
        flags = json.loads(flags_path.read_text())
        self.assertGreaterEqual(len(flags), 5)
        for f in flags:
            with self.subTest(flag_id=f["id"]):
                self.assertIn(f'id="flag-{f["id"]}"', self.review_html)
                self.assertTrue(all(u.startswith("https://") for u in f["source_urls"]))
        report = audit_site(self.site_dir)
        self.assertEqual(report["totals"]["violation"], 0)


if __name__ == "__main__":
    unittest.main()
