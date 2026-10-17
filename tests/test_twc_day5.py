"""Day-5 (18 October 2026) final-day coverage: slots, participants and prices.

The final day of the Thunderpick World Championship 2026 is the third-place
decider and the grand final. Their participants are decided by the two
semifinals, so this module proves that:

* both final-day slots are found from HLTV's own page titles;
* a participant is only published when a source publishes it, or when a
  verified semifinal final score decides it (and is then labelled a
  derivation, with the semifinal pages it came from);
* a series whose participants are not yet decided never gets a probability, a
  placeholder or a default 50/50;
* the verified ladder contains only series a retained original has finished.
"""
import copy
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from scripts import twc_research, build_twc, twc_lines
from scripts.domain import iso, timestamp
from tests.test_twc import example_data

NOW = timestamp('2026-10-17T20:00:00Z')
FINAL = '2026-10-18'
SEMI = '2026-10-17'
GRAND_FINAL_URL = 'https://www.hltv.org/matches/2399417/grand-final-thunderpick-world-championship-2026'
THIRD_PLACE_URL = 'https://www.hltv.org/matches/2399416/third-place-thunderpick-world-championship-2026'
SEMI_ONE_URL = 'https://www.hltv.org/matches/2399414/furia-vs-aurora-thunderpick-world-championship-2026'
SEMI_TWO_URL = 'https://www.hltv.org/matches/2399415/falcons-vs-winner-thunderpick-world-championship-2026'


def final_page(url, title, teams, start):
    """A final-day page as HLTV publishes it before the participants are known."""
    return {'source_url': url, 'observed_at': iso(NOW), 'title': title, 'facts': {
        'teams': teams, 'starts_at': start, 'event_url': twc_research.EVENT_URL,
        'finished': False, 'score': None, 'maps': []}}


def semifinal(url, teams, start, score=None):
    return {'source_url': url, 'observed_at': iso(NOW), 'title': 'Semi at Thunderpick World Championship 2026',
            'facts': {'teams': teams, 'starts_at': start, 'event_url': twc_research.EVENT_URL,
                      'finished': score is not None, 'score': score, 'maps': []}}


def research(pages):
    return {'pages': pages, 'target_day': twc_research.TARGET_DAY, 'final_day': twc_research.FINAL_DAY}


class Day5SlotTests(unittest.TestCase):
    """Both final-day series are found, named and dated from the source."""

    def setUp(self):
        self.pages = [
            final_page(THIRD_PLACE_URL, 'Thunderpick World Championship 2026 - 3rd Place Decider Match | HLTV.org',
                       [None, ''], '2026-10-18T11:30:00Z'),
            final_page(GRAND_FINAL_URL, 'Thunderpick World Championship 2026 - Grand Final | HLTV.org',
                       [None, ''], '2026-10-18T15:00:00Z'),
        ]
        self.p = patch('scripts.twc_research.load', side_effect=lambda source: copy.deepcopy(research(self.pages)))
        self.p.start(); self.addCleanup(self.p.stop)
        self.lp = patch('scripts.twc_lines.load', return_value={'available': False, 'day': FINAL, 'days': [FINAL],
                                                                'observed_at': None, 'matches': [], 'reasons': {},
                                                                'report_path': None, 'policy': 'x',
                                                                'earlier_reads': 0, 'read_sources': [],
                                                                'unverifiable_reads': 0})
        self.lp.start(); self.addCleanup(self.lp.stop)

    def derive(self):
        return twc_research.derive_day5({}, Path('data'), NOW)

    def test_both_final_day_series_are_published_with_their_own_times(self):
        slots = self.derive()['slots']
        self.assertEqual(len(slots), 2)
        self.assertEqual([s['slot'] for s in slots], ['Third-place decider', 'Grand Final'])
        self.assertEqual([s['starts_at'] for s in slots], ['2026-10-18T11:30:00Z', '2026-10-18T15:00:00Z'])
        self.assertEqual([s['source_url'] for s in slots], [THIRD_PLACE_URL, GRAND_FINAL_URL])

    def test_undecided_participants_are_never_guessed(self):
        for slot in self.derive()['slots']:
            self.assertIsNone(slot['teams'])
            self.assertEqual(slot['participant_basis'], 'undecided')
            self.assertIsNone(slot['line'])
            self.assertIn('not published', slot['limitation'])

    def test_no_default_fifty_fifty_is_substituted(self):
        html = build_twc.render_day5(self.derive(), '../')
        self.assertIn('No placeholder, no default 50/50', html)
        self.assertNotIn('50.0%', html)

    def test_every_final_day_row_carries_its_source_link(self):
        html = build_twc.render_day5(self.derive(), '../')
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select('#day-five-picks article')
        self.assertEqual(len(cards), 2)
        for card in cards:
            hrefs = [a['href'] for a in card.select('.evidence-links a')]
            self.assertTrue(any('hltv.org/matches/' in h for h in hrefs))


class Day5ParticipantDerivationTests(unittest.TestCase):
    """A participant may be derived, but only from a verified semifinal score."""

    def setUp(self):
        self.pages = [
            semifinal(SEMI_ONE_URL, ['FURIA', 'Aurora'], '2026-10-17T14:00:00Z', score=[1, 2]),
            semifinal(SEMI_TWO_URL, ['Falcons', 'Legacy'], '2026-10-17T17:00:00Z', score=[2, 1]),
            final_page(THIRD_PLACE_URL, 'Thunderpick World Championship 2026 - 3rd Place Decider Match | HLTV.org',
                       [None, ''], '2026-10-18T11:30:00Z'),
            final_page(GRAND_FINAL_URL, 'Thunderpick World Championship 2026 - Grand Final | HLTV.org',
                       [None, ''], '2026-10-18T15:00:00Z'),
        ]
        self.p = patch('scripts.twc_research.load', side_effect=lambda source: copy.deepcopy(research(self.pages)))
        self.p.start(); self.addCleanup(self.p.stop)
        self.lp = patch('scripts.twc_lines.load', return_value={'available': False, 'day': FINAL, 'days': [FINAL],
                                                                'observed_at': None, 'matches': [], 'reasons': {},
                                                                'report_path': None, 'policy': 'x',
                                                                'earlier_reads': 0, 'read_sources': [],
                                                                'unverifiable_reads': 0})
        self.lp.start(); self.addCleanup(self.lp.stop)

    def derive(self):
        return twc_research.derive_day5({}, Path('data'), NOW)

    def test_winners_meet_in_the_grand_final_and_losers_in_the_third_place(self):
        slots = {s['slot']: s for s in self.derive()['slots']}
        self.assertEqual(sorted(slots['Grand Final']['teams']), ['Aurora', 'Falcons'])
        self.assertEqual(sorted(slots['Third-place decider']['teams']), ['FURIA', 'Legacy'])

    def test_a_derived_participant_is_labelled_and_links_its_semifinals(self):
        for slot in self.derive()['slots']:
            self.assertEqual(slot['participant_basis'], 'derived')
            self.assertIn('winners of the two semifinals', slot['derivation']['rule'])
            self.assertEqual(sorted(slot['derivation']['from']), sorted([SEMI_ONE_URL, SEMI_TWO_URL]))
        html = build_twc.render_day5(self.derive(), '../')
        self.assertIn('Participants derived from verified semifinal results', html)

    def test_one_unfinished_semifinal_leaves_both_series_undecided(self):
        self.pages[0]['facts']['finished'] = False
        self.pages[0]['facts']['score'] = None
        for slot in self.derive()['slots']:
            self.assertIsNone(slot['teams'])
            self.assertEqual(slot['participant_basis'], 'undecided')

    def test_a_tied_series_has_no_outcome(self):
        self.pages[0]['facts']['score'] = [2, 2]
        slots = self.derive()['slots']
        self.assertTrue(all(s['teams'] is None for s in slots))

    def test_published_participants_are_used_as_published(self):
        self.pages[3]['facts']['teams'] = ['Aurora', 'Falcons']
        slot = [s for s in self.derive()['slots'] if s['slot'] == 'Grand Final'][0]
        self.assertEqual(slot['participant_basis'], 'published')
        self.assertEqual(slot['teams'], ['Aurora', 'Falcons'])
        self.assertIsNone(slot['derivation'])

    def test_the_ladder_lists_only_finished_series(self):
        ladder = self.derive()['ladder']
        self.assertEqual(len(ladder), 2)
        self.assertEqual({tuple(r['teams']) for r in ladder}, {('FURIA', 'Aurora'), ('Falcons', 'Legacy')})
        for row in ladder:
            self.assertTrue(row['source_url'].startswith('https://www.hltv.org/matches/'))


class Day5PriceTests(unittest.TestCase):
    """A final-day price comes from an external book or from nowhere."""

    def setUp(self):
        self.pages = [
            semifinal(SEMI_ONE_URL, ['FURIA', 'Aurora'], '2026-10-17T14:00:00Z', score=[1, 2]),
            semifinal(SEMI_TWO_URL, ['Falcons', 'Legacy'], '2026-10-17T17:00:00Z', score=[2, 1]),
            final_page(GRAND_FINAL_URL, 'Thunderpick World Championship 2026 - Grand Final | HLTV.org',
                       ['Aurora', 'Falcons'], '2026-10-18T15:00:00Z'),
        ]
        self.p = patch('scripts.twc_research.load', side_effect=lambda source: copy.deepcopy(research(self.pages)))
        self.p.start(); self.addCleanup(self.p.stop)
        self.line = {'fixture_id': 'twc-2399417', 'teams': ['Aurora', 'Falcons'],
                     'starts_at': '2026-10-18T15:00:00Z', 'probabilities': [0.62, 0.38],
                     'pick_index': 0, 'method': 'consensus', 'label': 'External consensus line',
                     'observed_at': iso(NOW), 'providers': [{'provider': 'Polymarket',
                                                            'source_url': 'https://polymarket.com/event/x'}],
                     'attempts': [], 'limitations': [], 'source_url': 'https://polymarket.com/event/x'}
        self.lp = patch('scripts.twc_lines.load', return_value={'available': True, 'day': FINAL, 'days': [FINAL],
                                                                'observed_at': iso(NOW), 'matches': [self.line],
                                                                'reasons': {}, 'report_path': 'research/twc-current/evidence/twc-day4-lines.json',
                                                                'policy': 'x', 'earlier_reads': 0, 'read_sources': [],
                                                                'unverifiable_reads': 0})
        self.lp.start(); self.addCleanup(self.lp.stop)

    def derive(self):
        return twc_research.derive_day5({}, Path('data'), NOW)

    def test_a_validated_line_becomes_the_published_pick(self):
        slot = [s for s in self.derive()['slots'] if s['slot'] == 'Grand Final'][0]
        self.assertIsNotNone(slot['line'])
        self.assertEqual(slot['line']['pick_index'], 0)
        html = build_twc.render_day5(self.derive(), '../')
        self.assertIn('Default pick: Aurora', html)
        self.assertIn('62.0%', html)
        self.assertIn('https://polymarket.com/event/x', html)

    def test_a_fixture_without_a_book_stays_blank_with_a_reason(self):
        slot = [s for s in self.derive()['slots'] if s['slot'] == 'Third-place decider']
        self.assertEqual(slot, [])

    def test_the_day_scoped_line_count_only_counts_that_day(self):
        guide = self.derive()
        self.assertEqual(guide['lines']['day'], FINAL)
        self.assertEqual(guide['lines']['total'], 1)
        self.assertEqual(guide['lines']['resolved'], 1)


class Day5LineScopingTests(unittest.TestCase):
    """The final day and the semifinal day are reported separately."""

    def test_for_day_keeps_only_that_day(self):
        lines = {'matches': [
            {'teams': ['Aurora', 'Falcons'], 'starts_at': '2026-10-18T15:00:00Z', 'probabilities': [0.6, 0.4]},
            {'teams': ['FURIA', 'Aurora'], 'starts_at': '2026-10-17T14:00:00Z', 'probabilities': [0.5, 0.5]},
        ], 'available': True, 'observed_at': iso(NOW)}
        final = twc_lines.for_day(lines, FINAL)
        self.assertEqual(final['total'], 1)
        self.assertEqual(final['resolved'], 1)
        self.assertEqual(final['matches'][0]['teams'], ['Aurora', 'Falcons'])
        semi = twc_lines.for_day(lines, SEMI)
        self.assertEqual(semi['total'], 1)


class Day5RenderTests(unittest.TestCase):
    """The section is phone-readable, linked and never invents a number."""

    def setUp(self):
        self.guide = {'schema_version': 1, 'generated_at': None, 'source_snapshot_at': None,
                      'evaluated_at': iso(NOW), 'event_day': FINAL, 'research_available': True,
                      'slots': [], 'semifinals': [], 'ladder': [],
                      'lines': {'available': False, 'day': FINAL, 'observed_at': None,
                                'report_path': 'research/twc-current/source-report.json', 'policy': 'x',
                                'resolved': 0, 'total': 0, 'fixtures': []},
                      'research_report': 'research/twc-current/source-report.json',
                      'policy': 'x'}

    def test_an_empty_final_day_says_so_instead_of_inventing_a_fixture(self):
        html = build_twc.render_day5(self.guide, '../')
        self.assertIn('No final-day series is confirmed in the retained research', html)
        self.assertIn('nothing is invented', html)

    def test_the_section_carries_its_own_anchors(self):
        html = build_twc.render_day5(self.guide, '../')
        soup = BeautifulSoup(html, 'html.parser')
        for anchor in ('day-five-picks', 'day-five-ladder', 'day-five-guide'):
            self.assertIsNotNone(soup.find(id=anchor), anchor)

    def test_the_guide_states_that_results_are_context_not_a_probability(self):
        html = build_twc.render_day5(self.guide, '../')
        self.assertIn('they do not set a probability', html)
        self.assertIn('take the higher-probability side of the external line as the default', html)


if __name__ == '__main__':
    unittest.main()
