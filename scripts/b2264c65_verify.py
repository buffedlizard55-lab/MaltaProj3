"""Deterministic dossier, alias, arithmetic-replay, and executive-summary verifier for session arena-b2264c65.

Safe across future 4-hour scheduled publishes: root `snapshot.json` and
`origination.json` are replayed dynamically row-by-row without hard-pinning
ephemeral active fixture counts or IDs that rotate as matches start.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

from scripts import audit_rows, build, originate, reference_odds
from scripts.domain import no_vig, normalize_pair

UTC = timezone.utc
VALVE_G = 1.0 / math.sqrt(1.0 + 3.0 * ((math.log(10.0) / 400.0) ** 2) * (75.0 ** 2) / (math.pi ** 2))


def verify_dossiers(root: Path) -> dict:
    rdir = root / 'data' / 'research' / 'b2264c65'
    ref = json.loads((rdir / 'reference-odds.json').read_text(encoding='utf-8'))
    entries = ref.get('entries') or []
    rejected = ref.get('rejected') or []
    if len(entries) != 4 or len(rejected) != 15:
        raise AssertionError(f'Expected 4 entries and 15 rejected in b2264c65 reference-odds.json, got {len(entries)}/{len(rejected)}')
    for entry in entries:
        probs = reference_odds.problems(entry)
        if probs:
            raise AssertionError(f"Invalid reference entry {entry.get('fixture_id')}: {probs}")
        digest = hashlib.sha256(entry['excerpt'].encode('utf-8')).hexdigest()
        if entry['excerpt_sha256'] != digest:
            raise AssertionError(f"SHA-256 mismatch on reference entry {entry['fixture_id']}")
    for rej in rejected:
        if rej.get('rejected') is not True or not str(rej.get('source_url', '')).startswith('https://egamersworld.com/'):
            raise AssertionError(f"Malformed rejected entry: {rej.get('fixture_id')}")

    cov_text = (rdir / 'live-coverage.json').read_text(encoding='utf-8')
    if '%' in cov_text:
        raise AssertionError('live-coverage.json must not contain percent characters')
    cov = json.loads(cov_text)
    if not (rdir / 'live-coverage.md').is_file():
        raise AssertionError('Missing sibling live-coverage.md')
    live_rows = cov.get('live_fixtures') or []
    if len(live_rows) != 19:
        raise AssertionError(f'Expected 19 live fixtures in b2264c65 live-coverage.json, got {len(live_rows)}')
    for row in live_rows:
        if not str(row.get('hotspawn_url', '')).startswith('https://') or not str(row.get('hltv_url', '')).startswith('https://www.hltv.org/matches/'):
            raise AssertionError(f"Missing official Hotspawn/HLTV URL on {row.get('id')}")

    obs = json.loads((rdir / 'hltv-first-observations.json').read_text(encoding='utf-8'))
    if not (rdir / 'hltv-first-observations.md').is_file():
        raise AssertionError('Missing sibling hltv-first-observations.md')
    observations = obs.get('observations') or []
    if len(observations) != 6:
        raise AssertionError(f'Expected 6 HLTV-first observations, got {len(observations)}')
    scoped_fids = set()
    for o in observations:
        digest = hashlib.sha256(o['excerpt'].encode('utf-8')).hexdigest()
        if o.get('excerpt_sha256') != digest:
            raise AssertionError(f"SHA-256 mismatch on observation {o.get('id')}")
        scoped_fids.update(str(fid) for fid in (o.get('fixture_ids') or []))
    # Only the 10 fixtures NOT resolved via featured exact-name money lines
    expected_non_featured = {'1079201', '1081159', '1081160', '1093218', '1082861',
                             '1081162', '1081163', '1081164', '1082792', '1082793'}
    if scoped_fids != expected_non_featured:
        raise AssertionError(f'HLTV-first scope drift: {scoped_fids} != {expected_non_featured}')

    flags = json.loads((rdir / 'flags.json').read_text(encoding='utf-8'))
    if len(flags) != 5:
        raise AssertionError(f'Expected 5 flags in b2264c65/flags.json, got {len(flags)}')
    for fl in flags:
        urls = fl.get('source_urls') or []
        if not urls or not all(audit_rows.is_official(u) for u in urls):
            raise AssertionError(f"Flag {fl.get('id')} has missing or non-official source_urls")

    return {
        'reference_entries': len(entries),
        'reference_rejected': len(rejected),
        'live_coverage_fixtures': len(live_rows),
        'observations': len(observations),
        'flags': len(flags),
    }


def verify_aliases(root: Path) -> dict:
    registry = originate.load_registry(root / 'data' / 'origination' / 'aliases.json')
    checks = [
        ('Team Nemesis', 'Nemesis', 'NODWIN Clutch Series #13', 'Nemesis Academy'),
        ('THUNDERdOWNUNDER', 'Off Chops', 'DFRAG Invitational 2026', 'Off Chops Academy'),
        ('THUNDER dOWNUNDER', 'Off Chops', 'DFRAG Invitational 2026', 'THUNDER dOWNUNDER Academy'),
        ('Luminosity Gaming', 'Luminosity', 'Tesla Cup 2026', 'Luminosity Academy'),
        ('Team Envy', 'Envy', 'Tesla Cup 2026', 'Team Envy Academy'),
    ]
    for alias, canonical, comp, excluded in checks:
        _, used = originate.resolve_name(alias, registry, competition=comp)
        if len(used) != 1 or used[0]['canonical'] != canonical:
            raise AssertionError(f'Alias {alias!r} failed in {comp!r}: {used}')
        _, out_used = originate.resolve_name(alias, registry, competition='Unrelated Cup 2099')
        if out_used:
            raise AssertionError(f'Alias {alias!r} leaked outside declared competition')
        _, exc_used = originate.resolve_name(excluded, registry, competition=comp)
        if exc_used:
            raise AssertionError(f'Excluded academy variant {excluded!r} matched in {comp!r}')
    return {'aliases_verified': len(checks)}


def verify_published_replay(root: Path) -> dict:
    snap = json.loads((root / 'snapshot.json').read_text(encoding='utf-8'))
    orig = json.loads((root / 'origination.json').read_text(encoding='utf-8'))

    past, open_priced, open_blank = 0, 0, 0
    for m in snap.get('matches') or []:
        if not str(m.get('source_url', '')).startswith('https://'):
            raise AssertionError(f"Missing https source_url on snapshot match {m.get('id')}")
        if m.get('availability') == 'past':
            if m.get('analysis') is not None or m.get('pick_index') is not None:
                raise AssertionError(f"Past match {m.get('id')} must not fabricate retrospective probability")
            past += 1
            continue
        analysis = m.get('analysis')
        if analysis is None:
            if m.get('pick_index') is not None or not m.get('limitations'):
                raise AssertionError(f"Blank match {m.get('id')} must have null pick_index and explicit limitations")
            open_blank += 1
            continue
        probs = analysis['probabilities']
        if abs(sum(probs) - 1.0) > 1e-6:
            raise AssertionError(f"Probabilities do not sum to 1 on {m.get('id')}")
        if 'hotspawn' in str(analysis.get('source', '')).lower():
            raise AssertionError(f"Hotspawn crowd source forbidden on {m.get('id')}")
        if analysis['method'] == 'model':
            r_a, r_b = analysis['inputs'][0]['points'], analysis['inputs'][1]['points']
            p_a = 1.0 / (1.0 + 10.0 ** (VALVE_G * (r_b - r_a) / 400.0))
            if abs(probs[0] - p_a) > 1e-6:
                raise AssertionError(f"Valve Glicko drift on {m.get('id')}: {probs[0]} vs {p_a}")
        elif analysis['method'] == 'bookmaker':
            nv = no_vig(analysis['quotes'][0]['odds'])
            if any(abs(a - b) > 1e-6 for a, b in zip(probs, nv)):
                raise AssertionError(f"Bookmaker no-vig drift on {m.get('id')}")
        elif analysis['method'] == 'market':
            mids = [q['midpoint'] for q in analysis['quotes']]
            np = normalize_pair(mids[0], mids[1])
            if any(abs(a - b) > 1e-6 for a, b in zip(probs, np)):
                raise AssertionError(f"Market midpoint drift on {m.get('id')}")
        open_priced += 1

    orig_resolved, orig_unresolved = 0, 0
    for m in orig.get('matches') or []:
        o = m.get('origination')
        if o is None:
            if m.get('pick_index') is not None or not m.get('limitations'):
                raise AssertionError(f"Unresolved origination row {m.get('id')} lacks limitations or has pick")
            orig_unresolved += 1
            continue
        probs = o['probabilities']
        if abs(sum(probs) - 1.0) > 1e-6:
            raise AssertionError(f"Origination probabilities do not sum to 1 on {m.get('id')}")
        if 'hotspawn' in str(o.get('source', '')).lower():
            raise AssertionError(f"Hotspawn source forbidden in origination on {m.get('id')}")
        orig_resolved += 1

    soup = BeautifulSoup((root / 'index.html').read_text(encoding='utf-8'), 'html.parser')
    vp = soup.find('meta', attrs={'name': 'viewport'})
    if not vp or 'width=device-width' not in (vp.get('content') or ''):
        raise AssertionError('Missing responsive viewport meta on index.html')
    if soup.find(id='unresolved-register') is None:
        raise AssertionError('Missing #unresolved-register section in executive summary')
    hrefs = [a.get('href', '') for a in soup.find_all('a')]
    if not any('origination/#picks' in h for h in hrefs) or not any('unresolved/' in h for h in hrefs):
        raise AssertionError('Missing executive-summary internal links to origination/#picks or unresolved/')

    loaded_cov = build.load_live_coverage(root / 'data')
    if loaded_cov is None or loaded_cov.get('observed_at', '') < '2026-10-26T01:09:00Z':
        raise AssertionError('load_live_coverage did not select b2264c65 or newer record')

    return {
        'snapshot_past': past,
        'snapshot_open_priced': open_priced,
        'snapshot_open_blank': open_blank,
        'origination_resolved': orig_resolved,
        'origination_unresolved': orig_unresolved,
        'clock_checked': datetime.now(UTC).isoformat(),
    }


def verify_all(root: Path | None = None) -> dict:
    base = Path(root or Path(__file__).resolve().parent.parent)
    return {
        'dossiers': verify_dossiers(base),
        'aliases': verify_aliases(base),
        'published': verify_published_replay(base),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    summary = verify_all(args.root)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
