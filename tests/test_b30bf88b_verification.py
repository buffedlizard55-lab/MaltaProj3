"""Verification tests for session arena-b30bf88b artifacts and replay math."""
from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import reference_odds
from scripts.domain import valve_analysis
from scripts.originate import model_estimate, originate_match

ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = ROOT / 'data/research/b30bf88b'
NOW = datetime(2026, 10, 18, 1, 0, tzinfo=timezone.utc)


class B30bf88bReferenceOddsTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((RESEARCH_DIR / 'reference-odds.json').read_text(encoding='utf-8'))

    def test_accepted_entries_pass_hash_and_replay_checks(self):
        entries = self.doc['entries']
        self.assertEqual({e['fixture_id'] for e in entries}, {'1081129', '1082206', '1081519'})
        for entry in entries:
            self.assertEqual(reference_odds.problems(entry), [], entry['fixture_id'])
            self.assertEqual(
                entry['excerpt_sha256'],
                hashlib.sha256(entry['excerpt'].encode('utf-8')).hexdigest(),
            )
            fixture = {
                'id': entry['fixture_id'],
                'starts_at': entry['starts_at'],
                'locks_at': entry['starts_at'],
                'availability': 'open',
                'competition': entry['event'],
                'tier': 'c',
                'source_url': f"https://play.hotspawn.com/cs2/match/{entry['fixture_id']}",
                'lobby_url': 'https://play.hotspawn.com/cs2-pickems',
                'teams': [
                    {'id': '1', 'name': entry['teams'][0]},
                    {'id': '2', 'name': entry['teams'][1]},
                ],
            }
            quote, reason = reference_odds.quote(entry, fixture, NOW)
            self.assertIsNotNone(quote, reason)
            reference_odds.replay(entry, quote)
            result = originate_match(fixture, [], [], [], None, {'aliases': []}, NOW, reference=[entry])
            self.assertIsNotNone(result['origination'])
            self.assertEqual(result['origination']['method'], 'reference')
            self.assertEqual(result['origination']['probabilities'], entry['no_vig'])

    def test_rejected_entries_fail_closed(self):
        rejected = self.doc['rejected']
        self.assertEqual({e['fixture_id'] for e in rejected}, {'1082207', '1079181'})
        for entry in rejected:
            self.assertEqual(entry['banner_odds'], [1.8, 1.8])
            self.assertNotIn('odds', entry)
            fixture = {
                'id': entry['fixture_id'],
                'starts_at': entry['starts_at'],
                'teams': [
                    {'name': entry['teams'][0]},
                    {'name': entry['teams'][1]},
                ],
            }
            quote, reason = reference_odds.quote(entry, fixture, NOW)
            self.assertIsNone(quote)
            self.assertIn('rejected', reason.lower())


class B30bf88bTwcAndUnresolvedAuditTests(unittest.TestCase):
    def test_twc_day1_to_5_audit_matches_valve_and_hltv_facts(self):
        twc = json.loads((RESEARCH_DIR / 'twc-day1-to-5-audit.json').read_text(encoding='utf-8'))
        valve = json.loads((ROOT / 'data/evidence/valve-ratings.json').read_text(encoding='utf-8'))
        valve_by_name = {r['name']: r for r in valve['rows']}

        aurora = twc['aurora_roster_and_onboarding_context']['valve_standing_2026_10_05']
        self.assertEqual(valve_by_name['Aurora']['standing'], aurora['standing'])
        self.assertEqual(valve_by_name['Aurora']['points'], aurora['points'])
        self.assertEqual(valve_by_name['Aurora']['roster'], aurora['roster'])

        days = twc['days_1_to_4_verified_results']
        self.assertEqual([d['day'] for d in days], [1, 2, 3, 4])
        hltv_ids = [m['hltv_match_id'] for d in days for m in d['matches']]
        self.assertEqual(
            hltv_ids,
            [2399384, 2399385, 2399386, 2399387, 2399408, 2399409, 2399410, 2399411, 2399412, 2399413, 2399414, 2399415],
        )

        day5 = twc['day_5_final_day_picks_and_contrarian_plan']['fixtures']
        self.assertEqual(len(day5), 2)
        self.assertEqual(day5[0]['primary_winner_pick'], 'Falcons')
        self.assertEqual(day5[0]['contrarian_pick'], 'Aurora')
        self.assertEqual(day5[1]['primary_winner_pick'], 'FURIA')
        self.assertIsNone(day5[1]['contrarian_pick'])

    def test_unresolved_audit_and_fire_flux_vs_ex6666_valve_math(self):
        audit = json.loads((RESEARCH_DIR / 'unresolved-live-audit.json').read_text(encoding='utf-8'))
        self.assertEqual(audit['summary']['baseline_unresolved_fixtures'], 7)
        self.assertEqual(audit['summary']['newly_resolved_by_verified_sources'], 4)
        self.assertEqual(audit['summary']['remaining_fail_closed_unresolved'], 3)

        by_id = {f['fixture_id']: f for f in audit['fixtures']}
        ff = by_id['1079181']['primary_resolution']
        valve = json.loads((ROOT / 'data/evidence/valve-ratings.json').read_text(encoding='utf-8'))
        aliases = {
            'aliases': [
                {
                    'alias': '6666',
                    'canonical': 'ex-6666',
                    'applies_to': ['NODWIN Clutch Series #13'],
                }
            ]
        }
        fixture = {
            'id': '1079181',
            'starts_at': '2026-10-19T17:00:00Z',
            'competition': 'NODWIN Clutch Series #13',
            'teams': [{'name': 'Fire Flux'}, {'name': 'ex-6666'}],
        }
        meta = {
            'source_url': valve['source_url'],
            'snapshot_date': valve['snapshot_date'],
            'observed_at': '2026-10-18T00:52:00Z',
            'evidence_file': 'data/evidence/valve-ratings.json',
        }
        est, reason = model_estimate(fixture, valve['rows'], aliases, meta, NOW)
        self.assertIsNotNone(est, reason)
        self.assertEqual(est['probabilities'], ff['probabilities'])
        self.assertEqual(ff['pick'], 'ex-6666')

        unresolved_ids = {f['fixture_id'] for f in audit['fixtures'] if f['resolution_status'] == 'unresolved'}
        self.assertEqual(unresolved_ids, {'1082207', '1081861', '1081863'})

    def test_flags_conform_to_review_schema(self):
        flags = json.loads((RESEARCH_DIR / 'flags.json').read_text(encoding='utf-8'))
        self.assertEqual(len(flags), 2)
        for flag in flags:
            self.assertTrue(flag['id'].startswith('b30bf88b-'))
            self.assertIn(flag['severity'], ('notice', 'warning'))
            self.assertTrue(flag['title'])
            self.assertTrue(flag['detail'])
            self.assertTrue(all(u.startswith('https://') for u in flag['source_urls']))

    def test_repo_line_by_line_review_covers_core_modules(self):
        review = json.loads((RESEARCH_DIR / 'repo-line-by-line-review.json').read_text(encoding='utf-8'))
        self.assertEqual(review['session_id'], 'arena-b30bf88b')
        paths = {f['path'] for f in review['files_reviewed']}
        self.assertTrue(
            {'scripts/build.py', 'scripts/originate.py', 'scripts/reference_odds.py', 'scripts/audit_rows.py'}.issubset(paths)
        )
        for item in review['files_reviewed']:
            self.assertTrue((ROOT / item['path']).exists(), item['path'])
            self.assertEqual(item['status'], 'verified')


if __name__ == '__main__':
    unittest.main()
