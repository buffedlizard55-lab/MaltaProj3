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
    """A live manifest can name fixtures the replayed snapshot predates."""

    def data(self, rendered_ids):
        return {'_direct_observations': record(fixture_scope=[
            {'hotspawn_id': '1083014', 'teams': ['K27', 'Virtus.pro'],
             'competition': 'CIS LAN Championship #9', 'starts_at': '2026-10-23T13:00:00Z',
             'published_method': 'Market line'},
            {'hotspawn_id': '9999999', 'teams': ['Not In', 'This Snapshot'],
             'competition': 'Future Series', 'starts_at': '2026-11-01T10:00:00Z',
             'published_method': 'Valve-rating research estimate'},
        ]),
            'matches': [{'id': i} for i in rendered_ids],
            'complete_picks': {'matches': []}}

    def test_a_rendered_fixture_is_linked(self):
        html = direct_observation_block(self.data(['1083014']), '../')
        self.assertIn('../origination/#match-1083014', html)

    def test_an_absent_fixture_is_never_linked_so_no_anchor_can_dangle(self):
        html = direct_observation_block(self.data(['1083014']), '../')
        self.assertNotIn('match-9999999', html)
        self.assertIn('Not In vs This Snapshot', html)

    def test_a_fixture_in_the_complete_picks_feed_also_counts_as_rendered(self):
        data = self.data([])
        data['complete_picks'] = {'matches': [{'id': '1083014'}]}
        self.assertIn('../origination/#match-1083014', direct_observation_block(data, '../'))

    def test_no_scope_list_at_all_when_the_record_has_none(self):
        html = direct_observation_block({'_direct_observations': record(fixture_scope=[]),
                                         'matches': [], 'complete_picks': None}, '../')
        self.assertNotIn('direct-scope', html)
        self.assertNotIn('In scope:', html)


class CheckedInRecord(unittest.TestCase):
    """The committed evidence must itself satisfy the contract it renders from."""

    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text(encoding='utf-8'))

    def test_the_record_and_its_markdown_both_exist(self):
        self.assertTrue(RECORD.is_file())
        self.assertTrue(MARKDOWN.is_file())

    def test_the_loader_accepts_the_committed_record(self):
        got = load_direct_observations(ROOT / 'data')
        self.assertIsNotNone(got)
        self.assertEqual(got['observed_at'], self.record['observed_at'])

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

    def test_the_hltv_reachability_correction_is_flagged_for_review(self):
        flags = {f['id']: f for f in json.loads(FLAGS.read_text(encoding='utf-8'))}
        self.assertIn('a7128fdd-hltv-reachable-not-403', flags)
        self.assertEqual(flags['a7128fdd-hltv-reachable-not-403']['severity'], 'review')

    def test_the_phantom_academy_identity_conflict_is_not_silently_joined(self):
        flags = {f['id']: f for f in json.loads(FLAGS.read_text(encoding='utf-8'))}
        flag = flags['a7128fdd-phantom-academy-opponent-conflict']
        self.assertEqual(flag['match_ids'], ['1081605'])
        self.assertIn('Banda chuya', flag['detail'])
        self.assertIn('los kogutos', flag['detail'])
        self.assertIn('NOT joined', flag['detail'])


if __name__ == '__main__':
    unittest.main()
