"""Regression for fresh-candidate versus actually-published coverage labels."""
from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

probe = importlib.import_module('scripts.2016c841_research')


class CoveragePublicationLabelTests(unittest.TestCase):
    def test_a_local_candidate_is_not_called_a_published_pick(self):
        """A fixture absent from the live site must show no published pick.

        The line sweep deliberately prefers the just-collected local
        origination. The separate public-coverage comparison must nevertheless
        read the public origination, rather than relabelling that candidate as
        already published.
        """
        fixture = {
            'id': 'candidate-only',
            'teams': ['Alpha', 'Beta'],
            'competition': 'Verified event',
            'starts_at': '2099-01-01T00:00:00Z',
            'tier': 'a',
        }
        candidate = {
            'candidate-only': {
                'method': 'model_vrs',
                'label': 'Candidate research model',
                'probability': 0.75,
                'source_url': 'https://example.test/candidate',
            }
        }
        candidate_source = {
            'source': 'local',
            'url': 'candidate.json',
            'generated_at': '2098-12-31T23:59:00Z',
        }
        session = object()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with (
                mock.patch.object(probe.requests, 'Session', return_value=session),
                mock.patch.object(probe, 'hotspawn_fixtures',
                                  return_value=([fixture], {'http_status': 200})),
                mock.patch.object(probe, 'published_methods',
                                  side_effect=lambda _s, local=None:
                                  (candidate, candidate_source) if local else ({}, {'source': 'live'})),
                mock.patch.object(probe, 'bo3_upcoming', return_value=([], [])),
                mock.patch.object(probe, 'PAGES', []),
                mock.patch.object(probe, 'healthy_methods', return_value=(True, '')),
                mock.patch.object(probe, 'smarkets_sweep', return_value=({}, {})),
                mock.patch.object(probe, 'fetch_json', return_value=(
                    {'http_status': 200},
                    {'generated_at': '2026-10-24T00:00:00Z', 'matches': []},
                )),
            ):
                self.assertEqual(probe.main(['--out', str(out),
                                             '--origination', 'candidate.json']), 0)

            coverage = json.loads((out / 'live-coverage.json').read_text())
            row = coverage['live_fixtures'][0]
            self.assertFalse(row['in_published_snapshot'])
            self.assertIsNone(row['published_pick'])
            self.assertIsNone(row['published_method'])
            markdown = (out / 'live-coverage.md').read_text()
            self.assertIn('| NO | — |', markdown)
            self.assertNotIn('75.0% (published Candidate research model)', markdown)
            self.assertIn('Candidate method (this collection)',
                          (out / 'line-source-research.md').read_text())


class RunnerEvidenceCopyTests(unittest.TestCase):
    def test_refresh_replaces_evidence_before_copying(self):
        workflow = Path('.github/workflows/89c00d8a-research.yml').read_text()
        removal = ('rm -rf data/research/89c00d8a/live/evidence '
                   'data/research/89c00d8a/live/origination-evidence')
        first_copy = 'cp -r data/evidence data/research/89c00d8a/live/evidence'
        self.assertIn(removal, workflow)
        self.assertIn(first_copy, workflow)
        self.assertLess(workflow.index(removal), workflow.index(first_copy))


if __name__ == '__main__':
    unittest.main()
