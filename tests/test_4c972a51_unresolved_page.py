"""Session 4c972a51 — the dedicated unresolved page and the picks-page arithmetic.

Two rendering contracts the brief asks for:

* a separate place for every fixture without a pick, with its blocker and the
  limitations behind it, reachable from the executive summary and the phone
  navigation;
* a match-picks header whose counts add up — the header used to say "33 of 33"
  while the sentence beside it added the featured-only counters (11 + 12 = 23).

These tests build pages from the repository's own snapshot. They contact no
source, invent no probability and change no pick.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import build as build_module
from scripts.build import PAGES, exec_banner, picks, session_probe_block, summary, unresolved_page

ROOT = Path(__file__).resolve().parents[1]


def inventory():
    return json.loads((ROOT / 'data/latest.json').read_text())


def with_complete(data=None):
    data = copy.deepcopy(data or inventory())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    data['fallbacks'] = {str(r['id']): r for r in data['complete_picks'].get('matches') or []
                         if r.get('origination')}
    data['complete_picks'].setdefault('counts', {})
    counts = data['complete_picks']['counts']
    rows = data['complete_picks'].get('matches') or []
    counts.setdefault('active', len(rows))
    counts.setdefault('resolved', sum(1 for r in rows if r.get('origination')))
    counts.setdefault('unresolved', sum(1 for r in rows if not r.get('origination')))
    counts.setdefault('with_pick', sum(1 for r in rows if r.get('pick_index') is not None))
    data.setdefault('flags', [])
    return data


class UnresolvedPageContract(unittest.TestCase):
    def setUp(self):
        self.data = with_complete()
        self.page = unresolved_page(self.data, './')

    def test_the_page_is_a_first_class_site_page(self):
        self.assertIn('unresolved', PAGES)
        label, path, _ = PAGES['unresolved']
        self.assertEqual(path, 'unresolved/index.html')
        self.assertIn('Unresolved', label)

    def test_navigation_and_summary_link_the_page(self):
        shell = build_module.shell(self.data, 'summary', summary(self.data, './'), './')
        soup = BeautifulSoup(shell, 'html.parser')
        nav_hrefs = {a.get('href') for a in soup.select('.mobile-nav a')}
        self.assertIn('./unresolved/', nav_hrefs)
        self.assertIn('./unresolved/', {a.get('href') for a in soup.select('.sidebar a')})
        banner_hrefs = {a.get('href') for a in soup.select('.exec-banner a')}
        self.assertIn('./unresolved/', banner_hrefs)
        site_map = {a.get('href') for a in soup.select('#site-map a')}
        self.assertIn('./unresolved/', site_map)

    def test_status_cards_are_the_published_counts(self):
        counts = self.data['complete_picks']['counts']
        text = BeautifulSoup(self.page, 'html.parser').get_text(' ', strip=True)
        self.assertIn(str(counts['active']), text)
        self.assertIn('No pick', text)
        self.assertIn('No side', text)
        self.assertIn(str(counts['unresolved']), text)

    def test_every_blank_fixture_is_named_with_its_reason(self):
        blank_rows = [m for m in self.data['complete_picks']['matches'] if not m.get('origination')]
        soup = BeautifulSoup(self.page, 'html.parser')
        register = soup.select_one('#unresolved-register')
        self.assertIsNotNone(register)
        for row in blank_rows:
            self.assertIn(f'id="unresolved-summary-{row["id"]}"', str(register))
        # A blank row must link its Hotspawn fixture and at least one source tried.
        for card in register.select('.unresolved-summary-card'):
            self.assertTrue(card.select('a[href^="https://"]'), card.get('id'))

    def test_ladder_names_the_tie_break_rule(self):
        text = BeautifulSoup(self.page, 'html.parser').get_text(' ', strip=True)
        self.assertIn('exactly 50/50', text)
        self.assertIn('published order', text)
        self.assertIn('never a probability', text)

    def test_page_without_probe_data_still_renders(self):
        data = copy.deepcopy(self.data)
        data.pop('_session_probe', None)
        page = unresolved_page(data, './')
        self.assertIn('unresolved-register', page)
        self.assertNotIn('id="source-matrix"', page)


class SourceMatrixContract(unittest.TestCase):
    def data(self):
        data = with_complete()
        payload = json.loads((ROOT / 'data/research/4c972a51/source-probe.json').read_text())
        data['_session_probe'] = payload
        return data, payload

    def test_every_probed_surface_is_published_with_its_link(self):
        data, payload = self.data()
        html = session_probe_block(data, './')
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('.probe-source')
        self.assertEqual(len(items), len(payload['surfaces']))
        for item in items:
            self.assertTrue(item.select_one('a[href^="https://"]'), item.get_text(' ', strip=True)[:80])

    def test_the_ladder_endpoints_and_hltv_are_published(self):
        data, payload = self.data()
        names = {s['name'] for s in payload['surfaces']}
        self.assertTrue(any('thunderpick' in n.lower() for n in names), names)
        self.assertTrue(any('hltv' in n.lower() for n in names), names)
        # The renderer must show the ladder group as soon as the probe records one,
        # independently of which probe capture is checked in.
        data['_session_probe'] = {'observed_at': '2026-10-22T07:38:14Z', 'unresolved_fixtures': 0,
                                  'surfaces': [{'name': 'THUNDERPICK api/matches', 'kind': 'ladder',
                                                'url': 'https://thunderpick.io/api/matches', 'status': 200,
                                                'bytes': 4096}]}
        html = session_probe_block(data, './')
        self.assertIn('The exact endpoints the resolver calls', html)
        self.assertIn('A refusal is recorded as a source limitation',
                      BeautifulSoup(html, 'html.parser').get_text(' ', strip=True))

    def test_a_status_code_is_never_presented_as_a_price(self):
        data, _ = self.data()
        text = BeautifulSoup(session_probe_block(data, './'), 'html.parser').get_text(' ', strip=True).lower()
        for forbidden in ('odds of', 'probability of', 'implied probability'):
            self.assertNotIn(forbidden, text)


class PicksHeaderArithmetic(unittest.TestCase):
    """The sentence beside the header must add up to the number of rows shown."""

    def test_parts_sum_to_the_displayed_rows(self):
        data = with_complete()
        html = picks(data, './')
        soup = BeautifulSoup(html, 'html.parser')
        strip = soup.select_one('.info-strip').get_text(' ', strip=True)
        chips = {b.get('data-basis'): int(b.select_one('span').get_text())
                 for b in soup.select('.filter-tabs button')}
        parts = chips['market'] + chips['model'] + chips.get('guidance', 0) + chips['unresolved']
        self.assertEqual(chips['all'], parts, chips)
        # The money count in the sentence is the displayed market count, not the
        # featured-only counter that used to make 11 + 12 leave ten rows unaccounted.
        self.assertIn(f"{chips['market']} come from an external market", strip)
        if chips['model']:
            self.assertIn(f"{chips['model']} from a labelled research model", strip)

    def test_header_count_is_the_displayed_row_count(self):
        data = with_complete()
        soup = BeautifulSoup(picks(data, './'), 'html.parser')
        text = soup.select_one('.info-strip').get_text(' ', strip=True)
        shown = int(soup.select('.filter-tabs button')[0].select_one('span').get_text())
        self.assertIn(f'{shown} of {shown} matches below carry a pick', text)


if __name__ == '__main__':
    unittest.main()
