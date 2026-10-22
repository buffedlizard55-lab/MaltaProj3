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

    def test_a_featured_bookmaker_tie_upgrades_to_a_directional_aliased_money_line(self):
        m = match(None)
        m['analysis'] = {**model_featured(), 'method': 'bookmaker', 'label': 'No-vig bookmaker estimate',
                         'probabilities': [0.5, 0.5], 'source': 'Thunderpick',
                         'source_url': 'https://thunderpick.io/esports/counter-strike'}
        m['pick_index'] = None
        r = resolve(m, [poly(bid=(0.52, 0.47), ask=(0.53, 0.48))])
        self.assertIs(r['upgraded_from_featured_model'], True)
        self.assertEqual(r['origination']['method'], 'market')
        self.assertEqual(r['origination']['probabilities'], [0.525, 0.475])
        self.assertEqual(r['pick_index'], 0)
        self.assertEqual([a['alias'] for a in r['aliases_used']], ['Aurora Gaming'])

    def test_a_featured_bookmaker_tie_is_kept_when_no_directional_money_line_exists(self):
        m = match(None)
        m['analysis'] = {**model_featured(), 'method': 'bookmaker', 'label': 'No-vig bookmaker estimate',
                         'probabilities': [0.5, 0.5], 'source': 'Thunderpick',
                         'source_url': 'https://thunderpick.io/esports/counter-strike'}
        m['pick_index'] = None
        r = resolve(m, [poly(bid=(0.49, 0.49), ask=(0.51, 0.51))])
        self.assertNotIn('upgraded_from_featured_model', r)
        self.assertEqual(r['origination']['method'], 'bookmaker')
        self.assertEqual(r['origination']['probabilities'], [0.5, 0.5])
        self.assertIsNone(r['pick_index'])


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
        target = next((m for m in latest['matches'] if m['id'] == self.TARGET), None)
        if target is None:
            self.skipTest('the committed snapshot no longer lists the featured-model fixture this end-to-end test replays')
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

    def test_a_featured_bookmaker_tie_upgrades_end_to_end_and_passes_replay_validation(self):
        latest = json.loads((self.tmp / 'latest.json').read_text())
        target = next(m for m in latest['matches'] if m['id'] == self.TARGET)
        target['analysis'] = {
            'method': 'bookmaker', 'label': 'No-vig bookmaker estimate',
            'probabilities': [0.5, 0.5], 'fair_decimal': [2.0, 2.0],
            'observed_at': originate.iso(datetime.now(UTC)),
            'source': 'Thunderpick', 'source_url': 'https://thunderpick.io/esports/counter-strike',
            'quotes': [], 'limitations': [],
        }
        target['pick_index'] = None
        (self.tmp / 'latest.json').write_text(json.dumps(latest))
        data = originate.run(self.tmp, live=False)
        build_origination.validate_origination(data, self.tmp)
        r = next(m for m in data['matches'] if m['id'] == self.TARGET)
        self.assertIs(r.get('upgraded_from_featured_model'), True)
        self.assertEqual(r['featured_method'], 'bookmaker')
        self.assertIsNone(r['featured_pick_index'])
        self.assertEqual(r['pick_index'], 1)
        page = build_origination.page(data, inventory_complete=True)
        self.assertIn('Upgraded from the featured bookmaker tie (50.0% / 50.0%)', page)


class LiveModelResearch(unittest.TestCase):
    """Exercise the collector, not just the resolver; all responses are synthetic."""

    def collect(self, featured='model', *, zero_size=False, duplicate=False, prop=False):
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        market = {'id': '1', 'sportsMarketType': 'moneyline',
                  'question': 'Counter-Strike: Aurora Gaming vs 9z (BO3)',
                  'active': True, 'closed': False, 'acceptingOrders': True,
                  'outcomes': ['Aurora Gaming', '9z'], 'gameStartTime': START,
                  'clobTokenIds': ['10', '20'], 'conditionId': 'condition'}
        if prop:
            market['question'] = 'Counter-Strike: Aurora Gaming vs 9z (BO3) Map 1'
        event = {'id': '990001', 'slug': 'cs2-aur1-9z-2026-10-16', 'active': True,
                 'closed': False, 'live': False, 'markets': [market] + ([dict(market, id='2')] if duplicate else [])}
        seen = []

        def get_json(client, url, label, **kwargs):
            seen.append(label)
            if label == 'live-thunderpick-matches':
                data = {'data': {'upcoming': []}}
            elif label.startswith('live-polymarket-event-'):
                data = event
            elif label.startswith('live-polymarket-book-'):
                token = url.split('=')[-1]
                p = 0.69 if token == '10' else 0.31
                data = {'asset_id': token, 'market': 'condition', 'timestamp': str(int(NOW.timestamp() * 1000)),
                        'bids': [{'price': p - 0.01, 'size': '0' if zero_size else '5'}],
                        'asks': [{'price': p + 0.01, 'size': '5'}]}
            elif label.startswith('live-kalshi-events-'):
                data = {'events': [], 'cursor': ''}
            else:
                data = []
            entry = {'id': label, 'url': url, 'observed_at': originate.iso(NOW), 'status': 'ok'}
            client.requests.append(entry)
            return data, entry

        with TemporaryDirectory() as tmp, patch.object(originate.Collector, 'get_json', new=get_json), \
                patch.object(originate.Collector, 'fetch_html', return_value=('synthetic', {})), \
                patch('scripts.sources.polymarket_games', return_value=[{'id': '990001', 'homeName': 'Aurora Gaming', 'awayName': '9z', 'startTime': START}]), \
                patch('scripts.originate.datetime', wraps=datetime) as clock:
            clock.now.return_value = NOW
            originate.live_collect(Path(tmp), [match(featured)], registry())
            saved = json.loads((Path(tmp) / 'live-polymarket-observations.json').read_text())
        return seen, saved

    def test_model_only_rows_get_fresh_alias_aware_market_books(self):
        seen, saved = self.collect()
        self.assertIn('live-polymarket-event-990001', seen)
        self.assertIn('live-polymarket-book-990001-1', seen)
        self.assertEqual(len(saved['polymarket_events']), 1)
        ev = saved['polymarket_events'][0]
        for actual, expected in zip(ev['book_bid'], [0.68, 0.3]):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(ev['observed_at'], originate.iso(NOW))

    def test_featured_money_line_does_not_get_researched_or_overwritten(self):
        seen, saved = self.collect('market')
        self.assertNotIn('live-polymarket-event-990001', seen)
        self.assertEqual(saved['polymarket_events'], [])

    def test_previously_unresolved_rows_still_get_researched(self):
        seen, _ = self.collect(None)
        self.assertIn('live-polymarket-book-990001-1', seen)

    def test_zero_size_levels_cannot_become_an_executable_quote(self):
        _, saved = self.collect(zero_size=True)
        self.assertNotIn('book_bid', saved['polymarket_events'][0])

    def test_duplicate_full_series_markets_stay_ambiguous(self):
        seen, saved = self.collect(duplicate=True)
        self.assertFalse(any('polymarket-book' in x for x in seen))
        self.assertEqual(saved['polymarket_events'], [])

    def test_a_map_moneyline_is_not_a_series_moneyline(self):
        seen, saved = self.collect(prop=True)
        self.assertFalse(any('polymarket-book' in x for x in seen))
        self.assertEqual(saved['polymarket_events'], [])


class OriginalBookReplay(unittest.TestCase):
    TARGET = EndToEnd.TARGET
    row = EndToEnd.row

    def setUp(self):
        EndToEnd.setUp(self)
        self.folder = self.tmp / 'origination/evidence'
        path = self.folder / 'live-polymarket-observations.json'
        observations = json.loads(path.read_text())
        observations['schema_version'] = 2
        ev = observations['polymarket_events'][0]
        ev['clob_token_ids'] = ['a', 'b']
        path.write_text(json.dumps(observations))
        market = {'id': '1', 'outcomes': ev['outcomes'], 'clobTokenIds': ['a', 'b'], 'conditionId': 'condition',
                  'gameStartTime': ev['game_start_time'], 'sportsMarketType': 'moneyline',
                  'question': ev['title'], 'active': True, 'closed': False, 'acceptingOrders': True}
        self.event = {'id': '990001', 'slug': 'cs2-pari-bb-test', 'active': True, 'closed': False, 'live': False, 'markets': [market]}
        (self.folder / 'live-polymarket-event-990001.json').write_text(json.dumps(self.event))
        for i, token in enumerate(['a', 'b']):
            book = {'asset_id': token, 'market': 'condition', 'timestamp': str(int(timestamp_for_test(ev['observed_at']).timestamp() * 1000)),
                    'bids': [{'price': ev['book_bid'][i], 'size': '5'}],
                    'asks': [{'price': ev['book_ask'][i], 'size': '6'}]}
            (self.folder / f'live-polymarket-book-990001-{i}.json').write_text(json.dumps(book))
        (self.folder / 'live-collection-manifest.json').write_text(json.dumps([{'id': 'live-polymarket-event-990001', 'status': 'ok', 'observed_at': ev['observed_at']}]))

    def validate(self):
        build_origination.validate_origination(self.data, self.tmp)

    def mutate_book(self, change):
        path = self.folder / 'live-polymarket-book-990001-0.json'
        b = json.loads(path.read_text()); change(b); path.write_text(json.dumps(b))

    def test_full_original_event_and_books_reproduce_the_summary(self):
        self.validate()

    def test_summary_cannot_hide_a_changed_original_bid(self):
        self.mutate_book(lambda b: b['bids'][0].update(price=0.29))
        with self.assertRaises(AssertionError): self.validate()

    def test_zero_size_original_levels_cannot_back_a_pick(self):
        self.mutate_book(lambda b: b['bids'][0].update(size='0'))
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_token_or_condition_is_not_replayable(self):
        self.mutate_book(lambda b: b.update(market='different-condition'))
        with self.assertRaises(ValueError): self.validate()

    def test_duplicate_or_map_original_markets_are_not_replayable(self):
        self.event['markets'].append(copy.deepcopy(self.event['markets'][0]))
        (self.folder / 'live-polymarket-event-990001.json').write_text(json.dumps(self.event))
        with self.assertRaises(AssertionError): self.validate()

    def test_direction_and_fair_line_are_replayed_not_just_probability_sum(self):
        row = self.row()
        row['pick_index'] = 1 - row['pick_index']
        with self.assertRaises(AssertionError): self.validate()
        row['pick_index'] = 1 - row['pick_index']
        row['origination']['fair_decimal'][0] = 1.001
        with self.assertRaises(AssertionError): self.validate()


def timestamp_for_test(value):
    from scripts.domain import timestamp
    return timestamp(value)


if __name__ == "__main__":
    unittest.main()


class DisplayAndCSVParity(unittest.TestCase):
    """Money-backed upgrades must not disagree across HTML, CSV and full picks."""
    def render(self, m, result):
        import csv
        import io
        from bs4 import BeautifulSoup
        from scripts import build
        m.update(observed_at=originate.iso(NOW), source_status='scheduled', best_of=None, source_api='https://play.hotspawn.com/cs2-pickems')
        if m.get('analysis', {}).get('method') == 'market':
            m['analysis'].update(event_id='synthetic', source_api='https://gamma-api.polymarket.com/events/synthetic')
        full = {m['id']: result}
        html = BeautifulSoup(build.matches_table([m], '../', fallbacks=full), 'html.parser')
        row = next(csv.DictReader(io.StringIO(build.picks_csv({'matches': [m], 'fallbacks': full}))))
        return html, row

    def test_money_line_replaces_model_in_both_html_and_csv_including_direction(self):
        m = match()
        result = resolve(m, [poly(bid=(0.38, 0.60), ask=(0.40, 0.62))])
        html, csv = self.render(m, result)
        self.assertEqual([n.get_text() for n in html.select('.prob-line > strong')], ['39.0%', '61.0%'])
        self.assertEqual(html.select_one('[data-pick-choice] strong')['data-original'], '9z')
        self.assertEqual(html.select_one('.match-row')['data-method'], 'market')
        self.assertEqual(csv['suggested_team'], '9z')
        self.assertEqual([float(csv[k]) for k in ['team_a_probability_calculated', 'team_b_probability_calculated']], result['origination']['probabilities'])
        self.assertEqual(csv['analysis_source'], result['origination']['source_url'])
        self.assertIn('money line replaced the featured model', html.select_one('[data-pick-caption]')['data-original'])

    def test_no_upgrade_flag_cannot_silently_replace_a_featured_estimate(self):
        m = match()
        result = resolve(m, [poly(bid=(0.38, 0.60), ask=(0.40, 0.62))])
        result.pop('upgraded_from_featured_model')
        html, csv = self.render(m, result)
        self.assertEqual([n.get_text() for n in html.select('.prob-line > strong')], ['72.5%', '27.5%'])
        self.assertEqual(csv['suggested_team'], 'Aurora')
        self.assertEqual(csv['basis'], 'model')

    def test_featured_money_line_is_preserved_even_if_a_competing_fallback_disagrees(self):
        m = match('market')
        result = resolve(match(), [poly(bid=(0.38, 0.60), ask=(0.40, 0.62))])
        html, csv = self.render(m, result)
        self.assertEqual([n.get_text() for n in html.select('.prob-line > strong')], ['60.0%', '40.0%'])
        self.assertEqual(csv['suggested_team'], 'Aurora')
        self.assertEqual(float(csv['team_a_probability_calculated']), 0.6)
