"""Contract tests for scripts/coverage_probe.py (session arena-8fa2b226).

The probe may explain a blank and surface a lead. It may never fill a blank. These tests pin that
boundary, the reuse of the production join for rejection reasons, and the reachability-only rule
for book endpoints.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.coverage_probe import overlap, probe_book, provider_listings, run  # noqa: E402

START = '2026-10-18T14:00:00Z'
START_MS = int(datetime(2026, 10, 18, 14, 0, tzinfo=timezone.utc).timestamp() * 1000)  # provider clock, milliseconds


def write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def snapshot(tmp: Path, *, display_name_block: bool):
    """One unresolved fixture: either a provider lists it under a variant name, or under a wrong time."""
    provider_name = 'BET-M 33' if display_name_block else 'BET-M'
    provider_start = START_MS if display_name_block else START_MS + 40 * 60 * 1000
    latest = {'coverage_complete': True, 'inventory_observed_at': '2026-10-17T00:00:00Z',
              'counts': {'inventory': 1, 'upcoming': 1},
              'matches': [{'id': '1', 'teams': [{'id': '9', 'name': 'BET-M'}, {'id': '10', 'name': 'Just Players'}],
                           'competition': 'NODWIN Clutch Series #13', 'starts_at': START,
                           'locks_at': '2026-10-18T13:54:00Z', 'availability': 'open', 'tier': 'b',
                           'source_url': 'https://www.hotspawn.com/matches/bet-m-vs-just-players-nodwin-clutch-series-13-1',
                           'research': [], 'analysis': None, 'pick_index': None, 'limitations': []}]}
    origination = {'schema_version': 1, 'source_snapshot_at': '2026-10-17T00:00:00Z',
                   'counts': {'active': 1, 'resolved': 0, 'unresolved': 1, 'with_pick': 0},
                   'unresolved_ids': ['1'], 'flags': [],
                   'matches': [{'id': '1', 'teams': [{'id': '9', 'name': 'BET-M'}, {'id': '10', 'name': 'Just Players'}],
                                'competition': 'NODWIN Clutch Series #13', 'starts_at': START,
                                'locks_at': '2026-10-18T13:54:00Z', 'availability': 'open', 'tier': 'b',
                                'source_url': 'https://www.hotspawn.com/matches/bet-m-vs-just-players-nodwin-clutch-series-13-1',
                                'origination': None, 'pick_index': None,
                                'research': [
                                    {'stage': 'Primary: Polymarket', 'status': 'unresolved',
                                     'detail': 'No unique exact-name, exact-start-time fixture.',
                                     'source_url': 'https://polymarket.com/esports/cs2'},
                                    {'stage': 'Valve research model', 'status': 'unresolved',
                                     'detail': 'Just Players: multiple Valve rosters share this name; identity is unresolved',
                                     'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'}]}]}
    write(tmp / 'data' / 'latest.json', latest)
    write(tmp / 'data' / 'origination.json', origination)
    write(tmp / 'data' / 'origination' / 'aliases.json', {'schema_version': 1, 'aliases': []})
    write(tmp / 'data' / 'origination' / 'evidence' / 'live-thunderpick-matches.json',
          {'data': {'upcoming': [{'id': 555, 'gameId': 6, 'isLive': False, 'startTime': provider_start,
                                  'teams': {'home': {'name': provider_name}, 'away': {'name': 'Just Players'}},
                                  'market': {'name': 'Match winner', 'status': 1,
                                             'home': {'name': provider_name, 'odds': 1.55, 'status': 1},
                                             'away': {'name': 'Just Players', 'odds': 2.35, 'status': 1}}}]}})
    return tmp / 'data'


class ProbeContract(unittest.TestCase):
    def test_reports_display_name_as_the_blocker_and_proposes_nothing_applied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = snapshot(Path(tmpdir), display_name_block=True)
            report = run(data, live=False)
            fixture = report['fixtures'][0]
            self.assertEqual(report['counts']['unresolved_fixtures'], 1)
            self.assertEqual(fixture['likely_blocker'], 'display-name only')
            lead = fixture['provider_leads'][0]
            self.assertEqual(lead['provider'], 'Thunderpick')
            self.assertEqual(lead['strict_join'], 'names')
            self.assertEqual(lead['blocks_on'], 'display name (needs a reviewed alias)')
            self.assertFalse(lead['would_join'])
            proposal = fixture['alias_proposal']
            self.assertEqual(proposal['provider_names'], ['BET-M 33', 'Just Players'])
            self.assertFalse(proposal['applied'])
            self.assertIn('aliases.json', proposal['requires'])

    def test_wrong_start_time_is_reported_as_a_time_block_and_never_as_an_alias_lead(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = snapshot(Path(tmpdir), display_name_block=False)
            fixture = run(data, live=False)['fixtures'][0]
            self.assertEqual(fixture['provider_leads'][0]['strict_join'], 'time')
            self.assertEqual(fixture['likely_blocker'], 'listed start time')
            self.assertTrue(fixture['blockers']['time'])
            self.assertIsNone(fixture['alias_proposal'])

    def test_probe_never_writes_a_probability_pick_or_line_for_a_blank_fixture(self):
        banned = {'probabilities', 'probability', 'pick', 'pick_index', 'fair_decimal', 'odds', 'analysis', 'suggested_pick'}

        def walk(node, path=''):
            if isinstance(node, dict):
                for key, value in node.items():
                    self.assertNotIn(key, banned, f'{path}/{key} must never be produced by the probe')
                    walk(value, f'{path}/{key}')
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, f'{path}[{index}]')

        with tempfile.TemporaryDirectory() as tmpdir:
            report = run(snapshot(Path(tmpdir), display_name_block=True), live=False)
            walk({k: v for k, v in report.items() if k != 'counts'})
            self.assertNotIn('book_probes', json.dumps(report['fixtures']))

    def test_reasons_and_trail_are_the_ladder_reasons_not_new_inventions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture = run(snapshot(Path(tmpdir), display_name_block=True), live=False)['fixtures'][0]
            self.assertIn('No unique exact-name, exact-start-time fixture.', fixture['reasons'])
            self.assertTrue(all(step['source_url'].startswith('https://') for step in fixture['resolution_trail']))

    def test_offline_mode_does_not_touch_the_network_and_live_mode_is_reachability_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = snapshot(Path(tmpdir), display_name_block=True)
            self.assertEqual(run(data, live=False)['book_probes'], [])
            import scripts.coverage_probe as module

            calls = []
            original = module.probe_book

            def fake(url, timeout=20):
                calls.append(url)
                return {'url': url, 'method': 'GET', 'observed_at': module.now_iso(), 'status': 'unavailable',
                        'detail': "403 Client Error: Forbidden for url: https://gg.bet/…", 'role': 'reachability check only'}

            module.probe_book = fake
            try:
                report = run(data, live=True)
            finally:
                module.probe_book = original
            self.assertEqual(len(calls), len(module.BOOK_CANDIDATES))
            self.assertEqual(len(report['book_probes']), len(module.BOOK_CANDIDATES))
            for probe in report['book_probes']:
                self.assertEqual(probe['status'], 'unavailable')
                self.assertNotIn('probabilities', json.dumps(probe))
                self.assertIn('why_checked', probe)
            # A refused book must not quietly resolve a fixture.
            self.assertEqual(report['counts']['with_pick'] if 'with_pick' in report['counts'] else 0, 0)
            self.assertIsNone(run(data, live=True)['fixtures'][0].get('origination'))

    def test_provider_listings_tolerate_missing_or_broken_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir)
            self.assertEqual(provider_listings(evidence), [])
            write(evidence / 'live-thunderpick-matches.json', {'data': {'upcoming': ['not-a-row', {'teams': None}]}})
            rows = provider_listings(evidence)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['names'], ['', ''])

    def test_name_overlap_is_a_lead_heuristic_only(self):
        self.assertGreater(overlap('BET-M 33', 'BET-M'), 0.5)
        self.assertEqual(overlap('Aurora', 'Just Players'), 0.0)

    def test_probe_book_records_a_failure_verbatim_without_inventing_data(self):
        result = probe_book('http://127.0.0.1:1/definitely-not-a-book', timeout=2)
        self.assertEqual(result['status'], 'unavailable')
        self.assertTrue(result['detail'])
        self.assertNotIn('odds', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
