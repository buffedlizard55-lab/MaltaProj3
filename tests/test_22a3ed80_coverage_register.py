"""Session arena-22a3ed80: the dated lobby-gap register must not count cards it
says were already carried.

Why this exists
---------------
The executive summary section ``#live-coverage-gaps`` compares a dated Hotspawn
lobby sweep with the published snapshot. On the 2026-10-25T14:23:33Z publish it
rendered **"9 missing at that observation"** for nine cards whose own notes in
the same record read *"Carried in the published complete picks list"* — every one
of the 22 compared cards carries ``in_published_snapshot: true`` in
``data/research/c2a74e33/live-coverage.json``. They had left the snapshot only
because they started, so a reader on a phone was told a fully covered inventory
had nine holes.

``scripts.build.live_coverage_gaps`` therefore excludes any card the record
marks as carried from the missing count and names it separately instead. These
tests pin that contract without pinning any live fixture id: they hold for
whatever record is newest and whatever snapshot the publisher wrote, so the
module cannot become another wall-clock trap for the four-hour publisher.
"""
import json
import re
import unittest
from pathlib import Path

from scripts.build import live_coverage_gaps

ROOT = Path(__file__).resolve().parents[1]

#: The record that produced the shipped defect. Dated evidence, not a feed.
SHIPPED_RECORD = ROOT / 'data' / 'research' / 'c2a74e33' / 'live-coverage.json'


def _text(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


def _row_blocks(html):
    return re.findall(r'<li class="coverage-gap-row">.*?</li>', html, re.S)


class ShippedRegisterTests(unittest.TestCase):
    """The record and the published snapshot, read as published."""

    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(SHIPPED_RECORD.read_text())
        snapshot_path = ROOT / 'snapshot.json'
        cls.snapshot = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else {'matches': []}
        cls.html = live_coverage_gaps(
            {'matches': cls.snapshot.get('matches') or [],
             'complete_picks': {'matches': []},
             '_live_coverage': cls.record},
            '',
        )

    def test_every_compared_card_was_carried_at_that_observation(self):
        """The premise of the fix, straight from the record's own field."""
        fixtures = self.record['live_fixtures']
        self.assertGreater(len(fixtures), 0)
        for fixture in fixtures:
            self.assertTrue(fixture.get('in_published_snapshot'), fixture.get('id'))

    def test_shipped_record_renders_no_gap_rows(self):
        self.assertIn('0 missing at that observation', self.html)
        self.assertEqual(_row_blocks(self.html), [])

    def test_rotated_cards_are_named_but_never_counted(self):
        known = {str(m.get('id')) for m in self.snapshot.get('matches') or []}
        rotated = [f for f in self.record['live_fixtures'] if str(f.get('id')) not in known]
        self.assertIn('id="live-coverage-rotated"', self.html)
        self.assertIn(f'<strong>{len(rotated)}</strong> further card', self.html)
        # Each one keeps its own official Hotspawn link, so the reader can check it.
        for fixture in rotated:
            self.assertIn(fixture['hotspawn_url'], self.html)
        # Nothing is counted as missing while every compared card was carried.
        self.assertNotIn('coverage-gap-row', self.html)

    def test_no_probability_leaks_into_the_section(self):
        """A coverage note is not a price: the section carries no percentage."""
        self.assertNotIn('%', self.html.split('id="live-coverage-gaps"')[1])

    def test_the_section_keeps_its_dated_observation_and_record_links(self):
        self.assertIn('dated observation, not a live claim', self.html)
        self.assertIn('datetime="2026-10-24T16:42:00Z"', self.html)

    def test_the_record_path_from_the_loader_is_the_link_rendered(self):
        """The dated-record link must point at the sweep actually rendered."""
        record = dict(self.record, _record_path='research/c2a74e33/live-coverage.json')
        html = live_coverage_gaps({'matches': self.snapshot.get('matches') or [],
                                   'complete_picks': {'matches': []},
                                   '_live_coverage': record}, '')
        self.assertIn('research/c2a74e33/live-coverage.json', html)


class SyntheticContractTests(unittest.TestCase):
    """The rule itself, on minimal fixtures, independent of any live data."""

    def _data(self, fixtures, matches=()):
        return {'matches': list(matches), 'complete_picks': {'matches': []},
                '_live_coverage': {'observed_at': '2026-10-25T16:42:00Z',
                                   'live_fixtures': list(fixtures)}}

    def test_a_carried_card_that_has_since_started_is_not_a_gap(self):
        fixtures = [{'id': '900001', 'teams': ['Alpha', 'Beta'],
                     'competition': 'CCT Test', 'starts_at': '2026-10-25T17:00:00Z',
                     'hotspawn_url': 'https://www.hotspawn.com/matches/alpha-vs-beta-900001',
                     'in_published_snapshot': True,
                     'note': 'Carried in the published complete picks list (Market-implied estimate).'}]
        html = live_coverage_gaps(self._data(fixtures), '')
        self.assertIn('0 missing at that observation', html)
        self.assertIn('https://www.hotspawn.com/matches/alpha-vs-beta-900001', html)
        self.assertIn('id="live-coverage-rotated"', html)
        self.assertNotIn('coverage-gap-row', html)
        self.assertNotIn('Every live lobby fixture in that research window is already in this snapshot', html)

    def test_a_card_with_no_published_row_is_still_a_gap(self):
        fixtures = [{'id': '900002', 'teams': ['Gamma', 'Delta'],
                     'competition': 'CCT Test',
                     'hltv_url': 'https://www.hltv.org/matches/1/gamma-vs-delta'}]
        html = live_coverage_gaps(self._data(fixtures), '')
        self.assertIn('1 missing at that observation', html)
        self.assertIn('Gamma vs Delta', html)
        self.assertIn('https://www.hltv.org/matches/1/gamma-vs-delta', html)
        self.assertNotIn('id="live-coverage-rotated"', html)

    def test_carried_and_genuinely_missing_rows_coexist(self):
        fixtures = [
            {'id': '900003', 'teams': ['Epsilon', 'Zeta'], 'in_published_snapshot': True,
             'hotspawn_url': 'https://www.hotspawn.com/matches/epsilon-vs-zeta-900003'},
            {'id': '900004', 'teams': ['Eta', 'Theta'],
             'hotspawn_url': 'https://www.hotspawn.com/matches/eta-vs-theta-900004'},
        ]
        html = live_coverage_gaps(self._data(fixtures), '')
        self.assertIn('1 missing at that observation', html)
        rows = _row_blocks(html)
        self.assertEqual(len(rows), 1)
        self.assertIn('Eta vs Theta', rows[0])
        self.assertIn('<strong>1</strong> further card', html)  # singular, not "cards"

    def test_a_card_already_in_this_snapshot_is_neither_gap_nor_rotated(self):
        fixtures = [{'id': '900005', 'teams': ['Iota', 'Kappa'],
                     'hotspawn_url': 'https://www.hotspawn.com/matches/iota-vs-kappa-900005',
                     'in_published_snapshot': True}]
        matches = [{'id': '900005', 'teams': [{'name': 'Iota'}, {'name': 'Kappa'}]}]
        html = live_coverage_gaps(self._data(fixtures, matches), '')
        self.assertIn('Every live lobby fixture in that research window is already in this snapshot', html)
        self.assertNotIn('id="live-coverage-rotated"', html)


class ExecutiveSummaryRouteTests(unittest.TestCase):
    """The reader must still reach the register from the phone summary."""

    def test_the_summary_banner_still_links_the_section(self):
        from scripts.build import exec_banner
        banner = exec_banner({'counts': {'upcoming': 1, 'unresolved': 0, 'model': 0},
                              'inventory_observed_at': '2026-10-25T14:23:15Z',
                              '_live_coverage': {'observed_at': '2026-10-25T14:42:00Z'}}, '')
        self.assertIn('#live-coverage-gaps', banner)


if __name__ == '__main__':
    unittest.main()
