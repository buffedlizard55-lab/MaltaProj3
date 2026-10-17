"""Read-only, row-by-row source/replay audit; never repairs or invents values.

Also provides the provider replay boundary used by build_origination: decoding
only odds again is insufficient if the original event became live, changed its
teams/start, or contains more than one full-series candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.domain import iso, is_fresh, timestamp
from scripts import originate

UTC = timezone.utc


def evidence_path(source: Path, reference: str) -> Path:
    """Resolve a published data/ reference without allowing path traversal."""
    assert isinstance(reference, str) and reference.startswith('data/'), 'Missing data evidence reference'
    relative = Path(reference.removeprefix('data/'))
    assert not relative.is_absolute() and '..' not in relative.parts, 'Unsafe evidence path'
    path = (source / relative).resolve()
    assert path.is_relative_to(source.resolve()), 'Evidence reference escapes its source directory'
    assert path.is_file(), 'Missing original evidence: ' + reference
    return path


def _read(path: Path):
    return json.loads(path.read_text())


def _requests(source: Path, *, live: bool):
    if live:
        path = source / 'origination/evidence/live-collection-manifest.json'
        assert path.is_file(), 'Missing original live request manifest'
        result = _read(path)
    else:
        result = _read(source / 'latest.json').get('requests')
    assert isinstance(result, list), 'Original request manifest is not an array'
    return result


def _observation(requests_: list, label: str, observed: str, now: datetime, *, reference=None, url=None, method=None):
    hits = [r for r in requests_ if r.get('id') == label and r.get('status') == 'ok']
    assert len(hits) == 1, label + ': original successful request is missing or ambiguous'
    assert hits[0].get('observed_at') == observed, label + ': source observation restamped'
    assert is_fresh(observed, now), label + ': original source is stale, future-dated or missing its observation'
    if reference is not None:
        assert hits[0].get('evidence') == reference, label + ': original request points to different evidence'
    if url is not None:
        assert hits[0].get('url') == url, label + ': original request was not the official source endpoint'
    if method is not None:
        assert hits[0].get('method') == method, label + ': original HTTP method changed'


def replay_provider_quote(q: dict, match: dict, registry: dict, source: Path, now: datetime) -> float:
    """Replay Thunderpick, Kalshi or Bovada through the original collection rules.

    Returns only the matched team's probability, after full original-state and
    unique-candidate verification. Snapshot time is explicit and stable.
    """
    provider = q.get('provider')
    assert provider in {'Thunderpick', 'Kalshi', 'Bovada'}, 'Unsupported replay provider'
    reference = q.get('evidence_file')
    saved = _read(evidence_path(source, reference))
    folder = source / 'origination/evidence'
    if provider == 'Thunderpick':
        allowed = {'data/evidence/thunderpick-matches.json',
                   'data/origination/evidence/live-thunderpick-matches.json'}
        assert reference in allowed, 'Unrecognized Thunderpick original source path'
        live = reference.startswith('data/origination/')
        manifest = _requests(source, live=live)
        label = 'live-thunderpick-matches' if live else 'thunderpick-matches'
        # sources.Client stores data/-rooted references; research Collector.save
        # deliberately stores a basename relative to origination/evidence.
        request_reference = Path(reference).name if live else reference
        _observation(manifest, label, q.get('observed_at'), now, reference=request_reference,
                     url=originate.THUNDERPICK_API, method='POST')
        assert saved.get('ok') is True, 'Original Thunderpick response is not successful'
        payload = {'thunderpick': saved, 'requests': manifest} if live else None
        rows = originate.thunderpick_rows(source, payload)
    elif provider == 'Kalshi':
        assert reference == 'data/origination/evidence/live-kalshi-events.json', 'Unrecognized Kalshi original path'
        manifest = _requests(source, live=True)
        for i, page in enumerate(saved.get('pages') or []):
            assert str(page.get('url', '')).startswith(originate.KALSHI_EVENTS + '?'), 'Unverified Kalshi source endpoint'
            _observation(manifest, 'live-kalshi-events-' + str(i), page.get('observed_at'), now,
                         url=page['url'], method='GET')
            assert page.get('url') == next(r['url'] for r in manifest if r.get('id') == 'live-kalshi-events-' + str(i)
                                          and r.get('status') == 'ok'), 'Kalshi original page URL changed'
        rows = originate.kalshi_rows(folder)
    else:
        assert reference == 'data/origination/evidence/live-bovada-cs2.json', 'Unrecognized Bovada original path'
        manifest = _requests(source, live=True)
        _observation(manifest, 'live-bovada-cs2', saved.get('observed_at'), now,
                     url=originate.BOVADA_API, method='GET')
        assert saved.get('url') == originate.BOVADA_API, 'Bovada original API URL changed'
        rows = originate.bovada_rows(folder)
    # Match against all original full-series candidates, not just the ID that a
    # summarized quote selected. Otherwise a forged summary could hide a second
    # equally matching event/market and turn ambiguity into an arbitrary pick.
    candidates = []
    for row in rows:
        if originate.pair_join(row['names'], row['start'], match, registry)[2] == 'matched' and row not in candidates:
            candidates.append(row)
    assert len(candidates) == 1, provider + ': original full-series event/market is missing, invalid or ambiguous'
    row = candidates[0]
    assert str(row['event_id']) == str(q.get('event_id')), provider + ': original event identity changed'
    if row['family'] == 'market':
        expected, reason = originate.market_estimate(row, match, registry, now)
    else:
        expected, reason = originate.bookmaker_estimate(row, match, registry, now=now)
    assert expected is not None, provider + ': original source rejected: ' + reason
    required = {'provider', 'family', 'probabilities', 'source_url', 'event_id', 'evidence_file', 'observed_at'}
    required |= {'bid', 'ask', 'spread', 'thin'} if row['family'] == 'market' else {'odds'}
    for key, value in expected.items():
        if key in required or key in q:
            assert q.get(key) == value, provider + ': summarized ' + key + ' differs from original source'
    return expected['probabilities'][0]


def audit(source: Path, now: datetime | None = None) -> dict:
    """Validate both feeds then produce a small, explicitly dated row register."""
    from scripts.validate import check_data
    from scripts.build_origination import validate_origination
    from scripts.pick_safety import presentation

    now = now or datetime.now(UTC)
    featured = _read(source / 'latest.json')
    complete = _read(source / 'origination.json')
    check_data(source)
    validate_origination(complete, source)
    originals = {str(m['id']): m for m in featured['matches'] if m['availability'] != 'past'}
    rows = []
    for m in complete['matches']:
        o = m.get('origination')
        safety = presentation(m, featured['inventory_observed_at'], featured['coverage_complete'], now)
        refs = [{'url': m['source_url'], 'role': 'Official Hotspawn fixture/inventory'}]
        if o:
            for q in o.get('quotes') or []:
                refs.append({'url': q['source_url'], 'provider': q.get('provider'),
                             'role': ('Official ratings input; uncalibrated research model' if q.get('family') == 'model'
                                      else 'Original paired prematch money line'),
                             'observed_at': q.get('observed_at'), 'evidence_file': q.get('evidence_file')})
            if not o.get('quotes'):
                refs.append({'url': o['source_url'], 'role': 'Official ratings input; uncalibrated research model',
                             'observed_at': o.get('observed_at'), 'snapshot_date': o.get('snapshot_date')})
        rows.append({'fixture_id': m['id'], 'teams': [t.get('name') for t in m['teams']],
                     'starts_at': m.get('starts_at'), 'locks_at': m.get('locks_at'),
                     'inventory_observed_at': featured['inventory_observed_at'],
                     'estimate_method': o.get('method') if o else None,
                     'probabilities': o.get('probabilities') if o else None,
                     'snapshot_pick_index': m.get('pick_index'), 'currently_usable': safety['current'],
                     'sources': refs, 'unresolved_reason': m.get('unresolved_reason') if not o else None,
                     'limitations': m.get('limitations', []),
                     'featured_facts_unchanged': m['teams'] == originals[str(m['id'])]['teams']
                                                 and m['starts_at'] == originals[str(m['id'])]['starts_at']})
    return {'schema_version': 1, 'audited_at': iso(now),
            'scope': 'Read-only source/replay register. Dated input estimates are not restamped or promoted to current picks.',
            'inventory_observed_at': featured['inventory_observed_at'],
            'origination_generated_at': complete['generated_at'],
            'inventory_fresh_at_audit': is_fresh(featured['inventory_observed_at'], now),
            'inventory_complete': featured['coverage_complete'],
            'input_sha256': {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                             for name in ('latest.json', 'origination.json')},
            'counts': {'canonical_nonpast_fixtures': len(originals), 'audited_rows': len(rows),
                       'supported_dated_estimates': sum(r['probabilities'] is not None for r in rows),
                       'currently_usable_lines': sum(r['currently_usable'] for r in rows),
                       'explicitly_unresolved': sum(r['probabilities'] is None for r in rows)},
            'research_discovery': complete.get('research_discovery'), 'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.source)
    except Exception as exc:
        message = (type(exc).__name__ + ': ' + str(exc)).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::error title=First-party source-integrity audit::' + message)
        raise
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('::notice title=First-party source-integrity audit::' + json.dumps({
        'inventory_observed_at': report['inventory_observed_at'],
        'counts': report['counts'], 'input_sha256': report['input_sha256']}))


if __name__ == '__main__':
    main()
