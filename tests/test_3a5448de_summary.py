"""arena-3a5448de: the executive summary has ONE unresolved section title.

The summary used to render "Unresolved picks & limitations" twice — the
separate register near the top and a featured-method table near the bottom —
with different counts, and phone shortcuts pointed at both. These tests pin
the single-register contract: exactly one H2 carries that title, every
summary shortcut for unresolved picks lands on it, and the bottom section is
labelled as the featured-method audit trail that feeds it.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from scripts.build import summary

ROOT = Path(__file__).resolve().parents[1]


class SingleUnresolvedRegisterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT / 'data/latest.json').read_text())
        origination = json.loads((ROOT / 'data/origination.json').read_text())
        data['complete_picks'] = origination
        data['_twc_day4'] = {'matches': [], 'not_in_hotspawn_snapshot': [], 'lines': {}}
        with patch('scripts.build.contrarian_review', return_value=''), \
             patch('scripts.build.contrarian_briefing', return_value=''):
            cls.soup = BeautifulSoup(summary(data, './'), 'html.parser')

    def test_exactly_one_h2_carries_the_unresolved_title(self):
        titles = [h.get_text(' ', strip=True) for h in self.soup.select('h2')]
        self.assertEqual(titles.count('Unresolved picks & limitations'), 1,
                         f'H2 titles were: {titles}')

    def test_bottom_section_is_the_featured_method_audit_trail(self):
        section = self.soup.select_one('#unresolved')
        self.assertIsNotNone(section)
        self.assertEqual(section.select_one('h2').get_text(' ', strip=True),
                         'Featured-method gaps, before research fallback')
        self.assertIn('register above is the current answer',
                      section.get_text(' ', strip=True))

    def test_summary_shortcuts_land_on_the_canonical_register(self):
        register_hrefs = [a['href'] for a in self.soup.select(
            '.hero a[href="#unresolved-register"], .briefing-links a[href="#unresolved-register"]')]
        self.assertGreaterEqual(len(register_hrefs), 2)
        self.assertIsNotNone(self.soup.select_one('#unresolved-register'))


if __name__ == '__main__':
    unittest.main()
