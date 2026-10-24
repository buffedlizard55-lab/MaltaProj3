"""Session arena-99d48cd8: reconcile the live Hotspawn lobby with the published picks.

Reads (only):
  - data/research/99d48cd8/observations-2026-10-24.json  (verbatim first-hand reads)
  - snapshot.json  (checked-in published snapshot, branch root)

Writes (only inside data/research/99d48cd8/):
  - reconciliation-2026-10-24.json / .md      every lobby card vs the published pick
  - unresolved-limitations-2026-10-24.json/.md the separate unresolved section:
    each fixture with no featured pick, the blocker, every source tried, and the
    limitation — written for the executive summary with in-site links.

Rules this script must never break:
  - No probability, pick or alias is computed or emitted. Polymarket/EGamersWorld
    display figures are copied verbatim from the observations file and labelled
    as display evidence for the reviewed collector, never as a pick.
  - Hotspawn "% picked" and HLTV fan votes are never inputs (they are not even
    present in the observations file).
  - A Polymarket observation counts as a priced lead only with non-zero volume
    and a two-sided display sum <= 112 cents (the collector's 12c spread bound);
    an EGamersWorld observation only with non-identical header decimals.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "research" / "99d48cd8"
OBS_PATH = OUT_DIR / "observations-2026-10-24.json"
SNAPSHOT_PATH = ROOT / "snapshot.json"

PM_MAX_SUM_CENTS = 112  # collector bound: books crossed/wider than 12c are refused


def pm_is_priced(pm: dict | None) -> bool:
    if not pm or not pm.get("display_cents"):
        return False
    if not (pm.get("volume_usd") or 0) > 0:
        return False
    total = sum(pm["display_cents"].values())
    stated = pm.get("display_sum_cents")
    if stated is not None and stated != total:
        raise SystemExit(f"display sum mismatch: stated {stated} != summed {total} for {pm.get('url')}")
    return total <= PM_MAX_SUM_CENTS


def egw_is_priced(egw: dict | None) -> bool:
    if not egw or not egw.get("header_decimal"):
        return False
    values = [v for k, v in egw["header_decimal"].items() if k]
    return len(values) == 2 and values[0] != values[1] and all(v > 1 for v in values)


def expected_assessment(entry: dict) -> str:
    pm, egw = pm_is_priced(entry.get("polymarket")), egw_is_priced(entry.get("egamersworld"))
    if pm and egw:
        return "priced_lead_two_independent_sources"
    return None  # unpriced variants are stated per-fixture in the observations


def no_vig_from_decimals(a: float, b: float) -> tuple[float, float]:
    """Evidence arithmetic only (cross-source agreement check) — never a pick."""
    ia, ib = 1.0 / a, 1.0 / b
    return round(100 * ia / (ia + ib), 1), round(100 * ib / (ia + ib), 1)


def main() -> None:
    obs = json.loads(OBS_PATH.read_text())
    snap = json.loads(SNAPSHOT_PATH.read_text())
    generated = snap["generated_at"]
    by_id = {m["id"]: m for m in snap["matches"]}
    upcoming = {m["id"]: m for m in snap["matches"] if (m.get("starts_at") or "") >= generated}
    gap = {g["id"]: g for g in obs["gap_fixture_research"]}

    rows, covered, missing = [], [], []
    for card in obs["lobby"]["cards"]:
        cid = card["id"]
        pub = upcoming.get(cid)
        row = {
            "id": cid,
            "teams": card["teams"],
            "competition": card["competition"],
            "lobby_time_displayed": card["lobby_time_displayed"],
            "source_url": card["source_url"],
            "in_published_snapshot_upcoming": pub is not None,
            "starts_at_utc_published": pub["starts_at"] if pub else None,
            "published_method": (pub or {}).get("analysis", {}).get("method") if pub and pub.get("analysis") else None,
            "published_pick_index": pub.get("pick_index") if pub else None,
            "published_source_url": pub["source_url"] if pub else None,
            "source_url_matches_published": (pub["source_url"] == card["source_url"]) if pub else None,
        }
        (covered if pub else missing).append(cid)
        rows.append(row)

    lobby_ids = {c["id"] for c in obs["lobby"]["cards"]}
    past_published = sorted(set(upcoming) - lobby_ids)
    unresolved_published = sorted(i for i, m in upcoming.items() if m.get("pick_index") is None)

    # Cross-source agreement check for priced leads (evidence only).
    leads = []
    for gid, g in gap.items():
        want = expected_assessment(g)
        if want and g["assessment"] != want:
            raise SystemExit(f"{gid}: assessment {g['assessment']!r} != derived {want!r}")
        if g["assessment"] == "priced_lead_two_independent_sources":
            if not want:
                raise SystemExit(f"{gid}: stated priced lead fails the priced-lead rule")
            pm_cents = g["polymarket"]["display_cents"]
            egw_dec = {k: v for k, v in g["egamersworld"]["header_decimal"].items() if k}
            (e1, d1), (e2, d2) = list(egw_dec.items())
            nv1, nv2 = no_vig_from_decimals(d1, d2)
            leads.append({
                "id": gid, "teams": g["teams"],
                "polymarket_display_cents": pm_cents,
                "polymarket_volume_usd": g["polymarket"]["volume_usd"],
                "egamersworld_header_decimal": egw_dec,
                "egamersworld_no_vig_pct_evidence_only": {e1: nv1, e2: nv2},
                "note": "No-vig figure is evidence arithmetic on the verbatim EGamersWorld pair, shown only to test cross-source agreement. It is not a published probability; the collector re-derives from validated books on its next run.",
            })

    reconciliation = {
        "session": obs["session"],
        "read_window_utc": obs["read_window_utc"],
        "published_snapshot": obs["published_snapshot"],
        "totals": {
            "lobby_future_cards": len(rows),
            "covered_by_published_snapshot": len(covered),
            "missing_from_published_snapshot": len(missing),
            "published_upcoming_no_longer_in_future_lobby": len(past_published),
            "published_unresolved": len(unresolved_published),
            "gap_fixtures_researched": len(gap),
            "priced_leads_two_sources": sum(1 for g in gap.values() if g["assessment"] == "priced_lead_two_independent_sources"),
        },
        "missing_ids": sorted(missing),
        "past_published_ids": past_published,
        "published_unresolved_ids": unresolved_published,
        "rows": rows,
        "priced_lead_crosscheck": leads,
    }

    # --- separate unresolved / no-featured-pick section (for the executive summary) ---
    site = "https://buffedlizard55-lab.github.io/MaltaProj3"
    blockers = {
        "priced_lead_two_independent_sources": "Not in the published snapshot yet (publisher starved since 2026-10-23T20:10Z). A real two-sided line exists at two independent sources read first-hand; the next successful collector run is expected to originate the pick from validated books. Limitation: board display cents are last-trade displays — the collector must still validate live bid/ask books, exact names and exact start before publishing.",
        "unpriced_placeholder_books_only": "No validated line exists at the sources checked: Polymarket shows a $0.00-volume display whose two sides sum far above 100 cents (placeholder), and EGamersWorld shows identical 1.8/1.8 header decimals (placeholder). Limitation: originating a percentage from placeholder books would be inventing a number, so the pick stays blank until a book posts a real two-sided price or the research model can bind both teams.",
        "unpriced_placeholder_books_and_name_conflict": "Placeholder books at both sources plus a team-identity conflict: Hotspawn renders 'LFO 10', Polymarket renders 'Sökerorg' for the same slot, EGamersWorld renders the opponent name blank. Limitation: this project never aliases a team silently; roster evidence (Sapec, dottie, flaw, L00m1 shared with HLTV's LFO 10) is recorded for a reviewed alias decision, and a real price is still absent.",
        "unpriced_crossed_book_and_no_valve_rating": "Polymarket event exists but the collector refused its book (crossed or wider than 12 cents) and the board still shows $0 volume; original esportsbooks returned errors/landing pages at snapshot time; the Valve research model cannot bind 'Off Chops' (no exact-name rating). Limitation: no rung of the ladder can produce a sourced number today.",
        "unpriced_placeholder_book_and_ambiguous_valve_identity": "A Polymarket market has appeared since the snapshot but is a $0.00-volume placeholder (187-cent two-sided sum); the Valve model is blocked because multiple Valve rosters share the name 'The Huns'. Limitation: neither a market line nor a safely-bound model input exists today.",
    }
    unresolved = []
    for gid in sorted(gap, key=lambda i: (gap[i]["gap_kind"], i)):
        g = gap[gid]
        unresolved.append({
            "id": gid,
            "teams": g["teams"],
            "gap_kind": g["gap_kind"],
            "assessment": g["assessment"],
            "blocker_and_limitation": blockers[g["assessment"]],
            "hotspawn_url": next(c["source_url"] for c in obs["lobby"]["cards"] if c["id"] == gid) if any(c["id"] == gid for c in obs["lobby"]["cards"]) else (by_id[gid]["source_url"] if gid in by_id else None),
            "site_links": {
                "executive_summary": f"{site}/",
                "pick_row": f"{site}/picks/#match-{gid}",
                "unresolved_page": f"{site}/unresolved/",
                "audit_trail": f"{site}/origination/#match-{gid}",
            },
            "sources_tried": {k: g.get(k) for k in ("hltv", "polymarket", "egamersworld")},
        })
    unresolved_doc = {
        "session": obs["session"],
        "read_window_utc": obs["read_window_utc"],
        "title": "Unresolved picks & limitations — fixtures with no featured pick (2026-10-24)",
        "how_to_use_on_phone": [
            f"Start at the executive summary: {site}/ (banner: 'start here on your phone').",
            f"Every updated pick: {site}/picks/ — one row per match, both team percentages, pick highlighted.",
            f"Fixtures still without a pick, and why: {site}/unresolved/ and the per-fixture audit trails under {site}/origination/.",
            f"Flagged items for manual review: {site}/review/ · method: {site}/methodology/ · freshness/source health: {site}/coverage/.",
        ],
        "entries": unresolved,
    }

    (OUT_DIR / "reconciliation-2026-10-24.json").write_text(json.dumps(reconciliation, indent=1) + "\n")
    (OUT_DIR / "unresolved-limitations-2026-10-24.json").write_text(json.dumps(unresolved_doc, indent=1) + "\n")

    t = reconciliation["totals"]
    md = [f"# Lobby reconciliation — 2026-10-24 (session arena-99d48cd8)\n",
          f"Read window (UTC): {obs['read_window_utc']['start']} – {obs['read_window_utc']['end']}. "
          f"Lobby: {obs['lobby']['url']} ({obs['lobby']['rendered_header']!r}, {obs['lobby']['tier_filter_label']!r}). "
          f"Published snapshot: {generated} (`{snap['run_status']}`, counts {snap['counts']}).\n",
          f"**{t['lobby_future_cards']} future cards · {t['covered_by_published_snapshot']} covered · "
          f"{t['missing_from_published_snapshot']} missing · {t['published_upcoming_no_longer_in_future_lobby']} published rows now past start · "
          f"{t['published_unresolved']} published unresolved.** Missing: {', '.join(reconciliation['missing_ids'])}. "
          f"Past: {', '.join(past_published)}. Unresolved: {', '.join(unresolved_published)}.\n",
          "| ID | Match | Competition | Lobby time (as rendered) | Published? | Method | Hotspawn source |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['id']} | {' vs '.join(r['teams'])} | {r['competition']} | {r['lobby_time_displayed']} | "
                  f"{'yes' if r['in_published_snapshot_upcoming'] else '**missing**'} | {r['published_method'] or '—'} | [Hotspawn]({r['source_url']}) |")
    md.append("\nLobby times are transcribed verbatim; the render timezone was not verified, so no UTC start is inferred from them. "
              "Hotspawn '% picked' figures are never used as probabilities and are not transcribed.\n")
    (OUT_DIR / "reconciliation-2026-10-24.md").write_text("\n".join(md) + "\n")

    umd = [f"# {unresolved_doc['title']}\n",
           "## Where the updated picks live (phone-first)\n"]
    umd += [f"- {line}" for line in unresolved_doc["how_to_use_on_phone"]]
    umd.append("\n## Fixtures with no featured pick, and the limitation for each\n")
    for u in unresolved:
        umd.append(f"### {' vs '.join(u['teams'])} (`{u['id']}`, {u['gap_kind']})\n")
        umd.append(f"- **Limitation:** {u['blocker_and_limitation']}")
        umd.append(f"- **Hotspawn:** {u['hotspawn_url']}")
        umd.append(f"- **On our site:** [summary]({u['site_links']['executive_summary']}) · [pick row]({u['site_links']['pick_row']}) · "
                   f"[unresolved]({u['site_links']['unresolved_page']}) · [audit trail]({u['site_links']['audit_trail']})")
        for name in ("hltv", "polymarket", "egamersworld"):
            s = u["sources_tried"][name] or {}
            detail = s.get("detail") or s.get("note") or ""
            umd.append(f"- **{name}:** {s.get('url') or '—'} — {detail}")
        umd.append("")
    (OUT_DIR / "unresolved-limitations-2026-10-24.md").write_text("\n".join(umd) + "\n")
    print(f"lobby {t['lobby_future_cards']} covered {t['covered_by_published_snapshot']} missing {t['missing_from_published_snapshot']} "
          f"past {t['published_upcoming_no_longer_in_future_lobby']} unresolved {t['published_unresolved']} priced-leads {t['priced_leads_two_sources']}")


if __name__ == "__main__":
    main()
