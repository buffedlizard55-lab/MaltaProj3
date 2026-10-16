"""Canonical TWC probabilities, source replay, blank values and mobile handoff."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from scripts import build_twc
from scripts.audit_rows import audit_html
from scripts.domain import timestamp, iso

ROOT = Path(__file__).resolve().parents[1]
NOW = timestamp('2026-10-16T09:00:00Z')


def example_data():
    """Synthetic pricing inputs. Never written to the published data directory."""
    matches, full = [], []
    for mid, names, start, probabilities in [
        ('test-a', ['Aurora', '9z'], '2026-10-16T14:00:00Z', [0.69, 0.31]),
        ('test-b', ['BetBoom', 'Legacy'], '2026-10-16T17:00:00Z', [0.36, 0.64]),
    ]:
        pick = 0 if probabilities[0] > probabilities[1] else 1
        row = {'id': mid, 'teams': [{'name': n} for n in names], 'competition': build_twc.EVENT,
               'starts_at': start, 'locks_at': iso(timestamp(start) - timedelta(minutes=6)), 'availability': 'open',
               'source_url': 'https://play.hotspawn.com/cs2-pickems#fixture-' + mid}
        analysis = {'method': 'consensus', 'probabilities': probabilities,
                    'fair_decimal': [round(1/p, 3) for p in probabilities], 'observed_at': iso(NOW),
                    'label': 'Synthetic test consensus', 'source': 'Polymarket + Kalshi',
                    'source_url': 'https://polymarket.com/event/synthetic', 'quotes': []}
        matches.append(row)
        full.append(dict(row, origination=analysis, pick_index=pick, research=[]))
    return {'generated_at': iso(NOW), 'inventory_observed_at': iso(NOW), 'coverage_complete': True,
            'matches': matches, 'flags': [],
            'complete_picks': {'generated_at': iso(NOW), 'source_snapshot_at': iso(NOW), 'matches': full,
                               'counts': {'active': 2, 'resolved': 2, 'unresolved': 0, 'with_pick': 2}}}


class CanonicalTWC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.research = build_twc.load_research(ROOT / 'data')

    def setUp(self):
        self.data = example_data()
        self.patch = patch('scripts.build_twc.load_research', return_value=copy.deepcopy(self.research))
        self.patch.start(); self.addCleanup(self.patch.stop)

    def derive(self, now=NOW):
        return build_twc.derive(self.data, ROOT / 'data', now)

    def test_both_default_picks_and_numbers_are_exact_canonical_copies(self):
        report = self.derive()
        for result, canonical in zip(report['day3_matches'], self.data['complete_picks']['matches']):
            self.assertEqual(result['analysis'], canonical['origination'])
            self.assertEqual(result['pick_index'], canonical['pick_index'])
            self.assertEqual(result['status'], 'open')
        self.assertEqual([r['pick'] for r in report['day3_matches']], ['Aurora', 'Legacy'])

    def test_price_changes_flow_through_without_manual_twc_edits(self):
        row = self.data['complete_picks']['matches'][0]
        row['origination']['probabilities'] = [0.58, 0.42]
        row['origination']['fair_decimal'] = [round(1/.58, 3), round(1/.42, 3)]
        self.assertEqual(self.derive()['day3_matches'][0]['analysis']['probabilities'], [0.58, 0.42])

    def test_swapped_hotspawn_team_order_does_not_swap_the_meaning_of_a_probability(self):
        a, b = self.data['matches'][0], self.data['complete_picks']['matches'][0]
        a['teams'] = b['teams'] = list(reversed(a['teams']))
        b['origination']['probabilities'] = [0.31, 0.69]
        b['origination']['fair_decimal'].reverse(); b['pick_index'] = 1
        result = self.derive()['day3_matches'][0]
        self.assertEqual(result['teams'], ['9z', 'Aurora']); self.assertEqual(result['pick'], 'Aurora')

    def test_unresolved_is_blank_never_filled_from_historical_research_or_fan_votes(self):
        row = self.data['complete_picks']['matches'][0]
        row['origination'] = None; row['pick_index'] = None
        result = self.derive()['day3_matches'][0]
        self.assertIsNone(result['analysis']); self.assertIsNone(result['pick'])
        self.assertIsNone(result['contrarian_candidate_at_build'])
        self.assertEqual(result['status'], 'unresolved')

    def test_missing_or_duplicate_fixture_is_not_guessed(self):
        self.data['matches'].append(copy.deepcopy(self.data['matches'][0]))
        result = self.derive()['day3_matches'][0]
        self.assertIsNone(result['id']); self.assertIsNone(result['analysis'])
        self.data['matches'] = []
        self.assertTrue(all(r['analysis'] is None for r in self.derive()['day3_matches']))

    def test_different_inventory_observation_is_rejected(self):
        self.data['complete_picks']['source_snapshot_at'] = iso(NOW - timedelta(minutes=1))
        with self.assertRaises(ValueError): self.derive()

    def test_fixture_fact_changes_are_rejected(self):
        self.data['complete_picks']['matches'][0]['locks_at'] = iso(NOW)
        with self.assertRaises(ValueError): self.derive()

    def test_wrong_direction_is_rejected_even_if_probabilities_sum_to_one(self):
        self.data['complete_picks']['matches'][0]['pick_index'] = 1
        with self.assertRaises(ValueError): self.derive()

    def test_a_true_tie_is_not_an_arbitrary_direction_or_underdog(self):
        r = self.data['complete_picks']['matches'][0]
        r['origination'].update(probabilities=[0.5, 0.5], fair_decimal=[2.0, 2.0]); r['pick_index'] = None
        result = self.derive()['day3_matches'][0]
        self.assertIsNone(result['pick']); self.assertIsNone(result['contrarian_candidate_at_build'])

    def test_stale_inventory_or_quote_and_missing_lock_cannot_promote_a_flip(self):
        for what in ['inventory', 'quote', 'lock']:
            self.data = example_data()
            if what == 'inventory': self.data['inventory_observed_at'] = self.data['complete_picks']['source_snapshot_at'] = iso(NOW - timedelta(hours=9))
            elif what == 'quote': self.data['complete_picks']['matches'][0]['origination']['observed_at'] = iso(NOW - timedelta(hours=9))
            else: self.data['matches'][0]['locks_at'] = self.data['complete_picks']['matches'][0]['locks_at'] = None
            result = self.derive()['day3_matches'][0]
            self.assertNotEqual(result['status'], 'open'); self.assertIsNone(result['contrarian_candidate_at_build'])

    def test_lock_or_start_passing_retains_only_a_snapshot_not_a_current_pick(self):
        result = self.derive(timestamp('2026-10-16T14:00:00Z'))['day3_matches'][0]
        self.assertEqual(result['status'], 'closed'); self.assertIsNone(result['contrarian_candidate_at_build'])

    def test_model_only_and_sub_thirty_percent_watch_are_not_promoted(self):
        row = self.data['complete_picks']['matches'][0]
        row['origination']['method'] = 'model'
        self.assertIsNone(self.derive()['day3_matches'][0]['contrarian_candidate_at_build'])
        row['origination'].update(method='market', probabilities=[0.8, 0.2], fair_decimal=[1.25, 5.0])
        self.assertIsNone(self.derive()['day3_matches'][0]['contrarian_candidate_at_build'])

    def test_switch_cost_uses_only_current_external_probabilities(self):
        result = self.derive()['day3_matches'][0]['contrarian_candidate_at_build']
        self.assertEqual(result['team'], '9z'); self.assertEqual(result['probability'], 0.31)
        self.assertAlmostEqual(result['cost_per_base_point'], 0.38)

    def test_result_rows_have_sources_and_no_invented_day_three_result(self):
        report = self.derive()
        self.assertEqual(len(report['day1_results']), 4); self.assertEqual(len(report['day2_results']), 4)
        for row in report['day1_results'] + report['day2_results']:
            self.assertTrue(row['source_url'].startswith('https://www.hltv.org/matches/'))
            self.assertTrue(row['finished']); self.assertIsNotNone(row['score'])
        for row in report['day3_matches']:
            self.assertIsNone(row['hltv']['facts']['score'])

    def test_render_is_source_linked_and_explains_the_unverified_factors(self):
        with patch('scripts.build_twc.datetime', wraps=datetime) as clock:
            clock.now.return_value = NOW
            text = build_twc.render(self.data, '../', ROOT / 'data')
        soup = BeautifulSoup(text, 'html.parser')
        self.assertEqual(len(soup.select('#day-three-picks .twc-card')), 2)
        self.assertEqual(len(soup.select('#day-one-results tbody tr')), 4)
        self.assertEqual(len(soup.select('#day-two-results tbody tr')), 4)
        self.assertEqual(audit_html(text, 'twc-picks/index.html')['violation'], 0)
        self.assertIn('not establish equal rest', text)


class ArtifactIntegration(unittest.TestCase):
    def test_generated_twc_is_not_overwritten_by_the_old_root_copy(self):
        from scripts.build import build
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site'; build(ROOT / 'data', out)
            soup = BeautifulSoup((out / 'twc-picks/index.html').read_text(), 'html.parser')
            self.assertEqual(soup.body.get('data-page'), 'twc')
            self.assertEqual(soup.h1.get_text(), 'TWC Day 4: picks & review')
            self.assertEqual(len(soup.select('#day-two-results tbody tr')), 4)
            report = json.loads((out / 'data/twc-day3-picks.json').read_text())
            self.assertEqual(report['schema_version'], 2)
            canonical = json.loads((ROOT / 'data/latest.json').read_text())
            self.assertEqual(report['source_snapshot_at'], canonical['inventory_observed_at'])
            self.assertNotIn('HLTV simulation', str(soup))
            self.assertNotIn('fan vote: Legacy', str(soup))
            self.assertIn('./twc-picks/', (out / 'index.html').read_text())
