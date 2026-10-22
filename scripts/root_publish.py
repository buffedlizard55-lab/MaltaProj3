"""Publish the verified build into the branch root, so the site can never serve an old page.

Why this exists
---------------
The repository's GitHub Pages site is configured in the platform's *legacy* mode
(``GET /repos/.../pages`` -> ``{"build_type": "legacy", "source": {"branch": "main", "path": "/"}}``).
The refresh workflow (``.github/workflows/pages.yml``) publishes the freshly built ``site/`` tree
through ``actions/deploy-pages``. A legacy build republishes the checked-in branch root on **every
push to ``main``**, so the two publishers race for the same paths:

* the artifact deploy wins  -> current picks,
* the legacy build wins     -> whatever was last committed to the root.

Observed on 2026-10-22 (see ``data/research/96fbe295/pages-root-verification.json``):

* the legacy build for ``2fb99b0`` finished 07:52:31Z and published the root;
* the public ``data/latest.json`` then read ``generated_at 2026-10-15T08:36:13Z`` (17 fixtures
  whose start times were a week in the past), and the public ``data/row-source-audit.json`` was
  byte-identical to the tracked file, proving the served site *was* the branch root;
* ``PUT /repos/.../pages {"build_type": "workflow"}`` answers **403 Resource not accessible by
  integration**, so the source cannot be switched from a workflow token.

This module closes the race from the only side the repository controls: it copies the verified
build over the checked-in root, so *both* publishers serve the same, current site.

What is copied (and what is deliberately not)
---------------------------------------------
Copied: every rendered page, ``assets/``, the four data files those pages read plus the alias
registry and the two inventory-evidence files the rows link (~2 MB in total), and ``.nojekyll``.

Not copied: the remaining ``data/evidence/`` attachments and all of ``data/research/`` (~22 MB).
Those files change on every refresh; committing them every four hours would put hundreds of
megabytes into the repository for no publishing benefit. They stay committed from their own
sessions, and the artifact deploy still serves their current copies.

Guards
------
The publisher is fail-closed, because a wrong publish is worse than a stale one:

* it refuses an output tree without a substantial ``index.html``;
* it refuses an output whose ``data/latest.json`` is missing, unparseable or has no
  ``generated_at``;
* it never moves backwards: if the root already carries a *newer* snapshot than the one being
  published, nothing is written (an equal snapshot is still reconciled, so a hand-edited or
  half-published root is repaired);
* it refuses a snapshot older than ``--max-age-hours`` (default 12) unless ``--allow-stale`` is
  given, so a fallback republication cannot overwrite a newer root;
* it writes only files whose bytes changed, so re-running it is a no-op.

CLI
---
    python -m scripts.root_publish                 # publish site/ -> repo root
    python -m scripts.root_publish --print-paths   # one changed path per line (for git add)
    python -m scripts.root_publish --check         # exit 2 if the root is not current
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

#: Top-level directories in the build output that are never part of the published root copy.
SKIP_DIRS = {"data", "docs", "archive", "_fixture", "assets", "node_modules", "__pycache__"}

#: Files at the top of the build output that are always published (compat redirect stubs included).
TOP_FILES = ("index.html", "flagged.html", "methodology.html", "picks.html")

#: Data files the rendered pages read, plus the two small pieces of inventory evidence the pages
#: link from every row. The rest of ``data/evidence/`` (3 MB) and all of ``data/research/`` (19 MB)
#: stay out of the four-hour commit; the artifact deploy still serves their current copies.
DATA_FILES = (
    "data/latest.json",
    "data/origination.json",
    "data/sources.json",
    "data/row-source-audit.json",
    "data/origination/aliases.json",
    "data/evidence/hotspawn-fixtures.json",
    "data/evidence/hotspawn-context.json",
)

#: A real dashboard page, not a redirect stub. Guards against publishing an empty build.
MIN_INDEX_BYTES = 50_000


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


def _snapshot_time(payload: object) -> datetime | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("generated_at") or payload.get("inventory_observed_at")
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


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
        published = root / "data/latest.json"
        if published.is_file():
            try:
                current = _snapshot_time(json.loads(published.read_text()))
            except (json.JSONDecodeError, OSError):
                current = None
            if current is not None and current > stamp:
                plan.reason = (
                    f"root already carries {current.isoformat()}, which is newer than the build's "
                    f"{stamp.isoformat()}; refusing to move the published site backwards"
                )
                return plan

    sources: list[Path] = list(_view_pages(output)) + _asset_files(output)
    for name in DATA_FILES:
        candidate = output / name
        if candidate.is_file():
            sources.append(candidate)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=Path("site"), help="built site directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="repository root to publish into")
    parser.add_argument("--max-age-hours", type=float, default=12.0)
    parser.add_argument("--allow-stale", action="store_true", help="publish an old snapshot anyway")
    parser.add_argument("--no-monotonic", action="store_true", help="allow publishing an older snapshot")
    parser.add_argument("--print-paths", action="store_true", help="print changed root paths one per line")
    parser.add_argument("--paths-file", type=Path, help="write changed root paths to this file (for git add)")
    parser.add_argument("--check", action="store_true", help="exit 2 if the root is not current")
    args = parser.parse_args(argv)

    try:
        plan = build_plan(
            args.output,
            args.root,
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
