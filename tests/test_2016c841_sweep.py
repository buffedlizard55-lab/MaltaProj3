"""Session arena-2016c841 — the dated no-line sweep and its summary contract.

The brief asks for a pick or a sourced probability for every Hotspawn CS2
fixture, research for the ones the featured method cannot resolve (HLTV first,
then esportsbooks and esports betting lines), and a *separate* section in the
executive summary for anything unresolved with its limitations. This session's
probe (``scripts/2016c841_research.py``) is the 2026-10-23 mid-morning sweep and
adds verbatim Smarkets exchange evidence plus a fresh live-lobby coverage
comparison to the already-reviewed bo3.gg relay sweep.

These tests pin the rules the sweep must never break:

* joins onto bo3.gg and Smarkets are exact on BOTH team names plus a 60-second
  start window, and near misses are recorded as near misses;
* a two-sided price needs two *active* bo3 relay sides above 1.00, and a
  two-sided exchange quote needs both contracts carrying bids AND offers;
* the record copies bookmaker coefficients and exchange quote integers
  verbatim — nothing is divided, de-vigged or converted into a probability
  by the probe;
* the newest-wins loaders in ``scripts.build`` only promote eligible records:
  a runner sweep with a Markdown sibling for the no-line register, and any
  dated record that actually compared a non-empty lobby for the coverage gap
  register (a failed fetch can never replace a real observation);
* the coverage-gap section's dated-record links always point at the record
  actually rendered, never a hardcoded older sweep.
"""
from __future__ import annotations

import importlib
import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts.build import load_live_coverage, live_coverage_gaps, no_line_research_block

probe = importlib.import_module('scripts.2016c841_research')

UTC = timezone.utc


class ProbeJoinTests(unittest.TestCase):
    def row(self, **overrides):
        row = {'slug': 'a-vs-b-23-10-2026', 'start_date': '2026-10-23T13:00:00.000+00:00',
               'team1': {'name': '5star'}, 'team2': {'name': '1WIN'},
               'bet_updates': {'provider': 'thunderpick', 'path': 'https://thunderpick.io/match/1',
                               'team_1': {'name': '5star', 'coeff': 3.40, 'active': True, 'team_id': 1},
                               'team_2': {'name': '1WIN', 'coeff': 1.22, 'active': True, 'team_id': 2}}}
        row.update(overrides)
        return row

    def test_both_names_and_a_60s_start_window_are_required(self):
        start = datetime(2026, 10, 23, 13, 0, tzinfo=UTC)
        bound, near = probe.bind(['5star', '1WIN'], start, [self.row()])
        self.assertIsNotNone(bound)
        self.assertEqual(near, [])
        bound, near = probe.bind(['5star', '1WIN'], start,
                                 [self.row(start_date='2026-10-23T13:01:30.000+00:00')])
        self.assertIsNone(bound)
        self.assertIn('outside the 60s window', near[0]['status'])
        bound, near = probe.bind(['5star', 'Other'], start, [self.row()])
        self.assertIsNone(bound)
        self.assertTrue(near and near[0]['status'] == 'one shared side only')

    def test_two_sided_requires_two_active_sides_above_one(self):
        self.assertTrue(probe.relay_block(self.row())['two_sided_price'])
        stale = self.row()
        stale['bet_updates']['team_2']['active'] = False
        self.assertFalse(probe.relay_block(stale)['two_sided_price'])
        short = self.row()
        short['bet_updates']['team_2']['coeff'] = 1.0
        self.assertFalse(probe.relay_block(short)['two_sided_price'])
        self.assertIsNone(probe.relay_block(self.row(bet_updates=None)))

    def test_the_record_carries_no_probability_of_its_own(self):
        quote = probe.relay_block(self.row())
        self.assertEqual(set(quote), {'provider', 'book_url', 'markets_count', 'sides',
                                      'two_sided_price'})
        self.assertNotIn('probability', json.dumps(quote).lower())

    def test_hotspawn_url_matches_the_site_slug_form(self):
        self.assertEqual(
            probe.hotspawn_match_url(['MIBR', 'BC.Game'], 'Stake Pulse Beat III', '1079440'),
            'https://www.hotspawn.com/matches/mibr-vs-bc-game-stake-pulse-beat-iii-1079440')


class SmarketsSweepTests(unittest.TestCase):
    """The exchange sweep binds with the reviewed rule and copies quotes verbatim."""

    def _responses(self):
        return {
            'https://api.smarkets.com/v3/events/?type=csgo_match&states=upcoming&limit=200&sort=start_datetime,id': (
                {'http_status': 200},
                {'events': [{'id': 11, 'name': '5star vs 1WIN',
                             'start_datetime': '2026-10-31T14:00:00Z',
                             'full_slug': '/event/5star-vs-1win'},
                            {'id': 12, 'name': 'Someone Else vs Another',
                             'start_datetime': '2026-10-31T15:00:00Z'}]}),
            'https://api.smarkets.com/v3/events/11/markets/': (
                {'http_status': 200},
                {'markets': [{'id': 100, 'event_id': 11, 'state': 'open', 'hidden': False,
                              'market_type': {'name': 'WINNER_2_WAY'}},
                             {'id': 101, 'event_id': 11, 'state': 'suspended',
                              'market_type': {'name': 'WINNER_2_WAY'}}]}),
            'https://api.smarkets.com/v3/markets/100/contracts/': (
                {'http_status': 200},
                {'contracts': [{'id': 500, 'market_id': 100, 'name': '5star',
                                'state_or_outcome': 'open', 'contract_type': {'name': 'HOME'}},
                               {'id': 501, 'market_id': 100, 'name': '1WIN',
                                'state_or_outcome': 'open', 'contract_type': {'name': 'AWAY'}}]}),
            'https://api.smarkets.com/v3/markets/100/quotes/': (
                {'http_status': 200},
                {'500': {'bids': [{'price': '2210', 'quantity': '10000'}],
                         'offers': [{'price': '2450', 'quantity': '10000'}]},
                 '501': {'bids': [{'price': '7550', 'quantity': '10000'}],
                         'offers': [{'price': '7790', 'quantity': '10000'}]}}),
        }

    def target(self):
        return [{'hotspawn_id': '1082793', 'teams': [{'name': '5star'}, {'name': '1WIN'}],
                 'starts_at': '2026-10-31T14:00:00Z'}]

    def _run(self, responses):
        def fake_fetch_json(session, url, *, headers=None, timeout=25):
            attempt, body = responses.get(url, ({'http_status': 404}, {}))
            return {'url': url, 'method': 'GET', 'observed_at': '2026-10-23T10:00:00Z',
                    **attempt}, body
        with mock.patch.object(probe, 'fetch_json', side_effect=fake_fetch_json):
            return probe.smarkets_sweep(object(), self.target())

    def test_two_sided_quote_is_copied_verbatim_and_never_divided(self):
        board, per_fixture = self._run(self._responses())
        self.assertEqual(board['bound'], 1)
        entry = per_fixture['1082793']
        self.assertTrue(entry['two_sided'])
        self.assertEqual(entry['quotes']['500']['bids'][0]['price'], '2210')
        # 0.221 would be a derived probability; the probe must never write it.
        self.assertNotIn('0.221', json.dumps(entry))
        self.assertNotIn('probability', json.dumps(entry).lower())

    def test_one_sided_book_is_not_two_sided(self):
        responses = self._responses()
        url = 'https://api.smarkets.com/v3/markets/100/quotes/'
        responses[url] = ({'http_status': 200},
                          {'500': {'bids': [], 'offers': [{'price': '2450'}]},
                           '501': {'bids': [{'price': '7550'}], 'offers': [{'price': '7790'}]}})
        _, per_fixture = self._run(responses)
        self.assertFalse(per_fixture['1082793']['two_sided'])

    def test_ambiguous_or_suspended_markets_price_nothing(self):
        responses = self._responses()
        url = 'https://api.smarkets.com/v3/events/11/markets/'
        responses[url] = ({'http_status': 200},
                          {'markets': [{'id': 100, 'event_id': 11, 'state': 'open', 'hidden': False,
                                        'market_type': {'name': 'WINNER_2_WAY'}},
                                       {'id': 101, 'event_id': 11, 'state': 'open', 'hidden': False,
                                        'market_type': {'name': 'WINNER_2_WAY'}}]})
        _, per_fixture = self._run(responses)
        # Two open two-way winner markets for one event is ambiguous.
        self.assertFalse(per_fixture['1082793']['two_sided'])
        self.assertIsNone(per_fixture['1082793']['quotes'])

    def test_name_or_start_mismatch_binds_nothing(self):
        target = self.target()
        target[0]['teams'] = [{'name': '5star'}, {'name': 'Wrong Team'}]
        with mock.patch.object(probe, 'fetch_json',
                               side_effect=lambda s, u, **k: ({'http_status': 200}, {'events': []})):
            board, per_fixture = probe.smarkets_sweep(object(), target)
        self.assertEqual(board['bound'], 0)
        self.assertEqual(per_fixture, {})


class ProbeRecordEligibilityTests(unittest.TestCase):
    def test_environment_is_reported_honestly(self):
        with mock.patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}):
            self.assertEqual(probe.environment_name(), 'github-actions-runner')
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(probe.environment_name(), 'local checkout')

    def test_the_probe_writes_every_file_it_declares(self):
        source = Path('scripts/2016c841_research.py').read_text()
        for name in ('line-source-research.json', 'line-source-research.md',
                     'live-coverage.json', 'live-coverage.md'):
            self.assertIn(f"'{name}'", source)
        self.assertIn("'environment': environment_name()", source)
        self.assertIn("'per_fixture': [compatible(record) for record in findings]", source)

    def test_published_probability_pair_is_read_in_team_order(self):
        """origination.json publishes a [home, away] pair; the home scalar is kept."""
        import tempfile
        payload = {'generated_at': '2026-10-23T10:14:39Z',
                   'matches': [{'id': '1082926', 'teams': [{'name': 'A'}, {'name': 'B'}],
                                'origination': {'method': 'market',
                                                'probabilities': [0.762, 0.238]}}]}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'origination.json'
            target.write_text(json.dumps(payload))
            methods, source = probe.published_methods(object(), Path(target))
        self.assertEqual(methods['1082926']['method'], 'market')
        self.assertEqual(methods['1082926']['probability'], 0.762)


class LiveCoverageLoaderTests(unittest.TestCase):
    """The coverage-gap register promotes the newest real observation only."""

    def _record(self, session, observed, fixtures=1, markdown=True):
        return session, observed, fixtures, markdown

    def _write(self, root, session, observed, fixtures=1, markdown=True):
        target = root / f'research/{session}/live-coverage.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        record = {'session': session, 'observed_at': observed,
                  'live_fixtures': [{'id': str(1000 + i), 'teams': ['A', 'B']}
                                    for i in range(fixtures)]}
        target.write_text(json.dumps(record))
        if markdown:
            target.with_suffix('.md').write_text('# Dated record\n')
        return target

    def test_newest_wins_and_links_follow_the_record(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, 'older', '2026-10-23T04:58:00Z')
            self._write(root, 'newer', '2026-10-23T10:15:00Z')
            record = load_live_coverage(root)
            self.assertEqual(record['session'], 'newer')
            self.assertEqual(record['_record_path'], 'research/newer/live-coverage.json')
            # The rendered section must link the record it describes.
            data = {'_live_coverage': record, 'matches': []}
            html = live_coverage_gaps(data, '')
            self.assertIn('data/research/newer/live-coverage.json', html)
            self.assertNotIn('data/research/older/', html)

    def test_a_failed_fetch_can_never_replace_a_real_observation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, 'real', '2026-10-23T04:58:00Z')
            # A newer but empty record (an unreachable lobby) must lose.
            self._write(root, 'empty', '2026-10-23T11:00:00Z', fixtures=0)
            self.assertEqual(load_live_coverage(root)['session'], 'real')
            # A record with no parseable timestamp is never eligible.
            newer = root / 'research/real/live-coverage.json'
            newer.write_text(json.dumps({'session': 'broken', 'live_fixtures': [{'id': '1'}]}))
            self.assertIsNone(load_live_coverage(root))

    def test_the_markdown_link_only_renders_for_a_real_sibling(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, 'older', '2026-10-23T04:58:00Z', markdown=False)
            record = load_live_coverage(root)
            self.assertIsNone(record['_markdown_path'])
            html = live_coverage_gaps({'_live_coverage': record, 'matches': []}, '')
            self.assertNotIn('Markdown ↓', html)


class NoLineBlockExchangeEvidenceTests(unittest.TestCase):
    def _data(self, per_fixture):
        return {'_no_line_research': {
            'observed_at': '2026-10-23T10:30:00Z',
            '_record_path': 'research/2016c841/line-source-research.json',
            'per_fixture': per_fixture}}

    def test_two_sided_exchange_evidence_is_listed_not_counted_as_nothing(self):
        data = self._data([{'id': '1082793', 'teams': ['5star', '1WIN'],
                            'money_line_lead': False,
                            'smarkets_evidence': {'two_sided': True,
                                                  'event_url': 'https://smarkets.com/event/5star-vs-1win'}}])
        html = no_line_research_block(data, '')
        self.assertIn('exchange quote', html)
        self.assertIn('https://smarkets.com/event/5star-vs-1win', html)
        self.assertIn('1</strong> fixture(s) also had two-sided exchange quote evidence', html)
        self.assertNotIn('0.2', html)  # no derived number, ever

    def test_exchange_evidence_is_not_double_counted_as_a_relay_lead(self):
        data = self._data([{'id': '1', 'teams': ['A', 'B'], 'money_line_lead': True,
                            'bo3_bet': {'provider': 'thunderpick', 'path': None,
                                        'team_1': {'name': 'A', 'coeff': 1.5},
                                        'team_2': {'name': 'B', 'coeff': 2.5}},
                            'smarkets_evidence': {'two_sided': True,
                                                  'event_url': 'https://smarkets.com/event/a-vs-b'}}])
        html = no_line_research_block(data, '')
        self.assertIn('1</strong> new money-line lead', html)
        self.assertNotIn('also had two-sided exchange quote evidence', html)

    def test_no_evidence_keeps_the_block_unchanged(self):
        data = self._data([{'id': '1', 'teams': ['A', 'B'], 'money_line_lead': False}])
        html = no_line_research_block(data, '')
        self.assertIn('No new money-line lead was found', html)
        self.assertNotIn('exchange quote', html)


if __name__ == '__main__':
    unittest.main()
