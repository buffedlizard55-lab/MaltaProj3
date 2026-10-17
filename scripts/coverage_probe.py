"""Coverage probe for the fixtures the origination ladder leaves blank (session arena-8fa2b226).

Why this exists
---------------
Low-tier CS2 series are frequently missing from the big no-vig exchanges, so the pipeline
publishes them as *unresolved* — a blank, never a default 50/50. The brief asks for a pick for
every match, so every blank has to come with a documented reason and, where possible, a lead the
next reviewed alias can close. This module produces that dossier.

Hard rules (the same invariants the rest of the repository enforces):

* **It never writes a probability, a pick or an alias.** The strict ladder in
  ``scripts.originate`` is the only code path that can publish an estimate; the registry in
  ``data/origination/aliases.json`` is edited only by a reviewed commit with official evidence.
* Provider listings are re-tested through the production join (``pair_join``), so a lead says
  exactly why the strict match failed (name display, start time, market state) instead of
  hand-waving "no market".
* A blocked or geo-fenced endpoint is recorded as *unavailable with the provider's own error*.
  Absence of access is never reported as absence of a market, and a page that answered is never
  turned into a price here.
* ``--live`` is the only mode that touches the network, one bounded GET per provider, no retries,
  no challenge bypass, and an identifying User-Agent.

Usage
-----
    python -m scripts.coverage_probe --data data --out data/research/8fa2b226/coverage-probe.json
    python -m scripts.coverage_probe --data data --live --out /tmp/probe.json
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

UTC = timezone.utc
SCHEMA = 1
SESSION_DIR = 'data/research/8fa2b226'
POLY_CLOB_DOCS = 'https://docs.polymarket.com/api-reference/market-data/get-order-book'

# Additional public esportsbook endpoints checked *only* for reachability, never priced here.
# Each entry states what the check proves. Two providers were already recorded as unusable by the
# collector (GG.BET/Stake 403, Pinnacle/Rivalry generic redirects); the list below re-checks them
# alongside the providers the ladder has never tried, so the review page can say what was actually
# attempted at the current snapshot rather than repeating a historical note.
BOOK_CANDIDATES = [
    {'name': 'GG.BET esportsbook', 'url': 'https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike',
     'why': 'Covers many tier-B/academy series; the collector records only a failed page check today.'},
    {'name': 'Pinnacle esportsbook', 'url': 'https://www.pinnacle.com/en/esports-hub/cs2',
     'why': 'Sharp book commonly used as a closing-line reference.'},
    {'name': 'Rivalry esportsbook', 'url': 'https://api.rivalry.com/sports/public/v1/sports?sport_key=esports_cs2&lang=en&region=ca&timezone=UTC&odds_format=decimal',
     'why': 'Documented public sports API path rather than the marketing page the collector tries.'},
    {'name': 'Bovada CS2 coupon', 'url': 'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2?marketFilterId=def&preMatchOnly=true&lang=en',
     'why': 'Already an accepted ladder source; re-checked so the probe can say whether a listing exists at all.'},
    {'name': '1xBet line feed', 'url': 'https://1xbet.com/LineFeed/Get1x2_VZip?sports=71&count=25&mode=4&getEmpty=true',
     'why': 'Lists deep-tier CS2 series, but the operator geo-fences restricted countries.'},
]

TOKEN = re.compile(r'[a-z0-9]+')


def now_iso() -> str:
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def tokens(name: str) -> set:
    return {t for t in TOKEN.findall((name or '').lower()) if len(t) >= 3}


def overlap(a: str, b: str) -> float:
    """Jaccard-style token overlap between two display names; a *lead* heuristic only."""
    x, y = tokens(a), tokens(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def provider_listings(evidence_dir: Path) -> list:
    """Every provider event that could conceivably be this fixture, as saved by the collector.

    Nothing here is matched loosely for pricing — these are only *candidates* whose strict join
    verdict is then re-computed with the production matcher below.
    """
    out = []
    thunder = load(evidence_dir / 'live-thunderpick-matches.json')
    body = (thunder or {}).get('data') if isinstance(thunder, dict) else None
    rows = (body or {}).get('upcoming') or (body or {}).get('matches') or [] if isinstance(body, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        teams, market = row.get('teams') or {}, row.get('market') or {}
        names = [((market.get(side) or {}).get('name')) or ((teams.get(side) or {}).get('name')) or ''
                 for side in ('home', 'away')]
        out.append({'provider': 'Thunderpick', 'title': ' vs '.join(n or '?' for n in names), 'names': names,
                    'start_epoch': row.get('startTime'), 'url': 'https://thunderpick.io/esports/counter-strike',
                    'evidence': 'live-thunderpick-matches.json',
                    'extra': {'market_name': market.get('name'), 'market_status': market.get('status'),
                              'is_live': row.get('isLive'), 'event_id': row.get('id')},
                    'available': thunder is not None})
    bovada = load(evidence_dir / 'live-bovada-cs2.json')
    for group in (bovada or {}).get('response', []) if isinstance(bovada, dict) else []:
        for event in group.get('events', []) or []:
            names = [c.get('name') for c in event.get('competitors', []) or []]
            start = event.get('startTime')
            out.append({'provider': 'Bovada', 'title': event.get('description') or ' vs '.join(n or '?' for n in names),
                        'names': [n or '' for n in names], 'start_epoch': (start or 0) / 1000 if isinstance(start, (int, float)) else None,
                        'url': 'https://www.bovada.lv/sports/esports/counter-strike-2',
                        'evidence': 'live-bovada-cs2.json', 'available': True})
    kalshi = load(evidence_dir / 'live-kalshi-events.json')
    for page in (kalshi or {}).get('pages', []) if isinstance(kalshi, dict) else []:
        for event in (page.get('response') or {}).get('events', []) or []:
            for market in event.get('markets', []) or []:
                title = market.get('yes_sub_title') or event.get('title') or ''
                names = re.split(r'\s+(?:vs\.?|@)\s+', title)
                out.append({'provider': 'Kalshi', 'title': title, 'names': [p.strip() for p in names][:2],
                            'start_epoch': None, 'url': 'https://kalshi.com/markets/kxcs2game/counterstrike-2-game/',
                            'evidence': 'live-kalshi-events.json',
                            'extra': {'event_ticker': event.get('event_ticker'), 'market_ticker': market.get('ticker'),
                                      'status': market.get('status')},
                            'available': True})
    poly = load(evidence_dir / 'live-polymarket-observations.json')
    for event in (poly or {}).get('polymarket_events', []) if isinstance(poly, dict) else []:
        out.append({'provider': 'Polymarket', 'title': event.get('title') or '',
                    'names': list(event.get('outcomes') or []), 'start_epoch': None,
                    'url': event.get('public_page') or event.get('source_url') or 'https://polymarket.com/esports/cs2',
                    'evidence': 'live-polymarket-observations.json',
                    'extra': {'event_id': event.get('event_id'), 'book_bid': event.get('book_bid'), 'book_ask': event.get('book_ask')},
                    'available': True})
    return out


def strict_verdict(candidates: list, match: dict, registry: dict) -> list:
    """Re-run the production join for each candidate lead and keep the explanation.

    ``scripts.originate.pair_join`` is the same function the ladder uses; using it here means a
    lead reports the *real* rejection (display name, start time, uniqueness), not a second,
    weaker opinion about it.
    """
    from scripts.originate import pair_join

    leads = []
    for row in candidates:
        names = [n for n in (row.get('names') or []) if n]
        if len(names) < 2:
            continue
        score = max(overlap(names[0], match['teams'][0]['name']), overlap(names[0], match['teams'][1]['name']))
        if score <= 0:
            continue
        try:
            joined, _per_team, reason = pair_join(names, iso_from_epoch(row.get('start_epoch')), match, registry)
        except Exception as exc:  # a provider row that cannot be parsed is a limitation, not a crash
            joined, reason = None, f'candidate row unreadable by the production join: {str(exc)[:120]}'
        leads.append({'provider': row['provider'], 'title': row.get('title'), 'provider_names': names,
                      'listed_start': iso_from_epoch(row.get('start_epoch')), 'url': row.get('url'),
                      'evidence': row.get('evidence'), 'name_similarity': round(score, 3),
                      'strict_join': reason or 'matched', 'would_join': joined is not None,
                      'blocks_on': ({'names': 'display name (needs a reviewed alias)', 'time': 'listed start time',
                                     'matched': 'nothing — the strict join accepts this row'}
                                    .get(reason or 'matched', 'unreadable candidate row')),
                      'extra': row.get('extra') or {}})
    leads.sort(key=lambda x: (-x['name_similarity'], x['provider']))
    return leads[:6]


def iso_from_epoch(value):
    """Format a provider clock value with the pipeline's own normaliser (seconds or milliseconds)."""
    from scripts.domain import timestamp

    moment = timestamp(value)
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ') if moment else None


def probe_book(url: str, timeout=20) -> dict:
    """One bounded GET, recorded as reachability evidence only. Never parsed into a price."""
    import requests

    entry = {'url': url, 'method': 'GET', 'observed_at': now_iso(), 'status': 'error',
             'role': 'reachability check only — this script never turns a page into a probability'}
    try:
        response = requests.get(url, timeout=(10, timeout), allow_redirects=True,
                                headers={'User-Agent': 'HotspawnCS2CoverageProbe/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)',
                                         'Accept': 'application/json,text/html;q=0.9'})
        entry.update(http_status=response.status_code, final_url=response.url,
                     content_type=(response.headers.get('Content-Type') or '')[:80],
                     bytes=len(response.content), sha256=hashlib.sha256(response.content).hexdigest())
        entry['status'] = 'reachable' if response.status_code == 200 else 'refused'
        text = response.text[:4000].lower()
        entry['looks_like_a_fixture_list'] = bool(re.search(r'(counter-strike|cs2|counter strike)', text))
        if response.status_code == 200 and 'block' in (response.url or '').lower():
            entry['status'] = 'geo-blocked'
        if entry['status'] == 'reachable' and not entry['looks_like_a_fixture_list']:
            entry['detail'] = 'Answered, but the body is not a CS2 fixture list; nothing was extracted.'
    except Exception as exc:  # network errors are published verbatim as the source limitation
        entry['status'] = 'unavailable'
        entry['detail'] = str(exc)[:300]
    return entry


def run(data_dir: Path, *, live: bool = False, timeout: int = 20, sleep: float = 0.5) -> dict:
    latest = load(data_dir / 'latest.json') or {}
    origination = load(data_dir / 'origination.json') or {}
    registry = load(data_dir / 'origination' / 'aliases.json') or {'aliases': []}
    evidence_dir = data_dir / 'origination' / 'evidence'
    by_id = {m['id']: m for m in latest.get('matches', [])}
    candidates = provider_listings(evidence_dir)

    unresolved = [m for m in (origination.get('matches') or []) if not (m.get('origination') or {}).get('probabilities')]
    if not unresolved:  # An originated snapshot with nothing to explain still reports its state.
        unresolved = [dict(by_id.get(m['id'], m), origination=None) for m in (origination.get('matches') or [])
                      if not (m.get('origination') or {}).get('probabilities')]

    fixtures = []
    for match in unresolved:
        if by_id.get(match.get('id'), {}).get('availability') == 'past':
            continue
        trail = [{'stage': step.get('stage'), 'status': step.get('status'),
                  'detail': (step.get('detail') or '')[:400], 'source_url': step.get('source_url')}
                 for step in (match.get('research') or [])]
        leads = strict_verdict(candidates, match, registry)
        blockers = {
            'identity': any('roster' in (x.get('detail') or '').lower() or 'identity' in (x.get('detail') or '').lower() for x in trail),
            'time': any(x.get('strict_join') == 'time' for x in leads),
            'name_only': any(x.get('strict_join') == 'names' and x['name_similarity'] >= 0.5 for x in leads),
        }
        blocker = ('display-name only' if blockers['name_only'] else
                   'listed start time' if blockers['time'] else
                   'no provider listing found' if not leads else 'market state or provider gap')
        fixtures.append({
            'id': match.get('id'),
            'teams': [t.get('name') for t in match.get('teams', [])],
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'locks_at': match.get('locks_at'),
            'tier': match.get('tier'),
            'source_url': match.get('source_url'),
            'reasons': [x['detail'] for x in trail if x['status'] in ('unresolved', 'unavailable', 'rejected')] or
                       ['No ladder stage recorded for this fixture in this snapshot.'],
            'resolution_trail': trail,
            'provider_leads': leads,
            'likely_blocker': blocker,
            'alias_proposal': next(({'provider': l['provider'], 'provider_names': l['provider_names'],
                                     'hotspawn_names': [t.get('name') for t in match.get('teams', [])],
                                     'evidence_url': l['url'], 'saved_listing': l['evidence'],
                                     'listed_start': l['listed_start'], 'applied': False,
                                     'requires': 'a reviewed entry in data/origination/aliases.json with official evidence and an applies_to scope'}
                                    for l in leads if l['strict_join'] == 'names' and l['name_similarity'] >= 0.5), None),
            'blockers': blockers,
        })

    report = {
        'schema_version': SCHEMA,
        'session': 'arena-8fa2b226',
        'generated_at': now_iso(),
        'mode': 'live' if live else 'offline-evidence-only',
        # Reachability proves nothing about a book unless the reader knows where the request came from: a
        # sandbox, the CI runner and an end user get refused for different reasons.
        'environment': ('github-actions-runner' if os.environ.get('CI') == 'true'
                        else 'local checkout (not the runner: refusals here describe this machine, not the book)'),
        'source_snapshot_at': origination.get('source_snapshot_at') or latest.get('inventory_observed_at'),
        'policy': ('Dossier for fixtures the strict ladder leaves blank. It proposes nothing that is applied '
                   'automatically, records which providers were checked, and publishes the provider error text '
                   'when a source refuses access. No probability, pick or alias is written by this script.'),
        'excluded_inputs': ['Hotspawn "% picked" and offered points', 'HLTV fan votes', 'outright and map markets',
                            'any price read from a page this script fetched (reachability only)'],
        'headline': (f"{len(fixtures)} blank, live fixture(s) documented" if fixtures else
                      'No fixture in this snapshot is blank: every live row carries a sourced line.'),
        'counts': {'unresolved_fixtures': len(fixtures),
                   'with_provider_lead': sum(1 for f in fixtures if f['provider_leads']),
                   'display_name_only': sum(1 for f in fixtures if f['likely_blocker'] == 'display-name only')},
        'fixtures': fixtures,
        'book_probes': [],
        'limitations': [
            'A lead is a listing that mentions the same words; only the production join decides whether it is the fixture.',
            'geo-blocked and 403 responses prove nothing about whether a market exists for a given series.',
            'The probe runs once per pipeline refresh, so a lead can expire before it is reviewed.',
        ],
    }
    if live:
        for row in BOOK_CANDIDATES:
            result = probe_book(row['url'], timeout=timeout)
            result.update(name=row['name'], why_checked=row['why'])
            report['book_probes'].append(result)
            time.sleep(sleep)
        report['book_probe_note'] = ('Reachability only. A provider that answers is not therefore usable, and a '
                                     'provider that refuses is not therefore empty; both are published on the review page.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path(SESSION_DIR) / 'coverage-probe.json')
    parser.add_argument('--live', action='store_true', help='allow one bounded public GET per book candidate')
    parser.add_argument('--timeout', type=int, default=20)
    args = parser.parse_args()
    report = run(args.data, live=args.live, timeout=args.timeout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    counts = report['counts']
    print(f'coverage probe ({report["mode"]}): {counts["unresolved_fixtures"]} unresolved fixture(s), '
          f'{counts["with_provider_lead"]} with a provider lead, {counts["display_name_only"]} blocked by display name only')
    for row in report['book_probes']:
        print(f"::notice title=book probe {row['name']}::{row['status']} {row.get('http_status', '')}")
    for fixture in report['fixtures']:
        if fixture['alias_proposal']:
            print(f"::notice title=alias lead {fixture['id']}::{fixture['alias_proposal']['provider']} "
                  f"{fixture['alias_proposal']['provider_names']} -> {fixture['teams']} (not applied)")
    print(f'wrote {args.out}')
    return report


if __name__ == '__main__':
    main()
