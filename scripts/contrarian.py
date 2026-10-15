"""Validate and derive the source-linked contrarian watch section.

The watch is deliberately separate from the primary pick engine. It is a small,
reviewable layer for recent-result context; it never changes a probability or
creates a missing line.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_HISTORICAL_SOURCES = {
    "https://www.hotspawn.com/matches/9z-vs-aurora-thunderpick-world-championship-2026-1080176",
    "https://www.hltv.org/matches/2399384/9z-vs-aurora-thunderpick-world-championship-2026",
    "https://www.hltv.org/news/45718/9z-beat-aurora-2-0-to-kick-off-twc-2026",
    "https://polymarket.com/market/cs2-9z-aur1-2026-10-14",
}
REQUIRED_ROSTER_SOURCE = "https://www.hltv.org/news/45082/official-aurora-complete-rebuild-with-kyxsan"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _source_list(value, label: str) -> list[str]:
    _require(isinstance(value, list) and value, f"{label} must contain source URLs")
    _require(all(isinstance(url, str) and _https(url) for url in value), f"{label} contains a non-HTTPS source")
    return value


def load_review(path: Path) -> dict:
    review = json.loads(Path(path).read_text())
    validate_review_shape(review)
    return review


def validate_review_shape(review: dict) -> None:
    _require(review.get("schema_version") == 1, "Unsupported contrarian review schema")
    _require(review.get("reviewed_on") == "2026-10-15", "Contrarian review date must be explicit")
    historical = review.get("historical_match") or {}
    _require(historical.get("id") == "9z-aurora-2026-10-14", "Unexpected historical match identity")
    _require(historical.get("teams") == ["9z", "Aurora"], "Historical teams are not exact")
    _require(historical.get("event") == "Thunderpick World Championship 2026", "Historical event is not exact")
    probabilities = historical.get("pre_match_probabilities")
    _require(isinstance(probabilities, list) and len(probabilities) == 2, "Historical probabilities must have two values")
    _require(all(isinstance(p, (int, float)) and 0 < p < 1 for p in probabilities), "Invalid historical probability")
    _require(abs(sum(probabilities) - 1) < 1e-8, "Historical probabilities do not sum to one")
    _require(historical.get("pre_match_pick") == "Aurora", "Historical primary pick must be explicit")
    result = historical.get("result") or {}
    _require(result.get("winner") == "9z" and result.get("series_score") == "2-0", "Historical result is not exact")
    maps = result.get("maps")
    _require(isinstance(maps, list) and len(maps) == 2, "Historical result must contain the two reported maps")
    _require(all(m.get("winner") == "9z" for m in maps), "Historical map winners are not exact")
    _require([m.get("map") for m in maps] == ["Inferno", "Nuke"], "Historical map order is not exact")
    _source_list(historical.get("source_urls"), "Historical match")
    _require(REQUIRED_HISTORICAL_SOURCES <= set(historical["source_urls"]), "Historical source trail is incomplete")

    roster = review.get("roster_context") or {}
    _require(roster.get("team") == "Aurora" and roster.get("reported_on") == "2026-07-08", "Roster context date/team is not exact")
    _require(roster.get("new_players") == ["Jimpphat", "kyxsan"], "Roster additions are not exact")
    _require(roster.get("new_coach") == "ash", "Roster coach context is not exact")
    _require(roster.get("replaced") == ["MAJ3R", "soulfly", "Fabre"], "Roster departures are not exact")
    _source_list(roster.get("source_urls"), "Roster context")
    _require(REQUIRED_ROSTER_SOURCE in roster["source_urls"], "Roster context lacks its HLTV source")

    profile = review.get("watch_profile") or {}
    _require(profile.get("team") == "9z" and profile.get("opponent") == "Falcons", "Watch profile identity is not exact")
    _require(profile.get("max_probability") == 0.25, "Watch threshold must remain conservative")
    _source_list(profile.get("source_urls"), "Watch profile")
    _require(isinstance(profile.get("limitations"), list) and profile["limitations"], "Watch limitations must be visible")
    policy = review.get("policy") or {}
    _require(policy.get("hotspawn_popularity_used") is False, "Hotspawn popularity must not be used")
    _require(policy.get("watch_is_a_pick") is False, "Contrarian watch cannot be represented as a pick")
    _require(policy.get("do_not_flip_primary_pick") is True, "Watch cannot flip the primary pick")


def _match_names(match: dict) -> set[str]:
    return {team.get("name") for team in match.get("teams", [])}


def derive_context(data: dict, review: dict) -> dict:
    """Return a dated historical review plus a current exact-pair watch, if any."""
    validate_review_shape(review)
    profile = review["watch_profile"]
    candidates = [
        match for match in data.get("matches", [])
        if match.get("availability") != "past"
        and _match_names(match) == {profile["team"], profile["opponent"]}
    ]
    current = None
    if len(candidates) == 1:
        match = candidates[0]
        analysis = match.get("analysis")
        if analysis and profile["team"] in [t.get("name") for t in match.get("teams", [])]:
            underdog_index = [t.get("name") for t in match["teams"]].index(profile["team"])
            probability = analysis["probabilities"][underdog_index]
            if probability <= profile["max_probability"]:
                current = {
                    "match_id": match["id"],
                    "teams": [t.get("name") for t in match["teams"]],
                    "starts_at": match.get("starts_at"),
                    "watch_team": profile["team"],
                    "watch_probability": probability,
                    "primary_pick": match["teams"][match["pick_index"]]["name"] if match.get("pick_index") is not None else None,
                    "primary_method": analysis.get("method"),
                    "source_urls": list(dict.fromkeys([match["source_url"], analysis["source_url"], *profile["source_urls"]])),
                    "status": "contrarian-watch",
                }
    if current is None:
        current = {
            "match_id": None,
            "teams": [],
            "starts_at": None,
            "watch_team": profile["team"],
            "watch_probability": None,
            "primary_pick": None,
            "primary_method": None,
            "source_urls": list(profile["source_urls"]),
            "status": "no-current-watch",
        }
    return {"historical": review["historical_match"], "roster": review["roster_context"], "profile": profile, "current": current, "policy": review["policy"]}


def validate_context(data: dict, context: dict) -> None:
    """Assert derived values still agree with the canonical current snapshot."""
    current = context["current"]
    if current["status"] != "contrarian-watch":
        return
    match = next((m for m in data["matches"] if m["id"] == current["match_id"]), None)
    _require(match is not None, "Contrarian watch references a missing current fixture")
    _require(match.get("analysis") is not None, "Contrarian watch has no canonical probability")
    _require(current["primary_pick"] == match["teams"][match["pick_index"]]["name"], "Watch changed the canonical pick")
    watch_index = [team.get("name") for team in match["teams"]].index(current["watch_team"])
    _require(abs(current["watch_probability"] - match["analysis"]["probabilities"][watch_index]) < 1e-8, "Watch probability differs from the canonical row")
    _require(current["watch_probability"] <= context["profile"]["max_probability"], "Watch exceeds its conservative threshold")
    _require(current["source_urls"], "Current watch lacks sources")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args()
    from scripts.validate import check_data

    canonical = check_data(args.data)
    review = load_review(args.data / "contrarian.json")
    context = derive_context(canonical, review)
    validate_context(canonical, context)
    print(json.dumps(context, indent=2))
