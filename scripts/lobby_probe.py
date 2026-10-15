"""Read-only probe of how Hotspawn's lobby pages relate to the fixture API it calls.

Public GET requests only, no credentials, no bypasses. For several rounds it fetches the lobby page,
the CS2 lobby page and the fixture API, then records:
  * HTTP cache headers of each response (is the server-rendered HTML cached, and for how long?),
  * every API call embedded in the pages' Angular hydration state (the lobby's real endpoint surface),
  * the exact CS2 fixture-ID differences between the three sources, with the differing rows.

It exists to answer one question the collector can only answer with "disagree": WHY, when it does.
Usage: python -m scripts.lobby_probe [--rounds 3] [--pause 25] [--out path.json]
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import requests
from bs4 import BeautifulSoup

from scripts.sources import CS2_LOBBY, FIXTURES_API, LOBBY

HEADERS = ['Date', 'Age', 'Cache-Control', 'Expires', 'ETag', 'Last-Modified', 'CF-Cache-Status', 'X-Cache', 'Via', 'Server', 'Content-Type', 'Vary']
UA = {'User-Agent': 'HotspawnCS2Coverage/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)', 'Accept': 'application/json,text/html;q=0.9'}


def now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def get(url: str):
    started = now()
    response = requests.get(url, headers=UA, timeout=(15, 45))
    return response, started


def header_summary(response) -> dict:
    return {k: response.headers.get(k) for k in HEADERS if response.headers.get(k) is not None}


def state_entries(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    node = soup.find('script', id='ng-state')
    if not node:
        return []
    state = json.loads(node.get_text())
    out = []
    for key, value in state.items():
        if not isinstance(value, dict):
            continue
        url = value.get('u') or ''
        parsed = urlparse(url)
        body = value.get('b')
        keep = None
        if parsed.path == '/api/v1/week-prizes/widget' and isinstance(body, dict):
            keep = body
        elif parsed.path == '/api/v1/tenants/slug/hotspawn' and isinstance(body, dict):
            keep = {k: body.get(k) for k in ('features', 'games') if k in body}
        out.append({'path': parsed.path, 'query': dict(parse_qsl(parsed.query)), 'status': value.get('s'), 'kept_body': keep,
                    'body_type': type(body).__name__, 'records': len(body) if isinstance(body, (list, dict)) else None,
                    'body_keys': sorted(body.keys())[:12] if isinstance(body, dict) else None, '_body': body if isinstance(body, list) else None, '_body_all': body})
    return out


def cs2_rows(entries: list[dict]) -> list[dict]:
    lists = [e['_body'] for e in entries if e['path'] == '/api/v1/fixtures' and e['_body'] is not None]
    return [r for r in (lists[0] if lists else []) if isinstance(r, dict) and r.get('sport_alias') == 'cs2']


def brief(row: dict) -> dict:
    return {'id': str(row.get('id')), 'teams': [row.get('participants0_name'), row.get('participants1_name')], 'competition': row.get('competition_name'),
            'status': row.get('status'), 'start': datetime.fromtimestamp(int(row['scheduled_start_time']) / 1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if row.get('scheduled_start_time') else None,
            'tier': row.get('tier'), 'total_picks': row.get('total_picks')}


def one_round(bust: bool = False) -> dict:
    stamp = str(int(time.time()))
    lobby, t1 = get(LOBBY + ('?cb=' + stamp if bust else ''))
    cs2, t2 = get(CS2_LOBBY + ('?cb=' + stamp if bust else ''))
    api, t3 = get(FIXTURES_API)
    lobby_entries, cs2_entries = state_entries(lobby.text), state_entries(cs2.text)
    api_rows = [r for r in api.json() if isinstance(r, dict) and r.get('sport_alias') == 'cs2']
    sources = {'lobby': cs2_rows(lobby_entries), 'cs2_lobby': cs2_rows(cs2_entries), 'api': api_rows}
    ids = {k: {str(r['id']) for r in v} for k, v in sources.items()}
    by_id = {}
    for name in ('api', 'cs2_lobby', 'lobby'):
        for r in sources[name]:
            by_id.setdefault(str(r['id']), r)
    union = set().union(*ids.values())
    diffs = {}
    for name, own in ids.items():
        missing = sorted(union - own)
        if missing:
            diffs[name + '_lacks'] = [brief(by_id[i]) for i in missing]
    now_utc = datetime.now(timezone.utc).timestamp()
    return {
        'cache_busted': bust,
        'fetched_at': {'lobby': t1, 'cs2_lobby': t2, 'api': t3},
        'http': {'lobby': {'status': lobby.status_code, 'bytes': len(lobby.content), 'headers': header_summary(lobby)},
                 'cs2_lobby': {'status': cs2.status_code, 'bytes': len(cs2.content), 'headers': header_summary(cs2)},
                 'api': {'status': api.status_code, 'bytes': len(api.content), 'headers': header_summary(api)}},
        'counts': {k: len(v) for k, v in ids.items()},
        'agree': len({frozenset(v) for v in ids.values()}) == 1,
        'differences': diffs,
        'api_status_counts': {s: sum(1 for r in api_rows if r.get('status') == s) for s in sorted({r.get('status') for r in api_rows}, key=str)},
        'api_future_start': sum(1 for r in api_rows if r.get('scheduled_start_time') and int(r['scheduled_start_time']) / 1000 > now_utc),
        'hydration_calls': {'lobby': [{k: v for k, v in e.items() if k not in ('_body', '_body_all')} for e in lobby_entries], 'cs2_lobby': [{k: v for k, v in e.items() if k not in ('_body', '_body_all')} for e in cs2_entries]},
    }


TOURNAMENT_PAGES = ['https://play.hotspawn.com/tournaments', 'https://play.hotspawn.com/tournaments/thunderpick-world-championships']


def tournament_probe() -> list[dict]:
    """The tournament pick'em pages: which API calls they hydrate and what the embedded bodies hold."""
    out = []
    for url in TOURNAMENT_PAGES:
        try:
            response, fetched = get(url + '?cb=' + str(int(time.time())))
            entries = state_entries(response.text)
            calls = []
            for e in entries:
                body = e.get('_body')
                calls.append({'path': e['path'], 'query': e['query'], 'status': e['status'], 'records': e['records'], 'body_type': e['body_type'], 'body_keys': e['body_keys'],
                              'sample': body[:2] if isinstance(body, list) else None})
            out.append({'url': url, 'fetched_at': fetched, 'status': response.status_code, 'headers': header_summary(response), 'bytes': len(response.content), 'calls': calls,
                        'hydrated_bodies': {e['path']: e['_body_all'] for e in entries if e.get('_body_all') is not None and len(json.dumps(e['_body_all'])) < 60000}})
        except Exception as exc:
            out.append({'url': url, 'error': f'{type(exc).__name__}: {exc}'})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--pause', type=float, default=25)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    rounds = []
    for i in range(args.rounds + 2):
        if i:
            time.sleep(args.pause if i < args.rounds else 3)
        bust = i >= args.rounds  # the last two rounds ask for a fresh render with a cache-busting query string
        try:
            rounds.append(one_round(bust))
        except Exception as exc:  # a failed round is evidence too
            rounds.append({'error': f'{type(exc).__name__}: {exc}', 'at': now()})
    plain = [r for r in rounds if 'error' not in r and not r.get('cache_busted')]
    busted = [r for r in rounds if 'error' not in r and r.get('cache_busted')]
    report = {'schema_version': 1, 'probe': 'scripts/lobby_probe.py', 'urls': {'lobby': LOBBY, 'cs2_lobby': CS2_LOBBY, 'fixture_api': FIXTURES_API}, 'rounds': rounds,
              'tournament_pages': tournament_probe(),
              'all_plain_rounds_agree': bool(plain) and all(r['agree'] for r in plain), 'all_busted_rounds_agree': bool(busted) and all(r['agree'] for r in busted)}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    for i, r in enumerate(rounds):
        if 'error' in r:
            print(f'::notice title=lobby-probe round {i}::ERROR {r["error"]}')
            continue
        cache = {k: {h: v['headers'].get(h) for h in ('Age', 'Cache-Control', 'CF-Cache-Status', 'X-Cache', 'Date') if v['headers'].get(h)} for k, v in r['http'].items()}
        print('::notice title=lobby-probe round %d::%s' % (i, json.dumps({'cache_busted': r['cache_busted'], 'agree': r['agree'], 'counts': r['counts'], 'api_status_counts': r['api_status_counts'], 'api_future_start': r['api_future_start'], 'cache': cache}, ensure_ascii=False)))
        for name, rows in r['differences'].items():
            print(f'::notice title=lobby-probe round {i} {name}::' + json.dumps(rows[:12], ensure_ascii=False))
        for source in ('lobby', 'cs2_lobby'):
            calls = [(c['path'], c['query'], c['status'], c['records']) for c in r['hydration_calls'][source]]
            if i == 0:
                print(f'::notice title=lobby-probe hydration {source}::' + json.dumps(calls, ensure_ascii=False)[:3000])
    for page in report['tournament_pages']:
        if 'error' in page:
            print('::notice title=lobby-probe tournament::ERROR ' + page['error'])
        else:
            print('::notice title=lobby-probe tournament %s::%s' % (page['url'].rsplit('/', 1)[-1], json.dumps([(c['path'], c['query'], c['status'], c['records'], c['body_keys']) for c in page['calls']], ensure_ascii=False)[:3000]))
    print('::notice title=lobby-probe verdict::plain_agree=%s busted_agree=%s' % (report['all_plain_rounds_agree'], report['all_busted_rounds_agree']))


if __name__ == '__main__':
    main()
