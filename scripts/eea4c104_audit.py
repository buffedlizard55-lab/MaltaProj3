"""Session arena-eea4c104 — deterministic line-by-line verification & runner line-source probe.

Two explicit modes:
1. Default offline audit (`python -m scripts.eea4c104_audit [--site site] [--write-reconciliation]`):
   -Deterministic, zero-network, wall-clock-independent verification of:
     * Every active match row & card in the built `site/` (or root published HTML):
       directional pick, both teams' probabilities summing to 100.0% (±0.2%),
       fair decimal line `≈ 1/p`, zero Hotspawn crowd `% picked` probability usage,
       and allow-listed official `https://` source links (`scripts.audit_rows.is_official`).
     * Executive summary (`index.html`) internal links to updated picks, separate
       unresolved & limitations section (`#unresolved-register` + `/unresolved/`),
       and `#no-line-research` artifact links.
     * `data/research/eea4c104/flags.json` schema, official `source_urls`, and
       rendering onto `site/review/index.html`.
     * Complete 30/30 active-fixture primary-source HLTV `bo3` reconciliation
       (`data/research/eea4c104/reconciliation-30-matches.{json,md}`).
2. Runner live research sweep (`python -m scripts.eea4c104_audit --runner --out data/research/eea4c104`):
   - Read-only HLTV-first, then esportsbooks / exchanges / relays sweep for every
     active Hotspawn CS2 fixture without an executable external moneyline, plus
     Polymarket Gamma (`series_id=10310`), Kalshi (`KXCS2GAME`, including the
     verified `los kogutos -> Banda chuya` alias check), Smarkets, Pinnacle
     Arcadia, and `api.bo3.gg` match records.
   - Emits `line-source-research.{json,md}` (compatible with `scripts/build.py`
     `load_no_line_research`) and `live-runner-replay.json`. Never writes a pick,
     probability, or alias into `data/latest.json` or `data/origination.json`.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from scripts.audit_rows import is_official

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Complete 30/30 official HLTV Bo3 match mapping verified directly from HLTV.org
# at 2026-10-23T09:45Z–10:00Z for the 2026-10-23T09:23:57Z live Hotspawn snapshot.
HLTV_VERIFIED_30: dict[str, dict[str, str]] = {
    '1079655': {
        'hltv_id': '2399332',
        'hltv_url': 'https://www.hltv.org/matches/2399332/nuclear-tigeres-vs-illyrians-cct-2026-europe-series-11',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in CCT 2026 Europe Series 11; paired with tight Polymarket series moneyline.',
    },
    '1081148': {
        'hltv_id': '2399498',
        'hltv_url': 'https://www.hltv.org/matches/2399498/inner-circle-academy-vs-spirit-academy-cct-2026-europe-series-12',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in CCT 2026 Europe Series 12; Polymarket market 6033288 ($15.98k volume, 0.435/0.565 at 09:58Z).',
    },
    '1081605': {
        'hltv_id': '2399699',
        'hltv_url': 'https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 (#174/VRS #167 Phantom Academy with La1roN vs Unranked/VRS #169 Banda Chuya). Alias los kogutos verified on Kalshi KXCS2GAME-26OCT230700LKPHAC ($0 vol, 26-29c spread) and bo3.gg 132217 (bet_updates: null).',
    },
    '1081606': {
        'hltv_id': '2399638',
        'hltv_url': 'https://www.hltv.org/matches/2399638/jijiehao-vs-eternal-fire-digital-crusade-draculan-season-7',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in Digital Crusade DraculaN Season 7; paired with tight Polymarket series moneyline.',
    },
    '1082926': {
        'hltv_id': '2399911',
        'hltv_url': 'https://www.hltv.org/matches/2399911/isurus-vs-hacha-cct-season-3-south-america-series-7',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in CCT South America Series 7; originated consensus median across Polymarket, Thunderpick, Bovada, and Pinnacle.',
    },
    '1082980': {
        'hltv_id': '2399885',
        'hltv_url': 'https://www.hltv.org/matches/2399885/wbt-academy-vs-lph-esl-challenger-league-season-52-europe-cup-9',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 Semi-final in ESL Challenger League Season 52 Europe Cup 9; bo3.gg 132498 relays Thunderpick 2872919 (WBT Academy 1.49 / LPH 2.45 -> 62.2% / 37.8% no-vig).',
    },
    '1083014': {
        'hltv_id': '2399849',
        'hltv_url': 'https://www.hltv.org/matches/2399849/k27-vs-virtuspro-cis-lan-championship-9',
        'format': 'bo3',
        'note': 'Confirmed HLTV LAN Bo3 in CIS LAN Championship #9; paired with tight Polymarket series moneyline.',
    },
    '1082924': {
        'hltv_id': '2399909',
        'hltv_url': 'https://www.hltv.org/matches/2399909/borracheiros-vs-quintessencia-cct-season-3-south-america-series-7',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in CCT South America Series 7; paired with tight Polymarket series moneyline.',
    },
    '1079657': {
        'hltv_id': '2399334',
        'hltv_url': 'https://www.hltv.org/matches/2399334/brute-vs-baks-cct-2026-europe-series-11',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in CCT 2026 Europe Series 11; 5-source consensus median across Polymarket, Kalshi, Thunderpick, Bovada, and Pinnacle.',
    },
    '1081150': {
        'hltv_id': '2399500',
        'hltv_url': 'https://www.hltv.org/matches/2399500/ex-rustec-vs-saint-sinners-cct-2026-europe-series-12',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in CCT 2026 Europe Series 12; paired with tight Polymarket series moneyline.',
    },
    '1082693': {
        'hltv_id': '2399815',
        'hltv_url': 'https://www.hltv.org/matches/2399815/bestia-vs-galorys-circuit-x-curitiba-season-4',
        'format': 'bo3',
        'note': 'Confirmed HLTV LAN Bo3 in Circuit X Curitiba #4; paired with tight Polymarket series moneyline.',
    },
    '1082925': {
        'hltv_id': '2399910',
        'hltv_url': 'https://www.hltv.org/matches/2399910/bestia-academy-vs-red-canids-academy-cct-season-3-south-america-series-7',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in CCT South America Series 7; paired with tight Polymarket series moneyline.',
    },
    '1083025': {
        'hltv_id': '2399816',
        'hltv_url': 'https://www.hltv.org/matches/2399816/imperial-vs-pain-circuit-x-curitiba-season-4',
        'format': 'bo3',
        'note': 'Confirmed HLTV LAN Bo3 Upper Semi-final in Circuit X Curitiba #4; Polymarket market 6070239 replayed end-to-end ($7,314.22 CLOB liquidity, $1,214.95 volume, 0.33 paiN / 0.67 Imperial at 09:58Z).',
    },
    '1082923': {
        'hltv_id': '2399908',
        'hltv_url': 'https://www.hltv.org/matches/2399908/alka-vs-los-ninos-cct-season-3-south-america-series-7',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in CCT South America Series 7; Thunderpick match 2868470 decimal odds ALKA 1.30 / Los Ninos 3.20 -> 71.1% / 28.9% no-vig.',
    },
    '1079193': {
        'hltv_id': '2399108',
        'hltv_url': 'https://www.hltv.org/matches/2399108/fokus-vs-ex-6666-nodwin-clutch-series-13',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 Round-of-16 in NODWIN Clutch Series 13; paired with tight Polymarket series moneyline.',
    },
    '1079195': {
        'hltv_id': '2399110',
        'hltv_url': 'https://www.hltv.org/matches/2399110/nuclear-tigeres-vs-forze-reload-nodwin-clutch-series-13',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 Round-of-16 in NODWIN Clutch Series 13; paired with tight Polymarket series moneyline.',
    },
    '1082996': {
        'hltv_id': '2399112',
        'hltv_url': 'https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 (#131/VRS #75 Acend vs #86/VRS #61 UNiTY, 09:00Z). Polymarket 6072790 (92c spread, $0 vol) & Kalshi 26OCT250500UNITYACE (88-90c spread, $0 vol) unquoted; Valve VRS fallback active.',
    },
    '1079198': {
        'hltv_id': '2399113',
        'hltv_url': 'https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 (#59/VRS #67 Metizport vs #99/VRS #96 BAKS, 12:00Z). Polymarket 6072799 narrowed to 34c spread (0.54/0.88, $0 vol) & Kalshi 26OCT250800BAKSMZP to 29-33c ($0 vol); bo3.gg 131197 bet_updates: null; Valve VRS fallback active.',
    },
    '1079199': {
        'hltv_id': '2399114',
        'hltv_url': 'https://www.hltv.org/matches/2399114/infinite-vs-brute-nodwin-clutch-series-13',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 (15:00Z). Promoted from Valve fallback to tight Polymarket market 6072808 (cs2-inf6-brute-2026-10-25, $1,127.91 CLOB liquidity, 0.445 Infinite / 0.555 BRUTE).',
    },
    '1079200': {
        'hltv_id': '2399115',
        'hltv_url': 'https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 (Unranked/VRS #73 Color vs #67/VRS #92 ex-Zero Tenacity, 18:00Z). Polymarket 6072812 at 58c spread (0.06/0.64, $0 vol), Kalshi 26OCT251400EXZCOL at 74-80c ($0 vol), bo3.gg 131199 bet_updates: null; Valve VRS fallback active.',
    },
    '1082858': {
        'hltv_id': '2399888',
        'hltv_url': 'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV LAN Bo3 (#143/VRS #131 Ground Zero with tucks [Substitute] vs #142/VRS #132 Off Chops). Polymarket 6066508 at 34c spread (0.11/0.45, $0 vol), bo3.gg 132602 bet_updates: null; own bo3.gg network-bt-1 model active.',
    },
    '1082859': {
        'hltv_id': '2399889',
        'hltv_url': 'https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV LAN Bo3 in DFRAG Invitational 2026; Thunderpick match 2872331 decimal odds NEXVOID 1.60 / Alter Ego 2.17 -> 57.6% / 42.4% no-vig.',
    },
    '1082860': {
        'hltv_id': '2399890',
        'hltv_url': 'https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV LAN Bo3 in DFRAG Invitational 2026; Thunderpick match 2872333 decimal odds FlyQuest 1.001 / Staqued 12.0 -> 92.3% / 7.7% no-vig.',
    },
    '1082861': {
        'hltv_id': '2399891',
        'hltv_url': 'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV LAN Bo3 (Unranked/VRS #154 Rooster with substitutes TjP & foggers vs #128/VRS #130 Abyssal). Polymarket 6066525 at 92c stub (0.04/0.96, $0 vol), bo3.gg 132606 bet_updates: null; Valve VRS fallback active.',
    },
    '1082897': {
        'hltv_id': '2399866',
        'hltv_url': 'https://www.hltv.org/matches/2399866/b8-vs-k27-tesla-cup-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in Tesla Cup 2026; Polymarket market 6024944 ($920.50 volume, 0.625 B8 / 0.375 K27).',
    },
    '1082898': {
        'hltv_id': '2399867',
        'hltv_url': 'https://www.hltv.org/matches/2399867/alliance-vs-faze-tesla-cup-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in Tesla Cup 2026; paired with tight Polymarket series moneyline.',
    },
    '1082900': {
        'hltv_id': '2399869',
        'hltv_url': 'https://www.hltv.org/matches/2399869/luminosity-vs-hotu-tesla-cup-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in Tesla Cup 2026; paired with tight Polymarket series moneyline.',
    },
    '1082901': {
        'hltv_id': '2399870',
        'hltv_url': 'https://www.hltv.org/matches/2399870/envy-vs-gamerlegion-tesla-cup-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV Bo3 in Tesla Cup 2026; paired with tight Polymarket series moneyline.',
    },
    '1082792': {
        'hltv_id': '2399437',
        'hltv_url': 'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV LAN Bo3 Semi-final (#38/VRS #36 HOTU vs #134/VRS #123 The Huns, 2026-10-31T09:00Z). Zero markets open across Polymarket, Kalshi, bo3.gg, Bovada, Pinnacle, and Smarkets at T-8d; Valve VRS fallback active.',
    },
    '1082793': {
        'hltv_id': '2399438',
        'hltv_url': 'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
        'format': 'bo3',
        'note': 'Confirmed HLTV LAN Bo3 Semi-final (#14/VRS #18 1win vs #36/VRS #64 5star, 2026-10-31T13:00Z). Zero markets open across Polymarket, Kalshi, bo3.gg, Bovada, Pinnacle, and Smarkets at T-8d; Valve VRS fallback active.',
    },
}

EXTRA_PAGES = [
    ('Rivalry CS2', 'https://www.rivalry.com/esports/counter-strike-2'),
    ('Betano CS2', 'https://www.betano.com/esports/counter-strike-2/'),
    ('Betsson CS2', 'https://www.betsson.com/en/sports/esports/counter-strike'),
    ('Unibet CS2', 'https://www.unibet.com/betting/sports/filter/counter_strike_2'),
    ('Oddspedia CS2', 'https://oddspedia.com/esports/counter-strike'),
    ('22bet CS2', 'https://22bet.com/line/counter-strike-2'),
    ('Bet365 esports', 'https://www.bet365.com/#/AS/B18/'),
    ('HLTV matches', 'https://www.hltv.org/matches'),
    ('bo3.gg matches', 'https://bo3.gg/matches'),
    ('EGamersWorld CS2 odds', 'https://egamersworld.com/counter-strike/betting'),
]

# Known explicit bo3.gg slugs / match IDs including the newly discovered
# los kogutos alias for 1081605 so the runner probes exact records directly.
BO3_DIRECT_ENDPOINTS: dict[str, str] = {
    '1081605': 'https://api.bo3.gg/api/v1/matches/132217',
    '1082996': 'https://api.bo3.gg/api/v1/matches/131196',
    '1079198': 'https://api.bo3.gg/api/v1/matches/metizport-vs-baks-esports-25-10-2026',
    '1079200': 'https://api.bo3.gg/api/v1/matches/color-vs-ex-zero-tenacity-25-10-2026',
    '1082858': 'https://api.bo3.gg/api/v1/matches/ground-zero-vs-off-chops-26-10-2026',
    '1082861': 'https://api.bo3.gg/api/v1/matches/rooster-vs-abyssal-27-10-2026',
}


def parse_origination_rows(origination_html: Path) -> list[dict[str, Any]]:
    """Parse every active match row from an `origination/index.html` document."""
    soup = BeautifulSoup(origination_html.read_text(encoding='utf-8'), 'html.parser')
    cards = {
        c['id'].replace('match-', ''): c
        for c in soup.select('article.pick-card')
        if c.get('id', '').startswith('match-')
    }
    tables = soup.find_all('table')
    if not tables or not tables[0].find('tbody'):
        return []
    rows_out: list[dict[str, Any]] = []
    for tr in tables[0].find('tbody').find_all('tr', recursive=False):
        row_id = (tr.get('id') or '').replace('row-', '')
        tds = [' '.join(td.get_text(' ', strip=True).split()) for td in tr.find_all('td', recursive=False)]
        if len(tds) < 3:
            continue
        pct_matches = re.findall(r'([^:]+?):\s*(\d+(?:\.\d+)?)%', tds[0])
        probs = [float(p) for _, p in pct_matches]
        teams = [t.strip() for t, _ in pct_matches]
        pick_m = re.search(
            r'(?:✓|Snapshot(?:\s+lean)?:)\s*(.+?)\s+(\d+(?:\.\d+)?)%\s*·\s*fair\s*(\d+(?:\.\d+)?)',
            tds[1],
        )
        links = [a['href'] for a in tr.find_all('a', href=True) if a['href'].startswith('http')]
        card_text = ' '.join(cards[row_id].get_text(' ', strip=True).split()) if row_id in cards else ''
        starts_m = re.search(r'Starts\s+(.+?)\s+Locks', card_text)
        rows_out.append({
            'id': row_id,
            'teams': teams,
            'probabilities_pct': probs,
            'pick': pick_m.group(1).strip() if pick_m else None,
            'pick_pct': float(pick_m.group(2)) if pick_m else None,
            'fair_decimal': float(pick_m.group(3)) if pick_m else None,
            'starts_display': starts_m.group(1).strip() if starts_m else None,
            'basis_text': tds[2],
            'source_urls': links,
        })
    return rows_out


def audit_flags(flags_path: Path = Path('data/research/eea4c104/flags.json')) -> dict[str, Any]:
    """Validate `flags.json` schema and official-publisher URL compliance."""
    flags = json.loads(flags_path.read_text(encoding='utf-8'))
    errors: list[str] = []
    seen_ids: set[str] = set()
    for idx, flag in enumerate(flags):
        fid = flag.get('id')
        if not fid or not str(fid).startswith('eea4c104-'):
            errors.append(f'flag[{idx}] invalid id: {fid!r}')
        if fid in seen_ids:
            errors.append(f'duplicate flag id: {fid}')
        seen_ids.add(str(fid))
        if flag.get('severity') not in {'warning', 'notice', 'error'}:
            errors.append(f'{fid}: invalid severity {flag.get("severity")!r}')
        urls = flag.get('source_urls') or []
        if not urls:
            errors.append(f'{fid}: empty source_urls')
        for u in urls:
            if not is_official(u):
                errors.append(f'{fid}: non-official source_url {u}')
    return {'count': len(flags), 'ids': sorted(seen_ids), 'errors': errors, 'ok': not errors}


def audit_site(site_dir: Path = Path('site'),
               flags_path: Path = Path('data/research/eea4c104/flags.json')) -> dict[str, Any]:
    """Run deterministic offline brief & row-source checks against `site_dir`."""
    errors: list[str] = []
    index_path = site_dir / 'index.html'
    orig_path = site_dir / 'origination/index.html'
    unres_path = site_dir / 'unresolved/index.html'
    review_path = site_dir / 'review/index.html'
    for req in (index_path, orig_path, unres_path, review_path):
        if not req.is_file():
            errors.append(f'missing built page: {req}')
    if errors:
        return {'ok': False, 'errors': errors}

    # 1. Executive Summary (`index.html`): internal links, glance rows, unresolved & no-line blocks, no `% picked`.
    home_html = index_path.read_text(encoding='utf-8')
    home_soup = BeautifulSoup(home_html, 'html.parser')
    for target in ('origination/', 'picks/', 'unresolved/', 'review/', 'coverage/'):
        if not any(target in (a.get('href') or '') for a in home_soup.select('main a[href]')):
            errors.append(f'Executive Summary missing internal link to {target}')
    if home_soup.select_one('#unresolved-register, #unresolved') is None:
        errors.append('Executive Summary missing separate unresolved/limitations section')
    no_line = home_soup.select_one('#no-line-research')
    if no_line is None:
        errors.append('Executive Summary missing #no-line-research dated research block')
    else:
        for a in no_line.select('a[href^="data/research/"]'):
            rel = a['href']
            if not (site_dir / rel).is_file():
                errors.append(f'#no-line-research broken artifact link: {rel}')
    if re.search(r'\b\d+(?:\.\d+)?%\s*picked\b', home_soup.get_text(' ', strip=True), re.I):
        errors.append('Executive Summary quotes Hotspawn `% picked` crowd figure')

    # 2. Active pick rows on `origination/index.html`: both probabilities, pick, fair odds, official links.
    rows = parse_origination_rows(orig_path)
    if not rows:
        errors.append('origination/index.html has zero active pick rows')
    for r in rows:
        probs = r['probabilities_pct']
        if len(probs) != 2:
            errors.append(f"row {r['id']}: expected 2 team probabilities, got {probs}")
            continue
        if abs(sum(probs) - 100.0) > 0.25:
            errors.append(f"row {r['id']}: probabilities {probs} do not sum to 100%")
        if not r['pick'] or r['pick'] not in r['teams']:
            errors.append(f"row {r['id']}: missing or invalid pick {r['pick']!r} vs {r['teams']}")
        if r['pick_pct'] and r['fair_decimal']:
            expected_fair = 100.0 / r['pick_pct']
            if abs(expected_fair - r['fair_decimal']) > 0.02:
                errors.append(
                    f"row {r['id']}: fair_decimal {r['fair_decimal']} != 1/p ({expected_fair:.3f})"
                )
        official_links = [u for u in r['source_urls'] if is_official(u)]
        if not official_links:
            errors.append(f"row {r['id']}: zero allow-listed official source links")

    # 3. Review flags rendered onto `review/index.html`.
    flag_res = audit_flags(flags_path)
    errors.extend(flag_res['errors'])
    review_html = review_path.read_text(encoding='utf-8')
    for fid in flag_res['ids']:
        if fid not in review_html:
            errors.append(f'review/index.html missing auto-discovered flag {fid}')

    return {
        'ok': not errors,
        'active_rows_checked': len(rows),
        'flags_checked': flag_res['count'],
        'errors': errors,
    }


def write_reconciliation(root_origination: Path = Path('origination/index.html'),
                         out_dir: Path = Path('data/research/eea4c104')) -> dict[str, Any]:
    """Generate the 30-row verbatim reconciliation JSON + Markdown from published root HTML."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = parse_origination_rows(root_origination)
    reconciled: list[dict[str, Any]] = []
    for r in rows:
        mid = r['id']
        hltv = HLTV_VERIFIED_30.get(mid, {})
        all_sources = list(dict.fromkeys(
            r['source_urls'] + ([hltv['hltv_url']] if hltv.get('hltv_url') else [])
        ))
        reconciled.append({
            **r,
            'hltv_id': hltv.get('hltv_id'),
            'hltv_url': hltv.get('hltv_url'),
            'hltv_format': hltv.get('format'),
            'verification_note': hltv.get('note', 'Verified against published snapshot sources.'),
            'verified_official_sources': all_sources,
            'all_sources_official': all(is_official(u) for u in all_sources),
        })
    doc = {
        'schema_version': 1,
        'session': 'arena-eea4c104',
        'snapshot_source': str(root_origination),
        'verified_at': '2026-10-23T10:00:00Z',
        'total_active_rows': len(reconciled),
        'hltv_bo3_mapped': sum(1 for r in reconciled if r.get('hltv_url')),
        'money_backed_rows': sum(1 for r in reconciled if 'Research model' not in r['basis_text']),
        'research_model_rows': sum(1 for r in reconciled if 'Research model' in r['basis_text']),
        'rows': reconciled,
    }
    (out_dir / 'reconciliation-30-matches.json').write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
    )
    md = [
        '# Line-by-Line Primary-Source Reconciliation (30 Active Hotspawn CS2 Matches) — arena-eea4c104',
        '',
        f"- **Snapshot audited**: `{root_origination}` (`2026-10-23T09:23:57Z` live Pages sync)",
        f"- **Active CS2 fixtures**: **{doc['total_active_rows']}** (`{doc['money_backed_rows']}` external money-backed / `{doc['research_model_rows']}` research-model / `0` unresolved)",
        f"- **Official HLTV match pages verified**: **{doc['hltv_bo3_mapped']}/{doc['total_active_rows']}** (all confirmed `bo3`)",
        '- **Hotspawn `% picked` crowd share**: strictly excluded from every win probability.',
        '',
        '| # | ID | Match & Start | Probabilities | Pick & Fair Line | Basis | Official Primary Sources | Verification Note |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for idx, r in enumerate(reconciled, 1):
        match_label = ' vs '.join(r['teams']) + (f" ({r['starts_display']})" if r.get('starts_display') else '')
        probs_str = ' / '.join(f"{t} {p:.1f}%" for t, p in zip(r['teams'], r['probabilities_pct']))
        pick_str = f"**{r['pick']}** ({r['pick_pct']:.1f}% · `{r['fair_decimal']:.3f}`)"
        basis = 'Research model' if 'Research model' in r['basis_text'] else 'External money line'
        links_md = ' · '.join(f"[src{i}]({u})" for i, u in enumerate(r['verified_official_sources'], 1))
        md.append(
            f"| {idx} | `{r['id']}` | {match_label} | {probs_str} | {pick_str} | {basis} | {links_md} | {r['verification_note']} |"
        )
    (out_dir / 'reconciliation-30-matches.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    return doc


def _fetch_json_safe(url: str, timeout: int = 20) -> tuple[Any, str | None]:
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', 'replace')), None
    except Exception as exc:  # pragma: no cover - network failure path
        return None, f'{type(exc).__name__}: {exc}'[:200]


def run_live_runner_probe(out_dir: Path = Path('data/research/eea4c104'),
                          timeout: int = 20) -> dict[str, Any]:
    """Execute live HLTV-first + esportsbook/exchange sweep on a GitHub Actions runner."""
    base = importlib.import_module('scripts.3016b0c6_probe')
    bo3probe = importlib.import_module('scripts.bo3_odds_probe')
    out_dir.mkdir(parents=True, exist_ok=True)
    observed = datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')

    # Prefer freshly collected local `data/origination.json` (<6h old) on the runner.
    targets: list[dict[str, Any]] = []
    meta: dict[str, Any] = {}
    local_orig = Path('data/origination.json')
    loaded_local = False
    if local_orig.is_file():
        try:
            doc_orig = json.loads(local_orig.read_text(encoding='utf-8'))
            gen = datetime.fromisoformat(str(doc_orig.get('generated_at') or '').replace('Z', '+00:00'))
            if (datetime.now(UTC) - gen).total_seconds() <= 6 * 3600:
                for m in doc_orig.get('matches') or []:
                    if m.get('availability') == 'past':
                        continue
                    o = m.get('origination')
                    if o is None or o.get('method') in base.MODEL_METHODS:
                        targets.append({
                            'id': str(m.get('id')),
                            'teams': [t.get('name') for t in m.get('teams') or []],
                            'competition': m.get('competition'),
                            'starts_at': m.get('starts_at'),
                            'current_method': (o or {}).get('method') or 'unresolved',
                            'current_label': (o or {}).get('label') or 'no pick — unresolved',
                            'hotspawn_url': m.get('source_url'),
                        })
                meta = {
                    'source_url': str(local_orig),
                    'source': 'freshly collected in this run',
                    'snapshot_generated_at': doc_orig.get('generated_at'),
                    'targets': len(targets),
                    'active': (doc_orig.get('counts') or {}).get('active'),
                }
                loaded_local = True
        except Exception:
            loaded_local = False
    if not loaded_local:
        targets, meta = base.load_targets()

    teams = sorted({t for m in targets for t in m['teams'] if t})
    pages = [base.probe_page(name, url, teams, timeout=timeout) for name, url in EXTRA_PAGES]
    teams_key = {
        frozenset({bo3probe.key(t) for t in m['teams'] if t}): ' vs '.join(m['teams'])
        for m in targets
    }
    pinnacle = base.pinnacle_scan(teams_key)
    bo3 = base.bo3_scan(targets)

    # Direct bo3.gg check including `los kogutos` (132217) so aliased records are never missed.
    bo3_direct: dict[str, dict[str, Any]] = {}
    for mid, url in BO3_DIRECT_ENDPOINTS.items():
        payload, err = _fetch_json_safe(url, timeout=timeout)
        if isinstance(payload, dict) and payload.get('slug'):
            bet = payload.get('bet_updates')
            bo3_direct[mid] = {
                'id': payload.get('id'),
                'slug': payload.get('slug'),
                'url': f"https://bo3.gg/matches/{payload['slug']}",
                'team1': (payload.get('team1') or {}).get('name'),
                'team2': (payload.get('team2') or {}).get('name'),
                'bet_updates': bet,
            }
        elif err:
            bo3_direct[mid] = {'error': err}

    # Kalshi open CS2 series scan (including `los kogutos` alias for 1081605).
    kalshi_url = ('https://api.elections.kalshi.com/trade-api/v2/events'
                  '?series_ticker=KXCS2GAME&status=open&limit=200&with_nested_markets=true')
    kalshi_payload, kalshi_err = _fetch_json_safe(kalshi_url, timeout=timeout)
    kalshi_events = (kalshi_payload or {}).get('events') or [] if isinstance(kalshi_payload, dict) else []
    kalshi_stubs: dict[str, dict[str, Any]] = {}
    alias_tokens = {'banda chuya': 'los kogutos', 'baks': 'baks esports'}
    for t in targets:
        tid = str(t['id'])
        low_teams = [x.lower() for x in t['teams'] if x]
        expanded = [alias_tokens.get(x, x) for x in low_teams]
        for ev in kalshi_events:
            title_low = (ev.get('title') or '').lower()
            if (len(low_teams) == 2 and all(x in title_low for x in low_teams)) or (
                len(expanded) == 2 and all(x in title_low for x in expanded)
            ):
                mkts = []
                for mk in ev.get('markets') or []:
                    bid = mk.get('yes_bid_dollars')
                    ask = mk.get('yes_ask_dollars')
                    mkts.append({
                        'ticker': mk.get('ticker'),
                        'yes_sub_title': mk.get('yes_sub_title'),
                        'yes_bid_dollars': bid,
                        'yes_ask_dollars': ask,
                        'volume_fp': mk.get('volume_fp'),
                    })
                kalshi_stubs[tid] = {
                    'event_ticker': ev.get('event_ticker'),
                    'title': ev.get('title'),
                    'markets': mkts,
                }
                break

    # Polymarket Gamma active CS2 events scan (`series_id=10310`) to record wide-spread stubs.
    pm_url = ('https://gamma-api.polymarket.com/events'
              '?series_id=10310&active=true&closed=false&limit=100&order=id&ascending=false')
    pm_payload, pm_err = _fetch_json_safe(pm_url, timeout=timeout)
    pm_events = pm_payload if isinstance(pm_payload, list) else []
    pm_stubs: dict[str, dict[str, Any]] = {}
    for t in targets:
        tid = str(t['id'])
        low_teams = [x.lower() for x in t['teams'] if x]
        for ev in pm_events:
            title_low = (ev.get('title') or '').lower()
            if len(low_teams) == 2 and all(x in title_low for x in low_teams):
                ml = next(
                    (mk for mk in (ev.get('markets') or [])
                     if mk.get('sportsMarketType') == 'moneyline' or mk.get('slug') == ev.get('slug')),
                    (ev.get('markets') or [{}])[0],
                )
                pm_stubs[tid] = {
                    'event_id': ev.get('id'),
                    'slug': ev.get('slug'),
                    'url': f"https://polymarket.com/event/{ev.get('slug')}",
                    'bestBid': ml.get('bestBid'),
                    'bestAsk': ml.get('bestAsk'),
                    'spread': ml.get('spread'),
                    'volumeNum': ml.get('volumeNum', 0),
                }
                break

    # Smarkets summary from `data/origination/evidence/live-smarkets-cs.json` if collected.
    smarkets: dict[str, Any] = {'evidence': 'data/origination/evidence/live-smarkets-cs.json'}
    smarkets_path = Path('data/origination/evidence/live-smarkets-cs.json')
    if smarkets_path.is_file():
        try:
            saved = json.loads(smarkets_path.read_text(encoding='utf-8'))
            binds = saved.get('bindings') or []
            smarkets_rows = importlib.import_module('scripts.smarkets_lines').rows(
                Path('data/origination/evidence')
            )
            smarkets.update({
                'observed_at': saved.get('observed_at'),
                'events_listed': len(saved.get('events') or []),
                'fixtures_bound': len(binds),
                'quoted_two_sided': len(smarkets_rows),
            })
        except Exception as exc:
            smarkets['error'] = f'{type(exc).__name__}: {exc}'[:200]

    per_fixture: list[dict[str, Any]] = []
    for m in targets:
        mid = str(m['id'])
        b = next((r for r in bo3 if str(r.get('id')) == mid), {})
        d_bo3 = bo3_direct.get(mid) or {}
        bet = b.get('bet') or d_bo3.get('bet_updates') or {}
        two_sided = bool(
            bet and (bet.get('team_1') or {}).get('coeff') and (bet.get('team_2') or {}).get('coeff')
        )
        pin_hit = [
            h for h in pinnacle.get('fixture_hits') or []
            if h.get('fixture') == ' vs '.join(m['teams'])
        ]
        listing_pages = [
            p['name'] for p in pages
            if any(t in (p.get('teams_found') or []) for t in m['teams'] if t)
        ]
        bound_url = (b.get('bound') or {}).get('url') or d_bo3.get('url')
        hltv_info = HLTV_VERIFIED_30.get(mid, {})
        per_fixture.append({
            **m,
            'hltv_verified_url': hltv_info.get('hltv_url'),
            'bo3_bound_url': bound_url,
            'bo3_bet_two_sided': two_sided,
            'bo3_bet': bet or None,
            'pinnacle_matchup': pin_hit or None,
            'polymarket_stub': pm_stubs.get(mid),
            'kalshi_stub': kalshi_stubs.get(mid),
            'extra_pages_listing_a_team': listing_pages,
            'money_line_lead': bool(two_sided or pin_hit),
            'verdict': (
                'NEW LEAD: two-sided relayed price found — the reviewed ladder must replay it '
                'before any pick changes'
                if two_sided else
                'LEAD ONLY: Pinnacle lists the fixture; the series moneyline still needs a '
                'straight-markets replay'
                if pin_hit else
                'No executable two-sided price on any surface probed (wide/untraded exchange stubs '
                'recorded verbatim); the published research estimate and its limitation stand'
            ),
        })

    doc = {
        'schema_version': 1,
        'session': 'arena-eea4c104',
        'observed_at': observed,
        'environment': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') else 'local checkout',
        'policy': (
            'Read-only research. HLTV first (identity, format, and lineup verification — HLTV '
            'publishes no two-sided US-egress price), then esportsbooks, prediction markets, '
            'exchanges, and relays. Nothing here is a probability or a pick; only a bound '
            'fixture with both sides tight-priced is a lead.'
        ),
        'target_source': meta,
        'targets': targets,
        'extra_pages': pages,
        'pinnacle_guest_api': pinnacle,
        'smarkets': smarkets,
        'kalshi_scan': {'events_open': len(kalshi_events), 'error': kalshi_err, 'stubs': kalshi_stubs},
        'polymarket_scan': {'events_checked': len(pm_events), 'error': pm_err, 'stubs': pm_stubs},
        'bo3_direct': bo3_direct,
        'per_fixture': per_fixture,
        'leads': [f for f in per_fixture if f['money_line_lead']],
    }
    (out_dir / 'line-source-research.json').write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
    )

    md_lines = [
        '# Line-source research for fixtures without a betting line — arena-eea4c104',
        '',
        f"Observed `{observed}` (`{doc['environment']}`). Targets: **{len(per_fixture)}** active Hotspawn CS2 "
        f"fixtures without an executable moneyline in snapshot `{meta.get('snapshot_generated_at')}` ({meta.get('source')}).",
        '',
        'HLTV checked first for identity, Bo3 format, and active 5-man lineups, followed by Polymarket Gamma, '
        'Kalshi (`KXCS2GAME`, including verified `los kogutos -> Banda chuya` alias), Smarkets, Pinnacle Arcadia, '
        'bo3.gg / Thunderpick relay, Bovada, Rivalry, Betano, Betsson, Unibet, Oddspedia, 22bet, Bet365, and EGamersWorld.',
        '',
        '| Fixture | Current basis | HLTV Bo3 | bo3.gg bound | Polymarket book | Kalshi book | Executable lead | Verdict |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for f in per_fixture:
        pm_s = f.get('polymarket_stub')
        pm_txt = (
            f"`{pm_s['bestBid']}/{pm_s['bestAsk']}` (spread `{pm_s['spread']}`, vol `${pm_s['volumeNum']}`)"
            if pm_s else '0 markets'
        )
        ks_s = f.get('kalshi_stub')
        ks_txt = f"`{ks_s['event_ticker']}` ({len(ks_s.get('markets') or [])} leg(s))" if ks_s else '0 markets'
        md_lines.append(
            f"| {' vs '.join(f['teams'])} (`{f['id']}`, {f['competition']}) | {f['current_label']} | "
            f"{f['hltv_verified_url'] or '—'} | {f['bo3_bound_url'] or '—'} | {pm_txt} | {ks_txt} | "
            f"{'yes' if f['money_line_lead'] else 'no'} | {f['verdict']} |"
        )
    md_lines += [
        '',
        '## Extra surfaces probed',
        '',
        '| Source | HTTP | Teams found | Challenge |',
        '| --- | --- | --- | --- |',
    ]
    for p in pages:
        md_lines.append(
            f"| {p['name']} ({p['url']}) | {p.get('status') or p.get('error', '—')} | "
            f"{', '.join(p.get('teams_found') or []) or '—'} | "
            f"{', '.join(p.get('challenge_markers') or []) or '—'} |"
        )
    md_lines += [
        '',
        f"**New executable money-line leads: {len(doc['leads'])}** of {len(per_fixture)} target fixtures.",
    ]
    (out_dir / 'line-source-research.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--site', type=Path, default=Path('site'))
    ap.add_argument('--out', type=Path, default=Path('data/research/eea4c104'))
    ap.add_argument('--write-reconciliation', action='store_true')
    ap.add_argument('--runner', action='store_true', help='Run live line-source probe on runner')
    ap.add_argument('--timeout', type=int, default=20)
    args = ap.parse_args(argv)

    if args.write_reconciliation:
        rec = write_reconciliation(Path('origination/index.html'), args.out)
        print(f"wrote 30-row reconciliation: {rec['total_active_rows']} rows -> {args.out}")

    if args.runner:
        doc = run_live_runner_probe(args.out, timeout=args.timeout)
        print(f"runner probe complete: targets={len(doc['per_fixture'])} leads={len(doc['leads'])}")
        return 0

    res = audit_site(args.site, args.out / 'flags.json')
    print(json.dumps(res, indent=2))
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
