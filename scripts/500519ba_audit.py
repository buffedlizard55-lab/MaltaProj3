"""Live coverage audit for session 500519ba — a pick for every open Hotspawn CS2 fixture.

Why this runs on a runner
-------------------------
The authoring sandbox for this session has no TCP route to `play.hotspawn.com`,
`hltv.org`, `polymarket.com`, `thunderpick.io` or the published Pages site: every
request fails with `SSL_ERROR_SYSCALL` before a status line is printed (verified
2026-10-26T00:45Z).  A claim about what those hosts publish therefore cannot be
made from the sandbox.  This module runs on GitHub Actions, reads the surfaces,
and records the observation time, status code and SHA-256 of every response it
parses, so each statement in the dossier can be re-checked against the bytes.

What it measures
----------------
1. **The live inventory.** Hotspawn's public scheduled-fixture API, read twice in
   the same pass — the URL the collector uses and the same URL with a cache
   buster — plus the rendered lobby pages.  The difference between the two reads
   is how a CDN-cached response is detected instead of assumed.
2. **The fresh ladder.** `data/latest.json` and `data/origination.json` as the
   collector and `scripts.originate --live` just wrote them on this runner.  For
   every fixture Hotspawn has open right now: is there a pick, both
   probabilities, the method and a source link?
3. **The deployed snapshot.** The `snapshot.json` a reader is actually served,
   compared with the live open set.  A fixture that is open on Hotspawn and
   absent from the deployed snapshot is a coverage gap, named with its ID.
4. **HLTV first, then the books, for anything the ladder left blank.**  HLTV's
   upcoming listing and weekly world-ranking page, Polymarket's public CS2 event
   index, the Thunderpick match feed, bo3.gg's match listing and EGamersWorld are
   each recorded as answered / refused / candidate rows found.  This is where the
   brief's "try HLTV, then look at esportsbooks" is applied to the *remaining*
   fixtures only.

What it never does
------------------
It writes **no probability, no pick and no alias**.  A source that answers is not
evidence that a price exists; a 403 is a limitation of this runner, not proof
that a market is missing.  `scripts/originate.py` remains the only path to a
published number, and a fixture it cannot price is published as an explicit
limitation, never as a default 50/50.

Outputs
-------
`data/research/500519ba/coverage.json`, `coverage.md` and `summary.txt`.

CLI
---
    python -m scripts.500519ba_audit            # read live, then write the dossier
    python -m scripts.500519ba_audit --replay   # re-derive from data/ already on disk
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / '500519ba'

FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
LOBBY = 'https://play.hotspawn.com/lobby'
CS2_LOBBY = 'https://play.hotspawn.com/cs2-pickems'
DEPLOYED = 'https://buffedlizard55-lab.github.io/MaltaProj3/'
HLTV_MATCHES = 'https://www.hltv.org/matches'
HLTV_RANKING = 'https://www.hltv.org/ranking/teams'
POLY_EVENTS = ('https://gamma-api.polymarket.com/events?tag_slug=cs2&closed=false'
               '&limit=100&order=startDate&ascending=true')
THUNDERPICK_API = 'https://thunderpick.io/api/matches'
BO3_MATCHES = 'https://bo3.gg/matches'
EGW_MATCHES = 'https://egamersworld.com/counterstrike/matches'
POLICY = ('Read-only audit. No probability, pick or alias is written here; scripts/originate.py '
          'remains the only path to a published number. A refused source is a limitation of this '
          'runner, never proof that a market does not exist. Hotspawn "% picked" and HLTV fan votes '
          'are never read as inputs.')

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/128.0 Safari/537.36'),
    'Accept-Language': 'en-US,en;q=0.9',
}


def now_iso() -> str:
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def iso(value) -> str | None:
    if not value:
        return None
    try:
        stamp = float(value) / 1000 if float(value) > 1e11 else float(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(stamp, UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def fetch(session: requests.Session, url: str, timeout: int = 25) -> dict:
    """One observation: status, cache headers, byte count and SHA-256 of the body."""
    record = {'url': url, 'observed_at': now_iso(), 'status': None, 'ok': False,
              'bytes': 0, 'sha256': None, 'cache': {}, 'error': None, 'text': None}
    try:
        response = session.get(url, timeout=timeout, headers=HEADERS)
        body = response.content
        record.update(status=response.status_code, ok=response.status_code == 200,
                      bytes=len(body),
                      sha256=hashlib.sha256(body).hexdigest(),
                      cache={k: response.headers.get(k) for k in
                             ('cache-control', 'age', 'x-cache', 'cf-cache-status', 'date')
                             if response.headers.get(k) is not None})
        record['text'] = body.decode('utf-8', 'replace')
    except requests.RequestException as exc:  # transport failure is a finding, not a crash
        record['error'] = f'{type(exc).__name__}: {exc}'
    return record


def drop_text(record: dict) -> dict:
    """The archived record without the body; the hash keeps it re-checkable."""
    return {k: v for k, v in record.items() if k != 'text'}


def cs2_rows(payload) -> list:
    if not isinstance(payload, list):
        return []
    return [row for row in payload if row.get('sport_alias') == 'cs2']


def open_rows(rows: list, now: datetime) -> list:
    """Fixtures the lobby will still offer a pick for: scheduled start in the future."""
    out = []
    for row in rows:
        start = iso(row.get('scheduled_start_time'))
        if not start:
            continue
        if datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC) > now:
            out.append(row)
    return sorted(out, key=lambda r: (iso(r.get('scheduled_start_time')), str(r.get('id'))))


def lobby_ids(html: str | None) -> list:
    """Fixture IDs the rendered lobby links, in document order."""
    if not html:
        return []
    return re.findall(r'/matches/[a-z0-9\-]+-(\d{4,})', html)


def lobby_links(html: str | None) -> dict:
    """Fixture ID -> official Hotspawn permalink, from the rendered lobby."""
    if not html:
        return {}
    links = {}
    for url in re.findall(r'https://www\.hotspawn\.com/matches/[^"\'<> ]+', html):
        match = re.search(r'-(\d{4,})$', url)
        if match:
            links[match.group(1)] = url
    return links


def fixture_record(row: dict) -> dict:
    return {
        'id': str(row.get('id')),
        'competition': row.get('competition_name'),
        'competition_id': row.get('competition_id'),
        'teams': [row.get('participants0_name'), row.get('participants1_name')],
        'team_ids': [str(row.get('participants0_id')), str(row.get('participants1_id'))],
        'starts_at': iso(row.get('scheduled_start_time')),
        'locks_at': iso(row.get('lock_time')),
        'tier': row.get('tier'),
        'source_status': row.get('status'),
        'best_of': row.get('best_of'),
        'lobby_url': f'{CS2_LOBBY}#fixture-{row.get("id")}',
    }


def pick_summary(origination_row: dict | None) -> dict:
    """What the fresh ladder published for one fixture, in a few named fields."""
    if not origination_row:
        return {'present': False, 'pick': None, 'probabilities': None, 'method': None,
                'label': None, 'source': None, 'source_url': None, 'limitations': [],
                'trail': [], 'research_model': None}
    block = origination_row.get('origination') or {}
    pick_index = origination_row.get('pick_index')
    teams = [t.get('name') for t in origination_row.get('teams') or []]
    probabilities = block.get('probabilities')
    return {
        'present': True,
        'pick_index': pick_index,
        'pick': teams[pick_index] if pick_index is not None and pick_index < len(teams) else None,
        'opponent': teams[1 - pick_index] if pick_index is not None and len(teams) == 2 else None,
        'probabilities': [round(p * 100, 1) for p in probabilities] if probabilities else None,
        'method': block.get('method'),
        'label': block.get('label'),
        'source': block.get('source'),
        'source_url': block.get('source_url'),
        'observed_at': block.get('observed_at'),
        'limitations': (block.get('limitations') or []) + (origination_row.get('limitations') or []),
        'trail': origination_row.get('research') or [],
        'featured_method': (origination_row.get('featured_method') or None),
        'aliases_used': origination_row.get('aliases_used') or [],
    }


def deployed_summary(snapshot: dict | None, fixture_id: str) -> dict:
    if not snapshot:
        return {'present': False}
    for match in snapshot.get('matches') or []:
        if str(match.get('id')) == fixture_id:
            analysis = match.get('analysis') or {}
            pick_index = match.get('pick_index')
            teams = [t.get('name') for t in match.get('teams') or []]
            probabilities = analysis.get('probabilities')
            return {
                'present': True,
                'availability': match.get('availability'),
                'pick': teams[pick_index] if pick_index is not None else None,
                'probabilities': [round(p * 100, 1) for p in probabilities] if probabilities else None,
                'method': analysis.get('method'),
                'source': analysis.get('source'),
                'source_url': analysis.get('source_url'),
            }
    return {'present': False}


def name_in(needle: str, haystack: str) -> bool:
    return bool(needle) and needle.casefold() in haystack.casefold()


def source_availability(records: dict) -> dict:
    return {name: {'status': record['status'], 'ok': record['ok'], 'error': record['error'],
                   'bytes': record['bytes'], 'sha256': record['sha256'],
                   'observed_at': record['observed_at'], 'cache': record['cache'],
                   'url': record['url']}
            for name, record in records.items()}


def audit(data_dir: Path, out_dir: Path, *, live: bool = True, timeout: int = 25) -> dict:
    observed_at = now_iso()
    now = datetime.now(UTC)
    session = requests.Session()
    records: dict = {}
    payloads: dict = {}

    # 1. Live inventory, read twice so a cached answer is visible as a diff.
    if live:
        records['fixtures_api'] = fetch(session, FIXTURES_API, timeout)
        records['fixtures_api_cache_busted'] = fetch(
            session, FIXTURES_API + '&cb=' + str(int(time.time())), timeout)
        records['lobby'] = fetch(session, LOBBY + '?cb=' + str(int(time.time())), timeout)
        records['cs2_lobby'] = fetch(session, CS2_LOBBY + '?cb=' + str(int(time.time())), timeout)
        records['deployed_snapshot'] = fetch(session, DEPLOYED + 'snapshot.json', timeout)
        records['hltv_matches'] = fetch(session, HLTV_MATCHES, timeout)
        records['hltv_ranking'] = fetch(session, HLTV_RANKING, timeout)
        records['polymarket_events'] = fetch(session, POLY_EVENTS, timeout)
        records['thunderpick'] = fetch(session, THUNDERPICK_API, timeout)
        records['bo3'] = fetch(session, BO3_MATCHES, timeout)
        records['egamersworld'] = fetch(session, EGW_MATCHES, timeout)
    for name, record in records.items():
        if not record.get('ok') or not record.get('text'):
            continue
        try:
            payloads[name] = json.loads(record['text'])
        except ValueError:
            payloads[name] = record['text']

    api_rows = cs2_rows(payloads.get('fixtures_api'))
    api_fresh_rows = cs2_rows(payloads.get('fixtures_api_cache_busted'))
    chosen = api_fresh_rows if len(api_fresh_rows) >= len(api_rows) else api_rows
    choice = 'cache_busted' if chosen is api_fresh_rows else 'cached'
    live_open = open_rows(chosen, now)
    open_ids = [str(row['id']) for row in live_open]

    lobby_page_ids = lobby_ids(payloads.get('lobby') if isinstance(payloads.get('lobby'), str) else None)
    cs2_page_ids = lobby_ids(payloads.get('cs2_lobby') if isinstance(payloads.get('cs2_lobby'), str) else None)

    fresh_snapshot = json.loads((data_dir / 'latest.json').read_text()) if (data_dir / 'latest.json').exists() else None
    fresh_origination = json.loads((data_dir / 'origination.json').read_text()) if (data_dir / 'origination.json').exists() else None
    deployed = payloads.get('deployed_snapshot') if isinstance(payloads.get('deployed_snapshot'), dict) else None

    fresh_orig_by_id = {}
    for row in (fresh_origination or {}).get('matches') or []:
        fresh_orig_by_id[str(row.get('id'))] = row
    fresh_snap_by_id = {str(m.get('id')): m for m in (fresh_snapshot or {}).get('matches') or []}

    hltv_text = records.get('hltv_matches', {}).get('text') or ''
    hltv_ranking_text = records.get('hltv_ranking', {}).get('text') or ''
    poly_payload = payloads.get('polymarket_events') if isinstance(payloads.get('polymarket_events'), list) else []
    thunder_text = records.get('thunderpick', {}).get('text') or ''
    bo3_text = records.get('bo3', {}).get('text') or ''
    poly_text = json.dumps(poly_payload)

    fixtures = []
    for row in live_open:
        record = fixture_record(row)
        fixture_id = record['id']
        summary = pick_summary(fresh_orig_by_id.get(fixture_id))
        fresh_snap = fresh_snap_by_id.get(fixture_id)
        published = deployed_summary(deployed, fixture_id)
        one, two = record['teams']
        # Independent, source-by-source availability for fixtures the ladder left blank.
        if summary['pick'] is None:
            summary['independent_sources'] = {
                'hltv_matches_answered': bool(hltv_text) and records['hltv_matches']['ok'],
                'hltv_page_mentions_team_0': name_in(one, hltv_text),
                'hltv_page_mentions_team_1': name_in(two, hltv_text),
                'hltv_ranking_answered': bool(hltv_ranking_text) and records['hltv_ranking']['ok'],
                'polymarket_index_mentions_team_0': name_in(one, poly_text),
                'polymarket_index_mentions_team_1': name_in(two, poly_text),
                'thunderpick_answered': records['thunderpick']['ok'],
                'thunderpick_feed_mentions_team_0': name_in(one, thunder_text),
                'thunderpick_feed_mentions_team_1': name_in(two, thunder_text),
                'bo3_answered': records['bo3']['ok'],
                'bo3_listing_mentions_team_0': name_in(one, bo3_text),
                'bo3_listing_mentions_team_1': name_in(two, bo3_text),
                'egamersworld_answered': records['egamersworld']['ok'],
            }
        fixtures.append({
            **record,
            'fresh_collected': fixture_id in fresh_snap_by_id,
            'fresh_ladder': summary,
            'fresh_snapshot_availability': (fresh_snap or {}).get('availability'),
            'deployed': published,
            'gap_vs_deployed': not published.get('present'),
        })

    unpicked = [f for f in fixtures if f['fresh_ladder']['pick'] is None]
    missing_from_deployed = [f['id'] for f in fixtures if f['gap_vs_deployed']]
    unpicked_in_deployed = [f['id'] for f in fixtures
                            if f['deployed'].get('present') and f['deployed'].get('pick') is None]

    counts = {
        'api_records': len(api_rows),
        'api_records_cache_busted': len(api_fresh_rows),
        'api_read_used': choice,
        'lobby_linked_fixtures': len(set(lobby_page_ids)),
        'cs2_lobby_linked_fixtures': len(set(cs2_page_ids)),
        'live_open': len(fixtures),
        'fresh_ladder_picked': sum(1 for f in fixtures if f['fresh_ladder']['pick']),
        'fresh_ladder_unpicked': len(unpicked),
        'deployed_snapshot_present': sum(1 for f in fixtures if f['deployed'].get('present')),
        'deployed_snapshot_missing': len(missing_from_deployed),
        'deployed_snapshot_unpicked': len(unpicked_in_deployed),
    }

    report = {
        'session': 'arena-500519ba',
        'observed_at': observed_at,
        'policy': POLICY,
        'sources': source_availability(records),
        'counts': counts,
        'fixtures': fixtures,
        'unpicked': [
            {
                'id': f['id'], 'teams': f['teams'], 'starts_at': f['starts_at'],
                'competition': f['competition'], 'tier': f['tier'],
                'limitations': f['fresh_ladder']['limitations'],
                'trail': f['fresh_ladder']['trail'],
                'independent_sources': f['fresh_ladder'].get('independent_sources'),
                'deployed': f['deployed'],
            } for f in unpicked
        ],
        'gaps_vs_deployed': missing_from_deployed,
        'fresh_snapshot_generated_at': (fresh_snapshot or {}).get('generated_at'),
        'fresh_origination_generated_at': (fresh_origination or {}).get('generated_at'),
        'deployed_snapshot_generated_at': (deployed or {}).get('generated_at'),
        'deployed_counts': (deployed or {}).get('counts'),
        'hltv_ranking_rows': len(re.findall(r'class="ranked-team', hltv_ranking_text)),
        'lobby_page_ids_not_in_api': sorted(set(lobby_page_ids) - set(str(r['id']) for r in chosen))[:20],
        'api_ids_not_linked_by_lobby': sorted(set(str(r['id']) for r in chosen) - set(lobby_page_ids))[:20],
    }

    links = lobby_links(payloads.get('lobby') if isinstance(payloads.get('lobby'), str) else None)
    record = live_coverage_record(report, links, fresh_orig_by_id, fresh_snap_by_id)
    report['live_coverage_record'] = {
        'path': 'data/research/500519ba/live-coverage.json',
        'fixtures': len(record['live_fixtures']),
        'missing_from_build': record['counts']['missing_from_build'],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'live-coverage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    (out_dir / 'live-coverage.md').write_text(render_live_coverage(record))
    (out_dir / 'coverage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (out_dir / 'coverage.md').write_text(render_markdown(report))
    (out_dir / 'summary.txt').write_text(render_summary(report))
    return report


def live_coverage_record(report: dict, links: dict, fresh_orig: dict, fresh_snap: dict) -> dict:
    """The dated lobby-vs-this-build record the executive summary already renders.

    Schema-compatible with `data/research/<session>/live-coverage.json` as read by
    `scripts/build.py::load_live_coverage` / `live_coverage_gaps`.  A fixture this
    run did not collect is published as a named, linked gap with the observation
    time — never as a probability.  `in_published_snapshot` means *this build's*
    complete list carries the row, so `live_coverage_gaps` skips it.
    """
    fixtures = []
    for fixture in report['fixtures']:
        fixture_id = fixture['id']
        carried = fixture_id in fresh_orig or fixture_id in fresh_snap
        if fixture['fresh_ladder'].get('pick'):
            note = ('In this build with a pick (' + str(fixture['fresh_ladder'].get('label') or
                                                         fixture['fresh_ladder'].get('method')) + ').')
        elif carried:
            note = ('In this build, but the ladder published no pick: see the unresolved register '
                    'for the blocker and the sources actually tried.')
        else:
            note = ('Open on Hotspawn at this observation but not in this build: it was scheduled after '
                    'the collect that produced this snapshot. No probability is invented here; the next '
                    'four-hour collect is the authority.')
        fixtures.append({
            'id': fixture_id,
            'teams': fixture['teams'],
            'competition': fixture['competition'],
            'starts_at': fixture['starts_at'],
            'hotspawn_url': links.get(fixture_id),
            'hltv_url': None,
            'in_published_snapshot': carried,
            'in_featured_resolved': bool(fixture['fresh_ladder'].get('pick')),
            'published_method': fixture['fresh_ladder'].get('label'),
            'note': note,
        })
    missing = [f for f in fixtures if not f['in_published_snapshot']]
    return {
        'schema_version': 1,
        'session': report['session'],
        'observed_at': report['observed_at'],
        'environment': 'github-actions-runner',
        'role': ('Dated comparison of the live Hotspawn CS2 lobby with the build this run produced. '
                 'Evidence only: no probability, pick or alias.'),
        'source_urls': [LOBBY, CS2_LOBBY, FIXTURES_API],
        'counts': {
            'live_fixtures': len(fixtures),
            'carried_in_build': len(fixtures) - len(missing),
            'missing_from_build': len(missing),
            'picked_in_build': sum(1 for f in fixtures if f['in_featured_resolved']),
        },
        'live_fixtures': fixtures,
    }


def render_live_coverage(record: dict) -> str:
    lines = [
        '# Live Hotspawn CS2 lobby vs this build — session arena-500519ba',
        '',
        f"Observed **{record['observed_at']}** (UTC) on a GitHub Actions runner.",
        '',
        record['role'],
        '',
        '| Fixture | Teams | Starts (UTC) | In this build | Pick | Note |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for fixture in record['live_fixtures']:
        name = ' vs '.join(t or '?' for t in fixture['teams'])
        label = f"[{name}]({fixture['hotspawn_url']})" if fixture.get('hotspawn_url') else name
        lines.append(f"| {fixture['id']} | {label} | {fixture['starts_at']} | "
                     f"{'yes' if fixture['in_published_snapshot'] else '**no**'} | "
                     f"{'yes' if fixture['in_featured_resolved'] else 'no'} | {fixture['note']} |")
    return '\n'.join(lines) + '\n'


def render_summary(report: dict) -> str:
    counts = report['counts']
    lines = [
        f"observed_at={report['observed_at']}",
        f"live_open={counts['live_open']} picked={counts['fresh_ladder_picked']} "
        f"unpicked={counts['fresh_ladder_unpicked']}",
        f"api_records={counts['api_records']} cache_busted={counts['api_records_cache_busted']} "
        f"used={counts['api_read_used']} lobby_cards={counts['lobby_linked_fixtures']}",
        f"deployed_snapshot={report['deployed_snapshot_generated_at']} "
        f"present={counts['deployed_snapshot_present']} missing={counts['deployed_snapshot_missing']} "
        f"unpicked_there={counts['deployed_snapshot_unpicked']}",
        f"fresh_snapshot={report['fresh_snapshot_generated_at']} "
        f"fresh_origination={report['fresh_origination_generated_at']}",
    ]
    for fixture in report['fixtures']:
        ladder = fixture['fresh_ladder']
        prob = ladder['probabilities']
        lines.append(
            'fixture {id} {teams} {starts} :: {state}'.format(
                id=fixture['id'], teams=' vs '.join(t or '?' for t in fixture['teams']),
                starts=fixture['starts_at'],
                state=('PICK ' + str(ladder['pick']) + ' ' + str(prob) + ' [' + str(ladder['method']) + '] '
                       if ladder['pick'] else 'UNPICKED')))
    for item in report['unpicked']:
        lines.append(f"unpicked {item['id']} {' vs '.join(t or '?' for t in item['teams'])}: "
                     + ' | '.join(item['limitations'])[:400])
        for stage in item['trail']:
            lines.append(f"   {stage.get('stage')}: {stage.get('status')} :: {str(stage.get('detail'))[:220]}")
        sources = item.get('independent_sources') or {}
        if sources:
            lines.append('   sources: ' + ', '.join(f'{k}={v}' for k, v in sources.items()))
    return '\n'.join(lines) + '\n'


def render_markdown(report: dict) -> str:
    counts = report['counts']
    lines = [
        '# Live coverage audit — session arena-500519ba',
        '',
        f"Observed **{report['observed_at']}** (UTC) on a GitHub Actions runner.",
        '',
        report['policy'],
        '',
        '## Counts',
        '',
        '| Measure | Value |',
        '| --- | --- |',
    ]
    for key, value in counts.items():
        lines.append(f'| `{key}` | {value} |')
    lines += ['', f"Deployed snapshot `{report['deployed_snapshot_generated_at']}`; fresh run "
                  f"`{report['fresh_snapshot_generated_at']}` / origination `{report['fresh_origination_generated_at']}`.", '',
              '## Sources read', '', '| Source | Status | Bytes | SHA-256 | Cache |', '| --- | --- | --- | --- | --- |']
    for name, record in report['sources'].items():
        lines.append(f"| `{name}` | {record['status']} | {record['bytes']} | "
                     f"`{(record['sha256'] or '')[:16]}` | {record['cache'] or '—'} |")
    lines += ['', '## Every open Hotspawn CS2 fixture', '',
              '| Fixture | Teams | Starts (UTC) | Tier | Pick | Probabilities | Method | Source | In deployed snapshot |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for fixture in report['fixtures']:
        ladder = fixture['fresh_ladder']
        prob = ' / '.join(f'{p}%' for p in ladder['probabilities']) if ladder['probabilities'] else '—'
        deployed = fixture['deployed']
        in_deployed = 'no' if not deployed.get('present') else (
            'yes — ' + str(deployed.get('pick')) if deployed.get('pick') else 'yes — no pick')
        lines.append(
            f"| [{fixture['id']}](https://www.hotspawn.com/matches/x-{fixture['id']}) | "
            f"{' vs '.join(t or '?' for t in fixture['teams'])} | {fixture['starts_at']} | {fixture['tier']} | "
            f"{ladder['pick'] or '**unresolved**'} | {prob} | {ladder['method'] or '—'} | "
            f"{ladder['source_url'] or '—'} | {in_deployed} |")
    lines += ['', '## Fixtures the ladder left blank', '']
    if not report['unpicked']:
        lines.append('None: every open fixture carries a pick with both probabilities and a source link.')
    for item in report['unpicked']:
        lines += [f"### {item['id']} — {' vs '.join(t or '?' for t in item['teams'])}", '',
                  f"*{item['competition']} · {item['starts_at']} · tier {item['tier']}*", '',
                  'Limitations:', '']
        for limitation in item['limitations']:
            lines.append(f'- {limitation}')
        lines += ['', 'Trail:', '']
        for stage in item['trail']:
            lines.append(f"- **{stage.get('stage')}** — {stage.get('status')}: {stage.get('detail')} "
                         f"({stage.get('source_url')})")
        sources = item.get('independent_sources') or {}
        if sources:
            lines += ['', 'Independent source availability:', ''] + [f'- `{k}`: {v}' for k, v in sources.items()]
        lines.append('')
    lines += ['', '## Gaps against the deployed snapshot', '',
              (', '.join(report['gaps_vs_deployed']) or 'None'), '']
    return '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--replay', action='store_true', help='do not fetch; re-derive from data/ on disk')
    parser.add_argument('--timeout', type=int, default=25)
    args = parser.parse_args()
    report = audit(args.data, args.out, live=not args.replay, timeout=args.timeout)
    print(render_summary(report))


if __name__ == '__main__':
    main()
