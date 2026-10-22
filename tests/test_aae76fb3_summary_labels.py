"""Session arena-aae76fb3: every phone-summary row names the source it links.

These are rendering contracts only. Each fixture and origination record below is
synthetic, so no probability is invented for a real match and no network source
is contacted. The contracts are:

* a consensus row is never published as "Bookmaker" over one provider's URL;
* the link text names the provider the row's own provenance actually names;
* a researched money line keeps the required "Researched" marker *and* shows
  whether it is money-backed or a research model;
* the executive-summary unresolved tile says "unresolved" and never reads
  "0 without a line" beside a non-zero model-only count.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from scripts.build import analysis_source_label, exec_banner, glance

BASE = datetime(2026, 10, 22, 1, 0, tzinfo=timezone.utc)


def match(i, *, hours=6, resolved=False):
    start = BASE + timedelta(hours=hours)
    return {
        'id': str(i),
        'teams': [{'id': f'a{i}', 'name': f'Alpha{i}'}, {'id': f'b{i}', 'name': f'Beta{i}'}],
        'competition': 'Test Cup',
        'starts_at': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'locks_at': (start - timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'availability': 'open',
        'source_url': f'https://www.hotspawn.com/matches/x-{i}',
        'source_api': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2',
        'lobby_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{i}',
        'evidence': 'data/evidence/hotspawn-fixtures.json',
        'competition_id': '1', 'series_format': None, 'lock_offset_sec': 360,
        'source_end_at': None, 'analysis': None, 'pick_index': None,
        'observed_at': BASE.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'research': [], 'limitations': [], 'tier': 'c', 'source_status': 'scheduled',
        'best_of': None,
    }


def fallback(m, *, method, source, source_url, probability=0.6, pick=0):
    return {
        'id': m['id'], 'pick_index': pick,
        'origination': {
            'method': method, 'label': f'{method} label',
            'probabilities': [probability, 1 - probability],
            'fair_decimal': [round(1 / probability, 3), round(1 / (1 - probability), 3)],
            'observed_at': m['observed_at'], 'source': source, 'source_url': source_url,
            'quotes': [],
        },
    }


def render(m, fb):
    return glance({'matches': [m], 'fallbacks': {m['id']: fb}}, '', now=BASE)


class SourceLinkLabelTests(unittest.TestCase):
    def test_a_consensus_is_not_called_a_bookmaker(self):
        m = match(1)
        fb = fallback(m, method='consensus', source='Bovada + Pinnacle',
                      source_url='https://www.bovada.lv/sports/esports/counter-strike-2/x',
                      probability=0.3, pick=1)
        html = render(m, fb)
        soup = BeautifulSoup(html, 'html.parser')
        labels = [a.get_text(strip=True) for a in soup.select('.glance-links a.source-link')]
        self.assertIn('Consensus (2 sources)', labels)
        self.assertNotIn('Bookmaker', labels)
        hrefs = [a.get('href') for a in soup.select('.glance-links a.source-link')]
        self.assertIn('https://www.bovada.lv/sports/esports/counter-strike-2/x', hrefs)

    def test_each_money_provider_is_named_on_its_own_row(self):
        cases = [
            ('market', 'Polymarket', 'https://polymarket.com/event/cs2-x', 'Polymarket'),
            ('market', 'Kalshi', 'https://kalshi.com/markets/kxcs2game/x', 'Kalshi'),
            ('bookmaker', 'Thunderpick', 'https://thunderpick.io/match/1', 'Thunderpick'),
            ('bookmaker', 'Bovada', 'https://www.bovada.lv/sports/esports/x', 'Bovada'),
            ('bookmaker', 'Pinnacle', 'https://www.pinnacle.com/en/esports/x', 'Pinnacle'),
            ('reference', 'EGamersWorld (bookmaker average)',
             'https://egamersworld.com/counterstrike/match/x', 'EGamersWorld'),
        ]
        for index, (method, source, url, expected) in enumerate(cases, start=1):
            with self.subTest(expected=expected):
                m = match(index)
                html = render(m, fallback(m, method=method, source=source, source_url=url))
                self.assertIn(f'>{expected}<', html)

    def test_a_research_model_still_names_the_model(self):
        m = match(9)
        fb = fallback(m, method='model', source='Valve official standings',
                      source_url='https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/x.md')
        self.assertIn('Valve', render(m, fb))

    def test_the_helper_never_claims_a_provider_the_record_does_not_name(self):
        self.assertEqual(analysis_source_label({'method': 'consensus', 'source': 'Polymarket + Kalshi',
                                                'source_url': 'https://polymarket.com/event/x'}),
                         'Consensus (2 sources)')
        self.assertEqual(analysis_source_label({'method': 'reference', 'source': 'Unknown aggregate',
                                                'source_url': 'https://example.com/x'}), 'Aggregated')
        self.assertEqual(analysis_source_label({'method': 'guidance', 'source': 'Unknown',
                                                'source_url': 'https://example.com/x'}), 'Wide book')
        self.assertEqual(analysis_source_label({}), 'Source')


class FallbackBadgeTests(unittest.TestCase):
    def test_a_researched_money_line_shows_both_markers(self):
        m = match(2)
        html = render(m, fallback(m, method='consensus', source='Bovada + Pinnacle',
                                  source_url='https://www.bovada.lv/x'))
        self.assertIn('>Researched</span>', html)
        self.assertIn('>Consensus</span>', html)

    def test_a_researched_model_keeps_only_the_research_marker(self):
        m = match(3)
        html = render(m, fallback(m, method='model', source='Valve official standings',
                                  source_url='https://github.com/ValveSoftware/x'))
        self.assertIn('>Researched</span>', html)
        self.assertNotIn('badge green', html)


class UnresolvedTileTests(unittest.TestCase):
    def data(self):
        return {
            'generated_at': '2026-10-22T05:37:07Z',
            'inventory_observed_at': '2026-10-22T05:36:38Z',
            'counts': {'upcoming': 33},
            'complete_picks': {
                'generated_at': '2026-10-22T05:37:07Z',
                'counts': {'active': 33, 'resolved': 33, 'with_pick': 33,
                           'unresolved': 0, 'model': 18, 'market': 10,
                           'bookmaker': 2, 'consensus': 2, 'reference': 1},
            },
        }

    def test_the_tile_says_unresolved_and_names_the_model_only_count(self):
        text = BeautifulSoup(exec_banner(self.data(), './'), 'html.parser').get_text(' ')
        self.assertIn('0 unresolved', text)
        self.assertIn('18 model-only (no betting line)', text)
        self.assertNotIn('without a line', text)

    def test_the_tile_still_links_the_unresolved_section(self):
        soup = BeautifulSoup(exec_banner(self.data(), './'), 'html.parser')
        hrefs = [a.get('href') for a in soup.select('.exec-banner-actions a')]
        self.assertIn('./origination/#unresolved', hrefs)


if __name__ == '__main__':
    unittest.main()
