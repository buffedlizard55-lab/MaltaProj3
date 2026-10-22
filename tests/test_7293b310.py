"""Session arena-7293b310 — the executive summary answers the phone questions.

The brief's complaints were concrete: "the site is a bit confusing", "I want to
be able to visit the site and be able to find where the picks for the matches
are easily on my phone", and "a separate section for any unresolved picks and the
limitations for generating picks for them and include this in the executive
summary". These tests pin the presentation contract:

* the first block after the page heading states when the snapshot was observed,
  how many fixtures carry a pick and how many are unresolved — copied from the
  published snapshot, never computed from a model or a Hotspawn popularity score;
* the complete picks list, its unresolved register and the next-match preview sit
  above the dated archive, so nothing historical interrupts the pick route;
* the dated final-day and contrarian material is still published in full, inside
  one labelled, collapsed archive, with every anchor link still resolvable;
* the featured-method rejection table is no longer a byte-for-byte duplicate of
  the researched register.

No test here writes a probability, a pick or a source observation.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import PAGES, summary

ROOT = Path(__file__).resolve().parents[1]


def data():
    from scripts.contrarian import derive_context, load_review
    payload = json.loads((ROOT / 'data/latest.json').read_text())
    payload['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    # build() derives this before calling summary(); the dated 9z-Aurora review
    # renders from it. Without it the section is empty, which is what the site
    # did before a session context existed.
    payload['_contrarian'] = derive_context(payload, load_review(ROOT / 'data' / 'contrarian.json'))
    return payload


class BannerStatus(unittest.TestCase):
    def setUp(self):
        self.payload = data()
        self.html = summary(self.payload, './')
        self.soup = BeautifulSoup(self.html, 'html.parser')

    def test_status_line_is_the_first_thing_after_the_banner_label(self):
        banner = self.soup.select_one('section.exec-banner')
        self.assertIsNotNone(banner)
        status = banner.select_one('[data-banner-status]')
        self.assertIsNotNone(status, 'the banner must state the snapshot time and counts')
        self.assertLess(str(banner).index('data-banner-status'), str(banner).index('exec-banner-actions'))

    def test_status_counts_are_the_published_counts(self):
        cc = self.payload['complete_picks']['counts']
        status = self.soup.select_one('[data-banner-status]').get_text(' ', strip=True)
        self.assertIn(f"{cc['active']} fixtures", status)
        self.assertIn(f"{cc['with_pick']} with a pick", status)
        self.assertIn(f"{cc['unresolved']} unresolved", status)
        # It names the observation timestamp, not the build time.
        from scripts.build import local_time
        self.assertIn(f"Updated {local_time(self.payload['inventory_observed_at'])}", status)

    def test_status_renders_without_a_complete_picks_file(self):
        bare = json.loads((ROOT / 'data/latest.json').read_text())
        html = summary(bare, './')
        soup = BeautifulSoup(html, 'html.parser')
        status = soup.select_one('[data-banner-status]')
        self.assertIsNotNone(status)
        self.assertIn('fixtures', status.get_text(' ', strip=True))

    def test_status_line_never_carries_a_probability_or_a_pick(self):
        status = self.soup.select_one('[data-banner-status]').get_text(' ', strip=True)
        self.assertNotIn('%', status)
        for match in self.payload['complete_picks']['matches']:
            names = [t['name'] for t in match['teams'] if t.get('name')]
            for name in names:
                self.assertNotIn(name, status)


class ArchiveFold(unittest.TestCase):
    def setUp(self):
        self.payload = data()
        self.html = summary(self.payload, './')
        self.soup = BeautifulSoup(self.html, 'html.parser')
        self.fold = self.soup.select_one('details.archive-fold')

    def test_archive_is_one_labelled_collapsed_block(self):
        self.assertIsNotNone(self.fold)
        self.assertFalse(self.fold.has_attr('open'))
        summary_text = ' '.join(self.fold.summary.get_text(' ', strip=True).split())
        self.assertIn('Archive', summary_text)
        self.assertIn('not current picks', summary_text.lower())

    def test_current_route_stays_above_the_archive(self):
        html = self.html
        fold_at = html.index('class="archive-fold"')
        for marker in ('id="start-here"', 'id="picks-at-a-glance"', 'id="unresolved-register"',
                       'id="next-matches-section"'):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)
                self.assertLess(html.index(marker), fold_at)

    def test_dated_material_is_kept_inside_the_archive(self):
        for anchor in ('contrarian', 'upset-watchlist'):
            with self.subTest(anchor=anchor):
                target = self.soup.find(id=anchor)
                self.assertIsNotNone(target, f'#{anchor} must still exist')
                self.assertTrue(self.fold in target.parents, f'#{anchor} belongs in the archive')

    def test_two_dated_reviews_are_no_longer_confusingly_similar(self):
        headings = [h.get_text(' ', strip=True) for h in self.soup.find_all('h2')]
        self.assertIn('Day-one upset review: 9z–Aurora', headings)
        self.assertIn('Market-backed upset watchlist', headings)
        self.assertNotIn('Contrarian, not careless', headings)
        self.assertNotIn('Contrarian, not reckless', headings)

    def test_archive_link_targets_the_complete_picks_list(self):
        link = self.fold.summary.select_one('a[href="./origination/#picks"]')
        self.assertIsNotNone(link)


class SingleUnresolvedRegister(unittest.TestCase):
    def setUp(self):
        self.payload = data()
        self.soup = BeautifulSoup(summary(self.payload, './'), 'html.parser')

    def test_one_researched_register_and_one_featured_audit_table(self):
        register = self.soup.select_one('#unresolved-register')
        featured = self.soup.select_one('#unresolved')
        self.assertIsNotNone(register)
        self.assertIsNotNone(featured)
        # The two lists are genuinely different now: the featured table shows the
        # original method's own rejections, not a second copy of the researched one.
        featured_rows = featured.select('.unresolved-table > tbody > tr')
        researched_ids = {m['id'] for m in self.payload['complete_picks']['matches'] if not m.get('origination')}
        featured_ids = [m['id'] for m in self.payload['matches']
                        if m['availability'] in {'open', 'locked', 'unknown_lock'} and m['analysis'] is None]
        self.assertEqual(len(featured_rows), len(featured_ids))
        self.assertNotEqual(set(featured_ids), researched_ids)

    def test_register_keeps_every_researched_blank_and_its_sources(self):
        register = self.soup.select_one('#unresolved-register')
        for match in self.payload['complete_picks']['matches']:
            if match.get('origination'):
                continue
            self.assertIn(f'id="unresolved-summary-{match["id"]}"', str(register))
            card = register.select_one(f'#unresolved-summary-{match["id"]}')
            self.assertTrue(card.select('a[href^="https://"]'))

    def test_no_duplicate_heading_for_two_different_lists(self):
        headings = [h.get_text(' ', strip=True) for h in self.soup.find_all('h2')]
        self.assertEqual(headings.count('Unresolved picks & limitations'), 1)
        self.assertIn('Unresolved in the featured exact-name method', headings)


class PhonePresentation(unittest.TestCase):
    def test_glance_rows_show_both_probabilities_and_the_pick(self):
        payload = data()
        soup = BeautifulSoup(summary(payload, './'), 'html.parser')
        glance = soup.select_one('#picks-at-a-glance')
        rows = glance.select('li.glance-row')
        self.assertTrue(rows)
        resolved = [li for li in rows if li.select_one('.glance-prob') and 'no side' not in li.select_one('.glance-prob').get_text()]
        self.assertTrue(resolved, 'at least one resolved row must be rendered')
        for li in resolved:
            self.assertIsNotNone(li.select_one('.glance-other'))
            self.assertIsNotNone(li.select_one('.glance-pick-label'))

    def test_status_and_archive_styles_exist_for_phone_widths(self):
        css = (ROOT / 'assets' / 'scout.css').read_text()
        self.assertIn('.exec-banner-status', css)
        self.assertIn('.archive-fold', css)
        mobile = re.search(r'@media\(max-width:700px\)\{[^}]*\.exec-banner-status', css)
        self.assertIsNotNone(mobile, 'the banner status must be styled at phone width')
        self.assertIn('.archive-note', css)

    def test_archive_fold_reveals_itself_for_in_page_links(self):
        script = (ROOT / 'assets' / 'scout.js').read_text()
        self.assertIn("details.archive-fold", script)
        self.assertIn('scrollIntoView', script)

    def test_unresolved_page_is_still_part_of_the_site(self):
        self.assertIn('unresolved', PAGES)
        self.assertEqual(PAGES['unresolved'][1], 'unresolved/index.html')


if __name__ == '__main__':
    unittest.main()


class EvenEstimateAudit(unittest.TestCase):
    """The public coverage audit accepts an even pick only with its evidence."""

    def test_a_documented_tie_break_is_accepted_and_nothing_else_is(self):
        from scripts.coverage_audit import documented_tie_break
        even = {'method': 'model', 'probabilities': [0.5, 0.5], 'tie_break': {
            'rule': 'published-rank tie-break', 'ranks': [215, 229], 'winner': 0,
            'source': 'HLTV world ranking', 'source_url': 'https://www.hltv.org/ranking/teams/2026/october/20'}}
        self.assertTrue(documented_tie_break(even, 0))
        self.assertFalse(documented_tie_break(even, 1))                     # wrong direction
        self.assertTrue(documented_tie_break(even, None))                   # no side is always allowed
        for broken in ({'method': 'market', 'probabilities': [0.5, 0.5], 'tie_break': even['tie_break']},
                       {'method': 'model', 'tie_break': dict(even['tie_break'], ranks=[215, 215])},
                       {'method': 'model', 'tie_break': dict(even['tie_break'], source_url='')},
                       {'method': 'model', 'tie_break': dict(even['tie_break'], rule='because')}):
            with self.subTest(broken=broken):
                self.assertFalse(documented_tie_break(broken, 0))

    def test_the_checked_in_snapshot_passes_the_public_coverage_audit(self):
        from scripts.coverage_audit import audit_complete_picks
        payload = json.loads((ROOT / 'data/origination.json').read_text())
        self.assertEqual(audit_complete_picks(payload), [])
