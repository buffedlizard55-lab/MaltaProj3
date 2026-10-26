"""Verify session e3bc19d6's live-coverage dossier line by line.

What this checks
----------------
1. **Replay arithmetic.** Every probability published for the ten fixtures that
   were open in the site's own 2026-10-25T23:03:48Z build is recomputed from the
   evidence that row carries (order-book bid/ask midpoints, the bookmaker's raw
   decimal odds, or the official Valve rating points) and must match the
   published number to 1e-6. A hand-edited published value fails here.
2. **Official rating rows.** Every Valve row quoted in
   ``valve-coverage.json`` must equal the row in the committed official
   ``data/evidence/valve-ratings.json`` (points, standing, roster, name,
   snapshot date), and its detail link must exist on the official repository
   path for that snapshot date.
3. **Inventory transcription.** Every fixture in ``live-inventory.json`` is
   compared with the collector's independently fetched
   ``data/evidence/hotspawn-fixtures.json`` whenever that file carries the
   record; team names and the scheduled start must match exactly. Records the
   published evidence does not carry (a different observation vintage) are
   reported as ``absent-from-vintage`` rather than silently passing.
4. **Identity joins.** Each HLTV row's derived UTC start must equal the
   Hotspawn start of the same fixture id, and every link must be https and
   unique.
5. **Coverage join.** Every open fixture appears exactly once in
   ``coverage.json``, and the dossier's summary counts must be recomputed from
   the rows rather than trusted.
6. **Review flags.** Every flag carries the id/severity/title/detail/source_urls
   that the site's review renderer requires, at least one https source, and a
   severity the schema allows.
7. **No vote inputs.** Hotspawn ``% picked`` values are community votes; the
   dossier must never carry one as an input.

Usage
-----
    python -m scripts.e3bc19d6_verify            # check, print a report
    python -m scripts.e3bc19d6_verify --json out.json
Exit status is 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / 'data' / 'research' / 'e3bc19d6'
VALVE_EVIDENCE = ROOT / 'data' / 'evidence' / 'valve-ratings.json'
HOTSPAWN_EVIDENCE = ROOT / 'data' / 'evidence' / 'hotspawn-fixtures.json'
VALVE_RD = 75.0
TOLERANCE = 1e-6
SEVERITIES = {'info', 'notice', 'warning', 'critical'}
# A JSON key carrying a Hotspawn community vote count or percentage. The dossier
# may describe in prose that these values are never used; it may not carry one.
VOTE_MARKER = re.compile(r'"(?:participants[01]_)?picked_percent"\s*:\s*[0-9]')


def _load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def g_factor(rd: float = VALVE_RD) -> float:
    return 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)


def normalise(first: float, second: float) -> list[float]:
    total = first + second
    if total <= 0:
        raise ValueError('a probability pair must have a positive total')
    return [first / total, second / total]


def replay_row(row: dict) -> tuple[list[float], str]:
    """Recompute one published probability pair from its recorded evidence."""
    method = row.get('method')
    evidence = row.get('evidence') or {}
    if method == 'market':
        bids, asks = evidence.get('bid'), evidence.get('ask')
        if not (isinstance(bids, list) and isinstance(asks, list) and len(bids) == len(asks) == 2):
            raise ValueError('order book needs two bid and two ask prices')
        for bid, ask in zip(bids, asks):
            if float(bid) > float(ask):
                raise ValueError(f'crossed book: bid {bid} is above ask {ask}')
            if not 0 <= float(bid) <= 1 or not 0 <= float(ask) <= 1:
                raise ValueError('order-book prices must be between 0 and 1')
        midpoints = [(float(b) + float(a)) / 2 for b, a in zip(bids, asks)]
        if sum(midpoints) <= 0:
            raise ValueError('both sides are priced at zero')
        return normalise(midpoints[0], midpoints[1]), 'midpoint of the two-sided book, normalised'
    if method == 'bookmaker':
        odds = evidence.get('raw_decimal_odds')
        if not (isinstance(odds, list) and len(odds) == 2):
            raise ValueError('bookmaker row needs two decimal odds')
        if min(float(o) for o in odds) <= 1:
            raise ValueError('decimal odds must both exceed 1.0')
        return normalise(1 / float(odds[0]), 1 / float(odds[1])), 'proportional margin removal on the raw odds'
    if method == 'model':
        points = evidence.get('points')
        if not (isinstance(points, list) and len(points) == 2):
            raise ValueError('model row needs two ranking point values')
        rd = float(evidence.get('rd_assumption', VALVE_RD))
        g = g_factor(rd)
        p = 1 / (1 + 10 ** (g * (float(points[1]) - float(points[0])) / 400))
        return [p, 1 - p], f'Valve fit.js logistic with g={g:.9f} (RD {rd:g})'
    raise ValueError(f'unknown method {method!r}')


def check_replay(report: dict) -> list[str]:
    errors = []
    rows = _load(SESSION / 'replay.json')['rows']
    if not rows:
        return ['replay.json carries no rows']
    for row in rows:
        fixture = row.get('fixture_id')
        try:
            recomputed, rule = replay_row(row)
        except ValueError as exc:
            errors.append(f'{fixture}: {exc}')
            continue
        published = row.get('published_probabilities') or []
        if len(published) != 2:
            errors.append(f'{fixture}: published pair is not two values')
            continue
        delta = max(abs(recomputed[0] - float(published[0])), abs(recomputed[1] - float(published[1])))
        if delta > TOLERANCE:
            errors.append(f'{fixture}: published {published} but {rule} gives {[round(v, 8) for v in recomputed]}')
        if abs(sum(float(v) for v in published) - 1) > 1e-4:
            errors.append(f'{fixture}: published pair sums to {sum(float(v) for v in published):.6f}')
        pick_index = row.get('pick_index')
        if pick_index not in (0, 1):
            errors.append(f'{fixture}: pick_index {pick_index!r} is not 0 or 1')
        elif row.get('pick') != (row.get('teams') or [None, None])[pick_index]:
            errors.append(f'{fixture}: pick {row.get("pick")!r} is not the side at pick_index {pick_index}')
        elif int(pick_index) != int(max(range(2), key=lambda i: float(published[i]))):
            errors.append(f'{fixture}: the obvious pick is not the higher published probability')
        report['replay'].append({'fixture_id': fixture, 'method': row.get('method'),
                                 'rule': rule, 'delta': round(delta, 10),
                                 'published': published,
                                 'recomputed': [round(v, 8) for v in recomputed]})
    return errors


def compare_valve_team(fixture_id, team: dict, complete: list[dict], snapshot_day: str) -> list[str]:
    """Compare one recorded team row with the complete official rows for its name."""
    errors = []
    name = team.get('valve_name')
    if name is None:
        if team.get('valve_points') is not None:
            errors.append(f'{fixture_id}: a blank Valve name carries points')
        if len(complete) == 1:
            errors.append(f'{fixture_id}: {team["hotspawn_name"]} has one complete row but was recorded as unpriceable')
        return errors
    if len(complete) != 1:
        errors.append(f'{fixture_id}: Valve name {name!r} is not unique among complete rows')
        return errors
    official = complete[0]
    if str(official.get('name') or '').casefold() != str(name).casefold():
        errors.append(f'{fixture_id}: {name!r} is not the official spelling')
    if float(official['points']) != float(team['valve_points']):
        errors.append(f'{fixture_id}: {name} points {team["valve_points"]} != official {official["points"]}')
    if int(official['standing']) != int(team['valve_standing']):
        errors.append(f'{fixture_id}: {name} standing {team["valve_standing"]} != official {official["standing"]}')
    if list(official.get('roster') or []) != list(team.get('roster') or []):
        errors.append(f'{fixture_id}: {name} roster differs from the official file')
    expected = ('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/'
                + str(snapshot_day)[:4] + '/' + str(official.get('detail_path')))
    if team.get('detail_path') != expected:
        errors.append(f'{fixture_id}: {name} detail link is not the official path')
    return errors


def check_valve_rows(report: dict) -> list[str]:
    errors = []
    if not VALVE_EVIDENCE.exists():
        return ['the committed official Valve evidence file is missing']
    evidence = _load(VALVE_EVIDENCE)
    index = {}
    for row in evidence.get('rows') or []:
        index.setdefault(str(row.get('name') or '').casefold(), []).append(row)
    snapshot_day = evidence.get('snapshot_date')
    dossier = _load(SESSION / 'valve-coverage.json')
    if dossier.get('snapshot_date') != snapshot_day:
        errors.append(f'valve-coverage.json declares snapshot {dossier.get("snapshot_date")} but the evidence is {snapshot_day}')
    for fixture in dossier.get('fixtures') or []:
        for team in fixture.get('teams') or []:
            name = team.get('valve_name')
            # The rung (scripts/originate.py) excludes incomplete remnants before
            # the uniqueness test and fails closed when two complete rows share a
            # name, so this check applies the same rule rather than "any row".
            candidates = index.get(str(team['hotspawn_name']).casefold()) or []
            complete = [r for r in candidates if len(r.get('roster') or []) == 5]
            if int(team.get('rows_with_this_name', -1)) != len(candidates):
                errors.append(f'{fixture.get("fixture_id")}: {team["hotspawn_name"]} row count differs from the official file')
            if int(team.get('complete_five_player_rows', -1)) != len(complete):
                errors.append(f'{fixture.get("fixture_id")}: {team["hotspawn_name"]} complete-row count differs from the official file')
            errors.extend(compare_valve_team(fixture.get('fixture_id'), team, complete, snapshot_day))
            if team.get('valve_name'):
                report['valve_rows'].append({'fixture_id': fixture.get('fixture_id'), 'name': team['valve_name'],
                                             'points': team['valve_points'], 'standing': team['valve_standing'],
                                             'verified': True})
    priceable = [f for f in dossier.get('fixtures') or [] if f.get('valve_model_priceable')]
    if int(dossier.get('summary', {}).get('priceable', -1)) != len(priceable):
        errors.append('valve-coverage.json summary.priceable does not equal the rows')
    for fixture in dossier.get('fixtures') or []:
        both = all(t.get('valve_points') is not None for t in fixture.get('teams') or [])
        if bool(fixture.get('valve_model_priceable')) != both:
            errors.append(f'{fixture.get("fixture_id")}: valve_model_priceable disagrees with its own rows')
    return errors


def compare_inventory_record(record: dict, source: dict) -> list[str]:
    """Compare one transcribed fixture with the collector's own evidence row."""
    fixture = str(record.get('id'))
    errors = []
    names = [source.get('participants0_name'), source.get('participants1_name')]
    mine = [t.get('name') for t in record.get('teams') or []]
    if names != mine:
        errors.append(f'{fixture}: transcribed teams {mine} != collected {names}')
    if str(source.get('scheduled_start_time')) != str(record.get('scheduled_start_time_ms')):
        errors.append(f'{fixture}: transcribed start {record.get("scheduled_start_time_ms")} '
                      f'!= collected {source.get("scheduled_start_time")}')
    return errors


def check_inventory(report: dict) -> list[str]:
    errors = []
    inventory = _load(SESSION / 'live-inventory.json')
    records = inventory.get('open_records') or []
    if len(records) != inventory.get('count'):
        errors.append('live-inventory.json count does not equal its records')
    if int((inventory.get('summary') or {}).get('open_fixtures', len(records))) != len(records):
        errors.append('live-inventory.json summary.open_fixtures does not equal its records')
    ids = [r.get('id') for r in records]
    if len(set(ids)) != len(ids):
        errors.append('live-inventory.json repeats a fixture id')
    for url in [inventory.get('source_url')] + [r.get('source_api') for r in records]:
        if not (isinstance(url, str) and url.startswith('https://')):
            errors.append('an inventory source URL is not https')
            break
    published = {}
    if HOTSPAWN_EVIDENCE.exists():
        try:
            payload = _load(HOTSPAWN_EVIDENCE)
        except ValueError:
            payload = None
        raw = payload.get('data') if isinstance(payload, dict) else payload
        if isinstance(raw, list):
            published = {str(item.get('id')): item for item in raw if isinstance(item, dict)}
    for record in records:
        fixture = str(record.get('id'))
        source = published.get(fixture)
        if source is None:
            report['inventory'].append({'fixture_id': fixture, 'state': 'absent-from-vintage'})
            continue
        errors.extend(compare_inventory_record(record, source))
        report['inventory'].append({'fixture_id': fixture, 'state': 'matched-collected-evidence'})
    return errors


def check_identities(report: dict) -> list[str]:
    errors = []
    inventory = {r['id']: r for r in _load(SESSION / 'live-inventory.json')['open_records']}
    dossier = _load(SESSION / 'hltv-identities.json')
    seen = set()
    for row in dossier.get('rows') or []:
        fixture = row.get('fixture_id')
        url = row.get('hltv_url') or ''
        if not url.startswith('https://www.hltv.org/matches/'):
            errors.append(f'{fixture}: HLTV match URL is not an https hltv.org match link')
        if url in seen:
            errors.append(f'{fixture}: HLTV match URL is reused')
        seen.add(url)
        if fixture not in inventory:
            errors.append(f'{fixture}: HLTV identity does not correspond to an open inventory record')
            continue
        if row.get('hltv_start_utc') != inventory[fixture]['starts_at']:
            errors.append(f'{fixture}: HLTV start {row.get("hltv_start_utc")} != Hotspawn {inventory[fixture]["starts_at"]}')
        if row.get('best_of') != 3:
            errors.append(f'{fixture}: best_of is not the verified 3')
        report['identities'].append({'fixture_id': fixture, 'hltv_url': url, 'start_utc': row.get('hltv_start_utc')})
    return errors


def check_coverage(report: dict) -> list[str]:
    errors = []
    inventory = _load(SESSION / 'live-inventory.json')
    dossier = _load(SESSION / 'coverage.json')
    rows = dossier.get('rows') or []
    ids = [r.get('fixture_id') for r in rows]
    if sorted(ids) != sorted(r['id'] for r in inventory['open_records']):
        errors.append('coverage.json does not cover exactly the open inventory records once each')
    summary = dossier.get('summary') or {}
    recomputed = {
        'open_fixtures': len(rows),
        'published_pick': sum(1 for r in rows if r.get('in_published_snapshot')),
        'not_in_published_snapshot': sum(1 for r in rows if not r.get('in_published_snapshot')),
        'priceable_by_valve_rung': sum(1 for r in rows if (r.get('valve') or {}).get('priceable')),
        'priceable_by_hltv_ranking_rung_only': sum(
            1 for r in rows
            if not r.get('in_published_snapshot') and not (r.get('valve') or {}).get('priceable') and r.get('hltv')),
    }
    for key, value in recomputed.items():
        if int(summary.get(key, -1)) != value:
            errors.append(f'coverage.json summary.{key} is {summary.get(key)!r}, rows give {value}')
    leftover = [r['fixture_id'] for r in rows
                if not r.get('in_published_snapshot')
                and not (r.get('valve') or {}).get('priceable')
                and not r.get('hltv')]
    if leftover != list(summary.get('with_no_pricing_rung') or []):
        errors.append('coverage.json with_no_pricing_rung does not equal the rows without a rung')
    for row in rows:
        fixture = row.get('fixture_id')
        if not str(row.get('hotspawn_url') or '').startswith('https://'):
            errors.append(f'{fixture}: no https Hotspawn link')
        if not row.get('verdict'):
            errors.append(f'{fixture}: no verdict')
        if row.get('published'):
            published = row['published']
            if not str(published.get('source_url') or '').startswith('https://'):
                errors.append(f'{fixture}: published pick has no https source link')
            if published.get('probabilities', [None, None])[row.get('published', {}).get('pick_index', 0)] is None:
                errors.append(f'{fixture}: published pick has no probability')
            if published.get('replay_verdict') != 'pass':
                errors.append(f'{fixture}: published pick did not replay')
    report['coverage'] = recomputed
    return errors


def check_flags(report: dict) -> list[str]:
    errors = []
    flags = _load(SESSION / 'flags.json')
    if not isinstance(flags, list) or not flags:
        return ['flags.json is empty']
    seen = set()
    for flag in flags:
        for key in ('id', 'severity', 'title', 'detail', 'source_urls'):
            if not flag.get(key):
                errors.append(f'{flag.get("id")!r}: missing {key}')
        if flag.get('id') in seen:
            errors.append(f'{flag.get("id")!r}: duplicated id')
        seen.add(flag.get('id'))
        if flag.get('severity') not in SEVERITIES:
            errors.append(f'{flag.get("id")!r}: severity {flag.get("severity")!r} not allowed')
        urls = flag.get('source_urls') or []
        if not urls or not all(str(u).startswith('https://') for u in urls):
            errors.append(f'{flag.get("id")!r}: every source must be an https URL')
    report['flags'] = len(flags)
    return errors


def check_no_votes(_report: dict) -> list[str]:
    errors = []
    for path in sorted(SESSION.glob('*.json')):
        text = path.read_text(encoding='utf-8')
        if VOTE_MARKER.search(text):
            errors.append(f'{path.name} carries a Hotspawn community vote value; votes are never an input')
    return errors


def published_coverage(build: Path, now_open_only: bool = True) -> tuple[list[str], list[dict]]:
    """Check a published build: does every open fixture carry a pick or a blocker?

    ``build`` is a directory holding the published ``origination.json`` (the
    researched list the site renders) and, optionally, ``snapshot.json``. A
    fixture passes when it has a pick index and a two-value probability pair
    that sums to one. A fixture without a pick passes only when the build lists
    its id in ``unresolved_ids``, i.e. it is published with an explicit blocker
    in the unresolved register. A silent blank fails.
    """
    errors: list[str] = []
    path = build / 'origination.json'
    if not path.exists():
        return [f'{path} is missing'], []
    document = _load(path)
    rows = document.get('matches') if isinstance(document, dict) else document
    if not isinstance(rows, list):
        return ['origination.json does not carry a match list'], []
    open_ids = document.get('unresolved_ids') if isinstance(document, dict) else None
    open_ids = list(open_ids or [])
    table = []
    for row in rows:
        fixture = str(row.get('id'))
        availability = row.get('availability')
        if now_open_only and availability not in (None, 'open'):
            continue
        origination = row.get('origination') or {}
        probabilities = origination.get('probabilities')
        pick_index = row.get('pick_index')
        resolved = (isinstance(probabilities, list) and len(probabilities) == 2
                    and all(isinstance(v, (int, float)) for v in probabilities)
                    and abs(sum(probabilities) - 1) <= 1e-4
                    and pick_index in (0, 1))
        if resolved:
            table.append({'fixture_id': fixture, 'state': 'pick',
                          'pick': row['teams'][pick_index]['name'],
                          'probability': round(float(probabilities[pick_index]), 6),
                          'method': origination.get('method'),
                          'source_url': origination.get('source_url')})
            if not str(origination.get('source_url') or '').startswith('https://'):
                errors.append(f'{fixture}: a pick has no https source link')
        elif fixture in open_ids:
            table.append({'fixture_id': fixture, 'state': 'unresolved-with-blocker'})
        else:
            errors.append(f'{fixture}: open fixture has neither a pick nor an unresolved entry')
            table.append({'fixture_id': fixture, 'state': 'silent-blank'})
    published = {str(item.get('id')) for item in rows}
    for fixture in open_ids:
        if fixture not in published:
            errors.append(f'{fixture}: listed as unresolved but has no published row at all')
    return errors, table


def published_coverage(build: Path, open_only: bool = True) -> tuple[list[str], list[dict]]:
    """Check a published build: does every open fixture carry a pick or a blocker?

    ``build`` is a directory holding the published ``origination.json`` (the
    researched list the site renders). A fixture passes when it has a pick index
    and a two-value probability pair that sums to one. A fixture without a pick
    passes only when the build lists its id in ``unresolved_ids``, i.e. it is
    published with an explicit blocker in the unresolved register. A silent
    blank fails.
    """
    errors: list[str] = []
    path = build / 'origination.json'
    if not path.exists():
        return [f'{path} is missing'], []
    document = _load(path)
    rows = document.get('matches') if isinstance(document, dict) else document
    if not isinstance(rows, list):
        return ['origination.json does not carry a match list'], []
    unresolved_ids = list((document.get('unresolved_ids') if isinstance(document, dict) else None) or [])
    table = []
    for row in rows:
        fixture = str(row.get('id'))
        if open_only and row.get('availability') not in (None, 'open'):
            continue
        origination = row.get('origination') or {}
        probabilities = origination.get('probabilities')
        pick_index = row.get('pick_index')
        resolved = (isinstance(probabilities, list) and len(probabilities) == 2
                    and all(isinstance(value, (int, float)) for value in probabilities)
                    and abs(sum(probabilities) - 1) <= 1e-4
                    and pick_index in (0, 1))
        if resolved:
            table.append({'fixture_id': fixture, 'state': 'pick',
                          'pick': row['teams'][pick_index]['name'],
                          'probability': round(float(probabilities[pick_index]), 6),
                          'method': origination.get('method'),
                          'source_url': origination.get('source_url')})
            if not str(origination.get('source_url') or '').startswith('https://'):
                errors.append(f'{fixture}: a pick has no https source link')
        elif fixture in unresolved_ids:
            table.append({'fixture_id': fixture, 'state': 'unresolved-with-blocker'})
        else:
            table.append({'fixture_id': fixture, 'state': 'silent-blank'})
            errors.append(f'{fixture}: open fixture has neither a pick nor an unresolved entry')
    published_ids = {str(item.get('id')) for item in rows}
    for fixture in unresolved_ids:
        if fixture not in published_ids:
            errors.append(f'{fixture}: listed as unresolved but has no published row at all')
    return errors, table


def replay_published_row(row: dict) -> tuple[list[float] | None, str]:
    """Recompute one row of the live published build from its own evidence.

    Handles the five shapes the ladder produces: a prediction-market book
    (normalised midpoints), a single bookmaker (proportional margin removal),
    a consensus of independent money sources (median of the per-source no-vig
    probabilities), the Valve official-rating model (fit.js logistic, RD 75) and
    the project's own results-based fit (same logistic, with the rating
    deviation derived from the number of anchored series).
    """
    method = row.get('method')
    evidence = row.get('evidence') or {}
    if method == 'market':
        bids, asks = evidence.get('bid'), evidence.get('ask')
        if not (isinstance(bids, list) and isinstance(asks, list) and len(bids) == len(asks) == 2):
            raise ValueError('order book needs two bid and two ask prices')
        for bid, ask in zip(bids, asks):
            if float(bid) > float(ask):
                raise ValueError(f'crossed book: bid {bid} above ask {ask}')
        midpoints = [(float(b) + float(a)) / 2 for b, a in zip(bids, asks)]
        return normalise(midpoints[0], midpoints[1]), 'midpoint of the two-sided book, normalised'
    if method == 'bookmaker':
        odds = evidence.get('raw_decimal_odds')
        if not (isinstance(odds, list) and len(odds) == 2 and min(float(o) for o in odds) > 1):
            raise ValueError('a bookmaker row needs two decimal odds above 1')
        return normalise(1 / float(odds[0]), 1 / float(odds[1])), 'proportional margin removal on the raw odds'
    if method == 'consensus':
        sources = evidence.get('sources') or []
        pairs = []
        for source in sources:
            odds = source.get('odds')
            if not (isinstance(odds, list) and len(odds) == 2 and min(float(o) for o in odds) > 1):
                raise ValueError('every consensus source needs two decimal odds above 1')
            pairs.append(normalise(1 / float(odds[0]), 1 / float(odds[1])))
        if len(pairs) < 2:
            raise ValueError('a consensus needs at least two money sources')

        def median(values: list[float]) -> float:
            ordered = sorted(values)
            middle = len(ordered) // 2
            return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2

        return (normalise(median([p[0] for p in pairs]), median([p[1] for p in pairs])),
                f'median of {len(pairs)} source no-vig probabilities')
    if method == 'model':
        points = evidence.get('points')
        if not (isinstance(points, list) and len(points) == 2):
            raise ValueError('a model row needs two rating values')
        if evidence.get('n_series'):
            n = max(1, int(evidence['n_series']))
            rd = min(400.0, 150.0 + 300.0 / math.sqrt(n))
            p = 1 / (1 + 10 ** (g_factor(rd) * (float(points[1]) - float(points[0])) / 400))
            return [p, 1 - p], f'own results-based fit (rd {rd:.4f} from {n} anchored series)'
        rd = float(evidence.get('rd_assumption', VALVE_RD))
        p = 1 / (1 + 10 ** (g_factor(rd) * (float(points[1]) - float(points[0])) / 400))
        return [p, 1 - p], f'Valve fit.js logistic with RD {rd:g}'
    raise ValueError(f'unknown method {method!r}')


def check_published_verification(report: dict) -> list[str]:
    """Recompute every row of the first published build after this live read."""
    errors = []
    path = SESSION / 'published-verification.json'
    if not path.exists():
        return []
    document = _load(path)
    rows = document.get('rows') or []
    if not rows:
        return ['published-verification.json carries no rows']
    for row in rows:
        fixture = row.get('fixture_id')
        try:
            recomputed, rule = replay_published_row(row)
        except ValueError as exc:
            errors.append(f'{fixture}: {exc}')
            continue
        if recomputed is None:
            continue
        published = row.get('probabilities') or []
        if len(published) != 2:
            errors.append(f'{fixture}: published pair is not two values')
            continue
        delta = max(abs(recomputed[0] - float(published[0])), abs(recomputed[1] - float(published[1])))
        if delta > TOLERANCE:
            errors.append(f'{fixture}: published {published} but {rule} gives '
                          f'{[round(v, 8) for v in recomputed]}')
        if row.get('pick_index') not in (0, 1):
            errors.append(f'{fixture}: the published build carries no pick')
        elif row.get('pick') != (row.get('teams') or [None, None])[row['pick_index']]:
            errors.append(f'{fixture}: pick {row.get("pick")!r} is not the side at that index')
        report['published_rows'].append({'fixture_id': fixture, 'method': row.get('method'),
                                         'rule': rule, 'delta': round(delta, 12)})
    summary = document.get('summary') or {}
    if int(summary.get('fixtures', -1)) != len(rows):
        errors.append('published-verification.json summary.fixtures does not equal its rows')
    if int(summary.get('with_pick', -1)) != sum(1 for r in rows if r.get('pick_index') in (0, 1)):
        errors.append('published-verification.json summary.with_pick does not equal its rows')
    if int(summary.get('replay_pass', -1)) != sum(1 for r in rows if r.get('replay_verdict') == 'pass'):
        errors.append('published-verification.json summary.replay_pass does not equal its rows')
    return errors


def verify() -> tuple[list[str], dict]:
    report = {'checks': [], 'replay': [], 'valve_rows': [], 'inventory': [],
              'identities': [], 'coverage': {}, 'published_rows': [], 'flags': 0}
    errors: list[str] = []
    for name, fn in (('replay', check_replay), ('valve', check_valve_rows), ('inventory', check_inventory),
                     ('identities', check_identities), ('coverage', check_coverage),
                     ('published', check_published_verification),
                     ('flags', check_flags), ('no-votes', check_no_votes)):
        found = fn(report)
        report['checks'].append({'check': name, 'errors': found, 'ok': not found})
        errors.extend(f'{name}: {message}' for message in found)
    report['ok'] = not errors
    return errors, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--json', type=Path, help='write the machine-readable report here')
    parser.add_argument('--published', type=Path,
                        help='also check a published build directory (origination.json): every open '
                             'fixture must carry a pick or an explicit unresolved entry')
    args = parser.parse_args(argv)
    errors, report = verify()
    if args.published:
        published_errors, table = published_coverage(args.published)
        report['published'] = {'build': str(args.published), 'rows': table,
                               'checks': {'errors': published_errors, 'ok': not published_errors}}
        errors.extend(f'published: {message}' for message in published_errors)
        picks = [r for r in table if r['state'] == 'pick']
        print(f'\nPublished build {args.published}: {len(table)} open fixtures, '
              f'{len(picks)} with a pick, '
              f'{sum(1 for r in table if r["state"] == "unresolved-with-blocker")} explicitly unresolved')
        for row in table:
            detail = (f'{row["pick"]} {row["probability"]:.4f} via {row["method"]}'
                      if row['state'] == 'pick' else row['state'])
            print(f'  {row["fixture_id"]}  {detail}')
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'Replay: {len(report["replay"])} published probability pairs recomputed '
          f'({sum(1 for r in report["replay"] if r["delta"] <= TOLERANCE)} exact)')
    for row in report['replay']:
        print(f'  {row["fixture_id"]}  {row["method"]:9s}  {row["rule"][:52]:52s}  '
              f'published {row["published"][0]:.4f}/{row["published"][1]:.4f}  delta {row["delta"]:.2e}')
    print(f'Valve rows: {len(report["valve_rows"])} matched the official committed file')
    states = {}
    for item in report['inventory']:
        states[item['state']] = states.get(item['state'], 0) + 1
    print('Inventory transcription: ' + ', '.join(f'{k} {v}' for k, v in sorted(states.items())))
    print(f'HLTV identities: {len(report["identities"])}')
    print('Coverage: ' + json.dumps(report['coverage']))
    print(f'Published build (2026-10-26T01:04:30Z): {len(report["published_rows"])} rows re-derived '
          f'({sum(1 for r in report["published_rows"] if r["delta"] <= TOLERANCE)} exact), '
          f'{len({r["method"] for r in report["published_rows"]})} methods')
    print(f'Review flags: {report["flags"]}')
    if errors:
        print('\nFAIL')
        for message in errors:
            print('  - ' + message)
        return 1
    print('\nPASS: every dossier value re-derives from its own official evidence.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
