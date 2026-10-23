"""Session arena-3a010437: the dated lobby-gap register must stay dated.

Published defect (2026-10-23 09:23Z build): the executive summary rendered the
2026-10-23T04:58Z inventory research record in the present tense — *"These cards
are on Hotspawn right now"* — and listed two fixtures (`1081872`, `1081149`)
that the record itself had already seen **inside a published snapshot**
(`in_published_snapshot: true`). By 09:23Z those cards had left the inventory, so
the page was claiming a live gap that no longer existed and could no longer be
picked (a started match has no prematch pick).

The rules pinned here:

* a fixture the record saw in a published snapshot is never a current gap;
* a fixture with no Hotspawn id is matched to a published row by the exact two
  team names (and the competition when both are known) before it is called
  missing — this is not an alias join;
* every rendered row still carries its own Hotspawn/HLTV link and no `%`;
* the copy names the observation time and says the card may have started since.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from scripts.build import live_coverage_gaps, live_coverage_missing

OBSERVED = '2026-10-23T04:58:00Z'


def match(i, a, b, competition='CCT Test'):
    return {
        'id': str(i), 'competition': competition, 'starts_at': '2099-01-01T10:00:00Z',
        'locks_at': '2099-01-01T09:54:00Z', 'availability': 'open',
        'source_url': f'https://www.hotspawn.com/matches/x-{i}',
        'teams': [{'name': a}, {'name': b}],
        'analysis': {'method': 'market', 'source_url': 'https://polymarket.com/event/x',
                     'probabilities': [0.62, 0.38]},
        'pick_index': 0,
    }


def record(*fixtures):
    return {'observed_at': OBSERVED, 'live_fixtures': list(fixtures)}


class DatedGapRegister(unittest.TestCase):
    def test_a_card_already_seen_in_a_published_snapshot_is_not_a_gap(self):
        data = {'matches': [], '_live_coverage': record(
            {'id': '1081872', 'teams': ['NEXVOID', 'Rare Atom'],
             'competition': 'VOID Autumn Cup 2026', 'in_published_snapshot': True,
             'hotspawn_url': 'https://www.hotspawn.com/matches/nexvoid-vs-rare-atom-void-autumn-cup-2026-1081872'},
            {'id': '1081149', 'teams': ['FORZE Reload', 'LFO 10'],
             'competition': 'CCT Europe 2026 Series #12', 'in_published_snapshot': True,
             'hotspawn_url': 'https://www.hotspawn.com/matches/forze-reload-vs-lfo-10-cct-europe-2026-series-12-1081149'},
        )}
        _, missing = live_coverage_missing(data)
        self.assertEqual(missing, [])
        html = live_coverage_gaps(data, '')
        self.assertNotIn('1081872', html)
        self.assertNotIn('1081149', html)
        self.assertIn('already published in this snapshot', html)

    def test_an_id_less_card_is_matched_by_its_two_team_names(self):
        data = {'matches': [match(1081606, 'JiJieHao', 'Eternal Fire', 'DraculaN Season 7')],
                '_live_coverage': record(
                    {'id': None, 'teams': ['JiJieHao', 'Eternal Fire'],
                     'competition': 'DraculaN Season 7'})}
        _, missing = live_coverage_missing(data)
        self.assertEqual(missing, [])

    def test_an_id_less_card_with_different_competition_stays_a_gap(self):
        data = {'matches': [match(1081606, 'JiJieHao', 'Eternal Fire', 'DraculaN Season 7')],
                '_live_coverage': record(
                    {'id': None, 'teams': ['JiJieHao', 'Eternal Fire'],
                     'competition': 'Some Other Cup'})}
        _, missing = live_coverage_missing(data)
        self.assertEqual(len(missing), 1)

    def test_a_genuinely_missing_card_is_named_with_links_and_no_percent(self):
        data = {'matches': [match(1, 'A', 'B')], '_live_coverage': record(
            {'id': '1081605', 'teams': ['Phantom Academy', 'Banda chuya'],
             'competition': 'CCT Europe 2026 Challengers #8',
             'hotspawn_url': 'https://www.hotspawn.com/matches/phantom-academy-vs-banda-chuya-cct-europe-2026-challengers-8-1081605',
             'hltv_url': 'https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8'},
            {'id': '1', 'teams': ['A', 'B'], 'competition': 'CCT Test'})}
        html = live_coverage_gaps(data, '')
        self.assertIn('1081605', html)
        self.assertIn('https://www.hltv.org/matches/2399699/', html)
        self.assertNotIn('A vs B', html)
        self.assertNotIn('%', html.split('id="live-coverage-gaps"')[1])

    def test_the_copy_names_the_observation_time_and_the_started_case(self):
        data = {'matches': [], '_live_coverage': record(
            {'id': '999', 'teams': ['X', 'Y'], 'competition': 'Cup',
             'hotspawn_url': 'https://www.hotspawn.com/matches/x-999'})}
        html = live_coverage_gaps(data, '')
        observed = datetime(2026, 10, 23, 4, 58, tzinfo=timezone.utc)
        self.assertIn('at ', html)
        self.assertIn(str(observed.year), html)
        self.assertNotIn('right now', html.casefold())
        self.assertIn('no prematch pick exists', html)
        self.assertIn('not</strong> a claim that the card is on the lobby now', html)


if __name__ == '__main__':
    unittest.main()
