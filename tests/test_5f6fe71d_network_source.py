"""Session arena-5f6fe71d, board task 5F-1 — network-quote provenance links.

Residual of the 11B-4 finding: the own-network rung published
``https://bo3.gg/matches`` (the index) as its quote-level ``source_url`` even
when the identity binding held a specific official bo3.gg record — the bound
fixture page (bridge ``start_time_and_team_name``) or the bound team page
(bridge ``exact_team_name_lookup``). The executive-summary chip and the
origination card therefore linked a less specific page than the evidence.

These tests pin the repaired behaviour with a synthetic results graph only:
no network, no live evidence, no bookmaker price. The probability arithmetic,
gates and replay contract are pinned by ``tests/test_network_model.py`` and
``tests/test_network_replay.py``; nothing here changes a rating, a probability
or a pick.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from scripts import network_model

UTC = timezone.utc
NOW = datetime(2026, 10, 22, 0, 0, tzinfo=UTC)
INDEX_URL = 'https://bo3.gg/matches'


def _day(offset: int) -> str:
    return (NOW - timedelta(days=offset)).date().isoformat()


def _graph() -> tuple[list[dict], list[dict]]:
    """Twelve anchored teams plus two unrated teams linked through them."""
    anchors = [{'team': f'A{i}', 'points': 2200 - i * 100,
                'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'}
               for i in range(12)]
    edges, ident = [], 1000
    names = {i: f'A{i}' for i in range(12)}
    names[90], names[91] = 'Unrated One', 'Unrated Two'
    for repeat in range(5):
        for i in range(12):
            for j in range(i + 1, 12):
                ident += 1
                edges.append({'id': ident, 'date': _day(10 + repeat), 'a': i, 'b': j, 'winner': i,
                              'a_name': names[i], 'b_name': names[j], 'parsed': 'done',
                              'url': f'https://bo3.gg/matches/synthetic-{ident}'})
    for _k in range(10):
        for a, b, winner in ((0, 90, 0), (1, 91, 1), (90, 91, 90)):
            ident += 1
            edges.append({'id': ident, 'date': _day(5), 'a': a, 'b': b, 'winner': winner,
                          'a_name': names[a], 'b_name': names[b], 'parsed': 'done',
                          'url': f'https://bo3.gg/matches/synthetic-{ident}'})
    return edges, anchors


def _fixture() -> dict:
    return {'teams': [{'name': 'Unrated One'}, {'name': 'Unrated Two'}],
            'starts_at': (NOW + timedelta(hours=3)).isoformat()}


def _binding(**extra) -> dict:
    return dict({'sides': [{'name': 'Unrated One', 'team_id': 90},
                           {'name': 'Unrated Two', 'team_id': 91}]}, **extra)


class NetworkQuoteSourceTest(unittest.TestCase):
    def setUp(self):
        edges, anchors = _graph()
        self.document = network_model.build(edges, anchors, NOW)

    def _quote(self, binding):
        quote, reason = network_model.estimate_fixture(_fixture(), binding, self.document, NOW)
        self.assertIsNotNone(quote, reason)
        return quote

    def test_bound_fixture_record_is_published_as_the_quote_source(self):
        quote = self._quote(_binding(bridge='start_time_and_team_name',
                                     source_url='https://bo3.gg/matches/unrated-one-vs-unrated-two-22-10-2026'))
        self.assertEqual(quote['source_url'],
                         'https://bo3.gg/matches/unrated-one-vs-unrated-two-22-10-2026')
        # The repair is provenance-only: the replay contract still passes and
        # the per-team input links are unchanged.
        network_model.replay_check(quote, self.document)
        self.assertEqual([r['source_url'] for r in quote['inputs']],
                         ['https://bo3.gg/teams/90', 'https://bo3.gg/teams/91'])

    def test_bound_team_lookup_page_is_published_as_the_quote_source(self):
        quote = self._quote(_binding(bridge='exact_team_name_lookup',
                                     source_url='https://bo3.gg/teams/90'))
        self.assertEqual(quote['source_url'], 'https://bo3.gg/teams/90')
        network_model.replay_check(quote, self.document)

    def test_missing_binding_source_falls_back_to_the_index(self):
        quote = self._quote(_binding(bridge='exact_team_name_lookup'))
        self.assertEqual(quote['source_url'], INDEX_URL)
        network_model.replay_check(quote, self.document)

    def test_non_bo3gg_binding_source_never_leaks_into_the_quote(self):
        quote = self._quote(_binding(bridge='start_time_and_team_name',
                                     source_url='https://www.hotspawn.com/matches/some-page'))
        self.assertEqual(quote['source_url'], INDEX_URL)

    def test_probability_and_interval_are_untouched_by_the_repair(self):
        with_record = self._quote(_binding(source_url='https://bo3.gg/matches/synthetic-fixture'))
        without = self._quote(_binding())
        self.assertEqual(with_record['probabilities'], without['probabilities'])
        self.assertEqual(with_record['interval'], without['interval'])
        self.assertEqual(with_record['rating_sd_diff'], without['rating_sd_diff'])
        self.assertEqual(with_record['evidence_sha256'], without['evidence_sha256'])


if __name__ == '__main__':
    unittest.main()
