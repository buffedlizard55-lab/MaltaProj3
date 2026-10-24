"""Session arena-5260ef4e: the automated EGamersWorld rung must be wired, not just written.

Session arena-43110640 added `scripts/egw_live.py`, which every live refresh runs
to capture EGamersWorld's published bookmaker-average prices, and a block in
`scripts/originate.py::live_collect` that saves the capture to
`data/origination/evidence/live-egw-reference.json`.

Two defects made that whole rung inert in production:

1. `scripts/originate.py` never imported `egw_live`, so the capture block raised
   `NameError` before its own `try`. That aborted the live collection and failed
   nine regression tests in `tests/test_f9d0a5a2.py`,
   `tests/test_origination_upgrade.py` and `tests/test_source_integrity.py`
   (`NameError: name 'egw_live' is not defined`), which is the failure the
   scheduled `pages.yml` regression step hit from 2026-10-23T21:41Z onwards.
2. Nothing ever read the capture back. `egw_live.load_live()` had no caller and
   `reference_odds.load()` only reads the three reviewed manual captures, so no
   automated EGamersWorld price could ever reach a pick.

These tests assert the wiring and the fail-closed behaviour that must survive it.
Every input here is synthetic; no network is touched.
"""
from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import egw_live, originate, reference_odds

UTC = timezone.utc
NOW = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
START = '2026-10-24T14:00:00Z'
HOTSPAWN = 'https://www.hotspawn.com/matches/a-vs-b-nodwin-clutch-series-13-1082996'
EGW_PAGE = 'https://egamersworld.com/counterstrike/match/synthetic/acend-vs-unity-xyz'


def match():
    """A low-tier fixture the featured ladder leaves blank."""
    return {
        'id': '1082996',
        'teams': [{'id': '1', 'name': 'Acend'}, {'id': '2', 'name': 'UNiTY'}],
        'competition': 'NODWIN Clutch Series #13',
        'starts_at': START,
        'locks_at': '2026-10-24T13:54:00Z',
        'availability': 'open',
        'tier': 'c',
        'source_url': HOTSPAWN,
        'lobby_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1082996',
        'analysis': None,
        'pick_index': None,
        'research': [],
        'limitations': [],
    }


def capture(odds=(2.37, 1.50), observed=None, fixture='1082996', teams=('Acend', 'UNiTY')):
    excerpt = (f"EGamersWorld CS2 matches index ({egw_live.INDEX_URL}) lists "
               f"{teams[0]} vs {teams[1]} at decimal odds {odds[0]:g} / {odds[1]:g}")
    import hashlib
    return {
        'fixture_id': fixture,
        'teams': list(teams),
        'provider_teams': list(teams),
        'starts_at': START,
        'odds': list(odds),
        'source_url': EGW_PAGE,
        'observed_at': observed or originate.iso(NOW),
        'excerpt': excerpt,
        'excerpt_sha256': hashlib.sha256(excerpt.encode('utf-8')).hexdigest(),
        'provider': egw_live.PROVIDER,
        'capture': 'automated EGW index capture (scripts/egw_live.py)',
    }


class TheModuleIsImported(unittest.TestCase):
    """Defect 1: an undefined name is a production outage, not a cosmetic lint."""

    def test_originate_exposes_the_egw_live_module(self):
        self.assertIs(originate.egw_live, egw_live)

    def test_the_live_collector_reaches_its_own_capture_block(self):
        source = inspect.getsource(originate.live_collect)
        self.assertIn('egw_live.INDEX_URL', source)
        self.assertIn('egw_live.EVIDENCE_NAME', source)


class TheCaptureIsReplayed(unittest.TestCase):
    """Defect 2: a saved capture with no reader prices nothing."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.evidence = Path(self.tmp.name)
        self.registry = originate.load_registry(
            Path(__file__).resolve().parents[1] / 'data/origination/aliases.json')
        # Synthetic original markup, not generated prose standing in for an
        # observed provider clock and named outcomes. Match Collector.fetch_html.
        self.html = (f'<html><a href="{EGW_PAGE}"><time datetime="{START}"></time>'
                     'Acend 2.37 UNiTY 1.50</a></html>')
        observed = originate.iso(NOW)
        entries = egw_live.entries_for(self.html, [match()], self.registry, observed)
        self.assertEqual(len(entries), 1)
        (self.evidence / (egw_live.INDEX_EVIDENCE + '.json')).write_text(json.dumps({
            'url': egw_live.INDEX_URL, 'observed_at': observed, 'html': self.html}))
        import hashlib
        (self.evidence / 'live-collection-manifest.json').write_text(json.dumps([{
            'id': egw_live.INDEX_EVIDENCE, 'url': egw_live.INDEX_URL,
            'method': 'GET', 'status': 'ok', 'http_status': 200,
            'observed_at': observed, 'evidence': egw_live.INDEX_EVIDENCE + '.json',
            'response_sha256': hashlib.sha256(self.html.encode()).hexdigest()}]))
        (self.evidence / egw_live.EVIDENCE_NAME).write_text(json.dumps({
            'source': 'EGamersWorld CS2 matches index (automated capture)',
            'url': egw_live.INDEX_URL, 'observed_at': observed, 'entries': entries}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_replays_the_capture_into_the_reference_rung(self):
        source = inspect.getsource(originate.run)
        self.assertIn("egw_live.load_live(evidence_dir, snapshot['matches'], registry)", source)
        self.assertIn("'egw_live_replay'", source)

    def test_a_replayed_entry_prices_a_fixture_the_featured_ladder_left_blank(self):
        rows = egw_live.load_live(self.evidence, [match()], self.registry)
        self.assertEqual(len(rows), 1)
        result = originate.resolve_match(match(), [], [], [], None,
                                         originate.load_registry(
                                             Path(__file__).resolve().parents[1]
                                             / 'data' / 'origination' / 'aliases.json'),
                                         NOW, reference=rows)
        origination = result['origination']
        self.assertEqual(origination['method'], 'reference')
        # 2.37 / 1.50 de-vigged: 1/2.37 = 0.4219, 1/1.50 = 0.6667, sum 1.0886
        self.assertAlmostEqual(origination['probabilities'][0], 0.3876, places=3)
        self.assertAlmostEqual(origination['probabilities'][1], 0.6124, places=3)
        self.assertEqual(origination['source_url'], EGW_PAGE)
        self.assertEqual(result['pick_index'], 1)
        self.assertIn('EGamersWorld', origination['label'])
        self.assertIn('EGamersWorld', reference_odds.PROVIDER)

    def test_derived_capture_without_original_response_cannot_price_anything(self):
        (self.evidence / (egw_live.INDEX_EVIDENCE + '.json')).unlink()
        self.assertEqual(egw_live.load_live(self.evidence, [match()], self.registry), [])

    def test_identical_placeholder_prices_still_price_nothing(self):
        # EGamersWorld serves 1.8/1.8 on pages without a real bookmaker average;
        # the automated capture must not turn that placeholder into a pick.
        rows = [capture(odds=(1.8, 1.8))]
        result = originate.resolve_match(match(), [], [], [], None,
                                         originate.load_registry(
                                             Path(__file__).resolve().parents[1]
                                             / 'data' / 'origination' / 'aliases.json'),
                                         NOW, reference=rows)
        self.assertIsNone(result['origination'])
        self.assertIsNone(result['pick_index'])

    def test_a_stale_capture_prices_nothing(self):
        stale = originate.iso(NOW - timedelta(hours=12))
        rows = [capture(observed=stale)]
        result = originate.resolve_match(match(), [], [], [], None,
                                         originate.load_registry(
                                             Path(__file__).resolve().parents[1]
                                             / 'data' / 'origination' / 'aliases.json'),
                                         NOW, reference=rows)
        self.assertIsNone(result['origination'])

    def test_a_capture_for_another_start_time_prices_nothing(self):
        row = dict(capture(), starts_at='2026-10-24T16:00:00Z')
        result = originate.resolve_match(match(), [], [], [], None,
                                         originate.load_registry(
                                             Path(__file__).resolve().parents[1]
                                             / 'data' / 'origination' / 'aliases.json'),
                                         NOW, reference=[row])
        self.assertIsNone(result['origination'])


class ReviewedCapturesStillOutrankAutomatedOnes(unittest.TestCase):
    def test_manual_entries_are_ordered_before_the_automated_capture(self):
        source = inspect.getsource(originate.run)
        # The manual capture is built first, then the automated rows are appended.
        self.assertLess(source.index('reference_odds.load(output)'),
                        source.index("egw_live.load_live(evidence_dir, snapshot['matches'], registry)"))
        self.assertIn('reference_rows = reference_rows + egw_live_rows', source)


if __name__ == '__main__':
    unittest.main()
