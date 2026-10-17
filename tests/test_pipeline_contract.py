"""Independent production-contract checks: run the real collector, then replay it.

Everything returned by HTTP in this file is synthetic. In particular, the
response body is compact JSON while Client.save stores indented JSON, just as
normal provider responses do. Hand-writing a replay report hides schema and
serialization mistakes at this boundary; these tests deliberately do not.
"""
from __future__ import annotations

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
    def collect(self, root: Path, priced: bool):
        client = Client(root / 'research/twc-current')
        games = [{'id': '9900001', 'homeName': 'Synthetic A', 'awayName': 'Synthetic B',
                  'startTime': START}] if priced else []

        def response(method, url, **kwargs):
            if url.startswith(twc_lines.POLY_EVENTS):
                payload = event()
            elif url.startswith(twc_lines.CLOB_BOOK):
                payload = book(url.split('=')[-1])
            elif url.startswith(twc_lines.KALSHI_API):
                payload = {'events': [], 'cursor': ''}
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
            report = twc_lines.collect(client, [MATCH], REGISTRY, '2026-10-17', NOW)
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


class ReadOnlyRunnerAudit(unittest.TestCase):
    def test_session_source_audit_exercises_twc_collection_before_building(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/origination.yml').read_text()
        collect_at = workflow.index("report = collect(Path('data'))")
        replay_at = workflow.index("lines = load(Path('data'), datetime.now(timezone.utc))")
        build_at = workflow.index('      - name: Build the origination page and check it')
        self.assertLess(collect_at, replay_at)
        self.assertLess(replay_at, build_at)
        self.assertIn('::error title=TWC collect/replay contract::', workflow)
        self.assertIn('contents: read', workflow)
        self.assertNotIn('git push', workflow)
        self.assertNotIn('deploy-pages@', workflow)


if __name__ == '__main__':
    unittest.main()
