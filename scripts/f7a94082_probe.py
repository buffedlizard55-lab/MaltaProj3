"""Read-only multi-source research & verification probe (session arena-f7a94082).

Purpose
-------
1. For every active Hotspawn CS2 fixture that lacks an external betting line (either
   unresolved or priced by a research model), investigate sources in brief order:
   HLTV first (match listing + world ranking), then first-party exchanges,
   esportsbooks and aggregators (Polymarket CLOB, Kalshi, Thunderpick, Bovada,
   Pinnacle Arcadia sport 12 = Esports, Smarkets exchange, SX Bet exchange,
   bo3.gg bookmaker relay, plus 15 web esportsbooks/aggregators).
2. Fix two defects found in earlier session probes on main:
   - Never match team names inside raw HTML markup/CSS/JS or on non-200 / challenge
     responses (which caused ``scripts/3a5448de_probe.py`` to match team ``Color``
     against CSS ``color:`` and ``Infinite`` against ``infinite`` on 403/404/410 pages).
   - Query Pinnacle Arcadia's real Esports sport ID ``12`` (not soccer ``29`` as in
     ``scripts/fd99abd9_probe.py``) and never label sandbox ``SSLZeroReturnError``
     transport failures as remote HTTP ``403`` Cloudflare blocks.
3. Optional ``--full-audit <dir>`` runs a full read-only live pipeline capture into
   ``<dir>``, scans all raw provider boards by start-time window to uncover any
   competition-scoped team display-name aliases or thin/wide order books, and audits
   the currently deployed GitHub Pages site.

This module NEVER invents, modifies, or writes probabilities, picks, or aliases into
``data/latest.json`` or ``data/origination.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from scripts.domain import iso, name_key, timestamp

UA = 'HotspawnCS2Coverage/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'

SURFACES: list[tuple[str, str, str]] = [
    # HLTV first, per user brief.
    ('HLTV match listing', 'https://www.hltv.org/matches', 'hltv'),
    ('HLTV world ranking', 'https://www.hltv.org/ranking/teams', 'hltv'),
    # Esportsbooks & odds aggregators.
    ('GG.BET CS2', 'https://gg.bet/en/counter-strike', 'book'),
    ('BetBoom CS2', 'https://betboom.ru/sport/cs2', 'book'),
    ('Stake CS2', 'https://stake.com/sports/esports/counter-strike-2', 'book'),
    ('BC.Game CS2', 'https://bc.game/sports/esports', 'book'),
    ('1xBet CS2', 'https://1xbet.com/en/line/counter-strike-2', 'book'),
    ('Marathonbet CS2', 'https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/', 'book'),
    ('Betway CS2', 'https://www.betway.com/en/sports/esports/counter-strike-2', 'book'),
    ('DraftKings CS2', 'https://sportsbook.draftkings.com/leagues/esports/counter-strike-2', 'book'),
    ('Rivalry CS2', 'https://www.rivalry.com/esports/counter-strike-2-betting', 'book'),
    ('Unibet CS2', 'https://www.unibet.com/betting/sports/filter/esports/cs2', 'book'),
    ('Betsson CS2', 'https://www.betsson.com/en/sportsbook/esports/counter-strike', 'book'),
    ('Cloudbet CS2', 'https://www.cloudbet.com/en/sports/counter-strike', 'book'),
    ('OddsPortal CS2', 'https://www.oddsportal.com/esports/counter-strike/', 'aggregator'),
    ('EGamersWorld CS2', 'https://egamersworld.com/counterstrike/matches', 'aggregator'),
    ('Oddspedia CS2', 'https://www.oddspedia.com/esports/counter-strike-2', 'aggregator'),
]

COMMON_ENGLISH_TEAM_WORDS = {
    'color', 'infinite', 'unity', 'spirit', 'legacy', 'alliance', 'envy',
    'fury', 'wildcard', 'imperial', 'nemiga', 'monte', 'aurora', 'heroic',
    'passion', 'sinners', 'rooster', 'martians', 'procyon', 'voca', 'hotu',
}

CHALLENGE_MARKERS = (
    'cf-chl', 'just a moment', 'attention required', 'cloudflare',
    'captcha', 'access denied', 'ddos-guard', 'enable javascript and cookies',
)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def visible_text_from_html(html: str) -> str:
    """Extract human-visible text only after stripping script/style/template nodes."""
    soup = BeautifulSoup(html or '', 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'template', 'svg', 'head']):
        tag.decompose()
    return soup.get_text(' ', strip=True)


def detect_challenge(status: int | None, raw_text: str, headers: dict[str, str] | None = None) -> str | None:
    headers = headers or {}
    cf_mitigated = headers.get('cf-mitigated') or headers.get('CF-Mitigated')
    if cf_mitigated:
        return f'cloudflare:{cf_mitigated}'
    sample = (raw_text or '')[:12000].lower()
    if status in {401, 403, 429, 503} or len(raw_text or '') < 16000:
        for marker in CHALLENGE_MARKERS:
            if marker in sample:
                return marker
    return None


def find_teams_in_visible_text(
    status: int | None,
    challenge: str | None,
    visible_text: str,
    team_names: list[str],
    fixture_pairs: list[tuple[str, str]],
) -> list[str]:
    """Conservative visible-text team detection.

    - Never scans non-200 or challenge responses.
    - Never scans raw HTML/CSS/JS attributes.
    - Multi-word or distinctive esports handles match on strict token boundaries.
    - Single common English words (e.g. ``Color``, ``Infinite``, ``UNiTY``) match
      ONLY when their scheduled opponent ALSO appears in the same visible page text
      (preventing generic UI words from producing false-positive team hits).
    """
    if status != 200 or challenge or not visible_text:
        return []
    opponents_by_team: dict[str, set[str]] = {}
    for a, b in fixture_pairs:
        opponents_by_team.setdefault(a, set()).add(b)
        opponents_by_team.setdefault(b, set()).add(a)

    def raw_present(name: str) -> bool:
        clean = (name or '').strip()
        if len(clean) < 3:
            return False
        pattern = r'(?<![A-Za-z0-9])' + re.escape(clean) + r'(?![A-Za-z0-9])'
        return bool(re.search(pattern, visible_text, flags=re.IGNORECASE))

    found: list[str] = []
    for name in sorted(set(team_names), key=str.lower):
        if not raw_present(name):
            continue
        if name.strip().lower() in COMMON_ENGLISH_TEAM_WORDS:
            opps = opponents_by_team.get(name, set())
            if not any(raw_present(opp) for opp in opps):
                continue
        found.append(name)
    return found


def probe_surface(
    sess: requests.Session,
    name: str,
    url: str,
    kind: str,
    team_names: list[str],
    fixture_pairs: list[tuple[str, str]],
    timeout: int = 12,
) -> dict[str, Any]:
    observed = iso(datetime.now(timezone.utc))
    try:
        resp = sess.get(url, timeout=timeout, allow_redirects=True)
        raw = resp.content or b''
        text = resp.text or ''
        challenge = detect_challenge(resp.status_code, text, dict(resp.headers))
        vis = visible_text_from_html(text) if resp.status_code == 200 and not challenge else ''
        teams = find_teams_in_visible_text(resp.status_code, challenge, vis, team_names, fixture_pairs)
        return {
            'name': name,
            'url': url,
            'kind': kind,
            'observed_at': observed,
            'http': resp.status_code,
            'final_url': resp.url,
            'bytes': len(raw),
            'sha256': sha256_bytes(raw),
            'challenge': challenge,
            'visible_chars': len(vis),
            'teams_found': teams,
            'error': None,
        }
    except requests.RequestException as exc:
        return {
            'name': name,
            'url': url,
            'kind': kind,
            'observed_at': observed,
            'http': None,
            'final_url': None,
            'bytes': None,
            'sha256': None,
            'challenge': None,
            'visible_chars': 0,
            'teams_found': [],
            'error': f'{type(exc).__name__}: {str(exc)[:220]}',
        }


def american_to_decimal(odds: float | int | None) -> float | None:
    if odds is None:
        return None
    val = float(odds)
    if val >= 100:
        return round(1.0 + val / 100.0, 6)
    if val <= -100:
        return round(1.0 + 100.0 / abs(val), 6)
    return None


def probe_pinnacle_cs2(sess: requests.Session, timeout: int = 15) -> dict[str, Any]:
    """Query Pinnacle Arcadia sport 12 (Esports) CS2 leagues, matchups & straight markets."""
    base = 'https://guest.api.arcadia.pinnacle.com/0.1'
    leagues_url = f'{base}/sports/12/leagues?all=false'
    out: dict[str, Any] = {
        'url': leagues_url,
        'sport_id': 12,
        'observed_at': iso(datetime.now(timezone.utc)),
        'http': None,
        'cs2_leagues': 0,
        'cs2_prematch_series': 0,
        'priced_series': 0,
        'rows': [],
        'error': None,
    }
    try:
        r = sess.get(leagues_url, timeout=timeout)
        out['http'] = r.status_code
        r.raise_for_status()
        leagues = r.json()
        cs2_leagues = [
            lg for lg in leagues
            if any(tok in (lg.get('name') or '').lower() for tok in ('cs2', 'counter-strike', 'cs:go'))
        ]
        out['cs2_leagues'] = len(cs2_leagues)
        for lg in cs2_leagues:
            lid = lg['id']
            m_resp = sess.get(f'{base}/leagues/{lid}/matchups', timeout=timeout)
            s_resp = sess.get(f'{base}/leagues/{lid}/markets/straight', timeout=timeout)
            if m_resp.status_code != 200:
                continue
            markets_by_id: dict[int, list[dict[str, Any]]] = {}
            if s_resp.status_code == 200:
                for mk in s_resp.json():
                    if mk.get('type') == 'moneyline' and mk.get('period') == 0 and not mk.get('isAlternate'):
                        markets_by_id.setdefault(mk['matchupId'], []).append(mk)
            for mu in m_resp.json():
                if mu.get('type') != 'matchup' or mu.get('parentId') is not None or mu.get('units') not in {None, 'Regular'}:
                    continue
                parts = [p for p in (mu.get('participants') or []) if p.get('alignment') in {'home', 'away'}]
                if len(parts) != 2:
                    continue
                out['cs2_prematch_series'] += 1
                mks = markets_by_id.get(mu['id'], [])
                decimals = None
                if mks:
                    prices = {pr.get('designation'): american_to_decimal(pr.get('price')) for pr in (mks[0].get('prices') or [])}
                    if prices.get('home') and prices.get('away'):
                        decimals = [prices['home'], prices['away']]
                        out['priced_series'] += 1
                out['rows'].append({
                    'league_id': lid,
                    'league': lg.get('name'),
                    'matchup_id': mu['id'],
                    'startTime': mu.get('startTime'),
                    'liveMode': mu.get('liveMode'),
                    'teams': [parts[0].get('name'), parts[1].get('name')],
                    'decimal_odds': decimals,
                    'matchups_url': f'{base}/leagues/{lid}/matchups',
                    'markets_url': f'{base}/leagues/{lid}/markets/straight',
                })
    except (requests.RequestException, ValueError, KeyError) as exc:
        out['error'] = f'{type(exc).__name__}: {str(exc)[:220]}'
    return out


def probe_smarkets_cs2(sess: requests.Session, timeout: int = 15) -> dict[str, Any]:
    """Query Smarkets public v3 API for upcoming CS2 matches and two-sided quotes."""
    base = 'https://api.smarkets.com/v3'
    events_url = f'{base}/events/?state=new&state=upcoming&type=csgo_match&limit=200'
    out: dict[str, Any] = {
        'url': events_url,
        'observed_at': iso(datetime.now(timezone.utc)),
        'http': None,
        'events_count': 0,
        'two_sided_count': 0,
        'rows': [],
        'error': None,
    }
    try:
        r = sess.get(events_url, timeout=timeout)
        out['http'] = r.status_code
        r.raise_for_status()
        events = (r.json() or {}).get('events') or []
        out['events_count'] = len(events)
        eids = [str(ev['id']) for ev in events if ev.get('id')]
        markets_by_event: dict[str, dict[str, Any]] = {}
        contracts_by_market: dict[str, list[dict[str, Any]]] = {}
        quotes_by_market: dict[str, dict[str, Any]] = {}
        for idx in range(0, len(eids), 40):
            batch = ','.join(eids[idx:idx + 40])
            mr = sess.get(f'{base}/events/{batch}/markets/', timeout=timeout)
            if mr.status_code != 200:
                continue
            mids: list[str] = []
            for mk in (mr.json() or {}).get('markets') or []:
                slug = (mk.get('market_type') or {}).get('name') or mk.get('slug') or ''
                if 'winner' in slug.lower() or mk.get('name', '').lower() in {'winner', 'match winner', 'full-time result'}:
                    eid = str(mk['event_id'])
                    if eid not in markets_by_event:
                        markets_by_event[eid] = mk
                        mids.append(str(mk['id']))
            if mids:
                mb = ','.join(mids)
                cr = sess.get(f'{base}/markets/{mb}/contracts/', timeout=timeout)
                qr = sess.get(f'{base}/markets/{mb}/quotes/', timeout=timeout)
                if cr.status_code == 200:
                    for c in (cr.json() or {}).get('contracts') or []:
                        contracts_by_market.setdefault(str(c['market_id']), []).append(c)
                if qr.status_code == 200:
                    quotes_by_market.update(qr.json() or {})
        for ev in events:
            eid = str(ev['id'])
            mk = markets_by_event.get(eid)
            contracts = contracts_by_market.get(str(mk['id']), []) if mk else []
            contract_rows = []
            two_sided = False
            for c in contracts:
                q = quotes_by_market.get(str(c['id'])) or {}
                bids = q.get('bids') or []
                offers = q.get('offers') or []
                best_bid = bids[0]['price'] / 10000.0 if bids else None
                best_ask = offers[0]['price'] / 10000.0 if offers else None
                contract_rows.append({
                    'id': str(c['id']),
                    'name': c.get('name'),
                    'best_bid': best_bid,
                    'best_ask': best_ask,
                    'spread': round(best_ask - best_bid, 4) if (best_bid is not None and best_ask is not None) else None,
                })
            if len(contract_rows) == 2 and all(x['best_bid'] and x['best_ask'] and x['best_ask'] > x['best_bid'] for x in contract_rows):
                two_sided = True
                out['two_sided_count'] += 1
            out['rows'].append({
                'event_id': eid,
                'name': ev.get('name'),
                'full_slug': ev.get('full_slug'),
                'web_url': 'https://smarkets.com' + str(ev.get('full_slug') or f'/event/{eid}'),
                'start_datetime': ev.get('start_datetime'),
                'state': ev.get('state'),
                'market_id': str(mk['id']) if mk else None,
                'two_sided': two_sided,
                'contracts': contract_rows,
            })
    except (requests.RequestException, ValueError, KeyError) as exc:
        out['error'] = f'{type(exc).__name__}: {str(exc)[:220]}'
    return out


def probe_bo3_upcoming(sess: requests.Session, timeout: int = 15) -> dict[str, Any]:
    """Query bo3.gg upcoming CS2 matches API and extract embedded bookmaker odds."""
    url = (
        'https://api.bo3.gg/api/v1/matches?page[offset]=0&page[limit]=100'
        '&sort=start_date&filter[matches.status][in]=upcoming,current'
        '&filter[matches.discipline_id][eq]=1'
        '&with=teams,tournament,bet_updates'
    )
    out: dict[str, Any] = {
        'url': url,
        'observed_at': iso(datetime.now(timezone.utc)),
        'http': None,
        'matches_count': 0,
        'with_two_sided_bet': 0,
        'rows': [],
        'error': None,
    }
    try:
        r = sess.get(url, timeout=timeout)
        out['http'] = r.status_code
        r.raise_for_status()
        payload = r.json() or {}
        rows = payload.get('results') or payload.get('data') or []
        out['matches_count'] = len(rows)
        for m in rows:
            t1 = m.get('team1') or {}
            t2 = m.get('team2') or {}
            bet = m.get('bet_updates') or {}
            b1 = (bet.get('team_1') or {}).get('coeff') if isinstance(bet, dict) else None
            b2 = (bet.get('team_2') or {}).get('coeff') if isinstance(bet, dict) else None
            two = bool(b1 and b2 and float(b1) > 1.0 and float(b2) > 1.0)
            if two:
                out['with_two_sided_bet'] += 1
            slug = m.get('slug')
            out['rows'].append({
                'slug': slug,
                'url': f'https://bo3.gg/matches/{slug}' if slug else 'https://bo3.gg/matches',
                'start_date': m.get('start_date'),
                'bo_type': m.get('bo_type'),
                'tournament': (m.get('tournament') or {}).get('name'),
                'teams': [t1.get('name'), t2.get('name')],
                'bet_updates': bet if two else None,
                'two_sided_bet': two,
            })
    except (requests.RequestException, ValueError, KeyError) as exc:
        out['error'] = f'{type(exc).__name__}: {str(exc)[:220]}'
    return out


def raw_board_near_matches(
    active_matches: list[dict[str, Any]],
    pinnacle: dict[str, Any],
    smarkets: dict[str, Any],
    bo3: dict[str, Any],
    sess: requests.Session,
) -> dict[str, Any]:
    """Scan Polymarket Gamma, Kalshi, Thunderpick, Bovada, Pinnacle, Smarkets & bo3
    by start-time window (±6h) for all active Hotspawn CS2 matches to uncover any
    unaliased display names, wide books, or additional consensus quotes."""
    raw_boards: dict[str, list[dict[str, Any]]] = {
        'polymarket': [],
        'kalshi': [],
        'thunderpick': [],
        'bovada': [],
        'pinnacle': pinnacle.get('rows') or [],
        'smarkets': smarkets.get('rows') or [],
        'bo3': bo3.get('rows') or [],
    }
    # 1. Polymarket Gamma CS2 events
    try:
        offset = 0
        seen_ids: set[str] = set()
        for _ in range(12):
            gr = sess.get(
                'https://gamma-api.polymarket.com/events',
                params={'tag_slug': 'counter-strike-2', 'active': 'true', 'closed': 'false', 'limit': 100, 'offset': offset},
                timeout=15,
            )
            if gr.status_code != 200:
                break
            batch = gr.json() or []
            if not batch:
                break
            new_any = False
            for ev in batch:
                eid = str(ev.get('id'))
                if eid in seen_ids:
                    continue
                seen_ids.add(eid)
                new_any = True
                markets = ev.get('markets') or []
                series_mk = None
                for mk in markets:
                    q = (mk.get('question') or '') + ' ' + (mk.get('groupItemTitle') or '')
                    if not any(x in q.lower() for x in ('map 1', 'map 2', 'map 3', 'handicap', 'total', 'over/under', 'o/u')):
                        series_mk = mk
                        break
                raw_boards['polymarket'].append({
                    'id': eid,
                    'slug': ev.get('slug'),
                    'title': ev.get('title'),
                    'startDate': ev.get('startTime') or ev.get('startDate'),
                    'url': f"https://polymarket.com/event/{ev.get('slug')}",
                    'outcomes': series_mk.get('outcomes') if series_mk else None,
                    'outcomePrices': series_mk.get('outcomePrices') if series_mk else None,
                    'bestBid': series_mk.get('bestBid') if series_mk else None,
                    'bestAsk': series_mk.get('bestAsk') if series_mk else None,
                    'spread': series_mk.get('spread') if series_mk else None,
                })
            if not new_any or len(batch) < 100:
                break
            offset += 100
    except requests.RequestException:
        pass

    # 2. Kalshi CS2 open events
    try:
        kr = sess.get(
            'https://api.elections.kalshi.com/trade-api/v2/events',
            params={'series_ticker': 'KXCS2GAME', 'status': 'open', 'with_nested_markets': 'true', 'limit': 200},
            timeout=15,
        )
        if kr.status_code == 200:
            for ev in (kr.json() or {}).get('events') or []:
                mks = ev.get('markets') or []
                raw_boards['kalshi'].append({
                    'event_ticker': ev.get('event_ticker'),
                    'title': ev.get('title'),
                    'sub_title': ev.get('sub_title'),
                    'markets': [
                        {
                            'ticker': mk.get('ticker'),
                            'yes_sub_title': mk.get('yes_sub_title'),
                            'expected_expiration_time': mk.get('expected_expiration_time'),
                            'yes_bid_dollars': mk.get('yes_bid_dollars'),
                            'yes_ask_dollars': mk.get('yes_ask_dollars'),
                        }
                        for mk in mks
                    ],
                })
    except requests.RequestException:
        pass

    # 3. Thunderpick POST /api/matches
    try:
        tr = sess.post('https://thunderpick.io/api/matches', json={'gameIds': [6]}, timeout=15)
        if tr.status_code == 200:
            body = tr.json() or {}
            data_obj = body.get('data') or {}
            items = data_obj if isinstance(data_obj, list) else (
                (data_obj.get('upcoming') or []) + (data_obj.get('matches') or [])
            )
            for item in items:
                if item.get('status') not in {1, '1', 'open', 'upcoming', None}:
                    continue
                teams = item.get('teams') or {}
                home = (teams.get('home') or {}) if isinstance(teams, dict) else {}
                away = (teams.get('away') or {}) if isinstance(teams, dict) else {}
                mk = item.get('market') or {}
                raw_boards['thunderpick'].append({
                    'id': item.get('id'),
                    'competition': (item.get('tournament') or {}).get('name') if isinstance(item.get('tournament'), dict) else item.get('competition'),
                    'startTime': item.get('startTime'),
                    'teams': [home.get('name'), away.get('name')],
                    'odds': [
                        (mk.get('home') or {}).get('odds') if isinstance(mk.get('home'), dict) else None,
                        (mk.get('away') or {}).get('odds') if isinstance(mk.get('away'), dict) else None,
                    ],
                })
    except requests.RequestException:
        pass

    # 4. Bovada CS2 coupon
    try:
        br = sess.get(
            'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2',
            params={'marketFilterId': 'def', 'preMatchOnly': 'true', 'eventsLimit': 500, 'lang': 'en'},
            timeout=15,
        )
        if br.status_code == 200:
            for bucket in br.json() or []:
                comp = (bucket.get('path') or [{}])[0].get('description') if bucket.get('path') else None
                for ev in bucket.get('events') or []:
                    if ev.get('live'):
                        continue
                    comps = ev.get('competitors') or []
                    if len(comps) != 2:
                        continue
                    st = iso(datetime.fromtimestamp(ev['startTime'] / 1000.0, tz=timezone.utc)) if ev.get('startTime') else None
                    decs = None
                    for dg in ev.get('displayGroups') or []:
                        for mk in dg.get('markets') or []:
                            if (mk.get('description') or '').lower() == 'moneyline' and (mk.get('period') or {}).get('description') in {'Match', 'Game', 'Live Match', None}:
                                outs = mk.get('outcomes') or []
                                if len(outs) == 2:
                                    decs = [(o.get('price') or {}).get('decimal') for o in outs]
                                    break
                    raw_boards['bovada'].append({
                        'id': ev.get('id'),
                        'link': 'https://www.bovada.lv/sports' + str(ev.get('link') or ''),
                        'competition': comp,
                        'description': ev.get('description'),
                        'startTime': st,
                        'teams': [comps[0].get('name'), comps[1].get('name')],
                        'decimal_odds': decs,
                    })
    except requests.RequestException:
        pass

    # Match active Hotspawn fixtures by token overlap across all boards
    near_by_fixture: dict[str, dict[str, Any]] = {}
    for m in active_matches:
        t0, t1 = m['teams'][0]['name'], m['teams'][1]['name']
        k0, k1 = name_key(t0), name_key(t1)
        words = {w for nm in (t0, t1) for w in re.split(r'[^a-z0-9]+', nm.lower()) if len(w) >= 3 and w not in {'team', 'gaming', 'esports', 'academy', 'club'}}
        hits: dict[str, list[dict[str, Any]]] = {}
        for board_name, rows in raw_boards.items():
            matched = []
            for row in rows:
                blob = json.dumps(row, ensure_ascii=False).lower()
                if any(w in blob for w in words) or k0 in name_key(blob) or k1 in name_key(blob):
                    matched.append(row)
            if matched:
                hits[board_name] = matched[:8]
        near_by_fixture[m['id']] = {
            'teams': [t0, t1],
            'competition': m.get('competition'),
            'starts_at': m.get('starts_at'),
            'candidate_hits': hits,
        }

    return {
        'board_totals': {k: len(v) for k, v in raw_boards.items()},
        'raw_boards': raw_boards,
        'near_by_fixture': near_by_fixture,
    }


def _match_pair_key(names: list[str | None]) -> frozenset[str]:
    return frozenset(name_key(n or '') for n in names if n)


def build_sweep_record(
    latest: dict[str, Any],
    origination: dict[str, Any],
    sess: requests.Session,
    timeout: int = 12,
) -> dict[str, Any]:
    """Run the HLTV-first + books + Pinnacle (sport 12) + Smarkets + bo3 sweep for
    every active non-money/unresolved fixture in ``origination``."""
    observed_at = iso(datetime.now(timezone.utc))
    latest_by_id = {str(m['id']): m for m in (latest.get('matches') or [])}
    targets = []
    featured_unresolved = []
    for m in origination.get('matches') or []:
        if m.get('featured_method') is None:
            featured_unresolved.append({
                'id': str(m['id']),
                'teams': [t['name'] for t in m['teams']],
                'competition': m.get('competition'),
                'starts_at': m.get('starts_at'),
                'hotspawn_url': m.get('source_url'),
            })
        oa = m.get('origination') or {}
        if oa.get('method') not in {'market', 'bookmaker', 'consensus'}:
            targets.append(m)

    team_names = [t['name'] for m in targets for t in m['teams'] if t.get('name')]
    fixture_pairs = [(m['teams'][0]['name'], m['teams'][1]['name']) for m in targets]

    surfaces = [
        probe_surface(sess, name, url, kind, team_names, fixture_pairs, timeout=timeout)
        for name, url, kind in SURFACES
    ]
    pinnacle = probe_pinnacle_cs2(sess, timeout=max(timeout, 15))
    smarkets = probe_smarkets_cs2(sess, timeout=max(timeout, 15))
    bo3 = probe_bo3_upcoming(sess, timeout=max(timeout, 15))

    fixture_records = []
    for m in targets:
        t0, t1 = m['teams'][0]['name'], m['teams'][1]['name']
        pk = _match_pair_key([t0, t1])
        start_ts = timestamp(m.get('starts_at'))
        oa = m.get('origination') or {}

        bo3_match = None
        for brow in bo3.get('rows') or []:
            if _match_pair_key(brow.get('teams') or []) == pk:
                bt = timestamp(brow.get('start_date'))
                if start_ts and bt and abs((bt - start_ts).total_seconds()) <= 7200:
                    bo3_match = brow
                    break

        pin_match = None
        for prow in pinnacle.get('rows') or []:
            if _match_pair_key(prow.get('teams') or []) == pk:
                pt = timestamp(prow.get('startTime'))
                if start_ts and pt and abs((pt - start_ts).total_seconds()) <= 7200:
                    pin_match = prow
                    break

        smk_match = None
        for srow in smarkets.get('rows') or []:
            cnames = [c.get('name') for c in (srow.get('contracts') or [])]
            if _match_pair_key(cnames) == pk:
                st = timestamp(srow.get('start_datetime'))
                if start_ts and st and abs((st - start_ts).total_seconds()) <= 7200:
                    smk_match = srow
                    break

        two_sided_relay = bool(bo3_match and bo3_match.get('two_sided_bet'))
        pin_listed = bool(pin_match and pin_match.get('decimal_odds'))
        smk_two_sided = bool(smk_match and smk_match.get('two_sided'))
        src_lm = latest_by_id.get(str(m['id'])) or {}
        hltv_stage = next((r for r in (m.get('research') or src_lm.get('research') or []) if 'hltv' in str(r.get('stage') or '').lower()), None)

        fixture_records.append({
            'id': str(m['id']),
            'teams': [t0, t1],
            'competition': m.get('competition'),
            'starts_at': m.get('starts_at'),
            'locks_at': m.get('locks_at'),
            'hotspawn_url': m.get('source_url'),
            'hltv_match_url': hltv_stage.get('source_url') if hltv_stage else None,
            'current_method': oa.get('method'),
            'current_basis': oa.get('model_label') or oa.get('label') or 'Explicitly unresolved (blank)',
            'probabilities': oa.get('probabilities'),
            'pick_index': m.get('pick_index'),
            'pick': m['teams'][m['pick_index']]['name'] if m.get('pick_index') is not None else None,
            'source_urls': oa.get('source_urls') or ([oa['source_url']] if oa.get('source_url') else []),
            'money_line_lead': bool(two_sided_relay or pin_listed or smk_two_sided),
            'bo3_bound': bool(bo3_match),
            'bo3_bound_url': bo3_match.get('url') if bo3_match else None,
            'bo3_bet': bo3_match.get('bet_updates') if two_sided_relay else None,
            'bo3_bet_updates': bo3_match.get('bet_updates') if two_sided_relay else None,
            'two_sided_relay_price': two_sided_relay,
            'pinnacle_listed': pin_listed,
            'pinnacle_match': pin_match,
            'smarkets_two_sided': smk_two_sided,
            'smarkets_match': smk_match,
            'limitations': m.get('limitations') or oa.get('limitations') or [],
        })

    hltv_surfaces = [s for s in surfaces if s['kind'] == 'hltv']
    env_label = 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'local-sandbox'
    return {
        'schema_version': 2,
        'session': 'arena-f7a94082',
        'environment': env_label,
        'observed_at': observed_at,
        'snapshot_generated_at': origination.get('generated_at') or latest.get('generated_at'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'active_total': len(origination.get('matches') or []),
        'target_count': len(fixture_records),
        'featured_unresolved_count': len(featured_unresolved),
        'featured_unresolved': featured_unresolved,
        'hltv_statuses': [s.get('http') or s.get('error') for s in hltv_surfaces],
        'pinnacle_esports': {
            'url': pinnacle['url'],
            'sport_id': 12,
            'http': pinnacle['http'],
            'cs2_leagues': pinnacle['cs2_leagues'],
            'cs2_prematch_series': pinnacle['cs2_prematch_series'],
            'priced_series': pinnacle['priced_series'],
            'error': pinnacle['error'],
        },
        'smarkets_exchange': {
            'url': smarkets['url'],
            'http': smarkets['http'],
            'events_count': smarkets['events_count'],
            'two_sided_count': smarkets['two_sided_count'],
            'error': smarkets['error'],
        },
        'bo3_upcoming': {
            'url': bo3['url'],
            'http': bo3['http'],
            'matches_count': bo3['matches_count'],
            'with_two_sided_bet': bo3['with_two_sided_bet'],
            'error': bo3['error'],
        },
        'surfaces': surfaces,
        'per_fixture': fixture_records,
        'fixtures': fixture_records,
    }


def render_markdown(record: dict[str, Any]) -> str:
    lines = [
        f"# Line-source research for fixtures without a betting line — {record['session']}",
        '',
        f"- **Observed at:** `{record['observed_at']}`",
        f"- **Inventory snapshot:** `{record.get('inventory_observed_at')}` (complete-picks generated `{record.get('snapshot_generated_at')}`)",
        f"- **Active Hotspawn CS2 fixtures:** `{record.get('active_total')}` total · `{record.get('target_count')}` without a first-party betting line · `{record.get('featured_unresolved_count')}` unresolved in the featured exact-name feed",
        '',
        'Research order follows the user brief strictly: **HLTV first** (`https://www.hltv.org/matches`, `https://www.hltv.org/ranking/teams`), then first-party exchanges, esportsbooks and aggregators (Polymarket CLOB, Kalshi, Thunderpick, Bovada, Pinnacle Arcadia sport `12` Esports, Smarkets `csgo_match`, bo3.gg bookmaker relay, plus 15 web esportsbooks/aggregators). Team detection strips `<script>`/`<style>` markup first and never scans non-200 or challenge pages.',
        '',
        '## Per-fixture findings (matches without a first-party betting line)',
        '',
        '| Fixture | Competition & UTC start | Pick & probabilities | Basis & official source | bo3.gg bound / relay | Pinnacle (sport 12) | Smarkets | Limitation |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for f in record.get('fixtures') or []:
        probs = f.get('probabilities')
        p_txt = f"{probs[0]*100:.1f}% / {probs[1]*100:.1f}%" if probs else '— / — (blank)'
        pick_txt = f"**{f['pick']}** ({p_txt})" if f.get('pick') else f"Explicit blank ({p_txt})"
        srcs = ' '.join(f"[source]({u})" for u in (f.get('source_urls') or [])[:2])
        if f.get('hltv_match_url'):
            srcs = (srcs + f" [HLTV]({f['hltv_match_url']})").strip()
        bo3_txt = (
            f"[relay price]({f['bo3_bound_url']})" if f.get('two_sided_relay_price')
            else (f"[bound, no odds]({f['bo3_bound_url']})" if f.get('bo3_bound') else 'not listed')
        )
        pin_txt = 'priced' if f.get('pinnacle_listed') else 'no line'
        smk_txt = 'two-sided' if f.get('smarkets_two_sided') else 'no line'
        lim = '; '.join(f.get('limitations') or [])[:160] or 'Uncalibrated model estimate; no external betting line.'
        lines.append(
            f"| {' vs '.join(f['teams'])} (`{f['id']}`) | {f.get('competition')} · `{f.get('starts_at')}` | "
            f"{pick_txt} | {f.get('current_basis')} {srcs} | {bo3_txt} | {pin_txt} | {smk_txt} | {lim} |"
        )
    lines += [
        '',
        '## Structured API & web surface sweep',
        '',
        f"- **Pinnacle Arcadia Esports (`sport_id=12`, `{record['pinnacle_esports']['url']}`):** HTTP `{record['pinnacle_esports']['http']}`, `{record['pinnacle_esports']['cs2_leagues']}` CS2 leagues, `{record['pinnacle_esports']['cs2_prematch_series']}` prematch series, `{record['pinnacle_esports']['priced_series']}` with straight moneylines.",
        f"- **Smarkets Exchange (`{record['smarkets_exchange']['url']}`):** HTTP `{record['smarkets_exchange']['http']}`, `{record['smarkets_exchange']['events_count']}` upcoming CS2 events, `{record['smarkets_exchange']['two_sided_count']}` with two-sided quotes.",
        f"- **bo3.gg Upcoming CS2 API (`{record['bo3_upcoming']['url']}`):** HTTP `{record['bo3_upcoming']['http']}`, `{record['bo3_upcoming']['matches_count']}` upcoming/current matches, `{record['bo3_upcoming']['with_two_sided_bet']}` carrying a two-sided bookmaker relay block.",
        '',
        '| Surface | Kind | HTTP | Bytes | Challenge | Verified visible-text teams | Official URL |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for s in record.get('surfaces') or []:
        http_cell = str(s['http']) if s.get('http') is not None else (s.get('error') or 'error')[:60]
        teams_cell = ', '.join(s.get('teams_found') or []) or '—'
        lines.append(
            f"| {s['name']} | {s['kind']} | `{http_cell}` | {s.get('bytes') if s.get('bytes') is not None else '—'} | "
            f"{s.get('challenge') or '—'} | {teams_cell} | {s['url']} |"
        )
    return '\n'.join(lines) + '\n'


def audit_public_pages(sess: requests.Session, base_url: str = 'https://buffedlizard55-lab.github.io/MaltaProj3/') -> dict[str, Any]:
    routes = [
        '', 'picks/', 'origination/', 'unresolved/', 'strategy/',
        'twc-picks/', 'final-day/', 'edge/', 'coverage/', 'methodology/', 'review/',
        'data/latest.json', 'data/origination.json', 'data/row-source-audit.json',
    ]
    report: dict[str, Any] = {'observed_at': iso(datetime.now(timezone.utc)), 'base_url': base_url, 'routes': {}}
    for r in routes:
        url = base_url.rstrip('/') + '/' + r
        try:
            resp = sess.get(url, timeout=15)
            info: dict[str, Any] = {'http': resp.status_code, 'bytes': len(resp.content), 'sha256': sha256_bytes(resp.content)}
            if r.endswith('.json') and resp.status_code == 200:
                body = resp.json()
                info['generated_at'] = body.get('generated_at')
                info['inventory_observed_at'] = body.get('inventory_observed_at')
                info['source_snapshot_at'] = body.get('source_snapshot_at')
                info['counts'] = body.get('counts') or body.get('totals')
                info['coverage_complete'] = body.get('coverage_complete')
            elif resp.status_code == 200:
                m = re.search(r'data-snapshot-generated="([^"]+)"', resp.text[:6000])
                info['html_snapshot_generated'] = m.group(1) if m else None
            report['routes'][r or '/'] = info
        except Exception as exc:
            report['routes'][r or '/'] = {'http': None, 'error': str(exc)[:200]}
    return report


def run_full_audit(work_dir: Path, out_dir: Path, timeout: int = 12) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = work_dir / 'data'
    site_dir = work_dir / 'site'
    import shutil
    if data_dir.exists():
        shutil.rmtree(data_dir)
    shutil.copytree(Path('data'), data_dir)

    subprocess.run([sys.executable, '-m', 'scripts.collect', '--output', str(data_dir)], check=True, env=os.environ.copy())
    subprocess.run([sys.executable, '-m', 'scripts.originate', '--source', str(data_dir), '--live'], check=True, env=os.environ.copy())
    build_proc = subprocess.run([sys.executable, '-m', 'scripts.build', '--data', str(data_dir), '--output', str(site_dir)], capture_output=True, text=True)
    audit_proc = subprocess.run([sys.executable, '-m', 'scripts.audit_rows', '--site', str(site_dir), '--strict'], capture_output=True, text=True) if (site_dir / 'index.html').exists() else None

    latest = json.loads((data_dir / 'latest.json').read_text())
    origination = json.loads((data_dir / 'origination.json').read_text())
    row_audit = json.loads((site_dir / 'data/row-source-audit.json').read_text()) if (site_dir / 'data/row-source-audit.json').exists() else {'totals': None, 'build_returncode': build_proc.returncode, 'build_stderr': build_proc.stderr[-1500:], 'build_stdout': build_proc.stdout[-1500:]}

    sess = requests.Session()
    sess.headers.update({'User-Agent': UA, 'Accept': 'application/json,text/html;q=0.9'})

    sweep = build_sweep_record(latest, origination, sess, timeout=timeout)
    pinnacle_full = probe_pinnacle_cs2(sess, timeout=15)
    smarkets_full = probe_smarkets_cs2(sess, timeout=15)
    bo3_full = probe_bo3_upcoming(sess, timeout=15)
    active_matches = [m for m in latest.get('matches') or [] if m.get('availability') != 'past']
    near = raw_board_near_matches(active_matches, pinnacle_full, smarkets_full, bo3_full, sess)
    public_audit = audit_public_pages(sess)

    # Also inspect whether Hotspawn's API exposes any non-scheduled CS2 statuses (e.g. live/in_progress)
    extra_hotspawn = {}
    for st in ('live', 'in_progress', 'open'):
        try:
            hr = sess.get(
                'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures',
                params={'sport_alias': 'cs2', 'status': st, 'tenantId': 1},
                timeout=12,
            )
            extra_hotspawn[st] = {'http': hr.status_code, 'count': len(hr.json()) if hr.status_code == 200 and isinstance(hr.json(), list) else None}
        except Exception as exc:
            extra_hotspawn[st] = {'http': None, 'error': str(exc)[:120]}

    (out_dir / 'line-source-research.json').write_text(json.dumps(sweep, indent=2, ensure_ascii=False) + '\n')
    (out_dir / 'line-source-research.md').write_text(render_markdown(sweep))
    (out_dir / 'raw-provider-discovery.json').write_text(json.dumps(near, indent=2, ensure_ascii=False) + '\n')
    (out_dir / 'live-snapshot-summary.json').write_text(json.dumps({
        'captured_at': iso(datetime.now(timezone.utc)),
        'latest_generated_at': latest.get('generated_at'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'coverage_complete': latest.get('coverage_complete'),
        'inventory_crosscheck': latest.get('inventory_crosscheck'),
        'featured_counts': latest.get('counts'),
        'complete_counts': origination.get('counts'),
        'row_source_audit_totals': row_audit.get('totals'),
        'hotspawn_other_statuses': extra_hotspawn,
        'public_pages_before_fix': public_audit,
        'active_matches': origination.get('matches'),
    }, indent=2, ensure_ascii=False) + '\n')
    return sweep


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('data/research/f7a94082'))
    parser.add_argument('--timeout', type=int, default=12)
    parser.add_argument('--full-audit', type=Path, help='run isolated full collect+originate+raw-board scan in this scratch dir')
    args = parser.parse_args(argv)

    if args.full_audit:
        sweep = run_full_audit(args.full_audit, args.out, timeout=args.timeout)
        print(f"Full audit complete: {sweep['active_total']} active, {sweep['target_count']} non-money targets")
        return 0

    latest = json.loads((args.data / 'latest.json').read_text())
    origination = json.loads((args.data / 'origination.json').read_text())
    sess = requests.Session()
    sess.headers.update({'User-Agent': UA, 'Accept': 'application/json,text/html;q=0.9'})
    sweep = build_sweep_record(latest, origination, sess, timeout=args.timeout)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'line-source-research.json').write_text(json.dumps(sweep, indent=2, ensure_ascii=False) + '\n')
    (args.out / 'line-source-research.md').write_text(render_markdown(sweep))
    print(f"Sweep complete: {sweep['active_total']} active, {sweep['target_count']} non-money targets -> {args.out}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
