"""Session arena-99d48cd8: executive-summary navigation + phone legibility, offline.

Checks the checked-in branch-root build (what GitHub Pages serves between
publishes): the executive summary must link inside the site to the updated
picks, to the separate unresolved page, and to per-fixture rows; every
published upcoming fixture must be reachable from the summary by an in-site
link; the unresolved page must name both published-unresolved fixtures.
Viewport/overflow is asserted structurally (meta viewport + no fixed-width
body) so the test stays offline; pixel-level overflow is covered by the
repo's Playwright specs when a browser is available.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(".")
INDEX = (ROOT / "index.html").read_text()
PICKS = (ROOT / "picks" / "index.html").read_text()
UNRESOLVED = (ROOT / "unresolved" / "index.html").read_text()


class ExecutiveSummaryLinks(unittest.TestCase):
    def setUp(self):
        snap = json.loads((ROOT / "snapshot.json").read_text())
        self.upcoming = [m for m in snap["matches"] if (m.get("starts_at") or "") >= snap["generated_at"]]

    def test_summary_links_to_picks_unresolved_methodology_coverage(self):
        for target in ("picks/", "unresolved/", "methodology/", "coverage/", "review/"):
            self.assertIn(f'href="./{target}"', INDEX, target)
            self.assertTrue((ROOT / target / "index.html").exists(), target)

    def test_every_published_upcoming_fixture_linked_from_summary(self):
        # No hard-coded fixture count: the summary must link whatever the
        # snapshot in this checkout publishes, so the check survives each
        # four-hourly republish instead of expiring with the data.
        linked = set(re.findall(r"match-(\d+)", INDEX))
        self.assertTrue(self.upcoming, "the published snapshot has no upcoming fixture")
        for m in self.upcoming:
            self.assertIn(m["id"], linked, m["id"])

    def test_unresolved_page_names_both_unresolved_fixtures(self):
        # Same rule: name every fixture the snapshot leaves unresolved, rather
        # than the two it left unresolved on 2026-10-23.
        unresolved = [m for m in self.upcoming if m.get("pick_index") is None]
        snapshot_data = json.loads((ROOT / "snapshot.json").read_text())
        expected = snapshot_data.get("counts", {}).get("unresolved")
        if expected is not None:
            self.assertEqual(len(unresolved), expected,
                             "every unresolved fixture must appear on the unresolved page")
        for m in unresolved:
            for team in m["teams"]:
                self.assertIn(team["name"], UNRESOLVED)

    def test_picks_page_has_a_row_per_published_upcoming_fixture(self):
        rows = set(re.findall(r'id="match-(\d+)"', PICKS))
        for m in self.upcoming:
            self.assertIn(m["id"], rows, m["id"])

    def test_phone_basics_viewport_and_no_forced_fixed_width(self):
        for page in (INDEX, PICKS, UNRESOLVED):
            self.assertIn('name="viewport"', page)
            self.assertIn("width=device-width", page)
            self.assertNotRegex(page, r'<body[^>]*style="[^"]*width:\s*\d{3,}px')

    def test_session_unresolved_section_links_land_on_real_site_pages(self):
        doc = json.loads((ROOT / "data/research/99d48cd8/unresolved-limitations-2026-10-24.json").read_text())
        for entry in doc["entries"]:
            links = entry["site_links"]
            self.assertTrue(links["pick_row"].endswith(f"/picks/#match-{entry['id']}"))
            self.assertTrue(links["unresolved_page"].endswith("/unresolved/"))
        for line in doc["how_to_use_on_phone"]:
            self.assertIn("buffedlizard55-lab.github.io/MaltaProj3", line)


if __name__ == "__main__":
    unittest.main()
