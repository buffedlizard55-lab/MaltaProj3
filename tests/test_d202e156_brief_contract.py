"""Session arena-d202e156: the brief's rendered-output contract, re-checked on the built site.

`scripts/acceptance_audit.py` already checks ten brief lines against the rendered
pages. This module pins the three the reviewer asked about specifically, and does
it on the *built* site rather than on a hand-written fixture:

* the executive summary links, in-site, to where the updated picks live, and every
  one of those links resolves to a real page or a real same-page anchor;
* a separate "Unresolved picks & limitations" register sits inside the executive
  summary, and every per-fixture card in it states why no line was found;
* the site is phone-ready: a device-width viewport on every page, a fixed phone
  nav with thumb-sized targets, tables that collapse to cards, and no element
  wider than a 320 px screen.

Nothing here invents a probability. It reads the built HTML and the built CSS.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'

# Every current Pages view the build emits. A page missing from this list is a
# build regression, not a test gap.
PAGES = [
    'index.html', 'picks/index.html', 'origination/index.html', 'unresolved/index.html',
    'strategy/index.html', 'coverage/index.html', 'methodology/index.html',
    'review/index.html', 'edge/index.html', 'twc-picks/index.html', 'final-day/index.html',
]

# Ids inside the no-line register that are headings, not per-fixture cards.
NOT_CARDS = {'no-line-register', 'no-line-title', 'no-line-research'}

# `scripts/build.py::shell()` puts the phone status strip on every page it
# renders. Two views are then overwritten by their own builders
# (`build_origination.py`, `build_strategy.py`), whose shells do not carry it, so
# a reader on the phone loses the one-tap route to the picks exactly where they
# are most likely to be. Recorded as a cross-session request in COORDINATION.md
# and as flag `d202e156-phone-status-strip-missing-on-two-views`; the builders are
# claimed by open PRs #245 and #238, so this session does not edit them. Any
# *third* page losing the strip fails this test.
PHONE_STRIP_KNOWN_ABSENT = {'origination/index.html', 'strategy/index.html'}


def page(rel: str) -> BeautifulSoup:
    return BeautifulSoup((SITE / rel).read_text(), 'html.parser')


def resolve(rel: str, href: str, soup: BeautifulSoup) -> str | None:
    """Return None when the link resolves, else why it does not.

    Handles the three relative forms the build emits: `./page/#anchor`,
    `../page/#anchor` from a sub-page, and `#anchor` on the same page. A query
    string (`?basis=market`) is a filter, not a path.
    """
    if href.startswith(('http://', 'https://', 'mailto:', 'tel:', 'data:')):
        return None
    path, _, anchor = href.partition('#')
    path = path.split('?', 1)[0]
    if path in ('', '.'):
        if anchor and soup.find(id=anchor) is None:
            return f'{href}: anchor #{anchor} not on the page'
        return None
    if path.startswith('/'):
        return f'{href}: absolute path, not resolvable in a project-subpath site'
    target = (SITE / rel).parent
    for part in path.split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            target = target.parent
        else:
            target = target / part
    if target.is_dir():
        target = target / 'index.html'
    if not target.exists():
        return f'{href}: {target.relative_to(SITE)} does not exist'
    if anchor and BeautifulSoup(target.read_text(), 'html.parser').find(id=anchor) is None:
        return f'{href}: anchor #{anchor} not on {target.relative_to(SITE)}'
    return None


def phone_blocks(css: str) -> str:
    """Every declaration inside any `@media(max-width:700px)` block, whitespace-stripped."""
    return media_block(css, 700)


def media_block(css: str, px: int) -> str:
    """Every declaration inside any `@media(max-width:{px}px)` block, whitespace-stripped."""
    out = []
    for match in re.finditer(rf'@media\(max-width:{px}px\)\{{', css):
        depth, i = 1, match.end()
        while i < len(css) and depth:
            if css[i] == '{':
                depth += 1
            elif css[i] == '}':
                depth -= 1
            i += 1
        out.append(css[match.end():i - 1])
    return re.sub(r'\s+', '', ''.join(out))


class BuiltSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (SITE / 'index.html').exists():
            raise unittest.SkipTest('site/ not built; run python -m scripts.build first')
        cls.pages = {rel: page(rel) for rel in PAGES}


class ExecutiveSummaryLinksInSite(BuiltSite):
    def test_every_current_page_exists_in_the_build(self):
        missing = [rel for rel in PAGES if not (SITE / rel).exists()]
        self.assertEqual(missing, [], f'build did not emit: {missing}')

    def test_start_here_links_to_the_updated_picks_and_resolves(self):
        soup = self.pages['index.html']
        start = soup.find(id='start-here')
        self.assertIsNotNone(start, '#start-here is missing from the executive summary')
        hrefs = [a['href'] for a in start.find_all('a') if a.get('href')]
        self.assertTrue(hrefs, '#start-here has no links')
        for href in hrefs:
            self.assertIsNone(resolve('index.html', href, soup), f'start-here link broken: {href}')
        joined = ' '.join(hrefs)
        self.assertIn('origination/#picks', joined)
        self.assertIn('unresolved', joined)

    def test_every_internal_link_on_the_executive_summary_resolves(self):
        soup = self.pages['index.html']
        broken = [resolve('index.html', a['href'], soup) for a in soup.find_all('a', href=True)]
        self.assertEqual([b for b in broken if b], [], '; '.join(b for b in broken if b)[:400])

    def test_every_internal_link_on_every_page_resolves(self):
        broken = []
        for rel, soup in self.pages.items():
            for a in soup.find_all('a', href=True):
                problem = resolve(rel, a['href'], soup)
                if problem:
                    broken.append(f'{rel}: {problem}')
        self.assertEqual(broken, [], '; '.join(broken[:10]))


class UnresolvedSectionIsInsideTheSummary(BuiltSite):
    def test_the_register_is_present_and_labelled(self):
        soup = self.pages['index.html']
        self.assertIsNotNone(soup.find(id='unresolved-register'),
                             '#unresolved-register missing from the summary')
        title = soup.find(id='unresolved-register-title')
        self.assertIsNotNone(title, '#unresolved-register-title missing')
        self.assertIn('Unresolved picks & limitations', title.get_text(' ', strip=True))

    def test_the_no_betting_line_register_is_present(self):
        soup = self.pages['index.html']
        self.assertIsNotNone(soup.find(id='no-line-register'),
                             '#no-line-register missing from the summary')

    def test_every_no_line_card_names_its_limitation(self):
        soup = self.pages['index.html']
        cards = [t for t in soup.select('[id^="no-line-"]') if t.get('id') not in NOT_CARDS]
        self.assertTrue(cards, 'no per-fixture no-line cards in the summary')
        for card in cards:
            text = card.get_text(' ', strip=True)
            self.assertIn('No betting line', text,
                          f'{card.get("id")} does not state that no line was found')
            self.assertTrue(card.find('a', href=True),
                            f'{card.get("id")} links no source')

    def test_a_dedicated_unresolved_page_exists(self):
        self.assertTrue((SITE / 'unresolved/index.html').exists())


class PhoneReady(BuiltSite):
    def test_every_page_declares_a_device_width_viewport(self):
        missing = [rel for rel, soup in self.pages.items()
                   if not soup.find('meta', attrs={'name': 'viewport'})]
        self.assertEqual(missing, [], f'no viewport meta on: {missing}')

    def test_the_phone_status_strip_links_to_the_picks_and_the_blanks(self):
        absent = []
        for rel, soup in self.pages.items():
            nav = soup.select_one('nav.mobile-status')
            if nav is None:
                if rel not in PHONE_STRIP_KNOWN_ABSENT:
                    absent.append(rel)
                continue
            picks = nav.select_one('a.mobile-status-picks')
            blank = nav.select_one('a.mobile-status-blank')
            self.assertIsNotNone(picks, f'{rel}: no phone picks link')
            self.assertIsNotNone(blank, f'{rel}: no phone unresolved link')
            self.assertIsNone(resolve(rel, picks['href'], soup), f'{rel}: {picks["href"]}')
            self.assertIsNone(resolve(rel, blank['href'], soup), f'{rel}: {blank["href"]}')
        self.assertEqual(absent, [],
                         'phone status strip missing on: ' + ', '.join(absent) +
                         ' (see COORDINATION.md cross-session request)')

    def test_no_element_declares_a_width_wider_than_a_320px_phone(self):
        """A fixed width or min-width above 320 px forces horizontal scrolling."""
        wide = []
        for rel, soup in self.pages.items():
            for tag in soup.find_all(style=True):
                for chunk in tag['style'].split(';'):
                    if ':' not in chunk:
                        continue
                    prop, value = chunk.split(':', 1)
                    prop, value = prop.strip().lower(), value.strip().lower()
                    if prop in ('width', 'min-width') and value.endswith('px'):
                        try:
                            px = float(value[:-2])
                        except ValueError:
                            continue
                        if px > 320:
                            wide.append(f'{rel}: <{tag.name} style="{tag["style"]}">')
        self.assertEqual(wide, [], '; '.join(wide[:6]))

    def test_the_css_collapses_tables_and_sets_thumb_targets_on_phone(self):
        css = (ROOT / 'assets/scout.css').read_text()
        # Tables become cards at 850 px, before the phone breakpoint at 700 px.
        tablet = media_block(css, 850)
        self.assertIn('.matches-table,.matches-table>tbody{display:block}', tablet,
                      'tables do not collapse to cards on a phone')
        self.assertIn('overflow-wrap:anywhere', tablet,
                      'long team names cannot wrap on a phone')
        block = phone_blocks(css)
        self.assertIn('.mobile-status{display:flex', block,
                      'the phone status strip is never shown at <=700px')
        self.assertIn('min-height:44px', block,
                      'no 44px minimum tap target in the phone block')

    def test_the_phone_nav_is_fixed_to_the_bottom(self):
        css = (ROOT / 'assets/scout.css').read_text()
        block = phone_blocks(css)
        self.assertIn('.mobile-nav{position:fixed', block)


class PickCoverageOnTheBuiltSummary(BuiltSite):
    """Every fixture the snapshot calls active must appear with both percentages."""

    def test_glance_rows_carry_both_probabilities_and_a_source(self):
        snapshot = json.loads((SITE / 'snapshot.json').read_text())
        active = [m for m in snapshot['matches'] if m.get('availability') != 'past']
        soup = self.pages['index.html']
        rows = soup.select('#glance-list .glance-row')
        self.assertTrue(rows, 'no glance rows rendered')
        missing = []
        for match in active:
            names = [t['name'] for t in match['teams']]
            row = next((r for r in rows if all(n in r.get('data-search', '') or
                                               n in r.get_text(' ', strip=True) for n in names)), None)
            if row is None:
                missing.append(f"{match['id']} {' vs '.join(names)}")
                continue
            text = row.get_text(' ', strip=True)
            percents = re.findall(r'(\d+(?:\.\d+)?)%', text)
            self.assertGreaterEqual(len(percents), 2,
                                     f'{match["id"]}: fewer than two percentages rendered')
            self.assertTrue(row.select('.glance-links a[href^="http"]'),
                            f'{match["id"]}: no source link on the row')
        self.assertEqual(missing, [], f'active fixtures absent from the summary: {missing}')


if __name__ == '__main__':
    unittest.main()
