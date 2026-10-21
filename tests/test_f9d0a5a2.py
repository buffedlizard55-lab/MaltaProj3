"""Regression tests for session arena-f9d0a5a2 fixes.

Covers:
1. Polymarket Gamma discovery under real tag_slug='counter-strike-2' alongside legacy 'cs2'.
2. Standalone live_collect() tagged-discovery fallback and single-fetch deduplication.
3. Unicode NFKD diacritic folding in form_model.key() and alias-aware collect_bo3_results().
4. Scoped low-tier team identity joins and must_not_match guards in data/origination/aliases.json.
5. Model source-badge provenance ('HLTV ranking', 'bo3.gg results', 'Valve'), directional tie
   upgrade selection, and strict row-source audit allowlisting for bo3.gg.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import audit_rows, build, form_model, originate, sources
from scripts.domain import iso

UTC = timezone.utc
NOW = datetime(2026, 10, 21, 13, 15, tzinfo=UTC)
REPO = Path(__file__).resolve().parents[1]


class PolymarketCounterStrike2TagDiscoveryTests(unittest.TestCase):
    def test_gamma_games_accepts_counter_strike_2_and_cs2_tags(self):
        events = [
            {
                'id': '1224206',
                'slug': 'cs2-cs1-bli4-2026-10-21',
                'startTime': '2026-10-21T15:00:00Z',
                'tags': [{'id': '100780', 'slug': 'counter-strike-2'}],
                'markets': [{
                    'outcomes': '["CYBERSHOKE Esports", "BlinkDagger"]',
                    'sportsMarketType': 'moneyline',
                    'gameStartTime': '2026-10-21 15:00:00+00',
                }],
            },
            {
                'id': 'legacy-1',
                'slug': 'cs2-legacy',
                'startTime': '2026-10-21T16:00:00Z',
                'tags': [{'slug': 'cs2'}],
                'markets': [{
                    'outcomes': '["Team A", "Team B"]',
                    'sportsMarketType': 'moneyline',
                }],
            },
            {
                'id': 'valorant-1',
                'slug': 'val-other',
                'startTime': '2026-10-21T16:00:00Z',
                'tags': [{'slug': 'valorant'}],
                'markets': [{
                    'outcomes': '["Team C", "Team D"]',
                    'sportsMarketType': 'moneyline',
                }],
            },
        ]
        games = sources.gamma_games(events, 'data/evidence/polymarket-discovery-0.json')
        self.assertEqual([g['id'] for g in games], ['1224206', 'legacy-1'])

    def test_poly_index_queries_counter_strike_2_tag_slug(self):
        client = Mock()
        client.fetch.side_effect = sources.SourceError('synthetic html unavailable')
        page = [{
            'id': '1224207',
            'slug': 'cs2-upgrad-tf4-2026-10-21',
            'startTime': '2026-10-21T15:00:00Z',
            'tags': [{'id': '100780', 'slug': 'counter-strike-2'}],
            'markets': [{
                'outcomes': '["UPGRADE", "Team flacons"]',
                'sportsMarketType': 'moneyline',
            }],
        }]
        client.json.side_effect = [(page, {
            'observed_at': iso(NOW),
            'evidence': 'data/evidence/polymarket-discovery-0.json',
        })]
        games, health = sources.poly_index(client)
        self.assertEqual(len(games), 1)
        self.assertTrue(health['discovery_complete'])
        self.assertIn('tag_slug=counter-strike-2', client.json.call_args.args[0])

    def test_live_collect_deduplicates_duplicate_polymarket_game_ids(self):
        registry = originate.load_registry(REPO / 'data/origination/aliases.json')
        fixture = {
            'id': '1082763',
            'teams': [{'name': 'UPGRADE'}, {'name': 'flacons'}],
            'starts_at': '2026-10-21T15:00:00Z',
            'locks_at': '2026-10-21T14:54:00Z',
            'availability': 'open',
            'competition': 'CIS LAN Championship #9',
            'analysis': None,
            'research': [],
        }
        event = {
            'id': '1224207',
            'slug': 'cs2-upgrad-tf4-2026-10-21',
            'active': True,
            'closed': False,
            'live': False,
            'startTime': '2026-10-21T15:00:00Z',
            'tags': [{'slug': 'counter-strike-2'}],
            'markets': [{
                'id': '5971986',
                'question': 'Counter-Strike: UPGRADE vs Team flacons (BO3)',
                'conditionId': '0x1aa59b3f',
                'outcomes': '["UPGRADE", "Team flacons"]',
                'sportsMarketType': 'moneyline',
                'gameStartTime': '2026-10-21 15:00:00+00',
                'active': True,
                'closed': False,
                'acceptingOrders': True,
                'enableOrderBook': True,
                'clobTokenIds': '["tok-0", "tok-1"]',
            }],
        }
        calls = []

        def fake_get_json(self_client, url, label, **kwargs):
            calls.append(label)
            if label == 'live-thunderpick-matches':
                body = {'ok': True, 'data': {'upcoming': []}}
            elif label == 'live-polymarket-discovery-0':
                body = [event]
            elif label.startswith('live-polymarket-event-'):
                body = event
            elif label.startswith('live-polymarket-book-'):
                idx = label.rsplit('-', 1)[-1]
                bid, ask = (0.95, 0.96) if idx == '0' else (0.04, 0.05)
                body = {
                    'asset_id': f'tok-{idx}',
                    'market': '0x1aa59b3f',
                    'timestamp': str(int(NOW.timestamp() * 1000)),
                    'bids': [{'price': str(bid), 'size': '25'}],
                    'asks': [{'price': str(ask), 'size': '25'}],
                }
            elif label.startswith('live-kalshi-events-'):
                body = {'events': [], 'cursor': ''}
            else:
                body = []
            entry = {'id': label, 'url': url, 'observed_at': iso(NOW), 'status': 'ok'}
            if kwargs.get('save', True):
                entry['evidence'] = self_client.save(label, body)
            self_client.requests.append(entry)
            return body, entry

        dup_game = {
            'id': '1224207',
            'homeName': 'UPGRADE',
            'awayName': 'Team flacons',
            'startTime': '2026-10-21T15:00:00Z',
        }
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'data/origination/evidence'
            folder.mkdir(parents=True)
            with patch.object(originate.Collector, 'get_json', new=fake_get_json), \
                    patch.object(originate.Collector, 'fetch_html', return_value=('', {})), \
                    patch('scripts.sources.polymarket_games', return_value=[dup_game]), \
                    patch('scripts.originate.datetime', wraps=datetime) as clock:
                clock.now.return_value = NOW
                originate.live_collect(folder, [fixture], registry)
            self.assertEqual(calls.count('live-polymarket-event-1224207'), 1)


class FormModelDiacriticsAndAliasBindingTests(unittest.TestCase):
    def test_form_model_key_folds_diacritics(self):
        self.assertEqual(form_model.key('Grêmio'), 'gremio')
        self.assertEqual(form_model.key('QUINTESSÊNCIA'), 'quintessencia')
        self.assertEqual(form_model.key('Los Niños'), 'losninos')
        self.assertEqual(form_model.key('LOS NINOS'), 'losninos')

    def test_collect_bo3_results_binds_scoped_alias_names(self):
        registry = originate.load_registry(REPO / 'data/origination/aliases.json')
        match = {
            'id': '1082837',
            'teams': [{'name': 'Zetta'}, {'name': 'LOS NINOS'}],
            'starts_at': '2026-10-21T22:00:00Z',
            'availability': 'open',
            'competition': 'CCT South America 2026 Series #7',
        }

        def fake_get_json(self_client, url, label, **kwargs):
            if label == 'live-bo3-upcoming-0':
                body = {'results': [{
                    'id': 132583,
                    'slug': 'alianza-lima-esports-vs-los-ninos-21-10-2026',
                    'start_date': '2026-10-21T22:00:00.000+00:00',
                    'team1': {'id': 25489, 'name': 'Alianza Lima Esports'},
                    'team2': {'id': 25310, 'name': 'Los Niños'},
                }]}
            elif label == 'live-bo3-results-25310':
                body = {'results': [{
                    'team1_id': 24856,
                    'team2_id': 25310,
                    'winner_team_id': 25310,
                    'bo_type': 3,
                    'parsed_status': 'done',
                    'start_date': '2026-10-13T19:00:00.000+00:00',
                    'slug': 'gremio-vs-los-ninos-13-10-2026',
                    'team1': {'name': 'Grêmio'},
                    'team2': {'name': 'Los Niños'},
                }]}
            else:
                body = {'results': []}
            return body, {'id': label, 'url': url, 'observed_at': iso(NOW), 'status': 'ok'}

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            client = originate.Collector(folder)
            with patch.object(originate.Collector, 'get_json', new=fake_get_json):
                summary = originate.collect_bo3_results(
                    client, folder, [match], registry, known={'zetta'}
                )
            self.assertEqual(summary['fixtures_bound'], 1)
            saved = form_model.load_bindings(folder)
            results = saved['1082837']['results']
            self.assertIn('losninos', results)
            self.assertEqual(results['losninos'][0]['opponent'], 'Grêmio')


class ScopedAliasAndProvenanceTests(unittest.TestCase):
    def test_scoped_aliases_resolve_inside_declared_competition_only(self):
        registry = originate.load_registry(REPO / 'data/origination/aliases.json')
        cases = [
            ('CYBERSHOKE', 'CIS LAN Championship #9', 'ex-CYBERSHOKE'),
            ('CYBERSHOKE Esports', 'CIS LAN Championship #9', 'ex-CYBERSHOKE'),
            ('Team flacons', 'CIS LAN Championship #9', 'flacons'),
            ('Hacha Esports', 'CCT South America 2026 Series #7', 'Hacha'),
            ('Damajuanaa', 'CCT South America 2026 Series #7', 'Damajuana'),
            ('Alianza Lima Esports', 'CCT South America 2026 Series #7', 'Zetta'),
            ('Los Niños', 'CCT South America 2026 Series #7', 'LOS NINOS'),
            ('largadosypelados', 'Circuit X Curitiba #4', 'BARCA'),
            ('paiN Gaming', 'Circuit X Curitiba #4', 'paiN'),
        ]
        for alias, comp, expected in cases:
            canonical, entry = originate.resolve_name(alias, registry, comp)
            self.assertEqual(canonical, originate.name_key(expected))
            self.assertTrue(entry)
            other, other_entry = originate.resolve_name(alias, registry, 'Unrelated Event 2026')
            self.assertEqual(other, originate.name_key(alias))
            self.assertEqual(other_entry, [])
        # Ensure Team Falcons never collides with Team flacons.
        same, entry = originate.resolve_name('Team Falcons', registry, 'CIS LAN Championship #9')
        self.assertEqual(same, originate.name_key('Team Falcons'))
        self.assertEqual(entry, [])

    def test_model_source_label_and_bo3_official_host(self):
        self.assertEqual(build.model_source_label({
            'method': 'model', 'source': 'HLTV world ranking',
            'source_url': 'https://www.hltv.org/ranking/teams',
        }), 'HLTV ranking')
        self.assertEqual(build.model_source_label({
            'method': 'model', 'source': 'Own results-based model (bo3.gg series results)',
            'source_url': 'https://bo3.gg/matches/gremio-vs-los-ninos-13-10-2026',
        }), 'bo3.gg results')
        self.assertEqual(build.model_source_label({
            'method': 'model', 'source': 'Valve official standings',
            'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
        }), 'Valve')
        self.assertTrue(audit_rows.is_official('https://bo3.gg/matches/gremio-vs-los-ninos-13-10-2026'))


if __name__ == '__main__':
    unittest.main()
