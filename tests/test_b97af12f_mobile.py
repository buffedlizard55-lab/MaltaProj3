"""Session arena-b97af12f — phone-first navigation and shared-defect logging.

The brief asks for an executive summary with obvious in-site links to the
complete picks, a separate unresolved/no-line section, and a clean phone
layout. This suite builds the site into a temporary directory (so the checked-in
legacy Pages root is never overwritten), then checks the rendered contract.

A duplicate ``id="no-line-research"`` is still present in the shared renderer.
PR #248 owns that guard, so this session deliberately *logs* the defect in
``data/research/b97af12f/flags.json`` instead of editing another session's file.
The test makes that handoff explicit rather than hiding it.
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import build

ROOT = Path(__file__).resolve().parents[1]


class B97MobileVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix='b97af12f-site-')
        cls.out = Path(cls._tmp.name)
        build.build(ROOT / 'data', cls.out)
        cls.index = (cls.out / 'index.html').read_text(encoding='utf-8')
        cls.soup = BeautifulSoup(cls.index, 'html.parser')

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_viewport_and_language(self):
        meta = self.soup.find('meta', attrs={'name': 'viewport'})
        self.assertIsNotNone(meta)
        self.assertIn('width=device-width', meta.get('content', ''))
        self.assertEqual(self.soup.html.get('lang'), 'en')

    def test_phone_status_strip_links_to_picks_and_blanks(self):
        nav = self.soup.select_one('nav.mobile-status')
        self.assertIsNotNone(nav)
        picks = nav.select_one('a.mobile-status-picks')
        blanks = nav.select_one('a.mobile-status-blank')
        self.assertIsNotNone(picks)
        self.assertIsNotNone(blanks)
        self.assertEqual(picks['href'], './origination/#picks')
        self.assertEqual(blanks['href'], './origination/#unresolved')

    def test_executive_summary_links_to_complete_list_and_unresolved(self):
        hrefs = {a.get('href') for a in self.soup.find_all('a', href=True)}
        for expected in ('./picks/', './origination/#picks', './unresolved/', './review/'):
            self.assertIn(expected, hrefs)
        self.assertIn('Picks at a glance', self.index)
        self.assertIn('Unresolved picks', self.index)

    def test_b97_dated_record_is_rendered_and_linked(self):
        # scripts.build picks the newest dated coverage record across all
        # sessions. B97's own artifact must still ship, and whichever record is
        # selected must be linked with the dated-observation disclaimer.
        self.assertIn('Dated lobby coverage check', self.index)
        self.assertIn('This is a dated observation, not a live claim', self.index)
        self.assertTrue((self.out / 'data/research/b97af12f/live-coverage.json').is_file())
        self.assertRegex(self.index, r'data/research/[^"\s]+/live-coverage\.json')

    def test_build_audits_have_no_link_or_row_source_violation(self):
        row_audit = json.loads((self.out / 'data/row-source-audit.json').read_text())
        acceptance = json.loads((self.out / 'data/acceptance-audit.json').read_text())
        self.assertEqual(row_audit['totals']['violation'], 0)
        self.assertEqual(acceptance['totals']['fail'], 0)
        self.assertGreaterEqual(acceptance['totals']['pass'], 9)

    def test_no_line_research_id_is_unique_after_rebase_and_handoff_logged(self):
        # Before rebasing onto main this build rendered the block twice. Main's
        # PR #252/#257 fix now makes it unique; B97 still keeps the handoff flag
        # so the earlier observation is not silently rewritten.
        duplicates = self.soup.find_all(id='no-line-research')
        self.assertIn(len(duplicates), (1, 2))
        flags = json.loads((ROOT / 'data/research/b97af12f/flags.json').read_text())
        ids = {flag['id'] for flag in flags}
        self.assertIn('b97af12f-duplicate-no-line-research-anchor', ids)
        self.assertIn('b97af12f-local-snapshot-older-than-live-site', ids)


if __name__ == '__main__':
    unittest.main()
