"""Session ee27e097 — the separate unresolved/limitations page and its phone links.

The brief asks for two things this file pins:

* a separate section for the picks that cannot be resolved the same way as the
  featured picks, with the limitations that stopped a price, and
* an executive summary that makes an updated picks list and that register easy
  to reach on a phone.

Both are properties of the rendered HTML, not of the copy. The fixtures are the
repository's own retained snapshot; nothing here writes production data or
invents a probability.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import PAGES, shell, summary, unresolved_page

ROOT = Path(__file__).resolve().parents[1]


def payload():
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    return data


class UnresolvedPageContract(unittest.TestCase):
    def test_page_is_registered_with_its_own_address(self):
        self.assertIn('unresolved', PAGES)
        self.assertEqual(PAGES['unresolved'][1], 'unresolved/index.html')

    def test_page_renders_the_register_and_both_gap_counts(self):
        data = payload()
        counts = data['complete_picks']['counts']
        soup = BeautifulSoup(unresolved_page(data, '../'), 'html.parser')
        register = soup.select_one('#unresolved-register')
        self.assertIsNotNone(register)
        # The register is the same renderer the summary uses, so the no-line
        # section and the dated source records must be present here too.
        self.assertIsNotNone(soup.select_one('#no-line-register'))
        intro = soup.select_one('.info-strip').get_text(' ', strip=True)
        self.assertIn(str(counts['unresolved']), intro)
        model = counts.get('model')
        if model is not None:
            self.assertIn(str(model), intro)

    def test_page_does_not_add_a_probability_of_its_own(self):
        data = payload()
        html = unresolved_page(data, '../')
        # Every percentage rendered on this page must already exist in the
        # published origination record, compared as a rounded string.
        published = set()
        for match in data['complete_picks'].get('matches') or []:
            for p in ((match.get('origination') or {}).get('probabilities') or []):
                published.add(f'{float(p) * 100:.1f}')
        import re
        shown = set(re.findall(r'([0-9]+\.[0-9])%', html))
        self.assertTrue(shown.issubset(published),
                        f'unpublished percentages rendered: {sorted(shown - published)}')

    def test_page_links_the_pick_list_and_the_review(self):
        html = unresolved_page(payload(), '../')
        self.assertIn('href="../origination/#picks"', html)
        self.assertIn('href="../review/"', html)
        self.assertIn('href="../methodology/"', html)


class ExecutiveSummaryLinksTheRegister(unittest.TestCase):
    def test_summary_links_the_dedicated_page_from_the_start_here_bar_and_hero(self):
        data = payload()
        soup = BeautifulSoup(summary(data, './'), 'html.parser')
        start = soup.select_one('#start-here')
        self.assertIsNotNone(start)
        hrefs = {a['href'] for a in start.select('a')}
        self.assertIn('./unresolved/', hrefs)
        self.assertIn('./origination/#picks', hrefs)
        hero_links = {a['href'] for a in soup.select('.hero-actions a')}
        self.assertIn('./unresolved/', hero_links)

    def test_summary_register_heading_links_the_page_without_self_linking(self):
        data = payload()
        soup = BeautifulSoup(summary(data, './'), 'html.parser')
        heading = soup.select_one('#unresolved-register .section-heading')
        self.assertIsNotNone(heading)
        self.assertIn('./unresolved/', {a['href'] for a in heading.select('a')})
        # The dedicated page must not link to itself from its own heading.
        page = BeautifulSoup(unresolved_page(data, '../'), 'html.parser')
        page_heading = page.select_one('#unresolved-register .section-heading')
        self.assertNotIn('../unresolved/', {a['href'] for a in page_heading.select('a')})


class PhoneStatusStripCountsBothGaps(unittest.TestCase):
    def test_no_line_count_is_shown_beside_the_unresolved_count(self):
        data = payload()
        counts = data['complete_picks']['counts']
        money = sum(counts.get(k) or 0 for k in ('market', 'bookmaker', 'consensus', 'reference'))
        no_line = max(0, counts['resolved'] - money)
        soup = BeautifulSoup(shell(data, 'summary', '<p id="page-body">body</p>', './'), 'html.parser')
        blank = soup.select_one('nav.mobile-status a.mobile-status-blank')
        self.assertIsNotNone(blank)
        self.assertEqual(blank['href'], './origination/#unresolved')
        text = blank.get_text(' ', strip=True)
        self.assertIn(str(counts['unresolved']), text)
        self.assertIn(f'{no_line} no line', text)

    def test_falls_back_without_a_complete_list(self):
        data = json.loads((ROOT / 'data/latest.json').read_text())
        soup = BeautifulSoup(shell(data, 'summary', '<p id="page-body">body</p>', './'), 'html.parser')
        blank = soup.select_one('nav.mobile-status a.mobile-status-blank')
        self.assertIn('0 no line', blank.get_text(' ', strip=True))


class NavigationReachesTheRegister(unittest.TestCase):
    def test_desktop_and_phone_navigation_include_the_page(self):
        data = payload()
        for prefix, key in (('./', 'summary'), ('../', 'review')):
            with self.subTest(prefix=prefix):
                soup = BeautifulSoup(shell(data, key, '<p id="page-body">body</p>', prefix), 'html.parser')
                self.assertIn(f'{prefix}unresolved/', {a['href'] for a in soup.select('aside nav a')})
                self.assertIn(f'{prefix}unresolved/', {a['href'] for a in soup.select('nav.mobile-nav a')})


if __name__ == '__main__':
    unittest.main()
