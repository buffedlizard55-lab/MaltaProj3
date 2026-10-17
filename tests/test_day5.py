"""Synthetic final-day vectors, never live results or published picks."""
import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from scripts import day5, twc_lines, twc_research
from scripts.audit_rows import audit_html
from scripts.domain import timestamp, iso
from scripts.verify_live import verify_day5
from tests.test_twc_day4 import example, record

NOW = timestamp('2026-10-17T20:00:00Z')


def data():
    d = example()
    d['inventory_observed_at'] = d['complete_picks']['source_snapshot_at'] = iso(NOW)
    for m, c in zip(d['matches'], d['complete_picks']['matches']):
        m['starts_at'] = c['starts_at'] = m['starts_at'].replace('2026-10-17', '2026-10-18')
        m['locks_at'] = c['locks_at'] = m['locks_at'].replace('2026-10-17', '2026-10-18')
        c['origination']['observed_at'] = iso(NOW)
    return d


class FinalDay(unittest.TestCase):
    def setUp(self):
        self.d = data()
        self.records = [record(start='2026-10-18T14:00:00Z')]
        for target, side in [('scripts.twc_research.load', lambda _: {'pages': copy.deepcopy(self.records)}),
                             ('scripts.twc_research.retained_discovery_urls', lambda _: set())]:
            p = patch(target, side_effect=side); p.start(); self.addCleanup(p.stop)

    def derive(self, now=NOW):
        return day5.derive(self.d, Path('data'), now)

    def test_keeps_every_weekly_fixture_and_exact_canonical_probabilities(self):
        g = self.derive()
        self.assertEqual(len(g['cards']), 2)
        for row, canonical in zip(g['cards'], self.d['complete_picks']['matches']):
            self.assertEqual(row['analysis'], canonical['origination'])
            self.assertTrue(row['state']['current'])
        self.assertEqual(g['counts']['current_picks'], 2)

    def test_day4_outcome_requires_completed_source_not_past_start(self):
        self.records.append(record(start='2026-10-17T14:00:00Z'))
        self.assertIsNone(self.derive()['day4_results'][0]['score'])
        self.records[-1]['facts'].update(finished=True, score=[2, 1])
        self.assertEqual(self.derive()['day4_results'][0]['score'], [2, 1])

    def test_other_day_never_becomes_a_final_day_fixture(self):
        self.records = [record(start='2026-10-19T14:00:00Z')]
        self.assertEqual(len(self.derive()['cards']), 2)
        self.assertTrue(all(r['hltv'] is None for r in self.derive()['cards']))

    def test_missing_line_is_blank_and_listed_unresolved_not_fifty_fifty(self):
        self.d['complete_picks']['matches'][0].update(origination=None, pick_index=None)
        g = self.derive()
        soup = BeautifulSoup(day5.render(g, '../'), 'html.parser')
        self.assertEqual([n.text for n in soup.select('.twc-day5-card')[0].select('.twc-prob strong')], ['—', '—'])
        self.assertEqual(g['counts']['unresolved'], 1)
        self.assertIn(g['cards'][0]['fixture']['id'], g['unresolved_ids'])

    def test_even_supported_line_has_no_direction_or_underdog(self):
        c = self.d['complete_picks']['matches'][0]
        c['origination']['probabilities'] = [0.5, 0.5]; c['pick_index'] = None
        row = self.derive()['cards'][0]
        self.assertIsNone(row['pick']); self.assertIsNone(row['underdog_screen'])
        self.assertIn('No edge — even line', day5.render(self.derive(), '../'))

    def test_model_does_not_promote_underdog(self):
        c = self.d['complete_picks']['matches'][0]
        c['origination']['method'] = 'model'
        self.assertIsNone(self.derive()['cards'][0]['underdog_screen'])

    def test_stale_and_locked_lines_never_recommend_a_current_pick(self):
        self.assertEqual(self.derive(timestamp('2026-10-18T05:00:01Z'))['counts']['current_picks'], 0)
        self.assertEqual(self.derive(timestamp('2026-10-18T20:00:00Z'))['counts']['current_picks'], 0)

    def test_wrong_inventory_binding_is_rejected(self):
        self.d['complete_picks']['source_snapshot_at'] = '2026-10-17T19:00:00Z'
        with self.assertRaises(ValueError): self.derive()

    def test_hltv_only_line_never_invents_a_hotspawn_lock_or_current_pick(self):
        self.d['matches'] = []; self.d['complete_picks']['matches'] = []
        line = {'probabilities': [0.6, 0.4], 'method': 'market', 'observed_at': iso(NOW),
                'teams': ['Aurora', '9z'], 'starts_at': '2026-10-18T14:00:00Z'}
        with patch('scripts.twc_lines.for_fixture', return_value=line):
            g = self.derive()
        row = g['cards'][0]
        self.assertEqual(row['pick'], 'Aurora')
        self.assertEqual(row['scope'], 'hltv-only')
        self.assertIsNone(row['fixture']['locks_at'])
        self.assertFalse(row['state']['current'])
        self.assertEqual(g['counts']['current_picks'], 0)
        soup = BeautifulSoup(day5.render(g, '../'), 'html.parser')
        self.assertTrue(all(n.has_attr('hidden') for n in soup.select('[data-current-only]')))

    def test_result_table_and_unresolved_rows_have_original_sources(self):
        self.records.append(record(start='2026-10-17T14:00:00Z'))
        html = day5.render(self.derive(), '../')
        self.assertEqual(audit_html(html, 'twc-picks/index.html')['violation'], 0)

    def test_public_per_fixture_parity_rejects_wrong_numbers_and_missing_cards(self):
        g = self.derive(); soup = BeautifulSoup(day5.render(g, '../'), 'html.parser')
        self.assertEqual(verify_day5(self.d, self.d['complete_picks'], {'day5': g}, g, soup), g['counts'])
        soup.select_one('.twc-prob strong').string = '99.9%'
        with self.assertRaisesRegex(ValueError, 'probabilities'):
            verify_day5(self.d, self.d['complete_picks'], {'day5': g}, g, soup)
        soup.select_one('.twc-day5-card').decompose()
        with self.assertRaisesRegex(ValueError, 'coverage'):
            verify_day5(self.d, self.d['complete_picks'], {'day5': g}, g, soup)


class DiscoveryAndReports(unittest.TestCase):
    def test_seed_links_replay_hashes_not_extracted_facts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); folder = root / twc_research.FOLDER; folder.mkdir(parents=True)
            url = 'https://www.hltv.org/matches/2399417/x-thunderpick-world-championship-2026'
            raw = f'<a href="{url.removeprefix("https://www.hltv.org")}">Final</a>'.encode()
            (folder / 'page.gz').write_bytes(gzip.compress(raw))
            page = {'request': {'status': 'ok', 'url': twc_research.EVENT_URL}, 'original_response': 'page.gz',
                    'stored_sha256': hashlib.sha256(raw).hexdigest()}
            (folder / 'source-report.json').write_text(json.dumps({'pages': [page]}))
            self.assertEqual(twc_research.retained_discovery_urls(root), {url})
            page['stored_sha256'] = '0' * 64
            (folder / 'source-report.json').write_text(json.dumps({'pages': [page]}))
            with self.assertRaises(ValueError): twc_research.retained_discovery_urls(root)

    def test_day5_never_loads_a_day4_report_as_its_own(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); folder = root / twc_research.FOLDER / 'evidence'; folder.mkdir(parents=True)
            (folder / twc_lines.REPORT.name).write_text(json.dumps({'day': '2026-10-17', 'records': []}))
            self.assertFalse(twc_lines.load(root, NOW, report_file=twc_lines.DAY5_REPORT)['available'])
            (folder / twc_lines.DAY5_REPORT.name).write_text(json.dumps({'day': '2026-10-18', 'records': []}))
            self.assertEqual(twc_lines.load(root, NOW, report_file=twc_lines.DAY5_REPORT)['day'], '2026-10-18')

    def test_report_path_cannot_escape(self):
        with self.assertRaises(ValueError):
            twc_lines.load(Path('data'), NOW, report_file=Path('../escape.json'))

class TournamentAlignment(unittest.TestCase):
    def test_reversed_canonical_pair_reorders_all_numbers_without_mutating_source(self):
        row = {'teams': ['Alpha', 'Beta'], 'starts_at': '2026-10-18T15:00:00Z',
               'probabilities': [0.6, 0.4], 'pick_index': 0,
               'providers': [{'probabilities': [0.6, 0.4], 'bid': [0.59,0.39], 'ask': [0.61,0.41], 'odds': [1.5,3]}],
               'movement': {'before': [0.7,0.3], 'delta': [-0.1,0.1], 'points': [-10,10]}}
        original = copy.deepcopy(row)
        aligned = twc_lines.for_fixture({'matches': [row]}, ['Beta','Alpha'], row['starts_at'])
        self.assertEqual(aligned['probabilities'], [0.4,0.6]); self.assertEqual(aligned['pick_index'], 1)
        self.assertEqual(aligned['providers'][0]['odds'], [3,1.5])
        self.assertEqual(aligned['movement']['points'], [10,-10]); self.assertEqual(row, original)

    def test_duplicate_fixture_cannot_take_first_line(self):
        row = {'teams':['Alpha','Beta'], 'starts_at':'2026-10-18T15:00:00Z'}
        self.assertIsNone(twc_lines.for_fixture({'matches':[row,copy.deepcopy(row)]}, row['teams'], row['starts_at']))
