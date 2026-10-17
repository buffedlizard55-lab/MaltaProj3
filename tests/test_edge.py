"""The dated upset review must be source-linked, scoped and never inventive.

These tests protect three properties of `data/edge-review.json` and
`scripts/build_edge.py`:

1. every published fact carries an official https source *and* its own
   observation time, so a reviewer can re-check it,
2. the renderer never fabricates a Hotspawn link — it takes the fixture URL from
   the verified inventory row and renders 'unverified' when that row is absent,
3. displayed market prices, map scores and counts are exactly the recorded
   values, and unconfirmed lineups stay blank.
"""
import copy
import json
import re
import unittest
from statistics import median
from html import escape
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import build_edge
from scripts.build_edge import edge_review, load_edge

ROOT = Path(__file__).resolve().parents[1]
EDGE = ROOT / 'data' / 'edge-review.json'
LATEST = ROOT / 'data' / 'latest.json'


def review():
    return load_edge(EDGE)


def inventory():
    return json.loads(LATEST.read_text())


class ReviewDataContractTests(unittest.TestCase):
    def test_every_source_is_https_and_timestamped(self):
        data = review()
        seen = 0
        for group in ['day_one', 'day_two', 'day_three', 'roster_watch', 'edge_rules']:
            if group == 'day_three' and group not in data:
                continue
            for row in data[group]:
                self.assertTrue(row.get('sources'), f'{group} row without sources')
                for src in row['sources']:
                    self.assertTrue(src['url'].startswith('https://'), src)
                    self.assertTrue(src.get('observed_at'), src)
                    seen += 1
        for src in data['headline']['sources'] + data['event']['sources']:
            self.assertTrue(src['url'].startswith('https://') and src.get('observed_at'))
            seen += 1
        self.assertGreater(seen, 20, 'the review should stay densely sourced')

    def test_research_window_is_bounded_and_preparation_is_inside_it_or_later(self):
        data = review()
        window = data['research_window']
        self.assertLess(window['from'], window['to'])
        self.assertLessEqual(window['to'], data['prepared_at'])

    def test_day_one_upset_is_the_documented_9z_aurora_series(self):
        data = review()
        upset = [r for r in data['day_one'] if r.get('upset')]
        self.assertEqual(len(upset), 1, 'exactly one day-one series is labeled an upset')
        row = upset[0]
        self.assertEqual((row['team_a'], row['team_b'], row['score']), ('9z', 'Aurora', '2-0'))
        self.assertEqual([m['map'] for m in row['maps']], ['Inferno', 'Nuke'])
        self.assertTrue(any('hltv.org' in s['url'] for s in row['sources']))

    def test_no_hotspawn_url_is_written_into_the_review_data(self):
        """Hotspawn links come from the verified inventory, never from prose."""
        text = EDGE.read_text()
        self.assertNotIn('hotspawn.com/matches', text)
        for row in review()['day_two']:
            self.assertNotIn('url', row)

    def test_unverified_values_stay_null_instead_of_guessed(self):
        data = review()
        falcons = next(r for r in data['roster_watch'] if r['team'] == 'Falcons')
        self.assertIsNone(falcons['current_lineup'], 'an unconfirmed current lineup must stay blank')
        self.assertIsNone(falcons['rankings'])
        self.assertIsNotNone(falcons.get('valve_snapshot'), 'the dated official snapshot is published instead')

    def test_loader_rejects_missing_keys_and_unsafe_sources(self):
        data = json.loads(EDGE.read_text())
        broken = copy.deepcopy(data)
        del broken['day_one']
        with self.assertRaises(ValueError):
            _write_and_load(broken)
        unsafe = copy.deepcopy(data)
        unsafe['day_one'][0]['sources'][0]['url'] = 'http://insecure.example/match'
        with self.assertRaises(ValueError):
            _write_and_load(unsafe)
        unstamped = copy.deepcopy(data)
        unstamped['day_two'][0]['sources'][0].pop('observed_at')
        with self.assertRaises(ValueError):
            _write_and_load(unstamped)


def _write_and_load(payload):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'edge-review.json'
        path.write_text(json.dumps(payload))
        return load_edge(path)


class ReviewRenderingTests(unittest.TestCase):
    def body(self, data=None):
        return edge_review(data or inventory(), '../', EDGE)

    def test_required_sections_and_anchors_are_rendered(self):
        soup = BeautifulSoup(self.body(), 'html.parser')
        for anchor in ['day-one', 'rosters', 'rules', 'day-two', 'day-three', 'day-three-results', 'day-four', 'standings', 'lineup-disambiguation', 'edge-limitations']:
            self.assertIsNotNone(soup.find(id=anchor), anchor)
        self.assertEqual(len(soup.select('#day-one tbody tr')), len(review()['day_one']))
        self.assertEqual(len(soup.select('#day-two tbody tr')), len(review()['day_two']))
        self.assertEqual(len(soup.select('#rules .resolution-step')), len(review()['edge_rules']))
        self.assertEqual(len(soup.select('#lineup-disambiguation tbody tr')), 5)

    def test_all_day_one_rows_have_verified_five_player_lineups_and_day_three_has_live_markets(self):
        data = review()
        for row in data['day_one']:
            self.assertEqual(len(row['verified_lineup_a']), 5, row['team_a'])
            self.assertEqual(len(row['verified_lineup_b']), 5, row['team_b'])
        falcons_opener = next(r for r in data['day_one'] if r['team_a'] == 'Falcons')
        self.assertIn('karrigan', falcons_opener['verified_lineup_a'])
        for row in data['day_three']:
            self.assertIsNotNone(row['hotspawn_id'])
            self.assertIsNotNone(row['market'])
            self.assertAlmostEqual(sum(row['market']['prices'].values()), 1.0, places=4)

    def test_day_two_rows_use_the_verified_inventory_hotspawn_link(self):
        """Hotspawn links come from the live inventory; fixtures the scheduled
        feed has dropped are labeled unverified instead of being guessed."""
        data = inventory()
        soup = BeautifulSoup(self.body(data), 'html.parser')
        by_id = {str(m['id']): m for m in data['matches']}
        rendered = {a.get('href') for a in soup.select('#day-two a[href^="https://"]')}
        present = [r for r in review()['day_two'] if str(r['hotspawn_id']) in by_id]
        absent = [r for r in review()['day_two'] if str(r['hotspawn_id']) not in by_id]
        self.assertTrue(present or absent)
        for row in present:
            self.assertIn(by_id[str(row['hotspawn_id'])]['source_url'], rendered, row['hotspawn_id'])
        for row in absent:
            self.assertIn('Hotspawn row not in this snapshot', soup.find(id='day-two').get_text())

    def test_missing_inventory_row_renders_unverified_not_a_guessed_link(self):
        data = inventory()
        data['matches'] = [m for m in data['matches'] if str(m['id']) != '1080202']
        html = self.body(data)
        self.assertIn('Hotspawn row not in this snapshot', html)
        self.assertNotIn('hotspawn.com/matches/9z-vs-falcons', html)

    def test_displayed_prices_match_the_recorded_observations(self):
        soup = BeautifulSoup(self.body(), 'html.parser')
        table = soup.find(id='day-two')
        for row in review()['day_two']:
            market = row.get('market') or {}
            for name, value in (market.get('prices') or {}).items():
                self.assertIn(f'{value * 100:.1f}%', table.get_text())
            self.assertIn(name, table.get_text())

    def test_limitations_and_policy_are_published_on_the_page(self):
        rendered = self.body()
        for limitation in review()['limitations']:
            self.assertIn(escape(limitation)[:80], rendered, limitation[:40])
        self.assertIn('dated research', rendered.lower())
        self.assertIn('never read', rendered)

    def test_day_three_results_and_day_four_render_with_sources(self):
        soup = BeautifulSoup(self.body(), 'html.parser')
        self.assertIsNotNone(soup.find(id='day-three-results'))
        self.assertIsNotNone(soup.find(id='day-four'))
        self.assertIsNotNone(soup.find(id='day-four-guidance'))
        results = review()['day_three_results']
        self.assertEqual(len(soup.select('#day-three-results tbody tr')), len(results))
        day_four = review()['day_four']
        self.assertEqual(len(soup.select('#day-four tbody tr')), len(day_four))

    def test_day_four_displayed_prices_match_the_recorded_observations(self):
        soup = BeautifulSoup(self.body(), 'html.parser')
        table = soup.find(id='day-four')
        for row in review()['day_four']:
            market = row.get('market') or {}
            for name, value in (market.get('prices') or {}).items():
                self.assertIn(f'{value * 100:.1f}%', table.get_text(), name)

    def test_day_four_prices_equal_the_median_of_its_provider_books(self):
        """Every published pair must be reproducible from its own provider quotes."""
        for row in review()['day_four']:
            market = row['market']
            providers = market['providers']
            self.assertGreaterEqual(len(providers), 2, market['provider'])
            for provider in providers:
                for bid, ask in zip(provider['bid'], provider['ask']):
                    self.assertLess(bid, ask, provider['provider'])
                    self.assertLessEqual(round(ask - bid, 8), 0.12, provider['provider'])
            normalized = []
            for provider in providers:
                mids = [(bid + ask) / 2 for bid, ask in zip(provider['bid'], provider['ask'])]
                normalized.append([mid / sum(mids) for mid in mids])
            combined = [median(pair[index] for pair in normalized) for index in (0, 1)]
            total = sum(combined)
            expected = [round(value / total, 4) for value in combined]
            self.assertEqual([round(v, 4) for v in market['prices'].values()], expected, market['provider'])

    def test_a_semifinal_without_a_market_renders_an_unverified_marker(self):
        """No market ⇒ explicit unverified marker, never an invented number."""
        row = {'slot': 'Semifinal 1', 'competition': 'Thunderpick World Championship 2026',
               'team_a': 'FURIA', 'team_b': 'Aurora', 'starts_at': '2026-10-17T14:00:00Z',
               'market': None, 'status_at_observation': 'Scheduled.', 'assessment': 'No price written.',
               'sources': [{'url': 'https://www.hltv.org/results?event=8932', 'source': 'HLTV.org event results',
                            'detail': 'Fixture only.', 'observed_at': '2026-10-17T00:02:00Z'}]}
        rendered = build_edge.day_four_section({'day_four': [row]})
        table = BeautifulSoup(rendered, 'html.parser').find('table')
        self.assertIn('no verified market at the dated observation', table.get_text())
        self.assertIsNone(re.search(r'\d+(\.\d+)?%', table.get_text()), table.get_text())

    def test_day_four_guidance_lists_every_principle(self):
        soup = BeautifulSoup(self.body(), 'html.parser')
        guidance = review()['day_four_guidance']
        self.assertEqual(len(soup.select('#day-four-guidance li')), len(guidance['principles']))

    def test_day_three_results_never_complete_an_unfinished_series(self):
        data = review()
        open_rows = [r for r in data['day_three_results'] if r.get('result') is None]
        for row in open_rows:
            self.assertIn('in progress', row['status_at_observation'].lower())

    def test_standings_table_replays_the_official_valve_snapshot(self):
        block = review()['valve_standings']
        soup = BeautifulSoup(self.body(), 'html.parser')
        rows = soup.select('#standings tbody tr')
        self.assertEqual(len(rows), len(block['rows']))
        for row in rows:
            text = row.get_text(' ', strip=True)
            self.assertIn('points', text)
        self.assertIn(block['git_blob_sha'], EDGE.read_text())
        self.assertIn(block['source_url'], str(soup))


class NavigationIntegrationTests(unittest.TestCase):
    def test_edge_page_is_part_of_the_published_navigation(self):
        from scripts.build import PAGES
        self.assertIn('edge', PAGES)
        self.assertEqual(PAGES['edge'][1], 'edge/index.html')

    def test_executive_summary_links_to_the_review_and_maps_the_site(self):
        from scripts.build import summary
        data = inventory()
        originated = json.loads((ROOT / 'data' / 'origination.json').read_text())
        data['fallbacks'] = {str(r['id']): r for r in originated['matches'] if r.get('origination')}
        originated = json.loads((ROOT / 'data' / 'origination.json').read_text())
        data['complete_picks'] = originated
        from scripts.contrarian import derive_context, load_review
        data['_contrarian'] = derive_context(data, load_review(ROOT / 'data' / 'contrarian.json'))
        soup = BeautifulSoup(summary(data, './'), 'html.parser')
        self.assertIsNotNone(soup.find(id='contrarian'), 'the bounded contrarian review stays on the summary')
        self.assertIsNotNone(soup.find(id='site-map'))
        links = {a.get('href') for a in soup.select('#site-map a[href]')}
        for target in ['./picks/', './edge/', './origination/#picks', './coverage/', './methodology/', './review/']:
            self.assertIn(target, links)
        shortcuts = {a.get('href') for a in soup.select('.briefing-links a[href]')}
        self.assertIn('./edge/', shortcuts)


if __name__ == '__main__':
    unittest.main()
