"""Unit & integration tests for session arena-c2a74e33 verification, <8h EGW
reference-odds refresh in CAPTURE_PATHS, 22/22 live coverage dossier, flags,
and line-by-line repository review register."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import audit_rows, build, c2a74e33_verify, originate, reference_odds, review_register

ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = ROOT / 'data/research/c2a74e33'
UTC = timezone.utc


class SessionC2A74E33VerificationTests(unittest.TestCase):
    def test_verify_all_replays_18_featured_and_23_complete_cards_and_dossiers(self) -> None:
        summary = c2a74e33_verify.verify_all(ROOT)
        snap = summary['snapshot_and_origination']
        self.assertEqual(snap['active'], 23)
        self.assertEqual(snap['featured_resolved'], 18)
        self.assertEqual(
            set(snap['featured_unresolved']),
            {'1083121', '1083122', '1081156', '1082858', '1082792'},
        )
        self.assertEqual(snap['complete_pick_cards'], 23)
        dos = summary['dossiers']
        self.assertEqual(dos['reference_entries'], 4)
        self.assertEqual(dos['reference_rejected'], 9)
        self.assertEqual(dos['live_coverage_fixtures'], 22)
        self.assertEqual(dos['observations'], 5)
        self.assertEqual(dos['flags'], 5)
        self.assertEqual(dos['review_items'], 5)
        self.assertEqual(dos['gz_1082858_probabilities'], [0.26495726, 0.73504274])

    def test_fresh_c2a74e33_capture_rescues_1082858_when_e57_is_stale(self) -> None:
        now = datetime(2026, 10, 24, 16, 45, tzinfo=UTC)
        e57 = json.loads((ROOT / 'data/research/e57df95b/reference-odds.json').read_text(encoding='utf-8'))['entries'][0]
        match = {
            'id': '1082858',
            'starts_at': '2026-10-26T03:00:00Z',
            'locks_at': '2026-10-26T02:55:00Z',
            'availability': 'open',
            'competition': 'DFRAG Invitational 2026',
            'tier': 'c',
            'source_url': 'https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858',
            'lobby_url': 'https://play.hotspawn.com/lobby',
            'teams': [{'id': '1', 'name': 'Ground Zero'}, {'id': '2', 'name': 'Off Chops'}],
        }
        stale_q, stale_reason = reference_odds.quote(e57, match, now)
        self.assertIsNone(stale_q)
        self.assertIn('older than eight hours', stale_reason)

        loaded = reference_odds.load(ROOT / 'data')
        rows = list(loaded['entries']) + list(loaded['rejected'])
        resolved = originate.originate_match(match, [], [], {}, {}, {}, now, reference=rows)
        orig = resolved['origination']
        self.assertEqual(orig['method'], 'reference')
        self.assertEqual(orig['probabilities'], [0.26495726, 0.73504274])
        self.assertEqual(resolved['pick_index'], 1)

    def test_live_coverage_selected_and_renders_zero_percent_signs(self) -> None:
        cov = json.loads((RESEARCH_DIR / 'live-coverage.json').read_text(encoding='utf-8'))
        self.assertTrue((RESEARCH_DIR / 'live-coverage.md').is_file())
        selected = build.load_live_coverage(ROOT / 'data')
        self.assertIsNotNone(selected)
        self.assertGreaterEqual(selected['observed_at'], cov['observed_at'])
        html = build.live_coverage_gaps({'matches': [], 'complete_picks': {'matches': []}, '_live_coverage': cov}, '')
        self.assertIn('22 missing at that observation', html)
        self.assertNotIn('%', html)
        for row in cov['live_fixtures']:
            self.assertIn(row['hotspawn_url'], html)
            self.assertIn(row['hltv_url'], html)

    def test_flags_and_review_register_render_with_zero_audit_violations(self) -> None:
        rel = 'research/c2a74e33/repo-review.json'
        self.assertIn(rel, review_register.REGISTERS)
        reg_doc = json.loads((RESEARCH_DIR / 'repo-review.json').read_text(encoding='utf-8'))
        flags_doc = json.loads((RESEARCH_DIR / 'flags.json').read_text(encoding='utf-8'))
        reg_html = review_register.render(
            reg_doc, '../', section_id='session-review-c2a74e33', register_path=rel
        )
        flags_html = build.flags_table(flags_doc)
        for flag_id in ('c2a74e33-001', 'c2a74e33-002', 'c2a74e33-003', 'c2a74e33-004', 'c2a74e33-005'):
            self.assertIn(f'flag-{flag_id}', flags_html)
        for item_id in ('C2A7-R01', 'C2A7-R02', 'C2A7-R03', 'C2A7-R04', 'C2A7-R05'):
            self.assertIn(f'review-{item_id}', reg_html)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site/review'
            out.mkdir(parents=True)
            (out / 'index.html').write_text(
                f'<!doctype html><html><body>{flags_html}{reg_html}</body></html>',
                encoding='utf-8',
            )
            report = audit_rows.audit_site(Path(tmp) / 'site')
            self.assertEqual(report['totals']['violation'], 0)


if __name__ == '__main__':
    unittest.main()
