"""Independent, read-only replay of a complete-picks candidate.

This deliberately does not import the production pricing or validation modules.
It reconciles the official Hotspawn response, recomputes every money/model row,
checks the current first-hand lobby ID list, verifies Valve inputs against a
freshly retrieved official file, and refits the two own-model forms from their
saved observations.  It writes a source-linked JSON/Markdown dossier and exits
non-zero on any mismatch.  Hotspawn/HLTV popularity is never read as a price.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
SCALE = math.log(10) / 400


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def key(value: str) -> str:
    folded = "".join(c for c in unicodedata.normalize("NFKD", value or "")
                     if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", folded.casefold())


def instant(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)


def glicko_g(rd: float) -> float:
    return 1 / math.sqrt(1 + 3 * SCALE**2 * rd**2 / math.pi**2)


def expectation(a: float, b: float, rd: float = 75.0) -> list[float]:
    p = 1 / (1 + 10 ** (glicko_g(rd) * (b - a) / 400))
    return [p, 1 - p]


def logistic(a: float, b: float) -> list[float]:
    p = 1 / (1 + 10 ** ((b - a) / 400))
    return [p, 1 - p]


def no_vig(odds: list[float]) -> list[float]:
    if len(odds) != 2 or any(not isinstance(x, (int, float)) or x <= 1 for x in odds):
        raise ValueError("two decimal prices greater than one are required")
    implied = [1 / x for x in odds]
    if not 0.85 <= sum(implied) <= 1.35:
        raise ValueError("book sum outside the documented acceptance band")
    return [implied[0] / sum(implied), implied[1] / sum(implied)]


def valve_rows(text: str) -> list[dict]:
    lines = [line for line in text.splitlines() if line.startswith("|")]
    if not lines or "Standing" not in lines[0] or "Team Name" not in lines[0]:
        raise ValueError("official Valve table header not found")
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    required = ["Standing", "Points", "Team Name", "Roster"]
    if headers[:4] != required:
        raise ValueError("official Valve table columns changed")
    out = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5 or not cells[0].isdigit():
            continue
        roster = [x.strip() for x in cells[3].split(",") if x.strip()]
        out.append({"standing": int(cells[0]), "points": int(cells[1]),
                    "name": cells[2], "roster": roster,
                    "complete": len(roster) == 5})
    if not out:
        raise ValueError("official Valve table has no rows")
    return out


def unique_official(rows: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        if row["complete"]:
            grouped.setdefault(key(row["name"]), []).append(row)
    return {name: found[0] for name, found in grouped.items() if len(found) == 1}


def money_replay(orig: dict) -> tuple[list[float], str]:
    quotes = orig.get("quotes") or []
    if not quotes:
        raise ValueError("money row has no quote")
    first = quotes[0]
    if first.get("odds") is not None:
        return no_vig(first["odds"]), "decimal odds with proportional margin removal"
    if isinstance(first.get("bid"), list):
        pairs = list(zip(first["bid"], first["ask"]))
    else:
        pairs = [(q.get("bid"), q.get("ask")) for q in quotes[:2]]
    if len(pairs) != 2:
        raise ValueError("money row does not have two books")
    mids = []
    for bid, ask in pairs:
        if not all(isinstance(x, (int, float)) for x in (bid, ask)) or not 0 < bid <= ask < 1:
            raise ValueError("invalid/crossed/empty book")
        if ask - bid > 0.1500001:
            raise ValueError("book exceeds the 15-cent origination ceiling")
        mids.append((bid + ask) / 2)
    total = sum(mids)
    return [mids[0] / total, mids[1] / total], "two order-book midpoints, normalized"


def fit_form(samples: list[dict]) -> dict:
    """Independent MAP grid fit for the one unrated side."""
    center = sorted(s["opponent_points"] for s in samples)[len(samples) // 2]
    scored = []
    for rating in range(300, 2601, 5):
        lp = -0.5 * ((rating - center) / 250.0) ** 2
        for sample in samples:
            p = expectation(rating, sample["opponent_points"], 75)[0]
            p = min(max(p, 1e-6), 1 - 1e-6)
            lp += math.log(p if sample["won"] else 1 - p)
        scored.append((lp, rating))
    best_lp, best = max(scored)
    weights = [(math.exp(lp - best_lp), rating) for lp, rating in scored]
    total = sum(w for w, _ in weights)
    mean = sum(w * rating for w, rating in weights) / total
    variance = sum(w * (rating - mean)**2 for w, rating in weights) / total
    return {"points": best, "prior_center": center, "n": len(samples),
            "posterior_sd": round(math.sqrt(variance), 1)}


def form_samples(record: dict, orig: dict, bindings: dict,
                 officials: dict[str, dict]) -> tuple[list[dict], dict]:
    fitted_index = next(i for i, side in enumerate(orig["inputs"]) if side.get("fitted"))
    side = orig["inputs"][fitted_index]
    binding = (bindings.get("matches") or {}).get(str(record["id"]))
    if not binding:
        raise ValueError("form row has no saved bo3 binding")
    raw = (binding.get("results") or {}).get(key(side["name"]))
    if raw is None:
        raise ValueError("form row has no saved result series for the fitted side")
    observed = instant(binding["observed_at"])
    cutoff = observed - timedelta(days=120)
    clean = []
    for sample in raw:
        day = datetime.fromisoformat(str(sample.get("date"))[:10]).replace(tzinfo=UTC)
        opponent = officials.get(key(sample.get("opponent") or ""))
        if (day < cutoff or day > observed + timedelta(days=1)
                or sample.get("parsed") != "done" or sample.get("won") not in (True, False)
                or opponent is None):
            continue
        clean.append(dict(sample, opponent_points=opponent["points"]))
    if len(clean) < 8 or len({key(s["opponent"]) for s in clean}) < 3:
        raise ValueError("form gates failed")
    published = [{k: s.get(k) for k in ("date", "opponent", "won", "bo", "source_url")}
                 for s in sorted(clean, key=lambda s: s["date"])[-12:]]
    if published != orig.get("samples"):
        raise ValueError("published form samples differ from the saved observations")
    return clean, binding


def refit_network(document: dict) -> dict:
    """Refit every saved edge/rating, without importing network_model."""
    saved_hash = document.get("evidence_sha256")
    unsigned = {k: v for k, v in document.items() if k != "evidence_sha256"}
    actual_hash = hashlib.sha256(json.dumps(unsigned, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if actual_hash != saved_hash:
        raise ValueError("network evidence hash mismatch")
    anchors = {int(k): v for k, v in (document.get("anchors") or {}).items()}
    adjacency: dict[int, list[tuple[int, float, float]]] = {}
    for edge in document.get("edges") or []:
        a, b, winner = int(edge["a"]), int(edge["b"]), edge["winner"]
        if winner not in (a, b):
            raise ValueError("network edge has an invalid winner")
        wa = 1.0 if winner == a else 0.0
        weight = float(edge["weight"])
        adjacency.setdefault(a, []).append((b, wa, weight))
        adjacency.setdefault(b, []).append((a, 1 - wa, weight))
    points = sorted(float(a["points"]) for a in anchors.values())
    center = points[len(points) // 2]
    rating = {team: float(anchors[team]["points"]) if team in anchors else center
              for team in adjacency}
    prior = dict(rating)
    for _ in range(60):
        moved = 0.0
        for team, games in adjacency.items():
            sd = 60.0 if team in anchors else 400.0
            gradient = -(rating[team] - prior[team]) / sd**2
            curvature = 1 / sd**2
            for opponent, won, weight in games:
                p = logistic(rating[team], rating[opponent])[0]
                gradient += weight * (won - p) * SCALE
                curvature += weight * p * (1 - p) * SCALE**2
            step = max(-120.0, min(120.0, gradient / curvature))
            rating[team] += step
            moved = max(moved, abs(step))
        if moved < 1e-4:
            break
    fitted = {}
    for team, games in adjacency.items():
        sd = 60.0 if team in anchors else 400.0
        curvature = 1 / sd**2
        for opponent, _won, weight in games:
            p = logistic(rating[team], rating[opponent])[0]
            curvature += weight * p * (1 - p) * SCALE**2
        fitted[str(team)] = {"points": round(rating[team], 1),
                             "se": round(1 / math.sqrt(curvature), 1),
                             "series": len(games), "anchored": team in anchors,
                             "anchor_points": anchors[team]["points"] if team in anchors else None}
    if fitted != document.get("ratings"):
        deltas = [abs(fitted[k]["points"] - document["ratings"][k]["points"]) for k in fitted]
        raise ValueError(f"network refit differs (max rating delta {max(deltas)})")
    return {"sha256": actual_hash, "series_refit": len(document["edges"]),
            "teams_refit": len(fitted), "anchors": len(anchors),
            "note": "The collector retains the complete derived edge list, not raw graph API responses; every edge retains a bo3.gg match URL."}


def close(actual: list[float], expected: list[float], tolerance: float = 5.1e-8) -> float:
    if len(actual) != 2 or any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in actual):
        raise ValueError("invalid probability pair")
    if abs(sum(actual) - 1) > 1e-7:
        raise ValueError("probabilities do not sum to one")
    delta = max(abs(a - b) for a, b in zip(actual, expected))
    if delta > tolerance:
        raise ValueError(f"arithmetic mismatch: published {actual}, recomputed {expected}, delta {delta}")
    return delta


def markdown(report: dict) -> str:
    s = report["summary"]
    lines = ["# E57 independent candidate replay", "",
             f"Generated: `{report['generated_at']}`", f"Candidate: `{report['candidate_ref']}`", "",
             "**This is a dated audit, not a deployment attestation.** Hotspawn and HLTV popularity were excluded.", "",
             f"- Live official lobby IDs: **{s['live_lobby_fixtures']}**; candidate active rows: **{s['candidate_active_fixtures']}**; exact ID-set match: **{str(s['exact_live_id_set_match']).lower()}**.",
             f"- Rows independently replayed: **{s['passed']}/{s['audited']}**; failures: **{s['failed']}**.",
             f"- Methods: **{s['methods']}**. Featured-method blanks resolved by the complete layer: **{', '.join(s['featured_unresolved_ids'])}**.",
             f"- Direct HLTV no-money-line reviews: **{s['hltv_direct_reviews']}**; official Valve file SHA-256: `{report['official_valve']['sha256']}`.", "",
             "| Fixture | Teams (Hotspawn order) | Start (UTC) | Pick | Both probabilities | Method | Independent replay | Source |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in report["rows"]:
        probs = " / ".join(f"{100*p:.4f}%" for p in row["probabilities"])
        lines.append(f"| {row['id']} | {' vs '.join(row['teams'])} | {row['starts_at']} | {row['pick']} | {probs} | {row['method']} | {row['arithmetic']['basis']}; Δ={row['arithmetic']['max_abs_delta']:.2e} | [source]({row['source_url']}) |")
    lines += ["", "## Limitations and irregularities", ""]
    lines += [f"- {x}" for x in report["limitations"]]
    lines += ["", "The separate `line-source-review.json` records the current EGW match-page line for Ground Zero–Off Chops and all reviewed placeholders; any integration through the reviewed-reference rung is reported explicitly above.", ""]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    root = args.candidate_root.resolve()
    session = args.session_dir.resolve()
    latest = load(root / "data/latest.json")
    complete = load(root / "data/origination.json")
    lobby = load(session / "live-lobby.json")
    hltv = load(session / "hltv-review.json")
    valve_path = session / "evidence/valve-standings-2026-10-05.md"
    valve_text = valve_path.read_text(encoding="utf-8")
    officials_list = valve_rows(valve_text)
    officials = unique_official(officials_list)
    raw_path = root / "data/evidence/hotspawn-fixtures.json"
    raw_bytes = raw_path.read_bytes()
    raw = json.loads(raw_bytes)
    raw_by_id = {str(row["id"]): row for row in raw}
    request = next(r for r in latest["requests"] if r.get("id") == "hotspawn-fixtures")
    # The collector hashes the original compact JSON response, then retains a
    # pretty-printed replay file. Re-serializing compactly reproduces that hash
    # for this endpoint while still checking every retained value.
    canonical_raw = json.dumps(raw, ensure_ascii=False, separators=(",", ":")).encode()
    if hashlib.sha256(canonical_raw).hexdigest() != request.get("response_sha256"):
        raise ValueError("Hotspawn evidence hash differs from its request manifest")
    active = [m for m in latest["matches"] if m.get("availability") != "past"]
    active_by_id = {str(m["id"]): m for m in active}
    active_ids = [str(m["id"]) for m in active]
    if len(active_ids) != len(set(active_ids)) or set(active_ids) != set(lobby["future_fixture_ids"]):
        raise ValueError("candidate active IDs differ from the first-hand current lobby list")
    if [str(m["id"]) for m in complete["matches"]] != active_ids:
        raise ValueError("complete-picks rows differ from the active inventory")
    bindings = load(root / "data/origination/evidence/live-bo3-bindings.json")
    network_cache = None
    rows, failures = [], []
    featured_unresolved = []
    for record in complete["matches"]:
        fid = str(record["id"])
        match = active_by_id[fid]
        source = raw_by_id[fid]
        orig = record.get("origination") or {}
        teams = [t["name"] for t in record["teams"]]
        errors = []
        try:
            if teams != [source["participants0_name"], source["participants1_name"]]:
                raise ValueError("team names/order differ from official Hotspawn response")
            if [str(t["id"]) for t in record["teams"]] != [str(source["participants0_id"]), str(source["participants1_id"])]:
                raise ValueError("team IDs differ from official Hotspawn response")
            start = datetime.fromtimestamp(int(source["scheduled_start_time"]) / 1000, UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
            if start != record["starts_at"] or start != match["starts_at"] or record.get("competition") != source["competition_name"]:
                raise ValueError("start/competition differs from official Hotspawn response")
            if not ((match.get("analysis") or {}).get("probabilities")):
                featured_unresolved.append(fid)
            method = orig.get("method")
            detail = ""
            extra = {}
            if method in ("market", "bookmaker", "reference"):
                expected, detail = money_replay(orig)
                if method == "reference":
                    detail = "reviewed aggregated decimal odds with proportional margin removal; hash/freshness checked separately"
            elif method == "model" and orig.get("family") == "network":
                inputs = orig["inputs"]
                expected = logistic(float(inputs[0]["points"]), float(inputs[1]["points"]))
                detail = "own network 400-scale logistic; complete saved graph independently refit"
                if network_cache is None:
                    network_cache = refit_network(load(root / "data/origination/evidence/live-bo3-graph.json"))
                extra["network"] = network_cache
                sd = math.sqrt(float(inputs[0]["se"])**2 + float(inputs[1]["se"])**2)
                if abs(sd - orig["rating_sd_diff"]) > 0.051:
                    raise ValueError("network uncertainty differs from inputs")
            elif method == "model" and orig.get("family") == "form":
                inputs = orig["inputs"]
                samples, binding = form_samples(record, orig, bindings, officials)
                fitted = fit_form(samples)
                fitted_side = next(side for side in inputs if side.get("fitted"))
                published_fit = dict(fitted_side["fitted"], points=fitted_side["points"])
                if fitted != published_fit:
                    raise ValueError(f"form refit differs: {fitted} vs {published_fit}")
                rd = max(min(400.0, 150.0 + 300.0 / math.sqrt(side["fitted"]["n"])) if side.get("fitted") else 75.0 for side in inputs)
                expected = expectation(float(inputs[0]["points"]), float(inputs[1]["points"]), rd)
                detail = f"independent {len(samples)}-series MAP refit; Valve logistic RD {rd:g}"
                extra["form_refit"] = fitted
                for side in inputs:
                    if not side.get("fitted"):
                        official = officials.get(key(side["name"]))
                        if official is None or official["points"] != side["points"]:
                            raise ValueError("official anchor in form row differs from Valve")
            elif method == "model" and len(orig.get("inputs") or []) == 2:
                inputs = orig["inputs"]
                rd = float(orig.get("rd_assumption") or 75)
                expected = expectation(float(inputs[0]["points"]), float(inputs[1]["points"]), rd)
                detail = f"official Valve inputs; Glicko expectation RD {rd:g}"
                verified = []
                for side in inputs:
                    candidates = [r for r in officials_list if r["complete"] and key(r["name"]) == key(side["name"])
                                  and r["standing"] == side.get("standing")]
                    if len(candidates) != 1:
                        raise ValueError(f"Valve input {side['name']} does not resolve to its published standing")
                    official = candidates[0]
                    if official["points"] != side["points"] or official["roster"] != side.get("roster"):
                        raise ValueError(f"Valve input {side['name']} points/roster differ")
                    verified.append({"standing": official["standing"], "points": official["points"], "name": official["name"]})
                extra["official_inputs"] = verified
                if orig.get("lineup_disambiguation"):
                    joins = orig["lineup_disambiguation"]
                    if len(joins) != 1 or joins[0].get("overlap") != 4 or joins[0].get("standing") != inputs[1].get("standing"):
                        raise ValueError("four-of-five roster-change join is not explicit")
                    extra["roster_join"] = joins[0]
            else:
                raise ValueError(f"no independent replay for method {method!r}")
            published = orig.get("probabilities")
            delta = close(published, expected)
            pick = record.get("pick_index")
            if pick not in (0, 1) or published[pick] <= published[1 - pick]:
                raise ValueError("directional pick is not the higher-probability side")
            fair = orig.get("fair_decimal")
            if fair != [round(1 / p, 3) for p in published]:
                raise ValueError("fair decimal line differs from probabilities")
            url = orig.get("source_url") or ""
            if not url.startswith("https://") or "hotspawn.com" in url:
                raise ValueError("probability source is missing or is Hotspawn popularity")
            rows.append({"id": fid, "teams": teams, "starts_at": record["starts_at"],
                         "pick": teams[pick], "pick_index": pick, "probabilities": published,
                         "method": method, "family": orig.get("family"), "label": orig.get("label"), "source_url": url,
                         "status": "pass", "arithmetic": {"basis": detail, "recomputed": expected,
                         "max_abs_delta": delta}, **extra})
        except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError) as exc:
            failures.append({"id": fid, "error": str(exc)})
            rows.append({"id": fid, "teams": teams, "starts_at": record.get("starts_at"),
                         "pick": None, "probabilities": orig.get("probabilities") or [],
                         "method": orig.get("method"), "source_url": orig.get("source_url"),
                         "status": "fail", "arithmetic": {"basis": "failed", "max_abs_delta": 0},
                         "error": str(exc)})
    counts = Counter(r["method"] for r in rows)
    limitations = [
        "The candidate replay proves arithmetic and retained-evidence consistency, not that a model probability is calibrated or a money line is still executable.",
        "HLTV text extraction does not expose a timezone for its display clock; UTC starts in this audit come from the official Hotspawn response, not a guessed HLTV timezone.",
    ]
    if any(r.get("family") == "network" for r in rows):
        limitations.insert(1, "The network model's raw graph API responses are not retained; the complete derived edge list is hash-checked and independently refit, with a source URL on every edge.")
    ground_zero = next((r for r in rows if r["id"] == "1082858"), {})
    if ground_zero.get("family") == "network":
        limitations.append("Ground Zero–Off Chops has a separately reviewed EGW match-page aggregate that differs from the candidate's network estimate; see line-source-review.json before integration.")
    elif ground_zero.get("method") == "reference":
        limitations.append("Ground Zero–Off Chops uses the separately reviewed, hash-checked EGW aggregate; it is third-party evidence and must expire after eight hours rather than being refreshed by assertion.")
    report = {
        "schema_version": 1, "session": "arena-e57df95b",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candidate_ref": args.candidate_ref, "candidate_root": str(root),
        "official_lobby": {"url": lobby["source_url"], "observed_at": lobby["observed_at"]},
        "official_hotspawn_response": {"url": request["url"], "observed_at": request["observed_at"],
                                       "sha256": request["response_sha256"], "inventory_rows": len(raw)},
        "official_valve": {"url": "https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md",
                           "sha256": hashlib.sha256(valve_path.read_bytes()).hexdigest(), "rows": len(officials_list)},
        "summary": {"live_lobby_fixtures": len(lobby["future_fixture_ids"]),
                    "candidate_active_fixtures": len(active), "exact_live_id_set_match": True,
                    "audited": len(rows), "passed": len(rows) - len(failures), "failed": len(failures),
                    "methods": dict(sorted(counts.items())), "featured_unresolved_ids": featured_unresolved,
                    "hltv_direct_reviews": len(hltv["fixtures"])},
        "rows": rows, "failures": failures,
        "limitations": limitations,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "candidate-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (args.output_dir / "candidate-audit.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    if failures:
        print(json.dumps(failures, indent=2))
        return 1
    print(f"PASS: {len(rows)} rows independently replayed; official lobby/API identities and all probability formulas match")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--candidate-ref", default="unknown")
    parser.add_argument("--session-dir", type=Path, default=Path("data/research/e57df95b"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/research/e57df95b"))
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
