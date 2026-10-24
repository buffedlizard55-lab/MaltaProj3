"""Read-only runner research sweep for 2026-10-24 active Hotspawn CS2 fixtures (session arena-dd433e7f).

After ``scripts.collect`` and ``scripts.originate --live`` run in the probe
workflow (without committing ``data/latest.json`` or ``data/origination.json``),
this script records:

1. ``line-source-research.{json,md}`` — HLTV-first, then Polymarket Gamma/CLOB,
   Smarkets exchange v3, bo3.gg (Thunderpick relay), Pinnacle guest API, Bovada,
   Kalshi and esportsbook surfaces for every active fixture whose current pick
   has no external betting line (or is unresolved). Compatible with
   ``scripts.build.load_no_line_research`` and ``scripts.eea4c104_audit``.
2. ``live-coverage.{json,md}`` — live Hotspawn CS2 inventory vs both the live
   published ``snapshot.json`` and the freshly originated ``data/origination.json``.
   Compatible with ``scripts.build.load_live_coverage``.
3. ``live-manifest.{json,md}`` — complete 2026-10-24 active Hotspawn CS2 fixture
   manifest (featured vs originated method, probabilities, pick, official source
   URLs, and research trail) from the fresh runner collection.
4. ``unmatched-scan.json`` — time-window scan (+/- 3600s) across Polymarket,
   Smarkets and bo3.gg for any external CS2 events near target fixtures that did
   not bind on exact or competition-scoped aliased names.

Policy: read-only evidence only. Never writes ``data/latest.json``,
``data/origination.json``, or the alias registry; never uses Hotspawn crowd
``% picked`` or HLTV fan votes as probabilities; never fabricates values.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import importlib
import json
import os
from pathlib import Path
import re
from typing import Any
import urllib.error
import urllib.request

from scripts import originate
from scripts.domain import name_key, timestamp

base = importlib.import_module('scripts.3016b0c6_probe')
bo3probe = importlib.import_module('scripts.bo3_odds_probe')
smarkets_mod = importlib.import_module('scripts.smarkets_lines')

UA = 'MaltaProj3-dd433e7f-research/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'


def _http_get_json(url: str, timeout: int = 20) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return int(getattr(resp, 'status', 200) or 200), json.loads(resp.read().decode('utf-8'))

LIVE_SNAPSHOT = 'https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json'
LIVE_ORIG = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json'
GAMMA_CS2 = 'https://gamma-api.polymarket.com/events'
CLOB_BOOK = 'https://clob.polymarket.com/book'
HOTSPAWN_API = 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1'
HOTSPAWN_LOBBY = 'https://play.hotspawn.com/lobby'

EXTRA_PAGES = [
    ('HLTV match listing', 'https://www.hltv.org/matches'),
    ('HLTV world ranking', 'https://www.hltv.org/ranking/teams'),
    ('Kalshi CS2 series markets',
     'https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXCS2GAME&status=open&limit=50'),
    ('Bovada CS2 coupon',
     'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2?marketFilterId=def&preMatchOnly=true&lang=en'),
    ('EGamersWorld CS2 predictions', 'https://egamersworld.com/counterstrike/predictions'),
    ('EGamersWorld CS2 matches', 'https://egamersworld.com/counterstrike/matches'),
]

# Official HLTV match pages verified via platform HLTV event match listings on 2026-10-24.
KNOWN_HLTV_URLS: dict[str, str] = {
    '1079658': 'https://www.hltv.org/matches/2399335/acend-vs-forze-reload-cct-2026-europe-series-11',
    '1079193': 'https://www.hltv.org/matches/2399108/fokus-vs-ex-6666-nodwin-clutch-series-13',
    '1081152': 'https://www.hltv.org/matches/2399502/havu-vs-azuolas-cct-2026-europe-series-12',
    '1079659': 'https://www.hltv.org/matches/2399336/spirit-academy-vs-lavked-cct-2026-europe-series-11',
    '1081153': 'https://www.hltv.org/matches/2399503/6yubojlbl-vs-saint-sinners-cct-2026-europe-series-12',
    '1079660': 'https://www.hltv.org/matches/2399337/inox-division-vs-brute-cct-2026-europe-series-11',
    '1079195': 'https://www.hltv.org/matches/2399110/nuclear-tigeres-vs-forze-reload-nodwin-clutch-series-13',
    '1081154': 'https://www.hltv.org/matches/2399504/baks-vs-illyrians-cct-2026-europe-series-12',
    '1079661': 'https://www.hltv.org/matches/2399338/nuclear-tigeres-vs-ex-zero-tenacity-cct-2026-europe-series-11',
    '1082996': 'https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13',
    '1081156': 'https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12',
    '1079198': 'https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13',
    '1079199': 'https://www.hltv.org/matches/2399114/infinite-vs-brute-nodwin-clutch-series-13',
    '1081158': 'https://www.hltv.org/matches/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12',
    '1079200': 'https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13',
    '1082858': 'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
    '1082859': 'https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026',
    '1082860': 'https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026',
    '1082861': 'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
    '1082897': 'https://www.hltv.org/matches/2399866/b8-vs-k27-rlg-tesla-cup-2026',
    '1082898': 'https://www.hltv.org/matches/2399867/alliance-vs-faze-rlg-tesla-cup-2026',
    '1082900': 'https://www.hltv.org/matches/2399869/luminosity-vs-hotu-rlg-tesla-cup-2026',
    '1082901': 'https://www.hltv.org/matches/2399870/envy-vs-gamerlegion-rlg-tesla-cup-2026',
    '1082792': 'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
    '1082793': 'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
}


def _slug_part(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')


def hotspawn_match_url(teams: list[str], competition: str, fid: str) -> str:
    parts = [_slug_part(teams[0] if teams else ''), 'vs',
             _slug_part(teams[1] if len(teams) > 1 else ''),
             _slug_part(competition), str(fid)]
    return 'https://www.hotspawn.com/matches/' + '-'.join(p for p in parts if p)


def _hltv_url_from_trail(match: dict[str, Any]) -> str | None:
    fid = str(match.get('id') or '')
    if fid in KNOWN_HLTV_URLS:
        return KNOWN_HLTV_URLS[fid]
    for step in match.get('research') or []:
        url = step.get('url') or ''
        if 'hltv.org/matches/' in url:
            return url
    return None


def load_active_origination() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    local_orig = Path('data/origination.json')
    local_latest = Path('data/latest.json')
    if local_orig.exists():
        doc = json.loads(local_orig.read_text(encoding='utf-8'))
        gen = timestamp(doc.get('generated_at'))
        if gen and (datetime.now(UTC) - gen).total_seconds() < 8 * 3600:
            latest_doc = json.loads(local_latest.read_text(encoding='utf-8')) if local_latest.exists() else {}
            return doc, latest_doc, {'source': 'data/origination.json (fresh live collection)',
                                     'snapshot_generated_at': doc.get('generated_at')}
    try:
        _, doc = _http_get_json(LIVE_ORIG, timeout=20)
        return doc, {}, {'source': LIVE_ORIG, 'snapshot_generated_at': doc.get('generated_at')}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        doc = json.loads(local_orig.read_text(encoding='utf-8'))
        latest_doc = json.loads(local_latest.read_text(encoding='utf-8')) if local_latest.exists() else {}
        return doc, latest_doc, {
            'source': 'data/origination.json (checked-in fallback)',
            'live_fetch_error': f'{type(exc).__name__}: {exc}'[:200],
            'snapshot_generated_at': doc.get('generated_at'),
        }


def extract_targets(orig_doc: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for m in orig_doc.get('matches') or []:
        if m.get('availability') not in {'open', 'locked', 'unknown_lock'}:
            continue
        o = m.get('origination') or {}
        if o.get('money_backed'):
            continue
        teams = [t.get('name') or '' for t in m.get('teams') or []]
        out.append({
            'id': str(m.get('id')),
            'teams': teams,
            'competition': m.get('competition'),
            'starts_at': m.get('starts_at'),
            'current_method': o.get('method'),
            'current_label': o.get('label') or 'Unresolved (blank)',
            'hotspawn_url': m.get('source_url'),
            'hltv_url': _hltv_url_from_trail(m),
        })
    return out


def _as_list(val: Any) -> list[Any]:
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except ValueError:
            return []
    return val if isinstance(val, list) else []


def _clob_top(token_id: str) -> dict[str, Any]:
    try:
        _, book = _http_get_json(f'{CLOB_BOOK}?token_id={token_id}', timeout=12)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {'error': f'{type(exc).__name__}: {exc}'[:120]}
    bids = [float(b['price']) for b in book.get('bids') or [] if 'price' in b]
    asks = [float(a['price']) for a in book.get('asks') or [] if 'price' in a]
    best_bid = max(bids) if bids else None
    best_ask = min(asks) if asks else None
    return {
        'best_bid': best_bid,
        'best_ask': best_ask,
        'spread': round(best_ask - best_bid, 4) if best_bid is not None and best_ask is not None else None,
        'bids_n': len(bids),
        'asks_n': len(asks),
    }


def polymarket_scan(targets: list[dict[str, Any]], registry: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    pages = 0
    terminal = False
    try:
        for offset in range(0, 1000, 100):
            url = (f'{GAMMA_CS2}?tag_slug=counter-strike-2&active=true&closed=false'
                   f'&limit=100&offset={offset}')
            _, page = _http_get_json(url, timeout=20)
            pages += 1
            if not isinstance(page, list):
                break
            events.extend(page)
            if len(page) < 100:
                terminal = True
                break
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {'error': f'{type(exc).__name__}: {exc}'[:200], 'events_seen': len(events),
                'pages_read': pages, 'terminal_page': terminal, 'bindings': {}}, events

    bindings: dict[str, Any] = {}
    for t in targets:
        comp = t.get('competition') or ''
        want_exact = {bo3probe.key(n) for n in t['teams'] if n}
        want_canon = {name_key(originate.resolve_name(n, registry, comp)[0]) for n in t['teams'] if n}
        if len(want_exact) != 2:
            continue
        for ev in events:
            for mkt in ev.get('markets') or []:
                if mkt.get('sportsMarketType') not in (None, 'moneyline'):
                    continue
                outcomes = _as_list(mkt.get('outcomes'))
                outcomes_exact = {bo3probe.key(str(o)) for o in outcomes}
                outcomes_canon = {name_key(originate.resolve_name(str(o), registry, comp)[0]) for o in outcomes}
                if outcomes_exact != want_exact and outcomes_canon != want_canon:
                    continue
                tokens = _as_list(mkt.get('clobTokenIds'))
                books = {str(o): _clob_top(str(tok)) for o, tok in zip(outcomes, tokens)}
                bindings[str(t['id'])] = {
                    'event_slug': ev.get('slug'),
                    'url': f"https://polymarket.com/event/{ev.get('slug')}",
                    'title': ev.get('title'),
                    'game_start_time': mkt.get('gameStartTime') or ev.get('startTime'),
                    'outcomes': outcomes,
                    'outcome_prices_gamma': _as_list(mkt.get('outcomePrices')),
                    'clob': books,
                    'matched_via_alias': outcomes_exact != want_exact,
                }
                break
    return {
        'source_url': f'{GAMMA_CS2}?tag_slug=counter-strike-2&active=true&closed=false',
        'events_seen': len(events),
        'pages_read': pages,
        'terminal_page': terminal,
        'bindings': bindings,
    }, events


def polymarket_state(binding: dict[str, Any] | None) -> str:
    if not binding:
        return 'not listed'
    clob = binding.get('clob') or {}
    spreads = [b.get('spread') for b in clob.values() if isinstance(b, dict)]
    if not spreads or any(s is None for s in spreads):
        return f"listed ({binding.get('event_slug')}), one-sided or empty CLOB"
    worst = max(spreads)
    parts = [f"{team} {b.get('best_bid')}/{b.get('best_ask')}" for team, b in clob.items()]
    verdict = 'eligible' if worst <= 0.15 else f'refused (spread {worst:.2f} > 0.15 cap)'
    return f"listed ({'; '.join(parts)}) — {verdict}"


def build_live_manifest(orig_doc: dict[str, Any], latest_doc: dict[str, Any], observed: str) -> tuple[dict[str, Any], str]:
    featured_by_id = {str(m.get('id')): m for m in (latest_doc.get('matches') or [])}
    active_rows = []
    for m in orig_doc.get('matches') or []:
        if m.get('availability') not in {'open', 'locked', 'unknown_lock'}:
            continue
        fid = str(m.get('id'))
        feat = (featured_by_id.get(fid) or {}).get('analysis') or m.get('featured_analysis') or {}
        orig = m.get('origination') or {}
        teams = [t.get('name') or '' for t in m.get('teams') or []]
        pick_idx = m.get('pick_index')
        probs = orig.get('probabilities')
        active_rows.append({
            'id': fid,
            'teams': teams,
            'competition': m.get('competition'),
            'starts_at': m.get('starts_at'),
            'locks_at': m.get('locks_at'),
            'availability': m.get('availability'),
            'hotspawn_url': m.get('source_url'),
            'hltv_url': _hltv_url_from_trail(m),
            'featured_method': feat.get('method') if isinstance(feat, dict) else None,
            'featured_source_url': feat.get('source_url') if isinstance(feat, dict) else None,
            'originated_method': orig.get('method'),
            'originated_label': orig.get('label'),
            'originated_source': orig.get('source'),
            'originated_source_url': orig.get('source_url'),
            'money_backed': bool(orig.get('money_backed')),
            'thin_liquidity': bool(orig.get('thin_liquidity')),
            'team_a_win_pct': round(probs[0] * 100, 2) if isinstance(probs, list) and len(probs) == 2 else None,
            'team_b_win_pct': round(probs[1] * 100, 2) if isinstance(probs, list) and len(probs) == 2 else None,
            'selected_team': teams[pick_idx] if isinstance(pick_idx, int) and 0 <= pick_idx < len(teams) else None,
            'research_steps_count': len(m.get('research') or []),
        })
    manifest = {
        'schema_version': 1,
        'session': 'arena-dd433e7f',
        'observed_at': observed,
        'origination_generated_at': orig_doc.get('generated_at'),
        'counts': orig_doc.get('counts') or {},
        'active_count': len(active_rows),
        'money_backed_count': sum(1 for r in active_rows if r['money_backed']),
        'model_only_count': sum(1 for r in active_rows if r['originated_method'] and not r['money_backed']),
        'unresolved_count': sum(1 for r in active_rows if not r['originated_method']),
        'active_fixtures': active_rows,
    }
    md = [
        f'# Live 2026-10-24 Hotspawn CS2 Origination Manifest — {observed}',
        '',
        f"Origination snapshot: `{orig_doc.get('generated_at')}` · Active fixtures: **{len(active_rows)}** "
        f"(**{manifest['money_backed_count']}** money-backed, **{manifest['model_only_count']}** research-model, "
        f"**{manifest['unresolved_count']}** unresolved).",
        '',
        '| ID | Fixture | Competition | Start (UTC) | Basis | Selected | Win % (A / B) | Source |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for r in active_rows:
        pair = ' vs '.join(r['teams'])
        pcts = (f"{r['team_a_win_pct']:.1f}% / {r['team_b_win_pct']:.1f}%"
                if r['team_a_win_pct'] is not None and r['team_b_win_pct'] is not None else 'blank')
        md.append(
            f"| `{r['id']}` | [{pair}]({r['hotspawn_url']}) | {r['competition']} | {r['starts_at']} | "
            f"{r['originated_label'] or 'Unresolved'} | **{r['selected_team'] or '—'}** | {pcts} | "
            f"{r['originated_source_url'] or '—'} |"
        )
    return manifest, '\n'.join(md) + '\n'


def build_live_coverage(orig_doc: dict[str, Any], observed: str, timeout: int) -> tuple[dict[str, Any], str]:
    now_dt = timestamp(observed) or datetime.now(UTC)
    live_snap_meta: dict[str, Any] = {'snapshot_url': LIVE_SNAPSHOT}
    live_published_ids: set[str] = set()
    try:
        status, snap = _http_get_json(LIVE_SNAPSHOT, timeout=timeout)
        live_snap_meta.update({'http_status': status, 'generated_at': snap.get('generated_at')})
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        live_snap_meta['error'] = f'{type(exc).__name__}: {exc}'[:160]

    try:
        status, live_orig = _http_get_json(LIVE_ORIG, timeout=timeout)
        live_published_ids = {str(m.get('id')) for m in live_orig.get('matches') or [] if m.get('id') is not None}
        live_snap_meta['live_origination_generated_at'] = live_orig.get('generated_at')
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        live_snap_meta['live_origination_error'] = f'{type(exc).__name__}: {exc}'[:160]

    fresh_by_id = {str(m.get('id')): m for m in orig_doc.get('matches') or [] if m.get('id') is not None}

    api_status = None
    api_rows: list[dict[str, Any]] = []
    try:
        api_status, payload = _http_get_json(HOTSPAWN_API, timeout=timeout)
        api_rows = payload if isinstance(payload, list) else (payload.get('data') or [])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        live_snap_meta['hotspawn_api_error'] = f'{type(exc).__name__}: {exc}'[:160]

    live_fixtures: list[dict[str, Any]] = []
    for row in api_rows:
        fid = str(row.get('id') or '')
        ms = row.get('scheduled_start_time')
        if not fid or not isinstance(ms, (int, float)):
            continue
        start_dt = datetime.fromtimestamp(ms / 1000.0, tz=UTC)
        if start_dt < now_dt:
            continue
        starts_iso = start_dt.isoformat(timespec='seconds').replace('+00:00', 'Z')
        teams_raw = row.get('teams') or []
        teams = [str(t.get('name') or '') for t in teams_raw[:2]]
        comp = str((row.get('competition') or {}).get('name') or row.get('competition_name') or '')
        fresh = fresh_by_id.get(fid) or {}
        orig = fresh.get('origination') or {}
        probs = orig.get('probabilities')
        pick_idx = fresh.get('pick_index')
        pick_summary = None
        if isinstance(probs, list) and len(probs) == 2 and isinstance(pick_idx, int) and 0 <= pick_idx < len(teams):
            pick_summary = f"{teams[pick_idx]} {probs[pick_idx] * 100:.1f}% ({orig.get('label') or orig.get('method')})"
        in_fresh = fid in fresh_by_id
        live_fixtures.append({
            'id': fid,
            'teams': teams,
            'competition': comp,
            'starts_at': starts_iso,
            'hotspawn_url': fresh.get('source_url') or hotspawn_match_url(teams, comp, fid),
            'hltv_url': _hltv_url_from_trail(fresh) or KNOWN_HLTV_URLS.get(fid),
            'in_published_snapshot': in_fresh,
            'in_prior_live_origination': fid in live_published_ids,
            'published_method': orig.get('label') or orig.get('method'),
            'published_pick': pick_summary,
            'note': ('Resolved in fresh 2026-10-24 collection.' if in_fresh else
                     'Not yet in snapshot; awaiting next scheduled collect+publish. No probability invented.'),
        })

    coverage = {
        'schema_version': 1,
        'session': 'arena-dd433e7f',
        'observed_at': observed,
        'observer': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') else 'local-checkout',
        'role': 'Dated inventory and identity reconciliation only. No value here is a hand-entered probability or pick.',
        'published_site': live_snap_meta,
        'hotspawn': {
            'lobby_url': HOTSPAWN_LOBBY,
            'api_url': HOTSPAWN_API,
            'api_http_status': api_status,
            'fixtures_returned': len(api_rows),
            'future_fixtures_compared': len(live_fixtures),
            'note': ('Past-start scheduled rows returned by the upstream API are excluded from future '
                     'open-fixture comparison. Hotspawn crowd pick percentages are never used as probabilities.'),
        },
        'counts': {
            'live_future_fixtures': len(live_fixtures),
            'in_published_snapshot': sum(1 for r in live_fixtures if r['in_published_snapshot']),
            'missing_from_published': sum(1 for r in live_fixtures if not r['in_published_snapshot']),
        },
        'limitations': [
            'HLTV match pages provide fixture identity, rankings, and recent map history; fan votes are crowd polls and never probabilities.',
            'Hotspawn crowd participation percentages are never used as win probabilities.',
            'Fixtures without an eligible two-sided external bookmaker/exchange line use labelled research models or remain blank.',
        ],
        'live_fixtures': live_fixtures,
    }
    md_lines = [
        f'# Live Hotspawn CS2 Lobby vs Originated Snapshot — {observed}',
        '',
        f"Future upcoming Hotspawn CS2 fixtures: **{len(live_fixtures)}** · "
        f"In fresh snapshot: **{coverage['counts']['in_published_snapshot']}** · "
        f"Missing: **{coverage['counts']['missing_from_published']}**.",
        '',
        '| ID | Fixture | Start (UTC) | HLTV | Fresh Snapshot Basis |',
        '| --- | --- | --- | --- | --- |',
    ]
    for r in live_fixtures:
        md_lines.append(
            f"| `{r['id']}` | [{' vs '.join(r['teams'])}]({r['hotspawn_url']}) | {r['starts_at']} | "
            f"{r.get('hltv_url') or '—'} | {r.get('published_pick') or '—'} |"
        )
    return coverage, '\n'.join(md_lines) + '\n'


def scan_unmatched_near_targets(
    targets: list[dict[str, Any]],
    poly_events: list[dict[str, Any]],
    smarkets_saved: dict[str, Any],
) -> dict[str, Any]:
    smarkets_events = smarkets_saved.get('events') or []
    near_by_target: dict[str, Any] = {}
    for t in targets:
        t_start = timestamp(t.get('starts_at'))
        if not t_start:
            continue
        poly_near = []
        for ev in poly_events:
            for mkt in ev.get('markets') or []:
                gs = timestamp(mkt.get('gameStartTime') or ev.get('startTime'))
                if gs and abs((gs - t_start).total_seconds()) <= 3600:
                    poly_near.append({
                        'slug': ev.get('slug'),
                        'title': ev.get('title'),
                        'game_start_time': mkt.get('gameStartTime') or ev.get('startTime'),
                        'outcomes': _as_list(mkt.get('outcomes')),
                    })
                    break
        smarkets_near = []
        for sev in smarkets_events:
            ss = timestamp(sev.get('start_datetime'))
            if ss and abs((ss - t_start).total_seconds()) <= 3600:
                smarkets_near.append({
                    'id': sev.get('id'),
                    'name': sev.get('name'),
                    'start_datetime': sev.get('start_datetime'),
                    'full_slug': sev.get('full_slug'),
                })
        near_by_target[str(t['id'])] = {
            'teams': t['teams'],
            'competition': t.get('competition'),
            'starts_at': t.get('starts_at'),
            'polymarket_within_1h': poly_near,
            'smarkets_within_1h': smarkets_near,
        }
    return near_by_target


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('data/research/dd433e7f'))
    ap.add_argument('--timeout', type=int, default=20)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    observed = datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')

    orig_doc, latest_doc, meta = load_active_origination()
    registry = originate.load_registry(Path('data/origination/aliases.json'))

    manifest, manifest_md = build_live_manifest(orig_doc, latest_doc, observed)
    (args.out / 'live-manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (args.out / 'live-manifest.md').write_text(manifest_md, encoding='utf-8')

    targets = extract_targets(orig_doc)
    teams = sorted({t for m in targets for t in m['teams'] if t})
    print(f"targets (no external betting line): {len(targets)} from {meta['source']}")

    pages = ([base.probe_page(n, u, teams, timeout=args.timeout) for n, u in base.PAGES]
             + [base.probe_page(n, u, teams, timeout=args.timeout) for n, u in EXTRA_PAGES])
    teams_key = {frozenset({bo3probe.key(t) for t in m['teams'] if t}): ' vs '.join(m['teams'])
                 for m in targets}
    pinnacle = base.pinnacle_scan(teams_key)
    bo3 = base.bo3_scan(targets)
    polymarket, poly_events = polymarket_scan(targets, registry)

    smarkets = {'evidence': 'data/origination/evidence/live-smarkets-cs.json'}
    smarkets_saved: dict[str, Any] = {}
    smarkets_path = Path('data/origination/evidence/live-smarkets-cs.json')
    if smarkets_path.exists():
        try:
            smarkets_saved = json.loads(smarkets_path.read_text(encoding='utf-8'))
            binds = smarkets_saved.get('bindings') or []
            s_rows = smarkets_mod.rows(Path('data/origination/evidence'))
            smarkets.update({
                'observed_at': smarkets_saved.get('observed_at'),
                'events_listed': len(smarkets_saved.get('events') or []),
                'fixtures_bound': len(binds),
                'quoted_two_sided': len(s_rows),
                'bound_fixtures': [{'hotspawn_id': b.get('hotspawn_id'), 'event_id': b.get('event_id'),
                                    'event_name': b.get('event_name'), 'event_url': b.get('event_url'),
                                    'aliases_used': b.get('aliases_used') or []}
                                   for b in binds],
                'target_bindings': [b.get('hotspawn_id') for b in binds
                                    if str(b.get('hotspawn_id')) in {str(t['id']) for t in targets}],
                'errors': smarkets_saved.get('errors') or [],
            })
        except (ValueError, TypeError) as exc:
            smarkets['error'] = f'{type(exc).__name__}: {exc}'[:200]
    else:
        smarkets['status'] = 'no Smarkets evidence file present'

    smarkets_by_fid = {str(b.get('hotspawn_id')): b for b in (smarkets_saved.get('bindings') or [])}
    smarkets_quotes = smarkets_saved.get('quotes') or {}

    per_fixture = []
    for m in targets:
        b = next((r for r in bo3 if r['id'] == m['id']), {})
        bet = b.get('bet') or {}
        two_sided = bool(bet and (bet.get('team_1') or {}).get('coeff')
                         and (bet.get('team_2') or {}).get('coeff'))
        pin_hit = [h for h in pinnacle.get('fixture_hits') or []
                   if h['fixture'] == ' vs '.join(m['teams'])]
        hltv_page = (base.probe_page('HLTV match page', m['hltv_url'], m['teams'],
                                     timeout=args.timeout)
                     if m.get('hltv_url') else None)
        listing_pages = [p['name'] for p in pages if any(
            t in (p.get('teams_found') or []) for t in m['teams'] if t)]
        lead = bool(two_sided or pin_hit)
        poly = polymarket_state(polymarket['bindings'].get(str(m['id'])))
        sb = smarkets_by_fid.get(str(m['id']))
        sb_quotes = None
        if sb:
            mid = str(sb.get('market_id') or '')
            sb_quotes = {
                'event_id': sb.get('event_id'),
                'event_name': sb.get('event_name'),
                'event_url': sb.get('event_url'),
                'market_id': mid,
                'aliases_used': sb.get('aliases_used') or [],
                'quotes_verbatim': smarkets_quotes.get(mid),
            }
        verdict = ('NEW LEAD: two-sided relayed price found — the reviewed ladder must replay it '
                   'before any pick changes' if two_sided else
                   'LEAD ONLY: Pinnacle lists the fixture; series moneyline still needs a '
                   'straight-markets replay' if pin_hit else
                   'No eligible two-sided price within spread ceiling on any probed surface; '
                   'the published research estimate and its limitation stand')
        per_fixture.append({
            **m,
            'hltv_page': hltv_page,
            'polymarket_book': polymarket['bindings'].get(str(m['id'])),
            'polymarket_state': poly,
            'smarkets_bound': sb_quotes,
            'bo3_bound_url': (b.get('bound') or {}).get('url'),
            'bo3_bet_two_sided': two_sided,
            'bo3_bet': bet or None,
            'pinnacle_matchup': pin_hit or None,
            'extra_pages_listing_a_team': listing_pages,
            'money_line_lead': lead,
            'verdict': f'{verdict}. Polymarket: {poly}.',
        })

    doc = {
        'schema_version': 1,
        'session': 'arena-dd433e7f',
        'observed_at': observed,
        'environment': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') else 'local checkout',
        'policy': ('Read-only research. HLTV first (fixture identity, rosters, and published rankings — '
                   'HLTV fan votes are crowd polls and never probabilities), then esportsbooks, exchanges '
                   'and betting-line aggregators. Nothing here is a hand-entered probability or pick; '
                   'only a bound fixture with both sides priced inside spread rules enters the ladder.'),
        'target_source': meta,
        'targets': targets,
        'extra_pages': pages,
        'pinnacle_guest_api': pinnacle,
        'polymarket': polymarket,
        'smarkets': smarkets,
        'bo3': bo3,
        'per_fixture': per_fixture,
        'leads': [f for f in per_fixture if f['money_line_lead']],
    }
    (args.out / 'line-source-research.json').write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    lines = [
        '# Line-source research for fixtures without an external betting line — arena-dd433e7f',
        '',
        f'Observed `{observed}` (`{doc["environment"]}`). Targets: **{len(targets)}** active fixtures '
        f'without an external betting line in snapshot `{meta.get("snapshot_generated_at")}` ({meta["source"]}).',
        '',
        'HLTV first, then esportsbooks, exchanges, and betting-line aggregators. A reachable page is never treated as a price.',
        '',
        '| Fixture | Current basis | HLTV page | Polymarket | Smarkets | bo3.gg bound | Two-sided relay price | Pinnacle | Verdict |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for f in per_fixture:
        hp = f.get('hltv_page') or {}
        hltv_cell = (f"{hp.get('status') or hp.get('error', '—')} ({f['hltv_url']})"
                     if f.get('hltv_url') else 'no HLTV URL')
        sb = f.get('smarkets_bound')
        sm_cell = f"bound ({sb['event_url']})" if sb else 'not listed'
        lines.append(
            f"| {' vs '.join(f['teams'])} ({f['competition']}) | {f['current_label']} | "
            f"{hltv_cell} | {f['polymarket_state']} | {sm_cell} | {f['bo3_bound_url'] or '—'} | "
            f"{'yes' if f['bo3_bet_two_sided'] else 'no'} | "
            f"{'yes' if f['pinnacle_matchup'] else 'no'} | {f['verdict']} |"
        )
    lines += [
        '',
        '## Surfaces probed (HLTV first)',
        '',
        '| Source | HTTP | Teams found | Challenge |',
        '| --- | --- | --- | --- |',
    ]
    for p in pages:
        lines.append(
            f"| {p['name']} ({p['url']}) | {p.get('status') or p.get('error', '—')} | "
            f"{', '.join(p.get('teams_found') or []) or '—'} | "
            f"{', '.join(p.get('challenge_markers') or []) or '—'} |"
        )
    lines += [
        '',
        f"**New money-line leads: {len(doc['leads'])}** of {len(targets)} target fixtures.",
    ]
    (args.out / 'line-source-research.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    coverage, coverage_md = build_live_coverage(orig_doc, observed, timeout=args.timeout)
    (args.out / 'live-coverage.json').write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (args.out / 'live-coverage.md').write_text(coverage_md, encoding='utf-8')

    unmatched = scan_unmatched_near_targets(targets, poly_events, smarkets_saved)
    (args.out / 'unmatched-scan.json').write_text(
        json.dumps({'observed_at': observed, 'targets_scanned': len(targets), 'by_target': unmatched},
                   indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8',
    )
    print(f"done: active={manifest['active_count']}, targets={len(targets)}, leads={len(doc['leads'])}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
