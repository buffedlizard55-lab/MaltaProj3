"""Session ee124e8b: end-to-end proof of the rendered-lobby fallback on a 403.

The unit tests in ``test_lobby_freshness`` and ``test_9c4b1f7a_inventory_fallback``
pin the reader and the validator separately. This test drives the *real*
``scripts.collect.collect`` -> ``scripts.validate.check_data`` ->
``scripts.build.build`` path with a fake HTTP transport that reproduces the
2026-10-23T10:43Z runner condition: the scheduled-fixture API answers 403 while
both rendered lobby pages still embed the identical public array, and every
other external surface is refused as well. It is fully offline and
wall-clock independent; no probability, pick or alias is invented.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from scripts import collect as collect_module
from scripts.sources import Client, FIXTURES_API, LOBBY, CS2_LOBBY, SourceError


def page_html(rows):
    state = {
        'k': {'s': 200, 'u': 'https://play.hotspawn.com/api/v1/fixtures', 'b': rows},
        'p': {'s': 200, 'u': 'https://play.hotspawn.com/api/v1/permalinks',
              'b': {'permalinks': {str(r['id']): 'https://www.hotspawn.com/matches/m-' + str(r['id']) for r in rows}}},
    }
    return '<html><script id="ng-state" type="application/json">' + json.dumps(state) + '</script></html>'


class FakeResponse:
    def __init__(self, status_code, url, content=b'', content_type='text/html'):
        self.status_code = status_code
        self.url = url
        self.content = content
        self.headers = {'Content-Type': content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'{self.status_code} Client Error for url: {self.url}')

    def json(self):
        return json.loads(self.content.decode())

    @property
    def text(self):
        return self.content.decode()


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def request(self, method, url, json=None, headers=None, timeout=None, allow_redirects=None):
        if url.startswith(FIXTURES_API):
            return FakeResponse(403, url, b'Forbidden', 'application/json')
        if url.startswith(LOBBY) or url.startswith(CS2_LOBBY):
            return FakeResponse(200, url, page_html(self.rows).encode())
        # Every other external surface (Polymarket, HLTV, books, Valve, rules)
        # is refused; the collector must record each as a limitation, not abort.
        return FakeResponse(403, url, b'Forbidden')


class TransportFallbackClient(Client):
    def __init__(self, output, rows):
        super().__init__(output)
        self.session = FakeSession(rows)


class RenderedCollectionEndToEnd(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        start = now + timedelta(days=2)
        lock = now + timedelta(days=2) - timedelta(minutes=6)
        self.rows = [
            {
                'id': '900001', 'sport_alias': 'cs2', 'status': 'scheduled',
                'competition_id': '9001', 'competition_name': 'Fallback Test Cup',
                'scheduled_start_time': str(int(start.timestamp() * 1000)),
                'lock_time': str(int(lock.timestamp() * 1000)),
                'lock_offset_sec': 360, 'tier': 'c', 'best_of': None, 'series_format': None,
                'end_time': str(int((start + timedelta(hours=2)).timestamp() * 1000)),
                'participants0_id': '1', 'participants0_name': 'Alpha Team',
                'participants1_id': '2', 'participants1_name': 'Beta Team',
            },
            {
                'id': '900002', 'sport_alias': 'cs2', 'status': 'scheduled',
                'competition_id': '9001', 'competition_name': 'Fallback Test Cup',
                'scheduled_start_time': str(int((start + timedelta(hours=1)).timestamp() * 1000)),
                'lock_time': str(int((lock + timedelta(hours=1)).timestamp() * 1000)),
                'lock_offset_sec': 360, 'tier': 'b', 'best_of': None, 'series_format': None,
                'end_time': None,
                'participants0_id': '3', 'participants0_name': 'Gamma Team',
                'participants1_id': '4', 'participants1_name': 'Delta Team',
            },
        ]
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = Path(self.tmp.name) / 'data'
        self.data_dir.mkdir()
        self._original_client = collect_module.Client
        collect_module.Client = lambda output: TransportFallbackClient(output, self.rows)

    def tearDown(self):
        collect_module.Client = self._original_client

    def test_a_refused_api_still_publishes_a_complete_rendered_snapshot(self):
        snapshot = collect_module.collect(self.data_dir)

        # The refresh did not disown its inventory: coverage is complete and
        # the snapshot is explicitly labelled as a rendered-lobby read.
        self.assertTrue(snapshot['coverage_complete'])
        self.assertEqual(snapshot['inventory_crosscheck'], 'rendered')
        self.assertEqual({m['id'] for m in snapshot['matches']}, {'900001', '900002'})
        self.assertTrue(any(f['id'] == 'inventory-api-unavailable' for f in snapshot['flags']))
        self.assertIn('rendered Hotspawn lobby pages', snapshot['inventory_definition'])

        evidence = self.data_dir / 'evidence'
        context = json.loads((evidence / 'hotspawn-context.json').read_text())
        self.assertEqual(context['inventory_source'], 'rendered-lobby')
        self.assertEqual(context['api_ids'], [])
        self.assertEqual(set(context['rendered_ids']), {'900001', '900002'})
        rendered = json.loads((evidence / 'hotspawn-rendered-fixtures.json').read_text())
        self.assertEqual(rendered['pages'], ['lobby', 'cs2'])
        self.assertIn('403', rendered['api_error'])
        # The refused API attempt is retained in the request manifest.
        requests_log = snapshot['requests']
        self.assertTrue(any(r['id'] == 'hotspawn-fixtures' and r['status'] == 'error' for r in requests_log))
        self.assertTrue(any(r['id'] == 'hotspawn-lobby' and r['status'] == 'ok' for r in requests_log))

        # The strict first-party replay accepts the rendered snapshot.
        from scripts.validate import check_data
        check_data(self.data_dir)

        # The exact snapshot fields the dashboard builder turns into labels.
        # (Label rendering itself is pinned against the real checked-in data in
        # tests.test_ee124e8b_inventory_fallback.RenderedDashboardLabels.)
        self.assertEqual(snapshot['sources'][0]['crosscheck'], 'rendered')
        self.assertEqual(snapshot['sources'][0]['inventory_source'], 'rendered-lobby')
        self.assertIn('same official array', snapshot['sources'][0]['detail'])
        # Re-collecting over the same refused transport is a no-op on evidence:
        # the second run replays from the same saved rendered payload.
        again = collect_module.collect(self.data_dir)
        self.assertTrue(again['coverage_complete'])
        check_data(self.data_dir)

    def test_an_all_refused_round_still_fails_closed(self):
        class AllBlocked(FakeSession):
            def request(self, method, url, json=None, headers=None, timeout=None, allow_redirects=None):
                return FakeResponse(403, url, b'Forbidden')

        collect_module.Client = lambda output: self._all_blocked_client(output, AllBlocked)
        snapshot = collect_module.collect(self.data_dir)
        self.assertFalse(snapshot['coverage_complete'])
        self.assertEqual(snapshot['run_status'], 'degraded')
        self.assertTrue(any(f['id'] == 'inventory-failed' for f in snapshot['flags']))
        self.assertFalse((self.data_dir / 'evidence' / 'hotspawn-rendered-fixtures.json').exists())

    def _all_blocked_client(self, output, session_cls):
        client = TransportFallbackClient(output, self.rows)
        client.session = session_cls(self.rows)
        return client


if __name__ == '__main__':
    unittest.main()
