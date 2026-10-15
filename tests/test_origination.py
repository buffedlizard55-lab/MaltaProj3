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
        row = {'names': ['WBT', 'ENCE'], 'bid': [0.57, 0.42], 'ask': [0.58, 0.43],
               'source_url': 'https://polymarket.com/event/x', 'event_id': '1', 'evidence_file': 'e.json'}
        quote, detail = originate.market_estimate(row, self.match(), registry(), datetime.now(UTC))
        self.assertAlmostEqual(quote['probabilities'][0], 0.575, places=4)
        self.assertFalse(quote['thin'])
        row['bid'], row['ask'] = [0.54, 0.17], [0.81, 0.32]
        quote, detail = originate.market_estimate(row, self.match(), registry(), datetime.now(UTC))
        self.assertIsNone(quote)
        self.assertIn('ceiling', detail)

    def test_market_estimate_rejects_spread_above_ceiling(self):
        row = {'names': ['WBT', 'ENCE'], 'bid': [0.5, 0.1], 'ask': [0.95, 0.5],
               'source_url': 'https://polymarket.com/event/x', 'event_id': '1', 'evidence_file': 'e.json'}
        quote, detail = originate.market_estimate(row, self.match(), registry(), datetime.now(UTC))
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
        quote, detail = originate.model_estimate(self.match(), ratings, registry(), meta, datetime.now(UTC))
        self.assertIsNotNone(quote)
        self.assertGreater(quote['probabilities'][0], 0.6)
        self.assertTrue(any(a['alias'] == 'WBT' for a in quote['aliases_used']))

    def test_model_estimate_rejects_incomplete_roster(self):
        ratings = [
            {'name': 'WBT', 'points': 1201, 'standing': 60, 'roster': ['a', 'b'], 'snapshot_date': '2026-10-05'},
            {'name': 'ENCE', 'points': 1025, 'standing': 105, 'roster': ['f', 'g', 'h', 'i', 'j'], 'snapshot_date': '2026-10-05'},
        ]
        meta = {'source_url': 'https://x', 'snapshot_date': '2026-10-05', 'evidence_file': 'v.json'}
        quote, detail = originate.model_estimate(self.match(), ratings, registry(), meta, datetime.now(UTC))
        self.assertIsNone(quote)
        self.assertIn('roster', detail)

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
