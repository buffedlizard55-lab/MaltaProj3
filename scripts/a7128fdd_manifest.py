"""Session arena-a7128fdd — compact live manifest of every active Hotspawn CS2 fixture.

Read-only. It never collects, never prices and never invents a value: it joins the
two feeds the repository already produced (``data/latest.json`` and
``data/origination.json``) and writes one small, dated manifest that a human or a
later research step can read without downloading a 200 KB snapshot.

The point of the manifest is to answer three questions exactly:

1. Which fixtures are active right now, and what did the ladder price them with?
2. Which of those are **model-only** (no external money line) — the brief's
   low-tier class that needs HLTV / esportsbook research?
3. For each model-only fixture, what are the exact names, competition and start
   time needed to bind an external source page without a fuzzy join?

Nothing here changes a probability. Output goes to
``data/research/a7128fdd/live-manifest.{json,md}``.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "data" / "latest.json"
ORIGINATION = ROOT / "data" / "origination.json"
OUT_DIR = ROOT / "data" / "research" / "a7128fdd"

MONEY_METHODS = {"market", "bookmaker", "consensus", "exchange", "relay", "reference"}


def _load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing feed: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _as_utc(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except ValueError:
        return str(value)


def build_manifest(now: datetime | None = None) -> dict:
    latest = _load(LATEST)
    origination = _load(ORIGINATION)
    observed = now or datetime.now(timezone.utc)

    orig_by_id = {str(m.get("id")): m for m in origination.get("matches", [])}

    active: list[dict] = []
    for match in latest.get("matches", []):
        if match.get("availability") == "past":
            continue
        mid = str(match.get("id"))
        teams = [t.get("name", "") for t in match.get("teams", [])]
        orig = orig_by_id.get(mid) or {}
        originated = orig.get("origination") or {}
        method = originated.get("method") or ""
        featured = match.get("analysis") or {}
        row = {
            "id": mid,
            "teams": teams,
            "competition": match.get("competition") or "",
            "starts_at": _as_utc(match.get("starts_at")),
            "locks_at": _as_utc(match.get("locks_at")),
            "tier": match.get("tier") or "",
            "best_of": match.get("best_of"),
            "featured_method": featured.get("method") if isinstance(featured, dict) else None,
            "method": method,
            "label": originated.get("label") or "",
            "source": originated.get("source") or "",
            "source_url": originated.get("source_url") or "",
            "probabilities": originated.get("probabilities"),
            "pick_index": orig.get("pick_index"),
            "in_complete_feed": bool(orig),
            "money_backed": method in MONEY_METHODS,
        }
        active.append(row)

    active.sort(key=lambda r: (r["starts_at"] or "9999", r["id"]))
    model_only = [r for r in active if r["method"] and not r["money_backed"]]
    no_pick = [r for r in active if not r["method"]]
    missing_from_feed = [r for r in active if not r["in_complete_feed"]]

    return {
        "schema": "a7128fdd-live-manifest/1",
        "generated_at": observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snapshot_generated_at": latest.get("generated_at"),
        "inventory_observed_at": latest.get("inventory_observed_at"),
        "origination_generated_at": origination.get("generated_at"),
        "counts": {
            "active": len(active),
            "money_backed": sum(1 for r in active if r["money_backed"]),
            "model_only": len(model_only),
            "no_pick": len(no_pick),
            "missing_from_complete_feed": len(missing_from_feed),
        },
        "active": active,
        "model_only": model_only,
        "no_pick": no_pick,
        "missing_from_complete_feed": missing_from_feed,
    }


def render_markdown(manifest: dict) -> str:
    c = manifest["counts"]
    lines = [
        "# Live manifest — every active Hotspawn CS2 fixture (arena-a7128fdd)",
        "",
        f"- Manifest generated: **{manifest['generated_at']}**",
        f"- Snapshot `generated_at`: `{manifest['snapshot_generated_at']}`",
        f"- Inventory observed: `{manifest['inventory_observed_at']}`",
        f"- Origination generated: `{manifest['origination_generated_at']}`",
        "",
        f"**{c['active']} active · {c['money_backed']} money-backed · "
        f"{c['model_only']} model-only · {c['no_pick']} with no pick · "
        f"{c['missing_from_complete_feed']} missing from the complete-picks feed**",
        "",
        "## Model-only fixtures (no external money line — the research class)",
        "",
        "| Hotspawn id | Teams | Competition | Starts (UTC) | Method | Source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in manifest["model_only"]:
        lines.append(
            "| {id} | {t} | {c} | {s} | {m} | {src} |".format(
                id=r["id"],
                t=" vs ".join(r["teams"]),
                c=r["competition"],
                s=r["starts_at"],
                m=r["label"] or r["method"],
                src=r["source"] or "—",
            )
        )
    if not manifest["model_only"]:
        lines.append("| — | none | — | — | — | — |")
    lines += [
        "",
        "## Fixtures with no pick at all",
        "",
    ]
    if manifest["no_pick"]:
        lines += [
            "| Hotspawn id | Teams | Competition | Starts (UTC) |",
            "| --- | --- | --- | --- |",
        ]
        for r in manifest["no_pick"]:
            lines.append(
                f"| {r['id']} | {' vs '.join(r['teams'])} | {r['competition']} | {r['starts_at']} |"
            )
    else:
        lines.append("None — every active fixture carries a directional pick in this snapshot.")
    lines += [
        "",
        "## Every active fixture",
        "",
        "| Hotspawn id | Teams | Competition | Starts (UTC) | Money-backed | Method | Probabilities |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in manifest["active"]:
        probs = r["probabilities"]
        ptext = (
            f"{probs[0]:.4f} / {probs[1]:.4f}"
            if isinstance(probs, list) and len(probs) == 2 and all(isinstance(p, (int, float)) for p in probs)
            else "—"
        )
        lines.append(
            "| {id} | {t} | {c} | {s} | {mb} | {m} | {p} |".format(
                id=r["id"],
                t=" vs ".join(r["teams"]),
                c=r["competition"],
                s=r["starts_at"],
                mb="yes" if r["money_backed"] else "no",
                m=r["method"] or "—",
                p=ptext,
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    manifest = build_manifest()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "live-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "live-manifest.md").write_text(render_markdown(manifest), encoding="utf-8")
    c = manifest["counts"]
    print(
        "live manifest: {active} active, {money} money-backed, {model} model-only, "
        "{none} no-pick -> {out}".format(
            active=c["active"],
            money=c["money_backed"],
            model=c["model_only"],
            none=c["no_pick"],
            out=OUT_DIR.relative_to(ROOT),
        )
    )
    for r in manifest["model_only"]:
        print(f"  model-only {r['id']}: {' vs '.join(r['teams'])} @ {r['starts_at']} ({r['competition']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
