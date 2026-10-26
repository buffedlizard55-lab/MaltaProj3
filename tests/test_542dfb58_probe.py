"""Session arena-542dfb58 — offline verification of the live gap probe and its published records.

Everything here replays bytes that a GitHub Actions runner archived in the repository
(`data/research/542dfb58/raw/*.gz`), so no test in this file needs network access and every
assertion can be re-checked by hand against the archived response and its SHA-256.

What is pinned:

1. the probe's parsers agree with the first-party captures they were written against
   (HLTV's listing, Smarkets' event board, Thunderpick's Match-Winner market, Pinnacle's
   CS2 board) — a parser that silently stops matching its source fails here, not on the site;
2. the probe never derives a probability: no published record may carry a `probabilities`,
   `win_probability` or `no_vig` field, only prices, margins, statuses and links;
3. the margin policy is the project's own (two decimals > 1, paired margin 0.85-1.35,
   identical prices rejected as a site placeholder);
4. a Hotspawn card with a missing team name can never crash a join;
5. the two dated records the probe writes are consumable by the site's own newest-wins
   loaders, and the rendered blocks keep their "dated observation, not a live claim" wording.
"""
from __future__ import annotations

import gzip
import importlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'data/research/542dfb58'
probe = importlib.import_module('scripts.542dfb58_gap_probe')


def archived(name: str):
    """A response body this probe stored, or None when the run did not reach that surface.

    A surface stored before the JSON-body fix carries a `.html` name and a JSON payload,
    so the suffix never decides the type — the first character does.
    """
    for candidate in (name + '.json.gz', name + '.html.gz'):
        path = RECORD / 'raw' / candidate
        if path.exists():
            text = gzip.decompress(path.read_bytes()).decode('utf-8', 'replace').lstrip()
            if text[:1] in '[{':
                try:
                    return json.loads(text)
                except ValueError:
                    return text
            return text
    return None


def fixture(fixture_id: str, left: str, right: str, starts_at: str) -> dict:
    return {'id': fixture_id, 'teams': [{'name': left}, {'name': right}], 'starts_at': starts_at}


class ParserReplay(unittest.TestCase):
    """The probe's readers against the bytes the runner actually received."""

    @classmethod
    def setUpClass(cls):
        cls.hltv = archived('hltv-matches')
        cls.smarkets = archived('smarkets-events')
        cls.thunderpick = archived('thunderpick-matches')
        cls.pinnacle = archived('pinnacle-matchups')

    def test_hltv_listing_finds_the_lobby_fixtures(self):
        if not self.hltv:
            self.skipTest('no archived HLTV listing in this checkout')
        rows = probe.hltv_listing(self.hltv)
        self.assertGreaterEqual(len(rows), 20, 'HLTV listing regressed to almost nothing')
        for row in rows:
            self.assertRegex(row['url'], r'^https://www\.hltv\.org/matches/\d+/[a-z0-9-]+$')
            self.assertEqual(len(row['names']), 2)
            self.assertTrue(row['start'], 'every HLTV card the probe accepts carries a start time')

    def test_smarkets_board_binds_by_exact_names_and_start(self):
        if not self.smarkets:
            self.skipTest('no archived Smarkets board in this checkout')
        target = [fixture('1082858', 'Ground Zero', 'Off Chops', '2026-10-26T03:00:00Z')]
        joined = probe.bind(probe.smarkets_rows(self.smarkets), target)
        self.assertTrue(joined, 'the saved Smarkets board publishes this pairing and must bind')
        self.assertEqual(joined[0]['join'], 'exact-names-and-start')
        self.assertTrue(joined[0]['url'].startswith('https://smarkets.com/'))

    def test_thunderpick_prices_are_read_from_the_match_winner_market(self):
        if not self.thunderpick:
            self.skipTest('no archived Thunderpick board in this checkout')
        rows = probe.thunderpick_rows(self.thunderpick)
        priced = [row for row in rows if row.get('prices')]
        self.assertTrue(priced, 'Thunderpick publishes two-decimal Match Winner prices; 0 rows is a parser break')
        flyquest = [row for row in priced
                    if {probe.name_key(n) for n in row['names']} == {'flyquest', 'staqued'}]
        if flyquest:
            # Pinned to the archived response: the book published its own minimum price on
            # one side (1.001). The probe reports the pair and the margin it implies, and
            # leaves the judgement to the ladder — that clip is flag 824A-R02 on the site.
            prices = [float(x) for x in flyquest[0]['prices']]
            self.assertIn(1.001, prices)
            verdict = probe.usable_pair(prices)
            self.assertTrue(verdict['usable'])
            self.assertGreater(verdict['margin'], 1.05, 'the clipped side must not look like a thin margin')
            self.assertNotIn('no_vig', verdict, 'the probe reports prices, never a probability')

    def test_pinnacle_rows_stay_on_the_cs2_board_and_drop_specials(self):
        if not self.pinnacle:
            self.skipTest('no archived Pinnacle board in this checkout')
        rows = probe.pinnacle_rows(self.pinnacle)
        for row in rows:
            self.assertIn('cs2', (row.get('league') or '').lower())
            self.assertNotIn('yes', [probe.name_key(n) for n in row['names']])

    def test_a_fixture_with_a_missing_name_can_never_crash_a_join(self):
        broken = [fixture('1', None, 'Off Chops', '2026-10-26T03:00:00Z'),
                  fixture('2', 'Ground Zero', 'Off Chops', '2026-10-26T03:00:00Z')]
        self.assertEqual(probe.team_keys(broken[0]), [])
        scan = probe.presence_scan('Ground Zero vs Off Chops at 03:00', broken)
        self.assertEqual(scan['fixture_ids'], ['2'])
        self.assertEqual(probe.bind([{'names': ['Ground Zero', 'Off Chops'], 'start': None}], broken),
                         [{'names': ['Ground Zero', 'Off Chops'], 'start': None,
                           'fixture_id': '2', 'join': 'name-only-review-only'}])


class MarginPolicy(unittest.TestCase):
    def test_prices_outside_the_project_band_are_not_marked_usable(self):
        self.assertFalse(probe.usable_pair([1.8, 1.8])['usable'], 'identical prices are a placeholder')
        self.assertFalse(probe.usable_pair([1.01, 1.01])['usable'], 'a 198% book margin is not a market')
        self.assertFalse(probe.usable_pair(['n/a', 2.5])['usable'], 'a non-numeric price is refused')
        self.assertFalse(probe.usable_pair([1.001])['usable'], 'one side is not a market')
        verdict = probe.usable_pair([1.9, 1.95])
        self.assertTrue(verdict['usable'])
        self.assertAlmostEqual(verdict['margin'], round(1/1.9 + 1/1.95, 4), places=4)


class DatedRecords(unittest.TestCase):
    """The two files the probe drops for the site's newest-wins loaders."""

    def setUp(self):
        self.coverage = RECORD / 'live-coverage.json'
        self.research = RECORD / 'line-source-research.json'

    def test_records_are_well_formed_and_state_they_write_no_probability(self):
        for path, marker in ((self.coverage, 'live_fixtures'), (self.research, 'per_fixture')):
            if not path.exists():
                self.skipTest(f'{path.name} is produced by the runner, not by this checkout')
            record = json.loads(path.read_text())
            self.assertEqual(record['schema_version'], 1)
            self.assertTrue(record['observed_at'].endswith('Z') or '+' in record['observed_at'])
            self.assertTrue(record[marker], 'an empty dated record must never be published')
            self.assertNotIn('probabilities', json.dumps(record),
                             'the probe may not write a probability into a dated record')
            self.assertFalse(path.with_suffix('.md').exists() is False,
                             'every dated JSON ships with the human rundown the site links')

    def test_site_loaders_pick_the_record_up_and_render_it(self):
        if not self.coverage.exists() or not self.research.exists():
            self.skipTest('no runner record in this checkout yet')
        from scripts.build import (load_live_coverage, load_no_line_research, live_coverage_gaps,
                                   no_line_research_block)
        loaded_coverage = load_live_coverage(ROOT / 'data')
        loaded_research = load_no_line_research(ROOT / 'data')
        self.assertIsNotNone(loaded_coverage, 'a dated live-coverage record must load')
        self.assertIsNotNone(loaded_research, 'a dated line-source record must load')
        data = {'_live_coverage': loaded_coverage, '_no_line_research': loaded_research,
                'matches': [], 'complete_picks': {'matches': []}}
        gaps_html = live_coverage_gaps(data, './')
        research_html = no_line_research_block(data, './')
        self.assertIn('id="live-coverage-gaps"', gaps_html)
        self.assertIn('id="no-line-research"', research_html)
        self.assertIn('dated', gaps_html.lower(),
                      'the coverage register must present itself as a dated observation')
        self.assertIn('historical research', research_html.lower(),
                      'the research block must never read as the current pick list')


class ProbeNeverOverclaims(unittest.TestCase):
    def test_probe_json_carries_links_and_statuses_only(self):
        path = RECORD / 'probe.json'
        if not path.exists():
            self.skipTest('probe.json is produced by the runner, not by this checkout')
        text = path.read_text()
        for forbidden in ('"probabilities"', '"win_probability"', '"no_vig"', '"pick_index"'):
            self.assertNotIn(forbidden, text, f'the probe must not publish {forbidden}')
        payload = json.loads(text)
        for label, record in payload['surfaces']['surfaces'].items():
            self.assertIn(record['status'], {'ok', 'error'}, f'{label} lost its reachability status')
            self.assertTrue(record['url'].startswith('https://'), f'{label} is not linked to an https source')
            self.assertTrue(record['observed_at'], f'{label} has no observation minute')


if __name__ == '__main__':
    unittest.main(verbosity=2)
