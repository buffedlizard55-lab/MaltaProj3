"""Every-match coverage audit for the complete Hotspawn CS2 picks list.

Session arena-7e8bed83. The brief requires a pick for *every* Hotspawn CS2
match, researched HLTV-first then through esportsbooks, and — where no
compliant source exists — an explicit unresolved entry with its research
trail and limitations, never a blank row and never a default 50/50.

The publisher already builds that list, and ``scripts.verify_live`` already
checks that the deployed page's cards match the inventory. What nothing
enforced until now is the *content* invariant on the deployed data itself:

* every active fixture is either resolved or unresolved — the published
  counts must agree with the rows, exactly;
* a resolved row carries two probabilities in (0, 1) summing to 1, an
  https source link, a known ladder method, and a pick that is the argmax
  (or no pick for an exactly even estimate);
* an unresolved row carries no probability and no pick, but does carry a
  non-empty, https-linked research trail and at least one limitation;
* Hotspawn "% picked" and HLTV fan votes are never probability inputs
  (the published policy must say so).

This module is pure (dict in, list of violations out) so it is unit-tested
against the checked-in fixture and synthetic mutations, and it runs in
``scripts.verify_live`` against the public ``data/origination.json`` after
every deploy: a regression that silently drops picks now fails the
publisher instead of reaching phones unnoticed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KNOWN_METHODS = {'market', 'bookmaker', 'consensus', 'reference', 'model', 'guidance'}
SUM_TOLERANCE = 0.002


def _https(value) -> bool:
    return isinstance(value, str) and value.startswith('https://')


def documented_tie_break(origination: dict, pick) -> bool:
    """True when an exactly even estimate carries the provider's own published order.

    Session 7293b310. ``selection()`` gives an exactly even estimate no side, but
    session 4c972a51 lets such a row keep a direction when the ranking provider
    publishes an order for the two teams, recording the rule in ``tie_break``.
    The audit accepts that side only with the documented rule, matching winner,
    two different positive ranks, a research model (never a money line) and an
    https source. The probabilities themselves are untouched and stay 50/50.
    """
    if pick is None:
        return True
    tie = origination.get('tie_break') or {}
    ranks = tie.get('ranks') or []
    return bool(origination.get('method') == 'model'
                and tie.get('rule') == 'published-rank tie-break'
                and tie.get('winner') == pick
                and len(ranks) == 2
                and all(isinstance(r, int) and not isinstance(r, bool) and r > 0 for r in ranks)
                and ranks[0] != ranks[1]
                and _https(tie.get('source_url')))


def audit_complete_picks(payload: dict) -> list[str]:
    """Return human-readable violations; an empty list means full coverage."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ['complete-picks payload is not an object']
    matches = payload.get('matches')
    counts = payload.get('counts') or {}
    if not isinstance(matches, list) or not matches:
        return ['complete-picks payload has no matches']

    policy = payload.get('policy') or {}
    if policy.get('hotspawn_votes_used') is not False:
        problems.append('policy.hotspawn_votes_used is not explicitly false')
    if policy.get('fan_votes_used') is not False:
        problems.append('policy.fan_votes_used is not explicitly false')

    resolved = unresolved = with_pick = 0
    seen_ids: set[str] = set()
    for row in matches:
        mid = str(row.get('id'))
        label = f'fixture {mid}'
        if mid in seen_ids:
            problems.append(f'{label}: duplicate fixture id')
        seen_ids.add(mid)
        teams = row.get('teams') or []
        if len(teams) != 2 or not all(t.get('name') for t in teams):
            problems.append(f'{label}: does not name exactly two teams')
            continue
        origination = row.get('origination')
        pick = row.get('pick_index')
        if origination:
            resolved += 1
            probs = origination.get('probabilities') or []
            if len(probs) != 2 or not all(isinstance(p, (int, float)) and 0 < p < 1 for p in probs):
                problems.append(f'{label}: resolved without two probabilities in (0, 1)')
                continue
            if abs(sum(probs) - 1.0) > SUM_TOLERANCE:
                problems.append(f'{label}: probabilities sum to {sum(probs):.4f}, not 1')
            if origination.get('method') not in KNOWN_METHODS:
                problems.append(f'{label}: unknown method {origination.get("method")!r}')
            if not _https(origination.get('source_url')):
                problems.append(f'{label}: resolved estimate has no https source link')
            # Money estimates carry per-provider quotes; model estimates carry
            # rating inputs instead (featured Valve rows publish quotes=[]).
            # Either way every published evidence link must be https and at
            # least one must exist beyond the top-level source link.
            evidence = list(origination.get('quotes') or []) + list(origination.get('inputs') or [])
            if origination.get('method') in {'market', 'bookmaker', 'consensus', 'reference'} and not evidence:
                problems.append(f'{label}: money estimate publishes no quote evidence')
            for item in evidence:
                url = item.get('source_url')
                if url is not None and not _https(url):
                    problems.append(f'{label}: evidence link is not https: {url!r}')
            if probs[0] == probs[1]:
                if not documented_tie_break(origination, pick):
                    problems.append(f'{label}: exactly even estimate must not name a pick (no documented tie-break)')
            elif pick != (0 if probs[0] > probs[1] else 1):
                problems.append(f'{label}: pick_index {pick!r} is not the higher-probability team')
            if pick is not None:
                with_pick += 1
        else:
            unresolved += 1
            if pick is not None:
                problems.append(f'{label}: unresolved fixture must not name a pick')
            trail = row.get('research') or []
            if not trail or not all(_https(r.get('source_url')) for r in trail):
                problems.append(f'{label}: unresolved fixture lacks an https-linked research trail')
            if not (row.get('limitations')):
                problems.append(f'{label}: unresolved fixture publishes no limitation')

    expected = {'active': len(matches), 'resolved': resolved,
                'unresolved': unresolved, 'with_pick': with_pick}
    for key, value in expected.items():
        if counts.get(key) != value:
            problems.append(f'counts.{key} is {counts.get(key)!r}, rows give {value}')
    if resolved + unresolved != len(matches):
        problems.append('resolved + unresolved does not cover every active fixture')
    return problems


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path('data/origination.json')
    payload = json.loads(path.read_text())
    problems = audit_complete_picks(payload)
    counts = payload.get('counts') or {}
    print(f'complete-picks coverage: {counts.get("with_pick")}/{counts.get("active")} with a pick, '
          f'{counts.get("unresolved")} unresolved (explicit, source-linked)')
    for problem in problems:
        print(f'::error::{problem}')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
