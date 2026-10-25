"""Session arena-0c034b94: every published number replayed, and the phone routes to the picks.

The brief for this session is (1) a pick, or an explicit unresolved entry with its
limitations, for every Counter-Strike 2 match Hotspawn lists, (2) research that
starts at HLTV and then esportsbooks only for the fixtures the featured method
cannot resolve, (3) a separate unresolved/limitations section inside the
executive summary, and (4) in-site links to the current picks that a phone can
reach.

These tests pin the parts of that contract that can be checked without a network:
the arithmetic replay in ``scripts/0c034b94_verify.py`` (every probability is
re-derived from the evidence in the snapshot, never copied), and the rendered
routes from the executive summary to the picks, fallback and unresolved lists.
They never invent a probability and never assert a *specific* fixture's value,
so a four-hourly refresh cannot turn them red for the wrong reason.
"""
from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import build

ROOT = Path(__file__).resolve().parents[1]
verify = importlib.import_module('scripts.0c034b94_verify')

#: Sections a reader must be able to reach from the executive summary. Each id
#: is rendered by scripts/build.py and each href must appear on the summary page.
PICK_ROUTES = (
    './origination/#picks',       # the complete, phone-first picks list
    './origination/#unresolved',  # unresolved trails on that list
    './unresolved/',              # the dedicated unresolved page
    './#picks-at-a-glance',       # the on-page index
    './#unresolved-register',     # in-page unresolved register
    './#no-line-register',        # in-page register of picks without a betting line
    './#fallback-register',       # in-page register of non-featured fallback picks
)


class ReplayTests(unittest.TestCase):
    """The snapshot's own numbers, re-derived from the evidence it carries."""

    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((ROOT / 'snapshot.json').read_text())
        cls.report = verify.verify(cls.snapshot)

    def test_no_published_number_conflicts_with_its_own_evidence(self):
        self.assertEqual(self.report['violations'], [], 'a published row failed its replay')

    def test_the_replay_actually_recomputes_most_rows(self):
        # A guard against a vacuous pass: the verifier must re-derive the numbers,
        # not merely restate them.
        self.assertGreater(self.report['replayed'], 0)
        self.assertGreaterEqual(self.report['replayed'], self.report['open_rows'] // 2)

    def test_anything_not_replayed_states_why(self):
        for item in self.report['not_replayed']:
            self.assertIn(':', item)
            self.assertGreater(len(item.split(':', 1)[1].strip()), 10, item)

    def test_fixtures_without_a_featured_analysis_carry_limits_and_https_research(self):
        by_id = {str(m['id']): m for m in self.snapshot['matches']}
        for fid in self.report['without_featured_analysis']:
            match = by_id[fid]
            self.assertTrue(match.get('limitations'), fid)
            stages = match.get('research') or []
            self.assertTrue(stages, fid)
            for stage in stages:
                self.assertTrue(str(stage.get('source_url', '')).startswith('https://'), fid)

    def test_the_snapshot_states_its_refresh_contract(self):
        # The brief asks for a refresh every four to eight hours; the snapshot
        # carries the interval and the staleness bound the site renders.
        self.assertEqual(self.snapshot.get('refresh_interval_hours'), 4)
        self.assertEqual(self.snapshot.get('stale_after_hours'), 8)

    def test_crowd_and_fan_percentages_are_never_inputs(self):
        for match in self.snapshot['matches']:
            leakage = verify.find_forbidden(match.get('analysis') or {})
            self.assertEqual(leakage, [], match.get('id'))


class ArchiveTests(unittest.TestCase):
    def test_raw_originals_are_gzipped_and_never_plain_html(self):
        # The publisher copies the research tree into the site and then validates
        # every .html it finds there as one of its own pages. A retained original
        # must therefore be archived as .html.gz, or the build fails with
        # "no main landmark" on a source file (measured 2026-10-25).
        raw = ROOT / 'data' / 'research' / '0c034b94' / 'raw'
        plain = sorted(str(p.relative_to(ROOT)) for p in raw.rglob('*.html'))
        self.assertEqual(plain, [])
        self.assertTrue(list(raw.glob('*.html.gz')), 'no archived original HTML at all')


class ValveFormulaTests(unittest.TestCase):
    """The research model must keep using Valve's published expectation."""

    def test_the_rd_scaling_is_valves_own_g(self):
        # VALVE_RD = 75 gives g = 0.97282099..., the value the snapshot carries.
        self.assertAlmostEqual(verify.valve_g(75), 0.9728209910486895, places=12)

    def test_a_known_points_difference_lands_where_valve_puts_it(self):
        # 5star 1110 vs 1WIN 1383 in the official 2026-10-05 standings.
        self.assertAlmostEqual(verify.valve_probability(1110, 1383), 0.17816902, places=6)

    def test_a_symmetric_difference_is_a_coin_flip(self):
        self.assertAlmostEqual(verify.valve_probability(1500, 1500), 0.5, places=12)


class SummaryRoutesTests(unittest.TestCase):
    """A phone reader must be able to reach every picks list from the summary."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.site = Path(cls.tmp.name) / 'site'
        build.build(ROOT / 'data', cls.site)
        cls.index = (cls.site / 'index.html').read_text(encoding='utf-8')
        cls.soup = BeautifulSoup(cls.index, 'html.parser')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_summary_links_every_picks_route(self):
        hrefs = {a.get('href') for a in self.soup.find_all('a') if a.get('href')}
        for route in PICK_ROUTES:
            self.assertIn(route, hrefs, route)

    def test_the_unresolved_register_is_a_section_of_the_summary(self):
        self.assertIsNotNone(self.soup.select_one('#unresolved-register'))
        self.assertIsNotNone(self.soup.select_one('#no-line-register'))
        text = self.soup.get_text(' ', strip=True).lower()
        self.assertIn('unresolved picks & limitations', text)
        self.assertIn('limitation', text)

    def test_the_phone_viewport_and_landmarks_are_present(self):
        viewport = self.soup.find('meta', attrs={'name': 'viewport'})
        self.assertIsNotNone(viewport)
        self.assertIn('width=device-width', viewport.get('content', ''))
        self.assertIsNotNone(self.soup.select_one('a[href="#main"]'))
        self.assertIsNotNone(self.soup.select_one('nav[aria-label]'))

    def test_the_dedicated_unresolved_page_exists_and_lists_limits(self):
        page = (self.site / 'unresolved' / 'index.html').read_text(encoding='utf-8')
        soup = BeautifulSoup(page, 'html.parser')
        self.assertIsNotNone(soup.select_one('#fallback-register') or soup.select_one('#unresolved'))
        self.assertIn('limitation', soup.get_text(' ', strip=True).lower())


if __name__ == '__main__':
    unittest.main()
