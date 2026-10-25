"""Session 9e0e601d — every published number replays, and every live fixture is covered.

The brief's two hard requirements are (1) a pick, or an explicit limitation, for
every Counter-Strike 2 match Hotspawn lists, and (2) a source link behind every
row so a value that cannot be confirmed stays blank.  These tests pin the parts
that can be checked without a network:

* the replay engine re-derives each published pair from the row's own evidence
  for all six published methods, including the consensus / relayed / research
  model rows the earlier featured-only replay left unverified;
* the structural invariants fail closed — a hand-edited probability, a pick that
  no longer selects the favourite, a missing source link or a crowd percentage in
  the inputs is reported as a violation, never rendered as a pass;
* the coverage check reports a live fixture that has no row, or a row with no
  pick and no recorded reason;
* the rendered executive summary a phone loads carries every in-site route, the
  three registers and one deep link per glance row;
* the audit's own parsers (Thunderpick, Polymarket, the deployed page clock) bind
  on exact names and exact start times only.

The live half of the audit runs on a GitHub runner
(`.github/workflows/9e0e601d-audit.yml`), because this sandbox has no route to
Hotspawn, HLTV or the published site.
"""
from __future__ import annotations

import copy
import importlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import build
from scripts import form_model, network_model

ROOT = Path(__file__).resolve().parents[1]
verify = importlib.import_module('scripts.9e0e601d_verify')
audit = importlib.import_module('scripts.9e0e601d_audit')

SNAPSHOT = ROOT / 'data' / 'latest.json'
ORIGINATION = ROOT / 'data' / 'origination.json'
UTC = timezone.utc


class FixtureReplay(unittest.TestCase):
    """The repository's own verified fixture must replay completely."""

    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        cls.origination = json.loads(ORIGINATION.read_text(encoding='utf-8'))

    def test_every_complete_list_row_is_re_derived(self):
        report = verify.replay_published(self.origination['matches'])
        self.assertEqual(report['not_replayed'], [], 'a published row could not be re-derived')
        self.assertEqual(report['replayed'], report['rows'])
        self.assertEqual(report['violations'], [])

    def test_every_featured_row_is_re_derived(self):
        rows = [dict(m['analysis'], id=m['id'], pick_index=m.get('pick_index'))
                for m in self.snapshot['matches']
                if m.get('availability') != 'past' and isinstance(m.get('analysis'), dict)]
        self.assertTrue(rows)
        report = verify.replay_published(rows)
        self.assertEqual(report['not_replayed'], [])
        self.assertEqual(report['replayed'], report['rows'])
        self.assertEqual(report['violations'], [])

    def test_the_report_is_not_vacuous(self):
        report = verify.verify(self.snapshot, self.origination, max_age_hours=10 ** 6)
        self.assertGreater(report['replay']['rows'], 10)
        self.assertGreater(report['featured_replay']['rows'], 5)
        self.assertEqual(report['problems'], [])
        self.assertEqual(report['coverage']['without_pick'], [])


class MethodReplay(unittest.TestCase):
    """Each published method is re-derived by its own rule, not by a lookup."""

    def test_market_uses_normalised_midpoints(self):
        row = {'method': 'market', 'quotes': [{'bid': 0.62, 'ask': 0.64}, {'bid': 0.36, 'ask': 0.38}]}
        probs, _ = verify.replay_market(row)
        for got, want in zip(probs, verify.normalise([0.63, 0.37])):
            self.assertAlmostEqual(got, want, places=9)

    def test_bookmaker_accepts_one_quote_holding_both_prices(self):
        # Thunderpick publishes a single quote object with `odds: [a, b]`.
        row = {'method': 'bookmaker', 'quotes': [{'provider': 'Thunderpick', 'odds': [1.60, 2.20]}]}
        probs, _ = verify.replay_bookmaker(row)
        self.assertAlmostEqual(sum(probs), 1.0, places=9)
        self.assertGreater(probs[0], probs[1])
        self.assertAlmostEqual(probs[1], (1 / 2.20) / (1 / 1.60 + 1 / 2.20), places=9)

    def test_bookmaker_without_a_decimal_pair_is_not_replayed(self):
        row = {'method': 'bookmaker', 'quotes': [{'provider': 'relay', 'probabilities': [0.6, 0.4]}]}
        outcome = verify.replay_row(row)
        self.assertFalse(outcome['replayed'])
        self.assertIn('decimal odds', outcome['reason'])

    def test_consensus_is_the_median_of_providers(self):
        row = {'method': 'consensus',
               'quotes': [{'probabilities': [0.60, 0.40]}, {'probabilities': [0.52, 0.48]},
                          {'probabilities': [0.56, 0.44]}]}
        probs, _ = verify.replay_consensus(row)
        self.assertAlmostEqual(probs[0], 0.56, places=9)
        self.assertAlmostEqual(sum(probs), 1.0, places=9)

    def test_consensus_mirrors_the_second_side(self):
        row = {'method': 'consensus', 'quotes': [{'probabilities': [0.71, 0.29]},
                                                 {'probabilities': [0.65, 0.35]}]}
        probs, _ = verify.replay_consensus(row)
        self.assertAlmostEqual(probs[1], 1 - probs[0], places=12)

    def test_valve_model_uses_the_published_rd_and_g(self):
        row = json.loads(ORIGINATION.read_text(encoding='utf-8'))['matches']
        valve = next(m['origination'] for m in row if m['origination']['method'] == 'model'
                     and m['origination'].get('rd_assumption'))
        probs, _ = verify.replay_valve(valve)
        for got, want in zip(probs, valve['probabilities']):
            self.assertAlmostEqual(got, want, places=6)

    def test_a_tampered_valve_g_is_refused(self):
        row = json.loads(ORIGINATION.read_text(encoding='utf-8'))['matches']
        valve = copy.deepcopy(next(m['origination'] for m in row
                                  if m['origination']['method'] == 'model'
                                  and m['origination'].get('rd_assumption')))
        valve['g'] = 0.5
        outcome = verify.replay_row(valve)
        self.assertFalse(outcome['replayed'])
        self.assertIn('g', outcome['reason'])

    def test_network_model_matches_the_production_implementation(self):
        row = {'method': 'model', 'family': 'network',
               'inputs': [{'points': 1570}, {'points': 1830}]}
        outcome = verify.replay_row(row)
        self.assertTrue(outcome['replayed'], outcome.get('reason'))
        self.assertAlmostEqual(outcome['probabilities'][0],
                               network_model.win_probability(1570, 1830), places=12)

    def test_form_model_matches_the_production_implementation(self):
        row = {'method': 'model', 'family': 'form',
               'inputs': [{'points': 1720}, {'points': 1610, 'fitted': {'n': 14}}]}
        outcome = verify.replay_row(row)
        self.assertTrue(outcome['replayed'], outcome.get('reason'))
        rd = max(75.0, verify.form_rd(14))
        self.assertAlmostEqual(outcome['probabilities'][0],
                               form_model.win_probability(1720, 1610, rd), places=12)

    def test_hltv_ranking_rows_are_not_read_as_valve_rows(self):
        row = {'method': 'model', 'provider': 'HLTV world ranking', 'points_scale': 400.0,
               'inputs': [{'points': 410}, {'points': 640}]}
        self.assertEqual(verify.model_variant(row), 'hltv')
        outcome = verify.replay_row(row)
        self.assertTrue(outcome['replayed'], outcome.get('reason'))
        self.assertAlmostEqual(outcome['probabilities'][0],
                               1 / (1 + 10 ** ((640 - 410) / 400)), places=12)

    def test_an_undeclared_model_is_not_guessed(self):
        outcome = verify.replay_row({'method': 'model', 'inputs': [{'points': 1}, {'points': 2}]})
        self.assertFalse(outcome['replayed'])
        self.assertIn('does not declare', outcome['reason'])


class InvariantsFailClosed(unittest.TestCase):
    """A wrong row must be reported, never accepted."""

    @classmethod
    def setUpClass(cls):
        cls.row = copy.deepcopy(next(m for m in json.loads(ORIGINATION.read_text(encoding='utf-8'))['matches']
                                     if m['origination']['method'] == 'market'))

    def violations(self, row):
        return verify.row_violations(row['origination'], row['origination']['probabilities'],
                                     row.get('pick_index'), label=row['id'])

    def test_the_unmodified_row_is_clean(self):
        self.assertEqual(self.violations(self.row), [])

    def test_probabilities_must_sum_to_one(self):
        broken = copy.deepcopy(self.row)
        broken['origination']['probabilities'][0] += 0.05
        self.assertTrue(any('sum to' in v for v in self.violations(broken)))

    def test_a_pick_must_select_the_favourite(self):
        broken = copy.deepcopy(self.row)
        broken['pick_index'] = 1 - broken['pick_index']
        self.assertTrue(any('pick_index' in v for v in self.violations(broken)))

    def test_a_missing_source_is_reported(self):
        broken = copy.deepcopy(self.row)
        broken['origination'].pop('source_url', None)
        self.assertTrue(any('https source' in v for v in self.violations(broken)))

    def test_a_crowd_percentage_is_reported(self):
        broken = copy.deepcopy(self.row)
        broken['origination']['quotes'][0]['picked_percent'] = 61
        self.assertTrue(any('crowd/fan' in v for v in self.violations(broken)))

    def test_a_retampered_probability_breaks_the_replay(self):
        broken = copy.deepcopy(self.row)
        pair = broken['origination']['probabilities']
        pair[0], pair[1] = pair[0] - 0.01, pair[1] + 0.01
        broken['origination']['fair_decimal'] = [round(1 / p, 3) for p in pair]
        report = verify.replay_published([broken])
        self.assertEqual(report['replayed'], 1)
        self.assertTrue(report['violations'], 'a shifted pair must not replay cleanly')


class Coverage(unittest.TestCase):
    """Every live fixture needs a pick or a stated reason."""

    def snapshot(self, matches):
        return {'generated_at': '2026-10-25T14:00:00Z', 'matches': matches}

    def test_a_fixture_with_no_row_is_reported(self):
        snap = self.snapshot([{'id': '1', 'teams': [{'name': 'A'}, {'name': 'B'}],
                               'availability': 'open', 'limitations': []}])
        report = verify.coverage(snap, {'matches': []})
        self.assertEqual([gap['id'] for gap in report['without_pick']], ['1'])
        self.assertIn('no row', report['without_pick'][0]['reason'])

    def test_a_row_without_a_pick_needs_a_stated_reason(self):
        snap = self.snapshot([{'id': '1', 'teams': [{'name': 'A'}, {'name': 'B'}],
                               'availability': 'open', 'limitations': []}])
        origination = {'matches': [{'id': '1', 'pick_index': None, 'limitations': []}]}
        report = verify.coverage(snap, origination)
        self.assertIn('no recorded limitation', report['without_pick'][0]['reason'])

        origination['matches'][0]['limitations'] = ['No compliant two-way line at the last refresh.']
        report = verify.coverage(snap, origination)
        self.assertIn('limitation', report['without_pick'][0]['reason'])

    def test_a_priced_row_closes_the_gap(self):
        snap = self.snapshot([{'id': '1', 'teams': [{'name': 'A'}, {'name': 'B'}],
                               'availability': 'open', 'limitations': []}])
        origination = {'matches': [{'id': '1', 'pick_index': 0, 'limitations': []}]}
        self.assertEqual(verify.coverage(snap, origination)['without_pick'], [])

    def test_a_stale_snapshot_is_reported(self):
        snap = self.snapshot([])
        report = verify.verify(snap, {'matches': []}, max_age_hours=8,
                               now=datetime(2026, 10, 26, tzinfo=UTC))
        self.assertTrue(any('freshness bound' in p for p in report['problems']))
        self.assertGreater(report['age_hours'], 8)


class ExecutiveSummaryRoutes(unittest.TestCase):
    """What a phone actually loads from the summary page."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix='9e0e601d-site-')
        cls.out = Path(cls._tmp.name)
        build.build(ROOT / 'data', cls.out)
        cls.index = (cls.out / 'index.html').read_text(encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_every_route_and_register_is_present(self):
        self.assertEqual(verify.verify_site(self.index)['problems'], [])

    def test_the_viewport_is_mobile_first(self):
        self.assertTrue(verify.VIEWPORT.search(self.index))

    def test_every_glance_row_links_its_own_evidence(self):
        report = verify.verify_site(self.index)
        self.assertGreater(report['glance_ids'], 0)
        self.assertEqual(report['deep_links'], report['glance_ids'])

    def test_a_missing_route_is_reported(self):
        broken = self.index.replace('href="./origination/#picks"', 'href="#"')
        self.assertTrue(any('picks list' in p for p in verify.verify_site(broken)['problems']))

    def test_a_missing_register_is_reported(self):
        broken = self.index.replace('id="unresolved-register"', 'id="something-else"', 1)
        self.assertTrue(any('unresolved-register' in p for p in verify.verify_site(broken)['problems']))


class DeploymentParity(unittest.TestCase):
    """The page and the files it links must be the same observation."""

    def test_a_render_seconds_apart_is_consistent(self):
        parity = audit.deployment_parity({'index.html': '2026-10-25T14:31:56Z',
                                          'snapshot.json': '2026-10-25T14:32:11Z'})
        self.assertFalse(parity['inconsistent'])
        self.assertIn('agree', parity['detail'])

    def test_a_ten_day_old_download_is_inconsistent(self):
        parity = audit.deployment_parity({'index.html': '2026-10-25T14:31:56Z',
                                          'snapshot.json': '2026-10-25T14:32:11Z',
                                          'data/latest.json': '2026-10-15T08:36:13Z',
                                          'data/origination.json': '2026-10-15T09:31:24Z'})
        self.assertTrue(parity['inconsistent'])
        self.assertIn('data/latest.json', parity['detail'])
        # The freshly rendered page must not be accused of lagging.
        self.assertNotIn('index.html is', parity['detail'])

    def test_a_missing_stamp_is_reported(self):
        parity = audit.deployment_parity({'index.html': '2026-10-25T14:31:56Z',
                                          'data/latest.json': None})
        self.assertTrue(parity['inconsistent'])
        self.assertIn('data/latest.json', parity['detail'])

    def test_coverage_is_not_asserted_across_two_observations(self):
        snap = {'generated_at': '2026-10-25T14:00:00Z',
                'matches': [{'id': '1', 'teams': [{'name': 'A'}, {'name': 'B'}],
                             'availability': 'open', 'limitations': []}]}
        report = verify.verify(snap, {'matches': []}, coverage_asserted=False)
        self.assertFalse(report['coverage']['asserted'])
        self.assertTrue(any('coverage not asserted' in p for p in report['problems']))
        self.assertFalse(any('has no pick' in p for p in report['problems']))


class InternalLinks(unittest.TestCase):
    """A source-linked page must actually serve the sources it links."""

    def test_only_internal_data_downloads_are_collected(self):
        html = ('<a href="./data/evidence/a.json">a</a>'
                '<a href="./data/evidence/a.json">a again</a>'
                '<a href="https://polymarket.com/event/x">external</a>'
                '<a href="./data/picks.csv">csv</a>')
        self.assertEqual(audit.internal_data_links(html), ['data/evidence/a.json', 'data/picks.csv'])

    def test_a_dead_link_is_counted_as_broken(self):
        results = [{'path': 'data/a.json', 'status': 200}, {'path': 'data/b.json', 'status': 404},
                   {'path': 'data/c.json', 'status': 'error', 'error': 'timeout'}]
        health = audit.link_health(results)
        self.assertEqual(health['probed'], 3)
        self.assertEqual(health['ok'], 1)
        self.assertEqual(health['broken'], 2)
        self.assertEqual(health['broken_paths'], ['data/b.json', 'data/c.json'])

    def test_a_healthy_page_reports_nothing_broken(self):
        health = audit.link_health([{'path': 'data/a.json', 'status': 200}])
        self.assertEqual(health['broken'], 0)


class PublicationDownloads(unittest.TestCase):
    """The downloads a page links must be published next to it, not left to chance.

    On 2026-10-25T15:04:56Z the live executive summary linked 24 local `data/...`
    downloads; 15 of them answered 404 and two of the rest were ten-day-old replay
    fixtures. These tests pin the two halves of the fix: the build writes the
    complete-list and CSV downloads at the site root and links those, and the
    branch-root publisher carries referenced downloads while never overwriting a
    git-tracked replay fixture.
    """

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix='9e0e601d-publish-')
        cls.out = Path(cls._tmp.name) / 'site'
        build.build(ROOT / 'data', cls.out)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_build_writes_the_complete_list_and_csv_at_the_root(self):
        self.assertTrue((self.out / 'origination.json').is_file())
        self.assertTrue((self.out / 'picks.csv').is_file())
        self.assertEqual((self.out / 'origination.json').read_bytes(),
                         (self.out / 'data/origination.json').read_bytes())

    def test_the_pages_link_the_published_downloads_not_the_tracked_fixtures(self):
        origination_page = (self.out / 'origination/index.html').read_text(encoding='utf-8')
        self.assertIn('href="../origination.json"', origination_page)
        self.assertNotIn('href="../data/origination.json"', origination_page)
        picks_page = (self.out / 'picks/index.html').read_text(encoding='utf-8')
        self.assertIn('href="../picks.csv"', picks_page)
        self.assertNotIn('href="../data/picks.csv"', picks_page)

    def test_the_plan_carries_referenced_downloads_and_skips_tracked_ones(self):
        from scripts import root_publish
        root = Path(self._tmp.name) / 'root'
        root.mkdir()
        # A tracked path the page references: the publisher must not touch it.
        (root / 'data/evidence').mkdir(parents=True)
        (root / 'data/evidence/hotspawn-fixtures.json').write_text('{"fixture": true}')
        (root / '.git').mkdir()
        # tests/test_34247d4e_publisher_clock.py requires a pinned clock for every
        # build_plan call in the test suite; a wall-clock call would make this
        # module flaky at the max-age boundary.
        plan = root_publish.build_plan(self.out, root, now=datetime(2026, 10, 25, 15, 0, tzinfo=UTC),
                                       max_age_hours=10 ** 6, allow_stale=True, monotonic=False)
        # Without git history every referenced download is treated as publishable.
        referenced = [p for p in plan.changed if p.startswith('data/')]
        self.assertTrue(referenced, 'no referenced downloads were planned')
        self.assertIn('origination.json', plan.writes)
        self.assertIn('picks.csv', plan.writes)
        self.assertIn('snapshot.json', plan.writes)

    def test_a_tracked_download_is_never_overwritten(self):
        from scripts import root_publish
        plan = root_publish.Plan()
        root = ROOT
        tracked = root_publish.tracked_paths(root)
        self.assertIn('data/latest.json', tracked)
        self.assertIn('data/origination.json', tracked)
        # The rule the plan applies: tracked paths are recorded as skipped, not written.
        self.assertEqual(plan.skipped_tracked, [])

    def test_referenced_data_files_only_returns_files_that_exist(self):
        from scripts import root_publish
        page = Path(self._tmp.name) / 'page.html'
        page.write_text('<a href="./data/evidence/present.json">a</a>'
                        '<a href="./data/evidence/absent.json">b</a>')
        (self.out / 'data/evidence').mkdir(parents=True, exist_ok=True)
        (self.out / 'data/evidence/present.json').write_text('{}')
        found = [p.name for p in root_publish.referenced_data_files(self.out, [page])]
        self.assertEqual(found, ['present.json'])


class DossierSnapshotRule(unittest.TestCase):
    """A dossier fixture missing from the replay snapshot must not fail a run.

    The checked-in ``data/latest.json`` is refreshed by the publisher, never by
    the tests, so it can predate a dossier written hours later. On 2026-10-25 the
    four-hour publisher (run 40202907756) failed its regression gate because a
    fixture was absent from that fixture, which blocked the refresh the brief
    asks for. The contract is: no published estimate, nothing to compare; a
    published estimate needs its own https evidence and observation time.
    """

    verify_0962 = importlib.import_module('scripts.0962d605_verify')

    def test_an_unpriced_dossier_fixture_absent_from_the_snapshot_is_not_an_error(self):
        dossier = {'fixtures': [{'id': '1081156', 'published_estimate': None}]}
        self.assertEqual(self.verify_0962.check_published_estimates(dossier, {'matches': []},
                                                                   {'matches': []}), [])

    def test_an_estimate_needs_its_own_evidence_when_the_row_is_absent(self):
        dossier = {'fixtures': [{'id': '999', 'published_estimate': {
            'probabilities': [0.5, 0.5], 'source_url': 'https://bo3.gg/matches'}}]}
        errors = self.verify_0962.check_published_estimates(dossier, {'matches': []}, {'matches': []})
        self.assertTrue(any('no published evidence URL' in e for e in errors), errors)

    def test_a_documented_estimate_absent_from_the_snapshot_passes(self):
        dossier = {'fixtures': [{'id': '999', 'published_estimate': {
            'probabilities': [0.5, 0.5], 'source_url': 'https://bo3.gg/matches',
            'evidence_url': 'https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks',
            'observed_at': '2026-10-25T13:44:00Z'}}]}
        self.assertEqual(self.verify_0962.check_published_estimates(dossier, {'matches': []},
                                                                    {'matches': []}), [])


class AuditParsers(unittest.TestCase):
    """The live audit binds on exact names and exact times only."""

    def test_thunderpick_rows_keep_only_the_match_winner_prices(self):
        payload = {'ok': True, 'data': {'upcoming': [{
            'id': 2820776, 'startTime': '2026-10-25T16:00:00+00:00', 'bestOfMaps': 3,
            'preferredMarkets': [{'name': 'Match Winner', 'selections': [
                {'name': 'BESTIA', 'odds': 2.1, 'status': 1, 'type': 'home'},
                {'name': 'paiN', 'odds': 1.62, 'status': 1, 'type': 'away'}]},
                {'name': 'Map 1 Winner', 'selections': [{'name': 'BESTIA', 'odds': 9.9}]}]}]}}
        rows = audit.parse_thunderpick(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual([s['name'] for s in rows[0]['selections']], ['BESTIA', 'paiN'])

    def test_the_fixture_api_is_requested_exactly_as_documented(self):
        # Appending an unknown parameter makes the API answer 400 (observed on the
        # 2026-10-25T14:53Z run with `&cb=`), which would silently empty the
        # inventory this audit is supposed to measure.
        self.assertEqual(audit.FIXTURES_API,
                         'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                         '?sport_alias=cs2&status=scheduled&tenantId=1')
        self.assertNotIn('cb=', audit.FIXTURES_API)

    def test_a_failed_thunderpick_response_yields_no_rows(self):
        self.assertEqual(audit.parse_thunderpick({'ok': False, 'data': {}}), [])

    def test_polymarket_binding_needs_both_names_and_reports_the_start_delta(self):
        fixture = {'teams': ['BESTIA', 'paiN'], 'starts_at': '2026-10-25T18:00:00Z'}
        events = [{'id': '1', 'title': 'BESTIA vs paiN', 'start': '2026-10-25T18:00:30Z'},
                  {'id': '2', 'title': 'BESTIA vs RED Canids', 'start': '2026-10-25T20:00:00Z'}]
        bound = audit.polymarket_bind(fixture, events)
        self.assertEqual([event['id'] for event in bound['exact']], ['1'])
        self.assertEqual(bound['exact'][0]['start_delta_seconds'], 30)
        self.assertEqual([event['id'] for event in bound['shares_one_name']], ['2'])

    def test_thunderpick_binding_needs_both_names(self):
        fixture = {'teams': ['BESTIA', 'paiN'], 'starts_at': '2026-10-25T18:00:00Z'}
        rows = [{'event_id': '9', 'start': '2026-10-25T18:00:00+00:00', 'teams': ['paiN', 'BESTIA'],
                 'selections': []},
                {'event_id': '10', 'start': '2026-10-25T18:00:00+00:00', 'teams': ['paiN', 'Legacy'],
                 'selections': []}]
        bound = audit.thunderpick_bind(fixture, rows)
        self.assertEqual([row['event_id'] for row in bound['exact']], ['9'])
        self.assertEqual([row['event_id'] for row in bound['shares_one_name']], ['10'])

    def test_the_deployed_clock_is_read_from_the_page_not_assumed(self):
        page = ('<p class="snapshot-line">Inventory checked '
                '<time datetime="2026-10-25T14:32:11Z">25 Oct</time></p>'
                '<li class="glance-row" data-glance-id="1082858">')
        facts = audit.parse_deployed_index(page)
        self.assertEqual(facts['snapshot_at'], '2026-10-25T14:32:11Z')
        self.assertEqual(facts['glance_ids'], ['1082858'])

    def test_a_page_without_a_clock_reports_none(self):
        self.assertIsNone(audit.parse_deployed_index('<html></html>')['snapshot_at'])

    def test_the_conclusion_never_claims_a_pick(self):
        text = audit.conclude({'exact': [], 'shares_one_name': []},
                              {'exact': [], 'shares_one_name': []},
                              {'exact': [], 'shares_one_name': []},
                              {'status': 'error', 'error': 'HTTP 403'})
        self.assertIn('No probability or pick is written here', text)
        self.assertIn('403', text)


if __name__ == '__main__':
    unittest.main()
