"""Pins the independent replay in :mod:`scripts.deea3ec4_verify`.

Session arena-deea3ec4. The published build is replayed from its own inputs, so
these tests are written as *properties*, not as snapshots of one fixture list:
they pass on any correctly published build and fail on a hand-edited number,
a missing external source, a pick that is not the favourite, a fixture the
snapshot should have covered, or an executive summary that stops being a phone
entry point to the picks.
"""
from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import deea3ec4_verify as verify

ROOT = Path(__file__).resolve().parent.parent
PUBLISHED = ('snapshot.json', 'origination.json', 'index.html', 'origination/index.html')


def _copy_published(target: Path) -> Path:
    for name in PUBLISHED:
        source = ROOT / name
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return target


class _Tree:
    """A throwaway copy of the published build that a test can corrupt."""

    def __init__(self):
        self._dir = tempfile.TemporaryDirectory()
        self.path = _copy_published(Path(self._dir.name))

    def close(self):
        self._dir.cleanup()

    def snapshot(self):
        return json.loads((self.path / 'snapshot.json').read_text())

    def origination(self):
        return json.loads((self.path / 'origination.json').read_text())

    def write_origination(self, data):
        (self.path / 'origination.json').write_text(json.dumps(data))

    def html(self):
        return (self.path / 'index.html').read_text()

    def write_html(self, text):
        (self.path / 'index.html').write_text(text)

    def run(self, **kwargs):
        return verify.run(self.path, **kwargs)


class _Base(unittest.TestCase):
    def setUp(self):
        self.tree = _Tree()

    def tearDown(self):
        self.tree.close()

    def first_priced_row(self, methods=('market', 'bookmaker', 'model')):
        data = self.tree.origination()
        for index, row in enumerate(data['matches']):
            method = (row.get('origination') or {}).get('method')
            if method in methods and row.get('pick_index') in (0, 1):
                return data, index, row
        self.skipTest('no priced row of the requested method in the published build')


class PublishedBuildTests(unittest.TestCase):
    """The tracked published build itself must replay with zero violations."""

    def test_every_published_row_replays_from_its_own_inputs(self):
        report = verify.run(ROOT)
        self.assertEqual(report['errors'], [])
        self.assertGreaterEqual(report['active_rows'], 1)
        for row in report['rows']:
            self.assertEqual(row['problems'], [], row['id'])
            if row['probabilities']:
                self.assertAlmostEqual(sum(row['probabilities']), 1.0, places=6)

    def test_named_pick_is_the_strict_favourite_of_its_two_numbers(self):
        data = json.loads((ROOT / 'origination.json').read_text())
        for row in data['matches']:
            probs = (row.get('origination') or {}).get('probabilities')
            if not probs:
                continue
            pick = row['pick_index']
            self.assertGreaterEqual(probs[pick], probs[1 - pick], row['id'])

    def test_every_money_row_cites_an_outside_https_source(self):
        data = json.loads((ROOT / 'origination.json').read_text())
        money = verify.MONEY_METHODS
        for row in data['matches']:
            origin = row.get('origination') or {}
            if origin.get('method') not in money:
                continue
            self.assertTrue(origin.get('source_url', '').startswith('https://'), row['id'])
            self.assertFalse(verify.is_vendor(origin['source_url']), row['id'])

    def test_phone_entry_point_contract(self):
        html = (ROOT / 'index.html').read_text()
        self.assertRegex(html, r'<meta[^>]+name="viewport"[^>]+width=device-width')
        self.assertIn('aria-label="Where to find the updated picks"', html)
        self.assertRegex(html, r'href="[^"]*origination/#picks"')
        self.assertRegex(html, r'href="[^"]*unresolved/"')
        self.assertIn('id="picks-at-a-glance"', html)
        self.assertIn('id="unresolved-register"', html)

    def test_inventory_gaps_are_only_fixtures_the_snapshot_pre_dates(self):
        report = verify.run(ROOT, inventory_path=Path('data/research/deea3ec4/live-coverage.json'))
        generated = report['snapshot_generated_at']
        inventory = json.loads((ROOT / 'data/research/deea3ec4/live-coverage.json').read_text())
        starts = {str(f['id']): f['starts_at_utc'] for f in inventory['live_fixtures']}
        for error in report['errors']:
            identity = error.split(':', 1)[0]
            self.assertIn(identity, starts, error)
            self.assertGreater(starts[identity], generated, error)


class ReplayArithmeticTests(unittest.TestCase):
    """The three arithmetic shapes the publisher records, checked directly."""

    def test_market_midpoint_pair_normalises_to_one(self):
        row = {'quotes': [{'bid': 0.18, 'ask': 0.22}, {'bid': 0.78, 'ask': 0.82}]}
        self.assertAlmostEqual(sum(verify.replay_market(row)), 1.0, places=9)
        self.assertAlmostEqual(verify.replay_market(row)[0], 0.2, places=9)

    def test_crossed_book_is_refused(self):
        with self.assertRaises(verify.Violation):
            verify.replay_market({'quotes': [{'bid': 0.55, 'ask': 0.45}, {'bid': 0.55, 'ask': 0.45}]})

    def test_bookmaker_margin_removal(self):
        probs = verify.replay_bookmaker({'quotes': [{'odds': [1.61, 2.18]}]})
        self.assertAlmostEqual(probs[0], 0.575197885, places=8)
        self.assertAlmostEqual(sum(probs), 1.0, places=12)

    def test_bookmaker_with_no_margin_is_refused(self):
        with self.assertRaises(verify.Violation):
            verify.replay_bookmaker({'quotes': [{'odds': [2.0, 2.0]}]})

    def test_valve_glicko_row(self):
        row = {'inputs': [{'points': 1110, 'source_url': 'https://example.org/a'},
                          {'points': 1383, 'source_url': 'https://example.org/b'}],
               'rd_assumption': 75, 'g': 0.9728209910486895}
        probs = verify.replay_model(row)
        self.assertAlmostEqual(probs[0], 0.17816902, places=8)

    def test_results_based_row_uses_its_sample_size(self):
        row = {'inputs': [{'points': 825, 'source_url': 'https://bo3.gg/x', 'fitted': {'n': 10}},
                          {'points': 923, 'source_url': 'https://example.org/valve'}],
               'rating_sd': 114.7}
        probs = verify.replay_model(row)
        self.assertAlmostEqual(probs[0], 0.390446058, places=8)

    def test_consensus_pair_is_the_per_side_median(self):
        row = {'quotes': [{'provider': 'Thunderpick', 'probabilities': [0.58201058, 0.41798942]},
                          {'provider': 'Bovada', 'probabilities': [0.58349699, 0.41650301]}]}
        probs = verify.replay_consensus(row)
        self.assertAlmostEqual(probs[0], 0.58275378, places=8)

    def test_consensus_counts_one_provider_once(self):
        row = {'quotes': [{'provider': 'Thunderpick', 'probabilities': [0.58, 0.42]},
                          {'provider': 'Thunderpick', 'probabilities': [0.60, 0.40]}]}
        with self.assertRaises(verify.Violation):
            verify.replay_consensus(row)


class MutationTests(_Base):
    """A hand-edited number, source or pick must fail the replay."""

    def test_scaled_probabilities_fail(self):
        data, index, row = self.first_priced_row()
        row['origination']['probabilities'] = [value * 1.1 for value in row['origination']['probabilities']]
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertTrue(any('sum to' in error for error in report['errors']), report['errors'])

    def test_pick_that_is_not_the_favourite_fails(self):
        data, index, row = self.first_priced_row()
        row['pick_index'] = 1 - row['pick_index']
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertTrue(any('not the favourite' in error for error in report['errors']), report['errors'])

    def test_edited_bookmaker_odds_fail_the_replay(self):
        data, index, row = self.first_priced_row(('bookmaker',))
        row['origination']['quotes'][0]['odds'] = [1.01, 100.0]
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertTrue(any('replay mismatch' in error for error in report['errors']), report['errors'])

    def test_edited_exchange_book_fails_the_replay(self):
        data, index, row = self.first_priced_row(('market',))
        quote = row['origination']['quotes'][0]
        if 'bid' in quote and isinstance(quote['bid'], (int, float)):
            quote['bid'], quote['ask'] = quote['bid'] * 0.5, quote['ask'] * 0.5
        elif isinstance(quote.get('bid'), list):
            quote['bid'] = [value * 0.5 for value in quote['bid']]
        else:
            self.skipTest('published market quote carries no two-sided book')
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertTrue(any('replay mismatch' in error for error in report['errors']), report['errors'])

    def test_missing_source_link_fails(self):
        data, index, row = self.first_priced_row()
        row['origination'].pop('source_url', None)
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertTrue(any('not an https link' in error for error in report['errors']), report['errors'])

    def test_hotspawn_as_probability_source_fails(self):
        data, index, row = self.first_priced_row()
        row['origination']['source_url'] = 'https://play.hotspawn.com/cs2-pickems'
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertTrue(any('cites Hotspawn' in error for error in report['errors']), report['errors'])

    def test_crowd_percentage_in_a_row_fails(self):
        data, index, row = self.first_priced_row()
        row['picked_percent'] = [76, 24]
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertTrue(any('crowd field' in error for error in report['errors']), report['errors'])

    def test_row_without_a_pick_fails(self):
        data, index, row = self.first_priced_row()
        row['pick_index'] = None
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertTrue(any('is not a side' in error for error in report['errors']), report['errors'])

    def test_unresolved_row_with_a_reason_is_a_warning_not_an_error(self):
        data, index, row = self.first_priced_row()
        row['origination'] = {'method': None, 'probabilities': None,
                              'limitations': ['No two-sided external price was published at the observation.']}
        row['pick_index'] = None
        row['featured_probabilities'] = None
        row['featured_pick_index'] = None
        row['research'] = [{'stage': 'HLTV identity', 'status': 'checked', 'detail': 'no bookmaker price'}]
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertEqual(report['errors'], [])
        self.assertTrue(any('unresolved' in warning for warning in report['warnings']))

    def test_unresolved_row_without_a_reason_fails(self):
        data, index, row = self.first_priced_row()
        row['origination'] = {'method': None, 'probabilities': None}
        row['pick_index'] = None
        row['limitations'] = []
        row['research'] = [{'stage': 'none', 'status': 'checked', 'detail': ''}]
        self.tree.write_origination(data)
        report = self.tree.run()
        self.assertTrue(any('no limitation' in error for error in report['errors']), report['errors'])


class RenderedTests(_Base):
    def test_missing_viewport_fails(self):
        html = self.tree.html()
        self.tree.write_html(html.replace('width=device-width, initial-scale=1', 'width=1024'))
        report = self.tree.run()
        self.assertTrue(any('viewport' in error for error in report['errors']), report['errors'])

    def test_visible_stale_banner_fails(self):
        html = self.tree.html()
        self.tree.write_html(html.replace('id="stale-warning" class="stale-warning" role="status" hidden',
                                          'id="stale-warning" class="stale-warning" role="status"'))
        report = self.tree.run()
        self.assertTrue(any('stale-warning' in error for error in report['errors']), report['errors'])

    def test_missing_picks_link_fails(self):
        html = self.tree.html()
        rewritten = re.sub(r'href="[^"]*origination/#picks"', 'href="#"', html)
        self.assertNotEqual(rewritten, html)
        self.tree.write_html(rewritten)
        report = self.tree.run()
        self.assertTrue(any('complete picks list' in error for error in report['errors']), report['errors'])

    def test_one_glance_row_per_active_fixture(self):
        html = self.tree.html()
        self.tree.write_html(html.replace('class="glance-row"', 'class="glance-row-x"', 1))
        report = self.tree.run()
        self.assertTrue(any('glance rows rendered' in error for error in report['errors']), report['errors'])

    def test_a_changed_percentage_is_caught(self):
        data, index, row = self.first_priced_row()
        value = row['origination']['probabilities'][0]
        rendered = f'{value * 100:.1f}%'
        html = self.tree.html()
        self.assertIn(rendered, html)
        self.tree.write_html(html.replace(rendered, '99.9%'))
        report = self.tree.run()
        self.assertTrue(any('99.9' in error or 'is not rendered' in error for error in report['errors']),
                        report['errors'])


class CoverageTests(_Base):
    def _inventory(self, fixtures):
        record = {'schema_version': 1, 'session': 'test', 'observed_at': '2026-10-26T00:00:00Z',
                  'live_fixtures': fixtures}
        path = self.tree.path / 'inventory.json'
        path.write_text(json.dumps(record))
        return path

    def test_future_fixture_absent_from_the_picks_is_an_error(self):
        path = self._inventory([{'id': '9999999', 'teams': ['A', 'B'],
                                 'competition': 'Test Cup', 'starts_at_utc': '2030-01-01T00:00:00Z'}])
        report = self.tree.run(inventory_path=path)
        self.assertTrue(any('9999999' in error and 'missing from the published picks' in error
                            for error in report['errors']), report['errors'])

    def test_past_fixture_absent_from_the_picks_is_only_a_note(self):
        path = self._inventory([{'id': '9999998', 'teams': ['A', 'B'],
                                 'competition': 'Test Cup', 'starts_at_utc': '2020-01-01T00:00:00Z'}])
        report = self.tree.run(inventory_path=path)
        self.assertEqual(report['errors'], [])
        self.assertTrue(any('9999998' in note for note in report['coverage_notes']))


if __name__ == '__main__':
    unittest.main()
