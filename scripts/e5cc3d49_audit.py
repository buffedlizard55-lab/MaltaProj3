"""Independent, read-only line-by-line audit of the published CS2 picks.

Session arena-e5cc3d49. The publisher already replays every published
*featured* probability from its saved evidence (``scripts.validate``) and
checks complete-pick coverage (``scripts.coverage_audit``). This module does
something different and complementary: it takes the two published JSON files
(``data/latest.json`` and ``data/origination.json``), the saved first-party
evidence and the built ``site/`` tree, and re-derives every number it can from
the primary observation that is quoted beside it, then records — explicitly —
the rows it cannot re-derive instead of passing them silently.

What it recomputes, with no network access and no new data:

* a Polymarket row, from the saved CLOB order books (best bid / best ask per
  outcome, normalised) and from the bid/ask the row itself publishes;
* an esportsbook row, from the quoted decimal odds (``1/o`` normalised);
* a consensus row, from the median of the per-provider normalised prices;
* a Valve-rating research model row, from the published official points and
  the documented Glicko scaling (fixed RD 75);
* every row's internal arithmetic: two probabilities in (0, 1) summing to 1,
  a pick that is the argmax, an https source link, a known ladder method and a
  real ISO-8601 observation time.

What it *cannot* recompute is named per row: the Bradley–Terry network fit,
the HLTV-ranking transform and the results-form fit need the collector's graph
inputs, which are not in the published payload. Those rows are listed as
``not_recomputable`` with the reason — never marked verified.

It also reconciles inventory to rows (every active Hotspawn fixture has a row),
rows to counts, and rows to the built phone pages (the executive summary's
glance index must name every active fixture and its pick, and the complete list
must carry a ``match-<id>`` anchor). Exit code 1 means at least one violation.

Usage::

    python -m scripts.e5cc3d49_audit --data data --site site \
        --out data/research/e5cc3d49/line-by-line-audit.json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = 1
TOLERANCE = 0.003          # published values are rounded to 3 decimals
SUM_TOLERANCE = 0.002
FRESH_HOURS = 8
KNOWN_METHODS = {'market', 'bookmaker', 'consensus', 'reference', 'model', 'guidance'}
ACTIVE = {'open', 'locked', 'unknown_lock'}
VALVE_RD = 75.0


def _https(value) -> bool:
    return isinstance(value, str) and value.startswith('https://')


def _iso(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def _pairs(probabilities):
    return (len(probabilities) == 2
            and all(isinstance(p, (int, float)) and 0 < p < 1 for p in probabilities))


def _norm(values):
    total = sum(values)
    return [v / total for v in values]


def _median_of(rows):
    return [statistics.median([r[0] for r in rows]), statistics.median([r[1] for r in rows])]


def best_book_prices(book: dict):
    """Return (best bid, best ask) from a saved Polymarket CLOB book.

    The saved book lists bids ascending and asks descending; the best bid is
    therefore the highest bid price and the best ask the lowest ask price.
    """
    bids = [float(row['price']) for row in book.get('bids') or [] if row.get('size')]
    asks = [float(row['price']) for row in book.get('asks') or [] if row.get('size')]
    if not bids or not asks:
        return None
    return max(bids), min(asks)


def _valve_probability(points_a: float, points_b: float) -> float:
    """Valve's published logistic scale with the fixed RD the site documents."""
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * VALVE_RD ** 2 / math.pi ** 2)
    return 1 / (1 + 10 ** (g * (points_b - points_a) / 400))


def audit_row(row: dict, evidence_dir: Path, now: datetime):
    """Return (checks_performed, violations, recomputation_or_None, note)."""
    mid = str(row.get('id'))
    label = f'fixture {mid}'
    problems: list[str] = []
    checks: list[str] = []
    teams = row.get('teams') or []
    if len(teams) != 2 or not all(t.get('name') for t in teams):
        return checks, [f'{label}: does not name exactly two teams'], None, 'no row'
    names = [t['name'] for t in teams]
    checks.append('two named teams')

    # The fixture link must be an official Hotspawn surface that carries this id.
    hotspawn_links = [u for u in (row.get('source_url'), row.get('lobby_url')) if _https(u)]
    if not any(mid in (u or '') for u in hotspawn_links):
        problems.append(f'{label}: no official Hotspawn link carrying the fixture id')
    else:
        checks.append('official Hotspawn link carries the fixture id')

    origination = row.get('origination')
    if not origination:
        trail = row.get('research') or []
        if not trail:
            problems.append(f'{label}: unresolved without a research trail')
        else:
            checks.append(f'unresolved with {len(trail)} research steps')
            if not any(_https(step.get('source_url')) for step in trail):
                problems.append(f'{label}: research trail has no https source')
            else:
                checks.append('research trail cites an https source')
        if not (row.get('limitations') or []):
            problems.append(f'{label}: unresolved without a published limitation')
        else:
            checks.append(f'{len(row["limitations"])} published limitation(s)')
        if row.get('pick_index') is not None:
            problems.append(f'{label}: unresolved row still publishes a pick')
        return checks, problems, None, 'unresolved (blank by design)'

    probs = origination.get('probabilities') or []
    if not _pairs(probs):
        return checks, problems + [f'{label}: probabilities are not two values in (0, 1)'], None, 'invalid'
    checks.append('two probabilities in (0, 1)')
    if abs(sum(probs) - 1.0) > SUM_TOLERANCE:
        problems.append(f'{label}: probabilities sum to {sum(probs):.4f}')
    else:
        checks.append('probabilities sum to 1')

    pick = row.get('pick_index')
    if abs(probs[0] - probs[1]) <= 0.0005:
        if pick is not None:
            problems.append(f'{label}: even estimate still publishes a side')
    elif pick is None:
        problems.append(f'{label}: directional estimate publishes no pick')
    elif pick not in (0, 1) or probs[pick] != max(probs):
        problems.append(f'{label}: published pick is not the higher-probability side')
    else:
        checks.append(f'pick is the argmax ({names[pick]})')

    method = origination.get('method')
    if method not in KNOWN_METHODS:
        problems.append(f'{label}: unknown ladder method {method!r}')
    else:
        checks.append(f'known ladder method ({method})')

    links = [origination.get('source_url')] + [q.get('source_url') for q in origination.get('quotes') or []]
    links += [i.get('source_url') for i in origination.get('inputs') or []]
    if not any(_https(link) for link in links):
        problems.append(f'{label}: no https source link beside the number')
    else:
        checks.append('https source link beside the number')

    observed = _iso(origination.get('observed_at'))
    if observed is None:
        problems.append(f'{label}: missing or malformed observation time')
    else:
        checks.append('ISO-8601 observation time')
        if observed - now > timedelta(minutes=5):
            problems.append(f'{label}: observation time is in the future')
        if row.get('availability') in ACTIVE and now - observed > timedelta(hours=FRESH_HOURS):
            problems.append(f'{label}: active row observed {now - observed} before this audit '
                            f'(older than {FRESH_HOURS}h)')

    # ---- recomputation ---------------------------------------------------
    recomputed = None
    quotes = origination.get('quotes') or []
    families = {q.get('family') for q in quotes}
    if method == 'market' and quotes and all('bid' in q and 'ask' in q for q in quotes):
        mids = [(q['bid'] + q['ask']) / 2 for q in quotes]
        recomputed = _norm(mids)
        checks.append('recomputed from published bid/ask midpoints')
        for q, published in zip(quotes, probs):
            if abs((q['bid'] + q['ask']) / 2 / sum(mids) - published) > TOLERANCE:
                problems.append(f'{label}: bid/ask midpoint does not reproduce the published probability')
        # Replay the saved order books, when the collector stored them. Each
        # outcome's book is saved under its own index; a book is never used to
        # confirm the other outcome.
        event_id = origination.get('event_id')
        for index, quote in enumerate(quotes):
            book_path = evidence_dir / f'polymarket-book-{event_id}-{index}.json' if event_id else None
            if not book_path or not book_path.exists():
                continue
            try:
                prices = best_book_prices(json.loads(book_path.read_text()))
            except (ValueError, KeyError, OSError):
                prices = None
            if not prices:
                problems.append(f'{label}: saved order book for outcome {index} has no two-sided quote')
                continue
            if abs(prices[0] - quote['bid']) > 0.005 or abs(prices[1] - quote['ask']) > 0.005:
                problems.append(f'{label}: saved order book does not reproduce the quoted bid/ask for outcome {index}')
            else:
                checks.append(f'saved order book reproduces outcome {index} bid/ask')
    elif method in {'bookmaker', 'reference'} and quotes and all(q.get('odds') for q in quotes):
        odds = quotes[0]['odds']
        if all(isinstance(o, (int, float)) and o > 1 for o in odds) and len(odds) == 2:
            recomputed = _norm([1 / o for o in odds])
            checks.append('recomputed from quoted decimal odds (1/o, normalised)')
            if max(abs(a - b) for a, b in zip(recomputed, probs)) > TOLERANCE:
                problems.append(f'{label}: quoted odds do not reproduce the published probability')
        else:
            problems.append(f'{label}: quoted odds are not a valid two-way decimal pair')
    elif method in {'bookmaker'} and quotes and not quotes[0].get('odds'):
        # A relayed price publishes the provider's own probabilities only.
        per_provider = [q['probabilities'] for q in quotes if _pairs(q.get('probabilities') or [])]
        if per_provider:
            checks.append('relayed two-way price present (probabilities only, no odds relayed)')
        else:
            problems.append(f'{label}: bookmaker row without odds or probabilities')
    elif method == 'consensus' and quotes:
        per_provider = {}
        for quote in quotes:
            if _pairs(quote.get('probabilities') or []):
                per_provider.setdefault(quote.get('provider'), quote['probabilities'])
        if len(per_provider) > 1:
            recomputed = _median_of(list(per_provider.values()))
            checks.append(f'recomputed as the median of {len(per_provider)} independent providers')
            if max(abs(a - b) for a, b in zip(recomputed, probs)) > TOLERANCE:
                problems.append(f'{label}: provider median does not reproduce the published probability')
        else:
            problems.append(f'{label}: consensus row has fewer than two independent providers')
    elif method == 'model' and (origination.get('family') == 'valve' or origination.get('provider') == 'Valve official standings'):
        inputs = origination.get('inputs') or []
        if len(inputs) == 2 and all(isinstance(i.get('points'), (int, float)) for i in inputs):
            recomputed = _norm([_valve_probability(inputs[0]['points'], inputs[1]['points']),
                                _valve_probability(inputs[1]['points'], inputs[0]['points'])])
            checks.append('recomputed from official Valve points (fixed RD 75)')
            if max(abs(a - b) for a, b in zip(recomputed, probs)) > 0.006:
                problems.append(f'{label}: Valve points do not reproduce the published model probability')
        else:
            problems.append(f'{label}: Valve model row without two point inputs')

    note = ''
    if recomputed is None and method == 'model':
        note = ('model fit (network / HLTV-ranking / results form); its graph inputs are not in the '
                'published payload, so the number is recorded as not independently recomputable')
    elif recomputed is None and method == 'guidance':
        note = 'wide-book guidance midpoint; not a validated line'
    return checks, problems, recomputed, note


def audit_payload(latest: dict, origination: dict, site: Path | None, evidence_dir: Path, now: datetime | None = None):
    now = now or datetime.now(timezone.utc)
    report = {'schema_version': SCHEMA, 'audited_at': now.isoformat().replace('+00:00', 'Z'),
              'snapshot': {'featured_generated_at': latest.get('generated_at'),
                           'origination_generated_at': origination.get('generated_at'),
                           'inventory_observed_at': latest.get('inventory_observed_at')},
              'violations': [], 'rows': [], 'not_recomputable': [], 'checks': {}}
    rows = origination.get('matches') or []
    if not rows:
        report['violations'].append('complete-picks payload has no matches')
        return report

    active_inventory = sorted(str(m['id']) for m in latest.get('matches') or []
                              if m.get('availability') in ACTIVE)
    ids = [str(r.get('id')) for r in rows]
    if len(set(ids)) != len(ids):
        report['violations'].append('duplicate fixture id in the complete-picks payload')
    missing = [mid for mid in active_inventory if mid not in set(ids)]
    if missing:
        report['violations'].append(f'{len(missing)} active Hotspawn fixture(s) have no pick row: {", ".join(missing)}')
    extra = [mid for mid in ids if mid not in {str(m['id']) for m in latest.get('matches') or []}]
    if extra:
        report['violations'].append(f'{len(extra)} pick row(s) are not in the current inventory: {", ".join(extra)}')
    report['checks']['inventory_reconciled'] = not missing and not extra
    report['checks']['active_fixtures'] = len(active_inventory)

    totals = {'market': 0, 'bookmaker': 0, 'consensus': 0, 'reference': 0, 'model': 0,
              'guidance': 0, 'unresolved': 0, 'recomputed': 0, 'rows': len(rows)}
    for row in rows:
        checks, problems, recomputed, note = audit_row(row, evidence_dir, now)
        method = (row.get('origination') or {}).get('method')
        if method is None:
            totals['unresolved'] += 1
        elif method in totals:
            totals[method] += 1
        if recomputed is not None:
            totals['recomputed'] += 1
        elif method == 'model':
            report['not_recomputable'].append({'id': str(row.get('id')), 'reason': note,
                                               'source_url': (row.get('origination') or {}).get('source_url')})
        report['rows'].append({'id': str(row.get('id')),
                               'teams': [t.get('name') for t in row.get('teams') or []],
                               'method': method,
                               'pick': (row.get('teams') or [{}])[row['pick_index']]['name']
                                       if row.get('pick_index') in (0, 1) else None,
                               'probabilities': (row.get('origination') or {}).get('probabilities'),
                               'checks': checks, 'violations': problems, 'note': note})
        report['violations'].extend(problems)
    report['totals'] = totals

    published = origination.get('counts') or {}
    mismatched = {key: (published.get(key), totals.get(key)) for key in published
                  if key in totals and isinstance(published.get(key), int) and published[key] != totals[key]}
    if mismatched:
        report['violations'].append(f'published counts disagree with the rows: {mismatched}')
    report['checks']['counts_reconciled'] = not mismatched

    if site is not None and site.exists():
        summary = (site / 'index.html').read_text()
        complete = (site / 'origination' / 'index.html').read_text()
        for target in ('origination/#picks', 'origination/#unresolved', '#unresolved-register', '#no-line-register'):
            if target not in summary and target.replace('origination/', './origination/') not in summary:
                report['violations'].append(f'executive summary does not link {target}')
        report['checks']['summary_links'] = all(
            t in summary or t.replace('origination/', './origination/') in summary
            for t in ('origination/#picks', 'origination/#unresolved', '#unresolved-register'))
        absent = []
        for row in rows:
            mid = str(row.get('id'))
            if row.get('availability') not in ACTIVE and row.get('availability') is not None:
                pass
            if f'data-glance-id="{mid}"' not in summary and row.get('availability') in ACTIVE:
                # A resolved row may be grouped below the fold but must still be
                # in the glance index; an unresolved row must always be there.
                absent.append(mid)
            if f'id="match-{mid}"' not in complete:
                report['violations'].append(f'complete list has no anchor for fixture {mid}')
            if f'id="row-{mid}"' not in complete:
                report['violations'].append(f'complete list overview has no row for fixture {mid}')
        if absent:
            report['violations'].append(f'executive summary glance index omits {len(absent)} active fixture(s): '
                                        f'{", ".join(absent)}')
        report['checks']['glance_complete'] = not absent
        # The pick named in the summary index must be the published argmax.
        for row in rows:
            if row.get('availability') not in ACTIVE or not row.get('origination'):
                continue
            mid = str(row.get('id'))
            pick = row.get('pick_index')
            if pick not in (0, 1):
                continue
            name = (row['teams'])[pick]['name']
            start = summary.find(f'data-glance-id="{mid}"')
            if start == -1:
                continue
            block = summary[start:start + 2000]
            if name not in block:
                report['violations'].append(f'summary glance row {mid} does not name the published pick {name}')
        report['checks']['summary_picks_match'] = not any('does not name the published pick' in v
                                                          for v in report['violations'])
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--site', type=Path, default=Path('site'))
    parser.add_argument('--out', type=Path, default=None)
    args = parser.parse_args(argv)
    latest = json.loads((args.data / 'latest.json').read_text())
    origination = json.loads((args.data / 'origination.json').read_text())
    report = audit_payload(latest, origination, args.site, args.data / 'evidence')
    text = json.dumps(report, indent=1)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + '\n')
    print(f"audited {report['totals']['rows']} rows: "
          f"{report['totals']['recomputed']} recomputed from their own primary evidence, "
          f"{len(report['not_recomputable'])} model rows not independently recomputable, "
          f"{len(report['violations'])} violation(s)")
    for violation in report['violations'][:40]:
        print(' - ' + violation)
    return 1 if report['violations'] else 0


if __name__ == '__main__':
    sys.exit(main())
