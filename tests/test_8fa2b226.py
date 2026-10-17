"""Session arena-8fa2b226's published research must be wired, dated and non-authoritative.

Three separate traps are guarded here, all of them real failures this repo has already produced once:

1. a findings file under ``data/research/<session>/`` is invisible to the site unless its path is in
   the loader tuple in ``scripts/build.py`` — so the tuple is asserted directly, not inferred from a
   rendered page that might be rendering an older copy;
2. the coverage probe has to stay *outside* the decision path: a dossier that ever grew a probability,
   a pick or an applied alias would mean a blank was filled by a guess;
3. the probe step in the four-hour publisher has to be non-fatal. A blocking step whose only job is to
   explain blanks would turn a provider outage into a red deploy and stop the refresh the brief requires.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'data' / 'research' / '8fa2b226'
FLAGS = HERE / 'flags.json'
PROBE = HERE / 'coverage-probe.json'
BUILD = (ROOT / 'scripts' / 'build.py').read_text()
PAGES = (ROOT / '.github' / 'workflows' / 'pages.yml').read_text()

SEVERITIES = {'blocking', 'warning', 'notice'}


def read(path):
    return json.loads(path.read_text())


class FlagsRegisterTests(unittest.TestCase):
    def test_findings_file_is_registered_in_the_loader_tuple(self):
        # Without this the file is silently never published, however well-formed it is.
        self.assertIn("source / 'research/8fa2b226/flags.json'", BUILD)

    def test_every_flag_is_actionable_and_sourced(self):
        flags = read(FLAGS)
        self.assertTrue(flags)
        for finding in flags:
            self.assertTrue(finding['id'].startswith('8fa2b226-'), finding['id'])
            self.assertIn(finding['severity'], SEVERITIES, finding['id'])
            self.assertGreater(len(finding['title']), 20, finding['id'])
            self.assertGreater(len(finding['detail']), 120, finding['id'])
            self.assertTrue(finding['source_urls'], finding['id'])
            for url in finding['source_urls']:
                self.assertTrue(url.startswith('https://'), (finding['id'], url))
            self.assertIsInstance(finding['match_ids'], list, finding['id'])

    def test_flags_do_not_pretend_to_excuse_a_specific_blank_row(self):
        # None of this session's findings is about one fixture, so none may carry a match id.
        for finding in read(FLAGS):
            self.assertEqual(finding['match_ids'], [], finding['id'])

    def test_the_blocked_endpoints_flag_refuses_to_conclude_absence(self):
        finding = next(x for x in read(FLAGS) if x['id'] == '8fa2b226-book-endpoints-geo-blocked')
        text = finding['title'] + finding['detail']
        self.assertIn('not proof', text)
        self.assertIn('vantage', text)
        self.assertIn('No price was taken', finding['detail'])


class CoverageProbeDossierTests(unittest.TestCase):
    def test_committed_dossier_carries_no_probability_pick_or_alias(self):
        data = read(PROBE)
        self.assertEqual(data['schema_version'], 1)
        self.assertEqual(data['session'], 'arena-8fa2b226')
        self.assertTrue(data['environment'], 'a reachability record is meaningless without its vantage point')
        self.assertIn(data['mode'], ('offline-evidence-only', 'live'))
        self.assertTrue(data['environment'])
        text = json.dumps(data)
        for banned in ('"probability"', '"probabilities"', '"pick"', '"pick_index"', '"applied": true'):
            self.assertNotIn(banned, text, banned)

    def test_counts_agree_with_the_fixture_list(self):
        data = read(PROBE)
        counts = data['counts']
        fixtures = data['fixtures']
        self.assertEqual(counts['unresolved_fixtures'], len(fixtures))
        self.assertEqual(counts['with_provider_lead'], sum(1 for x in fixtures if x['provider_leads']))
        self.assertEqual(counts['display_name_only'],
                          sum(1 for x in fixtures if x['likely_blocker'] == 'display-name only'))
        self.assertTrue(data['headline'])
        for fixture in fixtures:
            self.assertTrue(fixture['source_url'], fixture['id'])
            self.assertIn(fixture['mode'] if 'mode' in fixture else fixture['likely_blocker'],
                          ('display-name only', 'listed start time', 'no provider listing found',
                           'market state or provider gap'))
            self.assertTrue(fixture['reasons'], fixture['id'])
            for lead in fixture['provider_leads']:
                self.assertTrue(lead['url'].startswith('https://'), lead['url'])
                self.assertIn(lead['strict_join'], ('names', 'time', 'matched', 'unique'), lead['strict_join'])
                self.assertTrue(lead['blocks_on'])
                self.assertIn('needs a reviewed alias' if lead['strict_join'] == 'names' else '', lead['blocks_on'])
                # A lead is a clue with a citation, never an applied change.
                self.assertTrue(lead['evidence'], 'a lead must point at the saved listing it came from')

    def test_the_publisher_runs_the_probe_and_survives_its_failure(self):
        self.assertIn('python -m scripts.coverage_probe', PAGES)
        step = PAGES.split('- name: Document why every blank')[1].split('\n      - name:')[0]
        self.assertIn('if python -m scripts.coverage_probe --live; then', step)
        self.assertIn('::warning::coverage probe failed', step, 'a probe outage must not redden the deploy')
        self.assertNotIn('continue-on-error', step, 'the branch itself must be explicit or the step name lies')

    def test_the_site_links_the_dossier_from_the_unresolved_section(self):
        data_dir = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(ROOT / 'data', data_dir / 'data')
            probe = read(PROBE)
            probe['fixtures'] = [probe_fixture()]
            probe['counts'] = {'unresolved_fixtures': 1, 'with_provider_lead': 1, 'display_name_only': 1}
            probe['headline'] = '1 blank, live fixture(s) documented'
            (data_dir / 'data/research/8fa2b226/coverage-probe.json').write_text(json.dumps(probe))
            from scripts.build import build
            build(data_dir / 'data', data_dir / 'site')
            soup = BeautifulSoup((data_dir / 'site/index.html').read_text(), 'html.parser')
            box = next(x.parent for x in soup.select('p.eyebrow') if 'Coverage probe' in x.get_text())
            text = box.get_text(' ', strip=True)
            self.assertIn('1 blank, live fixture(s) documented', text)
            self.assertIn('blocked by display-name differences alone', text)
            link = next(a for a in box.select('a') if 'coverage-probe.json' in (a.get('href') or ''))
            self.assertTrue((data_dir / 'site' / link['href'].lstrip('./')).exists())
            self.assertIn('never writes a probability', text)
        finally:
            shutil.rmtree(data_dir, ignore_errors=True)


def probe_fixture():
    return {
        'id': 'example-blank', 'teams': ['Tau', 'Upsilon'], 'competition': 'Example League',
        'starts_at': '2026-10-20T15:00:00Z', 'locks_at': '2026-10-20T15:00:00Z', 'tier': 'c',
        'source_url': 'https://www.hltv.org/events/0000/example-league',
        'reasons': ['No provider listing matched.'], 'resolution_trail': [],
        'likely_blocker': 'display-name only', 'blockers': {'identity': False, 'time': False, 'name_only': True},
        'provider_leads': [{'provider': 'HLTV', 'url': 'https://www.hltv.org/matches/2399999/tau-vs-upsilon',
                            'strict_join': 'names', 'name_similarity': 0.82, 'evidence': 'live-x.json',
                            'listed_start': '2026-10-20T15:00:00Z',
                            'alias_proposal': {'applied': False, 'provider_names': ['Tau'],
                                               'hotspawn_names': ['Tau Esports'],
                                               'evidence_url': 'https://www.hltv.org/matches/2399999/tau-vs-upsilon',
                                               'saved_listing': 'live-x.json', 'listed_start': '2026-10-20T15:00:00Z',
                                               'requires': 'a reviewed entry'}}],
    }


class CrossCheckTests(unittest.TestCase):
    """The dated TWC research must agree with an independent first-party record of the same matches."""

    def test_group_stage_record_matches_hltv_match_ids_and_its_own_sweep_count(self):
        edge = read(ROOT / 'data' / 'edge-review.json')
        record = edge['group_stage_record']
        ids = [row['hltv_match_id'] for row in record['series']]
        self.assertEqual(len(ids), len(set(ids)))
        for row in record['series']:
            self.assertTrue(row['url'].endswith(f"/{row['hltv_match_id']}/{row['slug']}"), row['url'])
            self.assertIn(row['score'], ('2-0', '2-1', '1-2', '0-2'), row)
            self.assertEqual(row['winner'], row['team_a'] if row['score'].startswith('2') else row['team_b'], row)
            self.assertEqual(row['maps_played'], sum(int(x) for x in row['score'].split('-')), row)
        self.assertEqual(record['summary']['series_completed'], len(record['series']))

    def test_the_refresh_declares_what_it_does_not_refresh(self):
        edge = read(ROOT / 'data' / 'edge-review.json')
        self.assertIn('not a live pricing feed', edge['policy'])
        limitations = json.dumps(edge['limitations']) + json.dumps(edge['session_refresh'])
        self.assertIn('keep their stated times until a later session re-reads them', limitations,
                      'the page must say which parts a refresh will not move')
        self.assertIn('No probability in the pipeline', edge['session_refresh']['not_touched'])

    def test_day_five_card_has_no_team_names_while_the_bracket_is_open(self):
        edge = read(ROOT / 'data' / 'edge-review.json')
        block = edge['day_five_card']
        self.assertTrue(block['observed_at'] and block['source_url'].startswith('https://www.hltv.org/'))
        self.assertGreaterEqual(len(block['limitations']), 2)
        for row in block['matches']:
            self.assertIsNone(row['teams'])
            self.assertIsNone(row['starts_at'])
            self.assertIsNone(row['pick'])
            self.assertIsNone(row['probabilities'])
            # A blank row still needs the official page that proves it is blank.
            self.assertTrue(row['url'].startswith('https://www.hltv.org/matches/'), row['url'])
            self.assertIn('no teams', row['status'].lower())



class BuiltSiteTests(unittest.TestCase):
    """What actually ships, from a build of this tree.

    ``site/`` is generated output and is deliberately not tracked, so these tests build their own copy in a
    temp directory instead of reading a developer's leftovers: CI runs the test step *before* the build step.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / 'data', cls.tmp / 'data')
        from scripts.build import build
        build(cls.tmp / 'data', cls.tmp / 'site')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def page(self, route):
        return BeautifulSoup((self.tmp / 'site' / route).read_text(), 'html.parser')

    def test_a_single_provider_read_is_never_rendered_as_consensus(self):
        block = self.page('edge/index.html').find(id='day-four-refresh')
        self.assertIsNotNone(block)
        text = block.get_text(' ', strip=True)
        self.assertIn('One provider only', text)
        self.assertIn('this is not consensus', text.lower(), 'a one-provider reading must deny outright')
        self.assertIn('not re-read: blank', text, 'an unread provider field renders as blank, never as a plausible id')

    def test_the_review_page_lists_every_flag_this_session_raised(self):
        text = self.page('review/index.html').get_text(' ', strip=True)
        for finding in read(FLAGS):
            self.assertIn(finding['title'][:40], text, finding['id'])

    def test_the_exec_summary_links_the_dossier_it_describes(self):
        soup = self.page('index.html')
        box = next(x.parent for x in soup.select('p.eyebrow') if 'Coverage probe' in x.get_text())
        text = box.get_text(' ', strip=True)
        self.assertIn('never writes a probability', text)
        link = next(a for a in box.select('a') if 'coverage-probe.json' in (a.get('href') or ''))
        self.assertTrue((self.tmp / 'site' / link['href'].lstrip('./')).exists(), link['href'])
        published = json.loads((self.tmp / 'site' / 'data/research/8fa2b226/coverage-probe.json').read_text())
        self.assertIn(str(published['counts']['unresolved_fixtures']), text)

    def test_the_single_provider_section_cross_checks_the_canonical_record(self):
        # Two providers' worth of numbers on one page is only honest if the page reconciles them out loud.
        edge = read(ROOT / 'data' / 'edge-review.json')
        canonical = {row['slot']: row['market']['prices'] for row in edge['day_four']}
        soup = self.page('edge/index.html')
        rows = soup.select('#day-four-refresh tbody tr')
        self.assertEqual(len(rows), len(edge['day_four_refresh']['fixtures']))
        for row, fixture in zip(rows, edge['day_four_refresh']['fixtures']):
            prices = canonical[fixture['slot']]
            text = row.get_text(' ', strip=True)
            self.assertIn('Cross-check', text)
            for name, value in prices.items():
                self.assertIn(f'{name} {value * 100:.1f}%', text, name)
            link = row.select_one('a[href="#day-four"]')
            self.assertIsNotNone(link, 'the reconciliation must be followable, not just asserted')
            self.assertTrue(soup.find(id='day-four'), 'the anchor the row links to must exist')

    def test_the_group_stage_table_links_each_series_to_its_own_page(self):
        soup = self.page('edge/index.html')
        rows = soup.select('#group-stage-series tbody tr')
        record = read(ROOT / 'data' / 'edge-review.json')['group_stage_record']['series']
        self.assertEqual(len(rows), len(record))
        for row, series in zip(rows, record):
            hrefs = [a.get('href') for a in row.select('a')]
            self.assertIn(series['url'], hrefs, series['hltv_match_id'])


class ExecutiveSummaryAnchorTests(unittest.TestCase):
    """A link the summary prints into another page must land on an anchor that page actually renders.

    This is the defect that reddened the publisher twice on 2026-10-17: the Day-4 *tournament-card lines*
    shortcut was emitted unconditionally while the TWC page renders that section only while an HLTV listing
    is unmatched to the weekly inventory. `scripts/validate.check_links` (run inside the build) turns a
    dangling in-page anchor into a failed deploy, so the generator - not the checker - has to be honest.
    """

    def setUp(self):
        self.data = json.loads((ROOT / 'data' / 'latest.json').read_text())

    def day4(self, **overrides):
        guide = {'matches': [], 'not_in_hotspawn_snapshot': [], 'lines': {'available': False}}
        guide.update(overrides)
        return guide

    def render(self, guide):
        from scripts.build import summary
        self.data['_twc_day4'] = guide
        return summary(self.data, '../')

    def test_the_shortcut_is_absent_when_the_section_will_not_render(self):
        self.assertNotIn('day-four-tournament-lines', self.render(self.day4()))

    def test_the_shortcut_is_present_when_the_section_renders(self):
        html = self.render(self.day4(not_in_hotspawn_snapshot=[{'id': 'hltv-2399414'}]))
        self.assertIn('twc-picks/#day-four-tournament-lines', html)

    def test_the_callout_still_states_the_blank_when_no_lines_are_retained(self):
        html = self.render(self.day4())
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        self.assertIn('No retained external tournament-card book yet', text)
        self.assertIn('stay blank rather than guessed', text)
        self.assertIn('twc-picks/#day-four-picks', html, 'the always-rendered sections keep their shortcuts')
        self.assertIn('twc-picks/#day-three-results', html)

    def test_the_twc_page_and_the_summary_agree_on_the_same_gate(self):
        # Both sides read one key: no second, weaker definition of "the section exists".
        from scripts import build_twc
        twc = (ROOT / 'scripts' / 'build_twc.py').read_text()
        build = (ROOT / 'scripts' / 'build.py').read_text()
        self.assertIn("if guide['not_in_hotspawn_snapshot']:", twc)
        self.assertGreaterEqual(build.count('if pending else'), 1)
        self.assertIn("pending = len(day4['not_in_hotspawn_snapshot'])", build)
        self.assertIsNotNone(build_twc.render_day4)


class RegressionGuardTests(unittest.TestCase):
    def test_verifier_reports_numbers_not_just_a_sentence(self):
        verify = (ROOT / 'scripts' / 'verify_live.py').read_text()
        self.assertIn('::error title=Public deployment verification failed::', verify)
        self.assertIn("'html_cards'", verify)
        self.assertIn("'inventory_ids'", verify)

    def test_probe_refuses_to_write_into_the_decision_path(self):
        source = (ROOT / 'scripts' / 'coverage_probe.py').read_text()
        # The probe may only ever write its own dossier file; the alias registry and the pick files are off-limits.
        for forbidden in ("aliases.json', 'w", 'aliases.json\").write_text', 'out.write_text' + "('data/origination.json'",
                          "'probabilities': [0.5, 0.5]", 'default_probability'):
            self.assertNotIn(forbidden, source)
        self.assertIn("applied': False", source, 'a proposed alias must stay visibly unapplied')

    def test_no_key_of_the_probe_dossier_resembles_an_authority(self):
        keys = set()

        def walk(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    keys.add(k)
                    walk(v)
            elif isinstance(value, list):
                for v in value:
                    walk(v)

        walk(read(PROBE))
        self.assertFalse(keys & {'pick', 'probability', 'probabilities', 'edge', 'consensus', 'confidence'})


if __name__ == '__main__':  # noqa:  allow direct execution during review
    unittest.main()
