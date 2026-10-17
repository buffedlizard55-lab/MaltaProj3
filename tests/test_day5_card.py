"""Day-5 final-day card: sourced values, recomputed fallbacks, both pipeline days.

Guards the session arena-9b2a96e1 contract:

1. the dated research file records every source with an official https link and
   an observation time, and the published card never drifts away from it,
2. the labelled Valve-model fallback numbers are recomputed here from the saved
   first-party ratings snapshot — a hand-edited probability fails the suite,
3. the renderer exposes the final-day picks, the market-scan record and the
   contrarian guidance with their source links,
4. the scheduled runner prices fixtures on *both* playoff days, so the final-day
   fixtures cannot be skipped by the four-hour pipeline.
"""
import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import twc_lines, twc_research
from scripts.build_edge import edge_review, load_edge
from scripts.domain import valve_analysis

ROOT = Path(__file__).resolve().parents[1]
EDGE = ROOT / 'data' / 'edge-review.json'
RESEARCH = ROOT / 'data' / 'research' / '9b2a96e1' / 'day5-research.json'
RATINGS = ROOT / 'data' / 'evidence' / 'valve-ratings.json'
LATEST = ROOT / 'data' / 'latest.json'
NOW = datetime(2026, 10, 17, 20, 55, 0, tzinfo=timezone.utc)


def research():
    return json.loads(RESEARCH.read_text())


def body():
    data = json.loads(LATEST.read_text())
    return edge_review(data, '../', EDGE)


class ResearchEvidenceTests(unittest.TestCase):
    def test_every_research_source_is_https_and_timestamped(self):
        doc = research()
        blocks = [doc['day4_results'], doc['day5_fixtures'],
                  doc['market_scan']['probes'], doc['day5_pick_guidance']['sources'],
                  doc['hltv_analytics_context']['rows']]
        for group in blocks:
            for row in group:
                for key in ('sources',):
                    for src in row.get(key) or [row]:
                        if 'url' in src:
                            self.assertTrue(str(src['url']).startswith('https://'), src)
                            self.assertTrue(src.get('observed_at'), src)

    def test_market_scan_records_observed_absence_not_a_probability(self):
        scan = research()['market_scan']
        self.assertIn('No', scan['answer'][:40])
        self.assertTrue(scan['probes'])
        for probe in scan['probes']:
            self.assertEqual(probe['outcome'], 'no Day-5 listing')
            self.assertTrue(probe['observed_at'])

    def test_valve_fallback_is_recomputed_from_the_saved_snapshot(self):
        rows = json.loads(RATINGS.read_text())['rows']
        doc = research()
        for estimate in doc['valve_model_fallback']['estimates']:
            analysis, reason = valve_analysis({'teams': [{'name': n} for n in estimate['teams']]},
                                              rows, NOW, doc['market_scan']['observed_at'])
            self.assertIsNotNone(analysis, reason)
            for got, want in zip(analysis['probabilities'], estimate['probabilities']):
                self.assertAlmostEqual(got, want, places=6,
                                       msg=f"stored fallback drifted from Valve formula: {estimate['teams']}")


class PublishedCardTests(unittest.TestCase):
    def setUp(self):
        self.data = load_edge(EDGE)
        self.card = self.data['day_five_card']

    def test_card_matches_the_research_file(self):
        doc = research()
        for row, ref in zip(self.card['matches'], doc['day5_fixtures']):
            self.assertEqual(row['teams'], [ref['team_a'], ref['team_b']])
            self.assertEqual(row['starts_at'], ref['starts_at'])
            self.assertEqual(row['best_of'], ref['best_of'])
            self.assertEqual(row['url'], ref['url'])
        for row, ref in zip(self.card['semifinal_results'], doc['day4_results']):
            self.assertEqual(row['score'], ref['score'])
            self.assertEqual(row['maps'], ref['maps'])

    def test_fallback_probabilities_are_the_recomputed_values(self):
        rows = json.loads(RATINGS.read_text())['rows']
        for row in self.card['matches']:
            analysis, reason = valve_analysis({'teams': [{'name': n} for n in row['teams']]},
                                              rows, NOW, self.card['market_scan']['observed_at'])
            self.assertIsNotNone(analysis, reason)
            for got, want in zip(analysis['probabilities'], row['model_estimate']['probabilities']):
                self.assertAlmostEqual(got, want, places=6)

    def test_rendered_section_exposes_picks_scan_and_guidance(self):
        soup = BeautifulSoup(body(), 'html.parser')
        section = soup.find(id='day-five-card')
        text = section.get_text()
        self.assertIn('Falcons', text)
        self.assertIn('BETBOOM', text)
        self.assertIn('Default pick', text)
        self.assertIn('Score slip', text)
        self.assertIn('Contrarian watch', text)
        # Money-line blanks render as unverified, never as a fabricated price.
        self.assertIn('— unverified', text)
        self.assertNotIn('50.0%', text)
        scan = soup.find(id='day-five-market-scan')
        self.assertIsNotNone(scan)
        self.assertTrue(scan.select('a[href^="https://"]'), 'every probe keeps its record link')
        guidance = soup.find(id='day-five-guidance')
        self.assertIsNotNone(guidance)
        items = guidance.select('li')
        self.assertEqual(len(items), len(self.data['day_five_guidance']['principles']))
        # Every row keeps its own HLTV match page.
        for row in self.card['matches']:
            self.assertTrue(section.select(f'a[href="{row["url"]}"]'), row['url'])

    def test_grand_final_score_stays_blank_and_third_place_score_is_labelled(self):
        third = [r for r in self.card['matches'] if r['best_of'] == 3][0]
        final = [r for r in self.card['matches'] if r['best_of'] == 5][0]
        self.assertIsNotNone(third['score'])
        self.assertIn('Editorial', third['score']['basis'])
        self.assertIsNone(final['score'])
        self.assertTrue(final['score_limitation'])


class PipelineCoverageTests(unittest.TestCase):
    def test_target_days_cover_the_final_day(self):
        self.assertIn('2026-10-17', twc_research.TARGET_DAYS)
        self.assertIn('2026-10-18', twc_research.TARGET_DAYS)

    def test_fixtures_join_on_either_playoff_day(self):
        rows = [
            {'source_url': 'https://www.hltv.org/matches/2399415/falcons-vs-betboom-thunderpick-world-championship-2026',
             'observed_at': '2026-10-17T12:00:00Z',
             'facts': {'teams': ['Falcons', 'BETBOOM'], 'starts_at': '2026-10-17T17:00:00Z', 'finished': True}},
            {'source_url': 'https://www.hltv.org/matches/2399416/aurora-vs-falcons-thunderpick-world-championship-2026',
             'observed_at': '2026-10-17T20:26:00Z',
             'facts': {'teams': ['Aurora', 'Falcons'], 'starts_at': '2026-10-18T11:30:00Z', 'finished': False}},
            {'source_url': 'https://www.hltv.org/matches/2399417/furia-vs-betboom-thunderpick-world-championship-2026',
             'observed_at': '2026-10-17T20:27:00Z',
             'facts': {'teams': ['FURIA', 'BETBOOM'], 'starts_at': '2026-10-18T15:00:00Z', 'finished': False}},
        ]
        targets = twc_lines.fixtures(rows, twc_research.TARGET_DAYS)
        self.assertEqual([t['id'] for t in targets], ['twc-2399416', 'twc-2399417'],
                         'a finished series is never priced; both final-day fixtures join')
        self.assertEqual(twc_lines.fixtures(rows, '2026-10-18'), targets,
                         'a single-day call must cover the same final-day fixtures')

    def test_collect_report_records_every_target_day(self):
        seen = {}

        class FakeClient:
            manifest = []
            evidence = Path('/nonexistent-evidence')

            def save(self, name, report):
                seen['report'] = report

            def json(self, url, label):
                raise twc_lines.SourceError('offline test')

            def fetch(self, url, label):
                raise twc_lines.SourceError('offline test')

        rows = [{'source_url': 'https://www.hltv.org/matches/2399417/furia-vs-betboom-thunderpick-world-championship-2026',
                 'observed_at': '2026-10-17T20:27:00Z',
                 'facts': {'teams': ['FURIA', 'BETBOOM'], 'starts_at': '2026-10-18T15:00:00Z', 'finished': False}}]
        report = twc_lines.collect(FakeClient(), rows, {'aliases': []}, twc_research.TARGET_DAYS, NOW)
        self.assertEqual(report['days'], ['2026-10-17', '2026-10-18'])
        self.assertEqual(report['day'], '2026-10-17')
        self.assertEqual(len(report['records']), 1, 'the final-day fixture is priced-or-blanked, never skipped')
        self.assertEqual(report['records'][0]['fixture']['teams'], ['FURIA', 'BETBOOM'])
        self.assertIs(seen['report'], report)


if __name__ == '__main__':
    unittest.main()
