"""Session arena-43110640: automated EGamersWorld aggregated-line capture.

The EGW rung used to depend on manual capture files and went stale after
eight hours. These tests prove the automated capture is fail-closed:
exact two-team title/alias joins plus an independent timezone-bearing provider
start, identical placeholder odds rejected by the existing reviewed gate,
stale observations rejected, and odds re-ordered to Hotspawn's team order when
the listing order differs. Missing/naive times and slug-only similarities price
nothing.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from scripts import egw_live, reference_odds

NOW = datetime(2026, 10, 24, 2, 0, tzinfo=timezone.utc)
OBSERVED = '2026-10-24T01:30:00Z'

INDEX_HTML = """
<html><body>
<a href="https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d"
   title="Ground Zero VS Off Chops"><time datetime="2026-10-26T03:00:00Z">24.10 03:00</time>
  Ground Zero 3.44 Off Chops 1.24</a>
<a href="https://egamersworld.com/counterstrike/match/EkalRNMvVx/hotu-vs-the-huns-esports-SfdtzDhiK"
   title="HOTU VS The Huns"><time datetime="2026-10-31T09:00:00Z"></time>
  HOTU 1.8 The Huns 1.8</a>
<a href="https://egamersworld.com/counterstrike/match/xx/aurora-vs-the-mongolz-yy"
   title="Aurora VS The MongolZ"><time datetime="2026-10-24T03:00:00Z"></time>
  Aurora 1.3 The MongolZ 3.27</a>
<a href="/counterstrike/match/zz/ground-zero-vs-off-chops-ww"
   title="Ground Zero VS Off Chops"><time datetime="2026-10-26T03:00:00+00:00"></time>
  Ground Zero 3.44 Off Chops 1.24</a>
<a href="https://egamersworld.com/counterstrike/teams">not a match</a>
</body></html>
"""

MATCH_GZ = {'id': '1082858', 'competition': 'DFRAG Invitational 2026',
            'starts_at': '2026-10-26T03:00:00Z',
            'teams': [{'name': 'Ground Zero'}, {'name': 'Off Chops'}]}
MATCH_HOTU = {'id': '1082792', 'competition': 'Moscow Cyber Games 2026',
              'starts_at': '2026-10-31T09:00:00Z',
              'teams': [{'name': 'HOTU'}, {'name': 'The Huns'}]}


class ParseIndex(unittest.TestCase):
    def test_only_match_anchors_with_two_odds(self):
        rows = egw_live.parse_index(INDEX_HTML)
        self.assertEqual(len(rows), 4)  # includes the relative-href listing
        self.assertTrue(all(r['url'].startswith('https://egamersworld.com/') for r in rows))
        self.assertEqual(rows[0]['odds'], [3.44, 1.24])
        self.assertEqual(rows[0]['provider_teams'], ['Ground Zero', 'Off Chops'])
        self.assertEqual(rows[0]['starts_at'], '2026-10-26T03:00:00Z')


class EntriesFor(unittest.TestCase):
    def entries(self, matches):
        return egw_live.entries_for(INDEX_HTML, matches, {'aliases': []}, OBSERVED)

    def test_exact_title_join_and_hotspawn_order(self):
        (entry,) = self.entries([MATCH_GZ])
        self.assertEqual(entry['fixture_id'], '1082858')
        self.assertEqual(entry['teams'], ['Ground Zero', 'Off Chops'])
        self.assertEqual(entry['provider_teams'], ['Ground Zero', 'Off Chops'])
        self.assertEqual(entry['starts_at'], '2026-10-26T03:00:00Z')
        self.assertEqual(entry['odds'], [3.44, 1.24])
        self.assertEqual(reference_odds.problems(entry), [])

    def test_unrelated_fixture_gets_no_entry(self):
        match = {'id': '999', 'competition': 'X', 'starts_at': '2026-10-26T03:00:00Z',
                 'teams': [{'name': 'Nope'}, {'name': 'Nada'}]}
        self.assertEqual(self.entries([match]), [])

    def test_missing_or_naive_provider_start_emits_no_entry(self):
        for value in (None, '2026-10-26T03:00:00'):
            with self.subTest(value=value):
                attribute = '' if value is None else f' datetime="{value}"'
                html = (f'<a href="https://egamersworld.com/counterstrike/match/x/'
                        f'ground-zero-vs-off-chops-y" title="Ground Zero VS Off Chops">'
                        f'<time{attribute}></time>Ground Zero 3.44 Off Chops 1.24</a>')
                self.assertEqual(egw_live.entries_for(html, [MATCH_GZ], {'aliases': []}, OBSERVED), [])

    def test_slug_substring_is_not_team_identity(self):
        html = ('<a href="https://egamersworld.com/counterstrike/match/x/'
                'ground-zero-vs-off-chops-y" title="Zero VS Chops">'
                '<time datetime="2026-10-26T03:00:00Z"></time>Zero 3.44 Chops 1.24</a>')
        self.assertEqual(egw_live.entries_for(html, [MATCH_GZ], {'aliases': []}, OBSERVED), [])

    def test_reversed_provider_title_reorders_odds_only_after_exact_join(self):
        html = INDEX_HTML.replace('Ground Zero VS Off Chops', 'Off Chops VS Ground Zero', 1)
        (entry,) = egw_live.entries_for(html, [MATCH_GZ], {'aliases': []}, OBSERVED)
        self.assertEqual(entry['provider_teams'], ['Off Chops', 'Ground Zero'])
        self.assertEqual(entry['teams'], ['Ground Zero', 'Off Chops'])
        self.assertEqual(entry['odds'], [1.24, 3.44])

    def test_quote_prices_off_chops_as_favourite(self):
        (entry,) = self.entries([MATCH_GZ])
        match = dict(MATCH_GZ, teams=[{'name': 'Ground Zero'}, {'name': 'Off Chops'}])
        quote, _reason = reference_odds.quote(entry, match, NOW)
        self.assertIsNotNone(quote)
        self.assertGreater(quote['probabilities'][1], quote['probabilities'][0])
        # no-vig of 3.44 / 1.24
        self.assertAlmostEqual(quote['probabilities'][1], 0.735, places=3)

    def test_identical_placeholder_odds_are_rejected_by_the_gate(self):
        (entry,) = self.entries([MATCH_HOTU])
        match = dict(MATCH_HOTU, teams=[{'name': 'HOTU'}, {'name': 'The Huns'}])
        quote, reason = reference_odds.quote(entry, match, NOW)
        self.assertIsNone(quote)
        self.assertIn('placeholder', reason + str(reference_odds.problems(entry)))

    def test_stale_capture_is_rejected(self):
        (entry,) = self.entries([MATCH_GZ])
        entry['observed_at'] = '2026-10-20T01:30:00Z'
        match = dict(MATCH_GZ, teams=[{'name': 'Ground Zero'}, {'name': 'Off Chops'}])
        quote, _ = reference_odds.quote(entry, match, NOW)
        self.assertIsNone(quote)

    def test_start_mismatch_is_rejected(self):
        (entry,) = self.entries([MATCH_GZ])
        match = dict(MATCH_GZ, starts_at='2026-10-26T04:00:00Z',
                     teams=[{'name': 'Ground Zero'}, {'name': 'Off Chops'}])
        quote, _ = reference_odds.quote(entry, match, NOW)
        self.assertIsNone(quote)


if __name__ == '__main__':
    unittest.main()
