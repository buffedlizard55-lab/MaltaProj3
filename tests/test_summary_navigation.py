"""Presentation regressions: retained evidence is not fresh coverage.

Use dated repository fixtures for rendering only. No synthetic probability is
written to the production feed and no HTTP success is assumed to verify inventory.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from scripts.build import coverage, summary

ROOT = Path(__file__).resolve().parents[1]


class SummaryNavigation(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/latest.json').read_text())
        self.data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
        self.data['_twc_day4'] = {
            'matches': [{'analysis': {'method': 'market'}}],
            'not_in_hotspawn_snapshot': [], 'lines': {},
        }

    def render(self, prefix='./'):
        # Other independently tested editorial sections are outside this scope.
        with patch('scripts.build.contrarian_review', return_value=''), \
             patch('scripts.build.contrarian_briefing', return_value=''):
            return BeautifulSoup(summary(self.data, prefix), 'html.parser')

    def test_next_matches_all_picks_link_uses_complete_feed(self):
        for prefix in ('./', '../'):
            with self.subTest(prefix=prefix):
                link = self.render(prefix).select_one('#next-matches-section .section-heading a')
                self.assertEqual(link['href'], prefix + 'origination/#picks')
                self.assertIn('All match picks', link.get_text())

    def test_degraded_day4_does_not_claim_reconciliation(self):
        self.data['coverage_complete'] = False
        text = self.render().select_one('[aria-label="TWC Day 4 coverage"]').get_text(' ', strip=True)
        self.assertIn('retained Hotspawn snapshot', text)
        self.assertIn('current coverage is unverified', text)
        self.assertNotIn('in the reconciled Hotspawn inventory', text)

    def test_successful_day4_calls_reconciliation_a_snapshot_not_live_coverage(self):
        self.data['coverage_complete'] = True
        text = self.render().select_one('[aria-label="TWC Day 4 coverage"]').get_text(' ', strip=True)
        self.assertIn('last reconciled Hotspawn snapshot', text)
        self.assertNotIn('current coverage is unverified', text)

    def test_equal_estimate_explains_why_pick_and_probability_counts_differ(self):
        counts = self.data['complete_picks']['counts']
        counts['with_pick'] = counts['resolved'] - 1
        text = self.render().select_one('[aria-label="Complete pick coverage"]').get_text(' ', strip=True)
        self.assertIn(f'{counts["resolved"]} with probabilities', text)
        self.assertIn('1 equal estimate(s) have no directional pick', text)
        self.assertIn(f'{counts["unresolved"]} unresolved', text)

    def test_preview_is_not_described_as_featured_only(self):
        text = self.render().get_text(' ', strip=True)
        self.assertNotIn('metrics and next-match preview below describe the original featured method only', text)
        self.assertIn('next-match preview uses the same selected estimates as the complete list', text)

    def test_presentation_changes_do_not_mutate_source_facts_or_probabilities(self):
        original = copy.deepcopy(self.data)
        self.render()
        coverage(self.data, '../')
        self.assertEqual(self.data, original)

    def test_coverage_ledger_explicitly_dates_retained_reconciliation(self):
        self.data['coverage_complete'] = False
        soup = BeautifulSoup(coverage(self.data, '../'), 'html.parser')
        ledger = next(row for row in soup.select('tr') if 'Fixture identity reconciliation' in row.get_text())
        text = ledger.get_text(' ', strip=True)
        self.assertIn('Retained snapshot only', text)
        self.assertIn('current coverage is unverified', text)
        self.assertIn('datetime="' + self.data['inventory_observed_at'] + '"', str(ledger))
        self.assertIsNotNone(ledger.select_one('a[href="https://play.hotspawn.com/cs2-pickems"]'))

    def test_coverage_lists_both_actual_crons_and_workflow_source(self):
        workflow = (ROOT / '.github/workflows/pages.yml').read_text()
        self.assertIn("cron: '17 */4 * * *'", workflow)
        self.assertIn("cron: '47 2-22/4 * * *'", workflow)
        soup = BeautifulSoup(coverage(self.data, '../'), 'html.parser')
        text = soup.get_text(' ', strip=True)
        self.assertIn('02:47, 06:47, 10:47, 14:47, 18:47, 22:47 UTC', text)
        self.assertIn('may delay or drop runs', text)
        self.assertIsNotNone(soup.select_one('a[href="https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/.github/workflows/pages.yml"]'))


if __name__ == '__main__':
    unittest.main()
