"""Regression tests for the pick-origination layer.

Synthetic fixtures only: no test value is ever published. Every real-data
invariant checked here (alias citations, source links, blank-unverified) must
hold for generated output as well.
"""
import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import build_origination, originate

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def registry():
    return originate.load_registry(ROOT / 'data' / 'origination' / 'aliases.json')


class AliasRegistryTests(unittest.TestCase):
    def test_every_alias_has_https_evidence(self):
        for entry in registry()['aliases']:
            self.assertTrue(entry['alias'] and entry['canonical'])
            self.assertTrue(entry['evidence'], entry['alias'])
            for ev in entry['evidence']:
                self.assertTrue(ev['url'].startswith('https://'), ev)
                self.assertTrue(ev.get('detail'), ev)

    def test_wbt_resolves_to_wrotberry_with_hltv_slug_evidence(self):
        canon, used = originate.resolve_name('WBT', registry())
        self.assertEqual(canon, 'wrotberry')
        self.assertEqual(used[0]['canonical'], 'WROTBERRY')
        urls = [ev['url'] for ev in used[0]['evidence']]
        self.assertIn('https://www.hltv.org/team/13683/wrotberry', urls)

    def test_rounds_resolves_to_roundsgg(self):
        canon, used = originate.resolve_name('ROUNDS', registry())
        self.assertEqual(canon, 'roundsgg')
        self.assertTrue(any('liquipedia' in ev['url'] for ev in used[0]['evidence']))

    def test_unknown_names_pass_through_unmatched(self):
        canon, used = originate.resolve_name('Some Unlisted Squad', registry())
        self.assertEqual(canon, 'some unlisted squad')
        self.assertEqual(used, [])

    def test_must_not_match_exclusion(self):
        # 'Phantom Esports Academy' must NOT alias onto 'Phantom'.
        canon, used = originate.resolve_name('Phantom Esports Academy', registry())
        self.assertEqual(canon, 'phantom esports academy')
        self.assertEqual(used, [])
        canon, used = originate.resolve_name('Phantom Esports', registry())
        self.assertEqual(canon, 'phantom')


class JoinTests(unittest.TestCase):
    def match(self):
        return {'id': 'm1', 'starts_at': '2026-10-15T12:00:00Z',
                'competition': 'Elisa BreakOut Series #2', 'teams': [{'name': 'WROTBERRY'}, {'name': 'ENCE'}]}

    def test_alias_join_matches_with_exact_time(self):
        values, used, status = originate.pair_join(['WBT', 'ENCE'], '2026-10-15T12:00:00Z', self.match(), registry())
        self.assertEqual(status, 'matched')
        self.assertTrue(any(a['alias'] == 'WBT' for a in used))

    def test_time_disagreement_beyond_tolerance_fails(self):
        _, _, status = originate.pair_join(['WBT', 'ENCE'], '2026-10-15T14:00:00Z', self.match(), registry())
        self.assertEqual(status, 'time')

    def test_twenty_minute_provider_clock_skew_is_rejected(self):
        _, _, status = originate.pair_join(['WBT', 'ENCE'], '2026-10-15T12:20:00Z', self.match(), registry())
        self.assertEqual(status, 'time')

    def test_wrong_teams_do_not_join(self):
        _, _, status = originate.pair_join(['WBT', 'BOJONG'], '2026-10-15T12:00:00Z', self.match(), registry())
        self.assertEqual(status, 'names')


class EstimateTests(unittest.TestCase):
    def match(self, a='WROTBERRY', b='ENCE'):
        return {'id': 'm1', 'starts_at': '2026-10-15T12:00:00Z',
                'competition': 'Elisa BreakOut Series #2', 'teams': [{'name': a}, {'name': b}]}

    def test_market_estimate_uses_midpoints_and_flags_thin_books(self):
        now = datetime(2026, 10, 15, 8, tzinfo=UTC)
        row = {'names': ['WBT', 'ENCE'], 'bid': [0.57, 0.42], 'ask': [0.58, 0.43],
               'observed_at': originate.iso(now),
               'source_url': 'https://polymarket.com/event/x', 'event_id': '1', 'evidence_file': 'e.json'}
        quote, detail = originate.market_estimate(row, self.match(), registry(), now)
        self.assertAlmostEqual(quote['probabilities'][0], 0.575, places=4)
        self.assertFalse(quote['thin'])
        row['bid'], row['ask'] = [0.54, 0.17], [0.81, 0.32]
        quote, detail = originate.market_estimate(row, self.match(), registry(), now)
        self.assertIsNone(quote)
        self.assertIn('ceiling', detail)

    def test_market_estimate_rejects_spread_above_ceiling(self):
        now = datetime(2026, 10, 15, 8, tzinfo=UTC)
        row = {'names': ['WBT', 'ENCE'], 'bid': [0.5, 0.1], 'ask': [0.95, 0.5],
               'observed_at': originate.iso(now),
               'source_url': 'https://polymarket.com/event/x', 'event_id': '1', 'evidence_file': 'e.json'}
        quote, detail = originate.market_estimate(row, self.match(), registry(), now)
        self.assertIsNone(quote)

    def test_bookmaker_estimate_removes_margin_and_aligns(self):
        row = {'provider': 'Thunderpick', 'names': ['ENCE', 'WBT'], 'odds': [2.4, 1.5],
               'source_url': 'https://thunderpick.io/esports/counter-strike', 'api_url': 'https://thunderpick.io/api/matches',
               'observed_at': originate.iso(datetime.now(UTC)), 'event_id': '9', 'evidence_file': 't.json'}
        quote, detail = originate.bookmaker_estimate(row, self.match(), registry())
        # Source order ENCE first; aligned to match order WROTBERRY first.
        self.assertGreater(quote['probabilities'][0], quote['probabilities'][1])
        self.assertEqual(quote['odds'], [1.5, 2.4])

    def test_model_estimate_works_with_reverse_alias(self):
        ratings = [
            {'name': 'WBT', 'points': 1201, 'standing': 60, 'roster': ['a', 'b', 'c', 'd', 'e'], 'snapshot_date': '2026-10-05'},
            {'name': 'ENCE', 'points': 1025, 'standing': 105, 'roster': ['f', 'g', 'h', 'i', 'j'], 'snapshot_date': '2026-10-05'},
        ]
        meta = {'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'snapshot_date': '2026-10-05', 'evidence_file': 'v.json'}
        quote, detail = originate.model_estimate(self.match(), ratings, registry(), meta, datetime(2026, 10, 15, tzinfo=UTC))
        self.assertIsNotNone(quote)
        self.assertGreater(quote['probabilities'][0], 0.6)
        self.assertTrue(any(a['alias'] == 'WBT' for a in quote['aliases_used']))

    def test_model_estimate_rejects_incomplete_roster(self):
        ratings = [
            {'name': 'WBT', 'points': 1201, 'standing': 60, 'roster': ['a', 'b'], 'snapshot_date': '2026-10-05'},
            {'name': 'ENCE', 'points': 1025, 'standing': 105, 'roster': ['f', 'g', 'h', 'i', 'j'], 'snapshot_date': '2026-10-05'},
        ]
        meta = {'source_url': 'https://x', 'snapshot_date': '2026-10-05', 'evidence_file': 'v.json'}
        quote, detail = originate.model_estimate(self.match(), ratings, registry(), meta, datetime(2026, 10, 15, tzinfo=UTC))
        self.assertIsNone(quote)
        self.assertIn('roster', detail)

    def test_model_estimate_uses_unique_five_player_row_despite_incomplete_sibling(self):
        ratings = [
            {'name': 'WBT', 'points': 1201, 'standing': 60, 'roster': ['a', 'b', 'c', 'd', 'e'], 'snapshot_date': '2026-10-05'},
            {'name': 'WBT', 'points': 900, 'standing': 90, 'roster': ['a', 'b'], 'snapshot_date': '2026-10-05'},
            {'name': 'ENCE', 'points': 1025, 'standing': 105, 'roster': ['f', 'g', 'h', 'i', 'j'], 'snapshot_date': '2026-10-05'},
        ]
        meta = {'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'snapshot_date': '2026-10-05', 'evidence_file': 'v.json'}
        quote, detail = originate.model_estimate(self.match(), ratings, registry(), meta, datetime(2026, 10, 15, tzinfo=UTC))
        self.assertIsNotNone(quote, detail)
        wbt = [i for i in quote['inputs'] if i['name'] == 'WBT']
        self.assertEqual([i['points'] for i in wbt], [1201])

    def test_model_estimate_rejects_several_complete_five_player_rows(self):
        ratings = [
            {'name': 'WBT', 'points': 1201, 'standing': 60, 'roster': ['a', 'b', 'c', 'd', 'e'], 'snapshot_date': '2026-10-05'},
            {'name': 'WBT', 'points': 900, 'standing': 90, 'roster': ['f', 'g', 'h', 'i', 'j'], 'snapshot_date': '2026-10-05'},
            {'name': 'ENCE', 'points': 1025, 'standing': 105, 'roster': ['l', 'm', 'n', 'o', 'p'], 'snapshot_date': '2026-10-05'},
        ]
        meta = {'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'snapshot_date': '2026-10-05', 'evidence_file': 'v.json'}
        quote, detail = originate.model_estimate(self.match(), ratings, registry(), meta, datetime(2026, 10, 15, tzinfo=UTC))
        self.assertIsNone(quote)
        self.assertIn('multiple Valve rosters', detail)

    def test_checked_in_valve_snapshot_five_player_rule(self):
        """Real 2026-10-05 official snapshot: incomplete siblings resolve, complete duplicates stay blank."""
        import json as _json
        from pathlib import Path
        rows = _json.loads((Path(__file__).resolve().parents[1] / 'data' / 'evidence' / 'valve-ratings.json').read_text())['rows']
        meta = {'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                'snapshot_date': '2026-10-05', 'evidence_file': 'data/evidence/valve-ratings.json'}
        now = datetime(2026, 10, 16, 4, 40, tzinfo=UTC)
        # ex-RUSTEC (one complete + one four-player row) resolves against Bushido Wildcats.
        bw = {'id': '1079167', 'competition': 'NODWIN Clutch Series #13',
              'teams': [{'name': 'Bushido Wildcats', 'id': '1'}, {'name': 'ex-RUSTEC', 'id': '2'}],
              'starts_at': '2026-10-16T11:00:00Z'}
        quote, detail = originate.model_estimate(bw, rows, registry(), meta, now)
        self.assertIsNotNone(quote, detail)
        self.assertEqual([(i['name'], i['points']) for i in quote['inputs']],
                         [('Bushido Wildcats', 982), ('ex-RUSTEC', 1066)])
        self.assertLess(quote['probabilities'][0], quote['probabilities'][1])
        # aimclub and Leo each have two complete five-player rows: identity stays unresolved.
        for fid, a, b in (('1081527', 'aimclub', 'BASEMENT BOYS'), ('1081532', 'ASTRAL', 'Leo')):
            m = {'id': fid, 'competition': 'DraculaN Season 7',
                 'teams': [{'name': a, 'id': '1'}, {'name': b, 'id': '2'}],
                 'starts_at': '2026-10-19T09:00:00Z'}
            q, d = originate.model_estimate(m, rows, registry(), meta, now)
            self.assertIsNone(q, fid)
            self.assertIn('multiple Valve rosters', d)

    def test_incomplete_fixture_remains_blank_instead_of_crashing(self):
        match = {'id': 'unknown', 'starts_at': None, 'teams': [{'name': None}, {'name': 'Opponent'}]}
        result = originate.originate_match(match, [], [], [], None, registry(), datetime.now(UTC))
        self.assertIsNone(result['origination'])
        self.assertIsNone(result['pick_index'])
        self.assertIn('unverified', result['limitations'][0])

    def test_no_default_fifty_fifty(self):
        self.assertIsNone(originate.selection([0.5, 0.5]))
        self.assertEqual(originate.selection([0.50000001, 0.49999999]), 0)


class PublishedOutputTests(unittest.TestCase):
    """Invariants on the generated snapshot that ships to the site."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / 'data' / 'origination.json'
        cls.data = json.loads(path.read_text()) if path.exists() else None

    def test_snapshot_exists_and_resolves_every_active_match(self):
        self.assertIsNotNone(self.data, 'data/origination.json must be generated before tests')
        self.assertEqual(self.data['counts']['active'], len(self.data['matches']))
        self.assertEqual(self.data['counts']['resolved'] + self.data['counts']['unresolved'], self.data['counts']['active'])

    def test_every_row_links_hotspawn_and_its_analysis_source(self):
        for m in self.data['matches']:
            self.assertTrue(m['source_url'].startswith('https://'), m['id'])
            o = m['origination']
            if o is None:
                continue
            self.assertTrue(o['source_url'].startswith('https://'), m['id'])
            for q in o.get('quotes', []):
                self.assertTrue(q.get('source_url', '').startswith('https://'), m['id'])

    def test_hotspawn_and_fan_votes_are_never_inputs(self):
        self.assertFalse(self.data['policy']['hotspawn_votes_used'])
        self.assertFalse(self.data['policy']['fan_votes_used'])

    def test_thin_market_rows_are_labeled(self):
        for m in self.data['matches']:
            for q in (m['origination'] or {}).get('quotes', []):
                if q.get('thin'):
                    self.assertTrue(any('thin' in x.lower() for x in m['limitations']), m['id'])

    def test_replay_is_deterministic_for_picks(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # Replay only reads repo data; copy the consumed inputs.
            (tmp / 'evidence').mkdir()
            for name in ['latest.json', 'origination.json']:
                src = ROOT / 'data' / name
                if src.exists():
                    (tmp / name).write_text(src.read_text())
            for src in (ROOT / 'data' / 'evidence').glob('*.json'):
                (tmp / 'evidence' / src.name).write_text(src.read_text())
            (tmp / 'origination').mkdir()
            (tmp / 'origination' / 'aliases.json').write_text((ROOT / 'data' / 'origination' / 'aliases.json').read_text())
            (tmp / 'origination' / 'evidence').mkdir()
            for src in (ROOT / 'data' / 'origination' / 'evidence').glob('*.json'):
                (tmp / 'origination' / 'evidence' / src.name).write_text(src.read_text())
            result = originate.run(tmp, live=False)
            first = {m['id']: (m['pick_index'], (m['origination'] or {}).get('probabilities')) for m in result['matches']}
            result = originate.run(tmp, live=False)
            second = {m['id']: (m['pick_index'], (m['origination'] or {}).get('probabilities')) for m in result['matches']}
            self.assertEqual(first, second)


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'data' / 'origination.json'
        cls.data = json.loads(path.read_text()) if path.exists() else None

    def test_page_contains_summary_links_unresolved_and_rows(self):
        self.assertIsNotNone(self.data)
        page = build_origination.page(self.data)
        for needle in ['EXECUTIVE SUMMARY', '#picks', '#unresolved', 'Unresolved picks &amp; limitations',
                       'Updated picks — all matches', 'Verified alias registry', 'Source register']:
            self.assertIn(needle, page)
        for m in self.data['matches']:
            self.assertIn('match-' + m['id'], page)

    def test_featured_bookmaker_badge_is_not_mislabeled_model(self):
        data = copy.deepcopy(self.data)
        match = data['matches'][0]
        match['origination']['method'] = 'bookmaker'
        match['origination']['quotes'] = [{'family': 'thunderpick'}]
        rendered = build_origination.pick_row(match)
        self.assertIn('Money-backed line', rendered)
        self.assertNotIn('>Research model<', rendered)

    def test_page_escapes_provider_text(self):
        data = copy.deepcopy(self.data)
        data['matches'][0]['teams'][0]['name'] = '<unsafe>x'
        page = build_origination.page(data)
        self.assertNotIn('<unsafe>', page)
        self.assertIn('&lt;unsafe&gt;', page)


if __name__ == '__main__':
    unittest.main()


class AliasScopeTests(unittest.TestCase):
    """Every alias declares the competitions it may join, and never crosses them."""

    def test_every_alias_declares_its_competition_scope(self):
        for entry in registry()['aliases']:
            self.assertTrue(entry.get('applies_to'), entry['alias'])
            self.assertTrue(all(isinstance(s, str) and s.strip() for s in entry['applies_to']))

    def test_registry_rejects_an_alias_without_a_declared_scope(self):
        broken = copy.deepcopy(registry())
        del broken['aliases'][0]['applies_to']
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'aliases.json'
            path.write_text(json.dumps(broken))
            with self.assertRaises(ValueError):
                originate.load_registry(path)

    def twc(self, a='9z', b='Falcons', starts_at='2026-10-15T11:00:00Z'):
        return {'id': '1080202', 'starts_at': starts_at,
                'competition': 'Thunderpick World Championship 2026',
                'teams': [{'name': a}, {'name': b}]}

    def test_thunderpick_display_names_join_inside_their_own_event(self):
        values, used, status = originate.pair_join(['9z', 'Team Falcons'], '2026-10-15T11:00:00Z', self.twc(), registry())
        self.assertEqual(status, 'matched')
        self.assertTrue(any(a['alias'] == 'Team Falcons' and a['canonical'] == 'Falcons' for a in used))
        values, used, status = originate.pair_join(['PARIVISION', 'BetBoom Team'], '2026-10-15T13:30:00Z',
                                                   self.twc('PARIVISION', 'BetBoom', '2026-10-15T13:30:00Z'), registry())
        self.assertEqual(status, 'matched')
        self.assertTrue(any(a['alias'] == 'BetBoom Team' for a in used))

    def test_an_alias_never_joins_a_different_competition(self):
        other = {'id': 'x', 'starts_at': '2026-10-15T11:00:00Z', 'competition': 'Some Other Event',
                 'teams': [{'name': '9z'}, {'name': 'Falcons'}]}
        _, used, status = originate.pair_join(['9z', 'Team Falcons'], '2026-10-15T11:00:00Z', other, registry())
        self.assertEqual(status, 'names')
        self.assertEqual(used, [])

    def test_elisa_aliases_stay_inside_elisa(self):
        twc = self.twc('WROTBERRY', 'ENCE')
        _, _, status = originate.pair_join(['WBT', 'ENCE'], '2026-10-15T11:00:00Z', twc, registry())
        self.assertEqual(status, 'names')

    def test_resolve_name_honours_the_declared_scope(self):
        canon, used = originate.resolve_name('Team Falcons', registry(), 'Thunderpick World Championship 2026')
        self.assertEqual(canon, 'falcons')
        self.assertTrue(used)
        canon, used = originate.resolve_name('Team Falcons', registry(), 'Elisa BreakOut Series #2')
        self.assertEqual(canon, 'team falcons')
        self.assertEqual(used, [])

    def test_nip_abbreviation_excludes_the_academy_and_women_rosters(self):
        canon, used = originate.resolve_name('NIP Impact', registry(), 'Thunderpick World Championship 2026')
        self.assertEqual(canon, 'nip impact')
        self.assertEqual(used, [])
        canon, used = originate.resolve_name('NIP', registry(), 'Thunderpick World Championship 2026')
        self.assertEqual(canon, 'ninjas in pyjamas')
        self.assertTrue(used)

    def test_reverse_model_lookup_is_also_scope_bound(self):
        ratings = [
            {'name': 'Team Falcons', 'points': 1843, 'standing': 6, 'roster': ['a', 'b', 'c', 'd', 'e'], 'snapshot_date': '2026-10-05'},
            {'name': '9z', 'points': 1543, 'standing': 17, 'roster': ['f', 'g', 'h', 'i', 'j'], 'snapshot_date': '2026-10-05'},
        ]
        meta = {'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                'snapshot_date': '2026-10-05', 'evidence_file': 'v.json'}
        quote, detail = originate.model_estimate(self.twc(), ratings, registry(), meta, datetime(2026, 10, 15, tzinfo=UTC))
        self.assertIsNotNone(quote, detail)
        self.assertTrue(any(a['alias'] == 'Team Falcons' for a in quote['aliases_used']))
        other = dict(self.twc(), competition='Unrelated Cup')
        quote, detail = originate.model_estimate(other, ratings, registry(), meta, datetime(2026, 10, 15, tzinfo=UTC))
        self.assertIsNone(quote)


class ModelFallbackRenderTests(unittest.TestCase):
    """Regression (session c07e1b40): scheduled runs 38742696250/38797535468 and origination audit
    38733458812 crashed with KeyError 'source_url' whenever a featured-unresolved fixture was resolved by
    the Valve-model fallback, because model inputs dropped their per-row source link and snapshot date."""

    def fallback(self):
        match = {'id': 'm1', 'starts_at': '2026-10-15T12:00:00Z', 'competition': 'Elisa BreakOut Series #2',
                 'source_url': 'https://www.hotspawn.com/matches/x', 'teams': [{'id': '1', 'name': 'WROTBERRY'}, {'id': '2', 'name': 'ENCE'}]}
        ratings = [
            {'name': 'WBT', 'points': 1201, 'standing': 60, 'roster': ['a', 'b', 'c', 'd', 'e'], 'snapshot_date': '2026-10-05'},
            {'name': 'ENCE', 'points': 1025, 'standing': 105, 'roster': ['f', 'g', 'h', 'i', 'j'], 'snapshot_date': '2026-10-05'},
        ]
        meta = {'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                'snapshot_date': '2026-10-05', 'evidence_file': 'v.json'}
        return match, originate.originate_match(match, [], [], ratings, meta, registry(), datetime(2026, 10, 15, tzinfo=UTC))

    def test_model_inputs_carry_their_own_source_link_and_snapshot(self):
        _, result = self.fallback()
        self.assertEqual(result['origination']['method'], 'model')
        for row in result['origination']['inputs']:
            self.assertTrue(row['source_url'].startswith('https://github.com/ValveSoftware/'), row)
            self.assertEqual(row['snapshot_date'], '2026-10-05')

    def test_featured_detail_renders_a_model_fallback_without_crashing(self):
        from scripts import build
        match, result = self.fallback()
        canonical = dict(match, analysis=None, pick_index=None, research=[], limitations=[], source_status='scheduled',
                         locks_at='2026-10-15T11:54:00Z', best_of=None, observed_at='2026-10-15T10:00:00Z',
                         source_api='https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures')
        html = build.evidence(canonical, '../', result)
        self.assertIn('Valve rating input', html)
        self.assertIn('standings_global_2026_10_05.md', html)


class ExtraMoneySourceTests(unittest.TestCase):
    """Kalshi (regulated exchange) and Bovada (sportsbook) readers added by session c07e1b40."""

    OBS = '2026-10-15T22:32:24Z'

    def kalshi_event(self, rules_time='4:00 AM EDT', ticker='KXCS2GAME-26OCT160400TLNIP', bids=('0.4500', '0.5300'), asks=('0.4800', '0.5400')):
        rules = 'If {} wins the Stake Pulse Beat III 2026: Liquid vs. NIP CS2 match originally scheduled for Oct 16, 2026 at ' + rules_time + ', then the market resolves to Yes.'
        markets = [{'ticker': ticker + '-' + code, 'yes_sub_title': name, 'status': 'active', 'yes_bid_dollars': bid, 'yes_ask_dollars': ask,
                    'rules_primary': rules.format(name)} for name, code, bid, ask in zip(['Liquid', 'NIP'], ['TL', 'NIP'], bids, asks)]
        return {'event_ticker': ticker, 'series_ticker': 'KXCS2GAME', 'title': 'Liquid vs. NIP', 'mutually_exclusive': True,
                'product_metadata': {'competition': 'CS2'}, 'markets': markets}

    def write(self, tmp, name, payload):
        path = Path(tmp) / name
        path.write_text(json.dumps(payload))
        return Path(tmp)

    def match(self):
        return {'id': '1079586', 'starts_at': '2026-10-16T08:00:00Z', 'competition': 'Stake Pulse Beat III',
                'source_url': 'https://www.hotspawn.com/matches/x', 'teams': [{'id': '367', 'name': 'Ninjas in Pyjamas'}, {'id': '58', 'name': 'Team Liquid'}]}

    def test_kalshi_start_reads_rules_and_requires_ticker_agreement(self):
        self.assertEqual(originate.kalshi_start(self.kalshi_event()), '2026-10-16T08:00:00Z')
        self.assertEqual(originate.kalshi_start(self.kalshi_event('12:00 PM EST', 'KXCS2GAME-26OCT161200TLNIP')), '2026-10-16T17:00:00Z')
        self.assertIsNone(originate.kalshi_start(self.kalshi_event('5:00 AM EDT')), 'ticker 0400 disagrees with rules 05:00')

    def test_kalshi_rows_skip_started_events_and_keep_paired_books(self):
        with TemporaryDirectory() as tmp:
            started = self.kalshi_event()
            payload = {'pages': [{'observed_at': self.OBS, 'response': {'events': [self.kalshi_event()]}},
                                 {'observed_at': '2026-10-16T09:00:00Z', 'response': {'events': [started]}}]}
            rows = originate.kalshi_rows(self.write(tmp, 'live-kalshi-events.json', payload))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['provider'], 'Kalshi')
        self.assertEqual(rows[0]['bid'], [0.45, 0.53])
        self.assertTrue(rows[0]['source_url'].startswith('https://kalshi.com/markets/kxcs2game/'))

    def test_wide_kalshi_book_is_rejected_with_the_observed_quotes_in_the_reason(self):
        with TemporaryDirectory() as tmp:
            event = self.kalshi_event(bids=('0.1900', '0.3400'), asks=('0.6400', '0.7600'))
            rows = originate.kalshi_rows(self.write(tmp, 'live-kalshi-events.json', {'pages': [{'observed_at': self.OBS, 'response': {'events': [event]}}]}))
        quote, detail = originate.market_estimate(rows[0], self.match(), registry(), originate.timestamp(self.OBS))
        self.assertIsNone(quote)
        self.assertIn('0.19/0.64', detail)
        self.assertIn('not used as a pick input', detail)

    def bovada_payload(self, live=False, status='O'):
        outcomes = [{'description': 'Ninjas in Pyjamas', 'status': status, 'price': {'decimal': '1.769230'}},
                    {'description': 'Team Liquid', 'status': 'O', 'price': {'decimal': '2.00'}}]
        market = {'id': '1', 'key': '2W-12', 'description': 'Moneyline', 'status': 'O', 'period': {'main': True, 'live': False}, 'outcomes': outcomes}
        event = {'id': '32266578', 'type': 'GAMEEVENT', 'live': live, 'startTime': 1792137600000, 'link': '/esports/counter-strike-2/pulse-beat-iii/x',
                 'competitors': [{'name': 'Ninjas in Pyjamas'}, {'name': 'Team Liquid'}], 'displayGroups': [{'markets': [market]}]}
        return {'observed_at': self.OBS, 'response': [{'path': [{'description': 'Pulse Beat III'}], 'events': [event]}]}

    def test_bovada_rows_accept_prematch_moneyline_only(self):
        with TemporaryDirectory() as tmp:
            rows = originate.bovada_rows(self.write(tmp, 'live-bovada-cs2.json', self.bovada_payload()))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['start'], '2026-10-16T08:00:00Z')
            self.assertEqual(rows[0]['odds'], [1.76923, 2.0])
            self.assertEqual(originate.bovada_rows(self.write(tmp, 'live-bovada-cs2.json', self.bovada_payload(live=True))), [])
            self.assertEqual(originate.bovada_rows(self.write(tmp, 'live-bovada-cs2.json', self.bovada_payload(status='S'))), [])

    def test_consensus_takes_one_vote_per_provider_and_aliases_stay_scoped(self):
        from datetime import timedelta
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        local = (now + timedelta(days=3)).astimezone(timezone(timedelta(hours=-4))).replace(hour=4, minute=0)
        start = local.astimezone(UTC)
        ticker = 'KXCS2GAME-' + local.strftime('%y%b%d').upper() + '0400TLNIP'
        event = self.kalshi_event(ticker=ticker)
        for m in event['markets']:
            m['rules_primary'] = m['rules_primary'].replace('Oct 16, 2026', local.strftime('%b ') + str(local.day) + local.strftime(', %Y'))
        payload = self.bovada_payload()
        payload['response'][0]['events'][0]['startTime'] = int(start.timestamp() * 1000)
        payload['observed_at'] = originate.iso(now)
        with TemporaryDirectory() as tmp:
            k = originate.kalshi_rows(self.write(tmp, 'live-kalshi-events.json', {'pages': [{'observed_at': originate.iso(now), 'response': {'events': [event]}}]}))
            b = originate.bovada_rows(self.write(tmp, 'live-bovada-cs2.json', payload))
        self.assertEqual(len(k), 1)
        self.assertEqual(len(b), 1)
        match = dict(self.match(), starts_at=originate.iso(start))
        result = originate.originate_match(match, k, b, [], None, registry(), now)
        self.assertEqual(result['origination']['method'], 'consensus')
        self.assertEqual({q['provider'] for q in result['origination']['quotes']}, {'Kalshi', 'Bovada'})
        other = dict(match, competition='Some Other Cup')
        self.assertEqual({q['provider'] for q in originate.originate_match(other, k, b, [], None, registry(), now)['origination']['quotes']}, {'Bovada'},
                         'Liquid/NIP aliases must not join outside Stake Pulse Beat III; Bovada uses exact names')


class ReviewNoteTests(unittest.TestCase):
    def test_alias_review_notes_are_published_on_the_registry_section(self):
        data = {'alias_registry': registry()}
        html = build_origination.section_aliases(data)
        flagged = [a for a in data['alias_registry']['aliases'] if a.get('review_note')]
        self.assertTrue(flagged, 'session c07e1b40 flagged WBT and ROUNDS evidence for review')
        self.assertEqual(html.count('Flagged for review:'), len(flagged))


class PublicContractTests(unittest.TestCase):
    """Mirror scripts/verify_live.py: exactly one .pick-card per active fixture, even with unresolved cards."""

    def test_unresolved_cards_do_not_add_pick_cards(self):
        from bs4 import BeautifulSoup
        data = json.loads((ROOT / 'data' / 'origination.json').read_text())
        data = copy.deepcopy(data)
        victim = data['matches'][0]
        victim['origination'], victim['pick_index'] = None, None
        victim['research'] = [{'stage': 'Exchange market (Kalshi CS2 match winner)', 'status': 'unresolved',
                               'source_url': 'https://kalshi.com/markets/kxcs2game', 'detail': 'spread too wide'}]
        page = BeautifulSoup(build_origination.page(data), 'html.parser')
        self.assertEqual({el.get('id') for el in page.select('.pick-card')}, {'match-' + m['id'] for m in data['matches']})
        self.assertEqual(len(page.select('.unresolved-card')), 1)
        self.assertIsNotNone(page.find(id='unresolved-' + victim['id']))


class SourceLinkDedupeTests(unittest.TestCase):
    def test_each_source_url_is_linked_once_per_card(self):
        from bs4 import BeautifulSoup
        data = json.loads((ROOT / 'data' / 'origination.json').read_text())
        for m in data['matches']:
            if not m['origination']:
                continue
            card = BeautifulSoup(build_origination.pick_row(m), 'html.parser')
            hrefs = [a['href'] for a in card.select('.row-srcs a')]
            self.assertEqual(len(hrefs), len(set(hrefs)), m['id'])
            self.assertTrue(any('hotspawn' in h for h in hrefs), m['id'])
            self.assertGreaterEqual(len(hrefs), 2, m['id'])


class RowSourceAuditTests(unittest.TestCase):
    def test_kalshi_and_bovada_source_rows_pass_the_official_source_audit(self):
        from scripts import audit_rows
        data = copy.deepcopy(json.loads((ROOT / 'data' / 'origination.json').read_text()))
        data['sources'] = [
            {'name': 'Kalshi CS2 match markets', 'url': originate.KALSHI_PAGE.rstrip('/'), 'api_url': originate.KALSHI_EVENTS, 'role': 'exchange'},
            {'name': 'Bovada esportsbook', 'url': originate.BOVADA_SITE, 'api_url': originate.BOVADA_API, 'role': 'book'},
        ]
        result = audit_rows.audit_html(build_origination.page(data), 'origination/index.html')
        self.assertEqual(result['violations'], [], result['violations'])
