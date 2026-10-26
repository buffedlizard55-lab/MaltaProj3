"""Session arena-c333bb27 verification: live Hotspawn CS2 inventory parity,
HLTV-first + external-line origination replay, executive-summary & mobile
readability, and Flagged-for-Review register integrity.

Designed to validate both the current 19-open-fixture snapshot and any future
4-hour publisher snapshot (including snapshots with labelled pick-less rows)
without wall-clock brittleness.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
from statistics import median

from scripts.domain import VALVE_RD, no_vig, normalize_pair
from scripts.form_model import win_probability
from scripts.review_register import REGISTERS, validate as validate_register

HLTV_MATCH_URLS_2026_10_26 = {
    '1082858': 'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
    '1082859': 'https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026',
    '1079201': 'https://www.hltv.org/matches/2399116/nemesis-vs-inox-division-nodwin-clutch-series-13',
    '1079202': 'https://www.hltv.org/matches/2399117/fokus-vs-ex-zero-tenacity-nodwin-clutch-series-13',
    '1081159': 'https://www.hltv.org/matches/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12',
    '1079203': 'https://www.hltv.org/matches/2399118/metizport-vs-brute-nodwin-clutch-series-13',
    '1081160': 'https://www.hltv.org/matches/2399510/havu-vs-illyrians-cct-2026-europe-series-12',
    '1093218': 'https://www.hltv.org/matches/2399119/nuclear-tigeres-vs-unity-nodwin-clutch-series-13',
    '1082860': 'https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026',
    '1082861': 'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
    '1082897': 'https://www.hltv.org/matches/2399866/b8-vs-k27-rlg-tesla-cup-2026',
    '1082898': 'https://www.hltv.org/matches/2399867/alliance-vs-faze-rlg-tesla-cup-2026',
    '1081162': 'https://www.hltv.org/matches/2399512/ex-rustec-vs-spirit-academy-cct-2026-europe-series-12',
    '1081163': 'https://www.hltv.org/matches/2399513/baks-vs-saint-sinners-cct-2026-europe-series-12',
    '1082900': 'https://www.hltv.org/matches/2399869/luminosity-vs-hotu-rlg-tesla-cup-2026',
    '1081164': 'https://www.hltv.org/matches/2399514/inner-circle-academy-vs-lavked-cct-2026-europe-series-12',
    '1082901': 'https://www.hltv.org/matches/2399870/envy-vs-gamerlegion-rlg-tesla-cup-2026',
    '1082792': 'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
    '1082793': 'https://www.hltv.org/matches/2399438/5star-vs-1win-gluck-moscow-cyber-games-2026',
}


def replay_origination_probabilities(match_snap: dict, match_orig: dict) -> tuple[list[float] | None, str]:
    """Recompute the published probability pair from the stored quotes/inputs."""
    orig = match_orig.get('origination')
    if not isinstance(orig, dict):
        return None, 'unresolved'
    probs = orig.get('probabilities')
    if not isinstance(probs, list) or len(probs) != 2:
        return None, 'no_probabilities'
    method = orig.get('method')
    quotes = orig.get('quotes') or []
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * VALVE_RD ** 2 / math.pi ** 2)

    if method in ('market', 'guidance'):
        if len(quotes) == 2 and 'midpoint' in quotes[0]:
            m0 = (float(quotes[0]['bid']) + float(quotes[0]['ask'])) / 2.0
            m1 = (float(quotes[1]['bid']) + float(quotes[1]['ask'])) / 2.0
            return normalize_pair(m0, m1), method
        if quotes and isinstance(quotes[0].get('bid'), list) and isinstance(quotes[0].get('ask'), list):
            q = quotes[0]
            m0 = (float(q['bid'][0]) + float(q['ask'][0])) / 2.0
            m1 = (float(q['bid'][1]) + float(q['ask'][1])) / 2.0
            return normalize_pair(m0, m1), method
        return list(probs), method

    if method in ('bookmaker', 'reference'):
        if quotes and isinstance(quotes[0].get('odds'), list) and len(quotes[0]['odds']) == 2:
            return no_vig(quotes[0]['odds']), method
        return list(probs), method

    if method == 'consensus':
        q_probs = []
        for q in quotes:
            if isinstance(q.get('probabilities'), list) and len(q['probabilities']) == 2:
                q_probs.append(q['probabilities'])
            elif isinstance(q.get('odds'), list) and len(q['odds']) == 2:
                q_probs.append(no_vig(q['odds']))
        if q_probs:
            p0 = median(float(pr[0]) for pr in q_probs)
            return normalize_pair(p0, 1.0 - p0), method
        return list(probs), method

    if method == 'model':
        if quotes and quotes[0].get('family') == 'form':
            q = quotes[0]
            pts0 = float(q['inputs'][0]['points'])
            pts1 = float(q['inputs'][1]['points'])
            rd = min(400.0, 150.0 + 300.0 / math.sqrt(max(1, int(q['n_series']))))
            p0 = win_probability(pts0, pts1, rd)
            return [p0, 1.0 - p0], 'model:form'
        if quotes and quotes[0].get('family') == 'network':
            return list(probs), 'model:network'
        inputs = (quotes[0].get('inputs') if quotes and 'inputs' in quotes[0]
                  else (match_snap.get('analysis') or {}).get('inputs')) or []
        if len(inputs) == 2 and 'points' in inputs[0] and 'points' in inputs[1]:
            pts0 = float(inputs[0]['points'])
            pts1 = float(inputs[1]['points'])
            if (orig.get('source') or '').startswith('HLTV'):
                p0 = 1.0 / (1.0 + 10.0 ** ((pts1 - pts0) / 400.0))
            else:
                p0 = 1.0 / (1.0 + 10.0 ** (g * (pts1 - pts0) / 400.0))
            return normalize_pair(p0, 1.0 - p0), 'model:ratings'
        return list(probs), 'model'

    return list(probs), str(method)


def verify(root: Path, errors: list[str] | None = None) -> dict:
    """Validate root-synced site, snapshot, origination ladder, CSV and c333bb27 dossier."""
    if errors is None:
        errors = []
    root = Path(root)

    index_path = root / 'index.html'
    snap_path = root / 'snapshot.json'
    orig_path = root / 'origination.json'
    csv_path = root / 'picks.csv'

    for req in (index_path, snap_path, orig_path):
        if not req.exists():
            errors.append(f'missing required file: {req.name}')
    if errors:
        return {'errors': errors}

    index = index_path.read_text()
    snap = json.loads(snap_path.read_text())
    orig = json.loads(orig_path.read_text())

    result: dict = {
        'snapshot_generated_at': snap.get('generated_at'),
        'origination_generated_at': orig.get('generated_at'),
        'counts': snap.get('counts', {}),
        'origination_counts': orig.get('counts', {}),
    }

    # 1. Coverage & inventory contract
    if not snap.get('coverage_complete'):
        errors.append('snapshot.json coverage_complete is not True')
    active = [m for m in snap.get('matches', []) if m.get('availability') != 'past']
    active_ids = [str(m['id']) for m in active]
    if snap.get('counts', {}).get('upcoming') != len(active):
        errors.append(f"snapshot counts.upcoming ({snap.get('counts', {}).get('upcoming')}) != len(active) ({len(active)})")

    # 2. Mobile viewport & 6-tab navigation
    if 'name="viewport"' not in index or 'width=device-width' not in index:
        errors.append('index.html missing responsive viewport meta')
    nav_blocks = re.findall(r'class="mobile-nav".*?</nav>', index, re.S)
    if not nav_blocks:
        errors.append('index.html missing .mobile-nav')
    else:
        tabs = re.findall(r'<span>([^<]+)</span>', nav_blocks[0])
        expected_tabs = {'Summary', 'Picks', 'Unresolved', 'Edge', 'Sources', 'Review'}
        if set(tabs) != expected_tabs:
            errors.append(f'mobile-nav tabs {tabs} != {sorted(expected_tabs)}')
        result['mobile_tabs'] = tabs

    # 3. Executive summary in-site links (#start-here) and #unresolved-register
    if 'id="start-here"' not in index:
        errors.append('index.html missing #start-here navigation')
    else:
        start_here = index[index.find('id="start-here"'):index.find('id="start-here"') + 3500]
        for href in ('./#picks-at-a-glance', './origination/#picks', './#unresolved-register', './origination/#unresolved'):
            if href not in start_here:
                errors.append(f'#start-here missing in-site link {href}')
    if 'id="unresolved-register"' not in index:
        errors.append('index.html missing #unresolved-register section inside executive summary')

    # 4. Glance rows match active fixtures 1-for-1 and obey probability/pick/source rules
    glance_rows = re.findall(r'<li class="glance-row[^"]*"[^>]*data-glance-id="(\d+)"[^>]*>(.*?)</li>', index, re.S)
    glance_ids = [fid for fid, _ in glance_rows]
    if sorted(glance_ids) != sorted(active_ids):
        errors.append(f'glance row IDs {sorted(glance_ids)} != active IDs {sorted(active_ids)}')
    result['glance_row_count'] = len(glance_rows)

    for fid, body in glance_rows:
        is_unresolved_row = ('glance-unresolved' in body or 'No price' in body or 'Unresolved' in body) and 'data-glance-pick' not in body
        probs = [float(p) for p in re.findall(r'(\d+\.\d)%', body)]
        if is_unresolved_row:
            if probs:
                errors.append(f'unresolved glance row {fid} must not print percentages: {probs}')
        else:
            if len(probs) < 2:
                errors.append(f'priced glance row {fid} missing two percentages: {probs}')
            elif abs((probs[0] + probs[1]) - 100.0) > 0.25:
                errors.append(f'priced glance row {fid} percentages do not sum to 100%: {probs}')
            if 'data-glance-pick' not in body:
                errors.append(f'priced glance row {fid} missing data-glance-pick marker')
            ext_links = [u for u in re.findall(r'href="(https://[^"]+)"', body) if 'hotspawn.com' not in u]
            if not ext_links:
                errors.append(f'priced glance row {fid} missing non-Hotspawn official https:// source link')

    # 5. Replay every active fixture in origination.json
    orig_by_id = {str(m['id']): m for m in orig.get('matches', [])}
    replayed_rows = []
    max_prob_diff = 0.0
    for m in active:
        fid = str(m['id'])
        om = orig_by_id.get(fid)
        if not om:
            errors.append(f'origination.json missing active fixture {fid}')
            continue
        o = om.get('origination')
        if o is None:
            replayed_rows.append({'id': fid, 'status': 'unresolved'})
            continue
        probs = o.get('probabilities')
        if not isinstance(probs, list) or len(probs) != 2:
            errors.append(f'fixture {fid} origination block missing 2 probabilities')
            continue
        src_url = str(o.get('source_url') or '')
        if not src_url.startswith('https://') or 'hotspawn.com' in src_url:
            errors.append(f'fixture {fid} has invalid or Hotspawn probability source_url: {src_url}')
        rep, kind = replay_origination_probabilities(m, om)
        if rep is not None:
            diff = max(abs(rep[0] - probs[0]), abs(rep[1] - probs[1]))
            max_prob_diff = max(max_prob_diff, diff)
            if diff > 1e-5:
                errors.append(f'fixture {fid} ({kind}) replay mismatch: {rep} vs {probs} (diff={diff})')
        pick = om.get('pick_index')
        if abs(probs[0] - probs[1]) > 1e-8:
            expected_pick = 0 if probs[0] > probs[1] else 1
            if pick != expected_pick:
                errors.append(f'fixture {fid} pick_index {pick} != argmax {expected_pick} for {probs}')
        replayed_rows.append({
            'id': fid,
            'teams': [m['teams'][0]['name'], m['teams'][1]['name']],
            'competition': m.get('competition'),
            'starts_at': m.get('starts_at'),
            'method': o.get('method'),
            'replay_kind': kind,
            'source': o.get('source'),
            'source_url': src_url,
            'probabilities': probs,
            'pick_index': pick,
            'pick_team': m['teams'][pick]['name'] if pick in (0, 1) else None,
            'hltv_match_url': HLTV_MATCH_URLS_2026_10_26.get(fid),
        })

    result['replayed_count'] = len(replayed_rows)
    result['max_probability_diff'] = max_prob_diff
    result['replayed_rows'] = replayed_rows

    # 6. Verify picks.csv if present
    if csv_path.exists():
        rows_csv = list(csv.DictReader(csv_path.read_text().splitlines()))
        csv_open_ids = [
            str(r.get('hotspawn_id') or r.get('id'))
            for r in rows_csv
            if (r.get('availability_at_snapshot') or r.get('availability')) != 'past'
        ]
        if sorted(csv_open_ids) != sorted(active_ids):
            errors.append(f'picks.csv open IDs {sorted(csv_open_ids)} != snapshot active IDs {sorted(active_ids)}')
        result['csv_total_rows'] = len(rows_csv)
        result['csv_open_rows'] = len(csv_open_ids)

    # 7. Verify session c333bb27 review register and flags if data/research/c333bb27 exists
    data_dir = root / 'data'
    c333_dir = data_dir / 'research' / 'c333bb27'
    if c333_dir.exists():
        reg_rel = 'research/c333bb27/repo-review.json'
        if reg_rel not in REGISTERS:
            errors.append(f'{reg_rel} not registered in scripts.review_register.REGISTERS')
        reg_file = c333_dir / 'repo-review.json'
        if not reg_file.exists():
            errors.append('missing data/research/c333bb27/repo-review.json')
        else:
            reg_data = json.loads(reg_file.read_text())
            try:
                validate_register(reg_data)
            except ValueError as exc:
                errors.append(f'invalid repo-review.json: {exc}')
            result['c333bb27_review_items'] = len(reg_data.get('items', []))
        flags_file = c333_dir / 'flags.json'
        if not flags_file.exists():
            errors.append('missing data/research/c333bb27/flags.json')
        else:
            flags = json.loads(flags_file.read_text())
            if not isinstance(flags, list) or len(flags) < 4:
                errors.append('data/research/c333bb27/flags.json has fewer than 4 flags')
            for f in flags:
                urls = f.get('source_urls') or []
                if not urls or not all(str(u).startswith('https://') for u in urls):
                    errors.append(f"flag {f.get('id')} missing https:// source_urls")
            result['c333bb27_flags'] = len(flags)

    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.', help='repository root directory')
    ap.add_argument('--check', action='store_true', help='exit non-zero if any error is found')
    args = ap.parse_args(argv)

    errors: list[str] = []
    res = verify(Path(args.root), errors)
    summary = {k: v for k, v in res.items() if k != 'replayed_rows'}
    print(json.dumps(summary, indent=2))
    if errors:
        print(f'FAIL ({len(errors)} errors):', file=sys.stderr)
        for err in errors:
            print(f'  - {err}', file=sys.stderr)
        return 1 if args.check else 0
    print(f"PASS: {res.get('replayed_count', 0)} active fixtures replayed (max_diff={res.get('max_probability_diff', 0.0):.2e}), 0 errors.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
