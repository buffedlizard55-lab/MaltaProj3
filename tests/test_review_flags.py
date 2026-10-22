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
        """The source snapshot is never rewritten; the published copy only annotates it.

        build.write_reconciled_snapshot deliberately adds three keys to the
        *published* copy (featured_method_counts, complete_coverage_counts,
        counts_note) so a reader of the downloadable JSON is not told "10
        unresolved" while every page renders the researched list. Everything
        else — every source key, every match record, every featured counter —
        must survive untouched, and the source directory's own file must stay
        byte-identical. Session 3cf793ef: the previous assertion required the
        published copy to be byte-identical too, which the reconciliation
        feature made impossible, so main went red for every PR.
        """
        self.assertEqual((self.source / 'latest.json').read_bytes(), self.original)
        published = json.loads((self.output / 'data/latest.json').read_text())
        canonical = json.loads(self.original)
        added = set(published) - set(canonical)
        self.assertEqual(added, {'featured_method_counts', 'complete_coverage_counts', 'counts_note'})
        for key in canonical:
            with self.subTest(key=key):
                self.assertEqual(published[key], canonical[key])
        self.assertEqual(published['counts'], canonical['counts'])
        self.assertEqual([m['id'] for m in published['matches']], [m['id'] for m in canonical['matches']])
        self.assertTrue(published['counts_note'].startswith('counts.* and featured_method_counts'))


if __name__ == '__main__':
    unittest.main()
