"""Session arena-5fbf5cd5 - read-only live coverage probe.

Why this exists
---------------
The brief asks for a pick for *every* Hotspawn CS2 fixture and for evidence of
where each pick came from: first HLTV, then esportsbooks and betting lines. The
ladder in ``scripts.originate`` already runs those sources, but this session
needs a first-hand, dated record of what each unresolved or model-only fixture
looks like **right now**, written by the runner (the only place with egress to
Hotspawn, HLTV, bo3.gg and the books).

Hard rules
----------
* It never writes a probability, a pick or an alias. Only observations.
* Every entry records the exact URL, the UTC observation time, the HTTP status
  and a SHA-256 of the body it read, so the claim can be replayed.
* A blocked endpoint (403, timeout, geo-fence) is reported as *unavailable with
  the provider's own error*. Absence of access is never reported as absence of
  a market, and a page that answered is never turned into a price here.
* Nothing in ``data/`` is modified. The report goes to
  ``data/research/5fbf5cd5/live-<date>/coverage.json``.

Usage
-----
    python -m scripts.coverage_5fbf5cd5 --live
    python -m scripts.coverage_5fbf5cd5            # offline: report only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
SESSION = ROOT / 'data' / 'research' / '5fbf5cd5'
# The repository's own collector identifies itself with this UA and reads HLTV
# successfully from the runner. An earlier version of this probe impersonated a
# desktop browser and every HLTV request returned HTTP 403; that measured the
# probe's headers, not HLTV, so the polite identifying UA is used instead.
UA = 'HotspawnCS2Coverage/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'
FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')
LOBBY = 'https://play.hotspawn.com/lobby'
CS2_LOBBY = 'https://play.hotspawn.com/cs2-pickems'
HLTV_MATCHES = 'https://www.hltv.org/matches'
HLTV_SEARCH = 'https://www.hltv.org/search?query='
EGAMERS = 'https://egamersworld.com/counterstrike/matches'
BO3_API = 'https://api.bo3.gg/api/v1'
MONEY = {'market', 'bookmaker', 'consensus', 'reference'}


def iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def get(url: str, *, headers: dict | None = None, timeout: int = 25) -> dict:
    """One bounded GET. Every outcome is recorded, never raised."""
    base = {'User-Agent': UA, 'Accept': 'application/json,text/html;q=0.9'}
    base.update(headers or {})
    started = datetime.now(UTC)
    request = urllib.request.Request(url, headers=base)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {
                'url': url, 'status': response.status, 'observed_at': iso_now(),
                'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                'content_type': response.headers.get('Content-Type'),
                'elapsed_ms': int((datetime.now(UTC) - started).total_seconds() * 1000),
                'body': body,
            }
    except urllib.error.HTTPError as exc:
        body = b''
        try:
            body = exc.read()[:4096]
        except Exception:  # noqa: BLE001 - the status is the finding
            pass
        return {'url': url, 'status': exc.code, 'observed_at': iso_now(),
                'error': f'HTTP {exc.code}', 'bytes': len(body),
                'sha256': hashlib.sha256(body).hexdigest() if body else None,
                'elapsed_ms': int((datetime.now(UTC) - started).total_seconds() * 1000)}
    except Exception as exc:  # noqa: BLE001 - recorded, never fatal
        return {'url': url, 'status': None, 'observed_at': iso_now(),
                'error': f'{type(exc).__name__}: {exc}'[:200],
                'elapsed_ms': int((datetime.now(UTC) - started).total_seconds() * 1000)}


def key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (value or '').casefold())


def strip_body(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != 'body'}


def parse_fixtures(payload) -> list[dict]:
    """Hotspawn's fixture array. The endpoint has been seen as a bare array and
    as an object with a data key; both are accepted, anything else is recorded
    as unparsed rather than assumed."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for name in ('data', 'fixtures', 'results'):
            if isinstance(payload.get(name), list):
                return payload[name]
    return []


def active_ids(snapshot: dict, now: datetime) -> list[str]:
    out = []
    for match in snapshot.get('matches') or []:
        start = match.get('starts_at')
        parsed = None
        if isinstance(start, str):
            try:
                parsed = datetime.fromisoformat(start.replace('Z', '+00:00'))
            except ValueError:
                parsed = None
        if parsed and parsed > now:
            out.append(str(match.get('id')))
    return out


def hotspawn_start(row: dict) -> datetime | None:
    """The fixture start exactly as Hotspawn publishes it.

    The scheduled-fixture array stores epoch **milliseconds as a string** in
    ``scheduled_start_time`` (verified against the saved 2026-10-22 payload:
    15 records carried ``start_time`` too, but that field is the actual start
    used after a match has begun). The first version of this probe looked for
    ``start_date``/``starts_at`` and silently produced zero live rows; the
    fix is recorded in the session log rather than hidden.
    """
    raw = row.get('scheduled_start_time')
    if raw in (None, ''):
        return None
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None
    # 13 digits = milliseconds, 10 digits = seconds.
    seconds = value / 1000 if value > 10_000_000_000 else value
    try:
        return datetime.fromtimestamp(seconds, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def inventory_check(now: datetime, *, live: bool) -> dict:
    """Compare the published snapshot with Hotspawn's own scheduled array."""
    snapshot = json.loads((ROOT / 'data' / 'latest.json').read_text())
    published = active_ids(snapshot, now)
    report = {'published_active_ids': sorted(published),
              'published_count': len(published),
              'snapshot_generated_at': snapshot.get('generated_at')}
    if not live:
        report['skipped'] = 'offline mode: no network request made'
        return report
    response = get(FIXTURES_API)
    report['request'] = strip_body(response)
    if response.get('status') != 200 or not response.get('body'):
        report['result'] = 'unavailable'
        return report
    try:
        payload = json.loads(response['body'].decode('utf-8', 'replace'))
    except ValueError as exc:
        report['result'] = 'unparsed'
        report['error'] = str(exc)[:200]
        return report
    rows = parse_fixtures(payload)
    live_active = []
    for row in rows:
        parsed = hotspawn_start(row)
        if parsed is not None and parsed > now:
            live_active.append(str(row.get('id')))
    report.update({
        'result': 'ok',
        'api_records': len(rows),
        'api_active_ids': sorted(set(live_active)),
        'api_active_count': len(set(live_active)),
        'missing_from_site': sorted(set(live_active) - set(published)),
        'extra_on_site': sorted(set(published) - set(live_active)),
    })
    return report


def ladder_rows(origination: dict) -> list[dict]:
    rows = []
    for match in origination.get('matches') or []:
        if match.get('availability') == 'past':
            continue
        analysis = match.get('origination') or {}
        rows.append({
            'id': str(match.get('id')),
            'teams': [t.get('name') for t in match.get('teams') or []],
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'method': analysis.get('method'),
            'probabilities': analysis.get('probabilities'),
            'pick': ([t.get('name') for t in match.get('teams') or []][match['pick_index']]
                     if match.get('pick_index') is not None else None),
            'source_url': analysis.get('source_url'),
            'trail': [{'stage': r.get('stage'), 'status': r.get('status'),
                       'detail': (r.get('detail') or '')[:240],
                       'source_url': r.get('source_url')}
                      for r in match.get('research') or []],
        })
    return rows


def probe_hltv(team_names: list[str]) -> dict:
    """Identity research first, as the brief asks. Two reads: the fixture list
    and a team search. A 403 is recorded as a blocked source."""
    queries = []
    for name in team_names:
        if not name:
            continue
        queries.append({'url': HLTV_SEARCH + urllib.parse.quote(name),
                        'response': strip_body(get(HLTV_SEARCH + urllib.parse.quote(name)))})
    listing = get(HLTV_MATCHES)
    return {'listing': strip_body(listing),
            'team_searches': queries,
            'reachable': bool(listing.get('status') == 200)}


def probe_bo3(team_names: list[str]) -> dict:
    """bo3.gg relays a named bookmaker's two-way price for a bound fixture.
    The relay is recorded; nothing is converted into a probability here."""
    found = {}
    for name in team_names:
        if not name:
            continue
        query = ('/teams?page[offset]=0&page[limit]=5&filter[teams.name][eq]='
                 + urllib.parse.quote(name, safe=''))
        response = get(BO3_API + query, headers={'Origin': 'https://bo3.gg',
                                                 'Referer': 'https://bo3.gg/'})
        row = {'request': strip_body(response)}
        if response.get('status') == 200 and response.get('body'):
            try:
                results = (json.loads(response['body'].decode('utf-8', 'replace'))
                           .get('results') or [])
            except ValueError:
                results = []
            exact = [r for r in results if key(r.get('name') or '') == key(name)]
            row['exact'] = [{'id': r.get('id'), 'slug': r.get('slug'), 'rank': r.get('rank')}
                            for r in exact]
            if exact:
                match_query = ('/matches?page[offset]=0&page[limit]=10&sort=start_date'
                               '&filter[matches.status][in]=upcoming'
                               '&filter[matches.discipline_id][eq]=1'
                               f'&filter[matches.team_ids][overlap]={exact[0]["id"]}'
                               '&with=teams,tournament')
                matches_response = get(BO3_API + match_query,
                                       headers={'Origin': 'https://bo3.gg',
                                                'Referer': 'https://bo3.gg/'})
                row['matches_request'] = strip_body(matches_response)
                if matches_response.get('status') == 200 and matches_response.get('body'):
                    try:
                        payload = json.loads(matches_response['body'].decode('utf-8', 'replace'))
                    except ValueError:
                        payload = {}
                    wanted = {key(n) for n in team_names if n}
                    bound = []
                    for candidate in payload.get('results') or []:
                        names = {key((candidate.get('team1') or {}).get('name') or ''),
                                 key((candidate.get('team2') or {}).get('name') or '')}
                        if wanted != names:
                            continue
                        bet = candidate.get('bet_updates')
                        bound.append({
                            'slug': candidate.get('slug'),
                            'url': 'https://bo3.gg/matches/' + str(candidate.get('slug')),
                            'start_date': candidate.get('start_date'),
                            'relayed_provider': (bet or {}).get('provider') if isinstance(bet, dict) else None,
                            'relayed_coefficients': {side: (bet or {}).get(side, {}).get('coeff')
                                                     for side in ('team_1', 'team_2')}
                            if isinstance(bet, dict) else None,
                        })
                    row['bound_matches'] = bound
        found[name] = row
    return found


def probe_egamers(team_names: list[str]) -> dict:
    """EGamersWorld publishes a bookmaker average; the page is recorded as a
    reachability and listing observation only."""
    response = get(EGAMERS)
    out = {'index': strip_body(response), 'pairs_seen': []}
    if response.get('status') == 200 and response.get('body'):
        text = response['body'].decode('utf-8', 'replace').casefold()
        for name in team_names:
            if name:
                out['pairs_seen'].append({'team': name, 'appears': key(name) in key(text)})
    return out


MONEY = {'market', 'bookmaker', 'consensus', 'reference'}


def build_register(archive: Path) -> dict:
    """Derive the per-fixture coverage register from an archived run.

    Read-only: every value is copied from the snapshot, the origination file
    and the probe report that the same run wrote. Nothing is recomputed and
    nothing is filled in.
    """
    snapshot = json.loads((archive / 'latest.json').read_text())
    origination = json.loads((archive / 'origination.json').read_text())
    coverage = json.loads((archive / 'coverage.json').read_text())
    summary = json.loads((archive / 'summary.json').read_text()) \
        if (archive / 'summary.json').exists() else {}
    probe_rows = {f['id']: f for f in coverage.get('fixtures') or []}
    register = []
    for match in origination.get('matches') or []:
        if match.get('availability') == 'past':
            continue
        analysis = match.get('origination') or {}
        probe = probe_rows.get(str(match.get('id')), {})
        bound, priced = {}, []
        for team, info in (probe.get('bo3gg') or {}).items():
            for candidate in info.get('bound_matches') or []:
                bound[candidate.get('slug')] = candidate
        for candidate in bound.values():
            coefficients = candidate.get('relayed_coefficients') or {}
            if coefficients and all(coefficients.values()):
                priced.append({'provider': candidate.get('relayed_provider'),
                               'coefficients': coefficients, 'url': candidate.get('url')})
        names = [t.get('name') for t in match.get('teams') or []]
        pick_index = match.get('pick_index')
        register.append({
            'id': str(match.get('id')),
            'teams': names,
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'method': analysis.get('method'),
            'family': analysis.get('family'),
            'provider': analysis.get('provider'),
            'probabilities': analysis.get('probabilities'),
            'pick': names[pick_index] if pick_index is not None and pick_index < len(names) else None,
            'low_confidence': analysis.get('low_confidence'),
            'source_url': analysis.get('source_url'),
            'hltv_listing_status': (probe.get('hltv') or {}).get('listing', {}).get('status'),
            'bo3_bound_matches': len(bound),
            'bo3_relayed_price': priced,
            'ladder': [{'stage': r.get('stage'), 'status': r.get('status')}
                       for r in match.get('research') or []
                       if r.get('stage') != 'Origination result'],
        })
    register.sort(key=lambda row: (row.get('starts_at') or '', row['id']))
    return {
        'session': 'arena-5fbf5cd5',
        'archive': str(archive.as_posix()),
        'generated_at': snapshot.get('generated_at'),
        'inventory_observed_at': snapshot.get('inventory_observed_at'),
        'run_id': summary.get('run_id'),
        'commit': summary.get('commit'),
        'source': ('GitHub Actions runner: python -m scripts.collect && '
                   'python -m scripts.originate --live && '
                   'python -m scripts.coverage_5fbf5cd5 --live'),
        'inventory': coverage.get('inventory'),
        'counts': {'featured': snapshot.get('counts'),
                   'complete_ladder': origination.get('counts')},
        'method_mix': {method: sum(1 for r in register if r['method'] == method)
                       for method in sorted({r['method'] for r in register if r['method']})},
        'money_backed': sum(1 for r in register if r['method'] in MONEY),
        'fixtures': register,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='make bounded public GETs')
    parser.add_argument('--out', type=Path, default=None)
    parser.add_argument('--register', type=Path, default=None,
                        help='derive coverage-register.json from an archived run directory')
    args = parser.parse_args(argv)
    if args.register:
        target = SESSION / 'coverage-register.json'
        register = build_register(args.register)
        target.write_text(json.dumps(register, ensure_ascii=False, indent=1) + '\n')
        print(json.dumps({'path': str(target), 'fixtures': len(register['fixtures']),
                          'money_backed': register['money_backed'],
                          'inventory_missing': (register['inventory'] or {}).get('missing_from_site')},
                         indent=1))
        return 0
    now = datetime.now(UTC)
    origination = json.loads((ROOT / 'data' / 'origination.json').read_text())
    rows = ladder_rows(origination)
    report = {
        'session': 'arena-5fbf5cd5',
        'generated_at': iso_now(),
        'mode': 'live' if args.live else 'offline',
        'policy': ('Read-only observations. No probability, pick or alias is written by this probe. '
                   'A blocked source is never evidence that no market exists.'),
        'inventory': inventory_check(now, live=args.live),
        'fixtures_total': len(rows),
        'model_only_ids': [r['id'] for r in rows if r['method'] not in MONEY],
        'fixtures': [],
    }
    for row in rows:
        entry = dict(row)
        if args.live:
            teams = row['teams']
            entry['hltv'] = probe_hltv(teams)
            entry['bo3gg'] = probe_bo3(teams)
            entry['egamersworld'] = probe_egamers(teams)
        report['fixtures'].append(entry)
    out = args.out or SESSION / f"live-{now.strftime('%Y-%m-%d')}" / 'coverage.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'path': str(out), 'mode': report['mode'],
                      'fixtures': report['fixtures_total'],
                      'model_only': len(report['model_only_ids']),
                      'inventory': report['inventory'].get('result'),
                      'missing_from_site': report['inventory'].get('missing_from_site')}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
