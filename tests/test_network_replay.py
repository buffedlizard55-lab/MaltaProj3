"""Session 541cd43a — the publisher replays an own-network pick from evidence.

`scripts.build_origination.validate_origination` refuses to publish a
probability it cannot re-derive. This test runs that validator against a minimal
snapshot containing exactly one own-line network row, so the new rung cannot
ship without a working replay path (the first live run had no network row, so
this is the only place the branch is exercised).
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import network_model
from scripts.build_origination import validate_origination

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


def graph() -> tuple[list[dict], list[dict]]:
    anchors = [{'team': f'A{i}', 'points': 2200 - i * 100,
                'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'} for i in range(12)]
    edges, ident = [], 500
    names = {i: f'A{i}' for i in range(12)}
    names[90], names[91] = 'Zetta', 'LOS NINOS'
    for repeat in range(5):
        for i in range(12):
            for j in range(i + 1, 12):
                ident += 1
                edges.append({'id': ident, 'date': (NOW - timedelta(days=9 + repeat)).date().isoformat(),
                              'a': i, 'b': j, 'winner': i, 'a_name': names[i], 'b_name': names[j],
                              'parsed': 'done', 'url': f'https://bo3.gg/matches/synthetic-{ident}'})
    for k in range(8):
        for a, b, winner in ((0, 90, 0), (1, 91, 1), (90, 91, 90)):
            ident += 1
            edges.append({'id': ident, 'date': (NOW - timedelta(days=3)).date().isoformat(),
                          'a': a, 'b': b, 'winner': winner, 'a_name': names[a], 'b_name': names[b],
                          'parsed': 'done', 'url': f'https://bo3.gg/matches/synthetic-{ident}'})
    return edges, anchors


def fixture_row() -> dict:
    return {
        'id': '1082837',
        'teams': [{'id': '1', 'name': 'Zetta'}, {'id': '2', 'name': 'LOS NINOS'}],
        'competition': 'CCT South America 2026 Series #7',
        'starts_at': '2026-10-21T22:00:00Z',
        'locks_at': '2026-10-21T21:54:00Z',
        'availability': 'open',
        'tier': 'c',
        'source_url': 'https://www.hotspawn.com/matches/zetta-vs-los-ninos-1082837',
        'lobby_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1082837',
        'analysis': None, 'pick_index': None,
        'source_status': 'scheduled', 'observed_at': NOW.isoformat(),
        'best_of': None,
    }


class NetworkReplayTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / 'data'
        (self.source / 'origination' / 'evidence').mkdir(parents=True)
        shutil.copy(ROOT / 'data/origination/aliases.json', self.source / 'origination/aliases.json')
        edges, anchors = graph()
        self.document = network_model.build(edges, anchors, NOW)
        network_model.save(self.document, self.source / 'origination/evidence')
        match, _ = fixture_row(), None
        binding = {'sides': [{'name': 'Zetta', 'team_id': 90}, {'name': 'LOS NINOS', 'team_id': 91}],
                   'bridge': 'exact_team_name_lookup'}
        quote, reason = network_model.estimate_fixture(match, binding, self.document, NOW)
        assert quote, reason
        self.quote = dict(quote, method='model',
                          label='Own network estimate (bo3.gg results graph)',
                          fair_decimal=[round(1 / p, 3) for p in quote['probabilities']],
                          quotes=[quote], source='Own network model (bo3.gg results graph)',
                          model_crosscheck=None)
        row = fixture_row()
        row.update({'origination': self.quote, 'pick_index': 0 if self.quote['probabilities'][0] > 0.5 else 1,
                    'aliases_used': [], 'research': [], 'limitations': [], 'time_flags': [],
                    'featured_method': None, 'featured_probabilities': None,
                    'featured_pick_index': None, 'featured_source_url': None})
        (self.source / 'latest.json').write_text(json.dumps(
            {'inventory_observed_at': '2026-10-21T11:00:00Z', 'matches': [fixture_row()]}))
        self.data = {'source_snapshot_at': '2026-10-21T11:00:00Z',
                     'generated_at': NOW.isoformat(), 'matches': [row]}

    def test_validator_accepts_a_replayable_network_row(self):
        validate_origination(self.data, self.source)

    def test_validator_rejects_a_changed_rating(self):
        self.data['matches'][0]['origination']['inputs'][0]['points'] += 30
        with self.assertRaises(AssertionError):
            validate_origination(self.data, self.source)

    def test_validator_rejects_missing_evidence(self):
        (self.source / 'origination/evidence/live-bo3-graph.json').unlink()
        with self.assertRaises(AssertionError):
            validate_origination(self.data, self.source)


if __name__ == '__main__':
    unittest.main()
