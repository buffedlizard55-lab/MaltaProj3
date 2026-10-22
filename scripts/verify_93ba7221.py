"""Read-only line-by-line verification of the published pick data (session 93ba7221).

Every check works on files already in the tree or on the published JSON, never on a
live provider, and it produces no probability of its own: it either reproduces the
published number from the published inputs or reports that it cannot.

Run: python -m scripts.93ba7221_verify [--data data] [--out data/research/93ba7221]
Exit code 0 = every published value reproduced; 1 = at least one row failed, with
the failing ids printed. Nothing is written unless --out is given.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

#: Hosts that count as an official or first-party source for a published row.
OFFICIAL_HOSTS = (
    'https://polymarket.com/', 'https://gamma-api.polymarket.com/', 'https://clob.polymarket.com/',
    'https://kalshi.com/', 'https://api.elections.kalshi.com/',
    'https://thunderpick.io/', 'https://www.bovada.lv/', 'https://bo3.gg/',
    'https://www.hltv.org/', 'https://hltv.org/',
    'https://github.com/ValveSoftware/counter-strike_regional_standings',
    'https://egamersworld.com/', 'https://www.hotspawn.com/', 'https://play.hotspawn.com/',
    'https://phpstack-1372681-6459848.cloudwaysapps.com/',
)

MONEY = {'market', 'bookmaker', 'consensus', 'reference'}
ACTIVE = {'open', 'locked', 'unknown_lock'}
TOL = 5e-4  # published values are rounded to four decimals


def _prob_pair(quotes) -> list[float] | None:
    """No-vig probabilities from two decimal (or two 0-1) quotes, or None."""
    try:
        values = [float(q) for q in quotes]
    except (TypeError, ValueError):
        return None
    if len(values) != 2:
        return None
    if all(v <= 1.0 for v in values):      # already probabilities (midpoints)
        total = sum(values)
        return [v / total for v in values] if total > 0 else None
    if all(v > 1.0 for v in values):       # decimal odds
        inv = [1 / v for v in values]
        total = sum(inv)
        return [v / total for v in inv] if total > 0 else None
    return None


def _checks(source: dict, pick, trail) -> dict:
    """Every reproducible property of one published record."""
    checks = {}
    probs = source.get('probabilities') or []
    checks['two_sided'] = len(probs) == 2 and all(0 < p < 1 for p in probs)
    checks['sums_to_one'] = bool(checks['two_sided']) and abs(sum(probs) - 1) <= TOL
    checks['pick_matches_higher_probability'] = (
        pick in (0, 1) and bool(checks['two_sided']) and probs[pick] >= probs[1 - pick])
    checks['no_exact_even_with_a_side'] = not (
        bool(checks['two_sided']) and abs(probs[0] - probs[1]) < 1e-8 and pick is not None)
    url = str(source.get('source_url') or '')
    checks['official_source_link'] = any(url.startswith(h) for h in OFFICIAL_HOSTS)
    checks['research_trail_has_a_link'] = all(
        str(t.get('source_url') or '').startswith('https://') for t in trail) if trail else False

    method = str(source.get('method') or '')
    quotes = [q for q in (source.get('quotes') or []) if isinstance(q, dict)]
    if method in MONEY and quotes:
        # A prediction market publishes a bid/ask pair per outcome; an esportsbook
        # publishes a decimal price pair instead. Recompute from whichever the row
        # actually saved, never from the published result.
        mids = [q.get('midpoint') for q in quotes]
        if all(m is not None for m in mids):
            reproduced = _prob_pair(mids)
            checks['reproduces_from_saved_quotes'] = bool(reproduced) and all(
                abs(a - b) <= 2e-3 for a, b in zip(reproduced, probs))
            checks['spread_within_12_cents'] = all(
                float(q.get('spread', 0)) <= 0.12 + 1e-9 for q in quotes)
        elif all(isinstance(q.get('odds'), list) for q in quotes):
            odds = quotes[0]['odds']
            reproduced = _prob_pair(odds)
            checks['reproduces_from_saved_quotes'] = bool(reproduced) and all(
                abs(a - b) <= 2e-3 for a, b in zip(reproduced, probs))
            # A two-way book keeps a positive margin; a pair summing to 1.0 or
            # below is a placeholder or an error, not a price.
            checks['book_holds_a_margin'] = sum(1 / float(o) for o in odds) > 1.0
        else:
            checks['reproduces_from_saved_quotes'] = False
    elif method == 'model':
        inputs = source.get('inputs') or []
        points = [i.get('points') for i in inputs]
        rd = source.get('rd_assumption')
        g = source.get('g')
        if len(points) == 2 and rd and g:
            p0 = 1 / (1 + 10 ** (float(g) * (float(points[1]) - float(points[0])) / 400))
            checks['reproduces_from_published_points'] = abs(p0 - probs[0]) <= TOL
            checks['rd_assumption_is_75'] = float(rd) == 75
        else:
            checks['reproduces_from_published_points'] = False
    return checks


def check(data_dir: Path) -> dict:
    latest = json.loads((data_dir / 'latest.json').read_text(encoding='utf-8'))
    complete = {}
    origination_path = data_dir / 'origination.json'
    if origination_path.exists():
        complete = {str(r['id']): r for r in
                    (json.loads(origination_path.read_text(encoding='utf-8')).get('matches') or [])}
    rows, failures = [], []
    for match in latest['matches']:
        if match['availability'] not in ACTIVE:
            continue
        fid = str(match['id'])
        record = complete.get(fid) or {}
        featured = match.get('analysis')
        ladder = record.get('origination')
        # The site renders the ladder record when it exists and the featured
        # estimate otherwise; both are verified, but only the rendered one can
        # fail the run, so a replaced estimate never hides a real defect.
        candidates = []
        if ladder:
            candidates.append(('origination', ladder,
                               record.get('pick_index'),
                               record.get('research') or match.get('research') or []))
        if featured:
            candidates.append(('featured', featured, match.get('pick_index'),
                               match.get('research') or record.get('research') or []))
        name = ' vs '.join(t['name'] or '?' for t in match['teams'])
        if not candidates:
            rows.append({'fixture_id': fid, 'fixture': name,
                         'status': 'unresolved — no probability published', 'checks': {}})
            continue
        rendered_kind = candidates[0][0]
        row = {'fixture_id': fid, 'fixture': name, 'competition': match.get('competition'),
               'starts_at': match.get('starts_at'), 'rendered_record': rendered_kind,
               'records': {}, 'checks': {}, 'status': 'reproduced'}
        problems = []
        for kind, source, pick, trail in candidates:
            checks = _checks(source, pick, trail)
            failed = [n for n, ok in checks.items() if ok is False]
            row['records'][kind] = {'method': source.get('method'), 'label': source.get('label'),
                                    'probabilities': source.get('probabilities'),
                                    'pick_index': pick, 'source_url': source.get('source_url'),
                                    'failed_checks': failed}
            if kind == rendered_kind:
                row.update({'checks': checks, 'method': source.get('method'),
                            'label': source.get('label'), 'probabilities': source.get('probabilities'),
                            'pick_index': pick, 'source_url': source.get('source_url')})
                problems = failed
        if problems:
            row['status'] = 'FAILED'
            failures.append({'fixture_id': fid, 'fixture': name, 'problems': problems})
        rows.append(row)
    return {
        'observed_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source_snapshot_generated_at': latest.get('generated_at'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'active_rows': len(rows),
        'with_published_probability': sum(1 for r in rows if r['checks']),
        'reproduced': sum(1 for r in rows if r['status'] == 'reproduced'),
        'failed': failures,
        'rows': rows,
        'note': ('Every check recomputes a published value from inputs that are already published with it (saved '
                 'order-book midpoints, saved bookmaker decimal odds, or Valve points with the documented formula). '
                 'It contacts no provider and writes no probability of its own. A row that cannot be reproduced is '
                 'reported, not repaired.'),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=None)
    args = parser.parse_args()
    report = check(args.data)
    print(json.dumps({k: report[k] for k in
                      ('active_rows', 'with_published_probability', 'reproduced', 'failed')}, indent=2))
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / 'row-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 1 if report['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
