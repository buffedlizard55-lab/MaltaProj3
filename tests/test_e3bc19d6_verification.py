"""Pin session e3bc19d6's coverage dossier and its verifier.

The dossier records a live read of Hotspawn's own fixture endpoint, HLTV identity
for every fixture that was added after the published snapshot, the official Valve
rating rows behind each pricing verdict, and a replay of every published
probability. These tests pin the properties that make it usable for review:

* every published probability re-derives from the evidence the row carries;
* a hand-edited published value, a crossed book or an out-of-range price fails;
* a Valve row that differs from the committed official file fails;
* a transcribed fixture that differs from the collector's own evidence fails;
* the coverage join stays exactly the open inventory, once each;
* no community vote value is ever carried as an input.
"""
from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

from scripts import e3bc19d6_verify as v

SESSION = Path(__file__).resolve().parents[1] / 'data' / 'research' / 'e3bc19d6'


class DossierVerifies(unittest.TestCase):
    def test_the_whole_dossier_passes(self):
        errors, report = v.verify()
        self.assertEqual(errors, [])
        self.assertTrue(report['ok'])
        self.assertEqual(len(report['replay']), 10)
        self.assertTrue(all(row['delta'] <= v.TOLERANCE for row in report['replay']))

    def test_every_replay_row_is_an_open_fixture_of_the_published_build(self):
        rows = json.loads((SESSION / 'replay.json').read_text())['rows']
        ids = {row['fixture_id'] for row in rows}
        self.assertEqual(len(ids), 10, 'the published build carried ten active fixtures')
        for row in rows:
            self.assertIn(row['method'], {'market', 'bookmaker', 'model'})
            self.assertEqual(len(row['published_probabilities']), 2)
            self.assertAlmostEqual(sum(row['published_probabilities']), 1.0, places=6)


class ReplayArithmetic(unittest.TestCase):
    def _row(self, **overrides):
        row = {
            'fixture_id': 'test', 'method': 'market',
            'evidence': {'bid': [0.18, 0.78], 'ask': [0.22, 0.82],
                         'midpoint': [0.2, 0.8], 'rule': 'midpoint'},
            'published_probabilities': [0.2, 0.8],
            'teams': ['A', 'B'], 'pick_index': 1, 'pick': 'B',
        }
        row.update(overrides)
        return row

    def test_midpoint_pair_normalises_to_one(self):
        probabilities, _ = v.replay_row(self._row())
        self.assertAlmostEqual(probabilities[0], 0.2, places=9)
        self.assertAlmostEqual(sum(probabilities), 1.0, places=12)

    def test_a_hand_edited_published_value_is_caught(self):
        probabilities, _ = v.replay_row(self._row())
        published = [0.35, 0.65]
        delta = max(abs(probabilities[0] - published[0]), abs(probabilities[1] - published[1]))
        self.assertGreater(delta, v.TOLERANCE)

    def test_crossed_book_is_rejected(self):
        row = self._row(evidence={'bid': [0.5, 0.6], 'ask': [0.4, 0.9], 'midpoint': [0.45, 0.75]})
        with self.assertRaises(ValueError) as caught:
            v.replay_row(row)
        self.assertIn('crossed', str(caught.exception))

    def test_out_of_range_price_is_rejected(self):
        row = self._row(evidence={'bid': [-0.1, 0.78], 'ask': [0.22, 0.82], 'midpoint': [0.06, 0.8]})
        with self.assertRaises(ValueError):
            v.replay_row(row)

    def test_bookmaker_margin_removal(self):
        row = self._row(method='bookmaker',
                        evidence={'raw_decimal_odds': [1.61, 2.18],
                                  'published_fair_decimal': [1.739, 2.354]},
                        published_probabilities=[0.57519789, 0.42480211])
        probabilities, rule = v.replay_row(row)
        self.assertAlmostEqual(probabilities[0], 0.57519789, places=8)
        self.assertIn('margin', rule)

    def test_decimal_odds_below_one_are_rejected(self):
        row = self._row(method='bookmaker', evidence={'raw_decimal_odds': [0.9, 2.18]})
        with self.assertRaises(ValueError):
            v.replay_row(row)

    def test_valve_logistic_matches_the_published_model(self):
        row = self._row(method='model',
                        evidence={'points': [1110, 1383], 'rd_assumption': v.VALVE_RD},
                        published_probabilities=[0.17816902, 0.82183098])
        probabilities, rule = v.replay_row(row)
        self.assertAlmostEqual(probabilities[0], 0.17816902, places=8)
        self.assertAlmostEqual(probabilities[1] + probabilities[0], 1.0, places=12)
        self.assertIn('fit.js', rule)
        # The g factor is a fixed function of the published RD assumption.
        self.assertAlmostEqual(v.g_factor(75), 0.972820991, places=8)

    def test_equal_points_give_even_probability(self):
        row = self._row(method='model', evidence={'points': [1200, 1200], 'rd_assumption': v.VALVE_RD})
        probabilities, _ = v.replay_row(row)
        self.assertAlmostEqual(probabilities[0], 0.5, places=12)

    def test_unknown_method_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            v.replay_row(self._row(method='vibes'))


class ValveRowIntegrity(unittest.TestCase):
    def _official(self):
        return {'name': 'Rooster', 'points': 718, 'standing': 205,
                'roster': ['ADK', 'chelleos', 'damyo', 'rekonz', 'SkulL'],
                'detail_path': 'details/2026_10_05/0205--rooster--adk-chelleos-damyo-rekonz-skull.md'}

    def _team(self, **overrides):
        team = {'hotspawn_name': 'Rooster', 'valve_name': 'Rooster', 'valve_points': 718,
                'valve_standing': 205, 'roster': ['ADK', 'chelleos', 'damyo', 'rekonz', 'SkulL'],
                'detail_path': ('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/'
                                'live/2026/details/2026_10_05/0205--rooster--adk-chelleos-damyo-rekonz-skull.md'),
                'rows_with_this_name': 1, 'complete_five_player_rows': 1}
        team.update(overrides)
        return team

    def test_a_matching_row_passes(self):
        self.assertEqual(v.compare_valve_team('t', self._team(), [self._official()], '2026-10-05'), [])

    def test_edited_points_fail(self):
        errors = v.compare_valve_team('t', self._team(valve_points=999), [self._official()], '2026-10-05')
        self.assertTrue(any('points' in e for e in errors))

    def test_edited_roster_fails(self):
        errors = v.compare_valve_team('t', self._team(roster=['x'] * 5), [self._official()], '2026-10-05')
        self.assertTrue(any('roster' in e for e in errors))

    def test_wrong_detail_link_fails(self):
        errors = v.compare_valve_team('t', self._team(detail_path='https://example.com/x'),
                                      [self._official()], '2026-10-05')
        self.assertTrue(any('detail' in e for e in errors))

    def test_two_complete_rows_stay_unpriceable(self):
        team = self._team(valve_name=None, valve_points=None, valve_standing=None, roster=None, detail_path=None)
        errors = v.compare_valve_team('t', team, [self._official(), self._official()], '2026-10-05')
        self.assertEqual(errors, [], 'an ambiguous name recorded as unpriceable is the fail-closed outcome')

    def test_a_complete_row_recorded_as_unpriceable_fails(self):
        team = self._team(valve_name=None, valve_points=None, valve_standing=None, roster=None, detail_path=None)
        errors = v.compare_valve_team('t', team, [self._official()], '2026-10-05')
        self.assertTrue(any('unpriceable' in e for e in errors))

    def test_blank_name_with_points_fails(self):
        team = self._team(valve_name=None, detail_path=None, roster=None)
        errors = v.compare_valve_team('t', team, [], '2026-10-05')
        self.assertTrue(any('carries points' in e for e in errors))


class InventoryTranscription(unittest.TestCase):
    def _record(self):
        return {'id': '1082858', 'scheduled_start_time_ms': '1792983600000',
                'teams': [{'name': 'Ground Zero'}, {'name': 'Off Chops'}]}

    def test_matching_evidence_passes(self):
        source = {'participants0_name': 'Ground Zero', 'participants1_name': 'Off Chops',
                  'scheduled_start_time': '1792983600000'}
        self.assertEqual(v.compare_inventory_record(self._record(), source), [])

    def test_swapped_teams_fail(self):
        source = {'participants0_name': 'Off Chops', 'participants1_name': 'Ground Zero',
                  'scheduled_start_time': '1792983600000'}
        self.assertTrue(v.compare_inventory_record(self._record(), source))

    def test_changed_start_fails(self):
        source = {'participants0_name': 'Ground Zero', 'participants1_name': 'Off Chops',
                  'scheduled_start_time': '1792987200000'}
        errors = v.compare_inventory_record(self._record(), source)
        self.assertTrue(any('start' in e for e in errors))


class CoverageJoin(unittest.TestCase):
    def setUp(self):
        self.inventory = json.loads((SESSION / 'live-inventory.json').read_text())
        self.coverage = json.loads((SESSION / 'coverage.json').read_text())

    def test_every_open_fixture_has_exactly_one_row(self):
        ids = [row['fixture_id'] for row in self.coverage['rows']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(ids), sorted(r['id'] for r in self.inventory['open_records']))

    def test_the_nine_new_fixtures_are_the_ones_absent_from_the_snapshot(self):
        new = sorted(row['fixture_id'] for row in self.coverage['rows'] if not row['in_published_snapshot'])
        self.assertEqual(new, sorted(['1079201', '1081159', '1079202', '1081160', '1079203',
                                      '1093218', '1081162', '1081163', '1081164']))

    def test_no_open_fixture_is_left_without_a_pricing_rung(self):
        self.assertEqual(self.coverage['summary']['with_no_pricing_rung'], [])
        for row in self.coverage['rows']:
            if row['in_published_snapshot']:
                continue
            self.assertTrue(row['valve']['priceable'] or row['hltv'],
                            f'{row["fixture_id"]} has neither a Valve row nor an HLTV identity')
            self.assertTrue(row['resolution_path'])

    def test_every_published_row_replayed(self):
        published = [row for row in self.coverage['rows'] if row['in_published_snapshot']]
        self.assertEqual(len(published), 10)
        for row in published:
            self.assertEqual(row['published']['replay_verdict'], 'pass')
            self.assertTrue(row['published']['source_url'].startswith('https://'))
            self.assertAlmostEqual(sum(row['published']['probabilities']), 1.0, places=6)

    def test_identities_are_unique_https_and_time_matched(self):
        identities = json.loads((SESSION / 'hltv-identities.json').read_text())['rows']
        starts = {r['id']: r['starts_at'] for r in self.inventory['open_records']}
        urls = [row['hltv_url'] for row in identities]
        self.assertEqual(len(urls), len(set(urls)))
        for row in identities:
            self.assertTrue(row['hltv_url'].startswith('https://www.hltv.org/matches/'))
            self.assertEqual(row['hltv_start_utc'], starts[row['fixture_id']])
            self.assertEqual(row['best_of'], 3)


class ReviewFlags(unittest.TestCase):
    def setUp(self):
        self.flags = json.loads((SESSION / 'flags.json').read_text())

    def test_schema_the_site_renders(self):
        seen = set()
        for flag in self.flags:
            for key in ('id', 'severity', 'title', 'detail', 'source_urls'):
                self.assertTrue(flag.get(key), f'{flag.get("id")} lacks {key}')
            self.assertNotIn(flag['id'], seen)
            seen.add(flag['id'])
            self.assertIn(flag['severity'], v.SEVERITIES)
            self.assertTrue(all(u.startswith('https://') for u in flag['source_urls']))

    def test_the_lobby_gap_is_flagged_with_all_nine_ids(self):
        flag = next(f for f in self.flags if f['id'] == 'e3bc19d6-nine-fixtures-added-after-the-published-snapshot')
        self.assertEqual(sorted(flag['match_ids']),
                         sorted(['1079201', '1081159', '1079202', '1081160', '1079203',
                                 '1093218', '1081162', '1081163', '1081164']))


class NoCommunityVoteInputs(unittest.TestCase):
    def test_no_vote_value_is_carried(self):
        self.assertEqual(v.check_no_votes({}), [])

    def test_the_guard_would_catch_a_vote_value(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'x.json'
            path.write_text(json.dumps({'participants0_picked_percent': 76}))
            original = v.SESSION
            try:
                v.SESSION = Path(folder)
                self.assertTrue(v.check_no_votes({}))
            finally:
                v.SESSION = original


if __name__ == '__main__':
    unittest.main()
