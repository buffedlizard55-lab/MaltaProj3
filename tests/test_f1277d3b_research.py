"""Session arena-f1277d3b — publisher un-stall + HLTV-first no-line research.

Pins, offline and line by line:

* the wall-clock fix: ``test_ca7e10e5_snapshot`` passes the injectable clock to
  every ``root_publish.build_plan`` call, and the plan for the fixture stamp
  succeeds at the fixed reference time (the failure that stalled scheduled
  publisher runs 40028653350..40063011446 must not recur);
* the dossier's target set is exactly the fixtures the published snapshot
  prices without an external line (featured ``method`` model or unresolved),
  recomputed from the checked-in published ``snapshot.json``;
* every dossier row carries an official HLTV link, a verdict and an excluded
  fan poll, and no dossier field masquerades as a probability;
* the review flags use the shared dated schema with official source links;
* the probe is this session's copy (session id + output dir), import-clean and
  still read-only (no write of probabilities into snapshot files);
* the built executive summary carries the dated no-line block exactly once
  (duplicate-id regression found and fixed in this session).

Nothing here asserts a probability or a pick.
"""
from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data/research/f1277d3b/hltv-first-research.json'
FLAGS = ROOT / 'data/research/f1277d3b/flags.json'
SNAPSHOT = ROOT / 'snapshot.json'


class WallClockFixHolds(unittest.TestCase):
    def test_every_build_plan_call_passes_the_fixed_clock(self):
        source = (ROOT / 'tests/test_ca7e10e5_snapshot.py').read_text()
        calls = source.count('root_publish.build_plan(self.output, self.root')
        self.assertGreaterEqual(calls, 3)
        self.assertEqual(
            source.count('root_publish.build_plan(self.output, self.root, now=NOW)'), calls)

    def test_fixture_stamp_plans_at_the_fixed_reference_time(self):
        from scripts import root_publish
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            output, root = base / 'site', base / 'root'
            (output / 'data').mkdir(parents=True)
            root.mkdir()
            stamp = '2026-10-23T09:23:57Z'
            (output / 'data/latest.json').write_text(json.dumps(
                {'schema_version': 1, 'generated_at': stamp, 'counts': {}}))
            (output / 'index.html').write_text(
                f'<html><body data-snapshot-generated="{stamp}">'
                + 'x' * root_publish.MIN_INDEX_BYTES + '</body></html>')
            plan = root_publish.build_plan(
                output, root, now=datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc))
            self.assertIn('index.html', plan.writes)


class DossierTargetsAreExactlyTheNoLineRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = json.loads(DOSSIER.read_text())
        cls.snapshot = json.loads(SNAPSHOT.read_text())

    def test_target_rule_recomputes_from_the_published_snapshot(self):
        expected = set()
        for match in self.snapshot.get('matches') or []:
            if match.get('availability') == 'past':
                continue
            analysis = match.get('analysis') or {}
            if analysis.get('method') not in ('market', 'bookmaker'):
                expected.add(str(match.get('id')))
        self.assertEqual({f['hotspawn_id'] for f in self.dossier['fixtures']}, expected)
        self.assertEqual(set(self.dossier['target_selection']['ids']), expected)

    def test_every_row_links_its_official_hltv_page(self):
        snap_urls = {}
        for match in self.snapshot.get('matches') or []:
            for entry in match.get('research') or []:
                url = str((entry or {}).get('source_url') or '')
                if url.startswith('https://www.hltv.org/matches/'):
                    snap_urls[str(match.get('id'))] = url
        for fixture in self.dossier['fixtures']:
            hltv = fixture['hltv']
            self.assertTrue(
                hltv['url'].startswith('https://www.hltv.org/matches/'), fixture['hotspawn_id'])
            if fixture['hotspawn_id'] in snap_urls:
                self.assertEqual(hltv['url'], snap_urls[fixture['hotspawn_id']])
            self.assertIn('Best of 3', hltv['format'])
            self.assertIn('no decimal odds', hltv['betting_block'])
            self.assertIn('excluded by policy', hltv['fan_poll_excluded']['note'])
            self.assertTrue(fixture['verdict'])

    def test_no_probability_is_presented_as_research_output(self):
        # Published percentages may only be copied, clearly sourced to the
        # snapshot; the dossier itself originates numbers nowhere.
        self.assertIn('copied verbatim', self.dossier['published_estimates_note'])
        for fixture in self.dossier['fixtures']:
            self.assertIn('published_percentages_snapshot_2010Z', fixture)
            for key in fixture:
                self.assertNotIn(key, {'probability', 'our_probability', 'new_pick', 'odds'})
        self.assertEqual(self.dossier['summary']['hltv_betting_blocks_with_two_sided_odds'], 0)
        self.assertEqual(self.dossier['summary']['money_line_leads_from_hltv'], 0)


class FlagsUseTheReviewSchema(unittest.TestCase):
    def test_flags(self):
        flags = json.loads(FLAGS.read_text())
        snapshot_ids = {str(m.get('id')) for m in json.loads(SNAPSHOT.read_text())['matches']}
        ids = [f['id'] for f in flags]
        self.assertEqual(len(ids), len(set(ids)))
        for flag in flags:
            self.assertTrue(flag['id'].startswith('f1277d3b-'))
            self.assertIn(flag['severity'], {'notice', 'warning', 'critical'})
            self.assertTrue(flag['title'] and flag['detail'])
            self.assertTrue(flag['source_urls'])
            self.assertTrue(all(u.startswith('https://') for u in flag['source_urls']))
            for match_id in flag.get('match_ids') or []:
                self.assertIn(match_id, snapshot_ids)


class ProbeIsThisSessionsReadOnlyCopy(unittest.TestCase):
    def test_probe_imports_and_names_this_session(self):
        probe = importlib.import_module('scripts.f1277d3b_probe')
        source = Path(probe.__file__).read_text()
        self.assertIn("default=Path('data/research/f1277d3b')", source)
        self.assertIn("'session': 'arena-f1277d3b'", source)
        # Read-only contract: writes only under its own research --out dir.
        self.assertNotIn("Path('data/latest.json').write_text", source)
        self.assertNotIn("Path('data/origination.json').write_text", source)

    def test_polymarket_state_is_verbatim_not_a_conversion(self):
        probe = importlib.import_module('scripts.f1277d3b_probe')
        self.assertEqual(
            probe.polymarket_state(None),
            'no open Polymarket CS2 event bound both exact team names')
        binding = {'slug': 'x-vs-y', 'markets': [
            {'best_bid': 0.10, 'best_ask': 0.90}]}
        self.assertIn('widest recorded spread 0.80', probe.polymarket_state(binding))


class SummaryCarriesTheDatedBlockOnce(unittest.TestCase):
    def test_built_summary_has_one_no_line_research_block(self):
        site = ROOT / 'site/index.html'
        if not site.exists():
            self.skipTest('run python -m scripts.build first')
        html = site.read_text()
        self.assertEqual(html.count('id="no-line-research"'), 1)
        # The separate unresolved section and the one-tap picks links the brief
        # asks for stay on the summary.
        self.assertIn('id="unresolved-register"', html)
        self.assertIn('href="./picks/"', html)
        self.assertIn('href="./unresolved/"', html)

    def test_build_source_keeps_single_summary_render(self):
        source = (ROOT / 'scripts/build.py').read_text()
        summary_start = source.index('def summary(data, prefix, now=None):')
        summary_body = source[summary_start:source.index('\ndef ', summary_start + 10)]
        self.assertEqual(summary_body.count('no_line_research_block(data, prefix)'), 1)
        register_start = source.index('def unresolved_register(')
        register_body = source[register_start:source.index('\ndef ', register_start + 10)]
        # The full (non-compact) register on /unresolved/ renders it once; the
        # compact branch must not add a second copy to the summary.
        compact_body = register_body[:register_body.index("out.append(no_line_register")]
        self.assertNotIn('out.append(no_line_research_block(data, prefix))', compact_body)


if __name__ == '__main__':
    unittest.main()
