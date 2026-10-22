"""Session 3016b0c6: phone find-a-pick filter + executive banner wording.

The filter is markup + progressive-enhancement JS only: every glance row must
carry a searchable team/competition string, the input must exist on the
executive summary, and with no JS nothing is hidden (no `hidden` in markup).
"""
import unittest
from datetime import datetime, timezone

from scripts.build import exec_banner, glance


def match(i, name_a, name_b, comp="CCT Test"):
    return {"id": str(i), "competition": comp, "starts_at": "2099-01-01T10:00:00Z",
            "locks_at": "2099-01-01T09:54:00Z", "availability": "open",
            "source_url": "https://www.hotspawn.com/matches/x",
            "teams": [{"name": name_a}, {"name": name_b}],
            "analysis": {"method": "market", "source_url": "https://polymarket.com/event/x",
                         "probabilities": [0.62, 0.38]},
            "pick_index": 0}


class GlanceFinderTests(unittest.TestCase):
    def setUp(self):
        now = datetime(2026, 10, 22, tzinfo=timezone.utc)
        data = {"matches": [match(1, "Spirit Academy", "GenOne"),
                            match(2, "BakS", "Azuolas", "DraculaN")],
                "fallbacks": {}}
        self.html = glance(data, "", now=now)

    def test_finder_input_present_and_controls_list(self):
        self.assertIn('id="glance-search"', self.html)
        self.assertIn('type="search"', self.html)
        self.assertIn('aria-controls="glance-list"', self.html)
        self.assertIn('<ol class="glance-list" id="glance-list">', self.html)

    def test_every_row_searchable_by_both_teams_and_tournament(self):
        self.assertIn('data-search="spirit academy genone cct test"', self.html)
        self.assertIn('data-search="baks azuolas draculan"', self.html)

    def test_no_row_hidden_in_static_markup(self):
        # Without JS the phone reader must still see every pick.
        self.assertNotIn('glance-row" data-glance-id="1" data-search="spirit academy genone cct test" hidden', self.html)
        self.assertIn('id="glance-empty" hidden', self.html)  # only the empty-note starts hidden

    def test_js_and_css_ship_the_filter(self):
        from pathlib import Path
        js = Path("assets/scout.js").read_text()
        css = Path("assets/scout.css").read_text()
        self.assertIn("#glance-search", js)
        self.assertIn("row.dataset.search", js)
        self.assertIn(".glance-finder", css)
        self.assertIn("position:sticky", css)  # stays reachable while scrolling on a phone


class BannerWordingTests(unittest.TestCase):
    def test_unresolved_without_a_pick_not_without_a_line(self):
        data = {"counts": {"upcoming": 3, "unresolved": 1, "model": 2},
                "inventory_observed_at": "2026-10-22T05:36:38Z",
                "complete_picks": {"counts": {"active": 3, "with_pick": 2, "unresolved": 1, "model": 2, "guidance": 0},
                                   "generated_at": "2026-10-22T05:37:07Z"}}
        html = exec_banner(data, "")
        self.assertIn("1 without a pick · 2 model-only (no betting line)", html)
        self.assertNotIn("without a line ·", html.replace("model-only (no betting line)", ""))


if __name__ == "__main__":
    unittest.main()
