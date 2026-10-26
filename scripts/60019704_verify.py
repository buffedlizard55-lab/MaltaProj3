"""Session arena-60019704: independent, offline replay of the deployed build.

The deployed snapshot (``snapshot.json``, ``generated_at`` 2026-10-25T23:03:48Z``) is the
published dashboard input.  This script re-derives, line by line and without network access,
every number that snapshot claims, and cross-checks the published pages and this session's
research dossier against it:

``inventory``
    Declared counts agree with the rows the file actually carries; ids are unique; the
    open/past split follows the start timestamps; declared evidence files exist; the
    refresh/stale cadence is 4/8 hours as promised.
``replay``
    Every open row with an analysis has its two probabilities recomputed from the inputs
    the row itself publishes: bid/ask midpoints for a market row (with the spread ceiling
    enforced on both quotes), proportional no-vig normalisation for a bookmaker row, and
    Valve's published fixed-RD Glicko expectation for a model row.  A mismatch is an
    error, not a rounding note.  Every priced row must have a strict favourite.
``unresolved``
    Every open row without an analysis publishes a non-empty limitations list and a
    multi-stage research trail; the one such row (1082792) must state the Valve
    identity reason that the official standings file actually contains.
``sources``
    Every probability is attributed to an official publisher over https.  Hotspawn (the
    pick'em host) is never a probability source, and no crowd field leaks into an
    analysis row.
``pages``
    The deployed pages carry the same observations: both the landing page and the picks
    page reference the snapshot, and every open fixture id appears on both.
``dossier``
    This session's research dossier (``data/research/60019704/research.json``) covers
    exactly the fixtures the deployed build leaves unpicked: the unresolved open row
    plus the nine live lobby fixtures the snapshot does not contain.

Usage::

    python -m scripts.60019704_verify [--snapshot snapshot.json] [--site .] [--check]

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
DOSSIER = ROOT / 'data/research/60019704/research.json'

# The publishers a probability may be attributed to.  Hotspawn is deliberately
# absent: it hosts the pick'em, so it is the question, never the evidence.
PROBABILITY_HOSTS = (
    'polymarket.com', 'gamma-api.polymarket.com', 'clob.polymarket.com',
    'thunderpick.io', 'smarkets.com', 'egamersworld.com',
    'hltv.org', 'github.com', 'bo3.gg', 'valvesoftware.com',
)
CROWD_HOSTS = ('hotspawn.com', 'play.hotspawn.com')
CROWD_KEYS = ('picked', 'percent_picked', 'crowd', 'fan_vote', 'fan_rating', 'votes')

MAX_SPREAD = 0.15          # Collector's market-rung spread ceiling.
VALVE_RD = 75.0            # Fixed-RD assumption in Valve's published model/fit.js.
UNRESOLVED_ID = '1082792'  # HOTU vs The Huns, the deployed build's only open pick-less row.
DEPLOYED_AT = '2026-10-25T23:03:48Z'


def host_of(url: str) -> str:
    m = re.match(r'^https?://([^/]+)', url or '')
    return (m.group(1) if m else '').lower()


def close(a, b, tol=1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol


def valve_expectation(points0: float, points1: float, rd: float = VALVE_RD) -> tuple[float, float]:
    """Valve's published fixed-RD Glicko expectation (scripts/originate.py model_estimate)."""
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)
    p = 1 / (1 + 10 ** (g * (points1 - points0) / 400))
    return p, 1 - p


def iter_crowd_leaks(node, path: str = 'analysis'):
    """Yield (path, key, value) for any crowd field nested inside an analysis row."""
    if isinstance(node, dict):
        for k, v in node.items():
            here = f'{path}.{k}'
            if k.lower() in CROWD_KEYS or any(h in str(v) and k == 'source_url' and h in CROWD_HOSTS for h in CROWD_HOSTS):
                yield here, k, v
            yield from iter_crowd_leaks(v, here)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_crowd_leaks(v, f'{path}[{i}]')


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks = 0

    def check(self, ok: bool, message: str) -> bool:
        self.checks += 1
        if not ok:
            self.errors.append(message)
        return ok

    def result(self) -> dict:
        return {'session': 'arena-60019704', 'checks': self.checks,
                'errors': self.errors, 'ok': not self.errors}


def verify(snapshot_path: Path, site: Path) -> dict:
    r = Report()
    snap = json.loads(snapshot_path.read_text(encoding='utf-8'))

    # ---------------------------------------------------------------- inventory
    matches = snap.get('matches') or []
    r.check(snap.get('generated_at') == DEPLOYED_AT,
            f"generated_at {snap.get('generated_at')!r} is not the deployed {DEPLOYED_AT!r}")
    r.check(snap.get('refresh_interval_hours') == 4 and snap.get('stale_after_hours') == 8,
            'refresh cadence is not the promised 4h/8h window')
    ids = [str(m.get('id')) for m in matches]
    r.check(len(ids) == len(set(ids)), 'duplicate fixture ids in the snapshot')
    counts = snap.get('counts') or {}
    r.check(counts.get('inventory') == len(matches),
            f"counts.inventory {counts.get('inventory')} != {len(matches)} rows")
    open_rows = [m for m in matches if m.get('availability') == 'open']
    past_rows = [m for m in matches if m.get('availability') == 'past']
    r.check(counts.get('upcoming') == len(open_rows),
            f"counts.upcoming {counts.get('upcoming')} != {len(open_rows)} open rows")
    r.check(counts.get('archived') == len(past_rows),
            f"counts.archived {counts.get('archived')} != {len(past_rows)} past rows")
    r.check(all(m.get('availability') in ('open', 'past') for m in matches),
            'availability outside the open/past split')
    gen = snap.get('generated_at')
    for m in open_rows:
        r.check(bool(m.get('starts_at')) and m['starts_at'] > gen,
                f"open row {m.get('id')} does not start after generated_at")
        ev = m.get('evidence')
        r.check(not ev or (ROOT / ev).exists(), f"row {m.get('id')} cites missing evidence file {ev}")

    priced = [m for m in open_rows if m.get('analysis')]
    unresolved = [m for m in open_rows if not m.get('analysis')]
    by_method: dict[str, int] = {}
    for m in priced:
        by_method[m['analysis'].get('method')] = by_method.get(m['analysis'].get('method'), 0) + 1
    for key in ('market', 'bookmaker', 'model'):
        r.check(counts.get(key) == by_method.get(key, 0),
                f"counts.{key} {counts.get(key)} != {by_method.get(key, 0)} replayed rows")
    r.check(counts.get('unresolved') == len(unresolved),
            f"counts.unresolved {counts.get('unresolved')} != {len(unresolved)} unresolved rows")
    r.check(counts.get('picks') == len(priced),
            f"counts.picks {counts.get('picks')} != {len(priced)} priced rows")

    # ------------------------------------------------------------------- replay
    for m in priced:
        a = m['analysis']
        mid, probs = str(m['id']), a.get('probabilities') or []
        names = [t['name'] for t in m.get('teams') or []]
        r.check(len(probs) == 2 and all(isinstance(p, (int, float)) for p in probs),
                f'{mid}: probabilities are not a numeric pair')
        if len(probs) != 2:
            continue
        method = a.get('method')
        if method == 'market':
            quotes = a.get('quotes') or []
            r.check(len(quotes) == 2, f'{mid}: market row without two order-book quotes')
            for i, q in enumerate(quotes):
                r.check(close((q['bid'] + q['ask']) / 2, q.get('midpoint')),
                        f'{mid}: quote {i} midpoint is not (bid+ask)/2')
                r.check(close(q['ask'] - q['bid'], q.get('spread')),
                        f'{mid}: quote {i} spread is not ask-bid')
                r.check(q['ask'] - q['bid'] <= MAX_SPREAD + 1e-9,
                        f'{mid}: quote {i} spread {q["ask"] - q["bid"]:.2f} breaches the {MAX_SPREAD} ceiling')
                r.check(close(q.get('midpoint'), probs[i]),
                        f'{mid}: probability {i} {probs[i]} != quote midpoint {q.get("midpoint")}')
        elif method == 'bookmaker':
            quotes = a.get('quotes') or []
            r.check(len(quotes) >= 1, f'{mid}: bookmaker row without a quote')
            for q in quotes:
                odds = q.get('odds') or []
                r.check(len(odds) == 2 and all(1 < float(o) for o in odds),
                        f'{mid}: bookmaker odds are not a >1 pair')
                if len(odds) == 2:
                    inv = [1 / float(o) for o in odds]
                    s = sum(inv)
                    for i in (0, 1):
                        r.check(close(inv[i] / s, probs[i]),
                                f'{mid}: no-vig probability {i} {probs[i]} != {inv[i] / s}')
        elif method == 'model':
            inputs = a.get('inputs') or []
            r.check(len(inputs) == 2, f'{mid}: model row without two Valve inputs')
            if len(inputs) == 2:
                rd = float(a.get('rd_assumption') or VALVE_RD)
                p0, p1 = valve_expectation(inputs[0]['points'], inputs[1]['points'], rd)
                r.check(close(p0, probs[0]) and close(p1, probs[1]),
                        f'{mid}: Valve expectation [{p0:.8f}, {p1:.8f}] != published {probs}')
                r.check(a.get('g') is None or close(a['g'], 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)),
                        f'{mid}: published g does not match the fixed-RD formula')
                for inp in inputs:
                    r.check(len(inp.get('roster') or []) == 5,
                            f'{mid}: Valve input {inp.get("name")!r} is not a five-player record')
                    r.check(bool(inp.get('points')) and bool(inp.get('source_url')),
                            f'{mid}: Valve input {inp.get("name")!r} lacks points or source link')
        else:
            r.check(False, f'{mid}: unknown analysis method {method!r}')
        # A published pick must be the strict favourite of its own two numbers.
        r.check(probs[0] != probs[1], f'{mid} ({names[0]} vs {names[1]}): probabilities tie; no strict favourite')

    # --------------------------------------------------------------- unresolved
    for m in unresolved:
        mid = str(m['id'])
        r.check(bool(m.get('limitations')), f'{mid}: pick-less row without limitations')
        r.check(bool(m.get('research')), f'{mid}: pick-less row without a research trail')
        r.check(m.get('pick_index') is None, f'{mid}: pick-less row carries a pick')
    r.check([str(m['id']) for m in unresolved] == [UNRESOLVED_ID],
            f'unresolved open rows {[str(m["id"]) for m in unresolved]} != [{UNRESOLVED_ID}]')
    row = next((m for m in unresolved if str(m['id']) == UNRESOLVED_ID), None)
    if row is None:
        r.check(False, f'the deployed build must leave {UNRESOLVED_ID} unresolved; it is priced or missing')
    else:
        r.check(any('multiple Valve rosters share this name' in str(x) for x in row.get('limitations') or []),
                '1082792 does not state the Valve identity limitation')
        stages = [s.get('stage') for s in row.get('research') or []]
        r.check(stages and stages[0] == 'Primary: Polymarket',
                f'1082792 research trail does not start at the primary market stage: {stages}')
        r.check(any('HLTV' in str(s) for s in stages),
                '1082792 research trail lacks an HLTV research stage')

    # ------------------------------------------------------------------ sources
    for m in priced:
        a, mid = m['analysis'], str(m['id'])
        host = host_of(a.get('source_url') or '')
        r.check(bool(host) and (host in PROBABILITY_HOSTS or any(host.endswith('.' + h) for h in PROBABILITY_HOSTS)),
                f'{mid}: probability attributed to non-official host {host!r}')
        r.check(host not in CROWD_HOSTS, f'{mid}: probability attributed to Hotspawn {host!r}')
        for path, key, value in iter_crowd_leaks(a):
            r.check(False, f'{mid}: crowd field leaked into analysis at {path} ({key}={value!r})')

    # -------------------------------------------------------------------- pages
    landing = (site / 'index.html').read_text(encoding='utf-8')
    picks = (site / 'picks' / 'index.html').read_text(encoding='utf-8')
    r.check('data-data-url="./snapshot.json"' in landing, 'landing page does not load ./snapshot.json')
    r.check('data-data-url="../snapshot.json"' in picks, 'picks page does not load ../snapshot.json')
    r.check('id="unresolved-register"' in landing, 'landing page lacks the unresolved register')
    r.check('HOTU vs The Huns' in landing, 'unresolved register does not name the 1082792 fixture')
    for m in open_rows:
        mid = str(m['id'])
        r.check(mid in landing, f'open fixture {mid} missing from the landing page')
        r.check(mid in picks, f'open fixture {mid} missing from the picks page')

    # ------------------------------------------------------------------ dossier
    dossier = json.loads(DOSSIER.read_text(encoding='utf-8'))
    covered = {str(f['hotspawn_id']) for f in dossier.get('fixtures') or []}
    snapshot_ids = {str(m['id']) for m in matches}
    priced_ids = {str(m['id']) for m in priced}
    # Everything the deployed build leaves unpicked: its one unresolved open row plus
    # the nine live lobby fixtures the snapshot does not contain at all (documented by
    # arena-500519ba at 00:44Z and re-read first-hand by this session).
    r.check(UNRESOLVED_ID in covered, f'dossier does not cover the unresolved fixture {UNRESOLVED_ID}')
    additions = covered - {UNRESOLVED_ID}
    r.check(len(additions) == 9, f'dossier documents {len(additions)} lobby additions, expected 9')
    r.check(not (covered & priced_ids),
            f'dossier covers fixtures the deployed build already prices: {sorted(covered & priced_ids)}')
    r.check(not (additions & snapshot_ids),
            f'dossier additions already exist as snapshot rows: {sorted(additions & snapshot_ids)}')

    for f in dossier.get('fixtures') or []:
        fid = str(f['hotspawn_id'])
        r.check(bool(f.get('hotspawn_start_utc')) and bool(f.get('findings')),
                f'dossier fixture {fid} lacks a start time or findings')
        for src, obs in (f.get('findings') or {}).items():
            if isinstance(obs, dict):
                r.check(bool(obs.get('url') or obs.get('base') or obs.get('api_url')) and bool(obs.get('observed_at')),
                        f'dossier fixture {fid} source {src!r} lacks a URL or read time')
    for flag in dossier.get('cross_source_flags') or []:
        r.check(bool(flag.get('id')) and bool(flag.get('title')) and bool(flag.get('evidence')),
                f'dossier flag {flag.get("id")!r} lacks id, title or evidence links')
    r.check(dossier.get('snapshot_under_review', {}).get('generated_at') == DEPLOYED_AT,
            'dossier does not pin the deployed snapshot timestamp')

    return r.result()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--snapshot', type=Path, default=SNAPSHOT)
    ap.add_argument('--site', type=Path, default=ROOT)
    ap.add_argument('--check', action='store_true', help='exit 1 on any error')
    args = ap.parse_args()
    result = verify(args.snapshot, args.site)
    stamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    print(json.dumps({'verified_at': stamp, **result}, indent=2))
    if args.check and result['errors']:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
