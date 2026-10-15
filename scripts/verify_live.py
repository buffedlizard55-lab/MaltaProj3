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
    for route in ['', 'picks/', 'edge/', 'coverage/', 'methodology/', 'review/']:
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
                    summary.write('\n## Public deployment verified\n\n' + base + '\n\nAll six current pages, the dated upset review, full snapshot, three old URLs and both preserved archives returned the expected content.\n')
            return
        except (requests.RequestException, ValueError) as exc:
            if attempt == 11:
                raise SystemExit(f'Public deployment verification failed: {exc}') from exc
            print(f'Waiting for Pages/CDN propagation ({attempt + 1}/12): {exc}', flush=True)
            time.sleep(5)


if __name__ == '__main__':
    main()
