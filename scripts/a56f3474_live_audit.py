"""Read-only row audit for the exact A56 live evidence export.

This deliberately does not collect, originate, or edit a match. It compares the
exported complete-picks feed with its featured inventory and compact pick index,
then checks every row's identity links, arithmetic, pick direction, provenance,
and count ledger. Official-input network verification is a separate concern;
the runner's independent 416d93ee report is retained beside this report.

Usage:
    python -m scripts.a56f3474_live_audit \
      --source data/research/a56f3474/live \
      --output data/research/a56f3474/live-row-audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

UTC = timezone.utc
ACTIVE = {'open', 'locked', 'unknown_lock'}
METHODS = {'market', 'bookmaker', 'consensus', 'reference', 'model', 'guidance'}
MONEY = {'market', 'bookmaker', 'consensus', 'reference'}
COUNT_METHODS = ('market', 'bookmaker', 'consensus', 'reference', 'model', 'guidance')


def read_json(path: Path):
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def https(value) -> bool:
    try:
        parsed = urlsplit(str(value or ''))
        return parsed.scheme == 'https' and bool(parsed.netloc)
    except ValueError:
        return False


def names(match: dict) -> list[str]:
    return [str(team.get('name') or '') for team in match.get('teams') or []]


def audit(source: Path) -> dict:
    latest = read_json(source / 'latest.json')
    complete = read_json(source / 'origination.json')
    index_path = source / 'pick-index.json'
    pick_index = read_json(index_path) if index_path.exists() else None
    featured = {str(row['id']): row for row in latest.get('matches') or []}
    featured_active = {str(row['id']) for row in latest.get('matches') or []
                       if row.get('availability') in ACTIVE}
    rows = complete.get('matches') or []
    indexed = {str(row.get('id')): row for row in (pick_index or {}).get('rows') or []}
    report_rows = []
    all_violations = []

    for position, match in enumerate(rows, 1):
        fixture_id = str(match.get('id') or '')
        violations = []
        warnings = []
        featured_row = featured.get(fixture_id)
        estimate = match.get('origination')
        pick = match.get('pick_index')

        def require(condition, code, detail):
            if not condition:
                violations.append({'code': code, 'detail': detail})

        require(bool(fixture_id), 'missing-id', f'row {position} has no fixture id')
        require(featured_row is not None, 'missing-featured-row', 'not present in latest.json')
        require(fixture_id in featured_active, 'not-active-in-featured', 'not an active featured fixture')
        require(match.get('availability') in ACTIVE, 'not-active-in-complete-feed',
                f"availability={match.get('availability')!r}")
        require(https(match.get('source_url')), 'fixture-source-missing',
                'Hotspawn fixture permalink is absent or not HTTPS')
        require(https(match.get('lobby_url')), 'lobby-source-missing',
                'Hotspawn lobby permalink is absent or not HTTPS')
        if featured_row is not None:
            require(names(featured_row) == names(match), 'team-identity-mismatch',
                    f"latest={names(featured_row)!r}, origination={names(match)!r}")
            for key in ('competition', 'starts_at', 'locks_at'):
                require(featured_row.get(key) == match.get(key), 'schedule-identity-mismatch',
                        f'{key}: latest={featured_row.get(key)!r}, origination={match.get(key)!r}')
            require(https(featured_row.get('source_api')), 'inventory-api-source-missing',
                    'official scheduled-fixture API link is absent or not HTTPS')
            require(featured_row.get('evidence') == 'data/evidence/hotspawn-fixtures.json',
                    'inventory-evidence-mismatch', f"evidence={featured_row.get('evidence')!r}")

        if fixture_id not in indexed and pick_index is not None:
            violations.append({'code': 'missing-pick-index-row', 'detail': 'compact export omitted this fixture'})

        probabilities = (estimate or {}).get('probabilities')
        if estimate is None:
            require(pick is None, 'unresolved-has-pick', 'an unresolved row cannot name a side')
            require(bool(match.get('research')), 'unresolved-research-missing',
                    'unresolved fixture has no research trail')
        else:
            method = estimate.get('method')
            require(method in METHODS, 'unknown-method', repr(method))
            require(https(estimate.get('source_url')), 'estimate-source-missing',
                    'estimate source is absent or not HTTPS')
            require(bool(str(estimate.get('source') or '').strip()), 'estimate-provider-missing',
                    'estimate provider label is blank')
            require(bool(estimate.get('observed_at') or estimate.get('evaluation_at')),
                    'estimate-observation-missing', 'no dated estimate observation')
            require('hotspawn.com' not in str(estimate.get('source_url') or ''),
                    'hotspawn-used-as-estimate-source', 'Hotspawn is inventory evidence, not a probability source')
            require(isinstance(probabilities, list) and len(probabilities) == 2,
                    'probability-shape', 'expected exactly two probabilities')
            valid_numbers = (isinstance(probabilities, list) and len(probabilities) == 2
                             and all(isinstance(p, (int, float)) and not isinstance(p, bool)
                                     and math.isfinite(p) and 0 < p < 1 for p in probabilities))
            require(valid_numbers, 'probability-domain', repr(probabilities))
            if valid_numbers:
                require(abs(sum(probabilities) - 1) <= 1e-8, 'probability-sum', str(sum(probabilities)))
                expected = None if abs(probabilities[0] - probabilities[1]) <= 1e-8 else (0 if probabilities[0] > probabilities[1] else 1)
                require(pick == expected, 'pick-direction', f'published={pick!r}, expected={expected!r}')
                fair = estimate.get('fair_decimal') or []
                require(len(fair) == 2 and all(abs(float(fair[i]) - round(1 / probabilities[i], 3)) < 1e-9 for i in range(2)),
                        'fair-decimal-replay', repr(fair))
            quotes = estimate.get('quotes') or []
            for quote in quotes:
                require(https(quote.get('source_url')), 'quote-source-missing',
                        f"provider={quote.get('provider')!r}")
            if method in MONEY:
                require(bool(quotes), 'money-quotes-missing', 'money method has no paired quotes')
            provider = str(estimate.get('provider') or estimate.get('source') or '')
            label = str(estimate.get('label') or '')
            if 'HLTV' in provider or 'HLTV' in label or 'Valve' in provider:
                require(bool(estimate.get('inputs')), 'rating-inputs-missing',
                        'rating-model row has no published team inputs')
            if method in {'model', 'guidance', 'reference'}:
                require(bool(match.get('limitations') or estimate.get('limitations')),
                        'limitations-missing', f'{method} row has no limitation')

        research = match.get('research') or []
        if not research:
            warnings.append('no research trail entries')
        for entry in research:
            if entry.get('source_url') and not https(entry.get('source_url')):
                violations.append({'code': 'research-source-not-https',
                                   'detail': str(entry.get('source_url'))})

        if pick_index is not None and fixture_id in indexed:
            compact = indexed[fixture_id]
            comparisons = {
                'teams': names(match),
                'competition': match.get('competition'),
                'starts_at': match.get('starts_at'),
                'locks_at': match.get('locks_at'),
                'availability': match.get('availability'),
                'featured_method': match.get('featured_method'),
                'method': (estimate or {}).get('method'),
                'label': (estimate or {}).get('label'),
                'source': (estimate or {}).get('source'),
                'source_url': (estimate or {}).get('source_url'),
                'probabilities': probabilities,
                'pick_index': pick,
            }
            for key, expected in comparisons.items():
                require(compact.get(key) == expected, 'pick-index-mismatch',
                        f'{key}: compact={compact.get(key)!r}, canonical={expected!r}')

        status = 'unresolved' if estimate is None else ('no-side' if pick is None else 'directional')
        all_violations.extend({'id': fixture_id, **item} for item in violations)
        report_rows.append({
            'position': position,
            'id': fixture_id,
            'teams': names(match),
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'method': (estimate or {}).get('method'),
            'source': (estimate or {}).get('source'),
            'source_url': (estimate or {}).get('source_url'),
            'probabilities': probabilities,
            'pick_index': pick,
            'status': status,
            'violations': violations,
            'warnings': warnings,
        })

    ids = [str(row.get('id')) for row in rows]
    if len(ids) != len(set(ids)):
        all_violations.append({'id': None, 'code': 'duplicate-active-id', 'detail': 'duplicate id in complete feed'})
    if set(ids) != featured_active:
        all_violations.append({'id': None, 'code': 'active-inventory-set-mismatch',
                               'detail': {'missing_from_complete': sorted(featured_active - set(ids)),
                                          'extra_in_complete': sorted(set(ids) - featured_active)}})
    if pick_index is not None and set(indexed) != set(ids):
        all_violations.append({'id': None, 'code': 'pick-index-set-mismatch',
                               'detail': 'compact and canonical active fixture sets differ'})

    actual = Counter((row.get('origination') or {}).get('method') for row in rows)
    expected_counts = {
        'active': len(rows),
        'resolved': sum(row.get('origination') is not None for row in rows),
        'unresolved': sum(row.get('origination') is None for row in rows),
        'with_pick': sum(row.get('pick_index') is not None for row in rows),
        **{method: actual[method] for method in COUNT_METHODS},
    }
    published_counts = complete.get('counts') or {}
    count_checks = {}
    for key, expected in expected_counts.items():
        published = published_counts.get(key, 0)
        count_checks[key] = {'published': published, 'recomputed': expected,
                             'status': 'match' if published == expected else 'mismatch'}
        if published != expected:
            all_violations.append({'id': None, 'code': 'count-mismatch',
                                   'detail': {'key': key, 'published': published, 'recomputed': expected}})

    return {
        'schema_version': 1,
        'session': 'arena-a56f3474',
        'audited_at': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source_directory': str(source),
        'source_generated_at': complete.get('generated_at'),
        'source_snapshot_at': complete.get('source_snapshot_at'),
        'source_sha256': {path.name: sha256(source / path.name)
                          for path in (source / name for name in ('latest.json', 'origination.json', 'sources.json'))
                          if path.exists()},
        'summary': {
            'rows': len(rows),
            'directional': sum(row['status'] == 'directional' for row in report_rows),
            'no_side': sum(row['status'] == 'no-side' for row in report_rows),
            'unresolved': sum(row['status'] == 'unresolved' for row in report_rows),
            'rows_with_violations': sum(bool(row['violations']) for row in report_rows),
            'violations': len(all_violations),
        },
        'count_checks': count_checks,
        'policy': complete.get('policy'),
        'violations': all_violations,
        'rows': report_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data/research/a56f3474/live'))
    parser.add_argument('--output', type=Path, default=Path('data/research/a56f3474/live-row-audit.json'))
    args = parser.parse_args()
    report = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report['summary'], sort_keys=True))
    for row in report['rows']:
        if row['status'] != 'directional' or row['violations']:
            print(row['id'], ' vs '.join(row['teams']), row['status'],
                  [item['code'] for item in row['violations']])
    return 1 if report['summary']['violations'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
