"""Unit tests for session arena-eea4c104 line-by-line audit, flags, and 30-row HLTV reconciliation.

All assertions are strictly deterministic and wall-clock independent (no fixed date thresholds
that can expire in future scheduled publisher runs).
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import build, eea4c104_audit
from scripts.audit_rows import audit_site as audit_rows_site, is_official

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / 'data' / 'research' / 'eea4c104'
FLAGS_PATH = RESEARCH_DIR / 'flags.json'
RECON_JSON = RESEARCH_DIR / 'reconciliation-30-matches.json'
RECON_MD = RESEARCH_DIR / 'reconciliation-30-matches.md'
LINE_RESEARCH_JSON = RESEARCH_DIR / 'line-source-research.json'
LINE_RESEARCH_MD = RESEARCH_DIR / 'line-source-research.md'


class Eea4c104FlagsAndReconciliationTests(unittest.TestCase):
    def test_flags_schema_and_official_sources(self):
        res = eea4c104_audit.audit_flags(FLAGS_PATH)
        self.assertTrue(res['ok'], res['errors'])
        self.assertGreaterEqual(res['count'], 5)

        flags = json.loads(FLAGS_PATH.read_text(encoding='utf-8'))
        by_id = {f['id']: f for f in flags}
        self.assertIn('eea4c104-kalshi-bo3-alias-banda-chuya-los-kogutos-1081605', by_id)
        self.assertIn('eea4c104-lph-gaming-thunderpick-alias-1082980', by_id)
        self.assertIn('eea4c104-abyssal-alias-evidence-drift-1082861', by_id)
        self.assertIn('eea4c104-nodwin-oct25-promotion-and-kalshi-spreads', by_id)
        replay_flag = by_id['eea4c104-replayed-1083025-and-hotspawn-ssr-cdn-lag']
        self.assertIn('f6bfc506-row-1083025-not-replayed', replay_flag.get('supersedes') or [])

        # Verify build.flags_table renders supersede linkage cleanly.
        prior = {
            'id': 'f6bfc506-row-1083025-not-replayed',
            'severity': 'notice',
            'match_ids': ['1083025'],
            'title': 'Prior unverified replay note',
            'detail': 'Not yet replayed.',
            'source_urls': ['https://polymarket.com/event/cs2-pain-imp11-2026-10-23'],
        }
        rendered = build.flags_table([prior, replay_flag])
        self.assertIn('class="superseded-flag"', rendered)
        self.assertIn('#flag-eea4c104-replayed-1083025-and-hotspawn-ssr-cdn-lag', rendered)

    def test_thirty_row_hltv_reconciliation_complete_and_official(self):
        self.assertTrue(RECON_JSON.is_file(), 'missing reconciliation-30-matches.json')
        self.assertTrue(RECON_MD.is_file(), 'missing reconciliation-30-matches.md')
        doc = json.loads(RECON_JSON.read_text(encoding='utf-8'))
        self.assertEqual(doc['session'], 'arena-eea4c104')
        self.assertEqual(doc['total_active_rows'], 30)
        self.assertEqual(doc['hltv_bo3_mapped'], 30)
        self.assertEqual(doc['money_backed_rows'] + doc['research_model_rows'], 30)

        seen_ids = set()
        for row in doc['rows']:
            rid = row['id']
            seen_ids.add(rid)
            self.assertEqual(len(row['teams']), 2, rid)
            self.assertEqual(len(row['probabilities_pct']), 2, rid)
            self.assertAlmostEqual(sum(row['probabilities_pct']), 100.0, delta=0.25, msg=rid)
            self.assertIn(row['pick'], row['teams'], rid)
            self.assertAlmostEqual(row['pick_pct'], max(row['probabilities_pct']), delta=0.15, msg=rid)
            self.assertAlmostEqual(row['fair_decimal'], 100.0 / row['pick_pct'], delta=0.02, msg=rid)
            self.assertTrue(str(row.get('hltv_url') or '').startswith('https://www.hltv.org/matches/'), rid)
            self.assertEqual(row.get('hltv_format'), 'bo3', rid)
            self.assertTrue(row['all_sources_official'], rid)
            for u in row['verified_official_sources']:
                self.assertTrue(is_official(u), f'{rid}: non-official {u}')
        self.assertEqual(len(seen_ids), 30)

    def test_built_site_passes_eea4c104_and_strict_row_audit_plus_mutations(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site'
            build.build(ROOT / 'data', out)
            res = eea4c104_audit.audit_site(out, FLAGS_PATH)
            self.assertTrue(res['ok'], res['errors'])
            self.assertEqual(res['flags_checked'], len(json.loads(FLAGS_PATH.read_text(encoding='utf-8'))))

            strict = audit_rows_site(out)
            self.assertEqual(strict['totals']['violation'], 0, strict)

            # Mutation 1: Hotspawn `% picked` crowd-figure leak on Executive Summary must fail.
            mutated = Path(tmp) / 'site_mut'
            shutil.copytree(out, mutated)
            idx = mutated / 'index.html'
            idx.write_text(
                idx.read_text(encoding='utf-8').replace('</main>', '<p>Crowd 74.2% picked Team A</p></main>'),
                encoding='utf-8',
            )
            bad_crowd = eea4c104_audit.audit_site(mutated, FLAGS_PATH)
            self.assertFalse(bad_crowd['ok'])
            self.assertTrue(any('% picked' in e for e in bad_crowd['errors']), bad_crowd['errors'])

            # Mutation 2: non-official source URL in flags.json must fail audit_flags.
            bad_flags = Path(tmp) / 'bad-flags.json'
            bad_flags.write_text(json.dumps([{
                'id': 'eea4c104-bad',
                'severity': 'warning',
                'match_ids': [],
                'title': 'Bad source test',
                'detail': 'Unlisted domain',
                'source_urls': ['https://untrusted.example.org/odds'],
            }]), encoding='utf-8')
            bad_res = eea4c104_audit.audit_flags(bad_flags)
            self.assertFalse(bad_res['ok'])

    def test_runner_line_source_research_is_valid_and_discoverable(self):
        self.assertTrue(LINE_RESEARCH_JSON.is_file(), 'missing line-source-research.json')
        self.assertTrue(LINE_RESEARCH_MD.is_file(), 'missing line-source-research.md')
        doc = json.loads(LINE_RESEARCH_JSON.read_text(encoding='utf-8'))
        self.assertEqual(doc['session'], 'arena-eea4c104')
        self.assertEqual(doc['environment'], 'github-actions-runner')
        self.assertGreaterEqual(len(doc['per_fixture']), 8)
        self.assertIn('1081605', (doc.get('kalshi_scan') or {}).get('stubs') or {})

        selected = build.load_no_line_research(ROOT / 'data')
        self.assertIsNotNone(selected)
        self.assertGreaterEqual(selected['observed_at'], doc['observed_at'])


if __name__ == '__main__':
    unittest.main()
