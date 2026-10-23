"""Session 96fbe295 + f2b91672 — publish rendered HTML views to the root without breaking data fixtures.

The brief says the site has to be updated every 4-8 hours and that it must be obvious where the
picks are. GitHub Pages is configured in legacy mode (`main /`), so every push to `main` triggers a
legacy Pages build alongside `actions/deploy-pages`.

These tests lock the publisher and workflow ordering that close both sides of that race:

* only rendered HTML pages, `assets/`, and `.nojekyll` are copied into the git-tracked branch root;
* `data/*` (including `data/latest.json`, `data/origination.json`, `data/evidence/*`, and
  `data/research/*`), `docs/*`, and `archive/*` are NEVER copied into the git-tracked root, so
  deterministic CI replay (`scripts.validate.check_data`, `validate_origination`,
  `tests/test_contrarian.py`) never breaks on `main`;
* monotonicity is enforced via `data-snapshot-generated` on `root/index.html`;
* an unchanged root is a byte-for-byte no-op (so the four-hour job does not commit noise);
* a stub, missing or unparseable build is refused, and a snapshot older than the age limit is
  refused unless explicitly allowed;
* whenever `pages.yml` pushes a `[skip ci]` root-sync commit, it waits for that commit's legacy
  Pages build (`--wait-legacy-sha`) and re-deploys `actions/deploy-pages@v5` + `scripts.verify_live`
  so the live deployment serves the complete `site/` artifact last.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import root_publish
from scripts.root_publish import PublishRefused, build_plan, main, wait_for_legacy_pages_build

NOW = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path, *, when: datetime, upcoming: int = 3) -> None:
    stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    _write(
        root / "data/latest.json",
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": stamp,
                "counts": {"upcoming": upcoming, "picks": upcoming},
                "matches": [],
            }
        ),
    )


def _write_index(root: Path, *, when: datetime) -> None:
    stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    _write(
        root / "index.html",
        f'<!doctype html><html lang="en" data-snapshot-generated="{stamp}">'
        f"<title>Executive summary</title>" + "x" * 60_000,
    )


def make_site(tmp: Path, *, when: datetime = NOW - timedelta(minutes=20)) -> Path:
    """A miniature build output shaped like the real ``site/`` tree."""
    output = tmp / "site"
    _write_index(output, when=when)
    _write(output / "picks.html", '<meta http-equiv="refresh" content="0;url=picks/">')
    _write(output / "picks/index.html", "<title>Picks</title>" + "y" * 4_000)
    _write(output / "unresolved/index.html", "<title>Unresolved picks & limitations</title>")
    _write(output / "review/index.html", "<title>Flagged for review</title>")
    _write(output / "final-day/index.html", "<title>Archived final day</title>")
    _write(output / "assets/scout.css", "body{font-size:16px}")
    _write(output / "assets/scout.js", "console.log('scout')")
    _write(output / ".nojekyll", "")
    _snapshot(output, when=when)
    # Never published into git-tracked `data/` — served via the `github-pages` artifact instead:
    _write(output / "data/origination.json", json.dumps({"counts": {"active": 3}}))
    _write(output / "data/sources.json", json.dumps({"sources": []}))
    _write(output / "data/row-source-audit.json", json.dumps({"totals": {"rows": 1}}))
    _write(output / "data/origination/aliases.json", json.dumps({"aliases": []}))
    _write(output / "data/evidence/hotspawn-fixtures.json", "[{}]")
    _write(output / "data/evidence/hotspawn-context.json", "{}")
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

    def test_publishes_pages_assets_and_nojekyll(self):
        _, written = self.publish()
        self.assertIn("index.html", written)
        self.assertIn("picks/index.html", written)
        self.assertIn("unresolved/index.html", written)
        self.assertIn("final-day/index.html", written)
        self.assertIn("assets/scout.css", written)
        self.assertIn(".nojekyll", written)
        for expected in written:
            self.assertTrue((self.root / expected).is_file(), expected)

    def test_never_overwrites_git_tracked_data_docs_or_archive(self):
        _, written = self.publish()
        for forbidden in ("data/", "docs/", "archive/"):
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
        # Session arena-308fcaad: the fixture snapshot is pinned at NOW-20min, so
        # `--check` must be given that same clock. Without it, main() compared the
        # real wall clock against the pinned stamp and every run more than 12h past
        # 2026-10-22T08:40Z (Pages runs 39792708185 onward) exited 3 instead of 0,
        # which stopped the four-hour refresh before it could build or deploy.
        # Production behaviour is unchanged: the CLI still defaults to the clock.
        self.publish()
        self.assertEqual(
            main(["--output", str(self.output), "--root", str(self.root), "--check"], now=NOW), 0
        )
        _write(self.root / "picks/index.html", "<title>stale hand edit</title>")
        self.assertEqual(
            main(["--output", str(self.output), "--root", str(self.root), "--check"], now=NOW), 2
        )

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

    def test_max_age_hours_is_configurable(self):
        _snapshot(self.output, when=NOW - timedelta(hours=20))
        with self.assertRaises(PublishRefused):
            build_plan(self.output, self.root, now=NOW)
        plan = build_plan(self.output, self.root, now=NOW, max_age_hours=24)
        self.assertTrue(plan.writes)

    def test_never_moves_the_root_backwards(self):
        _write_index(self.root, when=NOW - timedelta(minutes=5))
        plan = build_plan(self.output, self.root, now=NOW)
        self.assertEqual(plan.writes, {})
        self.assertIn("newer than the build", plan.reason)

    def test_an_older_root_is_replaced_by_a_newer_build(self):
        _write_index(self.root, when=NOW - timedelta(days=6))
        plan = build_plan(self.output, self.root, now=NOW)
        self.assertIn("index.html", plan.writes)

    def test_refusal_exit_code_is_three(self):
        (self.output / "data/latest.json").unlink()
        self.assertEqual(main(["--output", str(self.output), "--root", str(self.root)]), 3)


class LegacyWaitTests(unittest.TestCase):
    def test_wait_completes_once_dynamic_pages_run_completes(self):
        calls = []

        class FakeResp:
            def __init__(self, body):
                self._body = body

            def raise_for_status(self):
                return None

            def json(self):
                return self._body

        class FakeSession:
            def get(self, url, headers=None, params=None, timeout=20):
                calls.append((url, params))
                if url.endswith("/pages"):
                    return FakeResp({"build_type": "legacy"})
                if len(calls) == 2:
                    return FakeResp(
                        {
                            "workflow_runs": [
                                {
                                    "id": 99,
                                    "name": "pages build and deployment",
                                    "status": "in_progress",
                                    "conclusion": None,
                                    "head_sha": "abc123",
                                }
                            ]
                        }
                    )
                return FakeResp(
                    {
                        "workflow_runs": [
                            {
                                "id": 99,
                                "name": "pages build and deployment",
                                "status": "completed",
                                "conclusion": "success",
                                "head_sha": "abc123",
                            }
                        ]
                    }
                )

        summary = wait_for_legacy_pages_build(
            "owner/repo", "abc123", "tok", session=FakeSession(), attempts=4, pause=0.0
        )
        self.assertEqual(summary["build_type"], "legacy")
        self.assertEqual(summary["legacy_runs"][0]["status"], "completed")


class PathsFileTests(unittest.TestCase):
    def test_paths_file_lists_changed_html_and_assets_never_data(self):
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
            self.assertIn("unresolved/index.html", listed)
            self.assertFalse([p for p in listed if p.startswith("data/")])


class EvenEstimateAuditTests(unittest.TestCase):
    """An exactly even estimate may only name a side when a provider publishes the order.

    Session 4c972a51 added that tie-break in ``scripts/originate.py``; the published
    coverage audit still rejected every even pick, so the 10:05Z deploy's own
    ``verify_live`` step failed on fixture 1082926 (job 119749532581, annotation
    "exactly even estimate must not name a pick") and the run never reached the
    branch-root publish. These tests pin the audit to the tie-break contract.
    """

    def payload(self, probs, pick, tie_break=None):
        origination = {
            "method": "model",
            "label": "Research model estimate",
            "probabilities": list(probs),
            "source_url": "https://www.hltv.org/ranking/teams",
            "quotes": [{"family": "model", "source_url": "https://www.hltv.org/ranking/teams",
                        "provider": "HLTV world ranking"}],
        }
        if tie_break is not None:
            origination["tie_break"] = tie_break
        return {
            "policy": {"hotspawn_votes_used": False, "fan_votes_used": False},
            "counts": {"active": 1, "resolved": 1, "unresolved": 0,
                       "with_pick": 0 if pick is None else 1},
            "matches": [{
                "id": "1082926",
                "teams": [{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Bravo"}],
                "pick_index": pick,
                "origination": origination,
            }],
        }

    def real_tie_break(self, ranks=(40, 61), pick=0):
        from scripts.originate import ranked_tie_break
        quote = {
            "family": "model",
            "probabilities": [0.5, 0.5],
            "provider": "HLTV world ranking",
            "source_url": "https://www.hltv.org/ranking/teams",
            "inputs": [{"name": "Alpha", "rank": ranks[0]}, {"name": "Bravo", "rank": ranks[1]}],
        }
        winner, record = ranked_tie_break(quote)
        self.assertEqual(winner, pick)
        return record

    def audit(self, payload):
        from scripts.coverage_audit import audit_complete_picks
        return audit_complete_picks(payload)

    def test_even_estimate_with_the_real_tie_break_passes(self):
        record = self.real_tie_break()
        self.assertEqual(self.audit(self.payload([0.5, 0.5], 0, record)), [])

    def test_even_estimate_without_a_tie_break_still_fails(self):
        problems = self.audit(self.payload([0.5, 0.5], 0))
        self.assertTrue(any("exactly even estimate must not name a pick" in p for p in problems), problems)

    def test_a_tie_break_that_points_at_the_other_team_fails(self):
        record = self.real_tie_break()
        problems = self.audit(self.payload([0.5, 0.5], 1, record))
        self.assertTrue(any("exactly even" in p for p in problems), problems)

    def test_a_tie_break_with_equal_ranks_fails(self):
        record = dict(self.real_tie_break(), ranks=[40, 40])
        problems = self.audit(self.payload([0.5, 0.5], 0, record))
        self.assertTrue(any("exactly even" in p for p in problems), problems)

    def test_a_tie_break_without_a_source_fails(self):
        record = dict(self.real_tie_break(), source_url="http://example.invalid")
        problems = self.audit(self.payload([0.5, 0.5], 0, record))
        self.assertTrue(any("exactly even" in p for p in problems), problems)

    def test_a_tie_break_of_the_wrong_rule_fails(self):
        record = dict(self.real_tie_break(), rule="coin toss")
        problems = self.audit(self.payload([0.5, 0.5], 0, record))
        self.assertTrue(any("exactly even" in p for p in problems), problems)

    def test_a_clear_favourite_is_unaffected(self):
        self.assertEqual(self.audit(self.payload([0.62, 0.38], 0)), [])
        problems = self.audit(self.payload([0.62, 0.38], 1))
        self.assertTrue(any("higher-probability" in p for p in problems), problems)


class WorkflowWiringTests(unittest.TestCase):
    """The publisher is only useful if the four-hour job calls it and re-deploys the artifact."""

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

    def test_artifact_is_redeployed_after_root_sync_legacy_build(self):
        publish = self.text.index("name: Publish the verified build into the branch root")
        wait_step = self.text.index("name: Wait for the root-sync commit's legacy Pages build")
        redeploy = self.text.index("name: Re-deploy the verified artifact over the legacy root build")
        reverify = self.text.index("name: Verify the public site after root-sync re-deploy")
        self.assertLess(publish, wait_step)
        self.assertLess(wait_step, redeploy)
        self.assertLess(redeploy, reverify)

    def test_the_publisher_is_idempotent_in_the_job(self):
        self.assertIn('if [ ! -s "$RUNNER_TEMP/root-paths.txt" ]', self.text)


if __name__ == "__main__":
    unittest.main()
