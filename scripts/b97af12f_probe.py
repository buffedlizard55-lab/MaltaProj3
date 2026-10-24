"""Session arena-b97af12f — runner-side re-check of the dated reconciliation.

The arena workspace has already read the Hotspawn lobby, Hotspawn's own fixture
API, HLTV, Polymarket and EGamersWorld first-hand. This script is *not* a
second opinion from the blocked coding sandbox: it is intended to run on a
GitHub-hosted runner, re-fetch the same public sources, save status/hash/excerpt
evidence, and only then refresh the two records ``scripts.build`` knows how to
publish (``live-coverage.json`` and, when runner-verified,
``line-source-research.json``). It never writes a probability, pick or alias,
never edits the live snapshot, and never deploys.

Usage (on a runner):
  python -m scripts.b97af12f_probe --out data/research/b97af12f
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts.b97af12f_reconcile import (
    API_URL, CS2_LOBBY_URL, LOBBY_URL, OBSERVED_AT, POLYMARKET_BOARD,
    EGW_INDEX, PUBLISHED_DATA_URL, HLTV_EVENTS, RESEARCH, PUBLISHED,
    build_reconciliation, iso_ms, render_live_coverage_md,
)

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
PUBLISHED_ORIGINATION = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json'
CHALLENGE = ('just a moment', 'cf-chl', 'challenge-platform', 'attention required',
             'enable javascript and cookies', 'captcha', 'access denied')

# The five fixtures for which the dated dossier found no compliant two-sided
# price, plus the five rows the stale snapshot labels as model/researched rather
# than a money line. The runner re-reads them; it does not promote any quote.
NO_LINE_TARGETS = [
    '1081152', '1081153', '1081154', '1081156', '1081158',
    '1082996', '1079198', '1079200', '1082861', '1082793',
]

# First-hand URLs transcribed by the workspace session. The runner fetches the
# exact same pages, so a reviewer can compare the excerpts and hashes.
TARGET_URLS = {
    '1081152': [
        ('HLTV first', 'https://www.hltv.org/matches/2399502/havu-vs-azuolas-cct-2026-europe-series-12'),
        ('Polymarket board', POLYMARKET_BOARD),
        ('EGamersWorld', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/havu-vs-azuolas-Dm2JAvY3OO'),
    ],
    '1081153': [
        ('HLTV first', 'https://www.hltv.org/matches/2399503/6yubojlbl-vs-saint-sinners-cct-2026-europe-series-12'),
        ('Polymarket', 'https://polymarket.com/esports/cs2/cct-europe/cs2-6yuboj-ssins-2026-10-24'),
        ('EGamersWorld', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/6yubojlbl-vs-saint-sinners-cCSiulSZ3S'),
    ],
    '1081154': [
        ('HLTV first', 'https://www.hltv.org/matches/2399504/baks-vs-illyrians-cct-2026-europe-series-12'),
        ('Polymarket', 'https://polymarket.com/esports/cs2/cct-europe/cs2-baks-ill4-2026-10-24'),
        ('EGamersWorld', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/baks-esports-vs-illyrians-IG9Tsqw9TJ'),
    ],
    '1081156': [
        ('HLTV first', 'https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12'),
        ('Polymarket', 'https://polymarket.com/esports/cs2/cct-europe/cs2-tsa-skr2-2026-10-25'),
        ('EGamersWorld', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/spirit-academy-vs-zgh7PZE301'),
    ],
    '1081158': [
        ('HLTV first', 'https://www.hltv.org/matches/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12'),
        ('Polymarket', 'https://polymarket.com/esports/cs2/cct-europe/cs2-forzer-rustec-2026-10-25'),
        ('EGamersWorld', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/forze-reload-vs-ex-rustec-_GZF4CT4kR'),
    ],
    '1082996': [
        ('HLTV first', 'https://www.hltv.org/matches'),
        ('EGamersWorld', 'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/acend-vs-unity-esports-iwaKSVfgf'),
    ],
    '1079198': [
        ('HLTV first', 'https://www.hltv.org/matches'),
        ('EGamersWorld', 'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/metizport-vs-baks-esports-qOJcZA7Wgq'),
    ],
    '1079200': [
        ('HLTV first', 'https://www.hltv.org/matches'),
        ('EGamersWorld', EGW_INDEX),
    ],
    '1082861': [
        ('HLTV first', 'https://www.hltv.org/matches'),
        ('EGamersWorld', EGW_INDEX),
    ],
    '1082793': [
        ('HLTV first', 'https://www.hltv.org/matches'),
        ('EGamersWorld', EGW_INDEX),
    ],
}


def environment_name() -> str:
    return 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'local checkout'


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def excerpt(text: str, needle: str, before: int = 220, after: int = 420) -> str:
    low = text.casefold()
    pos = low.find(needle.casefold())
    if pos < 0:
        return ''
    start = max(0, pos - before)
    end = min(len(text), pos + after)
    return re.sub(r'\s+', ' ', text[start:end]).strip()


def fetch(session: requests.Session, url: str, *, timeout: int = 30) -> dict:
    observed = now_iso()
    try:
        response = session.get(url, headers={'User-Agent': UA}, timeout=timeout)
    except requests.RequestException as exc:
        return {'url': url, 'observed_at': observed, 'http_status': None,
                'error': f'{type(exc).__name__}: {exc}'[:300]}
    body = response.text or ''
    low = body[:5000].casefold()
    record = {
        'url': url, 'observed_at': observed,
        'http_status': response.status_code,
        'content_type': response.headers.get('content-type'),
        'bytes': len(body.encode('utf-8')),
        'sha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
        'cache': {k: response.headers.get(k) for k in ('age', 'x-cache', 'cf-cache-status')},
        'challenge_page': any(token in low for token in CHALLENGE),
    }
    for needle, label in (('make a bet', 'egw_bet_widget'),
                          ('moneyline', 'moneyline'),
                          ('$0.00 vol', 'zero_volume'),
                          ('pick a winner', 'fan_vote_excluded'),
                          ('best of 3', 'best_of_3')):
        got = excerpt(body, needle)
        if got:
            record[label] = got[:900]
    return record


def fetch_json(session: requests.Session, url: str, *, timeout: int = 30) -> tuple[dict, object]:
    observed = now_iso()
    base = {'url': url, 'observed_at': observed}
    try:
        response = session.get(url, headers={'User-Agent': UA}, timeout=timeout)
    except requests.RequestException as exc:
        return {**base, 'http_status': None,
                'error': f'{type(exc).__name__}: {exc}'[:300]}, None
    record = {**base, 'http_status': response.status_code,
              'content_type': response.headers.get('content-type'),
              'bytes': len(response.content),
              'sha256': hashlib.sha256(response.content).hexdigest(),
              'cache': {k: response.headers.get(k) for k in ('age', 'x-cache', 'cf-cache-status')}}
    try:
        return record, response.json()
    except ValueError:
        return {**record, 'error': 'response was not JSON'}, None


def hotspawn_url(teams, competition, fixture_id: str) -> str:
    def slug(text) -> str:
        return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', str(text or '').casefold())).strip('-')
    parts = [slug(teams[0]), 'vs', slug(teams[1]), slug(competition), str(fixture_id)]
    return 'https://www.hotspawn.com/matches/' + '-'.join(p for p in parts if p)


def parse_fixtures(payload) -> list[dict]:
    rows = []
    if not isinstance(payload, list):
        return rows
    for item in payload:
        try:
            start_ms = int(str(item.get('scheduled_start_time') or '').strip())
        except (TypeError, ValueError):
            continue
        rows.append({
            'id': str(item.get('id')),
            'teams': [item.get('participants0_name'), item.get('participants1_name')],
            'competition': item.get('competition_name'),
            'starts_at': iso_ms(start_ms),
            'locks_at': iso_ms(int(str(item.get('lock_time') or start_ms - 360_000))),
            'scheduled_start_time_ms': start_ms,
            'lock_offset_sec': item.get('lock_offset_sec'),
            'tier': item.get('tier'),
            'status': item.get('status'),
        })
    return rows


def lobby_ids(session: requests.Session) -> tuple[set[str], dict]:
    """IDs actually rendered as /matches/<slug>-<id> links in the lobby HTML."""
    record = fetch(session, LOBBY_URL + f'?cb={int(time.time())}')
    ids = set()
    if record.get('http_status') == 200:
        # fetch() stores only excerpts; re-read the body once for ID extraction.
        try:
            response = session.get(LOBBY_URL + f'?cb={int(time.time())}',
                                   headers={'User-Agent': UA}, timeout=30)
            if response.status_code == 200:
                ids = set(re.findall(r'/matches/[a-z0-9-]+-(\d{6,})', response.text or ''))
        except requests.RequestException:
            pass
    record['rendered_match_ids'] = sorted(ids)
    return ids, record


def published_ids(payload) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    return {str(m.get('id')) for m in payload.get('matches') or [] if m.get('id') is not None}


def build_live(rows: list[dict], rendered_ids: set[str], published: set[str],
               latest_meta: dict, observed: str) -> dict:
    opener = datetime.now(UTC)
    live = []
    for row in rows:
        start = datetime.fromisoformat(row['starts_at'].replace('Z', '+00:00'))
        if start <= opener:
            continue
        in_lobby = row['id'] in rendered_ids
        url = (hotspawn_url(row['teams'], row['competition'], row['id']) if in_lobby
               else f'{CS2_LOBBY_URL}#fixture-{row["id"]}')
        live.append({
            'id': row['id'],
            'teams': row['teams'],
            'competition': row['competition'],
            'starts_at': row['starts_at'],
            'hotspawn_url': url,
            'in_published_snapshot': row['id'] in published,
            'published_method': (PUBLISHED.get(row['id']) or [None])[0],
            'published_pick': ((PUBLISHED.get(row['id']) or [None, None])[1] +
                               ' (STALE reference, not a current pick)'
                               if PUBLISHED.get(row['id']) else None),
            'in_lobby_rendered': in_lobby,
            'note': ('In the stale published snapshot; its own page warns not to use it as a current pick.'
                     if row['id'] in published else
                     ('Missing from the stale published snapshot.'
                      if in_lobby else
                      'Future Hotspawn API row not rendered in the fetched lobby HTML; flagged for review.')),
        })
    live.sort(key=lambda r: (r['starts_at'], r['id']))
    missing = sum(not r['in_published_snapshot'] for r in live)
    return {
        'schema_version': 1,
        'session': 'arena-b97af12f',
        'observed_at': observed,
        'observer': environment_name(),
        'role': 'Dated inventory and identity research only. No value here is a probability or a pick.',
        'published_site': {'latest_json': PUBLISHED_DATA_URL, 'attempt': latest_meta},
        'hotspawn': {'lobby_url': LOBBY_URL, 'cs2_lobby_url': CS2_LOBBY_URL,
                     'api_url': API_URL, 'future_fixtures_compared': len(live),
                     'note': 'Only API rows starting after the observation instant are compared. The API lock_offset_sec is 360; the rules page says five minutes.'},
        'counts': {'live_future_fixtures': len(live),
                   'in_published_snapshot': len(live) - missing,
                   'missing_from_published': missing,
                   'api_only_rows': sum(not r['in_lobby_rendered'] for r in live)},
        'limitations': build_reconciliation()['limitations'],
        'live_fixtures': live,
    }


def build_research(attempts: list[dict], observed: str) -> dict:
    recon = build_reconciliation()
    by_id = {f['id']: f for f in recon['fixtures']}
    per_fixture = []
    for fid in NO_LINE_TARGETS:
        f = by_id.get(fid) or {}
        target_attempts = [a for a in attempts if a.get('url') in
                           {u for _, u in TARGET_URLS.get(fid, [])}]
        reachable = sum(a.get('http_status') == 200 for a in target_attempts)
        per_fixture.append({
            'id': fid,
            'teams': f.get('teams') or [None, None],
            'competition': f.get('competition'),
            'starts_at': f.get('starts_at'),
            'hotspawn_url': f.get('hotspawn_url'),
            'hltv_url': f.get('hltv_url'),
            'current_method': (PUBLISHED.get(fid) or [None])[0],
            'current_label': (PUBLISHED.get(fid) or [None, None])[1],
            # Never claim a bo3.gg/Thunderpick lead from an EGW or Polymarket
            # page. The rendered block's lead field is reserved for the
            # reviewed first-party ladder; here a lead stays false.
            'money_line_lead': False,
            'reachable_surfaces': reachable,
            'source_urls': [u for _, u in TARGET_URLS.get(fid, [])],
            'attempts': target_attempts,
            'verdict': ('No first-party two-sided replay was performed by this probe. '
                        'The dated dossier records any displayed quote; the reviewed '
                        'collector remains the only path to a published pick.'),
            'irregularity': f.get('irregularity'),
        })
    return {
        'schema_version': 1,
        'session': 'arena-b97af12f',
        'observed_at': observed,
        'environment': environment_name(),
        'policy': ('Read-only runner re-check in brief order: HLTV first for identity, then '
                   'Polymarket/EGamersWorld esportsbook and betting-line surfaces. Nothing here '
                   'writes a probability, pick or alias. Hotspawn % picked and HLTV fan votes are excluded.'),
        'source_scope': {
            'hotspawn_api': API_URL,
            'hltv_events': HLTV_EVENTS,
            'polymarket_board': POLYMARKET_BOARD,
            'egamersworld_index': EGW_INDEX,
            'workspace_dossier_observed_at': OBSERVED_AT,
        },
        'counts': {'fixtures_researched': len(per_fixture),
                   'dated_external_line_leads_recorded_in_dossier': 4,
                   'first_party_leads_promoted_here': 0},
        'sources_tried': attempts,
        'per_fixture': per_fixture,
    }


def render_research_md(record: dict) -> str:
    lines = [
        '# arena-b97af12f — runner re-check of HLTV-first no-line research',
        '',
        f'Observed **{record["observed_at"]}** in **{record["environment"]}**. '
        f'Re-read {len(record["sources_tried"])} URLs for '
        f'{record["counts"]["fixtures_researched"]} fixtures. '
        'This probe promotes **no** first-party lead; the dated workspace dossier keeps the '
        'displayed quotes and the reviewed collector remains the only path to a pick.',
        '',
        '## Surface attempts',
        '',
        '| URL | HTTP | Bytes | SHA-256 | Note |',
        '| --- | --- | --- | --- | --- |',
    ]
    for a in record['sources_tried']:
        note = 'challenge page' if a.get('challenge_page') else (a.get('error') or 'reachable')
        lines.append(f'| <{a["url"]}> | {a.get("http_status") or "no response"} | '
                     f'{a.get("bytes") or 0} | `{a.get("sha256") or "—"}` | {note} |')
    lines += ['', '## Per-fixture research', '']
    for f in record['per_fixture']:
        lines += [f'### {f["id"]} — {" vs ".join(t or "?" for t in f["teams"])}', '',
                  f'- Verdict: {f["verdict"]}',
                  f'- Reachable surfaces: {f["reachable_surfaces"]} of {len(f["source_urls"])}',
                  f'- Limitation: {f["irregularity"] or "See workspace dossier."}',
                  '']
        lines += [f'- <{u}>' for u in f['source_urls']]
        lines.append('')
    return '\n'.join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('data/research/b97af12f'))
    ap.add_argument('--delay', type=float, default=0.4, help='Seconds between page fetches')
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    observed = now_iso()
    session = requests.Session()
    attempts: list[dict] = []

    api_meta, api_payload = fetch_json(session, API_URL)
    latest_meta, latest_payload = fetch_json(session, PUBLISHED_DATA_URL + f'?cb={int(time.time())}')
    origination_meta, _ = fetch_json(session, PUBLISHED_ORIGINATION + f'?cb={int(time.time())}')
    rendered_ids, lobby_meta = lobby_ids(session)
    attempts.extend([api_meta, latest_meta, origination_meta, lobby_meta])
    rows = parse_fixtures(api_payload)
    published = published_ids(latest_payload)

    for url in [POLYMARKET_BOARD, EGW_INDEX, *HLTV_EVENTS]:
        attempts.append(fetch(session, url))
        time.sleep(args.delay)
    for fid, urls in TARGET_URLS.items():
        for _, url in urls:
            attempts.append(fetch(session, url))
            time.sleep(args.delay)

    evidence = {
        'session': 'arena-b97af12f', 'observed_at': observed,
        'environment': environment_name(),
        'attempts': attempts,
        'api_fixture_count': len(rows),
        'rendered_lobby_ids': sorted(rendered_ids),
        'published_latest_ids': sorted(published),
    }
    stamp = observed.replace(':', '').replace('-', '')
    (args.out / 'evidence').mkdir(exist_ok=True)
    (args.out / 'evidence' / f'fetch-{stamp}.json').write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    healthy_api = api_meta.get('http_status') == 200 and rows
    if healthy_api:
        live = build_live(rows, rendered_ids, published, latest_meta, observed)
        (args.out / 'live-coverage.json').write_text(
            json.dumps(live, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        (args.out / 'live-coverage.md').write_text(render_live_coverage_md(live), encoding='utf-8')
    else:
        (args.out / f'runner-failed-{stamp}.json').write_text(
            json.dumps({'observed_at': observed, 'reason': 'Hotspawn API unhealthy',
                        'api_meta': api_meta, 'attempts': attempts}, indent=2) + '\n',
            encoding='utf-8')
        print('::warning::Hotspawn API unhealthy; static dated live-coverage.json was left unchanged.')

    research_ok = any(a.get('http_status') == 200 for a in attempts)
    if research_ok:
        research = build_research(attempts, observed)
        (args.out / 'line-source-research.json').write_text(
            json.dumps(research, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        (args.out / 'line-source-research.md').write_text(render_research_md(research), encoding='utf-8')
    else:
        print('::warning::No research surface answered HTTP 200; static dated research was left unchanged.')

    summary = {'observed_at': observed, 'api_fixtures': len(rows),
               'rendered_lobby_ids': len(rendered_ids),
               'published_ids': len(published), 'attempts': len(attempts)}
    print('::notice title=b97af12f runner probe::' + json.dumps(summary))
    return 0 if healthy_api else 1


if __name__ == '__main__':
    raise SystemExit(main())
