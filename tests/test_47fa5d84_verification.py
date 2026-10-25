"""Regression tests for session arena-47fa5d84 verification and HLTV-first fallback audit.

All assertions against the mutable root `snapshot.json` are snapshot-independent
invariants (probabilities sum to 1, external https:// source URLs, no Hotspawn crowd
pick usage) so future scheduled `pages.yml` refreshes never break this test module.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts import session_47fa5d84_verify as verify
from scripts.domain import no_vig

ROOT = Path(__file__).resolve().parent.parent
AUDIT_JSON = ROOT / 'data' / 'research' / '47fa5d84' / 'verification-audit.json'
AUDIT_MD = ROOT / 'data' / 'research' / '47fa5d84' / 'verification-audit.md'


class Session47fa5d84VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit_doc = json.loads(AUDIT_JSON.read_text(encoding='utf-8'))
        cls.audit_md = AUDIT_MD.read_text(encoding='utf-8')
        cls.live_report = verify.build_report(ROOT)

    def test_audit_artifacts_exist_and_identify_session(self) -> None:
        self.assertTrue(AUDIT_JSON.exists())
        self.assertTrue(AUDIT_MD.exists())
        self.assertEqual(self.audit_doc['session_id'], 'arena-47fa5d84')
        self.assertFalse(self.audit_doc['policy']['hotspawn_crowd_pct_used_as_probability'])
        self.assertFalse(self.audit_doc['policy']['hltv_fan_poll_used_as_probability'])

    def test_mutable_root_snapshot_invariants_hold(self) -> None:
        snap_info = self.live_report['root_snapshot_verification']
        self.assertGreater(snap_info['total_inventory'], 0)
        self.assertEqual(
            snap_info['active_count'] + snap_info['archived_count'],
            snap_info['total_inventory'],
        )
        self.assertEqual(
            snap_info['featured_resolved_count'] + snap_info['featured_unresolved_count'],
            snap_info['active_count'],
        )
        for row in snap_info['active_matches']:
            if row['featured_status'] == 'resolved':
                probs = row['featured_probabilities']
                self.assertEqual(len(probs), 2)
                self.assertAlmostEqual(probs[0] + probs[1], 1.0, places=5)
                self.assertIn(row['featured_method'], {'market', 'bookmaker', 'consensus', 'reference', 'model'})
                self.assertTrue(row['source_url'].startswith('https://'))
                self.assertNotIn('hotspawn.com', row['source_url'])

    def test_live_17_open_fixtures_all_have_directional_picks_and_official_sources(self) -> None:
        live = self.live_report['live_origination_verification']
        self.assertEqual(live['official_api_total_records'], 78)
        self.assertEqual(live['open_fixture_count'], 17)
        self.assertEqual(live['archived_fixture_count'], 61)
        self.assertEqual(live['resolved_with_directional_pick'], 17)
        self.assertEqual(live['unresolved_count'], 0)
        self.assertEqual(
            live['no_line_model_only_ids'],
            ['1082858', '1082861', '1082792', '1082793'],
        )
        for m in live['matches']:
            probs = m['complete_probabilities']
            self.assertEqual(len(probs), 2, m['id'])
            self.assertAlmostEqual(probs[0] + probs[1], 1.0, places=5, msg=m['id'])
            self.assertIn(m['pick_index'], (0, 1), m['id'])
            self.assertEqual(m['pick_index'], 0 if probs[0] > probs[1] else 1, m['id'])
            self.assertTrue(m['hltv_url'].startswith('https://www.hltv.org/matches/'), m['id'])
            self.assertTrue(m['primary_source_url'].startswith('https://'), m['id'])
            self.assertNotIn('hotspawn.com', m['primary_source_url'], m['id'])

    def test_egamersworld_first_hand_verifications_and_sha256(self) -> None:
        egw_rows = {r['fixture_id']: r for r in self.audit_doc['egamersworld_first_hand_verification']}
        self.assertEqual(
            set(egw_rows),
            {'1082858', '1082859', '1082860', '1086696', '1086697', '1082861', '1082792', '1082793'},
        )
        for fid in ('1082858', '1082859', '1082860', '1086696'):
            row = egw_rows[fid]
            self.assertEqual(row['status'], 'verified_bookmaker_average')
            expected_sha = hashlib.sha256(row['excerpt'].encode('utf-8')).hexdigest()
            self.assertEqual(row['excerpt_sha256'], expected_sha)
            self.assertEqual(row['no_vig_probabilities'], no_vig(row['odds']))
        for fid in ('1086697', '1082861', '1082792', '1082793'):
            row = egw_rows[fid]
            self.assertEqual(row['status'], 'rejected_placeholder')
            self.assertEqual(row['banner_odds'], [1.8, 1.8])

    def test_executive_summary_links_and_surface_audits_pass(self) -> None:
        surf = self.live_report['rendered_surface_verification']
        self.assertEqual(surf['active_dashboard_violations'], 0)
        self.assertEqual(surf['acceptance_fail'], 0)
        self.assertTrue(surf['unresolved_register_present'])
        self.assertTrue(surf['no_line_register_present'])
        self.assertTrue(surf['unique_no_line_research_id'])
        self.assertEqual(
            surf['executive_summary_links_verified'],
            ['./origination/#picks', './picks/', './review/', './unresolved/'],
        )
        for fid in ('1085542', '1086696', '1082697', '1086697', '1082858', '1082861', '1082792', '1082793'):
            self.assertIn(fid, self.audit_md)


if __name__ == '__main__':
    unittest.main()
