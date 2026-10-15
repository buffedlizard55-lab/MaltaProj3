"""Regression: a researched model fallback whose Valve inputs lack a link must not crash the build.

Origin: scheduled production runs 38742696250 / 38797535468 and origination audit 38733458812 failed with a bare
KeyError: 'source_url' when a featured-unresolved fixture was resolved by the Valve model fallback. The root cause
(inputs emitted without source_url) is fixed in the originate layer; this test pins the renderer's own tolerance so
one missing link can never again take down a data refresh. A missing link must be shown as unverified, not invented.
"""
import unittest

from scripts import build


def match():
    return {'id': '1', 'teams': [{'id': 'a', 'name': 'WROTBERRY'}, {'id': 'b', 'name': 'ENCE'}], 'source_status': 'scheduled', 'starts_at': '2026-10-15T12:00:00Z',
            'locks_at': '2026-10-15T11:54:00Z', 'best_of': None, 'observed_at': '2026-10-15T10:13:43Z', 'source_url': 'https://www.hotspawn.com/matches/x-1',
            'source_api': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2', 'analysis': None, 'research': [], 'availability': 'open', 'limitations': []}


def fallback(with_input_links):
    inputs = [{'name': 'WBT', 'points': 1201, 'roster': ['a', 'b', 'c', 'd', 'e']}, {'name': 'ENCE', 'points': 1025, 'roster': ['f', 'g', 'h', 'i', 'j']}]
    if with_input_links:
        for row in inputs:
            row.update(source_url='https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md', snapshot_date='2026-10-05')
    return {'origination': {'method': 'model', 'label': 'Research model estimate (Valve official ratings)', 'observed_at': '2026-10-15T12:17:11Z', 'fair_decimal': [1.373, 3.679],
                            'probabilities': [0.728, 0.272], 'quotes': [], 'inputs': inputs, 'source': 'Valve official standings',
                            'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                            'limitations': ['Uncalibrated research model.']}}


class ModelFallbackRendering(unittest.TestCase):
    def test_inputs_without_their_own_link_fall_back_to_the_estimate_source_link(self):
        html = build.evidence(match(), '../', fallback(False))
        self.assertIn('Valve rating input: <strong>WBT</strong>', html)
        self.assertIn('snapshot unverified', html)
        self.assertIn('standings_global_2026_10_05.md', html)
        self.assertNotIn('None', html.split('Valve rating input')[1][:400])

    def test_complete_inputs_keep_their_own_link_and_snapshot_date(self):
        html = build.evidence(match(), '../', fallback(True))
        self.assertIn('snapshot 2026-10-05', html)

    def test_without_any_link_the_row_says_unverified_instead_of_inventing_one(self):
        fb = fallback(False)
        del fb['origination']['source_url']
        # the later 'Research source' link needs the estimate URL; only the per-input row is under test here
        fb['origination']['source_url'] = ''
        html = build.evidence(match(), '../', fb)
        self.assertIn('source link unverified', html)


if __name__ == '__main__':
    unittest.main()
