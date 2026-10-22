"""Session arena-7e8bed83 — every-match coverage invariant.

Every active Hotspawn CS2 fixture must carry either a source-linked
probability + pick (or an even, no-side estimate) or an explicit unresolved
entry with a research trail and limitations. These tests pin that contract
on the checked-in fixture and on synthetic regressions that must fail.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.coverage_audit import audit_complete_picks

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / 'data/origination.json').read_text())


class CoverageAudit(unittest.TestCase):
    def test_checked_in_fixture_has_full_coverage(self):
        payload = fixture()
        self.assertEqual(audit_complete_picks(payload), [])
        counts = payload['counts']
        self.assertEqual(counts['resolved'] + counts['unresolved'], counts['active'])

    def test_every_resolved_pick_is_the_argmax_with_a_source(self):
        for row in fixture()['matches']:
            if not row.get('origination'):
                continue
            probs = row['origination']['probabilities']
            self.assertTrue(row['origination']['source_url'].startswith('https://'))
            if probs[0] != probs[1]:
                self.assertEqual(row['pick_index'], 0 if probs[0] > probs[1] else 1)

    def test_dropped_pick_is_caught(self):
        payload = fixture()
        row = next(r for r in payload['matches'] if r.get('origination'))
        row['pick_index'] = 1 - row['pick_index'] if row['origination']['probabilities'][0] != row['origination']['probabilities'][1] else None
        if row['pick_index'] is not None:
            self.assertTrue(any('not the higher-probability' in p for p in audit_complete_picks(payload)))

    def test_silent_blank_is_caught(self):
        payload = fixture()
        row = next(r for r in payload['matches'] if r.get('origination'))
        row['origination'] = None
        row['research'] = []
        row['limitations'] = []
        problems = audit_complete_picks(payload)
        self.assertTrue(any('research trail' in p for p in problems))
        self.assertTrue(any('counts.unresolved' in p for p in problems))

    def test_even_estimate_names_no_side(self):
        payload = fixture()
        row = next(r for r in payload['matches'] if r.get('origination'))
        row['origination']['probabilities'] = [0.5, 0.5]
        row['pick_index'] = 0
        self.assertTrue(any('exactly even' in p for p in audit_complete_picks(payload)))

    def test_hotspawn_votes_can_never_be_an_input(self):
        payload = fixture()
        payload['policy']['hotspawn_votes_used'] = True
        self.assertTrue(any('hotspawn_votes_used' in p for p in audit_complete_picks(payload)))

    def test_probabilities_must_sum_to_one(self):
        payload = copy.deepcopy(fixture())
        row = next(r for r in payload['matches'] if r.get('origination'))
        row['origination']['probabilities'] = [0.9, 0.9]
        self.assertTrue(any('sum' in p for p in audit_complete_picks(payload)))


if __name__ == '__main__':
    unittest.main()
