"""Session arena-c03ef201 — deep first-party research for fixtures the ladder leaves blank.

Why this exists
---------------
The brief asks for a pick for *every* Hotspawn CS2 match. The published ladder
(Polymarket -> Kalshi -> Thunderpick -> Bovada -> reviewed aggregated reference
-> Valve model) still leaves low-tier fixtures blank: no exchange or sportsbook
lists them at all, or the only listed book is far wider than the published
spread ceilings. The brief's research order for those fixtures is HLTV first,
then esportsbooks and esports betting lines.

This module is the dated evidence pass for that research. It runs on the GitHub
runner (the only environment in this session with egress to the providers) and:

* rebuilds the live blank list from the collectors' own outputs
  (``data/latest.json`` + ``data/origination.json``) — it never guesses;
* probes HLTV first: the fixture's own confirmed match page, the weekly official
  world-ranking pages, and each team's official page — every original response
  is saved and hash-checked in the request manifest;
* then esportsbook / betting-line providers: the Pinnacle public guest board
  (first-party prices, series period 0 only, "Yes/No" specials rejected),
  1xBet's public esports line page and bo3.gg's public match lists — recording,
  for each blank fixture, whether the provider actually lists the fixture and
  any two-way series price it prints;
* writes ``data/research/c03ef201/`` reports: a live-probe summary in the same
  shape as session be84edde's (inventory counts plus the full research trail of
  every blank fixture) and a provider-deep-probe report with per-fixture facts.

It writes no probability, no pick and no alias of its own. Values that fail the
published book contract are recorded as observations for the human-reviewed
rung work (task C-3), never promoted to picks by this module. Every fetch
failure is recorded per source and never fabricates an observation.

Usage:  python -m scripts.c03ef201_research --live
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts.hltv_ranking import parse_ranking_page  # shared, tested parser

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / 'c03ef201'
EVIDENCE = OUT / 'evidence'

# The honest project UA that scripts/sources.py uses to read HLTV successfully
# from GitHub runners. A fake browser UA was answered HTTP 403 on 2026-10-19
# while this UA read the same pages in the same job; keep the working style.
UA = 'HotspawnCS2Research/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'

HLTV_RANKING = 'https://www.hltv.org/ranking/'
HLTV_MATCHES = 'https://www.hltv.org/matches'
PINNACLE_LEAGUES = 'https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues'
PINNACLE_MATCHUPS = 'https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups'
PINNACLE_STRAIGHT = 'https://guest.api.arcadia.pinnacle.com/0.1/leagues/{league}/markets/straight'
PINNACLE_SITE = 'https://www.pinnacle.com/en/esports/csgo/matchups'
X1BET_LINE = 'https://1xbet.com/en/line/Esports'
X1BET_SITE = 'https://1xbet.com/en/line/Esports'
BO3GG_CURRENT = 'https://bo3.gg/matches/current?game=csgo'
BO3GG_UPCOMING = 'https://bo3.gg/matches/upcoming?game=csgo'
BO3GG_SITE = 'https://bo3.gg/matches'
# The public HTML is a Nuxt client shell, so the site's own JSON endpoints are
# probed too. Each candidate is recorded whatever it answers; a missing API is
# an observation, not an error.
BO3GG_API_CANDIDATES = (
    'https://bo3.gg/api/matches?game=csgo&status=upcoming',
    'https://bo3.gg/api/v1/matches?game=csgo',
    'https://bo3.gg/api/v1/matches/upcoming?game=csgo',
    'https://bo3.gg/_nuxt/matches.json',
)

# Pinnacle prints specials ("Yes"/"No", "Odd"/"Even", "Team By N", exact score
# grids) as matchups on the same board as real two-team series. Those are never
# match-winner lines; reject them by participant text before any price is read.
PINNACLE_SPECIAL = re.compile(
    r'^(yes|no|odd|even|tie|draw|over|under|1|x|2|\d+|.+ by \d+|\d+,\s*\d+|\d+\s*-\s*\d+)$', re.I)


def name_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def probe_fetch(label: str, url: str, manifest: list, *, timeout: int = 30):
    """One read-only GET. Every outcome is recorded; failures are never fatal.

    Any 2xx is kept: some providers answer 203 for public pages (observed from
    1xbet.com on 2026-10-19). The body is still scanned and hashed — never
    trusted as verified odds without the published book contract.
    """
    entry = {'id': label, 'url': url, 'method': 'GET',
             'observed_at': iso(datetime.now(timezone.utc)), 'status': 'error'}
    manifest.append(entry)
    try:
        response = requests.get(url, headers={'User-Agent': UA, 'Accept': '*/*',
                                              'Accept-Encoding': 'gzip, identity'},
                                timeout=(15, timeout))
        raw = response.content
        entry.update(http_status=response.status_code,
                     content_type=response.headers.get('Content-Type', ''),
                     bytes=len(raw),
                     response_sha256=hashlib.sha256(raw).hexdigest())
        if not 200 <= response.status_code < 300:
            entry['error'] = f'HTTP {response.status_code}'
            return None
        entry['status'] = 'ok'
        text = raw.decode('utf-8', errors='replace')
        if 'html' in (entry['content_type'] or '') or text.lstrip()[:1] not in ('{', '['):
            # Large HTML originals are kept gzip-compressed, as twc_research.py
            # does, so the committed evidence stays small but byte-verifiable.
            path = EVIDENCE / f'{label}.html.gz'
            path.write_bytes(gzip.compress(text.encode('utf-8'), mtime=0))
            entry['evidence'] = 'data/research/c03ef201/evidence/' + path.name
        else:
            try:
                body = json.loads(text)
            except ValueError:
                body = {'raw_text': text}
            path = EVIDENCE / f'{label}.json'
            path.write_text(json.dumps(
                {'url': url, 'observed_at': entry['observed_at'],
                 'response_sha256': entry['response_sha256'], 'body': body},
                ensure_ascii=False) + '\n')
            entry['evidence'] = 'data/research/c03ef201/evidence/' + path.name
        return text
    except (requests.RequestException, TimeoutError, OSError, ValueError) as exc:
        code = getattr(getattr(exc, 'response', None), 'status_code', None)
        if code is not None:
            entry['http_status'] = code
        entry['error'] = str(exc)[:300]
        return None


def load_json(path: Path):
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# BLANK LIST — copied from the collectors' own outputs, never invented
# ---------------------------------------------------------------------------

def blank_fixtures(latest: dict, origination: dict) -> list:
    by_id = {str(m.get('id')): m for m in (latest.get('matches') or [])}
    out = []
    for row in origination.get('matches') or []:
        if row.get('origination'):
            continue
        mid = str(row.get('id'))
        src = by_id.get(mid) or {}
        trail = row.get('research') or []
        hltv_url = next((r.get('source_url') for r in trail
                         if str(r.get('stage', '')).startswith('HLTV')
                         and str(r.get('source_url', '')).startswith('https://www.hltv.org/matches/')), None)
        out.append({
            'hotspawn_id': mid,
            'teams': [t.get('name') for t in (src.get('teams') or row.get('teams') or [])],
            'competition': src.get('competition') or row.get('competition'),
            'starts_at': src.get('starts_at') or row.get('starts_at'),
            'hltv_url': hltv_url,
            'hotspawn_source_url': src.get('source_url'),
            'research_trail': [{'stage': r.get('stage'), 'status': r.get('status'),
                                'detail': (r.get('detail') or '')[:400],
                                'source_url': r.get('source_url')} for r in trail],
        })
    return out


# ---------------------------------------------------------------------------
# HLTV PROBE — ranking facts first, per the brief's research order
# ---------------------------------------------------------------------------
# parse_ranking_page is imported from scripts.hltv_ranking (single tested
# parser shared with the origination rung).


def parse_team_page(text: str) -> dict:
    """Official HLTV team page facts: profile world-ranking row and team id."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, 'html.parser')
    out = {'team': None, 'world_ranking': None, 'team_url': None}
    title = soup.select_one('.profile-team-name') or soup.select_one('h1 .context-item-name') or soup.select_one('h1')
    if title:
        out['team'] = title.get_text(' ', strip=True)
    for row in soup.select('.profile-team-stat'):
        label = row.get_text(' ', strip=True).lower()
        value = row.select_one('.stats-row .value') or row.select_one('a') or row
        if 'world ranking' in label or 'ranking' in label:
            m = re.search(r'#?(\d+)', value.get_text(' ', strip=True))
            out['world_ranking'] = int(m.group(1)) if m else None
    return out


def parse_match_team_links(text: str) -> list:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, 'html.parser')
    links = []
    for a in soup.select('a[href^="/team/"]'):
        href = (a.get('href') or '').split('?')[0]
        m = re.fullmatch(r'/team/(\d+)/([a-z0-9-]+)', href)
        if not m:
            continue
        url = 'https://www.hltv.org' + href
        if url not in links:
            links.append(url)
    return links[:4]


def hltv_probe(fixtures: list, manifest: list) -> dict:
    """HLTV first: fixture match pages, official weekly ranking, team pages."""
    report = {'ranking_url': HLTV_RANKING, 'ranking_pages': [], 'teams': {}, 'matches': {}}
    ranking = {}
    for offset in (0, 30, 60, 90, 120):
        url = HLTV_RANKING + (f'?offset={offset}' if offset else '')
        text = probe_fetch(f'hltv-ranking-{offset}', url, manifest)
        if text is None:
            report['ranking_pages'].append({'url': url, 'status': 'fetch-failed'})
            break
        rows = parse_ranking_page(text)
        for i, row in enumerate(rows):
            row['rank'] = offset + i + 1
            row['source_url'] = url
            ranking.setdefault(name_key(row['team']), row)
        report['ranking_pages'].append({'url': url, 'status': 'ok', 'rows': len(rows)})
        if len(rows) < 25:
            break
    report['ranking_teams'] = len(ranking)
    for fixture in fixtures:
        fid = fixture['hotspawn_id']
        entry = {'teams': fixture['teams'], 'ranking_hits': {}}
        if fixture.get('hltv_url'):
            text = probe_fetch(f'hltv-match-{fid}', fixture['hltv_url'], manifest)
            if text is not None:
                entry['match_page'] = {'url': fixture['hltv_url'], 'status': 'ok',
                                       'team_links': parse_match_team_links(text)}
            else:
                entry['match_page'] = {'url': fixture['hltv_url'], 'status': 'fetch-failed'}
        else:
            entry['match_page'] = {'url': HLTV_MATCHES, 'status': 'no-fixture-specific-url'}
        for team in fixture['teams']:
            hit = ranking.get(name_key(team))
            facts = {'ranking_entry': None if not hit else
                     {'rank': hit['rank'], 'points': hit['points'],
                      'published_team': hit['team'], 'source_url': hit['source_url']}}
            entry['ranking_hits'][team] = facts
        report['matches'][fid] = entry
    # Official team pages for every blank-fixture team (ranking row + identity).
    for fixture in fixtures:
        links = (report['matches'].get(fixture['hotspawn_id']) or {}).get('match_page', {}).get('team_links') or []
        for link in links:
            label = 'hltv-team-' + link.rstrip('/').split('/')[-2] + '-' + fixture['hotspawn_id']
            text = probe_fetch(label, link, manifest)
            if text is not None:
                report['teams'][link] = parse_team_page(text)
    return report


# ---------------------------------------------------------------------------
# PINNACLE GUEST BOARD — first-party esportsbook prices (series period 0)
# ---------------------------------------------------------------------------

def parse_pinnacle_matchups(payload) -> list:
    rows = []
    for m in payload if isinstance(payload, list) else []:
        if not isinstance(m, dict):
            continue
        participants = [p.get('name') for p in m.get('participants') or [] if isinstance(p, dict)]
        rows.append({'id': m.get('id'), 'league_id': m.get('leagueId'),
                     'league': m.get('league') or m.get('leagueName'),
                     'participants': participants, 'start': m.get('startTime'),
                     'is_live': m.get('isLive'), 'best_of': m.get('bestOfX')})
    return rows


def parse_pinnacle_straight(payload) -> list:
    """Two-way series moneylines from a league's straight markets.

    Period 0 is the series/game line; periods >= 1 are per-map prices (session
    be84edde verified periods 1-3 repeat identical numbers). Participants
    without an id are read by name only, and specials ("Yes"/"No", "Odd/Even",
    "Team By N") are rejected before any price is read.
    """
    out = []
    for block in payload if isinstance(payload, list) else []:
        if not isinstance(block, dict):
            continue
        matchup_id = block.get('matchupId') or (block.get('matchup') or {}).get('id')
        for period in block.get('periods') or []:
            if not isinstance(period, dict) or int(period.get('number') or 0) != 0:
                continue
            for market in period.get('markets') or []:
                if not isinstance(market, dict):
                    continue
                if str(market.get('type') or '').lower() not in ('moneyline', '2-way', 'gamel'):
                    continue
                prices = {}
                for side in market.get('prices') or []:
                    if not isinstance(side, dict):
                        continue
                    name = side.get('participant') or side.get('name') or side.get('designation')
                    price = side.get('price') if isinstance(side.get('price'), (int, float)) else side.get('american')
                    if isinstance(name, str) and isinstance(price, (int, float)):
                        prices.setdefault(name, []).append(float(price))
                names = list(prices)
                if len(names) != 2 or any(PINNACLE_SPECIAL.match(n) for n in names):
                    continue
                values = [prices[n][0] for n in names]
                if any(v <= 1 for v in values):
                    continue
                out.append({'matchup_id': matchup_id, 'period': 0,
                            'names': names, 'odds': values})
    return out


def pinnacle_probe(fixtures: list, manifest: list) -> dict:
    report = {'matchups': [], 'series_lines': [], 'fixture_hits': {}, 'leagues': []}
    leagues_text = probe_fetch('pinnacle-leagues-cs', PINNACLE_LEAGUES, manifest)
    matchups_text = probe_fetch('pinnacle-matchups-cs', PINNACLE_MATCHUPS, manifest)
    leagues = []
    try:
        if leagues_text:
            leagues = [{'id': l.get('id'), 'name': l.get('name')}
                       for l in json.loads(leagues_text) if isinstance(l, dict)]
    except ValueError:
        leagues = []
    report['leagues'] = leagues
    matchups = []
    try:
        if matchups_text:
            matchups = parse_pinnacle_matchups(json.loads(matchups_text))
    except ValueError:
        matchups = []
    report['matchups'] = matchups
    by_matchup = {str(m['id']): m for m in matchups}
    for league in leagues:
        if not isinstance(league.get('id'), int):
            continue
        text = probe_fetch(f'pinnacle-straight-{league["id"]}',
                           PINNACLE_STRAIGHT.format(league=league['id']), manifest)
        if text is None:
            continue
        try:
            rows = parse_pinnacle_straight(json.loads(text))
        except ValueError:
            rows = []
        for row in rows:
            meta = by_matchup.get(str(row['matchup_id'])) or {}
            row['league'] = league.get('name')
            row['start'] = meta.get('start')
            row['source_url'] = PINNACLE_SITE
            report['series_lines'].append(row)
    for fixture in fixtures:
        hits = []
        for row in report['series_lines']:
            names = {name_key(n) for n in row['names']}
            if names == {name_key(t) for t in fixture['teams']}:
                hits.append(row)
        report['fixture_hits'][fixture['hotspawn_id']] = hits
    return report


# ---------------------------------------------------------------------------
# 1XBET / BO3.GG — public esports line pages: listing evidence only
# ---------------------------------------------------------------------------

def scan_listing(text: str, teams: list) -> dict:
    """Does the provider's own page print these team names? Snippet evidence.

    A case-insensitive exact-name hit carries a page snippet. A normalized-core
    hit (accents and punctuation removed) is recorded as a weaker
    ``normalized-core`` match without a snippet. No hit stays None.
    """
    low = text.lower()
    norm = name_key(low)
    out = {}
    for team in teams:
        lowered = str(team or '').lower().strip()
        if not lowered:
            out[team] = None
            continue
        index = low.find(lowered)
        if index >= 0:
            out[team] = {'found': True, 'match': 'exact-name',
                         'snippet': text[max(0, index - 80):index + 160].replace('\n', ' ')[:240]}
        elif name_key(team) and name_key(team) in norm:
            out[team] = {'found': True, 'match': 'normalized-core', 'snippet': None}
        else:
            out[team] = None
    return out


def xbet_probe(fixtures: list, manifest: list) -> dict:
    report = {'url': X1BET_LINE, 'fixture_hits': {}}
    text = probe_fetch('x1bet-line-esports', X1BET_LINE, manifest)
    report['status'] = 'ok' if text is not None else 'fetch-failed'
    if text is not None:
        for fixture in fixtures:
            report['fixture_hits'][fixture['hotspawn_id']] = scan_listing(text, fixture['teams'])
    return report


def bo3gg_probe(fixtures: list, manifest: list) -> dict:
    report = {'urls': [BO3GG_CURRENT, BO3GG_UPCOMING], 'pages': [], 'fixture_hits': {}}
    combined = ''
    for label, url in (('bo3gg-current', BO3GG_CURRENT), ('bo3gg-upcoming', BO3GG_UPCOMING)):
        text = probe_fetch(label, url, manifest)
        report['pages'].append({'url': url, 'status': 'ok' if text is not None else 'fetch-failed'})
        if text is not None:
            combined += text
    for candidate in BO3GG_API_CANDIDATES:
        label = 'bo3gg-api-' + re.sub(r'[^a-z0-9]+', '-', candidate.split('bo3.gg/')[-1])[:40]
        text = probe_fetch(label, candidate, manifest)
        report['pages'].append({'url': candidate, 'status': 'ok' if text is not None else 'fetch-failed'})
        if text is not None:
            combined += text
    if combined:
        for fixture in fixtures:
            report['fixture_hits'][fixture['hotspawn_id']] = scan_listing(combined, fixture['teams'])
    return report


# ---------------------------------------------------------------------------
# LIVE-PROBE SUMMARY — same shape as session be84edde's report
# ---------------------------------------------------------------------------

def summarise(latest: dict, origination: dict, fixtures: list) -> dict:
    by_id = {str(m.get('id')): m for m in (latest.get('matches') or [])}
    out = {
        'probe': 'c03ef201 deep unresolved-fixture research probe',
        'generated_at': latest.get('generated_at'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'inventory_counts': latest.get('counts'),
        'coverage_complete': latest.get('coverage_complete'),
        'run_status': latest.get('run_status'),
        'inventory_crosscheck': latest.get('inventory_crosscheck'),
        'origination_generated_at': origination.get('generated_at'),
        'origination_counts': origination.get('counts'),
        'unresolved_ids': origination.get('unresolved_ids'),
        'unresolved_detail': [],
        'resolved_detail': [],
    }
    for row in origination.get('matches') or []:
        mid = str(row.get('id'))
        src = by_id.get(mid) or {}
        entry = {
            'id': mid,
            'teams': [t.get('name') for t in (src.get('teams') or row.get('teams') or [])],
            'competition': src.get('competition') or row.get('competition'),
            'starts_at': src.get('starts_at') or row.get('starts_at'),
            'origination': row.get('origination'),
            'research_trail': [
                {'stage': r.get('stage'), 'status': r.get('status'),
                 'detail': (r.get('detail') or '')[:400], 'source_url': r.get('source_url')}
                for r in (row.get('research') or [])],
            'hotspawn_source_url': src.get('source_url'),
        }
        if row.get('origination'):
            out['resolved_detail'].append(entry)
        else:
            out['unresolved_detail'].append(entry)
    out['blank_fixtures'] = fixtures
    return out


def run(live: bool = False) -> dict:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    manifest = []
    latest = load_json(ROOT / 'data' / 'latest.json')
    origination = load_json(ROOT / 'data' / 'origination.json')
    fixtures = blank_fixtures(latest, origination)
    deep = {
        'probe': 'c03ef201 provider deep probe (evidence only; never a pick)',
        'policy': ('Dated research evidence for fixtures the published ladder leaves blank. '
                   'HLTV first (official ranking and fixture identity), then esportsbook/betting-line '
                   'providers. Listing hits are observations for the reviewed rung work; this file '
                   'never writes a probability or fills a blank.'),
        'generated_at': iso(datetime.now(timezone.utc)),
        'blank_fixtures': fixtures,
        'hltv': hltv_probe(fixtures, manifest) if live else {'status': 'offline'},
        'pinnacle': pinnacle_probe(fixtures, manifest) if live else {'status': 'offline'},
        'x1bet': xbet_probe(fixtures, manifest) if live else {'status': 'offline'},
        'bo3gg': bo3gg_probe(fixtures, manifest) if live else {'status': 'offline'},
    }
    (OUT / 'provider-deep-probe.json').write_text(json.dumps(deep, ensure_ascii=False, indent=2) + '\n')
    summary = summarise(latest, origination, fixtures)
    (OUT / 'live-probe.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'request-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return {'summary': summary, 'deep': deep, 'manifest': manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='fetch providers (runner-side) instead of offline summarise')
    args = parser.parse_args()
    result = run(live=args.live)
    counts = result['summary'].get('inventory_counts') or {}
    print(json.dumps({'unresolved': len(result['summary']['unresolved_detail']),
                      'resolved': len(result['summary']['resolved_detail']),
                      'inventory_counts': counts,
                      'requests': len(result['manifest'])}, indent=2))
    print('::notice title=c03ef201 research probe::'
          + json.dumps({'unresolved': len(result['summary']['unresolved_detail']),
                        'requests_ok': sum(1 for r in result['manifest'] if r.get('status') == 'ok')}))


if __name__ == '__main__':
    main()
