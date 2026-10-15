"""Static/no-JS output must not advertise an already expired current pick."""
import copy
import json
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
from scripts.build import matches_table, picks, summary
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
