"""Session arena-17d77cb3 — the dated line-source probe and its summary contract.

The brief asks for a pick or a sourced probability for every Hotspawn CS2
fixture, and for the fixtures that cannot be resolved a *separate* section that
states the limitations. This session adds the runner probe that researches
those fixtures (HLTV first, then esportsbooks and esports betting lines) in
``scripts/17d77cb3_research.py``.

These tests pin the rules the probe must never break:

* the join onto a bookmaker relay is exact on BOTH team names plus a start
  window, and a near miss is recorded as a near miss;
* a two-sided price needs two *active* sides above 1.00 — a suspended or
  blocked book is not a price;
* the record copies bookmaker coefficients verbatim and carries no probability
  of its own;
* the record is stamped with the environment it actually ran in, because
  ``scripts.build.load_no_line_research`` promotes only runner sweeps, and it
  writes the sibling Markdown record that block requires;
* the public Hotspawn match URL the record links to follows Hotspawn's own
  observed slug form.
"""
from __future__ import annotations

import importlib
import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts.build import load_no_line_research

# A module name starting with a digit cannot be imported with `import`, so the
# session probe (scripts/17d77cb3_research.py) is loaded by path-name like the
# earlier session probes.
probe = importlib.import_module('scripts.17d77cb3_research')

UTC = timezone.utc


class ProbeJoinTests(unittest.TestCase):
    def row(self, **overrides):
        row = {'slug': 'a-vs-b-23-10-2026', 'start_date': '2026-10-23T13:00:00.000+00:00',
               'team1': {'name': 'Isurus'}, 'team2': {'name': 'Hacha'},
               'bet_updates': {'provider': 'thunderpick', 'path': 'https://thunderpick.io/match/1',
                               'team_1': {'name': 'Isurus', 'coeff': 1.10, 'active': True, 'team_id': 1},
                               'team_2': {'name': 'Hacha', 'coeff': 5.80, 'active': True, 'team_id': 2}}}
        row.update(overrides)
        return row

    def test_both_names_and_a_60s_start_window_are_required(self):
        start = datetime(2026, 10, 23, 13, 0, tzinfo=UTC)
        bound, near = probe.bind(['Isurus', 'Hacha'], start, [self.row()])
        self.assertIsNotNone(bound)
        self.assertEqual(near, [])
        bound, near = probe.bind(['Isurus', 'Hacha'], start,
                                 [self.row(start_date='2026-10-23T13:01:30.000+00:00')])
        self.assertIsNone(bound)
        self.assertIn('outside the 60s window', near[0]['status'])
        bound, near = probe.bind(['Isurus', 'Other'], start, [self.row()])
        self.assertIsNone(bound)
        self.assertTrue(near and near[0]['status'] == 'one shared side only')

    def test_two_sided_requires_two_active_sides_above_one(self):
        self.assertTrue(probe.relay_block(self.row())['two_sided_price'])
        stale = self.row()
        stale['bet_updates']['team_2']['active'] = False
        self.assertFalse(probe.relay_block(stale)['two_sided_price'])
        short = self.row()
        short['bet_updates']['team_2']['coeff'] = 1.0
        self.assertFalse(probe.relay_block(short)['two_sided_price'])
        self.assertIsNone(probe.relay_block(self.row(bet_updates=None)))

    def test_the_record_carries_no_probability_of_its_own(self):
        quote = probe.relay_block(self.row())
        self.assertEqual(set(quote), {'provider', 'book_url', 'markets_count', 'sides',
                                      'two_sided_price'})
        self.assertNotIn('probability', json.dumps(quote).lower())

    def test_hotspawn_url_matches_the_site_slug_form(self):
        # Observed form: https://www.hotspawn.com/matches/mibr-vs-bc-game-stake-pulse-beat-iii-1079440
        self.assertEqual(
            probe.hotspawn_match_url(['MIBR', 'BC.Game'], 'Stake Pulse Beat III', '1079440'),
            'https://www.hotspawn.com/matches/mibr-vs-bc-game-stake-pulse-beat-iii-1079440')


class ProbeRecordEligibilityTests(unittest.TestCase):
    """The summary block only promotes runner sweeps with a Markdown record."""

    def test_environment_is_reported_honestly(self):
        with mock.patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}):
            self.assertEqual(probe.environment_name(), 'github-actions-runner')
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(probe.environment_name(), 'local checkout')

    def test_a_probe_document_is_promoted_only_when_it_is_a_runner_record(self):
        import tempfile
        probe_record = {
            'observed_at': '2026-10-23T06:30:00Z',
            'environment': 'github-actions-runner',
            'per_fixture': [{'id': '1082926', 'teams': ['Isurus', 'Hacha'],
                             'money_line_lead': True, 'current_method': 'model',
                             'hotspawn_url': 'https://www.hotspawn.com/matches/isurus-vs-hacha-1082926',
                             'bo3_bound_url': 'https://bo3.gg/matches/isurus-gaming-cs-go-vs-hacha-esports-23-10-2026',
                             'bo3_bet': {'provider': 'thunderpick', 'path': 'https://thunderpick.io/match/2870814',
                                         'team_1': {'name': 'Isurus', 'coeff': 1.1},
                                         'team_2': {'name': 'Hacha', 'coeff': 5.8}}}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'research/17d77cb3/line-source-research.json'
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(probe_record))
            target.with_suffix('.md').write_text('# Dated record\n')
            record = load_no_line_research(root)
            self.assertEqual(record['_record_path'], 'research/17d77cb3/line-source-research.json')

            # The same document without the runner stamp must not be promoted.
            local = dict(probe_record, environment='local checkout')
            target.write_text(json.dumps(local))
            self.assertIsNone(load_no_line_research(root))

    def test_the_probe_writes_both_files_it_declares(self):
        source = Path('scripts/17d77cb3_research.py').read_text()
        self.assertIn("'line-source-research.json'", source)
        self.assertIn("'line-source-research.md'", source)
        self.assertIn("'environment': environment_name()", source)
        self.assertIn("'per_fixture': [compatible(record) for record in findings]", source)


if __name__ == '__main__':
    unittest.main()
