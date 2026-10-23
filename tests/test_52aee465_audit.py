from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path

from scripts import audit_rows, build, originate, review_register

audit_52aee465 = importlib.import_module('scripts.52aee465_audit')
ROOT = Path(__file__).resolve().parent.parent


class Session52aee465AuditTests(unittest.TestCase):
    def test_verify_all_passes_with_zero_errors(self) -> None:
        result = audit_52aee465.verify_all()
        self.assertTrue(result['ok'], msg=json.dumps(result['errors'], indent=2))
        self.assertEqual(result['verified_joins'], 16)
        self.assertEqual(result['negative_guards'], 8)
        self.assertEqual(result['audited_fixtures'], 30)
        self.assertGreaterEqual(result['flag_count'], 6)

    def test_pair_join_upgrades_live_fixtures_to_consensus(self) -> None:
        registry = originate.load_registry(ROOT / 'data' / 'origination' / 'aliases.json')

        # Fixture 1081149: Bovada 'Forze Reload vs Sokerorg' joins Hotspawn 'FORZE Reload vs LFO 10'
        fx_1081149 = {
            'fixture_id': '1081149',
            'competition': 'CCT Europe 2026 Series #12',
            'starts_at': '2026-10-23T08:00:00Z',
            'teams': [{'name': 'FORZE Reload'}, {'name': 'LFO 10'}],
        }
        joined, used, status = originate.pair_join(
            ['Forze Reload', 'Sokerorg'], '2026-10-23T08:00:00Z', fx_1081149, registry
        )
        self.assertEqual(status, 'matched')
        self.assertIsNotNone(joined)
        self.assertEqual(len(used), 1)
        self.assertEqual(used[0]['canonical'], 'LFO 10')
        aligned = originate.align_by_name([0.81, 0.19], ['Forze Reload', 'Sokerorg'], fx_1081149, registry)
        self.assertEqual(aligned, [0.81, 0.19])

        # Fixture 1082924: Pinnacle/Bovada 'Quintessencia vs Borracheiros' (reversed order) aligns cleanly
        fx_1082924 = {
            'fixture_id': '1082924',
            'competition': 'CCT South America 2026 Series #7',
            'starts_at': '2026-10-23T16:00:00Z',
            'teams': [{'name': 'BORRACHEIROS'}, {'name': 'QUINTESSÊNCIA'}],
        }
        joined_sa, used_sa, status_sa = originate.pair_join(
            ['Quintessencia', 'Borracheiros'], '2026-10-23T16:00:00Z', fx_1082924, registry
        )
        self.assertEqual(status_sa, 'matched')
        self.assertIsNotNone(joined_sa)
        self.assertEqual(used_sa[0]['canonical'], 'QUINTESSÊNCIA')
        aligned_sa = originate.align_by_name([0.74, 0.26], ['Quintessencia', 'Borracheiros'], fx_1082924, registry)
        self.assertEqual(aligned_sa, [0.26, 0.74])

        # Fixture 1082925: 'RED Academy' joins 'RED Canids Academy' but NEVER 'RED Canids'
        fx_1082925 = {
            'fixture_id': '1082925',
            'competition': 'CCT South America 2026 Series #7',
            'starts_at': '2026-10-23T19:00:00Z',
            'teams': [{'name': 'BESTIA Academy'}, {'name': 'RED Canids Academy'}],
        }
        _, _, status_acad = originate.pair_join(
            ['Bestia Academy', 'RED Academy'], '2026-10-23T19:00:00Z', fx_1082925, registry
        )
        self.assertEqual(status_acad, 'matched')
        _, _, status_main_blocked = originate.pair_join(
            ['Bestia Academy', 'RED Canids'], '2026-10-23T19:00:00Z', fx_1082925, registry
        )
        self.assertEqual(status_main_blocked, 'names')

    def test_flags_and_review_register_render_cleanly_in_site_builder(self) -> None:
        flags = json.loads((ROOT / 'data' / 'research' / '52aee465' / 'flags.json').read_text())
        ids = {f['id'] for f in flags}
        expected_flags = {
            '52aee465-model-roster-drift-1081605',
            '52aee465-model-roster-drift-1082861',
            '52aee465-network-model-thin-pm-1082858',
            '52aee465-nodwin-polymarket-stubs-2026-10-25',
            '52aee465-hotspawn-lobby-1081606-and-null-bo',
            '52aee465-published-pages-snapshot-lag',
        }
        self.assertTrue(expected_flags.issubset(ids))
        rendered_flags = build.flags_table(flags)
        for fid in expected_flags:
            self.assertIn(f'id="flag-{fid}"', rendered_flags)

        self.assertIn('research/52aee465/repo-review.json', review_register.REGISTERS)
        reg_doc = json.loads((ROOT / 'data' / 'research' / '52aee465' / 'repo-review.json').read_text())
        review_register.validate(reg_doc)
        rendered_reg = review_register.render(reg_doc, '../', section_id='session-review-52aee465',
                                              register_path='research/52aee465/repo-review.json',
                                              include_shared=False)
        for idx in range(1, 7):
            item_id = f'52aee465-0{idx}'
            self.assertIn(f'id="review-{item_id}"', rendered_reg)


if __name__ == '__main__':
    unittest.main()
