"""Session arena-c6b8d58b — 31/31 Hotspawn + 31/31 HLTV match-page reconciliation,
EGW bookmaker-average capture across the 13 model-only fixtures, and scoped SA aliases."""
from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import build, eea4c104_audit, originate, reference_odds, review_register

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / 'data' / 'research' / 'c6b8d58b'
NOW = datetime(2026, 10, 24, 6, 55, tzinfo=timezone.utc)
SA_IDS = {'1083120', '1083121', '1082695', '1083122', '1083140', '1083123'}


class ScopedSouthAmericaAliasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = originate.load_registry(ROOT / 'data' / 'origination' / 'aliases.json')

    def test_gremio_esports_resolves_in_cct_sa_series_7_and_blocks_academy(self):
        comp = 'CCT South America 2026 Series #7'
        canon, used = originate.resolve_name('Gremio Esports', self.registry, comp)
        self.assertEqual(canon, 'grêmio')
        self.assertEqual(len(used), 1)
        out_canon, out_used = originate.resolve_name('Gremio Esports', self.registry, 'Unrelated Event 2026')
        self.assertEqual(out_canon, 'gremio esports')
        self.assertEqual(out_used, [])
        for acad in ('Gremio Academy', 'Gremio Esports Academy'):
            acad_canon, acad_used = originate.resolve_name(acad, self.registry, comp)
            self.assertNotEqual(acad_canon, 'grêmio')
            self.assertEqual(acad_used, [])

    def test_isurus_gaming_resolves_in_cct_sa_series_7_and_blocks_academy(self):
        comp = 'CCT South America 2026 Series #7'
        canon, used = originate.resolve_name('Isurus Gaming', self.registry, comp)
        self.assertEqual(canon, 'isurus')
        self.assertEqual(len(used), 1)
        out_canon, out_used = originate.resolve_name('Isurus Gaming', self.registry, 'Unrelated Event 2026')
        self.assertEqual(out_canon, 'isurus gaming')
        self.assertEqual(out_used, [])
        for acad in ('Isurus Academy', 'Isurus Gaming Academy'):
            acad_canon, acad_used = originate.resolve_name(acad, self.registry, comp)
            self.assertNotEqual(acad_canon, 'isurus')
            self.assertEqual(acad_used, [])

    def test_tropa_do_kingui_carries_quarterfinal_2399913_and_1083121_evidence(self):
        comp = 'CCT South America 2026 Series #7'
        canon, used = originate.resolve_name('Tropa do KinGui', self.registry, comp)
        self.assertEqual(canon, 'projeto do kingui')
        self.assertEqual(len(used), 1)
        urls = {ev['url'] for ev in used[0]['evidence']}
        self.assertIn('https://www.hltv.org/matches/2399913/tropa-do-kingui-vs-meia-noite-cct-2026-south-america-series-7', urls)
        self.assertIn('https://www.hotspawn.com/matches/projeto-do-kingui-vs-meia-noite-cct-south-america-2026-series-7-1083121', urls)


class CompleteLiveCoverageAndHltvReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cov = json.loads((RESEARCH_DIR / 'live-coverage.json').read_text(encoding='utf-8'))
        cls.obs = json.loads((RESEARCH_DIR / 'hltv-first-observations.json').read_text(encoding='utf-8'))

    def test_every_31_live_fixture_has_both_hotspawn_and_hltv_match_links(self):
        self.assertTrue((RESEARCH_DIR / 'live-coverage.md').is_file())
        fixtures = self.cov['live_fixtures']
        self.assertEqual(len(fixtures), 31)
        self.assertEqual(self.cov['counts']['live_future_fixtures'], 31)
        self.assertEqual(self.cov['counts']['hltv_match_pages_verified'], 31)
        seen_ids = set()
        for f in fixtures:
            fid = str(f['id'])
            seen_ids.add(fid)
            self.assertTrue(f['hotspawn_url'].startswith('https://www.hotspawn.com/matches/'), fid)
            self.assertTrue(f['hotspawn_url'].endswith('-' + fid), fid)
            self.assertIsNotNone(f.get('hltv_url'), f'{fid} missing hltv_url')
            self.assertTrue(f['hltv_url'].startswith('https://www.hltv.org/matches/'), fid)
        self.assertTrue(SA_IDS.issubset(seen_ids))

    def test_loader_selects_complete_record_and_renders_hltv_links_for_all_missing_rows(self):
        selected = build.load_live_coverage(ROOT / 'data')
        self.assertIsNotNone(selected)
        self.assertGreaterEqual(selected['observed_at'], self.cov['observed_at'])
        snap_ids = [f['id'] for f in self.cov['live_fixtures'] if f['in_published_snapshot']]
        data = {
            'matches': [{'id': str(i), 'teams': [{'name': f'A{i}'}, {'name': f'B{i}'}]} for i in snap_ids],
            'complete_picks': {'matches': []},
            '_live_coverage': self.cov,
        }
        html = build.live_coverage_gaps(data, '')
        self.assertIn('15 missing at that observation', html)
        for f in self.cov['live_fixtures']:
            if not f['in_published_snapshot']:
                self.assertIn(f['hotspawn_url'], html)
                self.assertIn(f['hltv_url'], html)

    def test_hltv_first_observations_are_31_of_31_and_hash_verified(self):
        self.assertTrue((RESEARCH_DIR / 'hltv-first-observations.md').is_file())
        self.assertEqual(self.obs['active_hotspawn_inventory_count'], 31)
        self.assertEqual(self.obs['hltv_match_pages_reconciled'], 31)
        self.assertEqual(len(self.obs['observations']), 21)
        observed_fids = {o['fixture_ids'][0] for o in self.obs['observations']}
        self.assertTrue(SA_IDS.issubset(observed_fids))
        for o in self.obs['observations']:
            self.assertTrue(o['url'].startswith('https://www.hltv.org/matches/'))
            self.assertEqual(o['http_status'], 200)
            self.assertIsNone(o['two_sided_price'])
            self.assertFalse(o['usable_as_price'])
            digest = hashlib.sha256(o['excerpt'].encode('utf-8')).hexdigest()
            self.assertEqual(o['excerpt_sha256'], digest, o['id'])


class ReviewedReferenceOddsAndRegisterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = json.loads((RESEARCH_DIR / 'reference-odds.json').read_text(encoding='utf-8'))

    def test_seven_egw_entries_validate_quote_and_replay_cleanly(self):
        entries = self.ref['entries']
        self.assertEqual(
            {e['fixture_id'] for e in entries},
            {'1083122', '1082858', '1082996', '1079198', '1079200', '1082861', '1082792'},
        )
        for entry in entries:
            self.assertEqual(reference_odds.problems(entry), [], entry['fixture_id'])
            fixture = {
                'id': entry['fixture_id'],
                'starts_at': entry['starts_at'],
                'teams': [{'name': entry['teams'][0]}, {'name': entry['teams'][1]}],
            }
            quote, reason = reference_odds.quote(entry, fixture, NOW)
            self.assertIsNotNone(quote, f"{entry['fixture_id']}: {reason}")
            reference_odds.replay(entry, quote)

    def test_six_equal_side_placeholders_are_rejected(self):
        rejected = self.ref['rejected']
        self.assertEqual(
            {r['fixture_id'] for r in rejected},
            {'1081152', '1081153', '1081154', '1081156', '1081158', '1082793'},
        )
        for rej in rejected:
            self.assertEqual(rej['excerpt_sha256'], hashlib.sha256(rej['excerpt'].encode('utf-8')).hexdigest())
            fixture = {
                'id': rej['fixture_id'],
                'starts_at': rej['starts_at'],
                'teams': [{'name': rej['teams'][0]}, {'name': rej['teams'][1]}],
            }
            quote, reason = reference_odds.quote(rej, fixture, NOW)
            self.assertIsNone(quote)
            self.assertIn('rejected', reason.lower())

    def test_flags_and_repo_review_validate_and_render(self):
        flags = json.loads((RESEARCH_DIR / 'flags.json').read_text(encoding='utf-8'))
        self.assertEqual(len(flags), 4)
        for flag in flags:
            self.assertTrue(flag['id'].startswith('c6b8d58b-'))
            self.assertIn(flag['severity'], {'notice', 'warning', 'error'})
            self.assertTrue(flag['source_urls'])
            for url in flag['source_urls']:
                self.assertTrue(eea4c104_audit.is_official(url), url)

        rel = 'research/c6b8d58b/repo-review.json'
        self.assertIn(rel, review_register.REGISTERS)
        doc = json.loads((ROOT / 'data' / rel).read_text(encoding='utf-8'))
        review_register.validate(doc)
        html = review_register.render(doc, '../', section_id='session-review-c6b8d58b', register_path=rel)
        for item_id in ('C6B8-R01', 'C6B8-R02', 'C6B8-R03', 'C6B8-R04'):
            self.assertIn(f'id="review-{item_id}"', html)


if __name__ == '__main__':
    unittest.main()
