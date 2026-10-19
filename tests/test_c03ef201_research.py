"""Tests for session arena-c03ef201's deep research probe parsers.

Every parser is fail-closed: a missing value stays None and is never invented.
The fixtures below are hand-written minimal markup with the exact selector
contract the probe relies on, so a change to the parsers must be deliberate.
"""
from __future__ import annotations

import unittest

from scripts.c03ef201_research import (blank_fixtures, parse_pinnacle_matchups,
                                       parse_pinnacle_straight, parse_ranking_page,
                                       parse_team_page, parse_match_team_links,
                                       scan_listing)

RANKING_HTML = """
<html><body>
<div class="ranked-team standard-box">
  <div class="ranked-team-header"><span class="name">Lynn Vision</span>
    <span class="points">412 points</span></div>
  <a href="/team/7532/lynn-vision"><img/></a>
</div>
<div class="ranked-team standard-box">
  <div class="ranked-team-header"><span class="name">Fire Flux</span>
    <span class="points">188 points</span></div>
  <a href="/team/11584/fire-flux"><img/></a>
</div>
<div class="ranked-team standard-box">
  <div class="ranked-team-header"><span class="name">Broken</span>
    <span class="points"></span></div>
</div>
</body></html>
"""

TEAM_HTML = """
<html><body>
<div class="profile-team-name">Lynn Vision</div>
<div class="profile-team-stat"><span>World ranking</span>
  <span class="stats-row"><a href="/ranking/teams">#34</a></span></div>
</body></html>
"""

MATCH_HTML = """
<html><body>
<div class="box-headline"><a href="/team/7532/lynn-vision">Lynn Vision</a></div>
<div class="box-headline"><a href="/team/9999/morningstar">Morningstar</a></div>
</body></html>
"""


class RankingParseTest(unittest.TestCase):
    def test_points_and_names_parse_only_complete_rows(self):
        rows = parse_ranking_page(RANKING_HTML)
        self.assertEqual([r['team'] for r in rows], ['Lynn Vision', 'Fire Flux'])
        self.assertEqual(rows[0]['points'], 412.0)
        self.assertEqual(rows[0]['team_url'], 'https://www.hltv.org/team/7532/lynn-vision')
        # A row without points is skipped, never filled in.
        self.assertEqual(len(rows), 2)

    def test_team_page_world_ranking(self):
        facts = parse_team_page(TEAM_HTML)
        self.assertEqual(facts['team'], 'Lynn Vision')
        self.assertEqual(facts['world_ranking'], 34)

    def test_team_page_missing_ranking_stays_none(self):
        facts = parse_team_page('<html><body><h1>Some Team</h1></body></html>')
        self.assertIsNone(facts['world_ranking'])

    def test_match_page_team_links_are_deduplicated(self):
        links = parse_match_team_links(MATCH_HTML + '<a href="/team/7532/lynn-vision">dup</a>')
        self.assertEqual(links, ['https://www.hltv.org/team/7532/lynn-vision',
                                 'https://www.hltv.org/team/9999/morningstar'])


class PinnacleParseTest(unittest.TestCase):
    def test_matchups_keep_name_only_participants(self):
        rows = parse_pinnacle_matchups([
            {'id': 5, 'leagueId': 285925, 'startTime': '2026-10-19T17:00:00Z', 'isLive': False,
             'participants': [{'name': 'Fire Flux'}, {'name': 'ex-6666'}]},
            'not-a-dict'])
        self.assertEqual(rows[0]['participants'], ['Fire Flux', 'ex-6666'])
        self.assertEqual(rows[0]['id'], 5)

    def test_straight_series_moneyline_uses_period_zero_only(self):
        payload = [
            {'matchupId': 5, 'type': 'moneyline', 'period': 0, 'key': 's;0;m',
             'prices': [{'participantId': 1, 'price': -143}, {'participantId': 2, 'price': 110}]},
            {'matchupId': 5, 'type': 'moneyline', 'period': 1, 'key': 's;1;m',
             'prices': [{'participantId': 1, 'price': -300}, {'participantId': 2, 'price': 250}]},
        ]
        rows = parse_pinnacle_straight(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['period'], 0)
        self.assertEqual(rows[0]['odds'], [1.6993, 2.1])

    def test_specials_and_non_two_way_rows_are_rejected(self):
        payload = [
            # Yes/No special
            {'matchupId': 6, 'type': 'moneyline', 'period': 0,
             'prices': [{'participant': 'Yes', 'price': -190}, {'participant': 'No', 'price': 160}]},
            # "Team By N" specials grid
            {'matchupId': 7, 'type': 'moneyline', 'period': 0,
             'prices': [{'participant': 'FURIA By 2', 'price': 400}, {'participant': 'BB Team By 2', 'price': 500}]},
            # valid shape but American price 0 carries no probability
            {'matchupId': 8, 'type': 'moneyline', 'period': 0,
             'prices': [{'participant': 'Alpha', 'price': 0}, {'participant': 'Beta', 'price': 0}]},
        ]
        self.assertEqual(parse_pinnacle_straight(payload), [])

    def test_missing_market_values_stay_blank(self):
        self.assertEqual(parse_pinnacle_straight(None), [])
        self.assertEqual(parse_pinnacle_straight([{'periods': None}]), [])
        self.assertEqual(parse_pinnacle_matchups(None), [])


class ListingScanTest(unittest.TestCase):
    def test_snippet_evidence_and_misses(self):
        hits = scan_listing('... upcoming: Fire Flux vs ex-6666 odds 1.7 ...', ['Fire Flux', 'Morningstar'])
        self.assertTrue(hits['Fire Flux']['found'])
        self.assertIn('Fire Flux', hits['Fire Flux']['snippet'])
        self.assertIsNone(hits['Morningstar'])

    def test_accented_name_matches_numeric_core(self):
        hits = scan_listing('QUINTESSÊNCIA vs RED Canids', ['QUINTESSÊNCIA'])
        self.assertTrue(hits['QUINTESSÊNCIA']['found'])


class BlankListTest(unittest.TestCase):
    def test_blank_list_copies_collector_rows_without_invention(self):
        latest = {'matches': [{'id': '9', 'teams': [{'name': 'A'}, {'name': 'B'}],
                               'competition': 'Cup', 'starts_at': '2026-10-19T17:00:00Z',
                               'source_url': 'https://www.hotspawn.com/matches/a-vs-b-9'}]}
        origination = {'matches': [
            {'id': '9', 'origination': None,
             'research': [{'stage': 'HLTV research', 'status': 'checked',
                           'source_url': 'https://www.hltv.org/matches/1/x-vs-y-cup',
                           'detail': 'confirmed'}]},
            {'id': '10', 'origination': {'method': 'model'}, 'research': []}]}
        fixtures = blank_fixtures(latest, origination)
        self.assertEqual(len(fixtures), 1)
        self.assertEqual(fixtures[0]['hotspawn_id'], '9')
        self.assertEqual(fixtures[0]['hltv_url'], 'https://www.hltv.org/matches/1/x-vs-y-cup')
        self.assertEqual(fixtures[0]['research_trail'][0]['stage'], 'HLTV research')


if __name__ == '__main__':
    unittest.main()
