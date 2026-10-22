"""Tests for the independent line-by-line audit (session arena-e5cc3d49)."""
from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import e5cc3d49_audit as audit

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)


def fixture(match_id='1', method='market', probs=(0.6, 0.4), quotes=None, **extra):
    row = {
        'id': match_id,
        'teams': [{'id': '10', 'name': 'Alpha'}, {'id': '11', 'name': 'Beta'}],
        'availability': 'open',
        'source_url': f'https://www.hotspawn.com/matches/alpha-vs-beta-cup-{match_id}',
        'lobby_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{match_id}',
        'pick_index': 0 if probs[0] > probs[1] else 1,
        'origination': {
            'method': method,
            'label': 'test',
            'probabilities': list(probs),
            'fair_decimal': [round(1 / p, 3) for p in probs],
            'observed_at': '2026-10-22T07:00:00Z',
            'source': 'test source',
            'source_url': 'https://polymarket.com/event/test',
            'quotes': quotes or [],
            'limitations': [],
        },
        'research': [], 'limitations': [],
    }
    row['origination']['source_outcomes'] = ['Alpha', 'Beta']
    row.update(extra)
    return row


def payload(rows):
    latest = {'matches': [{'id': r['id'], 'availability': r['availability']} for r in rows]}
    counts = {}
    for r in rows:
        method = (r.get('origination') or {}).get('method')
        key = 'unresolved' if method is None else method
        counts[key] = counts.get(key, 0) + 1
    return latest, {'matches': rows, 'counts': counts}


def run(rows, evidence=None, site=None):
    latest, orig = payload(rows)
    return audit.audit_payload(latest, orig, site, evidence or Path('/nonexistent'), now=NOW)


class RecomputeTests(unittest.TestCase):
    def test_market_midpoints_reproduce_probability(self):
        quotes = [
            {'provider': 'Polymarket', 'family': 'market', 'bid': 0.58, 'ask': 0.62},
            {'provider': 'Polymarket', 'family': 'market', 'bid': 0.38, 'ask': 0.42},
        ]
        report = run([fixture(quotes=quotes)])
        self.assertEqual(report['violations'], [])
        self.assertEqual(report['totals']['recomputed'], 1)

    def test_market_midpoint_mismatch_is_a_violation(self):
        quotes = [
            {'provider': 'Polymarket', 'family': 'market', 'bid': 0.70, 'ask': 0.72},
            {'provider': 'Polymarket', 'family': 'market', 'bid': 0.28, 'ask': 0.30},
        ]
        report = run([fixture(quotes=quotes)])
        self.assertTrue(any('bid/ask midpoint does not reproduce' in v for v in report['violations']))

    def test_saved_order_book_is_replayed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'polymarket-book-99-0.json').write_text(json.dumps(
                {'bids': [{'price': '0.57', 'size': '10'}, {'price': '0.58', 'size': '5'}],
                 'asks': [{'price': '0.63', 'size': '4'}, {'price': '0.62', 'size': '9'}]}))
            Path(tmp, 'polymarket-book-99-1.json').write_text(json.dumps(
                {'bids': [{'price': '0.37', 'size': '10'}, {'price': '0.38', 'size': '5'}],
                 'asks': [{'price': '0.43', 'size': '4'}, {'price': '0.42', 'size': '9'}]}))
            quotes = [
                {'provider': 'Polymarket', 'family': 'market', 'bid': 0.58, 'ask': 0.62},
                {'provider': 'Polymarket', 'family': 'market', 'bid': 0.38, 'ask': 0.42},
            ]
            row = fixture(quotes=quotes)
            row['origination']['event_id'] = '99'
            report = run([row], evidence=Path(tmp))
            self.assertEqual(report['violations'], [])
            self.assertTrue(any('saved order book reproduces Alpha bid/ask' in c for c in report['rows'][0]['checks']))

    def test_reversed_outcome_order_maps_books_by_name(self):
        """A market whose outcome order is reversed must not be flagged.

        Polymarket publishes 'Phantom Academy vs Falcons Force' while Hotspawn
        lists 'Falcons Force vs Phantom Academy'; the collector reorders the
        quotes, so the audit has to pair each team with its own book rather than
        with the book of the same position.
        """
        quotes = [
            {'provider': 'Polymarket', 'family': 'market', 'bid': 0.58, 'ask': 0.62},
            {'provider': 'Polymarket', 'family': 'market', 'bid': 0.38, 'ask': 0.42},
        ]
        row = fixture(quotes=quotes)
        row['origination']['source_outcomes'] = ['Beta', 'Alpha']
        row['origination']['event_id'] = '98'
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            # book 0 is Beta (the second Hotspawn team), book 1 is Alpha
            Path(tmp, 'polymarket-book-98-0.json').write_text(json.dumps(
                {'bids': [{'price': '0.38', 'size': '10'}], 'asks': [{'price': '0.42', 'size': '4'}]}))
            Path(tmp, 'polymarket-book-98-1.json').write_text(json.dumps(
                {'bids': [{'price': '0.58', 'size': '10'}], 'asks': [{'price': '0.62', 'size': '4'}]}))
            report = run([row], evidence=Path(tmp))
        self.assertEqual(report['violations'], [])
        self.assertTrue(any('books mapped' in c for c in report['rows'][0]['checks']))
        self.assertTrue(any('reproduces Alpha bid/ask' in c for c in report['rows'][0]['checks']))

    def test_bookmaker_odds_reproduce_probability(self):
        quotes = [{'provider': 'Thunderpick', 'family': 'thunderpick', 'odds': [1.5, 2.5]}]
        report = run([fixture(method='bookmaker', probs=(0.625, 0.375), quotes=quotes)])
        self.assertEqual(report['violations'], [])
        self.assertEqual(report['totals']['recomputed'], 1)

    def test_bookmaker_odds_mismatch(self):
        quotes = [{'provider': 'Thunderpick', 'family': 'thunderpick', 'odds': [1.2, 6.0]}]
        report = run([fixture(method='bookmaker', probs=(0.625, 0.375), quotes=quotes)])
        self.assertTrue(any('quoted odds do not reproduce' in v for v in report['violations']))

    def test_consensus_median(self):
        quotes = [
            {'provider': 'Polymarket', 'family': 'market', 'probabilities': [0.55, 0.45]},
            {'provider': 'Kalshi', 'family': 'market', 'probabilities': [0.65, 0.35]},
            {'provider': 'Thunderpick', 'family': 'thunderpick', 'probabilities': [0.60, 0.40]},
        ]
        report = run([fixture(method='consensus', probs=(0.60, 0.40), quotes=quotes)])
        self.assertEqual(report['violations'], [])
        self.assertTrue(any('median of 3 independent providers' in c for c in report['rows'][0]['checks']))

    def test_valve_points_recompute(self):
        a = audit._valve_probability(1600, 1500)
        quotes = []
        row = fixture(method='model', probs=(a, 1 - a), quotes=quotes)
        row['origination'].update({'provider': 'Valve official standings',
                                   'inputs': [{'name': 'Alpha', 'points': 1600, 'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'},
                                              {'name': 'Beta', 'points': 1500, 'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'}]})
        report = run([row])
        self.assertEqual(report['violations'], [])
        self.assertEqual(report['totals']['recomputed'], 1)

    def test_unrecomputable_model_is_named_not_verified(self):
        quotes = [{'provider': 'bo3.gg graph', 'family': 'network', 'probabilities': [0.7, 0.3],
                   'source_url': 'https://bo3.gg/matches'}]
        row = fixture(method='model', probs=(0.7, 0.3), quotes=quotes)
        row['origination']['family'] = 'network'
        report = run([row])
        self.assertEqual(report['violations'], [])
        self.assertEqual(len(report['not_recomputable']), 1)
        self.assertIn('not independently recomputable', report['not_recomputable'][0]['reason'])


class RowContractTests(unittest.TestCase):
    def test_pick_must_be_argmax(self):
        quotes = [
            {'provider': 'Polymarket', 'family': 'market', 'bid': 0.58, 'ask': 0.62},
            {'provider': 'Polymarket', 'family': 'market', 'bid': 0.38, 'ask': 0.42},
        ]
        row = fixture(quotes=quotes)
        row['pick_index'] = 1
        report = run([row])
        self.assertTrue(any('published pick is not the higher-probability side' in v for v in report['violations']))

    def test_missing_source_is_a_violation(self):
        quotes = [{'provider': 'Thunderpick', 'family': 'thunderpick', 'odds': [1.5, 2.5]}]
        row = fixture(method='bookmaker', probs=(0.625, 0.375), quotes=quotes)
        row['origination']['source_url'] = 'http://insecure.example/x'
        quotes[0]['source_url'] = 'http://insecure.example/x'
        report = run([row])
        self.assertTrue(any('no https source link' in v for v in report['violations']))

    def test_stale_active_row_is_flagged(self):
        quotes = [{'provider': 'Thunderpick', 'family': 'thunderpick', 'odds': [1.5, 2.5]}]
        row = fixture(method='bookmaker', probs=(0.625, 0.375), quotes=quotes)
        row['origination']['observed_at'] = '2026-10-21T00:00:00Z'
        report = run([row])
        self.assertTrue(any('older than 8h' in v for v in report['violations']))

    def test_unresolved_row_needs_trail_and_limitation(self):
        row = fixture()
        row['origination'] = None
        row['pick_index'] = None
        row['research'] = [{'stage': 'HLTV', 'source_url': 'https://www.hltv.org/matches', 'detail': 'no exact fixture'}]
        report = run([row])
        self.assertTrue(any('unresolved without a published limitation' in v for v in report['violations']))
        row['limitations'] = ['No two-sided price.']
        report = run([row])
        self.assertEqual([v for v in report['violations'] if 'unresolved' in v], [])

    def test_counts_must_reconcile(self):
        quotes = [{'provider': 'Thunderpick', 'family': 'thunderpick', 'odds': [1.5, 2.5]}]
        rows = [fixture('1', method='bookmaker', probs=(0.625, 0.375), quotes=quotes)]
        latest, orig = payload(rows)
        orig['counts']['bookmaker'] = 7
        report = audit.audit_payload(latest, orig, None, Path('/nonexistent'), now=NOW)
        self.assertTrue(any('published counts disagree' in v for v in report['violations']))

    def test_active_inventory_gap_is_a_violation(self):
        quotes = [{'provider': 'Thunderpick', 'family': 'thunderpick', 'odds': [1.5, 2.5]}]
        rows = [fixture('1', method='bookmaker', probs=(0.625, 0.375), quotes=quotes)]
        latest, orig = payload(rows)
        latest['matches'].append({'id': '2', 'availability': 'open'})
        report = audit.audit_payload(latest, orig, None, Path('/nonexistent'), now=NOW)
        self.assertTrue(any('have no pick row' in v for v in report['violations']))


class CheckedInSnapshotTests(unittest.TestCase):
    """The audit must pass on the repository's own snapshot (pinned clock)."""

    def test_repository_snapshot_has_no_violations_at_its_own_time(self):
        latest = json.loads((ROOT / 'data' / 'latest.json').read_text())
        orig = json.loads((ROOT / 'data' / 'origination.json').read_text())
        generated = datetime.fromisoformat(orig['generated_at'].replace('Z', '+00:00'))
        report = audit.audit_payload(latest, orig, None, ROOT / 'data' / 'evidence',
                                     now=generated + timedelta(hours=1))
        self.assertEqual(report['violations'], [])
        self.assertGreaterEqual(report['totals']['recomputed'], 10)
        self.assertEqual(report['totals']['rows'], len(orig['matches']))


if __name__ == '__main__':
    unittest.main()
