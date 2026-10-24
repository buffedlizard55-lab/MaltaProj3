"""Read-only audit of the published root complete-picks page and its snapshot.

This checks fixture coverage, source links and presentation consistency in the
last published root artifacts. It deliberately does not claim that old external
markets are still available or substitute for a fresh collector/originator run.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import audit_rows


def percent_values(nodes):
    return [float(node.get_text(strip=True).rstrip('%')) for node in nodes]


def pick_name(row):
    text = row.select_one('.tbl-pick').get_text(' ', strip=True)
    return re.sub(r'^(?:(?:✓\s*)|(?:Snapshot:\s*))+', '', text).strip()


def compare_featured(row, card, overview, analysis):
    """Allow only the renderer's explicit, exact money-line upgrade note.

    The complete-picks layer may replace an uncalibrated featured model with a
    verified market. Its card preserves the old pair and the reason. A bare
    probability mismatch, an approximate note, or an unlabelled row still fails.
    """
    expected = [round(value * 100, 1) for value in analysis['probabilities']]
    if overview == expected:
        return 'matched-snapshot-analysis'
    if analysis.get('method') == 'model' and 'Money-backed line' in row.get_text(' ', strip=True):
        old_pair = f'({expected[0]:.1f}% / {expected[1]:.1f}%)'
        notes = [node.get_text(' ', strip=True) for node in card.select('.alias-note')]
        if any('Upgraded from the featured Valve-model estimate ' + old_pair in note
               and 'found a verified money-backed line, which replaces the uncalibrated model' in note
               for note in notes):
            return 'documented-money-line-upgrade'
    return 'mismatch'


def audit(root: Path) -> dict:
    snapshot = json.loads((root / 'snapshot.json').read_text(encoding='utf-8'))
    page_path = root / 'origination/index.html'
    markup = page_path.read_text(encoding='utf-8')
    soup = BeautifulSoup(markup, 'html.parser')
    active = {m['id']: m for m in snapshot['matches'] if m.get('availability') != 'past'}
    rows = {row['id'].removeprefix('row-'): row for row in soup.select('.picks-table tbody tr[id^="row-"]')}
    violations = []
    checked = []

    if set(rows) != set(active):
        violations.append({'type': 'fixture-coverage', 'missing': sorted(set(active) - set(rows)),
                           'unexpected': sorted(set(rows) - set(active))})
    if len(rows) != len(soup.select('.picks-table tbody tr[id^="row-"]')):
        violations.append({'type': 'duplicate-overview-id'})
    body = soup.body
    if not body or body.get('data-inventory-at') != snapshot.get('inventory_observed_at'):
        violations.append({'type': 'inventory-binding', 'expected': snapshot.get('inventory_observed_at'),
                           'actual': body.get('data-inventory-at') if body else None})

    for match_id, match in sorted(active.items()):
        row = rows.get(match_id)
        if row is None:
            continue
        cards = soup.select(f'#match-{match_id}')
        teams = [team['name'] for team in match['teams']]
        if len(cards) != 1:
            violations.append({'type': 'evidence-card-count', 'match_id': match_id, 'count': len(cards)})
            continue
        card = cards[0]
        card_teams = [node.get_text(' ', strip=True) for node in card.select('.teams > strong')]
        if card_teams != teams:
            violations.append({'type': 'card-team-order', 'match_id': match_id,
                               'expected': teams, 'actual': card_teams})
        if row.select_one('th a').get_text(' ', strip=True) != ' vs '.join(teams):
            violations.append({'type': 'overview-team-order', 'match_id': match_id})

        overview = percent_values(row.select('.tbl-prob > strong'))
        evidence = percent_values(card.select('.probs > li > strong'))
        if len(overview) != 2 or overview != evidence:
            violations.append({'type': 'probability-agreement', 'match_id': match_id,
                               'overview': overview, 'evidence': evidence})
        if len(overview) == 2 and abs(sum(overview) - 100) > 0.11:
            violations.append({'type': 'probability-total', 'match_id': match_id, 'values': overview})

        source_links = [a.get('href') for a in row.select('.tbl-srcs a[href]')]
        if match['source_url'] not in source_links:
            violations.append({'type': 'official-fixture-link', 'match_id': match_id,
                               'expected': match['source_url'], 'actual': source_links})
        if any(not url.startswith('https://') for url in source_links):
            violations.append({'type': 'non-https-source', 'match_id': match_id, 'actual': source_links})
        if card.select_one('.pick-line strong') is None:
            violations.append({'type': 'missing-card-pick', 'match_id': match_id})
            continue
        selected = pick_name(row)
        card_selected = card.select_one('.pick-line strong').get_text(' ', strip=True)
        if selected != card_selected or selected not in teams:
            violations.append({'type': 'pick-agreement', 'match_id': match_id,
                               'overview': selected, 'evidence': card_selected, 'teams': teams})
        if selected in teams and len(overview) == 2:
            selected_probability = overview[teams.index(selected)]
            if selected_probability != max(overview) or selected_probability <= 50:
                violations.append({'type': 'not-obvious-pick', 'match_id': match_id,
                                   'pick': selected, 'probabilities': overview})

        analysis = match.get('analysis') or {}
        featured_comparison = 'not-applicable-complete-layer-supplement'
        if match.get('pick_index') is not None and analysis.get('probabilities'):
            featured_comparison = compare_featured(row, card, overview, analysis)
            if featured_comparison == 'mismatch':
                expected = [round(value * 100, 1) for value in analysis['probabilities']]
                violations.append({'type': 'snapshot-analysis-agreement', 'match_id': match_id,
                                   'expected': expected, 'actual': overview})
            if analysis.get('source_url') not in source_links:
                violations.append({'type': 'snapshot-analysis-link', 'match_id': match_id,
                                   'expected': analysis.get('source_url'), 'actual': source_links})
                featured_comparison = 'mismatch'

        checked.append({'match_id': match_id, 'teams': teams, 'fixture_source': match['source_url'],
                        'analysis_sources': [url for url in source_links if url != match['source_url']],
                        'probabilities_percent': overview, 'pick': selected,
                        'snapshot_analysis_comparison': featured_comparison})

    source_audit = audit_rows.audit_html(markup, 'origination/index.html')
    return {
        'audited_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'audit_scope': ('Read-only consistency/source audit of the last published root artifacts. '
                        'This is not a fresh market-availability or probability re-derivation.'),
        'page': 'https://buffedlizard55-lab.github.io/MaltaProj3/origination/',
        'snapshot': 'https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json',
        'source_snapshot_at': snapshot.get('inventory_observed_at'),
        'snapshot_generated_at': snapshot.get('generated_at'),
        'snapshot_coverage_complete': snapshot.get('coverage_complete'),
        'active_snapshot_fixtures': len(active),
        'overview_rows': len(rows),
        'evidence_cards': len(soup.select('.pick-card[data-safety-card]')),
        'row_source_audit': {key: source_audit[key] for key in ('rows', 'ok', 'flagged', 'navigation', 'violation')},
        'checks': checked,
        'violations': violations,
        'status': 'pass' if not violations and source_audit['violation'] == 0 else 'fail',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit(args.root)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('status', 'source_snapshot_at', 'active_snapshot_fixtures',
                                                   'overview_rows', 'evidence_cards', 'violations')}, indent=2))
    raise SystemExit(0 if result['status'] == 'pass' else 1)


if __name__ == '__main__':
    main()
