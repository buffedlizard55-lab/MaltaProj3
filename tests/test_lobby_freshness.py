"""Hotspawn inventory reconciliation: fresh renders, one retry, self-explaining failures.

Evidence (probe run, 2026-10-15, data/research/1112299f/lobby-probe.json): the server-rendered lobby pages are CDN-cached
(X-Cache HIT, Age 4,000-5,000 s) while the fixture API is live; a cache-busting query string returns a fresh render
(MISS, Age 0). These tests use a fake client, never the network.
"""
import json
import unittest
from unittest import mock

from scripts import sources
from scripts.sources import LOBBY, CS2_LOBBY, FIXTURES_API, SourceError, disagreement, fresh_url, hotspawn


def row(i, sport='cs2'):
    return {'id': str(i), 'sport_alias': sport, 'participants0_name': 'A', 'participants1_name': 'B'}


def page(rows):
    state = {'k': {'s': 200, 'u': 'https://x/api/v1/fixtures', 'b': rows}, 'p': {'s': 200, 'u': 'https://x/api/v1/permalinks', 'b': {'permalinks': {str(r['id']): 'https://www.hotspawn.com/matches/m-' + str(r['id']) for r in rows}}}}
    return '<html><script id="ng-state" type="application/json">' + json.dumps(state) + '</script></html>'


class FakeClient:
    """Serves queued page/API payloads per call and records every requested URL."""

    def __init__(self, rounds, refuse_fresh=False, headers=None, block=()):
        self.rounds, self.refuse_fresh, self.headers = list(rounds), refuse_fresh, headers or {}
        self.block = set(block)
        self.urls, self.manifest, self.saved, self.n = [], [], {}, -1

    def fetch(self, url, label, **kw):
        self.urls.append(url)
        if label in self.block:
            raise SourceError(label + ': 403 Client Error: Forbidden for url: ' + url)
        if self.refuse_fresh and 'cb=' in url:
            raise SourceError(label + ': 403')
        if label == 'hotspawn-lobby':
            self.n += 1  # one round per lobby request; the CS2 page and API reuse that round
        rnd = self.rounds[min(self.n, len(self.rounds) - 1)]
        text = page(rnd['lobby'] if label == 'hotspawn-lobby' else rnd['cs2'])
        return text, {'observed_at': '2026-10-16T08:00:00Z', **self.headers}

    def json(self, url, label, **kw):
        self.urls.append(url)
        rnd = self.rounds[min(self.n, len(self.rounds) - 1)]
        return rnd['api'], {'observed_at': '2026-10-16T08:00:01Z'}

    def save(self, name, data):
        self.saved[name] = data
        return 'data/evidence/' + name + '.json'


class FreshUrl(unittest.TestCase):
    def test_adds_a_unique_query_string_and_keeps_existing_ones(self):
        self.assertEqual(fresh_url('https://play.hotspawn.com/lobby', 1792000000.9), 'https://play.hotspawn.com/lobby?cb=1792000000')
        self.assertEqual(fresh_url('https://x/y?a=1', 5), 'https://x/y?a=1&cb=5')

    def test_two_calls_in_different_seconds_get_different_keys(self):
        self.assertNotEqual(fresh_url('https://x/y', 1), fresh_url('https://x/y', 2))


class Reconciliation(unittest.TestCase):
    def agree(self, ids):
        rows = [row(i) for i in ids]
        return {'lobby': rows, 'cs2': rows, 'api': rows}

    def test_agreement_returns_the_api_rows_and_requests_fresh_renders(self):
        client = FakeClient([self.agree([1, 2, 3])])
        rows, links, health = hotspawn(client)
        self.assertEqual([r['id'] for r in rows], ['1', '2', '3'])
        self.assertEqual(health['status'], 'ok')
        pages = [u for u in client.urls if u != FIXTURES_API]
        self.assertTrue(pages[0].startswith(LOBBY + '?cb=') and pages[1].startswith(CS2_LOBBY + '?cb='))
        self.assertEqual(client.saved['hotspawn-context']['lobby_url'], LOBBY)  # evidence still names the canonical page

    def test_a_refused_fresh_render_falls_back_to_the_plain_page(self):
        client = FakeClient([self.agree([1])], refuse_fresh=True)
        rows, _, _ = hotspawn(client)
        self.assertEqual(len(rows), 1)
        self.assertIn(LOBBY, client.urls)
        self.assertIn(CS2_LOBBY, client.urls)

    def test_a_race_between_the_requests_is_absorbed_by_one_retry(self):
        racing = {'lobby': [row(1)], 'cs2': [row(1)], 'api': [row(1), row(2)]}
        client = FakeClient([racing, self.agree([1, 2])])
        with mock.patch.object(sources.time, 'sleep') as sleep:
            rows, _, _ = hotspawn(client)
        sleep.assert_called_once_with(5)
        self.assertEqual([r['id'] for r in rows], ['1', '2'])

    def test_a_persistent_disagreement_still_fails_and_names_the_ids_and_cache_state(self):
        persistent = {'lobby': [row(1), row(9)], 'cs2': [row(1), row(2)], 'api': [row(1), row(2)]}
        client = FakeClient([persistent], headers={'cache_status': 'HIT', 'cache_age_sec': '5040'})
        with mock.patch.object(sources.time, 'sleep'):
            with self.assertRaises(SourceError) as ctx:
                hotspawn(client)
        message = str(ctx.exception)
        self.assertIn('disagree', message)
        self.assertIn("in the API only ['2']", message)
        self.assertIn("in the page only ['9']", message)
        self.assertIn('cache_status=HIT', message)
        self.assertIn('cache_age_sec=5040', message)
        self.assertNotIn('CS2 lobby page', message)  # that page agrees with the API

    def test_other_games_never_count_as_cs2_fixtures(self):
        rnd = {'lobby': [row(1), row(7, 'lol')], 'cs2': [row(1)], 'api': [row(1), row(8, 'lol')]}
        rows, _, _ = hotspawn(FakeClient([rnd]))
        self.assertEqual([r['id'] for r in rows], ['1'])

    def test_duplicate_ids_are_refused(self):
        rnd = {'lobby': [row(1), row(1)], 'cs2': [row(1)], 'api': [row(1)]}
        with self.assertRaises(SourceError):
            hotspawn(FakeClient([rnd]))

    def test_an_api_that_stops_being_an_array_is_refused_not_treated_as_empty(self):
        rnd = {'lobby': [row(1)], 'cs2': [row(1)], 'api': {'data': []}}
        with self.assertRaises(SourceError):
            hotspawn(FakeClient([rnd]))


class ApiOnlyFallback(unittest.TestCase):
    """A blocked rendered page must not make a healthy official API array unusable."""

    def round(self, ids):
        rows = [row(i) for i in ids]
        return {'lobby': rows, 'cs2': rows, 'api': rows}

    def test_both_blocked_pages_publish_the_api_array_with_an_explicit_unavailable_crosscheck(self):
        client = FakeClient([self.round([1, 2])], block=('hotspawn-lobby', 'hotspawn-cs2'))
        rows, links, health = hotspawn(client)
        self.assertEqual([r['id'] for r in rows], ['1', '2'])
        self.assertEqual(health['status'], 'ok')
        self.assertEqual(health['crosscheck'], 'unavailable')
        self.assertEqual(health['verified_pages'], [])
        self.assertIn('both rendered lobby pages were unavailable', health['detail'].lower())
        self.assertIn('no three-response reconciliation is claimed', health['detail'])
        self.assertEqual(client.saved['hotspawn-context']['crosscheck'], 'unavailable')
        self.assertEqual(client.saved['hotspawn-context']['verified_pages'], [])
        self.assertEqual(client.saved['hotspawn-context']['api_ids'], ['1', '2'])
        self.assertEqual(links, {})

    def test_one_blocked_page_is_a_partial_crosscheck_not_a_failure(self):
        client = FakeClient([self.round([1])], block=('hotspawn-cs2',))
        rows, links, health = hotspawn(client)
        self.assertEqual([r['id'] for r in rows], ['1'])
        self.assertEqual(health['crosscheck'], 'partial')
        self.assertEqual(health['verified_pages'], ['lobby'])
        self.assertEqual(client.saved['hotspawn-context']['lobby_ids'], ['1'])
        self.assertIn('was unavailable', health['detail'])
        self.assertIn('1', links)  # the readable page still supplies the match permalink

    def test_a_readable_page_that_disagrees_still_fails_closed(self):
        rnd = {'lobby': [row(1), row(9)], 'cs2': [row(1)], 'api': [row(1)]}
        client = FakeClient([rnd], block=('hotspawn-cs2',))
        with mock.patch.object(sources.time, 'sleep'):
            with self.assertRaises(SourceError) as ctx:
                hotspawn(client)
        self.assertIn('disagree', str(ctx.exception))
        self.assertIn("in the page only ['9']", str(ctx.exception))

    def test_a_200_challenge_page_without_app_state_is_unreadable_not_a_schema_break(self):
        rounds = {'lobby': [row(1)], 'cs2': [row(1)], 'api': [row(1)]}
        client = FakeClient([rounds])

        def fetch(url, label, **kw):
            if label == 'hotspawn-cs2':
                return '<html><body>Please verify you are human</body></html>', {'observed_at': '2026-10-16T08:00:00Z'}
            return FakeClient.fetch(client, url, label, **kw)

        client.fetch = fetch
        rows, _, health = hotspawn(client)
        self.assertEqual([r['id'] for r in rows], ['1'])
        self.assertEqual(health['crosscheck'], 'partial')
        self.assertIn('no Hotspawn app state', health['detail'])

    def test_an_invalid_api_still_fails_even_when_both_pages_are_blocked(self):
        bad = {'lobby': [row(1)], 'cs2': [row(1)], 'api': {'data': []}}
        with self.assertRaises(SourceError):
            hotspawn(FakeClient([bad], block=('hotspawn-lobby', 'hotspawn-cs2')))

    def test_an_empty_api_is_refused_even_when_both_pages_are_blocked(self):
        empty = {'lobby': [], 'cs2': [], 'api': []}
        with self.assertRaises(SourceError):
            hotspawn(FakeClient([empty], block=('hotspawn-lobby', 'hotspawn-cs2')))


class DisagreementText(unittest.TestCase):
    def test_empty_when_everything_agrees(self):
        self.assertEqual(disagreement({'1'}, {'1'}, {'1'}, {}, {}), '')

    def test_reports_no_cache_headers_when_none_were_returned(self):
        self.assertIn('no cache headers', disagreement({'1', '2'}, {'1'}, {'1', '2'}, {}, {}))


if __name__ == '__main__':
    unittest.main()
