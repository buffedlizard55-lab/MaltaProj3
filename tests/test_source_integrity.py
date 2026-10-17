"""Source-integrity and missing-pick coverage regressions. All inputs synthetic.

A provider listing is not a pick until its identity, time, status and complete
paired market are verified. More discovery must never relax these contracts.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import tempfile
import unittest

import requests
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


    def test_alias_aware_live_collection_fetches_tag_only_original_event_and_both_books(self):
        registry = {'aliases': [{'alias': 'Synthetic A', 'canonical': 'Synthetic A Display', 'kind': 'synthetic test only',
                                'applies_to': [MATCH['competition']],
                                'evidence': [{'url': 'https://github.com/buffedlizard55-lab/MaltaProj3',
                                              'detail': 'Synthetic fixture mapping; never published.'}]}]}
        fixture = dict(copy.deepcopy(MATCH), availability='open', analysis=None)
        fixture['teams'][0]['name'] = 'Synthetic A Display'
        event = {'id': 'synthetic-tag-only', 'slug': 'cs2-synthetic-a-synthetic-b',
                 'active': True, 'closed': False, 'live': False,
                 'markets': [{'id': 'synthetic-full-series', 'conditionId': 'synthetic-condition',
                              'sportsMarketType': 'moneyline', 'question': 'Synthetic A vs Synthetic B (BO3)',
                              'active': True, 'closed': False, 'acceptingOrders': True,
                              'outcomes': ['Synthetic A', 'Synthetic B'], 'gameStartTime': START,
                              'clobTokenIds': ['synthetic-token-a', 'synthetic-token-b']}]}
        for directory_fails in (False, True):
            with self.subTest(directory_fails=directory_fails), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.seed(root)
                folder = root / 'origination/evidence'
                seen = []

                def get_json(client, url, label, **kwargs):
                    seen.append(label)
                    if label == 'live-thunderpick-matches': body = {'ok': True, 'data': {'upcoming': []}}
                    elif label.startswith('live-polymarket-event-'): body = event
                    elif label.startswith('live-polymarket-book-'):
                        token = url.split('=')[-1]
                        midpoint = 0.6 if token.endswith('-a') else 0.4
                        body = {'asset_id': token, 'market': 'synthetic-condition',
                                'timestamp': str(int(NOW.timestamp() * 1000)),
                                'bids': [{'price': midpoint - 0.01, 'size': '10'}],
                                'asks': [{'price': midpoint + 0.01, 'size': '10'}]}
                    elif label.startswith('live-kalshi-events-'): body = {'events': [], 'cursor': ''}
                    else: body = []
                    entry = {'id': label, 'url': url, 'observed_at': iso(NOW), 'status': 'ok'}
                    if kwargs.get('save', True): entry['evidence'] = client.save(label, body)
                    client.requests.append(entry)
                    return body, entry

                with patch.object(originate.Collector, 'get_json', new=get_json), \
                        patch.object(originate.Collector, 'fetch_html',
                                     side_effect=RuntimeError('Synthetic unavailable directory') if directory_fails else None,
                                     return_value=('synthetic empty directory', {})), \
                        patch('scripts.sources.polymarket_games', return_value=[]), \
                        patch('scripts.originate.datetime', wraps=datetime) as clock:
                    clock.now.return_value = NOW
                    report = originate.live_collect(folder, [fixture], registry)
                self.assertIn('live-polymarket-event-synthetic-tag-only', seen)
                self.assertIn('live-polymarket-book-synthetic-tag-only-0', seen)
                self.assertIn('live-polymarket-book-synthetic-tag-only-1', seen)
                self.assertEqual(report['polymarket_discovery']['supplemental_identities'], 1)
                self.assertFalse(report['polymarket_discovery']['prices_used'])
                saved = json.loads((folder / 'live-polymarket-observations.json').read_text())
                self.assertEqual(len(saved['polymarket_events']), 1)
                self.assertEqual(saved['polymarket_events'][0]['outcomes'], ['Synthetic A', 'Synthetic B'])
                self.assertEqual(saved['polymarket_events'][0]['observed_at'], iso(NOW))
                self.assertTrue((folder / 'live-discovery-audit.json').is_file())


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


class ExtraProviderOriginalStates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'origination/evidence'
        self.folder.mkdir(parents=True)

    def write(self, name, saved):
        (self.folder / name).write_text(json.dumps(saved))

    def kalshi(self):
        ticker = 'KXCS2GAME-26OCT170800SYNTHETIC'
        event = {'event_ticker': ticker, 'series_ticker': originate.KALSHI_SERIES,
                 'product_metadata': {'competition': 'CS2'}, 'mutually_exclusive': True, 'markets': []}
        for name, suffix, bid, ask in (('Synthetic A', 'A', '0.59', '0.61'), ('Synthetic B', 'B', '0.39', '0.41')):
            event['markets'].append({'ticker': ticker + '-' + suffix, 'yes_sub_title': name, 'status': 'active',
                'rules_primary': 'The game originally scheduled for Oct 17, 2026 at 8:00 AM EDT must complete.',
                'yes_bid_dollars': bid, 'yes_ask_dollars': ask})
        url = originate.KALSHI_EVENTS + '?series_ticker=KXCS2GAME&status=open'
        saved = {'observed_at': iso(NOW), 'pages': [{'url': url, 'observed_at': iso(NOW), 'response': {'events': [event]}}]}
        self.write('live-kalshi-events.json', saved)
        self.write('live-collection-manifest.json', [{'id': 'live-kalshi-events-0', 'url': url,
                                                     'status': 'ok', 'observed_at': iso(NOW)}])
        row = originate.kalshi_rows(self.folder)[0]
        quote, reason = originate.market_estimate(row, MATCH, REGISTRY, NOW)
        self.assertIsNotNone(quote, reason)
        return saved, event, quote

    def bovada(self):
        outcomes = [{'description': 'Synthetic A', 'status': 'O', 'price': {'decimal': '1.5'}},
                    {'description': 'Synthetic B', 'status': 'O', 'price': {'decimal': '2.5'}}]
        market = {'id': 'synthetic-moneyline', 'key': '2W-12', 'description': 'Moneyline', 'status': 'O',
                  'period': {'main': True, 'live': False}, 'outcomes': outcomes}
        event = {'id': 'synthetic-bovada-1', 'type': 'GAMEEVENT', 'live': False,
                 'startTime': int(originate.timestamp(START).timestamp() * 1000),
                 'link': '/esports/counter-strike-2/synthetic-a-vs-synthetic-b',
                 'competitors': [{'name': 'Synthetic A'}, {'name': 'Synthetic B'}],
                 'displayGroups': [{'markets': [market]}]}
        saved = {'observed_at': iso(NOW), 'url': originate.BOVADA_API,
                 'response': [{'path': [{'description': MATCH['competition']}], 'events': [event]}]}
        self.write('live-bovada-cs2.json', saved)
        self.write('live-collection-manifest.json', [{'id': 'live-bovada-cs2', 'url': originate.BOVADA_API,
                                                     'status': 'ok', 'observed_at': iso(NOW)}])
        row = originate.bovada_rows(self.folder)[0]
        quote, reason = originate.bookmaker_estimate(row, MATCH, REGISTRY, now=NOW)
        self.assertIsNotNone(quote, reason)
        return saved, event, quote

    def replay(self, q):
        from scripts.pipeline_audit import replay_provider_quote
        return replay_provider_quote(q, MATCH, REGISTRY, self.root, NOW)

    def test_kalshi_original_paired_series_replays(self):
        _, _, quote = self.kalshi()
        self.assertEqual(self.replay(quote), 0.6)

    def test_kalshi_original_status_rules_start_and_competition_are_checked(self):
        for field in ('status', 'rules', 'competition', 'exclusive', 'start', 'team'):
            with self.subTest(field=field):
                saved, event, quote = self.kalshi()
                if field == 'status': event['markets'][0]['status'] = 'settled'
                elif field == 'rules': event['markets'][0]['rules_primary'] = 'Unverified schedule'
                elif field == 'competition': event['product_metadata']['competition'] = 'Basketball'
                elif field == 'exclusive': event['mutually_exclusive'] = False
                elif field == 'start':
                    for market in event['markets']:
                        market['rules_primary'] = market['rules_primary'].replace('8:00 AM', '9:00 AM')
                else: event['markets'][0]['yes_sub_title'] = 'Unrelated team'
                self.write('live-kalshi-events.json', saved)
                with self.assertRaises((AssertionError, ValueError)):
                    self.replay(quote)

    def test_bovada_original_paired_series_replays(self):
        _, _, quote = self.bovada()
        self.assertEqual(self.replay(quote), 0.625)

    def test_bovada_original_inplay_status_competitors_and_period_are_checked(self):
        for field in ('live', 'market', 'outcome', 'team', 'period', 'start'):
            with self.subTest(field=field):
                saved, event, quote = self.bovada()
                market = event['displayGroups'][0]['markets'][0]
                if field == 'live': event['live'] = True
                elif field == 'market': market['status'] = 'S'
                elif field == 'outcome': market['outcomes'][0]['status'] = 'S'
                elif field == 'team': event['competitors'][0]['name'] = 'Unrelated team'
                elif field == 'period': market['period']['main'] = False
                else: event['startTime'] += 3600000
                self.write('live-bovada-cs2.json', saved)
                with self.assertRaises((AssertionError, ValueError)):
                    self.replay(quote)

    def test_an_extra_matching_bovada_moneyline_is_ambiguous(self):
        saved, event, quote = self.bovada()
        second = copy.deepcopy(event['displayGroups'][0]['markets'][0])
        second['id'] = 'a-second-series-market'
        event['displayGroups'][0]['markets'].append(second)
        self.write('live-bovada-cs2.json', saved)
        with self.assertRaises((AssertionError, ValueError)):
            self.replay(quote)

    def test_request_time_does_not_get_replaced_with_wrapper_time(self):
        _, _, quote = self.kalshi()
        manifest = json.loads((self.folder / 'live-collection-manifest.json').read_text())
        manifest[0]['observed_at'] = iso(NOW - timedelta(hours=1))
        self.write('live-collection-manifest.json', manifest)
        with self.assertRaises((AssertionError, ValueError)):
            self.replay(quote)


class RowRegister(unittest.TestCase):
    def test_dated_repository_snapshot_is_audited_without_being_restamped(self):
        from scripts.pipeline_audit import audit
        source = Path(__file__).resolve().parents[1] / 'data'
        before = {name: (source / name).read_bytes() for name in ('latest.json', 'origination.json')}
        report = audit(source, NOW)
        for name in before:
            self.assertEqual(before[name], (source / name).read_bytes())
        self.assertEqual(report['counts']['audited_rows'], report['counts']['canonical_nonpast_fixtures'])
        self.assertFalse(report['inventory_fresh_at_audit'])
        self.assertEqual(report['counts']['currently_usable_lines'], 0)
        self.assertTrue(all(r['featured_facts_unchanged'] for r in report['rows']))
        for row in report['rows']:
            self.assertTrue(row['sources'])
            self.assertTrue(all(s['url'].startswith('https://') for s in row['sources']))


class LiveValveOriginalReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'evidence').mkdir()
        self.folder = self.root / 'origination/evidence'
        self.folder.mkdir(parents=True)
        registry_source = Path(__file__).resolve().parents[1] / 'data/origination/aliases.json'
        (self.root / 'origination/aliases.json').write_text(registry_source.read_text())
        self.raw = dict(copy.deepcopy(MATCH), availability='open', locks_at='2026-10-17T11:54:00Z', analysis=None)
        self.latest = {'inventory_observed_at': iso(NOW), 'matches': [self.raw], 'requests': []}
        self.primary = self.seed_valve(False, 1200, '2026-10-05', NOW - timedelta(hours=1))
        self.live = self.seed_valve(True, 1400, '2026-10-16', NOW)
        (self.root / 'latest.json').write_text(json.dumps(self.latest))

    def seed_valve(self, live, points, day, observed):
        from scripts.domain import parse_valve_table
        text = (f'| 1 | {points} | Synthetic A | a1, a2, a3, a4, a5 | details |\n'
                '| 2 | 1000 | Synthetic B | b1, b2, b3, b4, b5 | details |\n')
        raw = text.encode()
        path = 'live/2026/standings_global_' + day.replace('-', '_') + '.md'
        url = 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/' + path
        sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        original = {'path': path, 'sha': sha, 'html_url': url, 'encoding': 'base64',
                    'content': base64.b64encode(raw).decode()}
        directory = [{'name': path.split('/')[-1], 'path': path, 'sha': sha, 'html_url': url}]
        if live:
            payload = {'snapshot_date': day, 'source_url': url, 'text_sha256': hashlib.sha256(raw).hexdigest(), 'text': text}
            (self.folder / 'live-valve-standings.json').write_text(json.dumps(original))
            (self.folder / 'live-valve-directory.json').write_text(json.dumps(directory))
            (self.folder / 'live-valve-standings-text.json').write_text(json.dumps(payload))
            requests_ = [{'id': 'live-valve-standings', 'url': originate.VALVE_REPO + '/contents/' + path,
                          'evidence': 'live-valve-standings.json',
                          'status': 'ok', 'observed_at': iso(observed)},
                         {'id': 'live-valve-directory', 'url': originate.VALVE_REPO + '/contents/live/2026',
                          'evidence': 'live-valve-directory.json',
                          'status': 'ok', 'observed_at': iso(observed)}]
            (self.folder / 'live-collection-manifest.json').write_text(json.dumps(requests_))
        else:
            payload = {'snapshot_date': day, 'source_url': url, 'git_blob_sha': sha,
                       'rows': parse_valve_table(text, url, day)}
            (self.root / 'evidence/valve-standings-response.json').write_text(json.dumps(original))
            (self.root / 'evidence/valve-directory.json').write_text(json.dumps(directory))
            (self.root / 'evidence/valve-ratings.json').write_text(json.dumps(payload))
            requests_ = [{'id': 'valve-standings-response', 'url': originate.VALVE_REPO + '/contents/' + path,
                          'evidence': 'data/evidence/valve-standings-response.json',
                          'status': 'ok', 'observed_at': iso(observed)}]
            self.latest['requests'].extend(requests_)
        return {'requests': requests_}

    def test_fresh_live_model_replays_live_original_not_a_different_primary_cache(self):
        from scripts.build_origination import validate_origination
        rows, meta = originate.valve_rows(self.root, self.live)
        result = originate.originate_match(self.raw, [], [], rows, meta, REGISTRY, NOW)
        self.assertIsNotNone(result['origination'])
        data = {'source_snapshot_at': iso(NOW), 'generated_at': iso(NOW),
                'matches': [dict(self.raw, **result)]}
        validate_origination(data, self.root)

    def test_failed_refetch_never_reuses_old_live_text_and_restamps_it(self):
        failed = copy.deepcopy(self.live)
        failed['requests'][0]['status'] = 'error'
        rows, meta = originate.valve_rows(self.root, failed)
        self.assertEqual(meta['evidence_file'], 'data/evidence/valve-ratings.json')
        self.assertEqual(meta['observed_at'], iso(NOW - timedelta(hours=1)))
        self.assertEqual(rows[0]['points'], 1200)

    def test_unverified_decoded_live_text_cannot_override_official_content(self):
        file = self.folder / 'live-valve-standings-text.json'
        payload = json.loads(file.read_text())
        payload['text'] = payload['text'].replace('1400', '1800')
        file.write_text(json.dumps(payload))
        rows, meta = originate.valve_rows(self.root, self.live)
        self.assertEqual(meta['evidence_file'], 'data/evidence/valve-ratings.json')
        self.assertEqual(rows[0]['points'], 1200)

    def test_primary_model_observation_is_not_replaced_by_its_computation_time(self):
        rows, meta = originate.valve_rows(self.root, None)
        quote, reason = originate.model_estimate(self.raw, rows, REGISTRY, meta, NOW)
        self.assertIsNotNone(quote, reason)
        self.assertEqual(quote['observed_at'], iso(NOW - timedelta(hours=1)))
        self.assertEqual(quote['evaluation_at'], iso(NOW))

    def test_primary_derived_ratings_must_match_the_original_official_contents(self):
        file = self.root / 'evidence/valve-ratings.json'
        payload = json.loads(file.read_text())
        payload['rows'][0]['points'] = 1900
        file.write_text(json.dumps(payload))
        with self.assertRaises((AssertionError, ValueError)):
            originate.valve_rows(self.root, None)


class ActualResearchCollectorManifest(unittest.TestCase):
    def test_actual_collector_basename_reference_round_trips_through_source_replay(self):
        from scripts.pipeline_audit import replay_provider_quote
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'origination/evidence'
            client = originate.Collector(folder)
            response = requests.Response()
            response.status_code = 200
            response.url = originate.THUNDERPICK_API
            response.headers['Content-Type'] = 'application/json'
            response._content = json.dumps({'ok': True, 'data': {'upcoming': [thunderpick_event()]}},
                                           separators=(',', ':')).encode()
            with patch.object(client.session, 'request', return_value=response), \
                    patch('scripts.originate.datetime', wraps=datetime) as clock:
                clock.now.return_value = NOW
                body, request = client.get_json(originate.THUNDERPICK_API, 'live-thunderpick-matches',
                                                method='POST', payload={'gameIds': [6]})
            self.assertEqual(request['evidence'], 'live-thunderpick-matches.json')
            (folder / 'live-collection-manifest.json').write_text(json.dumps(client.requests))
            row = originate.thunderpick_rows(root, {'thunderpick': body, 'requests': client.requests})[0]
            quote, reason = originate.bookmaker_estimate(row, MATCH, REGISTRY, now=NOW)
            self.assertIsNotNone(quote, reason)
            self.assertEqual(replay_provider_quote(quote, MATCH, REGISTRY, root, NOW), 0.625)


if __name__ == '__main__':
    unittest.main()
