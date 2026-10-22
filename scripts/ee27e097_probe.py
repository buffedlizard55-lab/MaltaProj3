"""Read-only network probe for session ee27e097 (external lines for model-only fixtures).

Nothing in this module prices a fixture, writes a pick or edits published data.  It
fetches a small, explicit list of public pages from the GitHub runner, records the
HTTP status, size, selected headers and a bounded excerpt, and (when asked) the
accessibility of the page's embedded JSON.  The result is committed by the
branch-scoped workflow so a human can review exactly what the runner saw.

Usage:
    python -m scripts.ee27e097_probe --out data/research/ee27e097
    python -m scripts.ee27e097_probe --out ... --browser     # Playwright fallback
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

UTC = timezone.utc

BROWSER_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
}

TARGETS = [
    ('egamersworld-listing', 'https://egamersworld.com/counterstrike/matches'),
    ('egamersworld-match-page',
     'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/bushido-wildcats-vs-ex-6666-Xs452MP7y'),
    ('betexplorer-cs2', 'https://www.betexplorer.com/esports/counter-strike-2/'),
    ('oddspedia-cs2', 'https://oddspedia.com/esports/counter-strike'),
    ('oddsportal-cs2', 'https://www.oddsportal.com/esports/counter-strike/'),
    ('hltv-matches', 'https://www.hltv.org/matches'),
    ('bo3-gg-matches', 'https://bo3.gg/matches'),
    ('hotspawn-lobby', 'https://play.hotspawn.com/lobby'),
]

HOTSPAWN_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
BO3_API = ('https://api.bo3.gg/api/v1/matches?page[offset]=0&page[limit]=100&sort=start_date'
           '&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1'
           '&with=teams,tournament')


def _probe(url: str, *, timeout: int = 20) -> dict:
    record = {'url': url, 'observed_at': datetime.now(UTC).isoformat(timespec='seconds')}
    try:
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - a probe records, never raises
        record.update({'status': None, 'error': f'{type(exc).__name__}: {exc}'[:300]})
        return record
    text = response.text or ''
    record.update({
        'status': response.status_code,
        'bytes': len(response.content or b''),
        'content_type': response.headers.get('content-type'),
        'server': response.headers.get('server'),
        'cf_ray': response.headers.get('cf-ray'),
        'title': (re.search(r'<title[^>]*>(.*?)</title>', text, re.I | re.S).group(1).strip()[:200]
                  if re.search(r'<title[^>]*>(.*?)</title>', text, re.I | re.S) else None),
        'has_next_data': '__NEXT_DATA__' in text,
        'has_nuxt': '__NUXT__' in text or 'window.__NUXT' in text,
        'length': len(text),
    })
    if response.status_code == 200:
        record['excerpt'] = text[:4000]
        lowered = text.lower()
        for token in ('average odds', 'bookmakers', 'coeff', '"odds"', 'make a bet'):
            record[f'has_{token.strip(chr(34)).replace(" ", "_")}'] = token in lowered
    return record


def _browser_probe(url: str) -> dict:
    record = {'url': url, 'mode': 'playwright', 'observed_at': datetime.now(UTC).isoformat(timespec='seconds')}
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        record['error'] = f'playwright unavailable: {type(exc).__name__}: {exc}'[:300]
        return record
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=['--no-sandbox'])
            context = browser.new_context(user_agent=BROWSER_HEADERS['User-Agent'],
                                          locale='en-US', timezone_id='UTC')
            page = context.new_page()
            response = page.goto(url, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(4000)
            text = page.inner_text('body')
            html = page.content()
            record.update({'status': response.status if response else None,
                           'bytes': len(html), 'text_length': len(text),
                           'text_excerpt': text[:6000]})
            browser.close()
    except Exception as exc:  # noqa: BLE001
        record['error'] = f'{type(exc).__name__}: {exc}'[:500]
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/research/ee27e097'))
    parser.add_argument('--browser', action='store_true', help='also probe EGamersWorld in Chromium')
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    observed = datetime.now(UTC).isoformat(timespec='seconds')
    document = {'session': 'ee27e097', 'observed_at': observed,
                'policy': ('Read-only accessibility probe. No price is converted into a pick here; '
                           'nothing is averaged, de-vigged or defaulted.'),
                'targets': [], 'bo3': None, 'fixtures': None}

    for name, url in TARGETS:
        record = _probe(url)
        record['name'] = name
        document['targets'].append(record)

    try:
        response = requests.get(BO3_API, headers={'Origin': 'https://bo3.gg', 'Referer': 'https://bo3.gg/',
                                                  'Accept': 'application/json'}, timeout=25)
        body = response.json() if response.status_code == 200 else None
        results = (body or {}).get('results') or []
        document['bo3'] = {
            'status': response.status_code,
            'rows': len(results),
            'with_bet_block': sum(1 for r in results if isinstance(r.get('bet_updates'), dict)),
            'sample': [{'slug': r.get('slug'), 'start': r.get('start_date'),
                        'teams': [(r.get('team1') or {}).get('name'), (r.get('team2') or {}).get('name')],
                        'bet_provider': (r.get('bet_updates') or {}).get('provider'),
                        'bet': r.get('bet_updates')} for r in results[:40]],
        }
        document['bo3_rows'] = [{'slug': r.get('slug'), 'start': r.get('start_date'),
                                 'tournament': (r.get('tournament') or {}).get('name'),
                                 'teams': [(r.get('team1') or {}).get('name'),
                                           (r.get('team2') or {}).get('name')],
                                 'team_ranks': [(r.get('team1') or {}).get('rank'),
                                                (r.get('team2') or {}).get('rank')],
                                 'bet_provider': (r.get('bet_updates') or {}).get('provider'),
                                 'bet': r.get('bet_updates')} for r in results]
    except Exception as exc:  # noqa: BLE001
        document['bo3'] = {'error': f'{type(exc).__name__}: {exc}'[:300]}

    try:
        response = requests.get(HOTSPAWN_API, timeout=25)
        body = response.json()
        matches = body if isinstance(body, list) else (body.get('data') or body.get('fixtures') or [])
        document['fixtures'] = {'status': response.status_code,
                                'count': len(matches) if isinstance(matches, list) else None,
                                'keys': sorted(matches[0].keys())[:30] if isinstance(matches, list) and matches
                                and isinstance(matches[0], dict) else None}
        (args.out / 'hotspawn-fixtures.json').write_text(json.dumps(body, indent=1) + '\n')
    except Exception as exc:  # noqa: BLE001
        document['fixtures'] = {'error': f'{type(exc).__name__}: {exc}'[:300]}

    if args.browser:
        document['browser'] = _browser_probe(TARGETS[0][1])

    stamp = datetime.now(UTC).strftime('%Y-%m-%dT%H%MZ')
    path = args.out / f'probe-{stamp}.json'
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'wrote': str(path),
                      'statuses': {t['name']: t.get('status') for t in document['targets']},
                      'bo3': {k: v for k, v in (document.get('bo3') or {}).items() if k != 'sample'},
                      'browser': {k: v for k, v in (document.get('browser') or {}).items()
                                  if k in ('status', 'bytes', 'error')}}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
