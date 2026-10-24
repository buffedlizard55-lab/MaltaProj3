"""Session arena-a7128fdd: the dated direct-observation register.

What a surface that *answered* actually published, for the fixtures the priced
ladder could only resolve with a research model. Evidence and limitations only:
no test here permits a probability, a pick or an alias to come out of it, and
several tests exist purely to prove that.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build import direct_observation_block, load_direct_observations

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'data' / 'research' / 'a7128fdd' / 'direct-observations.json'
MARKDOWN = ROOT / 'data' / 'research' / 'a7128fdd' / 'direct-observations.md'
FLAGS = ROOT / 'data' / 'research' / 'a7128fdd' / 'flags.json'



def committed_records():
    """Every dated direct-observation dossier in the repository, oldest first."""
    found = []
    for path in sorted((ROOT / 'data' / 'research').glob('*/direct-observations.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        found.append(dict(record, _record_path=path.relative_to(ROOT / 'data').as_posix()))
    return sorted(found, key=lambda item: item['observed_at'])


def newest_committed_record():
    return committed_records()[-1]

def observation(**over):
    base = {
        'id': 'x-surface',
        'surface': 'HLTV match page',
        'url': 'https://www.hltv.org/matches/2399849/k27-vs-virtuspro',
        'http_status': 200,
        'fixture_ids': ['1083014'],
        'teams_as_published': ['K27', 'Virtus.pro'],
        'excerpt': 'Best of 3 (LAN) · K27 [HLTV: #46] [VRS: #33]',
        'two_sided_price': None,
        'usable_as_price': False,
        'verdict': 'reachable, no price',
        'reason': 'The page publishes format and ranks, not a two-sided prematch price.',
    }
    base.update(over)
    base.setdefault('excerpt_sha256', hashlib.sha256(base['excerpt'].encode()).hexdigest())
    return base


def record(**over):
    base = {
        'schema': 'a7128fdd-direct-observations/1',
        'observed_at': '2026-10-23T10:05:00Z',
        'environment': 'authoring-fetch-path',
        'fixture_scope': [
            {'hotspawn_id': '1083014', 'teams': ['K27', 'Virtus.pro'],
             'competition': 'CIS LAN Championship #9', 'starts_at': '2026-10-23T13:00:00Z',
             'published_method': 'Market line'},
        ],
        'observations': [observation()],
        'conclusions': {
            'fixtures_in_scope': 1,
            'fixtures_with_a_new_two_sided_price': 0,
            'fixtures_with_new_official_identity_or_format_evidence': 1,
            'probabilities_changed': 0,
            'picks_changed': 0,
            'aliases_added': 0,
            'summary': 'No two-sided price existed, so nothing changed.',
        },
    }
    base.update(over)
    return base


def write_tree(root: Path, name: str, payload, *, markdown: bool = True):
    """Write a candidate record the way the loader discovers it."""
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'direct-observations.json'
    path.write_text(payload if isinstance(payload, str)
                    else json.dumps(payload), encoding='utf-8')
    if markdown:
        path.with_suffix('.md').write_text('# record\n', encoding='utf-8')
    return path


class LoaderContract(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.source = self.tmp / 'data'
        (self.source / 'research').mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_accepts_a_well_formed_record(self):
        write_tree(self.source / 'research', 'a7128fdd', record())
        got = load_direct_observations(self.source)
        self.assertIsNotNone(got)
        self.assertEqual(got['observed_at'], '2026-10-23T10:05:00Z')
        self.assertEqual(got['_record_path'], 'research/a7128fdd/direct-observations.json')

    def test_returns_none_when_nothing_is_present(self):
        self.assertIsNone(load_direct_observations(self.source))

    def test_rejects_a_record_without_its_markdown_sibling(self):
        write_tree(self.source / 'research', 'a7128fdd', record(), markdown=False)
        self.assertIsNone(load_direct_observations(self.source))

    def test_rejects_a_missing_observations_list(self):
        for bad in ({}, 'nope', 7, None):
            write_tree(self.source / 'research', 'a7128fdd', record(observations=bad))
            self.assertIsNone(load_direct_observations(self.source), f'accepted {bad!r}')

    def test_rejects_an_empty_observations_list(self):
        write_tree(self.source / 'research', 'a7128fdd', record(observations=[]))
        self.assertIsNone(load_direct_observations(self.source))

    def test_rejects_an_unparseable_or_missing_observed_at(self):
        for bad in (None, '', 'not-a-time', '2026-13-45T99:99:99Z'):
            write_tree(self.source / 'research', 'a7128fdd', record(observed_at=bad))
            self.assertIsNone(load_direct_observations(self.source), f'accepted {bad!r}')

    def test_rejects_malformed_json_and_non_dict_payloads(self):
        write_tree(self.source / 'research', 'a7128fdd', '{not json')
        self.assertIsNone(load_direct_observations(self.source))
        write_tree(self.source / 'research', 'a7128fdd', '[1,2,3]')
        self.assertIsNone(load_direct_observations(self.source))

    def test_picks_the_newest_observation_not_the_newest_directory_name(self):
        write_tree(self.source / 'research', 'zzz99999',
                   record(observed_at='2026-10-20T01:00:00Z'))
        write_tree(self.source / 'research', 'aaa00001',
                   record(observed_at='2026-10-23T10:05:00Z'))
        got = load_direct_observations(self.source)
        self.assertEqual(got['_record_path'], 'research/aaa00001/direct-observations.json')

    def test_environment_is_preserved_verbatim_not_normalised_to_the_runner(self):
        """The capture path is the finding, so it must survive the round trip."""
        write_tree(self.source / 'research', 'a7128fdd',
                   record(environment='authoring-fetch-path'))
        self.assertEqual(load_direct_observations(self.source)['environment'],
                         'authoring-fetch-path')

    def test_it_is_not_eligible_for_the_runner_only_priced_ladder(self):
        """The complement of load_no_line_research, never a replacement for it."""
        from scripts.build import load_no_line_research
        payload = record(environment='github-actions-runner',
                         per_fixture=[{'id': '1083014', 'teams': ['K27', 'Virtus.pro']}])
        write_tree(self.source / 'research', 'a7128fdd', payload)
        # A direct-observations file is never read as a line-source-research file.
        self.assertIsNone(load_no_line_research(self.source))
        self.assertIsNotNone(load_direct_observations(self.source))


class RenderedBlock(unittest.TestCase):
    def setUp(self):
        self.data = {'_direct_observations': record(),
                     'matches': [{'id': '1083014'}],
                     'complete_picks': {'matches': []}}
        self.html = direct_observation_block(self.data, '../')

    def test_returns_empty_without_a_record(self):
        self.assertEqual(direct_observation_block({}, '../'), '')
        self.assertEqual(direct_observation_block({'_direct_observations': None}, '../'), '')
        self.assertEqual(direct_observation_block({'_direct_observations': record(observations=[])}, '../'), '')

    def test_it_has_a_stable_anchor_and_reuses_the_existing_card_style(self):
        self.assertIn('id="direct-observations"', self.html)
        self.assertIn('class="line-sources"', self.html)
        self.assertIn('class="line-source-list"', self.html)

    def test_every_observation_links_the_page_as_read_over_https(self):
        self.assertIn('https://www.hltv.org/matches/2399849/k27-vs-virtuspro', self.html)
        self.assertIn('Open the page as read', self.html)
        self.assertIn('rel="noopener noreferrer"', self.html)

    def test_the_verbatim_excerpt_and_its_hash_are_published(self):
        self.assertIn('Best of 3 (LAN)', self.html)
        self.assertIn(hashlib.sha256(b'Best of 3 (LAN) \xc2\xb7 K27 [HLTV: #46] [VRS: #33]')
                      .hexdigest()[:16], self.html)

    def test_the_reason_it_is_not_an_input_is_printed_for_every_observation(self):
        self.assertIn('Why this is not a pick input.', self.html)
        self.assertIn('not a two-sided prematch price', self.html)

    def test_an_observation_that_cannot_price_is_chipped_as_such(self):
        self.assertIn('no usable price', self.html)
        self.assertNotIn('>two-sided price<', self.html)

    def test_a_genuinely_priced_observation_would_be_chipped_as_priced(self):
        data = {'_direct_observations': record(observations=[
            observation(two_sided_price=[1.76, 2.05], usable_as_price=True,
                        verdict='two-sided bookmaker price captured')]),
                'matches': [{'id': '1083014'}], 'complete_picks': {'matches': []}}
        html = direct_observation_block(data, '../')
        self.assertIn('>two-sided price<', html)

    def test_it_never_renders_a_pick_or_a_probability_of_its_own(self):
        """The register is evidence. It must not look like a pick list."""
        for forbidden in ('pick-index', 'data-pick', 'class="pick"', 'suggested_team',
                          'probability-bar', 'glance-row'):
            self.assertNotIn(forbidden, self.html)

    def test_the_capture_path_is_visible_and_human_readable(self):
        self.assertIn('authoring fetch path', self.html)
        self.assertIn('not the four-hour runner', self.html)

    def test_the_counts_it_reports_come_from_the_record(self):
        for needle in ('<strong>0</strong> gained a two-sided price',
                       '<strong>1</strong> gained official identity or format evidence',
                       '<strong>0</strong> probabilities'):
            self.assertIn(needle, self.html)

    def test_the_conclusion_sentence_is_published(self):
        self.assertIn('No two-sided price existed, so nothing changed.', self.html)

    def test_download_links_point_at_the_record_it_rendered(self):
        self.data['_direct_observations']['_record_path'] = \
            'research/a7128fdd/direct-observations.json'
        html = direct_observation_block(self.data, '../')
        self.assertIn('../data/research/a7128fdd/direct-observations.md', html)
        self.assertIn('../data/research/a7128fdd/direct-observations.json', html)

    def test_no_download_links_when_the_path_is_unknown(self):
        html = direct_observation_block({'_direct_observations': record(),
                                         'matches': [], 'complete_picks': None}, '../')
        self.assertNotIn('Full dated record', html)


class ScopeLinksCannotBreak(unittest.TestCase):
    """A fixture can be active in the inventory and absent from the origination feed.

    Regression for the live-build failure CI caught on this PR: gating on
    ``data['matches']`` published ``./origination/#match-1081605`` with no anchor
    behind it, because those ``id="match-<id>"`` articles are rendered by
    ``scripts/build_origination.py`` from the *complete-picks* feed only, which is
    a narrower set than the inventory. ``scripts.validate.check_links`` rejected
    it, correctly.
    """

    SCOPE = [
        {'hotspawn_id': '1083014', 'teams': ['K27', 'Virtus.pro'],
         'competition': 'CIS LAN Championship #9', 'starts_at': '2026-10-23T13:00:00Z',
         'published_method': 'Market line'},
        {'hotspawn_id': '1081605', 'teams': ['Phantom Academy', 'Banda chuya'],
         'competition': 'CCT Europe 2026 Challengers #8', 'starts_at': '2026-10-23T11:00:00Z',
         'published_method': 'Valve-rating research estimate'},
    ]

    def data(self, origination_ids, inventory_ids=None):
        return {'_direct_observations': record(fixture_scope=self.SCOPE),
                'matches': [{'id': i} for i in (inventory_ids or origination_ids)],
                'complete_picks': {'matches': [{'id': i} for i in origination_ids]}}

    def test_a_fixture_the_origination_page_rendered_is_linked(self):
        html = direct_observation_block(self.data(['1083014', '1081605']), '../')
        self.assertIn('../origination/#match-1083014', html)
        self.assertIn('../origination/#match-1081605', html)

    def test_a_fixture_only_in_the_inventory_is_never_linked(self):
        """The exact CI failure: active in latest.json, absent from origination.json."""
        html = direct_observation_block(
            self.data(['1083014'], inventory_ids=['1083014', '1081605']), '../')
        self.assertIn('../origination/#match-1083014', html)
        self.assertNotIn('match-1081605', html)
        # The fixture is still listed as evidence, just not linked.
        self.assertIn('Phantom Academy vs Banda chuya', html)

    def test_no_link_at_all_when_the_origination_feed_is_empty(self):
        html = direct_observation_block(self.data([], inventory_ids=['1083014']), '../')
        self.assertNotIn('origination/#match-', html)
        self.assertIn('K27 vs Virtus.pro', html)

    def test_no_scope_list_at_all_when_the_record_has_none(self):
        html = direct_observation_block({'_direct_observations': record(fixture_scope=[]),
                                         'matches': [], 'complete_picks': None}, '../')
        self.assertNotIn('direct-scope', html)
        self.assertNotIn('In scope:', html)

    def test_a_missing_complete_picks_feed_is_not_an_error(self):
        html = direct_observation_block({'_direct_observations': record(fixture_scope=self.SCOPE),
                                         'matches': [{'id': '1083014'}],
                                         'complete_picks': None}, '../')
        self.assertNotIn('origination/#match-', html)
        self.assertIn('K27 vs Virtus.pro', html)

    def test_a_scope_entry_without_an_id_is_rendered_as_text_not_a_broken_link(self):
        scope = [{'teams': ['No Id', 'Here'], 'competition': 'X', 'starts_at': '', 'published_method': ''}]
        html = direct_observation_block({'_direct_observations': record(fixture_scope=scope),
                                         'matches': [], 'complete_picks': {'matches': []}}, '../')
        self.assertIn('No Id vs Here', html)
        self.assertNotIn('#match-"', html)
        self.assertNotIn('#match-<', html)


class CheckedInRecord(unittest.TestCase):
    """The committed evidence must itself satisfy the contract it renders from."""

    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text(encoding='utf-8'))

    def test_the_record_and_its_markdown_both_exist(self):
        self.assertTrue(RECORD.is_file())
        self.assertTrue(MARKDOWN.is_file())

    def test_the_loader_accepts_the_committed_record(self):
        # Newest wins by design (`load_direct_observations` sorts on observed_at),
        # so this asserts that the loader renders the newest committed dossier —
        # which was this one until 2026-10-24, when arena-8aa401c8 committed a
        # later read. Pinning this session's stamp instead of the loader's own
        # rule would fail every later session that adds dated evidence, which is
        # the opposite of the register's purpose.
        got = load_direct_observations(ROOT / 'data')
        self.assertIsNotNone(got)
        newest = newest_committed_record()
        self.assertEqual(got['observed_at'], newest['observed_at'])
        self.assertEqual(got['_record_path'], newest['_record_path'])

    def test_it_states_its_capture_path_and_does_not_claim_to_be_a_runner(self):
        self.assertEqual(self.record['environment'], 'authoring-fetch-path')
        self.assertIn('NOT from a GitHub Actions runner', self.record['environment_note'])

    def test_every_observation_carries_url_status_excerpt_hash_verdict_and_reason(self):
        self.assertTrue(self.record['observations'])
        for o in self.record['observations']:
            for key in ('id', 'surface', 'url', 'http_status', 'excerpt',
                        'excerpt_sha256', 'verdict', 'reason'):
                self.assertIn(key, o, f'{o.get("id")} missing {key}')
            self.assertTrue(str(o['url']).startswith('https://'), o['id'])
            self.assertIn('usable_as_price', o)

    def test_every_excerpt_hash_matches_its_excerpt(self):
        for o in self.record['observations']:
            self.assertEqual(
                hashlib.sha256(o['excerpt'].encode('utf-8')).hexdigest(),
                o['excerpt_sha256'],
                f'{o["id"]}: excerpt and hash disagree, so the quote is not provably unchanged')

    def test_no_observation_claims_a_price_it_did_not_find(self):
        """The whole point of the sweep: nothing was fabricated."""
        for o in self.record['observations']:
            if o['two_sided_price'] is None:
                self.assertFalse(o['usable_as_price'], o['id'])

    def test_the_conclusions_admit_that_nothing_was_changed(self):
        c = self.record['conclusions']
        self.assertEqual(c['fixtures_with_a_new_two_sided_price'], 0)
        self.assertEqual(c['probabilities_changed'], 0)
        self.assertEqual(c['picks_changed'], 0)
        self.assertEqual(c['aliases_added'], 0)

    def test_every_committed_dossier_obeys_the_same_contract(self):
        """The newest record is what readers see, so it must carry the same guarantees."""
        for record in committed_records():
            with self.subTest(record=record['_record_path']):
                self.assertTrue(record.get('observations'), record['_record_path'])
                sibling = ROOT / 'data' / str(record['_record_path']).replace(
                    'direct-observations.json', 'direct-observations.md')
                self.assertTrue(sibling.is_file(), f'{record["_record_path"]} has no markdown')
                for o in record['observations']:
                    for key in ('id', 'surface', 'url', 'http_status', 'excerpt',
                                'excerpt_sha256', 'verdict', 'reason', 'usable_as_price'):
                        self.assertIn(key, o, f'{o.get("id")} missing {key}')
                    self.assertEqual(hashlib.sha256(o['excerpt'].encode('utf-8')).hexdigest(),
                                     o['excerpt_sha256'],
                                     f'{o["id"]}: excerpt and hash disagree')
                    if o['two_sided_price'] is None:
                        self.assertFalse(o['usable_as_price'], o['id'])
                c = record['conclusions']
                self.assertEqual(c['probabilities_changed'], 0, record['_record_path'])
                self.assertEqual(c['picks_changed'], 0, record['_record_path'])
                self.assertEqual(c['aliases_added'], 0, record['_record_path'])

    def test_the_scope_matches_the_runner_manifest_it_cites(self):
        manifest = json.loads((ROOT / 'data' / 'research' / 'a7128fdd'
                               / 'live-manifest.json').read_text(encoding='utf-8'))
        manifest_ids = {r['id'] for r in manifest['model_only']}
        scope_ids = {f['hotspawn_id'] for f in self.record['fixture_scope']}
        self.assertEqual(manifest_ids, scope_ids)
        self.assertEqual(len(scope_ids), self.record['conclusions']['fixtures_in_scope'])
        self.assertEqual(manifest['generated_at'],
                         self.record['live_manifest_at_research_time']['manifest_generated_at'])

    def test_the_flags_file_is_valid_and_every_flag_links_a_source(self):
        flags = json.loads(FLAGS.read_text(encoding='utf-8'))
        self.assertTrue(flags)
        for f in flags:
            for key in ('id', 'severity', 'match_ids', 'title', 'detail', 'source_urls'):
                self.assertIn(key, f, f'{f.get("id")} missing {key}')
            self.assertTrue(f['id'].startswith('a7128fdd-'))
            self.assertIn(f['severity'], {'notice', 'review'})
            self.assertTrue(f['source_urls'])
            for url in f['source_urls']:
                self.assertTrue(url.startswith('https://'), f'{f["id"]}: {url}')

    def test_the_hltv_reachability_correction_is_published_and_does_not_overstate(self):
        """A notice, not a defect: the site copy already qualifies the runner's 403."""
        flags = {f['id']: f for f in json.loads(FLAGS.read_text(encoding='utf-8'))}
        flag = flags['a7128fdd-hltv-reachable-not-403']
        self.assertEqual(flag['severity'], 'notice')
        self.assertIn('HTTP 200', flag['detail'])
        self.assertIn('the site copy is NOT wrong', flag['detail'])
        self.assertIn('no probability should have changed and none did', flag['detail'].lower()
                      .replace('So no probability should have changed and none did',
                               'no probability should have changed and none did'))

    def test_the_phantom_academy_claim_is_the_final_corrected_one(self):
        """Both earlier readings were wrong; the registry-gap one is the accurate claim."""
        flags = {f['id']: f for f in json.loads(FLAGS.read_text(encoding='utf-8'))}
        for withdrawn in ('a7128fdd-phantom-academy-opponent-conflict',
                          'a7128fdd-phantom-academy-hotspawn-corroborated'):
            self.assertNotIn(withdrawn, flags, f'{withdrawn} was withdrawn and must not come back')
        flag = flags['a7128fdd-los-kogutos-is-banda-chuya-alias-missing']
        self.assertEqual(flag['severity'], 'review')
        self.assertEqual(flag['match_ids'], ['1081605'])
        # It must own both earlier mistakes explicitly rather than bury them.
        self.assertIn('second correction', flag['detail'])
        self.assertIn('Both were wrong', flag['detail'])
        self.assertIn('there is no conflict anywhere', flag['detail'])
        self.assertIn('not in data/origination/aliases.json', flag['title'] + flag['detail'])
        self.assertIn('NOT edited here', flag['detail'])

    def test_no_flag_may_claim_an_identity_conflict_that_the_rosters_disprove(self):
        """1081605 is one match on four surfaces; no flag may *assert* it is disputed.

        Quoting a withdrawn phrase in order to own the mistake is required, not
        forbidden, so the check is that the phrase appears exactly once and only
        inside a retraction, and that the flag states the accurate conclusion.
        """
        identity = None
        for f in json.loads(FLAGS.read_text(encoding='utf-8')):
            if '1081605' not in f['match_ids']:
                continue
            self.assertNotIn('different opponent', f['title'])
            self.assertNotIn('identity conflict', f['title'].lower())
            detail = f['detail']
            self.assertLessEqual(detail.count('surfaces out of line'), 1,
                                 'the withdrawn phrase may be quoted once, as a retraction, never asserted')
            if 'surfaces out of line' in detail:
                self.assertIn("'the surfaces out of line'. Both were wrong", detail)
                identity = f
        self.assertIsNotNone(identity, 'the identity correction must stay on the record')
        self.assertEqual(identity['id'], 'a7128fdd-los-kogutos-is-banda-chuya-alias-missing')
        self.assertIn('there is no conflict anywhere', identity['detail'])

    def test_the_los_kogutos_identity_is_proved_by_roster_and_results_not_by_name(self):
        rec = json.loads(RECORD.read_text(encoding='utf-8'))
        obs = next(o for o in rec['observations']
                   if o['id'] == 'a7128fdd-bo3gg-los-kogutos-roster-identity')
        pub = obs['published']
        self.assertTrue(pub['roster_identical_case_insensitively'])
        bo3 = {p.lower() for p in pub['bo3gg_starters']}
        hltv = {p.lower() for p in pub['hltv_lineup_from_match_2399699']}
        self.assertEqual(bo3, hltv)
        self.assertEqual(len(bo3), 5)
        self.assertEqual(len(pub['matching_results']), 3)
        self.assertFalse(pub['in_alias_registry'])
        self.assertIsNone(obs['two_sided_price'])
        self.assertFalse(obs['usable_as_price'])
        self.assertEqual(obs['fixture_ids'], ['1081605'])

    def test_the_registry_gap_is_real_when_checked_against_the_registry_itself(self):
        """Pinned against the live file, so the flag goes stale visibly if it is filled."""
        registry = json.loads((ROOT / 'data' / 'origination' / 'aliases.json').read_text(encoding='utf-8'))
        aliases = {a.get('alias') for a in registry['aliases']}
        canonical = {a.get('canonical') for a in registry['aliases']}
        self.assertNotIn('los kogutos', aliases)
        self.assertNotIn('los kogutos', canonical)
        self.assertNotIn('Banda Chuya', canonical)
        self.assertNotIn('Banda chuya', aliases)

    def test_no_flag_may_call_team_abyssal_unregistered_while_the_registry_holds_it(self):
        """Pinned against the registry itself, so the correction cannot silently rot."""
        registry = json.loads((ROOT / 'data' / 'origination' / 'aliases.json').read_text(encoding='utf-8'))
        registered = {(a.get('alias'), a.get('canonical')) for a in registry['aliases']}
        self.assertIn(('Team Abyssal', 'Abyssal'), registered)
        self.assertIn(('Los Niños', 'LOS NINOS'), registered)
        flags = json.loads(FLAGS.read_text(encoding='utf-8'))
        ids = {f['id'] for f in flags}
        self.assertNotIn('a7128fdd-team-abyssal-unregistered-alias', ids)
        for f in flags:
            self.assertNotIn('is not in data/origination/aliases.json', f['detail'])
            self.assertNotIn('the alias is unregistered', f['title'].lower())
        self.assertIn('a7128fdd-team-abyssal-alias-already-registered', ids)

    def test_the_vrs_direction_divergence_is_review_and_changes_nothing(self):
        flags = {f['id']: f for f in json.loads(FLAGS.read_text(encoding='utf-8'))}
        flag = flags['a7128fdd-1081605-vrs-direction-divergence']
        self.assertEqual(flag['severity'], 'review')
        self.assertEqual(flag['match_ids'], ['1081605'])
        # It must say plainly that it did not adjudicate and did not change a value.
        self.assertIn('this session did not do', flag['detail'])
        self.assertIn('no value was changed and no', flag['detail'])

    def test_the_hltv_capture_of_2399699_binds_by_start_time_not_just_names(self):
        rec = json.loads(RECORD.read_text(encoding='utf-8'))
        obs = next(o for o in rec['observations']
                   if o['id'] == 'a7128fdd-hltv-2399699-phantom-academy')
        self.assertEqual(obs['fixture_ids'], ['1081605'])
        self.assertEqual(obs['http_status'], 200)
        self.assertTrue(obs['published']['start_agrees_with_hotspawn'])
        self.assertEqual(obs['published']['resolves_to_utc'], obs['published']['hotspawn_starts_at'])
        self.assertIsNone(obs['published']['banda_chuya']['hltv_rank'])
        self.assertIsNone(obs['two_sided_price'])
        self.assertFalse(obs['usable_as_price'])
        for side in ('phantom_academy', 'banda_chuya'):
            self.assertEqual(len(obs['published'][side]['lineup']), 5,
                             'a partial lineup must not be published as a five-player record')

    def test_no_observation_in_the_record_claims_a_price_for_the_model_only_class(self):
        rec = json.loads(RECORD.read_text(encoding='utf-8'))
        for o in rec['observations']:
            self.assertIsNone(o['two_sided_price'], o['id'])
            self.assertFalse(o['usable_as_price'], o['id'])


class VerificationRecord(unittest.TestCase):
    """The re-derivation of published probabilities from independent surfaces."""

    @classmethod
    def setUpClass(cls):
        cls.rec = json.loads((ROOT / 'data' / 'research' / 'a7128fdd'
                              / 'verification.json').read_text(encoding='utf-8'))
        cls.manifest = json.loads((ROOT / 'data' / 'research' / 'a7128fdd'
                                   / 'live-manifest.json').read_text(encoding='utf-8'))
        cls.byid = {r['id']: r for r in cls.manifest['active']}

    def test_every_row_binds_through_the_reviewed_registry(self):
        self.assertTrue(self.rec['rows'])
        self.assertEqual(self.rec['conclusions']['name_bindings_unresolved'], 0)
        for r in self.rec['rows']:
            self.assertEqual(r['name_binding'], 'resolved via data/origination/aliases.json', r['hotspawn_id'])
            for b in r['binding_detail']:
                self.assertIsNotNone(b['hotspawn_index'], f"{r['hotspawn_id']}: {b['published']} did not bind")

    def test_the_de_vig_arithmetic_is_reproducible_from_the_published_odds(self):
        for r in self.rec['rows']:
            a, b = r['odds_as_published'].values()
            ia, ib = 1.0 / a, 1.0 / b
            total = ia + ib
            self.assertAlmostEqual(r['overround'], round(total, 4), places=4, msg=r['hotspawn_id'])
            self.assertGreater(total, 1.0, 'a book with no overround is not a book')
            for side, implied in zip((ia / total, ib / total),
                                     (r['devigged'][k] for k in r['odds_as_published'])):
                self.assertAlmostEqual(side, implied, places=4, msg=r['hotspawn_id'])

    def test_the_exact_rows_really_do_match_the_published_manifest_values(self):
        exact = [r for r in self.rec['rows'] if r['exact_match']]
        self.assertGreaterEqual(len(exact), 2)
        for r in exact:
            published = self.byid[r['hotspawn_id']]['probabilities']
            self.assertEqual(r['published_probabilities'], published)
            # The manifest keeps full precision; the re-derivation is rounded to
            # four decimals, so agreement is the documented 5e-5 tolerance and
            # never an equality of floats at different precisions.
            for got, want in zip(r['devigged_aligned_to_hotspawn'], published):
                self.assertLess(abs(got - want), 5e-5, r['hotspawn_id'])

    def test_no_row_claims_exactness_it_does_not_have(self):
        for r in self.rec['rows']:
            al, pub = r['devigged_aligned_to_hotspawn'], r['published_probabilities']
            really = all(abs(x - y) < 5e-5 for x, y in zip(al, pub))
            self.assertEqual(r['exact_match'], really, r['hotspawn_id'])

    def test_it_admits_that_it_changed_nothing(self):
        self.assertEqual(self.rec['conclusions']['published_values_changed'], 0)

    def test_the_snapshot_consistency_claim_is_stated_with_its_sources(self):
        snap = self.rec['published_snapshot_verified']
        self.assertTrue(snap['agree'])
        self.assertEqual(snap['live_root_data_latest_json_generated_at'],
                         snap['live_root_page_snapshot_generated'])
        self.assertTrue(snap['source_urls'])
        for url in snap['source_urls']:
            self.assertTrue(url.startswith('https://'))

    def test_the_inventory_claim_matches_the_manifest_it_cites(self):
        inv = self.rec['inventory_verified']
        self.assertTrue(inv['agree'])
        self.assertEqual(inv['published_counts']['upcoming'], self.manifest['counts']['active'])
        self.assertIn('sport_alias=cs2', inv['hotspawn_api'])


class RenderedMarkdownIsDerived(unittest.TestCase):
    """The loader requires an .md sibling; this proves the sibling is generated."""

    def test_check_mode_passes_on_the_committed_files(self):
        from scripts.a7128fdd_render_evidence import main
        self.assertEqual(main(['--check']), 0)

    def test_regenerating_is_byte_identical(self):
        from scripts.a7128fdd_render_evidence import render_observations, render_verification
        obs = json.loads(RECORD.read_text(encoding='utf-8'))
        ver = json.loads((ROOT / 'data' / 'research' / 'a7128fdd'
                          / 'verification.json').read_text(encoding='utf-8'))
        self.assertEqual(render_observations(obs), MARKDOWN.read_text(encoding='utf-8'))
        self.assertEqual(render_verification(ver),
                         (ROOT / 'data' / 'research' / 'a7128fdd' / 'verification.md')
                         .read_text(encoding='utf-8'))

    def test_the_markdown_says_it_is_generated(self):
        self.assertIn('Generated from `direct-observations.json`', MARKDOWN.read_text(encoding='utf-8'))

    def test_the_markdown_carries_the_refused_placeholder_table(self):
        text = MARKDOWN.read_text(encoding='utf-8')
        for needle in ('1.8 / 1.8', '1.23', '2.00x / 2.00x', 'Pick a winner', 'power rating'):
            self.assertIn(needle, text)

    def test_drift_is_detected_not_rewritten_in_check_mode(self):
        import shutil
        import tempfile
        from scripts.a7128fdd_render_evidence import OUT, write
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        target = tmp / 'x.md'
        target.write_text('stale hand-written prose\n', encoding='utf-8')
        self.assertFalse(write(target, 'the derived text\n', check=True))
        self.assertEqual(target.read_text(encoding='utf-8'), 'stale hand-written prose\n',
                         '--check must not write')
        self.assertTrue(write(target, 'the derived text\n', check=False))
        self.assertEqual(target.read_text(encoding='utf-8'), 'the derived text\n')
        self.assertTrue(OUT.is_dir())


if __name__ == '__main__':
    unittest.main()


class PhoneContractWithoutABrowser(unittest.TestCase):
    """The register lands on the executive summary, which is read on a phone.

    CI renders these pages at 320/390/768/1440 px with Playwright. These checks
    are the structural half that does not need a browser: nothing in the new CSS
    may fix a width, open a nested horizontal scroll region, or leave a long
    unbroken token (a slug, a hash, a URL) able to push the page past 320 px.
    """

    @classmethod
    def setUpClass(cls):
        cls.css = (ROOT / 'assets' / 'scout.css').read_text(encoding='utf-8')
        start = cls.css.find('Session arena-a7128fdd')
        assert start != -1, 'the appended session block is missing from scout.css'
        cls.block = cls.css[start:]

    def test_the_session_css_is_appended_not_interleaved(self):
        """Append-only, so another session's rules cannot be silently reordered.

        This session appended twice (the full register, then its compact form),
        so the contract is that every occurrence sits in one contiguous region
        at the end of the file with no other session's rules inside it.
        """
        self.assertGreater(len(self.css), len(self.block))
        first, last = self.css.find('Session arena-a7128fdd'), self.css.rfind('Session arena-a7128fdd')
        self.assertGreater(last, first, 'expected both appended blocks')
        between = self.css[first:last]
        for other in ('Session 9c4b1f7a', 'Session 17d77cb3', 'Session 3016b0c6'):
            self.assertNotIn(other, between,
                             f'{other} rules were interleaved between this session\'s two blocks')
        # Everything after the first occurrence is this session's, to EOF.
        self.assertEqual(self.css[first:], self.block)

    def test_it_only_styles_the_new_register(self):
        for selector in ('.start-here', '.glance-row', '#picks-at-a-glance',
                         '.mobile-nav', '#unresolved-register'):
            self.assertNotIn(selector, self.block,
                             f'the appended block must not restyle {selector}')

    def test_no_fixed_width_and_no_nested_horizontal_scroll(self):
        self.assertNotIn('overflow-x', self.block)
        # A @media(max-width:700px) breakpoint is a query, not an element width,
        # so media lines are excluded; what must not appear is a fixed px width
        # or a min-width on an element, either of which can exceed 320 px.
        for line in self.block.splitlines():
            stripped = line.strip()
            if stripped.startswith('@media') or stripped.startswith('/*') or stripped.startswith('*'):
                continue
            for prop in ('min-width:', 'flex-basis:'):
                self.assertNotIn(prop, stripped, f'a fixed {prop} can exceed a 320 px viewport')
            for declaration in stripped.split(';'):
                if 'width:' in declaration and 'max-width:' not in declaration:
                    self.fail(f'a fixed width can exceed a 320 px viewport: {declaration.strip()}')

    def test_long_tokens_are_allowed_to_break(self):
        for selector in ('.direct-quote', '.direct-why', '.direct-scope li'):
            self.assertIn(selector, self.block)
        self.assertIn('overflow-wrap:anywhere', self.block)

    def test_a_small_screen_media_query_exists_at_the_phone_widths_ci_renders(self):
        self.assertIn('@media(max-width:700px)', self.block)

    def test_chips_may_wrap_instead_of_forcing_width(self):
        self.assertIn('.tried-chip{white-space:normal}', self.block)

    def test_the_register_renders_on_the_executive_summary_and_the_unresolved_page(self):
        """The brief asks for the unresolved section inside the executive summary.

        The summary renders the compact form and /unresolved/ the full one, which
        is the same split the summary's own compact branch applies to the source
        probe matrix and the 22-surface sweep.
        """
        summary_page, unresolved_page = ROOT / 'site' / 'index.html', ROOT / 'site' / 'unresolved' / 'index.html'
        if not (summary_page.is_file() and unresolved_page.is_file()):
            self.skipTest('the site has not been built locally')
        s = summary_page.read_text(encoding='utf-8')
        u = unresolved_page.read_text(encoding='utf-8')
        self.assertEqual(s.count('id="direct-observations"'), 1)
        self.assertEqual(u.count('id="direct-observations"'), 1)
        self.assertIn('direct-sources-compact', s)
        self.assertNotIn('direct-sources-compact', u)
        # The full per-surface evidence lives on /unresolved/, not on the phone summary.
        self.assertIn('Open the page as read', u)
        self.assertNotIn('Open the page as read', s)
        # ...and the summary links to it, so it is one tap away.
        self.assertIn('./unresolved/#direct-observations', s)


class CompactFormForThePhoneSummary(unittest.TestCase):
    """The executive summary must carry the section, not the whole register."""

    def setUp(self):
        rec = record(fixture_scope=[
            {'hotspawn_id': '1083014', 'teams': ['K27', 'Virtus.pro'],
             'competition': 'CIS LAN Championship #9', 'starts_at': '2026-10-23T13:00:00Z',
             'published_method': 'Market line'},
        ])
        rec['observations'] = [observation(), observation(id='x-2', surface='bo3.gg match centre',
                                                          url='https://bo3.gg/matches/current')]
        self.data = {'_direct_observations': rec, 'matches': [],
                     'complete_picks': {'matches': [{'id': '1083014'}]}}

    def html(self, compact):
        return direct_observation_block(self.data, './', compact=compact)

    def test_compact_is_much_shorter_than_the_full_register(self):
        self.assertLess(len(self.html(True)), len(self.html(False)) // 2)

    def test_compact_keeps_the_counts_that_matter(self):
        html = self.html(True)
        self.assertIn('<strong>0</strong> gained a two-sided price', html)
        self.assertIn('<strong>2</strong> of <strong>2</strong>', html)
        self.assertIn('<strong>0</strong> probabilities', html)

    def test_compact_names_the_in_scope_fixtures(self):
        self.assertIn('K27 vs Virtus.pro', self.html(True))

    def test_compact_links_to_the_full_register_and_the_current_picks(self):
        html = self.html(True)
        self.assertIn('./unresolved/#direct-observations', html)
        self.assertIn('./origination/#picks', html)

    def test_compact_omits_the_long_per_surface_prose(self):
        html = self.html(True)
        self.assertNotIn('Why this is not a pick input.', html)
        self.assertNotIn('Open the page as read', html)

    def test_compact_still_states_the_capture_path_and_the_observation_time(self):
        html = self.html(True)
        self.assertIn('authoring fetch path', html)
        self.assertIn('23 Oct', html)

    def test_compact_still_never_publishes_a_price_or_a_pick(self):
        for forbidden in ('pick-index', 'data-pick', 'class="pick"', 'probability-bar'):
            self.assertNotIn(forbidden, self.html(True))

    def test_compact_is_empty_without_a_record(self):
        self.assertEqual(direct_observation_block({}, './', compact=True), '')

    def test_both_forms_share_the_same_anchor_id(self):
        """One id, so the summary's link to /unresolved/#direct-observations resolves."""
        for compact in (True, False):
            self.assertIn('id="direct-observations"', self.html(compact))

    def test_the_executive_summary_still_routes_a_phone_reader_to_the_picks(self):
        built = ROOT / 'site' / 'index.html'
        if not built.is_file():
            self.skipTest('index.html has not been built locally')
        html = built.read_text(encoding='utf-8')
        self.assertIn('id="start-here"', html)
        self.assertIn('href="./#picks-at-a-glance"', html)
        self.assertIn('href="./origination/#picks"', html)
        self.assertIn('width=device-width, initial-scale=1', html)
