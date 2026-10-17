"""Independent production-contract checks: run the real collector, then replay it.

Everything returned by HTTP in this file is synthetic. In particular, the
response body is compact JSON while Client.save stores indented JSON, just as
normal provider responses do. Hand-writing a replay report hides schema and
serialization mistakes at this boundary; these tests deliberately do not.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import requests

from scripts import twc_lines
from scripts.domain import iso
from scripts.sources import Client

NOW = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
START = '2026-10-17T14:00:00Z'
REGISTRY = {'aliases': []}
MATCH = {
    'source_url': 'https://www.hltv.org/matches/9900001/synthetic-a-vs-synthetic-b-thunderpick-world-championship-2026',
    'observed_at': iso(NOW),
    'facts': {'teams': ['Synthetic A', 'Synthetic B'], 'starts_at': START, 'finished': False},
}


def event():
    return {'id': '9900001', 'slug': 'cs2-synthetic-a-synthetic-b-2026-10-17',
            'active': True, 'closed': False, 'live': False, 'markets': [{
                'id': '9900002', 'conditionId': 'synthetic-condition',
                'question': 'Counter-Strike: Synthetic A vs Synthetic B (BO3)',
                'sportsMarketType': 'moneyline', 'outcomes': ['Synthetic A', 'Synthetic B'],
                'clobTokenIds': ['synthetic-token-a', 'synthetic-token-b'],
                'gameStartTime': START, 'active': True, 'closed': False, 'acceptingOrders': True,
            }]}


def book(token):
    bid, ask = (0.59, 0.61) if token.endswith('-a') else (0.39, 0.41)
    return {'asset_id': token, 'market': 'synthetic-condition',
            'timestamp': str(int(NOW.timestamp() * 1000)),
            'bids': [{'price': str(bid), 'size': '30'}],
            'asks': [{'price': str(ask), 'size': '30'}]}


class ActualCollectorReplay(unittest.TestCase):
    def collect(self, root: Path, priced: bool, *, research_rows=None, kalshi_payloads=()):
        client = Client(root / 'research/twc-current')
        kalshi_responses = iter(kalshi_payloads)
        games = [{'id': '9900001', 'homeName': 'Synthetic A', 'awayName': 'Synthetic B',
                  'startTime': START}] if priced else []

        def response(method, url, **kwargs):
            if url.startswith(twc_lines.POLY_EVENTS):
                payload = event()
            elif url.startswith(twc_lines.CLOB_BOOK):
                payload = book(url.split('=')[-1])
            elif url.startswith(twc_lines.KALSHI_API):
                payload = next(kalshi_responses, {'events': [], 'cursor': ''})
            else:
                self.fail('Unexpected synthetic request: ' + url)
            result = requests.Response()
            result.status_code = 200
            result.url = url
            result.encoding = 'utf-8'
            result.headers['Content-Type'] = 'application/json'
            # Keep the server's formatting different from Client.save's format.
            result._content = json.dumps(payload, separators=(',', ':')).encode()
            return result

        with patch.object(client.session, 'request', side_effect=response), \
                patch('scripts.sources.time.sleep'), \
                patch('scripts.sources.datetime', wraps=datetime) as clock, \
                patch('scripts.twc_lines.poly_index', return_value=(games, {'status': 'ok'})):
            clock.now.return_value = NOW
            report = twc_lines.collect(client, research_rows or [MATCH], REGISTRY, '2026-10-17', NOW)
        return report, client

    def test_no_provider_round_trip_stays_blank_instead_of_breaking_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.collect(root, priced=False)
            loaded = twc_lines.load(root, NOW, REGISTRY)
            self.assertEqual(len(loaded['matches']), 1)
            row = loaded['matches'][0]
            self.assertEqual(row['teams'], ['Synthetic A', 'Synthetic B'])
            self.assertIsNone(row['probabilities'])
            self.assertIsNone(row['pick_index'])

    def test_priced_round_trip_replays_actual_saved_bytes_and_fixture_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.collect(root, priced=True)
            loaded = twc_lines.load(root, NOW, REGISTRY)
            row = loaded['matches'][0]
            self.assertEqual(row['teams'], ['Synthetic A', 'Synthetic B'])
            self.assertEqual(row['probabilities'], [0.6, 0.4])
            self.assertEqual(row['pick_index'], 0)
            self.assertEqual([q['provider'] for q in row['providers']], ['Polymarket'])

    def test_evidence_digest_matches_the_persisted_representation(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report, client = self.collect(root, priced=True)
            for provider in report['records'][0]['providers']:
                for item in provider.get('evidence') or []:
                    raw = (root / 'research/twc-current' / item['file']).read_bytes()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'],
                                     'HTTP response hash is not the hash of re-serialized evidence bytes')

    def test_collected_provider_entries_are_objects_not_nested_tuples(self):
        with tempfile.TemporaryDirectory() as tmp:
            report, _ = self.collect(Path(tmp), priced=False)
            for provider in report['records'][0]['providers']:
                self.assertIsInstance(provider, dict)
                self.assertIn('provider', provider)

    def test_replay_preserves_names_from_the_real_collected_fixture_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report, _ = self.collect(root, priced=False)
            record = dict(report['records'][0], providers=[])
            row = twc_lines._replay_record(record, root / 'research/twc-current', REGISTRY, NOW)
            self.assertEqual(row['teams'], ['Synthetic A', 'Synthetic B'])

    def test_two_fixture_collections_cannot_overwrite_each_others_kalshi_original(self):
        second = copy.deepcopy(MATCH)
        second['source_url'] = second['source_url'].replace('/9900001/', '/9900002/')
        second['facts']['teams'] = ['Synthetic C', 'Synthetic D']
        second['facts']['starts_at'] = '2026-10-17T17:00:00Z'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report, _ = self.collect(root, priced=False, research_rows=[MATCH, second],
                                     kalshi_payloads=[{'events': [], 'cursor': '', 'synthetic_read': 1},
                                                      {'events': [], 'cursor': '', 'synthetic_read': 2}])
            references = [next(p for p in r['providers'] if p['provider'] == 'Kalshi')['evidence'][0]['file']
                          for r in report['records']]
            self.assertEqual(len(set(references)), 2, 'A later fixture refresh overwrote the first original response')
            loaded = twc_lines.load(root, NOW, REGISTRY)
            self.assertEqual(len(loaded['matches']), 2)
            self.assertTrue(all(row['probabilities'] is None for row in loaded['matches']))

    def test_replay_cannot_re_age_a_kalshi_original_by_editing_the_cached_provider_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report, _ = self.collect(root, priced=False, kalshi_payloads=[
                {'events': [ProviderObservationContract().kalshi()], 'cursor': ''}])
            original = twc_lines.load(root, NOW, REGISTRY)['matches'][0]
            self.assertEqual(original['probabilities'], [0.6, 0.4])
            provider = next(p for p in report['records'][0]['providers'] if p['provider'] == 'Kalshi')
            provider['observed_at'] = iso(NOW + timedelta(hours=1))
            report_path = root / 'research/twc-current' / twc_lines.REPORT
            report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'observation|timestamp'):
                twc_lines.load(root, NOW + timedelta(hours=1), REGISTRY)

    def test_round_trip_retains_previous_validated_read_after_a_second_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.collect(root, priced=True)
            self.collect(root, priced=True)
            loaded = twc_lines.load(root, NOW, REGISTRY)
            self.assertEqual(len(loaded['matches']), 1)
            # A duplicate same-time read must not pretend to be price movement.
            move = loaded['matches'][0].get('movement')
            if move is not None:
                self.assertEqual(move['delta'], [0.0, 0.0])


class ProviderObservationContract(unittest.TestCase):
    def fixture(self):
        return twc_lines.fixtures([MATCH], '2026-10-17')[0]

    def kalshi(self):
        ticker = 'KXCS2GAME-26OCT171000SYNTHETIC'
        return {'event_ticker': ticker, 'series_ticker': 'KXCS2GAME',
                'product_metadata': {'competition': 'CS2'}, 'mutually_exclusive': True,
                'markets': [{'ticker': ticker + '-' + suffix, 'yes_sub_title': name, 'status': 'active',
                             'yes_bid_dollars': bid, 'yes_ask_dollars': ask,
                             'rules_primary': 'This game was originally scheduled for Oct 17, 2026 at 10:00 AM EDT'}
                            for name, suffix, bid, ask in (('Synthetic A', 'A', '0.59', '0.61'),
                                                          ('Synthetic B', 'B', '0.39', '0.41'))]}

    def test_kalshi_valid_current_observation_is_accepted(self):
        quote, reason = twc_lines.kalshi_quote(self.kalshi(), self.fixture(), REGISTRY, iso(NOW), NOW)
        self.assertIsNotNone(quote, reason)
        self.assertEqual(quote['probabilities'], [0.6, 0.4])

    def test_kalshi_stale_future_or_missing_source_observation_stays_blank(self):
        for observed in (iso(NOW - timedelta(hours=9)), iso(NOW + timedelta(hours=1)), None):
            with self.subTest(observed=observed):
                quote, reason = twc_lines.kalshi_quote(self.kalshi(), self.fixture(), REGISTRY, observed, NOW)
                self.assertIsNone(quote)

    def test_kalshi_observation_is_bound_to_the_selected_original_page(self):
        older = NOW - timedelta(hours=1)
        with tempfile.TemporaryDirectory() as tmp:
            client = Client(Path(tmp))
            bodies = iter([{'events': [self.kalshi()], 'cursor': 'next-page'}, {'events': [], 'cursor': ''}])

            def response(method, url, **kwargs):
                result = requests.Response()
                result.status_code, result.url = 200, url
                result.headers['Content-Type'] = 'application/json'
                result._content = json.dumps(next(bodies), separators=(',', ':')).encode()
                return result

            with patch.object(client.session, 'request', side_effect=response), \
                    patch('scripts.sources.time.sleep'), \
                    patch('scripts.sources.datetime', wraps=datetime) as clock:
                clock.now.side_effect = [older, NOW]
                provider, count = twc_lines._collect_kalshi(client, self.fixture(), REGISTRY, NOW, 'synthetic-read')
            self.assertEqual(count, 2)
            self.assertIsNotNone(provider['quote'])
            self.assertEqual(provider['observed_at'], iso(older), 'An unrelated later page re-aged the selected event')

    def test_combined_line_expires_from_the_oldest_contributing_observation(self):
        fixture = self.fixture()
        quote, reason = twc_lines.polymarket_quote(event(), [book('synthetic-token-a'), book('synthetic-token-b')],
                                                    fixture, REGISTRY, NOW)
        self.assertIsNotNone(quote, reason)
        older = iso(NOW - timedelta(hours=7))
        providers = [{'provider': name, 'quote': dict(quote, provider=name), 'status': 'resolved',
                      'reason': '', 'source_url': quote['source_url'], 'observed_at': observed}
                     for name, observed in (('Polymarket', older), ('Kalshi', iso(NOW)))]
        row = twc_lines.analyse(providers, fixture)
        self.assertEqual(row['observed_at'], older, 'A new provider response cannot re-age an older consensus input')


class ReadOnlyRunnerAudit(unittest.TestCase):
    def test_session_source_audit_exercises_twc_collection_before_building(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/origination.yml').read_text()
        collect_at = workflow.index("report = collect(Path('data'))")
        replay_at = workflow.index("lines = load(Path('data'), datetime.now(timezone.utc))")
        build_at = workflow.index('      - name: Build the origination page and check it')
        self.assertLess(collect_at, replay_at)
        self.assertLess(replay_at, build_at)
        row_audit_at = workflow.index('run: python -m scripts.pipeline_audit --source data')
        self.assertLess(row_audit_at, collect_at)
        self.assertIn('::error title=TWC collect/replay contract::', workflow)
        self.assertIn('contents: read', workflow)
        self.assertNotIn('git push', workflow)
        self.assertNotIn('deploy-pages@', workflow)


if __name__ == '__main__':
    unittest.main()
