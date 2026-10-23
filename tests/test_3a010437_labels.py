"""Session arena-3a010437: a link's label must name where the link goes.

Published defect (2026-10-23 09:23Z build, row `1082980` LPH vs WBT Academy):
the phone summary showed **Thunderpick** over `https://bo3.gg/matches/...`,
because the old helper searched `source` *and* `source_url` with Thunderpick
listed first, so the relay's provider beat the link's own destination. A reader
who taps that link lands on bo3.gg, not on Thunderpick.

The helper now reads the destination host first and, when the row's own text
names a different provider, says the provider is relayed instead of choosing
one of the two silently. These tests are rendering contracts only; every record
is synthetic and no network source is contacted.
"""
from __future__ import annotations

import unittest

from scripts.build import analysis_source_label

#: (record, expected label, why)
CASES = [
    ({'method': 'market', 'source': 'Polymarket',
      'source_url': 'https://polymarket.com/event/cs2-x'}, 'Polymarket',
     'the link opens a Polymarket event page'),
    ({'method': 'bookmaker', 'source': 'Thunderpick',
      'source_url': 'https://thunderpick.io/api/matches'}, 'Thunderpick',
     'a documented feed endpoint still belongs to Thunderpick'),
    ({'method': 'bookmaker', 'source': 'Thunderpick (relayed by bo3.gg)',
      'source_url': 'https://bo3.gg/matches/lph-gaming-vs-wbt-academy-23-10-2026'},
     'bo3.gg (Thunderpick relay)',
     'the published 1082980 row: the link opens bo3.gg, so the label cannot say Thunderpick alone'),
    ({'method': 'bookmaker', 'source': 'bo3.gg relay',
      'source_url': 'https://bo3.gg/matches/x'}, 'bo3.gg',
     'provider and destination agree'),
    ({'method': 'market', 'source': 'Smarkets',
      'source_url': 'https://smarkets.com/event/1'}, 'Smarkets',
     'the exchange row names its own destination'),
    ({'method': 'reference', 'source': 'EGamersWorld (bookmaker average)',
      'source_url': 'https://egamersworld.com/counterstrike/match/x'}, 'EGamersWorld',
     'an aggregated average is named by the page it links'),
    ({'method': 'bookmaker', 'source': 'Thunderpick', 'source_url': ''}, 'Thunderpick',
     'with no URL the record name is the only evidence and is used as-is'),
    ({'method': 'consensus', 'source': 'Polymarket + Kalshi + Bovada',
      'source_url': 'https://polymarket.com/event/x'}, 'Consensus (3 sources)',
     'a median of three is still a consensus, never one provider'),
]


class LinkLabelNamesDestination(unittest.TestCase):
    def test_every_case(self):
        for record, expected, why in CASES:
            with self.subTest(expected=expected, why=why):
                self.assertEqual(analysis_source_label(record), expected)

    def test_the_defect_cannot_come_back_through_source_first_search(self):
        """The regression itself: `Thunderpick` must never label a bo3.gg href."""
        label = analysis_source_label({'method': 'bookmaker',
                                       'source': 'Thunderpick (relayed by bo3.gg)',
                                       'source_url': 'https://bo3.gg/matches/x'})
        self.assertNotEqual(label, 'Thunderpick')
        self.assertTrue(label.startswith('bo3.gg'), label)

    def test_a_relay_keeps_both_names_visible(self):
        label = analysis_source_label({'method': 'bookmaker', 'source': 'Thunderpick relayed by bo3.gg',
                                       'source_url': 'https://bo3.gg/matches/x'})
        self.assertIn('bo3.gg', label)
        self.assertIn('Thunderpick', label)


if __name__ == '__main__':
    unittest.main()
