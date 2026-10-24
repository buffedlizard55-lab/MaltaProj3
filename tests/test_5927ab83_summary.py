"""Session 5927ab83: executive-summary anchor and every-row phone contracts."""
from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import (
    load_direct_observations,
    load_no_line_research,
    summary,
    unresolved_page,
)

ROOT = Path(__file__).resolve().parents[1]


class UniqueExecutiveSummaryResearchAnchor(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/latest.json').read_text())
        self.data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
        self.data['_no_line_research'] = load_no_line_research(ROOT / 'data')
        self.data['_direct_observations'] = load_direct_observations(ROOT / 'data')
        self.assertIsNotNone(self.data['_no_line_research'])

    def assert_unique_ids(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        counts = Counter(tag['id'] for tag in soup.find_all(id=True))
        duplicates = {key: value for key, value in counts.items() if value > 1}
        self.assertEqual(duplicates, {})
        self.assertEqual(counts['no-line-research'], 1)
        self.assertEqual(counts['unresolved-register'], 1)
        self.assertEqual(counts['no-line-register'], 1)

    def test_summary_renders_the_dated_research_exactly_once(self):
        self.assert_unique_ids(summary(self.data, './'))

    def test_full_unresolved_page_keeps_its_own_single_research_anchor(self):
        self.assert_unique_ids(unresolved_page(self.data, './'))


if __name__ == '__main__':
    unittest.main()
