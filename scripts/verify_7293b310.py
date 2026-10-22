"""Session arena-7293b310 — line-by-line audit of the published pick snapshot.

Read-only. For every active Hotspawn fixture in the published JSON this prints
one row: the fixture id and Hotspawn permalink, both team names, the kick-off,
the selected pick, both published probabilities, the method that produced the
number and the original source URL of that number. It then applies the project's
own rules and counts failures:

* every active fixture must have a two-way estimate and a side, or appear in the
  unresolved register with the sources that were tried;
* every published probability must carry an https source URL on an allow-listed
  official/primary host (``scripts.audit_rows.OFFICIAL``);
* every row must carry its Hotspawn match permalink;
* no probability may be 0 %, 100 % or a made-up default.

Usage::

    python -m scripts.verify_7293b310 [--data data] [--json report.json] [--markdown report.md]

Exit code 1 when a rule fails. The report never edits a value.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from scripts.audit_rows import OFFICIAL

ACTIVE = {'open', 'locked', 'unknown_lock'}


def official(url: str) -> bool:
    """True when the URL is https and its host is an allow-listed publisher."""
    if not isinstance(url, str) or not url.startswith('https://'):
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    path = parsed.path or '/'
    for allowed, prefix in OFFICIAL:
        if host == allowed or host.endswith('.' + allowed):
            if not prefix or path.startswith(prefix):
                return True
    return False


def team_names(match):
    return [t.get('name') or 'Unverified team' for t in match.get('teams') or []][:2]


def row_for(match):
    """One audit row from an originated match record."""
    origination = match.get('origination') or {}
    pick = match.get('pick_index')
    probs = origination.get('probabilities') or []
    names = team_names(match)
    start = match.get('starts_at') or ''
    source = (origination.get('source') or {}) if isinstance(origination.get('source'), dict) else {}
    source_url = origination.get('source_url') or source.get('url')
    problems = []
    if not match.get('source_url'):
        problems.append('no Hotspawn permalink')
    if not origination:
        problems.append('no estimate (belongs in the unresolved register)')
    else:
        if len(probs) != 2:
            problems.append('not a two-way estimate')
        else:
            if any(not isinstance(p, (int, float)) for p in probs):
                problems.append('non-numeric probability')
            elif any(p <= 0 or p >= 1 for p in probs):
                problems.append('probability at 0 or 1')
            elif abs(sum(probs) - 1) > 1e-6:
                problems.append('two-way probabilities do not sum to 1')
        if pick not in (0, 1):
            problems.append('no side')
        if not source_url:
            problems.append('no source URL for the probability')
        elif not official(source_url):
            problems.append(f'source is not an allow-listed official host: {source_url}')
    return {
        'id': str(match.get('id')),
        'match': ' vs '.join(names),
        'competition': match.get('competition'),
        'starts_at': start,
        'pick': names[pick] if pick in (0, 1) and len(names) == 2 else None,
        'probabilities': {names[i]: (round(probs[i], 6) if i < len(probs) and isinstance(probs[i], (int, float)) else None)
                          for i in range(min(2, len(names)))},
        'method': origination.get('method'),
        'source_url': source_url,
        'hotspawn_url': match.get('source_url'),
        'problems': problems,
    }


def audit(data_dir: Path):
    latest = json.loads((data_dir / 'latest.json').read_text())
    origination = json.loads((data_dir / 'origination.json').read_text())
    active = [m for m in latest['matches'] if m['availability'] in ACTIVE]
    originated = {str(m['id']): m for m in origination.get('matches') or []}
    rows, missing = [], []
    for match in active:
        merged = dict(match)
        priced = originated.get(str(match['id'])) or {}
        merged['origination'] = priced.get('origination')
        # The researched list is the record the site renders; it carries the side
        # and the priced teams for alias-joined fixtures whose featured row has no
        # pick yet. Copy only fields that exist so nothing is invented.
        for key in ('pick_index', 'teams', 'starts_at', 'competition', 'locks_at'):
            if priced.get(key) is not None:
                merged[key] = priced[key]
        rows.append(row_for(merged))
    for match_id in origination.get('unresolved_ids') or []:
        if match_id not in originated:
            missing.append(str(match_id))
    counts = origination.get('counts') or {}
    failing = [r for r in rows if r['problems']]
    report = {
        'schema_version': 1,
        'session': 'arena-7293b310',
        'generated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'snapshot_generated_at': latest.get('generated_at'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'featured_counts': latest.get('counts'),
        'origination_counts': counts,
        'active_fixtures': len(active),
        'with_estimate': sum(1 for r in rows if r['method']),
        'with_pick': sum(1 for r in rows if r['pick'] and r['method']),
        'without_pick': sum(1 for r in rows if not r['pick']),
        'unresolved_ids': origination.get('unresolved_ids') or [],
        'unresolved_ids_absent_from_the_list': missing,
        'rows_with_problems': len(failing),
        'rows': rows,
    }
    return report


def markdown(report) -> str:
    lines = [
        '# Session arena-7293b310 — line-by-line verification of the published picks',
        '',
        f"Generated {report['generated_at']} from the snapshot observed "
        f"{report['inventory_observed_at']} (featured build {report['snapshot_generated_at']}).",
        '',
        '| Fixture | Match | Competition | Start (UTC) | Pick | Probabilities | Method | Source | Problems |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in report['rows']:
        probs = ' · '.join(f'{team} {p * 100:.1f}%' for team, p in row['probabilities'].items() if p is not None) or '—'
        start = row['starts_at'][:16].replace('T', ' ') if row['starts_at'] else '—'
        source = f"[source]({row['source_url']})" if row['source_url'] else '—'
        hotspawn = f"[{row['id']}]({row['hotspawn_url']})" if row.get('hotspawn_url') else row['id']
        problems = '; '.join(row['problems']) or 'none'
        lines.append(f"| {hotspawn} | {row['match']} | {row['competition'] or '—'} | {start} | "
                     f"{row['pick'] or '—'} | {probs} | {row['method'] or '—'} | {source} | {problems} |")
    counts = report['origination_counts']
    lines += [
        '',
        '## Totals',
        '',
        f"- Active Hotspawn CS2 fixtures: **{report['active_fixtures']}**",
        f"- With a two-way estimate: **{report['with_estimate']}**",
        f"- With a directional pick: **{report['with_pick']}**",
        f"- Without a pick (published in the unresolved register): **{report['without_pick']}**",
        f"- Original unresolved ids: {', '.join(report['unresolved_ids']) or 'none'}",
        f"- Rows with a rule problem: **{report['rows_with_problems']}**",
        '',
        f"Origination counters as published: `{json.dumps(counts, sort_keys=True)}`",
        '',
        'Every probability above is copied from `data/origination.json`; every row keeps the source URL '
        'that produced it. This report adds no value of its own.',
    ]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default='data')
    parser.add_argument('--json')
    parser.add_argument('--markdown')
    args = parser.parse_args(argv)
    report = audit(Path(args.data))
    text = markdown(report)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    if args.markdown:
        Path(args.markdown).write_text(text)
    print(text)
    return 1 if report['rows_with_problems'] else 0


if __name__ == '__main__':
    sys.exit(main())
