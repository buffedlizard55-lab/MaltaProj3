"""BD-2: a phone-index source link must name the site it opens.

The executive summary is the page a reader uses on a phone. Until this session
every money link on it read "Bookmaker" regardless of destination, so a consensus
row whose evidence link is a Polymarket event, or a relayed row that opens bo3.gg,
told the reader it would land on a sportsbook. These tests pin the label to the
row's own `source_url` and `quotes`; no probability, pick or provider is invented.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from scripts.build import glance, source_link_label

BASE = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)


def match(i, analysis=None, pick=0, hours=5):
    start = BASE + timedelta(hours=hours)
    row = {
        'id': str(i),
        'teams': [{'id': f'a{i}', 'name': 'Alpha'}, {'id': f'b{i}', 'name': 'Beta'}],
        'competition': 'Test Cup',
        'starts_at': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'locks_at': (start - timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'availability': 'open',
        'source_url': f'https://www.hotspawn.com/matches/x-{i}',
        'analysis': analysis, 'pick_index': pick if analysis else None,
        'limitations': [], 'research': [], 'tier': 'c', 'best_source': None,
    }
    return row


def analysis(method, url, quotes=(), probability=0.6):
    return {'method': method, 'label': 'test label',
            'probabilities': [probability, 1 - probability],
            'fair_decimal': [round(1 / probability, 3), round(1 / (1 - probability), 3)],
            'observed_at': BASE.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'source': 'test source', 'source_url': url, 'quotes': list(quotes)}


class SourceLinkLabelTests(unittest.TestCase):
    def test_a_polymarket_market_row_names_polymarket(self):
        self.assertEqual(source_link_label(analysis('market', 'https://polymarket.com/event/cs2-x')), 'Polymarket')

    def test_a_consensus_row_names_the_site_it_opens_and_counts_the_rest(self):
        quotes = [{'provider': 'Polymarket'}, {'provider': 'Thunderpick'}, {'provider': 'Bovada'}]
        label = source_link_label(analysis('consensus', 'https://polymarket.com/event/cs2-x', quotes))
        self.assertEqual(label, 'Polymarket +2')

    def test_a_relayed_bookmaker_names_the_relay_it_opens(self):
        label = source_link_label(analysis('bookmaker', 'https://bo3.gg/matches/a-vs-b-22-10-2026'))
        self.assertEqual(label, 'bo3.gg')

    def test_a_valve_model_row_names_the_official_standings(self):
        label = source_link_label(analysis('model', 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/x.md'))
        self.assertEqual(label, 'Valve standings')

    def test_an_hltv_model_row_names_hltv(self):
        self.assertEqual(source_link_label(analysis('model', 'https://www.hltv.org/ranking/teams')), 'HLTV')

    def test_an_unrecognised_host_falls_back_to_the_host_itself(self):
        label = source_link_label(analysis('bookmaker', 'https://example-book.test/esports/cs2'))
        self.assertEqual(label, 'example-book.test')

    def test_a_missing_url_uses_the_method_not_a_provider(self):
        self.assertEqual(source_link_label(analysis('market', '')), 'Market line')

    def test_the_label_never_names_a_provider_the_row_does_not_use(self):
        # A single-provider consensus must not imply a second source.
        label = source_link_label(analysis('consensus', 'https://kalshi.com/markets/kxcs2game/x',
                                            [{'provider': 'Kalshi'}]))
        self.assertEqual(label, 'Kalshi +1')


class GlanceLinkTests(unittest.TestCase):
    def test_the_phone_index_never_labels_a_polymarket_link_bookmaker(self):
        row = match(1, analysis('bookmaker', 'https://polymarket.com/event/cs2-x'))
        html = glance({'matches': [row], 'fallbacks': {}}, '', now=BASE)
        self.assertIn('rel="noopener noreferrer">Polymarket<', html)
        # The method badge may still say "Bookmaker" (that is the method); the
        # *link* must not, because the reader lands on Polymarket.
        self.assertNotIn('rel="noopener noreferrer">Bookmaker<', html)

    def test_the_phone_index_shows_the_consensus_extra_providers(self):
        row = match(1, analysis('consensus', 'https://polymarket.com/event/cs2-x',
                                [{'provider': 'Polymarket'}, {'provider': 'Thunderpick'}, {'provider': 'Bovada'}]))
        html = glance({'matches': [row], 'fallbacks': {}}, '', now=BASE)
        self.assertIn('>Polymarket +2<', html)

    def test_a_researched_relay_row_names_bo3gg_on_the_phone_index(self):
        row = match(1, None)
        fallback = {row['id']: {'id': row['id'], 'teams': row['teams'], 'pick_index': 0,
                                'upgraded_from_featured_model': False,
                                'origination': analysis('bookmaker', 'https://bo3.gg/matches/a-vs-b-22-10-2026')}}
        html = glance({'matches': [row], 'fallbacks': fallback}, '', now=BASE)
        self.assertIn('>bo3.gg<', html)

    def test_every_published_link_label_is_derived_from_its_own_url(self):
        rows = [match(1, analysis('market', 'https://polymarket.com/event/cs2-x')),
                match(2, analysis('bookmaker', 'https://thunderpick.io/esports/counter-strike')),
                match(3, analysis('model', 'https://github.com/ValveSoftware/counter-strike_regional_standings'))]
        html = glance({'matches': rows, 'fallbacks': {}}, '', now=BASE)
        for label in ('>Polymarket<', '>Thunderpick<', '>Valve standings<'):
            self.assertIn(label, html)


if __name__ == '__main__':
    unittest.main()
