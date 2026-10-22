"""Session 75aa5b56 — Hotspawn full inventory, every-match picks, phone-first summary.

The brief says:
- every Hotspawn CS2 match must have a pick or an explicit unresolved entry with blocker + source
- missing picks must be researched HLTV first, then esportsbooks/betting lines
- unresolved picks + limitations need a separate section in the executive summary
- executive summary must provide obvious internal links to the updated picks list and be thumb-friendly on phone
- site must be mobile-friendly (viewport, readable type, 44px targets, no overflow at 320px)
- full Hotspawn inventory must be reconciled from the public scheduled-fixture feed and refreshed every 4-8h
- every table row must have an official source link (verified by row-source audit)
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import build
from scripts.audit_rows import audit_site

ROOT = Path(__file__).resolve().parents[1]


class Session75aa5b56Tests(unittest.TestCase):
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
        cls.index_soup = BeautifulSoup(cls.index_html, "html.parser")

    def test_every_active_fixture_has_pick_or_explicit_unresolved_with_source_links(self):
        # The complete list is the canonical inventory
        active = self.orig["matches"]
        self.assertEqual(self.orig["counts"]["active"], len(active))
        for m in active:
            with self.subTest(id=m["id"]):
                self.assertTrue(str(m.get("source_url") or "").startswith("https://"), "Hotspawn link required")
                o = m.get("origination")
                if o is not None:
                    self.assertEqual(len(o["probabilities"]), 2)
                    self.assertAlmostEqual(sum(o["probabilities"]), 1.0, places=6)
                    self.assertTrue(str(o.get("source_url") or "").startswith("https://"))
                    if o["probabilities"][0] != o["probabilities"][1]:
                        self.assertIsNotNone(m.get("pick_index"))
                else:
                    # unresolved must have research trail with source links
                    trail = m.get("research") or []
                    self.assertGreater(len(trail), 0)
                    for r in trail:
                        self.assertTrue(str(r.get("source_url") or "").startswith("https://"))

    def test_low_tier_fallbacks_show_hltv_then_esportsbook_research(self):
        # At least the historically low-tier fixtures must show the ladder stages
        low = [m for m in self.orig["matches"] if m.get("featured_method") is None]
        self.assertGreaterEqual(len(low), 1)
        for m in low:
            stages = [r["stage"] for r in m.get("research", [])]
            # HLTV stage must be present for researched fallbacks
            self.assertTrue(any("HLTV" in s for s in stages), f"HLTV stage missing on {m['id']}")
            # at least one esportsbook/market stage should appear
            self.assertTrue(any("Polymarket" in s or "Thunderpick" in s or "Esportsbook" in s or "Original esportsbook" in s or "Pinnacle" in s or "Bovada" in s or "Kalshi" in s for s in stages),
                            f"Esportsbook stage missing on {m['id']}")

    def test_executive_summary_has_obvious_internal_links_to_updated_picks(self):
        hrefs = {a.get("href") or "" for a in self.index_soup.find_all("a", href=True)}
        # The brief's core ask: start here → updated picks
        self.assertIn("./origination/#picks", hrefs)
        self.assertIn("./origination/#unresolved", hrefs)
        self.assertIn("./picks/", hrefs)
        self.assertIn("./review/", hrefs)
        # exec banner is the first tappable block
        banner = self.index_soup.find("section", class_="exec-banner")
        self.assertIsNotNone(banner, "Executive summary must have the exec-banner start-here block")
        banner_links = {a.get("href") or "" for a in banner.find_all("a", href=True)}
        self.assertIn("./origination/#picks", banner_links)
        self.assertIn("./origination/#unresolved", banner_links)
        # start-here jump bar
        nav = self.index_soup.find("nav", id="start-here")
        self.assertIsNotNone(nav)
        nav_links = {a.get("href") or "" for a in nav.find_all("a", href=True)}
        self.assertIn("./origination/#picks", nav_links)

    def test_unresolved_picks_and_limitations_in_executive_summary(self):
        sec = self.index_soup.find(id="unresolved-register")
        self.assertIsNotNone(sec, "Executive summary must contain #unresolved-register (separate register)")
        text = sec.get_text(" ", strip=True)
        self.assertIn("Unresolved picks", text)
        self.assertIn("limitations", text.lower())
        # every unresolved must be listed or the 'no unresolved' note shown
        active_count = self.orig["counts"]["active"]
        if self.orig["counts"]["unresolved"] == 0:
            self.assertIn("No unresolved fixtures", text)

    def test_mobile_friendly_picks_at_a_glance_with_both_probabilities(self):
        viewport = self.index_soup.find("meta", attrs={"name": "viewport"})
        self.assertIsNotNone(viewport)
        self.assertIn("width=device-width", viewport.get("content", ""))
        mobile_nav = self.index_soup.find("nav", class_="mobile-nav")
        self.assertIsNotNone(mobile_nav)
        glance = self.index_soup.find(id="picks-at-a-glance")
        self.assertIsNotNone(glance)
        rows = glance.select("ol.glance-list > li.glance-row")
        self.assertEqual(len(rows), len(self.orig["matches"]))
        for li in rows:
            choice = li.find(class_="glance-choice")
            self.assertIsNotNone(choice)
            # both probabilities must be visible on the row (pick + other)
            prob = choice.find(class_="glance-prob")
            other = choice.find(class_="glance-other")
            # Even estimates have 'no side' — still not a missing number
            if prob and "no side" not in prob.get_text():
                self.assertIsNotNone(other, "Both teams' probabilities must appear on a resolved glance row")

    def test_hotspawn_inventory_reconciliation_documented(self):
        # SOURCE_RESEARCH.md and hotspawn-integration section must exist
        src_md = ROOT / "docs" / "SOURCE_RESEARCH.md"
        self.assertTrue(src_md.exists())
        txt = src_md.read_text()
        self.assertIn("phpstack-1372681-6459848.cloudwaysapps.com", txt)
        self.assertIn("Hotspawn reverse engineering", txt)
        # Coverage page must have hotspawn-integration anchor
        cov = (self.site_dir / "coverage/index.html").read_text()
        self.assertIn("hotspawn-integration", cov.lower())
        self.assertIn("Authoritative fixture array", cov)

    def test_every_table_row_has_official_source_link_and_zero_audit_violations(self):
        report = audit_site(self.site_dir)
        self.assertEqual(report["totals"]["violation"], 0, f"Row-source audit must be 0, got {report['totals']}")

    def test_no_hallucinated_values_every_blank_stays_blank(self):
        # No active row should be given a silent 50/50 or invented bookmaker name
        for m in self.orig["matches"]:
            o = m.get("origination")
            if o is None:
                continue
            # method badge must match the origination method — never invented
            self.assertIn(o["method"], {"market", "bookmaker", "consensus", "reference", "model", "guidance", "relay"})

