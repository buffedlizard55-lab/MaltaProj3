"""Offline regression tests for the verification probe's parsers.

These never touch the network. They pin the extraction contract so a source markup
change is reported as a limitation instead of silently producing a wrong value.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.research_verify import (Probe, bovada_moneylines, moneyline_markets,
                                     parse_hltv_match_page, parse_hltv_odds, parse_hltv_results,
                                     parse_hltv_schedule, polymarket_directory_games,
                                     thunderpick_moneylines, valve_rating_rows)

EVENT = {
    'id': '1194512',
    'slug': 'cs2-aur1-9z-2026-10-16',
    'title': 'Counter-Strike: Aurora Gaming vs 9z (BO3) - Thunderpick World Championship Group A',
    'tags': [{'slug': 'cs2'}, {'slug': 'esports'}],
    'updatedAt': '2026-10-16T07:19:24.623084Z',
    'markets': [
        {'id': '5733286', 'question': 'Counter-Strike: Aurora Gaming vs 9z - Map 1 Winner',
         'sportsMarketType': 'child_moneyline', 'outcomes': '["Aurora Gaming", "9z"]',
         'gameStartTime': '2026-10-16 14:00:00+00', 'bestBid': 0.64, 'bestAsk': 0.65},
        {'id': '5733290', 'question': 'Counter-Strike: Aurora Gaming vs 9z (BO3) - Winner',
         'sportsMarketType': 'moneyline', 'outcomes': '["Aurora Gaming", "9z"]',
         'outcomePrices': '["0.69", "0.31"]', 'gameStartTime': '2026-10-16 14:00:00+00',
         'eventStartTime': '2026-10-16T14:00:00Z', 'bestBid': 0.69, 'bestAsk': 0.70,
         'spread': 0.01, 'acceptingOrders': True, 'active': True, 'closed': False,
         'volumeNum': 27449.33, 'liquidityNum': 268023.53,
         'conditionId': '0xabc', 'clobTokenIds': '["111", "222"]',
         'updatedAt': '2026-10-16T07:19:08.672139Z'},
        {'id': '5733291', 'question': 'Counter-Strike: Aurora Gaming vs 9z - Total Maps Over 2.5',
         'sportsMarketType': 'moneyline', 'outcomes': '["Over", "Under"]'},
    ],
}


class MoneylineContract(unittest.TestCase):
    def test_only_the_series_moneyline_is_kept(self):
        rows = moneyline_markets(EVENT)
        self.assertEqual(len(rows), 1, 'map-winner and total-maps markets must never become a series line')
        row = rows[0]
        self.assertEqual(row['event_id'], '1194512')
        self.assertEqual(row['market_id'], '5733290')
        self.assertEqual(row['outcomes'], ['Aurora Gaming', '9z'])
        self.assertEqual(row['game_start_time'], '2026-10-16 14:00:00+00')
        self.assertEqual(row['best_bid'], 0.69)
        self.assertEqual(row['best_ask'], 0.70)
        self.assertEqual(row['spread'], 0.01)
        self.assertEqual(row['clob_token_ids'], ['111', '222'])
        self.assertEqual(row['outcome_prices'], ['0.69', '0.31'])
        self.assertEqual(row['source_url'], 'https://polymarket.com/event/cs2-aur1-9z-2026-10-16')

    def test_non_cs2_events_are_ignored(self):
        other = dict(EVENT, slug='nba-lal-bos-2026-10-16', tags=[{'slug': 'nba'}])
        self.assertEqual(moneyline_markets(other), [])
        self.assertEqual(moneyline_markets({}), [])
        self.assertEqual(moneyline_markets(None), [])

    def test_both_gamma_cs2_tag_spellings_are_accepted(self):
        # Gamma tags the listing `cs2` but a single-event read of the same event
        # `counter-strike-2`; requiring only the first silently dropped all 67
        # per-match events on the second probe run (archived: gamma-event-1133922.json).
        for tag in ('cs2', 'counter-strike-2'):
            with self.subTest(tag=tag):
                event = dict(EVENT, tags=[{'slug': 'esports'}, {'slug': tag}])
                self.assertEqual(len(moneyline_markets(event)), 1)

    def test_a_cs2_prefixed_slug_without_a_cs2_tag_is_still_rejected(self):
        self.assertEqual(moneyline_markets(dict(EVENT, tags=[{'slug': 'esports'}])), [])


SCHEDULE_HTML = '''<html><body>
<h2>Friday - 2026-10-16</h2>
<a class="a-reset" href="/matches/2399412/aurora-vs-9z-thunderpick-world-championship-2026">
  <div class="time">10:00</div><div class="standard">bo3</div>
  <div class="t1">Aurora</div><div class="t2">9z</div></a>
<a class="a-reset" href="/matches/2399413/betboom-vs-legacy-thunderpick-world-championship-2026">
  <div class="time">13:00</div><div class="standard">bo3</div>
  <div class="t1">BETBOOM</div><div class="t2">Legacy</div></a>
<h2>Saturday - 2026-10-17</h2>
<a class="a-reset" href="/matches/2399414/furia-vs-aurora-9z-winner-thunderpick-world-championship-2026">
  <div class="time">10:00</div><div class="standard">bo3</div>
  <div class="t1">FURIA</div><div class="t2">Aurora/9z winner</div></a>
</body></html>'''

RESULTS_HTML = '''<html><body>
<div class="standard-headline">October 15th 2026</div>
<a href="/matches/2399408/aurora-vs-ninjas-in-pyjamas-thunderpick-world-championship-2026">
  Aurora 2 - 0 Ninjas in Pyjamas bo3</a>
<div class="standard-headline">October 14th 2026</div>
<a href="/matches/2399384/9z-vs-aurora-thunderpick-world-championship-2026">9z 2 - 0 Aurora bo3</a>
</body></html>'''

MATCH_HTML = '''<html><head><title>Aurora vs. 9z at Thunderpick World Championship 2026 | HLTV.org</title>
<link rel="canonical" href="https://www.hltv.org/matches/2399412/aurora-vs-9z-thunderpick-world-championship-2026">
</head><body><div class="countdown" data-unix="1792159200000" data-time-format="HH:mm">10:00</div>
<p>Maps Best of 3 (LAN) * Group A decider match</p>
<p>10:00 16th of October 2026</p>
<div class=" lineup"><a href="/player/11282/wicadia">Wicadia</a><a href="/player/7398/xantares">XANTARES</a>
<a href="/player/9893/woxic">woxic</a><a href="/player/16888/jimpphat">Jimpphat</a>
<a href="/player/12069/kyxsan">kyxsan</a></div>
<div class=" lineup"><a href="/player/15086/luchov">luchov</a><a href="/player/16413/huasopeek">HUASOPEEK</a>
<a href="/player/11978/meyern">meyern</a><a href="/player/12512/dgt">dgt</a><a href="/player/9214/max">max</a></div>
</body></html>'''

ODDS_HTML = '''<html><body>
<p>Aurora is better ranked (#6)</p><p>9z is worse ranked (#17)</p>
<p>This speaks in favor of Aurora</p><p>Aurora has won 3 out of the last 5 matches</p>
<p>Aurora is the bookmaker favorite with the best odds</p>
<table><tr><td>bet365</td><td>1.36</td><td>3.10</td></tr></table>
<p>2 - 0 wins | 45.8%</p><p>1 - 2 losses | 16.7%</p>
</body></html>'''


class HltvParsers(unittest.TestCase):
    def test_schedule_groups_by_displayed_day(self):
        parsed = parse_hltv_schedule(SCHEDULE_HTML)
        days = parsed['days']
        self.assertEqual([d['date'] for d in days], ['2026-10-16', '2026-10-17'])
        self.assertEqual([f['match_id'] for f in days[0]['fixtures']], [2399412, 2399413])
        self.assertEqual(days[0]['fixtures'][0]['displayed_time'], '10:00')
        self.assertEqual(days[0]['fixtures'][0]['best_of'], 3)
        self.assertTrue(days[0]['fixtures'][0]['url'].startswith('https://www.hltv.org/matches/'))

    def test_results_keep_score_and_day(self):
        parsed = parse_hltv_results(RESULTS_HTML)
        self.assertEqual(len(parsed['days']), 2)
        self.assertEqual(parsed['days'][0]['displayed_day'], 'October 15th 2026')
        self.assertEqual(parsed['days'][0]['results'][0]['match_id'], 2399408)
        self.assertEqual(parsed['days'][0]['results'][0]['score'], [2, 0])
        self.assertEqual(parsed['days'][1]['results'][0]['match_id'], 2399384)

    def test_match_page_exposes_absolute_start_and_canonical_url(self):
        info = parse_hltv_match_page(MATCH_HTML)
        self.assertEqual(info['data_unix'], 1792159200000)
        self.assertEqual(info['start_utc_from_countdown'], '2026-10-16T14:00:00+00:00')
        self.assertEqual(info['displayed_time'], '10:00')
        self.assertEqual(info['displayed_date'], '16th of October 2026')
        self.assertEqual(info['best_of'], 3)
        self.assertEqual(info['setting'], 'LAN')
        self.assertEqual(info['slot'], 'Group A decider match')
        self.assertEqual(info['canonical_url'],
                         'https://www.hltv.org/matches/2399412/aurora-vs-9z-thunderpick-world-championship-2026')
        self.assertEqual(info['lineup_blocks'][0], ['Wicadia', 'XANTARES', 'woxic', 'Jimpphat', 'kyxsan'])
        self.assertEqual(info['lineup_blocks'][1], ['luchov', 'HUASOPEEK', 'meyern', 'dgt', 'max'])

    def test_match_page_without_data_unix_stays_blank(self):
        info = parse_hltv_match_page('<html><body><p>no countdown here</p></body></html>')
        self.assertNotIn('start_utc_from_countdown', info)

    def test_odds_page_captures_rankings_insights_and_decimal_odds(self):
        odds = parse_hltv_odds(ODDS_HTML)
        self.assertEqual(odds['rankings'].get('Aurora'), {'rank': 6, 'side': 'better'})
        self.assertEqual(odds['rankings'].get('9z'), {'rank': 17, 'side': 'worse'})
        self.assertIn(['bet365', '1.36', '3.10'], odds['odds_rows'])
        self.assertIn(['2 - 0 wins', '45.8%'], odds['odds_rows'])
        self.assertTrue(any('bookmaker favorite' in i for i in odds['insights']))


class ProbeArchiving(unittest.TestCase):
    def test_failed_fetch_is_recorded_and_never_raises(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            probe = Probe(Path(tmp))
            data, evidence = probe.get('unreachable', 'https://invalid.example.test/x')
            self.assertIsNone(data)
            self.assertEqual(len(probe.log), 1)
            self.assertIn(probe.log[0]['status'], {'error', 'http-404'})
            self.assertEqual(probe.log[0]['url'], 'https://invalid.example.test/x')
            self.assertTrue(probe.log[0]['observed_at'].endswith('Z'))

    def test_log_entries_are_json_serialisable(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            probe = Probe(Path(tmp))
            probe.get('unreachable', 'https://invalid.example.test/y')
            json.dumps(probe.log)


if __name__ == '__main__':
    unittest.main()


# ---------------------------------------------------------------------------
# Replay tests against the archived first-party responses. These prove the
# extractors reproduce what the official source actually said, and they pin the
# two defects found on the first probe run (Valve column order, Bovada nesting).
# ---------------------------------------------------------------------------

RAW = Path(__file__).resolve().parents[1] / 'data/research/ba7164a0/raw'
VALVE_SNAPSHOT = 'standings_global_2026_10_05.md'
VALVE_URL = ('https://raw.githubusercontent.com/ValveSoftware/counter-strike_regional_standings/'
             'main/live/2026/' + VALVE_SNAPSHOT)


@unittest.skipUnless((RAW / 'valve-standings-latest.html').exists(), 'archived Valve snapshot not committed')
class ValveReplay(unittest.TestCase):
    def setUp(self):
        self.text = (RAW / 'valve-standings-latest.html').read_text()
        self.teams = ['Aurora', '9z', 'BETBOOM', 'Legacy', 'FURIA', 'Falcons',
                      'Ninjas in Pyjamas', 'PARIVISION']
        self.rows = valve_rating_rows(self.text, self.teams, VALVE_SNAPSHOT, VALVE_URL)

    def test_points_come_from_the_points_column_not_the_standing(self):
        self.assertEqual(self.rows['standings_as_of'], '2026_10_05')
        aurora = self.rows['ratings']['Aurora']
        self.assertEqual(aurora['standing'], 9)
        self.assertEqual(aurora['points'], 1716)
        self.assertNotEqual(aurora['points'], aurora['standing'],
                            'regression: the first probe run returned the standing as the points')

    def test_every_twc_team_has_an_exact_name_row_with_five_players(self):
        for team in self.teams:
            with self.subTest(team=team):
                self.assertIn(team, self.rows['ratings'])
                self.assertEqual(len(self.rows['ratings'][team]['roster']), 5)

    def test_aurora_official_roster_shows_the_completed_july_rebuild(self):
        self.assertEqual(sorted(self.rows['ratings']['Aurora']['roster']),
                         sorted(['Jimpphat', 'kyxsan', 'Wicadia', 'woxic', 'XANTARES']))

    def test_unknown_team_stays_absent_rather_than_fuzzy_matched(self):
        rows = valve_rating_rows(self.text, ['LOS NINOS', 'Insiders', 'ex-6666', 'antidaun'],
                                 VALVE_SNAPSHOT, VALVE_URL)
        self.assertEqual(rows['ratings'], {})
        self.assertEqual(rows['ambiguous'], {})
        self.assertEqual(sorted(rows['absent']), sorted(['LOS NINOS', 'Insiders', 'ex-6666', 'antidaun']))
        self.assertEqual(len(rows['limitations']), 4)

    def test_duplicate_valve_names_are_published_as_ambiguous_and_never_chosen(self):
        # Verified in Valve's own snapshot: these four names each appear twice with
        # different rosters. Picking one would be an inference, not a sourced fact.
        rows = valve_rating_rows(self.text, ['aimclub', 'Bebop', 'Leo', 'Just Players', 'Legacy'],
                                 VALVE_SNAPSHOT, VALVE_URL)
        self.assertEqual(sorted(rows['ambiguous']), ['Bebop', 'Just Players', 'Leo', 'aimclub'])
        for team, candidates in rows['ambiguous'].items():
            with self.subTest(team=team):
                self.assertEqual(len(candidates), 2)
                self.assertNotEqual(candidates[0]['roster'], candidates[1]['roster'])
        self.assertEqual(list(rows['ratings']), ['Legacy'], 'the unambiguous team is still rated')
        self.assertTrue(any('appears 2 times' in note for note in rows['limitations']))


def bovada_event(description, start_ms, outcomes, *, key='2W-12', status='O', main=True,
                 live_period=False, event_live=False, event_type='GAMEEVENT', link='/x'):
    """Build a Bovada coupon response (a list of league groups) with one event in it."""
    return [{
        'path': [{'description': 'Counter-Strike 2'}, {'description': 'Esports'}],
        'events': [{
            'id': '32299372', 'description': description, 'type': event_type, 'live': event_live,
            'startTime': start_ms, 'link': link,
            'competitors': [{'name': o[0]} for o in outcomes],
            'displayGroups': [{'markets': [{
                'id': '536148496', 'key': key, 'description': 'Moneyline', 'status': status,
                'period': {'main': main, 'live': live_period},
                'outcomes': [{'description': name, 'status': status,
                              'price': {'decimal': decimal, 'american': american}}
                             for name, decimal, american in outcomes],
            }]}],
        }],
    }]


class BovadaContract(unittest.TestCase):
    """Deterministic: the accepted/rejected market rules, pinned to fixed payloads."""

    TWC_AURORA = 1792159200000  # 2026-10-16T14:00:00Z, as archived on the first probe run

    def test_the_main_open_prematch_moneyline_is_read_with_both_prices(self):
        rows = bovada_moneylines(bovada_event(
            'Team AURORA vs 9Z Globant', self.TWC_AURORA,
            [('Team AURORA', '1.434783', '-230'), ('9Z Globant', '2.750', '+175')]))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['start_utc'], '2026-10-16T14:00:00+00:00')
        self.assertEqual(row['moneyline_markets'], 1)
        self.assertTrue(row['prematch_main_moneyline'])
        self.assertEqual([o['name'] for o in row['outcomes']], ['Team AURORA', '9Z Globant'])
        self.assertEqual([o['decimal'] for o in row['outcomes']], ['1.434783', '2.750'])
        self.assertEqual(row['source_url'], 'https://www.bovada.lv/x')

    def test_a_map_handicap_key_is_never_read_as_a_series_moneyline(self):
        rows = bovada_moneylines(bovada_event(
            'A vs B', self.TWC_AURORA, [('A', '1.50', '-200'), ('B', '2.50', '+150')], key='2W-45'))
        self.assertEqual(rows[0]['moneyline_markets'], 0)
        self.assertEqual(rows[0]['outcomes'], [])

    def test_a_live_period_or_closed_market_is_never_flagged_prematch(self):
        for kwargs in ({'live_period': True}, {'status': 'C'}, {'main': False},
                       {'event_live': True}, {'event_type': 'OTHER'}):
            with self.subTest(**kwargs):
                rows = bovada_moneylines(bovada_event(
                    'A vs B', self.TWC_AURORA, [('A', '1.50', '-200'), ('B', '2.50', '+150')], **kwargs))
                self.assertFalse(rows[0]['prematch_main_moneyline'],
                                 'a non-prematch or non-main market must not be usable as a series line')

    def test_an_in_play_event_is_recorded_verbatim_and_flagged_unusable(self):
        # The probe records what the feed said; it never silently drops a row. The
        # event-level facts stay visible so a reviewer can see why it was rejected.
        rows = bovada_moneylines(bovada_event(
            'A vs B', self.TWC_AURORA, [('A', '1.50', '-200'), ('B', '2.50', '+150')], event_live=True))
        self.assertIs(rows[0]['live'], True)
        self.assertEqual(rows[0]['event_type'], 'GAMEEVENT')
        self.assertEqual(rows[0]['moneyline_markets'], 1)
        self.assertEqual(len(rows[0]['outcomes']), 2)
        self.assertFalse(rows[0]['prematch_main_moneyline'])


@unittest.skipUnless((RAW / 'bovada-cs2.json').exists(), 'archived Bovada coupon not committed')
class BovadaReplay(unittest.TestCase):
    """Structural invariants over the archived coupon.

    Prices and which fixtures are still prematch both move between refreshes, so no
    specific odds value is asserted here; those are recorded with their observation
    timestamp in the audit dossier instead.
    """

    def setUp(self):
        self.rows = bovada_moneylines(json.loads((RAW / 'bovada-cs2.json').read_text()))

    def test_every_archived_event_is_a_prematch_game_event(self):
        self.assertTrue(self.rows, 'no Bovada event extracted')
        for row in self.rows:
            self.assertEqual(row['event_type'], 'GAMEEVENT')
            self.assertIs(row['live'], False)
            self.assertTrue(row['start_utc'].endswith('+00:00'))

    def test_every_priced_row_has_exactly_two_open_decimal_outcomes(self):
        priced = [r for r in self.rows if r['prematch_main_moneyline']]
        self.assertTrue(priced, 'the archived coupon has no usable prematch moneyline')
        for row in priced:
            with self.subTest(event=row['description']):
                self.assertEqual(len(row['outcomes']), 2)
                for outcome in row['outcomes']:
                    self.assertEqual(outcome['status'], 'O')
                    self.assertGreater(float(outcome['decimal']), 1.0)

    def test_a_row_without_an_open_main_moneyline_is_never_flagged_usable(self):
        for row in self.rows:
            if row['prematch_main_moneyline']:
                continue
            # Either no qualifying market, or a price that fails an open/decimal check.
            self.assertTrue(row['moneyline_markets'] != 1 or len(row['outcomes']) != 2
                            or any(o['status'] != 'O' or float(o['decimal']) <= 1.0
                                   for o in row['outcomes']),
                            f'{row["description"]}: flagged unusable without a recorded reason')

    def test_every_row_carries_its_own_bovada_source_url(self):
        for row in self.rows:
            self.assertTrue(row['source_url'].startswith('https://www.bovada.lv/'))


class ThunderpickContract(unittest.TestCase):
    def test_only_a_two_selection_open_match_winner_market_is_read(self):
        payload = {'data': {'upcoming': [
            {'preferredMarkets': [
                {'name': 'Match Winner', 'status': 1, 'eventId': 1, 'id': 2,
                 'selections': [{'name': 'A', 'odds': 1.9, 'type': 'home', 'status': 1},
                                {'name': 'B', 'odds': 1.95, 'type': 'away', 'status': 1}]},
                {'name': 'Map Handicap', 'status': 1, 'eventId': 1, 'id': 3,
                 'selections': [{'name': 'A', 'odds': 1.9, 'status': 1},
                                {'name': 'B', 'odds': 1.9, 'status': 1}]},
                {'name': 'Match Winner', 'status': 0, 'eventId': 1, 'id': 4,
                 'selections': [{'name': 'A', 'odds': 1.9, 'status': 1},
                                {'name': 'B', 'odds': 1.9, 'status': 1}]},
            ]},
            {'preferredMarkets': [
                {'name': 'Match Winner', 'status': 1, 'eventId': 5, 'id': 6,
                 'selections': [{'name': 'A', 'odds': 1.9, 'status': 1}]},
            ]},
        ]}}
        rows = thunderpick_moneylines(payload)
        self.assertEqual(len(rows), 1, 'handicap, closed and single-selection markets must be rejected')
        self.assertEqual(rows[0]['market'], 'Match Winner')
        self.assertEqual([s['odds'] for s in rows[0]['selections']], [1.9, 1.95])

    def test_an_unrecognised_payload_yields_no_rows_rather_than_a_guess(self):
        self.assertEqual(thunderpick_moneylines({}), [])
        self.assertEqual(thunderpick_moneylines({'data': {}}), [])
        self.assertEqual(thunderpick_moneylines('not a dict'), [])


@unittest.skipUnless((RAW / 'thunderpick-cs2.json').exists(), 'archived Thunderpick coupon not committed')
class ThunderpickReplay(unittest.TestCase):
    def test_match_winner_odds_are_two_selections_with_decimal_prices(self):
        rows = thunderpick_moneylines(json.loads((RAW / 'thunderpick-cs2.json').read_text()))
        self.assertTrue(rows, 'no Thunderpick match-winner line extracted')
        for row in rows:
            self.assertEqual(row['market'], 'Match Winner')
            self.assertEqual(len(row['selections']), 2)
            for selection in row['selections']:
                self.assertIsInstance(selection['odds'], (int, float))
                self.assertGreater(selection['odds'], 1.0)


class FlightDecoder(unittest.TestCase):
    def test_directory_games_are_read_from_flight_json_not_displayed_percentages(self):
        payload = json.dumps({'sportSlug': 'cs2', 'id': 1194512, 'slug': 'cs2-aur1-9z-2026-10-16',
                              'homeName': 'Aurora Gaming', 'awayName': '9z',
                              'homeTokenId': 'a', 'awayTokenId': 'b',
                              'startTime': '2026-10-16T14:00:00Z'})
        html = 'noise<script>self.__next_f.push([1,' + json.dumps('2:' + payload + '\n') + '])</script>'
        games = polymarket_directory_games(html)
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]['id'], 1194512)
        self.assertEqual(games[0]['homeName'], 'Aurora Gaming')

    def test_non_cs2_games_and_percentage_only_objects_are_ignored(self):
        html = 'x<script>self.__next_f.push([1,' + json.dumps('2:{"sportSlug":"nba","id":1}\n') + '])</script>'
        self.assertEqual(polymarket_directory_games(html), [])
        self.assertEqual(polymarket_directory_games('no flight data at all'), [])


class ProbeResilience(unittest.TestCase):
    """A collector bug or a blocked source must never lose the rest of the dossier.

    Fully offline and deterministic: every collector is stubbed, so this unit test never
    depends on network egress, source availability or live prices.
    """

    def test_a_crashing_collector_is_published_and_the_others_survive(self):
        import scripts.research_verify as rv

        def boom(probe, *extra):
            raise RuntimeError('simulated collector defect')

        def stub(probe, *extra):
            return {'stubbed': True, 'limitations': []}

        names = ['collect_hotspawn', 'collect_production', 'collect_polymarket',
                 'collect_hltv', 'collect_valve', 'collect_other_books']
        originals = {name: getattr(rv, name) for name in names}
        for name in names:
            setattr(rv, name, stub)
        rv.collect_polymarket = boom
        try:
            with tempfile.TemporaryDirectory() as tmp:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = rv.main(['--out', tmp])
                data = json.loads((Path(tmp) / 'observations.json').read_text())
        finally:
            for name, func in originals.items():
                setattr(rv, name, func)
        self.assertEqual(code, 0)
        self.assertEqual(len(data['collector_crashes']), 1)
        crash = data['collector_crashes'][0]
        self.assertEqual(crash['collector'], 'polymarket')
        self.assertIn('simulated collector defect', crash['error'])
        self.assertIn('Traceback', crash['traceback'])
        self.assertIn('Collector polymarket raised RuntimeError', data['polymarket']['limitations'][0])
        # Every other collector still produced its own record.
        for key in ('hotspawn', 'production_site', 'hltv', 'valve', 'other_books'):
            self.assertIn(key, data)
            self.assertIsInstance(data[key], dict)
            self.assertTrue(data[key].get('stubbed'))
        self.assertEqual(data['session'], 'arena-ba7164a0')
        self.assertTrue(data['probe_started_at'].endswith('Z'))
        self.assertTrue(data['probe_finished_at'] >= data['probe_started_at'])
