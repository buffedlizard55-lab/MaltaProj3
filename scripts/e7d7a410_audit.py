"""Read-only coverage audit for session arena-e7d7a410.

Why this exists
---------------
The brief asks for a pick and a source for *every* Hotspawn CS2 fixture, never a
filled-in default, and a separate register for whatever cannot be priced. The
published site already enforces that per row, but nothing compared the complete
picks feed (`data/origination.json`) with the inventory snapshot that the site
actually lists. This audit performs that join by Hotspawn fixture id and fails
closed:

  * a fixture with no complete-feed row is a defect, not a blank;
  * the row's team names and scheduled start must match the inventory;
  * probabilities must be two numbers in (0, 1) summing to 1;
  * `pick_index` must point at the favourite (an exact tie is allowed, and the
    published tie-break must be the one on the row);
  * every row needs an https source;
  * external money lines and model estimates are counted separately, and every
    model-only row is reprinted with the reason it has no line.

It never writes to the data the site publishes. `--strict` exits 1 on any defect
so a workflow can stop before publication.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MONEY_METHODS = frozenset({'market', 'bookmaker', 'consensus', 'reference'})
MODEL_METHODS = frozenset({'model', 'network'})
TOL = 1e-6


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _probabilities(row: dict[str, Any]) -> list[float] | None:
    values = row.get('probabilities')
    if not isinstance(values, list) or len(values) != 2:
        return None
    out = []
    for value in values:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        out.append(float(value))
    return out


def _pick_from(probabilities: list[float]) -> int:
    """The published rule: favourite wins, exact tie goes to team 0."""
    return 0 if probabilities[0] >= probabilities[1] else 1


def audit_fixture(match: dict[str, Any], completed: dict[str, Any] | None) -> dict[str, Any]:
    """Audit one inventory fixture against its complete-feed row.

    `match` is an entry from data/latest.json, `completed` the same id from
    data/origination.json (or None). Pure function so tests can pin every rule.
    """
    row: dict[str, Any] = {
        'id': match['id'],
        'competition': match.get('competition'),
        'teams': [t.get('name') for t in match.get('teams', [])],
        'starts_at': match.get('starts_at'),
        'locks_at': match.get('locks_at'),
        'availability': match.get('availability'),
        'featured_method': (match.get('analysis') or {}).get('method'),
        'defects': [],
    }
    if completed is None:
        row['defects'].append('no complete-picks row for this fixture')
        return row

    origination = completed.get('origination') or {}
    probabilities = _probabilities(origination)
    row.update(
        method=origination.get('method'),
        family=origination.get('family'),
        label=origination.get('label'),
        source=origination.get('source'),
        source_url=origination.get('source_url'),
        observed_at=origination.get('observed_at'),
        probabilities=probabilities,
        pick_index=completed.get('pick_index'),
        pick=(row['teams'][completed['pick_index']] if completed.get('pick_index') in (0, 1) and len(row['teams']) == 2 else None),
        money_line=origination.get('method') in MONEY_METHODS,
    )

    if not origination:
        row['defects'].append('complete row has no origination block')
    if probabilities is None:
        row['defects'].append('probabilities are not two numeric values')
    else:
        if not all(0.0 < p < 1.0 for p in probabilities):
            row['defects'].append('probability outside (0, 1)')
        if abs(sum(probabilities) - 1.0) > TOL:
            row['defects'].append(f'probabilities sum to {sum(probabilities):.6f}')
        expected = _pick_from(probabilities)
        if completed.get('pick_index') != expected:
            row['defects'].append(f'pick_index {completed.get("pick_index")} is not the favourite ({expected})')
    if completed.get('pick_index') not in (0, 1):
        row['defects'].append('missing pick_index')

    url = str(origination.get('source_url') or '')
    if not url.startswith('https://'):
        row['defects'].append('source_url is not https')

    inventory_teams = row['teams']
    feed_teams = [t.get('name') for t in completed.get('teams', [])]
    if feed_teams != inventory_teams:
        row['defects'].append(f'team names differ: inventory {inventory_teams} vs feed {feed_teams}')
    if str(completed.get('starts_at')) != str(match.get('starts_at')):
        row['defects'].append(f'start time differs: inventory {match.get("starts_at")} vs feed {completed.get("starts_at")}')

    method = origination.get('method')
    if method not in MONEY_METHODS and method not in MODEL_METHODS:
        row['defects'].append(f'unrecognised method {method!r}')
    if method in MODEL_METHODS:
        row['no_line_reason'] = origination.get('limitation') or origination.get('detail')
        row['no_line_research'] = origination.get('research')
    return row


def build_report(latest: dict[str, Any], completed: dict[str, Any]) -> dict[str, Any]:
    active = [m for m in latest.get('matches', [])
              if m.get('availability') in {'open', 'locked', 'unknown_lock'}]
    feed = {str(m['id']): m for m in completed.get('matches', [])}
    rows = [audit_fixture(match, feed.get(str(match['id']))) for match in active]
    active_ids = {str(m['id']) for m in active}
    orphans = sorted(set(feed) - active_ids)

    defects = [{'id': row['id'], 'teams': row.get('teams'), 'defects': row['defects']}
               for row in rows if row['defects']]
    money = [r for r in rows if r.get('money_line')]
    model = [r for r in rows if r.get('method') in MODEL_METHODS]

    return {
        'schema_version': 1,
        'session': 'arena-e7d7a410',
        'audited_at': _iso_now(),
        'inventory_generated_at': latest.get('generated_at'),
        'picks_feed_generated_at': completed.get('generated_at'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'inventory_definition': latest.get('inventory_definition'),
        'inventory_crosscheck': latest.get('inventory_crosscheck'),
        'inventory_counts': latest.get('counts'),
        'summary': {
            'active_fixtures': len(active),
            'with_pick': sum(1 for r in rows if r.get('pick') and not r['defects']),
            'without_pick': sum(1 for r in rows if not r.get('pick')),
            'defective_rows': len(defects),
            'money_line_resolved': len(money),
            'model_only_no_betting_line': len(model),
            'featured_blank_active': sum(1 for m in active if not m.get('analysis')),
            'no_line_share': round(len(model) / len(active), 4) if active else None,
            'orphan_picks_feed_rows': len(orphans),
        },
        'methods': {method: sum(1 for r in rows if r.get('method') == method)
                    for method in sorted({r.get('method') for r in rows if r.get('method')})},
        'orphan_picks_feed_rows': orphans,
        'defects': defects,
        'no_pick': [{'id': r['id'], 'competition': r.get('competition'), 'teams': r.get('teams'),
                     'starts_at': r.get('starts_at'), 'defects': r['defects']}
                    for r in rows if not r.get('pick')],
        'model_only_no_line': [{'id': r['id'], 'competition': r.get('competition'), 'teams': r.get('teams'),
                                'starts_at': r.get('starts_at'), 'pick': r.get('pick'),
                                'probabilities': r.get('probabilities'), 'label': r.get('label'),
                                'source': r.get('source'), 'source_url': r.get('source_url'),
                                'limitation': r.get('no_line_reason')}
                               for r in model],
        'rows': rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report['summary']
    lines = [
        '# arena-e7d7a410 — live coverage audit',
        '',
        f"Audited **{report['audited_at']}** against the inventory observed "
        f"**{report['inventory_observed_at']}** (snapshot {report['inventory_generated_at']}, "
        f"picks feed {report['picks_feed_generated_at']}).",
        '',
        '| Check | Result |',
        '| --- | --- |',
        f"| Active Hotspawn CS2 fixtures | **{s['active_fixtures']}** |",
        f"| With a pick and no defect | **{s['with_pick']}** |",
        f"| Without a pick | **{s['without_pick']}** |",
        f"| Defective rows | **{s['defective_rows']}** |",
        f"| Resolved by an external money line | **{s['money_line_resolved']}** |",
        f"| Model-only estimate (no betting line) | **{s['model_only_no_betting_line']}** |",
        f"| Featured exact-name method left blank (resolved by the complete feed) | **{s['featured_blank_active']}** |",
        f"| Complete-feed rows with no active fixture | **{s['orphan_picks_feed_rows']}** |",
        '',
        'Money methods: ' + ', '.join(f'{k} {v}' for k, v in report['methods'].items() if k in MONEY_METHODS)
        + '. Model methods: ' + ', '.join(f'{k} {v}' for k, v in report['methods'].items() if k in MODEL_METHODS) + '.',
        '',
    ]
    if report['defects']:
        lines += ['## Defects', '']
        for d in report['defects']:
            lines.append(f"- `{d['id']}` {d['teams']}: " + '; '.join(d['defects']))
        lines.append('')
    else:
        lines += ['No defective row: every active fixture has two probabilities in (0, 1) summing to 1, '
                  'a pick at the favourite, an https source, and the same team names and start time as the inventory.', '']
    lines += ['## Picks without an external betting line', '',
              'Each row keeps a labelled research estimate, the source actually used and the reason no market was bound. '
              'It is never presented as a betting price.', '']
    if report['model_only_no_line']:
        lines += ['| Fixture | Competition | Start | Pick | Estimate | Source |',
                  '| --- | --- | --- | --- | --- | --- |']
        for r in report['model_only_no_line']:
            teams = ' vs '.join(t or '?' for t in r['teams'])
            probs = r['probabilities'] or []
            pick = r['pick'] or '—'
            estimate = f"{pick} {probs[r['probabilities'].index(max(probs))] * 100:.1f}%" if probs else '—'
            lines.append(f"| {teams} | {r['competition']} | {r['starts_at']} | {pick} | {estimate} | "
                         f"[{r['source']}]({r['source_url']}) |")
        lines.append('')
        for r in report['model_only_no_line']:
            lines.append(f"- `{r['id']}` {' vs '.join(t or '?' for t in r['teams'])}: {r['limitation']}")
        lines.append('')
    else:
        lines += ['None: every active fixture had an external two-sided price at this observation.', '']
    if report['no_pick']:
        lines += ['## Fixtures with no pick at all', '']
        for r in report['no_pick']:
            lines.append(f"- `{r['id']}` {' vs '.join(t or '?' for t in r['teams'])}: " + '; '.join(r['defects']))
        lines.append('')
    lines += ['## Inventory basis', '',
              f"{report['inventory_definition'] or 'Hotspawn public fixture inventory'}. "
              f"Cross-check: {report['inventory_crosscheck']}.", '']
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--latest', default='data/latest.json')
    parser.add_argument('--origination', default='data/origination.json')
    parser.add_argument('--out', default='data/research/e7d7a410')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args(argv)

    latest = json.loads(Path(args.latest).read_text())
    completed = json.loads(Path(args.origination).read_text())
    report = build_report(latest, completed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'live-coverage-audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    (out / 'live-coverage-audit.md').write_text(render_markdown(report))

    s = report['summary']
    print(f"active {s['active_fixtures']} | picks {s['with_pick']} | without {s['without_pick']} | "
          f"defects {s['defective_rows']} | money {s['money_line_resolved']} | model-only {s['model_only_no_betting_line']}")
    for defect in report['defects']:
        print(f"DEFECT {defect['id']}: {'; '.join(defect['defects'])}")
    if not args.strict:
        return 0
    if report['defects']:
        return 1
    if not latest.get('coverage_complete', True):
        print('STRICT: the inventory snapshot is marked incomplete')
        return 1
    if not report['summary']['active_fixtures']:
        print('STRICT: no active fixture in the snapshot — zero coverage is not evidence of coverage')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
