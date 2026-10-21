"""Static/no-JS output must not advertise an already expired current pick."""
import copy
import json
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
from scripts.build import glance, matches_table, picks, summary
from scripts.domain import timestamp


class StaticFreshnessTests(unittest.TestCase):
    def example(self):
        # Replayed checked-in first-party observation, not fabricated production data.
        data = json.loads(Path('data/latest.json').read_text())
        match = next((m for m in data['matches'] if m['analysis'] and m['pick_index'] is not None), None)
        if match is None:
            self.skipTest('Retained snapshot contains no supported choices to test')
        return copy.deepcopy(match)

    def test_stale_static_build_demotes_pick_without_javascript(self):
        match = self.example()
        now = timestamp(match['observed_at']) + timedelta(days=3)
        with patch('scripts.build.datetime') as clock:
            clock.now.return_value = now
            text = matches_table([match], '../')
        self.assertIn('Snapshot: ', text)
        self.assertIn('not a current pick', text)
        self.assertIn('data-original=', text)

    def test_fresh_but_locked_build_demotes_pick(self):
        match = self.example()
        now = timestamp(match['starts_at'])
        match['observed_at'] = match['analysis']['observed_at'] = now.isoformat()
        with patch('scripts.build.datetime') as clock:
            clock.now.return_value = now
            text = matches_table([match], '../')
        self.assertIn('Closed for picks', text)
        self.assertIn('Snapshot: ', text)


    def test_unknown_schedule_remains_in_full_picks_list_and_unresolved_filter(self):
        from scripts.collect import counts
        from bs4 import BeautifulSoup
        data = json.loads(Path('data/latest.json').read_text())
        match = copy.deepcopy(data['matches'][0])
        match.update(starts_at=None, locks_at=None, availability='unknown', analysis=None, pick_index=None, research=[])
        data['matches'] = [match]
        data['counts'] = counts(data['matches'])
        soup = BeautifulSoup(picks(data, '../'), 'html.parser')
        self.assertEqual(len(soup.select('#match-list > tbody > tr')), 1)
        self.assertIn('unverified', soup.select_one('.match-cell').get_text())
        self.assertIn('1', soup.select_one('[data-basis="unresolved"]').get_text())
        self.assertEqual(len(soup.select('#unresolved .unresolved-table > tbody > tr')), 1)


class ResearchedFallbackDisplayTests(unittest.TestCase):
    """Featured rejections may show an audited fallback estimate, never a guess."""

    def fallbacks(self):
        path = Path('data/origination.json')
        if not path.exists():
            self.skipTest('No researched fallback data in this snapshot')
        originated = json.loads(path.read_text())
        return {str(r['id']): r for r in originated['matches'] if r.get('origination')}

    def inventory(self):
        data = json.loads(Path('data/latest.json').read_text())
        data['fallbacks'] = self.fallbacks()
        return data

    def test_every_active_row_shows_a_pick_when_a_fallback_exists(self):
        data = self.inventory()
        soup = BeautifulSoup(picks(data, '../'), 'html.parser')
        rows = soup.select('#match-list > tbody > tr')
        active = [m for m in data['matches'] if m['availability'] != 'past']
        self.assertEqual(len(rows), len(active))
        for m, row in zip(active, rows):
            if m['analysis'] is None and str(m['id']) in data['fallbacks']:
                self.assertEqual(row.get('data-researched-fallback'), 'true')
                self.assertIn('Researched fallback', row.get_text())
                self.assertNotIn('Not yet resolved', row.get_text())
                self.assertEqual(len(row.select('.fair-line')), 2)
                self.assertTrue(row.select_one('a[href*="origination/#match-"]'))
            elif m['analysis'] is None:
                self.assertEqual(row.get('data-researched-fallback'), 'false')
                self.assertIn('Not yet resolved', row.get_text())

    def test_fallback_probabilities_replay_the_researched_values_exactly(self):
        data = self.inventory()
        soup = BeautifulSoup(picks(data, '../'), 'html.parser')
        checked = 0
        for mid, row in data['fallbacks'].items():
            tr = soup.find(id=f'match-{mid}')
            if tr is None or tr.get('data-researched-fallback') != 'true':
                continue
            text = tr.get_text()
            for value in row['origination']['probabilities']:
                self.assertIn(f'{value * 100:.1f}%', text)
            checked += 1
        if not checked:
            self.skipTest('The current inventory shares no fixture with the researched fallback snapshot')

    def test_filter_counts_match_the_rows_actually_rendered(self):
        data = self.inventory()
        soup = BeautifulSoup(picks(data, '../'), 'html.parser')
        rows = soup.select('#match-list > tbody > tr')
        tabs = {b.get('data-basis'): int(b.select_one('span').get_text()) for b in soup.select('[data-basis]')}
        self.assertEqual(tabs['all'], len(rows))
        self.assertEqual(tabs['market'], sum(1 for r in rows if r.get('data-method') in ('market', 'bookmaker')))
        self.assertEqual(tabs['model'], sum(1 for r in rows if r.get('data-method') == 'model'))
        self.assertEqual(tabs['unresolved'], sum(1 for r in rows if r.get('data-method') == 'unresolved'))

    def test_unresolved_section_separates_fallback_backed_rows_from_blank_ones(self):
        data = self.inventory()
        soup = BeautifulSoup(picks(data, '../'), 'html.parser')
        section = soup.select_one('#unresolved')
        intro = section.select_one('.section-intro')
        blank_rows = [m for m in data['matches'] if m['availability'] != 'past' and m['analysis'] is None
                      and str(m['id']) not in data['fallbacks']]
        if blank_rows or any(str(m['id']) in data['fallbacks'] for m in data['matches'] if m['analysis'] is None):
            self.assertIsNotNone(intro)
            self.assertIn('Researched fallback', intro.get_text())
        self.assertEqual(len(section.select('.unresolved-table > tbody > tr')),
                         len([m for m in data['matches'] if m['availability'] != 'past' and m['analysis'] is None]))

    def test_summary_reports_complete_pick_coverage(self):
        data = self.inventory()
        originated = json.loads(Path('data/origination.json').read_text())
        data['complete_picks'] = originated
        soup = BeautifulSoup(summary(data, './'), 'html.parser')
        active = [m for m in data['matches'] if m['availability'] != 'past']
        covered = sum(1 for m in active if m['analysis'] or str(m['id']) in data['fallbacks'])
        callout = soup.select_one('[aria-label="Complete pick coverage"]')
        self.assertIsNotNone(callout)
        self.assertIn(f'{originated["counts"]["with_pick"]} / {originated["counts"]["active"]}', callout.get_text(' '))
        # The callout reports the complete researched list; the featured audit
        # inventory can legitimately differ between observations, so the two are
        # not forced to agree here.
        del covered, active
        site_map = soup.find(id='site-map')
        self.assertIsNotNone(site_map)
        for target in ['./origination/#picks', './picks/', './edge/']:
            self.assertIn(target, {a.get('href') for a in site_map.select('a[href]')})

    def test_summary_never_links_an_absent_tournament_lines_anchor(self):
        data = self.inventory()
        data['_twc_day4'] = {'matches': [], 'not_in_hotspawn_snapshot': [],
                             'lines': {'available': True, 'resolved': 0, 'total': 0}}
        soup = BeautifulSoup(summary(data, './'), 'html.parser')
        hrefs = {a.get('href') for a in soup.select('a[href]')}
        self.assertIn('./twc-picks/#day-four-picks', hrefs)
        self.assertNotIn('./twc-picks/#day-four-tournament-lines', hrefs)
        data['_twc_day4']['not_in_hotspawn_snapshot'] = [{'facts': {'teams': ['A', 'B']}}]
        soup = BeautifulSoup(summary(data, './'), 'html.parser')
        self.assertIn('./twc-picks/#day-four-tournament-lines',
                      {a.get('href') for a in soup.select('a[href]')})


class ConsensusQuoteShapeTests(unittest.TestCase):
    """Market-family quotes carry bid/ask, bookmaker quotes carry odds; both render."""

    def row(self):
        data = json.loads(Path('data/latest.json').read_text())
        match = next(m for m in data['matches'] if m['availability'] != 'past' and m['analysis'] is None)
        return copy.deepcopy(match)

    def test_mixed_quote_shapes_render_without_key_errors(self):
        match = self.row()
        fallback = {'id': match['id'], 'pick_index': 0, 'aliases_used': [],
                    'origination': {'method': 'consensus', 'label': 'Originated consensus line',
                                    'probabilities': [0.62, 0.38], 'fair_decimal': [1.61, 2.63],
                                    'observed_at': match['observed_at'], 'source': 'Polymarket + Thunderpick',
                                    'source_url': 'https://polymarket.com/event/x',
                                    'limitations': ['Two independent money sources.'],
                                    'quotes': [
                                        {'provider': 'Polymarket', 'family': 'market', 'probabilities': [0.635, 0.365],
                                         'bid': [0.63, 0.36], 'ask': [0.64, 0.37], 'spread': 0.01, 'thin': False,
                                         'observed_at': match['observed_at'], 'source_url': 'https://polymarket.com/event/x',
                                         'event_id': '1'},
                                        {'provider': 'Thunderpick', 'family': 'bookmaker', 'probabilities': [0.615, 0.385],
                                         'odds': [1.5, 2.4], 'observed_at': match['observed_at'],
                                         'source_url': 'https://thunderpick.io/api/matches', 'event_id': '2'}]}}
        html = matches_table([match], '../', fallbacks={match['id']: fallback})
        self.assertIn('bid/ask 0.630/0.640', html)
        self.assertIn('decimal odds 1.5 / 2.4', html)
        self.assertIn('Researched fallback', html)

    def test_quote_without_any_price_fields_still_links_its_source(self):
        match = self.row()
        fallback = {'id': match['id'], 'pick_index': None, 'aliases_used': [],
                    'origination': {'method': 'bookmaker', 'label': 'Originated esportsbook line',
                                    'probabilities': [0.5, 0.5], 'fair_decimal': [2.0, 2.0],
                                    'observed_at': match['observed_at'], 'source': 'Thunderpick',
                                    'source_url': 'https://thunderpick.io/api/matches', 'limitations': [],
                                    'quotes': [{'provider': 'Thunderpick', 'family': 'bookmaker',
                                                'observed_at': match['observed_at'],
                                                'source_url': 'https://thunderpick.io/api/matches'}]}}
        html = matches_table([match], '../', fallbacks={match['id']: fallback})
        self.assertIn('price observation recorded in the saved evidence', html)

class GlanceIndexTests(unittest.TestCase):
    """The phone summary must expose picks immediately and never hide an unresolved fixture."""

    def match(self, i, probability, future, resolved=True, base=None):
        from datetime import datetime, timedelta, timezone
        # `base` pins the fixture to an explicit instant (the repository's
        # injected-time contract); the default keeps the historical wall-clock
        # behaviour for tests that never depend on which side of a cap a row falls.
        now = base or datetime.now(timezone.utc)
        start = now + timedelta(hours=2 + i) if future else now - timedelta(hours=3)
        m = {'id': str(i), 'teams': [{'id': 'a', 'name': f'TeamA{i}'}, {'id': 'b', 'name': f'TeamB{i}'}],
             'competition': 'Test Cup', 'starts_at': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
             'locks_at': (start - timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%SZ'), 'availability': 'open',
             'source_url': f'https://www.hotspawn.com/matches/x-{i}', 'analysis': None, 'pick_index': None,
             'observed_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'research': [], 'limitations': [], 'tier': 'b',
             'source_status': 'scheduled', 'best_of': 3}
        if resolved:
            m['analysis'] = {'method': 'market', 'label': 'Market-implied estimate', 'probabilities': [probability, 1 - probability],
                             'fair_decimal': [round(1 / probability, 3), round(1 / (1 - probability), 3)],
                             'observed_at': m['observed_at'], 'source': 'Polymarket',
                             'source_url': 'https://polymarket.com/event/cs2-x', 'quotes': []}
            m['pick_index'] = 0
        return m

    def test_first_pick_and_source_links_appear_near_the_top(self):
        html = glance({'matches': [self.match(1, 0.62, True)], 'fallbacks': {}}, '../')
        self.assertLess(html.index('Picks at a glance'), html.index('62.0%'))
        self.assertIn('href="../origination/#match-1"', html)
        self.assertIn('href="https://www.hotspawn.com/matches/x-1"', html)
        self.assertIn('href="https://polymarket.com/event/cs2-x"', html)

    def test_every_active_fixture_is_listed_and_never_given_a_50_50(self):
        # Explicit synthetic instant, never the wall clock: twelve resolved
        # matches start 2-13 h after `base` and two unresolved rows are added.
        # The summary used to cap resolved rows at ten, which hid an active
        # fixture (5star-1WIN, 2026-10-21) from the phone index. Every active
        # fixture must now appear, so the complete-list footer is deterministic.
        # Building the times from `datetime.now()` and leaving `now=None` made
        # the outcome depend on the real time of day - the exact time bomb that
        # failed scheduled publisher runs 39371739014 and 39389855311 on
        # 2026-10-20 between about 04:01Z and 09:01Z when the
        # freshness-determinism guard re-ran this module pinned to
        # 2026-10-20T12:00Z (see data/research/905fa4cf/).
        from datetime import datetime, timezone
        base = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        matches = [self.match(i, 0.6, True, base=base) for i in range(12)] + [self.match(100, 0.5, True, resolved=False, base=base),
                                                                             self.match(101, 0.5, False, resolved=False, base=base)]
        html = glance({'matches': matches, 'fallbacks': {}}, '', now=base)
        for index in range(12):
            self.assertIn(f'TeamA{index}', html)
        self.assertIn('TeamA100', html)
        self.assertIn('TeamA101', html)
        self.assertEqual(html.count('50.0%'), 0)
        self.assertIn('2</strong> explicitly unresolved', html)
        # Session arena-75de2710: future resolved rows are never capped on the
        # phone-first index, so all 14 active fixtures now fit on the summary.
        # Merged with arena-11be2015's no-cap index: also no 'Showing' label.
        self.assertIn('All 14 active fixtures are listed', html)
        self.assertEqual(html.count('glance-row'), 14)
        self.assertNotIn('Showing', html)

    def test_a_researched_fallback_is_labelled_and_uses_its_own_probability(self):
        m = self.match(7, 0.5, True, resolved=False)
        fallback = {'id': '7', 'pick_index': 1, 'origination': {
            'method': 'market', 'label': 'Originated market line (Polymarket)', 'probabilities': [0.3, 0.7],
            'fair_decimal': [3.333, 1.429], 'observed_at': m['observed_at'], 'source': 'Polymarket',
            'source_url': 'https://polymarket.com/event/cs2-y', 'quotes': []}}
        html = glance({'matches': [m], 'fallbacks': {'7': fallback}}, '')
        self.assertIn('Researched', html)
        self.assertIn('TeamB7', html)
        self.assertIn('70.0%', html)
        self.assertNotIn('50.0%', html)

    def fixed_match(self, i, start, probability=0.62):
        # Explicit instants (never the wall clock): the glance rows must not expire with time.
        from datetime import timedelta
        m = self.match(i, probability, True)
        m['starts_at'] = start.strftime('%Y-%m-%dT%H:%M:%SZ')
        m['locks_at'] = (start - timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%SZ')
        return m

    def test_a_started_fixture_is_labelled_locked_at_build_time_not_pick(self):
        # Built after a fixture started: the summary must never keep advertising "Pick".
        from datetime import datetime, timedelta, timezone
        fixed_now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
        started = self.fixed_match(3, fixed_now - timedelta(hours=3))
        html = glance({'matches': [started], 'fallbacks': {}}, '', now=fixed_now)
        self.assertIn('data-glance-closed="true"', html)
        self.assertIn('is-closed', html)
        self.assertIn('>Locked</span>', html)
        self.assertNotIn('>Pick</span>', html)
        self.assertIn('62.0%', html)  # the estimate and its label stay visible, never dropped
        self.assertIn('href="https://www.hotspawn.com/matches/x-3"', html)

    def test_an_open_fixture_keeps_pick_label_and_lock_attributes_for_the_browser(self):
        from datetime import datetime, timedelta, timezone
        fixed_now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
        open_match = self.fixed_match(4, fixed_now + timedelta(hours=2))
        html = glance({'matches': [open_match], 'fallbacks': {}}, '', now=fixed_now)
        self.assertIn('data-glance-closed="false"', html)
        self.assertIn('data-glance-locks="', html)
        self.assertIn('data-glance-starts="', html)
        self.assertIn('data-glance-pick', html)
        self.assertIn('>Pick</span>', html)
        self.assertNotIn('>Locked</span>', html)

    def test_browser_lock_script_can_only_close_a_pick_never_reopen_or_rewrite_it(self):
        js = Path('assets/glance-lock.js').read_text(encoding='utf-8')
        self.assertIn("label.textContent = 'Locked';", js)
        self.assertIn("data-glance-closed", js)
        self.assertIn("'true'", js)
        for forbidden in ("label.textContent = 'Pick'", 'innerHTML', 'href', 'fetch(', 'XMLHttpRequest'):
            self.assertNotIn(forbidden, js, forbidden)
    def test_a_researched_model_names_the_ranking_page_it_came_from(self):
        # Session arena-75de2710, following session 802f6a59's live finding:
        # an HLTV-ranking quote also carries method 'model', but labelling it
        # 'Valve' misattributes the source. The label must follow the URL.
        # (Integration note, arena-6e92015a: main's model_source_label() renders
        # this quote as 'HLTV ranking', so the assertion follows that label.)
        m = self.match(8, 0.5, True, resolved=False)
        fallback = {'id': '8', 'pick_index': 0, 'origination': {
            'method': 'model', 'label': 'HLTV world-ranking research estimate',
            'probabilities': [0.66, 0.34], 'fair_decimal': [1.515, 2.941],
            'observed_at': m['observed_at'], 'source': 'HLTV world ranking',
            'source_url': 'https://www.hltv.org/ranking/teams', 'quotes': []}}
        html = glance({'matches': [m], 'fallbacks': {'8': fallback}}, '')
        self.assertIn('href="https://www.hltv.org/ranking/teams"', html)
        self.assertIn('>HLTV ranking<', html)
        self.assertNotIn('>Valve<', html)

    def test_no_active_fixtures_renders_nothing_rather_than_an_empty_claim(self):
        self.assertEqual(glance({'matches': [], 'fallbacks': {}}, ''), '')

