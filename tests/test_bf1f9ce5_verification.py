"""Regression suite for session arena-bf1f9ce5.

All assertions are clock-free and mutable-snapshot-safe so future 4-hourly
`pages.yml` refreshes never break on fixture rotation.
"""
from __future__ import annotations

import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import build, review_register

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'data' / 'research' / 'bf1f9ce5'
verifier = importlib.import_module('scripts.bf1f9ce5_verify')


class ImportSafetyAndDossierTests(unittest.TestCase):
    def test_diagnostic_scripts_have_import_guards(self):
        self.assertEqual(verifier.verify_import_guards(), [])

    def test_top_level_network_call_is_caught_by_verifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'bad_script.py'
            bad.write_text('from urllib.request import urlopen\nurlopen("https://example.com")\n', encoding='utf-8')
            errs = verifier.verify_import_guards([bad])
            self.assertTrue(any('urlopen' in e for e in errs), errs)
            self.assertTrue(any('missing def main()' in e for e in errs), errs)

    def test_live_hotspawn_reconciliation_and_17_picks(self):
        self.assertEqual(verifier.verify_live_reconciliation(), [])

    def test_hotspawn_source_leak_is_rejected(self):
        recon = json.loads((RESEARCH / 'fresh-reconciliation.json').read_text(encoding='utf-8'))
        broken = copy.deepcopy(recon)
        broken['arithmetic_and_provenance'][0]['source_url'] = 'https://play.hotspawn.com/lobby'
        errs = verifier.verify_live_reconciliation(recon=broken)
        self.assertTrue(any('Hotspawn probability source' in e for e in errs), errs)

    def test_hltv_first_line_research_dossier_is_valid(self):
        self.assertEqual(verifier.verify_line_research(), [])

    def test_handwritten_probability_in_line_research_is_rejected(self):
        doc = json.loads((RESEARCH / 'line-source-research.json').read_text(encoding='utf-8'))
        broken = copy.deepcopy(doc)
        broken['per_fixture'][0]['probabilities'] = [0.6, 0.4]
        errs = verifier.verify_line_research(broken)
        self.assertTrue(any('hand-written probabilities' in e for e in errs), errs)

    def test_snapshot_independent_invariants_hold(self):
        self.assertEqual(verifier.verify_current_snapshot(), [])

    def test_review_register_and_flags_validate_cleanly(self):
        self.assertIn('research/bf1f9ce5/repo-review.json', review_register.REGISTERS)
        reg = json.loads((RESEARCH / 'repo-review.json').read_text(encoding='utf-8'))
        review_register.validate(reg)
        html = review_register.render(
            reg,
            '../',
            section_id='session-review-bf1f9ce5',
            register_path='research/bf1f9ce5/repo-review.json',
            include_shared=False,
        )
        self.assertIn('BF1F-R01', html)
        self.assertIn('BF1F-R08', html)
        flags = json.loads((RESEARCH / 'flags.json').read_text(encoding='utf-8'))
        self.assertEqual(len(flags), 3)
        for flag in flags:
            self.assertTrue(flag['id'].startswith('bf1f9ce5-'))
            self.assertTrue(all(u.startswith('https://') for u in flag['source_urls']))


class BuiltDashboardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix='bf1f9ce5-site-')
        cls.site = Path(cls._tmp.name) / 'site'
        build.build(ROOT / 'data', cls.site)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_newest_line_research_and_live_coverage_selected(self):
        nl = build.load_no_line_research(ROOT / 'data')
        self.assertIsNotNone(nl)
        doc_nl = nl[0] if isinstance(nl, tuple) else nl
        self.assertGreaterEqual(str(doc_nl.get('observed_at', '')), '2026-10-25T13:57:50Z')

        lc = build.load_live_coverage(ROOT / 'data')
        self.assertIsNotNone(lc)
        doc_lc = lc[0] if isinstance(lc, tuple) else lc
        self.assertGreaterEqual(str(doc_lc.get('observed_at', '')), '2026-10-25T13:57:50Z')

        index_html = (self.site / 'index.html').read_text(encoding='utf-8')
        soup = BeautifulSoup(index_html, 'html.parser')
        self.assertIsNotNone(soup.select_one('#unresolved-register'))
        self.assertIsNotNone(soup.select_one('#no-line-register'))
        gap = soup.select_one('#live-coverage-gap')
        if gap is not None:
            self.assertNotIn('%', gap.get_text())

        unresolved_html = (self.site / 'unresolved' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('no-line-research', unresolved_html)

        hrefs = {a.get('href') for a in soup.find_all('a', href=True)}
        for expected in ('./origination/#picks', './picks/', './unresolved/', './review/'):
            self.assertIn(expected, hrefs)

    def test_flagged_for_review_renders_bf1f9ce5_register_and_flags(self):
        review_html = (self.site / 'review' / 'index.html').read_text(encoding='utf-8')
        for token in (
            'BF1F-R01',
            'BF1F-R02',
            'BF1F-R04',
            'BF1F-R08',
            'bf1f9ce5-lobby-edge-cache-stale-cards',
            'bf1f9ce5-dfrag-substitute-markers-no-narrow-line',
            'bf1f9ce5-prelock-polymarket-rolloff-1085542',
        ):
            self.assertIn(token, review_html)


if __name__ == '__main__':
    unittest.main()
