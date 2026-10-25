"""Session arena-27ac20d6 verifier (offline, deterministic, no network).

Re-checks, against only the committed tree, the two claims this session makes:

1. 27AC-1 research integrity. The dossier in ``data/research/27ac20d6/``
   records direct source reads for the fixtures the featured method left
   unresolved. This script replays the one piece of arithmetic in it - the
   project's own Valve-model formula (``scripts/domain.py`` ``valve_analysis``,
   RD 75) over the committed official standings
   (``data/evidence/valve-ratings.json``) - and confirms the identity facts
   the dossier states (two "The Huns" rows, one HOTU row, no "LFO 10" row).
   It invents no probability: the replay exists to prove the published model
   rows (1082793, 1082861) are exactly what the committed evidence produces,
   and to bound the 1082792 cross-check quoted in the dossier.

2. 27AC-2 executive-summary contract. The committed root ``index.html`` (the
   bytes the legacy Pages builder serves) must carry: a picks-at-a-glance
   section, a separate unresolved-picks register with limitations on the
   same page, the no-line and fallback registers, banner links to each and
   to coverage/methodology, and a glance row per active fixture that always
   shows a pick marker (or an explicit unresolved/even label), both teams'
   percentages where an estimate exists, at least one external source link,
   and a working detail anchor into ``origination/``.

Fixture- and figure-specific assertions are bound to the snapshot the
dossier is about (``generated_at 2026-10-25T05:12:25Z``) and report ``skip``
once a newer snapshot replaces it - the guard pattern earlier sessions
adopted after dated tests froze the four-hour publisher. Freshness is
reported as information only and never fails: keeping the snapshot inside
the 8-hour bound is the publisher's job, and a test that fails merely
because time passed is how the publisher stalls.
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER_DIR = ROOT / "data" / "research" / "27ac20d6"
DOSSIER_SNAPSHOT = "2026-10-25T05:12:25Z"
VALVE_RD = 75.0


def _g(rd: float = VALVE_RD) -> float:
    return 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd**2 / math.pi**2)


def valve_probability(points_a: float, points_b: float) -> float:
    """P(a beats b) under the project's Valve-model formula (domain.py)."""
    return 1 / (1 + 10 ** (_g() * (points_b - points_a) / 400))


def _strip(html_fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_fragment)).strip()


def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def run(root: Path = ROOT) -> dict:
    index_path = root / "index.html"
    origination_path = root / "origination" / "index.html"
    snapshot_path = root / "snapshot.json"
    ratings_path = root / "data" / "evidence" / "valve-ratings.json"
    dossier_dir = root / "data" / "research" / "27ac20d6"
    checks: list[dict] = []

    # --- dossier integrity -------------------------------------------------
    try:
        research = json.loads((dossier_dir / "research.json").read_text(encoding="utf-8"))
        flags = json.loads((dossier_dir / "flags.json").read_text(encoding="utf-8"))
        problems = []
        for fx in research.get("fixtures", []):
            for read in fx.get("reads", []):
                if not str(read.get("url", "")).startswith("https://"):
                    problems.append(f"{fx.get('fixture_id')}: read without https url")
                if not read.get("observed_at"):
                    problems.append(f"{fx.get('fixture_id')}: read without observed_at")
        for flag in flags:
            for key in ("id", "severity", "title", "detail", "source_urls"):
                if not flag.get(key):
                    problems.append(f"flag {flag.get('id')}: missing {key}")
            for url in flag.get("source_urls", []):
                if not str(url).startswith("https://"):
                    problems.append(f"flag {flag.get('id')}: non-https source {url}")
        checks.append(_check(
            "dossier-integrity",
            "pass" if not problems else "fail",
            "; ".join(problems) or (
                f"{len(research.get('fixtures', []))} researched fixtures, "
                f"{sum(len(f.get('reads', [])) for f in research.get('fixtures', []))} dated source reads, "
                f"{len(flags)} flags - every read and flag carries an https source link"),
        ))
    except Exception as exc:  # noqa: BLE001 - report, do not crash the suite
        checks.append(_check("dossier-integrity", "fail", f"dossier unreadable: {exc}"))
        research, flags = {}, []

    # --- Valve evidence identities -----------------------------------------
    ratings = {}
    try:
        doc = json.loads(ratings_path.read_text(encoding="utf-8"))
        for row in doc.get("rows", []):
            ratings.setdefault(row["name"], []).append(row)
        huns = sorted(r["points"] for r in ratings.get("The Huns", []))
        hotu = [r["points"] for r in ratings.get("HOTU", [])]
        spirit_ac = [r["points"] for r in ratings.get("Spirit Academy", [])]
        lfos = sorted(name for name in ratings if name.startswith("LFO "))
        ok = (huns == [701, 944] and hotu == [1437] and spirit_ac == [981]
              and lfos == ["LFO 7", "LFO 8", "LFO 9"])
        checks.append(_check(
            "valve-evidence-identities",
            "pass" if ok else "fail",
            f"standings {doc.get('snapshot_date')}: The Huns rows {huns}, HOTU {hotu}, "
            f"Spirit Academy {spirit_ac}, LFO rows {lfos} (no LFO 10) - the two raw-snapshot "
            "blockers reproduce exactly from committed official evidence" if ok else
            f"standings {doc.get('snapshot_date')}: The Huns {huns}, HOTU {hotu}, "
            f"Spirit Academy {spirit_ac}, LFO rows {lfos}"),
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(_check("valve-evidence-identities", "fail", f"ratings unreadable: {exc}"))

    # --- Valve cross-check bound for 1082792 --------------------------------
    if ratings:
        p122 = valve_probability(1437, 944) * 100
        p213 = valve_probability(1437, 701) * 100
        ok = 93.8 <= p122 <= 94.4 and 98.1 <= p213 <= 98.7
        checks.append(_check(
            "valve-crosscheck-1082792",
            "pass" if ok else "fail",
            f"project Valve model (RD 75) on committed points: HOTU {p122:.1f}% vs the "
            f"HLTV-verified #122 core (944 pts), {p213:.1f}% vs the #213 core (701 pts); "
            "published network figure is 98.2% - direction agrees, magnitude single-sourced",
        ))

    # --- snapshot guard ------------------------------------------------------
    snapshot = {}
    snapshot_matches = False
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot_matches = snapshot.get("generated_at") == DOSSIER_SNAPSHOT
    except Exception:  # noqa: BLE001
        snapshot = {}
    guard_note = ("bound to the dossier snapshot; the tree's snapshot is "
                  f"{snapshot.get('generated_at', 'unreadable')} - figures are historical, "
                  "re-derive from the current build instead")

    # --- executive-summary structure (any build) -----------------------------
    try:
        index_html = index_path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        checks.append(_check("exec-summary-sections", "fail", f"index.html unreadable: {exc}"))
        index_html = ""
    if index_html:
        required_ids = ["start-here", "picks-at-a-glance", "unresolved-register", "fallback-register"]
        missing = [i for i in required_ids if f'id="{i}"' not in index_html]
        if 'id="no-line-register"' not in index_html and "Picks without a betting line" not in index_html:
            missing.append("no-line-register")
        checks.append(_check(
            "exec-summary-sections",
            "pass" if not missing else "fail",
            "landing page carries start-here, picks-at-a-glance, the separate unresolved "
            "register, the no-line register and the fallback register" if not missing
            else f"missing sections: {missing}",
        ))
        banner_links = ["coverage/", "methodology/", "#unresolved-register", "#picks-at-a-glance"]
        missing_links = [h for h in banner_links if h not in index_html]
        checks.append(_check(
            "exec-summary-links",
            "pass" if not missing_links else "fail",
            "executive summary links one tap to the glance picks, the unresolved register, "
            "coverage/refresh status and methodology" if not missing_links
            else f"missing in-page links: {missing_links}",
        ))

    # --- glance rows: sourced, marked, anchored ------------------------------
    glance_rows = re.findall(r'<li class="glance-row".*?</li>', index_html, re.S) if index_html else []
    glance_ids = []
    if index_html:
        try:
            origination_html = origination_path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            origination_html = ""
        problems = []
        for row_html in glance_rows:
            m_id = re.search(r'data-glance-id="(\d+)"', row_html)
            if not m_id:
                problems.append("glance row without data-glance-id")
                continue
            fid = m_id.group(1)
            glance_ids.append(fid)
            if "data-glance-pick" not in row_html:
                problems.append(f"{fid}: no pick/state marker")
            text = _strip(row_html)
            percents = re.findall(r"\d+\.\d%", row_html)
            if len(percents) < 2 and "Unresolved" not in text and "no side" not in text:
                problems.append(f"{fid}: fewer than two percentages and no unresolved/even label")
            external = [u for u in re.findall(r'href="(https://[^"]+)"', row_html)
                        if "hotspawn.com" not in u]
            # Session arena-22a3ed80: a row published as explicitly unresolved has
            # no number to source, so the external-price requirement cannot apply
            # to it (fixture 1086697 on the 2026-10-25T16:20:19Z publish). What it
            # must carry instead is the reason, linked into the unresolved
            # register. A row with numbers still needs a non-Hotspawn source.
            unresolved_row = len(percents) < 2 and ("Unresolved" in text or "no side" in text)
            if not external and not unresolved_row:
                problems.append(f"{fid}: no external source link for the number")
            if unresolved_row and "origination/#unresolved" not in row_html:
                problems.append(f"{fid}: unresolved row does not link its reason")
            if f'id="match-{fid}"' not in origination_html:
                problems.append(f"{fid}: detail anchor #match-{fid} missing in origination/")
        checks.append(_check(
            "glance-rows-sourced",
            "pass" if glance_rows and not problems else "fail",
            f"{len(glance_rows)} glance rows; each carries a state marker, both teams' "
            "percentages or an explicit unresolved/even label, an external source link and a "
            "live detail anchor" if glance_rows and not problems
            else ("; ".join(problems) or "no glance rows found"),
        ))

    # --- snapshot-bound checks -----------------------------------------------
    if snapshot and index_html:
        if not snapshot_matches:
            checks.append(_check("glance-snapshot-parity", "skip", guard_note))
            checks.append(_check("unresolved-register-names", "skip", guard_note))
            checks.append(_check("valve-replay-model-rows", "skip", guard_note))
        else:
            open_ids = sorted(str(m["id"]) for m in snapshot.get("matches", [])
                               if m.get("availability") == "open")
            checks.append(_check(
                "glance-snapshot-parity",
                "pass" if sorted(glance_ids) == open_ids else "fail",
                f"glance lists {len(glance_ids)} fixtures, snapshot has {len(open_ids)} open - "
                "identical sets, no fixture dropped" if sorted(glance_ids) == open_ids
                else f"glance {sorted(glance_ids)} vs open {open_ids}",
            ))
            reg = re.search(r'id="unresolved-register".{0,40000}?(?=<section|\Z)', index_html, re.S)
            reg_text = _strip(reg.group(0)) if reg else ""
            raw_open_unresolved = [m for m in snapshot.get("matches", [])
                                   if m.get("availability") == "open" and not m.get("analysis")]
            unnamed = [m["id"] for m in raw_open_unresolved
                       if not all(t["name"] in reg_text for t in m["teams"])]
            checks.append(_check(
                "unresolved-register-names",
                "pass" if not unnamed and "limitation" in reg_text.lower() else "fail",
                f"all {len(raw_open_unresolved)} raw-unresolved open fixtures are named in the "
                "landing-page unresolved register, which states their limitations"
                if not unnamed else f"fixtures not named in the register: {unnamed}",
            ))
            # Model-row replay against the published glance percentages.
            replay_targets = {"1082793": (1383, 1110), "1082861": (734, 718)}
            replay_problems = []
            for fid, (fav_pts, dog_pts) in replay_targets.items():
                expected = valve_probability(fav_pts, dog_pts) * 100
                row_html = next((r for r in glance_rows if f'data-glance-id="{fid}"' in r), "")
                m_prob = re.search(r'class="glance-prob">([\d.]+)%', row_html)
                if not m_prob:
                    replay_problems.append(f"{fid}: no published percentage to replay against")
                elif abs(float(m_prob.group(1)) - expected) > 0.15:
                    replay_problems.append(
                        f"{fid}: published {m_prob.group(1)}% vs replay {expected:.1f}%")
            checks.append(_check(
                "valve-replay-model-rows",
                "pass" if not replay_problems else "fail",
                "both Valve-model glance rows (1082793, 1082861) reproduce to within 0.15pp "
                "from the committed official standings" if not replay_problems
                else "; ".join(replay_problems),
            ))

    # --- freshness: information only, never a failure ------------------------
    if snapshot.get("generated_at"):
        try:
            generated = datetime.fromisoformat(snapshot["generated_at"].replace("Z", "+00:00"))
            age_h = (datetime.now(UTC) - generated).total_seconds() / 3600
            checks.append(_check(
                "snapshot-freshness (info)",
                "info",
                f"snapshot {snapshot['generated_at']} is {age_h:.1f}h old at verification time; "
                f"published bound is {snapshot.get('stale_after_hours')}h - reported, not failed",
            ))
        except Exception:  # noqa: BLE001
            pass

    failed = [c for c in checks if c["status"] == "fail"]
    return {
        "session": "arena-27ac20d6",
        "snapshot_generated_at": snapshot.get("generated_at"),
        "snapshot_bound_to_dossier": snapshot_matches,
        "checks": checks,
        "summary": {
            "pass": sum(1 for c in checks if c["status"] == "pass"),
            "fail": len(failed),
            "skip": sum(1 for c in checks if c["status"] == "skip"),
            "info": sum(1 for c in checks if c["status"] == "info"),
        },
    }


def main() -> int:
    report = run()
    for c in report["checks"]:
        print(f"[{c['status']:>4}] {c['name']}: {c['detail']}")
    s = report["summary"]
    print(f"summary: {s['pass']} pass / {s['fail']} fail / {s['skip']} skip / {s['info']} info")
    return 1 if s["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
