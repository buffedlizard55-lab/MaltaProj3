"""Summary/mobile anchors must remain unique after independently merged widgets."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import summary, unresolved_page
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


if __name__ == '__main__':
    unittest.main()
