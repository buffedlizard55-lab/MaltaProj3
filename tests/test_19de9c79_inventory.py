"""Replay contract for Hotspawn's official-lobby API-outage recovery."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.collect import _collect_into, counts, normalize_fixture
from scripts.domain import iso
from scripts.sources import CS2_LOBBY, LOBBY, SourceError
from scripts.validate import check_data

NOW = datetime(2026, 10, 23, 4, 0, tzinfo=timezone.utc)
OBSERVED = '2026-10-23T04:00:00Z'


def row(identifier='1'):
    return {
        'id': identifier, 'sport_alias': 'cs2', 'status': 'scheduled',
        'participants0_id': 'a', 'participants1_id': 'b',
        'participants0_name': 'Alpha', 'participants1_name': 'Beta',
        'competition_name': 'Synthetic official-payload Cup', 'competition_id': 'cup',
        'scheduled_start_time': '2026-10-24T04:00:00Z',
        'lock_time': '2026-10-24T03:55:00Z', 'best_of': 3,
        'series_format': 'bo3', 'tier': 'B', 'lock_offset_sec': 300,
    }


def html_for(rows):
    state = {'fixtures': {'s': 200, 'u': 'https://play.hotspawn.com/api/v1/fixtures', 'b': rows}}
    return '<html><script id="ng-state" type="application/json">' + json.dumps(state) + '</script></html>'


class HydrationReplay(unittest.TestCase):
    def seed(self, root: Path):
        evidence = root / 'evidence'
        evidence.mkdir(parents=True)
        raw = [row()]
        html = html_for(raw)
        url = CS2_LOBBY + '?cb=1792723200'
        document_ref = 'data/evidence/hotspawn-inventory-cs2-html.json'
        raw_ref = 'data/evidence/hotspawn-fixtures.json'
        response_hash = hashlib.sha256(html.encode()).hexdigest()
        document = {'url': url, 'observed_at': OBSERVED, 'html': html,
                    'response_sha256': response_hash, 'html_utf8_sha256': response_hash}
        (evidence / 'hotspawn-inventory-cs2-html.json').write_text(json.dumps(document))
        (evidence / 'hotspawn-fixtures.json').write_text(json.dumps(raw))
        links = {'1': 'https://www.hotspawn.com/matches/alpha-vs-beta-1'}
        match = normalize_fixture(raw[0], links, OBSERVED, NOW)
        context = {'observed_at': OBSERVED, 'api_ids': ['1'], 'lobby_ids': [], 'cs2_ids': ['1'],
                   'verified_pages': ['cs2'], 'crosscheck': 'partial', 'permalinks': links,
                   'inventory_via': 'cs2-hydration', 'source_document': document_ref}
        (evidence / 'hotspawn-context.json').write_text(json.dumps(context))
        request = {'id': 'hotspawn-fixtures', 'url': url, 'method': 'GET', 'observed_at': OBSERVED,
                   'http_status': 200, 'status': 'ok', 'evidence': raw_ref,
                   'source_document': document_ref, 'via': 'official-lobby-hydration',
                   'response_sha256': response_hash}
        flag = {'id': 'unresolved-1', 'title': 'Unresolved synthetic row', 'detail': 'No price',
                'source_urls': [CS2_LOBBY], 'match_ids': ['1'], 'severity': 'warning'}
        snapshot = {'schema_version': 1, 'generated_at': OBSERVED, 'last_attempted_at': OBSERVED,
                    'analysis_as_of': OBSERVED, 'inventory_observed_at': OBSERVED,
                    'coverage_complete': True, 'run_status': 'partial-picks',
                    'inventory_via': 'cs2-hydration', 'inventory_source_document': document_ref,
                    'counts': counts([match]), 'matches': [match], 'sources': [], 'flags': [flag],
                    'requests': [request]}
        (root / 'latest.json').write_text(json.dumps(snapshot))
        return document, request

    def test_original_html_extracted_rows_and_successful_transport_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.seed(Path(tmp))
            result = check_data(Path(tmp))
            self.assertTrue(result['coverage_complete'])

    def test_extracted_rows_cannot_differ_from_the_original_official_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            document, _ = self.seed(root)
            document['html'] = html_for([row('different')])
            document['html_utf8_sha256'] = hashlib.sha256(document['html'].encode()).hexdigest()
            (root / 'evidence/hotspawn-inventory-cs2-html.json').write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, 'replay'):
                check_data(root)

    def test_recovery_cannot_be_relabelled_as_an_unofficial_or_direct_api_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, request = self.seed(root)
            for field, value in (('url', 'https://unverified.invalid/fixtures'),
                                 ('via', 'direct-api'), ('method', 'POST')):
                with self.subTest(field=field):
                    snapshot = json.loads((root / 'latest.json').read_text())
                    snapshot['requests'] = [dict(request, **{field: value})]
                    (root / 'latest.json').write_text(json.dumps(snapshot))
                    with self.assertRaises(ValueError):
                        check_data(root)


class CollectorRecoveryIntegration(unittest.TestCase):
    def test_direct_api_outage_recovers_validates_and_labels_the_complete_inventory(self):
        raw = row()
        raw['scheduled_start_time'] = iso(NOW + timedelta(hours=24))
        raw['lock_time'] = iso(NOW + timedelta(hours=23, minutes=55))
        html = html_for([raw])

        def fake_json(client, url, label, **kwargs):
            client.manifest.append({'id': label, 'url': url, 'method': 'GET', 'observed_at': OBSERVED,
                                    'http_status': 403, 'status': 'error', 'error': 'synthetic API refusal'})
            raise SourceError('hotspawn-fixtures: synthetic 403')

        def fake_fetch(client, url, label, **kwargs):
            body = html if label in {'hotspawn-lobby', 'hotspawn-cs2'} else '<html>picks lock 5 minutes before start</html>'
            request = {'id': label, 'url': url, 'final_url': url, 'method': 'GET', 'observed_at': OBSERVED,
                       'http_status': 200, 'status': 'ok', 'response_sha256': hashlib.sha256(body.encode()).hexdigest(),
                       'cache_age_sec': '0', 'cache_status': 'MISS'}
            client.manifest.append(request)
            return body, request

        def health(name, url, status='ok'):
            return {'name': name, 'url': url, 'status': status, 'observed_at': OBSERVED,
                    'records': 0, 'detail': 'synthetic no matching external rows'}

        with tempfile.TemporaryDirectory() as tmp, \
                patch('scripts.collect.datetime', wraps=datetime) as clock, \
                patch('scripts.collect.Client.json', new=fake_json), \
                patch('scripts.collect.Client.fetch', new=fake_fetch), \
                patch('scripts.collect.poly_index', return_value=([], health('Polymarket CS2', 'https://polymarket.com/esports/cs2'))), \
                patch('scripts.collect.hltv_research', return_value=([], health('HLTV fallback research', 'https://www.hltv.org/matches'))), \
                patch('scripts.collect.thunderpick', return_value=([], health('Thunderpick esportsbook', 'https://thunderpick.io/esports/counter-strike'))), \
                patch('scripts.collect.book_page_check', side_effect=lambda client, url, label, title: health(title, url, 'unavailable')), \
                patch('scripts.collect.valve_ratings', return_value=([], health('Valve official rating fallback', 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'unavailable'))):
            clock.now.return_value = NOW
            root = Path(tmp)
            snapshot = _collect_into(root)
            self.assertTrue(snapshot['coverage_complete'])
            self.assertEqual(snapshot['inventory_via'], 'cs2-hydration')
            self.assertEqual(snapshot['counts']['inventory'], 1)
            self.assertIn('official CS2 lobby Angular hydration', snapshot['inventory_definition'])
            self.assertTrue((root / 'evidence/hotspawn-inventory-cs2-html.json').is_file())
            self.assertEqual(json.loads((root / 'evidence/hotspawn-fixtures.json').read_text()), [raw])
            check_data(root)


if __name__ == '__main__':
    unittest.main()
