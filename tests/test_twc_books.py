"""Synthetic original-book contracts. No live quote is invented by these tests."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import twc_books, twc_lines
from scripts.sources import Client
from scripts.domain import timestamp, iso

NOW = timestamp('2026-10-17T20:00:00Z')
START = '2026-10-18T15:00:00Z'
REG = {'aliases': []}
FIXTURE = {'id': 'twc-1', 'teams': [{'name': 'Alpha'}, {'name': 'Beta'}], 'starts_at': START,
           'competition': twc_lines.EVENT, 'source_url': 'https://www.hltv.org/matches/1/x-thunderpick-world-championship-2026'}


def thunder():
    return {'ok': True, 'data': {'upcoming': [{'id': 1, 'gameId': 6, 'isLive': False,
            'startTime': int(timestamp(START).timestamp()), 'teams': {'home': {'name': 'Alpha'}, 'away': {'name': 'Beta'}},
            'market': {'name': 'Match Winner', 'status': 1, 'draw': None,
                       'home': {'name': 'Alpha', 'status': 1, 'odds': 1.5},
                       'away': {'name': 'Beta', 'status': 1, 'odds': 3.0}}}]}}


def bovada():
    return [{'path': [], 'events': [{'id': 'b1', 'type': 'GAMEEVENT', 'live': False,
             'startTime': int(timestamp(START).timestamp()*1000), 'link': '/esports/test',
             'competitors': [{'name': 'Alpha'}, {'name': 'Beta'}],
             'displayGroups': [{'markets': [{'id': 'm1', 'key': '2W-12', 'description': 'Moneyline', 'status': 'O',
                'period': {'main': True, 'live': False}, 'outcomes': [
                    {'description': 'Alpha', 'status': 'O', 'price': {'decimal': 1.5}},
                    {'description': 'Beta', 'status': 'O', 'price': {'decimal': 3.0}}]}]}]}]}]


class BookContracts(unittest.TestCase):
    def test_both_original_books_remove_margin_and_preserve_team_order(self):
        for name, body in [('Thunderpick', thunder()), ('Bovada', bovada())]:
            q, _ = twc_books.quote(name, body, iso(NOW), FIXTURE, REG, NOW)
            self.assertAlmostEqual(q['probabilities'][0], 2/3, places=6)
            self.assertEqual(q['odds'], [1.5, 3.0]); self.assertIsNone(q['bid'])
            reverse = dict(FIXTURE, teams=list(reversed(FIXTURE['teams'])))
            q, _ = twc_books.quote(name, body, iso(NOW), reverse, REG, NOW)
            self.assertAlmostEqual(q['probabilities'][0], 1/3, places=6)

    def test_other_time_opponent_map_market_and_live_are_rejected(self):
        for mutation in ['time', 'opponent', 'map', 'live', 'draw', 'duplicate']:
            body = thunder(); r = body['data']['upcoming'][0]
            if mutation == 'time': r['startTime'] += 600
            if mutation == 'opponent': r['teams']['home']['name'] = 'Gamma'
            if mutation == 'map': r['market']['name'] = 'Map 1 Winner'
            if mutation == 'live': r['isLive'] = True
            if mutation == 'draw': r['market']['draw'] = {'odds': 5}
            if mutation == 'duplicate': body['data']['upcoming'].append(copy.deepcopy(r))
            q, why = twc_books.quote('Thunderpick', body, iso(NOW), FIXTURE, REG, NOW)
            self.assertIsNone(q, mutation); self.assertTrue(why)

    def test_stale_future_or_past_start_never_prices(self):
        for observed, now in [(NOW-timedelta(hours=9), NOW), (NOW+timedelta(hours=1), NOW), (NOW, timestamp(START))]:
            q, _ = twc_books.quote('Thunderpick', thunder(), iso(observed), FIXTURE, REG, now)
            self.assertIsNone(q)

    def test_hash_replay_recomputes_not_saved_quote_and_checks_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root / 'research/twc-current'; (folder/'evidence').mkdir(parents=True)
            raw = json.dumps(thunder()).encode(); label = 'twc-day5-book-thunderpick-twc-1'
            path = folder/'evidence'/f'{label}.json'; path.write_bytes(raw)
            evidence = {'label': label, 'url': twc_books.PROVIDERS['Thunderpick']['api'], 'method': 'POST',
                        'observed_at': iso(NOW), 'file': 'evidence/'+path.name, 'sha256': hashlib.sha256(raw).hexdigest()}
            provider = {'provider': 'Thunderpick', 'status': 'resolved', 'reason': '', 'source_url': twc_books.PROVIDERS['Thunderpick']['page'],
                        'observed_at': iso(NOW), 'quote': {'probabilities': [0.99,0.01]}, 'evidence': [evidence]}
            report = {'day': '2026-10-18', 'records': [{'fixture': twc_lines.fixture_record(FIXTURE), 'providers': [provider]}]}
            manifest = folder/twc_lines.DAY5_REPORT
            manifest.write_text(json.dumps(report))
            line = twc_lines.load(root, NOW, REG, report_file=twc_lines.DAY5_REPORT)['matches'][0]
            self.assertAlmostEqual(line['probabilities'][0],2/3,places=6)
            self.assertEqual(line['method'], 'bookmaker')
            evidence['url'] = 'https://example.invalid/fake'; manifest.write_text(json.dumps(report))
            with self.assertRaises(ValueError): twc_lines.load(root, NOW, REG, report_file=twc_lines.DAY5_REPORT)
            evidence['url'] = twc_books.PROVIDERS['Thunderpick']['api']; manifest.write_text(json.dumps(report))
            path.write_bytes(raw+b' ')
            with self.assertRaises(ValueError): twc_lines.load(root, NOW, REG, report_file=twc_lines.DAY5_REPORT)

    def test_fallback_is_scoped_to_unresolved_final_day_only(self):
        row = {'source_url': FIXTURE['source_url'], 'facts': {'teams':['Alpha','Beta'], 'starts_at':START,'finished':False}}
        failed = {'provider':'Kalshi','quote':None,'status':'unresolved','reason':'No event','source_url':'https://kalshi.com'}
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.twc_lines.poly_index', return_value=([],{})), patch('scripts.twc_lines._collect_kalshi',return_value=(failed,1)), patch('scripts.twc_books.collect',return_value=[]) as fallback:
            client=Client(Path(tmp))
            twc_lines.collect(client,[row],REG,'2026-10-18',NOW)
            fallback.assert_not_called()
            twc_lines.collect(client,[row],REG,'2026-10-18',NOW,report_path=twc_lines.DAY5_REPORT)
            fallback.assert_called_once()
