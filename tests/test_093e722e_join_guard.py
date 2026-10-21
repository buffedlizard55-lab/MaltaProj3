"""93E regression guard: a market/bookmaker row may join a Hotspawn fixture
only when BOTH team names (exact, or via a competition-scoped reviewed alias)
AND the start time match. Regression case: Kalshi KXCS2GAME-26OCT211800LNALE
("Los Ninos vs Alianza Lima Esports") vs Hotspawn 1082837 / HLTV 2399865
("Zetta vs LOS NINOS", CCT South America 2026 Series #7, 2026-10-21T22:00Z),
flagged by session arena-32bed9e3. A one-team-plus-time join must never pass.
"""
import unittest
from pathlib import Path

from scripts import originate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = {
    'teams': [{'name': 'Zetta'}, {'name': 'LOS NINOS'}],
    'competition': 'CCT South America 2026 Series #7',
    'starts_at': '2026-10-21T22:00:00Z',
}
START = '2026-10-21T22:00:00Z'


def real_registry():
    return originate.load_registry(ROOT / 'data/origination/aliases.json')


class BothTeamsJoinGuard(unittest.TestCase):
    def test_one_shared_team_different_opponent_rejected(self):
        # Kalshi names with no alias registry at all: only LOS NINOS matches.
        _, _, status = originate.pair_join(
            ['Los Ninos', 'Alianza Lima Esports'], START, FIXTURE, {'aliases': []})
        self.assertEqual(status, 'names')

    def test_unrelated_second_team_rejected_with_real_registry(self):
        _, _, status = originate.pair_join(
            ['LOS NINOS', 'Damajuana'], START, FIXTURE, real_registry())
        self.assertEqual(status, 'names')

    def test_both_exact_names_and_time_match(self):
        _, _, status = originate.pair_join(
            ['Zetta', 'LOS NINOS'], START, FIXTURE, real_registry())
        self.assertEqual(status, 'matched')

    def test_both_names_but_wrong_start_rejected(self):
        _, _, status = originate.pair_join(
            ['Zetta', 'LOS NINOS'], '2026-10-21T23:30:00Z', FIXTURE, real_registry())
        self.assertEqual(status, 'time')

    def test_alias_join_is_competition_scoped(self):
        # The reviewed Alianza Lima Esports -> Zetta alias (5/5 identical roster
        # on HLTV 2399865 and bo3.gg) applies only inside its declared event.
        _, used, status = originate.pair_join(
            ['Los Ninos', 'Alianza Lima Esports'], START, FIXTURE, real_registry())
        self.assertEqual(status, 'matched')
        self.assertTrue(any(u['canonical'] == 'Zetta' for u in used))
        other = dict(FIXTURE, competition='Some Other Event 2026')
        _, _, status = originate.pair_join(
            ['Los Ninos', 'Alianza Lima Esports'], START, other, real_registry())
        self.assertEqual(status, 'names')

    def test_duplicate_or_single_name_rows_rejected(self):
        for names in (['Zetta'], ['Zetta', 'Zetta'], ['', 'LOS NINOS']):
            _, _, status = originate.pair_join(names, START, FIXTURE, real_registry())
            self.assertEqual(status, 'names', names)


if __name__ == '__main__':
    unittest.main()
