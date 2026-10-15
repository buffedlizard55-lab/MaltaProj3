"""Research probe (session c07e1b40): which public line sources cover unresolved fixtures?

Diagnostic only. Nothing written here is a probability input: the probe saves the
original responses of candidate first-party line sources and reports, for every
active Hotspawn fixture, which provider events *mention* the same team names, so a
reviewer (and the origination engine's strict exact/alias joins) can decide what is
usable. Name containment below is deliberately loose because it only drives this
report; it never prices anything.

Sources probed (public, unauthenticated, no challenge bypass):
  * Kalshi public market-data API (CFTC-regulated exchange), CS2 match series
    KXCS2GAME — https://docs.kalshi.com/api-reference/market/get-markets
  * Bovada public sportsbook coupon feed for Counter-Strike 2.

Run after `python -m scripts.collect` and `python -m scripts.originate --live`:
    python -m scripts.research_lines
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

from scripts.domain import iso, name_key

UTC = timezone.utc
OUT = Path('.cache/research')
KALSHI_EVENTS = 'https://api.elections.kalshi.com/trade-api/v2/events'
BOVADA_CS2 = ('https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2?'
              + urlencode({'marketFilterId': 'def', 'preMatchOnly': 'true', 'lang': 'en'}))
UA = 'HotspawnCS2Research/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'


def fetch(session, url, label, manifest):
    entry = {'id': label, 'url': url, 'observed_at': iso(datetime.now(UTC)), 'status': 'error'}
    manifest.append(entry)
    try:
        response = session.get(url, timeout=(15, 45))
        entry.update(http_status=response.status_code, final_url=response.url,
                     content_type=response.headers.get('Content-Type'),
                     response_sha256=hashlib.sha256(response.content).hexdigest(), bytes=len(response.content))
        response.raise_for_status()
        data = response.json()
        (OUT / f'{label}.json').write_text(json.dumps(data, ensure_ascii=False) + '\n')
        entry['status'] = 'ok'
        entry['evidence'] = f'.cache/research/{label}.json'
        return data
    except (requests.RequestException, ValueError) as exc:
        entry['error'] = str(exc)[:300]
        return None
    finally:
        time.sleep(0.4)


def kalshi(session, manifest):
    events, cursor = [], ''
    for page in range(10):
        query = {'series_ticker': 'KXCS2GAME', 'status': 'open', 'with_nested_markets': 'true', 'limit': 200}
        if cursor:
            query['cursor'] = cursor
        data = fetch(session, KALSHI_EVENTS + '?' + urlencode(query), f'kalshi-events-{page}', manifest)
        if not isinstance(data, dict):
            break
        events.extend(data.get('events') or [])
        cursor = data.get('cursor') or ''
        if not cursor:
            break
    return events


def bovada(session, manifest):
    data = fetch(session, BOVADA_CS2, 'bovada-cs2', manifest)
    out = []
    for group in data or []:
        for event in group.get('events', []) if isinstance(group, dict) else []:
            out.append(event)
    return out


def tokens(name):
    return {t for t in name_key(name or '').replace('.', ' ').split() if len(t) >= 3}


def mentions(team_names, text):
    text_key = name_key(text or '')
    hits = 0
    for name in team_names:
        key = name_key(name or '')
        if key and (key in text_key or (tokens(name) and tokens(name) <= set(text_key.split()))):
            hits += 1
    return hits


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept': 'application/json'})
    manifest = []
    latest = json.loads(Path('data/latest.json').read_text())
    origination = json.loads(Path('data/origination.json').read_text()) if Path('data/origination.json').exists() else {}
    orig_by_id = {m['id']: m for m in origination.get('matches', [])}
    k_events = kalshi(session, manifest)
    b_events = bovada(session, manifest)
    report = {'observed_at': iso(datetime.now(UTC)), 'inventory_observed_at': latest.get('inventory_observed_at'),
              'coverage_complete': latest.get('coverage_complete'), 'counts': latest.get('counts'),
              'origination_counts': origination.get('counts'), 'kalshi_events': len(k_events),
              'bovada_events': len(b_events), 'requests': manifest, 'fixtures': []}
    for match in latest.get('matches', []):
        if match.get('availability') == 'past':
            continue
        names = [t.get('name') or '' for t in match.get('teams', [])]
        orig = orig_by_id.get(match['id'], {})
        k_hits = []
        for ev in k_events:
            text = ' '.join([ev.get('title') or ''] + [m.get('yes_sub_title') or '' for m in ev.get('markets', [])])
            score = mentions(names, text)
            if score:
                k_hits.append({'score': score, 'event_ticker': ev.get('event_ticker'), 'title': ev.get('title'),
                               'rules': (ev.get('markets') or [{}])[0].get('rules_primary', '')[:220],
                               'quotes': [{k: m.get(k) for k in ['yes_sub_title', 'yes_bid_dollars', 'yes_ask_dollars', 'last_price_dollars', 'volume_fp', 'status']} for m in ev.get('markets', [])]})
        b_hits = []
        for ev in b_events:
            text = ' '.join([ev.get('description') or ''] + [c.get('name') or '' for c in ev.get('competitors', [])])
            score = mentions(names, text)
            if score:
                ml = []
                for group in ev.get('displayGroups', []):
                    for market in group.get('markets', []):
                        if market.get('description') == 'Moneyline' and (market.get('period') or {}).get('main'):
                            ml = [{'name': o.get('description'), 'decimal': (o.get('price') or {}).get('decimal'), 'status': o.get('status')} for o in market.get('outcomes', [])]
                b_hits.append({'score': score, 'id': ev.get('id'), 'description': ev.get('description'), 'link': ev.get('link'),
                               'start': iso(datetime.fromtimestamp(ev['startTime'] / 1000, UTC)) if isinstance(ev.get('startTime'), (int, float)) else None,
                               'live': ev.get('live'), 'moneyline': ml})
        report['fixtures'].append({
            'id': match['id'], 'teams': names, 'competition': match.get('competition'), 'starts_at': match.get('starts_at'),
            'availability': match.get('availability'), 'featured_method': (match.get('analysis') or {}).get('method'),
            'origination_method': (orig.get('origination') or {}).get('method'),
            'kalshi': sorted(k_hits, key=lambda h: -h['score'])[:4], 'bovada': sorted(b_hits, key=lambda h: -h['score'])[:4]})
    out = Path('.cache/research/report.json')
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    for req in manifest:
        print(f"::notice title=probe {req['id']}::{req.get('http_status')} {req['status']} {req.get('error', '')}")
    for fx in report['fixtures']:
        if fx['origination_method'] is None:
            print(f"::warning title=unresolved {fx['id']}::{' vs '.join(fx['teams'])} | {fx['competition']} | {fx['starts_at']} | "
                  f"kalshi={[h['event_ticker'] for h in fx['kalshi']]} bovada={[h['description'] for h in fx['bovada']]}")
    print(json.dumps({k: report[k] for k in ['observed_at', 'kalshi_events', 'bovada_events', 'counts', 'origination_counts']}, indent=2))


if __name__ == '__main__':
    main()
