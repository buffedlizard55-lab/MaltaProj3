"""Pin the arena-e7d7a410 coverage audit.

The first draft of this audit read the *featured* `analysis` block in
`data/latest.json` and reported four fixtures as unpicked. That block is only the
featured exact-name method; the published pick lives in the complete feed
(`data/origination.json`). These tests keep the join on the complete feed, keep
fail-closed behaviour, and pin the arithmetic that the published rows rely on.
"""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.e7d7a410_audit import build_report, main, render_markdown


def match(fixture_id='1', teams=('Alpha', 'Beta'), start='2026-10-23T12:00:00Z', analysis=None):
    return {
        'id': fixture_id,
        'competition': 'Test Cup',
        'teams': [{'id': str(i), 'name': name} for i, name in enumerate(teams)],
        'starts_at': start,
        'locks_at': start,
        'availability': 'open',
        'analysis': analysis,
    }


def completed(fixture_id='1', teams=('Alpha', 'Beta'), start='2026-10-23T12:00:00Z',
              probabilities=(0.6, 0.4), pick_index=0, method='market',
              source_url='https://polymarket.com/event/test'):
    return {
        'id': fixture_id,
        'teams': [{'name': name} for name in teams],
        'starts_at': start,
        'pick_index': pick_index,
        'origination': {
            'method': method,
            'family': 'model' if method in {'model', 'network'} else 'money',
            'label': 'Market-implied estimate',
            'probabilities': list(probabilities),
            'source': 'Polymarket',
            'source_url': source_url,
            'observed_at': '2026-10-23T05:29:19Z',
            'limitation': 'No unique exact-name fixture on any external book.',
        },
    }


def snapshot(*matches):
    return {'generated_at': '2026-10-23T05:29:35Z', 'inventory_observed_at': '2026-10-23T05:29:12Z',
            'inventory_definition': 'All Hotspawn CS2 fixtures', 'inventory_crosscheck': 'complete',
            'counts': {'inventory': 92}, 'matches': list(matches)}


def feed(*rows, generated_at='2026-10-23T05:29:49Z'):
    return {'generated_at': generated_at, 'matches': list(rows)}


class AuditRowTests(unittest.TestCase):
    def test_a_complete_money_line_row_passes(self):
        report = build_report(snapshot(match()), feed(completed()))
        self.assertEqual(report['summary']['active_fixtures'], 1)
        self.assertEqual(report['summary']['with_pick'], 1)
        self.assertEqual(report['summary']['defective_rows'], 0)
        self.assertEqual(report['summary']['money_line_resolved'], 1)
        self.assertTrue(report['rows'][0]['money_line'])

    def test_missing_complete_row_is_a_defect_not_a_blank(self):
        report = build_report(snapshot(match()), feed())
        self.assertEqual(report['summary']['without_pick'], 1)
        self.assertEqual(report['summary']['defective_rows'], 1)
        self.assertIn('no complete-picks row', report['defects'][0]['defects'][0])

    def test_featured_block_alone_never_counts_as_coverage(self):
        featured = {'method': 'market', 'probabilities': [0.7, 0.3]}
        report = build_report(snapshot(match(analysis=featured)), feed())
        self.assertEqual(report['summary']['with_pick'], 0)
        self.assertEqual(report['summary']['featured_blank_active'], 0)
        self.assertEqual(report['summary']['defective_rows'], 1)

    def test_probabilities_must_sum_to_one(self):
        report = build_report(snapshot(match()), feed(completed(probabilities=(0.6, 0.5))))
        self.assertTrue(any('sum to' in d for d in report['defects'][0]['defects']))

    def test_probabilities_must_stay_inside_the_open_interval(self):
        report = build_report(snapshot(match()), feed(completed(probabilities=(1.0, 0.0))))
        self.assertTrue(any('outside (0, 1)' in d for d in report['defects'][0]['defects']))

    def test_pick_must_point_at_the_favourite(self):
        report = build_report(snapshot(match()), feed(completed(probabilities=(0.6, 0.4), pick_index=1)))
        self.assertTrue(any('not the favourite' in d for d in report['defects'][0]['defects']))

    def test_exact_tie_must_still_use_the_published_tie_break(self):
        report = build_report(snapshot(match()), feed(completed(probabilities=(0.5, 0.5), pick_index=0)))
        self.assertEqual(report['summary']['defective_rows'], 0)

    def test_source_must_be_https(self):
        report = build_report(snapshot(match()), feed(completed(source_url='http://example.test/x')))
        self.assertTrue(any('https' in d for d in report['defects'][0]['defects']))

    def test_team_names_and_start_time_must_match_the_inventory(self):
        report = build_report(snapshot(match()),
                              feed(completed(teams=('Alpha', 'Gamma'),
                                             start='2026-10-23T13:00:00Z')))
        joined = ' '.join(report['defects'][0]['defects'])
        self.assertIn('team names differ', joined)
        self.assertIn('start time differs', joined)

    def test_feed_rows_without_an_active_fixture_are_reported(self):
        report = build_report(snapshot(match()), feed(completed(), completed(fixture_id='999')))
        self.assertEqual(report['summary']['orphan_picks_feed_rows'], 1)
        self.assertEqual(report['orphan_picks_feed_rows'], ['999'])

    def test_model_only_rows_keep_their_limitation_and_are_counted_separately(self):
        model = completed(method='model', source_url='https://www.hltv.org/ranking/teams')
        report = build_report(snapshot(match()), feed(model))
        self.assertEqual(report['summary']['model_only_no_betting_line'], 1)
        self.assertEqual(report['summary']['money_line_resolved'], 0)
        self.assertEqual(report['model_only_no_line'][0]['limitation'],
                         'No unique exact-name fixture on any external book.')

    def test_an_unrecognised_method_is_a_defect(self):
        report = build_report(snapshot(match()), feed(completed(method='vibes')))
        self.assertTrue(any('unrecognised method' in d for d in report['defects'][0]['defects']))


class RenderTests(unittest.TestCase):
    def test_markdown_states_the_counts_and_names_every_no_line_fixture(self):
        report = build_report(snapshot(match()), feed(completed(method='model',
                                                                source_url='https://www.hltv.org/ranking/teams')))
        text = render_markdown(report)
        self.assertIn('| Active Hotspawn CS2 fixtures | **1** |', text)
        self.assertIn('Alpha vs Beta', text)
        self.assertIn('https://www.hltv.org/ranking/teams', text)
        self.assertIn('No unique exact-name fixture', text)

    def test_markdown_says_so_when_every_fixture_has_a_money_line(self):
        report = build_report(snapshot(match()), feed(completed()))
        self.assertIn('None: every active fixture had an external two-sided price', render_markdown(report))


class CommandTests(unittest.TestCase):
    def write(self, directory, latest, origination):
        latest_path = Path(directory) / 'latest.json'
        origination_path = Path(directory) / 'origination.json'
        latest_path.write_text(json.dumps(latest))
        origination_path.write_text(json.dumps(origination))
        return latest_path, origination_path

    def test_strict_exits_one_on_a_defect_and_zero_when_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            latest_path, origination_path = self.write(directory, snapshot(match()), feed())
            args = ['--latest', str(latest_path), '--origination', str(origination_path),
                    '--out', directory, '--strict']
            self.assertEqual(main(args), 1)
            self.assertTrue((Path(directory) / 'live-coverage-audit.md').exists())
            self.assertTrue((Path(directory) / 'live-coverage-audit.json').exists())
            origination_path.write_text(json.dumps(feed(completed())))
            self.assertEqual(main(args), 0)

    def test_strict_refuses_an_incomplete_or_empty_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            latest_path, origination_path = self.write(directory, snapshot(), feed())
            args = ['--latest', str(latest_path), '--origination', str(origination_path),
                    '--out', directory, '--strict']
            self.assertEqual(main(args), 1)
            empty = snapshot()
            empty['coverage_complete'] = False
            latest_path.write_text(json.dumps(empty))
            self.assertEqual(main(args), 1)

    def test_checked_in_snapshot_has_no_defective_row(self):
        root = Path(__file__).resolve().parent.parent
        latest = json.loads((root / 'data/latest.json').read_text())
        origination = json.loads((root / 'data/origination.json').read_text())
        report = build_report(latest, origination)
        self.assertGreater(report['summary']['active_fixtures'], 0)
        self.assertEqual(report['summary']['defective_rows'], 0, report['defects'])
        self.assertEqual(report['summary']['without_pick'], 0)


if __name__ == '__main__':
    unittest.main()
