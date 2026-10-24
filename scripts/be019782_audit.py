"""Dated, read-only acceptance/research audit for the unattended CS2 refresh.

Run after collect + originate --live, never instead of them. Reuse the existing
strict source replay, then research only rows with no accepted external line:
HLTV match pages first, followed by original books/exchanges and a bounded
bo3.gg relay search. No probability, pick, alias or runtime file is edited.
A blocked page is unknown, not evidence that a bookmaker has no market.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts import audit_rows, pipeline_audit, smarkets_lines
from scripts.domain import is_fresh, timestamp

UTC = timezone.utc
MODEL_METHODS = {'model', 'guidance', 'form', 'network'}
# Reuse the existing, reviewed source readers; do not create another odds model.
research = importlib.import_module('scripts.2016c841_research')
RUN_URL = 'https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/'


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def targets(complete: dict) -> list[dict]:
    """Only no-line or unresolved rows; never redo a usable featured money pick."""
    out = []
    for match in complete.get('matches') or []:
        if match.get('availability') == 'past':
            continue
        estimate = match.get('origination') or {}
        if estimate and estimate.get('method') not in MODEL_METHODS:
            continue
        hltv = next((r.get('source_url') for r in match.get('research') or []
                     if str(r.get('stage', '')).lower().startswith('hltv')
                     and '/matches/' in str(r.get('source_url', ''))), None)
        out.append({'id': str(match['id']), 'teams': [t['name'] for t in match['teams']],
                    'competition': match.get('competition'), 'starts_at': match.get('starts_at'),
                    'hotspawn_url': match.get('source_url'), 'hltv_url': hltv,
                    'current_method': estimate.get('method') or 'unresolved',
                    'current_label': estimate.get('label') or 'Unresolved — no supported estimate',
                    'limitations': match.get('limitations') or [],
                    'research': match.get('research') or []})
    return out


def unique_relay(target: dict, rows: list[dict]) -> tuple[dict | None, str]:
    """Both exact names, start within 60 s, and one unique full match only.

    This is a lead, not an executable quote. Unlike a first/last-match scan,
    ambiguity cannot silently pick a duplicate event or the next meeting.
    """
    wanted = {research.key(n) for n in target.get('teams') or []}
    start = timestamp(target.get('starts_at'))
    if len(wanted) != 2 or start is None:
        return None, 'unverified fixture identity/start; no relay join attempted'
    candidates = {}
    for row in rows:
        names = {research.key((row.get(side) or {}).get('name')) for side in ('team1', 'team2')}
        row_start = timestamp(row.get('start_date'))
        if names != wanted or row_start is None or abs((start - row_start).total_seconds()) > 60:
            continue
        # Only rows explicitly listed as upcoming are leads. An unknown/live
        # status is not made prematch by its start time alone.
        if row.get('status') != 'upcoming':
            continue
        identity = str(row.get('id') or row.get('slug') or '')
        if not identity:
            continue
        if identity in candidates and candidates[identity] != row:
            return None, 'conflicting observations for the same relay fixture'
        candidates[identity] = row
    if len(candidates) != 1:
        return None, f'{len(candidates)} unique exact-name/start upcoming relay fixtures; not a verified price'
    return next(iter(candidates.values())), 'one exact-name/start upcoming relay fixture'


def paired_relay(row: dict | None) -> dict | None:
    """Copy a real active two-sided decimal block; never calculate a probability."""
    if row is None:
        return None
    quote = research.relay_block(row)
    if not quote or not quote.get('two_sided_price') or not quote.get('provider'):
        return None
    sides = quote.get('sides') or {}
    for key in ('team_1', 'team_2'):
        side = sides.get(key) or {}
        value = side.get('coeff')
        if (isinstance(value, bool) or not isinstance(value, (float, int))
                or not math.isfinite(value) or value <= 1 or side.get('active') is not True):
            return None
    names = {research.key(sides[k].get('name')) for k in ('team_1', 'team_2')}
    if names != {research.key((row.get(k) or {}).get('name')) for k in ('team1', 'team2')}:
        return None
    return {'provider': quote['provider'], 'path': quote.get('book_url'),
            'team_1': sides['team_1'], 'team_2': sides['team_2']}


def source_link(url: str | None, label: str) -> str:
    return f'[{label}]({url})' if url else 'unverified — no confirmed source URL'


def write_research(source: Path, out: Path, complete: dict, now: datetime) -> dict:
    selected = targets(complete)
    session = requests.Session()
    # Actually perform the requests in the order described by the brief.
    hltv = {}
    for target in selected:
        url = target.get('hltv_url') or 'https://www.hltv.org/matches'
        hltv[target['id']] = research.fetch(session, url, timeout=20)
    providers = []
    for label, url in research.PAGES:
        if label.startswith('HLTV') or 'bo3.gg' in label or 'Smarkets' in label:
            continue  # already checked above, or structured originals below
        providers.append({'label': label, **research.fetch(session, url, timeout=12)})
    relay_rows, relay_requests = research.bo3_upcoming(session, pages=5)
    exchange = smarkets_lines.rows(source / 'origination/evidence')
    exchange_document = source / 'origination/evidence' / smarkets_lines.EVIDENCE_NAME
    exchange_original = json.loads(exchange_document.read_text()) if exchange_document.is_file() else {}
    per_fixture = []
    for target in selected:
        bound, join_note = unique_relay(target, relay_rows)
        quote = paired_relay(bound)
        exchange_quotes = [q for q in exchange if str(q.get('fixture_id')) == target['id']]
        bindings = [b for b in exchange_original.get('bindings') or []
                    if str(b.get('hotspawn_id')) == target['id']]
        note = ('Two-sided bookmaker relay lead only; original-source replay is required before any pick changes.'
                if quote else 'No new usable two-sided relay price confirmed in the bounded scan. '
                'Blocked/empty/unlisted sources do not establish that no market exists anywhere. '
                'Current research estimates remain explicitly model-only; unresolved values remain blank.')
        per_fixture.append({**target, 'hltv_page': hltv[target['id']],
                            'bo3_join_note': join_note,
                            'bo3_bound_url': ('https://bo3.gg/matches/' + bound['slug']) if bound and bound.get('slug') else None,
                            'bo3_bet': quote, 'bo3_bet_two_sided': bool(quote),
                            'money_line_lead': bool(quote),
                            'smarkets_evidence': {'two_sided': bool(exchange_quotes),
                                                   'event_url': bindings[0].get('event_url') if len(bindings) == 1 else None,
                                                   'bindings': bindings, 'quotes': exchange_quotes},
                            'verdict': note})
    doc = {'schema_version': 1, 'session': 'arena-be019782', 'observed_at': iso(now),
           'completed_at': iso(datetime.now(UTC)),
           'environment': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'local checkout',
           'run_url': RUN_URL + os.environ['GITHUB_RUN_ID'] if os.environ.get('GITHUB_RUN_ID') else None,
           'policy': 'Read-only. HLTV first, then esportsbooks/exchanges. No crowd votes, invented odds, probabilities, picks or aliases.',
           'target_source': {'source': 'freshly collected and source-replayed in this run',
                             'source_url': str(source / 'origination.json'),
                             'snapshot_generated_at': complete.get('generated_at'), 'targets': len(selected)},
           'per_fixture': per_fixture, 'providers': providers,
           'relay_discovery': {'requests': relay_requests, 'rows_seen': len(relay_rows), 'max_pages': 5,
                               'limitation': 'Bounded discovery; absence is not global bookmaker noncoverage.'},
           'leads': [f for f in per_fixture if f['money_line_lead']]}
    (out / 'line-source-research.json').write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    lines = ['# Dated no-line research — arena-be019782', '',
             f'Observed {doc["observed_at"]}; completed {doc["completed_at"]}. '
             f'Snapshot {complete.get("generated_at")}. **{len(selected)}** no-line/unresolved fixtures; '
             f'**{len(doc["leads"])}** new relay leads. No probability or pick was written by this probe.', '',
             '| Fixture (official source) | Basis | HLTV HTTP | Relay join | Limitation / verdict |',
             '| --- | --- | --- | --- | --- |']
    for f in per_fixture:
        status = f['hltv_page'].get('http_status') or f['hltv_page'].get('error') or 'unverified'
        lines.append(f'| {source_link(f["hotspawn_url"], " vs ".join(f["teams"]))} | {f["current_label"]} | '
                     f'{source_link(f["hltv_page"].get("url"), str(status))} | '
                     f'{source_link(f["bo3_bound_url"], f["bo3_join_note"])} | {f["verdict"]} |')
    lines += ['', '## Original-source access (HTTP 200 is not a fixture price)', '',
              '| Source | HTTP | Limitation |', '| --- | --- | --- |']
    for p in providers:
        lines.append(f'| {source_link(p["url"], p["label"])} | {p.get("http_status") or "unverified"} | '
                     f'{p.get("error") or ("challenge page; no price verified" if p.get("challenge_page") else "reachability only; see each fixture’s saved research trail")} |')
    lines += ['', 'Every fixture retains the original collector/research trail in the JSON. '
              'Smarkets quotes are copied from that run’s original saved exchange response; '
              'the production ladder alone decides spread/freshness eligibility. '
              'HLTV fan polls and Hotspawn participation are excluded.']
    (out / 'line-source-research.md').write_text('\n'.join(lines) + '\n')
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('data/research/be019782'))
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    latest = json.loads((args.source / 'latest.json').read_text())
    complete = json.loads((args.source / 'origination.json').read_text())
    # Do not promote a local stale fixture or a failed collection as dated live research.
    if not latest.get('coverage_complete') or not is_fresh(latest.get('inventory_observed_at'), now):
        raise ValueError('A fresh, complete official inventory is required for this live research audit')
    report = pipeline_audit.audit(args.source, now=now)
    report['session'] = 'arena-be019782'
    report['runtime_input_sha256'] = hashlib.sha256((args.source / 'origination.json').read_bytes()).hexdigest()
    report['source_link_check'] = all(audit_rows.is_official(ref['url'])
                                      for row in report['rows'] for ref in row['sources'])
    if not report['source_link_check']:
        raise ValueError('An audit row lacks a recognised first-party source URL')
    (args.out / 'source-replay.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    # Keep the original resolved records needed for an independently reviewable
    # per-fixture dossier. Never overwrite deterministic repository data fixtures.
    (args.out / 'audited-fixtures.json').write_text(json.dumps({
        'generated_at': complete.get('generated_at'), 'source_snapshot_at': complete.get('source_snapshot_at'),
        'counts': complete.get('counts'), 'matches': complete.get('matches')}, indent=2, ensure_ascii=False) + '\n')
    document = write_research(args.source, args.out, complete, now)
    print('::notice title=be019782 verified live acceptance::' + json.dumps({
        'snapshot': report['inventory_observed_at'], 'counts': report['counts'],
        'no_line_targets': len(document['per_fixture']), 'new_relay_leads': len(document['leads'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
