"""Session arena-f43dc4f1: the findings register must be searchable on a phone.

`site/review/index.html` is the longest page on the site — 305 findings, 417
table rows, ~1 MB of HTML on 2026-10-24 — and a reader had no way to find one
finding inside it: no index, no search, no grouping, on any screen size. The
brief asks for a site that is "easily readable and accessible on phone and
mobile device", so a page that can only be read top-to-bottom fails it.

The fix is presentation-only and deliberately conservative:

* every finding is still rendered server-side, in the same order, with the same
  title, detail and source links;
* a search box and two severity filters let a reader narrow those same rows;
* the only script is self-hosted (`script-src 'self'` in the page CSP) and it
  only hides rows — it adds no text and makes no network request;
* with JavaScript disabled every row stays visible, and a `<noscript>` note says
  so.

Nothing here asserts a probability, a pick or a source status.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BUILD = (ROOT / 'scripts/build.py').read_text()
SCRIPT = ROOT / 'assets/findings-filter.js'


def flags_table_source() -> str:
    start = BUILD.index('def flags_table(')
    return BUILD[start:BUILD.index('\ndef ', start + 10)]


class TheRegisterCarriesAFilter(unittest.TestCase):
    def test_the_table_renders_a_search_box_and_severity_buttons(self):
        body = flags_table_source()
        self.assertIn('id="finding-search"', body)
        self.assertIn('id="finding-count"', body)
        for mode in ('all', 'review', 'notice'):
            self.assertIn(f'data-finding-filter="{mode}"', body, mode)

    def test_every_row_publishes_its_severity_for_the_filter(self):
        self.assertIn("data-finding-severity=", flags_table_source())

    def test_the_counts_come_from_the_rows_not_from_a_constant(self):
        # A hardcoded number could claim findings the table does not show.
        body = flags_table_source()
        self.assertIn('len(flags)', body)
        self.assertNotRegex(body, r'finding-count[^>]*>\s*\d+\s*findings')

    def test_a_reader_without_javascript_is_told_everything_is_still_rendered(self):
        body = flags_table_source()
        self.assertIn('<noscript>', body)
        self.assertIn('Every finding below is rendered either way', body)


class TheScriptOnlyHidesRows(unittest.TestCase):
    def setUp(self):
        self.source = SCRIPT.read_text()

    def test_the_asset_exists_and_ships_with_every_build(self):
        self.assertTrue(SCRIPT.is_file())

    def test_no_network_calls(self):
        for forbidden in ('fetch(', 'XMLHttpRequest', 'WebSocket', 'navigator.sendBeacon', 'import('):
            self.assertNotIn(forbidden, self.source, forbidden)

    def test_it_hides_rows_without_the_hidden_attribute_being_overridden(self):
        # scout.css sets `display: block` on these rows below 700px, which beats
        # the user-agent `[hidden] { display: none }` rule; an inline style is
        # the only thing that reliably hides a row here.
        self.assertIn('row.style.display', self.source)
        self.assertNotIn('row.hidden =', self.source)

    def test_it_never_writes_a_finding_or_a_source(self):
        for forbidden in ('textContent =', 'innerHTML', 'insertAdjacentHTML'):
            if forbidden == 'textContent =':
                # The count line is the one permitted write, and it is a count.
                self.assertEqual(self.source.count('textContent ='), 1)
                continue
            self.assertNotIn(forbidden, self.source, forbidden)

    def test_it_targets_the_findings_register_only(self):
        self.assertIn("#findings table", self.source)


class TheReviewPageLoadsItAndNothingElseDoes(unittest.TestCase):
    def test_the_shell_adds_the_script_for_the_review_page_only(self):
        self.assertIn("if key == 'review':", BUILD)
        self.assertIn("assets/findings-filter.js", BUILD)

    def test_the_built_page_keeps_every_row_visible_by_default(self):
        page = ROOT / 'site/review/index.html'
        if not page.is_file():
            self.skipTest('run python -m scripts.build first')
        soup = BeautifulSoup(page.read_text(), 'html.parser')
        rows = soup.select('#findings table tbody tr')
        self.assertGreater(len(rows), 10)
        for row in rows:
            self.assertIsNotNone(row.get('data-finding-severity'), row.get('id'))
            self.assertIsNone(row.get('style'), f"{row.get('id')} must not be pre-hidden")
        count = soup.find(id='finding-count').get_text(strip=True)
        self.assertEqual(count, f'{len(rows)} findings')
        self.assertIsNotNone(soup.find('script', src=re.compile('findings-filter\\.js')))

    def test_no_other_page_loads_the_filter(self):
        site = ROOT / 'site'
        if not site.is_dir():
            self.skipTest('run python -m scripts.build first')
        pages = [p for p in site.rglob('*.html') if 'findings-filter.js' in p.read_text()]
        self.assertEqual([p.relative_to(site).as_posix() for p in pages], ['review/index.html'])


if __name__ == '__main__':
    unittest.main()
