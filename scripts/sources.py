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

from scripts.domain import iso, name_key, timestamp

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
            response = self.session.request(method, url, json=payload, timeout=(15, 45), allow_redirects=True)
            entry.update(http_status=response.status_code, final_url=response.url, content_type=response.headers.get('Content-Type'), response_date=response.headers.get('Date'), response_sha256=hashlib.sha256(response.content).hexdigest())
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


def hotspawn(client: Client):
    lobby_html, lobby_req = client.fetch(LOBBY, 'hotspawn-lobby')
    cs2_html, cs2_req = client.fetch(CS2_LOBBY, 'hotspawn-cs2')
    lobby_rows, links = hydration(lobby_html)
    cs2_rows, more_links = hydration(cs2_html)
    links.update(more_links)
    api_rows, api_req = client.json(FIXTURES_API, 'hotspawn-fixtures')
    if not isinstance(api_rows, list):
        raise SourceError('Fixture API is no longer an unpaginated array; refusing partial coverage')
    def ids(rows):
        values = [str(x['id']) for x in rows if x.get('sport_alias') == 'cs2']
        if len(values) != len(set(values)):
            raise SourceError('Duplicate CS2 fixture IDs')
        return set(values)
    official_ids = ids(api_rows)
    if official_ids != ids(cs2_rows) or official_ids != ids(lobby_rows):
        raise SourceError('Lobby, CS2 lobby and fixture API disagree; complete coverage cannot be confirmed')
    visible_ids = re.findall(r'<app-pickem-vs-card\b[^>]*\bid="fixture-(\d+)"', cs2_html)
    evidence = client.save('hotspawn-context', {'lobby_url': LOBBY, 'cs2_url': CS2_LOBBY, 'fixture_api': FIXTURES_API, 'observed_at': api_req['observed_at'], 'visible_ids': visible_ids, 'permalinks': links, 'lobby_ids': sorted(ids(lobby_rows)), 'cs2_ids': sorted(ids(cs2_rows)), 'api_ids': sorted(official_ids)})
    rows = [r for r in api_rows if r.get('sport_alias') == 'cs2']
    return rows, links, {'status': 'ok', 'name': 'Hotspawn match inventory', 'url': LOBBY, 'api_url': FIXTURES_API, 'observed_at': api_req['observed_at'], 'records': len(rows), 'visible_cards': len(visible_ids), 'detail': 'All CS2 fixture IDs reconciled across the lobby, CS2 lobby and public fixture array. No client-side pagination is used by the inspected public client.', 'evidence': evidence}


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


def poly_index(client: Client):
    html, req = client.fetch(POLY_INDEX, 'polymarket-index')
    games = polymarket_games(html)
    req['evidence'] = client.save('polymarket-index', games)
    return games, {'status': 'ok', 'name': 'Polymarket CS2', 'url': POLY_INDEX, 'observed_at': req['observed_at'], 'records': len(games), 'detail': 'Public game index used for discovery. Each selected fixture is rechecked against its official Gamma event and both live order books; rounded directory percentages are never probability inputs.'}


def parse_hltv_matches(html: str):
    """Support observed split-link cards without joining neighboring matches.

    The time and teams now live in separate anchors with the SAME match URL.
    Pinned cards may repeat a match; conflicting repeats fail closed.
    """
    soup = BeautifulSoup(html, 'html.parser')
    grouped = {}
    for anchor in soup.select('a[href^="/matches/"]'):
        href = anchor['href']
        if not re.fullmatch(r'/matches/\d+/[^/?#]+', href):
            continue
        group = grouped.setdefault(href, {'times': set(), 'teams': set()})
        for node in ([anchor] if anchor.has_attr('data-unix') else anchor.select('[data-unix]')):
            start = timestamp(node.get('data-unix'))
            if start:
                group['times'].add(iso(start))
        names = tuple(n.get_text(' ', strip=True) for n in anchor.select('.matchTeamName, .match-teamname, .match-team-name'))
        if len(names) == 2 and all(names):
            group['teams'].add(names)
    candidates = []
    for href, group in grouped.items():
        if len(group['times']) > 1 or len(group['teams']) > 1:
            raise SourceError('Conflicting repeated HLTV match identity/time; research not accepted')
        if len(group['times']) == len(group['teams']) == 1:
            candidates.append({'teams': list(next(iter(group['teams']))), 'starts_at': next(iter(group['times'])), 'source_url': 'https://www.hltv.org' + href})
    if not candidates:
        raise SourceError('HLTV match schema unavailable; no structured research observations confirmed')
    return candidates


def hltv_research(client: Client, matches: list):
    """Research only unresolved primary matches; no votes converted to odds."""
    html, req = client.fetch(HLTV, 'hltv-matches')
    req['evidence'] = client.save('hltv-index-response', {'url': HLTV, 'observed_at': req['observed_at'], 'html': html})
    candidates = parse_hltv_matches(html)
    client.save('hltv-research', candidates)
    return candidates, {'status': 'ok', 'name': 'HLTV fallback research', 'url': HLTV, 'observed_at': req['observed_at'], 'records': len(candidates), 'detail': 'Match identities only, parsed from same-URL time/team links and deduplicated across pinned cards. HLTV fan votes and rankings are not converted into betting odds. No bookmaker line is accepted without its original source.'}


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
