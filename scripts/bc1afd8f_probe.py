"""Session arena-bc1afd8f — live pick-coverage report plus HLTV-first line research.

Read-only. The coding sandbox has no egress to Hotspawn, HLTV or any bookmaker;
the GitHub runner does, so this module is executed by
``.github/workflows/bc1afd8f-live.yml`` right after the repository's own
collectors (``scripts.collect`` and ``scripts.originate --live``) have produced a
fresh snapshot. It then answers two questions the brief asks, per fixture:

1. **Does every listed match have a pick?** Each active Hotspawn CS2 fixture is
   classified from the snapshot's own fields — ``money-line`` (an external
   betting line produced the number), ``model-only`` (a research model produced
   it, no two-sided price was reachable) or ``blank`` (nothing produced it) —
   with both probabilities, the pick, the method label the row itself carries and
   the row's own source URL.
2. **For the fixtures without a betting line, what did the independent sources
   actually say?** HLTV first, then esportsbooks / betting-line surfaces. Each
   surface is recorded with its HTTP status, final URL, payload size, title,
   whether it served a challenge page, and whether the *exact* team names of the
   line-less fixtures appear in the payload (word-boundary matching, names
   shorter than three characters are skipped so a two-letter tag cannot
   substring-match inside an unrelated word or URL).

It never writes a probability, a pick, an alias or a price, and it never edits
the canonical feeds: the collector's outputs are restored before the workflow
commits, and only ``data/research/bc1afd8f/`` is committed. A blocked source is
published as blocked; it is never treated as proof that no market exists, and no
number is invented to fill the gap.

Usage
-----
    python -m scripts.bc1afd8f_probe                     # read data/, write data/research/bc1afd8f/
    python -m scripts.bc1afd8f_probe --no-network        # coverage report only (offline safe)
    python -m scripts.bc1afd8f_probe --data DIR --out DIR --timeout 12
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence

UTC = timezone.utc
SCHEMA_VERSION = 1
SESSION = "arena-bc1afd8f"

#: Mirrors ``scripts.build.MONEY_METHODS``. Imported when possible so the two
#: reports can never disagree about what counts as a betting line; the local copy
#: is the fallback if the renderer is refactored by another session.
try:  # pragma: no cover - import guard
    from scripts.build import MONEY_METHODS as _BUILD_MONEY_METHODS

    MONEY_METHODS = frozenset(_BUILD_MONEY_METHODS)
except Exception:  # pragma: no cover - import guard
    MONEY_METHODS = frozenset({"market", "bookmaker", "consensus", "reference"})

#: ``scripts.build`` treats these availability values as the live inventory.
ACTIVE_AVAILABILITY = frozenset({"open", "locked", "unknown_lock"})

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

#: Surfaces grouped by how a price could legitimately be used. Order matters: the
#: brief asks for HLTV first, then esportsbooks and betting lines. A results or
#: ratings surface can only ever support a research model, never a money line, and
#: the report says so explicitly.
SURFACES: tuple[tuple[str, str, str, str], ...] = (
    # (label, group, method, url)
    ("HLTV match listing", "hltv", "GET", "https://www.hltv.org/matches"),
    ("HLTV world ranking", "hltv", "GET", "https://www.hltv.org/ranking/teams"),
    ("HLTV CS2 results", "hltv", "GET", "https://www.hltv.org/results"),
    ("EGamersWorld CS2 matches", "aggregator", "GET", "https://egamersworld.com/counterstrike/matches"),
    ("EGamersWorld CS2 odds", "aggregator", "GET", "https://egamersworld.com/counterstrike/odds"),
    ("bo3.gg matches", "aggregator", "GET", "https://bo3.gg/matches"),
    ("Oddspedia CS2", "aggregator", "GET", "https://www.oddspedia.com/esports/counter-strike-2"),
    ("OddsPortal CS2", "aggregator", "GET", "https://www.oddsportal.com/esports/counter-strike/"),
    ("Thunderpick match API", "bookmaker", "POST", "https://thunderpick.io/api/matches"),
    ("Bovada CS2 coupon", "bookmaker", "GET", "https://www.bovada.lv/sports/esports/counter-strike-2"),
    ("Pinnacle CS2", "bookmaker", "GET", "https://www.pinnacle.com/en/esports/counter-strike-2"),
    ("GG.BET CS", "bookmaker", "GET", "https://gg.bet/en/counter-strike"),
    ("Betway CS2", "bookmaker", "GET", "https://www.betway.com/en/sports/esports/counter-strike-2"),
    ("DraftKings CS2", "bookmaker", "GET", "https://sportsbook.draftkings.com/leagues/esports/counter-strike-2"),
    ("Polymarket CS2 directory", "exchange", "GET", "https://polymarket.com/esports/cs2"),
    ("Kalshi CS2 series", "exchange", "GET", "https://kalshi.com/markets/kxcs2game/counter-strike-2-game"),
)

#: POST bodies the surface needs to answer at all. ``{"gameIds": [6]}`` is
#: Counter-Strike on Thunderpick's own public client contract (documented in
#: ``docs/SOURCE_RESEARCH.md``); a failed GET does not establish the POST is dead.
POST_BODIES = {
    "https://thunderpick.io/api/matches": {"gameIds": [6]},
}

CHALLENGE_MARKERS = (
    "just a moment",
    "cf-chl",
    "challenge-platform",
    "attention required",
    "enable javascript and cookies",
    "captcha",
    "access denied",
    "are you a robot",
    "please verify you are a human",
)

Fetch = Callable[..., dict]


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    """Read one JSON document, or return an empty mapping with the reason."""
    try:
        payload = json.loads(path.read_text())
    except FileNotFoundError:
        return {"__missing__": str(path)}
    except json.JSONDecodeError as exc:
        return {"__unreadable__": f"{path}: {exc}"}
    return payload if isinstance(payload, dict) else {"__unexpected_shape__": str(path)}


def team_names(row: dict) -> list[str]:
    return [str((team or {}).get("name") or "") for team in (row.get("teams") or [])]


def classify(row: dict) -> str:
    """``money-line`` / ``model-only`` / ``blank`` from the row's own fields."""
    origination = row.get("origination") or {}
    method = origination.get("method")
    pick = row.get("pick_index")
    probabilities = origination.get("probabilities") or []
    if pick is None or len(probabilities) != 2:
        return "blank"
    if method in MONEY_METHODS or origination.get("quotes"):
        return "money-line"
    return "model-only"


def fixture_row(match: dict, originated: dict | None = None) -> dict:
    """One line of the coverage report, using only fields the snapshot carries.

    The basis is the originated row when the fixture has one; otherwise the
    inventory row's own ``analysis`` block, which carries the same shape. Both are
    read, never recomputed.
    """
    originated = originated or {}
    basis = originated.get("origination") or match.get("analysis") or {}
    probabilities = basis.get("probabilities") or []
    pick = originated.get("pick_index")
    if pick is None:
        pick = match.get("pick_index")
    names = team_names(match)
    basis_name = "originated" if originated.get("origination") else "featured-inventory"
    row = {
        "hotspawn_id": match.get("id"),
        "basis": basis_name,
        "teams": names,
        "competition": match.get("competition"),
        "starts_at": match.get("starts_at"),
        "locks_at": match.get("locks_at"),
        "availability": match.get("availability"),
        "tier": match.get("tier"),
        "hotspawn_source_url": match.get("source_url"),
        "lobby_url": match.get("lobby_url"),
        "classification": classify({"origination": basis, "pick_index": pick}),
        "pick_index": pick,
        "pick_team": names[pick] if isinstance(pick, int) and pick < len(names) else None,
        "probabilities": probabilities if len(probabilities) == 2 else [],
        "method": basis.get("method"),
        "method_label": basis.get("label"),
        "line_source": basis.get("source"),
        "line_source_url": basis.get("source_url"),
        "line_observed_at": basis.get("observed_at"),
        "money_providers": sorted(
            {str((quote or {}).get("provider") or "") for quote in (basis.get("quotes") or []) if quote}
        ),
        "limitations": list(originated.get("limitations") or match.get("limitations") or []),
        "research_trail": [
            {
                "stage": stage.get("stage"),
                "status": stage.get("status"),
                "source_url": stage.get("source_url"),
                "detail": stage.get("detail"),
            }
            for stage in (originated.get("research") or [])
        ],
    }
    row["active"] = row["availability"] in ACTIVE_AVAILABILITY
    return row


def coverage_rows(latest: dict, origination: dict) -> list[dict]:
    """Every inventory fixture, joined to its originated line where one exists."""
    originated_by_id = {str(m.get("id")): m for m in (origination.get("matches") or [])}
    rows = []
    for match in latest.get("matches") or []:
        rows.append(fixture_row(match, originated_by_id.get(str(match.get("id")))))
    return rows


def coverage_counts(rows: Sequence[dict]) -> dict:
    active = [row for row in rows if row["active"]]
    archived = [row for row in rows if not row["active"]]
    tally = {
        "inventory": len(rows),
        "active": len(active),
        "archived_past_start": len(archived),
        "active_with_pick": sum(1 for row in active if row["pick_index"] is not None),
        "active_money_line": sum(1 for row in active if row["classification"] == "money-line"),
        "active_model_only": sum(1 for row in active if row["classification"] == "model-only"),
        "active_blank": sum(1 for row in active if row["classification"] == "blank"),
        "active_missing_second_probability": sum(
            1 for row in active if row["pick_index"] is not None and len(row["probabilities"]) != 2
        ),
    }
    tally["active_without_betting_line"] = tally["active_model_only"] + tally["active_blank"]
    return tally


def name_pattern(name: str) -> re.Pattern[str] | None:
    """A word-boundary pattern for an exact team name, or ``None`` if too short.

    Substring matching produced a false "found on HLTV" for the two-letter tag
    ``WW`` inside unrelated words and URLs in an earlier session's probe; names
    shorter than three characters are therefore never matched at all, and the
    report says which fixtures were skipped for that reason.
    """
    cleaned = re.sub(r"\s+", " ", (name or "").strip())
    if len(cleaned) < 3:
        return None
    return re.compile(r"(?<![\w])" + re.escape(cleaned) + r"(?![\w])", re.IGNORECASE)


def fetch(session, url: str, *, method: str = "GET", payload: dict | None = None, timeout: float = 12.0) -> dict:
    """One bounded, read-only request. Every failure mode is recorded, not raised."""
    record: dict = {"url": url, "method": method, "observed_at": iso(utc_now())}
    try:
        if method.upper() == "POST":
            response = session.post(url, json=payload or {}, headers=HEADERS, timeout=timeout)
        else:
            response = session.get(url, headers=HEADERS, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - a blocked host is evidence, not a crash
        record.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return record
    body = response.text or ""
    lowered = body.lower()
    record.update(
        {
            "ok": bool(response.ok),
            "status": response.status_code,
            "final_url": str(getattr(response, "url", url)),
            "bytes": len(getattr(response, "content", b"") or b""),
            "title": (re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S).group(1).strip()[:160]
                      if re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S) else ""),
            "challenge": any(marker in lowered for marker in CHALLENGE_MARKERS),
        }
    )
    record["__body__"] = body
    return record


def probe_surfaces(fetcher: Fetch, timeout: float = 12.0) -> list[dict]:
    """Probe every surface once, HLTV first, and keep the dated evidence."""
    import requests  # imported lazily so the coverage-only path stays offline

    records = []
    with requests.Session() as session:
        for label, group, method, url in SURFACES:
            record = fetcher(session, url, method=method, payload=POST_BODIES.get(url), timeout=timeout)
            record.pop("__body__", None)
            records.append({"name": label, "group": group, **record})
    return records


def surface_bodies(fetcher: Fetch, timeout: float = 12.0) -> tuple[list[dict], dict[str, str]]:
    """Probe every surface and keep the payloads for the fixture name search."""
    import requests

    records: list[dict] = []
    bodies: dict[str, str] = {}
    with requests.Session() as session:
        for label, group, method, url in SURFACES:
            record = fetcher(session, url, method=method, payload=POST_BODIES.get(url), timeout=timeout)
            bodies[label] = record.pop("__body__", "") or ""
            records.append({"name": label, "group": group, **record})
    return records, bodies


def fixture_research(rows: Iterable[dict], bodies: dict[str, str]) -> list[dict]:
    """For every fixture without a betting line: which surfaces even list it?

    Appearance in a page is *identity* evidence only. It never becomes a price:
    the report records whether the exact names were present, and the limitation
    that no two-sided prematch price could be verified from that surface.
    """
    wanted = [row for row in rows if row["active"] and row["classification"] != "money-line"]
    out = []
    for row in wanted:
        names = row["teams"]
        patterns = [(name, name_pattern(name)) for name in names]
        skipped = [name for name, pattern in patterns if pattern is None]
        usable = [(name, pattern) for name, pattern in patterns if pattern is not None]
        hits = []
        for label, body in bodies.items():
            if not body:
                continue
            matched = [name for name, pattern in usable if pattern.search(body)]
            if matched:
                hits.append({"surface": label, "names_matched": matched})
        out.append(
            {
                "hotspawn_id": row["hotspawn_id"],
                "teams": names,
                "competition": row["competition"],
                "starts_at": row["starts_at"],
                "classification": row["classification"],
                "published_pick_team": row["pick_team"],
                "published_probabilities": row["probabilities"],
                "published_method_label": row["method_label"],
                "published_source_url": row["line_source_url"],
                "names_matched_on": hits,
                "names_too_short_to_match": skipped,
                "surfaces_probed": sorted(bodies),
                "two_sided_price_verified": False,
                "limitation": (
                    "No two-sided prematch series price could be verified from a reachable independent "
                    "source at observation time. The published number stays exactly as the snapshot's own "
                    "rung produced it; nothing here overrides, repairs or re-prices it."
                    if row["classification"] == "model-only"
                    else "No rung produced a probability for this fixture, so it stays blank and flagged."
                ),
                "research_trail": row["research_trail"],
                "hotspawn_source_url": row["hotspawn_source_url"],
            }
        )
    return out


def build_report(
    latest: dict,
    origination: dict,
    *,
    surfaces: list[dict] | None = None,
    research: list[dict] | None = None,
    observed_at: datetime | None = None,
) -> dict:
    rows = coverage_rows(latest, origination)
    moment = observed_at or utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "session": SESSION,
        "observed_at": iso(moment),
        "purpose": (
            "Independent, dated check that every active Hotspawn CS2 fixture carries a pick, and "
            "HLTV-first / esportsbook research for the fixtures that carry no betting line. "
            "No probability, pick, alias or price is produced or altered by this report."
        ),
        "snapshot": {
            "latest_generated_at": latest.get("generated_at"),
            "latest_missing": latest.get("__missing__"),
            "latest_unreadable": latest.get("__unreadable__"),
            "inventory_observed_at": latest.get("inventory_observed_at"),
            "origination_generated_at": origination.get("generated_at"),
            "origination_live_collection": origination.get("live_collection"),
            "origination_source_snapshot_at": origination.get("source_snapshot_at"),
            "inventory_crosscheck": latest.get("inventory_crosscheck"),
            "run_status": latest.get("run_status"),
        },
        "counts": coverage_counts(rows),
        "fixtures": rows,
        "line_source_research": {
            "surfaces": surfaces or [],
            "fixtures_without_a_betting_line": research or [],
            "policy": [
                "HLTV is probed first, then aggregators, then bookmakers, then prediction-market exchanges.",
                "An HTTP status is evidence about reachability. It is never narrated as a price.",
                "A refusal, a challenge page or a script shell is published as-is; no access control is bypassed.",
                "Team-name appearance is identity evidence only and never produces a probability.",
                "A ratings or results surface can support a research model, never a money line.",
            ],
        },
    }


def render_markdown(report: dict) -> str:
    counts = report["counts"]
    snapshot = report["snapshot"]
    lines = [
        f"# {SESSION} — live pick coverage and line research",
        "",
        f"Observed **{report['observed_at']}**. Read-only. Every number below is copied from the",
        "snapshot's own fields; nothing is recalculated, repaired or invented here.",
        "",
        "## Snapshot",
        "",
        f"- inventory `data/latest.json` generated_at: `{snapshot.get('latest_generated_at')}`",
        f"- inventory observed_at: `{snapshot.get('inventory_observed_at')}`",
        f"- origination `data/origination.json` generated_at: `{snapshot.get('origination_generated_at')}`",
        f"- origination live collection: `{snapshot.get('origination_live_collection')}`",
        f"- run status: `{snapshot.get('run_status')}`",
        "",
        "## Pick coverage",
        "",
        "| Measure | Count |",
        "| --- | --- |",
    ]
    for key in (
        "inventory",
        "active",
        "archived_past_start",
        "active_with_pick",
        "active_money_line",
        "active_model_only",
        "active_blank",
        "active_without_betting_line",
        "active_missing_second_probability",
    ):
        lines.append(f"| `{key}` | {counts.get(key)} |")
    lines += ["", "## Every active fixture", "", "| Fixture | Pick | Probabilities | Basis | Line source |", "| --- | --- | --- | --- | --- |"]
    for row in report["fixtures"]:
        if not row["active"]:
            continue
        names = " vs ".join(row["teams"]) or "(unnamed)"
        probabilities = (
            f"{row['probabilities'][0] * 100:.1f}% / {row['probabilities'][1] * 100:.1f}%"
            if len(row["probabilities"]) == 2
            else "—"
        )
        lines.append(
            f"| {names} (`{row['hotspawn_id']}`) | {row['pick_team'] or 'blank'} | {probabilities} "
            f"| {row['classification']} | {row['line_source'] or '—'} |"
        )
    surfaces = report["line_source_research"]["surfaces"]
    if surfaces:
        lines += ["", "## Line-source reachability at observation time", "",
                  "| Surface | Group | Result |", "| --- | --- | --- |"]
        for surface in surfaces:
            status = surface.get("status")
            if status is None:
                result = f"unreachable — {str(surface.get('error'))[:110]}"
            else:
                result = f"HTTP {status}"
                if surface.get("challenge"):
                    result += " (challenge page)"
                result += f", {surface.get('bytes')} bytes"
            lines.append(f"| [{surface['name']}]({surface['url']}) | {surface['group']} | {result} |")
    research = report["line_source_research"]["fixtures_without_a_betting_line"]
    if research:
        lines += ["", "## Fixtures without a betting line", ""]
        for item in research:
            names = " vs ".join(item["teams"])
            lines.append(f"### {names} (`{item['hotspawn_id']}`)")
            lines.append("")
            lines.append(f"- competition: {item['competition']} · starts `{item['starts_at']}`")
            lines.append(
                f"- published: {item['classification']}, pick **{item['published_pick_team'] or 'blank'}**"
                f" ({item['published_method_label'] or 'no label'})"
            )
            if item["published_source_url"]:
                lines.append(f"- published source: {item['published_source_url']}")
            matched = item["names_matched_on"]
            if matched:
                for hit in matched:
                    lines.append(f"- names seen on **{hit['surface']}**: {', '.join(hit['names_matched'])}")
            else:
                lines.append("- exact team names were not seen on any reachable surface probed")
            if item["names_too_short_to_match"]:
                lines.append(
                    "- not matched (name shorter than three characters, never substring-matched): "
                    + ", ".join(item["names_too_short_to_match"])
                )
            lines.append(f"- two-sided price verified: **{item['two_sided_price_verified']}**")
            lines.append(f"- limitation: {item['limitation']}")
            lines.append("")
    else:
        lines += ["", "## Fixtures without a betting line", "",
                  "Every active fixture in this snapshot carried an external betting line at observation time.", ""]
    return "\n".join(lines) + "\n"


def write_reports(out_dir: Path, report: dict) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["observed_at"].replace(":", "").replace("-", "")
    json_path = out_dir / f"live-coverage-{stamp}.json"
    md_path = out_dir / f"live-coverage-{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    md_path.write_text(render_markdown(report))
    # A stable name the workflow summary and the review page can link to.
    (out_dir / "live-coverage.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (out_dir / "live-coverage.md").write_text(render_markdown(report))
    return [json_path, md_path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=Path("data"), help="directory holding latest.json/origination.json")
    parser.add_argument("--out", type=Path, default=Path("data/research/bc1afd8f"))
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--no-network", action="store_true", help="coverage report only; no surface is fetched")
    parser.add_argument("--fetcher", default=None, help=argparse.SUPPRESS)  # test seam
    args = parser.parse_args(argv)

    latest = load_json(args.data / "latest.json")
    origination = load_json(args.data / "origination.json")
    rows = coverage_rows(latest, origination)

    surfaces: list[dict] = []
    research: list[dict] = []
    if not args.no_network:
        needs_research = any(row["active"] and row["classification"] != "money-line" for row in rows)
        if needs_research:
            surfaces, bodies = surface_bodies(fetch, timeout=args.timeout)
            research = fixture_research(rows, bodies)
        else:
            surfaces = probe_surfaces(fetch, timeout=args.timeout)

    report = build_report(latest, origination, surfaces=surfaces, research=research)
    written = write_reports(args.out, report)
    counts = report["counts"]
    print(
        f"{SESSION}: {counts['active']} active fixtures · {counts['active_with_pick']} with a pick · "
        f"{counts['active_money_line']} money-line · {counts['active_model_only']} model-only · "
        f"{counts['active_blank']} blank · {len(surfaces)} surfaces probed"
    )
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
