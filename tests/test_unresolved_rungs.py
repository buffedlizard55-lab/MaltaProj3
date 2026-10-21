"""Tests for session c03ef201's last-resort pick-resolution rungs.

Contract under test — the published ladder gains exactly three new rungs, and
each one is fail-closed and never overrides anything above it:

1. Pinnacle guest-board series moneylines (first-party money vote; period 0
   only; "Yes/No" and score-grid specials rejected by participant text).
2. HLTV world-ranking research model (uncalibrated; same evidence class as the
   Valve rung; only when the Valve rung has no row).
3. Wide-book indicative guidance (midpoint of the narrowest observed book that
   every published ceiling rejected; only when every other rung failed; never
   in MONEY_METHODS; an even midpoint has no directional pick).
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import hltv_ranking, pinnacle_lines
from scripts.domain import iso
from scripts.originate import (MONEY_METHODS, load_registry, pair_join, pinnacle_rows,
                               resolve_match, selection, wide_book_quote)

UTC = timezone.utc
NOW = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)


def fixture(name_a='Fire Flux', name_b='ex-6666', start='2026-10-19T17:00:00Z'):
    return {'id': '1079181', 'teams': [{'id': '1', 'name': name_a}, {'id': '2', 'name': name_b}],
            'competition': 'NODWIN Clutch Series #13', 'starts_at': start,
            'locks_at': '2026-10-19T16:54:00Z', 'availability': 'open',
            'source_url': 'https://www.hotspawn.com/matches/a-vs-b-1079181',
            'research': [], 'limitations': []}


def wide_market_row(spread_pair=((0.20, 0.83), (0.17, 0.80))):
    (b0, a0), (b1, a1) = spread_pair
    return {'family': 'market', 'provider': 'Polymarket', 'names': ['Fire Flux', 'ex-6666'],
            'start': '2026-10-19T17:00:00Z', 'bid': [b0, b1], 'ask': [a0, a1],
            'observed_at': '2026-10-19T11:00:00Z',
            'source_url': 'https://polymarket.com/event/x', 'event_id': '1',
            'market_id': 'm1', 'evidence_file': 'data/origination/evidence/live-polymarket-observations.json'}


class PinnacleSpecialsTest(unittest.TestCase):
    def test_yes_no_special_is_not_a_series_moneyline(self):
        matchup = {'id': 5, 'participants': [{'id': 6, 'name': 'Yes'}, {'id': 7, 'name': 'No'}],
                   'startTime': '2026-10-19T17:00:00Z'}
        markets = [{'matchupId': 5, 'type': 'moneyline', 'period': 0,
                    'prices': [{'participantId': 6, 'price': -120},
                               {'participantId': 7, 'price': 100}]}]
        self.assertIsNone(pinnacle_lines.series_moneyline(matchup, markets))

    def test_team_pair_resolves_on_participant_ids(self):
        matchup = {'id': 5, 'participants': [{'id': 6, 'name': 'Fire Flux'}, {'id': 7, 'name': 'ex-6666'}],
                   'startTime': '2026-10-19T17:00:00Z'}
        markets = [{'matchupId': 5, 'type': 'moneyline', 'period': 0,
                    'prices': [{'participantId': 7, 'price': 151},
                               {'participantId': 6, 'price': -186}]}]
        found = pinnacle_lines.series_moneyline(matchup, markets)
        self.assertIsNotNone(found)
        self.assertEqual(found['participants'], ['ex-6666', 'Fire Flux'])
        self.assertAlmostEqual(found['decimal'][0], 2.51, places=2)

    def test_american_conversion(self):
        self.assertAlmostEqual(pinnacle_lines.american_to_decimal(100), 2.0)
        self.assertAlmostEqual(pinnacle_lines.american_to_decimal(-200), 1.5)
        with self.assertRaises(ValueError):
            pinnacle_lines.american_to_decimal(0)


class PinnacleRowsTest(unittest.TestCase):
    def _write(self, tmp, payload):
        (Path(tmp) / 'live-pinnacle-cs.json').write_text(json.dumps(payload))

    def test_period_zero_series_row_is_loaded(self):
        with TemporaryDirectory() as tmp:
            self._write(tmp, {
                'observed_at': '2026-10-19T11:00:00Z',
                'matchups': [{'id': 5, 'isLive': False, 'bestOfX': 3, 'startTime': '2026-10-19T17:00:00Z',
                              'league': {'id': 278848, 'name': 'CS2 - NODWIN Clutch Series Qualifier'},
                              'participants': [{'name': 'Fire Flux'}, {'name': 'ex-6666'}]}],
                'straight': [{'league_id': 278848, 'observed_at': '2026-10-19T11:00:01Z', 'markets': [
                    {'matchupId': 5, 'type': 'moneyline', 'period': 0,
                     'prices': [{'price': -186}, {'price': 151}]},
                    {'matchupId': 5, 'type': 'moneyline', 'period': 1,
                     'prices': [{'price': -300}, {'price': 250}]}]}]})
            rows = pinnacle_rows(Path(tmp))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['provider'], 'Pinnacle')
        self.assertEqual(row['observed_at'], '2026-10-19T11:00:01Z')
        self.assertEqual(row['market_id'], 'series-moneyline-period-0')
        # Ordering fallback: prices carry no keys at all and the matchup has
        # no participant ids, so price order follows the participant order.
        self.assertEqual(row['names'], ['Fire Flux', 'ex-6666'])

    def test_id_keyed_prices_are_mapped_by_participant_id(self):
        with TemporaryDirectory() as tmp:
            self._write(tmp, {
                'observed_at': '2026-10-19T11:00:00Z',
                'matchups': [{'id': 5, 'isLive': False, 'startTime': '2026-10-19T17:00:00Z',
                              'league': {'id': 278848, 'name': 'CS2 - NODWIN Clutch Series Qualifier'},
                              'participants': [{'id': 900, 'name': 'Fire Flux'}, {'id': 901, 'name': 'ex-6666'}]}],
                'straight': [{'league_id': 278848, 'observed_at': '2026-10-19T11:00:01Z', 'markets': [
                    {'matchupId': 5, 'type': 'moneyline', 'period': 0,
                     'prices': [{'participantId': 901, 'price': 151}, {'participantId': 900, 'price': -186}]}]}]})
            rows = pinnacle_rows(Path(tmp))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['odds'], [1.5376, 2.51])  # decimal aligned to Fire Flux, ex-6666

    def test_per_map_only_matchup_is_not_a_series(self):
        with TemporaryDirectory() as tmp:
            self._write(tmp, {
                'observed_at': '2026-10-19T11:00:00Z',
                'matchups': [{'id': 5, 'isLive': False, 'startTime': '2026-10-19T17:00:00Z',
                              'league': {'id': 285202, 'name': 'CS2 - STK Ranked'},
                              'participants': [{'name': 'GenOne'}, {'name': 'Omega'}]}],
                'straight': [{'league_id': 285202, 'observed_at': '2026-10-19T11:00:01Z', 'markets': [
                    {'matchupId': 5, 'type': 'moneyline', 'period': 1,
                     'prices': [{'price': -170}, {'price': 139}]}]}]})
            rows = pinnacle_rows(Path(tmp))
        self.assertEqual(rows, [])

    def test_missing_capture_is_inert(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(pinnacle_rows(Path(tmp)), [])


class HltvRankingModelTest(unittest.TestCase):
    def _rows(self):
        return [{'name': 'Fire Flux', 'points': 412.0, 'rank': 30,
                 'source_url': 'https://www.hltv.org/ranking/', 'snapshot_date': '2026-10-19'},
                {'name': 'ex-6666', 'points': 188.0, 'rank': 120,
                 'source_url': 'https://www.hltv.org/ranking/', 'snapshot_date': '2026-10-19'}]

    def _meta(self, day='2026-10-19', observed='2026-10-19T11:00:00Z'):
        return {'source_url': 'https://www.hltv.org/ranking/', 'snapshot_date': day,
                'observed_at': observed, 'evidence_file': 'data/origination/evidence/live-hltv-ranking.json',
                'publication_pages': 1}

    def test_logistic_transform_matches_published_formula(self):
        quote, detail = hltv_ranking.estimate(fixture(), self._rows(), {'aliases': []}, NOW, meta=self._meta())
        self.assertIsNotNone(quote, detail)
        expected = 1 / (1 + 10 ** ((188.0 - 412.0) / 400))
        self.assertAlmostEqual(quote['probabilities'][0], expected, places=6)
        self.assertEqual(quote['provider'], 'HLTV world ranking')
        self.assertEqual(quote['family'], 'model')

    def test_missing_team_stays_unresolved(self):
        rows = [r for r in self._rows() if r['name'] == 'Fire Flux']
        quote, reason = hltv_ranking.estimate(fixture(), rows, {'aliases': []}, NOW, meta=self._meta())
        self.assertIsNone(quote)
        self.assertIn('no HLTV world-ranking entry', reason)

    def test_stale_publication_rejected(self):
        quote, reason = hltv_ranking.estimate(fixture(), self._rows(), {'aliases': []}, NOW,
                                              meta=self._meta(day='2026-09-01', observed='2026-09-01T11:00:00Z'))
        self.assertIsNone(quote)
        self.assertIn('older than 14 days', reason)

    def test_registry_alias_reverse_join(self):
        registry = {'aliases': [{'alias': 'Flux Fire', 'canonical': 'Fire Flux', 'kind': 'test',
                                 'applies_to': ['NODWIN Clutch Series #13'],
                                 'evidence': [{'url': 'https://www.hltv.org/ranking/', 'detail': 'x'}]}]}
        rows = [dict(self._rows()[0], name='Flux Fire'), self._rows()[1]]
        quote, detail = hltv_ranking.estimate(fixture(), rows, registry, NOW, meta=self._meta())
        self.assertIsNotNone(quote, detail)
        self.assertEqual(quote['inputs'][0]['matched_as'], 'flux fire')  # domain name_key keeps spaces

    def test_missing_capture_is_inert(self):
        quote, reason = hltv_ranking.estimate(fixture(), [], {'aliases': []}, NOW, meta=None)
        self.assertIsNone(quote)


class WideBookGuidanceTest(unittest.TestCase):
    def test_midpoint_and_alignment(self):
        quote, spread = wide_book_quote(wide_market_row(), fixture(), {'aliases': []}, NOW)
        self.assertIsNotNone(quote)
        self.assertAlmostEqual(spread, 0.63)
        self.assertEqual(quote['family'], 'guidance')
        self.assertEqual(quote['probabilities'], quote['probabilities'])  # pair
        self.assertAlmostEqual(sum(quote['probabilities']), 1.0, places=6)

    def test_guidance_is_never_money(self):
        self.assertNotIn('guidance', MONEY_METHODS)

    def test_even_wide_book_has_no_directional_pick(self):
        row = wide_market_row(spread_pair=((0.05, 0.95), (0.06, 0.94)))
        result = resolve_match(fixture(), [], [], None, None, {'aliases': []}, NOW)
        # No rows at all: stays blank, never 50/50.
        self.assertIsNone(result['origination'])
        result = resolve_match(dict(fixture(), analysis=None), [row], [], None, None, {'aliases': []}, NOW)
        self.assertEqual(result['origination']['method'], 'guidance')
        self.assertIsNone(result['pick_index'])  # even midpoint: no lean is published as no lean

    def test_guidance_only_when_everything_else_fails(self):
        row = wide_market_row()
        # A compliant money quote must win over guidance.
        money = {'family': 'bookmaker', 'provider': 'Thunderpick', 'names': ['Fire Flux', 'ex-6666'],
                 'start': '2026-10-19T17:00:00Z', 'odds': [1.72, 2.10],
                 'observed_at': '2026-10-19T11:00:00Z', 'source_url': 'https://thunderpick.io/esports/counter-strike',
                 'event_id': '2767837', 'evidence_file': 'data/evidence/thunderpick-matches.json'}
        result = resolve_match(fixture(), [row], [money], None, None, {'aliases': []}, NOW)
        self.assertIn(result['origination']['method'], ('bookmaker', 'consensus'))
        self.assertNotEqual(result['origination']['method'], 'guidance')

    def test_valve_model_beats_guidance(self):
        row = wide_market_row()
        day = NOW.date().isoformat()
        ratings = [{'name': 'Fire Flux', 'points': 1620.0, 'standing': 40,
                    'roster': ['a', 'b', 'c', 'd', 'e'], 'snapshot_date': day,
                    'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'},
                   {'name': 'ex-6666', 'points': 1400.0, 'standing': 200,
                    'roster': ['f', 'g', 'h', 'i', 'j'], 'snapshot_date': day,
                    'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'}]
        meta = {'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                'snapshot_date': day, 'evidence_file': 'data/evidence/valve-ratings.json',
                'observed_at': '2026-10-19T11:00:00Z'}
        result = resolve_match(fixture(), [row], [], ratings, meta, {'aliases': []}, NOW)
        self.assertEqual(result['origination']['method'], 'model')
        self.assertIn('Valve', result['origination']['source'])

    def test_hltv_ranking_model_beats_guidance(self):
        row = wide_market_row()
        day = NOW.date().isoformat()
        rank_rows = [{'name': 'Fire Flux', 'points': 412.0, 'rank': 30,
                      'source_url': 'https://www.hltv.org/ranking/', 'snapshot_date': day},
                     {'name': 'ex-6666', 'points': 188.0, 'rank': 120,
                      'source_url': 'https://www.hltv.org/ranking/', 'snapshot_date': day}]
        meta = {'source_url': 'https://www.hltv.org/ranking/', 'snapshot_date': day,
                'observed_at': '2026-10-19T11:00:00Z',
                'evidence_file': 'data/origination/evidence/live-hltv-ranking.json'}
        result = resolve_match(fixture(), [row], [], None, None, {'aliases': []}, NOW,
                               hltv_rank=rank_rows, hltv_meta=meta)
        self.assertEqual(result['origination']['method'], 'model')
        self.assertEqual(result['origination']['source'], 'HLTV world ranking')
        self.assertTrue(any('HLTV world ranking' in r['stage'] for r in result['research']))

    def test_guidance_labels_and_limitations(self):
        row = wide_market_row()
        result = resolve_match(fixture(), [row], [], None, None, {'aliases': []}, NOW)
        o = result['origination']
        self.assertEqual(o['method'], 'guidance')
        self.assertIn('guidance only', o['label'].lower())
        self.assertTrue(any('GUIDANCE ONLY' in x for x in result['limitations']))
        self.assertTrue(any(r['stage'] == 'Wide-book guidance fallback' for r in result['research']))

    def test_featured_model_is_never_downgraded_to_guidance(self):
        featured = {'method': 'model', 'label': 'Research model estimate (Valve official ratings)',
                    'probabilities': [0.8, 0.2], 'fair_decimal': [1.25, 5.0],
                    'source': 'Valve official standings',
                    'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                    'observed_at': '2026-10-19T08:00:00Z', 'quotes': []}
        row = wide_market_row()
        result = resolve_match(dict(fixture(), analysis=featured, pick_index=0, research=[], limitations=[]),
                               [row], [], None, None, {'aliases': []}, NOW)
        self.assertEqual(result['origination']['method'], 'model')
        self.assertIsNone(result.get('upgraded_from_featured_model'))


class AliasRegistryTest(unittest.TestCase):
    def test_session_aliases_load_and_scope(self):
        registry = load_registry(Path('data/origination/aliases.json'))
        from scripts.originate import resolve_name
        canon, used = resolve_name('Betclic', registry, 'Stake Ranked Episode 6: Closed Qualifier')
        self.assertEqual(canon, 'apogee betclic')  # domain name_key: case/whitespace equivalence only
        self.assertEqual(len(used), 1)
        # Out of scope: the alias must not join any other competition.
        canon, used = resolve_name('Betclic', registry, 'Some Other Event')
        self.assertEqual(canon, 'betclic')
        self.assertEqual(used, [])
        canon, used = resolve_name('Aurora Young Blud', registry, 'Stake Ranked Episode 6: Closed Qualifier')
        self.assertEqual(canon, 'aurora yb')




class BovadaDisplayNameJoinTest(unittest.TestCase):
    """Session arena-75de2710: the one live Bovada line for a published blank.

    Bovada's public coupon listed CIS LAN Championship #9 fixture 1082762 as
    "CYBERSHOKE vs blinkdagger" at exactly 2026-10-21T15:00:00Z with a two-way
    prematch Moneyline (decimal 1.125 / 5.750), while Hotspawn and HLTV name the
    same side "ex-CYBERSHOKE". The reviewed registry now carries that scoped
    display-name variant; this test pins the join, its scope and the resulting
    no-vig estimate so the blank cannot silently regress to a default 50/50.
    """

    MATCH = {'id': '1082762', 'starts_at': '2026-10-21T15:00:00Z',
             'competition': 'CIS LAN Championship #9',
             'teams': [{'id': '1', 'name': 'ex-CYBERSHOKE'}, {'id': '2', 'name': 'BlinkDagger'}]}

    def registry(self):
        return load_registry(Path('data/origination/aliases.json'))

    def test_the_scoped_alias_exists_with_official_evidence(self):
        entry = next((a for a in self.registry()['aliases'] if a['alias'] == 'CYBERSHOKE'), None)
        self.assertIsNotNone(entry, 'the reviewed CYBERSHOKE -> ex-CYBERSHOKE entry is required')
        self.assertEqual(entry['canonical'], 'ex-CYBERSHOKE')
        self.assertEqual(entry['applies_to'], ['CIS LAN Championship #9'])
        self.assertTrue(entry.get('review_note'))
        urls = [ev['url'] for ev in entry['evidence']]
        self.assertTrue(any('hotspawn.com/matches/' in u for u in urls))
        self.assertTrue(any('hltv.org/matches/' in u for u in urls))
        self.assertTrue(any('bovada.lv/' in u for u in urls))
        self.assertTrue(all(u.startswith('https://') for u in urls))

    def test_the_bovada_pair_joins_this_fixture_and_nothing_else(self):
        values, used, status = pair_join(['CYBERSHOKE', 'blinkdagger'], '2026-10-21T15:00:00Z',
                                         self.MATCH, self.registry())
        self.assertEqual(status, 'matched')
        self.assertEqual([a['alias'] for a in used], ['CYBERSHOKE'])
        other = dict(self.MATCH, competition='CCT Europe 2026 Series #11')
        self.assertEqual(pair_join(['CYBERSHOKE', 'blinkdagger'], '2026-10-21T15:00:00Z',
                                   other, self.registry())[2], 'names')
        self.assertEqual(pair_join(['CYBERSHOKE', 'blinkdagger'], '2026-10-21T16:00:00Z',
                                   self.MATCH, self.registry())[2], 'time')

    def test_the_published_probability_is_the_no_vig_bovada_line(self):
        from scripts.domain import no_vig
        self.assertEqual([round(x, 6) for x in no_vig([1.125, 5.750])], [0.836364, 0.163636])
        self.assertEqual(selection(no_vig([1.125, 5.750])), 0)


class ReplayBoundaryTest(unittest.TestCase):
    """The build-time replay validator must actually execute the guidance path.

    The first CI run of the guidance rung failed with NameError: name 'originate'
    is not defined inside validate_origination's guidance branch — a path the
    frozen repository fixtures never exercised (they contain no guidance rows).
    This test runs that branch end-to-end on a synthetic tree.
    """

    def test_validate_origination_replays_guidance_rows(self):
        import shutil
        from unittest.mock import patch
        from scripts.build_origination import validate_origination
        from scripts.domain import normalize_pair

        row = wide_market_row()
        start = row['start']
        with TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / 'origination' / 'evidence').mkdir(parents=True)
            shutil.copy('data/origination/aliases.json', source / 'origination' / 'aliases.json')
            fx = dict(fixture(), availability='open', lobby_url=fixture()['source_url'],
                      tier=None, source_status='scheduled')
            latest = {'inventory_observed_at': row['observed_at'],
                      'matches': [dict(fx, analysis=None, pick_index=None)]}
            (source / 'latest.json').write_text(json.dumps(latest))
            quote, spread = wide_book_quote(row, fx, {'aliases': []}, NOW)
            self.assertIsNotNone(quote)
            probs = quote['probabilities']
            origination = {
                'schema_version': 1, 'generated_at': iso(NOW),
                'source_snapshot_at': row['observed_at'],
                'matches': [dict(fx, origination={
                    'method': 'guidance', 'label': 'Wide-book indicative midpoint (guidance only)',
                    'probabilities': probs,
                    'fair_decimal': [round(1 / p, 3) for p in probs],
                    'quotes': [quote], 'source': quote['provider'],
                    'source_url': quote['source_url'], 'observed_at': quote['observed_at'],
                }, pick_index=(0 if probs[0] > probs[1] else 1 if probs[1] > probs[0] else None),
                    aliases_used=[], research=[], limitations=['GUIDANCE ONLY'], time_flags=[])],
            }
            with patch('scripts.originate.polymarket_rows', return_value=[row]), \
                    patch('scripts.originate.kalshi_rows', return_value=[]):
                validate_origination(origination, source)  # must not raise

    def test_validate_origination_replays_hltv_ranking_rows(self):
        import shutil
        from scripts.build_origination import validate_origination

        with TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / 'origination' / 'evidence').mkdir(parents=True)
            shutil.copy('data/origination/aliases.json', source / 'origination' / 'aliases.json')
            fx = dict(fixture(), availability='open', lobby_url=fixture()['source_url'],
                      tier=None, source_status='scheduled')
            latest = {'inventory_observed_at': '2026-10-19T11:00:00Z',
                      'matches': [dict(fx, analysis=None, pick_index=None)]}
            (source / 'latest.json').write_text(json.dumps(latest))
            day = NOW.date().isoformat()
            capture = {'source': 'HLTV official weekly world ranking',
                       'source_url': 'https://www.hltv.org/ranking/teams',
                       'observed_at': '2026-10-19T11:00:00Z', 'snapshot_date': day,
                       'pages': [{'url': 'https://www.hltv.org/ranking/teams', 'status': 'ok',
                                  'observed_at': '2026-10-19T11:00:00Z', 'rows': [
                                      {'team': 'Fire Flux', 'points': 412.0, 'rank': 30},
                                      {'team': 'ex-6666', 'points': 188.0, 'rank': 120}]}]}
            (source / 'origination' / 'evidence' / 'live-hltv-ranking.json').write_text(json.dumps(capture))
            registry = load_registry(source / 'origination' / 'aliases.json')
            quote, detail = hltv_ranking.estimate(fx, hltv_ranking.load(source / 'origination' / 'evidence')[0],
                                                  registry, NOW,
                                                  meta=hltv_ranking.load(source / 'origination' / 'evidence')[1])
            self.assertIsNotNone(quote, detail)
            probs = quote['probabilities']
            origination = {
                'schema_version': 1, 'generated_at': iso(NOW),
                'source_snapshot_at': '2026-10-19T11:00:00Z',
                'matches': [dict(fx, origination=dict(
                    quote, method='model',
                    label='Research model estimate (HLTV world ranking)',
                    fair_decimal=[round(1 / p, 3) for p in probs], quotes=[dict(quote)],
                    source='HLTV world ranking'),
                    pick_index=(0 if probs[0] > probs[1] else 1 if probs[1] > probs[0] else None),
                    aliases_used=[], research=[], limitations=['Research model'], time_flags=[])],
            }
            validate_origination(origination, source)  # must not raise


if __name__ == '__main__':
    unittest.main()
