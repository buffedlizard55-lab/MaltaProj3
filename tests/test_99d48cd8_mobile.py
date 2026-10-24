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

import html
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
        # Counts/ids are derived from the checked-in snapshot rather than
        # hard-coded: the dated constants (19 upcoming; unresolved
        # 1082792/1082858) broke the publisher regression the moment a
        # fresh snapshot root-synced on 2026-10-24 (run 40085158851).
        # Behaviour intent is unchanged and now holds for any snapshot.
        # (Integration fix by arena-f1277d3b.)
        linked = set(re.findall(r"match-(\d+)", INDEX))
        self.assertGreater(len(self.upcoming), 0)
        for m in self.upcoming:
            self.assertIn(m["id"], linked, m["id"])

    def test_unresolved_page_names_both_unresolved_fixtures(self):
        # Derive the same set the page derives. `scripts/build.py::unresolved_table`
        # lists every non-past fixture whose featured analysis is empty; the
        # collector's `counts.unresolved` is a different counter (it includes
        # locked and unknown-schedule rows), so comparing the two numbers pinned
        # nothing real and failed the publisher's regression step once a fresher
        # root snapshot landed (runs 40116915898 and 40120126457). The intent --
        # every published-unresolved fixture is named on the separate page --
        # is asserted directly.
        snap = json.loads((ROOT / "snapshot.json").read_text())
        unresolved = [m for m in snap["matches"]
                      if m.get("availability") != "past" and m.get("analysis") is None]
        page = html.unescape(UNRESOLVED)
        page_ids = set(re.findall(r"match-(\d+)", page))
        for m in unresolved:
            self.assertIn(str(m["id"]), page_ids, m["id"])
            for team in m["teams"]:
                self.assertIn(team["name"], page, team["name"])
        # The page never claims fewer blanks than the snapshot actually has.
        self.assertGreaterEqual(len(page_ids), len(unresolved))

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
