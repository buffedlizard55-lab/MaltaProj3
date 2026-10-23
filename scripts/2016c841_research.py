"""Session arena-2016c841 — dated line-source research for fixtures with no external betting line.

Read-only research. The user brief asks for a pick or a sourced probability for
*every* Hotspawn CS2 fixture, and for the fixtures the featured method cannot
resolve (low tier, or not listed on Polymarket/books we can read) the brief asks
for research in this order: **HLTV first, then esportsbooks and esports betting
lines** — plus a separate, source-linked register of what could not be resolved
and why, included in the executive summary.

This probe is the 2026-10-23 mid-morning sweep. It extends the already-merged
arena-17d77cb3 / arena-46ade650 approach and never writes a probability, a pick
or an alias, and it never edits a published row:

* a fixture's *current* method is read from the live published origination
  snapshot (falling back to the checked-in one, and the source used is
  recorded), so the probe works on the same rows a reader sees;
* a "no external line" fixture is one whose published method is a research
  model (model / network / form / guidance / reference) or that is unresolved
  in the published snapshot;
* HLTV is tried first for identity (a match or ranking page). HLTV publishes no
  two-sided prematch money line, so it is never a price source; the Arena
  workspace companion record ``hltv-platform-sweep.md`` carries the platform-side
  HLTV reads with quoted text and links;
* bo3.gg's public match API is queried for an *upcoming* row joining BOTH team
  names plus a start time inside ``RELAY_START_TOLERANCE_SEC``. A joined row is
  a *lead* only if its ``bet_updates`` block names a bookmaker and two active
  coefficients; the block is copied verbatim, never converted into a
  probability here (that is the reviewed ladder's job);
* Smarkets' public documented exchange API is swept the same way: upcoming
  ``csgo_match`` events are bound on BOTH names plus the 60-second start window
  (the reviewed ``scripts.smarkets_lines.binds`` rule), and the raw
  events/markets/quotes responses are copied verbatim (integer 1/10000 quotes —
  evidence the reviewed ladder replays, never a probability created here);
* every other bookmaker/aggregator surface records its HTTP status only. A 200
  is not a price;
* the live Hotspawn lobby inventory is compared fixture-by-fixture with the
  live published snapshot, so the executive summary's coverage-gap register can
  quote a sweep hours newer than the archived one.

Usage: python -m scripts.2016c841_research [--out data/research/2016c841]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from scripts.smarkets_lines import binds as smarkets_binds
from scripts.smarkets_lines import events_url as smarkets_events_url
from scripts.smarkets_lines import event_url as smarkets_event_url
from scripts.smarkets_lines import API as SMARKETS_API

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
HOTSPAWN_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
HOTSPAWN_LOBBY = 'https://play.hotspawn.com/lobby'
BO3_API = 'https://api.bo3.gg/api/v1'
BO3_HEADERS = {'Origin': 'https://bo3.gg', 'Referer': 'https://bo3.gg/',
               'Accept': 'application/json'}
LIVE_ORIGINATION = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json'
LIVE_LATEST = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json'
MODEL_METHODS = {'model', 'network', 'form', 'guidance', 'reference'}
RELAY_START_TOLERANCE_SEC = 60

# HLTV first (identity only), then esportsbooks, exchanges and esports
# betting-line surfaces. Status codes only: an HTTP 200 landing page is not a
# prematch price.
PAGES = [
    ('HLTV match listing', 'https://www.hltv.org/matches'),
    ('HLTV world ranking', 'https://www.hltv.org/ranking/teams'),
    ('Thunderpick CS2', 'https://thunderpick.io/esports/counter-strike'),
    ('GG.BET CS2', 'https://gg.bet/en/counter-strike'),
    ('Stake CS2', 'https://stake.com/sports/esports/cs2'),
    ('BC.Game esports', 'https://bc.game/sports/esports'),
    ('Bet365 esports', 'https://www.bet365.com/'),
    ('Rivalry CS2', 'https://www.rivalry.com/esports/csgo-betting'),
    ('Betano esports', 'https://betano.com/'),
    ('Betsson esports', 'https://www.betsson.com/en'),
    ('Unibet esports', 'https://www.unibet.com/betting#filter/esports'),
    ('22bet esports', 'https://22bet.com/line/esports'),
    ('BetBoom CS2', 'https://betboom.ru/sport/cs2'),
    ('1xBet CS2', 'https://1xbet.com/en/line/counter-strike-2'),
    ('Marathonbet CS2', 'https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/'),
    ('Betway CS2', 'https://www.betway.com/en/sports/esports/counter-strike-2'),
    ('DraftKings CS2', 'https://sportsbook.draftkings.com/leagues/esports/counter-strike-2'),
    ('OddsPortal CS2', 'https://www.oddsportal.com/esports/counter-strike/'),
    ('Oddspedia CS2', 'https://oddspedia.com/esports/cs-go'),
    ('EGamersWorld CS2 matches', 'https://egamersworld.com/counterstrike/matches'),
    ('Pinnacle CS2', 'https://www.pinnacle.com/en/esports/counter-strike-2'),
    ('Kalshi CS2 series', 'https://api.elections.kalshi.com/trade-api/v2/series/KXCS2GAME'),
    ('Polymarket CS2 tag', 'https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2&active=true&closed=false&limit=1'),
    ('Smarkets CS2 exchange', smarkets_events_url(1)),
    ('bo3.gg matches API', BO3_API + '/matches?page[limit]=1&filter[matches.discipline_id][eq]=1'),
]
CHALLENGE = ('just a moment', 'cf-chl', 'challenge-platform', 'attention required',
             'enable javascript and cookies', 'captcha', 'access denied')


def environment_name() -> str:
    """Where this sweep ran.

    ``scripts.build.load_no_line_research`` only promotes a sweep that ran on a
    GitHub runner (``github-actions-runner``) with a sibling Markdown record, so
    a local, possibly network-blocked probe can never replace runner-verified
    evidence. Reporting the real environment is what keeps that rule honest.
    """
    return 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'local checkout'


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def stamp(value) -> datetime | None:
    text = str(value or '').strip()
    if text.isdigit() and len(text) >= 12:  # Hotspawn milliseconds
        return datetime.fromtimestamp(int(text) / 1000, UTC)
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(UTC)
    except ValueError:
        return None


def key(name) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(name or '').casefold())


def fetch(session: requests.Session, url: str, *, method: str = 'GET', headers=None,
          json_body=None, timeout: int = 25) -> dict:
    started = iso(datetime.now(UTC))
    try:
        response = session.request(method, url, headers=headers or {'User-Agent': UA},
                                   json=json_body, timeout=timeout)
    except requests.RequestException as exc:
        return {'url': url, 'method': method, 'observed_at': started,
                'http_status': None, 'error': f'{type(exc).__name__}: {exc}'[:200]}
    body = response.text or ''
    lowered = body[:4000].lower()
    return {'url': url, 'method': method, 'observed_at': started,
            'http_status': response.status_code,
            'content_type': response.headers.get('content-type'),
            'bytes': len(body),
            'challenge_page': any(token in lowered for token in CHALLENGE)}


def fetch_json(session: requests.Session, url: str, *, headers=None,
               timeout: int = 25) -> tuple[dict, dict]:
    """Status record plus parsed JSON body (never raises)."""
    started = iso(datetime.now(UTC))
    base = {'url': url, 'method': 'GET', 'observed_at': started}
    try:
        response = session.get(url, headers=headers or {'User-Agent': UA}, timeout=timeout)
    except requests.RequestException as exc:
        return {**base, 'http_status': None,
                'error': f'{type(exc).__name__}: {exc}'[:200]}, {}
    body = {}
    try:
        body = response.json()
    except ValueError:
        pass
    return {**base, 'http_status': response.status_code,
            'content_type': response.headers.get('content-type'),
            'bytes': len(response.text or '')}, body


def hotspawn_fixtures(session) -> tuple[list, dict]:
    attempt, payload = fetch_json(session, HOTSPAWN_API)
    rows = []
    if attempt.get('http_status') == 200:
        for item in payload if isinstance(payload, list) else []:
            start = stamp(item.get('scheduled_start_time'))
            rows.append({'id': str(item.get('id')),
                         'teams': [item.get('participants0_name'), item.get('participants1_name')],
                         'competition': item.get('competition_name'),
                         'starts_at': iso(start) if start else None,
                         'tier': item.get('tier')})
    attempt['fixtures'] = len(rows)
    return rows, attempt


def published_methods(session, local: Path | None = None) -> tuple[dict, dict]:
    """Current published method per Hotspawn fixture id.

    A local snapshot produced by this run's own ``scripts.originate --live`` is
    preferred (it is the freshest), then the live published file.
    """
    candidates = ([('local', str(local))] if local else []) + [('live', LIVE_ORIGINATION)]
    last = {}
    for source, url in candidates:
        if source == 'local':
            try:
                payload = json.loads(Path(url).read_text())
            except (OSError, ValueError) as exc:
                last = {'source': source, 'url': url,
                        'error': f'{type(exc).__name__}: {exc}'[:200]}
                continue
            attempt = {'source': source, 'url': url}
        else:
            attempt, payload = fetch_json(session, url)
            attempt['source'] = source
        if attempt.get('http_status') not in (None, 200):
            last = attempt
            continue
        if not isinstance(payload, dict) or not payload.get('matches'):
            last = {**attempt, 'error': 'no matches in payload'}
            continue
        methods = {}
        for match in payload.get('matches') or []:
            origin = match.get('origination') or {}
            methods[str(match.get('hotspawn_id') or match.get('id'))] = {
                'method': origin.get('method'),
                'label': origin.get('label'),
                'featured': bool(match.get('featured_method')),
                'probability': origin.get('probability'),
                'source_url': origin.get('source_url'),
                'generated_at': payload.get('generated_at')}
        return methods, {'source': source, 'url': url, 'http_status': 200,
                         'fixtures': len(methods),
                         'generated_at': payload.get('generated_at')}
    return {}, last


def hotspawn_match_url(teams: list, competition, fixture_id: str) -> str:
    """The public Hotspawn match URL for a fixture, in Hotspawn's own slug form.

    Hotspawn's fixture feed returns no URL, so the slug is built exactly as the
    site does: lowercased team names, " vs ", competition, then the fixture id,
    with every non-alphanumeric run collapsed to one hyphen
    (observed: BC.Game -> bc-game, Stake Pulse Beat III -> stake-pulse-beat-iii).
    """
    def slug(text) -> str:
        return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', str(text or '').casefold())).strip('-')
    parts = [slug(teams[0]) if len(teams) > 0 else '', 'vs',
             slug(teams[1]) if len(teams) > 1 else '', slug(competition), str(fixture_id)]
    return 'https://www.hotspawn.com/matches/' + '-'.join(p for p in parts if p)


def bo3_upcoming(session, pages: int = 3) -> tuple[list, list]:
    rows, attempts = [], []
    for page in range(pages):
        query = (f'/matches?page[offset]={page * 100}&page[limit]=100&sort=start_date'
                 '&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1'
                 '&with=teams,tournament')
        attempt, body = fetch_json(session, BO3_API + query, headers=BO3_HEADERS)
        attempts.append(attempt)
        if attempt.get('http_status') != 200:
            break
        chunk = body.get('results') or []
        rows.extend(chunk)
        if len(chunk) < 100:
            break
    return rows, attempts


def relay_block(row: dict) -> dict | None:
    """Verbatim copy of the bookmaker quote bo3.gg relays, or None."""
    block = row.get('bet_updates')
    if not isinstance(block, dict):
        return None
    sides = {}
    for side in ('team_1', 'team_2'):
        entry = block.get(side) or {}
        sides[side] = {'name': entry.get('name'), 'coeff': entry.get('coeff'),
                       'active': entry.get('active'), 'team_id': entry.get('team_id')}
    coeffs = [sides['team_1'].get('coeff'), sides['team_2'].get('coeff')]
    two_sided = (all(isinstance(c, (int, float)) and c > 1 for c in coeffs)
                 and sides['team_1'].get('active') is True
                 and sides['team_2'].get('active') is True)
    return {'provider': block.get('provider'), 'book_url': block.get('path'),
            'markets_count': block.get('markets_count'), 'sides': sides,
            'two_sided_price': two_sided}


def bind(teams: list, start: datetime | None, rows: list) -> tuple[dict | None, list]:
    """Exact both-name + start-window join; near misses are returned honestly."""
    wanted = {key(name) for name in teams if name}
    if len(wanted) != 2 or start is None:
        return None, []
    bound, near = None, []
    for row in rows:
        names = {(row.get('team1') or {}).get('name'), (row.get('team2') or {}).get('name')}
        row_start = stamp(row.get('start_date'))
        delta = int(abs((row_start - start).total_seconds())) if row_start else None
        if {key(n) for n in names if n} == wanted:
            if delta is not None and delta <= RELAY_START_TOLERANCE_SEC:
                bound = row
            else:
                near.append({'slug': row.get('slug'), 'teams': sorted(n for n in names if n),
                             'start': row.get('start_date'), 'start_delta_sec': delta,
                             'status': 'name match, start outside the 60s window'})
        elif {key(n) for n in names if n} & wanted and len(near) < 4:
            near.append({'slug': row.get('slug'), 'teams': sorted(n for n in names if n),
                         'start': row.get('start_date'), 'start_delta_sec': delta,
                         'status': 'one shared side only'})
    return bound, near


def smarkets_sweep(session, targets: list) -> tuple[dict, dict]:
    """Bind targets onto the Smarkets exchange board; copy raw responses.

    ``targets`` are ``{teams: [{name}], starts_at}``-shaped rows (the reviewed
    ``scripts.smarkets_lines.binds`` contract). Raw events/markets/quotes bodies
    are kept verbatim per bound fixture — integer 1/10000 quotes are the
    exchange's own words, and no decimal is ever divided out here.
    """
    attempt, body = fetch_json(session, smarkets_events_url())
    board = {'api': SMARKETS_API, 'events_attempt': attempt,
             'events_seen': 0, 'bound': 0, 'errors': []}
    per_fixture: dict[str, dict] = {}
    events = body.get('events') if isinstance(body, dict) else None
    if attempt.get('http_status') != 200 or not isinstance(events, list):
        board['errors'].append(attempt.get('error') or f"http {attempt.get('http_status')}")
        return board, per_fixture
    board['events_seen'] = len(events)
    bound_events = []
    for target in targets:
        hits = [e for e in events if isinstance(e, dict) and smarkets_binds(e, target)]
        if len(hits) == 1:
            bound_events.append((target, hits[0]))
    board['bound'] = len(bound_events)
    if not bound_events:
        return board, per_fixture
    joined_events = ','.join(str(e.get('id')) for _, e in bound_events)
    market_attempt, market_body = fetch_json(session, f'{SMARKETS_API}/events/{joined_events}/markets/')
    board['markets_attempt'] = market_attempt
    markets = [m for m in (market_body or {}).get('markets', []) if isinstance(m, dict)]
    by_event: dict[str, list] = {}
    for market in markets:
        # The reviewed rules exactly: only an open, visible two-way winner
        # market, and exactly one per event, may carry a quote.
        if ((market.get('market_type') or {}).get('name') != 'WINNER_2_WAY'
                or market.get('state') != 'open' or market.get('hidden') is True):
            continue
        by_event.setdefault(str(market.get('event_id')), []).append(market)
    usable: list[tuple[dict, dict, dict]] = []
    for target, event in bound_events:
        event_markets = by_event.get(str(event.get('id'))) or []
        entry = {'event_id': event.get('id'),
                 'event_name': event.get('name'),
                 'event_url': smarkets_event_url(event),
                 'start_datetime': event.get('start_datetime'),
                 'markets_verbatim': event_markets or None,
                 'quotes': None, 'two_sided': False}
        per_fixture[str(target.get('hotspawn_id'))] = entry
        if len(event_markets) != 1:
            # Zero: the exchange lists no open two-way winner market; more than
            # one is ambiguous. Neither may become a price.
            continue
        usable.append((target, event, event_markets[0]))
    if not usable:
        return board, per_fixture
    market_ids = [str(market.get('id')) for _, _, market in usable]
    joined_markets = ','.join(market_ids)
    contract_attempt, contract_body = fetch_json(session, f'{SMARKETS_API}/markets/{joined_markets}/contracts/')
    board['contracts_attempt'] = contract_attempt
    contracts = [c for c in (contract_body or {}).get('contracts', []) if isinstance(c, dict)]
    quote_attempt, quote_body = fetch_json(session, f'{SMARKETS_API}/markets/{joined_markets}/quotes/')
    board['quotes_attempt'] = quote_attempt
    quotes = quote_body if isinstance(quote_body, dict) else {}
    for target, event, market in usable:
        sides = [c for c in contracts if str(c.get('market_id')) == str(market.get('id'))
                 and c.get('state_or_outcome') == 'open']
        books = [quotes.get(str(side.get('id'))) or {} for side in sides]
        two_sided = len(sides) == 2 and all(b.get('bids') and b.get('offers') for b in books)
        per_fixture[str(target.get('hotspawn_id'))].update(
            {'market_id': market.get('id'),
             'contracts_verbatim': sides,
             # Keyed by contract id, the exchange's own integers (price/10000).
             'quotes': {str(side.get('id')): quotes.get(str(side.get('id'))) for side in sides},
             'two_sided': two_sided})
    return board, per_fixture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/research/2016c841'))
    parser.add_argument('--per-fixture-delay', type=float, default=0.0)
    parser.add_argument('--origination', type=Path, default=None,
                        help='local data/origination.json from this run (preferred over the live file)')
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    observed_at = iso(datetime.now(UTC))
    fixtures, hotspawn_attempt = hotspawn_fixtures(session)
    methods, method_source = published_methods(session, args.origination)
    rows, bo3_attempts = bo3_upcoming(session)

    providers = []
    for label, url in PAGES:
        attempt = fetch(session, url, headers=BO3_HEADERS if url.startswith(BO3_API) else None)
        attempt['label'] = label
        providers.append(attempt)
        time.sleep(0.2)

    findings, unresolved = [], []
    skipped_past = 0
    opener = datetime.now(UTC) - timedelta(minutes=2)
    targets = []
    for fixture in fixtures:
        start = stamp(fixture['starts_at'])
        published = methods.get(fixture['id']) or {}
        method = published.get('method')
        needs_research = (not published or method is None or method in MODEL_METHODS)
        if not needs_research:
            continue
        # Hotspawn's scheduled feed also returns long-past fixtures that the
        # source never retired (June 2026 records observed on 23 October 2026).
        # A past start cannot be bet, so it is counted and skipped instead of
        # being offered as a research target or a "lead".
        if start is None or start < opener:
            skipped_past += 1
            continue
        targets.append({'hotspawn_id': fixture['id'],
                        'teams': [{'name': t} for t in fixture['teams']],
                        'starts_at': fixture['starts_at'],
                        'fixture': fixture, 'published': published})

    smarkets_board, smarkets_quotes = smarkets_sweep(session, targets)

    for target in targets:
        fixture, published = target['fixture'], target['published']
        start = stamp(fixture['starts_at'])
        method = published.get('method')
        bound, near = bind(fixture['teams'], start, rows)
        quote = relay_block(bound) if bound else None
        bo3 = ({'slug': bound.get('slug'),
                'url': 'https://bo3.gg/matches/' + str(bound.get('slug')),
                'start': bound.get('start_date'),
                'start_delta_sec': int(abs((stamp(bound.get('start_date')) - start).total_seconds())),
                'tier': bound.get('tier'), 'quote': quote}
               if bound else None)
        smarkets = smarkets_quotes.get(fixture['id'])
        lead = bool(quote and quote.get('two_sided_price'))
        record = {'hotspawn_id': fixture['id'], 'teams': fixture['teams'],
                  'competition': fixture['competition'], 'starts_at': fixture['starts_at'],
                  'tier': fixture['tier'], 'published_method': method,
                  'published_label': published.get('label'),
                  'published_probability': published.get('probability'),
                  'published_source_url': published.get('source_url'),
                  'hotspawn_url': hotspawn_match_url(fixture['teams'], fixture['competition'],
                                                     fixture['id']),
                  'bo3': bo3,
                  'bo3_near_misses': near,
                  'smarkets': smarkets,
                  'lead': lead}
        findings.append(record)
        if not record['lead']:
            unresolved.append(record)
        if args.per_fixture_delay:
            time.sleep(args.per_fixture_delay)

    def compatible(record: dict) -> dict:
        """The published dated-research block's schema, from this probe's record.

        Keys are the ones ``scripts.build.no_line_research_block`` renders; the
        values are copied, never re-derived, and a lead stays a lead. Exchange
        quote evidence rides along under ``smarkets_evidence`` for the linked
        full record; the schema the block needs is unchanged.
        """
        bo3 = record.get('bo3') or {}
        quote = bo3.get('quote') or None
        smarkets = record.get('smarkets')
        if record['lead']:
            verdict = ('A two-sided, active prematch bookmaker quote is published for this fixture; '
                       'it is a lead for the reviewed ladder, not a pick made here.')
        elif smarkets and smarkets.get('two_sided'):
            verdict = ('The Smarkets exchange lists this fixture with a two-sided quote (raw evidence '
                       'attached); the reviewed ladder replays that first-party source itself on the '
                       'next refresh, so this sweep creates no pick here.')
        else:
            verdict = ('No two-sided prematch price found on any probed surface; the research-model '
                       'pick and its limitation stand.')
        return {'id': record['hotspawn_id'], 'teams': record['teams'],
                'competition': record['competition'], 'starts_at': record['starts_at'],
                'current_method': record['published_method'],
                'current_label': record.get('published_label'),
                'hotspawn_url': record.get('hotspawn_url'),
                'bo3_bound_url': bo3.get('url'),
                'bo3_start_delta_sec': bo3.get('start_delta_sec'),
                'bo3_bet_two_sided': bool(quote and quote.get('two_sided_price')),
                'bo3_bet': ({'provider': quote.get('provider'), 'path': quote.get('book_url'),
                             'team_1': (quote.get('sides') or {}).get('team_1'),
                             'team_2': (quote.get('sides') or {}).get('team_2')}
                            if quote else None),
                'smarkets_evidence': ({'event_url': smarkets.get('event_url'),
                                       'event_name': smarkets.get('event_name'),
                                       'quotes_verbatim': smarkets.get('quotes'),
                                       'two_sided': smarkets.get('two_sided')}
                                      if smarkets else None),
                'money_line_lead': record['lead'],
                'near_misses': record['bo3_near_misses'][:3],
                'verdict': verdict}

    document = {
        'session': 'arena-2016c841',
        'schema_version': 1,
        'environment': environment_name(),
        'purpose': ('Dated, source-linked research for Hotspawn CS2 fixtures the published ladder leaves '
                    'as a research model (no external betting line). HLTV is tried first for identity, '
                    'then the Smarkets exchange, bo3.gg (which relays Thunderpick prices) and the '
                    'esportsbook/aggregator surfaces.'),
        'observed_at': observed_at,
        'policy': ('Evidence only. A joined bo3.gg row is a lead, not a pick: this script writes no '
                   'probability, no pick and no alias. Only a two-sided, active, prematch bookmaker quote '
                   'is recorded as a lead, copied verbatim. Smarkets raw 1/10000 quotes are copied '
                   'verbatim and never divided out here. An HTTP 200 on a book landing page is never '
                   'treated as a price.'),
        'hotspawn_source': {'url': HOTSPAWN_API, **hotspawn_attempt},
        'published_methods_source': method_source,
        'bo3_pages': bo3_attempts,
        'smarkets_board': {k: smarkets_board.get(k) for k in ('api', 'events_attempt', 'markets_attempt',
                                                              'contracts_attempt', 'quotes_attempt',
                                                              'events_seen', 'bound', 'errors')},
        'counts': {'hotspawn_fixtures': len(fixtures),
                   'no_external_line': len(findings),
                   'two_sided_lead': sum(1 for f in findings if f['lead']),
                   'smarkets_two_sided': sum(1 for f in findings
                                             if (f.get('smarkets') or {}).get('two_sided')),
                   'still_unresolved': len(unresolved),
                   'skipped_past_start': skipped_past,
                   'bo3_rows_fetched': len(rows)},
        'sources_tried': [{'label': p['label'], 'url': p['url'],
                           'http_status': p.get('http_status'),
                           'note': ('challenge page' if p.get('challenge_page') else
                                    p.get('error') or ('page reachable; no fixture price read'
                                                       if p.get('http_status') == 200 else 'blocked'))}
                          for p in providers],
        'providers': providers,
        'fixtures': findings,
        # Rendered by the executive summary's dated-research block.
        'leads': [compatible(record) for record in findings if record['lead']],
        'per_fixture': [compatible(record) for record in findings],
    }
    (args.out / 'line-source-research.json').write_text(
        json.dumps(document, indent=1, ensure_ascii=False) + '\n')

    lines = [f'# Line-source research — {observed_at}', '',
             f'Source snapshot: `{method_source.get("url")}` '
             f'(generated {method_source.get("generated_at")}); '
             f'{len(fixtures)} Hotspawn fixtures, {len(findings)} with no external line.', '',
             '| Fixture | Start (UTC) | Published method | HLTV | bo3.gg join | bo3 relay price | Smarkets exchange |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    hltv_status = next((p for p in providers if p['label'] == 'HLTV match listing'), {})
    hltv_note = (f"HTTP {hltv_status.get('http_status')}"
                 + (' (Cloudflare)' if hltv_status.get('challenge_page') else '')
                 + ' — platform-side reads in hltv-platform-sweep.md')
    for record in findings:
        bo3 = record['bo3']
        join = (f'[{" vs ".join(record["teams"])}]({bo3["url"]}) · Δ{bo3["start_delta_sec"]}s'
                if bo3 else
                (record['bo3_near_misses'][0]['status'] if record['bo3_near_misses'] else 'not listed'))
        quote = bo3['quote'] if bo3 else None
        price = (f'{quote["provider"]} {quote["sides"]["team_1"]["coeff"]} / '
                 f'{quote["sides"]["team_2"]["coeff"]} ({quote["book_url"]})'
                 if quote and quote['two_sided_price'] else 'none published')
        smarkets = record.get('smarkets')
        if smarkets:
            smarkets_note = (f"[{smarkets['event_name']}]({smarkets['event_url']}) — "
                             + ('two-sided quote saved verbatim (see JSON)' if smarkets['two_sided']
                                else 'bound, no two-sided quote'))
        else:
            smarkets_note = 'not bound (no exact both-name + 60 s event match)'
        lines.append(f'| {" vs ".join(record["teams"])} | {record["starts_at"]} | '
                     f'{record["published_method"] or "unresolved"} | {hltv_note} | {join} | {price} | {smarkets_note} |')
    lines += ['', '## Surface status (HTTP only — a 200 is not a price)', '',
              '| Surface | Status | Note |', '| --- | --- | --- |']
    for provider in providers:
        note = ('challenge page' if provider.get('challenge_page') else
                provider.get('error') or ('ok' if provider.get('http_status') == 200 else 'blocked'))
        lines.append(f'| [{provider["label"]}]({provider["url"]}) | '
                     f'{provider.get("http_status") or "no response"} | {note} |')
    (args.out / 'line-source-research.md').write_text('\n'.join(lines) + '\n')

    # Live-lobby coverage: every current Hotspawn fixture id vs the live
    # published snapshot, one row each, so the executive summary's gap register
    # can quote this sweep instead of one hours older.
    latest_attempt, latest_body = fetch_json(session, LIVE_LATEST)
    published_ids = set()
    if latest_attempt.get('http_status') == 200:
        published_ids = {str(m.get('id')) for m in latest_body.get('matches') or []
                         if m.get('id') is not None}
    live_rows = []
    for fixture in fixtures:
        start = stamp(fixture['starts_at'])
        if start is None or start < opener:
            continue
        published = methods.get(fixture['id']) or {}
        probability = published.get('probability')
        pick = None
        if isinstance(probability, (int, float)) and fixture['teams'][0]:
            winner = fixture['teams'][0] if probability >= 0.5 else (fixture['teams'][1] or fixture['teams'][0])
            share = probability if probability >= 0.5 else 1 - probability
            pick = f'{winner} {share * 100:.1f}% (published {published.get("label") or published.get("method")})'
        live_rows.append({'id': fixture['id'], 'teams': fixture['teams'],
                          'competition': fixture['competition'], 'starts_at': fixture['starts_at'],
                          'hotspawn_url': hotspawn_match_url(fixture['teams'], fixture['competition'],
                                                             fixture['id']),
                          'in_published_snapshot': fixture['id'] in published_ids,
                          'published_method': published.get('label') or published.get('method'),
                          'published_pick': pick,
                          'note': ('In the published snapshot.' if fixture['id'] in published_ids else
                                   'Not in the published snapshot at this observation; the next scheduled '
                                   'collect+publish is the authority. No probability is invented.')})
    coverage = {
        'schema_version': 1,
        'session': 'arena-2016c841',
        'observed_at': observed_at,
        'observer': environment_name(),
        'role': 'Dated inventory and identity research only. No value here is a probability or a pick.',
        'published_site': {'latest_json': LIVE_LATEST,
                           'generated_at': latest_body.get('generated_at')
                           if isinstance(latest_body, dict) else None,
                           'attempt': latest_attempt},
        'hotspawn': {'lobby_url': HOTSPAWN_LOBBY, 'api_url': HOTSPAWN_API,
                     'api_http_status': hotspawn_attempt.get('http_status'),
                     'fixtures_returned': len(fixtures),
                     'future_fixtures_compared': len(live_rows),
                     'note': ('The API still returns long-past rows marked scheduled; past-start rows are '
                              'counted as retired history and left out of the comparison. Lobby crowd '
                              'percentages are never a win probability.')},
        'counts': {'live_future_fixtures': len(live_rows),
                   'in_published_snapshot': sum(1 for r in live_rows if r['in_published_snapshot']),
                   'missing_from_published': sum(1 for r in live_rows if not r['in_published_snapshot'])},
        'limitations': ['HLTV match pages are identity/form evidence; they are not a two-sided prematch '
                        'odds feed.',
                        'Hotspawn crowd participation figures are never used as a win probability.',
                        'A missing snapshot row is a coverage gap to be closed by the next scheduled '
                        'collect, not proof that no market exists.'],
        'live_fixtures': live_rows,
    }
    (args.out / 'live-coverage.json').write_text(
        json.dumps(coverage, indent=1, ensure_ascii=False) + '\n')
    coverage_lines = [f'# Live Hotspawn lobby vs published snapshot — {observed_at}', '',
                      f'Published `latest.json` generated `{coverage["published_site"]["generated_at"]}`; '
                      f'{len(live_rows)} future fixtures compared, '
                      f'{coverage["counts"]["missing_from_published"]} missing from the published snapshot.',
                      '',
                      '| Fixture | Start (UTC) | In published snapshot | Published pick |',
                      '| --- | --- | --- | --- |']
    for row in live_rows:
        coverage_lines.append(f'| [{" vs ".join(row["teams"])}]({row["hotspawn_url"]}) | '
                              f'{row["starts_at"]} | {"yes" if row["in_published_snapshot"] else "NO"} | '
                              f'{row["published_pick"] or "—"} |')
    (args.out / 'live-coverage.md').write_text('\n'.join(coverage_lines) + '\n')

    summary = document['counts']
    print(f'::notice title=2016c841 line research::{json.dumps(summary)}')
    print(f'::notice title=2016c841 coverage::{json.dumps(coverage["counts"])}')
    for record in findings:
        if record['lead']:
            print('::notice::two-sided lead ' + json.dumps(
                {'teams': record['teams'], 'start': record['starts_at'],
                 'bo3': record['bo3']['url'], 'quote': record['bo3']['quote']}))
        smarkets = record.get('smarkets')
        if smarkets and smarkets.get('two_sided'):
            print('::notice::smarkets two-sided quote evidence ' + json.dumps(
                {'teams': record['teams'], 'event_url': smarkets['event_url']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
