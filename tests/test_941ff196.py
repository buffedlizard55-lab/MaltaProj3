"""Session arena-941ff196: executive-summary pick finder, guidance display, Hotspawn provenance.

All fixtures are the repository's own checked-in snapshots; no live network
access and no invented probabilities. These tests guard the additive
executive-summary banner (internal links to the updated picks list), the
guidance-aware coverage sentence, and the Hotspawn reverse-engineering
provenance block on the coverage page.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import coverage, exec_banner, summary


def inventory():
    return json.loads(Path('data/latest.json').read_text())


def with_complete(data):
    data = copy.deepcopy(data)
    data['complete_picks'] = json.loads(Path('data/origination.json').read_text())
    return data


class ExecBannerTests(unittest.TestCase):
    def test_banner_links_only_internal_picks_lists(self):
        html = exec_banner(with_complete(inventory()), './')
        soup = BeautifulSoup(html, 'html.parser')
        section = soup.select_one('section.exec-banner')
        self.assertIsNotNone(section)
        hrefs = [a['href'] for a in section.select('.exec-banner-actions a')]
        # Session 4c972a51 gives the unresolved register its own page, so the
        # third action now points there; the full research trails stay linked
        # from the banner meta line and the register itself.
        self.assertEqual(hrefs, ['./origination/#picks', './picks/', './unresolved/'])
        for href in hrefs:
            self.assertTrue(href.startswith('./'), href)
            self.assertNotIn('http', href)
        self.assertIn('./origination/#unresolved', [a['href'] for a in section.select('a')])

    def test_banner_counts_match_complete_picks_snapshot(self):
        data = with_complete(inventory())
        cc = data['complete_picks']['counts']
        text = BeautifulSoup(exec_banner(data, './'), 'html.parser').get_text(' ')
        self.assertIn(f"{cc['with_pick']} of {cc['active']} with a pick", text)
        self.assertIn(f"{cc['unresolved']} without a pick", text)

    def test_banner_renders_without_complete_picks(self):
        # A retained snapshot without origination data must not crash the summary.
        text = BeautifulSoup(exec_banner(inventory(), './'), 'html.parser').get_text(' ')
        self.assertIn('Updated picks', text)
        self.assertIn('Unresolved', text)

    def test_banner_is_first_block_after_summary_heading(self):
        html = summary(with_complete(inventory()), './')
        banner_at = html.find('exec-banner')
        self.assertGreater(banner_at, 0)
        # Phone-first (f60683a4): the jump bar and glance index sit above the
        # banner so #picks-at-a-glance is actually on the first phone screen.
        # The banner still has to exist; the register still follows it.
        self.assertGreater(html.find('id="start-here"'), 0)
        self.assertGreater(html.find('id="picks-at-a-glance"'), html.find('id="start-here"'))
        self.assertGreater(html.find('id="unresolved-register"'), banner_at)


class GuidanceDisplayTests(unittest.TestCase):
    def test_missing_guidance_key_renders_clean_sentence(self):
        data = with_complete(inventory())
        data['complete_picks']['counts'].pop('guidance', None)
        html = summary(data, './')
        self.assertNotIn('guidance', html.lower().split('id="picks-status"')[1].split('</section>')[0]
                         .replace('guidance for manual review', ''))

    def test_present_guidance_count_is_shown_not_hidden(self):
        data = with_complete(inventory())
        cc = data['complete_picks']['counts']
        cc['guidance'] = 2
        html = summary(data, './')
        self.assertIn('2 wide-book guidance', html)


class HotspawnProvenanceTests(unittest.TestCase):
    def test_coverage_documents_hotspawn_integration(self):
        html = coverage(with_complete(inventory()), './')
        soup = BeautifulSoup(html, 'html.parser')
        section = soup.select_one('#hotspawn-integration')
        self.assertIsNotNone(section)
        hrefs = [a.get('href', '') for a in section.select('a')]
        self.assertIn(
            'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
            '?sport_alias=cs2&status=scheduled&tenantId=1', hrefs)
        self.assertIn('https://play.hotspawn.com/lobby', hrefs)
        self.assertIn('https://play.hotspawn.com/cs2-pickems', hrefs)
        self.assertIn('https://play.hotspawn.com/how-it-works', hrefs)
        text = section.get_text(' ')
        for phrase in ('fixture array', 'cross-check', 'Fail-closed', '4'):
            self.assertIn(phrase, text)

    def test_banner_styles_are_responsive(self):
        css = Path('assets/scout.css').read_text()
        self.assertIn('.exec-banner', css)
        self.assertIn('.exec-banner-actions a .label', css)
        # The phone rule stacks the three actions vertically.
        phone = css[css.find('Session 941ff196'):]
        self.assertIn('@media(max-width:700px)', phone)
        self.assertIn('grid-template-columns:1fr', phone.replace(' ', ''))


if __name__ == '__main__':
    unittest.main()
