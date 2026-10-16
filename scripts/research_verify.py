"""Independent first-party research probe for the verification/audit session.

Purpose
-------
The brief's REPO WORK and VERIFICATION pillars require every published value to be
checked against an *official* source, with a link a human can open.  This sandbox has
no general egress, so this module runs on a GitHub Actions runner and records what the
runner actually read, when it read it, and from which URL.

It is strictly read-only and self-contained:

* it never writes outside ``data/research/ba7164a0/``;
* it never imports a module another session is actively editing, so a concurrent
  change to ``scripts/collect.py`` or ``scripts/originate.py`` cannot break it;
* it never computes, repairs or invents a probability.  It only records observations.

Two things are captured:

1. ``observations.json`` - compact, quotable facts (moneyline bid/ask, HLTV fixture
   times, Valve rating points, the deployed production counts) with a source URL and
   an observation timestamp on every entry.
2. ``raw/<label>.html|json`` - the original response bodies, so any extraction can be
   replayed by a reviewer without trusting this parser.

Usage::

    python -m scripts.research_verify            # write into data/research/ba7164a0
    python -m scripts.research_verify --out DIR  # elsewhere (tests)
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

UTC = timezone.utc
OUT_DEFAULT = Path('data/research/ba7164a0')

# --- official first-party endpoints ---------------------------------------
GAMMA_EVENTS = 'https://gamma-api.polymarket.com/events'
CLOB_BOOK = 'https://clob.polymarket.com/book'
POLY_INDEX = 'https://polymarket.com/esports/cs2'
POLY_TAG_URL = POLY_INDEX
HLTV_EVENT_MATCHES = 'https://www.hltv.org/events/8932/matches'
HLTV_EVENT_RESULTS = 'https://www.hltv.org/results?event=8932'
HLTV_EVENT_PAGE = 'https://www.hltv.org/events/8932/thunderpick-world-championship-2026'
HLTV_MATCHES = 'https://www.hltv.org/matches'
HLTV_RANKING = 'https://www.hltv.org/ranking/teams'
TWC_MATCH_IDS = [2399412, 2399413, 2399414, 2399415]
TWC_ANALYTICS_IDS = [2399412, 2399413]
HLTV_TEAM_PAGES = {
    'Aurora': 'https://www.hltv.org/team/11861/aurora',
    '9z': 'https://www.hltv.org/team/9996/9z',
}
HOTSPAWN_FIXTURES = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?'
                     + urlencode({'sport_alias': 'cs2', 'status': 'scheduled', 'tenantId': 1}))
HOTSPAWN_LOBBY = 'https://play.hotspawn.com/lobby'
VALVE_API = 'https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings'
KALSHI_EVENTS = 'https://api.elections.kalshi.com/trade-api/v2/events'
BOVADA_API = ('https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2?'
              + urlencode({'marketFilterId': 'def', 'preMatchOnly': 'true', 'lang': 'en'}))
THUNDERPICK_API = 'https://thunderpick.io/api/matches'
# The deployed production snapshot: what a reader actually sees right now.
PAGES_BASE = 'https://buffedlizard55-lab.github.io/MaltaProj3'

# The project's own declared identity, identical to the one scripts/sources.py uses.
# A spoofed browser User-Agent is *more* likely to be rejected: HLTV's edge returned
# HTTP 403 to a Chrome UA on the first probe run (2026-10-16T07:41Z) while the
# production pipeline's `hltv-matches` request with this UA returned HTTP 200 in the
# deployed snapshot of the same hour. No challenge is bypassed either way.
UA = 'HotspawnCS2Coverage/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'
ACCEPT = 'application/json,text/html;q=0.9'


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


class Probe:
    """Fetch + archive. Every result keeps its URL, status and observation time."""

    def __init__(self, out: Path):
        self.out = out
        self.raw = out / 'raw'
        self.raw.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': UA, 'Accept': ACCEPT})
        self.log: list[dict] = []

    def _record(self, label, url, status, observed_at, note='', evidence='', kind=''):
        entry = {'label': label, 'url': url, 'status': status, 'observed_at': observed_at, 'kind': kind}
        if note:
            entry['note'] = note
        if evidence:
            entry['evidence'] = evidence
        self.log.append(entry)
        print(f'[{status}] {label} -> {url}' + (f' ({note})' if note else ''), flush=True)

    def get(self, label: str, url: str, *, method='GET', payload=None, headers=None, save=True, timeout=45):
        observed = now_iso()
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers or {}, timeout=timeout)
            else:
                response = self.session.request(method, url, json=payload, headers=headers or {}, timeout=timeout)
        except Exception as exc:  # a blocked source is a finding, not a crash
            self._record(label, url, 'error', observed, note=f'{type(exc).__name__}: {exc}')
            return None, None
        evidence = ''
        if save:
            suffix = '.json' if 'json' in response.headers.get('content-type', '') else '.html'
            name = f'{label}{suffix}'
            path = self.raw / name
            body = response.content
            if len(body) > 400_000:  # keep the repository light; gzip anything large
                path = path.with_suffix(suffix + '.gz')
                body = gzip.compress(body)
            path.write_bytes(body)
            evidence = str(path)
        if response.status_code != 200:
            self._record(label, url, f'http-{response.status_code}', observed, evidence=evidence)
            return None, evidence
        try:
            data = response.json() if 'json' in response.headers.get('content-type', '') else response.text
        except Exception as exc:
            self._record(label, url, 'parse-error', observed, note=str(exc), evidence=evidence)
            return None, evidence
        self._record(label, url, 'ok', observed, evidence=evidence,
                     kind='json' if not isinstance(data, str) else 'html')
        return data, evidence


# ---------------------------------------------------------------------------
# Polymarket: independent moneylines (never Hotspawn popularity)
# ---------------------------------------------------------------------------

def moneyline_markets(event: dict) -> list[dict]:
    """Series moneyline markets only, matching the published methodology's contract.

    Map/handicap/total/outright markets are excluded, so nothing here can be a
    disguised single-map price.
    """
    found = []
    if not isinstance(event, dict) or not str(event.get('slug', '')).startswith('cs2-'):
        return found
    tags = [t.get('slug') for t in event.get('tags', []) if isinstance(t, dict)]
    if 'cs2' not in tags:
        return found
    for market in event.get('markets', []) or []:
        scope = market.get('sportsMarketType') or (market.get('sports') or {}).get('sports_market_type')
        question = market.get('question') or ''
        outcomes = market.get('outcomes')
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except Exception:
                outcomes = None
        if scope != 'moneyline' or not isinstance(outcomes, list) or len(outcomes) != 2:
            continue
        if re.search(r'\b(map\s*\d|game\s*\d|handicap|spread|total|outright)\b', question, re.I):
            continue
        prices = market.get('outcomePrices')
        if isinstance(prices, str):
            try:
                prices = json.loads(prices)
            except Exception:
                prices = None
        tokens = market.get('clobTokenIds')
        if isinstance(tokens, str):
            try:
                tokens = json.loads(tokens)
            except Exception:
                tokens = None
        found.append({
            'event_id': str(event.get('id')),
            'event_slug': event.get('slug'),
            'event_title': event.get('title'),
            'market_id': str(market.get('id')),
            'question': question,
            'outcomes': outcomes,
            'game_start_time': market.get('gameStartTime') or event.get('startTime'),
            'event_start_time': market.get('eventStartTime'),
            'end_date': market.get('endDate'),
            'best_bid': market.get('bestBid'),
            'best_ask': market.get('bestAsk'),
            'spread': market.get('spread'),
            'last_trade_price': market.get('lastTradePrice'),
            'outcome_prices': prices,
            'accepting_orders': market.get('acceptingOrders'),
            'active': market.get('active'),
            'closed': market.get('closed'),
            'volume': market.get('volumeNum'),
            'liquidity': market.get('liquidityNum'),
            'condition_id': market.get('conditionId'),
            'clob_token_ids': tokens,
            'updated_at': market.get('updatedAt'),
            'event_updated_at': event.get('updatedAt'),
            'source_url': f'https://polymarket.com/event/{event.get("slug")}',
        })
    return found


FLIGHT_PUSH = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')


def polymarket_directory_games(html: str) -> list:
    """Decode the public Next.js flight JSON of Polymarket's CS2 directory.

    The *displayed* directory shows rounded percentages and crowd numbers. Those are
    never used here: only the game identity (id, slug, team names, start time) is read,
    and every price is then taken from the event's own moneyline market and CLOB books.
    """
    games: dict[str, dict] = {}

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get('sportSlug') == 'cs2' and 'homeTokenId' in obj and 'awayTokenId' in obj:
                key = obj.get('slug') or obj.get('id')
                if key:
                    games[str(key)] = obj
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    for part in FLIGHT_PUSH.findall(html):
        try:
            text = json.loads(part)
        except ValueError:
            continue
        for line in text.split('\n'):
            colon = line.find(':')
            if colon < 0:
                continue
            try:
                walk(json.JSONDecoder().raw_decode(line[colon + 1:])[0])
            except (ValueError, TypeError):
                continue
    return list(games.values())


def collect_polymarket(probe: Probe) -> dict:
    # Route 1: the public CS2 directory. The `tag_slug=cs2` event query alone returns
    # only long-dated/outright markets, not per-match moneylines, so the directory is
    # decoded first and each game's own event is then read from Gamma.
    directory: list[dict] = []
    html, ev = probe.get('polymarket-directory', POLY_INDEX)
    if isinstance(html, str):
        directory = polymarket_directory_games(html)
        if not directory:
            probe._record('polymarket-directory-games', POLY_INDEX, 'schema-missing', now_iso(),
                          note='No cs2 game objects with home/away token ids; discovery completeness unverified.')
    seen: dict[str, dict] = {}
    pages = 0
    limitations = []
    for offset in range(0, 2000, 100):
        url = GAMMA_EVENTS + '?' + urlencode({'tag_slug': 'cs2', 'active': 'true', 'closed': 'false',
                                              'limit': 100, 'offset': offset})
        events, evidence = probe.get(f'gamma-cs2-{offset}', url)
        if not isinstance(events, list):
            limitations.append(f'Gamma page offset={offset} did not return a list; pagination completeness unverified.')
            break
        pages += 1
        ids = [str(e.get('id')) for e in events if isinstance(e, dict) and e.get('id')]
        if len(set(ids)) != len(ids):
            limitations.append(f'Repeated Gamma event IDs at offset={offset}.')
        if not ids:
            break
        for event in events:
            for market in moneyline_markets(event):
                seen.setdefault(market['event_id'] + '/' + market['market_id'], market)
        if len(events) < 100:
            break
        time.sleep(0.4)
    if pages * 100 >= 2000:
        limitations.append('Reached the bounded 2,000-event Gamma window; discovery completeness is not proven.')
    # Route 2: every game the directory names, fetched individually by its own event id.
    directory_games = []
    for game in directory:
        gid = game.get('id')
        if not gid:
            continue
        directory_games.append({'id': str(gid), 'slug': game.get('slug'),
                                'home': game.get('homeName'), 'away': game.get('awayName'),
                                'start_time': game.get('startTime')})
        if str(gid) in {r['event_id'] for r in seen.values()}:
            continue
        event, eev = probe.get(f'gamma-event-{gid}', GAMMA_EVENTS + f'/{gid}')
        if isinstance(event, dict):
            for market in moneyline_markets(event):
                seen.setdefault(market['event_id'] + '/' + market['market_id'], market)
        time.sleep(0.2)
    rows = list(seen.values())
    # Order books for every moneyline token: the published midpoint method needs both sides.
    books = {}
    for row in rows:
        for token in (row.get('clob_token_ids') or [])[:2]:
            if not token:
                continue
            book, _ = probe.get(f'clob-book-{str(token)[:14]}', CLOB_BOOK + '?' + urlencode({'token_id': token}))
            if isinstance(book, dict):
                books[str(token)] = {
                    'bids': book.get('bids'),
                    'asks': book.get('asks'),
                    'market': book.get('market'),
                    'asset_id': book.get('asset_id'),
                    'hash': book.get('hash'),
                    'timestamp': book.get('timestamp'),
                }
            time.sleep(0.15)
    return {'moneylines': rows, 'books': books, 'pages': pages, 'limitations': limitations,
            'directory_games': directory_games, 'directory_evidence': ev,
            'observed_at': now_iso(), 'source_url': POLY_INDEX, 'api': GAMMA_EVENTS}


# ---------------------------------------------------------------------------
# HLTV: fixtures, results, countdowns, lineups, official odds page
# ---------------------------------------------------------------------------

HLTV_TIME_CELL = re.compile(r'(\d{1,2}:\d{2})')


def _text(el) -> str:
    return re.sub(r'\s+', ' ', el.get_text(' ', strip=True)) if el is not None else ''


def parse_hltv_schedule(html: str) -> dict:
    """Parse the event Matches page into date-grouped fixtures exactly as displayed."""
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return {'limitation': 'beautifulsoup4 unavailable'}
    soup = BeautifulSoup(html, 'html.parser')
    days, current = [], None
    # The page groups fixtures under a plain-text day heading; walk the DOM in order.
    body = soup.find('body')
    if body is None:
        return {'limitation': 'no body element'}
    for el in body.descendants:
        if getattr(el, 'name', None) is None:
            continue
        classes = ' '.join(el.get('class') or [])
        if el.name in ('h1', 'h2', 'h3') or 'date' in classes or 'day' in classes:
            text = _text(el)
            m = re.search(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*-\s*(\d{4}-\d{2}-\d{2})', text)
            if m:
                current = {'displayed_day': text.strip(), 'date': m.group(2), 'weekday': m.group(1), 'fixtures': []}
                days.append(current)
                continue
        href = el.get('href') if hasattr(el, 'get') else None
        if isinstance(href, str) and '/matches/' in href and current is not None:
            mid = re.search(r'/matches/(\d+)/', href)
            if not mid:
                continue
            text = _text(el)
            row = {'match_id': int(mid.group(1)),
                   'url': href if href.startswith('http') else 'https://www.hltv.org' + href,
                   'displayed': text[:220]}
            tm = HLTV_TIME_CELL.search(text)
            if tm:
                row['displayed_time'] = tm.group(1)
            bm = re.search(r'\bbo(\d)\b', text, re.I)
            if bm:
                row['best_of'] = int(bm.group(1))
            if row not in current['fixtures']:
                current['fixtures'].append(row)
    return {'days': days}


def parse_hltv_results(html: str) -> dict:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return {'limitation': 'beautifulsoup4 unavailable'}
    soup = BeautifulSoup(html, 'html.parser')
    out, current = [], None
    for el in soup.find_all(True):
        text = _text(el)
        dm = re.fullmatch(r'(January|February|March|April|May|June|July|August|September|October|November|December)'
                          r'\s+\d{1,2}(st|nd|rd|th)?\s+\d{4}', text.strip())
        if dm:
            current = {'displayed_day': text.strip(), 'results': []}
            out.append(current)
            continue
        href = el.get('href') or ''
        if isinstance(href, str) and '/matches/' in href and current is not None:
            mid = re.search(r'/matches/(\d+)/', href)
            sm = re.search(r'(\d+)\s*-\s*(\d+)', text)
            if mid and sm:
                row = {'match_id': int(mid.group(1)),
                       'url': href if href.startswith('http') else 'https://www.hltv.org' + href,
                       'score': [int(sm.group(1)), int(sm.group(2))],
                       'displayed': text[:200]}
                bm = re.search(r'\bbo(\d)\b', text, re.I)
                if bm:
                    row['best_of'] = int(bm.group(1))
                if row not in current['results']:
                    current['results'].append(row)
    return {'days': out}


def parse_hltv_match_page(html: str) -> dict:
    """Read only what the match page states. Anything absent stays absent."""
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return {'limitation': 'beautifulsoup4 unavailable'}
    soup = BeautifulSoup(html, 'html.parser')
    info: dict = {'title': _text(soup.find('title'))}
    canonical = soup.find('link', rel='canonical')
    if canonical and canonical.get('href'):
        info['canonical_url'] = canonical['href']
    # Countdown: HLTV stores the absolute start in a data attribute (unix milliseconds).
    # This is the only timezone-independent start time on the page.
    for el in soup.find_all(attrs={'data-unix': True}):
        try:
            info['data_unix'] = int(el.get('data-unix'))
            info['start_utc_from_countdown'] = datetime.fromtimestamp(info['data_unix'] / 1000, UTC).isoformat()
            break
        except (TypeError, ValueError, OSError, OverflowError):
            continue
    for el in soup.find_all(attrs={'data-time-format': True}):
        info.setdefault('time_format', el.get('data-time-format'))
        break
    text = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))
    m = re.search(r'Best of (\d+)', text)
    if m:
        info['best_of'] = int(m.group(1))
    if re.search(r'\bLAN\b', text):
        info['setting'] = 'LAN'
    m = re.search(r'\*\s*([A-Za-z0-9 ]{3,60}match)', text)
    if m:
        info['slot'] = m.group(1).strip()
    m = re.search(r'(\d{1,2}:\d{2})\s*(\d{1,2}(?:st|nd|rd|th)? of \w+ \d{4})', text)
    if m:
        info['displayed_time'] = m.group(1)
        info['displayed_date'] = m.group(2)
    # Lineups: HLTV marks each roster block with a "lineup" class and players as links.
    lineups = []
    for block in soup.find_all(class_=re.compile(r'lineup')):
        names = []
        for link in block.find_all('a'):
            href = link.get('href') or ''
            if '/player/' not in href:
                continue
            nick = _text(link)
            if nick and nick not in names:
                names.append(nick)
        if names:
            lineups.append(names[:6])
    if lineups:
        info['lineup_blocks'] = lineups
    return info


def parse_hltv_odds(html: str) -> dict:
    """HLTV's own odds/prediction page. Bookmaker decimal odds only where shown."""
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return {'limitation': 'beautifulsoup4 unavailable'}
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text('\n', strip=True)
    out: dict = {'odds_rows': [], 'insights': [], 'rankings': {}}
    for row in soup.find_all('tr'):
        cells = [_text(c) for c in row.find_all(['td', 'th'])]
        if len(cells) >= 2 and any(re.fullmatch(r'\d+\.\d{2}', c) for c in cells):
            out['odds_rows'].append(cells[:6])
    for m in re.finditer(r'(better ranked|worse ranked)\s*\(#(\d+)\)', text):
        out['rankings'][m.group(1)] = int(m.group(2))
    for m in re.finditer(r'([A-Za-z0-9\. ]{2,40}) is (better|worse) ranked \(#(\d+)\)', text):
        out['rankings'][m.group(1).strip()] = {'rank': int(m.group(3)), 'side': m.group(2)}
    for m in re.finditer(r'(?:This speaks (?:in favor of|against) )?([A-Za-z0-9\.\' ]{2,30})'
                         r'(?:has won \d+ out of the last \d+ matches'
                         r'|is the bookmaker favorite with the best odds'
                         r'|played \d+ matches against [A-Za-z0-9 ]+ in the past 30 days, and (?:won|lost) the latest'
                         r'|has better form ranking)', text):
        out['insights'].append(m.group(0).strip()[:200])
    # Series-result distribution (HLTV "Handicap data, past 3 months").
    for m in re.finditer(r'(2 - 0 wins|2 - 1 wins|0 - 2 losses|1 - 2 losses|Overtimes)\s*\|\s*([\d\.]+)%', text):
        out['odds_rows'].append([m.group(1), m.group(2) + '%'])
    return out


def collect_hltv(probe: Probe) -> dict:
    result: dict = {'fixtures': {}, 'results': {}, 'match_pages': {}, 'analytics': {}, 'teams': {}, 'limitations': []}
    html, ev = probe.get('hltv-event-matches', HLTV_EVENT_MATCHES)
    if isinstance(html, str):
        parsed = parse_hltv_schedule(html)
        parsed['source_url'] = HLTV_EVENT_MATCHES
        parsed['evidence'] = ev
        result['schedule'] = parsed
    else:
        result['limitations'].append('HLTV event Matches page was not readable; fixture times stay unverified.')
    html, ev = probe.get('hltv-event-results', HLTV_EVENT_RESULTS)
    if isinstance(html, str):
        parsed = parse_hltv_results(html)
        parsed['source_url'] = HLTV_EVENT_RESULTS
        parsed['evidence'] = ev
        result['results'] = parsed
    else:
        result['limitations'].append('HLTV event Results page was not readable; Day 1/2 results stay unverified.')
    html, ev = probe.get('hltv-matches-index', HLTV_MATCHES)
    if isinstance(html, str):
        result['matches_index_evidence'] = ev
    for mid in TWC_MATCH_IDS:
        url = f'https://www.hltv.org/matches/{mid}/thunderpick-world-championship-2026'
        page, pev = probe.get(f'hltv-match-{mid}', url)
        if isinstance(page, str):
            info = parse_hltv_match_page(page)
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', page)
            info['source_url'] = canonical.group(1) if canonical else url
            info['evidence'] = pev
            result['match_pages'][str(mid)] = info
        else:
            result['limitations'].append(f'HLTV match page {mid} was not readable.')
        time.sleep(0.5)
    for mid in TWC_ANALYTICS_IDS:
        slug = 'aurora-vs-9z' if mid == 2399412 else 'betboom-vs-legacy'
        url = f'https://www.hltv.org/betting/analytics/{mid}/{slug}-thunderpick-world-championship-2026'
        page, pev = probe.get(f'hltv-analytics-{mid}', url)
        if isinstance(page, str):
            odds = parse_hltv_odds(page)
            odds['source_url'] = url
            odds['evidence'] = pev
            result['analytics'][str(mid)] = odds
        else:
            result['limitations'].append(f'HLTV odds page {mid} was not readable; no bookmaker odds captured.')
        time.sleep(0.5)
    for name, url in HLTV_TEAM_PAGES.items():
        page, pev = probe.get(f'hltv-team-{name.lower()}', url)
        if isinstance(page, str):
            soup_text = re.sub(r'\s+', ' ', page)
            players = re.findall(r'/player/(\d+)/([a-zA-Z0-9\-]+)', soup_text)
            uniq = []
            for pid, nick in players:
                if nick not in [u[1] for u in uniq]:
                    uniq.append((pid, nick))
            result['teams'][name] = {'url': url, 'evidence': pev, 'player_links': uniq[:12]}
        else:
            result['limitations'].append(f'HLTV team page for {name} was not readable.')
    result['observed_at'] = now_iso()
    return result


# ---------------------------------------------------------------------------
# Valve regional standings (official rating points)
# ---------------------------------------------------------------------------

def valve_rating_rows(text: str, teams: list[str], snapshot: str, source_url: str) -> dict:
    """Read Valve's own standings table by column position, never by "first number".

    Official column order is ``Standing | Points | Team Name | Roster | details``. Taking
    the first numeric cell returns the *standing* instead of the points; the first probe
    run made exactly that mistake, so the columns are addressed by position and the five
    listed players are kept so a reviewer can see which roster the row describes.
    Only an exact, case-insensitive team-name match is accepted. Nothing is fuzzy-matched.
    """
    out: dict = {'ratings': {}, 'ambiguous': {}, 'absent': [], 'limitations': [], 'standings_as_of': None}
    heading = re.search(r'Standings as of (\d{4}_\d{2}_\d{2})', text)
    if heading:
        out['standings_as_of'] = heading.group(1)
    wanted = {team.lower(): team for team in teams}
    found: dict[str, list] = {}
    for line in text.splitlines():
        if not line.strip().startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 4 or not re.fullmatch(r'\d+', cells[0]) or not re.fullmatch(r'\d+', cells[1]):
            continue
        standing, points, name, roster = cells[0], cells[1], cells[2], cells[3]
        team = wanted.get(name.lower())
        if team is None:
            continue
        found.setdefault(team, []).append({
            'standing': int(standing), 'points': int(points), 'team_name': name,
            'roster': [part.strip() for part in roster.split(',') if part.strip()],
            'snapshot': snapshot, 'source_url': source_url})
    for team, rows in found.items():
        if len(rows) == 1:
            out['ratings'][team] = rows[0]
        else:
            # Valve's own snapshot lists this name more than once with different rosters.
            # Choosing one would be an inference, so all candidates are published and the
            # team gets no rating. Verified against standings_global_2026_10_05.md, where
            # aimclub, Bebop, Leo and Just Players each appear twice.
            out['ambiguous'][team] = rows
            out['limitations'].append(
                f'"{team}" appears {len(rows)} times in {snapshot} with different rosters '
                f'(standings {", ".join(str(r["standing"]) for r in rows)}); no rating is chosen.')
    for team in teams:
        if team not in found:
            out['absent'].append(team)
            out['limitations'].append(f'No exact-name Valve row for "{team}" in {snapshot}; left blank, not inferred.')
    return out


def collect_valve(probe: Probe, teams: list[str]) -> dict:
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    listing, ev = probe.get('valve-live-2026', VALVE_API + '/contents/live/2026', headers=headers)
    out: dict = {'teams_requested': teams, 'ratings': {}, 'limitations': [], 'listing_evidence': ev}
    if not isinstance(listing, list):
        out['limitations'].append('Valve live/2026 directory listing was not readable.')
        return out
    names = sorted(f['name'] for f in listing if isinstance(f, dict) and f.get('name', '').startswith('standings_global_'))
    out['snapshots'] = names
    if not names:
        out['limitations'].append('No standings_global_*.md snapshot found in Valve live/2026.')
        return out
    latest = names[-1]
    out['snapshot_used'] = latest
    item = next(f for f in listing if f.get('name') == latest)
    raw_url = item.get('download_url') or f'https://raw.githubusercontent.com/ValveSoftware/counter-strike_regional_standings/main/live/2026/{latest}'
    text, tev = probe.get('valve-standings-latest', raw_url)
    out['source_url'] = raw_url
    out['evidence'] = tev
    if not isinstance(text, str):
        out['limitations'].append('Valve standings snapshot was not readable.')
        return out
    parsed = valve_rating_rows(text, teams, latest, raw_url)
    out['ratings'] = parsed['ratings']
    out['ambiguous'] = parsed['ambiguous']
    out['absent'] = parsed['absent']
    out['standings_as_of'] = parsed['standings_as_of']
    out['limitations'].extend(parsed['limitations'])
    out['observed_at'] = now_iso()
    return out


# ---------------------------------------------------------------------------
# Hotspawn inventory + the deployed production snapshot
# ---------------------------------------------------------------------------

def collect_hotspawn(probe: Probe) -> dict:
    data, ev = probe.get('hotspawn-fixtures', HOTSPAWN_FIXTURES)
    out: dict = {'source_url': HOTSPAWN_FIXTURES, 'lobby_url': HOTSPAWN_LOBBY, 'evidence': ev,
                 'limitations': [], 'fixtures': []}
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict) or row.get('sport_alias') != 'cs2':
                continue
            teams = row.get('teams') or []
            out['fixtures'].append({
                'id': str(row.get('id')),
                'teams': [ (t.get('name') if isinstance(t, dict) else t) for t in teams ],
                'competition': row.get('competition', {}).get('name') if isinstance(row.get('competition'), dict) else row.get('competition'),
                'starts_at': row.get('starts_at') or row.get('start_date'),
                'status': row.get('status'),
                'tier': row.get('tier') or row.get('competition', {}).get('tier') if isinstance(row.get('competition'), dict) else row.get('tier'),
            })
        out['count'] = len(out['fixtures'])
    else:
        out['limitations'].append('Hotspawn fixture API was not readable from the runner; inventory comparison unavailable.')
    lobby, lev = probe.get('hotspawn-lobby', HOTSPAWN_LOBBY)
    if isinstance(lobby, str):
        m = re.search(r'(\d+)\s+matches', lobby)
        out['lobby_match_text'] = m.group(0) if m else None
        out['lobby_evidence'] = lev
    out['observed_at'] = now_iso()
    return out


def collect_production(probe: Probe) -> dict:
    """What the public site currently serves. This is the object of the audit."""
    out: dict = {'base': PAGES_BASE, 'snapshots': {}, 'limitations': []}
    for name in ('latest.json', 'origination.json', 'row-source-audit.json'):
        url = f'{PAGES_BASE}/data/{name}?cb=ba7164a0-{int(time.time())}'
        data, ev = probe.get(f'pages-{name.split(".")[0]}', url)
        if isinstance(data, dict):
            compact = {}
            if name == 'latest.json':
                compact = {k: data.get(k) for k in ('schema_version', 'generated_at', 'last_attempted_at',
                                                    'analysis_as_of', 'inventory_observed_at', 'coverage_complete',
                                                    'run_status', 'refresh_interval_hours', 'stale_after_hours', 'counts')}
                compact['upcoming'] = [
                    {'id': m.get('id'),
                     'teams': [t.get('name') for t in m.get('teams') or []],
                     'competition': m.get('competition'),
                     'starts_at': m.get('starts_at'),
                     'locks_at': m.get('locks_at'),
                     'availability': m.get('availability'),
                     'tier': m.get('tier'),
                     'method': (m.get('analysis') or {}).get('method'),
                     'probabilities': (m.get('analysis') or {}).get('probabilities'),
                     'pick_index': m.get('pick_index'),
                     'analysis_source': (m.get('analysis') or {}).get('source_url'),
                     'hotspawn_source': m.get('source_url'),
                     'limitations': m.get('limitations')}
                    for m in data.get('matches') or [] if m.get('availability') in ('upcoming', 'live')]
                compact['flag_ids'] = [f.get('id') for f in data.get('flags') or []]
                compact['flag_titles'] = [f.get('title') for f in data.get('flags') or []]
            elif name == 'origination.json':
                compact = {k: data.get(k) for k in ('generated_at', 'observed_at', 'counts', 'ladder', 'limitations') if k in data}
                compact['matches'] = [
                    {'id': r.get('id'),
                     'teams': [t.get('name') for t in r.get('teams') or []],
                     'competition': r.get('competition'),
                     'starts_at': r.get('starts_at'),
                     'origination_method': (r.get('origination') or {}).get('method'),
                     'origination_label': (r.get('origination') or {}).get('label'),
                     'origination_probabilities': (r.get('origination') or {}).get('probabilities'),
                     'origination_source': (r.get('origination') or {}).get('source_url'),
                     'origination_observed_at': (r.get('origination') or {}).get('observed_at'),
                     'unresolved_reason': r.get('unresolved_reason') or (r.get('origination') or {}).get('reason'),
                     'limitations': r.get('limitations')}
                    for r in data.get('matches') or []]
            else:
                compact = data.get('totals') or {}
                compact['sample_violations'] = (data.get('violations') or [])[:20]
            compact['url'] = url
            compact['evidence'] = ev
            compact['observed_at'] = now_iso()
            out['snapshots'][name] = compact
        else:
            out['limitations'].append(f'Deployed {name} was not readable from the runner.')
    return out


def bovada_moneylines(response) -> list:
    """Bovada prematch series moneylines, exactly as the coupon feed states them.

    Only the main, non-live, open ``2W-12`` Moneyline market of a prematch GAMEEVENT is
    kept: a map handicap or a live price must never be mistaken for a series winner line.
    """
    rows = []
    for group in response if isinstance(response, list) else []:
        if not isinstance(group, dict):
            continue
        league = ' / '.join(str(p.get('description')) for p in group.get('path') or [] if isinstance(p, dict))
        for event in group.get('events') or []:
            if not isinstance(event, dict):
                continue
            start = event.get('startTime')
            lines = []
            for dg in event.get('displayGroups') or []:
                for market in dg.get('markets') or []:
                    period = market.get('period') or {}
                    if (market.get('key') == '2W-12' and market.get('description') == 'Moneyline'
                            and period.get('main') is True and period.get('live') is False
                            and market.get('status') == 'O'):
                        lines.append(market)
            outcomes = (lines[0].get('outcomes') if len(lines) == 1 else None) or []
            rows.append({
                'event_id': str(event.get('id')),
                'description': event.get('description'),
                'event_type': event.get('type'),
                'live': event.get('live'),
                'start_time_ms': start,
                'start_utc': (datetime.fromtimestamp(start / 1000, UTC).isoformat()
                              if isinstance(start, (int, float)) else None),
                'league': league,
                'competitors': [c.get('name') for c in event.get('competitors') or [] if isinstance(c, dict)],
                'moneyline_markets': len(lines),
                'outcomes': [{'name': o.get('description'),
                              'decimal': (o.get('price') or {}).get('decimal'),
                              'american': (o.get('price') or {}).get('american'),
                              'status': o.get('status')} for o in outcomes],
                'market_id': str(lines[0].get('id')) if len(lines) == 1 else None,
                'source_url': 'https://www.bovada.lv' + str(event.get('link') or ''),
                'page_url': 'https://www.bovada.lv/sports',
            })
    return rows


def thunderpick_moneylines(response) -> list:
    """Thunderpick's own "Match Winner" selections with the decimal odds it quotes."""
    rows = []
    data = response.get('data') if isinstance(response, dict) else None
    if not isinstance(data, dict):
        return rows
    for key in ('upcoming', 'live'):
        for event in data.get(key) or []:
            if not isinstance(event, dict):
                continue
            for market in event.get('preferredMarkets') or []:
                if market.get('name') not in ('Match Winner',) or market.get('status') != 1:
                    continue
                selections = market.get('selections') or []
                if len(selections) != 2:
                    continue
                rows.append({
                    'bucket': key,
                    'event_id': market.get('eventId'),
                    'market_id': market.get('id'),
                    'market': market.get('name'),
                    'competition': event.get('competition') or event.get('tournament'),
                    'starts_at': event.get('startsAt') or event.get('date'),
                    'selections': [{'name': s.get('name'), 'odds': s.get('odds'), 'type': s.get('type'),
                                    'status': s.get('status')} for s in selections],
                    'source_url': 'https://thunderpick.io/esports/counter-strike',
                })
    return rows


def collect_other_books(probe: Probe) -> dict:
    """Esportsbook / exchange checks. A failure here is recorded, never guessed around."""
    out: dict = {'providers': {}, 'limitations': []}
    events, ev = probe.get('kalshi-cs2', KALSHI_EVENTS + '?' + urlencode(
        {'series_ticker': 'KXCS2GAME', 'status': 'open', 'limit': 200, 'with_nested_markets': 'true'}))
    if isinstance(events, dict):
        rows = []
        for event in events.get('events') or []:
            for market in event.get('markets') or []:
                rows.append({'ticker': market.get('ticker'), 'question': market.get('question'),
                             'yes_bid': market.get('yes_bid'), 'yes_ask': market.get('yes_ask'),
                             'no_bid': market.get('no_bid'), 'no_ask': market.get('no_ask'),
                             'volume': market.get('volume'), 'event_ticker': event.get('event_ticker'),
                             'close_time': market.get('close_time'), 'active': market.get('active')})
        out['providers']['kalshi'] = {'markets': rows, 'count': len(rows), 'evidence': ev,
                                      'source_url': 'https://kalshi.com/markets/kxcs2game/counterstrike-2-game/',
                                      'api_docs': 'https://docs.kalshi.com/api-reference/market/get-markets',
                                      'observed_at': now_iso()}
    else:
        out['limitations'].append('Kalshi CS2 series was not readable; no Kalshi price is claimed.')
    bovada, bev = probe.get('bovada-cs2', BOVADA_API)
    if isinstance(bovada, list):
        out['providers']['bovada'] = {'moneylines': bovada_moneylines(bovada), 'evidence': bev,
                                      'source_url': 'https://www.bovada.lv/sports', 'api': BOVADA_API,
                                      'observed_at': now_iso()}
        out['providers']['bovada']['count'] = len(out['providers']['bovada']['moneylines'])
    else:
        out['limitations'].append('Bovada CS2 coupon was not readable; no Bovada price is claimed.')
    thunder, tev = probe.get('thunderpick-cs2', THUNDERPICK_API, method='POST', payload={'gameIds': [6]},
                             headers={'Content-Type': 'application/json', 'Origin': 'https://thunderpick.io',
                                      'Referer': 'https://thunderpick.io/'})
    if isinstance(thunder, (list, dict)):
        rows = thunderpick_moneylines(thunder)
        out['providers']['thunderpick'] = {'moneylines': rows, 'count': len(rows), 'evidence': tev,
                                           'source_url': 'https://thunderpick.io/esports/counter-strike',
                                           'api': THUNDERPICK_API, 'observed_at': now_iso(),
                                           'note': 'Read-only POST with {"gameIds":[6]}; opening the endpoint as a '
                                                   'browser GET does not reproduce this request.'}
    else:
        out['limitations'].append('Thunderpick match API was not readable; no Thunderpick price is claimed.')
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(argv)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    probe = Probe(out)
    started = now_iso()

    twc_teams = ['Aurora', '9z', 'BETBOOM', 'Legacy', 'FURIA', 'Falcons', 'Ninjas in Pyjamas', 'PARIVISION']
    collectors = [('hotspawn', collect_hotspawn, ()),
                  ('production_site', collect_production, ()),
                  ('polymarket', collect_polymarket, ()),
                  ('hltv', collect_hltv, ()),
                  ('valve', collect_valve, (twc_teams,)),
                  ('other_books', collect_other_books, ())]
    collected, crashes = {}, []
    for key, func, extra in collectors:
        try:
            collected[key] = func(probe, *extra)
        except Exception as exc:  # a collector bug is a finding, not a lost run
            import traceback
            crashes.append({'collector': key, 'error': f'{type(exc).__name__}: {exc}',
                            'traceback': traceback.format_exc()[-3000:]})
            collected[key] = {'limitations': [f'Collector {key} raised {type(exc).__name__}: {exc}']}
            print(f'::warning title=Verification collector {key} failed::{type(exc).__name__}: {exc}', flush=True)
    hotspawn = collected['hotspawn']
    production = collected['production_site']
    polymarket = collected['polymarket']
    hltv = collected['hltv']
    valve = collected['valve']
    books = collected['other_books']

    observations = {
        'schema_version': 1,
        'session': 'arena-ba7164a0',
        'title': 'Independent first-party observations for line-by-line verification',
        'probe_started_at': started,
        'probe_finished_at': now_iso(),
        'policy': ('Read-only observations. No probability is calculated, repaired or invented here. '
                   'Hotspawn popularity or participation is never a probability input. Values that an '
                   'official source does not confirm are recorded as blank with the reason.'),
        'hotspawn': hotspawn,
        'production_site': production,
        'polymarket': polymarket,
        'hltv': hltv,
        'valve': valve,
        'other_books': books,
        'collector_crashes': crashes,
        'requests': probe.log,
    }
    path = out / 'observations.json'
    path.write_text(json.dumps(observations, indent=1, ensure_ascii=False) + '\n')
    for crash in crashes:
        print(crash['traceback'], flush=True)
    ok = sum(1 for r in probe.log if r['status'] == 'ok')
    print(f'\nWrote {path}')
    print(f'Sources ok={ok} not-ok={len(probe.log) - ok}; '
          f'moneylines={len(polymarket.get("moneylines") or [])}; '
          f'hotspawn_cs2={hotspawn.get("count", 0)}; valve_ratings={len(valve.get("ratings", {}))}; '
          f'collector_crashes={len(crashes)}')
    # Partial evidence is still evidence: only an unwritten dossier is a hard failure.
    return 0


if __name__ == '__main__':
    sys.exit(main())
