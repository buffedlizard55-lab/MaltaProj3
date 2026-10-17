"""Session 9866e1ba verification dossier and Leaderboard Plan Day 3–4 integration tests.

Verifies:
1. Every URL in data/research/9866e1ba/verification-report.json and flags.json is an official source.
2. All 10 TWC 2026 Days 1–3 series, Aurora's July 2026 rebuild context, both Day 4 semifinals, and all 8 unresolved fixtures are documented with official sources and no invented values.
3. The /strategy/ build publishes Day 3 decider results and Day 4 semifinal BO3 score-slip guidance in both HTML and site/data/strategy.json with zero row-source audit violations.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import audit_rows, build_strategy

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'data' / 'research' / '9866e1ba' / 'verification-report.json'
FLAGS = ROOT / 'data' / 'research' / '9866e1ba' / 'flags.json'


def iter_urls(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('source_url', 'url') and isinstance(v, str):
                yield v
            elif k == 'source_urls' and isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        yield item
            else:
                yield from iter_urls(v)
    elif isinstance(node, list):
        for item in node:
            yield from iter_urls(item)


class Session9866e1baDossierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT.read_text(encoding='utf-8'))
        cls.flags = json.loads(FLAGS.read_text(encoding='utf-8'))

    def test_every_url_in_report_and_flags_is_official(self):
        report_urls = list(iter_urls(self.report))
        flag_urls = list(iter_urls(self.flags))
        self.assertGreaterEqual(len(report_urls), 20)
        self.assertGreaterEqual(len(flag_urls), 10)
        for url in report_urls + flag_urls:
            self.assertTrue(audit_rows.is_official(url), f'Non-official URL: {url}')

    def test_twc_days_1_to_3_cover_all_ten_completed_series(self):
        series = self.report['twc_days_1_to_3_results']
        self.assertEqual(len(series), 10)
        by_id = {s['hltv_match_id']: s for s in series}
        self.assertEqual(by_id[2399384]['winner'], '9z')
        self.assertEqual(by_id[2399384]['loser'], 'Aurora')
        self.assertEqual(by_id[2399412]['winner'], 'Aurora')
        self.assertEqual(by_id[2399412]['score'], '2-0')
        self.assertEqual(by_id[2399413]['winner'], 'BETBOOM')
        self.assertEqual(by_id[2399413]['score'], '2-1')

    def test_aurora_rebuild_context_is_dated_and_refuses_unverified_adjustments(self):
        rc = self.report['aurora_roster_and_form_context']
        self.assertEqual(rc['documented_rebuild_date'], '2026-07-08')
        self.assertEqual(set(rc['players_in']), {'kyxsan', 'Jimpphat'})
        self.assertEqual(rc['coach_in'], ['ash'])
        self.assertTrue(rc['unverified_and_unquantified_factors'])

    def test_day_four_semifinal_plan_separates_contrarian_slot_from_chalk_lock(self):
        sf1, sf2 = self.report['day_four_semifinal_plan']
        self.assertEqual(sf1['teams'], ['FURIA', 'Aurora'])
        self.assertEqual(sf1['default_pick'], 'FURIA')
        self.assertEqual(sf1['contrarian_verdict'], 'defensible-contrarian-slot')
        self.assertEqual(sf1['contrarian_pick'], 'Aurora')
        self.assertAlmostEqual(sf1['probabilities']['FURIA'] + sf1['probabilities']['Aurora'], 1.0, places=4)

        self.assertEqual(sf2['teams'], ['Falcons', 'BETBOOM'])
        self.assertEqual(sf2['default_pick'], 'Falcons')
        self.assertEqual(sf2['contrarian_verdict'], 'lock-do-not-fade')
        self.assertIsNone(sf2['contrarian_pick'])
        self.assertAlmostEqual(sf2['probabilities']['Falcons'] + sf2['probabilities']['BETBOOM'], 1.0, places=4)

    def test_unresolved_fixtures_review_covers_all_eight_snapshot_gaps(self):
        unresolved = self.report['unresolved_fixtures_review']
        ids = [u['hotspawn_id'] for u in unresolved]
        self.assertEqual(
            set(ids),
            {'1079170', '1081515', '1081526', '1081527', '1081521', '1081522', '1081861', '1081863'},
        )
        for u in unresolved:
            self.assertTrue(u['limitation'], u['hotspawn_id'])
            self.assertTrue(u['source_urls'], u['hotspawn_id'])

    def test_flags_schema_is_valid(self):
        self.assertEqual(len({f['id'] for f in self.flags}), len(self.flags))
        for f in self.flags:
            self.assertEqual(set(f.keys()), {'id', 'severity', 'title', 'detail', 'match_ids', 'source_urls'})
            self.assertIn(f['severity'], {'notice', 'warning'})

    def test_flags_are_registered_with_the_executive_review_builder(self):
        build_source = (ROOT / 'scripts' / 'build.py').read_text(encoding='utf-8')
        self.assertIn("for findings in sorted((source / 'research').glob('*/flags.json')):", build_source)
        self.assertIn(FLAGS, sorted((ROOT / 'data/research').glob('*/flags.json')))

    def test_strategy_build_exports_day3_and_day4_to_html_and_json_and_passes_strict_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site'
            html_path = build_strategy.build(ROOT / 'data', out)
            html = html_path.read_text(encoding='utf-8')
            data = json.loads((out / 'data' / 'strategy.json').read_text(encoding='utf-8'))
            report = audit_rows.audit_site(out)
        self.assertEqual(report['totals']['violation'], 0)
        self.assertGreaterEqual(report['totals']['ok'], 29)
        self.assertIn('id="day3-completed-results"', html)
        self.assertIn('id="day4-semifinals-plan"', html)
        self.assertEqual(len(data['twc_day3_results']), 2)
        self.assertEqual(len(data['twc_day4_semifinals']), 2)


if __name__ == '__main__':
    unittest.main()
