"""Read-only live research probe for session 0c034b94 (picks for every Hotspawn CS2 match).

Why this exists
---------------
The brief asks for a pick, or an explicit limitation, for **every** Counter-Strike 2
match Hotspawn lists, and says the research order is HLTV first and esportsbooks
second for any fixture the featured method cannot resolve.  The authoring sandbox
cannot reach `play.hotspawn.com`, `hltv.org`, `egamersworld.com` or the exchange
APIs at all (every request fails before a status line), so the only place that
question can be answered with first-hand evidence is a GitHub runner.

This module therefore **only records what a source publishes**.  It never writes a
probability, a pick or an alias: the publisher's ladder (`scripts/originate.py`)
remains the only path to a published number.  Values that cannot be read stay
absent and are reported as a limitation.

What is read, in the order the brief names
------------------------------------------
1. The **published site** (`latest.json`, `origination.json`) - what the dashboard
   currently claims, so a gap can be described against the live page.
2. **Hotspawn** - the official scheduled-fixtures API and the rendered lobby, so
   the inventory the picks must cover is measured, not assumed.
3. **HLTV** - the upcoming-matches page and the official weekly world ranking.
   HLTV is used for identity, schedule and ranking membership; it is never used
   for fan votes (HLTV fan votes are excluded from every number by policy).
4. **Esportsbooks / exchanges** - EGamersWorld's match directory and Polymarket's
   public CS2 tag are read for HTTP reachability only.  A `403` is recorded as a
   limitation of this runner, not as proof that no market exists.

Output
------
`data/research/0c034b94/probe.json` (machine readable) and `probe.md` (readable),
with the raw response bodies archived under `data/research/0c034b94/raw/` so every
parse below can be re-run offline with `--parse-raw`.

CLI
---
    python -m scripts.0c034b94_probe                 # fetch live, then write the dossier
    python -m scripts.0c034b94_probe --parse-raw     # re-parse the archived bodies only
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scripts import hltv_ranking
from scripts.domain import name_key, timestamp

UTC = timezone.utc
OUT = Path('data/research/0c034b94')
RAW = OUT / 'raw'

DEPLOYED = 'https://buffedlizard55-lab.github.io/MaltaProj3/'
FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
LOBBY = 'https://play.hotspawn.com/lobby'
CS2_LOBBY = 'https://play.hotspawn.com/cs2-pickems'
HLTV_MATCHES = 'https://www.hltv.org/matches'
HLTV_RANKING = hltv_ranking.RANKING_URL
EGW_MATCHES = 'https://egamersworld.com/counterstrike/matches'
POLY_TAG = 'https://gamma-api.polymarket.com/events?tag_slug=cs2&closed=false&limit=100'
HEADERS = {
    'User-Agent': 'HotspawnCS2Origination/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)',
    'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8',
}
#: Every published method that carries an observed betting price.  A row outside
#: this set is either a research model or has no pick at all, i.e. exactly the
#: population the brief asks to research HLTV-first.
MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference', 'relay'}
TIMEOUT = (15, 45)


def now_iso() -> str:
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def slug(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')


def record(label: str, url: str, response=None, *, error: str | None = None, body: bytes | None = None) -> dict:
    """One dated, hash-checked source observation. Nothing is inferred."""
    entry = {'label': label, 'url': url, 'observed_at': now_iso(), 'status': 'error'}
    if error is not None:
        entry['error'] = error[:400]
        return entry
    entry.update(http_status=response.status_code, final_url=response.url,
                 content_type=response.headers.get('Content-Type'),
                 bytes=len(body or b''),
                 sha256=hashlib.sha256(body or b'').hexdigest())
    entry['status'] = 'ok' if response.ok else 'error'
    if not response.ok:
        entry['error'] = 'HTTP ' + str(response.status_code)
    return entry


def get(label: str, url: str, *, expect_json: bool = False) -> tuple[dict, object]:
    """Public GET. The body is archived before anything parses it."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:            # noqa: PERF203 - one row per failure
        return record(label, url, error=type(exc).__name__ + ': ' + str(exc)), None
    entry = record(label, url, response, body=response.content)
    RAW.mkdir(parents=True, exist_ok=True)
    # HTML is archived gzipped (``.html.gz``), the repository's convention for
    # retained originals: the publisher copies the research tree into the site,
    # and a bare ``.html`` there is validated as one of its own pages.
    path = RAW / f'{slug(label)}.{"json" if expect_json else "html.gz"}'
    if response.ok:
        if expect_json:
            path.write_bytes(response.content)
        else:
            path.write_bytes(gzip.compress(response.content, mtime=0))
            # A pre-gzip archive of the same label would be validated as one of
            # the site's own pages when the publisher copies this tree.
            path.with_suffix('').unlink(missing_ok=True)
        entry['raw'] = str(path)
    else:
        path.unlink(missing_ok=True)
    if not response.ok:
        return entry, None
    if expect_json:
        try:
            return entry, response.json()
        except ValueError as exc:
            entry.update(status='error', error='unparseable JSON: ' + str(exc)[:200])
            return entry, None
    return entry, response.text


# ---------------------------------------------------------------------------
# Parsers (pure functions over archived text; re-runnable with --parse-raw)
# ---------------------------------------------------------------------------

def parse_hltv_listing(text: str) -> list:
    """Upcoming fixtures from an HLTV listing page, one row per match card.

    HLTV renders each fixture as ``div.match-wrapper[data-match-wrapper]`` with
    ``data-match-id``, a ``.match-teamname`` per side in page order, the start as
    the card's own ``data-unix`` epoch and the event as
    ``.match-event[data-event-headline]``.  The localized clock text is never
    parsed and a card missing a team name or an epoch is dropped rather than
    guessed.  Live and finished cards are excluded from the "upcoming" list by
    the wrapper's own ``live`` attribute and by the epoch test, not by scraping
    the displayed time.
    """
    soup = BeautifulSoup(text, 'html.parser')
    rows, seen = [], set()
    for card in soup.select('div.match-wrapper[data-match-wrapper]'):
        teams = [n.get_text(' ', strip=True) for n in card.select('.match-teamname')]
        teams = [n for n in teams if n]
        stamp = card.select_one('[data-unix]')
        epoch = stamp.get('data-unix') if stamp else None
        start = timestamp(epoch) if epoch else None
        if len(teams) != 2 or start is None:
            continue
        href = None
        link = card.select_one('a.match-teams[href^="/matches/"], a.match-top[href^="/matches/"]')
        if link is not None:
            href = (link.get('href') or '').split('?')[0]
        event = card.select_one('.match-event[data-event-headline]')
        analytics = card.select_one('a[href^="/betting/analytics/"]')
        meta = card.select_one('.match-meta')
        # The listing repeats pinned cards; one row per match id keeps the
        # evidence a set of observations rather than a count of DOM nodes.
        dedupe = str(card.get('data-match-id') or href or '')
        if dedupe in seen:
            continue
        seen.add(dedupe)
        rows.append({
            'match_id': card.get('data-match-id'),
            'url': ('https://www.hltv.org' + href) if href else None,
            'teams': teams,
            'starts_at': start.isoformat().replace('+00:00', 'Z'),
            'event': (event.get('data-event-headline') if event is not None else None),
            'best_of': (meta.get_text(' ', strip=True) if meta is not None else None),
            'live': (card.get('live') or '').lower() == 'true',
            'betting_analytics_url': ('https://www.hltv.org' + analytics['href'].split('?')[0]
                                      if analytics is not None else None),
        })
    return rows


def parse_lobby_fixture_ids(text: str) -> list:
    """Fixture ids the rendered lobby actually encodes, in page order."""
    ids = re.findall(r'fixture[-_/](\d{4,})', text)
    return sorted({i for i in ids}, key=int)


def parse_polymarket_events(payload) -> list:
    """Public identifiers only: id, slug, title, start date. No prices here."""
    rows = []
    for event in payload if isinstance(payload, list) else []:
        if not isinstance(event, dict):
            continue
        rows.append({'id': str(event.get('id')), 'slug': event.get('slug'),
                     'title': event.get('title'), 'start': event.get('startDate'),
                     'markets': len(event.get('markets') or [])})
    return rows


def open_fixtures(records: list, reference: datetime) -> list:
    """Fixture API records whose scheduled start is in the future of the observation.

    Hotspawn's feed is flat: ``scheduled_start_time`` is an epoch in milliseconds
    (a digit string), and ``status`` is ``scheduled``.  A record without a
    parseable start is kept out of the "open" inventory and never guessed; the
    caller reports the count so the omission stays visible.
    """
    out = []
    for item in records:
        if not isinstance(item, dict):
            continue
        start = timestamp(item.get('scheduled_start_time') or item.get('start_date')
                          or item.get('starts_at'))
        if start is None or start <= reference:
            continue
        out.append(item)
    return out


def fixture_view(item: dict) -> dict:
    """Normalise one Hotspawn fixture record without inventing missing fields."""
    start = timestamp(item.get('scheduled_start_time') or item.get('start_date')
                      or item.get('starts_at'))
    names = [item.get('participants0_name'), item.get('participants1_name')]
    if not any(names):
        left = item.get('team1') or {}
        right = item.get('team2') or {}
        names = [left.get('name') if isinstance(left, dict) else None,
                 right.get('name') if isinstance(right, dict) else None]
    return {'id': str(item.get('id')),
            'teams': names,
            'competition': item.get('competition_name') or item.get('competition'),
            'tier': item.get('tier'),
            'source_status': item.get('status'),
            'starts_at': start.isoformat().replace('+00:00', 'Z') if start else None}


# ---------------------------------------------------------------------------
# Joins (exact names only; never fuzzy)
# ---------------------------------------------------------------------------

def hltv_join(fixture: dict, rows: list) -> dict:
    """Does HLTV list these two names, and does its start agree with Hotspawn?

    Names are compared with :func:`name_key` only (case, Unicode and whitespace
    equivalence); no sponsor or abbreviation alias is applied here.  Each exact
    name match also carries the start-time delta, because a rescheduled fixture
    must never inherit another slot's identity: a delta above the project's
    60-second window is reported, not smoothed over.
    """
    wanted = [name_key(n) if n else '' for n in fixture['teams']]
    own_start = timestamp(fixture.get('starts_at'))
    exact, shared = [], []
    for row in rows:
        keys = [name_key(n) for n in row['teams']]
        if len(keys) != 2:
            continue
        row_start = timestamp(row.get('starts_at'))
        delta = None
        if own_start is not None and row_start is not None:
            delta = int((row_start - own_start).total_seconds())
        entry = dict(row, start_delta_seconds=delta)
        if sorted(keys) == sorted(wanted):
            exact.append(entry)
        elif set(keys) & set(wanted):
            shared.append(entry)
    return {'exact': exact, 'shares_one_name': shared}


def ranking_row(name: str, rows: list) -> dict | None:
    if not name:
        return None
    key = name_key(name)
    for row in rows:
        if name_key(row['team']) == key:
            return row
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--parse-raw', action='store_true',
                        help='re-parse the archived bodies instead of fetching')
    args = parser.parse_args(argv)
    out_dir = args.output
    RAW.mkdir(parents=True, exist_ok=True)

    observations: list = []
    claims: dict = {}

    def text_of(label: str, url: str, expect_json: bool = False):
        if args.parse_raw:
            path = RAW / f'{slug(label)}.{"json" if expect_json else "html.gz"}'
            if not path.exists():
                observations.append({'label': label, 'url': url, 'status': 'error',
                                     'error': 'not archived', 'observed_at': now_iso()})
                return None
            observations.append({'label': label, 'url': url, 'status': 'archived',
                                 'raw': str(path), 'observed_at': now_iso()})
            if expect_json:
                body = path.read_text(encoding='utf-8', errors='replace')
            else:
                body = gzip.decompress(path.read_bytes()).decode('utf-8', errors='replace')
            if expect_json:
                try:
                    return json.loads(body)
                except ValueError:
                    return None
            return body
        entry, body = get(label, url, expect_json=expect_json)
        observations.append(entry)
        return body

    # 1. what the dashboard publishes right now -----------------------------
    published_latest = text_of('published latest.json', DEPLOYED + 'data/latest.json', True)
    published_complete = text_of('published origination.json', DEPLOYED + 'data/origination.json', True)
    published_rows = {}
    if isinstance(published_complete, dict):
        for row in published_complete.get('matches') or []:
            if isinstance(row, dict) and row.get('id') is not None:
                origin = row.get('origination') or {}
                published_rows[str(row['id'])] = {
                    'teams': [t.get('name') if isinstance(t, dict) else t for t in row.get('teams') or []],
                    'method': origin.get('method'),
                    'pick_index': row.get('pick_index'),
                    'probabilities': origin.get('probabilities'),
                    'starts_at': row.get('starts_at'),
                    'competition': row.get('competition'),
                    'source_url': origin.get('source_url'),
                }
    claims['published'] = {
        'latest_generated_at': (published_latest or {}).get('generated_at') if isinstance(published_latest, dict) else None,
        'complete_generated_at': (published_complete or {}).get('generated_at') if isinstance(published_complete, dict) else None,
        'complete_rows': len(published_rows),
        'complete_unresolved_ids': [k for k, v in published_rows.items() if v['pick_index'] is None],
        'complete_methods': sorted({str(v['method']) for v in published_rows.values()}),
    }

    # 2. Hotspawn: the inventory every pick must cover ----------------------
    _, fixtures_payload = (None, text_of('hotspawn fixtures api', FIXTURES_API, True))
    records = []
    if isinstance(fixtures_payload, dict):
        records = fixtures_payload.get('data') or fixtures_payload.get('fixtures') or []
    elif isinstance(fixtures_payload, list):
        records = fixtures_payload
    observed = datetime.now(UTC)
    kept = open_fixtures(records, observed)
    live_open = [fixture_view(r) for r in kept]
    live_open = [f for f in live_open if f['id'] and all(f['teams'])]
    skipped = [str(r.get('id')) for r in records if isinstance(r, dict)
               and not str(r.get('id')) in {f['id'] for f in live_open}]
    lobby_html = text_of('hotspawn lobby', LOBBY + '?cb=' + str(int(observed.timestamp())))
    lobby_ids = parse_lobby_fixture_ids(lobby_html or '')
    claims['hotspawn'] = {
        'api_records': len(records),
        'api_records_not_open_or_incomplete': len(skipped),
        'api_open_fixtures': len(live_open),
        'api_open_ids': [f['id'] for f in live_open],
        'lobby_fixture_ids': lobby_ids,
        'open_not_in_lobby': [f['id'] for f in live_open if lobby_ids and f['id'] not in lobby_ids],
        'lobby_not_open_in_api': [i for i in lobby_ids if i not in {f['id'] for f in live_open}],
    }

    # 3. coverage: live open fixtures vs the published complete list --------
    published_ids = set(published_rows)
    published_open_ids = {mid for mid, row in published_rows.items()
                          if (timestamp(row.get('starts_at')) or observed) > observed}
    uncovered = [f for f in live_open if f['id'] not in published_ids]
    claims['coverage'] = {
        'open_without_published_row': uncovered,
        'published_open_rows': len(published_open_ids),
        'published_open_rows_not_in_live_open': sorted(published_open_ids - {f['id'] for f in live_open}),
        'live_open_not_in_published_open': sorted({f['id'] for f in live_open} - published_open_ids),
        'open_without_pick': [f for f in live_open
                              if f['id'] in published_rows and published_rows[f['id']]['pick_index'] is None],
    }

    # 4. HLTV first: identity, schedule, ranking membership -----------------
    hltv_html = text_of('hltv matches', HLTV_MATCHES)
    hltv_rows = parse_hltv_listing(hltv_html or '')
    ranking_rows = []
    for offset in (0, 30, 60, 90):
        url = HLTV_RANKING + (f'?offset={offset}' if offset else '')
        page = text_of(f'hltv ranking {offset}', url)
        if not page:
            continue
        rows = hltv_ranking.parse_ranking_page(page)
        for position, row in enumerate(rows):
            row['rank'] = offset + position + 1
            grading = observations[-1]
            row['page_url'] = grading.get('final_url') or url
        ranking_rows.extend(rows)
        if len(rows) < 25 or len(rows) >= 200:
            break
    claims['hltv'] = {
        'upcoming_rows_parsed': len(hltv_rows),
        'ranking_rows_parsed': len(ranking_rows),
        'ranking_pages': [o.get('final_url') or o['url'] for o in observations if o['label'].startswith('hltv ranking')
                          and o.get('status') in ('ok', 'archived')],
    }

    # 5. Esportsbook / exchange reachability (recorded, never inferred) -----
    _, egw_status = (None, text_of('egamersworld matches', EGW_MATCHES))
    poly_payload = text_of('polymarket cs2 tag', POLY_TAG, True)
    poly_rows = parse_polymarket_events(poly_payload or [])
    claims['esportsbooks'] = {
        'egamersworld_ok': bool(egw_status),
        'polymarket_events_parsed': len(poly_rows),
        'polymarket_event_ids': [r['id'] for r in poly_rows][:60],
    }

    # 6. HLTV-first research for every fixture that is not a featured market line
    targets = []
    for fixture in live_open:
        row = published_rows.get(fixture['id'])
        method = (row or {}).get('method')
        if row is not None and method in MONEY_METHODS:
            continue
        join = hltv_join(fixture, hltv_rows)
        # HLTV's own odds-comparison page for the matched fixture, when HLTV
        # publishes one, is recorded for review. It is evidence that HLTV
        # aggregates bookmaker prices for the match; no price is copied here.
        analytics = None
        linked = next((r for r in (join['exact'] + join['shares_one_name'])
                       if r.get('betting_analytics_url')), None)
        if linked is not None and not args.parse_raw:
            url = linked['betting_analytics_url']
            entry, page = get('hltv betting analytics ' + fixture['id'], url)
            observations.append(entry)
            title = None
            if page:
                soup = BeautifulSoup(page, 'html.parser')
                title = soup.title.get_text(' ', strip=True) if soup.title else None
            best_bet = re.findall(r'class="best-bet-odds">([\d.]+)<', page or '')
            analytics = {'url': url, 'bound_by': ('both names' if linked in join['exact'] else 'one name + start'),
                         'status': entry.get('status'), 'http_status': entry.get('http_status'),
                         'title': title,
                         'mentions_bookmaker': (page or '').lower().count('bookmaker'),
                         'mentions_odds': (page or '').lower().count('odds'),
                         # What the served HTML actually carries. HLTV renders the
                         # odds table client-side for these cards, so the only
                         # decimal prices present are the promo widget's repeated
                         # ``best-bet-odds`` values -- recorded, never used.
                         'best_bet_odds': sorted(set(best_bet)),
                         'best_bet_odds_count': len(best_bet),
                         'usable_two_way_price': bool(best_bet) and len(set(best_bet)) > 1}
        targets.append({
            'fixture': fixture,
            'published': row,
            'reason': ('no published row at all' if row is None
                       else 'published by ' + str(method)),
            'hltv_exact': join['exact'],
            'hltv_shares_one_name': join['shares_one_name'],
            'hltv_betting_analytics': analytics,
            'hltv_ranking': {name: ranking_row(name, ranking_rows) for name in fixture['teams']},
        })
    claims['targets'] = targets

    dossier = {
        'session': 'arena-0c034b94',
        'purpose': ('Record what Hotspawn, HLTV and esportsbook surfaces publish for the live CS2 '
                    'fixtures whose pick is not a featured market line. Facts only: no probability, '
                    'pick or alias is written here.'),
        'observed_at': now_iso(),
        'mode': 'parse-raw' if args.parse_raw else 'live',
        'sources': observations,
        'summary': claims,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'probe.json').write_text(json.dumps(dossier, ensure_ascii=False, indent=2) + '\n')
    (out_dir / 'probe.md').write_text(render_markdown(dossier))
    print('wrote', out_dir / 'probe.json')
    print('targets', len(targets), '| live open', len(live_open), '| published rows', len(published_rows))
    return 0


def render_markdown(dossier: dict) -> str:
    s = dossier['summary']
    lines = ['# Live probe - picks for every Hotspawn CS2 match', '',
             'Observed ' + dossier['observed_at'] + ' (' + dossier['mode'] + ').',
             'Facts only: this file records what each source served. No probability, pick or alias is written here.', '',
             '## Published dashboard', '']
    pub = s['published']
    lines += ['| Field | Value |', '| --- | --- |',
              '| `data/latest.json` generated_at | ' + str(pub['latest_generated_at']) + ' |',
              '| complete picks generated_at | ' + str(pub['complete_generated_at']) + ' |',
              '| complete pick rows | ' + str(pub['complete_rows']) + ' |',
              '| rows without a pick | ' + str(len(pub['complete_unresolved_ids'])) + ' ' + str(pub['complete_unresolved_ids']) + ' |',
              '| methods present | ' + ', '.join(pub['complete_methods']) + ' |', '',
              '## Hotspawn inventory', '', '| Field | Value |', '| --- | --- |',
              '| API records | ' + str(s['hotspawn']['api_records']) + ' |',
              '| API open fixtures | ' + str(s['hotspawn']['api_open_fixtures']) + ' |',
              '| rendered lobby fixture ids | ' + str(len(s['hotspawn']['lobby_fixture_ids'])) + ' |',
              '| open fixtures not listed in the lobby | ' + str(s['hotspawn']['open_not_in_lobby']) + ' |',
              '| lobby ids not open in the API | ' + str(s['hotspawn']['lobby_not_open_in_api']) + ' |', '',
              '## Coverage against the published picks', '',
              'Open fixtures with **no published row at all**: ' +
              (', '.join(f['id'] + ' ' + ' vs '.join(f['teams']) for f in s['coverage']['open_without_published_row']) or 'none'),
              '', '## HLTV-first research targets', '']
    if not s['targets']:
        lines += ['Every live open fixture is published from an observed betting price; nothing needed research.', '']
    for target in s['targets']:
        f = target['fixture']
        lines += ['### ' + f['id'] + ' - ' + ' vs '.join(f['teams']),
                  '',
                  '- start (Hotspawn API): ' + str(f['starts_at']),
                  '- competition: ' + str(f['competition']),
                  '- published pick: ' + (str(target['published']['pick_index']) if target['published'] else 'none')
                  + ' (' + target['reason'] + ')',
                  '- HLTV exact-name listing: ' + (', '.join(
                      r['url'] + ' (start delta ' + str(r.get('start_delta_seconds')) + 's)'
                      for r in target['hltv_exact']) or 'not found'),
                  '- HLTV odds-comparison page: ' + (
                      str(target['hltv_betting_analytics']) if target.get('hltv_betting_analytics') else 'not fetched'),
                  '- HLTV rows sharing one name (review only): ' +
                  (', '.join(r['url'] + ' (start delta ' + str(r.get('start_delta_seconds')) + 's)'
                             for r in target['hltv_shares_one_name']) or 'none'),
                  '- HLTV ranking: ' + json.dumps({k: (v or {}).get('rank') for k, v in target['hltv_ranking'].items()}),
                  '']
    lines += ['## Source observations', '', '| Source | Status | HTTP | Observed | URL |', '| --- | --- | --- | --- | --- |']
    for o in dossier['sources']:
        lines.append('| ' + o.get('label', '?') + ' | ' + str(o.get('status')) + ' | ' + str(o.get('http_status') or o.get('error') or '') +
                     ' | ' + str(o.get('observed_at')) + ' | ' + str(o.get('final_url') or o.get('url')) + ' |')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    raise SystemExit(main())
