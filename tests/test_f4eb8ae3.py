"""Session f4eb8ae3 contract tests — the user-facing brief items this session verified.

The brief asked for: (1) a separate unresolved-picks-and-limitations section
inside the executive summary, (2) executive-summary links to where the updated
list of picks can be found, obvious on a phone, and (3) every research finding
published with official source links, never invented values. These tests pin
that contract on the real checked-in snapshot and on this session's research
artifacts, so a regression fails the build before it can ship.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import review, shell, summary

ROOT = Path(__file__).resolve().parents[1]
SESSION_DIR = ROOT / 'data/research/f4eb8ae3'


def load_data() -> dict:
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['coverage_complete'] = True
    if (ROOT / 'data/origination.json').exists():
        data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
        data['fallbacks'] = {str(r['id']): r for r in data['complete_picks'].get('matches') or []
                             if r.get('origination')}
    data['flags'] = list(data.get('flags') or [])
    have = {f['id'] for f in data['flags']}
    for findings in sorted((ROOT / 'data/research').glob('*/flags.json')):
        for finding in json.loads(findings.read_text()):
            if finding['id'] not in have:
                data['flags'].append(finding)
                have.add(finding['id'])
    return data


class ExecutiveSummaryContractTests(unittest.TestCase):
    """Links to the updated picks list and the unresolved section live in the summary."""

    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.summary_html = shell(cls.data, 'summary', summary(cls.data, './'), './')

    def test_exec_banner_links_to_updated_picks_featured_feed_and_unresolved(self):
        soup = BeautifulSoup(self.summary_html, 'html.parser')
        banner = soup.select_one('.exec-banner')
        self.assertIsNotNone(banner, 'executive summary must open with the picks jump banner')
        hrefs = {a.get('href') for a in banner.select('a[href]')}
        self.assertIn('./origination/#picks', hrefs, 'banner must link the updated picks list')
        self.assertIn('./picks/', hrefs, 'banner must link the featured picks feed')
        self.assertIn('./origination/#unresolved', hrefs, 'banner must link unresolved picks & limitations')

    def test_start_here_nav_and_glance_index_reach_the_picks(self):
        soup = BeautifulSoup(self.summary_html, 'html.parser')
        start = soup.select_one('#start-here')
        self.assertIsNotNone(start, 'phone-first start-here jump bar must exist')
        hrefs = {a.get('href') for a in start.select('a[href]')}
        self.assertIn('./origination/#picks', hrefs)
        self.assertIn('./origination/#unresolved', hrefs)
        self.assertIn('./#unresolved-register', hrefs)
        glance_rows = soup.select('#picks-at-a-glance .glance-row, #picks-at-a-glance li, #picks-at-a-glance tr')
        self.assertTrue(glance_rows, 'picks-at-a-glance index must render rows')

    def test_unresolved_register_is_a_separate_summary_section_with_limitations(self):
        soup = BeautifulSoup(self.summary_html, 'html.parser')
        register = soup.select_one('#unresolved-register')
        self.assertIsNotNone(register, 'executive summary needs its own unresolved section')
        heading = register.find(['h2', 'h3'])
        self.assertIsNotNone(heading)
        self.assertIn('Unresolved', heading.get_text())
        self.assertTrue(register.select('a[href*="origination/#unresolved"]'),
                        'register must link the full research trails')

    def test_mobile_landmarks_and_viewport(self):
        soup = BeautifulSoup(self.summary_html, 'html.parser')
        self.assertIsNotNone(soup.find('meta', attrs={'name': 'viewport'}))
        nav = soup.select_one('nav.mobile-nav')
        self.assertIsNotNone(nav, 'bottom mobile navigation must exist on every page')
        labels = [a.get_text(strip=True) for a in nav.select('a')]
        self.assertIn('Picks', labels, 'phone navigation must reach the picks directly')

    def test_no_hotspawn_popularity_or_fan_vote_enters_the_summary(self):
        text = BeautifulSoup(self.summary_html, 'html.parser').get_text(' ', strip=True).lower()
        self.assertNotIn('% picked', text)
        # Fan votes may appear only as an excluded input ("never inputs", "no fan votes").
        for sentence in text.split('.'):
            if 'fan vote' in sentence:
                excluded = ('never' in sentence or 'no fan votes' in sentence
                            or 'not' in sentence and 'input' in sentence)
                self.assertTrue(excluded, f'fan-vote mention is not an exclusion: {sentence!r}')


class SessionResearchArtifactTests(unittest.TestCase):
    """Every f4eb8ae3 finding is published with https source links and no invented values."""

    def setUp(self):
        self.flags = json.loads((SESSION_DIR / 'flags.json').read_text())
        self.dossier = json.loads(
            (SESSION_DIR / 'pick-source-research-2026-10-21.json').read_text())

    def test_flags_schema_and_source_links(self):
        seen = set()
        for flag in self.flags:
            for key in ('id', 'severity', 'match_ids', 'title', 'detail', 'source_urls'):
                self.assertTrue(flag.get(key), f'{flag.get("id")} missing {key}')
            self.assertNotIn(flag['id'], seen, 'flag ids must be unique')
            seen.add(flag['id'])
            self.assertIn(flag['severity'], {'warning', 'notice'})
            for url in flag['source_urls']:
                self.assertTrue(str(url).startswith('https://'), f'{flag["id"]} needs https links')

    def test_flags_render_on_the_review_page(self):
        data = load_data()
        html = review(data, '../')
        for flag in self.flags:
            self.assertIn(flag['id'], html, f'{flag["id"]} must render on Flagged for Review')

    def test_dossier_documents_every_pick_less_fixture_with_links(self):
        text = json.dumps(self.dossier)
        for match_id in ('1081597', '1082858', '1082860', '1082837'):
            self.assertIn(match_id, text)
        for finding in self.dossier['findings']:
            self.assertTrue(finding.get('conclusion'))
            self.assertIn('url', json.dumps(finding), 'each finding needs source urls')
        self.assertIn('limitations', self.dossier['findings'][1])
        self.assertIn('limitations', self.dossier['findings'][2])

    def test_never_used_inputs_are_stated(self):
        self.assertIs(self.dossier['findings'][0]['hotspawn_votes_used'], False)
        self.assertIs(self.dossier['findings'][0]['fan_votes_used'], False)
        self.assertIn('never used', json.dumps(self.dossier))


if __name__ == '__main__':
    unittest.main()
