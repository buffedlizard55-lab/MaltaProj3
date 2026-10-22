"""Regression and end-to-end verification tests for session arena-ca4d2a02."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import audit_rows, build, ca4d2a02_verify, coverage_audit

REPO_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = REPO_ROOT / 'data' / 'research' / 'ca4d2a02'


class TestCA4D2A02Verification(unittest.TestCase):
    """End-to-end verification of canonical feeds, built HTML, mobile summary, and flags."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.site_dir = Path(cls._tmp.name) / 'site'
        build.build(REPO_ROOT / 'data', cls.site_dir)
        cls.report = ca4d2a02_verify.run_full_verification(REPO_ROOT, cls.site_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_full_verification_passes_with_zero_errors(self) -> None:
        self.assertEqual(self.report['status'], 'pass', self.report['errors'])
        self.assertEqual(self.report['total_errors'], 0)
        self.assertEqual(self.report['canonical']['latest_rows_checked'], 80)
        self.assertEqual(self.report['canonical']['origination_rows_checked'], 17)
        self.assertEqual(self.report['site']['row_audit_counts']['violation'], 0)
        self.assertEqual(self.report['site']['glance_rows_checked'], 17)
        self.assertEqual(self.report['site']['expected_flags_verified'], 6)

    def test_dated_research_artifacts_schema_and_official_links(self) -> None:
        flags = json.loads((RESEARCH_DIR / 'flags.json').read_text(encoding='utf-8'))
        self.assertIsInstance(flags, list)
        self.assertEqual(len(flags), 6)
        for flag in flags:
            self.assertTrue(str(flag['id']).startswith('ca4d2a02-'))
            self.assertIn(flag['severity'], {'warning', 'notice'})
            self.assertTrue(flag['title'])
            self.assertTrue(flag['detail'])
            urls = flag['source_urls']
            self.assertTrue(urls, f'flag {flag["id"]} missing source_urls')
            for url in urls:
                self.assertTrue(url.startswith('https://'), url)
                self.assertTrue(audit_rows.is_official(url), f'non-official URL on {flag["id"]}: {url}')

        live_audit = json.loads((RESEARCH_DIR / 'live-inventory-audit.json').read_text(encoding='utf-8'))
        self.assertEqual(live_audit['inventory_counts']['inventory'], 107)
        self.assertEqual(live_audit['origination_counts']['active'], 46)
        self.assertEqual(live_audit['origination_counts']['with_pick'], 45)
        self.assertFalse(live_audit['policy']['hotspawn_votes_used'])
        self.assertFalse(live_audit['policy']['fan_votes_used'])
        self.assertEqual(len(live_audit['active_matches']), 46)
        for row in live_audit['active_matches']:
            self.assertTrue(audit_rows.is_official(row['hotspawn_url']), row['id'])
            self.assertTrue(audit_rows.is_official(row['official_source_url']), row['id'])
            self.assertAlmostEqual(sum(row['probabilities']), 1.0, places=5)

        low_tier = json.loads((RESEARCH_DIR / 'low-tier-line-research.json').read_text(encoding='utf-8'))
        self.assertFalse(low_tier['methodology']['hotspawn_votes_used'])
        self.assertFalse(low_tier['methodology']['hltv_fan_votes_used'])
        self.assertEqual(len(low_tier['featured_unresolved_live_fixtures']), 11)
        self.assertGreaterEqual(len(low_tier['recommended_competition_scoped_aliases_for_owner']), 5)

        repo_audit = json.loads((RESEARCH_DIR / 'repo-line-audit.json').read_text(encoding='utf-8'))
        self.assertEqual(repo_audit['status'], 'pass')
        self.assertEqual(repo_audit['total_errors'], 0)

    def test_review_page_renders_all_ca4d2a02_flags_with_official_links(self) -> None:
        review_html = (self.site_dir / 'review' / 'index.html').read_text(encoding='utf-8')
        soup = BeautifulSoup(review_html, 'html.parser')
        flags = json.loads((RESEARCH_DIR / 'flags.json').read_text(encoding='utf-8'))
        for flag in flags:
            fid = flag['id']
            self.assertIn(fid, review_html)
            self.assertIn(flag['title'], soup.get_text())

    def test_mobile_executive_summary_links_both_probs_and_unresolved_section(self) -> None:
        index_html = (self.site_dir / 'index.html').read_text(encoding='utf-8')
        soup = BeautifulSoup(index_html, 'html.parser')

        banner = soup.select_one('section.exec-banner')
        self.assertIsNotNone(banner)
        hrefs = {(a.get('href') or '').removeprefix('./') for a in banner.find_all('a', href=True)}
        self.assertIn('origination/#picks', hrefs)
        self.assertIn('picks/', hrefs)
        self.assertIn('origination/#unresolved', hrefs)

        glance_rows = soup.select('#picks-at-a-glance .glance-row')
        self.assertEqual(len(glance_rows), 17)
        for grow in glance_rows:
            self.assertIsNotNone(grow.select_one('.glance-prob'))
            self.assertIsNotNone(grow.select_one('.glance-other'))
            self.assertIsNotNone(grow.select_one('.glance-pick-label'))

        self.assertIsNotNone(soup.find(id='unresolved'))

    def test_verifier_rejects_unconfirmed_fill_and_crowd_vote_leakage(self) -> None:
        orig = json.loads((REPO_ROOT / 'data' / 'origination.json').read_text(encoding='utf-8'))
        bad_orig = copy.deepcopy(orig)
        bad_orig['policy']['hotspawn_votes_used'] = True
        problems = coverage_audit.audit_complete_picks(bad_orig)
        self.assertTrue(any('hotspawn_votes_used' in p for p in problems))

        bad_tie = copy.deepcopy(orig)
        bad_tie['matches'][0]['origination']['probabilities'] = [0.5, 0.5]
        bad_tie['matches'][0]['pick_index'] = 0
        problems_tie = coverage_audit.audit_complete_picks(bad_tie)
        self.assertTrue(any('even estimate must not name a pick' in p for p in problems_tie))


if __name__ == '__main__':
    unittest.main()
