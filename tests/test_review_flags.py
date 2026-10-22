"""Final integration: every session's dated, source-linked findings stay visible.

The extra finding is a synthetic test record, never a production research claim.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build import build

ROOT = Path(__file__).resolve().parents[1]


class ReviewFlagsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        root = Path(cls.temporary.name)
        cls.source, cls.output = root / 'data', root / 'site'
        shutil.copytree(ROOT / 'data', cls.source)
        cls.original = (cls.source / 'latest.json').read_bytes()
        cls.baseline_flag = json.loads(cls.original)['flags'][0]
        cls.synthetic = {
            'id': 'synthetic-new-session-review-finding', 'severity': 'notice',
            'match_ids': [], 'title': 'Synthetic reviewed finding',
            'detail': 'Synthetic regression only; not an actual source observation.',
            'source_urls': ['https://github.com/buffedlizard55-lab/MaltaProj3'],
        }
        findings = cls.source / 'research/synthetic-new-session/flags.json'
        findings.parent.mkdir(parents=True)
        # Neither a duplicate in this file nor an earlier canonical ID may be
        # repeated or overwrite the real finding's original text.
        findings.write_text(json.dumps([
            cls.synthetic, cls.synthetic,
            dict(cls.baseline_flag, title='Synthetic duplicate must not replace the original'),
        ]))
        build(cls.source, cls.output)
        cls.html = (cls.output / 'review/index.html').read_text()

    def test_new_sessions_do_not_need_another_hardcoded_loader_path(self):
        self.assertIn('id="flag-' + self.synthetic['id'] + '"', self.html)

    def test_every_checked_in_session_finding_is_visible_once(self):
        expected = set()
        for findings in sorted((ROOT / 'data/research').glob('*/flags.json')):
            expected.update(finding['id'] for finding in json.loads(findings.read_text()))
        self.assertTrue(expected)
        for identity in sorted(expected):
            with self.subTest(identity=identity):
                self.assertEqual(self.html.count('id="flag-' + identity + '"'), 1)

    def test_duplicate_findings_do_not_overwrite_or_repeat(self):
        for identity in (self.synthetic['id'], self.baseline_flag['id']):
            with self.subTest(identity=identity):
                self.assertEqual(self.html.count('id="flag-' + identity + '"'), 1)
        self.assertNotIn('Synthetic duplicate must not replace the original', self.html)

    def test_render_only_findings_do_not_rewrite_the_canonical_json(self):
        # The collected snapshot itself is never rewritten by a build.
        self.assertEqual((self.source / 'latest.json').read_bytes(), self.original)
        # The published copy carries exactly one documented addition since
        # session 4c972a51: the featured-vs-researched reconciliation keys,
        # because counts.* describes the featured method alone while every page
        # renders the researched list. Every original key and value must survive
        # byte for byte, and no reconciliation key may appear without a note.
        published = json.loads((self.output / 'data/latest.json').read_text())
        original = json.loads(self.original)
        added = {'featured_method_counts', 'complete_coverage_counts', 'counts_note'}
        self.assertEqual(set(published) - set(original), added)
        for key, value in original.items():
            self.assertEqual(published[key], value, f'{key} was rewritten by the build')
        self.assertTrue(published['counts_note'])
        self.assertIn('featured', published['counts_note'].lower())


if __name__ == '__main__':
    unittest.main()
