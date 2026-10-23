"""Smarkets exchange prices for CS2 series winners (sessions arena-46ade650 & arena-80c3b4e0).

Why this source
---------------
The brief asks for a pick for **every** Hotspawn CS2 fixture, including the
low-tier matches that Polymarket, Kalshi and the big sportsbooks do not list. The
reviewed ladder used to fall back to a rating or results model for those
fixtures. [Smarkets](https://smarkets.com/sport/esports/cs-go) is a regulated
betting exchange that publishes a **public, documented** read-only API
([docs.smarkets.com](https://docs.smarkets.com/)) and lists CS2 (``csgo_match``)
matches, including academy and tier-3 events such as CCT Europe, NODWIN Clutch
Series and United21.

What is read
------------
* ``GET /v3/events/?type=csgo_match&states=upcoming`` — upcoming fixtures.
* ``GET /v3/events/{ids}/markets/`` — markets for the fixtures that bind.
* ``GET /v3/markets/{ids}/contracts/`` — the two WINNER_2_WAY contracts.
* ``GET /v3/markets/{ids}/quotes/`` — the exchange's best bid and best offer
  for each contract.

Smarkets quotes integer probabilities scaled by 10,000 (``4132`` is 0.4132), so
a contract's implied probability is ``price / 10000``. Only a fixture that binds
on **both** team names (either exact normalized names or competition-scoped
verified aliases in ``data/origination/aliases.json``) and a start time inside
the project-wide 60-second window is stored, and only a market that is two-way,
open, not in-play and quoted on both sides becomes a price row.

This module never writes a probability by itself: it saves the original API
responses under ``data/origination/evidence/`` and returns rows that
``scripts/originate.py`` re-validates (freshness, crossed books, spread
ceilings, competition-scoped alias alignment) exactly like every other exchange
row.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.domain import name_key, timestamp

UTC = timezone.utc
API = 'https://api.smarkets.com/v3'
SITE = 'https://smarkets.com'
SOURCE_URL = 'https://smarkets.com/sport/esports/cs-go'
DOCS = 'https://docs.smarkets.com/'
EVENT_TYPE = 'csgo_match'
EVIDENCE_NAME = 'live-smarkets-cs.json'
START_TOLERANCE_SEC = 60
QUOTE_SCALE = 10000
DEFAULT_ALIASES_PATH = Path(__file__).resolve().parent.parent / 'data' / 'origination' / 'aliases.json'


def events_url(limit: int = 200) -> str:
    return f'{API}/events/?type={EVENT_TYPE}&states=upcoming&limit={limit}&sort=start_datetime,id'


def event_url(event: dict) -> str:
    """The public page for one exchange event (never an API URL)."""
    slug = str(event.get('full_slug') or '')
    if slug.startswith('/'):
        return SITE + slug
    return f'{SITE}/event/{event.get("id")}'


def split_names(name: str) -> list[str]:
    """``"A vs B"`` -> ``["A", "B"]`` with the exchange's own spelling kept."""
    for marker in (' vs ', ' VS ', ' Vs '):
        if marker in str(name or ''):
            left, _, right = str(name).partition(marker)
            return [left.strip(), right.strip()]
    return []


def _load_default_registry(evidence_dir: Path) -> dict:
    """Load competition-scoped alias registry next to ``evidence_dir`` or direct file."""
    target = Path(evidence_dir)
    candidates = [target] if target.is_file() else [target.parent / 'aliases.json']
    repo_root = DEFAULT_ALIASES_PATH.parent.parent.resolve()
    try:
        target.resolve().relative_to(repo_root)
        candidates.append(DEFAULT_ALIASES_PATH)
    except ValueError:
        pass
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict) and isinstance(data.get('aliases'), list):
                return data
        except (OSError, ValueError, TypeError):
            continue
    return {'aliases': []}


def resolve_team(name: str, registry: dict | None, competition: str | None = None) -> tuple[str, list[dict]]:
    """Resolve an exchange team name using exact match or competition-scoped aliases.

    Mirrors ``scripts.originate.resolve_name`` so ``smarkets_lines.collect`` and
    ``originate.pair_join`` apply the exact same non-fuzzy, competition-scoped
    contract. When ``registry`` is ``None`` or empty, only exact normalized
    names match.
    """
    key = name_key(name)
    if not registry or not isinstance(registry.get('aliases'), list):
        return key, []
    comp_key = name_key(competition or '')
    pool = (registry['aliases'] if competition is None else
            [e for e in registry['aliases']
             if isinstance(e, dict) and comp_key in {name_key(s) for s in (e.get('applies_to') or [])}])
    for entry in pool:
        if not isinstance(entry, dict):
            continue
        excluded = {name_key(x) for x in (entry.get('must_not_match') or [])}
        if key in excluded:
            continue
        if key == name_key(entry.get('alias') or ''):
            used = [{
                'alias': entry.get('alias'),
                'canonical': entry.get('canonical'),
                'kind': entry.get('kind'),
                'applies_to': list(entry.get('applies_to') or []),
                'evidence': list(entry.get('evidence') or []),
            }]
            return name_key(entry.get('canonical') or ''), used
    return key, []


def _bind_detail(event: dict, match: dict, registry: dict | None = None) -> tuple[bool, list[dict]]:
    """Return ``(matched, aliases_used)`` under the 60-second prematch join contract."""
    names = split_names(event.get('name'))
    if len(names) != 2 or not all(names):
        return False, []
    wanted = [name_key(t.get('name') or '') for t in (match.get('teams') or []) if t.get('name')]
    if len(wanted) != 2 or len(set(wanted)) != 2:
        return False, []
    canon, aliases_used = [], []
    competition = match.get('competition')
    for raw_name in names:
        resolved, used = resolve_team(raw_name, registry, competition)
        canon.append(resolved)
        aliases_used.extend(used)
    if len(set(canon)) != 2 or set(canon) != set(wanted):
        return False, []
    start, fixture_start = timestamp(event.get('start_datetime')), timestamp(match.get('starts_at'))
    if start is None or fixture_start is None:
        return False, []
    if abs((start - fixture_start).total_seconds()) > START_TOLERANCE_SEC:
        return False, []
    return True, aliases_used


def binds(event: dict, match: dict, registry: dict | None = None) -> bool:
    """Both names match (exact, or competition-scoped alias when ``registry`` given) and start <= 60s."""
    matched, _ = _bind_detail(event, match, registry=registry)
    return matched


def collect(client, evidence_dir: Path, matches: list, registry: dict | None = None) -> dict:
    """Fetch and save the exchange board for the fixtures that bind.

    ``client`` is ``scripts.originate.Collector``. When ``registry`` is omitted
    (as in ``originate.collect_live``), the competition-scoped registry in
    ``data/origination/aliases.json`` is loaded automatically so verified
    spellings such as ``BakS eSports -> BakS`` or ``UNiTY esports -> UNiTY`` bind
    consistently with ``originate.pair_join``. Every HTTP failure is raised as
    ``RuntimeError`` by ``client`` and caught here so the four-hour pipeline
    never stalls when an external surface is unreachable.
    """
    active_registry = _load_default_registry(evidence_dir) if registry is None else registry
    observed_at = datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')
    document = {'source': 'Smarkets public exchange API', 'api': API, 'site': SITE,
                'docs': DOCS, 'event_type': EVENT_TYPE, 'observed_at': observed_at,
                'events_url': events_url(), 'bindings': [], 'events': [], 'markets': [],
                'contracts': [], 'quotes': {}, 'errors': []}
    try:
        body, _ = client.get_json(events_url(), 'live-smarkets-events', save=False)
    except RuntimeError as exc:
        document['errors'].append(str(exc)[:300])
        (evidence_dir / EVIDENCE_NAME).write_text(json.dumps(document, ensure_ascii=False) + '\n')
        return {'error': document['errors'][0], 'bound': 0}
    events = body.get('events') if isinstance(body, dict) else None
    if not isinstance(events, list):
        document['errors'].append('Smarkets events contract unrecognized')
        (evidence_dir / EVIDENCE_NAME).write_text(json.dumps(document, ensure_ascii=False) + '\n')
        return {'error': document['errors'][0], 'bound': 0}

    bound = []
    for match in matches:
        if match.get('availability') == 'past':
            continue
        hits = []
        for event in events:
            if not isinstance(event, dict):
                continue
            ok, aliases_used = _bind_detail(event, match, registry=active_registry)
            if ok:
                hits.append((event, aliases_used))
        if len(hits) != 1:
            # Zero hits means the exchange does not list it; more than one means
            # the identity is ambiguous. Neither may become a price.
            continue
        bound.append((match, hits[0][0], hits[0][1]))

    if not bound:
        (evidence_dir / EVIDENCE_NAME).write_text(json.dumps(document, ensure_ascii=False) + '\n')
        return {'bound': 0, 'events_seen': len(events)}

    event_ids = [str(e.get('id')) for _, e, _ in bound]
    try:
        markets_body, _ = client.get_json(f'{API}/events/{",".join(event_ids)}/markets/',
                                          'live-smarkets-markets', save=False)
        document['markets'] = [m for m in (markets_body or {}).get('markets', [])
                               if isinstance(m, dict)]
    except RuntimeError as exc:
        document['errors'].append(str(exc)[:300])
        document['markets'] = []

    by_event = {}
    for market in document['markets']:
        if ((market.get('market_type') or {}).get('name') != 'WINNER_2_WAY'
                or market.get('state') != 'open' or market.get('hidden') is True):
            continue
        by_event.setdefault(str(market.get('event_id')), []).append(market)

    market_ids = []
    for match, event, aliases_used in bound:
        markets = by_event.get(str(event.get('id'))) or []
        if len(markets) != 1:
            # Several markets for one event (specials, map winners) is ambiguous.
            document['errors'].append(
                f'{event.get("id")}: {len(markets)} open two-way winner markets; not priced')
            continue
        binding_record = {
            'hotspawn_id': match.get('id'),
            'event_id': str(event.get('id')),
            'market_id': str(markets[0].get('id')),
            'event_name': event.get('name'),
            'event_url': event_url(event),
            'start_datetime': event.get('start_datetime'),
        }
        if aliases_used:
            binding_record['aliases_used'] = aliases_used
        document['bindings'].append(binding_record)
        market_ids.append(str(markets[0].get('id')))

    if market_ids:
        joined = ','.join(market_ids)
        try:
            contracts_body, _ = client.get_json(f'{API}/markets/{joined}/contracts/',
                                                'live-smarkets-contracts', save=False)
            document['contracts'] = [c for c in (contracts_body or {}).get('contracts', [])
                                     if isinstance(c, dict)]
        except RuntimeError as exc:
            document['errors'].append(str(exc)[:300])
        try:
            quotes_body, _ = client.get_json(f'{API}/markets/{joined}/quotes/',
                                             'live-smarkets-quotes', save=False)
            document['quotes'] = quotes_body if isinstance(quotes_body, dict) else {}
        except RuntimeError as exc:
            document['errors'].append(str(exc)[:300])

    document['events'] = [e for _, e, _ in bound]
    Path(evidence_dir).mkdir(parents=True, exist_ok=True)
    (Path(evidence_dir) / EVIDENCE_NAME).write_text(json.dumps(document, ensure_ascii=False) + '\n')
    return {'bound': len(document['bindings']), 'events_seen': len(events),
            'quotes': len(document['quotes']), 'errors': document['errors'][:4]}


def _price(levels) -> float | None:
    """Best price from a Smarkets book side, converted to a 0-1 probability."""
    if not isinstance(levels, list) or not levels:
        return None
    raw = (levels[0] or {}).get('price')
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if not 0 < value < QUOTE_SCALE:
        return None
    return value / QUOTE_SCALE


def rows(evidence_dir: Path) -> list[dict]:
    """Price rows rebuilt from the saved original responses.

    Returns one row per binding whose market carries an open contract for both
    sides and a two-sided quote. Everything else is skipped — never defaulted —
    and the caller's own validation (freshness, spread, names) still applies.
    """
    path = Path(evidence_dir) / EVIDENCE_NAME
    if not path.exists():
        return []
    try:
        document = json.loads(path.read_text())
    except ValueError:
        return []
    contracts = {}
    for contract in document.get('contracts') or []:
        contracts.setdefault(str(contract.get('market_id')), []).append(contract)
    quotes = document.get('quotes') or {}
    events = {str(e.get('id')): e for e in document.get('events') or [] if isinstance(e, dict)}
    out = []
    for binding in document.get('bindings') or []:
        market_id = str(binding.get('market_id'))
        sides = contracts.get(market_id) or []
        if len(sides) != 2 or any(s.get('state_or_outcome') != 'open' for s in sides):
            continue
        # HOME first so the saved row reads in the exchange's own team order;
        # every join downstream aligns by name, never by position.
        sides.sort(key=lambda c: 0 if str((c.get('contract_type') or {}).get('name')) == 'HOME' else 1)
        names = [s.get('name') for s in sides]
        if not all(isinstance(n, str) and n.strip() for n in names):
            continue
        books = [quotes.get(str(s.get('id'))) or {} for s in sides]
        bid = [_price(book.get('bids')) for book in books]
        ask = [_price(book.get('offers')) for book in books]
        if any(v is None for v in bid + ask):
            continue
        event = events.get(str(binding.get('event_id'))) or {}
        out.append({
            'family': 'market', 'provider': 'Smarkets', 'names': names,
            'start': event.get('start_datetime'), 'bid': bid, 'ask': ask,
            'event_id': str(binding.get('event_id')), 'market_id': market_id,
            'fixture_id': binding.get('hotspawn_id'),
            'source_url': binding.get('event_url') or f'{SITE}/event/{binding.get("event_id")}',
            'api_url': f'{API}/markets/{market_id}/quotes/',
            'evidence_file': f'data/origination/evidence/{EVIDENCE_NAME}',
            'observed_at': document.get('observed_at'),
        })
    return out
