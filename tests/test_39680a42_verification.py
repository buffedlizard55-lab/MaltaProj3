"""Regression tests for session arena-39680a42's source-side verification (tasks 3968-1 / 3968-3).

These pin the rules the verifier enforces, so a future change that re-introduces one
of the mistakes this session was checking for fails here:

* a published pair that does not sum to 1, or a pick that names the smaller side;
* a row whose probability source is a Hotspawn page (the brief forbids using Hotspawn
  crowd data as a probability input);
* an identity chain whose three sources disagree on the start time;
* a live coverage gap that no longer matches the recorded dossier;
* an executive summary that loses the in-site path to the picks.

Run:  python -m unittest tests.test_39680a42_verification -v
"""
from __future__ import annotations

import importlib
import unittest
from pathlib import Path

v = importlib.import_module('scripts.39680a42_verify')


def snapshot_with(**overrides):
    row = {
        'id': '1000000',
        'teams': [{'id': '1', 'name': 'Alpha'}, {'id': '2', 'name': 'Bravo'}],
        'availability': 'open',
        'analysis': {
            'method': 'market',
            'probabilities': [0.2, 0.8],
            'source_url': 'https://polymarket.com/event/cs2-alpha-bravo-2026-10-31',
        },
        'pick_index': 1,
    }
    row.update(overrides)
    return {'matches': [row], 'featured': {'picked': 1, 'unresolved': 0}}


def live_lobby(**overrides):
    base = {
        'lobby_open_ids': ['1000000', '1000001'],
        'coverage_gap_ids': ['1000001'],
        'deployed_snapshot_upcoming_ids': ['1000000'],
    }
    base.update(overrides)
    return base


def identity_chain(**overrides):
    base = {
        'hotspawn_fixture': {'id': '1082792', 'teams': ['HOTU', 'The Huns'],
                             'starts_at': '2026-10-31T09:00:00Z'},
        'polymarket_event': {'slug': 'cs2-hotu-the9-2026-10-31', 'outcomes': ['HOTU', 'The Huns Esports'],
                             'eventStartTime': '2026-10-31T09:00:00Z'},
        'hltv_match': {'format': 'Best of 3 (LAN)', 'start_iso': '2026-10-31T09:00:00Z'},
        'deployed_executive_summary_row': {'source_link': 'https://polymarket.com/event/cs2-hotu-the9-2026-10-31'},
    }
    base.update(overrides)
    return base


EXEC_HTML = """
<html><body>
<section id="start-here"><a href="./picks/">picks</a><a href="./unresolved/">unresolved</a>
<a href="./origination/#picks">origination</a></section>
<section id="picks-at-a-glance"><li class="glance-row" data-glance-id="1082792">
<span class="glance-pick-label" data-glance-pick>Pick</span><strong>HOTU</strong>
<span class="glance-prob">87.0%</span><span class="glance-other">The Huns 13.0%</span>
<a class="source-link" href="https://polymarket.com/event/cs2-hotu-the9-2026-10-31">Polymarket</a>
</li></section>
<section id="unresolved-register"></section><section id="no-line-register"></section>
<section id="fallback-register"></section></body></html>
"""


class PublishedArithmetic(unittest.TestCase):
    def test_pair_must_sum_to_one(self):
        errors, _ = v.check_published_arithmetic(snapshot_with(
            analysis={'method': 'market', 'probabilities': [0.6, 0.6], 'source_url': 'https://x.test'}))
        self.assertTrue(any('sum to' in e for e in errors))

    def test_pick_must_name_the_larger_side(self):
        errors, _ = v.check_published_arithmetic(snapshot_with(pick_index=0))
        self.assertTrue(any('larger side' in e for e in errors))

    def test_unresolved_row_is_recorded_not_failed(self):
        errors, stats = v.check_published_arithmetic(snapshot_with(analysis=None, pick_index=None))
        self.assertEqual(errors, [])
        self.assertEqual(stats['unresolved'], ['1000000'])


class SourceLinks(unittest.TestCase):
    def test_hotspawn_page_cannot_be_a_probability_source(self):
        errors, _ = v.check_source_links(snapshot_with(
            analysis={'method': 'market', 'probabilities': [0.2, 0.8],
                      'source_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1082792'}))
        self.assertTrue(any('Hotspawn' in e for e in errors))

    def test_non_https_source_is_flagged(self):
        errors, _ = v.check_source_links(snapshot_with(
            analysis={'method': 'market', 'probabilities': [0.2, 0.8],
                      'source_url': 'http://polymarket.com/event/x'}))
        self.assertTrue(any('not https' in e for e in errors))

    def test_official_source_passes(self):
        errors, rows = v.check_source_links(snapshot_with())
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]['host'], 'polymarket.com')


class IdentityChain(unittest.TestCase):
    def test_start_time_must_agree_across_sources(self):
        chain = identity_chain()
        chain['hltv_match']['start_iso'] = '2026-11-01T09:00:00Z'
        self.assertTrue(v.check_identity_chain(chain, chain['deployed_executive_summary_row']))

    def test_polymarket_must_name_the_fixture(self):
        chain = identity_chain(polymarket_event={'slug': 'cs2-hotu-the9-2026-10-31',
                                                 'outcomes': ['HOTU', 'Someone Else'],
                                                 'eventStartTime': '2026-10-31T09:00:00Z'})
        self.assertTrue(v.check_identity_chain(chain, chain['deployed_executive_summary_row']))

    def test_agreeing_chain_passes(self):
        self.assertEqual(v.check_identity_chain(identity_chain(), identity_chain()['deployed_executive_summary_row']), [])


class Coverage(unittest.TestCase):
    def test_gap_must_match_the_dossier(self):
        errors, _ = v.check_coverage_reconciliation(snapshot_with(), live_lobby())
        self.assertEqual(errors, [])

    def test_unrecorded_live_fixture_is_flagged(self):
        live = live_lobby(lobby_open_ids=['1000000', '1000001', '1000002'])
        errors, stats = v.check_coverage_reconciliation(snapshot_with(), live)
        self.assertTrue(any('coverage gap drift' in e for e in errors))


class ExecutiveSummary(unittest.TestCase):
    def test_missing_picks_link_is_flagged(self):
        errors, _ = v.check_executive_summary(EXEC_HTML.replace('href="./picks/"', 'href="https://elsewhere.test"'))
        self.assertTrue(any('./picks/' in e for e in errors))

    def test_row_without_source_link_is_flagged(self):
        html = EXEC_HTML.replace('<a class="source-link" href="https://polymarket.com/event/cs2-hotu-the9-2026-10-31">Polymarket</a>', '')
        errors, _ = v.check_executive_summary(html)
        self.assertTrue(any('no source link' in e for e in errors))

    def test_contract_holds_on_the_deployed_landing_page(self):
        html = Path(v.INDEX_HTML).read_text(encoding='utf-8')
        errors, stats = v.check_executive_summary(html)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(stats['glance_rows'], 10)


class RealTree(unittest.TestCase):
    def test_the_checked_in_tree_passes_every_check(self):
        result = v.run()
        self.assertEqual(result['errors'], [])


if __name__ == '__main__':
    unittest.main()
