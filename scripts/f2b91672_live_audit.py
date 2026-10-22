"""Session f2b91672 — reproducible live verification & origination-replay dossier.

Verifies the 2026-10-22 live observations captured from:
  - Hotspawn lobby & Cloudways fixtures API (`play.hotspawn.com/lobby`)
  - HLTV match & team pages (`2399904`..`2399907`, `2399911`, `2399499`, `team/14084/lfo-10`)
  - Polymarket Gamma API (`1232953`, `1232955`, `1232957`, `1232958`, `1233762`, `1233768`)
  - Pinnacle Arcadia guest API (`league 235977`: `1638943045`, `1638943044`, `1638938930`)
  - bo3.gg match page (`tropa-do-kingui-vs-martians-22-10-2026`)

Writes read-only research artifacts under `data/research/f2b91672/` only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import originate
from scripts.pinnacle_lines import american_to_decimal

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "research" / "f2b91672"
NOW = datetime(2026, 10, 22, 9, 12, tzinfo=timezone.utc)

SCOPED_ALIAS_EXPECTATIONS = [
    ("Tropa do KinGui", "CCT South America 2026 Series #7", "Projeto do KinGui"),
    ("Procyon Gaming", "CCT South America 2026 Series #7", "Procyon"),
    ("Yawara Esports", "CCT South America 2026 Series #7", "Yawara"),
    ("Low Cortisol", "CCT South America 2026 Series #7", "Low Cortisol BR"),
    ("Grêmio Esports", "CCT South America 2026 Series #7", "Grêmio"),
    ("Gremio", "CCT South America 2026 Series #7", "Grêmio"),
    ("Hacha Esports", "CCT South America 2026 Series #7", "Hacha"),
    ("Sökerorg", "CCT Europe 2026 Series #12", "LFO 10"),
]


def _poly_row(
    *,
    event_id: str,
    market_id: str,
    slug: str,
    names: list[str],
    start: str,
    bid0: float,
    ask0: float,
) -> dict:
    bid1 = round(1.0 - ask0, 4)
    ask1 = round(1.0 - bid0, 4)
    return {
        "family": "market",
        "provider": "Polymarket",
        "event_id": event_id,
        "market_id": market_id,
        "names": names,
        "start": start,
        "bid": [bid0, bid1],
        "ask": [ask0, ask1],
        "source_url": f"https://gamma-api.polymarket.com/events?slug={slug}",
        "observed_at": "2026-10-22T09:05:00Z",
        "evidence_file": f"data/research/f2b91672/live-audit.json#{event_id}",
    }


def _pinnacle_row(*, matchup_id: str, names: list[str], start: str, us_prices: list[int]) -> dict:
    return {
        "family": "bookmaker",
        "provider": "Pinnacle",
        "event_id": matchup_id,
        "market_id": f"{matchup_id}:0:s;0;m",
        "names": names,
        "start": start,
        "odds": [round(american_to_decimal(p), 6) for p in us_prices],
        "american_prices": us_prices,
        "source_url": "https://guest.api.arcadia.pinnacle.com/0.1/leagues/235977/markets/straight",
        "observed_at": "2026-10-22T09:11:00Z",
        "evidence_file": f"data/research/f2b91672/live-audit.json#{matchup_id}",
    }


def build_audit() -> dict:
    registry = originate.load_registry(ROOT / "data" / "origination" / "aliases.json")

    alias_checks = []
    for alias, competition, canonical in SCOPED_ALIAS_EXPECTATIONS:
        resolved, used = originate.resolve_name(alias, registry, competition)
        leaked, leaked_used = originate.resolve_name(alias, registry, "Unrelated Tournament 2026")
        alias_checks.append(
            {
                "alias": alias,
                "competition": competition,
                "expected_canonical": canonical,
                "resolved_key": resolved,
                "matches_expected": resolved == originate.name_key(canonical) and bool(used),
                "isolated_outside_scope": leaked == originate.name_key(alias) and not leaked_used,
                "evidence_urls": [ev["url"] for u in used for ev in u.get("evidence", [])],
            }
        )

    poly_rows = [
        _poly_row(
            event_id="1232953",
            market_id="m-1232953",
            slug="cs2-tdkg-mar1-2026-10-22",
            names=["Tropa do KinGui", "Martians"],
            start="2026-10-22T13:00:00Z",
            bid0=0.57,
            ask0=0.76,
        ),
        _poly_row(
            event_id="1232955",
            market_id="m-1232955",
            slug="cs2-meiano-pcy-2026-10-22",
            names=["MEIA NOITE", "Procyon Gaming"],
            start="2026-10-22T16:00:00Z",
            bid0=0.47,
            ask0=0.50,
        ),
        _poly_row(
            event_id="1232957",
            market_id="m-1232957",
            slug="cs2-yaw-youren-2026-10-22",
            names=["Yawara Esports", "your end"],
            start="2026-10-22T19:00:00Z",
            bid0=0.83,
            ask0=0.89,
        ),
        _poly_row(
            event_id="1232958",
            market_id="m-1232958",
            slug="cs2-lowcor1-grmioe-2026-10-22",
            names=["Low Cortisol", "Grêmio Esports"],
            start="2026-10-22T22:00:00Z",
            bid0=0.29,
            ask0=0.30,
        ),
        _poly_row(
            event_id="1233762",
            market_id="m-1233762",
            slug="cs2-forzer-skr2-2026-10-23",
            names=["FORZE Reload", "Sökerorg"],
            start="2026-10-23T14:00:00Z",
            bid0=0.04,
            ask0=0.96,
        ),
        _poly_row(
            event_id="1233768",
            market_id="m-1233768",
            slug="cs2-isg-hachae-2026-10-23",
            names=["Isurus", "Hacha Esports"],
            start="2026-10-23T22:00:00Z",
            bid0=0.04,
            ask0=0.96,
        ),
    ]

    book_rows = [
        _pinnacle_row(
            matchup_id="1638943044",
            names=["MEIA NOITE", "Procyon"],
            start="2026-10-22T16:00:00Z",
            us_prices=[-108, -123],
        ),
        _pinnacle_row(
            matchup_id="1638938930",
            names=["Yawara", "your end"],
            start="2026-10-22T19:00:00Z",
            us_prices=[-1040, 440],
        ),
        _pinnacle_row(
            matchup_id="1638943045",
            names=["Low Cortisol", "Gremio"],
            start="2026-10-22T22:00:00Z",
            us_prices=[208, -315],
        ),
    ]

    hltv_rank = [
        {"name": "FORZE Reload", "rank": 127, "points": 14.0},
        {"name": "LFO 10", "rank": 167, "points": 7.0},
        {"name": "Isurus", "rank": 215, "points": 2.0},
        {"name": "Hacha", "rank": 229, "points": 2.0},
        {"name": "Martians", "rank": 240, "points": 1.0},
    ]
    hltv_meta = {
        "published_at": "2026-10-20T00:00:00Z",
        "observed_at": "2026-10-22T09:05:00Z",
        "source_url": "https://www.hltv.org/ranking/teams",
        "evidence_file": "data/research/f2b91672/live-audit.json#hltv-ranking",
    }

    fixtures = [
        {
            "id": "1082919",
            "competition": "CCT South America 2026 Series #7",
            "starts_at": "2026-10-22T13:00:00Z",
            "teams": [{"id": "t-pdkg", "name": "Projeto do KinGui"}, {"id": "t-mar", "name": "Martians"}],
            "source_url": "https://www.hotspawn.com/matches/projeto-do-kingui-vs-martians-cct-south-america-2026-series-7-1082919",
            "prior_live_state": "50.1% Martians (HLTV 0.0-pt unranked floor; inverted vs Polymarket 0.57/0.76 & bo3.gg 56%)",
        },
        {
            "id": "1082920",
            "competition": "CCT South America 2026 Series #7",
            "starts_at": "2026-10-22T16:00:00Z",
            "teams": [{"id": "t-mn", "name": "MEIA NOITE"}, {"id": "t-pcy", "name": "Procyon"}],
            "source_url": "https://www.hotspawn.com/matches/meia-noite-vs-procyon-cct-south-america-2026-series-7-1082920",
            "prior_live_state": "Single-book Pinnacle only (Polymarket 'Procyon Gaming' missed)",
        },
        {
            "id": "1082921",
            "competition": "CCT South America 2026 Series #7",
            "starts_at": "2026-10-22T19:00:00Z",
            "teams": [{"id": "t-yaw", "name": "Yawara"}, {"id": "t-ye", "name": "your end"}],
            "source_url": "https://www.hotspawn.com/matches/yawara-vs-your-end-cct-south-america-2026-series-7-1082921",
            "prior_live_state": "Single-book Pinnacle only (Polymarket 'Yawara Esports' missed)",
        },
        {
            "id": "1082922",
            "competition": "CCT South America 2026 Series #7",
            "starts_at": "2026-10-22T22:00:00Z",
            "teams": [{"id": "t-lcbr", "name": "Low Cortisol BR"}, {"id": "t-gre", "name": "Grêmio"}],
            "source_url": "https://www.hotspawn.com/matches/low-cortisol-br-vs-gremio-cct-south-america-2026-series-7-1082922",
            "prior_live_state": "66.2% Low Cortisol BR (dated 2026-10-05 Valve row; inverted vs Polymarket 70.5% & Pinnacle 70.0% Grêmio)",
        },
        {
            "id": "1081149",
            "competition": "CCT Europe 2026 Series #12",
            "starts_at": "2026-10-23T14:00:00Z",
            "teams": [{"id": "t-fr", "name": "FORZE Reload"}, {"id": "t-lfo", "name": "LFO 10"}],
            "source_url": "https://www.hotspawn.com/matches/forze-reload-vs-lfo-10-cct-europe-2026-series-12-1081149",
            "prior_live_state": "HLTV model (Polymarket 'Sökerorg' unjoined)",
        },
        {
            "id": "1082926",
            "competition": "CCT South America 2026 Series #7",
            "starts_at": "2026-10-23T22:00:00Z",
            "teams": [{"id": "t-isg", "name": "Isurus"}, {"id": "t-hac", "name": "Hacha"}],
            "source_url": "https://www.hotspawn.com/matches/isurus-vs-hacha-cct-south-america-2026-series-7-1082926",
            "prior_live_state": "50.0% / 50.0% even without pick on 08:22Z live board",
        },
    ]

    replayed = []
    for fixture in fixtures:
        res = originate.originate_match(
            fixture,
            poly_rows,
            book_rows,
            {},
            {"source_url": "https://github.com/ValveSoftware/counter-strike_regional_standings"},
            registry,
            NOW,
            hltv_rank=hltv_rank,
            hltv_meta=hltv_meta,
        )
        orig = res["origination"] or {}
        pick_idx = res["pick_index"]
        replayed.append(
            {
                "id": fixture["id"],
                "competition": fixture["competition"],
                "starts_at": fixture["starts_at"],
                "teams": [t["name"] for t in fixture["teams"]],
                "prior_live_state": fixture["prior_live_state"],
                "method": orig.get("method"),
                "label": orig.get("label"),
                "source": orig.get("source"),
                "probabilities": orig.get("probabilities"),
                "pick_index": pick_idx,
                "pick_team": fixture["teams"][pick_idx]["name"] if pick_idx is not None else None,
                "aliases_used": [f"{a['alias']} -> {a['canonical']}" for a in res["aliases_used"]],
                "source_url": orig.get("source_url"),
            }
        )

    return {
        "session": "arena-f2b91672",
        "observed_at": "2026-10-22T09:12:00Z",
        "alias_checks": alias_checks,
        "replayed_fixtures": replayed,
    }


def render_markdown(audit: dict) -> str:
    lines = [
        "# Session `arena-f2b91672` — Live Verification & Origination Audit (2026-10-22)",
        "",
        f"Observed at `{audit['observed_at']}` against live Hotspawn, HLTV, Polymarket Gamma, Pinnacle Arcadia, and bo3.gg.",
        "",
        "## 1. Verified Competition-Scoped Aliases",
        "",
        "| Alias | Competition Scope | Canonical Team | Scoped Join | Isolated Outside Scope | Official Evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in audit["alias_checks"]:
        ev = " · ".join(f"[link]({u})" for u in c["evidence_urls"])
        lines.append(
            f"| `{c['alias']}` | `{c['competition']}` | `{c['expected_canonical']}` | "
            f"`{c['matches_expected']}` | `{c['isolated_outside_scope']}` | {ev} |"
        )
    lines.extend(
        [
            "",
            "## 2. Replayed Live Fixture Outcomes",
            "",
            "| Fixture | Matchup | Prior `08:22Z` Live State | Updated Method (`source`) | Probabilities | Directional Pick | Scoped Aliases Used |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for r in audit["replayed_fixtures"]:
        probs = (
            f"{r['probabilities'][0]*100:.1f}% / {r['probabilities'][1]*100:.1f}%"
            if r["probabilities"]
            else "blank"
        )
        aliases = ", ".join(f"`{a}`" for a in r["aliases_used"]) or "exact"
        lines.append(
            f"| `{r['id']}` | {' vs '.join(r['teams'])} | {r['prior_live_state']} | "
            f"`{r['method']}` (`{r['source']}`) | `{probs}` | **{r['pick_team']}** | {aliases} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    (OUT_DIR / "live-audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    (OUT_DIR / "live-audit.md").write_text(render_markdown(audit))
    print(f"wrote {OUT_DIR / 'live-audit.json'} and {OUT_DIR / 'live-audit.md'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
