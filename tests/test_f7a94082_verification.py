import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from scripts import build, f7a94082_probe, originate, sources, twc_lines, twc_research, validate


def _sample_hotspawn_ng_state(match_id: int = 1099001) -> str:
    payload = {
        'k1': {
            's': 200,
            'u': 'https://backend.hotspawn.com/api/v1/fixtures',
            'b': [
                {
                    'id': match_id,
                    'status': 'scheduled',
                    'sport_alias': 'cs2',
                    'format': {'best_of': 3},
                    'starts_at': '2026-10-25T15:00:00Z',
                    'locks_at': '2026-10-25T14:55:00Z',
                    'tournament_name': 'CCT Season 3 Europe Series 9',
                    'teams': [
                        {'id': 9001, 'name': 'Team Alpha'},
                        {'id': 9002, 'name': 'Team Beta'},
                    ],
                }
            ],
        }
    }
    escaped = json.dumps(payload)
    return f'<html><body><h1>CS2 Picks</h1><script id="ng-state" type="application/json">{escaped}</script></body></html>'


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.manifest = []

    def json(self, url, name):
        item = self.responses[name]
        if isinstance(item, Exception):
            self.manifest.append({'id': name, 'url': url, 'status': 'error', 'error': str(item)})
            raise item
        rec = {'id': name, 'url': url, 'status': 'ok', 'sha256': 'abc123', 'observed_at': '2026-10-23T06:00:00Z'}
        self.manifest.append(rec)
        return item, rec

    def fetch(self, url, name):
        item = self.responses[name]
        if isinstance(item, Exception):
            self.manifest.append({'id': name, 'url': url, 'status': 'error', 'error': str(item)})
            raise item
        rec = {'id': name, 'url': url, 'status': 'ok', 'sha256': 'def456', 'observed_at': '2026-10-23T06:00:00Z'}
        self.manifest.append(rec)
        return item, rec

    def save(self, label, data):
        return f'data/evidence/{label}.json'


class F7a94082VerificationTests(unittest.TestCase):
    def test_hotspawn_ssr_fallback_reconciles_lobby_and_cs2_without_api(self):
        html = _sample_hotspawn_ng_state(1099001)
        client = FakeClient({
            'hotspawn-fixtures': sources.SourceError('HTTP 403 Forbidden'),
            'hotspawn-lobby': html,
            'hotspawn-cs2': html,
        })
        with mock.patch('time.sleep'):
            rows, _links, result = sources.hotspawn(client)
        self.assertEqual(result['crosscheck'], 'partial')
        self.assertEqual(result['unavailable'], ['api: HTTP 403 Forbidden'])
        self.assertEqual(result['verified_pages'], ['lobby', 'cs2'])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], 1099001)
        ok_fixtures = [m for m in client.manifest if m.get('id') == 'hotspawn-fixtures' and m.get('status') == 'ok']
        self.assertEqual(len(ok_fixtures), 1)
        self.assertEqual(ok_fixtures[0]['evidence'], 'data/evidence/hotspawn-fixtures.json')

    def test_hotspawn_fails_closed_if_only_one_ssr_surface_responds(self):
        html = _sample_hotspawn_ng_state(1099002)
        client = FakeClient({
            'hotspawn-fixtures': sources.SourceError('HTTP 403 Forbidden'),
            'hotspawn-lobby': html,
            'hotspawn-cs2': sources.SourceError('HTTP 503 Service Unavailable'),
        })
        with mock.patch('time.sleep'), self.assertRaises(sources.SourceError):
            sources.hotspawn(client)

    def test_resolve_match_preserves_full_research_trail_and_time_flags_for_featured_model(self):
        match = {
            'id': 1082999,
            'source_url': 'https://play.hotspawn.com/lobby/match/1082999',
            'teams': [{'name': 'Alpha'}, {'name': 'Beta'}],
            'pick_index': 0,
            'research': [
                {'stage': 'featured_valve_model', 'status': 'priced', 'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_21.md'},
            ],
            'analysis': {
                'method': 'model',
                'source': 'valve_standings',
                'probabilities': [58.4, 41.6],
                'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_21.md',
                'quotes': [],
            },
        }
        fake_trail = {
            'origination': {'method': 'model'},
            'research': [
                {'stage': 'hltv', 'status': 'checked-blocked', 'source_url': 'https://www.hltv.org/matches', 'note': 'HTTP 403'},
                {'stage': 'bo3', 'status': 'matched', 'source_url': 'https://bo3.gg/matches/alpha-vs-beta-23-10-2026', 'note': 'Bound BO3 series without two-sided moneyline'},
                {'stage': 'valve_model', 'status': 'priced', 'source_url': match['analysis']['source_url'], 'note': 'Global #24 vs #41'},
            ],
            'time_flags': [{'kind': 'bo3-time-gap', 'minutes': 45}],
        }
        now = f7a94082_probe.timestamp('2026-10-23T06:00:00Z')
        with mock.patch.object(originate, 'originate_match', return_value=fake_trail):
            kept = originate.resolve_match(match, [], [], [], {}, {}, now)
        self.assertEqual(kept['research'], match['research'])
        stages = [c['stage'] for c in kept['alias_research']]
        self.assertEqual(stages, ['hltv', 'bo3', 'valve_model'])
        self.assertEqual(kept['origination']['probabilities'], [58.4, 41.6])
        self.assertEqual(kept['pick_index'], 0)
        self.assertEqual(kept['time_flags'], [{'kind': 'bo3-time-gap', 'minutes': 45}])

    def test_f7a94082_probe_challenge_guard_and_load_no_line_research_schema(self):
        cf_html = '<html><head><title>Just a moment...</title></head><body>cf-mitigated challenge-platform</body></html>'
        self.assertIsNotNone(f7a94082_probe.detect_challenge(403, cf_html, {'cf-mitigated': 'challenge'}))
        visible = f7a94082_probe.visible_text_from_html(
            '<html><style>.color{color:red}</style><body>Visible words only<script id="ng-state">{"popularPickPercentage":91}</script></body></html>'
        )
        self.assertEqual(visible, 'Visible words only')
        self.assertNotIn('popularPickPercentage', visible)
        self.assertEqual(
            f7a94082_probe.find_teams_in_visible_text(
                200, None, 'Choose a background color theme', ['Color', 'Team opponent'], [('Color', 'Team opponent')]
            ),
            [],
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'data/research/f7a94082'
            out.mkdir(parents=True)
            sample_latest = json.loads(Path('data/latest.json').read_text())
            sample_orig = json.loads(Path('data/origination.json').read_text())
            with (
                mock.patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}),
                mock.patch.object(
                    f7a94082_probe,
                    'probe_surface',
                    side_effect=lambda sess, name, url, kind, *a, **kw: {
                        'name': name, 'url': url, 'kind': kind, 'http': 403 if kind == 'hltv' else 200,
                        'challenge': 'cloudflare:challenge' if kind == 'hltv' else None, 'teams_found': [], 'error': None,
                    },
                ),
                mock.patch.object(
                    f7a94082_probe,
                    'probe_pinnacle_cs2',
                    return_value={'url': 'https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups/highlighted', 'http': 200, 'cs2_leagues': 42, 'cs2_prematch_series': 14, 'priced_series': 11, 'rows': [], 'error': None},
                ),
                mock.patch.object(
                    f7a94082_probe,
                    'probe_smarkets_cs2',
                    return_value={'url': 'https://api.smarkets.com/v3/events/', 'http': 200, 'events_count': 8, 'two_sided_count': 8, 'rows': [], 'error': None},
                ),
                mock.patch.object(
                    f7a94082_probe,
                    'probe_bo3_upcoming',
                    return_value={'url': 'https://api.bo3.gg/api/v1/matches', 'http': 200, 'matches_count': 100, 'with_two_sided_bet': 4, 'rows': [], 'error': None},
                ),
            ):
                rec = f7a94082_probe.build_sweep_record(sample_latest, sample_orig, requests.Session(), timeout=5)
            (out / 'line-source-research.json').write_text(json.dumps(rec, indent=2) + '\n')
            (out / 'line-source-research.md').write_text(f7a94082_probe.render_markdown(rec))
            loaded = build.load_no_line_research(root / 'data')
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded['session'], 'arena-f7a94082')
            self.assertIsInstance(loaded['per_fixture'], list)

    def test_caches_detect_mutation_and_isolate_deep_copies(self):
        now = f7a94082_probe.timestamp('2026-10-16T09:00:00Z')
        res1 = twc_lines.load(Path('data/research/twc-current'), now)
        res1['mutated_test_key'] = 'dirty'
        res2 = twc_lines.load(Path('data/research/twc-current'), now)
        self.assertNotIn('mutated_test_key', res2)

        r1 = twc_research.load(Path('data/research/twc-current'))
        r1['mutated_test_key'] = 'dirty'
        r2 = twc_research.load(Path('data/research/twc-current'))
        self.assertNotIn('mutated_test_key', r2)

    def test_wcag_link_and_target_size_css_rules_present(self):
        scout = Path('assets/scout.css').read_text()
        self.assertNotIn('data-method=\\"market\\"', scout)
        self.assertRegex(scout, r'\.ladder-list a\s*\{[^}]*text-decoration:\s*underline')
        self.assertRegex(scout, r'\.prose a\s*\{[^}]*text-decoration:\s*underline')
        for css_path in ('assets/scout.css', 'assets/origination.css', 'assets/strategy.css'):
            css = Path(css_path).read_text()
            self.assertIn('min-height: 24px', css)
            self.assertIn('min-width: 24px', css)


if __name__ == '__main__':
    unittest.main()
