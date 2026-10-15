"""Leaderboard-plan engine: rules, edge cases and rendering, on synthetic inputs only.

Nothing here reads data/latest.json, data/origination.json or any live snapshot:
production restores a live snapshot over data/ before the regression tests run,
and data-dependent tests are what made that run brittle. Only the committed,
static data/strategy-rules.json is read.
"""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import audit_rows
from scripts import build_strategy as bs

NOW = datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc)
RULES = json.loads(Path('data/strategy-rules.json').read_text())


def match(mid, a, b, probs, method='market', tier='b', starts='2026-10-16T12:00:00Z', locks='2026-10-16T11:54:00Z',
          observed='2026-10-16T08:00:00Z', pick_index=None, research=None):
    return {
        'id': mid, 'teams': [{'id': 't' + mid + 'a', 'name': a}, {'id': 't' + mid + 'b', 'name': b}], 'competition': 'Test Cup', 'tier': tier,
        'starts_at': starts, 'locks_at': locks, 'availability': 'open', 'source_url': 'https://www.hotspawn.com/matches/test-' + mid,
        'lobby_url': 'https://play.hotspawn.com/cs2-pickems#fixture-' + mid, 'featured_method': method, 'pick_index': pick_index,
        'origination': None if probs is None else {'method': method, 'label': 'Test line', 'probabilities': probs, 'observed_at': observed,
                                                     'source': 'Polymarket', 'source_url': 'https://polymarket.com/event/test-' + mid, 'quotes': [], 'limitations': []},
        'research': research or [], 'limitations': [],
    }


def fixture(mid, points=3, shares=(50, 50), n=40, tier_mult=1.5):
    return {'id': mid, 'offered_points': points, 'base_points': 2, 'points_breakdown': {'game_multiplier': 1.25, 'tier_multiplier': tier_mult, 'series_multiplier': 1, 'stage_multiplier': 1, 'tournament_multiplier': 1},
            'participants0_id': 't' + mid + 'a', 'participants1_id': 't' + mid + 'b', 'participants0_picked_percent': shares[0], 'participants1_picked_percent': shares[1], 'total_picks': n}


def inputs(matches, fixtures=None, rules=None, latest=None, twc=None, contract=None):
    return {'rules': rules or copy.deepcopy(RULES),
            'latest': latest if latest is not None else {'coverage_complete': True, 'inventory_observed_at': '2026-10-16T08:30:00Z'},
            'orig': {'matches': matches, 'source_snapshot_at': '2026-10-16T08:30:00Z'},
            'fixtures': {f['id']: f for f in (fixtures or [])}, 'contract': contract, 'twc': twc}


class Primitives(unittest.TestCase):
    def test_valid_pair_rejects_everything_that_is_not_a_real_two_way_probability(self):
        self.assertTrue(bs.valid_pair([0.31, 0.69]))
        for bad in (None, [0.5], [0.5, 0.5, 0.0], [0, 1], [1.0, 0.0], [0.4, 0.4], [float('nan'), 0.5], [True, 0.5], ['0.5', '0.5'], [0.2, 0.9]):
            self.assertFalse(bs.valid_pair(bad), bad)

    def test_class_boundaries(self):
        c = lambda p: bs.classify(p, RULES)
        self.assertEqual([c(0.2499), c(0.25), c(0.3499), c(0.35), c(0.4499), c(0.45), c(0.5)], ['lock', 'lean', 'lean', 'live_dog', 'live_dog', 'coin_flip', 'coin_flip'])

    def test_points_prefer_the_api_then_the_tier_table_then_blank(self):
        self.assertEqual(bs.points_for({'tier': 'c'}, {'offered_points': 7}, RULES), (7, 'Hotspawn fixture API'))
        value, source = bs.points_for({'tier': 'b'}, None, RULES)
        self.assertEqual(value, 3)
        self.assertIn('tier table', source)
        self.assertEqual(bs.points_for({'tier': 's'}, {'offered_points': 0}, RULES)[0], 7)
        self.assertEqual(bs.points_for({'tier': 'x'}, None, RULES), (None, 'Points unverified'))
        self.assertEqual(bs.points_for({'tier': ''}, {'offered_points': True}, RULES)[0], None)

    def test_points_formula_check_detects_a_changed_multiplier(self):
        good = fixture('1', points=7, tier_mult=3)
        self.assertTrue(bs.points_formula_ok(good, RULES))
        self.assertFalse(bs.points_formula_ok(fixture('1', points=7, tier_mult=2), RULES))
        self.assertIsNone(bs.points_formula_ok(None, RULES))
        self.assertIsNone(bs.points_formula_ok({'offered_points': 3}, RULES))

    def test_field_share_joins_on_team_ids_not_on_position(self):
        m = match('1', 'A', 'B', [0.6, 0.4])
        raw = fixture('1', shares=(30, 70), n=20)
        self.assertEqual(bs.field_info(m, raw), {'pct': [30, 70], 'n': 20})
        swapped = copy.deepcopy(m)
        swapped['teams'].reverse()
        self.assertEqual(bs.field_info(swapped, raw), {'pct': [70, 30], 'n': 20})
        raw['participants0_id'] = 'someone-else'
        self.assertIsNone(bs.field_info(m, raw))
        self.assertIsNone(bs.field_info(m, fixture('1', shares=(130, -30))))
        self.assertIsNone(bs.field_info(m, None))


class SwapRules(unittest.TestCase):
    def plan(self, matches, fixtures=None, rules=None, **kw):
        return bs.plan(inputs(matches, fixtures, rules, **kw), NOW)

    def only(self, pl):
        self.assertEqual(len(pl['rows']), 1)
        return pl['rows'][0]

    def test_a_money_backed_live_dog_on_a_big_match_is_the_one_upset_play(self):
        r = self.only(self.plan([match('1', 'Aurora', '9z', [0.69, 0.31], tier='s')], [fixture('1', points=7, shares=(89, 11), n=20, tier_mult=3)]))
        self.assertTrue(r['swap'])
        self.assertEqual((r['fav'], r['dog'], r['default']), (0, 1, 1))
        self.assertAlmostEqual(r['cost'], 7 * (0.69 - 0.31))
        self.assertAlmostEqual(r['upside'], 7 * 0.31)
        self.assertEqual(r['klass'], 'lean')  # 31% is a lean by class; the swap rule is separate and stricter on evidence, looser on probability

    def test_below_thirty_percent_is_never_an_upset_play(self):
        r = self.only(self.plan([match('1', 'A', 'B', [0.71, 0.29], tier='s')], [fixture('1', points=7, tier_mult=3)]))
        self.assertFalse(r['swap'])
        self.assertIn('underdog under 30%', r['blockers'])
        self.assertEqual(r['default'], r['fav'])

    def test_exactly_thirty_percent_qualifies(self):
        r = self.only(self.plan([match('1', 'A', 'B', [0.7, 0.3], tier='s')], [fixture('1', points=7, shares=(80, 20), n=20, tier_mult=3)]))
        self.assertTrue(r['swap'])

    def test_a_model_only_estimate_can_never_be_an_upset_play_even_at_49_percent(self):
        r = self.only(self.plan([match('1', 'A', 'B', [0.51, 0.49], method='model')], [fixture('1', shares=(80, 20), n=40)]))
        self.assertFalse(r['swap'])
        self.assertIn('model-only line', r['blockers'])
        self.assertEqual(r['klass'], 'coin_flip')

    def test_a_stale_line_is_never_an_upset_play(self):
        r = self.only(self.plan([match('1', 'A', 'B', [0.6, 0.4], observed='2026-10-16T00:30:00Z')], [fixture('1', shares=(80, 20), n=40)]))
        self.assertFalse(r['fresh'])
        self.assertFalse(r['swap'])
        self.assertIn('line older than 8 hours', r['blockers'])

    def test_two_point_matches_are_not_worth_the_variance(self):
        r = self.only(self.plan([match('1', 'A', 'B', [0.6, 0.4], tier='c')], [fixture('1', points=2, shares=(80, 20), n=40, tier_mult=1)]))
        self.assertFalse(r['swap'])
        self.assertIn('under 3 points', r['blockers'])

    def test_unknown_points_block_a_swap_instead_of_being_guessed(self):
        r = self.only(self.plan([match('1', 'A', 'B', [0.6, 0.4], tier='')], []))
        self.assertIsNone(r['points'])
        self.assertFalse(r['swap'])
        self.assertIsNone(r['cost'])

    def test_a_crowd_already_on_the_underdog_is_not_contrarian(self):
        r = self.only(self.plan([match('1', 'A', 'B', [0.55, 0.45])], [fixture('1', shares=(35, 65), n=79)]))
        self.assertTrue(r['crowd_on_dog'])
        self.assertFalse(r['swap'])
        self.assertIn('the field is already on this side', r['blockers'])

    def test_a_tiny_sample_does_not_trigger_the_crowd_filter(self):
        r = self.only(self.plan([match('1', 'A', 'B', [0.55, 0.45])], [fixture('1', shares=(0, 100), n=1)]))
        self.assertFalse(r['crowd_on_dog'])
        self.assertIsNone(r['field_dog'])
        self.assertTrue(r['swap'])
        self.assertEqual(r['leverage_weight'], RULES['thresholds']['leverage_weight_when_field_unknown'])

    def test_the_field_filter_can_be_switched_off_in_the_rules(self):
        rules = copy.deepcopy(RULES)
        rules['use_field_for_leverage'] = False
        r = self.only(self.plan([match('1', 'A', 'B', [0.55, 0.45])], [fixture('1', shares=(35, 65), n=79)], rules=rules))
        self.assertFalse(r['crowd_on_dog'])
        self.assertTrue(r['swap'])

    def test_at_most_two_plays_per_utc_day_ranked_by_points_probability_and_leverage(self):
        ms = [match('1', 'A', 'B', [0.60, 0.40], tier='s'), match('2', 'C', 'D', [0.60, 0.40], tier='b'), match('3', 'E', 'F', [0.55, 0.45], tier='b'),
              match('4', 'G', 'H', [0.60, 0.40], tier='b', starts='2026-10-17T12:00:00Z', locks='2026-10-17T11:54:00Z')]
        fs = [fixture('1', points=7, shares=(90, 10), n=30, tier_mult=3), fixture('2', points=3, shares=(70, 30), n=40), fixture('3', points=3, shares=(60, 40), n=40),
              fixture('4', points=3, shares=(70, 30), n=40)]
        pl = self.plan(ms, fs)
        swaps = {r['id'] for r in pl['rows'] if r['swap']}
        # 16 Oct rank values: match 1 = 7*0.40*0.90 = 2.52, match 2 = 3*0.40*0.70 = 0.84, match 3 = 3*0.45*0.60 = 0.81.
        # The cap of two keeps 1 and 2; match 3 is eligible but capped. The 17 Oct match has its own slot.
        self.assertEqual(swaps, {'1', '2', '4'})
        third = next(r for r in pl['rows'] if r['id'] == '3')
        self.assertTrue(third['eligible'])
        self.assertFalse(third['swap'])
        day16 = [r for r in pl['rows'] if r['starts_at'].startswith('2026-10-16') and r['swap']]
        self.assertEqual(len(day16), 2)
        self.assertEqual(pl['summary']['swaps'], 3)

    def test_ranking_prefers_the_play_that_passes_more_of_the_field(self):
        ms = [match('1', 'A', 'B', [0.60, 0.40]), match('2', 'C', 'D', [0.60, 0.40]), match('3', 'E', 'F', [0.60, 0.40])]
        fs = [fixture('1', shares=(60, 40), n=40), fixture('2', shares=(95, 5), n=40), fixture('3', shares=(85, 15), n=40)]
        pl = self.plan(ms, fs)
        self.assertEqual({r['id'] for r in pl['rows'] if r['swap']}, {'2', '3'})

    def test_probabilities_and_the_favorite_never_depend_on_hotspawn_shares(self):
        base = None
        for shares in [(50, 50), (95, 5), (5, 95), (0, 100)]:
            r = self.only(self.plan([match('1', 'A', 'B', [0.62, 0.38])], [fixture('1', shares=shares, n=60)]))
            snapshot = (r['p'], r['fav'], r['dog'], r['klass'])
            base = base or snapshot
            self.assertEqual(snapshot, base)

    def test_an_exact_tie_uses_the_pipeline_pick_not_the_crowd(self):
        r = self.only(self.plan([match('1', 'A', 'B', [0.5, 0.5], pick_index=1)], [fixture('1', shares=(95, 5), n=60)]))
        self.assertEqual(r['fav'], 1)

    def test_locked_fixtures_leave_the_slate_and_are_listed_as_closed(self):
        pl = self.plan([match('1', 'A', 'B', [0.6, 0.4], locks='2026-10-16T08:59:00Z'), match('2', 'C', 'D', [0.6, 0.4])], [])
        self.assertEqual([r['id'] for r in pl['rows']], ['2'])
        self.assertEqual([r['id'] for r in pl['closed']], ['1'])
        self.assertEqual(pl['summary']['closed'], 1)

    def test_a_fixture_without_a_valid_probability_is_unresolved_with_its_trail_not_defaulted(self):
        trail = [{'stage': 'Primary: Polymarket', 'status': 'unresolved', 'detail': 'No unique fixture.', 'source_url': 'https://polymarket.com/esports/cs2'},
                 {'stage': 'Valve research model', 'status': 'resolved', 'detail': 'ok', 'source_url': 'https://github.com/ValveSoftware/x'}]
        pl = self.plan([match('1', 'A', 'B', None, research=trail), match('2', 'C', 'D', [0.7, 0.7])])
        self.assertEqual(pl['rows'], [])
        self.assertEqual({u['id'] for u in pl['unresolved']}, {'1', '2'})
        first = next(u for u in pl['unresolved'] if u['id'] == '1')
        self.assertEqual([s['stage'] for s in first['research']], ['Primary: Polymarket'])  # resolved steps are not "limitations"
        self.assertIn('validation', next(u for u in pl['unresolved'] if u['id'] == '2')['reason'])

    def test_staleness_flags(self):
        ok = self.plan([match('1', 'A', 'B', [0.6, 0.4])])
        self.assertFalse(ok['summary']['stale'])
        incomplete = self.plan([match('1', 'A', 'B', [0.6, 0.4])], latest={'coverage_complete': False, 'inventory_observed_at': '2026-10-16T08:30:00Z'})
        self.assertTrue(incomplete['summary']['stale'])
        old = self.plan([match('1', 'A', 'B', [0.6, 0.4])], latest={'coverage_complete': True, 'inventory_observed_at': '2026-10-15T08:30:00Z'})
        self.assertTrue(old['summary']['stale'])
        missing = self.plan([match('1', 'A', 'B', [0.6, 0.4])], latest={})
        self.assertTrue(missing['summary']['stale'])

    def test_rows_are_in_lock_order(self):
        ms = [match('1', 'A', 'B', [0.6, 0.4], locks='2026-10-16T14:00:00Z'), match('2', 'C', 'D', [0.6, 0.4], locks='2026-10-16T10:00:00Z')]
        self.assertEqual([r['id'] for r in self.plan(ms)['rows']], ['2', '1'])

    def test_featured_estimates_are_used_when_the_originated_list_is_missing(self):
        i = inputs([])
        i['orig'] = None
        i['latest'] = {'coverage_complete': True, 'inventory_observed_at': '2026-10-16T08:30:00Z', 'matches': [
            {**match('1', 'A', 'B', None), 'analysis': {'method': 'market', 'label': 'x', 'probabilities': [0.8, 0.2], 'observed_at': '2026-10-16T08:00:00Z', 'source': 'Polymarket', 'source_url': 'https://polymarket.com/event/x', 'quotes': [], 'limitations': []}}]}
        pl = bs.plan(i, NOW)
        self.assertEqual(len(pl['rows']), 1)
        self.assertIn('origination.json was not available', pl['summary']['basis_note'])


class Rendering(unittest.TestCase):
    def render(self, matches, fixtures=None, **kw):
        i = inputs(matches, fixtures, **kw)
        return bs.page(i, bs.plan(i, NOW))

    def test_every_card_names_the_plan_pick_and_the_upset_ribbon_only_on_swaps(self):
        html = self.render([match('1', 'Aurora', '9z', [0.69, 0.31], tier='s'), match('2', 'Heroic', 'Envy', [0.9, 0.1])],
                           [fixture('1', points=7, shares=(89, 11), n=20, tier_mult=3), fixture('2', shares=(90, 10), n=40)])
        self.assertEqual(html.count('class="ribbon swap"'), 1)
        self.assertIn('Plan pick <strong>9z</strong>', html)
        self.assertIn('Plan pick <strong>Heroic</strong>', html)
        self.assertIn('Most likely winner: Aurora 69.0%', html)

    def test_executive_links_and_the_unresolved_section_exist_even_when_empty(self):
        html = self.render([match('1', 'A', 'B', [0.6, 0.4])])
        self.assertIn('href="#unresolved"', html)
        self.assertIn('id="unresolved"', html)
        self.assertIn('Every active fixture in this snapshot has a probability and a plan pick.', html)
        self.assertIn('href="../origination/#picks"', html)
        self.assertIn('id="slate"', html)

    def test_unresolved_rows_show_the_reason_and_are_marked_unverified(self):
        html = self.render([match('1', 'Alpha', 'Beta', None, research=[{'stage': 'Esportsbook', 'status': 'unavailable', 'detail': '403 from the provider', 'source_url': 'https://gg.bet/x'}])])
        self.assertIn('no pick · unverified', html)
        self.assertIn('403 from the provider', html)
        self.assertIn('Unresolved &amp; limitations (1)', html)

    def test_user_controlled_text_is_escaped(self):
        html = self.render([match('1', '<script>alert(1)</script>', 'B&B', [0.6, 0.4])])
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertIn('B&amp;B', html)

    def test_stale_snapshot_shows_a_visible_warning(self):
        html = self.render([match('1', 'A', 'B', [0.6, 0.4])], latest={'coverage_complete': False, 'inventory_observed_at': '2026-10-16T08:30:00Z'})
        self.assertIn('Not a current snapshot.', html)

    def test_the_rendered_page_passes_the_row_source_audit(self):
        ms = [match('1', 'Aurora', '9z', [0.69, 0.31], tier='s'), match('2', 'C', 'D', None)]
        twc = {'series': [{'day': 1, 'date': '2026-10-14', 'group': 'A', 'round': 'Opening', 'winner': '9z', 'loser': 'Aurora', 'score': '2-0', 'maps_played': 2, 'hltv_url': 'https://www.hltv.org/matches/2399384/x'}],
               'day_three': [{'teams': ['Aurora', '9z'], 'group': 'A', 'round': 'Decider', 'date': '2026-10-16', 'hltv_url': 'https://www.hltv.org/matches/2399412/x', 'on_hotspawn': True, 'hotspawn_fixture_id': '1', 'polymarket_url': 'https://polymarket.com/event/x', 'polymarket_listing_cents': {'Aurora': 69, '9z': 31}}],
               'results_observed_at': '2026-10-15T22:30:00Z'}
        contract = {'note': 'n', 'observations': [{'id': 'H-01', 'claim': 'c', 'status': 'verified', 'how_verified': 'h', 'observed_at': '2026-10-15T08:36:04Z', 'source_url': 'https://play.hotspawn.com/how-it-works'}]}
        i = inputs(ms, [fixture('1', points=7, shares=(89, 11), n=20, tier_mult=3)], twc=twc, contract=contract)
        html = bs.page(i, bs.plan(i, NOW))
        result = audit_rows.audit_html(html, 'strategy/index.html')
        self.assertGreaterEqual(result['rows'], 4)
        self.assertEqual(result['violation'], 0, result['violations'])

    def test_context_notes_appear_only_for_fixtures_with_a_dated_research_entry(self):
        twc = {'series': [], 'day_three': [{'teams': ['Aurora', '9z'], 'group': 'A', 'round': 'Decider', 'format': 'Best of 3 (LAN)', 'hltv_url': 'https://www.hltv.org/matches/2399412/x',
                                            'ranks_hltv_vrs': {'Aurora': {'hltv': 6, 'vrs': 5}, '9z': {'hltv': 17, 'vrs': 11}}}]}
        html = self.render([match('1', 'Aurora', '9z', [0.69, 0.31], tier='s'), match('2', 'C', 'D', [0.6, 0.4])], [fixture('1', points=7, shares=(89, 11), n=20, tier_mult=3)], twc=twc)
        self.assertEqual(html.count('<summary>Situation &amp; sources</summary>'), 1)
        self.assertIn('Ranks (HLTV · Valve VRS): Aurora #6 · #5', html)
        self.assertIn('its absence means nothing was verified', html)

    def test_build_writes_the_page_and_a_public_json_without_raw_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / 'data', Path(tmp) / 'site'
            (src / 'evidence').mkdir(parents=True)
            (src / 'strategy-rules.json').write_text(json.dumps(RULES))
            (src / 'latest.json').write_text(json.dumps({'coverage_complete': True, 'inventory_observed_at': '2026-10-16T08:30:00Z'}))
            (src / 'origination.json').write_text(json.dumps({'source_snapshot_at': '2026-10-16T08:30:00Z', 'matches': [match('1', 'A', 'B', [0.6, 0.4])]}))
            (src / 'evidence/hotspawn-fixtures.json').write_text(json.dumps([fixture('1')]))
            path = bs.build(src, out, now=NOW)
            self.assertTrue(path.exists())
            public = json.loads((out / 'data/strategy.json').read_text())
            self.assertEqual(public['rules_version'], RULES['version'])
            self.assertEqual(len(public['rows']), 1)
            self.assertNotIn('quotes', public['rows'][0])

    def test_missing_optional_inputs_degrade_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / 'data', Path(tmp) / 'site'
            src.mkdir()
            (src / 'strategy-rules.json').write_text(json.dumps(RULES))
            html = bs.build(src, out, now=NOW).read_text()
            self.assertIn('No Day 1–2 research file is present', html)
            self.assertIn('No Hotspawn contract research file is present', html)

    def test_missing_rules_file_is_an_explicit_error_and_the_placeholder_keeps_links_alive(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                bs.load_inputs(Path(tmp))
            text = bs.placeholder(Path(tmp) / 'site', 'rules <missing>').read_text()
            self.assertIn('temporarily unavailable', text)
            self.assertIn('rules &lt;missing&gt;', text)
            self.assertIn('../origination/#picks', text)


class RulesFile(unittest.TestCase):
    def test_thresholds_are_ordered_and_documented(self):
        t = RULES['thresholds']
        self.assertLess(t['lock_underdog_below'], t['lean_underdog_below'])
        self.assertLess(t['lean_underdog_below'], t['live_dog_underdog_below'])
        self.assertLessEqual(t['swap_min_underdog_probability'], t['live_dog_underdog_below'])
        self.assertGreaterEqual(t['swap_min_points'], 3)
        self.assertEqual(set(RULES['classes']), {'lock', 'lean', 'live_dog', 'coin_flip'})
        text = ' '.join(RULES['swap_rule'])
        for needle in ('30%', '8 hours', '3 Hotspawn points', 'crowd', '2 plays'):
            self.assertIn(needle, text)

    def test_hotspawn_popularity_is_declared_unusable_as_a_probability(self):
        never = ' '.join(RULES['probability_inputs']['never_used']).lower()
        self.assertIn("hotspawn '% picked'", never)
        self.assertIn('fan', never)
        self.assertIn('never changes a probability', RULES['field_share_policy'])

    def test_every_scoring_source_is_an_official_host(self):
        for url in RULES['scoring']['source_urls']:
            self.assertTrue(audit_rows.is_official(url), url)


if __name__ == '__main__':
    unittest.main()
