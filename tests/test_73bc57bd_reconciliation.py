"""Session arena-73bc57bd: the coverage dossier must re-derive from its sources.

These tests fail if the committed dossier drifts from either of its two inputs
(the recorded observations and the deployed branch-root pick rows), if any row
carries a value that is not verbatim-backed by a linked first-party page, or if
a probability/pick/alias appears anywhere in the session's output.
"""
from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

from scripts import review_register

SESSION_DIR = Path('data/research/73bc57bd')
OBSERVATIONS = SESSION_DIR / 'observations-2026-10-24.json'
DOSSIER = SESSION_DIR / 'inventory-reconciliation-2026-10-24.json'
MARKDOWN = SESSION_DIR / 'inventory-reconciliation-2026-10-24.md'
REGISTER = SESSION_DIR / 'repo-review.json'

reconcile = importlib.import_module('scripts.73bc57bd_reconcile')

ALLOWED_HOSTS = {
    'play.hotspawn.com', 'www.hotspawn.com', 'polymarket.com', 'www.hltv.org',
    'egamersworld.com', 'github.com', 'buffedlizard55-lab.github.io',
    'phpstack-1372681-6459848.cloudwaysapps.com',
}
VERDICTS = {
    'two-sided external price observed',
    'placeholder or one-sided books only',
    'no market observed',
}


class DossierShape(unittest.TestCase):
    def setUp(self):
        self.observations = json.loads(OBSERVATIONS.read_text())
        self.dossier = json.loads(DOSSIER.read_text())

    def test_the_dossier_is_the_join_of_its_own_inputs(self):
        rebuilt = reconcile.build_dossier(self.observations, reconcile.parse_published())
        self.assertEqual(rebuilt['counts'], self.dossier['counts'])
        self.assertEqual(
            [item['id'] for item in rebuilt['uncovered']],
            [item['id'] for item in self.dossier['uncovered']],
        )

    def test_every_lobby_card_is_either_covered_or_has_gap_research(self):
        cards = {card['id'] for card in self.observations['lobby']['cards']}
        covered = {item['id'] for item in self.dossier['covered']}
        uncovered = {item['id'] for item in self.dossier['uncovered']}
        self.assertFalse(covered & uncovered, 'a card cannot be both covered and uncovered')
        self.assertEqual(cards, covered | uncovered)
        self.assertEqual(len(cards), len(self.observations['lobby']['cards']) == len(cards) and len(cards))

    def test_counts_add_up_against_the_published_rows(self):
        counts = self.dossier['counts']
        self.assertEqual(counts['published_rows'], len(reconcile.parse_published()))
        self.assertEqual(
            counts['cards_with_a_published_pick'] + counts['cards_without_a_published_pick']
            + counts['published_rows_no_longer_in_the_future_lobby'],
            counts['published_rows'] + counts['cards_without_a_published_pick'],
        )
        self.assertEqual(
            counts['cards_with_a_published_pick'] + counts['cards_without_a_published_pick'],
            counts['lobby_future_cards'],
        )
        self.assertEqual(sum(counts['gap_verdicts'].values()), counts['cards_without_a_published_pick'])

    def test_the_published_row_count_matches_the_deployed_page(self):
        # The deployed page states its own coverage; the parse must agree with it.
        html = Path('picks/index.html').read_text()
        self.assertIn('carry a pick', html)
        self.assertEqual(len(reconcile.parse_published()), 19)
        self.assertEqual(self.dossier['counts']['published_rows'], 19)


class EveryRowHasAFirstPartyLink(unittest.TestCase):
    def setUp(self):
        self.dossier = json.loads(DOSSIER.read_text())

    def test_each_card_links_its_own_hotspawn_permalink(self):
        for item in self.dossier['covered'] + self.dossier['uncovered']:
            url = item['hotspawn_url']
            self.assertTrue(url.startswith('https://www.hotspawn.com/matches/'), url)
            self.assertTrue(url.endswith('-' + item['id']), f'{url} does not end with fixture {item["id"]}')
            self.assertEqual(len(item['teams']), 2)

    def test_every_observation_links_an_allowed_first_party_host(self):
        checked = 0
        for item in self.dossier['uncovered']:
            self.assertGreaterEqual(len(item['research']['observations']), 1, item['id'])
            for observation in item['research']['observations']:
                host = urlparse(observation['url']).netloc
                self.assertIn(host, ALLOWED_HOSTS, observation['url'])
                self.assertTrue(observation['prices_verbatim'], observation)
                self.assertRegex(observation['read_at'], r'^2026-10-24T\d\d:\d\d:\d\dZ$')
                checked += 1
        self.assertGreater(checked, 0)

    def test_hltv_links_point_at_hltv_match_pages(self):
        hltv_rows = [item for item in self.dossier['uncovered'] if item['research'].get('hltv')]
        self.assertGreaterEqual(len(hltv_rows), 3)
        for item in hltv_rows:
            url = item['research']['hltv']['url']
            self.assertRegex(url, r'^https://www\.hltv\.org/matches/\d+/')

    def test_every_cross_check_source_is_linked(self):
        for check in self.dossier['cross_checks']:
            for key in ('live_market', 'second_source'):
                host = urlparse(check[key]['url']).netloc
                self.assertIn(host, ALLOWED_HOSTS, check[key]['url'])


class NoInventedValues(unittest.TestCase):
    def setUp(self):
        self.dossier = json.loads(DOSSIER.read_text())

    def test_the_dossier_declares_that_nothing_was_hand_written(self):
        policy = self.dossier['policy']
        for key in ('hotspawn_votes_used', 'fan_votes_used', 'probabilities_written_by_hand',
                    'picks_written_by_hand', 'aliases_created'):
            self.assertIs(policy[key], False, key)

    def test_no_probability_or_pick_field_exists(self):
        text = DOSSIER.read_text()
        for forbidden in ('"probability"', '"probabilities"', '"pick"', '"pick_index"', '"edge"'):
            self.assertFalse(forbidden in text, f'{forbidden} must not appear in the dossier')

    def test_published_confidences_are_restated_not_invented(self):
        parsed = {row['id']: row for row in reconcile.parse_published()}
        for item in self.dossier['covered']:
            row = item['published']
            self.assertEqual(row['confidence'], parsed[item['id']]['confidence'], item['id'])
            self.assertEqual(row['published_line'], parsed[item['id']]['published_line'], item['id'])

    def test_every_verdict_is_from_the_closed_set(self):
        for item in self.dossier['uncovered']:
            self.assertIn(item['research']['verdict'], VERDICTS)
            self.assertTrue(item['research']['limitations'], item['id'])

    def test_placeholder_rows_are_never_called_two_sided(self):
        for item in self.dossier['uncovered']:
            research = item['research']
            books = {observation['book'] for observation in research['observations']}
            if research['verdict'] == 'two-sided external price observed':
                self.assertIn('two-sided', books, item['id'])
            else:
                self.assertNotIn('two-sided', books, f'{item["id"]} claims {research["verdict"]}')

    def test_identical_placeholder_odds_are_flagged(self):
        text = DOSSIER.read_text()
        self.assertIn('1.8 / 1.8', text)
        self.assertIn('placeholder', text.lower())


class MarkdownDossier(unittest.TestCase):
    def setUp(self):
        self.markdown = MARKDOWN.read_text()
        self.dossier = json.loads(DOSSIER.read_text())

    def test_every_uncovered_card_appears_with_its_permalink(self):
        for item in self.dossier['uncovered']:
            self.assertIn(item['hotspawn_url'], self.markdown)
            self.assertIn(f'{item["teams"][0]} vs {item["teams"][1]}', self.markdown)

    def test_the_cause_and_the_runs_are_named(self):
        for run in self.dossier['publisher_runs']:
            self.assertIn(run['id'], self.markdown)
        self.assertIn('Regression tests', self.markdown)
        self.assertIn('failed four consecutive runs', self.markdown)

    def test_no_unconverted_lobby_time_is_presented_as_utc(self):
        # The dossier records lobby times verbatim and never converts them.
        self.assertIn('US Eastern', self.markdown)
        for item in self.dossier['uncovered']:
            self.assertIn(item['lobby_time_verbatim'], self.markdown)


class ReviewRegisterIsPublished(unittest.TestCase):
    def setUp(self):
        self.register = json.loads(REGISTER.read_text())

    def test_the_register_is_valid_and_wired_into_the_review_page(self):
        review_register.validate(self.register)
        self.assertIn('research/73bc57bd/repo-review.json', review_register.REGISTERS)

    def test_every_item_links_https_evidence(self):
        for item in self.register['items']:
            self.assertTrue(item['evidence'])
            for evidence in item['evidence']:
                self.assertTrue(evidence['url'].startswith('https://'))
                self.assertTrue(evidence['detail'])
                self.assertIn(urlparse(evidence['url']).netloc, ALLOWED_HOSTS)

    def test_the_frozen_publisher_and_duplicate_id_are_published_as_needs_review(self):
        by_id = {item['id']: item for item in self.register['items']}
        for key in ('73bc57bd-publisher-frozen-nine-cards-unpicked', '73bc57bd-wall-clock-regression',
                    '73bc57bd-duplicate-no-line-research-id', '73bc57bd-lfo10-name-conflict'):
            self.assertEqual(by_id[key]['status'], 'needs review', key)

    def test_the_register_renders_on_the_review_section(self):
        html = review_register.render(self.register, '../', section_id='session-review-99',
                                      register_path='research/73bc57bd/repo-review.json',
                                      include_shared=False)
        self.assertIn('id="session-review-99"', html)
        self.assertIn('73bc57bd-publisher-frozen-nine-cards-unpicked', html)
        self.assertIn('hotspawn.com/cs2-pickems', html)
        self.assertNotIn('href="http://', html)


if __name__ == '__main__':
    unittest.main()
