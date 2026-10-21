"""Unit tests for session 541cd43a's own-line network model.

These tests use a synthetic results graph only: no network, no live evidence,
no bookmaker price. They pin the properties the published rung relies on —
deterministic fit, fail-closed gates, and a replay that re-derives the
probability from the quote's own published inputs.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from scripts import network_model

UTC = timezone.utc
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


def _day(offset: int) -> str:
    return (NOW - timedelta(days=offset)).date().isoformat()


def _graph() -> tuple[list[dict], list[dict]]:
    """Twelve anchored teams plus two unrated teams linked through them."""
    anchors = [{'team': f'A{i}', 'points': 2200 - i * 100,
                'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'} for i in range(12)]
    edges, ident = [], 1000
    names = {}
    for i in range(12):
        names[i] = f'A{i}'
    names[90], names[91] = 'Unrated One', 'Unrated Two'
    # 330 filler series among anchored teams: deterministic, all won by the
    # higher-rated side, which the fit must reproduce.
    for repeat in range(5):
        for i in range(12):
            for j in range(i + 1, 12):
                ident += 1
                edges.append({'id': ident, 'date': _day(10 + repeat), 'a': i, 'b': j, 'winner': i,
                              'a_name': names[i], 'b_name': names[j], 'parsed': 'done',
                              'url': f'https://bo3.gg/matches/synthetic-{ident}'})
    for k in range(10):
        ident += 1
        edges.append({'id': ident, 'date': _day(5), 'a': 0, 'b': 90, 'winner': 0,
                      'a_name': names[0], 'b_name': names[90], 'parsed': 'done',
                      'url': f'https://bo3.gg/matches/synthetic-{ident}'})
        ident += 1
        edges.append({'id': ident, 'date': _day(5), 'a': 1, 'b': 91, 'winner': 1,
                      'a_name': names[1], 'b_name': names[91], 'parsed': 'done',
                      'url': f'https://bo3.gg/matches/synthetic-{ident}'})
        ident += 1
        edges.append({'id': ident, 'date': _day(4), 'a': 90, 'b': 91, 'winner': 90,
                      'a_name': names[90], 'b_name': names[91], 'parsed': 'done',
                      'url': f'https://bo3.gg/matches/synthetic-{ident}'})
    return edges, anchors


def _fixture() -> tuple[dict, dict]:
    match = {'teams': [{'name': 'Unrated One'}, {'name': 'Unrated Two'}],
             'starts_at': (NOW + timedelta(hours=3)).isoformat()}
    binding = {'sides': [{'name': 'Unrated One', 'team_id': 90},
                         {'name': 'Unrated Two', 'team_id': 91}],
               'source_url': 'https://bo3.gg/matches/synthetic-fixture'}
    return match, binding


class NetworkModelTest(unittest.TestCase):
    def setUp(self):
        edges, anchors = _graph()
        self.document = network_model.build(edges, anchors, NOW)

    def test_fit_places_unrated_teams_on_the_official_scale(self):
        ratings = self.document['ratings']
        one, two = ratings['90'], ratings['91']
        self.assertGreater(one['points'], two['points'])
        # The anchored neighbours sit at 2200 and 2100, so both fitted ratings
        # must stay in a plausible band rather than running to infinity.
        self.assertLess(one['points'], 2600)
        self.assertGreater(two['points'], 300)
        self.assertFalse(one['anchored'])
        self.assertTrue(ratings['0']['anchored'])

    def test_fit_is_deterministic(self):
        edges, anchors = _graph()
        again = network_model.build(edges, anchors, NOW)
        self.assertEqual(again['ratings'], self.document['ratings'])
        self.assertEqual(again['evidence_sha256'], self.document['evidence_sha256'])

    def test_quote_publishes_inputs_and_replays(self):
        match, binding = _fixture()
        quote, reason = network_model.estimate_fixture(match, binding, self.document, NOW)
        self.assertIsNotNone(quote, reason)
        self.assertEqual(quote['method'], 'model')
        self.assertEqual(quote['family'], 'network')
        self.assertEqual(len(quote['inputs']), 2)
        self.assertGreater(quote['probabilities'][0], 0.5)
        self.assertAlmostEqual(sum(quote['probabilities']), 1.0, places=9)
        self.assertTrue(quote['evidence_sha256'])
        network_model.replay_check(quote, self.document)

    def test_replay_rejects_tampered_evidence(self):
        match, binding = _fixture()
        quote, _ = network_model.estimate_fixture(match, binding, self.document, NOW)
        tampered = json.loads(json.dumps(self.document))
        tampered['ratings']['90']['points'] += 25
        with self.assertRaises(AssertionError):
            network_model.replay_check(quote, tampered)

    def test_replay_rejects_changed_probability(self):
        match, binding = _fixture()
        quote, _ = network_model.estimate_fixture(match, binding, self.document, NOW)
        quote['probabilities'] = [quote['probabilities'][0] + 0.01, quote['probabilities'][1] - 0.01]
        with self.assertRaises(AssertionError):
            network_model.replay_check(quote, self.document)

    def test_thin_graph_fails_closed(self):
        small = network_model.build(_graph()[0][:40], _graph()[1], NOW)
        match, binding = _fixture()
        quote, reason = network_model.estimate_fixture(match, binding, small, NOW)
        self.assertIsNone(quote)
        self.assertIn('finished series', reason)

    def test_missing_anchor_fails_closed(self):
        document = network_model.build(_graph()[0], [], NOW)
        match, binding = _fixture()
        quote, reason = network_model.estimate_fixture(match, binding, document, NOW)
        self.assertIsNone(quote)
        self.assertIn('official rating table', reason)

    def test_missing_binding_fails_closed(self):
        match, _ = _fixture()
        quote, reason = network_model.estimate_fixture(match, None, self.document, NOW)
        self.assertIsNone(quote)
        self.assertIn('bo3.gg identity', reason)

    def test_unknown_team_fails_closed(self):
        match = {'teams': [{'name': 'Unrated One'}, {'name': 'Never Played'}],
                 'starts_at': (NOW + timedelta(hours=3)).isoformat()}
        binding = {'sides': [{'name': 'Unrated One', 'team_id': 90},
                             {'name': 'Never Played', 'team_id': 777}]}
        quote, reason = network_model.estimate_fixture(match, binding, self.document, NOW)
        self.assertIsNone(quote)
        self.assertIn('no rating', reason)

    def test_ambiguous_name_is_not_anchored(self):
        edges, anchors = _graph()
        teams = {1: 'Twin', 2: 'Twin', 3: 'Unique'}
        found, notes = network_model.anchor_rows(teams, anchors)
        self.assertNotIn(1, found)
        self.assertNotIn(2, found)
        self.assertNotIn(3, found)  # not in the official table at all
        duplicate_rows = [{'team': 'Unique', 'points': 1500, 'source_url': 'https://x'},
                          {'team': 'Unique', 'points': 1600, 'source_url': 'https://y'}]
        found, notes = network_model.anchor_rows(teams, duplicate_rows)
        self.assertNotIn(3, found)

    def test_window_and_winner_rules(self):
        old = {'id': 1, 'date': _day(200), 'a': 1, 'b': 2, 'winner': 1,
               'a_name': 'A', 'b_name': 'B', 'parsed': 'done'}
        no_winner = {'id': 2, 'date': _day(3), 'a': 1, 'b': 2, 'winner': None,
                     'a_name': 'A', 'b_name': 'B', 'parsed': 'done'}
        unparsed = {'id': 3, 'date': _day(3), 'a': 1, 'b': 2, 'winner': 1,
                    'a_name': 'A', 'b_name': 'B', 'parsed': 'waiting'}
        kept = network_model.usable_edges([old, no_winner, unparsed], NOW)
        self.assertEqual([edge['id'] for edge in kept], [3])


if __name__ == '__main__':
    unittest.main()
