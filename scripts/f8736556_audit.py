"""Session arena-f8736556 — public publication and pick-coverage audit.

This is a read-only audit of the site a reader actually receives. It does not
collect a replacement snapshot, calculate a probability, choose a pick or edit
an alias. It answers four separate questions and keeps them separate:

1. **Publication parity.** Do the plain public executive-summary page,
   ``data/latest.json`` and ``data/origination.json`` describe the same
   observation? Query-string and duplicate-slash reads are diagnostics only;
   they never make a stale plain URL pass.
2. **Every active row.** Does every non-past fixture in the published Hotspawn
   inventory appear exactly once in the complete-picks feed, with the same
   teams/start/source, two probabilities and an argmax pick, or an explicit
   unresolved research trail and limitation? Published probabilities are also
   replayed from the quote/input fields retained in that feed.
3. **Fresh Hotspawn identity check.** Has the first-party scheduled-fixture
   API changed since the published snapshot? Additions/removals are recorded,
   not silently treated as covered.
4. **Only the fallback gaps.** For rows that do not already carry an external
   money line, HLTV is probed first and esportsbook/aggregator surfaces second.
   An HTTP response or team mention is not a price. Only a fixture-bound,
   two-sided coefficient block is a lead, and even a lead is never converted
   into a probability here.

Usage:
    python -m scripts.f8736556_audit --out data/research/f8736556
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scripts.coverage_audit import audit_complete_picks
from scripts.domain import finite, no_vig, normalize_pair
from scripts.form_model import win_probability as form_win_probability
from scripts.network_model import win_probability as network_win_probability

UTC = timezone.utc
SESSION_ID = "f8736556"
BASE_URL = "https://buffedlizard55-lab.github.io/MaltaProj3/"
MONEY_METHODS = {"market", "bookmaker", "consensus", "reference"}
USER_AGENT = "MaltaProj3-publication-audit/f8736556"


def iso_z(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _unique(values: list[Any]) -> list[Any]:
    out: list[Any] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def extract_page_stamp(html_bytes: bytes) -> str | None:
    match = re.search(rb'data-snapshot-generated="([^"]+)"', html_bytes[:250_000])
    return match.group(1).decode("utf-8", "replace") if match else None


def publication_checks(page_stamp: str | None, latest: dict, complete: dict, now: datetime) -> list[dict]:
    """Plain-URL parity and freshness checks, with no cache-bypass credit."""

    def check(key: str, status: bool, detail: str) -> dict:
        return {"key": key, "status": "pass" if status else "fail", "detail": detail}

    generated = latest.get("generated_at")
    inventory_observed = latest.get("inventory_observed_at")
    generated_dt = parse_time(generated)
    age_hours = None if generated_dt is None else (now - generated_dt).total_seconds() / 3600
    return [
        check(
            "page_and_plain_latest_are_one_snapshot",
            bool(page_stamp and page_stamp == generated),
            f"executive-summary stamp={page_stamp!r}; plain data/latest.json generated_at={generated!r}",
        ),
        check(
            "complete_picks_cite_this_inventory_generation",
            complete.get("source_generated_at") == generated,
            "complete-picks source_generated_at="
            f"{complete.get('source_generated_at')!r}; inventory generated_at={generated!r}",
        ),
        check(
            "complete_picks_cite_this_inventory_observation",
            complete.get("source_snapshot_at") == inventory_observed,
            "complete-picks source_snapshot_at="
            f"{complete.get('source_snapshot_at')!r}; inventory observed_at={inventory_observed!r}",
        ),
        check(
            "published_inventory_is_inside_eight_hours",
            age_hours is not None and 0 <= age_hours <= 8,
            "inventory age at audit="
            + (f"{age_hours:.3f} hours" if age_hours is not None else "unparseable"),
        ),
        check(
            "collector_asserts_complete_inventory",
            latest.get("coverage_complete") is True,
            f"coverage_complete={latest.get('coverage_complete')!r}",
        ),
    ]


def _team_names(row: dict) -> list[Any]:
    return [team.get("name") for team in row.get("teams") or []]


def _is_external_line(origination: dict | None) -> bool:
    return bool(
        origination
        and (origination.get("method") in MONEY_METHODS or origination.get("family") == "relay")
    )


REPLAY_TOLERANCE = 2e-6


def _probability_pair(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    pair = [finite(item) for item in value]
    if any(item is None or not 0 < item < 1 for item in pair):
        return None
    return [float(item) for item in pair]


def _numeric_pair(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    pair = [finite(item) for item in value]
    if any(item is None for item in pair):
        return None
    return [float(item) for item in pair]


def _quote_replay_pair(quote: dict) -> tuple[list[float] | None, str, list[str]]:
    """Recompute one provider quote from raw odds/book fields when present."""
    stored = _probability_pair(quote.get("probabilities"))
    derived: list[float] | None = None
    basis = "stored provider probabilities (no raw odds/book fields published)"
    problems: list[str] = []

    odds = _numeric_pair(quote.get("odds"))
    bid = _numeric_pair(quote.get("bid"))
    ask = _numeric_pair(quote.get("ask"))
    try:
        if odds is not None and all(item > 1 for item in odds):
            derived = no_vig(odds)
            basis = "decimal odds, proportional no-vig"
        elif bid is not None and ask is not None:
            if any(not 0 < b <= a < 1 for b, a in zip(bid, ask)):
                problems.append("provider bid/ask book is crossed or outside (0, 1)")
            else:
                derived = normalize_pair(*[(b + a) / 2 for b, a in zip(bid, ask)])
                basis = "paired bid/ask midpoints, normalized"
    except ValueError as exc:
        problems.append(f"provider quote could not be replayed: {exc}")

    if derived is not None and stored is not None:
        difference = max(abs(a - b) for a, b in zip(derived, stored))
        if difference > REPLAY_TOLERANCE:
            problems.append(
                "provider stored probabilities differ from raw quote replay "
                f"by {difference:.8f}"
            )
    return derived or stored, basis, problems


def replay_probabilities(origination: dict | None) -> dict:
    """Replay a published pair from the quote/input fields in that same row.

    This deliberately does not use the live provider price at audit time:
    markets move. It proves the arithmetic from the evidence the publisher
    retained in the complete-picks document. Unknown future schemas are
    reported as unsupported rather than silently passed.
    """
    if not origination:
        return {
            "status": "not-applicable",
            "basis": "unresolved row has no probability to replay",
            "derived_probabilities": None,
            "max_abs_difference": None,
            "problems": [],
        }
    published = _probability_pair(origination.get("probabilities"))
    if published is None:
        return {
            "status": "fail",
            "basis": "published probabilities are not a valid pair",
            "derived_probabilities": None,
            "max_abs_difference": None,
            "problems": ["published probabilities are not two numbers in (0, 1)"],
        }

    quotes = [q for q in origination.get("quotes") or [] if isinstance(q, dict)]
    derived: list[float] | None = None
    basis = "unsupported published quote/input schema"
    problems: list[str] = []

    if origination.get("method") == "model":
        inputs = origination.get("inputs")
        if not isinstance(inputs, list) or len(inputs) != 2:
            for quote in quotes:
                if isinstance(quote.get("inputs"), list) and len(quote["inputs"]) == 2:
                    inputs = quote["inputs"]
                    break
        points = (
            [finite(row.get("points")) for row in inputs]
            if isinstance(inputs, list) and len(inputs) == 2
            else [None, None]
        )
        if all(point is not None for point in points):
            families = {origination.get("family"), *(q.get("family") for q in quotes)}
            g_value = finite(origination.get("g"))
            if g_value is None:
                g_value = next(
                    (finite(q.get("g")) for q in quotes if finite(q.get("g")) is not None),
                    None,
                )
            if "network" in families:
                p0 = network_win_probability(float(points[0]), float(points[1]))
                derived = normalize_pair(p0, 1 - p0)
                basis = "network-model published rating points, 400-point logistic"
            elif "form" in families:
                fitted_counts = [
                    finite((row.get("fitted") or {}).get("n"))
                    for row in inputs
                    if finite((row.get("fitted") or {}).get("n")) is not None
                ]
                if fitted_counts:
                    rd = min(400.0, 150.0 + 300.0 / math.sqrt(max(1.0, min(fitted_counts))))
                    p0 = form_win_probability(float(points[0]), float(points[1]), rd)
                    derived = normalize_pair(p0, 1 - p0)
                    basis = "results-form published rating points and fitted sample size"
                else:
                    problems.append("form-model row does not publish a fitted sample size")
            elif origination.get("source") == "HLTV world ranking":
                p0 = network_win_probability(float(points[0]), float(points[1]))
                derived = normalize_pair(p0, 1 - p0)
                basis = "HLTV published ranking points, 400-point logistic (g=1)"
            elif g_value is not None:
                p0 = 1 / (
                    1
                    + 10 ** (float(g_value) * (float(points[1]) - float(points[0])) / 400)
                )
                derived = normalize_pair(p0, 1 - p0)
                basis = "published official rating points and published g factor"
        if derived is None and quotes:
            quote_pair = _probability_pair(quotes[0].get("probabilities"))
            if quote_pair is not None:
                derived = quote_pair
                basis = "stored model quote probabilities (formula inputs incomplete)"
    elif len(quotes) == 2 and all(
        finite(q.get("midpoint")) is not None and "probabilities" not in q for q in quotes
    ):
        # Featured Polymarket schema: one side-level order-book quote per team.
        try:
            derived = normalize_pair(*(float(finite(q.get("midpoint"))) for q in quotes))
            basis = "two side-level order-book midpoints, normalized"
        except ValueError as exc:
            problems.append(f"side-level order-book replay failed: {exc}")
    elif quotes:
        quote_pairs: list[list[float]] = []
        quote_bases: list[str] = []
        for quote in quotes:
            pair, quote_basis, quote_problems = _quote_replay_pair(quote)
            problems.extend(
                f"{quote.get('provider') or 'provider'}: {problem}" for problem in quote_problems
            )
            if pair is not None:
                quote_pairs.append(pair)
                quote_bases.append(quote_basis)
        if quote_pairs:
            if len(quote_pairs) == 1:
                derived = quote_pairs[0]
                basis = quote_bases[0]
            else:
                p0 = median(pair[0] for pair in quote_pairs)
                derived = normalize_pair(p0, 1 - p0)
                basis = "median of provider first-team probabilities, normalized; providers: " + "; ".join(
                    _unique(quote_bases)
                )

    fair = origination.get("fair_decimal")
    if fair is not None:
        expected_fair = [round(1 / probability, 3) for probability in published]
        if fair != expected_fair:
            problems.append(f"fair_decimal {fair!r} differs from 1/probability {expected_fair!r}")

    if derived is None:
        return {
            "status": "unsupported",
            "basis": basis,
            "derived_probabilities": None,
            "max_abs_difference": None,
            "problems": problems,
        }
    difference = max(abs(a - b) for a, b in zip(derived, published))
    if difference > REPLAY_TOLERANCE:
        problems.append(
            f"published probabilities differ from retained-evidence replay by {difference:.8f}"
        )
    return {
        "status": "fail" if problems else "pass",
        "basis": basis,
        "derived_probabilities": derived,
        "max_abs_difference": difference,
        "problems": problems,
    }


def row_audit(latest: dict, complete: dict) -> dict:
    """Line-by-line inventory/complete-picks join; inputs are not mutated."""
    inventory = [m for m in latest.get("matches") or [] if m.get("availability") != "past"]
    complete_rows = complete.get("matches") or []
    by_id: dict[str, dict] = {}
    duplicate_ids: list[str] = []
    for row in complete_rows:
        row_id = str(row.get("id"))
        if row_id in by_id:
            duplicate_ids.append(row_id)
        else:
            by_id[row_id] = row

    coverage_problems = audit_complete_picks(complete)
    rows: list[dict] = []
    for match in sorted(inventory, key=lambda m: (str(m.get("starts_at") or ""), str(m.get("id")))):
        match_id = str(match.get("id"))
        completed = by_id.get(match_id)
        problems = [p for p in coverage_problems if p.startswith(f"fixture {match_id}:")]
        if completed is None:
            problems.append("active inventory fixture is missing from complete-picks feed")
            completed = {}
        else:
            identity_checks = {
                "teams": (_team_names(match), _team_names(completed)),
                "starts_at": (match.get("starts_at"), completed.get("starts_at")),
                "locks_at": (match.get("locks_at"), completed.get("locks_at")),
                "competition": (match.get("competition"), completed.get("competition")),
                "source_url": (match.get("source_url"), completed.get("source_url")),
            }
            for field, (expected, actual) in identity_checks.items():
                if expected != actual:
                    problems.append(f"{field} differs between inventory and complete-picks feed")

        origination = completed.get("origination") if isinstance(completed.get("origination"), dict) else None
        probability_replay = replay_probabilities(origination)
        if probability_replay["status"] == "fail":
            problems.extend(
                f"probability replay: {problem}" for problem in probability_replay["problems"]
            )
        pick_index = completed.get("pick_index") if completed.get("pick_index") in (0, 1) else None
        names = _team_names(match)
        state = (
            "external-line"
            if _is_external_line(origination)
            else "research-model"
            if origination
            else "unresolved"
        )
        rows.append(
            {
                "hotspawn_id": match_id,
                "teams": names,
                "competition": match.get("competition"),
                "starts_at": match.get("starts_at"),
                "locks_at": match.get("locks_at"),
                "availability_in_snapshot": match.get("availability"),
                "hotspawn_url": match.get("source_url"),
                "featured_method": completed.get("featured_method"),
                "state": state,
                "method": (origination or {}).get("method"),
                "method_label": (origination or {}).get("label"),
                "probabilities": (origination or {}).get("probabilities"),
                "pick": names[pick_index] if pick_index is not None and len(names) == 2 else None,
                "pick_index": pick_index,
                "source": (origination or {}).get("source"),
                "source_url": (origination or {}).get("source_url"),
                "observed_at": (origination or {}).get("observed_at"),
                "probability_replay": probability_replay,
                "limitations": _unique(
                    list(completed.get("limitations") or [])
                    + list((origination or {}).get("limitations") or [])
                ),
                "research_source_urls": _unique(
                    [item.get("source_url") for item in completed.get("research") or [] if item.get("source_url")]
                ),
                "problems": problems,
            }
        )

    expected_ids = {str(m.get("id")) for m in inventory}
    extra_ids = sorted(set(by_id) - expected_ids)
    global_problems = [
        p
        for p in coverage_problems
        if not any(p.startswith(f"fixture {row['hotspawn_id']}:") for row in rows)
    ]
    if duplicate_ids:
        global_problems.append("duplicate complete-pick IDs: " + ", ".join(sorted(set(duplicate_ids))))
    if extra_ids:
        global_problems.append("complete-picks feed contains fixtures absent from active inventory: " + ", ".join(extra_ids))

    return {
        "active_inventory_rows": len(rows),
        "complete_pick_rows": len(complete_rows),
        "directional_picks": sum(row["pick_index"] in (0, 1) for row in rows),
        "external_line_rows": sum(row["state"] == "external-line" for row in rows),
        "research_model_rows": sum(row["state"] == "research-model" for row in rows),
        "unresolved_rows": sum(row["state"] == "unresolved" for row in rows),
        "probability_replay_pass_rows": sum(
            row["probability_replay"]["status"] == "pass" for row in rows
        ),
        "probability_replay_unsupported_rows": sum(
            row["probability_replay"]["status"] == "unsupported" for row in rows
        ),
        "probability_replay_failed_rows": sum(
            row["probability_replay"]["status"] == "fail" for row in rows
        ),
        "rows_with_problems": sum(bool(row["problems"]) for row in rows),
        "extra_complete_pick_ids": extra_ids,
        "global_problems": global_problems,
        "rows": rows,
    }


def select_targets(audit: dict) -> list[dict]:
    """Only rows without an external money line enter fallback line research."""
    targets = []
    for row in audit["rows"]:
        if row["state"] == "external-line":
            continue
        targets.append(
            {
                "id": row["hotspawn_id"],
                "teams": row["teams"],
                "competition": row["competition"],
                "starts_at": row["starts_at"],
                "current_method": row["method"] or "unresolved",
                "current_label": row["method_label"] or "no pick — unresolved",
                "current_probabilities": row["probabilities"],
                "current_pick_index": row["pick_index"],
                "hotspawn_url": row["hotspawn_url"],
                "current_source_url": row["source_url"],
                "limitations": row["limitations"],
                "research_source_urls": row["research_source_urls"],
            }
        )
    return targets


def public_summary_checks(html_bytes: bytes, expected_ids: list[str]) -> dict:
    """Check the phone entry points in the public executive summary HTML."""
    soup = BeautifulSoup(html_bytes, "html.parser")
    glance_rows = soup.select("#picks-at-a-glance .glance-row")
    glance_ids = [str(row.get("data-glance-id")) for row in glance_rows]
    viewport = soup.select_one('meta[name="viewport"]')
    hrefs = [a.get("href") or "" for a in soup.select("a[href]")]
    mobile_hrefs = [a.get("href") or "" for a in soup.select(".mobile-nav a[href]")]
    unresolved = soup.select_one("#unresolved-register")
    return {
        "viewport": viewport.get("content") if viewport else None,
        "glance_row_count": len(glance_rows),
        "expected_active_count": len(expected_ids),
        "glance_ids_match_active_inventory": set(glance_ids) == set(expected_ids)
        and len(glance_ids) == len(set(glance_ids)),
        "missing_glance_ids": sorted(set(expected_ids) - set(glance_ids)),
        "extra_glance_ids": sorted(set(glance_ids) - set(expected_ids)),
        "links": {
            "all_match_picks": any(h.endswith("origination/#picks") for h in hrefs),
            "unresolved_register_on_summary": unresolved is not None,
            "unresolved_page": any(h.endswith("unresolved/") or h.endswith("origination/#unresolved") for h in hrefs),
            "methodology": any(h.endswith("methodology/") for h in hrefs),
            "coverage": any(h.endswith("coverage/") for h in hrefs),
            "flagged_for_review": any(h.endswith("review/") for h in hrefs),
        },
        "mobile_nav_links_to_all_picks": any(h.endswith("origination/#picks") for h in mobile_hrefs),
    }


def _observation(url: str, label: str, response: requests.Response, payload: Any | None = None) -> dict:
    body = response.content or b""
    result = {
        "label": label,
        "requested_url": url,
        "final_url": response.url,
        "observed_at": iso_z(datetime.now(UTC)),
        "http_status": response.status_code,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "cache_headers": {
            key: response.headers.get(key)
            for key in ("age", "cache-control", "etag", "last-modified", "x-cache")
            if response.headers.get(key) is not None
        },
    }
    if isinstance(payload, dict):
        result.update(
            generated_at=payload.get("generated_at"),
            inventory_observed_at=payload.get("inventory_observed_at"),
            source_generated_at=payload.get("source_generated_at"),
            source_snapshot_at=payload.get("source_snapshot_at"),
            counts=payload.get("counts"),
        )
    return result


def fetch_bytes(session: requests.Session, url: str, label: str, *, params: dict | None = None) -> tuple[bytes, dict]:
    response = session.get(url, params=params, timeout=(10, 45))
    response.raise_for_status()
    return response.content, _observation(str(response.url), label, response)


def fetch_json(
    session: requests.Session, url: str, label: str, *, params: dict | None = None
) -> tuple[Any, bytes, dict]:
    response = session.get(url, params=params, timeout=(10, 45))
    response.raise_for_status()
    payload = response.json()
    return payload, response.content, _observation(str(response.url), label, response, payload)


def fetch_official_inventory(session: requests.Session, latest: dict, out: Path) -> dict:
    api_url = next((m.get("source_api") for m in latest.get("matches") or [] if m.get("source_api")), None)
    if not api_url:
        return {"status": "unavailable", "finding": "published inventory carries no source_api URL"}
    try:
        payload, raw, observation = fetch_json(session, api_url, "Hotspawn scheduled-fixtures API")
        if not isinstance(payload, list) or not payload:
            raise ValueError("official inventory response is not a non-empty list")
        if any(not isinstance(m, dict) or not m.get("id") or m.get("sport_alias") != "cs2" for m in payload):
            raise ValueError("official inventory contains a row outside the CS2/id contract")
        official_ids = [str(m["id"]) for m in payload]
        if len(official_ids) != len(set(official_ids)):
            raise ValueError("official inventory contains duplicate IDs")
        (out / "official-inventory-response.json").write_bytes(raw if raw.endswith(b"\n") else raw + b"\n")
        published_ids = {str(m.get("id")) for m in latest.get("matches") or []}
        return {
            "status": "fetched",
            "observation": observation,
            "official_records": len(official_ids),
            "added_since_publication": sorted(set(official_ids) - published_ids),
            "removed_since_publication": sorted(published_ids - set(official_ids)),
            "note": (
                "This API read is later than the published snapshot. A delta is a refresh-timing "
                "finding to re-check after the next publisher run, not proof by itself that the "
                "collector dropped a fixture it had observed."
            ),
        }
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {
            "status": "unavailable",
            "api_url": api_url,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "finding": "fresh official inventory could not be independently fetched",
        }


def research_targets(targets: list[dict], timeout: int) -> dict:
    """HLTV first, then books/aggregators, using the repository's read-only probes."""
    if not targets:
        return {"pages": [], "pinnacle_guest_api": {}, "bo3": [], "per_fixture": [], "leads": []}

    base = importlib.import_module("scripts.3016b0c6_probe")
    extra = importlib.import_module("scripts.46ade650_probe")
    bo3probe = importlib.import_module("scripts.bo3_odds_probe")

    pages_to_probe: list[tuple[str, str]] = []
    seen_urls: set[str] = set()
    for name, url in list(base.PAGES) + list(extra.EXTRA_PAGES):
        if url not in seen_urls:
            pages_to_probe.append((name, url))
            seen_urls.add(url)

    teams = sorted({team for target in targets for team in target["teams"] if team})
    pages = [base.probe_page(name, url, teams, timeout=timeout) for name, url in pages_to_probe]
    teams_key = {
        frozenset({bo3probe.key(team) for team in target["teams"] if team}): " vs ".join(target["teams"])
        for target in targets
    }
    pinnacle = base.pinnacle_scan(teams_key)
    bo3 = base.bo3_scan(targets)

    per_fixture = []
    for target in targets:
        bound = next((row for row in bo3 if str(row.get("id")) == str(target["id"])), {})
        bet = bound.get("bet") or {}
        two_sided = bool(
            bet
            and (bet.get("team_1") or {}).get("coeff")
            and (bet.get("team_2") or {}).get("coeff")
        )
        pinnacle_hits = [
            hit
            for hit in pinnacle.get("fixture_hits") or []
            if hit.get("fixture") == " vs ".join(target["teams"])
        ]
        listing_pages = [
            page["name"]
            for page in pages
            if any(team in (page.get("teams_found") or []) for team in target["teams"] if team)
        ]
        verified_two_sided_lead = two_sided
        per_fixture.append(
            {
                **target,
                "bo3_bound_url": (bound.get("bound") or {}).get("url"),
                "bo3_bet_two_sided": two_sided,
                "bo3_bet": bet or None,
                "pinnacle_matchup": pinnacle_hits or None,
                "pages_listing_a_team": listing_pages,
                # A Pinnacle matchup listing without a replayed two-sided
                # moneyline is context, not a verified price lead.
                "money_line_lead": verified_two_sided_lead,
                "verdict": (
                    "LEAD ONLY: a fixture-bound two-sided relay coefficient was observed; the "
                    "reviewed first-party ladder must replay it before any pick changes"
                    if two_sided
                    else "CONTEXT ONLY: Pinnacle lists a matchup, but no two-sided series "
                    "moneyline was replayed by this audit"
                    if pinnacle_hits
                    else "No fixture-bound two-sided price was readable on the surfaces probed; "
                    "the published research estimate or blank limitation stands"
                ),
            }
        )
    return {
        "pages": pages,
        "pinnacle_guest_api": pinnacle,
        "bo3": bo3,
        "per_fixture": per_fixture,
        "leads": [row for row in per_fixture if row["money_line_lead"]],
    }


def _md_escape(value: Any) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def render_line_source_markdown(report: dict, research: dict) -> str:
    rows = research.get("per_fixture") or []
    lines = [
        "# Fixtures without a betting line — dated HLTV/esportsbook research (f8736556)",
        "",
        f"Observed {report['observed_at']} in {report['environment']}. This record covers only "
        f"{len(rows)} published fixture(s) that did not already carry an external money line. "
        "HLTV was probed first for identity/context, then esportsbook and aggregator surfaces. "
        "A reachable page, a team mention or a fan vote is not a price, and nothing here changes "
        "a published probability or pick.",
        "",
        "| Fixture | Starts (UTC) | Current basis | bo3.gg bound | Two-sided relay coefficients | Pinnacle matchup | Verdict |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                _md_escape(value)
                for value in [
                    f"{' vs '.join(row['teams'])} ({row['competition']})",
                    row["starts_at"],
                    row["current_label"],
                    row["bo3_bound_url"] or "—",
                    "yes — lead only" if row["bo3_bet_two_sided"] else "no",
                    "listed; price not replayed" if row["pinnacle_matchup"] else "no",
                    row["verdict"],
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Surfaces probed",
        "",
        "| Source | URL | HTTP/observation | Teams found | Challenge markers |",
        "| --- | --- | --- | --- | --- |",
    ]
    for page in research.get("pages") or []:
        lines.append(
            "| "
            + " | ".join(
                _md_escape(value)
                for value in [
                    page.get("name"),
                    page.get("url"),
                    page.get("status") or page.get("error") or "—",
                    ", ".join(page.get("teams_found") or []) or "—",
                    ", ".join(page.get("challenge_markers") or []) or "—",
                ]
            )
            + " |"
        )
    pinnacle = research.get("pinnacle_guest_api") or {}
    lines += [
        "",
        f"Pinnacle guest API: {pinnacle.get('matchups_seen', 0)} esports matchups observed; "
        f"{len(pinnacle.get('fixture_hits') or [])} target matchup listing(s). "
        + (f"Error: {pinnacle['error']}." if pinnacle.get("error") else "No fetch error recorded."),
        "",
        f"**Verified two-sided relay leads requiring first-party replay: {len(research.get('leads') or [])}.**",
        "",
        "Current picks remain on the live site: https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks",
    ]
    return "\n".join(lines) + "\n"


def render_audit_markdown(report: dict) -> str:
    publication = report["publication"]
    rows = report["row_audit"]
    lines = [
        "# Public Hotspawn CS2 publication and pick-coverage audit — 23 October 2026",
        "",
        f"Observed {report['observed_at']} ({report['environment']}). This is a dated audit, "
        "not a replacement picks feed. Use the live executive summary and complete picks list for current picks.",
        "",
        "## Where the updated picks are",
        "",
        "- Executive summary: https://buffedlizard55-lab.github.io/MaltaProj3/",
        "- Picks at a glance: https://buffedlizard55-lab.github.io/MaltaProj3/#picks-at-a-glance",
        "- Every match, both probabilities and sources: https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks",
        "- Unresolved picks and limitations inside the summary: https://buffedlizard55-lab.github.io/MaltaProj3/#unresolved-register",
        "- Dedicated unresolved page: https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/",
        "- Flagged for Review: https://buffedlizard55-lab.github.io/MaltaProj3/review/",
        "",
        "## Publication parity (plain public URLs)",
        "",
        "| Check | Result | Evidence |",
        "| --- | --- | --- |",
    ]
    for check_item in publication["checks"]:
        lines.append(
            f"| {_md_escape(check_item['key'])} | {_md_escape(check_item['status'])} | "
            f"{_md_escape(check_item['detail'])} |"
        )
    lines += [
        "",
        "Duplicate-slash/query reads are recorded in `audit.json` as cache diagnostics only. "
        "They do not turn a failing plain URL into a pass.",
        "",
        "## Coverage at the published snapshot",
        "",
        f"- Active inventory rows: **{rows['active_inventory_rows']}**",
        f"- Directional picks: **{rows['directional_picks']}**",
        f"- External-line rows: **{rows['external_line_rows']}**",
        f"- Research-model rows (not betting lines): **{rows['research_model_rows']}**",
        f"- Explicitly unresolved rows: **{rows['unresolved_rows']}**",
        f"- Rows with audit problems: **{rows['rows_with_problems']}**",
        "",
        "## Unresolved picks & limitations",
        "",
    ]
    unresolved = [row for row in rows["rows"] if row["state"] == "unresolved"]
    model_only = [row for row in rows["rows"] if row["state"] == "research-model"]
    if unresolved:
        lines += [
            "| Fixture | Probability | Pick | Published limitation | Research sources |",
            "| --- | --- | --- | --- | --- |",
        ]
        for row in unresolved:
            lines.append(
                "| "
                + " | ".join(
                    _md_escape(value)
                    for value in [
                        f"{row['hotspawn_id']}: {' vs '.join(row['teams'])}",
                        "blank — unverified",
                        "none",
                        " ".join(row["limitations"]) or "No limitation published — audit problem",
                        " ".join(row["research_source_urls"]) or "—",
                    ]
                )
                + " |"
            )
    else:
        lines.append("No fixture was explicitly unresolved in this published snapshot.")
    lines += [
        "",
        f"{len(model_only)} row(s) carry a research-model estimate rather than an external betting "
        "line. Those rows are separately listed in `line-source-research.md`; their percentages "
        "must not be described as bookmaker odds or calibrated market probabilities.",
        "",
        "## Every active row checked",
        "",
        "| Hotspawn ID | Fixture | Starts (UTC) | Basis | Probabilities | Pick | Source | Problems |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows["rows"]:
        probabilities = (
            " / ".join(f"{value * 100:.4f}%" for value in row["probabilities"])
            if row["probabilities"]
            else "blank — unverified"
        )
        lines.append(
            "| "
            + " | ".join(
                _md_escape(value)
                for value in [
                    row["hotspawn_id"],
                    " vs ".join(row["teams"]),
                    row["starts_at"],
                    row["method_label"] or row["state"],
                    probabilities,
                    row["pick"] or "none",
                    row["source_url"] or row["hotspawn_url"],
                    "; ".join(row["problems"]) or "none",
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Limitations",
        "",
        "- Hotspawn is used for fixture identity only; Hotspawn participation and HLTV fan votes are not probability inputs.",
        "- HLTV evidence can confirm identity, schedule, format or ranking context; it is not treated as a two-sided bookmaker price.",
        "- A book/aggregator outage, 403, challenge page or generic landing page proves only that this audit could not read a price there; it does not prove no market exists.",
        "- Research-model percentages are uncalibrated estimates, not official odds and not betting advice.",
        "- Fixtures and prices change. This dated audit must not replace the live four-hour publisher output.",
    ]
    if report.get("findings"):
        lines += ["", "## Findings", ""] + [f"- {finding}" for finding in report["findings"]]
    return "\n".join(lines) + "\n"


def build_flags(report: dict) -> list[dict]:
    rows = report["row_audit"]
    research = report["line_research"]
    unresolved_ids = [row["hotspawn_id"] for row in rows["rows"] if row["state"] == "unresolved"]
    model_ids = [row["hotspawn_id"] for row in rows["rows"] if row["state"] == "research-model"]
    publication_status = (
        "passed"
        if all(item["status"] == "pass" for item in report["publication"]["checks"])
        else "did not fully pass"
    )
    detail = (
        f"Independent public audit at {report['observed_at']}: plain-URL publication parity "
        f"{publication_status}; {rows['active_inventory_rows']} active published fixtures, "
        f"{rows['directional_picks']} directional picks, {rows['external_line_rows']} external-line, "
        f"{rows['research_model_rows']} research-model and {rows['unresolved_rows']} unresolved. "
        f"HLTV-first/esportsbook research covered {len(research.get('per_fixture') or [])} non-money-line "
        f"fixture(s) and found {len(research.get('leads') or [])} two-sided relay lead(s), which are not "
        "picks until the reviewed first-party ladder replays them. Research-model percentages are not "
        "bookmaker odds. Unresolved probabilities remain blank."
    )
    flags = [
        {
            "id": "f8736556-publication-and-coverage-audit-2026-10-23",
            "severity": "warning" if report["findings"] else "notice",
            "match_ids": unresolved_ids + model_ids,
            "title": "Dated plain-URL publication parity and every-fixture pick audit (23 October)",
            "detail": detail,
            "source_urls": [
                "https://buffedlizard55-lab.github.io/MaltaProj3/",
                "https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json",
                "https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json",
                "https://play.hotspawn.com/lobby",
                "https://www.hltv.org/matches",
                "https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/f8736556/audit.json",
                "https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/f8736556/line-source-research.md",
            ],
        }
    ]
    if report.get("pages_configuration", {}).get("build_type") == "legacy":
        flags.append(
            {
                "id": "f8736556-pages-legacy-mode-remains-2026-10-23",
                "severity": "notice",
                "match_ids": [],
                "title": "GitHub Pages remains in legacy mode; publisher ordering is the control",
                "detail": (
                    "The official GitHub Pages API read at 2026-10-23T09:43:46Z reported "
                    "build_type=legacy from main:/. The attempted change to build_type=workflow "
                    "returned HTTP 403, Resource not accessible by integration, so this session "
                    "does not claim Actions is the sole configured publisher. The repository "
                    "workflow waits for legacy builds, deploys the verified artifact last, syncs "
                    "rendered HTML—not deterministic data fixtures—into the root, waits again and "
                    "redeploys/verifies the artifact. A repository owner can remove this race in "
                    "Pages settings by selecting GitHub Actions as the source."
                ),
                "source_urls": [
                    "https://docs.github.com/en/rest/pages/pages#update-information-about-a-apiname-pages-site",
                    "https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/.github/workflows/pages.yml",
                    "https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/f8736556/pages-before.json",
                ],
            }
        )
    return flags


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/research/f8736556"))
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--skip-line-research", action="store_true")
    parser.add_argument("--strict", action="store_true", help="exit 1 if the audit records a finding")
    args = parser.parse_args(argv)

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/") + "/"
    now = datetime.now(UTC)
    session = requests.Session()
    session.headers.update(
        {"User-Agent": USER_AGENT, "Cache-Control": "no-cache", "Pragma": "no-cache"}
    )

    root_html, root_obs = fetch_bytes(session, base, "plain executive summary")
    page_stamp = extract_page_stamp(root_html)
    latest, latest_raw, latest_obs = fetch_json(
        session, urljoin(base, "data/latest.json"), "plain data/latest.json"
    )
    complete, complete_raw, complete_obs = fetch_json(
        session, urljoin(base, "data/origination.json"), "plain data/origination.json"
    )
    (out / "published-latest.plain.json").write_bytes(
        latest_raw if latest_raw.endswith(b"\n") else latest_raw + b"\n"
    )
    (out / "published-origination.plain.json").write_bytes(
        complete_raw if complete_raw.endswith(b"\n") else complete_raw + b"\n"
    )

    diagnostics: list[dict] = []
    diagnostic_specs = [
        ("data//latest.json diagnostic", urljoin(base, "data//latest.json"), None),
        ("data//origination.json diagnostic", urljoin(base, "data//origination.json"), None),
    ]
    if page_stamp:
        diagnostic_specs.append(
            (
                "data/latest.json?snapshot=<page stamp> diagnostic",
                urljoin(base, "data/latest.json"),
                {"snapshot": page_stamp},
            )
        )
    for label, url, params in diagnostic_specs:
        try:
            _, _, observation = fetch_json(session, url, label, params=params)
            diagnostics.append(observation)
        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            diagnostics.append({"label": label, "requested_url": url, "error": f"{type(exc).__name__}: {exc}"[:300]})

    checks = publication_checks(page_stamp, latest, complete, now)
    rows = row_audit(latest, complete)
    active_ids = [row["hotspawn_id"] for row in rows["rows"]]
    summary_checks = public_summary_checks(root_html, active_ids)
    official_inventory = fetch_official_inventory(session, latest, out)
    targets = select_targets(rows)
    line_research = (
        {"pages": [], "pinnacle_guest_api": {}, "bo3": [], "per_fixture": [], "leads": [], "skipped": True}
        if args.skip_line_research
        else research_targets(targets, timeout=args.timeout)
    )

    pages_config_path = out / "pages-before.json"
    pages_configuration: dict[str, Any] = {}
    if pages_config_path.exists():
        try:
            saved = json.loads(pages_config_path.read_text())
            pages_configuration = {
                "status": saved.get("status"),
                "build_type": saved.get("build_type"),
                "source": saved.get("source"),
                "html_url": saved.get("html_url"),
                "evidence": "pages-before.json",
                "workflow_update_attempt": {
                    "observed_at": "2026-10-23T09:43:46Z",
                    "requested_build_type": "workflow",
                    "http_status": 403,
                    "message": "Resource not accessible by integration",
                },
            }
        except (ValueError, TypeError) as exc:
            pages_configuration = {"error": f"{type(exc).__name__}: {exc}"[:200]}

    findings: list[str] = []
    findings.extend(
        f"Publication check failed: {item['key']} ({item['detail']})"
        for item in checks
        if item["status"] != "pass"
    )
    findings.extend(rows["global_problems"])
    findings.extend(
        f"Fixture {row['hotspawn_id']}: " + "; ".join(row["problems"])
        for row in rows["rows"]
        if row["problems"]
    )
    if not summary_checks["glance_ids_match_active_inventory"]:
        findings.append("Public executive-summary glance IDs do not exactly match active inventory IDs")
    if not summary_checks["mobile_nav_links_to_all_picks"]:
        findings.append("Public mobile navigation does not link to the complete picks list")
    if official_inventory.get("status") != "fetched":
        findings.append(str(official_inventory.get("finding") or official_inventory.get("error")))
    elif official_inventory.get("added_since_publication") or official_inventory.get("removed_since_publication"):
        findings.append(
            "Hotspawn official inventory changed after publication: "
            f"added={official_inventory['added_since_publication']}; "
            f"removed={official_inventory['removed_since_publication']}"
        )
    if args.skip_line_research and targets:
        findings.append("Fallback line research was explicitly skipped for this diagnostic run")

    report = {
        "schema_version": 1,
        "session": f"arena-{SESSION_ID}",
        "observed_at": iso_z(now),
        "environment": "github-actions-runner" if os.environ.get("GITHUB_ACTIONS") == "true" else "local checkout",
        "policy": (
            "Read-only. Plain public URLs are authoritative for parity. Hotspawn is fixture "
            "identity only. HLTV is identity/ranking context, not a price. No probability, pick, "
            "alias or 50/50 default is created by this audit."
        ),
        "publication": {
            "page_snapshot_generated": page_stamp,
            "observations": [root_obs, latest_obs, complete_obs],
            "cache_diagnostics_not_used_for_pass": diagnostics,
            "checks": checks,
        },
        "public_summary": summary_checks,
        "official_inventory_check": official_inventory,
        "row_audit": rows,
        "line_research": {
            "targets": targets,
            "pages": line_research.get("pages") or [],
            "pinnacle_guest_api": line_research.get("pinnacle_guest_api") or {},
            "bo3": line_research.get("bo3") or [],
            "per_fixture": line_research.get("per_fixture") or [],
            "leads": line_research.get("leads") or [],
            "skipped": bool(line_research.get("skipped")),
        },
        "pages_configuration": pages_configuration,
        "findings": findings,
        "sources": [
            {"name": "Published executive summary", "url": base},
            {"name": "Published inventory JSON", "url": urljoin(base, "data/latest.json")},
            {"name": "Published complete-picks JSON", "url": urljoin(base, "data/origination.json")},
            {"name": "Hotspawn lobby", "url": "https://play.hotspawn.com/lobby"},
            {"name": "HLTV matches", "url": "https://www.hltv.org/matches"},
            {
                "name": "GitHub Pages REST API documentation",
                "url": "https://docs.github.com/en/rest/pages/pages#update-information-about-a-apiname-pages-site",
            },
        ],
    }

    line_doc = {
        "schema_version": 1,
        "session": report["session"],
        "observed_at": report["observed_at"],
        "environment": report["environment"],
        "policy": report["policy"],
        "target_source": {
            "source_url": urljoin(base, "data/origination.json"),
            "source": "plain published complete-picks snapshot",
            "snapshot_generated_at": complete.get("generated_at"),
            "targets": len(targets),
            "active": rows["active_inventory_rows"],
        },
        "targets": targets,
        "pages": report["line_research"]["pages"],
        "pinnacle_guest_api": report["line_research"]["pinnacle_guest_api"],
        "bo3": report["line_research"]["bo3"],
        "per_fixture": report["line_research"]["per_fixture"],
        "leads": report["line_research"]["leads"],
    }
    (out / "line-source-research.json").write_text(
        json.dumps(line_doc, indent=2, ensure_ascii=False) + "\n"
    )
    (out / "line-source-research.md").write_text(render_line_source_markdown(report, line_doc))
    (out / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (out / "audit.md").write_text(render_audit_markdown(report))
    (out / "flags.json").write_text(json.dumps(build_flags(report), indent=2, ensure_ascii=False) + "\n")
    print(
        f"f8736556 audit: {rows['active_inventory_rows']} active, "
        f"{rows['directional_picks']} picks, {rows['external_line_rows']} external-line, "
        f"{rows['research_model_rows']} research-model, {rows['unresolved_rows']} unresolved; "
        f"findings={len(findings)}"
    )
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
