"""Independent verification for session arena-c0bba79a (tasks C0B-1 / C0B-3).

Three groups of checks, all replayable offline from checked-in files:

1. **Dossier arithmetic** — `data/research/c0bba79a/live-reconciliation.json`
   must be internally consistent: the snapshot's 18 upcoming ids partition
   exactly into 13 still-open + 4 started-and-dropped + 1 in-play, the API
   total equation 79 - 4 + 3 = 78 must hold, and the lobby open set must equal
   the API future set.

2. **Snapshot binding (date-guarded)** — when (and only when) the checked-in
   `snapshot.json` is the snapshot the dossier names (`2026-10-25T05:12:25Z`),
   its upcoming id set must equal the dossier's list, and every still-open
   dossier id must be present.  For any newer snapshot the structural invariants
   still run: `counts` must add up (`inventory == upcoming + archived` and the
   featured method's parts must not exceed `upcoming`) and every active row
   with an analysis must carry two probabilities summing to 1 within 1e-6 with
   a named side unless the pair is exactly even.  Publisher output is never
   *pinned* — it is only ever checked against the dossier that names it.

3. **Rendered executive-summary contract** — in a built `site/` (when present):
   the landing page must link the in-site picks routes, carry the separate
   unresolved/limitations register, give every glance row a state marker, and
   hold each of the landmark ids exactly once.

Nothing here writes a probability, a pick or an alias.  A failure means a
claim in the dossier (or the rendered contract) is untrue of the tree, not
that a number should be changed.

CLI
---
    python -m scripts.c0bba79a_verify            # run all checks
    python -m scripts.c0bba79a_verify --write     # also write verification.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data' / 'research' / 'c0bba79a' / 'live-reconciliation.json'
SNAPSHOT = ROOT / 'snapshot.json'
OUT = ROOT / 'data' / 'research' / 'c0bba79a' / 'verification.json'
DOSSIER_SNAPSHOT_GENERATED = '2026-10-25T05:12:25Z'
TOL = 1e-6


def _load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def check_dossier_arithmetic(dossier: dict) -> list[str]:
    """The recorded reconciliation must be arithmetically and set-consistent."""
    errors: list[str] = []
    rec = dossier.get('reconciliation') or {}
    upcoming = rec.get('snapshot_upcoming_18') or []
    still = rec.get('snapshot_still_open_13') or []
    dropped = rec.get('snapshot_started_and_dropped_from_api_4') or []
    inplay = rec.get('snapshot_in_play_api_only_1') or []
    new = rec.get('open_on_live_site_but_absent_from_deployed_snapshot_3') or []

    if len(upcoming) != 18:
        errors.append(f'dossier upcoming list has {len(upcoming)} entries, expected 18')
    if len(still) != 13:
        errors.append(f'dossier still-open list has {len(still)} entries, expected 13')
    if len(dropped) != 4:
        errors.append(f'dossier dropped list has {len(dropped)} entries, expected 4')
    if len(inplay) != 1:
        errors.append(f'dossier in-play list has {len(inplay)} entries, expected 1')
    if len(new) != 3:
        errors.append(f'dossier new-fixture list has {len(new)} entries, expected 3')

    parts = still + dropped + inplay
    if sorted(parts) != sorted(upcoming):
        errors.append('the 13 + 4 + 1 partitions do not cover the 18 upcoming ids exactly')
    if len(set(parts)) != len(parts):
        errors.append('the partition lists overlap')
    if set(new) & set(upcoming):
        errors.append('a "new" fixture is also in the deployed upcoming list')

    obs = {o['kind']: o for o in dossier.get('observations', [])}
    api = obs.get('official Hotspawn scheduled-fixtures API')
    if api:
        total = api['figures'].get('records_total')
        if total != 78:
            errors.append(f'API record total recorded as {total}, expected 78')
        future = api['figures'].get('open_count')
        if future != 17:
            errors.append(f'API open count recorded as {future}, expected 17 (16 future + 1 in play)')
        ids = api['figures'].get('open_or_in_play_ids') or []
        if len(ids) != 17 or len(set(ids)) != 17:
            errors.append('API open id list must hold 17 unique ids')
        if sorted(set(ids) - set(upcoming)) != sorted(new):
            errors.append('API ids beyond the deployed upcoming set are not exactly the 3 new fixtures')

    lobby = obs.get("rendered pick'em lobby (the reverse-engineering target)")
    if lobby:
        cards = lobby['figures'].get('rendered_open_card_ids') or []
        if len(cards) != 16 or len(set(cards)) != 16:
            errors.append('lobby open card list must hold 16 unique ids')
        if lobby['figures'].get('rendered_open_cards') != 16:
            errors.append('lobby rendered open card count must be 16')
        if sorted(cards) != sorted(set(cards)):
            errors.append('lobby card ids repeat')
        # The lobby's open set is exactly the API's future set (16), i.e. the
        # in-play 1085542 is API-only by construction.
        if api:
            future_only = sorted(set(api['figures'].get('open_or_in_play_ids') or []) - set(inplay))
            if sorted(cards) != future_only:
                errors.append('lobby open set does not equal the API future set')

    # The recorded equation must hold symbolically.
    published = obs.get('published snapshot')
    if published:
        counts = published['figures'].get('counts') or {}
        inv, up, arch = counts.get('inventory'), counts.get('upcoming'), counts.get('archived')
        if inv is not None and up is not None and arch is not None and inv != up + arch:
            errors.append(f'deployed counts do not add: inventory {inv} != {up} + {arch}')
        if inv is not None and inv - len(dropped) + len(new) != 78:
            errors.append('equation 79 - 4 + 3 = 78 does not hold for the recorded sets')
    return errors


def check_snapshot_binding(dossier: dict, snapshot: dict) -> list[str]:
    """Date-guarded equality for the named snapshot; structural invariants always."""
    errors: list[str] = []
    rec = dossier.get('reconciliation') or {}
    upcoming = rec.get('snapshot_upcoming_18') or []
    still = set(rec.get('snapshot_still_open_13') or [])

    matches = snapshot.get('matches') or []
    counts = snapshot.get('counts') or {}

    # Structural: counts add up.
    inv, up, arch = counts.get('inventory'), counts.get('upcoming'), counts.get('archived')
    if None not in (inv, up, arch) and inv != up + arch:
        errors.append(f'snapshot counts do not add: {inv} != {up} + {arch}')

    active = [m for m in matches if m.get('availability') != 'past']
    # Structural: every active row with an analysis carries a consistent pair.
    for m in active:
        a = m.get('analysis')
        if not a:
            continue
        prob = a.get('probabilities')
        if not isinstance(prob, (list, tuple)) or len(prob) != 2:
            errors.append(f'{m.get("id")}: analysis without a two-element probability pair')
            continue
        if abs(sum(prob) - 1.0) > TOL:
            errors.append(f'{m.get("id")}: probabilities sum to {sum(prob)}')
        if any(not (0.0 < float(p) < 1.0) for p in prob):
            errors.append(f'{m.get("id")}: probability outside (0, 1)')
        pi = m.get('pick_index')
        if pi is not None and pi not in (0, 1):
            errors.append(f'{m.get("id")}: pick_index {pi} is not 0, 1 or null')
        if pi is not None and prob[0] != prob[1] and prob[int(pi)] != max(prob):
            errors.append(f'{m.get("id")}: pick_index does not name the larger side')

    # Date-guarded equality with the dossier's named snapshot only.
    if snapshot.get('generated_at') == DOSSIER_SNAPSHOT_GENERATED:
        snap_up = [m['id'] for m in active]
        if sorted(snap_up) != sorted(upcoming):
            errors.append('named snapshot upcoming set differs from the dossier list')
        allowed_blank = set(rec.get('still_open_without_featured_analysis') or [])
        missing = [i for i in still
                   if not any(m.get('analysis') for m in active if m.get('id') == i)]
        if set(missing) - allowed_blank:
            errors.append(f'still-open ids without featured analysis and without a recorded complete-layer pick: {sorted(set(missing) - allowed_blank)}')
        if allowed_blank - set(missing):
            errors.append(f'recorded complete-layer id unexpectedly has featured analysis: {sorted(allowed_blank - set(missing))}')
    return errors


def check_rendered_summary(site: Path) -> list[str]:
    """The landing page contract the brief asks for on a phone, one tap away."""
    errors: list[str] = []
    index = site / 'index.html'
    if not index.exists():
        return [f'{index} not built (run python -m scripts.build first)']
    html = index.read_text(encoding='utf-8')

    for landmark in ('id="start-here"', 'id="unresolved-register"'):
        n = html.count(landmark)
        if n != 1:
            errors.append(f'{landmark} appears {n} times, expected exactly 1')

    for route in ('./picks/', './unresolved/', 'origination/#picks'):
        if route not in html:
            errors.append(f'executive summary has no in-site link to {route}')

    if 'Unresolved picks' not in html:
        errors.append('executive summary does not mention the unresolved-picks register')

    markers = html.count('data-glance-pick')
    if markers < 1:
        errors.append('no glance row carries a data-glance-pick state marker')

    # Every "Full detail" row on the summary must point at an in-site anchor.
    detail_links = re.findall(r'href="([^"]*origination/#match-\d+)"', html)
    if markers and len(detail_links) < 1:
        errors.append('glance rows exist but no Full detail anchor was rendered')

    # Viewport meta (mobile-first requirement) on the landing page.
    if 'name="viewport"' not in html:
        errors.append('landing page has no viewport meta tag')
    return errors


def run(site: Path | None = None) -> dict:
    site = site or (ROOT / 'site')
    dossier = _load(DOSSIER)
    snapshot = _load(SNAPSHOT)
    # CI runs unittest before `python -m scripts.build`, so a fresh checkout has
    # no rendered site: record that group as an explicit SKIP (the build step
    # and the browser specs verify the rendered contract there) instead of
    # failing a test for the workflow's step order. The function-level contract
    # still fails loudly when given a missing or broken site, so the skip can
    # never hide a regression - tests/test_c0bba79a_verification.py asserts both.
    built = (site / 'index.html').exists()
    groups: dict[str, dict] = {
        'dossier_arithmetic': {'errors': check_dossier_arithmetic(dossier)},
        'snapshot_binding': {'errors': check_snapshot_binding(dossier, snapshot)},
    }
    if built:
        groups['rendered_summary'] = {'errors': check_rendered_summary(site)}
    else:
        groups['rendered_summary'] = {
            'errors': [],
            'status': 'SKIP',
            'note': 'site/index.html not built in this checkout; CI builds and audits it in the next workflow step',
        }
    for name, group in groups.items():
        group.setdefault('status', 'PASS' if not group['errors'] else 'FAIL')
    return {
        'session_id': 'arena-c0bba79a',
        'checks': groups,
        'error_total': sum(len(g['errors']) for g in groups.values()),
        'snapshot_generated_at': snapshot.get('generated_at'),
        'named_dossier_snapshot': DOSSIER_SNAPSHOT_GENERATED,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true', help='write verification.json')
    ap.add_argument('--site', default=None, help='built site directory (default: <root>/site)')
    args = ap.parse_args(argv)
    site = Path(args.site) if args.site else None
    report = run(site)
    if args.write:
        OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print(f'wrote {OUT.relative_to(ROOT)}')
    for name, res in report['checks'].items():
        print(f"{res['status']}: {name}" + ('' if res['status'] == 'PASS' else ''))
        for err in res['errors']:
            print(f"  - {err}")
    print(f"error_total={report['error_total']}")
    return 0 if report['error_total'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
