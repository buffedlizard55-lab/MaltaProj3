"""Verify the deployed Pages artifact, including project-subpath routing.

Run after deploy-pages. Bounded retries allow CDN propagation, never conceal a
failed deployment. No source collection or credentialed requests occur here.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def verify_day4(expected, originated, twc, day4, page):
    """All Day-4 picks must agree across inventory, canonical JSON and HTML."""
    from scripts.domain import name_key
    if day4 != twc.get('day4') or day4.get('schema_version') != 1:
        raise ValueError('Day-4 JSON differs between published views')
    if day4.get('source_snapshot_at') != expected.get('inventory_observed_at'):
        raise ValueError('Day-4 snapshot mismatch')
    wanted = {m['id']: m for m in expected['matches']
              if name_key(m.get('competition') or '') == name_key('Thunderpick World Championship 2026')
              and str(m.get('starts_at') or '').startswith('2026-10-17')}
    rows = day4.get('matches') or []
    if len(rows) != len(wanted) or {r['fixture']['id'] for r in rows} != set(wanted):
        raise ValueError('Day-4 view omits or invents a Hotspawn fixture')
    if len(page.select('#day-four-picks .twc-day4-card')) != len(rows):
        raise ValueError('Day-4 HTML fixture coverage mismatch')
    canonical = {m['id']: m for m in originated['matches']}
    for row in rows:
        fixture = row['fixture']
        original = wanted[fixture['id']]
        c = canonical.get(fixture['id']) or {}
        if any(fixture.get(k) != original.get(k) for k in ['teams', 'starts_at', 'locks_at', 'source_url']):
            raise ValueError('Day-4 fixture facts differ from inventory')
        if row.get('analysis') != c.get('origination') or row.get('pick_index') != c.get('pick_index'):
            raise ValueError('Day-4 probabilities or direction differ from canonical picks')
        pick = row.get('pick_index')
        names = [t.get('name') for t in original['teams']]
        if row['teams'] != names or row.get('pick') != (names[pick] if pick is not None else None):
            raise ValueError('Day-4 team direction mismatch')
        card = page.find(id='twc-day4-' + fixture['id'])
        values = [n.get_text(strip=True) for n in card.select('.twc-prob strong')] if card else []
        probs = row['analysis']['probabilities'] if row.get('analysis') else None
        if values != ([f'{p*100:.1f}%' for p in probs] if probs else ['—', '—']):
            raise ValueError('Day-4 HTML probabilities differ from JSON')
    return len(rows)


def verify(url, expected):
    base = url.rstrip('/') + '/'
    session = requests.Session()
    session.headers.update({'Cache-Control': 'no-cache', 'User-Agent': 'CS2DashboardDeploymentVerifier/1.0'})

    def get(path):
        response = session.get(urljoin(base, path), params={'snapshot': expected['generated_at']}, timeout=(5, 15))
        response.raise_for_status()
        return response

    actual = get('data/latest.json').json()
    if actual.get('generated_at') != expected['generated_at'] or actual.get('counts') != expected['counts']:
        raise ValueError('Public snapshot does not match this verified deployment yet')
    for route in ['', 'picks/', 'edge/', 'twc-picks/', 'coverage/', 'methodology/', 'review/']:
        page = BeautifulSoup(get(route).text, 'html.parser')
        body = page.find('body')
        if not body or body.get('data-snapshot-generated') != expected['generated_at']:
            raise ValueError(f'{route or "/"}: wrong or stale dashboard HTML')
        if not page.find('h1') or not page.find('main'):
            raise ValueError(f'{route or "/"}: missing main page content')
        if route == '':
            primary = page.select_one('.hero-actions a.primary')
            mobile_picks = page.select('.mobile-nav a')
            if not primary or primary.get('href') != './origination/#picks':
                raise ValueError('Public primary pick button does not reach complete picks')
            if len(mobile_picks) < 2 or mobile_picks[1].get('href') != './origination/#picks':
                raise ValueError('Public phone picks navigation does not reach complete picks')
            if not page.find(id='contrarian') or not page.find(id='upset-watchlist') or not page.select_one('[aria-label="Complete pick coverage"]'):
                raise ValueError('Public complete-coverage/contrarian briefing missing')
        if route == 'review/' and not page.find(id='day-one-review'):
            raise ValueError('Public day-one verification limitations missing')
        if route == 'picks/':
            rows = page.select('#match-list > tbody > tr')
            upcoming = [m for m in expected['matches'] if m['availability'] != 'past']
            if len(rows) != len(upcoming):
                raise ValueError('Public picks page omits a future or unknown-schedule source row')
    # The dated upset review must publish its own research window, sections and sources.
    edge_page = BeautifulSoup(get('edge/').text, 'html.parser')
    for anchor in ['day-one', 'rosters', 'rules', 'day-two', 'day-two-results', 'day-three', 'day-three-guide', 'standings', 'edge-limitations']:
        if not edge_page.find(id=anchor):
            raise ValueError(f'edge/: missing #{anchor} section')
    if not any('hltv.org' in (a.get('href') or '') for a in edge_page.select('a[href^="https://"]')):
        raise ValueError('edge/: no official HLTV source link published')
    edge_data = get('data/edge-review.json').json()
    if edge_data.get('schema_version') != 1 or not edge_data.get('prepared_at'):
        raise ValueError('edge/: published research review data is missing its schema or preparation time')
    if not edge_data.get('day_one') or not edge_data.get('day_two'):
        raise ValueError('edge/: published research review has no reviewed matches')
    day3_data = get('data/day3-guide.json').json()
    if day3_data.get('schema_version') != 1 or not day3_data.get('prepared_at'):
        raise ValueError('edge/: published Day-3 guide data is missing its schema or preparation time')
    if len(day3_data.get('day_two_results') or []) != 4 or len(day3_data.get('day_three') or []) != 2:
        raise ValueError('edge/: published Day-3 guide does not cover all Day-2 results and Day-3 deciders')
    originated = get('data/origination.json').json()
    if originated.get('source_snapshot_at') != expected['inventory_observed_at']:
        raise ValueError('Public fallback lines belong to another inventory observation')
    # The TWC page must be the generated view of this exact snapshot, not the
    # former hand-authored file with conflicting probabilities.
    twc = get('data/twc-day3-picks.json').json()
    if twc.get('schema_version') != 2 or twc.get('source_snapshot_at') != expected['inventory_observed_at']:
        raise ValueError('TWC data is not the generated view of this inventory snapshot')
    if twc.get('source_generated_at') != originated.get('generated_at'):
        raise ValueError('TWC probabilities belong to another complete-picks snapshot')
    if len(twc.get('day3_matches') or []) != 2 or {r.get('label') for r in twc['day3_matches']} != {'day3-aurora-9z', 'day3-betboom-legacy'}:
        raise ValueError('TWC data omits or invents a decider')
    twc_page = BeautifulSoup(get('twc-picks/').text, 'html.parser')
    if twc_page.body.get('data-page') != 'twc' or len(twc_page.select('#day-three-picks .twc-card')) != 2:
        raise ValueError('TWC generated page was replaced or its deciders are missing')
    for anchor in ['twc-summary', 'day-four-picks', 'day-three-results', 'day-three-picks', 'day-one-results', 'day-two-results', 'roster-check', 'unresolved']:
        if not twc_page.find(id=anchor):
            raise ValueError('TWC page missing #' + anchor)
    by_id = {m['id']: m for m in originated['matches']}
    for row in twc.get('day3_matches', []):
        current = by_id.get(row['id'])
        if row.get('analysis') and not current:
            raise ValueError('TWC estimate has no canonical complete-picks row')
        if current and (row.get('analysis') != current.get('origination') or row.get('pick_index') != current.get('pick_index')):
            raise ValueError('TWC probabilities or default pick diverged from complete picks')
        card = twc_page.find(id='twc-' + row['label'])
        values = [n.get_text(strip=True) for n in card.select('.twc-prob strong')] if card else []
        expected_values = [f'{p*100:.1f}%' for p in row['analysis']['probabilities']] if row.get('analysis') else ['—', '—']
        if values != expected_values:
            raise ValueError('TWC HTML probabilities differ from its generated JSON')
    day4 = get('data/twc-day4-picks.json').json()
    day4_count = verify_day4(expected, originated, twc, day4, twc_page)
    print('::notice::Public Day-4 canonical fixture coverage: ' + str(day4_count))
    get('assets/pick-safety.js')
    for row in twc['day3_matches']:
        a = row.get('analysis') or {}
        print('::notice::Public TWC: ' + json.dumps({
            'teams': row['teams'], 'probabilities': a.get('probabilities'),
            'default_pick': row.get('pick'), 'status_at_build': row['status'],
            'quote_observed_at': a.get('observed_at'), 'locks_at': row.get('locks_at'),
            'inventory_observed_at': twc['source_snapshot_at']}, ensure_ascii=False))
    get('assets/twc.css')
    print('::notice::TWC probabilities and defaults match this deployment’s complete-picks snapshot')
    wanted = {m['id'] for m in expected['matches'] if m['availability'] != 'past'}
    if {m['id'] for m in originated.get('matches', [])} != wanted:
        raise ValueError('Public complete-picks data omits or invents fixtures')
    page = BeautifulSoup(get('origination/').text, 'html.parser')
    if {el.get('id') for el in page.select('.pick-card')} != {'match-' + mid for mid in wanted}:
        raise ValueError('Public complete-picks page differs from its inventory')
    if not page.find(id='unresolved') or not page.find(id='aliases') or not page.find('h1'):
        raise ValueError('Public fallback evidence/limitations sections missing')
    if not expected['coverage_complete'] and not page.find(id='inventory-warning'):
        raise ValueError('Public complete-picks page hides unverified inventory status')
    for finding in actual.get('flags', []):
        if finding['id'] == 'inventory-failed':
            print('::notice::Inventory source limitation: ' + finding['detail'])
    get('assets/origination.css')
    # Leaderboard plan and row-source audit: derived output. A placeholder page is reported loudly but the
    # deployment itself (data, pages, links) has already been verified above.
    plan = BeautifulSoup(get('strategy/').text, 'html.parser')
    if plan.find(id='slate') and plan.find(id='unresolved') and plan.find('h1'):
        for asset in ['assets/strategy.css', 'assets/strategy.js', 'data/strategy.json', 'data/strategy-rules.json']:
            get(asset)
        print('::notice::Leaderboard plan published with its slate and unresolved section')
    else:
        print('::warning::Leaderboard plan page is the placeholder; the data refresh itself was published')
    audit = get('data/row-source-audit.json').json()
    totals = audit.get('totals') or {}
    print('::notice::Row-source audit: ' + json.dumps(totals))
    if totals.get('violation'):
        print(f"::warning::{totals['violation']} published rows lack an official source link or an unverified flag")
    print('::notice::Public complete-picks counts: ' + json.dumps(originated['counts']))
    for route in ['docs/index.html', 'archive/root-session/index.html']:
        if 'Archived session snapshot' not in get(route).text:
            raise ValueError(f'{route}: missing preserved, clearly labeled session archive')
    for route in ['picks.html', 'methodology.html', 'flagged.html']:
        if 'Open the current CS2 dashboard' not in get(route).text:
            raise ValueError(f'{route}: broken legacy URL handoff')
    print(f'PASS: deployed {base}; all current pages, full data, old URLs and both archives verified.')
    return base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--data', type=Path, default=Path('data/latest.json'))
    args = parser.parse_args()
    expected = json.loads(args.data.read_text())
    for attempt in range(12):
        try:
            base = verify(args.url, expected)
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
                    summary.write('\n## Public deployment verified\n\n' + base + '\n\nAll seven current dashboard pages, the canonical TWC view, the dated upset review, full snapshot, three old URLs and both preserved archives returned the expected content.\n')
            return
        except (requests.RequestException, ValueError) as exc:
            if attempt == 11:
                raise SystemExit(f'Public deployment verification failed: {exc}') from exc
            print(f'Waiting for Pages/CDN propagation ({attempt + 1}/12): {exc}', flush=True)
            time.sleep(5)


if __name__ == '__main__':
    main()
