"""The historical dossier must not veto new prices or weekly inventory rollover."""
import copy
import unittest
from tests import test_b72154e1_guided_picks as guided


class SnapshotEvolutionTest(unittest.TestCase):
    def case(self):
        guided.GuidedPicksTest.setUpClass()
        case = guided.GuidedPicksTest()
        case.snapshot = copy.deepcopy(case.snapshot)
        case.by_id = copy.deepcopy(case.by_id)
        return case

    def test_resolved_historical_gap_is_allowed_on_new_snapshot(self):
        case = self.case()
        case.snapshot['generated_at'] = '2026-10-25T12:00:00Z'
        for fid in ('1082858', '1082792'):
            case.by_id[fid] = {'pick_index': 1, 'teams': [
                {'name': name} for name in case.fixtures[fid]['teams']]}
        case.test_group_a_are_snapshot_unresolved()

    def test_historical_gap_still_asserted_on_named_snapshot(self):
        case = self.case()
        case.snapshot['generated_at'] = case.dossier['published_snapshot']['generated_at']
        for fid in ('1082858', '1082792'):
            case.by_id[fid] = {'pick_index': None, 'teams': [
                {'name': name} for name in case.fixtures[fid]['teams']]}
        case.test_group_a_are_snapshot_unresolved()
        case.by_id['1082858']['pick_index'] = 1
        with self.assertRaises(AssertionError):
            case.test_group_a_are_snapshot_unresolved()

    def test_weekly_inventory_can_retire_every_historical_fixture(self):
        case = self.case()
        case.snapshot['generated_at'] = '2026-11-02T12:00:00Z'
        case.by_id = {}
        case.test_group_a_are_snapshot_unresolved()
        case.test_group_b_are_snapshot_model_picks()
        case.test_group_c_absent_from_snapshot()

    def test_current_bad_probability_still_fails(self):
        case = self.case()
        case.snapshot['generated_at'] = '2026-10-25T12:00:00Z'
        case.by_id = {case.GROUP_B[0]: {'pick_index': 0, 'analysis': {
            'probabilities': [0.8, 0.8], 'observed_at': '2026-10-25T12:00:00Z'}}}
        with self.assertRaises(AssertionError):
            case.test_group_b_are_snapshot_model_picks()
