"""Session bd4f77c6 — a published pick must name the rung that produced it.

Two first-hand defects were found on the live site on 22 October 2026:

1. `scripts/originate.py` assigned the own-line network quote to the variable
   `model` before the selection ladder. The ladder tests `elif model:` before
   `elif network_quote:`, so every network-resolved fixture was published with
   the label "Research model estimate (Valve official ratings)" and with the
   generic Valve limitation instead of the network model's own inputs,
   uncertainty and low-confidence note. The same assignment also let the lowest
   rung overwrite a resolved Valve or results model.
2. `scripts/build.py`'s executive-summary note hardcoded "a verified Thunderpick
   paired-price book" for every fixture the featured method left blank, which was
   false for rows resolved by the Valve, results or network models.

These tests pin both directions: the label follows the quote that actually won,
the higher rung keeps precedence, and the executive summary repeats only the
rungs the snapshot really used.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from scripts import build, originate

UTC = timezone.utc
NOW = datetime(2026, 10, 22, 1, 0, tzinfo=UTC)


def network_quote(probability: float = 0.778) -> dict:
    """The shape `scripts.network_model.estimate_fixture` publishes."""
    return {
        'provider': 'Own network model (bo3.gg results graph)',
        'family': 'network',
        'method': 'model',
        'model_version': 'network-bt-1',
        'probabilities': [probability, 1 - probability],
        'inputs': [
            {'name': 'benched gods', 'team_id': 13599, 'points': 1483.2, 'se': 71.4, 'series': 11,
             'anchored': False, 'anchor_points': None,
             'source': 'Own network Bradley–Terry fit over bo3.gg finished series',
             'source_url': 'https://bo3.gg/teams/13599'},
            {'name': 'TitanFlow', 'team_id': 263800, 'points': 1836.9, 'se': 88.1, 'series': 9,
             'anchored': False, 'anchor_points': None,
             'source': 'Own network Bradley–Terry fit over bo3.gg finished series',
             'source_url': 'https://bo3.gg/teams/263800'},
        ],
        'rating_sd_diff': 113.4,
        'interval': [0.6321, 0.8842],
        'n_series': 9,
        'graph_matches': 4659,
        'graph_anchors': 269,
        'low_confidence': True,
        'source_url': 'https://bo3.gg/matches',
        'identity_bridge': 'exact_team_name_lookup',
        'evidence_file': 'data/origination/evidence/live-bo3-graph.json',
        'evidence_sha256': '0' * 64,
        'observed_at': NOW.isoformat(),
    }


def fixture(**overrides) -> dict:
    match = {
        'id': '1081597',
        'teams': [{'id': '244042', 'name': 'benched gods'}, {'id': '263800', 'name': 'TitanFlow'}],
        'competition': 'CCT Europe 2026 Challenges #8',
        'starts_at': (NOW + timedelta(hours=10)).isoformat().replace('+00:00', 'Z'),
        'locks_at': (NOW + timedelta(hours=9, minutes=54)).isoformat().replace('+00:00', 'Z'),
        'availability': 'open',
        'tier': 'c',
        'source_url': 'https://www.hotspawn.com/matches/benched-gods-vs-titanflow-1081597',
        'lobby_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1081597',
        'analysis': None,
        'pick_index': None,
        'source_status': 'scheduled',
        'observed_at': NOW.isoformat(),
        'best_of': None,
    }
    match.update(overrides)
    return match


class NetworkProvenanceTest(unittest.TestCase):
    def _resolve(self, match: dict):
        return originate.resolve_match(match, [], [], [], None, {'aliases': []}, NOW)

    def test_network_quote_is_labelled_as_the_network_model(self):
        result = self._resolve(fixture(_network=network_quote()))
        chosen = result['origination']
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen['method'], 'model')
        self.assertEqual(chosen['label'], 'Own network estimate (bo3.gg results graph)')
        self.assertEqual(chosen['source'], 'Own network model (bo3.gg results graph)')
        # The label may never claim an official rating table produced this number.
        self.assertNotIn('Valve official ratings', chosen['label'])
        joined = ' '.join(result['limitations'])
        self.assertIn('network model', joined)
        self.assertIn('4659', joined)
        self.assertIn('Low confidence', joined)

    def test_network_quote_is_never_published_as_a_valve_estimate(self):
        # A quote whose only inputs are bo3.gg series cannot be an official
        # Valve standing; the published label must stay on the network rung.
        chosen = self._resolve(fixture(_network=network_quote(0.61)))['origination']
        self.assertEqual(chosen['label'], 'Own network estimate (bo3.gg results graph)')
        self.assertAlmostEqual(chosen['probabilities'][0], 0.61)

    def test_a_resolved_valve_model_keeps_precedence_over_the_network(self):
        valve = {
            'provider': 'Valve official standings',
            'family': 'valve',
            'probabilities': [0.812, 0.188],
            'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
            'observed_at': NOW.isoformat(),
            'snapshot_date': '2026-10-05',
        }
        with mock.patch.object(originate, 'model_estimate', return_value=(dict(valve), 'Valve row matched')):
            result = self._resolve(fixture(_network=network_quote()))
        chosen = result['origination']
        self.assertEqual(chosen['label'], 'Research model estimate (Valve official ratings)')
        self.assertAlmostEqual(chosen['probabilities'][0], 0.812)
        self.assertEqual(chosen['source'], 'Valve official standings')

    def test_a_resolved_results_model_keeps_precedence_over_the_network(self):
        form = {
            'provider': 'Own results model',
            'family': 'form',
            'probabilities': [0.455, 0.545],
            'n_series': 9,
            'rating_sd': 92,
            'interval': [0.31, 0.60],
            'source_url': 'https://bo3.gg/matches',
            'observed_at': NOW.isoformat(),
        }
        result = self._resolve(fixture(_form=form, _network=network_quote()))
        chosen = result['origination']
        self.assertEqual(chosen['label'], 'Own results-based estimate (bo3.gg series results)')
        self.assertAlmostEqual(chosen['probabilities'][0], 0.455)


class SummaryProvenanceTest(unittest.TestCase):
    def _complete(self) -> dict:
        return {
            'generated_at': NOW.isoformat().replace('+00:00', 'Z'),
            'counts': {'active': 2, 'resolved': 2, 'unresolved': 0, 'with_pick': 2},
            'matches': [
                {
                    'id': '1081597',
                    'teams': [{'name': 'benched gods'}, {'name': 'TitanFlow'}],
                    'competition': 'CCT Europe 2026 Challenges #8',
                    'starts_at': (NOW + timedelta(hours=10)).isoformat().replace('+00:00', 'Z'),
                    'featured_method': None,
                    'pick_index': 1,
                    'origination': {'method': 'model',
                                    'label': 'Own network estimate (bo3.gg results graph)',
                                    'probabilities': [0.222, 0.778],
                                    'quotes': [network_quote()]},
                    'research': [
                        {'stage': 'Primary: Polymarket', 'status': 'unresolved',
                         'source_url': 'https://polymarket.com/esports/cs2', 'detail': 'No market.'},
                        {'stage': 'Esportsbook line (Thunderpick original prices)', 'status': 'unresolved',
                         'source_url': 'https://thunderpick.io/esports/counter-strike', 'detail': 'No line.'},
                        {'stage': 'Own network model (bo3.gg results graph)', 'status': 'resolved',
                         'source_url': 'https://bo3.gg/matches', 'detail': 'Fitted.'},
                    ],
                    'limitations': [
                        'Own uncalibrated network model, not observed betting odds: a Bradley–Terry fit.',
                        'Low confidence: the interval crosses 50% or a side has fewer than ten finished series.',
                    ],
                },
                {
                    'id': '1081870',
                    'teams': [{'name': 'Vitalem Aerem'}, {'name': 'Rare Atom'}],
                    'competition': 'VOID Autumn Cup 2026',
                    'starts_at': (NOW + timedelta(hours=3)).isoformat().replace('+00:00', 'Z'),
                    'featured_method': None,
                    'pick_index': 1,
                    'origination': {'method': 'market', 'label': 'Originated market line (Kalshi)',
                                    'probabilities': [0.323, 0.677], 'quotes': []},
                    'research': [],
                    'limitations': [],
                },
            ],
        }

    def test_summary_names_only_the_rung_that_was_used(self):
        html = build.unresolved_register({'complete_picks': self._complete(), 'counts': {'upcoming': 2}}, '')
        self.assertIn('Own network estimate (bo3.gg results graph)', html)
        self.assertIn('Originated market line (Kalshi)', html)
        # The old hardcoded sentence credited a Thunderpick price to every blank
        # row, including the network-model row that has no Thunderpick line.
        self.assertNotIn('verified Thunderpick paired-price book', html)

    def test_model_pick_register_publishes_the_limitation_trail(self):
        html = build.model_pick_register({'complete_picks': self._complete()}, '')
        self.assertIn('Picks without a bookmaker line', html)
        self.assertIn('benched gods', html)
        self.assertIn('TitanFlow', html)
        self.assertIn('77.8%', html)
        self.assertIn('Own network estimate (bo3.gg results graph)', html)
        self.assertIn('Polymarket', html)
        self.assertIn('Thunderpick', html)
        self.assertIn('Low confidence', html)
        # A market-backed row is not a model pick and must not be listed here.
        self.assertNotIn('Vitalem Aerem', html)

    def test_model_pick_register_is_empty_without_model_picks(self):
        data = {'complete_picks': {'matches': [self._complete()['matches'][1]]}}
        self.assertEqual(build.model_pick_register(data, ''), '')


if __name__ == '__main__':
    unittest.main()
