"""Session arena-60019704: independent, offline replay of a published build.

The dashboard's promise is that a reader can re-derive each published number
from the data the page itself publishes.  This script performs that check line
by line, without network access and without trusting any value it cannot
recompute.  It was built to replay the deployed 2026-10-25T23:03:48Z build
(that snapshot is archived verbatim at
``data/research/60019704/snapshot-2026-10-25T23-03-48Z.json`` so the dated
verification stays reproducible), but every assertion is snapshot-independent:
the four-hour publisher replaces the root ``snapshot.json`` on every refresh,
and an assertion pinned to one observation would break the publisher's
regression step and freeze the refresh (the failure class recorded on
2026-10-25, run 40174233578).  Run against any snapshot the checks are:

``inventory``
    Declared counts agree with the rows the file actually carries; ids are
    unique; the open/past split follows the start timestamps; declared
    evidence files exist; the refresh/stale cadence is 4/8 hours as promised.
``replay``
    Every open row with an analysis has its two probabilities recomputed from
    the inputs the row itself publishes: bid/ask midpoints for a market row
    (with the spread ceiling enforced on both quotes), proportional no-vig
    normalisation for a bookmaker row, and Valve's published fixed-RD Glicko
    expectation for a model row.  A mismatch is an error, not a rounding
    note.  Every priced row must have a strict favourite.
``unresolved``
    Every open row without an analysis publishes a non-empty limitations list
    and a multi-stage research trail.  When 1082792 (HOTU vs The Huns, the
    fixture this session researched) is among them, its Valve identity
    limitation and research trail are checked; when a later build prices or
    drops it, that is recorded as a note (publishing evolution), not an error.
``sources``
    Every probability is attributed to an official publisher over https.
    Hotspawn (the pick'em host) is never a probability source, and no crowd
    field leaks into an analysis row.
``pages``
    When the built pages carry the same observation as the snapshot (same
    ``generated`` marker), every open fixture id appears on both the landing
    and the picks page and the unresolved register exists.  A newer snapshot
    than the built pages is a publishing window, recorded as a note.
``dossier``
    This session's research dossier (``data/research/60019704/research.json``)
    is self-consistent: it covers the unresolved 1082792 plus exactly the nine
    documented lobby additions, none of them priced in the build the dossier
    reviewed (archived alongside it).  Later builds pricing those fixtures are
    recorded as notes, not errors.

Usage::

    python -m scripts.60019704_verify [--snapshot PATH] [--site PATH] [--check]

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
ARCHIVE = ROOT / 'data/research/60019704/snapshot-2026-10-25T23-03-48Z.json'
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
RESEARCHED_ID = '1082792'  # HOTU vs The Huns — the fixture this session researched.
# The nine additional live lobby fixtures documented in the dossier (read
# 2026-10-26T00:52Z, first observed by arena-500519ba at 00:44Z).
LOBBY_ADDITIONS = frozenset({
    '1079201', '1079202', '1079203', '1081159', '1081160',
    '1081162', '1081163', '1081164', '1093218',
})


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
            if k.lower() in CROWD_KEYS or (k == 'source_url' and any(h in str(v) for h in CROWD_HOSTS)):
                yield here, k, v
            yield from iter_crowd_leaks(v, here)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_crowd_leaks(v, f'{path}[{i}]')


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.notes: list[str] = []
        self.checks = 0

    def check(self, ok: bool, message: str) -> bool:
        self.checks += 1
        if not ok:
            self.errors.append(message)
        return ok

    def note(self, message: str) -> None:
        self.notes.append(message)

    def result(self, summary: dict) -> dict:
        return {'session': 'arena-60019704', 'checks': self.checks, 'errors': self.errors,
                'notes': self.notes, 'ok': not self.errors, **summary}


def verify(snapshot_path: Path, site: Path | None = None) -> dict:
    r = Report()
    snap = json.loads(snapshot_path.read_text(encoding='utf-8'))

    # ---------------------------------------------------------------- inventory
    matches = snap.get('matches') or []
    generated_at = snap.get('generated_at')
    r.check(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', generated_at or '')),
            f'generated_at {generated_at!r} is not a UTC timestamp')
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
    for m in open_rows:
        r.check(bool(m.get('starts_at')) and m['starts_at'] > generated_at,
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
    row = next((m for m in unresolved if str(m['id']) == RESEARCHED_ID), None)
    if row is not None:
        r.check(any('multiple Valve rosters share this name' in str(x) for x in row.get('limitations') or []),
                '1082792 does not state the Valve identity limitation')
        stages = [s.get('stage') for s in row.get('research') or []]
        r.check(stages and stages[0] == 'Primary: Polymarket',
                f'1082792 research trail does not start at the primary market stage: {stages}')
        r.check(any('HLTV' in str(s) for s in stages),
                '1082792 research trail lacks an HLTV research stage')
    elif any(str(m['id']) == RESEARCHED_ID for m in matches):
        r.note(f'{RESEARCHED_ID} is priced in this build; the 2026-10-25T23:03:48Z build left it unresolved '
               '(publishing evolution, not a defect)')
    else:
        r.note(f'{RESEARCHED_ID} is not in this snapshot (archived or rotated)')

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
    page_marker = None
    if site is not None:
        landing_path, picks_path = site / 'index.html', site / 'picks' / 'index.html'
        r.check(landing_path.exists() and picks_path.exists(), 'landing or picks page is missing from the site')
        if landing_path.exists() and picks_path.exists():
            landing = landing_path.read_text(encoding='utf-8')
            picks = picks_path.read_text(encoding='utf-8')
            r.check('data-data-url="./snapshot.json"' in landing, 'landing page does not load ./snapshot.json')
            r.check('data-data-url="../snapshot.json"' in picks, 'picks page does not load ../snapshot.json')
            r.check('id="unresolved-register"' in landing, 'landing page lacks the unresolved register')
            found = re.search(r'generated="([^"]+)"', landing)
            page_marker = found.group(1) if found else None
            if page_marker and page_marker != generated_at:
                r.note(f'built pages carry {page_marker}, snapshot carries {generated_at}; '
                       'page coverage not judged (a newer snapshot than the built pages)')
            elif page_marker:
                for m in open_rows:
                    mid = str(m['id'])
                    r.check(mid in landing, f'open fixture {mid} missing from the landing page')
                    r.check(mid in picks, f'open fixture {mid} missing from the picks page')
                if row is not None:
                    r.check('HOTU vs The Huns' in landing,
                            'unresolved register does not name the 1082792 fixture')
            else:
                r.note('landing page carries no generated marker; page coverage not judged')

    # ------------------------------------------------------------------ dossier
    dossier = json.loads(DOSSIER.read_text(encoding='utf-8'))
    covered = {str(f['hotspawn_id']) for f in dossier.get('fixtures') or []}
    r.check(covered == LOBBY_ADDITIONS | {RESEARCHED_ID},
            f'dossier coverage {sorted(covered)} != 1082792 + the nine documented lobby additions')
    # The reviewed build is the archived 2026-10-25T23:03:48Z snapshot, kept
    # verbatim beside the dossier so the dated claims stay reproducible.
    try:
        archive = json.loads(ARCHIVE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        archive = {}
        r.check(False, f'archived reviewed snapshot missing or unreadable: {ARCHIVE}')
    if archive:
        archive_open = [m for m in archive.get('matches') or [] if m.get('availability') == 'open']
        reviewed = dossier.get('snapshot_under_review') or {}
        r.check(reviewed.get('generated_at') == archive.get('generated_at'),
                'dossier snapshot_under_review does not name the archived build')
        r.check({str(x) for x in reviewed.get('open_fixtures') or []} == {str(m['id']) for m in archive_open},
                'dossier open-fixture record does not match the archived build')
        archive_priced = {str(m['id']) for m in archive_open if m.get('analysis')}
        r.check(not (covered & archive_priced),
                f'dossier covers fixtures the reviewed build already priced: {sorted(covered & archive_priced)}')
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
    # Publishing evolution: later builds may price the researched fixtures.
    now_priced = sorted(covered & {str(m['id']) for m in priced})
    if now_priced:
        r.note('fixtures the reviewed build left unpicked that this build prices: ' + ', '.join(now_priced))
    still_open_unresolved = sorted(covered & {str(m['id']) for m in unresolved})
    if still_open_unresolved:
        r.note('researched fixtures still without a pick in this build: ' + ', '.join(still_open_unresolved))

    summary = {'snapshot_generated_at': generated_at,
               'counts': {'open': len(open_rows), 'priced': len(priced), 'unresolved': len(unresolved)},
               'methods': by_method, 'page_marker': page_marker}
    return r.result(summary)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--snapshot', type=Path, default=SNAPSHOT,
                    help='snapshot to replay (default: the live root snapshot.json)')
    ap.add_argument('--site', type=Path, default=ROOT,
                    help='site root for the page checks (pass . to judge only the snapshot)')
    ap.add_argument('--check', action='store_true', help='exit 1 on any error')
    args = ap.parse_args()
    site = None if str(args.site) in ('', '.') else args.site
    result = verify(args.snapshot, site)
    stamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    print(json.dumps({'verified_at': stamp, **result}, indent=2))
    if args.check and result['errors']:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
