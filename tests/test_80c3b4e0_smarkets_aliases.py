"""Session arena-80c3b4e0 — competition-scoped alias binding on Smarkets & verification tests."""
from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import originate, smarkets_lines
from scripts.domain import iso

UTC = timezone.utc
ROOT = Path(__file__).resolve().parent.parent
NOW = datetime.now(UTC).replace(microsecond=0)
START = (NOW + timedelta(hours=6)).isoformat().replace('+00:00', 'Z')
LOCK = (NOW + timedelta(hours=6) - timedelta(minutes=6)).isoformat().replace('+00:00', 'Z')


REGISTRY = {
    'aliases': [
        {
            'alias': 'BakS eSports',
            'canonical': 'BakS',
            'kind': 'display-name expansion',
            'applies_to': ['CCT Europe 2026 Series #11', 'NODWIN Clutch Series #13'],
            'must_not_match': ['BakS Junior', 'BakS Academy'],
            'evidence': [{'url': 'https://www.hltv.org/matches/2399334/brute-vs-baks-cct-2026-europe-series-11'}],
        },
        {
            'alias': 'UNiTY esports',
            'canonical': 'UNiTY',
            'kind': 'display-name expansion',
            'applies_to': ['NODWIN Clutch Series #13'],
            'must_not_match': ['UNiTY Academy', 'UNiTY fe'],
            'evidence': [{'url': 'https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13'}],
        },
    ]
}


class AliasClient:
    """Stub client returning live-shaped Smarkets payloads (Brute listed HOME, BakS eSports AWAY)."""

    def __init__(self, *, event, market, contracts, quotes):
        self.event = event
        self.market = market
        self.contracts = contracts
        self.quotes = quotes

    def get_json(self, url, label, *, method='GET', payload=None, save=True, headers=None):
        if 'events/?type=csgo_match' in url:
            return {'events': [self.event]}, {'observed_at': iso(NOW), 'status': 'ok'}
        if '/markets/' in url and 'contracts' in url:
            return {'contracts': self.contracts}, {'observed_at': iso(NOW), 'status': 'ok'}
        if '/quotes/' in url:
            return self.quotes, {'observed_at': iso(NOW), 'status': 'ok'}
        if url.endswith('/markets/'):
            return {'markets': [self.market]}, {'observed_at': iso(NOW), 'status': 'ok'}
        raise AssertionError('unexpected URL ' + url)


class SmarketsScopedAliasTests(unittest.TestCase):
    def _baks_fixture(self, competition='CCT Europe 2026 Series #11'):
        return {
            'id': '1079657',
            'availability': 'open',
            'teams': [{'id': '1', 'name': 'BakS'}, {'id': '2', 'name': 'BRUTE'}],
            'starts_at': START,
            'locks_at': LOCK,
            'competition': competition,
            'source_url': 'https://www.hotspawn.com/matches/brute-vs-baks-cct-europe-2026-series-11-1079657',
        }

    def _baks_event(self, name='Brute vs BakS eSports'):
        return {
            'id': '45394317',
            'name': name,
            'state': 'upcoming',
            'bettable': True,
            'start_datetime': START,
            'type': 'csgo_match',
            'full_slug': '/sport/esports/cs-go/cct-europe/playoffs/2026/10/23/17-00/brute-vs-baks-esports',
        }

    def test_exact_mode_stays_strict_when_registry_omitted(self):
        self.assertFalse(smarkets_lines.binds(self._baks_event(), self._baks_fixture()))

    def test_scoped_alias_binds_in_matching_competition_even_when_side_order_is_reversed(self):
        self.assertTrue(smarkets_lines.binds(self._baks_event(), self._baks_fixture(), registry=REGISTRY))

    def test_scoped_alias_is_rejected_outside_applies_to(self):
        wrong_comp = self._baks_fixture(competition='Some Unlisted Regional Cup 2026')
        self.assertFalse(smarkets_lines.binds(self._baks_event(), wrong_comp, registry=REGISTRY))

    def test_must_not_match_exclusions_never_bind(self):
        academy_event = self._baks_event(name='Brute vs BakS Academy')
        self.assertFalse(smarkets_lines.binds(academy_event, self._baks_fixture(), registry=REGISTRY))

    def test_collect_records_aliases_used_and_replays_reversed_side_order_through_ladder(self):
        event = self._baks_event()
        market = {'id': '172923315', 'event_id': '45394317', 'state': 'open', 'hidden': False,
                  'market_type': {'name': 'WINNER_2_WAY'}}
        contracts = [
            {'id': '476959990', 'market_id': '172923315', 'name': 'Brute', 'state_or_outcome': 'open'},
            {'id': '476959991', 'market_id': '172923315', 'name': 'BakS eSports', 'state_or_outcome': 'open'},
        ]
        # Exact quotes observed on Smarkets 45394317: Brute 4587/5848, BakS eSports 4167/5405
        quotes = {
            '476959990': {'bids': [{'price': 4587, 'quantity': 200}], 'offers': [{'price': 5848, 'quantity': 200}]},
            '476959991': {'bids': [{'price': 4167, 'quantity': 200}], 'offers': [{'price': 5405, 'quantity': 200}]},
        }
        client = AliasClient(event=event, market=market, contracts=contracts, quotes=quotes)
        match = self._baks_fixture()

        with tempfile.TemporaryDirectory() as tmp:
            # Write aliases.json in parent of evidence_dir just like data/origination/aliases.json
            root_tmp = Path(tmp)
            (root_tmp / 'aliases.json').write_text(json.dumps(REGISTRY))
            ev_dir = root_tmp / 'evidence'
            summary = smarkets_lines.collect(client, ev_dir, [match])
            self.assertEqual(summary['bound'], 1)
            self.assertEqual(summary['quotes'], 2)

            saved = json.loads((ev_dir / smarkets_lines.EVIDENCE_NAME).read_text())
            self.assertEqual(saved['bindings'][0]['aliases_used'][0]['alias'], 'BakS eSports')
            self.assertEqual(saved['bindings'][0]['aliases_used'][0]['canonical'], 'BakS')

            row = smarkets_lines.rows(ev_dir)[0]
            quote, detail = originate.market_estimate(row, match, REGISTRY, NOW)
            self.assertIsNotNone(quote, detail)
            # Hotspawn lists BakS (team 0) vs BRUTE (team 1); BRUTE is slightly favored (~52.2%)
            self.assertLess(quote['probabilities'][0], 0.5)
            self.assertGreater(quote['probabilities'][1], 0.5)
            self.assertAlmostEqual(sum(quote['probabilities']), 1.0, places=6)

    def test_wide_dfrag_exchange_book_stays_guidance_only_above_spread_cap(self):
        # Exact Smarkets 45396333 quotes for Ground Zero vs Off Chops (18.5pp spread > 15pp cap)
        match = {
            'id': '1082858',
            'availability': 'open',
            'teams': [{'id': '1', 'name': 'Ground Zero'}, {'id': '2', 'name': 'Off Chops'}],
            'starts_at': START,
            'locks_at': LOCK,
            'competition': 'DFRAG Invitational 2026',
            'source_url': 'https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858',
        }
        event = {
            'id': '45396333',
            'name': 'Ground Zero vs Off Chops',
            'state': 'upcoming',
            'bettable': True,
            'start_datetime': START,
            'type': 'csgo_match',
            'full_slug': '/sport/esports/cs-go/dfrag-invitational/group-a/2026/10/26/03-00/ground-zero-vs-off-chops',
        }
        market = {'id': '172960355', 'event_id': '45396333', 'state': 'open', 'hidden': False,
                  'market_type': {'name': 'WINNER_2_WAY'}}
        contracts = [
            {'id': '477100001', 'market_id': '172960355', 'name': 'Ground Zero', 'state_or_outcome': 'open'},
            {'id': '477100002', 'market_id': '172960355', 'name': 'Off Chops', 'state_or_outcome': 'open'},
        ]
        quotes = {
            '477100001': {'bids': [{'price': 1429, 'quantity': 100}], 'offers': [{'price': 3279, 'quantity': 100}]},
            '477100002': {'bids': [{'price': 6711, 'quantity': 100}], 'offers': [{'price': 8547, 'quantity': 100}]},
        }
        client = AliasClient(event=event, market=market, contracts=contracts, quotes=quotes)
        with tempfile.TemporaryDirectory() as tmp:
            ev_dir = Path(tmp) / 'evidence'
            smarkets_lines.collect(client, ev_dir, [match])
            row = smarkets_lines.rows(ev_dir)[0]
            quote, detail = originate.market_estimate(row, match, {'aliases': []}, NOW)
            self.assertIsNone(quote)
            self.assertIn('spread', str(detail).lower())


class VerificationArtifactsTests(unittest.TestCase):
    def test_session_flags_json_has_official_https_links_and_valid_schema(self):
        flags = json.loads((ROOT / 'data/research/80c3b4e0/flags.json').read_text())
        self.assertGreaterEqual(len(flags), 5)
        ids = set()
        for f in flags:
            self.assertNotIn(f['id'], ids)
            ids.add(f['id'])
            self.assertIn(f['severity'], ('warning', 'notice'))
            self.assertIsInstance(f['match_ids'], list)
            self.assertTrue(f['title'].strip())
            self.assertTrue(f['detail'].strip())
            self.assertGreaterEqual(len(f['source_urls']), 1)
            for url in f['source_urls']:
                self.assertTrue(url.startswith('https://'), url)

    def test_verify_module_reconciles_checked_in_and_published_data(self):
        verify_mod = importlib.import_module('scripts.80c3b4e0_verify')
        report = verify_mod.build_report(ROOT)
        self.assertEqual(report['checked_in_replay_audit']['prob_sum_errors'], [])
        self.assertEqual(report['checked_in_replay_audit']['missing_source_urls'], [])
        self.assertEqual(report['checked_in_replay_audit']['hotspawn_probability_leaks'], [])
        self.assertEqual(report['published_live_table_audit']['unlinked_rows'], [])
        self.assertTrue(report['smarkets_alias_binding_verification']['all_passed'])


if __name__ == '__main__':
    unittest.main()
