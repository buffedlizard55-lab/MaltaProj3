"""Session 719a314a: the live-coverage dossier must replay, not just read well.

The dossier `data/research/719a314a/live-coverage-2026-10-24.json` claims that
nine of the twenty-five upcoming Hotspawn CS2 cards had no published pick at
2026-10-24T06:26Z, and it publishes five no-vig probabilities derived from
two-sided EGamersWorld/Thunderpick quotes. These tests pin the properties that
make those claims checkable:

* every card's UTC start is exactly its lobby label plus the documented +4 h
  lobby-clock offset (the offset itself is proven by the sixteen cards whose
  first-party fixture-API epoch agreed, 16/16);
* every published percentage and pick re-derives from the two stored decimal
  prices — a hand-edited number fails;
* a card with no quote must state a limitation, so a blank can never be silent;
* the flags are published in the review schema with https evidence.
"""
from __future__ import annotations

import json
import unittest
from importlib import import_module
from pathlib import Path

coverage = import_module('scripts.719a314a_live_coverage')

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / 'data/research/719a314a'
RECORD = SESSION / 'live-coverage-2026-10-24.json'
FLAGS = SESSION / 'flags.json'
DOSSIER = SESSION / 'live-coverage-2026-10-24.md'


def load_record() -> dict:
    return json.loads(RECORD.read_text())


class DossierReplays(unittest.TestCase):
    def setUp(self):
        self.record = load_record()

    def test_the_record_replays_with_no_problems(self):
        self.assertEqual(coverage.verify(self.record), [])

    def test_the_command_line_passes(self):
        self.assertEqual(coverage.main(['--record', str(RECORD)]), 0)

    def test_sixteen_cards_are_covered_and_nine_were_missing(self):
        self.assertEqual(self.record['counts']['lobby_upcoming'], 25)
        self.assertEqual(self.record['counts']['in_published_snapshot'], 16)
        self.assertEqual(self.record['counts']['missing_from_published_snapshot'], 9)
        missing = {c['hotspawn_id'] for c in self.record['cards'] if not c['in_published_snapshot']}
        self.assertEqual(missing, {'1079658', '1079659', '1079660', '1079661',
                                   '1081152', '1081153', '1081154', '1081156', '1081158'})

    def test_every_published_probability_re_derives_from_its_two_prices(self):
        checked = 0
        for card in self.record['cards']:
            line = card.get('reference_line')
            if not line:
                continue
            teams = card['teams']
            o1 = line['quoted_decimal_odds'][teams[0]]
            o2 = line['quoted_decimal_odds'][teams[1]]
            p1, p2 = coverage.no_vig(o1, o2)
            self.assertEqual(line['no_vig_probabilities'][teams[0]], p1, card['hotspawn_id'])
            self.assertEqual(line['no_vig_probabilities'][teams[1]], p2, card['hotspawn_id'])
            self.assertEqual(line['pick'], teams[0] if p1 > p2 else teams[1])
            checked += 1
        self.assertEqual(checked, 5, 'five cards carry a two-sided price in this observation')

    def test_the_known_arithmetic_is_exact(self):
        # 1079658 Acend 2.87 / FORZE Reload 1.35 — worked by hand in the dossier.
        self.assertEqual(coverage.no_vig(2.87, 1.35), (32.0, 68.0))
        self.assertEqual(coverage.no_vig(1.49, 2.45), (62.2, 37.8))
        self.assertEqual(coverage.no_vig(1.76, 1.94), (52.4, 47.6))
        self.assertEqual(coverage.no_vig(1.45, 2.51), (63.4, 36.6))

    def test_the_lobby_clock_conversion_is_the_documented_offset(self):
        self.assertEqual(coverage.start_from_label('Oct 24, 04:00'), '2026-10-24T08:00:00Z')
        self.assertEqual(coverage.start_from_label('Oct 31, 09:00'), '2026-10-31T13:00:00Z')
        self.assertEqual(coverage.LOBBY_CLOCK_OFFSET_HOURS, 4)

    def test_a_tampered_percentage_fails_the_replay(self):
        record = load_record()
        card = next(c for c in record['cards'] if c.get('reference_line'))
        teams = card['teams']
        card['reference_line']['no_vig_probabilities'][teams[0]] = 50.0
        problems = coverage.verify(record)
        self.assertTrue(any('!= replayed' in p for p in problems), problems)

    def test_a_silent_blank_fails_the_replay(self):
        record = load_record()
        card = next(c for c in record['cards']
                    if not c['in_published_snapshot'] and not c.get('reference_line'))
        card.pop('limitation', None)
        problems = coverage.verify(record)
        self.assertTrue(any('no stated limitation' in p for p in problems), problems)

    def test_a_participation_percentage_is_rejected_as_a_probability_input(self):
        record = load_record()
        record['cards'][0]['participants0_picked_percent'] = 93
        problems = coverage.verify(record)
        self.assertTrue(any('forbidden probability key' in p for p in problems), problems)


class FlagsArePublishable(unittest.TestCase):
    def setUp(self):
        self.flags = json.loads(FLAGS.read_text())

    def test_every_flag_matches_the_review_schema(self):
        for flag in self.flags:
            for key in ('id', 'severity', 'title', 'detail', 'match_ids', 'source_urls'):
                self.assertIn(key, flag)
            self.assertTrue(flag['detail'].strip())
            self.assertTrue(flag['source_urls'])
            for url in flag['source_urls']:
                self.assertTrue(url.startswith('https://'), url)
            self.assertIn(flag['severity'], {'notice', 'warning', 'error'})

    def test_ids_are_unique_and_session_scoped(self):
        ids = [f['id'] for f in self.flags]
        self.assertEqual(len(ids), len(set(ids)))
        for flag_id in ids:
            self.assertTrue(flag_id.startswith('719a314a-'), flag_id)

    def test_the_gap_flag_names_all_nine_missing_cards(self):
        flag = next(f for f in self.flags if f['id'] == '719a314a-nine-cct-cards-never-collected')
        self.assertEqual(len(flag['match_ids']), 9)
        self.assertEqual(set(flag['match_ids']),
                         {'1079658', '1079659', '1079660', '1079661',
                          '1081152', '1081153', '1081154', '1081156', '1081158'})


class DossierText(unittest.TestCase):
    def test_the_markdown_states_the_gap_and_the_limitation(self):
        text = DOSSIER.read_text()
        for fixture in ('1079658', '1081152', '1081158'):
            self.assertIn(fixture, text)
        for phrase in ('no usable price', 'placeholder', 'never replaced with 50/50'):
            self.assertIn(phrase, text)
        self.assertIn('https://play.hotspawn.com/lobby', text)

    def test_no_card_claims_hotspawn_or_hltv_votes_as_a_probability(self):
        # The record's method note names both exclusions in prose; the cards
        # themselves must not carry either value as a probability input.
        record = load_record()
        for card in record['cards']:
            keys = {str(k).lower() for k in card}
            self.assertEqual({k for k in keys if 'picked_percent' in k or 'vote' in k}, set(),
                             card['hotspawn_id'])
            for value in card.values():
                if isinstance(value, dict):
                    for key in value:
                        self.assertNotIn('vote', str(key).lower())
                        self.assertNotIn('picked_percent', str(key).lower())
        self.assertIn('never inputs', record['method'])


if __name__ == '__main__':
    unittest.main()
