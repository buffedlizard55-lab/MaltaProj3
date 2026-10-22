"""Session-only (arena-3cf793ef) report on what the *live* ladder produced.

Runs after ``scripts.collect`` and ``scripts.originate --live`` and writes one
compact, dated document that answers a single question per fixture:

    for every CS2 match Hotspawn lists with a start in the future,
    what did the origination ladder produce - a pick or an explicit reason?

It writes only ``data/research/3cf793ef/ladder-<utc>.json``. It never edits
``data/latest.json`` or ``data/origination.json`` and never prices anything.

Usage: python -m scripts.3cf793ef_ladder_report
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
OUT_DIR = Path('data/research/3cf793ef')


def stamp(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None


def main() -> int:
    now = datetime.now(UTC)
    latest = json.loads(Path('data/latest.json').read_text())
    orig = json.loads(Path('data/origination.json').read_text())
    rows = {str(m['id']): m for m in orig.get('matches') or []}

    upcoming = []
    for m in latest['matches']:
        start = stamp(m.get('starts_at'))
        if not start or start <= now:
            continue
        row = rows.get(str(m['id']))
        o = (row or {}).get('origination') or {}
        trail = [{'stage': r.get('stage'), 'status': r.get('status')}
                 for r in (row or {}).get('research') or []]
        upcoming.append({
            'id': m['id'],
            'teams': [t['name'] for t in m['teams']],
            'competition': m.get('competition'),
            'starts_at': m.get('starts_at'),
            'tier': m.get('tier'),
            'in_ladder': row is not None,
            'probabilities': o.get('probabilities'),
            'pick': ([t['name'] for t in m['teams']][row['pick_index']]
                     if row and row.get('pick_index') in (0, 1) else None),
            'method': o.get('method'),
            'label': o.get('label'),
            'source': o.get('source'),
            'source_url': o.get('source_url'),
            'observed_at': o.get('observed_at'),
            'limitations': (row or {}).get('limitations') or [],
            'research': trail,
        })

    unpriced = [u for u in upcoming if not u['probabilities'] or u['pick'] is None]
    report = {
        'schema_version': 1,
        'session': 'arena-3cf793ef',
        'written_at': now.isoformat(timespec='seconds'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'ladder_generated_at': orig.get('generated_at'),
        'inventory_records': len(latest['matches']),
        'upcoming': len(upcoming),
        'upcoming_in_ladder': sum(1 for u in upcoming if u['in_ladder']),
        'upcoming_with_pick': len(upcoming) - len(unpriced),
        'upcoming_without_pick': len(unpriced),
        'methods': {},
        'fixtures': upcoming,
        'without_pick': unpriced,
    }
    for u in upcoming:
        key = u['method'] or ('no-line' if not u['probabilities'] else 'unlabelled')
        report['methods'][key] = report['methods'].get(key, 0) + 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"ladder-{now.strftime('%Y%m%dT%H%MZ')}.json"
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in ('inventory_records', 'upcoming', 'upcoming_in_ladder',
                                             'upcoming_with_pick', 'upcoming_without_pick',
                                             'methods')}, indent=1))
    for u in unpriced:
        print('NO PICK', u['id'], u['teams'], '|', u['competition'], '|',
              '; '.join(f"{r['stage']}={r['status']}" for r in u['research'][-3:]))
    print('report:', path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
