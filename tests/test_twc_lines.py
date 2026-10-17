"""Day-4 tournament-card lines: identity, book contract, replay and blanks.

All fixtures here are synthetic. They exercise the published contract only; no
live response is read and the repository's reviewed alias registry is loaded
explicitly, exactly as the production module does.
"""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import twc_lines
from scripts.domain import iso

NOW = datetime(2026, 10, 16, 23, 50, tzinfo=timezone.utc)
START = '2026-10-17T14:00:00Z'
REGISTRY = json.loads(Path('data/origination/aliases.json').read_text())


def fixture(teams=('FURIA', 'Aurora')):
    return {'id': 'twc-2399414', 'teams': [{'name': teams[0]}, {'name': teams[1]}], 'starts_at': START,
            'competition': 'Thunderpick World Championship 2026',
            'source_url': 'https://www.hltv.org/matches/2399414/furia-vs-aurora-thunderpick-world-championship-2026',
            'hltv_match_id': '2399414'}


def polymarket_event(outcomes=('FURIA', 'Aurora Gaming'), start='2026-10-17 14:00:00+00'):
    return {'id': '5778024', 'slug': 'cs2-furia-aur1-2026-10-17', 'active': True, 'closed': False,
            'markets': [{'id': '9001', 'conditionId': '0xcond', 'question': 'Counter-Strike: FURIA vs Aurora Gaming (BO3)',
                         'outcomes': json.dumps(list(outcomes)), 'clobTokenIds': json.dumps(['t-furia', 't-aurora']),
                         'sportsMarketType': 'moneyline', 'active': True, 'closed': False,
                         'acceptingOrders': True, 'gameStartTime': start,
                         'volumeNum': 38365.68, 'liquidityNum': 158522.82}]}


def book(asset, bid, ask, *, condition='0xcond', when=None):
    when = when or NOW - timedelta(minutes=1)
    return {'market': condition, 'asset_id': asset, 'timestamp': str(int(when.timestamp() * 1000)),
            'bids': [{'price': str(bid), 'size': '100'}], 'asks': [{'price': str(ask), 'size': '100'}]}


def kalshi_event(teams=('Aurora', 'FURIA'), bids=('0.46', '0.52'), asks=('0.48', '0.54'),
                 ticker='KXCS2GAME-26OCT171000AURFURIA'):
    markets = []
    for name, bid, ask in zip(teams, bids, asks):
        markets.append({'ticker': ticker + '-' + name.upper()[:3], 'yes_sub_title': name, 'status': 'active',
                        'yes_bid_dollars': bid, 'yes_ask_dollars': ask,
                        'rules_primary': 'If %s wins the CS2 match originally scheduled for Oct 17, 2026 at '
                                         '10:00 AM EDT, then the market resolves to Yes.' % name})
    return {'series_ticker': 'KXCS2GAME', 'product_metadata': {'competition': 'CS2'}, 'mutually_exclusive': True,
            'event_ticker': ticker, 'markets': markets}


class Quotes(unittest.TestCase):
    def test_alias_and_exact_start_join(self):
        quote, reason = twc_lines.polymarket_quote(
            polymarket_event(), [book('t-furia', 0.52, 0.53), book('t-aurora', 0.47, 0.48)],
            fixture(), REGISTRY, NOW)
        self.assertEqual(reason, '')
        self.assertAlmostEqual(quote['probabilities'][0], 0.525, places=6)
        self.assertAlmostEqual(quote['probabilities'][1], 0.475, places=6)
        self.assertEqual(quote['source_url'], 'https://polymarket.com/event/cs2-furia-aur1-2026-10-17')

    def test_unscoped_name_is_not_joined(self):
        event = polymarket_event(outcomes=('FURIA', 'Aurora'))
        event['markets'][0]['outcomes'] = json.dumps(['FURIA', 'Aurora Esports'])
        quote, reason = twc_lines.polymarket_quote(
            event, [book('t-furia', 0.52, 0.53), book('t-aurora', 0.47, 0.48)], fixture(), REGISTRY, NOW)
        self.assertIsNone(quote)
        self.assertTrue(reason)  # No scoped alias for 'Aurora Esports' → no join, no invented value.

    def test_start_mismatch_is_rejected(self):
        quote, reason = twc_lines.polymarket_quote(
            polymarket_event(start='2026-10-17 15:00:00+00'),
            [book('t-furia', 0.52, 0.53), book('t-aurora', 0.47, 0.48)], fixture(), REGISTRY, NOW)
        self.assertIsNone(quote)
        self.assertTrue(reason)

    def test_wide_or_one_sided_book_is_rejected(self):
        quote, reason = twc_lines.polymarket_quote(
            polymarket_event(), [book('t-furia', 0.40, 0.60), book('t-aurora', 0.40, 0.60)],
            fixture(), REGISTRY, NOW)
        self.assertIsNone(quote)
        self.assertIn('contract', reason)
        single = {'market': '0xcond', 'asset_id': 't-furia', 'timestamp': str(int(NOW.timestamp() * 1000)) ,
                  'bids': [{'price': '0.5', 'size': '10'}], 'asks': [{'price': '0.5', 'size': '0'}]}
        quote, reason = twc_lines.polymarket_quote(
            polymarket_event(), [single, book('t-aurora', 0.47, 0.48)], fixture(), REGISTRY, NOW)
        self.assertIsNone(quote)
        self.assertIn('contract', reason)

    def test_stale_book_is_rejected(self):
        old = NOW - timedelta(hours=9)
        quote, reason = twc_lines.polymarket_quote(
            polymarket_event(), [book('t-furia', 0.52, 0.53, when=old), book('t-aurora', 0.47, 0.48)],
            fixture(), REGISTRY, NOW)
        self.assertIsNone(quote)
        self.assertIn('stale', reason)

    def test_kalshi_requires_contract_start_not_displayed_title(self):
        quote, reason = twc_lines.kalshi_quote(kalshi_event(), fixture(), REGISTRY, iso(NOW), NOW)
        self.assertEqual(reason, '')
        # Kalshi lists Aurora first; the pair is aligned to the fixture's own
        # team order (FURIA, Aurora), so FURIA carries the 0.53 midpoint.
        self.assertAlmostEqual(quote['probabilities'][0], 0.53, places=6)
        self.assertAlmostEqual(quote['probabilities'][1], 0.47, places=6)

    def test_kalshi_wide_or_prematch_failures(self):
        quote, reason = twc_lines.kalshi_quote(kalshi_event(bids=('0.10', '0.10'), asks=('0.90', '0.90')),
                                               fixture(), REGISTRY, iso(NOW), NOW)
        self.assertIsNone(quote)
        self.assertIn('wider', reason)
        quote, reason = twc_lines.kalshi_quote(kalshi_event(), fixture(), REGISTRY, '2026-10-17T15:00:00Z', NOW)
        self.assertIsNone(quote)
        self.assertIn('prematch', reason)

    def test_median_of_providers_and_single_source_label(self):
        poly = {'provider': 'Polymarket', 'quote': {'provider': 'Polymarket', 'probabilities': [0.5, 0.5],
                                                    'bid': [0.49, 0.49], 'ask': [0.51, 0.51],
                                                    'source_url': 'https://polymarket.com/event/x', 'api_url': 'u',
                                                    'event_id': '1'}, 'status': 'resolved', 'reason': '',
                    'source_url': 'https://polymarket.com/event/x', 'observed_at': iso(NOW)}
        kal = {'provider': 'Kalshi', 'quote': {'provider': 'Kalshi', 'probabilities': [0.6, 0.4],
                                               'bid': [0.58, 0.38], 'ask': [0.62, 0.42],
                                               'source_url': 'https://kalshi.com/x', 'api_url': 'u',
                                               'event_id': '2'}, 'status': 'resolved', 'reason': '',
               'source_url': 'https://kalshi.com/x', 'observed_at': iso(NOW)}
        row = twc_lines.analyse([poly, kal], fixture())
        self.assertAlmostEqual(row['probabilities'][0], 0.55, places=6)
        self.assertEqual(row['pick_index'], 0)
        self.assertIn('consensus', row['label'])
        single = twc_lines.analyse([poly], fixture())
        self.assertIn('single independent source', single['label'])
        self.assertTrue(any('not a multi-book consensus' in x for x in single['limitations']))

    def test_no_provider_keeps_every_value_blank(self):
        row = twc_lines.analyse([{'provider': 'Polymarket', 'status': 'unresolved', 'reason': 'no market',
                                  'source_url': 'https://polymarket.com/esports/cs2', 'observed_at': iso(NOW),
                                  'quote': None}], fixture())
        self.assertIsNone(row['probabilities'])
        self.assertIsNone(row['pick_index'])
        self.assertIsNone(row['method'])
        self.assertNotIn('50', row['label'])

    def test_underdog_floor(self):
        row = twc_lines.analyse([{'provider': 'Kalshi', 'status': 'resolved', 'reason': '',
                                  'source_url': 'https://kalshi.com/x', 'observed_at': iso(NOW),
                                  'quote': {'provider': 'Kalshi', 'probabilities': [0.52, 0.48],
                                            'bid': [0.51, 0.47], 'ask': [0.53, 0.49],
                                            'source_url': 'https://kalshi.com/x', 'api_url': 'u', 'event_id': '2'}}],
                                fixture())
        dog = twc_lines.underdog(row)
        self.assertEqual(dog['team'], 'Aurora')
        self.assertTrue(dog['passes_floor'])
        thin = twc_lines.analyse([{'provider': 'Kalshi', 'status': 'resolved', 'reason': '',
                                   'source_url': 'https://kalshi.com/x', 'observed_at': iso(NOW),
                                   'quote': {'provider': 'Kalshi', 'probabilities': [0.8, 0.2],
                                             'bid': [0.79, 0.19], 'ask': [0.81, 0.21],
                                             'source_url': 'https://kalshi.com/x', 'api_url': 'u', 'event_id': '2'}}],
                                 fixture(('Falcons', 'BETBOOM')))
        self.assertFalse(twc_lines.underdog(thin)['passes_floor'])


class Fixtures(unittest.TestCase):
    def test_only_two_named_teams_on_the_requested_day(self):
        rows = [{'source_url': 'https://www.hltv.org/matches/2399414/furia-vs-aurora-thunderpick-world-championship-2026',
                 'observed_at': iso(NOW), 'facts': {'teams': ['FURIA', 'Aurora'], 'starts_at': START, 'finished': False}}]
        self.assertEqual(len(twc_lines.fixtures(rows, '2026-10-17')), 1)
        rows += [{'source_url': 'https://www.hltv.org/matches/2399416/x-thunderpick-world-championship-2026',
                  'observed_at': iso(NOW), 'facts': {'teams': ['TBD', 'TBD'], 'starts_at': START, 'finished': False}},
                 {'source_url': 'https://www.hltv.org/matches/2399417/y-thunderpick-world-championship-2026',
                  'observed_at': iso(NOW), 'facts': {'teams': ['FURIA', 'Aurora'], 'starts_at': '2026-10-18T11:00:00Z',
                                                     'finished': False}},
                 {'source_url': 'https://www.hltv.org/matches/2399418/z-thunderpick-world-championship-2026',
                  'observed_at': iso(NOW), 'facts': {'teams': ['FURIA', 'Aurora'], 'starts_at': START, 'finished': True}}]
        kept = twc_lines.fixtures(rows, '2026-10-17')
        self.assertEqual([r['hltv_match_id'] for r in kept], ['2399414'])


class Replay(unittest.TestCase):
    def _write(self, root: Path, *, tamper=False, omit_book=False):
        folder = root / 'research/twc-current'
        (folder / 'evidence').mkdir(parents=True)
        payloads = {'twc-day4-poly-event-5778024': polymarket_event()}
        if not omit_book:
            payloads['twc-day4-poly-book-5778024-0'] = book('t-furia', 0.52, 0.53)
            payloads['twc-day4-poly-book-5778024-1'] = book('t-aurora', 0.47, 0.48)
        evidence = []
        for label, payload in payloads.items():
            raw = json.dumps(payload, indent=2).encode()
            (folder / 'evidence' / (label + '.json')).write_bytes(raw)
            evidence.append({'label': label, 'url': 'https://example.invalid/' + label,
                             'observed_at': iso(NOW), 'file': 'evidence/' + label + '.json',
                             'sha256': hashlib.sha256(raw).hexdigest()})
        report = {'schema_version': 1, 'policy': twc_lines.POLICY, 'event': twc_lines.EVENT, 'day': '2026-10-17',
                  'observed_at': iso(NOW), 'records': [{'fixture': {'id': 'twc-2399414', 'teams': ['FURIA', 'Aurora'],
                                                                    'starts_at': START, 'source_url': 'https://www.hltv.org/matches/2399414/furia-vs-aurora-thunderpick-world-championship-2026',
                                                                    'hltv_match_id': '2399414'},
                                                        'providers': [{'provider': 'Polymarket', 'status': 'resolved', 'reason': '',
                                                                       'source_url': 'https://polymarket.com/event/cs2-furia-aur1-2026-10-17',
                                                                       'observed_at': iso(NOW), 'quote': {'probabilities': [0.9, 0.1]},
                                                                       'evidence': evidence, 'event_id': '5778024'}]}]}
        (folder / twc_lines.REPORT).write_text(json.dumps(report))
        return folder

    def test_replay_recomputes_from_originals_not_stored_probabilities(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(Path(tmp))
            lines = twc_lines.load(Path(tmp), NOW, REGISTRY)
            self.assertTrue(lines['available'])
            row = lines['matches'][0]
            self.assertAlmostEqual(row['probabilities'][0], 0.525, places=6)
            self.assertEqual(row['pick_index'], 0)
            self.assertEqual(row['providers'][0]['provider'], 'Polymarket')
            self.assertEqual(twc_lines.for_fixture(lines, ['FURIA', 'Aurora'], START)['fixture_id'], 'twc-2399414')
            self.assertIsNone(twc_lines.for_fixture(lines, ['FURIA', 'BETBOOM'], START))

    def test_tampered_original_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._write(Path(tmp))
            path = folder / 'evidence/twc-day4-poly-book-5778024-0.json'
            path.write_bytes(path.read_bytes().replace(b'0.52', b'0.99'))
            with self.assertRaises(ValueError):
                twc_lines.load(Path(tmp), NOW, REGISTRY)

    def test_missing_book_publishes_blank_with_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(Path(tmp), omit_book=True)
            lines = twc_lines.load(Path(tmp), NOW, REGISTRY)
            row = lines['matches'][0]
            self.assertIsNone(row['probabilities'])
            self.assertIsNone(twc_lines.for_fixture(lines, ['FURIA', 'Aurora'], START)['probabilities'])

    def test_absent_report_is_empty_not_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines = twc_lines.load(Path(tmp), NOW, REGISTRY)
            self.assertFalse(lines['available'])
            self.assertEqual(lines['matches'], [])
            self.assertIsNone(twc_lines.for_fixture(lines, ['FURIA', 'Aurora'], START))

    def test_evidence_path_cannot_escape_the_research_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self._write(Path(tmp))
            report = json.loads((folder / twc_lines.REPORT).read_text())
            report['records'][0]['providers'][0]['evidence'][0]['file'] = '../../../etc/passwd'
            (folder / twc_lines.REPORT).write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                twc_lines.load(Path(tmp), NOW, REGISTRY)
