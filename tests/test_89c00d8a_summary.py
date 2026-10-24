"""Regression checks for the 2026-10-24 executive-summary integration."""
from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import summary, unresolved_register

ROOT = Path(__file__).resolve().parents[1]


def fixture_data() -> dict:
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    data['_no_line_research'] = {
        'observed_at': '2026-10-24T05:00:00Z',
        'environment': 'github-actions-runner',
        '_record_path': 'research/89c00d8a/line-source-research.json',
        'per_fixture': [{
            'id': '1082996', 'teams': ['Acend', 'UNiTY'],
            'competition': 'NODWIN Clutch Series #13',
            'money_line_lead': None,
            'verdict': 'Dated test evidence only; no price is created.',
        }],
    }
    return data


class ExecutiveSummaryResearchBlockTests(unittest.TestCase):
    def test_summary_renders_the_dated_research_exactly_once(self):
        html = summary(fixture_data(), './')
        self.assertEqual(html.count('id="no-line-research"'), 1)
        self.assertIn('latest dated research', html)
        self.assertIn('id="unresolved-register"', html)
        self.assertIn('id="no-line-register"', html)

    def test_summary_has_no_duplicate_html_ids(self):
        page = BeautifulSoup(summary(fixture_data(), './'), 'html.parser')
        counts = Counter(node['id'] for node in page.select('[id]'))
        self.assertEqual({key: value for key, value in counts.items() if value > 1}, {})

    def test_full_unresolved_page_register_still_owns_its_research_block(self):
        html = unresolved_register(fixture_data(), './')
        self.assertEqual(html.count('id="no-line-research"'), 1)
        self.assertIn('Limitations that apply to every row above', html)


if __name__ == '__main__':
    unittest.main()
