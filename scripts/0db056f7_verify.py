"""Session arena-0db056f7: independent offline verification (no network).

Replays, from first principles, the artifacts this session relies on:

* root ``snapshot.json`` (the deployed featured snapshot): count arithmetic,
  every open fixture's probability pair summing to 1, the directional pick
  being the argmax (or a genuine tie), and every research/analysis source
  link being https;
* ``data/research/0db056f7/reference-odds.json``: the one captured entry
  passes ``reference_odds.problems()``, quotes and replays through the
  shipped ladder code, and every rejected row produces no quote;
* root ``index.html`` (the deployed executive summary): the phone-first
  landmarks exist (picks-at-a-glance, unresolved-register,
  no-line-register, fallback-register, start-here, mobile-status,
  mobile-nav, viewport meta) and the summary links to the complete list.

Writes ``data/research/0db056f7/verification.json`` and exits non-zero on
any failed check.  Nothing here fetches the network or writes publisher
outputs.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import reference_odds  # noqa: E402

OUT = ROOT / 'data/research/0db056f7/verification.json'


def check_snapshot() -> dict:
    snap = json.loads((ROOT / 'snapshot.json').read_text(encoding='utf-8'))
    counts, matches = snap['counts'], snap['matches']
    open_rows = [m for m in matches if m.get('availability') == 'open']
    problems = []
    if counts['inventory'] != len(matches):
        problems.append('inventory != len(matches)')
    if counts['upcoming'] != len(open_rows):
        problems.append('upcoming != open rows')
    if counts['upcoming'] + counts['archived'] + counts['unknown_schedule'] != counts['inventory']:
        problems.append('upcoming+archived+unknown != inventory')
    if counts['market'] + counts['bookmaker'] + counts['model'] + counts['unresolved'] != counts['upcoming']:
        problems.append('method counts != upcoming')
    replayed = unresolved = 0
    for m in open_rows:
        analysis = m.get('analysis') or {}
        probs = analysis.get('probabilities')
        if probs:
            replayed += 1
            if len(probs) != 2 or abs(sum(probs) - 1.0) > 1e-6:
                problems.append(f"{m['id']}: probabilities do not sum to 1")
            pick = m.get('pick_index')
            if abs(probs[0] - probs[1]) > 1e-9:
                if pick != (0 if probs[0] > probs[1] else 1):
                    problems.append(f"{m['id']}: pick_index is not the argmax")
            src = str(analysis.get('source_url') or '')
            if not src.startswith('https://'):
                problems.append(f"{m['id']}: analysis source_url is not https")
        else:
            unresolved += 1
            if m.get('pick_index') is not None:
                problems.append(f"{m['id']}: unresolved row carries a pick")
        for row in m.get('research') or []:
            if not str(row.get('source_url') or '').startswith('https://'):
                problems.append(f"{m['id']}: research source_url is not https")
    if unresolved != counts['unresolved']:
        problems.append('unresolved recount != counts')
    return {'generated_at': snap.get('generated_at'), 'counts': counts,
            'open_replayed': replayed, 'open_unresolved': unresolved, 'problems': problems}


def _fixture(entry: dict) -> dict:
    return {'id': entry['fixture_id'], 'starts_at': entry['starts_at'],
            'locks_at': entry['starts_at'], 'availability': 'open',
            'competition': entry.get('event') or '', 'tier': 'c',
            'source_url': 'https://www.hotspawn.com/matches/x-' + entry['fixture_id'],
            'lobby_url': 'https://play.hotspawn.com/cs2-pickems',
            'teams': [{'id': '1', 'name': entry['teams'][0]}, {'id': '2', 'name': entry['teams'][1]}]}


def check_capture() -> dict:
    doc = json.loads((ROOT / 'data/research/0db056f7/reference-odds.json').read_text(encoding='utf-8'))
    problems, quotes = [], {}
    for entry in doc['entries']:
        bad = reference_odds.problems(entry)
        if bad:
            problems.append(f"{entry['fixture_id']}: {bad}")
            continue
        now = datetime.fromisoformat(entry['observed_at'].replace('Z', '+00:00')) + timedelta(minutes=5)
        quote, reason = reference_odds.quote(entry, _fixture(entry), now)
        if quote is None:
            problems.append(f"{entry['fixture_id']}: no quote ({reason})")
            continue
        reference_odds.replay(entry, quote)
        quotes[entry['fixture_id']] = quote['probabilities']
    for entry in doc['rejected']:
        now = datetime.fromisoformat(entry['observed_at'].replace('Z', '+00:00')) + timedelta(minutes=5)
        quote, _reason = reference_odds.quote(entry, _fixture(entry), now)
        if quote is not None:
            problems.append(f"{entry['fixture_id']}: rejected row produced a quote")
    return {'entries': len(doc['entries']), 'rejected': len(doc['rejected']),
            'quotes': quotes, 'problems': problems}


def check_summary() -> dict:
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    required = ['name="viewport"', 'id="picks-at-a-glance"', 'id="unresolved-register"',
                'id="no-line-register"', 'id="fallback-register"', 'id="start-here"',
                'class="mobile-status"', 'class="mobile-nav"', './origination/#picks',
                './unresolved/', 'Unresolved picks &amp; limitations']
    missing = [r for r in required if r not in html]
    return {'missing_landmarks': missing}


def main() -> int:
    report = {'session': 'arena-0db056f7', 'snapshot': check_snapshot(),
              'capture': check_capture(), 'executive_summary': check_summary()}
    failed = bool(report['snapshot']['problems'] or report['capture']['problems']
                  or report['executive_summary']['missing_landmarks'])
    report['result'] = 'FAIL' if failed else 'PASS'
    OUT.write_text(json.dumps(report, indent=1), encoding='utf-8')
    print(json.dumps(report, indent=1))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
