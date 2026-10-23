"""Collect the entire public Hotspawn CS2 inventory and resolve supported picks.

Run: python -m scripts.collect [--output data]
Source failures are published as coverage limitations, never invented values.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.domain import (identity_matches, name_key, iso, market_analysis, polymarket_candidate,
                            selection, sportsbook_quote, consensus, timestamp, valve_analysis)
from scripts.sources import (Client, SourceError, LOBBY, CS2_LOBBY, FIXTURES_API,
                             POLY_INDEX, HLTV, hotspawn, poly_index, hltv_research,
                             thunderpick, book_page_check, valve_detail_points, valve_ratings)


BOOK_PAGES = [
    ('https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike', 'ggbet-cs2', 'GG.BET esportsbook'),
    ('https://www.pinnacle.com/en/esports-hub/cs2', 'pinnacle-cs2', 'Pinnacle esportsbook'),
    ('https://www.rivalry.com/esports/counter-strike-betting', 'rivalry-cs2', 'Rivalry esportsbook'),
    ('https://stake.com/sports/esports/counter-strike', 'stake-cs2', 'Stake esportsbook'),
]


def failed(name, url, exc, now):
    return {'name': name, 'url': url, 'status': 'unavailable', 'observed_at': iso(datetime.now(timezone.utc)), 'records': None, 'detail': str(exc)}


def record_book_check(matches, result):
    """Attach shared source-access evidence only to still-unresolved matches.

    A page check is not a match search or proof that a market does not exist.
    Preserve that distinction and the actual source observation timestamp.
    """
    for match in matches:
        if match['analysis'] is None:
            match['research'].append({
                'stage': result['name'], 'source_url': result['url'],
                'status': result['status'], 'observed_at': result['observed_at'],
                'detail': result['detail'],
            })


def normalize_fixture(raw, links, observed_at, now):
    start, lock = timestamp(raw.get('scheduled_start_time')), timestamp(raw.get('lock_time'))
    fixture_id = str(raw['id'])
    availability = 'unknown'
    if start:
        availability = 'past' if start <= now else ('unknown_lock' if not lock else ('locked' if lock <= now else 'open'))
    permalink = links.get(fixture_id)
    if not isinstance(permalink, str) or not permalink.startswith('https://www.hotspawn.com/matches/'):
        permalink = None
    return {
        'id': fixture_id, 'teams': [{'id': str(raw[f'participants{i}_id']) if raw.get(f'participants{i}_id') is not None else None, 'name': raw.get(f'participants{i}_name')} for i in [0, 1]],
        'competition': raw.get('competition_name'), 'competition_id': raw.get('competition_id'),
        'starts_at': iso(start) if start else None, 'locks_at': iso(lock) if lock else None,
        'source_status': raw.get('status'), 'source_end_at': iso(timestamp(raw.get('end_time'))) if timestamp(raw.get('end_time')) else None,
        'best_of': raw.get('best_of'), 'series_format': raw.get('series_format'), 'tier': raw.get('tier'),
        'lock_offset_sec': raw.get('lock_offset_sec'), 'availability': availability,
        'observed_at': observed_at, 'source_url': permalink or (f'{CS2_LOBBY}#fixture-{fixture_id}' if availability != 'past' else FIXTURES_API),
        'lobby_url': f'{CS2_LOBBY}#fixture-{fixture_id}' if availability != 'past' else CS2_LOBBY,
        'source_api': FIXTURES_API, 'evidence': 'data/evidence/hotspawn-fixtures.json',
        'analysis': None, 'pick_index': None, 'research': [], 'limitations': [],
    }


def counts(matches):
    upcoming = [m for m in matches if m['availability'] in {'open', 'locked', 'unknown_lock'}]
    return {
        'inventory': len(matches), 'upcoming': len(upcoming),
        'archived': sum(m['availability'] == 'past' for m in matches),
        'unknown_schedule': sum(m['availability'] == 'unknown' for m in matches),
        'market': sum(bool(m['analysis']) and m['analysis']['method'] == 'market' for m in upcoming),
        'bookmaker': sum(bool(m['analysis']) and m['analysis']['method'] == 'bookmaker' for m in upcoming),
        'model': sum(bool(m['analysis']) and m['analysis']['method'] == 'model' for m in upcoming),
        'unresolved': sum(m['analysis'] is None for m in upcoming),
        'picks': sum(m['pick_index'] is not None for m in upcoming),
        'no_edge': sum(m['analysis'] is not None and m['pick_index'] is None for m in upcoming),
    }


def flag(key, title, detail, urls, ids=None, severity='warning'):
    return {'id': key, 'title': title, 'detail': detail, 'source_urls': urls, 'match_ids': ids or [], 'severity': severity}


def _collect_into(output: Path):
    now = datetime.now(timezone.utc)
    output.mkdir(parents=True, exist_ok=True)
    client = Client(output)
    health, flags = [], []
    try:
        raw, links, inventory = hotspawn(client)
        health.append(inventory)
    except (SourceError, ValueError, KeyError) as exc:
        health.append(failed('Hotspawn match inventory', LOBBY, exc, now))
        prior = output / 'latest.json'
        snapshot = json.loads(prior.read_text()) if prior.exists() else {'schema_version': 1, 'matches': [], 'inventory_observed_at': None, 'flags': []}
        snapshot.setdefault('analysis_as_of', snapshot.get('last_attempted_at', iso(now)))
        # A failed attempt cannot reset successful evidence or its observation times.
        prior_requests = snapshot.get('requests', [])
        snapshot.update(generated_at=iso(now), last_attempted_at=iso(now), coverage_complete=False, run_status='degraded', sources=health, requests=prior_requests + client.manifest)
        snapshot['flags'] = [f for f in snapshot.get('flags', []) if f['id'] != 'inventory-failed'] + [flag('inventory-failed', 'Hotspawn refresh failed — current coverage unverified', f'{exc}. Last-known records are retained with their ORIGINAL observation times. No new inventory or current-pick completeness is claimed.', [LOBBY, CS2_LOBBY, FIXTURES_API], severity='critical')]
        snapshot['counts'] = counts(snapshot['matches'])
        write_snapshot(output, snapshot)
        detail = f'{type(exc).__name__}: {exc}'.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::error title=Hotspawn inventory refresh failed::' + detail)
        print('WARNING: Hotspawn inventory unavailable; retained last-known data without changing its source timestamps.')
        return snapshot

    observed = inventory['observed_at']
    crosscheck = inventory.get('crosscheck', 'complete')
    matches = [normalize_fixture(r, links, observed, now) for r in raw]
    matches.sort(key=lambda m: (m['starts_at'] or '9999', m['id']))
    active = [m for m in matches if m['availability'] in {'open', 'locked', 'unknown_lock'}]
    for m in matches:
        if m['availability'] == 'past':
            m['limitations'].append('Past scheduled start. Source status is not a verified result; no retrospective prematch probability is manufactured.')
        if m['starts_at'] is None:
            m['limitations'].append('Scheduled start is unverified; no match identity/time join is permitted.')
        if m['best_of'] is None:
            m['limitations'].append('Hotspawn best-of format is unverified; left blank.')
        if not all(t['name'] and t['id'] for t in m['teams']):
            m['limitations'].append('Team identity is incomplete; no pick generated.')

    games = []
    try:
        games, h = poly_index(client)
        health.append(h)
    except (SourceError, ValueError, KeyError) as exc:
        health.append(failed('Polymarket CS2', POLY_INDEX, exc, now))
    for m in active:
        if not all(t['name'] and t['id'] for t in m['teams']):
            continue
        stage = {'stage': 'Primary: Polymarket', 'source_url': POLY_INDEX, 'status': 'unresolved', 'detail': ''}
        m['research'].append(stage)
        found = [g for g in games if identity_matches([g.get('homeName', ''), g.get('awayName', '')], g.get('startTime'), m) and g.get('isLive') is not True]
        # The same event may occur in the directory and the paginated feed.
        found = list({str(g['id']): g for g in found}.values())
        if len(found) != 1:
            stage['detail'] = ('Source unavailable; no absence-of-market claim is made.' if not games else 'No unique exact-name, exact-start-time fixture. Directory and paginated CS2-tag API checked where available; sponsor/abbreviated names are not silently aliased.')
            continue
        game = found[0]
        try:
            event, event_req = client.json('https://gamma-api.polymarket.com/events/' + str(game['id']), 'polymarket-event-' + str(game['id']))
            stage['source_url'] = 'https://polymarket.com/event/' + event['slug']
            market, reason = polymarket_candidate(event, m, now)
            if market is None:
                stage['detail'] = reason
                continue
            from scripts.domain import array
            books = []
            for i, token in enumerate(array(market['clobTokenIds'])):
                book, req = client.json('https://clob.polymarket.com/book?token_id=' + str(token), f'polymarket-book-{game["id"]}-{i}')
                books.append(book)
            analysis = market_analysis(event, market, books, m, now, req['observed_at'])
            m.update(analysis=analysis, pick_index=selection(analysis))
            stage.update(status='resolved', detail='Exact teams/time; unique active series-winner market; both source order books validated. Normalized midpoint analysis, not Hotspawn votes.')
        except (SourceError, ValueError, KeyError, TypeError) as exc:
            stage['detail'] = str(exc)

    missing = [m for m in active if m['analysis'] is None]
    if missing:
        # Research is deliberately restricted to matches the primary method did not resolve.
        try:
            research, h = hltv_research(client, missing)
            health.append(h)
            for m in missing:
                found = [r for r in research if identity_matches(r['teams'], r['starts_at'], m)]
                m['research'].append({'stage': 'HLTV research', 'source_url': found[0]['source_url'] if len(found) == 1 else HLTV, 'status': 'checked', 'detail': ('Exact teams/time confirmed on HLTV; ' + ('HLTV lists BO' + str(found[0]['best_of']) + '; Hotspawn format remains separately unverified. ' if found[0].get('best_of') else 'HLTV format unverified. ') + 'No original bookmaker price verified at this stage.') if len(found) == 1 else 'No unique structured HLTV identity confirmed.'})
                if not found:
                    wanted = {name_key(t['name']) for t in m['teams']}
                    start = timestamp(m['starts_at'])
                    nearby = [r for r in research if start and abs((timestamp(r['starts_at']) - start).total_seconds()) <= 60 and len(wanted.intersection(map(name_key, r['teams']))) == 1]
                    for r in nearby:
                        m['research'].append({'stage': 'HLTV identity review', 'source_url': r['source_url'], 'status': 'unresolved', 'detail': 'HLTV lists ' + ' vs '.join(r['teams']) + ' at the same scheduled time with one exact-name opponent. The other name differs; equivalence is NOT verified. This record is for review only, not a probability input or confirmed match join.'})

        except (SourceError, ValueError) as exc:
            health.append(failed('HLTV fallback research', HLTV, exc, now))
            for m in missing:
                m['research'].append({'stage': 'HLTV research', 'source_url': HLTV, 'status': 'unavailable', 'detail': str(exc)})

        book_rows = []
        book_observed = iso(now)
        try:
            book_rows, h = thunderpick(client)
            book_observed = h['observed_at']
            health.append(h)
        except (SourceError, ValueError) as exc:
            health.append(failed('Thunderpick esportsbook', 'https://thunderpick.io/esports/counter-strike', exc, now))
        for m in missing:
            qs = []
            for row in book_rows:
                try:
                    q = sportsbook_quote(row, m, book_observed, now)
                    if q:
                        qs.append(q)
                except (ValueError, KeyError, TypeError):
                    continue
            # More than one exact event is ambiguous, not independent confirmation.
            analysis = consensus(qs, now) if len(qs) == 1 else None
            if analysis:
                m.update(analysis=analysis, pick_index=selection(analysis))
            m['research'].append({'stage': 'Original esportsbook lines', 'source_url': 'https://thunderpick.io/esports/counter-strike', 'status': 'resolved' if analysis else 'unresolved', 'detail': 'Verified paired prematch series prices; proportional margin removal.' if analysis else 'No unique validated pair of original bookmaker odds available; source failures are not proof that no market exists.'})

        if any(m['analysis'] is None for m in missing):
            for url, label, title in BOOK_PAGES:
                try:
                    result = book_page_check(client, url, label, title)
                except (SourceError, ValueError) as exc:
                    result = failed(title, url, exc, now)
                health.append(result)
                record_book_check(missing, result)
            ratings = []
            ratings_observed = None
            try:
                ratings, h = valve_ratings(client, now)
                ratings_observed = h['observed_at']
                health.append(h)
            except (SourceError, ValueError, KeyError, TypeError) as exc:
                health.append(failed('Valve official rating fallback', 'https://github.com/ValveSoftware/counter-strike_regional_standings', exc, now))
            for m in missing:
                if m['analysis'] is not None:
                    continue
                analysis, reason = valve_analysis(m, ratings, now, ratings_observed) if ratings else (None, 'Official Valve ratings unavailable')
                if (analysis and analysis['inputs'][0]['points'] == analysis['inputs'][1]['points']
                        and all(inp.get('detail_path') for inp in analysis['inputs'])):
                    try:
                        year = analysis['snapshot_date'][:4]
                        exact = {inp['standing']: valve_detail_points(client, year, inp['detail_path'], inp['standing'])
                                 for inp in analysis['inputs']}
                        analysis, reason = valve_analysis(m, ratings, now, ratings_observed, exact_points=exact)
                    except (SourceError, ValueError, KeyError, TypeError) as exc:
                        m['research'].append({'stage': 'Valve official detail files', 'source_url': analysis['source_url'], 'status': 'unavailable', 'detail': str(exc)})
                if analysis:
                    m.update(analysis=analysis, pick_index=selection(analysis))
                m['research'].append({'stage': 'Valve research model', 'source_url': analysis['source_url'] if analysis else 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'status': 'resolved' if analysis else 'unresolved', 'detail': 'Unique exact-name five-player rating records. Explicitly uncalibrated model; no bookmaker odds claimed.' if analysis else reason})
                if analysis is None:
                    m['limitations'].append(reason)

    past = [m['id'] for m in matches if m['availability'] == 'past' and m['source_status'] == 'scheduled']
    if past:
        flags.append(flag('past-scheduled', 'Past-start records still marked scheduled', f'{len(past)} source records have past scheduled starts but are still labeled scheduled. They are retained in the source archive, not presented as playable matches or verified results.', [FIXTURES_API, LOBBY], past))
    unknown_schedule = [m['id'] for m in matches if m['availability'] == 'unknown']
    if unknown_schedule:
        flags.append(flag('unknown-schedule', 'Unverified schedules prevent match resolution', f'{len(unknown_schedule)} source records have no confirmed start time. They remain in the unresolved section and source inventory; no time-based market join or probability is invented.', [FIXTURES_API, LOBBY], unknown_schedule))
    unformatted = [m['id'] for m in matches if m['best_of'] is None]
    if unformatted:
        flags.append(flag('missing-format', 'Hotspawn series format is unverified', f'{len(unformatted)} fixtures have no confirmed Hotspawn best-of value. The field stays blank; market scope must independently confirm a full-series winner.', [FIXTURES_API], unformatted))
    try:
        rules, req = client.fetch('https://play.hotspawn.com/how-it-works', 'hotspawn-rules')
        text = BeautifulSoup(rules, 'html.parser').get_text(' ', strip=True)
        found = re.search(r'picks lock\s+(\d+)\s+minutes before', text, re.I)
        client.save('hotspawn-rules', {'url': req['url'], 'observed_at': req['observed_at'], 'confirmed_lock_minutes': int(found.group(1)) if found else None, 'text': text})
        if found:
            minutes = int(found.group(1))
            different = [m['id'] for m in matches if m['lock_offset_sec'] is not None and m['lock_offset_sec'] != minutes * 60]
            if different:
                flags.append(flag('lock-policy', 'Published lock rule differs from fixture data', f'Help page says {minutes} minutes before start; {len(different)} fixture lock offsets differ. Explicit per-fixture lock timestamps take precedence on this dashboard. Submit in Hotspawn before its countdown expires.', [req['url'], FIXTURES_API], different))
    except SourceError as exc:
        flags.append(flag('rules-unavailable', 'Help-page rule could not be refreshed', str(exc), ['https://play.hotspawn.com/how-it-works']))
    for h in health:
        if h['status'] != 'ok':
            flags.append(flag('source-' + re.sub(r'[^a-z0-9]+', '-', h['name'].lower()).strip('-'), h['name'] + ': source limitation', h['detail'] + ' No unsupported prices or statistics are substituted.', [h['url']]))
    modeled = [m['id'] for m in active if m['analysis'] and m['analysis']['method'] == 'model']
    if modeled:
        flags.append(flag('model-limitations', 'Research estimates are not verified betting odds', f'{len(modeled)} matches use published Valve rating inputs after the primary method and fallback book checks did not resolve them. The estimates are uncalibrated; current lineups, stand-ins and map vetoes are unverified. They do not replace or modify primary market picks.', ['https://github.com/ValveSoftware/counter-strike_regional_standings', 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/fit.js'], modeled, 'notice'))
    unresolved = [m for m in active if m['analysis'] is None]
    for m in unresolved:
        flags.append(flag('unresolved-' + m['id'], 'Unresolved: ' + ' vs '.join(t['name'] or 'Unverified team' for t in m['teams']), '; '.join(m['limitations'] + [r['detail'] for r in m['research'] if r['status'] != 'resolved']), [m['source_url']] + [r['source_url'] for r in m['research']], [m['id']]))
    if (output / 'matches.json').exists() or (output / 'picks-model.json').exists():
        flags.append(flag('legacy-snapshots', 'Earlier session snapshots are archived, not the current feed', 'Concurrent sessions used different identity rules, source timestamps and model weights. Their datasets, scripts and pages are retained for provenance. The current dashboard uses only data/latest.json and its replayed first-party evidence. Legacy records are not silently merged, relabeled as current, or independently reverified by this pipeline.', ['https://github.com/buffedlizard55-lab/MaltaProj3', LOBBY, POLY_INDEX], severity='notice'))
    if crosscheck in {'rendered', 'rendered-partial'}:
        # Session 9c4b1f7a (2026-10-23): the API itself answered 403 while the
        # rendered pages still carried the same public array. Publishing the
        # page-read array keeps the dashboard current; the flag keeps the
        # substituted surface visible instead of claiming a clean three-source read.
        flags.append(flag('inventory-api-unavailable', 'Hotspawn fixture API refused; inventory read from the rendered lobby', inventory['detail'] + ' Every retained probability, pick and fixture identity is unchanged and keeps its own observation time; nothing was invented to fill the gap.', [FIXTURES_API, CS2_LOBBY, LOBBY], severity='warning'))
    elif crosscheck != 'complete':
        flags.append(flag('inventory-crosscheck', 'Hotspawn lobby HTML cross-check unavailable', inventory['detail'] + ' No rendered page was treated as agreement, and no probability, pick or fixture was invented. Picks tied to this API snapshot remain usable and carry their own source observations.', [LOBBY, CS2_LOBBY, FIXTURES_API], severity='warning'))
    snapshot = {
        'schema_version': 1, 'generated_at': iso(datetime.now(timezone.utc)), 'last_attempted_at': iso(now), 'analysis_as_of': iso(now),
        'inventory_observed_at': observed, 'coverage_complete': True, 'inventory_crosscheck': crosscheck,
        'run_status': 'complete' if not unresolved else 'partial-picks',
        'refresh_interval_hours': 4, 'stale_after_hours': 8,
        'counts': counts(matches), 'matches': matches, 'sources': health, 'flags': flags, 'requests': client.manifest,
        'evidence_files': sorted(client.saved),
        'inventory_definition': (
            'Every CS2 record returned by Hotspawn’s scheduled-fixture API, reconciled with both official lobby payloads. Future starts are separate from past-start source anomalies. Coverage is not a claim that all rows have verified probabilities.'
            if crosscheck == 'complete' else
            'Every CS2 record in the public fixture array embedded in the rendered Hotspawn lobby pages, which agree on every ID. The scheduled-fixture API was unavailable this cycle, so no three-response reconciliation is claimed; the rendered payload is the same official array the API serves. Future starts are separate from past-start source anomalies. Coverage is not a claim that all rows have verified probabilities.'
            if crosscheck == 'rendered' else
            'Every CS2 record in the public fixture array embedded in the one readable Hotspawn lobby page. The scheduled-fixture API and the other rendered page were unavailable this cycle, so no reconciliation is claimed. Future starts are separate from past-start source anomalies. Coverage is not a claim that all rows have verified probabilities.'
            if crosscheck == 'rendered-partial' else
            'Every CS2 record returned by Hotspawn’s scheduled-fixture API. The rendered lobby HTML cross-check was ' + ('partial' if crosscheck == 'partial' else 'unavailable') + '; the API array is the authoritative scheduled inventory and no three-response reconciliation is claimed. Future starts are separate from past-start source anomalies. Coverage is not a claim that all rows have verified probabilities.'),
    }
    write_snapshot(output, snapshot)
    print('::notice title=Hotspawn inventory::' + json.dumps({'records': len(raw), 'crosscheck': crosscheck, 'verified_pages': inventory.get('verified_pages', []), 'unavailable': [x.split(':')[0] for x in inventory.get('unavailable', [])]}))
    print(json.dumps({'status': snapshot['run_status'], 'counts': snapshot['counts'], 'sources': [{k: h[k] for k in ['name', 'status']} for h in health]}, indent=2))
    return snapshot


def collect(output: Path):
    """Stage and replay a complete update before replacing any last-good files.

    A source can return a new API body and THEN fail reconciliation. Such a
    response must not overwrite the evidence underpinning retained old rows.
    Keep partial-attempt responses under distinct audit filenames instead.
    """
    from scripts.validate import check_data

    output = Path(output)
    prior = json.loads((output / 'latest.json').read_text()) if (output / 'latest.json').exists() else {}
    with tempfile.TemporaryDirectory(prefix='cs2-source-collection-') as directory:
        staged = Path(directory) / 'data'
        if output.exists():
            shutil.copytree(output, staged)
        else:
            staged.mkdir()
        snapshot = _collect_into(staged)
        evidence = staged / 'evidence'
        if not snapshot['coverage_complete']:
            attempted = snapshot['requests'][len(prior.get('requests', [])):]
            preserved = {}
            stamp = snapshot['last_attempted_at'].replace(':', '').replace('-', '')
            for index, request in enumerate(attempted):
                if request.get('evidence'):
                    incoming = evidence / Path(request['evidence']).name
                    if incoming.is_file():
                        name = f'failed-attempt-{stamp}-{index}-{incoming.name}'
                        preserved[name] = incoming.read_bytes()
                        request['evidence'] = 'data/evidence/' + name
                        request['failed_inventory_attempt_only'] = True
            shutil.rmtree(evidence, ignore_errors=True)
            if (output / 'evidence').exists():
                shutil.copytree(output / 'evidence', evidence)
            else:
                evidence.mkdir()
            for name, body in preserved.items():
                (evidence / name).write_bytes(body)
            write_snapshot(staged, snapshot)
        elif snapshot.get('evidence_files'):
            # Retain only evidence generated by THIS successful collection;
            # old events must not accumulate indefinitely in public artifacts.
            current = set(snapshot['evidence_files'])
            for path in evidence.glob('*.json'):
                if 'data/evidence/' + path.name not in current:
                    path.unlink()
        check_data(staged)
        # Nothing in the caller's data directory is touched unless replay passes.
        output.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staged, output, dirs_exist_ok=True)
        if snapshot['coverage_complete'] and snapshot.get('evidence_files'):
            current = set(snapshot['evidence_files'])
            for path in (output / 'evidence').glob('*.json'):
                if 'data/evidence/' + path.name not in current:
                    path.unlink()
        return snapshot


def write_snapshot(output, snapshot):
    temp = output / 'latest.json.tmp'
    temp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    temp.replace(output / 'latest.json')
    (output / 'sources.json').write_text(json.dumps(snapshot['requests'], ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data'))
    args = parser.parse_args()
    try:
        collect(args.output)
    except Exception as exc:
        # Job logs are not always readable through the API; make the exact
        # failure visible as a check annotation without leaking a traceback
        # into the published data.
        import traceback
        frames = traceback.extract_tb(exc.__traceback__)
        where = ' > '.join(f'{Path(f.filename).name}:{f.lineno}:{f.name}' for f in frames[-6:])
        detail = f'{type(exc).__name__}: {exc} @ {where}'.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::error title=CS2 collection failed::' + detail)
        raise
