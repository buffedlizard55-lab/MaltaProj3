import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from scripts.current_coverage_audit import reconcile


class CurrentCoverageAuditTests(unittest.TestCase):
    def setUp(self):
        self.latest = json.loads(Path('data/latest.json').read_text())
        self.complete = json.loads(Path('data/origination.json').read_text())
        self.now = datetime.fromisoformat(self.latest['generated_at'].replace('Z', '+00:00'))

    def audit(self):
        return reconcile(self.latest, self.complete, self.now)

    def test_saved_snapshot_has_all_ids(self):
        report = self.audit()
        self.assertEqual(report['missing_ids'], [])
        self.assertEqual(report['extra_ids'], [])
        self.assertTrue(report['snapshot_clocks_agree'])

    def test_complete_but_old_is_not_current(self):
        self.now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(any('eight hours' in x for x in self.audit()['findings']))

    def test_mixed_snapshots_are_not_verified(self):
        self.complete['source_generated_at'] = '2020-01-01T00:00:00Z'
        self.assertFalse(self.audit()['snapshot_clocks_agree'])

    def test_missing_fixture_visible(self):
        missing = self.complete['matches'].pop()['id']
        self.assertIn(str(missing), self.audit()['missing_ids'])

    def test_duplicate_visible(self):
        self.complete['matches'].append(copy.deepcopy(self.complete['matches'][0]))
        self.assertIn('Duplicate complete-pick IDs.', self.audit()['findings'])

    def test_only_no_money_rows_researched_and_no_mutation(self):
        before = copy.deepcopy(self.complete)
        report = self.audit()
        for row in report['no_line_fixtures']:
            self.assertNotIn(row['method'], ('market', 'bookmaker', 'consensus', 'reference'))
        self.assertEqual(before, self.complete)

    def test_unresolved_remains_blank(self):
        row = self.complete['matches'][0]
        row['origination'] = None
        row['pick_index'] = None
        gap = next(g for g in self.audit()['no_line_fixtures'] if g['id'] == row['id'])
        self.assertIsNone(gap['probabilities'])
        self.assertIsNone(gap['pick_index'])
        self.assertEqual(gap['state'], 'unresolved; probability blank')

    def test_bad_clock_is_flagged(self):
        self.latest['generated_at'] = 'invalid'
        self.assertIsNone(self.audit()['inventory_age_hours'])
        self.assertTrue(self.audit()['findings'])
