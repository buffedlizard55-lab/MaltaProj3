"""Session arena-3e64f4fb tests.

Two kinds of pin, kept separate so a closing coverage gap can never fail the
four-hour publisher again (the 2026-10-25 regression, 824A-R01):

* behaviour pins run entirely on synthetic fixtures: every replay rule and
  cross-layer rule is mutated until it must report an error;
* the dated dossier pin replays the committed verification against the root
  snapshot/origination ONLY while those files still carry the observation
  the dossier names; after the next publisher rotation it checks the
  dossier's internal consistency instead of failing.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data' / 'research' / '3e64f4fb' / 'verification.json'

import importlib
v = importlib.import_module('scripts.3e64f4fb_verify')
probe = importlib.import_module('scripts.3e64f4fb_probe')


def market_analysis(bid1=0.58, ask1=0.62, bid2=0.38, ask2=0.42):
    mid1, mid2 = (bid1 + ask1) / 2, (bid2 + ask2) / 2
    total = mid1 + mid2
    return {
        'method': 'market', 'probabilities': [mid1 / total, mid2 / total],
        'observed_at': '2026-10-26T00:00:00Z', 'source': 'Polymarket',
        'source_url': 'https://polymarket.com/event/test',
        'quotes': [{'bid': bid1, 'ask': ask1, 'spread': ask1 - bid1, 'midpoint': mid1},
                   {'bid': bid2, 'ask': ask2, 'spread': ask2 - bid2, 'midpoint': mid2}],
        'limitations': ['One market.'],
    }


def model_analysis(p1=1200, p2=1100):
    prob1, g = v.valve_probability(p1, p2)
    return {
        'method': 'model', 'probabilities': [round(prob1, 8), round(1 - prob1, 8)],
        'observed_at': '2026-10-26T00:00:00Z', 'source': 'Valve official standings',
        'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
        'inputs': [{'name': 'Alpha', 'points': p1, 'standing': 10, 'roster': [],
                    'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'},
                   {'name': 'Bravo', 'points': p2, 'standing': 20, 'roster': [],
                    'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'}],
        'rd_assumption': 75, 'g': g,
        'limitations': ['Research model.'],
    }


def fixture(fid, analysis, pick, availability='open'):
    return {
        'id': fid, 'teams': [{'name': 'Alpha'}, {'name': 'Bravo'}],
        'competition': 'Test Cup', 'starts_at': '2026-10-27T10:00:00Z',
        'availability': availability, 'analysis': analysis, 'pick_index': pick,
        'limitations': ['lim'], 'research': [{'stage': 'HLTV', 'status': 'checked'}],
    }


def snapshot_of(matches):
    active = [m for m in matches if m['availability'] != 'past']
    counts = {'inventory': len(matches), 'upcoming': len(active),
              'archived': len(matches) - len(active),
              'market': sum(1 for m in active if (m.get('analysis') or {}).get('method') == 'market'),
              'bookmaker': sum(1 for m in active if (m.get('analysis') or {}).get('method') == 'bookmaker'),
              'model': sum(1 for m in active if (m.get('analysis') or {}).get('method') == 'model'),
              'unresolved': sum(1 for m in active if not m.get('analysis')),
              'picks': sum(1 for m in active if m.get('pick_index') is not None)}
    return {'generated_at': '2026-10-26T00:05:00Z', 'inventory_observed_at': '2026-10-26T00:05:00Z',
            'counts': counts, 'matches': matches}


def origination_of(rows):
    return {'generated_at': '2026-10-26T00:06:00Z',
            'counts': {'active': len(rows)},
            'unresolved_ids': [str(r['id']) for r in rows
                               if not ((r.get('origination') or {}).get('probabilities'))],
            'matches': rows}


def org_row(fid, featured_method, origination, pick, aliases=None):
    return {'id': fid, 'teams': [{'name': 'Alpha'}, {'name': 'Bravo'}],
            'starts_at': '2026-10-27T10:00:00Z', 'featured_method': featured_method,
            'origination': origination, 'pick_index': pick, 'aliases_used': aliases or [],
            'limitations': ['lim'], 'research': [{'stage': 'HLTV', 'status': 'checked'}]}


def site_tree(active_ids, probs_by_id, model_ids=(), researched_ids=()):
    cards = ''.join(
        f'<article id="{fid}">Pick {"Alpha" if p and p[0] > p[1] else "Bravo"} '
        + (' '.join(f'{x * 100:.1f}%' for x in p) if p else '') + '</article>'
        for fid, p in ((i, probs_by_id.get(i)) for i in active_ids))
    noline = ''.join(f'<div id="no-line-{i}"></div>' for i in model_ids)
    researched = ''.join(f'<div id="researched-{i}"></div>' for i in researched_ids)
    index = ('<!doctype html><html lang="en"><head>'
             '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
             '<a href="./picks/">All picks</a><a href="./unresolved/">Unresolved</a>'
             '<section id="picks-at-a-glance">' + cards + '</section>'
             '<section id="unresolved-register">' + researched + '</section>'
             '<section id="no-line-register">' + noline + '</section>'
             '<section id="fallback-register"></section></body></html>')
    picks = ('<!doctype html><html lang="en"><head>'
             '<meta name="viewport" content="width=device-width"></head><body>'
             + ''.join(f'<div id="match-{i}">' + (' '.join(f'{x * 100:.1f}%'
                       for x in probs_by_id[i]) if probs_by_id.get(i) else '') + '</div>'
                       for i in active_ids) + '</body></html>')
    unresolved = ('<!doctype html><html lang="en"><head>'
                  '<meta name="viewport" content="width=device-width"></head><body>'
                  '<section id="unresolved-register"></section></body></html>')
    root = Path(tempfile.mkdtemp())
    (root / 'index.html').write_text(index)
    (root / 'picks').mkdir(); (root / 'picks' / 'index.html').write_text(picks)
    (root / 'unresolved').mkdir(); (root / 'unresolved' / 'index.html').write_text(unresolved)
    return root


class TwoLayerReplayTest(unittest.TestCase):
    def run_verify(self, matches, rows, probs=None, model_ids=(), researched_ids=()):
        ids = [str(m['id']) for m in matches if m['availability'] != 'past']
        site = site_tree(ids, probs or {}, model_ids, researched_ids)
        return v.verify(snapshot_of(matches), origination_of(rows), site)

    def test_clean_market_row_passes_both_layers(self):
        a = market_analysis()
        result = self.run_verify([fixture('1', a, 0)], [org_row('1', 'market', dict(a), 0)],
                                   probs={'1': a['probabilities']})
        self.assertEqual(result['errors'], [])

    def test_wrong_midpoint_fails(self):
        a = market_analysis()
        a['probabilities'] = [0.9, 0.1]
        result = self.run_verify([fixture('1', a, 0)], [org_row('1', 'market', dict(a), 0)],
                                   probs={'1': a['probabilities']})
        self.assertTrue(any('midpoint' in e for e in result['errors']))

    def test_pick_must_be_strict_favourite(self):
        a = market_analysis()
        result = self.run_verify([fixture('1', a, 1)], [org_row('1', 'market', dict(a), 1)],
                                   probs={'1': a['probabilities']})
        self.assertTrue(any('strict favourite' in e for e in result['errors']))

    def test_hotspawn_can_never_be_a_probability_source(self):
        a = market_analysis()
        a['source_url'] = 'https://play.hotspawn.com/cs2-pickems'
        result = self.run_verify([fixture('1', a, 0)], [org_row('1', 'market', dict(a), 0)],
                                   probs={'1': a['probabilities']})
        self.assertTrue(any('Hotspawn' in e for e in result['errors']))

    def test_model_row_replays_from_valve_points(self):
        a = model_analysis()
        result = self.run_verify([fixture('2', a, 0)], [org_row('2', 'model', dict(a), 0)],
                                   probs={'2': a['probabilities']}, model_ids=('2',))
        self.assertEqual(result['errors'], [])
        bad = model_analysis()
        bad['probabilities'] = [0.5, 0.5]
        result = self.run_verify([fixture('2', bad, 0)], [org_row('2', 'model', dict(bad), 0)],
                                   probs={'2': bad['probabilities']}, model_ids=('2',))
        self.assertTrue(any('Valve replay' in e for e in result['errors']))

    def test_featured_blank_resolved_by_research_needs_evidence(self):
        researched = {
            'method': 'market', 'probabilities': [0.87, 0.13],
            'observed_at': '2026-10-26T00:00:00Z', 'source': 'Polymarket',
            'source_url': 'https://polymarket.com/event/test',
            'quotes': [{'provider': 'Polymarket', 'bid': [0.82, 0.08], 'ask': [0.92, 0.18],
                        'probabilities': [0.87, 0.13]}],
        }
        alias = {'alias': 'Alpha Esports', 'canonical': 'Alpha',
                 'evidence': [{'url': 'https://www.hltv.org/matches/1/test'}]}
        result = self.run_verify(
            [fixture('3', None, None)],
            [org_row('3', None, researched, 0, aliases=[alias])],
            probs={'3': [0.87, 0.13]}, researched_ids=('3',))
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['checks']['cross_layer']['researched_resolutions'], ['3'])

        bare_alias = {'alias': 'Alpha Esports', 'canonical': 'Alpha', 'evidence': []}
        result = self.run_verify(
            [fixture('3', None, None)],
            [org_row('3', None, dict(researched), 0, aliases=[bare_alias])],
            probs={'3': [0.87, 0.13]}, researched_ids=('3',))
        self.assertTrue(any('without https evidence' in e for e in result['errors']))

    def test_complete_list_cannot_silently_replace_a_featured_estimate(self):
        a = market_analysis()
        other = market_analysis(0.78, 0.82, 0.18, 0.22)
        result = self.run_verify([fixture('1', a, 0)], [org_row('1', 'market', other, 0)],
                                   probs={'1': other['probabilities']})
        self.assertTrue(any('without declaring an upgrade' in e for e in result['errors']))

    def test_graduating_from_blank_to_sourced_pick_passes(self):
        """The 2026-10-25 publisher-freeze class: a gap closing is not an error."""
        a = market_analysis()
        result = self.run_verify([fixture('1', a, 0), fixture('4', None, None)],
                                   [org_row('1', 'market', dict(a), 0),
                                    org_row('4', None, None, None)],
                                   probs={'1': a['probabilities']})
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['checks']['featured']['blank'], ['4'])
        self.assertEqual(result['checks']['complete']['blank'], ['4'])

    def test_form_rung_replays_under_its_published_rd_schedule(self):
        import math
        rd = min(400.0, 150.0 + 300.0 / math.sqrt(10))
        prob1, _ = v.valve_probability(825, 923, rd)
        form = {
            'method': 'model', 'family': 'form',
            'probabilities': [prob1, 1 - prob1],
            'observed_at': '2026-10-26T00:00:00Z',
            'source': 'Own results-based model (bo3.gg series results)',
            'source_url': 'https://bo3.gg/matches/test',
            'inputs': [{'name': 'Alpha', 'points': 825, 'source_url': 'https://bo3.gg/matches/test',
                        'fitted': {'n': 10, 'posterior_sd': 114.7, 'prior_center': 981}},
                       {'name': 'Bravo', 'points': 923,
                        'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'}],
            'rating_sd': 114.7, 'interval': [0.18, 0.65], 'low_confidence': True,
            'samples': [{'date': '2026-10-25', 'opponent': 'X', 'won': False,
                         'source_url': 'https://bo3.gg/matches/x'}],
        }
        result = self.run_verify([fixture('5', None, None)],
                                   [org_row('5', None, dict(form), 1)],
                                   probs={'5': form['probabilities']}, researched_ids=('5',), model_ids=('5',))
        self.assertEqual(result['errors'], [])
        wrong_rd, _ = v.valve_probability(825, 923, 75)
        form['probabilities'] = [round(wrong_rd, 8), round(1 - wrong_rd, 8)]
        result = self.run_verify([fixture('5', None, None)],
                                   [org_row('5', None, dict(form), 1)],
                                   probs={'5': form['probabilities']}, researched_ids=('5',), model_ids=('5',))
        self.assertTrue(any('form probabilities' in e for e in result['errors']))

    def test_summary_requires_unresolved_and_no_line_sections(self):
        a = model_analysis()
        site = site_tree(['2'], {'2': a['probabilities']}, model_ids=())
        result = v.verify(snapshot_of([fixture('2', a, 0)]),
                          origination_of([org_row('2', 'model', dict(a), 0)]), site)
        self.assertTrue(any('no-line register' in e for e in result['errors']))


class ProbeParsersTest(unittest.TestCase):
    def test_hltv_listing_needs_two_teams_and_an_epoch(self):
        html = ('<div class="match-wrapper" data-match-wrapper data-match-id="9" live="false">'
                '<a class="match-teams" href="/matches/9/alpha-vs-bravo-test"></a>'
                '<span class="match-teamname">Alpha</span><span class="match-teamname">Bravo</span>'
                '<div class="match-event" data-event-headline="Test Cup"></div>'
                '<div data-unix="1793083200000"></div></div>'
                '<div class="match-wrapper" data-match-wrapper data-match-id="10">'
                '<span class="match-teamname">Solo</span></div>')
        rows = probe.parse_hltv_listing(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['teams'], ['Alpha', 'Bravo'])
        self.assertTrue(rows[0]['starts_at'].endswith('Z'))

    def test_thunderpick_records_raw_pair_only_for_exact_names(self):
        payload = {'data': {'upcoming': [
            {'id': 5, 'teams': {'home': {'name': 'Alpha'}, 'away': {'name': 'Bravo'}},
             'market': {'name': 'Match Winner',
                        'home': {'odds': 1.61}, 'away': {'odds': 2.18}}},
            {'id': 6, 'teams': {'home': {'name': 'Alpha Academy'}, 'away': {'name': 'Bravo'}},
             'market': {'name': 'Match Winner',
                        'home': {'odds': 3.0}, 'away': {'odds': 1.3}}}]}}
        hits = probe.thunderpick_candidates(payload, ['Alpha', 'Bravo'])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['paired_odds']['odds_home_away'], [1.61, 2.18])

    def test_polymarket_series_view_skips_map_markets(self):
        event = {'id': '42', 'slug': 'cs2-test', 'title': 'Alpha vs Bravo',
                 'markets': [{'question': 'Alpha vs Bravo - Map 1 Winner',
                              'sportsMarketType': 'child_moneyline',
                              'outcomes': '["Alpha","Bravo"]', 'bestBid': 0.5, 'bestAsk': 0.6},
                             {'question': 'Alpha vs Bravo', 'sportsMarketType': 'moneyline',
                              'outcomes': '["Alpha","Bravo"]', 'bestBid': 0.8, 'bestAsk': 0.84,
                              'closed': False}]}
        view = probe.polymarket_series_view(event)
        self.assertEqual(view['best_bid'], 0.8)
        self.assertEqual(view['outcomes'], ['Alpha', 'Bravo'])


class DossierTest(unittest.TestCase):
    def test_dossier_is_internally_consistent_and_replays_while_current(self):
        dossier = json.loads(DOSSIER.read_text())
        for check in ('inventory', 'featured', 'complete', 'cross_layer', 'summary'):
            self.assertIn(check, dossier['checks'])
        self.assertEqual(dossier['errors'], [])
        snapshot = json.loads((ROOT / 'snapshot.json').read_text())
        origination = json.loads((ROOT / 'origination.json').read_text())
        if snapshot.get('generated_at') != dossier['snapshot_generated_at'] \
                or origination.get('generated_at') != dossier['origination_generated_at']:
            self.skipTest('root snapshot rotated after this dated dossier; '
                          'dated specifics stay in the dossier, invariants above still ran')
        result = v.verify(snapshot, origination, ROOT)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['active_fixtures'], dossier['active_fixtures'])

    def test_valve_inputs_all_matched_the_official_file(self):
        valve = json.loads((ROOT / 'data' / 'research' / '3e64f4fb' / 'valve-check.json').read_text())
        self.assertGreaterEqual(len(valve['checks']), 4)
        self.assertTrue(all(c['exact_match'] for c in valve['checks']))

    def test_review_register_entries_have_unique_ids_and_evidence(self):
        register = json.loads((ROOT / 'data' / 'research' / '3e64f4fb' / 'repo-review.json').read_text())
        ids = [item['id'] for item in register['items']]
        self.assertEqual(len(ids), len(set(ids)))
        for item in register['items']:
            self.assertTrue(item['evidence'])
            for link in item['evidence']:
                self.assertTrue(str(link['url']).startswith('https://'))


if __name__ == '__main__':
    unittest.main()
