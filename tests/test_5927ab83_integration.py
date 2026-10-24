"""Final-integration regressions for arena-5927ab83.

These cover interactions between merged sessions, not new pick or pricing
behaviour. All source values come from the checked-in dated evidence.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import tempfile
import unittest

from scripts.eea4c104_audit import parse_origination_rows


integration_audit = importlib.import_module('scripts.5927ab83_integration_audit')
ROOT = Path(__file__).resolve().parent.parent


class CombinedOverviewAudit(unittest.TestCase):
    def parse_cells(self, pick_html: str):
        html = f'''<html><body><table><tbody><tr id="row-fixture-1">
        <td>Alpha: 60.0% Bravo: 40.0%</td>
        <td>{pick_html}<small>60.0% · fair 1.667</small></td>
        <td>Money-backed line</td></tr></tbody></table></body></html>'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'index.html'
            path.write_text(html, encoding='utf-8')
            (row,) = parse_origination_rows(path)
        return row

    def test_both_current_and_hidden_historical_markers_do_not_become_the_team(self):
        row = self.parse_cells(
            '<strong><span>✓ </span><span hidden>Snapshot: </span>Alpha</strong>')
        self.assertEqual(row['pick'], 'Alpha')
        self.assertEqual(row['pick_pct'], 60.0)
        self.assertEqual(row['fair_decimal'], 1.667)

    def test_existing_single_snapshot_and_snapshot_lean_markers_still_parse(self):
        for marker in ('Snapshot: ', 'Snapshot lean: '):
            with self.subTest(marker=marker):
                row = self.parse_cells(f'<strong>{marker}Alpha</strong>')
                self.assertEqual(row['pick'], 'Alpha')


class DatedDossierIntegration(unittest.TestCase):
    def test_complete_picks_dossier_replays_without_cross_session_drift(self):
        report = integration_audit.audit(ROOT / 'data/research/be019782')
        self.assertTrue(report['ok'])
        self.assertEqual(report['counts']['official_inventory_rows'], 25)
        self.assertEqual(report['counts']['normalized_directional_estimates'], 25)
        self.assertEqual(report['counts']['model_only_targets'], 10)
        self.assertEqual(report['counts']['hltv_first_research_rows'], 10)
        self.assertEqual(report['counts']['replayed_rows'], 25)
        self.assertEqual(report['counts']['row_source_violations'], 0)
        self.assertEqual(report['methods'], {'bookmaker': 3, 'market': 12, 'model': 10})


if __name__ == '__main__':
    unittest.main()
