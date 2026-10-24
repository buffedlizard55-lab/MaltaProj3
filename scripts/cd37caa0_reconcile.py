"""Reconcile a fresh Hotspawn/origination candidate with the deployed snapshot.

This is a read-only audit. It never writes ``data/latest.json``,
``data/origination.json`` or ``snapshot.json`` and never creates a probability.
Every published value in the report is copied from the supplied candidate and
checked for internal consistency. The candidate remains explicitly distinct
from the deployed snapshot until Pages deployment is independently verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
HOTSPAWN_HOSTS = ('play.hotspawn.com', 'phpstack-1372681-6459848.cloudwaysapps.com')
MONEY_METHODS = {'market', 'bookmaker', 'reference', 'consensus'}


def read_json(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('matches'), list):
        raise ValueError(f'{path}: expected an object with a matches array')
    return data


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def active_rows(data: dict) -> list[dict]:
    return [row for row in data['matches']
            if isinstance(row, dict) and row.get('availability') != 'past']


def by_id(rows: list[dict], label: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    duplicates: set[str] = set()
    for row in rows:
        fixture_id = str(row.get('id') or '')
        if not fixture_id.isdigit():
            raise ValueError(f'{label}: non-numeric or missing Hotspawn fixture id')
        if fixture_id in out:
            duplicates.add(fixture_id)
        out[fixture_id] = row
    if duplicates:
        raise ValueError(f'{label}: duplicate fixture ids: {sorted(duplicates)}')
    return out


def teams(row: dict) -> list[str]:
    values = row.get('teams') or []
    return [str(team.get('name') or '') if isinstance(team, dict) else ''
            for team in values]


def valid_url(value) -> bool:
    return isinstance(value, str) and value.startswith('https://') and ' ' not in value


def hotspawn_url(value) -> bool:
    return isinstance(value, str) and any(host in value for host in HOTSPAWN_HOSTS)


def research_url(row: dict, prefix: str) -> str | None:
    for item in row.get('research') or []:
        if not isinstance(item, dict):
            continue
        stage = str(item.get('stage') or '').casefold()
        url = item.get('source_url')
        if stage.startswith(prefix.casefold()) and valid_url(url):
            return url
    return None


def check_row(latest: dict, researched: dict) -> tuple[dict, list[str]]:
    problems: list[str] = []
    names = teams(latest)
    if len(names) != 2 or not all(names) or names[0].casefold() == names[1].casefold():
        problems.append('two distinct named teams are required')
    if teams(researched) != names:
        problems.append('team names/order differ between inventory and origination')
    if latest.get('starts_at') != researched.get('starts_at'):
        problems.append('start time differs between inventory and origination')
    official_url = latest.get('source_url')
    if not valid_url(official_url):
        problems.append('official Hotspawn match source is missing or not HTTPS')
    analysis = researched.get('origination')
    pick_index = researched.get('pick_index')
    probabilities = analysis.get('probabilities') if isinstance(analysis, dict) else None
    method = analysis.get('method') if isinstance(analysis, dict) else None
    independent_url = analysis.get('source_url') if isinstance(analysis, dict) else None
    pick_team = None
    directional = False
    if analysis is None or pick_index is None:
        problems.append('unresolved: no directional origination pick')
        probabilities = None
        method = None
        independent_url = None
    else:
        if pick_index not in (0, 1):
            problems.append('pick_index must be 0 or 1')
        elif len(names) == 2:
            pick_team = names[pick_index]
        if (not isinstance(probabilities, list) or len(probabilities) != 2
                or any(isinstance(p, bool) or not isinstance(p, (int, float))
                       or not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities)):
            problems.append('two finite probabilities in [0,1] are required')
        else:
            if abs(sum(probabilities) - 1) > 1e-6:
                problems.append('probabilities do not sum to one')
            if pick_index in (0, 1):
                directional = probabilities[pick_index] > probabilities[1 - pick_index]
                if not directional:
                    problems.append('published pick is not strictly directional')
        if not valid_url(independent_url):
            problems.append('independent origination source is missing or not HTTPS')
        elif hotspawn_url(independent_url):
            problems.append('Hotspawn cannot be the independent probability source')
    limitations = [str(x) for x in researched.get('limitations') or []]
    if analysis is None and not limitations and not researched.get('research'):
        problems.append('unresolved row needs a limitation or research trail')
    row = {
        'id': str(latest['id']),
        'teams': names,
        'competition': latest.get('competition'),
        'starts_at': latest.get('starts_at'),
        'official_source_url': official_url,
        'official_inventory_api': latest.get('source_api'),
        'lobby_url': latest.get('lobby_url'),
        'featured_method': (latest.get('analysis') or {}).get('method'),
        'method': method,
        'external_line': method in MONEY_METHODS if method else False,
        'probabilities': probabilities,
        'pick_index': pick_index,
        'pick_team': pick_team,
        'strictly_directional': directional,
        'independent_source_url': independent_url,
        'hltv_research_url': research_url(researched, 'HLTV'),
        'limitations': limitations,
        'research': researched.get('research') or [],
        'unresolved': analysis is None or pick_index is None,
    }
    return row, problems


def reconcile(candidate_latest: dict, candidate_origination: dict,
              published: dict) -> dict:
    latest_rows = active_rows(candidate_latest)
    origination_rows = active_rows(candidate_origination)
    latest_by_id = by_id(latest_rows, 'candidate inventory')
    origination_by_id = by_id(origination_rows, 'candidate origination')
    published_by_id = by_id(active_rows(published), 'published snapshot')
    if latest_by_id.keys() != origination_by_id.keys():
        missing = sorted(latest_by_id.keys() - origination_by_id.keys())
        extra = sorted(origination_by_id.keys() - latest_by_id.keys())
        raise ValueError(f'candidate active-id mismatch; missing={missing}, extra={extra}')

    fixtures, row_problems = [], {}
    for fixture_id in sorted(latest_by_id, key=lambda x: (latest_by_id[x].get('starts_at') or '', x)):
        row, problems = check_row(latest_by_id[fixture_id], origination_by_id[fixture_id])
        row['new_since_published'] = fixture_id not in published_by_id
        fixtures.append(row)
        if problems:
            row_problems[fixture_id] = problems

    current_ids = set(latest_by_id)
    published_ids = set(published_by_id)
    unresolved = [row for row in fixtures if row['unresolved']]
    no_line = [row for row in fixtures if not row['external_line'] and not row['unresolved']]
    checks = [
        {'id': 'active-id-pairing', 'status': 'pass',
         'detail': f'{len(fixtures)} active inventory rows pair one-to-one with origination.'},
        {'id': 'row-validation', 'status': 'fail' if row_problems else 'pass',
         'detail': (f'{len(row_problems)} rows have validation problems.'
                    if row_problems else
                    'Every row has an official source; every resolved row has two normalized probabilities, a strict pick and an independent HTTPS source.')},
        {'id': 'candidate-not-deployment', 'status': 'info',
         'detail': 'This report reconciles a dated candidate. It is not evidence that GitHub Pages serves the candidate.'},
    ]
    return {
        'schema_version': 1,
        'session': 'arena-cd37caa0',
        'kind': 'dated candidate-versus-deployed reconciliation; not a deployment attestation',
        'candidate_generated_at': candidate_latest.get('generated_at'),
        'origination_generated_at': candidate_origination.get('generated_at'),
        'published_generated_at': published.get('generated_at'),
        'official_inventory_request': next((request for request in candidate_latest.get('requests') or []
                                            if isinstance(request, dict)
                                            and request.get('id') == 'hotspawn-fixtures'), None),
        'counts': {
            'candidate_active': len(fixtures),
            'candidate_resolved': len(fixtures) - len(unresolved),
            'candidate_unresolved': len(unresolved),
            'candidate_external_line': sum(row['external_line'] for row in fixtures),
            'candidate_no_external_line': len(no_line),
            'published_active': len(published_by_id),
            'shared': len(current_ids & published_ids),
            'new': len(current_ids - published_ids),
            'removed': len(published_ids - current_ids),
            'validation_problem_rows': len(row_problems),
        },
        'new_ids': sorted(current_ids - published_ids),
        'removed_ids': sorted(published_ids - current_ids),
        'unresolved_ids': [row['id'] for row in unresolved],
        'no_external_line_ids': [row['id'] for row in no_line],
        'row_problems': row_problems,
        'checks': checks,
        'fixtures': fixtures,
    }


def markdown(report: dict) -> str:
    counts = report['counts']
    lines = [
        '# CD37 fresh-candidate coverage reconciliation', '',
        '> Dated candidate audit, **not a deployment attestation**. Probabilities and picks are replayed from the supplied origination candidate; none are hand-written here.', '',
        f"- Candidate inventory: `{report['candidate_generated_at']}`; origination: `{report['origination_generated_at']}`.",
        f"- Deployed snapshot used for comparison: `{report['published_generated_at']}`.",
        f"- Candidate: **{counts['candidate_resolved']}/{counts['candidate_active']} resolved**, {counts['candidate_external_line']} with an external line, {counts['candidate_no_external_line']} model/no-line, {counts['candidate_unresolved']} unresolved.",
        f"- Against the deployed snapshot: **{counts['new']} new**, {counts['removed']} removed, {counts['shared']} shared active fixtures.",
        f"- Validation: **{counts['validation_problem_rows']} problem rows**.", '',
        '## Every current candidate row', '',
        'Probabilities are in Hotspawn team order. “Official” opens the Hotspawn match; “Basis” opens the independent probability/model source. HLTV links are research evidence, never fan-vote probabilities.', '',
        '| ID | Match (UTC) | Pick | Team 1 / Team 2 | Method | Sources | New |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in report['fixtures']:
        names = row['teams']
        match = f"{' / '.join(names)}<br>{row['starts_at'] or 'Unverified'}"
        pick = row['pick_team'] or '**UNRESOLVED**'
        probs = (' / '.join(f'{100 * p:.2f}%' for p in row['probabilities'])
                 if row['probabilities'] else '—')
        sources = [f"[Official]({row['official_source_url']})"] if valid_url(row['official_source_url']) else ['Official unverified']
        if row['independent_source_url']:
            sources.append(f"[Basis]({row['independent_source_url']})")
        if row['hltv_research_url']:
            sources.append(f"[HLTV]({row['hltv_research_url']})")
        lines.append(f"| {row['id']} | {match} | {pick} | {probs} | {row['method'] or 'unresolved'} | {' · '.join(sources)} | {'yes' if row['new_since_published'] else 'no'} |")
    lines.extend(['', '## Unresolved picks and limitations', ''])
    unresolved = [row for row in report['fixtures'] if row['unresolved']]
    if not unresolved:
        lines.append('No unresolved rows in this dated candidate. Model/no-line limitations remain on each row and in the JSON research trail.')
    else:
        for row in unresolved:
            lines.append(f"- **{row['id']} {' / '.join(row['teams'])}** — {' '.join(row['limitations']) or 'See the linked research trail; no compliant directional pick was verified.'}")
    if report['row_problems']:
        lines.extend(['', '## Validation problems', ''])
        for fixture_id, problems in report['row_problems'].items():
            lines.append(f"- `{fixture_id}`: {'; '.join(problems)}")
    lines.extend(['', '## Inventory changes', '',
                  'New IDs: ' + (', '.join(report['new_ids']) or 'none'),
                  'Removed IDs: ' + (', '.join(report['removed_ids']) or 'none'), ''])
    return '\n'.join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-latest', type=Path, required=True)
    parser.add_argument('--candidate-origination', type=Path, required=True)
    parser.add_argument('--published', type=Path, default=Path('snapshot.json'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--candidate-ref', default=None, help='Immutable source commit URL for attribution')
    parser.add_argument('--runner-url', default=None, help='Collection run URL for attribution')
    args = parser.parse_args(argv)
    latest = read_json(args.candidate_latest)
    origination = read_json(args.candidate_origination)
    published = read_json(args.published)
    report = reconcile(latest, origination, published)
    report['audited_at'] = datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')
    report['provenance'] = {
        'candidate_ref': args.candidate_ref,
        'runner_url': args.runner_url,
        'inputs': {str(path): {'sha256': sha256(path)} for path in
                   (args.candidate_latest, args.candidate_origination, args.published)},
        'note': 'Read-only attributed input. The source session/runner collected the candidate; this audit independently reconciles it and does not claim deployment.',
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'coverage-reconciliation.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.out / 'coverage-reconciliation.md').write_text(markdown(report), encoding='utf-8')
    print(json.dumps({'counts': report['counts'], 'checks': report['checks']}, indent=2))
    return 1 if report['row_problems'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
