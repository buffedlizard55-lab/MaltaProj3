"""Session 4c972a51: read-only diagnostics for the live resolver output.

Reads a collected snapshot (``latest.json``) plus the origination replay
(``origination.json``) and writes a compact, reviewable diagnostic that names
every active fixture, whether it carries a pick, which rung priced it, and —
for the fixtures that stayed blank — every rung that failed and why.

It computes nothing. Every number it prints is copied from the two files it
reads, so it can never invent a probability or a pick.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ACTIVE = {'open', 'locked', 'unknown_lock'}


def _probabilities(analysis: dict | None) -> list | None:
    if not analysis:
        return None
    probs = analysis.get('probabilities') or analysis.get('probability') or analysis.get('model_probabilities')
    return probs if isinstance(probs, list) else None


def _method(analysis: dict | None) -> str | None:
    if not analysis:
        return None
    return analysis.get('method') or analysis.get('label')


def _quote_providers(origination: dict | None) -> list:
    if not origination:
        return []
    out = []
    for quote in origination.get('quotes') or []:
        out.append({
            'provider': quote.get('provider'),
            'family': quote.get('family'),
            'odds': quote.get('odds'),
            'probabilities': quote.get('probabilities'),
            'event_id': quote.get('event_id'),
            'source_url': quote.get('source_url'),
        })
    return out


def _failed_stages(record: dict) -> list:
    failed = []
    for stage in record.get('research') or []:
        if stage.get('status') in {'unresolved', 'unavailable', 'rejected', 'missing'}:
            failed.append({
                'stage': stage.get('stage'),
                'status': stage.get('status'),
                'detail': stage.get('detail'),
                'source_url': stage.get('source_url'),
            })
    return failed


def _resolved_stage(record: dict) -> dict | None:
    for stage in reversed(record.get('research') or []):
        if stage.get('status') in {'resolved', 'checked'}:
            return {'stage': stage.get('stage'), 'status': stage.get('status'),
                    'detail': stage.get('detail'), 'source_url': stage.get('source_url')}
    return None


def diagnose(data_dir: Path, out_dir: Path) -> dict:
    latest = json.loads((data_dir / 'latest.json').read_text())
    origination_path = data_dir / 'origination.json'
    origination = json.loads(origination_path.read_text()) if origination_path.exists() else {}
    by_id = {str(m.get('id')): m for m in origination.get('matches') or []}

    fixtures = []
    for match in latest.get('matches') or []:
        if match.get('availability') not in ACTIVE:
            continue
        record = by_id.get(str(match.get('id'))) or {}
        analysis = record.get('origination')
        featured = match.get('analysis')
        probs = _probabilities(analysis) or _probabilities(featured)
        fixtures.append({
            'id': match.get('id'),
            'teams': [t.get('name') for t in match.get('teams') or []],
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'tier': match.get('tier'),
            'best_of': match.get('best_of'),
            'source_url': match.get('source_url'),
            'match_page': match.get('source_url') if str(match.get('source_url', '')).startswith('https://www.hotspawn.com/matches/') else None,
            'featured_method': _method(featured),
            'method': _method(analysis) or _method(featured),
            'label': (analysis or {}).get('label') or (featured or {}).get('label'),
            'probabilities': probs,
            'pick': (analysis or {}).get('pick') or (featured or {}).get('pick'),
            'source': (analysis or {}).get('source'),
            'source_url_used': (analysis or {}).get('source_url'),
            'model': (analysis or {}).get('model') or (analysis or {}).get('model_crosscheck'),
            'quotes': _quote_providers(analysis),
            'resolved_stage': _resolved_stage(record),
            'failed_stages': _failed_stages(record),
            'limitations': record.get('limitations') or match.get('limitations') or [],
            'status': 'picked' if probs else 'unresolved',
        })

    unresolved = [f for f in fixtures if f['status'] == 'unresolved']
    report = {
        'session': 'arena-4c972a51',
        'observed_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'snapshot_generated_at': latest.get('generated_at'),
        'counts': latest.get('counts'),
        'origination_counts': origination.get('counts'),
        'live_collection': origination.get('live_collection'),
        'active': len(fixtures),
        'with_pick': len(fixtures) - len(unresolved),
        'unresolved': len(unresolved),
        'fixtures': fixtures,
        'unresolved_ids': [f['id'] for f in unresolved],
        'source_health': [
            {'name': s.get('name'), 'status': s.get('status'), 'url': s.get('url'),
             'records': s.get('records'), 'detail': (s.get('detail') or '')[:400]}
            for s in latest.get('sources') or []
        ],
        'origination_sources': origination.get('sources'),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'live-diagnostic.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    lines = [
        f"# Live diagnostic {report['observed_at']}",
        '',
        f"Snapshot `{report['snapshot_generated_at']}` · {report['active']} active · "
        f"{report['with_pick']} with a pick · **{report['unresolved']} unresolved**",
        '',
        '## Unresolved fixtures',
        '',
        '| Match | Competition | Method tried | Why it stayed blank |',
        '| --- | --- | --- | --- |',
    ]
    for f in unresolved:
        why = '; '.join(
            f"{s['stage']}: {s['detail']}" for s in f['failed_stages'][-3:] if s.get('detail')
        ) or 'no failed stage recorded'
        lines.append(f"| {' vs '.join(f['teams'])} (`{f['id']}`) | {f['competition']} | "
                     f"{f['method'] or 'none'} | {why.replace('|', '/')} |")
    lines += ['', '## Picked fixtures', '', '| Match | Method | Pick | Probabilities | Source |', '| --- | --- | --- | --- | --- |']
    for f in fixtures:
        if f['status'] != 'picked':
            continue
        probs = ', '.join(f'{p:.4f}' for p in f['probabilities'] or [])
        lines.append(f"| {' vs '.join(f['teams'])} (`{f['id']}`) | {f['label'] or f['method']} | "
                     f"{f['pick']} | {probs} | {f['source'] or ''} |")
    (out_dir / 'live-diagnostic.md').write_text('\n'.join(lines) + '\n')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('data/research/4c972a51'))
    args = parser.parse_args()
    report = diagnose(args.data, args.out)
    print(json.dumps({
        'active': report['active'],
        'with_pick': report['with_pick'],
        'unresolved': report['unresolved'],
        'unresolved_ids': report['unresolved_ids'],
    }, indent=2))


if __name__ == '__main__':
    main()
