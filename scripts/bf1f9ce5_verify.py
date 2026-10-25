"""Independent offline verifier for session arena-bf1f9ce5.

Checks four contracts without making any network calls or pinning mutable
`snapshot.json` timestamps:
1. Import safety of `scripts/audit_sources.py` and `scripts/discover_sources.py`
   (no top-level network calls, sleeps, or `.mkdir()` outside `def main()`).
2. Exact Hotspawn cached `/lobby` vs cache-busted `/lobby?cb=` vs scheduled API
   reconciliation and 17/17 fresh origination arithmetic in
   `data/research/bf1f9ce5/fresh-reconciliation.json` + `live-coverage.json`.
3. HLTV-first + multi-book/exchange gap dossier integrity in
   `data/research/bf1f9ce5/line-source-research.json` (no hand-written picks or
   derived probabilities; SHA-256 digests and fan-poll exclusion intact).
4. Snapshot-independent replay of whatever `snapshot.json` is currently checked
   in (every picked match sums to 1.0, picks the higher-probability team, cites
   external `https://` sources, never uses Hotspawn `% picked` or HLTV fan
   polls, and every upcoming unresolved match carries `https://` research and
   explicit limitations).
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / 'data' / 'research' / 'bf1f9ce5'
FORBIDDEN_PROB_HOSTS = ('hotspawn.com', 'play.hotspawn.com')
FORBIDDEN_TEXT_MARKERS = ('% picked', 'community vote', 'fan poll probability')


def verify_import_guards(paths: list[Path] | None = None) -> list[str]:
    targets = paths or [
        ROOT / 'scripts' / 'audit_sources.py',
        ROOT / 'scripts' / 'discover_sources.py',
    ]
    errors: list[str] = []
    forbidden_calls = {'urlopen', 'fetch', 'sleep', 'mkdir', 'write_text', 'write_bytes'}

    for path in targets:
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        has_main_def = False
        has_name_guard = False
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == 'main':
                has_main_def = True
                continue
            if isinstance(node, ast.If):
                test_src = ast.unparse(node.test)
                if '__name__' in test_src and '__main__' in test_src:
                    has_name_guard = True
                    continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.FunctionDef):
                    break
                if isinstance(sub, ast.Call):
                    fn = sub.func
                    call_name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else '')
                    if call_name in forbidden_calls:
                        errors.append(f'{path.name}: top-level call to {call_name}() at line {sub.lineno}')
        if not has_main_def:
            errors.append(f'{path.name}: missing def main()')
        if not has_name_guard:
            errors.append(f'{path.name}: missing if __name__ == "__main__": guard')
    return errors


def verify_live_reconciliation(recon: dict | None = None, coverage: dict | None = None) -> list[str]:
    data = recon if recon is not None else json.loads((RESEARCH_DIR / 'fresh-reconciliation.json').read_text(encoding='utf-8'))
    cov = coverage if coverage is not None else json.loads((RESEARCH_DIR / 'live-coverage.json').read_text(encoding='utf-8'))
    errors: list[str] = []

    hs = data.get('hotspawn_surfaces') or {}
    cached = hs.get('lobby_cached') or {}
    fresh = hs.get('lobby_fresh') or {}
    cs2_fresh = hs.get('cs2_pickems_fresh') or {}
    api = hs.get('scheduled_api') or {}

    if cached.get('total_cs2') != 80 or cached.get('cache_status') != 'HIT':
        errors.append('cached /lobby expected 80 CS2 fixtures on edge cache HIT')
    if fresh.get('total_cs2') != 78 or fresh.get('cache_status') != 'MISS':
        errors.append('cache-busted /lobby?cb= expected 78 CS2 fixtures on cache MISS')
    if cs2_fresh.get('total_cs2') != 78 or api.get('total_cs2') != 78:
        errors.append('cache-busted /cs2-pickems?cb= and scheduled_api expected 78 CS2 fixtures')

    cached_only = sorted(set(cached.get('ids') or []) - set(api.get('ids') or []))
    if cached_only != ['1079198', '1081156']:
        errors.append(f'unexpected cached-only lobby fixture IDs: {cached_only}')
    if set(fresh.get('ids') or []) != set(api.get('ids') or []):
        errors.append('cache-busted /lobby?cb= IDs do not match scheduled API IDs 78-for-78')
    if set(cs2_fresh.get('ids') or []) != set(api.get('ids') or []):
        errors.append('cache-busted /cs2-pickems?cb= IDs do not match scheduled API IDs 78-for-78')

    rows = data.get('arithmetic_and_provenance') or []
    if len(rows) != 17:
        errors.append(f'expected 17 active originated fixtures, found {len(rows)}')
    for row in rows:
        fid = str(row.get('id'))
        probs = row.get('probabilities') or []
        if len(probs) != 2 or abs(float(probs[0]) + float(probs[1]) - 1.0) > 1e-6:
            errors.append(f'{fid}: probabilities {probs} do not sum to 1.0')
            continue
        pidx = row.get('pick_index')
        if pidx not in (0, 1):
            errors.append(f'{fid}: missing pick_index')
            continue
        other = 1 - pidx
        if float(probs[pidx]) + 1e-9 < float(probs[other]):
            errors.append(f'{fid}: pick_index {pidx} is lower probability ({probs})')
        src = str(row.get('source_url') or '')
        if not src.startswith('https://'):
            errors.append(f'{fid}: source_url is not https:// ({src!r})')
        if any(host in src for host in FORBIDDEN_PROB_HOSTS):
            errors.append(f'{fid}: forbidden Hotspawn probability source {src!r}')

    live_rows = cov.get('live_fixtures') or []
    if len(live_rows) != 17:
        errors.append(f'live-coverage.json expected 17 live_fixtures, found {len(live_rows)}')
    return errors


def verify_line_research(dossier: dict | None = None) -> list[str]:
    doc = dossier if dossier is not None else json.loads((RESEARCH_DIR / 'line-source-research.json').read_text(encoding='utf-8'))
    errors: list[str] = []

    if doc.get('environment') != 'github-actions-runner':
        errors.append(f"unexpected environment: {doc.get('environment')!r}")
    per_fixture = doc.get('per_fixture') or []
    if len(per_fixture) != 5:
        errors.append(f'expected 5 non-market model targets, found {len(per_fixture)}')

    hltv_checked = 0
    for item in per_fixture:
        fid = str(item.get('id'))
        if 'probabilities' in item or 'pick_index' in item:
            errors.append(f'{fid}: line-source-research must not carry hand-written probabilities or pick_index')
        hp = item.get('hltv_page')
        if hp is not None:
            hltv_checked += 1
            if hp.get('http_status') != 200 or not hp.get('sha256'):
                errors.append(f'{fid}: HLTV match page missing HTTP 200 or sha256')
            if hp.get('bookmaker_decimal_rows_count') != 0:
                errors.append(f"{fid}: unexpected HLTV decimal rows {hp.get('bookmaker_decimal_rows_count')}")
            if hp.get('fan_poll_present_and_excluded') is not True:
                errors.append(f'{fid}: fan_poll_present_and_excluded must be True')
    if hltv_checked != 4:
        errors.append(f'expected 4 live HLTV match pages among the 5 targets, found {hltv_checked}')
    return errors


def verify_current_snapshot(snap: dict | None = None) -> list[str]:
    doc = snap if snap is not None else json.loads((ROOT / 'snapshot.json').read_text(encoding='utf-8'))
    errors: list[str] = []

    if doc.get('refresh_interval_hours') != 4 or doc.get('stale_after_hours') != 8:
        errors.append('snapshot refresh contract must stay 4h refresh / 8h stale bound')

    for match in doc.get('matches') or []:
        fid = str(match.get('id'))
        analysis = match.get('analysis')
        raw_blob = json.dumps(analysis or {}, sort_keys=True).lower()
        for marker in FORBIDDEN_TEXT_MARKERS:
            if marker in raw_blob:
                errors.append(f'{fid}: forbidden crowd/poll marker {marker!r} in analysis')

        pidx = match.get('pick_index')
        if pidx in (0, 1):
            probs = (analysis or {}).get('probabilities') or match.get('probabilities') or []
            if len(probs) != 2 or abs(float(probs[0]) + float(probs[1]) - 1.0) > 1e-5:
                errors.append(f'{fid}: picked match probabilities {probs} do not sum to 1.0')
                continue
            if float(probs[pidx]) + 1e-9 < float(probs[1 - pidx]):
                errors.append(f'{fid}: pick_index {pidx} contradicts {probs}')
            src = str((analysis or {}).get('source_url') or match.get('source_url') or '')
            if not src.startswith('https://') or any(h in src for h in FORBIDDEN_PROB_HOSTS):
                errors.append(f'{fid}: invalid or Hotspawn probability source {src!r}')
        elif match.get('window') == 'upcoming' or match.get('is_upcoming') is True:
            if not match.get('limitations'):
                errors.append(f'{fid}: unresolved upcoming match lacks explicit limitations')
            stages = match.get('research') or []
            if not stages or not all(str(s.get('source_url', '')).startswith('https://') for s in stages):
                errors.append(f'{fid}: unresolved upcoming match lacks https:// research trail')
    return errors


def main() -> int:
    all_errors = (
        verify_import_guards()
        + verify_live_reconciliation()
        + verify_line_research()
        + verify_current_snapshot()
    )
    if all_errors:
        for err in all_errors:
            print('FAIL:', err)
        return 1
    print('PASS: bf1f9ce5 import-safety, 78/78 cache-busted Hotspawn parity, 17/17 pick replay, HLTV-first dossier, and snapshot invariants verified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
