"""Session arena-b3e91409: turn the captured live evidence into one documented, source-linked line per open fixture.

Run after `python -m scripts.b3e91409_probe` on the same runner:

    python -m scripts.b3e91409_research

Inputs (all first-party, already archived with URL + UTC time + SHA-256 by the probe):
  data/research/b3e91409/live/hotspawn-fixtures-api.json
  data/research/b3e91409/live/polymarket-events.json
  data/research/b3e91409/live/thunderpick-matches.json
  data/research/b3e91409/live/hltv-cards.json
  data/research/b3e91409/live/hltv-ranking.json
  data/research/b3e91409/live/valve-standings.md

Outputs:
  data/research/b3e91409/live/analysis.json   one record per open fixture, with every input and formula
  data/research/b3e91409/live/summary.md      the same, human-readable, for manual review

Rules this module enforces (they are the brief's rules, not a model choice):
  * identity is exact Unicode/case/whitespace-equivalent team naming AND a start time within 60 s;
    a near miss is recorded with its reason, never joined;
  * a probability is only ever derived from an observed two-way price (exchange midpoint or
    de-vigged bookmaker pair) or from published rating points with the formula printed;
  * nothing is filled in when no source supports it: the row keeps its blank and names the blockers;
  * Hotspawn's community "% picked" and HLTV fan votes are never read as inputs;
  * every emitted number carries the exact source URL and its UTC observation time.
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests

LIVE = Path('data/research/b3e91409/live')
CLOB_BOOK = 'https://clob.polymarket.com/book?token_id='
START_TOLERANCE_SEC = 60
MAX_EXCHANGE_SPREAD = 0.10          # per side, from best bid/ask in the order book
MAX_BOOK_MARGIN = 1.35              # paired decimal odds margin ceiling
MIN_BOOK_MARGIN = 0.85


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def key(name):
    text = unicodedata.normalize('NFKC', name or '').casefold()
    return re.sub(r'\s+', ' ', text).strip()


def parse_time(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        # Hotspawn publishes epoch milliseconds; a seconds value is accepted but never rescaled twice.
        number = float(value)
        if number > 10**11:
            number /= 1000
        return datetime.fromtimestamp(number, timezone.utc)
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


class Book:
    """One public CLOB order book, reduced to the two numbers anyone can check on the page."""

    def __init__(self, token, response, entry):
        self.token = token
        self.entry = entry
        self.book = response or {}

    def side(self):
        bids = [(float(x['price']), float(x.get('size') or 0)) for x in self.book.get('bids') or []]
        asks = [(float(x['price']), float(x.get('size') or 0)) for x in self.book.get('asks') or []]
        bid = max(bids)[0] if bids else None
        ask = min(asks)[0] if asks else None
        return bid, ask


def fetch_book(session, token, fixture_id, index, manifest):
    entry = {'url': CLOB_BOOK + str(token), 'observed_at': iso(now()), 'http_status': None, 'status': 'error'}
    wait = 0.25 - (time.monotonic() - manifest.get('_last', 0))
    if wait > 0:
        time.sleep(wait)
    manifest['_last'] = time.monotonic()
    try:
        response = session.get(CLOB_BOOK + str(token), timeout=(15, 45))
        entry['http_status'] = response.status_code
        response.raise_for_status()
        body = response.json()
        entry['status'] = 'ok'
        manifest.setdefault('books', []).append(dict(entry, asset_id=str(token), fixture=fixture_id))
        return Book(token, body, entry)
    except (requests.RequestException, ValueError) as exc:
        entry['error'] = str(exc)[:300]
        manifest.setdefault('books', []).append(dict(entry, asset_id=str(token), fixture=fixture_id))
        return Book(token, None, entry)


def no_vig(home, away):
    if not home or not away:
        return None, 'two decimal odds are required'
    try:
        home, away = float(home), float(away)
    except (TypeError, ValueError):
        return None, 'decimal odds are not numeric'
    if home <= 1 or away <= 1:
        return None, 'decimal odds must be greater than 1'
    implied = [1 / home, 1 / away]
    if not MIN_BOOK_MARGIN <= sum(implied) <= MAX_BOOK_MARGIN:
        return None, f'paired margin {sum(implied):.4f} is outside {MIN_BOOK_MARGIN}-{MAX_BOOK_MARGIN}'
    total = sum(implied)
    return [implied[0] / total, implied[1] / total], ''


def rank_model(home_points, away_points):
    """Elo-style logistic on HLTV's published points, exactly as printed in the dossier."""
    if home_points is None or away_points is None:
        return None
    p = 1 / (1 + 10 ** ((away_points - home_points) / 400))
    return [p, 1 - p]


def valve_table():
    path = LIVE / 'valve-standings.md'
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding='utf-8').splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 4 and re.fullmatch(r'\d+', cells[0] or ''):
            rows.append({'standing': int(cells[0]), 'team': cells[1], 'points': cells[2]})
    return rows


def main():
    reference = now()
    evidence = {
        'api': json.loads((LIVE / 'hotspawn-fixtures-api.json').read_text(encoding='utf-8')),
        'polymarket': json.loads((LIVE / 'polymarket-events.json').read_text(encoding='utf-8')),
        'thunderpick': json.loads((LIVE / 'thunderpick-matches.json').read_text(encoding='utf-8'))['data']['upcoming'],
        'hltv': json.loads((LIVE / 'hltv-cards.json').read_text(encoding='utf-8')) if (LIVE / 'hltv-cards.json').exists() else [],
        'ranking': json.loads((LIVE / 'hltv-ranking.json').read_text(encoding='utf-8')) if (LIVE / 'hltv-ranking.json').exists() else [],
        'valve': valve_table(),
    }
    sources_meta = json.loads((LIVE / 'sources.json').read_text(encoding='utf-8'))
    session = requests.Session()
    session.headers.update({'User-Agent': 'HotspawnCS2Coverage/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)',
                            'Accept': 'application/json'})
    manifest = {'observed_at': iso(reference), 'books': []}

    # Open fixtures come from the archived Hotspawn array, not from the site.
    fixtures = []
    for raw in evidence['api']:
        if raw.get('sport_alias') != 'cs2':
            continue
        start = parse_time(int(raw['scheduled_start_time']))
        if not start or start <= reference:
            continue
        fixtures.append({'id': str(raw['id']), 'teams': [raw['participants0_name'], raw['participants1_name']],
                         'competition': raw.get('competition_name'), 'tier': raw.get('tier'),
                         'starts_at': iso(start), 'best_of': raw.get('best_of'), '_start': start})
    fixtures.sort(key=lambda f: (f['starts_at'], f['id']))

    deduped_hltv, seen_ids = [], set()
    for card in evidence['hltv']:
        if card.get('match_id') in seen_ids:
            continue
        seen_ids.add(card.get('match_id'))
        deduped_hltv.append(card)
    evidence['hltv'] = deduped_hltv

    ranking_by_name = {}
    for row in evidence['ranking']:
        ranking_by_name.setdefault(key(row['team']), row)
    valve_by_name = {}
    for row in evidence['valve']:
        valve_by_name.setdefault(key(row['team']), []).append(row)

    records = []
    for fixture in fixtures:
        a, b = fixture['teams']
        wanted = {key(a), key(b)}
        research = []
        quotes = []
        market_candidate = None

        # ---- Polymarket: the full-series moneyline only, exact outcome names, start within 60 s.
        near = []
        for event in evidence['polymarket']:
            for market in event.get('markets') or []:
                try:
                    outcomes = json.loads(market.get('outcomes') or '[]')
                except ValueError:
                    continue
                if not (isinstance(outcomes, list) and len(outcomes) == 2 and {key(x) for x in outcomes} == wanted):
                    continue
                start = parse_time(market.get('gameStartTime'))
                delta = int((start - fixture['_start']).total_seconds()) if start else None
                series = market.get('sportsMarketType') == 'moneyline'
                item = {'event_id': event['id'], 'slug': event['slug'], 'title': event['title'],
                        'market_id': market['id'], 'question': market['question'],
                        'sports_market_type': market.get('sportsMarketType'),
                        'game_start_time': market.get('gameStartTime'), 'start_delta_sec': delta,
                        'outcomes': outcomes, 'outcome_prices': market.get('outcomePrices'),
                        'best_bid': market.get('bestBid'), 'best_ask': market.get('bestAsk'),
                        'spread': market.get('spread'),
                        'url': 'https://polymarket.com/event/' + str(event.get('slug'))}
                if series and delta is not None and abs(delta) <= START_TOLERANCE_SEC and market_candidate is None:
                    market_candidate = dict(item, tokens=json.loads(market.get('clobTokenIds') or '[]'))
                else:
                    item['rejected_because'] = ('not the full-series moneyline market' if not series
                                                else ('start delta outside 60 s' if delta is not None
                                                      else 'no published game start time'))
                    near.append(item)
        research.append({'stage': 'Polymarket series moneyline', 'url': 'https://polymarket.com/esports/cs2',
                         'status': 'resolved' if market_candidate else 'unresolved',
                         'detail': (f"event {market_candidate['event_id']} · market {market_candidate['market_id']} · "
                                    f"start delta {market_candidate['start_delta_sec']} s" if market_candidate
                                    else 'no event carries both exact team names in a full-series moneyline market with a start within 60 s'),
                         'near_misses': near[:6]})
        if market_candidate:
            tokens = market_candidate.get('tokens') or []
            if len(tokens) == 2:
                books = [fetch_book(session, token, fixture['id'], i, manifest) for i, token in enumerate(tokens)]
                sides = [book.side() for book in books]
                if all(bid is not None and ask is not None for bid, ask in sides):
                    midpoints = [round((bid + ask) / 2, 6) for bid, ask in sides]
                    spreads = [round(ask - bid, 6) for bid, ask in sides]
                    if all(0 < s <= MAX_EXCHANGE_SPREAD for s in spreads) and 0.9 <= sum(midpoints) <= 1.1:
                        total = sum(midpoints)
                        probs = [round(m / total, 6) for m in midpoints]
                        quotes.append({'provider': 'Polymarket', 'family': 'market',
                                       'url': market_candidate['url'], 'observed_at': iso(reference),
                                       'bid': [s[0] for s in sides], 'ask': [s[1] for s in sides],
                                       'spread': spreads, 'midpoint': midpoints,
                                       'probabilities': probs, 'market_id': market_candidate['market_id'],
                                       'order_book_urls': [b.entry['url'] for b in books]})
                        market_candidate['books'] = [{'asset_id': b.token, 'bid': s[0], 'ask': s[1],
                                                      'spread': round(s[1] - s[0], 6), 'url': b.entry['url']} for b, s in zip(books, sides)]
                    else:
                        market_candidate['rejected_because'] = f'order book too wide or one-sided: spreads {spreads}'
                else:
                    market_candidate['rejected_because'] = 'one side has no published bid/ask'

        # ---- Thunderpick: one esportsbook, exact names, start within 60 s.
        tp_hit, tp_near = None, []
        for row in evidence['thunderpick']:
            names = [row.get('teams', {}).get('home', {}).get('name'), row.get('teams', {}).get('away', {}).get('name')]
            if not all(names) or {key(n) for n in names} != wanted:
                continue
            start = parse_time(row.get('startTime'))
            delta = int((start - fixture['_start']).total_seconds()) if start else None
            item = {'id': row.get('id'), 'name': row.get('name'), 'start': row.get('startTime'),
                    'start_delta_sec': delta, 'best_of': row.get('bestOf'),
                    'home': row.get('market', {}).get('home', {}).get('name'),
                    'home_odds': row.get('market', {}).get('home', {}).get('odds'),
                    'away': row.get('market', {}).get('away', {}).get('name'),
                    'away_odds': row.get('market', {}).get('away', {}).get('odds'),
                    'url': 'https://thunderpick.io/esports/counter-strike'}
            if delta is not None and abs(delta) <= START_TOLERANCE_SEC and tp_hit is None:
                tp_hit = item
            else:
                item['rejected_because'] = 'start delta outside 60 s' if delta is not None else 'no start time'
                tp_near.append(item)
        if tp_hit:
            order = [0, 1] if key(tp_hit['home']) == key(a) else [1, 0]
            odds = [tp_hit['home_odds'], tp_hit['away_odds']]
            aligned = [odds[order[0]], odds[order[1]]]
            probs, why = no_vig(aligned[0], aligned[1])
            tp_hit['aligned_odds'] = aligned
            tp_hit['rejected_because'] = why or None
            if probs:
                quotes.append({'provider': 'Thunderpick', 'family': 'bookmaker', 'url': tp_hit['url'],
                               'observed_at': iso(reference), 'decimal_odds': aligned,
                               'probabilities': [round(x, 6) for x in probs], 'market_id': str(tp_hit['id'])})
        research.append({'stage': 'Thunderpick esportsbook', 'url': 'https://thunderpick.io/esports/counter-strike',
                         'status': 'resolved' if tp_hit and tp_hit.get('rejected_because') is None else 'unresolved',
                         'detail': (f"match {tp_hit['id']} · odds {tp_hit.get('aligned_odds')} · start delta {tp_hit['start_delta_sec']} s"
                                    if tp_hit else 'no Thunderpick row carries both exact team names'),
                         'near_misses': tp_near[:4]})

        # ---- HLTV: identity and format only; it publishes no market price.
        hltv_hit, hltv_near = None, []
        for card in evidence['hltv']:
            if {key(x) for x in card['teams']} != wanted:
                continue
            delta = int((parse_time(card['starts_at']) - fixture['_start']).total_seconds()) if parse_time(card['starts_at']) else None
            item = dict(card, start_delta_sec=delta)
            if delta is not None and abs(delta) <= START_TOLERANCE_SEC and hltv_hit is None:
                hltv_hit = item
            else:
                hltv_near.append(item)
        research.append({'stage': 'HLTV match page', 'url': hltv_hit['url'] if hltv_hit else 'https://www.hltv.org/matches',
                         'status': 'checked' if hltv_hit else 'unresolved',
                         'detail': (f"HLTV match {hltv_hit['match_id']} · BO{hltv_hit.get('best_of')} · start delta {hltv_hit['start_delta_sec']} s"
                                    if hltv_hit else 'no HLTV card carries both exact team names at this observation'),
                         'near_misses': hltv_near[:4]})

        # ---- Ratings: published points only, formula printed, never a market.
        rank_a = ranking_by_name.get(key(a))
        rank_b = ranking_by_name.get(key(b))
        valve_a = valve_by_name.get(key(a), [])
        valve_b = valve_by_name.get(key(b), [])
        model = None
        if rank_a and rank_b:
            probs = rank_model(rank_a['points'], rank_b['points'])
            if probs:
                model = {'method': 'hltv-rank-elo', 'probabilities': [round(p, 6) for p in probs],
                         'formula': 'p = 1 / (1 + 10 ** ((points_b - points_a) / 400))',
                         'inputs': {'a': rank_a, 'b': rank_b}, 'url': 'https://www.hltv.org/ranking/teams'}
        if model is None and len(valve_a) == 1 and len(valve_b) == 1:
            try:
                pa, pb = float(valve_a[0]['points']), float(valve_b[0]['points'])
                g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * 75 ** 2 / math.pi ** 2)
                p = 1 / (1 + 10 ** (g * (pb - pa) / 400))
                model = {'method': 'valve-glicko', 'probabilities': [round(p, 6), round(1 - p, 6)],
                         'formula': 'g = 1 / sqrt(1 + 3*(ln10/400)^2*RD^2/pi^2); p = 1/(1+10^(g*(pb-pa)/400)); RD=75',
                         'inputs': {'a': valve_a[0], 'b': valve_b[0]},
                         'url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/fit.js'}
            except (TypeError, ValueError):
                model = None

        # ---- One line per fixture, with the priority the brief asks for.
        chosen, method = None, None
        market_quotes = [q for q in quotes if q['family'] == 'market']
        book_quotes = [q for q in quotes if q['family'] == 'bookmaker']
        if market_quotes:
            chosen, method = market_quotes[0], 'market'
        elif book_quotes:
            chosen, method = book_quotes[0], 'bookmaker'
        elif model:
            chosen, method = model, model['method']

        probabilities = chosen['probabilities'] if chosen else None
        pick_index = None
        if probabilities:
            pick_index = 0 if probabilities[0] > probabilities[1] else (1 if probabilities[1] > probabilities[0] else None)
        limitations = []
        if market_candidate:
            limitations.append('Exchange midpoint, not a guaranteed execution price; fees excluded.')
        if tp_hit and tp_hit.get('rejected_because') is None:
            limitations.append('One esportsbook only; margin removed proportionally.')
        if method in ('hltv-rank-elo', 'valve-glicko'):
            limitations.append('Research model from published rating points, not observed betting odds.')
        if not probabilities:
            limitations.append('No observed two-way price and no complete published rating pair at this observation.')

        records.append({
            'id': fixture['id'], 'teams': fixture['teams'], 'competition': fixture['competition'],
            'tier': fixture['tier'], 'starts_at': fixture['starts_at'],
            'source_url': f"https://play.hotspawn.com/cs2-pickems#fixture-{fixture['id']}",
            'hotspawn_api_observed_at': sources_meta['sources']['hotspawn_api']['observed_at'],
            'research': research,
            'quotes': quotes,
            'polymarket_candidate': market_candidate,
            'thunderpick_candidate': tp_hit,
            'hltv_candidate': hltv_hit,
            'ratings': {'hltv': {'a': rank_a, 'b': rank_b}, 'valve': {'a': valve_a, 'b': valve_b}},
            'model': model,
            'method': method,
            'probabilities': probabilities,
            'pick_index': pick_index,
            'pick': fixture['teams'][pick_index] if pick_index is not None else None,
            'limitations': limitations,
        })

    counts = {
        'open': len(records),
        'with_line': sum(1 for r in records if r['method'] in ('market', 'bookmaker')),
        'with_model': sum(1 for r in records if r['method'] in ('hltv-rank-elo', 'valve-glicko')),
        'unresolved': sum(1 for r in records if r['probabilities'] is None),
        'market': sum(1 for r in records if r['method'] == 'market'),
        'bookmaker': sum(1 for r in records if r['method'] == 'bookmaker'),
    }
    dossier = {'schema_version': 1, 'session': 'arena-b3e91409', 'observed_at': iso(reference),
               'source_manifest': 'data/research/b3e91409/live/sources.json',
               'policy': {
                   'identity': 'exact Unicode/case/whitespace-equivalent team names and a start time within 60 s',
                   'exchange': f'exchange midpoint with both sides two-sided and spread <= {MAX_EXCHANGE_SPREAD}',
                   'bookmaker': f'paired decimal odds with margin in [{MIN_BOOK_MARGIN}, {MAX_BOOK_MARGIN}]',
                   'model': 'published rating points only, formula printed per row',
                   'never': 'Hotspawn % picked, HLTV fan votes, inferred values, default 50/50',
               },
               'counts': counts, 'fixtures': records, 'book_requests': manifest['books']}
    (LIVE / 'analysis.json').write_text(json.dumps(dossier, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')

    lines = [f"# Live line dossier — {iso(reference)}", '',
             f"Open Hotspawn CS2 fixtures: **{counts['open']}** · "
             f"with an observed betting line: **{counts['with_line']}** "
             f"(Polymarket {counts['market']}, esportsbook {counts['bookmaker']}) · "
             f"published-rating model only: **{counts['with_model']}** · "
             f"unresolved: **{counts['unresolved']}**", '']
    for record in records:
        prob = ('%.1f%% / %.1f%%' % (record['probabilities'][0] * 100, record['probabilities'][1] * 100)
                if record['probabilities'] else 'blank')
        pick = record['pick'] or ('no side — even' if record['probabilities'] else 'no pick')
        lines.append(f"## {record['id']} — {record['teams'][0]} vs {record['teams'][1]}")
        lines.append(f"- {record['starts_at']} · {record['competition']} · tier {record['tier']}")
        lines.append(f"- **pick {pick}** · {prob} · method `{record['method'] or 'unresolved'}`")
        for stage in record['research']:
            lines.append(f"  - {stage['stage']}: **{stage['status']}** — {stage['detail']}")
        for quote in record['quotes']:
            lines.append(f"  - quote {quote['provider']}: {quote['probabilities']} · {quote['url']}")
        for limitation in record['limitations']:
            lines.append(f"  - limitation: {limitation}")
        lines.append('')
    (LIVE / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines[:40]))
    print(f"... wrote analysis.json ({counts})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
