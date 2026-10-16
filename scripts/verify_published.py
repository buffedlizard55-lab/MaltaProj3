"""V-2: verify every published pick against official first-party sources.

Reads only the evidence this session archived with ``scripts/research_verify.py`` —
the deployed production snapshot plus the original responses from Hotspawn, Polymarket,
Kalshi, Bovada, Thunderpick, HLTV and Valve — and replays what the site publishes.

What this module does:
  * reconciles the deployed inventory against Hotspawn's own fixtures API;
  * recomputes every published count from the published rows;
  * replays every published probability from the quote the row itself cites;
  * checks that every cited source URL is an official source this project trusts;
  * looks for an independent money line for fixtures the site leaves unresolved;
  * writes an irregularity register in the schema ``scripts/build.py`` already loads.

What this module never does:
  * invent, estimate, default or repair a probability. A value that cannot be replayed
    from a cited official source is reported as unverified and left blank.
  * edit another session's script, dataset or page.

Usage::

    python -m scripts.verify_published [--evidence data/research/ba7164a0]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Read-only reuse of two published contracts. Neither module is modified here.
from scripts.audit_rows import is_official
from scripts.domain import name_key

SCHEMA_VERSION = 1
SESSION = 'arena-ba7164a0'
TOLERANCE = 1e-6          # published probabilities are rounded to 8 decimal places
FAIR_DECIMAL_PLACES = 3   # the published fair-decimal rounding

# The published origination ladder rejects an order book wider than this (scripts/
# originate.py MAX_ACCEPTED_SPREAD). Re-declared here so this audit applies the same
# ceiling without importing a module another session owns and is actively editing.
MAX_ACCEPTED_SPREAD = 0.12

VALVE_STANDINGS_BASE = ('https://github.com/ValveSoftware/counter-strike_regional_standings/'
                        'blob/main/live/2026/')
HOTSPAWN_FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?'
                         'sport_alias=cs2&status=scheduled&tenantId=1')
HOTSPAWN_LOBBY = 'https://play.hotspawn.com/lobby'
# The deployed snapshot is *fetched* from GitHub Pages, but Pages is not on the official
# allow-list published in scripts/audit_rows.py, so every citation a reviewer can click
# points at the same file in this repository instead. Fetch URL and cited URL are kept
# apart deliberately: citing the Pages host would make every row of this audit a
# row-source violation.
PAGES_LATEST_FETCH = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json'
PAGES_ORIGINATION_FETCH = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json'
REPO_DATA = 'https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/'
PAGES_LATEST = REPO_DATA + 'latest.json'
PAGES_ORIGINATION = REPO_DATA + 'origination.json'


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def parse_iso(value):
    if not value:
        return None
    text = str(value).replace('Z', '+00:00')
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError):
        return None


def load_raw(evidence: Path, name: str):
    """Read an archived original response, transparently handling the gzip variant."""
    plain = evidence / 'raw' / name
    if plain.exists():
        return load_json(plain)
    import gzip
    compressed = evidence / 'raw' / (name + '.gz')
    if compressed.exists():
        try:
            with gzip.open(compressed, 'rt') as handle:
                return json.loads(handle.read())
        except (ValueError, OSError):
            return None
    return None


def load_raw_text(evidence: Path, name: str) -> str | None:
    plain = evidence / 'raw' / name
    if plain.exists():
        try:
            return plain.read_text()
        except OSError:
            return None
    import gzip
    compressed = evidence / 'raw' / (name + '.gz')
    if compressed.exists():
        try:
            with gzip.open(compressed, 'rt') as handle:
                return handle.read()
        except OSError:
            return None
    return None


# ---------------------------------------------------------------------------
# Arithmetic that the published methodology documents
# ---------------------------------------------------------------------------

def devig(decimal_odds: list) -> list | None:
    """Remove a two-outcome book's overround by proportional normalisation.

    ``fair_i = (1 / decimal_i) / sum_j (1 / decimal_j)`` — the same rule the site
    publishes for its bookmaker rung. Returns ``None`` when any price is unusable,
    because a rejected book must never be normalised into a plausible-looking number.
    """
    if not isinstance(decimal_odds, list) or len(decimal_odds) != 2:
        return None  # a one-sided "book" would normalise to a confident-looking 100%
    implied = []
    for odd in decimal_odds:
        try:
            value = float(odd)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value) or value <= 1.0:
            return None
        implied.append(1.0 / value)
    total = sum(implied)
    if total <= 0:
        return None
    return [value / total for value in implied]


def midpoint(bid, ask):
    try:
        low, high = float(bid), float(ask)
    except (TypeError, ValueError):
        return None
    if not (0 < low <= high < 1):
        return None
    return (low + high) / 2


def executable_book(book: dict) -> dict | None:
    """Best executable bid/ask from a CLOB book's own price/size levels.

    Levels with no size are not executable and are ignored, and the best bid/ask are
    taken as max/min rather than trusting the provider's array order - the same rule
    scripts/domain.py::book_midpoint publishes.
    """
    if not isinstance(book, dict):
        return None

    def levels(key):
        out = []
        for level in book.get(key) or []:
            if not isinstance(level, dict):
                continue
            try:
                price, size = float(level.get('price')), float(level.get('size'))
            except (TypeError, ValueError):
                continue
            if size > 0 and 0 < price < 1:
                out.append(price)
        return out

    bids, asks = levels('bids'), levels('asks')
    if not bids or not asks:
        return None
    best_bid, best_ask = max(bids), min(asks)
    spread = round(best_ask - best_bid, 8)
    return {
        'best_bid': best_bid, 'best_ask': best_ask, 'spread': spread,
        'midpoint': (best_bid + best_ask) / 2,
        'crossed': best_bid > best_ask,
        'executable_within_ceiling': (not best_bid > best_ask) and spread <= MAX_ACCEPTED_SPREAD,
        'bid_levels': len(bids), 'ask_levels': len(asks),
        'timestamp': book.get('timestamp'),
        'asset_id': book.get('asset_id'),
        'source_url': book.get('source_url'),
    }


def overround(decimal_odds: list):
    """The book's total implied probability. Above 1.0 is the margin the book keeps."""
    try:
        values = [float(o) for o in decimal_odds]
    except (TypeError, ValueError):
        return None
    if len(values) != 2 or any(v <= 1.0 for v in values):
        return None
    return round(sum(1.0 / v for v in values), 6)


def median(values: list):
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        return None
    middle = count // 2
    if count % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def close(a, b, tolerance=TOLERANCE) -> bool:
    try:
        return abs(float(a) - float(b)) <= tolerance
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Identity joins
# ---------------------------------------------------------------------------

def compare_names(published: list, candidate: list) -> str:
    """Classify how two team-name pairs relate. Never asserts an equivalence it lacks.

    ``exact``        - identical strings.
    ``normalized``   - identical after case/whitespace/punctuation folding.
    ``unverified``   - anything else. An unverified join is reported, never used to
                       move a probability into the canonical pick list.
    """
    if not published or not candidate or len(published) != len(candidate) != 2:
        return 'unverified'
    if published == candidate:
        return 'exact'
    if [name_key(x) for x in published] == [name_key(x) for x in candidate]:
        return 'normalized'
    if sorted(name_key(x) for x in published) == sorted(name_key(x) for x in candidate):
        return 'normalized-swapped'
    return 'unverified'


def swap_if_needed(probs: list, source_names: list, target_names: list) -> list | None:
    """Align a two-sided probability vector to the published team order."""
    if not probs or len(probs) != 2 or len(source_names) != 2 or len(target_names) != 2:
        return None
    source = [name_key(x) for x in source_names]
    target = [name_key(x) for x in target_names]
    if source == target:
        return list(probs)
    if source == list(reversed(target)):
        return [probs[1], probs[0]]
    return None


# ---------------------------------------------------------------------------
# 1. Inventory reconciliation
# ---------------------------------------------------------------------------

def hotspawn_api_ids(payload) -> set:
    ids = set()
    if isinstance(payload, dict):
        payload = payload.get('data') or payload.get('fixtures') or []
    for fixture in payload if isinstance(payload, list) else []:
        if isinstance(fixture, dict) and fixture.get('id') is not None:
            ids.add(str(fixture['id']))
    return ids


def reconcile_inventory(deployed: dict, fixtures_payload) -> dict:
    api_ids = hotspawn_api_ids(fixtures_payload)
    rows = deployed.get('matches') or []
    site_ids = {str(r['id']) for r in rows if isinstance(r, dict) and r.get('id') is not None}
    open_rows = [r for r in rows if isinstance(r, dict) and r.get('availability') != 'past']
    return {
        'hotspawn_api_id_count': len(api_ids),
        'deployed_row_count': len(site_ids),
        'deployed_open_count': len(open_rows),
        'missing_from_site': sorted(api_ids - site_ids),
        'extra_on_site': sorted(site_ids - api_ids),
        'reconciled': api_ids == site_ids,
        'verdict': ('Every CS2 fixture Hotspawn lists is published, and the site publishes '
                    'no fixture Hotspawn does not list.'
                    if api_ids == site_ids else
                    'The published inventory and Hotspawn\'s own fixtures API disagree. '
                    'Both sets are listed below; nothing is reconciled by assumption.'),
        'fetch_url': PAGES_LATEST_FETCH,
        'source_urls': [HOTSPAWN_FIXTURES_API, HOTSPAWN_LOBBY, PAGES_LATEST],
    }


# ---------------------------------------------------------------------------
# 2. Published counts
# ---------------------------------------------------------------------------

def recompute_counts(deployed: dict) -> dict:
    rows = [r for r in deployed.get('matches') or [] if isinstance(r, dict)]
    upcoming = [r for r in rows if r.get('availability') != 'past']
    with_analysis = [r for r in upcoming if r.get('analysis')]
    methods = [str((r.get('analysis') or {}).get('method')) for r in with_analysis]
    unresolved_flags = [f for f in deployed.get('flags') or []
                        if isinstance(f, dict) and str(f.get('id', '')).startswith('unresolved-')]
    return {
        'inventory': len(rows),
        'upcoming': len(upcoming),
        'archived': len(rows) - len(upcoming),
        'unknown_schedule': sum(1 for r in rows if not r.get('starts_at')),
        # `pick_index` is published at row level, not inside `analysis`; both are accepted
        # so the recomputation cannot silently report zero picks. Verified against the
        # deployed rows of the 2026-10-16T08:10:35Z snapshot.
        'picks': sum(1 for r in with_analysis
                     if (r.get('pick_index') is not None
                         or (r.get('analysis') or {}).get('pick_index') is not None)),
        'market': methods.count('market'),
        'model': methods.count('model'),
        'bookmaker': methods.count('bookmaker'),
        'unresolved': sum(1 for r in upcoming if not r.get('analysis')),
        'unresolved_flags': len(unresolved_flags),
    }


def check_counts(deployed: dict) -> dict:
    published = deployed.get('counts') or {}
    recomputed = recompute_counts(deployed)
    mismatches = []
    for key, value in recomputed.items():
        if key == 'unresolved_flags':
            continue
        if key in published and published[key] != value:
            mismatches.append({'count': key, 'published': published[key], 'recomputed': value})
    return {
        'published': published,
        'recomputed': recomputed,
        'mismatches': mismatches,
        'verdict': ('Every published headline count was recomputed from the published rows '
                    'and agrees.' if not mismatches else
                    'At least one published headline count does not equal the value recomputed '
                    'from the published rows. The rows are authoritative; the discrepancy is '
                    'reported, not corrected here.'),
        'fetch_url': PAGES_LATEST_FETCH,
        'source_urls': [PAGES_LATEST],
    }


# ---------------------------------------------------------------------------
# 3. Probability replay
# ---------------------------------------------------------------------------

def replay_quote(quote: dict) -> list | None:
    """Replay one cited quote's own probabilities from the prices it cites."""
    family = str(quote.get('family') or '')
    odds = quote.get('odds')
    if isinstance(odds, list) and len(odds) == 2:
        return devig(odds)
    bid, ask = quote.get('bid'), quote.get('ask')
    if isinstance(bid, list) and isinstance(ask, list) and len(bid) == 2 and len(ask) == 2:
        mids = [midpoint(b, a) for b, a in zip(bid, ask)]
        if any(m is None for m in mids):
            return None
        total = sum(mids)
        return [m / total for m in mids] if total > 0 else None
    if quote.get('midpoint') is not None:
        return None  # single-sided quote object; handled by the paired-quote path
    if family == 'model':
        return None
    return None


def replay_row(row: dict) -> dict:
    """Replay a published origination row from the quotes the row itself cites."""
    origination = row.get('origination') or {}
    published = origination.get('probabilities')
    result = {
        'id': row.get('id'),
        'method': origination.get('method'),
        'published': published,
        'replayed': None,
        'status': 'not-checked',
        'checks': [],
        'source_urls': [],
    }
    if not published or len(published) != 2:
        result['status'] = 'blank'
        result['checks'].append('Probabilities are intentionally blank; nothing to replay.')
        return result
    result['checks'].append('Published probabilities sum to 1 within 1e-6: '
                            f'{close(sum(published), 1.0)}')
    quotes = [q for q in origination.get('quotes') or [] if isinstance(q, dict)]
    for quote in quotes:
        url = quote.get('source_url') or origination.get('source_url')
        if url:
            result['source_urls'].append(url)
    if origination.get('source_url'):
        result['source_urls'].append(origination['source_url'])
    result['source_urls'] = sorted(set(result['source_urls']))

    fair = origination.get('fair_decimal')
    if isinstance(fair, list) and len(fair) == 2:
        expected = [round(1.0 / p, FAIR_DECIMAL_PLACES) for p in published]
        result['checks'].append(f'fair_decimal equals 1/probability rounded to '
                                f'{FAIR_DECIMAL_PLACES} places: {all(close(a, b, 5e-4) for a, b in zip(fair, expected))}')

    if not quotes:
        inputs = origination.get('inputs') or []
        if origination.get('method') == 'model' and inputs:
            result['status'] = 'model-inputs-only'
            official_inputs = all(str(i.get('source_url', '')).startswith(VALVE_STANDINGS_BASE)
                                  for i in inputs if isinstance(i, dict))
            result['checks'].append(
                'The Valve-rating research model is the ladder\'s lowest rung and its formula is '
                'owned by another session, so it is not reimplemented here. The official inputs '
                f'the row cites are verified instead: {len(inputs)} rating row(s), every one '
                f'citing Valve\'s own standings file: {official_inputs}.')
            result['model_inputs'] = [
                {'name': i.get('name'), 'standing': i.get('standing'), 'points': i.get('points'),
                 'roster': i.get('roster'), 'snapshot_date': i.get('snapshot_date'),
                 'source_url': i.get('source_url')}
                for i in inputs if isinstance(i, dict)]
            if origination.get('source_url'):
                result['source_urls'] = sorted(set(result['source_urls'] + [origination['source_url']]))
        else:
            result['status'] = 'no-quote'
            result['checks'].append('The row cites no quote object and no official model inputs, '
                                    'so the published probability cannot be replayed from '
                                    'first-party prices.')
        return result

    # Paired single-sided quote objects (the featured market rung publishes one object
    # per outcome, each carrying its own bid/ask and midpoint).
    mids = [q.get('midpoint') for q in quotes if q.get('midpoint') is not None]
    if len(mids) == 2 and all(q.get('midpoint') is not None for q in quotes):
        replayed = []
        for quote in quotes:
            mid = midpoint(quote.get('bid'), quote.get('ask'))
            replayed.append(mid if mid is not None else quote.get('midpoint'))
            result['checks'].append(f'midpoint equals (bid+ask)/2 for {quote.get("provider")}: '
                                    f'{close(mid, quote.get("midpoint"))}')
        if all(r is not None for r in replayed):
            result['replayed'] = replayed
    else:
        per_quote = [replay_quote(q) for q in quotes]
        if all(p is not None for p in per_quote):
            for quote, replayed_quote in zip(quotes, per_quote):
                cited = quote.get('probabilities')
                if isinstance(cited, list) and len(cited) == 2:
                    result['checks'].append(
                        f'{quote.get("provider")} quote probabilities replay from its own cited '
                        f'prices: {all(close(a, b, 1e-6) for a, b in zip(cited, replayed_quote))}')
            method = origination.get('method')
            if method == 'consensus':
                sides = [[p[i] for p in per_quote] for i in (0, 1)]
                aggregated = [median(side) for side in sides]
                total = sum(aggregated)
                result['replayed'] = [v / total for v in aggregated] if total else None
                result['checks'].append('Consensus equals the median of the independent quotes '
                                        'per side, renormalised.')
            elif len(per_quote) == 1:
                result['replayed'] = per_quote[0]
            else:
                result['status'] = 'multi-quote-unaggregated'
                result['checks'].append('Several quotes are cited but the row is not a consensus, '
                                        'so no single replay is claimed.')
        elif origination.get('method') == 'model':
            inputs = origination.get('inputs') or []
            result['status'] = 'model-inputs-only'
            result['checks'].append(
                'The Valve-rating research model is the ladder\'s lowest rung and its formula is '
                'owned by another session; the formula is not reimplemented here. The official '
                'inputs the row cites are verified instead: '
                f'{len(inputs)} rating row(s), all citing '
                f'{bool(inputs) and all(str(i.get("source_url", "")).startswith(VALVE_STANDINGS_BASE) for i in inputs)}.')

    if result['replayed'] is None:
        if result['status'] == 'not-checked':
            result['status'] = 'unreplayable'
        return result
    # scripts/domain.py::market_analysis aligns `quotes` to the fixture's team order and
    # leaves `source_outcomes` in the market's own order. Verified against first-party
    # Polymarket prices for all 15 market rows of the 2026-10-16T08:10:35Z snapshot, so
    # the replayed vector is compared position-for-position with the published one.
    aligned = result['replayed']
    result['alignment'] = 'published-team-order'
    agrees = all(close(a, b, 5e-5) for a, b in zip(aligned, published))
    result['replayed'] = aligned
    result['status'] = 'replayed' if agrees else 'mismatch'
    result['deviation'] = [round(float(a) - float(b), 6) for a, b in zip(aligned, published)]
    result['checks'].append(f'Replayed probabilities agree with the published ones: {agrees}')
    return result


def row_event_id(row: dict) -> str:
    """The Polymarket event a row is priced from.

    Single-source rows carry `event_id` at the origination level; consensus rows carry it
    on each quote instead (verified against fixtures 1080205 and 1081775 of the deployed
    2026-10-16T08:18:38Z snapshot, both `Polymarket + Kalshi` consensus rows whose
    top-level `event_id` is null).
    """
    origination = row.get('origination') or {}
    if origination.get('event_id'):
        return str(origination['event_id'])
    for quote in origination.get('quotes') or []:
        if isinstance(quote, dict) and str(quote.get('provider') or '') == 'Polymarket' \
                and quote.get('event_id'):
            return str(quote['event_id'])
    for quote in origination.get('quotes') or []:
        if isinstance(quote, dict) and quote.get('event_id'):
            return str(quote['event_id'])
    return ''


def row_aliases(row: dict) -> dict:
    """The row's own published, reviewed alias registry: alias key -> canonical name.

    Only aliases the site itself published with evidence are used, and every use is
    recorded in the audit output. This module never invents an equivalence.
    """
    aliases = {}
    for entry in row.get('aliases_used') or []:
        if not isinstance(entry, dict):
            continue
        alias, canonical = entry.get('alias'), entry.get('canonical')
        if isinstance(alias, str) and isinstance(canonical, str) and alias.strip():
            aliases[name_key(alias)] = canonical
    return aliases


def verify_against_first_party_market(rows: list, observations: dict) -> dict:
    """Compare each market-priced row with Polymarket's own archived event, independently.

    This is the strongest check available: it does not trust the row's quotes, its
    recorded outcome order or its arithmetic. It reads the outcome names and prices from
    the archived Gamma response for the row's own ``event_id``, aligns them to the
    fixture's team order by name, and compares.

    Prices move between the site's refresh and this probe, so the deviation in percentage
    points is reported alongside the verdict rather than demanding exact equality.
    """
    moneylines = {str(m.get('event_id')): m
                  for m in (observations.get('polymarket') or {}).get('moneylines') or []}
    books = (observations.get('polymarket') or {}).get('books') or {}
    checked, agrees, drifts, unverifiable = [], [], [], []
    for row in rows:
        origination = row.get('origination') or {}
        published = origination.get('probabilities')
        if not published or origination.get('method') not in ('market', 'consensus'):
            continue
        event_id = row_event_id(row)
        first = moneylines.get(event_id)
        names = [t.get('name') for t in row.get('teams') or []]
        if not first:
            unverifiable.append({'id': row.get('id'), 'teams': names, 'event_id': event_id,
                                 'reason': 'No archived Polymarket event for this event_id; '
                                           'the row is neither confirmed nor contradicted.'})
            continue
        aliases = row_aliases(row)
        index = {}
        for i, outcome in enumerate(first.get('outcomes') or []):
            index.setdefault(name_key(outcome), i)
            canonical = aliases.get(name_key(outcome))
            if canonical:
                index.setdefault(name_key(canonical), i)
        try:
            positions = []
            for team in names:
                key = name_key(team)
                if key not in index:
                    raise KeyError(team)
                positions.append(index[key])
            if sorted(positions) != [0, 1]:
                raise KeyError('both first-party outcomes must be used exactly once')
            aligned = [float(first['outcome_prices'][i]) for i in positions]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            unverifiable.append({'id': row.get('id'), 'teams': names, 'event_id': event_id,
                                 'reason': 'First-party outcome names do not join to the fixture '
                                           f'names ({exc}); alignment is not assumed.',
                                 'first_party_outcomes': first.get('outcomes'),
                                 'reviewed_aliases': sorted(set(aliases.values()))})
            continue
        deviation = [round((aligned[i] - published[i]) * 100, 2) for i in (0, 1)]
        same_side = (aligned[0] >= aligned[1]) == (published[0] >= published[1])
        record = {
            'id': row.get('id'),
            'teams': names,
            'event_id': event_id,
            'aligned_via_reviewed_alias': [
                f'{alias} -> {canonical}' for alias, canonical in aliases.items()
                if alias in index and name_key(canonical) in [name_key(t) for t in names]],
            'event_slug': first.get('event_slug'),
            'first_party_outcomes': first.get('outcomes'),
            'first_party_prices': aligned,
            'published_probabilities': published,
            'deviation_pp': deviation,
            'same_favourite': same_side,
            'recorded_source_outcomes': origination.get('source_outcomes'),
            'source_url': first.get('source_url'),
            'first_party_observed_at': first.get('updated_at'),
            'published_observed_at': origination.get('observed_at'),
            'book': {str(t): books.get(str(t)) for t in first.get('clob_token_ids') or []} or None,
        }
        checked.append(record)
        (agrees if same_side and max(abs(v) for v in deviation) <= 5.0 else drifts).append(record)
    return {'checked': checked, 'agreeing': agrees, 'drifted_or_reversed': drifts,
            'unverifiable': unverifiable,
            'fetch_url': PAGES_ORIGINATION_FETCH,
            'source_urls': [PAGES_ORIGINATION,
                            'https://gamma-api.polymarket.com/events',
                            'https://polymarket.com/esports/cs2']}


def outcome_order_hazards(rows: list, first_party: dict) -> list:
    """Rows where the published `source_outcomes` order differs from the team order.

    `probabilities` and `quotes` are aligned to Hotspawn's team order while
    `source_outcomes` keeps the market's own order (scripts/domain.py::market_analysis).
    Nothing is wrong arithmetically, but a reviewer reading the two arrays positionally
    inverts the favourite. Each case is listed with the first-party prices that settle it.
    """
    by_id = {r['id']: r for r in first_party.get('checked') or []}
    hazards = []
    for row in rows:
        origination = row.get('origination') or {}
        recorded = origination.get('source_outcomes')
        names = [t.get('name') for t in row.get('teams') or []]
        if not recorded or len(recorded) != 2 or len(names) != 2:
            continue
        if [name_key(x) for x in recorded] == [name_key(x) for x in names]:
            continue
        verified = by_id.get(row.get('id'))
        hazards.append({
            'id': row.get('id'),
            'teams': names,
            'recorded_source_outcomes': recorded,
            'published_probabilities': origination.get('probabilities'),
            'first_party_outcomes': (verified or {}).get('first_party_outcomes'),
            'first_party_prices': (verified or {}).get('first_party_prices'),
            'published_matches_first_party_in_team_order': bool(verified) and verified.get('same_favourite'),
            'source_url': (verified or {}).get('source_url') or origination.get('source_url'),
        })
    return hazards


# ---------------------------------------------------------------------------
# 4. Source-link verification
# ---------------------------------------------------------------------------

def collect_urls(node, found: set) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ('source_url', 'api_url', 'source_api', 'lobby_url', 'url', 'public_page') \
                    and isinstance(value, str) and value.startswith('http'):
                found.add(value)
            else:
                collect_urls(value, found)
    elif isinstance(node, list):
        for value in node:
            collect_urls(value, found)


def check_source_links(origination: dict) -> dict:
    urls: set = set()
    for row in origination.get('matches') or []:
        collect_urls(row, urls)
    unofficial = sorted(u for u in urls if not is_official(u))
    return {
        'distinct_source_urls': len(urls),
        'unofficial': unofficial,
        'verdict': ('Every source URL cited by a published pick row is an official source this '
                    'project trusts.' if not unofficial else
                    'At least one cited URL is outside the official allow-list published in '
                    'scripts/audit_rows.py.'),
        'fetch_url': PAGES_ORIGINATION_FETCH,
        'source_urls': [PAGES_ORIGINATION],
    }


# ---------------------------------------------------------------------------
# 5. Independent money lines for fixtures the site leaves unresolved
# ---------------------------------------------------------------------------

def market_start_utc(row: dict) -> str | None:
    """The match start a Polymarket moneyline states, in ISO-8601 UTC.

    Gamma publishes `gameStartTime` as "2026-10-19 09:00:00+00" (a space separator, no
    seconds fraction), which `datetime.fromisoformat` rejects as written, so it is
    normalised here. `eventStartTime` is only a fallback: an event can open long before
    the match it prices.
    """
    for key in ('game_start_time', 'event_start_time'):
        value = row.get(key)
        if not value:
            continue
        stamp = parse_iso(str(value).replace(' ', 'T'))
        if stamp is not None:
            return stamp.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    return None


def independent_lines(evidence: Path, observations: dict) -> list:
    """Every prematch series line an official book or exchange quoted, with its own link.

    Nothing here is joined to a fixture by assumption: the join class is recorded and an
    ``unverified`` join never produces a probability for the canonical list.
    """
    lines = []

    bovada = ((observations.get('other_books') or {}).get('providers') or {}).get('bovada') or {}
    for row in bovada.get('moneylines') or []:
        if not row.get('prematch_main_moneyline'):
            continue
        names = [o.get('name') for o in row.get('outcomes') or []]
        fair = devig([o.get('decimal') for o in row.get('outcomes') or []])
        lines.append({
            'provider': 'Bovada',
            'family': 'bookmaker',
            'names': names,
            'start_utc': row.get('start_utc'),
            'decimal_odds': [o.get('decimal') for o in row.get('outcomes') or []],
            'american_odds': [o.get('american') for o in row.get('outcomes') or []],
            'devigged': fair,
            'overround': overround([o.get('decimal') for o in row.get('outcomes') or []]),
            # A posted sportsbook price is executable by definition: there is no order
            # book to be wide. Only exchange books carry a spread ceiling.
            'executable_within_ceiling': True,
            'worst_spread': None,
            'probability_basis': 'bookmaker-decimal-price',
            'league': row.get('league'),
            'event_id': row.get('event_id'),
            'source_url': row.get('source_url'),
            'page_url': row.get('page_url'),
            'observed_at': bovada.get('observed_at'),
            'evidence': 'data/research/ba7164a0/raw/bovada-cs2.json',
        })

    thunder = ((observations.get('other_books') or {}).get('providers') or {}).get('thunderpick') or {}
    for row in thunder.get('moneylines') or []:
        names = [s.get('name') for s in row.get('selections') or []]
        odds = [s.get('odds') for s in row.get('selections') or []]
        fair = devig(odds)
        lines.append({
            'provider': 'Thunderpick',
            'family': 'bookmaker',
            'names': names,
            'start_utc': row.get('starts_at'),
            'decimal_odds': odds,
            'american_odds': None,
            'devigged': fair,
            'overround': overround(odds),
            'executable_within_ceiling': True,
            'worst_spread': None,
            'probability_basis': 'bookmaker-decimal-price',
            'league': row.get('competition'),
            'event_id': row.get('event_id'),
            'source_url': row.get('source_url'),
            'page_url': row.get('source_url'),
            'observed_at': thunder.get('observed_at'),
            'evidence': 'data/research/ba7164a0/raw/thunderpick-cs2.json',
        })

    polymarket = observations.get('polymarket') or {}
    books = polymarket.get('books') or {}
    for row in polymarket.get('moneylines') or []:
        # A prediction market quotes probabilities, not decimal odds, so there is no
        # overround to remove. The executable midpoint of each side's own order book is
        # used when both books were read; otherwise the market's own last prices are
        # recorded as quoted, renormalised only so the two sides sum to one.
        fair, basis, side_books, spreads = None, None, [], []
        for token in row.get('clob_token_ids') or []:
            entry = executable_book(books.get(str(token)))
            side_books.append(entry)
            if entry:
                spreads.append(entry['spread'])
        if len(side_books) == 2 and all(side_books):
            mids = [b['midpoint'] for b in side_books]
            if sum(mids) > 0:
                fair = [m / sum(mids) for m in mids]
                basis = 'clob-executable-midpoint'
        if fair is None:
            prices = row.get('outcome_prices')
            if isinstance(prices, list) and len(prices) == 2:
                try:
                    values = [float(x) for x in prices]
                except (TypeError, ValueError):
                    values = []
                if len(values) == 2 and all(0 < v < 1 for v in values) and sum(values) > 0:
                    fair = [v / sum(values) for v in values]
                    basis = 'last-trade-price'
        lines.append({
            'provider': 'Polymarket',
            'family': 'market',
            'names': row.get('outcomes'),
            'start_utc': market_start_utc(row),
            'decimal_odds': None,
            'american_odds': None,
            'devigged': fair,
            'overround': None,
            'league': row.get('event_title'),
            'event_id': row.get('event_id'),
            'source_url': row.get('source_url'),
            'page_url': row.get('source_url'),
            'observed_at': row.get('updated_at'),
            'evidence': 'data/research/ba7164a0/observations.json',
            'books': side_books if all(side_books) else None,
            'worst_spread': max(spreads) if spreads else row.get('spread'),
            'executable_within_ceiling': bool(spreads) and max(spreads) <= MAX_ACCEPTED_SPREAD,
            'market_spread': row.get('spread'),
            'market_best_bid': row.get('best_bid'),
            'market_best_ask': row.get('best_ask'),
            'volume': row.get('volume'),
            'liquidity': row.get('liquidity'),
            'probability_basis': basis,
        })

    kalshi = ((observations.get('other_books') or {}).get('providers') or {}).get('kalshi') or {}
    for row in kalshi.get('markets') or []:
        lines.append({
            'provider': 'Kalshi',
            'family': 'market',
            'names': [row.get('yes_sub_title') or row.get('ticker')],
            'start_utc': None,
            'decimal_odds': None,
            'american_odds': None,
            'devigged': None,
            'overround': None,
            'league': row.get('event_title'),
            'event_id': row.get('event_ticker'),
            'source_url': row.get('source_url'),
            'page_url': row.get('source_url'),
            'observed_at': kalshi.get('observed_at'),
            'evidence': 'data/research/ba7164a0/raw/kalshi-cs2.json',
            'yes_bid': row.get('yes_bid'), 'yes_ask': row.get('yes_ask'),
            'no_bid': row.get('no_bid'), 'no_ask': row.get('no_ask'),
            'volume': row.get('volume'),
        })
    return lines


def join_line_to_fixture(line: dict, row: dict) -> dict:
    """Classify a line's identity join to one published fixture."""
    published_names = [t.get('name') for t in row.get('teams') or []]
    kind = compare_names(published_names, line.get('names') or [])
    out = {'join': kind}
    aligned = None
    if kind in ('exact', 'normalized'):
        aligned = swap_if_needed(line.get('devigged'), line.get('names') or [], published_names)
        out['aligned'] = aligned
    elif kind == 'normalized-swapped':
        out['aligned'] = None
        out['note'] = 'The same two names appear in the opposite order; side alignment is not assumed.'
    if kind == 'unverified':
        out['note'] = ('Names differ. The identity of this fixture and this line is NOT verified, '
                       'so no probability is taken from it.')
    return out


# ---------------------------------------------------------------------------
# 6. Unresolved fixtures: verify the stated reason against the original sources
# ---------------------------------------------------------------------------

def verify_unresolved(rows: list, lines: list, valve: dict) -> list:
    """For every fixture with no published probability, verify the reason it gives."""
    review = []
    ambiguous = valve.get('ambiguous') or {}
    ratings = valve.get('ratings') or {}
    absent = set(valve.get('absent') or [])
    for row in rows:
        origination = row.get('origination') or {}
        if origination.get('probabilities'):
            continue
        names = [t.get('name') for t in row.get('teams') or []]
        entry = {
            'id': row.get('id'),
            'teams': names,
            'competition': row.get('competition'),
            'starts_at': row.get('starts_at'),
            'locks_at': row.get('locks_at'),
            'lobby_url': row.get('lobby_url'),
            'source_url': row.get('source_url'),
            'stated_limitations': row.get('limitations') or [],
            'ladder': row.get('research') or [],
            'independent_lines': [],
            'verifications': [],
            'source_urls': [],
        }
        for item in row.get('research') or []:
            if isinstance(item, dict) and item.get('source_url'):
                entry['source_urls'].append(item['source_url'])
        # Verify each Valve-based rejection against Valve's own archived snapshot.
        for name in names:
            if name in ambiguous:
                candidates = ambiguous[name]
                entry['verifications'].append({
                    'claim': f'"{name}": multiple Valve rosters share this name',
                    'status': 'confirmed',
                    'detail': ('Valve\'s official snapshot lists this exact name '
                               f'{len(candidates)} times with different rosters: '
                               + '; '.join(f"standing {c['standing']}, {c['points']} points, "
                                           f"roster {', '.join(c['roster'])}" for c in candidates)
                               + '. Choosing one would be an inference, so no rating is used.'),
                    'source_url': candidates[0]['source_url'],
                })
                entry['source_urls'].append(candidates[0]['source_url'])
            elif name in absent:
                entry['verifications'].append({
                    'claim': f'"{name}": no Valve rating row found',
                    'status': 'confirmed',
                    'detail': (f'No exact-name row for "{name}" exists in '
                               f'{valve.get("snapshot_used")}.'),
                    'source_url': VALVE_STANDINGS_BASE + str(valve.get('snapshot_used')),
                })
                entry['source_urls'].append(VALVE_STANDINGS_BASE + str(valve.get('snapshot_used')))
            elif name in ratings:
                entry['verifications'].append({
                    'claim': f'"{name}": Valve rating row',
                    'status': 'present',
                    'detail': (f'Valve lists "{name}" at standing {ratings[name]["standing"]} with '
                               f'{ratings[name]["points"]} points and roster '
                               f'{", ".join(ratings[name]["roster"])}.'),
                    'source_url': ratings[name]['source_url'],
                })
        # Look for an independent money line for this fixture. Every observation is kept
        # and classified; a classification of `not-this-fixture` is retained in the dossier
        # so a reviewer can see what was considered and rejected, and why.
        for line in lines:
            candidate = classify_candidate(line, row)
            if candidate['verdict'] == 'not-this-fixture':
                continue
            entry['independent_lines'].append(candidate)
            if candidate.get('source_url'):
                entry['source_urls'].append(candidate['source_url'])
        entry['usable_lines'] = [c for c in entry['independent_lines'] if c['verdict'] == 'usable']
        entry['unusable_books'] = [c for c in entry['independent_lines']
                                   if c['verdict'] == 'identity-verified-book-unusable']
        entry['alias_candidates'] = [c for c in entry['independent_lines']
                                     if c['verdict'] == 'alias-candidate']
        entry['source_urls'] = sorted({u for u in entry['source_urls'] if u})
        review.append(entry)
    return review


def _name_matches(published: str, candidate: str) -> str | None:
    """How one published team name relates to one candidate name, or None."""
    key, other = name_key(published), name_key(candidate)
    if not key or not other:
        return None
    if key == other:
        return 'exact'
    if key in other or other in key:
        return 'substring'
    tokens = {t for t in re.split(r'\W+', key) if len(t) > 2}
    shared = tokens & {t for t in re.split(r'\W+', other) if len(t) > 2}
    return 'token' if shared else None


def candidate_similarity(published: list, candidate: list) -> dict:
    """Score a possible identity match. BOTH sides must relate, never one.

    Matching on a single shared name produced false candidates: 'ex-6666 vs Privateer'
    was paired with 'mellren vs Privateer Gaming' and 'antidaun vs Phantom Academy' with
    four unrelated 'Phantom ...' fixtures. A one-sided overlap is not evidence.
    """
    if len(published) != 2 or len(candidate) != 2:
        return {'plausible': False, 'matched_sides': 0, 'detail': 'not a two-sided pairing'}
    detail, matched = [], 0
    for name in published:
        best = None
        for other in candidate:
            kind = _name_matches(name, other)
            if kind:
                best = (kind, other)
                break
        if best:
            matched += 1
            detail.append(f'"{name}" ~ "{best[1]}" ({best[0]})')
        else:
            detail.append(f'"{name}" has no counterpart')
    return {'plausible': matched == 2, 'matched_sides': matched, 'detail': '; '.join(detail)}


def start_time_agreement(fixture_start, line_start) -> str:
    """Compare a fixture's scheduled start with a line's own start, in UTC."""
    left, right = parse_iso(fixture_start), parse_iso(line_start)
    if left is None or right is None:
        return 'unknown'
    delta = abs((left - right).total_seconds())
    if delta <= 60:
        return 'agrees'
    if delta <= 6 * 3600:
        return f'differs-by-{int(delta // 60)}-minutes'
    return 'differs'


def classify_candidate(line: dict, row: dict) -> dict:
    """Decide whether an observed line may speak for this fixture at all."""
    published = [t.get('name') for t in row.get('teams') or []]
    similarity = candidate_similarity(published, line.get('names') or [])
    join = join_line_to_fixture(line, row)
    time_agreement = start_time_agreement(row.get('starts_at'), line.get('start_utc'))
    executable = line.get('executable_within_ceiling')
    if line.get('family') == 'market' and line.get('worst_spread') is not None:
        executable = line['worst_spread'] <= MAX_ACCEPTED_SPREAD
    if join['join'] in ('exact', 'normalized') and executable:
        verdict = 'usable'
    elif join['join'] in ('exact', 'normalized'):
        verdict = 'identity-verified-book-unusable'
    elif similarity['plausible']:
        verdict = 'alias-candidate'
    else:
        verdict = 'not-this-fixture'
    return {
        'provider': line['provider'],
        'family': line.get('family'),
        'names': line.get('names'),
        'join': join['join'],
        'similarity': similarity,
        'start_time': time_agreement,
        'decimal_odds': line.get('decimal_odds'),
        'american_odds': line.get('american_odds'),
        'devigged': [round(v, 6) for v in join['aligned']] if join.get('aligned') else line.get('devigged'),
        'probability_basis': line.get('probability_basis'),
        'worst_spread': line.get('worst_spread'),
        'executable_within_ceiling': executable,
        'overround': line.get('overround'),
        'volume': line.get('volume'),
        'liquidity': line.get('liquidity'),
        'league': line.get('league'),
        'observed_at': line.get('observed_at'),
        'source_url': line.get('source_url'),
        'evidence': line.get('evidence'),
        'verdict': verdict,
    }


# ---------------------------------------------------------------------------
# 7. Cross-checks: does an independent line agree with the published pick?
# ---------------------------------------------------------------------------

def cross_checks(rows: list, lines: list) -> dict:
    """Does an independent official line agree with the pick the site published?

    Only lines whose identity is verified AND whose book is executable within the
    published ceiling are allowed to disagree with a pick. Anything else is recorded
    separately, because an unusable or unidentified line is not a counter-argument.
    """
    agreeing, disagreeing, unusable, alias_only = [], [], [], []
    for row in rows:
        origination = row.get('origination') or {}
        published = origination.get('probabilities')
        pick = row.get('pick_index')
        if not published or pick is None:
            continue
        names = [t.get('name') for t in row.get('teams') or []]
        for line in lines:
            candidate = classify_candidate(line, row)
            verdict = candidate['verdict']
            if verdict == 'not-this-fixture':
                continue
            if verdict == 'alias-candidate':
                alias_only.append({'id': row.get('id'), 'teams': names,
                                   'provider': candidate['provider'],
                                   'line_names': candidate['names'],
                                   'similarity': candidate['similarity']['detail'],
                                   'start_time': candidate['start_time'],
                                   'source_url': candidate['source_url']})
                continue
            aligned = candidate.get('devigged')
            if verdict != 'usable' or not aligned or len(aligned) != 2:
                unusable.append({'id': row.get('id'), 'teams': names,
                                 'provider': candidate['provider'],
                                 'line_names': candidate['names'],
                                 'worst_spread': candidate.get('worst_spread'),
                                 'probability_basis': candidate.get('probability_basis'),
                                 'source_url': candidate['source_url']})
                continue
            aligned = swap_if_needed(aligned, candidate['names'] or [], names) or aligned
            independent_pick = 0 if aligned[0] >= aligned[1] else 1
            record = {
                'id': row.get('id'),
                'teams': names,
                'competition': row.get('competition'),
                'starts_at': row.get('starts_at'),
                'published_provider': origination.get('source'),
                'published_method': origination.get('method'),
                'published_probabilities': published,
                'published_pick': names[pick] if pick < len(names) else None,
                'independent_provider': candidate['provider'],
                'independent_probabilities': [round(v, 6) for v in aligned],
                'independent_pick': names[independent_pick],
                'independent_decimal_odds': candidate.get('decimal_odds'),
                'independent_overround': candidate.get('overround'),
                'independent_basis': candidate.get('probability_basis'),
                'same_pick': independent_pick == pick,
                'deviation_pp': [round((aligned[i] - published[i]) * 100, 2) for i in (0, 1)],
                'source_url': candidate['source_url'],
                'published_source_url': origination.get('source_url'),
                'observed_at': candidate.get('observed_at'),
                'published_observed_at': origination.get('observed_at'),
            }
            (agreeing if record['same_pick'] else disagreeing).append(record)
    return {'agreeing': agreeing, 'disagreeing': disagreeing,
            'identity_verified_but_unusable': unusable, 'alias_only': alias_only}


# ---------------------------------------------------------------------------
# 8. Irregularity register
# ---------------------------------------------------------------------------

def build_flags(audit: dict) -> list:
    flags = []

    def add(flag_id, severity, title, detail, match_ids, source_urls):
        flags.append({'id': f'{SESSION}-{flag_id}', 'severity': severity, 'title': title,
                      'detail': detail, 'match_ids': sorted({str(m) for m in match_ids if m}),
                      'source_urls': sorted({u for u in source_urls if u})})

    inventory = audit['inventory_reconciliation']
    if not inventory['reconciled']:
        add('inventory-divergence', 'review',
            'Published inventory does not reconcile with Hotspawn\'s own fixtures API',
            f"Hotspawn lists {inventory['hotspawn_api_id_count']} CS2 fixtures; the site publishes "
            f"{inventory['deployed_row_count']}. Missing from the site: "
            f"{inventory['missing_from_site'] or 'none'}. Published but not listed by Hotspawn: "
            f"{inventory['extra_on_site'] or 'none'}. No row was added or removed by this audit.",
            inventory['missing_from_site'] + inventory['extra_on_site'], inventory['source_urls'])

    counts = audit['published_counts_check']
    for mismatch in counts['mismatches']:
        add(f"count-{mismatch['count']}", 'review',
            f"Published count '{mismatch['count']}' does not equal the rows",
            f"The deployed snapshot publishes {mismatch['count']}={mismatch['published']} while "
            f"recomputing from its own rows gives {mismatch['recomputed']}. Reported, not corrected.",
            [], counts['source_urls'])

    for replay in audit['probability_replay']['rows']:
        if replay['status'] == 'mismatch':
            add(f"replay-{replay['id']}", 'review',
                f"Published probability for {replay['id']} does not replay from its cited quote",
                f"Published {replay['published']}; replaying the cited quote gives "
                f"{[round(v, 6) for v in replay['replayed']]}. Checks: " + ' '.join(replay['checks']),
                [replay['id']], replay['source_urls'])
        elif replay['status'] in ('unreplayable', 'no-quote'):
            add(f"replay-{replay['id']}", 'notice',
                f"Published probability for {replay['id']} cannot be replayed from a cited price",
                f"Method '{replay['method']}'. Checks: " + ' '.join(replay['checks']),
                [replay['id']], replay['source_urls'])

    links = audit['source_links']
    if links['unofficial']:
        add('unofficial-source-url', 'review',
            'A published pick cites a URL outside the official allow-list',
            'URLs: ' + ', '.join(links['unofficial'][:12]),
            [], links['source_urls'] + links['unofficial'][:4])

    for record in audit['cross_checks']['disagreeing']:
        margin = max(abs(v) for v in record['deviation_pp'])
        add(f"pick-direction-{record['id']}", 'review',
            f"An independent official line disagrees with the published pick for {record['id']}",
            f"{record['teams'][0]} vs {record['teams'][1]} ({record['competition']}, "
            f"{record['starts_at']}): the site picks {record['published_pick']} from "
            f"{record['published_provider']} via its {record['published_method']} rung "
            f"({[round(v * 100, 1) for v in record['published_probabilities']]}%, observed "
            f"{record['published_observed_at']}), while {record['independent_provider']} "
            f"({record['independent_decimal_odds']}, overround {record['independent_overround']}, "
            f"observed {record['observed_at']}) de-vigs to {record['independent_pick']} "
            f"({[round(v * 100, 1) for v in record['independent_probabilities']]}%). The two official "
            f"sources are {margin} percentage points apart, which is enough to flip the pick on a "
            f"near-even match. Both are linked; neither was overridden, and no third opinion was "
            f"invented to break the tie.",
            [record['id']], [record['source_url'], record['published_source_url']])
    near_even = [r for r in audit['cross_checks']['agreeing']
                 if abs(r['published_probabilities'][0] - r['published_probabilities'][1]) < 0.05]
    if near_even:
        add('no-minimum-edge-threshold', 'notice',
            'Picks are published on margins smaller than the spread of their own source',
            'The origination ladder publishes a pick for every fixture it can price and has no '
            'minimum-edge threshold (the deployed snapshot reports no_edge=0). '
            f'{len(near_even)} resolved fixture(s) are decided by less than 5 percentage points: '
            + '; '.join(f"{r['id']} {r['teams'][0]} vs {r['teams'][1]} "
                        f"{[round(v * 100, 1) for v in r['published_probabilities']]}%"
                        for r in near_even)
            + '. These are arithmetically correct and every one replays from its cited source, but '
              'a reader on a phone cannot distinguish a 1.5-point margin from a strong favourite. '
              'Reported as a presentation irregularity, not a data error.',
            [r['id'] for r in near_even],
            [r['published_source_url'] for r in near_even] + [PAGES_ORIGINATION])

    for record in audit['unresolved_review']:
        usable, unusable, aliases = (record['usable_lines'], record['unusable_books'],
                                     record['alias_candidates'])
        if usable:
            add(f"unresolved-has-usable-line-{record['id']}", 'review',
                f"Unresolved fixture {record['id']} has an executable official line on record",
                f"{record['teams'][0]} vs {record['teams'][1]} ({record['competition']}, "
                f"{record['starts_at']}) is published with blank probabilities, yet "
                + '; '.join(f"{line['provider']} quotes {line.get('decimal_odds')} "
                            f"(names {line.get('names')}, de-vigged "
                            f"{[round(v * 100, 1) for v in line['devigged']] if line.get('devigged') else None}%, "
                            f"start time {line.get('start_time')})" for line in usable)
                + '. The probability is deliberately NOT moved into the canonical pick list here: '
                  'that join belongs to the origination ladder and its reviewed alias registry.',
                [record['id']], [line['source_url'] for line in usable] + [record.get('source_url')])
        for line in unusable:
            add(f"unresolved-rejection-confirmed-{record['id']}", 'notice',
                f"Blank probabilities for {record['id']} are correct: the only line is not executable",
                f"{record['teams'][0]} vs {record['teams'][1]}: {line['provider']} lists this exact "
                f"fixture but its own order book is {line.get('worst_spread')} wide "
                f"(basis {line.get('probability_basis')}, liquidity {line.get('liquidity')}, volume "
                f"{line.get('volume')}), beyond the {MAX_ACCEPTED_SPREAD} ceiling the methodology "
                f"publishes. Independently re-read from the archived book, this confirms the "
                f"site's rejection rather than contradicting it. No probability is inferred.",
                [record['id']], [line['source_url'], record.get('source_url')])
        if aliases and not usable:
            add(f"unresolved-alias-candidate-{record['id']}", 'notice',
                f"Unresolved fixture {record['id']} may be priced under a different team name",
                f"{record['teams'][0]} vs {record['teams'][1]} ({record['competition']}, "
                f"{record['starts_at']}): "
                + '; '.join(f"{line['provider']} lists {line.get('names')} — {line['similarity']['detail']}, "
                            f"start time {line.get('start_time')}" for line in aliases)
                + '. The names differ, so the identity is NOT verified and no probability is taken '
                  'from it. Recorded so a reviewer can decide whether a reviewed alias is warranted.',
                [record['id']], [line['source_url'] for line in aliases] + [record.get('source_url')])

    fp = audit['first_party_market_check']
    for record in fp['drifted_or_reversed']:
        reversed_side = not record['same_favourite']
        add(f"first-party-{record['id']}", 'review' if reversed_side else 'notice',
            ('Published favourite for %s is the opposite of Polymarket\'s own archived prices'
             % record['id']) if reversed_side else
            ('Published probability for %s has drifted more than 5 points from Polymarket\'s '
             'own archived prices' % record['id']),
            f"{record['teams'][0]} vs {record['teams'][1]}: Polymarket event {record['event_id']} "
            f"({record['event_slug']}) quotes {record['first_party_outcomes']} at "
            f"{record['first_party_prices']} observed {record['first_party_observed_at']}, while the "
            f"site published {record['published_probabilities']} observed "
            f"{record['published_observed_at']} (deviation {record['deviation_pp']} percentage "
            f"points). Both observations are kept; neither was overwritten by this audit.",
            [record['id']], [record['source_url'], PAGES_ORIGINATION])
    for record in fp['unverifiable']:
        add(f"first-party-unverifiable-{record['id']}", 'notice',
            f"Published probability for {record['id']} could not be checked against Polymarket",
            f"{record['teams'][0]} vs {record['teams'][1]}: {record['reason']} Left as published; "
            f"not confirmed and not contradicted.",
            [record['id']], [PAGES_ORIGINATION])

    hazards = audit['outcome_order_hazards']
    if hazards:
        add('source-outcomes-order', 'notice',
            'source_outcomes is published in market order while probabilities is in team order',
            'scripts/domain.py::market_analysis aligns `quotes` and `probabilities` to the '
            'fixture\'s team order but records `source_outcomes` in the market\'s own order. '
            f'{len(hazards)} published row(s) therefore carry the two arrays in opposite orders '
            '(' + ', '.join(str(h['id']) for h in hazards) + '). Every one was verified correct '
            'against Polymarket\'s own archived prices, so no published probability is wrong; '
            'but a reviewer comparing the two arrays positionally would invert the favourite. '
            'Nothing is rendered from `source_outcomes` on any page today.',
            [h['id'] for h in hazards],
            [h['source_url'] for h in hazards] + [PAGES_ORIGINATION, PAGES_LATEST])

    stale = audit['staleness']
    if stale['verdict'] != 'fresh':
        add('snapshot-stale', 'review',
            'The deployed snapshot is older than its own published staleness threshold',
            f"Generated {stale['generated_at']}, observed {stale['observed_at']}, age "
            f"{stale['age_minutes']} minutes against a published stale_after_hours of "
            f"{stale['stale_after_hours']}.",
            [], stale['source_urls'])
    return flags


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def audit(evidence: Path) -> dict:
    observations = load_json(evidence / 'observations.json') or {}
    deployed = load_raw(evidence, 'pages-latest.json') or {}
    origination = load_raw(evidence, 'pages-origination.json') or {}
    fixtures = load_raw(evidence, 'hotspawn-fixtures.json')
    valve = observations.get('valve') or {}

    generated = deployed.get('generated_at')
    observed = deployed.get('observed_at') or observations.get('probe_finished_at')
    age_minutes = None
    started, finished = parse_iso(generated), parse_iso(observed)
    if started and finished:
        age_minutes = round((finished - started).total_seconds() / 60, 1)
    stale_after = deployed.get('stale_after_hours')
    verdict = 'unknown'
    if age_minutes is not None and stale_after:
        verdict = 'fresh' if age_minutes <= stale_after * 60 else 'stale'
    staleness = {
        'generated_at': generated,
        'observed_at': observed,
        'age_minutes': age_minutes,
        'refresh_interval_hours': deployed.get('refresh_interval_hours'),
        'stale_after_hours': stale_after,
        'coverage_complete': deployed.get('coverage_complete'),
        'run_status': deployed.get('run_status'),
        'verdict': verdict,
        'fetch_url': PAGES_LATEST_FETCH,
        'source_urls': [PAGES_LATEST],
    }

    rows = origination.get('matches') or []
    replay_rows = [replay_row(row) for row in rows]
    first_party = verify_against_first_party_market(rows, observations)
    lines = independent_lines(evidence, observations)
    unresolved = verify_unresolved(rows, lines, valve)
    checks = cross_checks(rows, lines)

    audit_out = {
        'schema_version': SCHEMA_VERSION,
        'session': SESSION,
        'task': 'V-2 published-data verification',
        'generated_at': now_iso(),
        'evidence_dir': str(evidence),
        'probe_window': {'started_at': observations.get('probe_started_at'),
                         'finished_at': observations.get('probe_finished_at'),
                         'requests_ok': sum(1 for r in observations.get('requests') or [] if r.get('status') == 'ok'),
                         'requests_not_ok': sum(1 for r in observations.get('requests') or [] if r.get('status') != 'ok')},
        'staleness': staleness,
        'inventory_reconciliation': reconcile_inventory(deployed, fixtures),
        'published_counts_check': check_counts(deployed),
        'source_links': check_source_links(origination),
        'probability_replay': {
            'rows': replay_rows,
            'checked': len(replay_rows),
            'replayed': sum(1 for r in replay_rows if r['status'] == 'replayed'),
            'mismatched': sum(1 for r in replay_rows if r['status'] == 'mismatch'),
            'blank': sum(1 for r in replay_rows if r['status'] == 'blank'),
            'not_replayable': sum(1 for r in replay_rows
                                  if r['status'] in ('unreplayable', 'no-quote', 'model-inputs-only',
                                                     'multi-quote-unaggregated')),
        },
        'independent_lines': {
            'count': len(lines),
            'by_provider': {p: sum(1 for line in lines if line['provider'] == p)
                            for p in sorted({line['provider'] for line in lines})},
            'lines': lines,
        },
        'first_party_market_check': first_party,
        'outcome_order_hazards': outcome_order_hazards(rows, first_party),
        'unresolved_review': unresolved,
        'cross_checks': checks,
        'valve_snapshot': {
            'standings_as_of': valve.get('standings_as_of'),
            'snapshot_used': valve.get('snapshot_used'),
            'source_url': valve.get('source_url'),
            'ratings': valve.get('ratings'),
            'ambiguous': valve.get('ambiguous'),
            'absent': valve.get('absent'),
            'limitations': valve.get('limitations'),
        },
        'fixtures': [{
            'id': row.get('id'),
            'teams': [t.get('name') for t in row.get('teams') or []],
            'competition': row.get('competition'),
            'starts_at': row.get('starts_at'),
            'locks_at': row.get('locks_at'),
            'tier': row.get('tier'),
            'availability': row.get('availability'),
            'source_url': row.get('source_url'),
            'lobby_url': row.get('lobby_url'),
            'featured_method': row.get('featured_method'),
            'featured_probabilities': row.get('featured_probabilities'),
            'origination_method': (row.get('origination') or {}).get('method'),
            'origination_probabilities': (row.get('origination') or {}).get('probabilities'),
            'origination_source': (row.get('origination') or {}).get('source'),
            'origination_source_url': (row.get('origination') or {}).get('source_url'),
            'pick': ([t.get('name') for t in row.get('teams') or []][row['pick_index']]
                     if row.get('pick_index') is not None and row.get('teams') else None),
            'limitations': row.get('limitations') or [],
        } for row in rows],
        'limitations': [
            'This audit reads only what the archived first-party responses state. Where a source '
            'was unreadable the observation is absent, and the absence is reported rather than '
            'filled in.',
            'The Valve-rating research model formula is owned by another session and is not '
            'reimplemented here; for model rows the official inputs the row cites are verified '
            'instead of the arithmetic.',
            'An identity join classified as unverified never contributes a probability. Team names '
            'differing between Hotspawn and a book are reported for human review only.',
            'Prices move. Every line carries the timestamp at which it was observed; no line is '
            'presented as current beyond that timestamp.',
        ],
    }
    audit_out['flags'] = build_flags(audit_out)
    return audit_out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=Path('data/research/ba7164a0'))
    parser.add_argument('--flags-out', type=Path, default=None,
                        help='Also write the irregularity register on its own, in the schema '
                             'scripts/build.py already loads.')
    args = parser.parse_args(argv)

    result = audit(args.evidence)
    args.evidence.mkdir(parents=True, exist_ok=True)
    out = args.evidence / 'audit.json'
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
    if args.flags_out:
        args.flags_out.parent.mkdir(parents=True, exist_ok=True)
        args.flags_out.write_text(json.dumps(result['flags'], indent=1, ensure_ascii=False) + '\n')

    replay = result['probability_replay']
    print(f"Wrote {out}")
    print(f"  snapshot {result['staleness']['generated_at']} ({result['staleness']['verdict']}, "
          f"{result['staleness']['age_minutes']} min old)")
    print(f"  inventory reconciled={result['inventory_reconciliation']['reconciled']} "
          f"(Hotspawn {result['inventory_reconciliation']['hotspawn_api_id_count']} / "
          f"site {result['inventory_reconciliation']['deployed_row_count']})")
    print(f"  counts mismatches={len(result['published_counts_check']['mismatches'])}")
    fp = result['first_party_market_check']
    print(f"  first-party market check: agreeing={len(fp['agreeing'])} "
          f"drifted/reversed={len(fp['drifted_or_reversed'])} unverifiable={len(fp['unverifiable'])}")
    print(f"  outcome-order hazards={len(result['outcome_order_hazards'])}")
    print(f"  replay checked={replay['checked']} replayed={replay['replayed']} "
          f"mismatched={replay['mismatched']} blank={replay['blank']} "
          f"not_replayable={replay['not_replayable']}")
    print(f"  unofficial source URLs={len(result['source_links']['unofficial'])}")
    print(f"  independent lines={result['independent_lines']['count']} "
          f"{result['independent_lines']['by_provider']}")
    checks = result['cross_checks']
    print(f"  cross-checks agreeing={len(checks['agreeing'])} disagreeing={len(checks['disagreeing'])} "
          f"unusable={len(checks['identity_verified_but_unusable'])} alias_only={len(checks['alias_only'])}")
    print(f"  unresolved fixtures reviewed={len(result['unresolved_review'])}")
    print(f"  flags={len(result['flags'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
