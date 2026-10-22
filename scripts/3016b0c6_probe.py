"""Session arena-3016b0c6 — line-source research for fixtures with no betting line.

Read-only. Goal (user brief): for every Hotspawn CS2 fixture that the featured
method cannot resolve (low-tier / not listed on Polymarket), try HLTV first,
then esportsbooks and esports betting-line surfaces, and record — per fixture —
whether a real two-sided prematch price exists anywhere reachable.

It never writes a probability, a pick or an alias. Output is dated evidence in
``data/research/3016b0c6/``. A page answering HTTP 200 is not a price; only a
bound fixture with both sides carrying a coefficient/price is recorded as a
``money_line_lead``, and even that is a lead for the reviewed ladder in
``scripts/originate.py``, not a pick.

Fixture list: the live published complete-picks snapshot
(``https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json``),
falling back to the checked-in ``data/origination.json`` — the source actually
used is recorded. "Needs research" = origination is None (unresolved) or its
method is a research model (model / network / form / guidance): those are the
fixtures with no external betting line.

Usage: python -m scripts.3016b0c6_probe [--out data/research/3016b0c6]
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import requests

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
LIVE_ORIGINATION = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json'
MODEL_METHODS = {'model', 'network', 'form', 'guidance'}

# HLTV first (identity / ranking context; HLTV publishes no two-sided price),
# then esportsbooks and aggregators. Pinnacle's guest API and bo3.gg's API are
# probed structurally below, not as HTML pages.
PAGES = [
    ('HLTV match listing', 'https://www.hltv.org/matches'),
    ('HLTV world ranking', 'https://www.hltv.org/ranking/teams'),
    ('GG.BET CS2', 'https://gg.bet/en/counter-strike'),
    ('BetBoom CS2', 'https://betboom.ru/sport/cs2'),
    ('Stake CS2', 'https://stake.com/sports/esports/cs2'),
    ('BC.Game CS2', 'https://bc.game/sports/esports'),
    ('1xBet CS2', 'https://1xbet.com/en/line/counter-strike-2'),
    ('Marathonbet CS2', 'https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/'),
    ('Betway esports', 'https://www.betway.com/en/sports/esports/counter-strike-2'),
    ('DraftKings CS2', 'https://sportsbook.draftkings.com/leagues/esports/counter-strike-2'),
    ('OddsPortal CS2', 'https://www.oddsportal.com/esports/counter-strike/'),
    ('EGamersWorld CS2 matches', 'https://egamersworld.com/counterstrike/matches'),
    ('Pinnacle CS2 page', 'https://www.pinnacle.com/en/esports/counter-strike-2'),
]
CHALLENGE = ('just a moment', 'cf-chl', 'challenge-platform', 'attention required',
             'enable javascript and cookies', 'captcha', 'access denied')


def fetch_json_url(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', 'replace'))


def load_targets() -> tuple[list[dict], dict]:
    """Fixtures with no external betting line, from the live snapshot if reachable."""
    meta = {'source_url': LIVE_ORIGINATION, 'source': 'live published snapshot'}
    try:
        doc = fetch_json_url(LIVE_ORIGINATION)
    except Exception as exc:  # noqa: BLE001 - recorded, fallback is explicit
        doc = json.loads(Path('data/origination.json').read_text())
        meta = {'source_url': 'data/origination.json (checked-in fallback)',
                'source': f'live fetch failed: {type(exc).__name__}: {exc}'[:200]}
    meta['snapshot_generated_at'] = doc.get('generated_at')
    targets = []
    for m in doc.get('matches') or []:
        if m.get('availability') == 'past':
            continue
        o = m.get('origination')
        if o is None or o.get('method') in MODEL_METHODS:
            targets.append({'id': m.get('id'),
                            'teams': [t.get('name') for t in m.get('teams') or []],
                            'competition': m.get('competition'),
                            'starts_at': m.get('starts_at'),
                            'current_method': (o or {}).get('method') or 'unresolved',
                            'current_label': (o or {}).get('label') or 'no pick — unresolved',
                            'hotspawn_url': m.get('source_url')})
    meta['targets'] = len(targets)
    meta['active'] = (doc.get('counts') or {}).get('active')
    return targets, meta


def probe_page(name: str, url: str, teams: list[str], timeout: int = 20) -> dict:
    rec = {'name': name, 'url': url}
    try:
        r = requests.get(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'},
                         timeout=timeout, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001
        rec.update(status=None, error=f'{type(exc).__name__}: {exc}'[:250])
        return rec
    body = r.text or ''
    rec.update(status=r.status_code, final_url=r.url, bytes=len(body),
               challenge_markers=[m for m in CHALLENGE if m in body.lower()][:4],
               teams_found=sorted({t for t in teams if t and t.lower() in body.lower()}))
    return rec


def pinnacle_scan(teams_key: dict) -> dict:
    """Pinnacle guest esports board: matchups whose participants match a target fixture."""
    out = {'api': 'https://guest.api.arcadia.pinnacle.com/0.1/sports/29/matchups',
           'matchups_seen': 0, 'fixture_hits': []}
    try:
        rows = fetch_json_url(out['api'], timeout=30)
    except Exception as exc:  # noqa: BLE001
        out['error'] = f'{type(exc).__name__}: {exc}'[:250]
        return out
    if not isinstance(rows, list):
        out['error'] = 'unexpected contract: matchups is not a list'
        return out
    out['matchups_seen'] = len(rows)
    for row in rows:
        names = [((p or {}).get('name') or '') for p in row.get('participants') or []]
        from scripts.bo3_odds_probe import key
        keys = {key(n) for n in names}
        for fixture_key, label in teams_key.items():
            if fixture_key and fixture_key <= keys:
                out['fixture_hits'].append({'fixture': label, 'participants': names,
                                            'league': (row.get('league') or {}).get('name'),
                                            'startTime': row.get('startTime'), 'id': row.get('id')})
    return out


def bo3_scan(targets: list[dict]) -> list[dict]:
    """bo3.gg binding + published bookmaker block (both coefficients) per target fixture."""
    from scripts import bo3_odds_probe as probe
    rows = []
    for m in targets:
        row = {'id': m['id'], 'teams': m['teams'], 'bound': None, 'bet': None, 'lookup': []}
        ids = []
        for team in m['teams']:
            found = probe.team_id(team)
            row['lookup'].append({'name': team, **found})
            if found.get('id'):
                ids.append(found)
        if ids:
            wanted = {probe.key(n) for n in m['teams'] if n}
            for cand in probe.upcoming(ids[0]['id']):
                if not isinstance(cand, dict) or 'error' in cand:
                    continue
                names = {probe.key((cand.get('team1') or {}).get('name') or ''),
                         probe.key((cand.get('team2') or {}).get('name') or '')}
                if wanted == names:
                    row['bound'] = {'slug': cand.get('slug'), 'start_date': cand.get('start_date'),
                                    'url': 'https://bo3.gg/matches/' + str(cand.get('slug'))}
                    row['bet'] = probe.bet_block(cand)
                    break
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('data/research/3016b0c6'))
    ap.add_argument('--timeout', type=int, default=20)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    observed = datetime.now(UTC).isoformat(timespec='seconds')
    targets, meta = load_targets()
    teams = sorted({t for m in targets for t in m['teams'] if t})
    print(f"targets (no betting line): {len(targets)} from {meta['source']}")

    pages = [probe_page(n, u, teams, timeout=args.timeout) for n, u in PAGES]
    from scripts.bo3_odds_probe import key
    teams_key = {frozenset({key(t) for t in m['teams'] if t}): ' vs '.join(m['teams'])
                 for m in targets}
    pinnacle = pinnacle_scan(teams_key)
    bo3 = bo3_scan(targets)

    per_fixture = []
    for m in targets:
        b = next((r for r in bo3 if r['id'] == m['id']), {})
        bet = b.get('bet') or {}
        two_sided = bool(bet and (bet.get('team_1') or {}).get('coeff')
                         and (bet.get('team_2') or {}).get('coeff'))
        pin_hit = [h for h in pinnacle.get('fixture_hits') or []
                   if h['fixture'] == ' vs '.join(m['teams'])]
        listing_pages = [p['name'] for p in pages if any(
            t in (p.get('teams_found') or []) for t in m['teams'] if t)]
        per_fixture.append({**m,
                            'bo3_bound_url': (b.get('bound') or {}).get('url'),
                            'bo3_bet_two_sided': two_sided,
                            'bo3_bet': bet or None,
                            'pinnacle_matchup': pin_hit or None,
                            'pages_listing_a_team': listing_pages,
                            'money_line_lead': bool(two_sided or pin_hit),
                            'verdict': ('NEW LEAD: two-sided relayed price found — reviewed ladder '
                                        'must replay it before any pick changes' if two_sided else
                                        'LEAD ONLY: Pinnacle lists the fixture; series moneyline still '
                                        'needs the straight-markets replay' if pin_hit else
                                        'No two-sided price found on any probed surface; research-model '
                                        'pick remains, limitation stands')})

    doc = {'schema_version': 1, 'session': 'arena-3016b0c6', 'observed_at': observed,
           'environment': 'github-actions-runner' if __import__('os').environ.get('GITHUB_ACTIONS') else 'local checkout',
           'policy': ('Read-only research. HLTV first (identity/ranking, no price), then esportsbooks/'
                      'aggregators. Nothing here is a probability or a pick.'),
           'target_source': meta, 'targets': targets, 'pages': pages,
           'pinnacle_guest_api': pinnacle, 'bo3': bo3, 'per_fixture': per_fixture,
           'leads': [f for f in per_fixture if f['money_line_lead']]}
    (args.out / 'line-source-research.json').write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')

    lines = [f'# Line-source research for fixtures without a betting line — arena-3016b0c6', '',
             f'Observed {observed} ({doc["environment"]}). Targets: {len(targets)} fixtures with no external '
             f'line in snapshot {meta.get("snapshot_generated_at")} ({meta["source"]}).', '',
             'HLTV first, then esportsbooks/aggregators. A reachable page is not a price.', '',
             '| Fixture | Current basis | bo3.gg bound | Two-sided relay price | Pinnacle lists it | Verdict |',
             '| --- | --- | --- | --- | --- | --- |']
    for f in per_fixture:
        lines.append(f"| {' vs '.join(f['teams'])} ({f['competition']}) | {f['current_label']} | "
                     f"{f['bo3_bound_url'] or '—'} | {'yes' if f['bo3_bet_two_sided'] else 'no'} | "
                     f"{'yes' if f['pinnacle_matchup'] else 'no'} | {f['verdict']} |")
    lines += ['', '## Surfaces probed', '', '| Source | HTTP | Teams found | Challenge |', '| --- | --- | --- | --- |']
    for p in pages:
        lines.append(f"| {p['name']} ({p['url']}) | {p.get('status') or p.get('error','—')} | "
                     f"{', '.join(p.get('teams_found') or []) or '—'} | {', '.join(p.get('challenge_markers') or []) or '—'} |")
    lines += ['', f"Pinnacle guest API: {pinnacle.get('matchups_seen')} esports matchups, "
                  f"{len(pinnacle.get('fixture_hits') or [])} target-fixture hits"
                  + (f", error: {pinnacle['error']}" if pinnacle.get('error') else ''), '',
              f"**New money-line leads: {len(doc['leads'])}** of {len(targets)} target fixtures."]
    (args.out / 'line-source-research.md').write_text('\n'.join(lines) + '\n')
    print(f"leads: {len(doc['leads'])} -> {args.out / 'line-source-research.json'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
