"""Unit & replay tests for session arena-81c1058a verification, review artifacts, and acceptance_audit fixes."""
from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import acceptance_audit, build, review_register

verify_mod = importlib.import_module('scripts.81c1058a_verify')
ROOT = Path(__file__).resolve().parents[1]


class Session81c1058aVerificationTests(unittest.TestCase):
    def test_checked_in_snapshots_pass_line_by_line_verification(self):
        res = verify_mod.verify_checked_in_snapshots(ROOT / 'data')
        self.assertEqual(res['errors'], [])
        self.assertEqual(
            res['counts']['effective_resolved_upcoming'],
            res['counts']['latest_upcoming'],
        )
        self.assertGreaterEqual(res['counts']['scoped_aliases_verified'], 69)

    def test_live_hotspawn_30_fixtures_and_deep_dive_order_books_replay_cleanly(self):
        line_doc, unres_doc, errors = verify_mod.verify_live_observations()
        self.assertEqual(errors, [])
        self.assertEqual(line_doc['counts']['scheduled_api_rows'], 82)
        self.assertEqual(line_doc['counts']['active_upcoming_rows'], 30)
        self.assertEqual(line_doc['counts']['with_directional_pick'], 30)
        self.assertEqual(line_doc['counts']['unresolved'], 0)
        self.assertEqual(
            line_doc['counts']['pricing_tiers'],
            {'consensus': 2, 'market': 16, 'bookmaker': 4, 'model': 8},
        )
        self.assertTrue(line_doc['hotspawn_crowd_share_never_used'])

        by_id = {x['fixture_id']: x for x in unres_doc['fixtures']}
        # 1079199 upgraded to tight Polymarket CLOB order book (spread 0.01 <= 0.12)
        self.assertTrue(by_id['1079199']['exchange_and_book_observations'][0]['accepted_as_money_line'])
        self.assertEqual(by_id['1079199']['exchange_and_book_observations'][0]['spread'], 0.01)
        # 1081605 verified on bo3.gg under 'los kogutos' (match 132217)
        self.assertEqual(
            by_id['1081605']['bo3_url'],
            'https://bo3.gg/matches/phantom-academy-vs-los-kogutos-23-10-2026',
        )
        # 1082858 Smarkets spread 0.185 > 0.15 rejected
        self.assertFalse(by_id['1082858']['exchange_and_book_observations'][0]['accepted_as_money_line'])
        self.assertGreater(by_id['1082858']['exchange_and_book_observations'][0]['spread'], 0.15)

    def test_acceptance_audit_passes_on_both_site_and_branch_root(self):
        root_report = acceptance_audit.audit(ROOT, ROOT)
        self.assertEqual(root_report['totals']['fail'], 0)
        mobile_check = next(c for c in root_report['checks'] if c['key'] == 'mobile')
        self.assertEqual(mobile_check['status'], 'pass')
        snap_check = next(c for c in root_report['checks'] if c['key'] == 'snapshot_consistency')
        self.assertIn(snap_check['status'], ('pass', 'info'))

    def test_built_site_publishes_81c1058a_flags_and_register(self):
        reg = json.loads((ROOT / 'data' / 'research' / '81c1058a' / 'repo-review.json').read_text())
        review_register.validate(reg)
        existing_site = ROOT / 'site'
        if (existing_site / 'review' / 'index.html').exists():
            site_res = verify_mod.verify_built_site(existing_site, ROOT)
            self.assertEqual(site_res['errors'], [])
            self.assertEqual(site_res['row_source_violations'], 0)
        else:
            with TemporaryDirectory() as tmp:
                out = Path(tmp) / 'site'
                build.build(ROOT / 'data', out)
                site_res = verify_mod.verify_built_site(out, ROOT)
                self.assertEqual(site_res['errors'], [])
                self.assertEqual(site_res['row_source_violations'], 0)


if __name__ == '__main__':
    unittest.main()
