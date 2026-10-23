"""Republish guard — a stale "last good" build must never move the live site backwards.

Context (2026-10-23): the scheduled publisher failed six runs in a row at its
regression step, and the ``republish-last-verified`` job that runs *first*
publishes the newest **successful** run's artifact. Once the newest successful
run was a day old, that job would have republished a day-old snapshot over a
fresher live one. These tests pin the comparison, and pin the fail-open
behaviour when the live value cannot be read.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.root_publish import LIVE_SNAPSHOT_URL, main, published_snapshot_time, republish_regression

NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, body=None, status_code=200, boom=None):
        self._body, self.status_code, self._boom = body, status_code, boom

    def json(self):
        if self._boom:
            raise self._boom
        return self._body


class FakeSession:
    def __init__(self, response):
        self.response, self.calls = response, []

    def get(self, url, timeout=20, headers=None):
        self.calls.append((url, timeout))
        return self.response


def candidate(tmp: Path, when: datetime) -> Path:
    site = tmp / "candidate"
    (site / "data").mkdir(parents=True)
    (site / "data/latest.json").write_text(
        json.dumps({"schema_version": 1, "generated_at": when.strftime("%Y-%m-%dT%H:%M:%SZ")})
    )
    return site


def live(when: datetime) -> FakeSession:
    return FakeSession(FakeResponse({"generated_at": when.strftime("%Y-%m-%dT%H:%M:%SZ")}))


class RepublishRegressionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def test_an_older_candidate_is_refused_with_both_timestamps(self):
        site = candidate(self.tmp, NOW - timedelta(hours=20))
        reason = republish_regression(site, session=live(NOW - timedelta(hours=2)))
        self.assertIn("would move the site backwards", reason)
        self.assertIn("2026-10-22T09:00:00", reason)
        self.assertIn("2026-10-23T03:00:00", reason)

    def test_newer_or_equal_candidate_may_publish(self):
        site = candidate(self.tmp, NOW)
        self.assertEqual(republish_regression(site, session=live(NOW - timedelta(hours=2))), "")
        self.assertEqual(republish_regression(site, session=live(NOW)), "")

    def test_an_unreadable_live_snapshot_fails_open(self):
        site = candidate(self.tmp, NOW - timedelta(days=3))
        for response in (
            FakeResponse(status_code=404),
            FakeResponse(boom=ValueError("not json")),
            FakeResponse({"no": "stamp"}),
        ):
            self.assertEqual(republish_regression(site, session=FakeSession(response)), "")

    def test_the_read_is_never_cached(self):
        session = live(NOW)
        published_snapshot_time(session=session)
        self.assertEqual(session.calls[0][0], LIVE_SNAPSHOT_URL)
        self.assertIsNone(published_snapshot_time(url="https://example.test/x", session=FakeSession(FakeResponse(status_code=503))))

    def test_cli_exit_codes(self):
        """Exit 3 refuses the republish, 0 lets it run; the workflow gates on 0."""
        from unittest.mock import patch

        site = candidate(self.tmp, NOW - timedelta(hours=9))
        argv = ["--output", str(site), "--refuse-if-older-than-live", "--live-url", "https://example.test/x"]
        with patch("scripts.root_publish.republish_regression", return_value="older than live"):
            self.assertEqual(main(argv), 3)
        with patch("scripts.root_publish.republish_regression", return_value=""):
            self.assertEqual(main(argv), 0)
        # A test-network failure is a warning, not a blocked publish.
        with patch("scripts.root_publish.republish_regression", side_effect=OSError("no route to host")):
            self.assertEqual(main(argv), 0)


if __name__ == "__main__":
    unittest.main()
