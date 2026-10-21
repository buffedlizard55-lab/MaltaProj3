"""Session arena-541cd43a — read-only probe of HLTV, bo3.gg and esportsbook surfaces.

The brief for this session says: *try HLTV, then esportsbooks and esports betting
lines* for every fixture the featured ladder cannot price. This module performs
that research on the GitHub runner (the coding sandbox has no egress) and records
only what the sources answered:

* HLTV: the exact match page the ladder already verified, its HTTP status, size,
  content hash, the page title, whether a betting block is present, and whether
  both team names appear in the rendered text;
* bo3.gg: the fixture binding, any published ``bet_updates`` bookmaker block with
  its exact coefficients, and the number of finished series on each side (the
  sample the own-line results model can use);
* esportsbook and odds-aggregator surfaces, both generic CS2 pages and full-text
  searches for each team name, recording status, size, title and whether the team
  appears at all.

It never writes a probability, a pick, a price or an alias. Every observation is
evidence for the unresolved register and for the session's own-line model gates.

Usage: python -m scripts.s541cd43a_probe [--root .]
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
OUT_DIR = Path('data/research/541cd43a')
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
BO3_API = 'https://api.bo3.gg/api/v1'
BO3_HEADERS = {'User-Agent': UA, 'Accept': 'application/json',
               'Origin': 'https://bo3.gg', 'Referer': 'https://bo3.gg/'}
MAX_BYTES = 1_200_000

PROVIDER_PAGES = [
    ('EGamersWorld CS2 matches', 'https://egamersworld.com/counterstrike/matches'),
    ('EGamersWorld search', 'https://egamersworld.com/search?query={team}'),
    ('Oddspedia CS2', 'https://oddspedia.com/csgo'),
    ('Oddspedia search', 'https://oddspedia.com/search?q={team}'),
    ('Escorenews CS2', 'https://escorenews.com/en/csgo'),
    ('Escorenews search', 'https://escorenews.com/en/search?q={team}'),
    ('1xBet CS2 line', 'https://1xbet.com/Line/Counter-Strike-2'),
    ('GG.bet CS2', 'https://gg.bet/en/esports/counter-strike'),
    ('Betano CS2', 'https://www.betano.com/sport/esports/counter-strike-2/'),
    ('Betway CS2', 'https://betway.com/en/sports/grp/esports/counter-strike'),
    ('Unibet esports', 'https://www.unibet.com/betting/sports/filter/esports'),
    ('Betsson esports', 'https://www.betsson.com/en/odds/esports'),
    ('Thunderpick CS2', 'https://thunderpick.io/esports/counter-strike'),
    ('Pinnacle CS2', 'https://www.pinnacle.com/en/esports/counter-strike-2'),
    ('Bovada CS2', 'https://www.bovada.lv/sports/esports/counter-strike-2'),
    ('Kalshi CS2 series', 'https://kalshi.com/markets/kxcs2game/counter-strike-2-game'),
    ('Polymarket CS2', 'https://polymarket.com/esports/cs2'),
]


def iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).isoformat(timespec='seconds').replace('+00:00', 'Z')


def key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (value or '').casefold())


def fetch(url: str, *, headers: dict | None = None) -> dict:
    """Read a URL, return a manifest entry plus (optionally) decoded text."""
    request = urllib.request.Request(url, headers=headers or {'User-Agent': UA,
                                                              'Accept': 'text/html,application/xhtml+xml'})
    entry = {'url': url, 'observed_at': iso()}
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(MAX_BYTES)
            entry.update({'http_status': response.status,
                          'content_type': response.headers.get('Content-Type'),
                          'bytes': len(raw),
                          'sha256': hashlib.sha256(raw).hexdigest()})
    except urllib.error.HTTPError as exc:
        entry.update({'http_status': exc.code, 'error': f'HTTP {exc.code}'})
        return entry
    except Exception as exc:  # noqa: BLE001 - recorded, never fatal
        entry.update({'error': f'{type(exc).__name__}: {exc}'[:180]})
        return entry
    entry['text'] = raw.decode('utf-8', 'replace')
    return entry


def visible_text(html: str) -> str:
    text = re.sub(r'<script\b.*?</script>|<style\b.*?</style>', ' ', html, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text)


def get_json(path: str) -> tuple[dict | None, dict]:
    entry = fetch(BO3_API + path, headers=BO3_HEADERS)
    text = entry.pop('text', None)
    payload = None
    if text:
        try:
            payload = json.loads(text)
        except ValueError:
            entry['error'] = 'response was not JSON'
    return payload, entry


def bo3_team(name: str) -> dict:
    query = ('/teams?page[offset]=0&page[limit]=5&filter[teams.name][eq]='
             + urllib.parse.quote(name, safe=''))
    payload, entry = get_json(query)
    out = {'request': entry, 'matches': 0, 'exact': 0}
    rows = (payload or {}).get('results') or []
    exact = [r for r in rows if key(r.get('name') or '') == key(name)]
    out['matches'] = len(rows)
    out['exact'] = len(exact)
    if exact:
        out.update({'id': exact[0].get('id'), 'name': exact[0].get('name'),
                    'slug': exact[0].get('slug'), 'rank': exact[0].get('rank')})
    return out


def bo3_upcoming(team_id: int) -> list[dict]:
    payload, _ = get_json('/matches?page[offset]=0&page[limit]=10&sort=start_date'
                          '&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1'
                          f'&filter[matches.team_ids][overlap]={team_id}&with=teams,tournament')
    return (payload or {}).get('results') or []


def bo3_results(team_id: int, limit: int = 40) -> list[dict]:
    payload, _ = get_json('/matches?page[offset]=0&page[limit]=' + str(limit) + '&sort=-start_date'
                          '&filter[matches.status][in]=finished&filter[matches.discipline_id][eq]=1'
                          f'&filter[matches.team_ids][overlap]={team_id}&with=teams')
    return (payload or {}).get('results') or []


def bo3_bet_block(match: dict) -> dict | None:
    bet = match.get('bet_updates')
    if not isinstance(bet, dict):
        return None
    out = {'provider': bet.get('provider'), 'bet_provider_id': bet.get('bet_provider_id'),
           'path': bet.get('path'), 'markets_count': bet.get('markets_count')}
    for side in ('team_1', 'team_2'):
        row = bet.get(side) or {}
        out[side] = {'name': row.get('name'), 'coeff': row.get('coeff'), 'active': row.get('active')}
    return out


def graph_endpoint_probe() -> dict:
    """Validate the finished-match feed the own-line network model needs."""
    query = ('/matches?page[offset]=0&page[limit]=100&sort=-start_date'
             '&filter[matches.status][in]=finished&filter[matches.discipline_id][eq]=1&with=teams')
    payload, entry = get_json(query)
    rows = (payload or {}).get('results') or []
    teams = set()
    for row in rows:
        for side in ('team1', 'team2'):
            name = (row.get(side) or {}).get('name')
            if name:
                teams.add(key(name))
    return {'request': entry, 'rows': len(rows), 'distinct_teams': len(teams),
            'has_total': bool(payload and isinstance(payload.get('total'), (int, dict))),
            'sample': [{'id': r.get('id'), 'start_date': r.get('start_date'),
                        'team1': (r.get('team1') or {}).get('name'),
                        'team2': (r.get('team2') or {}).get('name'),
                        'winner_team_id': r.get('winner_team_id'),
                        'parsed_status': r.get('parsed_status')} for r in rows[:5]]}


def hltv_probe(url: str, teams: list[str]) -> dict:
    entry = fetch(url)
    text = entry.pop('text', None)
    out = {'request': entry}
    if text:
        title = re.search(r'<title>([^<]*)</title>', text)
        body = visible_text(text)
        out['title'] = title.group(1).strip() if title else None
        out['has_betting_block'] = bool(re.search(r'betting|bet now|odds', text, re.I))
        out['teams_present'] = {name: bool(re.search(re.escape(name), body, re.I)) for name in teams}
        out['blocked'] = 'Just a moment' in text or 'cf-browser-verification' in text
    return out


def main() -> int:
    root = Path('.').resolve()
    origination = json.loads((root / 'data/origination.json').read_text())
    latest = json.loads((root / 'data/latest.json').read_text()) if (root / 'data/latest.json').exists() else {}
    blanks = [m for m in origination.get('matches') or []
              if m.get('availability') != 'past' and m.get('origination') is None]
    teams_needed = {name for m in blanks for name in
                    [str((t or {}).get('name') or '') for t in m.get('teams') or []] if name}

    report = {
        'session': 'arena-541cd43a',
        'generated_at': iso(),
        'policy': ('Read-only research. No probability, pick, price or alias is written here. '
                   'Every value is the source response observed at the recorded time.'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'origination_counts': origination.get('counts'),
        'blank_fixtures': [],
        'bo3_graph_endpoint': graph_endpoint_probe(),
        'providers': [],
    }

    for match in blanks:
        teams = [str((t or {}).get('name') or '') for t in match.get('teams') or []]
        hltv_urls = sorted({r.get('source_url') for r in match.get('research') or []
                            if str(r.get('source_url') or '').startswith('https://www.hltv.org/matches/')})
        row = {
            'hotspawn_id': match.get('id'),
            'teams': teams,
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'hotspawn_source_url': match.get('source_url'),
            'hltv': [hltv_probe(url, teams) for url in hltv_urls] or
                    [{'request': {'url': 'https://www.hltv.org/matches', 'note': 'no verified HLTV match URL in trail'}}],
            'bo3': {},
        }
        lookups, ids = [], []
        for team in teams:
            found = bo3_team(team)
            lookups.append({'name': team, **found})
            if found.get('id'):
                ids.append(found)
        row['bo3']['team_lookup'] = lookups
        wanted = {key(name) for name in teams}
        binding = None
        if ids:
            for candidate in bo3_upcoming(ids[0]['id']):
                names = {key((candidate.get('team1') or {}).get('name') or ''),
                         key((candidate.get('team2') or {}).get('name') or '')}
                if names == wanted:
                    binding = candidate
                    break
        if binding:
            results = {}
            for side in ('team1', 'team2'):
                team = binding.get(side) or {}
                team_id = team.get('id')
                if not team_id:
                    continue
                finished = bo3_results(team_id)
                results[team.get('name')] = {
                    'finished_rows': len(finished),
                    'parsed_done': sum(1 for g in finished if g.get('parsed_status') == 'done'),
                    'with_winner': sum(1 for g in finished if g.get('winner_team_id')),
                    'first': min((str(g.get('start_date'))[:10] for g in finished), default=None),
                    'last': max((str(g.get('start_date'))[:10] for g in finished), default=None),
                    'opponents': sorted({str((g.get('team2') if g.get('team1_id') == team_id else g.get('team1') or {}).get('name'))
                                         for g in finished})[:40],
                }
            row['bo3'].update({
                'bound': {'id': binding.get('id'), 'slug': binding.get('slug'),
                          'start_date': binding.get('start_date'),
                          'tournament': (binding.get('tournament') or {}).get('name'),
                          'url': 'https://bo3.gg/matches/' + str(binding.get('slug')),
                          'team1': (binding.get('team1') or {}).get('name'),
                          'team2': (binding.get('team2') or {}).get('name')},
                'bet': bo3_bet_block(binding),
                'results': results,
            })
        else:
            row['bo3']['bound'] = None
        report['blank_fixtures'].append(row)

    for label, template in PROVIDER_PAGES:
        entry = fetch(template.format(team=urllib.parse.quote(sorted(teams_needed)[0] if teams_needed else '')))
        text = entry.pop('text', None)
        item = {'label': label, 'request': entry}
        if text:
            title = re.search(r'<title>([^<]*)</title>', text, re.I)
            body = visible_text(text)
            item['title'] = title.group(1).strip()[:120] if title else None
            item['teams_present'] = {name: bool(re.search(re.escape(name), body, re.I))
                                     for name in sorted(teams_needed)[:8]}
        report['providers'].append(item)

    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'provider-probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'blank': len(blanks),
                      'hltv': {f['hotspawn_id']: [h.get('request', {}).get('http_status') for h in f['hltv']]
                               for f in report['blank_fixtures']},
                      'bo3_bound': {f['hotspawn_id']: bool(f['bo3'].get('bound')) for f in report['blank_fixtures']},
                      'bo3_bet': {f['hotspawn_id']: bool(f['bo3'].get('bet')) for f in report['blank_fixtures']},
                      'bo3_graph': report['bo3_graph_endpoint']['request'].get('http_status'),
                      'bo3_graph_rows': report['bo3_graph_endpoint']['rows'],
                      'providers_ok': [p['label'] for p in report['providers']
                                       if p['request'].get('http_status') == 200]}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
