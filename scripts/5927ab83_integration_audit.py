"""Independently re-audit the dated complete-picks dossier before integration.

This is deliberately read-only with respect to picks, probabilities and source
captures. It checks the relationships that can otherwise be lost when several
sessions integrate: exact inventory/replay coverage, normalized directional
estimates, official per-row links, the precise model-only research target set,
and HLTV-first ordering before esportsbook/exchange follow-up.

It does not assert that a dated observation is still live and it does not turn
source reachability into a price. Production freshness remains the publisher's
separate fail-closed responsibility.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

UTC = timezone.utc
EXTERNAL_STAGES = ('esportsbook', 'exchange market', 'aggregated bookmaker')


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def hltv_precedes_external(stages: list[str], fixture_id: str) -> None:
    require('HLTV research' in stages, f'{fixture_id}: no HLTV research stage')
    hltv = stages.index('HLTV research')
    for stage in stages[:hltv]:
        require(not any(word in stage.lower() for word in EXTERNAL_STAGES),
                f'{fixture_id}: external follow-up precedes HLTV: {stage}')


def audit(directory: Path) -> dict:
    paths = {name: directory / f'{name}.json' for name in (
        'audited-fixtures', 'source-replay', 'line-source-research',
        'row-source-audit')}
    audited = load(paths['audited-fixtures'])
    replay = load(paths['source-replay'])
    research = load(paths['line-source-research'])
    row_sources = load(paths['row-source-audit'])

    rows = audited['matches']
    ids = [str(row['id']) for row in rows]
    total = len(rows)
    require(total > 0 and len(set(ids)) == total, 'inventory IDs are empty or duplicated')
    counts = audited['counts']
    require(counts['active'] == counts['resolved'] == counts['with_pick'] == total,
            'dated complete-picks counts do not cover every inventory row')
    require(counts['unresolved'] == 0, 'dated dossier contains an unresolved pick')

    methods = Counter()
    gaps = []
    for row in rows:
        fixture_id = str(row['id'])
        source = row.get('source_url') or ''
        require(source.startswith('https://www.hotspawn.com/matches/') and
                source.endswith(fixture_id), f'{fixture_id}: invalid official fixture link')
        estimate = row.get('origination') or {}
        probabilities = estimate.get('probabilities')
        require(isinstance(probabilities, list) and len(probabilities) == 2,
                f'{fixture_id}: missing two-team probabilities')
        require(all(isinstance(value, (int, float)) and not isinstance(value, bool) and
                    math.isfinite(value) and 0 < value < 1 for value in probabilities),
                f'{fixture_id}: non-finite or out-of-range probability')
        require(abs(sum(probabilities) - 1) < 2e-8,
                f'{fixture_id}: probabilities are not normalized')
        pick = row.get('pick_index')
        require(pick in (0, 1) and pick == (0 if probabilities[0] > probabilities[1] else 1),
                f'{fixture_id}: pick does not follow the larger probability')
        method = estimate.get('method')
        methods[method] += 1
        if method in {'model', 'network'}:
            gaps.append(fixture_id)
        if method in {'market', 'bookmaker', 'reference', 'relay'}:
            estimate_source = estimate.get('source_url') or ''
            require(estimate_source.startswith('https://') and
                    'play.hotspawn.com' not in estimate_source,
                    f'{fixture_id}: external estimate lacks an independent source')
        stages = [item.get('stage', '') for item in row.get('research') or []]
        if 'HLTV research' in stages:
            hltv_precedes_external(stages, fixture_id)
        for quote in estimate.get('quotes') or []:
            haystack = json.dumps(quote).lower()
            require('hotspawn' not in haystack and 'picked' not in haystack and
                    'fan vote' not in haystack,
                    f'{fixture_id}: crowd participation appears in a probability quote')

    target_rows = research['per_fixture']
    target_ids = [str(row['id']) for row in target_rows]
    require(len(target_rows) == len(set(target_ids)) and set(target_ids) == set(gaps),
            'HLTV-first research targets differ from the model-only fixture set')
    for row in target_rows:
        fixture_id = str(row['id'])
        require((row.get('hotspawn_url') or '').endswith(fixture_id),
                f'{fixture_id}: research has no official fixture link')
        hltv_url = row.get('hltv_url') or ''
        require(hltv_url.startswith('https://www.hltv.org/matches/') and
                (row.get('hltv_page') or {}).get('url') == hltv_url,
                f'{fixture_id}: HLTV observation is not bound to its match URL')
        stages = [item.get('stage', '') for item in row.get('research') or []]
        hltv_precedes_external(stages, fixture_id)
        hltv = stages.index('HLTV research')
        require(any(any(word in stage.lower() for word in
                        ('esportsbook', 'exchange market')) for stage in stages[hltv + 1:]),
                f'{fixture_id}: no esportsbook/exchange follow-up after HLTV')

    replay_rows = replay['rows']
    require(len(replay_rows) == total and
            {str(row['fixture_id']) for row in replay_rows} == set(ids),
            'source replay does not cover the exact inventory')
    by_id = {str(row['id']): row for row in rows}
    for row in replay_rows:
        fixture_id = str(row['fixture_id'])
        original = by_id[fixture_id]
        require(row['probabilities'] == original['origination']['probabilities'] and
                row['snapshot_pick_index'] == original['pick_index'],
                f'{fixture_id}: replay changed a probability or pick')
        require(row['currently_usable'] is True and
                row['featured_facts_unchanged'] is True,
                f'{fixture_id}: replay row is not usable or changed featured facts')
        require(any(item.get('url') == original['source_url']
                    for item in row.get('sources') or []),
                f'{fixture_id}: replay omitted the official fixture source')
    expected_replay_counts = {
        'canonical_nonpast_fixtures': total,
        'audited_rows': total,
        'supported_dated_estimates': total,
        'currently_usable_lines': total,
        'explicitly_unresolved': 0,
    }
    require(replay['counts'] == expected_replay_counts,
            'source-replay summary counts do not match the audited rows')

    source_totals = row_sources['totals']
    require(source_totals.get('violation') == 0,
            'row-source audit contains a source-less or unofficial-row violation')
    require(source_totals.get('rows') ==
            source_totals.get('ok', 0) + source_totals.get('flagged', 0) +
            source_totals.get('navigation', 0),
            'row-source totals do not reconcile')

    return {
        'schema_version': 1,
        'session': 'arena-5927ab83',
        'audited_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'source_session': research.get('session'),
        'source_run_url': research.get('run_url'),
        'source_snapshot_at': audited.get('source_snapshot_at'),
        'source_dossier': str(directory),
        'source_sha256': {path.name: digest(path) for path in paths.values()},
        'ok': True,
        'counts': {
            'official_inventory_rows': total,
            'unique_fixture_ids': len(set(ids)),
            'normalized_directional_estimates': total,
            'replayed_rows': len(replay_rows),
            'model_only_targets': len(gaps),
            'hltv_first_research_rows': len(target_rows),
            'qualified_new_line_leads': len(research.get('leads') or []),
            'row_source_violations': source_totals.get('violation'),
        },
        'methods': dict(sorted(methods.items())),
        'model_only_fixture_ids': gaps,
        'replay_counts': replay['counts'],
        'row_source_totals': source_totals,
        'checks': [
            'Every inventory ID is unique and has its official Hotspawn fixture URL.',
            'Every row has two finite in-range probabilities summing to one and a matching directional pick.',
            'Market/bookmaker estimates cite independent sources, never Hotspawn participation.',
            'Research targets exactly the model-only IDs; HLTV precedes esportsbook/exchange follow-up.',
            'Source replay preserves every probability/pick and includes the official fixture link.',
            'Row-source totals reconcile and contain zero violations; flagged rows remain reviewable.',
        ],
        'limitations': [
            'This is an internal-consistency and provenance audit of a dated dossier, not a new market observation.',
            'It is not a deployment attestation; production freshness and Pages verification are separate gates.',
            'Blocked, empty or unlisted sources do not establish that no betting market exists anywhere.',
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--research-dir', type=Path,
                        default=Path('data/research/be019782'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit(args.research_dir)
    text = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
