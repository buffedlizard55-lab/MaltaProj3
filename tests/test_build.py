"""Static/no-JS output must not advertise an already expired current pick."""
import copy
import json
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from scripts.build import matches_table, picks
from scripts.domain import timestamp


class StaticFreshnessTests(unittest.TestCase):
    def example(self):
        # Replayed checked-in first-party observation, not fabricated production data.
        data = json.loads(Path('data/latest.json').read_text())
        match = next((m for m in data['matches'] if m['analysis'] and m['pick_index'] is not None), None)
        if match is None:
            self.skipTest('Retained snapshot contains no supported choices to test')
        return copy.deepcopy(match)

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


    def test_unknown_schedule_remains_in_full_picks_list_and_unresolved_filter(self):
        from scripts.collect import counts
        from bs4 import BeautifulSoup
        data = json.loads(Path('data/latest.json').read_text())
        match = copy.deepcopy(data['matches'][0])
        match.update(starts_at=None, locks_at=None, availability='unknown', analysis=None, pick_index=None, research=[])
        data['matches'] = [match]
        data['counts'] = counts(data['matches'])
        soup = BeautifulSoup(picks(data, '../'), 'html.parser')
        self.assertEqual(len(soup.select('#match-list > tbody > tr')), 1)
        self.assertIn('unverified', soup.select_one('.match-cell').get_text())
        self.assertIn('1', soup.select_one('[data-basis="unresolved"]').get_text())
        self.assertEqual(len(soup.select('#unresolved .unresolved-table > tbody > tr')), 1)
