"""Unit & integration tests for session arena-b2264c65 verification, aliases, and reference-odds captures."""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import audit_rows, b2264c65_verify, build, originate, reference_odds

UTC = timezone.utc
ROOT = Path(__file__).resolve().parent.parent


class SessionB2264C65VerificationTests(unittest.TestCase):
    def test_verify_all_dossiers_aliases_and_published_replay(self):
        summary = b2264c65_verify.verify_all(ROOT)
        self.assertEqual(summary['dossiers']['reference_entries'], 4)
        self.assertEqual(summary['dossiers']['reference_rejected'], 15)
        self.assertEqual(summary['dossiers']['live_coverage_fixtures'], 19)
        self.assertEqual(summary['dossiers']['observations'], 6)
        self.assertEqual(summary['dossiers']['flags'], 5)
        self.assertEqual(summary['aliases']['aliases_verified'], 5)
        self.assertGreaterEqual(summary['published']['snapshot_past'], 60)

    def test_fresh_b2264c65_egw_captures_resolve_inside_8h_gate_and_reject_placeholders(self):
        now = datetime(2026, 10, 26, 1, 15, tzinfo=UTC)
        loaded_ref = reference_odds.load(ROOT / 'data')
        ref_rows = list(loaded_ref['entries']) + list(loaded_ref['rejected'])

        valid_cases = [
            ('1082858', '2026-10-26T03:00:00Z', 'DFRAG Invitational 2026', ['Ground Zero', 'Off Chops'], 1, [0.26495726, 0.73504274]),
            ('1082859', '2026-10-26T03:00:00Z', 'DFRAG Invitational 2026', ['NEXVOID', 'Alter Ego'], 0, [0.58151885, 0.41848115]),
            ('1082860', '2026-10-27T03:00:00Z', 'DFRAG Invitational 2026', ['FlyQuest', 'Staqued'], 0, [0.92184245, 0.07815755]),
            ('1082901', '2026-10-27T20:00:00Z', 'Tesla Cup 2026', ['Envy', 'GamerLegion'], 1, [0.48070175, 0.51929825]),
        ]
        for fid, starts_at, comp, teams, exp_pick, exp_probs in valid_cases:
            match = {
                'id': fid,
                'starts_at': starts_at,
                'locks_at': starts_at,
                'availability': 'open',
                'competition': comp,
                'tier': 'b',
                'source_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{fid}',
                'lobby_url': 'https://play.hotspawn.com/lobby',
                'teams': [{'id': '1', 'name': teams[0]}, {'id': '2', 'name': teams[1]}],
            }
            res = originate.originate_match(match, [], [], {}, {}, {'aliases': []}, now, reference=ref_rows)
            orig = res.get('origination') or {}
            self.assertEqual(orig.get('method'), 'reference', fid)
            self.assertEqual(res.get('pick_index'), exp_pick, fid)
            for got_p, exp_p in zip(orig['probabilities'], exp_probs):
                self.assertAlmostEqual(got_p, exp_p, places=7, msg=fid)

        # Placeholder 1.8/1.8 page (1081159) and prose-less page (1079201) stay unresolved on reference rung
        for fid, starts_at, comp, teams in (
            ('1081159', '2026-10-26T12:00:00Z', 'CCT Europe 2026 Series #12', ['LFO 10', 'ex-6666']),
            ('1079201', '2026-10-26T09:00:00Z', 'NODWIN Clutch Series #13', ['INOX Division', 'Nemesis']),
        ):
            match = {
                'id': fid,
                'starts_at': starts_at,
                'locks_at': starts_at,
                'availability': 'open',
                'competition': comp,
                'tier': 'c',
                'source_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{fid}',
                'lobby_url': 'https://play.hotspawn.com/lobby',
                'teams': [{'id': '1', 'name': teams[0]}, {'id': '2', 'name': teams[1]}],
            }
            res = originate.originate_match(match, [], [], {}, {}, {'aliases': []}, now, reference=ref_rows)
            self.assertIsNone(res.get('origination'), fid)

    def test_1079201_upgrades_from_featured_model_to_first_party_bovada_moneyline(self):
        now = datetime(2026, 10, 26, 1, 15, tzinfo=UTC)
        registry = originate.load_registry(ROOT / 'data' / 'origination' / 'aliases.json')
        match = {
            'id': '1079201',
            'starts_at': '2026-10-26T09:00:00Z',
            'locks_at': '2026-10-26T08:54:00Z',
            'availability': 'open',
            'competition': 'NODWIN Clutch Series #13',
            'tier': 'c',
            'source_url': 'https://www.hotspawn.com/matches/inox-division-vs-nemesis-nodwin-clutch-series-13-1079201',
            'lobby_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1079201',
            'teams': [{'id': '1', 'name': 'INOX Division'}, {'id': '2', 'name': 'Nemesis'}],
            'analysis': {
                'method': 'model',
                'label': 'Research model estimate (Valve official ratings)',
                'probabilities': [0.12346675, 0.87653325],
                'source': 'Valve official regional standings',
                'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                'quotes': [],
            },
            'pick_index': 1,
        }
        bovada_row = {
            'family': 'bookmaker',
            'provider': 'Bovada',
            'names': ['Team Nemesis', 'INOX Division'],
            'start': '2026-10-26T09:00:00Z',
            'odds': [1.363636, 3.0],
            'event_id': '32756569',
            'market_id': '539110949',
            'source_url': 'https://www.bovada.lv/sports/esports/counter-strike-2/nodwin-clutch-series/team-nemesis-inox-division-202610260500',
            'evidence_file': 'data/origination/evidence/live-bovada-cs2.json',
            'observed_at': '2026-10-26T01:04:30Z',
        }
        res = originate.resolve_match(match, [], [bovada_row], [], {}, registry, now)
        self.assertTrue(res.get('upgraded_from_featured_model'))
        self.assertEqual(res['origination']['method'], 'bookmaker')
        self.assertEqual(res['pick_index'], 1)
        self.assertAlmostEqual(res['origination']['probabilities'][0], 0.3125, places=5)
        self.assertAlmostEqual(res['origination']['probabilities'][1], 0.6875, places=5)

    def test_off_chops_luminosity_and_envy_scoped_aliases_bind_thunderpick_cleanly(self):
        now = datetime(2026, 10, 26, 1, 15, tzinfo=UTC)
        registry = originate.load_registry(ROOT / 'data' / 'origination' / 'aliases.json')
        cases = [
            ('1082858', '2026-10-26T03:00:00Z', 'DFRAG Invitational 2026', ['Ground Zero', 'Off Chops'],
             ['Ground Zero', 'THUNDERdOWNUNDER'], [3.5, 1.25], 1),
            ('1082900', '2026-10-27T17:00:00Z', 'Tesla Cup 2026', ['Luminosity', 'HOTU'],
             ['Luminosity Gaming', 'HOTU'], [1.75, 1.95], 0),
            ('1082901', '2026-10-27T20:00:00Z', 'Tesla Cup 2026', ['Envy', 'GamerLegion'],
             ['Team Envy', 'GamerLegion'], [1.92, 1.78], 1),
        ]
        for fid, starts_at, comp, teams, tp_names, odds, exp_pick in cases:
            match = {
                'id': fid,
                'starts_at': starts_at,
                'locks_at': starts_at,
                'availability': 'open',
                'competition': comp,
                'tier': 'b',
                'source_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{fid}',
                'lobby_url': 'https://play.hotspawn.com/lobby',
                'teams': [{'id': '1', 'name': teams[0]}, {'id': '2', 'name': teams[1]}],
            }
            tp_row = {
                'family': 'bookmaker',
                'provider': 'Thunderpick',
                'names': tp_names,
                'start': starts_at,
                'odds': odds,
                'event_id': f'tp-{fid}',
                'source_url': 'https://thunderpick.io/api/matches',
                'evidence_file': 'data/evidence/thunderpick-cs2.json',
                'observed_at': '2026-10-26T01:04:30Z',
            }
            res = originate.originate_match(match, [], [tp_row], {}, {}, registry, now)
            self.assertEqual(res['origination']['method'], 'bookmaker', fid)
            self.assertEqual(res['pick_index'], exp_pick, fid)

    def test_live_coverage_and_flags_have_no_percent_leak_and_official_sources(self):
        cov = json.loads((ROOT / 'data/research/b2264c65/live-coverage.json').read_text(encoding='utf-8'))
        html = build.live_coverage_gaps({'matches': [], 'complete_picks': {'matches': []}, '_live_coverage': cov}, '')
        self.assertNotIn('%', html)
        flags = json.loads((ROOT / 'data/research/b2264c65/flags.json').read_text(encoding='utf-8'))
        for fl in flags:
            for u in fl['source_urls']:
                self.assertTrue(audit_rows.is_official(u), u)


if __name__ == '__main__':
    unittest.main()
