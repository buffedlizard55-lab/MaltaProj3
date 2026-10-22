"""Session arena-bc1afd8f — reproduce, offline, what committing a fresh snapshot into the branch root would do.

Why this exists
---------------
``scripts/root_publish.py`` (merged in PR #176, 2026-10-22T08:29Z) copies a freshly
verified build — including ``data/latest.json``, ``data/origination.json``,
``data/sources.json`` and ``data/row-source-audit.json`` — over the checked-in
branch root and commits it, because GitHub Pages is in *legacy* mode
(``GET /repos/.../pages`` -> ``{"build_type":"legacy","source":{"branch":"main","path":"/"}}``)
and republishes that root on every push to ``main``.

That step had never executed: the ``pages.yml`` run for the very commit that added
it (run 39748055891, created 08:29:00Z) was cancelled at 08:45:52Z when the next
push to ``main`` created run 39750182735 in the same ``pages`` concurrency group.

This module answers the question that run never got to answer, **without touching
the repository**: it builds the exact root state a publish would produce in a
temporary directory and runs the repository's own replay validator
(``scripts.validate.check_data``) over it. ``root_publish`` deliberately does *not*
copy ``data/evidence/`` (~3 MB) or ``data/research/`` (~19 MB) — its own docstring
says committing those every four hours would put hundreds of megabytes into the
repository — so the candidate root pairs a **fresh** snapshot with the **frozen**
evidence that is checked in today.

Run it with::

    python -m scripts.bc1afd8f_root_risk                 # newest saved live snapshot as the candidate
    python -m scripts.bc1afd8f_root_risk --fresh DIR     # an explicit snapshot directory
    python -m scripts.bc1afd8f_root_risk --out data/research/bc1afd8f

Read-only: it copies into a temporary directory, never writes to ``data/`` and
never changes a probability, a pick or an alias.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
SCHEMA_VERSION = 1
SESSION = "arena-bc1afd8f"

#: The data files ``scripts.root_publish.DATA_FILES`` would copy into the root.
ROOT_DATA_FILES = (
    "data/latest.json",
    "data/origination.json",
    "data/sources.json",
    "data/row-source-audit.json",
)

#: Test modules that read the checked-in snapshot directly, i.e. the modules whose
#: contract assumes ``data/`` is a frozen fixture. Counted, never edited, here.
SNAPSHOT_READING_GLOB = "tests/test_*.py"


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def generated_at(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return payload.get("generated_at") if isinstance(payload, dict) else None


def find_candidate_snapshots(data_dir: Path) -> list[dict]:
    """Every saved live snapshot in the research tree, newest first."""
    found = []
    for latest in sorted(data_dir.glob("research/*/live/latest.json")) + sorted(
        data_dir.glob("research/*/live-latest.json")
    ):
        stamp = generated_at(latest)
        if not stamp:
            continue
        found.append({"generated_at": stamp, "latest": str(latest), "directory": str(latest.parent)})
    found.sort(key=lambda item: item["generated_at"], reverse=True)
    return found


def snapshot_files(directory: Path) -> dict[str, Path]:
    """The root-publishable files a saved snapshot directory actually carries.

    Sessions saved their snapshots under two conventions: ``live/latest.json`` and
    ``live-latest.json`` beside the other files. Both are accepted.
    """
    out = {}
    for name in ROOT_DATA_FILES:
        stem = Path(name).name
        for candidate in (directory / stem, directory / f"live-{stem}"):
            if candidate.is_file():
                out[name] = candidate
                break
    return out


def simulate_publish(repo_data: Path, fresh: dict[str, Path], work: Path) -> dict:
    """Build the post-publish root state in ``work`` and replay the validator over it."""
    candidate = work / "data"
    shutil.copytree(repo_data, candidate)
    copied = []
    for name, source in sorted(fresh.items()):
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.append({"path": name, "bytes": target.stat().st_size, "generated_at": generated_at(target)})

    from scripts.validate import check_data  # imported late: the copy must exist first

    result: dict = {
        "candidate_data_dir": str(candidate),
        "files_written": copied,
        "evidence_left_frozen": sorted(
            str(path.relative_to(work)) for path in (candidate / "evidence").glob("*.json")
        )[:8],
        "evidence_frozen_count": len(list((candidate / "evidence").glob("*"))),
    }
    try:
        data = check_data(candidate)
    except Exception as exc:  # noqa: BLE001 - the failure IS the finding
        result["check_data"] = "failed"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc(limit=6).splitlines()[-6:]
        result["published_rows"] = None
    else:
        result["check_data"] = "passed"
        result["published_rows"] = len(data.get("matches") or [])
    return result


def simulate_from_build(repo_root: Path, site: Path, work: Path) -> dict:
    """Run ``scripts.root_publish``'s own plan against a real build, then replay the validator.

    This is the faithful simulation: the publisher's own ``build_plan``/``apply_plan``
    decide which files land in the root (rendered pages, ``assets/`` and the seven
    ``DATA_FILES``), so the resulting tree is byte-for-byte what a successful
    root-sync commit would leave on ``main`` — including the part that matters, a
    fresh ``data/latest.json`` beside a frozen ``data/evidence/`` tree.
    """
    from scripts.root_publish import PublishRefused, apply_plan, build_plan

    result: dict = {"site": str(site), "site_exists": site.is_dir()}
    if not (site / "index.html").is_file() or not (site / "data" / "latest.json").is_file():
        result["check_data"] = "not-run"
        result["reason"] = "no built site with data/latest.json was available to publish"
        return result
    root_copy = work / "root"
    (root_copy / "data").parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo_root / "data", root_copy / "data")
    try:
        plan = build_plan(site, root_copy, allow_stale=True)
    except PublishRefused as exc:
        result["check_data"] = "not-run"
        result["refused"] = str(exc)
        return result
    if plan.reason:
        result["check_data"] = "not-run"
        result["skipped"] = plan.reason
        return result
    written = apply_plan(plan, root_copy)
    data_written = sorted(name for name in written if name.startswith("data/"))
    evidence_dir = root_copy / "data" / "evidence"
    result.update(
        {
            "files_written": len(written),
            "data_files_written": data_written,
            "evidence_files_after_publish": len(list(evidence_dir.glob("*"))) if evidence_dir.is_dir() else 0,
            "published_generated_at": generated_at(root_copy / "data" / "latest.json"),
            "frozen_generated_at": generated_at(repo_root / "data" / "latest.json"),
        }
    )

    from scripts.validate import check_data

    try:
        check_data(root_copy / "data")
    except Exception as exc:  # noqa: BLE001 - the failure IS the finding
        result["check_data"] = "failed"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc(limit=6).splitlines()[-6:]
    else:
        result["check_data"] = "passed"
    return result


def count_snapshot_reading_tests(repo_root: Path) -> dict:
    """How many checked-in test modules read ``data/latest.json`` by path."""
    readers = []
    for path in sorted(repo_root.glob(SNAPSHOT_READING_GLOB)):
        try:
            text = path.read_text()
        except OSError:
            continue
        if "data/latest.json" in text or "ROOT / 'data'" in text or 'ROOT / "data"' in text:
            readers.append(str(path.relative_to(repo_root)))
    return {"count": len(readers), "modules": readers}


def build_report(
    repo_root: Path,
    data_dir: Path,
    fresh_dir: Path,
    *,
    site: Path | None = None,
    observed_at: datetime | None = None,
) -> dict:
    fresh = snapshot_files(fresh_dir)
    moment = observed_at or datetime.now(UTC)
    with tempfile.TemporaryDirectory(prefix="bc1afd8f-root-risk-") as temporary:
        simulation = simulate_publish(data_dir, fresh, Path(temporary))
        from_build = (
            simulate_from_build(repo_root, site, Path(temporary)) if site is not None else {"check_data": "not-run"}
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "session": SESSION,
        "observed_at": iso(moment),
        "question": (
            "If the verified build were published into the branch root the way "
            "scripts/root_publish.py does it (fresh data files, frozen data/evidence), "
            "would the repository's own replay validator still accept the tree that "
            "checks.yml and pages.yml build from?"
        ),
        "method": [
            "Copied the checked-in data/ tree into a temporary directory (the repository was not modified).",
            "Overwrote exactly the data files scripts.root_publish.DATA_FILES would overwrite, from the newest saved live snapshot under data/research/*/live/.",
            "Left data/evidence/ frozen, exactly as root_publish.py documents and does.",
            "Ran scripts.validate.check_data over the resulting tree - the same call scripts.build makes first.",
        ],
        "checked_in_snapshot": {
            "data/latest.json": generated_at(data_dir / "latest.json"),
            "data/origination.json": generated_at(data_dir / "origination.json"),
        },
        "candidate_snapshot": {
            "directory": str(fresh_dir),
            "files": sorted(fresh),
            "generated_at": generated_at(fresh_dir / "latest.json"),
        },
        "simulation": simulation,
        "simulation_from_build": from_build,
        "snapshot_reading_tests": count_snapshot_reading_tests(repo_root),
        "conclusion": None,  # filled by main() so the wording follows the observed result
    }


def conclusion_for(report: dict) -> tuple[str, list[str]]:
    simulation = report.get("simulation_from_build") or {}
    if simulation.get("check_data") not in {"passed", "failed"}:
        simulation = report["simulation"]
    if simulation.get("check_data") == "passed":
        return (
            "A root publish of this candidate snapshot still replays: the checked-in evidence matches it.",
            [
                "Publishing the verified build into the branch root is safe for this candidate.",
                "The checked-in test modules that read data/latest.json were counted but not run here.",
            ],
        )
    return (
        "A root publish of this candidate snapshot would break the repository's own build: "
        f"{simulation.get('error_type')}: {simulation.get('error')}.",
        [
            "scripts.build calls scripts.validate.check_data first, so the build - and therefore "
            "checks.yml on every pull request and the pages.yml refresh - would fail on the published root.",
            "The cause is the pairing root_publish.py documents: a fresh data/latest.json with the frozen "
            "data/evidence/ tree (its inventory observation timestamp no longer matches).",
            "This is why the publisher shipped by this session re-deploys the verified artifact instead of "
            "committing fresh data to main: it makes the public site current without changing the frozen "
            "fixture that CI builds from.",
            f"{report['snapshot_reading_tests']['count']} checked-in test modules read data/latest.json or "
            "ROOT/'data' directly, so a committed fresh snapshot also moves their fixture underneath them.",
        ],
    )


def render_markdown(report: dict) -> str:
    simulation = report["simulation"]
    lines = [
        f"# {SESSION} — would publishing a fresh snapshot into the branch root break the build?",
        "",
        f"Observed **{report['observed_at']}**. Reproduced offline in a temporary directory; the",
        "repository's own `data/` tree was not modified and no value was invented.",
        "",
        f"**Question.** {report['question']}",
        "",
        "## Candidate",
        "",
        f"- checked-in `data/latest.json`: `{report['checked_in_snapshot']['data/latest.json']}`",
        f"- candidate snapshot directory: `{report['candidate_snapshot']['directory']}`",
        f"- candidate `generated_at`: `{report['candidate_snapshot']['generated_at']}`",
        f"- files overwritten: {', '.join(f'`{name}`' for name in report['candidate_snapshot']['files']) or 'none'}",
        f"- `data/evidence/` files left frozen: {simulation.get('evidence_frozen_count')}",
        "",
        "## Result of `scripts.validate.check_data` on the published root",
        "",
        f"- **{simulation.get('check_data')}**",
    ]
    if simulation.get("error"):
        lines += [
            f"- `{simulation.get('error_type')}: {simulation.get('error')}`",
            "",
            "```",
            *(simulation.get("traceback") or []),
            "```",
        ]
    from_build = report.get("simulation_from_build") or {}
    lines += [
        "",
        "## Same test using `scripts.root_publish`'s own plan on a real build",
        "",
        f"- built site: `{from_build.get('site')}` (present: {from_build.get('site_exists')})",
        f"- files the publisher would write into the root: {from_build.get('files_written')}",
        f"- data files among them: {', '.join(f'`{n}`' for n in (from_build.get('data_files_written') or [])) or 'none'}",
        f"- `data/evidence/` files left in the root afterwards: {from_build.get('evidence_files_after_publish')}",
        f"- published `generated_at`: `{from_build.get('published_generated_at')}` (frozen: `{from_build.get('frozen_generated_at')}`)",
        f"- `scripts.validate.check_data` on that root: **{from_build.get('check_data')}**"
        + (f" — `{from_build.get('error_type')}: {from_build.get('error')}`" if from_build.get("error") else "")
        + (f" — refused: {from_build.get('refused')}" if from_build.get("refused") else "")
        + (f" — skipped: {from_build.get('skipped')}" if from_build.get("skipped") else "")
        + (f" — {from_build.get('reason')}" if from_build.get("reason") else ""),
    ]
    if from_build.get("traceback"):
        lines += ["", "```", *from_build["traceback"], "```"]
    lines += [
        "",
        "## Conclusion",
        "",
        report["conclusion"],
        "",
    ]
    lines += [f"- {note}" for note in report["notes"]]
    lines += [
        "",
        "## Checked-in test modules that read the snapshot directly",
        "",
        f"{report['snapshot_reading_tests']['count']} module(s):",
        "",
    ]
    lines += [f"- `{module}`" for module in report["snapshot_reading_tests"]["modules"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--data", type=Path, default=None, help="defaults to <repo>/data")
    parser.add_argument("--fresh", type=Path, default=None, help="snapshot directory; default: newest saved live snapshot")
    parser.add_argument("--site", type=Path, default=None, help="a built site/ tree; enables the faithful root_publish simulation")
    parser.add_argument("--out", type=Path, default=Path("data/research/bc1afd8f"))
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    data_dir = (args.data or repo / "data").resolve()
    fresh_dir = args.fresh
    if fresh_dir is None:
        candidates = find_candidate_snapshots(data_dir)
        if not candidates:
            print("no saved live snapshot found under data/research/*/live/; nothing to simulate")
            return 0
        fresh_dir = Path(candidates[0]["directory"])
        if (fresh_dir / "origination.json").is_file() is False:
            # A `live-latest.json` style snapshot keeps its sibling beside it.
            sibling = fresh_dir.parent
            if (sibling / "live-origination.json").is_file():
                fresh_dir = sibling
    fresh_dir = fresh_dir.resolve()

    site = args.site
    if site is None and (repo / "site" / "data" / "latest.json").is_file():
        site = repo / "site"
    report = build_report(repo, data_dir, fresh_dir, site=site)
    report["conclusion"], report["notes"] = conclusion_for(report)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "root-publish-risk.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (args.out / "root-publish-risk.md").write_text(render_markdown(report))
    print(report["conclusion"])
    print(f"wrote {args.out / 'root-publish-risk.json'}")
    print(f"wrote {args.out / 'root-publish-risk.md'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
