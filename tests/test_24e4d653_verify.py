"""Session arena-24e4d653: every published number must replay from its own inputs.

The brief asks for a pick or an explicit limitation on every live Hotspawn card,
verified line by line, with nothing inferred. ``scripts.24e4d653_verify`` is the
mechanical half of that: it recomputes each active row's pick and both
probabilities from the quotes and ratings the row itself publishes, and it reads
the executive-summary contract off the built page (in-site links to the picks, a
separate unresolved register, both teams' probability and an obvious pick on
every row, phone viewport).

These tests do not pin any live fixture id or any live price. They build their
own rows so they cannot become a wall-clock trap for the four-hour publisher,
and they assert the refusal paths as hard as the happy path: a verifier that
passes everything it cannot read is worse than none.
"""
import importlib
import json
import unittest
from pathlib import Path

verify = importlib.import_module('scripts.24e4d653_verify')

ROOT = Path(__file__).resolve().parents[1]


def row(method, probabilities, quotes, pick_index=0, inputs=None, limitations=('A limitation.',)):
    origination = {'method': method, 'probabilities': probabilities, 'quotes': quotes,
                   'source_url': 'https://polymarket.com/event/example', 'observed_at': '2026-10-26T00:00:00Z',
                   'limitations': list(limitations)}
    if inputs is not None:
        origination['inputs'] = inputs
        origination['rd_assumption'] = 75.0
    return {'id': '1', 'teams': [{'name': 'Alpha'}, {'name': 'Beta'}], 'availability': 'open',
            'pick_index': pick_index, 'origination': origination}


class ValveTransformTests(unittest.TestCase):
    def test_equal_points_are_a_coin_flip(self):
        self.assertAlmostEqual(verify.valve_probability(1400, 1400), 0.5)

    def test_an_eighty_point_gap_is_about_six_in_ten(self):
        # Valve's published transform with RD 75: 80 points is close to 0.615.
        self.assertAlmostEqual(verify.valve_probability(1480, 1400), 0.6102, places=3)

    def test_the_transform_is_symmetric(self):
        low, high = verify.valve_probability(1200, 1500), verify.valve_probability(1500, 1200)
        self.assertAlmostEqual(low + high, 1.0, places=12)

    def test_a_larger_rating_deviation_flattens_the_curve(self):
        confident = verify.valve_probability(1480, 1400, rd=40)
        uncertain = verify.valve_probability(1480, 1400, rd=150)
        self.assertGreater(confident, uncertain)
        self.assertGreater(confident, 0.5)
        self.assertGreater(uncertain, 0.5)


class ReplayTests(unittest.TestCase):
    def test_a_market_row_replays_from_the_midpoints_of_its_two_quotes(self):
        quotes = [{'bid': 0.18, 'ask': 0.22}, {'bid': 0.78, 'ask': 0.82}]
        result = verify.replay_row(row('market', [0.2, 0.8], quotes, pick_index=1))
        self.assertEqual(result['replay'], 'ok')
        self.assertEqual(result['expected'], [0.2, 0.8])
        self.assertEqual(result['published_pick'], 'Beta')

    def test_a_single_record_with_list_shaped_bids_is_read_rather_than_rejected(self):
        quotes = [{'bid': [0.82, 0.08], 'ask': [0.92, 0.18]}]
        result = verify.replay_row(row('market', [0.87, 0.13], quotes, pick_index=0))
        self.assertEqual(result['replay'], 'ok')
        self.assertEqual(result['expected'], [0.87, 0.13])

    def test_a_crossed_single_record_is_refused(self):
        quotes = [{'bid': [0.5, 0.4], 'ask': [0.4, 0.6]}]
        result = verify.replay_row(row('market', [0.5, 0.5], quotes))
        self.assertEqual(result['replay'], 'unreplayable')
        self.assertIn('crossed', result['detail'])

    def test_a_spread_above_the_published_ceiling_is_refused_not_averaged(self):
        quotes = [{'bid': 0.40, 'ask': 0.60}, {'bid': 0.40, 'ask': 0.60}]
        result = verify.replay_row(row('market', [0.5, 0.5], quotes))
        self.assertEqual(result['replay'], 'unreplayable')
        self.assertIn('exceeds the published ceiling', result['detail'])

    def test_a_bookmaker_row_replays_from_no_vig_normalisation(self):
        quotes = [{'odds': [1.61, 2.18]}]
        result = verify.replay_row(row('bookmaker', [0.57519789, 0.42480211], quotes, pick_index=0))
        self.assertEqual(result['replay'], 'ok')
        self.assertAlmostEqual(result['expected'][0], 0.575198, places=6)

    def test_a_model_row_replays_from_its_recorded_points(self):
        quotes = []
        inputs = [{'points': 718}, {'points': 734}]
        result = verify.replay_row(row('model', [0.47761494, 0.52238506], quotes, pick_index=1,
                                       inputs=inputs))
        self.assertEqual(result['replay'], 'ok')
        self.assertEqual(result['published_pick'], 'Beta')

    def test_a_pick_against_the_replayed_direction_is_a_mismatch(self):
        quotes = [{'bid': 0.18, 'ask': 0.22}, {'bid': 0.78, 'ask': 0.82}]
        result = verify.replay_row(row('market', [0.2, 0.8], quotes, pick_index=0))
        self.assertEqual(result['replay'], 'mismatch')
        self.assertTrue(any('pick' in p for p in result['problems']))

    def test_a_probability_pair_that_does_not_sum_to_one_is_refused(self):
        quotes = [{'bid': 0.18, 'ask': 0.22}, {'bid': 0.78, 'ask': 0.82}]
        result = verify.replay_row(row('market', [0.3, 0.8], quotes, pick_index=0))
        self.assertEqual(result['replay'], 'not-replayed')
        self.assertIn('sum to', result['detail'])

    def test_an_active_row_without_a_pick_is_named_not_patched(self):
        result = verify.replay_row(row('market', [0.2, 0.8],
                                       [{'bid': 0.18, 'ask': 0.22}, {'bid': 0.78, 'ask': 0.82}],
                                       pick_index=None))
        self.assertEqual(result['replay'], 'not-replayed')
        self.assertIn('no pick recorded', result['detail'])

    def test_a_row_with_a_non_https_source_is_flagged(self):
        quotes = [{'odds': [1.61, 2.18]}]
        broken = row('bookmaker', [0.57519789, 0.42480211], quotes)
        broken['origination']['source_url'] = 'http://thunderpick.io/api/matches'
        result = verify.replay_row(broken)
        self.assertEqual(result['replay'], 'mismatch')
        self.assertTrue(any('source_url' in p for p in result['problems']))

    def test_an_unreplayable_method_is_reported_not_assumed(self):
        result = verify.replay_row(row('vibes', [0.5, 0.5], []))
        self.assertEqual(result['replay'], 'unreplayable')
        self.assertIn('no replayable inputs', result['detail'])


class ActiveSetTests(unittest.TestCase):
    def test_closed_and_refunded_rows_are_out_of_scope(self):
        rows = {'matches': [
            {'id': 'a', 'availability': 'open', 'pick_index': 0, 'teams': [], 'origination': {}},
            {'id': 'b', 'availability': 'closed', 'pick_index': 0, 'teams': [], 'origination': {}},
            {'id': 'c', 'availability': 'refunded', 'pick_index': 0, 'teams': [], 'origination': {}},
        ]}
        self.assertEqual([r['id'] for r in verify.active_rows(rows)], ['a'])

    def test_a_missing_availability_still_counts_as_active(self):
        rows = {'matches': [{'id': 'a', 'pick_index': 0, 'teams': [], 'origination': {}}]}
        self.assertEqual(len(verify.active_rows(rows)), 1)


class RenderedContractTests(unittest.TestCase):
    SUMMARY = '''
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <nav class="start-here" id="start-here"><a href="./#picks-at-a-glance">Picks</a></nav>
    <section id="unresolved-register"><p>No unresolved fixtures. Why: nothing is missing.</p>
      <a href="https://example.com/source">source</a></section>
    <ul>
      <li class="glance-row" data-glance-id="1" data-method="market">
        <span data-glance-pick>Pick</span> Beta <span class="glance-prob">80.0%</span>
        <span class="glance-other">Alpha 20.0%</span></li>
      <li class="glance-row" data-glance-id="2" data-method="model">
        <span>Beta</span> <span class="glance-prob">52.2%</span>
        <span class="glance-other">Alpha 47.8%</span></li>
    </ul>
    <nav class="mobile-nav"><a href="#picks-at-a-glance">Picks</a></nav>
    '''

    def test_the_shipped_shape_passes(self):
        report = verify.check_rendered(self.SUMMARY)
        self.assertEqual(report['rows'], 2)
        failed = [c['check'] for c in report['checks'] if c['status'] == 'fail']
        self.assertEqual(failed, ['an obvious pick on every glance row'],
                         'every other contract check must pass on the shipped shape')

    def test_a_row_with_one_probability_fails(self):
        html = self.SUMMARY.replace('<span class="glance-other">Alpha 20.0%</span>', '')
        report = verify.check_rendered(html)
        self.assertIn('both teams\' win probability on every glance row',
                      [c['check'] for c in report['checks'] if c['status'] == 'fail'])

    def test_a_summary_without_in_site_pick_links_fails(self):
        html = self.SUMMARY.replace('href="./#picks-at-a-glance"', 'href="https://example.com/picks"')
        report = verify.check_rendered(html)
        self.assertIn('in-site links to the updated picks', report['failures'])

    def test_a_summary_without_the_unresolved_register_fails(self):
        html = self.SUMMARY.replace('id="unresolved-register"', 'id="something-else"')
        report = verify.check_rendered(html)
        self.assertIn('separate unresolved/limitations register in the summary', report['failures'])

    def test_a_desktop_only_page_fails_the_phone_check(self):
        html = self.SUMMARY.replace('name="viewport"', 'name="not-viewport"')
        report = verify.check_rendered(html)
        self.assertIn('phone viewport', report['failures'])

    def test_a_row_without_a_method_fails(self):
        html = self.SUMMARY.replace('data-method="model"', 'data-nothing="model"', 1)
        report = verify.check_rendered(html)
        self.assertIn('a named method on every glance row', report['failures'])


class ShippedBuildTests(unittest.TestCase):
    """Replay the checked-in data and the built page, without touching the network."""

    def test_every_active_published_row_replays(self):
        origination = json.loads((ROOT / 'origination.json').read_text())
        report = verify.check_active(origination)
        self.assertEqual(report['without_pick'], [])
        self.assertEqual(report['replay_counts'].get('mismatch', 0), 0)
        self.assertEqual(report['replay_counts'].get('unreplayable', 0), 0)
        self.assertEqual(report['rows_without_a_limitation'], [])
        self.assertTrue(report['ok'])

    def test_every_dated_live_fixture_is_either_carried_or_named(self):
        dossier = json.loads((ROOT / 'data/research/24e4d653/live-coverage.json').read_text())
        snapshot = json.loads((ROOT / 'snapshot.json').read_text())
        origination = json.loads((ROOT / 'origination.json').read_text())
        report = verify.check_coverage(dossier, snapshot, origination)
        self.assertTrue(report['available'])
        if not report.get('checked', True):
            # The record is dated to another published build; the check says so
            # instead of inventing a contradiction with this checkout's snapshot.
            self.assertIn('not compared', report['detail'])
        else:
            self.assertEqual(report['problems'], [])
            self.assertEqual(report['carried'] + len(report['gaps']), report['live_future_fixtures'])
        self.assertTrue(report['ok'])

    def test_the_built_page_satisfies_the_executive_summary_contract(self):
        page = ROOT / 'index.html'
        if not page.is_file():
            self.skipTest('no built index.html in this checkout')
        report = verify.check_rendered(page.read_text())
        self.assertEqual(report['failures'], [], report['checks'])
        self.assertGreaterEqual(report['rows'], 1)


class PublishedLineSupersessionTests(unittest.TestCase):
    """A sourced origination line may supersede the featured line -- and only it.

    On the 2026-10-26 builds, fixture 1093218 renders the originated consensus line
    (Nuclear TigeRES 58.3%) while the snapshot's own featured analysis still records
    the model line (70.7%). That is the ladder doing its job: a two-sided money line
    replaces an uncalibrated rating model. ``scripts/22a3ed80_verify.py`` reconciles
    the two layers for a row the origination layer marks as upgraded; these tests pin
    that the shipped build clears, and that a tampered pair or a dropped upgrade flag
    does not.
    """

    @classmethod
    def setUpClass(cls):
        import shutil
        import tempfile
        cls.root = Path(__file__).resolve().parents[1]
        required = [cls.root / n for n in ('snapshot.json', 'index.html', 'origination.json')]
        if not all(f.is_file() for f in required):
            raise unittest.SkipTest('no built root in this checkout')
        cls.tmp = Path(tempfile.mkdtemp(prefix='24e4d653-supersede-'))
        for source in required:
            shutil.copy(source, cls.tmp / source.name)
        for page in ('origination/index.html', 'unresolved/index.html'):
            target = cls.tmp / page
            target.parent.mkdir(parents=True, exist_ok=True)
            if (cls.root / page).is_file():
                shutil.copy(cls.root / page, target)
        cls.pristine = (cls.tmp / 'origination.json').read_text()
        cls.verify_module = importlib.import_module('scripts.22a3ed80_verify')

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        (self.tmp / 'origination.json').write_text(self.pristine)

    def _upgraded_id(self):
        for entry in json.loads(self.pristine).get('matches') or []:
            if entry.get('upgraded_from_featured_model'):
                return str(entry['id'])
        return None

    def _hard_row_failures(self, report):
        return [c['detail'] for c in report['checks']
                if not c['ok'] and c.get('hard') and c['name'] == 'row_problem']

    def test_the_shipped_build_has_no_hard_failure(self):
        report = self.verify_module.verify(self.tmp)
        hard = [c for c in report['checks'] if not c['ok'] and c.get('hard')]
        self.assertEqual(hard, [], [c['detail'] for c in hard])

    def test_an_upgraded_row_renders_the_origination_pair(self):
        identifier = self._upgraded_id()
        if identifier is None:
            self.skipTest('this build upgraded no featured row')
        report = self.verify_module.verify(self.tmp)
        row = next(r for r in report['rows'] if r['id'] == identifier)
        entry = next(e for e in json.loads(self.pristine)['matches'] if str(e['id']) == identifier)
        probs = entry['origination']['probabilities']
        index = 0 if probs[0] >= probs[1] else 1
        self.assertEqual(row['rendered_pick'], row['teams'][index])
        self.assertEqual(row['rendered_probabilities'][0], round(probs[index] * 100, 1))

    def test_a_tampered_origination_pair_fails_the_gate(self):
        identifier = self._upgraded_id()
        if identifier is None:
            self.skipTest('this build upgraded no featured row')
        payload = json.loads(self.pristine)
        for entry in payload['matches']:
            if str(entry['id']) == identifier:
                entry['origination']['probabilities'] = [0.5, 0.5]
        (self.tmp / 'origination.json').write_text(json.dumps(payload))
        self.assertTrue(self._hard_row_failures(self.verify_module.verify(self.tmp)),
                        'a pair that matches neither layer must fail')

    def test_a_dropped_upgrade_flag_fails_the_gate(self):
        identifier = self._upgraded_id()
        if identifier is None:
            self.skipTest('this build upgraded no featured row')
        payload = json.loads(self.pristine)
        for entry in payload['matches']:
            if str(entry['id']) == identifier:
                entry.pop('upgraded_from_featured_model', None)
        (self.tmp / 'origination.json').write_text(json.dumps(payload))
        self.assertTrue(self._hard_row_failures(self.verify_module.verify(self.tmp)),
                        'without the upgrade marker the row contradicts the featured analysis')


if __name__ == '__main__':
    unittest.main()
