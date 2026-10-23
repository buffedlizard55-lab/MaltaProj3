"""Session arena-ca7e10e5 — published-state verification and line research.

The coding sandbox has egress to GitHub only, so it cannot read the live site,
Hotspawn, HLTV or any bookmaker. This read-only probe runs on a GitHub Actions
runner (which has full egress) immediately AFTER ``scripts.collect`` and
``scripts.originate --live``, and answers three questions with dated evidence:

1. **What is actually published right now?** It reads
   ``https://buffedlizard55-lab.github.io/MaltaProj3/`` — the rendered
   ``index.html``, the ``origination`` table and ``data/latest.json`` — and
   records their HTTP status, the ``data-snapshot-generated`` stamp on the
   page, the ``generated_at`` inside the JSON, the rendered active/pick/
   unresolved counts, and the gap between the page and the JSON it sits above.

2. **Is every active Hotspawn CS2 fixture covered?** For every active fixture
   in the freshly collected snapshot it checks: both team names, a two-value
   probability pair strictly inside (0,1) that sums to 1, a ``pick_index`` that
   points at the more likely team, an https source URL, and the method that
   produced the number. Anything missing is listed row by row. It writes no
   probability.

3. **Does any esportsbook or exchange price the fixtures that only a research
   model resolves?** It probes additional structured surfaces that earlier
   sessions did not cover (Kalshi, DraftKings, FanDuel, 1xBet, SofaScore) plus
   HLTV, and records the HTTP status, whether the exact team names appear in
   the response, and — verbatim, never parsed into a probability — a truncated
   snippet around the first hit. A reachable page is not a price.

Nothing here writes a probability, a pick or an alias. The output is a dated
JSON document plus a Markdown rendering, committed under
``data/research/ca7e10e5/`` and never deployed by this session.

Usage: python -m scripts.ca7e10e5_probe [--data data]
                                        [--out data/research/ca7e10e5]
                                        [--live-url https://buffedlizard55-lab.github.io/MaltaProj3]
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
ACTIVE = {'open', 'locked', 'unknown_lock'}
MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference', 'relay', 'network'}
EPSILON = 1e-6

# Surfaces probed once per run. Each is read-only: status, exact-name presence
# and (for JSON) a truncated verbatim snippet. None of them produces a number.
CANDIDATE_SURFACES = [
    ('HLTV matches (official)', 'https://www.hltv.org/matches'),
    ('Kalshi esports series', 'https://api.elections.kalshi.com/trade-api/v2/series?category=Esports'),
    ('Kalshi open CS2 markets',
     'https://api.elections.kalshi.com/trade-api/v2/markets?status=open&limit=1000'),
    ('DraftKings CS2 league feed',
     'https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnj/v1/leagues/20065'),
    ('FanDuel esports content page',
     'https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page'
     '?page=CUSTOM&customPageId=esports&_ak=FhMFpcPWXMeyZxOxGExQFdENaGpmQep7M'
     '&timezone=America%2FNew_York'),
    ('1xBet CS2 line feed',
     'https://1xbet.com/LineFeed/Get1x2_VZip?sports=14&count=100&lng=en&mode=4'
     '&country=1&partner=51&getEmpty=true'),
    ('SofaScore esports schedule (identity only)',
     'https://www.sofascore.com/api/v1/sport/esports/scheduled-events/2026-10-23'),
]


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def age_hours(stamp: str | None) -> float | None:
    if not stamp:
        return None
    try:
        moment = datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return round((datetime.now(UTC) - moment).total_seconds() / 3600, 2)


def fetch(url: str, timeout: int = 20) -> dict:
    """GET one URL and return status, length and body (never raise)."""
    record = {'url': url, 'status': None, 'bytes': 0, 'body': '', 'error': None,
              'observed_at': now_iso(), 'challenge': None}
    try:
        response = requests.get(url, timeout=timeout, headers={
            'User-Agent': UA, 'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8',
            'Cache-Control': 'no-cache'})
    except Exception as exc:  # noqa: BLE001 - evidence, not control flow
        record['error'] = f'{type(exc).__name__}: {exc}'[:200]
        return record
    record['status'] = response.status_code
    record['body'] = response.text or ''
    record['bytes'] = len(response.content or b'')
    lowered = record['body'][:8000].lower()
    for token in ('just a moment', 'challenge-platform', 'cf-chl', 'captcha',
                  'attention required', 'access denied', 'enable javascript'):
        if token in lowered:
            record['challenge'] = token
            break
    return record


# --------------------------------------------------------------------------
# 1. What is published right now
# --------------------------------------------------------------------------

def flatten(html: str) -> str:
    """Visible text of a page with tags removed and whitespace collapsed."""
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


ROW_RE = re.compile(r'<tr id="row-(\d+)"(.*?)</tr>', re.S)
PROB_RE = re.compile(r'<span class="tbl-prob[^"]*">\s*([^:<]+?):\s*<strong>([\d.]+)%</strong>')
PICK_RE = re.compile(r'<strong class="tbl-pick">[^<]*?([^<]+)</strong>')
SRC_RE = re.compile(r'<a class="src" href="(https?://[^"]+)"')


def parse_rows(html: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for match in ROW_RE.finditer(html):
        block = match.group(2)
        probs = [(name.strip(), float(value)) for name, value in PROB_RE.findall(block)]
        pick = PICK_RE.search(block)
        rows[match.group(1)] = {
            'team_percentages': [{'team': name, 'percent': value} for name, value in probs],
            'rendered_pick': pick.group(1).strip() if pick else None,
            'source_links': SRC_RE.findall(block),
        }
    return rows


def published_state(live_url: str, evidence_dir: Path | None = None) -> dict:
    stamp = now_iso().replace(':', '').replace('-', '')
    page = fetch(f'{live_url}/index.html?probe={stamp}')
    orig_page = fetch(f'{live_url}/origination/index.html?probe={stamp}')
    data = fetch(f'{live_url}/data/latest.json?probe={stamp}')
    picks_page = fetch(f'{live_url}/picks/index.html?probe={stamp}')

    page_stamp = None
    rendered = {}
    if page['body']:
        found = re.search(r'data-snapshot-generated="([^"]+)"', page['body'])
        page_stamp = found.group(1) if found else None
        text = flatten(page['body'])
        for key, pattern in (('picks_ready', r'(\d+)\s*picks ready'),
                             ('active', r'(\d+)\s*active Hotspawn CS2 fixtures'),
                             ('unresolved', r'(\d+)\s*unresolved'),
                             ('model_only', r'(\d+)\s*from a research model'),
                             ('money_backed', r'(\d+)\s*from an external betting line')):
            found = re.search(pattern, text)
            if found:
                rendered[key] = int(found.group(1))

    json_stamp, json_counts, json_status = None, None, None
    if data['status'] == 200 and data['body']:
        try:
            snapshot = json.loads(data['body'])
        except ValueError:
            snapshot = None
        if isinstance(snapshot, dict):
            json_stamp = snapshot.get('generated_at')
            json_counts = snapshot.get('counts')
            json_status = snapshot.get('run_status')

    rows = parse_rows(orig_page['body']) if orig_page['body'] else {}
    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        for name, record in (('index.html', page), ('origination.html', orig_page),
                             ('latest.json', data), ('picks.html', picks_page)):
            if record['body']:
                (evidence_dir / name).write_text(record['body'])
    return {
        'live_url': live_url,
        'observed_at': now_iso(),
        'index': {'status': page['status'], 'error': page['error'],
                  'data_snapshot_generated': page_stamp,
                  'age_hours': age_hours(page_stamp), 'rendered': rendered},
        'origination_page': {'status': orig_page['status'], 'rows_rendered': len(rows)},
        'picks_page': {'status': picks_page['status'], 'bytes': picks_page['bytes']},
        'data_latest_json': {'status': data['status'], 'error': data['error'],
                             'generated_at': json_stamp, 'age_hours': age_hours(json_stamp),
                             'counts': json_counts, 'run_status': json_status,
                             'page_vs_json_hours': (
                                 None if not (page_stamp and json_stamp) else
                                 round((datetime.fromisoformat(page_stamp.replace('Z', '+00:00')) -
                                        datetime.fromisoformat(json_stamp.replace('Z', '+00:00'))
                                        ).total_seconds() / 3600, 2))},
        'rendered_rows': rows,
    }


# --------------------------------------------------------------------------
# 2. Coverage of the freshly collected snapshot
# --------------------------------------------------------------------------


def coverage(snapshot: dict, origination: dict | None = None) -> dict:
    """Audit every active fixture against BOTH published feeds.

    The dashboard renders two lists: the featured list in ``data/latest.json``
    and the complete researched list in ``data/origination.json``. A fixture is
    covered for a reader when *either* feed carries a two-value probability
    pair and a pick; this function records which feed supplied it, because a
    fixture that is blank in the featured feed is not a gap if the complete
    list resolves it.
    """
    complete = {str(m.get('id')): (m.get('origination') or {})
                for m in (origination or {}).get('matches') or []}
    active = [m for m in snapshot.get('matches') or []
              if m.get('availability') in ACTIVE]
    rows, problems = [], []
    for match in active:
        fixture_id = str(match.get('id'))
        teams = [t.get('name') for t in match.get('teams') or []]
        featured = match.get('analysis') or match.get('origination') or {}
        research = complete.get(fixture_id) or {}
        chosen, feed = None, None
        for candidate, name in ((featured, 'featured'), (research, 'complete list')):
            probs = candidate.get('probabilities')
            if isinstance(probs, list) and len(probs) == 2:
                chosen, feed = candidate, name
                break
        chosen = chosen or {}
        probs = chosen.get('probabilities')
        pick = match.get('pick_index') if feed == 'featured' else chosen.get('pick_index')
        if pick is None and isinstance(probs, list) and len(probs) == 2:
            pick = 0 if probs[0] >= probs[1] else 1
        issues = []
        if len(teams) < 2 or not all(teams[:2]):
            issues.append('a team name is missing')
        if not isinstance(probs, list) or len(probs) != 2:
            issues.append('no two-value probability pair in either feed')
        elif not all(isinstance(v, (int, float)) and 0 < v < 1 for v in probs):
            issues.append('a probability is outside (0,1)')
        elif abs(sum(probs) - 1) > EPSILON:
            issues.append(f'probabilities sum to {sum(probs):.6f}')
        if pick not in (0, 1):
            issues.append('no directional pick')
        elif isinstance(probs, list) and len(probs) == 2 and probs[pick] < probs[1 - pick]:
            issues.append('pick points at the less likely team')
        source = chosen.get('source_url') or match.get('source_url')
        if not str(source).startswith('https://'):
            issues.append('no https source URL')
        method = chosen.get('method')
        if method not in MONEY_METHODS and method != 'model':
            issues.append(f'method {method!r} is neither money nor model')
        row = {
            'id': fixture_id, 'teams': teams, 'competition': match.get('competition'),
            'starts_at': match.get('starts_at'), 'availability': match.get('availability'),
            'feed': feed, 'method': method, 'source': chosen.get('source'),
            'source_url': chosen.get('source_url'),
            'hotspawn_url': match.get('source_url'),
            'probabilities': probs,
            'pick': None if pick not in (0, 1) or not isinstance(probs, list) or len(probs) != 2
                    else teams[pick],
            'issues': issues,
            'money_backed': method in MONEY_METHODS,
            'limitations': chosen.get('limitations') or [],
            'featured_blank': not (match.get('analysis') or {}).get('probabilities'),
            'research_stages': [
                {'stage': stage.get('stage'), 'status': stage.get('status')}
                for stage in (match.get('research') or [])
            ],
        }
        rows.append(row)
        if issues:
            problems.append(row)
    return {
        'active_count': len(active),
        'covered_count': sum(1 for r in rows if not r['issues']),
        'money_backed_count': sum(1 for r in rows if r['money_backed'] and not r['issues']),
        'model_only_count': sum(1 for r in rows if not r['money_backed'] and not r['issues']),
        'featured_blank_count': sum(1 for r in rows if r['featured_blank']),
        'problem_count': len(problems),
        'rows': rows, 'problems': problems,
    }


# --------------------------------------------------------------------------
# 3. Candidate book/exchange surfaces for model-only fixtures
# --------------------------------------------------------------------------


def probe_surfaces(team_names: list[str], timeout: int) -> list[dict]:
    out = []
    for name, url in CANDIDATE_SURFACES:
        record = fetch(url, timeout=timeout)
        body = record.pop('body') or ''
        lowered = body.lower()
        hits = [team for team in team_names if team and team.lower() in lowered]
        snippet = None
        if hits:
            index = lowered.find(hits[0].lower())
            snippet = body[max(0, index - 160):index + 240].replace('\n', ' ')[:400]
        record.update({
            'surface': name,
            'team_names_probed': len(team_names),
            'team_names_found': hits[:8],
            'hit_count': len(hits),
            'verbatim_snippet': snippet,
            'note': ('verbatim evidence only; no price is parsed or converted into a probability'),
        })
        out.append(record)
    return out


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def markdown(document: dict) -> str:
    published = document['published']
    cover = document['coverage']
    lines = [
        f"# Session arena-ca7e10e5 — published-state verification ({document['observed_at']})",
        '',
        'Read-only. No probability, pick or alias is written by this probe.',
        '',
        '## 1. What the public site is serving',
        '',
        '| What | Value |',
        '| --- | --- |',
        f"| Page `data-snapshot-generated` | `{published['index']['data_snapshot_generated']}` "
        f"(age {published['index']['age_hours']} h) |",
        f"| `data/latest.json` `generated_at` | `{published['data_latest_json']['generated_at']}` "
        f"(age {published['data_latest_json']['age_hours']} h) |",
        f"| Page vs JSON gap | {published['data_latest_json']['page_vs_json_hours']} h |",
        f"| Rendered active fixtures / picks / unresolved | "
        f"{published['index']['rendered'].get('active')} / "
        f"{published['index']['rendered'].get('picks_ready')} / "
        f"{published['index']['rendered'].get('unresolved')} |",
        f"| Rendered `origination` rows | {published['origination_page']['rows_rendered']} |",
        f"| HTTP status (index / origination / data) | {published['index']['status']} / "
        f"{published['origination_page']['status']} / {published['data_latest_json']['status']} |",
        '',
        '## 2. Coverage of the freshly collected snapshot',
        '',
        f"Snapshot `{document['snapshot']['generated_at']}`: **{cover['active_count']}** active "
        f"fixtures, **{cover['covered_count']}** with a pick and two probabilities, "
        f"**{cover['money_backed_count']}** from a money line, **{cover['model_only_count']}** "
        f"from a research model, **{cover['problem_count']}** with a problem, and "
        f"**{cover['featured_blank_count']}** blank in the featured feed but resolved by the "
        f"complete researched list.",
        '',
        '| Fixture | Competition | Feed | Method | Pick | Probabilities | Source |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in cover['rows']:
        probs = row['probabilities'] or []
        prob_text = ' / '.join(f'{p:.1%}' for p in probs) if len(probs) == 2 else '—'
        source = row['source_url'] or ''
        label = row['source'] or 'source'
        source_text = f'[{label}]({source})' if source else '—'
        lines.append(f"| {' vs '.join(row['teams'][:2])} | {row['competition'] or ''} | "
                     f"{row['feed'] or '**none**'} | {row['method'] or '—'} | "
                     f"{row['pick'] or '**none**'} | {prob_text} | {source_text} |")
    if cover['problems']:
        lines += ['', '### Rows with a problem', '']
        for row in cover['problems']:
            lines.append(f"- `{row['id']}` {' vs '.join(row['teams'][:2])} "
                         f"({row['competition'] or 'competition blank'}): "
                         f"{'; '.join(row['issues'])}")

    lines += ['', '## 3. Line research for fixtures resolved only by a research model', '',
              '| Surface | HTTP | Status | Team names found | Challenge |', '| --- | --- | --- | --- | --- |']
    for surface in document['surfaces']:
        found = ', '.join(surface['team_names_found'][:4]) or '—'
        lines.append(f"| [{surface['surface']}]({surface['url']}) | {surface['status']} | "
                     f"{surface['error'] or ('challenge' if surface['challenge'] else 'ok')} | "
                     f"{found} | {surface['challenge'] or '—'} |")
    snippets = [s for s in document['surfaces'] if s.get('verbatim_snippet')]
    if snippets:
        lines += ['', '### Verbatim snippets around the first team-name hit', '']
        for surface in snippets:
            lines += [f"**{surface['surface']}** — `{surface['url']}`", '',
                      '```', surface['verbatim_snippet'], '```', '']
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('data/research/ca7e10e5'))
    parser.add_argument('--live-url', default='https://buffedlizard55-lab.github.io/MaltaProj3')
    parser.add_argument('--timeout', type=int, default=20)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    snapshot = json.loads((args.data / 'latest.json').read_text())
    origination = json.loads((args.data / 'origination.json').read_text())
    cover = coverage(snapshot, origination)
    model_only = [row for row in cover['rows'] if not row['money_backed']]
    team_names = sorted({name for row in model_only for name in row['teams'][:2] if name})

    document = {
        'schema_version': 1,
        'session': 'arena-ca7e10e5',
        'observed_at': now_iso(),
        'environment': 'github-actions-runner',
        'policy': ('Read-only. Reads the public site and probes line sources; writes no '
                   'probability, pick or alias. A reachable page is not a price.'),
        'snapshot': {
            'generated_at': snapshot.get('generated_at'),
            'inventory_observed_at': snapshot.get('inventory_observed_at'),
            'coverage_complete': snapshot.get('coverage_complete'),
            'run_status': snapshot.get('run_status'),
            'counts': snapshot.get('counts'),
        },
        'published': published_state(args.live_url, args.out / 'live'),
        'coverage': cover,
        'model_only_ids': [row['id'] for row in model_only],
        'surfaces': probe_surfaces(team_names, args.timeout),
    }
    # The rendered rows are evidence for section 1 only; keep the JSON small
    # by replacing the full table with the ids and percentages it carried.
    published_rows = document['published'].pop('rendered_rows', {})
    document['published']['rendered_sample'] = {
        key: published_rows[key] for key in list(published_rows)[:40]
    }

    (args.out / 'published-and-coverage.json').write_text(
        json.dumps(document, indent=1, ensure_ascii=False) + '\n')
    (args.out / 'published-and-coverage.md').write_text(markdown(document))

    print(f"published page {document['published']['index']['data_snapshot_generated']} | "
          f"json {document['published']['data_latest_json']['generated_at']} | "
          f"active {cover['active_count']} covered {cover['covered_count']} "
          f"model-only {cover['model_only_count']} problems {cover['problem_count']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
