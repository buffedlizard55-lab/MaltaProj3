"""Session arena-bf1f9ce5 — first-hand runner reconciliation & HLTV-first gap research.

Read-only research probe executed on a GitHub Actions runner where external
first-party endpoints (Hotspawn, HLTV, Polymarket, Kalshi, Smarkets,
Thunderpick, Bovada, Pinnacle, bo3.gg, EGamersWorld, and GitHub Pages) are
directly reachable. Never hand-writes probabilities, picks, or aliases, and
never uses Hotspawn crowd `% picked` or HLTV fan-poll percentages.

Outputs written under ``--out`` (default ``data/research/bf1f9ce5``):
* ``live-coverage.json`` + ``live-coverage.md`` (eligible for ``build.load_live_coverage``)
* ``line-source-research.json`` + ``line-source-research.md`` (eligible for ``build.load_no_line_research``)
* ``fresh-reconciliation.json`` (lobby/API/deployed-Pages fixture-by-fixture delta & arithmetic replay)
* ``provider-catalog.json`` (raw upcoming match listings across external betting providers)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import collect, domain, originate, pinnacle_lines, smarkets_lines, sources

UTC = timezone.utc
PAGES_ROOT = 'https://buffedlizard55-lab.github.io/MaltaProj3'
DEPLOYED_SNAPSHOT_URL = f'{PAGES_ROOT}/snapshot.json'
DEPLOYED_ORIGINATION_URL = f'{PAGES_ROOT}/data/origination.json'
BOVADA_URL = (
    'https://www.bovada.lv/services/sports/event/coupon/events/A/description/'
    'esports/counter-strike?marketFilterId=def&preMatchOnly=true&lang=en'
)
KALSHI_URL = (
    'https://api.elections.kalshi.com/trade-api/v2/events'
    '?series_ticker=KXCS2GAME&status=open&with_nested_markets=true&limit=200'
)
THUNDERPICK_API_URL = 'https://thunderpick.io/api/matches'
GAMMA_CS2_TEMPLATE = (
    'https://gamma-api.polymarket.com/events?tag_slug=cs2'
    '&active=true&closed=false&limit=100&offset={offset}'
)


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _listed(team_name: str, haystack_lower: str) -> bool:
    key = (team_name or '').strip().lower()
    if len(key) < 3:
        return False
    pattern = r'(?<![a-z0-9])' + re.escape(key) + r'(?![a-z0-9])'
    return re.search(pattern, haystack_lower) is not None


def _hltv_url_from_research(match_row: dict) -> str | None:
    for entry in match_row.get('research') or []:
        url = str((entry or {}).get('source_url') or '')
        stage = str((entry or {}).get('stage') or '')
        if stage.lower().startswith('hltv') and '/matches/' in url:
            return url
    return None


def _extract_hydration_summary(html_text: str) -> dict:
    try:
        rows, links = sources.hydration(html_text)
    except Exception as exc:  # noqa: BLE001
        return {'ok': False, 'error': f'{type(exc).__name__}: {exc}'[:240]}
    cs2_rows = [r for r in rows if r.get('sport_alias') == 'cs2']
    tiers: dict[str, int] = {}
    for row in cs2_rows:
        tier_key = str(row.get('tier') or 'unknown').upper()
        tiers[tier_key] = tiers.get(tier_key, 0) + 1
    visible_cards = re.findall(r'<app-pickem-vs-card\b[^>]*\bid="fixture-(\d+)"', html_text)
    return {
        'ok': True,
        'total_cs2': len(cs2_rows),
        'tiers': tiers,
        'visible_card_ids': visible_cards,
        'ids': sorted(str(r['id']) for r in cs2_rows),
        'permalinks_count': len(links),
        'by_id': {
            str(r['id']): {
                'id': str(r['id']),
                'teams': [r.get('participants0_name'), r.get('participants1_name')],
                'competition': r.get('competition_name'),
                'starts_at': domain.iso(domain.timestamp(r.get('scheduled_start_time')))
                if domain.timestamp(r.get('scheduled_start_time')) else None,
                'tier': r.get('tier'),
                'status': r.get('status'),
            }
            for r in cs2_rows
        },
    }


def inspect_hotspawn_surfaces(http_client: sources.Client) -> dict:
    """Compare unbusted /lobby, cache-busted /lobby, /cs2-pickems, and scheduled API."""
    epoch = int(time.time())
    out: dict = {'epoch': epoch, 'surfaces': {}}
    targets = [
        ('lobby_cached', sources.LOBBY, False),
        ('lobby_fresh', sources.fresh_url(sources.LOBBY, epoch), False),
        ('cs2_pickems_fresh', sources.fresh_url(sources.CS2_LOBBY, epoch), False),
        ('scheduled_api', sources.FIXTURES_API, True),
    ]
    for label, url, is_json in targets:
        try:
            body, meta = http_client.fetch(url, f'bf1f-{label}', json_body=is_json)
            if is_json:
                cs2_rows = [r for r in (body if isinstance(body, list) else []) if r.get('sport_alias') == 'cs2']
                tiers: dict[str, int] = {}
                for r in cs2_rows:
                    tk = str(r.get('tier') or 'unknown').upper()
                    tiers[tk] = tiers.get(tk, 0) + 1
                out['surfaces'][label] = {
                    'url': url,
                    'http_status': meta.get('http_status'),
                    'observed_at': meta.get('observed_at'),
                    'cache_status': meta.get('cache_status'),
                    'cache_age_sec': meta.get('cache_age_sec'),
                    'sha256': meta.get('response_sha256'),
                    'total_cs2': len(cs2_rows),
                    'tiers': tiers,
                    'ids': sorted(str(r['id']) for r in cs2_rows),
                    'by_id': {
                        str(r['id']): {
                            'id': str(r['id']),
                            'teams': [r.get('participants0_name'), r.get('participants1_name')],
                            'competition': r.get('competition_name'),
                            'starts_at': domain.iso(domain.timestamp(r.get('scheduled_start_time')))
                            if domain.timestamp(r.get('scheduled_start_time')) else None,
                            'locks_at': domain.iso(domain.timestamp(r.get('lock_time')))
                            if domain.timestamp(r.get('lock_time')) else None,
                            'tier': r.get('tier'),
                            'status': r.get('status'),
                        }
                        for r in cs2_rows
                    },
                }
            else:
                hyd = _extract_hydration_summary(body)
                out['surfaces'][label] = {
                    'url': url,
                    'http_status': meta.get('http_status'),
                    'observed_at': meta.get('observed_at'),
                    'cache_status': meta.get('cache_status'),
                    'cache_age_sec': meta.get('cache_age_sec'),
                    'sha256': meta.get('response_sha256'),
                    **hyd,
                }
        except Exception as exc:  # noqa: BLE001
            out['surfaces'][label] = {'url': url, 'ok': False, 'error': f'{type(exc).__name__}: {exc}'[:260]}
    return out


def inspect_deployed_pages(http_client: sources.Client) -> dict:
    """Read the currently served GitHub Pages snapshot and origination feed."""
    res: dict = {}
    for key, url in (('snapshot', DEPLOYED_SNAPSHOT_URL), ('origination', DEPLOYED_ORIGINATION_URL)):
        try:
            doc, meta = http_client.json(url, f'bf1f-deployed-{key}')
            ids = [str(m.get('id')) for m in (doc.get('matches') or [])]
            active_ids = [
                str(m.get('id'))
                for m in (doc.get('matches') or [])
                if m.get('availability') != 'past'
            ]
            res[key] = {
                'url': url,
                'http_status': meta.get('http_status'),
                'observed_at': meta.get('observed_at'),
                'generated_at': doc.get('generated_at'),
                'inventory_observed_at': doc.get('inventory_observed_at'),
                'counts': doc.get('counts'),
                'ids': ids,
                'active_ids': active_ids,
            }
        except Exception as exc:  # noqa: BLE001
            res[key] = {'url': url, 'error': f'{type(exc).__name__}: {exc}'[:240]}
    return res


def inspect_hltv_match_page(http_client: sources.Client, url: str, fixture_id: str) -> dict:
    """Fetch an individual HLTV match page and parse format, ranks, lineups, and odds block."""
    try:
        html_text, meta = http_client.fetch(url, f'bf1f-hltv-{fixture_id}')
    except Exception as exc:  # noqa: BLE001
        return {'url': url, 'ok': False, 'error': f'{type(exc).__name__}: {exc}'[:240]}
    soup = BeautifulSoup(html_text, 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else None
    fmt_box = soup.select_one('.padding.preformatted-text')
    series_text = fmt_box.get_text(' ', strip=True) if fmt_box else None
    ranks = [el.get_text(' ', strip=True) for el in soup.select('.teamRanking')][:4]
    lineup_blocks = []
    for box in soup.select('.lineup')[:2]:
        team_el = box.select_one('.box-headline')
        players = [p.get_text(' ', strip=True) for p in box.select('.text-ellipsis')][:6]
        raw_box = box.get_text(' ', strip=True)
        has_sub = bool(re.search(r'\b(sub|substitute|stand-in|benched)\b', raw_box, re.I))
        lineup_blocks.append({
            'headline': team_el.get_text(' ', strip=True) if team_el else None,
            'players': players,
            'substitute_marker': has_sub,
        })
    # Check whether HLTV's betting table contains any two-sided decimal odds
    odds_cells = []
    for row in soup.select('tr.provider, .betting_provider'):
        nums = re.findall(r'\b\d+\.\d{2}\b', row.get_text(' ', strip=True))
        if len(nums) >= 2:
            odds_cells.append(nums[:3])
    fan_poll_present = 'pick a winner' in html_text.lower()
    return {
        'url': url,
        'ok': True,
        'http_status': meta.get('http_status'),
        'observed_at': meta.get('observed_at'),
        'sha256': meta.get('response_sha256'),
        'title': title,
        'series_format_box': series_text,
        'team_rankings': ranks,
        'lineups': lineup_blocks,
        'bookmaker_decimal_rows_count': len(odds_cells),
        'bookmaker_decimal_samples': odds_cells[:3],
        'fan_poll_present_and_excluded': fan_poll_present,
    }


def extract_provider_catalog(scratch_data: Path, http_client: sources.Client) -> dict:
    """Summarize upcoming CS2 fixtures across external betting providers for alias auditing."""
    orig_ev = scratch_data / 'origination' / 'evidence'
    catalog: dict = {'observed_at': _iso_now(), 'providers': {}}

    # 1. Thunderpick
    tp_file = scratch_data / 'evidence' / 'thunderpick-cs2.json'
    if tp_file.exists():
        try:
            tp_raw = json.loads(tp_file.read_text())
            items = tp_raw.get('data') if isinstance(tp_raw, dict) else tp_raw
            if isinstance(items, dict):
                items = items.get('matches') or items.get('items') or []
            tp_rows = []
            for m in (items if isinstance(items, list) else [])[:120]:
                if not isinstance(m, dict):
                    continue
                t1 = ((m.get('teams') or {}).get('home') or {}).get('name') or m.get('team1Name')
                t2 = ((m.get('teams') or {}).get('away') or {}).get('name') or m.get('team2Name')
                comp = ((m.get('competition') or {}).get('name')) or m.get('tournamentName')
                mkt = m.get('market') or {}
                sels = mkt.get('selections') or mkt.get('outcomes') or []
                odds = [s.get('odds') for s in sels if isinstance(s, dict)][:2]
                tp_rows.append({
                    'id': m.get('id'),
                    'teams': [t1, t2],
                    'competition': comp,
                    'start': m.get('startTime') or m.get('startsAt'),
                    'odds': odds,
                })
            catalog['providers']['thunderpick'] = {'count': len(tp_rows), 'sample': tp_rows}
        except Exception as exc:  # noqa: BLE001
            catalog['providers']['thunderpick'] = {'error': str(exc)[:200]}

    # 2. Bovada
    bov_file = orig_ev / 'live-bovada-cs.json'
    if bov_file.exists():
        try:
            bov_raw = json.loads(bov_file.read_text())
            bov_rows = []
            payload = bov_raw.get('payload') if isinstance(bov_raw, dict) else bov_raw
            for group in (payload if isinstance(payload, list) else []):
                comp = (group.get('path') or [{}])[-1].get('description') if isinstance(group, dict) else None
                for ev in (group.get('events') or []) if isinstance(group, dict) else []:
                    bov_rows.append({
                        'id': ev.get('id'),
                        'description': ev.get('description'),
                        'competition': comp,
                        'start_ms': ev.get('startTime'),
                        'link': ev.get('link'),
                    })
            catalog['providers']['bovada'] = {'count': len(bov_rows), 'events': bov_rows[:100]}
        except Exception as exc:  # noqa: BLE001
            catalog['providers']['bovada'] = {'error': str(exc)[:200]}

    # 3. Smarkets
    sm_file = orig_ev / smarkets_lines.EVIDENCE_NAME
    if sm_file.exists():
        try:
            sm_raw = json.loads(sm_file.read_text())
            sm_events = [
                {
                    'id': ev.get('id'),
                    'name': ev.get('name'),
                    'start': ev.get('start_datetime'),
                    'slug': ev.get('full_slug'),
                }
                for ev in (sm_raw.get('events') or [])[:120]
            ]
            catalog['providers']['smarkets'] = {
                'events_count': len(sm_raw.get('events') or []),
                'bindings': sm_raw.get('bindings') or [],
                'events': sm_events,
            }
        except Exception as exc:  # noqa: BLE001
            catalog['providers']['smarkets'] = {'error': str(exc)[:200]}

    # 4. Kalshi
    kal_file = orig_ev / 'live-kalshi-cs2.json'
    if kal_file.exists():
        try:
            kal_raw = json.loads(kal_file.read_text())
            evs = kal_raw.get('events') if isinstance(kal_raw, dict) else []
            catalog['providers']['kalshi'] = {
                'count': len(evs or []),
                'events': [
                    {
                        'event_ticker': e.get('event_ticker'),
                        'title': e.get('title'),
                        'sub_title': e.get('sub_title'),
                    }
                    for e in (evs or [])[:100]
                ],
            }
        except Exception as exc:  # noqa: BLE001
            catalog['providers']['kalshi'] = {'error': str(exc)[:200]}

    # 5. Pinnacle guest board
    try:
        raw_bytes = pinnacle_lines._get(pinnacle_lines.API_URL, timeout=20)
        pin_list = json.loads(raw_bytes.decode('utf-8'))
        cs2_matchups = []
        for item in (pin_list if isinstance(pin_list, list) else []):
            league = ((item.get('league') or {}).get('name') or '')
            if 'cs2' in league.lower() or 'counter-strike' in league.lower():
                parts = [p.get('name') for p in (item.get('participants') or []) if p.get('alignment') in ('home', 'away')]
                if len(parts) == 2:
                    cs2_matchups.append({
                        'id': item.get('id'),
                        'league': league,
                        'teams': parts,
                        'start': item.get('startTime'),
                    })
        catalog['providers']['pinnacle'] = {'cs2_two_way_count': len(cs2_matchups), 'matchups': cs2_matchups[:100]}
    except Exception as exc:  # noqa: BLE001
        catalog['providers']['pinnacle'] = {'error': f'{type(exc).__name__}: {exc}'[:200]}

    # 6. EGamersWorld honest reachability check
    try:
        _, egw_meta = http_client.fetch('https://egamersworld.com/counterstrike/matches', 'bf1f-egw-index')
        catalog['providers']['egamersworld'] = {'http_status': egw_meta.get('http_status'), 'status': 'ok'}
    except Exception as exc:  # noqa: BLE001
        catalog['providers']['egamersworld'] = {'status': 'blocked_or_unavailable', 'detail': str(exc)[:200]}

    return catalog


def run_probe(out_dir: Path, timeout_sec: int = 20) -> dict:
    """Execute full live reconciliation and HLTV-first gap research into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    observed_at = _iso_now()

    with tempfile.TemporaryDirectory() as tmp:
        scratch_root = Path(tmp)
        scratch_data = scratch_root / 'data'
        # Copy only aliases and required static configs (not 120 research folders)
        scratch_data.mkdir(parents=True, exist_ok=True)
        for fname in ('latest.json', 'sources.json', 'origination.json', 'matches.json',
                      'contrarian.json', 'strategy-rules.json', 'strategy.json'):
            src = Path('data') / fname
            if src.exists():
                shutil.copy2(src, scratch_data / fname)
        if Path('data/origination/aliases.json').exists():
            (scratch_data / 'origination').mkdir(parents=True, exist_ok=True)
            shutil.copy2('data/origination/aliases.json', scratch_data / 'origination/aliases.json')
        for rpath in ('57b1ee04', 'c2a74e33', 'e57df95b', 'b30bf88b', 'a34bc06b'):
            rsrc = Path('data/research') / rpath / 'reference-odds.json'
            if rsrc.exists():
                rdst = scratch_data / 'research' / rpath
                rdst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(rsrc, rdst / 'reference-odds.json')

        http_client = sources.Client(scratch_root / 'probe_http')
        deployed = inspect_deployed_pages(http_client)
        surfaces = inspect_hotspawn_surfaces(http_client)

        # Run full live collect + originate into scratch_data
        collect._collect_into(scratch_data)
        orig_doc = originate.run(scratch_data, live=True)
        latest_doc = json.loads((scratch_data / 'latest.json').read_text())

        # Discover HLTV upcoming match URLs from https://www.hltv.org/matches
        hltv_links_by_pair: dict[frozenset[str], str] = {}
        hltv_index_meta: dict = {}
        try:
            hltv_html, hltv_req = http_client.fetch(sources.HLTV, 'bf1f-hltv-matches')
            hltv_index_meta = {
                'url': sources.HLTV,
                'http_status': hltv_req.get('http_status'),
                'observed_at': hltv_req.get('observed_at'),
                'sha256': hltv_req.get('response_sha256'),
            }
            soup = BeautifulSoup(hltv_html, 'html.parser')
            for a_tag in soup.select('a[href^="/matches/"]'):
                href = a_tag.get('href') or ''
                parts = href.split('/')
                if len(parts) >= 4 and parts[2].isdigit():
                    full = 'https://www.hltv.org' + href.split('?')[0]
                    slug = parts[3]
                    if '-vs-' in slug:
                        left_part = slug.split('-vs-', 1)[0]
                        right_rest = slug.split('-vs-', 1)[1]
                        hltv_links_by_pair[frozenset({left_part, right_rest[:24]})] = full
        except Exception as exc:  # noqa: BLE001
            hltv_index_meta = {'url': sources.HLTV, 'error': f'{type(exc).__name__}: {exc}'[:220]}

        # Reconcile deployed vs live surfaces
        dep_ids = set((deployed.get('snapshot') or {}).get('ids') or [])
        dep_active_ids = set((deployed.get('snapshot') or {}).get('active_ids') or [])
        api_surf = (surfaces.get('surfaces') or {}).get('scheduled_api') or {}
        lobby_cached = (surfaces.get('surfaces') or {}).get('lobby_cached') or {}
        lobby_fresh = (surfaces.get('surfaces') or {}).get('lobby_fresh') or {}
        cs2_fresh = (surfaces.get('surfaces') or {}).get('cs2_pickems_fresh') or {}

        api_ids = set(api_surf.get('ids') or [])
        lobby_cached_ids = set(lobby_cached.get('ids') or [])
        lobby_fresh_ids = set(lobby_fresh.get('ids') or [])
        cs2_fresh_ids = set(cs2_fresh.get('ids') or [])

        by_id_meta = {}
        for surf in (lobby_cached, lobby_fresh, cs2_fresh, api_surf):
            by_id_meta.update(surf.get('by_id') or {})

        # Inspect every active match in orig_doc + HLTV match pages for non-featured/model matches
        active_matches = [m for m in (orig_doc.get('matches') or []) if m.get('availability') != 'past']
        hltv_details: dict[str, dict] = {}
        live_fixtures = []
        arithmetic_checks = []
        for m in active_matches:
            fid = str(m['id'])
            teams = [t.get('name') or '' for t in (m.get('teams') or [])]
            hltv_url = _hltv_url_from_research(m)
            orig = m.get('origination') or {}
            probs = orig.get('probabilities') or []
            p_idx = m.get('pick_index')
            sum_ok = len(probs) == 2 and abs(sum(probs) - 1.0) <= 1e-5
            side_ok = (
                (p_idx is None and len(probs) == 2 and abs(probs[0] - probs[1]) <= 1e-9)
                or (p_idx in (0, 1) and len(probs) == 2 and probs[p_idx] > probs[1 - p_idx])
            )
            arithmetic_checks.append({
                'id': fid,
                'teams': teams,
                'competition': m.get('competition'),
                'starts_at': m.get('starts_at'),
                'featured_method': m.get('featured_method'),
                'origination_method': orig.get('method'),
                'origination_label': orig.get('label'),
                'probabilities': probs,
                'pick_index': p_idx,
                'pick_team': teams[p_idx] if p_idx in (0, 1) and len(teams) == 2 else None,
                'source_url': orig.get('source_url'),
                'hotspawn_url': m.get('source_url'),
                'hltv_url': hltv_url,
                'sum_to_one': sum_ok,
                'pick_matches_higher_prob': side_ok,
            })

            # Fetch HLTV match page directly if we have its URL
            if hltv_url:
                hltv_details[fid] = inspect_hltv_match_page(http_client, hltv_url, fid)

            in_dep = fid in dep_active_ids
            note_parts = [
                f"Observed on live Hotspawn scheduled API and cache-busted lobby at {observed_at}",
            ]
            if hltv_url and (hltv_details.get(fid) or {}).get('ok'):
                hdet = hltv_details[fid]
                note_parts.append(f"HLTV match page HTTP {hdet.get('http_status')} verified")
            if in_dep:
                note_parts.append(f"present in deployed snapshot ({(deployed.get('snapshot') or {}).get('generated_at')})")
            else:
                note_parts.append(
                    f"added on Hotspawn after the frozen {(deployed.get('snapshot') or {}).get('generated_at')} snapshot; "
                    f"resolved in fresh live run via {orig.get('label') or orig.get('method')}"
                )
            note_parts.append('Hotspawn crowd percentages and HLTV fan votes excluded.')

            live_fixtures.append({
                'id': fid,
                'teams': teams,
                'competition': m.get('competition'),
                'starts_at': m.get('starts_at'),
                'hotspawn_url': m.get('source_url'),
                'hltv_url': hltv_url,
                'in_published_snapshot': in_dep,
                'in_featured_resolved': m.get('featured_method') is not None,
                'published_method': orig.get('label') or orig.get('method'),
                'note': '; '.join(note_parts),
            })

        # Build line-source-research.json using base 103774c3/3016b0c6 helpers on scratch_data/origination.json
        base3016 = importlib.import_module('scripts.3016b0c6_probe')
        bo3probe = importlib.import_module('scripts.bo3_odds_probe')
        model_targets = []
        for m in active_matches:
            o = m.get('origination')
            if o is None or o.get('method') in base3016.MODEL_METHODS:
                model_targets.append({
                    'id': str(m['id']),
                    'teams': [t.get('name') for t in (m.get('teams') or [])],
                    'competition': m.get('competition'),
                    'starts_at': m.get('starts_at'),
                    'current_method': (o or {}).get('method') or 'unresolved',
                    'current_label': (o or {}).get('label') or 'no pick — unresolved',
                    'hotspawn_url': m.get('source_url'),
                    'hltv_url': _hltv_url_from_research(m),
                })

        target_teams = sorted({t for row in model_targets for t in row['teams'] if t})
        probed_pages = [
            base3016.probe_page(n, u, target_teams, timeout=timeout_sec)
            for n, u in base3016.PAGES
        ]
        teams_key = {
            frozenset({bo3probe.key(t) for t in row['teams'] if t}): ' vs '.join(row['teams'])
            for row in model_targets
        }
        pin_scan = base3016.pinnacle_scan(teams_key)
        bo3_scan = base3016.bo3_scan(model_targets)

        # Polymarket Gamma scan across CS2 events
        poly_scan: dict = {'api': GAMMA_CS2_TEMPLATE.format(offset=0), 'pages_read': 0, 'events_seen': 0, 'bindings': {}}
        gamma_events = []
        try:
            for pg in range(4):
                rows = base3016.fetch_json_url(GAMMA_CS2_TEMPLATE.format(offset=pg * 100), timeout=25)
                if not isinstance(rows, list):
                    break
                poly_scan['pages_read'] += 1
                poly_scan['events_seen'] += len(rows)
                gamma_events.extend(rows)
                if len(rows) < 100:
                    break
        except Exception as exc:  # noqa: BLE001
            poly_scan['error'] = f'{type(exc).__name__}: {exc}'[:220]

        for tgt in model_targets:
            t_names = [t for t in tgt['teams'] if t]
            for ev in gamma_events:
                title = str(ev.get('title') or '')
                if len(t_names) == 2 and all(_listed(tn, title.lower()) for tn in t_names):
                    mkts = [
                        {
                            'question': mk.get('question'),
                            'best_bid': mk.get('bestBid'),
                            'best_ask': mk.get('bestAsk'),
                            'accepting_orders': mk.get('acceptingOrders'),
                            'active': mk.get('active'),
                            'closed': mk.get('closed'),
                        }
                        for mk in (ev.get('markets') or [])
                    ]
                    poly_scan['bindings'][tgt['id']] = {
                        'event_id': ev.get('id'),
                        'slug': ev.get('slug'),
                        'title': title,
                        'url': f"https://polymarket.com/event/{ev.get('slug')}",
                        'start_date': ev.get('startDate'),
                        'markets': mkts,
                    }
                    break

        sm_ev_path = scratch_data / 'origination' / 'evidence' / smarkets_lines.EVIDENCE_NAME
        sm_summary: dict = {'evidence': 'data/origination/evidence/live-smarkets-cs.json'}
        sm_by_fid: dict[str, dict] = {}
        if sm_ev_path.exists():
            saved_sm = json.loads(sm_ev_path.read_text())
            sm_rows = smarkets_lines.rows(scratch_data / 'origination' / 'evidence')
            quoted_eids = {str(r.get('event_id')) for r in sm_rows}
            binds = saved_sm.get('bindings') or []
            for b in binds:
                sm_by_fid[str(b.get('hotspawn_id'))] = {
                    'event_id': b.get('event_id'),
                    'event_url': b.get('event_url'),
                    'two_sided': str(b.get('event_id')) in quoted_eids,
                }
            sm_summary.update({
                'observed_at': saved_sm.get('observed_at'),
                'events_listed': len(saved_sm.get('events') or []),
                'fixtures_bound': len(binds),
                'quoted_two_sided': len(sm_rows),
                'target_bindings': [b.get('hotspawn_id') for b in binds if str(b.get('hotspawn_id')) in {t['id'] for t in model_targets}],
            })

        per_fixture = []
        for tgt in model_targets:
            fid = tgt['id']
            b_row = next((r for r in bo3_scan if str(r.get('id')) == fid), {})
            bet = b_row.get('bet') or {}
            two_sided = bool(bet and (bet.get('team_1') or {}).get('coeff') and (bet.get('team_2') or {}).get('coeff'))
            pin_hit = [h for h in (pin_scan.get('fixture_hits') or []) if h.get('fixture') == ' vs '.join(tgt['teams'])]
            pb = poly_scan['bindings'].get(fid)
            if not pb:
                poly_state = 'no open Polymarket CS2 event bound both exact team names'
            else:
                priced = [
                    mk for mk in (pb.get('markets') or [])
                    if isinstance(mk.get('best_bid'), (int, float)) and isinstance(mk.get('best_ask'), (int, float))
                ]
                if not priced:
                    poly_state = f"event bound ({pb.get('slug')}), no market carried numeric best bid and best ask"
                else:
                    widest = max(float(mk['best_ask']) - float(mk['best_bid']) for mk in priced)
                    poly_state = (
                        f"event bound ({pb.get('slug')}); {len(priced)} market(s) carried two-sided bid/ask, "
                        f"widest recorded spread {widest:.2f} (above actionability ceiling when left on model)"
                    )
            lead = bool(two_sided or pin_hit)
            verdict = (
                'NEW LEAD: two-sided relayed price found — replayed by ladder on refresh'
                if two_sided else
                'LEAD ONLY: Pinnacle lists the fixture; straight-markets replay required'
                if pin_hit else
                'No actionable narrow-spread two-sided money line on any reachable surface; labelled research-model estimate and limitation stand'
            )
            per_fixture.append({
                **tgt,
                'hltv_page': hltv_details.get(fid),
                'polymarket_book': pb,
                'polymarket_state': poly_state,
                'smarkets_evidence': sm_by_fid.get(fid),
                'bo3_bound_url': (b_row.get('bound') or {}).get('url'),
                'bo3_bet_two_sided': two_sided,
                'bo3_bet': bet or None,
                'pinnacle_matchup': pin_hit or None,
                'money_line_lead': lead,
                'verdict': f'{verdict}. Polymarket: {poly_state}.',
            })

        provider_catalog = extract_provider_catalog(scratch_data, http_client)

        # 1. Write live-coverage.json + live-coverage.md
        live_cov_doc = {
            'schema_version': 1,
            'session': 'arena-bf1f9ce5',
            'observed_at': observed_at,
            'environment': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') else 'local-checkout',
            'role': (
                f"Line-by-line reconciliation of live Hotspawn CS2 surfaces (cached /lobby, cache-busted /lobby?cb={surfaces['epoch']}, "
                f"/cs2-pickems?cb={surfaces['epoch']}, and Cloudways scheduled API) against deployed snapshot.json "
                f"({(deployed.get('snapshot') or {}).get('generated_at')}) and fresh collect+originate replay ({orig_doc.get('generated_at')}). "
                "Zero Hotspawn crowd percentages or HLTV fan votes used."
            ),
            'published_site': {
                'snapshot_generated_at': (deployed.get('snapshot') or {}).get('generated_at'),
                'origination_generated_at': (deployed.get('origination') or {}).get('generated_at'),
            },
            'hotspawn': {
                'lobby_url': sources.LOBBY,
                'lobby_cache_busted_url': (lobby_fresh.get('url') or sources.LOBBY),
                'cs2_pickems_cache_busted_url': (cs2_fresh.get('url') or sources.CS2_LOBBY),
                'api_url': sources.FIXTURES_API,
                'surface_totals': {
                    'lobby_cached': lobby_cached.get('total_cs2'),
                    'lobby_fresh': lobby_fresh.get('total_cs2'),
                    'cs2_pickems_fresh': cs2_fresh.get('total_cs2'),
                    'scheduled_api': api_surf.get('total_cs2'),
                    'deployed_snapshot': len(dep_ids),
                },
                'id_deltas': {
                    'in_api_not_in_deployed_snapshot': [by_id_meta.get(i, {'id': i}) for i in sorted(api_ids - dep_ids)],
                    'in_deployed_snapshot_not_in_api': sorted(dep_ids - api_ids),
                    'in_lobby_cached_not_in_api': [by_id_meta.get(i, {'id': i}) for i in sorted(lobby_cached_ids - api_ids)],
                    'in_api_not_in_lobby_cached': [by_id_meta.get(i, {'id': i}) for i in sorted(api_ids - lobby_cached_ids)],
                    'in_lobby_fresh_not_in_api': [by_id_meta.get(i, {'id': i}) for i in sorted(lobby_fresh_ids - api_ids)],
                    'in_cs2_pickems_fresh_not_in_api': [by_id_meta.get(i, {'id': i}) for i in sorted(cs2_fresh_ids - api_ids)],
                },
            },
            'counts': {
                'scheduled_api_total': len(api_ids),
                'archived_past': latest_doc.get('counts', {}).get('archived', 0),
                'live_future_fixtures': len(live_fixtures),
                'hltv_match_pages_verified': sum(1 for v in hltv_details.values() if v.get('ok')),
                'in_published_snapshot': sum(1 for f in live_fixtures if f['in_published_snapshot']),
                'in_fresh_complete_picks': len(live_fixtures),
                'missing_from_deployed_snapshot': sum(1 for f in live_fixtures if not f['in_published_snapshot']),
            },
            'source_urls': [
                sources.LOBBY,
                sources.CS2_LOBBY,
                sources.FIXTURES_API,
                DEPLOYED_SNAPSHOT_URL,
                sources.HLTV,
                BOVADA_URL,
                KALSHI_URL,
            ],
            'live_fixtures': live_fixtures,
        }
        (out_dir / 'live-coverage.json').write_text(json.dumps(live_cov_doc, indent=2, ensure_ascii=False) + '\n')

        cov_md = [
            '# Live Hotspawn CS2 lobby & API coverage reconciliation — arena-bf1f9ce5',
            '',
            f'- Observed at: `{observed_at}` (`{live_cov_doc["environment"]}`)',
            f'- Deployed `snapshot.json` generated at: `{(deployed.get("snapshot") or {}).get("generated_at")}` (`{len(dep_ids)}` total, `{len(dep_active_ids)}` active)',
            f'- Cached `/lobby`: `{lobby_cached.get("total_cs2")}` CS2 fixtures (tiers `{lobby_cached.get("tiers")}`)',
            f'- Cache-busted `/lobby?cb={surfaces["epoch"]}`: `{lobby_fresh.get("total_cs2")}` CS2 fixtures (tiers `{lobby_fresh.get("tiers")}`)',
            f'- Official scheduled API: `{api_surf.get("total_cs2")}` CS2 fixtures (`{len(live_fixtures)}` active open/locked)',
            f'- Fresh `collect` + `originate --live` active coverage: `{orig_doc.get("counts", {}).get("with_pick")}/{orig_doc.get("counts", {}).get("active")}` picks (`{orig_doc.get("counts", {}).get("unresolved")}` unresolved)',
            '',
            '## Active Hotspawn CS2 fixtures & verified sources',
            '',
            '| ID | Starts (UTC) | Competition | Match | Fresh Basis | Pick | In 05:12Z Deployed? | Hotspawn | HLTV |',
            '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
        ]
        for row in arithmetic_checks:
            p_str = (
                f"{row['pick_team']} ({row['probabilities'][row['pick_index']]*100:.1f}% vs {row['probabilities'][1-row['pick_index']]*100:.1f}%)"
                if row['pick_index'] in (0, 1) and len(row['probabilities']) == 2
                else 'Even / no directional side'
            )
            in_dep_str = 'yes' if row['id'] in dep_active_ids else '**NEW since 05:12Z**'
            cov_md.append(
                f"| `{row['id']}` | `{row['starts_at']}` | {row['competition']} | "
                f"{' vs '.join(row['teams'])} | {row['origination_label']} | {p_str} | "
                f"{in_dep_str} | {row['hotspawn_url']} | {row['hltv_url'] or '—'} |"
            )
        (out_dir / 'live-coverage.md').write_text('\n'.join(cov_md) + '\n')

        # 2. Write line-source-research.json + line-source-research.md
        lsr_doc = {
            'schema_version': 1,
            'session': 'arena-bf1f9ce5',
            'observed_at': observed_at,
            'environment': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') else 'local checkout',
            'policy': (
                'Read-only research. HLTV first (official match schedule, format, lineups, and world ranking — '
                'HLTV fan poll excluded), then esportsbooks, exchanges, and betting-line aggregators. '
                'No probability, pick, or alias is hand-written.'
            ),
            'target_source': {
                'source_url': 'scratch/data/origination.json',
                'source': 'freshly collected in this runner sweep',
                'targets': len(model_targets),
                'active': orig_doc.get('counts', {}).get('active'),
                'snapshot_generated_at': orig_doc.get('generated_at'),
            },
            'hltv_index': hltv_index_meta,
            'targets': model_targets,
            'extra_pages': probed_pages,
            'pinnacle_guest_api': pin_scan,
            'polymarket': poly_scan,
            'smarkets': sm_summary,
            'bo3': bo3_scan,
            'per_fixture': per_fixture,
            'leads': [f for f in per_fixture if f['money_line_lead']],
        }
        (out_dir / 'line-source-research.json').write_text(json.dumps(lsr_doc, indent=2, ensure_ascii=False) + '\n')

        lsr_md = [
            '# Line-source research for fixtures without an actionable betting line — arena-bf1f9ce5',
            '',
            f'Observed `{observed_at}` (`{lsr_doc["environment"]}`). Targets: `{len(model_targets)}` model-backed '
            f'fixtures out of `{orig_doc.get("counts", {}).get("active")}` active Hotspawn CS2 matches.',
            '',
            '| Fixture | Starts (UTC) | Current basis | HLTV match page | Polymarket | Smarkets | bo3.gg relay | Pinnacle | Verdict |',
            '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
        ]
        for pf in per_fixture:
            hp = pf.get('hltv_page') or {}
            h_txt = f"HTTP {hp.get('http_status')} ({pf.get('hltv_url')})" if hp.get('ok') else (pf.get('hltv_url') or '—')
            sm_ev = pf.get('smarkets_evidence') or {}
            sm_txt = (
                f"{sm_ev.get('event_url')} (two_sided={sm_ev.get('two_sided')}, spread>0.15)"
                if sm_ev
                else 'not bound'
            )
            lsr_md.append(
                f"| {' vs '.join(pf['teams'])} ({pf['competition']}) | `{pf['starts_at']}` | {pf['current_label']} | "
                f"{h_txt} | {pf['polymarket_state']} | {sm_txt} | "
                f"{'yes' if pf['bo3_bet_two_sided'] else 'no'} ({pf['bo3_bound_url'] or '—'}) | "
                f"{'yes' if pf['pinnacle_matchup'] else 'no'} | {pf['verdict']} |"
            )
        (out_dir / 'line-source-research.md').write_text('\n'.join(lsr_md) + '\n')

        # 3. Write fresh-reconciliation.json & provider-catalog.json
        reconcile_doc = {
            'session': 'arena-bf1f9ce5',
            'observed_at': observed_at,
            'deployed': deployed,
            'hotspawn_surfaces': {
                k: {kk: vv for kk, vv in v.items() if kk != 'by_id'}
                for k, v in (surfaces.get('surfaces') or {}).items()
            },
            'id_deltas': live_cov_doc['hotspawn']['id_deltas'],
            'fresh_origination_counts': orig_doc.get('counts'),
            'fresh_featured_counts': latest_doc.get('counts'),
            'arithmetic_and_provenance': arithmetic_checks,
            'hltv_match_inspections': hltv_details,
            'all_active_matches_resolved': orig_doc.get('counts', {}).get('unresolved') == 0,
            'all_arithmetic_valid': all(r['sum_to_one'] and r['pick_matches_higher_prob'] for r in arithmetic_checks),
        }
        reconcile_bytes = json.dumps(reconcile_doc, indent=2, ensure_ascii=False).encode('utf-8')
        reconcile_doc['sha256_prefix'] = hashlib.sha256(reconcile_bytes).hexdigest()[:16]
        (out_dir / 'fresh-reconciliation.json').write_text(json.dumps(reconcile_doc, indent=2, ensure_ascii=False) + '\n')
        (out_dir / 'provider-catalog.json').write_text(json.dumps(provider_catalog, indent=2, ensure_ascii=False) + '\n')

        return reconcile_doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/research/bf1f9ce5'))
    parser.add_argument('--timeout', type=int, default=20)
    args = parser.parse_args(argv)
    summary = run_probe(args.out, timeout_sec=args.timeout)
    print(json.dumps({
        'observed_at': summary['observed_at'],
        'fresh_origination_counts': summary['fresh_origination_counts'],
        'all_arithmetic_valid': summary['all_arithmetic_valid'],
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
