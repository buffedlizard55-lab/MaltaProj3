"""DE-2: reconcile the live Hotspawn lobby read against the stored fixture evidence.

Lobby entries were transcribed from the fetched lobby page (https://play.hotspawn.com/lobby),
each with its own View Match link ID and displayed start (Oct 15/16, UTC). Nothing is inferred:
a lobby entry is "matched" only when the same fixture ID exists in the saved API evidence with the
same competition and start time (minute precision). Output: coverage-reconciliation.json.
"""
import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "data/evidence/hotspawn-fixtures.json"
LATEST = ROOT / "data/latest.json"
OUT = ROOT / "data/research/de176356/coverage-reconciliation.json"

# (fixture_id, lobby_day_time_utc, competition, teams as displayed) read from the live lobby page.
LOBBY_UPCOMING = [
    ("1079440", "2026-10-15T10:00Z", "Stake Pulse Beat III", "MIBR vs BC.Game"),
    ("1079442", "2026-10-15T10:00Z", "Stake Pulse Beat III", "Heroic vs Envy"),
    ("1080280", "2026-10-15T10:00Z", "Elisa BreakOut Series #2", "ENCE vs BOJONG"),
    ("1080202", "2026-10-15T11:00Z", "Thunderpick World Championship 2026", "9z vs Falcons"),
    ("1080281", "2026-10-15T12:00Z", "Elisa BreakOut Series #2", "WROTBERRY vs ENCE"),
    ("1080203", "2026-10-15T13:30Z", "Thunderpick World Championship 2026", "PARIVISION vs BetBoom"),
    ("1080282", "2026-10-15T14:00Z", "Elisa BreakOut Series #2", "EAC vs BOJONG"),
    ("1080204", "2026-10-15T16:00Z", "Thunderpick World Championship 2026", "Legacy vs FURIA"),
    ("1080283", "2026-10-15T16:00Z", "Elisa BreakOut Series #2", "WROTBERRY vs BOJONG"),
    ("1080284", "2026-10-15T18:00Z", "Elisa BreakOut Series #2", "EAC vs ENCE"),
    ("1080285", "2026-10-16T08:00Z", "Elisa BreakOut Series #2", "Voca vs Phantom"),
    ("1080286", "2026-10-16T10:00Z", "Elisa BreakOut Series #2", "HAVU vs RoundsGG"),
    ("1080287", "2026-10-16T12:00Z", "Elisa BreakOut Series #2", "Voca vs HAVU"),
    ("1081120", "2026-10-16T14:00Z", "CCT Europe 2026 Series #12 Play-In", "mellren vs Privateer"),
    ("1080288", "2026-10-16T14:00Z", "Elisa BreakOut Series #2", "Phantom vs RoundsGG"),
    ("1080289", "2026-10-16T16:00Z", "Elisa BreakOut Series #2", "RoundsGG vs Voca"),
    ("1080290", "2026-10-16T18:00Z", "Elisa BreakOut Series #2", "Phantom vs HAVU"),
]
# Lobby per-tournament filter counts as displayed (sum 78; header says "72 matches this week").
LOBBY_TOURNAMENT_COUNTS = {
    "CCT Europe 2026 Challengers #4": 8, "CCT Europe 2026 Series #11": 1,
    "CCT Europe 2026 Series #12 Play-In": 1, "CCT South America 2026 Series #3": 8,
    "CCT South America 2026 Series #7": 1, "DACH CS Masters Season 5": 1,
    "DraculaN Season 7": 6, "Elisa BreakOut Series #2": 11,
    "European Pro League Series 8": 1, "European Pro League Series 8 Play-In": 6,
    "LG UltraGear Tournament 2026": 1, "Rainhas do Clutch 2026": 2,
    "Stake Pulse Beat III": 2, "Svenska CS-Ligan 2026": 6,
    "Thunderpick World Championship 2026": 3,
    "Thunderpick World Championship 2026: South American Series #1": 8,
    "Urban Riga Open #5": 12,
}
LOBBY_HEADER_MATCHES = 72
LOBBY_TIER_ALL = 78


def utc_minute(ms: str) -> str:
    t = dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%MZ")


def main() -> None:
    fx = {str(x["id"]): x for x in json.loads(EVIDENCE.read_text())}
    latest = json.loads(LATEST.read_text())
    inv_future = {m["id"] for m in latest["matches"] if m.get("availability") != "past" and m.get("status_bucket", "upcoming") != "past"}

    rows = []
    for fid, lobby_time, comp, teams in LOBBY_UPCOMING:
        rec = fx.get(fid)
        if rec is None:
            rows.append({"fixture_id": fid, "lobby_time_utc": lobby_time, "lobby_teams": teams,
                         "status": "missing_from_fixture_evidence"})
            continue
        api_time = utc_minute(rec["scheduled_start_time"])
        api_teams = f'{rec["participants0_name"]} vs {rec["participants1_name"]}'
        same_comp = rec["competition_name"] == comp
        same_time = api_time == lobby_time
        rows.append({
            "fixture_id": fid,
            "lobby_time_utc": lobby_time,
            "api_start_utc": api_time,
            "lobby_teams": teams,
            "api_teams": api_teams,
            "competition_match": same_comp,
            "time_match": same_time,
            "status": "matched" if (same_comp and same_time) else "mismatch",
            "source_url": f"https://play.hotspawn.com/lobby#fixture-{fid}",
        })

    comp_counts = {}
    for rec in fx.values():
        comp_counts[rec["competition_name"]] = comp_counts.get(rec["competition_name"], 0) + 1
    diff = {}
    for name in sorted(set(comp_counts) | set(LOBBY_TOURNAMENT_COUNTS)):
        a, b = comp_counts.get(name, 0), LOBBY_TOURNAMENT_COUNTS.get(name, 0)
        if a != b:
            diff[name] = {"fixture_evidence": a, "lobby_filter": b}

    not_in_lobby = sorted(
        (fid for fid in fx if fid not in {r[0] for r in LOBBY_UPCOMING}),
        key=lambda f: fx[f]["scheduled_start_time"],
    )
    summary = {
        "generated_for_observation": "lobby read ~2026-10-15T10:05Z; fixture evidence observed 2026-10-15T08:36:04Z",
        "lobby_upcoming_entries": len(LOBBY_UPCOMING),
        "lobby_upcoming_matched_by_id_time_competition": sum(r["status"] == "matched" for r in rows),
        "fixture_evidence_records": len(fx),
        "fixture_evidence_unique_ids": len({str(x["id"]) for x in fx.values()}),
        "lobby_tournament_filter_sum": sum(LOBBY_TOURNAMENT_COUNTS.values()),
        "lobby_header_matches_this_week": LOBBY_HEADER_MATCHES,
        "lobby_tier_all_count": LOBBY_TIER_ALL,
        "tournament_count_differences": diff,
        "records_not_on_lobby_list": [
            {"fixture_id": f, "competition": fx[f]["competition_name"],
             "start_utc": utc_minute(fx[f]["scheduled_start_time"]),
             "teams": f'{fx[f]["participants0_name"]} vs {fx[f]["participants1_name"]}'}
            for f in not_in_lobby
        ],
        "inventory_future_ids_in_latest_json": len(inv_future),
    }
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
