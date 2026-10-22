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

    def test_validate_origination_replays_ranked_tie_break(self):
        from scripts.build_origination import validate_origination
        from scripts.originate import ranked_tie_break

        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / 'data'
            dst.mkdir()
            latest = json.loads((ROOT / 'data' / 'latest.json').read_text(encoding='utf-8'))
            orig = json.loads((ROOT / 'data' / 'origination.json').read_text(encoding='utf-8'))
            (dst / 'origination').mkdir()
            (dst / 'origination' / 'aliases.json').write_text(
                (ROOT / 'data' / 'origination' / 'aliases.json').read_text(encoding='utf-8'),
                encoding='utf-8',
            )
            ev_dir = dst / 'origination' / 'evidence'
            ev_dir.mkdir()

            active = [m for m in latest['matches'] if m['availability'] != 'past']
            target_id = active[0]['id']
            team_a, team_b = [t['name'] for t in active[0]['teams']]
            latest['matches'] = [copy.deepcopy(active[0])]
            latest['matches'][0]['analysis'] = None
            latest['matches'][0]['pick_index'] = None
            (dst / 'latest.json').write_text(json.dumps(latest), encoding='utf-8')

            snap_day = orig['generated_at'][:10]
            obs_ts = orig['generated_at']
            hltv_doc = {
                'observed_at': obs_ts,
                'snapshot_date': snap_day,
                'source_url': 'https://www.hltv.org/ranking/teams',
                'pages': [{
                    'status': 'ok',
                    'url': 'https://www.hltv.org/ranking/teams',
                    'rows': [
                        {'team': team_a, 'points': 2, 'rank': 215},
                        {'team': team_b, 'points': 2, 'rank': 229},
                    ],
                }],
            }
            (ev_dir / 'live-hltv-ranking.json').write_text(json.dumps(hltv_doc), encoding='utf-8')

            from scripts import hltv_ranking
            from scripts.domain import name_key, timestamp
            rows, meta = hltv_ranking.load(ev_dir)
            quote, reason = hltv_ranking.estimate(latest['matches'][0], rows, {'aliases': []}, timestamp(orig['generated_at']), meta=meta)
            self.assertIsNotNone(quote, reason)
            quote = dict(quote, method='model', label='Research model estimate (HLTV world ranking)',
                         fair_decimal=[2.0, 2.0], quotes=[], source='HLTV world ranking')
            winner, tie_record = ranked_tie_break(quote)
            quote['tie_break'] = tie_record

            orig_row = next(copy.deepcopy(m) for m in orig['matches'] if m['id'] == target_id)
            orig_row['origination'] = quote
            orig_row['pick_index'] = winner
            orig['matches'] = [orig_row]

            validate_origination(orig, dst)

            bad = copy.deepcopy(orig)
            bad['matches'][0]['pick_index'] = 1 - winner
            with self.assertRaises(AssertionError):
                validate_origination(bad, dst)


if __name__ == '__main__':
    unittest.main()
