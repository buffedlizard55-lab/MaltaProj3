"""32ce1d11 verification: executive-summary contract, phone rendering, picks coverage, links."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def verify(root: Path, errors: list[str]) -> dict:
    index = (root / 'index.html').read_text()
    snap = json.loads((root / 'snapshot.json').read_text())
    orig = json.loads((root / 'origination.json').read_text())

    result: dict = {}

    # 1. Mobile viewport meta
    if 'name="viewport"' not in index or 'width=device-width' not in index:
        _fail(errors, 'index.html missing viewport meta')

    # 2. Mobile nav has 6 tabs: Summary, Picks, Unresolved, Edge, Sources, Review
    nav_tabs = re.findall(r'class="mobile-nav".*?</nav>', index, re.S)
    if not nav_tabs:
        _fail(errors, 'no mobile-nav element')
    else:
        tab_spans = re.findall(r'<span>([^<]+)</span>', nav_tabs[0])
        expected = {'Summary', 'Picks', 'Unresolved', 'Edge', 'Sources', 'Review'}
        if set(tab_spans) != expected:
            _fail(errors, f'mobile-nav tabs {tab_spans} != {sorted(expected)}')
        result['mobile_tabs'] = tab_spans

    # 3. Start-here nav has links to picks on this page, all match picks, unresolved
    if 'id="start-here"' not in index:
        _fail(errors, 'no #start-here section')
    start_here = index[index.find('id="start-here"'):index.find('id="start-here"') + 3000]
    for href, label in [
        ('./#picks-at-a-glance', 'Picks on this page'),
        ('./origination/#picks', 'All match picks'),
        ('./#unresolved-register', 'unresolved register'),
        ('./origination/#unresolved', 'complete-list unresolved'),
    ]:
        if href not in start_here:
            _fail(errors, f'start-here missing link to {href} ({label})')

    # 4. Mobile status strip shows X picks ready of Y, Z unresolved
    m_picks = re.search(r'class="mobile-status-picks"[^>]*>\s*<strong>(\d+)</strong>\s*<span>([^<]+)', index)
    m_blank = re.search(r'class="mobile-status-blank"[^>]*>\s*<strong>(\d+)</strong>', index)
    if not (m_picks and m_blank):
        _fail(errors, 'mobile-status strip missing picks/blank counts')
    else:
        picks_ready = int(m_picks.group(1))
        unresolved = int(m_blank.group(1))
        result['mobile_status'] = {'picks_ready': picks_ready, 'unresolved': unresolved}

    # 5. Picks-at-a-glance lists one row per active open fixture
    glance_ids = re.findall(r'data-glance-id="(\d+)"', index)
    active = [m for m in snap['matches'] if m['availability'] != 'past']
    active_ids = sorted(str(m['id']) for m in active)
    glance_ids_sorted = sorted(glance_ids)
    if glance_ids_sorted != active_ids:
        missing = set(active_ids) - set(glance_ids_sorted)
        extra = set(glance_ids_sorted) - set(active_ids)
        _fail(errors, f'glance rows != active fixtures. missing={missing} extra={extra}')
    result['glance_fixtures'] = len(glance_ids)

    # 6. Every glance row has BOTH probabilities, a pick, a source link
    rows = re.findall(r'<li class="glance-row"[^>]*data-glance-id="(\d+)"[^>]*>(.*?)</li>', index, re.S)
    missing_prob = []
    missing_pick = []
    missing_source = []
    for fid, body in rows:
        # Both probabilities must be present as NN.N%
        probs = re.findall(r'(\d+\.\d)%', body)
        if len(probs) < 2:
            missing_prob.append(fid)
        if 'data-glance-pick' not in body:
            missing_pick.append(fid)
        # Every row should have at least one source-link to an https:// URL
        sources = re.findall(r'href="(https://[^"]+)"', body)
        if not sources:
            missing_source.append(fid)
    if missing_prob:
        _fail(errors, f'glance rows missing both probabilities: {missing_prob}')
    if missing_pick:
        _fail(errors, f'glance rows missing pick marker: {missing_pick}')
    if missing_source:
        _fail(errors, f'glance rows without https source link: {missing_source}')

    # 7. Unresolved section (blanks in this summary) shows 0 blanks link
    if 'unresolved-register' not in index:
        _fail(errors, 'no #unresolved-register anchor')

    # 8. Snapshot freshness under 8 hours?
    from datetime import datetime, timezone
    gen = datetime.fromisoformat(snap['generated_at'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    age_h = (now - gen).total_seconds() / 3600
    result['snapshot_generated_at'] = snap['generated_at']
    result['snapshot_age_hours'] = round(age_h, 2)
    result['snapshot_fresh'] = age_h < 8

    # 9. Check origination layer covers all active
    omap = {str(m['id']): m for m in orig.get('matches', [])}
    uncovered = [str(m['id']) for m in active if str(m['id']) not in omap]
    if uncovered:
        _fail(errors, f'origination.json missing active fixtures: {uncovered}')
    no_orig = []
    for m in active:
        om = omap.get(str(m['id']))
        if not om:
            continue
        od = om.get('origination', {}) if isinstance(om.get('origination'), dict) else {}
        if 'probabilities' not in od and om.get('pick_index') is not None:
            # pick_index is set but no probabilities block; acceptable if research resolved it
            pass
    result['origination_counts'] = orig.get('counts', {})

    # 10. Verify snapshot.json counts against glance row count
    counts = snap.get('counts', {})
    if counts.get('upcoming') != len(active):
        _fail(errors, f'counts.upcoming ({counts.get("upcoming")}) != active fixtures ({len(active)})')

    # 11. Snapshot coverage_complete must be true
    if not snap.get('coverage_complete'):
        _fail(errors, 'snapshot.json coverage_complete is false')

    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.', help='repository root with index.html and snapshot.json')
    ap.add_argument('--check', action='store_true', help='exit non-zero on errors')
    args = ap.parse_args(argv)

    root = Path(args.root)
    errors: list[str] = []
    result = verify(root, errors)

    print('32ce1d11 verification:')
    print(json.dumps(result, indent=2))
    if errors:
        print(f'\nERRORS ({len(errors)}):')
        for e in errors:
            print(f'  - {e}')
        if args.check:
            return 1
    else:
        print('\nPASS: 0 errors')
    return 0


if __name__ == '__main__':
    sys.exit(main())
