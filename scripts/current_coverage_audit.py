"""Read-only current inventory audit. Never writes picks or substitutes cached data.

Run on a network-capable runner. Compares separately timestamped live snapshots,
then researches only no-line fixtures, HLTV first, using existing read-only probes.
A snapshot race is a review finding, not proof that the collector dropped a match.
"""
from __future__ import annotations

import argparse
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts.coverage_audit import audit_complete_picks

BASE = 'https://buffedlizard55-lab.github.io/MaltaProj3/'
MONEY = {'market', 'bookmaker', 'consensus', 'reference'}


def reconcile(latest, complete, now):
    """Report coverage and freshness separately; do not bless old complete snapshots."""
    inventory = [m for m in latest.get('matches', []) if m.get('availability') != 'past']
    rows = complete.get('matches', [])
    expected = {str(m['id']) for m in inventory}
    actual = {str(m['id']) for m in rows}
    generated = latest.get('generated_at')
    try:
        age = (now - datetime.fromisoformat(generated.replace('Z', '+00:00'))).total_seconds() / 3600
    except (ValueError, TypeError, AttributeError):
        age = None
    source_clock = complete.get('source_generated_at') or complete.get('source_snapshot_at')
    coherent = source_clock == generated
    findings = []
    if age is None or age < 0 or age > 8:
        findings.append('Inventory timestamp missing, in the future, or older than eight hours; not verified current.')
    if not coherent:
        findings.append('Published inventory and complete-picks source clocks differ; fetch may straddle a deployment.')
    if expected != actual:
        findings.append('Active inventory and complete-pick IDs differ; inspect missing/extra IDs and snapshot clocks.')
    if len(rows) != len(actual):
        findings.append('Duplicate complete-pick IDs.')
    if latest.get('coverage_complete') is not True:
        findings.append('Collector does not assert complete inventory.')
    findings.extend(audit_complete_picks(complete))
    gaps = []
    for m in rows:
        o = m.get('origination') or {}
        if o.get('method') in MONEY or o.get('family') == 'relay':
            continue
        gaps.append({
            'id': m['id'], 'teams': [t.get('name') for t in m.get('teams', [])],
            'competition': m.get('competition'), 'starts_at': m.get('starts_at'),
            'hotspawn_url': m.get('source_url'), 'method': o.get('method'),
            'probabilities': o.get('probabilities'), 'pick_index': m.get('pick_index'),
            'source_url': o.get('source_url'), 'research': m.get('research', []),
            'limitations': m.get('limitations', []) + o.get('limitations', []),
            'state': 'model-only; not a betting line' if o else 'unresolved; probability blank',
        })
    return {'inventory_generated_at': generated, 'complete_source_clock': source_clock,
            'snapshot_clocks_agree': coherent, 'inventory_age_hours': age,
            'active_inventory': len(inventory), 'complete_rows': len(rows),
            'directional_picks': sum(m.get('pick_index') in (0, 1) for m in rows),
            'unresolved': sum(not m.get('origination') for m in rows),
            'missing_ids': sorted(expected - actual), 'extra_ids': sorted(actual - expected),
            'findings': findings, 'no_line_fixtures': gaps}


def fetch(url):
    observed = datetime.now(timezone.utc).isoformat()
    response = requests.get(url, timeout=45, headers={'Cache-Control': 'no-cache'})
    response.raise_for_status()
    return response.json(), {'url': url, 'observed_at': observed, 'http_status': response.status_code}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/research/38c53ece'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    latest, inventory_fetch = fetch(BASE + 'data/latest.json')
    complete, picks_fetch = fetch(BASE + 'data/origination.json')
    report = reconcile(latest, complete, now)
    report.update(observed_at=now.isoformat(), fetches=[inventory_fetch, picks_fetch],
                  policy='Read-only audit; no price inferred from reachability, votes, rankings or team mentions. Model probabilities are existing uncalibrated estimates, not official odds.')
    # Retain the exact public documents so reconciliation can be reproduced.
    for name, doc in [('published-inventory', latest), ('published-complete-picks', complete)]:
        (args.out / (name + '.json')).write_text(json.dumps(doc, indent=2) + '\n')
    probe = importlib.import_module('scripts.3016b0c6_probe')
    targets = report['no_line_fixtures']
    teams = sorted({t for m in targets for t in m['teams'] if t})
    report['surfaces'] = [probe.probe_page(n, u, teams, timeout=12) for n, u in probe.PAGES] if targets else []
    from scripts.bo3_odds_probe import key
    report['pinnacle'] = probe.pinnacle_scan({frozenset(key(t) for t in m['teams'] if t): ' vs '.join(m['teams']) for m in targets}) if targets else {}
    report['bo3_relay_leads_not_verified_prices'] = probe.bo3_scan(targets) if targets else []
    # The API URL is taken from the published original inventory, never guessed.
    api = next((m.get('source_api') for m in latest.get('matches', []) if m.get('source_api')), None)
    if api:
        try:
            official, observation = fetch(api)
            (args.out / 'official-inventory-response.json').write_text(json.dumps(official, indent=2) + '\n')
            report['official_inventory_fetch'] = observation
            if not isinstance(official, list) or not official or any(not isinstance(m, dict) or not m.get('id') or m.get('sport_alias') != 'cs2' for m in official):
                raise ValueError('Unexpected official inventory contract')
            official_ids = [str(m['id']) for m in official]
            if len(official_ids) != len(set(official_ids)):
                raise ValueError('Duplicate official inventory IDs')
            published_ids = {str(m['id']) for m in latest.get('matches', [])}
            report['official_inventory_delta'] = {
                'official_records': len(official_ids),
                'added_since_publication': sorted(set(official_ids) - published_ids),
                'removed_since_publication': sorted(published_ids - set(official_ids)),
            }
            if set(official_ids) != published_ids:
                report['findings'].append('Official inventory has changed since publication; additions/removals are recorded, not silently treated as covered.')
            report['official_inventory_note'] = 'Raw official response saved separately. Observation is later than the published snapshot; this is not a simultaneous inventory-equality claim.'
        except (requests.RequestException, ValueError) as exc:
            report['official_inventory_fetch'] = {'url': api, 'error': str(exc)}
            report['findings'].append('Fresh official inventory could not be fetched; published coverage is not independently confirmed against current Hotspawn.')
    else:
        report['findings'].append('Published inventory has no source_api URL; fresh official check unavailable.')
    (args.out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    details = (f"Dated audit {report['observed_at']}: published snapshot {report['inventory_generated_at']}; "
               f"{report['active_inventory']} active records, {report['complete_rows']} complete rows, "
               f"{report['directional_picks']} directional picks, {report['unresolved']} unresolved, "
               f"{len(targets)} without an external betting line. "
               'HLTV was probed first, then esportsbooks. HTTP success or a team mention is not a verified price. '
               'Relay responses are leads only, never new picks. Consult current pick cards, not this historical audit. '
               + ' '.join(report['findings']))
    flags = [{'id': '38c53ece-current-coverage-audit', 'severity': 'notice',
              'match_ids': [], 'title': 'Dated live coverage and no-line source audit (23 October)',
              'detail': details, 'source_urls': [
                  'https://play.hotspawn.com/lobby', 'https://www.hltv.org/matches',
                  'https://guest.api.arcadia.pinnacle.com/0.1/sports/29/matchups',
                  'https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/38c53ece/audit.json']}]
    (args.out / 'flags.json').write_text(json.dumps(flags, indent=2) + '\n')
    print(details)


if __name__ == '__main__':
    main()
