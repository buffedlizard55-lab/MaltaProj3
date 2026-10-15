"""Synthetic examples of the split-link HLTV contract observed 2026-10-15."""
import unittest
from scripts.sources import parse_hltv_matches, SourceError

TIME = '<a href="/matches/123/alpha-vs-beta"><div data-unix="1792058400000">12:00</div></a>'
TEAMS = '<a href="/matches/123/alpha-vs-beta"><div class="match-teamname">Alpha</div><div class="match-teamname">Beta</div></a>'


class HltvTests(unittest.TestCase):
    def test_split_links_join_only_on_identical_url(self):
        rows = parse_hltv_matches(TIME + TEAMS)
        self.assertEqual(rows, [{'teams': ['Alpha', 'Beta'], 'starts_at': '2026-10-15T10:00:00Z', 'source_url': 'https://www.hltv.org/matches/123/alpha-vs-beta'}])

    def test_pinned_duplicates_do_not_create_ambiguous_match(self):
        self.assertEqual(len(parse_hltv_matches((TIME + TEAMS) * 2)), 1)

    def test_different_urls_cannot_supply_missing_fields(self):
        with self.assertRaises(SourceError):
            parse_hltv_matches(TIME + TEAMS.replace('/123/', '/124/'))

    def test_conflicting_pinned_observations_fail_closed(self):
        with self.assertRaises(SourceError):
            parse_hltv_matches(TIME + TEAMS + TIME.replace('1792058400000', '1792062000000'))

    def test_challenge_page_is_not_successful_empty_feed(self):
        with self.assertRaises(SourceError):
            parse_hltv_matches('<html><title>Just a moment</title></html>')

    def test_original_combined_anchor_still_works(self):
        combined = TIME.replace('</a>', TEAMS.split('>', 1)[1])
        self.assertEqual(len(parse_hltv_matches(combined)), 1)
