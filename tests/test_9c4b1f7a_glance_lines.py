"""Session 9c4b1f7a — the observed price is visible next to the phone estimate.

The brief asks for an analysis of the betting lines, not only a link to one.
These tests pin the literal renderer against the two stored quote shapes
(featured rows and origination rows), against the consensus rung, and against
the research-model rows that have no market price at all. No probability is
recomputed anywhere in this feature: the chip restates the row's own quote.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from scripts.build import glance, observed_price_label

BASE = datetime(2026, 10, 23, 9, 0, tzinfo=timezone.utc)


def featured_market(bid=(0.63, 0.36), ask=(0.64, 0.37)):
    return {
        'method': 'market', 'label': 'Market-implied estimate', 'source': 'Polymarket',
        'source_url': 'https://polymarket.com/event/cs2-x', 'probabilities': [0.635, 0.365],
        'pick_index': 0,
        'quotes': [
            {'bid': bid[0], 'ask': ask[0], 'spread': ask[0] - bid[0], 'midpoint': 0.635},
            {'bid': bid[1], 'ask': ask[1], 'spread': ask[1] - bid[1], 'midpoint': 0.365},
        ],
    }


class ObservedPriceLabel(unittest.TestCase):
    def test_featured_market_shows_both_sides_bid_and_ask(self):
        self.assertEqual(observed_price_label(featured_market()), '63–64¢ / 36–37¢')

    def test_featured_bookmaker_shows_decimal_odds(self):
        analysis = {
            'method': 'bookmaker', 'source': 'Thunderpick',
            'source_url': 'https://thunderpick.io/api/matches', 'probabilities': [0.55, 0.45],
            'quotes': [{'provider': 'Thunderpick', 'odds': [1.68, 2.05]}],
        }
        self.assertEqual(observed_price_label(analysis), 'line 1.68 / 2.05')

    def test_origination_market_arrays_render_as_cents(self):
        analysis = {
            'method': 'market', 'source': 'Polymarket',
            'source_url': 'https://polymarket.com/event/x', 'probabilities': [0.66, 0.34],
            'quotes': [{'provider': 'Polymarket', 'bid': [0.65, 0.31], 'ask': [0.69, 0.35]}],
        }
        self.assertEqual(observed_price_label(analysis), '65–69¢ / 31–35¢')

    def test_origination_bookmaker_odds_render_with_two_decimals(self):
        analysis = {
            'method': 'bookmaker', 'source': 'Thunderpick',
            'source_url': 'https://thunderpick.io/api/matches', 'probabilities': [0.75, 0.25],
            'quotes': [{'provider': 'Thunderpick', 'odds': [1.2, 4.0]}],
        }
        self.assertEqual(observed_price_label(analysis), 'line 1.20 / 4.00')

    def test_a_consensus_counts_its_books_instead_of_pretending_to_be_one(self):
        analysis = {
            'method': 'consensus', 'source': 'Polymarket + Thunderpick + Bovada + Pinnacle',
            'source_url': 'https://polymarket.com/event/x', 'probabilities': [0.762, 0.238],
            'quotes': [{'provider': name} for name in ('Polymarket', 'Thunderpick', 'Bovada', 'Pinnacle')],
        }
        self.assertEqual(observed_price_label(analysis), 'median of 4 books')
        without_quotes = dict(analysis)
        without_quotes.pop('quotes')
        self.assertEqual(observed_price_label(without_quotes), 'median of 4 books')

    def test_a_model_price_never_claims_a_market_line(self):
        self.assertEqual(observed_price_label({'method': 'model', 'source': 'Valve official standings'}), '')
        self.assertEqual(observed_price_label(None), '')
        self.assertEqual(observed_price_label({'method': 'market'}), '')

    def test_malformed_odds_are_ignored_rather_than_invented(self):
        analysis = {'method': 'bookmaker', 'quotes': [{'odds': [0.9, 1.1]}]}
        self.assertEqual(observed_price_label(analysis), '')
        analysis = {'method': 'bookmaker', 'quotes': [{'odds': ['x', 'y']}]}
        self.assertEqual(observed_price_label(analysis), '')


def match(i, name_a, name_b, analysis, start='2099-01-01T10:00:00Z', lock='2099-01-01T09:54:00Z'):
    return {
        'id': str(i), 'competition': 'CCT Test', 'starts_at': start, 'locks_at': lock,
        'availability': 'open', 'source_url': f'https://www.hotspawn.com/matches/x-{i}',
        'teams': [{'name': name_a}, {'name': name_b}],
        'analysis': analysis, 'pick_index': 0 if analysis else None,
    }


class GlanceRendersTheLine(unittest.TestCase):
    def render(self, data):
        return BeautifulSoup(glance(data, '', now=BASE), 'html.parser')

    def test_each_money_row_shows_the_price_and_the_fixture_chip(self):
        soup = self.render({'matches': [match(1, 'A', 'B', featured_market())], 'fallbacks': {}})
        chip = soup.select_one('.glance-line')
        self.assertIsNotNone(chip)
        self.assertIn('Observed: 63–64¢ / 36–37¢', chip.get_text(' ', strip=True))
        labels = [a.get_text(strip=True) for a in soup.select('.glance-links a.source-link')]
        self.assertIn('Hotspawn fixture', labels)
        self.assertNotIn('Hotspawn', labels)

    def test_a_model_row_has_no_price_chip(self):
        model = {'method': 'model', 'source': 'Valve official standings',
                 'source_url': 'https://github.com/ValveSoftware/x.md',
                 'probabilities': [0.6, 0.4]}
        soup = self.render({'matches': [match(2, 'A', 'B', model)], 'fallbacks': {}})
        self.assertIsNone(soup.select_one('.glance-line'))

    def test_an_unresolved_row_has_no_price_chip_and_keeps_its_why_link(self):
        soup = self.render({'matches': [match(3, 'A', 'B', None)], 'fallbacks': {}})
        self.assertIsNone(soup.select_one('.glance-line'))
        self.assertIsNotNone(soup.select_one('#glance-list') or soup.select_one('.glance-row'))

    def test_the_chip_never_changes_the_published_probabilities(self):
        analysis = featured_market()
        soup = self.render({'matches': [match(4, 'A', 'B', analysis)], 'fallbacks': {}})
        text = soup.select_one('.glance-choice').get_text(' ', strip=True)
        self.assertIn('63.5%', text)
        self.assertIn('36.5%', text)


if __name__ == '__main__':
    unittest.main()
