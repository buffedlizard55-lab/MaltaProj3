"""Originate an independently researched line and pick for every Hotspawn CS2 fixture.

The featured pipeline (scripts/collect.py) resolves picks with strict exact-name
joins. Fixtures it cannot resolve still deserve picks: this module researches
them the way the project brief asks — HLTV identity research first, then
esportsbook / betting-line sources (Polymarket series-winner markets, Thunderpick
match-winner prices), then an explicitly labeled Valve-rating research model.

Identity joins may use only the reviewed alias registry
(data/origination/aliases.json), where every alias carries official source
links. Nothing is fuzzy-matched and nothing is invented: values that cannot be
confirmed stay blank and are published as unresolved with the full research
trail.

Usage:
    python -m scripts.originate            # replay saved evidence (offline)
    python -m scripts.originate --live     # refetch first-party sources first
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from urllib.parse import urlencode

import requests

from scripts.domain import iso, name_key, no_vig, normalize_pair, timestamp, finite

UTC = timezone.utc
VALVE_RD = 75  # Fixed-RD assumption in Valve's published model/fit.js.
START_TOLERANCE_SEC = 60  # Provider clocks disagree up to ±30 min on delayed fixtures.
TIME_DISAGREEMENT_SEC = 60  # Beyond this, the disagreement is published as a flag.
MAX_PRICE_AGE_HOURS = 12
THIN_SPREAD = 0.12
MAX_ACCEPTED_SPREAD = 0.12

FIXTURES_API = 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?' + urlencode({'sport_alias': 'cs2', 'status': 'scheduled', 'tenantId': 1})
POLY_INDEX = 'https://polymarket.com/esports/cs2'
POLY_EVENTS = 'https://gamma-api.polymarket.com/events/'
CLOB_BOOK = 'https://clob.polymarket.com/book?token_id='
THUNDERPICK_API = 'https://thunderpick.io/api/matches'
THUNDERPICK_PAGE = 'https://thunderpick.io/esports/counter-strike'
VALVE_REPO = 'https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings'
HLTV_EVENT = 'https://www.hltv.org/events/9332/elisa-breakout-series-2'


# ---------------------------------------------------------------------------
# Reviewed alias registry
# ---------------------------------------------------------------------------

def load_registry(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data.get('aliases'), list) or not data['aliases']:
        raise ValueError('Alias registry is empty or unrecognized')
    for entry in data['aliases']:
        if not entry.get('alias') or not entry.get('canonical') or not entry.get('evidence'):
            raise ValueError('Every alias needs alias, canonical and evidence links')
        for ev in entry['evidence']:
            if not str(ev.get('url', '')).startswith('https://'):
                raise ValueError('Alias evidence must carry an https source link')
    return data


def resolve_name(name: str, registry: dict) -> tuple[str, list]:
    """Map a provider display name to its canonical Hotspawn-side name.

    Returns (canonical_name, alias_records). Exact names pass through. An alias
    applies only when the provider name is not in that alias's must_not_match
    list. No fuzzy matching.
    """
    key = name_key(name)
    used = []
    for entry in registry['aliases']:
        excluded = {name_key(x) for x in entry.get('must_not_match', [])}
        if key in excluded:
            continue
        if key == name_key(entry['alias']):
            used.append({'alias': entry['alias'], 'canonical': entry['canonical'], 'kind': entry['kind'],
                         'evidence': entry['evidence']})
            return name_key(entry['canonical']), used
    return key, used


def pair_join(source_names: list, source_start, match: dict, registry: dict) -> tuple[list | None, list, str]:
    """Try to join a provider two-team row onto a Hotspawn fixture.

    Returns (aligned_values_placeholder None, alias_records, status) where
    status is one of 'matched', 'names', 'time'.
    """
    if len(source_names) != 2 or not all(isinstance(n, str) and n.strip() for n in source_names):
        return None, [], 'names'
    canon, used = [], []
    for n in source_names:
        c, u = resolve_name(n, registry)
        canon.append(c)
        used.extend(u)
    wanted = [name_key(t['name']) for t in match['teams'] if t.get('name')]
    if len(wanted) != 2 or set(canon) != set(wanted) or len(set(canon)) != 2:
        return None, [], 'names'
    if used and name_key(match.get('competition') or '') not in {'elisa breakout series #2', 'elisa breakout series 2'}:
        return None, [], 'names'
    dt, md = timestamp(source_start), timestamp(match.get('starts_at'))
    if dt is None or md is None:
        return None, used, 'time'
    delta = abs((dt - md).total_seconds())
    if delta > START_TOLERANCE_SEC:
        return None, used, 'time'
    return [canon, [name_key(n) for n in source_names]], used, 'matched'


def align_by_name(values: list, source_names: list, match: dict, registry: dict) -> list:
    mapping = {}
    for value, name in zip(values, source_names):
        canon, _ = resolve_name(name, registry)
        mapping[canon] = value
    out = []
    for team in match['teams']:
        key = name_key(team['name'])
        if key not in mapping:
            raise ValueError('Outcome mapping incomplete')
        out.append(mapping[key])
    return out


# ---------------------------------------------------------------------------
# First-party collection (live mode)
# ---------------------------------------------------------------------------

class Collector:
    def __init__(self, evidence_dir: Path):
        self.dir = evidence_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'HotspawnCS2Origination/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)', 'Accept': 'application/json'})
        self.requests = []
        self.last = 0.0

    def save(self, label: str, data) -> str:
        path = self.dir / f'{label}.json'
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        return path.name

    def fetch_html(self, url: str, label: str):
        delay = 0.25 - (time.monotonic() - self.last)
        if delay > 0:
            time.sleep(delay)
        self.last = time.monotonic()
        entry = {'id': label, 'url': url, 'method': 'GET', 'observed_at': iso(datetime.now(UTC)), 'status': 'error'}
        self.requests.append(entry)
        try:
            response = self.session.get(url, timeout=(15, 45))
            entry.update(http_status=response.status_code,
                         response_sha256=hashlib.sha256(response.content).hexdigest())
            response.raise_for_status()
            entry['status'] = 'ok'
            path = self.dir / f'{label}.html'
            path.write_text(response.text)
            entry['evidence'] = path.name
            return response.text, entry
        except requests.RequestException as exc:
            entry['error'] = str(exc)[:300]
            raise RuntimeError(f'{label}: {entry["error"]}') from exc

    def get_json(self, url: str, label: str, *, method='GET', payload=None):
        delay = 0.25 - (time.monotonic() - self.last)
        if delay > 0:
            time.sleep(delay)
        self.last = time.monotonic()
        entry = {'id': label, 'url': url, 'method': method, 'observed_at': iso(datetime.now(UTC)), 'status': 'error'}
        self.requests.append(entry)
        try:
            response = self.session.request(method, url, json=payload, timeout=(15, 45))
            entry.update(http_status=response.status_code,
                         response_sha256=hashlib.sha256(response.content).hexdigest())
            response.raise_for_status()
            data = response.json()
            entry['status'] = 'ok'
            entry['evidence'] = self.save(label, data)
            return data, entry
        except (requests.RequestException, ValueError) as exc:
            entry['error'] = str(exc)[:300]
            raise RuntimeError(f'{label}: {entry["error"]}') from exc


def live_collect(evidence_dir: Path, matches: list, registry: dict) -> dict:
    """Refetch every first-party source used by the origination ladder.

    Polymarket discovery reuses the pipeline's public HTML decoder; events and
    order books are fetched for every game that joins an active fixture through
    exact names or the verified alias registry, so aliased low-tier matches get
    fresh books even though the featured pipeline skips them.
    """
    client = Collector(evidence_dir)
    out = {'requests': [], 'observed_at': iso(datetime.now(UTC))}
    try:
        body, _ = client.get_json(THUNDERPICK_API, 'live-thunderpick-matches', method='POST', payload={'gameIds': [6]})
        out['thunderpick'] = body
    except RuntimeError as exc:
        out['thunderpick_error'] = str(exc)
    games = []
    try:
        html_text, _ = client.fetch_html(POLY_INDEX, 'live-polymarket-index')
        from scripts.sources import polymarket_games
        games = polymarket_games(html_text)
        out['polymarket_games'] = len(games)
    except (RuntimeError, ValueError) as exc:
        out['polymarket_index_error'] = str(exc)
    active = [m for m in matches if m.get('availability') != 'past' and m.get('analysis') is None]
    events = []
    books = []
    for game in games:
        names = [game.get('homeName', ''), game.get('awayName', '')]
        joined = any(pair_join(names, game.get('startTime'), m, registry)[2] == 'matched' for m in active)
        if not joined:
            continue
        try:
            event, _ = client.get_json(POLY_EVENTS + str(game['id']), 'live-polymarket-event-' + str(game['id']))
        except RuntimeError as exc:
            continue
        if event.get('active') is not True or event.get('closed') is not False or event.get('live') is True:
            continue
        moneyline = None
        for market in event.get('markets', []):
            scope = market.get('sportsMarketType') or (market.get('sports') or {}).get('sports_market_type')
            if scope == 'moneyline' and market.get('active') is True and market.get('closed') is False and market.get('acceptingOrders') is True and str(market.get('question', '')).startswith('Counter-Strike:'):
                moneyline = market
                break
        if not moneyline:
            continue
        tokens = moneyline.get('clobTokenIds')
        if isinstance(tokens, str):
            try:
                tokens = json.loads(tokens)
            except ValueError:
                continue
        if not tokens or len(tokens) != 2:
            continue
        bid, ask = [], []
        for token in tokens:
            try:
                book, _ = client.get_json(CLOB_BOOK + str(token), 'live-polymarket-book-' + str(game['id']) + '-' + str(len(bid)))
            except RuntimeError:
                book = None
            if book is None:
                bid, ask = [], []
                break
            bids = [finite(x.get('price')) for x in book.get('bids', []) if finite(x.get('price')) is not None]
            asks = [finite(x.get('price')) for x in book.get('asks', []) if finite(x.get('price')) is not None]
            from scripts.domain import is_fresh
            stamp = timestamp(book.get('timestamp'))
            if not stamp or not is_fresh(iso(stamp), datetime.now(UTC)) or str(book.get('asset_id')) != str(token) or book.get('market') != moneyline.get('conditionId'):
                bid, ask = [], []
                break
            if not bids or not asks:
                bid, ask = [], []
                break
            bid.append(max(bids))
            ask.append(min(asks))
            books.append({'asset_id': str(token), 'best_bid': max(bids), 'best_ask': min(asks),
                          'last_trade_price': finite(book.get('last_trade_price')),
                          'source_url': CLOB_BOOK + str(token)})
        record = {
            'event_id': str(event.get('id')), 'slug': event.get('slug'), 'title': moneyline.get('question'),
            'source_url': POLY_EVENTS + str(event.get('id')),
            'public_page': 'https://polymarket.com/event/' + str(event.get('slug', '')),
            'observed_at': iso(datetime.now(UTC)), 'active': event.get('active'), 'closed': event.get('closed'),
            'moneyline_market_id': str(moneyline.get('id')),
            'outcomes': json.loads(moneyline['outcomes']) if isinstance(moneyline.get('outcomes'), str) else moneyline.get('outcomes'),
            'game_start_time': moneyline.get('gameStartTime') or event.get('startTime'),
            'clob_token_ids': [str(x) for x in tokens],
        }
        if len(bid) == 2:
            record['book_bid'] = bid
            record['book_ask'] = ask
        events.append(record)
    (evidence_dir / 'live-polymarket-observations.json').write_text(
        json.dumps({'observed_at': out['observed_at'], 'polymarket_events': events, 'polymarket_books': books},
                   ensure_ascii=False, indent=2) + '\n')
    try:
        now = datetime.now(UTC)
        directory, _ = client.get_json(f'{VALVE_REPO}/contents/live/{now.year}', 'live-valve-directory')
        names = []
        for entry in directory:
            m = re.fullmatch(r'standings_global_(\d{4})_(\d{2})_(\d{2})\.md', entry['name'])
            if m:
                day = '-'.join(m.groups())
                if day <= now.date().isoformat():
                    names.append((day, entry['path']))
        if names:
            day, path = max(names)
            content, _ = client.get_json(f'{VALVE_REPO}/contents/{path}', 'live-valve-standings')
            text = base64.b64decode(content['content']).decode('utf-8')
            (evidence_dir / 'live-valve-standings-text.json').write_text(
                json.dumps({'snapshot_date': day, 'source_url': content['html_url'],
                            'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'text': text},
                           ensure_ascii=False, indent=2) + '\n')
            out['valve'] = {'snapshot_date': day, 'source_url': content['html_url']}
    except RuntimeError as exc:
        out['valve_error'] = str(exc)
    out['requests'] = client.requests
    (evidence_dir / 'live-collection-manifest.json').write_text(json.dumps(out['requests'], ensure_ascii=False, indent=2) + '\n')
    return out


# ---------------------------------------------------------------------------
# Observation loading (replay from saved evidence)
# ---------------------------------------------------------------------------

def load_json(path: Path):
    return json.loads(path.read_text())


def thunderpick_rows(repo_data: Path, live: dict | None) -> list:
    rows = []
    if live and isinstance(live.get('thunderpick'), dict):
        body = (live['thunderpick'].get('data') or {})
        rows = body.get('upcoming') or body.get('matches') or []
        observed = next((r.get('observed_at') for r in live.get('requests', []) if r.get('id') == 'live-thunderpick-matches' and r.get('status') == 'ok'), None)
        source = ('data/origination/evidence/live-thunderpick-matches.json', observed)
    else:
        path = repo_data / 'evidence' / 'thunderpick-matches.json'
        if not path.exists():
            return []
        body = load_json(path)
        if isinstance(body, dict):
            inner = body.get('data') or {}
            rows = inner.get('upcoming') or inner.get('matches') or []
        snapshot = load_json(repo_data / 'latest.json')
        observed = next((r.get('observed_at') for r in snapshot.get('requests', []) if r.get('id') == 'thunderpick-matches' and r.get('status') == 'ok'), None)
        source = ('data/evidence/thunderpick-matches.json', observed)
    out = []
    for row in rows:
        teams = row.get('teams') or {}
        names = [(teams.get(k) or {}).get('name', '') for k in ['home', 'away']]
        market = row.get('market') or {}
        if name_key(market.get('name', '')) not in {'match winner', 'match winner incl. overtime', 'match winner inc. overtime'}:
            continue
        if row.get('gameId') != 6 or row.get('isLive') is not False or not row.get('id') or market.get('status') != 1 or market.get('draw') is not None:
            continue
        sides = [market.get(k) or {} for k in ['home', 'away']]
        if any(s.get('status') != 1 for s in sides):
            continue
        names = [s.get('name', '') for s in sides]
        odds = [finite(s.get('odds')) for s in sides]
        if any(o is None or o <= 1 for o in odds):
            continue
        if set(name_key(s.get('name', '')) for s in sides) != set(map(name_key, names)):
            continue
        out.append({'family': 'bookmaker', 'provider': 'Thunderpick', 'names': names,
                    'start': row.get('startTime'), 'odds': odds,
                    'event_id': str(row.get('id')), 'source_url': THUNDERPICK_PAGE, 'observed_at': source[1],
                    'api_url': THUNDERPICK_API, 'evidence_file': source[0]})
    return out


def polymarket_rows(repo_data: Path, orig_evidence: Path) -> list:
    """Build Polymarket market rows from saved pipeline evidence plus research fetches."""
    rows = []
    index_path = repo_data / 'evidence' / 'polymarket-index.json'
    games = load_json(index_path) if index_path.exists() else []
    by_id = {str(g.get('id')): g for g in games}
    # Events saved by the featured pipeline.
    for path in sorted((repo_data / 'evidence').glob('polymarket-event-*.json')):
        event = load_json(path)
        rows.extend(_rows_from_event(event, path.name, repo_data / 'evidence'))
    # Fresh aliased events captured by --live collection.
    live_path = orig_evidence / 'live-polymarket-observations.json'
    if live_path.exists():
        live = load_json(live_path)
        books = {b['asset_id']: b for b in live.get('polymarket_books', [])}
        for ev in live.get('polymarket_events', []):
            if ev.get('closed') is True or ev.get('active') is False:
                continue
            rows.extend(_rows_from_research_event(ev, books, 'data/origination/evidence/live-polymarket-observations.json'))
    # One row per event: fresh first-party observations override older saves.
    priority = {'live-polymarket-observations': 2, 'research-fetches': 1}
    by_event = {}
    for row in rows:
        rank = 0
        for key, value in priority.items():
            if key in (row.get('evidence_file') or ''):
                rank = value
        current = by_event.get(row['event_id'])
        if current is None or rank >= current[0]:
            by_event[row['event_id']] = (rank, row)
    return [entry[1] for entry in by_event.values()]


def _rows_from_event(event: dict, evidence_file: str, evidence_dir: Path) -> list:
    rows = []
    if event.get('closed') is not False or event.get('active') is not True:
        return rows
    for market in event.get('markets', []):
        scope = market.get('sportsMarketType') or (market.get('sports') or {}).get('sports_market_type')
        question = market.get('question', '')
        if scope != 'moneyline' and not re.match(r'Counter-Strike: .+ vs .+ \(BO\d\)', question):
            continue
        if re.search(r'\b(map\s*\d|game\s*\d|handicap|spread|total|outright|over/under)\b', question, re.I):
            continue
        outcomes = market.get('outcomes')
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except ValueError:
                outcomes = None
        tokens = market.get('clobTokenIds')
        if isinstance(tokens, str):
            try:
                tokens = json.loads(tokens)
            except ValueError:
                tokens = None
        if not outcomes or len(outcomes) != 2 or not tokens or len(tokens) != 2:
            continue
        start = market.get('gameStartTime') or event.get('startTime') or event.get('eventStartTime')
        bids, asks, ok = [], [], True
        for token in tokens:
            book_path = evidence_dir / f'polymarket-book-{event.get("id")}-{len(bids)}.json'
            if book_path.exists():
                book = load_json(book_path)
                from scripts.domain import is_fresh
                if not is_fresh(iso(timestamp(book.get('timestamp'))), datetime.now(UTC)) if timestamp(book.get('timestamp')) else True:
                    ok = False
                bid = max((finite(x.get('price')) for x in book.get('bids', []) if finite(x.get('price')) is not None), default=None)
                ask = min((finite(x.get('price')) for x in book.get('asks', []) if finite(x.get('price')) is not None), default=None)
                bids.append(bid)
                asks.append(ask)
                if bid is None or ask is None:
                    ok = False
            else:
                ok = False
        row = {'family': 'market', 'provider': 'Polymarket', 'names': [str(o) for o in outcomes],
               'start': start, 'event_id': str(event.get('id')), 'market_id': str(market.get('id')),
               'source_url': 'https://polymarket.com/event/' + str(event.get('slug', '')),
               'api_url': POLY_EVENTS + str(event.get('id')), 'evidence_file': evidence_file,
               'question': question}
        if ok and all(b is not None and a is not None for b, a in zip(bids, asks)):
            row['bid'] = bids
            row['ask'] = asks
        rows.append(row)
    return rows


def _rows_from_research_event(ev: dict, books: dict, evidence_file: str) -> list:
    row = {'family': 'market', 'provider': 'Polymarket', 'names': list(ev.get('outcomes', [])),
           'start': ev.get('game_start_time'), 'event_id': str(ev.get('event_id')),
           'market_id': str(ev.get('moneyline_market_id')),
           'source_url': ev.get('public_page'), 'api_url': ev.get('source_url'),
           'evidence_file': evidence_file,
           'question': ev.get('title', ''), 'observed_at': ev.get('observed_at')}
    if ev.get('book_bid') and ev.get('book_ask') and len(ev['book_bid']) == 2:
        row['bid'] = [float(x) for x in ev['book_bid']]
        row['ask'] = [float(x) for x in ev['book_ask']]
        return [row]
    bids, asks = [], []
    for token in ev.get('clob_token_ids', []):
        book = books.get(str(token))
        if not book or book.get('best_bid') is None or book.get('best_ask') is None:
            return [row]
        bids.append(float(book['best_bid']))
        asks.append(float(book['best_ask']))
    if len(bids) == 2:
        row['bid'] = bids
        row['ask'] = asks
    return [row]


def out_rows(rows: list) -> list:
    return rows


def valve_rows(repo_data: Path, live: dict | None) -> tuple[list | None, dict | None]:
    from scripts.domain import parse_valve_table
    if live and (repo_data / 'origination' / 'evidence' / 'live-valve-standings-text.json').exists():
        payload = load_json(repo_data / 'origination' / 'evidence' / 'live-valve-standings-text.json')
        rows = parse_valve_table(payload['text'], payload['source_url'], payload['snapshot_date'])
        return rows, {'source_url': payload['source_url'], 'snapshot_date': payload['snapshot_date'], 'evidence_file': 'data/origination/evidence/live-valve-standings-text.json'}
    path = repo_data / 'evidence' / 'valve-ratings.json'
    if not path.exists():
        return None, None
    payload = load_json(path)
    return payload['rows'], {'source_url': payload['source_url'], 'snapshot_date': payload['snapshot_date'], 'evidence_file': 'data/evidence/valve-ratings.json'}


# ---------------------------------------------------------------------------
# Origination ladder
# ---------------------------------------------------------------------------

def market_estimate(row: dict, match: dict, registry: dict, now: datetime):
    """Polymarket series-winner midpoint estimate; wide books are rejected."""
    from scripts.domain import is_fresh
    if row.get('observed_at') is not None and not is_fresh(row['observed_at'], now):
        return None, 'Market observation is stale'
    if row.get('bid') is not None and row.get('ask') is not None:
        mids, spreads = [], []
        for bid, ask in zip(row['bid'], row['ask']):
            if not (0 < bid <= ask < 1):
                return None, 'Crossed order book rejected'
            mids.append((bid + ask) / 2)
            spreads.append(round(ask - bid, 8))
        worst = max(spreads)
        if worst > MAX_ACCEPTED_SPREAD:
            return None, f'Order book spread {worst:.2f} exceeds the {MAX_ACCEPTED_SPREAD:.2f} indicative ceiling'
        probs = normalize_pair(*mids)
        thin = worst > THIN_SPREAD
        aligned = align_by_name(probs, row['names'], match, registry)
        quote = {'provider': 'Polymarket', 'family': 'market', 'probabilities': aligned,
                 'bid': align_by_name(row['bid'], row['names'], match, registry),
                 'ask': align_by_name(row['ask'], row['names'], match, registry),
                 'spread': worst, 'thin': thin, 'observed_at': row.get('observed_at'),
                 'source_url': row['source_url'], 'event_id': row['event_id'], 'evidence_file': row['evidence_file']}
        detail = ('Verified paired order-book midpoints.' if not thin else
                  f'THIN MARKET: best spread {worst:.2f} is wider than {THIN_SPREAD:.2f}; midpoint shown as indicative only.')
        return quote, detail
    if row.get('summary_mid') is not None:
        worst = float(row.get('summary_spread') or 0)
        if worst > MAX_ACCEPTED_SPREAD:
            return None, f'Provider top-of-book spread {worst:.2f} exceeds the {MAX_ACCEPTED_SPREAD:.2f} indicative ceiling'
        aligned = align_by_name(row['summary_mid'], row['names'], match, registry)
        quote = {'provider': 'Polymarket', 'family': 'market', 'probabilities': aligned,
                 'spread': worst, 'thin': worst > THIN_SPREAD, 'observed_at': row.get('observed_at'),
                 'source_url': row['source_url'], 'event_id': row['event_id'], 'evidence_file': row['evidence_file']}
        return quote, ('Provider top-of-book summary prices (both order-book sides were not saved at capture).'
                       + (' THIN MARKET indicator.' if worst > THIN_SPREAD else ''))
    return None, 'No paired executable prices in the saved response'


def bookmaker_estimate(row: dict, match: dict, registry: dict):
    from scripts.domain import is_fresh
    if not is_fresh(row.get('observed_at'), datetime.now(UTC)):
        return None, 'Bookmaker observation is missing or stale'
    try:
        probs = no_vig(row['odds'])
    except ValueError as exc:
        return None, str(exc)
    aligned = align_by_name(probs, row['names'], match, registry)
    odds = align_by_name(row['odds'], row['names'], match, registry)
    quote = {'provider': row['provider'], 'family': 'bookmaker', 'probabilities': aligned, 'odds': odds,
             'observed_at': row.get('observed_at'), 'source_url': row['source_url'],
             'api_url': row.get('api_url'), 'event_id': row['event_id'], 'evidence_file': row['evidence_file']}
    return quote, 'Verified paired prematch decimal prices; margin removed by proportional normalization.'


def model_estimate(match: dict, ratings: list, registry: dict, meta: dict, now: datetime):
    """Alias-aware Valve-rating research estimate (explicitly uncalibrated)."""
    if not ratings:
        return None, 'Official Valve ratings unavailable'
    by_name = {}
    for row in ratings:
        by_name.setdefault(name_key(row['name']), []).append(row)
    reverse = {}
    for entry in registry['aliases']:
        reverse.setdefault(name_key(entry['canonical']), []).append(name_key(entry['alias']))
    inputs = []
    used = []
    for team in match['teams']:
        team_key = name_key(team['name'])
        candidates = [team_key] + reverse.get(team_key, [])
        found = []
        matched_as = None
        for candidate in candidates:
            found = by_name.get(candidate) or []
            if found:
                matched_as = candidate
                break
        if len(found) != 1:
            return None, f'{team["name"]}: ' + ('multiple Valve rosters share this name' if found else 'no Valve rating row found (including registry aliases)')
        row = found[0]
        if name_key(row['name']) != team_key:
            used.append({'alias': row['name'], 'canonical': team['name'], 'kind': 'registry reverse lookup',
                         'evidence': [{'url': meta['source_url'], 'source': 'Valve official standings', 'detail': f'Valve publishes this roster under the name {row["name"]}; the reviewed alias registry links the two names.'}]})
        day = timestamp(row['snapshot_date'] + 'T00:00:00Z')
        if day is None or not 0 <= (now - day).total_seconds() <= 35 * 86400:
            return None, 'Valve snapshot is future-dated or older than 35 days'
        if len(row.get('roster') or []) != 5:
            return None, f'{team["name"]}: a complete five-player Valve roster is not confirmed'
        inputs.append(row)
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * VALVE_RD ** 2 / math.pi ** 2)
    p = 1 / (1 + 10 ** (g * (inputs[1]['points'] - inputs[0]['points']) / 400))
    probs = normalize_pair(p, 1 - p)
    quote = {'provider': 'Valve official standings', 'family': 'model', 'probabilities': probs,
             'inputs': [{'name': r['name'], 'points': r['points'], 'standing': r['standing'], 'roster': r['roster']} for r in inputs],
             'snapshot_date': meta['snapshot_date'], 'source_url': meta['source_url'],
             'evidence_file': meta['evidence_file'], 'rd_assumption': VALVE_RD, 'g': g,
             'aliases_used': used, 'observed_at': iso(now)}
    return quote, 'Alias-aware exact-name Valve rating rows; uncalibrated research model (Valve fit.js formula).'


def selection(probs) -> int | None:
    a, b = probs
    return None if abs(a - b) < 1e-8 else (0 if a > b else 1)


def originate_match(match: dict, poly_rows: list, book_rows: list, ratings, valve_meta, registry: dict, now: datetime) -> dict:
    trail = []
    aliases = []
    estimates = {'market': [], 'bookmaker': []}
    time_flags = []

    # 1. Identity + market rows (Polymarket).
    market_notes = []
    for row in poly_rows:
        joined, used, status = pair_join(row['names'], row['start'], match, registry)
        if status != 'matched':
            continue
        aliases.extend(used)
        if used:
            market_notes.append('joined via verified alias registry')
        delta = None
        if timestamp(row.get('start')) and timestamp(match.get('starts_at')):
            delta = abs((timestamp(row['start']) - timestamp(match['starts_at'])).total_seconds())
        if delta is not None and delta > TIME_DISAGREEMENT_SEC:
            time_flags.append(f'{row["provider"]} start time differs by {int(delta)}s')
        quote, detail = market_estimate(row, match, registry, now)
        if quote:
            estimates['market'].append((quote, detail))
        else:
            market_notes.append(detail)
    if estimates['market']:
        quote, detail = estimates['market'][0]
        trail.append({'stage': 'Betting market (Polymarket series winner)', 'status': 'resolved',
                      'source_url': quote['source_url'], 'detail': detail + (' ' + ' '.join(market_notes) if market_notes else '')})
    else:
        detail = market_notes[0] if market_notes else 'No alias-verified Polymarket series-winner market found for these teams and start time.'
        trail.append({'stage': 'Betting market (Polymarket series winner)', 'status': 'unresolved',
                      'source_url': POLY_INDEX, 'detail': detail})

    # 2. Esportsbook rows (Thunderpick).
    book_notes = []
    for row in book_rows:
        joined, used, status = pair_join(row['names'], row['start'], match, registry)
        if status != 'matched':
            continue
        aliases.extend(used)
        if timestamp(row.get('start')) and timestamp(match.get('starts_at')):
            delta = abs((timestamp(row['start']) - timestamp(match['starts_at'])).total_seconds())
            if delta > TIME_DISAGREEMENT_SEC:
                time_flags.append(f'{row["provider"]} start time differs by {int(delta)}s')
        quote, detail = bookmaker_estimate(row, match, registry)
        if quote:
            estimates['bookmaker'].append((quote, detail))
        else:
            book_notes.append(detail)
    if estimates['bookmaker']:
        quote, detail = estimates['bookmaker'][0]
        trail.append({'stage': 'Esportsbook line (original prices)', 'status': 'resolved',
                      'source_url': quote.get('api_url') or quote['source_url'], 'detail': detail})
    else:
        detail = book_notes[0] if book_notes else 'No alias-verified paired esportsbook prices for these teams and start time.'
        trail.append({'stage': 'Esportsbook line (original prices)', 'status': 'unresolved',
                      'source_url': THUNDERPICK_PAGE, 'detail': detail})

    # 3. Research model cross-check (always attempted, never overrides money lines).
    model, model_detail = model_estimate(match, ratings, registry, valve_meta or {}, now)
    if model:
        aliases.extend(model.get('aliases_used') or [])
        trail.append({'stage': 'Research model cross-check (Valve official ratings)', 'status': 'resolved',
                      'source_url': model['source_url'],
                      'detail': model_detail + ' Cross-check only unless no market or bookmaker line exists.'})
    else:
        trail.append({'stage': 'Research model cross-check (Valve official ratings)', 'status': 'unresolved',
                      'source_url': (valve_meta or {}).get('source_url', 'https://github.com/ValveSoftware/counter-strike_regional_standings'),
                      'detail': model_detail})

    # HLTV research stage (identity/rank context always recorded with its link).
    trail.append({'stage': 'HLTV research (identity and rankings)', 'status': 'checked',
                  'source_url': HLTV_EVENT,
                  'detail': 'HLTV lists this fixture under the event page with published team ranks. HLTV fan voting percentages are recorded nowhere as probability inputs; HLTV identity evidence feeds the alias registry only.'})

    # 4. Choose the originated line: consensus of money sources, else model.
    families = {}
    for quote, _ in estimates['market']:
        families.setdefault('market', quote)
    for quote, _ in estimates['bookmaker']:
        families.setdefault('bookmaker', quote)
    chosen = None
    method = None
    label = None
    limitations = []
    if families:
        probs_list = [q['probabilities'] for q in families.values()]
        p0 = median(pr[0] for pr in probs_list)
        probs = normalize_pair(p0, 1 - p0)
        sources = [q['provider'] for q in families.values()]
        thin = any(q.get('thin') for q in families.values())
        method = 'consensus' if len(families) > 1 else next(iter(families))
        label = ('Originated consensus line (median of independent money sources)' if len(families) > 1
                 else ('Originated market line (Polymarket)' if method == 'market' else 'Originated esportsbook line (no-vig)'))
        chosen = {'method': method, 'label': label, 'probabilities': probs,
                  'fair_decimal': [round(1 / p, 3) for p in probs],
                  'quotes': list(families.values()), 'source': ' + '.join(sources),
                  'source_url': list(families.values())[0]['source_url'],
                  'observed_at': min(q.get('observed_at') or iso(now) for q in families.values()),
                  'model_crosscheck': model}
        if thin:
            limitations.append('At least one contributing market is thin/wide; treat the estimate as indicative, not executable.')
        if len(families) == 1:
            limitations.append('Single independent source; not a multi-source consensus.')
        limitations.append('Margin removed where applicable. Estimate is not a guaranteed outcome.')
    elif model:
        chosen = dict(model)
        chosen.update({'method': 'model', 'label': 'Research model estimate (Valve official ratings)',
                       'fair_decimal': [round(1 / p, 3) for p in model['probabilities']],
                       'quotes': [model], 'source': 'Valve official standings',
                       'model_crosscheck': None})
        limitations.append('Research model, not observed betting odds. Uncalibrated; current lineups and map vetoes unverified.')
    else:
        trail.append({'stage': 'Origination result', 'status': 'unresolved',
                      'source_url': match.get('source_url') or POLY_INDEX,
                      'detail': 'No alias-verified market, bookmaker or rating input could be confirmed. The pick stays blank.'})
        limitations.append('No verified inputs; probabilities intentionally left blank (no default 50/50).')

    if time_flags:
        limitations.append('Provider start-time disagreement: ' + '; '.join(sorted(set(time_flags))) + '. Times are never silently overwritten.')
    pick = selection(chosen['probabilities']) if chosen else None
    deduped = []
    seen = set()
    for a in aliases:
        key = (a['alias'], a['canonical'])
        if key not in seen:
            seen.add(key)
            deduped.append(a)
    return {
        'origination': chosen,
        'pick_index': pick,
        'aliases_used': deduped,
        'research': trail,
        'limitations': limitations,
        'time_flags': sorted(set(time_flags)),
    }


def run(output: Path, *, live: bool = False) -> dict:
    output = Path(output)
    orig_dir = output / 'origination'
    evidence_dir = orig_dir / 'evidence'
    registry = load_registry(orig_dir / 'aliases.json')
    now = datetime.now(UTC)
    snapshot = load_json(output / 'latest.json')
    live_payload = live_collect(evidence_dir, snapshot['matches'], registry) if live else None
    poly_rows = polymarket_rows(output, evidence_dir)
    book_rows = thunderpick_rows(output, live_payload)
    ratings, valve_meta = valve_rows(output, live_payload)
    # Preserve original source observation timestamps. Never stamp retained quotes as new.
    for row in poly_rows:
        if not row.get('observed_at'):
            event_id = row.get('event_id')
            row['observed_at'] = next((r.get('observed_at') for r in snapshot.get('requests', []) if r.get('id') == 'polymarket-event-' + str(event_id) and r.get('status') == 'ok'), None)

    matches_out = []
    for match in snapshot['matches']:
        if match.get('availability') == 'past':
            continue
        featured = match.get('analysis')
        if featured:
            result = {'origination': dict(featured, quotes=[dict(q, source_url=q.get('source_url') or featured['source_url'], provider=q.get('provider') or featured['source'], family=q.get('family') or featured['method']) for q in featured.get('quotes', [])], model_crosscheck=None),
                      'pick_index': match.get('pick_index'), 'aliases_used': [],
                      'research': match.get('research', []), 'limitations': match.get('limitations', []), 'time_flags': []}
        else:
            result = originate_match(match, poly_rows, book_rows, ratings, valve_meta, registry, now)
        matches_out.append({
            'id': match['id'],
            'teams': match['teams'],
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'locks_at': match.get('locks_at'),
            'availability': match.get('availability'),
            'tier': match.get('tier'),
            'source_url': match.get('source_url'),
            'lobby_url': match.get('lobby_url'),
            'featured_method': featured.get('method') if featured else None,
            'featured_probabilities': featured.get('probabilities') if featured else None,
            'featured_pick_index': match.get('pick_index'),
            'featured_source_url': featured.get('source_url') if featured else None,
            **result,
        })
    matches_out.sort(key=lambda m: (m['starts_at'] or '9999', m['id']))

    unresolved = [m['id'] for m in matches_out if m['origination'] is None]
    counts = {
        'active': len(matches_out),
        'resolved': len(matches_out) - len(unresolved),
        'unresolved': len(unresolved),
        'with_pick': sum(m['pick_index'] is not None for m in matches_out),
        'consensus': sum((m['origination'] or {}).get('method') == 'consensus' for m in matches_out),
        'market': sum((m['origination'] or {}).get('method') == 'market' for m in matches_out),
        'bookmaker': sum((m['origination'] or {}).get('method') == 'bookmaker' for m in matches_out),
        'model': sum((m['origination'] or {}).get('method') == 'model' for m in matches_out),
        'alias_joined': sum(bool(m['aliases_used']) for m in matches_out),
    }
    flags = []
    for m in matches_out:
        if m['origination'] is None:
            flags.append({'id': 'origination-unresolved-' + m['id'], 'severity': 'warning',
                          'title': 'Unresolved: ' + ' vs '.join(t['name'] or 'Unverified team' for t in m['teams']),
                          'detail': 'No alias-verified market, esportsbook or rating input was confirmed. Blank pick is intentional.',
                          'match_ids': [m['id']],
                          'source_urls': [m['source_url']] + [r['source_url'] for r in m['research']]})
        for note in m['time_flags']:
            flags.append({'id': 'start-time-' + m['id'], 'severity': 'notice',
                          'title': 'Provider start-time disagreement', 'detail': note,
                          'match_ids': [m['id']], 'source_urls': [m['source_url']]})
    thin = [m['id'] for m in matches_out if any(q.get('thin') for q in (m['origination'] or {}).get('quotes', []) if isinstance(q, dict))]
    if thin:
        flags.append({'id': 'thin-markets', 'severity': 'notice',
                      'title': 'Thin/wide markets used as indicative inputs',
                      'detail': 'These estimates include at least one order book wider than 12 cents. Values are labeled indicative and must not be treated as executable prices.',
                      'match_ids': thin, 'source_urls': [POLY_INDEX]})
    flags.append({'id': 'alias-registry', 'severity': 'notice',
                  'title': 'Verified alias registry used for provider name joins',
                  'detail': f'{counts["alias_joined"]} active fixtures required a registry alias to join provider names. Every alias and its evidence links are published on the origination page and in data/origination/aliases.json.',
                  'match_ids': [], 'source_urls': [HLTV_EVENT, 'https://liquipedia.net/rocketleague/ROUNDS']})

    result = {
        'schema_version': 1,
        'generated_at': iso(now),
        'source_snapshot_at': snapshot.get('inventory_observed_at'),
        'source_generated_at': snapshot.get('generated_at'),
        'registry_updated_at': registry.get('updated_at'),
        'live_collection': bool(live),
        'counts': counts,
        'policy': {
            'hotspawn_votes_used': False,
            'fan_votes_used': False,
            'start_tolerance_sec': START_TOLERANCE_SEC,
            'thin_spread': THIN_SPREAD,
            'max_accepted_spread': MAX_ACCEPTED_SPREAD,
            'ladder': ['verified-alias Polymarket series-winner books', 'verified-alias esportsbook paired prices (no-vig)',
                       'median consensus across money families', 'Valve-rating research model fallback', 'blank + flagged'],
        },
        'matches': matches_out,
        'unresolved_ids': unresolved,
        'flags': flags,
        'sources': [
            {'name': 'Hotspawn fixture inventory', 'url': snapshot.get('sources', [{}])[0].get('url', 'https://play.hotspawn.com/lobby') if snapshot.get('sources') else 'https://play.hotspawn.com/lobby', 'role': 'match list only; Hotspawn popularity is never a probability input'},
            {'name': 'Polymarket CS2', 'url': POLY_INDEX, 'role': 'series-winner order books (money source)'},
            {'name': 'Thunderpick esportsbook', 'url': THUNDERPICK_PAGE, 'api_url': THUNDERPICK_API, 'role': 'original paired prematch prices (money source)'},
            {'name': 'HLTV.org', 'url': HLTV_EVENT, 'role': 'identity research and published ranks; fan votes never a probability input'},
            {'name': 'Valve official standings', 'url': (valve_meta or {}).get('source_url', 'https://github.com/ValveSoftware/counter-strike_regional_standings'), 'role': 'uncalibrated research-model fallback only'},
        ],
        'alias_registry': registry,
    }
    (output / 'origination.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data'))
    parser.add_argument('--live', action='store_true', help='refetch first-party sources before resolving')
    args = parser.parse_args()
    result = run(args.output, live=args.live)
    print(json.dumps({'counts': result['counts'], 'unresolved': result['unresolved_ids'],
                      'generated_at': result['generated_at']}, indent=2))


if __name__ == '__main__':
    main()
