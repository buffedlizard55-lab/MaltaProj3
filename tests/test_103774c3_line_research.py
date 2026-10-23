"""Session arena-103774c3 — HLTV-first line research for fixtures with no betting line.

The brief asks for a pick for every Hotspawn CS2 fixture and, for the fixtures
the featured method cannot resolve (low tier, or not covered by books such as
Polymarket), a researched route to a pick: HLTV first, then esportsbooks and
betting lines, with a separate section for whatever stays unresolved and its
limitations. This session adds the read-only runner probe
``scripts/103774c3_probe.py`` and the dated platform-side dossier in
``data/research/103774c3/``.

These tests pin the rules that keep that research honest:

* the probe never writes a probability or a pick — copied exchange/bookmaker
  numbers only, and ``money_line_lead`` keeps the exact meaning the executive
  summary renders (two-sided bo3.gg relay quote, or the Pinnacle guest board);
* the emitted runner record is eligible for the summary's dated no-line block
  (runner stamp, sibling Markdown, per-fixture list) and the block's loader
  accepts it;
* the dossier records an HLTV match page for every researched fixture, marks
  the fan poll excluded, and leaves unread values blank rather than inferred;
* the review flags carry the schema the Flagged-for-Review page requires.
"""
from __future__ import annotations

import importlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build import load_no_line_research

# A module name starting with a digit cannot be imported with ``import``; load
# by dotted path like the earlier session probes.
probe = importlib.import_module('scripts.103774c3_probe')

RESEARCH = Path('data/research/103774c3')


class ProbePureFunctionTests(unittest.TestCase):
    def test_listing_match_is_word_bounded_and_not_a_substring(self):
        self.assertTrue(probe._listed('Acend', 'counter-strike: acend vs unity (bo3)'))
        self.assertFalse(probe._listed('WW', 'ww vs someone'))  # shorter than 3 chars: never matched
        self.assertFalse(probe._listed('Color', 'colorful fixtures listed here'))
        self.assertTrue(probe._listed('ex-Zero Tenacity', 'color vs ex-zero tenacity (bo3)'))

    def test_hltv_url_comes_from_the_ladders_own_research_trail(self):
        match = {'research': [
            {'stage': 'Primary: Polymarket', 'source_url': 'https://polymarket.com/esports/cs2'},
            {'stage': 'HLTV research', 'source_url': 'https://www.hltv.org/matches/2399699/a-vs-b'},
        ]}
        self.assertEqual(probe._hltv_url(match), 'https://www.hltv.org/matches/2399699/a-vs-b')
        self.assertIsNone(probe._hltv_url({'research': []}))
        self.assertIsNone(probe._hltv_url({}))

    def test_polymarket_state_describes_copied_prices_and_derives_no_probability(self):
        self.assertIn('no open Polymarket CS2 event', probe.polymarket_state(None))
        empty = probe.polymarket_state({'slug': 'x', 'markets': [{'best_bid': None, 'best_ask': None}]})
        self.assertIn('no market carried both', empty)
        bound = probe.polymarket_state({'slug': 'x', 'markets': [
            {'best_bid': 0.04, 'best_ask': 0.96}, {'best_bid': 0.40, 'best_ask': 0.55}]})
        self.assertIn('widest recorded spread 0.92', bound)
        for text in (empty, bound):
            self.assertNotIn('probabilit', text.lower())
            self.assertNotIn('pick', text.lower())

    def test_the_probe_writes_both_files_the_summary_block_requires(self):
        source = Path('scripts/103774c3_probe.py').read_text()
        self.assertIn("'line-source-research.json'", source)
        self.assertIn("'line-source-research.md'", source)
        self.assertIn("'environment': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS')", source)


class RunnerRecordTests(unittest.TestCase):
    """The sweep the workflow committed must be summary-eligible and pick-free."""

    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((RESEARCH / 'line-source-research.json').read_text())

    def test_record_shape_and_honest_environment(self):
        self.assertEqual(self.record['session'], 'arena-103774c3')
        self.assertEqual(self.record['environment'], 'github-actions-runner')
        self.assertTrue((RESEARCH / 'line-source-research.md').is_file())
        self.assertIsInstance(self.record['per_fixture'], list)
        self.assertTrue(self.record['per_fixture'])

    def test_record_is_accepted_by_the_summary_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'research/103774c3/line-source-research.json'
            target.parent.mkdir(parents=True)
            shutil.copyfile(RESEARCH / 'line-source-research.json', target)
            shutil.copyfile(RESEARCH / 'line-source-research.md', target.with_suffix('.md'))
            loaded = load_no_line_research(root)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded['_record_path'], 'research/103774c3/line-source-research.json')

    def test_lead_means_only_a_two_sided_relay_or_a_pinnacle_listing(self):
        for fixture in self.record['per_fixture']:
            allowed = bool(fixture.get('bo3_bet_two_sided') or fixture.get('pinnacle_matchup'))
            self.assertEqual(bool(fixture.get('money_line_lead')), allowed, fixture.get('id'))
            # Copied prices only: no probability or pick is ever written.
            blob = json.dumps(fixture).lower()
            self.assertNotIn('"probabilities"', blob)
            self.assertNotIn('"pick"', blob)

    def test_every_target_carries_an_official_link_and_a_verdict(self):
        for fixture in self.record['per_fixture']:
            self.assertTrue(str(fixture.get('hotspawn_url') or '').startswith('https://'), fixture.get('id'))
            self.assertTrue(fixture.get('verdict'), fixture.get('id'))
            self.assertTrue(fixture.get('polymarket_state'), fixture.get('id'))


class DossierTests(unittest.TestCase):
    """The platform-side HLTV dossier: dated, sourced, blanks left blank."""

    @classmethod
    def setUpClass(cls):
        cls.dossier = json.loads((RESEARCH / 'hltv-first-research.json').read_text())

    def test_all_eight_fixtures_have_hltv_first_evidence(self):
        fixtures = self.dossier['fixtures']
        self.assertEqual(len(fixtures), 8)
        self.assertEqual(self.dossier['summary']['fixtures_researched'], 8)
        for fixture in fixtures:
            hltv = fixture['hltv']
            self.assertTrue(hltv['url'].startswith('https://www.hltv.org/matches/'), fixture['hotspawn_id'])
            self.assertTrue(fixture['hotspawn_url'].startswith('https://'), fixture['hotspawn_id'])
            self.assertTrue(fixture['site_card'].startswith('https://'), fixture['hotspawn_id'])
            self.assertIn('no decimal odds', hltv['betting_block'], fixture['hotspawn_id'])
            # The fan poll is recorded only as excluded evidence.
            self.assertIn('excluded', hltv['fan_poll_excluded']['note'], fixture['hotspawn_id'])

    def test_unread_values_are_blank_not_inferred(self):
        phantom = next(f for f in self.dossier['fixtures'] if f['hotspawn_id'] == '1081605')
        self.assertIsNone(phantom['hltv']['ranks_read'])
        self.assertIn('left blank, not inferred', phantom['hltv']['ranks_note'])

    def test_the_one_live_book_is_copied_verbatim_with_its_ceiling(self):
        ground_zero = next(f for f in self.dossier['fixtures'] if f['hotspawn_id'] == '1082858')
        quotes = ground_zero['smarkets']['quotes_copied_verbatim']
        self.assertEqual(quotes['477141069']['bids'][0]['price'], 1429)
        self.assertEqual(quotes['477141070']['offers'][0]['price'], 8547)
        self.assertIn('0.15', ground_zero['smarkets']['arithmetic_on_copied_quotes'])
        acend = next(f for f in self.dossier['fixtures'] if f['hotspawn_id'] == '1082996')
        self.assertEqual(acend['smarkets']['quotes'],
                         {'477168991': {'bids': [], 'offers': []},
                          '477168992': {'bids': [], 'offers': []}})

    def test_dossier_writes_no_pick_of_its_own(self):
        self.assertIn('Nothing here is a probability, a pick or an alias', self.dossier['policy'])
        for fixture in self.dossier['fixtures']:
            # The only percentages are the site's published snapshot values,
            # carried under a key that names their source and date.
            for key in fixture:
                if 'percent' in key:
                    self.assertIn('snapshot_0923Z', key)


class FlagTests(unittest.TestCase):
    def test_flags_carry_the_review_schema(self):
        flags = json.loads((RESEARCH / 'flags.json').read_text())
        ids = [f['id'] for f in flags]
        self.assertEqual(len(ids), len(set(ids)))
        target_ids = {f['hotspawn_id'] for f in
                      json.loads((RESEARCH / 'hltv-first-research.json').read_text())['fixtures']}
        for flag in flags:
            for key in ('id', 'severity', 'title', 'detail', 'source_urls', 'match_ids'):
                self.assertIn(key, flag)
            self.assertEqual(flag['severity'], 'notice')
            self.assertTrue(flag['source_urls'])
            for url in flag['source_urls']:
                self.assertTrue(url.startswith('https://'), url)
            for match_id in flag['match_ids']:
                self.assertIn(match_id, target_ids)


if __name__ == '__main__':
    unittest.main()
