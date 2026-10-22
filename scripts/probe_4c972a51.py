"""Session 4c972a51: reachability and coverage probe for independent price sources.

Read-only. For every candidate surface it records the HTTP status, the final URL
after redirects, the payload size, whether the names of today's *unresolved*
fixtures appear in the payload, and a short excerpt. It never parses a price
into a published feed and it never writes a probability; its output is a dated
evidence file for deciding which sources can legitimately close a blank.

The development sandbox cannot reach these hosts, so the probe runs on the same
GitHub runner that publishes the site and commits only under
``data/research/4c972a51/``.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests

UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/126.0.0.0 Safari/537.36')
HEADERS = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Surfaces are grouped by how a price could legitimately be used. A first-party
# bookmaker price is preferred; an aggregator is a cross-check unless it
# publishes its own two-sided price; a results/ratings source can only feed a
# research model, never a money line.
TARGETS = [
    # --- the exact endpoints the resolver already calls (production contract) --
    # These are probed with the same method and payload the collector uses, so a
    # green row here means the ladder's own source answered, not merely its host.
    ('POLYMARKET gamma events (tag counter-strike-2)', 'ladder', 'GET',
     'https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2&active=true&closed=false&limit=100&offset=0', None),
    ('POLYMARKET CLOB order book (token 0)', 'ladder', 'GET',
     'https://clob.polymarket.com/book?token_id=0', None),
    ('THUNDERPICK api/matches (POST gameIds [6])', 'ladder', 'POST',
     'https://thunderpick.io/api/matches', {'gameIds': [6]}),
    ('KALSHI trade-api events (series KXCS2GAME)', 'ladder', 'GET',
     'https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXCS2GAME&status=open&with_nested_markets=true&limit=200', None),
    ('BOVADA coupon (counter-strike-2)', 'ladder', 'GET',
     'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2?marketFilterId=def&preMatchOnly=true&lang=en', None),
    ('PINNACLE guest 12/matchups', 'ladder', 'GET',
     'https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups', None),
    ('PINNACLE guest 12/leagues', 'ladder', 'GET',
     'https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues', None),
    ('BO3 api/v1/matches (relay/upcoming)', 'ladder', 'GET',
     'https://api.bo3.gg/api/v1/matches?page[offset]=0&page[limit]=100&sort=start_date&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1&with=teams,tournament', None),
    ('HLTV ranking/teams (ranking rung)', 'ladder', 'GET',
     'https://www.hltv.org/ranking/teams', None),
    ('VALVE standings API (live/2026)', 'ladder', 'GET',
     'https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings/contents/live/2026', None),
    # --- candidate first-party esportsbooks ----------------------------------
    ('THUNDERPICK esports page', 'book', 'GET', 'https://thunderpick.io/esports/counter-strike', None),
    ('GG.BET next-to-go', 'book', 'GET',
     'https://gg.bet/en/next-to-go?hoursAhead=168&sportId=esports_counter_strike', None),
    ('BETWAY esports', 'book', 'GET', 'https://sports.betway.com/en/sports/grp/esports/counter-strike', None),
    ('MARATHONBET counter-strike', 'book', 'GET', 'https://www.marathonbet.com/en/betting/Esports/Counter-Strike/', None),
    ('1XBET counter-strike', 'book', 'GET', 'https://1xbet.com/en/line/esports/counter-strike/', None),
    ('FONBET counter-strike', 'book', 'GET', 'https://www.fonbet.ru/sports/esports/counter-strike/', None),
    ('WINLINE counter-strike', 'book', 'GET', 'https://winline.ru/stavki/sport/kibersport/counter-strike', None),
    ('BETBOOM counter-strike', 'book', 'GET', 'https://betboom.ru/sport/esports/counter-strike', None),
    ('RIVALRY counter-strike-2', 'book', 'GET', 'https://www.rivalry.com/esports/counter-strike-2', None),
    ('STAKE counter-strike', 'book', 'GET', 'https://stake.com/sports/esports/counter-strike', None),
    ('COOLBET esports', 'book', 'GET', 'https://www.coolbet.com/en/sports/esports/counter-strike', None),
    ('UNIBET counter_strike', 'book', 'GET', 'https://www.unibet.com/betting/sports/filter/counter_strike/all/matches', None),
    ('LEOVEGAS esports', 'book', 'GET', 'https://www.leovegas.com/en-row/sportsbook/esports/counter-strike', None),
    ('BETANO BR e-sports', 'book', 'GET', 'https://www.betano.bet.br/e-sports/counter-strike/', None),
    ('BETNACIONAL e-sports', 'book', 'GET', 'https://betnacional.bet.br/esportes/e-sports', None),
    ('ESPORTES DA SORTE e-sports', 'book', 'GET', 'https://esportesdasorte.bet.br/esportes/e-sports', None),
    ('KTO BR e-sports', 'book', 'GET', 'https://kto.bet.br/esportes/e-sports', None),
    ('BET365 esports', 'book', 'GET', 'https://www.bet365.com/#/AC/B151/C1/D50/E1/F2/', None),
    ('BETFAIR exchange esports', 'book', 'GET', 'https://www.betfair.com/exchange/plus/esports', None),
    ('SMARKETS esports', 'book', 'GET', 'https://smarkets.com/sport/esports', None),
    ('MATCHBOOK esports', 'book', 'GET', 'https://www.matchbook.com/events/esports', None),
    ('MIDNITE esports', 'book', 'GET', 'https://www.midnite.com/sports/esports', None),
    ('LUCKBOX', 'book', 'GET', 'https://luckbox.games/', None),
    ('CSGOEMPIRE', 'book', 'GET', 'https://csgoempire.com/', None),
    # --- aggregators / odds comparisons -------------------------------------
    ('ODDSPORTAL counter-strike', 'aggregator', 'GET', 'https://www.oddsportal.com/esports/counter-strike/', None),
    ('ODDSPEDIA counter-strike', 'aggregator', 'GET', 'https://oddspedia.com/counter-strike', None),
    ('BO3.gg match center', 'aggregator', 'GET', 'https://bo3.gg/matches', None),
    ('EGAMERSWORLD counter-strike', 'aggregator', 'GET', 'https://egamersworld.com/counter-strike/matches', None),
    ('ESCORENEWS csgo', 'aggregator', 'GET', 'https://escorenews.com/en/csgo', None),
    ('GOSUGAMERS counterstrike', 'aggregator', 'GET', 'https://www.gosugamers.net/counterstrike', None),
    ('ESCHARTS tournaments', 'aggregator', 'GET', 'https://escharts.com/tournaments/csgo', None),
    ('DLTV matches', 'aggregator', 'GET', 'https://dltv.org/matches', None),
    ('CSGO.COM matches', 'aggregator', 'GET', 'https://csgo.com/matches/', None),
    ('CYBERSPORT matches', 'aggregator', 'GET', 'https://www.cybersport.ru/matches', None),
    ('STRAFE', 'aggregator', 'GET', 'https://strafe.to/', None),
    ('VEGASINSIDER esports odds', 'aggregator', 'GET', 'https://www.vegasinsider.com/esports/odds/', None),
    ('ACTIONNETWORK esports odds', 'aggregator', 'GET', 'https://www.actionnetwork.com/esports/odds', None),
    ('BETTINGPROS esports odds', 'aggregator', 'GET', 'https://www.bettingpros.com/esports/odds/', None),
    # --- identity / ratings / results ---------------------------------------
    ('HLTV matches', 'ratings', 'GET', 'https://www.hltv.org/matches', None),
    ('HLTV result RSS', 'ratings', 'GET', 'https://www.hltv.org/rss/matches', None),
    ('LIQUIPEDIA api.php', 'ratings', 'GET',
     'https://liquipedia.net/counterstrike/api.php?action=query&meta=siteinfo&format=json', None),
    ('LIQUIPEDIA Matches page', 'ratings', 'GET', 'https://liquipedia.net/counterstrike/Matches', None),
]

# Search endpoints that take a free-text query, used once per unresolved fixture.
SEARCHES = [
    ('oddsportal-search', 'https://www.oddsportal.com/search/results/{q}/'),
    ('bo3-search', 'https://bo3.gg/search?q={q}'),
    ('liquipedia-search', 'https://liquipedia.net/counterstrike/index.php?search={q}&fulltext=1'),
    ('hltv-search', 'https://www.hltv.org/search?query={q}'),
]

ODDS_RE = re.compile(r'\b\d{1,2}\.\d{2}\b')
SPACE_RE = re.compile(r'\s+')


def _norm(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (value or '').lower())


def _excerpt(body: bytes, limit: int = 1200) -> str:
    text = body.decode('utf-8', errors='replace')
    text = re.sub(r'<script.*?</script>', ' ', text, flags=re.S | re.I)
    text = re.sub(r'<style.*?</style>', ' ', text, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    return SPACE_RE.sub(' ', text).strip()[:limit]


def fetch(session: requests.Session, method: str, url: str, timeout: int,
          payload=None) -> dict:
    started = time.time()
    out = {'url': url, 'method': method}
    try:
        response = session.request(method, url, timeout=timeout, allow_redirects=True,
                                   json=payload)
    except Exception as exc:  # noqa: BLE001 - every transport failure is evidence
        out.update({'status': None, 'error': f'{type(exc).__name__}: {exc}'[:240],
                    'elapsed_s': round(time.time() - started, 2)})
        return out
    body = response.content
    out.update({
        'status': response.status_code,
        'final_url': response.url,
        'bytes': len(body),
        'content_type': response.headers.get('content-type', '')[:120],
        'elapsed_s': round(time.time() - started, 2),
    })
    ctype = out['content_type'].lower()
    if 'json' in ctype and len(body) < 4_000_000:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            out['json_keys'] = list(payload)[:20]
        elif isinstance(payload, list):
            out['json_items'] = len(payload)
            if payload and isinstance(payload[0], dict):
                out['json_item_keys'] = list(payload[0])[:20]
    if len(body) < 6_000_000 and ('html' in ctype or 'json' in ctype or 'text' in ctype):
        out['excerpt'] = _excerpt(body)
        out['odds_like_tokens'] = len(ODDS_RE.findall(out['excerpt']))
    return out


def names_in(record: dict, team_names: list[str]) -> list[str]:
    haystack = _norm((record.get('excerpt') or '')[:200000])
    if not haystack:
        return []
    return [name for name in team_names if _norm(name) and _norm(name) in haystack]


def load_fixtures(data_dir: Path) -> tuple[list[dict], list[dict]]:
    latest = json.loads((data_dir / 'latest.json').read_text())
    orig_path = data_dir / 'origination.json'
    orig = json.loads(orig_path.read_text()) if orig_path.exists() else {}
    priced = {str(m.get('id')) for m in orig.get('matches') or [] if m.get('origination')}
    active, unresolved = [], []
    for match in latest.get('matches') or []:
        if match.get('availability') not in {'open', 'locked', 'unknown_lock'}:
            continue
        entry = {
            'id': str(match.get('id')),
            'teams': [t.get('name') for t in match.get('teams') or []],
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'tier': match.get('tier'),
            'featured_method': (match.get('analysis') or {}).get('method'),
            'match_page': match.get('source_url'),
        }
        active.append(entry)
        if entry['id'] not in priced:
            unresolved.append(entry)
    return active, unresolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('live'))
    parser.add_argument('--out', type=Path, default=Path('data/research/4c972a51'))
    parser.add_argument('--timeout', type=int, default=12)
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()

    active, unresolved = load_fixtures(args.data)
    teams = sorted({name for f in active for name in f['teams'] if name})
    unresolved_teams = sorted({name for f in unresolved for name in f['teams'] if name})

    session = requests.Session()
    session.headers.update(HEADERS)

    def surface(item):
        name, kind, method, url, payload = item
        record = fetch(session, method, url, args.timeout, payload)
        record.update({'name': name, 'kind': kind})
        record['teams_present'] = names_in(record, teams)
        record['unresolved_teams_present'] = names_in(record, unresolved_teams)
        return record

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(surface, TARGETS))

    searches = []
    for fixture in unresolved:
        query = quote_plus(' '.join(fixture['teams']))
        for name, template in SEARCHES:
            url = template.format(q=query)
            record = fetch(session, 'GET', url, args.timeout)
            record.update({'name': name, 'kind': 'search', 'fixture': fixture['id'],
                           'query': ' '.join(fixture['teams'])})
            record['teams_present'] = names_in(record, fixture['teams'])
            searches.append(record)

    report = {
        'session': 'arena-4c972a51',
        'observed_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'active_fixtures': len(active),
        'unresolved_fixtures': len(unresolved),
        'unresolved': unresolved,
        'surfaces': results,
        'searches': searches,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'source-probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')

    lines = ['# Source probe — runner egress', '', f"Observed `{report['observed_at']}` on the GitHub runner.",
             f"{len(results)} surfaces, {len(searches)} searches for {len(unresolved)} unresolved fixtures.", '',
             '| Surface | Kind | Status | Bytes | Unresolved team names present |',
             '| --- | --- | --- | --- | --- |']
    for record in results:
        lines.append(f"| {record['name']} | {record['kind']} | {record.get('status') or record.get('error', '')[:60]} | "
                     f"{record.get('bytes', '')} | {', '.join(record['unresolved_teams_present'][:4]) or '—'} |")
    (args.out / 'source-probe.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({
        'surfaces': len(results),
        'answered_200': sum(1 for r in results if r.get('status') == 200),
        'with_unresolved_teams': [r['name'] for r in results if r.get('unresolved_teams_present')],
        'unresolved_fixtures': len(unresolved),
    }, indent=2))


if __name__ == '__main__':
    main()
