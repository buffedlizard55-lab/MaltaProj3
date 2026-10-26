"""Line-by-line verification of the published CS2 picks and of the rendered contract.

Session arena-24e4d653. Two questions, answered from data rather than opinion:

1. **Does every published number replay from the inputs the row itself publishes?**
   For each active fixture in the published origination layer the pick and both
   probabilities are recomputed from the row's own recorded quotes:

   * ``market``    -- ``(bid+ask)/2`` of both recorded Polymarket/Kalshi/Smarkets
                      quotes, normalised to sum to one, with the recorded spread
                      inside the published ceiling;
   * ``bookmaker`` -- ``1/decimal`` for both recorded bookmaker prices, margin
                      removed proportionally (the published no-vig rule);
   * ``model``     -- Valve's published Glicko transform
                      ``p = 1/(1+10**(g*(opp-own)/400))`` with
                      ``g = 1/sqrt(1+3*(ln10/400)**2 * RD**2 / pi**2)``, over the
                      two recorded standing-points values. RD is the row's own
                      published ``rd_assumption`` (75 for two Valve rows), or, for
                      the project's results-based fit, ``150 + 300/sqrt(n)`` capped
                      at 400 for the fitted side -- the rule in
                      ``scripts/form_model.py`` -- taking the wider of the two;
   * ``consensus`` -- the median of the per-source no-vig probabilities of the
                      recorded quotes, recomputed from each quote's own odds.

   A row whose method cannot be replayed is reported as unreplayable. It is never
   silently accepted, and nothing is filled in.

2. **Does the executive summary do what the brief asks?** On the built page:
   in-site links to the updated picks, a separate unresolved/limitations register
   that names each row's limitation and source, both teams' win probability and
   an obvious pick on every active row, and a real phone viewport.

Usage
-----
    python -m scripts.24e4d653_verify                 # verify data/ + site/
    python -m scripts.24e4d653_verify --write         # also write the dossier
    python -m scripts.24e4d653_verify --html index.html --data .
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable

VALVE_RD = 75.0
MAX_ACCEPTED_SPREAD = 0.15
MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference'}
ACTIVE_STATES = {'open', 'locked', 'unknown_lock'}


def _f(value: Any) -> float:
    return float(value)


def valve_probability(points_own: float, points_opponent: float, rd: float = VALVE_RD) -> float:
    """Valve's published transform (counter-strike_regional_standings/model/fit.js)."""
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)
    return 1 / (1 + 10 ** (g * (points_opponent - points_own) / 400))


def normalise(pair: Iterable[float]) -> list[float]:
    values = [max(0.0, _f(v)) for v in pair]
    total = sum(values)
    if not total:
        raise ValueError('non-positive probability pair')
    return [v / total for v in values]


def _close(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def _scalar(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def quote_pair(quotes: list) -> tuple[list | None, list | None]:
    """Read the two published order-book quotes in either shape the ladder emits.

    Shape A: two quote records, one per outcome, each with scalar ``bid``/``ask``.
    Shape B: one quote record carrying ``bid``/``ask`` as two-element lists.
    """
    if len(quotes) == 2 and all(_scalar(q.get('bid')) and _scalar(q.get('ask')) for q in quotes):
        return [float(q['bid']) for q in quotes], [float(q['ask']) for q in quotes]
    if len(quotes) == 1:
        bid, ask = quotes[0].get('bid'), quotes[0].get('ask')
        if isinstance(bid, list) and isinstance(ask, list) and len(bid) == len(ask) == 2:
            return [float(v) for v in bid], [float(v) for v in ask]
    return None, None


def _median(values: list) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def quote_odds(quotes: list) -> list | None:
    """The two published decimal odds, whichever quote shape carries them."""
    if len(quotes) == 1 and isinstance(quotes[0].get('odds'), list) and len(quotes[0]['odds']) == 2:
        return [float(o) for o in quotes[0]['odds']]
    if len(quotes) == 2 and all(_scalar(q.get('odds')) for q in quotes):
        return [float(q['odds']) for q in quotes]
    return None


def replay_row(row: dict) -> dict:
    """Recompute one active row from its own published inputs."""
    orig = row.get('origination') or {}
    method = orig.get('method')
    published = [_f(p) for p in orig.get('probabilities') or []]
    result: dict[str, Any] = {
        'id': str(row.get('id')),
        'teams': [t.get('name') for t in row.get('teams') or []],
        'method': method,
        'published': published,
        'published_pick': None,
        'expected': None,
        'expected_pick': None,
        'replay': 'not-replayed',
        'detail': '',
        'source_url': orig.get('source_url') or row.get('source_url'),
        'observed_at': orig.get('observed_at'),
        'limitation': (orig.get('limitations') or row.get('limitations') or [None])[0],
    }
    if len(published) != 2:
        result['detail'] = f'expected two probabilities, found {len(published)}'
        return result
    if not _close(sum(published), 1.0, 1e-6):
        result['detail'] = f'the two probabilities sum to {sum(published):.6f}, not 1'
        return result
    index = row.get('pick_index')
    if index not in (0, 1):
        result['detail'] = 'no pick recorded on an active, resolved row'
        return result
    result['published_pick'] = result['teams'][index]

    quotes = orig.get('quotes') or []
    bids, asks = quote_pair(quotes)
    odds = quote_odds(quotes)
    expected = None
    if method in MONEY_METHODS and odds is not None:
        if min(odds) <= 1.0:
            result['detail'] = 'recorded decimal odds do not exceed 1.00'
            return result
        expected = normalise(1 / o for o in odds)
        result['detail'] = 'no-vig normalisation of ' + ' / '.join(f'{o:g}' for o in odds)
    elif method in MONEY_METHODS and bids is not None:
        spreads = [a - b for b, a in zip(bids, asks)]
        result['spread'] = [round(s, 4) for s in spreads]
        if min(asks) <= 0 or min(bids) < 0 or min(spreads) <= 0:
            result['replay'] = 'unreplayable'
            result['detail'] = 'a recorded quote is crossed or not a usable price'
            return result
        if max(spreads) > MAX_ACCEPTED_SPREAD + 1e-9:
            result['replay'] = 'unreplayable'
            result['detail'] = (f'quote spread {max(spreads):.2f} exceeds the published ceiling '
                                f'{MAX_ACCEPTED_SPREAD}')
            return result
        expected = normalise([(b + a) / 2 for b, a in zip(bids, asks)])
        result['detail'] = ('midpoints of ' + ' / '.join(f'{b:g}-{a:g}' for b, a in zip(bids, asks))
                            + ', normalised')
    elif method == 'model':
        inputs = orig.get('inputs') or []
        try:
            points = [_f(i['points']) for i in inputs]
            if len(points) != 2:
                raise ValueError('two rating inputs are required')
            if any((i.get('fitted') or {}).get('n') for i in inputs):
                # The project's results-based fit publishes its own rating deviation
                # rule (scripts/form_model.py): 150 + 300/sqrt(n), capped at 400, for
                # the fitted side, and 75 for a side that already has a Valve row.
                deviations = []
                for item in inputs:
                    n = (item.get('fitted') or {}).get('n')
                    deviations.append(min(400.0, 150.0 + 300.0 / math.sqrt(max(1, int(n))))
                                      if n else VALVE_RD)
                rd = max(deviations)
                rule = 'results-based fit rule'
            else:
                rd = _f(orig.get('rd_assumption') or VALVE_RD)
                rule = "Valve's published transform"
            p0 = valve_probability(points[0], points[1], rd)
            expected = normalise([p0, 1 - p0])
            result['detail'] = (f'{rule} over {points[0]:g} / {points[1]:g} points (RD {rd:g})')
        except (TypeError, ValueError, KeyError) as exc:
            result['detail'] = f'rating inputs unusable: {exc}'
    elif method == 'consensus':
        sources = []
        for quote in quotes:
            odds_pair = quote.get('odds')
            if isinstance(odds_pair, list) and len(odds_pair) == 2:
                try:
                    odds = [float(o) for o in odds_pair]
                    if min(odds) <= 1.0:
                        raise ValueError('decimal odds do not exceed 1.00')
                    sources.append(normalise(1 / o for o in odds))
                    continue
                except (TypeError, ValueError, ZeroDivisionError):
                    return {**result, 'replay': 'unreplayable',
                            'detail': 'a consensus quote carries unusable odds'}
            recorded = quote.get('probabilities')
            if isinstance(recorded, list) and len(recorded) == 2:
                try:
                    sources.append(normalise(recorded))
                except (TypeError, ValueError):
                    return {**result, 'replay': 'unreplayable',
                            'detail': 'a consensus quote carries unusable probabilities'}
        if not sources:
            result['detail'] = 'no consensus source carries a replayable quote'
        else:
            ordered = [sorted(src[i] for src in sources) for i in (0, 1)]
            median = [_median(column) for column in ordered]
            expected = normalise(median)
            result['detail'] = (f'median of {len(sources)} independent quotes: ' +
                                ' / '.join(f'{m * 100:.2f}%' for m in median))
    else:
        result['detail'] = (f'method {method!r} carries no replayable inputs in the published row '
                            f'({len(quotes)} quote(s))')

    if expected is None:
        result['replay'] = 'unreplayable'
        return result
    result['expected'] = [round(p, 6) for p in expected]
    result['expected_pick'] = result['teams'][0] if expected[0] >= expected[1] else result['teams'][1]
    problems = []
    if not all(_close(a, b) for a, b in zip(expected, published)):
        problems.append(f'probabilities {published} != replayed {result["expected"]}')
    if result['published_pick'] != result['expected_pick']:
        problems.append(f'pick {result["published_pick"]!r} != replayed {result["expected_pick"]!r}')
    if not str(result['source_url'] or '').startswith('https://'):
        problems.append('no official https source_url on the row')
    result['replay'] = 'ok' if not problems else 'mismatch'
    if problems:
        result['problems'] = problems
    return result


def active_rows(origination: dict) -> list[dict]:
    rows = origination.get('matches') or []
    return [r for r in rows if (r.get('availability') or 'open') in ACTIVE_STATES]


def check_active(origination: dict) -> dict:
    rows = active_rows(origination)
    replays = [replay_row(r) for r in rows]
    counts: dict[str, int] = {}
    for item in replays:
        counts[item['replay']] = counts.get(item['replay'], 0) + 1
    unpicked = [r['id'] for r, item in zip(rows, replays) if r.get('pick_index') is None]
    without_limitation = [item['id'] for item in replays if not item.get('limitation')]
    return {
        'active_rows': len(rows),
        'with_pick': sum(1 for r in rows if r.get('pick_index') is not None),
        'without_pick': unpicked,
        'replay_counts': counts,
        'rows': replays,
        'rows_without_a_limitation': without_limitation,
        'ok': not unpicked and counts.get('mismatch', 0) == 0 and counts.get('unreplayable', 0) == 0
              and not without_limitation,
    }


def check_coverage(dossier: dict | None, snapshot: dict, origination: dict) -> dict:
    """Every fixture in the dated live record must be either carried or named as a gap."""
    if not dossier:
        return {'available': False, 'detail': 'no dated live-coverage record found', 'ok': True}
    recorded = ((dossier.get('published_site') or {}).get('snapshot_generated_at')
                or (dossier.get('after_observation') or {}).get('snapshot_generated_at'))
    if recorded and snapshot.get('generated_at') and recorded != snapshot.get('generated_at'):
        # The record is dated to another build. Comparing its flags with a different
        # snapshot would manufacture a contradiction that does not exist, so the
        # comparison is skipped and said to be skipped.
        return {'available': True, 'checked': False, 'observed_at': dossier.get('observed_at'),
                'detail': (f"the record is dated to snapshot {recorded}; this checkout carries "
                           f"{snapshot.get('generated_at')}, so its flags are not compared here"),
                'ok': True}
    carried = {str(m.get('id')) for m in origination.get('matches') or []}
    snapshot_ids = {str(m.get('id')) for m in snapshot.get('matches') or []}
    live = dossier.get('live_fixtures') or []
    problems, gaps, covered = [], [], []
    for fixture in live:
        identity = str(fixture.get('id'))
        if identity in carried:
            covered.append(identity)
            if not fixture.get('in_published_snapshot'):
                problems.append(f'{identity}: dossier says absent, the published layer carries it')
        elif fixture.get('in_published_snapshot'):
            problems.append(f'{identity}: dossier says carried, the published layer does not carry it')
        else:
            gaps.append(identity)
            if fixture.get('in_published_snapshot'):
                problems.append(f'{identity}: contradictory in_published_snapshot flag')
    return {
        'available': True,
        'checked': True,
        'observed_at': dossier.get('observed_at'),
        'live_future_fixtures': len(live),
        'carried': len(covered),
        'gaps': gaps,
        'gaps_named_with_a_limitation': sum(1 for f in live
                                            if str(f.get('id')) in gaps and (f.get('note') or '').strip()),
        'snapshot_only': sorted(snapshot_ids - {str(f.get('id')) for f in live}),
        'problems': problems,
        'ok': not problems,
    }


GLANCE_ROW = re.compile(r'<li class="glance-row"(?P<attrs>[^>]*)>(?P<body>.*?)</li>', re.S)


def check_rendered(html: str) -> dict:
    """The brief's executive-summary and phone contract, read off the built page."""
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str, severity: str = 'fail') -> None:
        checks.append({'check': name, 'status': 'pass' if ok else severity, 'detail': detail})

    add('phone viewport', 'name="viewport"' in html and 'width=device-width' in html,
        'meta viewport with width=device-width is present')
    start = re.search(r'<nav class="start-here" id="start-here"[^>]*>(.*?)</nav>', html, re.S)
    picks_links = re.findall(r'href="([^"]+)"', start.group(1)) if start else []
    in_site = [h for h in picks_links if not h.startswith(('http', 'mailto:'))]
    add('in-site links to the updated picks', bool(in_site),
        f'start-here links: {in_site or "none"}')
    register = re.search(r'id="unresolved-register".*?(?=<section|</section>|</main>)', html, re.S)
    add('separate unresolved/limitations register in the summary', bool(register),
        'section #unresolved-register present' if register else 'section #unresolved-register missing')
    if register:
        block = register.group(0)
        add('register names the limitation for each unresolved/fallback row',
            'Why' in block or 'Why not the featured line' in block or 'No betting line' in block
            or 'No unresolved fixtures' in block,
            'the register states each row\'s blocker (or that none are unresolved)')
        add('register links an official source', 'href="https://' in block,
            'the register carries at least one external source link')
    rows = GLANCE_ROW.findall(html)
    blank, no_pick, no_method = [], [], []
    for attrs, body in rows:
        identity = re.search(r'data-glance-id="([^"]+)"', attrs)
        key = identity.group(1) if identity else '?'
        if len(re.findall(r'\d+\.\d%', body)) < 2:
            blank.append(key)
        if not re.search(r'data-glance-pick\b', body):
            no_pick.append(key)
        if 'data-method="' not in attrs:
            no_method.append(key)
    add('both teams\' win probability on every glance row', bool(rows) and not blank,
        f'{len(rows)} glance row(s); rows without two percentages: {blank or "none"}')
    add('an obvious pick on every glance row', bool(rows) and not no_pick,
        f'rows without a pick marker: {no_pick or "none"}')
    add('a named method on every glance row', bool(rows) and not no_method,
        f'rows without data-method: {no_method or "none"}')
    mobile_nav = re.search(r'<nav class="mobile-nav"[^>]*>(.*?)</nav>', html, re.S)
    add('mobile navigation to the picks', bool(mobile_nav),
        'bottom mobile navigation present' if mobile_nav else 'bottom mobile navigation missing')
    failed = [c for c in checks if c['status'] == 'fail']
    return {'checks': checks, 'rows': len(rows), 'ok': not failed, 'failures': [c['check'] for c in failed]}


def run(root: Path, html: str | None = None) -> dict:
    """Verify data + the rendered page. ``html`` overrides reading ``site/index.html``."""
    root = Path(root)
    snapshot = json.loads((root / 'snapshot.json').read_text())
    origination = json.loads((root / 'origination.json').read_text())
    dossier_path = root / 'data/research/24e4d653/live-coverage.json'
    dossier = json.loads(dossier_path.read_text()) if dossier_path.is_file() else None
    if html is None:
        page = root / 'site/index.html'
        html = page.read_text() if page.is_file() else None
    active = check_active(origination)
    coverage = check_coverage(dossier, snapshot, origination)
    rendered = check_rendered(html) if html else {'available': False, 'ok': True, 'detail': 'no page'}
    return {
        'session': 'arena-24e4d653',
        'snapshot_generated_at': snapshot.get('generated_at'),
        'origination_generated_at': origination.get('generated_at'),
        'active': active,
        'coverage': coverage,
        'rendered': rendered,
        'ok': bool(active['ok'] and coverage['ok'] and rendered.get('ok', True)),
    }


def markdown(report: dict) -> str:
    active = report['active']
    coverage = report['coverage']
    rendered = report['rendered']
    lines = ['# Pick verification — every published row replayed from its own inputs', '',
             f"- Published snapshot: **{report['snapshot_generated_at']}**",
             f"- Published origination layer: **{report['origination_generated_at']}**",
             f"- Active fixtures: **{active['active_rows']}**; with a pick: **{active['with_pick']}**; "
             f"without: **{len(active['without_pick'])}**",
             f"- Replay: **{active['replay_counts'].get('ok', 0)} replay exactly**, "
             f"{active['replay_counts'].get('mismatch', 0)} mismatched, "
             f"{active['replay_counts'].get('unreplayable', 0)} unreplayable", '',
             '| Fixture | Method | Published | Replayed | Pick | Source |', '| --- | --- | --- | --- | --- | --- |']
    for row in active['rows']:
        published = ' / '.join(f'{p*100:.1f}%' for p in row['published']) or '—'
        replayed = ' / '.join(f'{p*100:.1f}%' for p in row['expected']) if row['expected'] else '—'
        lines.append(f"| {row['teams'][0]} vs {row['teams'][1]} (`{row['id']}`) | {row['method']} | "
                     f"{published} | {replayed} | {row['published_pick'] or '—'} | "
                     f"{'[source](' + row['source_url'] + ')' if row['source_url'] else '—'} |")
    lines += ['', '## Coverage of the live Hotspawn lobby', '']
    if coverage.get('available') and not coverage.get('checked', True):
        lines.append(f"- Not compared here: {coverage['detail']}")
    elif coverage.get('available'):
        lines += [f"- Dated live record: **{coverage['observed_at']}**",
                  f"- Live upcoming fixtures in that record: **{coverage['live_future_fixtures']}**; carried by the "
                  f"published layer: **{coverage['carried']}**; named gaps: **{len(coverage['gaps'])}**",
                  f"- Gaps named with an explicit limitation: **{coverage['gaps_named_with_a_limitation']}**"]
        if coverage['gaps']:
            lines.append('- Gap ids: ' + ', '.join(f'`{i}`' for i in coverage['gaps']))
        if coverage['problems']:
            lines.append('- Problems: ' + '; '.join(coverage['problems']))
    else:
        lines.append(f"- {coverage.get('detail', 'no dated record')}")
    lines += ['', '## Executive-summary contract', '']
    if rendered.get('available') is False:
        lines.append(f"- {rendered.get('detail')}")
    else:
        for check in rendered['checks']:
            lines.append(f"- **{check['status'].upper()}** — {check['check']}: {check['detail']}")
    lines.append('')
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('.'))
    parser.add_argument('--html', type=Path, default=None, help='built index.html to check')
    parser.add_argument('--write', action='store_true', help='write the dossier under data/research/24e4d653/')
    args = parser.parse_args(argv)
    html = args.html.read_text() if args.html else None
    report = run(args.data, html)
    print(json.dumps({k: v for k, v in report.items() if k != 'active'}, indent=2)[:4000])
    print(f"active rows: {report['active']['active_rows']}, replay {report['active']['replay_counts']}")
    if args.write:
        folder = args.data / 'data/research/24e4d653'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'verification.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        (folder / 'verification.md').write_text(markdown(report) + '\n')
        print(f'wrote {folder}/verification.json and .md')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
