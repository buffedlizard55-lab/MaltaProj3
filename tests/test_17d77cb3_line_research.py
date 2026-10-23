"""Session arena-17d77cb3 — dated line research, and the summary block that renders it.

The brief asks for a pick or a sourced probability for every Hotspawn CS2
fixture, and for a *separate* section that states the limitations of the
fixtures that cannot be resolved, included in the executive summary. These
tests pin the parts this session added:

* the research probe's join is still exact (both names) plus a start window, and
  a two-sided quote needs two active sides above 1.00 — a blocked or suspended
  book is not a price;
* the probe never writes a probability: its records carry bookmaker
  coefficients verbatim and nothing else;
* the executive summary's dated-research block is fed by the *newest* sweep and
  describes that sweep's own sources and statuses, with links to its own
  evidence file — an older hardcoded description can no longer be published
  over newer research.
"""
from __future__ import annotations

import importlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build import load_no_line_research, no_line_research_block

# A module name starting with a digit cannot be imported with `import`, so the
# session probe (scripts/17d77cb3_research.py) is loaded by path-name like the
# earlier session probes.
probe = importlib.import_module('scripts.17d77cb3_research')
bind, hotspawn_match_url, relay_block = probe.bind, probe.hotspawn_match_url, probe.relay_block

UTC = timezone.utc


def sweep(observed_at: str, *, hltv_status=403, fixtures=None, path_marker=None) -> dict:
    return {
        'observed_at': observed_at,
        'sources_tried': [
            {'label': 'HLTV match listing', 'url': 'https://www.hltv.org/matches',
             'http_status': hltv_status, 'note': 'blocked' if hltv_status != 200 else 'page reachable'},
            {'label': 'Thunderpick CS2', 'url': 'https://thunderpick.io/esports/counter-strike',
             'http_status': 200, 'note': 'page reachable; no fixture price read'},
            {'label': 'GG.BET CS2', 'url': 'https://gg.bet/en/counter-strike',
             'http_status': 403, 'note': 'blocked'},
        ],
        'per_fixture': fixtures if fixtures is not None else [
            {'id': '1081146', 'teams': ['A', 'B'], 'money_line_lead': False,
             'hotspawn_url': 'https://www.hotspawn.com/matches/a-vs-b-1081146'},
        ],
    }


class NewestSweepWinsTests(unittest.TestCase):
    def test_the_newer_record_is_the_one_published(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'research/17d77cb3').mkdir(parents=True)
            (root / 'research/3016b0c6').mkdir(parents=True)
            (root / 'research/17d77cb3/line-source-research.json').write_text(
                json.dumps(sweep('2026-10-23T05:40:00Z')))
            (root / 'research/3016b0c6/line-source-research.json').write_text(
                json.dumps(sweep('2026-10-22T07:39:00Z')))
            record = load_no_line_research(root)
            self.assertEqual(record['observed_at'], '2026-10-23T05:40:00Z')
            self.assertEqual(record['_path'], 'research/17d77cb3/line-source-research.json')
            html = no_line_research_block({'_no_line_research': record}, '')
            self.assertIn('data/research/17d77cb3/line-source-research.json', html)
            self.assertNotIn('data/research/3016b0c6/line-source-research.json', html)

    def test_the_older_record_still_wins_when_it_is_newer(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'research/17d77cb3').mkdir(parents=True)
            (root / 'research/3016b0c6').mkdir(parents=True)
            (root / 'research/17d77cb3/line-source-research.json').write_text(
                json.dumps(sweep('2026-10-21T05:40:00Z')))
            (root / 'research/3016b0c6/line-source-research.json').write_text(
                json.dumps(sweep('2026-10-22T07:39:00Z')))
            record = load_no_line_research(root)
            self.assertEqual(record['_path'], 'research/3016b0c6/line-source-research.json')

    def test_an_unparseable_or_empty_record_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'research/17d77cb3/line-source-research.json'
            path.parent.mkdir(parents=True)
            path.write_text('{not json')
            self.assertIsNone(load_no_line_research(root))
            path.write_text(json.dumps({'observed_at': '2026-10-23T05:40:00Z', 'per_fixture': []}))
            self.assertIsNone(load_no_line_research(root))

    def test_no_records_means_no_block(self):
        with TemporaryDirectory() as tmp:
            self.assertIsNone(load_no_line_research(Path(tmp)))
        self.assertEqual(no_line_research_block({}, ''), '')


class RecordDescriptionTests(unittest.TestCase):
    def test_the_block_describes_the_sweep_it_renders(self):
        html = no_line_research_block({'_no_line_research': sweep('2026-10-23T05:40:00Z')}, '')
        self.assertIn('id="no-line-research"', html)
        self.assertIn('HTTP 403', html)
        self.assertIn('Thunderpick CS2', html)
        self.assertIn('GG.BET CS2', html)
        self.assertNotIn('Cloudflare 403', html)
        self.assertIn('model picks and limitations stand', html)

    def test_a_reachable_hltv_page_is_not_described_as_a_403(self):
        html = no_line_research_block(
            {'_no_line_research': sweep('2026-10-23T05:40:00Z', hltv_status=200)}, '')
        self.assertIn('identity/ranking only; it publishes no two-sided price', html)
        self.assertNotIn('HTTP 200', html)
        self.assertNotIn('Cloudflare 403', html)

    def test_a_lead_is_rendered_as_a_lead_with_its_own_links(self):
        fixtures = [{'id': '1081146', 'teams': ['6yuBoJlbl', 'ex-6666'], 'money_line_lead': True,
                     'hotspawn_url': 'https://www.hotspawn.com/matches/x-1081146',
                     'bo3_bound_url': 'https://bo3.gg/matches/x-22-10-2026',
                     'bo3_bet': {'provider': 'thunderpick', 'path': 'https://thunderpick.io/match/1',
                                 'team_1': {'name': '6yuBoJlbl', 'coeff': 1.72},
                                 'team_2': {'name': 'ex-6666', 'coeff': 2.0}}}]
        html = no_line_research_block(
            {'_no_line_research': sweep('2026-10-23T05:40:00Z', fixtures=fixtures)}, '')
        self.assertIn('1</strong> new money-line lead', html)
        self.assertIn('first-party ladder must replay it on a later refresh', html)
        self.assertIn('https://thunderpick.io/match/1', html)
        self.assertIn('https://bo3.gg/matches/x-22-10-2026', html)


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
        bound, near = bind(['Isurus', 'Hacha'], start, [self.row()])
        self.assertIsNotNone(bound)
        self.assertEqual(near, [])
        # 90 seconds late is a near miss, not a join.
        bound, near = bind(['Isurus', 'Hacha'], start,
                           [self.row(start_date='2026-10-23T13:01:30.000+00:00')])
        self.assertIsNone(bound)
        self.assertIn('outside the 60s window', near[0]['status'])
        # One shared side is never a join.
        bound, near = bind(['Isurus', 'Other'], start, [self.row()])
        self.assertIsNone(bound)
        self.assertTrue(near and near[0]['status'] == 'one shared side only')

    def test_two_sided_requires_two_active_sides_above_one(self):
        quote = relay_block(self.row())
        self.assertTrue(quote['two_sided_price'])
        stale = self.row()
        stale['bet_updates']['team_2']['active'] = False
        self.assertFalse(relay_block(stale)['two_sided_price'])
        short = self.row()
        short['bet_updates']['team_2']['coeff'] = 1.0
        self.assertFalse(relay_block(short)['two_sided_price'])
        self.assertIsNone(relay_block(self.row(bet_updates=None)))

    def test_the_record_carries_no_probability_of_its_own(self):
        quote = relay_block(self.row())
        self.assertEqual(set(quote), {'provider', 'book_url', 'markets_count', 'sides',
                                      'two_sided_price'})
        self.assertNotIn('probability', json.dumps(quote).lower())

    def test_hotspawn_url_matches_the_site_slug_form(self):
        # Observed form: https://www.hotspawn.com/matches/mibr-vs-bc-game-stake-pulse-beat-iii-1079440
        self.assertEqual(
            hotspawn_match_url(['MIBR', 'BC.Game'], 'Stake Pulse Beat III', '1079440'),
            'https://www.hotspawn.com/matches/mibr-vs-bc-game-stake-pulse-beat-iii-1079440')
        self.assertEqual(
            hotspawn_match_url(['Sökerorg', 'MAYBE'], 'CCT Europe 2026 Series 12', '1083000'),
            'https://www.hotspawn.com/matches/s-kerorg-vs-maybe-cct-europe-2026-series-12-1083000')


if __name__ == '__main__':
    unittest.main()
