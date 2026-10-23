"""Session arena-17d77cb3 — dated line-source research for fixtures with no betting line.

Read-only research. The user brief asks for a pick or a sourced probability for
*every* Hotspawn CS2 fixture, and for the fixtures the featured method cannot
resolve (low tier, or not listed on Polymarket/books we can read) the brief asks
for research in this order: HLTV first, then esportsbooks and esports betting
lines — plus a separate, source-linked register of what could not be resolved
and why.

This probe answers exactly that question per fixture and writes dated evidence
to ``data/research/17d77cb3/``. It never writes a probability, a pick or an
alias, and it never edits a published row:

* a fixture's *current* method is read from the live published origination
  snapshot (falling back to the checked-in one, and the source used is
  recorded), so the probe works on the same rows a reader sees;
* a "no external line" fixture is one whose published method is a research
  model (model / network / form / guidance) or that is unresolved;
* bo3.gg's public match API is queried for an *upcoming* row joining BOTH team
  names plus a start time inside ``RELAY_START_TOLERANCE_SEC``. A joined row is
  only a *lead* if it carries a ``bet_updates`` block naming a bookmaker and
  both decimal coefficients; the block is copied verbatim, never converted into
  a probability here (that is the reviewed ladder's job);
* HLTV is tried first for identity (a match URL) and never for a price: HLTV
  publishes no two-sided prematch money line;
* every other bookmaker/aggregator surface records its HTTP status only. A 200
  is not a price.

Usage: python -m scripts.17d77cb3_research [--out data/research/17d77cb3]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
HOTSPAWN_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
BO3_API = 'https://api.bo3.gg/api/v1'
BO3_HEADERS = {'Origin': 'https://bo3.gg', 'Referer': 'https://bo3.gg/',
               'Accept': 'application/json'}
LIVE_ORIGINATION = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json'
MODEL_METHODS = {'model', 'network', 'form', 'guidance', 'reference'}
RELAY_START_TOLERANCE_SEC = 60

# HLTV first (identity only), then esportsbooks and esports betting-line
# surfaces. Status codes only: an HTTP 200 landing page is not a prematch price.
PAGES = [
    ('HLTV match listing', 'https://www.hltv.org/matches'),
    ('HLTV world ranking', 'https://www.hltv.org/ranking/teams'),
    ('Thunderpick CS2', 'https://thunderpick.io/esports/counter-strike'),
    ('GG.BET CS2', 'https://gg.bet/en/counter-strike'),
    ('Stake CS2', 'https://stake.com/sports/esports/cs2'),
    ('BC.Game esports', 'https://bc.game/sports/esports'),
    ('BetBoom CS2', 'https://betboom.ru/sport/cs2'),
    ('1xBet CS2', 'https://1xbet.com/en/line/counter-strike-2'),
    ('Marathonbet CS2', 'https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/'),
    ('Betway CS2', 'https://www.betway.com/en/sports/esports/counter-strike-2'),
    ('DraftKings CS2', 'https://sportsbook.draftkings.com/leagues/esports/counter-strike-2'),
    ('OddsPortal CS2', 'https://www.oddsportal.com/esports/counter-strike/'),
    ('EGamersWorld CS2 matches', 'https://egamersworld.com/counterstrike/matches'),
    ('Pinnacle CS2', 'https://www.pinnacle.com/en/esports/counter-strike-2'),
    ('Kalshi CS2 series', 'https://api.elections.kalshi.com/trade-api/v2/series/KXCS2GAME'),
    ('Polymarket CS2 tag', 'https://gamma-api.polymarket.com/tags/slug/esports-counter-strike-2'),
]
CHALLENGE = ('just a moment', 'cf-chl', 'challenge-platform', 'attention required',
             'enable javascript and cookies', 'captcha', 'access denied')


def environment_name() -> str:
    """Where this sweep ran.

    ``scripts.build.load_no_line_research`` only promotes a sweep that ran on a
    GitHub runner (``github-actions-runner``) with a sibling Markdown record, so
    a local, possibly network-blocked probe can never replace runner-verified
    evidence. Reporting the real environment is what keeps that rule honest.
    """
    return 'github-actions-runner' if os.environ.get('GITHUB_ACTIONS') == 'true' else 'local checkout'


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def stamp(value) -> datetime | None:
    text = str(value or '').strip()
    if text.isdigit() and len(text) >= 12:  # Hotspawn milliseconds
        return datetime.fromtimestamp(int(text) / 1000, UTC)
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(UTC)
    except ValueError:
        return None


def key(name) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(name or '').casefold())


def fetch(session: requests.Session, url: str, *, method: str = 'GET', headers=None,
          json_body=None, timeout: int = 25) -> dict:
    started = iso(datetime.now(UTC))
    try:
        response = session.request(method, url, headers=headers or {'User-Agent': UA},
                                   json=json_body, timeout=timeout)
    except requests.RequestException as exc:
        return {'url': url, 'method': method, 'observed_at': started,
                'http_status': None, 'error': f'{type(exc).__name__}: {exc}'[:200]}
    body = response.text or ''
    lowered = body[:4000].lower()
    return {'url': url, 'method': method, 'observed_at': started,
            'http_status': response.status_code,
            'content_type': response.headers.get('content-type'),
            'bytes': len(body),
            'challenge_page': any(token in lowered for token in CHALLENGE)}


def hotspawn_fixtures(session) -> tuple[list, dict]:
    attempt = fetch(session, HOTSPAWN_API)
    if attempt.get('http_status') != 200:
        return [], attempt
    try:
        payload = session.get(HOTSPAWN_API, headers={'User-Agent': UA}, timeout=25).json()
    except (requests.RequestException, ValueError) as exc:
        attempt['error'] = f'{type(exc).__name__}: {exc}'[:200]
        return [], attempt
    rows = []
    for item in payload if isinstance(payload, list) else []:
        start = stamp(item.get('scheduled_start_time'))
        rows.append({'id': str(item.get('id')),
                     'teams': [item.get('participants0_name'), item.get('participants1_name')],
                     'competition': item.get('competition_name'),
                     'starts_at': iso(start) if start else None,
                     'tier': item.get('tier')})
    attempt['fixtures'] = len(rows)
    return rows, attempt


def published_methods(session, local: Path | None = None) -> tuple[dict, dict]:
    """Current published method per Hotspawn fixture id.

    A local snapshot produced by this run's own ``scripts.originate --live`` is
    preferred (it is the freshest), then the live published file.
    """
    candidates = ([('local', str(local))] if local else []) + [('live', LIVE_ORIGINATION)]
    for source, url in candidates:
        try:
            if source == 'local':
                payload = json.loads(Path(url).read_text())
                response = None
            else:
                response = session.get(url, headers={'User-Agent': UA}, timeout=25)
        except (requests.RequestException, OSError, ValueError) as exc:
            last = {'source': source, 'url': url, 'error': f'{type(exc).__name__}: {exc}'[:200]}
            continue
        if response is not None and response.status_code != 200:
            last = {'source': source, 'url': url, 'http_status': response.status_code}
            continue
        if response is not None:
            try:
                payload = response.json()
            except ValueError:
                last = {'source': source, 'url': url, 'error': 'unparseable JSON'}
                continue
        methods = {}
        for match in payload.get('matches') or []:
            origin = match.get('origination') or {}
            methods[str(match.get('hotspawn_id') or match.get('id'))] = {
                'method': origin.get('method'),
                'label': origin.get('label'),
                'featured': bool(match.get('featured_method')),
                'probability': origin.get('probability'),
                'source_url': origin.get('source_url'),
                'generated_at': payload.get('generated_at')}
        return methods, {'source': source, 'url': url, 'http_status': 200,
                         'fixtures': len(methods),
                         'generated_at': payload.get('generated_at')}
    return {}, last


def hotspawn_match_url(teams: list, competition, fixture_id: str) -> str:
    """The public Hotspawn match URL for a fixture, in Hotspawn's own slug form.

    Hotspawn's fixture feed returns no URL, so the slug is built exactly as the
    site does: lowercased team names, " vs ", competition, then the fixture id,
    with every non-alphanumeric run collapsed to one hyphen
    (observed: BC.Game -> bc-game, Stake Pulse Beat III -> stake-pulse-beat-iii).
    """
    def slug(text) -> str:
        return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', str(text or '').casefold())).strip('-')
    parts = [slug(teams[0]) if len(teams) > 0 else '', 'vs',
             slug(teams[1]) if len(teams) > 1 else '', slug(competition), str(fixture_id)]
    return 'https://www.hotspawn.com/matches/' + '-'.join(p for p in parts if p)


def bo3_upcoming(session, pages: int = 3) -> tuple[list, list]:
    rows, attempts = [], []
    for page in range(pages):
        query = (f'/matches?page[offset]={page * 100}&page[limit]=100&sort=start_date'
                 '&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1'
                 '&with=teams,tournament')
        attempt = fetch(session, BO3_API + query, headers=BO3_HEADERS)
        attempts.append(attempt)
        if attempt.get('http_status') != 200:
            break
        try:
            body = session.get(BO3_API + query, headers=BO3_HEADERS, timeout=25).json()
        except (requests.RequestException, ValueError) as exc:
            attempt['error'] = f'{type(exc).__name__}: {exc}'[:200]
            break
        chunk = body.get('results') or []
        rows.extend(chunk)
        if len(chunk) < 100:
            break
    return rows, attempts


def relay_block(row: dict) -> dict | None:
    """Verbatim copy of the bookmaker quote bo3.gg relays, or None."""
    block = row.get('bet_updates')
    if not isinstance(block, dict):
        return None
    sides = {}
    for side in ('team_1', 'team_2'):
        entry = block.get(side) or {}
        sides[side] = {'name': entry.get('name'), 'coeff': entry.get('coeff'),
                       'active': entry.get('active'), 'team_id': entry.get('team_id')}
    coeffs = [sides['team_1'].get('coeff'), sides['team_2'].get('coeff')]
    two_sided = (all(isinstance(c, (int, float)) and c > 1 for c in coeffs)
                 and sides['team_1'].get('active') is True
                 and sides['team_2'].get('active') is True)
    return {'provider': block.get('provider'), 'book_url': block.get('path'),
            'markets_count': block.get('markets_count'), 'sides': sides,
            'two_sided_price': two_sided}


def bind(teams: list, start: datetime | None, rows: list) -> tuple[dict | None, list]:
    """Exact both-name + start-window join; near misses are returned honestly."""
    wanted = {key(name) for name in teams if name}
    if len(wanted) != 2 or start is None:
        return None, []
    bound, near = None, []
    for row in rows:
        names = {(row.get('team1') or {}).get('name'), (row.get('team2') or {}).get('name')}
        row_start = stamp(row.get('start_date'))
        delta = int(abs((row_start - start).total_seconds())) if row_start else None
        if {key(n) for n in names if n} == wanted:
            if delta is not None and delta <= RELAY_START_TOLERANCE_SEC:
                bound = row
            else:
                near.append({'slug': row.get('slug'), 'teams': sorted(n for n in names if n),
                             'start': row.get('start_date'), 'start_delta_sec': delta,
                             'status': 'name match, start outside the 60s window'})
        elif {key(n) for n in names if n} & wanted and len(near) < 4:
            near.append({'slug': row.get('slug'), 'teams': sorted(n for n in names if n),
                         'start': row.get('start_date'), 'start_delta_sec': delta,
                         'status': 'one shared side only'})
    return bound, near


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/research/17d77cb3'))
    parser.add_argument('--per-fixture-delay', type=float, default=0.0)
    parser.add_argument('--origination', type=Path, default=None,
                        help='local data/origination.json from this run (preferred over the live file)')
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    observed_at = iso(datetime.now(UTC))
    fixtures, hotspawn_attempt = hotspawn_fixtures(session)
    methods, method_source = published_methods(session, args.origination)
    rows, bo3_attempts = bo3_upcoming(session)

    providers = []
    for label, url in PAGES:
        attempt = fetch(session, url)
        attempt['label'] = label
        providers.append(attempt)
        time.sleep(0.2)

    findings, unresolved = [], []
    for fixture in fixtures:
        start = stamp(fixture['starts_at'])
        published = methods.get(fixture['id']) or {}
        method = published.get('method')
        needs_research = (not published or method is None or method in MODEL_METHODS)
        if not needs_research:
            continue
        bound, near = bind(fixture['teams'], start, rows)
        quote = relay_block(bound) if bound else None
        bo3 = ({'slug': bound.get('slug'),
                'url': 'https://bo3.gg/matches/' + str(bound.get('slug')),
                'start': bound.get('start_date'),
                'start_delta_sec': int(abs((stamp(bound.get('start_date')) - start).total_seconds())),
                'tier': bound.get('tier'), 'quote': quote}
               if bound else None)
        lead = bool(quote and quote.get('two_sided_price'))
        record = {'hotspawn_id': fixture['id'], 'teams': fixture['teams'],
                  'competition': fixture['competition'], 'starts_at': fixture['starts_at'],
                  'tier': fixture['tier'], 'published_method': method,
                  'published_label': published.get('label'),
                  'published_probability': published.get('probability'),
                  'hotspawn_url': hotspawn_match_url(fixture['teams'], fixture['competition'],
                                                     fixture['id']),
                  'bo3': bo3,
                  'bo3_near_misses': near,
                  'lead': lead}
        findings.append(record)
        if not record['lead']:
            unresolved.append(record)
        if args.per_fixture_delay:
            time.sleep(args.per_fixture_delay)

    def compatible(record: dict) -> dict:
        """The published dated-research block's schema, from this probe's record.

        Keys are the ones ``scripts.build.no_line_research_block`` renders; the
        values are copied, never re-derived, and a lead stays a lead.
        """
        bo3 = record.get('bo3') or {}
        quote = bo3.get('quote') or None
        return {'id': record['hotspawn_id'], 'teams': record['teams'],
                'competition': record['competition'], 'starts_at': record['starts_at'],
                'current_method': record['published_method'],
                'current_label': record.get('published_label'),
                'hotspawn_url': record.get('hotspawn_url'),
                'bo3_bound_url': bo3.get('url'),
                'bo3_start_delta_sec': bo3.get('start_delta_sec'),
                'bo3_bet_two_sided': bool(quote and quote.get('two_sided_price')),
                'bo3_bet': ({'provider': quote.get('provider'), 'path': quote.get('book_url'),
                             'team_1': (quote.get('sides') or {}).get('team_1'),
                             'team_2': (quote.get('sides') or {}).get('team_2')}
                            if quote else None),
                'money_line_lead': record['lead'],
                'near_misses': record['bo3_near_misses'][:3],
                'verdict': ('A two-sided, active prematch bookmaker quote is published for this fixture; '
                            'it is a lead for the reviewed ladder, not a pick made here.'
                            if record['lead'] else
                            'No two-sided prematch price found on any probed surface; the research-model '
                            'pick and its limitation stand.')}

    document = {
        'session': 'arena-17d77cb3',
        'schema_version': 1,
        'environment': environment_name(),
        'purpose': ('Dated, source-linked research for Hotspawn CS2 fixtures the published ladder leaves '
                    'as a research model (no external betting line). HLTV is tried first for identity, '
                    'then bo3.gg (which relays Thunderpick prices) and the esportsbook/aggregator surfaces.'),
        'observed_at': observed_at,
        'policy': ('Evidence only. A joined bo3.gg row is a lead, not a pick: this script writes no '
                   'probability, no pick and no alias. Only a two-sided, active, prematch bookmaker quote '
                   'is recorded as a lead, copied verbatim. An HTTP 200 on a book landing page is never '
                   'treated as a price.'),
        'hotspawn_source': {'url': HOTSPAWN_API, **hotspawn_attempt},
        'published_methods_source': method_source,
        'bo3_pages': bo3_attempts,
        'counts': {'hotspawn_fixtures': len(fixtures),
                   'no_external_line': len(findings),
                   'two_sided_lead': sum(1 for f in findings if f['lead']),
                   'still_unresolved': len(unresolved),
                   'bo3_rows_fetched': len(rows)},
        'sources_tried': [{'label': p['label'], 'url': p['url'],
                           'http_status': p.get('http_status'),
                           'note': ('challenge page' if p.get('challenge_page') else
                                    p.get('error') or ('page reachable; no fixture price read'
                                                       if p.get('http_status') == 200 else 'blocked'))}
                          for p in providers],
        'providers': providers,
        'fixtures': findings,
        # Rendered by the executive summary's planned dated-research block.
        'leads': [compatible(record) for record in findings if record['lead']],
        'per_fixture': [compatible(record) for record in findings],
    }
    (args.out / 'line-source-research.json').write_text(
        json.dumps(document, indent=1, ensure_ascii=False) + '\n')

    lines = [f'# Line-source research — {observed_at}', '',
             f'Source snapshot: `{method_source.get("url")}` '
             f'(generated {method_source.get("generated_at")}); '
             f'{len(fixtures)} Hotspawn fixtures, {len(findings)} with no external line.', '',
             '| Fixture | Start (UTC) | Published method | bo3.gg join | Two-sided bookmaker price |',
             '| --- | --- | --- | --- | --- |']
    for record in findings:
        bo3 = record['bo3']
        join = (f'[{" vs ".join(record["teams"])}]({bo3["url"]}) · Δ{bo3["start_delta_sec"]}s'
                if bo3 else
                (record['bo3_near_misses'][0]['status'] if record['bo3_near_misses'] else 'not listed'))
        quote = bo3['quote'] if bo3 else None
        price = (f'{quote["provider"]} {quote["sides"]["team_1"]["coeff"]} / '
                 f'{quote["sides"]["team_2"]["coeff"]} ({quote["book_url"]})'
                 if quote and quote['two_sided_price'] else 'none published')
        lines.append(f'| {" vs ".join(record["teams"])} | {record["starts_at"]} | '
                     f'{record["published_method"] or "unresolved"} | {join} | {price} |')
    lines += ['', '## Surface status (HTTP only — a 200 is not a price)', '',
              '| Surface | Status | Note |', '| --- | --- | --- |']
    for provider in providers:
        note = ('challenge page' if provider.get('challenge_page') else
                provider.get('error') or ('ok' if provider.get('http_status') == 200 else 'blocked'))
        lines.append(f'| [{provider["label"]}]({provider["url"]}) | '
                     f'{provider.get("http_status") or "no response"} | {note} |')
    (args.out / 'line-source-research.md').write_text('\n'.join(lines) + '\n')

    summary = document['counts']
    print(f'::notice title=17d77cb3 line research::{json.dumps(summary)}')
    for record in findings:
        if record['lead']:
            print('::notice::two-sided lead ' + json.dumps(
                {'teams': record['teams'], 'start': record['starts_at'],
                 'bo3': record['bo3']['url'], 'quote': record['bo3']['quote']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
