"""Session arena-3877d48d: every-match picks, the fallback register and price precision.

The brief asks for (1) a pick for every Hotspawn CS2 match, including the low-tier cards the
featured market does not cover, (2) a separate, published section for the matches that cannot be
resolved the same way as the featured picks, with the limitations of each method, and (3) that
section to be reachable from the executive summary on a phone.

These tests read the built data and the rendered HTML. They never invent a probability: every
assertion is about presentation, linking and the absence of a hard-coded number.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import (
    MONEY_METHODS,
    _fallback_limits,
    _fallback_rows,
    decimal_price,
    fallback_register,
    observed_price_label,
    research_verification_block,
    start_here,
    summary,
    unresolved_page,
)

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / 'data' / 'research' / '3877d48d'


def inventory():
    """The checked-in replay fixture plus its complete-picks record."""
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    data['_twc_day4'] = {'matches': [], 'not_in_hotspawn_snapshot': [], 'lines': {}}
    return data


def fallback_methods_in(data):
    _, rows = _fallback_rows(data)
    return {(m.get('origination') or {}).get('method') for m in rows}


class DecimalPriceTests(unittest.TestCase):
    def test_a_near_lock_price_keeps_its_third_decimal(self):
        self.assertEqual(decimal_price(1.001), '1.001')
        self.assertEqual(decimal_price(1.004), '1.004')

    def test_ordinary_prices_are_unchanged(self):
        self.assertEqual(decimal_price(1.38), '1.38')
        self.assertEqual(decimal_price(2.9), '2.90')
        self.assertEqual(decimal_price(12.0), '12.00')

    def test_the_rendered_line_no_longer_claims_one_point_zero_zero(self):
        label = observed_price_label({'method': 'bookmaker', 'quotes': [{'odds': [1.001, 12.0]}]})
        self.assertEqual(label, 'line 1.001 / 12.00')
        self.assertNotIn('line 1.00 /', label)

    def test_normal_bookmaker_rows_keep_two_decimals(self):
        label = observed_price_label({'method': 'bookmaker', 'quotes': [{'odds': [1.38, 2.9]}]})
        self.assertEqual(label, 'line 1.38 / 2.90')


class FallbackRegisterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = inventory()
        cls.html = fallback_register(cls.data, '../')
        cls.soup = BeautifulSoup(cls.html, 'html.parser')

    def test_the_register_exists_once_with_its_own_id(self):
        self.assertEqual(self.html.count('id="fallback-register"'), 1)

    def test_only_money_backed_fallback_methods_are_listed(self):
        self.assertTrue(self.soup.select('.fallback-card'))
        self.assertEqual(fallback_methods_in(self.data), {'bookmaker'})
        # Research models and wide-book guidance keep their own register, so no
        # fixture appears twice on one page.
        self.assertTrue(self.soup.select('a[href="#no-line-register"]') or not self.data)

    def test_every_card_states_both_probabilities_and_a_limit(self):
        for card in self.soup.select('.fallback-card'):
            self.assertTrue(card.select_one('.glance-prob'), card.get('id'))
            self.assertTrue(card.select_one('.glance-other'), card.get('id'))
            self.assertTrue(card.select_one('.fallback-limits li'), card.get('id'))

    def test_every_card_links_an_official_source_and_its_full_trail(self):
        for card in self.soup.select('.fallback-card'):
            external = [a['href'] for a in card.select('a.source-link')]
            self.assertTrue(external, card.get('id'))
            self.assertTrue(all(url.startswith('https://') for url in external), external)
            trail = [a['href'] for a in card.select('a.internal-link')]
            self.assertTrue(any('origination/#match-' in href for href in trail), trail)

    def test_a_market_row_is_not_listed(self):
        _, rows = _fallback_rows(self.data)
        market = [m['id'] for m in (self.data['complete_picks'].get('matches') or [])
                  if (m.get('origination') or {}).get('method') == 'market']
        self.assertTrue(market)
        for match_id in market:
            self.assertNotIn(f'id="fallback-card-{match_id}"', self.html)
            self.assertNotIn(f'id="fallback-{match_id}"', self.html)

    def test_no_register_is_rendered_when_every_pick_is_a_featured_market_line(self):
        data = inventory()
        for m in data['complete_picks']['matches']:
            if m.get('origination'):
                m['origination']['method'] = 'market'
        self.assertEqual(fallback_register(data, './'), '')

    def test_the_register_is_linked_from_the_pick_index_not_a_sixth_jump_tile(self):
        # A sixth jump tile pushed the first pick below the phone fold, so the
        # link lives in the pick index's own intro sentence.
        data = inventory()
        html = summary(data, './')
        self.assertIn('#fallback-register', html[html.index('id="picks-at-a-glance"'):html.index('id="fallback-register"')])
        self.assertNotIn('#fallback-register', start_here(data, './'))
        for m in data['complete_picks']['matches']:
            if m.get('origination'):
                m['origination']['method'] = 'market'
        self.assertEqual(fallback_register(data, './'), '')
        self.assertNotIn('#fallback-register', summary(data, './'))


class NearLockLimitationTests(unittest.TestCase):
    def _match(self):
        return {'id': '1082860', 'teams': [{'name': 'FlyQuest'}, {'name': 'Staqued'}],
                'competition': 'DFRAG Invitational 2026', 'starts_at': '2026-10-27T03:00:00Z',
                'source_url': 'https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860',
                'research': [], 'pick_index': 0}

    def test_a_sub_1_02_quote_is_labelled_as_a_near_lock(self):
        origins = {'method': 'bookmaker', 'probabilities': [0.923, 0.077],
                   'limits': [], 'limitations': [],
                   'quotes': [{'odds': [1.001, 12.0]}]}
        limits = _fallback_limits(self._match(), origins)
        self.assertTrue(any('Near-lock' in text for text in limits), limits)

    def test_an_ordinary_quote_gets_no_near_lock_label(self):
        origins = {'method': 'bookmaker', 'probabilities': [0.677, 0.323],
                   'limitations': ['Bookmaker margin removed.'], 'quotes': [{'odds': [1.38, 2.9]}]}
        limits = _fallback_limits(self._match(), origins)
        self.assertFalse(any('Near-lock' in text for text in limits), limits)


class SummaryAndUnresolvedPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = inventory()
        cls.summary = summary(cls.data, './')
        cls.unresolved = unresolved_page(cls.data, '../')

    def test_the_executive_summary_carries_the_separate_fallback_section_once(self):
        self.assertEqual(self.summary.count('id="fallback-register"'), 1)
        self.assertEqual(self.summary.count('id="no-line-register"'), 1)

    def test_the_fallback_section_sits_below_the_pick_index_and_above_the_counts(self):
        self.assertLess(self.summary.index('id="picks-at-a-glance"'), self.summary.index('id="fallback-register"'))
        self.assertLess(self.summary.index('id="fallback-register"'), self.summary.index('id="unresolved-register"'))

    def test_the_pick_index_links_the_fallback_section(self):
        section = self.summary[self.summary.index('id="picks-at-a-glance"'):self.summary.index('id="fallback-register"')]
        self.assertIn('#fallback-register', section)

    def test_compact_list_links_every_row_and_the_full_register(self):
        soup = BeautifulSoup(fallback_register(self.data, './', compact=True), 'html.parser')
        rows = soup.select('.fallback-row')
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row.select('a.source-link'), row.get('id'))
            self.assertTrue(row.select('a.fallback-teams[href*="origination/#match-"]'), row.get('id'))
            self.assertTrue(row.select_one('.fallback-pick'), row.get('id'))
        self.assertIn('./unresolved/#fallback-register', str(soup))
        # The model rows stay in their own register; the compact list links there.
        self.assertNotIn('fallback-card-', str(soup))

    def test_the_unresolved_page_publishes_the_full_register(self):
        self.assertIn('id="fallback-register"', self.unresolved)
        self.assertIn('id="independent-verification"', self.unresolved)
        self.assertIn('id="unresolved-register"', self.unresolved)


class ResearchVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((SESSION / 'findings.json').read_text())
        cls.html = research_verification_block({}, '../')
        cls.soup = BeautifulSoup(cls.html, 'html.parser')

    def test_every_recorded_observation_has_an_https_source(self):
        self.assertTrue(self.record['rows'])
        for row in self.record['rows']:
            self.assertTrue(str(row.get('url', '')).startswith('https://'), row)

    def test_the_rendered_table_links_each_row(self):
        rows = self.soup.select('tbody tr')
        self.assertEqual(len(rows), len(self.record['rows']))
        for row in rows:
            links = [a['href'] for a in row.select('a.source-link')]
            self.assertTrue(links and all(url.startswith('https://') for url in links))

    def test_the_record_does_not_claim_a_hand_written_pick(self):
        blob = json.dumps(self.record).lower()
        for forbidden in ('"probability":', '"pick":', 'our pick is'):
            self.assertNotIn(forbidden, blob)

    def test_compact_form_links_the_full_table(self):
        compact = research_verification_block({}, './', compact=True)
        self.assertIn('./unresolved/#independent-verification', compact)


class BuiltSiteFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        site = ROOT / 'site'
        if not (site / 'index.html').exists():
            raise unittest.SkipTest('site/ not built; run python -m scripts.build first')
        cls.site = site

    def test_the_built_summary_and_unresolved_page_anchor_the_register(self):
        soup = BeautifulSoup((self.site / 'index.html').read_text(), 'html.parser')
        register = soup.find(id='fallback-register')
        self.assertIsNotNone(register, 'summary')
        self.assertTrue(register.select('.fallback-row'), 'summary')
        for row in register.select('.fallback-row'):
            self.assertTrue(row.select('a.source-link'), f'summary:{row.get("id")}')
        page = BeautifulSoup((self.site / 'unresolved/index.html').read_text(), 'html.parser')
        full = page.find(id='fallback-register')
        self.assertIsNotNone(full, 'unresolved')
        for card in full.select('.fallback-card'):
            self.assertTrue(card.select('a.source-link'), f'unresolved:{card.get("id")}')
            self.assertTrue(card.select('.fallback-limits li'), card.get('id'))

    def test_the_summary_anchor_resolves_from_the_summary(self):
        soup = BeautifulSoup((self.site / 'index.html').read_text(), 'html.parser')
        hrefs = [a['href'] for a in soup.select('#picks-at-a-glance a[href]')]
        self.assertTrue(any(href.endswith('#fallback-register') for href in hrefs), hrefs)
        self.assertIsNotNone(soup.find(id='fallback-register'))


if __name__ == '__main__':
    unittest.main()


class EvenBookGlanceRowTests(unittest.TestCase):
    """An exactly even outside book is a labelled no-pick, never a silent gap.

    1079200 (Color vs ex-Zero Tenacity) became a true 0.50/0.50 Polymarket book
    on 2026-10-24. The published page showed both prices and "Even · no side"
    but carried no pick marker, so the rendered-output audit counted it as a
    fixture with no pick and no unresolved label and failed the publisher
    (main runs 40127253463 / 40129278739).
    """

    def test_every_glance_row_carries_a_pick_marker_whatever_its_state(self):
        # The rendered-output audit keys on [data-glance-pick]; a row that lacks
        # it is indistinguishable from a silent gap. So every state carries one:
        # Pick / Snapshot / Locked, "Even book" for an exactly even two-sided
        # book, "Unresolved" for a fixture with neither.
        soup = BeautifulSoup(summary(inventory(), './'), 'html.parser')
        rows = soup.select('.glance-row')
        self.assertTrue(rows)
        for row in rows:
            marker = row.select_one('[data-glance-pick]')
            self.assertIsNotNone(marker, row.get('data-glance-id'))
            self.assertIn(marker.get_text(), {'Pick', 'Snapshot', 'Locked', 'Even book', 'Unresolved'},
                          row.get('data-glance-id'))
            if marker.get_text() == 'Even book':
                choice = row.select_one('.glance-choice')
                self.assertIn('no side', choice.get_text().lower())
                self.assertIsNotNone(choice.select_one('a[href*="unresolved"]'))

    def test_the_audit_accepts_a_labelled_even_row_and_still_fails_a_blank_one(self):
        from scripts import acceptance_audit as A
        def row(label, text, link=None):
            extra = f'<a class="internal-link" href="./{link}">Why</a>' if link else ''
            return (f'<li class="glance-row"><div class="glance-match"><strong>A vs B</strong></div>'
                    f'<div class="glance-choice"><span class="glance-pick-label"{label}>'
                    f'{text}</span><span class="glance-prob">A 50.0%</span>'
                    f'<span class="glance-other">B 50.0%</span>{extra}</div>'
                    f'<div class="glance-links"><a href="https://www.hltv.org/matches/1/x">HLTV</a></div></li>')
        labelled = row(' data-glance-pick', 'Even book', 'unresolved/#unresolved-register')
        legacy = row('', 'Even · no side', 'unresolved/#unresolved-register')
        blank = row('', 'Unresolved', None)
        check = A.check_glance_rows(Path('.'),
                                    BeautifulSoup(f'<html><body><ul>{labelled}</ul></body></html>', 'html.parser'))
        self.assertEqual(check.status, 'pass', check.detail)
        check = A.check_glance_rows(Path('.'),
                                    BeautifulSoup(f'<html><body><ul>{legacy}</ul></body></html>', 'html.parser'))
        self.assertEqual(check.status, 'pass', 'a pre-marker build must still read as labelled')
        check = A.check_glance_rows(Path('.'),
                                    BeautifulSoup(f'<html><body><ul>{blank}</ul></body></html>', 'html.parser'))
        self.assertEqual(check.status, 'fail', 'an unlabelled pick-less row is still a gap')


if __name__ == '__main__':
    unittest.main()
