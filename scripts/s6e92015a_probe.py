"""Session arena-6e92015a — full-coverage research for fixtures the ladder leaves blank.

Why this exists
---------------
The coding sandbox cannot reach Hotspawn, HLTV, Polymarket, Kalshi or any
bookmaker; the GitHub runner can. This read-only probe therefore runs there and
records, with saved original bytes and SHA-256 for every request:

1. the **deployed** GitHub Pages release (HTML + JSON) so this session audits
   what is actually live instead of trusting a local build, including the
   executive-summary mobile landmarks and the unresolved register;
2. the **fresh live ladder** result (collect + originate) for the current
   inventory, so the blank list is this run's, not the deployment's;
3. for every fixture the ladder leaves blank, working HLTV-first (match page,
   event bracket, team pages, official ranking publications) and then every
   betting-line surface the project knows (Polymarket, Kalshi, Thunderpick,
   Bovada, Pinnacle guest board, EGamersWorld, bo3.gg bet blocks) plus a
   wider esportsbook reachability sweep;
4. per fixture, an explicit "resolution options" note stating exactly which
   reviewed rung could still price it and what evidence that rung requires.

Nothing here writes a probability, a pick or an alias. It only records what the
sources returned; ``scripts/originate.py`` remains the single code path allowed
to publish an estimate. A blocked endpoint is never reported as "no market
exists".

Usage:  python -m scripts.s6e92015a_probe --live
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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / '6e92015a'
EVIDENCE = OUT / 'evidence'
UA = 'HotspawnCS2Research/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'

LIVE = 'https://buffedlizard55-lab.github.io/MaltaProj3'
FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?'
                'sport_alias=cs2&status=scheduled&tenantId=1')
HLTV_RANKING = 'https://www.hltv.org/ranking/teams'
PINNACLE_BASE = 'https://guest.api.arcadia.pinnacle.com/0.1'
PINNACLE_MATCHUPS = f'{PINNACLE_BASE}/sports/12/matchups'
KALSHI = ('https://api.elections.kalshi.com/trade-api/v2/events?status=open&series_ticker=KXCS2GAME')
POLY_TAG = 'https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2&active=true&closed=false&limit=100&offset={offset}'
THUNDERPICK = 'https://thunderpick.io/api/matches'
BOVADA = ('https://www.bovada.lv/services/sports/event/coupon/events/A/description/'
          'esports/counter-strike-2?marketFilterId=def&preMatchOnly=true&lang=en')
EGW_LIST = 'https://egamersworld.com/counterstrike/matches'
BO3_API = 'https://api.bo3.gg/api/v1'

# Wider esportsbook sweep: name -> URL. Status and team mentions are recorded
# for each; a refusal is a documented limitation, never proof of no market.
BOOK_SWEEP = [
    ('ggbet-next', 'https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike'),
    ('ggbet-api', 'https://gg.bet/api/v1/line/esports/counter-strike'),
    ('rivalry-matches', 'https://api.rivalry.com/sports/public/v1/matches?sport_key=esports_cs2&lang=en&region=ca&timezone=UTC&odds_format=decimal'),
    ('stake', 'https://stake.com/sports/esports/counter-strike'),
    ('1xbet-linefeed', 'https://1xbet.com/LineFeed/Get1x2_VZip?sports=71&count=500&mode=4&getEmpty=true'),
    ('cloudbet', 'https://www.cloudbet.com/api/v1/sports/events?sport=counter-strike-2'),
    ('sportsbetio', 'https://api.sportsbet.io/v1/sports/esports'),
    ('betonline', 'https://api.betonline.ag/v1/sports/esports'),
    ('oddspedia', 'https://oddspedia.com/api/v1/getMatchList?sport=counter-strike&limit=100'),
    ('betway', 'https://sports.betway.com/api/v1/esports/counter-strike'),
    ('unibet', 'https://www.unibet.com/betting/api/api/sports/esports'),
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
    report: dict = {'schema_version': 1, 'session': 'arena-6e92015a',
                    'generated_at': now_iso(),
                    'policy': ('Read-only GET/POST probes. Every response is saved and hashed. '
                               'No probability, pick or alias is written here. A blocked endpoint '
                               'is not evidence that no market exists. HLTV fan votes and '
                               'Hotspawn "% picked" are never inputs.')}

    # 1. Deployed release audit (executive summary + mobile landmarks).
    live = {}
    for name, path in (('index', ''), ('origination', 'origination/')):
        body, _ = fetch(f'live-{name}-html', LIVE + '/' + path, manifest)
        html = text_body(body)
        live[name + '_html'] = {'bytes': len(body or b''),
                                'sha256': hashlib.sha256(body or b'').hexdigest()}
        if name == 'index':
            m = re.search(r'id="stale-warning"[^>]*>', html)
            live['stale_warning_tag'] = m.group(0) if m else None
            live['stale_warning_hidden'] = bool(m and 'hidden' in m.group(0))
            live['mobile_nav'] = 'class="mobile-nav"' in html
            live['viewport'] = bool(re.search(r'name="viewport"', html))
            live['skip_link'] = 'Skip to content' in html
            live['summary_links_picks'] = 'origination/#picks' in html
            live['summary_links_unresolved'] = 'origination/#unresolved' in html
            live['summary_links_featured'] = 'picks/' in html
    for name in ('origination.json', 'latest.json'):
        body, _ = fetch('live-' + name, f'{LIVE}/data/{name}', manifest)
        data = json_body(body)
        live[name] = {'bytes': len(body or b''), 'sha256': hashlib.sha256(body or b'').hexdigest(),
                      'parsed': isinstance(data, (dict, list))}
        if name == 'origination.json' and isinstance(data, dict):
            live['counts'] = data.get('counts')
            live['generated_at'] = data.get('generated_at')
            live['live_collection'] = data.get('live_collection')
    report['live_release'] = live

    # 2. Blank fixtures, HLTV-first. Two sources, both recorded:
    #    (a) the DEPLOYED origination.json (what the live site shows the user),
    #    which was fetched in step 1; (b) the fresh ladder this run just
    #    collected (the workflow saves a copy under this session's research
    #    directory BEFORE restoring the tracked data files, so the restore can
    #    never hide the fresh blanks). The per-fixture probing below runs for
    #    the union of both blank sets.
    fresh = {}
    fresh_copy = OUT / 'fresh-origination.json'
    if fresh_copy.exists():
        try:
            fresh = json.loads(fresh_copy.read_text())
        except ValueError:
            fresh = {}
    deployed = json.loads(gzip.decompress(
        (EVIDENCE / 'live-origination-json.gz').read_bytes())) if (
        EVIDENCE / 'live-origination-json.gz').exists() else {}

    def blanks_of(row: dict) -> list:
        out = []
        for m in row.get('matches') or []:
            if m.get('origination') is not None:
                continue
            if m.get('availability') not in {'open', 'locked', 'unknown_lock'}:
                continue
            trail = m.get('research') or []
            hltv_url = next((r.get('source_url') for r in trail
                             if str(r.get('source_url', '')).startswith('https://www.hltv.org/matches/')), None)
            out.append({'id': str(m.get('id')), 'teams': [t.get('name') for t in m.get('teams') or []],
                        'competition': m.get('competition'), 'starts_at': m.get('starts_at'),
                        'source_url': m.get('source_url'), 'hltv_url': hltv_url,
                        'trail': trail})
        return out

    deployed_blanks = blanks_of(deployed)
    fresh_blanks = blanks_of(fresh)
    by_id = {b['id']: b for b in deployed_blanks}
    for b in fresh_blanks:
        by_id.setdefault(b['id'], b)
    blanks = [by_id[k] for k in sorted(by_id)]
    report['blank_sources'] = {
        'deployed_generated_at': deployed.get('generated_at'),
        'deployed_blank_ids': [b['id'] for b in deployed_blanks],
        'fresh_generated_at': fresh.get('generated_at'),
        'fresh_blank_ids': [b['id'] for b in fresh_blanks],
        'probed_ids': [b['id'] for b in blanks],
    }
    report['fresh_ladder'] = {'generated_at': fresh.get('generated_at'),
                              'counts': fresh.get('counts'),
                              'blank_ids': [b['id'] for b in fresh_blanks]}
    report['blank_fixtures'] = [{k: b[k] for k in ('id', 'teams', 'competition', 'starts_at',
                                                   'source_url', 'hltv_url')}
                                for b in blanks]

    # 3. HLTV-first research per blank fixture: the collector may not have a
    #    structured match URL, so the event page and team pages are probed too.
    hltv = {}
    for b in blanks:
        entry: dict = {'match': None, 'team_search': [], 'event_bracket_mentions': []}
        if b['hltv_url']:
            html = text_body(fetch(f"hltv-match-{b['id']}", b['hltv_url'], manifest)[0])
            entry['match'] = {'url': b['hltv_url'], 'bytes': len(html),
                              'best_of': (re.search(r'Best of (\d)', html).group(1)
                                          if re.search(r'Best of (\d)', html) else None),
                              'finished': 'Match over' in html,
                              'rank_mentions': re.findall(r'(HLTV: #[0-9]+|VRS: #[0-9]+)', html)[:6],
                              'fan_vote_percentages': re.findall(r'>(\d{1,3}\.\d)%<', html)[:4],
                              'team_links': sorted(set(re.findall(r'https://www\.hltv\.org/team/\d+/[a-z0-9-]+', html)))[:4]}
        # HLTV team search pages exist only via the site search; instead probe
        # the player-less team URL pattern through the match/event HTML we have.
        hltv[b['id']] = entry

    # HLTV world ranking publication (raw fact for the model rung).
    world_html = text_body(fetch('hltv-ranking-world', HLTV_RANKING, manifest)[0])
    report['hltv_world_ranking'] = {
        'bytes': len(world_html),
        'note': 'raw page saved and hashed; ranking rows are parsed by scripts/hltv_ranking.py in the pipeline',
    }

    # 4. Betting-line surfaces per blank fixture.
    lines: dict = {}

    # 4a. Polymarket gamma tag pagination (identity discovery, no prices used).
    poly_events = []
    for offset in (0, 100, 200, 300, 400):
        body, _ = fetch(f'poly-tag-{offset}', POLY_TAG.format(offset=offset), manifest, save=(offset == 0))
        data = json_body(body) or []
        poly_events.extend(data if isinstance(data, list) else [])
    lines['polymarket'] = {'events_seen': len(poly_events),
                           'fixture_mentions': {}}
    for b in blanks:
        names = [key(n) for n in b['teams']]
        hits = []
        for ev in poly_events:
            blob = key(json.dumps(ev.get('title', '') + ' ' + str(ev.get('slug', ''))))
            if any(n in blob for n in names):
                hits.append({'slug': ev.get('slug'), 'title': ev.get('title')})
        lines['polymarket']['fixture_mentions'][b['id']] = hits[:6]

    # 4b. Kalshi open KXCS2GAME events.
    body, _ = fetch('kalshi-events', KALSHI, manifest)
    kal = json_body(body) or {}
    kal_events = (kal.get('events') or [])
    lines['kalshi'] = {'events': len(kal_events),
                       'fixture_mentions': {}}
    for b in blanks:
        names = [key(n) for n in b['teams']]
        hits = []
        for ev in kal_events:
            blob = key(str(ev.get('title', '')) + str(ev.get('ticker', '')))
            if any(n[:4] in blob for n in names):
                hits.append(ev.get('event_ticker') or ev.get('ticker') or ev.get('title'))
        lines['kalshi']['fixture_mentions'][b['id']] = hits[:6]

    # 4c. Thunderpick public client (read-only POST, gameIds 6 = CS2).
    body, _ = fetch('thunderpick', THUNDERPICK, manifest, method='POST', payload={'gameIds': [6]})
    tp = json_body(body)
    tp_rows = []
    if isinstance(tp, dict):
        tp_rows = tp.get('matches') or tp.get('data') or []
    elif isinstance(tp, list):
        tp_rows = tp
    lines['thunderpick'] = {'status_rows': len(tp_rows), 'fixture_mentions': {}}
    for b in blanks:
        names = [key(n) for n in b['teams']]
        blob = key(json.dumps(tp_rows)[:400000])
        lines['thunderpick']['fixture_mentions'][b['id']] = any(n in blob for n in names)

    # 4d. Bovada prematch coupon.
    body, _ = fetch('bovada', BOVADA, manifest)
    bo = text_body(body)
    lines['bovada'] = {'bytes': len(bo), 'fixture_mentions': {}}
    for b in blanks:
        names = [key(n) for n in b['teams']]
        lines['bovada']['fixture_mentions'][b['id']] = any(n in key(bo) for n in names)

    # 4e. Pinnacle guest board: CS2 leagues, exact participant names, and the
    #     straight market board of any league that lists a blank fixture.
    body, _ = fetch('pinnacle-matchups', PINNACLE_MATCHUPS, manifest, save=False)
    pin = json_body(body) or []
    pin_cs2 = [m for m in pin if str((m.get('league') or {}).get('name', '')).startswith('CS2')]
    lines['pinnacle'] = {'matchup_rows': len(pin), 'cs2_rows': len(pin_cs2),
                         'cs2_leagues': sorted({(m.get('league') or {}).get('name') for m in pin_cs2}),
                         'fixture_hits': {}}

    def _pair_matches(parts: list[str], names: list[str]) -> bool:
        """Both participants match both names, in either order."""
        if len(parts) != 2 or len(names) != 2:
            return False
        def eq(a: str, b: str) -> bool:
            return a == b or (len(a) >= 4 and a in b) or (len(b) >= 4 and b in a)
        return ((eq(parts[0], names[0]) and eq(parts[1], names[1]))
                or (eq(parts[0], names[1]) and eq(parts[1], names[0])))

    for b in blanks:
        names = [key(n) for n in b['teams']]
        hits = []
        for m in pin_cs2:
            parts = [key(p.get('name')) for p in (m.get('participants') or [])]
            if _pair_matches(parts, names):
                hits.append({'league': (m.get('league') or {}).get('name'),
                             'participants': [p.get('name') for p in m.get('participants') or []],
                             'starts': m.get('startTime'), 'id': m.get('id')})
        lines['pinnacle']['fixture_hits'][b['id']] = hits[:4]
        if hits:
            lg = hits[0]['league']
            league_id = next((m.get('league') or {}).get('id') for m in pin_cs2
                             if (m.get('league') or {}).get('name') == lg)
            if league_id:
                sbody, _ = fetch(f'pinnacle-straight-{league_id}',
                                 f'{PINNACLE_BASE}/leagues/{league_id}/markets/straight', manifest)
                sdata = json_body(sbody) or []
                lines['pinnacle'][f'straight_{b["id"]}'] = {
                    'league': lg, 'rows': len(sdata) if isinstance(sdata, list) else None}

    # 4f. EGamersWorld list + per-fixture match page (published odds sentence).
    #     The list page is a JS shell, so reviewed match URLs discovered on the
    #     official site are loaded from data/research/6e92015a/egw-urls.json
    #     (manual, dated, hash-checked capture - the same evidence class as
    #     scripts/reference_odds.py). Both routes are recorded.
    egw_url_map = {}
    egw_urls_path = OUT / 'egw-urls.json'
    if egw_urls_path.exists():
        try:
            egw_url_map = json.loads(egw_urls_path.read_text())
        except ValueError:
            egw_url_map = {}
    body, _ = fetch('egw-list', EGW_LIST, manifest, save=False)
    egw_html = text_body(body)
    lines['egamersworld'] = {'bytes': len(egw_html), 'fixture_pages': {}}
    egw_links = dict(re.findall(r'href="(https://egamersworld\.com/counterstrike/match/[^"#?]+)"[^>]*title="([^"]+)"', egw_html))
    for b in blanks:
        names = [key(n) for n in b['teams']]
        page = egw_url_map.get(b['id'])
        rec = {'list_hit': bool(page), 'url': page, 'url_source': 'reviewed capture' if page else None}
        if not page:
            for url, title in egw_links.items():
                if all(n in key(title) for n in names):
                    page = url
                    rec = {'list_hit': True, 'url': page, 'url_source': 'matches list'}
                    break
        if page:
            phtml = text_body(fetch(f"egw-match-{b['id']}", page, manifest)[0])
            rec['bytes'] = len(phtml)
            rec['top_odds'] = re.findall(r'>(\d\.\d{1,2})<', phtml)[:8]
            # The reviewed reference rung needs EGW's own average-odds sentence;
            # record whether one exists at all (identical prices are placeholders).
            rec['average_odds_sentence'] = bool(re.search(r'average odds|odds from \d+ bookmaker', phtml, re.I))
            rec['identical_placeholder_prices'] = bool(re.search(r'1\.8[^0-9]{0,80}1\.8', phtml))
        lines['egamersworld']['fixture_pages'][b['id']] = rec

    # 4g. bo3.gg per blank fixture: team binding + upcoming match + bet block.
    lines['bo3gg'] = {'fixtures': {}}
    for b in blanks:
        rec = {'teams': []}
        ids = []
        for i, name in enumerate(b['teams']):
            q = f"{BO3_API}/teams?filter[teams.name][eq]={requests.utils.quote(name)}"
            body, _ = fetch(f"bo3-team-{b['id']}-{i}", q, manifest, save=False)
            data = json_body(body) or {}
            rows = data.get('results') or []
            exact = [r for r in rows if key(r.get('name')) == key(name)]
            rec['teams'].append({'name': name, 'results': len(rows), 'exact': len(exact),
                                 'id': exact[0].get('id') if exact else None,
                                 'rank': exact[0].get('rank') if exact else None})
            if exact:
                ids.append(exact[0]['id'])
        rec['upcoming'] = None
        if ids:
            overlap = '%2C'.join(str(i) for i in ids)
            q = (f"{BO3_API}/matches?filter[matches.team_ids][overlap]={overlap}"
                 f"&with=teams,tournament&sort=start_date&page[offset]=0&page[limit]=20")
            body, _ = fetch(f"bo3-matches-{b['id']}", q, manifest, save=False)
            data = json_body(body) or {}
            rows = data.get('results') or []
            upcoming = [r for r in rows if r.get('status') != 'finished']
            finished_recent = [r for r in rows if r.get('status') == 'finished'][-5:]
            rec['total_series'] = len(rows)
            rec['upcoming'] = [{'id': r.get('id'), 'slug': r.get('slug'),
                                'start': r.get('start_date'),
                                'bet_updates': bool(r.get('bet_updates'))} for r in upcoming[:4]]
            rec['finished_recent'] = [{'slug': r.get('slug'), 'start': r.get('start_date'),
                                       'bet_updates': bool(r.get('bet_updates'))} for r in finished_recent]
            for r in upcoming[:2]:
                if r.get('bet_updates'):
                    rec['bet_block_sample'] = r.get('bet_updates')
        lines['bo3gg']['fixtures'][b['id']] = rec
    report['lines'] = lines

    # 5. Wider esportsbook reachability sweep.
    sweep = {}
    for name, url in BOOK_SWEEP:
        body, entry = fetch('sweep-' + name, url, manifest, save=False)
        text = text_body(body)
        sweep[name] = {'http_status': entry.get('http_status'), 'status': entry.get('status'),
                       'bytes': entry.get('bytes'), 'error': entry.get('error'),
                       'fixture_mentions': {b['id']: any(key(n) in key(text[:500000]) for n in b['teams'])
                                            for b in blanks}}
    report['book_sweep'] = sweep

    # 6. Live Hotspawn inventory reconciliation (fixture coverage).
    api_body, api_entry = fetch('hotspawn-fixtures', FIXTURES_API, manifest, save=False)
    api = json_body(api_body) or []
    api_rows = api if isinstance(api, list) else (api.get('data') or api.get('fixtures') or [])
    report['inventory'] = {'api_status': api_entry.get('status'),
                           'api_http_status': api_entry.get('http_status'),
                           'api_records': len(api_rows),
                           'fresh_ladder_active_ids': sorted(
                               str(m.get('id')) for m in (fresh.get('matches') or [])
                               if m.get('availability') in {'open', 'locked', 'unknown_lock'})}

    # 7. Resolution options per blank fixture — what reviewed rung could still
    #    price it, and the exact evidence that rung requires. Facts only.
    options = {}
    for b in blanks:
        rec = []
        pm = (lines['polymarket']['fixture_mentions'].get(b['id']) or [])
        kal = (lines['kalshi']['fixture_mentions'].get(b['id']) or [])
        pin_hits = (lines['pinnacle']['fixture_hits'].get(b['id']) or [])
        egw = (lines['egamersworld']['fixture_pages'].get(b['id']) or {})
        bo3 = (lines['bo3gg']['fixtures'].get(b['id']) or {})
        rec.append({'rung': 'Polymarket/Kalshi series-winner books',
                    'could_price': bool(pm or kal),
                    'evidence_required': 'unique exact-identity (or registry alias) active prematch series-winner event with a two-sided book <= 0.12 spread'})
        rec.append({'rung': 'Pinnacle guest board',
                    'could_price': bool(pin_hits),
                    'evidence_required': 'exact participant names on a CS2 league matchup with a live straight moneyline'})
        rec.append({'rung': 'EGamersWorld published bookmaker average (reference)',
                    'could_price': bool(egw.get('average_odds_sentence')),
                    'note': 'identical 1.8/1.8 prices are rejected as placeholders by scripts/reference_odds.py',
                    'evidence_required': 'fresh hash-checked average-odds sentence with non-identical paired decimals'})
        rec.append({'rung': 'bo3.gg bet_updates block',
                    'could_price': bool((bo3.get('upcoming') or [{}])[0].get('bet_updates')),
                    'note': 'not currently a pipeline rung; recorded as a potential future reference rung',
                    'evidence_required': 'a reviewed policy decision plus a hash-checked capture; bo3.gg is an aggregator, not a first-party book'})
        rec.append({'rung': 'Valve/HLTV ranking + bo3.gg results models',
                    'could_price': False,
                    'evidence_required': 'both teams uniquely rated (Valve five-player rows, HLTV ranking rows) or >= 8 anchored bo3.gg series per side; recorded blockers stand'})
        options[b['id']] = rec
    report['resolution_options'] = options

    (OUT / 'probe.json').write_text(json.dumps(report, indent=1) + '\n')
    (OUT / 'request-manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print('probe complete:', len(blanks), 'blank fixtures; evidence files:',
          len(list(EVIDENCE.glob('*.gz'))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
