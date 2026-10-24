"""Read-only gap research and wall-clock regression coverage; synthetic fixtures."""
from __future__ import annotations

import copy
import importlib
import io
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from scripts import be019782_audit as audit, root_publish

START = '2026-10-25T09:00:00Z'


def fixture(method=None):
    return {'id': 'test-fixture', 'teams': [{'name': 'Synthetic A'}, {'name': 'Synthetic B'}],
            'competition': 'Synthetic Cup', 'starts_at': START, 'availability': 'open',
            'source_url': 'https://play.hotspawn.com/lobby',
            'origination': {'method': method, 'label': method} if method else None,
            'research': [{'stage': 'HLTV identity', 'source_url': 'https://www.hltv.org/matches/1/test'}]}


def relay(**changes):
    row = {'id': 1, 'slug': 'synthetic-a-vs-synthetic-b', 'status': 'upcoming',
           'start_date': START, 'team1': {'name': 'Synthetic A'}, 'team2': {'name': 'Synthetic B'}}
    row.update(changes)
    return row


def quote():
    return {'provider': 'Synthetic bookmaker', 'book_url': 'https://thunderpick.io/',
            'two_sided_price': True,
            'sides': {'team_1': {'name': 'Synthetic A', 'active': True, 'coeff': 1.5},
                      'team_2': {'name': 'Synthetic B', 'active': True, 'coeff': 2.5}}}


class OnlyResearchTheGaps(unittest.TestCase):
    def test_money_backed_rows_are_not_researched_again(self):
        for method in ('market', 'bookmaker', 'consensus', 'reference'):
            with self.subTest(method=method):
                self.assertEqual(audit.targets({'matches': [fixture(method)]}), [])

    def test_unresolved_and_model_rows_are_researched(self):
        for method in (None, 'model', 'guidance', 'form', 'network'):
            with self.subTest(method=method):
                selected = audit.targets({'matches': [fixture(method)]})
                self.assertEqual(len(selected), 1)
                self.assertEqual(selected[0]['hltv_url'], 'https://www.hltv.org/matches/1/test')
                self.assertNotIn('probabilities', selected[0])
                self.assertNotIn('pick_index', selected[0])

    def test_past_rows_are_not_offered_as_new_picks(self):
        match = fixture('model')
        match['availability'] = 'past'
        self.assertEqual(audit.targets({'matches': [match]}), [])

    def test_selection_is_read_only(self):
        payload = {'matches': [fixture('model')]}
        before = copy.deepcopy(payload)
        audit.targets(payload)
        self.assertEqual(payload, before)


class RelayLeadSafety(unittest.TestCase):
    def setUp(self):
        self.target = audit.targets({'matches': [fixture()]})[0]

    def test_exact_names_and_start_bind_in_either_order(self):
        row = relay(team1={'name': 'Synthetic B'}, team2={'name': 'Synthetic A'})
        bound, _ = audit.unique_relay(self.target, [row])
        self.assertEqual(bound, row)

    def test_next_meeting_and_one_shared_team_do_not_bind(self):
        for row in (relay(start_date='2026-10-26T09:00:00Z'),
                    relay(team2={'name': 'Synthetic C'}), relay(start_date=None)):
            with self.subTest(row=row):
                self.assertIsNone(audit.unique_relay(self.target, [row])[0])

    def test_live_or_unknown_status_cannot_be_a_prematch_lead(self):
        for status in ('live', 'finished', None, ''):
            with self.subTest(status=status):
                self.assertIsNone(audit.unique_relay(self.target, [relay(status=status)])[0])

    def test_two_distinct_exact_fixtures_are_ambiguous(self):
        self.assertIsNone(audit.unique_relay(self.target, [relay(), relay(id=2)])[0])

    def test_repeated_identical_record_is_not_a_second_fixture(self):
        row = relay()
        self.assertEqual(audit.unique_relay(self.target, [row, copy.deepcopy(row)])[0], row)

    def test_conflicting_same_identity_cannot_pick_the_last_record(self):
        self.assertIsNone(audit.unique_relay(self.target, [relay(), relay(extra='changed')])[0])

    def test_only_active_finite_two_sided_coefficients_are_leads(self):
        for value in (None, True, 0, 1, float('nan'), float('inf'), '1.5'):
            with self.subTest(value=value):
                q = quote()
                q['sides']['team_1']['coeff'] = value
                with patch.object(audit.research, 'relay_block', return_value=q):
                    self.assertIsNone(audit.paired_relay(relay()))
        q = quote()
        q['sides']['team_2']['active'] = False
        with patch.object(audit.research, 'relay_block', return_value=q):
            self.assertIsNone(audit.paired_relay(relay()))

    def test_price_outcomes_must_be_the_joined_teams(self):
        q = quote()
        q['sides']['team_2']['name'] = 'Different team'
        with patch.object(audit.research, 'relay_block', return_value=q):
            self.assertIsNone(audit.paired_relay(relay()))

    def test_valid_relay_is_copied_without_probability(self):
        q = quote()
        with patch.object(audit.research, 'relay_block', return_value=q):
            lead = audit.paired_relay(relay())
        self.assertEqual(lead['team_1']['coeff'], 1.5)
        self.assertNotIn('probabilities', lead)
        self.assertNotIn('pick_index', lead)


class PublisherTestsSurviveTime(unittest.TestCase):
    def test_layout_and_monotonic_tests_survive_a_distant_wall_clock(self):
        # Reproduce the actual production outage without changing production
        # freshness policy: these fixture tests must supply their own clock.
        module = importlib.import_module('tests.test_ca7e10e5_snapshot')
        names = ('test_snapshot_json_is_published', 'test_the_replay_fixture_is_still_never_published',
                 'test_an_older_build_is_still_refused', 'test_the_age_limit_still_rejects_a_stale_snapshot')
        class DistantClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2037, 1, 1, tzinfo=timezone.utc)
        result = unittest.TestResult()
        with patch.object(root_publish, 'datetime', DistantClock):
            unittest.TestSuite(module.RootPublisherCarriesTheSnapshot(name) for name in names).run(result)
        self.assertEqual(result.testsRun, 4)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])


if __name__ == '__main__':
    unittest.main()
