"""Fail closed on unsupported contrarian eligibility; retain sourced estimates."""
import unittest
try:
    from tests.test_strategy import NOW, inputs, match
except ImportError:  # direct module runs with tests/ on sys.path
    from test_strategy import NOW, inputs, match
from scripts.build_strategy import plan


class StrategySafety(unittest.TestCase):
    def sample(self):
        return inputs([match('safety', 'A', 'B', [0.65, 0.35], tier='s')])

    def blocked(self, data):
        result = plan(data, NOW)
        row = result['rows'][0]
        self.assertFalse(row['eligible'])
        self.assertFalse(row['swap'])
        self.assertEqual(row['default'], row['fav'])
        self.assertEqual(row['p'], [0.65, 0.35])
        self.assertTrue(row['blockers'])
        return result

    def test_good_bound_inventory_allows_swap(self):
        self.assertTrue(plan(self.sample(), NOW)['rows'][0]['swap'])

    def test_incomplete_inventory(self):
        data = self.sample()
        data['latest']['coverage_complete'] = False
        self.assertTrue(self.blocked(data)['summary']['stale'])

    def test_stale_missing_and_future_inventory(self):
        for observed in ('2026-10-15T23:59:59Z', None, 'bad', '2026-10-16T10:00:00Z'):
            with self.subTest(observed=observed):
                data = self.sample()
                data['latest']['inventory_observed_at'] = observed
                data['orig']['source_snapshot_at'] = observed
                self.assertTrue(self.blocked(data)['summary']['stale'])

    def test_unbound_lines(self):
        for observed in (None, '2026-10-16T08:29:00Z'):
            data = self.sample()
            data['orig']['source_snapshot_at'] = observed
            self.assertTrue(self.blocked(data)['summary']['stale'])

    def test_missing_or_impossible_deadlines(self):
        for changes in ({'locks_at': None}, {'starts_at': None}, {'locks_at': '2026-10-16T13:00:00Z'},
                        {'availability': 'unknown_lock'}, {'availability': 'locked'}):
            with self.subTest(changes=changes):
                data = self.sample()
                data['orig']['matches'][0].update(changes)
                self.blocked(data)
