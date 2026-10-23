"""Read-only report: what the ladder actually priced on the runner (arena-7c0e457b).

Session 7C-1 added two things to the origination ladder: a Unibet/Kambi CS2
source (``scripts/kambi_lines.py``) and a near-time evidence class for a real
money price whose provider clock disagrees with Hotspawn's
(``scripts/gap_lines.py``). Both are fail-open and both are only exercised on a
network-connected machine, so this module exists to make one live run legible:
after ``scripts.collect`` + ``scripts.originate --live`` it reads the resulting
``data/origination.json`` and publishes

* how many active fixtures carry a first-party money line, a relayed line, or
  only a research model;
* which rows used the near-time class, with the provider, both clock values and
  the signed delta;
* for every research-model row, the first unresolved ladder stage and its
  reason — the published blocker, not a guess;
* what the Kambi capture contained: CS2 events seen, rows with a two-sided book,
  and rows whose team names did not resolve to this snapshot.

It never writes a pick, a probability, an alias or a published data file. The
report lands in ``data/research/7c0e457b/`` and the workflow that invokes it is
session-only and never deploys.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.domain import timestamp

SESSION = '7c0e457b'
MONEY = {'market', 'bookmaker', 'consensus', 'reference'}
LABEL = {'market': 'exchange/prediction market', 'bookmaker': 'bookmaker',
         'consensus': 'median of independent books', 'reference': 'aggregated reference',
         'relay': 'second-hand relay', 'model': 'Valve-rating model',
         'network': 'own results model', 'guidance': 'wide-book guidance'}


def _names(match: dict) -> str:
    teams = [t.get('name') or 'Unverified team' for t in match.get('teams') or []]
    return ' vs '.join(teams)


def _first_blocker(match: dict) -> dict:
    """The first failed ladder stage with its published reason."""
    for entry in match.get('research') or []:
        if str(entry.get('status') or '') in {'unresolved', 'rejected', 'blocked'}:
            return {'stage': entry.get('stage'), 'status': entry.get('status'),
                    'detail': entry.get('detail'), 'source_url': entry.get('source_url')}
    return {}


def kambi_summary(evidence: Path) -> dict:
    """Describe the saved Kambi capture without re-pricing anything."""
    path = evidence / 'live-kambi-cs2.json'
    if not path.exists():
        return {'captured': False, 'path': str(path)}
    try:
        document = json.loads(path.read_text())
    except ValueError as exc:
        return {'captured': True, 'path': str(path), 'error': f'invalid JSON: {exc}'}
    events = document.get('events') or []
    rows = document.get('rows') or []
    return {
        'captured': True,
        'path': str(path),
        'observed_at': document.get('observed_at'),
        'source_url': document.get('source_url'),
        'cs2_events_seen': document.get('cs2_events', len(events)),
        'rows_with_two_sided_book': len(rows),
        'rejected': document.get('rejected') or [],
        'rows': [{'provider': r.get('provider'), 'names': r.get('names'), 'odds': r.get('odds'),
                  'start': r.get('start'), 'event_id': r.get('event_id'),
                  'source_url': r.get('source_url')} for r in rows],
    }


def build_report(source: Path) -> dict:
    origination = json.loads((source / 'origination.json').read_text())
    latest = json.loads((source / 'latest.json').read_text()) if (source / 'latest.json').exists() else {}
    matches = [m for m in origination.get('matches') or []
               if m.get('availability') in {'open', 'locked', 'unknown_lock'}]
    rows, near, models = [], [], []
    for match in matches:
        quote = match.get('origination') or {}
        method = quote.get('method')
        row = {
            'id': str(match.get('id')), 'match': _names(match),
            'competition': match.get('competition'), 'starts_at': match.get('starts_at'),
            'method': method, 'class': LABEL.get(method, method),
            'probabilities': quote.get('probabilities'), 'source': quote.get('source'),
            'source_url': quote.get('source_url'), 'observed_at': quote.get('observed_at'),
            'binding': quote.get('binding'),
            'pick': (match.get('teams') or [{}, {}])[match['pick_index']]['name']
            if match.get('pick_index') is not None else None,
        }
        rows.append(row)
        if method not in MONEY:
            row['blocker'] = _first_blocker(match)
            models.append(row)
        if quote.get('binding') == 'near-time':
            near.append({'id': row['id'], 'match': row['match'], 'provider': quote.get('source'),
                         'hotspawn_start': quote.get('hotspawn_start'),
                         'provider_start': quote.get('provider_start'),
                         'start_delta_sec': quote.get('start_delta_sec'),
                         'probabilities': quote.get('probabilities')})
    classes = Counter(r['class'] for r in rows)
    return {
        'session': SESSION,
        'generated_at': origination.get('generated_at'),
        'source_snapshot_at': origination.get('source_snapshot_at'),
        'snapshot_generated_at': latest.get('generated_at'),
        'counts': origination.get('counts'),
        'active_fixtures': len(matches),
        'classes': dict(sorted(classes.items())),
        'money_rows': sum(1 for r in rows if r['method'] in MONEY),
        'rows_without_a_betting_line': len(models),
        'near_time_rows': near,
        'research_model_rows': models,
        'kambi': kambi_summary(source / 'origination' / 'evidence'),
        'rows': rows,
    }


def markdown(report: dict) -> str:
    lines = [f"# Live ladder report — session {report['session']}", '',
             f"- origination generated: {report.get('generated_at') or 'unknown'}",
             f"- source snapshot: {report.get('source_snapshot_at') or 'unknown'}",
             f"- active fixtures: **{report['active_fixtures']}**",
             f"- first-party money rows: **{report['money_rows']}**",
             f"- rows with only a research model: **{report['rows_without_a_betting_line']}**",
             f"- near-time rows: **{len(report['near_time_rows'])}**", '',
             '| fixture | class | pick | probabilities | source |', '| --- | --- | --- | --- | --- |']
    for row in report['rows']:
        probs = row.get('probabilities') or []
        shown = ' / '.join(f'{p * 100:.1f}%' for p in probs if isinstance(p, (int, float))) or '—'
        lines.append(f"| {row['match']} | {row['class']} | {row.get('pick') or '—'} | {shown} | "
                     f"{row.get('source') or '—'} |")
    if report['near_time_rows']:
        lines += ['', '## Near-time rows (same teams and date, clock disagrees)', '']
        for row in report['near_time_rows']:
            minutes = abs(row.get('start_delta_sec') or 0) / 60
            lines.append(f"- {row['match']} — {row['provider']} lists {row['provider_start']} vs "
                         f"Hotspawn {row['hotspawn_start']} ({minutes:.0f} min).")
    if report['research_model_rows']:
        lines += ['', '## Rows without a betting line', '']
        for row in report['research_model_rows']:
            blocker = row.get('blocker') or {}
            lines.append(f"- **{row['match']}** — {row['class']}; "
                         f"{blocker.get('stage') or 'no stage recorded'}: "
                         f"{(blocker.get('detail') or 'no detail recorded')[:240]}")
    kambi = report.get('kambi') or {}
    lines += ['', '## Unibet (Kambi) capture', '',
              f"- captured: {kambi.get('captured')}",
              f"- CS2 events seen: {kambi.get('cs2_events_seen')}",
              f"- rows with a two-sided Match Odds book: {kambi.get('rows_with_two_sided_book')}",
              f"- source: {kambi.get('source_url') or 'n/a'}"]
    return '\n'.join(lines) + '\n'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path(f'data/research/{SESSION}'))
    args = parser.parse_args(argv)
    if not (args.source / 'origination.json').exists():
        print('no data/origination.json — run scripts.originate first')
        return 2
    report = build_report(args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'live-ladder-report.json').write_text(json.dumps(report, indent=2) + '\n')
    text = markdown(report)
    (args.output / 'live-ladder-report.md').write_text(text)
    print(text)
    print(f"report written: {args.output / 'live-ladder-report.json'} ({timestamp(report.get('generated_at'))})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
