"""Near-time external lines — a documented, fail-closed binding class (session arena-7c0e457b).

The problem this solves
----------------------
The project's money ladder joins a provider row to a Hotspawn fixture only when
both team names match **and** the provider's start time is inside 60 seconds of
Hotspawn's. That rule is right: it stops a dashboard pairing a fixture with a
different match between the same two teams. But on 2026-10-23 this session
verified by hand that several low-tier CS2 fixtures stay unpriced *because of the
clock alone*, not because no book prices them:

* ``1079198`` Metizport vs BakS — Polymarket event ``1238705`` prices the same
  two teams in the same tournament, but says ``12:00Z`` while Hotspawn says
  ``11:00Z``;
* ``1081148`` Inner Circle Academy vs Spirit Academy — Unibet (Kambi) says
  ``11:10Z`` against Hotspawn's ``11:00Z``;
* ``1079655`` Nuclear TigeRES vs ILLYRIANS — the control case, where both
  sources say ``11:00Z`` and the row therefore already carries a market line.

What this module is allowed to do
---------------------------------
A row may be re-classified from ``time`` to ``near-time`` only when **all** of
these hold, checked here and re-checked at replay time:

1. ``pair_join`` matched both names through the reviewed alias registry — the
   same exact-name/competition-scoped identity test the strict ladder uses. A
   name that does not match is never a near-time candidate.
2. The absolute start difference is **greater than** the 60-second strict window
   (so this never competes with an exact row) and at most
   ``NEAR_MAX_DELTA_SEC`` (six hours).
3. Both timestamps fall on the **same UTC calendar date**. A postponement to the
   next day is not a clock discrepancy and stays unresolved.
4. The row is not in play, is inside the project's freshness window, and carries
   a two-sided book or a two-sided decimal pair — enforced downstream by the same
   ``market_estimate`` / ``bookmaker_estimate`` used for every other quote.

A near-time quote keeps its provider, its own observation time, its exact prices
and both timestamps in the published row, and it is placed *below* every
exact-bound money quote in the ladder. It is never described as an exact match.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.domain import name_key, timestamp

UTC = timezone.utc

#: Inside this window the strict ladder already binds the row.
STRICT_TOLERANCE_SEC = 60
#: Outside this window a row is a different fixture, not a clock discrepancy.
NEAR_MAX_DELTA_SEC = 6 * 3600
#: Published evidence class name.
NEAR_BINDING = 'near-time'
POLYMARKET_EVIDENCE = 'live-polymarket-near.json'


def same_utc_date(left: str, right: str) -> bool:
    a, b = timestamp(left), timestamp(right)
    return bool(a and b and a.astimezone(UTC).date() == b.astimezone(UTC).date())


def classify(row: dict, match: dict, join) -> tuple[str, float | None, list]:
    """Return ``('near'|'exact'|'reject', delta_seconds, alias_records)``.

    ``join(names, start)`` must be ``scripts.originate.pair_join`` already bound
    to the match and the reviewed alias registry, so this module can never drift
    from the project's single identity implementation. ``pair_join`` returns
    ``'names'`` when a team does not resolve, ``'time'`` when both names resolve
    but the clocks disagree and ``'matched'`` inside the 60-second window, which
    is exactly the three-way split this classification needs.
    """
    _, used, status = join(row.get('names') or [], row.get('start'))
    if status == 'names':
        return 'reject', None, []
    start, fixture_start = timestamp(row.get('start')), timestamp(match.get('starts_at'))
    if start is None or fixture_start is None:
        return 'reject', None, []
    delta = (start - fixture_start).total_seconds()
    if status == 'matched' or abs(delta) <= STRICT_TOLERANCE_SEC:
        return 'exact', delta, used
    if abs(delta) > NEAR_MAX_DELTA_SEC:
        return 'reject', delta, used
    if start.astimezone(UTC).date() != fixture_start.astimezone(UTC).date():
        return 'reject', delta, used
    return 'near', delta, used


def near_reason(row: dict, match: dict, delta: float) -> str:
    """Plain-language sentence published with a near-time quote."""
    provider = row.get('provider') or 'the provider'
    minutes = abs(delta) / 60
    shown = f'{minutes:.0f} minute' + ('' if round(minutes) == 1 else 's')
    return (f'{provider} lists this fixture at {row.get("start")} while Hotspawn lists '
            f'{match.get("starts_at")} — a {shown} difference on the same UTC date. Both team names match '
            f'exactly (or through the reviewed alias registry), so the price is used as a near-time '
            f'external line and the disagreement is printed on this row. It is never presented as an '
            f'exact-time match.')


def annotate(row: dict, match: dict, delta: float, *, provider: str | None = None) -> dict:
    """Copy a provider row into the near-time evidence shape."""
    out = dict(row)
    out['provider'] = provider or row.get('provider')
    out['near_time'] = True
    out['binding'] = NEAR_BINDING
    out['start_delta_sec'] = int(round(delta))
    out.setdefault('fixture_id', str(match.get('id')))
    out['hotspawn_start'] = match.get('starts_at')
    return out


def qualifies(row: dict, match: dict, join) -> dict | None:
    """The annotated row when it is a valid near-time candidate, else ``None``."""
    status, delta, used = classify(row, match, join)
    if status != 'near' or delta is None:
        return None
    out = annotate(row, match, delta)
    if used:
        out['aliases_used'] = used
    return out


# ---------------------------------------------------------------------------
# Polymarket near-time pass (its order books are only fetched for the fixtures
# the collector decided to price, so they need their own saving step).
# ---------------------------------------------------------------------------

def save_polymarket_near(evidence_dir: Path, document: dict) -> str:
    path = Path(evidence_dir) / POLYMARKET_EVIDENCE
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
    return path.name


def load_polymarket_near(evidence_dir: Path) -> dict | None:
    path = Path(evidence_dir) / POLYMARKET_EVIDENCE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except ValueError:
        return None


def polymarket_near_rows(evidence_dir: Path) -> list[dict]:
    """Rows rebuilt from the saved near-time Polymarket observations."""
    document = load_polymarket_near(evidence_dir)
    if not document:
        return []
    rows = []
    for record in document.get('events') or []:
        outcomes, bid, ask = record.get('outcomes'), record.get('book_bid'), record.get('book_ask')
        if not isinstance(outcomes, list) or len(outcomes) != 2:
            continue
        if not isinstance(bid, list) or not isinstance(ask, list) or len(bid) != 2 or len(ask) != 2:
            continue
        rows.append({
            'family': 'market', 'provider': 'Polymarket', 'names': list(outcomes),
            'start': record.get('game_start_time'), 'bid': list(bid), 'ask': list(ask),
            'event_id': str(record.get('event_id')), 'market_id': str(record.get('moneyline_market_id') or ''),
            'source_url': record.get('public_page') or record.get('source_url'),
            'api_url': record.get('source_url'),
            'observed_at': record.get('observed_at'),
            'evidence_file': f'data/origination/evidence/{POLYMARKET_EVIDENCE}',
            'near_time': True, 'binding': NEAR_BINDING,
            'start_delta_sec': record.get('start_delta_sec'),
            'fixture_id': str(record.get('fixture_id')) if record.get('fixture_id') else None,
        })
    return rows


def near_rows_for(match: dict, rows: list, join) -> list[dict]:
    """All valid near-time candidates for one fixture, provider-agnostic."""
    out = []
    for row in rows or []:
        fixture = row.get('fixture_id')
        if fixture is not None and str(fixture) != str(match.get('id')):
            continue
        candidate = qualifies(row, match, join)
        if candidate:
            out.append(candidate)
    return out


def describe(rows: list) -> list[str]:
    """Per-provider limitation sentences for the published row."""
    lines = []
    for row in rows:
        delta = row.get('start_delta_sec') or 0
        minutes = abs(delta) / 60
        shown = f'{minutes:.0f} min'
        lines.append(
            f"Near-time external line: {row.get('provider')} prices this fixture at a start "
            f'{shown} away from Hotspawn\'s published time ({row.get("hotspawn_start")} vs '
            f'{row.get("start")}). Both team names match; the price is real money on the same '
            'UTC date and the disagreement is shown, but the fixture identity rests on names and '
            'date rather than an exact clock match.')
    return lines


# ---------------------------------------------------------------------------
# Polymarket: the same series-winner contract as scripts.domain.polymarket_candidate
# with one substitution — the identity test is the near-time class above instead
# of the 60-second window. Every other guard is kept verbatim: active and
# prematch, a ``cs2-`` slug, ``moneyline`` scope, no map/prop words in the
# question, accepting orders, a future start and exactly two CLOB tokens.
# ---------------------------------------------------------------------------

import re  # noqa: E402  (module-local, used only by the selection below)

from scripts.domain import array  # noqa: E402


def polymarket_near_candidate(event: dict, match: dict, join, now: datetime) -> tuple[dict | None, str, float | None]:
    """Unique open Polymarket series-winner market for a near-time identity."""
    if event.get('closed') is not False or event.get('active') is not True or event.get('live') is True:
        return None, 'Event is not confirmed active and prematch', None
    if not str(event.get('slug', '')).startswith('cs2-'):
        return None, 'Not an identified CS2 fixture', None
    candidates, delta = [], None
    for market in event.get('markets', []):
        names = array(market.get('outcomes'))
        start = market.get('gameStartTime') or event.get('startTime')
        status, found, _ = classify({'names': names, 'start': start}, match, join)
        if status != 'near':
            continue
        scope = market.get('sportsMarketType') or (market.get('sports') or {}).get('sports_market_type')
        if scope != 'moneyline':
            continue
        if re.search(r'\b(map\s*\d|game\s*\d|handicap|spread|total|outright)\b', market.get('question', ''), re.I):
            continue
        if market.get('active') is not True or market.get('closed') is not False or market.get('acceptingOrders') is not True:
            continue
        if timestamp(start) is None or timestamp(start) <= now:
            continue
        if len(array(market.get('clobTokenIds'))) != 2:
            continue
        candidates.append(market)
        delta = found
    if len(candidates) != 1:
        return None, 'No unique open series-winner market with near-time teams and start', delta
    return candidates[0], '', delta
