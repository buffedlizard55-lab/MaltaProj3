"""Session arena-541cd43a — dated snapshot of the live origination state.

The coding sandbox has no egress to Hotspawn, HLTV, bo3.gg or any bookmaker
(TLS to every non-GitHub host fails with ``SSL_ERROR_SYSCALL``), so the evidence
for this session's coverage work is produced on a GitHub runner and committed
back to the session branch as a compact, reviewable report.

This module writes **no** probability, pick, alias or price of its own. It only
copies the values the published pipeline produced in that run, with the exact
provenance each row already carries, so a reviewer can compare the report with
the deployed site.

Outputs (all under ``data/research/541cd43a/``):

* ``live-snapshot.json`` — counts, every active fixture, its ladder result, the
  failing rungs' reasons, and the bo3.gg result sample sizes the research model
  saw;
* ``live/latest.json.gz`` and ``live/origination.json.gz`` — the two runtime
  snapshots exactly as collected, compressed so the repository does not grow
  with a second full copy;
* ``build.json`` — the result of building the site from those live inputs
  (command, exit code, tail of the output, row-source audit line).

Usage: python -m scripts.s541cd43a_snapshot [--root .]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
OUT_DIR = Path('data/research/541cd43a')
SNAPSHOT_FILES = ('data/latest.json', 'data/sources.json', 'data/origination.json')
EVIDENCE_FILES = ('data/evidence/live-bo3-bindings.json',)


def iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).isoformat(timespec='seconds').replace('+00:00', 'Z')


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def team_names(match: dict) -> list[str]:
    return [str((t or {}).get('name') or 'Unverified team') for t in match.get('teams') or []]


def pick_name(match: dict) -> str | None:
    index = match.get('pick_index')
    if index is None:
        return None
    names = team_names(match)
    return names[index] if 0 <= index < len(names) else None


def rung_summary(match: dict) -> dict:
    """Group the research trail by outcome without reinterpreting any value."""
    trail = match.get('research') or []
    resolved = [{'stage': r.get('stage'), 'source_url': r.get('source_url')}
                for r in trail if r.get('status') == 'resolved']
    unresolved = [{'stage': r.get('stage'), 'detail': r.get('detail'), 'source_url': r.get('source_url')}
                  for r in trail if r.get('status') == 'unresolved']
    return {'resolved': resolved, 'unresolved': unresolved}


def bo3_sample_detail(match_id: str, bindings: dict) -> dict | None:
    binding = (bindings.get('matches') or {}).get(str(match_id))
    if not binding:
        return None
    results = binding.get('results') or {}
    return {
        'source_url': binding.get('source_url'),
        'observed_at': binding.get('observed_at'),
        'bridge': binding.get('bridge'),
        'sides': {
            name: {
                'series': len(samples),
                'finished_parsed': sum(1 for s in samples if s.get('parsed') == 'done'),
                'opponents': sorted({str(s.get('opponent')) for s in samples if s.get('opponent')}),
                'first': min((str(s.get('date')) for s in samples), default=None),
                'last': max((str(s.get('date')) for s in samples), default=None),
            } for name, samples in results.items()
        },
    }


def compress(source: Path, target: Path) -> dict | None:
    if not source.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = source.read_bytes()
    with gzip.open(target, 'wb', compresslevel=9) as handle:
        handle.write(raw)
    return {'source': str(source), 'target': str(target), 'bytes': len(raw),
            'compressed_bytes': target.stat().st_size,
            'sha256_of_original': __import__('hashlib').sha256(raw).hexdigest()}


def run_build(root: Path) -> dict:
    command = [sys.executable, '-m', 'scripts.build']
    env = dict(os.environ)
    try:
        proc = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=1500, env=env)
    except subprocess.TimeoutExpired:
        return {'command': ' '.join(command), 'exit_code': None, 'error': 'timeout',
                'tail': 'build exceeded 1500s'}
    tail = '\n'.join((proc.stdout + proc.stderr).strip().splitlines()[-40:])
    audit = re.search(r'Row-source audit: .*', proc.stdout + proc.stderr)
    return {'command': ' '.join(command), 'exit_code': proc.returncode,
            'row_source_audit': audit.group(0) if audit else None, 'tail': tail}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--skip-build', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()

    latest = load(root / 'data/latest.json') or {}
    origination = load(root / 'data/origination.json') or {}
    bindings = load(root / 'data/evidence/live-bo3-bindings.json') or {}

    active = [m for m in origination.get('matches') or [] if m.get('availability') != 'past']
    rows = []
    for match in active:
        orig = match.get('origination') or {}
        rows.append({
            'id': match.get('id'),
            'teams': team_names(match),
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'availability': match.get('availability'),
            'featured_method': match.get('featured_method'),
            'method': orig.get('method'),
            'label': orig.get('label'),
            'probabilities': orig.get('probabilities'),
            'pick': pick_name(match),
            'source': orig.get('source'),
            'source_url': orig.get('source_url'),
            'observed_at': orig.get('observed_at'),
            'low_confidence': orig.get('low_confidence'),
            'n_series': orig.get('n_series'),
            'bo3_binding': bo3_sample_detail(match.get('id'), bindings),
            'rungs': rung_summary(match),
        })

    report = {
        'session': 'arena-541cd43a',
        'generated_at': iso(),
        'purpose': ('Dated live snapshot for the picks-for-every-match coverage work. Values are copied from the '
                    'pipeline outputs of the same run; this file originates no probability or pick.'),
        'inventory': {
            'observed_at': latest.get('inventory_observed_at'),
            'generated_at': latest.get('generated_at'),
            'coverage_complete': latest.get('coverage_complete'),
            'run_status': latest.get('run_status'),
            'counts': latest.get('counts'),
            'source': (latest.get('sources') or [{}])[0].get('url'),
        },
        'origination': {
            'generated_at': origination.get('generated_at'),
            'live_collection': origination.get('live_collection'),
            'counts': origination.get('counts'),
            'unresolved_ids': origination.get('unresolved_ids'),
            'collection': origination.get('collection'),
        },
        'active': rows,
        'blank': [r for r in rows if r['method'] is None],
    }

    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'live-snapshot.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    copies = []
    for relative in SNAPSHOT_FILES:
        entry = compress(root / relative, out_dir / 'live' / (Path(relative).name + '.gz'))
        if entry:
            copies.append(entry)
    for relative in EVIDENCE_FILES:
        entry = compress(root / relative, out_dir / 'live' / (Path(relative).name + '.gz'))
        if entry:
            copies.append(entry)

    build = {'skipped': True}
    if not args.skip_build:
        build = run_build(root)
        build['verified_at'] = iso()
    (out_dir / 'build.json').write_text(json.dumps(
        {'generated_at': iso(), 'copies': copies, 'build': build}, ensure_ascii=False, indent=2) + '\n')

    print(json.dumps({'active': len(rows), 'blank': len(report['blank']),
                      'blank_ids': [r['id'] for r in report['blank']],
                      'build': build.get('exit_code'), 'copies': len(copies)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
