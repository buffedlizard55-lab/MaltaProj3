"""Session arena-5fbf5cd5 — phone-first summary, separate unresolved page, live coverage.

The brief for this session had three parts: a phone-readable executive summary
that reaches the picks in one tap, a *separate* section for the matches that
still have no pick plus the limitations behind them, and proof from the runner
that every active Hotspawn CS2 fixture carries a pick or an explicit,
source-linked reason.

These tests pin the structure that delivers the first two and re-check the
archived live snapshot that proves the third. They never invent a probability:
every number asserted here is read from the repository's own saved evidence.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import (PAGES, coverage_probe_block, shell, summary, unresolved,
                           unresolved_register)
from scripts.coverage_5fbf5cd5 import hotspawn_start

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'data/research/5fbf5cd5/live-2026-10-22'


def data_with_complete() -> dict:
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    data['fallbacks'] = {str(m['id']): m for m in data['complete_picks']['matches']
                         if m.get('origination')}
    data['flags'] = list(data.get('flags') or [])
    return data


class SummaryOrderTests(unittest.TestCase):
    """The first pick must not sit behind two full screens of navigation."""

    @classmethod
    def setUpClass(cls):
        cls.data = data_with_complete()
        cls.html = summary(cls.data, './')

    def test_banner_then_picks_then_register_then_secondary_links(self):
        order = ['exec-banner', 'id="picks-at-a-glance"', 'id="unresolved-register"',
                 'id="start-here"']
        positions = [self.html.index(marker) for marker in order]
        self.assertEqual(positions, sorted(positions), f'phone order regressed: {order}')

    def test_banner_has_exactly_one_primary_action_to_the_picks(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        banner = soup.select_one('section.exec-banner')
        self.assertIsNotNone(banner)
        primaries = banner.select('a.primary')
        self.assertEqual(len(primaries), 1, 'a phone should see one obvious action')
        self.assertEqual(primaries[0]['href'], './origination/#picks')
        self.assertIn('every hotspawn cs2 pick', banner.get_text(' ', strip=True).lower())

    def test_banner_links_the_separate_unresolved_page(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        hrefs = {a['href'] for a in soup.select('section.exec-banner a[href]')}
        self.assertIn('./unresolved/', hrefs)
        self.assertIn('./methodology/', hrefs)

    def test_counts_in_the_banner_match_the_published_snapshot(self):
        cc = self.data['complete_picks']['counts']
        text = BeautifulSoup(self.html, 'html.parser').select_one('.exec-banner').get_text(' ', strip=True)
        self.assertIn(f"{cc['with_pick']} of {cc['active']}", text)
        self.assertIn(f"{cc['unresolved']} without a line", text)

    def test_secondary_line_states_the_no_direction_count(self):
        cc = self.data['complete_picks']['counts']
        no_direction = cc['resolved'] - cc['with_pick']
        bar = BeautifulSoup(self.html, 'html.parser').select_one('.start-here').get_text(' ', strip=True)
        if no_direction:
            self.assertIn(f'{no_direction} resolved estimate', bar)
        else:
            self.assertIn(f"{cc['with_pick']} directional picks", bar)

    def test_dated_tournament_material_is_collapsed(self):
        # `_twc_day4` is what the dated tournament block needs; the executive
        # summary receives it from build(), so set it here the same way.
        data = data_with_complete()
        data['_twc_day4'] = {'matches': [], 'not_in_hotspawn_snapshot': [], 'lines': {}}
        html = summary(data, './')
        archive = BeautifulSoup(html, 'html.parser').select_one('details#archive-twc')
        self.assertIsNotNone(archive, 'archived TWC review must not push today\'s picks down the page')
        self.assertNotIn('open', archive.attrs, 'the archive must start collapsed')
        self.assertLess(html.index('id="picks-at-a-glance"'), html.index('id="archive-twc"'),
                        'the archive must sit below the picks, not above them')


class UnresolvedPageTests(unittest.TestCase):
    """`/unresolved/` is the separate section the brief asked for."""

    @classmethod
    def setUpClass(cls):
        cls.data = data_with_complete()
        cls.html = unresolved(cls.data, '../')
        cls.soup = BeautifulSoup(cls.html, 'html.parser')

    def test_the_page_is_registered_and_reachable_from_the_mobile_bar(self):
        self.assertIn('unresolved', PAGES)
        self.assertEqual(PAGES['unresolved'][1], 'unresolved/index.html')
        bar = BeautifulSoup(shell(self.data, 'summary', summary(self.data, './'), './'),
                            'html.parser').select_one('nav.mobile-nav')
        labels = [a.get_text(' ', strip=True) for a in bar.select('a')]
        self.assertIn('Unresolved', labels)

    def test_heading_and_register_are_present(self):
        self.assertIsNotNone(self.soup.select_one('h1'))
        self.assertIn('Unresolved picks', self.soup.select_one('h1').get_text())
        self.assertIsNotNone(self.soup.select_one('#unresolved-register'))
        self.assertIsNotNone(self.soup.select_one('#unresolved'))

    def test_source_ladder_is_published_with_official_links(self):
        ladder = self.soup.select_one('#source-ladder')
        self.assertIsNotNone(ladder, 'the order in which sources are tried must be published')
        hrefs = {a.get('href') for a in ladder.select('a[href^="https://"]')}
        for host in ('polymarket.com', 'kalshi.com', 'thunderpick.io', 'bovada.lv',
                     'pinnacle.com', 'egamersworld.com', 'github.com/ValveSoftware',
                     'hltv.org', 'bo3.gg'):
            self.assertTrue(any(host in href for href in hrefs), f'missing official link: {host}')

    def test_model_rows_are_labelled_and_never_called_bookmaker_lines(self):
        section = self.soup.select_one('#research-only')
        self.assertIsNotNone(section)
        text = section.get_text(' ', strip=True)
        self.assertIn('never presented as a betting line', text)
        self.assertIn('not market-backed', text)
        for row in section.select('tbody tr'):
            # First <td> is the pick/probability cell; the row header is a <th>.
            cell = row.select('td')[0].get_text(' ', strip=True)
            self.assertRegex(cell, r'\d{1,3}\.\d%|Even estimate',
                             'a resolved model row must show its probability or say it is even')

    def test_a_blank_is_never_given_a_default_probability(self):
        # Every probability shown on this page belongs to a fixture that has an
        # estimate in the published snapshot; nothing is synthesised here.
        complete = self.data['complete_picks']
        with_estimate = {str(m['id']) for m in complete['matches'] if m.get('origination')}
        blank_ids = {str(m['id']) for m in complete['matches'] if not m.get('origination')}
        resolver = unresolved_register(self.data, '../')
        for match_id in blank_ids:
            card = BeautifulSoup(resolver, 'html.parser').select_one(f'#unresolved-summary-{match_id}')
            if card is None:
                continue
            self.assertNotRegex(card.get_text(' '), r'\b\d{1,3}\.\d%')
        self.assertFalse(with_estimate & blank_ids)

    def test_rules_section_names_the_forbidden_inputs(self):
        rules = self.soup.select_one('#unresolved-rules').get_text(' ', strip=True)
        self.assertIn('% picked', rules)
        self.assertIn('fan vote', rules)
        self.assertIn('never fills a missing value', rules)

    def test_coverage_probe_block_survives_on_the_unresolved_page(self):
        probe = json.loads((ROOT / 'data/research/8fa2b226/coverage-probe.json').read_text())
        data = data_with_complete()
        data['coverage_probe'] = probe
        block = coverage_probe_block(data, '../')
        self.assertIn('never writes a probability', block)
        self.assertEqual(coverage_probe_block(data_with_complete(), '../'), '')
        rendered = unresolved(data, '../')
        self.assertIn('Coverage probe', rendered)
        self.assertIn('data/research/8fa2b226/coverage-probe.json', rendered)


class LiveCoverageEvidenceTests(unittest.TestCase):
    """The archived runner snapshot: every active fixture has a pick or a reason."""

    @classmethod
    def setUpClass(cls):
        cls.register = json.loads((ROOT / 'data/research/5fbf5cd5/coverage-register.json').read_text())
        cls.snapshot = json.loads((LIVE / 'latest.json').read_text())
        cls.origination = json.loads((LIVE / 'origination.json').read_text())
        cls.coverage = json.loads((LIVE / 'coverage.json').read_text())

    def test_the_register_covers_every_published_active_fixture(self):
        published = {str(m['id']) for m in self.snapshot['matches']
                     if m['availability'] in {'open', 'locked', 'unknown_lock'}}
        registered = {row['id'] for row in self.register['fixtures']}
        self.assertEqual(published, registered)

    def test_every_registered_fixture_has_a_pick_or_a_stated_reason(self):
        for row in self.register['fixtures']:
            self.assertIsNotNone(row['method'], row['id'])
            if row['probabilities'] is None:
                self.assertTrue(row['ladder'], f'{row["id"]} has no probability and no trail')
                continue
            self.assertAlmostEqual(sum(row['probabilities']), 1.0, places=6, msg=row['id'])
            if row['pick'] is not None:
                self.assertIn(row['pick'], row['teams'])

    def test_every_registered_fixture_links_its_own_source(self):
        for row in self.register['fixtures']:
            self.assertTrue(str(row.get('source_url') or '').startswith('https://'), row['id'])

    def test_the_inventory_reconciles_with_hotspawns_own_array(self):
        inventory = self.register['inventory']
        self.assertEqual(inventory['result'], 'ok')
        self.assertEqual(inventory['missing_from_site'], [],
                         'every active record in Hotspawn\'s array must be on the site')

    def test_model_backed_rows_are_counted_separately_from_money(self):
        money = {'market', 'bookmaker', 'consensus', 'reference'}
        expected = sum(1 for row in self.register['fixtures'] if row['method'] in money)
        self.assertEqual(self.register['money_backed'], expected)
        for row in self.register['fixtures']:
            if row['method'] not in money:
                # Featured Valve-model rows predate the family field; the method
                # is still a model, never a money line.
                self.assertIn(row['family'], {None, 'model', 'network', 'form', 'guidance'},
                              row['id'])

    def test_each_fixture_record_carries_an_hltv_read(self):
        for fixture in self.coverage['fixtures']:
            hltv = fixture.get('hltv') or {}
            self.assertIn('listing', hltv, fixture['id'])
            self.assertIsNotNone(hltv['listing'].get('status'), fixture['id'])
            for search in hltv.get('team_searches') or []:
                self.assertTrue(search['url'].startswith('https://www.hltv.org/search?query='))


class HotspawnStartParsingTests(unittest.TestCase):
    """`scheduled_start_time` is epoch milliseconds in a string."""

    def test_milliseconds_are_parsed(self):
        parsed = hotspawn_start({'scheduled_start_time': '1792656000000'})
        self.assertEqual(parsed.isoformat(), '2026-10-22T08:00:00+00:00')

    def test_seconds_are_parsed(self):
        self.assertEqual(hotspawn_start({'scheduled_start_time': '1792656000'}).year, 2026)

    def test_missing_or_garbage_values_are_none(self):
        self.assertIsNone(hotspawn_start({}))
        self.assertIsNone(hotspawn_start({'scheduled_start_time': 'not a time'}))
        self.assertIsNone(hotspawn_start({'scheduled_start_time': None}))

    def test_the_probe_does_not_look_for_an_iso_field(self):
        source = (ROOT / 'scripts/coverage_5fbf5cd5.py').read_text()
        self.assertNotRegex(source, r"start_date'\) or row\.get\('starts_at'\)",
                            'the ISO-field lookup silently produced zero live rows once already')


if __name__ == '__main__':
    unittest.main()
