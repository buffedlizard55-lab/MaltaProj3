"""Verification for session arena-93c7475a: a pick — or an explicit limitation —
for every Hotspawn CS2 fixture, and a separated, reachable unresolved section.

These tests pin the four contracts this session changed:

1. **The renderer is actually wired in.**  ``scripts/unresolved_research.py``
   shipped a complete, schema-validated section for the unresolved-pick research
   dossier, but nothing imported it, so the per-fixture HLTV-first trails were
   published only as a JSON file.  ``scripts/build.load_unresolved_research`` is
   the missing half; these tests prove the section renders on ``/unresolved/``
   and that the executive summary links to it.
2. **A stale dossier is never presented as current research.**  Newest-wins is
   decided by the dossier's own ``prepared_at`` and bounded by
   ``UNRESOLVED_RESEARCH_MAX_AGE_HOURS``.
3. **Every rendered row carries a source or an unverified marker** — including
   the alias-join table, which the pre-existing test suite never audited and
   which the site's own row-source audit caught as soon as it rendered.
4. **The probe stays honest.**  A surface that refused the runner is never
   described as reachable, ``flags.json`` is a bare list in the site's finding
   schema, and no dossier can express an invented probability.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import build as site_build
from scripts.unresolved_research import load_research, render_section

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'scripts' / '93c7475a_probe.py'


def make_dossier(prepared_at='2026-10-25T14:40:00Z', *, aliases=False, evidence=True):
    """A minimal schema-valid dossier in the shape the probe emits."""
    source = {'url': 'https://www.hltv.org/matches', 'source': 'HLTV.org upcoming matches',
              'detail': 'Upcoming-match card for these exact two names.',
              'observed_at': '2026-10-25T14:40:00Z'}
    dossier = {
        'schema_version': 1,
        'title': 'Unresolved and non-featured-line picks — HLTV first, then the esportsbooks',
        'prepared_at': prepared_at,
        'research_window': {'from': '2026-10-25T14:39:00Z', 'to': '2026-10-25T14:40:00Z'},
        'prepared_by': 'arena-93c7475a',
        'policy': 'Dated first-hand research; no probability is invented here.',
        'method_order': ['HLTV identity', 'Polymarket', 'Thunderpick'],
        'fixtures': [{
            'hotspawn_id': '1082697',
            'teams': ['BESTIA', 'paiN'],
            'competition': 'Circuit X Curitiba #4',
            'starts_at': '2026-10-25T18:00:00Z',
            'hltv_url': 'https://www.hltv.org/matches/2399819/pain-vs-bestia-circuit-x-curitiba-season-4',
            'checks': [
                {'stage': 'HLTV identity', 'verdict': 'confirmed', 'detail': 'Exact names, start agrees.',
                 'sources': [source]},
                {'stage': 'thunderpick-matches', 'verdict': 'refused-or-failed',
                 'detail': 'HTTP 403 — this surface did not answer the runner.',
                 'sources': [{'url': 'https://thunderpick.io/esports/counter-strike',
                              'source': 'Thunderpick esportsbook', 'detail': 'Surface read.',
                              'observed_at': '2026-10-25T14:40:00Z'}]},
            ],
            'resolution': 'stays-unresolved',
            'resolution_detail': 'A pick exists but it is not a featured market line.',
        }],
        'limitations': ['This dossier records dated observations only.'],
    }
    if aliases:
        entry = {'alias': 'BET-M 33', 'canonical': 'BET-M',
                 'applies_to': ['NODWIN Clutch Series #13'], 'registry': 'data/origination/aliases.json'}
        if evidence:
            entry['evidence'] = [{'url': 'https://www.hltv.org/matches/2399087/x', 'source': 'HLTV.org match page',
                                  'observed_at': '2026-10-16T19:58:00Z'}]
        dossier['aliases_added_this_session'] = [entry]
    return dossier


def write_dossier(directory: Path, session: str, prepared_at: str, **kwargs) -> Path:
    path = directory / 'research' / session / 'unresolved-research.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(make_dossier(prepared_at, **kwargs)))
    return path


class LoaderTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.source = Path(self._tmp.name)

    def loader(self, now):
        return site_build.load_unresolved_research(self.source, now)

    def test_no_dossier_means_no_section(self):
        now = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
        self.assertIsNone(self.loader(now))

    def test_current_dossier_is_found_and_keeps_its_path(self):
        now = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
        write_dossier(self.source, '93c7475a', '2026-10-25T14:40:00Z')
        record = self.loader(now)
        self.assertIsNotNone(record)
        self.assertEqual(record['_record_path'], 'research/93c7475a/unresolved-research.json')

    def test_newest_prepared_at_wins_not_newest_directory_name(self):
        # 'aaa' sorts before 'zzz' but is the older observation.
        now = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
        write_dossier(self.source, 'aaa', '2026-10-25T14:40:00Z')
        write_dossier(self.source, 'zzz', '2026-10-25T14:50:00Z')
        self.assertEqual(self.loader(now)['_record_path'], 'research/zzz/unresolved-research.json')

    def test_stale_dossier_is_never_rendered_as_current_research(self):
        # The committed arena-35440d12 dossier is dated 2026-10-16T20:20:00Z.
        now = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
        write_dossier(self.source, '35440d12', '2026-10-16T20:20:00Z')
        self.assertIsNone(self.loader(now),
                          'a nine-day-old dossier describes a rotated inventory and must not render')
        # The same dossier is current when the reference time is its own day.
        fresh = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
        self.assertIsNotNone(self.loader(fresh))

    def test_schema_invalid_dossier_is_skipped_not_half_parsed(self):
        now = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
        path = write_dossier(self.source, '93c7475a', '2026-10-25T14:40:00Z')
        broken = json.loads(path.read_text())
        broken['fixtures'][0]['checks'][0]['sources'] = []
        path.write_text(json.dumps(broken))
        self.assertIsNone(self.loader(now))


class RenderWiringTests(unittest.TestCase):
    def test_section_renders_on_the_unresolved_page_and_summary_links_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            write_dossier(source, '93c7475a', '2026-10-25T14:40:00Z', aliases=True)
            now = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
            record = site_build.load_unresolved_research(source, now)
            data = {'_unresolved_research': record}
            page = BeautifulSoup(render_section(record, '../'), 'html.parser')
            self.assertIsNotNone(page.find(id='unresolved-research'))
            self.assertIsNotNone(page.find(id='unresolved-aliases'))
            self.assertIsNotNone(page.find(id='unresolved-limitations'))
            line = site_build.unresolved_research_link(data, './')
            self.assertIn('unresolved/#unresolved-research', line)
            self.assertIn('research/93c7475a/unresolved-research.json', line)

    def test_summary_link_is_empty_without_a_current_dossier(self):
        self.assertEqual(site_build.unresolved_research_link({}, './'), '')
        self.assertEqual(site_build.unresolved_research_link({'_unresolved_research': None}, './'), '')

    def test_unresolved_page_calls_the_renderer(self):
        text = (ROOT / 'scripts' / 'build.py').read_text()
        self.assertIn("from scripts.unresolved_research import render_section", text)
        self.assertIn('render_section(dossier, prefix)', text)


class RowSourceTests(unittest.TestCase):
    """The hole the pre-existing suite missed: only ``#unresolved-research`` was
    audited, so the alias table could publish unsourced rows."""

    def every_row(self, **kwargs):
        return BeautifulSoup(render_section(make_dossier(aliases=True, **kwargs), '../'),
                             'html.parser').select('table tbody tr')

    def test_every_rendered_row_carries_a_source_or_unverified_marker(self):
        rows = self.every_row()
        self.assertGreaterEqual(len(rows), 2, 'both the fixture table and the alias table must render')
        for row in rows:
            text = row.get_text(' ', strip=True)
            self.assertTrue('https://' in str(row) or 'unverified' in text, text[:120])

    def test_alias_join_with_evidence_links_it(self):
        html = str(self.every_row(evidence=True))
        self.assertIn('hltv.org', html)

    def test_alias_join_without_inline_evidence_is_marked_unverified(self):
        html = str(self.every_row(evidence=False))
        self.assertIn('unverified', html)

    def test_loader_rejects_alias_evidence_without_a_timestamp(self):
        import tempfile
        data = make_dossier(aliases=True)
        data['aliases_added_this_session'][0]['evidence'][0].pop('observed_at')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'd.json'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_research(path)

    def test_loader_rejects_alias_join_without_a_canonical_name(self):
        import tempfile
        data = make_dossier(aliases=True)
        data['aliases_added_this_session'][0].pop('canonical')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'd.json'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_research(path)


class ProbeContractTests(unittest.TestCase):
    """The probe is the only first-hand outbound path this session has, so its
    honesty is pinned here rather than trusted."""

    def setUp(self):
        self.module = __import__('scripts.93c7475a_probe', fromlist=['main'])

    def test_flags_file_is_a_bare_list_in_the_site_schema(self):
        # ``scripts/build.py`` globs ``data/research/*/flags.json`` and iterates
        # the parsed value directly, so a wrapper object breaks the entire build.
        # That contract is tested on what ``build_flags`` actually returns, not
        # on how the call site happens to be formatted — a source-text grep here
        # would pass on a call site that produced the wrong shape and fail on a
        # correct one.
        summary = {'coverage': {
            'stale_after_hours': 8,
            'published_snapshot_age_hours': None,
            'cited_age_hours': None,
            'published_artifact_url': 'https://example.invalid/snapshot.json',
            'cited_artifact_url': 'https://example.invalid/data/latest.json',
            'open_without_published_row': [{'id': '1082697', 'teams': ['BESTIA', 'paiN']}],
            'published_open_picks': 13,
            'published_open_rows': 16,
        }}
        flags = self.module.build_flags('2026-10-25T00:00:00Z', summary, [], [])
        self.assertIsInstance(flags, list, 'flags.json must be a bare list')
        self.assertTrue(flags, 'a fixture with no published row must produce a finding')
        required = {'id', 'severity', 'title', 'detail', 'match_ids', 'source_urls'}
        for flag in flags:
            self.assertIsInstance(flag, dict)
            self.assertEqual(required - set(flag), set(), f'missing keys in {flag.get("id")}')
            self.assertIn(flag['severity'], {'notice', 'warning'}, flag['id'])
            self.assertIsInstance(flag['match_ids'], list, flag['id'])
            self.assertIsInstance(flag['source_urls'], list, flag['id'])
            for url in flag['source_urls']:
                self.assertTrue(url.startswith('https://'), f'{flag["id"]}: {url}')
        # A stale citation artefact is its own finding, and a fresh dashboard
        # feed must never be reported as stale.
        ids = {f['id'] for f in flags}
        self.assertIn('93c7475a-open-fixtures-missing-from-snapshot', ids)
        self.assertNotIn('93c7475a-published-snapshot-outside-freshness-bound', ids)
        self.assertNotIn('93c7475a-cited-source-artifact-stale', ids)

    def test_a_refused_surface_is_never_described_as_reachable(self):
        dossier = make_dossier()
        dossier['fixtures'][0]['checks'][1]['verdict'] = 'refused-or-failed'
        for check in dossier['fixtures'][0]['checks']:
            if check['verdict'] == 'refused-or-failed':
                self.assertIn('did not answer', check['detail'])
                self.assertNotIn('reachable', check['detail'])
        # The renderer must keep that wording, not silently rewrite it.
        html = render_section(dossier, '../')
        self.assertIn('did not answer', html)
        self.assertIn('refused-or-failed', html)

    def test_refusal_wording_lives_in_the_probe(self):
        text = PROBE.read_text()
        self.assertIn("'refused-or-failed'", text)
        self.assertIn('reachable-no-exact-row', text)
        # The two verdicts must be chosen by the surface's own status.
        self.assertIn("reachable = surface.get('status') == 'ok'", text)

    def test_ranking_position_is_derived_because_the_parser_omits_it(self):
        # scripts.hltv_ranking.parse_ranking_page returns team/points/team_url
        # only, so a position read straight off the row would always be None.
        from scripts import hltv_ranking
        rows = self.module.ranking_rows_with_position([{'team': 'Spirit', 'points': 922.0},
                                                       {'team': 'paiN', 'points': 55.0}])
        self.assertEqual([r['position'] for r in rows], [1, 2])
        self.assertIsNone(self.module.ranking_row('Spirit', hltv_ranking.parse_ranking_page('<html></html>')))
        self.assertEqual(self.module.ranking_row('paiN', rows)['points'], 55.0)

    def test_a_single_repeated_placeholder_is_refused_as_a_two_way_line(self):
        text = PROBE.read_text()
        self.assertIn("'usable_two_way_price': len(distinct) >= 2", text)

    def test_dossier_cannot_express_an_invented_probability(self):
        # The invariant is about the dossier that gets published, not about which
        # source lines mention the word "probabilities": the probe legitimately
        # *reads* a published probability off the dashboard feed to decide
        # whether a pick already exists.  So this drives the real builder and
        # asserts on its output.
        target = {
            'fixture': {'id': '1082697', 'teams': ['BESTIA', 'paiN'], 'competition': 'Circuit X',
                        'starts_at': '2026-10-25T18:00:00Z'},
            'reason': 'pick-not-a-featured-line',
            'published_method': 'model',
            'published_pick': 1,
            'in_feed': True,
            'latest_availability': 'open',
            'hltv': {'exact': [{'url': 'https://www.hltv.org/matches/2399819/pain-vs-bestia',
                                'start_delta_seconds': 0, 'best_of': 'BO3'}],
                     'shares_one_name': []},
            'hltv_analytics': None,
            'ranking': {'BESTIA': {'position': 76, 'points': 180.5}},
            'book_hits': [],
        }
        dossier = self.module.build_dossier(
            '2026-10-25T16:00:00Z', [target], [],
            {'observed_at': '2026-10-25T16:00:00Z', 'upcoming_rows': 40,
             'ranking_observed_at': '2026-10-25T16:00:00Z',
             'ranking_final_url': 'https://www.hltv.org/ranking/teams/2026/october/19',
             'ranking_rows': 253})
        # No probability, pick index or invented 50/50 anywhere in the output.
        def walk(node, path='$'):
            if isinstance(node, dict):
                for key, value in node.items():
                    self.assertNotIn(key, ('probabilities', 'pick_index', 'probability'), f'{path}.{key}')
                    walk(value, f'{path}.{key}')
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, f'{path}[{index}]')
        walk(dossier)
        # ``resolution`` is the only thing allowed to stand in for an outcome, and
        # it is restricted to the two honest values.
        for fixture in dossier['fixtures']:
            self.assertIn(fixture['resolution'], {'stays-unresolved', 'expected-at-next-refresh'})
            self.assertTrue(fixture['resolution_detail'])
        # The dossier must still pass the renderer's own schema gate, which is
        # the check that actually decides whether the section can be published.
        with tempfile.TemporaryDirectory(prefix='93c7475a-dossier-') as tmp:
            path = Path(tmp) / 'unresolved-research.json'
            path.write_text(json.dumps(dossier))
            loaded = load_research(path)
        self.assertEqual(loaded['schema_version'], 1)
        self.assertEqual(len(loaded['fixtures']), 1)
        # And it must render without raising.
        self.assertIn('unresolved-research', render_section(dossier, '../'))

    def test_a_fixture_with_no_pick_is_not_reported_as_having_one(self):
        # Regression pin for the correction made in this session: the dashboard
        # feed (snapshot.json) is the authority on whether a pick exists, because
        # that is what a published page loads.  data/origination.json is a
        # separate artefact that can be many days older; using it as the
        # authority reported all 14 open fixtures as pickless when the feed in
        # fact carried 13 picks.
        text = PROBE.read_text()
        self.assertIn('for row in feed_matches:', text)
        self.assertIn("published.setdefault(str(row.get('id')), row)", text)
        # A row that exists but carries no pick is still "no published row", and
        # the dossier says so without claiming the fixture is absent.
        self.assertIn('has_pick', text)
        self.assertIn("'in_feed': bool(row)", text)

    def test_hotspawn_vote_share_is_never_parsed(self):
        text = PROBE.read_text()
        self.assertNotIn('picked_percent', text)


class LiveEvidenceTests(unittest.TestCase):
    """When the runner has committed live evidence, it must hold up."""

    DOSSIER = ROOT / 'data' / 'research' / '93c7475a' / 'unresolved-research.json'
    PROBE_JSON = ROOT / 'data' / 'research' / '93c7475a' / 'probe.json'
    FLAGS = ROOT / 'data' / 'research' / '93c7475a' / 'flags.json'

    def test_committed_live_evidence_is_consistent(self):
        if not (self.DOSSIER.exists() and self.PROBE_JSON.exists()):
            self.skipTest('the runner has not committed live evidence yet')
        data = load_research(self.DOSSIER)
        probe = json.loads(self.PROBE_JSON.read_text())
        target_ids = {t['fixture']['id'] for t in probe['summary']['targets']}
        self.assertEqual({str(f['hotspawn_id']) for f in data['fixtures']}, target_ids,
                         'the dossier must cover exactly the fixtures the probe researched')
        for fixture in data['fixtures']:
            stages = [c['stage'] for c in fixture['checks']]
            self.assertTrue(any('HLTV' in s for s in stages), fixture['hotspawn_id'])
            self.assertIn(fixture['resolution'], ('stays-unresolved', 'expected-at-next-refresh'))
            for check in fixture['checks']:
                self.assertTrue(check['sources'], check['stage'])
                for src in check['sources']:
                    self.assertTrue(src['url'].startswith('https://'), src)
                    self.assertTrue(src['observed_at'], src)
                if check['verdict'] == 'refused-or-failed':
                    self.assertNotIn('reachable', check['detail'], check['stage'])

    def test_committed_flags_are_a_bare_list(self):
        if not self.FLAGS.exists():
            self.skipTest('the runner has not committed live evidence yet')
        flags = json.loads(self.FLAGS.read_text())
        self.assertIsInstance(flags, list)
        for flag in flags:
            for key in ('id', 'severity', 'title', 'detail', 'match_ids', 'source_urls'):
                self.assertIn(key, flag)
            self.assertIn(flag['severity'], ('notice', 'warning'))
            for url in flag['source_urls']:
                self.assertTrue(url.startswith('https://'), url)


if __name__ == '__main__':
    unittest.main()


class BookParserTests(unittest.TestCase):
    """Regression guard for a false negative this session actually shipped.

    The first version of ``book_titles`` guessed three response shapes and
    silently reported zero rows for surfaces that were in fact serving CS2
    lines. Replayed here against the archived live bodies the runner captured at
    2026-10-25T14:44:30Z, so the shapes are pinned to real evidence rather than
    to a second guess.
    """

    RAW = ROOT / 'data' / 'research' / '93c7475a' / 'raw'

    def setUp(self):
        self.module = __import__('scripts.93c7475a_probe', fromlist=['book_titles'])
        if not (self.RAW / 'thunderpick-matches.json').exists():
            self.skipTest('the runner has not archived the live bodies yet')

    def load(self, name):
        return json.loads((self.RAW / name).read_text())

    def test_thunderpick_upcoming_carries_a_match_winner_price(self):
        rows = self.module.book_titles('thunderpick-matches', self.load('thunderpick-matches.json'), None)
        self.assertGreater(len(rows), 20, 'the archived body lists 42 upcoming CS2 matches')
        by_title = {r['title']: r for r in rows}
        self.assertIn('FlyQuest vs Staqued', by_title)
        odds = dict(by_title['FlyQuest vs Staqued']['odds'])
        self.assertEqual(odds, {'FlyQuest': 1.001, 'Staqued': 12},
                         'the Match Winner decimal prices must be read verbatim')
        # The handicap and total-maps markets must not be mistaken for the
        # full-series winner line.
        self.assertEqual(len(by_title['FlyQuest vs Staqued']['odds']), 2)

    def test_smarkets_events_are_read_from_the_events_key(self):
        rows = self.module.book_titles('smarkets-cs2', self.load('smarkets-cs2.json'), None)
        self.assertEqual(len(rows), 20, 'the archived body lists 20 upcoming CS2 events')
        flyquest = [r for r in rows if r['title'] == 'FlyQuest vs Staqued']
        self.assertEqual(len(flyquest), 1)
        self.assertTrue(flyquest[0]['url'].startswith('https://smarkets.com/sport/esports/cs-go/'),
                        flyquest[0]['url'])

    def test_kalshi_generic_events_are_not_counted_as_cs2_coverage(self):
        rows = self.module.book_titles('kalshi-cs2-events', self.load('kalshi-cs2-events.json'), None)
        self.assertEqual(rows, [], 'the generic open-events endpoint returned no CS2 event')

    def test_exact_name_matching_is_case_equivalent_only(self):
        # Hotspawn lists "BRUTE"; Thunderpick lists "Brute". The project's
        # identity rule is case/Unicode/whitespace equivalence, so this is a
        # legitimate exact join and must be found.
        rows = self.module.book_titles('thunderpick-matches', self.load('thunderpick-matches.json'), None)
        hits = self.module.exact_book_hits({'teams': ['Infinite', 'BRUTE']}, rows)
        self.assertEqual([h['title'] for h in hits], ['Infinite vs Brute'])
        # A different second team is not a hit.
        self.assertEqual(self.module.exact_book_hits({'teams': ['Infinite', 'FaZe']}, rows), [])

    def test_observed_prices_never_become_probabilities(self):
        rows = self.module.book_titles('thunderpick-matches', self.load('thunderpick-matches.json'), None)
        for row in rows:
            for _name, odd in row.get('odds') or []:
                # Prices arrive as int or float — Staqued is quoted as 12, not 12.0.
                self.assertIsInstance(odd, (int, float))
                self.assertNotIsInstance(odd, bool)
                self.assertNotIn('probabilit', str(row).lower())
