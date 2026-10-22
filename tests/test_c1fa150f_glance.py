"""C1F-1: both teams' probabilities on the phone summary, and a separate register
for picks that have no external betting line behind them.

Every assertion is a rendering contract, not a data claim: the tests build
synthetic fixtures and check what a phone reader is shown. No probability is
invented here, and no source is contacted.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from scripts.build import glance, no_line_register, summary, unresolved_register

BASE = datetime(2026, 10, 22, 1, 0, tzinfo=timezone.utc)


def fixture(i, probability, *, hours=6, method='market', resolved=True, pick=0):
    start = BASE + timedelta(hours=hours)
    match = {
        'id': str(i),
        'teams': [{'id': f'a{i}', 'name': f'Alpha{i}'}, {'id': f'b{i}', 'name': f'Beta{i}'}],
        'competition': 'Test Cup', 'starts_at': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'locks_at': (start - timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'availability': 'open', 'source_url': f'https://www.hotspawn.com/matches/x-{i}',
        'source_api': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2',
        'lobby_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{i}',
        'evidence': 'data/evidence/hotspawn-fixtures.json', 'competition_id': '1',
        'series_format': None, 'lock_offset_sec': 360, 'source_end_at': None,
        'analysis': None, 'pick_index': None, 'observed_at': BASE.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'research': [], 'limitations': [], 'tier': 'c', 'source_status': 'scheduled', 'best_of': None,
    }
    if resolved:
        match['analysis'] = {
            'method': method, 'label': 'Market-implied estimate',
            'probabilities': [probability, 1 - probability],
            'fair_decimal': [round(1 / probability, 3), round(1 / (1 - probability), 3)],
            'observed_at': match['observed_at'],
            'source': 'Polymarket' if method == 'market' else 'Valve official standings',
            'source_url': 'https://polymarket.com/event/cs2-x' if method == 'market'
                          else 'https://github.com/ValveSoftware/counter-strike_regional_standings',
            'quotes': [], 'limitations': [],
            'snapshot_date': '2026-10-05', 'inputs': [],
        }
        match['pick_index'] = pick
    return match


def origination(match, *, method='model', label='Valve-rating research estimate', pick=0, trail=None):
    """The published origination record the site reads for its fallback row."""
    probability = 0.75 if pick == 0 else 0.25
    return {
        'id': match['id'], 'teams': match['teams'], 'competition': match['competition'],
        'starts_at': match['starts_at'], 'locks_at': match['locks_at'], 'availability': 'open',
        'source_url': match['source_url'], 'pick_index': pick,
        'origination': {
            'method': method, 'label': label,
            'probabilities': [probability, 1 - probability],
            'fair_decimal': [round(1 / probability, 3), round(1 / (1 - probability), 3)],
            'observed_at': match['observed_at'],
            'source': 'Valve official standings',
            'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
        },
        'research': trail if trail is not None else [
            {'stage': 'Primary: Polymarket', 'status': 'unresolved',
             'detail': 'Crossed or wider-than-12-cent order book',
             'source_url': 'https://polymarket.com/event/cs2-x'},
            {'stage': 'Research model cross-check (Valve official ratings)', 'status': 'resolved',
             'detail': 'Alias-aware exact-name Valve rating rows; uncalibrated research model.',
             'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'},
        ],
    }


class BothTeamProbabilitiesTests(unittest.TestCase):
    def test_a_pick_row_shows_the_opponents_probability_too(self):
        html = glance({'matches': [fixture(1, 0.677)], 'fallbacks': {}}, '', now=BASE)
        self.assertIn('Alpha1', html)
        self.assertIn('67.7%', html)      # the pick
        self.assertIn('Beta1 32.3%', html)  # the other side of the same market
        self.assertIn('>Pick</span>', html)

    def test_the_basis_of_every_row_is_visible_on_the_row(self):
        market = glance({'matches': [fixture(1, 0.6)], 'fallbacks': {}}, '', now=BASE)
        self.assertIn('>Market line</span>', market)
        model = glance({'matches': [fixture(2, 0.4, method='model')], 'fallbacks': {}}, '', now=BASE)
        self.assertIn('>Model</span>', model)

    def test_a_researched_fallback_keeps_its_own_numbers_and_is_labelled(self):
        match = fixture(3, 0.5, resolved=False)
        fallback = {match['id']: origination(match, pick=1)}
        html = glance({'matches': [match], 'fallbacks': fallback}, '', now=BASE)
        self.assertIn('>Researched</span>', html)
        self.assertIn('Beta3', html)
        self.assertIn('75.0%', html)
        self.assertIn('Alpha3 25.0%', html)
        self.assertNotIn('50.0%', html)

    def test_an_unresolved_row_still_shows_no_probability_at_all(self):
        match = fixture(4, 0.5, resolved=False)
        html = glance({'matches': [match], 'fallbacks': {}}, '', now=BASE)
        self.assertIn('Unresolved', html)
        self.assertNotIn('50.0%', html)
        self.assertNotIn('glance-other', html)

    def test_the_summary_counts_money_lines_and_models_separately(self):
        matches = [fixture(1, 0.6), fixture(2, 0.55, method='model'), fixture(3, 0.5, resolved=False)]
        fallback = {matches[2]['id']: origination(matches[2])}
        html = glance({'matches': matches, 'fallbacks': fallback}, '', now=BASE)
        self.assertIn('<strong>3</strong> with a directional pick', html)
        self.assertIn('<strong>1</strong> from an external betting line', html)
        self.assertIn('<strong>2</strong> from a research model', html)
        self.assertIn('<strong>0</strong> explicitly unresolved', html)


class NoBettingLineRegisterTests(unittest.TestCase):
    def data(self, matches, origs):
        return {'complete_picks': {'matches': origs,
                                   'counts': {'active': len(origs), 'resolved': len(origs),
                                              'with_pick': len(origs), 'market': 0, 'bookmaker': 0,
                                              'consensus': 0, 'reference': 0, 'model': len(origs),
                                              'guidance': 0, 'unresolved': 0},
                                   'generated_at': '2026-10-22T01:00:00Z'},
                'matches': matches,
                'counts': {'upcoming': len(matches), 'model': len(origs), 'unresolved': 0,
                           'market': 0, 'bookmaker': 0, 'reference': 0, 'inventory': len(matches),
                           'archived': 0, 'unknown_schedule': 0, 'picks': len(origs), 'no_edge': 0},
                'generated_at': '2026-10-22T01:00:00Z',
                'inventory_observed_at': '2026-10-22T01:00:00Z',
                'coverage_complete': True, 'flags': []}

    def test_a_model_only_pick_is_published_with_its_blocker_and_sources(self):
        model_match = fixture(5, 0.5, method='model')
        html = no_line_register(self.data([model_match], [origination(model_match)]), '')
        self.assertIn('id="no-line-register"', html)
        self.assertIn('Alpha5', html)
        self.assertIn('Beta5', html)
        self.assertIn('75.0%', html)
        self.assertIn('Beta5 25.0%', html)
        self.assertIn('No betting line', html)
        self.assertIn('Crossed or wider-than-12-cent order book', html)  # the actual blocker
        self.assertIn('https://polymarket.com/event/cs2-x', html)        # the source that failed
        self.assertIn('counter-strike_regional_standings', html)         # the model that produced it
        self.assertIn('origination/#match-5', html)

    def test_a_fixture_priced_from_a_real_market_is_not_in_the_register(self):
        market_match = fixture(6, 0.6)
        html = no_line_register(self.data([market_match], [origination(market_match, method='market')]), '')
        self.assertEqual(html, '')

    def test_an_unresolved_fixture_without_any_origination_is_not_double_counted(self):
        blank = fixture(7, 0.5, resolved=False)
        row = origination(blank)
        row['origination'] = None
        self.assertEqual(no_line_register(self.data([blank], [row]), ''), '')

    def test_the_register_sits_inside_the_executive_summary_next_to_the_unresolved_register(self):
        model_match = fixture(8, 0.5, method='model')
        origs = [origination(model_match)]
        data = self.data([model_match], origs)
        register = unresolved_register(data, '')
        self.assertIn('id="unresolved-register"', register)
        self.assertIn('id="no-line-register"', register)
        self.assertLess(register.index('id="no-line-register"'), register.index('id="source-probe"')
                        if 'id="source-probe"' in register else len(register))
        page = summary(data, '', now=BASE)
        self.assertIn('id="picks-at-a-glance"', page)
        self.assertIn('id="no-line-register"', page)

    def test_the_stated_reason_is_the_failed_money_source_not_a_checked_identity(self):
        # A "checked" HLTV stage is a limitation, but it does not explain a missing
        # price. The register must quote the failed market stage instead.
        match = fixture(10, 0.5, method='model')
        trail = [
            {'stage': 'HLTV research', 'status': 'checked',
             'detail': 'Exact teams/time confirmed on HLTV; no original bookmaker price verified.',
             'source_url': 'https://www.hltv.org/matches/1/x'},
            {'stage': 'Betting market (Polymarket series winner)', 'status': 'unresolved',
             'detail': 'No alias-verified Polymarket match-winner line found for these teams and start time.',
             'source_url': 'https://polymarket.com/event/cs2-x'},
        ]
        html = no_line_register(self.data([match], [origination(match, trail=trail)]), '')
        self.assertIn('No alias-verified Polymarket match-winner line', html)
        self.assertNotIn('<strong>Why there is no line:</strong> Exact teams/time confirmed', html)

    def test_a_missing_probability_never_becomes_a_number(self):
        match = fixture(9, 0.5, method='model')
        row = origination(match)
        row['origination']['probabilities'] = []
        row['pick_index'] = None
        html = no_line_register(self.data([match], [row]), '')
        self.assertIn('no side', html)
        self.assertNotIn('0.0%', html)


if __name__ == '__main__':
    unittest.main()
