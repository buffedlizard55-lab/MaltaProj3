"""Read two-way series moneylines from Pinnacle's public guest board.

Why Pinnacle
------------
Session arena-be84edde's provider probe found that Pinnacle publishes a public
"guest" market board that is reachable from the GitHub runner and that lists
Counter-Strike 2 — including the Thunderpick World Championship playoffs, which
no other provider in the ladder had priced for the final day. Pinnacle is a
first-party bookmaker: the price is the book's own, not an aggregation.

Scope and safety
----------------
* Read-only GETs against the same public endpoints Pinnacle's own site calls.
* Fail closed: any transport, schema or validation problem yields ``None`` and
  a reason string. No price is inferred, interpolated or carried over.
* Only a two-way moneyline on the *series* is accepted. Map markets, totals,
  handicaps, correct-score markets, "Yes/No" specials and alternate lines are
  rejected by construction (they live on different matchups or periods and are
  filtered out explicitly).
* American prices are converted to decimal, then to probabilities with the
  same proportional-vig removal the rest of the repository uses.
* A caller must supply exact team names and a start time; nothing fuzzy is
  attempted here. Name joining is the caller's job (see
  ``data/origination/aliases.json``).

Nothing in this module writes a probability into a published feed. It returns a
quote; the caller decides whether the quote is allowed to become a pick.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

BASE = 'https://guest.api.arcadia.pinnacle.com/0.1'
SPORT_ESPORTS = 12  # confirmed by enumeration: 12 = Esports (29 is Soccer).
LEAGUE_CS2_PREFIX = 'CS2'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
SOURCE_URL = 'https://www.pinnacle.com/en/esports/counter-strike-2'
API_URL = f'{BASE}/sports/{SPORT_ESPORTS}/matchups'


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*',
                                               'Accept-Encoding': 'identity'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def american_to_decimal(price: float) -> float:
    """Pinnacle publishes American prices; the repository works in decimals."""
    price = float(price)
    if price > 0:
        return 1.0 + price / 100.0
    if price < 0:
        return 1.0 + 100.0 / abs(price)
    raise ValueError('a zero American price carries no probability')


def probabilities(dec_a: float, dec_b: float) -> tuple[float, float]:
    """Remove the overround proportionally, exactly as scripts/originate.py does."""
    ia, ib = 1.0 / dec_a, 1.0 / dec_b
    total = ia + ib
    if total <= 0:
        raise ValueError('non-positive implied probabilities')
    return ia / total, ib / total


def _norm(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (value or '').lower())


# Pinnacle's own board shortens a few organisation names. Only these reviewed
# display-name equivalences are applied, and only after the exact name has been
# tried first, so an unreviewed shortening can never silently join a fixture.
# Evidence: on 2026-10-18 the "CS2 - TP World Championship" league listed
# "FURIA" against "BB Team" for the 15:00Z grand final, which HLTV
# (https://www.hltv.org/matches/2399417/furia-vs-betboom-thunderpick-world-championship-2026)
# publishes as FURIA vs BETBOOM.
NAME_EQUIVALENCES = {
    'betboom': 'bb team',
    'betboomteam': 'bb team',
    'betboom team': 'bb team',
}


def _candidates(name: str) -> list[str]:
    base = _norm(name)
    alias = NAME_EQUIVALENCES.get(base)
    return [base, alias] if alias else [base]


def fetch_matchups(sport: int = SPORT_ESPORTS) -> list[dict[str, Any]]:
    import json
    raw = _get(f'{BASE}/sports/{sport}/matchups')
    return json.loads(raw.decode('utf-8', 'replace'))


def fetch_straight(league_id: int) -> list[dict[str, Any]]:
    import json
    raw = _get(f'{BASE}/leagues/{league_id}/markets/straight')
    return json.loads(raw.decode('utf-8', 'replace'))


def _resolve_participants(matchup: dict, row: dict) -> list[str] | None:
    """Map a moneyline's two prices onto the two team names on the matchup.

    Pinnacle publishes prices either keyed by ``participantId`` or by
    ``designation`` (home/away). Either way the array is ordered the same way
    as the matchup's own participant list, so ordering is the fallback and the
    explicit key is preferred. Returns ``None`` when the row cannot be tied to
    exactly the two teams on the matchup — that rejects map markets and
    "Yes/No" specials, which live on their own matchups.
    """
    participants = list(matchup.get('participants') or [])
    if len(participants) != 2:
        return None
    names = [p.get('name') for p in participants]
    # Esports participants on this board are published without an id. Building the
    # map unconditionally would collapse both prices onto the last name (observed
    # 2026-10-18: both sides of FURIA vs BB Team resolved to "BB Team"), so a
    # missing id is never used as a key.
    by_id = {p['id']: p.get('name') for p in participants if p.get('id') is not None}
    prices = row.get('prices') or []
    if len(prices) != 2:
        return None
    resolved = []
    for index, price in enumerate(prices):
        name = by_id.get(price.get('participantId'))
        if name is None and price.get('designation') in ('home', 'away'):
            name = names[0] if price['designation'] == 'home' else names[1]
        if name is None:
            # Only fall back to ordering when neither price carries a key at all.
            if any(p.get('participantId') is not None or p.get('designation') for p in prices):
                return None
            name = names[index]
        resolved.append(name)
    if sorted(resolved) != sorted(names):
        return None
    return resolved


def series_moneyline(matchup: dict, markets: list[dict]) -> dict | None:
    """Return the two-way series price for one matchup, or None.

    On this board the series moneyline sits on the **lowest** period and the
    higher periods price the individual maps. Evidence from the 2026-10-18
    probe: for FURIA vs BB Team the board printed the same pair (-186 / +151)
    on periods 1, 2 and 3 — identical per-map prices — while period 0 printed a
    different, tighter pair (-286 / +226) that matches the independent
    aggregator quotes for the series. The same pattern held for Aurora vs
    Falcons and for the CCT Europe Challengers fixture. Only the lowest period
    is therefore taken, and only when it prices exactly the two teams.
    """
    participants = list(matchup.get('participants') or [])
    if len(participants) != 2:
        return None
    candidates = []
    for row in markets or []:
        if row.get('matchupId') != matchup.get('id'):
            continue
        if row.get('type') != 'moneyline':
            continue
        if row.get('isAlternate'):
            continue
        if row.get('status') not in (None, 'open'):
            continue
        period = row.get('period')
        if not isinstance(period, int) or period < 0:
            continue
        if _resolve_participants(matchup, row) is None:
            continue
        candidates.append((period, row))
    if not candidates:
        return None
    period, row = min(candidates, key=lambda item: item[0])
    prices = row['prices']
    try:
        decs = [american_to_decimal(p['price']) for p in prices]
        pa, pb = probabilities(decs[0], decs[1])
    except (ValueError, KeyError, TypeError):
        return None
    return {
        'period': period,
        'participants': _resolve_participants(matchup, row),
        'american': [prices[0]['price'], prices[1]['price']],
        'decimal': [round(decs[0], 4), round(decs[1], 4)],
        'probabilities': [round(pa, 6), round(pb, 6)],
        'cutoff_at': row.get('cutoffAt'),
        'matchup_id': matchup.get('id'),
        'period_note': ('Lowest period on the board. Higher periods repeat identical '
                        'per-map prices and are excluded.'),
    }


def quote(team_a: str, team_b: str, starts_at: str | None, now: datetime | None = None,
          tolerance_minutes: int = 60):
    """Look up one fixture on the board. Returns (quote, reason)."""
    now = now or datetime.now(timezone.utc)
    # Validate before any network call: a fixture that cannot be identified
    # exactly must never reach the board.
    wanted_a, wanted_b = _norm(team_a), _norm(team_b)
    if not wanted_a or not wanted_b or wanted_a == wanted_b:
        return None, 'A unique two-team fixture is required.'
    try:
        matchups = fetch_matchups()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
        return None, f'Pinnacle guest board unavailable: {type(exc).__name__}: {exc}'
    target, matched = None, None
    aliased = {_norm(NAME_EQUIVALENCES.get(wanted_a, wanted_a)),
               _norm(NAME_EQUIVALENCES.get(wanted_b, wanted_b))}
    for wanted in ({wanted_a, wanted_b}, aliased):
        if wanted_a in wanted and wanted_b in wanted and len(wanted) != 2:
            continue
        for m in matchups:
            names = {_norm(p.get('name')) for p in (m.get('participants') or [])}
            if names == wanted and (m.get('league') or {}).get('name', '').startswith(LEAGUE_CS2_PREFIX):
                target, matched = m, wanted
                break
        if target is not None:
            break
    if target is None:
        return None, 'No Pinnacle CS2 matchup lists exactly these two teams.'
    if m_start := target.get('startTime'):
        if starts_at:
            try:
                board = datetime.fromisoformat(str(m_start).replace('Z', '+00:00'))
                want = datetime.fromisoformat(str(starts_at).replace('Z', '+00:00'))
                if abs((board - want).total_seconds()) > tolerance_minutes * 60:
                    return None, ('Pinnacle lists this pairing at a different start time '
                                  f'({m_start} vs {starts_at}).')
            except ValueError:
                return None, 'Start times could not be parsed for comparison.'
        if datetime.fromisoformat(str(m_start).replace('Z', '+00:00')) <= now:
            return None, 'Pinnacle lists this matchup as already started; prematch only.'
    if target.get('isLive'):
        return None, 'Pinnacle lists this matchup as live; prematch only.'
    league_id = (target.get('league') or {}).get('id')
    try:
        markets = fetch_straight(league_id)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
        return None, f'Pinnacle market read failed: {type(exc).__name__}: {exc}'
    found = series_moneyline(target, markets)
    if not found:
        return None, 'No two-way series moneyline is open on Pinnacle for this matchup.'
    found.update({
        'provider': 'Pinnacle (first-party bookmaker)',
        'source_url': SOURCE_URL,
        'api_url': API_URL,
        'league': (target.get('league') or {}).get('name'),
        'best_of': target.get('bestOfX'),
        'observed_at': now.replace(microsecond=0).isoformat(),
    })
    return found, None


def describe(limit_leagues: int = 6) -> dict:
    """Dump the CS2 coverage of the board. Diagnostic only; never a price input."""
    matchups = fetch_matchups()
    cs2 = [m for m in matchups
           if ((m.get('league') or {}).get('name') or '').startswith(LEAGUE_CS2_PREFIX)]
    out = {'leagues': {}, 'matchups': []}
    for m in cs2:
        league = (m.get('league') or {}).get('name')
        lid = (m.get('league') or {}).get('id')
        out['leagues'][league] = lid
        out['matchups'].append({
            'id': m.get('id'), 'league': league,
            'participants': [p.get('name') for p in (m.get('participants') or [])],
            'startTime': m.get('startTime'), 'bestOfX': m.get('bestOfX'),
            'isLive': m.get('isLive'), 'state': m.get('state'),
        })
    for league, lid in list(out['leagues'].items())[:limit_leagues]:
        try:
            markets = fetch_straight(lid)
        except Exception as exc:  # diagnostics must never raise
            out.setdefault('market_errors', {})[league] = f'{type(exc).__name__}: {exc}'
            continue
        rows = []
        for m in cs2:
            if (m.get('league') or {}).get('name') != league:
                continue
            for row in markets or []:
                if row.get('matchupId') != m.get('id') or row.get('type') != 'moneyline':
                    continue
                names = [x.get('name') for x in (m.get('participants') or [])]
                ids = [x.get('id') for x in (m.get('participants') or [])]
                rows.append({
                    'matchup': names,
                    'participant_ids': ids,
                    'startTime': m.get('startTime'),
                    'period': row.get('period'), 'key': row.get('key'), 'status': row.get('status'),
                    'prices': [{'participantId': p.get('participantId'),
                                'designation': p.get('designation'),
                                'american': p.get('price')} for p in (row.get('prices') or [])],
                    'price_order_note': 'prices are ordered the same way as "matchup"',
                })
        out.setdefault('moneyline_rows', {})[league] = rows
    return out
