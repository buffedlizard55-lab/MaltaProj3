"""Dossier integrity checks for session arena-ebd1ed70 (2026-10-24).

Every claim in data/research/ebd1ed70/ must be traceable: each source-ladder entry
carries first-hand source URLs, guided percentages are arithmetically consistent
with the published decimal pairs they cite (no-vig normalisation — never
hand-entered), unpriced fixtures carry NO percentage at all, and flags.json
matches the shape the review page loader expects.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data' / 'research' / 'ebd1ed70'


class Ebd1ed70Research(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ladder = json.loads((BASE / 'source-ladder-2026-10-24.json').read_text())
        cls.flags = json.loads((BASE / 'flags.json').read_text())
        cls.lobby = json.loads((BASE / 'live-lobby-2026-10-24.json').read_text())
        cls.md = (BASE / 'unresolved-guidance-2026-10-24.md').read_text()

    def test_lobby_roster_has_25_pickable_cards_with_links(self):
        self.assertEqual(len(self.lobby['cards']), 25)
        self.assertEqual(self.lobby['counts']['pickable_cards'], 25)
        for card in self.lobby['cards']:
            self.assertTrue(card['hotspawn_match_url'].startswith('https://www.hotspawn.com/matches/'), card)
            self.assertRegex(card['start_utc'], r'^2026-10-\d\dT\d\d:00:00Z$')
            # pick'em popularity is recorded but explicitly never a probability
            self.assertIn('never used as a probability', card['picked_percent_note'])

    def test_nine_gap_entries_cover_the_new_cct_cards(self):
        ids = {e['hotspawn_id'] for e in self.ladder['entries']}
        self.assertEqual(ids, {'1079658', '1079659', '1079660', '1079661',
                               '1081152', '1081153', '1081154', '1081156', '1081158'})
        self.assertEqual(self.ladder['counts']['cards_reviewed'], 9)
        self.assertEqual(self.ladder['counts']['resolvable_from_published_prices'], 4)
        self.assertEqual(self.ladder['counts']['no_compliant_line'], 5)

    def test_every_entry_cites_first_hand_sources(self):
        for e in self.ladder['entries']:
            self.assertTrue(e['hltv']['url'].startswith('https://www.hltv.org/'), e['hltv'])
            self.assertTrue(e['egamersworld']['url'].startswith('https://egamersworld.com/'))
            self.assertTrue(e['bo3_gg']['url'].startswith('https://bo3.gg/'))
            self.assertEqual(e['thunderpick_api']['url'], 'https://thunderpick.io/api/matches')
            self.assertTrue(e['hltv']['read_at'])
            for extra in e['extra_sources']:
                self.assertTrue(extra.startswith('https://'), extra)

    def test_guided_percentages_replay_from_published_pairs(self):
        priced = [e for e in self.ladder['entries'] if e['guided'].get('probability_team_a') is not None]
        self.assertEqual(len(priced), 4)
        for e in priced:
            a, b = e['egamersworld']['odds']
            pa = 100 * (1 / a) / (1 / a + 1 / b)
            pb = 100 - pa
            self.assertAlmostEqual(e['guided']['probability_team_a'], round(pa, 1), places=0.11)
            self.assertAlmostEqual(e['guided']['probability_team_b'], round(pb, 1), places=0.11)
            self.assertEqual(sorted([e['guided']['probability_team_a'],
                                     e['guided']['probability_team_b']]), sorted([round(pa, 1), round(pb, 1)]))
            self.assertIn('no-vig', e['guided']['basis'])

    def test_unpriced_entries_have_no_hand_written_percentage(self):
        unpriced = [e for e in self.ladder['entries'] if e['guided'].get('probability') is None
                    and e['guided'].get('probability_team_a') is None]
        self.assertEqual(len(unpriced), 5)
        for e in unpriced:
            self.assertEqual(e['guided']['probability'], None)
            self.assertTrue(e['guided']['direction'], e['hotspawn_id'])
            self.assertIn('none is written by hand', e['guided']['basis'])
            # the money rungs must all be empty/rejected for these five
            self.assertIsNone(e['bo3_gg']['odds'])
            self.assertEqual(e['egamersworld']['odds'], [1.8, 1.8])

    def test_placeholder_pairs_are_flagged_rejected(self):
        for e in self.ladder['entries']:
            if e['egamersworld']['odds'] == [1.8, 1.8]:
                self.assertRegex(e['egamersworld']['note'], r'placeholder|unnamed')

    def test_flags_match_review_loader_shape_and_cover_irregularities(self):
        ids = [f['id'] for f in self.flags]
        self.assertEqual(ids, ['ebd1ed70-lobby-nine-new-cct-cards',
                               'ebd1ed70-spirit-academy-lfo10-egw-identity-failure',
                               'ebd1ed70-lfo10-duplicate-valve-rows',
                               'ebd1ed70-thunderpick-guest-board-empty',
                               'ebd1ed70-polymarket-opponent-name-mismatch-1081156'])
        for f in self.flags:
            self.assertIn(f['severity'], {'notice', 'warning', 'critical'})
            self.assertTrue(f['title'] and f['detail'])
            self.assertTrue(f['source_urls'], f['id'])
            for u in f['source_urls']:
                self.assertTrue(u.startswith('https://'), u)
        identity = self.flags[1]
        self.assertEqual(identity['match_ids'], ['1081156'])
        self.assertEqual(self.flags[4]['match_ids'], ['1081156'])

    def test_markdown_dossier_states_the_limitations(self):
        for heading in ('## Why these nine', '## Method (per fixture)',
                        '## A. Resolvable from published prices (4)',
                        '## B. No compliant line anywhere checked (5)',
                        '### Limitations of generating picks for these five (plain words)',
                        '## Irregularities flagged for review'):
            self.assertIn(heading, self.md)
        # every fixture id appears in the readable dossier
        for fid in ('1079658', '1079659', '1079660', '1079661',
                    '1081152', '1081153', '1081154', '1081156', '1081158'):
            self.assertIn(fid, self.md)
        self.assertIn('never used as probabilities', self.md)
        self.assertIn('## Cross-check with concurrent session arena-73bc57bd', self.md)

    def test_cross_check_fields_cite_73bc57bd(self):
        for e in self.ladder['entries']:
            self.assertIn('cross_check', e, e['hotspawn_id'])
            self.assertIn('73bc57bd', e['cross_check'])
        self.assertEqual(self.ladder['counts']['cross_checked_by_73bc57bd'], 9)


if __name__ == '__main__':
    unittest.main()
