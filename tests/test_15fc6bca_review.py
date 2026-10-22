"""Tests for session 15fc6bca's live coverage review probe.

The review probe is evidence-only tooling: it copies the ladder's own published
output and never computes a probability. What it must get right is the reading
of that output — a 50/50 row is ``even`` (not picked, not unresolved), a relayed
bookmaker price counts as money-backed, the freshness verdict follows the
published 4 h / 8 h contract, and summary links are resolved against the anchors
that actually exist in the built page.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from scripts.coverage_review_15fc6bca import (AnchorParser, classify, freshness,
                                              markdown, summary_links)

UTC = timezone.utc
NOW = datetime(2026, 10, 22, 3, 0, tzinfo=UTC)


def row(**over):
    base = {'id': '1', 'teams': [{'id': 'a', 'name': 'Alpha'}, {'id': 'b', 'name': 'Beta'}],
            'competition': 'C', 'starts_at': '2026-10-22T14:00:00Z', 'availability': 'open',
            'origination': {'method': 'model', 'family': 'model', 'label': 'm',
                            'source': 'Valve official standings',
                            'source_url': 'https://example.test/v',
                            'probabilities': [0.62, 0.38]},
            'pick_index': 0, 'limitations': [], 'research': []}
    base.update(over)
    return base


class ClassifyTest(unittest.TestCase):
    def test_model_row_is_own_estimate_not_money_backed(self):
        out = classify(row())
        self.assertEqual(out['state'], 'picked')
        self.assertEqual(out['pick'], 'Alpha')
        self.assertFalse(out['money_backed'])

    def test_relayed_bookmaker_row_counts_as_money_backed(self):
        out = classify(row(origination={'method': 'bookmaker', 'family': 'relay',
                                        'label': 'Esportsbook line relayed by bo3.gg', 'source': 'x',
                                        'source_url': 'https://bo3.gg/matches/x',
                                        'probabilities': [0.39, 0.61]}, pick_index=1))
        self.assertTrue(out['money_backed'])
        self.assertEqual(out['pick'], 'Beta')

    def test_even_row_is_its_own_state(self):
        out = classify(row(origination={'method': 'model', 'probabilities': [0.5, 0.5],
                                        'source_url': 'https://example.test/v'}, pick_index=None))
        self.assertEqual(out['state'], 'even')
        self.assertIsNone(out['pick'])

    def test_blank_row_is_unresolved(self):
        out = classify(row(origination=None, pick_index=None))
        self.assertEqual(out['state'], 'unresolved')
        self.assertFalse(out['money_backed'])

    def test_sources_without_price_falls_back_to_the_ledger(self):
        out = classify(row(sources_checked=[{'source': 'Kalshi', 'outcome': 'unresolved'},
                                            {'source': 'Polymarket', 'outcome': 'resolved'}]))
        self.assertEqual(out['sources_without_price'], ['Kalshi'])


class FreshnessTest(unittest.TestCase):
    def test_snapshot_inside_the_contract(self):
        latest = {'generated_at': '2026-10-22T02:00:00Z', 'inventory_observed_at': '2026-10-22T01:59:00Z',
                  'refresh_interval_hours': 4, 'stale_after_hours': 8, 'counts': {'upcoming': 35}}
        out = freshness(latest, NOW)
        self.assertTrue(out['within_contract'])
        self.assertTrue(out['fresh'])
        self.assertAlmostEqual(out['age_hours'], 1.0167, places=3)

    def test_snapshot_older_than_eight_hours_is_outside_the_contract(self):
        latest = {'inventory_observed_at': '2026-10-21T18:00:00Z'}
        out = freshness(latest, NOW)
        self.assertFalse(out['within_contract'])
        self.assertFalse(out['fresh'])

    def test_published_contract_defaults_are_four_and_eight_hours(self):
        out = freshness({'inventory_observed_at': '2026-10-22T02:00:00Z'}, NOW)
        self.assertEqual(out['refresh_interval_hours'], 4)
        self.assertEqual(out['stale_after_hours'], 8)


class AnchorTest(unittest.TestCase):
    def test_parser_collects_ids_and_link_text(self):
        page = AnchorParser()
        page.feed('<div id="picks"></div><a href="./origination/#match-1">Alpha vs Beta</a>'
                  '<a href="https://x.test">External</a>')
        self.assertIn('picks', page.ids)
        self.assertEqual(page.hrefs[0]['text'], 'Alpha vs Beta')
        self.assertEqual(len(page.hrefs), 2)

    def test_summary_links_report_a_missing_anchor(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / 'origination').mkdir()
            (site / 'index.html').write_text('<a href="./origination/#picks">Picks</a>'
                                             '<a href="./origination/#match-9">Nine</a>')
            (site / 'origination' / 'index.html').write_text('<div id="picks"></div>')
            out = summary_links(site)
            self.assertEqual(len(out['broken']), 1)
            self.assertEqual(out['broken'][0]['anchor'], 'match-9')
            self.assertTrue(out['picks_anchor_present'])
            self.assertFalse(out['unresolved_anchor_present'])

    def test_markdown_names_each_fixture_without_a_pick(self):
        report = {'generated_at': 'x', 'freshness': {'inventory_observed_at': 'y', 'generated_at': 'y',
                                                     'age_hours': 0.5, 'refresh_interval_hours': 4,
                                                     'stale_after_hours': 8},
                  'totals': {'upcoming': 2, 'picked': 1, 'even': 0, 'unresolved': 1,
                             'money_backed': 1, 'own_model': 0, 'paid_by_relay': 0},
                  'rows': [classify(row()), classify(row(id='2', origination=None, pick_index=None,
                                                        teams=[{'name': 'Gamma'}, {'name': 'Delta'}]))],
                  'no_pick': [{'id': '2', 'teams': ['Gamma', 'Delta'], 'state': 'unresolved',
                               'sources_without_price': ['Polymarket', 'Kalshi']}],
                  'summary_links': {'status': 'checked', 'links_into_picks': 2, 'broken': [],
                                    'picks_anchor_present': True, 'unresolved_anchor_present': True},
                  'cards': {'status': 'checked', 'rows': 2, 'cards_present': 2, 'missing': []}}
        text = markdown(report)
        self.assertIn('Gamma vs Delta', text)
        self.assertIn('Polymarket, Kalshi', text)


if __name__ == '__main__':
    unittest.main()
