"""Session arena-b3e91409: capture live primary-source evidence for every open Hotspawn CS2 fixture.

Run on a network-capable runner:  python -m scripts.b3e91409_probe

Why a separate probe: the authoring sandbox has no route to play.hotspawn.com, hltv.org, Polymarket,
Thunderpick, Kalshi, Bovada or the published Pages site (every `curl` returns HTTP 000), while the
brief requires every published row to link an official source and every unconfirmable value to stay
blank. This module therefore *only observes*: it archives each response with its URL, method, UTC
observation time, HTTP status, byte count and SHA-256, and records which sources name both teams of
each open fixture. It never computes a probability, never writes a pick and never reads Hotspawn's
community "% picked" or HLTV's fan votes as an input.

Evidence written under data/research/b3e91409/live/:
  manifest.json                 every request, status, bytes, sha256, cache headers
  hotspawn-fixtures-api.json    the public scheduled-fixture array (raw)
  hotspawn-lobby.html.gz        fresh render of https://play.hotspawn.com/lobby
  hotspawn-cs2.html.gz          fresh render of https://play.hotspawn.com/cs2-pickems
  hltv-matches.html.gz          https://www.hltv.org/matches
  valve-directory.json          official Valve standings directory
  valve-standings.md            newest official Valve global standings on/before today
  polymarket-events-<offset>.json  gamma events for the official CS2 tag, compact projection
  thunderpick-matches.json      public Thunderpick match feed for gameId 6 (raw)
  kalshi-events.json            Kalshi events, compact projection (best effort)
  bovada-cs2.json               Bovada CS2 coupon (best effort)
  open-fixtures.json            per open fixture: every source that names both teams
  summary.txt                   human-readable, one block per open fixture
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

OUT = Path('data/research/b3e91409/live')

HOTSPAWN_API = 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?' + urlencode(
    {'sport_alias': 'cs2', 'status': 'scheduled', 'tenantId': 1})
LOBBY = 'https://play.hotspawn.com/lobby'
CS2_LOBBY = 'https://play.hotspawn.com/cs2-pickems'
HLTV = 'https://www.hltv.org/matches'
VALVE_REPO = 'https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings'
GAMMA = 'https://gamma-api.polymarket.com/events'
THUNDERPICK = 'https://thunderpick.io/api/matches'
KALSHI = 'https://api.elections.kalshi.com/trade-api/v2/events'
BOVADA = ('https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2'
          '?marketFilterId=def&preMatchOnly=true&lang=en')


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def key(name):
    """Same normalisation the site uses: Unicode/case/whitespace equivalent, nothing fuzzy."""
    import unicodedata
    text = unicodedata.normalize('NFKC', name or '').casefold()
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class Probe:
    def __init__(self, out: Path):
        self.out = out
        self.out.mkdir(parents=True, exist_ok=True)
        self.manifest = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HotspawnCS2Coverage/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)',
            'Accept': 'application/json,text/html;q=0.9',
        })
        self.last = 0.0

    def _pause(self):
        wait = 0.25 - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()

    def get(self, url, label, *, method='GET', payload=None, want='json', save=None):
        """Fetch once, record the manifest row, return (parsed_or_text, entry) or (None, entry)."""
        self._pause()
        entry = {'id': label, 'url': url, 'method': method, 'observed_at': iso(now()),
                 'http_status': None, 'status': 'error'}
        if payload is not None:
            entry['request_body'] = payload  # public read-only query, no credentials
        try:
            response = self.session.request(method, url, json=payload, timeout=(15, 60), allow_redirects=True)
            entry.update(http_status=response.status_code, final_url=response.url,
                         content_type=response.headers.get('Content-Type'),
                         response_date=response.headers.get('Date'),
                         bytes=len(response.content),
                         response_sha256=hashlib.sha256(response.content).hexdigest())
            for header, field in (('Age', 'cache_age_sec'), ('X-Cache', 'cache_status')):
                if response.headers.get(header) is not None:
                    entry[field] = response.headers[header]
            if response.status_code == 429:
                entry['error'] = 'Rate limited; no retry, no challenge bypass'
            response.raise_for_status()
            if len(response.content) > 12_000_000:
                raise ValueError('response exceeds the 12 MB safety limit')
            entry['status'] = 'ok'
            data = response.json() if want == 'json' else response.text
            if save:
                entry['evidence'] = self.save(save, data, want)
            return data, entry
        except (requests.RequestException, ValueError) as exc:
            entry['error'] = entry.get('error') or str(exc)[:300]
            return None, entry
        finally:
            self.manifest.append(entry)

    def save(self, name, data, want):
        path = self.out / name
        if want == 'json':
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        elif name.endswith('.gz'):
            with gzip.open(path, 'wt', encoding='utf-8') as fh:
                fh.write(data)
        else:
            path.write_text(data, encoding='utf-8')
        return 'data/research/b3e91409/live/' + path.name


# ---------------------------------------------------------------- Hotspawn

def fixture_start(raw):
    value = raw.get('scheduled_start_time')
    try:
        return datetime.fromtimestamp(int(value) / 1000, timezone.utc)
    except (TypeError, ValueError):
        return None


def open_fixtures(api_rows, reference):
    rows = []
    for raw in api_rows or []:
        if raw.get('sport_alias') != 'cs2':
            continue
        start = fixture_start(raw)
        if not start or start <= reference:
            continue
        rows.append({
            'id': str(raw.get('id')), 'competition': raw.get('competition_name'),
            'tier': raw.get('tier'), 'starts_at': iso(start), 'best_of': raw.get('best_of'),
            'source_url': 'https://www.hotspawn.com/matches/',
            'teams': [raw.get('participants0_name'), raw.get('participants1_name')],
        })
    return sorted(rows, key=lambda r: (r['starts_at'], r['id']))


# ---------------------------------------------------------------- HLTV

def parse_hltv(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or '', 'html.parser')
    grouped = {}
    for anchor in soup.select('a[href^="/matches/"]'):
        href = anchor['href']
        if not re.fullmatch(r'/matches/\d+/[^/?#]+', href):
            continue
        group = grouped.setdefault(href, {'times': set(), 'teams': set()})
        for node in ([anchor] if anchor.has_attr('data-unix') else anchor.select('[data-unix]')):
            try:
                group['times'].add(iso(datetime.fromtimestamp(int(node['data-unix']), timezone.utc)))
            except (TypeError, ValueError, KeyError):
                pass
        names = tuple(n.get_text(' ', strip=True) for n in anchor.select('.matchTeamName, .match-teamname'))
        if len(names) == 2 and all(names):
            group['teams'].add(names)
    out = []
    for href, group in grouped.items():
        if len(group['times']) != 1 or len(group['teams']) != 1:
            continue  # ambiguous card: record nothing rather than guess
        teams = list(next(iter(group['teams'])))
        out.append({'teams': teams, 'starts_at': next(iter(group['times'])),
                    'url': 'https://www.hltv.org' + href})
    return out


# ---------------------------------------------------------------- Polymarket

def polymarket_projection(event):
    markets = []
    for market in event.get('markets') or []:
        if not isinstance(market, dict):
            continue
        markets.append({k: market.get(k) for k in (
            'id', 'question', 'outcomes', 'outcomePrices', 'clobTokenIds',
            'bestBid', 'bestAsk', 'spread', 'lastTradePrice', 'active', 'closed',
            'gameStartTime', 'sportsMarketType')})
    return {k: event.get(k) for k in ('id', 'slug', 'title', 'startDate', 'endDate', 'closed', 'active', 'markets')} | {'markets': markets}


def gamma_events(probe, limit=100, max_pages=20):
    events, offsets = [], []
    for page in range(max_pages):
        offset = page * limit
        url = GAMMA + '?' + urlencode({'tag_slug': 'counter-strike-2', 'active': 'true',
                                       'closed': 'false', 'limit': limit, 'offset': offset})
        body, entry = probe.get(url, f'polymarket-events-{offset}')
        if not isinstance(body, list):
            break
        events.extend(polymarket_projection(e) for e in body if isinstance(e, dict))
        offsets.append({'offset': offset, 'records': len(body), 'url': url,
                        'observed_at': entry['observed_at'], 'sha256': entry.get('response_sha256'),
                        'http_status': entry.get('http_status')})
        probe.save(f'polymarket-page-{offset}.json', offsets[-1], 'json')
        if len(body) < limit:
            break
    if events:
        probe.save('polymarket-events.json', events, 'json')
    return events, offsets


# ---------------------------------------------------------------- Thunderpick

def thunderpick(probe):
    body, entry = probe.get(THUNDERPICK, 'thunderpick-matches', method='POST',
                            payload={'gameIds': [6]}, save='thunderpick-matches.json')
    if not isinstance(body, dict) or body.get('ok') is not True:
        return [], None
    data = body.get('data') or {}
    rows = data.get('upcoming') or data.get('matches') or []
    return (rows if isinstance(rows, list) else []), entry


# ---------------------------------------------------------------- Valve

def valve(probe, reference):
    directory, _ = probe.get(f'{VALVE_REPO}/contents/live/{reference.year}', 'valve-directory',
                             save='valve-directory.json')
    names = []
    for entry in directory or []:
        m = re.fullmatch(r'standings_global_(\d{4})_(\d{2})_(\d{2})\.md', entry.get('name', ''))
        if m and '-'.join(m.groups()) <= reference.date().isoformat():
            names.append(('-'.join(m.groups()), entry['path']))
    if not names:
        return []
    day, path = max(names)
    body, entry = probe.get(f'{VALVE_REPO}/contents/{path}', 'valve-standings')
    text = ''
    if isinstance(body, dict) and isinstance(body.get('content'), str):
        import base64
        try:
            text = base64.b64decode(body['content']).decode('utf-8', 'replace')
        except ValueError:
            text = ''
    if text:
        (OUT / 'valve-standings.md').write_text(text, encoding='utf-8')
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 4 and re.fullmatch(r'\d+', cells[0] or ''):
            rows.append({'standing': int(cells[0]), 'team': cells[1], 'points': cells[2]})
    return rows


# ---------------------------------------------------------------- summary

def name_in(text, name):
    return key(name) and key(name) in key(text)


def build_summary(fixtures, hltv_cards, poly_events, tp_rows, valve_rows, permalinks=None):
    permalinks = permalinks or {}
    blocks, records = [], []
    for fixture in fixtures:
        if permalinks.get(fixture['id']):
            fixture['source_url'] = permalinks[fixture['id']]
        a, b = fixture['teams']
        found = []
        # HLTV: exact both-name card, and the start delta must be recorded either way.
        for card in hltv_cards:
            names = {key(card['teams'][0]), key(card['teams'][1])}
            if names == {key(a), key(b)}:
                found.append({'source': 'HLTV /matches', 'url': card['url'],
                              'hltv_starts_at': card['starts_at'],
                              'hotspawn_starts_at': fixture['starts_at'],
                              'match': True})
        # Polymarket: event title/game naming, both names present in the event blob.
        for event in poly_events:
            blob = json.dumps(event)
            if name_in(blob, a) and name_in(blob, b):
                found.append({'source': 'Polymarket gamma', 'url': 'https://polymarket.com/event/' + str(event.get('slug')),
                              'event_id': event.get('id'), 'title': event.get('title'),
                              'start': event.get('startDate'), 'match': True})
        # Thunderpick: both names in one row.
        for row in tp_rows:
            blob = json.dumps(row)
            if name_in(blob, a) and name_in(blob, b):
                found.append({'source': 'Thunderpick', 'url': 'https://thunderpick.io/esports/counter-strike',
                              'row_keys': sorted(row)[:40], 'match': True, 'row': row})
        # Valve: each team's official standing row, separately (never a probability).
        for team in (a, b):
            for row in valve_rows:
                if key(row['team']) == key(team):
                    found.append({'source': 'Valve global standings', 'team': team,
                                  'standing': row['standing'], 'points': row['points'],
                                  'url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                                  'match': True})
        record = dict(fixture, sources=found)
        records.append(record)
        lines = [f"{fixture['id']}  {a} vs {b}  {fixture['starts_at']}  {fixture['competition']} (tier {fixture['tier']})"]
        if found:
            for item in found:
                detail = {k: v for k, v in item.items() if k not in ('row',)}
                lines.append('    ' + json.dumps(detail, ensure_ascii=False)[:400])
        else:
            lines.append('    no source above names both teams at this observation')
        blocks.append('\n'.join(lines))
    return records, '\n\n'.join(blocks)


def main():
    reference = now()
    probe = Probe(OUT)
    summary = {'schema_version': 1, 'observed_at': iso(reference), 'sources': {}, 'notes': []}

    api_rows, api_entry = probe.get(HOTSPAWN_API, 'hotspawn-fixtures-api', save='hotspawn-fixtures-api.json')
    fixtures = open_fixtures(api_rows if isinstance(api_rows, list) else [], reference)
    summary['sources']['hotspawn_api'] = {k: api_entry.get(k) for k in (
        'url', 'observed_at', 'http_status', 'status', 'bytes', 'response_sha256', 'error')}
    summary['sources']['hotspawn_api']['records'] = len(api_rows or []) if isinstance(api_rows, list) else None
    summary['sources']['hotspawn_api']['open_records'] = len(fixtures)

    stamp = int(time.time())
    permalinks = {}
    for url, label, name in ((LOBBY, 'hotspawn-lobby', 'hotspawn-lobby.html.gz'),
                             (CS2_LOBBY, 'hotspawn-cs2', 'hotspawn-cs2.html.gz')):
        sep = '&' if '?' in url else '?'
        body, entry = probe.get(f'{url}{sep}cb={stamp}', label, want='text', save=name)
        summary['sources'][label] = {k: entry.get(k) for k in (
            'url', 'observed_at', 'http_status', 'status', 'bytes', 'response_sha256',
            'cache_status', 'cache_age_sec', 'error')}
        if body:
            for slug, fid in re.findall(r'/matches/([a-z0-9-]+)-(\d{7,})', body):
                permalinks[fid] = f'https://www.hotspawn.com/matches/{slug}-{fid}'
            cards = sorted(set(re.findall(r'/matches/[a-z0-9-]+-(\d{7,})', body)))
            ids = sorted(set(re.findall(r'\bid="fixture-(\d+)"', body)))
            summary['sources'][label]['match_permalinks'] = len(cards)
            summary['sources'][label]['fixture_dom_ids'] = len(ids)
            summary['sources'][label]['dom_ids'] = ids

    hltv_html, entry = probe.get(HLTV, 'hltv-matches', want='text', save='hltv-matches.html.gz')
    hltv_cards = parse_hltv(hltv_html) if hltv_html else []
    if hltv_cards:
        probe.save('hltv-cards.json', hltv_cards, 'json')
    summary['sources']['hltv'] = {k: entry.get(k) for k in (
        'url', 'observed_at', 'http_status', 'status', 'bytes', 'response_sha256', 'error')}
    summary['sources']['hltv']['cards'] = len(hltv_cards)

    poly_events, poly_pages = gamma_events(probe)
    summary['sources']['polymarket'] = {'pages': poly_pages, 'events': len(poly_events),
                                        'url': GAMMA + '?tag_slug=counter-strike-2'}

    tp_rows, tp_entry = thunderpick(probe)
    summary['sources']['thunderpick'] = {k: tp_entry.get(k) for k in (
        'url', 'observed_at', 'http_status', 'status', 'bytes', 'response_sha256', 'error')} if tp_entry else {'status': 'unavailable'}
    summary['sources']['thunderpick']['rows'] = len(tp_rows)
    if tp_rows:
        summary['thunderpick_row_keys'] = sorted(tp_rows[0])[:60]

    valve_rows = valve(probe, reference)
    summary['sources']['valve'] = {'rows': len(valve_rows), 'standings': 'data/research/b3e91409/live/valve-standings.md'}

    for url, label, name in ((KALSHI, 'kalshi-events', 'kalshi-events.json'),
                             (BOVADA, 'bovada-cs2', 'bovada-cs2.json')):
        body, entry = probe.get(url, label, save=name)
        summary['sources'][label] = {k: entry.get(k) for k in (
            'url', 'observed_at', 'http_status', 'status', 'bytes', 'response_sha256', 'error')}

    records, text = build_summary(fixtures, hltv_cards, poly_events, tp_rows, valve_rows, permalinks)
    probe.save('open-fixtures.json', records, 'json')
    (OUT / 'summary.txt').write_text(
        f"observed {summary['observed_at']}\nopen Hotspawn CS2 fixtures: {len(fixtures)}\n\n" + text + '\n',
        encoding='utf-8')
    probe.save('manifest.json', probe.manifest, 'json')
    probe.save('sources.json', summary, 'json')
    print((OUT / 'summary.txt').read_text(encoding='utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
