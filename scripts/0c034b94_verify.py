"""Independent replay of the published snapshot (session 0c034b94).

The brief is explicit: every table row must be checkable against an official
source, and a value that cannot be confirmed stays blank and is flagged.  This
module therefore re-derives, from the evidence the snapshot itself carries, the
numbers the dashboard publishes - it never reads a published probability and
copies it back.

What is replayed, and from what
-------------------------------
* **Valve research model** (`method == "model"`, source "Valve official
  standings"): the two published probabilities are recomputed from the two
  official points values in `analysis.inputs` with Valve's own `fit.js`
  expectation (`g = 1 / sqrt(1 + 3*(ln10/400)^2*RD^2/pi^2)`, `p = 1/(1+10^(g*delta/400))`).
* **Prediction market** (`method == "market"`): the published pair must equal the
  two-sided order-book midpoints, proportionally normalised, from `analysis.quotes`.
* **Bookmaker** (`method == "bookmaker"`): the published pair must equal the
  no-vig conversion `(1/o_i) / sum(1/o)` of the quoted decimal odds.
* Every row, whatever its method: two probabilities inside (0, 1) that sum to 1
  within 1e-6, `fair_decimal` equal to the reciprocal of each probability, a
  `pick_index` that selects the higher probability (and no pick at all when the
  two are exactly equal), a UTC observation stamp, an https source link, and no
  crowd/fan percentage anywhere in the analysis.

Anything it cannot replay is reported with the reason instead of being assumed
correct, so a future method shows up as "not replayed" rather than passing
silently.

CLI
---
    python -m scripts.0c034b94_verify                 # verify snapshot.json
    python -m scripts.0c034b94_verify --write         # also write the dossier JSON
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'snapshot.json'
FIXTURES_EVIDENCE = ROOT / 'data' / 'evidence' / 'hotspawn-fixtures.json'
OUT = ROOT / 'data' / 'research' / '0c034b94'
VALVE_RD = 75
TOL = 1e-6
#: Keys that would mean a crowd/fan percentage leaked into a published number.
FORBIDDEN_INPUT_KEYS = ('picked_percent', 'fan_vote', 'fan_votes', 'crowd')


def valve_g(rd: float = VALVE_RD) -> float:
    return 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)


def valve_probability(points_a: float, points_b: float, rd: float = VALVE_RD) -> float:
    g = valve_g(rd)
    return 1 / (1 + 10 ** (g * (points_b - points_a) / 400))


def novig(odds: list) -> list:
    inverses = [1 / o for o in odds]
    total = sum(inverses)
    return [x / total for x in inverses]


def normalise(pair: list) -> list:
    total = sum(pair)
    return [x / total for x in pair]


def close(a, b, tol=TOL) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def find_forbidden(value, path='') -> list:
    """Any crowd/fan key inside an analysis object invalidates the row."""
    hits = []
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_INPUT_KEYS:
                hits.append(path + '/' + str(key))
            hits.extend(find_forbidden(item, path + '/' + str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(find_forbidden(item, path + '[' + str(index) + ']'))
    return hits


def replay_analysis(analysis: dict) -> tuple[str, str]:
    """Return (status, detail). `replayed` means the numbers were re-derived."""
    method = analysis.get('method')
    quotes = analysis.get('quotes') or []
    probs = analysis.get('probabilities') or []
    if method == 'model':
        inputs = analysis.get('inputs') or []
        if len(inputs) == 2 and all(isinstance(i.get('points'), (int, float)) for i in inputs):
            expected = valve_probability(inputs[0]['points'], inputs[1]['points'],
                                        analysis.get('rd_assumption') or VALVE_RD)
            if not close(probs[0], expected):
                return 'mismatch', (f"Valve replay gives {expected:.8f} for "
                                    f"{inputs[0].get('name')} but the snapshot publishes {probs[0]}")
            return 'replayed', (f"Valve fit.js expectation from official points "
                                f"{inputs[0]['points']:.0f} vs {inputs[1]['points']:.0f} "
                                f"(RD {analysis.get('rd_assumption') or VALVE_RD})")
        return 'not replayed', 'model row carries no two official points inputs'
    if method == 'market':
        mids = [q.get('midpoint') for q in quotes]
        if len(mids) == 2 and all(isinstance(m, (int, float)) for m in mids):
            expected = normalise(mids)
            if not all(close(a, b) for a, b in zip(probs, expected)):
                return 'mismatch', f'order-book midpoints {mids} normalise to {expected}, snapshot publishes {probs}'
            return 'replayed', f'two-sided midpoints {mids} normalised'
        return 'not replayed', 'market row carries no two-sided midpoint pair'
    if method == 'bookmaker':
        odds = [q.get('odds') for q in quotes]
        if len(odds) == 1 and isinstance(odds[0], list) and len(odds[0]) == 2:
            expected = novig(odds[0])
            if not all(close(a, b) for a, b in zip(probs, expected)):
                return 'mismatch', f'decimal odds {odds[0]} no-vig to {expected}, snapshot publishes {probs}'
            return 'replayed', f'no-vig conversion of {odds[0][0]} / {odds[0][1]}'
        return 'not replayed', 'bookmaker row does not carry exactly one two-way decimal quote'
    return 'not replayed', f'method {method!r} has no replay rule in this verifier'


def verify(snapshot: dict) -> dict:
    findings = []
    rows = []
    matches = snapshot.get('matches') or []
    open_rows = [m for m in matches if m.get('availability') != 'past']
    for match in open_rows:
        mid = str(match.get('id'))
        analysis = match.get('analysis')
        problems = []
        if not analysis:
            rows.append({'id': mid, 'method': None, 'status': 'no featured analysis',
                         'detail': 'carried by the researched complete-picks layer or listed as unresolved',
                         'limitations': match.get('limitations') or [],
                         'research_stages': len(match.get('research') or [])})
            if not match.get('limitations'):
                problems.append('no analysis and no limitation text')
            for stage in match.get('research') or []:
                if not str(stage.get('source_url', '')).startswith('https://'):
                    problems.append('research stage without an https source link')
            findings.extend(f'{mid}: {p}' for p in problems)
            continue
        probs = analysis.get('probabilities') or []
        if len(probs) != 2:
            problems.append(f'expected two probabilities, found {len(probs)}')
        else:
            if not all(isinstance(p, (int, float)) and 0 < p < 1 for p in probs):
                problems.append(f'probabilities outside (0, 1): {probs}')
            if not close(sum(probs), 1.0):
                problems.append(f'probabilities sum to {sum(probs)!r}, not 1')
            fair = analysis.get('fair_decimal') or []
            if len(fair) == 2:
                for p, d in zip(probs, fair):
                    if not close(d, round(1 / p, 3), 6e-4):
                        problems.append(f'fair decimal {d} is not 1/{p:.6f} = {round(1/p, 3)}')
            pick = match.get('pick_index')
            if abs(probs[0] - probs[1]) > 1e-9:
                if pick != (0 if probs[0] > probs[1] else 1):
                    problems.append(f'pick_index {pick} is not the higher probability side')
            elif pick is not None:
                problems.append('exactly even probabilities must not name a side')
        if not str(analysis.get('observed_at') or '').endswith('Z'):
            problems.append('analysis observation is not stamped in UTC')
        if not str(analysis.get('source_url', '')).startswith('https://'):
            problems.append('analysis source_url is not https')
        leaked = find_forbidden(analysis)
        if leaked:
            problems.append('crowd/fan input key present: ' + ', '.join(leaked))
        status, detail = replay_analysis(analysis)
        if status == 'mismatch':
            problems.append(detail)
        rows.append({'id': mid, 'method': analysis.get('method'),
                     'probabilities': probs, 'pick_index': match.get('pick_index'),
                     'status': status, 'detail': detail,
                     'source_url': analysis.get('source_url'),
                     'observed_at': analysis.get('observed_at'),
                     'limitations': analysis.get('limitations') or match.get('limitations') or []})
        findings.extend(f'{mid}: {p}' for p in problems)
    # Inventory: every future scheduled record in the committed evidence must be
    # in the snapshot, so a collected match cannot silently lose its row.
    evidence_ids, evidence_missing = [], []
    if FIXTURES_EVIDENCE.exists():
        try:
            records = json.loads(FIXTURES_EVIDENCE.read_text())
        except ValueError:
            records = []
        know = {str(m.get('id')) for m in matches}
        reference = datetime.now(UTC)
        for item in records if isinstance(records, list) else []:
            raw = item.get('scheduled_start_time')
            try:
                start = datetime.fromtimestamp(float(raw) / 1000, UTC) if raw else None
            except (TypeError, ValueError):
                start = None
            if start is None or start <= reference:
                continue
            evidence_ids.append(str(item.get('id')))
            if str(item.get('id')) not in know:
                evidence_missing.append(str(item.get('id')))
    return {
        'session': 'arena-0c034b94',
        'verified_at': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'snapshot_generated_at': snapshot.get('generated_at'),
        'snapshot_observed_at': snapshot.get('inventory_observed_at'),
        'snapshot_counts': snapshot.get('counts'),
        'open_rows': len(open_rows),
        'replayed': sum(1 for r in rows if r['status'] == 'replayed'),
        'not_replayed': [r['id'] + ': ' + r['detail'] for r in rows if r['status'] == 'not replayed'],
        'without_featured_analysis': [r['id'] for r in rows if r['status'] == 'no featured analysis'],
        'with_pick': sum(1 for row in open_rows if row.get('pick_index') is not None),
        'inventory_evidence_ids': len(evidence_ids),
        'inventory_evidence_missing_from_snapshot': evidence_missing,
        'violations': findings,
        'rows': rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=SNAPSHOT)
    parser.add_argument('--write', action='store_true', help='write data/research/0c034b94/verification.json')
    parser.add_argument('--check', action='store_true', help='exit 1 when a violation is found')
    args = parser.parse_args(argv)
    snapshot = json.loads(args.snapshot.read_text())
    report = verify(snapshot)
    lines = ['# Independent replay of the published snapshot', '',
             f"Snapshot generated {report['snapshot_generated_at']} "
             f"(inventory observed {report['snapshot_observed_at']}).", '',
             f"- open fixtures: **{report['open_rows']}**",
             f"- rows with a pick: **{report['with_pick']}**",
             f"- probabilities re-derived from their own evidence: **{report['replayed']}**"]
    for item in report['not_replayed']:
        lines.append(f'- not replayed: {item}')
    for item in report['without_featured_analysis']:
        lines.append(f'- no featured analysis (researched layer or unresolved register): {item}')
    lines.append(f"- violations: **{len(report['violations'])}**")
    for item in report['violations']:
        lines.append(f'  - {item}')
    if report['inventory_evidence_missing_from_snapshot']:
        lines.append(f"- committed fixture evidence not in the snapshot: "
                     f"{', '.join(report['inventory_evidence_missing_from_snapshot'])}")
    text = '\n'.join(lines) + '\n'
    print(text)
    if args.write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        (OUT / 'verification.md').write_text(text)
    if args.check and report['violations']:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
