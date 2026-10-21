"""Session arena-541cd43a — identity and coverage discovery for blank fixtures.

The first probe (``scripts/s541cd43a_probe.py``) showed that the three blank
fixtures fail before any model can run: bo3.gg's exact-name team lookup returns
nothing for ``ex-CYBERSHOKE`` and ``flacons``, so a fixture binding (and with it
the results-model sample) never exists. HLTV answers Cloudflare 403 from the
runner, and every esportsbook surface answers 403/404/429/203.

This probe asks the only questions that can turn a blank into a priced row,
without writing any value:

* does bo3.gg know the team under a different filter (contains / search /
  tournament listing) — and if so, what is its exact team id;
* does bo3.gg list the tournament at all, and are the fixture's matches there;
* does Liquipedia's public MediaWiki API cover these teams (a second,
  independently linkable results source), and does its search answer at all.

Usage: python -m scripts.s541cd43a_probe2 [--root .]
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from scripts.s541cd43a_probe import UA, bo3_results, fetch, get_json, iso, key

OUT_DIR = Path('data/research/541cd43a')
BO3_TEAM_FILTERS = [
    ('exact', '/teams?page[offset]=0&page[limit]=5&filter[teams.name][eq]={q}'),
    ('contains', '/teams?page[offset]=0&page[limit]=10&filter[teams.name][contains]={q}'),
    ('search', '/teams?page[offset]=0&page[limit]=10&search={q}'),
]
BO3_TOURNAMENT_FILTERS = [
    ('exact', '/tournaments?page[offset]=0&page[limit]=5&filter[tournaments.name][eq]={q}'),
    ('contains', '/tournaments?page[offset]=0&page[limit]=10&filter[tournaments.name][contains]={q}'),
    ('search', '/tournaments?page[offset]=0&page[limit]=10&search={q}'),
]


def bo3_query(template: str, value: str) -> dict:
    path = template.format(q=urllib.parse.quote(value, safe=''))
    payload, entry = get_json(path)
    rows = (payload or {}).get('results') or []
    return {'request': entry, 'rows': len(rows),
            'results': [{'id': r.get('id'), 'name': r.get('name'), 'slug': r.get('slug'),
                         'rank': r.get('rank')} for r in rows[:10]]}


def bo3_tournament_matches(tournament_id: int) -> dict:
    path = ('/matches?page[offset]=0&page[limit]=50&sort=start_date'
            f'&filter[matches.tournament_id][eq]={tournament_id}&with=teams,tournament')
    payload, entry = get_json(path)
    rows = (payload or {}).get('results') or []
    return {'request': entry, 'rows': len(rows),
            'matches': [{'id': r.get('id'), 'start_date': r.get('start_date'),
                         'status': r.get('status'), 'slug': r.get('slug'),
                         'team1': (r.get('team1') or {}).get('name'),
                         'team2': (r.get('team2') or {}).get('name'),
                         'winner_team_id': r.get('winner_team_id'),
                         'bet': bool(r.get('bet_updates'))} for r in rows[:50]]}


def liquipedia_search(term: str) -> dict:
    url = ('https://liquipedia.net/counterstrike/api.php?action=query&list=search&format=json'
           '&srlimit=5&srsearch=' + urllib.parse.quote(term))
    entry = fetch(url, headers={'User-Agent': 'SpawnScoutResearch/1.0 (github.com/buffedlizard55-lab/MaltaProj3)',
                                'Accept': 'application/json'})
    text = entry.pop('text', None)
    out = {'request': entry, 'hits': []}
    if text:
        try:
            payload = json.loads(text)
        except ValueError:
            out['error'] = 'response was not JSON'
            return out
        out['hits'] = [{'title': h.get('title'), 'snippet': h.get('snippet', '')[:200]}
                       for h in ((payload.get('query') or {}).get('search') or [])]
    return out


def main() -> int:
    root = Path('.').resolve()
    snapshot = json.loads((root / 'data/research/541cd43a/live-snapshot.json').read_text())
    blanks = snapshot.get('blank') or []
    report = {'session': 'arena-541cd43a', 'generated_at': iso(),
              'policy': 'Read-only identity/coverage discovery. No probability, pick, price or alias is written.',
              'fixtures': []}
    for fixture in blanks:
        row = {'hotspawn_id': fixture['id'], 'teams': fixture['teams'],
               'competition': fixture['competition'], 'starts_at': fixture['starts_at'],
               'bo3_team': {}, 'bo3_tournament': None, 'bo3_results': {}, 'liquipedia': {}}
        for team in fixture['teams']:
            row['bo3_team'][team] = {label: bo3_query(template, team)
                                     for label, template in BO3_TEAM_FILTERS}
            hits = [r for label in row['bo3_team'][team].values() for r in r['results']]
            ids = sorted({h['id'] for h in hits if h.get('id')})
            if len(ids) == 1:
                team_id = ids[0]
                finished = bo3_results(team_id, limit=40)
                row['bo3_results'][team] = {
                    'team_id': team_id, 'rows': len(finished),
                    'parsed_done': sum(1 for g in finished if g.get('parsed_status') == 'done'),
                    'first': min((str(g.get('start_date'))[:10] for g in finished), default=None),
                    'last': max((str(g.get('start_date'))[:10] for g in finished), default=None),
                    'opponents': sorted({(g.get('team2') if g.get('team1_id') == team_id else g.get('team1') or {}).get('name')
                                         for g in finished})[:30],
                }
            row['liquipedia'][team] = liquipedia_search(team)
        tournament = bo3_query(BO3_TOURNAMENT_FILTERS[1][1], fixture['competition'])
        row['bo3_tournament'] = tournament
        ids = sorted({r['id'] for r in tournament['results'] if r.get('id')})
        if len(ids) == 1:
            row['bo3_tournament_matches'] = bo3_tournament_matches(ids[0])
        report['fixtures'].append(row)
    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'identity-probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'fixtures': len(blanks),
                      'liquipedia_status': {f['hotspawn_id']: {t: f['liquipedia'][t]['request'].get('http_status')
                                                               for t in f['liquipedia']} for f in report['fixtures']},
                      'bo3_ids': {f['hotspawn_id']: {t: [r for r in (f['bo3_team'][t]['contains']['results'] or [])][:3]
                                                     for t in f['bo3_team']} for f in report['fixtures']}}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
