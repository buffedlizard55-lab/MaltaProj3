"""Session arena-46ade650 — Smarkets exchange board as an independent money source.

Contract under test
-------------------
* Only a fixture that binds on **both** team names and a start inside the
  60-second window may become a price row; one name, a renamed team or a shifted
  start is never a join.
* Smarkets quotes integer probabilities scaled by 10,000; the module converts
  them to 0-1 probabilities and keeps bid <= ask. A missing side is skipped, not
  defaulted.
* Every price row keeps the fixture id, the exchange event and market ids, the
  public event page and the saved evidence file, so the ladder (and
  ``build_origination.validate_origination``) can replay it.
* An unreachable exchange writes an error note and prices nothing: the
  four-hour refresh must never fail because a new research source is down.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import originate, smarkets_lines
from scripts.domain import iso

UTC = timezone.utc
# The collector stamps the live wall clock on its observation and the ladder
# enforces the prematch rule against it, so these tests derive both instants from
# the wall clock instead of pinning a date: a pinned date turns into a
# "future-dated observation" or a "post-start quote" as soon as it passes.
NOW = datetime.now(UTC).replace(microsecond=0)
START = (NOW + timedelta(hours=8)).isoformat().replace('+00:00', 'Z')
LOCK = (NOW + timedelta(hours=8) - timedelta(minutes=6)).isoformat().replace('+00:00', 'Z')


def fixture(*, names=('Ryvex', 'TitanFlow'), start=None, ident='999001'):
    return {'id': ident, 'availability': 'open',
            'teams': [{'id': '1', 'name': names[0]}, {'id': '2', 'name': names[1]}],
            'starts_at': start or START, 'locks_at': LOCK,
            'competition': 'CCT Europe 2026 Series #12',
            'source_url': 'https://www.hotspawn.com/matches/ryvex-vs-titanflow-999001'}


EVENT = {'id': '45396219', 'name': 'Ryvex vs TitanFlow', 'state': 'upcoming', 'bettable': True,
         'start_datetime': START, 'type': 'csgo_match',
         'full_slug': '/sport/esports/cs-go/cct-europe/2026/10/23/13-45/ryvex-vs-titanflow'}
MARKET = {'id': '172923329', 'event_id': '45396219', 'state': 'open', 'hidden': False,
          'market_type': {'name': 'WINNER_2_WAY'}}
CONTRACTS = [{'id': '477055180', 'market_id': '172923329', 'name': 'Ryvex', 'state_or_outcome': 'open',
              'contract_type': {'name': 'HOME'}},
             {'id': '477055181', 'market_id': '172923329', 'name': 'TitanFlow', 'state_or_outcome': 'open',
              'contract_type': {'name': 'AWAY'}}]
QUOTES = {'477055180': {'bids': [{'price': 4132, 'quantity': 100}], 'offers': [{'price': 5376, 'quantity': 100}]},
          '477055181': {'bids': [{'price': 4630, 'quantity': 100}], 'offers': [{'price': 5848, 'quantity': 100}]}}


class StubClient:
    def __init__(self, *, fail_events=False, quotes=QUOTES, market=MARKET):
        self.fail_events = fail_events
        self.quotes = quotes
        self.market = market
        self.calls = []

    def get_json(self, url, label, *, method='GET', payload=None, save=True, headers=None):
        self.calls.append(url)
        if 'events/?type=csgo_match' in url:
            if self.fail_events:
                raise RuntimeError('live-smarkets-events: HTTP 503')
            return {'events': [EVENT]}, {'observed_at': iso(NOW), 'status': 'ok'}
        if '/markets/' in url and 'contracts' in url:
            return {'contracts': CONTRACTS}, {'observed_at': iso(NOW), 'status': 'ok'}
        if '/quotes/' in url:
            return self.quotes, {'observed_at': iso(NOW), 'status': 'ok'}
        if url.endswith('/markets/'):
            return {'markets': [self.market]}, {'observed_at': iso(NOW), 'status': 'ok'}
        raise AssertionError('unexpected URL ' + url)


class JoinTests(unittest.TestCase):
    def test_both_names_and_the_start_window_are_required(self):
        self.assertTrue(smarkets_lines.binds(EVENT, fixture()))

    def test_one_shared_name_is_not_a_join(self):
        self.assertFalse(smarkets_lines.binds(EVENT, fixture(names=('Ryvex', 'Someone Else'))))

    def test_a_renamed_team_is_not_a_join(self):
        self.assertFalse(smarkets_lines.binds(EVENT, fixture(names=('Ryvex', 'Titan Flow'))))

    def test_a_shifted_start_is_not_a_join(self):
        shifted = (NOW + timedelta(hours=8, minutes=2)).isoformat().replace('+00:00', 'Z')
        inside = (NOW + timedelta(hours=8, seconds=30)).isoformat().replace('+00:00', 'Z')
        self.assertFalse(smarkets_lines.binds(EVENT, fixture(start=shifted)))
        # ... and the tolerance is the project-wide 60-second money window.
        self.assertTrue(smarkets_lines.binds(EVENT, fixture(start=inside)))
        self.assertEqual(smarkets_lines.START_TOLERANCE_SEC, 60)

    def test_event_url_is_a_public_page_not_an_api_url(self):
        self.assertEqual(smarkets_lines.event_url(EVENT),
                         'https://smarkets.com/sport/esports/cs-go/cct-europe/2026/10/23/13-45/ryvex-vs-titanflow')


class CollectTests(unittest.TestCase):
    def test_bound_fixture_is_saved_with_both_sides_and_its_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = smarkets_lines.collect(StubClient(), Path(tmp), [fixture()])
            self.assertEqual(summary['bound'], 1)
            saved = json.loads((Path(tmp) / smarkets_lines.EVIDENCE_NAME).read_text())
            self.assertEqual(saved['bindings'][0]['hotspawn_id'], '999001')
            self.assertEqual(saved['bindings'][0]['market_id'], '172923329')
            rows = smarkets_lines.rows(Path(tmp))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row['fixture_id'], '999001')
            self.assertEqual(row['provider'], 'Smarkets')
            self.assertEqual(row['bid'], [0.4132, 0.463])
            self.assertEqual(row['ask'], [0.5376, 0.5848])
            self.assertEqual(row['event_id'], '45396219')
            self.assertEqual(row['evidence_file'], 'data/origination/evidence/live-smarkets-cs.json')
            self.assertTrue(row['source_url'].startswith('https://smarkets.com/'))

    def test_prices_replay_through_the_ladder(self):
        with tempfile.TemporaryDirectory() as tmp:
            smarkets_lines.collect(StubClient(), Path(tmp), [fixture()])
            row = smarkets_lines.rows(Path(tmp))[0]
            quote, detail = originate.market_estimate(row, fixture(), {'aliases': []}, NOW)
            self.assertIsNotNone(quote, detail)
            self.assertTrue(quote['thin'])  # 12.4c spread is above the 0.12 thin line
            self.assertAlmostEqual(quote['probabilities'][0], (0.4754 / (0.4754 + 0.5239)), places=6)

    def test_one_sided_book_is_skipped_not_defaulted(self):
        quotes = {'477055180': {'bids': [{'price': 4132}], 'offers': [{'price': 5376}]},
                  '477055181': {'bids': [], 'offers': [{'price': 5848}]}}
        with tempfile.TemporaryDirectory() as tmp:
            smarkets_lines.collect(StubClient(quotes=quotes), Path(tmp), [fixture()])
            self.assertEqual(smarkets_lines.rows(Path(tmp)), [])

    def test_an_unreachable_exchange_writes_a_reason_and_no_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = smarkets_lines.collect(StubClient(fail_events=True), Path(tmp), [fixture()])
            self.assertIn('error', summary)
            self.assertEqual(smarkets_lines.rows(Path(tmp)), [])

    def test_an_ambiguous_market_is_not_priced(self):
        market = dict(MARKET, market_type={'name': 'MAP_WINNER'})
        with tempfile.TemporaryDirectory() as tmp:
            summary = smarkets_lines.collect(StubClient(market=market), Path(tmp), [fixture()])
            self.assertEqual(summary['bound'], 0)
            self.assertEqual(smarkets_lines.rows(Path(tmp)), [])

    def test_absent_evidence_loads_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(smarkets_lines.rows(Path(tmp)), [])


class OriginationTests(unittest.TestCase):
    def _originate(self, tmp, *, names=('Ryvex', 'TitanFlow')):
        rows = smarkets_lines.rows(Path(tmp))
        return originate.originate_match(fixture(names=names), rows, [], None, None, {'aliases': []}, NOW)

    def test_the_exchange_line_becomes_the_published_pick(self):
        with tempfile.TemporaryDirectory() as tmp:
            smarkets_lines.collect(StubClient(), Path(tmp), [fixture()])
            result = self._originate(tmp)
            o = result['origination']
            self.assertIsNotNone(o)
            self.assertEqual(o['method'], 'market')
            self.assertIn('Smarkets', o['label'])
            self.assertEqual(o['source'], 'Smarkets')
            # Ryvex 0.4754 mid vs TitanFlow 0.5239 mid: the exchange favours TitanFlow.
            self.assertEqual(result['pick_index'], 1)
            stages = [r['stage'] for r in result['research']]
            self.assertTrue(any(s.startswith('Exchange market (Smarkets') for s in stages))

    def test_a_row_for_another_fixture_is_never_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            smarkets_lines.collect(StubClient(), Path(tmp), [fixture()])
            result = self._originate(tmp, names=('Ryvex', 'Other Team'))
            self.assertIsNone(result['origination'])

    def test_a_wide_book_is_rejected_with_its_reason(self):
        quotes = {'477055180': {'bids': [{'price': 2000}], 'offers': [{'price': 8000}]},
                  '477055181': {'bids': [{'price': 2000}], 'offers': [{'price': 8000}]}}
        with tempfile.TemporaryDirectory() as tmp:
            smarkets_lines.collect(StubClient(quotes=quotes), Path(tmp), [fixture()])
            result = self._originate(tmp)
            market_rows = [r for r in result['research'] if r['stage'].startswith('Exchange market (Smarkets')]
            self.assertTrue(market_rows)
            self.assertEqual(market_rows[0]['status'], 'unresolved')
            self.assertIn('ceiling', market_rows[0]['detail'])


if __name__ == '__main__':
    unittest.main()
