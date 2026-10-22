"""Session arena-bc1afd8f — measure what the checked-in test suite does against a *fresh* snapshot.

``checks.yml`` and ``pages.yml`` both run ``python -m unittest discover -s tests``
against the checked-in ``data/`` tree before anything is published. That tree has
been frozen at ``data/latest.json`` ``generated_at 2026-10-15T08:36:13Z`` since
15 October, and 33 test modules read it (or ``ROOT/'data'``) directly as their
fixture. Any proposal that commits a freshly collected snapshot into the branch
root — which is exactly what ``scripts/root_publish.py`` does — therefore moves
the fixture underneath the suite.

This module measures the consequence instead of arguing about it. It runs a test
command as a subprocess, parses the unittest report, and writes a dated JSON/MD
record of which tests failed and against which snapshot. It never edits a test,
never edits data, and never turns a failure into a pass.

Usage
-----
    python -m scripts.bc1afd8f_gate                       # full suite, report to data/research/bc1afd8f/
    python -m scripts.bc1afd8f_gate --modules tests/test_contrarian.py tests/test_twc.py
    python -m scripts.bc1afd8f_gate --label fresh-snapshot --timeout 1800
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
SCHEMA_VERSION = 1
SESSION = "arena-bc1afd8f"

FAIL_RE = re.compile(r"^(FAIL|ERROR):\s+(\S+)\s+\(([^)]+)\)")
RAN_RE = re.compile(r"^Ran (\d+) tests? in ([0-9.]+)s")
FAILED_RE = re.compile(r"^FAILED \((.*)\)$")


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def snapshot_identity(data_dir: Path) -> dict:
    """Which fixture the suite is about to run against."""
    out: dict = {"data_dir": str(data_dir)}
    for name in ("latest.json", "origination.json"):
        path = data_dir / name
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            out[name] = None
            continue
        out[name] = {
            "generated_at": payload.get("generated_at"),
            "counts": payload.get("counts"),
            "live_collection": payload.get("live_collection"),
        }
    evidence = data_dir / "evidence"
    out["evidence_files"] = len(list(evidence.glob("*"))) if evidence.is_dir() else 0
    return out


def parse_unittest_output(text: str) -> dict:
    """The failures, errors and summary line of a unittest run."""
    failed = []
    ran = None
    seconds = None
    summary = None
    for line in text.splitlines():
        match = FAIL_RE.match(line.strip())
        if match:
            failed.append({"kind": match.group(1), "test": match.group(2), "suite": match.group(3)})
            continue
        ran_match = RAN_RE.match(line.strip())
        if ran_match:
            ran = int(ran_match.group(1))
            seconds = float(ran_match.group(2))
            continue
        failed_match = FAILED_RE.match(line.strip())
        if failed_match:
            summary = failed_match.group(1)
    ok = ran is not None and not failed and summary is None
    return {"ran": ran, "seconds": seconds, "ok": ok, "summary": summary or ("OK" if ok else None), "failed": failed}


def run_gate(
    *,
    command: list[str],
    data_dir: Path,
    label: str,
    timeout: float,
    cwd: Path | None = None,
) -> dict:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd or Path(".")),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        returncode = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
        error = None
    except subprocess.TimeoutExpired as exc:
        returncode = None
        stdout = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        error = f"timed out after {timeout}s"
    parsed = parse_unittest_output(stderr + "\n" + stdout)
    return {
        "schema_version": SCHEMA_VERSION,
        "session": SESSION,
        "observed_at": iso(datetime.now(UTC)),
        "label": label,
        "command": command,
        "returncode": returncode,
        "error": error,
        "wall_seconds": round(time.time() - started, 1),
        "snapshot": snapshot_identity(data_dir),
        **parsed,
        "tail": (stderr or stdout).strip().splitlines()[-25:],
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# {SESSION} — regression gate measurement: `{report['label']}`",
        "",
        f"Observed **{report['observed_at']}**. Command: `{' '.join(report['command'])}`",
        "",
        f"- snapshot `data/latest.json`: `{(report['snapshot'].get('latest.json') or {}).get('generated_at')}`",
        f"- snapshot `data/origination.json`: `{(report['snapshot'].get('origination.json') or {}).get('generated_at')}`"
        f" (live collection: `{(report['snapshot'].get('origination.json') or {}).get('live_collection')}`)",
        f"- `data/evidence/` files present: {report['snapshot'].get('evidence_files')}",
        f"- tests run: **{report.get('ran')}** in {report.get('seconds')}s · exit code `{report.get('returncode')}`"
        + (f" · {report['error']}" if report.get("error") else ""),
        f"- result: **{'PASS' if report.get('ok') else 'FAIL'}** ({report.get('summary') or 'no summary line'})",
        "",
    ]
    failed = report.get("failed") or []
    if failed:
        suites = sorted({item["suite"].split(".")[0] for item in failed})
        lines += [
            f"## {len(failed)} failing test(s) in {len(suites)} module(s)",
            "",
            "Modules: " + ", ".join(f"`{name}`" for name in suites),
            "",
            "| Kind | Test | Module |",
            "| --- | --- | --- |",
        ]
        lines += [f"| {item['kind']} | `{item['test']}` | `{item['suite']}` |" for item in failed]
    else:
        lines += ["## No failing tests", ""]
    lines += ["", "## Last lines of the run", "", "```", *(report.get("tail") or []), "```", ""]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("data/research/bc1afd8f"))
    parser.add_argument("--label", default="checked-in-snapshot")
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--modules", nargs="*", default=None, help="test modules; default: the whole suite")
    parser.add_argument("--interpreter", default=sys.executable)
    args = parser.parse_args(argv)

    if args.modules:
        command = [args.interpreter, "-m", "unittest", "-v", *args.modules]
    else:
        command = [args.interpreter, "-m", "unittest", "discover", "-s", "tests", "-v"]
    report = run_gate(command=command, data_dir=args.data, label=args.label, timeout=args.timeout)

    args.out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", args.label.lower()).strip("-")
    (args.out / f"gate-{slug}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (args.out / f"gate-{slug}.md").write_text(render_markdown(report))
    print(
        f"{SESSION}: {args.label} · ran {report.get('ran')} tests · "
        f"{len(report.get('failed') or [])} failing · {'PASS' if report.get('ok') else 'FAIL'}"
    )
    for item in (report.get("failed") or [])[:40]:
        print(f"  {item['kind']}: {item['suite']}.{item['test']}")
    # The gate reports; it does not decide. Exit 0 unless the run itself could not be made.
    return 0 if report.get("returncode") is not None else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
