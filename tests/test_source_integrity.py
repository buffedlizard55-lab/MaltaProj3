"""Source-integrity and missing-pick coverage regressions. All inputs synthetic.

A provider listing is not a pick until its identity, time, status and complete
paired market are verified. More discovery must never relax these contracts.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import originate
from scripts.domain import iso
from scripts.sources import gamma_games

NOW = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
START = '2026-10-17T12:00:00Z'
REGISTRY = {'aliases': []}
MATCH = {'id': 'synthetic-1', 'competition': 'Synthetic CS2 Cup', 'starts_at': START,
         'teams': [{'id': 'synthetic-a', 'name': 'Synthetic A'}, {'id': 'synthetic-b', 'name': 'Synthetic B'}],
         'source_url': 'https://play.hotspawn.com/cs2-pickems#fixture-synthetic-1'}


def market_row(event_id='synthetic-market-1', provider='Polymarket', *, p=0.6):
    return {'provider': provider, 'family': 'market', 'names': ['Synthetic A', 'Synthetic B'],
            'start': START, 'event_id': event_id, 'market_id': 'synthetic-full-series',
            'source_url': 'https://polymarket.com/event/cs2-synthetic-a-synthetic-b',
            'evidence_file': 'data/origination/evidence/synthetic.json', 'observed_at': iso(NOW),
            'bid': [p - 0.01, 1 - p - 0.01], 'ask': [p + 0.01, 1 - p + 0.01]}


def book_row(event_id='synthetic-book-1'):
    return {'provider': 'Thunderpick', 'family': 'bookmaker', 'names': ['Synthetic A', 'Synthetic B'],
            'start': START, 'event_id': event_id, 'source_url': originate.THUNDERPICK_PAGE,
            'api_url': originate.THUNDERPICK_API, 'evidence_file': 'data/evidence/thunderpick-matches.json',
            'observed_at': iso(NOW), 'odds': [1.5, 2.5]}


def thunderpick_event():
    return {'id': 'synthetic-book-1', 'gameId': 6, 'isLive': False, 'startTime': START,
            'teams': {'home': {'name': 'Synthetic A'}, 'away': {'name': 'Synthetic B'}},
            'market': {'name': 'Match Winner', 'status': 1, 'draw': None,
                       'home': {'name': 'Synthetic A', 'odds': 1.5, 'status': 1},
                       'away': {'name': 'Synthetic B', 'odds': 2.5, 'status': 1}}}


class OriginalBookIdentity(unittest.TestCase):
    def rows(self, event):
        live = {'thunderpick': {'ok': True, 'data': {'upcoming': [event]}},
                'requests': [{'id': 'live-thunderpick-matches', 'status': 'ok', 'observed_at': iso(NOW)}]}
        with tempfile.TemporaryDirectory() as tmp:
            return originate.thunderpick_rows(Path(tmp), live)

    def test_event_teams_cannot_disagree_with_the_priced_outcomes(self):
        event = thunderpick_event()
        event['teams']['home']['name'] = 'Different organization'
        self.assertEqual(self.rows(event), [], 'the old check compared the outcome names to themselves')

    def test_reverse_outcome_order_is_valid_when_the_event_pair_is_the_same(self):
        event = thunderpick_event()
        event['market']['home'], event['market']['away'] = event['market']['away'], event['market']['home']
        rows = self.rows(event)
        self.assertEqual(len(rows), 1)
        quote, reason = originate.bookmaker_estimate(rows[0], MATCH, REGISTRY, now=NOW)
        self.assertIsNotNone(quote, reason)
        self.assertEqual(quote['odds'], [1.5, 2.5])

    def test_missing_duplicate_and_nonstring_event_names_are_rejected(self):
        for bad in (None, '', 'Synthetic B', {'name': 'Synthetic A'}):
            with self.subTest(name=bad):
                event = thunderpick_event()
                event['teams']['home']['name'] = bad
                self.assertEqual(self.rows(event), [])

    def test_inplay_suspended_and_map_markets_are_rejected(self):
        for field in ('live', 'market', 'outcome', 'map'):
            with self.subTest(field=field):
                event = thunderpick_event()
                if field == 'live': event['isLive'] = True
                elif field == 'market': event['market']['status'] = 0
                elif field == 'outcome': event['market']['away']['status'] = 0
                else: event['market']['name'] = 'Map 1 Winner'
                self.assertEqual(self.rows(event), [])


class UniqueIndependentProvider(unittest.TestCase):
    def resolve(self, markets, books=()):
        return originate.originate_match(MATCH, list(markets), list(books), [], None, REGISTRY, NOW)

    def test_two_matching_events_from_one_provider_do_not_select_the_first(self):
        result = self.resolve([market_row(), market_row('another-event', p=0.35)])
        self.assertIsNone(result['origination'])
        self.assertIsNone(result['pick_index'])
        self.assertTrue(any('ambig' in r.get('detail', '').lower() or 'multiple' in r.get('detail', '').lower()
                            for r in result['research']))

    def test_two_full_series_markets_inside_one_event_are_also_ambiguous(self):
        first = market_row()
        other = dict(first, market_id='another-series-market')
        self.assertIsNone(self.resolve([first, other])['origination'])

    def test_an_exact_repeated_observation_is_not_a_second_provider_vote(self):
        one = market_row()
        result = self.resolve([one, copy.deepcopy(one)])
        self.assertIsNotNone(result['origination'])
        self.assertEqual(len(result['origination']['quotes']), 1)
        self.assertEqual(result['origination']['probabilities'], [0.6, 0.4])

    def test_conflicting_observations_of_the_same_market_fail_closed(self):
        first = market_row()
        other = market_row(p=0.35)
        self.assertIsNone(self.resolve([first, other])['origination'])

    def test_a_different_unique_provider_can_still_resolve_the_fixture(self):
        result = self.resolve([market_row(), market_row('duplicate', p=0.35),
                               market_row('other-provider-event', 'Kalshi', p=0.55)])
        self.assertEqual(result['origination']['probabilities'], [0.55, 0.45])
        self.assertEqual([q['provider'] for q in result['origination']['quotes']], ['Kalshi'])
        self.assertNotEqual(result['origination']['method'], 'consensus')

    def test_bookmaker_uses_the_explicit_evaluation_clock_not_wall_time(self):
        quote, reason = originate.bookmaker_estimate(book_row(), MATCH, REGISTRY, now=NOW)
        self.assertIsNotNone(quote, reason)
        later = NOW + timedelta(hours=9)
        quote, reason = originate.bookmaker_estimate(book_row(), MATCH, REGISTRY, now=later)
        self.assertIsNone(quote)

    def test_two_matching_book_events_are_not_a_consensus(self):
        result = self.resolve([], [book_row(), book_row('duplicate-event')])
        self.assertIsNone(result['origination'])


class RetainedTagDiscovery(unittest.TestCase):
    def seed(self, root: Path, *, observed=iso(NOW), request_ok=True):
        (root / 'evidence').mkdir(parents=True)
        origin = 'data/evidence/polymarket-discovery-0.json'
        event = {'id': 'synthetic-tag-only', 'slug': 'cs2-synthetic-a-synthetic-b', 'tags': [{'slug': 'cs2'}],
                 'markets': [{'sportsMarketType': 'moneyline', 'question': 'Synthetic A vs Synthetic B (BO3)',
                              'outcomes': ['Synthetic A', 'Synthetic B'], 'gameStartTime': START}]}
        body = [event]
        (root / 'evidence/polymarket-discovery-0.json').write_text(json.dumps(body))
        games = gamma_games(body, origin)
        (root / 'evidence/polymarket-index.json').write_text(json.dumps(games))
        request = {'id': 'polymarket-discovery-0', 'url': 'https://gamma-api.polymarket.com/events?tag_slug=cs2',
                   'observed_at': observed, 'status': 'ok' if request_ok else 'error', 'evidence': origin}
        (root / 'latest.json').write_text(json.dumps({'requests': [request]}))
        return games[0]

    def supplement(self, root, directory=()):
        return originate.supplement_polymarket_discovery(list(directory), root, NOW)

    def test_tag_only_identity_is_researched_even_when_not_visible_in_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = self.seed(root)
            games, audit = self.supplement(root)
            self.assertEqual([g['id'] for g in games], [game['id']])
            self.assertEqual(audit['supplemental_identities'], 1)
            self.assertFalse(audit['prices_used'])

    def test_duplicate_directory_and_tag_identity_fetches_one_event_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = self.seed(root)
            games, _ = self.supplement(root, [dict(game)])
            self.assertEqual(len(games), 1)

    def test_missing_or_failed_original_request_cannot_supply_a_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed(root, request_ok=False)
            games, audit = self.supplement(root)
            self.assertEqual(games, [])
            self.assertTrue(audit['limitations'])

    def test_stale_discovery_is_not_restamped_as_current_research(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed(root, observed=iso(NOW - timedelta(hours=9)))
            games, _ = self.supplement(root)
            self.assertEqual(games, [])

    def test_index_identity_must_replay_from_its_original_tagged_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed(root)
            index = json.loads((root / 'evidence/polymarket-index.json').read_text())
            index[0]['homeName'] = 'Invented provider name'
            (root / 'evidence/polymarket-index.json').write_text(json.dumps(index))
            games, audit = self.supplement(root)
            self.assertEqual(games, [])
            self.assertTrue(audit['limitations'])

    def test_discovery_path_cannot_escape_source_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.seed(root)
            index = json.loads((root / 'evidence/polymarket-index.json').read_text())
            index[0]['discovery_evidence'] = '../../outside.json'
            (root / 'evidence/polymarket-index.json').write_text(json.dumps(index))
            games, _ = self.supplement(root)
            self.assertEqual(games, [])


class OriginalStateReplay(unittest.TestCase):
    """A summarized price must fail if its full original state cannot replay."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'evidence').mkdir()
        (self.root / 'origination/evidence').mkdir(parents=True)
        registry_source = Path(__file__).resolve().parents[1] / 'data/origination/aliases.json'
        (self.root / 'origination/aliases.json').write_text(registry_source.read_text())
        self.raw = dict(copy.deepcopy(MATCH), availability='open', locks_at='2026-10-17T11:54:00Z', analysis=None)
        self.latest = {'inventory_observed_at': iso(NOW), 'matches': [self.raw], 'requests': []}
        self.saved = {'ok': True, 'data': {'upcoming': [thunderpick_event()]}}
        self.path = self.root / 'evidence/thunderpick-matches.json'
        self.path.write_text(json.dumps(self.saved))
        self.latest['requests'] = [{'id': 'thunderpick-matches', 'status': 'ok', 'observed_at': iso(NOW),
                                    'url': originate.THUNDERPICK_API,
                                    'evidence': 'data/evidence/thunderpick-matches.json'}]
        self.write_latest()
        result = originate.originate_match(self.raw, [], [book_row()], [], None, REGISTRY, NOW)
        self.data = {'source_snapshot_at': iso(NOW), 'generated_at': iso(NOW),
                     'matches': [dict(self.raw, **result)]}

    def write_latest(self):
        (self.root / 'latest.json').write_text(json.dumps(self.latest))

    def validate(self):
        from scripts.build_origination import validate_origination
        validate_origination(self.data, self.root)

    def test_valid_original_replays(self):
        self.validate()

    def test_modified_live_market_status_teams_time_and_scope_never_replay(self):
        original = copy.deepcopy(self.saved)
        for field in ('live', 'status', 'team', 'start', 'scope', 'draw', 'response'):
            with self.subTest(field=field):
                self.saved = copy.deepcopy(original)
                event = self.saved['data']['upcoming'][0]
                if field == 'live': event['isLive'] = True
                elif field == 'status': event['market']['away']['status'] = 0
                elif field == 'team': event['teams']['home']['name'] = 'An unrelated organization'
                elif field == 'start': event['startTime'] = '2026-10-17T13:00:00Z'
                elif field == 'scope': event['market']['name'] = 'Map 1 Winner'
                elif field == 'draw': event['market']['draw'] = {'odds': 2.0}
                else: self.saved['ok'] = False
                self.path.write_text(json.dumps(self.saved))
                with self.assertRaises((AssertionError, ValueError)):
                    self.validate()

    def test_second_original_event_cannot_be_hidden_by_a_summarized_selected_id(self):
        event = copy.deepcopy(self.saved['data']['upcoming'][0])
        event['id'] = 'another-event'
        self.saved['data']['upcoming'].append(event)
        self.path.write_text(json.dumps(self.saved))
        with self.assertRaises((AssertionError, ValueError)):
            self.validate()

    def test_quote_observation_must_equal_the_original_successful_request(self):
        self.latest['requests'][0]['observed_at'] = iso(NOW - timedelta(hours=1))
        self.write_latest()
        with self.assertRaises((AssertionError, ValueError)):
            self.validate()

    def test_fixture_deadlines_and_availability_are_not_rewritten(self):
        row = self.data['matches'][0]
        row['locks_at'] = '2026-10-17T11:59:00Z'
        with self.assertRaises((AssertionError, ValueError)):
            self.validate()

    def test_quote_path_cannot_escape_data_directory(self):
        from scripts.pipeline_audit import evidence_path
        with self.assertRaises(AssertionError):
            evidence_path(self.root, 'data/../outside.json')


class EstimateInputContract(unittest.TestCase):
    def test_paired_books_need_exactly_two_finite_values_on_both_sides(self):
        for bid, ask in (([0.59], [0.61]), ([0.59, 0.39], [0.61]),
                         ([float('nan'), 0.39], [0.61, 0.41]), ([True, 0.39], [0.61, 0.41])):
            with self.subTest(bid=bid, ask=ask):
                row = dict(market_row(), bid=bid, ask=ask)
                quote, reason = originate.market_estimate(row, MATCH, REGISTRY, NOW)
                self.assertIsNone(quote)

    def test_missing_stale_or_future_observation_is_not_filled_with_current_time(self):
        for observation in (None, iso(NOW - timedelta(hours=9)), iso(NOW + timedelta(hours=1))):
            with self.subTest(observation=observation):
                row = dict(market_row(), observed_at=observation)
                quote, reason = originate.market_estimate(row, MATCH, REGISTRY, NOW)
                self.assertIsNone(quote)

    def test_provider_clock_cannot_make_an_inplay_quote_prematch(self):
        row = dict(market_row(), start=iso(NOW - timedelta(seconds=1)))
        quote, _ = originate.market_estimate(row, MATCH, REGISTRY, NOW)
        self.assertIsNone(quote)


if __name__ == '__main__':
    unittest.main()
