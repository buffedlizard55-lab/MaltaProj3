"""Validate and render HLTV 5-player lineup disambiguation of duplicate Valve standings rows.

When `standings_global_2026_10_05.md` contains two rows with the same team name
(an active 2026 lineup and a legacy core), name-only lookup fails closed. This
module replays official HLTV match-page 5-player lineups against all candidate
rows in `data/evidence/valve-ratings.json` under Valve's >= 3/5 roster-core
rule:

- If both teams have a unique Valve row with >= 3/5 shared players, the pair's
  win probabilities are replayed via `scripts.model.win_probability` (RD=75).
- If either team has 0 rows with >= 3/5 shared players (e.g. unranked open
  qualifier rosters `LOS NINOS` and `Insiders`), probabilities and picks remain
  strictly `None` (unverified).
"""
from __future__ import annotations

import argparse
import json
import math
from html import escape
from pathlib import Path

from scripts.domain import VALVE_RD

DISAMBIGUATION_PATH = Path("data/research/f392649f/lineup-disambiguation.json")
TWC_VERIFICATION_PATH = Path("data/research/f392649f/twc-day3-verification.json")
VALVE_EVIDENCE_PATH = Path("data/evidence/valve-ratings.json")
MIN_CORE_OVERLAP = 3
RATING_DEVIATION = float(VALVE_RD)


def win_probability(ra: float, rb: float, rd: float = RATING_DEVIATION) -> tuple[float, float]:
    g = 1.0 / math.sqrt(1.0 + 3.0 * (math.log(10.0) / 400.0) ** 2 * (rd ** 2) / (math.pi ** 2))
    pa = 1.0 / (1.0 + 10.0 ** (g * (rb - ra) / 400.0))
    return round(pa, 8), round(1.0 - pa, 8)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _norm_player(handle: str) -> str:
    return handle.strip().lower()


def compute_overlap(hltv_lineup: list[str], valve_roster: list[str]) -> list[str]:
    valve_map = {_norm_player(p): p for p in valve_roster}
    shared = [p for p in hltv_lineup if _norm_player(p) in valve_map]
    return sorted(shared)


def load_disambiguation(
    path: Path = DISAMBIGUATION_PATH,
    valve_path: Path = VALVE_EVIDENCE_PATH,
) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    valve = json.loads(Path(valve_path).read_text(encoding="utf-8"))
    validate_disambiguation(data, valve)
    return data


def validate_disambiguation(data: dict, valve: dict) -> None:
    _require(data.get("schema_version") == 1, "Unsupported lineup-disambiguation schema")
    _require(bool(data.get("prepared_at")), "lineup-disambiguation missing prepared_at")
    window = data.get("research_window") or {}
    _require(bool(window.get("from")) and bool(window.get("to")), "lineup-disambiguation missing research_window")

    v_snap = data.get("valve_snapshot") or {}
    _require(v_snap.get("snapshot_date") == valve.get("snapshot_date"), "Valve snapshot_date mismatch")
    _require(v_snap.get("git_blob_sha") == valve.get("git_blob_sha"), "Valve git_blob_sha mismatch")
    _require(v_snap.get("min_core_overlap") == MIN_CORE_OVERLAP, "Valve min_core_overlap must be 3")

    rows_by_name: dict[str, list[dict]] = {}
    for row in valve.get("rows", []):
        rows_by_name.setdefault(row["name"].strip().lower(), []).append(row)

    fixtures = data.get("fixtures")
    _require(isinstance(fixtures, list) and len(fixtures) == 5, "Expected all 5 unresolved fixtures in lineup-disambiguation")

    resolved_count = 0
    unresolved_count = 0

    for fix in fixtures:
        _require(str(fix.get("hotspawn_url", "")).startswith("https://"), f"Invalid hotspawn_url on {fix.get('hotspawn_id')}")
        _require(str(fix.get("hltv_url", "")).startswith("https://"), f"Invalid hltv_url on {fix.get('hotspawn_id')}")
        sources = fix.get("sources") or []
        _require(len(sources) >= 3, f"Fixture {fix.get('hotspawn_id')} needs at least 3 official sources")
        for src in sources:
            _require(str(src.get("url", "")).startswith("https://"), f"Non-https source on {fix.get('hotspawn_id')}")
            _require(bool(src.get("observed_at")), f"Unstamped source on {fix.get('hotspawn_id')}")

        for side_key in ("team_a", "team_b"):
            team = fix.get(side_key) or {}
            lineup = team.get("hltv_match_lineup") or []
            _require(len(lineup) == 5, f"{fix['hotspawn_id']} {side_key} must list 5 HLTV match players")
            expected_rows = rows_by_name.get(team["name"].strip().lower(), [])
            candidates = team.get("valve_candidates") or []
            _require(
                len(candidates) == len(expected_rows),
                f"{fix['hotspawn_id']} {team['name']} candidate count mismatch against valve-ratings.json",
            )
            core_matches = []
            for cand, actual in zip(candidates, expected_rows):
                _require(cand["standing"] == actual["standing"], f"Standing mismatch for {team['name']}")
                _require(cand["points"] == actual["points"], f"Points mismatch for {team['name']}")
                _require(cand["roster"] == actual["roster"], f"Roster mismatch for {team['name']}")
                shared = compute_overlap(lineup, actual["roster"])
                _require(
                    cand["overlap_count"] == len(shared),
                    f"Overlap count mismatch for {team['name']} #{actual['standing']}",
                )
                _require(
                    cand["is_core_match"] is (len(shared) >= MIN_CORE_OVERLAP),
                    f"Core match boolean mismatch for {team['name']} #{actual['standing']}",
                )
                if cand["is_core_match"]:
                    core_matches.append(actual)

            if len(core_matches) == 1:
                _require(
                    team["selected_valve_standing"] == core_matches[0]["standing"],
                    f"Selected standing mismatch for {team['name']}",
                )
                _require(
                    team["selected_valve_points"] == core_matches[0]["points"],
                    f"Selected points mismatch for {team['name']}",
                )
            else:
                _require(
                    team["selected_valve_standing"] is None and team["selected_valve_points"] is None,
                    f"Unmatched team {team['name']} must keep selected_valve_* as None",
                )
                # Also verify no row under ANY name in valve-ratings.json shares >= 3/5 players
                any_core = [
                    r for r in valve.get("rows", [])
                    if len(compute_overlap(lineup, r.get("roster") or [])) >= MIN_CORE_OVERLAP
                ]
                _require(
                    len(any_core) == 0,
                    f"Unmatched team {team['name']} unexpectedly matched a Valve core under another name: {any_core}",
                )

        pts_a = fix["team_a"]["selected_valve_points"]
        pts_b = fix["team_b"]["selected_valve_points"]
        status = fix.get("disambiguation_status")

        if status == "resolved_by_hltv_lineup_core":
            resolved_count += 1
            _require(pts_a is not None and pts_b is not None, f"{fix['hotspawn_id']} missing selected points")
            p_a, p_b = win_probability(float(pts_a), float(pts_b), RATING_DEVIATION)
            probs = fix.get("probabilities")
            _require(isinstance(probs, list) and len(probs) == 2, f"{fix['hotspawn_id']} missing probabilities")
            _require(abs(probs[0] - p_a) < 1e-6 and abs(probs[1] - p_b) < 1e-6, f"{fix['hotspawn_id']} probability replay mismatch")
            _require(abs(sum(probs) - 1.0) < 1e-6, f"{fix['hotspawn_id']} probabilities do not sum to 1")
            expected_pick = fix["team_a"]["name"] if p_a >= p_b else fix["team_b"]["name"]
            _require(fix.get("recommended_pick") == expected_pick, f"{fix['hotspawn_id']} pick mismatch")
        elif status == "unresolved_opponent_unranked":
            unresolved_count += 1
            _require(
                fix.get("probabilities") is None
                and fix.get("fair_decimal_odds") is None
                and fix.get("recommended_pick") is None
                and fix.get("pick_index") is None,
                f"Unresolved fixture {fix['hotspawn_id']} must not publish a probability or pick",
            )
        else:
            raise ValueError(f"Unknown disambiguation_status: {status!r}")

    counts = data.get("counts") or {}
    _require(
        counts.get("evaluated") == len(fixtures)
        and counts.get("resolved_by_lineup_core") == resolved_count
        and counts.get("remaining_unresolved") == unresolved_count,
        "Disambiguation counts summary mismatch",
    )


def _format_candidate_summary(team: dict) -> str:
    lineup = ", ".join(escape(p) for p in team["hltv_match_lineup"])
    rank_bits = []
    if team.get("hltv_rank") is not None:
        rank_bits.append(f"HLTV #{int(team['hltv_rank'])}")
    else:
        rank_bits.append("HLTV Unranked")
    if team.get("hltv_vrs_rank") is not None:
        rank_bits.append(f"VRS #{int(team['hltv_vrs_rank'])}")
    else:
        rank_bits.append("VRS Unranked")
    cands = team.get("valve_candidates") or []
    if not cands:
        cand_html = '<span class="badge unverified">0 Valve rows · 0/5 core match across all 403 rosters</span>'
    else:
        parts = []
        for c in cands:
            tag = "core match" if c["is_core_match"] else "rejected legacy row"
            parts.append(
                f"#{int(c['standing'])} ({int(c['points'])} pts, {int(c['overlap_count'])}/5 {tag})"
            )
        cand_html = "; ".join(escape(p) for p in parts)
    return (
        f"<div><strong>{escape(team['name'])}</strong> ({escape(' · '.join(rank_bits))})<br>"
        f"<span class=\"muted\">HLTV 5: {lineup}</span><br>"
        f"<span class=\"muted\">Valve rows: {cand_html}</span></div>"
    )


def render_disambiguation_section(data: dict, prefix: str = "../") -> str:
    counts = data["counts"]
    v_snap = data["valve_snapshot"]
    rows_html = []
    for fix in data["fixtures"]:
        team_a = fix["team_a"]
        team_b = fix["team_b"]
        if fix["disambiguation_status"] == "resolved_by_hltv_lineup_core":
            p_a, p_b = fix["probabilities"]
            odds_a, odds_b = fix["fair_decimal_odds"]
            prob_cell = (
                f'<div><span class="badge verified">Lineup-core disambiguated</span></div>'
                f"<div><strong>{escape(team_a['name'])} {p_a * 100:.1f}%</strong> "
                f"<span class=\"muted\">(Fair line {odds_a:.3f} · #{team_a['selected_valve_standing']}, {team_a['selected_valve_points']} pts)</span></div>"
                f"<div><strong>{escape(team_b['name'])} {p_b * 100:.1f}%</strong> "
                f"<span class=\"muted\">(Fair line {odds_b:.3f} · #{team_b['selected_valve_standing']}, {team_b['selected_valve_points']} pts)</span></div>"
                f'<div><span class="pick-pill">Recommended pick: {escape(fix["recommended_pick"])}</span></div>'
            )
        else:
            prob_cell = (
                '<div><span class="badge unverified">Unverified · blank</span></div>'
                '<p class="muted">Opponent is unranked on both HLTV and Valve VRS (&lt; 3/5 core overlap across all 403 rosters) '
                'and has no bookmaker or exchange market. Left blank rather than guessed.</p>'
            )

        src_links = " · ".join(
            f'<a class="source-link" href="{escape(s["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
            f'{escape(s["source"])} ↗</a>'
            for s in fix["sources"]
        )
        lims = "".join(f"<li>{escape(item)}</li>" for item in fix.get("limitations") or [])
        rows_html.append(
            f'<tr id="disambig-{escape(fix["hotspawn_id"])}">'
            f"<td><strong>{escape(team_a['name'])} vs {escape(team_b['name'])}</strong><br>"
            f'<span class="muted">{escape(fix["competition"])} · {escape(fix["starts_at"])} · {escape(fix["best_of"].upper())}</span></td>'
            f"<td>{_format_candidate_summary(team_a)}{_format_candidate_summary(team_b)}</td>"
            f"<td>{prob_cell}</td>"
            f"<td><p>{escape(fix['rationale'])}</p><ul class=\"compact-list\">{lims}</ul><p>{src_links}</p></td>"
            f"</tr>"
        )

    return (
        '<section class="content-section" id="lineup-disambiguation">'
        '<div class="section-heading"><div>'
        '<p class="eyebrow">HLTV match-page 5-player core audit · Valve VRS 2026-10-05</p>'
        '<h2>Lineup-core disambiguation of the 5 unresolved low-tier fixtures</h2>'
        '</div>'
        f'<a class="source-link" href="{escape(prefix, quote=True)}data/research/f392649f/lineup-disambiguation.json">'
        'Disambiguation JSON ↗</a></div>'
        '<p class="section-lead">'
        f'The automated origination pipeline (<a class="internal-link" href="{escape(prefix, quote=True)}origination/#unresolved">26 / 31 resolved, 5 unresolved</a>) '
        'matches Valve standings by team name only and fails closed when a team name appears twice in '
        f'<a class="source-link" href="{escape(v_snap["source_url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
        f'standings_global_{escape(v_snap["snapshot_date"].replace("-", "_"))}.md ↗</a>. '
        f'Opening the five official HLTV match pages and comparing each published 5-player lineup against all 403 Valve rosters under Valve\'s &ge;3/5 core rule '
        f'uniquely resolves <strong>{counts["resolved_by_lineup_core"]} of the {counts["evaluated"]} fixtures</strong> '
        '(<strong>BET-M 72.7%</strong> over Just Players, <strong>aimclub 60.6%</strong> over BASEMENT BOYS, and <strong>ASTRAL 59.8%</strong> over Leo) '
        f'while proving why the remaining <strong>{counts["remaining_unresolved"]} fixtures</strong> '
        '(<strong>Procyon vs LOS NINOS</strong> and <strong>INFINITE vs Insiders</strong>) involve genuinely unranked opponents '
        'with 0 Valve core matches and must remain blank.'
        '</p>'
        '<div class="table-scroll"><table class="simple-table">'
        '<caption class="sr-only">HLTV 5-player lineup disambiguation of duplicate Valve rows and unranked low-tier CS2 fixtures</caption>'
        '<thead><tr>'
        '<th scope="col">Fixture &amp; schedule</th>'
        '<th scope="col">HLTV 5-player match lineup vs Valve candidate rows</th>'
        '<th scope="col">Disambiguated probability &amp; pick</th>'
        '<th scope="col">Verification rationale, limitations &amp; official sources</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table></div></section>'
    )


def load_twc_verification(
    path: Path = TWC_VERIFICATION_PATH,
    valve_path: Path = VALVE_EVIDENCE_PATH,
) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    valve = json.loads(Path(valve_path).read_text(encoding="utf-8"))
    validate_twc_verification(data, valve)
    return data


def validate_twc_verification(data: dict, valve: dict) -> None:
    _require(data.get("schema_version") == 1, "Unsupported twc-day3-verification schema")
    _require(bool(data.get("prepared_at")), "twc-day3-verification missing prepared_at")
    falcons = data.get("falcons_lineup_resolution") or {}
    lineup = falcons.get("verified_match_lineup") or []
    _require(len(lineup) == 5 and "karrigan" in lineup, "Falcons 5-player lineup must include karrigan")
    f_row = next((r for r in valve.get("rows", []) if r["standing"] == falcons.get("valve_standing")), None)
    _require(f_row is not None and f_row["points"] == falcons.get("valve_points"), "Falcons Valve standing mismatch")
    _require(len(compute_overlap(lineup, f_row["roster"])) == 5, "Falcons must match 5/5 against Valve #6")

    for group in ("day_one_complete", "day_two_complete"):
        series_list = data.get(group) or []
        _require(len(series_list) == 4, f"{group} must contain all 4 BO3 series")
        for s in series_list:
            _require(str(s.get("url", "")).startswith("https://www.hltv.org/matches/"), f"Invalid HLTV URL in {group}")
            _require(len(s.get("lineup_a") or []) == 5 and len(s.get("lineup_b") or []) == 5, f"Missing 5-player lineup in {s.get('hltv_match_id')}")
            a_score, b_score = (int(x) for x in s["score"].split("-"))
            maps = s.get("maps") or []
            _require(sum(1 for m in maps if m["a"] > m["b"]) == a_score, f"Map score A mismatch in {s.get('hltv_match_id')}")
            _require(sum(1 for m in maps if m["b"] > m["a"]) == b_score, f"Map score B mismatch in {s.get('hltv_match_id')}")

    deciders = data.get("day_three_deciders") or []
    _require(len(deciders) == 2, "Expected 2 Day-3 deciders")
    for dec in deciders:
        t_a, t_b = dec["team_a"], dec["team_b"]
        pm = dec.get("polymarket") or {}
        ks = dec.get("kalshi") or {}
        _require(str(pm.get("event_url", "")).startswith("https://polymarket.com/event/"), "Invalid Polymarket event_url")
        _require(str(ks.get("market_url", "")).startswith("https://kalshi.com/markets/"), "Invalid Kalshi market_url")
        pm_p = pm["probabilities"]
        ks_p = ks["normalized_probabilities"]
        cons = dec["consensus_probabilities"]
        _require(abs(pm_p[t_a] + pm_p[t_b] - 1.0) < 1e-6, "Polymarket probabilities must sum to 1")
        _require(abs(ks_p[t_a] + ks_p[t_b] - 1.0) < 1e-6, "Kalshi probabilities must sum to 1")
        _require(pm.get("moneyline_volume_usd", 0) > 1000, "Polymarket volume must be positive")
        _require(ks.get("volume_dollars", 0) > 100, "Kalshi volume must be positive")
        _require(abs(cons[t_a] - (pm_p[t_a] + ks_p[t_a]) / 2.0) < 1e-6, "Consensus probability A mismatch")
        _require(abs(cons[t_b] - (pm_p[t_b] + ks_p[t_b]) / 2.0) < 1e-6, "Consensus probability B mismatch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DISAMBIGUATION_PATH)
    parser.add_argument("--twc", type=Path, default=TWC_VERIFICATION_PATH)
    parser.add_argument("--valve", type=Path, default=VALVE_EVIDENCE_PATH)
    args = parser.parse_args()
    data = load_disambiguation(args.data, args.valve)
    twc = load_twc_verification(args.twc, args.valve)
    c = data["counts"]
    print(
        f"PASS: lineup-disambiguation validated: {c['evaluated']} evaluated, "
        f"{c['resolved_by_lineup_core']} resolved by >=3/5 HLTV lineup core, "
        f"{c['remaining_unresolved']} confirmed unranked; "
        f"{len(twc['day_one_complete']) + len(twc['day_two_complete'])} TWC series & "
        f"{len(twc['day_three_deciders'])} two-venue Day-3 deciders verified."
    )


if __name__ == "__main__":
    main()
