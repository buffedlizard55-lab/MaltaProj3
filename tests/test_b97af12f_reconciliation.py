"""Session arena-b97af12f: dated reconciliation must stay sourced and honest.

These tests are deliberately offline. The runner workflow separately re-fetches
the public URLs; here we prove the checked-in dossier never invents a
probability, starts from HLTV, keeps explicit UTC starts and the API's six-minute
lock, retains the six API-only rows, and is discoverable by the build loaders.
"""
from __future__ import annotations

import json
from pathlib import Path

import tempfile
import unittest

from scripts import build
from scripts.b97af12f_reconcile import (
    API_ONLY_FIXTURES, LOBBY_FIXTURES, OUT_DIR, PUBLISHED, RESEARCH,
    build_line_research, build_live_coverage, build_reconciliation, validate,
)

MISSING_LOBBY_IDS = {
    '1079658', '1079659', '1079660', '1079661', '1081152', '1081153',
    '1081154', '1081156', '1081158',
}
API_ONLY_IDS = {row[0] for row in API_ONLY_FIXTURES}


class DatedReconciliationTests(unittest.TestCase):
    def setUp(self):
        # The production/CI test runner is unittest, with no pytest dependency.
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp_path = Path(temporary.name)

    def test_dossier_counts_and_hltv_first(self):
        recon = build_reconciliation()
        assert validate(recon) == []
        assert recon['counts']['lobby_future_cards'] == 25
        assert recon['counts']['lobby_cards_missing_from_published'] == 9
        assert recon['counts']['api_future_rows_not_rendered_in_lobby'] == 6
        assert recon['counts']['total_api_future_rows'] == 31
        assert set(recon['missing_lobby_ids']) == MISSING_LOBBY_IDS
        assert set(recon['api_only_ids']) == API_ONLY_IDS
        for fid in MISSING_LOBBY_IDS:
            assert RESEARCH[fid]['stages'][0][0] == 'HLTV first'
            assert 'hltv.org/matches/' in RESEARCH[fid]['stages'][0][1]


    def test_no_probability_or_pick_is_invented(self):
        recon = build_reconciliation()
        for fixture in recon['fixtures']:
            assert 'probability' not in fixture
            assert 'probabilities' not in fixture
            assert 'pick' not in fixture or fixture.get('pick') is None
            # The published snapshot's own stale pick is carried as a dated string,
            # explicitly labelled, never as a numeric probability.
            if fixture['in_published_snapshot']:
                assert fixture['published_pick']
                assert fixture['published_snapshot_generated_at'] == '2026-10-23T20:10:00Z'
            assert fixture['starts_at'].endswith('Z')
            assert fixture['locks_at'].endswith('Z')
            start_ms = fixture['scheduled_start_time_ms']
            # Compare the rendered lock through the same converter used to build it.
            from scripts.b97af12f_reconcile import iso_ms
            assert fixture['locks_at'] == iso_ms(start_ms - 360_000)
            assert fixture['hotspawn_url'].startswith('https://')


    def test_live_coverage_record_has_rows_and_sources(self):
        recon = build_reconciliation()
        live = build_live_coverage(recon)
        with (OUT_DIR / 'live-coverage.json').open(encoding='utf-8') as handle:
            saved = json.load(handle)
        # The dated authoring dossier is frozen; the runner is allowed to refresh
        # this separate live-coverage file without changing that historical dossier.
        if saved.get('environment') != 'github-actions-runner':
            assert saved['counts'] == live['counts']
        assert saved['counts']['live_future_fixtures'] == len(saved['live_fixtures'])
        assert len({row['id'] for row in saved['live_fixtures']}) == len(saved['live_fixtures'])
        assert saved['live_fixtures']
        assert all(row['hotspawn_url'].startswith('https://') for row in saved['live_fixtures'])
        assert all(row['starts_at'].endswith('Z') for row in saved['live_fixtures'])
        assert 'probability' not in saved
        assert 'pick' not in saved


    def test_line_research_starts_with_hltv_and_does_not_write_a_number(self):
        record = build_line_research(build_reconciliation())
        assert record['environment'] == 'agent-authoring-path'
        assert record['counts']['fixtures_researched'] == 9
        assert record['counts']['dated_external_line_leads'] == 4
        assert record['counts']['no_compliant_line'] == 5
        def keys(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    yield key
                    yield from keys(value)
            elif isinstance(obj, list):
                for value in obj:
                    yield from keys(value)

        assert not ({k.casefold() for k in keys(record)} &
                    {'probability', 'probabilities', 'pick', 'picks', 'confidence'})
        for fixture in record['per_fixture']:
            assert fixture['sources'][0]['stage'].startswith('HLTV')
            assert fixture['id'] in MISSING_LOBBY_IDS
            assert isinstance(fixture['money_line_lead'], bool)


    def test_build_loader_finds_our_live_coverage_and_runner_variant(self):
        tmp_path = self.tmp_path
        source = Path('data')
        record = build.load_live_coverage(source)
        assert record is not None
        assert record['live_fixtures']
        assert record['_record_path'].endswith('live-coverage.json')
        # Other sessions publish newer independent coverage sweeps. The loader's
        # contract is "newest dated record wins", not "B97 always wins"; B97 only
        # has to remain a parseable candidate no older than the selected record.
        ours = json.loads((OUT_DIR / 'live-coverage.json').read_text(encoding='utf-8'))
        assert ours['live_fixtures']
        if record['session'] != 'arena-b97af12f':
            assert build.timestamp(record['observed_at']) >= build.timestamp(ours['observed_at'])

        # A local authoring record must not masquerade as runner evidence. Copy our
        # research record into a temporary research tree, set the real runner flag,
        # and prove the loader's environment gate accepts only that variant.
        research = build_line_research(build_reconciliation())
        selected = build.load_no_line_research(source)
        if selected is not None and selected.get('session') == 'arena-b97af12f':
            assert selected['environment'] == 'github-actions-runner'
        fake = tmp_path / 'research' / 'b97af12f-runner'
        fake.mkdir(parents=True)
        (fake / 'line-source-research.json').write_text(json.dumps(research), encoding='utf-8')
        (fake / 'line-source-research.md').write_text('# local authoring variant\n', encoding='utf-8')
        assert build.load_no_line_research(tmp_path) is None
        research['environment'] = 'github-actions-runner'
        (fake / 'line-source-research.json').write_text(json.dumps(research), encoding='utf-8')
        (fake / 'line-source-research.md').write_text('# runner variant\n', encoding='utf-8')
        loaded = build.load_no_line_research(tmp_path)
        assert loaded is not None
        assert loaded['environment'] == 'github-actions-runner'
        assert len(loaded['per_fixture']) == 9


    def test_markdown_every_row_has_a_source_link(self):
        text = (OUT_DIR / 'reconciliation-2026-10-24.md').read_text(encoding='utf-8')
        rows = [line for line in text.splitlines() if line.startswith('| 10') and '---' not in line]
        assert len(rows) == 31
        for row in rows:
            assert 'https://' in row
            assert '| yes |' in row or '| API only |' in row or '| NO |' in row


if __name__ == '__main__':
    unittest.main()
