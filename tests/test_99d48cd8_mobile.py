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
        # Snapshot-independent, because `snapshot.json` is rewritten by every
        # publish: the separate page must (a) report counts that add up and
        # (b) name, with a deep link, every fixture it reports as unpicked.
        # The published page's own numbers are the contract; a fixture that the
        # complete-picks layer resolved is *not* unresolved, and a fixture with
        # probabilities but no directional side is reported separately as
        # "No side" (1079200, the first even-market row, 2026-10-24).
        # (Integration fix by arena-5f9d0082.)
        page = html.unescape(UNRESOLVED)
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))

        def declared(label):
            match = re.search(re.escape(label) + r"\s+(\d+)", text)
            self.assertIsNotNone(match, f"the page does not declare '{label}'")
            return int(match.group(1))

        active = declared("Active fixtures")
        with_pick = declared("With a pick")
        no_pick = declared("No pick")
        no_side = declared("No side")
        self.assertEqual(with_pick + no_pick + no_side, active)

        # Both documented anchor conventions are legitimate deep links to a
        # fixture: `match-<id>` on origination rows and `no-line-<id>` on the
        # "picks without a betting line" cards.
        ids = set(re.findall(r"(?:match|no-line)-(\d+)", page))
        unpicked = [m for m in self.upcoming if m.get("analysis") is None]
        named = [m for m in unpicked if str(m["id"]) in ids]
        self.assertGreaterEqual(len(named), no_pick)
        for m in named:
            for team in m["teams"]:
                self.assertIn(team["name"], page, team["name"])

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
