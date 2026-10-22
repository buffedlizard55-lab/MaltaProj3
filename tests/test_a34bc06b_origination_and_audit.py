"""Tests for session arena-a34bc06b: alias scope & exclusions, reference captures,
origination table + provenance + unresolved parity, and review-page flags."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

from scripts import audit_rows, build_origination, deployment_audit, originate, reference_odds

ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = ROOT / 'data/research/a34bc06b'
NOW = datetime(2026, 10, 22, 1, 20, tzinfo=timezone.utc)


class SessionA34bAliasAndReferenceTests(unittest.TestCase):
    def setUp(self):
        self.registry = originate.load_registry(ROOT / 'data/origination/aliases.json')
        self.capture = json.loads((RESEARCH_DIR / 'reference-odds.json').read_text(encoding='utf-8'))

    def test_new_stake_ranked_aliases_resolve_in_scope_and_reject_outside_or_academy(self):
        comp = 'Stake Ranked Episode 6: Closed Qualifier'
        for alias, canonical in (
            ('UNiTY esports', 'UNiTY'),
            ('Team UNiTY', 'UNiTY'),
            ('Apogee Esports', 'Apogee Betclic'),
            ('Betclic Apogee', 'Apogee Betclic'),
            ('Betclic Apogee Esports', 'Apogee Betclic'),
            ('Sangal Esports', 'Sangal'),
        ):
            name, rec = originate.resolve_name(alias, self.registry, competition=comp)
            self.assertEqual(len(rec), 1, alias)
            self.assertEqual(rec[0]['canonical'], canonical, alias)
            out_name, out_rec = originate.resolve_name(alias, self.registry, competition='Unrelated Cup 2026')
            self.assertEqual(out_rec, [])
        for excluded in ('UNiTY Academy', 'Apogee Academy', 'Sangal Alter'):
            name, rec = originate.resolve_name(excluded, self.registry, competition=comp)
            self.assertEqual(rec, [])

    def test_nodwin_and_cct_ex6666_aliases_resolve_cleanly(self):
        for comp in ('NODWIN Clutch Series #13', 'CCT Europe 2026 Series #12'):
            name, rec = originate.resolve_name('6666', self.registry, competition=comp)
            self.assertEqual(len(rec), 1)
            self.assertEqual(rec[0]['canonical'], 'ex-6666')
        for alias in ('Just_Players', 'JPlay'):
            name, rec = originate.resolve_name(alias, self.registry, competition='NODWIN Clutch Series #13')
            self.assertEqual(len(rec), 1)
            self.assertEqual(rec[0]['canonical'], 'Just Players')

    def test_session_reference_entries_and_rejected_placeholders(self):
        self.assertEqual({e['fixture_id'] for e in self.capture['entries']}, {'1079188', '1082769'})
        for entry in self.capture['entries']:
            self.assertEqual(reference_odds.problems(entry), [])
            self.assertEqual(entry['excerpt_sha256'], hashlib.sha256(entry['excerpt'].encode('utf-8')).hexdigest())
        self.assertEqual({r['fixture_id'] for r in self.capture['rejected']},
                         {'1079654', '1081596', '1082882', '1081148'})
        for rej in self.capture['rejected']:
            q, reason = reference_odds.quote(
                rej,
                {'id': rej['fixture_id'], 'starts_at': rej['starts_at'],
                 'teams': [{'name': rej['teams'][0]}, {'name': rej['teams'][1]}]},
                NOW,
            )
            self.assertIsNone(q)
            self.assertIn('rejected', reason.lower())


class OriginationTableAndProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/origination.json').read_text(encoding='utf-8'))

    def test_overview_table_renders_every_active_fixture_with_zero_source_violations(self):
        html = build_origination.page(self.data, now=NOW)
        soup = BeautifulSoup(html, 'html.parser')
        table_rows = soup.select('.picks-table tbody tr')
        self.assertEqual(len(table_rows), len(self.data['matches']))
        audit = audit_rows.audit_html(html, 'origination/index.html')
        self.assertEqual(audit['violation'], 0, audit['violations'])

    def test_network_family_never_mislabels_as_valve_official_ratings(self):
        data = copy.deepcopy(self.data)
        m = data['matches'][0]
        m['origination']['method'] = 'model'
        m['origination']['family'] = 'network'
        m['origination']['label'] = 'Research model estimate (Valve official ratings)'
        html = build_origination.pick_row(m, now=NOW)
        self.assertIn('Own network estimate (bo3.gg finished-series graph)', html)
        self.assertNotIn('Research model estimate (Valve official ratings)', html)

    def test_even_estimate_without_pick_is_listed_honestly_without_breaking_unresolved_id_parity(self):
        data = copy.deepcopy(self.data)
        for m in data['matches']:
            if m['origination'] is None:
                m['origination'] = {
                    'method': 'model', 'label': 'Valve-rating research estimate',
                    'probabilities': [0.5, 0.5], 'fair_decimal': [2.0, 2.0],
                    'observed_at': '2026-10-22T01:06:00Z', 'source': 'Valve official standings',
                    'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                }
                m['pick_index'] = None
        data['matches'][0]['origination']['probabilities'] = [0.5, 0.5]
        data['matches'][0]['pick_index'] = None
        data['counts']['unresolved'] = 0
        data['counts']['with_pick'] = sum(1 for m in data['matches'] if m['pick_index'] is not None)
        section = build_origination.section_unresolved(data)
        self.assertNotIn('All ' + str(data['counts']['active']) + ' active Hotspawn CS2 fixtures have a researched directional pick', section)
        self.assertIn('equal-probability estimate(s) without a directional side', section)
        soup = BeautifulSoup(section, 'html.parser')
        self.assertEqual([n['id'] for n in soup.select('[id^="unresolved-"]')], [])
        self.assertTrue(len(soup.select('[id^="even-"]')) >= 1)

    def test_flags_and_verification_dossier_are_valid(self):
        flags = json.loads((RESEARCH_DIR / 'flags.json').read_text(encoding='utf-8'))
        self.assertEqual(len(flags), 4)
        for item in flags:
            self.assertTrue(item['id'].startswith('a34bc06b-'))
            self.assertTrue(all(u.startswith('https://') for u in item['source_urls']))
        dossier = json.loads((RESEARCH_DIR / 'verification-audit.json').read_text(encoding='utf-8'))
        self.assertEqual(dossier['counts']['active'], 35)
        self.assertEqual(dossier['counts']['with_pick'], 35)
        self.assertEqual(dossier['counts']['unresolved'], 0)
        self.assertEqual(len(dossier['all_35_active_matches']), 35)


if __name__ == '__main__':
    unittest.main()
