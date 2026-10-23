"""Session arena-7c0e457b — the phone-first executive summary.

Measured on the built site at 390x844 before this session: the page was 29,667
px tall, the separate *Unresolved picks & limitations* register started at
9,618 px and the hero at 16,428 px. Eight sessions of dated reviews and audit
trails sat between the picks and the rest of the page. Nothing was wrong with
the content; it was simply all open at once.

This session changed the presentation only:

* the register now precedes the live-gap cards (the brief asks for a separate
  register of unpriced fixtures, so it is the second block a phone reader
  reaches);
* dated reviews, research trails and the per-surface status sweeps are
  ``<details class="fold">`` blocks, closed by default, one tap from the same
  text and the same ``#anchor`` (``assets/scout.js`` opens an enclosing block
  when a deep link points inside it).

These tests pin the contract that makes that safe: the folded markup is real
``<details>``, it is closed, the ids and headings survive, the reading order is
picks -> register -> gaps -> everything else, and nothing that used to be
published has been dropped. They also pin the near-time badge added with the
7C-1 source work: a price whose provider clock disagrees with Hotspawn's must
say so on the row, in both clocks, and never silently look exact.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import (basis_badge, fold_close, fold_open, glance,
                           load_no_line_research, near_badge, near_note,
                           summary)
from scripts.contrarian import derive_context, load_review

ROOT = Path(__file__).resolve().parents[1]

#: Folds the executive summary is expected to render from the checked-in data
#: set. ``fold-twc``/``fold-twc-day4`` only appear when a dated review record is
#: loaded, and ``fold-probe`` only when the session source matrix has surfaces.
EXPECTED_FOLDS = (
    'fold-metrics', 'fold-contrarian', 'fold-audit', 'fold-fallback',
    'fold-watchlist', 'fold-no-line', 'fold-line-sources', 'fold-live-gaps',
    'fold-researched', 'fold-no-line-research',
)

#: Anchors that other pages and the summary's own navigation link to. They must
#: keep resolving inside the document even though they now sit in a fold.
DEEP_LINK_TARGETS = (
    'contrarian', 'upset-watchlist', 'unresolved', 'no-line-register',
    'line-sources', 'live-coverage-gap-list', 'unresolved-register',
    'picks-at-a-glance', 'start-here', 'next-matches-section',
)


def full_data():
    """The summary's input, assembled the way ``build`` assembles it.

    Tests that render the summary need the same private keys the real build
    attaches (complete picks, fallbacks, the dated sweeps, the contrarian
    context), otherwise the folded blocks would be empty and this suite would
    prove nothing about the content that survived.
    """
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    data['fallbacks'] = {str(r['id']): r for r in data['complete_picks'].get('matches') or []
                         if r.get('origination')}
    data['_contrarian'] = derive_context(data, load_review(ROOT / 'data/contrarian.json'))
    for key, rel in (('_live_coverage', 'research/9fd5fbf1/live-coverage.json'),
                     ('_line_sources', 'research/fbdc97d6/line-sources.json'),
                     ('_session_probe', 'research/4c972a51/source-probe.json'),
                     ('_no_line_research', 'research/fd99abd9/line-source-research.json')):
        path = ROOT / 'data' / rel
        if not path.exists():
            continue
        if rel.endswith('line-source-research.json'):
            data['_no_line_research'] = load_no_line_research(ROOT / 'data')
        else:
            data[key] = json.loads(path.read_text())
    return data


class FoldMarkupTests(unittest.TestCase):
    def test_a_fold_is_a_closed_details_block_with_a_labelled_summary(self):
        html = fold_open('fold-x', 'Dated review', 'Background', 'Two rows') + 'body' + fold_close()
        soup = BeautifulSoup(html, 'html.parser')
        details = soup.find('details')
        self.assertIsNotNone(details)
        self.assertEqual(details['class'], ['fold'])
        self.assertEqual(details['id'], 'fold-x')
        self.assertFalse(details.has_attr('open'), 'a background block must start closed')
        summary_el = details.find('summary', recursive=False)
        self.assertIsNotNone(summary_el)
        self.assertEqual(summary_el.select_one('.fold-kicker').get_text(), 'Background')
        self.assertEqual(summary_el.select_one('strong').get_text(), 'Dated review')
        self.assertEqual(summary_el.select_one('.fold-hint').get_text(), 'Two rows')
        self.assertEqual(summary_el.select_one('.fold-action').get_text(), 'Open')
        self.assertEqual(details.select_one('.fold-body').get_text(strip=True), 'body')

    def test_fold_text_is_escaped(self):
        html = fold_open('fold-"x', '<script>alert(1)</script>', '<b>k</b>', '')
        self.assertNotIn('<script>', html)
        self.assertNotIn('<b>k</b>', html)
        self.assertNotIn('fold-"x"', html)

    def test_close_balances_the_body_div(self):
        html = fold_open('a', 't', 'k') + fold_close()
        self.assertEqual(html.count('<div'), 1)
        self.assertEqual(html.count('</div>'), 1)
        self.assertTrue(html.rstrip().endswith('</details>'))


class SummaryFoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = summary(full_data(), './')
        cls.soup = BeautifulSoup(cls.html, 'html.parser')

    def test_expected_background_blocks_are_present_and_closed(self):
        for ident in EXPECTED_FOLDS:
            with self.subTest(fold=ident):
                block = self.soup.find('details', id=ident)
                self.assertIsNotNone(block, f'{ident} is missing from the summary')
                self.assertFalse(block.has_attr('open'), f'{ident} must start closed')
                self.assertGreater(len(block.select_one('.fold-body').get_text(strip=True)), 40,
                                   f'{ident} must still carry its content, not just a heading')

    def test_no_details_block_in_the_summary_is_open_on_load(self):
        for block in self.soup.find_all('details'):
            with self.subTest(fold=block.get('id')):
                self.assertFalse(block.has_attr('open'))

    def test_every_deep_link_target_still_resolves(self):
        for ident in DEEP_LINK_TARGETS:
            with self.subTest(target=ident):
                self.assertEqual(len(self.soup.find_all(id=ident)), 1,
                                 f'#{ident} must exist exactly once')

    def test_folded_sections_keep_their_headings_for_navigation(self):
        for ident, heading in (('fold-contrarian', 'chart-heading'),
                               ('fold-audit', 'unresolved'),
                               ('fold-fallback', None)):
            with self.subTest(fold=ident):
                block = self.soup.find('details', id=ident)
                self.assertTrue(block.find(['h2', 'h3']), f'{ident} lost its heading')

    def test_reading_order_is_picks_then_register_then_gaps(self):
        order = ['start-here', 'picks-at-a-glance', 'unresolved-register',
                 'live-coverage-gaps', 'next-matches-section']
        positions = [self.html.find(f'id="{ident}"') for ident in order]
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, sorted(positions), 'reading order changed')

    def test_the_register_still_follows_its_required_banner(self):
        # Session 941ff196 pinned the banner above the register; the reorder in
        # this session moved the register above the live-gap cards only.
        self.assertGreater(self.html.find('id="unresolved-register"'),
                           self.html.find('exec-banner'))
        self.assertGreater(self.html.find('id="unresolved-register"'),
                           self.html.find('id="picks-at-a-glance"'))

    def test_folded_pages_still_publish_their_counts(self):
        register = self.soup.find('section', id='unresolved-register')
        self.assertIn('No unresolved fixtures', register.get_text(' ', strip=True))
        gaps = self.soup.find('section', id='live-coverage-gaps')
        # The headline and the dated comparison stay open; only the card list is
        # folded, and it stays in the document with its per-fixture links.
        self.assertTrue(gaps.select_one('details.fold summary'))
        self.assertIsNotNone(gaps.select_one('details.fold .coverage-gap-row'))
        intro = gaps.select_one('.section-intro')
        self.assertIsNotNone(intro)
        self.assertNotIn(intro, gaps.select_one('details.fold').descendants)

    def test_nothing_that_was_published_disappeared(self):
        # A fold hides text from the eye, never from the document: the sentence
        # that opens each block must still be reachable by search and by a
        # screen reader that expands it.
        needed = ['Contrarian', 'Researched fallback picks',
                  'Fixtures without a betting line', 'Line sources checked']
        text = self.html
        for phrase in needed:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


class NearTimePresentationTests(unittest.TestCase):
    ANALYSIS = {
        'method': 'market', 'label': 'Market-implied estimate', 'source': 'Polymarket',
        'probabilities': [0.62, 0.38], 'binding': 'near-time', 'start_delta_sec': 3600,
        'hotspawn_start': '2026-10-23T11:00:00Z', 'provider_start': '2026-10-23T12:00:00Z',
        'source_url': 'https://polymarket.com/event/cs2-x',
    }

    def test_exact_quote_carries_no_near_marker(self):
        self.assertEqual(near_badge({'binding': 'exact'}), '')
        self.assertEqual(near_note({'binding': 'exact'}), '')

    def test_missing_binding_is_treated_as_exact(self):
        self.assertEqual(near_badge({}), '')
        self.assertEqual(near_note(None), '')

    def test_near_quote_is_badged_and_prints_both_clocks(self):
        badge = near_badge(self.ANALYSIS)
        self.assertIn('Start time differs', badge)
        self.assertIn('badge near', badge)
        note = near_note(self.ANALYSIS)
        self.assertIn('2026-10-23T12:00:00Z', note)
        self.assertIn('2026-10-23T11:00:00Z', note)
        self.assertIn('60 min', note)
        self.assertIn('later', note)
        self.assertIn('Polymarket', note)

    def test_direction_reads_from_the_signed_delta(self):
        # delta = provider start - Hotspawn start (scripts/gap_lines.classify).
        earlier = dict(self.ANALYSIS, start_delta_sec=-7200, provider_start='2026-10-23T09:00:00Z')
        self.assertIn('earlier', near_note(earlier))
        self.assertIn('120 min', near_note(earlier))

    def test_a_near_quote_without_clocks_never_invents_one(self):
        note = near_note({'binding': 'near-time', 'source': 'Unibet'})
        self.assertIn('different start time', note)
        self.assertNotIn('2026', note)

    def test_basis_badge_adds_the_near_marker_only_for_money_rows(self):
        self.assertIn('badge near', basis_badge(self.ANALYSIS, False))
        self.assertNotIn('badge near', basis_badge(dict(self.ANALYSIS, method='model'), True))


class GlanceNearRowTests(unittest.TestCase):
    """The glance row is where a phone reader meets the quote first."""

    def test_a_near_time_pick_shows_both_clock_values_in_the_index(self):
        data = full_data()
        match = next(m for m in data['matches']
                     if m['availability'] in {'open', 'locked', 'unknown_lock'}
                     and m['analysis'])
        analysis = dict(match['analysis'])
        analysis.update({'binding': 'near-time', 'start_delta_sec': 3600,
                         'hotspawn_start': match['starts_at'],
                         'provider_start': '2026-10-23T12:00:00Z'})
        match['analysis'] = analysis
        match['pick_index'] = 0
        html = glance(data, './')
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find(attrs={'data-glance-id': match['id']})
        self.assertIsNotNone(row)
        self.assertIn('Start time differs', row.get_text(' ', strip=True))
        self.assertIn('2026-10-23T12:00:00Z', row.get_text(' ', strip=True))
        self.assertIn(match['starts_at'], row.get_text(' ', strip=True))
        self.assertTrue(row.select_one('.glance-near'))


if __name__ == '__main__':
    unittest.main()
