"""Session arena-3a010437: the independent re-read must be honest about what it read.

``scripts/3a010437_verify.py`` runs on a runner and re-reads every published row
against the original source that row cites. These tests pin the parts that can
silently lie:

* only the *series winner* market is re-read — a Map 1 price must never be
  compared with a series probability;
* a later price within the drift band is ``confirmed``, a larger drift is
  ``price_moved``, and a price that now favours the other side is
  ``pick_disagrees`` (never "confirmed");
* a research-model row is ``model_not_a_line`` — no price exists to re-read;
* an unreachable source is ``source_unreadable`` and the run never raises;
* the published markdown says "reachability only" for a non-Polymarket money
  row instead of implying the price was re-verified.

All HTTP is mocked; no network is touched.
"""
import importlib
import json
import unittest
from unittest import mock

import requests

from scripts import __dict__ as _unused  # noqa: F401  (package import smoke)

verifier = importlib.import_module('scripts.3a010437_verify')


def response(payload=None, *, status=200, text=None):
    instance = mock.Mock()
    instance.status_code = status
    instance.url = 'https://example.com/final'
    instance.text = text if text is not None else json.dumps(payload or {})
    if payload is None and text is None:
        instance.json.side_effect = ValueError('no json')
    else:
        instance.json.return_value = payload
    return instance


def event(prices=('0.62', '0.38'), *, title='Counter-Strike: Alpha vs Beta (BO3) - Test Cup'):
    """A Gamma event whose first market is a map market and whose second is the series."""
    return {
        'title': title, 'volume': 100,
        'markets': [
            {'question': 'Counter-Strike: Alpha vs Beta - Map 1 Winner',
             'outcomes': json.dumps(['Alpha', 'Beta']),
             'outcomePrices': json.dumps(['0.55', '0.45']),
             'groupItemTitle': 'Map 1 Winner', 'slug': 'x-game1'},
            {'question': 'Counter-Strike: Alpha vs Beta', 'sportsMarketType': 'moneyline',
             'outcomes': json.dumps(['Alpha', 'Beta']),
             'outcomePrices': json.dumps(list(prices)),
             'groupItemTitle': 'Moneyline', 'slug': 'x'},
        ],
    }


ANALYSIS = {
    'method': 'market', 'source': 'Polymarket',
    'source_url': 'https://polymarket.com/event/x',
    'source_api': 'https://gamma-api.polymarket.com/events/1',
    'probabilities': [0.62, 0.38],
}
TEAMS = ['Alpha', 'Beta']


class SeriesMarketSelection(unittest.TestCase):
    def test_a_map_market_is_never_used_for_a_series_probability(self):
        market = verifier._series_market(event(), TEAMS)
        self.assertEqual(market['sportsMarketType'], 'moneyline')

    def test_no_matching_market_returns_none(self):
        self.assertIsNone(verifier._series_market(
            {'markets': [{'question': 'Alpha vs Gamma - Map 1 Winner',
                          'outcomes': json.dumps(['Alpha', 'Gamma'])}]}, TEAMS))


class PolymarketReread(unittest.TestCase):
    def _run(self, payload, team='Alpha'):
        with mock.patch.object(verifier.requests, 'get', return_value=response(payload)):
            return verifier.polymarket_reread(ANALYSIS, TEAMS, 0)

    def test_matching_price_is_confirmed(self):
        result = self._run(event(('0.62', '0.38')))
        self.assertEqual(result['max_abs_delta'], 0.0)
        self.assertTrue(result['price_survives'])
        self.assertTrue(result['pick_still_favoured'])

    def test_small_drift_is_still_called_agreement(self):
        result = self._run(event(('0.64', '0.36')))
        self.assertTrue(result['price_survives'])
        self.assertAlmostEqual(result['max_abs_delta'], 0.02)

    def test_large_drift_is_a_move(self):
        result = self._run(event(('0.70', '0.30')))
        self.assertFalse(result['price_survives'])
        self.assertTrue(result['pick_still_favoured'])

    def test_a_flipped_favourite_is_reported_as_a_conflict(self):
        result = self._run(event(('0.35', '0.65')))
        self.assertFalse(result['pick_still_favoured'])
        row = {'method': 'market', 'identity': {'checked': False}, 'price': result,
               'arithmetic': {'sums_to_one': True, 'pick_is_larger': True}}
        self.assertEqual(verifier.verdict(row), 'pick_disagrees')

    def test_an_unreadable_endpoint_never_raises(self):
        with mock.patch.object(verifier.requests, 'get',
                               side_effect=requests.ConnectionError('blocked')):
            result = verifier.polymarket_reread(ANALYSIS, TEAMS, 0)
        self.assertIsNone(result['http_status'])
        self.assertIn('ConnectionError', result['error'])

    def test_a_row_without_an_event_endpoint_is_not_checked(self):
        analysis = dict(ANALYSIS)
        analysis.pop('source_api')
        result = verifier.polymarket_reread(analysis, TEAMS, 0)
        self.assertFalse(result['checked'])


class Verdicts(unittest.TestCase):
    def row(self, **overrides):
        base = {'method': 'market', 'identity': {'checked': True, 'http_status': 200, 'both_present': True},
                'price': {'checked': True, 'http_status': 200, 'comparisons': [], 'price_survives': True,
                          'pick_still_favoured': True},
                'arithmetic': {'sums_to_one': True, 'pick_is_larger': True}}
        base.update(overrides)
        return base

    def test_a_research_model_is_not_a_line(self):
        self.assertEqual(verifier.verdict(self.row(method='model')), 'model_not_a_line')

    def test_a_broken_arithmetic_pair_is_reported(self):
        self.assertEqual(verifier.verdict(self.row(arithmetic={'sums_to_one': False, 'pick_is_larger': True})),
                         'arithmetic_error')

    def test_a_hotspawn_title_without_both_teams_is_an_identity_mismatch(self):
        self.assertEqual(verifier.verdict(self.row(identity={'checked': True, 'http_status': 200,
                                                             'both_present': False})),
                         'identity_mismatch')

    def test_a_dead_source_is_unreadable(self):
        self.assertEqual(verifier.verdict(self.row(price={'checked': True, 'http_status': 403})),
                         'source_unreadable')

    def test_a_reachable_non_polymarket_surface_is_not_called_confirmed(self):
        self.assertEqual(verifier.verdict(self.row(price={'checked': True, 'http_status': 200})),
                         'source_reachable')


class Markdown(unittest.TestCase):
    def test_reachability_is_labelled_as_such(self):
        report = {
            'snapshot': {'active_rows': 1, 'inventory_generated_at': '2026-10-23T09:23:57Z'},
            'started_at': '2026-10-23T10:00:00Z', 'finished_at': '2026-10-23T10:01:00Z',
            'totals': {'source_reachable': 1},
            'rows': [{
                'id': '1', 'teams': ['Alpha', 'Beta'], 'method': 'bookmaker',
                'published_probabilities': [0.6, 0.4], 'published_pick_index': 0,
                'verdict': 'source_reachable', 'source_url': 'https://thunderpick.io/api/matches',
                'price': {'checked': True, 'http_status': 200, 'url': 'https://thunderpick.io/api/matches',
                          'observed_at': '2026-10-23T10:00:30Z'},
            }],
        }
        text = verifier.markdown(report)
        self.assertIn('reachability only', text)
        self.assertIn('| 1 | Alpha vs Beta |', text)
        self.assertIn('No row conflicts', text)

    def test_a_conflict_is_listed_for_review_with_its_url(self):
        report = {
            'snapshot': {'active_rows': 1, 'inventory_generated_at': 'x'},
            'started_at': 'a', 'finished_at': 'b', 'totals': {'pick_disagrees': 1},
            'rows': [{
                'id': '2', 'teams': ['Alpha', 'Beta'], 'method': 'market',
                'published_probabilities': [0.6, 0.4], 'published_pick_index': 0,
                'verdict': 'pick_disagrees', 'source_url': 'https://polymarket.com/event/x',
                'price': {'checked': True, 'comparisons': [], 'http_status': 200},
            }],
        }
        text = verifier.markdown(report)
        self.assertIn('Flagged for review', text)
        self.assertIn('https://polymarket.com/event/x', text)


if __name__ == '__main__':
    unittest.main()
