"""Session arena-b72154e1: dossier arithmetic + sourcing guards.

Verifies, without network access:
* every no-vig percentage in data/research/b72154e1/coverage-and-guided-picks.json
  recomputes from its stated decimal odds;
* every fixture row carries at least one official/source URL (HLTV, EGW or
  Hotspawn) and an explicit limitations list;
* Group A/B fixture ids exist in the published snapshot with the stated
  pick state (unresolved vs research-model), and Group C ids are absent
  from it (they post-date the snapshot);
* fan-vote / crowd percentages are recorded as excluded, never priced.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data' / 'research' / 'b72154e1' / 'coverage-and-guided-picks.json'
FLAGS = ROOT / 'data' / 'research' / 'b72154e1' / 'flags.json'
SNAPSHOT = ROOT / 'snapshot.json'


def novig_pct(a, b):
    x, y = 1.0 / a, 1.0 / b
    s = x + y
    return round(100 * x / s, 1), round(100 * y / s, 1)


class GuidedPicksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = json.loads(DOSSIER.read_text(encoding='utf-8'))
        cls.flags = json.loads(FLAGS.read_text(encoding='utf-8'))
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        cls.by_id = {str(m['id']): m for m in cls.snapshot['matches']}
        cls.fixtures = {f['id']: f for f in cls.dossier['fixtures']}

    def test_no_vig_arithmetic(self):
        # Ground Zero 3.44 / Off Chops 1.24 -> 26.5 / 73.5
        self.assertEqual(novig_pct(3.44, 1.24), (26.5, 73.5))
        self.assertEqual(self.fixtures['1082858']['guided_pick']['probabilities_pct'],
                         [26.5, 73.5])
        # Acend 2.8 / FORZE Reload 1.35 -> 32.5 / 67.5
        self.assertEqual(novig_pct(2.8, 1.35), (32.5, 67.5))
        self.assertEqual(self.fixtures['1079658']['guided_pick']['probabilities_pct'],
                         [32.5, 67.5])
        # Cached Rooster 2.1 / Abyssal 1.66 -> 44.1 / 55.9 (guidance only)
        self.assertEqual(novig_pct(2.1, 1.66), (44.1, 55.9))
        # Cross-check Fokus 1.23 / ex-6666 3.83 -> 75.7 / 24.3
        self.assertEqual(novig_pct(1.23, 3.83), (75.7, 24.3))

    def test_every_fixture_sourced_and_limited(self):
        for fid, row in self.fixtures.items():
            urls = [row[k].get('url', '') for k in ('hltv', 'esportsbooks')]
            self.assertTrue(any(u.startswith('https://') for u in urls), fid)
            self.assertTrue(row.get('limitations'), fid)

    def test_group_a_are_snapshot_unresolved(self):
        for fid in ('1082858', '1082792'):
            self.assertEqual(self.fixtures[fid]['group'], 'A-unresolved')
            # This historical dossier is not a constraint on future picks.
            # 1082858 acquired a pick on 25 October, legitimately closing a gap.
            if self.snapshot.get('generated_at') == self.dossier['published_snapshot']['generated_at']:
                self.assertIsNone(self.by_id[fid].get('pick_index'), fid)

    GROUP_B = ('1082996', '1079198', '1079200', '1082861', '1082793')

    def test_group_b_are_snapshot_model_picks(self):
        # The dossier names the snapshot it read. Testing pinned fixture ids
        # against `snapshot.json` is a wall-clock trap: the publisher rewrites
        # that file every four hours, and on 2026-10-24 a fresher snapshot had
        # already upgraded 1079198 from the Valve model to a Bovada esportsbook
        # line, so this assertion failed the publisher's regression step
        # (runs 40116915898 and 40120126457) and froze the site — the same
        # failure class as run 40085158851. Pinned expectations therefore only
        # run against the snapshot the dossier names; for any newer snapshot the
        # always-on invariants below are asserted instead.
        named = (self.dossier.get('published_snapshot') or {}).get('generated_at')
        if self.snapshot.get('generated_at') == named:
            for fid in self.GROUP_B:
                match = self.by_id[fid]
                self.assertIsNotNone(match.get('pick_index'), fid)
                self.assertIn('research', (match['analysis']['label'] or '').lower(), fid)
                published = self.fixtures[fid]['published_pick']
                probs = match['analysis']['probabilities']
                self.assertAlmostEqual(published['probabilities'][0], probs[0], places=4, msg=fid)
                self.assertAlmostEqual(published['probabilities'][1], probs[1], places=4, msg=fid)
        # Always on, whatever snapshot is checked in: a Group B fixture that
        # still carries a featured analysis must publish two numbers that add
        # up, stamped in UTC. Whether that analysis is still the Valve model, a
        # money line that replaced it, or absent because the complete-picks
        # layer resolved the row instead, is the ladder's business -- not a
        # regression. Pinning any of those states to a mutable root snapshot is
        # what froze the publisher.
        for fid in self.GROUP_B:
            match = self.by_id.get(fid)
            if match is None:
                continue
            analysis = match.get('analysis')
            if not analysis:
                continue
            probs = analysis.get('probabilities') or []
            self.assertEqual(len(probs), 2, fid)
            self.assertAlmostEqual(sum(probs), 1.0, places=4, msg=fid)
            # An exactly even row legitimately publishes both sides with no
            # pick (1079200 became 50.0/50.0 from a two-sided Polymarket book on
            # 2026-10-24); anything else must name a side.
            if abs(probs[0] - probs[1]) > 1e-9:
                self.assertIsNotNone(match.get('pick_index'), fid)
            self.assertEqual(str(analysis.get('observed_at') or '')[-1:], 'Z', fid)
        # Weekly Hotspawn inventory eventually retires all these historical IDs.
        # Assert the dossier itself remains intact, not that old fixtures live forever.
        for fid in self.GROUP_B:
            self.assertEqual(self.fixtures[fid]['group'], 'B-model-only')

    def test_group_c_absent_from_snapshot(self):
        # Absence is asserted against the snapshot the dossier names
        # (published_snapshot.generated_at). A newer root-synced snapshot is
        # expected to contain these ids — that is the coverage gap closing,
        # not a regression (unguarded, it failed the publisher on 2026-10-24,
        # run 40085158851). Integration guard added by arena-f1277d3b.
        if self.snapshot.get('generated_at') == self.dossier['published_snapshot']['generated_at']:
            awaiting = self.dossier['group_c_awaiting_collect']['ids']
            for fid in awaiting + ['1079658']:
                self.assertNotIn(fid, self.by_id, fid)
        lobby = self.dossier['live_lobby']
        self.assertEqual(len(lobby['open_ids']), 25)
        self.assertEqual(len(lobby['in_lobby_not_in_snapshot']), 9)

    def test_flags_well_formed(self):
        ids = [f['id'] for f in self.flags]
        self.assertEqual(len(ids), len(set(ids)))
        for flag in self.flags:
            self.assertIn(flag['severity'], ('notice', 'warning', 'critical'))
            self.assertTrue(flag['source_urls'], flag['id'])
            self.assertTrue(all(u.startswith('https://') for u in flag['source_urls']))

    def test_crowd_and_fan_votes_excluded(self):
        text = DOSSIER.read_text(encoding='utf-8').lower()
        self.assertIn('never probabilities', text)
        self.assertIn('excluded', text)


if __name__ == '__main__':
    unittest.main()
