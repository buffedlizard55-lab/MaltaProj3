"""Session arena-dd433e7f — verification of publisher clock-pin, aliases, HLTV-first dossier, and review register."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import build, dd433e7f_probe, eea4c104_audit, originate, review_register

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / 'data' / 'research' / 'dd433e7f'


class ScopedAliasVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = originate.load_registry(ROOT / 'data' / 'origination' / 'aliases.json')

    def test_havu_gaming_resolves_in_cct_europe_series_12_and_blocks_academy(self):
        canon, used = originate.resolve_name('HAVU Gaming', self.registry, 'CCT Europe 2026 Series #12')
        self.assertEqual(canon, 'havu')
        self.assertEqual(len(used), 1)
        # Out-of-scope tournament does not match
        unscoped, used_unscoped = originate.resolve_name('HAVU Gaming', self.registry, 'Unrelated Open 2026')
        self.assertEqual(unscoped, 'havu gaming')
        self.assertEqual(used_unscoped, [])
        # Academy guard never folds into senior squad
        acad, used_acad = originate.resolve_name('HAVU Academy', self.registry, 'CCT Europe 2026 Series #12')
        self.assertEqual(acad, 'havu academy')
        self.assertEqual(used_acad, [])

    def test_the_huns_esports_resolves_in_moscow_cyber_games_and_blocks_academy(self):
        for comp in ('Moscow Cyber Games 2026', 'GLuck Moscow Cyber Games 2026'):
            canon, used = originate.resolve_name('The Huns Esports', self.registry, comp)
            self.assertEqual(canon, 'the huns', comp)
            self.assertEqual(len(used), 1, comp)
        unscoped, used_unscoped = originate.resolve_name('The Huns Esports', self.registry, 'Other Event 2026')
        self.assertEqual(unscoped, 'the huns esports')
        self.assertEqual(used_unscoped, [])
        for acad_name in ('The Huns Academy', 'The Huns Esports Academy'):
            acad, used_acad = originate.resolve_name(acad_name, self.registry, 'Moscow Cyber Games 2026')
            self.assertNotEqual(acad, 'the huns')
            self.assertEqual(used_acad, [])


class DossierAndReviewRegisterTests(unittest.TestCase):
    def test_repo_review_validates_and_is_registered_for_publication(self):
        rel = 'research/dd433e7f/repo-review.json'
        self.assertIn(rel, review_register.REGISTERS)
        doc = json.loads((ROOT / 'data' / rel).read_text(encoding='utf-8'))
        review_register.validate(doc)
        html = review_register.render(doc, '../', section_id='session-review-dd433e7f', register_path=rel)
        for item_id in ('DD43-R01', 'DD43-R02', 'DD43-R03', 'DD43-R04', 'DD43-R05', 'DD43-R06'):
            self.assertIn(f'id="review-{item_id}"', html)

    def test_hltv_first_observations_are_hash_verified_and_non_pricing(self):
        obs_json = RESEARCH_DIR / 'hltv-first-observations.json'
        obs_md = RESEARCH_DIR / 'hltv-first-observations.md'
        self.assertTrue(obs_json.is_file())
        self.assertTrue(obs_md.is_file())
        doc = json.loads(obs_json.read_text(encoding='utf-8'))
        self.assertEqual(doc['active_hotspawn_inventory_count'], 25)
        self.assertEqual(doc['hltv_match_pages_reconciled'], 25)
        self.assertEqual(len(doc['observations']), 15)
        for obs in doc['observations']:
            self.assertTrue(obs['url'].startswith('https://www.hltv.org/matches/'))
            self.assertEqual(obs['http_status'], 200)
            self.assertIsNone(obs['two_sided_price'])
            self.assertFalse(obs['usable_as_price'])
            digest = hashlib.sha256(obs['excerpt'].encode('utf-8')).hexdigest()
            self.assertEqual(obs['excerpt_sha256'], digest, obs['id'])

    def test_flags_carry_official_https_sources(self):
        flags = json.loads((RESEARCH_DIR / 'flags.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(flags), 2)
        for flag in flags:
            self.assertTrue(flag['id'].startswith('dd433e7f-'))
            self.assertIn(flag['severity'], {'notice', 'warning', 'error'})
            self.assertTrue(flag['source_urls'])
            for url in flag['source_urls']:
                self.assertTrue(eea4c104_audit.is_official(url), url)


class ReadOnlyProbeContractTests(unittest.TestCase):
    def test_originate_imports_and_wires_egw_live(self):
        self.assertTrue(hasattr(originate, 'egw_live'))
        src = (ROOT / 'scripts' / 'originate.py').read_text(encoding='utf-8')
        self.assertIn('from scripts import egw_live', src)
        self.assertIn('egw_live.load_live(evidence_dir)', src)

    def test_probe_is_read_only_and_emits_build_compatible_dossiers(self):
        probe_src = (ROOT / 'scripts' / 'dd433e7f_probe.py').read_text(encoding='utf-8')
        for forbidden in ("aliases.json').write_text", "origination.json').write_text", "latest.json').write_text"):
            self.assertNotIn(forbidden, probe_src)

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        out = tmp / 'research' / 'dd433e7f'
        orig_doc = json.loads((ROOT / 'data' / 'origination.json').read_text(encoding='utf-8'))
        fake_page = {'name': 'fake', 'url': 'https://www.hltv.org/matches', 'status': 403,
                     'teams_found': [], 'challenge_markers': ['cloudflare']}

        def fake_get(url, timeout=20):
            if 'origination.json' in url:
                return 200, orig_doc
            if 'snapshot.json' in url:
                return 200, {'generated_at': '2026-10-23T20:10:00Z'}
            if 'cloudwaysapps.com' in url:
                return 200, [{'id': 1082792, 'scheduled_start_time': 1793437200000,
                              'teams': [{'name': 'HOTU'}, {'name': 'The Huns'}],
                              'competition': {'name': 'Moscow Cyber Games 2026'}}]
            return 200, []

        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}), \
             patch.object(dd433e7f_probe, '_http_get_json', side_effect=fake_get), \
             patch.object(dd433e7f_probe.base, 'probe_page', return_value=fake_page), \
             patch.object(dd433e7f_probe.base, 'pinnacle_scan', return_value={'matchups_seen': 0, 'fixture_hits': []}), \
             patch.object(dd433e7f_probe.base, 'bo3_scan', return_value=[]):
            old_argv = sys.argv[:]
            try:
                sys.argv = ['dd433e7f_probe', '--out', str(out)]
                self.assertEqual(dd433e7f_probe.main(), 0)
            finally:
                sys.argv = old_argv

        loaded_res = build.load_no_line_research(tmp)
        loaded_cov = build.load_live_coverage(tmp)
        self.assertIsNotNone(loaded_res)
        self.assertIsNotNone(loaded_cov)
        self.assertEqual(loaded_res['_record_path'], 'research/dd433e7f/line-source-research.json')
        self.assertEqual(loaded_cov['_record_path'], 'research/dd433e7f/live-coverage.json')

    def test_committed_runner_line_research_if_present_is_selected_by_build(self):
        runner_json = RESEARCH_DIR / 'line-source-research.json'
        if not runner_json.is_file():
            self.skipTest('runner sweep not yet pulled')
        doc = json.loads(runner_json.read_text(encoding='utf-8'))
        self.assertEqual(doc['environment'], 'github-actions-runner')
        selected = build.load_no_line_research(ROOT / 'data')
        self.assertIsNotNone(selected)
        self.assertGreaterEqual(selected['observed_at'], doc['observed_at'])


if __name__ == '__main__':
    unittest.main()
