"""Replay every number the deployed dashboard publishes (session 9e0e601d).

Why a second replay
-------------------
``scripts/0c034b94_verify.py`` replays the three methods the *featured* snapshot
carries (prediction-market midpoints, no-vig bookmaker odds and the Valve
research model).  The complete picks list on the site is a wider document: it
also publishes rows priced by a **median of independent money sources**
(``consensus``), by a single relayed or aggregated bookmaker price
(``bookmaker`` / ``reference``) and by the repository's own **results models**
(``network`` and ``form``).  On the 2026-10-25 14:32Z snapshot four of the
sixteen active fixtures are priced only by those methods, so a replay that stops
at the featured three leaves a quarter of the board unverified.

This module re-derives each published pair from the row's *own* evidence and
never copies a published probability back into the result:

* ``market``      - the two-sided order-book midpoints, proportionally normalised.
* ``bookmaker``   - ``(1/o_i) / sum(1/o)`` over the quoted decimal odds.
* ``consensus``   - the median of the contributing providers' first-side
                    probabilities, mirrored to the second side and normalised.
* ``reference``   - the no-vig conversion of the aggregated decimal odds.
* ``model`` (Valve) - Valve's published logistic expectation from the two
                    official points values and the row's own ``g``/RD.
* ``model`` (network) - ``1 / (1 + 10 ** ((p_b - p_a) / 400))`` from the two
                    published rating inputs (``network-bt-1``).
* ``model`` (form)    - the same expectation with the form model's RD rule
                    ``150 + 300 / sqrt(n)``, capped at 400, against the
                    published ``n_series``.

A row it cannot reproduce from published inputs is reported as **not replayed**
with the reason, never as a pass.  Every row, whatever its method, also has to
satisfy the structural invariants: two probabilities inside (0, 1) summing to 1,
``fair_decimal`` the reciprocal of each probability, a pick that is the higher
probability (and no pick on an exact tie), an https source link, a UTC
observation stamp, and no crowd/fan percentage anywhere in the evidence.

The render contract is checked from the built executive summary itself: the
in-site routes a phone needs (picks list, glance index, the three registers, the
unresolved page), the viewport meta, and one deep link per glance row.

CLI
---
    python -m scripts.9e0e601d_verify                      # replay the checked-in fixtures
    python -m scripts.9e0e601d_verify --site site/index.html --write
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
TOL = 1e-6
#: ``fair_decimal`` is published rounded to three decimals.
DECIMAL_TOL = 6e-4
#: Longest acceptable gap between the snapshot's own clock and "now".
MAX_AGE_HOURS = 8
#: Keys that would mean a crowd/fan percentage leaked into a published number.
FORBIDDEN_INPUT_KEYS = ('picked_percent', 'fan_vote', 'fan_votes', 'crowd',
                        'percent_picked', 'pick_percentage')
VALVE_RD = 75.0
#: Routes a phone reader must be able to reach from the executive summary.
REQUIRED_ROUTES = (
    ('picks list', './origination/#picks'),
    ('unresolved trails', './origination/#unresolved'),
    ('unresolved page', './unresolved/'),
    ('glance index', './#picks-at-a-glance'),
    ('unresolved register', './#unresolved-register'),
    ('no-line register', './#no-line-register'),
    ('fallback register', './#fallback-register'),
    ('flagged for review', './review/'),
    ('source coverage', './coverage/'),
)
REQUIRED_IDS = (
    'picks-at-a-glance', 'glance-list', 'unresolved-register',
    'no-line-register', 'fallback-register',
)
VIEWPORT = re.compile(r'<meta\s+name="viewport"[^>]*width=device-width', re.I)
GLANCE_ROW = re.compile(r'<li class="glance-row"([^>]*)>')
GLANCE_ID = re.compile(r'data-glance-id="(\d+)"')
UTC_STAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

def novig(odds: list) -> list:
    inverses = [1.0 / float(o) for o in odds]
    total = sum(inverses)
    return [x / total for x in inverses]


def normalise(pair: list) -> list:
    total = float(sum(pair))
    return [float(x) / total for x in pair]


def close(a, b, tol: float = TOL) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def valve_g(rd: float = VALVE_RD) -> float:
    return 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)


def valve_probability(points_a: float, points_b: float, rd: float = VALVE_RD) -> float:
    return 1 / (1 + 10 ** (valve_g(rd) * (float(points_b) - float(points_a)) / 400))


def network_probability(points_a: float, points_b: float) -> float:
    return 1 / (1 + 10 ** ((float(points_b) - float(points_a)) / 400))


def form_rd(n_series: float) -> float:
    return min(400.0, 150.0 + 300.0 / math.sqrt(max(1.0, float(n_series))))


def find_forbidden(value, path: str = '') -> list:
    hits = []
    if isinstance(value, dict):
        for key, item in value.items():
            where = f'{path}.{key}' if path else str(key)
            if str(key).casefold() in FORBIDDEN_INPUT_KEYS:
                hits.append(where)
            hits.extend(find_forbidden(item, where))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(find_forbidden(item, f'{path}[{index}]'))
    return hits


# ---------------------------------------------------------------------------
# Row replay
# ---------------------------------------------------------------------------

def _quotes(row: dict) -> list:
    return [q for q in (row.get('quotes') or []) if isinstance(q, dict)]


def _inputs(row: dict) -> list:
    return [i for i in (row.get('inputs') or []) if isinstance(i, dict)]


def replay_market(row: dict):
    quotes = _quotes(row)
    if len(quotes) != 2:
        return None, f'market row carries {len(quotes)} quote(s), expected 2'
    midpoints = []
    for quote in quotes:
        if quote.get('midpoint') is not None:
            midpoints.append(float(quote['midpoint']))
        elif quote.get('bid') is not None and quote.get('ask') is not None:
            midpoints.append((float(quote['bid']) + float(quote['ask'])) / 2)
        else:
            return None, 'market quote has no midpoint and no bid/ask pair'
    return normalise(midpoints), 'two-sided midpoints, normalised'


def _decimal_pair(quotes: list):
    """The two decimal prices, in side order, however the row stores them.

    An esportsbook row publishes one quote object holding both prices
    (``odds: [1.68, 2.05]``); an exchange row publishes one quote per side with
    a scalar price.  Both are accepted; anything else is refused rather than
    guessed, because an odds pair is the whole evidence for a no-vig number.
    """
    if len(quotes) == 1:
        odds = quotes[0].get('odds')
        if isinstance(odds, list) and len(odds) == 2:
            pair = odds
        else:
            pair = None
    elif len(quotes) == 2:
        pair = [q.get('odds') for q in quotes]
    else:
        pair = None
    if not isinstance(pair, list) or len(pair) != 2:
        return None
    if not all(isinstance(o, (int, float)) and not isinstance(o, bool) and o > 1 for o in pair):
        return None
    return [float(pair[0]), float(pair[1])]


def replay_bookmaker(row: dict):
    quotes = _quotes(row)
    odds = _decimal_pair(quotes)
    if odds is None:
        # A relayed price publishes probabilities rather than odds; without the
        # decimal pair there is nothing to convert, so it stays unreplayed.
        return None, (f'bookmaker row publishes no two-way decimal odds pair '
                      f'({len(quotes)} quote(s))')
    return novig(odds), 'inverse-odds, margin removed'


def replay_reference(row: dict):
    odds = _decimal_pair(_quotes(row))
    if odds is None:
        return None, 'aggregated reference quote publishes no two-way decimal odds pair'
    return novig(odds), 'aggregated decimal odds, margin removed'


def replay_consensus(row: dict):
    quotes = _quotes(row)
    probs = []
    for quote in quotes:
        pair = quote.get('probabilities')
        if not (isinstance(pair, list) and len(pair) == 2):
            return None, 'consensus quote without a two-way probability pair'
        probs.append(float(pair[0]))
    if not probs:
        return None, 'consensus row carries no provider quotes'
    ordered = sorted(probs)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return normalise([median, 1 - median]), f'median of {len(probs)} provider first-side probabilities'


def replay_valve(row: dict):
    inputs = _inputs(row)
    if len(inputs) != 2 or any(i.get('points') is None for i in inputs):
        return None, 'Valve model row does not publish both official points values'
    rd = row.get('rd_assumption', VALVE_RD)
    p = valve_probability(inputs[0]['points'], inputs[1]['points'], float(rd))
    g = row.get('g')
    if g is not None and not close(g, valve_g(float(rd)), 1e-9):
        return None, f'published g {g} is not Valve\'s g at RD {rd}'
    return [p, 1 - p], f'Valve logistic expectation, RD {rd}'


def replay_network(row: dict):
    inputs = _inputs(row)
    if len(inputs) != 2 or any(i.get('points') is None for i in inputs):
        return None, 'network model row does not publish both rating inputs'
    p = network_probability(inputs[0]['points'], inputs[1]['points'])
    return [p, 1 - p], 'network Bradley-Terry expectation'


def replay_form(row: dict):
    inputs = _inputs(row)
    if len(inputs) != 2 or any(i.get('points') is None for i in inputs):
        return None, 'form model row does not publish both rating inputs'
    # Each fitted side publishes its own sample count; Valve-rated sides keep
    # RD 75.  The expectation uses the larger of the two RDs, exactly as
    # ``scripts/form_model.estimate_fixture`` computes it.
    rds = [VALVE_RD]
    for side in inputs:
        fitted = side.get('fitted') if isinstance(side.get('fitted'), dict) else None
        n = (fitted or {}).get('n') if fitted else None
        if n is None and fitted:
            n = row.get('n_series')
        if n is not None:
            rds.append(form_rd(n))
        elif side.get('source') and 'fit' in str(side.get('source')).casefold():
            return None, 'form model row has a fitted side without its sample count'
    rd = max(rds)
    p = valve_probability(inputs[0]['points'], inputs[1]['points'], rd)
    return [p, 1 - p], f'form-model expectation, RD {round(rd, 3)}'


def replay_hltv_ranking(row: dict):
    inputs = _inputs(row)
    if len(inputs) != 2 or any(i.get('points') is None for i in inputs):
        return None, 'HLTV-ranking model row does not publish both points values'
    scale = row.get('points_scale') or 400.0
    if not close(scale, 400.0, 1e-9):
        return None, f'HLTV-ranking row declares an unexpected points scale {scale!r}'
    p = 1 / (1 + 10 ** ((float(inputs[1]['points']) - float(inputs[0]['points'])) / 400.0))
    return [p, 1 - p], 'HLTV world-ranking points on the 400 scale'


def model_variant(row: dict) -> str:
    """Which research model produced this row.

    Four models publish ``method: model`` and they are *not* interchangeable: the
    Valve and HLTV models differ only in scale, while the network and form
    models carry their own rating and RD rules.  The variant is read from the
    row's own declarations, never guessed from team names.
    """
    family = str(row.get('family') or '').casefold()
    if family in {'network', 'form'}:
        return family
    if str(row.get('model_version') or '') == 'network-bt-1':
        return 'network'
    source = ' '.join(str(row.get(key) or '') for key in ('provider', 'source', 'label')).casefold()
    if 'hltv' in source or row.get('points_scale') is not None:
        return 'hltv'
    if row.get('rd_assumption') is not None or row.get('g') is not None:
        return 'valve'
    if 'valve' in source:
        return 'valve'
    return ''


def replay_row(row: dict) -> dict:
    """Re-derive one published pair from the row's own evidence."""
    method = (row.get('method') or '').strip()
    if method == 'market':
        probs, detail = replay_market(row)
    elif method == 'bookmaker':
        probs, detail = replay_bookmaker(row)
    elif method == 'reference':
        probs, detail = replay_reference(row)
    elif method == 'consensus':
        probs, detail = replay_consensus(row)
    elif method == 'model':
        variant = model_variant(row)
        if variant == 'network':
            probs, detail = replay_network(row)
        elif variant == 'form':
            probs, detail = replay_form(row)
        elif variant == 'hltv':
            probs, detail = replay_hltv_ranking(row)
        elif variant == 'valve':
            probs, detail = replay_valve(row)
        else:
            return {'replayed': False, 'detail': 'model',
                    'reason': 'model row does not declare which research model produced it'}
    else:
        return {'replayed': False, 'reason': f'method {method or "(none)"} has no replay rule', 'detail': method}
    if probs is None:
        return {'replayed': False, 'reason': detail, 'detail': method}
    return {'replayed': True, 'probabilities': probs, 'detail': detail}


# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------

def row_violations(row: dict, published: list | None, pick_index, *, label: str) -> list:
    """Every check that must hold whatever produced the numbers."""
    problems = []
    if not (isinstance(published, list) and len(published) == 2):
        return [f'{label}: published probabilities are not a two-way pair']
    try:
        pair = [float(published[0]), float(published[1])]
    except (TypeError, ValueError):
        return [f'{label}: published probabilities are not numbers']
    if not all(0 < p < 1 for p in pair):
        problems.append(f'{label}: probability outside (0, 1): {pair}')
    if not close(sum(pair), 1.0):
        problems.append(f'{label}: probabilities sum to {sum(pair)!r}, not 1')
    fair = row.get('fair_decimal')
    if fair is not None:
        if not (isinstance(fair, list) and len(fair) == 2):
            problems.append(f'{label}: fair_decimal is not a pair')
        else:
            for p, d in zip(pair, fair):
                if p and not close(d, 1 / p, DECIMAL_TOL):
                    problems.append(f'{label}: fair_decimal {d} is not 1/{p}')
    expected = None
    if pair[0] > pair[1]:
        expected = 0
    elif pair[1] > pair[0]:
        expected = 1
    if pick_index != expected:
        problems.append(f'{label}: pick_index {pick_index} does not select the higher probability (expected {expected})')
    source = row.get('source_url') or row.get('featured_source_url')
    if not (isinstance(source, str) and source.startswith('https://')):
        problems.append(f'{label}: no https source link')
    stamp = row.get('observed_at') or row.get('timestamp')
    if stamp is not None and not UTC_STAMP.match(str(stamp)):
        problems.append(f'{label}: observation stamp {stamp!r} is not a UTC ISO-8601 second stamp')
    forbidden = find_forbidden(row)
    if forbidden:
        problems.append(f'{label}: crowd/fan input present at {forbidden[0]}')
    return problems


def replay_published(rows: list, *, id_key: str = 'id') -> dict:
    """Replay the numbers published on the complete picks list."""
    report = {'rows': 0, 'replayed': 0, 'not_replayed': [], 'violations': [], 'methods': {}}
    for row in rows:
        if not isinstance(row, dict):
            continue
        report['rows'] += 1
        ident = str(row.get(id_key) or row.get('match_id') or '?')
        origin = row.get('origination') if isinstance(row.get('origination'), dict) else row
        method = (origin.get('method') or 'none') + ('/' + origin['family'] if origin.get('family') else '')
        report['methods'][method] = report['methods'].get(method, 0) + 1
        published = origin.get('probabilities')
        pick = row.get('pick_index', origin.get('pick_index'))
        report['violations'].extend(row_violations(origin, published, pick, label=ident))
        outcome = replay_row(origin)
        if not outcome['replayed']:
            report['not_replayed'].append({'id': ident, 'method': method, 'reason': outcome['reason']})
            continue
        report['replayed'] += 1
        for index, (got, want) in enumerate(zip(outcome['probabilities'], published or [])):
            if not close(got, want, 2e-6):
                report['violations'].append(
                    f'{ident}: published {index} probability {want!r} != replayed {round(got, 8)!r} ({outcome["detail"]})')
    return report


# ---------------------------------------------------------------------------
# Inventory coverage
# ---------------------------------------------------------------------------

def open_rows(snapshot: dict) -> list:
    return [m for m in snapshot.get('matches') or []
            if isinstance(m, dict) and m.get('availability') in {'open', 'locked', 'unknown_lock'}]


def coverage(snapshot: dict, origination: dict) -> dict:
    """Every live fixture must resolve to a pick row or an explicit limitation."""
    rows = [m for m in (origination.get('matches') or []) if isinstance(m, dict)]
    by_id = {str(m.get('id')): m for m in rows}
    unpicked = []
    for match in open_rows(snapshot):
        ident = str(match.get('id'))
        row = by_id.get(ident)
        if row is None:
            unpicked.append({'id': ident, 'teams': [t.get('name') for t in match.get('teams') or []],
                             'reason': 'no row in the complete picks list'})
            continue
        if row.get('pick_index') is None:
            limitations = [str(x) for x in (row.get('limitations') or []) + (match.get('limitations') or [])]
            unpicked.append({'id': ident, 'teams': [t.get('name') for t in match.get('teams') or []],
                             'reason': 'no pick and no recorded limitation' if not limitations
                             else 'no pick; limitation: ' + limitations[0]})
    extra = sorted(set(by_id) - {str(m.get('id')) for m in open_rows(snapshot)})
    return {'open': len(open_rows(snapshot)), 'complete_rows': len(rows),
            'with_pick': sum(1 for r in rows if r.get('pick_index') is not None),
            'without_pick': unpicked, 'rows_outside_snapshot': extra}


# ---------------------------------------------------------------------------
# Rendered contract
# ---------------------------------------------------------------------------

def verify_site(index_html: str) -> dict:
    """The executive summary a phone actually loads."""
    problems = []
    if not VIEWPORT.search(index_html or ''):
        problems.append('executive summary has no width=device-width viewport')
    for label, href in REQUIRED_ROUTES:
        if f'href="{href}"' not in index_html:
            problems.append(f'no in-site route to the {label} ({href})')
    for ident in REQUIRED_IDS:
        if f'id="{ident}"' not in index_html:
            problems.append(f'missing section #{ident}')
    ids = GLANCE_ID.findall(index_html)
    deep_links = set(re.findall(r'href="\./origination/#match-(\d+)"', index_html))
    missing_detail = sorted(set(ids) - deep_links)
    if missing_detail:
        problems.append('glance rows without a deep link to their evidence: ' + ', '.join(missing_detail[:5]))
    if 'data-glance-starts=' not in index_html:
        problems.append('glance rows carry no scheduled start for the phone filters')
    return {'glance_rows': len(GLANCE_ROW.findall(index_html)), 'glance_ids': len(ids),
            'deep_links': len(deep_links), 'problems': problems}


def verify(snapshot: dict, origination: dict, index_html: str | None = None,
           *, now: datetime | None = None, max_age_hours: float = MAX_AGE_HOURS,
           coverage_asserted: bool = True) -> dict:
    report = {'snapshot_at': snapshot.get('generated_at'), 'problems': []}
    replayed = replay_published([m for m in (origination.get('matches') or []) if isinstance(m, dict)])
    report['replay'] = replayed
    featured = []
    for match in open_rows(snapshot):
        analysis = match.get('analysis')
        if isinstance(analysis, dict):
            featured.append(dict(analysis, id=str(match.get('id')),
                                 pick_index=match.get('pick_index')))
    report['featured_replay'] = replay_published(featured)
    report['coverage'] = coverage(snapshot, origination)
    if index_html is not None:
        report['site'] = verify_site(index_html)
        report['problems'].extend(report['site']['problems'])
    report['violations'] = report['replay']['violations'] + report['featured_replay']['violations']
    stamp = snapshot.get('generated_at')
    reference = now or datetime.now(UTC)
    try:
        generated = datetime.strptime(str(stamp), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)
        age = (reference - generated).total_seconds() / 3600
        report['age_hours'] = round(age, 2)
        if age > max_age_hours:
            report['problems'].append(
                f'snapshot is {age:.1f} h old; the 4-8 h freshness bound is exceeded')
        if age < -0.25:
            report['problems'].append(f'snapshot clock {stamp} is in the future of {reference.isoformat()}')
    except (TypeError, ValueError):
        report['problems'].append('snapshot has no parseable generated_at')
    report['coverage']['asserted'] = bool(coverage_asserted)
    if coverage_asserted:
        for gap in report['coverage']['without_pick']:
            report['problems'].append(f"live fixture {gap['id']} has no pick: {gap['reason']}")
    elif report['coverage']['without_pick']:
        # The two files are different observations, so a fixture missing from one
        # of them says nothing about the other.  Saying so is the honest output.
        report['problems'].append(
            f"coverage not asserted: {len(report['coverage']['without_pick'])} fixture(s) differ between "
            'the deployed snapshot and the deployed complete picks list, which are different observations')
    return report


def summarise(report: dict) -> str:
    lines = []
    replay = report.get('replay') or {}
    featured = report.get('featured_replay') or {}
    lines.append(f"Complete picks list: {replay.get('replayed', 0)}/{replay.get('rows', 0)} rows replayed, "
                 f"{len(replay.get('not_replayed') or [])} not replayed")
    lines.append(f"Featured snapshot: {featured.get('replayed', 0)}/{featured.get('rows', 0)} rows replayed, "
                 f"{len(featured.get('not_replayed') or [])} not replayed")
    cov = report.get('coverage') or {}
    lines.append(f"Coverage: {cov.get('open', 0)} live fixtures, {cov.get('with_pick', 0)} rows with a pick, "
                 f"{len(cov.get('without_pick') or [])} without one")
    if report.get('site'):
        site = report['site']
        lines.append(f"Executive summary: {site['glance_ids']} glance rows, {site['deep_links']} deep links, "
                     f"{len(site['problems'])} render problems")
    lines.append(f"Age: {report.get('age_hours')} h")
    lines.append(f"Violations: {len(report.get('violations') or [])}; problems: {len(report.get('problems') or [])}")
    return '\n'.join(lines)


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT / 'snapshot.json')
    parser.add_argument('--origination', type=Path, default=ROOT / 'data' / 'origination.json')
    parser.add_argument('--site', type=Path, default=None)
    parser.add_argument('--write', action='store_true',
                        help='write the report to data/research/9e0e601d/verification.json')
    parser.add_argument('--json', action='store_true', help='print the whole report as JSON')
    parser.add_argument('--max-age-hours', type=float, default=MAX_AGE_HOURS,
                        help='freshness bound; the checked-in fixtures are replayed with a large value')
    args = parser.parse_args(argv)
    snapshot = load(args.snapshot)
    origination = load(args.origination)
    index_html = args.site.read_text(encoding='utf-8') if args.site else None
    report = verify(snapshot, origination, index_html, max_age_hours=args.max_age_hours)
    if args.write:
        out = ROOT / 'data' / 'research' / '9e0e601d' / 'verification.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2) if args.json else summarise(report))
    return 1 if report['violations'] or report['problems'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
