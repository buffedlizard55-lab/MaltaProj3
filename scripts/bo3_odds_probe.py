"""Session 1fb85c47 — does bo3.gg publish a bookmaker price for each blank fixture?

bo3.gg is reachable from the GitHub runner (HLTV is not: every HLTV path answers
Cloudflare HTTP 403, see data/research/1fb85c47/netcheck.txt). bo3.gg's public
match objects sometimes carry a ``bet_updates`` block with a named bookmaker and
decimal coefficients for both teams.

This module is a read-only probe. It never writes a probability, a pick or an
alias. For every fixture the origination ladder left blank it records:

* how the fixture was bound on bo3.gg (team ids + start time),
* whether a priced ``bet_updates`` block exists, the provider name and the exact
  coefficients,
* the bookmaker deep link bo3.gg publishes, and the bo3.gg match URL.

Usage: python -m scripts.bo3_odds_probe
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / '1fb85c47' / 'bo3-odds.json'
API = 'https://api.bo3.gg/api/v1'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def get(path: str) -> dict:
    req = urllib.request.Request(API + path,
                                 headers={'User-Agent': UA, 'Accept': 'application/json',
                                          'Origin': 'https://bo3.gg', 'Referer': 'https://bo3.gg/'})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode('utf-8', 'replace'))


def key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (value or '').casefold())


def team_id(name: str) -> dict:
    query = ('/teams?page[offset]=0&page[limit]=5&filter[teams.name][eq]='
             + urllib.parse.quote(name, safe=''))
    try:
        payload = get(query)
    except Exception as exc:  # noqa: BLE001 - recorded, never fatal
        return {'error': f'{type(exc).__name__}: {exc}'[:160]}
    rows = payload.get('results') or []
    exact = [r for r in rows if key(r.get('name') or '') == key(name)]
    out = {'matches': len(rows), 'exact': len(exact)}
    if exact:
        out.update({'id': exact[0]['id'], 'name': exact[0]['name'], 'slug': exact[0]['slug'],
                    'rank': exact[0].get('rank')})
    return out


def upcoming(team: int) -> list[dict]:
    query = ('/matches?page[offset]=0&page[limit]=10&sort=start_date'
             '&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1'
             f'&filter[matches.team_ids][overlap]={team}&with=teams,tournament')
    try:
        payload = get(query)
    except Exception as exc:  # noqa: BLE001
        return [{'error': f'{type(exc).__name__}: {exc}'[:160]}]
    return payload.get('results') or []


def bet_block(match: dict) -> dict | None:
    bet = match.get('bet_updates')
    if not isinstance(bet, dict):
        return None
    out = {'provider': bet.get('provider'), 'bet_provider_id': bet.get('bet_provider_id'),
           'path': bet.get('path'), 'markets_count': bet.get('markets_count')}
    for side in ('team_1', 'team_2'):
        row = bet.get(side) or {}
        out[side] = {'name': row.get('name'), 'coeff': row.get('coeff'),
                     'active': row.get('active'), 'team_id': row.get('team_id')}
    return out


def main() -> int:
    origination = json.loads((ROOT / 'data' / 'origination.json').read_text())
    blanks = [m for m in origination.get('matches', [])
              if m.get('availability') != 'past'
              and (m.get('origination') is None or m['origination'].get('method') == 'model'
                   or m['origination'].get('probabilities') is None)]
    report = {'generated_at': now(), 'source': 'https://api.bo3.gg/api/v1',
              'policy': 'Read-only. Every coefficient is copied from the response. '
                        'No probability, pick or alias is written here.',
              'fixtures': []}
    for match in blanks:
        row = {'hotspawn_id': match['id'], 'teams': [t['name'] for t in match['teams']],
               'competition': match.get('competition'), 'starts_at': match.get('starts_at'),
               'team_lookup': [], 'bound': None, 'bet': None}
        ids = []
        for team in match['teams']:
            found = team_id(team['name'])
            row['team_lookup'].append({'name': team['name'], **found})
            if found.get('id'):
                ids.append(found)
        if ids:
            candidates = upcoming(ids[0]['id'])
            wanted = {key(n) for n in row['teams']}
            for candidate in candidates:
                names = {key((candidate.get('team1') or {}).get('name') or ''),
                         key((candidate.get('team2') or {}).get('name') or '')}
                if wanted == names:
                    row['bound'] = {'id': candidate.get('id'), 'slug': candidate.get('slug'),
                                    'start_date': candidate.get('start_date'),
                                    'tournament': (candidate.get('tournament') or {}).get('name'),
                                    'url': 'https://bo3.gg/matches/' + str(candidate.get('slug')),
                                    'team1': candidate.get('team1'), 'team2': candidate.get('team2')}
                    row['bet'] = bet_block(candidate)
                    break
            if row['bound'] is None:
                row['candidates_seen'] = [{'slug': c.get('slug'), 'start': c.get('start_date')}
                                          for c in candidates[:5]]
        report['fixtures'].append(row)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'path': str(OUT), 'fixtures': len(report['fixtures']),
                      'priced': sum(1 for f in report['fixtures'] if f['bet']),
                      'bound': sum(1 for f in report['fixtures'] if f['bound'])}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
