"""Session arena-13bdd12a — a direction for every priced match.

An exact tie between two published official ratings yields a probability pair
but no pick. The brief requires a pick for every match, so when the selected
research model is level the ladder continues, in a fixed published order,
through the independent estimates it already fetched (HLTV world ranking, the
own bo3.gg network fit, the own results fit).

These tests pin the contract:

* a level Valve pair is separated by a dated HLTV ranking row;
* a money line is never tie-broken and never replaced by a model;
* when every sourced rung is level or missing, the fixture stays explicitly
  even — no invented side, no default 50/50 pick;
* the featured level row is upgraded, displayed and badged as a tie-break;
* the executive summary's limitations block is dated and source-linked and
  adds no probability.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import (glance, market_limits_block, matches_table,
                           selected_fallback, summary)
from scripts.originate import resolve_match

UTC = timezone.utc
NOW = datetime(2026, 10, 22, 12, 0, 0, tzinfo=UTC)
DAY = NOW.date().isoformat()
ROOT = Path(__file__).resolve().parents[1]

VALVE_URL = 'https://github.com/ValveSoftware/counter-strike_regional_standings'


def fixture():
    return {
        'id': '1079654',
        'teams': [{'id': '1', 'name': 'ex-Zero Tenacity'}, {'id': '2', 'name': 'ex-RUSTEC'}],
        'competition': 'CCT Europe 2026 Series #11',
        'starts_at': '2026-10-23T10:00:00Z',
        'locks_at': '2026-10-23T09:54:00Z',
        'availability': 'open',
        'source_url': 'https://www.hotspawn.com/matches/ex-zero-tenacity-vs-ex-rustec-cct-europe-2026-series-11-1079654',
        'research': [],
        'limitations': [],
        'source_status': 'scheduled',
        'source_api': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures',
        'best_of': 3,
        'observed_at': '2026-10-22T11:00:00Z',
        'tier': 'c',
    }


def level_ratings():
    return [
        {'name': 'ex-Zero Tenacity', 'points': 5.0, 'standing': 142, 'roster': list('abcde'),
         'snapshot_date': DAY, 'source_url': VALVE_URL},
        {'name': 'ex-RUSTEC', 'points': 5.0, 'standing': 143, 'roster': list('fghij'),
         'snapshot_date': DAY, 'source_url': VALVE_URL},
    ]


def valve_meta():
    return {'source_url': VALVE_URL, 'snapshot_date': DAY,
            'evidence_file': 'data/evidence/valve-ratings.json',
            'observed_at': '2026-10-22T11:00:00Z'}


def hltv_rows():
    return [
        {'name': 'ex-Zero Tenacity', 'points': 62.0, 'rank': 67,
         'source_url': 'https://www.hltv.org/ranking/', 'snapshot_date': DAY},
        {'name': 'ex-RUSTEC', 'points': 51.0, 'rank': 70,
         'source_url': 'https://www.hltv.org/ranking/', 'snapshot_date': DAY},
    ]


def hltv_meta():
    return {'source_url': 'https://www.hltv.org/ranking/', 'snapshot_date': DAY,
            'observed_at': '2026-10-22T11:00:00Z',
            'evidence_file': 'data/origination/evidence/live-hltv-ranking.json'}


def level_market_row():
    """A valid, exactly level two-sided market (spread 0.02, midpoint 0.5/0.5)."""
    return {'family': 'market', 'provider': 'Polymarket',
            'names': ['ex-Zero Tenacity', 'ex-RUSTEC'],
            'start': '2026-10-23T10:00:00Z',
            'bid': [0.49, 0.49], 'ask': [0.51, 0.51],
            'observed_at': '2026-10-22T11:00:00Z',
            'source_url': 'https://polymarket.com/event/cs2-ezt-rustec',
            'event_id': '1234567', 'market_id': '7654321',
            'evidence_file': 'data/origination/evidence/live-polymarket-observations.json'}


def featured_level_model():
    return {
        'method': 'model',
        'label': 'Research model estimate (Valve official ratings)',
        'probabilities': [0.5, 0.5], 'fair_decimal': [2.0, 2.0],
        'source': 'Valve official standings', 'source_url': VALVE_URL,
        'observed_at': '2026-10-22T11:00:00Z', 'quotes': [],
        'snapshot_date': DAY, 'limitations': [],
        'inputs': [
            {'name': 'ex-Zero Tenacity', 'points': 5.0, 'roster': list('abcde'), 'source_url': VALVE_URL},
            {'name': 'ex-RUSTEC', 'points': 5.0, 'roster': list('fghij'), 'source_url': VALVE_URL},
        ],
    }


class TieBreakLadderTest(unittest.TestCase):
    def test_level_valve_pair_is_separated_by_hltv_ranking(self):
        result = resolve_match(fixture(), [], [], level_ratings(), valve_meta(),
                               {'aliases': []}, NOW, hltv_rank=hltv_rows(), hltv_meta=hltv_meta())
        chosen = result['origination']
        self.assertEqual(chosen['method'], 'model')
        self.assertTrue(chosen['label'].startswith('Tie-break estimate'))
        self.assertEqual(chosen['tie_break_of']['probabilities'], [0.5, 0.5])
        self.assertIsNotNone(result['pick_index'])
        self.assertGreaterEqual(
            abs(chosen['probabilities'][0] - chosen['probabilities'][1]), 0.01)
        self.assertTrue(any(r['stage'] == 'Tie-break research' and r['status'] == 'resolved'
                            for r in result['research']))
        self.assertTrue(any('Tie-break direction' in x for x in result['limitations']))

    def test_level_pair_stays_even_when_no_source_separates_them(self):
        result = resolve_match(fixture(), [], [], level_ratings(), valve_meta(),
                               {'aliases': []}, NOW, hltv_rank=[], hltv_meta=None)
        chosen = result['origination']
        self.assertIsNone(chosen.get('tie_break_of'))
        self.assertEqual(chosen['probabilities'], [0.5, 0.5])
        self.assertIsNone(result['pick_index'])
        # The blank is explained, not silent: every documented rung is listed
        # with the outcome that stopped it from supplying a direction.
        attempts = result['tie_break_attempts']
        self.assertEqual([a['rung'] for a in attempts],
                         ['HLTV world ranking', 'Own network model (bo3.gg results graph)',
                          'Own results-based model (bo3.gg series results)'])
        self.assertTrue(all(a['status'] == 'unavailable' for a in attempts))
        self.assertTrue(any(r['stage'] == 'Tie-break research' and r['status'] == 'unresolved'
                            for r in result['research']))
        self.assertTrue(any(x.startswith('Even estimate:') for x in result['limitations']))

    def test_level_rung_is_recorded_as_level_not_as_a_decision(self):
        # Both official rows are present but identical, so the HLTV publication
        # in this fixture is level too: it must be reported as level, and the
        # fixture must stay Even instead of taking a rounding-level side.
        rows = [dict(r, points=5.0) for r in hltv_rows()]
        result = resolve_match(fixture(), [], [], level_ratings(), valve_meta(),
                               {'aliases': []}, NOW, hltv_rank=rows, hltv_meta=hltv_meta())
        self.assertIsNone(result['pick_index'])
        self.assertEqual(result['origination']['probabilities'], [0.5, 0.5])
        status = {a['rung']: a['status'] for a in result['tie_break_attempts']}
        self.assertEqual(status['HLTV world ranking'], 'level')

    def test_featured_even_row_publishes_its_attempts_without_a_pick(self):
        match = dict(fixture(), analysis=featured_level_model(), pick_index=None)
        result = resolve_match(match, [], [], level_ratings(), valve_meta(),
                               {'aliases': []}, NOW, hltv_rank=[], hltv_meta=None)
        self.assertIsNone(result['pick_index'])
        self.assertEqual(result['origination']['probabilities'], [0.5, 0.5])
        self.assertEqual(len(result['tie_break_attempts']), 3)
        self.assertTrue(any(r['stage'] == 'Tie-break research' for r in result['research']))

    def test_a_money_line_is_never_tie_broken(self):
        result = resolve_match(fixture(), [level_market_row()], [], level_ratings(),
                               valve_meta(), {'aliases': []}, NOW,
                               hltv_rank=hltv_rows(), hltv_meta=hltv_meta())
        chosen = result['origination']
        self.assertEqual(chosen['method'], 'market')
        self.assertIsNone(chosen.get('tie_break_of'))
        self.assertIsNone(result['pick_index'])

    def test_featured_level_model_is_upgraded_by_the_tie_break(self):
        featured = featured_level_model()
        match = dict(fixture(), analysis=featured, pick_index=None)
        result = resolve_match(match, [], [], level_ratings(), valve_meta(),
                               {'aliases': []}, NOW, hltv_rank=hltv_rows(), hltv_meta=hltv_meta())
        self.assertIs(result.get('upgraded_from_featured_model'), True)
        self.assertIsNotNone(result['pick_index'])
        self.assertTrue(result['origination']['tie_break_of'])

    def test_featured_level_model_without_a_separating_rung_stays_even(self):
        featured = featured_level_model()
        match = dict(fixture(), analysis=featured, pick_index=None)
        result = resolve_match(match, [], [], level_ratings(), valve_meta(),
                               {'aliases': []}, NOW, hltv_rank=[], hltv_meta=None)
        self.assertNotIn('upgraded_from_featured_model', result)
        self.assertIsNone(result['pick_index'])


def complete_row(probabilities=(0.516, 0.484), pick=0):
    origin = {
        'method': 'model', 'label': 'Tie-break estimate (HLTV world ranking)',
        'probabilities': list(probabilities), 'fair_decimal': [round(1 / p, 3) for p in probabilities],
        'source': 'HLTV world ranking', 'source_url': 'https://www.hltv.org/ranking/',
        'observed_at': '2026-10-22T11:00:00Z', 'snapshot_date': DAY,
        'tie_break_of': {'provider': 'Valve official standings', 'probabilities': [0.5, 0.5],
                         'label': 'Research model estimate (Valve official ratings)',
                         'source_url': VALVE_URL},
        'quotes': [{'provider': 'HLTV world ranking', 'family': 'model',
                    'probabilities': list(probabilities),
                    'source_url': 'https://www.hltv.org/ranking/',
                    'observed_at': '2026-10-22T11:00:00Z'}],
        'inputs': [{'name': 'ex-Zero Tenacity', 'points': 62.0, 'rank': 67,
                    'roster': list('abcde'), 'source_url': 'https://www.hltv.org/ranking/'},
                   {'name': 'ex-RUSTEC', 'points': 51.0, 'rank': 70,
                    'roster': list('fghij'), 'source_url': 'https://www.hltv.org/ranking/'}],
    }
    return {'id': '1079654', 'pick_index': pick, 'origination': origin,
            'upgraded_from_featured_model': True, 'limitations': [],
            'research': [{'stage': 'Tie-break research', 'status': 'resolved',
                          'source_url': 'https://www.hltv.org/ranking/',
                          'detail': 'Level official ratings; HLTV ranking separates the teams.'}]}


class TieBreakDisplayTest(unittest.TestCase):
    def match(self):
        return dict(fixture(), analysis=featured_level_model(), pick_index=None,
                    observed_at='2026-10-22T11:00:00Z', tier='c')

    def test_selected_fallback_shows_the_tie_break_row(self):
        row = selected_fallback(self.match(), {'1079654': complete_row()})
        self.assertIsNotNone(row)
        self.assertEqual(row['pick_index'], 0)
        self.assertTrue(row['origination']['tie_break_of'])

    def test_matches_table_badges_the_tie_break(self):
        html = matches_table([self.match()], './', fallbacks={'1079654': complete_row()}, now=NOW)
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(' ', strip=True)
        self.assertIn('Tie-break estimate', text)
        self.assertIn('tie-break direction, featured official ratings were level', text)
        self.assertNotIn('Equal estimate; no arbitrary pick', text)

    def test_glance_badges_the_tie_break(self):
        data = {'matches': [dict(self.match(), locks_at='2026-10-23T09:54:00Z')],
                'fallbacks': {'1079654': complete_row()},
                'counts': {'upcoming': 1, 'unresolved': 0}}
        html = glance(data, './', now=NOW)
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        self.assertIn('Tie-break', text)
        self.assertIn('ex-Zero Tenacity', text)


class ExecutiveSummaryLimitsTest(unittest.TestCase):
    def test_limitations_block_is_dated_and_source_linked(self):
        html = market_limits_block({}, './')
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(' ', strip=True)
        self.assertIn('verified 22 Oct 2026', text)
        urls = [a['href'] for a in soup.select('a[href^="https://"]')]
        self.assertIn('https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026', urls)
        self.assertIn('https://bo3.gg/matches/benched-gods-vs-titanflow-22-10-2026', urls)
        self.assertIn('https://egamersworld.com/counterstrike/match/rW6Ymkl0D/benched-gods-vs-titanflow-EcLgERbZn', urls)
        self.assertEqual(soup.select('a[href="./data/research/13bdd12a/limits-evidence.json"]')[0]['href'],
                         './data/research/13bdd12a/limits-evidence.json')
        # It explains sources; it must never print a modelled probability.
        self.assertNotIn('51.6%', text)
        self.assertNotIn('estimated win chance', text)

    def test_evidence_record_is_valid_and_dated(self):
        payload = json.loads((ROOT / 'data/research/13bdd12a/limits-evidence.json').read_text())
        self.assertTrue(payload['observed_at'].startswith('2026-10-22'))
        self.assertGreaterEqual(len(payload['observations']), 5)
        for entry in payload['observations']:
            self.assertTrue(entry['url'].startswith('https://'))
            self.assertIs(entry['used_as_probability'], False)

    def test_summary_heading_counts_probabilities_not_directional_picks(self):
        payload = json.loads((ROOT / 'data/latest.json').read_text())
        payload['matches'] = []
        payload['complete_picks'] = {
            'generated_at': '2026-10-22T11:00:00Z',
            'counts': {'active': 2, 'resolved': 2, 'with_pick': 1, 'unresolved': 0,
                       'market': 0, 'bookmaker': 0, 'model': 2, 'consensus': 0,
                       'reference': 0, 'guidance': 0},
            'matches': [],
        }
        payload['fallbacks'] = {}
        html = summary(payload, './', now=NOW)
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        self.assertIn('Win probabilities for every active match', text)
        self.assertIn('2 / 2', text)
        self.assertIn('1 resolved estimate has no directional pick', text)


if __name__ == '__main__':
    unittest.main()
