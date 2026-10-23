"""Session arena-1531ecf1 — researched picks for every Hotspawn CS2 fixture the
featured (exact-name Polymarket) method cannot resolve.

The brief: "We need to be able to generate picks for every match... Look for
information sources to guide pick selections only for any matches that cannot be
resolved in the same way as the featured picks. Do your own research to find a
way to resolve a pick for any matches that we don't have a pick for. Try hltv,
then try looking at esportsbooks and esports betting lines."

This module is a read-only research probe. It writes ONLY dated records under
``data/research/1531ecf1/``. It never writes ``data/latest.json``,
``data/origination.json`` or the alias registry, and it never converts Hotspawn
crowd percentages or HLTV "Pick a winner" fan votes into a probability.

Targets (only fixtures the featured method cannot resolve):
  * lobby gaps — live Hotspawn fixtures that the published snapshot does not
    contain at all (so no pick exists for them anywhere on the site);
  * no-line fixtures — published rows whose origination is a research model
    (or blank) rather than an external money line;
  * covered rows — live fixtures already present in the published snapshot
    (recorded as covered, never re-priced).

Research order for every target, per the brief: HLTV first (identity, format,
started/finished state; HLTV publishes no two-sided price and its fan votes are
never inputs), then esportsbooks and esports betting-line services (bo3.gg's
bookmaker relay, Smarkets, Thunderpick, the Pinnacle guest board), then a
book-surface reachability sweep.

Pick resolution mirrors the reviewed ladder in ``scripts/originate.py`` exactly
(reuses its functions). A pick is produced only from:
  1. a bound two-sided prematch price pair (relay or first-party bookmaker),
     margin removed by ``domain.no_vig`` under the published acceptance policy;
  2. the documented Valve-rating research model when no money source resolves
     the fixture and both sides have a unique exact-name Valve record.
Otherwise the fixture is recorded as unresolved with the limitation that
blocked it. An even estimate never receives an invented side.

Usage:
    python -m scripts.1531ecf1_gap_research --live     # GitHub runner / host with egress
    python -m scripts.1531ecf1_gap_research --replay   # re-render from saved evidence (offline)

Outputs (``data/research/1531ecf1/``):
    gap-picks.json / gap-picks.md                 — per-fixture researched picks + limitations
    line-source-research.json / .md               — dated per-fixture sweep (schema-compatible
                                                    with build.load_no_line_research)
    evidence/…                                    — verbatim API/page captures
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'data' / 'research' / '1531ecf1'
EVIDENCE = OUT_DIR / 'evidence'
SESSION = 'arena-1531ecf1'
UTC = timezone.utc

HOTSPAWN_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
HOTSPAWN_LOBBY = 'https://play.hotspawn.com/lobby'
HLTV_MATCHES = 'https://www.hltv.org/matches'
BO3_API = 'https://api.bo3.gg/api/v1'
BO3_SITE = 'https://bo3.gg'
SMARKETS_API = 'https://api.smarkets.com/v3'
SMARKETS_SITE = 'https://smarkets.com/sport/esports/cs-go'
SMARKETS_DOCS = 'https://docs.smarkets.com/'
THUNDERPICK_API = 'https://thunderpick.io/api/matches'
THUNDERPICK_SITE = 'https://thunderpick.io/esports/counter-strike'
PINNACLE_BASE = 'https://guest.api.arcadia.pinnacle.com/0.1'
PINNACLE_SITE = 'https://www.pinnacle.com/en/esports/counter-strike-2'
VALVE_STANDINGS = ('https://github.com/ValveSoftware/counter-strike_regional_standings'
                   '/blob/main/live/2026/')

BO3_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/124.0 Safari/537.36'),
    'Accept': 'application/json',
    'Origin': BO3_SITE,
    'Referer': BO3_SITE + '/',
}

#: Book surfaces probed for reachability + whether both team names appear.
#: A reachable page is never a price; only a readable two-sided pair prices a
#: fixture. These surfaces are recorded so a reader can review the limitation.
BOOK_SURFACES = [
    ('GG.BET esportsbook', 'https://gg.bet/esports/counter-strike'),
    ('Rivalry esportsbook', 'https://rivalry.com/esports/counter-strike-2'),
    ('Betano esportsbook', 'https://betano.com/esports/'),
    ('Betsson esportsbook', 'https://betsson.com/en/esports/'),
    ('Unibet esportsbook', 'https://unibet.com/esports/'),
    ('22bet esportsbook', 'https://22bet.com/esports/'),
    ('Betway esportsbook', 'https://betway.com/esports/counter-strike'),
    ('Bet365 esportsbook', 'https://bet365.com/esports/'),
    ('Oddspedia aggregator', 'https://oddspedia.com/esports/counter-strike'),
    ('OddsPortal aggregator', 'https://oddsportal.com/esports/counter-strike/'),
    ('EGamersWorld aggregator', 'https://egamersworld.com/counter-strike'),
    ('Marathonbet esportsbook', 'https://marathonbet.com/esports/'),
    ('BetBoom esportsbook', 'https://betboom.com/esports/'),
    ('1xBet esportsbook', 'https://1xbet.com/esports/'),
    ('Stake esportsbook', 'https://stake.com/esports/counter-strike'),
    ('DraftKings esportsbook', 'https://sportsbook.draftkings.com/esports'),
]

UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')


def now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def slug(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (value or '')).strip('-').lower() or 'page'


def save(label: str, data) -> str:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / f'{slug(label)}.json'
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False)[:2_000_000])
    return f'data/research/{SESSION}/evidence/{path.name}'


def fetch(url: str, label: str, headers: dict | None = None, timeout: int = 40):
    """GET ``url``; return (status, parsed-json-or-text, evidence_path, error)."""
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8', 'replace')
            status = resp.status
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode('utf-8', 'replace')[:2000]
        except Exception:  # noqa: BLE001
            raw = ''
        evidence = save(label, {'url': url, 'status': exc.code, 'body_head': raw[:400]})
        return exc.code, None, evidence, f'HTTP {exc.code}'
    except Exception as exc:  # noqa: BLE001 - recorded, never fatal
        evidence = save(label, {'url': url, 'status': None, 'error': f'{type(exc).__name__}: {exc}'[:200]})
        return None, None, evidence, f'{type(exc).__name__}: {exc}'[:160]
    try:
        parsed = json.loads(raw)
        evidence = save(label, parsed)
        return status, parsed, evidence, None
    except ValueError:
        evidence = save(label, {'url': url, 'status': status, 'body_head': raw[:400]})
        return status, raw, evidence, None


# ---------------------------------------------------------------- inventory

def hotspawn_inventory(observed_at: str) -> dict:
    """The live Hotspawn CS2 scheduled fixtures (the lobby's own source feed)."""
    status, body, evidence, error = fetch(HOTSPAWN_API, 'hotspawn-fixtures')
    rows = body if isinstance(body, list) else []
    fixtures = []
    for row in rows:
        if not isinstance(row, dict) or str(row.get('sport_alias')) != 'cs2':
            continue
        start = int(row.get('scheduled_start_time') or 0) / 1000
        starts = datetime.fromtimestamp(start, UTC).isoformat(timespec='seconds').replace('+00:00', 'Z') if start else None
        fixtures.append({
            'id': str(row.get('id')) if row.get('id') is not None else None,
            'teams': [row.get('participants0_name') or '', row.get('participants1_name') or ''],
            'competition': row.get('competition_name') or '',
            'starts_at': starts,
            'lock_at': (datetime.fromtimestamp(int(row.get('lock_time') or 0) / 1000, UTC)
                        .isoformat(timespec='seconds').replace('+00:00', 'Z')) if row.get('lock_time') else None,
            'tier': row.get('tier'),
            'started': row.get('start_time') is not None,
            'finished': row.get('end_time') is not None,
            'score': [row.get('participants0_score'), row.get('participants1_score')],
            'hotspawn_url': (f'https://www.hotspawn.com/matches/'
                             f'{slug(row.get("participants0_name"))}-vs-{slug(row.get("participants1_name"))}'
                             f'-{row.get("id")}'),
            'source_api': HOTSPAWN_API,
        })
    return {'status': status, 'error': error, 'evidence': evidence,
            'observed_at': observed_at, 'fixtures': fixtures}


def published_state() -> dict:
    """What the checked-out (published) snapshot already covers."""
    latest = json.loads((ROOT / 'data' / 'latest.json').read_text())
    orig = json.loads((ROOT / 'data' / 'origination.json').read_text()) if (ROOT / 'data' / 'origination.json').exists() else {}
    ids, pairs, rows = set(), set(), {}
    for m in latest.get('matches') or []:
        ident = str(m.get('id'))
        ids.add(ident)
        names = [t.get('name') or '' for t in m.get('teams') or []]
        if len(names) == 2:
            pairs.add(pair_key(names))
        rows[ident] = m
    orig_rows = {str(m.get('id')): m for m in orig.get('matches') or []}
    return {
        'latest_generated_at': latest.get('generated_at'),
        'origination_generated_at': orig.get('generated_at'),
        'ids': ids, 'pairs': pairs, 'rows': rows, 'origination_rows': orig_rows,
        'counts': latest.get('counts') or {},
    }


def pair_key(names) -> tuple:
    from scripts.domain import name_key
    return tuple(sorted(name_key(n) for n in names if n))


# ---------------------------------------------------------------- line probes

def probe_bo3(observed_at: str) -> dict:
    """bo3.gg match objects (upcoming + finished) with relayed bookmaker quotes."""
    rows = []
    status_log = []
    for state in ('upcoming', 'finished'):
        pages = 0
        while pages < 4:
            query = (f'/matches?page[offset]={pages * 100}&page[limit]=100&sort=start_date'
                     f'&filter[matches.status][in]={state}&filter[matches.discipline_id][eq]=1'
                     '&with=teams,tournament')
            status, body, evidence, error = fetch(BO3_API + query, f'bo3-{state}-{pages}',
                                                  headers=BO3_HEADERS)
            status_log.append({'surface': f'bo3.gg API {state}', 'url': BO3_API + query,
                               'http_status': status, 'error': error})
            chunk = (body or {}).get('results') if isinstance(body, dict) else None
            if not chunk:
                break
            rows.extend(chunk)
            pages += 1
            if len(chunk) < 100:
                break
    return {'observed_at': observed_at, 'status_log': status_log, 'rows': rows}


def bo3_binding(fixture: dict, bo3: dict, registry: dict) -> dict:
    """Bind one fixture onto bo3.gg rows; capture relay quotes and state."""
    from scripts.domain import timestamp
    from scripts.originate import relay_join
    match = {
        'id': fixture.get('id'), 'teams': [{'name': n} for n in fixture['teams']],
        'competition': fixture.get('competition'), 'starts_at': fixture.get('starts_at'),
        'availability': 'open',
    }
    out = {'bound_url': None, 'bet': None, 'bet_two_sided': False, 'score': None,
           'state': None, 'rejections': []}
    for row in bo3.get('rows') or []:
        names = [(row.get('team1') or {}).get('name'), (row.get('team2') or {}).get('name')]
        _, _, status = relay_join(names, row.get('start_date'), match, registry)
        if status != 'matched':
            continue
        out['bound_url'] = f"https://bo3.gg/matches/{row.get('slug')}" if row.get('slug') else BO3_SITE + '/matches'
        out['state'] = row.get('status')
        t1, t2 = (row.get('team1') or {}).get('score'), (row.get('team2') or {}).get('score')
        if t1 is not None and t2 is not None:
            out['score'] = [t1, t2]
        updates = row.get('bet_updates') or []
        for update in updates:
            prices = update.get('coefficient_values') or update.get('coefficients') or []
            active = update.get('active')
            provider = str(update.get('bookmaker') or update.get('provider') or 'bookmaker').strip()
            if len(prices) == 2 and all(p is not None for p in prices):
                both_active = (active if isinstance(active, list) else [active, active])
                out['bet'] = {
                    'provider': provider,
                    'team_1': {'name': names[0], 'coeff': prices[0]},
                    'team_2': {'name': names[1], 'coeff': prices[1]},
                    'active': both_active,
                    'path': update.get('path') or update.get('url'),
                    'observed_at': iso(now()),
                }
                out['bet_two_sided'] = all(bool(a) for a in both_active) and \
                    all(isinstance(p, (int, float)) and float(p) > 1 for p in prices)
        break
    return out


def probe_smarkets_page() -> dict:
    """Smarkets exchange CS:GO match events (verified endpoints from
    scripts/smarkets_lines.py: type=csgo_match, states=upcoming, 60s bind)."""
    from scripts.smarkets_lines import events_url
    status, body, evidence, error = fetch(events_url(), 'smarkets-events-page',
                                          headers={'Accept': 'application/json'})
    events = (body or {}).get('events') if isinstance(body, dict) else None
    return {'http_status': status, 'error': error, 'evidence': evidence,
            'events': events or [], 'url': SMARKETS_SITE, 'docs': SMARKETS_DOCS}


def smarkets_binding(fixture: dict, page: dict) -> dict:
    from scripts.smarkets_lines import binds, event_url
    result = {'http_status': page.get('http_status'), 'error': page.get('error'),
              'evidence': page.get('evidence'), 'bound': False, 'quote': None,
              'url': page.get('url') or SMARKETS_SITE, 'docs': SMARKETS_DOCS}
    match = {'teams': [{'name': n} for n in fixture['teams']],
             'starts_at': fixture.get('starts_at')}
    for ev in page.get('events') or []:
        if binds(ev, match):
            result['bound'] = True
            result['url'] = event_url(ev)
            result['event_name'] = ev.get('name')
            break
    return result


def probe_thunderpick_page(observed_at: str) -> dict:
    """Thunderpick's public match list, parsed by the reviewed
    ``originate.thunderpick_rows`` contract (match-winner market, both sides
    active, gameId 6, not live)."""
    status, body, evidence, error = fetch(THUNDERPICK_API, 'thunderpick-matches-live')
    result = {'http_status': status, 'error': error, 'evidence': evidence,
              'rows': [], 'url': THUNDERPICK_SITE}
    try:
        from scripts.originate import thunderpick_rows
        live = {'thunderpick': body if isinstance(body, dict) else {'ok': False},
                'requests': [{'id': 'live-thunderpick-matches', 'status': 'ok',
                              'observed_at': observed_at}]}
        result['rows'] = thunderpick_rows(ROOT / 'data', live)
    except Exception as exc:  # noqa: BLE001 - recorded, never fatal
        result['error'] = f'{type(exc).__name__}: {exc}'[:160]
    return result


def thunderpick_binding(fixture: dict, page: dict, observed_at: str) -> dict:
    from scripts.domain import timestamp as ts
    result = {'http_status': page.get('http_status'), 'error': page.get('error'),
              'evidence': page.get('evidence'), 'bound': False, 'quote': None,
              'url': page.get('url') or THUNDERPICK_SITE}
    wanted = pair_key(fixture['teams'])
    for row in page.get('rows') or []:
        if pair_key(row.get('names') or []) != wanted:
            continue
        start, row_start = ts(fixture.get('starts_at')), ts(row.get('start'))
        if start and row_start and abs((row_start - start).total_seconds()) > 300:
            continue
        result['bound'] = True
        result['quote'] = {'names': row['names'], 'odds': row['odds'],
                           'observed_at': row.get('observed_at') or observed_at,
                           'evidence': row.get('evidence_file') or result['evidence']}
        break
    return result


def probe_pinnacle(fixture: dict, observed_at: str) -> dict:
    """Pinnacle guest board matchups; series moneyline when bound."""
    result = {'http_status': None, 'bound': False, 'matchup': None, 'url': PINNACLE_SITE,
              'error': None}
    try:
        from scripts.pinnacle_lines import quote as pinnacle_quote
    except Exception as exc:  # noqa: BLE001
        result['error'] = f'pinnacle_lines unavailable: {exc}'[:120]
        return result
    try:
        found = pinnacle_quote(fixture['teams'][0], fixture['teams'][1],
                               fixture.get('starts_at'), now=now())
    except Exception as exc:  # noqa: BLE001
        result['error'] = f'{type(exc).__name__}: {exc}'[:120]
        return result
    result['http_status'] = 200 if found else 200
    if found:
        result['bound'] = True
        result['matchup'] = found
    return result


def probe_hltv_matches_page() -> dict:
    """HLTV first: one fetch of hltv.org/matches for identity/state evidence."""
    status, body, evidence, error = fetch(HLTV_MATCHES, 'hltv-matches-page')
    text = body if isinstance(body, str) else json.dumps(body or {})
    return {'status': status, 'error': error, 'evidence': evidence, 'text': text}


def probe_hltv(fixture: dict, matches_page: dict) -> dict:
    """HLTV first for one fixture. Identity and state only — HLTV publishes no
    two-sided price, and its 'Pick a winner' fan votes are never a probability
    input."""
    text = matches_page.get('text') or ''
    listed = all(name.lower() in text.lower() for name in fixture['teams'] if name)
    out = {'matches_page_status': matches_page.get('status'),
           'match_url': fixture.get('hltv_url'), 'match_status': None, 'state': None,
           'evidence': matches_page.get('evidence'),
           'detail': ('both teams listed on hltv.org/matches' if listed
                      else 'teams not seen on the fetched HLTV matches page')}
    if fixture.get('hltv_url'):
        st2, body2, ev2, err2 = fetch(fixture['hltv_url'],
                                      f'hltv-match-{fixture.get("id") or slug(fixture["teams"][0])}')
        out['match_status'] = st2
        text2 = body2 if isinstance(body2, str) else ''
        if st2 == 200 and text2:
            if re.search(r'\bFinished\b', text2):
                out['state'] = 'finished'
            elif re.search(r'\bLive\b', text2):
                out['state'] = 'started'
            out['match_evidence'] = ev2
    return out


def probe_book_surfaces() -> dict:
    """One reachability sweep of esportsbooks and betting-line aggregators.

    A reachable page is never a price; only a readable two-sided pair prices a
    fixture. Fetched once per run and re-used for every target fixture."""
    pages = {}
    for name, url in BOOK_SURFACES:
        status, body, evidence, error = fetch(url, f'book-{slug(name)}')
        text = body if isinstance(body, str) else json.dumps(body or {})
        pages[name] = {'name': name, 'url': url, 'http_status': status, 'error': error,
                       'evidence': evidence, 'text': text}
    return pages


def book_rows_for(fixture: dict, pages: dict) -> list:
    rows = []
    for name, page in pages.items():
        text = page.get('text') or ''
        listed = all(str(n).lower() in text.lower() for n in fixture['teams'] if n)
        rows.append({'name': name, 'url': page['url'], 'http_status': page['http_status'],
                     'error': page.get('error'), 'teams_listed': listed,
                     'evidence': page.get('evidence')})
    return rows


# ---------------------------------------------------------------- resolution

def resolve(fixture: dict, bound: dict, ratings, valve_meta, registry: dict,
            observed_at: str) -> dict:
    """The reviewed ladder, replayed for one fixture the featured method missed."""
    from scripts.domain import name_key
    from scripts.originate import (bookmaker_estimate, model_estimate,
                                   relayed_bookmaker_estimate, selection)
    match = {
        'id': fixture.get('id') or f'gap-{slug(fixture["teams"][0])}-{slug(fixture["teams"][1])}',
        'teams': [{'name': fixture['teams'][0]}, {'name': fixture['teams'][1]}],
        'competition': fixture.get('competition'), 'starts_at': fixture.get('starts_at'),
        'availability': 'open',
    }
    attempts = []

    def attempt(stage, fn):
        quote, detail = fn()
        attempts.append({'stage': stage, 'status': 'resolved' if quote else 'unresolved',
                         'detail': detail})
        return quote

    if bound.get('bo3', {}).get('bet'):
        bet = bound['bo3']['bet']
        row = {
            'provider': bet['provider'], 'names': [bet['team_1']['name'], bet['team_2']['name']],
            'odds': [float(bet['team_1']['coeff']), float(bet['team_2']['coeff'])],
            'active': bet.get('active') or [True, True],
            'observed_at': bet.get('observed_at') or observed_at, 'start': fixture.get('starts_at'),
            'source_url': bound['bo3'].get('bound_url') or BO3_SITE + '/matches',
            'book_url': bet.get('path'), 'event_id': None, 'evidence_file': 'evidence/bo3-upcoming-0.json',
            'start_delta_sec': 0,
        }
        quote = attempt('Relayed esportsbook line (bo3.gg)',
                        lambda: relayed_bookmaker_estimate(row, match, registry, now=now()))
        if quote:
            return finish(quote, attempts, 'relayed bookmaker', fixture['teams'])

    tp = bound.get('thunderpick') or {}
    if tp.get('quote'):
        row = {
            'provider': 'Thunderpick', 'names': tp['quote']['names'], 'odds': tp['quote']['odds'],
            'observed_at': tp['quote'].get('observed_at') or observed_at,
            'start': fixture.get('starts_at'), 'source_url': THUNDERPICK_API,
            'api_url': THUNDERPICK_API, 'event_id': None,
            'evidence_file': tp.get('evidence'), 'start_delta_sec': 0,
        }
        quote = attempt('Esportsbook line (Thunderpick)',
                        lambda: bookmaker_estimate(row, match, registry, now=now()))
        if quote:
            return finish(quote, attempts, 'bookmaker', fixture['teams'])

    pn = bound.get('pinnacle') or {}
    if pn.get('matchup') and isinstance(pn['matchup'], dict):
        m = pn['matchup']
        odds = m.get('odds') or m.get('prices')
        names = m.get('names') or fixture['teams']
        if isinstance(odds, list) and len(odds) == 2:
            row = {
                'provider': 'Pinnacle', 'names': list(names), 'odds': [float(o) for o in odds],
                'observed_at': observed_at, 'start': fixture.get('starts_at'),
                'source_url': PINNACLE_SITE, 'api_url': PINNACLE_BASE, 'event_id': None,
                'evidence_file': 'evidence/pinnacle-guest.json', 'start_delta_sec': 0,
            }
            quote = attempt('Esportsbook line (Pinnacle guest board)',
                            lambda: bookmaker_estimate(row, match, registry, now=now()))
            if quote:
                return finish(quote, attempts, 'bookmaker', fixture['teams'])

    quote = attempt('Valve-rating research model',
                    lambda: model_estimate(match, ratings or [], registry,
                                           valve_meta or {'source_url': VALVE_STANDINGS,
                                                          'snapshot_date': '2026-10-05',
                                                          'evidence_file': 'valve-standings'},
                                           now()))
    if quote:
        return finish(quote, attempts, 'model', fixture['teams'])

    return {'method': None, 'label': None, 'probabilities': None, 'pick_index': None,
            'pick_team': None, 'source': None, 'source_url': None, 'odds': None,
            'attempts': attempts}


def finish(quote: dict, attempts: list, kind: str, names: list) -> dict:
    from scripts.originate import selection
    probs = quote['probabilities']
    pick = selection(probs)
    families = {'relayed bookmaker': 'Relayed esportsbook line (bo3.gg relay)',
                'bookmaker': 'No-vig esportsbook estimate', 'model': 'Valve-rating research estimate'}
    return {
        'method': kind,
        'label': families[kind],
        'family': quote.get('family'),
        'probabilities': probs,
        'pick_index': pick,
        'pick_team': names[pick] if pick in (0, 1) and len(names) == 2 else None,
        'source': quote.get('provider'),
        'source_url': quote.get('source_url'),
        'book_url': quote.get('book_url'),
        'odds': quote.get('odds'),
        'observed_at': quote.get('observed_at'),
        'attempts': attempts,
    }


# ---------------------------------------------------------------- records

def build_record(inventory: dict, published: dict, bound: dict, ratings, valve_meta,
                 registry: dict, observed_at: str, environment: str) -> tuple[dict, dict]:
    """Compose gap-picks.json + line-source-research.json (shared per-fixture facts)."""
    from scripts.domain import timestamp as ts
    now_dt = now()
    lobby_rows, no_line_rows = [], []
    prior = {}
    prior_path = ROOT / 'data' / 'research' / '9fd5fbf1' / 'live-coverage.json'
    if prior_path.exists():
        try:
            for f in json.loads(prior_path.read_text()).get('live_fixtures') or []:
                if f.get('id'):
                    prior[str(f['id'])] = f
        except ValueError:
            pass

    def classify(fixture: dict) -> str:
        ident = fixture.get('id')
        if ident and ident in published['ids']:
            return 'covered'
        if pair_key(fixture['teams']) in published['pairs'] and all(fixture['teams']):
            return 'covered'
        if fixture.get('finished'):
            return 'finished'
        start = ts(fixture.get('starts_at'))
        if fixture.get('started') or (start and start < now_dt):
            return 'started'
        return 'open'

    def base_row(fixture: dict, status: str) -> dict:
        ident = fixture.get('id')
        covered_as = None
        if status == 'covered' and ident not in published['ids']:
            for pid, prow in published['rows'].items():
                names = [t.get('name') or '' for t in prow.get('teams') or []]
                if names and pair_key(names) == pair_key(fixture['teams']):
                    covered_as = pid
                    break
        row = {
            'id': ident,
            'teams': fixture['teams'],
            'competition': fixture.get('competition'),
            'starts_at': fixture.get('starts_at'),
            'hotspawn_url': fixture.get('hotspawn_url'),
            'status': status,
            'covered_as': covered_as,
            'research': [],
            'pick': None,
            'limitation': None,
        }
        return row

    for fixture in inventory['fixtures']:
        status = classify(fixture)
        if status == 'covered':
            continue  # already priced by the featured/complete ladder
        row = base_row(fixture, status)
        facts = bound.get(fixture.get('id') or pair_key(fixture['teams'])) or {}
        hltv = facts.get('hltv') or {}
        if hltv.get('match_url') or hltv.get('matches_page_status') is not None:
            row['hltv_url'] = hltv.get('match_url')
            row['research'].append({
                'stage': 'HLTV first (identity & state)', 'source_url': hltv.get('match_url') or HLTV_MATCHES,
                'status': 'checked' if hltv.get('matches_page_status') == 200 or hltv.get('match_status') == 200 else 'unavailable',
                'detail': (hltv.get('detail') or '') + (
                    f" · match page HTTP {hltv.get('match_status')}" if hltv.get('match_status') else ''),
            })
        if status in {'started', 'finished'} or hltv.get('state') in {'started', 'finished'}:
            if hltv.get('state') in {'started', 'finished'}:
                row['status'] = hltv['state']
            prior_pick = prior.get(str(fixture.get('id')) or '')
            if prior_pick and prior_pick.get('published_pick'):
                row['prior_published_pick'] = (
                    f"{prior_pick['published_pick']} ({prior_pick.get('published_method') or 'method unverified'}; "
                    f"published in the 2026-10-23T04:58Z research record)")
            row['limitation'] = ('The pick window has closed: this fixture is already running or finished, so no '
                                 'prematch pick can be generated now. Where an earlier snapshot published a '
                                 'prematch pick it is cited above with its method. Nothing is manufactured after lock.')
            lobby_rows.append(row)
            continue

        try:
            resolved = resolve(fixture, facts, ratings, valve_meta, registry, observed_at)
        except Exception as exc:  # noqa: BLE001 - fail closed to "unresolved"
            resolved = {'method': None, 'attempts': [
                {'stage': 'Resolution', 'status': 'unresolved',
                 'detail': f'{type(exc).__name__}: {exc}'[:180]}]}
        row['research'].extend(resolved.get('attempts') or [])
        if resolved.get('method'):
            row['pick'] = {k: resolved[k] for k in (
                'method', 'label', 'family', 'probabilities', 'pick_index', 'pick_team',
                'source', 'source_url', 'book_url', 'odds', 'observed_at')}
            row['limitation'] = (
                'Researched pick for a fixture missing from the published snapshot. '
                + ('Relayed esportsbook price: the number was read from the bo3.gg relay of a named bookmaker, '
                   'not from the bookmaker page itself; margins removed by proportional normalization.'
                   if resolved['method'] == 'relayed bookmaker' else
                   'Esportsbook price; margins removed by proportional normalization.'
                   if resolved['method'] == 'bookmaker' else
                   'Uncalibrated Valve-rating research model, not a price you could have bet. '
                   'No two-sided prematch price was reachable on any probed surface.'))
        else:
            row['limitation'] = ('No two-sided prematch price on any probed surface and no unique Valve-rating '
                                 'record, so no pick is generated. The sources tried are listed above; a blocked '
                                 'page is not evidence that no market exists.')
        lobby_rows.append(row)

    for ident, orig in published['origination_rows'].items():
        method = ((orig.get('origination') or {}).get('method'))
        if method in {'market', 'bookmaker', 'consensus', 'reference', 'guidance'}:
            continue
        match = published['rows'].get(ident)
        if not match or match.get('availability') == 'past':
            continue
        fixture = {
            'id': ident,
            'teams': [t.get('name') or '' for t in match.get('teams') or []],
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'hotspawn_url': (match.get('source_url') if str(match.get('source_url', '')).startswith('https://www.hotspawn.com')
                             else None) or f'https://play.hotspawn.com/cs2-pickems#fixture-{ident}',
        }
        row = base_row(fixture, 'open')
        facts = bound.get(ident) or bound.get(pair_key(fixture['teams'])) or {}
        try:
            resolved = resolve(fixture, facts, ratings, valve_meta, registry, observed_at)
        except Exception as exc:  # noqa: BLE001 - fail closed to "unresolved"
            resolved = {'method': None, 'attempts': [
                {'stage': 'Resolution', 'status': 'unresolved',
                 'detail': f'{type(exc).__name__}: {exc}'[:180]}]}
        row['research'] = list(resolved.get('attempts') or [])
        current = orig.get('origination') or {}
        current_probs = current.get('probabilities')
        if resolved.get('method') in {'relayed bookmaker', 'bookmaker'}:
            row['pick'] = {k: resolved[k] for k in (
                'method', 'label', 'family', 'probabilities', 'pick_index', 'pick_team',
                'source', 'source_url', 'book_url', 'odds', 'observed_at')}
            row['limitation'] = ('A dated money line was found for a fixture the last refresh left on a research '
                                 'model. The reviewed ladder replays it on the next four-hour refresh before any '
                                 'published pick changes; this row documents the lead, it does not re-price the site.')
        else:
            row['pick'] = None
            if current_probs:
                row['current_estimate'] = {
                    'label': current.get('label'), 'probabilities': current_probs,
                    'source': current.get('source'), 'source_url': current.get('source_url')}
            row['limitation'] = ('No two-sided prematch price on any probed surface; the published research '
                                 'estimate and its limitation stand until the next refresh.')
        no_line_rows.append(row)

    gap_picks = {
        'schema_version': 1,
        'session': SESSION,
        'observed_at': observed_at,
        'environment': environment,
        'role': ('Dated research and gap picks. Only a bound two-sided prematch price or the documented '
                 'Valve-rating research model may produce the probabilities recorded here. Hotspawn crowd '
                 'percentages and HLTV fan votes are never inputs.'),
        'policy': ('HLTV first (identity, format, started/finished state only), then esportsbooks and '
                   'esports betting-line services (bo3.gg bookmaker relay, Smarkets, Thunderpick, Pinnacle '
                   'guest board, book-surface sweep). Resolution reuses scripts/originate.py’s reviewed '
                   'ladder. An even estimate never receives an invented side.'),
        'inventory': {
            'source_api': HOTSPAWN_API, 'lobby_url': HOTSPAWN_LOBBY,
            'observed_at': inventory.get('observed_at'),
            'http_status': inventory.get('status'), 'fixtures_seen': len(inventory.get('fixtures') or []),
        },
        'published': {
            'latest_generated_at': published.get('latest_generated_at'),
            'origination_generated_at': published.get('origination_generated_at'),
            'upcoming_ids': sorted(published['ids']),
        },
        'lobby_fixtures': lobby_rows,
        'no_line_fixtures': no_line_rows,
        'counts': {
            'lobby_missing': len([r for r in lobby_rows if r['status'] == 'open']),
            'lobby_closed': len([r for r in lobby_rows if r['status'] in {'started', 'finished'}]),
            'lobby_resolved_picks': len([r for r in lobby_rows if r.get('pick')]),
            'lobby_unresolved': len([r for r in lobby_rows if r['status'] == 'open' and not r.get('pick')]),
            'no_line_targets': len(no_line_rows),
            'no_line_money_leads': len([r for r in no_line_rows if r.get('pick')]),
        },
    }

    per_fixture = []
    for row in lobby_rows + no_line_rows:
        bet = (row.get('pick') or {}).get('odds')
        names = row['teams']
        lead = bool((row.get('pick') or {}).get('method') in {'relayed bookmaker', 'bookmaker'})
        per_fixture.append({
            'id': row.get('id'),
            'teams': names,
            'competition': row.get('competition'),
            'starts_at': row.get('starts_at'),
            'current_method': (row.get('current_estimate') or {}).get('label') or (
                'missing from the published snapshot' if row in lobby_rows else 'model'),
            'hotspawn_url': row.get('hotspawn_url'),
            'bo3_bound_url': (row.get('pick') or {}).get('source_url') if lead else None,
            'bo3_bet_two_sided': bool((row.get('pick') or {}).get('method') == 'relayed bookmaker'),
            'bo3_bet': ({'provider': (row.get('pick') or {}).get('source'),
                         'team_1': {'name': names[0], 'coeff': bet[0] if bet else None},
                         'team_2': {'name': names[1], 'coeff': bet[1] if bet else None},
                         'path': (row.get('pick') or {}).get('book_url')}
                        if lead and bet else None),
            'pinnacle_matchup': None,
            'extra_pages_listing_a_team': [],
            'money_line_lead': lead,
            'verdict': row.get('limitation'),
            'pick': row.get('pick'),
            'status': row.get('status'),
        })
    line_research = {
        'schema_version': 1,
        'session': SESSION,
        'observed_at': observed_at,
        'environment': environment,
        'policy': ('Read-only research. HLTV first (identity and state only — HLTV publishes no two-sided '
                   'price and its fan votes are never inputs), then esportsbooks and betting-line '
                   'aggregators. Only a bound fixture with both sides priced is a lead.'),
        'target_source': {
            'source_url': 'data/origination.json',
            'source': 'published snapshot in this checkout',
            'snapshot_generated_at': published.get('origination_generated_at'),
            'targets': len(per_fixture),
            'active': len(published['origination_rows']),
        },
        'per_fixture': per_fixture,
        'leads': [p for p in per_fixture if p.get('money_line_lead')],
    }
    return gap_picks, line_research


def write_markdown(gap_picks: dict, line_research: dict) -> None:
    lines = [
        f"# Gap picks — {SESSION}",
        '',
        f"Observed {gap_picks['observed_at']} on `{gap_picks['environment']}`.",
        '',
        gap_picks['role'],
        '',
        f"Policy: {gap_picks['policy']}",
        '',
        '## Lobby fixtures missing from the published snapshot',
        '',
    ]
    for row in gap_picks['lobby_fixtures']:
        names = ' vs '.join(row['teams'])
        pick = row.get('pick')
        if pick and pick.get('probabilities'):
            probs = ' / '.join(f"{p * 100:.1f}%" for p in pick['probabilities'])
            side = pick.get('pick_team') or 'no side (even estimate)'
            lines.append(f"- **{names}** ({row.get('competition')}, {row.get('starts_at')}) — "
                         f"status `{row['status']}` — pick **{side}** {probs} · {pick.get('label')} · "
                         f"source: {pick.get('source')} {pick.get('source_url')} — {row.get('limitation')}")
        else:
            lines.append(f"- **{names}** ({row.get('competition')}, {row.get('starts_at')}) — "
                         f"status `{row['status']}` — no pick — {row.get('limitation')}")
        for r in row.get('research') or []:
            lines.append(f"    - {r.get('stage')} · {r.get('status')}: {r.get('detail')}")
    lines += ['', '## No-line fixtures (research-model rows) — dated sweep', '']
    for row in gap_picks['no_line_fixtures']:
        names = ' vs '.join(row['teams'])
        pick = row.get('pick')
        if pick and pick.get('probabilities'):
            probs = ' / '.join(f"{p * 100:.1f}%" for p in pick['probabilities'])
            lines.append(f"- **{names}** — money-line lead: **{pick.get('pick_team')}** {probs} · "
                         f"{pick.get('source')} {pick.get('source_url')} — {row.get('limitation')}")
        else:
            cur = row.get('current_estimate') or {}
            lines.append(f"- **{names}** — no money line found — {row.get('limitation')}"
                         + (f" Current estimate: {cur.get('label')}." if cur else ''))
    (OUT_DIR / 'gap-picks.md').write_text('\n'.join(lines) + '\n')

    llines = [f"# Line-source research — {SESSION}", '',
              f"Observed {line_research['observed_at']} on `{line_research['environment']}`.",
              '', line_research['policy'], '', '## Per fixture', '']
    for p in line_research['per_fixture']:
        llines.append(f"- **{' vs '.join(p['teams'])}** (`{p.get('id')}`) — lead: "
                      f"{p.get('money_line_lead')} — {p.get('verdict')}")
    (OUT_DIR / 'line-source-research.md').write_text('\n'.join(llines) + '\n')


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', action='store_true', help='probe live sources (runner)')
    ap.add_argument('--replay', action='store_true', help='re-render records from saved evidence')
    args = ap.parse_args()
    observed = iso(now())
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.replay and not args.live:
        evidence = EVIDENCE / 'hotspawn-fixtures.json'
        if not evidence.exists():
            print('replay needs evidence/hotspawn-fixtures.json', file=sys.stderr)
            return 2
        body = json.loads(evidence.read_text())
        fixtures = []
        for row in body if isinstance(body, list) else []:
            start = int(row.get('scheduled_start_time') or 0) / 1000
            fixtures.append({
                'id': str(row.get('id')), 'teams': [row.get('participants0_name') or '', row.get('participants1_name') or ''],
                'competition': row.get('competition_name') or '',
                'starts_at': datetime.fromtimestamp(start, UTC).isoformat(timespec='seconds').replace('+00:00', 'Z') if start else None,
                'started': row.get('start_time') is not None,
                'score': [row.get('participants0_score'), row.get('participants1_score')],
                'hotspawn_url': f'https://www.hotspawn.com/matches/x-{row.get("id")}',
            })
        inventory = {'status': 200, 'error': None, 'evidence': 'evidence/hotspawn-fixtures.json',
                     'observed_at': observed, 'fixtures': fixtures}
        environment = 'arena-session-replay'
    else:
        inventory = hotspawn_inventory(observed)
        environment = ('github-actions-runner'
                       if os.environ.get('GITHUB_ACTIONS') == 'true' else 'arena-session-fetch')

    published = published_state()
    from scripts.originate import load_registry, valve_rows
    registry = load_registry(ROOT / 'data' / 'origination' / 'aliases.json')

    bo3 = probe_bo3(observed) if args.live else {'rows': [], 'status_log': []}
    bound = {}
    ratings, valve_meta = None, None
    shared = {'hltv': {'status': None, 'text': '', 'evidence': None},
              'books': {}, 'smarkets': {'events': []}, 'thunderpick': {'rows': []}}
    if args.live:
        try:
            ratings, valve_meta = valve_rows(ROOT / 'data', {'live': True})
        except Exception as exc:  # noqa: BLE001
            ratings, valve_meta = None, {'error': f'{type(exc).__name__}: {exc}'[:160],
                                         'source_url': VALVE_STANDINGS,
                                         'snapshot_date': '2026-10-05',
                                         'evidence_file': 'valve-standings'}
        shared['hltv'] = probe_hltv_matches_page()
        shared['books'] = probe_book_surfaces()
        shared['smarkets'] = probe_smarkets_page()
        shared['thunderpick'] = probe_thunderpick_page(observed)

    targets = []
    seen = set()
    for fixture in inventory['fixtures']:
        ident = fixture.get('id')
        if ident and ident in published['ids']:
            continue
        if pair_key(fixture['teams']) in published['pairs'] and all(fixture['teams']):
            continue
        targets.append(fixture)
    for ident, orig in published['origination_rows'].items():
        method = ((orig.get('origination') or {}).get('method'))
        if method in {'market', 'bookmaker', 'consensus', 'reference', 'guidance'}:
            continue
        match = published['rows'].get(ident)
        if match and match.get('availability') != 'past':
            targets.append({'id': ident,
                            'teams': [t.get('name') or '' for t in match.get('teams') or []],
                            'competition': match.get('competition'),
                            'starts_at': match.get('starts_at'),
                            'hotspawn_url': f'https://play.hotspawn.com/cs2-pickems#fixture-{ident}'})

    for fixture in targets:
        key = fixture.get('id') or pair_key(fixture['teams'])
        if key in seen:
            continue
        seen.add(key)
        facts = {}
        if args.live:
            # Every probe failure is evidence, never fatal: one broken surface
            # must not stop the remaining fixtures from being researched.
            for stage, fn in (
                    ('hltv', lambda: probe_hltv(fixture, shared['hltv'])),
                    ('bo3', lambda: bo3_binding(fixture, bo3, registry)),
                    ('smarkets', lambda: smarkets_binding(fixture, shared['smarkets'])),
                    ('thunderpick', lambda: thunderpick_binding(fixture, shared['thunderpick'], observed)),
                    ('pinnacle', lambda: probe_pinnacle(fixture, observed)),
                    ('books', lambda: book_rows_for(fixture, shared['books']))):
                try:
                    facts[stage] = fn()
                except Exception as exc:  # noqa: BLE001 - recorded, never fatal
                    facts[stage] = {'error': f'{type(exc).__name__}: {exc}'[:180]}
        bound[key] = facts

    gap_picks, line_research = build_record(inventory, published, bound, ratings, valve_meta,
                                            registry, observed, environment)
    (OUT_DIR / 'gap-picks.json').write_text(json.dumps(gap_picks, indent=1, ensure_ascii=False))
    (OUT_DIR / 'line-source-research.json').write_text(json.dumps(line_research, indent=1, ensure_ascii=False))
    write_markdown(gap_picks, line_research)
    print(json.dumps(gap_picks['counts'], indent=1))
    print(f"wrote data/research/1531ecf1/gap-picks.json + line-source-research.json "
          f"({environment}, {observed})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
