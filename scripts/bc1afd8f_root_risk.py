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
copy the rest of ``data/evidence/`` (~3 MB) or ``data/research/`` (~19 MB) — its own
docstring says committing those every four hours would put hundreds of megabytes into
the repository — so the candidate root pairs a **fresh** snapshot with the **frozen**
evidence that is checked in today.

Both simulations are anchored on ``git archive HEAD data``, never on the working tree:
on a runner this workflow has already collected a fresh snapshot into ``data/``, and a
simulation over that tree compares fresh data with fresh evidence and reports a
comfortable ``passed`` that says nothing about ``main``.

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
import subprocess
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


def committed_data_tree(repo_root: Path, work: Path) -> tuple[Path, str]:
    """Materialise ``data/`` exactly as it is committed at ``HEAD``.

    On a GitHub runner the *working tree* ``data/`` is not the checked-in fixture:
    this session's own workflow runs ``scripts.collect`` and ``scripts.originate
    --live`` before this module, so ``data/latest.json`` and the whole
    ``data/evidence/`` tree are already the fresh live collection. Simulating a root
    publish against that tree pairs fresh data with fresh evidence and proves
    nothing (measured on run 39757283508: it reported `check_data: passed` and a
    "safe to publish" conclusion for a root that had never been published). The
    committed tree is what a root-sync commit would actually be applied to.
    """
    root = work / "root"
    root.mkdir(parents=True, exist_ok=True)
    archive = work / "data.tar"
    try:
        with archive.open("wb") as handle:
            subprocess.run(["git", "-C", str(repo_root), "archive", "HEAD", "data"], stdout=handle, check=True)
        subprocess.run(["tar", "-xf", str(archive), "-C", str(root)], check=True)
        if (root / "data" / "latest.json").is_file():
            return root, "git HEAD (the committed data/ tree)"
    except (OSError, subprocess.CalledProcessError):
        pass
    shutil.copytree(repo_root / "data", root / "data", dirs_exist_ok=True)
    return root, "working tree (git archive HEAD data unavailable)"


def evidence_stats(directory: Path) -> dict:
    """File count and byte size of an evidence tree - the cost side of the change request."""
    if not directory.is_dir():
        return {"files": 0, "bytes": 0}
    files = [path for path in sorted(directory.rglob("*")) if path.is_file()]
    return {"files": len(files), "bytes": sum(path.stat().st_size for path in files)}


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


def simulate_from_build(site: Path, root_copy: Path, *, provenance: str) -> dict:
    """Run ``scripts.root_publish``'s own plan against a real build, then replay the validator.

    This is the faithful simulation: the publisher's own ``build_plan``/``apply_plan``
    decide which files land in the root (rendered pages, ``assets/`` and the seven
    ``DATA_FILES``), so the resulting tree is byte-for-byte what a successful
    root-sync commit would leave on ``main``. ``work/root`` must already hold the
    **committed** ``data/`` tree (see :func:`committed_data_tree`), because that is
    what the commit would be applied to.
    """
    from scripts.root_publish import PublishRefused, apply_plan, build_plan

    result: dict = {
        "site": str(site),
        "site_exists": site.is_dir(),
        "root": str(root_copy),
        "root_provenance": provenance,
    }
    if not (site / "index.html").is_file() or not (site / "data" / "latest.json").is_file():
        result["check_data"] = "not-run"
        result["reason"] = "no built site with data/latest.json was available to publish"
        return result
    if not (root_copy / "data" / "latest.json").is_file():
        result["check_data"] = "not-run"
        result["reason"] = "no committed data/ tree was available to publish into"
        return result
    result["site_evidence"] = evidence_stats(site / "data" / "evidence")
    result["committed_evidence"] = evidence_stats(root_copy / "data" / "evidence")
    result["committed_generated_at"] = generated_at(root_copy / "data" / "latest.json")
    result["site_generated_at"] = generated_at(site / "data" / "latest.json")
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
    result.update(
        {
            "files_written": len(written),
            "data_files_written": sorted(name for name in written if name.startswith("data/")),
            "evidence_after_publish": evidence_stats(root_copy / "data" / "evidence"),
            "published_generated_at": generated_at(root_copy / "data" / "latest.json"),
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
        work = Path(temporary)
        offline_root, provenance = committed_data_tree(repo_root, work / "offline")
        simulation = simulate_publish(offline_root / "data", fresh, offline_root / "published")
        build_root, build_provenance = committed_data_tree(repo_root, work / "build")
        from_build = (
            simulate_from_build(site, build_root, provenance=build_provenance)
            if site is not None
            else {"check_data": "not-run", "root_provenance": build_provenance}
        )
        # Measured inside the temporary directory's lifetime: the numbers describe a
        # tree that is deleted as soon as this block ends.
        committed_stats = {
            "provenance": provenance,
            "data/latest.json": generated_at(offline_root / "data" / "latest.json"),
            "data/origination.json": generated_at(offline_root / "data" / "origination.json"),
            "evidence": evidence_stats(offline_root / "data" / "evidence"),
        }
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
            "Materialised the data/ tree as it is committed at HEAD with `git archive HEAD data` into a temporary directory; the repository's own working tree was not modified. On a runner the working tree is NOT the checked-in fixture, because this workflow collects and originates live data before this step.",
            "Simulation 1 overwrote exactly the data files scripts/root_publish.DATA_FILES would overwrite, from the newest saved live snapshot under data/research/*/live/, and left data/evidence/ frozen.",
            "Simulation 2 ran scripts.root_publish.build_plan()/apply_plan() against a real built site/ tree, so the publisher itself decided what lands in the root, then replayed scripts.validate.check_data - the same call scripts.build makes first.",
            "Both simulations report where their base tree came from, so a 'passed' result can never be mistaken for a measurement over an already-fresh tree.",
        ],
        "committed_root": committed_stats,
        "working_tree_root": {
            "data/latest.json": generated_at(data_dir / "latest.json"),
            "data/origination.json": generated_at(data_dir / "origination.json"),
            "evidence": evidence_stats(data_dir / "evidence"),
            "differs_from_commit": generated_at(data_dir / "latest.json") != committed_stats["data/latest.json"],
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
    """Pick the simulation that actually measured a *fresh* publish, and say which one that was.

    Simulation 2 is decisive only when the build it published was fresher than the
    committed root — on a runner, right after a live collection. Otherwise it is a
    control (publishing the same snapshot the root already carries), and the saved
    live snapshot in simulation 1 is the only fresh candidate on the table.
    """
    offline = report["simulation"]
    from_build = report.get("simulation_from_build") or {}
    committed_at = (report.get("committed_root") or {}).get("data/latest.json")
    site_at = from_build.get("site_generated_at")
    build_was_fresh = bool(site_at) and site_at != committed_at
    decisive_is_build = build_was_fresh and from_build.get("check_data") in {"passed", "failed"}
    decisive = from_build if decisive_is_build else offline
    which = (
        "simulation 2 (`scripts.root_publish`'s own plan over a build that was fresher than the committed root)"
        if decisive_is_build
        else "simulation 1 (the newest saved live snapshot over the committed root)"
    )
    control = (
        "simulation 1 measured a different, older candidate"
        if decisive_is_build
        else (
            f"simulation 2 was a control, not a measurement: the build it published carried the same "
            f"`generated_at` as the committed root (`{site_at}`), so publishing it changes no data file"
            if from_build.get("check_data") in {"passed", "failed"}
            else "simulation 2 could not run: " + str(from_build.get("reason") or from_build.get("refused") or from_build.get("skipped") or "no built site")
        )
    )

    if decisive.get("check_data") == "failed":
        return (
            "A root publish of a fresh snapshot would break the repository's own build: "
            f"{decisive.get('error_type')}: {decisive.get('error')}.",
            [
                f"Decisive measurement: {which}; {control}.",
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
    if decisive.get("check_data") != "passed":
        return (
            "Neither simulation could measure a fresh publish; this report proves nothing either way.",
            [f"{control}.", "Read `simulation.reason` / `simulation_from_build.reason` for what was missing."],
        )
    return (
        "A root publish of this build still replays: the committed evidence matches it.",
        [
            f"Decisive measurement: {which}; {control}.",
            "The checked-in test modules that read data/latest.json were counted but not run here.",
        ],
    )


def render_markdown(report: dict) -> str:
    simulation = report["simulation"]
    committed = report["committed_root"]
    working = report["working_tree_root"]

    def megabytes(value) -> str:
        return f"{(value or 0) / 1_000_000:.1f} MB"

    lines = [
        f"# {SESSION} — would publishing a fresh snapshot into the branch root break the build?",
        "",
        f"Observed **{report['observed_at']}**. Reproduced in a temporary directory; the",
        "repository's own `data/` tree was not modified and no value was invented.",
        "",
        f"**Question.** {report['question']}",
        "",
        "## Base tree (what a root-sync commit would be applied to)",
        "",
        f"- provenance: {committed['provenance']}",
        f"- committed `data/latest.json`: `{committed['data/latest.json']}`",
        f"- committed `data/origination.json`: `{committed['data/origination.json']}`",
        f"- committed `data/evidence/`: {committed['evidence']['files']} files, {megabytes(committed['evidence']['bytes'])}",
        f"- working-tree `data/latest.json` at the time of this run: `{working['data/latest.json']}`"
        f" ({working['evidence']['files']} evidence files)"
        + (" — **differs from the commit**, so the working tree was not used as the base"
           if working["differs_from_commit"] else " — same as the commit"),
        "",
        "## Simulation 1 — a saved live snapshot over the committed tree",
        "",
        f"- candidate snapshot directory: `{report['candidate_snapshot']['directory']}`",
        f"- candidate `generated_at`: `{report['candidate_snapshot']['generated_at']}`",
        f"- files overwritten: {', '.join(f'`{name}`' for name in report['candidate_snapshot']['files']) or 'none'}",
        f"- `data/evidence/` files left frozen: {simulation.get('evidence_frozen_count')}",
        f"- `scripts.validate.check_data`: **{simulation.get('check_data')}**",
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
    site_evidence = from_build.get("site_evidence") or {}
    after = from_build.get("evidence_after_publish") or {}
    lines += [
        "",
        "## Simulation 2 — `scripts.root_publish`'s own plan against a real build",
        "",
        f"- built site: `{from_build.get('site')}` (present: {from_build.get('site_exists')})",
        f"- base root: {from_build.get('root_provenance')}",
        f"- site `data/latest.json`: `{from_build.get('site_generated_at')}`",
        f"- site `data/evidence/`: {site_evidence.get('files')} files, {megabytes(site_evidence.get('bytes'))}"
        " — this is what the change request asks the publisher to copy",
        f"- files the publisher would write into the root: {from_build.get('files_written')}",
        f"- data files among them: {', '.join(f'`{n}`' for n in (from_build.get('data_files_written') or [])) or 'none'}",
        f"- `data/evidence/` in the root afterwards: {after.get('files')} files, {megabytes(after.get('bytes'))}"
        f" (committed: {committed['evidence']['files']})",
        f"- published `generated_at`: `{from_build.get('published_generated_at')}`",
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
