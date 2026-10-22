"""Tests for session 15fc6bca's published source ledger and even-estimate note.

The brief asks that a blank pick show the *real limiting factor* and name the
source that could not be used, and that an exactly even estimate never be
presented as a missing source. Both are published fields on every ladder row:

* ``sources_checked`` — one entry per price source the row was checked against,
  with that source's own outcome and a short reason. It is derived from the
  research trail, so a source cannot appear in it without a trail stage.
* a limitation naming every source that produced no price, one clause each;
* an explicit "exactly even" note for a 50/50 estimate, in the source's numbers.

No probability, pick or quote is changed by any of this.
"""
from __future__ import annotations

import unittest

from scripts.originate import (_concise_reason, even_estimate_explanation,
                               missing_price_sources, originate_match,
                               source_ledger)
from tests.test_15fc6bca_relay import NOW, REGISTRY, fixture, relay_row

VALVE_URL = ('https://github.com/ValveSoftware/counter-strike_regional_standings/'
             'blob/main/live/2026/standings_global_2026_10_05.md')
META = {'source_url': VALVE_URL, 'snapshot_date': '2026-10-05',
        'evidence_file': 'data/evidence/valve-standings.json', 'observed_at': '2026-10-22T00:50:00Z'}


def rating(name, points, standing):
    return {'name': name, 'points': points, 'standing': standing,
            'roster': ['p1', 'p2', 'p3', 'p4', 'p5'], 'snapshot_date': '2026-10-05',
            'source_url': VALVE_URL}


def even_fixture():
    match = fixture('ex-Zero Tenacity', 'ex-RUSTEC', start='2026-10-23T08:00:00Z')
    return match, [rating('ex-Zero Tenacity', 1066, 93), rating('ex-RUSTEC', 1066, 92)]


class SourceLedgerTest(unittest.TestCase):
    def test_ledger_names_each_price_source_with_its_own_outcome(self):
        trail = [
            {'stage': 'HLTV research', 'status': 'checked', 'detail': 'x', 'source_url': 'https://www.hltv.org/matches'},
            {'stage': 'Betting market (Polymarket series winner)', 'status': 'resolved',
             'detail': 'Exact teams and time.', 'source_url': 'https://polymarket.com/event/x'},
            {'stage': 'Exchange market (Kalshi CS2 match winner)', 'status': 'unresolved',
             'detail': 'No alias-verified Kalshi match-winner line found for these teams and start time.',
             'source_url': 'https://kalshi.com/markets/x'},
            {'stage': 'GG.BET esportsbook', 'status': 'unavailable',
             'detail': 'ggbet-cs2: 403 Client Error: Forbidden', 'source_url': 'https://gg.bet/x'},
            {'stage': 'Research model cross-check (Valve official ratings)', 'status': 'resolved',
             'detail': 'model', 'source_url': VALVE_URL},
        ]
        ledger = source_ledger(trail)
        self.assertEqual([e['source'] for e in ledger], ['Polymarket', 'Kalshi', 'GG.BET'])
        self.assertEqual([e['outcome'] for e in ledger], ['resolved', 'unresolved', 'unavailable'])
        self.assertEqual(ledger[1]['reason'], 'no matching line')
        self.assertEqual(ledger[2]['reason'], 'HTTP 403 from the runner')
        # Nothing that is not a price source leaks into the ledger.
        self.assertNotIn('HLTV', [e['source'] for e in ledger])
        self.assertNotIn('Valve', [e['source'] for e in ledger])

    def test_first_stage_for_a_source_wins_and_duplicates_are_dropped(self):
        trail = [
            {'stage': 'Esportsbook line (Pinnacle original prices)', 'status': 'unresolved',
             'detail': 'No alias-verified Pinnacle match-winner line found.', 'source_url': 'https://www.pinnacle.com/x'},
            {'stage': 'Pinnacle esportsbook', 'status': 'unavailable',
             'detail': 'Redirected to a generic landing page', 'source_url': 'https://www.pinnacle.com/x'},
        ]
        ledger = source_ledger(trail)
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]['outcome'], 'unresolved')

    def test_missing_price_sources_excludes_resolved_ones(self):
        ledger = [{'source': 'Polymarket', 'outcome': 'resolved'},
                  {'source': 'bo3.gg relay', 'outcome': 'not needed'},
                  {'source': 'Kalshi', 'outcome': 'unresolved'}]
        self.assertEqual([e['source'] for e in missing_price_sources(ledger)], ['bo3.gg relay', 'Kalshi'])

    def test_concise_reason_keeps_an_unmapped_failure_verbatim(self):
        self.assertEqual(_concise_reason('Stake', 'stake-cs2: 403 Client Error: Forbidden'),
                         'HTTP 403 from the runner')
        self.assertEqual(_concise_reason('Rivalry', ''), None)
        self.assertIn('no unique market', _concise_reason('Polymarket', 'There is no unique market here.'))


class EvenEstimateTest(unittest.TestCase):
    def test_equal_valve_points_are_explained_with_the_published_numbers(self):
        _, ratings = even_fixture()
        chosen = {'method': 'model', 'probabilities': [0.5, 0.5], 'source_url': VALVE_URL,
                  'inputs': [{'name': 'ex-Zero Tenacity', 'points': 1066, 'standing': 93,
                              'snapshot_date': '2026-10-05'},
                             {'name': 'ex-RUSTEC', 'points': 1066, 'standing': 92,
                              'snapshot_date': '2026-10-05'}]}
        detail, url = even_estimate_explanation(chosen)
        self.assertIn('same 1066 official points', detail)
        self.assertIn('standings 92 and 93', detail)
        self.assertIn('table sort', detail)
        self.assertEqual(url, VALVE_URL)
        self.assertTrue(ratings)

    def test_equal_quoted_odds_are_explained_by_the_prices(self):
        detail, url = even_estimate_explanation({
            'method': 'bookmaker', 'probabilities': [0.5, 0.5],
            'quotes': [{'provider': 'Some Book', 'odds': [1.9, 1.9],
                        'source_url': 'https://example.com/match'}]})
        self.assertIn('Some Book quotes the same 1.90', detail)
        self.assertEqual(url, 'https://example.com/match')

    def test_unknown_shape_falls_back_to_the_probabilities(self):
        detail, _ = even_estimate_explanation({'probabilities': [0.5, 0.5], 'source_url': 'https://x.test'})
        self.assertIn('50.0%', detail)

    def test_fifty_fifty_model_row_publishes_no_side_and_says_why(self):
        match, ratings = even_fixture()
        result = originate_match(match, [], [], ratings, META, REGISTRY, NOW)
        self.assertIsNone(result['pick_index'])
        self.assertEqual(result['origination']['probabilities'], [0.5, 0.5])
        even_notes = [note for note in result['limitations'] if note.startswith('Exactly even estimate')]
        self.assertEqual(len(even_notes), 1)
        self.assertIn('1066 official points', even_notes[0])
        stages = [r['stage'] for r in result['research']]
        self.assertIn('Exactly even estimate (no side published)', stages)
        note = next(r for r in result['research'] if r['stage'].startswith('Exactly even'))
        self.assertEqual(note['status'], 'checked')
        self.assertTrue(note['source_url'].startswith('https://github.com/ValveSoftware/'))


class NamedLimitingFactorTest(unittest.TestCase):
    def test_model_row_names_every_source_that_had_no_price(self):
        match, ratings = even_fixture()
        result = originate_match(match, [], [], ratings, META, REGISTRY, NOW)
        missing = [note for note in result['limitations'] if note.startswith('No usable price from any source')]
        self.assertEqual(len(missing), 1)
        for source in ('Polymarket', 'Kalshi', 'Thunderpick', 'Bovada', 'Pinnacle', 'bo3.gg relay', 'EGamersWorld'):
            self.assertIn(source, missing[0])
        self.assertIn('own model estimate', missing[0])
        # Every source in the ledger's missing set is named in that one sentence.
        named = result['sources_without_price']
        for source in named:
            self.assertIn(source, missing[0])
        self.assertEqual(set(named),
                         {'Polymarket', 'Kalshi', 'Thunderpick', 'Bovada', 'Pinnacle', 'bo3.gg relay', 'EGamersWorld'})

    def test_money_row_does_not_claim_that_nothing_priced_it(self):
        result = originate_match(fixture(), [], [], [], {}, REGISTRY, NOW, relay=[relay_row()])
        self.assertEqual(result['origination']['family'], 'relay')
        self.assertFalse([n for n in result['limitations'] if n.startswith('No usable price')])
        relay = next(e for e in result['sources_checked'] if e['source'] == 'bo3.gg relay')
        self.assertEqual(relay['outcome'], 'resolved')
        self.assertNotIn('bo3.gg relay', result['sources_without_price'])

    def test_unresolved_row_says_the_pick_stays_blank(self):
        result = originate_match(fixture(), [], [], [], {}, REGISTRY, NOW)
        self.assertIsNone(result['origination'])
        note = [n for n in result['limitations'] if n.startswith('Nothing priced this fixture')]
        self.assertEqual(len(note), 1)
        self.assertIn('pick stays blank', note[0])
        # The ledger still records what was checked; nothing in it priced the row.
        self.assertTrue(result['sources_checked'])
        self.assertEqual({e['outcome'] for e in result['sources_checked']}, {'unresolved'})

    def test_ledger_is_json_serialisable_and_one_entry_per_source(self):
        import json
        match, ratings = even_fixture()
        result = originate_match(match, [], [], ratings, META, REGISTRY, NOW)
        json.dumps(result['sources_checked'])
        sources = [e['source'] for e in result['sources_checked']]
        self.assertEqual(len(sources), len(set(sources)))


if __name__ == '__main__':
    unittest.main()
