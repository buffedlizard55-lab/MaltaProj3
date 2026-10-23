"""Session arena-7c0e457b — a sourced line for every fixture, and the near-time class.

Contract under test
-------------------
* Unibet's public offering feed is read as a first-party bookmaker source: one
  brand only (so one Kambi liquidity pool is not counted twice), one two-way
  ``Match Odds`` offer per fixture, both sides open, both decimal prices above
  1.01, and never an in-play or started event.
* The near-time class is narrow by construction: it needs the project's own
  ``pair_join`` to have matched **both names** (via the reviewed alias registry),
  the difference to be outside the 60-second strict window, at most six hours,
  and both instants on the same UTC date. Everything else is rejected.
* A near-time row is a real price, so it outranks the aggregated third-party
  average and every research model, but it never outranks an exact-bound quote,
  and both timestamps are published on the row.
* Nothing in this session writes a probability by hand: the ladder, the replay
  and these tests all derive the numbers from the saved provider responses.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import gap_lines, kambi_lines, originate
from scripts.domain import iso, no_vig, normalize_pair

UTC = timezone.utc
# Wall-clock relative, like every other live-source test in this repository: a
# pinned calendar date turns into a stale/future observation once it passes.
NOW = datetime.now(UTC).replace(microsecond=0)
START = (NOW + timedelta(hours=9)).replace(second=0).isoformat().replace('+00:00', 'Z')
LOCK = (NOW + timedelta(hours=9) - timedelta(minutes=6)).replace(second=0).isoformat().replace('+00:00', 'Z')
NAMES = ('Metizport', 'BakS')
# The real reviewed registry: Polymarket prints "BakS eSports" for this fixture and
# Hotspawn prints "BakS", which is exactly the join the registry is scoped to solve.
REGISTRY = json.loads((Path(__file__).resolve().parents[1] / 'data/origination/aliases.json').read_text())


def fixture(*, names=NAMES, start=None, ident='1082001', competition='NODWIN Clutch Series #13'):
    return {'id': ident, 'availability': 'open',
            'teams': [{'id': '1', 'name': names[0]}, {'id': '2', 'name': names[1]}],
            'starts_at': start or START, 'locks_at': LOCK, 'competition': competition,
            'source_url': 'https://www.hotspawn.com/matches/metizport-vs-baks-1082001'}


def shifted(seconds: int) -> str:
    return (datetime.fromisoformat(START.replace('Z', '+00:00'))
            + timedelta(seconds=seconds)).isoformat().replace('+00:00', 'Z')


def kambi_event(*, start=None, home='Metizport', away='BakS', odds=(1680, 2180),
                state='NOT_STARTED', sport='COUNTER_STRIKE', offers=1, status='OPEN'):
    outcomes = [{'type': 'OT_ONE', 'label': home, 'odds': odds[0], 'status': status,
                 'changedDate': '2026-10-23T08:00:00Z'},
                {'type': 'OT_TWO', 'label': away, 'odds': odds[1], 'status': status,
                 'changedDate': '2026-10-23T08:00:00Z'}]
    return {'event': {'id': 1029588001, 'name': f'{home} - {away}', 'homeName': home, 'awayName': away,
                      'start': start or START, 'group': 'CCT European Series 12', 'state': state,
                      'sport': sport,
                      'path': [{'name': 'Esports', 'termKey': 'esports'},
                               {'name': 'CS2', 'termKey': 'cs2'},
                               {'name': 'CCT European Series 12', 'termKey': 'cct_european_series_12'}]},
            'betOffers': [{'id': 2707307799, 'criterion': {'englishLabel': 'Match Odds'},
                           'betOfferType': {'name': 'Match'}, 'outcomes': outcomes}
                          for _ in range(offers)]}


class StubClient:
    """Minimal ``originate.Collector`` stand-in: records URLs, saves the body."""

    def __init__(self, events, *, fail=False):
        self.events = events
        self.fail = fail
        self.calls = []

    def get_json(self, url, label, *, method='GET', payload=None, save=True, headers=None):
        self.calls.append(url)
        if self.fail:
            raise RuntimeError(label + ': HTTP 403')
        if 'listView' not in url:
            raise AssertionError('unexpected URL ' + url)
        return {'events': self.events}, {'observed_at': iso(NOW), 'status': 'ok'}


class KambiFeedTests(unittest.TestCase):
    def test_the_feed_url_is_the_operator_offering_endpoint(self):
        url = kambi_lines.feed_url()
        self.assertTrue(url.startswith('https://eu.offering-api.kambicdn.com/offering/v2018/ub/'))
        self.assertIn('listView/esports', url)

    def test_the_public_link_is_the_operator_page_not_the_json_feed(self):
        url = kambi_lines.event_url(1029588001)
        self.assertTrue(url.startswith('https://www.unibet.co.uk/betting/sports/event/'))
        self.assertNotIn('kambicdn', url)

    def test_one_two_way_match_odds_offer_is_read_in_thousandths(self):
        offer = kambi_lines.series_offer(kambi_event(odds=(1680, 2180)))
        self.assertIsNotNone(offer)
        self.assertEqual(offer['names'], ['Metizport', 'BakS'])
        self.assertEqual(offer['odds'], [1.68, 2.18])

    def test_a_suspended_side_is_not_a_price(self):
        self.assertIsNone(kambi_lines.series_offer(kambi_event(status='SUSPENDED')))

    def test_two_match_odds_offers_are_ambiguous_and_rejected(self):
        self.assertIsNone(kambi_lines.series_offer(kambi_event(offers=2)))

    def test_below_1_01_is_not_a_decimal_price(self):
        self.assertIsNone(kambi_lines.series_offer(kambi_event(odds=(1000, 2180))))

    def test_only_counter_strike_is_read(self):
        self.assertTrue(kambi_lines.is_cs2(kambi_event()))
        self.assertFalse(kambi_lines.is_cs2(kambi_event(sport='DOTA')))

    def test_collect_saves_the_offer_and_the_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = kambi_lines.collect(StubClient([kambi_event()]), Path(tmp))
            self.assertEqual(summary['events'], 1)
            self.assertEqual(summary['priced'], 1)
            saved = json.loads((Path(tmp) / kambi_lines.EVIDENCE_NAME).read_text())
            self.assertEqual(saved['provider'], 'Unibet (Kambi)')
            self.assertEqual(saved['events'][0]['event_id'], '1029588001')
            self.assertEqual(saved['events'][0]['offer']['odds'], [1.68, 2.18])

    def test_a_failed_feed_records_a_reason_and_prices_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = kambi_lines.collect(StubClient([], fail=True), Path(tmp))
            self.assertIn('error', summary)
            self.assertEqual(kambi_lines.rows(Path(tmp)), [])


class KambiRowsTests(unittest.TestCase):
    def _saved(self, tmp, **kwargs):
        kambi_lines.collect(StubClient([kambi_event(**kwargs)]), Path(tmp))
        return kambi_lines.rows(Path(tmp))

    def test_row_keeps_identity_prices_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = self._saved(tmp)[0]
            self.assertEqual(row['provider'], 'Unibet (Kambi)')
            self.assertEqual(row['family'], 'bookmaker')
            self.assertEqual(row['names'], ['Metizport', 'BakS'])
            self.assertEqual(row['odds'], [1.68, 2.18])
            self.assertEqual(row['event_id'], '1029588001')
            self.assertEqual(row['start'], START)
            self.assertTrue(row['source_url'].startswith('https://www.unibet.co.uk/'))
            self.assertEqual(row['evidence_file'], 'data/origination/evidence/live-kambi-cs2.json')
            self.assertEqual(row['observed_at'], iso(NOW))

    def test_absent_evidence_is_not_a_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(kambi_lines.rows(Path(tmp)), [])

    def test_the_quote_replays_through_the_shared_bookmaker_estimator(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = self._saved(tmp)[0]
            quote, detail = originate.bookmaker_estimate(row, fixture(), {'aliases': []}, now=NOW)
            self.assertIsNotNone(quote, detail)
            expected = normalize_pair(*no_vig([1.68, 2.18]))
            self.assertAlmostEqual(quote['probabilities'][0], expected[0], places=9)
            self.assertLess(quote['probabilities'][0], 0.6)


class NearTimeClassTests(unittest.TestCase):
    def join(self, match):
        return lambda names, start: originate.pair_join(names, start, match, {'aliases': []})

    def row(self, *, names=NAMES, start=None, family='bookmaker', provider='Unibet (Kambi)'):
        base = {'provider': provider, 'family': family, 'names': list(names), 'start': start or START}
        if family == 'market':
            base.update({'bid': [0.5, 0.4], 'ask': [0.54, 0.44]})
        else:
            base.update({'odds': [1.68, 2.18]})
        return base

    def test_exact_window_is_exact_not_near(self):
        match = fixture()
        for offset in (0, 30, 60, -60):
            status, _, _ = gap_lines.classify(self.row(start=shifted(offset)), match, self.join(match))
            self.assertEqual(status, 'exact', offset)

    def test_a_small_clock_difference_is_near_time(self):
        match = fixture()
        for offset in (61, 600, 3600, -7200):
            status, delta, _ = gap_lines.classify(self.row(start=shifted(offset)), match, self.join(match))
            self.assertEqual(status, 'near', offset)
            self.assertEqual(int(delta), offset)

    def test_more_than_six_hours_is_a_different_fixture(self):
        match = fixture()
        status, _, _ = gap_lines.classify(self.row(start=shifted(6 * 3600 + 1)), match, self.join(match))
        self.assertEqual(status, 'reject')
        status, _, _ = gap_lines.classify(self.row(start=shifted(-6 * 3600 - 1)), match, self.join(match))
        self.assertEqual(status, 'reject')

    def test_a_different_utc_date_is_rejected_even_inside_the_window(self):
        # 23:30Z fixture, provider says 00:10Z the next day: 40 minutes apart but a
        # different UTC date, which is how a postponement looks. Never a join.
        late = (NOW + timedelta(days=1)).replace(hour=23, minute=30, second=0)
        match = fixture(start=iso(late))
        provider = iso(late + timedelta(minutes=40))
        status, _, _ = gap_lines.classify(self.row(start=provider), match, self.join(match))
        self.assertEqual(status, 'reject')

    def test_one_renamed_team_is_rejected(self):
        match = fixture()
        status, _, _ = gap_lines.classify(self.row(names=('Metizport', 'BakS eSports'),
                                                   start=shifted(3600)), match, self.join(match))
        self.assertEqual(status, 'reject')

    def test_a_swapped_pair_is_still_the_same_two_teams(self):
        match = fixture()
        status, delta, _ = gap_lines.classify(self.row(names=('BakS', 'Metizport'), start=shifted(600)),
                                              match, self.join(match))
        self.assertEqual(status, 'near')
        self.assertEqual(int(delta), 600)

    def test_the_reason_sentence_publishes_both_clocks(self):
        match = fixture()
        row = gap_lines.annotate(self.row(start=shifted(3600)), match, 3600)
        text = gap_lines.near_reason(row, match, 3600)
        self.assertIn('60 minutes', text)
        self.assertIn(START, text)
        self.assertIn('same UTC date', text)


class NearTimeLadderTests(unittest.TestCase):
    def _near_rows(self, tmp, *, start, names=NAMES, odds=(1680, 2180), fixture_id=None):
        kambi_lines.collect(StubClient([kambi_event(start=start, home=names[0], away=names[1],
                                                    odds=odds)]), Path(tmp))
        rows = kambi_lines.rows(Path(tmp))
        match = fixture()
        out = []
        for row in rows:
            if fixture_id:
                row['fixture_id'] = fixture_id
            candidate = gap_lines.qualifies(row, match, lambda n, s: originate.pair_join(n, s, match, {'aliases': []}))
            if candidate:
                out.append(candidate)
        return out

    def test_a_near_time_book_becomes_the_pick_with_its_disagreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            near = self._near_rows(tmp, start=shifted(600))
            self.assertEqual(len(near), 1)
            result = originate.originate_match(fixture(), [], [], None, None, {'aliases': []}, NOW, near=near)
            o = result['origination']
            self.assertIsNotNone(o)
            self.assertEqual(o['method'], 'bookmaker')
            self.assertEqual(o['binding'], 'near-time')
            self.assertEqual(o['start_delta_sec'], 600)
            self.assertEqual(o['source'], 'Unibet (Kambi)')
            self.assertEqual(o['provider_start'], shifted(600))
            self.assertEqual(o['hotspawn_start'], START)
            self.assertTrue(any('Near-time external line' in x for x in result['limitations']))
            stages = [r for r in result['research'] if r['stage'].startswith('Near-time external line')]
            self.assertEqual(len(stages), 1)
            self.assertEqual(stages[0]['status'], 'resolved')
            self.assertIn('10 minutes', stages[0]['detail'])

    def test_an_exact_quote_outranks_the_near_time_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            near = self._near_rows(tmp, start=shifted(600))
            exact = {'provider': 'Thunderpick', 'family': 'bookmaker', 'names': list(NAMES), 'start': START,
                     'odds': [1.5, 2.6], 'event_id': 'e1', 'market_id': 'm1',
                     'source_url': 'https://thunderpick.io/match/1', 'observed_at': iso(NOW),
                     'evidence_file': 'data/origination/evidence/live-thunderpick-matches.json'}
            result = originate.originate_match(fixture(), [], [exact], None, None, {'aliases': []}, NOW, near=near)
            o = result['origination']
            self.assertEqual(o['source'], 'Thunderpick')
            self.assertNotIn('binding', o)
            stage = [r for r in result['research'] if r['stage'].startswith('Near-time external line')][0]
            self.assertEqual(stage['status'], 'not needed')

    def test_a_near_time_line_outranks_the_aggregated_reference_and_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            near = self._near_rows(tmp, start=shifted(-3600))
            result = originate.originate_match(fixture(), [], [], None, None, {'aliases': []}, NOW, near=near)
            self.assertEqual(result['origination']['method'], 'bookmaker')
            self.assertEqual(result['origination']['start_delta_sec'], -3600)

    def test_two_near_time_rows_from_one_provider_are_ambiguous_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            near = self._near_rows(tmp, start=shifted(600))
            duplicate = dict(near[0], event_id='other')
            result = originate.originate_match(fixture(), [], [], None, None, {'aliases': []}, NOW,
                                               near=near + [duplicate])
            self.assertIsNone(result['origination'])
            stage = [r for r in result['research'] if r['stage'].startswith('Near-time external line')][0]
            self.assertEqual(stage['status'], 'unresolved')
            self.assertIn('ambiguous', stage['detail'])

    def test_a_row_bound_to_another_fixture_is_never_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            near = self._near_rows(tmp, start=shifted(600), fixture_id='999999')
            result = originate.originate_match(fixture(), [], [], None, None, {'aliases': []}, NOW, near=near)
            self.assertIsNone(result['origination'])


class PolymarketNearCandidateTests(unittest.TestCase):
    def join(self, match):
        return lambda names, start: originate.pair_join(names, start, match, REGISTRY)

    def event(self, *, question='Counter-Strike: Metizport vs BakS eSports', started=None,
              active=True, closed=False, scope='moneyline', start=None):
        return {'id': '1238705', 'slug': 'cs2-mzp-baks-2026-10-25', 'active': active, 'closed': closed,
                'markets': [{'id': '6072797', 'question': question, 'outcomes': ['Metizport', 'BakS eSports'],
                             'gameStartTime': start or START, 'sportsMarketType': scope,
                             'active': active, 'closed': closed, 'acceptingOrders': True,
                             'clobTokenIds': '["1", "2"]'}]}

    def test_a_near_time_series_market_is_selected_with_its_delta(self):
        match = fixture()
        market, reason, delta = gap_lines.polymarket_near_candidate(self.event(start=shifted(3600)), match,
                                                                    self.join(match), NOW)
        self.assertIsNotNone(market, reason)
        self.assertEqual(int(delta), 3600)

    def test_a_map_winner_is_never_a_series_price(self):
        match = fixture()
        market, _, _ = gap_lines.polymarket_near_candidate(
            self.event(start=shifted(3600), question='Counter-Strike: Metizport vs BakS - Map 1 Winner'),
            match, self.join(match), NOW)
        self.assertIsNone(market)

    def test_a_non_cs2_slug_is_rejected(self):
        match = fixture()
        event = dict(self.event(start=shifted(3600)), slug='will-faze-win-a-tier-1-event-in-2026')
        market, _, _ = gap_lines.polymarket_near_candidate(event, match, self.join(match), NOW)
        self.assertIsNone(market)

    def test_an_exact_start_is_not_a_near_time_candidate(self):
        match = fixture()
        market, _, _ = gap_lines.polymarket_near_candidate(self.event(start=START), match, self.join(match), NOW)
        self.assertIsNone(market)

    def test_saved_near_books_rebuild_into_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            gap_lines.save_polymarket_near(Path(tmp), {'schema_version': 1, 'events': [{
                'fixture_id': '1082001', 'event_id': '1238705', 'slug': 'cs2-mzp-baks-2026-10-25',
                'public_page': 'https://polymarket.com/event/cs2-mzp-baks-2026-10-25',
                'outcomes': ['Metizport', 'BakS eSports'], 'game_start_time': shifted(3600),
                'observed_at': iso(NOW), 'book_bid': [0.62, 0.34], 'book_ask': [0.66, 0.38],
                'start_delta_sec': 3600, 'moneyline_market_id': '6072800'}]})
            rows = gap_lines.polymarket_near_rows(Path(tmp))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['binding'], 'near-time')
            self.assertEqual(rows[0]['fixture_id'], '1082001')
            quote, detail = originate.market_estimate(rows[0], fixture(), REGISTRY, NOW)
            self.assertIsNotNone(quote, detail)
            self.assertAlmostEqual(quote['probabilities'][0], 0.64 / (0.64 + 0.36), places=6)


class NearCandidateAssemblyTests(unittest.TestCase):
    def test_near_candidates_include_every_saved_money_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            kambi_lines.collect(StubClient([kambi_event()]), Path(tmp))
            rows = originate.near_candidate_rows(Path(tmp))
            self.assertEqual([r['provider'] for r in rows], ['Unibet (Kambi)'])

    def test_exact_kambi_rows_are_also_available_to_the_strict_ladder(self):
        with tempfile.TemporaryDirectory() as tmp:
            kambi_lines.collect(StubClient([kambi_event()]), Path(tmp))
            rows = originate.kambi_rows(Path(tmp))
            self.assertEqual(len(rows), 1)
            quote, detail = originate.bookmaker_estimate(rows[0], fixture(), {'aliases': []}, now=NOW)
            self.assertIsNotNone(quote, detail)


if __name__ == '__main__':
    unittest.main()
