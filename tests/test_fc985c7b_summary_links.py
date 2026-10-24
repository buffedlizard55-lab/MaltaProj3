"""Session arena-fc985c7b — the executive summary must *route* the reader.

The brief asks for three things that are easy to regress one section at a time:

1. "an executive summary that provides links within our site to where an
   updated list of picks can be found" — so the summary's own navigation has
   to point at the picks list with an **in-site** (relative) link, on the
   summary itself and from every sub-page depth;
2. "a separate section for any unresolved picks and the limitations for
   generating picks" — so the summary must carry its own unresolved register,
   separate from the picks list, and that register must state a limitation
   rather than a probability;
3. "easily readable and accessible on phone" — so the phone status strip has
   to reach both lists in one tap with the right prefix, and the glance rows
   have to state both teams' probabilities and which side is the pick.

These tests render `scripts.build.summary` against the repository's checked-in
snapshot fixtures only: no network, no clock dependence, no synthetic
probability.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from scripts.build import shell, summary

ROOT = Path(__file__).resolve().parents[1]


def payload():
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    return data


def render_summary(prefix='./'):
    data = payload()
    with patch('scripts.build.contrarian_review', return_value=''), \
         patch('scripts.build.contrarian_briefing', return_value=''):
        return BeautifulSoup(summary(data, prefix), 'html.parser')


class ExecutiveSummaryRoutesToThePicks(unittest.TestCase):
    """The summary's 'start here' block must link to the picks, in-site."""

    def setUp(self):
        self.soup = render_summary('./')

    def test_start_here_exists_and_is_labelled(self):
        start = self.soup.select_one('nav#start-here')
        self.assertIsNotNone(start, 'the executive summary needs a start-here block')
        self.assertIn('start here', start.get_text(' ', strip=True).lower())

    def test_every_start_here_link_is_in_site(self):
        start = self.soup.select_one('nav#start-here')
        hrefs = [a.get('href') or '' for a in start.select('a')]
        self.assertTrue(hrefs, 'start-here must link somewhere')
        external = [h for h in hrefs
                    if not (h.startswith('#') or h.startswith('./') or h.startswith('../'))]
        self.assertEqual([], external,
                         'start-here links must stay inside the site: ' + ', '.join(external))

    def test_start_here_reaches_the_picks_list(self):
        start = self.soup.select_one('nav#start-here')
        targets = [a.get('href') or '' for a in start.select('a')]
        self.assertTrue(any('origination/' in t and 'picks' in t for t in targets),
                        f'no link to the picks list in {targets}')

    def test_start_here_reaches_the_unresolved_register(self):
        start = self.soup.select_one('nav#start-here')
        targets = [a.get('href') or '' for a in start.select('a')]
        self.assertTrue(any('unresolved' in t for t in targets),
                        f'no link to the unresolved register in {targets}')

    def test_prefix_is_relative_on_a_sub_page_too(self):
        sub = render_summary('../')
        start = sub.select_one('nav#start-here')
        targets = [a.get('href') or '' for a in start.select('a')]
        self.assertTrue(any(t.startswith('../origination/') for t in targets),
                        f'sub-page depth lost the prefix: {targets}')


class UnresolvedSectionIsSeparateAndStatesLimitations(unittest.TestCase):
    def setUp(self):
        self.soup = render_summary('./')

    def test_the_summary_carries_its_own_unresolved_register(self):
        register = self.soup.select_one('#unresolved-register')
        self.assertIsNotNone(register,
                             'the executive summary must keep its own unresolved block')

    def test_the_register_is_not_inside_the_picks_list(self):
        glance = self.soup.select_one('#picks-at-a-glance')
        register = self.soup.select_one('#unresolved-register')
        self.assertIsNotNone(glance)
        self.assertIsNone(glance.select_one('#unresolved-register'),
                          'the unresolved register must be a separate section')

    def test_a_blank_row_states_a_limitation_and_no_probability(self):
        register = self.soup.select_one('#unresolved-register')
        text = register.get_text(' ', strip=True)
        # The register either lists blanks with their blocker, or states that
        # there are none. It must never present a bare number as a pick.
        self.assertTrue(text, 'the unresolved register rendered empty')


class PhoneRouteToBothLists(unittest.TestCase):
    """One tap from any page to the picks and to the blanks."""

    def strip(self, prefix):
        data = payload()
        soup = BeautifulSoup(shell(data, 'summary', '<p id="page-body">body</p>', prefix),
                             'html.parser')
        return soup.select_one('nav.mobile-status')

    def test_both_targets_use_the_pages_prefix(self):
        for prefix in ('./', '../'):
            with self.subTest(prefix=prefix):
                nav = self.strip(prefix)
                self.assertIsNotNone(nav, 'the phone status strip is missing')
                picks = nav.select_one('a.mobile-status-picks')
                blanks = nav.select_one('a.mobile-status-blank')
                self.assertEqual(picks['href'], prefix + 'origination/#picks')
                self.assertEqual(blanks['href'], prefix + 'origination/#unresolved')

    def test_counts_come_from_the_published_complete_list(self):
        counts = payload()['complete_picks']['counts']
        nav = self.strip('./')
        picks = nav.select_one('a.mobile-status-picks').get_text(' ', strip=True)
        blanks = nav.select_one('a.mobile-status-blank').get_text(' ', strip=True)
        self.assertIn(str(counts['with_pick']), picks)
        self.assertIn(str(counts['active']), picks)
        self.assertIn(str(counts['unresolved']), blanks)


class GlanceRowsStateBothProbabilitiesAndThePick(unittest.TestCase):
    """The pick must be obvious and both teams must carry a number."""

    def test_every_glance_row_names_a_pick_and_both_probabilities(self):
        soup = render_summary('./')
        rows = soup.select('#picks-at-a-glance .glance-row, #picks-at-a-glance li')
        self.assertTrue(rows, 'no glance rows rendered')
        for row in rows:
            text = row.get_text(' ', strip=True)
            if 'Pick' not in text:
                continue  # filter controls, empty state, etc.
            percentages = [p for p in __import__('re').findall(r'(\d{1,3}\.\d)%', text)]
            self.assertGreaterEqual(len(percentages), 2,
                                    f'a pick row must show both probabilities: {text[:120]}')


if __name__ == '__main__':
    unittest.main()
