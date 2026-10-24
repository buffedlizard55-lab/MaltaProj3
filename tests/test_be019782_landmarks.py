"""Summary/mobile anchors must remain unique after independently merged widgets."""
from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import glance, summary, unresolved_page
from scripts.validate import check_links


class DatedResearchHasOneOwner(unittest.TestCase):
    def data(self):
        data = json.loads(Path('data/latest.json').read_text())
        data['complete_picks'] = json.loads(Path('data/origination.json').read_text())
        data['_no_line_research'] = {
            'observed_at': '2026-10-23T09:00:00Z', 'environment': 'github-actions-runner',
            '_record_path': 'research/be019782/line-source-research.json',
            'per_fixture': [{'id': 'synthetic', 'teams': ['Synthetic A', 'Synthetic B'],
                             'money_line_lead': False}],
        }
        return data

    def test_summary_keeps_one_dated_block_inside_its_separate_limitations_section(self):
        soup = BeautifulSoup(summary(self.data(), './'), 'html.parser')
        self.assertEqual(len(soup.select('#no-line-research')), 1)
        self.assertIsNotNone(soup.select_one('#unresolved-register #no-line-research'))
        self.assertIn('./origination/#picks',
                      {a['href'] for a in soup.select('#no-line-research a[href]')})
        self.assertIsNotNone(soup.select_one('#no-line-register'))

    def test_dedicated_unresolved_page_keeps_the_same_unique_dated_block(self):
        soup = BeautifulSoup(unresolved_page(self.data(), '../'), 'html.parser')
        self.assertEqual(len(soup.select('#no-line-research')), 1)
        self.assertIsNotNone(soup.select_one('#unresolved-register #no-line-research'))

    def test_every_id_is_unique_in_both_compositions(self):
        for renderer in (summary, unresolved_page):
            with self.subTest(renderer=renderer.__name__):
                soup = BeautifulSoup(renderer(self.data(), './'), 'html.parser')
                identities = [node['id'] for node in soup.find_all(id=True)]
                self.assertEqual(len(identities), len(set(identities)))


class LinkAuditRejectsAmbiguousAnchors(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name)

    def page(self, name, body):
        path = self.site / name
        path.write_text('<!doctype html><html><head><meta name="viewport" '
                        'content="width=device-width, initial-scale=1"></head>'
                        '<body><main>' + body + '</main></body></html>')

    def test_duplicate_id_is_rejected_even_when_the_anchor_exists(self):
        self.page('index.html', '<a href="#research">Research</a>'
                  '<section id="research"></section><div id="research"></div>')
        with self.assertRaisesRegex(ValueError, 'duplicate HTML id "research"'):
            check_links(self.site)

    def test_unique_ids_with_a_local_anchor_pass(self):
        self.page('index.html', '<a href="#research">Research</a><section id="research"></section>')
        with contextlib.redirect_stdout(io.StringIO()):
            check_links(self.site)

    def test_same_anchor_on_different_pages_is_not_a_duplicate(self):
        self.page('index.html', '<a href="other.html#research">Research</a><section id="research"></section>')
        self.page('other.html', '<a href="index.html#research">Back</a><section id="research"></section>')
        with contextlib.redirect_stdout(io.StringIO()):
            check_links(self.site)


class GlanceFreshnessAndEvenEstimates(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 24, 6, tzinfo=timezone.utc)
        stamp = self.now.isoformat()
        self.match = {
            'id': 'synthetic', 'teams': [{'name': 'Synthetic A'}, {'name': 'Synthetic B'}],
            'competition': 'Synthetic Cup', 'availability': 'open',
            'starts_at': '2026-10-26T10:00:00Z', 'locks_at': '2026-10-26T09:54:00Z',
            'source_url': 'https://play.hotspawn.com/lobby', 'pick_index': 0,
            'analysis': {'method': 'market', 'probabilities': [0.6, 0.4],
                         'observed_at': stamp, 'source_url': 'https://polymarket.com/esports/cs2'},
        }
        self.data = {'matches': [self.match], 'fallbacks': {},
                     'inventory_observed_at': stamp, 'coverage_complete': True}

    def label(self, now=None):
        return BeautifulSoup(glance(self.data, './', now=now or self.now), 'html.parser')

    def test_fresh_open_observation_is_a_pick(self):
        self.assertEqual(self.label().select_one('[data-glance-pick]').get_text(), 'Pick')

    def test_an_expired_snapshot_is_historical_without_javascript(self):
        soup = self.label(now=self.now + timedelta(hours=9))
        self.assertEqual(soup.select_one('[data-glance-pick]').get_text(), 'Snapshot')
        self.assertEqual(soup.select_one('.glance-prob').get_text(), '60.0%')
        self.assertIn('Synthetic B 40.0%', soup.get_text())
        self.assertTrue(soup.select_one('a[href="https://polymarket.com/esports/cs2"]'))
        self.assertEqual(soup.select_one('.glance-row')['data-glance-inactive'], 'true')

    def test_a_stale_line_cannot_use_a_fresh_inventory_to_become_current(self):
        self.match['analysis']['observed_at'] = (self.now - timedelta(hours=9)).isoformat()
        self.assertEqual(self.label().select_one('[data-glance-pick]').get_text(), 'Snapshot')

    def test_missing_or_future_quote_clocks_do_not_qualify(self):
        for stamp in (None, 'not-a-time', (self.now + timedelta(minutes=6)).isoformat()):
            with self.subTest(stamp=stamp):
                self.match['analysis']['observed_at'] = stamp
                self.assertEqual(self.label().select_one('[data-glance-pick]').get_text(), 'Snapshot')

    def test_an_incomplete_inventory_or_unverified_lock_is_not_a_pick(self):
        self.data['coverage_complete'] = False
        self.assertEqual(self.label().select_one('[data-glance-pick]').get_text(), 'Snapshot')
        self.data['coverage_complete'] = True
        self.match['locks_at'] = None
        self.assertEqual(self.label().select_one('[data-glance-pick]').get_text(), 'Snapshot')

    def test_locked_still_means_locked_not_a_current_pick(self):
        self.assertEqual(self.label(now=datetime(2026, 10, 26, 10, tzinfo=timezone.utc))
                         .select_one('[data-glance-pick]').get_text(), 'Locked')

    def test_known_even_estimate_shows_both_numbers_but_no_invented_side(self):
        self.match['analysis']['probabilities'] = [0.5, 0.5]
        self.match['pick_index'] = None
        soup = self.label()
        self.assertIn('Synthetic A 50.0%', soup.get_text())
        self.assertIn('Synthetic B 50.0%', soup.get_text())
        self.assertIn('Even book', soup.get_text())
        self.assertIn('no side', soup.get_text())
        # Integration fix by arena-3877d48d: an exactly even book now carries the
        # same machine-readable marker as a pick, because a pick-less row that
        # carries no marker is indistinguishable from a silent gap to the
        # rendered-output audit (scripts/acceptance_audit.py::check_glance_rows).
        # It still invents no side and still shows both numbers.
        marker = soup.select_one('[data-glance-pick]')
        self.assertIsNotNone(marker)
        self.assertEqual(marker.get_text(), 'Even book')
        self.assertIn('no side', soup.get_text())

    def test_an_unresolved_row_stays_blank_not_a_default_even_estimate(self):
        self.match['analysis'] = None
        self.match['pick_index'] = None
        soup = self.label()
        self.assertIn('Unresolved', soup.get_text())
        self.assertNotIn('50.0%', soup.get_text())
        self.assertIsNone(soup.select_one('.glance-prob'))


class GuardedPublisherBudget(unittest.TestCase):
    def job(self, path, name):
        text = Path(path).read_text()
        return text.split('\n  ' + name + ':', 1)[1]

    def budget(self, text):
        return int(re.search(r'^    timeout-minutes: (\d+)\s*$', text, re.M)[1])

    def test_fresh_publisher_has_headroom_after_the_code_check_budget(self):
        publisher = self.job('.github/workflows/pages.yml', 'verify-and-deploy')
        checks = self.job('.github/workflows/checks.yml', 'verify')
        self.assertGreaterEqual(self.budget(publisher), self.budget(checks) + 15)

    def test_extra_time_does_not_bypass_regression_or_restore_before_it(self):
        publisher = self.job('.github/workflows/pages.yml', 'verify-and-deploy')
        regression = publisher.split('- name: Regression tests', 1)[1].split(
            '- name: Restore last successfully verified public snapshot', 1)[0]
        self.assertIn('python -m unittest discover -s tests -v', regression)
        self.assertIn('status=${PIPESTATUS[0]}', regression)
        self.assertIn('exit "$status"', regression)
        self.assertNotRegex(regression, r'continue-on-error:\s*true')
        self.assertLess(publisher.index('- name: Regression tests'),
                        publisher.index('- name: Restore last successfully verified public snapshot'))


if __name__ == '__main__':
    unittest.main()
