"""Session ee124e8b: extra guarantees for the rendered-lobby inventory fallback.

The fallback itself was designed in stale PR #229 (session 9c4b1f7a) and
re-applied onto current main by this session. The original suites
(`test_lobby_freshness.RenderedFallback`, `test_9c4b1f7a_inventory_fallback`)
pin the primary paths; these tests pin additional edges this session verified
by hand: non-403 API refusals, the request manifest, the one-page marker
contract, missing rendered evidence, and the rendered-mode dashboard labels.
No test here uses the network or a wall-clock threshold.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import sources
from scripts.sources import SourceError, hotspawn
from scripts.validate import check_inventory

ROOT = Path(__file__).resolve().parents[1]


def row(i, sport='cs2'):
    return {'id': str(i), 'sport_alias': sport, 'participants0_name': 'A', 'participants1_name': 'B'}


def page_html(rows):
    state = {
        'k': {'s': 200, 'u': 'https://x/api/v1/fixtures', 'b': rows},
        'p': {'s': 200, 'u': 'https://x/api/v1/permalinks',
              'b': {'permalinks': {str(r['id']): 'https://www.hotspawn.com/matches/m-' + str(r['id']) for r in rows}}},
    }
    return '<html><script id="ng-state" type="application/json">' + json.dumps(state) + '</script></html>'


class StubClient:
    """Minimal Client stand-in with a real manifest, per-label failures and saved evidence."""

    def __init__(self, rows, block=(), api_error=None):
        self.rows = rows
        self.block = set(block)
        self.api_error = api_error
        self.manifest = []
        self.saved = {}

    def save(self, name, data):
        self.saved[name] = data
        return 'data/evidence/' + name + '.json'

    def json(self, url, label, **kw):
        entry = {'id': label, 'url': url, 'method': 'GET', 'observed_at': '2026-10-24T05:50:00Z',
                 'http_status': None, 'status': 'error'}
        if label == 'hotspawn-fixtures' and (label in self.block or self.api_error is not None):
            entry['error'] = self.api_error or 'hotspawn-fixtures: 403 Client Error: Forbidden'
            self.manifest.append(entry)
            raise SourceError(entry['error'])
        entry.update(status='ok', http_status=200, evidence='data/evidence/hotspawn-fixtures.json')
        self.manifest.append(entry)
        return self.rows, {'observed_at': '2026-10-24T05:50:00Z'}

    def fetch(self, url, label, **kw):
        entry = {'id': label, 'url': url, 'method': 'GET', 'observed_at': '2026-10-24T05:50:00Z',
                 'http_status': None, 'status': 'error'}
        if label in self.block:
            entry['error'] = label + ': 403 Client Error: Forbidden'
            self.manifest.append(entry)
            raise SourceError(entry['error'])
        entry.update(status='ok', http_status=200)
        self.manifest.append(entry)
        return page_html(self.rows), {'observed_at': '2026-10-24T05:50:00Z'}


class RenderedFallbackEdges(unittest.TestCase):
    def test_a_non_403_refusal_still_falls_back_to_the_rendered_array(self):
        # An access failure is an access failure regardless of its status wording.
        client = StubClient([row(1), row(2)], api_error='hotspawn-fixtures: 500 Server Error: Internal Server Error')
        rows, _, health = hotspawn(client)
        self.assertEqual([r['id'] for r in rows], ['1', '2'])
        self.assertEqual(health['inventory_source'], 'rendered-lobby')
        self.assertIn('500', health['api_error'])

    def test_the_refused_api_attempt_stays_in_the_manifest_for_audit(self):
        client = StubClient([row(1)], block=('hotspawn-fixtures',))
        hotspawn(client)
        refused = [r for r in client.manifest if r['id'] == 'hotspawn-fixtures']
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0]['status'], 'error')
        self.assertTrue(any(r['id'] == 'hotspawn-lobby' and r['status'] == 'ok' for r in client.manifest))

    def test_partial_rendered_evidence_names_exactly_the_one_readable_page(self):
        client = StubClient([row(1)], block=('hotspawn-fixtures', 'hotspawn-cs2'))
        rows, _, health = hotspawn(client)
        self.assertEqual(len(rows), 1)
        self.assertEqual(health['crosscheck'], 'rendered-partial')
        rendered = client.saved['hotspawn-rendered-fixtures']
        self.assertEqual(rendered['pages'], ['lobby'])
        self.assertIn('403', rendered['api_error'])
        context = client.saved['hotspawn-context']
        self.assertEqual(context['api_ids'], [])
        self.assertEqual(context['rendered_ids'], ['1'])

    def test_rendered_mode_never_overwrites_the_rendered_rows_with_api_rows(self):
        client = StubClient([row(1), row(2)], block=('hotspawn-fixtures',))
        rows, links, _ = hotspawn(client)
        self.assertEqual({r['id'] for r in rows}, {'1', '2'})
        self.assertEqual(links['2'], 'https://www.hotspawn.com/matches/m-2')

    def test_blocked_everything_fails_closed_and_keeps_no_inventory_claim(self):
        client = StubClient([row(1)], block=('hotspawn-fixtures', 'hotspawn-lobby', 'hotspawn-cs2'))
        with self.assertRaisesRegex(SourceError, 'no rendered lobby page could be read'):
            hotspawn(client)
        self.assertNotIn('hotspawn-rendered-fixtures', client.saved)


class RenderedReplayEdges(unittest.TestCase):
    def build_tree(self, context, rendered_rows, requests):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        evidence = Path(folder.name) / 'evidence'
        evidence.mkdir(parents=True)
        (evidence / 'hotspawn-context.json').write_text(json.dumps(context))
        (evidence / 'hotspawn-rendered-fixtures.json').write_text(json.dumps({
            'observed_at': '2026-10-24T05:50:00Z', 'pages': context['verified_pages'],
            'api_error': 'hotspawn-fixtures: 403 Client Error: Forbidden', 'rows': rendered_rows}))
        return evidence, {'inventory_observed_at': '2026-10-24T05:50:00Z', 'requests': requests}

    def test_partial_marker_must_match_the_single_page_read(self):
        context = {'observed_at': '2026-10-24T05:50:00Z', 'api_ids': [], 'rendered_ids': ['1'],
                   'lobby_ids': ['1'], 'cs2_ids': [], 'verified_pages': ['lobby'],
                   'crosscheck': 'rendered-partial', 'inventory_source': 'rendered-lobby'}
        requests = [{'id': 'hotspawn-fixtures', 'status': 'error', 'observed_at': '2026-10-24T05:50:00Z'},
                    {'id': 'hotspawn-lobby', 'status': 'ok', 'observed_at': '2026-10-24T05:50:00Z'}]
        evidence, data = self.build_tree(context, [row(1)], requests)
        raw, returned, _ = check_inventory(evidence, [{'id': '1'}], data)
        self.assertEqual(set(raw), {'1'})
        self.assertEqual(returned['crosscheck'], 'rendered-partial')
        # Claiming a two-page read while only one page's evidence exists must fail.
        lying = copy.deepcopy(context)
        lying['crosscheck'] = 'rendered'
        bad_evidence, bad_data = self.build_tree(lying, [row(1)], requests)
        with self.assertRaisesRegex(ValueError, 'cross-check marker'):
            check_inventory(bad_evidence, [{'id': '1'}], bad_data)

    def test_rendered_mode_without_its_saved_payload_is_refused(self):
        context = {'observed_at': '2026-10-24T05:50:00Z', 'api_ids': [], 'rendered_ids': ['1'],
                   'lobby_ids': ['1'], 'cs2_ids': ['1'], 'verified_pages': ['lobby', 'cs2'],
                   'crosscheck': 'rendered', 'inventory_source': 'rendered-lobby'}
        requests = [{'id': 'hotspawn-fixtures', 'status': 'error', 'observed_at': '2026-10-24T05:50:00Z'},
                    {'id': 'hotspawn-lobby', 'status': 'ok', 'observed_at': '2026-10-24T05:50:00Z'}]
        evidence, data = self.build_tree(context, [row(1)], requests)
        (evidence / 'hotspawn-rendered-fixtures.json').unlink()
        with self.assertRaises(FileNotFoundError):
            check_inventory(evidence, [{'id': '1'}], data)


class RenderedDashboardLabels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'data/latest.json').read_text())
        cls.data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())

    def render(self, marker):
        data = copy.deepcopy(self.data)
        data['coverage_complete'] = True
        data['inventory_crosscheck'] = marker
        from scripts.build import summary, coverage
        return summary(data, './'), coverage(data, './')

    def test_rendered_markers_publish_the_refused_api_labels(self):
        summary_html, coverage_html = self.render('rendered')
        self.assertIn('FIXTURE API REFUSED, LOBBY PAGES AGREE', summary_html)
        self.assertIn('from the rendered lobby payload; the fixture API was unavailable', coverage_html)
        self.assertIn('from the rendered lobby payload; the fixture API was unavailable this cycle.', coverage_html)

    def test_rendered_partial_marker_publishes_the_one_page_label(self):
        summary_html, coverage_html = self.render('rendered-partial')
        self.assertIn('FIXTURE API REFUSED, ONE LOBBY PAGE READ', summary_html)
        soup = BeautifulSoup(coverage_html, 'html.parser')
        self.assertIn('rendered lobby pages', soup.get_text(' ', strip=True))

    def test_the_healthy_marker_keeps_the_original_wording(self):
        summary_html, coverage_html = self.render('complete')
        self.assertIn('FULL INVENTORY RECONCILED', summary_html)
        self.assertIn('reconciled across three official responses', coverage_html)


if __name__ == '__main__':
    unittest.main()
