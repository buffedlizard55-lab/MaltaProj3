"""A featured *model* estimate yields to a verified money-backed line; nothing else about featured rows changes.

Why: on 16 Oct the Day-3 decider Aurora vs 9z was priced by the uncalibrated Valve model (72.5/27.5) while Polymarket listed
"Aurora Gaming vs 9z" at 69/31. The featured exact-name join missed the display name, the featured ladder fell to the model,
and the alias-aware money research never ran because the fixture counted as "resolved". All inputs here are synthetic.
"""
import copy
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import build_origination, build_strategy, originate

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
NOW = datetime(2026, 10, 16, 9, 0, tzinfo=UTC)
START = '2026-10-16T14:00:00Z'
VALVE = 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md'


def registry():
    return originate.load_registry(ROOT / 'data' / 'origination' / 'aliases.json')


def model_featured():
    return {'method': 'model', 'label': 'Valve-rating research estimate', 'probabilities': [0.725, 0.275], 'fair_decimal': [1.379, 3.636], 'observed_at': '2026-10-16T08:00:00Z',
            'source': 'Valve official standings', 'source_url': VALVE, 'snapshot_date': '2026-10-05', 'quotes': [], 'limitations': ['Research model, not observed betting odds.'],
            'inputs': [{'name': 'Aurora', 'points': 1800, 'roster': list('abcde'), 'source_url': VALVE, 'snapshot_date': '2026-10-05'},
                       {'name': '9z', 'points': 1571, 'roster': list('fghij'), 'source_url': VALVE, 'snapshot_date': '2026-10-05'}]}


def match(featured='model', competition='Thunderpick World Championship 2026'):
    analysis = {'model': model_featured(), 'market': {**model_featured(), 'method': 'market', 'label': 'Market-implied estimate', 'probabilities': [0.6, 0.4], 'source': 'Polymarket', 'source_url': 'https://polymarket.com/event/x'},
                None: None}[featured]
    return {'id': '1080205', 'teams': [{'id': '32416', 'name': 'Aurora'}, {'id': '11496', 'name': '9z'}], 'competition': competition, 'starts_at': START, 'locks_at': '2026-10-16T13:54:00Z',
            'availability': 'open', 'tier': 's', 'source_url': 'https://www.hotspawn.com/matches/aurora-vs-9z-thunderpick-world-championship-2026-1080205', 'lobby_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1080205',
            'analysis': analysis, 'pick_index': 0 if analysis else None, 'research': [{'stage': 'Primary: Polymarket', 'status': 'unresolved', 'detail': 'No unique exact-name fixture.', 'source_url': 'https://polymarket.com/esports/cs2'}], 'limitations': []}


def poly(names=('Aurora Gaming', '9z'), bid=(0.68, 0.30), ask=(0.70, 0.32), start=START, observed=None):
    return {'family': 'market', 'provider': 'Polymarket', 'names': list(names), 'start': start, 'event_id': '990001', 'market_id': '1',
            'source_url': 'https://polymarket.com/event/cs2-aur1-9z-2026-10-16', 'api_url': 'https://gamma-api.polymarket.com/events/990001',
            'evidence_file': 'data/origination/evidence/live-polymarket-observations.json', 'observed_at': observed or originate.iso(NOW), 'bid': list(bid), 'ask': list(ask)}


def resolve(m, rows):
    return originate.resolve_match(m, rows, [], [], None, registry(), NOW)


class DecisionRule(unittest.TestCase):
    def test_a_verified_alias_aware_market_replaces_the_featured_model_and_says_so(self):
        r = resolve(match(), [poly()])
        self.assertIs(r['upgraded_from_featured_model'], True)
        o = r['origination']
        self.assertEqual(o['method'], 'market')
        self.assertAlmostEqual(o['probabilities'][0], 0.69, places=2)
        self.assertEqual(r['pick_index'], 0)
        self.assertEqual([a['alias'] for a in r['aliases_used']], ['Aurora Gaming'])

    def test_the_money_line_can_change_the_pick_when_it_disagrees_with_the_model(self):
        r = resolve(match(), [poly(bid=(0.38, 0.60), ask=(0.40, 0.62))])
        self.assertIs(r['upgraded_from_featured_model'], True)
        self.assertEqual(r['pick_index'], 1)

    def test_without_a_money_line_the_featured_model_is_kept_exactly(self):
        m = match()
        r = resolve(m, [])
        self.assertNotIn('upgraded_from_featured_model', r)
        self.assertEqual(r['origination']['probabilities'], [0.725, 0.275])
        self.assertEqual(r['origination']['method'], 'model')
        self.assertEqual(r['pick_index'], m['pick_index'])
        self.assertEqual(r['research'], m['research'])

    def test_a_wide_book_is_rejected_by_the_existing_spread_ceiling_and_the_model_stays(self):
        r = resolve(match(), [poly(bid=(0.35, 0.30), ask=(0.70, 0.65))])
        self.assertNotIn('upgraded_from_featured_model', r)
        self.assertEqual(r['origination']['method'], 'model')

    def test_an_alias_never_joins_outside_its_declared_competition(self):
        r = resolve(match(competition='Some Other Cup'), [poly()])
        self.assertNotIn('upgraded_from_featured_model', r)
        self.assertEqual(r['origination']['method'], 'model')

    def test_a_start_time_mismatch_beyond_the_tolerance_keeps_the_model(self):
        r = resolve(match(), [poly(start='2026-10-16T14:20:00Z')])
        self.assertNotIn('upgraded_from_featured_model', r)

    def test_a_stale_observation_is_not_used(self):
        r = resolve(match(), [poly(observed=originate.iso(NOW - timedelta(hours=12)))])
        self.assertNotIn('upgraded_from_featured_model', r)
        self.assertEqual(r['origination']['method'], 'model')

    def test_featured_money_estimates_are_never_touched_even_when_another_line_disagrees(self):
        m = match('market')
        before = copy.deepcopy(m['analysis'])
        r = resolve(m, [poly(bid=(0.38, 0.60), ask=(0.40, 0.62))])
        self.assertNotIn('upgraded_from_featured_model', r)
        self.assertEqual(r['origination']['probabilities'], before['probabilities'])
        self.assertEqual(r['pick_index'], 0)

    def test_a_fixture_with_no_featured_estimate_still_takes_the_normal_path(self):
        r = resolve(match(None), [poly()])
        self.assertNotIn('upgraded_from_featured_model', r)
        self.assertEqual(r['origination']['method'], 'market')


class EndToEnd(unittest.TestCase):
    """run() -> replay validation -> both renderers, on a copy of the committed data with one synthetic live observation."""

    TARGET = '1080203'  # PARIVISION vs BetBoom, model-featured in the committed snapshot; 'BetBoom Team' is a scoped TWC alias

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / 'evidence').mkdir()
        for src in (ROOT / 'data' / 'evidence').glob('*.json'):
            shutil.copy(src, self.tmp / 'evidence' / src.name)
        (self.tmp / 'origination' / 'evidence').mkdir(parents=True)
        shutil.copy(ROOT / 'data/origination/aliases.json', self.tmp / 'origination/aliases.json')
        shutil.copy(ROOT / 'data/strategy-rules.json', self.tmp / 'strategy-rules.json')
        for src in (ROOT / 'data' / 'origination' / 'evidence').glob('*.json'):
            shutil.copy(src, self.tmp / 'origination' / 'evidence' / src.name)
        latest = json.loads((ROOT / 'data/latest.json').read_text())
        real_now = datetime.now(UTC).replace(microsecond=0)
        self.start = real_now + timedelta(days=1)
        target = next(m for m in latest['matches'] if m['id'] == self.TARGET)
        if (target.get('analysis') or {}).get('method') != 'model':
            self.skipTest('committed snapshot no longer has this fixture as a featured model estimate')
        target.update(starts_at=originate.iso(self.start), locks_at=originate.iso(self.start - timedelta(minutes=6)), availability='open')
        (self.tmp / 'latest.json').write_text(json.dumps(latest))
        (self.tmp / 'origination' / 'evidence' / 'live-polymarket-observations.json').write_text(json.dumps({'polymarket_books': [], 'polymarket_events': [{
            'event_id': '990001', 'outcomes': ['PARIVISION', 'BetBoom Team'], 'game_start_time': originate.iso(self.start), 'moneyline_market_id': '1',
            'public_page': 'https://polymarket.com/event/cs2-pari-bb-test', 'source_url': 'https://gamma-api.polymarket.com/events/990001', 'title': 'Counter-Strike: PARIVISION vs BetBoom Team (BO3)',
            'observed_at': originate.iso(real_now), 'book_bid': [0.30, 0.66], 'book_ask': [0.32, 0.68], 'closed': False, 'active': True}]}))
        self.data = originate.run(self.tmp, live=False)

    def row(self):
        return next(m for m in self.data['matches'] if m['id'] == self.TARGET)

    def test_only_the_model_featured_fixture_with_a_verified_line_is_upgraded(self):
        r = self.row()
        self.assertIs(r.get('upgraded_from_featured_model'), True)
        self.assertEqual(r['origination']['method'], 'market')
        self.assertEqual(r['featured_method'], 'model')
        self.assertTrue(r['featured_probabilities'])
        others = [m for m in self.data['matches'] if m['id'] != self.TARGET and m.get('upgraded_from_featured_model')]
        self.assertEqual(others, [], 'no other fixture had a verified line, so no other fixture changes')

    def test_the_replay_validator_accepts_the_upgrade_and_rejects_tampering(self):
        build_origination.validate_origination(self.data, self.tmp)
        unmarked = copy.deepcopy(self.data)
        del next(m for m in unmarked['matches'] if m['id'] == self.TARGET)['upgraded_from_featured_model']
        with self.assertRaises(AssertionError):
            build_origination.validate_origination(unmarked, self.tmp)
        tampered = copy.deepcopy(self.data)
        o = next(m for m in tampered['matches'] if m['id'] == self.TARGET)['origination']
        o['probabilities'] = [0.9, 0.1]
        with self.assertRaises(AssertionError):
            build_origination.validate_origination(tampered, self.tmp)

    def test_a_marked_upgrade_cannot_hide_a_changed_non_model_featured_row(self):
        forged = copy.deepcopy(self.data)
        other = next(m for m in forged['matches'] if m['id'] != self.TARGET and m['featured_method'] in {'market', 'bookmaker'})
        other['origination']['probabilities'] = [0.9, 0.1]
        other['upgraded_from_featured_model'] = True
        with self.assertRaises(AssertionError):
            build_origination.validate_origination(forged, self.tmp)

    def test_the_picks_page_and_the_plan_page_both_say_the_model_was_replaced(self):
        page = build_origination.page(self.data, inventory_complete=True)
        self.assertIn('Upgraded from the featured Valve-model estimate', page)
        self.assertEqual(page.count('Upgraded from the featured Valve-model estimate'), 1)
        inputs = build_strategy.load_inputs(self.tmp)
        plan = build_strategy.plan(inputs, datetime.now(UTC))
        row = next(r for r in plan['rows'] if r['id'] == self.TARGET)
        self.assertTrue(row['upgraded'])
        self.assertTrue(row['money'])
        self.assertIn('money line replaced the model estimate', build_strategy.page(inputs, plan))

    def test_rerunning_is_deterministic(self):
        again = originate.run(self.tmp, live=False)
        key = lambda d: {m['id']: (m['pick_index'], (m['origination'] or {}).get('probabilities'), m.get('upgraded_from_featured_model')) for m in d['matches']}
        self.assertEqual(key(self.data), key(again))


if __name__ == '__main__':
    unittest.main()
