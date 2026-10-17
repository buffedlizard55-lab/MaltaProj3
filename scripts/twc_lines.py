"""Day-4 TWC tournament-card lines originated from external first-party markets.

Thunderpick World Championship playoff fixtures are published by HLTV and by the
Hotspawn tournament pick'em, but they are *not* part of the weekly Hotspawn
scheduled-fixture inventory that the featured and researched pick pipelines join
against. Without this module those fixtures had no probability anywhere on the
site, which is exactly the gap the "every match needs a pick" requirement names.

The module only ever reads public first-party market data:

* Polymarket — the CS2 directory plus the paginated official CS2-tag event API
  (``scripts.sources.poly_index``), then the original Gamma event and both
  original CLOB order books for the selected full-series market.
* Kalshi — the public ``KXCS2GAME`` CS2 match-winner series (documented at
  https://docs.kalshi.com/api-reference/market/get-markets), parsed through the
  pipeline's existing contract rules so a start time must be stated by the
  contract text *and* encoded identically in the event ticker.

No value is inherited from Hotspawn, from HLTV fan votes, from a directory
percentage or from a previously saved number. A fixture whose providers do not
produce a valid two-sided book stays blank and carries the observed reason.
Probabilities are recomputed from the retained originals at render time, so a
tampered evidence file fails closed instead of publishing a number.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from scripts.domain import array, book_midpoint, finite, iso, name_key, normalize_pair, timestamp
from scripts.originate import aliased_series_market, kalshi_start, pair_join, resolve_name
from scripts.sources import SourceError, poly_index

EVENT = 'Thunderpick World Championship 2026'
POLY_EVENTS = 'https://gamma-api.polymarket.com/events/'
CLOB_BOOK = 'https://clob.polymarket.com/book?token_id='
POLY_DIRECTORY = 'https://polymarket.com/esports/cs2'
KALSHI_EVENTS = 'https://api.elections.kalshi.com/trade/v2'
KALSHI_API = 'https://api.elections.kalshi.com/trade-api/v2/events'
KALSHI_PAGE = 'https://kalshi.com/markets/kxcs2game/counterstrike-2-game'
KALSHI_SERIES = 'KXCS2GAME'
DOCS = 'https://docs.kalshi.com/api-reference/market/get-markets'
REPORT = Path('evidence/twc-day4-lines.json')
MAX_SPREAD = 0.12
MAX_KALSHI_PAGES = 5
HISTORY_READS = 6  # Earlier pipeline reads retained for verified line movement.
POLICY = ('External first-party market data only. Every fixture joins on exact team names (or a competition-scoped, '
          'evidence-linked alias) and an exact scheduled start; both sides of the selected full-series market must '
          'publish a two-sided book no wider than 0.12; in-play and past-start observations are rejected. The '
          'published pair is the median across the independent providers that validated, never a directory '
          'percentage, a fan vote, a Hotspawn figure or a previously stored estimate.')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def fixtures(rows: list, day: str) -> list:
    """BC-verified HLTV fixtures for one day, as joinable fixture records.

    Only the retained facts are used: both team names and the start time that
    HLTV itself published. A finished series is never priced as an upcoming one.
    """
    out = []
    for row in rows or []:
        facts = row.get('facts') or {}
        teams = [t for t in (facts.get('teams') or []) if isinstance(t, str) and t.strip()]
        start = facts.get('starts_at')
        url = row.get('source_url') or ''
        if len(teams) != 2 or len({name_key(t) for t in teams}) != 2:
            continue
        if not isinstance(start, str) or not start.startswith(day) or facts.get('finished'):
            continue
        parts = url.rstrip('/').split('/')
        if len(parts) < 5 or not parts[4].isdigit():
            continue
        out.append({'id': 'twc-' + parts[4], 'teams': [{'name': teams[0]}, {'name': teams[1]}],
                    'starts_at': start, 'competition': EVENT, 'source_url': url,
                    'hltv_match_id': parts[4], 'observed_at': row.get('observed_at')})
    return out


def fixture_key(fixture: dict) -> tuple:
    return (frozenset(name_key(t['name']) for t in fixture['teams']), fixture.get('starts_at'))


# ---------------------------------------------------------------------------
# Provider re-derivation (pure: original payloads in, probability pair out)
# ---------------------------------------------------------------------------

def polymarket_quote(event: dict, books: list, fixture: dict, registry: dict, now: datetime) -> tuple[dict | None, str]:
    """Re-derive one Polymarket pair from the original event and both books."""
    market, reason = aliased_series_market(event, fixture, registry, now)
    if market is None:
        return None, reason or 'No unique open full-series market for this fixture'
    tokens = array(market.get('clobTokenIds'))
    if len(tokens) != 2:
        return None, 'Series market does not publish exactly two outcome tokens'
    by_token = {str(b.get('asset_id')): b for b in books or []}
    quotes = []
    for token in tokens:
        book = by_token.get(str(token))
        if book is None:
            return None, 'One or both original order books were not retained'
        try:
            quotes.append(book_midpoint(book, str(token), market['conditionId'], now))
        except ValueError as exc:
            return None, 'Order book rejected by the published contract: ' + str(exc)
    names = array(market.get('outcomes'))
    canonical = [resolve_name(str(n), registry, fixture.get('competition'))[0] for n in names]
    wanted = [name_key(t['name']) for t in fixture['teams']]
    if len(set(canonical)) != 2 or set(canonical) != set(wanted):
        return None, 'Outcome names do not map onto the fixture teams'
    by_name = dict(zip(canonical, quotes))
    ordered = [by_name[key] for key in wanted]
    try:
        probs = normalize_pair(*(q['midpoint'] for q in ordered))
    except ValueError as exc:
        return None, 'Normalization failed: ' + str(exc)
    updated = max((timestamp(by_token[str(t)].get('timestamp')) for t in tokens), default=None)
    listed = timestamp(market.get('createdAt') or market.get('startDate') or event.get('creationDate')
                       or event.get('startDate'))
    return {'provider': 'Polymarket', 'family': 'market', 'probabilities': probs,
            'bid': [q['bid'] for q in ordered], 'ask': [q['ask'] for q in ordered],
            'source_url': 'https://polymarket.com/event/' + str(event.get('slug')),
            'api_url': POLY_EVENTS + str(event.get('id')),
            'event_id': str(event.get('id')), 'market_id': str(market.get('id')),
            'source_outcomes': [str(n) for n in names],
            'volume': finite(market.get('volumeNum', market.get('volume'))),
            'liquidity': finite(market.get('liquidityNum', market.get('liquidity'))),
            'activity': {'listed_at': iso(listed) if listed else None,
                         'book_updated_at': iso(updated) if updated else None,
                         'volume': finite(market.get('volumeNum', market.get('volume'))),
                         'liquidity': finite(market.get('liquidityNum', market.get('liquidity'))),
                         'last_price': None,
                         'note': 'Order books are the priced evidence; the directory price is never used.'}}, ''


def kalshi_quote(event: dict, fixture: dict, registry: dict, observed_at, now: datetime) -> tuple[dict | None, str]:
    """Re-derive one Kalshi pair from the original nested-markets event."""
    if event.get('series_ticker') != KALSHI_SERIES or (event.get('product_metadata') or {}).get('competition') != 'CS2':
        return None, 'Not a CS2 match-winner series event'
    markets = event.get('markets') or []
    if event.get('mutually_exclusive') is not True or len(markets) != 2:
        return None, 'Kalshi event does not publish exactly two mutually exclusive outcomes'
    start = kalshi_start(event)
    if start is None:
        return None, 'Scheduled start could not be verified from the contract rules and ticker'
    names = [m.get('yes_sub_title') for m in markets]
    placed, _used, status = pair_join(names, start, fixture, registry)
    if status != 'matched' or not placed:
        return None, 'Provider names/start do not join the fixture (' + status + ')'
    canonical = placed[0]  # pair_join returns [canonical names, requested keys]
    when = timestamp(observed_at)
    if when is None or timestamp(start) is None or timestamp(start) <= when:
        return None, 'Observation is not prematch'
    quotes, market_by_name = {}, {}
    for name, market in zip(canonical, markets):
        if market.get('status') != 'active':
            return None, 'A Kalshi outcome market is not active'
        bid, ask = finite(market.get('yes_bid_dollars')), finite(market.get('yes_ask_dollars'))
        if bid is None or ask is None or not 0 < bid < ask < 1:
            return None, 'Kalshi yes book is one-sided or outside 0/1'
        if ask - bid > MAX_SPREAD + 1e-9:
            return None, 'Kalshi yes book is wider than the 12-cent ceiling'
        quotes[name] = {'bid': bid, 'ask': ask, 'midpoint': (bid + ask) / 2}
        market_by_name[name] = market
    wanted = [name_key(t['name']) for t in fixture['teams']]
    if set(quotes) != set(wanted):
        return None, 'Kalshi outcomes do not map onto the fixture teams'
    ordered = [quotes[key] for key in wanted]
    ordered_markets = [market_by_name[key] for key in wanted]
    try:
        probs = normalize_pair(*(q['midpoint'] for q in ordered))
    except ValueError as exc:
        return None, 'Normalization failed: ' + str(exc)
    ticker = str(event.get('event_ticker'))
    updated, opened = timestamp(markets[0].get('updated_time')), timestamp(markets[0].get('open_time'))
    return {'provider': 'Kalshi', 'family': 'market', 'probabilities': probs,
            'bid': [q['bid'] for q in ordered], 'ask': [q['ask'] for q in ordered],
            'source_url': KALSHI_PAGE + '/' + ticker.lower(), 'api_url': KALSHI_API + '/' + ticker,
            'event_id': ticker, 'market_tickers': [str(m.get('ticker')) for m in markets],
            'source_outcomes': [str(n) for n in names],
            'activity': {'listed_at': iso(timestamp(markets[0].get('created_time'))) if timestamp(markets[0].get('created_time')) else None,
                         'opened_at': iso(opened) if opened else None,
                         'book_updated_at': iso(updated) if updated else None,
                         # Kalshi publishes the book's own update time, so "has this market
                         # repriced since it opened" is answerable from the retained original.
                         'changed_since_open': None if not (updated and opened) else bool(updated > opened),
                         'last_price': [finite(m.get('last_price_dollars')) for m in ordered_markets],
                         'open_interest': [finite(m.get('open_interest_fp')) for m in ordered_markets],
                         'volume': [finite(m.get('volume_fp')) for m in ordered_markets],
                         'note': 'Book and last-trade values are provider-reported; the midpoints are the priced evidence.'}}, ''


def median_pair(pairs: list) -> list | None:
    """Median across independent providers, one vote each; then normalized."""
    pairs = [p for p in pairs if isinstance(p, (list, tuple)) and len(p) == 2]
    if not pairs:
        return None
    try:
        return normalize_pair(median(p[0] for p in pairs), median(p[1] for p in pairs))
    except ValueError:
        return None


def analyse(providers: list, fixture: dict) -> dict:
    """Combine validated provider pairs into one labelled estimate or a blank."""
    usable = [p for p in providers if p.get('quote')]
    probs = median_pair([p['quote']['probabilities'] for p in usable])
    row = {'fixture_id': fixture['id'], 'teams': [t['name'] for t in fixture['teams']],
           'starts_at': fixture['starts_at'], 'source_url': fixture.get('source_url'),
           'hltv_match_id': fixture.get('hltv_match_id'), 'probabilities': probs,
           'providers': [{'provider': p['quote']['provider'], 'probabilities': p['quote']['probabilities'],
                          'bid': p['quote']['bid'], 'ask': p['quote']['ask'],
                          'source_url': p['quote']['source_url'], 'api_url': p['quote']['api_url'],
                          'event_id': p['quote']['event_id'], 'observed_at': p['observed_at'],
                          'activity': p['quote'].get('activity')}
                         for p in usable],
           'attempts': [{'provider': p['provider'], 'status': p['status'], 'reason': p['reason'],
                         'source_url': p['source_url'], 'observed_at': p['observed_at']} for p in providers],
           'limitations': []}
    if probs is None:
        row['method'] = None
        row['label'] = 'Unresolved — no validated two-sided external line'
        row['observed_at'] = None
        row['pick_index'] = None
        row['limitations'] = ['No provider produced a valid two-sided full-series book inside the published '
                              'contract. What each provider actually returned is listed above; a source failure is '
                              'not evidence that no market exists and no value is filled in.']
        return row
    observed = max(p['observed_at'] for p in usable if p.get('observed_at'))
    row['method'] = 'market'
    row['label'] = ('Tournament market line — ' + ('/'.join(sorted({p['quote']['provider'] for p in usable}))
                                                   + (' consensus' if len(usable) > 1 else ', single independent source')))
    row['observed_at'] = observed
    row['pick_index'] = None if abs(probs[0] - probs[1]) < 1e-8 else (0 if probs[0] > probs[1] else 1)
    if len(row['providers']) < 2:
        row['limitations'].append('One independent provider only; this is not a multi-book consensus.')
    row['limitations'].append('Midpoints are not guaranteed execution prices; fees and exchange rules are excluded.')
    return row


# ---------------------------------------------------------------------------
# Collection (runner side)
# ---------------------------------------------------------------------------

def _record_evidence(client, labels: list) -> list:
    """Reference the exact saved responses this run used, with their hashes.

    ``Client.fetch`` hashes the provider's raw HTTP bytes, while ``Client.json``
    retains a deterministic JSON serialization for replay. Those byte streams
    are legitimately different (whitespace alone is enough), so the replay hash
    must cover the file that replay actually reads. The raw-response hash stays
    in the request manifest and is also retained here as separate provenance.
    """
    manifest = {entry['id']: entry for entry in client.manifest}
    out = []
    for label in labels:
        entry = manifest.get(label) or {}
        if entry.get('status') != 'ok' or not entry.get('evidence'):
            continue
        saved = client.evidence / Path(entry['evidence']).name
        if not saved.is_file():
            continue
        out.append({'label': label, 'url': entry.get('url'), 'observed_at': entry.get('observed_at'),
                    'file': 'evidence/' + saved.name,
                    'sha256': hashlib.sha256(saved.read_bytes()).hexdigest(),
                    'response_sha256': entry.get('response_sha256')})
    return out


def _previous_reads(client) -> list:
    """Earlier pipeline reads, carried forward so movement stays verifiable."""
    path = client.evidence / 'twc-day4-lines.json'
    if not path.exists():
        return []
    try:
        previous = json.loads(path.read_text())
    except ValueError:
        return []
    out = list(previous.get('history') or [])[-HISTORY_READS:]
    if previous.get('records'):
        out.append({'observed_at': previous.get('observed_at'), 'records': previous.get('records')})
    return out[-HISTORY_READS:]


def collect(client, research_rows: list, registry: dict, day: str, now: datetime) -> dict:
    """Discover, validate and retain external Day-4 lines for TWC fixtures."""
    targets = fixtures(research_rows, day)
    stamp = now.strftime('%Y%m%dT%H%M')
    history = _previous_reads(client)
    games, poly_health = ([], None)
    if targets:
        try:
            games, poly_health = poly_index(client)
        except (SourceError, ValueError) as exc:
            poly_health = {'status': 'error', 'name': 'Polymarket CS2', 'url': POLY_DIRECTORY,
                           'detail': str(exc)[:300]}
    records = []
    for fixture in targets:
        providers = []
        candidates = [g for g in games
                      if pair_join([g.get('homeName', ''), g.get('awayName', '')], g.get('startTime'),
                                   fixture, registry)[2] == 'matched']
        event_ids = {str(g.get('id')) for g in candidates}
        if len(event_ids) == 1:
            event_id = next(iter(event_ids))
            labels = ['twc-day4-poly-event-' + event_id + '-' + stamp]
            try:
                event, req = client.json(POLY_EVENTS + event_id, labels[0])
            except SourceError as exc:
                event = None
                providers.append({'provider': 'Polymarket', 'status': 'unavailable', 'reason': str(exc)[:300],
                                  'source_url': POLY_DIRECTORY, 'observed_at': iso(now), 'quote': None})
            if event is not None:
                market, why = aliased_series_market(event, fixture, registry, now)
                tokens = array(market.get('clobTokenIds')) if market else []
                books = []
                for index, token in enumerate(tokens):
                    label = 'twc-day4-poly-book-' + event_id + '-' + str(index) + '-' + stamp
                    try:
                        book, _ = client.json(CLOB_BOOK + str(token), label)
                    except SourceError:
                        book = None
                    if book is None:
                        books = []
                        break
                    books.append(book)
                    labels.append(label)
                quote, reason = (polymarket_quote(event, books, fixture, registry, now)
                                 if market and len(books) == 2 else (None, why or 'Order books unavailable'))
                providers.append({'provider': 'Polymarket', 'status': 'resolved' if quote else 'unresolved',
                                  'reason': reason, 'source_url': 'https://polymarket.com/event/' + str(event.get('slug')),
                                  'observed_at': req['observed_at'], 'quote': quote,
                                  'evidence': _record_evidence(client, labels),
                                  'event_id': event_id, 'market_id': str(market.get('id')) if market else None,
                                  'token_ids': [str(t) for t in tokens],
                                  'condition_id': market.get('conditionId') if market else None,
                                  'outcomes': [str(x) for x in array(market.get('outcomes'))] if market else []})
        else:
            providers.append({'provider': 'Polymarket', 'status': 'unresolved',
                              'reason': ('No unique CS2 event for this pair and start time in the public directory '
                                         'and paginated CS2-tag events' if not candidates
                                         else 'More than one CS2 event matches this pair and start time'),
                              'source_url': POLY_DIRECTORY, 'observed_at': iso(now), 'quote': None})
        kalshi, kalshi_status = _collect_kalshi(client, fixture, registry, now, stamp)
        providers.append(kalshi)
        records.append({'fixture': {k: fixture[k] for k in ('id', 'teams', 'starts_at', 'source_url', 'hltv_match_id')},
                        'providers': providers, 'kalshi_pages': kalshi_status})
    report = {'schema_version': 1, 'policy': POLICY, 'event': EVENT, 'day': day, 'observed_at': iso(now),
              'polymarket': poly_health, 'records': records, 'history': history,
              'request_manifest': list(client.manifest)}
    client.save('twc-day4-lines', report)
    return report


def _collect_kalshi(client, fixture: dict, registry: dict, now: datetime, stamp: str = '') -> tuple[dict, int | None]:
    labels, pages, cursor = [], 0, None
    events = []
    while pages < MAX_KALSHI_PAGES:
        suffix = '' if cursor is None else '&cursor=' + str(cursor)
        url = (KALSHI_API + '?series_ticker=' + KALSHI_SERIES + '&status=open&with_nested_markets=true&limit=200' + suffix)
        label = 'twc-day4-kalshi-page-' + str(pages) + ('-' + stamp if stamp else '')
        try:
            body, _ = client.json(url, label)
        except SourceError as exc:
            return ({'provider': 'Kalshi', 'status': 'unavailable', 'reason': str(exc)[:300],
                     'source_url': KALSHI_PAGE, 'observed_at': iso(now), 'quote': None}, pages), pages
        labels.append(label)
        pages += 1
        events.extend(body.get('events') or [])
        cursor = body.get('cursor') or None
        if not cursor:
            break
    joined = [e for e in events
              if pair_join([m.get('yes_sub_title') for m in (e.get('markets') or [])][:2], kalshi_start(e),
                           fixture, registry)[2] == 'matched'] if len(events) else []
    joined = [e for e in joined if len(e.get('markets') or []) == 2]
    if len(joined) != 1:
        return ({'provider': 'Kalshi', 'status': 'unresolved',
                 'reason': ('No Kalshi CS2 match-winner event joins this pair and start time' if not joined
                            else 'More than one Kalshi event joins this pair and start time'),
                 'source_url': KALSHI_PAGE, 'observed_at': iso(now), 'quote': None,
                 'evidence': _record_evidence(client, labels)}, pages), pages
    event = joined[0]
    observed = max((client_manifest_time(client, label) for label in labels), default=iso(now))
    quote, reason = kalshi_quote(event, fixture, registry, observed, now)
    return ({'provider': 'Kalshi', 'status': 'resolved' if quote else 'unresolved', 'reason': reason,
             'source_url': KALSHI_PAGE + '/' + str(event.get('event_ticker')).lower(),
             'observed_at': observed, 'quote': quote, 'event_id': str(event.get('event_ticker')),
             'market_tickers': [str(m.get('ticker')) for m in event.get('markets') or []],
             'evidence': _record_evidence(client, labels)}, pages), pages


def client_manifest_time(client, label: str):
    for entry in client.manifest:
        if entry.get('id') == label and entry.get('observed_at'):
            return entry['observed_at']
    return None


# ---------------------------------------------------------------------------
# Replay (build side)
# ---------------------------------------------------------------------------

def _evidence_path(folder: Path, name: str) -> Path:
    """Resolve a retained evidence file, refusing anything outside its folder."""
    path = (folder / name).resolve()
    root = folder.resolve()
    if path == root or root not in path.parents:
        raise ValueError('TWC line evidence path escapes its research folder')
    return path


def _replay_record(record: dict, folder: Path, registry: dict, now: datetime) -> dict:
    """Re-derive one collected fixture from its hash-verified originals."""
    fixture = {'id': record['fixture']['id'], 'teams': [{'name': n} for n in record['fixture']['teams']],
               'starts_at': record['fixture']['starts_at'], 'competition': EVENT,
               'source_url': record['fixture'].get('source_url'),
               'hltv_match_id': record['fixture'].get('hltv_match_id')}
    providers = []
    for provider in record.get('providers') or []:
        payloads = {}
        for item in provider.get('evidence') or []:
            path = _evidence_path(folder, item['file'])
            if not path.exists():
                raise ValueError('TWC line evidence missing: ' + item['file'])
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != item.get('sha256'):
                raise ValueError('TWC line evidence hash mismatch: ' + item['file'])
            payloads[item['label']] = json.loads(raw.decode())
        quote, reason = None, provider.get('reason')
        if provider['provider'] == 'Polymarket' and payloads:
            event = next((v for k, v in payloads.items() if k.startswith('twc-day4-poly-event-')), None)
            books = [v for k, v in sorted(payloads.items()) if k.startswith('twc-day4-poly-book-')]
            if event is not None:
                quote, reason = polymarket_quote(event, books, fixture, registry, now)
        if provider['provider'] == 'Kalshi' and payloads:
            events = [e for page in payloads.values() for e in (page.get('events') or [])]
            joined = [e for e in events if str(e.get('event_ticker')) == str(provider.get('event_id'))]
            if len(joined) == 1:
                quote, reason = kalshi_quote(joined[0], fixture, registry, provider.get('observed_at'), now)
            elif not joined:
                reason = 'The retained Kalshi page no longer contains the selected event'
        providers.append({'provider': provider['provider'], 'status': 'resolved' if quote else 'unresolved',
                          'reason': reason, 'source_url': provider.get('source_url'),
                          'observed_at': provider.get('observed_at'), 'quote': quote})
    return analyse(providers, fixture)


def _movement(row: dict, earlier: dict | None) -> dict | None:
    """Point change between two independently replayed reads of one fixture."""
    if not earlier or not row.get('probabilities') or not earlier.get('probabilities'):
        return None
    if row['fixture_id'] != earlier.get('fixture_id'):
        return None
    before, after = earlier['probabilities'], row['probabilities']
    delta = [after[i] - before[i] for i in (0, 1)]
    return {'from': earlier.get('observed_at'), 'before': before, 'delta': delta,
            'points': [round(d * 100, 1) for d in delta],
            'providers_before': [p['provider'] for p in earlier.get('providers') or []],
            'label': 'Change against the previous validated read of the same fixture.'}


def load(source: Path, now: datetime, registry: dict | None = None) -> dict:
    """Replay retained originals and return validated Day-4 lines.

    Stored probabilities are never trusted: each provider is recomputed from the
    hash-verified original response, and any mismatch raises instead of
    publishing. A missing report returns an empty, explicitly unresolved result.
    Earlier reads are replayed too, so published line movement is a change
    between two verified observations rather than a remembered number; a read
    whose originals are gone is dropped instead of being trusted.
    """
    folder = source / 'research/twc-current'
    report_path = folder / REPORT
    if not report_path.exists():
        folder = source / 'research/138f48b7/twc-current'
        report_path = folder / REPORT
    empty = {'schema_version': 1, 'available': False, 'day': None, 'observed_at': None,
             'matches': [], 'reasons': {}, 'report_path': None, 'policy': POLICY}
    if not report_path.exists():
        return empty
    report = json.loads(report_path.read_text())
    # Evidence paths are stored relative to the research folder, which is the
    # report's own folder minus the report's relative path.
    folder = report_path.parent
    for _ in range(len(REPORT.parts) - 1):
        folder = folder.parent
    registry = registry if registry is not None else _registry()
    matches, reasons = [], {}
    for record in report.get('records') or []:
        row = _replay_record(record, folder, registry, now)
        matches.append(row)
        if row['probabilities'] is None:
            reasons[' vs '.join(row['teams'])] = [a for a in row['attempts']]
    earlier, dropped = [], 0
    for read in report.get('history') or []:
        try:
            rows = [_replay_record(record, folder, registry, now) for record in read.get('records') or []]
        except ValueError:
            dropped += 1  # Originals already rotated away: never trust a remembered number.
            continue
        if rows:
            earlier.append(rows)
    for row in matches:
        prior = next((candidate for rows in reversed(earlier) for candidate in rows
                      if candidate['fixture_id'] == row['fixture_id'] and candidate.get('probabilities')), None)
        row['movement'] = _movement(row, prior)
        if row['movement'] is None:
            row['movement_note'] = ('No earlier validated read of this fixture is retained yet; movement is published '
                                    'once a second observation of the same book is verified.')
    return {'schema_version': report.get('schema_version', 1), 'available': True, 'day': report.get('day'),
            'observed_at': report.get('observed_at'), 'matches': matches, 'reasons': reasons,
            'report_path': _relative_report(source, report_path), 'policy': POLICY,
            'earlier_reads': len(earlier), 'read_sources': [r.get('observed_at') for r in report.get('history') or []],
            'unverifiable_reads': dropped}


_REGISTRY: dict | None = None


def _registry() -> dict:
    """The reviewed alias registry, loaded once for replays."""
    global _REGISTRY
    if _REGISTRY is None:
        path = Path('data/origination/aliases.json')
        _REGISTRY = json.loads(path.read_text()) if path.exists() else {'aliases': []}
    return _REGISTRY


def _relative_report(source: Path, report_path: Path) -> str:
    try:
        return report_path.resolve().relative_to(source.resolve()).as_posix()
    except ValueError:
        return report_path.as_posix()


def for_fixture(lines: dict, teams: list, starts_at) -> dict | None:
    """The validated line for an exact team pair and start, or None."""
    key = (frozenset(name_key(t) for t in teams), starts_at)
    for row in lines.get('matches') or []:
        if fixture_key({'teams': [{'name': n} for n in row['teams']], 'starts_at': row['starts_at']}) == key:
            return row
    return None


def underdog(line: dict, floor: float = 0.30) -> dict | None:
    """The published underdog screen: money-backed, >= floor, unlocked."""
    if not line or line.get('pick_index') is None or line.get('method') not in {'market', 'bookmaker', 'consensus'}:
        return None
    dog = 1 - line['pick_index']
    probability = line['probabilities'][dog]
    return {'team': line['teams'][dog], 'probability': probability,
            'passes_floor': bool(probability >= floor),
            'cost_per_base_point': round(line['probabilities'][line['pick_index']] - probability, 8)}
