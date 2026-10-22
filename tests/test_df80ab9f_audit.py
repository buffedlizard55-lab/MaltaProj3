"""Unit tests for session arena-df80ab9f line-by-line verification and flags."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import df80ab9f_audit, review_register
from scripts.audit_rows import is_official

ROOT = Path(__file__).resolve().parents[1]
SESSION_DIR = ROOT / 'data' / 'research' / 'df80ab9f'


class Df80ab9fAuditTests(unittest.TestCase):
    def test_audit_session_dir_passes_with_zero_errors(self):
        report = df80ab9f_audit.audit_session_dir(SESSION_DIR)
        self.assertTrue(report['ok'], report.get('errors'))
        self.assertEqual(report['active_matches'], 46)
        self.assertGreaterEqual(report['low_tier_dossiers'], 12)
        self.assertEqual(report['flags'], 7)
        self.assertEqual(report['register_items'], 7)

    def test_register_is_declared_and_renders_cleanly(self):
        self.assertIn(df80ab9f_audit.REGISTER_REL, review_register.REGISTERS)
        reg = json.loads((SESSION_DIR / 'repo-review.json').read_text(encoding='utf-8'))
        review_register.validate(reg)
        html = review_register.render(
            reg,
            '../',
            section_id='session-review-df80',
            register_path=df80ab9f_audit.REGISTER_REL,
            include_shared=False,
        )
        self.assertIn('arena-df80ab9f', html)
        for item in reg['items']:
            self.assertIn(f'id="review-{item["id"]}"', html)
            for ev in item['evidence']:
                self.assertTrue(is_official(ev['url']), ev['url'])

    def test_unconfirmed_and_tied_matches_keep_null_picks_and_flags(self):
        inv = json.loads((SESSION_DIR / 'live-inventory-audit.json').read_text(encoding='utf-8'))
        by_id = {m['id']: m for m in inv['active_matches']}

        kingui = by_id['1082919']
        self.assertIsNone(kingui['verified_probabilities'])
        self.assertIsNone(kingui['verified_pick_team'])
        self.assertIn('df80ab9f-kingui-missing-alias-inverted-pick', kingui['flag_ids'])

        isurus = by_id['1082926']
        self.assertEqual(isurus['verified_probabilities'], [0.5, 0.5])
        self.assertIsNone(isurus['verified_pick_team'])
        self.assertIn('df80ab9f-isurus-hacha-hltv-integer-tie-1082926', isurus['flag_ids'])

        gremio = by_id['1082922']
        self.assertEqual(gremio['verified_probabilities'], [0.285, 0.715])
        self.assertEqual(gremio['verified_pick_team'], 'Grêmio')
        self.assertIn('df80ab9f-cct-sa7-polymarket-alias-gaps', gremio['flag_ids'])

    def test_audit_rejects_hotspawn_vote_usage_and_unofficial_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / 'df80ab9f'
            dst.mkdir()
            for name in ('live-inventory-audit.json', 'low-tier-line-research.json', 'flags.json', 'repo-review.json'):
                (dst / name).write_text((SESSION_DIR / name).read_text(encoding='utf-8'), encoding='utf-8')

            inv = json.loads((dst / 'live-inventory-audit.json').read_text(encoding='utf-8'))
            bad = copy.deepcopy(inv)
            bad['active_matches'][0]['hotspawn_votes_used'] = True
            bad['active_matches'][0]['source_urls'].append('https://untrusted-blog.example/odds')
            (dst / 'live-inventory-audit.json').write_text(json.dumps(bad), encoding='utf-8')

            report = df80ab9f_audit.audit_session_dir(dst)
            self.assertFalse(report['ok'])
            self.assertTrue(any('hotspawn_votes_used' in e for e in report['errors']))
            self.assertTrue(any('non-official URL' in e for e in report['errors']))


if __name__ == '__main__':
    unittest.main()
