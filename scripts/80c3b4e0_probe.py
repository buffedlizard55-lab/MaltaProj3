"""Session arena-80c3b4e0 — runner-verified no-line source research & Smarkets alias probe.

Read-only research probe executed on GitHub Actions (`ubuntu-24.04`) after a
fresh `collect` + `originate --live` pass in `.github/workflows/80c3b4e0-probe.yml`.
Follows the user's strict source order for matches not resolved by featured
money lines:
1. HLTV first (official match pages, World Ranking, rolling VRS, rosters/subs —
   identity and context only; HLTV publishes no two-sided odds),
2. Esportsbooks and betting exchanges (Smarkets with competition-scoped alias
   binding from `scripts/smarkets_lines.py`, Pinnacle guest Arcadia API,
   bo3.gg / Thunderpick relay, Rivalry, Betano, Betsson, Unibet, Oddspedia,
   22bet, EGamersWorld).

Never uses Hotspawn crowd `picked_percent` and never mutates `data/latest.json`
or `data/origination.json`. Writes `line-source-research.json` and
`line-source-research.md` under `data/research/80c3b4e0/`.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
base = importlib.import_module('scripts.3016b0c6_probe')
probe46 = importlib.import_module('scripts.46ade650_probe')
bo3probe = importlib.import_module('scripts.bo3_odds_probe')
smarkets_lines = importlib.import_module('scripts.smarkets_lines')


HLTV_OFFICIAL_MATCH_URLS = {
    '1081605': 'https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8',
    '1082996': 'https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13',
    '1079198': 'https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13',
    '1079200': 'https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13',
    '1082858': 'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
    '1082861': 'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
    '1082792': 'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
    '1082793': 'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('data/research/80c3b4e0'))
    ap.add_argument('--timeout', type=int, default=20)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    observed = datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')

    targets, meta = probe46.load_targets()
    teams = sorted({t for m in targets for t in m['teams'] if t})
    print(f"targets (no external betting line): {len(targets)} from {meta['source']}")

    pages = [base.probe_page(name, url, teams, timeout=args.timeout) for name, url in probe46.EXTRA_PAGES]
    teams_key = {frozenset({bo3probe.key(t) for t in m['teams'] if t}): ' vs '.join(m['teams'])
                 for m in targets}
    pinnacle = base.pinnacle_scan(teams_key)
    bo3 = base.bo3_scan(targets)

    smarkets = {'evidence': 'data/origination/evidence/live-smarkets-cs.json'}
    smarkets_path = Path('data/origination/evidence/live-smarkets-cs.json')
    smarkets_by_id: dict[str, dict] = {}
    if smarkets_path.exists():
        try:
            saved = json.loads(smarkets_path.read_text())
            binds = saved.get('bindings') or []
            rows = smarkets_lines.rows(Path('data/origination/evidence'))
            rows_by_id = {str(r.get('fixture_id') or r.get('hotspawn_id')): r for r in rows}
            bound_records = []
            for b in binds:
                hid = str(b.get('hotspawn_id'))
                rec = {
                    'hotspawn_id': hid,
                    'event_id': b.get('event_id'),
                    'event_name': b.get('event_name'),
                    'event_url': b.get('event_url'),
                    'aliases_used': b.get('aliases_used') or [],
                    'two_sided_quote': hid in rows_by_id,
                }
                smarkets_by_id[hid] = rec
                bound_records.append(rec)
            smarkets.update({
                'observed_at': saved.get('observed_at'),
                'events_listed': len(saved.get('events') or []),
                'fixtures_bound': len(binds),
                'alias_bound_count': sum(1 for b in bound_records if b['aliases_used']),
                'quoted_two_sided': len(rows),
                'bound_fixtures': bound_records,
                'errors': saved.get('errors') or [],
            })
        except (ValueError, TypeError) as exc:
            smarkets['error'] = f'{type(exc).__name__}: {exc}'[:200]
    else:
        smarkets['status'] = 'no live Smarkets evidence file present'

    per_fixture = []
    for m in targets:
        mid = str(m.get('id'))
        b = next((r for r in bo3 if str(r.get('id')) == mid), {})
        bet = b.get('bet') or {}
        two_sided = bool(bet and (bet.get('team_1') or {}).get('coeff')
                         and (bet.get('team_2') or {}).get('coeff'))
        pin_hit = [h for h in pinnacle.get('fixture_hits') or []
                   if h['fixture'] == ' vs '.join(m['teams'])]
        sm_hit = smarkets_by_id.get(mid)
        listing_pages = [p['name'] for p in pages if any(
            t in (p.get('teams_found') or []) for t in m['teams'] if t)]
        per_fixture.append({
            **m,
            'hltv_match_url': HLTV_OFFICIAL_MATCH_URLS.get(mid),
            'bo3_bound_url': (b.get('bound') or {}).get('url'),
            'bo3_bet_two_sided': two_sided,
            'bo3_bet': bet or None,
            'pinnacle_matchup': pin_hit or None,
            'smarkets_binding': sm_hit,
            'extra_pages_listing_a_team': listing_pages,
            'money_line_lead': bool(two_sided or pin_hit or (sm_hit and sm_hit.get('two_sided_quote'))),
            'verdict': (
                'NEW LEAD: two-sided relayed price found — the reviewed ladder must replay it before any pick changes'
                if two_sided else
                'EXCHANGE QUOTE OBSERVED: Smarkets lists a two-sided book (subject to <=15pp spread gate in originate.py)'
                if (sm_hit and sm_hit.get('two_sided_quote')) else
                'EXCHANGE EVENT OPEN (EMPTY BOOK): Smarkets bound via scoped alias; awaiting two-sided liquidity'
                if sm_hit else
                'LEAD ONLY: Pinnacle lists the fixture; straight-markets replay needed'
                if pin_hit else
                'No two-sided price on any surface probed; published HLTV/Valve/network research estimate stands'
            ),
        })

    doc = {
        'schema_version': 1,
        'session': 'arena-80c3b4e0',
        'observed_at': observed,
        'environment': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') else 'local checkout',
        'policy': ('Read-only research. HLTV first (identity, World Rank, rolling VRS, and roster/sub '
                   'verification only — HLTV publishes no two-sided odds), then esportsbooks and '
                   'exchanges (Smarkets with competition-scoped aliases, Pinnacle, bo3.gg/Thunderpick). '
                   'Hotspawn crowd pick shares are never used.'),
        'target_source': meta,
        'targets': targets,
        'extra_pages': pages,
        'pinnacle_guest_api': pinnacle,
        'smarkets': smarkets,
        'bo3': bo3,
        'per_fixture': per_fixture,
        'leads': [f for f in per_fixture if f['money_line_lead']],
    }
    (args.out / 'line-source-research.json').write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + '\n')

    lines = [
        '# Line-source research for fixtures without a betting line — arena-80c3b4e0',
        '',
        f'Observed {observed} ({doc["environment"]}). Targets: {len(targets)} fixtures with no '
        f'external line in snapshot {meta.get("snapshot_generated_at")} ({meta["source"]}).',
        '',
        'HLTV first, then esportsbooks and exchanges (with competition-scoped Smarkets alias binding).',
        '',
        '| Fixture | Current basis | HLTV match | bo3.gg bound | Smarkets exchange | Pinnacle | Verdict |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for f in per_fixture:
        sm = f.get('smarkets_binding')
        sm_label = (f"{sm['event_name']} ({'2-sided' if sm['two_sided_quote'] else 'empty book'})"
                    if sm else '—')
        lines.append(
            f"| {' vs '.join(f['teams'])} ({f['competition']}) | {f['current_label']} | "
            f"{f['hltv_match_url'] or '—'} | {f['bo3_bound_url'] or '—'} | {sm_label} | "
            f"{'yes' if f['pinnacle_matchup'] else 'no'} | {f['verdict']} |"
        )
    lines += [
        '',
        '## Smarkets exchange board (with competition-scoped alias binding)',
        '',
        f"Evidence: `{smarkets['evidence']}`"
        + (f" (observed {smarkets['observed_at']})" if smarkets.get('observed_at') else '')
        + (f" — {smarkets.get('fixtures_bound')} fixture(s) bound "
           f"({smarkets.get('alias_bound_count', 0)} via competition-scoped aliases), "
           f"{smarkets.get('quoted_two_sided')} with a two-sided quote."
           if 'fixtures_bound' in smarkets else f" — {smarkets.get('status') or smarkets.get('error')}"),
    ]
    for b in smarkets.get('bound_fixtures') or []:
        alias_tag = (f" [alias: {b['aliases_used'][0]['alias']} -> {b['aliases_used'][0]['canonical']}]"
                     if b.get('aliases_used') else '')
        lines.append(f"- `{b.get('hotspawn_id')}` {b.get('event_name')}{alias_tag} — {b.get('event_url')}")
    lines += [
        '',
        f"**Money-line / exchange-quote leads: {len(doc['leads'])}** of {len(targets)} target fixtures.",
    ]
    (args.out / 'line-source-research.md').write_text('\n'.join(lines) + '\n')
    print(f"leads: {len(doc['leads'])} -> {args.out / 'line-source-research.json'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
