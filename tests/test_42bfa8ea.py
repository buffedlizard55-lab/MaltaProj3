"""Session 42bfa8ea: compact summary register, dated coverage claim, live dossier.

The brief asked for a separate unresolved-picks-and-limitations section inside
the executive summary that is readable on a phone, and for every pick to be
checkable against an official source. These tests pin the three changes this
session made:

* the summary renders a compact unresolved digest (counts, each pick without a
  line, plain-word limitations, a link to the evidence) instead of repeating the
  full register above the picks;
* the dated live-coverage block never calls a fixture missing while the complete
  researched list carries it (covered in test_9fd5fbf1 as well);
* this session's dossier is source-linked and states its own limitations.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import summary, unresolved_page, unresolved_register

ROOT = Path(__file__).resolve().parents[1]
SESSION_DIR = ROOT / 'data/research/42bfa8ea'


def load_data() -> dict:
    data = json.loads((ROOT / 'data/latest.json').read_text())
    data['complete_picks'] = json.loads((ROOT / 'data/origination.json').read_text())
    return data


class CompactSummaryRegister(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.summary = BeautifulSoup(summary(cls.data, './'), 'html.parser')

    def test_register_keeps_its_label_and_id(self):
        section = self.summary.select_one('#unresolved-register')
        self.assertIsNotNone(section)
        self.assertEqual(section.get('aria-labelledby'), 'unresolved-register-title')
        self.assertEqual(section.h2.get_text(strip=True), 'Unresolved picks & limitations')

    def test_no_line_rows_keep_their_pick_blocker_and_link(self):
        register = self.summary.select_one('#no-line-register')
        self.assertIsNotNone(register, 'the summary must keep its no-line section')
        cards = register.select('.no-line-card')
        self.assertTrue(cards)
        for card in cards:
            self.assertIn('Why no line:', card.get_text(' ', strip=True))
            self.assertTrue(card.select_one('a[href*="unresolved/#no-line-"]'))

    def test_summary_keeps_plain_word_limitations_and_the_full_trail_link(self):
        text = self.summary.select_one('#unresolved-register').get_text(' ', strip=True)
        self.assertIn('Limitations that apply to every row above', text)
        self.assertIn('uncalibrated', text)
        self.assertIn('every four-hour refresh', text.lower())
        hrefs = {a.get('href') for a in self.summary.select('#unresolved-register a[href]')}
        self.assertIn('./unresolved/#unresolved-register', hrefs)
        self.assertIn('./methodology/', hrefs)

    def test_deep_evidence_stays_on_the_dedicated_page(self):
        # The summary no longer repeats the dated sweep inline; the dedicated
        # page still publishes every research stage and source status.
        self.assertIsNone(self.summary.select_one('#line-sources'))
        data = load_data()
        data['_line_sources'] = {
            'observed_at': '2026-10-23T04:57:00Z', 'environment': 'github-actions-runner',
            'sources': [{'name': 'HLTV match listing', 'url': 'https://www.hltv.org/matches',
                         'http_status': 403, 'note': 'Cloudflare challenge.'}],
        }
        full = BeautifulSoup(unresolved_page(data, './'), 'html.parser')
        self.assertIsNotNone(full.select_one('#unresolved-register'))
        self.assertIsNotNone(full.select_one('#line-sources'))
        full_register = unresolved_register(data, './')
        self.assertIn('id="line-sources"', full_register)
        compact = unresolved_register(data, './', compact=True)
        self.assertNotIn('id="line-sources"', compact)
        self.assertIn('id="no-line-register"', compact)


class DatedDossier(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((SESSION_DIR / 'live-coverage.json').read_text())
        self.flags = json.loads((SESSION_DIR / 'flags.json').read_text())

    def test_every_link_is_https_and_every_replay_has_a_public_market(self):
        for url in self.record['source_urls']:
            self.assertTrue(url.startswith('https://'), url)
        self.assertEqual(len(self.record['hotspawn']['fixtures']), 28)
        self.assertEqual(len(self.record['row_replays']), 5)
        for replay in self.record['row_replays']:
            self.assertTrue(replay['match_id'])
            self.assertTrue(replay['market']['public_url'].startswith('https://polymarket.com/'))
            self.assertEqual(len(replay['site_probabilities']), 2)

    def test_record_says_what_it_is_not(self):
        role = self.record['role'].lower()
        self.assertIn('dated', role)
        self.assertIn('is a probability input', role)
        self.assertTrue(any('not a runner capture' in note for note in self.record['limitations']))

    def test_flags_are_source_linked_and_never_claim_a_new_probability(self):
        self.assertTrue(self.flags)
        for flag in self.flags:
            for key in ('id', 'severity', 'title', 'detail', 'match_ids', 'source_urls'):
                self.assertTrue(flag.get(key), f'{flag.get("id")} missing {key}')
            for url in flag['source_urls']:
                self.assertTrue(url.startswith('https://'), url)
            self.assertIn('no probability', flag['detail'].lower())
        fix = next(f for f in self.flags if f['id'] == '42bfa8ea-stale-live-coverage-claim')
        self.assertIn('1081606', fix['match_ids'])

    def test_flags_render_on_the_review_page(self):
        from scripts.build import review
        data = load_data()
        data['flags'] = list(self.flags)
        html = review(data, '../')
        for flag in self.flags:
            self.assertIn(flag['id'], html)


if __name__ == '__main__':
    unittest.main()
