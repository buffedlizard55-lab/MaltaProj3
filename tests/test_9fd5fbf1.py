"""Session 9fd5fbf1: phone still-open finder and live-coverage gap register.

Presentation and dated research only. No probability is invented.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.build import exec_banner, glance, live_coverage_gaps

ROOT = Path(__file__).resolve().parents[1]


def match(i, name_a, name_b, start='2099-01-01T10:00:00Z', lock='2099-01-01T09:54:00Z'):
    return {
        'id': str(i), 'competition': 'CCT Test', 'starts_at': start, 'locks_at': lock,
        'availability': 'open', 'source_url': 'https://www.hotspawn.com/matches/x',
        'teams': [{'name': name_a}, {'name': name_b}],
        'analysis': {'method': 'market', 'source_url': 'https://polymarket.com/event/x',
                     'probabilities': [0.62, 0.38]},
        'pick_index': 0,
    }


class GlanceStillOpenChips(unittest.TestCase):
    def setUp(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        data = {'matches': [match(1, 'Spirit Academy', 'GenOne')], 'fallbacks': {}}
        self.html = glance(data, '', now=now)

    def test_status_chips_are_present_and_all_is_default(self):
        self.assertIn('data-glance-status="all"', self.html)
        self.assertIn('data-glance-status="open"', self.html)
        self.assertIn('Still open', self.html)
        self.assertIn('Locked', self.html)
        self.assertIn('aria-pressed="true"', self.html)

    def test_no_row_is_hidden_without_javascript(self):
        self.assertNotIn('hidden>', self.html.split('id="glance-empty"')[0])
        self.assertIn('id="glance-empty" hidden', self.html)

    def test_js_filters_open_and_locked(self):
        js = Path('assets/scout.js').read_text()
        self.assertIn('data-glance-status', js)
        self.assertIn('Still open', Path('scripts/build.py').read_text())
        lock_js = Path('assets/glance-lock.js').read_text()
        self.assertIn('list.appendChild(row)', lock_js)
        css = Path('assets/scout.css').read_text()
        self.assertIn('.glance-status', css)
        self.assertIn('min-height:44px', css)


class LiveCoverageGaps(unittest.TestCase):
    def test_missing_fixture_is_named_with_official_links_and_no_percent(self):
        data = {
            'matches': [match(1, 'A', 'B')],
            '_live_coverage': {
                'observed_at': '2026-10-23T04:58:00Z',
                'live_fixtures': [
                    {
                        'id': '1081605',
                        'teams': ['Phantom Academy', 'Banda chuya'],
                        'competition': 'CCT Europe 2026 Challengers #8',
                        'hotspawn_url': 'https://www.hotspawn.com/matches/phantom-academy-vs-banda-chuya-cct-europe-2026-challengers-8-1081605',
                        'hltv_url': 'https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8',
                    },
                    {
                        'id': '1',
                        'teams': ['A', 'B'],
                        'competition': 'CCT Test',
                        'hotspawn_url': 'https://www.hotspawn.com/matches/x',
                    },
                ],
            },
        }
        html = live_coverage_gaps(data, '')
        self.assertIn('id="live-coverage-gaps"', html)
        self.assertIn('Phantom Academy vs Banda chuya', html)
        self.assertIn('1081605', html)
        self.assertIn('https://www.hltv.org/matches/2399699/', html)
        self.assertNotIn('A vs B', html)
        self.assertNotIn('%', html.split('id="live-coverage-gaps"')[1])

    def test_blank_hotspawn_id_is_labelled_unverified(self):
        data = {
            'matches': [],
            '_live_coverage': {
                'observed_at': '2026-10-23T04:58:00Z',
                'live_fixtures': [{
                    'id': None,
                    'teams': ['JiJieHao', 'Eternal Fire'],
                    'competition': 'DraculaN Season 7',
                    'hltv_url': 'https://www.hltv.org/matches/2399638/jijiehao-vs-eternal-fire-digital-crusade-draculan-season-7',
                    'note': 'Lobby card had no permalink.',
                }],
            },
        }
        html = live_coverage_gaps(data, '')
        self.assertIn('Hotspawn id unverified', html)
        self.assertIn('JiJieHao vs Eternal Fire', html)

    def test_banner_only_links_the_section_when_the_record_is_loaded(self):
        empty = {'counts': {'upcoming': 1, 'unresolved': 0, 'model': 0},
                 'inventory_observed_at': '2026-10-22T13:21:33Z'}
        self.assertNotIn('live-coverage-gaps', exec_banner(empty, ''))
        loaded = dict(empty, _live_coverage={'observed_at': '2026-10-23T04:58:00Z'})
        self.assertIn('#live-coverage-gaps', exec_banner(loaded, ''))

    def test_research_record_has_source_urls_and_no_invented_picks(self):
        record = json.loads((ROOT / 'data/research/9fd5fbf1/live-coverage.json').read_text())
        self.assertTrue(record['source_urls'])
        self.assertTrue(all(u.startswith('https://') for u in record['source_urls']))
        self.assertIn('No value here is a probability or a pick', record['role'])
        missing = [f for f in record['live_fixtures'] if not f.get('in_published_snapshot')]
        self.assertGreaterEqual(len(missing), 8)
        for fixture in missing:
            if fixture.get('id'):
                self.assertTrue(str(fixture['hotspawn_url']).startswith('https://www.hotspawn.com/matches/'))
            else:
                self.assertIsNone(fixture.get('hotspawn_url'))
                self.assertTrue(str(fixture.get('hltv_url', '')).startswith('https://www.hltv.org/'))


if __name__ == '__main__':
    unittest.main()
