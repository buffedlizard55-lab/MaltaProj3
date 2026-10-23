"""Session arena-1531ecf1: researched picks for lobby fixtures missing from the
published snapshot, a separate unresolved register with limitations, and the
false-gap/stale-gap fixes.

Presentation and dated research only. A pick may appear only when the record
carries a bound two-sided price or a documented research-model estimate; a
blank stays blank and an even estimate never receives an invented side.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts.build import live_coverage_gaps, load_gap_picks, load_no_line_research

import importlib

_gap_mod = importlib.import_module('scripts.1531ecf1_gap_research')
build_record = _gap_mod.build_record

ROOT = Path(__file__).resolve().parents[1]


def match(i, name_a, name_b, start='2099-01-01T10:00:00Z'):
    return {
        'id': str(i), 'competition': 'CCT Test', 'starts_at': start,
        'availability': 'open', 'source_url': 'https://www.hotspawn.com/matches/x',
        'teams': [{'name': name_a}, {'name': name_b}],
    }


def gap_row(**over):
    row = {
        'id': '1090001', 'teams': ['Alpha Squad', 'Beta Five'], 'competition': 'CCT Gap Cup',
        'starts_at': '2099-01-01T10:00:00Z', 'hotspawn_url': 'https://www.hotspawn.com/matches/a-vs-b-1090001',
        'hltv_url': 'https://www.hltv.org/matches/9999999/alpha-squad-vs-beta-five',
        'status': 'open', 'covered_as': None, 'research': [], 'pick': None, 'limitation': None,
    }
    row.update(over)
    return row


class LoadGapPicks(unittest.TestCase):
    def test_newest_observed_at_wins(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name, observed in (('aaa/1', '2026-10-23T02:00:00Z'), ('bbb/1', '2026-10-23T09:00:00Z')):
                d = base / 'research' / name.split('/')[0]
                d.mkdir(parents=True)
                (d / 'gap-picks.json').write_text(json.dumps({
                    'observed_at': observed, 'lobby_fixtures': [], 'session': name}))
            record = load_gap_picks(base)
            self.assertEqual(record['observed_at'], '2026-10-23T09:00:00Z')

    def test_malformed_and_old_schema_are_skipped(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            d = base / 'research' / 'zzz'
            d.mkdir(parents=True)
            (d / 'gap-picks.json').write_text('{not json')
            (base / 'research' / 'yyy').mkdir()
            (base / 'research' / 'yyy' / 'gap-picks.json').write_text(json.dumps({'observed_at': '2026-10-23T09:00:00Z'}))
            self.assertIsNone(load_gap_picks(base))

    def test_repo_seed_record_is_loadable_and_dated(self):
        record = load_gap_picks(ROOT / 'data')
        self.assertIsNotNone(record)
        self.assertEqual(record['session'], 'arena-1531ecf1')
        self.assertTrue(record['observed_at'].startswith('2026-10-23'))


class GapRendering(unittest.TestCase):
    def test_researched_pick_renders_both_probabilities_and_sources(self):
        data = {
            'matches': [match(1, 'A', 'B')],
            '_gap_picks': {
                'observed_at': '2026-10-23T10:00:00Z', 'environment': 'arena-session-fetch',
                'lobby_fixtures': [gap_row(pick={
                    'method': 'bookmaker', 'label': 'No-vig esportsbook estimate',
                    'probabilities': [0.70, 0.30], 'pick_index': 0, 'pick_team': 'Alpha Squad',
                    'source': 'Thunderpick', 'source_url': 'https://thunderpick.io/api/matches',
                    'book_url': None, 'odds': [1.43, 3.33], 'observed_at': '2026-10-23T10:00:00Z',
                }, limitation='Esportsbook price; margins removed by proportional normalization.')],
            },
        }
        html = live_coverage_gaps(data, '')
        self.assertIn('Alpha Squad', html)
        self.assertIn('70.0%', html)
        self.assertIn('30.0%', html)
        self.assertIn('Research pick', html)
        self.assertIn('https://thunderpick.io/api/matches', html)
        self.assertIn('margins removed', html)

    def test_unresolved_open_fixture_keeps_limitation_and_no_percent(self):
        data = {
            'matches': [match(1, 'A', 'B')],
            '_gap_picks': {
                'observed_at': '2026-10-23T10:00:00Z', 'environment': 'arena-session-fetch',
                'lobby_fixtures': [gap_row(pick=None,
                    limitation='No two-sided prematch price on any probed surface and no unique Valve-rating record.')],
            },
        }
        html = live_coverage_gaps(data, '')
        self.assertIn('Unresolved pick', html)
        self.assertIn('No two-sided prematch price', html)
        body = html.split('id="live-coverage-gaps"')[1]
        self.assertNotIn('%', body)

    def test_started_fixture_is_closed_note_with_prior_pick_and_no_new_probability(self):
        data = {
            'matches': [],
            '_gap_picks': {
                'observed_at': '2026-10-23T10:00:00Z', 'environment': 'arena-session-fetch',
                'lobby_fixtures': [gap_row(status='started',
                    prior_published_pick='Alpha 55.0% (market line; earlier snapshot)',
                    limitation='The pick window has closed.')],
            },
        }
        html = live_coverage_gaps(data, '')
        self.assertIn('closed', html)
        self.assertIn('Alpha 55.0% (market line; earlier snapshot)', html)
        self.assertIn('Nothing is manufactured after lock', html)
        # The only percentages allowed are inside the cited earlier pick string.
        body = html.split('id="live-coverage-gaps"')[1]
        self.assertNotIn('Research pick', body)

    def test_false_gap_name_pair_is_not_listed_as_missing(self):
        data = {
            'matches': [match('1081606', 'JiJieHao', 'Eternal Fire')],
            '_gap_picks': {
                'observed_at': '2026-10-23T10:00:00Z', 'environment': 'arena-session-fetch',
                'lobby_fixtures': [gap_row(id=None, teams=['JiJieHao', 'Eternal Fire'],
                                           status='covered', covered_as='1081606')],
            },
        }
        html = live_coverage_gaps(data, '')
        self.assertNotIn('JiJieHao vs Eternal Fire', html)
        self.assertIn('1 lobby card(s) matched fixtures already in this snapshot', html)

    def test_legacy_record_still_renders_without_picks(self):
        data = {
            'matches': [match(1, 'A', 'B')],
            '_live_coverage': {
                'observed_at': '2026-10-23T04:58:00Z',
                'live_fixtures': [{
                    'id': '1081605', 'teams': ['Phantom Academy', 'Banda chuya'],
                    'competition': 'CCT Europe 2026 Challengers #8',
                    'hotspawn_url': 'https://www.hotspawn.com/matches/phantom-academy-vs-banda-chuya-cct-europe-2026-challengers-8-1081605',
                    'hltv_url': 'https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8',
                }],
            },
        }
        html = live_coverage_gaps(data, '')
        self.assertIn('Phantom Academy vs Banda chuya', html)
        self.assertIn('Not in this build', html)
        self.assertNotIn('%', html.split('id="live-coverage-gaps"')[1])

    def test_no_default_fifty_fifty_is_ever_invented(self):
        data = {
            'matches': [],
            '_gap_picks': {
                'observed_at': '2026-10-23T10:00:00Z', 'environment': 'arena-session-fetch',
                'lobby_fixtures': [gap_row(pick=None, limitation='no line found'),
                                   gap_row(id='1090002', teams=['Gamma', 'Delta'], pick={
                                       'method': 'model', 'label': 'Valve-rating research estimate',
                                       'probabilities': [0.5, 0.5], 'pick_index': None,
                                       'pick_team': None, 'source': 'Valve official standings',
                                       'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                                       'odds': None, 'observed_at': '2026-10-23T10:00:00Z'},
                                       limitation='Even estimate; no side is supportable.')],
            },
        }
        html = live_coverage_gaps(data, '')
        self.assertIn('Even estimate', html)
        self.assertIn('No side', html)
        self.assertNotIn('50.0%', html)


class RecordConstruction(unittest.TestCase):
    def _published(self):
        return {
            'latest_generated_at': '2026-10-23T09:23:57Z',
            'origination_generated_at': '2026-10-23T09:24:00Z',
            'ids': {'1081606'}, 'pairs': {_gap_mod.pair_key(['JiJieHao', 'Eternal Fire'])},
            'rows': {'1081606': {
                'id': '1081606', 'availability': 'open', 'competition': 'DraculaN Season 7',
                'starts_at': '2026-10-23T13:00:00Z',
                'teams': [{'name': 'JiJieHao'}, {'name': 'Eternal Fire'}],
                'source_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1081606',
            }},
            'origination_rows': {
                '1081606': {'origination': {'method': 'market', 'probabilities': [0.445, 0.555]}},
                '1090100': {'origination': {'method': 'model', 'label': 'Valve-rating research estimate',
                                            'probabilities': [0.2, 0.8],
                                            'source': 'Valve official standings',
                                            'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'}},
            },
            'counts': {},
        }

    def test_covered_and_money_rows_are_never_resolved_again(self):
        inventory = {
            'status': 200, 'error': None, 'evidence': 'evidence/x.json',
            'observed_at': '2026-10-23T10:00:00Z',
            'fixtures': [
                {'id': '1081606', 'teams': ['JiJieHao', 'Eternal Fire'],
                 'competition': 'DraculaN Season 7', 'starts_at': '2026-10-23T13:00:00Z',
                 'started': False, 'score': [None, None], 'hotspawn_url': 'https://www.hotspawn.com/matches/x'},
                {'id': None, 'teams': ['JiJieHao', 'Eternal Fire'],
                 'competition': 'DraculaN Season 7', 'starts_at': None,
                 'started': False, 'score': [None, None], 'hotspawn_url': None},
            ],
        }
        published = self._published()
        published['rows']['1090100'] = {
            'id': '1090100', 'availability': 'open', 'competition': 'CCT Test',
            'starts_at': '2099-01-01T10:00:00Z',
            'teams': [{'name': 'Gamma'}, {'name': 'Delta'}],
            'source_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1090100',
        }
        published['origination_rows']['1090100']['id'] = '1090100'
        gap, line = build_record(inventory, published, {}, [], None, {}, '2026-10-23T10:00:00Z',
                                 'arena-session-fetch')
        # Both inventory rows are covered (id + name pair): nothing missing.
        self.assertEqual(gap['counts']['lobby_missing'], 0)
        self.assertEqual(gap['lobby_fixtures'], [])
        # The no-line model row is still researched (target), the money row is not.
        targets = {r['id'] for r in gap['no_line_fixtures']}
        self.assertIn('1090100', targets)
        self.assertNotIn('1081606', targets)

    def test_started_inventory_rows_close_without_pick(self):
        inventory = {
            'status': 200, 'error': None, 'evidence': 'evidence/x.json',
            'observed_at': '2026-10-23T10:00:00Z',
            'fixtures': [{'id': '1081872', 'teams': ['NEXVOID', 'Rare Atom'],
                          'competition': 'VOID Autumn Cup 2026', 'starts_at': '2026-10-23T08:00:00Z',
                          'started': True, 'score': [0, 2],
                          'hotspawn_url': 'https://www.hotspawn.com/matches/x-1081872'}],
        }
        gap, _ = build_record(inventory, self._published(), {}, [], None, {}, '2026-10-23T10:00:00Z',
                              'arena-session-fetch')
        row = gap['lobby_fixtures'][0]
        self.assertIn(row['status'], {'started', 'finished'})
        self.assertIsNone(row['pick'])
        self.assertIn('pick window', (row['limitation'] or '').lower())

    def test_open_gap_without_any_evidence_stays_unresolved(self):
        inventory = {
            'status': 200, 'error': None, 'evidence': 'evidence/x.json',
            'observed_at': '2026-10-23T10:00:00Z',
            'fixtures': [{'id': '1090200', 'teams': ['Epsilon', 'Zeta'],
                          'competition': 'CCT Gap Cup', 'starts_at': '2099-01-01T10:00:00Z',
                          'started': False, 'score': [None, None],
                          'hotspawn_url': 'https://www.hotspawn.com/matches/x-1090200'}],
        }
        gap, line = build_record(inventory, self._published(), {}, [], None, {}, '2026-10-23T10:00:00Z',
                                 'arena-session-fetch')
        row = gap['lobby_fixtures'][0]
        self.assertEqual(row['status'], 'open')
        self.assertIsNone(row['pick'])
        self.assertIn('No two-sided prematch price', row['limitation'])
        self.assertEqual(gap['counts']['lobby_unresolved'], 1)


class RunnerRecordSchema(unittest.TestCase):
    def test_line_source_research_matches_the_displayed_loader_contract(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            d = base / 'research' / '1531ecf1'
            d.mkdir(parents=True)
            (d / 'line-source-research.json').write_text(json.dumps({
                'schema_version': 1, 'session': 'arena-1531ecf1',
                'observed_at': '2026-10-23T11:00:00Z', 'environment': 'github-actions-runner',
                'per_fixture': [{'id': '1081605', 'teams': ['Phantom Academy', 'Banda chuya'],
                                 'money_line_lead': False, 'bo3_bet': None,
                                 'verdict': 'No two-sided price.'}],
            }))
            (d / 'line-source-research.md').write_text('# line-source research\n')
            record = load_no_line_research(base)
            self.assertIsNotNone(record)
            self.assertEqual(record['environment'], 'github-actions-runner')
            self.assertEqual(record['_record_path'], 'research/1531ecf1/line-source-research.json')

    def test_seed_gap_record_never_claims_runner_identity(self):
        record = json.loads((ROOT / 'data/research/1531ecf1/gap-picks.json').read_text())
        self.assertNotEqual(record['environment'], 'github-actions-runner')
        self.assertTrue((ROOT / 'data/research/1531ecf1/gap-picks.md').is_file())


if __name__ == '__main__':
    unittest.main()
