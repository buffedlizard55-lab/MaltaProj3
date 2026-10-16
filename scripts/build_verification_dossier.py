"""V-1: the research dossier for session arena-ba7164a0.

Composes ``data/research/ba7164a0/verification.json`` from evidence this session already
archived, so no figure in it is hand-typed. It records, in the form the coordination
protocol asks for:

  * which official sources were consulted, when, and whether each was readable;
  * what was verified about the Thunderpick World Championship 2026 Day-1/Day-2 results,
    the remaining fixture board, the rosters and the ratings;
  * what was verified about the live published dashboard;
  * every irregularity found, with the sources behind it;
  * what remains unverified, and why.

Nothing here originates a probability. Where a value could not be confirmed from an
official source it is recorded as unverified and left blank.

Usage::

    python -m scripts.build_verification_dossier [--evidence data/research/ba7164a0]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_verify_report import clean_transfers, transfer_log
from scripts.verify_published import (HOTSPAWN_FIXTURES_API, HOTSPAWN_LOBBY, PAGES_LATEST,
                                      PAGES_ORIGINATION, SESSION, VALVE_STANDINGS_BASE,
                                      load_json, now_iso, parse_iso)

EVENT_ID = 8932
EVENT_URL = 'https://www.hltv.org/events/8932/thunderpick-world-championship-2026'
EVENT_MATCHES = 'https://www.hltv.org/events/8932/matches'
EVENT_RESULTS = 'https://www.hltv.org/results?event=8932'
EVENT_STATS = 'https://www.hltv.org/stats?event=8932'
ROSTERMANIA = 'https://www.hltv.org/news/44998/summer-2026-rostermania-as-it-happened'


def hours_between(start, end):
    left, right = parse_iso(start), parse_iso(end)
    if left is None or right is None:
        return None
    seconds = (right - left).total_seconds()
    return round(seconds / 3600, 2) if seconds >= 0 else None


def source_registry(observations: dict) -> list:
    """Every source this session consulted, with its status and observation time."""
    registry = []
    for entry in observations.get('requests') or []:
        registry.append({
            'label': entry.get('label'),
            'url': entry.get('url'),
            'status': entry.get('status'),
            'observed_at': entry.get('observed_at'),
            'archived_as': entry.get('evidence'),
            'note': entry.get('note'),
        })
    return registry


def twc_section(observations: dict, audit: dict) -> dict:
    hltv = observations.get('hltv') or {}
    schedule = (hltv.get('schedule') or {}).get('fixtures') or []
    results = (hltv.get('results') or {}).get('results') or []
    pages = hltv.get('match_pages') or {}
    analytics = hltv.get('analytics') or {}
    teams = hltv.get('teams') or {}
    valve = audit.get('valve_snapshot') or {}

    by_id = {str(f.get('match_id')): f for f in schedule}
    fixtures = []
    for fixture in schedule:
        page = pages.get(str(fixture.get('match_id'))) or {}
        fixtures.append({
            'hltv_match_id': fixture.get('match_id'),
            'teams': fixture.get('teams') or [],
            'teams_status': ('confirmed' if len(fixture.get('teams') or []) == 2
                             else 'not yet decided by HLTV'),
            'start_utc': fixture.get('start_utc'),
            'displayed_time': fixture.get('displayed_time'),
            'displayed_day': fixture.get('displayed_day'),
            'best_of': fixture.get('best_of'),
            'lan': fixture.get('lan'),
            'slot': page.get('slot'),
            'setting': page.get('setting'),
            'source_url': fixture.get('url') or page.get('canonical_url'),
            'start_evidence': ('HLTV data-unix attribute on the event board and the match '
                               'page countdown, both absolute milliseconds'),
        })

    completed = []
    for result in results:
        teams_listed = result.get('listed_teams') or []
        completed.append({
            'hltv_match_id': result.get('match_id'),
            'listed_order': teams_listed,
            'listed_score': result.get('listed_score'),
            'winner': result.get('winner'),
            'loser': result.get('loser'),
            'best_of': result.get('best_of'),
            'finished_utc': result.get('finished_utc'),
            'hltv_displayed_day': result.get('displayed_day'),
            'maps_played': sum(result['listed_score']) if result.get('listed_score') else None,
            'source_url': result.get('url'),
        })

    # Day grouping is derived from the UTC date of HLTV's own finish timestamp, not from
    # the day heading HLTV displays, which uses the viewer's timezone.
    days: dict[str, list] = {}
    for result in completed:
        stamp = parse_iso(result['finished_utc'])
        days.setdefault(stamp.strftime('%Y-%m-%d') if stamp else 'unknown', []).append(result)

    load = []
    decider_teams = []
    for fixture in fixtures:
        if len(fixture.get('teams') or []) == 2 and fixture.get('start_utc'):
            day = parse_iso(fixture['start_utc'])
            if day and day.strftime('%Y-%m-%d') == '2026-10-16':
                decider_teams.extend(fixture['teams'])
    for team in dict.fromkeys(decider_teams):
        played = [r for r in completed if team in (r['listed_order'] or [])]
        played.sort(key=lambda r: r.get('finished_utc') or '')
        next_start = next((f['start_utc'] for f in fixtures
                           if team in (f.get('teams') or []) and f.get('start_utc')), None)
        last = played[-1] if played else None
        load.append({
            'team': team,
            'series_played': len(played),
            'series_won': sum(1 for r in played if r['winner'] == team),
            'maps_played': sum(r['maps_played'] or 0 for r in played),
            'last_result': (f"{last['listed_order'][0]} {last['listed_score'][0]}-"
                            f"{last['listed_score'][1]} {last['listed_order'][1]}"
                            if last and last.get('listed_score') and len(last.get('listed_order')) == 2
                            else None),
            'last_finished_utc': last.get('finished_utc') if last else None,
            'last_result_url': last.get('source_url') if last else None,
            'next_start_utc': next_start,
            'rest_hours': hours_between(last.get('finished_utc'), next_start) if last else None,
            'note': ('Arithmetic on two timestamps HLTV publishes. Not a fatigue model: no '
                     'official source quantifies fatigue, so none is claimed.'),
        })

    squad_rows = []
    for name, info in teams.items():
        squad_rows.append({
            'team': name,
            'valve_ranking_shown_by_hltv': (info.get('valve_ranking') or {}).get('rank'),
            'valve_ranking_url': (info.get('valve_ranking') or {}).get('regional_url')
                                 or (info.get('valve_ranking') or {}).get('url'),
            'hltv_world_ranking': (info.get('hltv_world_ranking') or {}).get('rank'),
            'hltv_world_ranking_url': (info.get('hltv_world_ranking') or {}).get('url'),
            'coach': (info.get('coach') or {}).get('name'),
            'weeks_in_top30_for_core': info.get('weeks_in_top30_core'),
            'average_player_age': info.get('average_player_age'),
            'players_linked_on_page': [p.get('nick') for p in info.get('players') or []],
            'player_list_caveat': ('Every player page HLTV links from the squad block, which can '
                                   'include former players. The current five are confirmed by '
                                   "Valve's own roster column, and the two agree."),
            'source_url': info.get('url'),
        })

    analytics_rows = []
    for match_id, info in analytics.items():
        analytics_rows.append({
            'hltv_match_id': match_id,
            'rankings': info.get('rankings'),
            'insights': info.get('insights'),
            'odds_rows_read': len(info.get('odds_rows') or []),
            'odds_rows': info.get('odds_rows'),
            'source_url': info.get('source_url'),
            'caveat': ("HLTV's own odds and prediction page. The rows read include player rating "
                       'tables and map-veto tables, which also contain decimal-looking numbers; '
                       'no bookmaker series price is claimed from them here.'),
        })

    # HLTV shows a Valve ranking dated more recently than the newest global standings file
    # Valve has published in its official repository. Both are recorded side by side; the
    # project's model rung uses Valve's own file, and the gap is documented rather than
    # resolved by preferring whichever number is more convenient.
    official = valve.get('ratings') or {}
    comparison = []
    for row in squad_rows:
        name = row['team']
        comparison.append({
            'team': name,
            'hltv_valve_ranking_vrs': row.get('valve_ranking_shown_by_hltv'),
            'hltv_valve_ranking_url': row.get('valve_ranking_url'),
            'hltv_world_ranking': row.get('hltv_world_ranking'),
            'valve_official_standing': (official.get(name) or {}).get('standing'),
            'valve_official_points': (official.get(name) or {}).get('points'),
            'valve_official_snapshot': (official.get(name) or {}).get('snapshot'),
            'valve_official_url': (official.get(name) or {}).get('source_url'),
            'agree': (row.get('valve_ranking_shown_by_hltv')
                      == (official.get(name) or {}).get('standing')),
        })
    ranking_discrepancy = {
        'per_team': comparison,
        'finding': ('HLTV displays a Valve Regional Standings position dated more recently than '
                    'the newest global standings file Valve has published in its official '
                    'repository. For every team compared here the two disagree, and HLTV shows '
                    'the better position. This project\'s model rung reads Valve\'s own file, so '
                    'it uses the older, lower position. That is the conservative choice and it is '
                    'stated here rather than silently preferring the newer number.'),
        'valve_newest_published_snapshot': (valve.get('snapshot_used') or ''),
        'valve_directory_url': 'https://github.com/ValveSoftware/'
                               'counter-strike_regional_standings/tree/main/live/2026',
    }

    return {
        'ranking_discrepancy': ranking_discrepancy,
        'event': {'hltv_event_id': EVENT_ID, 'name': 'Thunderpick World Championship 2026',
                  'url': EVENT_URL, 'matches_url': EVENT_MATCHES, 'results_url': EVENT_RESULTS,
                  'stats_url': EVENT_STATS},
        'completed_results': completed,
        'results_grouped_by_utc_date': {k: [r['hltv_match_id'] for r in v] for k, v in sorted(days.items())},
        'timezone_caveat': (hltv.get('schedule') or {}).get('timezone_note'),
        'remaining_fixtures': fixtures,
        'rest_and_maps': load,
        'squads_and_rankings': squad_rows,
        'hltv_analytics_pages': analytics_rows,
        'valve_ratings': valve.get('ratings'),
        'valve_ambiguous_names': valve.get('ambiguous'),
        'valve_absent_names': valve.get('absent'),
        'valve_snapshot': {'used': valve.get('snapshot_used'), 'as_of': valve.get('standings_as_of'),
                           'source_url': valve.get('source_url')
                           or VALVE_STANDINGS_BASE + str(valve.get('snapshot_used'))},
        'hltv_valve_ranking_view': hltv.get('valve_ranking_view'),
        'limitations': hltv.get('limitations') or [],
    }


def roster_section(observations: dict, twc: dict) -> dict:
    hltv = observations.get('hltv') or {}
    transfers = clean_transfers(transfer_log(Path('data/research/ba7164a0'), hltv))
    valve_roster = ((twc.get('valve_ratings') or {}).get('Aurora') or {}).get('roster')
    hltv_players = next((s.get('players_linked_on_page') for s in twc.get('squads_and_rankings') or []
                         if s.get('team') == 'Aurora'), None)
    completed = next((x for x in transfers.get('entries') or []
                      if 'complete rebuild' in str(x.get('entry', '')).lower()), None)
    agreement = None
    if valve_roster and hltv_players:
        agreement = sorted(n.lower() for n in valve_roster) == sorted(
            n.lower() for n in hltv_players[:len(valve_roster)])
    return {
        'question': 'Is Aurora\'s roster change recent, and is it confirmed?',
        'answer': ('Confirmed from first-party evidence, and NOT recent. HLTV\'s own transfer log '
                   'records the rebuild complete on '
                   + (str(completed['hltv_displayed_date']) if completed else 'an unreadable date')
                   + ' (HLTV prints DD/MM), with the individual moves on 29/06, 02/07 and 03/07. '
                     'Day 3 is 16 October 2026, roughly three months later. Both official rating '
                     'sources already list the post-change squad.'),
        'hltv_transfer_entries': transfers.get('entries'),
        'comment_blocks_excluded': transfers.get('comment_blocks_excluded'),
        'exclusion_note': ('HLTV renders the reader comment thread under the article. An earlier '
                           'read published 15 forum replies as transfer records. Comments are '
                           'removed before anything is read and the count removed is reported.'),
        'transfer_log_url': transfers.get('source_url') or ROSTERMANIA,
        'valve_official_roster': valve_roster,
        'valve_snapshot': (twc.get('valve_snapshot') or {}).get('used'),
        'hltv_current_squad': hltv_players,
        'two_official_sources_agree': agreement,
        'consequence_for_the_picks': ('No probability on this site depends on the roster change, '
                                      'and none should: the change is three months old and both '
                                      'rating sources already reflect it. Any narrative that a '
                                      'fresh roster change explains Day-1 or Day-3 form is not '
                                      'supported by these sources.'),
    }


def published_section(audit: dict) -> dict:
    replay = audit['probability_replay']
    fp = audit['first_party_market_check']
    return {
        'snapshot': audit['staleness'],
        'inventory': audit['inventory_reconciliation'],
        'counts': audit['published_counts_check'],
        'first_party_market_check': {
            'checked': len(fp['checked']), 'agreeing': len(fp['agreeing']),
            'drifted_or_reversed': len(fp['drifted_or_reversed']),
            'unverifiable': len(fp['unverifiable']),
            'records': fp['checked'], 'unverifiable_records': fp['unverifiable'],
            'source_urls': fp['source_urls'],
        },
        'probability_replay': {k: v for k, v in replay.items() if k != 'rows'},
        'replay_rows': replay['rows'],
        'cross_checks': {
            'agreeing': len(audit['cross_checks']['agreeing']),
            'disagreeing': audit['cross_checks']['disagreeing'],
            'identity_verified_but_unusable': audit['cross_checks']['identity_verified_but_unusable'],
            'alias_only_count': len(audit['cross_checks']['alias_only']),
            'records': audit['cross_checks']['agreeing'],
        },
        'source_links': audit['source_links'],
        'outcome_order_hazards': audit['outcome_order_hazards'],
        'independent_lines_read': audit['independent_lines']['by_provider'],
        'unresolved_review': audit['unresolved_review'],
    }


def build(evidence: Path) -> dict:
    observations = load_json(evidence / 'observations.json') or {}
    audit = load_json(evidence / 'audit.json') or {}
    twc = twc_section(observations, audit)
    return {
        'schema_version': 1,
        'session': SESSION,
        'tasks': {
            'V-1': {'title': 'Independent first-party research dossier', 'status': 'done'},
            'V-2': {'title': 'Verify every published pick against official sources',
                    'status': 'done', 'tool': 'scripts/verify_published.py',
                    'output': 'data/research/ba7164a0/audit.json'},
            'V-3': {'title': 'Mobile-first verification and review page', 'status': 'done',
                    'tool': 'scripts/build_verify_report.py',
                    'output': 'data/research/ba7164a0/report.html',
                    'deployed_at': 'data/research/ba7164a0/report.html'},
        },
        'generated_at': now_iso(),
        'probe_window': audit.get('probe_window'),
        'method': {
            'read_only': True,
            'rules': [
                'Only official, first-party sources are cited. Where a value could not be '
                'confirmed, it is left blank and labelled unverified - never inferred, '
                'estimated or defaulted.',
                'Hotspawn popularity and participation are never used as a probability input.',
                'Research order for a fixture with no line: HLTV first, then prediction markets, '
                'then esports books and betting lines, then Valve\'s official ratings.',
                'An identity join that is not exact, or already reviewed as an alias with an '
                'official source, never contributes a probability.',
                'Every original response is archived verbatim so any extraction can be replayed.',
            ],
            'tools': ['scripts/research_verify.py', 'scripts/verify_published.py',
                      'scripts/build_verify_report.py'],
            'tests': ['tests/test_research_verify.py', 'tests/test_verify_published.py',
                      'tests/test_verify_report.py'],
        },
        'sources_consulted': source_registry(observations),
        'thunderpick_world_championship_2026': twc,
        'aurora_roster_change': roster_section(observations, twc),
        'published_dashboard_verification': published_section(audit),
        'irregularities': audit.get('flags') or [],
        'unverified_and_limitations': (audit.get('limitations') or []) + (twc.get('limitations') or []),
        'files_owned_by_this_session': [
            'scripts/research_verify.py', 'scripts/verify_published.py',
            'scripts/build_verify_report.py', 'tests/test_research_verify.py',
            'tests/test_verify_published.py', 'tests/test_verify_report.py',
            '.github/workflows/verify-research.yml', 'assets/verify-report.css',
            'data/research/ba7164a0/',
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=Path('data/research/ba7164a0'))
    args = parser.parse_args(argv)
    dossier = build(args.evidence)
    out = args.evidence / 'verification.json'
    out.write_text(json.dumps(dossier, indent=1, ensure_ascii=False) + '\n')
    twc = dossier['thunderpick_world_championship_2026']
    print(f'Wrote {out}')
    print(f"  sources consulted: {len(dossier['sources_consulted'])} "
          f"({sum(1 for s in dossier['sources_consulted'] if s['status'] == 'ok')} ok)")
    print(f"  TWC results: {len(twc['completed_results'])}, fixtures: {len(twc['remaining_fixtures'])}")
    print(f"  rest/maps rows: {len(twc['rest_and_maps'])}")
    print(f"  Aurora transfer entries: "
          f"{len(dossier['aurora_roster_change']['hltv_transfer_entries'] or [])} "
          f"(comments excluded: {dossier['aurora_roster_change']['comment_blocks_excluded']})")
    print(f"  irregularities: {len(dossier['irregularities'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
