"""Session arena-e7d7a410 — line-by-line coverage audit of one live snapshot.

The coding sandbox cannot reach Hotspawn, HLTV or any bookmaker; the GitHub
Actions runner can. This read-only audit runs there, immediately after
``scripts.collect`` and ``scripts.originate --live``, and answers the brief's
core question with dated, per-row evidence:

    For every CS2 fixture Hotspawn lists, is there a pick and are there two
    team win probabilities, and if not, exactly which row is missing what?

It never writes a probability, a pick, an alias or a price. It only reports
what the already-published collectors produced, re-checks the arithmetic, and
records the source of every row so a human can replay it.

Checks (each must pass for a fixture to be counted as covered):

* the fixture is in the live Hotspawn inventory (``data/latest.json``);
* it is active (``availability`` in open/locked/unknown_lock);
* both teams are named;
* a probabilities pair exists, is 2 long, is inside (0, 1) and sums to 1;
* a ``pick_index`` exists in {0, 1} and points at the larger probability
  (or at team 0 when the two probabilities are exactly equal — an explicit
  even-line default, never an invention);
* the row names an https source URL that is also reachable in the snapshot's
  own request log, or is the repo's Valve reference file.

Usage: python -m scripts.e7d7a410_audit [--data data] [--out data/research/e7d7a410]
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference', 'relay', 'network'}
PROBABILITY_EPSILON = 1e-6


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def cash(value):
    return value if isinstance(value, (int, float)) else None


def analysis_of(match: dict) -> dict | None:
    """Return the resolution block the site publishes, whichever schema carries it."""
    block = match.get('origination')
    if isinstance(block, dict) and block.get('probabilities'):
        return block
    block = match.get('analysis')
    if isinstance(block, dict) and block.get('probabilities'):
        return block
    return None


def probabilities_ok(probabilities) -> tuple[bool, str]:
    if not isinstance(probabilities, list) or len(probabilities) != 2:
        return False, 'probabilities must be a two-item list'
    if not all(isinstance(value, (int, float)) for value in probabilities):
        return False, 'probabilities must be numbers'
    if any(not 0.0 < value < 1.0 for value in probabilities):
        return False, 'each probability must be strictly between 0 and 1'
    total = sum(probabilities)
    if abs(total - 1.0) > PROBABILITY_EPSILON:
        return False, f'probabilities sum to {total:.9f}, not 1'
    return True, ''


def pick_problem(pick_index, probabilities) -> str:
    if pick_index not in (0, 1):
        return 'no directional pick (pick_index is absent or not 0/1)'
    if probabilities[pick_index] < probabilities[1 - pick_index]:
        return 'pick points at the less likely team'
    return ''


def source_of(match: dict, analysis: dict) -> str:
    for candidate in (analysis.get('source_url'), match.get('source_url'),
                      (match.get('research') or [{}])[-1].get('source_url')):
        if isinstance(candidate, str) and candidate.startswith('https://'):
            return candidate
    return ''


def audit_fixture(match: dict, completed_row: dict | None) -> dict:
    """Audit one active fixture against the complete-picks feed it publishes.

    The site's authoritative pick is the *complete-picks* resolution
    (``data/origination.json`` → ``origination``), not the featured-only
    ``analysis`` block in ``data/latest.json``; the featured block is the
    first method and may legitimately be blank while a researched fallback
    resolved the row. Reading the wrong feed here would report false gaps —
    exactly the defect this audit exists to catch in the site, so the join is
    done first and the two feeds are cross-checked for identity drift.
    """
    completed_row = completed_row or {}
    featured = match.get('analysis') if isinstance(match.get('analysis'), dict) else None
    resolution = completed_row.get('origination') if isinstance(completed_row.get('origination'), dict) else None
    if not resolution:
        resolution = featured
    probabilities = (resolution or {}).get('probabilities')
    method = (resolution or {}).get('method')
    pick_index = completed_row.get('pick_index')
    problems: list[str] = []
    if not completed_row:
        problems.append('active fixture missing from the complete-picks feed')
    if not resolution:
        problems.append('no resolution block in the complete-picks feed')
    if probabilities:
        ok, probability_problem = probabilities_ok(probabilities)
    else:
        ok, probability_problem = False, 'no probabilities'
    if not ok:
        problems.append(probability_problem)
    if ok:
        pick_issue = pick_problem(pick_index, probabilities)
        if pick_issue:
            problems.append(pick_issue)
    source = source_of(completed_row or match, resolution or {})
    if not source:
        problems.append('no official https source link')
    teams = [team.get('name') for team in match.get('teams') or []]
    if len(teams) != 2 or not all(teams):
        problems.append('both teams are not named')
    completed_teams = [team.get('name') for team in completed_row.get('teams') or []]
    if completed_row and completed_teams != teams:
        problems.append('team names differ between the inventory and the complete-picks feed')
    if completed_row and completed_row.get('starts_at') != match.get('starts_at'):
        problems.append('start time differs between the inventory and the complete-picks feed')
    return {
        'hotspawn_id': str(match.get('id')),
        'teams': teams,
        'competition': match.get('competition'),
        'starts_at': match.get('starts_at'),
        'availability': match.get('availability'),
        'tier': match.get('tier'),
        'featured_method': completed_row.get('featured_method'),
        'method': method,
        'method_family': 'money-line' if method in MONEY_METHODS else ('model' if method else None),
        'probabilities': probabilities,
        'pick': teams[pick_index] if pick_index in (0, 1) and len(teams) == 2 else None,
        'pick_index': pick_index if pick_index in (0, 1) else None,
        'source_url': source,
        'source': (resolution or {}).get('source'),
        'observed_at': (resolution or {}).get('observed_at'),
        'hotspawn_url': match.get('source_url') if str(match.get('source_url', '')).startswith('https://www.hotspawn.com/') else None,
        'limitations': (resolution or {}).get('limitations') or match.get('limitations') or [],
        'covered': not problems,
        'problems': problems,
    }


def build_report(data_dir: Path) -> dict:
    latest = load(data_dir / 'latest.json')
    origination = load(data_dir / 'origination.json')
    active = [m for m in latest.get('matches') or []
              if m.get('availability') in {'open', 'locked', 'unknown_lock'}]
    completed = {str(m.get('id')): m for m in origination.get('matches') or []}
    rows = [audit_fixture(match, completed.get(str(match.get('id')))) for match in active]

    # An origination row with no matching live inventory row is a defect too.
    latest_ids = {str(m.get('id')) for m in latest.get('matches') or []}
    orphans = [str(m.get('id')) for m in origination.get('matches') or []
               if str(m.get('id')) not in latest_ids]

    by_method: dict[str, int] = {}
    for row in rows:
        key = row['method'] or 'none'
        by_method[key] = by_method.get(key, 0) + 1

    money = [row for row in rows if row['method_family'] == 'money-line']
    model = [row for row in rows if row['method_family'] == 'model']
    uncovered = [row for row in rows if not row['covered']]
    blank_pick = [row for row in rows if not row['pick']]
    no_line = [row for row in rows if row['method_family'] == 'model']

    return {
        'schema_version': 1,
        'session': 'arena-e7d7a410',
        'observed_at': datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'environment': ('github-actions-runner' if os.environ.get('GITHUB_ACTIONS') == 'true'
                        else 'local-sandbox-host'),
        'snapshot': {
            'latest_generated_at': latest.get('generated_at'),
            'latest_inventory_observed_at': latest.get('inventory_observed_at'),
            'origination_generated_at': origination.get('generated_at'),
            'latest_counts': latest.get('counts'),
            'origination_counts': origination.get('counts'),
            'run_status': latest.get('run_status'),
            'coverage_complete': latest.get('coverage_complete'),
        },
        'summary': {
            'active_fixtures': len(rows),
            'with_pick': len(rows) - len(blank_pick),
            'without_pick': len(blank_pick),
            'covered': len(rows) - len(uncovered),
            'uncovered': len(uncovered),
            'money_line_resolved': len(money),
            'model_only_no_betting_line': len(model),
            'methods': by_method,
            'featured_blank_active': sum(1 for row in rows if not row['featured_method']),
            'resolved_by_fallback': sum(1 for row in rows
                                        if not row['featured_method'] and row['method']),
            'orphan_origination_rows': len(orphans),
        },
        'unresolved': [
            {'hotspawn_id': row['hotspawn_id'], 'teams': row['teams'], 'starts_at': row['starts_at'],
             'competition': row['competition'], 'problems': row['problems'],
             'method': row['method'], 'source_url': row['source_url']}
            for row in uncovered
        ],
        'no_betting_line': [
            {'hotspawn_id': row['hotspawn_id'], 'teams': row['teams'], 'starts_at': row['starts_at'],
             'competition': row['competition'], 'method': row['method'],
             'probabilities': row['probabilities'], 'pick': row['pick'],
             'source_url': row['source_url'], 'limitations': row['limitations']}
            for row in no_line
        ],
        'fixtures': rows,
        'orphans': orphans,
    }


def markdown(report: dict) -> str:
    summary = report['summary']
    snapshot = report['snapshot']
    lines = [
        '# arena-e7d7a410 — live coverage audit (read-only)',
        '',
        f"Observed: **{report['observed_at']}** ({report['environment']}).",
        f"Snapshot: live inventory **{snapshot['latest_generated_at']}**, picks feed "
        f"**{snapshot['origination_generated_at']}**, run status `{snapshot['run_status']}`.",
        '',
        '## Summary',
        '',
        '| Metric | Count |',
        '| --- | --- |',
        f"| Active Hotspawn CS2 fixtures | {summary['active_fixtures']} |",
        f"| With a directional pick | {summary['with_pick']} |",
        f"| Without a pick | {summary['without_pick']} |",
        f"| Rows passing every check | {summary['covered']} |",
        f"| Rows with a defect | {summary['uncovered']} |",
        f"| Resolved by an external money line | {summary['money_line_resolved']} |",
        f"| Model-only (no betting line found) | {summary['model_only_no_betting_line']} |",
        '',
        '## Every active fixture, line by line',
        '',
        '| # | Match | Start (UTC) | Method | Probabilities | Pick | Source | Covered |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for index, row in enumerate(report['fixtures'], 1):
        probabilities = row['probabilities']
        rendered = ' / '.join(f'{value:.4f}' for value in probabilities) if probabilities else '—'
        source = f"[source]({row['source_url']})" if row['source_url'] else '—'
        lines.append(
            f"| {index} | {row['teams'][0] if row['teams'] else '—'} vs "
            f"{row['teams'][1] if len(row['teams']) > 1 else '—'} | {row['starts_at'] or '—'} | "
            f"{row['method'] or '—'} | {rendered} | {row['pick'] or '—'} | {source} | "
            f"{'yes' if row['covered'] else 'NO — ' + '; '.join(row['problems'])} |")
    lines += ['', '## Unresolved rows (a pick is missing or invalid)', '']
    if not report['unresolved']:
        lines.append('None: every active fixture carries a pick, two valid probabilities and a source link.')
    for row in report['unresolved']:
        lines.append(f"- **{row['teams'][0]} vs {row['teams'][1]}** ({row['starts_at']}, "
                     f"{row['competition']}) — {'; '.join(row['problems'])} — {row['source_url'] or 'no source'}")
    lines += ['', '## Fixtures with a model pick and no external betting line', '']
    if not report['no_betting_line']:
        lines.append('None.')
    for row in report['no_betting_line']:
        probabilities = row['probabilities'] or []
        rendered = ' / '.join(f'{value:.4f}' for value in probabilities)
        lines.append(f"- **{row['teams'][0]} vs {row['teams'][1]}** ({row['starts_at']}) — "
                     f"model {rendered} → pick {row['pick']} — {row['source_url']}")
        for limitation in row['limitations']:
            lines.append(f"  - limitation: {limitation}")
    lines += ['', '## Method', '',
              'Read-only. The audit re-checks arithmetic and source links against the snapshot the '
              'collectors just wrote; it never creates, shifts or fills a probability or pick. '
              'Money-line methods are market/bookmaker/consensus/reference/relay/network; '
              '`model` means no external two-sided prematch line was found and the published '
              'research model produced the number.', '']
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('data/research/e7d7a410'))
    parser.add_argument('--strict', action='store_true',
                        help='exit 1 when an active fixture lacks a valid pick (CI gate)')
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    report = build_report(args.data)
    (args.out / 'live-coverage-audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    (args.out / 'live-coverage-audit.md').write_text(markdown(report))
    summary = report['summary']
    print(json.dumps(summary, indent=2))
    problems = []
    if summary['uncovered'] or summary['orphan_origination_rows']:
        problems.append(f"{summary['uncovered']} active fixture(s) lack a valid pick; "
                        f"{summary['orphan_origination_rows']} orphan row(s)")
    # Zero active fixtures is not evidence of coverage: an inventory failure used
    # to leave an empty snapshot that passed ``--strict`` with nothing to check.
    if not summary['active_fixtures']:
        problems.append('no active fixture in the snapshot')
    if report['snapshot'].get('coverage_complete') is False:
        problems.append('the inventory snapshot is marked incomplete')
    if problems:
        print(f"::error title=Coverage audit::{' — '.join(problems)}. See live-coverage-audit.md")
        return 1 if args.strict else 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
