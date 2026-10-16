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

from scripts.research_verify import (Probe, moneyline_markets, parse_hltv_match_page,
                                     parse_hltv_odds, parse_hltv_results, parse_hltv_schedule)

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
