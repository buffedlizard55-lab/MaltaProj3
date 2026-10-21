"""Session arena-75de2710 — live release audit and unresolved-pick source probe.

Why this exists
---------------
The coding sandbox cannot reach Hotspawn, HLTV or any bookmaker. The GitHub
runner can. This read-only probe therefore runs there and records, with saved
original bytes and SHA-256 for every request:

1. the **deployed** GitHub Pages release (HTML + JSON) so the session can audit
   what is actually live instead of trusting a local build;
2. the **live Hotspawn fixture inventory** from the same public API the
   collector uses, reconciled by fixture id against the deployed snapshot;
3. for every fixture the deployed ladder left blank: its HLTV match page, both
   teams' HLTV pages, the official ranking pages (world, regional and the
   per-team ranking-details page) and every esportsbook / betting-line endpoint
   the project has or has not tried yet;
4. a provider reachability table with the provider's own status code, so a
   blocked endpoint is never reported as "no market exists".

Nothing here writes a probability, a pick or an alias. It only records what
the sources returned; the reviewed ladder in ``scripts/originate.py`` remains
the single code path allowed to publish an estimate.

Usage:  python -m scripts.s75de2710_probe --live
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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / '75de2710'
EVIDENCE = OUT / 'evidence'
UA = 'HotspawnCS2Research/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'

LIVE = 'https://buffedlizard55-lab.github.io/MaltaProj3'
FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?'
                'sport_alias=cs2&status=scheduled&tenantId=1')
HLTV_RANKING = 'https://www.hltv.org/ranking/teams'
HLTV_REGIONS = [
    'https://www.hltv.org/ranking/teams/2026/october/19/country/Europe',
    'https://www.hltv.org/ranking/teams/2026/october/19/country/South%20America',
    'https://www.hltv.org/ranking/teams/2026/october/19/country/North%20America',
    'https://www.hltv.org/ranking/teams/2026/october/19/country/Asia',
    'https://www.hltv.org/ranking/teams/2026/october/19/country/Oceania',
]
PINNACLE = 'https://guest.api.arcadia.pinnacle.com/0.1'
THUNDERPICK = 'https://thunderpick.io/api/matches'
BOVADA = ('https://www.bovada.lv/services/sports/event/coupon/events/A/description/'
          'esports/counter-strike-2?marketFilterId=def&preMatchOnly=true&lang=en')
KALSHI = ('https://api.elections.kalshi.com/trade-api/v2/events?status=open&series_ticker=KXCS2GAME')
POLY_SEARCH = 'https://gamma-api.polymarket.com/events?closed=false&limit=100&tag=esports'
X1BET = 'https://1xbet.com/LineFeed/Get1x2_VZip?sports=71&count=500&mode=4&getEmpty=true'
X1BET_PAGE = 'https://1xbet.com/en/line/Esports'
BOOK_PROBES = [
    ('ggbet-page', 'https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike'),
    ('ggbet-api', 'https://gg.bet/api/v1/line/esports/counter-strike'),
    ('rivalry-api', 'https://api.rivalry.com/sports/public/v1/sports?sport_key=esports_cs2&lang=en&region=ca&timezone=UTC&odds_format=decimal'),
    ('rivalry-matches', 'https://api.rivalry.com/sports/public/v1/matches?sport_key=esports_cs2&lang=en&region=ca&timezone=UTC&odds_format=decimal'),
    ('cloudbet-api', 'https://www.cloudbet.com/api/v1/sports/events?sport=counter-strike-2'),
    ('sportsbetio-api', 'https://api.sportsbet.io/v1/sports/esports'),
    ('betonline-api', 'https://api.betonline.ag/v1/sports/esports'),
    ('oddspedia-cs2', 'https://oddspedia.com/esports/counter-strike'),
    ('oddspedia-api', 'https://oddspedia.com/api/v1/getMatchList?sport=counter-strike&limit=100'),
    ('egamersworld', 'https://egamersworld.com/counterstrike/matches'),
    ('bo3gg-api-matches', 'https://api.bo3.gg/api/v1/matches?page[offset]=0&page[limit]=50&sort=start_date&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1&with=teams,tournament'),
    ('stake-api', 'https://stake.com/api/sports/esports/counter-strike'),
    ('betway-api', 'https://sports.betway.com/api/v1/esports/counter-strike'),
    ('unibet-api', 'https://www.unibet.com/betting/api/api/sports/esports'),
]
MAX_BODY = 12_000_000


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def fetch(label: str, url: str, manifest: list, *, method='GET', payload=None,
          timeout=(15, 45), save=True) -> tuple[bytes | None, dict]:
    entry = {'id': label, 'url': url, 'method': method, 'observed_at': now_iso(),
             'http_status': None, 'status': 'error'}
    manifest.append(entry)
    try:
        resp = requests.request(method, url, json=payload, timeout=timeout,
                                headers={'User-Agent': UA,
                                         'Accept': 'application/json,text/html;q=0.9',
                                         'Accept-Encoding': 'gzip, deflate'},
                                allow_redirects=True)
        body = resp.content
        entry.update(http_status=resp.status_code, final_url=resp.url,
                     content_type=resp.headers.get('Content-Type'),
                     bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        if len(body) > MAX_BODY:
            entry['error'] = 'response exceeds 12 MB safety limit; body not stored'
            return None, entry
        if resp.status_code >= 400:
            entry['error'] = f'HTTP {resp.status_code}'
        else:
            entry['status'] = 'ok'
        if save and body:
            name = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')
            path = EVIDENCE / (name + '.gz')
            path.write_bytes(gzip.compress(body, 9))
            entry['evidence'] = str(path.relative_to(ROOT))
        return body, entry
    except Exception as exc:  # noqa: BLE001 - every failure is recorded, none fatal
        entry['error'] = f'{type(exc).__name__}: {exc}'[:300]
        return None, entry


def json_body(body):
    if not body:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return None


def text_body(body):
    return body.decode('utf-8', 'replace') if body else ''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', action='store_true', help='perform the read-only network probe')
    args = ap.parse_args()
    if not args.live:
        ap.error('--live is required (this module never runs against saved data)')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    manifest: list = []
    report: dict = {'schema_version': 1, 'session': 'arena-75de2710',
                    'generated_at': now_iso(),
                    'policy': ('Read-only GET/POST probes. Every response is saved and hashed. '
                               'No probability, pick or alias is written here. A blocked endpoint '
                               'is not evidence that no market exists.')}

    # 1. Deployed release.
    live = {}
    for name, path in (('index', ''), ('coverage', 'coverage/'), ('origination', 'origination/')):
        body, _ = fetch(f'live-{name}-html', LIVE + '/' + path, manifest)
        live[name + '_html'] = {'bytes': len(body or b''),
                                'sha256': hashlib.sha256(body or b'').hexdigest()}
        if name == 'index':
            html = text_body(body)
            m = re.search(r'id="stale-warning"[^>]*>', html)
            live['stale_warning_tag'] = m.group(0) if m else None
            live['stale_warning_hidden'] = bool(m and 'hidden' in m.group(0))
            live['mobile_nav'] = 'class="mobile-nav"' in html
            live['viewport'] = bool(re.search(r'name="viewport"', html))
    for name in ('latest.json', 'origination.json', 'row-source-audit.json', 'sources.json'):
        body, _ = fetch('live-' + name, f'{LIVE}/data/{name}', manifest)
        data = json_body(body)
        live[name] = {'bytes': len(body or b''), 'sha256': hashlib.sha256(body or b'').hexdigest(),
                      'parsed': isinstance(data, (dict, list))}
        if name == 'origination.json' and isinstance(data, dict):
            live['counts'] = data.get('counts')
            live['generated_at'] = data.get('generated_at')
            live['live_collection'] = data.get('live_collection')
    report['live_release'] = live

    origination = json_body(fetch('live-origination-copy', f'{LIVE}/data/origination.json',
                                  manifest, save=False)[0]) or {}
    live_matches = {str(m.get('id')): m for m in (origination.get('matches') or [])}
    if not live_matches:
        report['error'] = 'deployed origination.json could not be parsed; unresolved probe skipped'
        (OUT / 'probe.json').write_text(json.dumps(report, indent=1) + '\n')
        return 1

    # 2. Live Hotspawn inventory (same public API the collector uses).
    api_body, api_entry = fetch('hotspawn-fixtures', FIXTURES_API, manifest)
    api = json_body(api_body) or {}
    api_rows = api if isinstance(api, list) else (api.get('data') or api.get('fixtures') or [])
    api_ids = {str(r.get('id')) for r in api_rows if isinstance(r, dict)}
    report['inventory'] = {
        'api_status': api_entry.get('status'),
        'api_http_status': api_entry.get('http_status'),
        'api_records': len(api_rows),
        'deployed_active_ids': sorted(i for i, m in live_matches.items()
                                      if m.get('availability') in {'open', 'locked', 'unknown_lock'}),
        'missing_from_deployed': sorted(api_ids - set(live_matches)),
        'stale_in_deployed': sorted(i for i in live_matches
                                    if i not in api_ids
                                    and live_matches[i].get('availability') in {'open', 'locked', 'unknown_lock'}),
    }

    # 3. Blank fixtures from the deployed ladder.
    blanks = []
    for mid, m in live_matches.items():
        if m.get('origination') is not None:
            continue
        if m.get('availability') not in {'open', 'locked', 'unknown_lock'}:
            continue
        trail = m.get('research') or []
        hltv_url = next((r.get('source_url') for r in trail
                         if str(r.get('source_url', '')).startswith('https://www.hltv.org/matches/')), None)
        blanks.append({'id': mid, 'teams': [t.get('name') for t in m.get('teams') or []],
                       'competition': m.get('competition'), 'starts_at': m.get('starts_at'),
                       'hltv_url': hltv_url, 'trail': trail})
    report['blank_fixtures'] = [{k: b[k] for k in ('id', 'teams', 'competition', 'starts_at', 'hltv_url')}
                                for b in blanks]

    # 4. HLTV per-blank research (official facts only).
    hltv_pages = {}
    for b in blanks:
        entry = {'match': None, 'team_pages': [], 'ranking_details': [], 'roster': None}
        if b['hltv_url']:
            html = text_body(fetch(f"hltv-match-{b['id']}", b['hltv_url'], manifest)[0])
            entry['match'] = {'url': b['hltv_url'], 'bytes': len(html),
                              'best_of': (re.search(r'Best of (\d)', html).group(1)
                                          if re.search(r'Best of (\d)', html) else None),
                              'finished': 'Match over' in html,
                              'rank_mentions': re.findall(r'(HLTV: #[0-9]+|VRS: #[0-9]+|HLTV: Unranked)', html)[:6],
                              'fan_vote_percentages': re.findall(r'>(\d{1,3}\.\d)%<', html)[:4],
                              'odds_terms': {term: html.lower().count(term)
                                             for term in ('betting odds', 'decimal odds', 'bookmaker', 'coefficient')},
                              'team_links': sorted(set(re.findall(r'https://www\.hltv\.org/team/\d+/[a-z0-9-]+', html)))}
            for i, team_url in enumerate(entry['match']['team_links'][:2]):
                team_html = text_body(fetch(f"hltv-team-{b['id']}-{i}", team_url, manifest)[0])
                m = re.search(r'# ([^<]+)</h1>', team_html)
                rank = re.search(r'World ranking</strong>\s*([^<]*)', team_html)
                entry['team_pages'].append({
                    'url': team_url, 'bytes': len(team_html),
                    'name': m.group(1).strip() if m else None,
                    'world_rank': rank.group(1).strip() if rank else None,
                    'no_roster': 'does not currently have a roster' in team_html,
                    'no_rank': "doesn't have a world rank" in team_html,
                    'recent_results_2026': len(re.findall(r'\b(?:0[1-9]|[12]\d|3[01])/10/2026\b', team_html)),
                })
                team_id = re.search(r'/team/(\d+)/', team_url)
                if team_id:
                    details = (f'https://www.hltv.org/ranking/teams/2026/october/19/details/{team_id.group(1)}')
                    dhtml = text_body(fetch(f"hltv-ranking-details-{b['id']}-{i}", details, manifest)[0])
                    pts = re.search(r'(\d+)\s*HLTV points', dhtml)
                    entry['ranking_details'].append({'url': details, 'bytes': len(dhtml),
                                                     'points': int(pts.group(1)) if pts else None,
                                                     'has_rank_block': 'HLTV points' in dhtml})
        hltv_pages[b['id']] = entry
    report['hltv'] = hltv_pages

    # 5. Official ranking publications, including regional tables the ladder
    #    does not read yet. Recorded as raw facts; nothing is priced here.
    ranking = {'world': None, 'regions': {}}
    world_html = text_body(fetch('hltv-ranking-world', HLTV_RANKING, manifest)[0])
    ranking['world'] = {'bytes': len(world_html),
                        'teams': len(re.findall(r'class="ranked-team', world_html))}
    for url in HLTV_REGIONS:
        region = url.rsplit('/', 1)[-1].replace('%20', ' ')
        html = text_body(fetch('hltv-ranking-' + region, url, manifest)[0])
        names = re.findall(r'class="name"[^>]*>\s*([^<]+)', html)
        ranking['regions'][region] = {'bytes': len(html), 'teams': len(names),
                                      'has_blank_team': any(key(n) in {key(t) for t in b['teams']}
                                                            for n in names for b in blanks)}
    report['ranking_pages'] = ranking

    # 6. Provider reachability and fixture presence.
    providers = {}
    # Pinnacle: the public guest board, exactly as scripts/pinnacle_lines.py reads it.
    matchups, me = fetch('pinnacle-matchups', f'{PINNACLE}/sports/12/matchups', manifest)
    leagues, _ = fetch('pinnacle-leagues', f'{PINNACLE}/sports/12/leagues', manifest)
    mrows = json_body(matchups) or []
    lrows = json_body(leagues) or []
    league_names = {str(r.get('id')): r.get('name') for r in lrows if isinstance(r, dict)}
    p_hits = {}
    for b in blanks:
        names = {key(t) for t in b['teams']}
        for row in mrows if isinstance(mrows, list) else []:
            parts = [p.get('name') for p in (row.get('participants') or []) if isinstance(p, dict)]
            if names & {key(p) for p in parts}:
                p_hits.setdefault(b['id'], []).append({
                    'participants': parts,
                    'league': league_names.get(str(row.get('leagueId')), row.get('leagueId')),
                    'start': row.get('startTime'), 'matchup_id': row.get('id')})
    providers['pinnacle'] = {'matchups_status': me.get('http_status'), 'matchup_rows': len(mrows),
                             'cs2_leagues': sorted(v for v in league_names.values() if v),
                             'blank_fixture_hits': p_hits}
    # Thunderpick: public read-only POST used by the collector.
    tp_body, tp = fetch('thunderpick', THUNDERPICK, manifest, method='POST', payload={'gameIds': [6]})
    tdata = json_body(tp_body)
    trows = tdata if isinstance(tdata, list) else ((tdata or {}).get('data') or [])
    tp_hits = {}
    for b in blanks:
        names = {key(t) for t in b['teams']}
        for row in trows if isinstance(trows, list) else []:
            if not isinstance(row, dict):
                continue
            sides = [s.get('name') for s in (row.get('participants') or row.get('teams') or []) if isinstance(s, dict)]
            if names & {key(s) for s in sides}:
                tp_hits.setdefault(b['id'], []).append({'participants': sides,
                                                        'start': row.get('startTime') or row.get('start_time'),
                                                        'id': row.get('id')})
    providers['thunderpick'] = {'status': tp.get('http_status'), 'rows': len(trows),
                                'blank_fixture_hits': tp_hits}
    # Bovada coupon.
    bv_body, bv = fetch('bovada', BOVADA, manifest)
    bvtext = text_body(bv_body)
    providers['bovada'] = {'status': bv.get('http_status'), 'bytes': len(bvtext),
                           'mentions': {b['id']: any(key(t) in key(bvtext) for t in b['teams'])
                                        for b in blanks}}
    # Kalshi.
    k_body, kst = fetch('kalshi-events', KALSHI, manifest)
    kevents = (json_body(k_body) or {}).get('events') or []
    providers['kalshi'] = {'status': kst.get('http_status'), 'events': len(kevents),
                           'tickers': [e.get('event_ticker') for e in kevents][:40]}
    # Polymarket discovery (identity only).
    pm_body, pst = fetch('polymarket-events', POLY_SEARCH, manifest)
    pmevents = json_body(pm_body) or []
    providers['polymarket'] = {'status': pst.get('http_status'),
                              'events': len(pmevents) if isinstance(pmevents, list) else None,
                              'mentions': {b['id']: sum(1 for e in (pmevents if isinstance(pmevents, list) else [])
                                                        if any(key(t) in key(json.dumps(e)) for t in b['teams']))
                                           for b in blanks}}
    # 1xBet line feed + page.
    x_body, xe = fetch('1xbet-linefeed', X1BET, manifest)
    xpage, xpe = fetch('1xbet-page', X1BET_PAGE, manifest)
    xdata = json_body(x_body) or {}
    xvals = xdata.get('Value') if isinstance(xdata, dict) else None
    providers['1xbet'] = {'linefeed_status': xe.get('http_status'), 'linefeed_bytes': xe.get('bytes'),
                          'linefeed_events': len(xvals) if isinstance(xvals, list) else None,
                          'page_status': xpe.get('http_status'), 'page_bytes': xpe.get('bytes'),
                          'page_mentions': {b['id']: any(key(t) in key(text_body(xpage)) for t in b['teams'])
                                            for b in blanks}}
    # The remaining candidate books: reachability only.
    for label, url in BOOK_PROBES:
        body, entry = fetch(label, url, manifest)
        providers[label] = {'status': entry.get('http_status'), 'bytes': entry.get('bytes'),
                            'error': entry.get('error'),
                            'blank_fixture_mentions': {b['id']: any(key(t) in key(text_body(body)) for t in b['teams'])
                                                       for b in blanks}}
    report['providers'] = providers

    # 7. Save.
    report['request_manifest'] = manifest
    (OUT / 'probe.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    lines = ['# Live probe (arena-75de2710)', '',
             f'Generated {report["generated_at"]}. Read-only; every response saved under '
             '`data/research/75de2710/evidence/`.', '',
             f'- Deployed counts: `{json.dumps(live.get("counts"))}`',
             f'- Deployed generated_at: `{live.get("generated_at")}`',
             f'- Hotspawn API records: {len(api_rows)}',
             f'- Blank fixtures: {len(blanks)}',
             f'- Stale-warning hidden on live page: {live.get("stale_warning_hidden")}',
             '', '## Blank fixtures', '']
    for b in blanks:
        lines.append(f"- {b['id']} — {b['teams'][0]} vs {b['teams'][1]} ({b['competition']}, {b['starts_at']})")
    lines += ['', '## Provider status', '']
    for name, value in providers.items():
        lines.append(f'- {name}: HTTP {value.get("status") or value.get("linefeed_status")} '
                     f'({value.get("bytes") or value.get("linefeed_bytes")} bytes)')
    lines += ['', '## HLTV team facts', '']
    for fid, entry in hltv_pages.items():
        for team in entry['team_pages']:
            lines.append(f"- {fid}: {team['name']} — world rank `{team['world_rank']}`, "
                         f"no roster: {team['no_roster']}, no rank: {team['no_rank']}, "
                         f"results in Oct 2026: {team['recent_results_2026']}")
    (OUT / 'probe.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
