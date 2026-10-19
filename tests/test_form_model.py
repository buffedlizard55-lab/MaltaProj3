"""The lowest rung may only speak from observed series and must fail closed."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts import form_model, originate

UTC = timezone.utc
NOW = datetime(2026, 10, 19, 5, 0, tzinfo=UTC)


def sample(opponent, points=1200, won=True, days=5, parsed='done'):
    return {'date': (NOW - timedelta(days=days)).date().isoformat(), 'opponent': opponent,
            'opponent_points': points, 'won': won, 'bo': 3, 'parsed': parsed,
            'source_url': 'https://bo3.gg/matches/' + opponent.lower().replace(' ', '-')}


def ratings(*rows):
    return [{'name': name, 'points': points, 'standing': i + 1, 'snapshot_date': '2026-10-05',
             'roster': [f'p{i}{j}' for j in range(5)],
             'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md'}
            for i, (name, points) in enumerate(rows)]


class FitTests(unittest.TestCase):
    def test_an_undefeated_sample_rates_above_its_anchors(self):
        fitted = form_model.fit([sample(f'team{i}', 1200) for i in range(10)])
        self.assertTrue(fitted['ok'])
        self.assertGreater(fitted['points'], 1200)
        self.assertGreater(fitted['posterior_sd'], 0)

    def test_a_losing_sample_rates_below_its_anchors(self):
        fitted = form_model.fit([sample(f'team{i}', 1200, won=False) for i in range(10)])
        self.assertLess(fitted['points'], 1200)

    def test_the_prior_keeps_a_single_game_from_running_to_the_grid_edge(self):
        fitted = form_model.fit([sample('sole', 1200, won=True)])
        self.assertLess(fitted['points'], 1900)
        self.assertGreater(fitted['points'], 1200)

    def test_samples_without_an_anchor_are_ignored(self):
        self.assertFalse(form_model.fit([{'opponent_points': None, 'won': True}])['ok'])

    def test_usable_drops_stale_unparsed_and_unanchored_series(self):
        rows = [sample('ok'), sample('old', days=400), sample('pending', parsed='waiting'),
                {'date': '2026-10-01', 'opponent': 'none', 'won': True, 'parsed': 'done'}]
        kept = form_model.usable(rows, NOW)
        self.assertEqual([r['opponent'] for r in kept], ['ok'])

    def test_probability_moves_the_right_way(self):
        self.assertGreater(form_model.win_probability(1500, 1200, 75), 0.5)
        self.assertLess(form_model.win_probability(1000, 1200, 75), 0.5)


class FixtureTests(unittest.TestCase):
    def match(self):
        return {'id': '1', 'competition': 'VOID Autumn Cup 2026',
                'teams': [{'name': 'Rated One'}, {'name': 'Unrated Two'}]}

    def binding(self, n=10):
        opponents = ['Rated One', 'Rated Two', 'Rated Three']
        return {'source_url': 'https://bo3.gg/matches/unrated-two-vs-rated-one-20-10-2026',
                'observed_at': '2026-10-19T04:00:00Z',
                'results': {'unratedtwo': [sample(opponents[i % 3], 1100 + 40 * (i % 3), won=i % 2 == 0)
                                           for i in range(n)]}}

    def test_a_team_with_no_official_row_gets_a_labelled_quote(self):
        quote, reason = form_model.estimate_fixture(self.match(), self.binding(),
                                                    ratings(('Rated One', 1100), ('Rated Two', 1140),
                                                            ('Rated Three', 1180)),
                                                    {'aliases': []}, NOW)
        self.assertEqual(reason, '')
        self.assertEqual(quote['family'], 'form')
        self.assertEqual(quote['provider'], 'Own results-based model (bo3.gg series results)')
        self.assertAlmostEqual(sum(quote['probabilities']), 1.0, places=6)
        self.assertEqual(len(quote['inputs']), 2)
        self.assertTrue(quote['samples'])
        self.assertIn('low_confidence', quote)

    def test_too_few_series_stays_unresolved_with_a_reason(self):
        quote, reason = form_model.estimate_fixture(self.match(), self.binding(n=3),
                                                    ratings(('Rated One', 1100), ('Rated Two', 1140),
                                                            ('Rated Three', 1180)),
                                                    {'aliases': []}, NOW)
        self.assertIsNone(quote)
        self.assertIn('needs 8', reason)

    def test_a_missing_history_stays_unresolved(self):
        quote, reason = form_model.estimate_fixture(self.match(), self.binding(n=0), ratings(('Rated One', 1100)),
                                                    {'aliases': []}, NOW)
        self.assertIsNone(quote)
        self.assertIn('no finished', reason)

    def test_no_binding_is_reported_not_guessed(self):
        quote, reason = form_model.estimate_fixture(self.match(), None, ratings(('Rated One', 1100)),
                                                    {'aliases': []}, NOW)
        self.assertIsNone(quote)
        self.assertIn('No bo3.gg fixture binding', reason)

    def test_an_unrated_opponent_leaves_no_anchor(self):
        binding = {'source_url': 'https://bo3.gg/matches/x', 'observed_at': '2026-10-19T04:00:00Z',
                   'results': {'unratedtwo': [sample('nobody rated', 0, won=i % 2 == 0) for i in range(10)]}}
        quote, reason = form_model.estimate_fixture(self.match(), binding, ratings(('Rated One', 1100)),
                                                    {'aliases': []}, NOW)
        self.assertIsNone(quote)
        self.assertIn('anchored series', reason)


class IdentityRuleTests(unittest.TestCase):
    def test_one_complete_row_wins_over_an_incomplete_remnant(self):
        rows = ratings(('6666', 923))
        rows.append({'name': '6666', 'points': 425, 'standing': 368, 'snapshot_date': '2026-10-05',
                     'roster': ['a', 'b', 'c'], 'source_url': 'https://example.invalid'})
        self.assertEqual(originate.rating_row('6666', rows, {'aliases': []}, None)['points'], 923)

    def test_two_complete_rows_stay_ambiguous(self):
        rows = ratings(('Chinggis Warriors', 1084))
        rows.append({'name': 'Chinggis Warriors', 'points': 685, 'standing': 220,
                     'snapshot_date': '2026-10-05', 'roster': ['x', 'y', 'z', 'w', 'v'],
                     'source_url': 'https://example.invalid'})
        self.assertIsNone(originate.rating_row('Chinggis Warriors', rows, {'aliases': []}, None))

    def test_a_scoped_alias_is_honoured_only_in_its_competition(self):
        registry = {'aliases': [{'alias': 'Aurora Young Blud', 'canonical': 'Aurora YB',
                                 'applies_to': ['Stake Ranked Episode 6: Closed Qualifier'],
                                 'evidence': []}]}
        rows = ratings(('Aurora Young Blud', 526))
        self.assertIsNotNone(originate.rating_row('Aurora YB', rows, registry,
                                                  'Stake Ranked Episode 6: Closed Qualifier'))
        self.assertIsNone(originate.rating_row('Aurora YB', rows, registry, 'Another Cup'))


class LadderTests(unittest.TestCase):
    def test_a_form_quote_becomes_the_published_pick_only_without_money_or_valve(self):
        match = {'id': '1', 'competition': 'Cup', 'starts_at': '2026-10-20T12:00:00Z',
                 'teams': [{'name': 'A', 'id': '1'}, {'name': 'B', 'id': '2'}],
                 'source_url': 'https://play.hotspawn.com/lobby'}
        form = {'provider': 'Own results-based model (bo3.gg series results)', 'family': 'form',
                'probabilities': [0.7, 0.3],
                'inputs': [{'name': 'A', 'points': 1300, 'source': 'x', 'source_url': 'https://bo3.gg/matches/x'},
                           {'name': 'B', 'points': 1100, 'source': 'x', 'source_url': 'https://bo3.gg/matches/x'}],
                'rating_sd': 40.0, 'interval': [0.62, 0.77], 'n_series': 12, 'low_confidence': False,
                'samples': [], 'source_url': 'https://bo3.gg/matches/x', 'observed_at': '2026-10-19T04:00:00Z'}
        result = originate.originate_match(dict(match, _form=form), [], [], None, None, {'aliases': []}, NOW)
        self.assertIsNotNone(result['origination'])
        self.assertEqual(result['origination']['label'], 'Own results-based estimate (bo3.gg series results)')
        self.assertEqual(result['pick_index'], 0)
        self.assertTrue(any('results model' in note.lower() for note in result['limitations']))
        stages = [r['stage'] for r in result['research']]
        self.assertIn('Results model (own, bo3.gg series results)', stages)


if __name__ == '__main__':
    unittest.main()
