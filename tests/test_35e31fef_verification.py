"""Unit & integration tests for session arena-35e31fef verification & dossiers."""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import audit_rows, build, originate, reference_odds, review_register, session_35e31fef_verify

UTC = timezone.utc
ROOT = Path(__file__).resolve().parent.parent


class Session35E31FEFVerificationTest(unittest.TestCase):
    def test_verify_all_dossiers_and_snapshot_replay(self):
        summary = session_35e31fef_verify.verify_all(ROOT)
        dossiers = summary['dossiers']
        self.assertEqual(dossiers['reference_entries'], 3)
        self.assertEqual(dossiers['reference_rejected'], 5)
        self.assertEqual(dossiers['live_coverage_fixtures'], 17)
        self.assertEqual(dossiers['observations'], 7)
        self.assertEqual(dossiers['flags'], 6)
        self.assertEqual(dossiers['review_items'], 5)
        self.assertEqual(dossiers['gz_1082858_probabilities'], [0.26495726, 0.73504274])

    def test_fresh_egw_captures_rescue_1082858_1082859_1086696_inside_8h_gate(self):
        """At 2026-10-25T13:45Z (when 2026-10-24T16:42Z captures are >21h stale), 35e31fef resolves cleanly."""
        now = datetime(2026, 10, 25, 13, 45, tzinfo=UTC)
        loaded_ref = reference_odds.load(ROOT / 'data')
        ref_rows = list(loaded_ref['entries']) + list(loaded_ref['rejected'])

        cases = [
            (
                '1082858',
                '2026-10-26T03:00:00Z',
                'DFRAG Invitational 2026',
                ['Ground Zero', 'Off Chops'],
                1,
                [0.26495726, 0.73504274],
            ),
            (
                '1082859',
                '2026-10-26T03:00:00Z',
                'DFRAG Invitational 2026',
                ['NEXVOID', 'Alter Ego'],
                0,
                [0.57724645, 0.42275355],
            ),
            (
                '1086696',
                '2026-10-25T16:00:00Z',
                'CCT South America 2026 Series #7',
                ['BORRACHEIROS', 'RED Canids Academy'],
                1,
                [0.43548387, 0.56451613],
            ),
        ]
        for fid, starts_at, comp, teams, exp_pick, exp_probs in cases:
            match = {
                'id': fid,
                'starts_at': starts_at,
                'locks_at': starts_at,
                'availability': 'open',
                'competition': comp,
                'tier': 'b',
                'source_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{fid}',
                'lobby_url': 'https://play.hotspawn.com/lobby',
                'teams': [{'id': '1', 'name': teams[0]}, {'id': '2', 'name': teams[1]}],
            }
            res = originate.originate_match(match, [], [], {}, {}, {}, now, reference=ref_rows)
            orig = res.get('origination') or {}
            self.assertEqual(orig.get('method'), 'reference', fid)
            self.assertEqual(res.get('pick_index'), exp_pick, fid)
            for got_p, exp_p in zip(orig['probabilities'], exp_probs):
                self.assertAlmostEqual(got_p, exp_p, places=7, msg=fid)

    def test_post_snapshot_1086697_binds_polymarket_via_aliases_and_rejects_drifted_kalshi(self):
        """1086697 (Projeto do KinGui vs Yawara, 19:00Z) binds Tropa do KinGui / Yawara Esports on Polymarket and rejects 16:00Z Kalshi."""
        now = datetime(2026, 10, 25, 13, 45, tzinfo=UTC)
        registry = originate.load_registry(ROOT / 'data/origination/aliases.json')
        match = {
            'id': '1086697',
            'starts_at': '2026-10-25T19:00:00Z',
            'locks_at': '2026-10-25T18:54:00Z',
            'availability': 'open',
            'competition': 'CCT South America 2026 Series #7',
            'tier': 'c',
            'source_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1086697',
            'lobby_url': 'https://play.hotspawn.com/lobby',
            'teams': [{'id': '205456', 'name': 'Projeto do KinGui'}, {'id': '121549', 'name': 'Yawara'}],
        }
        poly_rows = [
            {
                'provider': 'Polymarket',
                'event_id': '1249642',
                'market_id': '6169151',
                'slug': 'cs2-tdkg-yaw-2026-10-25',
                'question': 'Counter-Strike: Tropa do KinGui vs Yawara Esports (BO3) - CCT South America Series #7 Semifinal',
                'start': datetime(2026, 10, 25, 19, 0, tzinfo=UTC),
                'names': ['Tropa do KinGui', 'Yawara Esports'],
                'bid': [0.61, 0.38],
                'ask': [0.62, 0.39],
                'liquidity': 3200.0,
                'volume': 410.0,
                'observed_at': '2026-10-25T13:44:00Z',
                'source_url': 'https://polymarket.com/event/cs2-tdkg-yaw-2026-10-25',
                'evidence_file': 'data/research/35e31fef/hltv-first-observations.json',
            },
            {
                'provider': 'Kalshi',
                'event_id': 'KXCS2GAME-26OCT251200YAWTDKG',
                'market_id': 'KXCS2GAME-26OCT251200YAWTDKG',
                'question': 'Will Tropa do KinGui win the Yawara vs. Tropa do KinGui Counter-Strike 2 match scheduled for Oct 25, 2026 at 12:00 PM EDT?',
                'start': datetime(2026, 10, 25, 16, 0, tzinfo=UTC),
                'names': ['Tropa do KinGui', 'Yawara'],
                'bid': [0.58, 0.29],
                'ask': [0.66, 0.46],
                'liquidity': 500.0,
                'volume': 0.0,
                'observed_at': '2026-10-25T13:44:00Z',
                'source_url': 'https://kalshi.com/markets/kxcs2game/cs2-game/kxcs2game-26oct251200yawtdkg',
                'evidence_file': 'data/research/35e31fef/hltv-first-observations.json',
            },
        ]
        res = originate.originate_match(match, poly_rows, [], {}, {}, registry, now)
        orig = res.get('origination') or {}
        self.assertEqual(orig.get('method'), 'market')
        self.assertEqual(res.get('pick_index'), 0)
        self.assertAlmostEqual(orig['probabilities'][0], 0.615, places=6)
        self.assertAlmostEqual(orig['probabilities'][1], 0.385, places=6)
        kalshi_stages = [s for s in res['research'] if 'Kalshi' in s.get('stage', '')]
        self.assertEqual(len(kalshi_stages), 1)
        self.assertEqual(kalshi_stages[0]['status'], 'unresolved')

    def test_live_coverage_and_review_register_render_cleanly_without_percent_chars(self):
        cov = build.load_live_coverage(ROOT / 'data')
        self.assertIsNotNone(cov)
        self.assertGreaterEqual(cov['observed_at'], '2026-10-25T13:37:45Z')

        cov_35e3 = json.loads((ROOT / 'data/research/35e31fef/live-coverage.json').read_text(encoding='utf-8'))
        gaps_html = build.live_coverage_gaps({'matches': [], 'complete_picks': {'matches': []}, '_live_coverage': cov_35e3}, '')
        self.assertNotIn('%', gaps_html)
        for fid in ('1086696', '1082697', '1086697'):
            self.assertIn(fid, gaps_html)

        reg = json.loads((ROOT / 'data/research/35e31fef/repo-review.json').read_text(encoding='utf-8'))
        reg_html = review_register.render(
            reg,
            '',
            section_id='session-review-35e31fef',
            register_path='research/35e31fef/repo-review.json',
            include_shared=False,
        )
        for item_id in ('review-35E3-R01', 'review-35E3-R02', 'review-35E3-R03', 'review-35E3-R04', 'review-35E3-R05'):
            self.assertIn(item_id, reg_html)

        flags = json.loads((ROOT / 'data/research/35e31fef/flags.json').read_text(encoding='utf-8'))
        self.assertEqual([f['id'] for f in flags], [f'35e31fef-00{i}' for i in range(1, 7)])
        for fl in flags:
            for url in fl['source_urls']:
                self.assertTrue(audit_rows.is_official(url), url)


if __name__ == '__main__':
    unittest.main()
