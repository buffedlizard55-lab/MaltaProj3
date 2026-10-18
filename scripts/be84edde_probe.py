"""Session arena-be84edde — dispatch-only provider probe for blank fixtures.

Why this exists
---------------
The six fixtures the research ladder leaves blank are all low-tier CS2 where
Polymarket/Kalshi either have no listing at all or list a book far wider than
the 0.12 indicative ceiling the pricing policy requires. The brief asks for a
way to resolve a pick for *every* Hotspawn CS2 match, starting with HLTV and
then esportsbooks and esports betting lines.

This module never prices anything and never writes a probability. It runs on
the GitHub runner (the only environment in this session with egress to the
providers) and records, for each candidate source, whether the source is
reachable at all and whether it actually lists each blank fixture.

It writes `data/research/be84edde/provider-probe.json`. Nothing else in the
repository reads it; it is evidence for a human decision about which provider,
if any, is safe to add to `scripts/originate.py`.

Usage:  python -m scripts.be84edde_probe --live
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / 'be84edde' / 'provider-probe.json'

# The six fixtures the 2026-10-18T01:01Z live run left blank, with the HLTV id
# the ladder's own HLTV rung already confirmed for each.
BLANK_FIXTURES = [
    {'hotspawn_id': '1081129', 'teams': ['Privateer', 'antidaun'],
     'hltv': 'https://www.hltv.org/matches/2399480/antidaun-vs-privateer-cct-2026-europe-series-12-closed-qualifier',
     'starts_at': '2026-10-18T11:00:00Z', 'competition': 'CCT Europe 2026 Series #12 Play-In'},
    {'hotspawn_id': '1082206', 'teams': ['Damajuana', 'A NATA'],
     'hltv': 'https://www.hltv.org/matches/2399791/damajuana-vs-a-nata-cct-2026-south-america-series-7',
     'starts_at': '2026-10-18T16:00:00Z', 'competition': 'CCT South America 2026 Series #7'},
    {'hotspawn_id': '1082207', 'teams': ['QUINTESSÊNCIA', 'RED Canids Academy'],
     'hltv': 'https://www.hltv.org/matches/2399792/quintessncia-vs-red-canids-academy-cct-2026-south-america-series-7',
     'starts_at': '2026-10-18T19:00:00Z', 'competition': 'CCT South America 2026 Series #7'},
    {'hotspawn_id': '1079181', 'teams': ['Fire Flux', 'ex-6666'],
     'hltv': 'https://www.hltv.org/matches/2399098/fire-flux-vs-ex-6666-nodwin-clutch-series-13',
     'starts_at': '2026-10-19T17:00:00Z', 'competition': 'NODWIN Clutch Series #13'},
    {'hotspawn_id': '1081861', 'teams': ['Lynn Vision', 'Morningstar'],
     'hltv': 'https://www.hltv.org/matches/2399576/lynn-vision-vs-morningstar-macemedia-void-autumn-cup-2026',
     'starts_at': '2026-10-20T03:00:00Z', 'competition': 'VOID Autumn Cup 2026'},
    {'hotspawn_id': '1081863', 'teams': ['Chinggis Warriors', 'WXM'],
     'hltv': 'https://www.hltv.org/matches/2399578/chinggis-warriors-vs-wxm-macemedia-void-autumn-cup-2026',
     'starts_at': '2026-10-20T07:00:00Z', 'competition': 'VOID Autumn Cup 2026'},
]

# Candidate discovery endpoints. Each is probed read-only with a plain GET.
# "kind" tells the probe how to interpret a 200 response.
DISCOVERY = [
    {'label': 'pinnacle-guest-sports', 'kind': 'json',
     'url': 'https://guest.api.arcadia.pinnacle.com/0.1/sports'},
    {'label': 'pinnacle-guest-leagues-esports', 'kind': 'json',
     'url': 'https://guest.api.arcadia.pinnacle.com/0.1/sports/29/leagues'},
    {'label': 'pinnacle-guest-matchups-esports', 'kind': 'json',
     'url': 'https://guest.api.arcadia.pinnacle.com/0.1/sports/29/matchups'},
    {'label': 'pinnacle-guest-leagues-cs', 'kind': 'json',
     'url': 'https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues'},
    {'label': 'pinnacle-guest-matchups-cs', 'kind': 'json',
     'url': 'https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups'},
    {'label': 'oddsportal-cs2', 'kind': 'html',
     'url': 'https://www.oddsportal.com/esports/counter-strike/'},
    {'label': 'bo3gg-cs2-matches', 'kind': 'html',
     'url': 'https://bo3.gg/matches/current?game=csgo'},
    {'label': 'egamersworld-cs-matches', 'kind': 'html',
     'url': 'https://egamersworld.com/counterstrike/matches'},
    {'label': 'ggscore-csgo-matches', 'kind': 'html',
     'url': 'https://ggscore.com/en/csgo/matches'},
    {'label': 'escorenews-csgo-matches', 'kind': 'html',
     'url': 'https://escorenews.com/en/csgo/matches'},
    {'label': 'cybersport-cs2-matches', 'kind': 'html',
     'url': 'https://www.cybersport.ru/matches/counter-strike'},
    {'label': 'stake-cs2', 'kind': 'html',
     'url': 'https://stake.com/sports/esports/counter-strike'},
    {'label': 'betway-esports', 'kind': 'html',
     'url': 'https://betway.com/esports'},
    {'label': '1xbet-esports-cs2', 'kind': 'html',
     'url': 'https://1xbet.com/en/line/Esports'},
    {'label': 'tipsgg-cs2', 'kind': 'html',
     'url': 'https://tips.gg/counter-strike/matches/'},
    {'label': 'esportsgg-cs2-matches', 'kind': 'html',
     'url': 'https://esports.gg/counter-strike-2-matches/'},
]

UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')


def _fetch(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*',
                                               'Accept-Encoding': 'gzip, identity'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get('Content-Encoding') == 'gzip':
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        return resp.status, resp.headers.get('Content-Type', ''), raw


def probe(url: str, kind: str):
    entry = {'url': url, 'kind': kind}
    try:
        status, ctype, body = _fetch(url)
    except urllib.error.HTTPError as exc:
        entry.update(status=exc.code, reachable=False, error=f'HTTP {exc.code}')
        return entry
    except Exception as exc:  # network/DNS/TLS — recorded, never fatal
        entry.update(status=None, reachable=False, error=f'{type(exc).__name__}: {exc}')
        return entry
    entry.update(status=status, reachable=200 <= status < 300, content_type=ctype,
                 bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    text = body.decode('utf-8', 'replace')
    if kind == 'json':
        entry['json_head'] = text[:600]
        try:
            parsed = json.loads(text)
            entry['json_type'] = type(parsed).__name__
            if isinstance(parsed, list):
                entry['json_len'] = len(parsed)
                entry['json_keys'] = sorted({k for row in parsed[:5] if isinstance(row, dict) for k in row})[:25]
            elif isinstance(parsed, dict):
                entry['json_keys'] = sorted(parsed)[:25]
        except Exception as exc:
            entry['json_parse_error'] = f'{type(exc).__name__}: {exc}'
    else:
        entry['text_head'] = re.sub(r'\s+', ' ', text[:400])
    return entry


def _norm(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (value or '').lower())


def search_listing(probe_rows, fixtures):
    """Report whether any reachable source mentions each blank fixture's teams."""
    out = []
    for fx in fixtures:
        a, b = _norm(fx['teams'][0]), _norm(fx['teams'][1])
        hits = []
        for row in probe_rows:
            text = (row.get('text_head') or '') + ' ' + (row.get('json_head') or '')
            blob = _norm(text)
            if a and b and a in blob and b in blob:
                hits.append(row['label'])
            elif a and a in blob:
                hits.append(row['label'] + ' (one team only)')
            elif b and b in blob:
                hits.append(row['label'] + ' (one team only)')
        out.append({'hotspawn_id': fx['hotspawn_id'], 'competition': fx['competition'],
                    'starts_at': fx['starts_at'], 'teams': fx['teams'],
                    'listed_on_head_only': hits})
    return out


PINNACLE_SPORT = 12  # confirmed by enumeration: sport 12 is Esports; sport 29 is Soccer.

# Teams of every fixture the 2026-10-18T01:01Z live run left blank, plus a
# broader look at what Pinnacle's esports board actually covers.
def _lid(matchups, league_name):
    for m in matchups:
        if ((m.get('league') or {}).get('name') or '') == league_name:
            return (m.get('league') or {}).get('id')
    return None


def pinnacle_markets(league_ids):
    """Read the straight moneyline market for a set of Pinnacle league ids."""
    out = []
    for lid in league_ids:
        if not lid:
            continue
        entry = {'league_id': lid}
        for path, label in (
            (f'https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight', 'straight'),
            (f'https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets?marketType=moneyline', 'moneyline'),
        ):
            try:
                status, _c, body = _fetch(path, timeout=30)
                payload = json.loads(body.decode('utf-8', 'replace'))
            except Exception as exc:
                entry[label] = {'error': f'{type(exc).__name__}: {exc}'}
                continue
            rec = {'status': status}
            if isinstance(payload, list):
                rec['count'] = len(payload)
                rec['sample'] = payload[:6]
                rec['keys'] = sorted({k for row in payload[:5] if isinstance(row, dict) for k in row})[:25]
            elif isinstance(payload, dict):
                rec['keys'] = sorted(payload)[:25]
                rec['sample_head'] = json.dumps(payload)[:600]
            entry[label] = rec
            if rec.get('count'):
                break
        out.append(entry)
    return out


def pinnacle_scan():
    """Read Pinnacle's public guest board for esports and report CS2 coverage."""
    status, _ctype, body = _fetch(f'https://guest.api.arcadia.pinnacle.com/0.1/sports/{PINNACLE_SPORT}/matchups')
    matchups = json.loads(body.decode('utf-8', 'replace'))
    rows = []
    for m in matchups:
        league = ((m.get('league') or {}).get('name') or '')
        parts = [p.get('name') for p in (m.get('participants') or [])]
        money = None
        for period in (m.get('periods') or []):
            ml = period.get('moneyline')
            if isinstance(ml, dict):
                money = {'number': period.get('number'), 'lineId': period.get('lineId'),
                         'home': ml.get('home'), 'away': ml.get('away'), 'draw': ml.get('draw'),
                         'capturedAt': period.get('cutoffAt') or period.get('maxBetAt')}
                break
        rows.append({'matchup_id': m.get('id'), 'league': league,
                     'groups': (m.get('league') or {}).get('group'),
                     'participants': parts, 'startTime': m.get('startTime'),
                     'bestOfX': m.get('bestOfX'), 'state': m.get('state'),
                     'isLive': m.get('isLive'), 'moneyline': money})
    leagues = sorted({(r['league'], _lid(matchups, r['league'])) for r in rows})
    hits = []
    for fx in BLANK_FIXTURES:
        a, b = _norm(fx['teams'][0]), _norm(fx['teams'][1])
        found = []
        for r in rows:
            names = {_norm(n) for n in r['participants'] if n}
            if a in names and b in names:
                found.append(r)
        hits.append({'hotspawn_id': fx['hotspawn_id'], 'competition': fx['competition'],
                     'starts_at': fx['starts_at'], 'teams': fx['teams'],
                     'pinnacle_matchups': found})
    cs2 = [r for r in rows if (r['league'] or '').startswith('CS2')]
    cs2_league_ids = sorted({lid for _l, lid in leagues if lid and any(
        r['league'] == _l for r in cs2)})
    return {'sport_id': PINNACLE_SPORT, 'status': status, 'matchup_count': len(rows),
            'leagues': leagues, 'priced_rows': sum(1 for r in rows if r['moneyline']),
            'blank_fixture_hits': hits,
            'cs2_matchups': cs2,
            'cs2_league_ids': cs2_league_ids,
            'cs2_markets': pinnacle_markets(cs2_league_ids)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='perform real network probes')
    parser.add_argument('--max', type=int, default=len(DISCOVERY))
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if not args.live:
        print('Refusing to run without --live: this probe performs real network calls.')
        return 2
    rows = []
    for item in DISCOVERY[: args.max]:
        print(f"probing {item['label']} ...", file=sys.stderr)
        rows.append(dict(probe(item['url'], item['kind']), label=item['label']))
    try:
        pinnacle = pinnacle_scan()
    except Exception as exc:
        pinnacle = {'error': f'{type(exc).__name__}: {exc}'}
    try:
        from scripts import pinnacle_lines
        diagnostic = pinnacle_lines.describe()
        final_day_quotes = {}
        for fx in BLANK_FIXTURES:
            pass
        for label, (a, b, starts) in {
            'third-place-decider': ('Aurora', 'Falcons', '2026-10-18T11:30:00Z'),
            'grand-final': ('FURIA', 'BB Team', '2026-10-18T15:00:00Z'),
            'grand-final-alt-name': ('FURIA', 'BETBOOM', '2026-10-18T15:00:00Z'),
        }.items():
            q, reason = pinnacle_lines.quote(a, b, starts)
            final_day_quotes[label] = {'quote': q, 'reason': reason}
    except Exception as exc:
        diagnostic = {'error': f'{type(exc).__name__}: {exc}'}
        final_day_quotes = {'error': f'{type(exc).__name__}: {exc}'}
    report = {
        'probe': 'be84edde provider probe for blank low-tier fixtures',
        'generated_at': started,
        'pinnacle_esports_board': pinnacle,
        'pinnacle_diagnostic': diagnostic,
        'pinnacle_final_day_quotes': final_day_quotes,
        'purpose': ('Decide whether any additional source can honestly price the fixtures the '
                    'research ladder leaves blank. Evidence only: no probability, pick or alias '
                    'is written by this module.'),
        'blank_fixtures': BLANK_FIXTURES,
        'reachable': [r['label'] for r in rows if r.get('reachable')],
        'blocked': [{'label': r['label'], 'status': r.get('status'), 'error': r.get('error')}
                    for r in rows if not r.get('reachable')],
        'sources': rows,
        'listing_check': search_listing(rows, BLANK_FIXTURES),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reachable': report['reachable'], 'generated_at': started}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
