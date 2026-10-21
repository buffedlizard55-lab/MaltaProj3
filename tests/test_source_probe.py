"""Session 541cd43a — the unresolved register must say why, per source.

The brief asked for a separate section for unresolved picks *and the
limitations for generating picks for them*, inside the executive summary. This
test pins the dated source-availability block that renders the read-only probe:
statuses are copied, missing values stay blank, and nothing becomes a
probability.
"""
from __future__ import annotations

import unittest

from bs4 import BeautifulSoup

from scripts.build import source_probe_block


def probe():
    return {
        'generated_at': '2026-10-21T12:49:57Z',
        'blank_fixtures': [
            {
                'hotspawn_id': '1082762', 'teams': ['ex-CYBERSHOKE', 'BlinkDagger'],
                'competition': 'CIS LAN Championship #9',
                'hotspawn_source_url': 'https://www.hotspawn.com/matches/ex-cybershoke-vs-blinkdagger-1082762',
                'hltv': [{'request': {'url': 'https://www.hltv.org/matches/2399839/ex-cybershoke-vs-blinkdagger',
                                      'http_status': 403}}],
                'bo3': {'team_lookup': [{'name': 'ex-CYBERSHOKE', 'matches': 0}, {'name': 'BlinkDagger', 'id': 246}],
                        'bound': None, 'bet': None},
            },
            {
                'hotspawn_id': '1082837', 'teams': ['Zetta', 'LOS NINOS'],
                'competition': 'CCT South America 2026 Series #7',
                'hotspawn_source_url': 'https://www.hotspawn.com/matches/zetta-vs-los-ninos-1082837',
                'hltv': [{'request': {'url': 'https://www.hltv.org/matches/2399999/zetta-vs-los-ninos',
                                      'http_status': 403}}],
                'bo3': {'team_lookup': [{'name': 'Zetta', 'id': 23468}, {'name': 'LOS NINOS', 'id': 25500}],
                        'bound': None, 'bet': None},
            },
        ],
        'providers': [
            {'label': 'Bovada CS2', 'request': {'url': 'https://www.bovada.lv/sports/esports/counter-strike-2',
                                                'http_status': 200}},
            {'label': 'GG.bet CS2', 'request': {'url': 'https://gg.bet/en/esports/counter-strike',
                                                'http_status': 403}},
            {'label': '1xBet CS2 line', 'request': {'url': 'https://1xbet.com/Line/Counter-Strike-2',
                                                    'http_status': 203}},
        ],
    }


def dataset():
    return {
        'complete_picks': {'matches': [
            {'id': '1082762', 'origination': None, 'teams': [{'name': 'ex-CYBERSHOKE'}, {'name': 'BlinkDagger'}],
             'research': [{'stage': 'Research model cross-check (Valve official ratings)', 'status': 'unresolved',
                           'detail': 'ex-CYBERSHOKE: no Valve rating row found'}]},
            {'id': '1082837', 'origination': None, 'teams': [{'name': 'Zetta'}, {'name': 'LOS NINOS'}],
             'research': [{'stage': 'Research model cross-check (Valve official ratings)', 'status': 'unresolved',
                           'detail': 'LOS NINOS: no Valve rating row found'}]},
        ]},
        '_source_probe': probe(),
    }


class SourceProbeBlock(unittest.TestCase):
    def render(self, data=None):
        return BeautifulSoup(source_probe_block(data or dataset(), './'), 'html.parser')

    def test_counts_are_derived_from_statuses(self):
        text = self.render().get_text(' ', strip=True)
        self.assertIn('1 of 3', text)      # one provider answered 200
        self.assertIn('2 refused', text)   # 403 and 203
        self.assertIn('HTTP 200', text)

    def test_every_fixture_row_keeps_its_links(self):
        soup = self.render()
        rows = soup.select('.source-probe-table tbody tr')
        self.assertEqual(len(rows), 2)
        hrefs = [a['href'] for a in soup.select('.source-probe-table a[href]')]
        self.assertTrue(any('hltv.org/matches/2399839' in h for h in hrefs))
        self.assertTrue(any('bo3.gg/teams/246' in h for h in hrefs))
        self.assertTrue(any('hotspawn.com/matches' in h for h in hrefs))

    def test_blocker_text_comes_from_the_published_trail(self):
        text = self.render().get_text(' ', strip=True)
        self.assertIn('no rating', text)
        self.assertIn('no Valve rating row found', text)

    def test_missing_values_stay_blank_not_invented(self):
        data = dataset()
        data['_source_probe']['blank_fixtures'][0]['hltv'] = []
        soup = self.render(data)
        first = soup.select('.source-probe-table tbody tr')[0].get_text(' ', strip=True)
        self.assertIn('no verified HLTV match URL', first)

    def test_no_probability_is_rendered(self):
        text = self.render().get_text(' ', strip=True)
        self.assertNotIn('%', text)

    def test_absent_probe_renders_nothing(self):
        self.assertEqual(source_probe_block({}, './'), '')


if __name__ == '__main__':
    unittest.main()
