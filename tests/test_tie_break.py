"""Session arena-3bad13ea: a pick for an exactly tied fixture, without inventing one.

Context
-------
On the 2026-10-22T01:11Z live snapshot the only Hotspawn CS2 fixture without a
directional pick was **ex-Zero Tenacity vs ex-RUSTEC** (1079654, CCT Europe
2026 Series #11, 08:00Z on 23 October). Both sides carry the same official
Valve points (1066, ranks 93 and 92), so the published transform returns exactly
0.500 / 0.500 and no side can be derived from it. HLTV's own world-ranking
publication ties them as well (13.0 points each). Our own Bradley–Terry fit over
bo3.gg results does separate them (48.7% / 51.3%, low confidence).

These tests pin the rule that was added for that case:

* only a *model* line that is exactly tied may be tie-broken;
* the tie-break is taken from a second, independent, already-audited source and
  is skipped when that source is tied too;
* the row is marked ``upgraded_from_featured_tie`` (never as a money upgrade)
  and publishes the tied primary estimate it replaced;
* the display helpers show that label on the picks page and in the evidence
  panel, so no page shows a blank side for a fixture the complete list resolved.

No real probability is invented anywhere: every number below is a synthetic
fixture value used only to exercise the rule.
"""
from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import build, build_origination, originate

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
NOW = datetime(2026, 10, 22, 2, 0, tzinfo=UTC)


def registry():
    return originate.load_registry(ROOT / 'data' / 'origination' / 'aliases.json')


def ratings(points=(1066, 1066)):
    return [
        {'name': 'Zero Tenacity', 'points': points[0], 'standing': 93,
         'roster': ['a', 'b', 'c', 'd', 'e'], 'snapshot_date': '2026-10-05',
         'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'},
        {'name': 'RUSTEC', 'points': points[1], 'standing': 92,
         'roster': ['f', 'g', 'h', 'i', 'j'], 'snapshot_date': '2026-10-05',
         'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'},
    ]


def meta():
    return {'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
            'snapshot_date': '2026-10-05', 'evidence_file': 'data/evidence/valve-ratings.json',
            'observed_at': '2026-10-22T01:16:50Z'}


def network_quote(probabilities=(0.4872, 0.5128), low_confidence=True):
    return {
        'provider': 'Own network model (bo3.gg results graph)', 'family': 'network',
        'method': 'model', 'probabilities': list(probabilities),
        'inputs': [
            {'name': 'Zero Tenacity', 'points': 1106.9, 'se': 38.0, 'series': 54,
             'source_url': 'https://bo3.gg/teams/1'},
            {'name': 'RUSTEC', 'points': 1115.8, 'se': 33.0, 'series': 74,
             'source_url': 'https://bo3.gg/teams/2'},
        ],
        'rating_sd_diff': 50.3, 'interval': [0.4407, 0.5340], 'n_series': 54,
        'graph_matches': 4645, 'graph_anchors': 269, 'low_confidence': low_confidence,
        'source_url': 'https://bo3.gg/matches',
        'observed_at': '2026-10-22T01:17:00Z',
    }


def fixture(**extra):
    match = {
        'id': '1079654', 'starts_at': '2026-10-23T08:00:00Z',
        'locks_at': '2026-10-23T07:54:00Z', 'competition': 'CCT Europe 2026 Series #11',
        'teams': [{'id': '241774', 'name': 'Zero Tenacity'}, {'id': '261629', 'name': 'RUSTEC'}],
        'source_url': 'https://www.hotspawn.com/matches/ex-zero-tenacity-vs-ex-rustec-cct-europe-2026-series-11-1079654',
        'lobby_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1079654',
        'availability': 'open', 'tier': 'b',
    }
    match.update(extra)
    return match


def resolve(match, *, ratings_rows=None):
    return originate.originate_match(
        match, [], [], ratings_rows if ratings_rows is not None else ratings(), meta(),
        registry(), NOW, hltv=[], reference=[], hltv_rank=[], hltv_meta=None)


class TieBreakGate(unittest.TestCase):
    """The rule fails closed: money lines and double ties are never broken."""

    def test_money_line_is_never_tie_broken(self):
        chosen = {'method': 'market', 'probabilities': [0.5, 0.5]}
        self.assertIsNone(originate.tie_break_quote(
            chosen, [('Own network model (bo3.gg results graph)', network_quote())]))

    def test_a_directional_model_is_not_tie_broken(self):
        chosen = {'method': 'model', 'probabilities': [0.62, 0.38]}
        self.assertIsNone(originate.tie_break_quote(chosen, [('HLTV world ranking', network_quote())]))

    def test_every_candidate_tied_means_no_side(self):
        chosen = {'method': 'model', 'probabilities': [0.5, 0.5]}
        tied = {'family': 'model', 'probabilities': [0.5, 0.5]}
        self.assertIsNone(originate.tie_break_quote(
            chosen, [('HLTV world ranking', tied), ('Own network model (bo3.gg results graph)', tied)]))

    def test_first_directional_candidate_wins_and_order_is_respected(self):
        chosen = {'method': 'model', 'probabilities': [0.5, 0.5]}
        tied = {'family': 'model', 'probabilities': [0.5, 0.5]}
        network = network_quote()
        source, quote = originate.tie_break_quote(
            chosen, [('HLTV world ranking', tied), ('Own network model (bo3.gg results graph)', network)])
        self.assertEqual(source, 'Own network model (bo3.gg results graph)')
        self.assertIs(quote, network)


class TieBreakInTheLadder(unittest.TestCase):
    """An exactly tied official estimate gets a documented side, not a made-up one."""

    def test_identical_valve_points_alone_stay_even_without_a_side(self):
        result = resolve(fixture())
        self.assertEqual(result['origination']['probabilities'], [0.5, 0.5])
        self.assertIsNone(result['pick_index'])
        self.assertNotIn('tie_break', result['origination'])

    def test_network_fit_supplies_the_side_and_publishes_the_tied_primary(self):
        result = resolve(fixture(_network=network_quote()))
        o = result['origination']
        self.assertEqual(result['pick_index'], 1)
        self.assertAlmostEqual(o['probabilities'][0], 0.4872, places=6)
        self.assertEqual(o['label'], 'Tie-break estimate (Own network model (bo3.gg results graph))')
        tie = o['tie_break']
        self.assertEqual(tie['primary_probabilities'], [0.5, 0.5])
        self.assertEqual(tie['primary_points'], [1066, 1066])
        self.assertEqual(tie['chosen_family'], 'network')
        self.assertEqual(tie['chosen_source_url'], 'https://bo3.gg/matches')
        self.assertTrue(any(stage['stage'].startswith('Tie-break (') for stage in result['research']))
        self.assertTrue(any('Tie-break, not a measured edge' in text for text in result['limitations']))
        self.assertTrue(any('Low confidence' in text for text in result['limitations']))

    def test_a_different_valve_points_pair_is_not_tie_broken(self):
        result = resolve(fixture(_network=network_quote()), ratings_rows=ratings((1066, 1040)))
        o = result['origination']
        self.assertNotIn('tie_break', o)
        self.assertNotEqual(result['pick_index'], None)

    def test_hltv_world_ranking_is_preferred_when_it_separates_the_sides(self):
        match = fixture(_network=network_quote(), _form={'family': 'form', 'probabilities': [0.4, 0.6],
                                                         'source_url': 'https://bo3.gg/matches',
                                                         'provider': 'Own results-based model (bo3.gg series results)'})
        rank_rows = [
            {'name': 'Zero Tenacity', 'points': 120.0, 'rank': 40, 'source_url': 'https://www.hltv.org/ranking/teams'},
            {'name': 'RUSTEC', 'points': 100.0, 'rank': 44, 'source_url': 'https://www.hltv.org/ranking/teams'},
        ]
        result = originate.originate_match(
            match, [], [], ratings(), meta(), registry(), NOW, hltv=[], reference=[],
            hltv_rank=rank_rows, hltv_meta={'source_url': 'https://www.hltv.org/ranking/teams',
                                            'snapshot_date': '2026-10-22',
                                            'observed_at': '2026-10-22T01:17:19Z'})
        o = result['origination']
        self.assertEqual(o['label'], 'Tie-break estimate (HLTV world ranking)')
        self.assertEqual(result['pick_index'], 0)
        self.assertEqual(o['source'], 'HLTV world ranking')

    def test_a_network_row_is_not_labelled_as_a_valve_estimate(self):
        """The network fit replaces `model`, so the label must follow its family."""
        # One side has no official row, so the network fit is the chosen model.
        only_one_row = ratings()[:1]
        result = resolve(fixture(_network=network_quote()), ratings_rows=only_one_row)
        o = result['origination']
        self.assertEqual(o.get('family'), 'network')
        self.assertEqual(o['label'], 'Own network estimate (bo3.gg results graph)')
        self.assertTrue(any('Bradley-Terry fit' in text for text in result['limitations']))
        self.assertFalse(any('not observed betting odds. Uncalibrated; current lineups and map vetoes '
                             'unverified.' == text for text in result['limitations']))


class ResolveMatchMarking(unittest.TestCase):
    """The featured tie is replaced only through the marked tie-break path."""

    def featured_tie(self):
        return {
            'method': 'model', 'label': 'Valve-rating research estimate',
            'probabilities': [0.5, 0.5], 'fair_decimal': [2.0, 2.0],
            'observed_at': '2026-10-22T01:11:44Z', 'source': 'Valve official standings',
            'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
            'inputs': [{'name': 'Zero Tenacity', 'points': 1066}, {'name': 'RUSTEC', 'points': 1066}],
            'quotes': [], 'limitations': [],
        }

    def test_tie_break_upgrades_a_featured_tie_and_is_marked_as_such(self):
        match = fixture(analysis=self.featured_tie(), pick_index=None, _network=network_quote())
        result = originate.resolve_match(match, [], [], ratings(), meta(), registry(), NOW,
                                         reference=[], hltv_rank=[], hltv_meta=None)
        self.assertIs(result.get('upgraded_from_featured_tie'), True)
        self.assertIsNot(result.get('upgraded_from_featured_model'), True)
        self.assertEqual(result['pick_index'], 1)

    def test_a_featured_tie_without_a_second_source_is_kept_verbatim(self):
        match = fixture(analysis=self.featured_tie(), pick_index=None)
        result = originate.resolve_match(match, [], [], ratings(), meta(), registry(), NOW,
                                         reference=[], hltv_rank=[], hltv_meta=None)
        self.assertNotIn('upgraded_from_featured_tie', result)
        self.assertIsNone(result['pick_index'])
        self.assertEqual(result['origination']['probabilities'], [0.5, 0.5])

    def test_a_featured_directional_model_is_never_replaced_by_a_tie_break(self):
        featured = dict(self.featured_tie(), probabilities=[0.61, 0.39])
        match = fixture(analysis=featured, pick_index=0, _network=network_quote())
        result = originate.resolve_match(match, [], [], ratings(), meta(), registry(), NOW,
                                         reference=[], hltv_rank=[], hltv_meta=None)
        self.assertNotIn('upgraded_from_featured_tie', result)
        self.assertEqual(result['pick_index'], 0)

    def test_an_unbreakable_tie_explains_every_source_it_tried(self):
        match = fixture(_network_reason='Own network model: no results-graph evidence for this run',
                        _form_reason='Both teams already have published Valve rows; results model not needed')
        result = resolve(match)
        self.assertIsNone(result['pick_index'])
        self.assertEqual(result['origination']['probabilities'], [0.5, 0.5])
        stage = next(r for r in result['research'] if r['stage'] == 'Exact-tie tie-break')
        self.assertEqual(stage['status'], 'unresolved')
        self.assertIn('no results-graph evidence for this run', stage['detail'])
        self.assertTrue(any('Exact tie, no side published' in text for text in result['limitations']))


class TieBreakDisplay(unittest.TestCase):
    """One list on every page: the tie-break row is not shown as blank elsewhere."""

    def inventory(self):
        data = json.loads((ROOT / 'data/latest.json').read_text())
        base = copy.deepcopy(data['matches'][0])
        base.update(fixture(availability='open', source_status='scheduled', analysis=None,
                            pick_index=None, research=[], limitations=[], observed_at='2026-10-22T01:11:28Z',
                            source_api='https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'))
        data['matches'] = [base]
        return data

    def fallback(self):
        return {'origination': {'method': 'model', 'label': 'Tie-break estimate (Own network model (bo3.gg results graph))',
                                'probabilities': [0.4872, 0.5128], 'fair_decimal': [2.053, 1.95],
                                'observed_at': '2026-10-22T01:17:00Z',
                                'source': 'Own network model (bo3.gg results graph)',
                                'source_url': 'https://bo3.gg/matches',
                                'quotes': [], 'model_crosscheck': None,
                                'tie_break': {'primary_probabilities': [0.5, 0.5],
                                              'chosen': 'Own network model (bo3.gg results graph)',
                                              'chosen_probabilities': [0.4872, 0.5128],
                                              'chosen_source_url': 'https://bo3.gg/matches'}},
                'pick_index': 1, 'upgraded_from_featured_tie': True,
                'featured_probabilities': [0.5, 0.5], 'featured_method': 'model'}

    def test_the_selected_basis_is_the_tie_break_row(self):
        data = self.inventory()
        match = data['matches'][0]
        # With no featured estimate at all, the complete-list row is the basis.
        self.assertIsNotNone(build.selected_fallback(match, {'1079654': self.fallback()}))
        # With a featured model tie, the marked tie-break replaces it.
        match['analysis'] = {'method': 'model', 'probabilities': [0.5, 0.5]}
        fallbacks = {'1079654': self.fallback()}
        self.assertIsNotNone(build.selected_fallback(match, fallbacks))
        self.assertEqual(build.effective_basis(match, fallbacks), ('model', True))

    def test_the_evidence_panel_names_the_tie_break(self):
        data = self.inventory()
        match = data['matches'][0]
        match['analysis'] = {'method': 'model', 'label': 'Valve-rating research estimate',
                             'probabilities': [0.5, 0.5], 'fair_decimal': [2.0, 2.0],
                             'observed_at': '2026-10-22T01:11:44Z', 'source': 'Valve official standings',
                             'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                             'inputs': [{'name': 'Zero Tenacity', 'points': 1066, 'roster': [],
                                         'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'},
                                        {'name': 'RUSTEC', 'points': 1066, 'roster': [],
                                         'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'}],
                             'snapshot_date': '2026-10-05', 'quotes': [], 'limitations': []}
        html = build.evidence(match, './', self.fallback())
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        self.assertIn('Featured model reference (replaced below)', text)
        self.assertIn('breaks the tie', text)
        self.assertIn('not a money line', text)

    def test_the_phone_glance_badges_the_row_as_a_tie_break(self):
        data = self.inventory()
        match = data['matches'][0]
        match.update(availability='open', analysis={'method': 'model', 'probabilities': [0.5, 0.5]},
                     pick_index=None, locks_at='2026-10-23T07:54:00Z')
        data['fallbacks'] = {'1079654': self.fallback()}
        html = build.glance(data, './')
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        self.assertIn('Tie-break', text)
        self.assertIn('RUSTEC', text)

    def test_the_picks_table_caption_says_tie_break_not_rejected(self):
        data = self.inventory()
        match = data['matches'][0]
        match.update(availability='open',
                     analysis={'method': 'model', 'label': 'Valve-rating research estimate',
                               'probabilities': [0.5, 0.5], 'fair_decimal': [2.0, 2.0],
                               'observed_at': '2026-10-22T01:11:44Z', 'source': 'Valve official standings',
                               'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                               'inputs': [], 'snapshot_date': '2026-10-05',
                               'quotes': [], 'limitations': []},
                     pick_index=None)
        html = build.matches_table([match], './', fallbacks={'1079654': self.fallback()})
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        self.assertIn('tie-break, the official ratings are exactly tied', text)
        self.assertNotIn('featured method rejected this fixture', text)


if __name__ == '__main__':
    unittest.main()
