"""Regression and verification suite for session arena-51eab39f."""
from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import audit_rows, build

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / 'data' / 'research' / '51eab39f'
verifier = importlib.import_module('scripts.51eab39f_verify')


class Session51eab39fVerificationTests(unittest.TestCase):
    def test_verify_all_dossiers_and_math_replay(self) -> None:
        summary = verifier.verify_all(ROOT)
        self.assertEqual(summary['session'], 'arena-51eab39f')
        self.assertEqual(summary['live_fixtures'], 19)
        self.assertEqual(summary['non_featured_fixtures'], 13)
        self.assertEqual(summary['flags'], 6)
        self.assertGreaterEqual(summary['ci_replayed'], 17)
        self.assertGreaterEqual(summary['root_replayed'], 1)

    def test_live_coverage_selected_and_renders_zero_missing_and_zero_percent(self) -> None:
        cov = json.loads((RESEARCH_DIR / 'live-coverage.json').read_text(encoding='utf-8'))
        self.assertTrue((RESEARCH_DIR / 'live-coverage.md').is_file())
        self.assertEqual(cov['environment'], 'arena-sandbox')

        selected = build.load_live_coverage(ROOT / 'data')
        self.assertIsNotNone(selected)
        self.assertGreaterEqual(selected['observed_at'], cov['observed_at'])

        # 1) Empty / older snapshot: all 19 carried cards appear under #live-coverage-rotated, 0 missing, zero '%'
        empty_html = build.live_coverage_gaps(
            {'matches': [], 'complete_picks': {'matches': []}, '_live_coverage': cov}, ''
        )
        self.assertIn('0 missing at that observation', empty_html)
        self.assertIn('id="live-coverage-rotated"', empty_html)
        self.assertNotIn('%', empty_html)
        for row in cov['live_fixtures']:
            self.assertIn(row['hotspawn_url'], empty_html)
            self.assertIn(row['hltv_url'], empty_html)

        # 2) Matching 19-card complete snapshot: 0 missing and no rotated note needed
        matched_rows = [
            {'id': row['id'], 'teams': [{'name': row['teams'][0]}, {'name': row['teams'][1]}]}
            for row in cov['live_fixtures']
        ]
        matched_html = build.live_coverage_gaps(
            {'matches': matched_rows, 'complete_picks': {'matches': matched_rows}, '_live_coverage': cov}, ''
        )
        self.assertIn('0 missing at that observation', matched_html)
        self.assertNotIn('id="live-coverage-rotated"', matched_html)
        self.assertNotIn('%', matched_html)

    def test_non_featured_research_enforces_hltv_first_and_excludes_hotspawn_crowd(self) -> None:
        doc = json.loads((RESEARCH_DIR / 'non-featured-research.json').read_text(encoding='utf-8'))
        self.assertTrue((RESEARCH_DIR / 'non-featured-research.md').is_file())
        self.assertTrue(doc['hotspawn_crowd_excluded'])
        self.assertEqual(len(doc['fixtures']), 13)
        for fx in doc['fixtures']:
            self.assertTrue(fx['hltv_match_url'].startswith('https://www.hltv.org/matches/'))
            self.assertTrue(audit_rows.is_official(fx['hltv_match_url']))
            self.assertTrue(audit_rows.is_official(fx['hotspawn_url']))
            self.assertTrue(fx['external_lines_checked'])
            for chk in fx['external_lines_checked']:
                self.assertTrue(audit_rows.is_official(chk['url']), chk['url'])

    def test_flags_render_with_zero_audit_violations(self) -> None:
        flags = json.loads((RESEARCH_DIR / 'flags.json').read_text(encoding='utf-8'))
        self.assertEqual([f['id'] for f in flags], [f'51eab39f-00{i}' for i in range(1, 7)])
        flags_html = build.flags_table(flags)
        for i in range(1, 7):
            self.assertIn(f'id="flag-51eab39f-00{i}"', flags_html)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site' / 'review'
            out.mkdir(parents=True)
            (out / 'index.html').write_text(
                f'<!doctype html><html><body>{flags_html}</body></html>',
                encoding='utf-8',
            )
            report = audit_rows.audit_site(Path(tmp) / 'site')
            self.assertEqual(report['totals']['violation'], 0, report['pages'])
            self.assertEqual(report['totals']['ok'], 6)


if __name__ == '__main__':
    unittest.main()
