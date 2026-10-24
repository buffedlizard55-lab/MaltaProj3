from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.cd37caa0_egw_audit import (BEHAVIOUR_PROGRAM, behaviour_checks,
                                        source_checks)


SAFE_ORIGINATE = '''
def run():
    reference_rows = [] + egw_live.load_live(evidence_dir, snapshot['matches'], registry)
    return reference_rows
'''
SAFE_LOADER = '''
def load_live(evidence_dir, matches, registry):
    original = read(INDEX_EVIDENCE)
    manifest = read('live-collection-manifest.json')
    replayed = entries_for(original['html'], matches, registry, original['observed_at'])
    return replayed
'''


class SourceCheckTests(unittest.TestCase):
    def root(self, originate=SAFE_ORIGINATE, loader=SAFE_LOADER):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / 'scripts').mkdir()
        (root / 'scripts/originate.py').write_text(originate)
        (root / 'scripts/egw_live.py').write_text(loader)
        self.addCleanup(temp.cleanup)
        return root

    def test_safe_wiring_and_original_replay_pass(self):
        checks = source_checks(self.root())
        self.assertEqual([check['status'] for check in checks], ['pass', 'pass'])

    def test_missing_live_loader_is_a_required_failure(self):
        checks = source_checks(self.root(originate='def run():\n    reference_rows = []\n'))
        self.assertEqual(checks[0]['id'], 'live-reference-loaded')
        self.assertEqual(checks[0]['status'], 'fail')
        self.assertTrue(checks[0]['required'])

    def test_derived_only_loader_is_a_required_failure(self):
        checks = source_checks(self.root(loader='def load_live(path):\n    return []\n'))
        self.assertEqual(checks[1]['id'], 'original-response-replay')
        self.assertEqual(checks[1]['status'], 'fail')

    def test_missing_files_fail_closed(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        checks = source_checks(Path(temp.name))
        self.assertEqual(checks[0]['status'], 'fail')


class BehaviourCheckTests(unittest.TestCase):
    def test_fail_closed_behaviour_passes_and_sibling_markup_is_visible(self):
        checks = behaviour_checks({'no_provider_time_entries': [],
                                   'substring_team_entries': [],
                                   'sibling_price_entries': []})
        self.assertEqual([check['status'] for check in checks], ['pass', 'pass', 'info'])
        self.assertIn('sibling links', checks[2]['detail'])

    def test_copied_start_and_substring_identity_are_required_failures(self):
        checks = behaviour_checks({'no_provider_time_entries': [{'id': 'bad-time'}],
                                   'substring_team_entries': [{'id': 'bad-team'}],
                                   'sibling_price_entries': []})
        self.assertEqual([check['status'] for check in checks[:2]], ['fail', 'fail'])
        self.assertTrue(all(check['required'] for check in checks[:2]))

    def test_probe_program_is_valid_python(self):
        compile(BEHAVIOUR_PROGRAM, '<cd37-egw-behaviour-probe>', 'exec')


if __name__ == '__main__':
    unittest.main()
