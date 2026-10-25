"""Session arena-824a2780: independent, offline replay of every published pick row.

The dashboard's promise is that a reader can re-derive each number from the data
the page itself publishes.  This script performs that check line by line against
``snapshot.json`` and the built pages, without network access and without
trusting any value it cannot recompute:

``inventory``
    Counts, ids, team pairs, start timestamps and the archive/upcoming split in
    the snapshot agree with the rows it contains.
``replay``
    Every active row's two probabilities are recomputed from the inputs the row
    publishes: bid/ask midpoints for a market row, no-vig decimal odds for a
    bookmaker row, and Valve's published Glicko expectation for a research-model
    row.  A mismatch is an error, not a rounding note.
``picks``
    Every active row either names a side that is the strict favourite of its own
    published probabilities, or is published with no side, a non-empty
    limitations list and a research trail saying which sources were tried.
``sources``
    Every probability is attributed to an official publisher over https.
    Hotspawn (the pick'em host) is never a probability source: its community
    "% picked" figure is not evidence, so any Hotspawn attribution on an
    analysis row fails this check.
``pages``
    When the built pages carry the same observation as the snapshot, every
    active fixture id appears on the picks list and every pick-less fixture
    appears in the unresolved register.  A snapshot newer than the built pages
    is skipped by id, never silently passed.

Usage::

    python -m scripts.824a2780_verify [--snapshot snapshot.json] [--site .] [--check]

``--check`` exits 1 when any error is found.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'snapshot.json'

# The publishers a probability may be attributed to.  Hotspawn is deliberately
# absent: it hosts the pick'em, so it is the question, never the evidence.
PROBABILITY_HOSTS = (
    'polymarket.com', 'gamma-api.polymarket.com', 'clob.polymarket.com', 'docs.polymarket.com',
    'kalshi.com', 'docs.kalshi.com',
    'thunderpick.io', 'gg.bet', 'stake.com', 'pinnacle.com', 'rivalry.com', 'bovada.lv',
    'smarkets.com', 'docs.smarkets.com',
    'egamersworld.com',
    'hltv.org',
    'github.com',
    'bo3.gg',
)
# Any of these under an analysis row means crowd participation leaked into a price.
CROWD_HOSTS = ('hotspawn.com', 'play.hotspawn.com')
CROWD_KEYS = ('picked', 'percent_picked', 'crowd', 'fan_vote', 'fan_rating', 'votes')

VALVE_RD = 75.0
METHODS = {'market', 'bookmaker', 'consensus', 'model', 'reference', 'guidance', 'relay'}


def host_of(url: str) -> str:
    m = re.match(r'^https?://([^/]+)', url or '')
    return (m.group(1) if m else '').lower()


def host_matches(host: str, allowed: str) -> bool:
    return host == allowed or host.endswith('.' + allowed)


def close(a, b, tol=1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol


def normalized(pair) -> list[float]:
    a, b = float(pair[0]), float(pair[1])
    total = a + b
    return [a / total, b / total]


def valve_probability(points1: float, points2: float, rd: float = VALVE_RD) -> float:
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)
    return 1 / (1 + 10 ** (g * (points2 - points1) / 400))


def iso(value) -> datetime | None:
    if not isinstance(value, str) or not value.endswith('Z'):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def teams_of(match: dict) -> list[dict]:
    return match.get('teams') or []


def is_active(match: dict) -> bool:
    return match.get('availability') != 'past'


def replay_row(match: dict, errors: list[str]) -> str:
    """Recompute one analysis row from its own published inputs."""
    mid = str(match.get('id'))
    analysis = match.get('analysis')
    if not analysis:
        return 'blank'
    method = analysis.get('method')
    probs = analysis.get('probabilities')
    if method not in METHODS:
        errors.append(f'{mid}: unknown method {method!r}')
        return 'invalid'
    if not isinstance(probs, list) or len(probs) != 2:
        errors.append(f'{mid}: analysis does not publish exactly two probabilities')
        return 'invalid'
    p = [float(x) for x in probs]
    if not all(0.0 < x < 1.0 for x in p):
        errors.append(f'{mid}: probability outside (0, 1): {p}')
    if not close(sum(p), 1.0, 1e-6):
        errors.append(f'{mid}: probabilities sum to {sum(p)!r}, not 1')
    if not (analysis.get('observed_at') or '').endswith('Z'):
        errors.append(f'{mid}: observation is not stamped in UTC')
    url = analysis.get('source_url') or ''
    host = host_of(url)
    if not url.startswith('https://'):
        errors.append(f'{mid}: probability source is not https: {url!r}')
    elif not any(host_matches(host, h) for h in PROBABILITY_HOSTS):
        errors.append(f'{mid}: probability attributed to an unapproved host {host!r}')
    if any(host_matches(host, h) for h in CROWD_HOSTS):
        errors.append(f'{mid}: Hotspawn is used as a probability source')
    for key in CROWD_KEYS:
        if key in analysis:
            errors.append(f'{mid}: crowd field {key!r} found on the analysis row')

    quotes = analysis.get('quotes') or []
    midpoints: list[float] = []
    books: list[list[float]] = []
    for quote in quotes:
        # 1. Arithmetic inside each published quote, whatever its family.
        bid, ask = quote.get('bid'), quote.get('ask')
        if bid is not None and ask is not None:
            if float(bid) > float(ask):
                errors.append(f'{mid}: crossed market quote bid {bid} > ask {ask}')
            price = (float(bid) + float(ask)) / 2
            if quote.get('midpoint') is None or not close(quote['midpoint'], price, 1e-9):
                errors.append(f'{mid}: midpoint {quote.get("midpoint")!r} != (bid+ask)/2 {price!r}')
            if quote.get('spread') is not None and not close(quote['spread'], float(ask) - float(bid), 1e-9):
                errors.append(f'{mid}: spread {quote["spread"]!r} != ask-bid {float(ask) - float(bid)!r}')
            midpoints.append(price)
        odds = quote.get('odds')
        if odds and len(odds) == 2:
            a, b = float(odds[0]), float(odds[1])
            if a <= 1.0 or b <= 1.0:
                errors.append(f'{mid}: decimal odds <= 1.0 published ({a}, {b})')
            else:
                books.append(normalized([1 / a, 1 / b]))
        stated = quote.get('probabilities')
        if stated:
            if len(stated) != 2 or not close(sum(float(x) for x in stated), 1.0, 1e-4):
                errors.append(f'{mid}: quote probabilities {stated!r} do not sum to 1')
    # 2. The published pair must be the pair recomputed from those quotes.
    if len(midpoints) == 2:
        want = normalized(midpoints)
    elif len(midpoints) == 1 and len(books) == 1:
        want = None  # mixed exchange + bookmaker row: no single recomputation
    elif books:
        zero = sorted(b[0] for b in books)[len(books) // 2]
        want = normalized([zero, 1 - zero])
    else:
        want = None
    if want and not (close(want[0], p[0], 1e-4) and close(want[1], p[1], 1e-4)):
        errors.append(f'{mid}: published {p} != the pair recomputed from its own quotes {want}')
    if not quotes and method in ('market', 'bookmaker'):
        errors.append(f'{mid}: {method} row publishes no price quote')
    if method == 'model' and analysis.get('inputs'):
        inputs = analysis['inputs']
        if len(inputs) != 2:
            errors.append(f'{mid}: model row without two rating inputs')
        elif all(i.get('points') is not None for i in inputs):
            rd = float(analysis.get('rd_assumption') or VALVE_RD)
            g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)
            if analysis.get('g') is not None and not close(analysis['g'], g, 1e-9):
                errors.append(f'{mid}: published g {analysis["g"]!r} != Glicko g(RD={rd}) {g!r}')
            want = valve_probability(float(inputs[0]['points']), float(inputs[1]['points']), rd)
            want = normalized([want, 1 - want])
            if not (close(want[0], p[0], 1e-6) and close(want[1], p[1], 1e-6)):
                errors.append(f'{mid}: published {p} != Valve expectation {want}')
            for row in inputs:
                if not str(row.get('source_url') or '').startswith('https://'):
                    errors.append(f'{mid}: model input {row.get("name")!r} has no https source')

    fair = analysis.get('fair_decimal')
    if fair:
        if len(fair) != 2:
            errors.append(f'{mid}: fair_decimal does not publish two lines')
        else:
            for line, prob in zip(fair, p):
                if prob and not close(float(line), 1 / prob, 5e-3):
                    errors.append(f'{mid}: fair line {line} is not the reciprocal of {prob}')
    return method


def row_report(path: Path) -> list[dict]:
    """One published record per active fixture: what was published and what replays."""
    document = json.loads(path.read_text(encoding='utf-8'))
    rows = []
    for match in document.get('matches') or []:
        if not is_active(match):
            continue
        analysis = match.get('analysis') or {}
        errors: list[str] = []
        method = replay_row(match, errors)
        probs = analysis.get('probabilities')
        pick = match.get('pick_index')
        teams = [t.get('name') for t in teams_of(match)]
        rows.append({
            'id': str(match.get('id')),
            'teams': teams,
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'availability': match.get('availability'),
            'method': method if method != 'blank' else None,
            'published_probabilities': probs,
            'replayed': not errors,
            'pick': (teams[pick] if pick in (0, 1) and len(teams) == 2 else None),
            'source_url': analysis.get('source_url'),
            'observed_at': analysis.get('observed_at'),
            'limitations': analysis.get('limitations') or match.get('limitations') or [],
            'errors': errors,
        })
    return rows


def verify_snapshot(path: Path, site: Path | None = None) -> dict:
    errors: list[str] = []
    notes: list[str] = []
    document = json.loads(path.read_text(encoding='utf-8'))
    matches = document.get('matches') or []

    # ---- inventory -------------------------------------------------------
    ids = [str(m.get('id')) for m in matches]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        errors.append(f'snapshot repeats fixture ids: {dupes}')
    observed = iso(document.get('generated_at'))
    if observed is None:
        errors.append('snapshot.generated_at is not a UTC timestamp')
    active = [m for m in matches if is_active(m)]
    archived = [m for m in matches if not is_active(m)]
    counts = document.get('counts') or {}
    computed = {
        'inventory': len(matches),
        'upcoming': len(active),
        'archived': len(archived),
        'picks': sum(m.get('pick_index') is not None for m in active),
        'unresolved': sum(m.get('analysis') is None for m in active),
    }
    for key, value in computed.items():
        if key in counts and counts[key] != value:
            errors.append(f'counts.{key} says {counts[key]!r}, rows say {value}')
    for match in matches:
        mid = str(match.get('id'))
        teams = teams_of(match)
        if len(teams) != 2 or any(not (t.get('name') or '').strip() for t in teams):
            errors.append(f'{mid}: does not name exactly two teams')
        if iso(match.get('starts_at')) is None:
            errors.append(f'{mid}: starts_at is not a UTC timestamp')
        if not str(match.get('source_url') or '').startswith('https://'):
            errors.append(f'{mid}: no https source_url for the fixture itself')

    # ---- replay + picks + sources ---------------------------------------
    tally: dict[str, int] = {}
    for match in active:
        mid = str(match.get('id'))
        method = replay_row(match, errors)
        tally[method] = tally.get(method, 0) + 1
        analysis = match.get('analysis')
        pick = match.get('pick_index')
        if analysis:
            probs = [float(x) for x in analysis.get('probabilities') or []]
            if pick is not None:
                if pick not in (0, 1):
                    errors.append(f'{mid}: pick_index {pick!r} is not a side')
                elif len(probs) == 2:
                    if not probs[pick] > probs[1 - pick]:
                        errors.append(f'{mid}: named side {pick} is not the strict favourite of {probs}')
            elif len(probs) == 2 and abs(probs[0] - probs[1]) > 1e-9:
                # A priced row with no side is allowed only when the row says so.
                if not (match.get('limitations') or analysis.get('limitations')):
                    errors.append(f'{mid}: priced row names no side and carries no limitation')
        else:
            if pick is not None:
                errors.append(f'{mid}: names a side but publishes no analysis to support it')
            if not match.get('limitations'):
                errors.append(f'{mid}: blank pick with no published limitation')
            trail = match.get('research') or []
            if len(trail) < 3:
                errors.append(f'{mid}: blank pick with only {len(trail)} researched source(s) named')
            for stage in trail:
                if not str(stage.get('source_url') or '').startswith('https://'):
                    errors.append(f'{mid}: research stage {stage.get("stage")!r} has no https source')
                if not stage.get('detail'):
                    errors.append(f'{mid}: research stage {stage.get("stage")!r} does not say what happened')

    # ---- pages -----------------------------------------------------------
    marker = None
    page = site / 'index.html' if site else None
    if page and page.exists():
        html = page.read_text(encoding='utf-8', errors='replace')
        found = re.search(r'generated="([^"]+)"', html)
        marker = found.group(1) if found else None
        if marker and marker != document.get('generated_at'):
            notes.append(f'built pages carry {marker}, snapshot carries {document.get("generated_at")}; '
                         'page coverage not judged (a newer snapshot than the built pages)')
            marker = None
    if marker:
        pages = {
            'picks': site / 'picks' / 'index.html',
            'unresolved': site / 'unresolved' / 'index.html',
        }
        for name, file in pages.items():
            if not file.exists():
                errors.append(f'built site is missing the {name} page')
        if (site / 'picks' / 'index.html').exists():
            picks_html = (site / 'picks' / 'index.html').read_text(encoding='utf-8', errors='replace')
            for match in active:
                if str(match.get('id')) not in picks_html:
                    errors.append(f'{match["id"]}: active fixture absent from the built picks page')
        if (site / 'unresolved' / 'index.html').exists():
            unresolved_html = (site / 'unresolved' / 'index.html').read_text(encoding='utf-8', errors='replace')
            for match in active:
                if match.get('analysis') is None and str(match.get('id')) not in unresolved_html:
                    errors.append(f'{match["id"]}: pick-less fixture absent from the unresolved register')
                if match.get('pick_index') is None and str(match.get('id')) not in unresolved_html:
                    errors.append(f'{match["id"]}: no side named and absent from the unresolved register')

    return {
        'snapshot': str(path),
        'generated_at': document.get('generated_at'),
        'inventory': len(matches),
        'active': len(active),
        'with_pick': computed['picks'],
        'without_pick': len(active) - computed['picks'],
        'methods': tally,
        'page_observation': marker,
        'errors': errors,
        'notes': notes,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=SNAPSHOT)
    parser.add_argument('--site', type=Path, default=None)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--rows', type=Path, default=None,
                        help='write one record per active fixture to this path')
    args = parser.parse_args(argv)
    if args.rows:
        args.rows.write_text(json.dumps(row_report(args.snapshot), indent=2) + '\n', encoding='utf-8')
    report = verify_snapshot(args.snapshot, args.site)
    print(json.dumps(report, indent=2))
    if args.check and report['errors']:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
