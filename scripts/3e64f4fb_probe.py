"""Session arena-3e64f4fb live research probe: HLTV first, then esportsbooks.

The brief: every Hotspawn CS2 match needs a pick, including low-tier fixtures
with no featured market line. For any fixture that cannot be resolved the way
the featured picks are, research must try HLTV first, then esportsbooks and
esports betting lines - and whatever still cannot be resolved must be listed
separately with its limitations.

This module records only what those sources publish for exactly that
population (fixtures whose published basis is not a featured market line,
plus any live Hotspawn fixture missing from the published snapshot). The
authoring sandbox cannot reach any of these hosts, so this runs on a GitHub
Actions runner and commits dated evidence. It never writes a probability, a
pick or an alias: `scripts/originate.py` remains the only path to a published
number, and observed prices are recorded raw, exactly as printed.

    python -m scripts.3e64f4fb_probe                # live fetch + write dossier
    python -m scripts.3e64f4fb_probe --parse-raw    # re-parse archived bodies
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
OUT = Path('data/research/3e64f4fb/probe')
RAW = OUT / 'raw'

FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
LOBBY = 'https://play.hotspawn.com/lobby'
CS2_LOBBY = 'https://play.hotspawn.com/cs2-pickems'
HLTV_MATCHES = 'https://www.hltv.org/matches'
HLTV_RANKING = hltv_ranking.RANKING_URL
POLY_TAG = 'https://gamma-api.polymarket.com/events?tag_slug=cs2&closed=false&limit=100&order=startDate&ascending=true'
POLY_EVENT = 'https://gamma-api.polymarket.com/events/{event_id}'
THUNDERPICK = 'https://thunderpick.io/api/matches'
KALSHI_EVENTS = ('https://api.elections.kalshi.com/trade-api/v2/events'
                 '?series_ticker=KXCS2GAME&status=open&with_nested_markets=true&limit=200')
BOOK_PAGES = {
    'gg.bet': 'https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike',
    'pinnacle': 'https://www.pinnacle.com/en/esports-hub/cs2',
    'rivalry': 'https://www.rivalry.com/esports/counter-strike-betting',
    'stake': 'https://stake.com/sports/esports/counter-strike',
}
HEADERS = {
    'User-Agent': 'HotspawnCS2Origination/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)',
    'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8',
}
TIMEOUT = (15, 45)
RAW_CAP = 2_500_000

_observations: list[dict] = []


def now_iso() -> str:
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def _label_slug(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')[:80]


def record(label: str, url: str, response=None, *, error: str | None = None,
           body: bytes | None = None) -> dict:
    entry = {'label': label, 'url': url, 'observed_at': now_iso()}
    if error:
        entry['error'] = error[:300]
    if response is not None:
        entry['status'] = response.status_code
        entry['final_url'] = response.url
        body = response.content
    if body:
        entry['bytes'] = len(body)
        entry['sha256'] = hashlib.sha256(body).hexdigest()
        RAW.mkdir(parents=True, exist_ok=True)
        name = _label_slug(label) + ('.json' if body[:1] in b'{[' else '.html.gz')
        path = RAW / name
        if name.endswith('.gz'):
            path.write_bytes(gzip.compress(body[:RAW_CAP], mtime=0))
        else:
            path.write_bytes(body[:RAW_CAP])
        entry['raw_file'] = str(path)
    _observations.append(entry)
    return entry


def get(label: str, url: str, *, expect_json: bool = False):
    """One polite GET. Returns (observation, parsed-or-text-or-None)."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return record(label, url, error=f'{type(exc).__name__}: {exc}'), None
    entry = record(label, url, response)
    if response.status_code != 200:
        return entry, None
    if expect_json:
        try:
            return entry, response.json()
        except ValueError:
            return entry, None
    return entry, response.text


# --- pure parsers (unit-tested offline) ------------------------------------

def parse_hltv_listing(text: str) -> list[dict]:
    soup = BeautifulSoup(text or '', 'html.parser')
    rows, seen = [], set()
    for card in soup.select('div.match-wrapper[data-match-wrapper]'):
        teams = [n.get_text(' ', strip=True) for n in card.select('.match-teamname')]
        teams = [t for t in teams if t]
        stamp = card.select_one('[data-unix]')
        start = timestamp(stamp.get('data-unix')) if stamp else None
        if len(teams) != 2 or start is None:
            continue
        link = card.select_one('a.match-teams[href^="/matches/"], a.match-top[href^="/matches/"]')
        href = (link.get('href') or '').split('?')[0] if link is not None else None
        event = card.select_one('.match-event[data-event-headline]')
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
            'event': event.get('data-event-headline') if event is not None else None,
            'meta': meta.get_text(' ', strip=True) if meta is not None else None,
            'live': (card.get('live') or '').lower() == 'true',
        })
    return rows


def parse_hltv_match_page(text: str) -> dict:
    """Best-effort facts from one HLTV match page. Missing facts stay absent."""
    soup = BeautifulSoup(text or '', 'html.parser')
    page = soup.get_text(' ', strip=True)
    facts: dict = {}
    stamp = soup.select_one('.date[data-unix], [data-unix]')
    start = timestamp(stamp.get('data-unix')) if stamp else None
    if start is not None:
        facts['starts_at'] = start.isoformat().replace('+00:00', 'Z')
    fmt = re.search(r'Best of (\d)', page)
    if fmt:
        facts['format'] = f'BO{fmt.group(1)}'
    names = [n.get_text(' ', strip=True) for n in soup.select('.team-name, .standard-box.teams-box .teamName')]
    names = [n for n in dict.fromkeys(names) if n]
    if len(names) >= 2:
        facts['teams'] = names[:2]
    lineups = []
    for box in soup.select('.lineup, .lineups .box-headline, .playersBox'):
        players = [p.get_text(' ', strip=True) for p in box.select('.player-nick, .flagAlign .text, a[href^="/player/"]')]
        players = [p for p in dict.fromkeys(players) if p]
        if players:
            lineups.append(players[:8])
    if lineups:
        facts['lineups'] = lineups[:2]
    odds = []
    for provider_box in soup.select('.betting_provider, .odds-provider, [class*="odds"]'):
        text_box = provider_box.get_text(' ', strip=True)
        decimals = re.findall(r'\b(\d{1,2}\.\d{2})\b', text_box)
        if len(decimals) >= 2:
            odds.append({'raw_text': text_box[:240], 'decimal_candidates': decimals[:4]})
    if odds:
        facts['odds_widgets_raw'] = odds[:6]
    return facts


def parse_lobby_fixture_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r'fixture[-_/](\d{4,})', text or '')), key=int)


def thunderpick_candidates(payload, team_names: list[str]) -> list[dict]:
    """Raw paired series odds for an exact two-name match. No conversion.

    Contract mirrors production (`scripts/originate.py::thunderpick_rows`):
    POST /api/matches with ``{'gameIds': [6]}``, rows under
    ``data.upcoming``/``data.matches``, one *Match Winner* market with
    ``home``/``away`` sides carrying decimal odds.
    """
    wanted = {name_key(t) for t in team_names}
    rows = []
    items = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        inner = payload.get('data') or {}
        items = (inner.get('upcoming') or inner.get('matches') or []) if isinstance(inner, dict) else []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        teams = item.get('teams') or {}
        pair = []
        for side in ('home', 'away'):
            team = teams.get(side) if isinstance(teams, dict) else None
            pair.append((team or {}).get('name') or '' if isinstance(team, dict) else '')
        if len(pair) != 2 or {name_key(p) for p in pair} != wanted:
            continue
        odds_pair = None
        markets = []
        single = item.get('market')
        if isinstance(single, dict):
            markets.append(single)
        markets += [m for m in (item.get('markets') or []) if isinstance(m, dict)]
        for market in markets:
            if name_key(str(market.get('name') or '')) not in {
                    'match winner', 'match winner incl. overtime', 'match winner inc. overtime'}:
                continue
            sides = [market.get('home') or {}, market.get('away') or {}]
            values = [s.get('odds') for s in sides if isinstance(s, dict)]
            if len(values) == 2 and all(isinstance(v, (int, float)) and v > 1 for v in values):
                odds_pair = {'market': market.get('name'), 'odds_home_away': values}
                break
        rows.append({'match_id': item.get('id') or item.get('matchId'),
                     'teams_home_away': pair, 'start': item.get('startTime') or item.get('startsAt'),
                     'is_live': item.get('isLive'),
                     'tournament': (item.get('tournament') or {}).get('name')
                     if isinstance(item.get('tournament'), dict) else None,
                     'paired_odds': odds_pair})
    return rows


def polymarket_series_view(event: dict) -> dict | None:
    """The series-winner (moneyline) market of a gamma event, raw bid/ask."""
    if not isinstance(event, dict):
        return None
    markets = event.get('markets') or []
    series = None
    for market in markets:
        mtype = (market.get('sportsMarketType') or '').lower()
        title = (market.get('groupItemTitle') or '').lower()
        if mtype == 'moneyline' or title in ('match winner', 'series', ''):
            if 'map' not in (market.get('question') or '').lower() or mtype == 'moneyline':
                series = market
                if mtype == 'moneyline':
                    break
    if series is None:
        return None
    try:
        outcomes = json.loads(series.get('outcomes') or '[]')
    except ValueError:
        outcomes = []
    return {
        'event_id': str(event.get('id')), 'slug': event.get('slug'),
        'title': event.get('title'), 'event_start': series.get('eventStartTime') or series.get('gameStartTime'),
        'outcomes': outcomes, 'best_bid': series.get('bestBid'), 'best_ask': series.get('bestAsk'),
        'closed': series.get('closed'), 'accepting_orders': series.get('acceptingOrders'),
        'url': f"https://polymarket.com/event/{event.get('slug')}" if event.get('slug') else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--parse-raw', action='store_true',
                        help='re-run the pure parsers over archived bodies (offline proof)')
    parser.add_argument('--tag', default='probe',
                        help='output basename; a second sweep must not overwrite the first')
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)

    snapshot = json.loads(Path('snapshot.json').read_text())
    origination = json.loads(Path('origination.json').read_text())
    org_by_id = {str(r['id']): r for r in origination.get('matches') or []}
    published_active = {str(m['id']) for m in snapshot.get('matches') or []
                        if m.get('availability') != 'past'}

    if args.parse_raw:
        replay = {}
        listing = RAW / 'hltv-matches.html.gz'
        if listing.exists():
            replay['hltv_listing_rows'] = len(parse_hltv_listing(
                gzip.decompress(listing.read_bytes()).decode('utf-8', 'replace')))
        tp = RAW / 'thunderpick-matches.json'
        if tp.exists():
            payload = json.loads(tp.read_text())
            replay['thunderpick_payload_items'] = len(payload) if isinstance(payload, list) else None
        (OUT / 'replay.json').write_text(json.dumps(replay, indent=1) + '\n')
        print(json.dumps(replay))
        return 0

    observed = datetime.now(UTC)
    dossier: dict = {
        'session': 'arena-3e64f4fb',
        'observed_at': now_iso(),
        'policy': 'Evidence only. Observed prices recorded raw; no probability, pick or alias '
                  'is produced here. Origination remains the only path to a published number.',
        'published': {
            'snapshot_generated_at': snapshot.get('generated_at'),
            'origination_generated_at': origination.get('generated_at'),
            'active_ids': sorted(published_active, key=int),
        },
    }

    # 1. Live Hotspawn inventory -------------------------------------------------
    _, fixtures_payload = get('hotspawn fixtures api', FIXTURES_API, expect_json=True)
    records = []
    if isinstance(fixtures_payload, dict):
        records = fixtures_payload.get('data') or fixtures_payload.get('fixtures') or []
    elif isinstance(fixtures_payload, list):
        records = fixtures_payload
    live_open = []
    for item in records if isinstance(records, list) else []:
        if not isinstance(item, dict):
            continue
        starts = None
        for key in ('scheduled_start_time', 'starts_at', 'start_time', 'startDate'):
            if item.get(key):
                starts = timestamp(item[key])
                break
        fid = str(item.get('id') or item.get('fixture_id') or '')
        # The fixtures API publishes flat participant fields; the picked
        # percentages are community votes and are deliberately NOT read.
        teams = [item.get('participants0_name'), item.get('participants1_name')]
        if not all(teams):
            teams = []
            for side in ('home_team', 'away_team'):
                team = item.get(side)
                if isinstance(team, dict):
                    teams.append(team.get('name'))
            if not teams and isinstance(item.get('teams'), list):
                teams = [(t or {}).get('name') for t in item['teams']]
        competition = item.get('competition_name')
        if not competition and isinstance(item.get('competition'), dict):
            competition = item['competition'].get('name')
        if fid and starts and starts > observed:
            live_open.append({'id': fid, 'teams': [t for t in teams if t],
                              'starts_at': starts.isoformat().replace('+00:00', 'Z'),
                              'competition': competition})
    _, lobby_html = get('hotspawn lobby', LOBBY)
    _, cs2_html = get('hotspawn cs2 lobby', CS2_LOBBY + f'?cb={int(observed.timestamp())}')
    lobby_ids = sorted(set(parse_lobby_fixture_ids(lobby_html or '')
                           + parse_lobby_fixture_ids(cs2_html or '')), key=lambda x: int(x) if x.isdigit() else 0)
    live_ids = {f['id'] for f in live_open}
    dossier['inventory'] = {
        'api_records': len(records) if isinstance(records, list) else None,
        'api_open_fixtures': len(live_open),
        'lobby_fixture_ids': lobby_ids,
        'live_open_missing_from_published': sorted(live_ids - published_active, key=int),
        'published_no_longer_live_open': sorted(published_active - live_ids, key=int),
        'live_open': live_open,
    }

    # 2. Targets: not resolved the featured-market way, plus coverage gaps --------
    targets = []
    for fid, row in org_by_id.items():
        if row.get('featured_method') != 'market':
            targets.append({
                'id': fid, 'teams': [t['name'] for t in row.get('teams') or []],
                'starts_at': row.get('starts_at'), 'competition': row.get('competition'),
                'published_featured_method': row.get('featured_method'),
                'published_complete_method': (row.get('origination') or {}).get('method'),
                'published_pick_index': row.get('pick_index'),
            })
    for f in live_open:
        if f['id'] not in org_by_id and f['id'] not in {t['id'] for t in targets}:
            targets.append({'id': f['id'], 'teams': f['teams'], 'starts_at': f['starts_at'],
                            'competition': f['competition'],
                            'published_featured_method': None,
                            'published_complete_method': None,
                            'published_pick_index': None, 'coverage_gap': True})

    # 3. HLTV first ----------------------------------------------------------------
    _, hltv_html = get('hltv matches', HLTV_MATCHES)
    hltv_rows = parse_hltv_listing(hltv_html or '')
    _, ranking_html = get('hltv ranking', HLTV_RANKING)
    ranking_rows = hltv_ranking.parse_ranking_page(ranking_html or '') if ranking_html else []
    dossier['hltv'] = {'listing_rows': len(hltv_rows), 'ranking_rows': len(ranking_rows)}

    # 4. Exchanges/books second ------------------------------------------------------
    _, poly_tag = get('polymarket cs2 tag', POLY_TAG, expect_json=True)
    poly_events = poly_tag if isinstance(poly_tag, list) else (poly_tag or {}).get('events') or []
    try:
        tp_response = requests.post(THUNDERPICK, headers=HEADERS, json={'gameIds': [6]},
                                    timeout=TIMEOUT)
        record('thunderpick matches', THUNDERPICK, tp_response)
        tp_payload = tp_response.json() if tp_response.status_code == 200 else None
    except (requests.RequestException, ValueError) as exc:
        record('thunderpick matches', THUNDERPICK, error=f'{type(exc).__name__}: {exc}')
        tp_payload = None
    _, kalshi_payload = get('kalshi esports events', KALSHI_EVENTS, expect_json=True)
    kalshi_events = (kalshi_payload or {}).get('events') if isinstance(kalshi_payload, dict) else None
    book_status = {}
    for name, url in BOOK_PAGES.items():
        entry, _ = get(f'book page {name}', url)
        book_status[name] = {'url': url, 'status': entry.get('status'),
                             'error': entry.get('error'), 'final_url': entry.get('final_url')}
    dossier['book_pages'] = book_status

    for target in targets:
        names = target['teams']
        keys = {name_key(n) for n in names if n}
        exact = [r for r in hltv_rows if {name_key(t) for t in r['teams']} == keys and len(keys) == 2]
        shared = [r for r in hltv_rows if r not in exact
                  and {name_key(t) for t in r['teams']} & keys]
        target['hltv_exact'] = exact
        target['hltv_shares_one_name'] = shared[:6]
        target['hltv_match_page'] = None
        if exact and exact[0].get('url'):
            _, page = get(f"hltv match {target['id']}", exact[0]['url'])
            if page:
                target['hltv_match_page'] = parse_hltv_match_page(page)
        target['hltv_ranking'] = {}
        for name in names:
            hit = next(((index, r) for index, r in enumerate(ranking_rows)
                        if name_key(str(r.get('team', ''))) == name_key(name)), None)
            target['hltv_ranking'][name] = (({'rank': hit[0] + 1, 'points': hit[1].get('points'),
                                              'team_url': hit[1].get('team_url')})
                                            if hit else None)
        poly_hits = []
        for event in poly_events if isinstance(poly_events, list) else []:
            title = name_key(str((event or {}).get('title') or ''))
            if keys and all(any(k in title for k in [name_key(n)]) for n in names if n):
                view = polymarket_series_view(event)
                if view:
                    poly_hits.append(view)
        row = org_by_id.get(target['id']) or {}
        for quote in ((row.get('origination') or {}).get('quotes') or []):
            if not str(quote.get('provider', '')).startswith('Polymarket'):
                continue
            event_id = quote.get('event_id')
            if event_id and str(event_id) not in {h['event_id'] for h in poly_hits}:
                _, event = get(f"polymarket event {target['id']}", POLY_EVENT.format(event_id=event_id),
                               expect_json=True)
                view = polymarket_series_view(event) if event else None
                if view:
                    poly_hits.append(view)
        target['polymarket_observed'] = poly_hits
        target['thunderpick_observed'] = thunderpick_candidates(tp_payload, names) if names else []
        kalshi_hits = []
        for event in kalshi_events or []:
            title = name_key(str((event or {}).get('title') or ''))
            if names and all(name_key(n) in title for n in names if n):
                markets = [{'ticker': m.get('ticker'), 'yes_sub_title': m.get('yes_sub_title'),
                            'yes_bid': m.get('yes_bid'), 'yes_ask': m.get('yes_ask'),
                            'no_bid': m.get('no_bid'), 'no_ask': m.get('no_ask')}
                           for m in (event.get('markets') or [])]
                kalshi_hits.append({'event_ticker': event.get('event_ticker'),
                                    'title': event.get('title'), 'markets': markets})
        target['kalshi_observed'] = kalshi_hits

    dossier['targets'] = targets
    dossier['observations'] = _observations
    (OUT / f'{args.tag}.json').write_text(json.dumps(dossier, indent=1) + '\n')
    (OUT / f'{args.tag}.md').write_text(render_markdown(dossier))
    print(f"targets={len(targets)} live_open={len(live_open)} "
          f"missing_from_published={dossier['inventory']['live_open_missing_from_published']}")
    return 0


def render_markdown(d: dict) -> str:
    lines = ['# arena-3e64f4fb live research — HLTV first, then esportsbooks', '',
             f"Observed `{d['observed_at']}` on a GitHub runner. **Evidence only:** raw observed "
             'prices, no derived probability or pick.', '',
             f"- Published snapshot `{d['published']['snapshot_generated_at']}`, "
             f"origination `{d['published']['origination_generated_at']}`",
             f"- Hotspawn API open fixtures: **{d['inventory']['api_open_fixtures']}**; "
             f"lobby fixture ids parsed: {len(d['inventory']['lobby_fixture_ids'])}",
             f"- Live-open fixtures missing from the published board: "
             f"**{d['inventory']['live_open_missing_from_published'] or 'none'}**",
             f"- Published fixtures no longer live-open (started/rotated): "
             f"{d['inventory']['published_no_longer_live_open'] or 'none'}",
             f"- HLTV listing rows parsed: {d['hltv']['listing_rows']}; "
             f"ranking rows: {d['hltv']['ranking_rows']}", '']
    for t in d['targets']:
        lines += [f"## {t['id']} — {' vs '.join(t['teams'])} ({t.get('competition')}, {t.get('starts_at')})",
                  f"- Published basis: featured={t.get('published_featured_method')}, "
                  f"complete={t.get('published_complete_method')}, pick_index={t.get('published_pick_index')}"
                  + (' **[coverage gap: no published row]**' if t.get('coverage_gap') else ''),
                  '- HLTV exact: ' + ('; '.join(f"{r['url']} @ {r['starts_at']} ({r.get('event')})"
                                                 for r in t['hltv_exact']) or 'not found on /matches'),
                  f"- HLTV match page: `{json.dumps(t.get('hltv_match_page'))[:400]}`",
                  f"- HLTV ranking: {json.dumps(t['hltv_ranking'])}",
                  '- Polymarket observed: ' + ('; '.join(
                      f"{h['url']} bid {h['best_bid']} / ask {h['best_ask']} ({h['outcomes']})"
                      for h in t['polymarket_observed']) or 'none found'),
                  '- Thunderpick observed: ' + ('; '.join(
                      f"{h['teams_home_away']} odds {((h.get('paired_odds') or {}).get('odds_home_away'))} "
                      f"start {h.get('start')}"
                      for h in t['thunderpick_observed']) or 'none found'),
                  '- Kalshi observed: ' + ('; '.join(h['title'] or h['event_ticker'] or ''
                                                     for h in t['kalshi_observed']) or 'none found'),
                  '']
    lines += ['## Book page reachability (status only)', '']
    for name, book in d['book_pages'].items():
        lines.append(f"- {name}: {book['status'] or book['error']} — {book['url']}")
    lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    raise SystemExit(main())
