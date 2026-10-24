"""Phone-first contracts for the canonical complete-picks page (arena-be27c3f6).

These tests render data; they never alter a fixture, probability, pick or alias.
"""
from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import audit_be27c3f6_published, audit_rows, build_origination

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc)


class CompletePicksPhoneStructureTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/origination.json').read_text(encoding='utf-8'))

    def render(self, data=None):
        return BeautifulSoup(build_origination.page(data or self.data, now=NOW), 'html.parser')

    def test_every_overview_row_is_searchable_and_has_an_official_source(self):
        soup = self.render()
        rows = soup.select('.picks-table tbody tr')
        self.assertEqual(len(rows), len(self.data['matches']))
        by_id = {str(m['id']): m for m in self.data['matches']}
        for row in rows:
            match = by_id[row['id'].removeprefix('row-')]
            expected = ' '.join([t['name'] for t in match['teams']] + [match.get('competition') or '']).lower()
            self.assertEqual(row['data-search'], expected)
            self.assertTrue(any(a.get('href', '').startswith('https://') for a in row.select('a')), row['id'])
            self.assertNotIn('hidden', row.attrs, 'No-JS markup must show the complete list')
        audit = audit_rows.audit_html(str(soup), 'origination/index.html')
        self.assertEqual(audit['violation'], 0, audit['violations'])

    def test_search_filter_and_status_are_labelled_and_composable(self):
        soup = self.render()
        query = soup.select_one('#picks-query')
        self.assertIsNotNone(query)
        self.assertEqual(query['type'], 'search')
        self.assertEqual(query['aria-controls'], 'picks-table-body')
        self.assertEqual(query['aria-describedby'], 'picks-filter-status')
        self.assertEqual(soup.select_one('label[for="picks-query"]').get_text(strip=True), 'Find a team or tournament')
        self.assertIsNotNone(soup.select_one('tbody#picks-table-body'))
        self.assertEqual(soup.select_one('[data-picks-status]').get_text(strip=True), f"Showing all {len(self.data['matches'])} matches.")
        self.assertEqual(len(soup.select('.filter-btn[aria-controls="picks-table-body"]')), 4)
        self.assertTrue(soup.select_one('[data-clear-picks]').has_attr('hidden'))
        self.assertTrue(soup.select_one('[data-picks-empty]').has_attr('hidden'))

    def test_unresolved_and_even_rows_jump_to_their_exact_limitations(self):
        data = copy.deepcopy(self.data)
        blank, even = data['matches'][:2]
        blank['origination'] = None
        blank['pick_index'] = None
        even['origination']['probabilities'] = [0.5, 0.5]
        even['origination']['fair_decimal'] = [2.0, 2.0]
        even['pick_index'] = None
        data['counts']['unresolved'] = 1
        data['counts']['with_pick'] = len(data['matches']) - 2
        soup = self.render(data)
        for match, prefix, text in ((blank, 'unresolved', 'Why unresolved'), (even, 'even', 'Why no side')):
            row = soup.select_one(f'#row-{match["id"]}')
            link = row.select_one('a.limitation-link')
            self.assertIn(text, link.get_text(strip=True))
            self.assertEqual(link['href'], f'#{prefix}-{match["id"]}')
            self.assertIsNotNone(soup.select_one(f'#{prefix}-{match["id"]}'))
        ids = [node['id'] for node in soup.select('[id]')]
        self.assertEqual(len(ids), len(set(ids)))

    def test_plain_language_navigation_and_evidence_heading(self):
        soup = self.render()
        self.assertIn('Complete CS2 match picks', soup.title.get_text())
        self.assertIn('complete match picks', soup.select_one('.top .brand span').get_text())
        self.assertEqual(len(soup.select('.quick a')), 8)
        self.assertNotIn('📋', soup.select_one('.quick').get_text())
        self.assertIsNotNone(soup.select_one('.hero-method summary'))
        mobile = soup.select('.mobile-quick a')
        self.assertEqual([a.get_text(strip=True) for a in mobile], ['Summary', 'Picks', 'Unresolved', 'Review'])
        self.assertEqual([a['href'] for a in mobile], ['../', '#picks', '#unresolved', '../review/'])
        heading = soup.select_one('#evidence-cards')
        self.assertIn('Full evidence', heading.get_text())
        self.assertIn('repeat the same fixtures', heading.get_text())

    def test_overview_pick_labels_start_in_the_same_safety_state_as_cards(self):
        current = self.render()
        current_picks = current.select('[data-overview-pick]')
        self.assertTrue(current_picks)
        for pick in current_picks:
            row = pick.find_parent('tr')
            card = current.select_one('#match-' + row['id'].removeprefix('row-'))
            self.assertEqual(row.get('class', []) == ['is-historical'], card['data-safety-status'] != 'current')
            self.assertEqual(pick.select_one('[data-overview-current]').has_attr('hidden'), card['data-safety-status'] != 'current')
            self.assertEqual(pick.select_one('[data-overview-historical]').has_attr('hidden'), card['data-safety-status'] == 'current')

        historical = BeautifulSoup(build_origination.page(self.data, now=datetime(2027, 1, 1, tzinfo=timezone.utc)), 'html.parser')
        for pick in historical.select('[data-overview-pick]'):
            self.assertTrue(pick.select_one('[data-overview-current]').has_attr('hidden'))
            self.assertFalse(pick.select_one('[data-overview-historical]').has_attr('hidden'))
            self.assertIn('is-historical', pick.find_parent('tr').get('class', []))

    def test_published_audit_accepts_only_an_exact_documented_money_upgrade(self):
        row = BeautifulSoup('<tr><td>Money-backed line · Originated market line</td></tr>', 'html.parser').tr
        note = ('Upgraded from the featured Valve-model estimate (73.6% / 26.4%): '
                'the alias-aware research found a verified money-backed line, which replaces the uncalibrated model.')
        card = BeautifulSoup(f'<article><p class="alias-note">{note}</p></article>', 'html.parser').article
        analysis = {'method': 'model', 'probabilities': [0.7359068, 0.2640932]}
        compare = audit_be27c3f6_published.compare_featured
        self.assertEqual(compare(row, card, [54.5, 45.5], analysis), 'documented-money-line-upgrade')
        self.assertEqual(compare(row, card, [73.6, 26.4], analysis), 'matched-snapshot-analysis')

        wrong_old_pair = BeautifulSoup('<article><p class="alias-note">Upgraded from the featured Valve-model estimate (60.0% / 40.0%): found a verified money-backed line, which replaces the uncalibrated model.</p></article>', 'html.parser').article
        self.assertEqual(compare(row, wrong_old_pair, [54.5, 45.5], analysis), 'mismatch')
        unexplained = BeautifulSoup('<article><p class="alias-note">A different estimate is shown.</p></article>', 'html.parser').article
        self.assertEqual(compare(row, unexplained, [54.5, 45.5], analysis), 'mismatch')
        unlabelled_row = BeautifulSoup('<tr><td>Research model</td></tr>', 'html.parser').tr
        self.assertEqual(compare(unlabelled_row, card, [54.5, 45.5], analysis), 'mismatch')

    def test_rendering_does_not_mutate_pick_data(self):
        data = copy.deepcopy(self.data)
        before = json.dumps(data, sort_keys=True, ensure_ascii=False)
        build_origination.page(data, now=NOW)
        self.assertEqual(json.dumps(data, sort_keys=True, ensure_ascii=False), before)


if __name__ == '__main__':
    unittest.main()
