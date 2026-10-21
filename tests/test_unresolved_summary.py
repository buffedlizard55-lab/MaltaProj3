"""The executive summary must carry its own unresolved register.

The brief asked for a separate section listing every match without a pick and
the limitations that caused it, reachable from the summary itself, not only
from the origination page. These tests pin that contract and the safety rules
around it: a blank is never given a probability, a default 50/50 or a pick.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from scripts.build import summary, unresolved_register

ROOT = Path(__file__).resolve().parents[1]


def blank_match(i: int, *, hltv: bool = True) -> dict:
    research = [
        {'stage': 'Betting market (Polymarket series winner)', 'status': 'unresolved',
         'detail': 'No unique exact-name, exact-start-time fixture; sponsor names are not aliased.',
         'source_url': 'https://polymarket.com/esports/cs2'},
        {'stage': 'Research model cross-check (Valve official ratings)', 'status': 'unresolved',
         'detail': 'TeamB has no Valve rating row found (including registry aliases).',
         'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'},
    ]
    if hltv:
        research.insert(0, {'stage': 'HLTV research', 'status': 'checked',
                            'detail': 'Exact teams/time confirmed on HLTV; no original bookmaker price verified.',
                            'source_url': f'https://www.hltv.org/matches/23990{i:02d}/team-a-vs-team-b'})
    return {
        'id': str(9000 + i),
        'teams': [{'id': 'a', 'name': f'Team A{i}'}, {'id': 'b', 'name': f'Team B{i}'}],
        'competition': 'CCT Europe 2026 Series #12 Play-In',
        'starts_at': '2026-10-19T13:00:00Z',
        'locks_at': '2026-10-19T12:54:00Z',
        'availability': 'open',
        'source_url': f'https://www.hotspawn.com/matches/team-a-vs-team-b-{9000 + i}',
        'analysis': None, 'pick_index': None, 'origination': None,
        'observed_at': '2026-10-19T04:00:00Z',
        'research': research, 'limitations': [], 'tier': 'c',
        'source_status': 'scheduled', 'best_of': 3,
    }


def dataset(rows):
    return {'generated_at': '2026-10-19T04:00:00Z',
            'counts': {'upcoming': len(rows), 'unresolved': len(rows)},
            'matches': rows,
            'complete_picks': {'generated_at': '2026-10-19T04:00:00Z',
                               'counts': {'active': len(rows), 'resolved': 0, 'with_pick': 0,
                                          'unresolved': len(rows), 'market': 0, 'bookmaker': 0,
                                          'consensus': 0, 'reference': 0, 'model': 0},
                               'matches': rows}}


class UnresolvedRegisterTests(unittest.TestCase):
    def test_every_blank_fixture_is_listed_with_blocker_and_sources(self):
        rows = [blank_match(1), blank_match(2, hltv=False)]
        html = unresolved_register(dataset(rows), './')
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select('#unresolved-register .unresolved-summary-card')
        self.assertEqual(len(cards), 2)
        text = soup.get_text(' ', strip=True)
        self.assertIn('Team A1', text)
        self.assertIn('Team B2', text)
        self.assertIn('No verified pick', text)
        # Session arena-75de2710: the label names the actual gap. The fixture
        # has one rated and one unrated side, so "no rating" implied a blanket
        # absence that the trail does not support.
        self.assertIn('one team unranked', text)
        first = cards[0]
        self.assertIn('https://www.hotspawn.com/matches/team-a-vs-team-b-9001', str(first))
        self.assertIn('https://www.hltv.org/matches/', str(first))
        self.assertIn('Full trail', first.get_text(' ', strip=True))

    def test_a_blank_is_never_given_a_probability_or_a_default_5050(self):
        html = unresolved_register(dataset([blank_match(1)]), './')
        self.assertNotIn('50.0%', html)
        self.assertNotIn('50%', html)
        self.assertNotIn('Pick', BeautifulSoup(html, 'html.parser').select_one('h3').get_text())
        self.assertNotRegex(html, r'\b\d{1,3}\.\d%')

    def test_no_unresolved_rows_states_the_dated_observation(self):
        data = dataset([])
        html = unresolved_register(data, './')
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        self.assertIn('No unresolved fixtures in this snapshot', text)

    def test_standing_limitations_are_published_with_the_register(self):
        text = BeautifulSoup(unresolved_register(dataset([blank_match(1)]), './'),
                             'html.parser').get_text(' ', strip=True)
        self.assertIn('Hotspawn participation percentages', text)
        self.assertIn('not evidence that no market exists', text)
        self.assertIn('uncalibrated', text)
        self.assertIn('four-hour refresh', text)

    def test_summary_links_to_the_register_and_renders_it(self):
        data = json.loads((ROOT / 'data/latest.json').read_text())
        data['complete_picks'] = dataset([blank_match(1)])['complete_picks']
        data['_twc_day4'] = {'matches': [], 'not_in_hotspawn_snapshot': [], 'lines': {}}
        with patch('scripts.build.contrarian_review', return_value=''), \
             patch('scripts.build.contrarian_briefing', return_value=''):
            soup = BeautifulSoup(summary(data, './'), 'html.parser')
        bar = soup.select_one('nav.start-here')
        self.assertIsNotNone(bar)
        hrefs = [a['href'] for a in bar.select('a[href]')]
        self.assertIn('./#unresolved-register', hrefs)
        self.assertIsNotNone(soup.select_one('#unresolved-register'))
        self.assertIn('Team A1', soup.select_one('#unresolved-register').get_text(' ', strip=True))


if __name__ == '__main__':
    unittest.main()
