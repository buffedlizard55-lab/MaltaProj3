"""Independent source-side verification for session arena-39680a42 (tasks 3968-1 / 3968-3).

What this checks, and why
-------------------------
The deployed dashboard already publishes a pick and two probabilities for nearly
every open Hotspawn CS2 fixture.  This session's slice of the brief is not to make
more picks but to re-check the ones the site is already serving, against the
sources the site itself names.  Four groups of checks, all replayable offline from
checked-in files:

1. **Published arithmetic** — for every active row in `snapshot.json` that carries
   an `analysis`, the two probabilities must sum to 1 (1e-6), and the published
   `pick_index` must name the larger side unless the pair is exactly even.  A row
   with no `analysis` is recorded as unresolved rather than treated as an error:
   leaving a value blank is the project's rule, not a failure.

2. **Source-link contract** — every active row's `analysis.source_url` must be an
   `https://` URL, must not be a Hotspawn pickems page (Hotspawn lists fixtures; it
   is never a probability input), and must not be an HLTV fan-vote surface.  The
   host is recorded so a reader can re-open each link by hand.

3. **The 1082792 identity chain** — the deployed executive summary carries a
   researched row for `1082792` while `snapshot.json`'s featured exact-name layer
   records the same fixture as unresolved.  The chain behind that row is checked
   against `identity-chain-1082792.json`: the three independent sources (Hotspawn
   fixture, Polymarket event, HLTV match page) must agree on the start time, and the
   Polymarket event must actually name both teams.

4. **Live coverage reconciliation** — the captured live lobby
   (`live-lobby-snapshot.json`) is compared with the snapshot's upcoming set.  Every
   fixture Hotspawn lists and the deployed snapshot does not serve is named with its
   id, so the gap is visible rather than implied.

Nothing here writes a probability, a pick or an alias.  A failure means a published
claim is untrue of the tree, not that a number should be changed.

CLI
---
    python -m scripts.39680a42_verify            # run all checks
    python -m scripts.39680a42_verify --write    # also write verification.json
    python -m scripts.39680a42_verify --check     # exit 1 on any error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'snapshot.json'
INDEX_HTML = ROOT / 'index.html'
DOSSIER = ROOT / 'data' / 'research' / '39680a42'
LIVE_LOBBY = DOSSIER / 'live-lobby-snapshot.json'
IDENTITY = DOSSIER / 'identity-chain-1082792.json'
OUT = DOSSIER / 'verification.json'

TOL = 1e-6
HOTSPAWN_HOSTS = {'play.hotspawn.com', 'hotspawn.com', 'www.hotspawn.com'}
HLTV_FAN_VOTE_HOSTS = {'www.hltv.org'}
HLTV_FAN_VOTE_PATHS = ('/vote', '/match/vote')
ACTIVE_AVAILABILITY = ('open', 'locked', 'unknown_lock')


def _load(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def _host(url: str) -> str:
    return urlparse(url).netloc.removeprefix('www.').lower()


# ---------------------------------------------------------------- check 1
def check_published_arithmetic(snapshot: dict) -> list[str]:
    errors: list[str] = []
    active = [m for m in snapshot.get('matches', []) if m.get('availability') in ACTIVE_AVAILABILITY]
    priced, unresolved = [], []
    for m in active:
        m_id = m.get('id')
        analysis = m.get('analysis')
        if not analysis:
            unresolved.append(m_id)
            continue
        probs = analysis.get('probabilities')
        if not isinstance(probs, list) or len(probs) != 2:
            errors.append(f'{m_id}: probabilities must be a pair, got {probs!r}')
            continue
        total = probs[0] + probs[1]
        if abs(total - 1.0) > TOL:
            errors.append(f'{m_id}: probabilities sum to {total!r}, not 1')
        pick = m.get('pick_index')
        if pick is None:
            errors.append(f'{m_id}: priced row has no pick_index')
        elif pick not in (0, 1):
            errors.append(f'{m_id}: pick_index {pick!r} is not 0 or 1')
        elif abs(probs[0] - probs[1]) > TOL and pick != (0 if probs[0] >= probs[1] else 1):
            errors.append(f'{m_id}: pick_index {pick} does not name the larger side')
        priced.append(m_id)
    return errors, {'active': len(active), 'priced': priced, 'unresolved': unresolved}


# ---------------------------------------------------------------- check 2
def check_source_links(snapshot: dict) -> list[str]:
    errors: list[str] = []
    rows = []
    for m in snapshot.get('matches', []):
        if m.get('availability') not in ACTIVE_AVAILABILITY:
            continue
        analysis = m.get('analysis')
        if not analysis:
            rows.append({'id': m.get('id'), 'source_url': None, 'host': None,
                         'method': None, 'blocker': 'unresolved'})
            continue
        url = analysis.get('source_url') or ''
        host = _host(url)
        rows.append({'id': m.get('id'), 'source_url': url, 'host': host,
                     'method': analysis.get('method'), 'blocker': None})
        if not url.startswith('https://'):
            errors.append(f"{m.get('id')}: source_url is not https: {url!r}")
        if host in HOTSPAWN_HOSTS:
            errors.append(f'{m.get("id")}: probability source is a Hotspawn page ({host}); '
                          'Hotspawn lists fixtures, it is never a probability input')
        if host in HLTV_FAN_VOTE_HOSTS and any(p in urlparse(url).path.lower() for p in HLTV_FAN_VOTE_PATHS):
            errors.append(f'{m.get("id")}: source_url is an HLTV fan-vote surface ({url!r})')
    return errors, rows


# ---------------------------------------------------------------- check 3
def check_identity_chain(identity: dict, exec_row: dict | None) -> list[str]:
    errors: list[str] = []
    if not identity:
        return ['identity-chain-1082792.json is missing; the researched row cannot be re-checked']
    hot = identity.get('hotspawn_fixture', {})
    poly = identity.get('polymarket_event', {})
    hltv = identity.get('hltv_match', {})
    starts = {'hotspawn': hot.get('starts_at'), 'polymarket': poly.get('eventStartTime'),
              'hltv': hltv.get('start_iso') or hltv.get('start')}
    if len(set(starts.values())) != 1:
        errors.append(f'1082792: the three sources disagree on the start time: {starts}')
    outcomes = [str(x).lower() for x in (poly.get('outcomes') or [])]
    teams = [str(x).lower() for x in hot.get('teams', [])]
    outcomes_blob = ' '.join(outcomes)
    unnamed = [t for t in teams if t.split()[0] not in outcomes_blob]
    if unnamed:
        errors.append(f'1082792: Polymarket outcomes {poly.get("outcomes")} do not name fixture teams {unnamed}')
    if hltv.get('format') and 'bo3' not in str(hltv.get('format', '')).upper() and 'best of 3' not in str(hltv.get('format', '')).lower():
        errors.append(f'1082792: HLTV format {hltv.get("format")!r} is not a BO3')
    if exec_row:
        cited = exec_row.get('source_link', '')
        if poly.get('slug') and poly['slug'] not in cited:
            errors.append(f'1082792: executive summary cites {cited!r}, not the Polymarket event '
                          f'{poly.get("slug")!r} recorded in the dossier')
    return errors


# ---------------------------------------------------------------- check 4
def check_coverage_reconciliation(snapshot: dict, live: dict) -> list[str]:
    errors: list[str] = []
    if not live:
        return ['live-lobby-snapshot.json is missing; the live gap cannot be reconciled']
    upcoming = {m.get('id') for m in snapshot.get('matches', [])
                if m.get('availability') in ACTIVE_AVAILABILITY}
    lobby = set(live.get('lobby_open_ids', []))
    expected_gap = set(live.get('coverage_gap_ids', []))
    actual_gap = sorted(lobby - upcoming)
    if set(actual_gap) != expected_gap:
        errors.append(f'coverage gap drift: lobby-minus-snapshot is {actual_gap}, dossier records {sorted(expected_gap)}')
    for m_id in actual_gap:
        if m_id in upcoming:
            errors.append(f'{m_id}: listed as both covered and uncovered')
    # every fixture in the deployed snapshot's upcoming set must be in the live lobby
    drifted = sorted(upcoming - lobby)
    if drifted:
        errors.append(f'snapshot rows that are no longer in the live lobby: {drifted}')
    return errors, {'upcoming': len(upcoming), 'lobby_open': len(lobby),
                    'gap': actual_gap, 'snapshot_only': drifted}


# ---------------------------------------------------------------- check 5
def check_executive_summary(index_html: str) -> list[str]:
    errors: list[str] = []
    if not index_html:
        return ['index.html is missing; the executive-summary contract cannot be checked']
    missing = [marker for marker in ('start-here', 'picks-at-a-glance', 'unresolved-register',
                                     'no-line-register', 'fallback-register')
               if f'id="{marker}"' not in index_html]
    if missing:
        errors.append(f'executive summary is missing landmark ids: {missing}')
    for target in ('./picks/', './unresolved/', './origination/#picks'):
        if target not in index_html:
            errors.append(f'executive summary does not link {target}')
    rows = re.findall(r'<li class="glance-row" data-glance-id="([^"]+)"[^>]*>(.*?)</li>',
                      index_html, flags=re.S)
    if not rows:
        errors.append('executive summary has no glance rows to check')
    for m_id, body in rows:
        if 'glance-pick-label' not in body:
            errors.append(f'glance row {m_id} has no pick label')
        if len(re.findall(r'glance-prob"[^>]*>', body)) < 1:
            errors.append(f'glance row {m_id} shows no win probability')
        if 'glance-other' not in body:
            errors.append(f'glance row {m_id} shows no opposing probability')
        if 'source-link' not in body:
            errors.append(f'glance row {m_id} has no source link')
    return errors, {'glance_rows': len(rows)}


def run(write: bool = False) -> dict:
    snapshot = _load(SNAPSHOT) or {}
    live = _load(LIVE_LOBBY)
    identity = _load(IDENTITY)
    index_html = INDEX_HTML.read_text(encoding='utf-8') if INDEX_HTML.exists() else ''

    arithmetic_errors, arithmetic = check_published_arithmetic(snapshot)
    link_errors, rows = check_source_links(snapshot)
    identity_errors = check_identity_chain(identity, identity.get('deployed_executive_summary_row') if identity else None)
    coverage_errors, coverage = check_coverage_reconciliation(snapshot, live)
    summary_errors, summary = check_executive_summary(index_html)

    errors = arithmetic_errors + link_errors + identity_errors + coverage_errors + summary_errors
    result = {
        'session': 'arena-39680a42',
        'checks': {
            'published_arithmetic': {'errors': arithmetic_errors, **arithmetic},
            'source_links': {'errors': link_errors, 'rows': rows},
            'identity_chain_1082792': {'errors': identity_errors},
            'coverage_reconciliation': {'errors': coverage_errors, **coverage},
            'executive_summary_contract': {'errors': summary_errors, **summary},
        },
        'errors': errors,
        'source_urls': [
            'https://buffedlizard55-lab.github.io/MaltaProj3/',
            'https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json',
            'https://play.hotspawn.com/lobby',
            'https://gamma-api.polymarket.com/events?slug=cs2-hotu-the9-2026-10-31',
            'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
        ],
    }
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true', help='also write verification.json')
    ap.add_argument('--check', action='store_true', help='exit 1 if any error')
    args = ap.parse_args(argv)
    result = run(write=args.write)
    for name, block in result['checks'].items():
        status = 'ok' if not block.get('errors') else f'{len(block["errors"])} error(s)'
        print(f'{name}: {status}')
        for err in block.get('errors', []):
            print(f'    - {err}')
    print(f'\n{len(result["errors"])} error(s) total')
    return 1 if (args.check and result['errors']) else 0


if __name__ == '__main__':
    sys.exit(main())
