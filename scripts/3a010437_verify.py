"""Session arena-3a010437 — an independent, dated re-read of every published pick.

The coding sandbox cannot reach Hotspawn, Polymarket, HLTV or a bookmaker; the
GitHub Actions runner can. This module runs there, after ``scripts.collect`` and
``scripts.originate --live``, and re-reads **each published row against the
original source that row itself cites**. It is an audit, not a pipeline stage:

* it never writes a probability, a pick, an alias or an ordinal ranking;
* it never fills a blank;
* it records what the original said at a second, later observation time and
  compares it with what the site published, so a human can see the delta.

For each active fixture it records

``identity``
    HTTP status and the page title of the row's own Hotspawn match URL, and
    whether both published team names appear in that title.

``price``
    For a Polymarket row, the event's own Gamma endpoint (``source_api`` as
    published in ``data/origination.json``): the series-winner market's current
    bid/ask midpoints, compared with the published probabilities (delta) and
    with the published pick (does the price still favour the picked side?).
    For any other money row (Thunderpick, Smarkets, Kalshi, bo3.gg relay, a
    consensus of those) the cited URL is fetched and its status recorded; a
    green status is reported as *reachable*, never as a re-verified price,
    unless the row cites a documented JSON endpoint that is parsed here.

``arithmetic``
    Two probabilities inside (0, 1) summing to 1, and ``pick_index`` pointing
    at the larger one.

Verdicts (per row): ``confirmed``, ``price_moved``, ``pick_disagrees``,
``source_unreadable`` or ``model_not_a_line`` (a research-model estimate has no
price to re-read; that is a limitation, not a failure).

Usage::

    python -m scripts.3a010437_verify [--data data] [--out data/research/3a010437]
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

UTC = timezone.utc
TIMEOUT = 20
#: A published probability may legitimately move after it is observed. Up to
#: this much drift is reported as agreement, above it as a move — never as an
#: error, because the site publishes an observation time and picks are forward
#: looking. Only a price that now favours the *other* side is a real conflict.
DRIFT_OK = 0.05
MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference', 'relay', 'network'}
HEADERS = {'User-Agent': 'SpawnScout-verify/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'}


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def fold(text: str) -> str:
    """Case/accent/punctuation-insensitive form for name containment checks."""
    text = unicodedata.normalize('NFKD', str(text or ''))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', '', text.casefold())


def get(url: str, *, as_json: bool = False):
    """One request, never raising: the report must survive a dead source."""
    started = now_iso()
    try:
        response = requests.get(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
        body = response.text
        record = {'url': url, 'observed_at': started, 'finished_at': now_iso(),
                  'http_status': response.status_code, 'final_url': response.url,
                  'bytes': len(body or '')}
        if as_json:
            try:
                record['json'] = response.json()
            except ValueError:
                record['json'] = None
                record['error'] = 'response was not JSON'
        else:
            record['text'] = body
        return record
    except requests.RequestException as exc:
        return {'url': url, 'observed_at': started, 'finished_at': now_iso(),
                'http_status': None, 'error': f'{type(exc).__name__}: {exc}'}


def page_title(html: str) -> str:
    match = re.search(r'<title[^>]*>(.*?)</title>', html or '', re.S | re.I)
    return re.sub(r'\s+', ' ', match.group(1)).strip() if match else ''


def identity_check(match: dict, team_names: list[str]) -> dict:
    """The row's own Hotspawn match page: does it name both teams?"""
    url = match.get('source_url')
    if not url:
        return {'checked': False, 'reason': 'row publishes no Hotspawn match URL'}
    page = get(url)
    title = page_title(page.get('text') or '')
    folded = fold(title)
    names = [{'team': name, 'present_in_title': fold(name) in folded} for name in team_names]
    return {'checked': True, 'url': url, 'observed_at': page['observed_at'],
            'http_status': page.get('http_status'), 'title': title,
            'teams': names, 'both_present': all(n['present_in_title'] for n in names),
            'error': page.get('error')}


def _series_market(event: dict, team_names: list[str]) -> dict | None:
    """The event's *series winner* market, never a map or handicap market."""
    markets = event.get('markets') or []
    folded = [fold(name) for name in team_names]
    best = None
    for market in markets:
        label = ' '.join(str(market.get(key) or '') for key in
                         ('question', 'groupItemTitle', 'sportsMarketType', 'slug')).casefold()
        if 'map' in label or 'handicap' in label or 'total' in label:
            continue
        outcomes = market.get('outcomes')
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except ValueError:
                outcomes = None
        if not outcomes or len(outcomes) != 2:
            continue
        if all(any(name in fold(outcome) or fold(outcome) in name for name in folded)
               for outcome in outcomes):
            best = market
            if 'moneyline' in label or 'series' in label:
                return market
    return best


def _floats(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return None
    if not isinstance(value, list):
        return None
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None


def polymarket_reread(analysis: dict, team_names: list[str], pick_index) -> dict:
    """Re-read a Polymarket row from the event endpoint the row itself names."""
    api = analysis.get('source_api')
    if not api:
        return {'checked': False, 'reason': 'row publishes no Polymarket event endpoint'}
    page = get(api, as_json=True)
    event = page.get('json')
    out = {'checked': True, 'api': api, 'observed_at': page['observed_at'],
           'http_status': page.get('http_status'), 'error': page.get('error')}
    if not isinstance(event, dict):
        return out
    out['event_title'] = event.get('title')
    out['event_volume'] = event.get('volume')
    market = _series_market(event, team_names)
    if not market:
        out['error'] = 'no series-winner market with both teams in this event'
        return out
    outcomes = market.get('outcomes')
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except ValueError:
            outcomes = None
    prices = _floats(market.get('outcomePrices'))
    out.update({'market_question': market.get('question'), 'outcomes': outcomes,
                'outcome_prices': prices,
                'best_bid': market.get('bestBid'), 'best_ask': market.get('bestAsk'),
                'volume': market.get('volume')})
    if not outcomes or not prices or len(outcomes) != 2 or len(prices) != 2:
        out['error'] = 'series market published no two-outcome price pair'
        return out
    published = [float(x) for x in (analysis.get('probabilities') or [])]
    if len(published) != 2:
        out['error'] = 'published row has no two-team probability pair'
        return out
    folded_names = [fold(name) for name in team_names]
    rows, deltas = [], []
    for outcome, price in zip(outcomes, prices):
        key = fold(outcome)
        index = next((i for i, name in enumerate(folded_names)
                      if key and (key in name or name in key)), None)
        if index is None:
            rows.append({'outcome': outcome, 'price': price, 'matched_team': None})
            continue
        delta = price - published[index]
        deltas.append(abs(delta))
        rows.append({'outcome': outcome, 'price': price, 'matched_team': team_names[index],
                     'published': published[index], 'delta': round(delta, 4)})
    out['comparisons'] = rows
    out['max_abs_delta'] = round(max(deltas), 4) if deltas else None
    out['price_survives'] = bool(deltas) and len(deltas) == 2 and max(deltas) <= DRIFT_OK
    if pick_index in (0, 1) and all(row.get('price') is not None for row in rows):
        current = [row['price'] for row in rows]
        out['pick_still_favoured'] = current[pick_index] >= max(current)
    return out


def other_source_reread(analysis: dict) -> dict:
    """Fetch the cited URL for a non-Polymarket money row; status only."""
    url = analysis.get('source_url')
    if not url:
        return {'checked': False, 'reason': 'row publishes no source URL'}
    parsed = urlparse(url)
    if parsed.netloc.endswith('polymarket.com'):
        page = get(url)
        return {'checked': True, 'url': url, 'observed_at': page['observed_at'],
                'http_status': page.get('http_status'), 'bytes': page.get('bytes'),
                'error': page.get('error'), 'price_reverified': False,
                'note': 'Reachability only: this row publishes no Polymarket event endpoint, so its '
                        'price is not re-read here.'}
    page = get(url)
    body = page.get('text') or ''
    return {'checked': True, 'url': url, 'observed_at': page['observed_at'],
            'http_status': page.get('http_status'), 'bytes': page.get('bytes'),
            'error': page.get('error'),
            # A reachable page is not a re-verified price. Say so explicitly.
            'price_reverified': False,
            'note': 'Reachability only. This audit does not parse a price from a rendered '
                    'page, so the row\'s own quote record remains the price evidence.'}


def arithmetic(match: dict, analysis: dict) -> dict:
    probabilities = analysis.get('probabilities') or []
    pick_index = match.get('pick_index')
    team_names = [t.get('name') for t in match.get('teams') or []]
    try:
        values = [float(x) for x in probabilities]
    except (TypeError, ValueError):
        values = []
    total = round(sum(values), 6) if len(values) == 2 else None
    return {
        'probabilities': values,
        'sum': total,
        'sums_to_one': total is not None and abs(total - 1) <= 1e-3,
        'pick_index': pick_index,
        'pick_team': team_names[pick_index] if pick_index in (0, 1) and len(team_names) == 2 else None,
        'pick_is_larger': bool(len(values) == 2 and pick_index in (0, 1)
                               and values[pick_index] >= max(values)),
    }


def verdict(row: dict) -> str:
    if row['method'] not in MONEY_METHODS:
        return 'model_not_a_line'
    if not row['arithmetic']['sums_to_one'] or not row['arithmetic']['pick_is_larger']:
        return 'arithmetic_error'
    identity = row['identity']
    if identity.get('checked') and identity.get('http_status') == 200 and not identity.get('both_present'):
        return 'identity_mismatch'
    price = row['price']
    if not price.get('checked'):
        return 'source_unreadable'
    if price.get('http_status') != 200:
        return 'source_unreadable'
    if 'comparisons' in price:
        if price.get('pick_still_favoured') is False:
            return 'pick_disagrees'
        if price.get('price_survives'):
            return 'confirmed'
        return 'price_moved'
    # A reachable non-Polymarket surface: the row's quote record is the price
    # evidence, so this is a provenance confirmation, not a price re-read.
    return 'source_reachable'


BASE = 'https://buffedlizard55-lab.github.io/MaltaProj3/'


def fetch_published(out_dir: Path, base: str = BASE) -> Path:
    """Download exactly what the public site serves, and audit that copy.

    Auditing the deployment (not a fresh local collect) is the point: the brief
    asks whether the rows a reader can open are backed by the sources they name.
    """
    target = out_dir / 'published-snapshot'
    target.mkdir(parents=True, exist_ok=True)
    for name in ('latest.json', 'origination.json'):
        page = get(base + 'data/' + name, as_json=True)
        if page.get('http_status') != 200 or not isinstance(page.get('json'), (dict, list)):
            raise SystemExit(f'published {name} unreadable: {page.get("http_status")} {page.get("error")}')
        (target / name).write_text(json.dumps(page['json'], ensure_ascii=False, indent=2) + '\n')
    return target


def inventory_delta(data_dir: Path) -> dict:
    """Compare the audited snapshot's active ids with the live Hotspawn API.

    A live id the snapshot does not contain is a coverage gap at this
    observation time; it is recorded, never turned into a pick here.
    """
    latest = json.loads((data_dir / 'latest.json').read_text())
    api = next((m.get('source_api') for m in latest.get('matches') or [] if m.get('source_api')), None)
    if not api:
        return {'checked': False, 'reason': 'snapshot publishes no fixture API URL'}
    page = get(api, as_json=True)
    official = page.get('json')
    if not isinstance(official, list) or not official:
        return {'checked': False, 'api': api, 'observed_at': page['observed_at'],
                'http_status': page.get('http_status'), 'error': page.get('error')}
    snapshot_ids = [str(m['id']) for m in latest.get('matches') or []]
    official_ids = [str(m.get('id')) for m in official if isinstance(m, dict) and m.get('id')]
    active = [m for m in official if isinstance(m, dict)
              and str(m.get('id')) in {str(x['id']) for x in latest.get('matches') or []
                                       if x.get('availability') != 'past'}]
    missing = [m for m in official if isinstance(m, dict) and str(m.get('id')) not in set(snapshot_ids)]
    return {
        'checked': True, 'api': api, 'observed_at': page['observed_at'],
        'http_status': page.get('http_status'),
        'official_records': len(official_ids),
        'snapshot_records': len(snapshot_ids),
        'active_in_audited_snapshot': len(active),
        'not_in_snapshot': [
            {'id': str(m.get('id')), 'teams': [m.get('participants0_name'), m.get('participants1_name')],
             'competition': m.get('competition_name'),
             'starts_at': m.get('scheduled_start_time')}
            for m in missing],
        'note': 'Raw official inventory is an observation later than the published snapshot. A difference '
                'is a dated coverage finding, not proof that a row was missed at collection time.',
    }


def verify(data_dir: Path, out_dir: Path) -> dict:
    latest = json.loads((data_dir / 'latest.json').read_text())
    complete = json.loads((data_dir / 'origination.json').read_text())
    published = {str(m['id']): m for m in latest.get('matches') or []}
    started = now_iso()
    rows = []
    for match in complete.get('matches') or []:
        analysis = match.get('origination') or {}
        team_names = [t.get('name') for t in match.get('teams') or []]
        source = str(analysis.get('source') or '')
        method = str(analysis.get('method') or '')
        is_market_row = method in MONEY_METHODS
        row = {
            'id': str(match.get('id')),
            'teams': team_names,
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'availability': match.get('availability'),
            'method': method,
            'source': source,
            'source_url': analysis.get('source_url'),
            'published_probabilities': analysis.get('probabilities'),
            'published_pick_index': match.get('pick_index'),
            'published_observed_at': analysis.get('observed_at'),
            'hotspawn_url': match.get('source_url'),
            'in_inventory_snapshot': str(match.get('id')) in published,
        }
        row['arithmetic'] = arithmetic(match, analysis)
        row['identity'] = identity_check(match, team_names) if match.get('source_url') else {
            'checked': False, 'reason': 'row publishes no Hotspawn match URL'}
        if not is_market_row:
            row['price'] = {'checked': False, 'reason':
                            'research-model estimate: there is no published price to re-read'}
        elif 'polymarket' in f'{source} {analysis.get("source_url")}'.casefold() and analysis.get('source_api'):
            row['price'] = polymarket_reread(analysis, team_names, match.get('pick_index'))
        else:
            row['price'] = other_source_reread(analysis)
        row['verdict'] = verdict(row)
        rows.append(row)
    summary = {}
    for row in rows:
        summary[row['verdict']] = summary.get(row['verdict'], 0) + 1
    report = {
        'schema_version': 1,
        'session': 'arena-3a010437',
        'role': 'Independent re-read of every published row against the original source that row '
                'cites. Audit only: no probability, pick or alias is written or corrected here.',
        'started_at': started,
        'finished_at': now_iso(),
        'snapshot': {
            'inventory_generated_at': latest.get('generated_at'),
            'inventory_observed_at': latest.get('inventory_observed_at'),
            'complete_source_snapshot_at': complete.get('source_snapshot_at'),
            'active_rows': len(rows),
        },
        'thresholds': {'drift_ok': DRIFT_OK,
                       'note': 'A published observation is a snapshot; a later price within '
                               f'{DRIFT_OK:.2f} of it is reported as confirmed agreement, a larger '
                               'drift as a move. Only a price that now favours the other side is a conflict.'},
        'totals': summary,
        'rows': rows,
        'live_inventory': inventory_delta(data_dir),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (out_dir / 'verification.md').write_text(markdown(report) + '\n')
    return report


BAD = {'identity_mismatch', 'arithmetic_error', 'pick_disagrees', 'source_unreadable'}


def markdown(report: dict) -> str:
    s = report['snapshot']
    lines = [
        '# Independent verification of every published pick (session arena-3a010437)',
        '',
        f"Re-read started **{report['started_at']}** and finished **{report['finished_at']}** against the "
        f"snapshot collected at **{s['inventory_generated_at']}** ({s['active_rows']} active rows).",
        '',
        'Each row is compared with the original source that row itself cites. Nothing is corrected here: '
        'the deltas are published so a reader can see them.',
        '',
        '| Verdict | Rows |',
        '| --- | --- |',
    ]
    for verdict_name, count in sorted(report['totals'].items()):
        lines.append(f'| `{verdict_name}` | {count} |')
    lines += ['', '| # | Match | Method | Pick | Published | Re-read from the row\'s own source | Verdict |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for index, row in enumerate(report['rows'], 1):
        probs = row.get('published_probabilities') or []
        pick = row.get('published_pick_index')
        pick_team = row['teams'][pick] if pick in (0, 1) and len(row['teams']) == 2 else '—'
        published = ' / '.join(f'{float(p):.3f}' for p in probs) if len(probs) == 2 else '—'
        price = row.get('price') or {}
        if 'comparisons' in price:
            detail = '; '.join(
                f"{c['outcome']} {c.get('price')} ({c.get('delta'):+.3f} vs published)"
                if c.get('delta') is not None else f"{c['outcome']} {c.get('price')} (unmatched)"
                for c in price['comparisons'])
            detail += f" · Polymarket `{price.get('api')}` @ {price.get('observed_at')}"
        elif price.get('checked'):
            status = price.get('http_status') if price.get('http_status') is not None else 'no response'
            detail = f"{status} reachability only · {price.get('api') or price.get('url')} @ {price.get('observed_at')}"
            if price.get('error'):
                detail += f" · {price['error']}"
        else:
            detail = price.get('reason') or 'not checked'
        lines.append(f"| {index} | {row['teams'][0]} vs {row['teams'][1]} | {row['method'] or '—'} | "
                     f"{pick_team} | {published} | {detail} | `{row['verdict']}` |")
    conflicts = [r for r in report['rows'] if r['verdict'] in BAD]
    lines += ['', '## Flagged for review', '']
    if conflicts:
        for row in conflicts:
            lines.append(f"- **{row['teams'][0]} vs {row['teams'][1]}** (`{row['id']}`, `{row['verdict']}`) — "
                         f"{row.get('source_url')}")
    else:
        lines.append('No row conflicts with a re-read of its own source in this window. This is a dated '
                     'observation, not a guarantee: a research-model row has no price to re-read, and a '
                     'non-Polymarket money row is confirmed only as reachable.')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('data/research/3a010437'))
    parser.add_argument('--published', action='store_true',
                        help='audit the deployed site\'s own latest.json/origination.json instead of --data')
    parser.add_argument('--base', default=BASE, help='site base URL used with --published')
    args = parser.parse_args()
    data_dir = fetch_published(args.out, args.base) if args.published else args.data
    report = verify(data_dir, args.out)
    print(f"Verified {report['snapshot']['active_rows']} rows: {report['totals']}")
    for row in report['rows']:
        if row['verdict'] in BAD:
            print(f"::warning title=Row does not match its own source::"
                  f"{row['teams'][0]} vs {row['teams'][1]} ({row['id']}): {row['verdict']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
