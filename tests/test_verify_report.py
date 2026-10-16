"""V-3: the verification report must publish, and must publish honestly.

Two obligations are tested here:

* the rendered page satisfies the site's own two gatekeepers -
  ``scripts/validate.py::check_links`` (main landmark, mobile viewport, no root-relative
  link, every local link and anchor resolves) and ``scripts/audit_rows.py`` (every table
  row and pick card carries an official source link, or visibly says it is unverified);
* the page never states a probability that the dossier does not contain. A fixture with
  no verified input must render as blank-and-flagged, not as a number.
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.audit_rows import audit_html
from scripts.build_verify_report import (CSS, REPORT_NAME, build, render, section_picks,
                                         section_unresolved, twc_context)
from scripts.validate import check_links

try:  # works both under `unittest discover -s tests` and `python -m unittest tests.x`
    from tests.test_verify_published import (build_evidence, clob_book, fixture_row,
                                             polymarket_line)
except ImportError:  # pragma: no cover
    from test_verify_published import (build_evidence, clob_book, fixture_row,
                                       polymarket_line)

from scripts.verify_published import audit

ROOT = Path(__file__).resolve().parents[1]
PAGE = 'data/research/ba7164a0/report.html'


def synthetic_audit(tmp: Path) -> tuple[dict, dict]:
    rows = [
        fixture_row('1080205', ['Aurora', '9z'], probabilities=[0.69346, 0.30654],
                    method='consensus', pick=0,
                    quotes=[{'provider': 'Polymarket', 'event_id': '1194512'}],
                    aliases=[{'alias': 'Aurora Gaming', 'canonical': 'Aurora'}],
                    source_url='https://www.hotspawn.com/matches/aurora-vs-9z-1080205'),
        fixture_row('1081775', ['BetBoom', 'Legacy'], probabilities=[0.3627, 0.6373],
                    method='consensus', pick=1, start='2026-10-16T17:00:00Z',
                    quotes=[{'provider': 'Polymarket', 'event_id': '1196836'}],
                    aliases=[{'alias': 'BetBoom Team', 'canonical': 'BetBoom'}]),
        fixture_row('1081527', ['aimclub', 'BASEMENT BOYS'], start='2026-10-19T09:00:00Z',
                    limitations=['No verified inputs; probabilities intentionally left blank '
                                 '(no default 50/50).'],
                    research=[{'stage': 'HLTV research', 'status': 'checked',
                               'source_url': 'https://www.hltv.org/matches/2399591/x',
                               'detail': 'Exact teams/time confirmed on HLTV.'},
                              {'stage': 'Betting market (Polymarket series winner)',
                               'status': 'unresolved',
                               'source_url': 'https://polymarket.com/event/cs2-aim1-bmb-2026-10-19',
                               'detail': 'Order book spread 0.93 exceeds the 0.12 ceiling.'}]),
    ]
    moneylines = [
        polymarket_line('1194512', 'cs2-aur1-9z-2026-10-16', ['Aurora Gaming', '9z'],
                        [0.695, 0.305]),
        polymarket_line('1196836', 'cs2-lgc-bb3-2026-10-16', ['Legacy', 'BetBoom Team'],
                        [0.635, 0.365], start='2026-10-16 17:00:00+00'),
        polymarket_line('1183120', 'cs2-aim1-bmb-2026-10-19', ['aimclub', 'BASEMENT BOYS'],
                        [0.495, 0.505], spread=0.93, start='2026-10-19 09:00:00+00'),
    ]
    books = {
        't1': clob_book([(0.69, 100)], [(0.70, 100)], 't1'),
        't2': clob_book([(0.30, 100)], [(0.31, 100)], 't2'),
    }
    valve = {
        'snapshot_used': 'standings_global_2026_10_05.md', 'standings_as_of': '2026_10_05',
        'source_url': 'https://raw.githubusercontent.com/ValveSoftware/'
                      'counter-strike_regional_standings/main/live/2026/'
                      'standings_global_2026_10_05.md',
        'limitations': [], 'absent': ['BASEMENT BOYS'],
        'ratings': {'Aurora': {'standing': 9, 'points': 1716, 'team_name': 'Aurora',
                               'roster': ['Jimpphat', 'kyxsan', 'Wicadia', 'woxic', 'XANTARES'],
                               'snapshot': 'standings_global_2026_10_05.md',
                               'source_url': 'https://raw.githubusercontent.com/ValveSoftware/'
                                             'counter-strike_regional_standings/main/live/2026/'
                                             'standings_global_2026_10_05.md'}},
        'ambiguous': {'aimclub': [
            {'standing': 77, 'points': 1113, 'team_name': 'aimclub',
             'roster': ['ERSIN', 'mhN1', 'ragga', 'waZz', 'zewts'],
             'snapshot': 'standings_global_2026_10_05.md',
             'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/'
                           'blob/main/live/2026/standings_global_2026_10_05.md'},
            {'standing': 336, 'points': 504, 'team_name': 'aimclub',
             'roster': ['Ed1m', 'ERSIN', 'RoberttMP', 'XELLOW', 'zewts'],
             'snapshot': 'standings_global_2026_10_05.md',
             'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/'
                           'blob/main/live/2026/standings_global_2026_10_05.md'}]},
    }
    hltv = {
        'observed_at': '2026-10-16T08:19:40Z',
        'schedule': {'fixtures': [
            {'match_id': 2399412, 'displayed_day': 'Friday - 2026-10-16',
             'displayed_time': '16:00', 'start_utc': '2026-10-16T14:00:00+00:00',
             'best_of': 3, 'teams': ['Aurora', '9z'], 'lan': 'true',
             'url': 'https://www.hltv.org/matches/2399412/aurora-vs-9z-x'},
            {'match_id': 2399413, 'displayed_day': 'Friday - 2026-10-16',
             'displayed_time': '19:00', 'start_utc': '2026-10-16T17:00:00+00:00',
             'best_of': 3, 'teams': ['BETBOOM', 'Legacy'], 'lan': 'true',
             'url': 'https://www.hltv.org/matches/2399413/betboom-vs-legacy-x'},
        ], 'timezone_note': 'Displayed times use the viewer timezone.'},
        'results': {'results': [
            {'match_id': 2399409, 'listed_teams': ['9z', 'Falcons'], 'listed_score': [1, 2],
             'winner': 'Falcons', 'loser': '9z', 'winner_score': 2, 'loser_score': 1,
             'best_of': 3, 'finished_unix': 1792074509000,
             'finished_utc': '2026-10-15T14:28:29+00:00', 'displayed_day': 'October 15th 2026',
             'url': 'https://www.hltv.org/matches/2399409/9z-vs-falcons-x'},
            {'match_id': 2399408, 'listed_teams': ['Aurora', 'Ninjas in Pyjamas'],
             'listed_score': [2, 0], 'winner': 'Aurora', 'loser': 'Ninjas in Pyjamas',
             'winner_score': 2, 'loser_score': 0, 'best_of': 3, 'finished_unix': 1792061242000,
             'finished_utc': '2026-10-15T10:47:22+00:00', 'displayed_day': 'October 15th 2026',
             'url': 'https://www.hltv.org/matches/2399408/aurora-vs-nip-x'},
        ]},
        'match_pages': {'2399412': {'slot': 'Group A decider match', 'setting': 'LAN',
                                    'best_of': 3,
                                    'canonical_url': 'https://www.hltv.org/matches/2399412/x'},
                        '2399413': {'slot': 'Group B decider match', 'setting': 'LAN',
                                    'best_of': 3,
                                    'canonical_url': 'https://www.hltv.org/matches/2399413/x'}},
        'teams': {'Aurora': {'url': 'https://www.hltv.org/team/11861/aurora',
                             'valve_ranking': {'rank': 5, 'rank_text': '#5', 'regional': '( EU #5)'},
                             'hltv_world_ranking': {'rank': 6, 'rank_text': '#6'},
                             'coach': {'name': "Ashley 'ash' Battye"},
                             'weeks_in_top30_core': '161', 'average_player_age': '25.5',
                             'players': [{'nick': n} for n in
                                         ('xantares', 'woxic', 'jimpphat', 'kyxsan', 'wicadia')]}},
        'aurora_transfer_log': {
            'source_url': 'https://www.hltv.org/news/44998/summer-2026-rostermania-as-it-happened',
            'entries': [{'hltv_displayed_date': '08/07 15:35', 'entry': 'kyxsan joins Aurora'},
                        {'hltv_displayed_date': '03/07 20:20',
                         'entry': 'Aurora complete Jimpphat signing'}]},
        'limitations': [],
    }
    build_evidence(tmp, rows=rows, moneylines=moneylines, books=books, valve=valve)
    observations = json.loads((tmp / 'observations.json').read_text())
    observations['hltv'] = hltv
    (tmp / 'observations.json').write_text(json.dumps(observations))
    return audit(tmp), observations


class RowSourcePolicy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.audit_data, self.observations = synthetic_audit(Path(self.tmp.name))
        self.html = render(self.audit_data, self.observations)

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_row_carries_an_official_link_or_says_it_is_unverified(self):
        result = audit_html(self.html, PAGE)
        self.assertEqual(result['violation'], 0,
                         json.dumps(result['violations'], indent=1)[:2000])
        self.assertGreater(result['ok'], 20)

    def test_the_page_has_a_main_landmark_and_a_mobile_viewport(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        self.assertIsNotNone(soup.find('main'))
        self.assertIsNotNone(soup.find('meta', attrs={'name': 'viewport'}))
        self.assertEqual(soup.find('html').get('lang'), 'en')

    def test_no_link_is_root_relative(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        for el in soup.select('[href], [src]'):
            value = el.get('href') or el.get('src')
            self.assertFalse(str(value).startswith('/'),
                             f'root-relative link breaks project Pages paths: {value}')

    def test_every_anchor_the_summary_links_to_exists_on_the_page(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        ids = {el.get('id') for el in soup.find_all(id=True)}
        for el in soup.select('a[href^="#"]'):
            self.assertIn(el['href'][1:], ids, f'dangling in-page anchor {el["href"]}')

    def test_no_inline_script_and_no_external_asset(self):
        self.assertNotIn('<script', self.html)
        soup = BeautifulSoup(self.html, 'html.parser')
        for el in soup.select('[src]'):
            self.assertFalse(str(el.get('src')).startswith('http'),
                             'an external asset would break the published CSP')


class NothingIsInvented(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.audit_data, self.observations = synthetic_audit(Path(self.tmp.name))
        self.html = render(self.audit_data, self.observations)

    def tearDown(self):
        self.tmp.cleanup()

    def test_an_unresolved_fixture_renders_blank_and_flagged_with_no_percentage(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        card = soup.find(id='unresolved-1081527')
        self.assertIsNotNone(card)
        text = card.get_text(' ', strip=True)
        self.assertIn('blank', text.lower())
        classes = ' '.join(' '.join(c.get('class') or []) for c in card.find_all(True))
        self.assertIn('unverified', (classes + ' ' + text).lower())
        self.assertNotRegex(re.sub(r'\s+', ' ', text), r'\b\d{1,3}\.\d%\s*(chance|win)',
                            'an unresolved fixture must not show a win percentage')
        self.assertIn('0.93', text, 'the reason the ladder rejected the line is shown verbatim')

    def test_a_resolved_fixture_shows_both_probabilities_and_badges_the_pick(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        card = soup.find(id='1080205')
        self.assertIsNotNone(card)
        text = card.get_text(' ', strip=True)
        self.assertIn('69.3%', text)
        self.assertIn('30.7%', text)
        self.assertIn('PICK', text)
        self.assertIn('Aurora', text)
        picked = card.select_one('.team.pick .name')
        self.assertIn('Aurora', picked.get_text())

    def test_the_pick_badge_appears_exactly_once_per_card(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        for card in soup.select('article.pick-card'):
            badges = card.select('.team.pick')
            self.assertLessEqual(len(badges), 1, f'{card.get("id")} badges two picks')

    def test_rest_is_arithmetic_on_hltv_timestamps_not_a_fatigue_claim(self):
        twc = twc_context(self.audit_data, self.observations)
        by_team = {row['team']: row for row in twc['load']}
        self.assertIn('Aurora', by_team)
        # Aurora finished 2026-10-15T10:47:22Z and starts 2026-10-16T14:00:00Z.
        self.assertEqual(by_team['Aurora']['rest'], '27h 12m')
        self.assertEqual(by_team['Aurora']['maps_played'], 2)
        section = render(self.audit_data, self.observations)
        self.assertIn('not a fatigue model', section)

    def test_the_roster_verdict_states_the_dates_hltv_published(self):
        twc = twc_context(self.audit_data, self.observations)
        text = twc['roster_verdict']['text']
        self.assertIn('08/07', text)
        self.assertIn('not recent', text)

    def test_a_missing_hltv_feed_states_that_instead_of_rendering_nothing(self):
        observations = dict(self.observations, hltv={'limitations': ['not readable']})
        html = render(self.audit_data, observations)
        soup = BeautifulSoup(html, 'html.parser')
        for anchor in ('deciders', 'roster'):
            self.assertIsNotNone(soup.find(id=anchor), f'#{anchor} must always exist')
        self.assertIn('not readable', soup.find(id='deciders').get_text(' ', strip=True).lower())
        self.assertEqual(audit_html(html, PAGE)['violation'], 0)


class PublishedArtifacts(unittest.TestCase):
    def test_css_declares_no_external_resource(self):
        self.assertNotIn('url(http', CSS)
        self.assertNotIn('@import', CSS)
        self.assertIn('prefers-reduced-motion', CSS)
        self.assertIn('@media (min-width:44rem)', CSS, 'the layout must widen past a phone')

    def test_build_writes_the_page_and_stylesheet_into_a_site_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / 'data' / 'research' / 'ba7164a0'
            audit_data, observations = synthetic_audit(evidence)
            (evidence / 'audit.json').write_text(json.dumps(audit_data))
            (evidence / 'observations.json').write_text(json.dumps(observations))
            site = Path(tmp) / 'site'
            page = build(Path(tmp) / 'data', site)
            self.assertEqual(page, site / REPORT_NAME)
            self.assertTrue(page.is_file())
            self.assertTrue((site / 'assets' / 'verify-report.css').is_file())


@unittest.skipUnless((ROOT / 'data' / 'research' / 'ba7164a0' / 'audit.json').exists(),
                     'committed audit dossier not present')
class RealBuild(unittest.TestCase):
    """End to end: the committed dossier must survive the site's own two gatekeepers."""

    def test_the_committed_report_passes_check_links_and_the_row_source_audit(self):
        from scripts.build import build as build_site
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / 'site'
            build_site(ROOT / 'data', site)
            page = site / REPORT_NAME
            self.assertTrue(page.is_file(), 'the report was not copied into the site')
            result = audit_html(page.read_text(), PAGE)
            self.assertEqual(result['violation'], 0,
                             json.dumps(result['violations'], indent=1)[:2000])
            check_links(site)


if __name__ == '__main__':
    unittest.main()
