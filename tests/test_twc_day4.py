"""Day-4 identity gates, original replay and time-safe rendering."""
import copy
import gzip
import hashlib
import json
import re
import tempfile
from statistics import median
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from scripts import twc_research, build_twc
from scripts.audit_rows import audit_html
from scripts.domain import timestamp, iso
from tests.test_twc import example_data

NOW = timestamp('2026-10-16T20:00:00Z')
SOURCE = 'https://www.hltv.org/matches/123/a-vs-b-thunderpick-world-championship-2026'


def example():
    d = example_data()
    d['inventory_observed_at'] = d['complete_picks']['source_snapshot_at'] = iso(NOW)
    for m, c in zip(d['matches'], d['complete_picks']['matches']):
        m['starts_at'] = c['starts_at'] = m['starts_at'].replace('2026-10-16', '2026-10-17')
        m['locks_at'] = c['locks_at'] = m['locks_at'].replace('2026-10-16', '2026-10-17')
        c['origination']['observed_at'] = iso(NOW)
    return d


def record(names=None, start='2026-10-17T14:00:00Z'):
    return {'source_url': SOURCE, 'observed_at': iso(NOW), 'facts': {
        'teams': names or ['Aurora', '9z'], 'starts_at': start,
        'event_url': twc_research.EVENT_URL, 'finished': False, 'score': None, 'maps': []}}


class Day4Canonical(unittest.TestCase):
    def setUp(self):
        self.d = example()
        self.research = {'pages': [record()], 'target_day': twc_research.TARGET_DAY}
        self.p = patch('scripts.twc_research.load', side_effect=lambda source: copy.deepcopy(self.research))
        self.p.start(); self.addCleanup(self.p.stop)

    def derive(self, now=NOW):
        return twc_research.derive_day4(self.d, Path('data'), now)

    def test_every_day4_hotspawn_fixture_is_kept_even_without_hltv(self):
        rows = self.derive()['matches']
        self.assertEqual(len(rows), 2)
        self.assertIsNotNone(rows[0]['hltv']); self.assertIsNone(rows[1]['hltv'])
        for row, canonical in zip(rows, self.d['complete_picks']['matches']):
            self.assertEqual(row['analysis'], canonical['origination'])
            self.assertTrue(row['state']['current'])
        self.assertEqual([r['pick'] for r in rows], ['Aurora', 'Legacy'])

    def test_no_result_is_inferred_from_past_start(self):
        self.research['pages'].append(record(start='2026-10-16T14:00:00Z'))
        result = self.derive()['day3_results'][0]
        self.assertIsNone(result['score']); self.assertFalse(result['finished'])

    def test_time_or_opponent_mismatch_does_not_copy_a_line(self):
        for r in [record(start='2026-10-17T14:01:00Z'), record(names=['Aurora', 'Legacy'])]:
            self.research['pages'] = [r]
            result = self.derive()
            self.assertIsNone(result['matches'][0]['hltv'])
            self.assertEqual(len(result['not_in_hotspawn_snapshot']), 1)
            self.assertNotIn('analysis', result['not_in_hotspawn_snapshot'][0])

    def test_ambiguous_hltv_join_is_not_selected(self):
        self.research['pages'].append(record())
        self.assertIsNone(self.derive()['matches'][0]['hltv'])

    def test_missing_line_stays_blank_not_half_or_historical_quote(self):
        c = self.d['complete_picks']['matches'][0]
        c['origination'] = c['pick_index'] = None
        row = self.derive()['matches'][0]
        self.assertIsNone(row['analysis']); self.assertIsNone(row['pick'])
        self.assertIsNone(row['alternative']); self.assertEqual(row['state']['status'], 'unresolved')
        soup = BeautifulSoup(build_twc.render_day4(self.derive(), '../'), 'html.parser')
        self.assertEqual([x.text for x in soup.select('.twc-day4-card')[0].select('.twc-prob strong')], ['—', '—'])

    def test_snapshots_and_directions_cannot_drift(self):
        self.d['complete_picks']['matches'][0]['pick_index'] = 1
        with self.assertRaises(ValueError): self.derive()
        self.d = example(); self.d['complete_picks']['source_snapshot_at'] = iso(NOW - timedelta(minutes=1))
        with self.assertRaises(ValueError): self.derive()
        self.d = example(); self.d['complete_picks']['matches'][0]['locks_at'] = None
        with self.assertRaises(ValueError): self.derive()

    def test_safety_rejects_bad_lock_status_future_quote_and_stale_line(self):
        for kind in ['stale', 'future', 'missing-lock', 'unknown-status', 'lock-after-start', 'locked', 'incomplete']:
            self.d = example()
            c, m = self.d['complete_picks']['matches'][0], self.d['matches'][0]
            if kind == 'stale': c['origination']['observed_at'] = iso(NOW - timedelta(hours=9))
            if kind == 'future': c['origination']['observed_at'] = iso(NOW + timedelta(minutes=6))
            if kind == 'missing-lock': c['locks_at'] = m['locks_at'] = None
            if kind == 'unknown-status': c['availability'] = m['availability'] = 'unknown'
            if kind == 'locked': c['availability'] = m['availability'] = 'locked'
            if kind == 'lock-after-start': c['locks_at'] = m['locks_at'] = '2026-10-17T15:00:00Z'
            if kind == 'incomplete': self.d['coverage_complete'] = False
            row = self.derive()['matches'][0]
            self.assertFalse(row['state']['current'], kind); self.assertIsNone(row['alternative'], kind)
            self.assertIsNotNone(row['analysis'], kind)

    def test_model_cannot_be_an_optional_upset(self):
        self.d['complete_picks']['matches'][0]['origination']['method'] = 'model'
        self.assertIsNone(self.derive()['matches'][0]['alternative'])

    def test_expiry_preserves_estimate_and_retires_choice_without_javascript(self):
        r = self.derive(NOW + timedelta(hours=9))
        self.assertTrue(all(not m['state']['current'] for m in r['matches']))
        soup = BeautifulSoup(build_twc.render_day4(r, '../'), 'html.parser')
        self.assertTrue(all(n.has_attr('hidden') for n in soup.select('[data-current-only]')))
        self.assertTrue(all(not n.has_attr('hidden') for n in soup.select('[data-historical-only]')))
        self.assertEqual(audit_html(str(soup), 'twc-picks/index.html')['violation'], 0)

    def test_team_order_keeps_canonical_probability_meaning(self):
        m, c = self.d['matches'][0], self.d['complete_picks']['matches'][0]
        m['teams'] = c['teams'] = list(reversed(m['teams']))
        c['origination']['probabilities'].reverse(); c['pick_index'] = 1
        r = self.derive()['matches'][0]
        self.assertEqual(r['pick'], 'Aurora'); self.assertEqual(r['analysis']['probabilities'], [0.31, 0.69])


class SourceReplay(unittest.TestCase):
    def test_discovery_never_follows_arbitrary_links(self):
        markup = '<a href="/matches/123/a-vs-b-thunderpick-world-championship-2026">ok</a><a href="https://evil.example/x">no</a><a href="/matches/124/unrelated">no</a>'
        self.assertEqual(twc_research.discovered_urls(markup), [SOURCE])

    def test_original_hash_and_containment_are_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); folder = root / twc_research.FOLDER; folder.mkdir(parents=True)
            raw = b'<html>not a confirmed match</html>'
            (folder / 'x.html.gz').write_bytes(gzip.compress(raw))
            page = {'request': {'status': 'ok', 'url': SOURCE, 'observed_at': iso(NOW)},
                    'original_response': 'x.html.gz', 'stored_sha256': hashlib.sha256(raw).hexdigest(),
                    'facts': {'score': [2, 0]}}
            manifest = folder / 'source-report.json'
            manifest.write_text(json.dumps({'pages': [page]}))
            self.assertEqual(twc_research.load(root)['pages'], [])  # stored extraction is not evidence
            page['stored_sha256'] = '0' * 64; manifest.write_text(json.dumps({'pages': [page]}))
            with self.assertRaises(ValueError): twc_research.load(root)
            page['original_response'] = '../escape.gz'; manifest.write_text(json.dumps({'pages': [page]}))
            with self.assertRaises(ValueError): twc_research.load(root)


if __name__ == '__main__':
    unittest.main()

class PublicDay4Parity(unittest.TestCase):
    def test_nonempty_day4_future_cards_verify_and_tampering_fails(self):
        from scripts.verify_live import verify_day4
        d = example()
        with patch('scripts.twc_research.load', return_value={'pages': [record()]}):
            guide = twc_research.derive_day4(d, Path('data'), NOW)
        page = BeautifulSoup(build_twc.render_day4(guide, '../'), 'html.parser')
        verify_day4(d, d['complete_picks'], {'day4': guide}, guide, page)
        page.select_one('.twc-prob strong').string = '80.0%'
        with self.assertRaisesRegex(ValueError, 'Day-4 HTML probabilities'):
            verify_day4(d, d['complete_picks'], {'day4': guide}, guide, page)


class TournamentCardLines(unittest.TestCase):
    """Day-4 tournament-card lines: rendered only with evidence or a reason."""

    def guide(self, line=None, observation=None):
        return {'matches': [], 'not_in_hotspawn_snapshot': [{
                    'source_url': SOURCE, 'observed_at': iso(NOW), 'line': line, 'line_underdog': None,
                    'facts': {'teams': ['FURIA', 'Aurora'], 'starts_at': '2026-10-17T14:00:00Z'}}],
                'lines': {'available': line is not None, 'observed_at': iso(NOW), 'resolved': 1 if line else 0,
                          'total': 1, 'report_path': 'research/twc-current/day4-lines.json'},
                'observations': [observation] if observation else [], 'research_available': True,
                'research_report': 'research/twc-current/source-report.json', 'day3_results': [],
                'day1_results': [], 'day2_results': [], 'day3_matches': [], 'roster_report': None,
                'roster_listings': {}, 'unresolved': [], 'global_unresolved': 0, 'limitations': []}

    def line(self):
        return {'fixture_id': 'twc-2399414', 'teams': ['FURIA', 'Aurora'], 'starts_at': '2026-10-17T14:00:00Z',
                'probabilities': [0.52380654, 0.47619346], 'pick_index': 0, 'method': 'market',
                'label': 'Tournament market line — Kalshi/Polymarket consensus', 'observed_at': iso(NOW),
                'providers': [{'provider': 'Polymarket', 'probabilities': [0.525, 0.475], 'bid': [0.52, 0.47],
                               'ask': [0.53, 0.48], 'source_url': 'https://polymarket.com/event/cs2-furia-aur1-2026-10-17',
                               'observed_at': iso(NOW)},
                              {'provider': 'Kalshi', 'probabilities': [0.5226, 0.4774], 'bid': [0.51, 0.47],
                               'ask': [0.53, 0.48], 'source_url': 'https://kalshi.com/markets/kxcs2game/counterstrike-2-game',
                               'observed_at': iso(NOW)}],
                'attempts': []}

    def test_collected_line_renders_probabilities_pick_and_provider_links(self):
        html = build_twc.render_day4(self.guide(self.line()), '../')
        text = BeautifulSoup(html, 'html.parser').get_text()
        self.assertIn('52.4%', text)
        self.assertIn('47.6%', text)
        self.assertIn('Default pick: FURIA', text)
        self.assertIn('polymarket.com/event/cs2-furia-aur1-2026-10-17', html)
        self.assertIn('kalshi.com/markets/kxcs2game', html)
        self.assertIn('day-four-tournament-lines', html)

    def test_underdog_verdicts_follow_the_published_floor(self):
        guide = self.guide(self.line())
        guide['not_in_hotspawn_snapshot'][0]['line_underdog'] = {
            'team': 'Aurora', 'probability': 0.47619346, 'passes_floor': True, 'cost_per_base_point': 0.04761308}
        text = BeautifulSoup(build_twc.render_day4(guide, '../'), 'html.parser').get_text()
        self.assertIn('Optional contrarian slot: Aurora', text)
        guide['not_in_hotspawn_snapshot'][0]['line_underdog'] = {
            'team': 'BETBOOM', 'probability': 0.20656091, 'passes_floor': False, 'cost_per_base_point': 0.58687818}
        text = BeautifulSoup(build_twc.render_day4(guide, '../'), 'html.parser').get_text()
        self.assertIn('No upset play offered: BETBOOM', text)

    def test_unresolved_line_publishes_a_reason_and_no_number(self):
        reason = {'fixture_id': 'twc-2399414', 'teams': ['FURIA', 'Aurora'], 'starts_at': '2026-10-17T14:00:00Z',
                  'probabilities': None, 'pick_index': None, 'method': None,
                  'label': 'Unresolved — no validated two-sided external line', 'observed_at': None,
                  'providers': [], 'attempts': [{'provider': 'Kalshi', 'reason': 'Kalshi yes book is wider than the 12-cent ceiling',
                                                 'status': 'unresolved', 'source_url': 'https://kalshi.com/markets/kxcs2game/counterstrike-2-game',
                                                 'observed_at': iso(NOW)}], 'limitations': []}
        html = build_twc.render_day4(self.guide(reason), '../')
        table = BeautifulSoup(html, 'html.parser').find('table')
        self.assertIn('No validated two-sided external line', table.get_text())
        self.assertIn('wider than the 12-cent ceiling', table.get_text())
        self.assertIsNone(re.search(r'\d+(\.\d+)?%', table.get_text()), table.get_text())

    def test_dated_observation_is_labelled_and_not_a_collected_line(self):
        observation = {'fixture_id': 'twc-2399414', 'teams': ['FURIA', 'Aurora'],
                       'starts_at': '2026-10-17T14:00:00Z', 'median': [0.52380654, 0.47619346], 'pick': 'FURIA',
                       'providers': [{'provider': 'Polymarket', 'outcomes': ['FURIA', 'Aurora Gaming'],
                                      'bid': [0.52, 0.47], 'ask': [0.53, 0.48],
                                      'observed_at': '2026-10-16T23:56:13Z',
                                      'book_updated_at': '2026-10-16T17:30:00Z'}],
                       'underdog': {'team': 'Aurora', 'probability': 0.47619346, 'passes_floor': True,
                                    'cost_per_base_point': 0.04761308, 'reading': 'Priced coin flip.'}}
        guide = self.guide(line=None, observation=observation)
        text = BeautifulSoup(build_twc.render_day4(guide, '../'), 'html.parser').get_text()
        self.assertIn('Dated market observation', text)
        self.assertIn('Dated lean: FURIA', text)
        self.assertIn("not the publisher's collected evidence", text)
        self.assertIn('Optional contrarian slot: Aurora', text)

    def test_committed_observation_dossier_is_source_complete(self):
        rows = twc_research.load_observations(Path('data'))
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(len(row['teams']), 2)
            self.assertTrue(row['starts_at'].endswith('Z'))
            self.assertGreaterEqual(len(row['providers']), 2)
            for provider in row['providers']:
                self.assertTrue(provider['book_url'].startswith('https://'))
                self.assertEqual(len(provider['outcomes']), 2)
                self.assertEqual(len(provider['bid']), 2)
                self.assertEqual(len(provider['ask']), 2)
                for bid, ask in zip(provider['bid'], provider['ask']):
                    self.assertLess(bid, ask)
                    self.assertLessEqual(round(ask - bid, 8), 0.12)
                self.assertTrue(provider['observed_at'])
            total = sum(row['median'])
            self.assertAlmostEqual(total, 1, places=4)
            # The published median must equal the median of the provider midpoints.
            normalized = []
            for provider in row['providers']:
                mids = [(bid + ask) / 2 for bid, ask in zip(provider['bid'], provider['ask'])]
                normalized.append([mid / sum(mids) for mid in mids])
            expected = [median(pair[index] for pair in normalized) for index in (0, 1)]
            for index in (0, 1):
                self.assertAlmostEqual(row['median'][index], expected[index], places=6)
            self.assertIn(row['pick'], row['teams'])
            self.assertLess(row['underdog']['probability'], 0.5)

    def test_missing_observation_file_is_empty_not_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(twc_research.load_observations(Path(tmp)), [])
