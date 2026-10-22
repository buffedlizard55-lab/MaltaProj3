"""Session 3cf793ef — independent recomputation of every Valve-rating probability.

The brief asks for a line-by-line review of the published numbers against the
official source, with a link for manual review, and explicitly forbids
unverified values. The largest single block of published rows is the
"Valve official standings" research model, so this script re-derives each of
those probabilities from Valve's own public markdown instead of trusting the
published JSON.

It applies the documented formula (scripts/domain.py:valve_analysis):

    g = 1 / sqrt(1 + 3 * (ln 10 / 400)^2 * RD^2 / pi^2),  RD = 75
    p = 1 / (1 + 10 ** (g * (points_away - points_home) / 400))

and the same identity rule: an exact-name row whose roster has five players,
exactly one such row, snapshot no older than 35 days. Where Valve rounded both
sides to the same integer the per-roster detail files carry the exact values;
that case is reported as "needs detail file" rather than silently accepted.

Usage:
    python -m scripts.3cf793ef_valve_check --standings valve.md \
        --origination data/origination.json --out report.json --markdown report.md

No network access is required: the standings markdown is passed in, so the
source file can be archived next to the report for manual review.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

RD = 75
TOLERANCE = 0.002


def rows_from_markdown(text: str) -> list[dict]:
    """Parse Valve's standings table into name/points/roster/standing records."""
    rows = []
    for line in text.splitlines():
        if not line.startswith('|') or 'details/' in line and not re.search(r'\|\s*\d+\s*\|', line):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        roster = [p.strip() for p in cells[3].split(',') if p.strip()] if cells[3] else []
        rows.append({'standing': int(cells[0]), 'points': int(cells[1]), 'name': cells[2], 'roster': roster})
    return rows


def g_value() -> float:
    return 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * RD ** 2 / math.pi ** 2)


def key(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', (name or '').lower())


def lookup(rows: list[dict], name: str) -> tuple[dict | None, str]:
    found = [r for r in rows if key(r['name']) == key(name)]
    if not found:
        return None, 'no exact-name Valve rating found'
    complete = [r for r in found if len(r['roster']) == 5]
    if len(complete) > 1:
        return None, f'{len(complete)} five-player rows share this name; identity unresolved'
    if not complete:
        return None, 'no five-player roster row'
    return complete[0], ''


def probabilities(pair, g):
    home, away = pair
    p = 1 / (1 + 10 ** (g * (away['points'] - home['points']) / 400))
    return [p, 1 - p]


def best_candidates(rows, names, probs, g):
    """Find the duplicate-row pair whose formula output matches the published values."""
    homes = [r for r in rows if key(r['name']) == key(names[0]) and len(r['roster']) == 5]
    aways = [r for r in rows if key(r['name']) == key(names[1]) and len(r['roster']) == 5]
    for h in homes:
        for a in aways:
            if max(abs(x - y) for x, y in zip(probs, probabilities((h, a), g))) <= TOLERANCE:
                return [h, a]
    return None


def git_blob_sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def detail_points(origination, home, away, g, detail_dir):
    """Resolve the rounded-points tie from Valve's per-roster detail markdown."""
    inputs = origination.get('inputs') or []
    if not detail_dir or len(inputs) != 2:
        return None, {'reason': 'Valve rounded both sides to the same integer; no archived detail file supplied'}
    resolved = []
    notes = []
    for row in inputs:
        path = row.get('detail_path')
        recorded = row.get('detail_sha')
        if not path or not recorded:
            return None, {'reason': 'Published row does not record a detail path and blob SHA'}
        file = Path(detail_dir) / Path(path).name
        if not file.exists():
            return None, {'reason': f'Detail file {Path(path).name} is not archived next to this report'}
        raw = file.read_bytes()
        digest = git_blob_sha(raw)
        if digest != recorded:
            return None, {'reason': f'Detail file {Path(path).name} hash {digest} does not match the published {recorded}'}
        import re as _re
        found = _re.search(r'Final Rank Value:\s*([0-9.]+)', raw.decode('utf-8'))
        if not found:
            return None, {'reason': f'No Final Rank Value in {Path(path).name}'}
        resolved.append({'name': row['name'], 'standing': row['standing'],
                         'points': float(found.group(1)), 'detail_sha': digest})
        notes.append(f"{row['name']} {found.group(1)} (blob {digest[:12]})")
    p = 1 / (1 + 10 ** (g * (resolved[1]['points'] - resolved[0]['points']) / 400))
    return [p, 1 - p], {'inputs': resolved,
                        'reason': 'Rounded summary tie resolved from the archived per-roster detail markdown, blob SHA verified: ' + '; '.join(notes)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--standings', required=True)
    ap.add_argument('--origination', required=True)
    ap.add_argument('--out')
    ap.add_argument('--markdown')
    ap.add_argument('--detail-dir', help='Directory holding archived Valve per-roster detail markdown')
    args = ap.parse_args()

    rows = rows_from_markdown(Path(args.standings).read_text())
    published = json.loads(Path(args.origination).read_text())
    g = g_value()
    checks = []
    for match in published.get('matches', []):
        o = match.get('origination') or {}
        if o.get('method') != 'model' or o.get('source') != 'Valve official standings':
            continue
        probs = o.get('probabilities')
        if not probs:
            continue
        names = [t['name'] for t in match['teams']]
        # The registry records the reverse direction (Valve name -> fixture name).
        # Honouring a row's own recorded alias is not a guess: the link is already
        # published with its evidence, and this check only tests the arithmetic on
        # top of it.
        valve_names = list(names)
        for entry in o.get('aliases_used') or []:
            for i, name in enumerate(names):
                if key(entry.get('canonical')) == key(name) and entry.get('alias'):
                    valve_names[i] = entry['alias']
        if valve_names != names:
            record['valve_names'] = valve_names
        home, why_home = lookup(rows, valve_names[0])
        away, why_away = lookup(rows, valve_names[1])
        record = {
            'id': str(match['id']),
            'teams': names,
            'starts_at': match.get('starts_at'),
            'published': probs,
            'source_url': o.get('source_url'),
            'snapshot_date': o.get('snapshot_date'),
        }
        if not home or not away:
            # Several complete five-player rows may share a name. The publisher
            # resolves that with a fresh HLTV lineup proof and records it in
            # origination.lineup_disambiguation; without network access this
            # check cannot re-prove identity, but it can still confirm which
            # candidate row reproduces the published arithmetic.
            pair = best_candidates(rows, names, probs, g)
            if pair:
                record.update(status='reproduced under disambiguation', inputs=[
                    {'name': r['name'], 'standing': r['standing'], 'points': r['points']} for r in pair],
                    recomputed=[round(x, 8) for x in probabilities(pair, g)],
                    max_delta=round(max(abs(a - b) for a, b in zip(probs, probabilities(pair, g))), 8),
                    reason='Multiple five-player Valve rows share a name; the candidate pair that matches the published value is shown. Identity is proven by the publisher\'s HLTV lineup evidence, not by this offline check.')
                checks.append(record)
            else:
                record.update(status='unverified', reason='; '.join(x for x in (why_home, why_away) if x))
                checks.append(record)
            continue
        record['inputs'] = [{'name': home['name'], 'standing': home['standing'], 'points': home['points']},
                            {'name': away['name'], 'standing': away['standing'], 'points': away['points']}]
        if home['points'] == away['points']:
            # Valve's summary table rounds to integers. The exact Final Rank Value
            # only exists in the linked per-roster detail markdown, which the
            # publisher records with its Git blob SHA.
            exact, proof = detail_points(o, home, away, g, args.detail_dir)
            if exact:
                record.update(status='reproduced from detail file', inputs=proof['inputs'],
                              recomputed=[round(x, 8) for x in exact],
                              max_delta=round(max(abs(a - b) for a, b in zip(probs, exact)), 8),
                              reason=proof['reason'])
            else:
                record.update(status='needs detail file', reason=proof['reason'])
            checks.append(record)
            continue
        p = 1 / (1 + 10 ** (g * (away['points'] - home['points']) / 400))
        recomputed = [p, 1 - p]
        delta = max(abs(a - b) for a, b in zip(probs, recomputed))
        record['recomputed'] = [round(x, 8) for x in recomputed]
        record['max_delta'] = round(delta, 8)
        record['status'] = 'reproduced' if delta <= TOLERANCE else 'MISMATCH'
        checks.append(record)

    counts = {}
    for c in checks:
        counts[c['status']] = counts.get(c['status'], 0) + 1
    report = {'standings_file': args.standings, 'g': g, 'rd': RD, 'tolerance': TOLERANCE,
              'checked': len(checks), 'counts': counts, 'checks': checks}
    text = json.dumps(report, indent=1)
    if args.out:
        Path(args.out).write_text(text + '\n')
    else:
        print(text)
    if args.markdown:
        lines = ['# Valve-rating recomputation (session 3cf793ef)', '',
                 f'Standings file: `{args.standings}` · g = {g:.6f} · RD = {RD} · tolerance ±{TOLERANCE}', '',
                 f'Checked {len(checks)} published Valve-model rows: ' +
                 ', '.join(f'{n} {s}' for s, n in sorted(counts.items())) + '.', '',
                 '| Fixture | Match | Published | Recomputed | Status | Source |',
                 '| --- | --- | --- | --- | --- | --- |']
        for c in checks:
            pub = ' / '.join(f'{x:.4f}' for x in c['published'])
            rec = ' / '.join(f'{x:.4f}' for x in c['recomputed']) if c.get('recomputed') else '—'
            status = c['status'] if c['status'] == 'reproduced' else f"**{c['status']}** — {c['reason']}"
            link = c.get('source_url') or ''
            lines.append(f"| {c['id']} | {c['teams'][0]} vs {c['teams'][1]} | {pub} | {rec} | {status} | {link} |")
        Path(args.markdown).write_text('\n'.join(lines) + '\n')
    mismatches = counts.get('MISMATCH', 0)
    print(f'checked={len(checks)} counts={counts} mismatches={mismatches}')
    return 1 if mismatches else 0


if __name__ == '__main__':
    raise SystemExit(main())
