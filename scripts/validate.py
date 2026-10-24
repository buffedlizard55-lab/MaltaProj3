"""Reconcile every published row to original source evidence and replay its math."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse, unquote

from bs4 import BeautifulSoup

from scripts.collect import counts, normalize_fixture
from scripts.sources import gamma_games, parse_hltv_matches

from scripts.domain import (array, consensus, iso, market_analysis, parse_valve_table,
                            polymarket_candidate, selection, sportsbook_quote,
                            timestamp, valve_analysis)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path: Path):
    return json.loads(path.read_text())


def check_inventory(evidence: Path, rows, data):
    """Replay the published inventory against the surface it was actually read from.

    Session 9c4b1f7a, re-applied by ee124e8b: the fixture API can be refused
    (403) while the rendered lobby still serves the identical public array in
    its hydration block. A snapshot built from that fallback must replay the
    page payload it saved, must not claim API rows, and must keep the refused
    attempt in the manifest. Snapshots without the marker keep the original
    API-evidence requirement.
    """
    context = load(evidence / 'hotspawn-context.json')
    rendered_mode = context.get('inventory_source') == 'rendered-lobby'
    if rendered_mode:
        rendered = load(evidence / 'hotspawn-rendered-fixtures.json')
        require(rendered['observed_at'] == context['observed_at'], 'Rendered inventory observation timestamp restamped')
        require(rendered['pages'] == [p for p in ('lobby', 'cs2') if p in context.get('verified_pages', [])],
                'Rendered inventory names pages it did not read')
        require(context.get('api_ids') == [], 'A rendered inventory must not claim rows from a refused API')
        raw_rows = rendered['rows']
    else:
        raw_rows = load(evidence / 'hotspawn-fixtures.json')
    require(data['inventory_observed_at'] == context['observed_at'], 'Inventory observation timestamp restamped')
    raw = {str(r['id']): r for r in raw_rows if r.get('sport_alias') == 'cs2'}
    require(set(raw) == {m['id'] for m in rows}, 'Published inventory omits or invents a Hotspawn row')
    require(set(raw) == set(context['rendered_ids'] if rendered_mode else context['api_ids']),
            'Published inventory omits or invents a Hotspawn source row')
    # Older retained snapshots have no cross-check marker and must keep the
    # original strict three-way requirement. A new snapshot may only omit a
    # rendered page when it records that the page was actually unreadable.
    verified_pages = context.get('verified_pages', ['lobby', 'cs2'])
    crosscheck = context.get('crosscheck', 'complete')
    require(crosscheck in {'complete', 'partial', 'unavailable', 'rendered', 'rendered-partial'}, 'Unknown inventory cross-check state')
    expected = (('rendered' if len(verified_pages) == 2 else 'rendered-partial') if rendered_mode
                else ('complete' if len(verified_pages) == 2 else 'partial' if len(verified_pages) == 1 else 'unavailable'))
    require(crosscheck == expected, 'Inventory cross-check marker does not match the pages actually read')
    for page in verified_pages:
        require(page in {'lobby', 'cs2'}, 'Unknown rendered inventory page')
        require(set(raw) == set(context[page + '_ids']), 'A rendered Hotspawn inventory did not agree with the API')
    fact_keys = ['id', 'teams', 'competition', 'competition_id', 'starts_at', 'locks_at', 'source_status', 'source_end_at', 'best_of', 'series_format', 'tier', 'lock_offset_sec', 'observed_at', 'source_url', 'source_api', 'lobby_url', 'availability', 'evidence']
    if rendered_mode:
        require(any(r['id'] == 'hotspawn-fixtures' and r.get('status') == 'error' for r in data.get('requests', [])),
                'A rendered inventory must keep the refused API attempt in the manifest')
        require(any(r['id'] in ('hotspawn-lobby', 'hotspawn-cs2') and r.get('observed_at') == context['observed_at'] and r.get('status') == 'ok' for r in data.get('requests', [])),
                'Rendered inventory lacks its original successful page request')
    else:
        require(any(r['id'] == 'hotspawn-fixtures' and r.get('observed_at') == context['observed_at'] and r.get('status') == 'ok' and r.get('evidence') == 'data/evidence/hotspawn-fixtures.json' for r in data.get('requests', [])),
                'Inventory lacks its original successful observation request')
    return raw, context, fact_keys


def check_data(root: Path):
    data = load(root / 'latest.json')
    require(data.get('schema_version') == 1, 'Unsupported data schema')
    # Retained historical analyses replay at their original successful run time,
    # not the time of a newer FAILED inventory attempt.
    now = timestamp(data.get('analysis_as_of', data['last_attempted_at']))
    require(now is not None, 'Missing attempt timestamp')
    require(data['counts'] == counts(data['matches']), 'Summary counts do not reconcile to rows')
    rows = data['matches']
    require(len({m['id'] for m in rows}) == len(rows), 'Duplicate fixture ID')
    evidence = root / 'evidence'
    if not data['coverage_complete'] and not rows:
        require(any(f['id'] == 'inventory-failed' for f in data['flags']), 'Empty unverified inventory must have a visible failure flag')
        return data
    raw, context, fact_keys = check_inventory(evidence, rows, data)
    attempts = {r['id']: r for r in data.get('requests', [])}
    valve_rows = None
    hltv_path = evidence / 'hltv-research.json'
    if hltv_path.exists():
        page = load(evidence / 'hltv-page.json')
        require(load(hltv_path) == parse_hltv_matches(page['html']), 'HLTV identities/formats do not replay from original markup')
        request = attempts.get('hltv-matches', {})
        require(request.get('status') == 'ok' and request.get('observed_at') == page['observed_at'], 'HLTV observation timestamp restamped')
        require(hashlib.sha256(page['html'].encode()).hexdigest() == request.get('response_sha256'), 'HLTV markup does not match original HTTP response hash')
    index_path = evidence / 'polymarket-index.json'
    if index_path.exists():
        for game in load(index_path):
            origin = game.get('discovery_evidence')
            if origin:
                require(re.fullmatch(r'data/evidence/polymarket-discovery-\d+\.json', origin) is not None, 'Unsafe Gamma discovery evidence path')
                discovered = gamma_games(load(evidence / Path(origin).name), origin)
                require(game in discovered, 'Gamma index identity does not replay from the original tagged event page')
                label = Path(origin).stem
                request = attempts.get(label, {})
                require(request.get('status') == 'ok' and request.get('evidence') == origin and request.get('url', '').startswith('https://gamma-api.polymarket.com/events?'), 'Gamma discovery page lacks its actual successful source request')
    for m in rows:
        expected = normalize_fixture(raw[m['id']], context['permalinks'], data['inventory_observed_at'], now)
        for key in fact_keys:
            require(m[key] == expected[key], f'{m["id"]}: {key} does not equal the official observation')
        for key in ['source_url', 'source_api']:
            url = urlparse(m[key])
            require(url.scheme == 'https' and url.netloc in {'play.hotspawn.com', 'www.hotspawn.com', 'phpstack-1372681-6459848.cloudwaysapps.com'}, f'{m["id"]}: nonofficial match source')
        require(timestamp(m['observed_at']) is not None, f'{m["id"]}: missing observation time')
        a = m['analysis']
        if a is None:
            require(m['pick_index'] is None, f'{m["id"]}: pick invented without probability evidence')
            continue
        require(m['availability'] != 'past', f'{m["id"]}: retrospective prematch price manufactured')
        require(len(a['probabilities']) == 2 and all(isinstance(p, (float, int)) and 0 < p < 1 for p in a['probabilities']), f'{m["id"]}: invalid probability')
        require(abs(sum(a['probabilities']) - 1) < 1e-7, f'{m["id"]}: probabilities do not sum to 100%')
        require(m['pick_index'] == selection(a), f'{m["id"]}: wrong favorite / arbitrary equal-probability pick')
        if a['method'] == 'market':
            event_id = a['event_id']
            event = load(evidence / f'polymarket-event-{event_id}.json')
            market, reason = polymarket_candidate(event, m, now)
            require(market is not None, f'{m["id"]}: {reason}')
            books = [load(evidence / f'polymarket-book-{event_id}-{i}.json') for i in [0, 1]]
            replay = market_analysis(event, market, books, m, now, a['observed_at'])
            require(attempts[f'polymarket-book-{event_id}-1']['observed_at'] == a['observed_at'], f'{m["id"]}: quote timestamp restamped')
            index = load(evidence / 'polymarket-index.json')
            require(any(str(g['id']) == event_id for g in index), f'{m["id"]}: event was not discovered from the official CS2 directory')
        elif a['method'] == 'model':
            if valve_rows is None:
                source = load(evidence / 'valve-standings-response.json')
                content = base64.b64decode(source['content'])
                git_sha = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
                require(git_sha == source['sha'], 'Valve evidence fails Git blob integrity verification')
                saved = load(evidence / 'valve-ratings.json')
                valve_rows = parse_valve_table(content.decode('utf-8'), source['html_url'], saved['snapshot_date'])
                require(valve_rows == saved['rows'], 'Valve rating records do not match original official markdown')
            exact = None
            if any('detail_sha' in inp for inp in a['inputs']):
                exact = {}
                for inp in a['inputs']:
                    standing = inp['standing']
                    detail_source = load(evidence / f'valve-detail-{standing}.json')
                    require(attempts.get(f'valve-detail-{standing}', {}).get('status') == 'ok', f'{m["id"]}: missing verified valve-detail-{standing} request')
                    require(detail_source.get('encoding') == 'base64', f'{m["id"]}: valve-detail-{standing} not base64')
                    detail_raw = base64.b64decode(''.join(detail_source['content'].split()), validate=True)
                    detail_sha = hashlib.sha1(b'blob ' + str(len(detail_raw)).encode() + b'\0' + detail_raw).hexdigest()
                    require(detail_sha == detail_source.get('sha') == inp.get('detail_sha'), f'{m["id"]}: Valve detail blob fails Git SHA-1 verification')
                    detail_match = re.search(r'Final Rank Value:\s*(\d+(?:\.\d+)?)', detail_raw.decode('utf-8'))
                    require(detail_match is not None and detail_source.get('html_url') == inp.get('source_url'), f'{m["id"]}: Valve detail file missing Final Rank Value or source URL')
                    exact[standing] = {'points': float(detail_match.group(1)), 'source_url': detail_source['html_url'], 'detail_sha': detail_sha}
            replay, reason = valve_analysis(m, valve_rows, now, a['observed_at'], exact_points=exact)
            require(replay is not None, f'{m["id"]}: {reason}')
            require(a['inputs'] == replay['inputs'], f'{m["id"]}: model inputs are not exact official records')
            if data.get('analysis_as_of'):
                require(a['observed_at'] == attempts['valve-standings-response']['observed_at'], f'{m["id"]}: rating observation timestamp restamped')
            require(any(r['stage'] == 'HLTV research' for r in m['research']) and any(r['stage'] == 'Original esportsbook lines' for r in m['research']), f'{m["id"]}: fallback sequence was not attempted')
            require(not any(r['status'] == 'resolved' and r['stage'].startswith('Primary') for r in m['research']), f'{m["id"]}: fallback overwrote primary pick')
        elif a['method'] == 'bookmaker':
            body = load(evidence / 'thunderpick-matches.json')['data']
            source_rows = body.get('upcoming', body.get('matches', []))
            qs = [sportsbook_quote(r, m, a['observed_at'], now) for r in source_rows]
            accepted = [q for q in qs if q]
            require(len(accepted) == 1, f'{m["id"]}: ambiguous original bookmaker events')
            request = attempts['thunderpick-matches']
            require(request.get('status') == 'ok' and request.get('url') == a['source_url'], 'Bookmaker source URL is not the actual successful request')
            require(request['observed_at'] == a['observed_at'], f'{m["id"]}: bookmaker observation timestamp restamped')
            require(request['method'] == 'POST' and request.get('request_body') == {'gameIds': [6]}, 'Original bookmaker POST query was not recorded')
            replay = consensus(accepted, now)
            require(replay is not None and replay['quotes'] == a['quotes'], f'{m["id"]}: bookmaker source evidence invalid')
        else:
            raise ValueError(f'{m["id"]}: unsupported analysis method')
        require(a == replay, f'{m["id"]}: displayed analysis/quotes/inputs do not equal the complete first-party replay')
        for key in ['probabilities', 'fair_decimal', 'source_url']:
            require(a[key] == replay[key], f'{m["id"]}: {key} calculation/provenance does not replay')
    for f in data['flags']:
        require(f['source_urls'], f'Flag without original source: {f["id"]}')
        require(set(f['match_ids']) <= set(raw), f'Flag references nonexistent fixture: {f["id"]}')
    for m in rows:
        if m['availability'] in {'open', 'locked', 'unknown_lock'} and m['analysis'] is None:
            require(any(m['id'] in f['match_ids'] for f in data['flags']), f'{m["id"]}: unresolved row is hidden from review')
    print(f'PASS: {len(rows)} source rows reconciled; every published probability and pick replayed from first-party evidence.')
    return data


def check_links(site: Path):
    checked = 0
    for path in site.rglob('*.html'):
        soup = BeautifulSoup(path.read_text(), 'html.parser')
        require(soup.find('main') is not None, f'{path}: no main landmark')
        require(soup.find('meta', attrs={'name': 'viewport'}) is not None, f'{path}: missing mobile viewport')
        for el in soup.select('[href], [src]'):
            value = el.get('href') if el.has_attr('href') else el.get('src')
            url = urlparse(value)
            if url.scheme or url.netloc:
                require(url.scheme in {'https', 'mailto', 'data'}, f'{path}: unsafe external URL {value}')
                continue
            require(not url.path.startswith('/'), f'{path}: root-relative link breaks project Pages paths: {value}')
            target = (path.parent / unquote(url.path)).resolve() if url.path else path.resolve()
            if target.is_dir():
                target /= 'index.html'
            require(target.is_file(), f'{path}: broken local link {value}')
            require(target.is_relative_to(site.resolve()), f'{path}: link escapes output directory')
            if url.fragment and target.suffix == '.html':
                dest = BeautifulSoup(target.read_text(), 'html.parser')
                require(dest.find(id=unquote(url.fragment)) is not None, f'{path}: missing anchor {value}')
            checked += 1
    require(checked > 0, 'No generated pages/links validated')
    print(f'PASS: {checked} internal links/assets/anchors; project-subpath routing and mobile landmarks checked.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--site', type=Path)
    args = parser.parse_args()
    check_data(args.data)
    if args.site:
        check_links(args.site)
