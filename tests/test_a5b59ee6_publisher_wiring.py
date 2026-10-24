"""Session arena-a5b59ee6: integration cover for the automated EGamersWorld rung.

Why this exists
---------------
PR #240 (merged 2026-10-24T06:09Z, ``bdb4fc9``) added the automated EGamersWorld
capture to ``scripts/originate.py`` without importing ``egw_live``. Reproduced
on that commit with this repository's own suite, three modules error with
``NameError: name 'egw_live' is not defined`` — which is job step 5 of
``pages.yml``, so four scheduled refreshes (40028653350, 40037957529,
40048429858, 40063011446) skipped collect, build, deploy and verify. In
production the same line is swallowed by the rung's own ``except``, so the
fallback that exists for low-tier fixtures priced nothing at all.

Sessions arena-5260ef4e, arena-b97af12f and arena-2ed65c56 fixed the wiring on
``main`` while this session reproduced it; their evidence-chain check in
``egw_live.load_live`` is stronger than the one this session had written, so
this branch keeps no competing implementation. What it keeps is the cover the
merge is missing: the rung is *reached* under the real collector, the whole
chain (original HTML → derived capture → manifest → ladder → published pick)
replays to the same numbers, a reviewed capture still outranks an automated one,
and a static check fails on the undefined-name class of defect that started all
of this.

These tests assert wiring and replay, never hand-written odds: every number is
recomputed from a saved response by the existing fail-closed gate.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import egw_live, originate, reference_odds

NOW = datetime(2026, 10, 24, 6, 30, tzinfo=timezone.utc)
OBSERVED = '2026-10-24T06:20:00Z'


def observed_now() -> str:
    """A capture time the live ladder still considers fresh.

    Session arena-3877d48d: the two end-to-end tests below call
    ``originate.run``, which judges freshness against the *real* clock (eight
    hours, ``scripts.domain.MAX_PRICE_AGE_HOURS``). Pinning their observation to
    the module's fixed ``NOW`` (06:30Z on 24 Oct) made them pass in the morning
    and fail every run after ~14:30Z — the same wall-clock bomb that froze the
    scheduled publisher on 23-24 October. The injected-clock test above keeps
    using ``NOW`` explicitly; only the live-path tests take the real time.
    """
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# The rung's contract since arena-b97af12f: a match anchor must carry its own
# timezone-qualified start and a decimal price bound to each exact outcome name.
# A bare "team 3.44 team 1.24" anchor is a lead, not a quote, and prices nothing.
INDEX_HTML = (
    '<html><body><a href="https://egamersworld.com/counterstrike/match/'
    '4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d">'
    '<time datetime="2026-10-26T03:00:00Z">26 Oct 06:00</time>'
    '<span>Ground Zero</span><span>3.44</span>'
    '<span>Off Chops</span><span>1.24</span></a>'
    '</body></html>'
)

MATCH = {
    'id': '1082858',
    'competition': 'DFRAG Invitational 2026',
    'starts_at': '2026-10-26T03:00:00Z',
    'availability': 'future',
    'teams': [{'id': '1', 'name': 'Ground Zero'}, {'id': '2', 'name': 'Off Chops'}],
    'analysis': None,
}

EGW_PAGE = ('https://egamersworld.com/counterstrike/match/'
            '4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d')


def write_chain(evidence: Path, observed: str = OBSERVED, html: str = INDEX_HTML,
                matches=None, manifest_status: str = 'ok') -> dict:
    """Write the three files a live refresh leaves behind, in order.

    This is the same chain ``scripts/originate.live_collect`` writes: the
    original index response, the derived reviewed-schema capture, and the
    request manifest that witnesses the fetch.
    """
    matches = [dict(MATCH)] if matches is None else matches
    entries = egw_live.entries_for(html, matches, {'aliases': []}, observed)
    (evidence / (egw_live.INDEX_EVIDENCE + '.json')).write_text(json.dumps(
        {'url': egw_live.INDEX_URL, 'observed_at': observed, 'html': html}))
    (evidence / egw_live.EVIDENCE_NAME).write_text(json.dumps(
        {'source': 'EGamersWorld CS2 matches index (automated capture)',
         'url': egw_live.INDEX_URL, 'observed_at': observed, 'entries': entries}))
    (evidence / 'live-collection-manifest.json').write_text(json.dumps([
        {'id': egw_live.INDEX_EVIDENCE, 'url': egw_live.INDEX_URL,
         'observed_at': observed, 'status': manifest_status, 'method': 'GET',
         'evidence': egw_live.INDEX_EVIDENCE + '.json'}]))
    return entries[0] if entries else {}


class TheRungIsReachable(unittest.TestCase):
    def test_the_automated_egw_rung_is_imported(self):
        # The exact NameError that stopped four scheduled refreshes.
        self.assertIs(originate.egw_live, egw_live)

    def test_live_collect_reaches_the_egw_rung_and_writes_the_chain(self):
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
            self.assertEqual(out['egw_live']['entries'], 1)
            saved = json.loads((evidence / egw_live.EVIDENCE_NAME).read_text())
            self.assertEqual(saved['entries'][0]['fixture_id'], '1082858')


class TheWholeChainReplays(unittest.TestCase):
    """Original HTML → derived capture → manifest → ladder → published pick."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.evidence = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_witnessed_chain_replays_to_the_saved_pick(self):
        write_chain(self.evidence)
        (entry,) = egw_live.load_live(self.evidence, [dict(MATCH)], {'aliases': []})
        quote, reason = reference_odds.quote(entry, MATCH, NOW)
        self.assertIsNotNone(quote, reason)
        # 3.44 / 1.24 de-vigged: Ground Zero 26.5 %, Off Chops 73.5 %.
        self.assertAlmostEqual(quote['probabilities'][0], 0.265, places=3)
        self.assertAlmostEqual(quote['probabilities'][1], 0.735, places=3)
        self.assertEqual(quote['source_url'], EGW_PAGE)
        self.assertEqual(quote['family'], 'reference')

    def test_a_missing_original_response_prices_nothing(self):
        write_chain(self.evidence)
        (self.evidence / (egw_live.INDEX_EVIDENCE + '.json')).unlink()
        self.assertEqual(egw_live.load_live(self.evidence, [dict(MATCH)],
                                            {'aliases': []}), [])

    def test_a_failed_or_restamped_manifest_prices_nothing(self):
        write_chain(self.evidence)
        manifest = self.evidence / 'live-collection-manifest.json'
        for broken in ([{'id': egw_live.INDEX_EVIDENCE, 'url': egw_live.INDEX_URL,
                         'observed_at': OBSERVED, 'status': 'error', 'method': 'GET',
                         'evidence': egw_live.INDEX_EVIDENCE + '.json'}],
                       [{'id': egw_live.INDEX_EVIDENCE, 'url': egw_live.INDEX_URL,
                         'observed_at': '2026-10-24T05:00:00Z', 'status': 'ok',
                         'method': 'GET',
                         'evidence': egw_live.INDEX_EVIDENCE + '.json'}]):
            manifest.write_text(json.dumps(broken))
            self.assertEqual(egw_live.load_live(self.evidence, [dict(MATCH)],
                                                {'aliases': []}), [])

    def test_a_tampered_capture_prices_nothing(self):
        write_chain(self.evidence)
        path = self.evidence / egw_live.EVIDENCE_NAME
        document = json.loads(path.read_text())
        document['entries'][0]['odds'] = [1.20, 8.00]       # not in the saved HTML
        path.write_text(json.dumps(document))
        self.assertEqual(egw_live.load_live(self.evidence, [dict(MATCH)],
                                            {'aliases': []}), [])


class TheLadderPublishesThePick(unittest.TestCase):
    """End to end: the capture must change a published pick, or it is decoration."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def data_dir(self, chain: bool = True):
        tmp = Path(self.tmp.name)
        evidence = tmp / 'origination' / 'evidence'
        evidence.mkdir(parents=True)
        repo = Path(__file__).resolve().parent.parent
        (tmp / 'origination' / 'aliases.json').write_text(
            (repo / 'data/origination/aliases.json').read_text())
        latest = json.loads((repo / 'data/latest.json').read_text())
        latest.update(matches=[dict(MATCH)], requests=[],
                      inventory_observed_at='2026-10-24T06:00:00Z')
        (tmp / 'latest.json').write_text(json.dumps(latest))
        if chain:
            write_chain(evidence, observed_now())
        return tmp

    def test_the_capture_becomes_a_published_pick(self):
        payload = originate.run(self.data_dir(), live=False, now=NOW)
        row = payload['matches'][0]
        quote = row['origination']
        self.assertIsNotNone(quote, 'the capture priced nothing')
        self.assertEqual(quote['method'], 'reference')
        self.assertEqual(row['pick_index'], 1)              # Off Chops
        self.assertAlmostEqual(quote['probabilities'][1], 0.735, places=3)
        self.assertEqual(quote['source_url'], EGW_PAGE)

    def test_without_the_chain_the_same_fixture_stays_blank(self):
        payload = originate.run(self.data_dir(chain=False), live=False, now=NOW)
        row = payload['matches'][0]
        self.assertIsNone(row['origination'])
        self.assertIsNone(row['pick_index'])

    def test_a_reviewed_capture_outranks_the_automated_one(self):
        tmp = self.data_dir()
        observed = observed_now()
        reviewed = dict(egw_live.entries_for(INDEX_HTML, [dict(MATCH)],
                                             {'aliases': []}, observed)[0],
                        odds=[2.00, 1.80],
                        source_url='https://egamersworld.com/counterstrike/match/'
                                   'reviewed/gz-vs-oc')
        (tmp / 'research' / '57b1ee04').mkdir(parents=True)
        (tmp / 'research/57b1ee04/reference-odds.json').write_text(json.dumps(
            {'entries': [reviewed], 'rejected': [], 'observed_at': observed}))
        payload = originate.run(tmp, live=False, now=NOW)
        quote = payload['matches'][0]['origination']
        self.assertIsNotNone(quote)
        self.assertEqual(quote['source_url'], reviewed['source_url'])
        self.assertEqual([round(x, 4) for x in quote['probabilities']],
                         [round(x, 4) for x in reference_odds.no_vig([2.00, 1.80])])


class NoUndefinedNamesInScripts(unittest.TestCase):
    """The class of defect above, caught statically on every run."""

    def test_scripts_have_no_undefined_module_names(self):
        try:
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
