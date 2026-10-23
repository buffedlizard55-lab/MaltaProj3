import json
import tempfile
import unittest
from pathlib import Path
from scripts.build import load_no_line_research, no_line_research_block


class CurrentResearchSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def record(self, name, clock, environment='github-actions-runner'):
        path = self.root / 'research' / name / 'line-source-research.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'observed_at': clock, 'environment': environment,
                                    'per_fixture': [{'teams': ['A', 'B'], 'money_line_lead': False}]}))
        path.with_suffix('.md').write_text('Dated report')
        return path

    def test_clock_not_directory_order_selects_report(self):
        self.record('z-old', '2026-10-22T00:00:00Z')
        self.record('a-current', '2026-10-23T00:00:00Z')
        result = load_no_line_research(self.root)
        self.assertEqual(result['_record_path'], 'research/a-current/line-source-research.json')
        output = no_line_research_block({'_no_line_research': result}, '../')
        self.assertIn('../data/research/a-current/line-source-research.json', output)
        self.assertIn('../data/research/a-current/line-source-research.md', output)
        self.assertNotIn('z-old', output)
        self.assertIn('historical research', output)
        self.assertNotIn('Cloudflare 403', output)

    def test_newer_local_failed_probe_does_not_displace_runner(self):
        self.record('runner', '2026-10-22T00:00:00Z')
        self.record('local', '2026-10-23T00:00:00Z', 'local checkout')
        self.assertIn('runner', load_no_line_research(self.root)['_record_path'])

    def test_missing_download_and_bad_date_are_skipped(self):
        self.record('bad-date', 'not-a-date')
        path = self.record('missing-download', '2026-10-23T00:00:00Z')
        path.with_suffix('.md').unlink()
        self.assertIsNone(load_no_line_research(self.root))

    def test_current_report_covers_all_nine_model_only_fixtures(self):
        root = Path('data/research/38c53ece')
        audit = json.loads((root / 'audit.json').read_text())
        summary = json.loads((root / 'line-source-research.json').read_text())
        self.assertEqual({str(x['id']) for x in audit['no_line_fixtures']},
                         {str(x['id']) for x in summary['per_fixture']})
        self.assertEqual(len(summary['per_fixture']), 9)
        self.assertEqual(summary['observed_at'], audit['observed_at'])
        self.assertFalse(summary['leads'])
