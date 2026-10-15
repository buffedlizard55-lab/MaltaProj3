"""Synthetic fixtures for logic tests only; never published as match observations."""
import copy
import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.domain import *
from scripts.collect import normalize_fixture, collect
from scripts.sources import hydration, polymarket_games, SourceError

NOW = datetime(2026, 10, 14, 4, 0, tzinfo=timezone.utc)
START = iso(NOW + timedelta(hours=4))
MATCH = {'id': 'synthetic', 'teams': [{'id': 'a', 'name': 'Alpha'}, {'id': 'b', 'name': 'Beta'}], 'starts_at': START}
MARKET = {'id': 'test', 'conditionId': 'condition', 'outcomes': '["Alpha", "Beta"]', 'clobTokenIds': '["a", "b"]', 'gameStartTime': START, 'sportsMarketType': 'moneyline', 'active': True, 'closed': False, 'acceptingOrders': True, 'question': 'Counter-Strike: Alpha vs Beta (BO3)'}
EVENT = {'id': 'example', 'slug': 'cs2-alpha-beta-2026-10-14', 'active': True, 'closed': False, 'markets': [MARKET]}


def book(token='a', bid=.59, ask=.61):
    return {'asset_id': token, 'market': 'condition', 'timestamp': str(int(NOW.timestamp() * 1000)), 'bids': [{'price': str(bid), 'size': '10'}, {'price': '.01', 'size': '1'}], 'asks': [{'price': '.99', 'size': '2'}, {'price': str(ask), 'size': '11'}]}


def rating(name, points=1000, day='2026-10-05', players=5):
    return {'name': name, 'points': points, 'standing': 1, 'roster': [f'p{i}' for i in range(players)], 'snapshot_date': day, 'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'detail_path': 'details/example.md'}


class TimeAndIdentityTests(unittest.TestCase):
    def test_millisecond_epoch(self):
        self.assertEqual(timestamp('1791950400000'), NOW)

    def test_second_epoch(self):
        self.assertEqual(timestamp(NOW.timestamp()), NOW)

    def test_naive_time_not_assumed_utc(self):
        self.assertIsNone(timestamp('2026-10-14T04:00:00'))

    def test_invalid_times(self):
        for value in [None, '', 'not a date', -2, float('nan'), True, 10**40]:
            self.assertIsNone(timestamp(value))

    def test_strict_name_equivalence(self):
        self.assertEqual(name_key(' ALPHA  Team '), 'alpha team')
        self.assertNotEqual(name_key('G2'), name_key('G2 Ares'))
        self.assertNotEqual(name_key('WBT'), name_key('WROTBERRY'))

    def test_swapped_teams(self):
        self.assertTrue(identity_matches(['beta', 'ALPHA'], START, MATCH))
        self.assertEqual(align([.2, .8], ['Beta', 'Alpha'], MATCH), [.8, .2])

    def test_wrong_date_and_alias_rejected(self):
        self.assertFalse(identity_matches(['Alpha', 'Beta'], iso(NOW + timedelta(days=1)), MATCH))
        self.assertFalse(identity_matches(['Alpha Gaming', 'Beta'], START, MATCH))
        self.assertFalse(identity_matches(['Alpha', 'Alpha'], START, MATCH))

    def test_freshness_includes_future_guard(self):
        self.assertTrue(is_fresh(iso(NOW), NOW))
        self.assertFalse(is_fresh(iso(NOW - timedelta(hours=9)), NOW))
        self.assertFalse(is_fresh(iso(NOW + timedelta(hours=1)), NOW))


class MarketTests(unittest.TestCase):
    def test_unique_series_market(self):
        self.assertIsNotNone(polymarket_candidate(EVENT, MATCH, NOW)[0])

    def test_rejects_map_moneyline(self):
        e = copy.deepcopy(EVENT); e['markets'][0]['question'] += ' - Map 1 Winner'
        self.assertIsNone(polymarket_candidate(e, MATCH, NOW)[0])

    def test_rejects_duplicate_markets(self):
        e = copy.deepcopy(EVENT); e['markets'].append(copy.deepcopy(e['markets'][0]))
        self.assertIsNone(polymarket_candidate(e, MATCH, NOW)[0])

    def test_closed_and_no_orders_rejected(self):
        for key, value in [('closed', True), ('acceptingOrders', False), ('active', False)]:
            e = copy.deepcopy(EVENT); e['markets'][0][key] = value
            self.assertIsNone(polymarket_candidate(e, MATCH, NOW)[0])

    def test_missing_scope_rejected(self):
        e = copy.deepcopy(EVENT); del e['markets'][0]['sportsMarketType']
        self.assertIsNone(polymarket_candidate(e, MATCH, NOW)[0])

    def test_best_bid_ask_not_array_order(self):
        self.assertEqual(book_midpoint(book(), 'a', 'condition', NOW)['midpoint'], .6)

    def test_bad_token_and_condition(self):
        with self.assertRaises(ValueError): book_midpoint(book('wrong'), 'a', 'condition', NOW)
        with self.assertRaises(ValueError): book_midpoint(book(), 'a', 'wrong', NOW)

    def test_wide_or_crossed_book_rejected(self):
        for bid, ask in [(.01, .99), (.6, .59)]:
            with self.assertRaises(ValueError): book_midpoint(book(bid=bid, ask=ask), 'a', 'condition', NOW)

    def test_one_sided_book_rejected(self):
        b = book(); b['bids'] = []
        with self.assertRaises(ValueError): book_midpoint(b, 'a', 'condition', NOW)

    def test_stale_book_rejected(self):
        b = book(); b['timestamp'] = str(int((NOW - timedelta(hours=9)).timestamp()*1000))
        with self.assertRaises(ValueError): book_midpoint(b, 'a', 'condition', NOW)

    def test_zero_size_book_rejected(self):
        b = book(); b['bids'] = [{'price': '.5', 'size': '0'}]
        with self.assertRaises(ValueError): book_midpoint(b, 'a', 'condition', NOW)

    def test_market_outputs_replay(self):
        a = market_analysis(EVENT, MARKET, [book('a'), book('b', .39, .41)], MATCH, NOW, iso(NOW))
        self.assertEqual(a['probabilities'], [.6, .4]); self.assertEqual(selection(a), 0)

    def test_exact_tie_has_no_arbitrary_pick(self):
        self.assertIsNone(selection({'probabilities': [.5, .5]}))
        self.assertIsNone(selection(None))


class BookmakerTests(unittest.TestCase):
    def test_no_vig_sum_and_orientation(self):
        p = no_vig([2.0, 1.5]); self.assertAlmostEqual(p[0], 3/7, places=7)
        self.assertAlmostEqual(sum(p), 1)

    def test_invalid_odds(self):
        for odds in [[0, 2], [1, 2], [float('nan'), 2], [2], [100, 100], [1.01, 1.01]]:
            with self.assertRaises(ValueError): no_vig(odds)

    def test_source_families_not_double_counted(self):
        q = {'provider': 'Book', 'family': 'one', 'probabilities': [.7, .3], 'observed_at': iso(NOW), 'source_url': 'https://example.test'}
        a = consensus([q, q], NOW)
        self.assertEqual(len(a['quotes']), 1)
        self.assertEqual(a['probabilities'], [.7, .3])

    def test_stale_sources_not_counted(self):
        q = {'provider': 'Book', 'family': 'one', 'probabilities': [.7, .3], 'observed_at': iso(NOW-timedelta(hours=10)), 'source_url': 'https://example.test'}
        self.assertIsNone(consensus([q], NOW))


class RatingTests(unittest.TestCase):
    def test_rating_formula_and_monotonicity(self):
        a, reason = valve_analysis(MATCH, [rating('Alpha', 1400), rating('Beta', 1000)], NOW, iso(NOW))
        self.assertFalse(reason); self.assertGreater(a['probabilities'][0], .89)
        self.assertLess(a['probabilities'][0], .91); self.assertEqual(selection(a), 0)

    def test_missing_team_never_becomes_average_rating(self):
        self.assertIsNone(valve_analysis(MATCH, [rating('Alpha')], NOW, iso(NOW))[0])

    def test_duplicate_name_never_selects_highest_rating(self):
        rows = [rating('Alpha', 1500), rating('Alpha', 500), rating('Beta')]
        self.assertIsNone(valve_analysis(MATCH, rows, NOW, iso(NOW))[0])

    def test_incomplete_roster_rejected(self):
        self.assertIsNone(valve_analysis(MATCH, [rating('Alpha', players=4), rating('Beta')], NOW, iso(NOW))[0])

    def test_old_or_future_rating_rejected(self):
        for day in ['2026-08-01', '2026-10-15']:
            self.assertIsNone(valve_analysis(MATCH, [rating('Alpha', day=day), rating('Beta')], NOW, iso(NOW))[0])

    def test_no_fuzzy_rating_aliases(self):
        self.assertIsNone(valve_analysis(MATCH, [rating('Alpha Gaming'), rating('Beta')], NOW, iso(NOW))[0])

    def test_valve_markdown_parser(self):
        text = '| 1 | 1234 | Alpha | a, b, c, d, e | [details](details/a.md) |'
        self.assertEqual(parse_valve_table(text, 'https://github.com/ValveSoftware', '2026-10-05')[0]['points'], 1234)


class SourceSafetyTests(unittest.TestCase):
    def test_hydration_contract(self):
        state = {'key': {'s': 200, 'u': 'https://example.test/api/v1/fixtures', 'b': [{'id':'1'}]}}
        rows, _ = hydration('<script id="ng-state" type="application/json">'+json.dumps(state)+'</script>')
        self.assertEqual(rows, [{'id':'1'}])

    def test_missing_hydration_fails_closed(self):
        with self.assertRaises(SourceError): hydration('<html>Loading</html>')

    def test_index_challenge_is_not_empty_success(self):
        with self.assertRaises(SourceError): polymarket_games('<html>Access denied</html>')

    def test_crowd_percent_and_points_are_not_inputs(self):
        raw = {'id': '1', 'scheduled_start_time': START, 'lock_time': iso(NOW+timedelta(hours=3)), 'participants0_id':'a', 'participants1_id':'b', 'participants0_name':'Alpha', 'participants1_name':'Beta'}
        first = normalize_fixture(raw, {}, iso(NOW), NOW)
        raw.update(participants0_picked_percent=99, participants1_picked_percent=1, offered_points=99999, participants0_score=1000)
        self.assertEqual(first, normalize_fixture(raw, {}, iso(NOW), NOW))

    def test_source_failure_does_not_claim_empty_inventory(self):
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.collect.hotspawn', side_effect=SourceError('HTTP 403')):
            x = collect(Path(tmp))
            self.assertFalse(x['coverage_complete'])
            self.assertEqual(x['run_status'], 'degraded')
            self.assertTrue(x['flags'])

    def test_source_failure_preserves_success_timestamps(self):
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.collect.hotspawn', side_effect=SourceError('HTTP 403')):
            old = {'schema_version':1, 'matches': [], 'inventory_observed_at':'2026-01-01T00:00:00Z', 'last_attempted_at':'2026-01-01T00:00:00Z', 'flags':[]}
            Path(tmp, 'latest.json').write_text(json.dumps(old))
            x = collect(Path(tmp)); self.assertEqual(x['inventory_observed_at'], old['inventory_observed_at'])


    def test_partial_inventory_failure_cannot_overwrite_last_good_evidence(self):
        def partial_failure(client):
            evidence = client.save('hotspawn-fixtures', [{'id': 'new-but-unreconciled'}])
            client.manifest.append({'id': 'hotspawn-fixtures', 'status': 'ok', 'evidence': evidence})
            raise SourceError('Lobby and API disagree')

        with tempfile.TemporaryDirectory() as tmp, patch('scripts.collect.hotspawn', side_effect=partial_failure):
            root = Path(tmp)
            (root / 'evidence').mkdir()
            original = '[{"id": "old-evidence"}]\n'
            (root / 'evidence/hotspawn-fixtures.json').write_text(original)
            old = {'schema_version': 1, 'matches': [], 'inventory_observed_at': '2026-01-01T00:00:00Z', 'last_attempted_at': '2026-01-01T00:00:00Z', 'flags': [], 'requests': []}
            (root / 'latest.json').write_text(json.dumps(old))
            result = collect(root)
            self.assertEqual((root / 'evidence/hotspawn-fixtures.json').read_text(), original)
            self.assertTrue(result['requests'][0]['failed_inventory_attempt_only'])
            audit = root / 'evidence' / Path(result['requests'][0]['evidence']).name
            self.assertEqual(json.loads(audit.read_text())[0]['id'], 'new-but-unreconciled')
            self.assertEqual(result['analysis_as_of'], old['last_attempted_at'])

    def test_failed_replay_never_changes_the_published_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.collect.hotspawn', side_effect=SourceError('HTTP 403')), patch('scripts.validate.check_data', side_effect=ValueError('Invalid evidence')):
            root = Path(tmp)
            original = json.dumps({'schema_version': 1, 'matches': [], 'inventory_observed_at': None, 'last_attempted_at': '2026-01-01T00:00:00Z', 'flags': []})
            (root / 'latest.json').write_text(original)
            with self.assertRaisesRegex(ValueError, 'Invalid evidence'):
                collect(root)
            self.assertEqual((root / 'latest.json').read_text(), original)


if __name__ == '__main__':
    unittest.main()

class ExpandedCoverageTests(unittest.TestCase):
    def sportsbook(self):
        return {'id': 'synthetic-event', 'gameId': 6, 'isLive': False, 'startTime': START,
                'teams': {'home': {'name': 'Alpha'}, 'away': {'name': 'Beta'}},
                'market': {'name': 'Match Winner', 'status': 1, 'draw': None,
                           'home': {'name': 'Beta', 'status': 1, 'odds': 3.0},
                           'away': {'name': 'Alpha', 'status': 1, 'odds': 1.5}}}

    def test_bookmaker_aligns_actual_outcome_names_not_container_keys(self):
        q = sportsbook_quote(self.sportsbook(), MATCH, iso(NOW), NOW)
        self.assertEqual(q['odds'], [1.5, 3.0])
        self.assertEqual(q['probabilities'], [0.66666667, 0.33333333])

    def test_past_bookmaker_start_rejected_even_when_live_false(self):
        event = self.sportsbook(); event['startTime'] = iso(NOW - timedelta(minutes=1))
        match = {**MATCH, 'starts_at': event['startTime']}
        self.assertIsNone(sportsbook_quote(event, match, iso(NOW), NOW))

    def test_bookmaker_duplicate_outcomes_rejected(self):
        event = self.sportsbook(); event['market']['home']['name'] = 'Alpha'
        self.assertIsNone(sportsbook_quote(event, MATCH, iso(NOW), NOW))

    def test_gamma_discovery_ignores_maps_and_outrights(self):
        from scripts.sources import gamma_games
        event = copy.deepcopy(EVENT); event['tags'] = [{'slug': 'cs2'}]
        event['markets'].append({**MARKET, 'question': 'Alpha vs Beta - Map 1 Winner'})
        event['markets'].append({**MARKET, 'sportsMarketType': 'outright'})
        found = gamma_games([event], 'data/evidence/synthetic.json')
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['homeName'], 'Alpha')
        self.assertNotIn('probabilities', found[0])

    def test_gamma_unrelated_tag_and_missing_time_rejected(self):
        from scripts.sources import gamma_games
        event = copy.deepcopy(EVENT); event['tags'] = [{'slug': 'dota2'}]
        self.assertEqual(gamma_games([event], 'synthetic'), [])
        event['tags'] = [{'slug': 'cs2'}]; del event['markets'][0]['gameStartTime']
        self.assertEqual(gamma_games([event], 'synthetic'), [])
