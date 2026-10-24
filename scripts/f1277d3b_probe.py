"""Session arena-f1277d3b — fresh line-source research for fixtures with no betting line.

Re-run after the 2026-10-23/24 publisher stall (wall-clock regression test;
runs 40028653350..40063011446) so the executive summary promotes a sweep
observed against the current lobby, not the frozen 2026-10-23 snapshot.
Adapted verbatim from scripts/103774c3_probe.py (session arena-103774c3);
only the session id, output directory and this note differ.

Read-only research. The brief asks for a pick for **every** CS2 fixture
Hotspawn lists, and for the fixtures the featured method cannot resolve — low
tier matches, or matches some books (e.g. Polymarket) do not cover — it asks us
to look outside the featured sources: HLTV first, then esportsbooks and esports
betting lines.

This module never writes a probability, a pick or an alias. For every active
fixture whose published pick rests only on a labelled research model (or that
is unresolved), it records, with the date and the source links:

* the HTTP answer of the fixture's own HLTV match page (identity only — HLTV
  publishes no two-sided price, and its fan vote is a crowd poll, never a line);
* the state of any Polymarket event that binds both exact team names (the
  market's best bid/ask copied verbatim, never converted), because some of
  these fixtures do have an event whose book was simply wider than the
  ladder's ceiling at the last refresh;
* the bo3.gg binding and any published two-sided bookmaker block, and the
  Pinnacle guest-board scan (via the runner-proven ``scripts/3016b0c6_probe``);
* what the Smarkets exchange bound and quoted during the same run's live
  collection (evidence saved by ``scripts/smarkets_lines.py``);
* the HTTP answer of the HLTV-first page surfaces earlier sessions probed
  (Rivalry, Betano, Betsson, Unibet, Oddspedia, 22bet, Bet365, EGamersWorld).

A page answering HTTP 200 is not a price. ``money_line_lead`` keeps the exact
meaning the executive-summary block (``scripts/build.py::no_line_research_block``)
renders: a bound two-sided bo3.gg relay quote, or the Pinnacle guest board
listing the fixture. Every other finding is documentation in the verdict text;
the reviewed first-party ladder re-reads the original sources on the next
four-hour refresh before any pick changes.

Usage: python -m scripts.f1277d3b_probe [--out data/research/f1277d3b]
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
base = importlib.import_module('scripts.3016b0c6_probe')
bo3probe = importlib.import_module('scripts.bo3_odds_probe')

GAMMA_CS2 = ('https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2'
             '&closed=false&limit=100&offset={offset}')
GAMMA_PAGES = 6  # bounded discovery, recorded in the report

# Surfaces probed on top of the HLTV-first list in the base probe. Every URL is
# a public prematch board; none needs an account or a credential.
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


def _hltv_url(match: dict):
    """The exact HLTV match-page URL the ladder's research trail recorded."""
    for entry in match.get('research') or []:
        url = (entry or {}).get('source_url') or ''
        stage = str((entry or {}).get('stage') or '')
        if stage.lower().startswith('hltv') and '/matches/' in url:
            return url
    return None


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
                            'hotspawn_url': m.get('source_url'),
                            'hltv_url': _hltv_url(m)})
    meta = dict(meta, targets=len(targets),
                active=(doc.get('counts') or {}).get('active'),
                snapshot_generated_at=doc.get('generated_at'))
    return targets, meta


def load_targets(prefer_local: Path | None = Path('data/origination.json')) -> tuple[list[dict], dict]:
    """Fixtures with no external money line, from the freshest snapshot available.

    The research workflow runs ``collect`` and ``originate --live`` first, so a
    fresh ``data/origination.json`` is newer than the published site; prefer it
    when less than six hours old, else fall back to the published snapshot
    (whose rows carry the same research trail). The source used is recorded.
    """
    if prefer_local is not None and Path(prefer_local).is_file():
        try:
            doc = json.loads(Path(prefer_local).read_text())
            generated = datetime.fromisoformat(str(doc.get('generated_at') or '').replace('Z', '+00:00'))
            if (datetime.now(UTC) - generated).total_seconds() <= 6 * 3600:
                return _select(doc, {'source_url': str(prefer_local),
                                      'source': 'freshly collected in this run'})
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
    try:
        doc = base.fetch_json_url(base.LIVE_ORIGINATION)
        return _select(doc, {'source_url': base.LIVE_ORIGINATION,
                              'source': 'live published snapshot'})
    except Exception as exc:  # noqa: BLE001 - recorded, fallback is explicit
        doc = json.loads(Path('data/origination.json').read_text())
        return _select(doc, {'source_url': 'data/origination.json (checked-in fallback)',
                              'source': f'live fetch failed: {type(exc).__name__}: {exc}'[:200]})


def _listed(name: str, haystack_lower: str) -> bool:
    """Same word-boundary rule as the base probe's page scan (never substrings)."""
    name = (name or '').lower()
    return len(name) >= 3 and re.search(
        r'(?<![a-z0-9])' + re.escape(name) + r'(?![a-z0-9])', haystack_lower) is not None


def polymarket_scan(targets: list[dict]) -> dict:
    """Bind each target to an open Polymarket CS2 event and copy its books verbatim.

    Discovery is the official Gamma CS2-tag feed, paginated to a terminal page
    or the recorded bound. An event binds only when its title contains BOTH
    exact team names. Market best bid/ask are copied as published; nothing is
    converted into a probability here — the featured collector re-reads the
    original CLOB order books itself on every refresh.
    """
    out = {'api': GAMMA_CS2.format(offset=0), 'pages_read': 0, 'events_seen': 0,
           'terminal_page': False, 'bindings': {}}
    events = []
    try:
        for page in range(GAMMA_PAGES):
            rows = base.fetch_json_url(GAMMA_CS2.format(offset=page * 100), timeout=30)
            if not isinstance(rows, list):
                out['error'] = 'unexpected contract: events is not a list'
                return out
            out['pages_read'] += 1
            out['events_seen'] += len(rows)
            events.extend(rows)
            if len(rows) < 100:
                out['terminal_page'] = True
                break
    except Exception as exc:  # noqa: BLE001
        out['error'] = f'{type(exc).__name__}: {exc}'[:250]
        return out
    for target in targets:
        teams = [t for t in target['teams'] if t]
        for event in events:
            title = str(event.get('title') or '')
            if len(teams) == 2 and all(_listed(t, title.lower()) for t in teams):
                markets = []
                for market in event.get('markets') or []:
                    markets.append({'question': market.get('question'),
                                    'best_bid': market.get('bestBid'),
                                    'best_ask': market.get('bestAsk'),
                                    'accepting_orders': market.get('acceptingOrders'),
                                    'active': market.get('active'),
                                    'closed': market.get('closed')})
                out['bindings'][str(target['id'])] = {
                    'event_id': event.get('id'), 'slug': event.get('slug'),
                    'title': title,
                    'url': f"https://polymarket.com/event/{event.get('slug')}",
                    'start_date': event.get('startDate'),
                    'markets': markets}
                break  # one bound event per fixture is the documented claim
    return out


def polymarket_state(binding: dict | None) -> str:
    """Mechanical description of a copied book. Prices only; no conversion."""
    if not binding:
        return 'no open Polymarket CS2 event bound both exact team names'
    priced = [m for m in binding.get('markets') or []
              if isinstance(m.get('best_bid'), (int, float))
              and isinstance(m.get('best_ask'), (int, float))]
    if not priced:
        return 'event bound, but no market carried both a numeric best bid and best ask'
    widest = max(m['best_ask'] - m['best_bid'] for m in priced)
    return (f"event bound ({binding.get('slug')}); {len(priced)} market(s) carried a two-sided "
            f"best bid/ask, widest recorded spread {widest:.2f} — the featured collector "
            're-reads the original order books each refresh and prices only books inside '
            'its published ceilings')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('data/research/f1277d3b'))
    ap.add_argument('--timeout', type=int, default=20)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    observed = datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')

    targets, meta = load_targets()
    teams = sorted({t for m in targets for t in m['teams'] if t})
    print(f"targets (no external betting line): {len(targets)} from {meta['source']}")

    pages = ([base.probe_page(n, u, teams, timeout=args.timeout) for n, u in base.PAGES]
             + [base.probe_page(n, u, teams, timeout=args.timeout) for n, u in EXTRA_PAGES])
    teams_key = {frozenset({bo3probe.key(t) for t in m['teams'] if t}): ' vs '.join(m['teams'])
                 for m in targets}
    pinnacle = base.pinnacle_scan(teams_key)
    bo3 = base.bo3_scan(targets)
    polymarket = polymarket_scan(targets)

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
        verdict = ('NEW LEAD: two-sided relayed price found — the reviewed ladder must replay it '
                   'before any pick changes' if two_sided else
                   'LEAD ONLY: Pinnacle lists the fixture; the series moneyline still needs a '
                   'straight-markets replay' if pin_hit else
                   'No two-sided price on any surface probed; the published research estimate and '
                   'its limitation stand')
        per_fixture.append({
            **m,
            'hltv_page': hltv_page,
            'polymarket_book': polymarket['bindings'].get(str(m['id'])),
            'polymarket_state': poly,
            'bo3_bound_url': (b.get('bound') or {}).get('url'),
            'bo3_bet_two_sided': two_sided,
            'bo3_bet': bet or None,
            'pinnacle_matchup': pin_hit or None,
            'extra_pages_listing_a_team': listing_pages,
            'money_line_lead': lead,
            'verdict': f'{verdict}. Polymarket: {poly}.',
        })

    # The live collection in this workflow also queries the Smarkets exchange
    # board (scripts/smarkets_lines.py). Record exactly what it bound and quoted
    # so a reviewer can see whether that rung priced any of these fixtures.
    smarkets = {'evidence': 'data/origination/evidence/live-smarkets-cs.json'}
    smarkets_path = Path('data/origination/evidence/live-smarkets-cs.json')
    if smarkets_path.exists():
        try:
            saved = json.loads(smarkets_path.read_text())
            binds = saved.get('bindings') or []
            rows = importlib.import_module('scripts.smarkets_lines').rows(
                Path('data/origination/evidence'))
            smarkets.update({
                'observed_at': saved.get('observed_at'),
                'events_listed': len(saved.get('events') or []),
                'fixtures_bound': len(binds),
                'quoted_two_sided': len(rows),
                'bound_fixtures': [{'hotspawn_id': b.get('hotspawn_id'), 'event_id': b.get('event_id'),
                                    'event_name': b.get('event_name'), 'event_url': b.get('event_url')}
                                   for b in binds],
                'target_bindings': [b.get('hotspawn_id') for b in binds
                                    if str(b.get('hotspawn_id')) in {str(t['id']) for t in targets}],
                'errors': saved.get('errors') or [],
            })
        except (ValueError, TypeError) as exc:
            smarkets['error'] = f'{type(exc).__name__}: {exc}'[:200]
    else:
        smarkets['status'] = 'the live collection produced no Smarkets evidence file'

    doc = {
        'schema_version': 1,
        'session': 'arena-f1277d3b',
        'observed_at': observed,
        'environment': 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') else 'local checkout',
        'policy': ('Read-only research. HLTV first (identity and ranking only — HLTV publishes no '
                   'two-sided price and its fan vote is a crowd poll), then esportsbooks, exchanges '
                   'and betting-line aggregators. Nothing here is a probability or a pick; only a '
                   'bound fixture with both sides priced is a lead.'),
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
        json.dumps(doc, indent=2, ensure_ascii=False) + '\n')

    lines = ['# Line-source research for fixtures without a betting line — arena-f1277d3b', '',
             f'Observed {observed} ({doc["environment"]}). Targets: {len(targets)} fixtures with no '
             f'external line in snapshot {meta.get("snapshot_generated_at")} ({meta["source"]}).', '',
             'HLTV first, then esportsbooks/exchanges/aggregators. A reachable page is not a price.', '',
             '| Fixture | Current basis | HLTV page | Polymarket | bo3.gg bound | Two-sided relay price | Pinnacle lists it | Verdict |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for f in per_fixture:
        hp = f.get('hltv_page') or {}
        hltv_cell = (f"{hp.get('status') or hp.get('error', '—')} ({f['hltv_url']})"
                     if f.get('hltv_url') else 'no HLTV URL in the research trail')
        lines.append(f"| {' vs '.join(f['teams'])} ({f['competition']}) | {f['current_label']} | "
                     f"{hltv_cell} | {f['polymarket_state']} | {f['bo3_bound_url'] or '—'} | "
                     f"{'yes' if f['bo3_bet_two_sided'] else 'no'} | "
                     f"{'yes' if f['pinnacle_matchup'] else 'no'} | {f['verdict']} |")
    lines += ['', '## Surfaces probed (HLTV first)', '', '| Source | HTTP | Teams found | Challenge |',
              '| --- | --- | --- | --- |']
    for p in pages:
        lines.append(f"| {p['name']} ({p['url']}) | {p.get('status') or p.get('error', '—')} | "
                     f"{', '.join(p.get('teams_found') or []) or '—'} | "
                     f"{', '.join(p.get('challenge_markers') or []) or '—'} |")
    lines += ['', '## Polymarket Gamma CS2 feed', '',
              f"{polymarket.get('events_seen')} open CS2 events over {polymarket.get('pages_read')} "
              f"page(s) (terminal page: {polymarket.get('terminal_page')}); "
              f"{len(polymarket.get('bindings') or {})} target fixture(s) bound both exact names."
              + (f" Error: {polymarket['error']}" if polymarket.get('error') else '')]
    for fid, binding in (polymarket.get('bindings') or {}).items():
        lines.append(f"- `{fid}` {binding.get('title')} — {binding.get('url')}")
    lines += ['', '## Smarkets exchange board', '',
              f"Evidence: `{smarkets['evidence']}`"
              + (f" (observed {smarkets['observed_at']})" if smarkets.get('observed_at') else '')
              + (f" — {smarkets.get('fixtures_bound')} fixture(s) bound, "
                 f"{smarkets.get('quoted_two_sided')} with a two-sided quote; "
                 f"target fixtures bound: {smarkets.get('target_bindings') or 'none'}."
                 if 'fixtures_bound' in smarkets
                 else f" — {smarkets.get('status') or smarkets.get('error')}")]
    lines += ['', f"Pinnacle guest API: {pinnacle.get('matchups_seen')} esports matchups, "
                  f"{len(pinnacle.get('fixture_hits') or [])} target-fixture hits"
                  + (f", error: {pinnacle['error']}" if pinnacle.get('error') else ''), '',
              f"**New money-line leads: {len(doc['leads'])}** of {len(targets)} target fixtures."]
    (args.out / 'line-source-research.md').write_text('\n'.join(lines) + '\n')
    print(f"leads: {len(doc['leads'])} -> {args.out / 'line-source-research.json'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
