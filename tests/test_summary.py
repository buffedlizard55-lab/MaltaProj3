"""Synthetic presentation/access-audit tests; not published source observations."""
import copy
import unittest
from bs4 import BeautifulSoup
from scripts.build import unresolved_table
from scripts.collect import record_book_check


class UnresolvedTests(unittest.TestCase):
    def match(self, availability='open'):
        return {'id': 'test', 'availability': availability, 'analysis': None,
                'teams': [{'name': 'Alpha'}, {'name': 'Beta'}], 'starts_at': None,
                'research': [], 'source_url': 'https://play.hotspawn.com/lobby'}

    def test_unknown_schedule_is_visible_and_links_to_inventory(self):
        html = unresolved_table({'matches': [self.match('unknown')]}, '../')
        self.assertIn('Scheduled start is unverified', html)
        self.assertIn('../coverage/#unknown-schedules', html)
        self.assertNotIn('Every future-start fixture', html)

    def test_past_rows_are_not_current_unresolved_picks(self):
        html = unresolved_table({'matches': [self.match('past')]}, '../')
        self.assertNotIn('Alpha', html)
        self.assertIn('not a guarantee', html)

    def test_actual_source_limitations_are_linked_and_escaped(self):
        m = self.match()
        m['research'] = [{'stage': 'Book check', 'status': 'unavailable',
                          'detail': '<unsafe> blocked', 'source_url': 'https://www.pinnacle.com/en/esports-hub/cs2'}]
        html = unresolved_table({'matches': [m]}, './')
        soup = BeautifulSoup(html, 'html.parser')
        self.assertIsNone(soup.find('unsafe'))
        self.assertIn('<unsafe> blocked', soup.get_text())
        self.assertEqual(len(soup.select('a[href*="pinnacle.com"]')), 1)
        self.assertIn('not proof', soup.get_text())

    def test_book_access_checks_never_modify_resolved_matches(self):
        missing = self.match()
        resolved = self.match()
        resolved['analysis'] = {'method': 'market'}
        before = copy.deepcopy(resolved)
        observation = {'name': 'Book check', 'url': 'https://www.pinnacle.com',
                       'status': 'unavailable', 'detail': 'Redirected, no prices verified',
                       'observed_at': '2026-10-15T08:00:00Z'}
        record_book_check([missing, resolved], observation)
        self.assertEqual(resolved, before)
        self.assertEqual(missing['research'][0]['observed_at'], observation['observed_at'])
        self.assertIsNone(missing['analysis'])
        self.assertEqual(missing['research'][0]['detail'], observation['detail'])
