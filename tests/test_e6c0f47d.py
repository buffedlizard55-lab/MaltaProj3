"""Session e6c0f47d: first-party unresolved-pick dossier and its publication hook.

Every external URL in the dossier and flags must pass the row-source audit's
official-host allow-list, and the review page must render the new findings.
Values are never inferred: fixtures carry explicit verdicts, and blank start
times are represented as null, not guesses.
"""
import json
import unittest
from pathlib import Path

from scripts import audit_rows as audit

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data' / 'research' / 'e6c0f47d' / 'unresolved-review.json'
FLAGS = ROOT / 'data' / 'research' / 'e6c0f47d' / 'flags.json'

EXPECTED_UNRESOLVED = {'1079167', '1079170', '1081126', '1081502', '1081526', '1081527', '1081532'}
VERDICTS = {'resolves-at-next-refresh', 'blocked'}


def load(path):
    return json.loads(path.read_text())


def external_urls(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ('source_url', 'market_url', 'event_url', 'results_source') and isinstance(value, str):
                yield value
            else:
                yield from external_urls(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from external_urls(item)


class DossierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load(DOSSIER)
        cls.flags = load(FLAGS)

    def test_all_seven_unresolved_fixtures_covered_exactly_once(self):
        ids = [f['id'] for f in self.data['fixtures']]
        self.assertEqual(set(ids), EXPECTED_UNRESOLVED)
        self.assertEqual(len(ids), len(set(ids)), 'duplicate fixture entries')

    def test_verdicts_are_explicit_and_known(self):
        for fixture in self.data['fixtures']:
            self.assertIn(fixture['verdict'], VERDICTS, fixture['id'])
            self.assertTrue(fixture['stages'], fixture['id'])
            if fixture['verdict'] == 'blocked':
                self.assertTrue(fixture.get('blocked_reason'), fixture['id'])
            else:
                probs = fixture.get('expected_probabilities_local_replay')
                self.assertIsNotNone(probs, fixture['id'])
                self.assertAlmostEqual(sum(probs), 1.0, places=3, msg=fixture['id'])
                self.assertIn(fixture.get('expected_pick'), fixture['teams'], fixture['id'])

    def test_unverified_start_times_are_blank_not_inferred(self):
        for fixture in self.data['fixtures']:
            if fixture.get('starts_at') is None:
                self.assertIn(fixture['id'], {'1081126', '1079170', '1081502', '1081526', '1081527'})

    def test_every_external_source_is_official(self):
        for url in dict.fromkeys(external_urls(self.data)):
            self.assertTrue(audit.is_official(url), f'dossier url not official: {url}')
        for url in dict.fromkeys(external_urls(self.flags)):
            self.assertTrue(audit.is_official(url), f'flag url not official: {url}')

    def test_flags_schema_matches_the_review_table_contract(self):
        ids = [f['id'] for f in self.flags]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 8)
        for f in self.flags:
            self.assertIn(f['severity'], ('notice', 'warning'), f['id'])
            for key in ('id', 'title', 'detail', 'match_ids', 'source_urls'):
                self.assertIn(key, f, f['id'])
            self.assertTrue(f['source_urls'], f['id'])

    def test_day_three_section_claims_no_result(self):
        day3 = self.data['day_three']
        self.assertIn('No 16 October 2026 results', day3['results_status'])
        fixtures = {f['hltv_match_id'] for f in day3['fixtures']}
        self.assertEqual(fixtures, {2399412, 2399413})
        for f in day3['fixtures']:
            self.assertTrue(f['implied_start_utc'].startswith('2026-10-16T'))
            self.assertTrue(audit.is_official(f['source_url']))


class ReviewPagePublicationTests(unittest.TestCase):
    def test_review_page_renders_the_new_flags(self):
        import tempfile
        from scripts.build import build
        with tempfile.TemporaryDirectory() as tmp:
            build(ROOT / 'data', Path(tmp) / 'site')
            html = (Path(tmp) / 'site' / 'review' / 'index.html').read_text()
            for flag in load(FLAGS):
                self.assertIn(f'id="flag-{flag["id"]}"', html, flag['id'])
            self.assertIn('data/research/e6c0f47d/unresolved-review.json', html, 'dossier link surfaced on the review page')
