"""Session arena-ec5083b9: the lobby-to-published-page coverage verifier.

These tests pin the verifier's contract, not any live value:

* it reads picks, probabilities and links out of the published markup and never
  computes a probability of its own,
* a live Hotspawn card that the pages do not carry is reported ``missing``,
* a row with no directional pick is ``no-pick``, and a row whose probabilities do
  not sum to one, or that carries no official https link, is a defect,
* in-site links are resolved with query strings dropped, fragments checked, and
  ``data/`` targets the branch root does not carry kept out of the broken count,
* the recorded 2026-10-24T06:27Z lobby inventory stays a faithful copy of what
  the lobby rendered (ids, team names, urls) with no schedule time asserted.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import ec5083b9_verify as verify

ROW = """
<li class="glance-row" data-glance-id="{fid}" data-glance-starts="2026-10-24T08:00:00Z"
    data-glance-closed="false" data-method="{method}">
  <div class="glance-match"><strong>{a} <span class="versus">vs</span> {b}</strong></div>
  <div class="glance-choice">
    <span class="glance-pick-label">{label}</span>
    <strong>{pick}</strong>
    <span class="glance-prob">{p1}%</span>
    <span class="glance-other">{b} {p2}%</span>
    <span class="badge green">Market line</span>
  </div>
  <div class="glance-links">{links}</div>
</li>
"""


def row(fid='1079658', method='market', a='Acend', b='FORZE Reload', label='Pick',
        pick='Acend', p1=76.5, p2=23.5, links=None):
    if links is None:
        links = ('<a class="source-link" href="https://www.hotspawn.com/matches/x-' + fid + '">'
                 'Hotspawn</a>'
                 '<a class="source-link" href="https://polymarket.com/event/x">Polymarket</a>')
    return ROW.format(fid=fid, method=method, a=a, b=b, label=label, pick=pick,
                      p1=p1, p2=p2, links=links)


CARD = {'hotspawn_id': '1079658', 'teams': ['Acend', 'FORZE Reload'],
        'competition': 'CCT Europe 2026 Series #11',
        'scheduled_start_displayed': 'Oct 24, 04:00',
        'fixture_url': 'https://www.hotspawn.com/matches/acend-vs-forze-reload-cct-europe-2026-series-11-1079658'}


class GlanceParsingTests(unittest.TestCase):
    def test_probabilities_and_links_are_read_not_computed(self):
        rows = verify.parse_glance('<ul>' + row() + '</ul>')
        self.assertEqual(rows['1079658']['pick_team'], 'Acend')
        self.assertAlmostEqual(rows['1079658']['pick_probability'], 0.765)
        self.assertAlmostEqual(rows['1079658']['other_probability'], 0.235)
        self.assertEqual(rows['1079658']['method'], 'market')
        self.assertIn('https://www.hotspawn.com/matches/x-1079658',
                      rows['1079658']['hotspawn_links'])

    def test_a_row_without_a_pick_keeps_its_label(self):
        rows = verify.parse_glance('<ul>' + row(label='Even', pick='') + '</ul>')
        self.assertEqual(rows['1079658']['pick_label'], 'Even')
        self.assertEqual(rows['1079658']['pick_team'], '')

    def test_unresolved_register_ids_are_collected_from_anchors(self):
        html = ('<div id="no-line-1082858"><p>no compliant line</p></div>'
                '<a href="./unresolved/#no-line-1082792">why</a>')
        found = verify.parse_unresolved(html)
        self.assertIn('1082858', found)
        self.assertIn('1082792', found)


class ReconcileTests(unittest.TestCase):
    def _report(self, html, card=None):
        rows = verify.parse_glance(html)
        return verify.reconcile([card or CARD], rows, {})

    def test_covered_card_has_no_defect(self):
        entry = self._report('<ul>' + row() + '</ul>')[0]
        self.assertEqual(entry['status'], 'covered')
        self.assertEqual(entry['defects'], [])
        self.assertEqual(entry['probabilities'], [0.765, 0.235])

    def test_absent_card_is_missing_and_says_so(self):
        entry = self._report('<ul></ul>')[0]
        self.assertEqual(entry['status'], 'missing')
        self.assertEqual(entry['defects'], ['No published row for this live Hotspawn card.'])
        self.assertEqual(verify.summarise([entry])['missing_fixture_ids'], ['1079658'])

    def test_row_without_a_pick_is_reported_not_filled_in(self):
        entry = self._report('<ul>' + row(label='Even', pick='') + '</ul>')[0]
        self.assertEqual(entry['status'], 'no-pick')
        self.assertIsNone(entry['pick'])
        self.assertIn('Row carries no directional pick.', entry['defects'])

    def test_probabilities_that_do_not_sum_to_one_are_a_defect(self):
        entry = self._report('<ul>' + row(p1=70.0, p2=20.0) + '</ul>')[0]
        self.assertTrue(any('do not sum to 1' in d for d in entry['defects']))

    def test_row_without_an_official_link_is_a_defect(self):
        links = '<a class="source-link" href="./origination/#match-1079658">detail</a>'
        entry = self._report('<ul>' + row(links=links) + '</ul>')[0]
        self.assertIn('Row has no Hotspawn fixture link.', entry['defects'])
        self.assertIn('Row has no official https source link.', entry['defects'])

    def test_model_only_rows_are_counted_separately(self):
        html = '<ul>' + row(method='model', p1=54.2, p2=45.8) + '</ul>'
        summary = verify.summarise(self._report(html))
        self.assertEqual(summary['model_only'], 1)
        self.assertEqual(summary['with_betting_line'], 0)


class InSiteLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        (self.site / 'picks').mkdir()
        (self.site / 'picks/index.html').write_text('<h2 id="picks">list</h2>')
        (self.site / 'index.html').write_text('<h2 id="main">summary</h2>')
        (self.site / 'data').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _links(self, anchors, page='index.html'):
        return verify.in_site_links('<body>' + anchors + '</body>', self.site, page)

    def test_fragment_on_another_page_is_checked(self):
        (self.site / 'picks/index.html').write_text('<h2 id="picks">list</h2>')
        link = self._links('<a href="./picks/#picks">picks</a>')[0]
        self.assertTrue(link['ok'])
        missing = self._links('<a href="./picks/#nowhere">picks</a>')[0]
        self.assertFalse(missing['ok'])
        self.assertFalse(missing['anchor_ok'])

    def test_query_string_is_not_part_of_the_file_name(self):
        link = self._links('<a href="./picks/?basis=market">market</a>')[0]
        self.assertEqual(link['target'], 'picks/index.html')
        self.assertTrue(link['ok'])

    def test_project_absolute_url_is_resolved(self):
        link = self._links('<a href="https://buffedlizard55-lab.github.io/MaltaProj3/picks/">x</a>')[0]
        self.assertTrue(link['ok'])

    def test_evidence_file_missing_from_the_branch_root_is_artifact_only(self):
        link = self._links('<a href="./data/evidence/x.json">evidence</a>')[0]
        self.assertFalse(link['ok'])
        self.assertTrue(link['artifact_only'])

    def test_external_source_is_not_fetched_or_flagged(self):
        link = self._links('<a href="https://polymarket.com/event/x">poly</a>')[0]
        self.assertTrue(link['ok'])
        self.assertTrue(link['external'])


class RecordedLobbyInventoryTests(unittest.TestCase):
    def setUp(self):
        self.path = verify.DEFAULT_LOBBY
        self.doc = json.loads(Path(self.path).read_text())

    def test_the_observation_carries_its_source_and_read_time(self):
        self.assertEqual(self.doc['source_url'], 'https://play.hotspawn.com/lobby')
        self.assertEqual(self.doc['observed_at'], '2026-10-24T06:27Z')

    def test_every_card_has_a_hotspawn_url_ending_in_its_id(self):
        for card in self.doc['cards']:
            self.assertTrue(card['fixture_url'].startswith('https://www.hotspawn.com/matches/'))
            self.assertTrue(card['fixture_url'].endswith('-' + card['hotspawn_id']))

    def test_no_schedule_time_is_asserted_that_the_read_did_not_confirm(self):
        # The lobby renders card times in the visitor's own timezone, so the
        # verifier must not publish a UTC instant for them.
        for card in self.doc['cards']:
            self.assertIsNone(card['scheduled_start_utc'])
            self.assertTrue(card['scheduled_start_displayed'])

    def test_the_dossier_records_no_crowd_percentage(self):
        text = Path(self.path).read_text()
        self.assertNotIn('% picked', text)
        self.assertNotIn('picked_percent', text)

    def test_team_names_come_from_the_lobby_verbatim(self):
        names = {tuple(card['teams']) for card in self.doc['cards']}
        self.assertIn(('Nuclear TigeRES', 'FORZE Reload'), names)
        self.assertIn(('Spirit Academy', 'LFO 10'), names)


if __name__ == '__main__':
    unittest.main()
