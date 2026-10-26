"""Session arena-b3e91409: independent, line-by-line verification of the published CS2 picks.

Run:  python -m scripts.b3e91409_verify [--check]

What it does, and deliberately does not do
------------------------------------------
It reads the *published* artefacts (`origination.json`, `snapshot.json`) and, when the live evidence
from `scripts.b3e91409_probe` is present, the first-party sources captured with their URLs and UTC
observation times. For every active row it checks, and re-derives, the numbers the row itself
publishes:

  market      midpoint of each side's published bid/ask, normalised   (exchange order books)
  bookmaker   proportional no-vig on the published decimal odds       (sportsbook prices)
  model       Valve's published fit.js logistic on the published points
  consensus / reference / network / relay / guidance
              median of the row's own published quotes

Nothing is imported from the production ladder: the formulas are re-implemented here from the
published inputs, so a defect in `scripts/originate.py` cannot make this checker agree with it.
A row is an **error** when a probability cannot be re-derived from what the row publishes, when the
pick is not the strict favourite, when a source link is missing/not https/not external, or when a
blank row carries a number. A live fixture with no published row is a **coverage gap**. Anything
that cannot be checked offline is reported as a note, never assumed correct.

Exit status: 0 when there are no errors (notes and coverage gaps may still exist), 1 with --check
when any error or coverage gap is present. The report is always written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('.')
LIVE = Path('data/research/b3e91409/live')
REPORT_DIR = Path('data/research/b3e91409')

METHODS = {'market', 'bookmaker', 'model', 'consensus', 'reference', 'network', 'relay', 'guidance'}
MARKET_TOL = 5e-7
MODEL_RD = 75
EXTERNAL_HOSTS = ('polymarket.com', 'thunderpick.io', 'github.com', 'kalshi.com', 'bovada.lv',
                  'hltv.org', 'pinnacle.com', 'gg.bet', 'stake.com', 'rivalry.com', 'smarkets.com',
                  'bo3.gg', 'egamersworld.com')


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_time(value):
    if not value:
        return None
    text = str(value).strip().replace(' ', 'T')
    if re.fullmatch(r'.*[+-]\d{2}$', text):
        text += ':00'
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def external(url):
    return isinstance(url, str) and url.startswith('https://') and any(
        url.split('/')[2].endswith(host) for host in EXTERNAL_HOSTS)


# ---------------------------------------------------------------- replay formulas

def replay_market(analysis):
    """Two published shapes are accepted, both of which carry the raw order book.

    (a) one quote per side:  quotes[i] = {bid: 0.18, ask: 0.22}      (the featured collector)
    (b) one quote, two sides: quotes[0] = {bid: [0.82, 0.08], ask: [0.92, 0.18]}  (originated line)
    """
    quotes = analysis.get('quotes') or []
    if not quotes:
        return None, 'a market row must publish its order-book quotes'
    if len(quotes) == 2 and all(not isinstance(q.get('bid'), list) for q in quotes):
        sides = [(q.get('bid'), q.get('ask')) for q in quotes]
        shape = 'one quote per side'
    elif len(quotes) == 1 and isinstance(quotes[0].get('bid'), list) and isinstance(quotes[0].get('ask'), list):
        if len(quotes[0]['bid']) != 2 or len(quotes[0]['ask']) != 2:
            return None, 'a two-sided quote must publish exactly two bids and two asks'
        sides = list(zip(quotes[0]['bid'], quotes[0]['ask']))
        shape = 'one quote carrying both sides'
    else:
        return None, 'the published quote shape is not a two-sided order book'
    midpoints = []
    for bid_raw, ask_raw in sides:
        bid, ask = number(bid_raw), number(ask_raw)
        if bid is None or ask is None:
            return None, 'both a bid and an ask are required for each side'
        if not (0 < bid < ask <= 1):
            # A zero bid or a 1.00 ask is one-sided: the price is not observable from both sides.
            return None, f'published bid/ask are not a valid two-sided book ({bid}/{ask})'
        midpoints.append((bid + ask) / 2)
    total = sum(midpoints)
    if not 0.9 <= total <= 1.1:
        return None, f'midpoints sum to {total:.6f}, outside 0.9-1.1'
    return [m / total for m in midpoints], f'{shape}: midpoints {[round(m, 6) for m in midpoints]} normalised by {round(total, 6)}'


def replay_bookmaker(analysis):
    quotes = analysis.get('quotes') or []
    if len(quotes) != 1:
        return None, 'a single-bookmaker row must publish exactly one quote pair'
    odds = quotes[0].get('odds')
    if not (isinstance(odds, list) and len(odds) == 2):
        return None, 'the quote must publish two decimal odds'
    values = [number(o) for o in odds]
    if any(v is None or v <= 1 for v in values):
        return None, 'decimal odds must be greater than 1'
    implied = [1 / v for v in values]
    margin = sum(implied)
    if not 0.85 <= margin <= 1.35:
        return None, f'paired margin {margin:.6f} is outside 0.85-1.35'
    return [i / margin for i in implied], f'implied {[round(i, 6) for i in implied]} de-vigged by {round(margin, 6)}'


def replay_model(analysis):
    """Valve's published fit.js logistic, unless the row is a fitted results model.

    A fitted form model publishes posterior means, a rating sd and the series it was fitted on, but
    not the predictive integral that turns those into a win probability. That number cannot be
    replayed from the row; the checker reports the standard Elo on the same published points so the
    size of the gap is visible instead of being hidden.
    """
    if analysis.get('family') == 'form' or 'results-based' in str(analysis.get('provider', '')).lower() or any(
            isinstance(i, dict) and i.get('fitted') for i in analysis.get('inputs') or []):
        inputs = analysis.get('inputs') or []
        points = [number(i.get('points')) for i in inputs if isinstance(i, dict)]
        if len(points) == 2 and all(p is not None for p in points):
            elo = 1 / (1 + 10 ** ((points[1] - points[0]) / 400))
            return None, ('a fitted results model does not publish the predictive formula that turns its '
                          f'posterior means {points} into a probability; a standard 400-point Elo on the same '
                          f'points gives {elo:.6f}')
        return None, 'a fitted results model publishes no replayable formula'
    inputs = analysis.get('inputs') or []
    if len(inputs) != 2:
        return None, 'a model row must publish both teams\' rating inputs'
    points = [number(row.get('points')) for row in inputs]
    if any(p is None for p in points):
        return None, 'both published rating-point values are required'
    rd = number(analysis.get('rd_assumption')) or MODEL_RD
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)
    p = 1 / (1 + 10 ** (g * (points[1] - points[0]) / 400))
    return [p, 1 - p], f'points {points} · RD {rd} · g {round(g, 9)} · fit.js logistic'


def replay_quotes(analysis):
    quotes = [q for q in (analysis.get('quotes') or []) if isinstance(q.get('probabilities'), list)]
    if not quotes:
        return None, 'an aggregated row must publish the per-source probabilities it summarises'
    medians = []
    for side in (0, 1):
        values = sorted(number(q['probabilities'][side]) for q in quotes)
        if any(v is None for v in values):
            return None, 'every published quote needs both probabilities'
        middle = len(values) // 2
        medians.append(values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2)
    total = sum(medians)
    return [m / total for m in medians], f'median of {len(quotes)} published quote pairs'


REPLAY = {'market': replay_market, 'bookmaker': replay_bookmaker, 'model': replay_model}


def replay(analysis):
    method = analysis.get('method')
    if method in REPLAY:
        return REPLAY[method](analysis)
    if method in METHODS:
        return replay_quotes(analysis)
    return None, f'unknown method {method!r}'


# ---------------------------------------------------------------- row checks

def check_row(row):
    findings, record = [], {
        'id': row.get('id'), 'teams': [t.get('name') for t in row.get('teams') or []],
        'starts_at': row.get('starts_at'), 'availability': row.get('availability'),
        'method': (row.get('origination') or {}).get('method') or row.get('featured_method'),
        'probabilities': None, 'pick': None, 'replay': None, 'verdict': 'blank',
    }
    analysis = row.get('origination') or {}
    probs = analysis.get('probabilities')
    if probs is None:
        # A blank row must still explain itself and must never carry a pick.
        if row.get('pick_index') is not None:
            findings.append(('error', row.get('id'), 'a row without probabilities carries a pick_index'))
        research = row.get('research') or []
        if not research:
            findings.append(('error', row.get('id'), 'a blank row publishes no research trail'))
        for item in research:
            if not item.get('source_url'):
                findings.append(('error', row.get('id'), f"research stage {item.get('stage')!r} has no source URL"))
        record['verdict'] = 'blank (explained)' if research else 'blank (unexplained)'
        return findings, record

    record['probabilities'] = probs
    if not (isinstance(probs, list) and len(probs) == 2):
        findings.append(('error', row.get('id'), 'probabilities must be exactly two numbers'))
        record['verdict'] = 'invalid'
        return findings, record
    values = [number(p) for p in probs]
    if any(v is None or not 0 < v < 1 for v in values):
        findings.append(('error', row.get('id'), f'probabilities are not both inside (0,1): {probs}'))
        record['verdict'] = 'invalid'
        return findings, record
    if abs(sum(values) - 1) > 1e-6:
        findings.append(('error', row.get('id'), f'probabilities sum to {sum(values):.9f}, not 1'))

    pick_index = row.get('pick_index')
    expected = 0 if values[0] > values[1] else (1 if values[1] > values[0] else None)
    if pick_index != expected:
        findings.append(('error', row.get('id'), f'pick_index {pick_index} is not the strict favourite ({expected})'))
    names = [t.get('name') for t in row.get('teams') or []]
    if pick_index in (0, 1) and len(names) == 2:
        record['pick'] = names[pick_index]
        if analysis.get('pick') not in (None, names[pick_index]):
            findings.append(('error', row.get('id'), f"analysis names {analysis.get('pick')!r} but pick_index is {pick_index}"))

    if analysis.get('method') not in METHODS:
        findings.append(('error', row.get('id'), f"unknown analysis method {analysis.get('method')!r}"))
    if not external(analysis.get('source_url')):
        findings.append(('error', row.get('id'), f"source URL is missing, not https or not external: {analysis.get('source_url')!r}"))
    observed = parse_time(analysis.get('observed_at'))
    if observed is None:
        findings.append(('error', row.get('id'), 'the analysis has no parseable observation time'))
    elif observed > now():
        findings.append(('error', row.get('id'), f"observation time {analysis.get('observed_at')} is in the future"))
    elif (now() - observed).total_seconds() > 48 * 3600:
        findings.append(('note', row.get('id'), f"price observed {(now() - observed).total_seconds() / 3600:.1f} h ago"))
    # The limitation can live on the nested analysis or on the row itself. The
    # published origination file uses `row['limitations']` (a list) for every
    # researched estimate, so only report a note when neither carries text.
    limitation_text = analysis.get('limitations') or analysis.get('limitation')
    if not limitation_text:
        limitation_text = row.get('limitations') or row.get('limitation')
    if not limitation_text:
        findings.append(('note', row.get('id'), 'the row publishes no limitation text'))

    replayed, detail = replay(analysis)
    record['replay'] = {'values': [round(v, 9) for v in replayed] if replayed else None, 'detail': detail}
    if replayed is None:
        findings.append(('error', row.get('id'), f'cannot replay the published numbers: {detail}'))
        record['verdict'] = 'unreplayable'
    else:
        tolerance = MARKET_TOL if analysis.get('method') in ('market', 'bookmaker') else 1e-6
        deltas = [abs(a - b) for a, b in zip(replayed, values)]
        record['replay']['deltas'] = [round(d, 12) for d in deltas]
        if max(deltas) > tolerance:
            findings.append(('error', row.get('id'),
                             f'published {values} differs from the replay {[round(v, 9) for v in replayed]} '
                             f'(max delta {max(deltas):.2e} > {tolerance})'))
            record['verdict'] = 'mismatch'
        else:
            record['verdict'] = 'verified'

    # Identity: a model's published inputs must name the same two teams the row does.
    inputs = analysis.get('inputs') or []
    published_names = [str(i.get('name')) for i in inputs if isinstance(i, dict) and i.get('name')]
    if analysis.get('method') == 'model' and len(published_names) == 2 and len(names) == 2:
        if [n.casefold().strip() for n in published_names] != [n.casefold().strip() for n in names]:
            order = [[n.casefold().strip() for n in names], [n.casefold().strip() for n in published_names]]
            if sorted(order[0]) != sorted(order[1]):
                findings.append(('error', row.get('id'),
                                 f'model inputs name different teams than the row: {published_names} vs {names}'))
            else:
                findings.append(('note', row.get('id'), 'model inputs are published in the opposite team order'))
    fair = analysis.get('fair_decimal')
    if fair:
        expected_fair = [round(1 / v, 3) for v in values]
        if [round(number(f) or 0, 3) for f in fair] != expected_fair:
            findings.append(('error', row.get('id'), f'fair_decimal {fair} is not 1/p rounded to 3 dp ({expected_fair})'))
    return findings, record


def find_crowd_fields(obj, path=''):
    """Hotspawn community participation is never an input; any such key in an analysis is an error."""
    hits = []
    if isinstance(obj, dict):
        for name, value in obj.items():
            if re.search(r'picked_?(percent|percentage|pct)', str(name), re.I):
                hits.append(path + '/' + str(name))
            hits.extend(find_crowd_fields(value, path + '/' + str(name)))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            hits.extend(find_crowd_fields(value, f'{path}[{index}]'))
    return hits


SITE_ROUTES = ('origination/#picks', 'picks/', 'unresolved/', 'coverage/', 'methodology/',
               '#picks-at-a-glance', '#unresolved-register')


def check_site(site_dir, matches):
    """The phone route the brief asks for: the executive summary must link the picks pages and
    every published match must have its own deep link on the page a reader lands on."""
    index = Path(site_dir) / 'index.html'
    if not index.exists():
        return [], None
    html = index.read_text(encoding='utf-8', errors='replace')
    findings = []
    for route in SITE_ROUTES:
        if route not in html:
            findings.append(('error', 'site', f'the executive summary does not link {route!r}'))
    missing = [m['id'] for m in matches if f'#match-{m["id"]}' not in html]
    for fixture_id in missing:
        findings.append(('error', fixture_id, 'the executive summary has no in-site deep link to this published row'))
    return findings, {'index': str(index), 'routes_present': [r for r in SITE_ROUTES if r in html],
                      'deep_links_missing': missing, 'rows': len(matches)}


def coverage(live, published_ids):
    gaps = []
    for fixture in live:
        if str(fixture['id']) in published_ids:
            continue
        gaps.append({'id': str(fixture['id']), 'teams': fixture['teams'],
                     'starts_at': fixture['starts_at'], 'competition': fixture.get('competition'),
                     'source_url': f"https://play.hotspawn.com/cs2-pickems#fixture-{fixture['id']}",
                     'analysis': fixture.get('analysis')})
    return gaps


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='exit 1 on any error or coverage gap')
    parser.add_argument('--origination', default=str(ROOT / 'origination.json'))
    parser.add_argument('--snapshot', default=str(ROOT / 'snapshot.json'))
    parser.add_argument('--report-dir', default=str(REPORT_DIR))
    parser.add_argument('--live-dir', default=str(LIVE))
    parser.add_argument('--site', default=None, help='optional built site directory to check the phone route')
    args = parser.parse_args(argv)

    origination_path, snapshot_path = Path(args.origination), Path(args.snapshot)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    if not origination_path.exists():
        print(f'missing {origination_path}', file=sys.stderr)
        return 2
    origination = json.loads(origination_path.read_text(encoding='utf-8'))
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8')) if snapshot_path.exists() else {}

    findings, rows = [], []
    for row in origination.get('matches') or []:
        row_findings, record = check_row(row)
        findings.extend(row_findings)
        rows.append(record)

    # Every published open fixture must also exist in the inventory snapshot, and vice versa.
    published_ids = {str(m['id']) for m in origination.get('matches') or []}
    snapshot_open = {str(m['id']) for m in snapshot.get('matches') or []
                     if m.get('availability') in ('open', 'locked', 'unknown_lock')}
    for missing in sorted(snapshot_open - published_ids):
        findings.append(('error', missing, 'the inventory snapshot lists this open fixture but the picks file has no row'))
    for extra in sorted(published_ids - {str(m['id']) for m in snapshot.get('matches') or []}):
        findings.append(('note', extra, 'the picks file lists a fixture the inventory snapshot does not carry'))

    live = []
    live_meta = None
    analysis_path = Path(args.live_dir) / 'analysis.json'
    if analysis_path.exists():
        analysis = json.loads(analysis_path.read_text(encoding='utf-8'))
        live = analysis.get('fixtures') or []
        live_meta = {'observed_at': analysis.get('observed_at'), 'counts': analysis.get('counts'),
                     'source': str(analysis_path)}
    gaps = coverage(live, published_ids) if live else []
    for gap in gaps:
        findings.append(('coverage-gap', gap['id'],
                         f"live open fixture {gap['teams'][0]} vs {gap['teams'][1]} ({gap['starts_at']}) has no published row"))

    site_findings, site_meta = ([], None)
    if args.site:
        site_findings, site_meta = check_site(args.site, origination.get('matches') or [])
        findings.extend(site_findings)

    crowd = find_crowd_fields(origination.get('matches'))
    for path in crowd:
        findings.append(('error', 'crowd', f'community participation field in a picks row: {path}'))

    errors = [f for f in findings if f[0] in ('error', 'coverage-gap')]
    summary = {
        'rows': len(rows),
        'verified': sum(1 for r in rows if r['verdict'] == 'verified'),
        'blank': sum(1 for r in rows if r['verdict'].startswith('blank')),
        'errors': len([f for f in findings if f[0] == 'error']),
        'coverage_gaps': len(gaps),
        'site_errors': len([f for f in findings if f[1] == 'site']),
        'notes': len([f for f in findings if f[0] == 'note']),
    }
    report = {
        'schema_version': 1, 'session': 'arena-b3e91409', 'verified_at': iso(now()),
        'inputs': [{'path': str(p), 'sha256': digest(p), 'generated_at':
                    (json.loads(p.read_text(encoding='utf-8')).get('generated_at') if p.suffix == '.json' else None)}
                   for p in (origination_path, snapshot_path) if p.exists()],
        'published': {'counts': origination.get('counts'), 'generated_at': origination.get('generated_at'),
                      'active_ids': sorted(published_ids)},
        'live': live_meta,
        'site': site_meta,
        'summary': summary,
        'rows': rows,
        'findings': [{'severity': s, 'id': i, 'detail': d} for s, i, d in findings],
        'coverage_gaps': gaps,
        'limits': ['Offline replay only: each number is re-derived from the inputs the row itself '
                   'publishes. The live sources captured by scripts.b3e91409_probe are compared for '
                   'coverage and identity, not re-priced after the fact.',
                   'A verified row means "the published probabilities follow from the published inputs"; '
                   'it does not mean the source price was profitable, liquid or still current.'],
    }
    (report_dir / 'verification.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')

    lines = [f'# Independent verification — {report["verified_at"]}', '',
             f"Rows checked: **{summary['rows']}** · verified: **{summary['verified']}** · "
             f"blank (explained): **{summary['blank']}** · errors: **{summary['errors']}** · "
             f"live coverage gaps: **{summary['coverage_gaps']}** · notes: **{summary['notes']}**", '']
    if report['inputs']:
        lines += ['## Inputs', '']
        for item in report['inputs']:
            lines.append(f"- `{item['path']}` · generated {item['generated_at']} · sha256 `{item['sha256'][:16]}…`")
        lines.append('')
    lines += ['## Rows', '', '| Fixture | Teams | Method | Probabilities | Pick | Replay | Verdict |', '| --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        probs = ' / '.join(f'{p * 100:.1f}%' for p in row['probabilities']) if row['probabilities'] else '—'
        delta = max(row['replay']['deltas']) if row['replay'] and row['replay'].get('deltas') else None
        lines.append(f"| {row['id']} | {row['teams'][0]} vs {row['teams'][1]} | {row['method']} | {probs} | "
                     f"{row['pick'] or '—'} | {'—' if delta is None else f'{delta:.1e}'} | {row['verdict']} |")
    lines += ['', '## Findings', '']
    if findings:
        for severity, target, detail in findings:
            lines.append(f'- **{severity}** `{target}` — {detail}')
    else:
        lines.append('- none')
    if gaps:
        lines += ['', '## Live fixtures with no published row', '',
                  '| Fixture | Teams | Starts (UTC) | Competition | Hotspawn |', '| --- | --- | --- | --- | --- |']
        for gap in gaps:
            lines.append(f"| {gap['id']} | {gap['teams'][0]} vs {gap['teams'][1]} | {gap['starts_at']} | "
                         f"{gap.get('competition') or '—'} | {gap['source_url']} |")
    lines += ['', '## Limits of this check', ''] + [f'- {item}' for item in report['limits']]
    (report_dir / 'verification.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    if args.check and errors:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
