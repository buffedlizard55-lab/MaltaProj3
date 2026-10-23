"""Publish rendered HTML views into the branch root without touching git-tracked data fixtures.

Why this exists
---------------
The repository's GitHub Pages site is configured in the platform's *legacy* mode
(``GET /repos/.../pages`` -> ``{"build_type": "legacy", "source": {"branch": "main", "path": "/"}}``).
The refresh workflow (``.github/workflows/pages.yml``) publishes the freshly built ``site/`` tree
through ``actions/deploy-pages``. A legacy build republishes the checked-in branch root on **every
push to ``main``**, so the two publishers race for the same paths:

* the artifact deploy wins  -> current picks and full ``data/`` tree,
* the legacy build wins     -> whatever HTML views were last committed to the root.

``PUT /repos/.../pages {"build_type": "workflow"}`` answers **403 Resource not accessible by
integration**, so the source cannot be switched from a workflow token.

What is copied (and why ``data/*`` is NEVER copied)
---------------------------------------------------
Copied: every rendered HTML page (``index.html``, ``picks/index.html``, ``origination/index.html``,
``unresolved/index.html``, ``coverage/index.html``, ``methodology/index.html``, ``review/index.html``,
``edge/index.html``, ``strategy/index.html``, ``final-day/index.html``, ``twc-picks/index.html``, and
top-level redirect stubs), ``assets/``, and ``.nojekyll``.

NEVER copied: ``data/*``, ``docs/*``, ``archive/*``.
Git-tracked ``data/*`` is the repository's deterministic CI replay fixture:

* ``scripts/validate.py:check_data`` and ``scripts/build_origination.py:validate_origination`` replay
  ``data/latest.json`` and ``data/origination.json`` against all 80+ files in ``data/evidence/`` and
  ``data/origination/evidence/``; overwriting ``data/latest.json`` or ``data/origination.json``
  without committing ~22 MB of evidence attachments breaks ``python -m scripts.build`` on ``main``;
* regression tests (e.g. ``tests/test_contrarian.py``, documented in ``.github/workflows/pages.yml``)
  assert against the checked-in ``data/latest.json`` snapshot before any runtime cache overlay.

To ensure the live deployment ALSO serves fresh ``data/*`` and evidence attachments after a
``[skip ci]`` root-sync push, ``pages.yml`` waits for that commit's legacy Pages build to complete
(``--wait-legacy-sha``) and immediately re-deploys the verified ``github-pages`` artifact.

Guards
------
The publisher is fail-closed, because a wrong publish is worse than a stale one:

* it refuses an output tree without a substantial ``index.html``;
* it refuses an output whose ``data/latest.json`` is missing, unparseable or has no
  ``generated_at``;
* it never moves backwards: if the root ``index.html`` already carries a *newer*
  ``data-snapshot-generated`` timestamp than the build being published, nothing is written;
* it refuses a snapshot older than ``--max-age-hours`` (default 12) unless ``--allow-stale`` is
  given, so a fallback republication cannot overwrite a newer root;
* it writes only files whose bytes changed, so re-running it is a no-op.

CLI
---
    python -m scripts.root_publish                          # publish site/ HTML+assets -> repo root
    python -m scripts.root_publish --print-paths            # one changed path per line (for git add)
    python -m scripts.root_publish --check                  # exit 2 if the root is not current
    python -m scripts.root_publish --wait-legacy-sha <sha>  # wait for legacy Pages build on <sha>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

#: Top-level directories in the build output that are never part of the published root copy.
SKIP_DIRS = {"data", "docs", "archive", "_fixture", "assets", "node_modules", "__pycache__"}

#: Files at the top of the build output that are always published (compat redirect stubs included).
TOP_FILES = ("index.html", "flagged.html", "methodology.html", "picks.html")

#: A real dashboard page, not a redirect stub. Guards against publishing an empty build.
MIN_INDEX_BYTES = 50_000

_HTML_STAMP_RE = re.compile(r'data-snapshot-generated="([^"]+)"')


class PublishRefused(RuntimeError):
    """Raised when the build must not be published into the branch root."""


@dataclass
class Plan:
    """The files a publish would write, relative to the repository root."""

    writes: dict[str, Path] = field(default_factory=dict)
    unchanged: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def changed(self) -> list[str]:
        return sorted(self.writes)


def _view_pages(output: Path) -> list[Path]:
    """Every rendered page in the build output, excluding evidence and archived session views."""
    pages: list[Path] = []
    for name in TOP_FILES:
        candidate = output / name
        if candidate.is_file():
            pages.append(candidate)
    for child in sorted(output.iterdir()):
        if not child.is_dir() or child.name in SKIP_DIRS or child.name.startswith("_"):
            continue
        page = child / "index.html"
        if page.is_file():
            pages.append(page)
    return pages


def _asset_files(output: Path) -> list[Path]:
    assets = output / "assets"
    if not assets.is_dir():
        return []
    return sorted(p for p in assets.rglob("*") if p.is_file())


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _snapshot_time(payload: object) -> datetime | None:
    if not isinstance(payload, dict):
        return None
    return _parse_iso(payload.get("generated_at") or payload.get("inventory_observed_at"))


def _html_snapshot_time(index_file: Path) -> datetime | None:
    """Extract ``data-snapshot-generated`` from a rendered ``index.html``."""
    if not index_file.is_file():
        return None
    try:
        head = index_file.read_text(encoding="utf-8", errors="ignore")[:4096]
    except OSError:
        return None
    match = _HTML_STAMP_RE.search(head)
    return _parse_iso(match.group(1)) if match else None


def load_snapshot_time(data_file: Path) -> datetime:
    """Return ``generated_at`` for a ``latest.json``-shaped file, or refuse."""
    try:
        payload = json.loads(data_file.read_text())
    except FileNotFoundError as exc:
        raise PublishRefused(f"{data_file} is missing; refusing to publish a build without data") from exc
    except json.JSONDecodeError as exc:
        raise PublishRefused(f"{data_file} is not valid JSON ({exc}); refusing to publish") from exc
    stamp = _snapshot_time(payload)
    if stamp is None:
        raise PublishRefused(f"{data_file} has no parseable generated_at; refusing to publish")
    return stamp


#: The public snapshot a republish would overwrite.
LIVE_SNAPSHOT_URL = "https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json"


def published_snapshot_time(url: str = LIVE_SNAPSHOT_URL, *, session=None, timeout: int = 20):
    """Return the ``generated_at`` the public site currently serves, or ``None``.

    ``None`` means the live value could not be read (network error, non-200, or
    an unparseable body); callers must treat that as "unknown", never as "older".
    """
    if session is None:
        import requests

        session = requests.Session()
    response = session.get(url, timeout=timeout, headers={"Cache-Control": "no-cache"})
    status = getattr(response, "status_code", 200)
    if status != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return _snapshot_time(payload)


def republish_regression(candidate: Path, *, url: str = LIVE_SNAPSHOT_URL, session=None) -> str:
    """Refuse to republish a "last good" build that is older than what is live.

    The fast republish job exists so the site never regresses to the checked-in
    branch root while a ten-minute build runs. It can only do that if the
    artifact it restores is *newer* than the live snapshot: on 2026-10-23 the
    newest successful publish was from the previous day, so restoring it would
    have moved the live site backwards. Returns a human-readable reason when the
    republish must be skipped, or ``""`` when it may proceed.
    """
    live = published_snapshot_time(url, session=session)
    if live is None:
        return ""  # cannot prove a regression; the republish proceeds as before
    candidate_time = load_snapshot_time(Path(candidate) / "data/latest.json")
    if candidate_time < live:
        return (
            f"the last verified build was generated {candidate_time.isoformat()} but the live site "
            f"already serves {live.isoformat()}; republishing it would move the site backwards"
        )
    return ""


def build_plan(
    output: Path,
    root: Path,
    *,
    now: datetime | None = None,
    max_age_hours: float = 12.0,
    allow_stale: bool = False,
    monotonic: bool = True,
) -> Plan:
    """Work out which root files must change. Raises :class:`PublishRefused` when it must not run."""
    output = Path(output)
    root = Path(root)
    index = output / "index.html"
    if not index.is_file():
        raise PublishRefused(f"{index} is missing; the build output does not look like a site")
    size = index.stat().st_size
    if size < MIN_INDEX_BYTES:
        raise PublishRefused(
            f"{index} is only {size} bytes (< {MIN_INDEX_BYTES}); refusing to publish a stub as the site"
        )

    latest = output / "data/latest.json"
    stamp = load_snapshot_time(latest)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    age = reference - stamp
    if not allow_stale and age > timedelta(hours=max_age_hours):
        raise PublishRefused(
            f"snapshot {stamp.isoformat()} is {age.total_seconds() / 3600:.1f}h old "
            f"(limit {max_age_hours}h); pass --allow-stale to publish it anyway"
        )

    plan = Plan()
    if monotonic:
        current = _html_snapshot_time(root / "index.html")
        if current is not None and current > stamp:
            plan.reason = (
                f"root index.html already carries {current.isoformat()}, which is newer than the build's "
                f"{stamp.isoformat()}; refusing to move the published site backwards"
            )
            return plan

    sources: list[Path] = list(_view_pages(output)) + _asset_files(output)
    if (output / ".nojekyll").is_file():
        sources.append(output / ".nojekyll")

    for source in sources:
        target = root / source.relative_to(output)
        if target.is_file() and target.read_bytes() == source.read_bytes():
            plan.unchanged.append(str(target.relative_to(root)))
            continue
        plan.writes[str(target.relative_to(root))] = source
    return plan


def apply_plan(plan: Plan, root: Path) -> list[str]:
    """Write the plan. Returns the repo-relative paths that changed."""
    root = Path(root)
    written: list[str] = []
    for relative, source in sorted(plan.writes.items()):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        written.append(relative)
    return written


def wait_for_legacy_pages_build(
    repository: str,
    sha: str,
    token: str,
    *,
    session=None,
    attempts: int = 36,
    pause: float = 5.0,
    initial_polls: int = 4,
) -> dict:
    """Wait for GitHub's legacy ``pages-build-deployment`` run on ``sha`` to finish without touching ``data/``."""
    import requests

    sess = session or requests.Session()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api = f"https://api.github.com/repos/{repository}"
    pages_resp = sess.get(f"{api}/pages", headers=headers, timeout=20)
    pages_resp.raise_for_status()
    pages = pages_resp.json()
    mode = pages.get("build_type")
    pages_status = pages.get("status")
    summary: dict = {
        "sha": sha,
        "build_type": mode,
        "pages_status": pages_status,
        "legacy_runs": [],
    }
    if mode != "legacy":
        return summary

    for attempt in range(attempts):
        runs_resp = sess.get(
            f"{api}/actions/runs",
            headers=headers,
            params={"head_sha": sha, "event": "dynamic", "per_page": 100},
            timeout=20,
        )
        runs_resp.raise_for_status()
        legacy = [
            r
            for r in runs_resp.json().get("workflow_runs", [])
            if (r.get("name") or "").replace(" ", "-").lower()
            in {"pages-build-deployment", "pages-build-and-deployment"}
        ]
        summary["legacy_runs"] = [
            {k: r.get(k) for k in ("id", "status", "conclusion", "head_sha")} for r in legacy
        ]
        if legacy and all(r.get("status") == "completed" for r in legacy):
            return summary
        # The dynamic-run listing can lag the Pages platform's own "building"
        # status. Treating an empty listing as finished in that state would let
        # an artifact deploy race (and lose to) a legacy build that GitHub has
        # already said is in progress. Only an idle/built site may use the
        # short no-run exit; a building site waits for the run to appear.
        if not legacy and attempt >= initial_polls and pages_status != "building":
            return summary
        if attempt < attempts - 1:
            time.sleep(pause)
    raise TimeoutError(f"Legacy Pages build for {sha} did not complete within {attempts * pause:.0f}s")


def main(argv: list[str] | None = None, *, now: datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=Path("site"), help="built site directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="repository root to publish into")
    parser.add_argument("--max-age-hours", type=float, default=12.0)
    parser.add_argument("--allow-stale", action="store_true", help="publish an old snapshot anyway")
    parser.add_argument("--no-monotonic", action="store_true", help="allow publishing an older snapshot")
    parser.add_argument("--print-paths", action="store_true", help="print changed root paths one per line")
    parser.add_argument("--paths-file", type=Path, help="write changed root paths to this file (for git add)")
    parser.add_argument("--check", action="store_true", help="exit 2 if the root is not current")
    parser.add_argument(
        "--wait-legacy-sha",
        help="wait for GitHub's legacy Pages build on this commit SHA before returning",
    )
    parser.add_argument(
        "--refuse-if-older-than-live",
        action="store_true",
        help="exit 3 when the build is older than the snapshot the public site already serves",
    )
    parser.add_argument("--live-url", default=LIVE_SNAPSHOT_URL, help="public snapshot URL for that guard")
    args = parser.parse_args(argv)

    if args.refuse_if_older_than_live:
        try:
            reason = republish_regression(args.output, url=args.live_url)
        except Exception as exc:  # a network problem must never block a publish
            print(f"::warning::republish guard could not read the live snapshot ({type(exc).__name__}: {exc})")
            reason = ""
        if reason:
            print(f"republish refused: {reason}")
            return 3
        print("republish guard: the build is not older than the live snapshot")
        return 0

    if args.wait_legacy_sha:
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
        if not repo or not token:
            print("root publish wait-legacy-sha requires GITHUB_REPOSITORY and GH_TOKEN", file=sys.stderr)
            return 3
        summary = wait_for_legacy_pages_build(repo, args.wait_legacy_sha, token)
        print(f"legacy Pages wait complete: {json.dumps(summary)}")
        return 0

    try:
        plan = build_plan(
            args.output,
            args.root,
            now=now,
            max_age_hours=args.max_age_hours,
            allow_stale=args.allow_stale,
            monotonic=not args.no_monotonic,
        )
    except PublishRefused as exc:
        print(f"root publish refused: {exc}", file=sys.stderr)
        return 3

    if plan.reason:
        print(f"root publish skipped: {plan.reason}")
        return 0

    if args.check:
        if plan.writes:
            print(
                f"root publish out of date: {len(plan.writes)} file(s) differ, "
                f"{len(plan.unchanged)} already match",
                file=sys.stderr,
            )
            for relative in plan.changed:
                print(relative, file=sys.stderr)
            return 2
        print(f"root publish current: {len(plan.unchanged)} file(s) match the build")
        return 0

    written = apply_plan(plan, Path(args.root))
    verb = "written" if written else "already current"
    # The path list is machine input for `git add`; keep it free of the human summary.
    stream = sys.stderr if (args.print_paths or args.paths_file) else sys.stdout
    print(
        f"root publish {verb}: {len(written)} changed, {len(plan.unchanged)} unchanged "
        f"({sum(s.stat().st_size for s in plan.writes.values())} bytes to write)",
        file=stream,
    )
    if args.paths_file:
        args.paths_file.write_text("".join(f"{relative}\n" for relative in written))
        print(f"root publish: wrote {len(written)} path(s) to {args.paths_file}", file=stream)
    if args.print_paths:
        for relative in written:
            print(relative)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
