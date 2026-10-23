"""Unit & replay tests for session arena-92a3e9fb verification, aliases, and review artifacts."""
from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import build, originate, review_register

verify_mod = importlib.import_module('scripts.92a3e9fb_verify')
ROOT = Path(__file__).resolve().parents[1]


class Session92a3e9fbVerificationTests(unittest.TestCase):
    def test_checked_in_snapshots_pass_line_by_line_verification(self):
        res = verify_mod.verify_checked_in_snapshots(ROOT / 'data')
        self.assertEqual(res['errors'], [])
        self.assertEqual(
            res['counts']['effective_resolved_upcoming'],
            res['counts']['latest_upcoming'],
        )
        self.assertGreaterEqual(res['counts']['scoped_aliases_verified'], 56)

    def test_live_hotspawn_capture_and_bookmaker_math_replay_cleanly(self):
        inv, unres, errors = verify_mod.verify_live_hotspawn_and_research()
        self.assertEqual(errors, [])
        self.assertEqual(inv['counts']['total_cs2_records'], 92)
        self.assertEqual(inv['counts']['upcoming_open_records'], 30)
        self.assertEqual(inv['counts']['past_or_locked_records'], 62)
        self.assertTrue(unres['hotspawn_crowd_share_never_used'])
        by_id = {x['fixture_id']: x for x in unres['fixtures']}
        self.assertEqual(
            by_id['1082859']['bookmaker_quotes'][0]['no_vig_probabilities'],
            [0.5707, 0.4293],
        )
        self.assertEqual(
            by_id['1082860']['bookmaker_quotes'][0]['no_vig_probabilities'],
            [0.9231, 0.0769],
        )

    def test_new_scoped_aliases_bind_in_competition_and_reject_outside_or_academy(self):
        reg = originate.load_registry(ROOT / 'data' / 'origination' / 'aliases.json')
        cases = [
            ('FOKUS CS', 'NODWIN Clutch Series #13', 'fokus'),
            ('UNiTY esports', 'NODWIN Clutch Series #13', 'unity'),
            ('Team UNiTY', 'NODWIN Clutch Series #13', 'unity'),
            ('BakS eSports', 'NODWIN Clutch Series #13', 'baks'),
            ('INFINITE Gaming', 'NODWIN Clutch Series #13', 'infinite'),
            ('Team Brute', 'NODWIN Clutch Series #13', 'brute'),
            ('Team Brute', 'CCT Europe 2026 Series #11', 'brute'),
            ('Team Abyssal', 'DFRAG Invitational 2026', 'abyssal'),
            ('FaZe Clan', 'Tesla Cup 2026', 'faze'),
        ]
        for raw, comp, expected in cases:
            canon, used = originate.resolve_name(raw, reg, competition=comp)
            self.assertEqual(canon, expected, (raw, comp))
            self.assertTrue(used, (raw, comp))

        # Out-of-scope competitions and academy teams must NOT cross-join
        self.assertNotEqual(originate.resolve_name('FOKUS CS', reg, competition='IEM Cologne 2026')[0], 'fokus')
        self.assertNotEqual(originate.resolve_name('Team Abyssal', reg, competition='NODWIN Clutch Series #13')[0], 'abyssal')
        self.assertNotEqual(originate.resolve_name('FOKUS Academy', reg, competition='NODWIN Clutch Series #13')[0], 'fokus')
        self.assertNotEqual(originate.resolve_name('Team Brute Academy', reg, competition='NODWIN Clutch Series #13')[0], 'brute')

    def test_built_site_publishes_flags_register_and_zero_broken_links(self):
        reg = json.loads((ROOT / 'data' / 'research' / '92a3e9fb' / 'repo-review.json').read_text())
        review_register.validate(reg)
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site'
            build.build(ROOT / 'data', out)
            site_res = verify_mod.verify_built_site(out)
            self.assertEqual(site_res['errors'], [])
            self.assertEqual(site_res['row_source_violations'], 0)


if __name__ == '__main__':
    unittest.main()
