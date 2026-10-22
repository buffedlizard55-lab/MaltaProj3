"""Regression suite for session arena-8877b140.

Locks the independent verification contracts from scripts/8877b140_verify.py:
- every active Hotspawn CS2 fixture is originated with a directional pick or an
  explicit, sourced unresolved limitation, and the published counts recompute;
- probability arithmetic, source-link and crowd-vote rules;
- executive-summary one-tap routes to the updated picks and unresolved
  sections, full glance coverage of active fixtures, and the separate
  unresolved/limitations register on the phone-first executive summary;
- viewport/CSP/https and mobile stylesheet contracts;
- every documented exception (non-allow-listed evidence host, CSP gap) is
  formally published on Flagged for Review, so a new exception cannot slip in.

The suite builds the site once into a temporary directory from the checked-in
saved evidence; it performs no network calls and edits no production file.
"""
from __future__ import annotations

import importlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.build import build

verify = importlib.import_module('scripts.8877b140_verify')

ROOT = Path(__file__).resolve().parents[1]
SESSION_DIR = ROOT / 'data' / 'research' / '8877b140'


class Contract8877Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        root = Path(cls.tmp.name)
        cls.data_dir = root / 'data'
        cls.site_dir = root / 'site'
        shutil.copytree(ROOT / 'data', cls.data_dir)
        build(cls.data_dir, cls.site_dir)
        cls.latest = json.loads((cls.data_dir / 'latest.json').read_text())
        cls.orig = json.loads((cls.data_dir / 'origination.json').read_text())
        cls.flags = json.loads((SESSION_DIR / 'flags.json').read_text())
        cls.dossier = verify.run(ROOT, cls.data_dir, cls.site_dir)
        cls.by_name = {c['check']: c for c in cls.dossier['checks']}
        cls.index_soup = BeautifulSoup((cls.site_dir / 'index.html').read_text(), 'html.parser')

    def test_dossier_has_no_hard_violation(self):
        failed = [c['check'] for c in self.dossier['checks'] if not c['ok']]
        self.assertEqual(failed, [], json.dumps(failed, indent=1))

    # --- inventory reconciliation ------------------------------------------
    def test_hotspawn_api_lobbies_and_feed_reconcile_with_unique_ids(self):
        results = {c['check']: c for c in verify.verify_inventory_reconciliation(self.data_dir)}
        check = results['hotspawn-inventory-reconciliation']
        self.assertTrue(check['ok'], check['detail'])
        detail = check['detail']
        self.assertEqual(detail['records'], detail['unique_records'])
        self.assertTrue(all(detail['sets_equal'].values()))

    # --- coverage contract -------------------------------------------------
    def test_every_active_fixture_is_originated_once(self):
        check = self.by_name['every-active-fixture-originated']
        self.assertTrue(check['ok'], check['detail'])
        active = [m for m in self.latest['matches']
                  if m.get('availability') in verify.ACTIVE_STATES]
        ids = [str(m['id']) for m in self.orig['matches']]
        self.assertEqual(sorted(ids), sorted({str(m['id']) for m in active}))
        self.assertEqual(len(ids), len(set(ids)))  # no duplicates

    def test_published_counts_recompute_from_rows(self):
        check = self.by_name['origination-counts-recompute']
        self.assertTrue(check['ok'], check['detail'])

    def test_probability_arithmetic_and_pick_direction_per_row(self):
        check = self.by_name['row-arithmetic-and-sources']
        self.assertTrue(check['ok'], check['detail'])
        for row in self.orig['matches']:
            origin = row.get('origination')
            if origin is None:
                continue
            probs = origin['probabilities']
            self.assertAlmostEqual(sum(probs), 1.0, places=6)
            self.assertTrue(all(0.0 < p < 1.0 for p in probs))
            if row['pick_index'] is not None:
                self.assertEqual(row['pick_index'], 0 if probs[0] > probs[1] else 1)
            if abs(probs[0] - probs[1]) <= 1e-9:
                self.assertIsNone(row['pick_index'])

    def test_blank_row_requires_limitation_and_sourced_trail(self):
        # Synthetic feed: a blank without limitation/trail must be a violation;
        # a blank with both must pass. No production file is touched.
        data = tempfile.TemporaryDirectory()
        self.addCleanup(data.cleanup)
        d = Path(data.name)
        latest = {'matches': [
            {'id': '1', 'availability': 'open'},
            {'id': '2', 'availability': 'open'},
        ]}
        orig = {
            'counts': {'active': 2, 'with_pick': 1, 'unresolved': 1},
            'policy': {'hotspawn_votes_used': False, 'fan_votes_used': False},
            'matches': [
                {'id': '1', 'origination': {'method': 'model',
                                            'probabilities': [0.6, 0.4],
                                            'source_url': 'https://bo3.gg/x',
                                            'fair_decimal': [1.667, 2.5],
                                            'limitations': ['uncalibrated'],
                                            'quotes': []},
                 'pick_index': 0, 'research': []},
                {'id': '2', 'origination': None, 'limitations': [], 'research': []},
            ],
        }
        (d / 'latest.json').write_text(json.dumps(latest))
        (d / 'origination.json').write_text(json.dumps(orig))
        results = {c['check']: c for c in verify.verify_origination_contract(d)}
        self.assertFalse(results['row-arithmetic-and-sources']['ok'])
        problems = {v['id']: v['problem']
                    for v in results['row-arithmetic-and-sources']['detail']['violations']}
        self.assertIn('2', problems)
        # Add the required limitation and sourced trail: the row now passes.
        orig['matches'][1]['limitations'] = ['No two-sided price or official rating.']
        orig['matches'][1]['research'] = [
            {'stage': 'HLTV research', 'status': 'unresolved',
             'source_url': 'https://www.hltv.org/matches', 'detail': 'no identity'}]
        (d / 'origination.json').write_text(json.dumps(orig))
        results = {c['check']: c for c in verify.verify_origination_contract(d)}
        self.assertTrue(results['row-arithmetic-and-sources']['ok'], results['row-arithmetic-and-sources']['detail'])

    def test_no_crowd_vote_inputs_are_claimed(self):
        self.assertTrue(self.by_name['no-crowd-vote-inputs']['ok'])

    # --- source link policy ------------------------------------------------
    def test_no_insecure_external_link_in_feeds(self):
        for name in ('origination.json-link-policy', 'latest.json-link-policy'):
            self.assertEqual(self.by_name[name]['detail']['insecure'], [])

    def test_every_non_allowlisted_feed_url_is_formally_flagged(self):
        flagged_urls = {u for f in self.flags for u in f.get('source_urls', [])}
        for name in ('origination.json-link-policy', 'latest.json-link-policy'):
            for url in self.by_name[name]['detail']['non_allowlisted']:
                self.assertIn(url, flagged_urls,
                              f'{url} is not on the official host list and is not covered by a Flagged-for-Review item')

    def test_documented_liquipedia_urls_are_evidence_only_not_probability_sources(self):
        # The two community-wiki URLs exist only inside alias evidence blocks;
        # no originated probability row may cite them as its source.
        for row in self.orig['matches']:
            origin = row.get('origination') or {}
            self.assertNotIn('liquipedia.net', origin.get('source_url', ''))
            for quote in origin.get('quotes', []):
                self.assertNotIn('liquipedia.net', quote.get('source_url', ''))
        # Every alias carrying Liquipedia evidence also carries HLTV evidence.
        for alias in self.orig.get('alias_registry', {}).get('aliases', []):
            urls = [e.get('url', '') for e in alias.get('evidence', [])]
            if any('liquipedia.net' in u for u in urls):
                self.assertTrue(any('hltv.org' in u for u in urls), alias.get('alias'))

    # --- executive summary findability (phone) -----------------------------
    def test_one_tap_routes_to_picks_and_unresolved_sections(self):
        check = self.by_name['executive-summary-one-tap-pick-routes']
        self.assertTrue(check['ok'], check['detail'])
        hrefs = {a.get('href') for a in self.index_soup.find_all('a')}
        self.assertIn('./origination/#picks', hrefs)
        self.assertIn('./origination/#unresolved', hrefs)
        self.assertTrue(self.index_soup.select_one('.exec-banner'))
        self.assertTrue(self.index_soup.find(id='start-here'))
        self.assertTrue(self.index_soup.select_one('.mobile-status-picks'))
        self.assertTrue(self.index_soup.select_one('.mobile-status-blank'))

    def test_glance_covers_every_active_fixture_with_both_probabilities(self):
        check = self.by_name['glance-covers-every-active-fixture']
        self.assertTrue(check['ok'], check['detail'])
        active = {str(m['id']) for m in self.latest['matches']
                  if m.get('availability') in verify.ACTIVE_STATES}
        glance_ids = {row.get('data-glance-id') for row in
                      self.index_soup.select('.glance-row')}
        self.assertEqual(active, glance_ids)
        # Every resolved glance row shows the picked side and its percentage.
        for row in self.index_soup.select('.glance-row'):
            if row.select_one('.glance-pick-label'):
                self.assertTrue(row.select_one('.glance-prob'))

    def test_separate_unresolved_register_and_limitations_live_on_summary(self):
        register = self.index_soup.find(id='unresolved-register')
        self.assertIsNotNone(register)
        self.assertTrue(register.find(id='unresolved-register-title'))
        # The universal limitations callout is part of the separate section.
        self.assertTrue(register.select_one('.unresolved-limits'))
        # Model-only picks have their own no-betting-line register on the page.
        self.assertIsNotNone(self.index_soup.find(id='no-line-register'))

    def test_every_current_page_has_viewport_and_only_known_csp_gap(self):
        detail = self.by_name['every-page-viewport-csp-https']['detail']
        self.assertEqual(detail['problems'], [])
        for relative in verify.CURRENT_PAGES:
            soup = BeautifulSoup((self.site_dir / relative).read_text(), 'html.parser')
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            self.assertIsNotNone(viewport, relative)
            self.assertIn('width=device-width', viewport.get('content', ''))
            has_csp = soup.find('meta', attrs={'http-equiv': 'Content-Security-Policy'}) is not None
            if not has_csp:
                self.assertIn(relative, verify.KNOWN_CSP_GAPS)
        # The single documented CSP gap must be published on Flagged for Review.
        self.assertTrue(any('Content-Security-Policy' in f['title'] or 'CSP' in f['title']
                            for f in self.flags))

    def test_no_insecure_links_in_built_pages(self):
        for html_path in self.site_dir.rglob('*.html'):
            if any(part in ('archive', 'docs') for part in html_path.parts):
                continue
            soup = BeautifulSoup(html_path.read_text(), 'html.parser')
            for anchor in soup.find_all('a', href=True):
                self.assertFalse(anchor['href'].startswith('http://'),
                                 f'{html_path}: {anchor["href"]}')

    def test_internal_links_and_anchors_resolve(self):
        check = self.by_name['internal-links-and-anchors-resolve']
        self.assertTrue(check['ok'], check['detail'])

    # --- mobile stylesheet -------------------------------------------------
    def test_mobile_stylesheet_contract(self):
        check = self.by_name['mobile-stylesheet-contract']
        self.assertTrue(check['ok'], check['detail'])
        detail = check['detail']
        self.assertLessEqual(detail['smallest_max_width_px'], 400)
        self.assertTrue(detail['sidebar_to_bottom_nav_swap'])
        self.assertTrue(detail['fixed_bottom_nav'])
        self.assertGreaterEqual(detail['largest_touch_min_height_px'], 44)

    # --- flags file itself -------------------------------------------------
    def test_flag_items_follow_the_review_schema(self):
        required = {'id', 'severity', 'title', 'detail', 'source_urls'}
        for flag in self.flags:
            self.assertTrue(required.issubset(flag), flag.get('id'))
            self.assertTrue(flag['source_urls'])
            for url in flag['source_urls']:
                self.assertTrue(url.startswith('https://'), url)


class EvidenceReplayTests(unittest.TestCase):
    """Independently recompute money-line probabilities from raw saved odds.

    These tests deliberately do not import the pipeline's de-vig or midpoint
    helpers: the formulas are re-derived here so a shared implementation bug
    cannot make the check and the publisher agree by construction.
    """

    @classmethod
    def setUpClass(cls):
        cls.orig = json.loads((ROOT / 'data' / 'origination.json').read_text())

    def test_bookmaker_quotes_recompute_to_their_stored_probabilities(self):
        checked = 0
        for row in self.orig['matches']:
            origin = row.get('origination') or {}
            for quote in origin.get('quotes', []):
                odds = quote.get('odds')
                if not odds or quote.get('family') == 'market':
                    continue
                # Independent proportional de-vig: raw implied 1/o, then normalize.
                implied = [1.0 / float(o) for o in odds]
                overround = sum(implied)
                rebuilt = [p / overround for p in implied]
                for got, want in zip(quote['probabilities'], rebuilt):
                    self.assertAlmostEqual(got, want, places=6,
                                           msg=(row['id'], quote.get('provider')))
                self.assertGreaterEqual(overround, 1.0)  # a real book carries a margin
                checked += 1
        self.assertGreater(checked, 0)  # the snapshot really contains book quotes

    def test_market_midpoints_recompute_from_bid_ask_and_normalize_to_the_row(self):
        checked = 0
        for row in self.orig['matches']:
            origin = row.get('origination') or {}
            market = [q for q in origin.get('quotes', []) if q.get('family') == 'market']
            if not market:
                continue
            for quote in market:
                self.assertAlmostEqual(quote['midpoint'],
                                       (quote['bid'] + quote['ask']) / 2, places=9)
                self.assertAlmostEqual(quote['spread'],
                                       quote['ask'] - quote['bid'], places=9)
            sides = [q['midpoint'] for q in market[:2]]
            if len(sides) == 2:
                total = sum(sides)
                rebuilt = [s / total for s in sides]
                for got, want in zip(origin['probabilities'], rebuilt):
                    self.assertAlmostEqual(got, want, places=6, msg=row['id'])
                checked += 1
        self.assertGreater(checked, 0)

    def test_single_source_rows_publish_that_source_exactly(self):
        for row in self.orig['matches']:
            origin = row.get('origination') or {}
            providers = {q.get('provider') for q in origin.get('quotes', [])}
            if len(providers) != 1:
                continue
            quote_probs = [q['probabilities'] for q in origin['quotes']
                           if 'probabilities' in q]
            if not quote_probs:
                continue
            # Every stored quote for a single-provider row equals the row output.
            for probs in quote_probs:
                for got, want in zip(origin['probabilities'], probs):
                    self.assertAlmostEqual(got, want, places=6, msg=row['id'])

    def test_every_published_probability_trails_a_saved_observation_timestamp(self):
        # No number without a dated observation: each quote carries its time.
        for row in self.orig['matches']:
            origin = row.get('origination') or {}
            for quote in origin.get('quotes', []):
                when = quote.get('observed_at') or quote.get('timestamp')
                self.assertTrue(when, (row['id'], quote.get('provider')))


if __name__ == '__main__':
    unittest.main()
