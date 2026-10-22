"""A56 executive-summary provenance and no-side wording regressions.

These are synthetic rendering fixtures only: no match probability is created,
changed or treated as live evidence. The contracts distinguish an unresolved
fixture from a resolved model estimate, and preserve a researched fallback's
actual money/bookmaker method instead of hiding it behind a generic badge.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from scripts.build import basis_badge, exec_banner, glance, no_line_register


def banner_data() -> dict:
    return {
        'complete_picks': {
            'counts': {
                'active': 46,
                'resolved': 46,
                'with_pick': 45,
                'unresolved': 0,
                'model': 20,
                'guidance': 0,
            },
            'generated_at': '2026-10-22T07:30:00Z',
        },
        'counts': {'upcoming': 46, 'model': 20, 'unresolved': 0},
        'inventory_observed_at': '2026-10-22T07:29:00Z',
    }


class ExecutiveBannerTests(unittest.TestCase):
    def test_banner_separates_unresolved_no_side_and_model_only(self):
        text = BeautifulSoup(exec_banner(banner_data(), './'), 'html.parser').get_text(' ', strip=True)
        self.assertIn('0 unresolved', text)
        self.assertIn('1 no-side estimate', text)
        self.assertIn('20 model-only', text)
        self.assertNotIn('0 without a line', text)

    def test_banner_probability_copy_is_literal_and_complete(self):
        html = exec_banner(banner_data(), './')
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        self.assertIn("both teams' probabilities shown", text)
        self.assertNotIn('% shown', text)
        self.assertNotIn('sub\\', html)

    def test_singular_no_side_estimate_is_grammatical(self):
        data = banner_data()
        data['complete_picks']['counts']['with_pick'] = 44
        text = BeautifulSoup(exec_banner(data, './'), 'html.parser').get_text(' ', strip=True)
        self.assertIn('2 no-side estimates', text)


class ResearchedMethodBadgeTests(unittest.TestCase):
    def test_researched_bookmaker_keeps_money_method_visible(self):
        html = basis_badge({'method': 'bookmaker'}, researched=True)
        self.assertIn('>Bookmaker</span>', html)
        self.assertNotIn('>Researched</span>', html)

    def test_every_recognised_money_method_survives_researched_fallback(self):
        expected = {
            'market': 'Market line',
            'bookmaker': 'Bookmaker',
            'consensus': 'Consensus',
            'reference': 'Aggregated',
            'guidance': 'Wide book',
        }
        for method, label in expected.items():
            with self.subTest(method=method):
                self.assertIn(f'>{label}</span>', basis_badge({'method': method}, researched=True))

    def test_research_model_remains_explicitly_researched(self):
        self.assertIn('>Researched</span>', basis_badge({'method': 'model'}, researched=True))


class EvenEstimateDisplayTests(unittest.TestCase):
    def setUp(self):
        self.match = {
            'id': 'even-fixture',
            'teams': [{'name': 'Alpha'}, {'name': 'Beta'}],
            'competition': 'Test Cup',
            'starts_at': '2026-10-23T22:00:00Z',
            'locks_at': '2026-10-23T21:54:00Z',
            'availability': 'open',
            'source_url': 'https://www.hotspawn.com/matches/even-fixture',
            'analysis': None,
            'pick_index': None,
        }
        self.fallback = {
            **self.match,
            'origination': {
                'method': 'model',
                'label': 'HLTV-ranking research estimate',
                'probabilities': [0.5, 0.5],
                'fair_decimal': [2.0, 2.0],
                'source': 'HLTV world ranking',
                'source_url': 'https://www.hltv.org/ranking/teams/2026/october/19',
                'observed_at': '2026-10-22T07:30:00Z',
            },
            'research': [],
        }

    def test_glance_shows_both_equal_probabilities_and_method(self):
        html = glance({'matches': [self.match], 'fallbacks': {'even-fixture': self.fallback}},
                      './', now=datetime(2026, 10, 22, tzinfo=timezone.utc))
        self.assertIn('Alpha 50.0%', html)
        self.assertIn('Beta 50.0%', html)
        self.assertIn('no side', html)
        self.assertIn('>Researched</span>', html)

    def test_model_only_register_calls_no_side_an_estimate_not_a_pick(self):
        data = {
            'complete_picks': {
                'matches': [self.fallback],
                'counts': {'active': 1, 'resolved': 1, 'with_pick': 0, 'unresolved': 0},
            },
            'matches': [self.match],
            'counts': {'upcoming': 1},
        }
        html = no_line_register(data, './')
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        self.assertIn('carry a research estimate', text)
        self.assertNotIn('carry a pick', text)
        self.assertIn('Alpha 50.0%', text)
        self.assertIn('Beta 50.0%', text)


if __name__ == '__main__':
    unittest.main()
