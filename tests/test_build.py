"""Static/no-JS output must not advertise an already expired current pick."""
import copy
import json
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from scripts.build import matches_table
from scripts.domain import timestamp


class StaticFreshnessTests(unittest.TestCase):
    def example(self):
        # Replayed checked-in first-party observation, not fabricated production data.
        data = json.loads(Path('data/latest.json').read_text())
        return copy.deepcopy(next(m for m in data['matches'] if m['analysis'] and m['pick_index'] is not None))

    def test_stale_static_build_demotes_pick_without_javascript(self):
        match = self.example()
        now = timestamp(match['observed_at']) + timedelta(days=3)
        with patch('scripts.build.datetime') as clock:
            clock.now.return_value = now
            text = matches_table([match], '../')
        self.assertIn('Snapshot: ', text)
        self.assertIn('not a current pick', text)
        self.assertIn('data-original=', text)

    def test_fresh_but_locked_build_demotes_pick(self):
        match = self.example()
        now = timestamp(match['starts_at'])
        match['observed_at'] = match['analysis']['observed_at'] = now.isoformat()
        with patch('scripts.build.datetime') as clock:
            clock.now.return_value = now
            text = matches_table([match], '../')
        self.assertIn('Closed for picks', text)
        self.assertIn('Snapshot: ', text)
