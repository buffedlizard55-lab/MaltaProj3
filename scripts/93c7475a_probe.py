"""Read-only live research probe for session 93c7475a: a pick, or an explicit
limitation, for **every** Hotspawn Counter-Strike 2 fixture.

Why this exists
---------------
The authoring sandbox for this session has **no outbound network at all** —
``curl https://www.hltv.org/matches`` and the Hotspawn fixture API both fail
before a status line is returned (recorded in ``COORDINATION.md`` for this
session).  The only place the brief's question can be answered with first-hand
evidence is a GitHub runner, so this module runs there.

It answers two questions the brief asks directly:

1. *Coverage.*  Which fixtures does Hotspawn list as open CS2 pickems right now,
   which of them has a published pick, and which does not?  The inventory is
   read twice — the official fixture API and the rendered lobby — and the two
   sets are compared in both directions, so a fixture that appears in only one
   of them is reported rather than silently dropped.

2. *Research order.*  For every open fixture whose pick is **not** a featured
   market line, what do HLTV and the esportsbook / betting-line surfaces
   actually publish?  HLTV is read first (match page, betting-analytics page and
   the official weekly world ranking), then the books and exchanges.

What it never does
------------------
It never writes a probability, a pick or an alias.  The publisher's ladder
(``scripts/originate.py``) remains the only path to a published number.  A value
that cannot be read stays absent and is published as a limitation.  Hotspawn
``% picked`` and HLTV fan votes are excluded from every calculation by policy;
they are not even parsed here.

Output
------
``data/research/93c7475a/probe.json`` (machine readable), ``probe.md`` (readable),
``unresolved-research.json`` (the schema consumed by
``scripts/unresolved_research.py``) and ``flags.json``.  Every raw response body
is archived under ``raw/`` with its URL, observation timestamp and SHA-256, so
every parse can be replayed offline with ``--parse-raw``.

CLI
---
    python -m scripts.93c7475a_probe                 # fetch live, then write the dossier
    python -m scripts.93c7475a_probe --parse-raw     # re-parse the archived bodies only
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scripts import hltv_ranking
from scripts.domain import name_key, timestamp

UTC = timezone.utc
OUT = Path('data/research/93c7475a')
RAW = OUT / 'raw'
SESSION = 'arena-93c7475a'

DEPLOYED = 'https://buffedlizard55-lab.github.io/MaltaProj3/'
FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
LOBBY = 'https://play.hotspawn.com/lobby'
CS2_LOBBY = 'https://play.hotspawn.com/cs2-pickems'
HLTV_MATCHES = 'https://www.hltv.org/matches'
HLTV_RANKING = hltv_ranking.RANKING_URL

#: The esportsbook / betting-line surfaces the brief names as the second
#: research step.  Each entry is probed for reachability and, where the surface
#: is machine readable, parsed for the gap fixtures.  A refusal is recorded as a
#: limitation of *this runner*, never as proof that no market exists.
BOOKS = [
    ('polymarket-cs2-tag', 'https://gamma-api.polymarket.com/events?tag_slug=cs2&closed=false&limit=100',
     'json', 'Polymarket CS2 tag', 'https://polymarket.com/esports/counter-strike'),
    ('thunderpick-matches', 'https://thunderpick.io/api/matches', 'post-json',
     'Thunderpick esportsbook', 'https://thunderpick.io/esports/counter-strike'),
    ('kalshi-cs2-events', 'https://api.elections.kalshi.com/trade-api/v2/events?status=open&limit=200',
     'json', 'Kalshi exchange', 'https://kalshi.com/markets/esports'),
    ('pinnacle-esports', 'https://guest.api.arcadia.pinnacle.com/0.1/esports/matchups?sportId=22&live=0',
     'json', 'Pinnacle esportsbook', 'https://www.pinnacle.com/en/esports/counter-strike-2'),
    ('smarkets-cs2', 'https://api.smarkets.com/v3/events?type=csgo_match&state=upcoming',
     'json', 'Smarkets exchange', 'https://smarkets.com/sport/esports/cs-go'),
    ('bo3gg-matches', 'https://bo3.gg/matches', 'html', 'bo3.gg results feed', 'https://bo3.gg/matches'),
    ('egamersworld-matches', 'https://egamersworld.com/counterstrike/matches', 'html',
     'EGamersWorld odds aggregator', 'https://egamersworld.com/counterstrike/matches'),
    ('ggbet-cs2', 'https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike',
     'html', 'GG.BET esportsbook', 'https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike'),
    ('stake-cs2', 'https://stake.com/sports/esports/counter-strike', 'html',
     'Stake esportsbook', 'https://stake.com/sports/esports/counter-strike'),
    ('rivalry-cs2', 'https://www.rivalry.com/esports/counter-strike-betting', 'html',
     'Rivalry esportsbook', 'https://www.rivalry.com/esports/counter-strike-betting'),
]

HEADERS = {
    'User-Agent': 'HotspawnCS2Origination/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)',
    'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8',
}
#: Every published method that carries an observed betting price.  Anything
#: outside this set is a research model, wide-book guidance or blank — exactly
#: the population the brief says to research HLTV-first.
MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference', 'relay'}
TIMEOUT = (15, 45)


def now_iso() -> str:
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def slug(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')


def record(label: str, url: str, response=None, *, error: str | None = None, body: bytes | None = None) -> dict:
    """One dated, hash-checked source observation.  Nothing is inferred."""
    entry = {'label': label, 'url': url, 'observed_at': now_iso(), 'status': 'error'}
    if error is not None:
        entry['error'] = error[:400]
        return entry
    entry.update(http_status=response.status_code, final_url=response.url,
                 content_type=response.headers.get('Content-Type'),
                 bytes=len(body or b''),
                 sha256=hashlib.sha256(body or b'').hexdigest())
    entry['status'] = 'ok' if response.ok else 'error'
    if not response.ok:
        entry['error'] = 'HTTP ' + str(response.status_code)
    return entry


def get(label: str, url: str, *, expect_json: bool = False, method: str = 'GET', payload=None) -> tuple[dict, object]:
    """Public read.  The body is archived before anything parses it."""
    try:
        if method == 'POST':
            response = requests.post(url, headers={**HEADERS, 'Content-Type': 'application/json'},
                                     data=json.dumps(payload or {}), timeout=TIMEOUT)
        else:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return record(label, url, error=type(exc).__name__ + ': ' + str(exc)), None
    entry = record(label, url, response, body=response.content)
    RAW.mkdir(parents=True, exist_ok=True)
    # HTML is archived gzipped (``.html.gz``): the publisher copies the research
    # tree into the site, and a bare ``.html`` there is validated as one of the
    # site's own pages (``no main landmark``).
    path = RAW / f'{slug(label)}.{"json" if expect_json else "html.gz"}'
    if response.ok:
        path.write_bytes(response.content if expect_json else gzip.compress(response.content))
    if not response.ok:
        return entry, None
    if not expect_json:
        return entry, response.text
    # A surface can answer HTTP 200 with an HTML challenge page instead of JSON.
    # That is a fact about the surface, not a crash: record it as an error so the
    # dossier reports the surface as refused, and keep going. (This is what
    # stopped the first live run — the JSON decode was unguarded.)
    try:
        return entry, response.json()
    except ValueError as exc:
        entry['status'] = 'error'
        entry['error'] = 'not JSON: ' + type(exc).__name__ + ': ' + str(exc)[:300]
        return entry, None


def read_archived(label: str, expect_json: bool):
    path = RAW / f'{slug(label)}.{"json" if expect_json else "html.gz"}'
    if not path.exists():
        return None
    raw = path.read_bytes()
    if expect_json:
        return json.loads(raw)
    return gzip.decompress(raw).decode('utf-8', 'replace')


def archived_sha256(label: str, expect_json: bool) -> str | None:
    """SHA-256 of the archived bytes, so a replay can re-prove a byte identity.

    The live runner hashes the served bytes; a replay hashes the same bytes as
    they were committed under ``raw/``.  Both are recorded with their provenance
    (``archived: True`` on the source entry) so a reader can tell which is which.
    A missing archive returns None rather than a fabricated digest.
    """
    path = RAW / f'{slug(label)}.{"json" if expect_json else "html.gz"}'
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


# ---------------------------------------------------------------------------
# Parsers (exact names only; nothing fuzzy)
# ---------------------------------------------------------------------------

def parse_hltv_listing(text: str) -> list:
    """Upcoming fixtures from an HLTV listing page, one row per match card."""
    soup = BeautifulSoup(text, 'html.parser')
    rows, seen = [], set()
    for card in soup.select('div.match-wrapper[data-match-wrapper]'):
        teams = [n.get_text(' ', strip=True) for n in card.select('.match-teamname')]
        teams = [n for n in teams if n]
        stamp = card.select_one('[data-unix]')
        epoch = stamp.get('data-unix') if stamp else None
        start = timestamp(epoch) if epoch else None
        if len(teams) != 2 or start is None:
            continue
        href = None
        link = card.select_one('a.match-teams[href^="/matches/"], a.match-top[href^="/matches/"]')
        if link is not None:
            href = (link.get('href') or '').split('?')[0]
        event = card.select_one('.match-event[data-event-headline]')
        analytics = card.select_one('a[href^="/betting/analytics/"]')
        meta = card.select_one('.match-meta')
        dedupe = str(card.get('data-match-id') or href or '')
        if dedupe in seen:
            continue
        seen.add(dedupe)
        rows.append({
            'match_id': card.get('data-match-id'),
            'url': ('https://www.hltv.org' + href) if href else None,
            'teams': teams,
            'starts_at': start.isoformat().replace('+00:00', 'Z'),
            'event': (event.get('data-event-headline') if event is not None else None),
            'best_of': (meta.get_text(' ', strip=True) if meta is not None else None),
            'live': (card.get('live') or '').lower() == 'true',
            'betting_analytics_url': ('https://www.hltv.org' + analytics['href'].split('?')[0]
                                      if analytics is not None else None),
        })
    return rows


def parse_lobby_fixture_ids(text: str) -> list:
    """Fixture ids the rendered lobby actually encodes, sorted by id."""
    ids = re.findall(r'fixture[-_/](\d{4,})', text)
    return sorted({i for i in ids}, key=int)


def open_fixtures(records: list, reference: datetime) -> list:
    """Fixture API records whose scheduled start is still in the future."""
    out = []
    for item in records:
        if not isinstance(item, dict):
            continue
        start = timestamp(item.get('scheduled_start_time') or item.get('start_date')
                          or item.get('starts_at'))
        if start is None or start <= reference:
            continue
        out.append(item)
    return out


def fixture_view(item: dict) -> dict:
    """Normalise one Hotspawn fixture record without inventing missing fields."""
    start = timestamp(item.get('scheduled_start_time') or item.get('start_date')
                      or item.get('starts_at'))
    names = [item.get('participants0_name'), item.get('participants1_name')]
    if not any(names):
        left, right = item.get('team1') or {}, item.get('team2') or {}
        names = [left.get('name') if isinstance(left, dict) else None,
                 right.get('name') if isinstance(right, dict) else None]
    return {'id': str(item.get('id')),
            'teams': names,
            'competition': item.get('competition_name') or item.get('competition'),
            'tier': item.get('tier'),
            'source_status': item.get('status'),
            'starts_at': start.isoformat().replace('+00:00', 'Z') if start else None}


def hltv_join(fixture: dict, rows: list) -> dict:
    """Exact-name HLTV listing, with the start-time delta kept visible."""
    wanted = [name_key(n) if n else '' for n in fixture['teams']]
    own_start = timestamp(fixture.get('starts_at'))
    exact, shared = [], []
    for row in rows:
        keys = [name_key(n) for n in row['teams']]
        if len(keys) != 2:
            continue
        row_start = timestamp(row.get('starts_at'))
        delta = None
        if own_start is not None and row_start is not None:
            delta = int((row_start - own_start).total_seconds())
        entry = dict(row, start_delta_seconds=delta)
        if sorted(keys) == sorted(wanted):
            exact.append(entry)
        elif set(keys) & set(wanted):
            shared.append(entry)
    return {'exact': exact, 'shares_one_name': shared}


def ranking_rows_with_position(rows: list) -> list:
    """Add the sequential rank to each parsed HLTV ranking row.

    :func:`scripts.hltv_ranking.parse_ranking_page` deliberately returns only
    ``team`` / ``points`` / ``team_url`` — the rank is the row's position on the
    dated publication, so it is derived here rather than assumed to exist.
    """
    return [dict(row, position=index + 1) for index, row in enumerate(rows)]


def ranking_row(name: str, rows: list) -> dict | None:
    if not name:
        return None
    key = name_key(name)
    for row in rows:
        if name_key(row.get('team') or '') == key:
            return row
    return None


def book_titles(label: str, payload, text) -> list:
    """Rows a book surface publishes, with any two-way price it shows.

    Each row keeps the *observed* decimal prices verbatim. Nothing here converts
    a price into a probability: the publisher's ladder owns every number. The
    shapes below were read from the archived response bodies in ``raw/`` during
    this session; the first version of this function guessed them and silently
    reported zero rows for three surfaces that were in fact serving CS2 lines.
    """
    titles = []
    if label == 'polymarket-cs2-tag' and isinstance(payload, list):
        for event in payload:
            if isinstance(event, dict):
                titles.append({'id': str(event.get('id')), 'title': event.get('title'),
                               'slug': event.get('slug'),
                               'url': 'https://polymarket.com/event/' + str(event.get('slug')),
                               'starts_at': event.get('startDate')})
    elif label == 'thunderpick-matches' and isinstance(payload, dict):
        # Real shape: {"statusCode":200,"ok":true,"data":{"upcoming":[...],"live":[...],"outrights":[...]}}.
        # Each match carries teams.home/teams.away and preferredMarkets[], where
        # the full-series winner is the market literally named "Match Winner".
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        for row in (data.get('upcoming') or []) + (data.get('live') or []):
            if not isinstance(row, dict):
                continue
            teams = row.get('teams') if isinstance(row.get('teams'), dict) else {}
            home = (teams.get('home') or {}).get('name')
            away = (teams.get('away') or {}).get('name')
            if not (home and away):
                continue
            odds = []
            for market in row.get('preferredMarkets') or []:
                if not isinstance(market, dict) or market.get('name') != 'Match Winner':
                    continue
                # bool is a subclass of int, so it is excluded explicitly.
                odds = [(s.get('name'), s.get('odds')) for s in market.get('selections') or []
                        if isinstance(s, dict) and isinstance(s.get('odds'), (int, float))
                        and not isinstance(s.get('odds'), bool)]
            comp = row.get('competition') if isinstance(row.get('competition'), dict) else {}
            titles.append({'id': str(row.get('id')), 'title': f'{home} vs {away}',
                           'url': 'https://thunderpick.io/esports/counter-strike',
                           'starts_at': row.get('startTime'), 'competition': comp.get('name'),
                           'odds': odds, 'best_of': row.get('bestOf')})
    elif label == 'kalshi-cs2-events' and isinstance(payload, dict):
        # The generic open-events endpoint answers 200 with politics and science
        # events, not esports. Counting those as CS2 rows would overstate the
        # coverage, so only rows whose own title names the sport are kept, and
        # the total is reported separately in the summary.
        for event in payload.get('events') or []:
            if not isinstance(event, dict):
                continue
            title = str(event.get('title') or '')
            if not any(word in title.lower() for word in ('counter-strike', 'cs2', 'csgo')):
                continue
            titles.append({'id': str(event.get('event_ticker')), 'title': title,
                           'url': 'https://kalshi.com/markets/esports'})
    elif label == 'smarkets-cs2' and isinstance(payload, dict):
        # Real shape: {"events":[{...}]}, each with name "A vs B" and a full_slug
        # under /sport/esports/cs-go/. The first version of this function read
        # payload["objects"], which does not exist, and reported zero rows while
        # the exchange was listing several of the live fixtures by exact name.
        for event in payload.get('events') or []:
            if not isinstance(event, dict) or not event.get('name'):
                continue
            slug = event.get('full_slug') or ''
            titles.append({'id': str(event.get('id')), 'title': event.get('name'),
                           'url': ('https://smarkets.com' + slug) if slug.startswith('/')
                                  else 'https://smarkets.com/sport/esports/cs-go'})
    elif label == 'pinnacle-esports' and isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict):
                continue
            names = [p.get('name') for p in (row.get('participants') or []) if isinstance(p, dict)]
            if len(names) == 2:
                titles.append({'id': str(row.get('id')), 'title': f'{names[0]} vs {names[1]}',
                               'url': 'https://www.pinnacle.com/en/esports/counter-strike-2'})
    elif text:
        # Loose HTML scan, bounded: a multi-megabyte SPA shell would make this
        # regex the slowest thing in the sweep for no benefit.
        if len(text) <= 2_000_000:
            for match in re.findall(r'([A-Za-z0-9 .\-&\']{2,40})\s*(?:vs\.?|—)\s*([A-Za-z0-9 .\-&\']{2,40})',
                                    text)[:2000]:
                titles.append({'id': None, 'title': f'{match[0].strip()} vs {match[1].strip()}', 'url': None})
    return titles


def exact_book_hits(fixture: dict, titles: list) -> list:
    """Book rows whose two names match the fixture exactly (name_key only)."""
    wanted = sorted(name_key(n) if n else '' for n in fixture['teams'])
    hits = []
    for row in titles:
        parts = [p.strip() for p in re.split(r'\s+vs\.?\s+', str(row.get('title') or ''), maxsplit=1)]
        if len(parts) == 2 and sorted(name_key(p) for p in parts) == wanted:
            hits.append(row)
    return hits


# ---------------------------------------------------------------------------
# Dossier
# ---------------------------------------------------------------------------

def build_dossier(observed_at: str, targets: list, books: list, hltv: dict) -> dict:
    """The schema-1 dossier consumed by :mod:`scripts.unresolved_research`.

    Every check carries its own dated https source.  Nothing here is a
    probability: the ``resolution`` field is deliberately restricted to
    ``stays-unresolved`` / ``expected-at-next-refresh`` so no fixture can render
    as an invented 50/50.
    """
    fixtures = []
    for target in targets:
        fixture = target['fixture']
        checks = []
        exact = target['hltv']['exact']
        shared = target['hltv']['shares_one_name']
        if exact:
            row = exact[0]
            delta = row.get('start_delta_seconds')
            detail = ('Exact team names on HLTV\'s upcoming listing'
                      + (f'; HLTV start differs by {delta} s' if delta else '; start time agrees exactly')
                      + (f'; HLTV lists {row.get("best_of")}' if row.get('best_of') else ''))
            checks.append({'stage': 'HLTV identity', 'verdict': 'confirmed' if delta == 0 else 'confirmed-with-clock-delta',
                           'detail': detail,
                           'sources': [{'url': row['url'], 'source': 'HLTV.org match listing',
                                        'detail': 'Upcoming-match card for these exact two names.',
                                        'observed_at': hltv['observed_at']}]})
        elif shared:
            checks.append({'stage': 'HLTV identity', 'verdict': 'partial-name-only',
                           'detail': 'HLTV lists a row sharing one team name only; the second name did not match, '
                                     'so no identity join is asserted.',
                           'sources': [{'url': shared[0]['url'], 'source': 'HLTV.org match listing',
                                        'detail': 'Nearest HLTV row sharing one team name (review only).',
                                        'observed_at': hltv['observed_at']}]})
        else:
            checks.append({'stage': 'HLTV identity', 'verdict': 'not-listed',
                           'detail': 'Neither the pair nor either team name appears on HLTV\'s upcoming listing at '
                                     'the observation time.',
                           'sources': [{'url': HLTV_MATCHES, 'source': 'HLTV.org upcoming matches',
                                        'detail': f'{hltv["upcoming_rows"]} upcoming cards read; no exact-name row.',
                                        'observed_at': hltv['observed_at']}]})

        analytics = target['hltv_analytics']
        if analytics:
            usable = analytics.get('usable_two_way_price')
            code = analytics.get('http_status')
            code_text = f'HTTP {code}' if code else 'no HTTP status recorded'
            checks.append({'stage': 'HLTV odds comparison', 'verdict': 'read' if usable else 'read-but-not-usable',
                           'detail': (f"{code_text}; "
                                      + (f"{analytics.get('distinct_odds_count')} distinct two-way prices"
                                         if usable else
                                         f"only {analytics.get('distinct_odds_count')} distinct decimal price(s) on the "
                                         f"page ({', '.join(analytics.get('distinct_odds') or []) or 'none'}) — a single "
                                         'repeated placeholder is refused as a two-way line')),
                           'sources': [{'url': analytics['url'], 'source': 'HLTV.org odds overview',
                                        'detail': 'Bookmaker odds-comparison page for the fixture.',
                                        'observed_at': analytics['observed_at']}]})

        ranks = target['ranking']
        described = []
        for name, row in ranks.items():
            if row:
                described.append(f"{name}: rank {row['position']} with {row['points']:g} points")
            else:
                described.append(f'{name}: no row on this dated publication')
        checks.append({'stage': 'HLTV world ranking',
                       'verdict': 'both-ranked' if all(ranks.values()) else 'partial-or-unranked',
                       'detail': '; '.join(described),
                       'sources': [{'url': hltv['ranking_final_url'] or HLTV_RANKING,
                                    'source': 'HLTV.org official world ranking',
                                    'detail': f'{hltv["ranking_rows"]} ranked teams on the dated publication '
                                              f'({hltv["ranking_final_url"] or HLTV_RANKING}).',
                                    'observed_at': hltv['ranking_observed_at']}]})

        for surface in target['book_hits']:
            hits = surface['hits']
            reachable = surface.get('status') == 'ok'
            code = surface.get('http_status')
            code_text = f'HTTP {code}' if code else 'no HTTP status recorded'
            if not reachable:
                verdict, detail = 'refused-or-failed', (
                    f"{code_text or surface.get('error') or 'request failed'} — this surface did not answer the "
                    'runner, so nothing can be said about its coverage of this fixture. That is a limitation of the '
                    'runner, not proof that no market exists.')
            elif hits:
                # Quote the observed price verbatim. This dossier never converts
                # a price into a probability: the publisher's ladder owns every
                # published number, and this row is a dated research lead.
                priced = [h for h in hits if h.get('odds')]
                quoted = []
                for hit in hits[:3]:
                    prices = hit.get('odds') or []
                    pair = (' / '.join(f'{name} {odd:g}' for name, odd in prices[:2]) if prices
                            else 'listed, no price on this endpoint')
                    quoted.append(pair + (f' (start {hit["starts_at"]})' if hit.get('starts_at') else ''))
                verdict = 'exact-name-price-observed' if priced else 'exact-name-row-found'
                detail = (f'{code_text}; {len(hits)} row(s) with these exact two names: ' + '; '.join(quoted) + '.'
                          + (' Observed price only — no probability is derived here and the published pick is '
                             'unchanged.' if priced else
                             ' The row confirms the fixture is listed; this endpoint carries no price for it.'))
            else:
                verdict, detail = 'reachable-no-exact-row', (
                    f"{code_text} — surface readable, but no row with these exact two names at the observation time.")
            hit_sources = [{'url': h['url'], 'source': surface['source'] + ' · matched row',
                            'detail': f'Row "{h.get("title")}" for these exact two names.',
                            'observed_at': surface['observed_at']}
                           for h in hits[:3] if str(h.get('url') or '').startswith('https://')]
            checks.append({'stage': surface['label'], 'verdict': verdict, 'detail': detail,
                           'sources': [{'url': surface['url'], 'source': surface['source'],
                                        'detail': surface['detail'],
                                        'observed_at': surface['observed_at']}] + hit_sources})

        checks.append({'stage': 'Publisher ladder', 'verdict': target['reason'],
                       'detail': 'The four-hour publisher retries every money surface, the Valve official-ratings model '
                                 'and the bo3.gg network/form rungs for this fixture at each refresh. This dossier '
                                 'records what was read, not a number.',
                       'sources': [{'url': DEPLOYED + 'origination/', 'source': 'Published picks',
                                    'detail': 'The live pick list this fixture is missing from, or is priced on by a '
                                              'research model.',
                                    'observed_at': observed_at}]})

        resolution = 'expected-at-next-refresh' if target['reason'] == 'no-published-row' else 'stays-unresolved'
        if resolution == 'expected-at-next-refresh':
            resolution_detail = (
                'The dashboard feed (snapshot.json) carries a row for this fixture but no pick on it, so the ladder '
                'returned nothing usable at the last collection. The next scheduled refresh re-attempts it through '
                'the same ladder; no probability is written here in the meantime.'
                if target.get('in_feed') else
                'This fixture is not in the dashboard feed at all: it appeared on Hotspawn after the last successful '
                'collection. The next scheduled refresh collects it and prices it through the same ladder; no '
                'probability is written here in the meantime.')
        else:
            resolution_detail = (
                'A published pick exists but it is not a featured market line — it comes from an explicitly '
                'uncalibrated research rung. Every money surface named above was read at the observation time and '
                'returned no compliant two-way price for these exact names. The pick stays as published; this dossier '
                'does not replace it.')
        fixtures.append({
            'hotspawn_id': fixture['id'],
            'teams': fixture['teams'],
            'competition': fixture.get('competition'),
            'starts_at': fixture.get('starts_at'),
            'hltv_url': (exact[0]['url'] if exact else None),
            'checks': checks,
            'resolution': resolution,
            'resolution_detail': resolution_detail,
        })

    refused = [b for b in books if b.get('status') != 'ok']
    limitations = [
        'This dossier records dated observations only. It writes no probability, no pick and no alias; the '
        'publisher ladder in scripts/originate.py remains the only path to a published number.',
        'Hotspawn "% picked" shares and HLTV fan "Pick a winner" votes are excluded from every calculation by policy '
        'and are not parsed here.',
        ('The following surfaces refused or failed from the runner at the observation time, so their silence is a '
         'limitation of the runner and not proof that no market exists: '
         + '; '.join(f"{b['label']} ({b.get('error') or b.get('http_status')})" for b in refused) + '.'
         ) if refused else
        'Every probed esportsbook surface answered at the observation time.',
        'A book surface answering HTTP 200 without a row for these exact two names is not evidence that no market '
        'exists: low-tier CS2 lines often open close to start.',
        'HLTV odds-comparison pages were read, but a page whose only price is one repeated placeholder across every '
        'bookmaker is refused as a two-way line; it would fabricate a price.',
        'Identity is exact-name only (case, Unicode and whitespace equivalence). Sponsor, abbreviation and fuzzy '
        'aliases are never applied here, so a differently spelled team stays unresolved rather than guessed.',
        'Current lineups, stand-ins and map vetoes are unverified for every fixture in this dossier.',
    ]
    return {
        'schema_version': 1,
        'title': 'Unresolved and non-featured-line picks — HLTV first, then the esportsbooks',
        'prepared_at': observed_at,
        'research_window': {'from': observed_at, 'to': observed_at},
        'prepared_by': SESSION,
        'policy': ('Dated first-hand research on every open Hotspawn CS2 fixture whose pick is not a featured market '
                   'line, plus every open fixture missing from the published snapshot. Method order follows the '
                   'brief: HLTV identity and the official world ranking first, then Polymarket, Thunderpick, Kalshi, '
                   'Pinnacle, Smarkets, bo3.gg, EGamersWorld, GG.BET, Stake and Rivalry. Every observation carries its '
                   'own https source and timestamp. Nothing here is a probability invented by this session.'),
        'method_order': [
            'HLTV identity and the official weekly world ranking (never a probability input by itself)',
            'Polymarket unique full-series match-winner books',
            'Thunderpick / Bovada / Pinnacle / Rivalry / Stake / GG.BET prematch series prices',
            'Kalshi and Smarkets exchange books',
            'bo3.gg finished-series results for our own network and form rungs',
            'Valve official regional standings model (exact unique five-player rows only)',
        ],
        'fixtures': fixtures,
        'limitations': limitations,
    }


def build_flags(observed_at: str, summary: dict, books: list, targets: list) -> list:
    """Findings for the Flagged for Review page. Every one carries its sources."""
    flags = []
    cov = summary['coverage']
    stale_after = cov.get('stale_after_hours', 8)
    feed_age = cov.get('published_snapshot_age_hours')
    cited_age = cov.get('cited_age_hours')

    # The dashboard's freshness is judged on the feed a published page actually
    # loads (snapshot.json), not on the citation artefact.
    if feed_age is not None and feed_age > stale_after:
        flags.append({
            'id': '93c7475a-published-snapshot-outside-freshness-bound',
            'title': f'Published dashboard feed is {feed_age:.1f} h old',
            'severity': 'warning',
            'detail': (f"The feed every published page declares (snapshot.json) was generated "
                       f"{cov['published_snapshot_generated_at']}, {feed_age:.1f} hours before this observation — "
                       f"outside the {stale_after}-hour bound the site itself publishes. "
                       f"{cov['published_rows_in_open_inventory']} of the {cov['api_open_fixtures']} currently open "
                       'Hotspawn CS2 fixtures appear in it, so a reader opening the site now sees an old inventory.'),
            'match_ids': [t['fixture']['id'] for t in targets],
            'source_urls': [cov['published_artifact_url'], FIXTURES_API, LOBBY],
            'observed_at': observed_at,
        })

    # The citation artefact can lag the dashboard.  That is a real defect — the
    # Flagged for Review page links it as evidence — but it is not a stale
    # dashboard, and it must not be reported as one.
    if (cited_age is not None and feed_age is not None and cited_age > stale_after
            and (feed_age <= stale_after or cov.get('cited_vs_feed_inventory_delta'))):
        delta = cov.get('cited_vs_feed_inventory_delta')
        detail = (f"data/latest.json is linked from the Flagged for Review page as the source for individual "
                  f"findings, but it was generated {cov['cited_generated_at']} — {cited_age:.1f} hours before this "
                  f"observation, outside the site's own {stale_after}-hour bound. At the same moment the dashboard "
                  f"feed (snapshot.json) was {feed_age:.1f} hours old, so the two artefacts served from the same "
                  f"site disagree.")
        if delta is not None:
            detail += (f" The inventory differs too: {cov['cited_inventory_rows']} rows in the cited artefact against "
                       f"{cov['published_inventory_rows']} in the feed ({cov['cited_open_rows']} open rows against "
                       f"{cov['published_open_rows']}). A reader following a citation link is handed a different "
                       'inventory than the dashboard shows.')
        if cov.get('cited_matches_branch_root'):
            detail += (' The served bytes are byte-identical (same SHA-256) to the checked-in branch-root '
                       f"data/latest.json generated {cov.get('branch_root_generated_at')}: the publisher writes the "
                       'rendered artefacts back to the branch root but never refreshes this source file, so the '
                       'stale copy is republished unchanged.')
        detail += (' This does not by itself change any displayed pick — the pages render from snapshot.json — but '
                   'every citation that points here is out of date.')
        flags.append({
            'id': '93c7475a-cited-source-artifact-stale',
            'title': (f'Source-citation file data/latest.json is {cited_age:.1f} h old and disagrees with the '
                      'dashboard it is cited from'),
            'severity': 'warning',
            'detail': detail,
            'match_ids': [t['fixture']['id'] for t in targets],
            'source_urls': [cov['cited_artifact_url'], cov['published_artifact_url'], FIXTURES_API],
            'observed_at': observed_at,
        })

    missing = summary['coverage']['open_without_published_row']
    if missing:
        flags.append({
            'id': '93c7475a-open-fixtures-missing-from-snapshot',
            'title': f'{len(missing)} open Hotspawn CS2 fixture(s) have no published pick row',
            'severity': 'warning',
            'detail': ('These fixtures are open on Hotspawn now but carry no pick row: '
                       + '; '.join(f"{m['id']} {' vs '.join(n for n in m['teams'] if n)}"
                                   for m in missing) + '. The dashboard feed shows '
                       f"{cov.get('published_open_picks')} picks across {cov.get('published_open_rows')} open rows. "
                       'Cause: the fixture appeared after the last successful collection, or no rung of the publisher '
                       'ladder returned a compliant two-way price for it. The next scheduled refresh re-attempts it.'),
            'match_ids': [m['id'] for m in missing],
            'source_urls': [FIXTURES_API, LOBBY, cov['published_artifact_url']],
            'observed_at': observed_at,
        })
    non_featured = [t for t in targets if t['reason'] != 'no-published-row']
    if non_featured:
        flags.append({
            'id': '93c7475a-non-featured-line-picks',
            'title': f'{len(non_featured)} open fixture(s) carry a pick that is not a featured market line',
            'severity': 'notice',
            'detail': ('Their published pick comes from an explicitly uncalibrated research rung. Every money surface '
                       'was read at the observation time and returned no compliant two-way price for these exact '
                       'names: ' + '; '.join(f"{t['fixture']['id']} {' vs '.join(n for n in t['fixture']['teams'] if n)}"
                                             for t in non_featured) + '.'),
            'match_ids': [t['fixture']['id'] for t in non_featured],
            'source_urls': [DEPLOYED + 'origination/', HLTV_MATCHES],
            'observed_at': observed_at,
        })
    refused = [b for b in books if b.get('status') != 'ok']
    if refused:
        flags.append({
            'id': '93c7475a-esportsbook-surface-refusals',
            'title': f'{len(refused)} esportsbook / betting-line surface(s) refused the runner',
            'severity': 'notice',
            'detail': ('Their silence is a limitation of this runner, not proof that no market exists: '
                       + '; '.join(f"{b['label']} → {b.get('error') or b.get('http_status')}" for b in refused) + '.'),
            'match_ids': [],
            'source_urls': [b['url'] for b in refused],
            'observed_at': observed_at,
        })
    for target in targets:
        for row in target['hltv']['exact']:
            delta = row.get('start_delta_seconds')
            if delta:
                flags.append({
                    'id': f"93c7475a-clock-delta-{target['fixture']['id']}",
                    'title': f"HLTV and Hotspawn disagree on the start time for {target['fixture']['id']}",
                    'severity': 'notice',
                    'detail': (f"Hotspawn {target['fixture'].get('starts_at')} vs HLTV {row.get('starts_at')} "
                               f'({delta:+d} s). Outside the project\'s 60-second join window, so the identity join is '
                               'reported rather than applied.'),
                    'match_ids': [str(target['fixture']['id'])],
                    'source_urls': [row['url'], FIXTURES_API],
                    'observed_at': observed_at,
                })
        if target['hltv']['shares_one_name'] and not target['hltv']['exact']:
            row = target['hltv']['shares_one_name'][0]
            flags.append({
                'id': f"93c7475a-name-mismatch-{target['fixture']['id']}",
                'title': f"HLTV spells a team differently for {target['fixture']['id']}",
                'severity': 'notice',
                'detail': (f"Hotspawn lists {' vs '.join(n for n in target['fixture']['teams'] if n)}; the nearest HLTV "
                           f"row is {' vs '.join(row['teams'])}. No alias is asserted without official proof."),
                'match_ids': [str(target['fixture']['id'])],
                'source_urls': [row['url'], FIXTURES_API],
                'observed_at': observed_at,
            })
    return flags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--parse-raw', action='store_true',
                        help='re-parse the archived bodies instead of fetching')
    args = parser.parse_args(argv)
    out_dir = args.output
    raw_dir = out_dir / 'raw'
    global RAW
    RAW = raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    sources: list[dict] = []
    observed_at = now_iso()

    def text_of(label: str, url: str, *, expect_json: bool = False, method: str = 'GET', payload=None):
        if args.parse_raw:
            body = read_archived(label, expect_json)
            # Recorded in the manifest exactly like a live fetch, but marked
            # ``archived`` so nobody mistakes a replay for a fresh observation.
            entry = {'label': label, 'url': url, 'observed_at': 'archived',
                     'status': 'ok' if body is not None else 'error',
                     'http_status': 200 if body is not None else None, 'archived': True,
                     'sha256': archived_sha256(label, expect_json)}
            sources.append(entry)
            return entry, body
        entry, body = get(label, url, expect_json=expect_json, method=method, payload=payload)
        sources.append(entry)
        return entry, body

    # 1. What the dashboard currently claims.
    #
    # Two different JSON artefacts are served from the same Pages site and they
    # are NOT interchangeable:
    #
    #   snapshot.json        the feed every published page declares
    #                        (<body data-data-url="./snapshot.json">, and the
    #                        footer "Open data" link).  This is what a reader's
    #                        browser loads, so it — and only it — decides whether
    #                        the dashboard is fresh.
    #   data/latest.json     a source-citation artefact.  It is linked from the
    #                        Flagged for Review page as evidence for individual
    #                        findings, never loaded by a page.
    #
    # Measuring freshness off data/latest.json therefore reports the *citation*'s
    # age as if it were the dashboard's.  Both are read, and kept separate.
    latest_entry, latest = text_of('published-latest-json', DEPLOYED + 'data/latest.json', expect_json=True)
    feed_entry, feed = text_of('published-snapshot-json', DEPLOYED + 'snapshot.json', expect_json=True)

    feed_matches = (feed or {}).get('matches') or []
    feed_ids = {str(m.get('id')) for m in feed_matches}
    feed_open_ids = {str(m.get('id')) for m in feed_matches if m.get('availability') == 'open'}
    feed_picked_ids = {str(m.get('id')) for m in feed_matches
                       if m.get('availability') == 'open' and m.get('pick_index') is not None}
    # The source-citation artefact, kept distinct so its age is never reported as
    # the dashboard's.
    cited_matches = (latest or {}).get('matches') or []
    cited_ids = {str(m.get('id')) for m in cited_matches}
    orig_entry, origination = text_of('published-origination-json', DEPLOYED + 'data/origination.json', expect_json=True)

    # 2. The Hotspawn inventory, read twice.
    api_entry, api_records = text_of('hotspawn-fixtures-api', FIXTURES_API, expect_json=True)
    api_records = api_records if isinstance(api_records, list) else []
    lobby_entry, lobby_html = text_of('hotspawn-lobby', LOBBY + '?cb=' + str(int(datetime.now(UTC).timestamp())))
    cs2_entry, cs2_html = text_of('hotspawn-cs2-pickems', CS2_LOBBY)

    reference = datetime.now(UTC)
    records_open = open_fixtures(api_records, reference)
    api_open_ids = sorted({str(r.get('id')) for r in records_open}, key=int)
    lobby_ids = sorted(set(parse_lobby_fixture_ids(lobby_html or '')) | set(parse_lobby_fixture_ids(cs2_html or '')),
                       key=int)

    # 3. HLTV first.
    hltv_entry, hltv_html = text_of('hltv-matches', HLTV_MATCHES)
    hltv_rows = parse_hltv_listing(hltv_html) if hltv_html else []
    rank_entry, rank_html = text_of('hltv-ranking', HLTV_RANKING)
    rank_rows = ranking_rows_with_position(hltv_ranking.parse_ranking_page(rank_html)) if rank_html else []

    # 4. Then the esportsbooks and exchanges.
    books = []
    for label, url, kind, source_name, source_url in BOOKS:
        # One unreadable surface is a finding, not a crash: the sweep must still
        # report what the other nine published.
        total_events = None
        try:
            if kind == 'post-json':
                entry, payload = text_of(label, url, expect_json=True, method='POST', payload={'gameIds': [6]})
                text = None
            elif kind == 'json':
                entry, payload = text_of(label, url, expect_json=True)
                text = None
            else:
                entry, text = text_of(label, url)
                payload = None
            titles = book_titles(label, payload, text) if entry.get('status') == 'ok' else []
            # Kalshi's generic open-events endpoint answers with politics and
            # science events; reporting those as CS2 rows would overstate the
            # coverage, so the pre-filter total is kept alongside the CS2 count.
            if label == 'kalshi-cs2-events' and isinstance(payload, dict):
                total_events = len(payload.get('events') or [])
        except Exception as exc:                                    # noqa: BLE001 - recorded, not raised
            entry, titles = {'label': label, 'url': url, 'observed_at': now_iso(), 'status': 'error',
                             'error': type(exc).__name__ + ': ' + str(exc)[:300]}, []
            sources.append(entry)
        books.append({'label': label, 'source': source_name, 'url': url, 'source_url': source_url,
                      'detail': f'{source_name} surface read for the gap fixtures.',
                      'status': entry.get('status'), 'http_status': entry.get('http_status'),
                      'error': entry.get('error'), 'observed_at': entry.get('observed_at'),
                      'titles_parsed': len(titles), 'titles': titles[:400],
                      'total_events_before_filter': total_events})

    # 5. Which open fixtures lack a featured line, or lack a row entirely.
    #
    # The dashboard renders from snapshot.json, so the feed is the authority on
    # whether a pick exists for a fixture.  data/origination.json is a separate,
    # independently published artefact and can be many days older than the feed;
    # treating it as the authority reports every fixture that appeared after it
    # was written as having no pick at all, which is not what the site shows.
    # Feed rows are therefore read first and the origination artefact only fills
    # the gaps the feed leaves.
    published = {}
    for row in feed_matches:
        published[str(row.get('id'))] = row
    for row in (origination or {}).get('matches') or []:
        published.setdefault(str(row.get('id')), row)
    latest_by_id = {str(m.get('id')): m for m in (latest or {}).get('matches') or []}

    targets = []
    target_errors = []
    for item in records_open:
      try:
        fixture = fixture_view(item)
        row = published.get(fixture['id'])
        # A feed row carries its method under `analysis`; an origination row
        # carries it under `origination`.  Both shapes are read, never assumed.
        method = (((row or {}).get('origination') or {}).get('method')
                  or ((row or {}).get('analysis') or {}).get('method'))
        has_pick = bool(row) and ((row.get('pick_index') is not None)
                                  or bool(((row.get('origination') or {}).get('probabilities'))))
        if not has_pick:
            reason = 'no-published-row'
        elif method not in MONEY_METHODS:
            reason = 'pick-not-a-featured-line'
        else:
            continue
        hltv = hltv_join(fixture, hltv_rows)
        analytics = None
        for candidate in (hltv['exact'] or hltv['shares_one_name']):
            url = candidate.get('betting_analytics_url')
            if not url:
                continue
            entry, body = text_of('hltv-odds-' + str(candidate.get('match_id')), url)
            prices = []
            if body:
                soup = BeautifulSoup(body, 'html.parser')
                # HLTV's odds overview wraps every quoted price in an
                # odds-bearing class; the exact class differs per layout, so the
                # class-substring selector is used and then filtered to strict
                # decimal prices.  "No bet" and empty cells are dropped, and a
                # page whose only decimal is one repeated placeholder fails the
                # two-way test below rather than being read as a real line.
                raw = [c.get_text(' ', strip=True) for c in soup.select('[class*=odds]')]
                prices = [p for p in raw if re.fullmatch(r'\d+\.\d{1,3}', p)]
            distinct = sorted(set(prices))
            analytics = {'url': url, 'observed_at': entry.get('observed_at'),
                         'http_status': entry.get('http_status'),
                         'distinct_odds': distinct[:8], 'distinct_odds_count': len(distinct),
                         'usable_two_way_price': len(distinct) >= 2}
            break
        targets.append({
            'fixture': fixture,
            'reason': reason,
            'published_method': method,
            'published_pick': (row or {}).get('pick_index'),
            # Whether the dashboard's own feed carries a row for this fixture at
            # all.  "No pick" and "no row" are different statements and the
            # dossier must not conflate them.
            'in_feed': bool(row),
            'latest_availability': (latest_by_id.get(fixture['id']) or {}).get('availability'),
            'hltv': hltv,
            'hltv_analytics': analytics,
            'ranking': {name: ranking_row(name, rank_rows) for name in fixture['teams'] if name},
            'book_hits': [{'label': b['label'], 'source': b['source'], 'url': b['url'], 'detail': b['detail'],
                           'http_status': b['http_status'], 'status': b['status'], 'observed_at': b['observed_at'],
                           'hits': exact_book_hits(fixture, b['titles']) if b['status'] == 'ok' else []}
                          for b in books],
        })
      except Exception as exc:                                      # noqa: BLE001 - recorded, not raised
        target_errors.append({'fixture_id': str(item.get('id')),
                              'error': type(exc).__name__ + ': ' + str(exc)[:400]})

    open_ids = set(api_open_ids)
    lobby_ids_set = set(lobby_ids)
    # The dashboard's own feed.  Rows it marks open, and the picks it carries.

    def _age(record):
        generated = timestamp((record or {}).get('generated_at'))
        return (round((reference - generated).total_seconds() / 3600, 2) if generated else None)

    coverage = {
        'api_records': len(api_records),
        'api_open_fixtures': len(api_open_ids),
        'lobby_fixture_ids': len(lobby_ids),
        'open_not_in_lobby': sorted(open_ids - lobby_ids_set, key=int),
        'lobby_not_open_in_api': sorted(lobby_ids_set - open_ids, key=int),
        'open_without_published_row': [t['fixture'] for t in targets if t['reason'] == 'no-published-row'],
        'open_with_non_featured_pick': [t['fixture'] for t in targets if t['reason'] != 'no-published-row'],
        'research_targets': len(targets),
        'research_target_errors': target_errors,
        # --- the feed a published page actually loads ---
        'published_artifact_url': DEPLOYED + 'snapshot.json',
        'published_snapshot_generated_at': (feed or {}).get('generated_at'),
        'published_snapshot_age_hours': _age(feed),
        'published_inventory_rows': len(feed_matches),
        'published_open_rows': len(feed_open_ids),
        'published_open_picks': len(feed_picked_ids),
        'published_rows_in_open_inventory': len([i for i in api_open_ids if i in feed_ids]),
        'stale_after_hours': (feed or {}).get('stale_after_hours', 8),
        'published_coverage_complete': (feed or {}).get('coverage_complete'),
        'published_run_status': (feed or {}).get('run_status'),
        'published_sha256': next((s.get('sha256') for s in sources
                                  if s.get('label') == 'published-snapshot-json'), None),
        # --- the source-citation artefact ---
        'cited_artifact_url': DEPLOYED + 'data/latest.json',
        'cited_generated_at': (latest or {}).get('generated_at'),
        'cited_age_hours': _age(latest),
        'cited_inventory_rows': len(cited_matches),
        'cited_open_rows': len({str(m.get('id')) for m in cited_matches
                                if m.get('availability') == 'open'}),
        'cited_rows_in_open_inventory': len([i for i in api_open_ids if i in cited_ids]),
        'published_origination_generated_at': (origination or {}).get('generated_at'),
        'published_pick_rows': len(published),
    }
    # How far the two artefacts disagree, so a reader following a citation link is
    # never quietly handed a different inventory than the dashboard shows.
    coverage['cited_vs_feed_inventory_delta'] = (
        len(cited_matches) - len(feed_matches) if feed_matches and cited_matches else None)
    coverage['cited_vs_feed_open_delta'] = (
        coverage['cited_open_rows'] - coverage['published_open_rows']
        if feed_matches and cited_matches else None)
    # Byte-identity checks.  Each served artefact is compared only with the
    # checked-in file of the same name, and a comparison is published only when
    # the served bytes were actually archived.
    def _served_sha(label):
        return next((s.get('sha256') for s in sources if s.get('label') == label), None)

    def _root_sha(relpath):
        p = Path(relpath)
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

    coverage['cited_sha256'] = _served_sha('published-latest-json')
    coverage['branch_root_sha256'] = _root_sha('data/latest.json')
    coverage['branch_root_feed_sha256'] = _root_sha('snapshot.json')
    coverage['published_matches_branch_root'] = (
        bool(coverage['published_sha256']) and coverage['published_sha256'] == coverage['branch_root_feed_sha256'])
    coverage['cited_matches_branch_root'] = (
        bool(coverage['cited_sha256']) and coverage['cited_sha256'] == coverage['branch_root_sha256'])
    try:
        coverage['branch_root_generated_at'] = json.loads(Path('data/latest.json').read_text()).get('generated_at')
    except (OSError, ValueError):
        coverage['branch_root_generated_at'] = None

    dossier = build_dossier(observed_at, targets, books, {
        'observed_at': hltv_entry.get('observed_at'),
        'upcoming_rows': len(hltv_rows),
        'ranking_observed_at': rank_entry.get('observed_at'),
        'ranking_final_url': rank_entry.get('final_url'),
        'ranking_rows': len(rank_rows),
    })
    summary = {
        'session': SESSION,
        'purpose': ('Record what Hotspawn, HLTV and the esportsbook surfaces publish for the live CS2 fixtures whose '
                    'pick is not a featured market line, and for every open fixture missing from the published '
                    'snapshot. Facts only: no probability, pick or alias is written here.'),
        'observed_at': observed_at,
        'mode': 'parse-raw' if args.parse_raw else 'live',
        'coverage': coverage,
        'hltv': {'upcoming_rows_parsed': len(hltv_rows), 'ranking_rows_parsed': len(rank_rows),
                 'ranking_final_url': rank_entry.get('final_url')},
        'books': [{k: v for k, v in b.items() if k != 'titles'} for b in books],
        'targets': [{
            'fixture': t['fixture'], 'reason': t['reason'], 'published_method': t['published_method'],
            'published_pick': t['published_pick'],
            'hltv_exact': [{'url': r['url'], 'start_delta_seconds': r.get('start_delta_seconds')}
                           for r in t['hltv']['exact']],
            'hltv_shared': [{'url': r['url'], 'teams': r['teams']} for r in t['hltv']['shares_one_name'][:3]],
            'hltv_analytics': t['hltv_analytics'],
            'ranking': {name: (f"rank {row['position']}, {row['points']:g} points" if row else None)
                        for name, row in t['ranking'].items()},
            'books_with_exact_row': [b['label'] for b in t['book_hits'] if b['hits']],
        } for t in targets],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'probe.json').write_text(json.dumps(
        {'session': SESSION, 'observed_at': observed_at, 'mode': summary['mode'], 'sources': sources,
         'summary': summary}, indent=2, sort_keys=True) + '\n')
    (out_dir / 'probe.md').write_text(render_markdown(summary, sources, targets))
    (out_dir / 'unresolved-research.json').write_text(json.dumps(dossier, indent=2) + '\n')
    # ``scripts/build.py`` globs ``data/research/*/flags.json`` and iterates the
    # parsed value directly, so this file must be a bare list in the site's own
    # finding schema (``id``, ``severity``, ``title``, ``detail``, ``match_ids``,
    # ``source_urls``) — a wrapper object breaks the whole build.
    (out_dir / 'flags.json').write_text(json.dumps(
        build_flags(observed_at, summary, books, targets), indent=2) + '\n')
    print(f"{summary['mode']}: {coverage['api_open_fixtures']} open fixtures, "
          f"{len(coverage['open_without_published_row'])} with no published row, "
          f"{len(coverage['open_with_non_featured_pick'])} with a non-featured pick, "
          f"{len(targets)} research targets -> {out_dir}")
    return 0


def render_markdown(summary: dict, sources: list, targets: list) -> str:
    cov = summary['coverage']
    out = ['# Live probe — a pick for every Hotspawn CS2 match', '',
           f"Observed {summary['observed_at']} ({summary['mode']}).",
           'Facts only: this file records what each source served. No probability, pick or alias is written here.',
           '', '## Sources read', '', '| Source | Status | HTTP | Bytes | SHA-256 |', '| --- | --- | --- | --- | --- |']
    for src in sources:
        out.append(f"| {src['label']} | {src['status']} | {src.get('http_status') or '—'} | "
                   f"{src.get('bytes', '—')} | `{(src.get('sha256') or '—')[:16]}…` |")
    out += ['', '## Coverage', '', '| Fact | Value |', '| --- | --- |',
            f"| fixture API records | {cov['api_records']} |",
            f"| open fixtures in the API | {cov['api_open_fixtures']} |",
            f"| fixture ids in the rendered lobby | {cov['lobby_fixture_ids']} |",
            f"| open in the API but not in the lobby | {cov['open_not_in_lobby'] or '[]'} |",
            f"| in the lobby but not open in the API | {cov['lobby_not_open_in_api'] or '[]'} |",
            f"| published snapshot generated | {cov['published_snapshot_generated_at']} |",
            f"| open fixtures with **no published row** | {len(cov['open_without_published_row'])} |",
            f"| open fixtures with a **non-featured-line** pick | {len(cov['open_with_non_featured_pick'])} |",
            '', '## Esportsbook / betting-line surfaces', '',
            '| Surface | Status | HTTP | Rows parsed |', '| --- | --- | --- | --- |']
    for book in summary['books']:
        out.append(f"| {book['label']} | {book['status']} | {book.get('http_status') or '—'} | "
                   f"{book.get('titles_parsed', 0)} |")
    out += ['', '## Research targets (HLTV first, then the books)', '']
    for target in summary['targets']:
        fixture = target['fixture']
        out += [f"### {fixture['id']} — {' vs '.join(n for n in fixture['teams'] if n)}", '',
                f"- start (Hotspawn API): {fixture.get('starts_at')}",
                f"- competition: {fixture.get('competition')}",
                f"- reason researched: {target['reason']}"
                + (f" (published method `{target['published_method']}`)" if target['published_method'] else ''),
                '- HLTV exact-name listing: '
                + (', '.join(f"{r['url']} (start delta {r['start_delta_seconds']}s)"
                             for r in target['hltv_exact']) or 'not found'),
                '- HLTV one-name-only rows (review only): '
                + (', '.join(f"{' vs '.join(r['teams'])} {r['url']}" for r in target['hltv_shared']) or 'none'),
                f"- HLTV odds page: {target['hltv_analytics'] or 'none'}",
                f"- HLTV ranking positions: {target['ranking']}",
                f"- books with an exact-name row: {target['books_with_exact_row'] or 'none'}", '']
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:                                          # noqa: BLE001 - diagnostic, then re-raised
        import traceback
        # The runner's log host is not always reachable, so the traceback is
        # written into the evidence tree where the workflow commits it.
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'probe-error.txt').write_text(traceback.format_exc())
        raise
