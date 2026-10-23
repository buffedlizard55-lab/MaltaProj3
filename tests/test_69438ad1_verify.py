"""Session arena-69438ad1 — contract tests for the published-vs-live reconciliation.

These run fully offline: the originals directory is synthesised here, exactly the
shape ``scripts.69438ad1_verify.Reader`` saves on a live read, so the offline
replay path and the live path share one implementation.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import importlib

mod = importlib.import_module('scripts.69438ad1_verify')

UTC = timezone.utc
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=UTC)
NOW_ISO = NOW.isoformat(timespec='seconds').replace('+00:00', 'Z')


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec='seconds').replace('+00:00', 'Z')


def epoch(moment: datetime) -> str:
    return str(int(moment.timestamp() * 1000))


def save(originals: Path, label: str, url: str, body, status: int = 200) -> None:
    text = body if isinstance(body, str) else json.dumps(body)
    (originals / f'{label}.json').write_text(json.dumps({
        'url': url, 'label': label, 'observed_at': NOW_ISO, 'http_status': status,
        'ok': status < 400, 'sha256': '0' * 64, 'x_cache': 'MISS', 'body': text,
    }) + '\n')


def fixture_row(fid: str, start: datetime, a='Alpha', b='Beta') -> dict:
    return {'id': fid, 'competition_name': 'Test League', 'sport_alias': 'cs2', 'status': 'scheduled',
            'tier': 'c', 'scheduled_start_time': epoch(start),
            'participants0_name': a, 'participants1_name': b}


def published_origination() -> dict:
    return {'matches': [
        {'id': '1', 'availability': 'upcoming', 'competition': 'Test League', 'starts_at': iso(NOW + timedelta(hours=2)),
         'teams': [{'name': 'Alpha'}, {'name': 'Beta'}],
         'origination': {'method': 'model', 'probabilities': [0.6, 0.4], 'pick_index': 0,
                         'source_url': 'https://www.hltv.org/ranking/teams'}},
        {'id': '2', 'availability': 'upcoming', 'competition': 'Test League', 'starts_at': iso(NOW + timedelta(hours=3)),
         'teams': [{'name': 'Gamma'}, {'name': 'Delta'}],
         'origination': {'method': 'model', 'probabilities': [0.5, 0.5], 'pick_index': None,
                         'source_url': 'https://www.hltv.org/ranking/teams'}},
        {'id': '3', 'availability': 'upcoming', 'competition': 'Test League', 'starts_at': iso(NOW + timedelta(hours=5)),
         'teams': [{'name': 'Epsilon'}, {'name': 'Zeta'}],
         'origination': {}},
    ]}


class ReconciliationTests(unittest.TestCase):
    def write_originals(self, originals: Path, generated: datetime, live: list[dict],
                        latest_ids=('1', '2', '3')) -> None:
        originals.mkdir(parents=True, exist_ok=True)
        save(originals, 'published-latest', 'https://x/data/latest.json', {
            'generated_at': iso(generated), 'inventory_observed_at': iso(generated),
            'coverage_complete': True, 'run_status': 'ok',
            'counts': {'inventory': 4, 'upcoming': 3},
            'matches': [{'id': i} for i in latest_ids]})
        save(originals, 'published-origination', 'https://x/data/origination.json', published_origination())
        save(originals, 'published-row-audit', 'https://x/data/row-source-audit.json',
             {'totals': {'rows': 3, 'ok': 3, 'flagged': 0, 'navigation': 0, 'violation': 0}})
        save(originals, 'live-fixtures-api', 'https://x/api', live)
        save(originals, 'live-lobby', 'https://x/lobby', '<html>lobby</html>')
        save(originals, 'live-cs2-lobby', 'https://x/cs2', '<html>cs2</html>')

    def run_verify(self, generated: datetime, live: list[dict]):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            originals = tmp / 'originals'
            out = tmp / 'out'
            self.write_originals(originals, generated, live)
            rc = mod.main(['--from', str(originals), '--out', str(out), '--now', NOW_ISO])
            self.assertEqual(rc, 0)
            report = json.loads((out / 'published-vs-live.json').read_text())
            rows = json.loads((out / 'row-audit.json').read_text())
            flags = json.loads((out / 'flags.json').read_text())
            markdown = (out / 'verification.md').read_text()
            return report, rows, flags, markdown

    def test_stale_snapshot_missing_fixture_and_row_problems_are_all_flagged(self):
        live = [fixture_row('1', NOW + timedelta(hours=2)),
                fixture_row('2', NOW + timedelta(hours=3)),
                fixture_row('9', NOW + timedelta(hours=4), 'New', 'Side'),
                fixture_row('5', NOW - timedelta(hours=1), 'Past', 'Start')]
        report, rows, flags, markdown = self.run_verify(NOW - timedelta(hours=9), live)
        ids = [f['id'] for f in flags]
        self.assertIn('69438ad1-published-snapshot-stale', ids)
        self.assertIn('69438ad1-coverage-gap', ids)
        self.assertIn('69438ad1-row-contract', ids)
        self.assertEqual(report['live']['upcoming'], 3)
        self.assertEqual([r['id'] for r in report['missing_from_active_list']], ['9'])
        self.assertEqual(report['published_active_not_in_live_source'], ['3'])
        self.assertEqual(report['published']['age_hours'], 9.0)
        self.assertTrue(report['published']['stale'])
        self.assertEqual(report['row_audit_totals'], {'active_rows': 3, 'with_pick': 1, 'even_no_side': 1,
                                                      'problems': 1,
                                                      'published_row_source_audit':
                                                      {'rows': 3, 'ok': 3, 'flagged': 0, 'navigation': 0,
                                                       'violation': 0}})
        self.assertIn('New', markdown)
        gap = next(f for f in flags if f['id'] == '69438ad1-coverage-gap')
        self.assertEqual(gap['match_ids'], ['9'])
        self.assertIn('https://www.hotspawn.com/matches/new-vs-side-test-league-9', gap['source_urls'])

    def test_fresh_snapshot_without_coverage_gap_flags_no_staleness_and_no_gap(self):
        live = [fixture_row('1', NOW + timedelta(hours=2)),
                fixture_row('2', NOW + timedelta(hours=3))]
        report, rows, flags, markdown = self.run_verify(NOW - timedelta(hours=1), live)
        ids = [f['id'] for f in flags]
        self.assertNotIn('69438ad1-published-snapshot-stale', ids)
        self.assertNotIn('69438ad1-coverage-gap', ids)
        # Row 3 is published active with no estimate at all, so the row-contract flag
        # fires; the clean-row flag is reserved for a contract with no problems.
        self.assertIn('69438ad1-row-contract', ids)
        self.assertNotIn('69438ad1-row-contract-clean', ids)
        self.assertEqual(report['missing_from_active_list'], [])
        # Row 3 stays published as active with no estimate: that is a row-contract problem,
        # never a silent blank.
        self.assertEqual(report['row_audit_totals']['problems'], 1)

    def test_flag_schema_is_renderable(self):
        live = [fixture_row('1', NOW + timedelta(hours=2))]
        _, _, flags, _ = self.run_verify(NOW - timedelta(hours=9), live)
        for flag in flags:
            for key in ('id', 'severity', 'match_ids', 'title', 'detail', 'source_urls'):
                self.assertIn(key, flag, flag['id'])
                self.assertTrue(flag[key] not in (None, ''), (flag['id'], key))
            for url in flag['source_urls']:
                self.assertTrue(url.startswith('https://'), (flag['id'], url))

    def test_unreachable_sources_are_unavailable_not_empty(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            originals = tmp / 'originals'
            originals.mkdir()
            save(originals, 'published-latest', 'https://x/latest.json', {'generated_at': iso(NOW)}, status=503)
            save(originals, 'live-fixtures-api', 'https://x/api', '[]', status=503)
            out = tmp / 'out'
            rc = mod.main(['--from', str(originals), '--out', str(out), '--now', NOW_ISO])
            self.assertEqual(rc, 0)
            report = json.loads((out / 'published-vs-live.json').read_text())
            self.assertEqual(report['sources']['live_fixtures_api']['http_status'], 503)
            self.assertFalse(report['sources']['live_fixtures_api']['ok'])
            self.assertEqual(report['missing_from_active_list'], [])
            self.assertTrue(report['published']['stale'])


if __name__ == '__main__':
    unittest.main()


class FlagSourceContractTests(unittest.TestCase):
    """Every published flag row must carry an allow-listed official source.

    The Flagged for Review page renders each ``flags.json`` entry as a table row,
    and ``scripts.audit_rows`` fails a build audit when a row has neither an
    official link nor an unverified marker. A self-referential finding (only this
    project's github.io URLs) tripped exactly that in CI run 39905107686, so the
    contract is pinned here against the real registry.
    """

    def test_every_session_flag_links_an_official_source(self):
        from scripts.audit_rows import is_official
        flags = json.loads((Path(__file__).resolve().parents[1] / 'data' / 'research'
                            / '69438ad1' / 'flags.json').read_text())
        self.assertGreaterEqual(len(flags), 5)
        for flag in flags:
            official = [u for u in flag['source_urls'] if is_official(u)]
            self.assertTrue(official, f"{flag['id']} has no allow-listed official source: {flag['source_urls']}")
