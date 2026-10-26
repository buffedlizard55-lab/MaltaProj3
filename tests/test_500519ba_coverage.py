"""Tests for session 500519ba's live coverage audit (scripts/500519ba_audit.py).

The audit runs on a runner because the sandbox cannot reach the sources.  These
tests pin the parts that decide what a reader is told, using fixtures only: no
network call is made, and no probability is ever computed here — the audit
reports what `scripts/originate.py` published and nothing else.
"""
import importlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

audit = importlib.import_module('scripts.500519ba_audit')

UTC = timezone.utc


def fixture_row(fid, name_a, name_b, start_ms='1793088000000'):
    return {
        'id': fid, 'competition_name': 'CCT Europe 2026 Series #12', 'competition_id': '35500',
        'participants0_id': '1', 'participants0_name': name_a,
        'participants1_id': '2', 'participants1_name': name_b,
        'scheduled_start_time': start_ms, 'lock_time': '1782469440000',
        'tier': 'b', 'status': 'scheduled', 'best_of': None, 'sport_alias': 'cs2',
    }


def origination_row(fid, names, pick_index, probabilities, method='bookmaker', source='Thunderpick'):
    return {
        'id': fid, 'teams': [{'id': str(i), 'name': name} for i, name in enumerate(names)],
        'origination': {
            'method': method, 'label': 'No-vig bookmaker estimate',
            'probabilities': probabilities, 'source': source,
            'source_url': 'https://thunderpick.io/api/matches',
            'observed_at': '2026-10-26T00:00:00Z', 'limitations': ['single source'],
        },
        'pick_index': pick_index, 'featured_method': 'bookmaker',
        'aliases_used': [], 'limitations': [], 'research': [],
    }


class EpochAndInventoryTests(unittest.TestCase):
    def test_millisecond_epoch_is_converted_to_utc(self):
        self.assertEqual(audit.iso('1782469800000'), '2026-06-26T10:30:00Z')

    def test_missing_or_garbage_epoch_is_none(self):
        self.assertIsNone(audit.iso(None))
        self.assertIsNone(audit.iso('not-a-time'))

    def test_only_future_scheduled_rows_are_open(self):
        now = datetime(2026, 10, 26, 0, 0, tzinfo=UTC)
        rows = [
            fixture_row('1', 'A', 'B', '1793088000000'),   # 2026-10-27, future
            fixture_row('2', 'C', 'D', '1782469800000'),   # 2026-06-26, past
        ]
        open_ids = [row['id'] for row in audit.open_rows(rows, now)]
        self.assertEqual(open_ids, ['1'])

    def test_open_rows_sort_by_start_then_id(self):
        now = datetime(2026, 10, 26, 0, 0, tzinfo=UTC)
        rows = [
            fixture_row('9', 'A', 'B', '1793437200000'),   # 2026-10-31
            fixture_row('8', 'C', 'D', '1793088000000'),   # 2026-10-27
        ]
        self.assertEqual([row['id'] for row in audit.open_rows(rows, now)], ['8', '9'])

    def test_cs2_rows_drop_other_sports(self):
        rows = [{'sport_alias': 'cs2', 'id': '1'}, {'sport_alias': 'lol', 'id': '2'}]
        self.assertEqual([row['id'] for row in audit.cs2_rows(rows)], ['1'])

    def test_cs2_rows_of_a_non_array_payload_is_empty_not_a_crash(self):
        # A challenge page or an API error is not an inventory.
        self.assertEqual(audit.cs2_rows({'detail': 'forbidden'}), [])

    def test_lobby_ids_come_from_rendered_permalinks(self):
        html = ('<a href="/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858">'
                '<a href="https://play.hotspawn.com/cs2-pickems#fixture-1082859">')
        self.assertEqual(audit.lobby_ids(html), ['1082858'])

    def test_lobby_ids_of_an_unreadable_page_is_empty(self):
        self.assertEqual(audit.lobby_ids(None), [])
        self.assertEqual(audit.lobby_ids('<html>403</html>'), [])


class PickReportingTests(unittest.TestCase):
    def test_pick_is_the_named_side_and_probabilities_are_one_decimal_percent(self):
        summary = audit.pick_summary(
            origination_row('1081159', ['LFO 10', 'ex-6666'], 0, [0.57519789, 0.42480211]))
        self.assertTrue(summary['present'])
        self.assertEqual(summary['pick'], 'LFO 10')
        self.assertEqual(summary['opponent'], 'ex-6666')
        self.assertEqual(summary['probabilities'], [57.5, 42.5])
        self.assertEqual(summary['method'], 'bookmaker')
        self.assertEqual(summary['source_url'], 'https://thunderpick.io/api/matches')

    def test_pick_of_the_second_side_is_reported_as_that_side(self):
        summary = audit.pick_summary(
            origination_row('1081163', ['BakS', 'Saint Sinners'], 1, [0.3, 0.7]))
        self.assertEqual(summary['pick'], 'Saint Sinners')
        self.assertEqual(summary['probabilities'], [30.0, 70.0])

    def test_a_fixture_absent_from_the_ladder_is_unpicked_and_carries_no_number(self):
        summary = audit.pick_summary(None)
        self.assertFalse(summary['present'])
        self.assertIsNone(summary['pick'])
        self.assertIsNone(summary['probabilities'])

    def test_an_even_estimate_has_probabilities_but_no_pick(self):
        summary = audit.pick_summary(
            origination_row('1081160', ['HAVU', 'ILLYRIANS'], None, [0.5, 0.5], method='model'))
        self.assertIsNone(summary['pick'])
        self.assertEqual(summary['probabilities'], [50.0, 50.0])

    def test_deployed_row_is_matched_by_string_id(self):
        snapshot = {'matches': [{
            'id': 1081159, 'teams': [{'name': 'LFO 10'}, {'name': 'ex-6666'}],
            'availability': 'open', 'pick_index': 1,
            'analysis': {'method': 'market', 'source': 'Polymarket',
                         'source_url': 'https://polymarket.com/event/x',
                         'probabilities': [0.25, 0.75]},
        }]}
        summary = audit.deployed_summary(snapshot, '1081159')
        self.assertTrue(summary['present'])
        self.assertEqual(summary['pick'], 'ex-6666')
        self.assertEqual(summary['probabilities'], [25.0, 75.0])

    def test_deployed_row_missing_is_reported_as_missing(self):
        self.assertEqual(audit.deployed_summary({'matches': []}, '1'), {'present': False})
        self.assertEqual(audit.deployed_summary(None, '1'), {'present': False})


class RenderTests(unittest.TestCase):
    def report(self):
        picked = {
            **audit.fixture_record(fixture_row('1081159', 'LFO 10', 'ex-6666')),
            'fresh_collected': True,
            'fresh_snapshot_availability': 'open',
            'fresh_ladder': audit.pick_summary(
                origination_row('1081159', ['LFO 10', 'ex-6666'], 0, [0.6, 0.4])),
            'deployed': {'present': False},
            'gap_vs_deployed': True,
        }
        blank = {
            **audit.fixture_record(fixture_row('1093218', 'Nuclear TigeRES', 'UNiTY',
                                               '1790000000000')),
            'fresh_collected': True,
            'fresh_snapshot_availability': 'open',
            'fresh_ladder': {**audit.pick_summary(None),
                             'limitations': ['No alias-verified Thunderpick match-winner line found.'],
                             'trail': [{'stage': 'Primary: Polymarket', 'status': 'unresolved',
                                        'source_url': 'https://polymarket.com/esports/cs2',
                                        'detail': 'No unique exact-name fixture.'}],
                             'independent_sources': {'hltv_matches_answered': True}},
            'deployed': {'present': True, 'pick': None},
            'gap_vs_deployed': False,
        }
        return {
            'session': 'arena-500519ba', 'observed_at': '2026-10-26T01:00:00Z', 'policy': audit.POLICY,
            'sources': {'fixtures_api': {'status': 200, 'ok': True, 'error': None, 'bytes': 10,
                                         'sha256': 'a' * 64, 'observed_at': '2026-10-26T01:00:00Z',
                                         'cache': {}, 'url': audit.FIXTURES_API}},
            'counts': {'api_records': 81, 'api_records_cache_busted': 81, 'api_read_used': 'cache_busted',
                       'lobby_linked_fixtures': 81, 'cs2_lobby_linked_fixtures': 81, 'live_open': 2,
                       'fresh_ladder_picked': 1, 'fresh_ladder_unpicked': 1,
                       'deployed_snapshot_present': 1, 'deployed_snapshot_missing': 1,
                       'deployed_snapshot_unpicked': 1},
            'fixtures': [picked, blank],
            'unpicked': [{'id': blank['id'], 'teams': blank['teams'], 'starts_at': blank['starts_at'],
                          'competition': blank['competition'], 'tier': blank['tier'],
                          'limitations': blank['fresh_ladder']['limitations'],
                          'trail': blank['fresh_ladder']['trail'],
                          'independent_sources': {'hltv_matches_answered': True},
                          'deployed': blank['deployed']}],
            'gaps_vs_deployed': ['1081159'],
            'fresh_snapshot_generated_at': '2026-10-26T01:00:00Z',
            'fresh_origination_generated_at': '2026-10-26T01:01:00Z',
            'deployed_snapshot_generated_at': '2026-10-25T23:03:48Z',
            'deployed_counts': {'inventory': 72},
            'hltv_ranking_rows': 30,
            'lobby_page_ids_not_in_api': [], 'api_ids_not_linked_by_lobby': [],
        }

    def test_every_fixture_gets_a_row_and_a_pick_or_an_explicit_blank(self):
        markdown = audit.render_markdown(self.report())
        self.assertIn('LFO 10 vs ex-6666', markdown)
        self.assertIn('Nuclear TigeRES vs UNiTY', markdown)
        self.assertIn('**unresolved**', markdown)
        self.assertIn('No alias-verified Thunderpick match-winner line found.', markdown)

    def test_the_summary_counts_reconcile_with_the_rows(self):
        summary = audit.render_summary(self.report())
        self.assertIn('live_open=2 picked=1 unpicked=1', summary)
        self.assertIn('missing=1', summary)

    def test_a_blank_row_never_renders_a_probability(self):
        summary = audit.render_summary(self.report())
        for line in summary.splitlines():
            if line.startswith('fixture 1093218'):
                self.assertIn('UNPICKED', line)
                self.assertNotIn('%', line)

    def test_gap_ids_are_named_not_just_counted(self):
        self.assertIn('1081159', audit.render_markdown(self.report()))

    def test_policy_states_the_read_only_rule(self):
        self.assertIn('No probability, pick or alias is written here', audit.POLICY)
        self.assertIn(audit.POLICY, audit.render_markdown(self.report()))


class LiveCoverageRecordTests(unittest.TestCase):
    """The record the executive summary's lobby register renders must be honest."""

    def report_with(self, carried_pick, carried_blank, absent):
        def block(record, pick_summary):
            return {**record, 'fresh_ladder': pick_summary,
                    'fresh_collected': record['id'] in carried_pick + carried_blank}
        picked = block(audit.fixture_record(fixture_row('1081159', 'LFO 10', 'ex-6666')),
                       audit.pick_summary(origination_row('1081159', ['LFO 10', 'ex-6666'], 0, [0.6, 0.4])))
        blank = block(audit.fixture_record(fixture_row('1093218', 'Nuclear TigeRES', 'UNiTY')),
                      audit.pick_summary(None))
        missing = block(audit.fixture_record(fixture_row('1079201', 'INOX Division', 'Nemesis')),
                        audit.pick_summary(None))
        return {'session': 'arena-500519ba', 'observed_at': '2026-10-26T01:00:00Z',
                'fixtures': [picked, blank, missing]}

    def test_a_fixture_this_run_did_not_collect_is_named_as_missing(self):
        report = self.report_with(['1081159'], ['1093218'], ['1079201'])
        record = audit.live_coverage_record(
            report,
            {'1079201': 'https://www.hotspawn.com/matches/inox-division-vs-nemesis-nodwin-clutch-series-13-1079201'},
            {'1081159': {}, '1093218': {}}, {'1081159': {}, '1093218': {}})
        by_id = {fixture['id']: fixture for fixture in record['live_fixtures']}
        self.assertTrue(by_id['1081159']['in_published_snapshot'])
        self.assertTrue(by_id['1093218']['in_published_snapshot'])
        self.assertFalse(by_id['1079201']['in_published_snapshot'])
        self.assertEqual(record['counts']['missing_from_build'], 1)
        self.assertEqual(record['counts']['carried_in_build'], 2)
        self.assertIn('scheduled after the collect', by_id['1079201']['note'])
        self.assertIsNone(by_id['1079201']['hltv_url'])

    def test_a_carried_but_unpriced_fixture_is_not_called_a_gap(self):
        report = self.report_with(['1081159'], ['1093218'], [])
        record = audit.live_coverage_record(report, {}, {'1081159': {}, '1093218': {}},
                                            {'1081159': {}, '1093218': {}})
        by_id = {fixture['id']: fixture for fixture in record['live_fixtures']}
        self.assertTrue(by_id['1093218']['in_published_snapshot'])
        self.assertFalse(by_id['1093218']['in_featured_resolved'])
        self.assertIn('unresolved register', by_id['1093218']['note'])

    def test_the_record_never_carries_a_probability(self):
        report = self.report_with(['1081159'], ['1093218'], ['1079201'])
        record = audit.live_coverage_record(report, {}, {'1081159': {}}, {'1081159': {}})
        self.assertNotIn('probabilities', json.dumps(record))
        self.assertNotIn('%"', json.dumps(record))

    def test_the_markdown_names_each_missing_fixture(self):
        report = self.report_with(['1081159'], ['1093218'], ['1079201'])
        record = audit.live_coverage_record(report, {}, {'1081159': {}}, {'1081159': {}})
        markdown = audit.render_live_coverage(record)
        self.assertIn('INOX Division vs Nemesis', markdown)
        self.assertIn('**no**', markdown)

    def test_lobby_links_map_the_permalink_to_its_id(self):
        html = ('<a href="https://www.hotspawn.com/matches/baks-vs-saint-sinners-cct-europe-2026-series-12-1081163">'
                '<a href="https://www.hotspawn.com/matches/x-1081164">')
        links = audit.lobby_links(html)
        self.assertEqual(links['1081163'],
                         'https://www.hotspawn.com/matches/baks-vs-saint-sinners-cct-europe-2026-series-12-1081163')
        self.assertEqual(links['1081164'], 'https://www.hotspawn.com/matches/x-1081164')
        self.assertEqual(audit.lobby_links(None), {})


class RepoIntegrationTests(unittest.TestCase):
    """The audit's own source files exist where the workflow expects them."""

    def test_workflow_and_module_are_tracked(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / 'scripts' / '500519ba_audit.py').exists())
        self.assertTrue((root / '.github' / 'workflows' / '500519ba-audit.yml').exists())

    def test_no_shared_publisher_file_is_named_as_written(self):
        source = (Path(__file__).resolve().parents[1] / 'scripts' / '500519ba_audit.py').read_text()
        for forbidden in ('scripts/collect.py', 'scripts/originate.py'):
            self.assertNotIn(f'open({forbidden!r}, \'w\')', source)
        self.assertNotIn('open(ROOT / \'snapshot.json\', \'w\')', source)


if __name__ == '__main__':
    unittest.main()
