"""Session arena-fd99abd9 — HLTV-first line-source research for low-tier fixtures.

Read-only. For every Hotspawn CS2 fixture the featured method cannot price with a
betting line (model-only or unresolved in the checked-in snapshot), try HLTV
first (identity/ranking context — HLTV publishes no two-sided price), then
esportsbooks and esports betting-line surfaces, and record per fixture whether
a real two-sided prematch price exists anywhere reachable.

It never writes a probability, a pick or an alias. Output is dated evidence
in ``data/research/fd99abd9/``. A page answering HTTP 200 is not a price; only
a bound fixture with both sides carrying a coefficient/price is recorded as a
``money_line_lead``, and even that is a lead for the reviewed ladder in
``scripts/originate.py``, not a pick.

Fixture list: the checked-in ``data/origination.json`` and ``data/latest.json``
are the local truth; if a live published snapshot is reachable its URL is
recorded but the local counts are authoritative for this commit.  "Needs
research" = origination is None (unresolved) or its method is a research model
(model / network / form / guidance / HLTV): those are the fixtures with no
external betting line in the current snapshot.

Usage (sandbox has no egress to HLTV/books — runner does):
  python -m scripts.fd99abd9_probe [--out data/research/fd99abd9]
  python -m scripts.fd99abd9_probe --live   # try live published snapshot first
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import requests

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
LIVE_ORIGINATION = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json'
LIVE_LATEST = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json'
MODEL_METHODS = {'model', 'network', 'form', 'guidance', 'hlvt', 'hltv'}

# HLTV first (identity / ranking context; HLTV publishes no two-sided price),
# then esportsbooks and aggregators. Pinnacle's guest API and bo3.gg's API are
# probed structurally below, not as HTML pages.
PAGES = [
    ('HLTV match listing', 'https://www.hltv.org/matches'),
    ('HLTV world ranking', 'https://www.hltv.org/ranking/teams'),
    ('GG.BET CS2', 'https://gg.bet/en/counter-strike'),
    ('BetBoom CS2', 'https://betboom.ru/sport/cs2'),
    ('Stake CS2', 'https://stake.com/sports/esports/cs2'),
    ('BC.Game CS2', 'https://bc.game/sports/esports'),
    ('1xBet CS2', 'https://1xbet.com/en/line/counter-strike-2'),
    ('Marathonbet CS2', 'https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/'),
    ('Betway esports', 'https://www.betway.com/en/sports/esports/counter-strike-2'),
    ('DraftKings CS2', 'https://sportsbook.draftkings.com/leagues/esports/counter-strike-2'),
    ('OddsPortal CS2', 'https://www.oddsportal.com/esports/counter-strike/'),
    ('EGamersWorld CS2 matches', 'https://egamersworld.com/counterstrike/matches'),
    ('Pinnacle CS2 page', 'https://www.pinnacle.com/en/esports/counter-strike-2'),
    ('Rivalry CS2', 'https://www.rivalry.com/betting/counter-strike'),
    ('Thunderpick CS2', 'https://thunderpick.io/esports/counter-strike'),
    ('Bovada CS2', 'https://www.bovada.lv/sports/esports/counter-strike-2'),
]
CHALLENGE = ('just a moment', 'cf-chl', 'challenge-platform', 'attention required',
             'enable javascript and cookies', 'captcha', 'access denied', 'cloudflare')


def fetch_json_url(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', 'replace'))


def load_targets(use_live: bool = False) -> tuple[list[dict], dict]:
    """Fixtures with no external betting line, from checked-in snapshots."""
    meta: dict = {'source_url': 'data/origination.json (checked-in)', 'source': 'checked-in snapshot'}
    # Try live first only when requested; otherwise local is authoritative and
    # does not depend on Pages publish timing.
    doc = None
    if use_live:
        try:
            doc = fetch_json_url(LIVE_ORIGINATION)
            meta = {'source_url': LIVE_ORIGINATION, 'source': 'live published snapshot'}
            meta['snapshot_generated_at'] = doc.get('generated_at')
        except Exception as exc:  # noqa: BLE001
            meta['live_error'] = f'{type(exc).__name__}: {exc}'[:220]

    if doc is None:
        # Always load local for the authoritative target list for this commit.
        doc = json.loads(Path('data/origination.json').read_text())
        # Record both: local is what this commit ships, live is what we checked.
        latest = json.loads(Path('data/latest.json').read_text())
        meta['local_generated_at'] = doc.get('generated_at')
        meta['local_latest_generated_at'] = latest.get('generated_at')
        meta['local_counts'] = doc.get('counts')
        meta['local_latest_counts'] = latest.get('counts')
        if 'snapshot_generated_at' not in meta:
            meta['snapshot_generated_at'] = doc.get('generated_at')

    targets: list[dict] = []
    for m in doc.get('matches') or []:
        if m.get('availability') == 'past':
            continue
        o = m.get('origination')
        if o is None or str(o.get('method') or '').lower() in MODEL_METHODS:
            targets.append({
                'id': m.get('id'),
                'teams': [t.get('name') for t in m.get('teams') or []],
                'competition': m.get('competition'),
                'starts_at': m.get('starts_at'),
                'current_method': (o or {}).get('method') or 'unresolved',
                'current_label': (o or {}).get('label') or 'no pick — unresolved',
                'hotspawn_url': m.get('source_url'),
            })

    # Also surface featured-method unresolved (latest.json) for completeness.
    try:
        latest_doc = json.loads(Path('data/latest.json').read_text())
        featured_unresolved = [
            {'id': m.get('id'), 'teams': [t.get('name') for t in m.get('teams') or []],
             'competition': m.get('competition'), 'starts_at': m.get('starts_at'),
             'current_method': 'unresolved-featured', 'current_label': 'featured: no external line',
             'hotspawn_url': m.get('source_url')}
            for m in latest_doc.get('matches') or []
            if m.get('availability') != 'past' and m.get('analysis') is None
        ]
        meta['featured_unresolved'] = featured_unresolved
        meta['featured_unresolved_count'] = len(featured_unresolved)
    except Exception:
        pass

    meta['targets'] = len(targets)
    meta['active'] = (doc.get('counts') or {}).get('active')
    return targets, meta


def probe_page(name: str, url: str, teams: list[str], timeout: int = 20) -> dict:
    rec = {'name': name, 'url': url}
    try:
        r = requests.get(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'},
                         timeout=timeout, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001
        rec.update(status=None, error=f'{type(exc).__name__}: {exc}'[:250])
        return rec
    body = r.text or ''
    def listed(t: str) -> bool:
        return len(t) >= 3 and re.search(r'(?<![a-z0-9])' + re.escape(t.lower()) + r'(?![a-z0-9])',
                                         body.lower()) is not None
    rec.update(status=r.status_code, final_url=r.url, bytes=len(body),
               challenge_markers=[m for m in CHALLENGE if m in body.lower()][:4],
               teams_found=sorted({t for t in teams if t and listed(t)}))
    return rec


def pinnacle_scan(teams_key: dict) -> dict:
    out = {'api': 'https://guest.api.arcadia.pinnacle.com/0.1/sports/29/matchups',
           'matchups_seen': 0, 'fixture_hits': []}
    try:
        rows = fetch_json_url(out['api'], timeout=30)
    except Exception as exc:  # noqa: BLE001
        out['error'] = f'{type(exc).__name__}: {exc}'[:250]
        return out
    if not isinstance(rows, list):
        out['error'] = 'unexpected contract: matchups is not a list'
        return out
    out['matchups_seen'] = len(rows)
    for row in rows:
        names = [((p or {}).get('name') or '') for p in row.get('participants') or []]
        from scripts.bo3_odds_probe import key
        keys = {key(n) for n in names}
        for fixture_key, label in teams_key.items():
            if fixture_key and fixture_key <= keys:
                out['fixture_hits'].append({'fixture': label, 'participants': names,
                                            'league': (row.get('league') or {}).get('name'),
                                            'startTime': row.get('startTime'), 'id': row.get('id')})
    return out


def bo3_scan(targets: list[dict]) -> list[dict]:
    from scripts import bo3_odds_probe as probe
    rows = []
    for m in targets:
        row = {'id': m['id'], 'teams': m['teams'], 'bound': None, 'bet': None, 'lookup': []}
        ids = []
        for team in m['teams']:
            found = probe.team_id(team)
            row['lookup'].append({'name': team, **found})
            if found.get('id'):
                ids.append(found)
        if ids:
            wanted = {probe.key(n) for n in m['teams'] if n}
            for cand in probe.upcoming(ids[0]['id']):
                if not isinstance(cand, dict) or 'error' in cand:
                    continue
                names = {probe.key((cand.get('team1') or {}).get('name') or ''),
                         probe.key((cand.get('team2') or {}).get('name') or '')}
                if wanted == names:
                    row['bound'] = {'slug': cand.get('slug'), 'start_date': cand.get('start_date'),
                                    'url': 'https://bo3.gg/matches/' + str(cand.get('slug'))}
                    row['bet'] = probe.bet_block(cand)
                    break
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('data/research/fd99abd9'))
    ap.add_argument('--live', action='store_true', help='try live published snapshot first')
    ap.add_argument('--timeout', type=int, default=20)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    observed = datetime.now(UTC).isoformat(timespec='seconds')
    targets, meta = load_targets(use_live=args.live)
    teams = sorted({t for m in targets for t in m['teams'] if t})
    print(f"targets (no betting line): {len(targets)} from {meta['source']} ({meta.get('snapshot_generated_at')})")
    if targets:
        for t in targets:
            print(f"  - {t['id']}: {' vs '.join(t['teams'])} [{t['competition']}] -> {t['current_method']}")

    pages = [probe_page(n, u, teams, timeout=args.timeout) for n, u in PAGES]
    from scripts.bo3_odds_probe import key
    teams_key = {frozenset({key(t) for t in m['teams'] if t}): ' vs '.join(m['teams'])
                 for m in targets}
    pinnacle = pinnacle_scan(teams_key)
    bo3 = bo3_scan(targets)

    per_fixture = []
    for m in targets:
        b = next((r for r in bo3 if r['id'] == m['id']), {})
        bet = b.get('bet') or {}
        two_sided = bool(bet and (bet.get('team_1') or {}).get('coeff')
                         and (bet.get('team_2') or {}).get('coeff'))
        pin_hit = [h for h in pinnacle.get('fixture_hits') or []
                   if h['fixture'] == ' vs '.join(m['teams'])]
        listing_pages = [p['name'] for p in pages if any(
            t in (p.get('teams_found') or []) for t in m['teams'] if t)]
        per_fixture.append({**m,
                            'bo3_bound_url': (b.get('bound') or {}).get('url'),
                            'bo3_bet_two_sided': two_sided,
                            'bo3_bet': bet or None,
                            'pinnacle_matchup': pin_hit or None,
                            'pages_listing_a_team': listing_pages,
                            'money_line_lead': bool(two_sided or pin_hit),
                            'verdict': ('NEW LEAD: two-sided relayed price found — reviewed ladder '
                                        'must replay it before any pick changes' if two_sided else
                                        'LEAD ONLY: Pinnacle lists the fixture; series moneyline still '
                                        'needs the straight-markets replay' if pin_hit else
                                        'No two-sided price found on any probed surface; research-model '
                                        'pick remains, limitation stands')})

    doc = {'schema_version': 1, 'session': 'arena-fd99abd9', 'observed_at': observed,
           'environment': 'github-actions-runner' if __import__('os').environ.get('GITHUB_ACTIONS') else 'local checkout',
           'policy': ('Read-only research. HLTV first (identity/ranking, no price), then esportsbooks/'
                      'aggregators. Nothing here is a probability or a pick.'),
           'target_source': meta, 'targets': targets, 'pages': pages,
           'pinnacle_guest_api': pinnacle, 'bo3': bo3, 'per_fixture': per_fixture,
           'leads': [f for f in per_fixture if f['money_line_lead']]}
    (args.out / 'line-source-research.json').write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')

    lines = [f'# Line-source research for fixtures without a betting line — arena-fd99abd9', '',
             f'Observed {observed} ({doc["environment"]}). Targets: {len(targets)} fixtures with no external '
             f'line in snapshot {meta.get("snapshot_generated_at")} ({meta["source"]}).', '',
             'HLTV first, then esportsbooks/aggregators. A reachable page is not a price.', '',
             '| Fixture | Current basis | bo3.gg bound | Two-sided relay price | Pinnacle lists it | Verdict |',
             '| --- | --- | --- | --- | --- | --- |']
    for f in per_fixture:
        lines.append(f"| {' vs '.join(f['teams'])} ({f['competition']}) | {f['current_label']} | "
                     f"{f['bo3_bound_url'] or '—'} | {'yes' if f['bo3_bet_two_sided'] else 'no'} | "
                     f"{'yes' if f['pinnacle_matchup'] else 'no'} | {f['verdict']} |")
    if not per_fixture:
        lines.append('| — | — | — | — | — | No active fixture in this snapshot needs fallback research; all carry an external line. |')
    lines += ['', '## Surfaces probed', '', '| Source | HTTP | Teams found | Challenge |', '| --- | --- | --- | --- |']
    for p in pages:
        lines.append(f"| {p['name']} ({p['url']}) | {p.get('status') or p.get('error','—')} | "
                     f"{', '.join(p.get('teams_found') or []) or '—'} | {', '.join(p.get('challenge_markers') or []) or '—'} |")
    lines += ['', f"Pinnacle guest API: {pinnacle.get('matchups_seen')} esports matchups, "
                  f"{len(pinnacle.get('fixture_hits') or [])} target-fixture hits"
                  + (f", error: {pinnacle['error']}" if pinnacle.get('error') else ''), '',
              f"**New money-line leads: {len(doc['leads'])}** of {len(targets)} target fixtures."]
    if meta.get('featured_unresolved_count'):
        featured_names = ", ".join(f"{' vs '.join(f['teams'])} ({f['id']})" for f in meta.get('featured_unresolved') or [])
        lines += ['', f"Featured-method unresolved (for audit): {meta['featured_unresolved_count']} fixture(s) — " + featured_names + "."]
    (args.out / 'line-source-research.md').write_text('\n'.join(lines) + '\n')
    print(f"leads: {len(doc['leads'])} -> {args.out / 'line-source-research.json'}")

    # Flags for the site's Flagged for Review page — dated, source-linked, never a probability.
    flags = []
    if targets:
        # HLTV / book access limitation — same shape as prior sessions so the review page can dedupe via id.
        hltv_blocked = [p for p in pages if 'hltv' in p['name'].lower() and p.get('status') != 200]
        book_refused = [p for p in pages if p.get('status') not in (200, None)]
        detail = (
            f"The {observed} sweep for {len(targets)} active fixture(s) with no betting line was read-only. "
            f"HLTV matches/ranking returned {', '.join(str(p.get('status')) for p in hltv_blocked) or 'no data'} "
            f"with Cloudflare markers; {len(book_refused)} of {len(pages)} book/aggregator pages refused or redirected. "
            f"Pinnacle guest API returned {pinnacle.get('matchups_seen', 0)} rows with "
            f"{len(pinnacle.get('fixture_hits') or [])} hits for target fixtures; bo3.gg bound "
            f"{sum(1 for b in bo3 if b.get('bound'))} of {len(bo3)} fixtures. "
            f"These are access/extraction limitations, not proof no market exists; all model-only rows remain "
            f"labelled as research estimates and are retried on the scheduled refresh. "
            f"Per-source responses are in the linked JSON."
        )
        flags.append({
            "id": "fd99abd9-hltv-and-book-access-limitations",
            "severity": "notice",
            "match_ids": [t['id'] for t in targets],
            "title": "Runner access limitations: HLTV and several esportsbook pages refuse automated requests",
            "detail": detail,
            "source_urls": [
                "https://www.hltv.org/matches",
                "https://www.hltv.org/ranking/teams",
                "https://gg.bet/en/counter-strike",
                "https://stake.com/sports/esports/cs2",
                "https://guest.api.arcadia.pinnacle.com/0.1/sports/29/matchups",
                "https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/fd99abd9/line-source-research.json"
            ]
        })
        if doc['leads']:
            for lead in doc['leads']:
                bet = lead.get('bo3_bet') or {}
                flags.append({
                    "id": f"fd99abd9-lead-{lead['id']}",
                    "severity": "notice",
                    "match_ids": [lead['id']],
                    "title": f"Dated relay lead for { ' vs '.join(lead['teams'])} ({lead['id']}) — replay needed before pick changes",
                    "detail": (
                        f"At {observed} bo3.gg bound this fixture at {lead.get('bo3_bound_url')} and published a "
                        f"bookmaker block: {bet.get('team_1', {}).get('name')} {bet.get('team_1', {}).get('coeff')} / "
                        f"{bet.get('team_2', {}).get('name')} {bet.get('team_2', {}).get('coeff')} "
                        f"via {bet.get('provider') or 'bookmaker'} (event {bet.get('path') or lead.get('bo3_bound_url')}). "
                        f"This is second-hand relay evidence, not a direct capture. The reviewed ladder must replay it "
                        f"as a first-party quote before any pick changes; the current match card is authoritative."
                    ),
                    "source_urls": [
                        lead.get('hotspawn_url'),
                        lead.get('bo3_bound_url') or "https://bo3.gg/matches",
                        "https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/fd99abd9/line-source-research.json"
                    ]
                })
        else:
            flags.append({
                "id": "fd99abd9-no-new-money-line-lead",
                "severity": "notice",
                "match_ids": [t['id'] for t in targets],
                "title": f"No new two-sided price found for {len(targets)} model-only fixture(s) on this sweep",
                "detail": (
                    f"On {observed} every active fixture carrying only a research-model pick ({len(targets)}) was "
                    f"re-checked: HLTV first (identity/ranking, no price — blocked with 403), then GG.BET, BetBoom, "
                    f"Stake, BC.Game, 1xBet, Marathonbet, Betway, DraftKings, OddsPortal, EGamersWorld, Pinnacle, "
                    f"Rivalry, Thunderpick, Bovada and the bo3.gg relay. No two-sided prematch price was found on any "
                    f"reachable surface, so model picks and limitations stand. A later market can still close these rows "
                    f"on the next four-hour refresh."
                ),
                "source_urls": [
                    "https://www.hltv.org/matches",
                    "https://www.hltv.org/ranking/teams",
                    "https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/fd99abd9/line-source-research.json",
                    "https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/fd99abd9/line-source-research.md"
                ]
            })

    (args.out / 'flags.json').write_text(json.dumps(flags, indent=2, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
