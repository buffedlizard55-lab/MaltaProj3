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
    # --- first-party esportsbooks -------------------------------------------
    ('thunderpick', 'book', 'GET', 'https://thunderpick.io/api/matches'),
    ('pinnacle-guest', 'book', 'GET', 'https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups'),
    ('bovada', 'book', 'GET',
     'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike?marketFilterId=def&preMatchOnly=true&lang=en'),
    ('ggbet', 'book', 'GET', 'https://gg.bet/en/counter-strike'),
    ('ggbet-next', 'book', 'GET', 'https://gg.bet/en/next-to-go?hoursAhead=168&sportId=esports_counter_strike'),
    ('betway', 'book', 'GET', 'https://sports.betway.com/en/sports/grp/esports/counter-strike'),
    ('marathonbet', 'book', 'GET', 'https://www.marathonbet.com/en/betting/Esports/Counter-Strike/'),
    ('1xbet', 'book', 'GET', 'https://1xbet.com/en/line/esports/counter-strike/'),
    ('fonbet', 'book', 'GET', 'https://www.fonbet.ru/sports/esports/counter-strike/'),
    ('winline', 'book', 'GET', 'https://winline.ru/stavki/sport/kibersport/counter-strike'),
    ('betboom', 'book', 'GET', 'https://betboom.ru/sport/esports/counter-strike'),
    ('rivalry', 'book', 'GET', 'https://www.rivalry.com/esports/counter-strike-2'),
    ('stake', 'book', 'GET', 'https://stake.com/sports/esports/counter-strike'),
    ('coolbet', 'book', 'GET', 'https://www.coolbet.com/en/sports/esports/counter-strike'),
    ('unibet', 'book', 'GET', 'https://www.unibet.com/betting/sports/filter/counter_strike/all/matches'),
    ('leovegas', 'book', 'GET', 'https://www.leovegas.com/en-row/sportsbook/esports/counter-strike'),
    ('betano-br', 'book', 'GET', 'https://www.betano.bet.br/e-sports/counter-strike/'),
    ('betnacional', 'book', 'GET', 'https://betnacional.bet.br/esportes/e-sports'),
    ('esportes-da-sorte', 'book', 'GET', 'https://esportesdasorte.bet.br/esportes/e-sports'),
    ('kto-br', 'book', 'GET', 'https://kto.bet.br/esportes/e-sports'),
    ('bet365', 'book', 'GET', 'https://www.bet365.com/#/AC/B151/C1/D50/E1/F2/'),
    ('betfair-exchange', 'book', 'GET', 'https://www.betfair.com/exchange/plus/esports'),
    ('smarkets', 'book', 'GET', 'https://smarkets.com/sport/esports'),
    ('matchbook', 'book', 'GET', 'https://www.matchbook.com/events/esports'),
    ('midnite', 'book', 'GET', 'https://www.midnite.com/sports/esports'),
    ('luckbox', 'book', 'GET', 'https://luckbox.games/'),
    ('csgoempire', 'book', 'GET', 'https://csgoempire.com/'),
    ('kalshi', 'exchange', 'GET',
     'https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXCS2&limit=100&status=open'),
    ('polymarket-gamma', 'exchange', 'GET',
     'https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2&active=true&closed=false&limit=100'),
    # --- aggregators / odds comparisons -------------------------------------
    ('oddsportal', 'aggregator', 'GET', 'https://www.oddsportal.com/esports/counter-strike/'),
    ('oddspedia', 'aggregator', 'GET', 'https://oddspedia.com/counter-strike'),
    ('bo3', 'aggregator', 'GET', 'https://bo3.gg/matches'),
    ('egamersworld', 'aggregator', 'GET', 'https://egamersworld.com/counter-strike/matches'),
    ('escorenews', 'aggregator', 'GET', 'https://escorenews.com/en/csgo'),
    ('gosugamers', 'aggregator', 'GET', 'https://www.gosugamers.net/counterstrike'),
    ('escharts', 'aggregator', 'GET', 'https://escharts.com/tournaments/csgo'),
    ('dltv', 'aggregator', 'GET', 'https://dltv.org/matches'),
    ('csgo-com', 'aggregator', 'GET', 'https://csgo.com/matches/'),
    ('cybersport', 'aggregator', 'GET', 'https://www.cybersport.ru/matches'),
    ('strafe', 'aggregator', 'GET', 'https://strafe.to/'),
    ('vegasinsider', 'aggregator', 'GET', 'https://www.vegasinsider.com/esports/odds/'),
    ('actionnetwork', 'aggregator', 'GET', 'https://www.actionnetwork.com/esports/odds'),
    ('bettingpros', 'aggregator', 'GET', 'https://www.bettingpros.com/esports/odds/'),
    # --- identity / ratings / results ---------------------------------------
    ('hltv-matches', 'ratings', 'GET', 'https://www.hltv.org/matches'),
    ('hltv-ranking', 'ratings', 'GET', 'https://www.hltv.org/ranking/teams'),
    ('hltv-rss', 'ratings', 'GET', 'https://www.hltv.org/rss/matches'),
    ('liquipedia-api', 'ratings', 'GET',
     'https://liquipedia.net/counterstrike/api.php?action=query&meta=siteinfo&format=json'),
    ('liquipedia-matches', 'ratings', 'GET', 'https://liquipedia.net/counterstrike/Matches'),
    ('valve-standings', 'ratings', 'GET',
     'https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings/contents/live/2026'),
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


def fetch(session: requests.Session, method: str, url: str, timeout: int) -> dict:
    started = time.time()
    out = {'url': url, 'method': method}
    try:
        response = session.request(method, url, timeout=timeout, allow_redirects=True)
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
        name, kind, method, url = item
        record = fetch(session, method, url, args.timeout)
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
