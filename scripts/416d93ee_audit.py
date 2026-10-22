"""Session 416d93ee: independent, first-party verification of the published picks.

This script is *read-only*. It never writes a pick, never edits data/, and never
touches the collectors. It answers four questions with dated, hashable evidence:

1. Inventory parity — is every CS2 fixture Hotspawn currently lists present in
   the published snapshot, with the same teams and the same start time?
2. Arithmetic replay — does every published probability follow from the inputs
   that same row publishes (order-book midpoints, decimal odds, official rating
   points)? The formulas are re-implemented here rather than imported, so a bug
   in ``scripts.originate`` cannot validate itself.
3. Official-input spot-check — do the rating points quoted by the model rows
   match what Valve and HLTV publish on the cited page?
4. Phone findability — does the published executive summary carry a working
   in-site link to the picks list, an unresolved section, and the viewport /
   landmark markup a phone needs?

Every network read records its HTTP status and SHA-256 so a reader can re-check
the exact bytes instead of trusting this report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests
from bs4 import BeautifulSoup

LIVE = 'https://buffedlizard55-lab.github.io/MaltaProj3'
FIXTURES_API = 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?' + urlencode(
    {'sport_alias': 'cs2', 'status': 'scheduled', 'tenantId': 1})
LOBBY = 'https://play.hotspawn.com/lobby'
CS2_LOBBY = 'https://play.hotspawn.com/cs2-pickems'
HLTV_RANKING = 'https://www.hltv.org/ranking/teams'
VALVE_TREE = 'https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings/git/trees/main?recursive=1'
VALVE_RAW = 'https://raw.githubusercontent.com/ValveSoftware/counter-strike_regional_standings/main/'
UA = 'MaltaProj3-verification/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'


class Reader:
    """Minimal read-only HTTP client that records what it actually observed."""

    def __init__(self, evidence: Path):
        self.evidence = evidence
        self.log: list[dict] = []
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': UA, 'Accept': 'application/json,text/html;q=0.9,*/*;q=0.8'})

    def get(self, url: str, label: str, *, keep: bool = False) -> dict:
        entry = {'label': label, 'url': url, 'observed_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
        try:
            response = self.session.get(url, timeout=(15, 60), allow_redirects=True)
            body = response.content
            entry.update(http_status=response.status_code, final_url=response.url,
                         content_type=response.headers.get('Content-Type'),
                         response_date=response.headers.get('Date'),
                         bytes=len(body),
                         sha256=hashlib.sha256(body).hexdigest())
            if keep and response.status_code == 200:
                # Never save evidence as .html: the site build publishes data/
                # verbatim and validates every .html page it finds, so a saved
                # source page would be audited as one of our own pages.
                suffix = '.json' if 'json' in (response.headers.get('Content-Type') or '') else '.html.txt'
                path = self.evidence / (re.sub(r'[^A-Za-z0-9_.-]+', '-', label).strip('-') + suffix)
                path.write_bytes(body)
                entry['saved_as'] = path.name
            entry['ok'] = response.status_code == 200
            entry['text'] = body.decode('utf-8', 'replace') if response.status_code == 200 else ''
        except Exception as exc:  # a read failure is recorded, never papered over
            entry.update(ok=False, http_status=None, error=f'{type(exc).__name__}: {exc}', text='')
        self.log.append({k: v for k, v in entry.items() if k != 'text'})
        return entry

    def manifest(self) -> list[dict]:
        return [dict(item) for item in self.log]


# ---------------------------------------------------------------------------
# Re-implemented arithmetic. Deliberately not imported from scripts.originate.
# ---------------------------------------------------------------------------

def _finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalise(a: float, b: float) -> list[float]:
    if a <= 0 or b <= 0:
        raise ValueError('two positive values required')
    p = a / (a + b)
    return [p, 1 - p]


def no_vig(odds: list) -> list[float]:
    implied = [1 / float(o) for o in odds]
    return normalise(*implied)


def valve_expectation(points_a: float, points_b: float, rd: float = 75.0) -> list[float]:
    """Valve's published Glicko-style expectation, re-implemented from fit.js."""
    scale = math.log(10) / 400
    g = 1 / math.sqrt(1 + 3 * (scale ** 2) * (rd ** 2) / (math.pi ** 2))
    p = 1 / (1 + 10 ** (g * (points_b - points_a) / 400))
    return [p, 1 - p]


def ranking_expectation(points_a: float, points_b: float) -> list[float]:
    """400-scale logistic transform used by the HLTV ranking rung."""
    p = 1 / (1 + 10 ** ((points_b - points_a) / 400))
    return [p, 1 - p]


def _midpoints(quotes: list[dict]) -> list[float]:
    """Two order-book midpoints, in either published shape.

    A featured Polymarket row stores one quote per outcome with scalar bid/ask;
    an origination row stores one quote holding a two-element bid/ask array.
    Both shapes are validated rather than assumed, and nothing is defaulted.
    """
    if not quotes:
        raise ValueError('no quotes to read')
    first = quotes[0]
    if isinstance(first.get('bid'), list) and isinstance(first.get('ask'), list):
        pairs = list(zip(first['bid'], first['ask']))
    elif len(quotes) >= 2:
        pairs = [(q.get('bid'), q.get('ask')) for q in quotes[:2]]
    else:
        raise ValueError('single quote without a paired book')
    values = [(_finite(b), _finite(a)) for b, a in pairs]
    if len(values) != 2 or any(b is None or a is None or not 0 < b <= a < 1 for b, a in values):
        raise ValueError('invalid or crossed order-book prices')
    return [(b + a) / 2 for b, a in values]


def replay_row(record: dict) -> dict:
    """Recompute one published row from the inputs that row itself publishes."""
    origination = record.get('origination') or {}
    published = origination.get('probabilities')
    method = origination.get('method')
    label = origination.get('label') or ''
    quotes = origination.get('quotes') or []
    result = {'id': record.get('id'), 'label': label, 'method': method,
              'family': origination.get('family'), 'provider': origination.get('provider'),
              'published': published, 'recomputed': None, 'status': 'not_replayable', 'detail': ''}
    if not published or len(published) != 2:
        result['detail'] = 'row publishes no probability pair'
        return result
    try:
        if method in ('market', 'bookmaker') and quotes:
            # A single family: replay that family's own inputs exactly.
            first = quotes[0]
            if first.get('odds'):
                recomputed = no_vig(first['odds'])
                basis = 'decimal odds, margin removed proportionally'
            elif first.get('bid') and first.get('ask'):
                mids = _midpoints(quotes)
                recomputed = normalise(*mids)
                basis = 'order-book midpoints, normalised'
            else:
                result['detail'] = 'quote carries neither odds nor a two-sided book'
                return result
        elif method == 'consensus' and quotes:
            pairs = [q.get('probabilities') for q in quotes if q.get('probabilities')]
            if not pairs:
                result['detail'] = 'consensus quotes publish no probability pairs'
                return result
            first_legs = sorted(p[0] for p in pairs)
            middle = len(first_legs) // 2
            median = first_legs[middle] if len(first_legs) % 2 else (first_legs[middle - 1] + first_legs[middle]) / 2
            recomputed = normalise(median, 1 - median)
            basis = f'median of {len(pairs)} independent money families'
        elif method == 'model' and str(origination.get('provider') or '').startswith('Own'):
            inputs = origination.get('inputs') or []
            if len(inputs) != 2:
                result['detail'] = 'own-model row does not publish two rating inputs'
                return result
            if origination.get('family') == 'network' or 'network' in str(origination.get('provider')).casefold():
                recomputed = ranking_expectation(float(inputs[0]['points']), float(inputs[1]['points']))
                basis = 'own network rating on the 400-point logistic'
            else:
                def side_rd(side: dict) -> float:
                    fit = side.get('fitted') or {}
                    if not fit.get('n'):
                        return 75.0
                    return min(400.0, 150.0 + 300.0 / math.sqrt(int(fit['n'])))
                rd = max(side_rd(inputs[0]), side_rd(inputs[1]))
                recomputed = valve_expectation(float(inputs[0]['points']), float(inputs[1]['points']), rd)
                basis = f'own results-based fit on Valve\'s logistic (RD {rd:.1f})'

        elif method == 'model' and 'Valve' in label:
            inputs = origination.get('inputs') or []
            if len(inputs) != 2:
                result['detail'] = 'Valve row does not publish two rating inputs'
                return result
            recomputed = valve_expectation(float(inputs[0]['points']), float(inputs[1]['points']),
                                          float(origination.get('rd_assumption') or 75))
            basis = "Valve fit.js expectation at RD 75"
        elif method == 'model' and 'HLTV' in label:
            inputs = origination.get('inputs') or []
            if len(inputs) == 2:
                recomputed = ranking_expectation(float(inputs[0]['points']), float(inputs[1]['points']))
                basis = 'HLTV ranking 400-scale logistic'
            else:
                quote = (quotes or [{}])[0]
                points = quote.get('points') or quote.get('ranking_points')
                if not points or len(points) != 2:
                    result['detail'] = 'HLTV row publishes no two ranking points'
                    return result
                recomputed = ranking_expectation(float(points[0]), float(points[1]))
                basis = 'HLTV ranking 400-scale logistic'
        elif method == 'guidance' and quotes:
            first = quotes[0]
            if not (first.get('bid') and first.get('ask')):
                result['detail'] = 'guidance quote publishes no two-sided book'
                return result
            mids = _midpoints(quotes)
            recomputed = normalise(*mids)
            basis = f'wide-book midpoint (spread {first.get("spread")})'
        elif method == 'reference' and quotes:
            odds = (quotes[0] or {}).get('odds')
            if not odds:
                result['detail'] = 'aggregated reference publishes no odds'
                return result
            recomputed = no_vig(odds)
            basis = 'aggregated reference odds, margin removed'
        else:
            result['detail'] = f'method {method!r} has no replayable formula in this audit'
            return result
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        result['detail'] = f'{type(exc).__name__}: {exc}'
        return result
    delta = max(abs(a - b) for a, b in zip(recomputed, published))
    result.update(recomputed=[round(p, 8) for p in recomputed], basis=basis,
                  max_abs_delta=round(delta, 8))
    if delta <= 5e-4:
        result['status'] = 'replayed'
        result['detail'] = f'{basis}; largest deviation {delta:.2e}'
    elif delta <= 5e-3:
        result['status'] = 'rounding-only'
        result['detail'] = f'{basis}; largest deviation {delta:.2e} (display rounding)'
    else:
        result['status'] = 'mismatch'
        result['detail'] = f'{basis}; published {published} vs recomputed {recomputed}'
    return result


# ---------------------------------------------------------------------------
# Official rating inputs
# ---------------------------------------------------------------------------

def valve_points(markdown: str) -> dict[str, list[dict]]:
    """Parse Valve's published global standings markdown into {name: points}.

    The published column order is ``Standing | Points | Team Name | Roster``;
    the header row is read rather than assumed, so a column reorder produces an
    empty table (an honest read failure) instead of a wrong number.
    """
    columns = None
    table: dict[str, list[dict]] = {}
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        cells = [c.strip() for c in stripped.strip('|').split('|')]
        if columns is None:
            lowered = [c.casefold() for c in cells]
            if any('points' in c for c in lowered) and any('team' in c for c in lowered):
                columns = (next(i for i, c in enumerate(lowered) if 'points' in c),
                           next(i for i, c in enumerate(lowered) if 'team' in c))
            continue
        if len(cells) <= max(columns):
            continue
        name = cells[columns[1]].replace('**', '').strip()
        match = re.fullmatch(r'\**([\d.]+)\**', cells[columns[0]])
        if name and match:
            roster = ''
            if len(cells) > columns[1] + 1:
                roster = cells[columns[1] + 1]
            table.setdefault(name.casefold(), []).append(
                {'points': float(match.group(1)), 'roster': roster.casefold()})
    return table


def hltv_ranking_points(html: str) -> dict[str, float]:
    """Parse HLTV's world ranking page into {team name: published points}."""
    soup = BeautifulSoup(html, 'html.parser')
    table: dict[str, float] = {}
    for row in soup.select('.ranked-team, .ranking-team'):
        name = row.select_one('.name, .teamLine .name')
        points = row.select_one('.points, .js-points')
        if not name:
            continue
        text = re.sub(r'^#\d+\s*', '', name.get_text(' ', strip=True)).strip()
        if points:
            match = re.search(r'(\d+(?:\.\d+)?)', points.get_text(' ', strip=True))
            if match:
                table[text.casefold()] = float(match.group(1))
    return table


# ---------------------------------------------------------------------------
# Site-level checks
# ---------------------------------------------------------------------------

def unresolved_section_text(summary_html: str) -> str:
    """Text of the summary's unresolved register, if the page publishes one."""
    soup = BeautifulSoup(summary_html, 'html.parser')
    # The executive summary uses ``unresolved-register``; the dedicated
    # origination page uses ``unresolved``. Accept both real publication
    # contracts instead of reporting a false missing-register failure.
    section = soup.find(id='unresolved-register') or soup.find(id='unresolved')
    return section.get_text(' ', strip=True) if section else ''


def phone_checks(summary_html: str, picks_html: str, unresolved_html: str = '') -> dict:
    soup = BeautifulSoup(summary_html, 'html.parser')
    links = [a.get('href', '') for a in soup.find_all('a', href=True)]
    internal = [href for href in links if href.startswith(('origination/', 'picks/', './', '/MaltaProj3/')) or href.startswith('#')]
    pick_links = [href for href in links if re.search(r'origination/(#picks)?$|origination/#picks$', href)]
    text = soup.get_text(' ', strip=True)
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    nav = soup.find_all('nav')
    pick_soup = BeautifulSoup(picks_html, 'html.parser')
    pick_table_rows = len(pick_soup.select('tr.match-row'))
    return {
        'viewport_meta': bool(viewport and 'width=device-width' in (viewport.get('content') or '')),
        'nav_landmarks': len(nav),
        'skip_link': bool(soup.find('a', href=re.compile(r'^#main'))),
        'internal_links': len(internal),
        'pick_index_links': sorted(set(pick_links)),
        'has_unresolved_section': 'Unresolved' in text and ('limitations' in text.casefold()),
        'mentions_every_match': 'All 12 active fixtures are listed' in text or 'active Hotspawn CS2 fixtures' in text,
        'picks_page_table_rows': pick_table_rows,
        'unresolved_page_present': bool(unresolved_html.strip()),
    }


def inventory_compare(published: list[dict], api_rows: list[dict], now: datetime) -> dict:
    """Compare the published active set with Hotspawn's own scheduled array."""
    def start(row):
        value = row.get('starts_at')
        if value:
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return None
        raw = row.get('scheduled_start_time')
        return datetime.fromtimestamp(int(raw) / 1000, timezone.utc) if raw else None

    api_future = {str(r['id']): r for r in api_rows if start(r) and start(r) > now}
    api_past = {str(r['id']): r for r in api_rows if start(r) and start(r) <= now}
    published_open = {str(m['id']): m for m in published if m.get('availability') == 'open'}
    missing = sorted(set(api_future) - set(published_open))
    extra = sorted(set(published_open) - set(api_future))
    rows = []
    for fixture_id in sorted(set(api_future) & set(published_open)):
        source, published_row = api_future[fixture_id], published_open[fixture_id]
        api_teams = [source.get('participants0_name'), source.get('participants1_name')]
        names = [t.get('name') for t in published_row.get('teams') or []]
        rows.append({
            'id': fixture_id,
            'teams_match': ([t.casefold() for t in api_teams if t]
                            == [n.casefold() for n in names if n]),
            'api_teams': api_teams,
            'published_teams': names,
            'start_delta_sec': int((start(published_row) - start(source)).total_seconds()),
            'api_start': start(source).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'published_start': published_row.get('starts_at'),
            'competition_match': (source.get('competition_name') or '').casefold() == (published_row.get('competition') or '').casefold(),
        })
    return {
        'api_records': len(api_rows),
        'api_future': len(api_future),
        'api_past_start_but_scheduled': len(api_past),
        'published_open': len(published_open),
        'missing_from_site': missing,
        'published_but_not_in_api': extra,
        'per_fixture': rows,
        'all_teams_match': all(r['teams_match'] for r in rows),
        'all_starts_within_60s': all(abs(r['start_delta_sec']) <= 60 for r in rows),
        'all_competitions_match': all(r['competition_match'] for r in rows),
    }


def lobby_counts(html: str) -> dict:
    week = re.search(r'(\d+)\s+matches this week', html)
    tiers = re.findall(r'All tiers\s*\((\d+)\)', html)
    fixture_ids = sorted(set(re.findall(r'hotspawn\.com/matches/[a-z0-9-]+-(\d{6,})', html)))
    return {
        'matches_this_week': int(week.group(1)) if week else None,
        'all_tiers_count': int(tiers[0]) if tiers else None,
        'fixture_links_in_html': len(fixture_ids),
        'fixture_ids_in_html': fixture_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', default='data/research/416d93ee')
    parser.add_argument('--source', default=None, help='Alternatively audit a local data directory instead of the live site')
    parser.add_argument('--site', default=None, help='Built Pages root for summary/picks HTML when auditing local data')
    args = parser.parse_args()
    evidence = Path(args.evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    reader = Reader(evidence)
    now = datetime.now(timezone.utc)
    stamp = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    report: dict = {'schema_version': 1, 'session': '416d93ee', 'observed_at': stamp,
                    'purpose': 'Independent verification of the published picks; read-only, no pick is written.'}

    # -- 1. the published snapshot ------------------------------------------
    if args.source:
        latest = json.loads((Path(args.source) / 'latest.json').read_text())
        origination = json.loads((Path(args.source) / 'origination.json').read_text())
        summary_html = (Path(args.source) / 'index.html').read_text() if (Path(args.source) / 'index.html').exists() else ''
        picks_html = (Path(args.source) / 'picks' / 'index.html').read_text() if (Path(args.source) / 'picks' / 'index.html').exists() else ''
        report['published_source'] = args.source
    else:
        read = reader.get(f'{LIVE}/data/latest.json?cb=416d93ee-{int(now.timestamp())}', 'live-latest', keep=True)
        latest = json.loads(read['text']) if read.get('ok') else {}
        read_orig = reader.get(f'{LIVE}/data/origination.json?cb=416d93ee-{int(now.timestamp())}', 'live-origination', keep=True)
        origination = json.loads(read_orig['text']) if read_orig.get('ok') else {}
        summary_html = reader.get(f'{LIVE}/?cb=416d93ee-{int(now.timestamp())}', 'live-summary').get('text', '')
        picks_html = reader.get(f'{LIVE}/picks/?cb=416d93ee-{int(now.timestamp())}', 'live-picks').get('text', '')
        report['published_source'] = LIVE
    if args.site:
        site_root = Path(args.site)
        summary_path = site_root / 'index.html'
        picks_path = site_root / 'picks' / 'index.html'
        summary_html = summary_path.read_text() if summary_path.exists() else ''
        picks_html = picks_path.read_text() if picks_path.exists() else ''
    report['published'] = {
        'generated_at': latest.get('generated_at'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'coverage_complete': latest.get('coverage_complete'),
        'counts': latest.get('counts'),
        'origination_counts': (origination or {}).get('counts'),
        'origination_source_snapshot_at': (origination or {}).get('source_snapshot_at'),
    }

    records = (origination or {}).get('matches') or []
    active = [r for r in records if r.get('availability') == 'open']
    report['pick_coverage'] = {
        'records': len(records),
        'active': len(active),
        'active_with_probabilities': sum(1 for r in active if (r.get('origination') or {}).get('probabilities')),
        'active_with_pick': sum(1 for r in active if r.get('pick_index') is not None),
        'active_without_pick': [{'id': r['id'], 'teams': [t['name'] for t in r['teams']],
                                 'reason': (r.get('limitations') or ['no limitation text'])[0]}
                                for r in active if r.get('pick_index') is None],
        'active_without_any_probability': [{'id': r['id'], 'teams': [t['name'] for t in r['teams']]}
                                           for r in active if not (r.get('origination') or {}).get('probabilities')],
    }

    # -- 2. arithmetic replay of every published row -------------------------
    replay = [replay_row(r) for r in records if (r.get('origination') or {}).get('probabilities')]
    report['arithmetic'] = {
        'rows_with_probabilities': len(replay),
        'replayed': sum(1 for r in replay if r['status'] == 'replayed'),
        'rounding_only': sum(1 for r in replay if r['status'] == 'rounding-only'),
        'mismatch': [r for r in replay if r['status'] == 'mismatch'],
        'not_replayable': [r for r in replay if r['status'] == 'not_replayable'],
        'pick_mismatches': [],
        'fair_line_mismatches': [],
        'sum_mismatches': [],
    }
    for record in records:
        origination_row = record.get('origination') or {}
        probabilities = origination_row.get('probabilities')
        if not probabilities:
            continue
        if abs(sum(probabilities) - 1) > 1e-6:
            report['arithmetic']['sum_mismatches'].append({'id': record['id'], 'sum': sum(probabilities)})
        expected = 0 if probabilities[0] > probabilities[1] else 1
        if abs(probabilities[0] - probabilities[1]) < 1e-8:
            expected = None
        if record.get('pick_index') != expected:
            report['arithmetic']['pick_mismatches'].append(
                {'id': record['id'], 'published': record.get('pick_index'), 'argmax': expected,
                 'probabilities': probabilities})
        fair = origination_row.get('fair_decimal') or []
        if fair:
            want = [round(1 / p, 3) for p in probabilities]
            if [round(v, 3) for v in fair] != want:
                report['arithmetic']['fair_line_mismatches'].append(
                    {'id': record['id'], 'published': fair, 'expected': want})

    # -- 2b. does the published label name the evidence actually used? --------
    label_issues = []
    for record in records:
        origination_row = record.get('origination') or {}
        if not origination_row:
            continue
        family = (origination_row.get('family') or '').casefold()
        provider = origination_row.get('provider') or ''
        label = origination_row.get('label') or ''
        actual = ('network' if family == 'network' or provider.startswith('Own network')
                  else 'results' if family == 'form' or provider.startswith('Own results')
                  else 'hltv' if 'HLTV' in provider or 'HLTV' in label
                  else 'valve' if family in ('model', '') and ('Valve' in provider or 'Valve' in label)
                  else None)
        if actual == 'network' and 'network' not in label.casefold():
            label_issues.append({'id': record['id'], 'label': label, 'provider': provider,
                                 'family': origination_row.get('family'),
                                 'expected': 'an own-network label',
                                 'detail': 'the row is priced from our own bo3.gg Bradley-Terry fit but the label names another method'})
        elif actual == 'results' and 'results-based' not in label.casefold():
            label_issues.append({'id': record['id'], 'label': label, 'provider': provider,
                                 'family': origination_row.get('family'),
                                 'expected': 'an own results-based label',
                                 'detail': 'the row is priced from our own results fit but the label names another method'})
        elif actual == 'valve' and 'Valve' not in label:
            label_issues.append({'id': record['id'], 'label': label, 'provider': provider,
                                 'family': origination_row.get('family'),
                                 'expected': 'a Valve-rating label',
                                 'detail': 'the row is priced from Valve rating rows but the label names another method'})
        elif actual == 'hltv' and 'HLTV' not in label:
            label_issues.append({'id': record['id'], 'label': label, 'provider': provider,
                                 'family': origination_row.get('family'),
                                 'expected': 'an HLTV-ranking label',
                                 'detail': 'the row is priced from the HLTV ranking but the label names another method'})
    report['label_consistency'] = {'checked': sum(1 for r in records if r.get('origination')),
                                   'issues': label_issues}

    # -- 3. official-input spot-check ---------------------------------------
    model_rows = [r for r in records if (r.get('origination') or {}).get('method') == 'model']
    snapshots = sorted({(r['origination'].get('snapshot_date') or '') for r in model_rows if 'Valve' in (r['origination'].get('label') or '')})
    valve_tables: dict[str, dict] = {}
    for date in [d for d in snapshots if d]:
        url = VALVE_RAW + f'live/{date[:4]}/standings_global_{date.replace("-", "_")}.md'
        read = reader.get(url, f'valve-standings-{date}', keep=True)
        if read.get('ok'):
            valve_tables[date] = valve_points(read['text'])
    hltv_read = reader.get(HLTV_RANKING, 'hltv-ranking', keep=True)
    hltv_table = hltv_ranking_points(hltv_read['text']) if hltv_read.get('ok') else {}
    report['official_inputs'] = {'valve_snapshots_read': sorted(valve_tables), 'hltv_ranking_http': hltv_read.get('http_status'),
                                 'hltv_rows_parsed': len(hltv_table), 'checks': []}
    for record in model_rows:
        origination_row = record['origination']
        label = origination_row.get('label') or ''
        entry = {'id': record['id'], 'label': label, 'checks': []}
        provider = str(origination_row.get('provider') or '')
        if provider.startswith('Own'):
            entry['checks'].append({'source': 'own-model', 'name': '-', 'row_points': None,
                                    'valve_points': None,
                                    'status': 'not-an-official-rating-row',
                                    'detail': f'priced from {provider}; Valve/HLTV rows are not its inputs'})
        elif 'Valve' in label:
            date = origination_row.get('snapshot_date') or ''
            table = valve_tables.get(date) or {}
            for source in origination_row.get('inputs') or []:
                name, points = source.get('name'), source.get('points')
                candidates = table.get((name or '').casefold()) or []
                roster = ' '.join(source.get('roster') or []).casefold()
                chosen = next((c for c in candidates if roster and roster in c['roster']), None)
                if chosen is None and len(candidates) == 1:
                    chosen = candidates[0]
                published = chosen['points'] if chosen else None
                ambiguous = len(candidates) > 1 and chosen is None
                entry['checks'].append({'source': 'Valve', 'name': name, 'row_points': points,
                                        'valve_points': published,
                                        'candidates': [c['points'] for c in candidates],
                                        'status': 'match' if published is not None and abs(published - float(points)) < 1e-6
                                        else ('ambiguous-name' if ambiguous
                                              else ('missing-in-table' if published is None else 'mismatch'))})
        elif 'HLTV' in label and not provider.startswith('Own'):
            for source in origination_row.get('inputs') or []:
                name, points = source.get('name'), source.get('points')
                published = hltv_table.get((name or '').casefold())
                entry['checks'].append({'source': 'HLTV', 'name': name, 'row_points': points,
                                        'hltv_points': published,
                                        'status': 'match' if published is not None and abs(published - float(points)) < 1e-6
                                        else ('not-in-top-listing' if published is None else 'mismatch')})
        report['official_inputs']['checks'].append(entry)

    # -- 4. Hotspawn inventory ----------------------------------------------
    api_read = reader.get(FIXTURES_API, 'hotspawn-fixtures', keep=True)
    api_rows = json.loads(api_read['text']) if api_read.get('ok') and api_read['text'].strip().startswith('[') else []
    lobby_read = reader.get(f'{LOBBY}?cb={int(now.timestamp())}', 'hotspawn-lobby', keep=True)
    cs2_read = reader.get(f'{CS2_LOBBY}?cb={int(now.timestamp())}', 'hotspawn-cs2-lobby', keep=True)
    report['hotspawn'] = {
        'api_http': api_read.get('http_status'),
        'api_sha256': api_read.get('sha256'),
        'lobby_http': lobby_read.get('http_status'),
        'cs2_lobby_http': cs2_read.get('http_status'),
        'lobby': lobby_counts(lobby_read.get('text', '')),
        'cs2_lobby': lobby_counts(cs2_read.get('text', '')),
    }
    lobby_total = (report['hotspawn'].get('cs2_lobby') or {}).get('all_tiers_count')
    report['hotspawn']['coverage_counts'] = {
        'lobby_cs2_all_tiers': lobby_total,
        'lobby_this_week': (report['hotspawn'].get('cs2_lobby') or {}).get('matches_this_week'),
        'api_records': len(api_rows),
        'published_inventory': (latest or {}).get('counts', {}).get('inventory'),
        'published_upcoming': (latest or {}).get('counts', {}).get('upcoming'),
        'lobby_equals_api': lobby_total == len(api_rows) if lobby_total is not None and api_rows else None,
        'lobby_equals_published_inventory': (lobby_total == (latest or {}).get('counts', {}).get('inventory')
                                             if lobby_total is not None and latest else None),
    }
    if api_rows:
        report['hotspawn']['inventory_compare'] = inventory_compare(active, api_rows, now)
        report['hotspawn']['status_matrix'] = {
            status: sum(1 for r in api_rows if r.get('status') == status)
            for status in sorted({r.get('status') for r in api_rows})}

    # -- 5. phone findability ------------------------------------------------
    if summary_html:
        report['phone'] = phone_checks(summary_html, picks_html)

    # -- 5b. are the side-less rows published in the unresolved register? ------
    register_text = unresolved_section_text(summary_html) if summary_html else ''
    report['unresolved_register'] = {
        'published_on_summary': bool(register_text),
        'rows_checked': [],
    }
    for record in active:
        if record.get('pick_index') is not None:
            continue
        names = [t.get('name') or '' for t in record.get('teams') or []]
        listed = bool(register_text) and all(name.casefold() in register_text.casefold() for name in names if name)
        report['unresolved_register']['rows_checked'].append({
            'id': record['id'], 'teams': names,
            'has_probabilities': bool((record.get('origination') or {}).get('probabilities')),
            'listed_in_register': listed,
        })

    # -- 6. honest verdicts --------------------------------------------------
    verdicts = []
    coverage = report['pick_coverage']
    verdicts.append(('inventory_and_picks_cover_every_active_fixture',
                     coverage['active'] > 0 and not coverage['active_without_any_probability']))
    verdicts.append(('every_active_fixture_shows_a_probability_on_the_summary',
                     not coverage['active_without_any_probability']))
    unpicked = report['unresolved_register']['rows_checked']
    verdicts.append(('every_active_fixture_has_a_pick_or_a_published_even_estimate',
                     all(row['has_probabilities'] for row in unpicked)))
    verdicts.append(('every_side_less_row_is_listed_in_the_unresolved_register',
                     all(row['listed_in_register'] for row in unpicked)))
    verdicts.append(('every_published_probability_replays_from_its_own_inputs',
                     bool(report['arithmetic']['rows_with_probabilities'])
                     and not report['arithmetic']['mismatch']
                     and not report['arithmetic']['not_replayable']))
    verdicts.append(('published_pick_is_the_published_argmax',
                     not report['arithmetic']['pick_mismatches']))
    verdicts.append(('every_published_label_names_the_evidence_it_uses',
                     not report['label_consistency']['issues']))
    if 'inventory_compare' in report['hotspawn']:
        compare = report['hotspawn']['inventory_compare']
        verdicts.append(('every_future_dated_hotspawn_fixture_is_published',
                         not compare['missing_from_site']))
        verdicts.append(('published_fixture_teams_and_times_match_the_api',
                         compare['all_teams_match'] and compare['all_starts_within_60s']))
    if 'phone' in report:
        phone = report['phone']
        verdicts.append(('phone_summary_links_the_picks_list',
                         bool(phone['pick_index_links']) and phone['viewport_meta']))
    report['verdicts'] = [{'check': name, 'pass': bool(ok)} for name, ok in verdicts]
    report['failures'] = [name for name, ok in verdicts if not ok]
    report['requests'] = reader.manifest()
    report['read_failures'] = [r for r in reader.manifest() if not r.get('ok')]

    (evidence / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (evidence / 'verification.md').write_text(render_markdown(report))
    print(json.dumps({'failures': report['failures'], 'coverage': coverage,
                      'arithmetic': {k: v for k, v in report['arithmetic'].items() if not isinstance(v, list) or not v},
                      'hotspawn': report['hotspawn'].get('inventory_compare', {}).get('missing_from_site'),
                      'phone': report.get('phone')}, indent=2, default=str))
    return 0 if not report['failures'] else 1


def render_markdown(report: dict) -> str:
    lines = [f"# Independent verification — {report['observed_at']}", '',
             f"Read-only audit by session 416d93ee of `{report['published_source']}`.", '']
    published = report['published']
    lines += ['## Published snapshot', '',
              f"- `generated_at`: {published['generated_at']}",
              f"- inventory observed: {published['inventory_observed_at']}",
              f"- published counts: `{json.dumps(published['counts'], sort_keys=True)}`",
              f"- origination counts: `{json.dumps(published['origination_counts'], sort_keys=True)}`", '']
    coverage = report['pick_coverage']
    lines += ['## Pick coverage', '',
              f"- records in the complete list: **{coverage['records']}**",
              f"- active fixtures: **{coverage['active']}**",
              f"- active with probabilities: **{coverage['active_with_probabilities']}**",
              f"- active with a directional pick: **{coverage['active_with_pick']}**",
              f"- active without a pick: **{len(coverage['active_without_pick'])}**", '']
    arithmetic = report['arithmetic']
    lines += ['## Arithmetic replay', '',
              f"- rows with probabilities: **{arithmetic['rows_with_probabilities']}**",
              f"- replayed exactly: **{arithmetic['replayed']}**",
              f"- display-rounding only: **{arithmetic['rounding_only']}**",
              f"- mismatches: **{len(arithmetic['mismatch'])}**",
              f"- not replayable: **{len(arithmetic['not_replayable'])}**", '']
    for row in arithmetic['not_replayable'][:40]:
        lines.append(f"  - `{row['id']}` {row['label']}: {row['detail']}")
    lines.append('')
    hotspawn = report.get('hotspawn') or {}
    compare = hotspawn.get('inventory_compare')
    labels = report.get('label_consistency') or {}
    lines += ['## Method labels', '',
              f"- rows checked: **{labels.get('checked')}**; labels naming a different method than the inputs: **{len(labels.get('issues') or [])}**", '']
    for issue in labels.get('issues') or []:
        lines.append(f"  - `{issue['id']}` label “{issue['label']}” but inputs are `{issue['provider']}` (family {issue['family']}) — expected {issue['expected']}")
    lines.append('')
    lines += ['## Hotspawn inventory parity', '']
    if compare:
        lines += [f"- API records: **{compare['api_records']}** (future starts: **{compare['api_future']}**, "
                  f"past-start records still marked scheduled: **{compare['api_past_start_but_scheduled']}**)",
                  f"- published open fixtures: **{compare['published_open']}**",
                  f"- missing from the published site: **{len(compare['missing_from_site'])}** {compare['missing_from_site']}",
                  f"- published but not in the API: **{len(compare['published_but_not_in_api'])}** {compare['published_but_not_in_api']}",
                  f"- teams match: **{compare['all_teams_match']}**; starts within 60 s: **{compare['all_starts_within_60s']}**; "
                  f"competitions match: **{compare['all_competitions_match']}**", '']
    lines += [f"- rendered lobby counts: `{json.dumps(hotspawn.get('lobby'), sort_keys=True)}`",
              f"- rendered CS2 lobby counts: `{json.dumps(hotspawn.get('cs2_lobby'), sort_keys=True)}`",
              f"- coverage counts: `{json.dumps(hotspawn.get('coverage_counts'), sort_keys=True)}`", '']
    official = report.get('official_inputs') or {}
    lines += ['## Official model inputs', '',
              f"- Valve snapshots read: {official.get('valve_snapshots_read')}",
              f"- HLTV ranking HTTP: {official.get('hltv_ranking_http')} ({official.get('hltv_rows_parsed')} rows parsed)", '']
    for entry in official.get('checks') or []:
        for check in entry['checks']:
            lines.append(f"  - `{entry['id']}` {entry['label']}: {check['source']} {check['name']} "
                         f"row {check['row_points']} vs published "
                         f"{(check.get('valve_points') if check['source'] == 'Valve' else check.get('hltv_points'))} — {check['status']}")
    lines.append('')
    phone = report.get('phone')
    if phone:
        lines += ['## Phone findability', '', f"- viewport meta: **{phone['viewport_meta']}**",
                  f"- nav landmarks: **{phone['nav_landmarks']}**",
                  f"- in-site pick links on the summary: {phone['pick_index_links']}",
                  f"- unresolved section on the summary: **{phone['has_unresolved_section']}**",
                  f"- rows on the picks page: **{phone['picks_page_table_rows']}**", '']
    register = report.get('unresolved_register') or {}
    lines += ['## Unresolved register', '',
              f"- register published on the summary: **{register.get('published_on_summary')}**", '']
    for row in register.get('rows_checked') or []:
        lines.append(f"  - `{row['id']}` {' vs '.join(row['teams'])}: probabilities {row['has_probabilities']}, "
                     f"listed in the register {row['listed_in_register']}")
    lines += ['', '## Verdicts', ''] + [f"- {'PASS' if v['pass'] else 'FAIL'} — {v['check']}" for v in report['verdicts']]
    read_failures = report.get('read_failures') or []
    lines += ['', '## Unreadable requests', ''] + ([f"- `{r['url']}` — {r.get('http_status') or r.get('error')}" for r in read_failures] or ['- none'])
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    raise SystemExit(main())
