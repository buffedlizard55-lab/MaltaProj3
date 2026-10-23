"""Session arena-e7d7a410 — the live coverage audit must be strict and truthful.

These tests use synthetic snapshots only. They lock the three properties the
brief depends on: a row is covered only when it carries a pick, two valid
probabilities and an official https source; an even split is an explicit
team-0 default rather than a missing pick; and the audit never mutates the
snapshot it reads.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import e7d7a410_audit


def match(match_id, teams, *, method='model', probabilities=(0.7, 0.3), pick=0,
          availability='open', source='https://example.com/odds'):
    analysis = None
    if method is not None:
        analysis = {
            'method': method,
            'label': method,
            'probabilities': list(probabilities),
            'observed_at': '2026-10-23T05:00:00Z',
            'source': 'synthetic',
            'source_url': source,
        }
    return {
        'id': str(match_id),
        'teams': [{'id': str(index), 'name': name} for index, name in enumerate(teams)],
        'competition': 'Synthetic Cup',
        'starts_at': '2026-10-23T12:00:00Z',
        'availability': availability,
        'analysis': analysis,
        'pick_index': pick,
        'source_url': f'https://www.hotspawn.com/matches/x-{match_id}',
        'featured_method': None,
        'limitations': ['synthetic'],
    }


def original(match_id, teams, *, method='model', pick=0, probabilities=(0.6, 0.4),
             starts_at='2026-10-23T12:00:00Z', featured_method='market'):
    analysis = {
        'method': method,
        'probabilities': list(probabilities),
        'source_url': 'https://example.com/odds',
    }
    return {
        'id': str(match_id),
        'teams': [{'id': str(index), 'name': name} for index, name in enumerate(teams)],
        'availability': 'open',
        'starts_at': starts_at,
        'featured_method': featured_method,
        'source_url': 'https://www.hotspawn.com/matches/x',
        'origination': analysis,
        'pick_index': pick,
    }


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.data = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, matches, origination):
        (self.data / 'latest.json').write_text(json.dumps({
            'schema_version': 1, 'generated_at': '2026-10-23T05:00:00Z',
            'inventory_observed_at': '2026-10-23T05:00:00Z',
            'run_status': 'complete', 'coverage_complete': True,
            'counts': {'inventory': len(matches)}, 'matches': matches,
        }))
        (self.data / 'origination.json').write_text(json.dumps({
            'generated_at': '2026-10-23T05:00:01Z', 'counts': {'active': len(origination)},
            'matches': origination,
        }))

    def test_every_valid_row_is_covered_and_keeps_its_pick(self):
        self.write([match(1, ('A', 'B'), method='market', probabilities=(0.62, 0.38), pick=0)],
                   [original(1, ('A', 'B'), method='market', probabilities=(0.62, 0.38))])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['active_fixtures'], 1)
        self.assertEqual(report['summary']['covered'], 1)
        self.assertEqual(report['summary']['money_line_resolved'], 1)
        self.assertEqual(report['fixtures'][0]['pick'], 'A')
        self.assertEqual(report['unresolved'], [])

    def test_an_inverted_pick_is_a_defect(self):
        self.write([match(1, ('A', 'B'), probabilities=(0.2, 0.8), pick=0)],
                   [original(1, ('A', 'B'), probabilities=(0.2, 0.8))])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['covered'], 0)
        self.assertIn('pick points at the less likely team', report['unresolved'][0]['problems'])

    def test_missing_resolution_and_pick_are_reported_not_filled(self):
        self.write([match(1, ('A', 'B'), method=None, pick=None)],
                   [dict(original(1, ('A', 'B')), origination=None, pick_index=None)])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['without_pick'], 1)
        self.assertEqual(report['fixtures'][0]['probabilities'], None)
        self.assertEqual(report['unresolved'][0]['hotspawn_id'], '1')

    def test_probabilities_must_sum_to_one(self):
        self.write([match(1, ('A', 'B'), probabilities=(0.7, 0.7))],
                   [original(1, ('A', 'B'), probabilities=(0.7, 0.7))])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['covered'], 0)
        self.assertIn('not 1', report['unresolved'][0]['problems'][0])

    def test_an_even_line_defaults_to_team_zero_and_still_covers(self):
        self.write([match(1, ('A', 'B'), probabilities=(0.5, 0.5), pick=0)],
                   [original(1, ('A', 'B'), probabilities=(0.5, 0.5))])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['covered'], 1)
        self.assertEqual(report['fixtures'][0]['pick'], 'A')

    def test_model_only_rows_are_listed_as_no_betting_line(self):
        self.write([match(1, ('A', 'B'), method='model')],
                   [original(1, ('A', 'B'), method='model')])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['model_only_no_betting_line'], 1)
        self.assertEqual(report['no_betting_line'][0]['hotspawn_id'], '1')

    def test_past_fixtures_are_not_counted_as_active(self):
        self.write([match(1, ('A', 'B'), availability='past')], [])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['active_fixtures'], 0)

    def test_an_orphan_origination_row_is_a_defect(self):
        self.write([], [original(9, ('A', 'B'))])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['orphan_origination_rows'], 1)

    def test_audit_never_mutates_its_inputs(self):
        matches = [match(1, ('A', 'B'))]
        self.write(matches, [dict(original(1, ('A', 'B')), origination=None, pick_index=None)])
        before = (self.data / 'latest.json').read_bytes(), (self.data / 'origination.json').read_bytes()
        e7d7a410_audit.build_report(self.data)
        after = (self.data / 'latest.json').read_bytes(), (self.data / 'origination.json').read_bytes()
        self.assertEqual(before, after)


    def test_strict_rejects_an_empty_or_incomplete_snapshot(self):
        self.write([], [])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['active_fixtures'], 0)
        self.assertEqual(e7d7a410_audit.main(['--data', str(self.data), '--out', str(self.data), '--strict']), 1)

        self.write([match(1, ('A', 'B'), method='market')],
                   [original(1, ('A', 'B'), method='market')])
        latest = json.loads((self.data / 'latest.json').read_text())
        latest['coverage_complete'] = False
        (self.data / 'latest.json').write_text(json.dumps(latest))
        self.assertEqual(e7d7a410_audit.main(['--data', str(self.data), '--out', str(self.data), '--strict']), 1)

    def test_a_researched_fallback_in_the_complete_picks_feed_is_the_published_pick(self):
        # The featured analysis is blank, but the complete-picks feed resolved
        # the fixture with a researched fallback. That is a covered row; reading
        # only the featured block would have reported a false gap.
        self.write([match(1, ('A', 'B'), method=None, pick=None)],
                   [original(1, ('A', 'B'), method='bookmaker', pick=1, probabilities=(0.3, 0.7),
                             featured_method=None)])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['covered'], 1)
        self.assertEqual(report['fixtures'][0]['pick'], 'B')
        self.assertEqual(report['summary']['featured_blank_active'], 1)
        self.assertEqual(report['summary']['resolved_by_fallback'], 1)
        self.assertEqual(report['summary']['money_line_resolved'], 1)

    def test_a_fixture_missing_from_the_complete_picks_feed_is_uncovered(self):
        self.write([match(1, ('A', 'B'))], [])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['covered'], 0)
        self.assertIn('active fixture missing from the complete-picks feed',
                      report['unresolved'][0]['problems'])

    def test_identity_drift_between_the_two_feeds_is_a_defect(self):
        self.write([match(1, ('A', 'B'))], [dict(original(1, ('A', 'C')), origination=None, pick_index=None)])
        report = e7d7a410_audit.build_report(self.data)
        self.assertEqual(report['summary']['covered'], 0)
        self.assertIn('team names differ between the inventory and the complete-picks feed',
                      report['unresolved'][0]['problems'])

    def test_markdown_lists_every_row_with_its_source(self):
        self.write([match(1, ('A', 'B'), method='market')],
                   [original(1, ('A', 'B'), method='market')])
        text = e7d7a410_audit.markdown(e7d7a410_audit.build_report(self.data))
        self.assertIn('https://example.com/odds', text)
        self.assertIn('A vs B', text)
        self.assertIn('Every active fixture', text)


if __name__ == '__main__':
    unittest.main()
