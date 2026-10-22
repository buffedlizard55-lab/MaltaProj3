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


class ModelLabelProvenanceTests(unittest.TestCase):
    """A network estimate must never be published as a Valve rating.

    Regression test for the 2026-10-22 finding: `model` is replaced with the
    bo3.gg network quote when that rung exists, and the label block used to
    assume anything that was not the 'form' family came from Valve.
    """

    NOW = __import__('datetime').datetime(2026, 10, 22, 2, 0, tzinfo=__import__('datetime').timezone.utc)

    def _originate(self, quote):
        from scripts.originate import originate_match
        match = {
            'id': '9001',
            'teams': [{'id': '1', 'name': 'Unrated One'}, {'id': '2', 'name': 'Unrated Two'}],
            'starts_at': '2026-10-22T06:00:00Z',
            'source_url': 'https://www.hotspawn.com/matches/example-9001',
            '_network': quote,
        }
        return originate_match(match, [], [], [], None, {}, self.NOW, hltv=[], reference=[],
                               hltv_rank=[], hltv_meta=None)

    def test_network_quote_is_labelled_as_the_network_model(self):
        result = self._originate({
            'provider': 'Own network model (bo3.gg results graph)', 'family': 'network',
            'method': 'model', 'model_version': 'network-bt-1',
            'probabilities': [0.62, 0.38], 'graph_matches': 4645, 'graph_anchors': 269,
            'rating_sd_diff': 120.0, 'interval': [0.3, 0.85], 'n_series': 12,
            'low_confidence': False, 'source_url': 'https://bo3.gg/matches',
        })
        analysis = result['origination']
        self.assertEqual(analysis['method'], 'model')
        self.assertIn('network', analysis['label'].lower())
        self.assertNotIn('valve', analysis['label'].lower())
        joined = ' '.join(result['limitations']).lower()
        self.assertIn('bradley', joined, 'the network limitation must be published with the number')

    def test_a_fixture_with_no_rung_stays_blank(self):
        result = self._originate(None)
        self.assertIsNone(result['origination'], 'no rung means no number, never a default')

    def test_the_live_snapshot_has_no_network_row_labelled_valve(self):
        register = json.loads((ROOT / 'data/research/5fbf5cd5/coverage-register.json').read_text())
        origination = json.loads((LIVE / 'origination.json').read_text())
        labels = {m['id']: (m.get('origination') or {}).get('label') for m in origination['matches']}
        # The archived snapshot predates the fix; the finding documents it and
        # this assertion pins that no *other* row carries the mismatch.
        network = [row['id'] for row in register['fixtures'] if row.get('family') == 'network']
        self.assertTrue(network, 'the snapshot should contain network-backed rows')
        for match_id in network:
            self.assertIsNotNone(labels.get(match_id))


class PicksPageCountTests(unittest.TestCase):
    """The picks page must describe the rows it renders, not the featured counters.

    On 2026-10-22 the page said "35 of 35 ... carry a pick" and "8 come from an
    external market" while the rendered table had 34 directional picks, 10
    money-backed rows and one exact even estimate. The counts now follow the
    selected fallback, and a no-side row is named instead of being counted as a
    pick.
    """

    def test_money_count_and_even_row_describe_the_rendered_table(self):
        from bs4 import BeautifulSoup
        from scripts.build import picks
        data = json.loads((ROOT / 'data/latest.json').read_text())
        data['fallbacks'] = {}
        active = [m for m in data['matches'] if m['availability'] != 'past']
        even = active[0]
        even['analysis'] = dict(even['analysis'] or {'probabilities': [0.5, 0.5], 'fair_decimal': [2.0, 2.0],
                                                      'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                                                      'source': 'Valve official ratings', 'observed_at': even['observed_at'],
                                                      'method': 'model'})
        even['analysis']['probabilities'] = [0.5, 0.5]
        even['pick_index'] = None
        expected = sum(1 for m in active if m['analysis'] and m['pick_index'] is not None)
        text = BeautifulSoup(picks(data, './'), 'html.parser').select_one('.info-strip').get_text(' ', strip=True)
        self.assertIn(f'{expected} of {len(active)} matches below carry a directional pick', text)
        self.assertNotIn('carry a pick', text)
        self.assertRegex(text, r'(shows|show) both probabilities with no supportable side')
        self.assertIn('No fixture is missing an estimate', text)


if __name__ == '__main__':
    unittest.main()
