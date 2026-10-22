"""93B-2: the read-only row verifier must keep reproducing every published pick.

``scripts/verify_93ba7221.py`` recomputes each active row's published probability from
inputs that are already published with it — saved order-book midpoints, saved bookmaker
decimal odds, or Valve points plus the documented formula. These tests pin the tool's
own behaviour on the checked-in snapshot so a later edit cannot quietly turn it into a
rubber stamp: the checked-in snapshot must reproduce with zero failures, a deliberately
tampered copy must fail, and the module must not be able to reach a provider.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.verify_93ba7221 import check

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SOURCE = (ROOT / 'scripts' / 'verify_93ba7221.py').read_text(encoding='utf-8')


class CheckedInSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = check(DATA)

    def test_every_active_row_carries_a_probability(self):
        self.assertGreater(self.report['active_rows'], 0)
        self.assertEqual(self.report['with_published_probability'], self.report['active_rows'])

    def test_every_published_probability_is_reproduced(self):
        self.assertEqual(self.report['failed'], [], self.report['failed'])
        self.assertEqual(self.report['reproduced'], self.report['active_rows'])

    def test_each_row_passes_every_applicable_check(self):
        for row in self.report['rows']:
            self.assertTrue(row['checks'], row['fixture_id'])
            failed = [name for name, ok in row['checks'].items() if not ok]
            self.assertEqual(failed, [], f'{row["fixture_id"]} {row["fixture"]}: {failed}')
            for kind, record in row['records'].items():
                self.assertEqual(record['failed_checks'], [], f'{row["fixture_id"]} ({kind})')

    def test_every_row_links_an_official_source(self):
        for row in self.report['rows']:
            self.assertTrue(row['checks'].get('official_source_link'), row['fixture_id'])
            self.assertTrue(row['checks'].get('research_trail_has_a_link'), row['fixture_id'])


class TamperTests(unittest.TestCase):
    """A verifier that cannot fail is not a verification."""

    def edited_copy(self, mutate):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copy(DATA / 'latest.json', tmp / 'latest.json')
        shutil.copy(DATA / 'origination.json', tmp / 'origination.json')
        origination = json.loads((tmp / 'origination.json').read_text(encoding='utf-8'))
        target = mutate(origination)
        (tmp / 'origination.json').write_text(json.dumps(origination), encoding='utf-8')
        return tmp, target

    def test_a_changed_bookmaker_price_is_caught(self):
        def mutate(doc):
            for record in doc['matches']:
                orig = record.get('origination') or {}
                quotes = [q for q in (orig.get('quotes') or []) if isinstance(q, dict) and 'odds' in q]
                if quotes:
                    quotes[0]['odds'] = [1.02, 12.0]   # still a valid pair, different price
                    return str(record['id'])
            self.skipTest('no bookmaker row with saved decimal odds in this snapshot')

        tmp, fixture_id = self.edited_copy(mutate)
        report = check(tmp)
        self.assertIn(fixture_id, [f['fixture_id'] for f in report['failed']])

    def test_a_missing_source_link_is_caught(self):
        def mutate(doc):
            for record in doc['matches']:
                orig = record.get('origination')
                if orig:
                    orig['source_url'] = 'https://example.com/not-a-source'
                    return str(record['id'])
            self.skipTest('no originated row in this snapshot')

        tmp, fixture_id = self.edited_copy(mutate)
        report = check(tmp)
        failed = {f['fixture_id']: f['problems'] for f in report['failed']}
        self.assertIn('official_source_link', failed.get(fixture_id, []))


class NoNetworkTests(unittest.TestCase):
    def test_the_verifier_imports_no_http_client(self):
        for banned in ('import requests', 'import urllib', 'import httpx', 'from urllib'):
            self.assertNotIn(banned, SOURCE)
        self.assertNotIn('http.server', SOURCE)


if __name__ == '__main__':
    unittest.main()
