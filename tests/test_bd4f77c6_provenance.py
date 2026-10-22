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


def quote(probabilities, *, family='valve', provider='Valve official standings', **extra) -> dict:
    """The shape the Valve, HLTV-ranking and network rungs publish."""
    row = {
        'provider': provider,
        'family': family,
        'probabilities': list(probabilities),
        'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
        'observed_at': NOW.isoformat(),
        'snapshot_date': '2026-10-05',
    }
    row.update(extra)
    return row


class TiedRungTest(unittest.TestCase):
    """An exact 50/50 is a probability pair, not a pick.

    Live defect (fixture 1079654, 22 Oct): the featured Valve model returned
    0.5/0.5, the ladder stopped there, and the row was published as "Even · no
    side" although HLTV ranks the two teams #67 and #70. The brief asks for a
    pick on every match, so a tied rung must yield to a rung that separates the
    sides; if every rung ties, the even probabilities stay and the fixture stays
    in the separate no-side register.
    """

    def _resolve(self, match):
        return originate.resolve_match(match, [], [], [], None, {'aliases': []}, NOW)

    def _patched(self, valve, hltv):
        return (mock.patch.object(originate, 'model_estimate', return_value=(dict(valve), 'valve row')),
                mock.patch.object(originate.hltv_ranking, 'estimate', return_value=(dict(hltv), 'ranking row')))

    def test_an_even_valve_model_yields_to_a_directional_hltv_ranking(self):
        valve = quote([0.5, 0.5])
        hltv = quote([0.56, 0.44], family='hltv', provider='HLTV world ranking')
        valve_patch, hltv_patch = self._patched(valve, hltv)
        with valve_patch, hltv_patch:
            result = self._resolve(fixture())
        chosen = result['origination']
        self.assertEqual(chosen['label'], 'Research model estimate (HLTV world ranking)')
        self.assertAlmostEqual(chosen['probabilities'][0], 0.56)
        self.assertEqual(result['pick_index'], 0, 'a separating rung must produce a side')

    def test_a_featured_model_tie_is_replaced_by_the_directional_rung(self):
        # The live fixture kept the featured even estimate because only money
        # upgrades were allowed; a labelled model with a side is better than no pick.
        featured = dict(quote([0.5, 0.5]), method='model')
        hltv = quote([0.56, 0.44], family='hltv', provider='HLTV world ranking')
        valve_patch, hltv_patch = self._patched(featured, hltv)
        with valve_patch, hltv_patch:
            result = self._resolve(fixture(analysis=dict(featured), pick_index=None))
        self.assertTrue(result.get('upgraded_from_featured_tie'))
        self.assertEqual(result['origination']['label'], 'Research model estimate (HLTV world ranking)')
        self.assertEqual(result['pick_index'], 0)

    def test_all_tied_rungs_keep_the_even_probabilities_and_no_side(self):
        valve = quote([0.5, 0.5])
        hltv = quote([0.5, 0.5], family='hltv', provider='HLTV world ranking')
        valve_patch, hltv_patch = self._patched(valve, hltv)
        with valve_patch, hltv_patch:
            result = self._resolve(fixture())
        self.assertIsNotNone(result['origination'], 'the estimate must still be published')
        self.assertEqual(result['origination']['probabilities'], [0.5, 0.5])
        self.assertIsNone(result['pick_index'], 'no side may be invented from a tie')


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

    def test_no_line_register_publishes_the_limitation_trail(self):
        # main's no_line_register replaced this session's earlier model-pick
        # register during integration; the contract is the same: name the rung,
        # the providers actually checked, and the blocker for model-only picks.
        html = build.no_line_register({'complete_picks': self._complete()}, '')
        self.assertIn('Picks without a betting line', html)
        self.assertIn('benched gods', html)
        self.assertIn('TitanFlow', html)
        self.assertIn('77.8%', html)
        self.assertIn('Own network estimate (bo3.gg results graph)', html)
        self.assertIn('Why there is no line', html)
        self.assertIn('uncalibrated estimate, not a betting price', html)
        self.assertIn('Thunderpick', html)
        # A market-backed row is not a model-only row and must not be listed here.
        self.assertNotIn('Vitalem Aerem', html)

    def test_no_line_register_is_empty_without_model_picks(self):
        data = {'complete_picks': {'matches': [self._complete()['matches'][1]]}}
        self.assertEqual(build.no_line_register(data, ''), '')


class TieUpgradeValidationTest(unittest.TestCase):
    """The replay validator must accept a marked tie upgrade and only that."""

    def _payloads(self):
        import math
        from scripts import form_model
        points = (1015.0, 950.0)
        rd = min(400.0, 150.0 + 300.0 / math.sqrt(9))
        probability = form_model.win_probability(points[0], points[1], rd)
        facts = {
            'id': '1079654',
            'teams': [{'id': '1', 'name': 'ex-Zero Tenacity'}, {'id': '2', 'name': 'ex-RUSTEC'}],
            'competition': 'CCT Europe 2026 Series #11',
            'starts_at': '2026-10-23T08:00:00Z',
            'locks_at': '2026-10-23T07:54:00Z',
            'availability': 'open',
            'tier': 'c',
            'source_url': 'https://www.hotspawn.com/matches/ex-zero-tenacity-vs-ex-rustec-1079654',
            'lobby_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1079654',
        }
        raw = dict(facts, analysis={'method': 'model', 'probabilities': [0.5, 0.5],
                                    'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                                    'observed_at': '2026-10-22T01:00:00Z'}, pick_index=None)
        current = {
            'method': 'model',
            'family': 'form',
            'label': 'Own results-based estimate (bo3.gg series results)',
            'probabilities': [probability, 1 - probability],
            'fair_decimal': [round(1 / probability, 3), round(1 / (1 - probability), 3)],
            'source': 'Own results-based model (bo3.gg series results)',
            'source_url': 'https://bo3.gg/matches/ex-zero-tenacity-vs-ex-rustec-22-10-2026',
            'observed_at': '2026-10-22T01:00:00Z',
            'inputs': [
                {'name': 'ex-Zero Tenacity', 'points': points[0],
                 'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'roster': []},
                {'name': 'ex-RUSTEC', 'points': points[1],
                 'source_url': 'https://bo3.gg/matches/ex-zero-tenacity-vs-ex-rustec-22-10-2026',
                 'fitted': {'n': 9, 'posterior_sd': 119.0, 'prior_center': 871}},
            ],
            'rating_sd': rd,
            'interval': [0.31, 0.79],
            'n_series': 9,
            'samples': [{'date': '2026-10-20', 'opponent': 'mellren', 'won': True, 'bo': 3,
                         'source_url': 'https://bo3.gg/matches/ex-rustec-vs-mellren-20-10-2026'}],
            'quotes': [],
        }
        row = dict(facts, pick_index=0 if probability >= 0.5 else 1, origination=current,
                   research=[], limitations=[], featured_method='model',
                   featured_probabilities=[0.5, 0.5], featured_pick_index=None,
                   upgraded_from_featured_tie=True)
        latest = {'inventory_observed_at': '2026-10-22T01:00:00Z', 'matches': [raw]}
        complete = {'source_snapshot_at': '2026-10-22T01:00:00Z',
                    'generated_at': '2026-10-22T01:05:00Z', 'matches': [row]}
        return latest, complete

    def test_marked_tie_upgrade_passes_and_unmarked_or_tampered_rows_fail(self):
        import json, shutil, tempfile
        from pathlib import Path
        from scripts import build_origination
        latest, complete = self._payloads()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / 'origination').mkdir()
            (source / 'origination' / 'aliases.json').write_text(
                Path('data/origination/aliases.json').read_text())
            (source / 'latest.json').write_text(json.dumps(latest))
            build_origination.validate_origination(complete, source)
            del complete['matches'][0]['upgraded_from_featured_tie']
            with self.assertRaises(AssertionError):
                build_origination.validate_origination(complete, source)


if __name__ == '__main__':
    unittest.main()
