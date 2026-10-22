"""93B-1: the coverage sentence on ``/picks/`` must add up, whoever writes it.

The live 22 October 2026 snapshot rendered

    33 of 33 matches below carry a pick. 11 come from an external market,
    esportsbook or aggregated bookmaker line, 12 more from the audited
    research ladder … and 0 remain blank

which accounts for 23 of the 33 rows: the first number was the *featured* count
(``data['counts']``) and the second the *fallback* count, while the page renders
the effective basis (featured pick, else researched fallback). Two sessions fixed
it independently — 4c972a51 on ``main`` and 93ba7221 on this branch — and the
merge kept main's wording.

These tests therefore assert the **arithmetic invariant, not the prose**: whatever
the sentence says, the published groups must add up to the rows the page renders,
a stale ``counts`` block must never reach it, and the executive summary must agree
with it. Synthetic fixtures only; no source is contacted and no probability is
invented.
"""
from __future__ import annotations

import re
import unittest
from datetime import datetime, timedelta, timezone

from scripts.build import glance, picks

BASE = datetime(2026, 10, 22, 1, 0, tzinfo=timezone.utc)
OBSERVED = BASE.strftime('%Y-%m-%dT%H:%M:%SZ')


def fixture(i, probability, *, hours=6, method='market', pick=0, resolved=True):
    start = BASE + timedelta(hours=hours)
    match = {
        'id': str(i),
        'teams': [{'id': f'a{i}', 'name': f'Alpha{i}'}, {'id': f'b{i}', 'name': f'Beta{i}'}],
        'competition': 'Test Cup', 'starts_at': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'locks_at': (start - timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'availability': 'open', 'source_url': f'https://www.hotspawn.com/matches/x-{i}',
        'source_api': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2',
        'lobby_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{i}',
        'evidence': 'data/evidence/hotspawn-fixtures.json', 'competition_id': '1',
        'series_format': None, 'lock_offset_sec': 360, 'source_end_at': None,
        'analysis': None, 'pick_index': None, 'observed_at': OBSERVED,
        'research': [], 'limitations': [], 'tier': 'c', 'source_status': 'scheduled', 'best_of': None,
    }
    if resolved:
        match['analysis'] = {
            'method': method,
            'label': 'Market-implied estimate' if method == 'market' else 'Valve-rating research estimate',
            'probabilities': [probability, 1 - probability],
            'fair_decimal': [round(1 / probability, 3), round(1 / (1 - probability), 3)],
            'observed_at': OBSERVED,
            'source': 'Polymarket' if method == 'market' else 'Valve official standings',
            'source_url': 'https://polymarket.com/event/cs2-x' if method == 'market'
                          else 'https://github.com/ValveSoftware/counter-strike_regional_standings',
            'quotes': [{'bid': probability - 0.01, 'ask': probability + 0.01},
                       {'bid': 1 - probability - 0.01, 'ask': 1 - probability + 0.01}]
            if method == 'market' else [],
            'limitations': [], 'snapshot_date': '2026-10-05', 'inputs': [],
            'event_id': 1231331, 'source_api': 'https://clob.polymarket.com/book?token_id=1',
        }
        match['pick_index'] = pick
    return match


def fallback_for(match, *, method='model', pick=0):
    probability = 0.75 if pick == 0 else 0.25
    return {
        'id': match['id'], 'teams': match['teams'], 'competition': match['competition'],
        'starts_at': match['starts_at'], 'locks_at': match['locks_at'], 'availability': 'open',
        'source_url': match['source_url'], 'pick_index': pick,
        'origination': {
            'method': method, 'label': 'Valve-rating research estimate',
            'probabilities': [probability, 1 - probability],
            'fair_decimal': [round(1 / probability, 3), round(1 / (1 - probability), 3)],
            'observed_at': OBSERVED, 'source': 'Valve official standings',
            'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
        },
        'research': [],
    }


def dataset():
    """2 featured money lines, 1 featured model, 1 researched fallback, 1 blank."""
    market_a, market_b = fixture(1, 0.70), fixture(2, 0.60, hours=7)
    model = fixture(3, 0.80, hours=8, method='model')
    researched = fixture(4, 0.55, hours=9, resolved=False)
    blank = fixture(5, 0.50, hours=10, resolved=False)
    blank['research'] = [{'stage': 'Primary: Polymarket', 'status': 'unresolved',
                          'detail': 'No exact-name market at this start time',
                          'source_url': 'https://polymarket.com/esports/cs2'}]
    return {
        'matches': [market_a, market_b, model, researched, blank],
        'fallbacks': {researched['id']: fallback_for(researched)},
        # Deliberately stale featured-only counts: the defect read these.
        'counts': {'inventory': 5, 'upcoming': 5, 'archived': 0, 'market': 99, 'bookmaker': 0,
                   'model': 42, 'unresolved': 7, 'picks': 3, 'no_edge': 0},
        'coverage_complete': True, 'inventory_crosscheck': 'complete',
        'inventory_observed_at': OBSERVED, 'generated_at': OBSERVED,
        'flags': [], 'sources': [], 'requests': [],
    }


def prose(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html)


def sentence_counts(html: str) -> dict:
    """Read the published groups out of the sentence without pinning the prose."""
    match = re.search(r'(\d+) of (\d+) match(?:es)? below carry a pick\.(.*?)Complete researched picks view',
                      prose(html), re.S)
    if not match:
        raise AssertionError('the picks-page coverage sentence is missing')
    with_pick, total, body = int(match.group(1)), int(match.group(2)), match.group(3)
    money = re.search(r'(\d+) come from an external', body)
    model = re.search(r'(\d+) from a (?:labelled )?research model', body)
    blank = re.search(r'(\d+) remain blank', body)
    return {'with_pick': with_pick, 'total': total,
            'money': int(money.group(1)) if money else 0,
            'model': int(model.group(1)) if model else 0,
            'blank': int(blank.group(1)) if blank else 0}


class PicksCoverageSentenceTests(unittest.TestCase):
    def test_groups_add_up_to_the_rows_with_a_pick(self):
        counts = sentence_counts(picks(dataset(), '', now=BASE))
        self.assertEqual(counts['total'], 5)
        self.assertEqual(counts['with_pick'], 4)
        self.assertEqual(counts['money'] + counts['model'], counts['with_pick'],
                         f"published groups do not add up: {counts}")
        self.assertEqual(counts['blank'], counts['total'] - counts['with_pick'])

    def test_stale_featured_counts_never_reach_the_sentence(self):
        html = prose(picks(dataset(), '', now=BASE))
        for number in ('99', '42'):
            self.assertNotIn(f'{number} come from', html)
            self.assertNotIn(f'{number} from a labelled research model', html)

    def test_summary_and_picks_page_publish_the_same_split(self):
        data = dataset()
        summary = prose(glance(data, '', now=BASE))
        counts = sentence_counts(picks(data, '', now=BASE))
        money = re.search(r'(\d+) from an external betting line', summary)
        model = re.search(r'(\d+) from a research model', summary)
        self.assertIsNotNone(money, summary[:400])
        self.assertIsNotNone(model, summary[:400])
        self.assertEqual(int(money.group(1)), counts['money'])
        self.assertEqual(int(model.group(1)), counts['model'])
        self.assertIn(f'{counts["with_pick"]} with a directional pick', summary)

    def test_a_single_row_still_adds_up(self):
        only = fixture(9, 0.66)
        html = picks({'matches': [only], 'fallbacks': {}, 'counts': {}, 'coverage_complete': True,
                      'inventory_observed_at': OBSERVED, 'generated_at': OBSERVED,
                      'flags': [], 'sources': [], 'requests': []}, '', now=BASE)
        counts = sentence_counts(html)
        self.assertEqual((counts['total'], counts['with_pick'], counts['money'], counts['blank']), (1, 1, 1, 0))


class CoverageCardConsistencyTests(unittest.TestCase):
    """The coverage page must not look like it contradicts the picks page."""

    def data(self):
        base = dataset()
        base['complete_picks'] = {
            'counts': {'active': 5, 'resolved': 5, 'unresolved': 0, 'with_pick': 5,
                       'consensus': 0, 'market': 2, 'bookmaker': 0, 'model': 3, 'alias_joined': 0},
            'matches': [],
        }
        base['counts'] = {'inventory': 8, 'upcoming': 5, 'archived': 3, 'market': 2,
                          'bookmaker': 0, 'model': 1, 'unresolved': 2, 'picks': 3, 'no_edge': 0}
        return base

    def test_the_card_names_the_complete_picks_figure_beside_the_featured_one(self):
        from scripts.build import coverage
        html = prose(coverage(self.data(), '', now=BASE))
        # The featured-only fraction ...
        self.assertIn('3 / 5', html)
        # ... and, in the same card, the researched list's complete figure.
        self.assertIn('the researched list has 5 of 5 with a pick and 0 unresolved', html)


if __name__ == '__main__':
    unittest.main()
