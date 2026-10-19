"""Independently audit a deployed GitHub Pages artifact without changing picks.

The production publisher already verifies its Pages URL after deployment.  This
module adds a separate, artifact-bound check: it reads the immutable GitHub
Actions ``github-pages`` artifact selected by GitHub's own API, verifies the
API-published SHA-256 digest, and inspects the files inside the archive.

It deliberately has no collector, probability model, alias or betting-source
logic.  It can only report whether the already-built artifact contains the
source-linked inventory, complete-picks list, phone-first route and explicit
unresolved surface required by the dashboard policy.

Examples
--------

Audit a local built site (useful in unit tests)::

    python -m scripts.deployment_audit --site site --output report.json

Audit the latest successful production refresh from a GitHub Actions runner::

    python -m scripts.deployment_audit \
      --repository buffedlizard55-lab/MaltaProj3 --token "$GITHUB_TOKEN" \
      --output data/research/7e429607/deployment-artifact-audit.json \
      --flags-output data/research/7e429607/flags.json --strict

The non-strict form always writes a reviewable report when it can reach the
GitHub API.  ``--strict`` makes a failed artifact check exit non-zero; it is
intended for a validation gate, not for the evidence-only archival workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import stat
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup


API_ROOT = "https://api.github.com"
DEFAULT_REPOSITORY = "buffedlizard55-lab/MaltaProj3"
DEFAULT_WORKFLOW = "pages.yml"
ARTIFACT_NAME = "github-pages"
MAX_ARTIFACT_BYTES = 128 * 1024 * 1024
# A source link in the review finding points reviewers to the per-fixture
# unresolved ledger after this session's branch is merged to main.
PUBLISHED_REPORT_PATH = "data/research/7e429607/deployment-artifact-audit.json"
REQUIRED_PATHS = (
    "index.html",
    "origination/index.html",
    "picks/index.html",
    "coverage/index.html",
    "review/index.html",
    "data/latest.json",
    "data/origination.json",
    "data/row-source-audit.json",
)
HOTSPAWN_HOSTS = {
    "hotspawn.com",
    "www.hotspawn.com",
    "play.hotspawn.com",
    "phpstack-1372681-6459848.cloudwaysapps.com",
}


class AuditError(RuntimeError):
    """An artifact cannot be selected, downloaded or safely opened."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def github_url(repository: str, path: str) -> str:
    """Return a GitHub REST URL after accepting only owner/repository syntax."""
    parts = repository.split("/")
    if len(parts) != 2 or not all(parts) or any("/" in part or ".." in part for part in parts):
        raise AuditError("repository must be owner/repository")
    owner, repo = (quote(part, safe="-._") for part in parts)
    return f"{API_ROOT}/repos/{owner}/{repo}/{path.lstrip('/')}"


def github_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Spawn-Scout-Deployment-Audit/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_json(session: requests.Session, url: str) -> dict[str, Any]:
    response = session.get(url, timeout=(10, 45))
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise AuditError(f"GitHub API returned a non-object from {url}")
    return payload


def select_latest_successful_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Choose a successful main-branch publisher run, never a pull-request run."""
    rows = payload.get("workflow_runs")
    if not isinstance(rows, list):
        raise AuditError("workflow-runs response has no workflow_runs list")
    candidates = [
        row for row in rows
        if isinstance(row, dict)
        and row.get("status") == "completed"
        and row.get("conclusion") == "success"
        and row.get("head_branch") == "main"
        and row.get("id") is not None
    ]
    if not candidates:
        raise AuditError("no successful main-branch publisher run was returned")
    return max(candidates, key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""))


def select_pages_artifact(payload: dict[str, Any], run_id: int | str | None = None) -> dict[str, Any]:
    """Select the non-expired Pages artifact belonging to the selected run."""
    rows = payload.get("artifacts")
    if not isinstance(rows, list):
        raise AuditError("artifacts response has no artifacts list")
    wanted = []
    for row in rows:
        if not isinstance(row, dict) or row.get("name") != ARTIFACT_NAME or row.get("expired"):
            continue
        workflow_run = row.get("workflow_run") or {}
        if run_id is not None and str(workflow_run.get("id")) != str(run_id):
            continue
        if row.get("id") is not None and row.get("archive_download_url"):
            wanted.append(row)
    if not wanted:
        suffix = f" for workflow run {run_id}" if run_id is not None else ""
        raise AuditError(f"no non-expired {ARTIFACT_NAME!r} artifact found{suffix}")
    return max(wanted, key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""))


def latest_artifact(repository: str, token: str | None, workflow: str = DEFAULT_WORKFLOW,
                    session: requests.Session | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read metadata for the latest successful Pages artifact from GitHub's API."""
    own_session = session is None
    session = session or requests.Session()
    session.headers.update(github_headers(token))
    try:
        runs_url = github_url(repository, f"actions/workflows/{quote(workflow, safe='-._')}/runs?status=success&per_page=100")
        run = select_latest_successful_run(get_json(session, runs_url))
        run_id = run["id"]
        artifacts_url = github_url(repository, f"actions/runs/{run_id}/artifacts?per_page=100")
        artifact = select_pages_artifact(get_json(session, artifacts_url), run_id)
        return run, artifact
    finally:
        if own_session:
            session.close()


def artifact_by_id(repository: str, token: str | None, artifact_id: int | str,
                   session: requests.Session | None = None) -> dict[str, Any]:
    own_session = session is None
    session = session or requests.Session()
    session.headers.update(github_headers(token))
    try:
        return get_json(session, github_url(repository, f"actions/artifacts/{artifact_id}"))
    finally:
        if own_session:
            session.close()


def download_artifact(artifact: dict[str, Any], token: str | None, destination: Path,
                      session: requests.Session | None = None) -> str:
    """Download the official archive and return the locally calculated SHA-256.

    GitHub redirects ``archive_download_url`` to a short-lived storage URL.  The
    redirect itself is an official GitHub API response and the final URL has a
    signed, read-only query string.  No external source is queried here.
    """
    url = artifact.get("archive_download_url")
    if not isinstance(url, str) or not url.startswith("https://api.github.com/"):
        raise AuditError("artifact has no GitHub API archive_download_url")
    advertised_size = artifact.get("size_in_bytes")
    if isinstance(advertised_size, int) and advertised_size > MAX_ARTIFACT_BYTES:
        raise AuditError(f"artifact is {advertised_size} bytes; audit limit is {MAX_ARTIFACT_BYTES}")
    own_session = session is None
    session = session or requests.Session()
    session.headers.update(github_headers(token))
    try:
        response = session.get(url, stream=True, allow_redirects=True, timeout=(10, 120))
        response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        digest = hashlib.sha256()
        with destination.open("wb") as target:
            for block in response.iter_content(1024 * 1024):
                if not block:
                    continue
                total += len(block)
                if total > MAX_ARTIFACT_BYTES:
                    raise AuditError(f"artifact exceeded {MAX_ARTIFACT_BYTES} byte audit limit")
                digest.update(block)
                target.write(block)
        if not total:
            raise AuditError("artifact download was empty")
        return digest.hexdigest()
    finally:
        if own_session:
            session.close()


def _safe_destination(base: Path, member_name: str) -> Path:
    member = PurePosixPath(member_name)
    if member.is_absolute() or ".." in member.parts:
        raise AuditError(f"unsafe archive member path: {member_name!r}")
    destination = (base / Path(*member.parts)).resolve()
    try:
        destination.relative_to(base.resolve())
    except ValueError as exc:
        raise AuditError(f"archive member escapes its destination: {member_name!r}") from exc
    return destination


def safe_extract_zip(archive: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as source:
            for item in source.infolist():
                if item.is_dir():
                    continue
                # ZIP stores POSIX mode bits in the upper external-attribute
                # word. Do not materialize a symlink supplied by an archive.
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise AuditError(f"unsupported zip symlink: {item.filename!r}")
                target = _safe_destination(destination, item.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(item) as input_file, target.open("wb") as output_file:
                    shutil.copyfileobj(input_file, output_file)
    except zipfile.BadZipFile as exc:
        raise AuditError("artifact is not a readable zip file") from exc


def safe_extract_tar(archive: Path, destination: Path) -> None:
    try:
        with tarfile.open(archive) as source:
            for item in source.getmembers():
                if item.isdir():
                    continue
                if item.issym() or item.islnk() or not item.isfile():
                    raise AuditError(f"unsupported tar member type: {item.name!r}")
                target = _safe_destination(destination, item.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                extracted = source.extractfile(item)
                if extracted is None:
                    raise AuditError(f"tar member cannot be read: {item.name!r}")
                with extracted, target.open("wb") as output_file:
                    shutil.copyfileobj(extracted, output_file)
    except tarfile.TarError as exc:
        raise AuditError("artifact contains an unreadable tar payload") from exc


def unpack_pages_artifact(archive: Path, destination: Path) -> Path:
    """Unpack the Actions outer ZIP and its Pages ``artifact.tar`` payload."""
    outer = destination / "outer"
    outer.mkdir(parents=True, exist_ok=True)
    safe_extract_zip(archive, outer)
    tar_members = [path for path in outer.rglob("*") if path.is_file() and path.suffix == ".tar"]
    content = destination / "content"
    content.mkdir(parents=True, exist_ok=True)
    if tar_members:
        if len(tar_members) != 1:
            raise AuditError("Pages artifact contains more than one tar payload")
        safe_extract_tar(tar_members[0], content)
        return content
    # A direct archive is useful for deterministic local tests and remains safe.
    return outer


def locate_site_root(extracted: Path) -> Path:
    """Find exactly one directory that contains a Pages site's required data."""
    candidates = []
    for latest in extracted.rglob("data/latest.json"):
        root = latest.parent.parent
        if (root / "index.html").is_file():
            candidates.append(root.resolve())
    candidates = sorted(set(candidates))
    if len(candidates) != 1:
        raise AuditError(f"expected one site root in artifact; found {len(candidates)}")
    return candidates[0]


def _source_is_hotspawn(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("https://"):
        return False
    host = (urlparse(value).hostname or "").lower()
    return host in HOTSPAWN_HOSTS or any(host.endswith("." + allowed) for allowed in HOTSPAWN_HOSTS)


def _source_is_https(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("https://") and bool(urlparse(value).hostname)


def _as_pair(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item) for item in value):
        return None
    return [float(item) for item in value]


def _check(checks: list[dict[str, Any]], check_id: str, passed: bool, detail: str,
           evidence: list[str] | None = None) -> None:
    row: dict[str, Any] = {
        "id": check_id,
        "status": "pass" if passed else "needs_review",
        "detail": detail,
    }
    if evidence:
        row["evidence"] = evidence
    checks.append(row)


def _load_object(path: Path, label: str, checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _check(checks, f"{label}-json", False, f"Could not parse {path.as_posix()}: {type(exc).__name__}: {exc}")
        return None
    if not isinstance(value, dict):
        _check(checks, f"{label}-json", False, f"{path.as_posix()} must contain a JSON object")
        return None
    return value


def audit_site(site: Path) -> dict[str, Any]:
    """Audit an extracted Pages directory and return only observed facts.

    This is intentionally separate from the app's own renderer checks.  It
    reopens the generated files, compares IDs across published JSON, re-runs the
    row-source audit on the artifact, and reads mobile navigation from the
    artifact HTML rather than from templates in the repository.
    """
    site = site.resolve()
    checks: list[dict[str, Any]] = []
    missing = [path for path in REQUIRED_PATHS if not (site / path).is_file()]
    _check(
        checks,
        "required-files",
        not missing,
        "All required current Pages routes and JSON files are present."
        if not missing else "Artifact is missing: " + ", ".join(missing),
    )
    if missing:
        return {
            "schema_version": 1,
            "artifact_audit": "deployed-pages-content",
            "site_root": ".",
            "status": "needs_review",
            "checks": checks,
            "unresolved": [],
            "findings": ["Artifact lacks required current-site files; no match values were inferred."],
        }

    latest = _load_object(site / "data/latest.json", "latest", checks)
    originated = _load_object(site / "data/origination.json", "origination", checks)
    published_row_audit = _load_object(site / "data/row-source-audit.json", "row-source-audit", checks)
    if latest is None or originated is None:
        return {
            "schema_version": 1,
            "artifact_audit": "deployed-pages-content",
            "site_root": ".",
            "status": "needs_review",
            "checks": checks,
            "unresolved": [],
            "findings": ["Published JSON could not be read; no match values were inferred."],
        }

    matches = latest.get("matches")
    inventory_ok = isinstance(matches, list)
    _check(checks, "inventory-array", inventory_ok,
           f"Published inventory contains {len(matches) if inventory_ok else 0} records."
           if inventory_ok else "data/latest.json has no matches array.")
    if not inventory_ok:
        return {
            "schema_version": 1,
            "artifact_audit": "deployed-pages-content",
            "site_root": ".",
            "status": "needs_review",
            "checks": checks,
            "unresolved": [],
            "findings": ["Published inventory is malformed; no values were inferred."],
        }

    ids = [str(row.get("id")) for row in matches if isinstance(row, dict) and row.get("id") is not None]
    unique_ids = len(ids) == len(matches) and len(set(ids)) == len(ids)
    _check(checks, "inventory-identities", unique_ids,
           f"{len(ids)} unique inventory IDs were found."
           if unique_ids else "Inventory has a missing or duplicate match ID.")
    count_value = (latest.get("counts") or {}).get("inventory")
    _check(checks, "inventory-count", count_value == len(matches),
           f"Published inventory count agrees with {len(matches)} records."
           if count_value == len(matches) else
           f"Published inventory count {count_value!r} differs from {len(matches)} records.")

    bad_hotspawn = [str(row.get("id")) for row in matches
                    if not isinstance(row, dict) or not _source_is_hotspawn(row.get("source_url"))]
    _check(checks, "inventory-source-links", not bad_hotspawn,
           "Every inventory row carries an HTTPS Hotspawn/API source link."
           if not bad_hotspawn else
           "Inventory rows without a recognized HTTPS Hotspawn/API source link: " + ", ".join(bad_hotspawn[:12]))

    active = [row for row in matches if isinstance(row, dict) and row.get("availability") != "past"]
    active_ids = {str(row.get("id")) for row in active}
    origin_rows = originated.get("matches")
    origin_ok = isinstance(origin_rows, list)
    _check(checks, "complete-picks-array", origin_ok,
           f"Complete-picks JSON contains {len(origin_rows) if origin_ok else 0} rows."
           if origin_ok else "data/origination.json has no matches array.")
    origin_rows = origin_rows if isinstance(origin_rows, list) else []
    origin_ids = {str(row.get("id")) for row in origin_rows if isinstance(row, dict) and row.get("id") is not None}
    _check(checks, "complete-picks-coverage", origin_ids == active_ids,
           f"Complete-picks IDs exactly cover {len(active_ids)} non-archived inventory records."
           if origin_ids == active_ids else
           "Complete-picks IDs differ from non-archived inventory; missing=" +
           ", ".join(sorted(active_ids - origin_ids)[:12]) + "; extra=" +
           ", ".join(sorted(origin_ids - active_ids)[:12]))

    invalid_estimates: list[str] = []
    unresolved_not_listed: list[str] = []
    unresolved_rows: list[dict[str, Any]] = []
    unresolved_ids = {str(item) for item in originated.get("unresolved_ids") or []}
    for row in origin_rows:
        if not isinstance(row, dict):
            invalid_estimates.append("non-object")
            continue
        match_id = str(row.get("id"))
        line = row.get("origination")
        if not line:
            if match_id not in unresolved_ids:
                unresolved_not_listed.append(match_id)
            # This ledger intentionally copies the published source trail and
            # limitations, rather than deriving a replacement reason or price.
            # The four fields below are the complete research-record schema in
            # complete-picks data (provider/HLTV stage, outcome, text, URL).
            trail = []
            for research in row.get("research") or []:
                if isinstance(research, dict):
                    trail.append({key: research.get(key)
                                  for key in ("stage", "status", "detail", "source_url")})
            unresolved_rows.append({
                "id": match_id,
                "teams": [team.get("name") if isinstance(team, dict) else None
                          for team in (row.get("teams") or [])],
                "competition": row.get("competition"),
                "starts_at": row.get("starts_at"),
                "locks_at": row.get("locks_at"),
                "hotspawn_source_url": row.get("source_url"),
                "research": trail,
                "limitations": list(row.get("limitations") or []),
            })
            continue
        if not isinstance(line, dict):
            invalid_estimates.append(match_id)
            continue
        probabilities = _as_pair(line.get("probabilities"))
        pick = row.get("pick_index")
        valid = (
            probabilities is not None
            and all(0 <= value <= 1 for value in probabilities)
            and math.isclose(sum(probabilities), 1.0, rel_tol=0, abs_tol=1e-6)
            and _source_is_https(line.get("source_url"))
            and isinstance(line.get("observed_at"), str)
            and bool(line.get("observed_at"))
            and (pick is None or (isinstance(pick, int) and not isinstance(pick, bool) and pick in {0, 1}))
            and (pick is None or probabilities[pick] >= probabilities[1 - pick])
        )
        if not valid:
            invalid_estimates.append(match_id)
    _check(checks, "probability-bases", not invalid_estimates,
           "Every populated estimate has a normalized pair, an HTTPS evidence URL, observation time and non-underdog default."
           if not invalid_estimates else
           "Invalid populated estimate rows: " + ", ".join(invalid_estimates[:12]))
    unresolved_row_ids = {row["id"] for row in unresolved_rows}
    unrelated_unresolved_ids = unresolved_ids - unresolved_row_ids
    _check(checks, "explicit-unresolved", not unresolved_not_listed and not unrelated_unresolved_ids,
           "Every blank complete-picks row is explicitly listed as unresolved, with no unrelated unresolved ID."
           if not unresolved_not_listed and not unrelated_unresolved_ids else
           "Blank rows absent from unresolved_ids: " + ", ".join(unresolved_not_listed[:12]) +
           "; unresolved_ids without a blank row: " + ", ".join(sorted(unrelated_unresolved_ids)[:12]))

    summary = BeautifulSoup((site / "index.html").read_text(encoding="utf-8"), "html.parser")
    originated_page = BeautifulSoup((site / "origination/index.html").read_text(encoding="utf-8"), "html.parser")
    html_snapshot = (summary.body or {}).get("data-snapshot-generated") if summary.body else None
    _check(checks, "summary-snapshot-parity", html_snapshot == latest.get("generated_at"),
           "Executive summary declares the same generated timestamp as data/latest.json."
           if html_snapshot == latest.get("generated_at") else
           f"Executive summary timestamp {html_snapshot!r} differs from JSON {latest.get('generated_at')!r}.")
    full_list_links = [node.get("href") for node in summary.select("a[href]")
                       if str(node.get("href")).rstrip("/").endswith("origination/#picks")]
    phone_links = [node.get("href") for node in summary.select(".mobile-nav a[href]")
                   if str(node.get("href")).rstrip("/").endswith("origination/#picks")]
    _check(checks, "phone-first-picks-route", bool(summary.find(id="picks-at-a-glance")) and bool(full_list_links) and bool(phone_links),
           "Artifact has the executive pick-at-a-glance section plus full-list links in normal and mobile navigation."
           if summary.find(id="picks-at-a-glance") and full_list_links and phone_links else
           "Artifact is missing the pick-at-a-glance section or an executive/mobile link to complete picks.")
    _check(checks, "unresolved-surface", bool(originated_page.find(id="picks")) and bool(originated_page.find(id="unresolved")),
           "Complete-picks page exposes both the full list and a separate unresolved/limitations section."
           if originated_page.find(id="picks") and originated_page.find(id="unresolved") else
           "Complete-picks page is missing #picks or #unresolved.")

    expected_cards = {"match-" + match_id for match_id in active_ids}
    actual_cards = {node.get("id") for node in originated_page.select(".pick-card[id]")}
    _check(checks, "complete-picks-html-coverage", actual_cards == expected_cards,
           f"Complete-picks HTML has one card for every {len(expected_cards)} non-archived inventory record."
           if actual_cards == expected_cards else
           "Complete-picks card IDs differ from inventory; missing=" +
           ", ".join(sorted(expected_cards - actual_cards)[:12]) + "; extra=" +
           ", ".join(sorted(actual_cards - expected_cards)[:12]))

    recomputed_rows: dict[str, Any] | None = None
    try:
        from scripts.audit_rows import audit_site as audit_rows_site
        recomputed_rows = audit_rows_site(site)
        recomputed_totals = (recomputed_rows.get("totals") or {})
        published_totals = (published_row_audit or {}).get("totals") or {}
        _check(checks, "row-source-manifest-parity", published_totals == recomputed_totals,
               "Published row-source totals match a fresh audit of this artifact."
               if published_totals == recomputed_totals else
               f"Published row-source totals {published_totals!r} differ from recomputed {recomputed_totals!r}.")
        _check(checks, "row-source-links", not recomputed_totals.get("violation"),
               f"Recomputed row-source audit found {recomputed_totals.get('violation', 0)} violations."
               if not recomputed_totals.get("violation") else
               f"Recomputed row-source audit found {recomputed_totals.get('violation')} violations.")
    except Exception as exc:  # Explicitly report an inability to audit; never assume success.
        _check(checks, "row-source-links", False,
               f"Could not re-run the row-source audit: {type(exc).__name__}: {exc}")

    checks_ok = all(row["status"] == "pass" for row in checks)
    snapshot = {
        key: latest.get(key)
        for key in ("generated_at", "inventory_observed_at", "analysis_as_of", "coverage_complete", "run_status", "counts")
    }
    return {
        "schema_version": 1,
        "artifact_audit": "deployed-pages-content",
        "site_root": ".",
        "status": "pass" if checks_ok else "needs_review",
        "snapshot": snapshot,
        "counts": {
            "inventory_records": len(matches),
            "non_archived_records": len(active_ids),
            "complete_picks_rows": len(origin_rows),
            "unresolved_complete_picks": len(unresolved_rows),
            "row_source_violations": ((recomputed_rows or {}).get("totals") or {}).get("violation"),
        },
        # The separate ledger keeps an unresolved fixture discoverable even when
        # its only available evidence is a failed provider lookup. It is copied
        # from the canonical complete-picks artifact and contains no estimate.
        "unresolved": sorted(unresolved_rows, key=lambda row: (str(row.get("starts_at") or ""), row["id"])),
        "checks": checks,
        "findings": [] if checks_ok else [row["detail"] for row in checks if row["status"] != "pass"],
    }


def artifact_provenance(repository: str | None, run: dict[str, Any] | None,
                        artifact: dict[str, Any] | None, local_digest: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if repository:
        result["repository"] = repository
    if run:
        run_id = run.get("id")
        result["workflow_run"] = {
            key: run.get(key) for key in ("id", "name", "event", "head_branch", "head_sha", "created_at", "updated_at", "conclusion")
        }
        if run_id is not None and repository:
            result["workflow_run"]["url"] = f"https://github.com/{repository}/actions/runs/{run_id}"
    if artifact:
        result["artifact"] = {
            key: artifact.get(key) for key in ("id", "name", "size_in_bytes", "digest", "created_at", "updated_at", "expires_at", "expired")
        }
        artifact_id = artifact.get("id")
        if artifact_id is not None and repository:
            result["artifact"]["api_url"] = github_url(repository, f"actions/artifacts/{artifact_id}")
    if local_digest:
        result.setdefault("artifact", {})["downloaded_sha256"] = "sha256:" + local_digest
        advertised = (artifact or {}).get("digest")
        result["artifact"]["digest_matches_github_api"] = (advertised == "sha256:" + local_digest) if advertised else None
    return result


def audit_archive(archive: Path, repository: str | None = None, run: dict[str, Any] | None = None,
                  artifact: dict[str, Any] | None = None, downloaded_digest: str | None = None) -> dict[str, Any]:
    """Audit an already downloaded artifact archive and bind the result to metadata."""
    if not archive.is_file():
        raise AuditError(f"artifact archive does not exist: {archive}")
    local_digest = downloaded_digest or sha256_file(archive)
    with tempfile.TemporaryDirectory(prefix="spawn-scout-pages-audit-") as temporary:
        root = Path(temporary)
        extracted = unpack_pages_artifact(archive, root)
        site = locate_site_root(extracted)
        report = audit_site(site)
    report["provenance"] = artifact_provenance(repository, run, artifact, local_digest)
    digest_match = ((report.get("provenance") or {}).get("artifact") or {}).get("digest_matches_github_api")
    if digest_match is False:
        report.setdefault("checks", []).insert(0, {
            "id": "github-artifact-digest",
            "status": "needs_review",
            "detail": "Downloaded archive SHA-256 does not match GitHub API artifact.digest.",
        })
        report["status"] = "needs_review"
        report.setdefault("findings", []).append("GitHub artifact digest mismatch; do not treat content audit as deploy proof.")
    elif digest_match is True:
        report.setdefault("checks", []).insert(0, {
            "id": "github-artifact-digest",
            "status": "pass",
            "detail": "Downloaded archive SHA-256 matches GitHub API artifact.digest.",
        })
    return report


def audit_remote(repository: str, token: str | None, workflow: str = DEFAULT_WORKFLOW,
                 artifact_id: int | str | None = None) -> dict[str, Any]:
    """Fetch and inspect a selected Pages artifact using GitHub's official API."""
    if not token:
        raise AuditError("a GitHub token is required to download an Actions artifact")
    run: dict[str, Any] | None = None
    if artifact_id is not None:
        artifact = artifact_by_id(repository, token, artifact_id)
        run_data = artifact.get("workflow_run") or {}
        run = {"id": run_data.get("id"), "head_sha": run_data.get("head_sha"), "head_branch": run_data.get("head_branch")}
    else:
        run, artifact = latest_artifact(repository, token, workflow)
    with tempfile.TemporaryDirectory(prefix="spawn-scout-pages-download-") as temporary:
        archive = Path(temporary) / "github-pages.zip"
        digest = download_artifact(artifact, token, archive)
        return audit_archive(archive, repository, run, artifact, digest)


def add_metadata(report: dict[str, Any], audited_at: str | None = None) -> dict[str, Any]:
    report = dict(report)
    report["audited_at"] = audited_at or utc_now()
    return report


def preserve_equivalent_audit_time(report: dict[str, Any], previous: Any) -> dict[str, Any]:
    """Keep an existing observation time when a repeat audit has identical facts.

    The branch workflow writes its report back to the branch. Without this
    guard, a repeat read of the *same* immutable Pages artifact would differ
    only by ``audited_at`` and create a bot commit. That new commit moves a pull
    request head even though the underlying artifact did not change, which can
    cancel a useful validation run. A changed artifact, report field or failure
    remains a new observation and receives its actual current audit time.
    """
    if not isinstance(previous, dict) or not previous.get("audited_at"):
        return report
    current_without_time = {key: value for key, value in report.items() if key != "audited_at"}
    previous_without_time = {key: value for key, value in previous.items() if key != "audited_at"}
    if current_without_time != previous_without_time:
        return report
    stable = dict(report)
    stable["audited_at"] = previous["audited_at"]
    return stable


def read_json_if_object(path: Path) -> dict[str, Any] | None:
    """Read a prior report only when it is a valid object; never mask corruption."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def report_flag(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Create one Flagged-for-Review entry using only audit evidence URLs."""
    provenance = report.get("provenance") or {}
    links: list[str] = []
    run_url = ((provenance.get("workflow_run") or {}).get("url"))
    artifact_url = ((provenance.get("artifact") or {}).get("api_url"))
    repository = provenance.get("repository")
    sha = ((provenance.get("workflow_run") or {}).get("head_sha"))
    if run_url:
        links.append(run_url)
    if artifact_url:
        links.append(artifact_url)
    if repository and sha:
        links.append(f"https://github.com/{repository}/blob/{sha}/.github/workflows/pages.yml")
    if repository:
        links.append(f"https://github.com/{repository}/blob/main/{PUBLISHED_REPORT_PATH}")
    status = report.get("status")
    snapshot = report.get("snapshot") or {}
    counts = report.get("counts") or {}
    artifact = provenance.get("artifact") or {}
    artifact_id = artifact.get("id")
    title = (
        "Deployed GitHub Pages artifact independently matches the published coverage contract"
        if status == "pass" else
        "Deployed GitHub Pages artifact audit needs manual review"
    )
    if status == "pass":
        detail = (
            f"Artifact {artifact_id if artifact_id is not None else 'local'} was inspected after its GitHub Actions deployment. "
            f"Its API digest {'matched the downloaded archive' if artifact.get('digest_matches_github_api') is True else 'was not available for a local archive'}, "
            f"the artifact contains {counts.get('inventory_records')} inventory records and "
            f"{counts.get('complete_picks_rows')} complete-picks rows. Its {counts.get('unresolved_complete_picks')} blank "
            f"complete-picks rows retain a per-fixture source/limitation ledger in this report, and it preserved the executive/mobile route to "
            f"the full list plus the separate unresolved section. Snapshot generated {snapshot.get('generated_at')}; "
            f"inventory observed {snapshot.get('inventory_observed_at')}. This is an artifact-integrity check, not a new line or probability source."
        )
    else:
        detail = (
            f"Artifact {artifact_id if artifact_id is not None else 'local'} could not satisfy every independent "
            f"content check. The report records only observed failures: " +
            "; ".join(str(item) for item in (report.get("findings") or [])[:3]) +
            ". No pick, probability or source availability was inferred or repaired."
        )
    # A linkless local test report must never be rendered as a production claim.
    if not links:
        links = ["https://github.com/buffedlizard55-lab/MaltaProj3"]
    return [{
        "id": "7e429607-deployed-pages-artifact-audit",
        "severity": "notice" if status == "pass" else "needs_review",
        "title": title,
        "detail": detail,
        "match_ids": [],
        "source_urls": links,
    }]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--site", type=Path, help="already extracted Pages site directory")
    group.add_argument("--archive", type=Path, help="downloaded github-pages artifact ZIP")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY, help="GitHub owner/repository for remote mode")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW, help="publisher workflow file name")
    parser.add_argument("--artifact-id", help="specific GitHub Actions artifact ID to download")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"),
                        help="GitHub token; defaults to GITHUB_TOKEN or GH_TOKEN")
    parser.add_argument("--output", type=Path, help="write the full JSON report here")
    parser.add_argument("--flags-output", type=Path, help="write a Flagged-for-Review JSON entry here")
    parser.add_argument("--audited-at", help="ISO-8601 timestamp override for deterministic tests")
    parser.add_argument("--strict", action="store_true", help="exit non-zero if the audit needs review")
    args = parser.parse_args(argv)

    try:
        if args.site:
            report = audit_site(args.site)
        elif args.archive:
            report = audit_archive(args.archive, args.repository)
        else:
            report = audit_remote(args.repository, args.token, args.workflow, args.artifact_id)
    except (AuditError, requests.RequestException, OSError, ValueError) as exc:
        report = {
            "schema_version": 1,
            "artifact_audit": "deployed-pages-content",
            "status": "needs_review",
            "checks": [{
                "id": "artifact-access",
                "status": "needs_review",
                "detail": f"Artifact audit could not complete: {type(exc).__name__}: {exc}",
            }],
            "unresolved": [],
            "findings": ["Artifact access or extraction failed; no content, probability or source conclusion was drawn."],
            "provenance": {"repository": args.repository},
        }
    report = add_metadata(report, args.audited_at)
    if args.output:
        # Re-reading an unchanged artifact is useful, but should not produce a
        # timestamp-only branch commit that races the validation workflows.
        report = preserve_equivalent_audit_time(report, read_json_if_object(args.output))
        write_json(args.output, report)
    if args.flags_output:
        write_json(args.flags_output, report_flag(report))
    summary = report.get("counts") or {}
    print("status=" + str(report.get("status")) + " inventory=" + str(summary.get("inventory_records")) +
          " active=" + str(summary.get("non_archived_records")) +
          " row-source-violations=" + str(summary.get("row_source_violations")))
    return 1 if args.strict and report.get("status") != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
