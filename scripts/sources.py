"""Public first-party readers with auditable response manifests; no bot bypasses."""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests
from bs4 import BeautifulSoup

from scripts.domain import array, iso, name_key, timestamp
from scripts.github_auth import auth_headers

LOBBY = 'https://play.hotspawn.com/lobby'
CS2_LOBBY = 'https://play.hotspawn.com/cs2-pickems'
FIXTURES_API = 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?' + urlencode({'sport_alias': 'cs2', 'status': 'scheduled', 'tenantId': 1})
POLY_INDEX = 'https://polymarket.com/esports/cs2'
HLTV = 'https://www.hltv.org/matches'
VALVE_REPO = 'https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings'


class SourceError(RuntimeError):
    pass


class Client:
    def __init__(self, output: Path):
        self.evidence = output / 'evidence'
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.manifest = []
        self.saved = set()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'HotspawnCS2Coverage/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)', 'Accept': 'application/json,text/html;q=0.9'})
        self.last_request = 0.0

    def save(self, name: str, data):
        path = self.evidence / (name + '.json')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        relative = 'data/evidence/' + path.name
        self.saved.add(relative)
        return relative

    def fetch(self, url: str, label: str, *, method='GET', payload=None, json_body=False):
        delay = 0.2 - (time.monotonic() - self.last_request)
        if delay > 0:
            time.sleep(delay)
        self.last_request = time.monotonic()
        entry = {'id': label, 'url': url, 'method': method, 'observed_at': iso(datetime.now(timezone.utc)), 'http_status': None, 'status': 'error'}
        if payload is not None:
            entry['request_body'] = payload  # Public read-only query, no credentials.
        self.manifest.append(entry)
        try:
            response = self.session.request(method, url, json=payload, headers=auth_headers(url), timeout=(15, 45), allow_redirects=True)
            entry.update(http_status=response.status_code, final_url=response.url, content_type=response.headers.get('Content-Type'), response_date=response.headers.get('Date'), response_sha256=hashlib.sha256(response.content).hexdigest())
            for header, field in (('Age', 'cache_age_sec'), ('X-Cache', 'cache_status')):
                if response.headers.get(header) is not None:
                    entry[field] = response.headers[header]
            if response.status_code == 429:
                entry['error'] = 'Rate limited; no aggressive retry or challenge bypass attempted'
            response.raise_for_status()
            if len(response.content) > 12_000_000:
                raise SourceError('Response exceeds 12 MB safety limit')
            data = response.json() if json_body else response.text
            entry['status'] = 'ok'
            if json_body:
                entry['evidence'] = self.save(label, data)
            return data, entry
        except (requests.RequestException, ValueError, SourceError) as exc:
            entry['error'] = entry.get('error') or str(exc)[:300]
            raise SourceError(f'{label}: {entry["error"]}') from exc

    def json(self, url: str, label: str, **kwargs):
        return self.fetch(url, label, json_body=True, **kwargs)


def hydration(html: str) -> tuple[list, dict]:
    soup = BeautifulSoup(html, 'html.parser')
    node = soup.find('script', id='ng-state')
    if not node:
        raise SourceError('Hotspawn public Angular hydration state missing')
    state = json.loads(node.get_text())
    fixture_lists, links = [], {}
    for value in state.values():
        if not isinstance(value, dict) or value.get('s') != 200:
            continue
        url, body = value.get('u', ''), value.get('b')
        if urlparse(url).path == '/api/v1/fixtures' and isinstance(body, list):
            fixture_lists.append(body)
        if isinstance(body, dict) and isinstance(body.get('permalinks'), dict):
            # Public hydration only. Never request administrative endpoints.
            links.update(body['permalinks'])
    if len(fixture_lists) != 1:
        raise SourceError('Expected one unpaginated public fixture array; contract changed')
    return fixture_lists[0], links


def fresh_url(url: str, stamp: float | None = None) -> str:
    """Ask for a current render of a server-rendered page.

    Observed 2026-10-15 from a GitHub-hosted runner: /lobby and /cs2-pickems are served from a CDN cache
    (X-Cache: HIT, Age 4,000-5,000 s and growing) while the fixture API is live, so the fixture list embedded in the
    HTML can be more than an hour behind and any fixture change makes the two "disagree". A unique query string gets
    a fresh render (X-Cache: MISS, Age: 0). It is an ordinary public GET; nothing is bypassed.
    """
    return url + ('&' if '?' in url else '?') + 'cb=' + str(int(time.time() if stamp is None else stamp))


def fetch_fresh_page(client: Client, url: str, label: str):
    try:
        return client.fetch(fresh_url(url), label)
    except SourceError:
        return client.fetch(url, label)  # unchanged behaviour if the fresh render is refused


def disagreement(api_ids: set, lobby_ids: set, cs2_ids: set, lobby_req: dict, cs2_req: dict) -> str:
    """A self-explaining reconciliation failure: which IDs differ, in which direction, and how old the HTML was."""
    parts = []
    for name, ids_, req in (('lobby page', lobby_ids, lobby_req), ('CS2 lobby page', cs2_ids, cs2_req)):
        only_api, only_page = sorted(api_ids - ids_), sorted(ids_ - api_ids)
        if only_api or only_page:
            cache = ', '.join(f'{k}={req[k]}' for k in ('cache_status', 'cache_age_sec') if req.get(k) is not None) or 'no cache headers'
            parts.append(f'{name} ({cache}): {len(only_api)} in the API only {only_api[:6]}, {len(only_page)} in the page only {only_page[:6]}')
    return '; '.join(parts)


def hotspawn(client: Client):
    """Read the public fixture array; use rendered pages only as a cross-check.

    The scheduled-fixture API is the same public array that feeds the Hotspawn
    client and is the authoritative inventory. The two rendered lobby pages are
    an independent reconciliation check. On 2026-10-17T07:16Z both rendered
    pages answered HTTP 403 while the API had answered 200 four hours earlier;
    failing the whole refresh in that case discarded a usable official inventory
    and made every otherwise source-backed pick look unusable. When no rendered
    page can be read, the valid API array is published with an explicit
    `unavailable` cross-check marker instead of a reconciliation claim. If any
    rendered page IS readable, a disagreement still fails closed.
    """
    def ids(rows):
        values = [str(x['id']) for x in rows if x.get('sport_alias') == 'cs2']
        if len(values) != len(set(values)):
            raise SourceError('Duplicate CS2 fixture IDs')
        return set(values)

    def page(url, label):
        try:
            html, req = fetch_fresh_page(client, url, label)
        except (SourceError, ValueError, KeyError) as exc:
            # Only transport/access failure is an unreadable page. Keep the
            # failed request in the manifest; never disguise it as read.
            return {'html': None, 'req': None, 'rows': None, 'ids': None, 'links': {}, 'error': str(exc)}
        try:
            rows, links = hydration(html)
            page_ids = ids(rows)
        except (SourceError, ValueError, KeyError) as exc:
            # A readable page that violates the inventory contract is a real
            # defect, not an access limitation. Never degrade it to "blocked".
            raise SourceError(f'{label}: readable page violates the inventory contract: {exc}') from exc
        return {'html': html, 'req': req, 'rows': rows, 'ids': page_ids, 'links': links, 'error': None}

    for attempt in range(2):
        # Observe the API and both rendered pages in the same round so a
        # fixture added between them is a real disagreement, not a stale read.
        api_rows, api_req = client.json(FIXTURES_API, 'hotspawn-fixtures')
        if not isinstance(api_rows, list):
            raise SourceError('Fixture API is no longer an unpaginated array; refusing partial coverage')
        official_ids = ids(api_rows)
        if not official_ids:
            raise SourceError('Fixture API returned no CS2 fixtures; refusing an empty inventory claim')
        lobby = page(LOBBY, 'hotspawn-lobby')
        cs2 = page(CS2_LOBBY, 'hotspawn-cs2')
        read = [(name, record) for name, record in (('lobby', lobby), ('cs2', cs2)) if record['ids'] is not None]
        if not read:
            # API-only mode. A retry here would only repeat a refused HTML
            # request; the API response is already a complete official array.
            break
        if all(official_ids == record['ids'] for _, record in read):
            break
        # A fixture can change in the few seconds between requests; look once
        # more before giving up, exactly as the reconciled path always has.
        if attempt == 0:
            time.sleep(5)
            continue
        raise SourceError('Rendered Hotspawn inventory disagrees with the fixture API; complete coverage cannot be confirmed (' + disagreement(official_ids, lobby['ids'] or set(), cs2['ids'] or set(), lobby['req'] or {}, cs2['req'] or {}) + ')')

    links = {}
    for record in (lobby, cs2):
        links.update(record['links'])
    verified_pages = [name for name, record in (('lobby', lobby), ('cs2', cs2)) if record['ids'] is not None]
    crosscheck = 'complete' if len(verified_pages) == 2 else ('partial' if verified_pages else 'unavailable')
    unavailable = [f'{name}: {record["error"]}' for name, record in (('lobby', lobby), ('cs2', cs2)) if record['ids'] is None]
    if crosscheck == 'complete':
        detail = 'All CS2 fixture IDs reconciled across the lobby, CS2 lobby and public fixture array. No client-side pagination is used by the inspected public client.'
    elif crosscheck == 'partial':
        detail = ('The public scheduled-fixture API returned a valid, duplicate-free CS2 array and agrees with the rendered page(s) that could be read ('
                  + ', '.join(verified_pages) + '). The other rendered page was unavailable: ' + '; '.join(unavailable)
                  + '. Inventory completeness rests on the API array; the missing page was not silently treated as agreement.')
    else:
        detail = ('The public scheduled-fixture API returned a valid, duplicate-free CS2 array. Both rendered lobby pages were unavailable: '
                  + '; '.join(unavailable) + '. The secondary HTML cross-check is unavailable; the API array is published as the complete scheduled inventory and no three-response reconciliation is claimed.')
    visible_ids = re.findall(r'<app-pickem-vs-card\b[^>]*\bid="fixture-(\d+)"', cs2['html'] or '')
    evidence = client.save('hotspawn-context', {'lobby_url': LOBBY, 'cs2_url': CS2_LOBBY, 'fixture_api': FIXTURES_API, 'observed_at': api_req['observed_at'], 'visible_ids': visible_ids, 'permalinks': links, 'lobby_ids': sorted(lobby['ids'] or []), 'cs2_ids': sorted(cs2['ids'] or []), 'api_ids': sorted(official_ids), 'crosscheck': crosscheck, 'verified_pages': verified_pages, 'unavailable': unavailable})
    rows = [r for r in api_rows if r.get('sport_alias') == 'cs2']
    return rows, links, {'status': 'ok', 'name': 'Hotspawn match inventory', 'url': LOBBY, 'api_url': FIXTURES_API, 'observed_at': api_req['observed_at'], 'records': len(rows), 'visible_cards': len(visible_ids), 'crosscheck': crosscheck, 'verified_pages': verified_pages, 'unavailable': unavailable, 'detail': detail, 'evidence': evidence}


def polymarket_games(html: str) -> list:
    """Decode public Next.js flight JSON, not displayed rounded/crowd percentages."""
    games = {}
    def walk(obj):
        if isinstance(obj, dict):
            if obj.get('sportSlug') == 'cs2' and 'homeTokenId' in obj and 'awayTokenId' in obj:
                key = obj.get('slug')
                if key:
                    games[key] = obj
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
    pattern = r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)'
    for part in re.findall(pattern, html):
        text = json.loads(part)
        for line in text.split('\n'):
            colon = line.find(':')
            if colon >= 0:
                try:
                    walk(json.JSONDecoder().raw_decode(line[colon + 1:])[0])
                except (ValueError, TypeError):
                    continue
    if not games:
        raise SourceError('Polymarket public CS2 game index schema missing; not a successful empty feed')
    return list(games.values())


def gamma_games(events: list, evidence: str) -> list:
    """Discover fixture identity from first-party moneyline records, never prices."""
    result = []
    for event in events:
        if not isinstance(event, dict) or not str(event.get('slug', '')).startswith('cs2-'):
            continue
        if not any(t.get('slug') == 'cs2' for t in event.get('tags', []) if isinstance(t, dict)):
            continue
        for market in event.get('markets', []):
            names = array(market.get('outcomes'))
            scope = market.get('sportsMarketType') or (market.get('sports') or {}).get('sports_market_type')
            if scope != 'moneyline' or len(names) != 2 or not all(isinstance(n, str) and n.strip() for n in names):
                continue
            if re.search(r'\b(map\s*\d|game\s*\d|handicap|spread|total|outright)\b', market.get('question', ''), re.I):
                continue
            start = market.get('gameStartTime') or event.get('startTime')
            if not event.get('id') or timestamp(start) is None:
                continue
            item = {'id': str(event['id']), 'slug': event['slug'], 'homeName': names[0], 'awayName': names[1], 'startTime': start, 'isLive': event.get('live'), 'discovery_evidence': evidence}
            if item not in result:
                result.append(item)
    return result


def poly_index(client: Client):
    games, limitations, observed = [], [], None
    try:
        html, req = client.fetch(POLY_INDEX, 'polymarket-directory')
        games = polymarket_games(html)
        observed = req['observed_at']
    except SourceError as exc:
        limitations.append(str(exc))
    # The displayed directory can be windowed. Independently paginate the
    # official CS2 tag rather than equating visible cards with all markets.
    seen, pages, complete = set(), 0, False
    for offset in range(0, 2000, 100):
        url = 'https://gamma-api.polymarket.com/events?' + urlencode({'tag_slug': 'cs2', 'active': 'true', 'closed': 'false', 'limit': 100, 'offset': offset})
        try:
            events, req = client.json(url, f'polymarket-discovery-{offset}')
            if not isinstance(events, list) or any(not isinstance(e, dict) or not e.get('id') for e in events):
                raise SourceError('Gamma event pagination contract changed')
            ids = [str(e['id']) for e in events]
            if len(set(ids)) != len(ids) or seen.intersection(ids):
                raise SourceError('Repeated Gamma event IDs; pagination completeness unverified')
            seen.update(ids)
            games.extend(gamma_games(events, req['evidence']))
            observed = req['observed_at']
            pages += 1
            if len(events) < 100:
                complete = True
                break
        except SourceError as exc:
            limitations.append(str(exc))
            break
    if not complete:
        limitations.append('Gamma pagination did not reach a terminal page; no exhaustive external-market discovery claim.')
    if observed is None:
        raise SourceError('; '.join(limitations))
    # Retain contradictory source identities as separate candidates so the
    # resolver can reject ambiguous joins; collapse identical event joins.
    unique = {}
    for game in games:
        key = (str(game.get('id')), name_key(game.get('homeName', '')), name_key(game.get('awayName', '')), game.get('startTime'))
        unique.setdefault(key, game)
    games = list(unique.values())
    client.save('polymarket-index', games)
    return games, {'status': 'ok' if not limitations else 'limited', 'name': 'Polymarket CS2', 'url': POLY_INDEX, 'observed_at': observed, 'records': len(games), 'discovery_complete': complete, 'pages': pages, 'detail': 'Public directory plus paginated official CS2-tag events used for discovery. Every selected fixture is rechecked against its original Gamma event and both order books; directory/outcome prices are never probability inputs.' + (' Limitations: ' + '; '.join(limitations) if limitations else '')}


def parse_hltv_matches(html: str) -> list:
    """Combine exact-URL sibling grouping with wrapper and repeat safeguards."""
    soup = BeautifulSoup(html, 'html.parser')
    wrappers = soup.select('[data-match-wrapper]')
    for card in wrappers:
        hrefs = {a['href'] for a in card.select('a[href^="/matches/"]')}
        times = {n.get('data-unix') for n in card.select('[data-unix]')}
        if len(hrefs) > 1 or len(times) > 1:
            raise SourceError('Conflicting HLTV wrapper paths/times; research not accepted')
    grouped = {}
    for anchor in soup.select('a[href^="/matches/"]'):
        href = anchor['href']
        if not re.fullmatch(r'/matches/\d+/[^/?#]+', href):
            continue
        group = grouped.setdefault(href, {'times': set(), 'teams': set(), 'formats': set()})
        for node in ([anchor] if anchor.has_attr('data-unix') else anchor.select('[data-unix]')):
            start = timestamp(node.get('data-unix'))
            if start:
                group['times'].add(iso(start))
        names = tuple(n.get_text(' ', strip=True) for n in anchor.select('.matchTeamName, .match-teamname, .match-team-name'))
        if len(names) == 2 and all(names):
            group['teams'].add(names)
        for node in anchor.select('.match-meta'):
            value = node.get_text(' ', strip=True).lower()
            if re.fullmatch(r'bo[1357]', value):
                group['formats'].add(int(value[2:]))
    candidates = []
    for href, group in grouped.items():
        if any(len(group[key]) > 1 for key in ['times', 'teams', 'formats']):
            raise SourceError('Conflicting repeated HLTV identity/time/format; research not accepted')
        if len(group['times']) == len(group['teams']) == 1:
            item = {'teams': list(next(iter(group['teams']))), 'starts_at': next(iter(group['times'])), 'source_url': 'https://www.hltv.org' + href}
            if group['formats'] or wrappers:
                item['best_of'] = next(iter(group['formats']), None)
            candidates.append(item)
    if not candidates:
        raise SourceError('HLTV match schema unavailable; no structured research observations confirmed')
    return candidates


def hltv_research(client: Client, matches: list):
    """Research only unresolved primary matches; no restricted filtered stats."""
    html, req = client.fetch(HLTV, 'hltv-matches')
    candidates = parse_hltv_matches(html)
    # Preserve original markup for independent parser replay and manual review.
    req['evidence'] = client.save('hltv-page', {'url': req['url'], 'observed_at': req['observed_at'], 'html': html})
    if not candidates:
        raise SourceError('HLTV match schema unavailable; no structured research observations confirmed')
    client.save('hltv-research', candidates)
    return candidates, {'status': 'ok', 'name': 'HLTV fallback research', 'url': HLTV, 'observed_at': req['observed_at'], 'records': len(candidates), 'detail': 'Split-anchor match cards parsed and saved for replay. Exact fixture identities and independently published series formats only. Fan votes are not probabilities; no bookmaker line is accepted without original-source prices.'}


def thunderpick(client: Client):
    url = 'https://thunderpick.io/api/matches'
    data, req = client.json(url, 'thunderpick-matches', method='POST', payload={'gameIds': [6]})
    if not isinstance(data, dict) or data.get('ok') is not True:
        raise SourceError('Thunderpick public API did not confirm a successful response')
    body = data.get('data') or {}
    rows = body.get('upcoming', body.get('matches'))
    if not isinstance(rows, list):
        raise SourceError('Thunderpick match array contract unrecognized')
    return rows, {'status': 'ok', 'name': 'Thunderpick esportsbook', 'url': 'https://thunderpick.io/esports/counter-strike', 'api_url': url, 'observed_at': req['observed_at'], 'records': len(rows), 'detail': 'Only active prematch CS2 match-winner markets with exact team/time alignment and two decimal odds are eligible.'}


def book_page_check(client: Client, url: str, label: str, title: str):
    html, req = client.fetch(url, label)
    redirected = urlparse(req['final_url']).path.rstrip('/') in {'', '/en'}
    return {'status': 'unavailable', 'name': title, 'url': url, 'observed_at': req['observed_at'], 'records': 0, 'detail': 'Redirected to a generic landing page; no match-level betting lines verified.' if redirected else 'Public page loaded but no validated, paired CS2 series-winner price contract is available. No prices extracted or invented.'}


def valve_ratings(client: Client, now: datetime):
    directory, _ = client.json(f'{VALVE_REPO}/contents/live/{now.year}', 'valve-directory')
    names = []
    for entry in directory:
        m = re.fullmatch(r'standings_global_(\d{4})_(\d{2})_(\d{2})\.md', entry['name'])
        if m:
            day = '-'.join(m.groups())
            if day <= now.date().isoformat():
                names.append((day, entry['path']))
    if not names:
        raise SourceError('No official global Valve snapshot on or before the observation date')
    day, path = max(names)
    content, req = client.json(f'{VALVE_REPO}/contents/{path}', 'valve-standings-response')
    import base64
    from scripts.domain import parse_valve_table
    text = base64.b64decode(content['content']).decode('utf-8')
    source_url = 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/' + content['sha'] + '/' + path
    # Git blob SHA is not a commit ref. Use the official path URL and separately
    # retain the response's immutable blob SHA for content integrity.
    source_url = content['html_url']
    rows = parse_valve_table(text, source_url, day)
    client.save('valve-ratings', {'snapshot_date': day, 'git_blob_sha': content['sha'], 'source_url': source_url, 'rows': rows})
    return rows, {'status': 'ok', 'name': 'Valve official rating fallback', 'url': source_url, 'observed_at': req['observed_at'], 'records': len(rows), 'snapshot_date': day, 'detail': 'Used only after primary markets, HLTV research and book checks fail to resolve a match. Duplicate team names, incomplete rosters or snapshots older than 35 days are rejected. Probabilities are labeled uncalibrated research estimates.'}
