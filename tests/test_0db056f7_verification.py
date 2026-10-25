"""Session arena-0db056f7 guards (offline, deterministic).

* The 1086696 EGamersWorld capture is hash-consistent, quotes through the
  shipped reference ladder at its own observation time, and replays.
* All five rejected rows stay rejected (placeholder / sentence-less pages
  never produce a quote).
* The gap register covers exactly the six researched fixtures and every
  row carries https evidence or an explicit limitation.
* The b72154e1 Group A test must not pin live pick state against the
  mutable root snapshot again (the freeze of 2026-10-25): its pinned
  branch is guarded by the dossier-named snapshot value.

Nothing here reads live fixture *resolution state* from snapshot.json —
only invariants that hold for any snapshot the publisher writes.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from scripts import reference_odds

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / 'data/research/0db056f7'


def fixture(entry: dict) -> dict:
    return {'id': entry['fixture_id'], 'starts_at': entry['starts_at'],
            'locks_at': entry['starts_at'], 'availability': 'open',
            'competition': entry.get('event') or 'CCT South America 2026 Series #7',
            'tier': 'c',
            'source_url': 'https://www.hotspawn.com/matches/x-' + entry['fixture_id'],
            'lobby_url': 'https://play.hotspawn.com/cs2-pickems',
            'teams': [{'id': '1', 'name': entry['teams'][0]},
                      {'id': '2', 'name': entry['teams'][1]}]}


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((RESEARCH / 'reference-odds.json').read_text(encoding='utf-8'))

    def test_capture_registered_in_ladder(self):
        paths = [str(p) for p in reference_odds.CAPTURE_PATHS]
        self.assertIn('research/0db056f7/reference-odds.json', paths)

    def test_single_entry_quotes_and_replays(self):
        self.assertEqual([e['fixture_id'] for e in self.doc['entries']], ['1086696'])
        entry = self.doc['entries'][0]
        self.assertEqual(reference_odds.problems(entry), [])
        self.assertEqual(entry['excerpt_sha256'],
                         hashlib.sha256(entry['excerpt'].encode()).hexdigest())
        self.assertIn('1.62', entry['excerpt'])
        self.assertIn('2.1', entry['excerpt'])
        now = datetime.fromisoformat(entry['observed_at'].replace('Z', '+00:00')) + timedelta(minutes=5)
        quote, reason = reference_odds.quote(entry, fixture(entry), now)
        self.assertIsNotNone(quote, reason)
        self.assertEqual(quote['probabilities'], [0.43548387, 0.56451613])
        self.assertEqual(quote['method'], 'reference')
        reference_odds.replay(entry, quote)

    def test_rejected_rows_produce_no_quote(self):
        self.assertEqual({e['fixture_id'] for e in self.doc['rejected']},
                         {'1086697', '1082697', '1082792', '1082793', '1082861'})
        for entry in self.doc['rejected']:
            self.assertTrue(entry.get('reason'), entry['fixture_id'])
            self.assertNotIn('odds', entry)
            now = datetime.fromisoformat(entry['observed_at'].replace('Z', '+00:00')) + timedelta(minutes=5)
            quote, _ = reference_odds.quote(entry, fixture(entry), now)
            self.assertIsNone(quote, entry['fixture_id'])


class GapRegisterTests(unittest.TestCase):
    def test_register_covers_six_fixtures_with_limits(self):
        doc = json.loads((RESEARCH / 'gap-research.json').read_text(encoding='utf-8'))
        self.assertEqual({f['fixture_id'] for f in doc['fixtures']},
                         {'1086696', '1082697', '1086697', '1082792', '1082861', '1082793'})
        self.assertEqual(doc['new_fixtures_since_snapshot'], ['1086696', '1082697', '1086697'])
        for row in doc['fixtures']:
            self.assertTrue(row.get('limitations'), row['fixture_id'])
            text = json.dumps(row)
            self.assertIn('https://', text, row['fixture_id'])

    def test_review_register_validates(self):
        from scripts import review_register
        doc = json.loads((RESEARCH / 'repo-review.json').read_text(encoding='utf-8'))
        review_register.validate(doc)  # raises on any malformed item
        self.assertIn('research/0db056f7/repo-review.json', review_register.REGISTERS)


class FreezeRegressionTests(unittest.TestCase):
    def test_group_a_pinned_branch_is_snapshot_guarded(self):
        text = (ROOT / 'tests/test_b72154e1_guided_picks.py').read_text(encoding='utf-8')
        body = text.split('def test_group_a_are_snapshot_unresolved')[1].split('GROUP_B')[0]
        # The pick_index pin may only run for the dossier-named snapshot.
        self.assertIn("self.snapshot.get('generated_at') == named", body)
        pin = body.index('assertIsNone(match.get(\'pick_index\')')
        guard = body.index("self.snapshot.get('generated_at') == named")
        self.assertLess(guard, pin)


if __name__ == '__main__':
    unittest.main()
