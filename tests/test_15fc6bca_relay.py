"""Tests for session 15fc6bca's relayed-bookmaker rung.

Contract under test
-------------------
bo3.gg relays a named bookmaker's own two-sided prematch decimal prices on the
fixtures its pages list (``bet_updates``). The rung built on top of that relay

1. joins only on BOTH team names (exact or through the reviewed alias registry)
   plus a start time inside ``RELAY_START_TOLERANCE_SEC``, and stores the
   Hotspawn fixture id the join proved;
2. re-validates every input at pricing time — freshness, prematch observation,
   explicit ``active`` on both sides, decimal odds above 1.01 and a paired
   margin inside the published acceptance band;
3. is labelled as a relay wherever it is published and never enters a
   first-party consensus;
4. ranks below every first-party quote and above the aggregated reference and
   the research models, and is marked "not needed" when a higher rung wins.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.originate import (RELAY_START_TOLERANCE_SEC, bo3_relay_rows,
                               collect_bo3_relay, originate_match,
                               relay_join, relayed_bookmaker_estimate)

UTC = timezone.utc
NOW = datetime(2026, 10, 22, 1, 0, 0, tzinfo=UTC)

REGISTRY = {'aliases': [], 'updated_at': '2026-10-01'}


def fixture(name_a='Imperial', name_b='Turma do Pagode', start='2026-10-22T14:00:00Z'):
    return {'id': '1082688', 'teams': [{'id': '1', 'name': name_a}, {'id': '2', 'name': name_b}],
            'competition': 'Circuit X Curitiba #4', 'starts_at': start,
            'locks_at': '2026-10-22T13:54:00Z', 'availability': 'open',
            'source_url': 'https://www.hotspawn.com/matches/imperial-vs-turma-do-pagode-1082688',
            'research': [], 'limitations': [], 'analysis': None, 'pick_index': None}


def relay_row(*, names=('Imperial', 'Turma do Pagode'), odds=(1.22, 3.8), active=(True, True),
              start='2026-10-22T14:00:00Z', observed_at='2026-10-22T00:30:00Z',
              provider='thunderpick', fixture_id='1082688'):
    return {'family': 'relay', 'provider': provider, 'names': list(names), 'odds': list(odds),
            'active': list(active), 'start': start, 'start_delta_sec': 0,
            'observed_at': observed_at,
            'source_url': 'https://bo3.gg/matches/imperial-vs-turma-do-pagode-22-10-2026',
            'book_url': 'https://thunderpick.io/match/2859701', 'event_id': 131954,
            'fixture_id': fixture_id,
            'evidence_file': 'data/origination/evidence/live-bo3-relay.json'}


class RelayJoinTest(unittest.TestCase):
    def test_both_names_and_time_must_match(self):
        canon, _, status = relay_join(['Imperial', 'Turma do Pagode'], '2026-10-22T14:00:00.000+00:00',
                                      fixture(), REGISTRY)
        self.assertEqual(status, 'matched')
        self.assertEqual(canon, ['imperial', 'turma do pagode'])

    def test_one_matching_team_is_not_a_join(self):
        _, _, status = relay_join(['Imperial', 'Some Other Team'], '2026-10-22T14:00:00Z',
                                  fixture(), REGISTRY)
        self.assertEqual(status, 'names')

    def test_start_outside_relay_tolerance_is_rejected(self):
        _, _, status = relay_join(['Imperial', 'Turma do Pagode'], '2026-10-22T15:00:00Z',
                                  fixture(), REGISTRY)
        self.assertEqual(status, 'time')
        # ... and the tolerance is the project-wide 60-second money window, so a
        # ten-minute disagreement stays a rejection (no relaxed matching).
        _, _, still = relay_join(['Imperial', 'Turma do Pagode'], '2026-10-22T14:00:30Z',
                                 fixture(), REGISTRY)
        self.assertEqual(still, 'matched')
        self.assertEqual(RELAY_START_TOLERANCE_SEC, 60)

    def test_alias_registry_is_the_only_relaxation(self):
        registry = {'updated_at': '2026-10-01', 'aliases': [{
            'alias': 'Betclic Apogee Esports', 'canonical': 'Apogee Betclic', 'kind': 'name',
            'applies_to': ['Circuit X Curitiba #4'],
            'evidence': [{'url': 'https://www.hltv.org/team/1/x', 'source': 'HLTV'}]}]}
        match = fixture('UNiTY', 'Apogee Betclic')
        _, _, status = relay_join(['UNiTY', 'Betclic Apogee Esports'], '2026-10-22T14:00:00Z',
                                  match, registry)
        self.assertEqual(status, 'matched')
        # The same alias outside the competition it declares is not applied.
        other = dict(match, competition='Another Event')
        _, _, status = relay_join(['UNiTY', 'Betclic Apogee Esports'], '2026-10-22T14:00:00Z',
                                  other, registry)
        self.assertEqual(status, 'names')


class RelayedQuoteTest(unittest.TestCase):
    def test_price_is_de_vigged_and_aligned_to_the_hotspawn_sides(self):
        quote, detail = relayed_bookmaker_estimate(relay_row(), fixture(), REGISTRY, now=NOW)
        self.assertIsNotNone(quote)
        self.assertEqual(quote['family'], 'relay')
        self.assertIn('relayed by bo3.gg', quote['provider'])
        self.assertTrue(quote['provider'].startswith('Thunderpick'))
        self.assertAlmostEqual(sum(quote['probabilities']), 1.0, places=9)
        # 1.22 / 3.80 => Imperial is the favourite after the margin is removed.
        self.assertGreater(quote['probabilities'][0], quote['probabilities'][1])
        self.assertAlmostEqual(quote['probabilities'][0], (1 / 1.22) / (1 / 1.22 + 1 / 3.8), places=7)
        self.assertGreater(quote['overround'], 0)
        self.assertIn('not from the bookmaker', detail)

    def test_bookmaker_sides_printed_in_reverse_are_realigned(self):
        row = relay_row(names=('Turma do Pagode', 'Imperial'), odds=(3.8, 1.22))
        quote, _ = relayed_bookmaker_estimate(row, fixture(), REGISTRY, now=NOW)
        self.assertIsNotNone(quote)
        self.assertEqual(quote['odds'], [1.22, 3.8])
        self.assertGreater(quote['probabilities'][0], quote['probabilities'][1])

    def test_suspended_side_is_rejected(self):
        quote, detail = relayed_bookmaker_estimate(relay_row(active=(True, False)), fixture(), REGISTRY, now=NOW)
        self.assertIsNone(quote)
        self.assertIn('suspended', detail)

    def test_missing_active_flag_is_rejected(self):
        quote, detail = relayed_bookmaker_estimate(relay_row(active=(True, None)), fixture(), REGISTRY, now=NOW)
        self.assertIsNone(quote)
        self.assertIn('suspended', detail)

    def test_odds_at_or_below_one_are_rejected(self):
        for odds in ((1.0, 3.8), (0.9, 1.2)):
            quote, _ = relayed_bookmaker_estimate(relay_row(odds=odds), fixture(), REGISTRY, now=NOW)
            self.assertIsNone(quote, odds)

    def test_margin_outside_the_acceptance_band_is_rejected(self):
        quote, detail = relayed_bookmaker_estimate(relay_row(odds=(1.02, 1.02)), fixture(), REGISTRY, now=NOW)
        self.assertIsNone(quote)
        self.assertIn('margin', detail)

    def test_stale_and_future_observations_are_rejected(self):
        quote, detail = relayed_bookmaker_estimate(
            relay_row(observed_at='2026-10-21T10:00:00Z'), fixture(), REGISTRY, now=NOW)
        self.assertIsNone(quote)
        self.assertIn('stale', detail)
        quote, _ = relayed_bookmaker_estimate(
            relay_row(observed_at='2026-10-22T02:00:00Z'), fixture(), REGISTRY, now=NOW)
        self.assertIsNone(quote)

    def test_post_start_observation_is_rejected(self):
        quote, detail = relayed_bookmaker_estimate(
            relay_row(start='2026-10-22T00:00:00Z', observed_at='2026-10-22T00:30:00Z'),
            fixture(start='2026-10-22T00:00:00Z'), REGISTRY, now=NOW)
        self.assertIsNone(quote)
        self.assertIn('prematch', detail)


class RelayLadderTest(unittest.TestCase):
    def _originate(self, relay, *, poly=(), ratings=()):
        return originate_match(fixture(), list(poly), [], ratings, {}, REGISTRY, NOW, relay=list(relay))

    def test_relay_prices_a_fixture_no_first_party_source_resolved(self):
        result = self._originate([relay_row()])
        chosen = result['origination']
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen['method'], 'bookmaker')
        self.assertEqual(chosen['family'], 'relay')
        self.assertIn('relayed by bo3.gg', chosen['label'])
        self.assertEqual(result['pick_index'], 0)
        self.assertTrue(any('relayed by bo3.gg' in note for note in result['limitations']))
        stage = [r for r in result['research'] if 'relayed by bo3.gg' in r['stage']][0]
        self.assertEqual(stage['status'], 'resolved')
        self.assertTrue(stage['source_url'].startswith('https://bo3.gg/matches/'))

    def test_first_party_quote_wins_and_relay_is_marked_not_needed(self):
        poly = [{'provider': 'Polymarket', 'family': 'market', 'names': ['Imperial', 'Turma do Pagode'],
                 'start': '2026-10-22T14:00:00Z', 'bid': [0.70, 0.27], 'ask': [0.72, 0.30],
                 'observed_at': '2026-10-22T00:30:00Z', 'source_url': 'https://polymarket.com/event/x',
                 'event_id': '1', 'market_id': 'm1',
                 'evidence_file': 'data/origination/evidence/live-polymarket-observations.json'}]
        result = self._originate([relay_row()], poly=poly)
        self.assertEqual(result['origination']['method'], 'market')
        stage = [r for r in result['research'] if 'relayed by bo3.gg' in r['stage']][0]
        self.assertEqual(stage['status'], 'not needed')

    def test_relay_outranks_the_aggregated_reference_and_the_models(self):
        reference = [{'fixture_id': '1082688', 'names': ['Imperial', 'Turma do Pagode'],
                      'odds': [1.5, 2.4], 'start': '2026-10-22T14:00:00Z',
                      'observed_at': '2026-10-22T00:10:00Z',
                      'source_url': 'https://egamersworld.com/counterstrike/matches'}]
        result = originate_match(fixture(), [], [], [], {}, REGISTRY, NOW,
                                 reference=reference, relay=[relay_row()])
        self.assertEqual(result['origination']['family'], 'relay')

    def test_relay_from_another_fixture_is_ignored(self):
        result = self._originate([relay_row(fixture_id='999999')])
        self.assertIsNone(result['origination'])
        self.assertIsNone(result['pick_index'])

    def test_relay_is_never_a_consensus_vote(self):
        rows = [relay_row(provider='thunderpick'), relay_row(provider='some other book')]
        result = self._originate(rows)
        self.assertNotEqual(result['origination']['method'], 'consensus')
        self.assertEqual(result['origination']['method'], 'bookmaker')

    def test_no_relay_row_reports_an_unresolved_stage(self):
        result = self._originate([])
        stage = [r for r in result['research'] if 'relayed by bo3.gg' in r['stage']][0]
        self.assertEqual(stage['status'], 'unresolved')
        self.assertIsNone(result['origination'])


class RelayCollectionTest(unittest.TestCase):
    class Stub:
        def get_json(self, url, label, headers=None, save=True):
            return {'results': [
                {'id': 131954, 'slug': 'imperial-vs-turma-do-pagode-22-10-2026',
                 'start_date': '2026-10-22T14:00:00.000+00:00', 'bo_type': 3,
                 'tournament': {'name': 'Circuit X Curitiba 4'},
                 'team1': {'id': 52, 'name': 'Imperial'}, 'team2': {'id': 98, 'name': 'Turma do Pagode'},
                 'bet_updates': {'provider': 'thunderpick', 'path': 'https://thunderpick.io/match/2859701',
                                 'team_1': {'team_id': 52, 'name': 'Imperial', 'coeff': 1.22, 'active': True},
                                 'team_2': {'team_id': 98, 'name': 'Turma do Pagode', 'coeff': 3.8, 'active': True}}},
                {'id': 200001, 'slug': 'wrong-start', 'start_date': '2026-10-22T20:00:00.000+00:00',
                 'team1': {'id': 52, 'name': 'Imperial'}, 'team2': {'id': 98, 'name': 'Turma do Pagode'},
                 'bet_updates': {'provider': 'other', 'team_1': {'team_id': 52, 'coeff': 2.0, 'active': True},
                                 'team_2': {'team_id': 98, 'coeff': 2.0, 'active': True}}},
                {'id': 200002, 'slug': 'no-quote', 'start_date': '2026-10-22T14:00:00.000+00:00',
                 'team1': {'id': 1, 'name': 'Other A'}, 'team2': {'id': 2, 'name': 'Other B'}},
            ]}, {'observed_at': '2026-10-22T00:30:00Z', 'status': 'ok'}

    def test_only_the_bound_fixture_is_saved_with_its_quote(self):
        # This collection record stamps the live wall clock. Keep the fixture
        # safely in the future so the contract test does not become a post-start
        # rejection on the date baked into the old fixture (2026-10-22 14:00Z).
        # Observed in Pages run 39792708185 after the scheduled job ran past 14Z.
        start_dt = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=24)
        start = start_dt.isoformat().replace('+00:00', 'Z')
        lock = (start_dt - timedelta(minutes=6)).isoformat().replace('+00:00', 'Z')
        future_fixture = fixture(start=start)
        future_fixture['locks_at'] = lock

        class FutureStartStub(RelayCollectionTest.Stub):
            def get_json(self, url, label, headers=None, save=True):
                body, entry = super().get_json(url, label, headers, save)
                body['results'][0]['start_date'] = start
                return body, entry

        with TemporaryDirectory() as tmp:
            summary = collect_bo3_relay(FutureStartStub(), Path(tmp), [future_fixture], REGISTRY)
            self.assertEqual(summary['fixtures_bound'], 1)
            document = json.loads((Path(tmp) / 'live-bo3-relay.json').read_text())
            record = document['fixtures'][0]
            self.assertEqual(record['hotspawn_id'], '1082688')
            self.assertEqual(record['bo3_url'], 'https://bo3.gg/matches/imperial-vs-turma-do-pagode-22-10-2026')
            self.assertEqual(record['provider'], 'thunderpick')
            self.assertEqual([s['coeff'] for s in record['sides']], [1.22, 3.8])
            # ... and the same document reloads as a row the ladder can price.
            rows = bo3_relay_rows(Path(tmp))
            self.assertEqual(rows[0]['fixture_id'], '1082688')
            # The collector stamps the wall clock, so replay against it.
            quote, _ = relayed_bookmaker_estimate(rows[0], future_fixture, REGISTRY)
            self.assertIsNotNone(quote)

    def test_bookmaker_sides_in_reverse_order_are_aligned_by_team_id(self):
        class Reversed(RelayCollectionTest.Stub):
            def get_json(self, url, label, headers=None, save=True):
                body, entry = super().get_json(url, label, headers, save)
                row = body['results'][0]
                block = row['bet_updates']
                block['team_1'], block['team_2'] = block['team_2'], block['team_1']
                return body, entry
        with TemporaryDirectory() as tmp:
            collect_bo3_relay(Reversed(), Path(tmp), [fixture()], REGISTRY)
            record = json.loads((Path(tmp) / 'live-bo3-relay.json').read_text())['fixtures'][0]
            self.assertEqual([s['name'] for s in record['sides']], ['Imperial', 'Turma do Pagode'])
            self.assertEqual([s['coeff'] for s in record['sides']], [1.22, 3.8])

    def test_a_name_match_with_a_wrong_start_is_recorded_not_priced(self):
        class WrongStart(RelayCollectionTest.Stub):
            def get_json(self, url, label, headers=None, save=True):
                body, entry = super().get_json(url, label, headers, save)
                body['results'][0]['start_date'] = '2026-10-22T15:00:00.000+00:00'
                return body, entry
        with TemporaryDirectory() as tmp:
            summary = collect_bo3_relay(WrongStart(), Path(tmp), [fixture()], REGISTRY)
            self.assertEqual(summary['fixtures_bound'], 0)
            document = json.loads((Path(tmp) / 'live-bo3-relay.json').read_text())
            self.assertEqual(document['fixtures'], [])
            rejection = document['rejections'][0]
            self.assertIn('60s start window', rejection['reason'])
            deltas = [c['start_delta_sec'] for c in rejection['candidates']]
            self.assertIn(3600, deltas)

    def test_absent_document_loads_no_rows(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(bo3_relay_rows(Path(tmp)), [])


if __name__ == '__main__':
    unittest.main()
