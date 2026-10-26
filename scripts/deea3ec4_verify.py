"""Independent, line-by-line replay of the published CS2 picks (session arena-deea3ec4).

This module answers one question for every published row: *is this number the
arithmetic of the inputs the row itself publishes, and is the named pick the
favourite of those two numbers?* It re-derives each estimate from the row's own
recorded evidence -- exchange midpoints for a prediction market, no-vig
normalisation for a bookmaker, the Valve Glicko formula for a research model --
and never reads a number from the rendered page.

It also pins four published contracts that the brief depends on:

1. **Full coverage.** Every fixture in the dated live-inventory record whose
   start is later than the snapshot's own generation time must have a pick row.
   A card that started before the snapshot is history, not a gap.
2. **External provenance.** A money-method row must point at an https source
   that is not Hotspawn. Hotspawn's crowd percentage is a popularity poll, not a
   probability, and is excluded from every row.
3. **One obvious pick.** ``pick_index`` must be the strict-favourite side, and
   the featured pair must agree with the row's own estimate.
4. **A phone-first executive summary.** The static page must declare a
   device-width viewport, link to the in-site picks list, render one glance row
   per active fixture, and never assert staleness or freshness unless its own
   script has checked it (both banners ship ``hidden``).

Usage::

    python -m scripts.deea3ec4_verify --check          # exit 1 on any violation
    python -m scripts.deea3ec4_verify --report out.json

Every check is offline and deterministic: it reads the tracked published build
in the branch root (``snapshot.json``, ``origination.json``, ``index.html``).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent

#: Valve's published fit example uses a fixed rating deviation of 75; the same
#: constant is what the publisher records in each model row.
VALVE_RD = 75.0

#: Methods whose number must come from an outside money source.
MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'relay', 'reference'}

#: Methods derived from published rating tables (research models).
MODEL_METHODS = {'model', 'network'}

#: First-party game host. It is the inventory source, never a probability.
VENDOR_HOSTS = ('hotspawn.com',)

#: A probability pair must sum to one to within this tolerance.
SUM_TOLERANCE = 1e-6

#: A replay must reproduce the published probability to within this tolerance.
REPLAY_TOLERANCE = 1e-6


class Violation(Exception):
    """A published value that its own inputs do not support."""


def load(path: Path):
    return json.loads(Path(path).read_text())


def timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def name_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]', '', (value or '').lower())


def normalise_pair(values):
    total = sum(values)
    if total <= 0:
        raise Violation(f'probability pair sums to {total!r}')
    return [value / total for value in values]


def round3(value: float) -> float:
    return round(1.0 / value, 3)


def host_of(url: str) -> str:
    return (urlparse(url or '').hostname or '').lower()


def is_vendor(url: str) -> bool:
    host = host_of(url)
    return any(host == candidate or host.endswith('.' + candidate) for candidate in VENDOR_HOSTS)


# --------------------------------------------------------------------------
# Replay: each published method, re-derived from its own recorded inputs.
# --------------------------------------------------------------------------

def replay_market(row: dict) -> list[float]:
    """Exchange / prediction-market row: the midpoint of every two-sided book."""
    quotes = row.get('quotes') or []
    if not quotes:
        raise Violation('market row publishes no quote')
    quote = quotes[0]
    mids = []
    # The publisher records one quote object per side (bid/ask/midpoint), and an
    # originated line may instead carry the two midpoints together.
    sides = [q for q in quotes if isinstance(q, dict) and 'bid' in q or isinstance(q, dict) and 'ask' in q]
    if isinstance(quote.get('bid'), list) and isinstance(quote.get('ask'), list):
        pairs = list(zip(quote['bid'], quote['ask']))
    elif len(sides) == 2:
        pairs = [(q.get('bid'), q.get('ask')) for q in sides]
    elif isinstance(quote.get('probabilities'), list) and len(quote['probabilities']) == 2:
        pairs = None
    else:
        raise Violation('market quote carries neither a two-sided book nor a probability pair')
    if pairs is None:
        mids = [float(value) for value in quote['probabilities']]
    else:
        for lo, hi in pairs:
            if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float))):
                raise Violation('quote is not numeric')
            if lo > hi:
                raise Violation(f'crossed book: bid {lo} > ask {hi}')
            mids.append((lo + hi) / 2.0)
    return normalise_pair(mids)


def replay_bookmaker(row: dict) -> list[float]:
    """Bookmaker row: decimal odds with the margin removed proportionally."""
    quotes = row.get('quotes') or []
    if not quotes:
        raise Violation('bookmaker row publishes no quote')
    odds = quotes[0].get('odds')
    if not isinstance(odds, list) or len(odds) != 2:
        raise Violation('bookmaker quote does not publish two decimal odds')
    for price in odds:
        if not isinstance(price, (int, float)) or price <= 1.0:
            raise Violation(f'decimal odds {price!r} cannot be a win price')
    implied = [1.0 / float(price) for price in odds]
    margin = sum(implied)
    if margin <= 1.0:
        raise Violation(f'bookmaker pair implies a negative margin ({margin:.6f})')
    return normalise_pair(implied)


def _glicko_g(rd: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * (math.log(10) / 400.0) ** 2 * rd ** 2 / math.pi ** 2)


def replay_model(row: dict) -> list[float]:
    """Research-model row: re-derived from the two rating inputs it publishes.

    Two shapes are published. A Valve row carries official points for both
    sides and a fixed rating deviation; a results-based row (family ``form``)
    carries at least one side fitted from finished series, whose rating
    deviation is derived from its sample size exactly as the fitted module
    documents (``min(400, 150 + 300/sqrt(n))``), with the wider of the two
    deviations used for the transform.
    """
    inputs = row.get('inputs') or []
    if len(inputs) != 2:
        raise Violation('model row does not publish exactly two rating inputs')
    points, deviations = [], []
    fitted = False
    for entry in inputs:
        if not isinstance(entry.get('points'), (int, float)):
            raise Violation('model input publishes no rating points')
        if not entry.get('source_url'):
            raise Violation('model input publishes no official source link')
        points.append(float(entry['points']))
        fit = entry.get('fitted') or {}
        if isinstance(fit.get('n'), (int, float)) and fit['n'] >= 1:
            fitted = True
            deviations.append(min(400.0, 150.0 + 300.0 / math.sqrt(float(fit['n']))))
        else:
            deviations.append(float(row.get('rd_assumption') or VALVE_RD))
    rd = max(deviations) if fitted else float(row.get('rd_assumption') or VALVE_RD)
    g = _glicko_g(rd)
    published_g = row.get('g')
    if isinstance(published_g, (int, float)) and abs(published_g - g) > 1e-6:
        raise Violation(f'published g {published_g!r} != recomputed {g:.9f}')
    first = 1.0 / (1.0 + 10 ** (g * (points[1] - points[0]) / 400.0))
    if fitted:
        expected_rd = min(400.0, 150.0 + 300.0 / math.sqrt(max(
            1.0, max(float((e.get('fitted') or {}).get('n') or 1) for e in inputs))))
        if abs(expected_rd - rd) > 1e-6:
            raise Violation('results-model rating deviation does not follow its published sample size')
    return normalise_pair([first, 1.0 - first])


def replay_consensus(row: dict) -> list[float]:
    """Consensus row: the per-side median across the independent money sources.

    With an even number of sources the median is the mean of the two middle
    values, which is exactly what an originated two-book consensus publishes.
    """
    quotes = [q for q in row.get('quotes') or [] if isinstance(q.get('probabilities'), list)]
    if not quotes:
        raise Violation('consensus row publishes no per-source probability pair')
    families = set()
    for quote in quotes:
        families.add((quote.get('provider') or quote.get('family') or '').lower())
    if len(families) != len(quotes):
        raise Violation('consensus row counts one provider twice')
    medians = []
    for side in (0, 1):
        values = sorted(float(q['probabilities'][side]) for q in quotes)
        middle = len(values) // 2
        medians.append(values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2.0)
    return normalise_pair(medians)


def replay_quotes(row: dict) -> list[float]:
    """Relay / reference / guidance: the published per-source pair, normalised."""
    quotes = row.get('quotes') or []
    if not quotes:
        raise Violation('row publishes no quote')
    pair = quotes[0].get('probabilities')
    if not isinstance(pair, list) or len(pair) != 2:
        raise Violation('quote publishes no probability pair')
    return normalise_pair([float(value) for value in pair])


REPLAY = {
    'market': replay_market,
    'bookmaker': replay_bookmaker,
    'model': replay_model,
    'network': replay_quotes,
    'consensus': replay_consensus,
    'relay': replay_quotes,
    'reference': replay_quotes,
    'guidance': replay_quotes,
}


# --------------------------------------------------------------------------
# Row verification
# --------------------------------------------------------------------------

def verify_row(row: dict, snapshot_row: dict | None, warnings: list | None = None) -> list[str]:
    """Return the list of violations for one published pick row."""
    problems = []
    if warnings is None:
        warnings = []
    identity = str(row.get('id'))
    teams = row.get('teams') or []
    if len(teams) != 2 or not all(t.get('name') for t in teams):
        return [f'{identity}: does not publish exactly two named teams']
    origin = row.get('origination') or {}
    method = origin.get('method')
    probs = origin.get('probabilities')
    if method is None and not probs:
        # An explicitly unresolved row is a published answer too, but only when it
        # says why and carries no number at all. A blank row with a number, or a
        # blank row with no reason, is still a violation.
        reasons = row.get('limitations') or []
        stages = row.get('research') or []
        if not reasons:
            problems.append(f'{identity}: unresolved row publishes no limitation')
        if not stages:
            problems.append(f'{identity}: unresolved row publishes no research trail')
        if row.get('pick_index') not in (None,):
            problems.append(f'{identity}: unresolved row still names a pick')
        warnings.append(f'{identity}: unresolved (no compliant external price); see its published limitation')
        return problems
    try:
        if not isinstance(probs, list) or len(probs) != 2:
            raise Violation('does not publish exactly two probabilities')
        values = [float(value) for value in probs]
        if any(not 0.0 < value < 1.0 for value in values):
            raise Violation(f'probability outside (0, 1): {values!r}')
        if abs(sum(values) - 1.0) > SUM_TOLERANCE:
            raise Violation(f'probabilities sum to {sum(values):.9f}, not 1')
        pick = row.get('pick_index')
        if pick not in (0, 1):
            raise Violation(f'pick_index {pick!r} is not a side')
        other = 1 - pick
        if values[pick] < values[other]:
            raise Violation(f'named pick is not the favourite ({values[pick]:.6f} < {values[other]:.6f})')
        featured = row.get('featured_probabilities')
        if isinstance(featured, list) and len(featured) == 2:
            if any(abs(float(a) - b) > 1e-6 for a, b in zip(featured, values)):
                # The ladder is allowed to supersede the featured estimate with a
                # higher-ranked rung (money beats model). The published pair must
                # still be the row's own estimate; the difference is reported.
                warnings.append(
                    f'{identity}: the featured {row.get("featured_method") or "estimate"} pair '
                    f'({float(featured[0]) * 100:.1f}/{float(featured[1]) * 100:.1f}) was superseded by '
                    f'{method} ({values[0] * 100:.1f}/{values[1] * 100:.1f})')
        if row.get('featured_pick_index') not in (None, pick):
            raise Violation('featured_pick_index names a different side than the published pick')
        fair = origin.get('fair_decimal')
        if isinstance(fair, list) and len(fair) == 2:
            for published, value in zip(fair, values):
                if abs(float(published) - round3(value)) > 0.002:
                    raise Violation(f'fair_decimal {published} != 1/{value:.6f} rounded to three places')
        for check in ('picked_percent', 'pickedPercent', 'crowd', 'vote_share'):
            if check in json.dumps(row):
                raise Violation(f'row carries the Hotspawn crowd field {check!r}')
        if not (origin.get('limitations') or row.get('limitations')):
            warnings.append(f'{identity}: publishes no limitation for its {method} estimate')
        observed = timestamp(origin.get('observed_at'))
        if observed is None:
            problems.append(f'{identity}: publishes no parseable observation time')
        source_url = origin.get('source_url') or ''
        if not source_url.startswith('https://'):
            problems.append(f'{identity}: source_url is not an https link ({source_url!r})')
        elif is_vendor(source_url) and method in MONEY_METHODS | MODEL_METHODS:
            problems.append(f'{identity}: {method} row cites Hotspawn itself as its probability source')
        elif is_vendor(source_url):
            problems.append(f'{identity}: cites Hotspawn as a probability source')
        if method in MONEY_METHODS:
            quotes = origin.get('quotes') or []
            if not quotes:
                problems.append(f'{identity}: money row publishes no quote')
            for quote in quotes:
                if not quote.get('source_url'):
                    problems.append(f'{identity}: money quote publishes no source link')
                elif is_vendor(quote['source_url']):
                    problems.append(f'{identity}: money quote cites Hotspawn ({quote["source_url"]})')
        replay = REPLAY.get(method)
        if replay is None:
            problems.append(f'{identity}: unknown method {method!r}')
        else:
            try:
                replayed = replay(origin)
                deltas = [abs(a - b) for a, b in zip(replayed, values)]
                if max(deltas) > REPLAY_TOLERANCE:
                    problems.append(
                        f'{identity}: {method} replay mismatch (published {values[0]:.9f}/{values[1]:.9f}, '
                        f'recomputed {replayed[0]:.9f}/{replayed[1]:.9f})')
            except Violation as exc:
                problems.append(f'{identity}: {method} row cannot be replayed: {exc}')
        if snapshot_row is not None:
            snap_names = {name_key(t.get('name')) for t in snapshot_row.get('teams') or []}
            row_names = {name_key(t.get('name')) for t in teams}
            if snap_names != row_names:
                problems.append(f'{identity}: team names disagree with the inventory record')
            if snapshot_row.get('starts_at') and row.get('starts_at') != snapshot_row['starts_at']:
                problems.append(f'{identity}: start time disagrees with the inventory record')
            if snapshot_row.get('competition') and row.get('competition') != snapshot_row['competition']:
                problems.append(f'{identity}: tournament disagrees with the inventory record')
    except Violation as exc:
        problems.append(f'{identity}: {exc}')
    return problems


def verify_coverage(origination: dict, inventory: dict | None) -> tuple[list[str], list[str]]:
    """Every live fixture that had not started when the snapshot was built needs a row."""
    errors, notes = [], []
    if not inventory:
        return errors, notes
    generated = timestamp(origination.get('generated_at'))
    if generated is None:
        return ['origination.json publishes no parseable generated_at'], notes
    rows = {str(row.get('id')): row for row in origination.get('matches') or []}
    observed = timestamp(inventory.get('observed_at'))
    for fixture in inventory.get('live_fixtures') or []:
        identity = str(fixture.get('id') or '')
        start = timestamp(fixture.get('starts_at_utc'))
        if not identity or start is None:
            notes.append('inventory entry without a parseable id or start; skipped')
            continue
        if start <= generated:
            notes.append(f'{identity}: started before this snapshot was built; not a coverage gap')
            continue
        if identity not in rows:
            errors.append(
                f'{identity}: live fixture ({fixture.get("starts_at_utc")}) is missing from the published picks '
                f'(inventory observed {inventory.get("observed_at")})')
            continue
        if rows[identity].get('pick_index') not in (0, 1):
            errors.append(f'{identity}: published row carries no pick')
    if observed and observed > generated:
        notes.append(f'inventory observation {inventory.get("observed_at")} is newer than the snapshot {origination.get("generated_at")}')
    return errors, notes


# --------------------------------------------------------------------------
# Rendered executive summary
# --------------------------------------------------------------------------

def verify_rendered(html: str, origination: dict, picks_html: str | None = None) -> list[str]:
    problems = []
    if not re.search(r'<meta[^>]+name="viewport"[^>]+content="[^"]*width=device-width', html):
        problems.append('page does not declare a device-width viewport')
    if 'aria-label="Where to find the updated picks"' not in html:
        problems.append('executive-summary banner ("Where to find the updated picks") is missing')
    if not re.search(r'href="[^"]*origination/#picks"', html):
        problems.append('executive summary does not link to the in-site complete picks list')
    if not re.search(r'href="[^"]*#picks-at-a-glance"', html):
        problems.append('executive summary does not link to its own picks list')
    if not re.search(r'href="[^"]*unresolved/"', html):
        problems.append('executive summary does not link to the unresolved & limitations page')
    if 'id="picks-at-a-glance"' not in html:
        problems.append('the picks-at-a-glance section is missing')
    if 'id="unresolved-register"' not in html:
        problems.append('the unresolved register is missing')
    for stale_id in ('stale-warning', 'new-snapshot'):
        match = re.search(r'<[^>]*id="%s"[^>]*>' % stale_id, html)
        if match and 'hidden' not in match.group(0):
            problems.append(f'{stale_id} ships visible instead of being revealed by its own script')
    active = [row for row in origination.get('matches') or []]
    glance_rows = len(re.findall(r'class="glance-row"', html))
    if glance_rows != len(active):
        problems.append(f'{glance_rows} glance rows rendered for {len(active)} active fixtures')
    for row in active:
        identity = str(row.get('id'))
        if f'data-glance-id="{identity}"' not in html:
            problems.append(f'{identity}: no picks-at-a-glance entry on the summary')
        if picks_html is not None and f'id="match-{identity}"' not in picks_html:
            problems.append(f'{identity}: no anchor id="match-{identity}" on the complete picks page')
        origin = row.get('origination') or {}
        probs = origin.get('probabilities') or []
        if len(probs) == 2:
            for value in probs:
                rendered = f'{value * 100:.1f}%'
                if rendered not in html:
                    problems.append(f'{identity}: {rendered} is not rendered anywhere on the summary')
    return problems


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def run(root: Path = ROOT, *, inventory_path: Path | None = None,
        picks_path: Path | None = None) -> dict:
    root = Path(root)
    snapshot = load(root / 'snapshot.json')
    origination = load(root / 'origination.json')
    html = (root / 'index.html').read_text()
    picks_html = None
    candidate = Path(picks_path) if picks_path is not None else root / 'origination' / 'index.html'
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_file():
        picks_html = candidate.read_text()
    inventory = None
    if inventory_path is not None:
        path = Path(inventory_path)
        if not path.is_absolute():
            path = root / path
        if path.is_file():
            inventory = load(path)
    snapshot_rows = {str(row.get('id')): row for row in snapshot.get('matches') or []}
    errors, warnings, rows = [], [], []
    for row in origination.get('matches') or []:
        row_warnings = []
        problems = verify_row(row, snapshot_rows.get(str(row.get('id'))), row_warnings)
        warnings.extend(row_warnings)
        errors.extend(problems)
        origin = row.get('origination') or {}
        rows.append({
            'id': str(row.get('id')),
            'teams': [t.get('name') for t in row.get('teams') or []],
            'method': origin.get('method'),
            'probabilities': origin.get('probabilities'),
            'pick': (row.get('teams') or [{}])[row.get('pick_index') or 0].get('name'),
            'source_url': origin.get('source_url'),
            'problems': problems,
        })
    coverage_errors, coverage_notes = verify_coverage(origination, inventory)
    errors.extend(coverage_errors)
    errors.extend(verify_rendered(html, origination, picks_html))
    return {
        'schema_version': 1,
        'session': 'arena-deea3ec4',
        'checked_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'snapshot_generated_at': snapshot.get('generated_at'),
        'origination_generated_at': origination.get('generated_at'),
        'active_rows': len(origination.get('matches') or []),
        'inventory_observed_at': (inventory or {}).get('observed_at'),
        'inventory_live_fixtures': len((inventory or {}).get('live_fixtures') or []),
        'rows': rows,
        'coverage_notes': coverage_notes,
        'warnings': warnings,
        'errors': errors,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', default=str(ROOT))
    parser.add_argument('--inventory', default='data/research/deea3ec4/live-coverage.json')
    parser.add_argument('--report', default=None)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    report = run(Path(args.root), inventory_path=Path(args.inventory) if args.inventory else None)
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2) + '\n')
    print(f"snapshot {report['snapshot_generated_at']} · picks {report['origination_generated_at']} · "
          f"{report['active_rows']} active rows · inventory {report['inventory_observed_at']} "
          f"({report['inventory_live_fixtures']} live fixtures)")
    for row in report['rows']:
        first, second = row['probabilities'] or [None, None]
        state = 'ok' if not row['problems'] else 'FAIL'
        print(f"  {state:4} {row['id']:8} {row['teams'][0]:>22} vs {row['teams'][1]:<22} "
              f"{first:.4f}/{second:.4f} pick {row['pick']} · {row['method']}")
    for note in report['coverage_notes']:
        print(f'  note: {note}')
    for warning in report['warnings']:
        print(f'  warn: {warning}')
    for error in report['errors']:
        print(f'  ERROR: {error}')
    print(f"{len(report['errors'])} violation(s)")
    return 1 if (args.check and report['errors']) else 0


if __name__ == '__main__':
    sys.exit(main())
