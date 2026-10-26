"""Session arena-b3e91409 — the independent replay fails closed in every direction.

The brief's verification rule is: every table row links an official source, every published number
can be checked, and a value that cannot be confirmed stays blank and flagged. These tests pin that
rule on the checker itself, with no network:

* all four published probability shapes (exchange midpoints as one quote per side, exchange
  midpoints as one quote carrying both sides, a de-vigged bookmaker pair, and Valve's fit.js
  logistic) replay from the row's own inputs;
* a hand-edited probability, a flipped pick, a broken source link, a pair that no longer sums to 1,
  a blank row that carries a pick or publishes no trail, a community "% picked" field and a
  bookmaker margin outside policy are each reported as an error;
* a live fixture with no published row is a coverage gap, and `--check` exits non-zero for both
  errors and gaps while a clean run exits zero.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import b3e91409_verify as verify


def stamp(hours_ago=1):
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime('%Y-%m-%dT%H:%M:%SZ')


def market_row(fixture_id='900001', shape='per-side'):
    if shape == 'per-side':
        quotes = [{'bid': 0.18, 'ask': 0.22, 'midpoint': 0.2},
                  {'bid': 0.78, 'ask': 0.82, 'midpoint': 0.8}]
    else:
        quotes = [{'bid': [0.18, 0.78], 'ask': [0.22, 0.82], 'spread': 0.04}]
    return {
        'id': fixture_id, 'teams': [{'name': 'Alpha'}, {'name': 'Beta'}], 'starts_at': '2026-12-01T10:00:00Z',
        'availability': 'open', 'pick_index': 1, 'research': [{'stage': 'Primary', 'source_url': 'https://polymarket.com/event/x'}],
        'origination': {'method': 'market', 'probabilities': [0.2, 0.8], 'fair_decimal': [5.0, 1.25],
                        'source_url': 'https://polymarket.com/event/x', 'observed_at': stamp(),
                        'quotes': quotes, 'limitations': ['Exchange midpoint, not an execution price.']},
    }


def bookmaker_row(fixture_id='900002'):
    odds = [1.61, 2.18]
    implied = [1 / odds[0], 1 / odds[1]]
    total = sum(implied)
    probs = [round(implied[0] / total, 8), round(implied[1] / total, 8)]
    return {
        'id': fixture_id, 'teams': [{'name': 'Gamma'}, {'name': 'Delta'}], 'starts_at': '2026-12-01T11:00:00Z',
        'availability': 'open', 'pick_index': 0, 'research': [{'stage': 'Book', 'source_url': 'https://thunderpick.io/x'}],
        'origination': {'method': 'bookmaker', 'probabilities': probs, 'fair_decimal': [round(1 / p, 3) for p in probs],
                        'source_url': 'https://thunderpick.io/api/matches', 'observed_at': stamp(),
                        'quotes': [{'odds': odds, 'probabilities': probs}], 'limitations': ['One book only.']},
    }


def model_row(fixture_id='900003'):
    points_a, points_b, rd = 1110.0, 1383.0, 75.0
    import math
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)
    p = 1 / (1 + 10 ** (g * (points_b - points_a) / 400))
    probs = [round(p, 8), round(1 - p, 8)]
    return {
        'id': fixture_id, 'teams': [{'name': 'Epsilon'}, {'name': 'Zeta'}], 'starts_at': '2026-12-01T12:00:00Z',
        'availability': 'open', 'pick_index': 1, 'research': [{'stage': 'Valve', 'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'}],
        'origination': {'method': 'model', 'probabilities': probs, 'fair_decimal': [round(1 / x, 3) for x in probs],
                        'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                        'observed_at': stamp(), 'quotes': [], 'rd_assumption': rd,
                        'inputs': [{'points': points_a}, {'points': points_b}], 'limitations': ['Research model.']},
    }


def blank_row(fixture_id='900004'):
    return {
        'id': fixture_id, 'teams': [{'name': 'Eta'}, {'name': 'Theta'}], 'starts_at': '2026-12-01T13:00:00Z',
        'availability': 'open', 'pick_index': None,
        'research': [{'stage': 'Primary', 'source_url': 'https://polymarket.com/esports/cs2', 'status': 'unresolved'}],
        'origination': {},
    }


def write_case(directory, rows, snapshot_ids=None, live=None):
    origination = {'generated_at': stamp(), 'counts': {'active': len(rows)}, 'matches': rows}
    (directory / 'origination.json').write_text(json.dumps(origination), encoding='utf-8')
    snapshot = {'generated_at': stamp(), 'matches': [{'id': r['id'], 'availability': 'open'} for r in rows]}
    (directory / 'snapshot.json').write_text(json.dumps(snapshot), encoding='utf-8')
    live_dir = directory / 'live'
    live_dir.mkdir(exist_ok=True)
    if live is not None:
        (live_dir / 'analysis.json').write_text(json.dumps({'observed_at': stamp(), 'counts': {}, 'fixtures': live}), encoding='utf-8')
    return ['--origination', str(directory / 'origination.json'), '--snapshot', str(directory / 'snapshot.json'),
            '--report-dir', str(directory / 'report'), '--live-dir', str(live_dir)]


def report(directory):
    return json.loads((directory / 'report' / 'verification.json').read_text(encoding='utf-8'))


class ReplayTests(unittest.TestCase):
    def test_every_published_shape_replays(self):
        for row in (market_row(shape='per-side'), market_row('900011', shape='both-sides'),
                    bookmaker_row(), model_row()):
            findings, record = verify.check_row(row)
            self.assertEqual([f for f in findings if f[0] == 'error'], [], row['id'])
            self.assertEqual(record['verdict'], 'verified', row['id'])

    def test_market_midpoints_are_normalised_not_taken_raw(self):
        row = market_row()
        row['origination']['quotes'] = [{'bid': 0.10, 'ask': 0.20}, {'bid': 0.70, 'ask': 0.80}]
        findings, record = verify.check_row(row)
        # midpoints 0.15 + 0.75 = 0.90, normalised to 1/6 and 5/6 - not the published 0.2/0.8
        self.assertEqual([f[0] for f in findings if f[0] == 'error'], ['error'])
        self.assertEqual(record['verdict'], 'mismatch')

    def test_one_sided_book_is_refused(self):
        row = market_row()
        row['origination']['quotes'][0]['bid'] = 0.0
        findings, _ = verify.check_row(row)
        self.assertTrue(any('valid two-sided book' in f[2] for f in findings), findings)

    def test_bookmaker_margin_outside_policy_is_refused(self):
        row = bookmaker_row()
        row['origination']['quotes'][0]['odds'] = [1.01, 1.01]
        findings, record = verify.check_row(row)
        self.assertTrue(any('margin' in f[2] for f in findings), findings)
        self.assertEqual(record['verdict'], 'unreplayable')

    def test_model_uses_the_published_points_and_rd(self):
        row = model_row()
        row['origination']['inputs'][1]['points'] = 1200.0
        findings, record = verify.check_row(row)
        self.assertEqual(record['verdict'], 'mismatch')


class FailClosedTests(unittest.TestCase):
    def assert_error(self, row, needle):
        findings, _ = verify.check_row(row)
        messages = [f[2] for f in findings if f[0] == 'error']
        self.assertTrue(any(needle in m for m in messages), messages)

    def test_hand_edited_probability(self):
        row = market_row()
        row['origination']['probabilities'] = [0.25, 0.75]
        self.assert_error(row, 'differs from the replay')

    def test_probabilities_must_sum_to_one(self):
        row = market_row()
        row['origination']['probabilities'] = [0.2, 0.7]
        self.assert_error(row, 'sum to')

    def test_pick_must_be_the_strict_favourite(self):
        row = market_row()
        row['pick_index'] = 0
        self.assert_error(row, 'strict favourite')

    def test_source_link_must_be_https_and_external(self):
        row = market_row()
        row['origination']['source_url'] = 'http://play.hotspawn.com/lobby'
        self.assert_error(row, 'not external')

    def test_observation_time_cannot_be_in_the_future(self):
        row = market_row()
        row['origination']['observed_at'] = (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.assert_error(row, 'future')

    def test_fair_decimal_must_match_the_probabilities(self):
        row = market_row()
        row['origination']['fair_decimal'] = [4.0, 1.25]
        self.assert_error(row, 'fair_decimal')

    def test_unknown_method_is_an_error(self):
        row = market_row()
        row['origination']['method'] = 'vibes'
        self.assert_error(row, 'unknown analysis method')

    def test_blank_row_with_a_pick_is_an_error(self):
        row = blank_row()
        row['pick_index'] = 0
        self.assert_error(row, 'pick_index')

    def test_blank_row_without_a_trail_is_an_error(self):
        row = blank_row()
        row['research'] = []
        self.assert_error(row, 'no research trail')

    def test_blank_row_research_needs_a_source_link(self):
        row = blank_row()
        row['research'] = [{'stage': 'Primary', 'status': 'unresolved'}]
        self.assert_error(row, 'no source URL')

    def test_community_percentage_is_an_error(self):
        row = market_row()
        row['origination']['participants0_picked_percent'] = 75
        hits = verify.find_crowd_fields([row])
        self.assertTrue(hits, 'the crowd-field scanner found nothing')


class CoverageTests(unittest.TestCase):
    def test_live_fixture_without_a_row_is_a_coverage_gap_and_fails_check(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            live = [{'id': '900009', 'teams': ['Live One', 'Live Two'], 'starts_at': '2026-12-01T14:00:00Z',
                     'competition': 'CCT', 'method': 'market', 'probabilities': [0.4, 0.6], 'pick': 'Live Two'}]
            argv = write_case(directory, [market_row()], live=live)
            self.assertEqual(verify.main(argv + ['--check']), 1)
            data = report(directory)
            self.assertEqual(data['summary']['coverage_gaps'], 1)
            self.assertEqual(data['coverage_gaps'][0]['id'], '900009')
            self.assertEqual(data['coverage_gaps'][0]['source_url'],
                             'https://play.hotspawn.com/cs2-pickems#fixture-900009')

    def test_snapshot_open_fixture_without_a_pick_row_is_an_error(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            argv = write_case(directory, [market_row()])
            snapshot = json.loads((directory / 'snapshot.json').read_text())
            snapshot['matches'].append({'id': '900010', 'availability': 'open'})
            (directory / 'snapshot.json').write_text(json.dumps(snapshot))
            self.assertEqual(verify.main(argv + ['--check']), 1)
            self.assertTrue(any(f['id'] == '900010' for f in report(directory)['findings']))

    def test_clean_build_exits_zero_with_check(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            argv = write_case(directory, [market_row(), bookmaker_row(), model_row(), blank_row()])
            self.assertEqual(verify.main(argv + ['--check']), 0)
            data = report(directory)
            self.assertEqual(data['summary']['errors'], 0)
            self.assertEqual(data['summary']['verified'], 3)
            self.assertEqual(data['summary']['blank'], 1)
            self.assertTrue((directory / 'report' / 'verification.md').exists())

    def test_tampered_build_exits_non_zero_without_check_too_when_asked(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            row = market_row()
            row['pick_index'] = 0
            argv = write_case(directory, [row])
            self.assertEqual(verify.main(argv + ['--check']), 1)
            self.assertEqual(verify.main(argv), 0)  # report-only mode writes the finding, exit stays 0


class PublishedDossierTests(unittest.TestCase):
    """The evidence this session publishes must itself obey the brief's rules."""

    def test_review_register_is_wired_and_every_item_links_a_source(self):
        from scripts.review_register import REGISTERS
        rel = 'research/b3e91409/repo-review.json'
        self.assertIn(rel, REGISTERS)
        data = json.loads((Path('data') / rel).read_text(encoding='utf-8'))
        self.assertEqual(data['session'], 'arena-b3e91409')
        self.assertTrue(data['items'])
        for item in data['items']:
            for key in ('id', 'area', 'status', 'finding', 'handling', 'evidence'):
                self.assertIn(key, item, item.get('id'))
            self.assertTrue(item['evidence'], item['id'])
            for evidence in item['evidence']:
                self.assertTrue(evidence['url'].startswith('https://'), (item['id'], evidence['url']))
                self.assertTrue(evidence.get('detail'), item['id'])

    def test_live_dossier_has_a_source_behind_every_probability(self):
        path = Path('data/research/b3e91409/live/analysis.json')
        if not path.exists():
            self.skipTest('live capture is produced on a runner')
        dossier = json.loads(path.read_text(encoding='utf-8'))
        self.assertTrue(dossier['fixtures'])
        self.assertEqual(dossier['counts']['open'], len(dossier['fixtures']))
        self.assertEqual(dossier['counts']['unresolved'],
                         sum(1 for f in dossier['fixtures'] if f['probabilities'] is None))
        for fixture in dossier['fixtures']:
            self.assertIn(fixture['method'], (None, 'market', 'bookmaker', 'hltv-rank-elo', 'valve-glicko'),
                          fixture['id'])
            if fixture['probabilities']:
                self.assertAlmostEqual(sum(fixture['probabilities']), 1.0, places=6, msg=fixture['id'])
                self.assertIn(fixture['pick_index'], (0, 1), fixture['id'])
                self.assertEqual(fixture['pick'], fixture['teams'][fixture['pick_index']], fixture['id'])
                source = (fixture['quotes'][0]['url'] if fixture['quotes'] else
                          (fixture['model'] or {}).get('url'))
                self.assertTrue(source and source.startswith('https://'), fixture['id'])
            else:
                self.assertTrue(fixture['limitations'], fixture['id'])
            self.assertFalse(verify.find_crowd_fields(fixture), fixture['id'])

    def test_live_capture_manifest_records_hash_and_time_for_every_source(self):
        path = Path('data/research/b3e91409/live/manifest.json')
        if not path.exists():
            self.skipTest('live capture is produced on a runner')
        entries = json.loads(path.read_text(encoding='utf-8'))
        self.assertTrue(entries)
        for entry in entries:
            self.assertTrue(entry['url'].startswith('https://'), entry['url'])
            self.assertRegex(entry['observed_at'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
            if entry['status'] == 'ok':
                self.assertTrue(entry.get('response_sha256'), entry['id'])
                self.assertTrue(entry.get('bytes'), entry['id'])


if __name__ == '__main__':
    unittest.main()
