"""Session arena-e619b921: dated live-lobby coverage record and its review flags.

Presentation and evidence only. These tests never read the live network, never
depend on the wall clock, and never assert anything about a snapshot that a
future refresh will replace. They pin the properties of the *record*:

* it is eligible for the live-coverage loader (the loader ignores a record whose
  fixtures are nested anywhere but ``live_fixtures``);
* its counts add up;
* every row it lists links a first-party Hotspawn page, and every uncovered row
  carries a line-research entry that quotes a source verbatim;
* a two-sided identical price is never marked usable;
* no probability or pick is written by the record itself;
* the rendered gap section lists exactly the uncovered rows when the snapshot
  does not contain them, and drops them when it does.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.build import live_coverage_gaps, load_live_coverage

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'data/research/e619b921/live-coverage.json'
MARKDOWN = ROOT / 'data/research/e619b921/live-coverage.md'
FLAGS = ROOT / 'data/research/e619b921/flags.json'


def record():
    return json.loads(RECORD.read_text())


def covered_rows():
    return [f for f in record()['live_fixtures'] if f.get('in_published_snapshot')]


def uncovered_rows():
    return [f for f in record()['live_fixtures'] if not f.get('in_published_snapshot')]


class TheRecordIsEligibleForTheLoader(unittest.TestCase):
    """A record nested under any other key renders nothing at all."""

    def _write(self, directory, payload):
        target = Path(directory) / 'research' / 'e619b921'
        target.mkdir(parents=True, exist_ok=True)
        (target / 'live-coverage.json').write_text(json.dumps(payload))
        return target / 'live-coverage.json'

    def test_the_shipped_record_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, record())
            loaded = load_live_coverage(Path(tmp))
            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded['live_fixtures']), 25)
            self.assertEqual(loaded['_record_path'], 'research/e619b921/live-coverage.json')

    def test_fixtures_nested_under_hotspawn_are_not_eligible(self):
        nested = dict(record())
        nested['hotspawn'] = dict(nested['hotspawn'])
        nested['hotspawn']['fixtures'] = nested.pop('live_fixtures')
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, nested)
            self.assertIsNone(load_live_coverage(Path(tmp)))

    def test_an_unparseable_observed_at_is_not_eligible(self):
        broken = dict(record(), observed_at='sometime yesterday')
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, broken)
            self.assertIsNone(load_live_coverage(Path(tmp)))

    def test_the_markdown_sits_next_to_the_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, record())
            path.with_suffix('.md').write_text('# dossier\n')
            loaded = load_live_coverage(Path(tmp))
            self.assertEqual(loaded['_markdown_path'], 'research/e619b921/live-coverage.md')


class TheCountsAddUp(unittest.TestCase):
    def test_the_three_groups_account_for_every_row_once(self):
        rows = record()['live_fixtures']
        gone = record()['published_rows_started_before_observation']
        self.assertEqual(len(rows), 25)
        self.assertEqual(len(covered_rows()), 16)
        self.assertEqual(len(uncovered_rows()), 9)
        self.assertEqual(len(covered_rows()) + len(gone), 19,
                         'the published snapshot had 19 rows: 16 still live + 3 started')
        self.assertEqual(record()['comparison']['live_cards_not_in_published_snapshot'], 9)
        ids = [f['id'] for f in rows] + [f['id'] for f in gone]
        self.assertEqual(len(ids), len(set(ids)), 'a fixture is listed twice')

    def test_the_published_counts_match_the_layers_they_came_from(self):
        counts = record()['published_site']['counts_read']
        self.assertEqual(counts['active'], counts['with_pick'])
        self.assertEqual(counts['external_line'] + counts['research_model'], counts['active'])
        self.assertEqual(counts['external_line'], 12)
        self.assertEqual(counts['research_model'], 7)

    def test_observed_at_is_iso_utc(self):
        stamp = record()['observed_at']
        self.assertTrue(stamp.endswith('Z'))
        datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')


class EveryRowLinksItsSource(unittest.TestCase):
    def test_every_live_row_has_a_hotspawn_page_with_its_own_id(self):
        for fixture in record()['live_fixtures']:
            url = fixture.get('hotspawn_url') or ''
            self.assertTrue(url.startswith('https://www.hotspawn.com/matches/'), fixture['id'])
            self.assertTrue(url.endswith(f"-{fixture['id']}"), url)

    def test_every_uncovered_row_carries_verbatim_line_research(self):
        usable = 0
        for fixture in uncovered_rows():
            entry = fixture.get('line_research')
            self.assertIsInstance(entry, dict, fixture['id'])
            self.assertTrue(entry['source_url'].startswith('https://'), fixture['id'])
            self.assertTrue(str(entry['quote']).strip(), fixture['id'])
            self.assertIn('usable', entry, fixture['id'])
            if entry['usable']:
                usable += 1
                self.assertNotIn('1.8 / 1.8', entry['quote'],
                                 'an identical two-sided pair is not a market')
        self.assertEqual(usable, 4)
        self.assertEqual(len(uncovered_rows()) - usable, 5)

    def test_every_source_url_in_the_record_is_https(self):
        urls = list(record()['source_urls'])
        for group in ('hotspawn', 'published_site', 'comparison'):
            urls.extend(record()[group].get('source_urls', []))
        for fixture in record()['live_fixtures']:
            urls.append(fixture['hotspawn_url'])
            if fixture.get('line_research'):
                urls.append(fixture['line_research']['source_url'])
        self.assertTrue(urls)
        for url in urls:
            self.assertTrue(str(url).startswith('https://'), url)

    def test_derived_start_times_are_labelled(self):
        for fixture in uncovered_rows():
            basis = fixture.get('starts_at_basis')
            self.assertIn(basis, {'verified', 'lobby_card_us_eastern_plus_4h'}, fixture['id'])
            self.assertTrue(fixture.get('lobby_card_time'), fixture['id'])


class NoProbabilityIsWrittenHere(unittest.TestCase):
    def test_the_record_has_no_probability_or_pick_field_of_its_own(self):
        payload = record()
        for banned in ('probability', 'probabilities', 'pick', 'pick_index', 'edge'):
            self.assertNotIn(banned, payload)
        for fixture in payload['live_fixtures']:
            for banned in ('probability', 'probabilities', 'pick', 'pick_index'):
                self.assertNotIn(banned, fixture)
        self.assertIn('No probability, pick or alias is written', payload['role'])


class TheGapSectionRendersTheRecord(unittest.TestCase):
    def _snapshot(self, ids):
        return {
            'matches': [
                {'id': str(i), 'teams': [{'name': f'T{i}a'}, {'name': f'T{i}b'}]}
                for i in ids
            ],
            'complete_picks': {'matches': []},
        }

    def test_nine_rows_render_when_the_snapshot_lacks_them(self):
        data = self._snapshot([f['id'] for f in covered_rows()])
        data['_live_coverage'] = record()
        html = live_coverage_gaps(data, '')
        self.assertIn('9 missing at that observation', html)
        for fixture in uncovered_rows():
            self.assertIn(fixture['hotspawn_url'], html)
        self.assertIn('2026-10-24T06:35:00Z', html)

    def test_the_rows_drop_out_once_the_snapshot_contains_them(self):
        ids = [f['id'] for f in covered_rows()] + [f['id'] for f in uncovered_rows()]
        data = self._snapshot(ids)
        data['_live_coverage'] = record()
        html = live_coverage_gaps(data, '')
        self.assertIn('0 missing at that observation', html)
        self.assertIn('Every live lobby fixture in that research window', html)

    def test_a_pair_match_also_drops_the_row(self):
        data = self._snapshot([f['id'] for f in covered_rows()])
        data['complete_picks'] = {'matches': [
            {'id': None, 'teams': [{'name': 'Spirit Academy'}, {'name': 'LFO 10'}]}
        ]}
        data['_live_coverage'] = record()
        html = live_coverage_gaps(data, '')
        self.assertIn('8 missing at that observation', html)
        self.assertNotIn('1081156', html)


class TheFlagsArePublishable(unittest.TestCase):
    def test_flags_match_the_review_schema(self):
        findings = json.loads(FLAGS.read_text())
        self.assertGreaterEqual(len(findings), 3)
        ids = [f['id'] for f in findings]
        self.assertEqual(len(ids), len(set(ids)))
        for finding in findings:
            self.assertTrue(finding['id'].startswith('e619b921-'), finding['id'])
            self.assertIn(finding['severity'], {'notice', 'warning'})
            self.assertTrue(finding['title'].strip())
            self.assertTrue(finding['detail'].strip())
            self.assertTrue(finding['source_urls'])
            for url in finding['source_urls']:
                self.assertTrue(url.startswith('https://'), url)
            self.assertIsInstance(finding['match_ids'], list)

    def test_every_uncovered_fixture_is_named_by_the_coverage_flag(self):
        findings = json.loads(FLAGS.read_text())
        flag = next(f for f in findings if f['id'] == 'e619b921-nine-live-cards-uncovered')
        for fixture in uncovered_rows():
            self.assertIn(fixture['id'], flag['match_ids'])
            self.assertIn(fixture['id'], flag['detail'])

    def test_the_markdown_names_every_uncovered_fixture(self):
        text = MARKDOWN.read_text()
        for fixture in uncovered_rows():
            self.assertIn(fixture['id'], text)
        self.assertIn('No probability, pick or alias is written', text)

    def test_the_one_dot_zero_price_finding_is_published(self):
        """A decimal leg of 1.00 is not a market price, whatever the arithmetic says."""
        findings = json.loads(FLAGS.read_text())
        flag = next(f for f in findings
                    if f['id'] == 'e619b921-thunderpick-decimal-price-of-1-00-published')
        self.assertEqual(flag['match_ids'], ['1082860'])
        self.assertIn('1.00', flag['detail'])
        self.assertIn('92.3', flag['detail'])
        self.assertIn('needs-review', flag['detail'])
        self.assertTrue(all(u.startswith('https://') for u in flag['source_urls']))

    def test_the_dossier_reports_the_one_dot_zero_price(self):
        text = MARKDOWN.read_text()
        self.assertIn('line 1.00 / 12.00', text)
        self.assertIn('92.3%', text)

    def test_the_verification_record_carries_the_same_finding(self):
        verification = json.loads(
            (ROOT / 'data/research/e619b921/verification.json').read_text())
        ids = [c['id'] for c in verification['checks']]
        self.assertIn('V9', ids)
        check = next(c for c in verification['checks'] if c['id'] == 'V9')
        self.assertEqual(check['result'], 'confirmed-with-defect')
        self.assertIn('0.92308', check['detail'])


if __name__ == '__main__':
    unittest.main()
