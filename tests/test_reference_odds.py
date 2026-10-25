"""The reviewed aggregated-bookmaker fallback must never overstate its evidence."""
from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import reference_odds
from scripts.domain import name_key
from scripts.originate import originate_match

ROOT = Path(__file__).resolve().parent.parent
CAPTURE = ROOT / 'data/research/57b1ee04/reference-odds.json'
NOW = datetime(2026, 10, 18, 1, 0, tzinfo=timezone.utc)


def fixture(fid='1081521', teams=('ex-6666', 'Privateer'), start='2026-10-18T13:45:00Z'):
    return {'id': fid, 'starts_at': start, 'locks_at': '2026-10-18T13:39:00Z',
            'availability': 'open', 'competition': 'CCT 2026 Challengers Europe Series 8',
            'tier': 'c', 'source_url': 'https://www.hotspawn.com/matches/ex-6666-vs-privateer-1081521',
            'lobby_url': 'https://play.hotspawn.com/cs2-pickems',
            'teams': [{'id': '1', 'name': teams[0]}, {'id': '2', 'name': teams[1]}]}


def capture():
    return json.loads(CAPTURE.read_text(encoding='utf-8'))


class CaptureFileTests(unittest.TestCase):
    def test_every_shipped_entry_is_valid_and_replays(self):
        data = reference_odds.load(ROOT / 'data')
        self.assertFalse(data['missing'])
        # Nine earlier reviewed captures plus E57 (1), C2A7 (4), arena-0db056f7 (1:
        # fixture 1086696), and arena-35e31fef (3: 1082858, 1082859, 1086696) captures.
        self.assertEqual(len(data['entries']), 18)
        for entry in data['entries']:
            self.assertEqual(reference_odds.problems(entry), [], entry.get('fixture_id'))
            entry_now = datetime.fromisoformat(entry['observed_at'].replace('Z', '+00:00')) + timedelta(minutes=5)
            quote, reason = reference_odds.quote(entry, fixture(entry['fixture_id'], tuple(entry['teams']), entry['starts_at']), entry_now)
            self.assertIsNotNone(quote, reason)
            reference_odds.replay(entry, quote)

    def test_probabilities_are_no_vig_and_not_home_made(self):
        entries = {e['fixture_id']: e for e in capture()['entries']}
        q, _ = reference_odds.quote(entries['1081521'], fixture(), NOW)
        self.assertEqual(q['probabilities'], [0.80782313, 0.19217687])
        self.assertAlmostEqual(sum(q['probabilities']), 1, places=7)
        self.assertEqual(q['method'], 'reference')
        self.assertEqual(q['family'], 'reference')
        self.assertTrue(q['aggregated'])

    def test_capture_records_provider_names_and_a_hash(self):
        for entry in capture()['entries']:
            self.assertEqual(len(entry['provider_teams']), 2)
            self.assertEqual(entry['excerpt_sha256'], hashlib.sha256(entry['excerpt'].encode()).hexdigest())
            self.assertTrue(entry['source_url'].startswith('https://egamersworld.com/'))

    def test_two_void_fixtures_stay_documented_as_rejected(self):
        rejected = {e['fixture_id']: e for e in capture()['rejected']}
        self.assertEqual(set(rejected), {'1081861', '1081863'})
        for entry in rejected.values():
            self.assertIn('1.8/1.8', entry['reason'])
            self.assertNotIn('odds', entry)
            quote, reason = reference_odds.quote(entry, fixture(entry['fixture_id'], tuple(entry['teams']), entry['starts_at']), NOW)
            self.assertIsNone(quote)
            self.assertIn('rejected', reason.lower())


class RejectionTests(unittest.TestCase):
    def setUp(self):
        self.entry = capture()['entries'][0]

    def test_identical_prices_are_a_placeholder(self):
        entry = dict(self.entry, odds=[1.8, 1.8],
                     excerpt_sha256=hashlib.sha256(self.entry['excerpt'].encode()).hexdigest())
        self.assertIn('placeholder', ' '.join(reference_odds.problems(entry)))

    def test_stale_capture_produces_no_quote(self):
        old = dict(self.entry, observed_at='2026-10-17T12:00:00Z')
        quote, reason = reference_odds.quote(old, fixture(), NOW)
        self.assertIsNone(quote)
        self.assertIn('older than eight hours', reason)

    def test_future_capture_beyond_skew_produces_no_quote(self):
        future = dict(self.entry, observed_at='2026-10-18T02:00:00Z')
        quote, reason = reference_odds.quote(future, fixture(), NOW)
        self.assertIsNone(quote)
        self.assertIn('older than eight hours', reason)

    def test_wrong_fixture_id_team_or_start_is_rejected(self):
        self.assertIsNone(reference_odds.quote(self.entry, fixture('1081522'), NOW)[0])
        self.assertIsNone(reference_odds.quote(self.entry, fixture(teams=('ex-6666', 'Someone')), NOW)[0])
        self.assertIsNone(reference_odds.quote(self.entry, fixture(start='2026-10-18T14:45:00Z'), NOW)[0])

    def test_tampered_excerpt_is_rejected(self):
        bad = dict(self.entry, excerpt=self.entry['excerpt'] + ' edited')
        self.assertIn('excerpt_sha256', ' '.join(reference_odds.problems(bad)))

    def test_odds_outside_the_band_are_rejected(self):
        bad = dict(self.entry, odds=[1.01, 1.02])
        self.assertTrue(reference_odds.problems(bad))


class OriginationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.entry = capture()['entries'][0]

    def run_match(self, match, reference, rows=()):
        return originate_match(match, [], list(rows), [], None, {'aliases': []}, NOW, reference=reference)

    def test_blank_fixture_gets_a_labelled_aggregated_pick(self):
        result = self.run_match(fixture(), [self.entry])
        line = result['origination']
        self.assertIsNotNone(line)
        self.assertEqual(line['method'], 'reference')
        self.assertEqual(line['probabilities'], [0.80782313, 0.19217687])
        self.assertEqual(result['pick_index'], 0)
        stage = next(r for r in result['research'] if r['stage'].startswith('Aggregated'))
        self.assertEqual(stage['status'], 'resolved')
        self.assertIn('hash-checked', stage['detail'])
        self.assertTrue(any('third-party' in x.lower() for x in result['limitations']))

    def test_reference_never_overrides_a_first_party_market(self):
        row = {'family': 'bookmaker', 'provider': 'Bovada',
               'names': ['ex-6666', 'Privateer'], 'start': '2026-10-18T13:45:00Z',
               'odds': [1.60, 2.40], 'event_id': '32266578', 'market_id': '1',
               'source_url': 'https://www.bovada.lv/esports/counter-strike-2/x',
               'api_url': 'https://www.bovada.lv/services/sports/event/v2/events/A/description/esports/counter-strike-2',
               'evidence_file': 'data/origination/evidence/live-bovada-cs2.json',
               'observed_at': '2026-10-18T00:30:00Z', 'league': 'CCT'}
        result = self.run_match(fixture(), [self.entry], rows=[row])
        line = result['origination']
        self.assertEqual(line['method'], 'bookmaker')
        self.assertEqual({q['provider'] for q in line['quotes']}, {'Bovada'})
        self.assertNotEqual(line['probabilities'], [0.80782313, 0.19217687])
        stage = next(r for r in result['research'] if r['stage'].startswith('Aggregated'))
        self.assertEqual(stage['status'], 'not needed')

    def test_rejected_capture_leaves_the_fixture_blank(self):
        rejected = capture()['rejected'][0]
        result = self.run_match(fixture(rejected['fixture_id'], tuple(rejected['teams']), rejected['starts_at']), [rejected])
        self.assertIsNone(result['origination'])
        self.assertIn('Reviewed capture rejected', ' '.join(r['detail'] for r in result['research']))


if __name__ == '__main__':
    unittest.main()
