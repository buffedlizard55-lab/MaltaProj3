"""Session f60683a4: phone-first pick jump and sourced low-tier research flags.

The brief asked for (1) a pick or an explicit limitation for every Hotspawn CS2
match, including low-tier fixtures the featured method cannot price, (2) an
executive summary a phone reader can use to find those picks, and (3) official
source links on every research claim. These tests lock the presentation change
and the research artifacts; they do not invent a probability.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from scripts.build import start_here, summary

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / 'data' / 'research' / 'f60683a4'


def _inventory():
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    data['_twc_day4'] = {'matches': [], 'not_in_hotspawn_snapshot': [], 'lines': {}}
    return data


class PhonePickJumpTests(unittest.TestCase):
    def test_start_here_leads_with_the_in_page_pick_index(self):
        html = start_here(_inventory(), './')
        soup = BeautifulSoup(html, 'html.parser')
        nav = soup.select_one('nav.start-here')
        self.assertIsNotNone(nav)
        hrefs = [a['href'] for a in nav.select('a[href]')]
        self.assertEqual(hrefs[0], './#picks-at-a-glance')
        self.assertEqual(nav.select_one('a.picks-here')['href'], './#picks-at-a-glance')
        self.assertIn('./origination/#picks', hrefs)
        self.assertIn('./origination/#unresolved', hrefs)
        self.assertIn('./#unresolved-register', hrefs)
        self.assertNotIn('./final-day/', hrefs)

    def test_summary_keeps_the_jump_bar_above_glance_and_the_unresolved_register(self):
        with patch('scripts.build.contrarian_review', return_value=''), \
             patch('scripts.build.contrarian_briefing', return_value=''):
            html = summary(_inventory(), './')
        self.assertLess(html.index('id="start-here"'), html.index('id="picks-at-a-glance"'))
        self.assertLess(html.index('id="picks-at-a-glance"'), html.index('id="unresolved-register"'))
        self.assertIn('Picks on this page', html)
        self.assertIn('id="no-line-register"', html)

    def test_phone_css_makes_the_picks_jump_full_width(self):
        css = (ROOT / 'assets' / 'scout.css').read_text()
        self.assertIn('.start-here a.picks-here', css)
        block = css[css.find('Session f60683a4'):]
        self.assertIn('@media(max-width:700px)', block)
        self.assertIn('grid-template-columns:1fr 1fr', block)
        self.assertIn('grid-column:1/-1', block.replace(' ', ''))


class LowTierResearchArtifactTests(unittest.TestCase):
    def test_research_file_carries_https_sources_and_does_not_claim_fan_votes(self):
        dossier = json.loads((SESSION / 'low-tier-line-research.json').read_text())
        self.assertEqual(dossier['session'], 'arena-f60683a4')
        self.assertTrue(dossier['observed_at'].startswith('2026-10-22'))
        blob = json.dumps(dossier)
        self.assertIn('never used as probabilities', blob)
        self.assertIn('excluded by project policy', blob)
        for row in dossier['featured_unresolved_in_snapshot'] + dossier['additional_model_only_research']:
            self.assertTrue(row['sources'], row.get('id'))
            for url in row['sources']:
                self.assertTrue(url.startswith('https://'), url)
        for url in dossier['live_snapshot']['sources']:
            self.assertTrue(url.startswith('https://'))

    def test_flags_are_source_linked_and_do_not_write_a_pick(self):
        flags = json.loads((SESSION / 'flags.json').read_text())
        self.assertGreaterEqual(len(flags), 4)
        ids = [f['id'] for f in flags]
        self.assertEqual(len(ids), len(set(ids)))
        for item in flags:
            self.assertIn(item['severity'], {'warning', 'notice', 'error'})
            self.assertTrue(item['title'])
            self.assertTrue(item['detail'])
            self.assertTrue(item['source_urls'])
            for url in item['source_urls']:
                self.assertTrue(url.startswith('https://'), url)
            # Directory cents may be described; they must not be presented as
            # an originated probability this session wrote into a snapshot.
            self.assertNotIn('written into the snapshot', item['detail'].lower())


if __name__ == '__main__':
    unittest.main()
