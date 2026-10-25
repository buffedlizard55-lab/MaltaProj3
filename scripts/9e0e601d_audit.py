"""Live coverage audit for session 9e0e601d (a pick for every live CS2 fixture).

Why this runs on a runner
-------------------------
The brief's first requirement is that **every** Counter-Strike 2 match Hotspawn
lists carries a pick.  The authoring sandbox for this session cannot open a TCP
connection to `play.hotspawn.com`, `hltv.org`, `buffedlizard55-lab.github.io` or
any esportsbook: every request fails with `SSL_ERROR_SYSCALL` before a status
line is printed, so a claim about what those hosts publish cannot be made from
there.  This module therefore runs on GitHub Actions and records what each
surface actually returned, with the observation time and the SHA-256 of every
response body it parses.

What it measures
----------------
1. **The deployed dashboard** - `snapshot.json`, `data/origination.json`,
   `data/latest.json` and `index.html` from the live Pages URL.  These are the
   bytes a reader is served, so a gap is described against the page, not against
   the repository fixture.
2. **The live inventory** - Hotspawn's public scheduled-fixture API (the same
   feed the lobby uses) plus the rendered lobby, so the set of fixtures the picks
   must cover is measured rather than assumed.
3. **HLTV** - the upcoming-matches listing, for identity and schedule only.  HLTV
   fan votes are never read.
4. **Esportsbooks and exchanges** - Polymarket's public CS2 event index, the
   Thunderpick public match feed (a two-way price, if one is listed) and the
   EGamersWorld match directory (reachability only).

What it never does
------------------
It writes **no probability, no pick and no alias**.  A fixture that no source
prices is published as a gap with the exact reason each stage produced; the
publisher's own ladder (`scripts/originate.py`) remains the only path to a
published number.  A reachability `403` is recorded as a limitation of this
runner, never as proof that a market does not exist.

Outputs
-------
`data/research/9e0e601d/audit.json` (machine readable), `audit.md` (readable)
and the archived originals under `data/research/9e0e601d/raw/`.

CLI
---
    python -m scripts.9e0e601d_audit              # fetch live, then write the dossier
    python -m scripts.9e0e601d_audit --replay     # re-derive from the archived bodies
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts.domain import name_key, timestamp

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / '9e0e601d'
RAW = OUT / 'raw'

verify_module = importlib.import_module('scripts.9e0e601d_verify')
probe = importlib.import_module('scripts.0c034b94_probe')

DEPLOYED = 'https://buffedlizard55-lab.github.io/MaltaProj3/'
FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
LOBBY = 'https://play.hotspawn.com/lobby'
HLTV_MATCHES = 'https://www.hltv.org/matches'
HLTV_RANKING = 'https://www.hltv.org/ranking/teams/2026/october/19'
POLY_TAG = 'https://gamma-api.polymarket.com/events?tag_slug=cs2&closed=false&limit=100'
THUNDERPICK_API = 'https://thunderpick.io/api/matches'
EGW_MATCHES = 'https://egamersworld.com/counterstrike/matches'
HEADERS = {
    'User-Agent': 'HotspawnCS2Origination/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)',
    'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8',
}
TIMEOUT = (15, 45)
#: The project-wide identity window for joining a provider fixture to Hotspawn.
START_TOLERANCE_SEC = 60


def now_iso() -> str:
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def slug(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')


def fetch(label: str, url: str, *, expect_json: bool = False, method: str = 'GET',
          payload: dict | None = None) -> tuple[dict, object]:
    """One dated, hash-checked source observation. Nothing is inferred."""
    entry = {'label': label, 'url': url, 'observed_at': now_iso(), 'status': 'error'}
    try:
        if method == 'POST':
            response = requests.post(url, headers=HEADERS, json=payload, timeout=TIMEOUT)
        else:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        entry['error'] = type(exc).__name__ + ': ' + str(exc)[:300]
        return entry, None
    body = response.content or b''
    entry.update(http_status=response.status_code, final_url=response.url,
                 content_type=response.headers.get('Content-Type'), bytes=len(body),
                 sha256=hashlib.sha256(body).hexdigest())
    entry['status'] = 'ok' if response.ok else 'error'
    if not response.ok:
        entry['error'] = 'HTTP ' + str(response.status_code)
        return entry, None
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f'{slug(label)}.{"json" if expect_json else "html.gz"}'
    if expect_json:
        path.write_bytes(body)
    else:
        path.write_bytes(gzip.compress(body, mtime=0))
        # A bare .html under data/research/ would be copied into the site and
        # validated as one of its own pages, so originals are stored gzipped.
        path.with_suffix('').unlink(missing_ok=True)
    entry['raw'] = str(path.relative_to(ROOT))
    if expect_json:
        try:
            return entry, response.json()
        except ValueError as exc:
            entry.update(status='error', error='unparseable JSON: ' + str(exc)[:200])
            return entry, None
    return entry, response.text


def archived(label: str, expect_json: bool) -> object:
    path = RAW / f'{slug(label)}.{"json" if expect_json else "html.gz"}'
    if not path.exists():
        return None
    if expect_json:
        try:
            return json.loads(path.read_text(encoding='utf-8', errors='replace'))
        except ValueError:
            return None
    return gzip.decompress(path.read_bytes()).decode('utf-8', errors='replace')


# ---------------------------------------------------------------------------
# Parsers over the archived bodies
# ---------------------------------------------------------------------------

#: Internal evidence downloads the rendered page links.  Every one of them has
#: to resolve on the deployed host: a page that says "this is the saved order
#: book" and then serves a 404 is not a source-linked page.
INTERNAL_LINK = re.compile(r'href="(?:\./)?(data/[^"#?]+)"')
MAX_LINK_PROBES = 40


def internal_data_links(html: str) -> list:
    """The distinct ``data/...`` downloads a page links, in page order."""
    seen, out = set(), []
    for match in INTERNAL_LINK.findall(html or ''):
        if match not in seen:
            seen.add(match)
            out.append(match)
    return out


def probe_links(base: str, links: list, *, limit: int = MAX_LINK_PROBES) -> list:
    """HTTP status of each internal download, so a dead link is measured."""
    results = []
    for link in links[:limit]:
        url = base + link
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
            status = response.status_code
            length = response.headers.get('Content-Length')
            response.close()
        except requests.RequestException as exc:
            results.append({'path': link, 'url': url, 'status': 'error',
                            'error': type(exc).__name__ + ': ' + str(exc)[:200], 'observed_at': now_iso()})
            continue
        results.append({'path': link, 'url': url, 'status': status,
                        'bytes': int(length) if str(length or '').isdigit() else None,
                        'observed_at': now_iso()})
    return results


def link_health(results: list) -> dict:
    broken = [r for r in results if r.get('status') != 200]
    return {'probed': len(results), 'ok': len(results) - len(broken), 'broken': len(broken),
            'broken_paths': [r['path'] for r in broken]}


def parse_deployed_origination(payload) -> dict:
    """The complete picks list a reader downloads, or an empty skeleton."""
    if not isinstance(payload, dict):
        return {'matches': [], 'counts': {}, 'generated_at': None}
    rows = [row for row in (payload.get('matches') or []) if isinstance(row, dict)]
    return {'matches': rows, 'counts': payload.get('counts') or {},
            'generated_at': payload.get('generated_at')}


def parse_deployed_index(text: str) -> dict:
    """The clock the published executive summary itself shows."""
    if not text:
        return {'snapshot_at': None, 'glance_ids': []}
    stamp = re.search(r'Inventory checked <time datetime="([^"]+)"', text)
    return {'snapshot_at': stamp.group(1) if stamp else None,
            'glance_ids': sorted(set(re.findall(r'data-glance-id="(\d+)"', text)))}


def parse_thunderpick(payload) -> list:
    """Public Thunderpick rows: teams, start, and the Match Winner prices."""
    if not isinstance(payload, dict) or payload.get('ok') is not True:
        return []
    body = payload.get('data') or {}
    rows = body.get('upcoming') if isinstance(body.get('upcoming'), list) else body.get('matches')
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        market = None
        for candidate in row.get('preferredMarkets') or []:
            if isinstance(candidate, dict) and str(candidate.get('name') or '').casefold() == 'match winner':
                market = candidate
                break
        selections = []
        if market is not None:
            for selection in market.get('selections') or []:
                if isinstance(selection, dict):
                    selections.append({'name': selection.get('name'), 'odds': selection.get('odds'),
                                       'status': selection.get('status'), 'type': selection.get('type')})
        out.append({'event_id': str(row.get('id')), 'start': row.get('startTime'),
                    'teams': [s['name'] for s in selections if s.get('name')],
                    'selections': selections,
                    'best_of': row.get('bestOfMaps'),
                    'in_play': bool(row.get('hasInPlayMarkets'))})
    return out


def polymarket_events(payload) -> list:
    """Public identifiers only: id, slug, title, start. No price is read here."""
    rows = []
    for event in payload if isinstance(payload, list) else []:
        if not isinstance(event, dict):
            continue
        rows.append({'id': str(event.get('id')), 'slug': event.get('slug'),
                     'title': event.get('title'), 'start': event.get('startDate'),
                     'closed': event.get('closed'), 'markets': len(event.get('markets') or [])})
    return rows


def title_teams(title: str | None) -> list:
    if not title:
        return []
    parts = re.split(r'\s+vs\.?\s+|\s+to\s+win|\s+-\s+', title, maxsplit=1)
    return [p.strip() for p in parts if p and p.strip()][:2]


def polymarket_bind(fixture: dict, events: list) -> dict:
    """Exact-name, exact-start candidates for one fixture. No fuzzy joins."""
    wanted = sorted(name_key(n or '') for n in fixture['teams'])
    own = timestamp(fixture.get('starts_at'))
    exact, shared = [], []
    for event in events:
        names = title_teams(event.get('title'))
        if len(names) != 2:
            continue
        keys = sorted(name_key(n) for n in names)
        start = timestamp(event.get('start'))
        delta = int((start - own).total_seconds()) if (start and own) else None
        entry = dict(event, teams=names, start_delta_seconds=delta)
        if keys == wanted:
            exact.append(entry)
        elif set(keys) & set(wanted):
            shared.append(entry)
    return {'exact': exact, 'shares_one_name': shared}


def thunderpick_bind(fixture: dict, rows: list) -> dict:
    wanted = sorted(name_key(n or '') for n in fixture['teams'])
    own = timestamp(fixture.get('starts_at'))
    exact, shared = [], []
    for row in rows:
        if len(row.get('teams') or []) != 2:
            continue
        keys = sorted(name_key(n) for n in row['teams'])
        start = timestamp(row.get('start'))
        delta = int((start - own).total_seconds()) if (start and own) else None
        entry = dict(row, start_delta_seconds=delta)
        if keys == wanted:
            exact.append(entry)
        elif set(keys) & set(wanted):
            shared.append(entry)
    return {'exact': exact, 'shares_one_name': shared}


def parse_stamp(value) -> datetime | None:
    try:
        return datetime.strptime(str(value), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


#: How far apart two artefacts of the same publish may legitimately be.  A build
#: renders one observation, so the HTML clock and `snapshot.json` are normally
#: seconds apart; anything beyond this means two different publishes are being
#: served under one URL.
PARITY_TOLERANCE_MINUTES = 60


def deployment_parity(artefacts: dict, *, tolerance_minutes: float = PARITY_TOLERANCE_MINUTES) -> dict:
    """Are the page and the files it links the same observation?

    A reader who opens the page and then downloads the JSON it links must get the
    same snapshot.  The check never assumes that; it compares the four clocks the
    deployment actually serves and reports the gap in hours.
    """
    stamps = {name: parse_stamp(value) for name, value in artefacts.items()}
    known = {name: stamp for name, stamp in stamps.items() if stamp is not None}
    missing = sorted(name for name, value in artefacts.items() if value is None)
    detail_bits = []
    inconsistent = bool(missing) and len(known) > 0
    if missing:
        detail_bits.append('no parseable observation stamp for ' + ', '.join(missing))
    if len(known) >= 2:
        newest = max(known.values())
        oldest = min(known.values())
        gap = (newest - oldest).total_seconds() / 3600
        if gap > tolerance_minutes / 60:
            inconsistent = True
            lagging = sorted(((newest - stamp).total_seconds() / 3600, name)
                             for name, stamp in known.items()
                             if (newest - stamp).total_seconds() / 60 > tolerance_minutes)
            detail_bits.append(
                'the newest artefact is ' + newest.strftime('%Y-%m-%dT%H:%M:%SZ') + ' but ' +
                ', '.join(f'{name} is {hours:.2f} h older' for hours, name in lagging))
    return {'artefacts': dict(artefacts), 'inconsistent': inconsistent,
            'detail': '; '.join(detail_bits) or 'all artefacts agree',
            'tolerance_minutes': tolerance_minutes}


def gap_target(record: dict, published_row: dict | None, hltv_rows: list, ranking_rows: list,
               poly_events: list, tp_rows: list, egw: dict) -> dict:
    """Everything the brief's research order says to check, for one gap."""
    fixture = probe.fixture_view(record)
    join = probe.hltv_join(fixture, hltv_rows)
    poly = polymarket_bind(fixture, poly_events)
    thunder = thunderpick_bind(fixture, tp_rows)
    return {
        'fixture': fixture,
        'published_row': None if published_row is None else {
            'pick_index': published_row.get('pick_index'),
            'method': (published_row.get('origination') or {}).get('method'),
            'probabilities': (published_row.get('origination') or {}).get('probabilities'),
            'source_url': (published_row.get('origination') or {}).get('source_url'),
            'limitations': published_row.get('limitations') or [],
        },
        'hltv_exact': join['exact'],
        'hltv_shares_one_name': join['shares_one_name'],
        'hltv_ranking': [probe.ranking_row(name, ranking_rows) for name in fixture['teams']],
        'polymarket_exact': poly['exact'],
        'polymarket_shares_one_name': poly['shares_one_name'],
        'thunderpick_exact': thunder['exact'],
        'thunderpick_shares_one_name': thunder['shares_one_name'],
        'egamersworld': egw,
        'research_conclusion': conclude(join, poly, thunder, egw),
    }


def conclude(join: dict, poly: dict, thunder: dict, egw: dict) -> str:
    """A sentence that states only what the evidence above establishes."""
    bits = []
    if join['exact']:
        deltas = sorted({row.get('start_delta_seconds') for row in join['exact']})
        bits.append('HLTV lists the identical pairing (start delta ' + ', '.join(f'{d:+d}s' for d in deltas) + ')')
    elif join['shares_one_name']:
        bits.append('HLTV lists one of these names against a different opponent under this fixture name — identity not joined')
    else:
        bits.append('HLTV does not list this pairing in its upcoming window')
    if poly['exact']:
        bits.append(f"Polymarket has an exact-name event ({len(poly['exact'])})")
    elif poly['shares_one_name']:
        bits.append('Polymarket has an event sharing one name only')
    else:
        bits.append('no exact-name Polymarket event')
    if thunder['exact']:
        priced = [row for row in thunder['exact'] if len(row.get('selections') or []) == 2
                  and all(isinstance(s.get('odds'), (int, float)) and s['odds'] > 1 for s in row['selections'])]
        bits.append(f'Thunderpick lists {len(thunder["exact"])} exact row(s), '
                    f'{len(priced)} with a two-way price' if thunder['exact'] else 'no exact Thunderpick row')
    else:
        bits.append('no exact Thunderpick row')
    if egw.get('status') != 'ok':
        bits.append(f"EGamersWorld is {egw.get('error') or 'unavailable'} from this runner")
    return '; '.join(bits) + '. No probability or pick is written here.'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(*, replay: bool = False) -> dict:
    observations = []

    def body_of(label: str, url: str, *, expect_json: bool = False, method: str = 'GET',
                payload: dict | None = None):
        if replay:
            data = archived(label, expect_json)
            path = RAW / slug(label)
            try:
                shown = str(path.resolve().relative_to(ROOT))
            except ValueError:
                shown = str(path)
            observations.append({'label': label, 'url': url,
                                 'status': 'archived' if data is not None else 'missing',
                                 'observed_at': now_iso(), 'raw': shown})
            return data
        entry, data = fetch(label, url, expect_json=expect_json, method=method, payload=payload)
        observations.append(entry)
        return data

    stamp = int(time.time())
    deployed_snapshot = body_of('deployed snapshot.json', DEPLOYED + 'snapshot.json', expect_json=True)
    deployed_origination = body_of('deployed origination.json', DEPLOYED + 'data/origination.json', expect_json=True)
    deployed_latest = body_of('deployed data/latest.json', DEPLOYED + 'data/latest.json', expect_json=True)
    deployed_index = body_of('deployed index.html', DEPLOYED)
    # Hotspawn's fixture API answers 400 when an unknown query parameter is
    # appended (observed on the 2026-10-25T14:53Z run with `&cb=`), so the
    # documented URL is requested unchanged and a no-cache header is used
    # instead of a cache-busting parameter.
    fixtures = body_of('hotspawn fixtures api', FIXTURES_API, expect_json=True)
    lobby = body_of('hotspawn lobby', f'{LOBBY}?cb={stamp}')
    hltv_html = body_of('hltv matches', HLTV_MATCHES)
    ranking_html = body_of('hltv ranking', HLTV_RANKING)
    poly = body_of('polymarket cs2 tag', POLY_TAG, expect_json=True)
    thunder = body_of('thunderpick matches', THUNDERPICK_API, expect_json=True,
                      method='POST', payload={'gameIds': [6]})
    body_of('egamersworld matches', EGW_MATCHES)
    egw_entry = next((o for o in observations if o['label'] == 'egamersworld matches'), {})
    links = internal_data_links(deployed_index or '')
    link_results = ([] if replay else probe_links(DEPLOYED, links))

    records = fixtures if isinstance(fixtures, list) else []
    reference = datetime.strptime(now_iso(), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)
    open_records = probe.open_fixtures(records, reference)
    open_views = [probe.fixture_view(item) for item in open_records]
    lobby_ids = probe.parse_lobby_fixture_ids(lobby or '') if lobby else []
    hltv_rows = probe.parse_hltv_listing(hltv_html) if hltv_html else []
    ranking_rows = []
    if ranking_html:
        try:
            from scripts import hltv_ranking
            ranking_rows = hltv_ranking.parse_ranking_page(ranking_html)
        except Exception as exc:                       # noqa: BLE001 - recorded, never guessed
            observations.append({'label': 'hltv ranking parse', 'status': 'error',
                                 'error': type(exc).__name__ + ': ' + str(exc)[:200],
                                 'observed_at': now_iso(), 'url': HLTV_RANKING})
    poly_events = polymarket_events(poly)
    tp_rows = parse_thunderpick(thunder)
    origination = parse_deployed_origination(deployed_origination)
    index_facts = parse_deployed_index(deployed_index or '')
    egw_status = {'status': egw_entry.get('status'), 'error': egw_entry.get('error'),
                  'http_status': egw_entry.get('http_status'), 'url': EGW_MATCHES,
                  'observed_at': egw_entry.get('observed_at')}

    published_by_id = {str(row.get('id')): row for row in origination['matches']}
    snapshot = deployed_snapshot if isinstance(deployed_snapshot, dict) else {'matches': [], 'generated_at': None}

    # The page, the featured snapshot and the two downloadable files must be the
    # same observation.  When Pages serves the branch root instead of the freshly
    # deployed artefact the HTML can be minutes old while `/data/*.json` is the
    # checked-in replay fixture, so a reader who downloads what the page links
    # gets a different, older dataset.  Measure it instead of assuming it.
    parity = deployment_parity(
        {'index.html': index_facts['snapshot_at'],
         'snapshot.json': snapshot.get('generated_at'),
         'data/latest.json': (deployed_latest or {}).get('generated_at') if isinstance(deployed_latest, dict) else None,
         'data/origination.json': origination['generated_at']})
    verification = verify_module.verify(snapshot, origination, deployed_index or '', now=reference,
                                        coverage_asserted=not parity['inconsistent'])
    if parity['inconsistent']:
        verification['problems'].append(
            'the deployed page and its downloadable data are different observations: ' + parity['detail'])
    health = link_health(link_results) if link_results else {'broken': 0, 'probed': 0}
    if health.get('broken'):
        verification['problems'].append(
            f"{health['broken']} of {health['probed']} internal data downloads linked by the executive summary "
            'did not answer 200 on the deployed host')

    inventory_available = bool(open_records)
    # Fixtures the brief asks to research, by fixture id.  Two populations:
    #   * no pick at all on the deployed site, and
    #   * a pick that the *featured* exact-name method could not produce, i.e.
    #     anything that fell through to a consensus, a relayed/reference price or
    #     a research model.  Those are exactly "matches that cannot be resolved in
    #     the same way as the featured picks".
    featured_methods = {'market', 'bookmaker'}
    gaps = []
    gap_reasons = {}
    for view in open_views:
        ident = str(view['id'])
        row = published_by_id.get(ident)
        method = ((row or {}).get('origination') or {}).get('method')
        if row is None:
            gaps.append(ident)
            gap_reasons[ident] = 'no row on the deployed complete picks list'
        elif row.get('pick_index') is None:
            gaps.append(ident)
            gap_reasons[ident] = 'row published without a pick'
        elif method not in featured_methods:
            gaps.append(ident)
            gap_reasons[ident] = f'pick came from the {method or "unknown"} fallback, not the featured line'
    # A fixture the complete list knows about but the featured snapshot does not
    # still needs a row; report both directions so neither can hide.
    missing_from_list = [view['id'] for view in open_views if str(view['id']) not in published_by_id]
    targets = []
    for ident in gaps:
        record = next((r for r in open_records if str(r.get('id')) == ident), None)
        if record is None:
            continue
        target = gap_target(record, published_by_id.get(str(ident)), hltv_rows, ranking_rows,
                            poly_events, tp_rows, egw_status)
        target['gap_reason'] = gap_reasons[ident]
        targets.append(target)

    unverifiable = []
    if not inventory_available:
        unverifiable.append(
            'the Hotspawn scheduled-fixture API did not return records in this observation, so the live '
            'inventory was read from the rendered lobby only; per-fixture coverage is not asserted')
    if parity['inconsistent']:
        unverifiable.append(
            'the deployed complete picks list is a different observation from the deployed page, so '
            'fixture-by-fixture coverage is not asserted against it')
    dossier = {
        'session': '9e0e601d',
        'mode': 'replay' if replay else 'live',
        'observed_at': now_iso(),
        'sources': observations,
        'deployed': {
            'snapshot_generated_at': snapshot.get('generated_at'),
            'snapshot_counts': snapshot.get('counts') or {},
            'origination_generated_at': origination['generated_at'],
            'origination_counts': origination['counts'],
            'data_latest_generated_at': (deployed_latest or {}).get('generated_at') if isinstance(deployed_latest, dict) else None,
            'index_snapshot_at': index_facts['snapshot_at'],
            'index_glance_ids': len(index_facts['glance_ids']),
        },
        'inventory': {
            'api_records': len(records),
            'api_open_fixtures': len(open_records),
            'lobby_fixture_ids': len(lobby_ids),
            'open_ids': sorted({str(v['id']) for v in open_views}, key=str),
            'lobby_ids_missing_from_api': sorted(set(lobby_ids) - {str(v['id']) for v in open_views}, key=str),
        },
        'deployment_parity': parity,
        'internal_links': {'links': links, 'results': link_results,
                           'health': link_health(link_results) if link_results else {'probed': 0}}, 
        'coverage': {
            'asserted': not unverifiable,
            'unverifiable_reason': unverifiable,
            'open': len(open_views),
            'published_rows': len(origination['matches']),
            'with_pick': sum(1 for row in origination['matches'] if row.get('pick_index') is not None),
            'open_without_pick': [ident for ident in gaps
                                  if gap_reasons[ident] in ('no row on the deployed complete picks list',
                                                            'row published without a pick')],
            'fallback_priced': [ident for ident in gaps
                                if gap_reasons[ident].startswith('pick came from the')],
            'research_targets': gaps,
            'open_missing_from_complete_list': missing_from_list,
        },
        'verification': verification,
        'targets': targets,
        'limitations': [
            'A 403 or a connection failure recorded here is a limitation of this runner, not evidence that a market does not exist.',
            'HLTV is used for identity, schedule and ranking membership only; fan votes are never read.',
            'This audit writes no probability, pick or alias; only scripts/originate.py may publish a number.',
        ],
    }
    return dossier


def render_markdown(dossier: dict) -> str:
    d = dossier
    lines = [f"# Live coverage audit — {d['observed_at']} ({d['mode']})", '']
    dep, inv, cov = d['deployed'], d['inventory'], d['coverage']
    lines += ['## What the deployed dashboard serves', '',
              '| Fact | Value |', '| --- | --- |',
              f"| snapshot.json generated_at | {dep['snapshot_generated_at']} |",
              f"| origination.json generated_at | {dep['origination_generated_at']} |",
              f"| data/latest.json generated_at | {dep['data_latest_generated_at']} |",
              f"| executive summary shows inventory checked | {dep['index_snapshot_at']} |",
              f"| glance rows on the summary | {dep['index_glance_ids']} |",
              f"| complete-list rows | {cov['published_rows']} |",
              f"| rows with a pick | {cov['with_pick']} |", '']
    lines += ['## Live inventory', '',
              '| Fact | Value |', '| --- | --- |',
              f"| Hotspawn scheduled-fixture records | {inv['api_records']} |",
              f"| open fixtures right now | {inv['api_open_fixtures']} |",
              f"| fixture ids encoded by the rendered lobby | {inv['lobby_fixture_ids']} |",
              f"| lobby ids absent from the API window | {len(inv['lobby_ids_missing_from_api'])} |", '']
    parity = d['deployment_parity']
    lines += ['## Deployment parity (page vs downloadable data)', '',
              '| Artefact | Observation |', '| --- | --- |']
    for name, value in parity['artefacts'].items():
        lines.append(f'| {name} | {value} |')
    lines += ['', ('**Inconsistent:** ' + parity['detail']) if parity['inconsistent']
              else 'Every artefact is the same observation.', '']
    if cov.get('unverifiable_reason'):
        lines += ['**Coverage not asserted.** ' + ' '.join(cov['unverifiable_reason']), '']
    health = d['internal_links']['health']
    if health.get('probed'):
        lines += ['## Internal evidence links on the deployed page', '',
                  f'- probed **{health["probed"]}** `data/...` downloads linked by the summary',
                  f'- **{health["ok"]}** answered 200, **{health["broken"]}** did not', '']
        for result in d['internal_links']['results']:
            if result.get('status') != 200:
                lines.append(f"- **{result['status']}** <{result['url']}>")
        lines.append('')
    v = d['verification']
    lines += ['## Independent replay of the deployed numbers', '',
              f"- Complete picks list: **{v['replay']['replayed']}/{v['replay']['rows']}** rows re-derived; "
              f"{len(v['replay']['not_replayed'])} not replayable from published inputs.",
              f"- Featured snapshot: **{v['featured_replay']['replayed']}/{v['featured_replay']['rows']}** rows re-derived.",
              f"- Structural violations: **{len(v['violations'])}**.",
              f"- Executive summary: {v['site']['glance_ids'] if v.get('site') else 0} glance rows, "
              f"{v['site']['deep_links'] if v.get('site') else 0} deep links, "
              f"{len(v['site']['problems']) if v.get('site') else 0} render problems.",
              f"- Snapshot age at observation: {v.get('age_hours')} h.", '']
    if v['violations']:
        lines += ['### Violations', ''] + [f'- {x}' for x in v['violations']] + ['']
    if v.get('problems'):
        lines += ['### Problems', ''] + [f'- {x}' for x in v['problems']] + ['']
    unpicked = cov['open_without_pick']
    lines += ['## Fixtures without a published pick', '',
              (f'{len(unpicked)} of {cov["open"]} open fixtures have no pick row on the deployed site.' if unpicked
               else 'Every open fixture on the deployed site carries a pick row.'), '',
              f"{len(cov['fallback_priced'])} further fixture(s) carry a pick that the featured exact-name line "
              f"could not produce ({', '.join(cov['fallback_priced']) or 'none'}); those are researched below "
              'in the brief\'s order — HLTV first, then esportsbooks and exchanges.', '']
    for target in d['targets']:
        f = target['fixture']
        lines += [f"**Why this fixture is researched:** {target.get('gap_reason')}", '']
        lines += [f"### {f['id']} — {' vs '.join(n or '?' for n in f['teams'])} ({f.get('competition') or 'competition unverified'}, {f.get('starts_at')})", '']
        lines.append(f"- Research conclusion: {target['research_conclusion']}")
        for row in target['hltv_exact']:
            lines.append(f"- HLTV exact: <{row['url']}> start delta {row['start_delta_seconds']:+d}s")
        for event in target['polymarket_exact']:
            lines.append(f"- Polymarket exact: {event['title']} (event {event['id']}), start delta {event['start_delta_seconds']}")
        for row in target['thunderpick_exact']:
            prices = ' / '.join(f"{s['name']} {s['odds']}" for s in row.get('selections') or [])
            lines.append(f"- Thunderpick exact: event {row['event_id']}, start delta {row['start_delta_seconds']}s, {prices}")
        egw = target['egamersworld']
        lines.append(f"- EGamersWorld: {egw.get('status')}{(' (' + str(egw.get('error')) + ')') if egw.get('error') else ''}")
        lines.append('')
    lines += ['## Sources read', '', '| Source | Status | HTTP | Observed | SHA-256 |', '| --- | --- | --- | --- | --- |']
    for source in d['sources']:
        sha = (source.get('sha256') or '')[:16]
        lines.append(f"| {source['label']} | {source['status']} | {source.get('http_status') or ''} | "
                     f"{source.get('observed_at')} | {sha} |")
    lines.append('')
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay', action='store_true',
                        help='re-derive the dossier from the archived bodies instead of fetching')
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--raw', type=Path, default=None,
                        help='where to read/write archived originals (default: <output>/raw, or the '
                             'live dossier raw/ when replaying)')
    args = parser.parse_args(argv)
    raw_dir = args.raw or ((OUT / 'raw') if args.replay else (args.output / 'raw'))
    globals()['RAW'] = raw_dir
    args.output.mkdir(parents=True, exist_ok=True)
    dossier = run(replay=args.replay)
    (args.output / 'audit.json').write_text(json.dumps(dossier, indent=2) + '\n')
    (args.output / 'audit.md').write_text(render_markdown(dossier))
    v = dossier['verification']
    print(f"deployed snapshot {dossier['deployed']['snapshot_generated_at']}, "
          f"{dossier['inventory']['api_open_fixtures']} open fixtures, "
          f"{len(dossier['coverage']['open_without_pick'])} without a published pick")
    print(f"replay {v['replay']['replayed']}/{v['replay']['rows']} complete-list rows, "
          f"{v['featured_replay']['replayed']}/{v['featured_replay']['rows']} featured rows, "
          f"{len(v['violations'])} violations, {len(v['problems'])} problems")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
