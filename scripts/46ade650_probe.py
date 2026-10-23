"""Session arena-46ade650 — fresh line-source research for fixtures with no betting line.

Read-only research. The brief asks for a pick, or a published research estimate,
for **every** CS2 fixture Hotspawn lists, and it asks us to look outside the
featured sources (HLTV first, then esportsbooks and esports betting lines) for
the fixtures that cannot be resolved the way a featured pick is.

This module does not replace the reviewed ladder and it never writes a
probability, a pick or an alias. It records, per fixture that has no external
money line, exactly which surfaces were tried, what each one answered, and
whether a real two-sided prematch price could be read. A page answering HTTP 200
is not a price.

It builds on the runner-proven probe in ``scripts/3016b0c6_probe.py`` (same
fixture-selection rule, same word-boundary name matching, same bo3.gg and
Pinnacle guest-API scans) and adds surfaces that earlier sessions did not try:

* Rivalry, Betano, Betsson/Unibet-style sportsbooks with CS2 prematch boards,
* Oddspedia, 22bet and Bet365 esports,
* HLTV's own search endpoint (identity only — HLTV publishes no prices).

Usage: python -m scripts.46ade650_probe [--out data/research/46ade650]
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
bo3probe = importlib.import_module('scripts.bo3_odds_probe')

# Surfaces this session adds on top of the 3016 probe. Every URL is a public
# prematch board; none needs an account or a credential.
EXTRA_PAGES = [
    ('Rivalry CS2', 'https://www.rivalry.com/esports/counter-strike-2'),
    ('Betano CS2', 'https://www.betano.com/esports/counter-strike-2/'),
    ('Betsson CS2', 'https://www.betsson.com/en/sports/esports/counter-strike'),
    ('Unibet CS2', 'https://www.unibet.com/betting/sports/filter/counter_strike_2'),
    ('Oddspedia CS2', 'https://oddspedia.com/esports/counter-strike'),
    ('22bet CS2', 'https://22bet.com/line/counter-strike-2'),
    ('Bet365 esports', 'https://www.bet365.com/#/AS/B18/'),
    ('HLTV search endpoint', 'https://www.hltv.org/search?query=counter-strike'),
    ('bo3.gg matches', 'https://bo3.gg/matches'),
    ('EGamersWorld CS2 odds', 'https://egamersworld.com/counter-strike/betting'),
]


def load_targets(prefer_local: Path | None = Path('data/origination.json')) -> tuple[list[dict], dict]:
    """Fixtures with no external money line, from the freshest snapshot available.

    Inside the research workflow ``collect`` and ``originate --live`` have just
    rewritten ``data/origination.json``, so that file is newer than the
    published site; prefer it when it was generated less than six hours ago and
    fall back to the published snapshot otherwise. The source actually used is
    recorded in the report.
    """
    if prefer_local is not None and Path(prefer_local).is_file():
        try:
            doc = json.loads(Path(prefer_local).read_text())
            stamp = doc.get('generated_at') or ''
            generated = datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
            if (datetime.now(UTC) - generated).total_seconds() <= 6 * 3600:
                meta = {'source_url': str(prefer_local), 'source': 'freshly collected in this run',
                        'snapshot_generated_at': doc.get('generated_at')}
                return _select(doc, meta)
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
    return base.load_targets()


def _select(doc: dict, meta: dict) -> tuple[list[dict], dict]:
    targets = []
    for m in doc.get('matches') or []:
        if m.get('availability') == 'past':
            continue
        o = m.get('origination')
        if o is None or o.get('method') in base.MODEL_METHODS:
            targets.append({'id': m.get('id'),
                            'teams': [t.get('name') for t in m.get('teams') or []],
                            'competition': m.get('competition'),
                            'starts_at': m.get('starts_at'),
                            'current_method': (o or {}).get('method') or 'unresolved',
                            'current_label': (o or {}).get('label') or 'no pick — unresolved',
                            'hotspawn_url': m.get('source_url')})
    meta = dict(meta, targets=len(targets), active=(doc.get('counts') or {}).get('active'))
    return targets, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('data/research/46ade650'))
    ap.add_argument('--timeout', type=int, default=20)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    observed = datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')

    targets, meta = load_targets()
    teams = sorted({t for m in targets for t in m['teams'] if t})
    print(f"targets (no external betting line): {len(targets)} from {meta['source']}")

    pages = [base.probe_page(name, url, teams, timeout=args.timeout) for name, url in EXTRA_PAGES]
    teams_key = {frozenset({bo3probe.key(t) for t in m['teams'] if t}): ' vs '.join(m['teams'])
                 for m in targets}
    pinnacle = base.pinnacle_scan(teams_key)
    bo3 = base.bo3_scan(targets)

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
        per_fixture.append({
            **m,
            'bo3_bound_url': (b.get('bound') or {}).get('url'),
            'bo3_bet_two_sided': two_sided,
            'bo3_bet': bet or None,
            'pinnacle_matchup': pin_hit or None,
            'extra_pages_listing_a_team': listing_pages,
            'money_line_lead': bool(two_sided or pin_hit),
            'verdict': ('NEW LEAD: two-sided relayed price found — the reviewed ladder must replay it '
                        'before any pick changes' if two_sided else
                        'LEAD ONLY: Pinnacle lists the fixture; the series moneyline still needs a '
                        'straight-markets replay' if pin_hit else
                        'No two-sided price on any surface probed; the published research estimate and '
                        'its limitation stand'),
        })

    doc = {
        'schema_version': 1,
        'session': 'arena-46ade650',
        'observed_at': observed,
        'environment': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') else 'local checkout',
        'policy': ('Read-only research. HLTV first (identity and ranking only — HLTV publishes no '
                   'two-sided price), then esportsbooks and betting-line aggregators. Nothing here is '
                   'a probability or a pick; only a bound fixture with both sides priced is a lead.'),
        'target_source': meta,
        'targets': targets,
        'extra_pages': pages,
        'pinnacle_guest_api': pinnacle,
        'bo3': bo3,
        'per_fixture': per_fixture,
        'leads': [f for f in per_fixture if f['money_line_lead']],
    }
    (args.out / 'line-source-research.json').write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + '\n')

    lines = [f'# Line-source research for fixtures without a betting line — arena-46ade650', '',
             f'Observed {observed} ({doc["environment"]}). Targets: {len(targets)} fixtures with no '
             f'external line in snapshot {meta.get("snapshot_generated_at")} ({meta["source"]}).', '',
             'HLTV first, then esportsbooks/aggregators. A reachable page is not a price.', '',
             '| Fixture | Current basis | bo3.gg bound | Two-sided relay price | Pinnacle lists it | Verdict |',
             '| --- | --- | --- | --- | --- | --- |']
    for f in per_fixture:
        lines.append(f"| {' vs '.join(f['teams'])} ({f['competition']}) | {f['current_label']} | "
                     f"{f['bo3_bound_url'] or '—'} | {'yes' if f['bo3_bet_two_sided'] else 'no'} | "
                     f"{'yes' if f['pinnacle_matchup'] else 'no'} | {f['verdict']} |")
    lines += ['', '## Surfaces probed', '', '| Source | HTTP | Teams found | Challenge |', '| --- | --- | --- | --- |']
    for p in pages:
        lines.append(f"| {p['name']} ({p['url']}) | {p.get('status') or p.get('error', '—')} | "
                     f"{', '.join(p.get('teams_found') or []) or '—'} | "
                     f"{', '.join(p.get('challenge_markers') or []) or '—'} |")
    lines += ['', f"Pinnacle guest API: {pinnacle.get('matchups_seen')} esports matchups, "
                  f"{len(pinnacle.get('fixture_hits') or [])} target-fixture hits"
                  + (f", error: {pinnacle['error']}" if pinnacle.get('error') else ''), '',
              f"**New money-line leads: {len(doc['leads'])}** of {len(targets)} target fixtures."]
    (args.out / 'line-source-research.md').write_text('\n'.join(lines) + '\n')
    print(f"leads: {len(doc['leads'])} -> {args.out / 'line-source-research.json'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
