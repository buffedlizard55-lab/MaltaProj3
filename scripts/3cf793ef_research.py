"""Session-only (arena-3cf793ef) independent verification + line-source probe.

Read-only. Nothing here writes a probability, a pick, an alias or a match
record. It records what the public sources actually returned, so a human can
re-check every value in ``data/research/3cf793ef/``.

Stages
------
1. Live Hotspawn CS2 scheduled-fixture API: inventory, duplicates, tiers and
   the split between fixtures whose start is still in the future and the
   past-start records the API still calls ``scheduled``.
2. The live published snapshot (``data/latest.json``) and the live published
   origination ladder (``data/origination.json``): every active fixture with
   its basis, both probabilities and the source it claims.
3. Drift check: the same fixture id in the API and in the published snapshot
   must agree on teams, competition and start time.
4. Gap analysis: active fixtures with no published probability, and the ones
   that are model-only (no money line), listed with exact team names so a
   targeted HLTV / esportsbook lookup can be made for each.

Usage: python -m scripts.3cf793ef_research [--out data/research/3cf793ef/live]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
       '?sport_alias=cs2&status=scheduled&tenantId=1')
SITE = 'https://buffedlizard55-lab.github.io/MaltaProj3'
LOBBY = 'https://play.hotspawn.com/lobby'
PICKEMS = 'https://play.hotspawn.com/cs2-pickems'


def now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')


def get(url: str, timeout: int = 30) -> dict:
    record = {'url': url, 'method': 'GET', 'observed_at': now()}
    try:
        r = requests.get(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'},
                         timeout=timeout, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001 - the failure itself is the evidence
        record.update(status=None, error=f'{type(exc).__name__}: {exc}'[:300])
        return record
    record.update(status=r.status_code, final_url=r.url, content_type=r.headers.get('content-type'),
                  bytes=len(r.content), text=r.text)
    return record


def epoch_ms(value) -> str | None:
    try:
        ms = int(str(value))
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat(timespec='seconds')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data/research/3cf793ef/live')
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary: dict = {'observed_at': now(), 'sources': [], 'stages': {}}

    # ── stage 1: live inventory ────────────────────────────────────────────
    api = get(API, timeout=45)
    summary['sources'].append({k: api[k] for k in ('url', 'status', 'observed_at', 'bytes')
                               if k in api} | ({'error': api['error']} if 'error' in api else {}))
    fixtures: list[dict] = []
    if api.get('status') == 200:
        (out / 'hotspawn-fixtures.json').write_text(api['text'])
        try:
            fixtures = json.loads(api['text'])
        except json.JSONDecodeError as exc:
            summary['stages']['inventory'] = {'parsed': False, 'error': str(exc)}
    ids = [str(f.get('id')) for f in fixtures]
    dupes = sorted([i for i, n in Counter(ids).items() if n > 1])
    stamp = datetime.now(UTC)
    rows = []
    for f in fixtures:
        start = epoch_ms(f.get('scheduled_start_time'))
        rows.append({
            'id': str(f.get('id')),
            'teams': [f.get('participants0_name'), f.get('participants1_name')],
            'team_ids': [str(f.get('participants0_id')), str(f.get('participants1_id'))],
            'competition': f.get('competition_name'),
            'competition_id': str(f.get('competition_id')),
            'starts_at': start,
            'locks_at': epoch_ms(f.get('lock_time')),
            'tier': f.get('tier'),
            'best_of': f.get('best_of'),
            'series_format': f.get('series_format'),
            'source_status': f.get('status'),
            'upcoming': bool(start and datetime.fromisoformat(start) > stamp),
            # Hotspawn's own community "% picked" is never a probability input.
            'crowd_picked_percent': [f.get('participants0_picked_percent'),
                                     f.get('participants1_picked_percent')],
            'source_url': f"https://www.hotspawn.com/matches/x-{f.get('id')}",
        })
    upcoming = sorted([r for r in rows if r['upcoming']], key=lambda r: r['starts_at'])
    summary['stages']['inventory'] = {
        'records': len(rows),
        'unique_ids': len(set(ids)),
        'duplicate_ids': dupes,
        'tiers': dict(Counter(r['tier'] for r in rows)),
        'upcoming': len(upcoming),
        'past_start_still_scheduled': len(rows) - len(upcoming),
        'best_of_published': sum(1 for r in rows if r['best_of'] not in (None, '')),
        'community_percent_published': sum(
            1 for r in rows if any((p or 0) > 0 for p in r['crowd_picked_percent'])),
        'earliest_upcoming_start': upcoming[0]['starts_at'] if upcoming else None,
        'latest_upcoming_start': upcoming[-1]['starts_at'] if upcoming else None,
    }

    # ── stage 2: the live published snapshot and ladder ────────────────────
    published: dict = {}
    for name in ('latest.json', 'origination.json'):
        got = get(f'{SITE}/data/{name}')
        summary['sources'].append({'url': got['url'], 'status': got.get('status'),
                                   'observed_at': got['observed_at'], 'bytes': got.get('bytes')})
        if got.get('status') == 200:
            (out / f'published-{name}').write_text(got['text'])
            try:
                published[name] = json.loads(got['text'])
            except json.JSONDecodeError:
                pass

    latest = published.get('latest.json') or {}
    orig = published.get('origination.json') or {}
    summary['stages']['published'] = {
        'latest_generated_at': latest.get('generated_at'),
        'latest_counts': latest.get('counts'),
        'latest_coverage_complete': latest.get('coverage_complete'),
        'origination_generated_at': orig.get('generated_at'),
        'origination_counts': orig.get('counts'),
    }

    # ── stage 3: drift check against the live API ──────────────────────────
    api_by_id = {r['id']: r for r in rows}
    drift = []
    for m in (orig.get('matches') or []):
        mid = str(m.get('id'))
        live = api_by_id.get(mid)
        if not live:
            drift.append({'id': mid, 'issue': 'published fixture absent from the live scheduled API'})
            continue
        pub_teams = [t.get('name') for t in m.get('teams') or []]
        if pub_teams != live['teams']:
            drift.append({'id': mid, 'issue': 'team name differs',
                          'published': pub_teams, 'live': live['teams']})
        if (m.get('starts_at') or '')[:16] != (live['starts_at'] or '')[:16]:
            drift.append({'id': mid, 'issue': 'start time differs',
                          'published': m.get('starts_at'), 'live': live['starts_at']})
        if (m.get('competition') or '') != (live['competition'] or ''):
            drift.append({'id': mid, 'issue': 'competition differs',
                          'published': m.get('competition'), 'live': live['competition']})
    summary['stages']['drift'] = {'checked': len(orig.get('matches') or []), 'issues': drift}

    # ── stage 4: per-fixture pick status and gaps ──────────────────────────
    by_id = {str(m.get('id')): m for m in (orig.get('matches') or [])}
    active, gaps, model_only = [], [], []
    for live in upcoming:
        pub = by_id.get(live['id'])
        if not pub:
            gaps.append({**live, 'reason': 'not in the published origination ladder at all'})
            continue
        o = pub.get('origination') or {}
        probs = pub.get('featured_probabilities') or o.get('probabilities')
        row = {
            'id': live['id'],
            'teams': live['teams'],
            'competition': live['competition'],
            'starts_at': live['starts_at'],
            'tier': live['tier'],
            'method': pub.get('featured_method'),
            'label': o.get('label'),
            'probabilities': probs,
            'pick': None,
            'source': o.get('source'),
            'source_url': o.get('source_url'),
            'observed_at': o.get('observed_at'),
        }
        if probs:
            idx = pub.get('pick_index', pub.get('featured_pick_index'))
            row['pick'] = live['teams'][idx] if isinstance(idx, int) and idx in (0, 1) else None
        active.append(row)
        if not probs:
            gaps.append({**row, 'reason': 'published with blank probabilities'})
        elif (pub.get('featured_method') or '').lower() == 'model':
            model_only.append(row)
    summary['stages']['active'] = {
        'count': len(active),
        'with_probabilities': sum(1 for a in active if a['probabilities']),
        'model_only': len(model_only),
        'money_line': sum(1 for a in active
                          if (a['method'] or '').lower() in ('market', 'bookmaker', 'consensus')),
        'methods': dict(Counter((a['method'] or 'blank') for a in active)),
        'no_source_url': sum(1 for a in active if a['probabilities'] and not a['source_url']),
        'fixtures': active,
    }
    summary['stages']['gaps'] = {'count': len(gaps), 'fixtures': gaps}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1))
    (out / 'upcoming.json').write_text(json.dumps(upcoming, indent=1))

    # compact console output, deliberately terse for the run log
    print(json.dumps({k: summary['stages'][k] for k in
                      ('inventory', 'published', 'drift')}, indent=1))
    print(f"ACTIVE {len(active)} | with probs {summary['stages']['active']['with_probabilities']}"
          f" | model-only {len(model_only)} | gaps {len(gaps)}")
    for a in active:
        p = a['probabilities']
        shown = f"{p[0]:.3f}/{p[1]:.3f}" if p else 'BLANK'
        print(f"  {a['id']} {a['starts_at']} {a['teams'][0]} vs {a['teams'][1]}"
              f" | {a['competition']} | {a['method']} | {shown} | pick={a['pick']}"
              f" | {a['source']}")
    for g in gaps:
        print(f"  GAP {g['id']} {g.get('starts_at')} {g['teams'][0]} vs {g['teams'][1]}"
              f" | {g.get('competition')} | {g['reason']}")
    print('VERIFY-JSON ' + json.dumps({
        'records': len(rows), 'upcoming': len(upcoming), 'active': len(active),
        'duplicates': dupes, 'drift': len(drift), 'gaps': len(gaps)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
