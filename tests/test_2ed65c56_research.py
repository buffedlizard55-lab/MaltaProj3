"""Regression checks for session arena-2ed65c56's dated coverage/line record.

The record is research evidence, so the tests are about honesty rather than
'does it render': every percentage must be reproducible from the decimal odds
stored beside it, a refused placeholder must carry no probability at all, and
the snapshot-membership flags must still agree with the published snapshot.

Nothing here reads the network and nothing here can turn a research value into
a priced pick: the record is only ever loaded by the builder as dated evidence.
"""
from __future__ import annotations

import json
import re
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'data/research/2ed65c56/live-coverage.json'
FLAGS = ROOT / 'data/research/2ed65c56/flags.json'
SNAPSHOT = ROOT / 'snapshot.json'
# The record's snapshot-membership flags are "as of" the snapshot it names. The
# root snapshot is republished every four hours, so the honest comparison is
# against that frozen copy -- not against whatever the site serves today, which
# would fail an unchanged, accurate record on the next publish.
FROZEN_SNAPSHOT = ROOT / 'tests/fixtures/published-snapshot-2026-10-23T20-10-00Z.json'

SEVERITIES = {'notice', 'warning', 'critical', 'info'}


def parse_ts(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def novig(decimal):
    inv = [1 / float(x) for x in decimal]
    total = sum(inv)
    return [round(i / total * 100, 1) for i in inv], round((total - 1) * 100, 2)


class RecordShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.fixtures = cls.record['live_fixtures']

    def test_observed_at_is_a_real_timestamp(self):
        self.assertIsNotNone(parse_ts(self.record['observed_at']))
        self.assertTrue(self.record['observed_at'].endswith('Z'))

    def test_every_card_has_two_teams_a_start_and_an_official_hotspawn_url(self):
        seen = set()
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture.get('id')):
                self.assertNotIn(fixture['id'], seen, 'duplicate Hotspawn id')
                seen.add(fixture['id'])
                self.assertEqual(len(fixture['teams']), 2)
                self.assertTrue(all(fixture['teams']))
                self.assertIsNotNone(parse_ts(fixture['starts_at']))
                url = fixture['hotspawn_url']
                self.assertTrue(url.startswith('https://www.hotspawn.com/matches/'))
                self.assertTrue(url.endswith('-' + fixture['id']), 'url must carry the fixture id')
                self.assertIn('-vs-', url)

    def test_counts_agree_with_the_rows(self):
        missing = [f for f in self.fixtures if not f['in_published_snapshot']]
        counts = self.record['counts']
        self.assertEqual(counts['live_future_fixtures'], len(self.fixtures))
        self.assertEqual(counts['in_published_snapshot'], len(self.fixtures) - len(missing))
        self.assertEqual(counts['missing_from_published'], len(missing))
        self.assertEqual(counts['missing_with_a_usable_external_line'],
                         sum(1 for f in missing if (f.get('line_observed') or {}).get('usable')))
        self.assertEqual(counts['missing_with_only_a_refused_placeholder'],
                         sum(1 for f in missing if (f.get('line_observed') or {}).get('usable') is False))

    def test_every_source_url_is_https(self):
        for url in self.record['source_urls']:
            self.assertTrue(url.startswith('https://'), url)
        for fixture in self.fixtures:
            line = fixture.get('line_observed')
            if line:
                self.assertTrue(line['source_url'].startswith('https://'))

    def test_snapshot_membership_matches_the_published_snapshot(self):
        frozen = json.loads(FROZEN_SNAPSHOT.read_text())
        self.assertEqual(frozen['generated_at'], self.record['published_site']['generated_at'],
                         'the frozen snapshot must be the one this record describes')
        published = {str(m['id']) for m in frozen['matches']}
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture['id']):
                self.assertEqual(fixture['in_published_snapshot'], fixture['id'] in published)
        # And the record stays honest about how old that observation is.
        self.assertLessEqual(parse_ts(frozen['generated_at']), parse_ts(self.record['observed_at']))


class LineArithmeticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.fixtures = {f['id']: f for f in cls.record['live_fixtures']}

    def test_no_probability_without_a_two_sided_line(self):
        for fixture in self.fixtures.values():
            line = fixture.get('line_observed')
            if line is None:
                self.assertNotIn('novig_percent', fixture)
                self.assertNotIn('guided_pick', fixture)
                continue
            if not line.get('usable'):
                # A refused placeholder must carry no probability, ever.
                self.assertNotIn('novig_percent', line)
                self.assertNotIn('guided_pick', line)
                self.assertTrue(line.get('reason'))

    def test_percentages_recompute_from_the_stored_decimal_odds(self):
        checked = 0
        for fixture in self.fixtures.values():
            line = fixture.get('line_observed')
            if not line or not line.get('usable'):
                continue
            pct, overround = novig(line['decimal'])
            with self.subTest(fixture=fixture['id']):
                self.assertEqual(len(line['decimal']), 2)
                self.assertAlmostEqual(pct[0], line['novig_percent'][0], places=1)
                self.assertAlmostEqual(pct[1], line['novig_percent'][1], places=1)
                self.assertAlmostEqual(overround, line['overround_percent'], places=1)
                self.assertAlmostEqual(sum(line['novig_percent']), 100.0, places=1)
                expected_pick = fixture['teams'][0] if pct[0] >= pct[1] else fixture['teams'][1]
                self.assertEqual(line['guided_pick'], expected_pick)
                self.assertEqual(line['guided_pick'], fixture['teams'][line['novig_percent'].index(max(line['novig_percent']))])
            checked += 1
        self.assertGreater(checked, 0, 'expected at least one usable two-sided line to verify')

    def test_identical_prices_are_never_treated_as_a_line(self):
        for fixture in self.fixtures.values():
            line = fixture.get('line_observed')
            if line and line['decimal'][0] == line['decimal'][1]:
                self.assertFalse(line['usable'], 'identical numbers on both sides are a placeholder')


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flags = json.loads(FLAGS.read_text())
        cls.record = json.loads(RECORD.read_text())
        cls.ids = {f['id'] for f in cls.record['live_fixtures']}

    def test_flags_are_unique_namespaced_and_sourced(self):
        seen = set()
        for flag in self.flags:
            with self.subTest(flag=flag.get('id')):
                self.assertTrue(flag['id'].startswith('2ed65c56-'))
                self.assertNotIn(flag['id'], seen)
                seen.add(flag['id'])
                self.assertIn(flag['severity'], SEVERITIES)
                self.assertTrue(flag['title'].strip())
                self.assertTrue(flag['detail'].strip())
                self.assertTrue(flag['source_urls'])
                for url in flag['source_urls']:
                    self.assertTrue(url.startswith('https://'), url)
                for match_id in flag['match_ids']:
                    self.assertRegex(str(match_id), r'^\d+$')

    def test_every_missing_card_is_named_by_the_coverage_flag(self):
        gap = next(f for f in self.flags if f['id'] == '2ed65c56-lobby-cards-missing-from-published')
        missing = [f['id'] for f in self.record['live_fixtures'] if not f['in_published_snapshot']]
        self.assertEqual(sorted(gap['match_ids']), sorted(missing))
        detail = gap['detail']
        for match_id in missing:
            self.assertIn(match_id, detail, 'the flag body must name the card it concerns')

    def test_guided_pick_flags_quote_the_same_numbers_as_the_record(self):
        by_id = {f['id']: f for f in self.record['live_fixtures']}
        for flag in self.flags:
            if not flag['id'].startswith('2ed65c56-guided-pick-'):
                continue
            line = None
            for match_id in flag['match_ids']:
                candidate = (by_id.get(match_id) or {}).get('line_observed')
                if candidate and candidate.get('usable'):
                    line = candidate
            if not line:
                continue
            with self.subTest(flag=flag['id']):
                self.assertIn(line['guided_pick'], flag['title'])
                self.assertIn('%.1f%%' % max(line['novig_percent']), flag['title'])
                for decimal in line['decimal']:
                    self.assertIn(str(decimal), flag['detail'])


class WordingTest(unittest.TestCase):
    def test_no_crowd_percentage_is_ever_used_as_a_probability(self):
        text = (ROOT / 'data/research/2ed65c56/report.md').read_text()
        self.assertIn('never', text)
        self.assertIn('% picked', text)
        # The record must not carry a Hotspawn crowd figure as a probability field.
        record = json.loads(RECORD.read_text())
        blob = json.dumps(record)
        self.assertNotIn('picked_percent', blob)

    def test_report_links_the_record_and_the_flags(self):
        text = (ROOT / 'data/research/2ed65c56/report.md').read_text()
        self.assertIn('live-coverage.json', text)
        self.assertIn('flags.json', text)
        links = re.findall(r'https://[^\s)\]]+', text)
        self.assertGreaterEqual(len(links), 12)
        record = json.loads(RECORD.read_text())
        # Every card the report tabulates must be named; the in-snapshot rows are
        # summarised by count instead of being re-tabulated.
        for fixture in record['live_fixtures']:
            if not fixture['in_published_snapshot']:
                self.assertIn(fixture['id'], text)
        self.assertIn(str(record['counts']['live_future_fixtures']), text)


if __name__ == '__main__':
    unittest.main()
