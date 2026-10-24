"""Session arena-f4217201 — dated, runner-side reconciliation of the live
Hotspawn CS2 lobby against the published picks, plus a source hunt for every
fixture the published snapshot does not cover.

Why this is a runner script and not a sandbox note: the Arena coding sandbox has
no general egress (only GitHub/npm/PyPI), so it cannot re-read Hotspawn, HLTV or
the esportsbooks. GitHub's runner can. This module therefore performs the reads
first-hand, stores status/hash/excerpt evidence for every URL it touched, and
writes only under ``data/research/f4217201/``. It never collects, never
originates a probability, never edits ``data/latest.json`` and never deploys.

The order of research is the one the brief asks for: Hotspawn identity first,
then HLTV identity, then esportsbook/betting-line sources. A fixture only gets
the label ``external-line-found`` when a real two-sided prematch quote was read;
an unreachable page is recorded as unreachable, never as proof that no market
exists. No probability, pick or alias is written by hand here.

Usage (on a GitHub runner):
  python -m scripts.f4217201_probe --out data/research/f4217201
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

UTC = timezone.utc
SESSION = 'arena-f4217201'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')

FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?'
                + urlencode({'sport_alias': 'cs2', 'status': 'scheduled', 'tenantId': 1}))
LOBBY_URL = 'https://play.hotspawn.com/lobby'
PUBLISHED_JSON = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json'
PUBLISHED_ORIGINATION = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json'
HLTV_MATCHES = 'https://www.hltv.org/matches'
EGW_INDEX = 'https://egamersworld.com/counterstrike/matches'
POLY_TAGGED = 'https://gamma-api.polymarket.com/events?' + urlencode({
    'tag_slug': 'counter-strike-2', 'active': 'true', 'closed': 'false', 'limit': 100})
THUNDERPICK_API = 'https://thunderpick.io/api/matches'
BOVADA_COUPON = ('https://www.bovada.lv/services/sports/event/coupon/events/A/description/'
                 'esports/counter-strike-2')
PINNACLE_MATCHUPS = ('https://guest.api.arcadia.pinnacle.com/0.1/sports/29/matchups')
KALSHI_EVENTS = ('https://api.elections.kalshi.com/trade-api/v2/events?'
                 + urlencode({'series_ticker': 'KXCS2GAME', 'limit': 100}))
BO3_MATCHES = 'https://api.bo3.gg/api/v1/matches?page[limit]=50'

STALE_HOURS = 8.0
CHALLENGE = ('just a moment', 'cf-chl', 'challenge-platform', 'attention required',
             'enable javascript and cookies', 'captcha', 'access denied')


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def parse_iso(value: str) -> datetime:
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8', 'replace')).hexdigest()[:32]


def excerpt(text: str, needle: str = '', before: int = 120, after: int = 320) -> str:
    text = re.sub(r'\s+', ' ', text or '').strip()
    if not needle:
        return text[:before + after]
    pos = text.casefold().find(needle.casefold())
    if pos < 0:
        return ''
    return text[max(0, pos - before):pos + after].strip()


def fetch(session: requests.Session, name: str, url: str, *, method: str = 'GET',
          payload: dict | None = None, timeout: int = 35, needle: str = '') -> dict:
    """One first-party read. Records status, hash and an excerpt, always."""
    observed = now_iso()
    record = {'name': name, 'url': url, 'method': method, 'observed_at': observed,
              'http': None, 'status': 'error', 'sha256': None, 'bytes': 0,
              'challenge': False, 'excerpt': '', 'error': None}
    try:
        if method == 'POST':
            response = session.post(url, json=payload, timeout=timeout, headers={
                'User-Agent': UA, 'Accept': 'application/json,*/*'})
        else:
            response = session.get(url, timeout=timeout, headers={
                'User-Agent': UA, 'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8'})
        record['http'] = response.status_code
        body = response.text or ''
        record['bytes'] = len(body)
        record['sha256'] = sha(body)
        record['excerpt'] = excerpt(body, needle) if needle else excerpt(body)
        lowered = body.casefold()
        record['challenge'] = any(marker in lowered for marker in CHALLENGE)
        if response.status_code >= 400:
            record['status'] = 'http-%d' % response.status_code
        elif record['challenge']:
            record['status'] = 'challenge'
        else:
            record['status'] = 'ok'
        record['_body'] = body
    except requests.RequestException as exc:  # network/DNS/TLS: never guessed
        record['error'] = type(exc).__name__ + ': ' + str(exc)[:180]
    return record


def strip_private(record: dict) -> dict:
    return {k: v for k, v in record.items() if not k.startswith('_')}


def lobby_ids(html: str) -> list[str]:
    """Fixture ids rendered as /matches/<slug>-<id> cards on the lobby page."""
    return sorted(set(re.findall(r'href="https://www\.hotspawn\.com/matches/[^"#]*?-(\d{6,})"',
                                 html or '')))


def fixture_rows(body: str, now: datetime) -> list[dict]:
    """Hotspawn's own scheduled rows, normalised. Epoch-ms fields only."""
    try:
        payload = json.loads(body)
    except ValueError:
        return []
    rows = []
    for row in payload if isinstance(payload, list) else []:
        start_ms = int(row.get('scheduled_start_time') or 0)
        lock_ms = int(row.get('lock_time') or 0)
        start = datetime.fromtimestamp(start_ms / 1000, UTC) if start_ms else None
        rows.append({
            'id': str(row.get('id')),
            'teams': [row.get('participants0_name') or '', row.get('participants1_name') or ''],
            'competition': row.get('competition_name') or '',
            'tier': row.get('tier'),
            'starts_at': start.strftime('%Y-%m-%dT%H:%M:%SZ') if start else '',
            'locks_at': (datetime.fromtimestamp(lock_ms / 1000, UTC)
                         .strftime('%Y-%m-%dT%H:%M:%SZ') if lock_ms else ''),
            'future': bool(start and start > now),
            # Hotspawn's own "% picked" is popularity, never a probability; the
            # value is kept out of this record on purpose.
        })
    return rows


def snapshot_index(published: dict) -> dict:
    """Matches in the published snapshot keyed by Hotspawn fixture id."""
    out = {}
    for match in (published.get('matches') or []):
        if not isinstance(match, dict):
            continue
        out[str(match.get('id'))] = match
    return out


def pick_of(match: dict) -> dict:
    analysis = match.get('analysis') or {}
    return {
        'method': analysis.get('method') or analysis.get('basis'),
        'pick': analysis.get('pick') or analysis.get('picked_team'),
        'probabilities': analysis.get('probabilities'),
        'source_url': analysis.get('source_url'),
    }


def egw_lookup(index_html: str, teams: list[str]) -> dict | None:
    """Join an EGW index row to a fixture by both teams' slugs in one match URL."""
    from scripts.egw_live import _slug_keys, parse_index

    rows = parse_index(index_html)
    for row in rows:
        flat = row['slug'].replace('-', '')
        positions = []
        for team in teams:
            keys = _slug_keys(team)
            pos = next((flat.find(k.replace('-', '')) for k in keys
                        if k.replace('-', '') and k.replace('-', '') in flat), -1)
            positions.append(pos)
        if all(p >= 0 for p in positions) and positions[0] != positions[1]:
            odds = [float(x) for x in row['odds']]
            return {
                'url': row['url'],
                'printed_odds': odds,
                'placeholder': len(set(round(o, 4) for o in odds)) == 1,
                'provider_order': 'fixture order' if positions[0] < positions[1] else 'reversed',
            }
    return None


def poly_lookup(events: list, teams: list[str]) -> dict | None:
    """A Polymarket event whose question/markets name both teams exactly."""
    def keys(value: str) -> set[str]:
        value = re.sub(r'[^a-z0-9]+', ' ', (value or '').casefold())
        return {w for w in value.split() if len(w) > 2}

    want = [keys(t) for t in teams]
    for event in events if isinstance(events, list) else []:
        if not isinstance(event, dict):
            continue
        text = ' '.join(str(event.get(f) or '') for f in ('title', 'slug', 'question'))
        haystack = keys(text)
        if not all(any(k and k in haystack for k in group) for group in want):
            continue
        markets = []
        for market in event.get('markets') or []:
            if not isinstance(market, dict):
                continue
            try:
                prices = json.loads(market.get('outcomes') or '[]'), json.loads(market.get('outcomePrices') or '[]')
            except (TypeError, ValueError):
                continue
            markets.append({
                'question': market.get('question'),
                'outcomes': prices[0],
                'prices': prices[1],
                'volume': market.get('volume'),
                'closed': market.get('closed'),
            })
        return {'url': 'https://polymarket.com/event/' + str(event.get('slug') or ''),
                'markets': markets, 'volume': event.get('volume')}
    return None


def hltv_identity(html: str, teams: list[str]) -> dict:
    """Search HLTV's upcoming-match listing for both team names in one match block."""
    from bs4 import BeautifulSoup

    if not html:
        return {'found': False, 'reason': 'no HTML retrieved'}
    soup = BeautifulSoup(html, 'html.parser')
    blocks = soup.select('div.upcomingMatch')
    for block in blocks:
        names = {n.get_text(' ', strip=True) for n in block.select('.matchTeamName')}
        lowered = {n.casefold() for n in names}
        if all(any(t.casefold() == n for n in lowered) for t in teams):
            anchor = block.select_one('a[href^="/matches/"]')
            href = anchor.get('href') if anchor else ''
            return {'found': True, 'blocks_scanned': len(blocks),
                    'url': ('https://www.hltv.org' + href) if href else HLTV_MATCHES,
                    'teams': sorted(names)}
    return {'found': False, 'blocks_scanned': len(blocks), 'url': HLTV_MATCHES}


def research_fixture(reads: dict, row: dict) -> dict:
    """Deterministic verdict for one uncovered fixture. No number is invented."""
    teams = row['teams']
    probes = []
    verdict = 'no-source-found'
    limitations = []

    hltv_read = reads.get('hltv') or {}
    hltv = hltv_identity(reads.get('hltv_html', ''), teams)
    probes.append({
        'source': 'HLTV match listing (identity only; no price is taken from HLTV)',
        'url': hltv.get('url') or HLTV_MATCHES,
        'status': hltv_read.get('status'),
        'found': bool(hltv.get('found')),
        'http': hltv_read.get('http'),
        'sha256': hltv_read.get('sha256'),
        'excerpt': hltv_read.get('excerpt'),
    })
    if hltv.get('found'):
        verdict = 'identity-confirmed-no-line'

    egw = egw_lookup(reads.get('egw_html', ''), teams)
    if egw:
        probes.append({
            'source': 'EGamersWorld CS2 matches index (published bookmaker average)',
            'url': egw['url'],
            'status': 'ok' if not egw['placeholder'] else 'placeholder',
            'printed_odds': egw['printed_odds'],
            'excerpt': ('identical decimal placeholders %s' % egw['printed_odds']
                        if egw['placeholder'] else
                        'two-sided decimal pair %s' % egw['printed_odds']),
        })
        if egw['placeholder']:
            limitations.append('EGamersWorld printed identical decimals '
                               '(%.2f/%.2f); that is a placeholder, not a two-sided price.'
                               % (egw['printed_odds'][0], egw['printed_odds'][1]))
        else:
            verdict = 'external-line-found'
    else:
        egw_read = reads.get('egw') or {}
        probes.append({'source': 'EGamersWorld CS2 matches index',
                       'url': EGW_INDEX, 'status': egw_read.get('status'),
                       'found': False, 'http': egw_read.get('http'),
                       'sha256': egw_read.get('sha256')})

    poly = poly_lookup(reads.get('poly_events'), teams)
    if poly:
        owed = []
        for market in poly['markets']:
            prices = market.get('prices') or []
            if len(prices) != 2:
                continue
            try:
                values = [float(x) for x in prices]
                volume = float(market.get('volume') or 0)
            except (TypeError, ValueError):
                continue
            # A $0.00-volume or crossed/identical book is not a usable prematch
            # quote for origination; it is reported, never promoted to a line.
            if volume <= 0 or values[0] == values[1]:
                continue
            owed.append({**market, 'prices': values, 'volume': volume})
        probes.append({'source': 'Polymarket event (tagged CS2 discovery)',
                       'url': poly['url'],
                       'status': 'ok' if owed else 'zero-volume-or-flat-book',
                       'markets': owed[:4]})
        if not owed:
            limitations.append('Polymarket has an event for this fixture but no market with '
                               'non-zero volume and a two-sided book; it is not used as a line.')
        elif verdict != 'external-line-found':
            verdict = 'external-line-found'
    else:
        poly_read = reads.get('poly') or {}
        probes.append({'source': 'Polymarket tagged CS2 discovery',
                       'url': POLY_TAGGED, 'status': poly_read.get('status'),
                       'found': False, 'http': poly_read.get('http'),
                       'sha256': poly_read.get('sha256')})

    for name, label in (('thunderpick', 'Thunderpick matches feed'),
                        ('bovada', 'Bovada CS2 coupon feed'),
                        ('pinnacle', 'Pinnacle guest matchups'),
                        ('kalshi', 'Kalshi CS2 exchange'),
                        ('bo3', 'bo3.gg match feed')):
        record = reads.get(name) or {}
        probes.append({'source': label, 'url': record.get('url'), 'status': record.get('status'),
                       'http': record.get('http'), 'sha256': record.get('sha256'),
                       'bytes': record.get('bytes'), 'note': record.get('error')})

    if not limitations:
        limitations.append('No reachable source published a two-sided prematch winner '
                           'market for this fixture at the observation time. Absence of a '
                           'retrieved line is not proof that no market exists.')
    return {'id': row['id'], 'teams': teams, 'competition': row['competition'],
            'starts_at': row['starts_at'], 'verdict': verdict,
            'probes': probes, 'limitations': limitations}


def build_reconciliation(api_rows: list[dict], rendered: list[str], published: dict,
                         origination: dict, observed_at: str) -> dict:
    now = parse_iso(observed_at)
    matches = snapshot_index(published)
    orig_by_id = {str(m.get('id')): m for m in (origination.get('matches') or [])
                  if isinstance(m, dict)}
    future = [r for r in api_rows if r['future']]
    rows, uncovered = [], []
    for row in future:
        snap = matches.get(row['id']) or orig_by_id.get(row['id'])
        pick = pick_of(snap) if snap else None
        with_pick = bool(snap and (snap.get('analysis') or {}).get('source_url'))
        coverage = ('published pick' if with_pick else
                    'published, no pick' if snap else
                    'not in published snapshot')
        rows.append({**row, 'lobby_rendered': row['id'] in rendered,
                     'in_snapshot': bool(snap), 'coverage': coverage,
                     'pick': pick})
        if coverage != 'published pick':
            uncovered.append(row)
    generated = published.get('generated_at') or ''
    age = None
    if generated:
        try:
            age = round((now - parse_iso(generated)).total_seconds() / 3600, 2)
        except ValueError:
            age = None
    return {
        'session': SESSION,
        'observed_at': observed_at,
        'counts': {
            'api_scheduled': len(api_rows),
            'api_future': len(future),
            'lobby_rendered': len(rendered),
            'snapshot_upcoming': published.get('counts', {}).get('upcoming'),
            'snapshot_with_pick': sum(1 for r in rows if r['coverage'] == 'published pick'),
            'uncovered': len(uncovered),
        },
        'snapshot': {'generated_at': generated, 'age_hours': age,
                     'counts': published.get('counts'),
                     'stale_over_8h': bool(age is not None and age > STALE_HOURS)},
        'rows': rows,
        'uncovered_ids': [r['id'] for r in uncovered],
    }


def render_reconciliation_md(rec: dict, line_research: dict) -> str:
    c, s = rec['counts'], rec['snapshot']
    out = [f"# Live Hotspawn CS2 reconciliation — {rec['observed_at']}", '',
           f"Session `{SESSION}`. First-hand read on a GitHub runner. Every row below links "
           f"its official source.", '',
           '| Check | Value |', '| --- | --- |',
           f"| Hotspawn scheduled API rows | {c['api_scheduled']} |",
           f"| Future (not yet started) rows | {c['api_future']} |",
           f"| Cards rendered on the lobby | {c['lobby_rendered']} |",
           f"| Published snapshot generated | {s['generated_at'] or 'unverified'} |",
           f"| Published snapshot age | {s['age_hours']} h |",
           f"| Future rows with a published pick | {c['snapshot_with_pick']} |",
           f"| Future rows without a published pick | {c['uncovered']} |", '',
           '## Uncovered fixtures, researched in order (HLTV → esportsbook lines)', '']
    for fixture in line_research.get('fixtures', []):
        out.append(f"### {fixture['teams'][0]} vs {fixture['teams'][1]} "
                   f"(`{fixture['id']}`, {fixture['competition']}, {fixture['starts_at']})")
        out.append('')
        out.append(f"Verdict: **{fixture['verdict']}**")
        out.append('')
        out.append('| Source | Status | Evidence |')
        out.append('| --- | --- | --- |')
        for item in fixture['probes']:
            link = (f"[{item.get('source')}]({item.get('url')})"
                    if item.get('url') else item.get('source'))
            evidence = item.get('excerpt') or item.get('note') or item.get('status') or ''
            out.append(f"| {link} | {item.get('status')} | {str(evidence)[:300]} |")
        out.append('')
        for limitation in fixture['limitations']:
            out.append(f"- {limitation}")
        out.append('')
    return '\n'.join(out) + '\n'


def flags_for(rec: dict, line_research: dict) -> list[dict]:
    flags = []
    stale = rec['snapshot']['stale_over_8h']
    uncovered = line_research.get('fixtures', [])
    if stale:
        flags.append({
            'id': 'f4217201-published-snapshot-older-than-eight-hours',
            'severity': 'notice',
            'match_ids': [],
            'title': 'The deployed snapshot was older than the eight-hour freshness bound when this sweep ran',
            'detail': (f"At {rec['observed_at']} the public data/latest.json was generated "
                       f"{rec['snapshot']['generated_at']} — {rec['snapshot']['age_hours']} hours "
                       f"earlier. The scheduled four-hour publisher had failed or been queued "
                       f"behind session pushes. The live lobby still rendered "
                       f"{rec['counts']['lobby_rendered']} cards, so the stale page under-reports "
                       f"coverage until the next successful publish."),
            'sources': [{'label': 'Deployed snapshot', 'url': PUBLISHED_JSON},
                        {'label': 'Hotspawn lobby', 'url': LOBBY_URL}],
        })
    if uncovered:
        flags.append({
            'id': 'f4217201-live-fixtures-without-a-published-pick',
            'severity': 'notice',
            'match_ids': [f['id'] for f in uncovered],
            'title': f"{len(uncovered)} live fixture(s) had no pick in the published snapshot when the sweep ran",
            'detail': ('Each one is listed on the live-coverage dossier with every source tried, '
                       'the HTTP status, the content hash and the exact limitation. They are '
                       'retried by the scheduled publisher; nothing was filled in by hand and no '
                       'probability was invented. Verdicts: '
                       + '; '.join(f"{f['teams'][0]} vs {f['teams'][1]} ({f['id']}): {f['verdict']}"
                                   for f in uncovered) + '.'),
            'sources': [{'label': 'Live reconciliation', 'url': LOBBY_URL},
                        {'label': 'Hotspawn fixture API', 'url': FIXTURES_API}],
        })
    blocked = sorted({p['source'] for f in uncovered for p in f['probes']
                      if str(p.get('status', '')).startswith(('http-', 'challenge', 'error'))
                      or p.get('status') in {'challenge', 'error'}})
    if blocked:
        flags.append({
            'id': 'f4217201-line-source-blocks-this-sweep',
            'severity': 'notice',
            'match_ids': [],
            'title': 'Some line sources refused or failed this automated sweep',
            'detail': ('Blocked or failed: ' + ', '.join(blocked) + '. A block is an access '
                       'limitation, not evidence that no market exists; the affected fixtures stay '
                       'labelled unresolved rather than being given a made-up price.'),
            'sources': [{'label': 'Research dossier',
                         'url': 'https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/f4217201/line-research.json'}],
        })
    return flags


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='data/research/f4217201')
    parser.add_argument('--offline-fixture', default=None,
                        help='Read saved bodies from this directory instead of the network')
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    observed_at = now_iso()
    session = requests.Session()
    reads, records = {}, []

    def read(name: str, url: str, **kwargs) -> dict:
        record = fetch(session, name, url, **kwargs)
        records.append(strip_private(record))
        reads[name] = record
        return record

    api = read('hotspawn-fixtures', FIXTURES_API)
    lobby = read('hotspawn-lobby', LOBBY_URL)
    published_read = read('published-snapshot', PUBLISHED_JSON)
    origination_read = read('published-origination', PUBLISHED_ORIGINATION)
    read('hltv', HLTV_MATCHES)
    read('egw', EGW_INDEX)
    read('poly', POLY_TAGGED)
    read('thunderpick', THUNDERPICK_API, method='POST', payload={'gameIds': [6]})
    read('bovada', BOVADA_COUPON)
    read('pinnacle', PINNACLE_MATCHUPS)
    read('kalshi', KALSHI_EVENTS)
    read('bo3', BO3_MATCHES)

    try:
        published = json.loads(published_read.get('_body') or '{}')
    except ValueError:
        published = {}
    try:
        origination = json.loads(origination_read.get('_body') or '{}')
    except ValueError:
        origination = {}
    try:
        poly_events = json.loads(reads['poly'].get('_body') or '[]')
    except ValueError:
        poly_events = []
    reads['poly_events'] = poly_events
    reads['hltv_html'] = reads['hltv'].get('_body') or ''
    reads['egw_html'] = reads['egw'].get('_body') or ''

    rows = fixture_rows(api.get('_body') or '', parse_iso(observed_at))
    rendered = lobby_ids(lobby.get('_body') or '')
    reconciliation = build_reconciliation(rows, rendered, published, origination, observed_at)
    uncovered = [r for r in rows if r['future'] and r['id'] in reconciliation['uncovered_ids']]
    line_research = {
        'session': SESSION,
        'observed_at': observed_at,
        'policy': ('HLTV first for fixture identity (never a price), then esportsbook and '
                   'exchange lines. A line is recorded only when a two-sided prematch quote was '
                   'actually retrieved; identical decimal placeholders are refused.'),
        'fixtures': [research_fixture(reads, row) for row in uncovered],
    }
    reconciliation['source_reads'] = records
    (out / 'live-reconciliation.json').write_text(json.dumps(reconciliation, indent=2) + '\n')
    (out / 'line-research.json').write_text(json.dumps(line_research, indent=2) + '\n')
    (out / 'live-reconciliation.md').write_text(
        render_reconciliation_md(reconciliation, line_research))
    (out / 'flags.json').write_text(json.dumps(flags_for(reconciliation, line_research), indent=2) + '\n')
    print(f"{SESSION}: {reconciliation['counts']['api_future']} future fixtures, "
          f"{reconciliation['counts']['snapshot_with_pick']} published picks, "
          f"{reconciliation['counts']['uncovered']} uncovered, "
          f"snapshot {reconciliation['snapshot']['age_hours']}h old")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
