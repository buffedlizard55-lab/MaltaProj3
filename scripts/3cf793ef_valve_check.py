"""Session-only (arena-3cf793ef) verification of the Valve-sourced probability rung.

Read-only and reproducible. For every published row whose stated source is
Valve's official regional standings it:

1. downloads the *same* official markdown the row links to
   (``live/2026/standings_global_2026_10_05.md`` in
   ``ValveSoftware/counter-strike_regional_standings``) through the GitHub
   contents API,
2. parses ``standing | points | team | roster`` rows and keeps only rows with a
   complete five-player roster - the same completeness rule the pricing ladder
   documents, because the file also contains incomplete remnant rows (for
   example ``Banda Chuya`` appears once with five players and once with two),
3. recomputes ``p = 1 / (1 + 10 ** (g * (points_b - points_a) / 400))`` with
   ``g = 1 / sqrt(1 + 3 * (ln10/400)^2 * RD^2 / pi^2)`` and the documented
   fixed ``RD = 75``, and
4. compares the result with the published probability.

It also prices the fixtures that the *live* Hotspawn inventory lists but the
published snapshot does not cover yet, so the next refresh can be checked
against these pre-registered numbers. Nothing here writes a probability into a
canonical feed; the output is evidence for ``data/research/3cf793ef/``.

Usage: python -m scripts.3cf793ef_valve_check [--out data/research/3cf793ef]
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = 'ValveSoftware/counter-strike_regional_standings'
SNAPSHOT = 'live/2026/standings_global_2026_10_05.md'
API = f'https://api.github.com/repos/{REPO}/contents/{SNAPSHOT}'
HTML = f'https://github.com/{REPO}/blob/main/{SNAPSHOT}'
RD = 75.0
SCALE = math.log(10) / 400
G = 1 / math.sqrt(1 + 3 * SCALE ** 2 * RD ** 2 / math.pi ** 2)
TOLERANCE = 0.002


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def key(value: str) -> str:
    folded = ''.join(ch for ch in unicodedata.normalize('NFKD', value or '')
                     if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', '', folded.casefold())


def win_probability(points_a: float, points_b: float) -> float:
    return 1 / (1 + 10 ** (G * (points_b - points_a) / 400))


def fetch_markdown() -> tuple[str, dict]:
    meta = {'url': API, 'observed_at': now()}
    r = requests.get(API, headers={'Accept': 'application/vnd.github.raw',
                                   'User-Agent': 'arena-3cf793ef-verification'},
                     timeout=45)
    meta['status'] = r.status_code
    if r.status_code == 200 and r.headers.get('content-type', '').startswith('application/json'):
        payload = r.json()
        meta['sha'] = payload.get('sha')
        text = base64.b64decode(payload['content']).decode('utf-8')
    else:
        text = r.text
    meta['bytes'] = len(text.encode())
    return text, meta


def parse(markdown: str) -> dict[str, list[dict]]:
    """Every row keyed by normalized team name; incomplete rosters are kept
    apart so the completeness rule can be applied explicitly."""
    rows: dict[str, list[dict]] = {}
    for line in markdown.splitlines():
        if not line.startswith('|') or 'Team Name' in line or line.startswith('| :'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 4 or not cells[1].isdigit():
            continue
        roster = [p.strip() for p in cells[3].split(',') if p.strip()]
        rows.setdefault(key(cells[2]), []).append({
            'standing': int(cells[0]), 'points': int(cells[1]),
            'name': cells[2], 'roster': roster, 'complete': len(roster) == 5,
            'detail': (re.search(r'\((details/[^)]+)\)', cells[4]).group(1)
                       if len(cells) > 4 and re.search(r'\((details/[^)]+)\)', cells[4]) else None),
        })
    return rows


def resolve(rows: dict[str, list[dict]], name: str) -> tuple[dict | None, str]:
    found = rows.get(key(name)) or []
    complete = [r for r in found if r['complete']]
    if len(complete) == 1:
        return complete[0], 'unique complete five-player row'
    if len(complete) > 1:
        return None, f'{len(complete)} complete rows - ambiguous, ladder must fail closed'
    if found:
        return None, f'{len(found)} row(s) but none with five players - excluded'
    return None, 'team not listed in this snapshot'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data/research/3cf793ef')
    ap.add_argument('--markdown', help='use an already-downloaded copy of the official snapshot '
                                       '(the fetch metadata then records the local path)')
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.markdown:
        markdown = Path(args.markdown).read_text()
        import hashlib
        meta = {'local_copy': args.markdown, 'observed_at': now(),
                'sha256': hashlib.sha256(markdown.encode()).hexdigest(),
                'note': 'downloaded with curl from the GitHub contents API in the same session'}
    else:
        markdown, meta = fetch_markdown()
    (out / 'valve-standings-2026-10-05.md').write_text(markdown)
    rows = parse(markdown)

    published = json.loads((out / 'live' / 'published-origination.json').read_text())
    upcoming = json.loads((out / 'live' / 'upcoming.json').read_text())

    checks, mismatches = [], []
    for m in published['matches']:
        o = m.get('origination') or {}
        if 'Valve' not in str(o.get('source') or ''):
            continue
        probs = m.get('featured_probabilities') or o.get('probabilities')
        names = [t['name'] for t in m['teams']]
        a, why_a = resolve(rows, names[0])
        b, why_b = resolve(rows, names[1])
        record = {'id': m['id'], 'teams': names, 'published': probs,
                  'source_url': o.get('source_url'), 'observed_at': o.get('observed_at'),
                  'a': why_a, 'b': why_b}
        inputs = o.get('inputs') or []
        if a and b:
            calc = win_probability(a['points'], b['points'])
            record.update(points=[a['points'], b['points']], recomputed=round(calc, 6),
                          delta=round(abs(calc - (probs[0] if probs else 0)), 6))
            if probs is None or abs(calc - probs[0]) > TOLERANCE:
                mismatches.append(record)
        elif len(inputs) == 2:
            # Rows whose inputs came from a details file carry fractional points.
            pa, pb = (i.get('points') for i in inputs)
            calc = win_probability(pa, pb)
            record.update(points=[pa, pb], recomputed=round(calc, 6),
                          delta=round(abs(calc - (probs[0] if probs else 0)), 6),
                          note='recomputed from the row inputs (details-file points)')
            if probs is None or abs(calc - probs[0]) > TOLERANCE:
                mismatches.append(record)
        checks.append(record)

    # Pre-registered prices for live fixtures the published snapshot does not cover.
    covered = {str(m['id']) for m in published['matches']}
    gaps = []
    for live in upcoming:
        if str(live['id']) in covered:
            continue
        names = live['teams']
        a, why_a = resolve(rows, names[0])
        b, why_b = resolve(rows, names[1])
        rec = {'id': live['id'], 'teams': names, 'competition': live['competition'],
               'starts_at': live['starts_at'], 'a': why_a, 'b': why_b}
        if a and b:
            calc = win_probability(a['points'], b['points'])
            rec.update(points=[a['points'], b['points']], probabilities=[round(calc, 4), round(1 - calc, 4)],
                       pick=names[0] if calc >= 0.5 else names[1], basis='Valve official standings (recomputed)')
        gaps.append(rec)

    report = {
        'schema_version': 1,
        'session': 'arena-3cf793ef',
        'observed_at': now(),
        'method': {
            'source': HTML,
            'fetch': meta,
            'formula': 'p = 1/(1+10^(g*(points_b-points_a)/400)), g = 1/sqrt(1+3*(ln10/400)^2*RD^2/pi^2), RD=75',
            'completeness_rule': 'only rows with a complete five-player roster are eligible; duplicates fail closed',
        },
        'published_valve_rows': len(checks),
        'reproduced_within_tolerance': len(checks) - len(mismatches),
        'tolerance': TOLERANCE,
        'mismatches': mismatches,
        'checks': checks,
        'live_fixtures_not_in_published_snapshot': len(gaps),
        'uncovered_with_recomputed_price': sum(1 for g in gaps if 'probabilities' in g),
        'uncovered_without_price': sum(1 for g in gaps if 'probabilities' not in g),
        'uncovered': gaps,
    }
    (out / 'valve-verification.json').write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ('published_valve_rows', 'reproduced_within_tolerance',
                                             'mismatches', 'live_fixtures_not_in_published_snapshot',
                                             'uncovered_with_recomputed_price',
                                             'uncovered_without_price')}, indent=1)[:2600])
    for g in gaps:
        print(g['id'], g['teams'], g.get('probabilities'), g.get('pick'), '|', g['a'], '/', g['b'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
