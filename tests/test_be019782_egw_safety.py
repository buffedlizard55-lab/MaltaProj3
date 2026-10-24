"""EGW source binding: synthetic only; no network, real quote or alias edits."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import egw_live, originate, reference_odds

STAMP = '2026-10-24T01:30:00Z'
START = '2026-10-26T03:00:00Z'
MATCH = {'id': '123', 'competition': 'Synthetic Cup', 'starts_at': START,
         'teams': [{'name': 'Ground Zero'}, {'name': 'Off Chops'}]}


def anchor(start=START, slug='ground-zero-vs-off-chops-id',
           text='Ground Zero 3.44 Off Chops 1.24', event='one'):
    clock = '' if start is None else f'<time datetime="{start}"></time>'
    return f'<a href="/counterstrike/match/{event}/{slug}">{clock}{text}</a>'


def entries(html, match=None):
    return egw_live.entries_for(html, [match or MATCH], {'aliases': []}, STAMP)


class OriginalClockAndOutcomeBinding(unittest.TestCase):
    def test_source_markup_clock_and_exact_outcomes_can_qualify(self):
        (row,) = entries(anchor())
        self.assertEqual(row['starts_at'], START)
        self.assertEqual(row['odds'], [3.44, 1.24])
        self.assertEqual(reference_odds.problems(row), [])

    def test_no_provider_time_is_not_filled_from_hotspawn(self):
        self.assertEqual(entries(anchor(None)), [])
        self.assertIsNone(egw_live.parse_index(anchor(None))[0]['starts_at'])

    def test_unknown_or_naive_time_is_not_guessed_as_utc(self):
        for value in ('tomorrow', '', '2026-10-26T03:00:00'):
            with self.subTest(value=value):
                self.assertEqual(entries(anchor(value)), [])

    def test_other_meeting_cannot_be_given_this_fixtures_start(self):
        self.assertEqual(entries(anchor('2026-10-27T03:00:00Z')), [])

    def test_utc_offset_is_normalized_from_source_not_copied(self):
        (row,) = entries(anchor('2026-10-26T05:00:00+02:00'))
        self.assertEqual(row['starts_at'], START)
        self.assertIn('05:00:00+02:00', row['excerpt'])

    def test_conflicting_source_time_elements_are_rejected(self):
        markup = anchor().replace('</a>', '<time datetime="2026-10-27T03:00:00Z"></time></a>')
        self.assertEqual(entries(markup), [])

    def test_slug_substring_cannot_alias_an_academy(self):
        self.assertEqual(entries(anchor(slug='ground-zero-academy-vs-off-chops-id',
                                        text='Ground Zero Academy 3.44 Off Chops 1.24')), [])

    def test_odds_are_bound_to_named_outcomes_not_the_url_order(self):
        (row,) = entries(anchor(text='Off Chops 1.24 Ground Zero 3.44'))
        self.assertEqual(row['odds'], [3.44, 1.24])
        self.assertEqual(row['provider_teams'], ['Off Chops', 'Ground Zero'])

    def test_an_unlabelled_positional_pair_does_not_establish_outcomes(self):
        self.assertEqual(entries(anchor(text='Ground Zero vs Off Chops 3.44 1.24')), [])

    def test_ambiguous_events_are_not_resolved_by_first_hit(self):
        self.assertEqual(entries(anchor(event='one') + anchor(event='two')), [])

    def test_same_url_with_conflicting_prices_is_not_hidden(self):
        self.assertEqual(entries(anchor() + anchor(text='Ground Zero 2.50 Off Chops 1.60')), [])

    def test_identical_duplicate_observations_do_not_conflict(self):
        self.assertEqual(len(entries(anchor() + anchor())), 1)

    def test_literal_original_markup_is_the_hashed_excerpt(self):
        html = "\n" + anchor().replace('href="', "href='").replace('id">', "id'>")
        (row,) = entries(html)
        self.assertIn(row['excerpt'], html)
        self.assertEqual(row['excerpt'], html.strip())
        self.assertEqual(row['excerpt_sha256'], hashlib.sha256(row['excerpt'].encode()).hexdigest())
        self.assertNotIn('automated capture', row['excerpt'])

    def test_inputs_are_never_mutated(self):
        before = copy.deepcopy(MATCH)
        entries(anchor())
        self.assertEqual(MATCH, before)

    def test_live_collector_has_the_import_it_references(self):
        self.assertIs(originate.egw_live, egw_live)


class OriginalResponseReplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.html = anchor()
        self.original = {'url': egw_live.INDEX_URL, 'observed_at': STAMP, 'html': self.html}
        self.saved = {'url': egw_live.INDEX_URL, 'observed_at': STAMP, 'entries': entries(self.html)}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        (self.root / (egw_live.INDEX_EVIDENCE + '.json')).write_text(json.dumps(self.original))
        (self.root / egw_live.EVIDENCE_NAME).write_text(json.dumps(self.saved))

    def load(self):
        return egw_live.load_live(self.root, [MATCH], {'aliases': []})

    def test_valid_original_response_replays(self):
        self.assertEqual(self.load(), self.saved['entries'])

    def test_missing_original_response_is_not_a_quote(self):
        (self.root / (egw_live.INDEX_EVIDENCE + '.json')).unlink()
        self.assertEqual(self.load(), [])

    def test_old_generated_prose_cannot_prove_an_undated_index(self):
        self.original['html'] = anchor(None)
        self.save()
        self.assertEqual(self.load(), [])

    def test_derived_probabilities_or_odds_cannot_be_self_attested(self):
        self.saved['entries'][0]['odds'] = [1.50, 2.60]
        self.save()
        self.assertEqual(self.load(), [])

    def test_observation_time_cannot_be_restamped(self):
        self.saved['observed_at'] = '2026-10-24T02:00:00Z'
        self.save()
        self.assertEqual(self.load(), [])

    def test_rebound_fixture_time_is_not_accepted(self):
        later = dict(MATCH, starts_at='2026-10-27T03:00:00Z')
        self.assertEqual(egw_live.load_live(self.root, [later], {}), [])

    def test_missing_unsafe_or_malformed_capture_is_inert(self):
        for value in (None, [], {}, {'url': 'https://example.com', 'entries': []}):
            with self.subTest(value=value):
                (self.root / egw_live.EVIDENCE_NAME).write_text(json.dumps(value))
                self.assertEqual(self.load(), [])
