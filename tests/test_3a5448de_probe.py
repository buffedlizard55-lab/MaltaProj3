"""arena-3a5448de: probe target selection and bo3 binding are fail-closed."""
import unittest
from datetime import datetime, timezone

from scripts import __dict__ as _unused  # noqa: F401  (package import smoke)
import importlib

probe = importlib.import_module('scripts.3a5448de_probe')


def fixture(fid, featured, method, availability='open'):
    orig = {'method': method, 'label': 'x', 'probabilities': [0.6, 0.4]} if method else None
    return {'id': fid, 'availability': availability, 'featured_method': featured,
            'origination': orig, 'pick_index': 0 if method else None,
            'teams': [{'name': 'A'}, {'name': 'B'}], 'competition': 'C',
            'starts_at': '2026-10-22T10:00:00Z', 'source_url': 'https://example.com/x',
            'research': [], 'limitations': []}


class TargetsTests(unittest.TestCase):
    def test_featured_money_excluded_model_and_blank_included(self):
        doc = {'matches': [
            fixture('1', 'market', 'market'),          # featured money -> resolved same way
            fixture('2', None, 'model'),               # featured blank, model pick -> target
            fixture('3', None, None),                  # still blank -> target
            fixture('4', 'model', 'bookmaker'),        # upgraded to a money line -> already priced, excluded
            fixture('5', None, 'model', 'past'),       # past -> excluded
            fixture('6', None, 'guidance'),            # guidance only -> target
        ]}
        self.assertEqual([m['id'] for m in probe.targets(doc)], ['2', '3', '6'])


class Bo3BindingTests(unittest.TestCase):
    def row(self, slug, t1, t2, start, bet=None):
        r = {'id': slug, 'slug': slug, 'team1': {'name': t1}, 'team2': {'name': t2},
             'start_date': start, 'tournament': {'name': 'T'}, 'bo_type': 3}
        if bet is not None:
            r['bet_updates'] = bet
        return r

    def test_binds_both_names_within_tolerance_and_copies_relay_verbatim(self):
        fx = fixture('9', None, 'model')
        bet = {'provider': 'thunderpick', 'path': 'https://example.com/book',
               'team_1': {'name': 'A', 'coeff': 1.5, 'active': True, 'team_id': 1},
               'team_2': {'name': 'B', 'coeff': 2.5, 'active': True, 'team_id': 2}}
        out = probe.fixture_bo3(fx, [self.row('a-vs-b', 'B', 'A', '2026-10-22T10:10:00Z', bet)])
        self.assertEqual(len(out['bound']), 1)
        report = probe.fixture_report(fx, out, {'A': {'matches': []}, 'B': {'matches': []}})
        self.assertTrue(report['bo3_relay_two_sided_quote_present'])
        self.assertEqual(report['bo3_fixture']['bound'][0]['bet_updates']['team_1']['coeff'], 1.5)

    def test_one_sided_or_time_mismatched_relay_is_not_a_quote(self):
        fx = fixture('9', None, None)
        bet = {'provider': 'x', 'team_1': {'name': 'A', 'coeff': None},
               'team_2': {'name': 'B', 'coeff': 2.0}}
        out = probe.fixture_bo3(fx, [self.row('a-vs-b', 'A', 'B', '2026-10-22T12:00:00Z', bet)])
        self.assertEqual(out['bound'], [])
        self.assertEqual(len(out['near_time_mismatch']), 1)
        report = probe.fixture_report(fx, out, {})
        self.assertFalse(report['bo3_relay_two_sided_quote_present'])


class SurfaceTests(unittest.TestCase):
    def test_surface_records_status_and_exact_names_only(self):
        class R:
            status_code = 403
            url = 'https://www.hltv.org/matches'
            text = 'Just a moment... Team Alpha plays'

        rec = probe.probe_surface('HLTV', 'https://www.hltv.org/matches',
                                  ['Team Alpha', 'Absent'], get=lambda *a, **k: R())
        self.assertEqual(rec['http_status'], 403)
        self.assertEqual(rec['teams_listed'], ['Team Alpha'])
        self.assertIn('just a moment', rec['challenge_markers'])

    def test_surface_failure_is_evidence_not_exception(self):
        def boom(*a, **k):
            raise ConnectionError('no route')
        rec = probe.probe_surface('X', 'https://example.com', [], get=boom)
        self.assertIsNone(rec['http_status'])
        self.assertIn('ConnectionError', rec['error'])


if __name__ == '__main__':
    unittest.main()
