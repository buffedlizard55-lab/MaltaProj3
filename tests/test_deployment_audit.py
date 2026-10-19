"""Regression tests for the independent GitHub Pages artifact audit.

All fixtures are generated from the repository's retained source data.  No test
calls Hotspawn, a sportsbook, GitHub Pages, or any external service.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tarfile
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.build import build
from scripts.deployment_audit import (
    AuditError,
    audit_archive,
    audit_site,
    preserve_equivalent_audit_time,
    report_flag,
    select_latest_successful_run,
    select_pages_artifact,
)


ROOT = Path(__file__).resolve().parents[1]


def check(report, identity):
    return next(item for item in report["checks"] if item["id"] == identity)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class DeploymentArtifactAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.site = cls.root / "site"
        # A fixed reference time makes the generated markup deterministic.  The
        # audit is about artifact parity and source links, not whether the
        # retained historical fixture is fresh today.
        build(ROOT / "data", cls.site, now=datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc))

    def copy_site(self, name):
        target = self.root / name
        shutil.copytree(self.site, target)
        return target

    def test_generated_artifact_has_complete_coverage_sources_and_phone_route(self):
        report = audit_site(self.site)
        self.assertEqual(report["status"], "pass", report.get("findings"))
        self.assertEqual(check(report, "complete-picks-coverage")["status"], "pass")
        self.assertEqual(check(report, "probability-bases")["status"], "pass")
        self.assertEqual(check(report, "phone-first-picks-route")["status"], "pass")
        self.assertEqual(check(report, "unresolved-surface")["status"], "pass")
        self.assertEqual(check(report, "row-source-links")["status"], "pass")
        self.assertEqual(report["counts"]["inventory_records"],
                         len(json.loads((self.site / "data/latest.json").read_text())["matches"]))
        source = json.loads((self.site / "data/origination.json").read_text())
        expected_blank = {str(row["id"]) for row in source["matches"] if not row.get("origination")}
        self.assertEqual({row["id"] for row in report["unresolved"]}, expected_blank)
        self.assertEqual(report["counts"]["unresolved_complete_picks"], len(expected_blank))

    def test_unresolved_ledger_copies_provider_trail_without_creating_a_probability(self):
        site = self.copy_site("unresolved-ledger")
        path = site / "data/origination.json"
        data = json.loads(path.read_text())
        row = next(item for item in data["matches"] if item.get("origination"))
        source_trail = [
            {"stage": "Primary: Polymarket", "status": "unresolved",
             "detail": "No unique fixture was verified.", "source_url": "https://polymarket.com/esports/cs2"},
            {"stage": "HLTV research", "status": "checked",
             "detail": "Identity checked; no price is claimed.", "source_url": "https://www.hltv.org/"},
            {"stage": "Original esportsbook lines", "status": "unresolved",
             "detail": "No paired line was verified.", "source_url": "https://thunderpick.io/esports/counter-strike"},
        ]
        row["origination"] = None
        row["pick_index"] = None
        row["research"] = source_trail
        row["limitations"] = ["No verified paired price; value stays blank."]
        data["unresolved_ids"] = [str(row["id"])]
        path.write_text(json.dumps(data))
        report = audit_site(site)
        self.assertEqual(check(report, "explicit-unresolved")["status"], "pass")
        ledger = next(item for item in report["unresolved"] if item["id"] == str(row["id"]))
        self.assertEqual(ledger["research"], source_trail)
        self.assertEqual(ledger["limitations"], row["limitations"])
        self.assertNotIn("probabilities", ledger)
        self.assertEqual(ledger["hotspawn_source_url"], row["source_url"])

    def test_repeat_of_identical_artifact_keeps_its_original_audit_time(self):
        prior = {
            "schema_version": 1,
            "status": "pass",
            "provenance": {"artifact": {"id": 456, "digest": "sha256:abc"}},
            "audited_at": "2026-10-19T04:11:17Z",
        }
        repeated = dict(prior, audited_at="2026-10-19T05:11:17Z")
        stable = preserve_equivalent_audit_time(repeated, prior)
        self.assertEqual(stable["audited_at"], prior["audited_at"])
        self.assertEqual({key: value for key, value in stable.items() if key != "audited_at"},
                         {key: value for key, value in repeated.items() if key != "audited_at"})

    def test_changed_artifact_or_audit_result_keeps_a_new_audit_time(self):
        prior = {
            "schema_version": 1,
            "status": "pass",
            "provenance": {"artifact": {"id": 456, "digest": "sha256:abc"}},
            "audited_at": "2026-10-19T04:11:17Z",
        }
        changed = {
            **prior,
            "provenance": {"artifact": {"id": 789, "digest": "sha256:def"}},
            "audited_at": "2026-10-19T05:11:17Z",
        }
        self.assertEqual(preserve_equivalent_audit_time(changed, prior)["audited_at"], changed["audited_at"])

    def test_a_missing_mobile_pick_surface_is_a_visible_review_failure(self):
        site = self.copy_site("missing-glance")
        index = site / "index.html"
        index.write_text(index.read_text().replace('id="picks-at-a-glance"', 'id="missing-glance"', 1))
        report = audit_site(site)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(check(report, "phone-first-picks-route")["status"], "needs_review")
        self.assertIn("pick-at-a-glance", check(report, "phone-first-picks-route")["detail"])

    def test_a_bad_probability_or_missing_evidence_is_not_silently_accepted(self):
        site = self.copy_site("bad-probability")
        path = site / "data/origination.json"
        data = json.loads(path.read_text())
        row = next(item for item in data["matches"] if item.get("origination"))
        row["origination"]["probabilities"] = [0.8, 0.8]
        row["origination"]["source_url"] = ""
        path.write_text(json.dumps(data))
        report = audit_site(site)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(check(report, "probability-bases")["status"], "needs_review")
        self.assertIn(str(row["id"]), check(report, "probability-bases")["detail"])

    def test_a_pages_tar_inside_github_outer_zip_is_checked_against_api_digest(self):
        content = self.root / "artifact-content"
        shutil.copytree(self.site, content)
        payload = self.root / "artifact.tar"
        with tarfile.open(payload, "w") as tar:
            for entry in sorted(content.rglob("*")):
                tar.add(entry, arcname=entry.relative_to(content).as_posix(), recursive=False)
        archive = self.root / "github-pages.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
            package.write(payload, "artifact.tar")
        digest = sha256(archive)
        report = audit_archive(
            archive,
            repository="buffedlizard55-lab/MaltaProj3",
            run={"id": 123, "head_sha": "a" * 40, "head_branch": "main", "conclusion": "success"},
            artifact={
                "id": 456,
                "name": "github-pages",
                "digest": "sha256:" + digest,
                "size_in_bytes": archive.stat().st_size,
                "archive_download_url": "https://api.github.com/repos/buffedlizard55-lab/MaltaProj3/actions/artifacts/456/zip",
            },
            downloaded_digest=digest,
        )
        self.assertEqual(report["status"], "pass", report.get("findings"))
        self.assertTrue(report["provenance"]["artifact"]["digest_matches_github_api"])
        self.assertEqual(check(report, "github-artifact-digest")["status"], "pass")
        flag = report_flag(report)[0]
        self.assertEqual(flag["severity"], "notice")
        self.assertIn("actions/runs/123", flag["source_urls"][0])
        self.assertTrue(any(link.endswith("/blob/main/data/research/7e429607/deployment-artifact-audit.json")
                            for link in flag["source_urls"]))
        self.assertTrue(all(link.startswith("https://github.com/") or link.startswith("https://api.github.com/")
                            for link in flag["source_urls"]))

    def test_digest_mismatch_is_published_as_needs_review(self):
        content = self.root / "mismatch-content"
        shutil.copytree(self.site, content)
        payload = self.root / "mismatch.tar"
        with tarfile.open(payload, "w") as tar:
            tar.add(content, arcname=".")
        archive = self.root / "mismatch.zip"
        with zipfile.ZipFile(archive, "w") as package:
            package.write(payload, "artifact.tar")
        report = audit_archive(
            archive,
            repository="buffedlizard55-lab/MaltaProj3",
            artifact={"id": 1, "name": "github-pages", "digest": "sha256:" + "0" * 64},
        )
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(check(report, "github-artifact-digest")["status"], "needs_review")
        flag = report_flag(report)[0]
        self.assertEqual(flag["severity"], "needs_review")
        self.assertIn("No pick, probability", flag["detail"])

    def test_run_and_artifact_selection_rejects_non_main_and_expired_candidates(self):
        run = select_latest_successful_run({"workflow_runs": [
            {"id": 1, "status": "completed", "conclusion": "success", "head_branch": "feature", "updated_at": "2026-10-19T04:00:00Z"},
            {"id": 2, "status": "completed", "conclusion": "failure", "head_branch": "main", "updated_at": "2026-10-19T05:00:00Z"},
            {"id": 3, "status": "completed", "conclusion": "success", "head_branch": "main", "updated_at": "2026-10-19T03:00:00Z"},
            {"id": 4, "status": "completed", "conclusion": "success", "head_branch": "main", "updated_at": "2026-10-19T06:00:00Z"},
        ]})
        self.assertEqual(run["id"], 4)
        artifact = select_pages_artifact({"artifacts": [
            {"id": 10, "name": "github-pages", "expired": True, "workflow_run": {"id": 4}, "archive_download_url": "https://api.github.com/x", "updated_at": "2026-10-19T07:00:00Z"},
            {"id": 11, "name": "other", "expired": False, "workflow_run": {"id": 4}, "archive_download_url": "https://api.github.com/x", "updated_at": "2026-10-19T07:00:00Z"},
            {"id": 12, "name": "github-pages", "expired": False, "workflow_run": {"id": 3}, "archive_download_url": "https://api.github.com/x", "updated_at": "2026-10-19T07:00:00Z"},
            {"id": 13, "name": "github-pages", "expired": False, "workflow_run": {"id": 4}, "archive_download_url": "https://api.github.com/x", "updated_at": "2026-10-19T06:00:00Z"},
        ]}, 4)
        self.assertEqual(artifact["id"], 13)

    def test_archive_path_traversal_is_rejected_before_content_is_read(self):
        archive = self.root / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("../outside.txt", "not allowed")
        with self.assertRaises(AuditError):
            audit_archive(archive)


if __name__ == "__main__":
    unittest.main()
