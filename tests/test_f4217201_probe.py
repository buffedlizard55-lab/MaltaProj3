"""Offline tests for session arena-f4217201's live reconciliation probe.

No network: every parser is exercised on a saved-shape fixture so the runner job
is not the first time the code runs. The tests also pin the two things the
brief cares about most: an unreachable source is never turned into a price, and
a fixture with no published pick is always reported as uncovered rather than
silently dropped.
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from scripts import f4217201_probe as probe

UTC = timezone.utc
OBSERVED = '2026-10-24T08:00:00Z'


def api_row(match_id: str, team0: str, team1: str, start: str, tier: str = 'b') -> dict:
    epoch = int(datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC).timestamp() * 1000)
    return {'id': match_id, 'competition_name': 'CCT Europe 2026 Series #11',
            'scheduled_start_time': str(epoch), 'lock_time': str(epoch - 360000),
            'tier': tier, 'participants0_name': team0, 'participants1_name': team1}


LOBBY_HTML = '''
<a href="https://www.hotspawn.com/matches/acend-vs-forze-reload-cct-europe-2026-series-11-1079658">View Match</a>
<a href="https://www.hotspawn.com/matches/havu-vs-azuolas-cct-europe-2026-series-12-1081152">View Match</a>
<a href="https://www.hotspawn.com/matches/havu-vs-azuolas-cct-europe-2026-series-12-1081152">dup</a>
'''

EGW_HTML = '''
<a href="/counterstrike/match/abc/acend-vs-forze-reload-xyz">Acend vs FORZE Reload 1.85 1.95</a>
<a href="/counterstrike/match/def/havu-vs-azuolas-xyz">HAVU vs Azuolas 1.80 1.80</a>
'''

HLTV_HTML = '''
<div class="upcomingMatch">
  <div class="matchTeamName">Acend</div>
  <a href="/matches/2399502/acend-vs-forze-reload-cct-2026-europe-series-11">details</a>
  <div class="matchTeamName">FORZE Reload</div>
</div>
<div class="upcomingMatch">
  <div class="matchTeamName">Somebody</div>
  <div class="matchTeamName">Else</div>
</div>
'''

POLY_EVENTS = [{
    'title': 'Counter-Strike: HAVU vs Azuolas',
    'slug': 'cs2-havu-azu-2026-10-24',
    'volume': '0',
    'markets': [{'question': 'Will HAVU win?', 'outcomes': '["Yes", "No"]',
                 'outcomePrices': '["0.5", "0.5"]', 'volume': '0', 'closed': False}],
}, {
    'title': 'Counter-Strike: Acend vs FORZE Reload',
    'slug': 'cs2-acend-forzer-2026-10-24',
    'volume': '410',
    'markets': [{'question': 'Will Acend win?', 'outcomes': '["Yes", "No"]',
                 'outcomePrices': '["0.42", "0.58"]', 'volume': '410', 'closed': False}],
}]


class LobbyParsing(unittest.TestCase):
    def test_rendered_ids_are_deduplicated_and_only_hotspawn_match_links(self):
        self.assertEqual(probe.lobby_ids(LOBBY_HTML), ['1079658', '1081152'])

    def test_epoch_fields_become_utc_and_future_is_explicit(self):
        rows = probe.fixture_rows(json.dumps([api_row('1', 'Acend', 'FORZE Reload',
                                                     '2026-10-24T11:00:00Z')]),
                                  probe.parse_iso(OBSERVED))
        self.assertEqual(rows[0]['starts_at'], '2026-10-24T11:00:00Z')
        self.assertEqual(rows[0]['locks_at'], '2026-10-24T10:54:00Z')
        self.assertTrue(rows[0]['future'])

    def test_past_rows_are_not_counted_as_future(self):
        rows = probe.fixture_rows(json.dumps([api_row('1', 'A', 'B', '2026-10-24T07:59:00Z')]),
                                  probe.parse_iso(OBSERVED))
        self.assertFalse(rows[0]['future'])


class EgwJoin(unittest.TestCase):
    def test_two_sided_decimal_pair_is_found(self):
        hit = probe.egw_lookup(EGW_HTML, ['Acend', 'FORZE Reload'])
        self.assertIsNotNone(hit)
        self.assertEqual(hit['printed_odds'], [1.85, 1.95])
        self.assertFalse(hit['placeholder'])

    def test_identical_decimals_are_refused_as_placeholder(self):
        hit = probe.egw_lookup(EGW_HTML, ['HAVU', 'Azuolas'])
        self.assertTrue(hit['placeholder'])

    def test_single_team_slug_does_not_join(self):
        self.assertIsNone(probe.egw_lookup(EGW_HTML, ['Acend', 'Azuolas']))


class PolymarketJoin(unittest.TestCase):
    def test_event_naming_both_teams_is_found(self):
        hit = probe.poly_lookup(POLY_EVENTS, ['HAVU', 'Azuolas'])
        self.assertEqual(hit['url'], 'https://polymarket.com/event/cs2-havu-azu-2026-10-24')

    def test_unrelated_events_do_not_join(self):
        self.assertIsNone(probe.poly_lookup(POLY_EVENTS, ['Acend', 'Azuolas']))


class HltvIdentity(unittest.TestCase):
    def test_both_names_in_one_block_is_the_only_match(self):
        hit = probe.hltv_identity(HLTV_HTML, ['Acend', 'FORZE Reload'])
        self.assertTrue(hit['found'])
        self.assertIn('/matches/2399502/', hit['url'])

    def test_missing_html_is_reported_not_assumed(self):
        hit = probe.hltv_identity('', ['Acend', 'FORZE Reload'])
        self.assertFalse(hit['found'])
        self.assertIn('no HTML', hit['reason'])


class Reconciliation(unittest.TestCase):
    def published(self):
        return {
            'generated_at': '2026-10-23T20:00:00Z',
            'counts': {'upcoming': 1, 'picks': 1},
            'matches': [{
                'id': '1079658', 'teams': [{'name': 'Acend'}, {'name': 'FORZE Reload'}],
                'availability': 'open',
                'analysis': {'method': 'market', 'pick': 'FORZE Reload',
                             'probabilities': [0.17, 0.83],
                             'source_url': 'https://polymarket.com/event/example'},
            }],
        }

    def test_unpublished_fixture_is_uncovered_and_never_dropped(self):
        rows = probe.fixture_rows(json.dumps([
            api_row('1079658', 'Acend', 'FORZE Reload', '2026-10-24T11:00:00Z'),
            api_row('1081152', 'HAVU', 'Azuolas', '2026-10-24T11:00:00Z'),
        ]), probe.parse_iso(OBSERVED))
        rec = probe.build_reconciliation(rows, ['1079658', '1081152'], self.published(),
                                         {}, OBSERVED)
        self.assertEqual(rec['counts']['api_future'], 2)
        self.assertEqual(rec['counts']['snapshot_with_pick'], 1)
        self.assertEqual(rec['uncovered_ids'], ['1081152'])
        self.assertTrue(rec['snapshot']['stale_over_8h'])

    def test_snapshot_age_is_computed_from_the_published_stamp(self):
        rec = probe.build_reconciliation([], [], self.published(), {}, OBSERVED)
        self.assertEqual(rec['snapshot']['age_hours'], 12.0)
        self.assertTrue(rec['snapshot']['stale_over_8h'])

    def test_row_without_source_url_is_not_counted_as_a_pick(self):
        published = self.published()
        published['matches'][0]['analysis']['source_url'] = None
        rows = probe.fixture_rows(json.dumps([
            api_row('1079658', 'Acend', 'FORZE Reload', '2026-10-24T11:00:00Z')]),
            probe.parse_iso(OBSERVED))
        rec = probe.build_reconciliation(rows, [], published, {}, OBSERVED)
        self.assertEqual(rec['counts']['snapshot_with_pick'], 0)
        self.assertEqual(rec['uncovered_ids'], ['1079658'])


class ResearchVerdicts(unittest.TestCase):
    def reads(self) -> dict:
        return {
            'hltv': {'status': 'ok', 'http': 200, 'sha256': 'a', 'excerpt': 'listing'},
            'hltv_html': HLTV_HTML,
            'egw': {'status': 'ok', 'http': 200, 'sha256': 'b'},
            'egw_html': EGW_HTML,
            'poly': {'status': 'ok', 'http': 200, 'sha256': 'c'},
            'poly_events': POLY_EVENTS,
            'thunderpick': {'url': 'x', 'status': 'ok', 'http': 200},
        }

    def row(self, team0: str, team1: str) -> dict:
        return {'id': '1079658', 'teams': [team0, team1], 'competition': 'CCT',
                'starts_at': '2026-10-24T11:00:00Z'}

    def test_two_sided_book_line_is_the_only_line_verdict(self):
        out = probe.research_fixture(self.reads(), self.row('Acend', 'FORZE Reload'))
        self.assertEqual(out['verdict'], 'external-line-found')

    def test_placeholder_and_zero_volume_stay_unresolved(self):
        out = probe.research_fixture(self.reads(), self.row('HAVU', 'Azuolas'))
        self.assertEqual(out['verdict'], 'identity-confirmed-no-line'
                         if 'HAVU' in HLTV_HTML else out['verdict'])
        self.assertTrue(any('identical decimals' in x for x in out['limitations']))
        self.assertTrue(any('non-zero volume' in x for x in out['limitations']))
        probe_row = [p for p in out['probes'] if 'Polymarket' in p['source']][0]
        self.assertEqual(probe_row['status'], 'zero-volume-or-flat-book')

    def test_unknown_teams_keep_a_stated_limitation(self):
        out = probe.research_fixture(self.reads(), self.row('Nobody', 'Nowhere'))
        self.assertEqual(out['verdict'], 'no-source-found')
        self.assertTrue(out['limitations'])

    def test_blocked_sources_appear_in_flags(self):
        reads = self.reads()
        reads['egw'] = {'status': 'challenge', 'http': 403}
        reads['egw_html'] = ''
        out = probe.research_fixture(reads, self.row('Nobody', 'Nowhere'))
        flags = probe.flags_for({'observed_at': OBSERVED,
                                 'snapshot': {'stale_over_8h': True,
                                              'generated_at': '2026-10-23T20:00:00Z',
                                              'age_hours': 12.0},
                                 'counts': {'lobby_rendered': 25}},
                                {'fixtures': [out]})
        ids = {f['id'] for f in flags}
        # The publisher's review renderer reads source_urls; a flag without it
        # would crash scripts.build for every session's page.
        for finding in flags:
            self.assertTrue(finding['source_urls'])
            self.assertTrue(all(u.startswith('https://') for u in finding['source_urls']))
            self.assertIn('match_ids', finding)
        self.assertIn('f4217201-published-snapshot-older-than-eight-hours', ids)
        self.assertIn('f4217201-live-fixtures-without-a-published-pick', ids)
        self.assertIn('f4217201-line-source-blocks-this-sweep', ids)


class Policy(unittest.TestCase):
    def test_probe_never_writes_a_probability_or_a_pick(self):
        import pathlib
        source = pathlib.Path(probe.__file__).read_text(encoding='utf-8')
        # The probe may read a probability to report coverage, but it must not
        # contain an origination path, an alias writer or a snapshot writer.
        for forbidden in ('originate', 'aliases.json', "latest.json'", 'root_publish'):
            self.assertNotIn('import ' + forbidden, source)
        self.assertIn('originates a probability', source)


if __name__ == '__main__':
    unittest.main()
