"""Bounded TWC Day-3/4 source research, independent of pricing.

Ordinary public HLTV GETs only; original markup and hashes are retained.
This collector never invents fixtures, scores, lines or roster adjustments.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.domain import iso, name_key, timestamp
from scripts.hltv_match import parse_match
from scripts.sources import Client, SourceError
from scripts import twc_lines

EVENT_URL = 'https://www.hltv.org/events/8932/thunderpick-world-championship-2026'
TARGET_DAY = '2026-10-17'
FINAL_DAY = '2026-10-18'
OBSERVATIONS = Path('research/138f48b7/day4-market-observations.json')
FOLDER = Path('research/twc-current')
DAY3_URLS = [
    'https://www.hltv.org/matches/2399412/aurora-vs-9z-thunderpick-world-championship-2026',
    'https://www.hltv.org/matches/2399413/betboom-vs-legacy-thunderpick-world-championship-2026',
]


def discovered_urls(text):
    """Only match links actually published on the event's own pages."""
    soup = BeautifulSoup(text, 'html.parser')
    return sorted({urljoin('https://www.hltv.org', a['href']) for a in soup.select('a[href^="/matches/"]')
                   if re.fullmatch(r'/matches/\d+/[a-z0-9-]*thunderpick-world-championship-2026', a['href'])})


def collect(source: Path):
    folder = source / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    client = Client(folder)
    pages, urls = [], set(DAY3_URLS)
    for label, url in [('event', EVENT_URL), ('matches', 'https://www.hltv.org/events/8932/matches'),
                       ('results', 'https://www.hltv.org/results?event=8932'),
                       ('hotspawn-tournament', 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/tournaments/thunderpick-world-championships?tenantId=1'),
                       ('hotspawn-tournament-page', 'https://play.hotspawn.com/tournaments/thunderpick-world-championships')]:
        try:
            text, req = client.fetch(url, 'twc-' + label)
            raw = text.encode('utf-8')
            filename = label + '.html.gz'
            (folder / filename).write_bytes(gzip.compress(raw, mtime=0))
            pages.append({'label': label, 'request': dict(req), 'original_response': filename,
                          'stored_sha256': hashlib.sha256(raw).hexdigest()})
            urls.update(discovered_urls(text))
        except SourceError:
            pages.append({'label': label, 'request': dict(client.manifest[-1])})
    # The event has a small finite bracket. Never follow arbitrary embedded links.
    for url in sorted(urls)[:24]:
        label = 'match-' + url.split('/')[4]
        try:
            text, req = client.fetch(url, 'twc-' + label)
            raw = text.encode('utf-8')
            filename = label + '.html.gz'
            (folder / filename).write_bytes(gzip.compress(raw, mtime=0))
            facts = parse_match(text)
            pages.append({'label': label, 'request': dict(req), 'original_response': filename,
                          'stored_sha256': hashlib.sha256(raw).hexdigest(), 'facts': facts})
            print('::notice title=TWC source facts::' + json.dumps({'source_url': url, 'observed_at': req['observed_at'], **facts}))
        except SourceError:
            pages.append({'label': label, 'request': dict(client.manifest[-1])})
    report = {'schema_version': 1, 'policy': 'Source research only; canonical picks supply all probabilities. HLTV is an independent reporter, not tournament organizer verification.',
              'target_day': TARGET_DAY, 'final_day': FINAL_DAY, 'pages': pages}
    # Tournament-card lines for the semifinal day and the final day. The weekly
    # Hotspawn lobby feed does not carry TWC playoff fixtures, so without this
    # step they could never have a probability. External first-party markets
    # only; blanks stay blank. A final-day series whose participants are not
    # published yet cannot be joined on exact team names, so it stays blank too.
    rows = [{'source_url': page['request']['url'], 'observed_at': page['request'].get('observed_at'),
             'facts': page['facts']} for page in pages if page.get('facts')]
    registry_path = Path('data/origination/aliases.json')
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {'aliases': []}
    lines = twc_lines.collect(client, rows, registry, [TARGET_DAY, FINAL_DAY], datetime.now(timezone.utc))
    resolved = [r for r in lines['records'] if any(p.get('quote') for p in r['providers'])]
    report['day4_lines'] = {
        'report': 'evidence/twc-day4-lines.json', 'fixtures': len(lines['records']),
        'resolved': len(resolved), 'observed_at': lines['observed_at'],
        'days': [TARGET_DAY, FINAL_DAY],
        'detail': 'External Polymarket/Kalshi full-series books for TWC fixtures that are absent from the weekly '
                  'Hotspawn inventory. Probabilities are recomputed from the retained originals at build time.'}
    print('::notice title=TWC day4 lines::' + json.dumps({'observed_at': lines['observed_at'],
                                                          'fixtures': len(lines['records']),
                                                          'resolved': len(resolved),
                                                          'days': [TARGET_DAY, FINAL_DAY]}))
    (folder / 'source-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


def page_title(raw: str) -> str:
    """HLTV's own page title, e.g. '… - Grand Final | HLTV.org'.

    The title is the source's own label for the bracket slot. It is read from
    the retained original, never from a hand-written mapping.
    """
    match = re.search(r'<title>(.*?)</title>', raw, re.S | re.I)
    return ' '.join(match.group(1).split()) if match else ''


def load(source: Path):
    """Replay originals, not stored extracted facts. Fail closed on tampering."""
    folder = source / FOLDER
    path = folder / 'source-report.json'
    if not path.exists():
        folder = source / 'research/8a6a5a84/twc-current'
        path = folder / 'source-report.json'
    if not path.exists():
        return {'pages': [], 'target_day': TARGET_DAY, 'final_day': FINAL_DAY}
    report = json.loads(path.read_text())
    records = []
    for page in report['pages']:
        request = page['request']
        if request.get('status') != 'ok' or not page.get('original_response'):
            continue
        original = folder / page['original_response']
        if original.resolve().parent != folder.resolve():
            raise ValueError('TWC current original path escapes research folder')
        raw = gzip.decompress(original.read_bytes())
        if hashlib.sha256(raw).hexdigest() != page.get('stored_sha256'):
            raise ValueError('TWC current original hash mismatch')
        if not re.fullmatch(r'https://www\.hltv\.org/matches/\d+/[a-z0-9-]*thunderpick-world-championship-2026', request['url']):
            continue
        text = raw.decode('utf-8')
        facts = parse_match(text)
        # A malformed or unrelated page cannot introduce a fixture/result.
        if facts.get('event_url') != EVENT_URL or not facts.get('starts_at'):
            continue
        # A final-day page legitimately has no published participants yet, so
        # the team list may be empty. The page is still kept: its own title
        # names the bracket slot and its schedule is a real published fact.
        records.append({'source_url': request['url'], 'observed_at': request['observed_at'],
                        'facts': facts, 'title': page_title(text)})
    return {'pages': records, 'target_day': TARGET_DAY, 'final_day': FINAL_DAY}


def load_observations(source: Path) -> list:
    """Dated market observations captured by a scoped research fetch.

    These are display-only context for fixtures the pipeline has not collected
    yet. They are never merged into a canonical pair, never used as a pricing
    input and never presented as freshly collected evidence.
    """
    path = source / OBSERVATIONS
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except ValueError:
        return []
    return payload.get('fixtures') or []


def derive_day4(data, source: Path, now):
    """Join only exact teams/event/date/time; use canonical prices unchanged."""
    from scripts.domain import name_key
    from scripts.pick_safety import presentation, valid_pair
    research = load(source)
    complete = data.get('complete_picks') or {}
    if complete and complete.get('source_snapshot_at') != data.get('inventory_observed_at'):
        raise ValueError('Day-4 picks belong to another inventory observation')
    by_id = {m['id']: m for m in complete.get('matches', [])}
    event_name = 'Thunderpick World Championship 2026'
    fixtures = [m for m in data['matches'] if name_key(m.get('competition') or '') == name_key(event_name)
                and str(m.get('starts_at') or '').startswith(TARGET_DAY)]
    records = [r for r in research['pages'] if str(r['facts'].get('starts_at') or '').startswith(TARGET_DAY)]
    rows, consumed = [], set()
    for fixture in fixtures:
        row = by_id.get(fixture['id'])
        if row and any(row.get(k) != fixture.get(k) for k in ['teams', 'starts_at', 'locks_at']):
            raise ValueError('Day-4 canonical fixture mismatch')
        names = [t.get('name') for t in fixture['teams']]
        pair = {name_key(n or '') for n in names}
        candidates = [r for r in records if {name_key(n) for n in r['facts']['teams']} == pair
                      and r['facts']['starts_at'] == fixture['starts_at']]
        record = candidates[0] if len(candidates) == 1 else None
        if record:
            consumed.add(record['source_url'])
        analysis = row.get('origination') if row else None
        pick = row.get('pick_index') if row and analysis else None
        if analysis:
            p = analysis.get('probabilities')
            if not valid_pair(p):
                raise ValueError('Invalid canonical Day-4 probability pair')
            expected = None if abs(p[0] - p[1]) < 1e-8 else (0 if p[0] > p[1] else 1)
            if pick != expected:
                raise ValueError('Day-4 direction differs from canonical higher probability')
        canonical = dict(fixture, origination=analysis)
        state = presentation(canonical, data.get('inventory_observed_at'), data.get('coverage_complete'), now)
        alternative = None
        if state['current'] and pick is not None and analysis['method'] in {'market', 'bookmaker', 'consensus'}:
            dog = 1 - pick
            if 0.30 <= analysis['probabilities'][dog] < 0.50:
                alternative = {'team': names[dog], 'probability': analysis['probabilities'][dog],
                               'cost_per_base_point': round(analysis['probabilities'][pick] - analysis['probabilities'][dog], 8)}
        rows.append({'fixture': canonical, 'hltv': record, 'teams': names, 'analysis': analysis,
                     'pick_index': pick, 'pick': names[pick] if pick is not None else None,
                     'state': state, 'alternative': alternative,
                     'limitation': None if analysis else 'No supported estimate. HLTV, first-party exchange/books and exact-five Valve fallback could not establish usable inputs; see the complete match research trail.'})
    # Report independently listed fixtures even before Hotspawn adds them, but
    # never claim they are in the pick-em inventory or manufacture a lock/price.
    unlisted = [r for r in records if r['source_url'] not in consumed]
    # Tournament-card lines are replayed from retained external originals. They
    # are attached beside the canonical pair, never over it, and only a fixture
    # without a supported estimate is allowed to use one as its own line.
    lines = twc_lines.load(source, now)
    day_lines = twc_lines.for_day(lines, TARGET_DAY)
    for row in rows:
        if row['analysis'] is None:
            row['line'] = twc_lines.for_fixture(lines, row['teams'], row['fixture']['starts_at'])
            row['line_underdog'] = twc_lines.underdog(row['line']) if row.get('line') else None
    for record in unlisted:
        record['line'] = twc_lines.for_fixture(lines, record['facts']['teams'], record['facts']['starts_at'])
        record['line_underdog'] = twc_lines.underdog(record['line']) if record.get('line') else None
    day3 = []
    for r in research['pages']:
        facts = r['facts']
        if str(facts.get('starts_at') or '').startswith('2026-10-16'):
            day3.append({'label': r['source_url'].split('/')[4], 'teams': facts['teams'],
                         'score': facts['score'], 'maps': facts['maps'], 'finished': facts['finished'],
                         'source_url': r['source_url'], 'observed_at': r['observed_at'],
                         'lesson': 'Use the completed series as matchup context, not a new win-rate sample or proof the earlier odds were wrong.' if facts['score'] else 'Result unverified. A past scheduled start does not establish a winner.'})
    return {'schema_version': 1, 'generated_at': data.get('generated_at'), 'source_snapshot_at': data.get('inventory_observed_at'), 'evaluated_at': iso(now), 'event_day': TARGET_DAY, 'research_available': bool(research['pages']), 'matches': rows, 'not_in_hotspawn_snapshot': unlisted,
            'day3_results': day3, 'research_report': str(FOLDER / 'source-report.json') if (source / FOLDER / 'source-report.json').exists() else 'research/8a6a5a84/twc-current/source-report.json',
            'lines': {'available': lines['available'], 'day': TARGET_DAY, 'observed_at': lines['observed_at'],
                      'report_path': lines['report_path'], 'policy': lines['policy'],
                      'resolved': day_lines['resolved'],
                      'total': day_lines['total'],
                      'fixtures': [{'fixture_id': m['fixture_id'], 'teams': m['teams'], 'starts_at': m['starts_at'],
                                    'probabilities': m.get('probabilities'), 'pick_index': m.get('pick_index'),
                                    'method': m.get('method'), 'label': m.get('label'), 'observed_at': m.get('observed_at'),
                                    'providers': m.get('providers') or [], 'attempts': m.get('attempts') or [],
                                    'limitations': m.get('limitations') or [], 'source_url': m.get('source_url')}
                                   for m in day_lines['matches']]},
            'observations': load_observations(source),
            'observations_path': OBSERVATIONS.as_posix(),
            'policy': 'Exact canonical probabilities; no historical, roster, crowd, rest or result premium.'}


# ---------------------------------------------------------------------------
# Day 5 — the final day (18 October 2026)
# ---------------------------------------------------------------------------

GRAND_FINAL = 'grand final'
THIRD_PLACE = '3rd place'


def slot_of(title: str) -> str | None:
    """The bracket slot, read from HLTV's own page title.

    HLTV titles the two semifinals as ordinary match-ups and the two final-day
    series explicitly ("… - Grand Final | HLTV.org" and "… - 3rd Place Decider
    Match | HLTV.org"). The label is taken from the source, not from a
    hand-written list of match ids.
    """
    lowered = (title or '').casefold()
    if GRAND_FINAL in lowered:
        return 'Grand Final'
    if THIRD_PLACE in lowered or 'third place' in lowered:
        return 'Third-place decider'
    return None


def published_teams(facts: dict) -> list[str] | None:
    """Both participant names, or None when the source has not published them."""
    teams = facts.get('teams') or []
    if len(teams) != 2:
        return None
    names = [t if isinstance(t, str) else None for t in teams]
    if not all(isinstance(n, str) and n.strip() for n in names):
        return None
    if len({name_key(n) for n in names}) != 2:
        return None
    return [n.strip() for n in names]


def series_outcome(record: dict) -> dict | None:
    """Winner and loser of a finished series, from the published final score.

    Nothing is inferred from a map score, a partial series or a past start.
    A series that is not marked finished, or whose final score is missing, has
    no outcome here.
    """
    facts = record.get('facts') or {}
    teams = published_teams(facts)
    score = facts.get('score')
    if not teams or not facts.get('finished') or not score or len(score) != 2:
        return None
    if not all(isinstance(v, int) for v in score) or score[0] == score[1]:
        return None
    winner = teams[0] if score[0] > score[1] else teams[1]
    loser = teams[1] if score[0] > score[1] else teams[0]
    return {'teams': teams, 'score': score, 'winner': winner, 'loser': loser,
            'source_url': record.get('source_url'), 'observed_at': record.get('observed_at'),
            'title': record.get('title')}


def derive_day5(data, source: Path, now):
    """The final day: the two final-day slots, their participants and any line.

    The participants of a final-day series are only published once the
    semifinals are decided. When HLTV has published them, they are used
    directly. When it has not, they are derived from the *verified* semifinal
    final scores using the bracket that HLTV's own titles describe: the winners
    of the two semifinals meet in the grand final and the losers meet in the
    third-place decider. A derivation is always labelled as one and always
    links the semifinal pages it came from. If a semifinal has no published
    final score, the participants stay blank.
    """
    research = load(source)
    lines = twc_lines.load(source, now)
    day_lines = twc_lines.for_day(lines, FINAL_DAY)
    records = [r for r in research['pages'] if str((r['facts'] or {}).get('starts_at') or '').startswith(FINAL_DAY)]
    semifinals = [r for r in research['pages']
                  if str((r['facts'] or {}).get('starts_at') or '').startswith(TARGET_DAY)
                  and slot_of(r.get('title')) is None]
    outcomes = [o for o in (series_outcome(r) for r in semifinals) if o]
    # Bracket order: the grand final takes the two semifinal winners, the
    # third-place decider the two losers, in the order HLTV scheduled them.
    winners = [o['winner'] for o in outcomes]
    losers = [o['loser'] for o in outcomes]
    slots = []
    for record in sorted(records, key=lambda r: str((r['facts'] or {}).get('starts_at') or '')):
        facts = record['facts']
        slot = slot_of(record.get('title'))
        named = published_teams(facts)
        derived = None
        basis = None
        if named:
            teams, basis = named, 'published'
        else:
            pool = winners if slot == 'Grand Final' else losers
            if len(pool) == 2:
                teams, basis = list(pool), 'derived'
                derived = {'from': [o['source_url'] for o in outcomes],
                           'rule': ('HLTV titles the two semifinals, the grand final and the third-place decider. '
                                    'The winners of the two semifinals meet in the grand final and the losers meet '
                                    'in the third-place decider, so the participants are derived from the verified '
                                    'semifinal final scores.')}
            else:
                teams, basis = None, 'undecided'
        line = None
        if teams:
            line = twc_lines.for_fixture(lines, teams, facts.get('starts_at'))
        limitation = None
        if not teams:
            limitation = ('The participants of this series are not published yet. '
                          + ('The semifinal final score that decides them has not been published in a retained '
                             'source, so no participant is named and no probability is shown.'
                             if basis == 'undecided' else
                             'No verified semifinal result is available, so no participant is named.'))
        elif line is None:
            limitation = ('No validated external full-series book joins this exact pair and start time, so no '
                          'probability is shown. Hotspawn participation, tournament outrights and fan votes are '
                          'never substituted for a missing price.')
        slots.append({'slot': slot or 'Final-day series', 'teams': teams,
                      'participant_basis': basis, 'derivation': derived,
                      'starts_at': facts.get('starts_at'),
                      'hltv_match_id': record['source_url'].split('/')[4],
                      'source_url': record['source_url'], 'observed_at': record['observed_at'],
                      'title': record.get('title'),
                      'line': line,
                      'line_underdog': twc_lines.underdog(line) if line else None,
                      'limitation': limitation})
    # The verified ladder that guides the final day: every series of this
    # event that a retained original has finished, with its published score.
    ladder = []
    for record in research['pages']:
        facts = record.get('facts') or {}
        outcome = series_outcome(record)
        if not outcome:
            continue
        ladder.append({'teams': outcome['teams'], 'score': outcome['score'],
                       'winner': outcome['winner'], 'loser': outcome['loser'],
                       'maps': facts.get('maps') or [],
                       'starts_at': facts.get('starts_at'), 'title': record.get('title'),
                       'source_url': record['source_url'], 'observed_at': record['observed_at']})
    ladder.sort(key=lambda r: (str(r['starts_at'] or ''), r['source_url']))
    return {'schema_version': 1, 'generated_at': data.get('generated_at'),
            'source_snapshot_at': data.get('inventory_observed_at'), 'evaluated_at': iso(now),
            'event_day': FINAL_DAY, 'research_available': bool(research['pages']),
            'slots': slots, 'semifinals': [{'teams': (r['facts'] or {}).get('teams'),
                                           'starts_at': (r['facts'] or {}).get('starts_at'),
                                           'score': (r['facts'] or {}).get('score'),
                                           'finished': (r['facts'] or {}).get('finished'),
                                           'source_url': r['source_url'], 'title': r.get('title'),
                                           'observed_at': r['observed_at']} for r in semifinals],
            'ladder': ladder,
            'lines': {'available': day_lines['available'], 'day': FINAL_DAY,
                      'observed_at': day_lines['observed_at'],
                      'report_path': lines.get('report_path'), 'policy': lines.get('policy'),
                      'resolved': day_lines['resolved'], 'total': day_lines['total'],
                      'fixtures': [{'fixture_id': m['fixture_id'], 'teams': m['teams'],
                                    'starts_at': m['starts_at'], 'probabilities': m.get('probabilities'),
                                    'pick_index': m.get('pick_index'), 'method': m.get('method'),
                                    'label': m.get('label'), 'observed_at': m.get('observed_at'),
                                    'providers': m.get('providers') or [], 'attempts': m.get('attempts') or [],
                                    'limitations': m.get('limitations') or [], 'source_url': m.get('source_url')}
                                   for m in day_lines['matches']]},
            'research_report': str(FOLDER / 'source-report.json') if (source / FOLDER / 'source-report.json').exists() else 'research/8a6a5a84/twc-current/source-report.json',
            'policy': ('Final-day participants are published or derived from verified semifinal results; no '
                       'probability is invented for a series whose participants are not yet decided. Prices are '
                       'external first-party books only. Day 1-4 results are context, never a probability premium.')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    args = parser.parse_args()
    collect(args.data)


if __name__ == '__main__':
    main()
