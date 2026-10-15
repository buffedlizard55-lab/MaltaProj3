"""Synthetic policy tests, not production observations or results."""
import copy
import unittest
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from scripts.briefing import candidates, render, review_note

NOW = datetime(2026, 10, 15, 10, tzinfo=timezone.utc)
OBS = '2026-10-15T09:00:00Z'


class BriefingTests(unittest.TestCase):
    def example(self):
        return {'id': 'synthetic', 'teams': [{'name': '<Alpha>'}, {'name': 'Beta'}],
                'starts_at': '2026-10-15T12:00:00Z', 'locks_at': '2026-10-15T11:54:00Z',
                'availability': 'open', 'source_url': 'https://play.hotspawn.com/lobby',
                'origination': {'method': 'market', 'observed_at': OBS,
                                'probabilities': [.4, .6], 'label': 'Synthetic market',
                                'source_url': 'https://polymarket.com/esports/cs2'}}

    def select(self, matches, observed=OBS):
        return candidates(matches, NOW, observed)

    def test_money_backed_underdog_is_alternative_without_mutating_default(self):
        m = self.example()
        before = copy.deepcopy(m)
        rows = self.select([m])
        self.assertEqual(rows, [(m, 0)])
        self.assertEqual(m, before)

    def test_model_tie_large_longshot_and_missing_prices_excluded(self):
        m = self.example()
        for method, probabilities in [('model', [.4, .6]), ('market', [.5, .5]), ('market', [.15, .85])]:
            m['origination'].update(method=method, probabilities=probabilities)
            self.assertEqual(self.select([m]), [])
        m['origination'] = None
        self.assertEqual(self.select([m]), [])

    def test_stale_quote_or_inventory_never_promoted(self):
        m = self.example()
        old = '2026-10-14T09:00:00Z'
        self.assertEqual(self.select([m], old), [])
        self.assertEqual(self.select([m], None), [])
        m['origination']['observed_at'] = old
        self.assertEqual(self.select([m]), [])

    def test_locked_started_and_unknown_lock_excluded(self):
        for key, value in [('locks_at', '2026-10-15T10:00:00Z'),
                           ('starts_at', '2026-10-15T10:00:00Z'),
                           ('locks_at', None), ('availability', 'locked')]:
            m = self.example()
            m[key] = value
            self.assertEqual(self.select([m]), [])

    def test_watchlist_rows_link_to_original_sources_and_both_sides(self):
        from unittest.mock import patch
        data = {'complete_picks': {'matches': [self.example()], 'source_snapshot_at': OBS}}
        with patch('scripts.briefing.datetime') as clock:
            clock.now.return_value = NOW
            text = render(data, './')
        soup = BeautifulSoup(text, 'html.parser')
        self.assertIsNone(soup.find('alpha'))
        self.assertIn('<Alpha>', soup.get_text())
        self.assertIn('40.0%', soup.get_text())
        row = soup.select_one('tbody tr')
        self.assertEqual(len(row.select('a')), 3)
        self.assertIn('./origination/#match-synthetic', text)
        self.assertIn('not a proven edge', text)

    def test_postmortem_is_explicitly_unverified_and_does_not_invent_roster(self):
        text = review_note('../')
        self.assertIn('user-reported leads', text)
        self.assertIn('No probability adjustment', text)
        self.assertIn('not citations confirming', text)
        self.assertNotIn('2–0', text)

    def test_main_navigation_and_coverage_use_complete_feed(self):
        import json
        from pathlib import Path
        from scripts.build import summary, shell
        data = json.loads(Path('data/latest.json').read_text())
        data['complete_picks'] = json.loads(Path('data/origination.json').read_text())
        text = shell(data, 'summary', summary(data, './'), './')
        soup = BeautifulSoup(text, 'html.parser')
        self.assertEqual(soup.select_one('.hero-actions a')['href'], './origination/#picks')
        self.assertEqual(soup.select('.mobile-nav a')[1]['href'], './origination/#picks')
        self.assertIn('featured-method rejections', text)
        self.assertIsNotNone(soup.select_one('[aria-label="Complete pick coverage"]'))

    def test_official_roster_rows_replay_original_github_blobs(self):
        import json
        from pathlib import Path
        from scripts.briefing import validate_audit
        audit = json.loads(Path('data/research/day-one-audit.json').read_text())
        self.assertEqual(validate_audit(audit), audit)
        for s in audit['valve_roster_snapshots'][1:]:
            self.assertIn('Jimpphat, kyxsan, Wicadia, woxic, XANTARES', s['aurora_row'])
        audit['valve_roster_snapshots'][0]['original_markdown'] += 'tampered'
        with self.assertRaises(ValueError):
            validate_audit(audit)

    def test_inspected_postmortem_separates_secondary_result_from_primary_verification(self):
        import json
        from pathlib import Path
        audit = json.loads(Path('data/research/day-one-audit.json').read_text())
        text = review_note('../', audit)
        self.assertIn('Primary organizer result: — unverified', text)
        self.assertIn('9z beat Aurora 2–0', text)
        self.assertIn('no numerical probability adjustment', text)
        soup = BeautifulSoup(text, 'html.parser')
        self.assertEqual(len(soup.select('tbody tr')), 4)
        for row in soup.select('tbody tr'):
            self.assertIn('github.com/ValveSoftware/', row.find('a')['href'])
        reports = [a['data'] for a in audit['hltv_annotations'] if a['title'] == 'Day-one report excerpt']
        self.assertTrue(any('9z beat Aurora 2-0' in r['title'] for r in reports))
