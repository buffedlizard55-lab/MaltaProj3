"""Session arena-15fc6bca — read-only ground-truth probe (never publishes a pick).

Why this exists
---------------
The coding sandbox has no egress to Hotspawn, HLTV, bo3.gg or any bookmaker, so
every live statement about coverage has to be made from a GitHub runner. This
module runs there, after ``scripts.collect`` and ``scripts.originate --live``,
and records:

* the exact per-fixture state the ladder produced (featured method, originated
  method, probabilities, pick, every research stage and its status),
* for every upcoming fixture, whether bo3.gg relays a two-sided bookmaker quote
  (provider, both decimal coefficients, suspension flag, deep link) and what
  bo3.gg's own team rank is for each side,
* the HTTP status of the sources the brief names, from the runner's own egress,
  so "unavailable from here" is never reported as "no market exists".

It writes no probability, no pick and no alias. Every value in the report is
copied from a source response or from the pipeline's own output; a missing value
stays ``null``.

Usage: python -m scripts.15fc6bca_probe
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / '15fc6bca'
LIVE = OUT / 'live'
BO3_API = 'https://api.bo3.gg/api/v1'
BO3_HEADERS = {'Origin': 'https://bo3.gg', 'Referer': 'https://bo3.gg/',
               'Accept': 'application/json', 'User-Agent': 'MaltaProj3-research/1.0 (+coverage probe)'}
UTC = timezone.utc


def get(url: str, *, headers: dict | None = None, timeout: int = 25) -> dict:
    """One bounded GET. Returns the status, the body (text) and a hash."""
    import hashlib
    req = Request(url, headers=headers or {'User-Agent': BO3_HEADERS['User-Agent']})
    started = datetime.now(UTC)
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read()
            return {'url': url, 'http_status': response.status,
                    'fetched_at': started.isoformat().replace('+00:00', 'Z'),
                    'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                    'body': body.decode('utf-8', 'replace')}
    except Exception as exc:  # noqa: BLE001 - status text is the finding
        detail = f'{type(exc).__name__}: {exc}'
        status = getattr(getattr(exc, 'code', None), 'real', None) or getattr(exc, 'code', None)
        return {'url': url, 'http_status': status if isinstance(status, int) else None,
                'fetched_at': started.isoformat().replace('+00:00', 'Z'),
                'error': detail[:400], 'body': None}


def key(name: str) -> str:
    from scripts.domain import name_key
    return name_key(name or '')


def ts(value):
    from scripts.domain import timestamp
    return timestamp(value)


def bo3_upcoming() -> tuple[list[dict], list[dict]]:
    rows, requests, pages = [], [], 0
    while pages < 4:
        query = ('/matches?page[offset]=' + str(pages * 100) + '&page[limit]=100&sort=start_date'
                 '&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1'
                 '&with=teams,tournament')
        result = get(BO3_API + query, headers=BO3_HEADERS)
        requests.append({k: result.get(k) for k in ('url', 'http_status', 'fetched_at', 'bytes', 'sha256', 'error')})
        if not result.get('body'):
            break
        chunk = (json.loads(result['body']) or {}).get('results') or []
        rows.extend(chunk)
        pages += 1
        if len(chunk) < 100:
            break
    return rows, requests


def bind(match: dict, rows: list[dict], alias_pairs: dict[str, set[str]]) -> dict:
    start = ts(match.get('starts_at'))
    names = set()
    for team in match.get('teams') or []:
        raw = key(team.get('name') or '')
        names.add(raw)
        names |= alias_pairs.get(raw, set())
    candidates = []
    for row in rows:
        other = ts(row.get('start_date'))
        if start is None or other is None:
            continue
        delta = abs((other - start).total_seconds())
        if delta > 5400:
            continue
        sides = {key((row.get('team1') or {}).get('name') or ''),
                 key((row.get('team2') or {}).get('name') or '')}
        if sides & names:
            candidates.append((delta, row))
    candidates.sort(key=lambda item: item[0])
    return {'candidates': len(candidates),
            'bound': candidates[0][1] if len(candidates) == 1 else None,
            'closest': [{'slug': c[1].get('slug'), 'start': c[1].get('start_date'),
                         'teams': [(c[1].get('team1') or {}).get('name'), (c[1].get('team2') or {}).get('name')],
                         'delta_min': round(c[0] / 60, 1)} for c in candidates[:3]],
            'ambiguous': len(candidates) > 1}


def relay(team1: dict, team2: dict, row: dict) -> dict:
    """Copy bo3.gg's relayed bookmaker quote exactly; never derive a price."""
    bu = row.get('bet_updates')
    out = {'match_slug': row.get('slug'), 'bo_type': row.get('bo_type'),
           'start_date': row.get('start_date'), 'tournament': (row.get('tournament') or {}).get('name'),
           'team1': {'id': (row.get('team1') or {}).get('id'), 'name': (row.get('team1') or {}).get('name'),
                     'rank': (row.get('team1') or {}).get('rank')},
           'team2': {'id': (row.get('team2') or {}).get('id'), 'name': (row.get('team2') or {}).get('name'),
                     'rank': (row.get('team2') or {}).get('rank')},
           'source_url': 'https://bo3.gg/matches/' + str(row.get('slug')),
           'quote': None}
    if not isinstance(bu, dict):
        return out
    sides = {}
    for side, book_side in (('team1', bu.get('team_1') or {}), ('team2', bu.get('team_2') or {})):
        sides[side] = {'team_id': book_side.get('team_id'), 'name': book_side.get('name'),
                       'coeff': book_side.get('coeff'), 'active': book_side.get('active')}
    # Align the book's sides to bo3.gg's team1/team2 using the team id bo3.gg itself prints.
    if (sides['team1'].get('team_id') and row.get('team2')
            and sides['team1']['team_id'] == (row.get('team2') or {}).get('id')):
        sides['team1'], sides['team2'] = sides['team2'], sides['team1']
    out['quote'] = {'provider': bu.get('provider'), 'book_url': bu.get('path'),
                    'updated_at': bu.get('updated_at') or bu.get('created_at'),
                    'team1': sides['team1'], 'team2': sides['team2']}
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    LIVE.mkdir(parents=True, exist_ok=True)
    latest = json.loads((ROOT / 'data' / 'latest.json').read_text())
    origination = {}
    path = ROOT / 'data' / 'origination.json'
    if path.exists():
        origination = json.loads(path.read_text())
    (LIVE / 'latest.json').write_text(json.dumps(latest, indent=1))
    (LIVE / 'origination.json').write_text(json.dumps(origination, indent=1))

    registry = json.loads((ROOT / 'data' / 'origination' / 'aliases.json').read_text())
    alias_pairs: dict[str, set[str]] = {}
    for entry in registry.get('entries') or []:
        alias_pairs.setdefault(key(entry.get('canonical') or ''), set()).add(key(entry.get('alias') or ''))
        alias_pairs.setdefault(key(entry.get('alias') or ''), set()).add(key(entry.get('canonical') or ''))

    now = datetime.now(UTC)
    upcoming = [m for m in latest.get('matches') or []
                if (ts(m.get('starts_at')) or now) > now]
    rows_by_id = {str(r.get('id')): r for r in (origination.get('matches') or [])}

    bo3_rows, bo3_requests = bo3_upcoming()

    fixtures = []
    for match in upcoming:
        row = rows_by_id.get(str(match.get('id'))) or {}
        origin = row.get('origination') or {}
        featured = match.get('analysis') or {}
        record = {
            'hotspawn_id': str(match.get('id')),
            'teams': [t.get('name') for t in match.get('teams') or []],
            'team_ids': [t.get('id') for t in match.get('teams') or []],
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'locks_at': match.get('locks_at'),
            'tier': match.get('tier'),
            'featured': {'method': featured.get('method'), 'probabilities': featured.get('probabilities'),
                         'pick_index': match.get('pick_index')} if featured else None,
            'originated': {'method': origin.get('method'), 'label': origin.get('label'),
                           'probabilities': origin.get('probabilities'), 'source': origin.get('source'),
                           'source_url': origin.get('source_url')} if origin else None,
            'pick_index': row.get('pick_index'),
            'trail': [{'stage': r.get('stage'), 'status': r.get('status')} for r in row.get('research') or []],
            'unresolved_details': [{'stage': r.get('stage'), 'detail': r.get('detail'), 'source_url': r.get('source_url')}
                                   for r in row.get('research') or [] if r.get('status') == 'unresolved'],
            'limitations': row.get('limitations'),
        }
        binding = bind(match, bo3_rows, alias_pairs)
        record['bo3'] = {'candidates': binding['candidates'], 'ambiguous': binding['ambiguous'],
                         'closest': binding['closest'], 'relay': None}
        if binding['bound']:
            record['bo3']['relay'] = relay(match['teams'][0], match['teams'][1], binding['bound'])
        fixtures.append(record)

    # Runner-egress checks for the sources the brief names. Status only: a page
    # that answers is not turned into a price here.
    sources = []
    for label, url in [
        ('Hotspawn lobby', 'https://play.hotspawn.com/lobby'),
        ('Hotspawn fixtures API', 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1'),
        ('HLTV matches', 'https://www.hltv.org/matches'),
        ('HLTV world ranking', 'https://www.hltv.org/ranking/teams'),
        ('bo3.gg API upcoming', BO3_API + '/matches?page[limit]=5&filter[matches.discipline_id][eq]=1'),
        ('EGamersWorld matches', 'https://egamersworld.com/counterstrike/matches'),
        ('Thunderpick matches API', 'https://thunderpick.io/api/matches'),
        ('Bovada CS2 coupon', 'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2'),
        ('Pinnacle guest CS2', 'https://guest.api.arcadia.pinnacle.com/0.1/sports/19/matchups'),
        ('Kalshi KXCS2GAME', 'https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXCS2GAME&limit=5'),
        ('Polymarket CS2 events', 'https://gamma-api.polymarket.com/events?series_id=10310&closed=false&limit=5'),
    ]:
        result = get(url)
        sources.append({'label': label, 'url': url, 'http_status': result.get('http_status'),
                        'bytes': result.get('bytes'), 'sha256': result.get('sha256'),
                        'error': result.get('error'), 'fetched_at': result.get('fetched_at')})
        time.sleep(0.4)

    report = {'schema': 1, 'session': 'arena-15fc6bca',
              'generated_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
              'snapshot': {'generated_at': latest.get('generated_at'),
                           'inventory_observed_at': latest.get('inventory_observed_at'),
                           'counts': latest.get('counts'),
                           'origination_counts': origination.get('counts')},
              'policy': 'Read-only ground truth. No probability, pick or alias is written by this probe.',
              'bo3_requests': bo3_requests, 'bo3_upcoming_rows': len(bo3_rows),
              'sources': sources, 'fixtures': fixtures}

    SUMMARY = OUT / 'coverage-probe.json'
    SUMMARY.write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')

    lines = ['# Session 15fc6bca coverage probe', '',
             f"Generated {report['generated_at']}. Snapshot `{latest.get('generated_at')}` "
             f"observed `{latest.get('inventory_observed_at')}`.",
             '', f"- Upcoming fixtures: **{len(fixtures)}**",
             f"- bo3.gg upcoming rows fetched: {len(bo3_rows)}",
             '', '| Fixture | Start | Method | Pick | bo3 relay | bo3 ranks |', '| --- | --- | --- | --- | --- | --- |']
    for f in fixtures:
        relay_block = (f.get('bo3') or {}).get('relay') or {}
        quote = relay_block.get('quote') or {}
        if quote.get('team1') and quote.get('team2'):
            relay_text = (f"{quote.get('provider')} "
                          f"{quote['team1'].get('coeff')}/{quote['team2'].get('coeff')} "
                          f"active={quote['team1'].get('active')}/{quote['team2'].get('active')}")
        else:
            relay_text = 'none' if relay_block else 'not bound'
        ranks = (f"{relay_block.get('team1', {}).get('rank')}/{relay_block.get('team2', {}).get('rank')}"
                 if relay_block else '')
        method = (f.get('originated') or {}).get('method') or 'unresolved'
        pick = f.get('pick_index')
        pick_text = f.get('teams')[pick] if pick is not None else '—'
        lines.append(f"| {' vs '.join(f.get('teams') or [])} | {f.get('starts_at')} | {method} | {pick_text} | {relay_text} | {ranks} |")
    (OUT / 'coverage-probe.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
