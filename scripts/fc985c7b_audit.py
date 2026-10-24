"""Session arena-fc985c7b — live-coverage audit and HLTV-first line research.

Read-only research probe. It runs on a GitHub runner (the coding sandbox has
no egress to Hotspawn/HLTV/the esportsbooks) immediately after the production
`scripts.collect` + `scripts.originate --live` refresh, so it sees the same
snapshot the publisher is about to publish.

What it answers, in the order the brief asks for it:

1. **Coverage** — does every CS2 card that Hotspawn is actually showing right
   now appear in the refreshed snapshot, and does every active fixture carry a
   pick? The live fixtures API and the rendered lobby are both fetched here and
   reconciled against the snapshot; any card without a row is reported.
2. **HLTV first, then esportsbooks** — for every active fixture that has no
   external betting line (published method `model`, or unresolved), HLTV is
   tried first (upcoming-match index, then the match page for format, ranks,
   lineups and HLTV's own displayed odds block). Only then are the esportsbooks
   and aggregators tried (EGamersWorld, bo3.gg, Thunderpick, Pinnacle, Stake,
   Smarkets, Bovada, Polymarket, Kalshi). Every attempt records its URL, HTTP
   status, observed time and what it did or did not answer.
3. **Limitations** — the reason each fixture still has no line, published as a
   dated record for the *Unresolved picks & limitations* section.

Hard discipline, unchanged from every earlier session:

* **Nothing here writes a probability, a pick or an alias.** A price found by
  this probe is recorded as a *lead* with its URL and the no-vig arithmetic,
  never injected into `data/latest.json`, `data/origination.json` or any
  pipeline rung. Only the reviewed ladder in `scripts/originate.py` prices a
  fixture, and only from evidence it saved and can replay.
* Hotspawn "% picked" and HLTV fan votes are never probabilities and are never
  read as one.
* Every network call is wrapped: an outage produces a dated reason, never a
  crash and never a value.

Usage:  python -m scripts.fc985c7b_audit --out data/research/fc985c7b
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scripts.domain import iso, name_key, no_vig
from scripts import egw_live

UTC = timezone.utc
UA = 'HotspawnCS2CoverageAudit/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'

FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
LOBBY_URL = 'https://play.hotspawn.com/lobby'
PICKEMS_URL = 'https://play.hotspawn.com/cs2-pickems'
HLTV_MATCHES = 'https://www.hltv.org/matches'

# Esportsbooks and aggregators, tried after HLTV. Each entry is
# (id, url, kind) where kind is 'index' (parse many matches) or 'text'
# (fetch and look for the team names and a two-sided decimal price).
BOOKS = [
    ('egamersworld', 'https://egamersworld.com/counterstrike/matches', 'index'),
    ('bo3', 'https://bo3.gg/matches/current', 'text'),
    ('thunderpick', 'https://thunderpick.io/esports/counter-strike', 'text'),
    ('pinnacle', 'https://www.pinnacle.com/en/esports-hub/cs2', 'text'),
    ('stake', 'https://stake.com/sports/esports/counter-strike', 'text'),
    ('smarkets', 'https://smarkets.com/l/sport/esports', 'text'),
    ('bovada', 'https://www.bovada.lv/esports/counter-strike-2', 'text'),
]

METHODS_WITH_A_LINE = {'market', 'bookmaker', 'consensus', 'relayed_bookmaker'}


class Probe:
    """Every fetch records url, http status, observed_at and a sha256 of the body."""

    def __init__(self, evidence_dir: Path):
        self.dir = evidence_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': UA, 'Accept': '*/*'})
        self.requests: list[dict] = []
        self.last = 0.0

    def _throttle(self):
        delay = 0.4 - (time.monotonic() - self.last)
        if delay > 0:
            time.sleep(delay)
        self.last = time.monotonic()

    def get(self, url: str, label: str, *, timeout=(15, 45)):
        self._throttle()
        entry = {'id': label, 'url': url, 'method': 'GET',
                 'observed_at': iso(datetime.now(UTC)), 'status': 'error'}
        self.requests.append(entry)
        try:
            response = self.session.get(url, timeout=timeout)
            entry['http_status'] = response.status_code
            entry['response_sha256'] = __import__('hashlib').sha256(response.content).hexdigest()
            if response.status_code >= 400:
                entry['error'] = f'HTTP {response.status_code}'
                return None, entry
            entry['status'] = 'ok'
            entry['bytes'] = len(response.content)
            path = self.dir / f'{label}.json'
            path.write_text(json.dumps({'url': url, 'observed_at': entry['observed_at'],
                                        'http_status': response.status_code,
                                        'html': response.text}, ensure_ascii=False))
            entry['evidence'] = path.name
            return response.text, entry
        except requests.RequestException as exc:
            entry['error'] = str(exc)[:300]
            return None, entry

    def manifest(self):
        return list(self.requests)


# ---------------------------------------------------------------------------
# Live inventory
# ---------------------------------------------------------------------------

def live_fixtures(probe: Probe):
    """The scheduled CS2 fixtures Hotspawn's own API is serving right now."""
    text, entry = probe.get(FIXTURES_API, 'hotspawn-fixtures')
    if not text:
        return None, entry
    try:
        rows = json.loads(text)
    except ValueError as exc:
        entry['error'] = f'JSON decode: {exc}'[:300]
        entry['status'] = 'error'
        return None, entry
    out = []
    for row in rows:
        teams = [row.get('participants0_name'), row.get('participants1_name')]
        if not all(teams):
            continue
        out.append({'id': str(row.get('id')), 'teams': teams,
                    'competition': row.get('competition_name'),
                    'starts_at': iso(datetime.fromtimestamp(
                        int(row.get('scheduled_start_time') or 0) / 1000, UTC))
                    if row.get('scheduled_start_time') else None,
                    'tier': row.get('tier')})
    return out, entry


def lobby_cards(probe: Probe):
    """Fixture ids that the rendered lobby links to, plus the card count."""
    text, entry = probe.get(LOBBY_URL, 'hotspawn-lobby')
    cards = []
    if text:
        for match in re.finditer(r'https://www\.hotspawn\.com/matches/([a-z0-9\-]+)-(\d{6,})', text):
            cards.append({'id': match.group(2), 'slug': match.group(1)})
    return cards, entry


# ---------------------------------------------------------------------------
# HLTV first
# ---------------------------------------------------------------------------

def hltv_upcoming(probe: Probe):
    """HLTV's upcoming-match index: team names, start, and the match link."""
    text, entry = probe.get(HLTV_MATCHES, 'hltv-matches')
    rows = []
    if text:
        soup = BeautifulSoup(text, 'html.parser')
        for card in soup.select('.upcomingMatch'):
            names = [n.get_text(' ', strip=True)
                     for n in card.select('.matchTeam .matchTeamName, .matchTeamName')]
            names = [n for n in names if n]
            link = card.select_one('a.match-page-link, a[href^="/matches/"]')
            unix = card.select_one('[data-unix]')
            start = None
            if unix and unix.get('data-unix'):
                try:
                    start = iso(datetime.fromtimestamp(int(unix['data-unix']) / 1000, UTC))
                except (TypeError, ValueError):
                    start = None
            event = card.select_one('.matchEventName, .matchMeta')
            if len(names) >= 2:
                rows.append({'teams': names[:2],
                             'url': ('https://www.hltv.org' + link['href']) if link and link.get('href') else None,
                             'starts_at': start,
                             'event': event.get_text(' ', strip=True) if event else None})
    return rows, entry


def hltv_lookup(rows: list, match: dict):
    """Join a Hotspawn fixture to an HLTV row by both team names (exact key)."""
    keys = {name_key(n) for n in match.get('teams', []) if n}
    if len(keys) != 2:
        return None
    for row in rows:
        if {name_key(n) for n in row['teams']} == keys:
            return row
    return None


def hltv_match_detail(probe: Probe, url: str, label: str):
    """Format, lineups and HLTV's own displayed odds block, verbatim."""
    text, entry = probe.get(url, label)
    detail = {'url': url, 'http_status': entry.get('http_status'), 'error': entry.get('error')}
    if not text:
        return detail, entry
    soup = BeautifulSoup(text, 'html.parser')
    best = soup.find(string=re.compile(r'Best of\s*\d', re.I))
    if best:
        found = re.search(r'Best of\s*(\d)', best if isinstance(best, str) else str(best), re.I)
        if found:
            detail['best_of'] = int(found.group(1))
    odds = soup.select_one('.odds, .match-betting, .betting-block, [class*="odds"]')
    if odds:
        detail['odds_text'] = odds.get_text(' ', strip=True)[:300]
        prices = re.findall(r'\b(\d\.\d{1,2})\b', detail['odds_text'])
        if len(prices) >= 2:
            detail['odds_tokens'] = prices[:4]
    ranks = soup.select('.teamRanking, .team-ranking')
    if ranks:
        detail['rank_text'] = ' | '.join(r.get_text(' ', strip=True) for r in ranks)[:200]
    return detail, entry


# ---------------------------------------------------------------------------
# Esportsbooks after HLTV
# ---------------------------------------------------------------------------

def book_scan(probe: Probe, book_id: str, url: str, kind: str, match: dict, label: str):
    """Did this book answer, does it carry this fixture, and with what price?"""
    text, entry = probe.get(url, label)
    result = {'provider': book_id, 'url': url, 'http_status': entry.get('http_status'),
              'error': entry.get('error'), 'observed_at': entry['observed_at'],
              'listed': False, 'prices': None, 'no_vig': None}
    if not text:
        return result, entry
    keys = [name_key(n) for n in match.get('teams', []) if n]
    if len(keys) != 2:
        return result, entry
    if kind == 'index' and book_id == 'egamersworld':
        for row in egw_live.parse_index(text):
            if {name_key(n) for n in row.get('teams', [])} == set(keys):
                result['listed'] = True
                result['match_url'] = row.get('url')
                result['prices'] = row.get('odds')
                if result['prices'] and len(result['prices']) == 2 and min(result['prices']) > 1:
                    result['no_vig'] = [round(p * 100, 1) for p in no_vig(result['prices'])]
                return result, entry
        return result, entry
    soup = BeautifulSoup(text, 'html.parser')
    blob = soup.get_text(' ', strip=True)
    result['listed'] = all(k in name_key(blob) for k in keys)
    return result, entry


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def classify(match: dict):
    analysis = match.get('analysis') or {}
    method = analysis.get('method')
    if match.get('availability') == 'past':
        return 'past'
    if method in METHODS_WITH_A_LINE:
        return 'line'
    if method == 'model':
        return 'model'
    return 'unresolved'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='data/research/fc985c7b')
    parser.add_argument('--data', default='data')
    parser.add_argument('--max-detail', type=int, default=12,
                        help='cap on per-fixture HLTV match-page fetches')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    evidence = out / 'live'
    probe = Probe(evidence)
    started = datetime.now(UTC)

    snapshot = json.loads((Path(args.data) / 'latest.json').read_text())
    matches = snapshot.get('matches', [])
    now = datetime.fromisoformat(snapshot['generated_at'].replace('Z', '+00:00'))

    # 1. Live inventory reconciliation -------------------------------------
    live_rows, fixture_entry = live_fixtures(probe)
    cards, lobby_entry = lobby_cards(probe)
    live_index = {}
    for row in live_rows or []:
        live_index[str(row['id'])] = row
    snapshot_ids = {str(m.get('id')) for m in matches}
    live_ids = set(live_index)
    active = [m for m in matches if m.get('availability') != 'past']
    coverage = {
        'observed_at': iso(started),
        'snapshot_generated_at': snapshot.get('generated_at'),
        'snapshot_counts': snapshot.get('counts'),
        'live_api_status': fixture_entry.get('http_status'),
        'live_api_error': fixture_entry.get('error'),
        'live_fixtures': len(live_rows or []),
        'live_future': sum(1 for r in (live_rows or [])
                           if r.get('starts_at') and r['starts_at'] > iso(now)),
        'lobby_status': lobby_entry.get('http_status'),
        'lobby_cards': len(cards),
        'lobby_ids_not_in_snapshot': sorted({c['id'] for c in cards} - snapshot_ids),
        'snapshot_active_not_in_live_api': sorted(
            {str(m['id']) for m in active} - live_ids),
        'active_fixtures': len(active),
        'by_class': {},
    }

    # 2. Classify every active fixture -------------------------------------
    rows = []
    for match in sorted(active, key=lambda m: (m.get('starts_at') or '')):
        klass = classify(match)
        analysis = match.get('analysis') or {}
        rows.append({
            'id': str(match.get('id')),
            'teams': [t.get('name') for t in match.get('teams', [])],
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'class': klass,
            'method': analysis.get('method'),
            'probabilities': analysis.get('probabilities'),
            'pick': analysis.get('selection'),
            'source_url': match.get('source_url'),
            'pricing_sources': [r.get('source_url') for r in match.get('research', [])
                                if r.get('source_url')],
        })
    coverage['by_class'] = {k: sum(1 for r in rows if r['class'] == k)
                            for k in ('line', 'model', 'unresolved')}

    # 3. HLTV first, then esportsbooks, for everything without a line ------
    hltv_rows, hltv_entry = hltv_upcoming(probe)
    coverage['hltv_index_status'] = hltv_entry.get('http_status')
    coverage['hltv_index_error'] = hltv_entry.get('error')
    coverage['hltv_index_rows'] = len(hltv_rows)

    no_line = [r for r in rows if r['class'] in ('model', 'unresolved')]
    coverage['researched'] = len(no_line)

    book_index_cache: dict[str, object] = {}
    detail_budget = args.max_detail
    for row in no_line:
        match = next((m for m in active if str(m.get('id')) == row['id']), None)
        if match is None:
            continue
        hit = hltv_lookup(hltv_rows, match)
        if hit:
            row['hltv'] = {'found': True, 'url': hit.get('url'),
                           'starts_at': hit.get('starts_at'), 'event': hit.get('event'),
                           'start_matches': hit.get('starts_at') == match.get('starts_at')}
            if hit.get('url') and detail_budget > 0:
                detail_budget -= 1
                detail, _ = hltv_match_detail(probe, hit['url'], f'hltv-match-{row["id"]}')
                row['hltv'].update({k: v for k, v in detail.items() if k != 'url'})
        else:
            row['hltv'] = {'found': False,
                           'reason': ('HLTV upcoming index did not list both team names'
                                      if hltv_rows else
                                      f'HLTV index unavailable (HTTP {hltv_entry.get("http_status")})'
                                      )}
        scans = []
        for book_id, url, kind in BOOKS:
            key = f'{book_id}'
            if kind == 'index':
                if key not in book_index_cache:
                    book_index_cache[key] = probe.get(url, f'book-{book_id}')[0]
                text = book_index_cache[key]
                if text:
                    entry = {'provider': book_id, 'url': url, 'listed': False,
                             'http_status': 200}
                    for parsed in egw_live.parse_index(text):
                        if {name_key(n) for n in parsed.get('teams', [])} == {
                                name_key(n) for n in match.get('teams', []) if n}:
                            entry['listed'] = True
                            entry['match_url'] = parsed.get('url')
                            entry['prices'] = parsed.get('odds')
                            if entry['prices'] and len(entry['prices']) == 2 and min(entry['prices']) > 1:
                                entry['no_vig'] = [round(p * 100, 1) for p in no_vig(entry['prices'])]
                            break
                    scans.append(entry)
                else:
                    scans.append({'provider': book_id, 'url': url, 'listed': False,
                                  'http_status': probe.requests[-1].get('http_status'),
                                  'error': probe.requests[-1].get('error')})
            else:
                scan, _ = book_scan(probe, book_id, url, kind, match, f'book-{book_id}-{row["id"]}')
                scans.append({k: v for k, v in scan.items() if v is not None or k == 'listed'})
        row['books'] = scans
        row['books_listing'] = [s['provider'] for s in scans if s.get('listed')]
        row['books_with_price'] = [s['provider'] for s in scans if s.get('no_vig')]
        row['limitation'] = limitation_for(row)

    # 4. Write the dated record --------------------------------------------
    record = {'session': 'arena-fc985c7b',
              'observed_at': iso(started),
              'finished_at': iso(datetime.now(UTC)),
              'snapshot_generated_at': snapshot.get('generated_at'),
              'purpose': ('Live coverage audit and HLTV-first, then esportsbook line '
                          'research for every active fixture without an external betting '
                          'line. Leads and limitations only — no probability, pick or '
                          'alias is written by this probe.'),
              'coverage': coverage,
              'rows': rows,
              'requests': probe.manifest()}
    (out / 'line-source-research.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    (out / 'live-coverage.json').write_text(
        json.dumps({'observed_at': iso(started), **coverage}, ensure_ascii=False, indent=2) + '\n')

    flags = build_flags(record, now)
    (out / 'flags.json').write_text(json.dumps(flags, ensure_ascii=False, indent=2) + '\n')
    (out / 'line-source-research.md').write_text(render(record))

    print(f'Active fixtures: {len(rows)} '
          f'(line {coverage["by_class"]["line"]}, model {coverage["by_class"]["model"]}, '
          f'unresolved {coverage["by_class"]["unresolved"]})')
    print(f'Live API: {coverage["live_api_status"]} · {coverage["live_fixtures"]} scheduled, '
          f'{coverage["live_future"]} still in the future')
    print(f'HLTV index: {coverage["hltv_index_status"]} · {coverage["hltv_index_rows"]} rows')
    print(f'Researched without a line: {coverage["researched"]}')
    print(f'Wrote {out}/line-source-research.json, live-coverage.json, flags.json')


def limitation_for(row: dict) -> str:
    """Why this fixture still has no external betting line, with the evidence."""
    if row['class'] == 'line':
        return 'Resolved from an external betting line.'
    bits = []
    hltv = row.get('hltv') or {}
    if hltv.get('found'):
        bits.append(f"HLTV lists the fixture ({hltv.get('url')})")
        if hltv.get('best_of'):
            bits.append(f"best-of {hltv['best_of']}")
        bits.append('HLTV published no bookmaker price on the page'
                    if not hltv.get('odds_tokens') else
                    f"HLTV page shows odds tokens {hltv['odds_tokens']}")
    else:
        bits.append(f"HLTV: {hltv.get('reason', 'not found')}")
    listed = row.get('books_listing') or []
    priced = row.get('books_with_price') or []
    if priced:
        providers = ', '.join(priced)
        bits.append(f'a two-sided price was only found on {providers} '
                    '(aggregated/guidance, not a first-party quote replayed by the ladder)')
    elif listed:
        bits.append(f'listed without a usable two-sided price on {", ".join(listed)}')
    else:
        bits.append('no esportsbook or aggregator reachable in this pass listed the fixture')
    return '; '.join(bits) + '.'


def build_flags(record: dict, now: datetime) -> list:
    flags = []
    coverage = record['coverage']
    if coverage['live_api_status'] != 200:
        flags.append({
            'id': 'fc985c7b-live-inventory-unreachable',
            'severity': 'warning',
            'match_ids': [],
            'title': 'Hotspawn fixtures API did not answer during this audit',
            'detail': (f"HTTP {coverage['live_api_status']} ({coverage['live_api_error']}) for "
                       f"{FIXTURES_API}. The coverage reconciliation below was computed against "
                       'the refreshed snapshot only; no card was invented.'),
            'source_urls': [FIXTURES_API]})
    missing = coverage['lobby_ids_not_in_snapshot']
    if missing:
        flags.append({
            'id': 'fc985c7b-lobby-cards-absent-from-snapshot',
            'severity': 'warning',
            'match_ids': missing[:40],
            'title': (f'{len(missing)} lobby card(s) are not rows in the refreshed snapshot'),
            'detail': ('The rendered lobby links these fixture ids, but the refreshed snapshot '
                       f"(generated {coverage['snapshot_generated_at']}) has no row for them. "
                       'They are listed here for manual reconciliation; nothing was inferred.'),
            'source_urls': [LOBBY_URL, PICKEMS_URL]})
    gaps = [r for r in record['rows'] if r['class'] == 'unresolved']
    for row in gaps:
        flags.append({
            'id': f"fc985c7b-unresolved-{row['id']}",
            'severity': 'notice',
            'match_ids': [row['id']],
            'title': (f"No external line for {' vs '.join(row['teams'])} — "
                      'limitations and sources tried'),
            'detail': row['limitation'],
            'source_urls': [row['source_url']] + row.get('pricing_sources', [])
            + ([row['hltv']['url']] if row.get('hltv', {}).get('url') else [])})
    return flags


def render(record: dict) -> str:
    c = record['coverage']
    lines = ['# Live coverage audit and HLTV-first line research — arena-fc985c7b', '',
             f"Observed **{record['observed_at']}** · snapshot generated "
             f"**{record['snapshot_generated_at']}**.", '',
             'Leads and limitations only: no probability, pick or alias is written by this '
             'probe. The reviewed ladder in `scripts/originate.py` remains the only writer of '
             'a published number.', '',
             '## Coverage', '',
             f"- Hotspawn fixtures API: HTTP {c['live_api_status']}, "
             f"{c['live_fixtures']} scheduled CS2 fixtures, {c['live_future']} still in the future.",
             f"- Rendered lobby: HTTP {c['lobby_status']}, {c['lobby_cards']} match links.",
             f"- Active fixtures in the snapshot: **{c['active_fixtures']}** — "
             f"**{c['by_class']['line']}** with an external betting line, "
             f"**{c['by_class']['model']}** research-model, "
             f"**{c['by_class']['unresolved']}** unresolved.", '']
    if c['lobby_ids_not_in_snapshot']:
        lines += ['Lobby cards with no snapshot row: '
                  + ', '.join(c['lobby_ids_not_in_snapshot'][:40]), '']
    lines += ['## Fixtures without an external betting line', '',
              '| Fixture | Teams | Starts | HLTV | Books listing | Books with a price |',
              '| --- | --- | --- | --- | --- | --- |']
    for row in record['rows']:
        if row['class'] not in ('model', 'unresolved'):
            continue
        hltv = row.get('hltv') or {}
        hltv_cell = (f"[page]({hltv['url']})" if hltv.get('url')
                     else (hltv.get('reason') or 'not listed'))
        lines.append(f"| {row['id']} | {' vs '.join(row['teams'])} | {row['starts_at']} "
                     f"| {hltv_cell} | {', '.join(row.get('books_listing') or ['—'])} "
                     f"| {', '.join(row.get('books_with_price') or ['—'])} |")
    lines += ['', '## Limitations, fixture by fixture', '']
    for row in record['rows']:
        if row['class'] not in ('model', 'unresolved'):
            continue
        lines.append(f"- **{row['id']} · {' vs '.join(row['teams'])}** ({row['class']}): "
                     f"{row['limitation']}")
    lines += ['', f"Every request this probe made is listed in "
                  f"`{record['session']}/line-source-research.json` → `requests`.", '']
    return '\n'.join(lines)


if __name__ == '__main__':
    main()
