"""Session arena-24e4d653: the coverage watchdog may only dispatch a publish.

The watchdog exists because the four-hour publisher is right about *age* but
blind to *coverage*: at 2026-10-26T00:49Z the live Hotspawn lobby exposed 81 CS2
cards while the 2026-10-25T23:03:48Z public snapshot carried 72, and nine cards
with future starts had no row, no probability and no pick. The freshness
watchdog keys on the snapshot's timestamp, so a two-hour-old snapshot with nine
holes looks perfectly fresh to it.

These tests pin the guard rails, because a dispatcher that fires on a bad reading
is worse than no dispatcher at all: it would publish a bundle built from a
half-read feed, or starve the real publisher by cancelling queued runs. Each test
names the failure it prevents. No test reads the network or the clock.
"""
import importlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

watch = importlib.import_module('scripts.24e4d653_coverage_watch')

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 26, 0, 49, tzinfo=timezone.utc)


def ms(when):
    return str(int(when.replace(tzinfo=timezone.utc).timestamp() * 1000))


def fixture(identity, hours_ahead=5.0, teams=('Alpha', 'Beta'), competition='Test Cup', status='scheduled'):
    return {
        'id': str(identity),
        'sport_alias': 'cs2',
        'status': status,
        'competition_name': competition,
        'scheduled_start_time': ms(NOW + timedelta(hours=hours_ahead)),
        'participants0_name': teams[0],
        'participants1_name': teams[1],
    }


def snapshot(*ids, generated_at='2026-10-25T23:03:48Z'):
    return {'generated_at': generated_at, 'matches': [{'id': str(i)} for i in ids]}


def run(identity, status, event='schedule', minutes_ago=0.0):
    created = NOW - timedelta(minutes=minutes_ago)
    return {'id': identity, 'status': status, 'event': event,
            'created_at': created.strftime('%Y-%m-%dT%H:%M:%SZ')}


class ParseTests(unittest.TestCase):
    def test_a_non_array_payload_yields_no_fixtures(self):
        # An error object from the API must never be read as "no cards to check".
        for payload in (None, {}, {'error': 'rate limited'}, 'nope', 3):
            self.assertEqual(watch.parse_fixtures(payload), [])

    def test_millisecond_starts_are_converted_and_missing_starts_are_not_invented(self):
        rows = watch.parse_fixtures([
            fixture(1, 2),
            {'id': '2', 'sport_alias': 'cs2', 'scheduled_start_time': 'not-a-number'},
            {'id': '3', 'sport_alias': 'cs2'},
        ])
        self.assertEqual(rows[0]['starts_at'], '2026-10-26T02:49:00Z')
        self.assertEqual(rows[0]['teams'], ['Alpha', 'Beta'])
        self.assertIsNone(rows[1]['starts_at'])
        self.assertIsNone(rows[2]['starts_at'])

    def test_records_without_an_id_or_from_another_sport_are_dropped(self):
        rows = watch.parse_fixtures([
            {'sport_alias': 'cs2', 'participants0_name': 'No Id'},
            {'id': '9', 'sport_alias': 'dota2'},
            {'id': '10', 'status': 'scheduled'},
        ])
        self.assertEqual([r['id'] for r in rows], ['10'])


class WindowTests(unittest.TestCase):
    def test_only_future_starts_are_eligible(self):
        # A card that has already started cannot carry a prematch pick, and the
        # project never manufactures a retrospective one.
        rows = watch.parse_fixtures([fixture(1, -1), fixture(2, 0.5), fixture(3, 1)])
        self.assertEqual([r['id'] for r in watch.future_fixtures(rows, NOW)], ['2', '3'])

    def test_undated_fixtures_are_skipped_rather_than_assumed_upcoming(self):
        self.assertEqual(watch.future_fixtures([{'id': '1', 'starts_at': None}], NOW), [])

    def test_a_malformed_start_is_skipped(self):
        self.assertEqual(watch.future_fixtures([{'id': '1', 'starts_at': '26 Oct 09:00'}], NOW), [])

    def test_the_order_is_earliest_first_so_the_reason_names_the_soonest_card(self):
        rows = watch.parse_fixtures([fixture(3, 9), fixture(1, 2), fixture(2, 4)])
        self.assertEqual([r['id'] for r in watch.future_fixtures(rows, NOW)], ['1', '2', '3'])


class DecideTests(unittest.TestCase):
    def test_a_new_upcoming_card_dispatches(self):
        live = watch.parse_fixtures([fixture(1, 3)])
        decision = watch.decide(live, snapshot(99), NOW)
        self.assertEqual(decision['action'], 'dispatch')
        self.assertEqual([f['id'] for f in decision['missing']], ['1'])
        self.assertIn('absent from the deployed snapshot', decision['reason'])

    def test_a_full_snapshot_is_silent(self):
        live = watch.parse_fixtures([fixture(1, 3), fixture(2, 6)])
        decision = watch.decide(live, snapshot(1, 2, 300), NOW)
        self.assertEqual(decision['action'], 'none')
        self.assertEqual(decision['missing'], [])

    def test_a_card_the_snapshot_carries_by_id_is_covered_even_when_names_differ(self):
        live = watch.parse_fixtures([fixture(1, 3, teams=('The Huns', 'HOTU'))])
        self.assertEqual(watch.decide(live, snapshot(1), NOW)['action'], 'none')

    def test_an_unreadable_fixture_feed_dispatches_nothing(self):
        # An empty feed is not evidence of a gap; dispatching on it would punish
        # the publisher for the watchdog's own outage.
        decision = watch.decide([], snapshot(1, 2), NOW)
        self.assertEqual(decision['action'], 'none')
        self.assertIn('no records', decision['reason'])

    def test_an_empty_snapshot_dispatches_nothing(self):
        # A snapshot with no rows is the freshness watchdog's job, and rebuilding
        # on it would let two watchdogs race each other.
        decision = watch.decide(watch.parse_fixtures([fixture(1, 3)]), snapshot(), NOW)
        self.assertEqual(decision['action'], 'none')
        self.assertIn('cannot', decision['reason'])

    def test_a_running_publish_holds_the_watchdog(self):
        live = watch.parse_fixtures([fixture(1, 3)])
        decision = watch.decide(live, snapshot(99), NOW, [run(7, 'in_progress')])
        self.assertEqual(decision['action'], 'none')
        self.assertIn('already running', decision['reason'])

    def test_a_queued_scheduled_publish_holds_the_watchdog(self):
        live = watch.parse_fixtures([fixture(1, 3)])
        decision = watch.decide(live, snapshot(99), NOW, [run(7, 'queued', minutes_ago=3)])
        self.assertEqual(decision['action'], 'none')
        self.assertIn('queued', decision['reason'])

    def test_any_queued_dispatch_holds_the_watchdog_however_old(self):
        # The publisher's concurrency group cancels a queued dispatch when a new
        # one arrives, so a second dispatch would silently drop the first.
        live = watch.parse_fixtures([fixture(1, 3)])
        decision = watch.decide(live, snapshot(99), NOW,
                                [run(7, 'queued', event='workflow_dispatch', minutes_ago=600)])
        self.assertEqual(decision['action'], 'none')
        self.assertIn('would cancel it', decision['reason'])

    def test_a_publish_that_started_moments_ago_is_left_to_finish(self):
        # A publish collects for ~25 minutes; dispatching into that window only
        # burns a queued run without improving coverage.
        live = watch.parse_fixtures([fixture(1, 3)])
        decision = watch.decide(live, snapshot(99), NOW, [run(7, 'completed', minutes_ago=10)])
        self.assertEqual(decision['action'], 'none')
        self.assertIn('letting it finish', decision['reason'])

    def test_a_completed_publish_older_than_the_quiet_window_does_not_block(self):
        live = watch.parse_fixtures([fixture(1, 3)])
        decision = watch.decide(live, snapshot(99), NOW, [run(7, 'completed', minutes_ago=45)])
        self.assertEqual(decision['action'], 'dispatch')

    def test_a_run_with_an_unparseable_start_cannot_block_forever_or_fire_early(self):
        live = watch.parse_fixtures([fixture(1, 3)])
        decision = watch.decide(live, snapshot(99), NOW,
                                [{'id': 7, 'status': 'completed', 'created_at': 'yesterday'}])
        self.assertEqual(decision['action'], 'dispatch')

    def test_the_decision_carries_the_evidence_it_acted_on(self):
        live = watch.parse_fixtures([fixture(1, 3), fixture(2, 8)])
        decision = watch.decide(live, snapshot(99), NOW)
        self.assertEqual(decision['live_records'], 2)
        self.assertEqual(decision['live_upcoming'], 2)
        self.assertEqual(decision['snapshot_records'], 1)
        self.assertEqual(decision['generated_at'], '2026-10-25T23:03:48Z')
        self.assertTrue(decision['reason'].endswith('no publish is queued or running'))


class ShippedGapTests(unittest.TestCase):
    """Replay the gap this session measured, from the dated record, not the network."""

    def setUp(self):
        self.dossier = json.loads((ROOT / 'data/research/24e4d653/live-coverage.json').read_text())

    def test_the_recorded_missing_set_reproduces_against_the_snapshot_it_names(self):
        # Reconstruct the 2026-10-25T23:03:48Z state from the record: every live
        # fixture it lists, minus the nine it measured absent. The watchdog must then
        # name exactly those nine and ask for a publish. Nothing here reads the live
        # feed, this checkout's snapshot or the clock.
        earlier = self.dossier['earlier_observation']
        absent = {f['id'] for f in earlier['missing']}
        present = [f['id'] for f in self.dossier['live_fixtures'] if f['id'] not in absent]
        live = [{'id': f['id'], 'teams': f['teams'], 'competition': f['competition'],
                 'starts_at': f['starts_at'], 'status': 'scheduled'} for f in self.dossier['live_fixtures']]
        old_snapshot = {'generated_at': earlier['snapshot_generated_at'],
                        'matches': [{'id': i} for i in present]}
        decision = watch.decide(live, old_snapshot, NOW)
        self.assertEqual({f['id'] for f in decision['missing']}, absent)
        self.assertEqual(decision['action'], 'dispatch')
        self.assertIn(earlier['snapshot_generated_at'], decision['reason'])

    def test_the_current_state_of_the_record_is_fully_covered(self):
        # The same nine ids were carried by the 2026-10-26T01:04:20Z publish; the
        # record must say so rather than leave the gap standing.
        self.assertEqual(self.dossier['counts']['missing_from_snapshot'], 0)
        self.assertEqual(self.dossier['counts']['carried_by_snapshot'],
                         self.dossier['counts']['live_future_fixtures'])
        self.assertTrue(all(f['in_published_snapshot'] for f in self.dossier['live_fixtures']))
        self.assertTrue(all(f.get('published_probabilities') for f in self.dossier['live_fixtures']))

    def test_the_earlier_gap_is_preserved_not_deleted(self):
        earlier = self.dossier['earlier_observation']
        self.assertEqual(earlier['missing_from_snapshot'], 9)
        self.assertEqual(len(earlier['missing']), 9)
        self.assertTrue(earlier['closed_by']['note'])
        text = (ROOT / 'data/research/24e4d653/live-coverage.md').read_text()
        self.assertIn('how it closed', text)
        self.assertIn('coverage_watch.py', text)


if __name__ == '__main__':
    unittest.main()
