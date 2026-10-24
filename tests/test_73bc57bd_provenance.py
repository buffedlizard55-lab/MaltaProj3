"""Tests for the offline provenance replay of the published picks (session 73bc57bd).

Every case here is synthetic: a small snapshot plus the HTML fragments the audit
reads, so the checks stay deterministic when the published build changes. One
smoke test runs the audit against whatever build is committed in the branch root,
but asserts only the report's shape, never a row count or a value that a later
publish is entitled to change.
"""
from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path

provenance = importlib.import_module('scripts.73bc57bd_provenance')
review_register = importlib.import_module('scripts.review_register')

ROOT = Path(__file__).resolve().parent.parent


def market_match(**overrides) -> dict:
    match = {
        'id': '900001',
        'teams': [{'id': '1', 'name': 'Alpha'}, {'id': '2', 'name': 'Beta'}],
        'source_url': 'https://www.hotspawn.com/matches/alpha-vs-beta-cup-900001',
        'availability': 'open',
        'best_of': 3,
        'pick_index': 0,
        'analysis': {
            'method': 'market',
            'source': 'Polymarket',
            'source_url': 'https://polymarket.com/event/cs2-alpha-beta-2026-10-24',
            'probabilities': [0.6, 0.4],
            'quotes': [
                {'bid': 0.59, 'ask': 0.61, 'midpoint': 0.6},
                {'bid': 0.39, 'ask': 0.41, 'midpoint': 0.4},
            ],
        },
        'research': [],
    }
    match.update(overrides)
    return match


def model_match() -> dict:
    return {
        'id': '900002',
        'teams': [{'id': '3', 'name': 'Gamma'}, {'id': '4', 'name': 'Delta'}],
        'source_url': 'https://www.hotspawn.com/matches/gamma-vs-delta-cup-900002',
        'availability': 'open',
        'best_of': None,
        'pick_index': 0,
        'analysis': {
            'method': 'model',
            'source': 'Valve official standings',
            'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
            'probabilities': [1 / (1 + 10 ** (-120 * 0.972821 / 400)),
                              1 - 1 / (1 + 10 ** (-120 * 0.972821 / 400))],
            'inputs': [{'points': 1200}, {'points': 1080}],
            'g': 0.972821,
            'snapshot_date': '2026-10-05',
        },
        'research': [{'stage': 'HLTV research', 'status': 'checked',
                      'detail': 'Exact teams/time confirmed on HLTV; HLTV lists BO3; Hotspawn format remains separately unverified.',
                      'source_url': 'https://www.hltv.org/matches/2399999/gamma-vs-delta'}],
    }


def snapshot(*matches) -> dict:
    return {
        'generated_at': '2026-10-23T20:10:00Z',
        'counts': {'upcoming': len(matches), 'unresolved': 0, 'model': 0},
        'matches': list(matches),
    }


def codes(report: dict) -> list[str]:
    return [f['code'] for f in report['findings']]


class ProbabilityChecks(unittest.TestCase):
    def test_a_consistent_market_row_produces_no_finding(self):
        report = provenance.audit(snapshot(market_match()), {})
        self.assertEqual(report['findings'], [])
        self.assertEqual(report['rows_probability_reproduced'], 1)

    def test_probabilities_must_sum_to_one(self):
        match = market_match()
        match['analysis']['probabilities'] = [0.62, 0.30]
        report = provenance.audit(snapshot(match), {})
        self.assertIn('probabilities_sum', codes(report))

    def test_the_pick_must_be_the_more_likely_side(self):
        match = market_match(pick_index=1)
        report = provenance.audit(snapshot(match), {})
        self.assertIn('pick_is_argmax', codes(report))

    def test_a_quote_that_does_not_replay_is_reported(self):
        match = market_match()
        match['analysis']['probabilities'] = [0.52, 0.48]
        match['analysis']['quotes'] = [
            {'bid': 0.29, 'ask': 0.31, 'midpoint': 0.30},
            {'bid': 0.69, 'ask': 0.71, 'midpoint': 0.70},
        ]
        report = provenance.audit(snapshot(match), {})
        self.assertIn('probability_not_reproducible', codes(report))
        self.assertEqual(report['rows_probability_reproduced'], 0)


class ReplayArithmetic(unittest.TestCase):
    def test_market_rows_replay_the_midpoint(self):
        analysis = market_match()['analysis']
        self.assertEqual(provenance.replay_probabilities(analysis), [0.6, 0.4])

    def test_bookmaker_rows_replay_proportional_no_vig(self):
        analysis = {
            'method': 'bookmaker',
            'quotes': [{'odds': [1.6, 2.17]}],
        }
        replay = provenance.replay_probabilities(analysis)
        self.assertAlmostEqual(replay[0], (1 / 1.6) / (1 / 1.6 + 1 / 2.17), places=9)

    def test_model_rows_replay_the_logistic_of_the_rating_gap(self):
        match = model_match()
        replay = provenance.replay_probabilities(match['analysis'])
        expected = 1 / (1 + 10 ** (-120 * 0.972821 / 400))
        self.assertAlmostEqual(replay[0], expected, places=12)
        report = provenance.audit(snapshot(match), {})
        self.assertEqual(report['rows_probability_reproduced'], 1)
        self.assertNotIn('probability_not_reproducible', codes(report))

    def test_a_degenerate_price_is_reported_not_used(self):
        match = market_match()
        match['analysis'] = {
            'method': 'bookmaker', 'source': 'Thunderpick',
            'source_url': 'https://thunderpick.io/api/matches',
            'probabilities': [0.923, 0.077],
            'quotes': [{'odds': [1.001, 12]}],
        }
        found = {f['code'] for f in provenance.audit(snapshot(match), {})['findings']}
        self.assertIn('degenerate_price', found)


class EvidenceLinks(unittest.TestCase):
    def test_a_provider_index_is_not_a_fixture_source(self):
        self.assertTrue(provenance.is_generic_link('https://thunderpick.io/api/matches'))
        self.assertTrue(provenance.is_generic_link('https://bo3.gg/matches'))
        self.assertFalse(provenance.is_generic_link(
            'https://polymarket.com/event/cs2-alpha-beta-2026-10-24'))
        self.assertFalse(provenance.is_generic_link('https://www.hltv.org/matches/2399999/gamma-vs-delta'))

    def test_generic_link_is_flagged_on_the_row(self):
        match = market_match()
        match['analysis']['source_url'] = 'https://thunderpick.io/api/matches'
        match['analysis']['source'] = 'Thunderpick'
        match['analysis']['event_id'] = '2872333'
        report = provenance.audit(snapshot(match), {})
        finding = next(f for f in report['findings'] if f['code'] == 'generic_evidence_link')
        self.assertIn('2872333', finding['detail'])
        self.assertTrue(finding['evidence'][0]['url'].startswith('https://'))


class LayerChecks(unittest.TestCase):
    def test_a_page_pick_over_a_null_analysis_is_divergence(self):
        match = market_match()
        match['analysis'] = None
        match['pick_index'] = None
        page = ('<section id="match-900001"><span>✓ pick</span>'
                '<span>Alpha 44.9%</span><span>Beta 55.1%</span></section>')
        report = provenance.audit(snapshot(match), {'origination/index.html': page})
        self.assertIn('layer_divergence', codes(report))

    def test_a_page_without_a_pick_is_not_divergence(self):
        match = market_match()
        match['analysis'] = None
        match['pick_index'] = None
        page = '<section id="match-900001"><span>Not yet resolved</span></section>'
        report = provenance.audit(snapshot(match), {'origination/index.html': page})
        self.assertNotIn('layer_divergence', codes(report))

    def test_summary_claim_must_match_the_snapshot_counts(self):
        data = snapshot(market_match())
        data['counts']['unresolved'] = 2
        page = '<p>and <strong>0</strong> explicitly unresolved.</p>'
        report = provenance.audit(data, {'index.html': page})
        subjects = [f['subject'] for f in report['findings'] if f['code'] == 'layer_divergence']
        self.assertIn('summary', subjects)

    def test_a_verified_format_must_not_be_blank(self):
        match = model_match()
        report = provenance.audit(snapshot(match), {})
        self.assertIn('blank_format_with_confirmed_format', codes(report))

    def test_a_stated_format_silences_that_check(self):
        match = model_match()
        match['best_of'] = 3
        report = provenance.audit(snapshot(match), {})
        self.assertNotIn('blank_format_with_confirmed_format', codes(report))

    def test_an_old_rating_snapshot_is_disclosed_not_hidden(self):
        report = provenance.audit(snapshot(model_match()), {})
        finding = next(f for f in report['findings'] if f['code'] == 'stale_reference')
        self.assertEqual(finding['severity'], 'verified')
        self.assertIn('18 days old', finding['detail'])


class ReportShape(unittest.TestCase):
    def test_the_report_is_deterministic_and_complete(self):
        data = snapshot(market_match(), model_match())
        first = provenance.audit(data, {})
        second = provenance.audit(json.loads(json.dumps(data)), {})
        self.assertEqual(first, second)
        for key in ('snapshot_generated_at', 'snapshot_counts', 'rows_examined',
                    'rows_with_analysis', 'rows_probability_reproduced', 'findings_total',
                    'findings_by_code', 'rows_with_findings', 'findings'):
            self.assertIn(key, first)
        for finding in first['findings']:
            self.assertTrue(finding['code'] and finding['detail'] and finding['subject'])
            for item in finding['evidence']:
                self.assertTrue(item['url'].startswith('https://'))

    def test_the_committed_build_audits_without_error(self):
        if not (ROOT / 'snapshot.json').exists():
            self.skipTest('no published build in this checkout')
        snapshot_data, pages = provenance.load(ROOT)
        report = provenance.audit(snapshot_data, pages)
        self.assertGreaterEqual(report['rows_examined'], 1)
        self.assertIn('findings', report)
        self.assertEqual(
            report['rows_probability_reproduced'],
            sum(1 for m in snapshot_data['matches']
                if m.get('analysis') and provenance.replay_probabilities(m['analysis'])),
        )


class PublishedRegister(unittest.TestCase):
    def test_the_session_register_is_wired_and_valid(self):
        path = 'research/73bc57bd/repo-review.json'
        self.assertIn(path, review_register.REGISTERS)
        register = json.loads((ROOT / 'data' / path).read_text(encoding='utf-8'))
        review_register.validate(register)
        ids = {item['id'] for item in register['items']}
        self.assertIn('73bc57bd-every-published-probability-replays', ids)
        self.assertIn('73bc57bd-degenerate-1001-bookmaker-price', ids)
        self.assertIn('73bc57bd-snapshot-and-page-disagree-on-unresolved', ids)

    def test_the_dated_report_matches_the_audit_it_came_from(self):
        report_path = ROOT / 'data/research/73bc57bd/provenance-2026-10-24.json'
        report = json.loads(report_path.read_text(encoding='utf-8'))
        after = json.loads((ROOT / 'data/research/73bc57bd/provenance-after-deploy-2026-10-24.json')
                           .read_text(encoding='utf-8'))
        self.assertEqual(after['replay']['largest_drift'], 0.0)
        self.assertEqual(after['replay']['rows_probability_reproduced'],
                         after['replay']['rows_with_analysis'])
        self.assertTrue((ROOT / 'data/research/73bc57bd/provenance-after-deploy-2026-10-24.md').exists())
        self.assertEqual(report['replay']['largest_drift'], 0.0)
        self.assertEqual(report['replay']['rows_probability_reproduced'],
                         report['replay']['rows_with_analysis'])
        for finding in report['findings']:
            for item in finding['evidence']:
                self.assertTrue(item['url'].startswith('https://'))
        self.assertTrue((ROOT / 'data/research/73bc57bd/provenance-2026-10-24.md').exists())


if __name__ == '__main__':
    unittest.main()
