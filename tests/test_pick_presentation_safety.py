"""Synthetic, pinned-clock regressions: a source-backed lean is not always playable.

No fixture here is a real recommendation or enters the published data directory.
This file also writes private browser fixtures when invoked with --fixtures DIR.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import build_origination, build_strategy
from scripts.domain import iso
from scripts.pick_safety import body_attributes, card_attributes, presentation, valid_pair

UTC = timezone.utc
NOW = datetime(2026, 10, 16, 9, 0, tzinfo=UTC)
INVENTORY = '2026-10-16T08:30:00Z'
ROOT = Path(__file__).resolve().parents[1]


def fixture(mid='ready', *, observed='2026-10-16T08:00:00Z', starts='2026-10-16T21:00:00Z',
            locks='2026-10-16T20:54:00Z', availability='open', probabilities=None):
    return {'id': mid, 'competition': 'Synthetic test event (never published)', 'tier': 's',
            'teams': [{'id': 'test-a', 'name': 'Test Alpha'}, {'id': 'test-b', 'name': 'Test Beta'}],
            'starts_at': starts, 'locks_at': locks, 'availability': availability, 'pick_index': 0,
            'source_url': 'https://play.hotspawn.com/lobby', 'research': [], 'limitations': [],
            'origination': {'probabilities': probabilities or [0.65, 0.35], 'fair_decimal': [1.538, 2.857],
                            'method': 'market', 'label': 'Synthetic source-backed test estimate',
                            'source': 'Polymarket', 'source_url': 'https://polymarket.com/esports/cs2',
                            'observed_at': observed, 'quotes': [], 'limitations': []}}


def payload(matches=None, inventory=INVENTORY):
    matches = matches if matches is not None else [fixture()]
    return {'generated_at': iso(NOW), 'source_snapshot_at': inventory, 'matches': matches,
            'counts': {'active': len(matches), 'with_pick': sum(bool(m['origination']) for m in matches),
                       'unresolved': sum(not m['origination'] for m in matches), 'consensus': 0,
                       'market': sum(bool(m['origination']) for m in matches), 'bookmaker': 0, 'model': 0},
            'policy': {'ladder': ['Test fixtures only; never used as published evidence.'], 'rd_assumption': 75,
                       'start_tolerance_sec': 60, 'thin_spread': 0.12, 'max_accepted_spread': 0.12},
            'alias_registry': {'aliases': [], 'updated_at': iso(NOW), 'policy': 'Synthetic tests only.'},
            'sources': [{'name': 'Hotspawn', 'url': 'https://play.hotspawn.com/lobby', 'role': 'Fixture identity only.'}]}


def strategy_inputs(matches=None, *, inventory=INVENTORY, complete=True, bound=True):
    return {'rules': json.loads((ROOT / 'data/strategy-rules.json').read_text()),
            'latest': {'inventory_observed_at': inventory, 'coverage_complete': complete},
            'orig': {'matches': matches if matches is not None else [fixture()],
                     'source_snapshot_at': inventory if bound else '2026-10-16T08:00:00Z'},
            'fixtures': {}, 'contract': None, 'tournament': None, 'twc': None}


def cases():
    unresolved = fixture('unresolved')
    unresolved['origination'] = None
    unresolved['pick_index'] = None
    return [
        ('current', fixture(), INVENTORY, True, True),
        ('locked', fixture(locks='2026-10-16T08:59:59Z'), INVENTORY, True, True),
        ('started', fixture(starts=iso(NOW), locks='2026-10-16T08:54:00Z'), INVENTORY, True, True),
        ('unknown-lock', fixture(locks=None), INVENTORY, True, True),
        ('unknown-lock', fixture(starts=None), INVENTORY, True, True),
        ('unknown-lock', fixture(locks='2026-10-16T22:00:00Z'), INVENTORY, True, True),
        ('unknown-lock', fixture(availability='unknown_lock'), INVENTORY, True, True),
        ('inventory-unverified', fixture(), INVENTORY, False, True),
        ('stale-inventory', fixture(), '2026-10-16T00:59:59Z', True, True),
        ('stale-inventory', fixture(), None, True, True),
        ('stale-inventory', fixture(), '2026-10-16T09:05:01Z', True, True),
        ('unbound-snapshot', fixture(), INVENTORY, True, False),
        ('stale-line', fixture(observed='2026-10-16T00:59:59Z'), INVENTORY, True, True),
        ('stale-line', fixture(observed=None), INVENTORY, True, True),
        ('stale-line', fixture(observed='2026-10-16T09:05:01Z'), INVENTORY, True, True),
        ('stale-line', fixture(observed='2026-10-16T08:00:00'), INVENTORY, True, True),
        ('current', fixture(observed='2026-10-16T01:00:00Z'), INVENTORY, True, True),
        ('current', fixture(observed='2026-10-16T09:05:00Z'), INVENTORY, True, True),
        ('unresolved', unresolved, INVENTORY, True, True),
        ('unresolved', fixture(probabilities=[0.6, 0.6]), INVENTORY, True, True),
    ]


class SafetyDecisionTests(unittest.TestCase):
    def test_all_guards_are_explicit_and_preserve_input(self):
        for expected, match, inventory, complete, bound in cases():
            with self.subTest(expected=expected, match=match, inventory=inventory):
                before = copy.deepcopy(match)
                state = presentation(match, inventory, complete, NOW, snapshot_bound=bound)
                self.assertEqual(state['status'], expected)
                self.assertEqual(state['current'], expected == 'current')
                self.assertEqual(match, before, 'presentation must never edit picks, odds or source facts')

    def test_freshness_expires_at_first_deadline_not_page_build(self):
        state = presentation(fixture(), INVENTORY, True, NOW)
        self.assertEqual(state['expires_at'], '2026-10-16T16:00:00Z')
        self.assertEqual(presentation(fixture(), INVENTORY, True, NOW + timedelta(hours=7, seconds=1))['status'], 'stale-line')
        early_lock = fixture(locks='2026-10-16T09:01:00Z')
        self.assertEqual(presentation(early_lock, INVENTORY, True, NOW)['expires_at'], '2026-10-16T09:01:00Z')

    def test_invalid_probabilities_are_not_current(self):
        for values in (None, [0.5], [0, 1], [True, 0], [float('nan'), 0.4], [0.6, 0.6], ['0.6', '0.4']):
            self.assertFalse(valid_pair(values))

    def test_attributes_escape_untrusted_source_text(self):
        match = fixture(observed='"><img src=x>')
        state = presentation(match, INVENTORY, True, NOW)
        self.assertNotIn('<img', card_attributes(match, state))
        self.assertNotIn('<img', body_attributes('<img>', True))


class CompletePicksPresentationTests(unittest.TestCase):
    def render(self, match=None, *, inventory=INVENTORY, complete=True):
        return BeautifulSoup(build_origination.page(payload([match or fixture()], inventory), complete, now=NOW), 'html.parser')

    def test_fresh_pick_has_lock_and_quote_times_with_sources(self):
        soup = self.render()
        card = soup.select_one('.pick-card')
        self.assertEqual(card['data-safety-status'], 'current')
        self.assertIsNotNone(card.select_one('[data-current-only]:not([hidden])'))
        self.assertIn('Locks', card.select_one('.when').get_text())
        self.assertEqual(card.select_one('.line-time time')['datetime'], '2026-10-16T08:00:00Z')
        self.assertEqual(len(card.select('.probs li')), 2)
        self.assertTrue(card.select('a[href^="https://"]'))

    def test_expired_locked_unknown_and_incomplete_have_only_historical_cues_without_js(self):
        for kwargs, expected in (({'match': fixture(locks='2026-10-16T08:59:00Z')}, 'locked'),
                                 ({'match': fixture(observed='2026-10-16T00:00:00Z')}, 'stale-line'),
                                 ({'match': fixture(locks=None)}, 'unknown-lock'),
                                 ({'complete': False}, 'inventory-unverified'),
                                 ({'inventory': '2026-10-16T00:00:00Z'}, 'stale-inventory')):
            with self.subTest(expected=expected):
                card = self.render(**kwargs).select_one('.pick-card')
                self.assertEqual(card['data-safety-status'], expected)
                self.assertIsNone(card.select_one('[data-current-only]:not([hidden])'))
                self.assertIn('Snapshot lean', card.select_one('.pick-line').get_text())
                self.assertFalse(card.select_one('[data-safety-message]').has_attr('hidden'))
                self.assertEqual([p.get_text() for p in card.select('.probs strong')], ['65.0%', '35.0%'])

    def test_every_fixture_is_kept_even_if_closed_or_unresolved(self):
        rows = [fixture(), fixture('closed', locks='2026-10-16T08:00:00Z'), cases()[18][1]]
        before = copy.deepcopy(rows)
        soup = BeautifulSoup(build_origination.page(payload(rows), now=NOW), 'html.parser')
        self.assertEqual({c['id'] for c in soup.select('.pick-card')}, {'match-ready', 'match-closed', 'match-unresolved'})
        self.assertEqual(rows, before)
        self.assertIn('1', soup.select_one('[data-current-count]').get_text())
        self.assertIn('Labels', soup.select_one('noscript').get_text().replace('labels', 'Labels'))

    def test_invalid_probability_pair_is_blank_not_a_displayed_line(self):
        card = self.render(fixture(probabilities=[0.6, 0.6])).select_one('.pick-card')
        self.assertEqual(card['data-safety-status'], 'unresolved')
        self.assertEqual([p.get_text() for p in card.select('.probs strong')], ['—', '—'])
        self.assertNotIn('60.0%', card.get_text())

    def test_runtime_guards_are_local_and_do_not_depend_on_external_apis(self):
        soup = self.render()
        self.assertEqual(soup.select_one('script[src]')['src'], '../assets/pick-safety.js')
        self.assertEqual(soup.body['data-inventory-complete'], 'true')
        self.assertEqual(soup.body['data-inventory-at'], INVENTORY)


class LeaderboardPresentationTests(unittest.TestCase):
    def render(self, data):
        pl = build_strategy.plan(data, NOW)
        return pl, BeautifulSoup(build_strategy.page(data, pl), 'html.parser')

    def test_stale_lines_do_not_get_a_current_plan_or_score_slip(self):
        data = strategy_inputs([fixture(observed='2026-10-16T00:00:00Z')])
        pl, soup = self.render(data)
        card = soup.select_one('#slate .pick-card')
        self.assertEqual(pl['summary']['current'], 0)
        self.assertEqual(card['data-safety-status'], 'stale-line')
        self.assertTrue(card.select_one('.verdict').has_attr('hidden'))
        self.assertFalse(card.select_one('.snapshot-plan').has_attr('hidden'))
        self.assertEqual(len(card.select('.prob .num')), 2)
        self.assertEqual(pl['rows'][0]['p'], [0.65, 0.35])

    def test_no_swap_favorite_instruction_also_has_runtime_expiry_guard(self):
        data = strategy_inputs([fixture(probabilities=[0.9, 0.1])])
        pl, soup = self.render(data)
        self.assertEqual(pl['summary']['swaps'], 0)
        self.assertIsNotNone(soup.select_one('.callout.calm[data-safety-synopsis]'))
        self.assertNotIn('today, costing', soup.get_text())
        self.assertIn('across the listed fixtures (capped per UTC day)', soup.get_text())

    def test_unbound_and_unverified_inventory_have_no_current_advice_even_for_favorites(self):
        for kwargs, expected in (({'bound': False}, 'unbound-snapshot'), ({'complete': False}, 'inventory-unverified')):
            pl, soup = self.render(strategy_inputs(**kwargs))
            self.assertEqual(soup.select_one('#slate .pick-card')['data-safety-status'], expected)
            self.assertEqual(pl['summary']['current'], 0)
            self.assertTrue(soup.select_one('[data-safety-synopsis]').has_attr('hidden'))
            self.assertEqual(pl['rows'][0]['default'], pl['rows'][0]['fav'])


def write_fixtures(directory):
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'assets', directory / 'assets', dirs_exist_ok=True)
    rows = [fixture(), fixture('edge', observed='2026-10-16T01:00:00Z'),
            fixture('close', locks='2026-10-16T09:01:00Z'), fixture('unknown', locks=None), cases()[18][1]]
    for name, inventory, complete in [('origination', INVENTORY, True), ('stale-origination', '2026-10-16T00:00:00Z', True),
                                      ('incomplete-origination', INVENTORY, False)]:
        target = directory / name
        target.mkdir(exist_ok=True)
        target.joinpath('index.html').write_text(build_origination.page(payload(rows, inventory), complete, now=NOW))
    for name, kwargs in [('strategy', {}), ('stale-strategy', {'inventory': '2026-10-16T00:00:00Z'}),
                         ('mismatch-strategy', {'bound': False}), ('no-upsets-strategy', {'matches': [fixture(probabilities=[0.9, 0.1])]})]:
        defaults = {'matches': [fixture(), fixture('edge', observed='2026-10-16T01:00:00Z')]}
        defaults.update(kwargs)
        data = strategy_inputs(**defaults)
        pl = build_strategy.plan(data, NOW)
        target = directory / name
        target.mkdir(exist_ok=True)
        target.joinpath('index.html').write_text(build_strategy.page(data, pl))
    vectors = []
    for expected, match, inventory, complete, bound in cases():
        state = presentation(match, inventory, complete, NOW, snapshot_bound=bound)
        card = BeautifulSoup('<article ' + card_attributes(match, state) + '></article>', 'html.parser').article
        body = BeautifulSoup('<body ' + body_attributes(inventory, complete, snapshot_bound=bound) + '></body>', 'html.parser').body
        # dataset camelCase keys are exactly what the browser guard consumes.
        camel = lambda s: s.split('-')[0] + ''.join(x.title() for x in s.split('-')[1:])
        vectors.append({'expected': expected, 'card': {camel(k[5:]): v for k, v in card.attrs.items()},
                        'context': {camel(k[5:]): v for k, v in body.attrs.items()}, 'now': int(NOW.timestamp() * 1000)})
    (directory / 'vectors.json').write_text(json.dumps(vectors))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', type=Path)
    args, rest = parser.parse_known_args()
    if args.fixtures:
        write_fixtures(args.fixtures)
    else:
        unittest.main(argv=[sys.argv[0]] + rest)
