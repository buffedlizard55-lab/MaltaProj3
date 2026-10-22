"""Tests for the read-only A56 exported-row audit.

The checked-in feeds are replay fixtures, not represented as current live data.
A temporary copy is mutated in the negative test; canonical match records and
probabilities are never edited.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.a56f3474_live_audit import audit

ROOT = Path(__file__).resolve().parents[1]


class ExportedRowAuditTests(unittest.TestCase):
    def test_checked_in_replay_snapshot_has_complete_row_contracts(self):
        report = audit(ROOT / 'data')
        self.assertEqual(report['summary']['violations'], 0, report['violations'])
        self.assertEqual(report['summary']['rows'], report['count_checks']['active']['recomputed'])
        self.assertEqual(
            report['summary']['directional'] + report['summary']['no_side'] + report['summary']['unresolved'],
            report['summary']['rows'],
        )

    def test_pick_direction_mismatch_is_detected_on_a_temporary_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'data'
            source.mkdir()
            for name in ('latest.json', 'origination.json', 'sources.json'):
                shutil.copy2(ROOT / 'data' / name, source / name)
            path = source / 'origination.json'
            feed = json.loads(path.read_text())
            row = next(row for row in feed['matches'] if row.get('origination') and row.get('pick_index') is not None)
            row['pick_index'] = 1 - row['pick_index']
            path.write_text(json.dumps(feed) + '\n')
            report = audit(source)
            self.assertGreater(report['summary']['violations'], 0)
            self.assertIn('pick-direction', {item['code'] for item in report['violations']})


if __name__ == '__main__':
    unittest.main()
