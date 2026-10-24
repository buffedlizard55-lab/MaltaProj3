"""Session arena-a5b59ee6: the fallback rungs must be *wired*, not just written.

Why this exists
---------------
PR #240 (merged 2026-10-24T06:09Z, ``bdb4fc9``) added the automated EGamersWorld
capture to ``scripts/originate.py`` but the merge dropped the module import: the
file called ``egw_live.*`` while importing every neighbouring module except that
one. Two consequences were reproduced on ``main``:

* the scheduled publisher failed at its first step, ``Regression tests``, with
  ``NameError: name 'egw_live' is not defined`` in three test modules, so five
  scheduled refreshes in a row (21:41Z, 23:08Z, 01:08Z, 04:36Z on 2026-10-23/24)
  deployed nothing; and
* in a live run the same ``NameError`` is swallowed by the rung's own
  ``except Exception`` and recorded as ``egw_live_error``, so the "automated"
  esportsbook-aggregator fallback silently priced no fixture at all.

A second, quieter defect sat behind it: ``egw_live.load_live`` had no caller.
The capture was written to ``data/origination/evidence/live-egw-reference.json``
on every refresh and never read back into the ladder, so even a successful
fetch could not change a pick.

These tests pin the wiring, not the odds. A rung is allowed to fail because a
source is unreachable; it must never fail because nothing called it.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import egw_live, originate, reference_odds

NOW = datetime(2026, 10, 24, 6, 30, tzinfo=timezone.utc)
OBSERVED = '2026-10-24T06:20:00Z'

INDEX_HTML = """
<html><body>
<a href="https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d">
  Ground Zero 3.44 Off Chops 1.24</a>
</body></html>
"""

MATCH = {
    'id': '1082858',
    'competition': 'DFRAG Invitational 2026',
    'starts_at': '2026-10-26T03:00:00Z',
    'availability': 'future',
    'teams': [{'id': '1', 'name': 'Ground Zero'}, {'id': '2', 'name': 'Off Chops'}],
    'analysis': None,
}


def live_entry(**overrides) -> dict:
    entry = egw_live.entries_for(INDEX_HTML, [MATCH], {'aliases': []}, OBSERVED)[0]
    entry.update(overrides)
    return entry


class TheImportSurvivesAMerge(unittest.TestCase):
    def test_the_automated_egw_rung_is_imported(self):
        # Would have failed on bdb4fc9: NameError at first use, not at import.
        self.assertIs(originate.egw_live, egw_live)
        self.assertTrue(hasattr(originate, 'egw_live'))

    def test_live_collect_reaches_the_egw_rung_and_records_it(self):
        """The rung must run under the real collector, not raise NameError."""

        def fake_fetch_html(self_client, url, label):
            body = INDEX_HTML if url == egw_live.INDEX_URL else ''
            entry = {'id': label, 'url': url, 'observed_at': OBSERVED,
                     'status': 'ok', 'method': 'GET'}
            self_client.requests.append(entry)
            return body, entry

        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / 'origination' / 'evidence'
            evidence.mkdir(parents=True)
            with patch.object(originate.Collector, 'fetch_html', new=fake_fetch_html), \
                    patch.object(originate.Collector, 'get_json',
                                 side_effect=RuntimeError('offline in this test')):
                out = originate.live_collect(evidence, [dict(MATCH)], {'aliases': []})
            self.assertNotIn('egw_live_error', out)
            self.assertEqual(out['egw_live'], {'entries': 1})
            saved = json.loads((evidence / egw_live.EVIDENCE_NAME).read_text())
            self.assertEqual(saved['entries'][0]['fixture_id'], '1082858')


class TheCaptureIsConsumed(unittest.TestCase):
    """``live-egw-reference.json`` must reach the reference rung and its audit."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name)
        (self.source / 'origination' / 'evidence').mkdir(parents=True)
        self.evidence = self.source / 'origination' / 'evidence'
        self.write_manifest(OBSERVED)

    def tearDown(self):
        self.tmp.cleanup()

    def write_manifest(self, observed, status='ok'):
        (self.evidence / 'live-collection-manifest.json').write_text(json.dumps([
            {'id': 'live-egw-index', 'url': egw_live.INDEX_URL, 'observed_at': observed,
             'status': status, 'method': 'GET'}]))

    def write_capture(self, entry):
        (self.evidence / egw_live.EVIDENCE_NAME).write_text(json.dumps(
            {'source': 'EGamersWorld CS2 matches index (automated capture)',
             'url': egw_live.INDEX_URL, 'observed_at': entry['observed_at'],
             'entries': [entry]}))

    def test_a_witnessed_capture_prices_the_fixture(self):
        entry = live_entry()
        self.write_capture(entry)
        capture = reference_odds.load(self.source)
        self.assertIn(entry['fixture_id'], [e['fixture_id'] for e in capture['entries']])
        quote, reason = reference_odds.quote(entry, MATCH, NOW)
        self.assertIsNotNone(quote, reason)
        self.assertEqual(quote['family'], 'reference')
        # No-vig of 3.44 / 1.24 is Ground Zero 26.5% / Off Chops 73.5%.
        # Probabilities are published as fractions (0.2649 / 0.7350).
        first, second = quote['probabilities']
        self.assertAlmostEqual(first, 0.265, places=3)
        self.assertAlmostEqual(second, 0.735, places=3)
        self.assertEqual(quote['source_url'], entry['source_url'])

    def test_an_unwitnessed_capture_is_rejected_with_a_reason(self):
        entry = live_entry()
        self.write_capture(entry)
        self.write_manifest('2026-10-24T05:00:00Z')  # restamped fetch
        capture = reference_odds.load(self.source)
        self.assertEqual(capture['entries'], [])
        (rejected,) = capture['rejected']
        self.assertTrue(rejected['rejected'])
        self.assertIn('not witnessed', rejected['reason'])
        quote, reason = reference_odds.quote(rejected, MATCH, NOW)
        self.assertIsNone(quote)
        self.assertIn('not witnessed', reason)

    def test_a_failed_fetch_cannot_price_anything(self):
        entry = live_entry()
        self.write_capture(entry)
        self.write_manifest(OBSERVED, status='error')
        self.assertEqual(reference_odds.load(self.source)['entries'], [])

    def test_a_missing_manifest_cannot_price_anything(self):
        self.write_capture(live_entry())
        (self.evidence / 'live-collection-manifest.json').unlink()
        self.assertEqual(reference_odds.load(self.source)['entries'], [])

    def test_hand_reviewed_captures_need_no_manifest(self):
        reviewed = live_entry(capture='manual review')
        (self.source / 'research' / '57b1ee04').mkdir(parents=True)
        (self.source / 'research/57b1ee04/reference-odds.json').write_text(
            json.dumps({'entries': [reviewed], 'rejected': [], 'observed_at': OBSERVED}))
        (self.evidence / 'live-collection-manifest.json').unlink()
        self.assertEqual(reference_odds.load(self.source)['entries'], [reviewed])

    def test_replay_selects_the_capture_the_quote_came_from(self):
        """A stale reviewed row and a fresh automated row can share a fixture."""
        reviewed = live_entry(observed_at='2026-10-20T00:00:00Z', source_url=(
            'https://egamersworld.com/counterstrike/match/reviewed/ground-zero-vs-off-chops'))
        automated = live_entry()
        (self.source / 'research' / '57b1ee04').mkdir(parents=True)
        (self.source / 'research/57b1ee04/reference-odds.json').write_text(
            json.dumps({'entries': [reviewed, automated], 'rejected': [], 'observed_at': OBSERVED}))
        quote, reason = reference_odds.quote(automated, MATCH, NOW)
        self.assertIsNotNone(quote, reason)
        entry = reference_odds.entry_for(self.source, MATCH['id'], quote)
        self.assertIsNotNone(entry)
        self.assertEqual(entry['observed_at'], OBSERVED)
        self.assertEqual(entry['source_url'], automated['source_url'])
        reference_odds.replay(entry, quote)  # no drift, no exception

    def test_replay_still_rejects_a_quote_with_no_capture(self):
        self.write_capture(live_entry())
        forged = {'source_url': 'https://egamersworld.com/counterstrike/match/forged/x-y',
                  'observed_at': OBSERVED, 'excerpt_sha256': '0' * 64}
        self.assertIsNone(reference_odds.entry_for(self.source, MATCH['id'], forged))

    def test_placeholder_prices_stay_rejected(self):
        """EGamersWorld prints 1.8/1.8 for fixtures it has no book for."""
        entry = {'fixture_id': '1082792',
                 'teams': ['HOTU', 'The Huns'],
                 'provider_teams': ['HOTU', 'The Huns Esports'],
                 'starts_at': '2026-10-31T09:00:00Z', 'odds': [1.8, 1.8],
                 'source_url': 'https://egamersworld.com/counterstrike/match/EkalRNMvVx/hotu-vs-the-huns',
                 'observed_at': OBSERVED,
                 'excerpt': 'EGamersWorld lists HOTU vs The Huns at 1.8 / 1.8 (placeholder).',
                 'excerpt_sha256': '', 'provider': reference_odds.PROVIDER,
                 'capture': 'automated EGW index capture (scripts/egw_live.py)'}
        import hashlib
        entry['excerpt_sha256'] = hashlib.sha256(entry['excerpt'].encode()).hexdigest()
        match = {'id': '1082792', 'starts_at': '2026-10-31T09:00:00Z',
                 'teams': [{'name': 'HOTU'}, {'name': 'The Huns'}]}
        self.write_capture(entry)
        self.write_manifest(OBSERVED)
        quote, reason = reference_odds.quote(entry, match, NOW)
        self.assertIsNone(quote)
        self.assertIn('placeholder', reason)


class TheLadderPublishesThePick(unittest.TestCase):
    """End to end: a live capture must change a published pick, or it is dead code.

    Before this session's fix the same evidence produced ``method=None`` and no
    pick for the fixture, because nothing ever read the capture back.
    """

    def data_dir(self):
        tmp = Path(self.tmp.name)
        (tmp / 'origination' / 'evidence').mkdir(parents=True)
        repo = Path(__file__).resolve().parent.parent
        (tmp / 'origination' / 'aliases.json').write_text(
            (repo / 'data/origination/aliases.json').read_text())
        latest = json.loads((repo / 'data/latest.json').read_text())
        latest.update(matches=[dict(MATCH)], requests=[],
                      inventory_observed_at='2026-10-24T06:00:00Z')
        (tmp / 'latest.json').write_text(json.dumps(latest))
        observed = NOW.strftime('%Y-%m-%dT%H:%M:%SZ')
        entry = egw_live.entries_for(INDEX_HTML, [dict(MATCH)], {'aliases': []}, observed)[0]
        (tmp / 'origination/evidence' / egw_live.EVIDENCE_NAME).write_text(json.dumps(
            {'source': 'EGamersWorld CS2 matches index (automated capture)',
             'url': egw_live.INDEX_URL, 'observed_at': observed, 'entries': [entry]}))
        (tmp / 'origination/evidence/live-collection-manifest.json').write_text(json.dumps(
            [{'id': 'live-egw-index', 'url': egw_live.INDEX_URL, 'observed_at': observed,
              'status': 'ok', 'method': 'GET'}]))
        return tmp

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_automated_capture_becomes_a_published_pick(self):
        payload = originate.run(self.data_dir(), live=False)
        row = payload['matches'][0]
        quote = row['origination']
        self.assertIsNotNone(quote, 'the capture priced nothing')
        self.assertEqual(quote['method'], 'reference')
        self.assertEqual(row['pick_index'], 1)          # Off Chops
        self.assertAlmostEqual(quote['probabilities'][1], 0.735, places=3)
        self.assertEqual(quote['source_url'],
                         'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/'
                         'ground-zero-vs-off-chops-5mfkMFe7d')

    def test_removing_the_capture_from_the_pool_leaves_the_fixture_blank(self):
        original = reference_odds.CAPTURE_PATHS
        reference_odds.CAPTURE_PATHS = tuple(
            p for p in original if p != reference_odds.LIVE_EVIDENCE_PATH)
        try:
            payload = originate.run(self.data_dir(), live=False)
        finally:
            reference_odds.CAPTURE_PATHS = original
        row = payload['matches'][0]
        self.assertIsNone(row['origination'])
        self.assertIsNone(row['pick_index'])


class NoUndefinedNamesInScripts(unittest.TestCase):
    """The class of defect above, caught statically on every run."""

    def test_scripts_have_no_undefined_module_names(self):
        try:
            import io
            from pyflakes import api, reporter
        except ImportError:  # pragma: no cover - CI installs it (requirements.txt)
            self.skipTest('pyflakes is not installed in this environment')

        root = Path(__file__).resolve().parent.parent
        problems, inspected = [], []
        for path in sorted((root / 'scripts').glob('*.py')):
            stream = io.StringIO()
            api.checkPath(str(path), reporter=reporter.Reporter(stream, stream))
            problems.extend(line for line in stream.getvalue().splitlines()
                            if 'undefined name' in line)
            inspected.append(path.name)
        self.assertTrue(inspected, 'no script modules were inspected')
        self.assertEqual(problems, [],
                         'undefined module-level names in scripts/: ' + '; '.join(problems))


if __name__ == '__main__':
    unittest.main()
