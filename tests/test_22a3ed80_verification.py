"""Session arena-22a3ed80: the published executive summary must reconcile with
the snapshot it says it was built from.

``scripts/22a3ed80_verify.py`` re-derives every featured pick and both of its
percentages from the fixture's own ``analysis`` block, checks that every active
fixture has exactly one glance row with an https source link, and checks the
headline and phone-status numbers against the snapshot's own counts.

Nothing here pins a fixture id, a team name, a probability or a timestamp, so a
four-hour publish cannot turn it into another wall-clock failure for the
publisher's regression gate. The checks compare the page with the snapshot in
the same tree.
"""
import json
import unittest
from pathlib import Path

import importlib

from scripts.build import live_coverage_gaps

#: The module name starts with a digit, so it is imported by path-based name.
VERIFY = importlib.import_module('scripts.22a3ed80_verify')

ROOT = Path(__file__).resolve().parents[1]


class PublishedSummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = VERIFY.verify(ROOT)
        cls.summary = cls.result['summary']

    def test_no_hard_check_fails(self):
        failures = [c for c in self.result['checks'] if c['hard'] and not c['ok']]
        self.assertEqual(failures, [], msg=json.dumps(failures, indent=1)[:4000])

    def test_every_published_fixture_is_checked(self):
        snapshot = json.loads((ROOT / 'snapshot.json').read_text())
        upcoming = [m for m in snapshot['matches'] if m.get('availability') != 'past']
        self.assertEqual(self.summary['rows_checked'], len(upcoming))
        self.assertGreater(len(upcoming), 0)

    def test_every_row_links_an_official_source(self):
        for row in self.result['rows']:
            self.assertGreaterEqual(row['source_links'], 1, row['id'])

    def test_featured_rows_are_re_derived_not_trusted(self):
        """At least the market/bookmaker rows must replay from their own evidence."""
        replayed = [r for r in self.result['rows']
                    if r['verification'] == 're-derived from the fixture analysis block']
        self.assertTrue(replayed)
        for row in replayed:
            self.assertIsNotNone(row['rendered_pick'], row['id'])
            self.assertAlmostEqual(sum(p for p in row['rendered_probabilities'] if p is not None), 100.0,
                                   places=1, msg=row['id'])

    def test_the_phone_status_matches_the_snapshot(self):
        snapshot = json.loads((ROOT / 'snapshot.json').read_text())
        upcoming = [m for m in snapshot['matches'] if m.get('availability') != 'past']
        names = {c['name'] for c in self.result['checks']}
        self.assertIn('phone_status_matches_snapshot', names)
        check = next(c for c in self.result['checks'] if c['name'] == 'phone_status_matches_snapshot')
        self.assertTrue(check['ok'], check['detail'])
        self.assertIn(str(len(upcoming)), check['detail'])


class LobbyGapRegisterTests(unittest.TestCase):
    """The executive summary must not advertise coverage holes it does not have."""

    def test_no_rendered_gap_row_is_a_card_the_record_says_was_carried(self):
        record_path = ROOT / 'data' / 'research' / 'c2a74e33' / 'live-coverage.json'
        record = json.loads(record_path.read_text())
        snapshot = json.loads((ROOT / 'snapshot.json').read_text())
        html = live_coverage_gaps({'matches': snapshot['matches'],
                                   'complete_picks': {'matches': []},
                                   '_live_coverage': record}, '')
        carried = {str(f.get('id')) for f in record['live_fixtures'] if f.get('in_published_snapshot')}
        for identifier in carried:
            self.assertNotIn(f'<span class="tried-chip unresolved">Hotspawn {identifier}</span>', html)


class RotatedFixtureTrapTests(unittest.TestCase):
    """A gap-research row must survive the publisher's rolling snapshot window.

    ``scripts/0962d605_verify.check_published_estimates`` failed the four-hour
    publisher's regression gate (run 40202907756) as soon as fixture 1081156
    Spirit Academy vs LFO 10 started and left the checked-in snapshot. The rule
    that replaced it (merged upstream by session arena-9e0e601d and kept here
    verbatim) is: absence alone is never an error, because the checked-in
    snapshot is a rolling window; a figure the dossier attributes to the board
    must still be sourced and dated.
    """

    @classmethod
    def setUpClass(cls):
        cls.verify_mod = importlib.import_module('scripts.0962d605_verify')

    def _dossier(self, fixture):
        return {'fixtures': [fixture]}

    def test_a_gap_row_with_no_published_estimate_is_never_an_error(self):
        dossier = self._dossier({
            'id': '999001',
            'hotspawn': {'source_url': 'https://www.hotspawn.com/matches/x-999001',
                         'starts_at': '2026-10-25T12:00:00Z'},
            'published_estimate': None,
        })
        snapshot = {'generated_at': '2026-10-25T14:32:11Z', 'matches': []}
        self.assertEqual(self.verify_mod.check_published_estimates(dossier, snapshot, {'matches': []}), [])

    def test_an_absent_estimate_without_published_evidence_is_an_error(self):
        dossier = self._dossier({
            'id': '999002',
            'hotspawn': {'source_url': 'https://www.hotspawn.com/matches/y-999002',
                         'starts_at': '2026-10-25T12:00:00Z'},
            'published_estimate': {'probabilities': [0.6, 0.4],
                                   'source_url': 'https://polymarket.com/event/y'},
        })
        snapshot = {'generated_at': '2026-10-25T14:32:11Z', 'matches': []}
        errors = self.verify_mod.check_published_estimates(dossier, snapshot, {'matches': []})
        self.assertTrue(any('names no published evidence' in e for e in errors), errors)

    def test_an_absent_estimate_with_evidence_and_a_clock_is_accepted(self):
        dossier = self._dossier({
            'id': '999003',
            'hotspawn': {'source_url': 'https://www.hotspawn.com/matches/z-999003',
                         'starts_at': '2026-10-25T12:00:00Z'},
            'published_estimate': {'probabilities': [0.6, 0.4],
                                   'source_url': 'https://polymarket.com/event/z',
                                   'evidence_url': 'https://polymarket.com/event/z',
                                   'observed_at': '2026-10-25T11:00:00Z'},
        })
        snapshot = {'generated_at': '2026-10-25T14:32:11Z', 'matches': []}
        self.assertEqual(self.verify_mod.check_published_estimates(dossier, snapshot, {'matches': []}), [])

    def test_a_present_row_still_has_to_match_the_board(self):
        dossier = self._dossier({'id': '999004',
                                 'published_estimate': {'probabilities': [0.6, 0.4],
                                                        'source_url': 'https://polymarket.com/event/x'}})
        snapshot = {'matches': [{'id': '999004'}]}
        origination = {'matches': [{'id': '999004', 'origination': {'probabilities': [0.55, 0.45]}}]}
        errors = self.verify_mod.check_published_estimates(dossier, snapshot, origination)
        self.assertTrue(any('!= published board' in e for e in errors), errors)


if __name__ == '__main__':
    unittest.main()
