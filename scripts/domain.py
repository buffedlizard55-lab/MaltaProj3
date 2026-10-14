"""Deterministic, source-only identity matching and explicitly labeled analysis.

No Hotspawn participation/score/points field is a probability input. Missing
observations stay None. Synthetic test fixtures never enter published data.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from statistics import median

UTC = timezone.utc
MAX_PRICE_AGE_HOURS = 8
MAX_RATING_AGE_DAYS = 35
MAX_SPREAD = 0.12
VALVE_RD = 75  # Fixed-RD assumption in Valve's published model/fit.js.


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def timestamp(value) -> datetime | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)) or str(value).isdigit():
            v = float(value)
            if not math.isfinite(v) or v <= 0:
                return None
            return datetime.fromtimestamp(v / 1000 if v > 100_000_000_000 else v, UTC)
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.astimezone(UTC) if dt.tzinfo else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def name_key(value: str) -> str:
    # Case/Unicode/whitespace equivalence only. No fuzzy or sponsor-name aliases.
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def array(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            result = json.loads(value)
            return result if isinstance(result, list) else []
        except (ValueError, TypeError):
            pass
    return []


def finite(value) -> float | None:
    try:
        v = float(value)
        return v if math.isfinite(v) and not isinstance(value, bool) else None
    except (ValueError, TypeError):
        return None


def normalize_pair(a, b) -> list[float]:
    a, b = finite(a), finite(b)
    if a is None or b is None or a <= 0 or b <= 0:
        raise ValueError('Two positive finite source values are required')
    p = a / (a + b)
    return [round(p, 8), round(1 - p, 8)]


def no_vig(odds: list) -> list[float]:
    if len(odds) != 2 or any(finite(o) is None or float(o) <= 1 for o in odds):
        raise ValueError('Two decimal odds greater than one are required')
    implied = [1 / float(o) for o in odds]
    if not 0.85 <= sum(implied) <= 1.35:
        raise ValueError('Paired market margin is outside the acceptance policy')
    return normalize_pair(*implied)


def is_fresh(observed_at: str, now: datetime) -> bool:
    dt = timestamp(observed_at)
    return dt is not None and -300 <= (now - dt).total_seconds() <= MAX_PRICE_AGE_HOURS * 3600


def identity_matches(names: list, start, match: dict) -> bool:
    if len(names) != 2 or not all(isinstance(n, str) and n.strip() for n in names):
        return False
    keys = [name_key(n) for n in names]
    wanted = [name_key(t['name']) for t in match['teams']]
    dt, md = timestamp(start), timestamp(match['starts_at'])
    return len(set(keys)) == 2 and set(keys) == set(wanted) and dt is not None and md is not None and abs((dt - md).total_seconds()) <= 60


def align(values: list, source_names: list, match: dict) -> list:
    if len(values) != 2 or len(set(map(name_key, source_names))) != 2:
        raise ValueError('Ambiguous outcome mapping')
    by_name = dict(zip(map(name_key, source_names), values))
    return [by_name[name_key(t['name'])] for t in match['teams']]


def polymarket_candidate(event: dict, match: dict, now: datetime) -> tuple[dict | None, str]:
    candidates = []
    if event.get('closed') is not False or event.get('active') is not True or event.get('live') is True:
        return None, 'Event is not confirmed active and prematch'
    if not str(event.get('slug', '')).startswith('cs2-'):
        return None, 'Not an identified CS2 fixture'
    for market in event.get('markets', []):
        names = array(market.get('outcomes'))
        start = market.get('gameStartTime') or event.get('startTime')
        if not identity_matches(names, start, match):
            continue
        scope = market.get('sportsMarketType') or (market.get('sports') or {}).get('sports_market_type')
        if scope != 'moneyline':
            continue
        # Map winners may share the two team names. Never confuse these with a series.
        if re.search(r'\b(map\s*\d|game\s*\d|handicap|spread|total|outright)\b', market.get('question', ''), re.I):
            continue
        if market.get('active') is not True or market.get('closed') is not False or market.get('acceptingOrders') is not True:
            continue
        if timestamp(start) is None or timestamp(start) <= now:
            continue
        if len(array(market.get('clobTokenIds'))) != 2:
            continue
        candidates.append(market)
    if len(candidates) != 1:
        return None, 'No unique open series-winner market with exact teams and start time'
    return candidates[0], ''


def book_midpoint(book: dict, token: str, condition: str, now: datetime) -> dict:
    if str(book.get('asset_id')) != str(token) or book.get('market') != condition:
        raise ValueError('Order book token/condition does not match the market')
    when = timestamp(book.get('timestamp'))
    if when is None or not is_fresh(iso(when), now):
        raise ValueError('Missing, future-dated or stale order book timestamp')
    bids = [finite(x.get('price')) for x in book.get('bids', []) if finite(x.get('size')) is not None and float(x['size']) > 0]
    asks = [finite(x.get('price')) for x in book.get('asks', []) if finite(x.get('size')) is not None and float(x['size']) > 0]
    if not bids or not asks or any(x is None or not 0 < x < 1 for x in bids + asks):
        raise ValueError('Two-sided executable order book unavailable')
    bid, ask = max(bids), min(asks)  # Do not rely on provider array order.
    if bid > ask or ask - bid > MAX_SPREAD + 1e-9:
        raise ValueError('Crossed or wider-than-12-cent order book')
    return {'bid': bid, 'ask': ask, 'spread': round(ask - bid, 8), 'midpoint': (bid + ask) / 2, 'timestamp': iso(when)}


def market_analysis(event: dict, market: dict, books: list, match: dict, now: datetime, observed_at: str) -> dict:
    tokens = array(market.get('clobTokenIds'))
    by_token = {str(b.get('asset_id')): b for b in books}
    quotes = [book_midpoint(by_token[str(t)], str(t), market['conditionId'], now) for t in tokens]
    names = array(market.get('outcomes'))
    quotes = align(quotes, names, match)
    probs = normalize_pair(*(q['midpoint'] for q in quotes))
    return {
        'method': 'market', 'label': 'Market-implied estimate', 'probabilities': probs,
        'fair_decimal': [round(1 / p, 3) for p in probs],
        'observed_at': observed_at, 'source': 'Polymarket',
        'source_url': 'https://polymarket.com/event/' + event['slug'],
        'source_api': 'https://gamma-api.polymarket.com/events/' + str(event['id']),
        'market_id': str(market['id']), 'event_id': str(event['id']),
        'source_outcomes': names, 'quotes': quotes,
        'volume': finite(market.get('volumeNum', market.get('volume'))),
        'liquidity': finite(market.get('liquidityNum', market.get('liquidity'))),
        'limitations': ['One prediction market, not a multi-book consensus. Midpoints are not guaranteed execution prices. Fees are excluded.'],
    }


def sportsbook_quote(event: dict, match: dict, observed_at: str, now: datetime) -> dict | None:
    teams = event.get('teams') or {}
    names = [(teams.get(k) or {}).get('name', '') for k in ['home', 'away']]
    if event.get('gameId') != 6 or event.get('isLive') is not False or not identity_matches(names, event.get('startTime'), match):
        return None
    if not is_fresh(observed_at, now):
        return None
    market = event.get('market') or {}
    if name_key(market.get('name', '')) not in {'match winner', 'match winner incl. overtime', 'match winner inc. overtime'} or market.get('status') != 1:
        return None
    if market.get('draw') is not None:
        return None
    sides = [market.get(k) or {} for k in ['home', 'away']]
    if any(s.get('status') != 1 for s in sides):
        return None
    if set(name_key(s.get('name', '')) for s in sides) != set(map(name_key, names)):
        return None
    odds = align([s.get('odds') for s in sides], names, match)
    probs = no_vig(odds)
    return {'provider': 'Thunderpick', 'family': 'thunderpick', 'odds': odds, 'probabilities': probs, 'observed_at': observed_at, 'source_url': 'https://thunderpick.io/api/matches?matchesIds=' + str(event['id']), 'event_id': str(event['id'])}


def consensus(quotes: list, now: datetime) -> dict | None:
    by_family = {}
    for q in quotes:
        if is_fresh(q['observed_at'], now):
            by_family.setdefault(q['family'], q)
    if not by_family:
        return None
    qs = list(by_family.values())
    p = median(q['probabilities'][0] for q in qs)
    probabilities = normalize_pair(p, 1 - p)
    return {'method': 'bookmaker', 'label': 'No-vig bookmaker estimate', 'probabilities': probabilities, 'fair_decimal': [round(1 / x, 3) for x in probabilities], 'observed_at': min(q['observed_at'] for q in qs), 'source': ' + '.join(q['provider'] for q in qs), 'source_url': qs[0]['source_url'], 'quotes': qs, 'limitations': ['Bookmaker margin removed by proportional normalization. A single source is not a consensus.' if len(qs) == 1 else 'Median of independent source-family no-vig probabilities; not a calibrated forecasting model.']}


def parse_valve_table(text: str, url: str, snapshot_date: str) -> list[dict]:
    result = []
    for line in text.splitlines():
        fields = [f.strip() for f in line.split('|')[1:-1]]
        if len(fields) < 5 or not fields[0].isdigit() or not fields[1].isdigit():
            continue
        link = re.search(r'\[details\]\(([^)]+)\)', fields[4])
        result.append({'standing': int(fields[0]), 'points': int(fields[1]), 'name': fields[2], 'roster': [x.strip() for x in fields[3].split(',') if x.strip()], 'snapshot_date': snapshot_date, 'source_url': url, 'detail_path': link.group(1) if link else None})
    if not result:
        raise ValueError('Valve standings table schema not recognized')
    return result


def valve_analysis(match: dict, rows: list, now: datetime, observed_at: str) -> tuple[dict | None, str]:
    by_name = defaultdict(list)
    for row in rows:
        by_name[name_key(row['name'])].append(row)
    inputs = []
    for team in match['teams']:
        found = by_name[name_key(team['name'])]
        if len(found) != 1:
            return None, f'{team["name"]}: ' + ('multiple Valve rosters share this name; identity is unresolved' if found else 'no exact-name Valve rating found')
        row = found[0]
        day = datetime.strptime(row['snapshot_date'], '%Y-%m-%d').replace(tzinfo=UTC)
        if not 0 <= (now - day).total_seconds() <= MAX_RATING_AGE_DAYS * 86400:
            return None, 'Valve standings snapshot is future-dated or older than 35 days'
        if len(row['roster']) != 5:
            return None, f'{team["name"]}: a complete five-player rating roster is not confirmed'
        inputs.append(row)
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * VALVE_RD ** 2 / math.pi ** 2)
    p = 1 / (1 + 10 ** (g * (inputs[1]['points'] - inputs[0]['points']) / 400))
    probs = normalize_pair(p, 1 - p)
    return {'method': 'model', 'label': 'Valve-rating research estimate', 'probabilities': probs, 'fair_decimal': [round(1 / x, 3) for x in probs], 'observed_at': observed_at, 'source': 'Valve official standings', 'source_url': inputs[0]['source_url'], 'inputs': inputs, 'rd_assumption': VALVE_RD, 'g': g, 'snapshot_date': inputs[0]['snapshot_date'], 'formula_source': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/fit.js', 'limitations': ['Research model, not observed betting odds or a verified true win probability.', 'Exact-name association only; current rosters, stand-ins and map vetoes are not independently confirmed.', 'Fixed rating deviation of 75 follows Valve’s published fit example. This deployment has not been backtested or calibrated.']}, ''


def selection(analysis: dict | None) -> int | None:
    if analysis is None:
        return None
    a, b = analysis['probabilities']
    # A genuinely equal estimate is a no-edge result, never an arbitrary pick.
    return None if abs(a - b) < 1e-8 else (0 if a > b else 1)
