from __future__ import annotations

import unittest

from scripts.cd37caa0_reconcile import by_id, markdown, reconcile


def inventory_row(fixture_id='1', name='Alpha', start='2026-10-24T10:00:00Z'):
    return {
        'id': fixture_id,
        'teams': [{'name': name}, {'name': 'Beta'}],
        'competition': 'Official event',
        'starts_at': start,
        'availability': 'upcoming',
        'source_url': f'https://play.hotspawn.com/match/{fixture_id}',
        'source_api': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2',
        'analysis': {'method': 'model'},
    }


def researched_row(fixture_id='1', name='Alpha', start='2026-10-24T10:00:00Z'):
    return {
        'id': fixture_id,
        'teams': [{'name': name}, {'name': 'Beta'}],
        'starts_at': start,
        'availability': 'upcoming',
        'origination': {
            'method': 'model',
            'probabilities': [0.6, 0.4],
            'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
        },
        'pick_index': 0,
        'limitations': ['Uncalibrated model.'],
        'research': [{'stage': 'HLTV research', 'source_url': 'https://www.hltv.org/matches/1/example'}],
    }


def document(rows, generated='2026-10-24T09:00:00Z'):
    return {'generated_at': generated, 'matches': rows, 'requests': []}


class ReconciliationTests(unittest.TestCase):
    def test_full_candidate_and_inventory_delta(self):
        latest = document([inventory_row('1'), inventory_row('2', 'Gamma')])
        researched = document([researched_row('1'), researched_row('2', 'Gamma')])
        old = document([inventory_row('1'), inventory_row('3', 'Old')], '2026-10-23T09:00:00Z')
        report = reconcile(latest, researched, old)
        self.assertEqual(report['counts']['candidate_active'], 2)
        self.assertEqual(report['counts']['candidate_resolved'], 2)
        self.assertEqual(report['new_ids'], ['2'])
        self.assertEqual(report['removed_ids'], ['3'])
        self.assertEqual(report['row_problems'], {})
        row = next(row for row in report['fixtures'] if row['id'] == '2')
        self.assertEqual(row['pick_team'], 'Gamma')
        self.assertTrue(row['new_since_published'])
        self.assertEqual(row['hltv_research_url'], 'https://www.hltv.org/matches/1/example')

    def test_hotspawn_is_not_an_independent_probability_source(self):
        researched = researched_row()
        researched['origination']['source_url'] = 'https://play.hotspawn.com/match/1'
        report = reconcile(document([inventory_row()]), document([researched]), document([]))
        self.assertIn('Hotspawn cannot be the independent probability source', report['row_problems']['1'])

    def test_tie_and_non_normalized_probabilities_are_rejected(self):
        researched = researched_row()
        researched['origination']['probabilities'] = [0.7, 0.7]
        report = reconcile(document([inventory_row()]), document([researched]), document([]))
        self.assertIn('probabilities do not sum to one', report['row_problems']['1'])
        self.assertIn('published pick is not strictly directional', report['row_problems']['1'])

    def test_unresolved_row_stays_visible_with_limitations(self):
        researched = researched_row()
        researched['origination'] = None
        researched['pick_index'] = None
        researched['limitations'] = ['No two-sided line verified.']
        report = reconcile(document([inventory_row()]), document([researched]), document([]))
        self.assertEqual(report['unresolved_ids'], ['1'])
        self.assertIn('unresolved: no directional origination pick', report['row_problems']['1'])
        text = markdown(report)
        self.assertIn('UNRESOLVED', text)
        self.assertIn('No two-sided line verified.', text)

    def test_active_inventory_and_origination_ids_must_pair(self):
        with self.assertRaisesRegex(ValueError, 'active-id mismatch'):
            reconcile(document([inventory_row('1'), inventory_row('2')]),
                      document([researched_row('1')]), document([]))

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate fixture ids'):
            by_id([inventory_row('1'), inventory_row('1')], 'test')

    def test_past_rows_do_not_count_as_active(self):
        past = inventory_row('2')
        past['availability'] = 'past'
        report = reconcile(document([inventory_row('1'), past]),
                           document([researched_row('1')]), document([past]))
        self.assertEqual(report['counts']['candidate_active'], 1)
        self.assertEqual(report['counts']['published_active'], 0)


if __name__ == '__main__':
    unittest.main()
