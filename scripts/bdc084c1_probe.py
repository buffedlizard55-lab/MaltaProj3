"""Line-by-line coverage probe for fixtures Hotspawn added after a published snapshot.

Run: python -m scripts.bdc084c1_probe [--report data/research/bdc084c1]

This script is **read-only with respect to the published data**. It never writes a
probability, a pick or an alias and it never edits `data/latest.json`,
`data/origination.json`, `data/sources.json` or `data/origination/aliases.json`.
It answers one question that the four-hour publisher cannot answer from a single
snapshot: *when Hotspawn lists a new fixture between two published snapshots, does
the next refresh give that fixture a pick, and if not, what exactly stopped it?*

Inputs
------
* the published snapshot committed at ``HEAD`` (``git show HEAD:data/latest.json``,
  ``git show HEAD:data/origination.json``), i.e. what the live site was built from;
* the freshly collected ``data/latest.json`` and ``data/origination.json`` in the
  working tree (produced by ``python -m scripts.collect`` and
  ``python -m scripts.originate --live`` immediately before this script runs).

Output
------
``<report dir>/probe-report.json`` — observed timestamps, both inventory id sets,
every active fixture with the basis that actually produced its displayed number,
and a separate record for every fixture that is new since the published snapshot
including the reason it has no pick (read from the collector's own limitations).

Every value is copied from the two snapshots. Nothing is inferred.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from scripts.build import MONEY_METHODS, selected_fallback

ACTIVE = {'open', 'locked', 'unknown_lock'}


def committed(path: str) -> dict | None:
    """The snapshot as published (HEAD), or None when the file is new."""
    try:
        raw = subprocess.run(['git', 'show', f'HEAD:{path}'], check=True,
                             capture_output=True, text=True).stdout
    except subprocess.CalledProcessError:
        return None
    return json.loads(raw)


def host(url: str) -> str:
    try:
        return urlparse(str(url)).netloc.removeprefix('www.') or ''
    except ValueError:
        return ''


def fixture(row: dict, fallbacks: dict) -> dict:
    """One published row with the basis that actually produces its number.

    The selection rule is imported from ``scripts.build`` (``selected_fallback``)
    rather than reimplemented, so this report cannot disagree with the site about
    which record produced a row's displayed number.
    """
    fallback = selected_fallback(row, fallbacks) or {}
    record = fallback.get('origination')
    analysis = record or row.get('analysis')
    pick = fallback.get('pick_index') if record else row.get('pick_index')
    teams = [t.get('name') for t in row.get('teams') or []]
    out = {
        'id': str(row['id']),
        'teams': teams,
        'competition': row.get('competition'),
        'starts_at': row.get('starts_at'),
        'availability': row.get('availability'),
        'best_of': row.get('best_of'),
        'featured_method': (row.get('analysis') or {}).get('method'),
        'basis': None,
        'basis_is_researched_fallback': bool(record),
        'probabilities': None,
        'pick': None,
        'source': None,
        'source_url': None,
        'source_host': None,
        'limitations': row.get('limitations') or [],
    }
    if analysis:
        probabilities = list(analysis.get('probabilities') or [])
        out.update({
            'basis': analysis.get('method'),
            'label': analysis.get('label'),
            'probabilities': probabilities,
            'pick': (teams[pick] if pick is not None and 0 <= pick < len(teams) else None),
            'source': analysis.get('source'),
            'source_url': analysis.get('source_url'),
            'source_host': host(analysis.get('source_url') or ''),
            'observed_at': analysis.get('observed_at'),
        })
    return out


def write_markdown(report: dict, path: Path) -> None:
    """The same evidence in a form a reader can check without opening the JSON."""
    lines = [
        '# Snapshot coverage probe — session arena-bdc084c1',
        '',
        f"Observed **{report['observed_at']}** by `python -m scripts.bdc084c1_probe`, immediately after "
        '`scripts.collect` and `scripts.originate --live` in the same working tree. Every value '
        'below is copied from those two artifacts; nothing is inferred.',
        '',
        '## What is compared',
        '',
        f"* Published snapshot (committed at HEAD): `{report['published_snapshot']['generated_at']}`, "
        f"{report['published_snapshot']['inventory']} inventory records.",
        f"* Fresh snapshot: `{report['fresh_snapshot']['generated_at']}`, "
        f"{report['fresh_snapshot']['inventory']} inventory records, inventory cross-check "
        f"`{report['fresh_snapshot']['inventory_crosscheck']}`.",
        f"* New fixture ids since publication: **{len(report['fixtures']['new_since_published'])}** "
        f"({report['fixtures']['new_active']} active, {report['fixtures']['new_archived']} archived). "
        f"No longer listed: {len(report['fixtures']['no_longer_listed'])}.",
        '',
        '## Fixtures new since the published snapshot',
        '',
    ]
    if report['new_fixtures']:
        lines += ['| Hotspawn id | Fixture | Start (UTC) | State | Basis | Source |',
                  '| --- | --- | --- | --- | --- | --- |']
        for row in report['new_fixtures']:
            state = ('pick ' + row['pick']) if row['pick'] else (
                'probabilities, no side' if row['probabilities'] else '**no probability**')
            link = str(row.get('source_url') or '')
            link = link if link.startswith('http') else 'https://play.hotspawn.com/lobby'
            lines.append(f"| [{row['id']}]({link}) "
                         f"| {row['teams'][0]} vs {row['teams'][1]} | {row['starts_at']} | {state} "
                         f"| {row['basis'] or 'unresolved'} | {row['source_host'] or '—'} |")
    else:
        lines.append('None: the fresh snapshot lists exactly the fixtures the published one lists.')
    active = report['active']
    lines += [
        '',
        '## Active-fixture coverage in the fresh snapshot',
        '',
        f"* Active fixtures: **{active['total']}**",
        f"* With a directional pick: **{active['with_pick']}**",
        f"* With probabilities: **{active['with_probabilities']}**",
        f"* Priced from an external betting line: **{active['with_betting_line']}**",
        f"* Research model only (not a betting price): **{active['research_model_only']}**",
        f"* Basis mix: `{json.dumps(active['by_basis'], sort_keys=True)}`",
        f"* Source hosts: `{json.dumps(active['by_source_host'], sort_keys=True)}`",
        '',
    ]
    blanks = active['without_probabilities']
    if blanks:
        lines += ['## Active fixtures with no probability', '']
        for row in blanks:
            lines.append(f"* {row['teams'][0]} vs {row['teams'][1]} ({row['id']}, {row['starts_at']}) — "
                         f"{'; '.join(row['limitations'][:2]) or 'no limitation recorded'}")
        lines.append('')
    no_side = [r for r in active['without_pick'] if r['probabilities']]
    if no_side:
        lines += ['## Active fixtures with probabilities but no side', '']
        for row in no_side:
            lines.append(f"* {row['teams'][0]} vs {row['teams'][1]} ({row['id']}) — "
                         f"{row['probabilities'][0]:.4f} / {row['probabilities'][1]:.4f}")
        lines.append('')
    path.write_text('\n'.join(lines) + '\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--report', type=Path, default=Path('data/research/bdc084c1'))
    args = parser.parse_args()

    published = committed(str(args.data / 'latest.json'))
    published_orig = committed(str(args.data / 'origination.json'))
    fresh = json.loads((args.data / 'latest.json').read_text())
    orig = json.loads((args.data / 'origination.json').read_text()) if (args.data / 'origination.json').exists() else {}

    fallbacks = {str(r['id']): r for r in (orig.get('matches') or []) if r.get('origination')}
    published_ids = {str(m['id']) for m in (published or {}).get('matches', [])}
    fresh_ids = {str(m['id']) for m in fresh.get('matches', [])}
    active = [m for m in fresh['matches'] if m.get('availability') in ACTIVE]
    rows = [fixture(m, fallbacks) for m in active]

    new_ids = sorted(fresh_ids - published_ids, key=int)
    gone_ids = sorted(published_ids - fresh_ids, key=int)
    new_active = [r for r in rows if r['id'] in new_ids]
    new_past = [r for r in rows if False]  # past rows are not active by definition
    archived_new = [fixture(m, fallbacks) for m in fresh['matches']
                    if str(m['id']) in new_ids and m.get('availability') not in ACTIVE]

    def resolved(r):
        return bool(r['basis']) and bool(r['probabilities'])

    report = {
        'session': 'arena-bdc084c1',
        'purpose': ('Does the next refresh give every fixture Hotspawn added after the published '
                    'snapshot a pick, and what stops any that do not?'),
        'observed_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'published_snapshot': {
            'generated_at': (published or {}).get('generated_at'),
            'inventory': len(published_ids),
            'origination_generated_at': (published_orig or {}).get('generated_at'),
        },
        'fresh_snapshot': {
            'generated_at': fresh.get('generated_at'),
            'inventory_observed_at': fresh.get('inventory_observed_at'),
            'inventory_crosscheck': fresh.get('inventory_crosscheck'),
            'inventory': len(fresh_ids),
            'counts': fresh.get('counts'),
            'coverage_complete': fresh.get('coverage_complete'),
            'run_status': fresh.get('run_status'),
        },
        'fixtures': {
            'new_since_published': new_ids,
            'no_longer_listed': gone_ids,
            'new_active': len(new_active),
            'new_archived': len(archived_new),
        },
        'active': {
            'total': len(rows),
            'with_pick': sum(1 for r in rows if r['pick']),
            'with_probabilities': sum(1 for r in rows if r['probabilities']),
            'without_probabilities': [r for r in rows if not r['probabilities']],
            'without_pick': [r for r in rows if not r['pick']],
            'by_basis': {},
            'by_source_host': {},
            'with_betting_line': 0,
            'research_model_only': 0,
        },
        'new_fixtures': new_active + archived_new,
        'all': rows,
    }
    for r in rows:
        basis = r['basis'] or 'unresolved'
        report['active']['by_basis'][basis] = report['active']['by_basis'].get(basis, 0) + 1
        if r['source_host']:
            report['active']['by_source_host'][r['source_host']] = (
                report['active']['by_source_host'].get(r['source_host'], 0) + 1)
        if r['probabilities']:
            if r['basis'] in MONEY_METHODS:
                report['active']['with_betting_line'] += 1
            else:
                report['active']['research_model_only'] += 1

    args.report.mkdir(parents=True, exist_ok=True)
    out = args.report / 'probe-report.json'
    out.write_text(json.dumps(report, indent=2, sort_keys=False) + '\n')
    write_markdown(report, args.report / 'probe-report.md')

    print(json.dumps({
        'published_snapshot': report['published_snapshot'],
        'fresh_snapshot': report['fresh_snapshot'],
        'fixtures': report['fixtures'],
        'active': {k: v for k, v in report['active'].items() if k not in {'without_probabilities', 'without_pick', 'all'}},
        'report': str(out),
    }, indent=2))

    # A compact, human-readable digest for the workflow log and step summary.
    print('\nNew since the published snapshot:')
    for r in report['new_fixtures']:
        state = 'pick ' + r['pick'] if r['pick'] else ('probabilities, no side' if r['probabilities'] else 'NO PICK')
        print(f"  {r['id']} {r['teams'][0]} vs {r['teams'][1]} [{r['availability']}] "
              f"{r['starts_at']} -> {state} ({r['basis'] or 'unresolved'}; {r['source_host'] or 'no source'})")
    if report['active']['without_probabilities']:
        print('\nActive fixtures without probabilities:')
        for r in report['active']['without_probabilities']:
            print(f"  {r['id']} {r['teams'][0]} vs {r['teams'][1]} {r['starts_at']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
