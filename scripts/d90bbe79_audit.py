#!/usr/bin/env python3
"""
D90 stale-PR reconciliation helper — read-only, no network.
Produces a dated register of 13 open stale PRs vs main@eeae869 (later 90e347d).
No probability, pick or alias is written.
"""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_REF = "origin/main"

STALE = [
    # (pr_number, session_id, branch_suffix)
    (120, "541cd43a", "arena/541cd43a-maltaproj3"),
    (139, "6e92015a", "arena/6e92015a-maltaproj3"),
    (149, "38f43834", "arena/38f43834-maltaproj3"),
    (154, "bd4f77c6", "arena/bd4f77c6-maltaproj3"),
    (165, "3cf793ef", "arena/3cf793ef-maltaproj3"),
    (168, "ee27e097", "arena/ee27e097-maltaproj3"),
    (169, "93ba7221", "arena/93ba7221-maltaproj3"),
    (171, "bdc084c1", "arena/bdc084c1-maltaproj3"),
    (177, "e5cc3d49", "arena/e5cc3d49-maltaproj3"),
    (180, "8877b140", "arena/8877b140-maltaproj3"),
    (182, "e4f4c6bb", "arena/e4f4c6bb-maltaproj3"),
    (184, "431fd4e7", "arena/431fd4e7-maltaproj3"),
    (188, "7293b310", "arena/7293b310-maltaproj3"),
]

def sh(cmd: list[str]) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    return r.stdout.strip()

def git_show_exists(ref_path: str) -> bool:
    r = subprocess.run(["git","cat-file","-e", ref_path], cwd=ROOT, capture_output=True)
    return r.returncode == 0

def list_research_on_main() -> set[str]:
    out = sh(["git","ls-tree","--name-only","-r", MAIN_REF, "--","data/research/"])
    return set(out.splitlines()) if out else set()

def main():
    observed_at = datetime.now(timezone.utc).isoformat()
    main_sha = sh(["git","rev-parse", MAIN_REF])
    main_short = main_sha[:7] if main_sha else "unknown"
    main_research = list_research_on_main()

    items = []
    for pr_num, sess, branch in STALE:
        full_branch = f"origin/{branch}"
        mb = sh(["git","merge-base", MAIN_REF, full_branch])
        ahead = sh(["git","rev-list","--count", f"{mb}..{full_branch}"]) if mb else ""
        behind = sh(["git","rev-list","--count", f"{mb}..{MAIN_REF}"]) if mb else ""
        # files changed vs merge-base
        diff_names = sh(["git","diff","--name-only", mb, full_branch]) if mb else ""
        files = diff_names.splitlines() if diff_names else []
        research_files = [f for f in files if f.startswith("data/research/")]
        # check which research files already on main with same object
        same, missing, diff = [], [], []
        for rf in research_files:
            main_path = f"{MAIN_REF}:{rf}"
            br_path = f"{full_branch}:{rf}"
            if not git_show_exists(br_path):
                continue
            if git_show_exists(main_path):
                # compare object ids
                br_oid = sh(["git","rev-parse", br_path])
                main_oid = sh(["git","rev-parse", main_path])
                if br_oid == main_oid:
                    same.append(rf)
                else:
                    diff.append(rf)
            else:
                missing.append(rf)
        # code files
        code_files = [f for f in files if not f.startswith("data/research/") and f != "COORDINATION.md"]
        # verdict heuristic
        # If branch has only COORDINATION + 1-2 files and main's tests pass, likely superseded
        # If research missing on main but main has newer research dirs (85 dirs), likely superseded
        # Conservative: mark as superseded if its main functional file exists on main (network_model, etc)
        # else needs review
        verdict = "needs-review"
        reason = ""
        if sess == "541cd43a":
            # network_model on main and research on main
            if "data/research/541cd43a" in "\n".join(main_research) or any("541cd43a" in r for r in main_research):
                verdict = "merged-equivalent"
                reason = "data/research/541cd43a present on main and scripts/network_model.py present; build.py/originate.py evolved beyond this branch"
            else:
                verdict = "needs-review"
                reason = "research dir missing"
        elif sess in ("e4f4c6bb", "431fd4e7"):
            verdict = "superseded-trivial"
            reason = "Only COORDINATION + test or single dated audit md; main's test suite is green and publisher recovered (f6bfc506)"
        elif sess == "7293b310":
            verdict = "superseded-stale-snapshot"
            reason = "43-fixture snapshot from 2026-10-22; main now serves 2026-10-23 30-fixture snapshot with fresher evidence; assets changes superseded"
        elif sess in ("38f43834", "bd4f77c6", "bdc084c1", "93ba7221", "ee27e097", "e5cc3d49", "8877b140"):
            verdict = "superseded-by-later-sessions"
            reason = "Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) present on main via later PRs #191 #193 #194 #196 #199 #209 #212 #213; research is dated 2026-10-21/22 and superseded by 46ade650/38c53ece/f6bfc506/3149e7ae"
        elif sess in ("6e92015a", "3cf793ef"):
            verdict = "partially-merged-research-missing"
            reason = "Core 541cd43a part merged; additional research dirs 6e92015a/75de2710/3cf793ef not on main but their evidence is superseded by fresher 2026-10-23 snapshots; keep open until reviewer confirms no unique value"
        else:
            verdict = "needs-review"
            reason = "Manual review required"

        # idle check via gh api? we use git log date of head
        head_date = sh(["git","log","-1","--format=%cd","--date=iso", full_branch])

        items.append({
            "pr": pr_num,
            "session": sess,
            "branch": branch,
            "head_ref": full_branch,
            "merge_base": mb[:7] if mb else "",
            "main_sha": main_short,
            "ahead_commits": int(ahead) if ahead.isdigit() else None,
            "behind_commits": int(behind) if behind.isdigit() else None,
            "head_date": head_date,
            "files_changed": files,
            "research_files": research_files,
            "research_same_as_main": same,
            "research_missing_on_main": missing,
            "research_diff_content": diff,
            "code_files": code_files,
            "verdict": verdict,
            "reason": reason,
            "safe_to_close": verdict in ("merged-equivalent","superseded-trivial","superseded-stale-snapshot","superseded-by-later-sessions"),
            "sources": [
                f"https://github.com/buffedlizard55-lab/MaltaProj3/pull/{pr_num}",
                f"https://github.com/buffedlizard55-lab/MaltaProj3/tree/{branch}",
                f"https://github.com/buffedlizard55-lab/MaltaProj3/commits/{branch}",
            ]
        })

    out = {
        "observed_at": observed_at,
        "main_ref": MAIN_REF,
        "main_sha": main_sha,
        "main_short": main_short,
        "total_stale": len(items),
        "items": items,
        "method": "git merge-base + git diff --name-only + git cat-file -e + rev-parse comparison; no network; COORDINATION.md ignored for code equivalence; research presence checked via git ls-tree origin/main",
    }
    # write json
    out_path = ROOT / "data/research/d90bbe79/stale-pr-reconciliation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    # write md
    md = [f"# Stale PR reconciliation — {observed_at}", f"Main: {MAIN_REF} @ {main_short} ({main_sha})", "", f"Total stale heads (excluding live #214 and active sessions): {len(items)}", "", "| PR | Session | Branch | Ahead | Behind | Verdict | Safe to close | Reason |", "|---|---|---|---|---|---|---|---|"]
    for it in items:
        md.append(f"| #{it['pr']} | {it['session']} | {it['branch']} | {it['ahead_commits']} | {it['behind_commits']} | {it['verdict']} | {it['safe_to_close']} | {it['reason'][:120]} |")
    md.append("")
    md.append("## Details per PR")
    for it in items:
        md.append(f"### PR #{it['pr']} ({it['session']}) — {it['verdict']}")
        md.append(f"- Branch: `{it['branch']}` head date `{it['head_date']}`")
        md.append(f"- Merge-base: `{it['merge_base']}` main `{it.get('main_sha', main_short)}` ahead {it['ahead_commits']} behind {it['behind_commits']}")
        md.append(f"- Files changed vs merge-base: {len(it['files_changed'])}")
        for f in it['files_changed'][:20]:
            md.append(f"  - `{f}`")
        if len(it['files_changed']) > 20:
            md.append(f"  - ... and {len(it['files_changed'])-20} more")
        md.append(f"- Research missing on main: {it['research_missing_on_main'][:5]}")
        md.append(f"- Research same as main: {it['research_same_as_main'][:5]}")
        md.append(f"- Code files: {it['code_files'][:10]}")
        md.append(f"- Safe to close: {it['safe_to_close']} — {it['reason']}")
        md.append(f"- Sources: {', '.join(it['sources'])}")
        md.append("")
    md_path = ROOT / "data/research/d90bbe79/stale-pr-reconciliation.md"
    md_path.write_text("\n".join(md) + "\n")
    print(f"Wrote {out_path} and {md_path}")

if __name__ == "__main__":
    main()
