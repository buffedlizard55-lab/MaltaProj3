"""Session arena-542dfb58 — live coverage reconciliation and gap-source research.

Run on a network-capable GitHub Actions runner (the Arena sandbox has no route to
Hotspawn, HLTV, Polymarket or any esportsbook — verified 2026-10-26T00:50Z: `curl`
to `buffedlizard55-lab.github.io` exits 35 with no status line).

It answers exactly two questions with first-hand, dated evidence:

1. **Coverage.** Does every CS2 fixture currently open on Hotspawn have a pick on
   the deployed site — either a featured first-party line or a researched fallback —
   and if not, which fixture ids are missing?
2. **Gaps.** For every fixture the *money* rungs cannot price, what does each
   external surface actually publish? HLTV first (match listing, then the betting
   analytics page that relays bookmaker prices), then the exchanges/books the
   project already trusts (Smarkets, Pinnacle, Thunderpick, Kalshi, Bovada), then
   the esports-betting surfaces the ladder does **not** yet read (Rivalry, GG.BET,
   Betexplorer, 1xBet's public line feed, BetCet, Esportsbetting, bo3.gg).

Facts only. No probability, pick or alias is written here; a price found by this
probe becomes a published number only through the publisher's own fail-closed
ladder (`scripts/originate.py`), which applies the project's join, margin, spread
and freshness contracts. Joining is deliberately as strict as the ladder's:
both team names normalised **and** a published start within 60 s, otherwise the
row is recorded as `name-only` for review and never bound.

Run:  python -m scripts.542dfb58_gap_probe [--output data/research/542dfb58]
      python -m scripts.542dfb58_gap_probe --parse-raw   # offline replay of stored bodies
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlencode

from scripts.domain import identity_matches, name_key, no_vig
from scripts.sources import CS2_LOBBY, FIXTURES_API, LOBBY, Client, SourceError, hotspawn

UTC = timezone.utc
SITE = 'https://buffedlizard55-lab.github.io/MaltaProj3'
DEFAULT_OUT = Path('data/research/542dfb58')
MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference', 'relay'}
MODEL_METHODS = {'model', 'network', 'guidance'}
START_TOLERANCE_SEC = 60

HLTV_MATCHES = 'https://www.hltv.org/matches'
HLTV_RANKING = 'https://www.hltv.org/ranking/teams'
SMARKETS_API = 'https://api.smarkets.com/v3'
PINNACLE_API = 'https://guest.api.arcadia.pinnacle.com/0.1'
THUNDERPICK_API = 'https://thunderpick.io/api/matches'
KALSHI_EVENTS = 'https://api.elections.kalshi.com/trade-api/v2/events'
BOVADA_API = ('https://www.bovada.lv/services/sports/event/coupon/events/A/description/'
              'esports/counter-strike-2?lang=en')
RIVALRY_API = 'https://api.rivalry.com/sports/v1/events?' + urlencode(
    {'sportSlug': 'counter-strike', 'timezone': 'UTC', 'page': 1, 'limit': 50})
GGBET_API = 'https://api.gg.bet/Sport/GetTopGames?sportId=esports_counter_strike&timezone=UTC&lang=en'
BETEXPLORER = 'https://www.betexplorer.com/counter-strike/'
ONXBET_LINE = 'https://1xbet.com/LineFeed/Get1x2_VZip?sports=82&count=200&tf=2200000&mode=4&getEmpty=true'
BUTCET = 'https://www.betcet.com/en/sports/esports/counter-strike'
ESPORTSBETTING = 'https://www.esportsbetting.com/odds/cs2'
BO3_MATCHES = 'https://bo3.gg/matches'
EGW_MATCHES = 'https://egamersworld.com/counterstrike/matches'


# --------------------------------------------------------------------------- io

def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def store_raw(out_dir: Path, label: str, body) -> dict:
    """Archive the exact bytes this probe read, so every claim is replayable."""
    raw_dir = out_dir / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, sort_keys=True)
    payload = text.encode('utf-8', errors='replace')
    suffix = '.json' if isinstance(body, (dict, list)) else '.html'
    path = raw_dir / f'{label}{suffix}.gz'
    path.write_bytes(gzip.compress(payload, 6))
    return {'raw_file': str(path), 'stored_bytes': len(payload),
            'stored_sha256': hashlib.sha256(payload).hexdigest()}


def grab(client: Client, out_dir: Path, label: str, url: str, *, method='GET', payload=None,
         json_body=False) -> tuple[object | None, dict]:
    """Fetch one public surface and record exactly what came back."""
    record = {'label': label, 'url': url, 'method': method, 'observed_at': now_iso()}
    try:
        data, entry = client.fetch(url, label, method=method, payload=payload, json_body=json_body)
    except (SourceError, ValueError, KeyError) as exc:
        entry = client.manifest[-1] if client.manifest else {}
        record.update(status='error', http_status=entry.get('http_status'),
                      error=str(exc)[:240], rows_parsed=0)
        return None, record
    record.update(status='ok', http_status=entry.get('http_status'), final_url=entry.get('final_url'),
                  content_type=(entry.get('content_type') or '')[:60], response_date=entry.get('response_date'),
                  response_sha256=entry.get('response_sha256'), rows_parsed=0)
    record.update(store_raw(out_dir, label, data))
    if method == 'GET' and record.get('final_url') and record['final_url'].split('?')[0] != url.split('?')[0]:
        record['redirected'] = True
    return data, record


def usable_pair(odds) -> dict:
    """Apply the project's own bookmaker contract to a two-decimal-price pair."""
    try:
        implied = [1 / float(o) for o in odds]
    except (TypeError, ValueError, ZeroDivisionError):
        return {'usable': False, 'reason': 'not two decimal prices above 1'}
    margin = sum(implied)
    if not 0.85 <= margin <= 1.35:
        return {'usable': False, 'reason': f'paired margin {round(margin, 4)} outside the 0.85-1.35 policy band',
                'margin': round(margin, 4)}
    if float(odds[0]) == float(odds[1]):
        return {'usable': False, 'reason': 'identical prices on both sides (site placeholder)',
                'margin': round(margin, 4)}
    return {'usable': True, 'margin': round(margin, 4), 'no_vig': no_vig(list(odds))}


def team_keys(fixture: dict) -> list:
    """Normalised team names of a fixture; an empty list when the card is incomplete."""
    names = [t.get('name') if isinstance(t, dict) else None for t in fixture.get('teams') or []]
    if len(names) != 2 or not all(isinstance(n, str) and n.strip() for n in names):
        return []
    return [name_key(n) for n in names]


def presence_scan(body, fixtures: list, window: int = 400) -> dict:
    """How many of the target fixtures a surface mentions at all.

    A proximity test on the raw body, deliberately weaker than a join: it answers
    "did this source publish anything about this pairing" for the reachability
    matrix, and can never bind a price. Both normalised team names must appear
    within ``window`` characters of each other (either order).
    """
    text = body if isinstance(body, str) else json.dumps(body or {}, ensure_ascii=False)
    text = re.sub(r'\s+', ' ', unescape(text)).lower()
    hits = []
    for fixture in fixtures:
        keys = team_keys(fixture)
        if len(keys) != 2:
            continue
        a, b = keys[0], keys[1]
        near = False
        for position in (m.start() for m in re.finditer(re.escape(a), text)):
            other = text.find(b, max(0, position - window), position + window)
            if other >= 0:
                near = True
                break
        if near:
            hits.append(str(fixture['id']))
    return {'fixtures_mentioned': len(hits), 'fixture_ids': hits}


def bind(rows: list, fixtures: list) -> list:
    """Join source rows to Hotspawn fixtures by exact names + start, never by position."""
    joined = []
    for row in rows:
        names, start = row.get('names') or [], row.get('start')
        for fixture in fixtures:
            if not isinstance(names, list) or len(names) != 2:
                continue
            strict = False
            try:
                strict = identity_matches(names, start, fixture)
            except (KeyError, TypeError, ValueError):
                strict = False
            if strict:
                joined.append({**row, 'fixture_id': fixture['id'], 'join': 'exact-names-and-start'})
                continue
            wanted = set(team_keys(fixture))
            if (wanted and len({name_key(n) for n in names if isinstance(n, str)}) == 2
                    and {name_key(n) for n in names if isinstance(n, str)} == wanted and not start):
                joined.append({**row, 'fixture_id': fixture['id'], 'join': 'name-only-review-only'})
    return joined


# ------------------------------------------------------------------- inventory

def live_inventory(client: Client, out_dir: Path, now: datetime) -> dict:
    # `hotspawn()` hands back the raw API array — exactly what `scripts.collect`
    # normalises. The probe runs the same normaliser, so "open", "locked" and
    # "past" mean here precisely what the publisher means by them.
    from scripts.collect import normalize_fixture
    raw_rows, links, health = hotspawn(client)
    observed = health.get('observed_at') or now.strftime('%Y-%m-%dT%H:%M:%SZ')
    rows = [normalize_fixture(raw, links, observed, now) for raw in raw_rows
            if isinstance(raw, dict) and raw.get('sport_alias') == 'cs2']
    open_rows = [r for r in rows if r.get('availability') in {'open', 'locked', 'unknown_lock'}]
    return {
        'observed_at': health.get('observed_at'),
        'records': len(rows),
        'records_including_past_and_other_sports': len(raw_rows),
        'api_url': FIXTURES_API,
        'lobby_pages': [LOBBY, CS2_LOBBY],
        'visible_cards': health.get('visible_cards'),
        'crosscheck': health.get('crosscheck'),
        'open_fixture_ids': sorted(r['id'] for r in open_rows),
        'open_fixtures': [{k: r[k] for k in ('id', 'teams', 'competition', 'starts_at', 'locks_at',
                                              'availability', 'tier', 'source_url')} for r in open_rows],
        'detail': health.get('detail'),
    }


def deployed_state(client: Client, out_dir: Path) -> dict:
    out = {}
    for name, path in (('snapshot', '/snapshot.json'), ('origination', '/origination.json')):
        data, record = grab(client, out_dir, f'deployed-{name}', SITE + path, json_body=False)
        try:
            parsed = json.loads(data) if isinstance(data, str) else None
        except (TypeError, ValueError):
            parsed = None
        if parsed is None:
            out[name] = {'status': 'unreadable', 'error': record.get('error', 'no json body')}
            continue
        out[name] = {'status': 'ok', 'generated_at': parsed.get('generated_at'),
                     'counts': parsed.get('counts'), 'payload': parsed}
    return out


def reconcile(inventory: dict, deployed: dict) -> dict:
    """Every live open fixture must be present and picked on the deployed site."""
    snapshot = (deployed.get('snapshot') or {}).get('payload') or {}
    origination = (deployed.get('origination') or {}).get('payload') or {}
    featured = {str(m['id']): m for m in snapshot.get('matches') or []}
    researched = {str(m['id']): m for m in origination.get('matches') or []}
    rows, unpicked, missing = [], [], []
    for fixture in inventory['open_fixtures']:
        fid = str(fixture['id'])
        feat = featured.get(fid)
        res = researched.get(fid)
        f_analysis = (feat or {}).get('analysis') or {}
        r_analysis = ((res or {}).get('origination') or {})
        method = f_analysis.get('method') or r_analysis.get('method')
        pick_side = None
        if feat and feat.get('pick_index') is not None:
            pick_side = fixture['teams'][feat['pick_index']]['name']
        elif res and r_analysis.get('pick') is not None:
            pick_side = r_analysis.get('pick')
        elif res and r_analysis.get('selection') is not None:
            pick_side = fixture['teams'][r_analysis['selection']]['name']
        row = {
            'fixture_id': fid,
            'teams': [t['name'] for t in fixture['teams']],
            'competition': fixture.get('competition'),
            'starts_at': fixture.get('starts_at'),
            'tier': fixture.get('tier'),
            'on_deployed_snapshot': feat is not None,
            'on_deployed_origination': res is not None,
            'featured_method': f_analysis.get('method'),
            'researched_method': r_analysis.get('method'),
            'effective_method': method,
            'priced_by_money': method in MONEY_METHODS,
            'model_only': method in MODEL_METHODS,
            'pick': pick_side,
            'source_url': (f_analysis or r_analysis).get('source_url'),
            'limitation_count': len((feat or {}).get('limitations') or []),
        }
        rows.append(row)
        if not pick_side:
            unpicked.append(row)
        if feat is None and res is None:
            missing.append(fid)
    return {
        'open_fixtures': len(rows),
        'with_a_published_pick': sum(bool(r['pick']) for r in rows),
        'unpicked': unpicked,
        'missing_from_both_layers': missing,
        'model_or_guidance_only': [r for r in rows if r['model_only']],
        'rows': rows,
    }


# --------------------------------------------------------------------- hltv

def hltv_listing(text) -> list:
    """HLTV's own match listing, parsed by the publisher's own reader.

    `scripts.sources.parse_hltv_matches` is the exact function the four-hour
    pipeline uses, including its duplicate-wrapper and repeat-safeguard rules, so
    this probe can never report a different HLTV row than the ladder would accept.
    """
    if not isinstance(text, str):
        return []
    from scripts.sources import parse_hltv_matches
    rows = []
    for card in parse_hltv_matches(text) or []:
        url = str(card.get('source_url') or '')
        found = re.search(r'/matches/(\d+)/([a-z0-9\-]+)', url)
        if not found or len(card.get('teams') or []) != 2:
            continue
        rows.append({'hltv_id': found.group(1), 'slug': found.group(2), 'names': list(card['teams']),
                     'start': card.get('starts_at'), 'best_of': card.get('best_of'), 'url': url})
    return rows


BEST_BET = re.compile(r'<span class="best-bet-odds(?: no-bet)?">(?P<odd>[0-9.]+|No bet)</span>\s*'
                      r'<span class="best-bet-provider(?: featured)?">(?P<provider>[^<]+)</span>', re.S)


def hltv_analytics_facts(text: str) -> dict:
    """What the HLTV betting-analytics page publishes for one fixture.

    Documented finding (this session, replayed from session 93c7475a's 2026-10-25T16:10Z
    capture): the page publishes per-outcome *handicap/set* best-bet prices and HLTV's own
    historical distribution, not a two-way series-winner price. The probe therefore reports
    the distinct prices and providers it can see and never converts them into a probability.
    """
    pairs = []
    for hit in BEST_BET.finditer(text or ''):
        odd = hit['odd'].strip()
        if odd.lower() == 'no bet':
            continue
        try:
            pairs.append({'odd': float(odd), 'provider': hit['provider'].strip()})
        except ValueError:
            continue
    distinct = sorted({p['odd'] for p in pairs})
    return {'best_bet_prices_seen': [p['odd'] for p in pairs], 'distinct_odds': distinct,
            'providers': sorted({p['provider'] for p in pairs}),
            'series_winner_price_published': len(distinct) >= 2}


# --------------------------------------------------------------- book surfaces

def smarkets_rows(body) -> list:
    rows = []
    for event in (body or {}).get('events') or []:
        if not isinstance(event, dict):
            continue
        names = re.split(r'\s+vs\.?\s+', str(event.get('name') or ''), maxsplit=1)
        if len(names) != 2:
            continue
        rows.append({'names': [n.strip() for n in names], 'start': event.get('start_datetime'),
                     'url': 'https://smarkets.com' + str(event.get('full_slug') or ''),
                     'event_id': event.get('id'), 'book': 'Smarkets'})
    return rows


def pinnacle_rows(body) -> list:
    """Guest feed rows: names and start only.

    Pinnacle prices are read by the publisher through `scripts.pinnacle_lines`
    (market-type, period and participant-id contracts included); re-implementing
    that parser here would risk a *different* answer from the published one, so
    this probe records reachability and fixture presence only.
    """
    rows = []
    for event in ((body or {}).get('result') or []):
        home, away = event.get('home') or {}, event.get('away') or {}
        if not (home.get('name') and away.get('name')):
            continue
        rows.append({'names': [home['name'], away['name']], 'start': event.get('start_time'),
                     'prices': None, 'book': 'Pinnacle',
                     'url': 'https://www.pinnacle.com/en/esports/matchups'})
    return rows


def thunderpick_rows(body) -> list:
    """Thunderpick's public board: the two-way "Match Winner" market per event.

    Shape verified against the 2026-10-25T16:10:27Z capture archived at
    data/research/93c7475a/raw/thunderpick-matches.json: data.upcoming[] events each
    carry preferredMarkets[] whose Match Winner market holds exactly two selections
    with `name` and decimal `odds`.
    """
    rows = []
    data = (body or {}).get('data') or {}
    buckets = []
    if isinstance(data, dict):
        buckets = [data.get('upcoming') or [], data.get('live') or []]
    for events in buckets:
        for event in events:
            if not isinstance(event, dict):
                continue
            for market in event.get('preferredMarkets') or []:
                if not isinstance(market, dict):
                    continue
                if str(market.get('nickName') or '').lower() not in {'winner', 'match winner'}:
                    continue
                selections = [s for s in (market.get('selections') or []) if isinstance(s, dict)]
                if len(selections) != 2:
                    continue
                names = [s.get('name') for s in selections]
                prices = [s.get('odds') for s in selections]
                if not all(isinstance(n, str) and n.strip() for n in names):
                    continue
                rows.append({'names': names, 'start': event.get('startTime'),
                             'prices': prices if all(isinstance(x, (int, float)) for x in prices) else None,
                             'book': 'Thunderpick', 'best_of': event.get('bestOfMaps'),
                             'url': 'https://thunderpick.io/esports/counter-strike'})
    return rows


def kalshi_rows(body) -> list:
    rows = []
    for event in (body or {}).get('events') or []:
        if not isinstance(event, dict):
            continue
        for market in event.get('markets') or []:
            if not isinstance(market, dict):
                continue
            title = str(market.get('title') or event.get('title') or '')
            names = re.split(r'\s+vs.?\s+', title, maxsplit=1, flags=re.I)
            if len(names) != 2:
                continue
            rows.append({'names': [names[0].strip(), names[1].strip()],
                         'start': market.get('close_time') or event.get('expected_expiration_time'),
                         'prices': None, 'book': 'Kalshi', 'ticker': market.get('ticker'),
                         'url': f'https://kalshi.com/markets/{market.get("ticker")}'})
    return rows


def bovada_rows(body) -> list:
    """Names and start times from the public coupon tree; prices stay with the ladder."""
    rows = []

    def walk(node):
        if isinstance(node, dict):
            teams = node.get('competitors') or node.get('participants')
            if isinstance(teams, list) and len(teams) == 2:
                names = [t.get('name') or t.get('abbreviation') for t in teams if isinstance(t, dict)]
                if len([n for n in names if n]) == 2:
                    rows.append({'names': [n for n in names if n],
                                 'start': node.get('rotTime') or node.get('eventLiveDate'),
                                 'prices': None, 'book': 'Bovada',
                                 'url': 'https://www.bovada.lv/sports/esports/counter-strike'})
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(body)
    return rows


RIVALRY_GAME = re.compile(r'"awayTeam"\s*:\s*\{\s*"name"\s*:\s*"(?P<away>[^"]+)".*?'
                          r'"homeTeam"\s*:\s*\{\s*"name"\s*:\s*"(?P<home>[^"]+)".*?'
                          r'"commenceTime"\s*:\s*"(?P<start>[^"]+)"', re.S)
RIVALRY_ODDS = re.compile(r'"decimalOdds"\s*:\s*\[\s*\{[^}]*?"oddsValue"\s*:\s*(?P<a>[0-9.]+).*?'
                         r'"oddsValue"\s*:\s*(?P<b>[0-9.]+)', re.S)


def rivalry_rows(body) -> list:
    text = body if isinstance(body, str) else json.dumps(body or {})
    rows = []
    games = list(RIVALRY_GAME.finditer(text))
    odds = list(RIVALRY_ODDS.finditer(text))
    for index, hit in enumerate(games):
        pair = odds[index].groups() if index < len(odds) else (None, None)
        rows.append({'names': [hit['home'], hit['away']], 'start': hit['start'],
                     'prices': [float(pair[0]), float(pair[1])] if all(pair) else None,
                     'book': 'Rivalry', 'url': 'https://www.rivalry.com/sportsbook/counter-strike'})
    return rows


BETEX_ROW = re.compile(r'<tr[^>]*data-realid="(?P<id>\d+)"[^>]*>(?P<body>.*?)</tr>', re.S)
BETEX_TEAMS = re.compile(r'<a[^>]*class="in-match"[^>]*>(?P<left>[^<]+)</a>(?P<middle>.*?)'
                         r'<a[^>]*class="in-match"[^>]*>(?P<right>[^<]+)</a>', re.S)
BETEX_ODD = re.compile(r'>(?P<odd>[1-9][0-9]?\.[0-9]{2})<')


def betexplorer_rows(text: str) -> list:
    """Betexplorer's CS2 index prints each pairing with its published decimal odds."""
    rows = []
    for block in BETEX_ROW.finditer(text or ''):
        chunk = block.group('body')
        teams = BETEX_TEAMS.search(chunk)
        if not teams:
            continue
        middle = teams.group('middle') or ''
        odds = [float(o) for o in BETEX_ODD.findall(middle)[:2]]
        rows.append({'names': [unescape(teams['left']).strip(), unescape(teams['right']).strip()],
                     'start': None, 'prices': odds if len(odds) == 2 else None, 'book': 'Betexplorer',
                     'url': 'https://www.betexplorer.com/counter-strike/'})
    return rows


def onxbet_rows(body) -> list:
    """1xBet's public pre-match line feed: `W1`/`W2` are decimal series prices."""
    rows = []
    for item in (body or {}).get('Value') or []:
        if not isinstance(item, dict):
            continue
        for game in item.get('E') or []:
            if not isinstance(game, dict):
                continue
            attrs = game.get('O1') if isinstance(game.get('O1'), dict) else game
            left, right = attrs.get('C1'), attrs.get('C2')
            if not (left and right):
                continue
            prices = [game.get('W1'), game.get('W2')]
            start = game.get('P') or game.get('S')
            rows.append({'names': [str(left), str(right)], 'start': str(start) if start else None,
                         'prices': [float(x) for x in prices if x] if all(prices) else None,
                         'book': '1xBet public line feed', 'url': 'https://1xbet.com/en/line/esports'})
    return rows


SURFACES = (
    # (label, url, kind, parser, note)
    ('hltv-matches', HLTV_MATCHES, 'html', hltv_listing, 'HLTV first: the official live match listing'),
    ('smarkets-events', f'{SMARKETS_API}/events/?type=csgo_match&states=upcoming&limit=200&sort=start_datetime,id',
     'json', smarkets_rows, 'regulated exchange, already a ladder rung'),
    ('pinnacle-matchups', f'{PINNACLE_API}/sports/12/matchups', 'json', pinnacle_rows,
     'Pinnacle guest esports API used by the ladder'),
    ('thunderpick-matches', THUNDERPICK_API, 'json-post', thunderpick_rows,
     'esportsbook with a public match endpoint, already a ladder rung'),
    ('kalshi-events', KALSHI_EVENTS + '?' + urlencode({'series_ticker': 'KXCS2GAME', 'status': 'open', 'limit': 200}),
     'json', kalshi_rows, 'exchange, already a ladder rung'),
    ('bovada-cs2', BOVADA_API, 'json', bovada_rows, 'sportsbook coupon, already a ladder rung'),
    ('rivalry-api', RIVALRY_API, 'json', rivalry_rows, 'esportsbook surface the ladder does not read'),
    ('ggbet-api', GGBET_API, 'json', lambda body: [], 'esportsbook surface the ladder does not read'),
    ('betexplorer', BETEXPLORER, 'html', betexplorer_rows, 'odds-aggregator index for Counter-Strike'),
    ('1xbet-linefeed', ONXBET_LINE, 'json', onxbet_rows, 'public pre-match line feed for low-tier esports'),
    ('betcet', BUTCET, 'html', lambda text: [], 'esportsbook page probe (reachability only)'),
    ('esportsbetting', ESPORTSBETTING, 'html', lambda text: [], 'odds comparison page probe (reachability only)'),
    ('bo3gg-matches', BO3_MATCHES, 'html', lambda text: [], 'results/odds site the ladder already relays'),
    ('egamersworld-matches', EGW_MATCHES, 'html', lambda text: [], 'aggregated average-odds reference page'),
)


def probe_surfaces(client: Client, out_dir: Path, fixtures: list) -> dict:
    surfaces, joined = {}, {}
    hltv_rows = []
    for label, url, kind, parser, note in SURFACES:
        payload = None
        if kind == 'json-post':
            payload = {'gameIds': [6]}
        data, record = grab(client, out_dir, label, url, method='POST' if payload else 'GET',
                            payload=payload, json_body=(kind == 'json'))
        record['note'] = note
        rows = []
        if data is not None:
            try:
                rows = parser(data) or []
            except Exception as exc:  # a contract change must be reported, not swallowed
                record['parse_error'] = f'{type(exc).__name__}: {exc}'[:200]
        record['rows_parsed'] = len(rows)
        if data is not None:
            record['presence'] = presence_scan(data, fixtures)
        record['fixture_ids_visible'] = (record.get('presence') or {}).get('fixtures_mentioned', 0)
        record['presence_fixture_ids'] = (record.get('presence') or {}).get('fixture_ids', [])
        if rows and label != 'hltv-matches':
            for row in rows:
                if not row.get('prices'):
                    continue
                verdict = usable_pair(row['prices'])
                row['price_check'] = verdict
            hits = bind([{**r, 'surface': label} for r in rows], fixtures)
            for hit in hits:
                joined.setdefault(hit['fixture_id'], []).append({
                    'surface': label, 'book': hit.get('book'), 'names': hit['names'], 'start': hit.get('start'),
                    'prices': hit.get('prices'), 'price_check': hit.get('price_check'),
                    'join': hit['join'], 'url': hit.get('url'), 'observed_at': record['observed_at'],
                    'evidence_sha256': record.get('response_sha256')})
        else:
            hltv_rows = rows
        surfaces[label] = record
    return {'surfaces': surfaces, 'joins': joined, 'hltv_rows': hltv_rows}


def probe_hltv_pages(client: Client, out_dir: Path, fixtures: list, hltv_rows: list) -> dict:
    """For every fixture with no money line, read its own HLTV pages."""
    hltv_by_fixture = {}
    listing = bind([{**r, 'names': r['names']} for r in hltv_rows], fixtures)
    for hit in listing:
        hltv_by_fixture.setdefault(hit['fixture_id'], []).append(hit)
    detail = {}
    for fixture_id, hits in hltv_by_fixture.items():
        for hit in hits[:2]:
            data, record = grab(client, out_dir, f'hltv-analytics-{hit["hltv_id"]}',
                               hit['url'].replace('/matches/', '/betting/analytics/'))
            facts = hltv_analytics_facts(data if isinstance(data, str) else '')
            record.update(hltv_match_url=hit['url'], **facts)
            detail.setdefault(fixture_id, []).append(record)
    return detail


# ------------------------------------------------------------------ reporting

def build_flags(inventory: dict, coverage: dict, surfaces: dict, joins: dict) -> list:
    flags = []
    unreachable = [label for label, rec in surfaces.items() if rec.get('status') != 'ok']
    if unreachable:
        flags.append({
            'id': '542dfb58-surfaces-unreachable', 'severity': 'warning', 'match_ids': [],
            'title': f'{len(unreachable)} of {len(surfaces)} probed surfaces refused the runner this hour',
            'detail': 'Reachability of the external surfaces tried for the fixtures no money line can price, '
                      'observed ' + str(inventory.get('observed_at')) + ': '
                      + '; '.join(f'{label} ({surfaces[label].get("http_status")})' for label in unreachable)
                      + '. A refused page is not evidence that no market exists; the ladder retries them every '
                        'four hours and will take a compliant price the moment one validates.',
            'source_urls': [surfaces[l].get('url', '') for l in unreachable][:6]})
    for row in coverage['unpicked']:
        flags.append({
            'id': f'542dfb58-unpicked-{row["fixture_id"]}', 'severity': 'critical',
            'match_ids': [row['fixture_id']],
            'title': f'No pick published for {row["teams"][0]} vs {row["teams"][1]}',
            'detail': f'Hotspawn lists this {row["competition"]} fixture open (starts {row["starts_at"]}, tier '
                      f'{row["tier"]}) and neither the featured line nor the researched fallback produced a pick. '
                      'Sources tried this hour are in data/research/542dfb58/probe.json.',
            'source_urls': [row['source_url'] or (SITE + '/snapshot.json')]})
    for row in coverage['model_or_guidance_only']:
        found = joins.get(row['fixture_id']) or []
        usable = [f for f in found if (f.get('price_check') or {}).get('usable')]
        flags.append({
            'id': f'542dfb58-magnitude-single-source-{row["fixture_id"]}', 'severity': 'info',
            'match_ids': [row['fixture_id']],
            'title': f'{row["teams"][0]} vs {row["teams"][1]} rests on a {row["effective_method"]} estimate, not a priced market',
            'detail': f'The published direction comes from the {row["effective_method"]} rung (uncalibrated research '
                      f'model). This hour the probe scanned {len(surfaces)} surfaces and bound '
                      f'{len(found)} row(s) by exact names and start time; {len(usable)} carry a two-decimal pair '
                      'inside the project margin policy. Nothing was written into a pick from this probe — if a '
                      'book or exchange validates, the four-hour ladder adopts it automatically.',
            'source_urls': [row['source_url'] or (SITE + '/origination/')] + [f.get('url', '') for f in found[:3]]})
    return flags


def render_markdown(out: dict) -> str:
    inv, coverage, surfaces = out['inventory'], out['coverage'], out['surfaces']['surfaces']
    lines = [
        '# Live coverage + gap-source probe — a pick for every Hotspawn CS2 fixture',
        '',
        f'Observed {inv["observed_at"]} (live, GitHub Actions runner). Facts only: this file records what each '
        'source served. No probability, pick or alias is written here; the publisher\'s ladder stays the only '
        'path to a published number.',
        '',
        '## Hotspawn inventory reconciliation',
        '',
        '| Fact | Value |',
        '| --- | --- |',
        f'| fixture-API records | {inv["records"]} |',
        f'| open CS2 fixtures | {len(inv["open_fixture_ids"])} |',
        f'| rendered-lobby crosscheck | {inv["crosscheck"]} |',
        f'| open ids missing from the deployed site | {coverage["missing_from_both_layers"] or "none"} |',
        f'| open fixtures with a published pick | {coverage["with_a_published_pick"]} of {coverage["open_fixtures"]} |',
        f'| open fixtures with **no** pick | {len(coverage["unpicked"])} |',
        f'| picks priced by a real market or book | {sum(r["priced_by_money"] for r in coverage["rows"])} |',
        f'| picks resting on a research model | {len(coverage["model_or_guidance_only"])} |',
        '',
        '## Every open fixture',
        '',
        '| Fixture | Starts | Method on the deployed site | Pick | Priced by money? |',
        '| --- | --- | --- | --- | --- |',
    ]
    for row in coverage['rows']:
        lines.append(f'| {row["teams"][0]} vs {row["teams"][1]} | {row["starts_at"]} | '
                     f'{row["effective_method"] or "—"} | {row["pick"] or "—"} | '
                     f'{"yes" if row["priced_by_money"] else "no"} |')
    lines += ['', '## Surfaces tried for the fixtures no money line prices', '',
              '| Surface | HTTP | Status | Rows parsed | Fixtures whose names appear |',
              '| --- | --- | --- | --- | --- |']
    for label, rec in surfaces.items():
        lines.append(f'| {label} | {rec.get("http_status", "—")} | {rec.get("status")} | '
                     f'{rec.get("rows_parsed", 0)} | {rec.get("fixture_ids_visible", 0)} |')
    lines += ['', '## Exact-name joins found for the gap fixtures', '',
              'Each row is a price the *source* published, with the project\'s own margin contract applied. '
              'A row marked `not bound` means the surface answered but published no price for that fixture.', '']
    for row in coverage['rows']:
        found = out['surfaces']['joins'].get(row['fixture_id']) or []
        lines.append(f'- **{row["teams"][0]} vs {row["teams"][1]}** ({row["starts_at"]}, '
                     f'{row["competition"]}, tier {row["tier"]}) — deployed method: '
                     f'{row["effective_method"] or "unresolved"}')
        if not found:
            lines.append('  - no surface published an exact-name two-team row this hour')
        for hit in found:
            verdict = hit.get('price_check') or {}
            lines.append(f'  - {hit["surface"]} → {hit["names"]} @ {hit.get("prices")} · '
                         f'{hit["join"]} · usable: {verdict.get("usable", False)}'
                         f'{"" if verdict.get("usable") else " (" + str(verdict.get("reason")) + ")"} · '
                         f'[{hit["url"]}]({hit["url"]}) at {hit["observed_at"]}')
    if out.get('hltv_details'):
        lines += ['', '## HLTV pages read for the unpicked fixtures', '']
        for fixture_id, records in out['hltv_details'].items():
            for rec in records:
                lines.append(f'- `{fixture_id}` — {rec.get("status")} ({rec.get("http_status", "—")}) '
                             f'{rec.get("url")}: best-bet prices {rec.get("distinct_odds")}, providers '
                             f'{rec.get("providers")}, series-winner price published: '
                             f'{rec.get("series_winner_price_published")}')
    lines += ['', '## Limitations of this probe', '',
              '- A single hour of observation. Prices move; the four-hour ladder re-reads every source.',
              '- HTTP 403/redirect surfaces (Cloudflare-protected books) are recorded as unreachable, not as '
              '"no market".',
              '- Rows joined `name-only` are for review only: without a published start time the project never '
              'binds a price to a fixture.',
              '- No number in this file is published as a pick. Only `scripts/originate.py` may do that, with '
              'its own strict contract and its own dated evidence.', '']
    return '\n'.join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--parse-raw', action='store_true',
                        help='replay the parsers from the stored gzipped bodies, offline')
    args = parser.parse_args(argv)
    out_dir, raw_dir = args.output, args.output / 'raw'
    now = datetime.now(UTC)

    if args.parse_raw:
        replay = {'observed_at': now_iso(), 'mode': 'offline-replay', 'surfaces': {}}
        for label, url, kind, parser_fn, note in SURFACES:
            suffix = '.json' if kind in ('json', 'json-post') else '.html'
            path = raw_dir / f'{label}{suffix}.gz'
            if not path.exists():
                replay['surfaces'][label] = {'stored': False}
                continue
            raw = gzip.decompress(path.read_bytes())
            body = raw.decode('utf-8', errors='replace')
            data = json.loads(body) if suffix == '.json' else body
            replay['surfaces'][label] = {'stored_sha256': hashlib.sha256(raw).hexdigest()}
            try:
                rows = parser_fn(data if isinstance(data, str) or isinstance(data, (dict, list)) else None) or []
            except Exception as exc:
                replay['surfaces'][label].update({'parse_error': f'{type(exc).__name__}: {exc}'[:200]})
                continue
            replay['surfaces'][label].update({'rows_parsed': len(rows)})
        replay_dir = out_dir / 'replay'
        replay_dir.mkdir(parents=True, exist_ok=True)
        (replay_dir / 'probe-replay.json').write_text(json.dumps(replay, indent=2, ensure_ascii=False) + '\n')
        try:
            stored = json.loads((out_dir / 'probe.json').read_text())
        except (OSError, ValueError):
            print('no probe.json to compare against — replay recorded alone')
            return 0
        drift = []
        for label, record in replay['surfaces'].items():
            if not record.get('stored'):
                continue
            live_rows = (stored.get('surfaces', {}).get('surfaces', {}).get(label) or {}).get('rows_parsed')
            if live_rows is not None and live_rows != record['rows_parsed']:
                drift.append(f'{label}: stored replay parsed {record["rows_parsed"]} vs {live_rows} live')
        (replay_dir / 'replay-drift.txt').write_text('\n'.join(drift) + ('\n' if drift else ''))
        print(f'offline replay: {sum(1 for r in replay["surfaces"].values() if r.get("stored"))} surfaces '
              f're-parsed from stored bytes, {len(drift)} drift line(s)')
        for line in drift:
            print('::warning::' + line)
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    client = Client(out_dir)
    try:
        inventory = live_inventory(client, out_dir, now)
        deployed = deployed_state(client, out_dir)
        coverage = reconcile(inventory, deployed)
    except Exception as exc:  # a partial, dated dossier beats a run with no evidence at all
        import traceback
        (out_dir / 'probe-error.txt').write_text(traceback.format_exc())
        (out_dir / 'inventory-failure.json').write_text(json.dumps(
            {'observed_at': now_iso(), 'error': f'{type(exc).__name__}: {exc}'[:400],
             'requests': client.manifest}, indent=2) + '\n')
        print('::error title=542dfb58 probe could not complete::'
              f'{type(exc).__name__}: {exc} — partial evidence committed, traceback in probe-error.txt')
        return 1
    for layer in ('snapshot', 'origination'):
        # Keep the published report compact and free of copied numbers: the layers
        # are cited by their own URL and generation timestamp, never reproduced.
        deployed.get(layer, {}).pop('payload', None)
    fixtures = []
    for fixture in inventory['open_fixtures']:
        record = dict(fixture)
        record['starts_at'] = fixture.get('starts_at')
        fixtures.append(record)
    coverage = reconcile(inventory, {k: dict(v) for k, v in deployed.items()})
    targets = [row for row in coverage['rows'] if not row['priced_by_money']] or [
        row for row in coverage['rows']]
    target_fixtures = [f for f in fixtures if str(f['id']) in {row['fixture_id'] for row in targets}]
    try:
        surfaces = probe_surfaces(client, out_dir, target_fixtures)
    except Exception as exc:
        import traceback
        (out_dir / 'surface-probe-error.txt').write_text(traceback.format_exc())
        print(f'::warning title=surface scan incomplete::{type(exc).__name__}: {exc}')
        surfaces = {'surfaces': {}, 'joins': {}, 'hltv_rows': []}
    try:
        hltv_details = probe_hltv_pages(client, out_dir, target_fixtures, surfaces.get('hltv_rows') or [])
    except Exception as exc:
        import traceback
        (out_dir / 'hltv-probe-error.txt').write_text(traceback.format_exc())
        print(f'::warning title=HLTV page scan incomplete::{type(exc).__name__}: {exc}')
        hltv_details = {}
    flags = build_flags(inventory, coverage, surfaces['surfaces'], surfaces['joins'])

    payload = {
        'schema_version': 1, 'session': 'arena-542dfb58', 'observed_at': inventory['observed_at'],
        'collected_at': now_iso(), 'policy': 'facts only — this probe never writes a probability, pick or alias',
        'deployed': deployed, 'inventory': {k: v for k, v in inventory.items() if k != 'open_fixtures'},
        'coverage': {k: v for k, v in coverage.items() if k != 'rows'},
        'coverage_rows': coverage['rows'], 'surfaces': surfaces, 'hltv_details': hltv_details,
        'requests': client.manifest,
    }
    (out_dir / 'probe.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    (out_dir / 'probe.md').write_text(render_markdown({
        'inventory': inventory, 'coverage': coverage, 'surfaces': surfaces, 'hltv_details': hltv_details}))
    (out_dir / 'flags.json').write_text(json.dumps(flags, indent=2, ensure_ascii=False) + '\n')
    (out_dir / 'probe-exit-code.txt').write_text('0\n')
    print(f'coverage: {coverage["with_a_published_pick"]}/{coverage["open_fixtures"]} open fixtures carry a '
          f'pick; {len(coverage["unpicked"])} unpicked; {len(targets)} gap fixture(s) researched across '
          f'{len(surfaces["surfaces"])} surfaces')
    return 0


if __name__ == '__main__':
    sys.exit(main())
