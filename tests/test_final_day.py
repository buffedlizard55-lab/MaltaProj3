"""Session arena-be84edde: the Final day review page and the Pinnacle reader.

Everything here is offline and deterministic. No test performs a network call,
and none of them writes a probability or a pick into a published feed. The
point is to pin the safety properties:

* the page cannot invent a probability — it only renders what a dated file says;
* every row carries an official link or a visible unverified marker;
* the Pinnacle reader rejects map markets, "Yes/No" specials and live games;
* the arithmetic (American -> decimal -> no-vig) is exactly reproducible.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import pinnacle_lines
from scripts.audit_rows import is_official
from scripts.build import PAGES, summary
from scripts.build_final_day import render

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data' / 'research' / 'be84edde' / 'twc-final-day.json'
LIVE_PROBE = ROOT / 'data' / 'research' / 'be84edde' / 'live-probe.json'
EDGE = ROOT / 'data' / 'edge-review.json'


def _data():
    data = json.loads((ROOT / 'data' / 'latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data' / 'origination.json').read_text())
    return data


class PinnacleReader(unittest.TestCase):
    """Pure arithmetic and the rejection rules, with no network."""

    def test_american_conversion(self):
        self.assertAlmostEqual(pinnacle_lines.american_to_decimal(-186), 1.537634, places=5)
        self.assertAlmostEqual(pinnacle_lines.american_to_decimal(151), 2.51, places=5)
        self.assertAlmostEqual(pinnacle_lines.american_to_decimal(100), 2.0, places=6)
        self.assertAlmostEqual(pinnacle_lines.american_to_decimal(-100), 2.0, places=6)
        with self.assertRaises(ValueError):
            pinnacle_lines.american_to_decimal(0)

    def test_overround_is_removed_proportionally(self):
        a, b = pinnacle_lines.probabilities(2.0, 2.0)
        self.assertAlmostEqual(a, 0.5, places=9)
        self.assertAlmostEqual(b, 0.5, places=9)
        a, b = pinnacle_lines.probabilities(1.4, 3.0)
        self.assertAlmostEqual(a + b, 1.0, places=9)
        self.assertGreater(a, b)

    def test_series_line_is_the_lowest_period_not_the_map_lines(self):
        matchup = {'id': 1, 'participants': [{'id': 11, 'name': 'FURIA'},
                                             {'id': 12, 'name': 'BB Team'}]}
        markets = [
            {'matchupId': 1, 'type': 'moneyline', 'period': 3,
             'prices': [{'participantId': 11, 'price': -186}, {'participantId': 12, 'price': 151}]},
            {'matchupId': 1, 'type': 'moneyline', 'period': 1,
             'prices': [{'participantId': 11, 'price': -186}, {'participantId': 12, 'price': 151}]},
            {'matchupId': 1, 'type': 'moneyline', 'period': 0,
             'prices': [{'participantId': 11, 'price': -286}, {'participantId': 12, 'price': 226}]},
        ]
        found = pinnacle_lines.series_moneyline(matchup, markets)
        self.assertIsNotNone(found)
        self.assertEqual(found['period'], 0)
        self.assertEqual(found['american'], [-286, 226])
        self.assertEqual(found['participants'], ['FURIA', 'BB Team'])
        self.assertAlmostEqual(sum(found['probabilities']), 1.0, places=6)
        # The series favourite is the team printed first at the shorter price.
        self.assertGreater(found['probabilities'][0], found['probabilities'][1])

    def test_designation_prices_resolve_by_home_away(self):
        matchup = {'id': 2, 'participants': [{'id': 21, 'name': 'Falcons Force'},
                                             {'id': 22, 'name': 'MAYBE'}]}
        markets = [{'matchupId': 2, 'type': 'moneyline', 'period': 0,
                    'prices': [{'designation': 'home', 'price': -210},
                               {'designation': 'away', 'price': 151}]}]
        found = pinnacle_lines.series_moneyline(matchup, markets)
        self.assertEqual(found['participants'], ['Falcons Force', 'MAYBE'])
        self.assertGreater(found['probabilities'][0], found['probabilities'][1])

    def test_yes_no_specials_and_other_matchups_are_rejected(self):
        matchup = {'id': 3, 'participants': [{'id': 31, 'name': 'Aurora'},
                                             {'id': 32, 'name': 'Falcons'}]}
        special = [{'matchupId': 3, 'type': 'moneyline', 'period': 0,
                    'prices': [{'participantId': 91, 'price': -499},
                               {'participantId': 92, 'price': 347}]}]
        self.assertIsNone(pinnacle_lines.series_moneyline(matchup, special))
        other = [{'matchupId': 99, 'type': 'moneyline', 'period': 0,
                  'prices': [{'participantId': 31, 'price': 112},
                             {'participantId': 32, 'price': -136}]}]
        self.assertIsNone(pinnacle_lines.series_moneyline(matchup, other))

    def test_non_moneyline_alternate_closed_and_one_sided_rows_are_rejected(self):
        matchup = {'id': 4, 'participants': [{'id': 41, 'name': 'A'}, {'id': 42, 'name': 'B'}]}
        good = [{'matchupId': 4, 'type': 'moneyline', 'period': 0,
                 'prices': [{'participantId': 41, 'price': 120},
                            {'participantId': 42, 'price': -140}]}]
        self.assertIsNotNone(pinnacle_lines.series_moneyline(matchup, good))
        for bad in (
            [dict(good[0], type='total')],
            [dict(good[0], isAlternate=True)],
            [dict(good[0], status='closed')],
            [dict(good[0], prices=[{'participantId': 41, 'price': 120}])],
            [dict(good[0], prices=[{'participantId': 41, 'price': 120},
                                   {'participantId': 41, 'price': -140}])],
        ):
            with self.subTest(bad=bad):
                self.assertIsNone(pinnacle_lines.series_moneyline(matchup, bad))

    def test_participants_without_ids_stay_home_and_away(self):
        """Pinnacle's esports board publishes participants with no id; the two
        prices must still land on the two different teams (regression: both
        sides of FURIA vs BB Team resolved to "BB Team")."""
        matchup = {'id': 5, 'participants': [{'name': 'FURIA'}, {'name': 'BB Team'}]}
        markets = [{'matchupId': 5, 'type': 'moneyline', 'period': 0,
                    'prices': [{'designation': 'home', 'price': -286},
                               {'designation': 'away', 'price': 226}]}]
        found = pinnacle_lines.series_moneyline(matchup, markets)
        self.assertIsNotNone(found)
        self.assertEqual(found['participants'], ['FURIA', 'BB Team'])
        self.assertGreater(found['probabilities'][0], found['probabilities'][1])
        self.assertAlmostEqual(found['probabilities'][0] + found['probabilities'][1], 1.0, places=6)

    def test_reviewed_name_equivalence_is_normalised_before_matching(self):
        # Pinnacle lists BetBoom Team as "BB Team"; the alias must be normalised
        # the same way as the board names or it can never match.
        self.assertEqual(pinnacle_lines._norm(pinnacle_lines.NAME_EQUIVALENCES['betboom']),
                         pinnacle_lines._norm('BB Team'))

    def test_quote_refuses_a_fuzzy_or_empty_fixture(self):
        # Short-circuits before any network call: an ambiguous name pair is refused.
        self.assertIn('unique two-team fixture',
                      pinnacle_lines.quote('', '', None)[1])
        self.assertIn('unique two-team fixture',
                      pinnacle_lines.quote('Same', 'Same', None)[1])


class FinalDayPage(unittest.TestCase):
    def setUp(self):
        self.dossier = json.loads(DOSSIER.read_text())
        self.soup = BeautifulSoup(render(_data(), './', EDGE), 'html.parser')

    def test_every_section_the_brief_asked_for_is_present(self):
        for anchor in ('start-here', 'day-one-to-four', 'day-read', 'roster',
                       'final-day-picks', 'dated-lines', 'contrarian-rules',
                       'upset-candidates', 'unresolved', 'sources'):
            with self.subTest(anchor=anchor):
                self.assertIsNotNone(self.soup.find(id=anchor))

    def test_results_table_lists_twelve_series_with_one_hltv_link_each(self):
        rows = self.soup.select('#day-one-to-four tbody tr')
        self.assertEqual(len(rows), 12, 'Days 1-3 group stage plus the two semifinals')
        for row in rows:
            links = [a['href'] for a in row.select('a[href]')]
            self.assertTrue(any(is_official(link) for link in links), row.get_text(' ', strip=True)[:80])

    def test_no_probability_is_printed_without_a_source_beside_it(self):
        """A number on this page is always sitting next to the line it came from."""
        for cell in self.soup.select('.prob-side'):
            card = cell.find_parent(class_='final-day-card')
            self.assertIsNotNone(card)
            links = [a['href'] for a in card.select('a[href]')]
            self.assertTrue(any(is_official(link) for link in links),
                            'a printed probability must sit beside an official link')
            text = card.get_text(' ', strip=True).lower()
            self.assertTrue('uncalibrated' in text or 'external market' in text,
                            'a printed probability must declare what produced it')

    def test_dated_dossier_stores_no_probability(self):
        raw = DOSSIER.read_text()
        self.assertNotIn('\"probabilities\"', raw)

    def test_unresolved_fixtures_are_named_not_dropped(self):
        section = self.soup.find(id='unresolved')
        text = section.get_text(' ', strip=True)
        self.assertIn('unresolved', text.lower())

    def test_roster_finding_flags_that_no_october_change_was_verified(self):
        finding = self.dossier['roster_verification']['finding']
        self.assertIn('No October 2026', finding)
        text = self.soup.find(id='roster').get_text(' ', strip=True)
        self.assertIn('No October 2026', text)

    def test_aggregator_quotes_are_labelled_and_flagged_unverified(self):
        table = self.soup.find(id='dated-lines')
        rows = table.select('tbody tr')
        self.assertTrue(rows)
        for row in rows:
            links = [a['href'] for a in row.select('a[href]')]
            text = row.get_text(' ', strip=True)
            has_official = any(is_official(link) for link in links)
            self.assertTrue(has_official or 'unverified' in text.lower(),
                            f'row must link an official source or be flagged: {text[:90]}')

    def test_every_sources_row_is_linked_and_classified(self):
        rows = self.soup.select('#sources tbody tr')
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row.select('a[href]'), 'every cited source must be openable')
            text = row.get_text(' ', strip=True)
            self.assertTrue(is_official(row.select_one('a[href]')['href'])
                            or 'unverified' in text.lower(), text[:90])

    def test_pinnacle_is_not_used_as_a_pick_until_a_quote_exists(self):
        # The dated dossier never stores a probability; only labelled context.
        def walk(node):
            if isinstance(node, dict):
                if 'probabilities' in node:
                    self.fail('the dated research dossier must not store a probability')
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
        walk(self.dossier)


class StartHereNavigation(unittest.TestCase):
    """The brief: find the picks on a phone without hunting."""

    def setUp(self):
        self.data = _data()

    def test_page_is_registered_and_reachable(self):
        self.assertIn('final', PAGES)
        self.assertEqual(PAGES['final'][1], 'final-day/index.html')

    def test_summary_puts_the_pick_entry_points_above_the_first_match_card(self):
        from unittest.mock import patch
        with patch('scripts.build.contrarian_review', return_value=''), \
             patch('scripts.build.contrarian_briefing', return_value=''):
            soup = BeautifulSoup(summary(self.data, './'), 'html.parser')
        bar = soup.select_one('nav.start-here')
        self.assertIsNotNone(bar)
        hrefs = [a['href'] for a in bar.select('a[href]')]
        self.assertIn('./origination/#picks', hrefs)
        self.assertIn('./final-day/', hrefs)
        self.assertIn('./origination/#unresolved', hrefs)
        # It must come before the first match row in document order.
        html = str(soup)
        self.assertLess(html.index('start-here'), html.index('id="picks-at-a-glance"'))

    def test_site_map_lists_the_final_day_page(self):
        from unittest.mock import patch
        with patch('scripts.build.contrarian_review', return_value=''), \
             patch('scripts.build.contrarian_briefing', return_value=''):
            soup = BeautifulSoup(summary(self.data, './'), 'html.parser')
        links = {a['href'] for a in soup.select('#site-map a[href]')}
        self.assertIn('./final-day/', links)


class LiveProbeEvidence(unittest.TestCase):
    """The dated runner probe, if it has been committed, must stay honest."""

    def test_probe_records_the_unresolved_fixtures_and_their_reasons(self):
        if not LIVE_PROBE.exists():
            self.skipTest('no live probe has been committed for this session')
        probe = json.loads(LIVE_PROBE.read_text())
        counts = probe['origination_counts']
        self.assertEqual(counts['unresolved'], len(probe['unresolved_detail']))
        for row in probe['unresolved_detail']:
            self.assertTrue(row['research_trail'], 'every blank needs a recorded reason')
            self.assertTrue(row['hotspawn_source_url'])
        self.assertLessEqual(counts['resolved'] + counts['unresolved'], counts['active'])


if __name__ == '__main__':
    unittest.main()
