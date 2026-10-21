"""Session 541cd43a — the phone must reach the picks and the blanks in one tap.

The brief asked for an executive summary that links to where the updated picks
live, and for the site to be obvious to use on a phone. These tests pin the
phone status strip that does that from every page, and the counts it shows:

* it links to `origination/#picks` and `origination/#unresolved` with the
  correct relative prefix on both the summary and a sub-page;
* its counts come from the published complete-picks counts (never a guess);
* it degrades to the featured snapshot counts when no complete list exists;
* the CSS shows it only on phone-width viewports.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import shell

ROOT = Path(__file__).resolve().parents[1]


def data():
    payload = json.loads((ROOT / 'data/latest.json').read_text())
    payload['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    return payload


class MobileStatusStrip(unittest.TestCase):
    def strip(self, payload, prefix='./', key='summary'):
        soup = BeautifulSoup(shell(payload, key, '<p id="page-body">body</p>', prefix), 'html.parser')
        return soup, soup.select_one('nav.mobile-status')

    def test_links_and_counts_on_the_summary(self):
        payload = data()
        counts = payload['complete_picks']['counts']
        soup, nav = self.strip(payload)
        self.assertIsNotNone(nav)
        picks = nav.select_one('a.mobile-status-picks')
        blanks = nav.select_one('a.mobile-status-blank')
        self.assertEqual(picks['href'], './origination/#picks')
        self.assertEqual(blanks['href'], './origination/#unresolved')
        self.assertIn(str(counts['with_pick']), picks.get_text(' ', strip=True))
        self.assertIn(str(counts['active']), picks.get_text(' ', strip=True))
        self.assertIn(str(counts['unresolved']), blanks.get_text(' ', strip=True))

    def test_relative_prefix_on_a_subpage(self):
        soup, nav = self.strip(data(), prefix='../', key='review')
        self.assertEqual(nav.select_one('a.mobile-status-picks')['href'], '../origination/#picks')
        self.assertEqual(nav.select_one('a.mobile-status-blank')['href'], '../origination/#unresolved')

    def test_strip_precedes_the_page_body(self):
        soup, nav = self.strip(data())
        html = str(soup)
        self.assertLess(html.index('mobile-status'), html.index('id="page-body"'))

    def test_falls_back_to_featured_counts_without_a_complete_list(self):
        payload = json.loads((ROOT / 'data/latest.json').read_text())
        payload.pop('complete_picks', None)
        _soup, nav = self.strip(payload)
        expected = payload['counts']['upcoming'] - payload['counts']['unresolved']
        self.assertIn(str(expected), nav.select_one('a.mobile-status-picks').get_text(' ', strip=True))
        self.assertIn(str(payload['counts']['unresolved']),
                      nav.select_one('a.mobile-status-blank').get_text(' ', strip=True))

    def test_css_is_phone_only(self):
        css = (ROOT / 'assets/scout.css').read_text()
        self.assertIn('.mobile-status{display:none}', css)
        phone = re.search(r'@media\(max-width:700px\)\{(.*?)\n\}', css, re.S)
        self.assertIsNotNone(phone)
        self.assertIn('.mobile-status{display:flex', css)

    def test_strip_carries_no_probability_claim(self):
        _soup, nav = self.strip(data())
        text = nav.get_text(' ', strip=True).lower()
        self.assertNotIn('%', text)
        self.assertNotIn('odds', text)


if __name__ == '__main__':
    unittest.main()
