"""Session arena-c0bba79a: C0B-3 verification tests.

These tests pin *claims and contracts*, never mutable publisher output:

* the recorded lobby/API/snapshot reconciliation must be internally consistent
  (18 = 13 + 4 + 1, 79 - 4 + 3 = 78, lobby open set == API future set);
* the snapshot checker must reject probability pairs that do not sum to 1,
  picks that do not name the larger side, and counts that do not add — for any
  snapshot, current or synthetic;
* the date guard must only assert id-set equality for the exact snapshot the
  dossier names, so a future publisher refresh can never fail this suite;
* the executive-summary contract (in-site picks routes, one unresolved
  register, glance-row state markers, viewport meta) must hold of a built site
  and fail loudly when a landmark is removed.

No probability, pick or alias is written or asserted here; every expected
value comes from the checked-in dossier or from structural rules.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import c0bba79a_verify as v

ROOT = Path(__file__).resolve().parents[1]


def dossier() -> dict:
    return json.loads(v.DOSSIER.read_text(encoding='utf-8'))


class DossierArithmeticTests(unittest.TestCase):
    def test_checked_in_dossier_is_consistent(self) -> None:
        self.assertEqual(v.check_dossier_arithmetic(dossier()), [])

    def test_dropping_a_partition_member_fails(self) -> None:
        d = dossier()
        d['reconciliation']['snapshot_still_open_13'].pop()
        errors = v.check_dossier_arithmetic(d)
        self.assertTrue(any('do not cover' in e or 'expected 13' in e for e in errors))

    def test_overlapping_partition_fails(self) -> None:
        d = dossier()
        d['reconciliation']['snapshot_started_and_dropped_from_api_4'][0] = \
            d['reconciliation']['snapshot_still_open_13'][0]
        errors = v.check_dossier_arithmetic(d)
        self.assertTrue(errors)

    def test_new_fixture_inside_upcoming_fails(self) -> None:
        d = dossier()
        d['reconciliation']['open_on_live_site_but_absent_from_deployed_snapshot_3'][0] = \
            d['reconciliation']['snapshot_upcoming_18'][0]
        errors = v.check_dossier_arithmetic(d)
        self.assertTrue(any('also in the deployed upcoming list' in e for e in errors))

    def test_api_total_must_stay_78(self) -> None:
        d = dossier()
        for obs in d['observations']:
            if obs['kind'] == 'official Hotspawn scheduled-fixtures API':
                obs['figures']['records_total'] = 77
        errors = v.check_dossier_arithmetic(d)
        self.assertTrue(any('expected 78' in e for e in errors))

    def test_lobby_set_must_equal_api_future_set(self) -> None:
        d = dossier()
        for obs in d['observations']:
            if obs['kind'] == "rendered pick'em lobby (the reverse-engineering target)":
                cards = obs['figures']['rendered_open_card_ids']
                cards[-1], cards[-2] = cards[-2], cards[-1]  # swap keeps length, breaks parity? no—sets equal
                cards.append(cards.pop(0))  # rotate: set unchanged, list order differs but sorted equal
                obs['figures']['rendered_open_card_ids'] = cards[:-1] + ['9999999']
        errors = v.check_dossier_arithmetic(d)
        self.assertTrue(any('lobby open set' in e for e in errors))


class SnapshotBindingTests(unittest.TestCase):
    def _snapshot(self) -> dict:
        return json.loads(v.SNAPSHOT.read_text(encoding='utf-8'))

    def test_checked_in_snapshot_passes(self) -> None:
        self.assertEqual(v.check_snapshot_binding(dossier(), self._snapshot()), [])

    def test_probability_pair_must_sum_to_one(self) -> None:
        snap = self._snapshot()
        for m in snap['matches']:
            if m.get('analysis'):
                m['analysis']['probabilities'] = [0.7, 0.2]
                break
        errors = v.check_snapshot_binding(dossier(), snap)
        self.assertTrue(any('sum to' in e for e in errors))

    def test_pick_must_name_larger_side(self) -> None:
        snap = self._snapshot()
        for m in snap['matches']:
            a = m.get('analysis')
            if a and a['probabilities'][0] != a['probabilities'][1]:
                m['pick_index'] = 0 if a['probabilities'][0] < a['probabilities'][1] else 1
                break
        errors = v.check_snapshot_binding(dossier(), snap)
        self.assertTrue(any('does not name the larger side' in e for e in errors))

    def test_counts_must_add(self) -> None:
        snap = self._snapshot()
        snap['counts']['inventory'] = snap['counts']['inventory'] + 1
        errors = v.check_snapshot_binding(dossier(), snap)
        self.assertTrue(any('counts do not add' in e for e in errors))

    def test_date_guard_skips_set_equality_for_other_snapshots(self) -> None:
        """A refreshed publisher snapshot must not be compared to the dossier's
        recorded id lists - only the structural invariants still apply."""
        snap = self._snapshot()
        snap['generated_at'] = '2099-01-01T00:00:00Z'
        active = [m for m in snap['matches'] if m.get('availability') != 'past']
        for m in active:
            m['id'] = '9999999'  # completely different active set
        errors = v.check_snapshot_binding(dossier(), snap)
        self.assertFalse(any('upcoming set differs' in e for e in errors))

    def test_named_snapshot_missing_recorded_blank_fails(self) -> None:
        """Self-contained synthetic snapshot with the dossier's recorded state:
        every still-open fixture has featured analysis except the one recorded
        complete-layer id.  Emptying the recorded allowance must fail; keeping
        it must pass.  Built synthetically so the assertions do not depend on
        which publisher snapshot happens to be checked in."""
        d = dossier()
        rec = d['reconciliation']
        allowed = set(rec['still_open_without_featured_analysis'])
        matches = []
        for fid in rec['snapshot_upcoming_18']:
            blank = fid in allowed and fid in set(rec['snapshot_still_open_13'])
            matches.append({
                'id': fid,
                'availability': 'future',
                'analysis': None if blank else {
                    'probabilities': [0.6, 0.4],
                    'method': 'market',
                    'observed_at': v.DOSSIER_SNAPSHOT_GENERATED,
                    'source_url': 'https://example.org/official',
                },
                'pick_index': None if blank else 0,
            })
        snap = {
            'generated_at': v.DOSSIER_SNAPSHOT_GENERATED,
            'counts': {'inventory': 18, 'upcoming': 18, 'archived': 0},
            'matches': matches,
        }
        self.assertEqual(v.check_snapshot_binding(d, snap), [])
        d['reconciliation']['still_open_without_featured_analysis'] = []
        errors = v.check_snapshot_binding(d, snap)
        self.assertTrue(any('without a recorded complete-layer pick' in e for e in errors), errors)


class RenderedSummaryTests(unittest.TestCase):
    GOOD = (
        '<html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1">'
        '</head><body><a id="start-here"></a><h2>Picks at a glance</h2>'
        '<a href="./picks/">picks</a><a href="./unresolved/">unresolved</a>'
        '<a href="origination/#picks">full list</a>'
        '<p>Unresolved picks</p><div id="unresolved-register">'
        '<span data-glance-pick></span>'
        '<a href="origination/#match-1000001">Full detail</a></div></body></html>'
    )

    def _site(self, html: str) -> Path:
        tmp = Path(tempfile.mkdtemp()) / 'site'
        tmp.mkdir(parents=True, exist_ok=True)
        (tmp / 'index.html').write_text(html, encoding='utf-8')
        return tmp

    def test_contract_passes_on_minimal_summary(self) -> None:
        self.assertEqual(v.check_rendered_summary(self._site(self.GOOD)), [])

    def test_missing_start_here_fails(self) -> None:
        html = self.GOOD.replace('id="start-here"', 'id="elsewhere"')
        errors = v.check_rendered_summary(self._site(html))
        self.assertTrue(any('start-here' in e for e in errors))

    def test_missing_unresolved_register_fails(self) -> None:
        html = self.GOOD.replace('id="unresolved-register"', 'id="x"')
        errors = v.check_rendered_summary(self._site(html))
        self.assertTrue(any('unresolved-register' in e for e in errors))

    def test_missing_picks_route_fails(self) -> None:
        html = self.GOOD.replace('./picks/', './nope/')
        errors = v.check_rendered_summary(self._site(html))
        self.assertTrue(any('./picks/' in e for e in errors))

    def test_missing_viewport_fails(self) -> None:
        html = self.GOOD.replace('<meta name="viewport" content="width=device-width, initial-scale=1">', '')
        errors = v.check_rendered_summary(self._site(html))
        self.assertTrue(any('viewport' in e for e in errors))

    def test_missing_site_fails_loudly_not_silently(self) -> None:
        empty = Path(tempfile.mkdtemp())
        errors = v.check_rendered_summary(empty)
        self.assertTrue(any('not built' in e for e in errors))

    def test_run_records_explicit_skip_without_site(self) -> None:
        """A fresh checkout (CI runs unittest before build) must skip the
        rendered group explicitly, never fail it and never silently pass."""
        report = v.run(site=Path(tempfile.mkdtemp()))
        rendered = report['checks']['rendered_summary']
        self.assertEqual(rendered['status'], 'SKIP')
        self.assertIn('not built', rendered['note'])
        self.assertEqual(report['error_total'], 0)

    def test_checked_in_tree_passes_all_checks(self) -> None:
        report = v.run()
        self.assertEqual(report['error_total'], 0, json.dumps(report['checks'], indent=2))


if __name__ == '__main__':
    unittest.main()
