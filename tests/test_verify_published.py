"""Deterministic tests for the V-2 published-data audit.

Every test builds its own synthetic evidence directory, so none of them depend on live
sources, on what the market happened to quote, or on which fixtures are still prematch.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_published import (MAX_ACCEPTED_SPREAD, audit, candidate_similarity,
                                      classify_candidate, compare_names, devig, executable_book,
                                      main, market_start_utc, median, overround, recompute_counts,
                                      row_aliases, row_event_id, start_time_agreement,
                                      swap_if_needed)

# 2026-10-16T14:00:00Z and 17:00:00Z, as HLTV's own data-unix attributes state them.
AURORA_START = '2026-10-16T14:00:00Z'
LEGACY_START = '2026-10-16T17:00:00Z'
AURORA_UNIX = 1792159200000


def fixture_row(fixture_id, teams, *, start=AURORA_START, probabilities=None, method=None,
                pick=None, quotes=None, aliases=None, research=None, limitations=None,
                competition='Thunderpick World Championship 2026', event_id=None, source_url=None):
    row = {
        'id': fixture_id,
        'teams': [{'id': str(i), 'name': name} for i, name in enumerate(teams)],
        'competition': competition,
        'starts_at': start,
        'locks_at': start,
        'availability': 'open',
        'tier': 's',
        'source_url': f'https://www.hotspawn.com/matches/{fixture_id}',
        'lobby_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{fixture_id}',
        'pick_index': pick,
        'limitations': limitations or [],
        'research': research or [],
        'aliases_used': aliases or [],
    }
    if probabilities is not None:
        row['origination'] = {
            'method': method, 'label': method, 'probabilities': probabilities,
            'fair_decimal': [round(1 / p, 3) for p in probabilities],
            'source': 'Polymarket', 'source_url': source_url or 'https://polymarket.com/event/x',
            'observed_at': '2026-10-16T08:18:42Z', 'event_id': event_id,
            'quotes': quotes or [],
        }
    else:
        row['origination'] = {'method': None, 'probabilities': None}
    return row


def polymarket_line(event_id, slug, outcomes, prices, *, tokens=('t1', 't2'), spread=0.01,
                    start='2026-10-16 14:00:00+00', updated='2026-10-16T08:17:08Z'):
    return {
        'event_id': event_id, 'event_slug': slug, 'event_title': f'Counter-Strike: {slug}',
        'market_id': 'm1', 'question': f'Counter-Strike: {outcomes[0]} vs {outcomes[1]}',
        'outcomes': outcomes, 'outcome_prices': [str(p) for p in prices],
        'game_start_time': start, 'event_start_time': AURORA_START.replace('Z', '+00:00'),
        'best_bid': prices[0], 'best_ask': prices[0] + spread, 'spread': spread,
        'volume': 100.0, 'liquidity': 200.0, 'accepting_orders': True,
        'active': True, 'closed': False, 'clob_token_ids': list(tokens), 'updated_at': updated,
        'source_url': f'https://polymarket.com/event/{slug}',
    }


def clob_book(bids, asks, token='t1'):
    return {'asset_id': token, 'market': '0xcond', 'timestamp': '2026-10-16T08:17:00Z',
            'source_url': f'https://clob.polymarket.com/book?token_id={token}',
            'bids': [{'price': str(p), 'size': str(s)} for p, s in bids],
            'asks': [{'price': str(p), 'size': str(s)} for p, s in asks]}


def bovada_line(description, names, odds, *, start=AURORA_START, usable=True, link='/esports/x'):
    return {'event_id': '32299372', 'description': description, 'event_type': 'GAMEEVENT',
            'live': False, 'start_utc': start.replace('Z', '+00:00'), 'league': 'TWC / CS2',
            'competitors': names, 'moneyline_markets': 1 if usable else 0,
            'prematch_main_moneyline': usable,
            'outcomes': [{'name': n, 'decimal': o, 'american': '-100', 'status': 'O'}
                         for n, o in zip(names, odds)] if usable else [],
            'source_url': 'https://www.bovada.lv' + link, 'page_url': 'https://www.bovada.lv/sports'}


def build_evidence(tmp: Path, *, rows, moneylines=None, books=None, bovada=None,
                   thunderpick=None, kalshi=None, valve=None, hotspawn_ids=None,
                   deployed_counts=None, generated='2026-10-16T08:18:38Z',
                   observed='2026-10-16T08:19:40Z', flags=None):
    (tmp / 'raw').mkdir(parents=True, exist_ok=True)
    ids = hotspawn_ids if hotspawn_ids is not None else [r['id'] for r in rows]
    deployed = {
        'generated_at': generated, 'observed_at': observed,
        'coverage_complete': True, 'run_status': 'partial-picks',
        'refresh_interval_hours': 4, 'stale_after_hours': 8,
        'counts': deployed_counts if deployed_counts is not None else recompute_counts(
            {'matches': [{**r, 'analysis': (r.get('origination') if r.get('origination', {}).get('probabilities') else None)}
                         for r in rows]}),
        'matches': [{**r, 'analysis': (r.get('origination')
                                       if r.get('origination', {}).get('probabilities') else None)}
                    for r in rows],
        'flags': flags if flags is not None else [
            {'id': f'unresolved-{r["id"]}', 'title': 't', 'detail': 'd', 'severity': 'notice',
             'match_ids': [r['id']], 'source_urls': ['https://www.hltv.org/matches']}
            for r in rows if not r.get('origination', {}).get('probabilities')],
    }
    (tmp / 'raw' / 'pages-latest.json').write_text(json.dumps(deployed))
    (tmp / 'raw' / 'pages-origination.json').write_text(json.dumps(
        {'generated_at': generated, 'observed_at': observed,
         'counts': {'active': len(rows)}, 'matches': rows}))
    (tmp / 'raw' / 'hotspawn-fixtures.json').write_text(json.dumps(
        {'data': [{'id': str(i), 'status': 'scheduled'} for i in ids]}))
    (tmp / 'observations.json').write_text(json.dumps({
        'session': 'arena-ba7164a0',
        'probe_started_at': '2026-10-16T08:19:40Z', 'probe_finished_at': observed,
        'requests': [{'label': 'x', 'url': 'https://www.hltv.org/matches', 'status': 'ok',
                      'observed_at': observed}],
        'polymarket': {'moneylines': moneylines or [], 'books': books or {},
                       'directory_games': [], 'limitations': [],
                       'observed_at': observed, 'source_url': 'https://polymarket.com/esports/cs2'},
        'other_books': {'providers': {
            'bovada': {'moneylines': bovada or [], 'observed_at': observed},
            'thunderpick': {'moneylines': thunderpick or [], 'observed_at': observed},
            'kalshi': {'markets': kalshi or [], 'observed_at': observed},
        }, 'limitations': []},
        'valve': valve or {'ratings': {}, 'ambiguous': {}, 'absent': [], 'limitations': [],
                           'snapshot_used': 'standings_global_2026_10_05.md',
                           'standings_as_of': '2026_10_05',
                           'source_url': 'https://raw.githubusercontent.com/ValveSoftware/'
                                         'counter-strike_regional_standings/main/live/2026/'
                                         'standings_global_2026_10_05.md'},
        'hotspawn': {'count': len(ids)},
    }))
    return tmp


def run_audit(**kwargs):
    with tempfile.TemporaryDirectory() as tmp:
        build_evidence(Path(tmp), **kwargs)
        return audit(Path(tmp))


class Arithmetic(unittest.TestCase):
    def test_devig_removes_the_overround_proportionally(self):
        # Bovada's archived Aurora line: 1.434783 / 2.750.
        fair = devig(['1.434783', '2.750'])
        self.assertAlmostEqual(fair[0], 0.657, places=3)
        self.assertAlmostEqual(sum(fair), 1.0, places=12)
        self.assertAlmostEqual(overround(['1.434783', '2.750']), 1.060606, places=5)

    def test_an_unusable_price_is_rejected_rather_than_normalised(self):
        for bad in (['1.0', '2.0'], ['0.9', '2.0'], [None, '2.0'], ['x', '2.0'], ['2.0']):
            with self.subTest(bad=bad):
                self.assertIsNone(devig(bad))
                self.assertIsNone(overround(bad))

    def test_midpoint_and_median(self):
        self.assertEqual(median([0.695, 0.69191919]), 0.69345959500000005 if False else
                         (0.69191919 + 0.695) / 2)
        self.assertEqual(median([0.4, 0.5, 0.6]), 0.5)
        self.assertIsNone(median([]))


class ExecutableBook(unittest.TestCase):
    def test_levels_without_size_are_not_executable(self):
        book = executable_book(clob_book([(0.60, 0), (0.55, 100)], [(0.70, 0), (0.75, 50)]))
        self.assertEqual(book['best_bid'], 0.55)
        self.assertEqual(book['best_ask'], 0.75)
        self.assertEqual(book['spread'], 0.2)
        self.assertFalse(book['executable_within_ceiling'])

    def test_provider_array_order_is_not_trusted(self):
        book = executable_book(clob_book([(0.10, 5), (0.60, 5)], [(0.99, 5), (0.62, 5)]))
        self.assertEqual((book['best_bid'], book['best_ask']), (0.60, 0.62))
        self.assertAlmostEqual(book['midpoint'], 0.61)
        self.assertTrue(book['executable_within_ceiling'])
        self.assertLessEqual(book['spread'], MAX_ACCEPTED_SPREAD)

    def test_a_crossed_or_empty_book_is_never_reported_as_executable(self):
        self.assertIsNone(executable_book(clob_book([], [(0.9, 5)])))
        self.assertIsNone(executable_book({}))
        crossed = executable_book(clob_book([(0.90, 5)], [(0.10, 5)]))
        self.assertTrue(crossed['crossed'])
        self.assertFalse(crossed['executable_within_ceiling'])

    def test_the_aimclub_book_that_the_ladder_rejected_is_reproduced(self):
        # Archived first-party book for Polymarket event 1183120: bids stop at 0.03 and
        # asks start at 0.96, exactly the 0.93 spread the ladder reported.
        book = executable_book(clob_book([(0.01, 33.42), (0.02, 2400), (0.03, 20.86)],
                                         [(0.99, 39.32), (0.98, 2100), (0.97, 5547.7), (0.96, 14.16)]))
        self.assertEqual((book['best_bid'], book['best_ask']), (0.03, 0.96))
        self.assertAlmostEqual(book['spread'], 0.93)
        self.assertFalse(book['executable_within_ceiling'])


class IdentityJoins(unittest.TestCase):
    def test_both_sides_must_relate_for_a_candidate_to_be_plausible(self):
        # Regression: one-sided overlap paired 'ex-6666 vs Privateer' with the unrelated
        # 'mellren vs Privateer Gaming' fixture, and 'antidaun vs Phantom Academy' with
        # four unrelated 'Phantom ...' fixtures.
        self.assertFalse(candidate_similarity(['ex-6666', 'Privateer'],
                                              ['mellren', 'Privateer Gaming'])['plausible'])
        self.assertFalse(candidate_similarity(['antidaun', 'Phantom Academy'],
                                              ['Voca', 'Phantom'])['plausible'])
        self.assertTrue(candidate_similarity(['Procyon', 'LOS NINOS'],
                                             ['Procyon Gaming', 'Los Niños'])['plausible'])
        self.assertTrue(candidate_similarity(['Aurora', '9z'],
                                             ['Team AURORA', '9Z Globant'])['plausible'])
        self.assertFalse(candidate_similarity(['Aurora'], ['Team AURORA', '9Z Globant'])['plausible'])

    def test_compare_names_never_asserts_an_equivalence_it_lacks(self):
        self.assertEqual(compare_names(['Aurora', '9z'], ['Aurora', '9z']), 'exact')
        self.assertEqual(compare_names(['LOS NINOS', 'Procyon'], ['Los Ninos', 'Procyon']), 'normalized')
        self.assertEqual(compare_names(['Aurora', '9z'], ['9z', 'Aurora']), 'normalized-swapped')
        self.assertEqual(compare_names(['Aurora', '9z'], ['Team AURORA', '9Z Globant']), 'unverified')
        self.assertEqual(compare_names(['Aurora'], ['Aurora', '9z']), 'unverified')

    def test_swap_aligns_only_when_both_names_are_present(self):
        self.assertEqual(swap_if_needed([0.6, 0.4], ['9z', 'Aurora'], ['Aurora', '9z']), [0.4, 0.6])
        self.assertEqual(swap_if_needed([0.6, 0.4], ['Aurora', '9z'], ['Aurora', '9z']), [0.6, 0.4])
        self.assertIsNone(swap_if_needed([0.6, 0.4], ['Falcons', '9z'], ['Aurora', '9z']))

    def test_start_times_are_compared_in_utc(self):
        self.assertEqual(start_time_agreement('2026-10-16T14:00:00Z', '2026-10-16T14:00:00+00:00'), 'agrees')
        self.assertEqual(start_time_agreement('2026-10-16T14:00:00Z', '2026-10-16 14:00:00+00'), 'agrees')
        self.assertEqual(start_time_agreement('2026-10-16T14:00:00Z', '2026-10-16T15:00:00Z'),
                         'differs-by-60-minutes')
        self.assertEqual(start_time_agreement('2026-10-16T14:00:00Z', None), 'unknown')
        self.assertEqual(start_time_agreement('2026-10-16T14:00:00Z', '2026-10-19T14:00:00Z'), 'differs')


class RowHelpers(unittest.TestCase):
    def test_a_consensus_row_carries_its_event_id_on_its_quotes(self):
        # Verified against fixtures 1080205 and 1081775 of the deployed snapshot: both are
        # Polymarket + Kalshi consensus rows whose top-level event_id is null.
        row = fixture_row('1', ['Aurora', '9z'], probabilities=[0.69, 0.31], method='consensus',
                          quotes=[{'provider': 'Kalshi', 'event_id': 'KX1'},
                                  {'provider': 'Polymarket', 'event_id': '1194512'}])
        self.assertEqual(row_event_id(row), '1194512')
        row['origination']['event_id'] = '999'
        self.assertEqual(row_event_id(row), '999')
        self.assertEqual(row_event_id(fixture_row('2', ['A', 'B'])), '')

    def test_only_the_rows_own_published_aliases_are_used(self):
        row = fixture_row('1', ['Aurora', '9z'],
                          aliases=[{'alias': 'Aurora Gaming', 'canonical': 'Aurora'},
                                   {'alias': '', 'canonical': 'X'}, 'not-a-dict'])
        self.assertEqual(row_aliases(row), {'aurora gaming': 'Aurora'})
        self.assertEqual(row_aliases({}), {})


class InventoryAndCounts(unittest.TestCase):
    def test_a_missing_or_invented_fixture_is_reported_never_reconciled(self):
        rows = [fixture_row('1080205', ['Aurora', '9z'], probabilities=[0.69, 0.31],
                            method='market', pick=0, event_id='1194512')]
        result = run_audit(rows=rows, hotspawn_ids=['1080205', '1081775'])
        inventory = result['inventory_reconciliation']
        self.assertFalse(inventory['reconciled'])
        self.assertEqual(inventory['missing_from_site'], ['1081775'])
        self.assertEqual(inventory['extra_on_site'], [])
        self.assertTrue(any(f['id'].endswith('inventory-divergence') for f in result['flags']))

    def test_a_fixture_that_started_between_the_two_readings_is_not_a_coverage_gap(self):
        # The site snapshot was generated before kick-off; Hotspawn drops a fixture once it
        # starts. Reporting that as a coverage gap would be a false alarm.
        rows = [fixture_row('1079586', ['Ninjas in Pyjamas', 'Team Liquid'],
                            start='2026-10-16T08:00:00Z', probabilities=[0.49, 0.51],
                            method='consensus', pick=1,
                            quotes=[{'provider': 'Polymarket', 'event_id': '1194412'}]),
                fixture_row('1080285', ['Voca', 'Phantom'], start='2026-10-16T10:00:00Z',
                            probabilities=[0.45, 0.55], method='market', pick=1,
                            event_id='1173317')]
        result = run_audit(rows=rows, hotspawn_ids=['1080285'],
                           generated='2026-10-16T07:35:00Z', observed='2026-10-16T09:44:00Z')
        inventory = result['inventory_reconciliation']
        self.assertEqual(inventory['extra_on_site'], ['1079586'])
        self.assertEqual([r['id'] for r in inventory['started_since_the_snapshot']], ['1079586'])
        self.assertTrue(inventory['explained_by_elapsed_time'])
        self.assertIn('passed their scheduled start', inventory['verdict'])
        flags = [f for f in result['flags'] if f['id'].endswith('inventory-divergence')]
        self.assertEqual(flags[0]['severity'], 'notice')

    def test_a_divergence_the_clock_cannot_explain_stays_a_review_finding(self):
        rows = [fixture_row('1080285', ['Voca', 'Phantom'], start='2026-10-16T10:00:00Z',
                            probabilities=[0.45, 0.55], method='market', pick=1,
                            event_id='1173317')]
        # 1099999 is published although Hotspawn never listed it and it has not started.
        rows.append(fixture_row('1099999', ['Ghost', 'Phantom'], start='2026-10-20T10:00:00Z'))
        result = run_audit(rows=rows, hotspawn_ids=['1080285'],
                           generated='2026-10-16T07:35:00Z', observed='2026-10-16T09:44:00Z')
        inventory = result['inventory_reconciliation']
        self.assertEqual(inventory['unexplained_extra_on_site'], ['1099999'])
        self.assertFalse(inventory['explained_by_elapsed_time'])
        flags = [f for f in result['flags'] if f['id'].endswith('inventory-divergence')]
        self.assertEqual(flags[0]['severity'], 'review')
        self.assertIn('NOT explained', flags[0]['detail'])

    def test_counts_are_recomputed_from_the_rows(self):
        rows = [fixture_row('1', ['Aurora', '9z'], probabilities=[0.69, 0.31], method='market', pick=0),
                fixture_row('2', ['BetBoom', 'Legacy'], start=LEGACY_START)]
        result = run_audit(rows=rows, deployed_counts={'inventory': 2, 'upcoming': 2, 'archived': 0,
                                                       'unknown_schedule': 0, 'picks': 1,
                                                       'market': 1, 'model': 0, 'bookmaker': 0,
                                                       'unresolved': 1, 'no_edge': 0})
        self.assertEqual(result['published_counts_check']['mismatches'], [])
        lied = run_audit(rows=rows, deployed_counts={'inventory': 2, 'upcoming': 2, 'archived': 0,
                                                     'unknown_schedule': 0, 'picks': 2,
                                                     'market': 1, 'model': 0, 'bookmaker': 0,
                                                     'unresolved': 1, 'no_edge': 0})
        self.assertEqual(lied['published_counts_check']['mismatches'],
                         [{'count': 'picks', 'published': 2, 'recomputed': 1}])
        self.assertTrue(any(f['id'].endswith('count-picks') for f in lied['flags']))


class FirstPartyVerification(unittest.TestCase):
    def setUp(self):
        self.moneylines = [polymarket_line('1194512', 'cs2-aur1-9z-2026-10-16',
                                           ['Aurora Gaming', '9z'], [0.695, 0.305])]
        self.books = {'t1': clob_book([(0.69, 100)], [(0.70, 100)], 't1'),
                      't2': clob_book([(0.30, 100)], [(0.31, 100)], 't2')}

    def test_a_correct_row_is_confirmed_against_polymarket_itself(self):
        rows = [fixture_row('1080205', ['Aurora', '9z'], probabilities=[0.69346, 0.30654],
                            method='market', pick=0, event_id='1194512',
                            aliases=[{'alias': 'Aurora Gaming', 'canonical': 'Aurora'}])]
        result = run_audit(rows=rows, moneylines=self.moneylines, books=self.books)
        check = result['first_party_market_check']
        self.assertEqual(len(check['agreeing']), 1)
        self.assertEqual(check['drifted_or_reversed'], [])
        record = check['agreeing'][0]
        self.assertEqual(record['first_party_prices'], [0.695, 0.305])
        self.assertTrue(record['same_favourite'])
        self.assertEqual(record['aligned_via_reviewed_alias'], ['aurora gaming -> Aurora'])
        self.assertEqual(record['source_url'], 'https://polymarket.com/event/cs2-aur1-9z-2026-10-16')

    def test_a_reversed_favourite_is_flagged_and_never_silently_accepted(self):
        rows = [fixture_row('1080205', ['Aurora', '9z'], probabilities=[0.30654, 0.69346],
                            method='market', pick=1, event_id='1194512',
                            aliases=[{'alias': 'Aurora Gaming', 'canonical': 'Aurora'}])]
        result = run_audit(rows=rows, moneylines=self.moneylines, books=self.books)
        self.assertEqual(len(result['first_party_market_check']['drifted_or_reversed']), 1)
        flags = [f for f in result['flags'] if f['id'].endswith('first-party-1080205')]
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]['severity'], 'review')
        self.assertIn('opposite', flags[0]['title'])
        self.assertIn('https://polymarket.com/event/cs2-aur1-9z-2026-10-16', flags[0]['source_urls'])

    def test_an_unjoinable_name_is_neither_confirmed_nor_contradicted(self):
        rows = [fixture_row('1080205', ['Aurora', '9z'], probabilities=[0.69, 0.31],
                            method='market', pick=0, event_id='1194512')]
        result = run_audit(rows=rows, moneylines=self.moneylines, books=self.books)
        unverifiable = result['first_party_market_check']['unverifiable']
        self.assertEqual(len(unverifiable), 1)
        self.assertIn('alignment is not assumed', unverifiable[0]['reason'])
        self.assertEqual(result['first_party_market_check']['agreeing'], [])


class UnresolvedClassification(unittest.TestCase):
    def test_an_executable_line_under_a_reviewed_alias_is_a_review_flag(self):
        rows = [fixture_row('1081502', ['Procyon', 'LOS NINOS'],
                            competition='CCT South America 2026 Series #7',
                            start='2026-10-16T16:00:00Z',
                            limitations=['No verified inputs; probabilities intentionally left blank.'],
                            aliases=[{'alias': 'Procyon Gaming', 'canonical': 'Procyon'},
                                     {'alias': 'Los Niños', 'canonical': 'LOS NINOS'}])]
        line = polymarket_line('1199999', 'cs2-pcy-ln-2026-10-16', ['Procyon', 'LOS NINOS'],
                               [0.67, 0.33], start='2026-10-16 16:00:00+00')
        books = {'t1': clob_book([(0.66, 10)], [(0.68, 10)], 't1'),
                 't2': clob_book([(0.32, 10)], [(0.34, 10)], 't2')}
        result = run_audit(rows=rows, moneylines=[line], books=books)
        entry = result['unresolved_review'][0]
        self.assertEqual(len(entry['usable_lines']), 1)
        self.assertTrue(any(f['id'].endswith('unresolved-has-usable-line-1081502')
                            for f in result['flags']))

    def test_a_wide_book_confirms_the_rejection_instead_of_contradicting_it(self):
        rows = [fixture_row('1081527', ['aimclub', 'BASEMENT BOYS'],
                            competition='DraculaN Season 7', start='2026-10-19T09:00:00Z',
                            limitations=['No verified inputs; probabilities intentionally left blank.'])]
        line = polymarket_line('1183120', 'cs2-aim1-bmb-2026-10-19', ['aimclub', 'BASEMENT BOYS'],
                               [0.495, 0.505], spread=0.93, start='2026-10-19 09:00:00+00')
        books = {'t1': clob_book([(0.03, 20.86)], [(0.96, 14.16)], 't1'),
                 't2': clob_book([(0.04, 14.16)], [(0.97, 20.86)], 't2')}
        result = run_audit(rows=rows, moneylines=[line], books=books)
        entry = result['unresolved_review'][0]
        self.assertEqual(entry['usable_lines'], [], 'a 0.93-wide book is not a usable line')
        self.assertEqual(len(entry['unusable_books']), 1)
        flags = [f for f in result['flags'] if f['id'].endswith('unresolved-rejection-confirmed-1081527')]
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]['severity'], 'notice')
        self.assertIn('confirms', flags[0]['detail'])

    def test_a_one_sided_name_overlap_produces_no_candidate_at_all(self):
        rows = [fixture_row('1081521', ['ex-6666', 'Privateer'],
                            competition='CCT Europe 2026 Challengers #8',
                            start='2026-10-18T13:45:00Z')]
        unrelated = polymarket_line('1190000', 'cs2-mellre-pg5-2026-10-16',
                                    ['mellren', 'Privateer Gaming'], [0.86, 0.14],
                                    start='2026-10-16 14:00:00+00')
        result = run_audit(rows=rows, moneylines=[unrelated],
                           books={'t1': clob_book([(0.85, 9)], [(0.87, 9)], 't1'),
                                  't2': clob_book([(0.13, 9)], [(0.15, 9)], 't2')})
        self.assertEqual(result['unresolved_review'][0]['independent_lines'], [])
        self.assertEqual(result['unresolved_review'][0]['alias_candidates'], [])

    def test_a_both_sided_overlap_with_differing_names_is_only_an_alias_candidate(self):
        rows = [fixture_row('1081526', ['Infinite', 'Insiders'], competition='DraculaN Season 7',
                            start='2026-10-19T09:00:00Z')]
        line = polymarket_line('1190001', 'cs2-inf6-ins-2026-10-19', ['Infinite', 'Insiders Esport'],
                               [0.55, 0.45], start='2026-10-19 09:00:00+00')
        self.assertEqual(market_start_utc(line), '2026-10-19T09:00:00Z',
                         'Gamma publishes gameStartTime with a space separator')
        result = run_audit(rows=rows, moneylines=[line],
                           books={'t1': clob_book([(0.54, 9)], [(0.56, 9)], 't1'),
                                  't2': clob_book([(0.44, 9)], [(0.46, 9)], 't2')})
        entry = result['unresolved_review'][0]
        self.assertEqual(entry['usable_lines'], [])
        self.assertEqual(len(entry['alias_candidates']), 1)
        self.assertEqual(entry['alias_candidates'][0]['start_time'], 'agrees')
        flags = [f for f in result['flags'] if f['id'].endswith('unresolved-alias-candidate-1081526')]
        self.assertEqual(len(flags), 1)
        self.assertIn('NOT verified', flags[0]['detail'])


class ValveVerification(unittest.TestCase):
    def test_a_duplicate_valve_name_confirms_the_stated_rejection(self):
        rows = [fixture_row('1081527', ['aimclub', 'BASEMENT BOYS'], start='2026-10-19T09:00:00Z',
                            research=[{'stage': 'Research model', 'status': 'unresolved',
                                       'detail': 'aimclub: multiple Valve rosters share this name',
                                       'source_url': 'https://github.com/ValveSoftware/'
                                                     'counter-strike_regional_standings/blob/main/'
                                                     'live/2026/standings_global_2026_10_05.md'}])]
        valve = {'snapshot_used': 'standings_global_2026_10_05.md', 'standings_as_of': '2026_10_05',
                 'source_url': 'https://raw.githubusercontent.com/x', 'limitations': [],
                 'ratings': {}, 'absent': ['BASEMENT BOYS'],
                 'ambiguous': {'aimclub': [
                     {'standing': 77, 'points': 1113, 'team_name': 'aimclub',
                      'roster': ['ERSIN', 'mhN1', 'ragga', 'waZz', 'zewts'],
                      'snapshot': 'standings_global_2026_10_05.md',
                      'source_url': 'https://raw.githubusercontent.com/ValveSoftware/x'},
                     {'standing': 336, 'points': 504, 'team_name': 'aimclub',
                      'roster': ['Ed1m', 'ERSIN', 'RoberttMP', 'XELLOW', 'zewts'],
                      'snapshot': 'standings_global_2026_10_05.md',
                      'source_url': 'https://raw.githubusercontent.com/ValveSoftware/x'}]}}
        result = run_audit(rows=rows, valve=valve)
        verifications = result['unresolved_review'][0]['verifications']
        confirmed = [v for v in verifications if v['status'] == 'confirmed']
        self.assertEqual(len(confirmed), 2)
        self.assertIn('lists this exact name 2 times', confirmed[0]['detail'])
        self.assertIn('ERSIN', confirmed[0]['detail'])
        self.assertTrue(any('no Valve rating row' in v['claim'] for v in confirmed))


class CrossChecks(unittest.TestCase):
    def test_an_independent_book_disagreeing_with_the_pick_is_flagged_with_both_links(self):
        rows = [fixture_row('1079588', ['Astralis', 'MIBR'], probabilities=[0.485, 0.515],
                            method='market', pick=1, event_id='1196576',
                            source_url='https://polymarket.com/event/cs2-ast10-mibr-2026-10-16')]
        bovada = [bovada_line('Astralis vs MIBR', ['Astralis', 'MIBR'], ['1.833333', '1.909091'])]
        result = run_audit(rows=rows, bovada=bovada)
        disagreeing = result['cross_checks']['disagreeing']
        self.assertEqual(len(disagreeing), 1)
        record = disagreeing[0]
        self.assertEqual(record['published_pick'], 'MIBR')
        self.assertEqual(record['independent_pick'], 'Astralis')
        self.assertEqual(record['independent_provider'], 'Bovada')
        flags = [f for f in result['flags'] if f['id'].endswith('pick-direction-1079588')]
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]['severity'], 'review')
        self.assertIn('https://www.bovada.lv/esports/x', flags[0]['source_urls'])
        self.assertIn('https://polymarket.com/event/cs2-ast10-mibr-2026-10-16', flags[0]['source_urls'])

    def test_an_agreeing_book_is_not_a_finding(self):
        rows = [fixture_row('1080205', ['Aurora', '9z'], probabilities=[0.69346, 0.30654],
                            method='consensus', pick=0,
                            quotes=[{'provider': 'Polymarket', 'event_id': '1194512'}],
                            aliases=[{'alias': 'Team AURORA', 'canonical': 'Aurora'},
                                     {'alias': '9Z Globant', 'canonical': '9z'}])]
        bovada = [bovada_line('Team AURORA vs 9Z Globant', ['Team AURORA', '9Z Globant'],
                              ['1.434783', '2.750'])]
        result = run_audit(rows=rows, bovada=bovada)
        self.assertEqual(result['cross_checks']['disagreeing'], [])
        self.assertFalse(any(f['id'].endswith('pick-direction-1080205') for f in result['flags']))


class FlagContract(unittest.TestCase):
    """Every flag must be reviewable: a source link, and only fixtures that exist."""

    def test_flags_are_well_formed_and_officially_sourced(self):
        from scripts.audit_rows import is_official
        rows = [fixture_row('1080205', ['Aurora', '9z'], probabilities=[0.69346, 0.30654],
                            method='market', pick=0, event_id='1194512',
                            aliases=[{'alias': 'Aurora Gaming', 'canonical': 'Aurora'}]),
                fixture_row('1081527', ['aimclub', 'BASEMENT BOYS'], start='2026-10-19T09:00:00Z')]
        result = run_audit(rows=rows, moneylines=[polymarket_line(
            '1194512', 'cs2-aur1-9z-2026-10-16', ['Aurora Gaming', '9z'], [0.305, 0.695])],
            books={'t1': clob_book([(0.30, 9)], [(0.31, 9)], 't1'),
                   't2': clob_book([(0.69, 9)], [(0.70, 9)], 't2')})
        ids = {r['id'] for r in rows}
        self.assertTrue(result['flags'])
        for flag in result['flags']:
            with self.subTest(flag=flag['id']):
                self.assertTrue(flag['id'].startswith('arena-ba7164a0-'))
                self.assertIn(flag['severity'], {'notice', 'review', 'watch', 'critical'})
                self.assertTrue(flag['title'] and flag['detail'])
                self.assertTrue(flag['source_urls'], 'a flag without a source link is not reviewable')
                self.assertTrue(set(flag['match_ids']) <= ids)
                for url in flag['source_urls']:
                    self.assertTrue(is_official(url), f'flag cites a non-official source: {url}')

    def test_a_stale_snapshot_is_reported(self):
        rows = [fixture_row('1', ['Aurora', '9z'], probabilities=[0.69, 0.31], method='market', pick=0)]
        result = run_audit(rows=rows, generated='2026-10-16T00:00:00Z', observed='2026-10-16T08:19:40Z')
        self.assertEqual(result['staleness']['verdict'], 'stale')
        self.assertTrue(any(f['id'].endswith('snapshot-stale') for f in result['flags']))

    def test_an_unofficial_cited_url_is_reported(self):
        rows = [fixture_row('1', ['Aurora', '9z'], probabilities=[0.69, 0.31], method='market',
                            pick=0, event_id='1', aliases=[{'alias': 'Aurora Gaming',
                                                            'canonical': 'Aurora'}])]
        rows[0]['aliases_used'][0]['evidence'] = [
            {'url': 'https://liquipedia.net/counterstrike/X', 'source': 'Liquipedia'}]
        result = run_audit(rows=rows)
        self.assertIn('https://liquipedia.net/counterstrike/X', result['source_links']['unofficial'])
        self.assertTrue(any(f['id'].endswith('unofficial-source-url') for f in result['flags']))


class CommandLine(unittest.TestCase):
    def test_main_writes_the_dossier_and_reports_a_summary(self):
        rows = [fixture_row('1080205', ['Aurora', '9z'], probabilities=[0.69346, 0.30654],
                            method='market', pick=0, event_id='1194512',
                            aliases=[{'alias': 'Aurora Gaming', 'canonical': 'Aurora'}])]
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / 'research'
            build_evidence(evidence, rows=rows, moneylines=[polymarket_line(
                '1194512', 'cs2-aur1-9z-2026-10-16', ['Aurora Gaming', '9z'], [0.695, 0.305])],
                books={'t1': clob_book([(0.69, 9)], [(0.70, 9)], 't1'),
                       't2': clob_book([(0.30, 9)], [(0.31, 9)], 't2')})
            flags_out = evidence / 'flags.json'
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['--evidence', str(evidence), '--flags-out', str(flags_out)])
            self.assertEqual(code, 0)
            written = json.loads((evidence / 'audit.json').read_text())
            self.assertEqual(written['session'], 'arena-ba7164a0')
            self.assertEqual(json.loads(flags_out.read_text()), written['flags'])
            self.assertIn('inventory reconciled=True', out.getvalue())
            self.assertIn('first-party market check', out.getvalue())

    def test_missing_evidence_produces_an_empty_audit_rather_than_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['--evidence', str(Path(tmp) / 'absent')])
            self.assertEqual(code, 0)
            written = json.loads((Path(tmp) / 'absent' / 'audit.json').read_text())
        self.assertEqual(written['probability_replay']['checked'], 0)
        self.assertEqual(written['inventory_reconciliation']['reconciled'], True)
        self.assertTrue(written['limitations'])


if __name__ == '__main__':
    unittest.main()
