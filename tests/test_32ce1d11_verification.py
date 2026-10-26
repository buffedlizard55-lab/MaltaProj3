"""Tests for the 32ce1d11 verification script (executive summary, mobile, picks coverage)."""
import unittest
import tempfile
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    'verify_32ce1d11',
    Path(__file__).parent.parent / 'scripts' / '32ce1d11_verify.py',
)
verify_32ce1d11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_32ce1d11)


class Verify32cTests(unittest.TestCase):
    def _minimal_index(self, n_picks=10, n_unresolved=0):
        return f'''<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
        <body>
        <nav class="mobile-nav" aria-label="Mobile navigation">
          <a href="./index.html" aria-current="page"><svg class="icon"></svg><span>Summary</span></a>
          <a href="./origination/#picks"><svg class="icon"></svg><span>Picks</span></a>
          <a href="./unresolved/"><svg class="icon"></svg><span>Unresolved</span></a>
          <a href="./edge/"><svg class="icon"></svg><span>Edge</span></a>
          <a href="./coverage/"><svg class="icon"></svg><span>Sources</span></a>
          <a href="./review/"><svg class="icon"></svg><span>Review</span></a>
        </nav>
        <nav class="mobile-status">
          <a class="mobile-status-picks"><strong>{n_picks}</strong><span>picks ready</span></a>
          <a class="mobile-status-blank"><strong>{n_unresolved}</strong><span>unresolved</span></a>
        </nav>
        <nav id="start-here">
          <a href="./#picks-at-a-glance"></a>
          <a href="./origination/#picks"></a>
          <a href="./#unresolved-register"></a>
          <a href="./origination/#unresolved"></a>
        </nav>
        <section id="picks-at-a-glance"><ol class="glance-list">
          <li class="glance-row" data-glance-id="1082858">
            <strong>Ground Zero vs Off Chops</strong>
            <span data-glance-pick>Pick</span><strong>Off Chops</strong>
            <span class="glance-prob">80.0%</span><span class="glance-other">Ground Zero 20.0%</span>
            <a class="source-link" href="https://www.hotspawn.com/m/gz-offchops">Hotspawn</a>
            <a class="source-link" href="https://polymarket.com/event/x">Polymarket</a>
          </li>
        </ol></section>
        <section id="unresolved-register"></section>
        </body></html>'''

    def _snapshot(self, n_active=1):
        return {
            'generated_at': '2026-10-26T00:00:00Z',
            'inventory_observed_at': '2026-10-26T00:00:00Z',
            'coverage_complete': True,
            'counts': {'inventory': 1, 'upcoming': n_active, 'archived': 0,
                       'market': 1, 'bookmaker': 0, 'model': 0,
                       'unresolved': 0, 'picks': 1, 'no_edge': 0},
            'matches': [
                {'id': '1082858',
                 'teams': [{'name': 'Ground Zero'}, {'name': 'Off Chops'}],
                 'availability': 'open',
                 'starts_at': '2026-10-26T03:00:00Z',
                 'locks_at': '2026-10-26T02:54:00Z',
                 'analysis': {'probabilities': [0.2, 0.8]}}
            ]
        }

    def _origination(self):
        return {
            'generated_at': '2026-10-26T00:00:00Z',
            'counts': {'active': 1, 'resolved': 1, 'unresolved': 0, 'with_pick': 1,
                       'market': 1, 'bookmaker': 0, 'model': 0},
            'matches': [
                {'id': 1082858,
                 'teams': [{'name': 'Ground Zero'}, {'name': 'Off Chops'}],
                 'pick_index': 1,
                 'origination': {'method': 'market',
                                 'probabilities': [0.2, 0.8],
                                 'source': 'Polymarket',
                                 'source_url': 'https://polymarket.com/event/x'}}
            ]
        }

    def test_pass_on_minimal_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'index.html').write_text(self._minimal_index())
            (root / 'snapshot.json').write_text(json.dumps(self._snapshot()))
            (root / 'origination.json').write_text(json.dumps(self._origination()))
            errors = []
            result = verify_32ce1d11.verify(root, errors)
            self.assertEqual(errors, [], f'errors: {errors}')
            self.assertEqual(result['glance_fixtures'], 1)
            self.assertTrue(result['snapshot_fresh'])

    def test_fail_when_mobile_nav_missing_tab(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            html = self._minimal_index().replace('<span>Sources</span>', '<span>Wrong</span>')
            (root / 'index.html').write_text(html)
            (root / 'snapshot.json').write_text(json.dumps(self._snapshot()))
            (root / 'origination.json').write_text(json.dumps(self._origination()))
            errors = []
            verify_32ce1d11.verify(root, errors)
            self.assertTrue(any('mobile-nav tabs' in e for e in errors),
                            f'expected nav-tab error, got: {errors}')

    def test_real_repo_passes(self):
        """Run against the actual repo root."""
        root = Path(__file__).parent.parent
        if not (root / 'snapshot.json').exists():
            self.skipTest('no snapshot.json in repo root')
        errors = []
        result = verify_32ce1d11.verify(root, errors)
        self.assertEqual(errors, [], f'errors on live repo: {errors}')
        self.assertGreaterEqual(result['glance_fixtures'], 10,
                                'expected at least 10 glance rows in current snapshot')
        self.assertEqual(result['mobile_status']['unresolved'], 0,
                         'live snapshot should report 0 unresolved')


if __name__ == '__main__':
    unittest.main()
