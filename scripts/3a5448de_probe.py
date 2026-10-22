"""Session arena-3a5448de — research picks for fixtures the featured method cannot resolve.

Read-only evidence probe. It runs AFTER ``scripts.collect`` and
``scripts.originate --live`` on a GitHub runner (the sandbox has no egress to
Hotspawn/HLTV/books) and answers, for every live fixture that the *featured*
exact-name method did not resolve with a first-party money line:

1. HLTV first — match listing, world ranking, and (when the collector saved a
   fixture-specific HLTV match URL) that match page. HLTV publishes identity,
   rankings and a fan vote; it publishes no two-sided prematch price, and the
   fan vote is never an input.
2. Esportsbooks / betting lines second — the first-party books already in the
   ladder (Polymarket, Kalshi, Thunderpick, Bovada, Pinnacle) are reported from
   the fixture's own published research trail; additionally this probe checks,
   read-only, the structured bo3.gg surfaces (upcoming-fixture binding,
   ``bet_updates`` bookmaker block, team lookup/detail) and the public pages of
   DraftKings, Stake, OddsPortal, Rivalry, GG.BET, BetBoom, 1xBet,
   Marathonbet, Betway, Luckbox, Oddspedia and EGamersWorld for reachability
   and for whether the fixture's exact team names are even listed.

It never writes a probability, a pick or an alias. A reachable page is not a
price: only a two-sided first-party prematch series line (validated by
``scripts/originate.py``) or a published official rating may produce a number.
HTML pages are status/name-presence evidence only; no price is scraped from
HTML. The bo3.gg ``bet_updates`` coefficients are copied verbatim as evidence
because that relay is already a validated rung of the ladder — this probe
decides nothing about them.

Usage: python -m scripts.3a5448de_probe [--out data/research/3a5448de]
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
BO3_API = 'https://api.bo3.gg/api/v1'
BO3_HEADERS = {'User-Agent': UA, 'Accept': 'application/json'}
MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference'}

# Public pages probed once per run (status + exact-name presence only).
SURFACES = [
    ('HLTV match listing', 'https://www.hltv.org/matches'),
    ('HLTV world ranking', 'https://www.hltv.org/ranking/teams'),
    ('EGamersWorld CS2 matches', 'https://egamersworld.com/counterstrike/matches'),
    ('DraftKings CS2', 'https://sportsbook.draftkings.com/leagues/esports/counter-strike-2'),
    ('Stake CS2', 'https://stake.com/sports/esports/counter-strike-2'),
    ('OddsPortal CS2', 'https://www.oddsportal.com/esports/counter-strike/'),
    ('Rivalry CS2', 'https://www.rivalry.com/esports/counter-strike-2-betting'),
    ('GG.BET CS', 'https://gg.bet/en/counter-strike'),
    ('BetBoom CS2', 'https://betboom.ru/sport/cs2'),
    ('1xBet CS2', 'https://1xbet.com/en/line/counter-strike-2'),
    ('Marathonbet CS2', 'https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/'),
    ('Betway CS2', 'https://www.betway.com/en/sports/esports/counter-strike-2'),
    ('Luckbox CS2', 'https://luckbox.com/esports/csgo'),
    ('Oddspedia CS2', 'https://www.oddspedia.com/esports/counter-strike-2'),
    ('bo3.gg matches', 'https://bo3.gg/matches'),
    ('bo3.gg teams', 'https://bo3.gg/teams'),
    ('Pinnacle guest leagues (sport 12)', 'https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues'),
]

CHALLENGE = ('just a moment', 'cf-chl', 'challenge-platform', 'attention required',
             'enable javascript and cookies', 'captcha', 'access denied')


def targets(origination: dict) -> list[dict]:
    """Fixtures not resolved the same way as the featured picks.

    That is: no featured method at all, or a complete-list resolution that is
    not a first-party money line (research model, wide-book guidance, or still
    blank). Featured money rows are excluded — they already have a pick from
    the featured method.
    """
    out = []
    for m in origination.get('matches') or []:
        if m.get('availability') == 'past':
            continue
        o = m.get('origination') or {}
        # A first-party money resolution (featured or researched) already has a
        # pick the featured way; everything else is a research target.
        if o.get('method') in MONEY_METHODS:
            continue
        out.append(m)
    return out


def norm(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (value or '').casefold())


def probe_surface(name: str, url: str, team_names: list[str], timeout: int = 20,
                  get=None) -> dict:
    """One read-only GET: status, challenge markers, exact team-name presence."""
    get = get or requests.get
    record = {'name': name, 'url': url,
              'observed_at': datetime.now(UTC).isoformat(timespec='seconds')}
    try:
        r = get(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'},
                timeout=timeout, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001 - the failure itself is the evidence
        record.update(http_status=None, error=f'{type(exc).__name__}: {exc}'[:300])
        return record
    body = r.text or ''
    lowered = body.lower()
    record.update(http_status=r.status_code, final_url=getattr(r, 'url', url),
                  bytes=len(body),
                  challenge_markers=[c for c in CHALLENGE if c in lowered][:4],
                  teams_listed=sorted({t for t in team_names if t and t.lower() in lowered}))
    return record


def bo3_upcoming(get=None, pages: int = 4) -> list[dict]:
    get = get or requests.get
    rows = []
    for page in range(pages):
        query = (f'/matches?page[offset]={page * 100}&page[limit]=100&sort=start_date'
                 '&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1'
                 '&with=teams,tournament')
        r = get(BO3_API + query, headers=BO3_HEADERS, timeout=25)
        r.raise_for_status()
        chunk = (r.json() or {}).get('results') or []
        rows.extend(chunk)
        if len(chunk) < 100:
            break
    return rows


def bo3_team_lookup(name: str, get=None) -> dict:
    """Exact-name bo3.gg team lookup + detail keys (identity evidence only)."""
    get = get or requests.get
    out = {'query_name': name, 'matches': [], 'detail_keys': None, 'detail_sample': None}
    query = '/teams?page[offset]=0&page[limit]=10&filter[teams.name][eq]=' + quote(name, safe='')
    r = get(BO3_API + query, headers=BO3_HEADERS, timeout=25)
    r.raise_for_status()
    rows = [row for row in (r.json() or {}).get('results') or []
            if norm(row.get('name') or '') == norm(name)]
    out['matches'] = [{'id': row.get('id'), 'name': row.get('name'),
                       'slug': row.get('slug')} for row in rows]
    if len(rows) == 1 and rows[0].get('id'):
        team_id = rows[0]['id']
        try:
            d = get(f'{BO3_API}/teams/{team_id}', headers=BO3_HEADERS, timeout=25)
            d.raise_for_status()
            payload = d.json() or {}
            record = payload.get('result') or payload.get('data') or payload
            if isinstance(record, dict):
                out['detail_keys'] = sorted(record.keys())
                # Scalars only, verbatim: this records whether bo3.gg publishes
                # any team rating/points field at all. It is never converted
                # into a probability by this probe.
                out['detail_sample'] = {k: record[k] for k in sorted(record.keys())
                                        if isinstance(record.get(k), (int, float, str, bool))
                                        and k not in ('logo', 'image', 'banner')}
        except Exception as exc:  # noqa: BLE001
            out['detail_error'] = f'{type(exc).__name__}: {exc}'[:200]
    return out


def fixture_bo3(fixture: dict, upcoming: list[dict], start_tolerance_sec: int = 900) -> dict:
    """Bind a Hotspawn fixture to bo3.gg upcoming rows by BOTH names + start."""
    from scripts.domain import timestamp
    names = {norm(t.get('name') or '') for t in fixture.get('teams') or []}
    start = timestamp(fixture.get('starts_at'))
    bound, near = [], []
    for row in upcoming:
        sides = {norm((row.get('team1') or {}).get('name') or ''),
                 norm((row.get('team2') or {}).get('name') or '')}
        if sides != names or len(sides) != 2:
            continue
        other = timestamp(row.get('start_date'))
        delta = (abs((other - start).total_seconds())
                 if other is not None and start is not None else None)
        record = {'bo3_id': row.get('id'),
                  'slug': row.get('slug'),
                  'url': 'https://bo3.gg/matches/' + str(row.get('slug')),
                  'start': row.get('start_date'), 'start_delta_sec': delta,
                  'tournament': (row.get('tournament') or {}).get('name'),
                  'bo_type': row.get('bo_type')}
        bet = row.get('bet_updates')
        if isinstance(bet, dict):
            record['bet_updates'] = {
                'provider': bet.get('provider'), 'book_url': bet.get('path'),
                'team_1': {k: (bet.get('team_1') or {}).get(k) for k in ('name', 'coeff', 'active', 'team_id')},
                'team_2': {k: (bet.get('team_2') or {}).get(k) for k in ('name', 'coeff', 'active', 'team_id')}}
        (bound if delta is not None and delta <= start_tolerance_sec else near).append(record)
    return {'bound': bound, 'near_time_mismatch': near}


def fixture_report(fixture: dict, bo3: dict, team_lookups: dict) -> dict:
    o = fixture.get('origination') or {}
    trail = [{'stage': r.get('stage'), 'status': r.get('status'),
              'source_url': r.get('source_url'),
              'detail': str(r.get('detail') or '')[:400]}
             for r in fixture.get('research') or []]
    unresolved_stages = [r['stage'] for r in trail if r.get('status') in ('unresolved', 'unavailable')]
    relay = [b for b in bo3.get('bound') or [] if b.get('bet_updates')]
    two_sided_relay = [b for b in relay
                       if (b['bet_updates']['team_1'].get('coeff') not in (None, '')
                           and b['bet_updates']['team_2'].get('coeff') not in (None, ''))]
    return {
        'hotspawn_id': str(fixture.get('id')),
        'teams': [t.get('name') for t in fixture.get('teams') or []],
        'competition': fixture.get('competition'),
        'starts_at': fixture.get('starts_at'),
        'hotspawn_url': fixture.get('source_url'),
        'featured_method': fixture.get('featured_method'),
        'current_resolution': ({'method': o.get('method'), 'label': o.get('label'),
                                'source': o.get('source'), 'source_url': o.get('source_url'),
                                'probabilities': o.get('probabilities'),
                                'pick_index': fixture.get('pick_index'),
                                'limitations': o.get('limitations') or fixture.get('limitations')}
                               if o else None),
        'sources_tried_from_published_trail': trail,
        'unresolved_stages': unresolved_stages,
        'bo3_fixture': bo3,
        'bo3_relay_two_sided_quote_present': bool(two_sided_relay),
        'bo3_team_lookups': {name: team_lookups.get(name) for name in
                             [t.get('name') for t in fixture.get('teams') or []]},
        'limitations': fixture.get('limitations') or [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('data/research/3a5448de'))
    parser.add_argument('--timeout', type=int, default=20)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    latest = json.loads((args.data / 'latest.json').read_text())
    origination = json.loads((args.data / 'origination.json').read_text())
    chosen = targets(origination)
    team_names = sorted({t.get('name') for m in chosen for t in m.get('teams') or [] if t.get('name')})

    surfaces, surface_errors = [], {}
    for name, url in SURFACES:
        try:
            surfaces.append(probe_surface(name, url, team_names, timeout=args.timeout))
        except Exception as exc:  # noqa: BLE001
            surface_errors[name] = f'{type(exc).__name__}: {exc}'[:200]

    upcoming, bo3_error = [], None
    try:
        upcoming = bo3_upcoming()
    except Exception as exc:  # noqa: BLE001
        bo3_error = f'{type(exc).__name__}: {exc}'[:300]

    lookups: dict[str, dict] = {}
    for name in team_names:
        try:
            lookups[name] = bo3_team_lookup(name)
        except Exception as exc:  # noqa: BLE001
            lookups[name] = {'query_name': name, 'error': f'{type(exc).__name__}: {exc}'[:200]}

    fixtures = [fixture_report(m, fixture_bo3(m, upcoming), lookups) for m in chosen]
    document = {
        'schema_version': 1,
        'session': 'arena-3a5448de',
        'observed_at': datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'environment': 'github-actions-runner',
        'policy': ('Read-only research for fixtures the featured method did not resolve with a '
                   'first-party money line. HLTV first (identity/ranking; no prematch price, fan '
                   'vote excluded), then esportsbooks/betting lines. No probability, pick or alias '
                   'is written here. HTML pages are reachability/name evidence only; no price is '
                   'scraped from HTML.'),
        'snapshot': {'latest_generated_at': latest.get('generated_at'),
                     'origination_generated_at': origination.get('generated_at'),
                     'counts': origination.get('counts')},
        'target_definition': ('active fixtures where featured_method is null, or the complete-list '
                              'resolution is not a first-party money line (model/guidance/blank)'),
        'target_count': len(fixtures),
        'surfaces': surfaces,
        'surface_errors': surface_errors,
        'bo3_upcoming_rows': len(upcoming),
        'bo3_error': bo3_error,
        'fixtures': fixtures,
        'conclusions': {
            'with_directional_pick': sum(1 for f in fixtures
                                         if (f.get('current_resolution') or {}).get('pick_index') is not None),
            'resolved_no_pick_even': sum(1 for f in fixtures
                                         if f.get('current_resolution') and f['current_resolution'].get('pick_index') is None),
            'still_blank': sum(1 for f in fixtures if not f.get('current_resolution')),
            'bo3_relay_two_sided': sum(1 for f in fixtures if f['bo3_relay_two_sided_quote_present']),
        },
    }
    (args.out / 'live-research.json').write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n')

    lines = ['# arena-3a5448de — research for fixtures the featured method cannot resolve',
             '', f"Observed: {document['observed_at']} (GitHub Actions runner)",
             f"Snapshot: latest {document['snapshot']['latest_generated_at']} · "
             f"origination {document['snapshot']['origination_generated_at']} · counts {document['snapshot']['counts']}",
             f"Targets (featured-blank or non-money resolution): {len(fixtures)}", '',
             '## Surfaces (HLTV first, then esportsbooks/aggregators)', '']
    for s in surfaces:
        listed = ', '.join(s.get('teams_listed') or []) or '—'
        lines.append(f"- **{s['name']}** — HTTP {s.get('http_status')} — {s['url']} — teams listed: {listed}")
    lines += ['', '## Per-fixture', '']
    for f in fixtures:
        cur = f.get('current_resolution') or {}
        lines.append(f"### {f['teams'][0]} vs {f['teams'][1]} ({f['competition']}, {f['starts_at']})")
        lines.append(f"- Hotspawn: {f['hotspawn_url']}")
        lines.append(f"- Featured method: {f['featured_method']} · current: {cur.get('method')} "
                     f"{cur.get('label') or ''} pick_index={cur.get('pick_index')} probs={cur.get('probabilities')}")
        lines.append(f"- Unresolved stages: {', '.join(f['unresolved_stages']) or '—'}")
        lines.append(f"- bo3.gg bound: {len(f['bo3_fixture']['bound'])} · two-sided relay quote: "
                     f"{f['bo3_relay_two_sided_quote_present']}")
        lines.append(f"- Limitations: {' | '.join(f['limitations']) or '—'}")
        lines.append('')
    lines += ['## Conclusions', '', json.dumps(document['conclusions'], indent=2)]
    (args.out / 'live-research.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'targets': len(fixtures), 'conclusions': document['conclusions'],
                      'surfaces_200': sum(1 for s in surfaces if s.get('http_status') == 200),
                      'surfaces_total': len(surfaces)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
