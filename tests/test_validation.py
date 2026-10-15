"""Displayed source details must replay too, not merely the final percentages."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.validate import check_data


class CompleteAnalysisReplayTests(unittest.TestCase):
    def mutate(self, change):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'data'
            shutil.copytree('data', target)
            snapshot = json.loads((target / 'latest.json').read_text())
            change(snapshot)
            (target / 'latest.json').write_text(json.dumps(snapshot))
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, 'complete first-party replay'):
                    check_data(target)

    def test_altered_displayed_bid_is_rejected_even_with_unchanged_probability(self):
        def change(snapshot):
            analysis = next(m['analysis'] for m in snapshot['matches'] if m['analysis'] and m['analysis']['method'] == 'market')
            analysis['quotes'][0]['bid'] += .001
        self.mutate(change)

    def test_relabeling_uncalibrated_model_as_verified_odds_is_rejected(self):
        def change(snapshot):
            analysis = next(m['analysis'] for m in snapshot['matches'] if m['analysis'] and m['analysis']['method'] == 'model')
            analysis['label'] = 'Verified bookmaker odds'
        self.mutate(change)
