"""Retry a refused Hotspawn fixture request — bounded, and only for access errors.

Observed on 2026-10-22 from a GitHub runner: the fixture host answered HTTP 200
at 01:11Z and HTTP 403 at 01:38Z for the same public URL while the rendered lobby
pages stayed readable. A single refused request used to discard the whole
refresh and keep the retained snapshot, which is the "no picks for the new
matches" symptom this brief is about.

These tests pin the contract with a fake client: no network, no sleeps.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import sources
from scripts.sources import SourceError, fixture_array

ROWS = [{'id': '1', 'sport_alias': 'cs2'}]


class FakeClient:
    def __init__(self, failures):
        self.failures = list(failures)
        self.calls = 0

    def json(self, url, label):
        self.calls += 1
        if self.failures:
            raise SourceError(self.failures.pop(0))
        return ROWS, {'id': label, 'status': 'ok'}


class FixtureRetryTests(unittest.TestCase):
    def run_with(self, failures):
        client = FakeClient(failures)
        with patch.object(sources.time, 'sleep', lambda *_: None):
            try:
                result = fixture_array(client)
            except SourceError as exc:
                return client, exc
        return client, result

    def test_a_403_is_retried_and_the_successful_read_is_returned(self):
        client, result = self.run_with(['hotspawn-fixtures: 403 Client Error: Forbidden for url: x'])
        self.assertEqual(result[0], ROWS)
        self.assertEqual(client.calls, 2)

    def test_retries_are_bounded(self):
        client, error = self.run_with(['hotspawn-fixtures: 403 Forbidden'] * 3)
        self.assertIsInstance(error, SourceError)
        self.assertEqual(client.calls, 1 + len(sources.FIXTURE_RETRY_DELAYS))

    def test_gateway_and_rate_limit_responses_are_retried(self):
        for message in ('503 Service Unavailable', '429 Too Many Requests'):
            client, result = self.run_with([f'hotspawn-fixtures: {message}'])
            self.assertEqual(result[0], ROWS, message)
            self.assertEqual(client.calls, 2, message)

    def test_a_contract_error_is_never_retried(self):
        client, error = self.run_with(['hotspawn-fixtures: Fixture API is no longer an unpaginated array'])
        self.assertIsInstance(error, SourceError)
        self.assertEqual(client.calls, 1)

    def test_the_retry_uses_the_same_documented_endpoint(self):
        self.assertIn('api/v1/fixtures', sources.FIXTURES_API)
        self.assertEqual(sources.FIXTURE_RETRY_DELAYS, (20, 45))


if __name__ == '__main__':
    unittest.main()
