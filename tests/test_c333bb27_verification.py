"""Tests for session arena-c333bb27 verification (Hotspawn 81/19 lobby parity,
HLTV-first + external-line origination replay, executive-summary & mobile
readability, and Flagged-for-Review register integrity).
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from scripts.review_register import REGISTERS, render, validate

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    'c333bb27_verify',
    ROOT / 'scripts' / 'c333bb27_verify.py',
)
c333bb27_verify = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(c333bb27_verify)


class TestC333bb27Verification(unittest.TestCase):
    def test_repo_root_passes_c333bb27_verifier(self):
        errors: list[str] = []
        res = c333bb27_verify.verify(ROOT, errors)
        self.assertEqual(errors, [], f'Unexpected verification errors: {errors}')
        self.assertGreaterEqual(res['replayed_count'], 1)
        self.assertLessEqual(res['max_probability_diff'], 1e-6)
        self.assertEqual(res['c333bb27_review_items'], 7)
        self.assertEqual(res['c333bb27_flags'], 4)

    def test_c333bb27_review_register_and_flags_schema(self):
        self.assertIn('research/c333bb27/repo-review.json', REGISTERS)
        reg_path = ROOT / 'data' / 'research' / 'c333bb27' / 'repo-review.json'
        reg = json.loads(reg_path.read_text())
        validate(reg)
        html = render(reg, '../', section_id='session-review-c333bb27',
                      register_path='research/c333bb27/repo-review.json',
                      include_shared=False)
        self.assertIn('arena-c333bb27', html)
        for item_id in ('C333-R01', 'C333-R02', 'C333-R03', 'C333-R04', 'C333-R05', 'C333-R06', 'C333-R07'):
            self.assertIn(item_id, html)

        flags_path = ROOT / 'data' / 'research' / 'c333bb27' / 'flags.json'
        flags = json.loads(flags_path.read_text())
        self.assertEqual(len(flags), 4)
        for flag in flags:
            self.assertTrue(flag['id'].startswith('c333bb27-'))
            self.assertIn(flag['severity'], ('notice', 'warning', 'error'))
            self.assertTrue(all(u.startswith('https://') for u in flag['source_urls']))

    def test_c333bb27_verification_dossier_replays_19_matches(self):
        dossier_path = ROOT / 'data' / 'research' / 'c333bb27' / 'verification-2026-10-26.json'
        dossier = json.loads(dossier_path.read_text())
        self.assertEqual(dossier['session'], 'arena-c333bb27')
        self.assertEqual(dossier['post_refresh_snapshot']['counts']['inventory'], 81)
        self.assertEqual(dossier['post_refresh_snapshot']['counts']['upcoming'], 19)
        self.assertEqual(dossier['post_refresh_snapshot']['origination_counts']['with_pick'], 19)
        self.assertEqual(dossier['replayed_count'], 19)
        self.assertEqual(dossier['max_probability_diff'], 0.0)
        for row in dossier['replayed_rows']:
            probs = row['probabilities']
            self.assertAlmostEqual(probs[0] + probs[1], 1.0, places=6)
            self.assertEqual(row['pick_index'], 0 if probs[0] > probs[1] else 1)
            self.assertTrue(row['source_url'].startswith('https://'))
            self.assertNotIn('hotspawn.com', row['source_url'])
            self.assertTrue(row['hltv_match_url'].startswith('https://www.hltv.org/matches/'))

    def test_synthetic_fixture_and_unresolved_glance_row_handling(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'index.html').write_text('''<!doctype html><html><head>
            <meta name="viewport" content="width=device-width, initial-scale=1"></head><body>
            <nav class="mobile-nav">
              <a><span>Summary</span></a><a><span>Picks</span></a><a><span>Unresolved</span></a>
              <a><span>Edge</span></a><a><span>Sources</span></a><a><span>Review</span></a>
            </nav>
            <nav id="start-here">
              <a href="./#picks-at-a-glance"></a><a href="./origination/#picks"></a>
              <a href="./#unresolved-register"></a><a href="./origination/#unresolved"></a>
            </nav>
            <ol class="glance-list">
              <li class="glance-row" data-glance-id="1079202">
                <span data-glance-pick>Pick</span><strong>FOKUS</strong>
                <span>68.2%</span><span>31.8%</span>
                <a href="https://thunderpick.io/api/matches">Thunderpick</a>
              </li>
              <li class="glance-row glance-unresolved" data-glance-id="9999999">
                <span>Unresolved · No price</span>
                <a href="./#unresolved-register">Why blank</a>
              </li>
            </ol>
            <section id="unresolved-register"></section>
            </body></html>''')
            (root / 'snapshot.json').write_text(json.dumps({
                'generated_at': '2026-10-26T01:04:20Z',
                'coverage_complete': True,
                'counts': {'upcoming': 2},
                'matches': [
                    {'id': '1079202', 'availability': 'open', 'teams': [{'name': 'FOKUS'}, {'name': 'ex-Zero Tenacity'}]},
                    {'id': '9999999', 'availability': 'open', 'teams': [{'name': 'Team A'}, {'name': 'Team B'}]},
                ],
            }))
            (root / 'origination.json').write_text(json.dumps({
                'generated_at': '2026-10-26T01:04:30Z',
                'counts': {'active': 2, 'resolved': 1, 'unresolved': 1, 'with_pick': 1},
                'matches': [
                    {
                        'id': '1079202',
                        'pick_index': 0,
                        'origination': {
                            'method': 'bookmaker',
                            'source': 'Thunderpick',
                            'source_url': 'https://thunderpick.io/api/matches',
                            'probabilities': [0.68235294, 0.31764706],
                            'quotes': [{'odds': [1.35, 2.9]}],
                        },
                    },
                    {
                        'id': '9999999',
                        'pick_index': None,
                        'origination': None,
                    },
                ],
            }))
            errors: list[str] = []
            c333bb27_verify.verify(root, errors)
            self.assertEqual(errors, [])

            # Inject a forbidden Hotspawn probability source_url and verify failure
            bad_orig = json.loads((root / 'origination.json').read_text())
            bad_orig['matches'][0]['origination']['source_url'] = 'https://www.hotspawn.com/matches/x'
            (root / 'origination.json').write_text(json.dumps(bad_orig))
            bad_errors: list[str] = []
            c333bb27_verify.verify(root, bad_errors)
            self.assertTrue(any('Hotspawn probability source_url' in e for e in bad_errors))


if __name__ == '__main__':
    unittest.main()
