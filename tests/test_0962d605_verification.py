"""Session arena-0962d605 — the gap dossier and the phone-first register hold up.

Two kinds of assertion live here:

* the dossier's own numbers are reproducible and sourced (bid/ask recompute to
  the published spread, every observation carries an https source and a UTC
  timestamp, and no probability is attributed to the board that the board does
  not publish);
* the rendered executive summary gives every fixture the featured line could not
  price a card with its pick, both probabilities, the method badge, the recorded
  blocker, the stages tried and a source link, and reconciles the board's count
  with the published snapshot's count instead of leaving two different numbers
  unexplained.

The mutation cases at the bottom prove the checks fail closed: a hand-edited
spread or an invented probability is reported, not rendered.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import build
from scripts import __dict__ as _scripts_dict  # noqa: F401  (keeps the package import explicit)
import importlib

verify_mod = importlib.import_module('scripts.0962d605_verify')

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data/research/0962d605/gap-research.json'


class DossierIsReproducible(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = json.loads(DOSSIER.read_text(encoding='utf-8'))

    def test_every_observation_is_sourced_and_recomputes(self):
        self.assertEqual(verify_mod.check_dossier(self.dossier), [])

    def test_published_estimates_match_the_board(self):
        snapshot = json.loads(verify_mod.SNAPSHOT.read_text(encoding='utf-8'))
        origination = json.loads(verify_mod.ORIGINATION.read_text(encoding='utf-8'))
        self.assertEqual(verify_mod.check_published_estimates(self.dossier, snapshot, origination), [])

    def test_aliases_are_registered_and_scoped(self):
        aliases = json.loads(verify_mod.ALIASES.read_text(encoding='utf-8'))
        self.assertEqual(verify_mod.check_aliases(self.dossier, aliases), [])

    def test_the_two_gap_fixtures_are_named(self):
        self.assertEqual([f['id'] for f in self.dossier['fixtures']], ['1081156', '1082792'])

    def test_no_observation_is_presented_as_a_pick(self):
        # The dossier records quotes and ranks; it must never carry a pick or a
        # probability that is not already published by the board.
        for fixture in self.dossier['fixtures']:
            self.assertNotIn('pick_index', fixture)
            self.assertNotIn('probabilities', fixture)
            self.assertNotIn('probabilities', fixture.get('hltv') or {})

    def test_a_hand_edited_spread_is_rejected(self):
        broken = copy.deepcopy(self.dossier)
        broken['fixtures'][1]['lines'][0]['spread'] = 0.15
        errors = verify_mod.check_dossier(broken)
        self.assertTrue(any('published spread' in err for err in errors), errors)

    def test_an_invented_board_probability_is_rejected(self):
        broken = copy.deepcopy(self.dossier)
        broken['fixtures'][1]['published_estimate']['probabilities'] = [0.5, 0.5]
        snapshot = json.loads(verify_mod.SNAPSHOT.read_text(encoding='utf-8'))
        origination = json.loads(verify_mod.ORIGINATION.read_text(encoding='utf-8'))
        # Simulate a board that does carry the row the dossier names: the
        # comparison must then fail on the invented pair.
        board = copy.deepcopy(origination)
        board['matches'].append({'id': '1082792', 'featured_method': None,
                                 'origination': {'method': 'model', 'probabilities': [0.9818, 0.0182]}})
        errors = verify_mod.check_published_estimates(broken, snapshot, board)
        self.assertTrue(any('published board' in err for err in errors), errors)

    def test_a_crossed_book_is_rejected(self):
        broken = copy.deepcopy(self.dossier)
        broken['fixtures'][0]['lines'][0]['bid'] = 0.99
        broken['fixtures'][0]['lines'][0]['ask'] = 0.40
        broken['fixtures'][0]['lines'][0]['spread'] = 0.0
        errors = verify_mod.check_dossier(broken)
        self.assertTrue(any('crossed book' in err for err in errors), errors)


class ExecutiveSummaryRegister(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix='0962d605-site-')
        cls.out = Path(cls._tmp.name)
        build.build(ROOT / 'data', cls.out)
        cls.index = (cls.out / 'index.html').read_text(encoding='utf-8')
        cls.origination = json.loads((ROOT / 'data/origination.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_register_and_cards_render(self):
        self.assertEqual(verify_mod.check_site(self.out, self.origination), [])

    def test_every_researched_row_gets_a_card(self):
        fallback = [m for m in self.origination['matches']
                    if m.get('origination') is not None and m.get('featured_method') is None]
        self.assertTrue(fallback, 'fixture data has no researched rows to check')
        for match in fallback:
            self.assertIn(f'id="researched-{match["id"]}"', self.index)

    def test_cards_show_both_probabilities_and_not_one(self):
        fallback = [m for m in self.origination['matches']
                    if m.get('origination') is not None and m.get('featured_method') is None
                    and len(((m.get('origination') or {}).get('probabilities') or [])) == 2
                    and m.get('pick_index') in (0, 1)]
        self.assertTrue(fallback)
        for match in fallback:
            probs = match['origination']['probabilities']
            for value in probs:
                self.assertIn(f'{value * 100:.1f}%', self.index, match['id'])

    def test_build_audits_are_clean(self):
        self.assertEqual(verify_mod.check_audits(self.out), [])


if __name__ == '__main__':
    unittest.main()
