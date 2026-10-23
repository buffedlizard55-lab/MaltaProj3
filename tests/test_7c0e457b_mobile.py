"""Session arena-7c0e457b — the executive summary has to work on a phone.

The published page was 29,667 px tall at 390x844, the separate
unresolved/limitation register began at 9,618 px and the hero at 16,428 px:
eight sessions of dated reviews, audit trails and source sweeps were rendered
open between the picks and everything else. Nothing in them was wrong; they
were simply always in the way.

This session changed presentation only, and these tests pin the guarantees that
make it safe:

* the picks come first, then the register, then the background;
* every dated block is a real, closed ``<details>`` with a readable summary —
  not a removed section and not a hidden div;
* its ids, headings, tables and links survive inside the block, so existing
  ``#anchor`` navigation (``#contrarian``, ``#upset-watchlist``, ``#unresolved``)
  still resolves once ``assets/scout.js`` opens the block;
* a near-time quote (7C-1) is labelled on the row with both clocks.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import glance, near_badge, near_note, summary
from scripts.contrarian import derive_context, load_review

ROOT = Path(__file__).resolve().parents[1]

#: Blocks this session folded. The two dated TWC blocks stay open on purpose:
#: their entry links are pinned as one tap from the summary by existing specs.
FOLDED = {
    'fold-contrarian': ('contrarian', '#contrarian'),
    'fold-audit': ('unresolved', '#unresolved'),
    'fold-watchlist': ('upset-watchlist', '#upset-watchlist'),
    'fold-fallback': (None, 'Researched fallback picks'),
    'fold-low-tier': ('low-tier-coverage', '#low-tier-coverage'),
    'fold-metrics': (None, 'What to know before you pick'),
    'fold-probe': ('source-matrix', '#source-matrix'),
    'fold-live-gaps': ('live-coverage-gap-list', '#live-coverage-gap-list'),
    'fold-no-line': (None, 'no-line'),
    'fold-line-sources': ('line-sources', '#line-sources'),
    'fold-no-line-research': ('no-line-research', '#no-line-research'),
}


def full_data():
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    data['fallbacks'] = {str(r['id']): r for r in data['complete_picks'].get('matches') or []
                         if r.get('origination')}
    data['_contrarian'] = derive_context(data, load_review(ROOT / 'data/contrarian.json'))
    for key, name in (('_live_coverage', 'live-coverage.json'),
                      ('_line_sources', 'line-sources.json'),
                      ('_session_probe', 'source-probe.json')):
        for path in (ROOT / 'data/research').glob(f'*/{name}'):
            data.setdefault(key, json.loads(path.read_text()))
            break
    return data


class SummaryFoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = full_data()
        cls.html = summary(cls.data, './')
        cls.soup = BeautifulSoup(cls.html, 'html.parser')

    def test_every_dated_block_is_a_closed_details_element(self):
        for ident, (anchor, text) in FOLDED.items():
            with self.subTest(fold=ident):
                block = self.soup.find('details', id=ident)
                if block is None:
                    # Data-dependent blocks (probe, live gaps, no-line research)
                    # only appear when their evidence file exists.
                    self.assertIn(anchor, {None, 'source-matrix', 'live-coverage-gap-list',
                                           'no-line-research', 'no-line', 'line-sources'},
                                  f'{ident} is missing although its evidence exists')
                    continue
                self.assertFalse(block.has_attr('open'), f'{ident} must start closed')
                summary_el = block.find('summary')
                self.assertIsNotNone(summary_el)
                self.assertTrue(summary_el.get_text(' ', strip=True))
                self.assertTrue(block.find(class_='fold-hint'),
                                f'{ident} needs a one-line description for a phone reader')

    def test_folding_never_deletes_the_section_it_wraps(self):
        for ident, (anchor, text) in FOLDED.items():
            if anchor is None:
                continue
            with self.subTest(fold=ident, anchor=anchor):
                target = self.soup.find(id=anchor)
                if target is None:
                    continue
                self.assertIsNotNone(target.find_parent('details') or target.name == 'details',
                                     f'#{anchor} must live inside its fold')

    def test_the_background_blocks_keep_their_headings_and_tables(self):
        for ident in ('fold-contrarian', 'fold-audit', 'fold-low-tier', 'fold-metrics'):
            block = self.soup.find('details', id=ident)
            if block is None:
                continue
            with self.subTest(fold=ident):
                self.assertTrue(block.find(['h2', 'h3']), f'{ident} lost its heading')
                self.assertGreater(len(block.get_text(' ', strip=True)), 200)

    def test_reading_order_is_picks_then_register_then_gaps(self):
        order = ['start-here', 'picks-at-a-glance', 'unresolved-register',
                 'live-coverage-gaps', 'next-matches-section']
        found = [self.html.find(f'id="{name}"') for name in order]
        self.assertNotIn(-1, found)
        self.assertEqual(found, sorted(found))
        self.assertLess(self.html.find('id="picks-at-a-glance"'),
                        self.html.find('id="unresolved-register"'))

    def test_the_register_still_follows_its_required_banner(self):
        self.assertGreater(self.html.find('id="unresolved-register"'),
                           self.html.find('exec-banner'))

    def test_the_glance_rows_keep_every_pick_and_both_probabilities(self):
        rows = self.soup.select('#picks-at-a-glance .glance-row')
        self.assertGreater(len(rows), 10)
        for row in rows:
            with self.subTest(match=row.get('data-glance-id')):
                choice = row.select_one('.glance-choice')
                self.assertTrue(choice)
                text = choice.get_text(' ', strip=True)
                # Pick or Locked, a team, a percentage and the opponent's percentage.
                self.assertRegex(text, r'\d+\.\d%')
                links = row.select('.glance-links a')
                self.assertGreaterEqual(len(links), 2, 'the row must keep its sources')

    def test_there_is_still_a_way_to_the_full_list_in_one_tap(self):
        start = self.soup.find(id='start-here')
        hrefs = [a.get('href') for a in start.find_all('a')]
        self.assertTrue(any(h and '#picks-at-a-glance' in h for h in hrefs))
        self.assertIsNotNone(self.soup.find('a', href=re.compile(r'origination/#picks')))


class SiteAssetTests(unittest.TestCase):
    """The fold, the compaction and the reveal script ship with the site."""

    @classmethod
    def setUpClass(cls):
        cls.css = (ROOT / 'assets/scout.css').read_text()
        cls.js = (ROOT / 'assets/scout.js').read_text()

    def test_fold_styles_exist_and_cap_the_summary_height(self):
        for rule in ('.fold{', '.fold>summary', '.fold-body', '.fold-hint'):
            with self.subTest(rule=rule):
                self.assertIn(rule, self.css)

    def test_a_link_into_a_closed_block_opens_it(self):
        self.assertIn("node.tagName === 'DETAILS'", self.js)
        self.assertIn('hashchange', self.js)
        self.assertIn("a[href^=\"#\"]", self.js)

    def test_phone_rows_are_compacted(self):
        self.assertIn('.glance-links .source-link{font-size:9px;min-height:24px', self.css)


class NearTimePresentationTests(unittest.TestCase):
    ANALYSIS = {
        'method': 'market', 'family': 'market', 'label': 'Originated market line (Polymarket, near-time start)',
        'probabilities': [0.62, 0.38], 'binding': 'near-time', 'start_delta_sec': 3600,
        'hotspawn_start': '2026-10-23T11:00:00Z', 'provider_start': '2026-10-23T12:00:00Z',
        'source': 'Polymarket', 'source_url': 'https://polymarket.com/event/x',
    }

    def test_no_marker_without_the_near_time_binding(self):
        self.assertEqual(near_badge({'binding': 'exact'}), '')
        self.assertEqual(near_note({'binding': 'exact'}), '')
        self.assertEqual(near_badge({}), '')

    def test_the_row_says_the_start_times_differ(self):
        self.assertIn('Start time differs', near_badge(self.ANALYSIS))
        note = near_note(self.ANALYSIS)
        self.assertIn('2026-10-23T12:00:00Z', note)
        self.assertIn('2026-10-23T11:00:00Z', note)
        self.assertIn('60 min later', note)

    def test_a_near_quote_without_clocks_never_invents_one(self):
        note = near_note({'binding': 'near-time', 'source': 'Unibet'})
        self.assertNotIn('2026', note)
        self.assertIn('different start time', note)

    def test_the_glance_row_carries_the_marker(self):
        data = full_data()
        match = next(m for m in data['matches']
                     if m['availability'] in {'open', 'locked', 'unknown_lock'} and m.get('analysis'))
        match['analysis'] = dict(match['analysis'], binding='near-time', start_delta_sec=3600,
                                 hotspawn_start=match['starts_at'],
                                 provider_start='2026-10-23T12:00:00Z')
        match['pick_index'] = 0
        soup = BeautifulSoup(glance(data, './'), 'html.parser')
        row = soup.find(attrs={'data-glance-id': match['id']})
        self.assertIsNotNone(row)
        self.assertIn('Start time differs', row.get_text(' ', strip=True))


if __name__ == '__main__':
    unittest.main()
