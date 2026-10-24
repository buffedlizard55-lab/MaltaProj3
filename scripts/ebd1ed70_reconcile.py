#!/usr/bin/env python3
"""Row-by-row reconciliation of the live-lobby roster against a published snapshot.

Session arena-ebd1ed70 (task E1/E4). Usage:

    python -m scripts.ebd1ed70_reconcile --snapshot data/latest.json \
        --roster data/research/ebd1ed70/live-lobby-2026-10-24.json

For every pickable Hotspawn CS2 card in the roster, prints whether the snapshot
carries the fixture, a pick (or an explicit unresolved reason), both-team
probabilities when the brief requires them, and at least one first-party source
URL on the row. Never invents values: anything missing is reported as a gap.
Exit code 0 when every roster card is covered by pick-or-explicit-reason and
every covered row carries a source URL; 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def row_sources(match: dict) -> list[str]:
    urls = []
    for key in ('source_url', 'lobby_url', 'source_api'):
        val = match.get(key)
        if isinstance(val, str) and val.startswith('https://'):
            urls.append(val)
    for ev in match.get('evidence_links') or []:
        if isinstance(ev, dict):
            u = ev.get('url') or ev.get('source_url')
            if isinstance(u, str) and u.startswith('https://'):
                urls.append(u)
        elif isinstance(ev, str) and ev.startswith('https://'):
            urls.append(ev)
    for research in match.get('research') or []:
        if isinstance(research, dict):
            u = research.get('url') or research.get('source_url')
            if isinstance(u, str) and u.startswith('https://'):
                urls.append(u)
    return urls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', default='data/latest.json')
    ap.add_argument('--roster', default='data/research/ebd1ed70/live-lobby-2026-10-24.json')
    args = ap.parse_args()

    snap = load(args.snapshot)
    roster = load(args.roster)
    by_id = {str(m.get('id')): m for m in snap.get('matches', [])}

    print(f"snapshot generated_at={snap.get('generated_at')} run_status={snap.get('run_status')}")
    print(f"counts={snap.get('counts')}")
    print(f"{'card':8} {'fixture':42} {'status':12} {'pick/probs':44} srcs")
    gaps = 0
    for card in roster['cards']:
        fid = str(card.get('hotspawn_id') or card.get('fixture_id') or card.get('id'))
        teams = f"{card['team_a']} vs {card['team_b']}"
        match = by_id.get(fid)
        if match is None:
            print(f"{fid:8} {teams:42} {'MISSING':12} {'—':44} 0")
            gaps += 1
            continue
        analysis = match.get('analysis') or {}
        team_rows = match.get('teams') or []
        pick_idx = match.get('pick_index')
        if isinstance(pick_idx, int) and 0 <= pick_idx < len(team_rows):
            pick_name = team_rows[pick_idx].get('name', '')
        else:
            pick_name = ''
        probs = analysis.get('probabilities') if isinstance(analysis, dict) else None
        pa = pb = None
        if isinstance(probs, list) and len(probs) == 2:
            pa, pb = probs
        if not pick_name and analysis.get('pick'):
            pick_name = analysis.get('pick')
        research = match.get('research') or []
        limitations = match.get('limitations') or []
        if pick_name or (research and limitations):
            status = 'covered'
        elif limitations:
            status = 'reason-only'
        else:
            status = 'NO-PICK'
            gaps += 1
        probs = f"pick={pick_name or '-'} a={pa if pa is not None else '-'} b={pb if pb is not None else '-'}"
        srcs = row_sources(match)
        if status == 'covered' and not srcs:
            status = 'NO-SOURCE'
            gaps += 1
        print(f"{fid:8} {teams:42} {status:12} {probs:44} {len(srcs)}")
    print(f"\nroster={len(roster['cards'])} cards, gaps={gaps}")
    return 1 if gaps else 0


if __name__ == '__main__':
    sys.exit(main())
