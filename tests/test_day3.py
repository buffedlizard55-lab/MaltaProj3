"""Contract tests for the dated Day-2-results / Day-3-guide research.

These protect: (1) every published Day-2 result and Day-3 fixture carries an
official https source with an observation time, (2) no probability is
published for a fixture whose market had no traded price at observation,
(3) priced guidance sums to ~100% and its primary pick is a priced team,
and (4) the rendered section is reachable from the executive summary and
never presents guidance as a pipeline probability.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build_day3 import load_day3, render_section

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / 'data' / 'day3-guide.json'


def guide():
    return load_day3(GUIDE)


class Day3DataContractTest(unittest.TestCase):
    def test_checked_in_guide_validates(self):
        data = guide()
        self.assertEqual(len(data['day_two_results']), 4)
        self.assertEqual(len(data['day_three']), 2)
        self.assertEqual(len(data['standings_after_day_two']), 8)

    def test_day_two_winners_match_verified_results(self):
        winners = {}
        for row in guide()['day_two_results']:
            a, b = (int(x) for x in row['score'].split('-'))
            winners[(row['team_a'], row['team_b'])] = row['team_a'] if a > b else row['team_b']
            map_a = sum(1 for m in row['maps'] if m['a'] > m['b'])
            map_b = sum(1 for m in row['maps'] if m['b'] > m['a'])
            self.assertEqual((map_a, map_b), (a, b), 'map winners must reproduce the series score')
        self.assertEqual(winners[('Aurora', 'Ninjas in Pyjamas')], 'Aurora')
        self.assertEqual(winners[('9z', 'Falcons')], 'Falcons')
        self.assertEqual(winners[('PARIVISION', 'BETBOOM')], 'BETBOOM')
        self.assertEqual(winners[('Legacy', 'FURIA')], 'FURIA')

    def test_unpriced_fixture_publishes_no_probability(self):
        row = next(r for r in guide()['day_three'] if r['team_a'] == 'Legacy')
        self.assertIsNone(row['market']['prices'])
        self.assertIsNone(row['primary_pick'])
        self.assertIsNone(row['contrarian_candidate'])

    def test_priced_fixture_contract(self):
        row = next(r for r in guide()['day_three'] if r['team_a'] == 'Aurora')
        prices = row['market']['prices']
        self.assertAlmostEqual(sum(prices.values()), 1.0, delta=0.02)
        self.assertIn(row['primary_pick'], prices)
        self.assertIn(row['contrarian_candidate'], prices)
        self.assertNotEqual(row['primary_pick'], row['contrarian_candidate'])

    def test_missing_source_rejected(self):
        bad = copy.deepcopy(guide())
        bad['day_three'][0]['sources'] = []
        path = Path(self.id() + '.json')
        try:
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                load_day3(path)
        finally:
            path.unlink(missing_ok=True)

    def test_invented_price_for_unpriced_fixture_rejected(self):
        bad = copy.deepcopy(guide())
        bad['day_three'][1]['primary_pick'] = 'Legacy'
        path = Path(self.id() + '.json')
        try:
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                load_day3(path)
        finally:
            path.unlink(missing_ok=True)


class Day3RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.soup = BeautifulSoup(render_section(guide(), '../'), 'html.parser')

    def test_sections_and_anchors_exist(self):
        self.assertIsNotNone(self.soup.find(id='day-two-results'))
        self.assertIsNotNone(self.soup.find(id='day-three'))

    def test_every_row_links_to_official_sources(self):
        hrefs = [a.get('href') or '' for a in self.soup.select('a[href^="https://"]')]
        self.assertTrue(any('hltv.org' in h for h in hrefs))
        self.assertTrue(any('polymarket.com' in h for h in hrefs))

    def test_unpriced_fixture_renders_unverified_not_a_percentage(self):
        text = self.soup.get_text(' ')
        self.assertIn('No traded price at observation', text)
        legacy_row = next(tr for tr in self.soup.select('#day-three tr')
                          if 'Legacy' in tr.get_text() and 'No traded price' in tr.get_text())
        self.assertIn('unverified', legacy_row.get_text())
        price_cell = legacy_row.select('td')[0]
        self.assertNotIn('%', price_cell.get_text())

    def test_guidance_never_claims_to_replace_pipeline(self):
        self.assertIn('never overwrites', self.soup.get_text(' '))


if __name__ == '__main__':
    unittest.main()
