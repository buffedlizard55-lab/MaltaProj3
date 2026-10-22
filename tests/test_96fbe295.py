"""Session 96fbe295 — the published root must carry the verified build, never an old page.

The brief says the site has to be updated every 4-8 hours and that it must be obvious where the
picks are. The public deployment failed both: on 2026-10-22T08:20Z the live ``data/latest.json`` was
the checked-in 15 October snapshot, because GitHub Pages is in legacy mode and the branch root was
six days old (see ``data/research/96fbe295/pages-root-verification.json``).

These tests lock the publisher that closes that race:

* only rendered pages, assets, the data files the pages read and the two small inventory-evidence
  files are copied - never ``data/research``, ``docs``, ``archive`` or the bulk evidence attachments;
* an unchanged root is a byte-for-byte no-op (so the four-hour job does not commit noise);
* a stub, missing or unparseable build is refused, and a snapshot older than the age limit is
  refused unless explicitly allowed;
* the root never moves backwards to an older snapshot.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import root_publish
from scripts.root_publish import PublishRefused, build_plan, main

NOW = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path, *, when: datetime, upcoming: int = 3) -> None:
    _write(
        root / "data/latest.json",
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "counts": {"upcoming": upcoming, "picks": upcoming},
                "matches": [],
            }
        ),
    )


def make_site(tmp: Path, *, when: datetime = NOW - timedelta(minutes=20)) -> Path:
    """A miniature build output shaped like the real ``site/`` tree."""
    output = tmp / "site"
    _write(output / "index.html", "<!doctype html><title>Executive summary</title>" + "x" * 60_000)
    _write(output / "picks.html", '<meta http-equiv="refresh" content="0;url=picks/">')
    _write(output / "picks/index.html", "<title>Picks</title>" + "y" * 4_000)
    _write(output / "review/index.html", "<title>Flagged for review</title>")
    _write(output / "final-day/index.html", "<title>Archived final day</title>")
    _write(output / "assets/scout.css", "body{font-size:16px}")
    _write(output / "assets/scout.js", "console.log('scout')")
    _write(output / ".nojekyll", "")
    _snapshot(output, when=when)
    _write(output / "data/origination.json", json.dumps({"counts": {"active": 3}}))
    _write(output / "data/sources.json", json.dumps({"sources": []}))
    _write(output / "data/row-source-audit.json", json.dumps({"totals": {"rows": 1}}))
    _write(output / "data/origination/aliases.json", json.dumps({"aliases": {}}))
    _write(output / "data/evidence/hotspawn-fixtures.json", "[{}]")
    _write(output / "data/evidence/hotspawn-context.json", "{}")
    # Never published, no matter how large:
    _write(output / "data/evidence/thunderpick-matches.json", "[{}]")
    _write(output / "data/research/abc/live.json", "{}")
    _write(output / "docs/index.html", "<title>old docs</title>")
    _write(output / "archive/root-session/index.html", "<title>archived</title>")
    return output


class PlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.output = make_site(self.tmp)
        self.root = self.tmp / "repo"
        self.root.mkdir()

    def publish(self, **kwargs):
        options = {"now": NOW}
        options.update(kwargs)
        plan = build_plan(self.output, self.root, **options)
        return plan, root_publish.apply_plan(plan, self.root)

    def test_publishes_pages_assets_and_the_four_data_files(self):
        plan, written = self.publish()
        self.assertIn("index.html", written)
        self.assertIn("picks/index.html", written)
        self.assertIn("assets/scout.css", written)
        self.assertIn("data/latest.json", written)
        self.assertIn("data/origination.json", written)
        self.assertIn(".nojekyll", written)
        for expected in written:
            self.assertTrue((self.root / expected).is_file(), expected)

    def test_publishes_only_the_inventory_evidence_the_rows_link(self):
        _, written = self.publish()
        self.assertIn("data/evidence/hotspawn-fixtures.json", written)
        self.assertIn("data/evidence/hotspawn-context.json", written)
        self.assertIn("data/origination/aliases.json", written)
        self.assertNotIn("data/evidence/thunderpick-matches.json", written,
                         "bulk evidence attachments must stay out of the four-hour commit")

    def test_never_publishes_research_docs_or_archive(self):
        _, written = self.publish()
        for forbidden in ("data/research/", "docs/", "archive/"):
            offenders = [p for p in written if p.startswith(forbidden)]
            self.assertEqual(offenders, [], f"{forbidden} must stay out of the root publish")

    def test_second_run_is_a_byte_for_byte_no_op(self):
        _, first = self.publish()
        self.assertTrue(first)
        plan, second = self.publish()
        self.assertEqual(second, [])
        self.assertEqual(plan.writes, {})
        self.assertEqual(len(plan.unchanged), len(first))

    def test_check_mode_reports_a_current_root_and_then_drift(self):
        self.publish()
        self.assertEqual(main(["--output", str(self.output), "--root", str(self.root), "--check"]), 0)
        _write(self.root / "picks/index.html", "<title>stale hand edit</title>")
        self.assertEqual(main(["--output", str(self.output), "--root", str(self.root), "--check"]), 2)

    def test_a_changed_page_is_republished(self):
        self.publish()
        (self.output / "picks/index.html").write_text("<title>Picks v2</title>")
        _, written = self.publish()
        self.assertEqual(written, ["picks/index.html"])
        self.assertIn("Picks v2", (self.root / "picks/index.html").read_text())


class RefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.output = make_site(self.tmp)
        self.root = self.tmp / "repo"
        self.root.mkdir()

    def test_refuses_a_missing_index(self):
        (self.output / "index.html").unlink()
        with self.assertRaises(PublishRefused):
            build_plan(self.output, self.root, now=NOW)

    def test_refuses_a_redirect_stub_as_the_site(self):
        _write(self.output / "index.html", '<meta http-equiv="refresh" content="0;url=/x">')
        with self.assertRaises(PublishRefused):
            build_plan(self.output, self.root, now=NOW)

    def test_refuses_a_build_without_data(self):
        (self.output / "data/latest.json").unlink()
        with self.assertRaises(PublishRefused):
            build_plan(self.output, self.root, now=NOW)

    def test_refuses_unparseable_snapshot(self):
        _write(self.output / "data/latest.json", "{not json")
        with self.assertRaises(PublishRefused):
            build_plan(self.output, self.root, now=NOW)

    def test_refuses_a_snapshot_older_than_the_age_limit(self):
        old = NOW - timedelta(hours=30)
        _snapshot(self.output, when=old)
        with self.assertRaises(PublishRefused):
            build_plan(self.output, self.root, now=NOW)

    def test_allow_stale_publishes_it_when_asked(self):
        old = NOW - timedelta(hours=30)
        _snapshot(self.output, when=old)
        plan = build_plan(self.output, self.root, now=NOW, allow_stale=True)
        self.assertTrue(plan.writes)

    def test_name_age_hours_is_configurable(self):
        _snapshot(self.output, when=NOW - timedelta(hours=20))
        with self.assertRaises(PublishRefused):
            build_plan(self.output, self.root, now=NOW)
        plan = build_plan(self.output, self.root, now=NOW, max_age_hours=24)
        self.assertTrue(plan.writes)

    def test_never_moves_the_root_backwards(self):
        _snapshot(self.root, when=NOW - timedelta(minutes=5))
        plan = build_plan(self.output, self.root, now=NOW)
        self.assertEqual(plan.writes, {})
        self.assertIn("newer than the build", plan.reason)

    def test_an_older_root_is_replaced_by_a_newer_build(self):
        _snapshot(self.root, when=NOW - timedelta(days=6))
        plan = build_plan(self.output, self.root, now=NOW)
        self.assertIn("data/latest.json", plan.writes)

    def test_refusal_exit_code_is_three(self):
        (self.output / "data/latest.json").unlink()
        self.assertEqual(main(["--output", str(self.output), "--root", str(self.root)]), 3)


class PathsFileTests(unittest.TestCase):
    def test_paths_file_lists_exactly_the_changed_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = make_site(tmp_path)
            root = tmp_path / "repo"
            root.mkdir()
            listing = tmp_path / "paths.txt"
            code = main(
                ["--output", str(output), "--root", str(root), "--paths-file", str(listing), "--allow-stale"]
            )
            self.assertEqual(code, 0)
            listed = [line for line in listing.read_text().splitlines() if line]
            self.assertIn("index.html", listed)
            self.assertIn("data/latest.json", listed)
            self.assertEqual(
                [p for p in listed if p.startswith("data/evidence")],
                ["data/evidence/hotspawn-context.json", "data/evidence/hotspawn-fixtures.json"],
            )
            self.assertFalse([p for p in listed if p.startswith("data/research")])


class WorkflowWiringTests(unittest.TestCase):
    """The publisher is only useful if the four-hour job actually calls it."""

    WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "pages.yml"

    def setUp(self):
        self.text = self.WORKFLOW.read_text()

    def test_the_job_may_push_to_the_branch(self):
        self.assertIn("contents: write", self.text)

    def test_the_job_runs_the_publisher(self):
        self.assertIn("python -m scripts.root_publish", self.text)
        self.assertIn("--paths-file", self.text)

    def test_the_commit_does_not_start_another_run(self):
        self.assertIn("[skip ci]", self.text)

    def test_publishing_happens_after_the_deployed_site_is_verified(self):
        verify = self.text.index("name: Verify the public site")
        publish = self.text.index("name: Publish the verified build into the branch root")
        self.assertLess(verify, publish, "a build must be verified before it is committed to the root")

    def test_pushes_cannot_cancel_a_scheduled_refresh(self):
        # GitHub cancels a pending run when a newer run enters its concurrency group.
        # With one shared `pages` group and a branch pushed every few minutes, the
        # four-hour refresh was cancelled before it could start (see the comment in
        # pages.yml). The runs must be grouped per event type.
        self.assertIn("group: pages-${{ github.event_name }}", self.text)
        self.assertNotIn("group: pages\n", self.text)

    def test_the_publisher_is_idempotent_in_the_job(self):
        # The step must exit cleanly when the root already matches, otherwise every
        # scheduled run would fail on an empty commit.
        self.assertIn('if [ ! -s "$RUNNER_TEMP/root-paths.txt" ]', self.text)


if __name__ == "__main__":
    unittest.main()
