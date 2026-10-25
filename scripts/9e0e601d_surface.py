"""Measure the *deployed* Pages surface, not the repository that should produce it.

Why this exists
---------------
``scripts.verify_live`` runs inside the publisher and reads a fixed list of
JSON endpoints. It never asks the question a reader asks: *does every download
this page links actually exist on the public site?* On 2026-10-25T15:04:56Z the
answer was no — 15 of the 24 local ``data/...`` downloads the served page linked
answered **404** (dossier ``data/research/0962d605``), while the publisher's own
verification was green, because it fetched a whitelist rather than the links the
HTML carries.

This module is the independent check, run from a network-capable Actions runner
(this sandbox cannot open a TCP connection to the Pages host at all):

1. every published page is fetched and its local ``href``/``src`` targets are
   fetched too, so a 404 download is a recorded fact with a status code rather
   than an inference from the repository;
2. the live ``snapshot.json`` / ``origination.json`` are compared with the live
   Hotspawn CS2 inventory (scheduled-fixtures API plus the rendered lobby, whose
   fixture ids the lobby's embedded JSON carries) — every open fixture must have
   a published row with a pick, and a row whose fixture is gone is reported as
   retired;
3. the run writes ``data/research/9e0e601d/surface.json`` (machine readable,
   with a SHA-256 and byte count per response) and ``surface.md`` (the same
   facts for a reader), so the claim is replayable and datable.

No probability, pick or alias is computed here. Hotspawn's ``% picked`` and
HLTV fan votes are never read: only fixture identity, teams, start time and
status are used, and the probabilities are read back from the deployed JSON that
already published them.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

SITE = 'https://buffedlizard55-lab.github.io/MaltaProj3/'

#: The pages a reader can reach from the executive summary. ``''`` is the
#: landing page; every other entry is a category subpage.
PAGES = ['', 'picks/', 'origination/', 'unresolved/', 'review/', 'methodology/',
         'coverage/', 'edge/', 'strategy/', 'final-day/', 'twc-picks/']

#: The Hotspawn CS2 inventory (public, unauthenticated).
FIXTURE_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/'
               'fixtures?sport_alias=cs2&status=scheduled&tenantId=1')
LOBBY_URL = 'https://play.hotspawn.com/lobby'

LOCAL_LINK_RE = re.compile(r'(?:href|src)="([^"]+)"')
USER_AGENT = 'Mozilla/5.0 (compatible; MaltaProj3-surface-audit/1; +github-actions)'


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def fetch(session: requests.Session, url: str, *, attempts: int = 3) -> dict:
    """GET ``url`` and record what actually came back, retrying only on transport errors."""
    last = ''
    for attempt in range(attempts):
        try:
            response = session.get(url, timeout=45, headers={
                'User-Agent': USER_AGENT,
                'Cache-Control': 'no-cache',
                'Accept': '*/*',
            })
            body = response.content or b''
            record = {
                'url': url,
                'status': response.status_code,
                'bytes': len(body),
                'sha256': sha256(body) if body else None,
                'content_type': response.headers.get('Content-Type', ''),
                'attempts': attempt + 1,
                # Kept in memory only; stripped before the dossier is written.
                '_body': body,
            }
            if response.status_code >= 500 and attempt + 1 < attempts:
                last = f'HTTP {response.status_code}'
                time.sleep(2 * (attempt + 1))
                continue
            return record
        except requests.RequestException as exc:  # pragma: no cover - network shape
            last = f'{type(exc).__name__}: {exc}'
            time.sleep(2 * (attempt + 1))
    return {'url': url, 'status': 0, 'bytes': 0, 'sha256': None, 'error': last, 'attempts': attempts}


def local_links(page_url: str, body: str) -> list[str]:
    """Every same-site link a page carries, normalised and de-duplicated."""
    base = urlsplit(page_url)
    found: list[str] = []
    seen: set[str] = set()
    for raw in LOCAL_LINK_RE.findall(body):
        raw = raw.strip()
        if not raw or raw.startswith(('#', 'mailto:', 'data:', 'javascript:')):
            continue
        absolute = urljoin(page_url, raw)
        parts = urlsplit(absolute)
        if parts.scheme not in {'http', 'https'} or parts.netloc != base.netloc:
            continue
        target = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
        if target in seen:
            continue
        seen.add(target)
        found.append(target)
    return found


def public(record: dict) -> dict:
    """A response record with the response body removed (bodies stay out of git)."""
    return {k: v for k, v in record.items() if not k.startswith('_')}


def fixture_id_of(row: dict) -> str:
    for key in ('source_url', 'source_api'):
        value = row.get(key)
        if isinstance(value, str):
            match = re.search(r'/fixtures?/(\d+)', value)
            if match:
                return match.group(1)
    for key in ('id', 'fixture_id', 'match_id'):
        value = row.get(key)
        if isinstance(value, (str, int)) and str(value).isdigit():
            return str(value)
    return ''


def has_pick(row: dict) -> bool:
    for key in ('probabilities', 'fair_probabilities', 'line'):
        value = row.get(key)
        if isinstance(value, list) and len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
            return True
    for team in row.get('teams') or []:
        if isinstance(team, dict) and isinstance(team.get('probability'), (int, float)):
            return True
    return bool(row.get('pick') or row.get('pick_name') or row.get('selection'))


def inventory(session: requests.Session) -> dict:
    """Live Hotspawn inventory: API records plus the fixture ids the lobby renders."""
    probe = importlib.import_module('scripts.0c034b94_probe')
    api = fetch(session, FIXTURE_API)
    lobby = fetch(session, LOBBY_URL + '?cb=' + str(int(time.time())))
    api_records: list = []
    if api['status'] == 200 and api.get('_body'):
        payload = json.loads(api['_body'])
        api_records = payload if isinstance(payload, list) else payload.get('data') or []
    lobby_ids = probe.parse_lobby_fixture_ids(lobby['_body'].decode('utf-8', 'ignore')) if lobby.get('_body') else []
    open_ids: list[str] = []
    for record in probe.open_fixtures(api_records, datetime.now(timezone.utc)):
        view = probe.fixture_view(record)
        if view.get('id') is not None:
            open_ids.append(str(view['id']))
    return {
        'api': public(api),
        'lobby': public(lobby),
        'api_records': len(api_records),
        'api_open_ids': sorted(set(open_ids)),
        'lobby_ids': sorted(set(lobby_ids)),
        'lobby_matches_api': sorted(set(lobby_ids)) == sorted(set(open_ids)) if open_ids else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/research/9e0e601d'))
    parser.add_argument('--site', default=SITE)
    parser.add_argument('--skip-inventory', action='store_true')
    args = parser.parse_args(argv)

    session = requests.Session()
    observed = now_iso()
    pages: dict[str, dict] = {}
    links: dict[str, dict] = {}

    for path in PAGES:
        url = urljoin(args.site, path)
        record = fetch(session, url)
        body = record['_body'].decode('utf-8', 'ignore') if record['status'] == 200 else ''
        record['local_links'] = len(local_links(url, body)) if body else 0
        pages[url] = public(record)
        for target in local_links(url, body):
            if target in links:
                links[target]['linked_from'].append(path or '/')
                continue
            entry = public(fetch(session, target))
            entry['linked_from'] = [path or '/']
            links[target] = entry

    broken = {url: r for url, r in links.items() if r['status'] != 200}
    docs = {}
    for name, url in (('snapshot', urljoin(args.site, 'snapshot.json')),
                      ('origination', urljoin(args.site, 'origination.json')),
                      ('picks_csv', urljoin(args.site, 'picks.csv'))):
        record = fetch(session, url)
        body = record.get('_body') or b''
        record = public(record)
        docs[name] = record
        if record['status'] == 200 and url.endswith('.json'):
            try:
                record['payload'] = json.loads(body)
            except ValueError:
                record['payload'] = None

    snapshot = docs['snapshot'].get('payload') or {}
    origination = docs['origination'].get('payload') or {}
    rows = origination.get('matches') or []
    published_ids = {fixture_id_of(row): row for row in rows if fixture_id_of(row)}
    published_unpicked = [fixture_id_of(row) for row in rows if not has_pick(row)]
    published_blank = [row for row in rows if not fixture_id_of(row)]

    inv = {'skipped': True} if args.skip_inventory else inventory(session)
    open_ids = inv.get('api_open_ids') or []
    missing = [fid for fid in open_ids if fid not in published_ids]
    stale = [fid for fid in published_ids if open_ids and fid not in open_ids]

    dossier = {
        'schema_version': 1,
        'session': 'arena-9e0e601d',
        'observed_at': observed,
        'site': args.site,
        'pages': pages,
        'links': {'checked': len(links), 'ok': len(links) - len(broken), 'broken': broken},
        'downloads': docs,
        'deployed_snapshot_generated_at': snapshot.get('generated_at'),
        'deployed_origination_generated_at': origination.get('generated_at'),
        'deployed_counts': origination.get('counts'),
        'published_rows': len(rows),
        'published_rows_without_pick': sorted(published_unpicked),
        'published_rows_without_fixture_id': len(published_blank),
        'inventory': inv,
        'coverage': {
            'hotspawn_open': len(open_ids),
            'published': len(rows),
            'open_without_published_row': missing,
            'published_but_not_open': stale,
            'complete': bool(open_ids) and not missing and not published_unpicked,
        },
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'surface.json').write_text(json.dumps(dossier, indent=1, sort_keys=True) + '\n')
    (args.out / 'surface.md').write_text(render_markdown(dossier))
    print(json.dumps({k: dossier[k] for k in ('observed_at', 'coverage')}, indent=1))
    print(f"links {dossier['links']['ok']} ok / {len(broken)} broken of {len(links)}")
    return 0


def render_markdown(dossier: dict) -> str:
    coverage = dossier['coverage']
    lines = [
        '# Deployed-surface audit — the bytes a reader is served',
        '',
        f"Observed **{dossier['observed_at']}** from a GitHub Actions runner against "
        f"<{dossier['site']}> (this sandbox cannot reach the host at all).",
        '',
        '## Coverage of the live Hotspawn inventory',
        '',
        f"- Hotspawn open CS2 fixtures (scheduled-fixtures API): **{coverage['hotspawn_open']}**",
        f"- Published rows on the deployed complete list: **{coverage['published']}**",
        f"- Open fixtures with **no** published row: **{len(coverage['open_without_published_row'])}**"
        + (': ' + ', '.join(coverage['open_without_published_row']) if coverage['open_without_published_row'] else ''),
        f"- Published rows whose fixture is no longer open (retired): "
        f"**{len(coverage['published_but_not_open'])}**"
        + (': ' + ', '.join(coverage['published_but_not_open']) if coverage['published_but_not_open'] else ''),
        f"- Published rows without a two-way pick: **{len(dossier['published_rows_without_pick'])}**",
        f"- Lobby fixture ids equal the API's open set: **{dossier['inventory'].get('lobby_matches_api')}**",
        '',
        '## Downloads the published pages link',
        '',
        f"Checked **{dossier['links']['checked']}** local links across {len(dossier['pages'])} pages: "
        f"**{dossier['links']['ok']}** answered 200, **{len(dossier['links']['broken'])}** did not.",
        '',
    ]
    if dossier['links']['broken']:
        lines += ['| Path | Status | Linked from |', '| --- | --- | --- |']
        for url, record in sorted(dossier['links']['broken'].items()):
            lines.append(f"| <{url}> | {record['status'] or record.get('error', 'error')} | "
                         f"{', '.join(record.get('linked_from') or [])} |")
        lines.append('')
    lines += ['## Pages', '', '| Page | Status | Bytes | SHA-256 |', '| --- | --- | --- | --- |']
    for url, record in dossier['pages'].items():
        lines.append(f"| <{url}> | {record['status']} | {record['bytes']} | `{(record.get('sha256') or '')[:16]}` |")
    lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    raise SystemExit(main())
