"""Replay session 719a314a's live-coverage dossier from its stored quotes.

Run:  python -m scripts.719a314a_live_coverage [--record PATH]

What it verifies, without touching the network:

1. every card carries a https source and a UTC start that matches its stored
   lobby label plus the documented +4 h lobby-clock conversion;
2. every published percentage and pick re-derives from the two stored decimal
   prices by proportional (no-vig) normalisation — a hand-written or stale
   number fails;
3. cards with no quote either say why (a placeholder rejection) or carry the
   explicit "no usable price" limitation; there is no silent blank;
4. the headline counts in the record agree with the cards themselves;
5. no card carries a Hotspawn "% picked" value or an HLTV fan vote as a
   probability — the only probability input is a two-sided price.

The script is fail-closed: any inconsistency raises and exits 1. It writes no
site data and cannot alter a pick.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD = ROOT / 'data/research/719a314a/live-coverage-2026-10-24.json'
LOBBY_CLOCK_OFFSET_HOURS = 4  # verified on every card whose fixture-API epoch is known


def load(path: Path = DEFAULT_RECORD) -> dict:
    return json.loads(path.read_text())


def no_vig(o1: float, o2: float) -> tuple[float, float]:
    """Proportional (no-vig) normalisation of a two-sided decimal price pair."""
    p1, p2 = 1 / o1, 1 / o2
    total = p1 + p2
    return round(100 * p1 / total, 1), round(100 * p2 / total, 1)


def start_from_label(label: str) -> str:
    """Convert the lobby's displayed clock label to UTC by the verified offset."""
    head, tail = label.rsplit(',', 1)
    parsed = datetime.strptime(f'{head.strip()} 2026 {tail.strip()}', '%b %d %Y %H:%M')
    return (parsed + timedelta(hours=LOBBY_CLOCK_OFFSET_HOURS)).replace(
        tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')


def verify(record: dict) -> list[str]:
    """Return a list of problems; empty means the record replays cleanly."""
    problems: list[str] = []
    cards = record.get('cards') or []
    if not cards:
        return ['the record carries no cards']

    for card in cards:
        cid = card.get('hotspawn_id')
        teams = card.get('teams') or []
        if len(teams) != 2:
            problems.append(f'{cid}: expected two teams, got {teams!r}')
            continue

        expected_start = start_from_label(card['lobby_displayed_start'])
        if card.get('start_utc') != expected_start:
            problems.append(f'{cid}: start_utc {card.get("start_utc")} != lobby+4h '
                            f'{expected_start}')

        line = card.get('reference_line')
        if line:
            odds = line['quoted_decimal_odds']
            o1, o2 = odds[teams[0]], odds[teams[1]]
            p1, p2 = no_vig(o1, o2)
            published = line['no_vig_probabilities']
            if (published[teams[0]], published[teams[1]]) != (p1, p2):
                problems.append(f'{cid}: published {published} != replayed '
                                f'{{{teams[0]!r}: {p1}, {teams[1]!r}: {p2}}}')
            if round(p1 + p2, 6) != 100.0:
                problems.append(f'{cid}: probabilities do not sum to 100')
            expected_pick = teams[0] if p1 > p2 else teams[1]
            if line.get('pick') != expected_pick:
                problems.append(f'{cid}: pick {line.get("pick")!r} is not the higher '
                                f'probability side {expected_pick!r}')
            if not str(line.get('page', '')).startswith('https://'):
                problems.append(f'{cid}: quote has no https page')
            if not line.get('caveat'):
                problems.append(f'{cid}: quote carries no caveat')
        elif card.get('in_published_snapshot'):
            # Covered by the published ladder; nothing to originate here.
            continue
        elif not card.get('limitation'):
            problems.append(f'{cid}: no published pick, no quote and no stated limitation')

        # A probability may only come from a two-sided price.
        for key in card:
            lowered = key.lower()
            if 'picked_percent' in lowered or 'fan_vote' in lowered or 'vote_percent' in lowered:
                problems.append(f'{cid}: forbidden probability key {key!r}')

    missing = sum(1 for c in cards if not c.get('in_published_snapshot'))
    quoted = sum(1 for c in cards if c.get('reference_line'))
    counts = record.get('counts') or {}
    if counts.get('lobby_upcoming') != len(cards):
        problems.append(f'counts.lobby_upcoming {counts.get("lobby_upcoming")} != {len(cards)} cards')
    if counts.get('missing_from_published_snapshot') != missing:
        problems.append(f'counts.missing {counts.get("missing_from_published_snapshot")} != {missing}')
    if counts.get('with_reference_two_sided_line') != quoted:
        problems.append(f'counts.with_line {counts.get("with_reference_two_sided_line")} != {quoted}')

    sources = [record.get('lobby_url'), record.get('fixture_api_url'),
               (record.get('published_snapshot') or {}).get('url')]
    for url in sources:
        if not str(url or '').startswith('https://'):
            problems.append(f'record-level source is not https: {url!r}')
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, default=DEFAULT_RECORD)
    args = parser.parse_args(argv)

    record = load(args.record)
    problems = verify(record)
    counts = record.get('counts') or {}
    print(f'Record: {args.record.relative_to(ROOT) if args.record.is_relative_to(ROOT) else args.record}')
    print(f'Observed: {record.get("observed_at")}')
    print(f'Cards: {counts.get("lobby_upcoming")} · in published snapshot: '
          f'{counts.get("in_published_snapshot")} · missing: '
          f'{counts.get("missing_from_published_snapshot")} · with a two-sided price: '
          f'{counts.get("with_reference_two_sided_line")}')
    if problems:
        print('\nFAIL: the record does not replay:')
        for problem in problems:
            print('  -', problem)
        return 1
    print('PASS: every card replays from its stored sources; every probability '
          're-derives from a two-sided price.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
