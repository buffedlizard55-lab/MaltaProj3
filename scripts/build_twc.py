"""One TWC view of the audited complete-picks feed, never a second pricing model.

Days 1–2 are replayed from retained, hash-checked original HLTV match pages.
Day-3 probabilities and default picks are copied from this build's canonical
origination snapshot. Editorial context never adds a roster/rest/form premium.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.domain import iso, timestamp, name_key, is_fresh
from scripts.hltv_match import parse_match

RESEARCH = Path('research/6426358d/observed-0723')
EVENT = 'Thunderpick World Championship 2026'
DAY = '2026-10-16'
MONEY = {'market', 'bookmaker', 'consensus'}
DAY3 = [('day3-aurora-9z', ['Aurora', '9z'], 'Group A decider'),
        ('day3-betboom-legacy', ['BetBoom', 'Legacy'], 'Group B decider')]
LESSONS = {
    'day1-9z-aurora': '9z won both maps, including Nuke 13–1. A repeat upset is plausible, not established as underpriced. Do not turn a head-to-head result into a new win rate.',
    'day1-falcons-nip': 'Ancient went to overtime. A 2–0 series score is not the same as two easy maps.',
    'day1-legacy-parivision': '13–11 and 16–14 were close map wins. The sweep alone would hide that context.',
    'day1-furia-betboom': 'FURIA won both maps. The round scores add context, not a quantitative adjustment.',
    'day2-aurora-nip': 'Aurora won both maps after the opening loss. That is evidence against blindly fading them, not proof that onboarding issues are fixed.',
    'day2-9z-falcons': '9z took Mirage but lost the series. It supports upset plausibility; one win or loss cannot tell us whether a prematch probability was accurate.',
    'day2-parivision-betboom': 'BetBoom recovered from a map down. That is a reason to inspect their decider, not proof of momentum or a pricing edge.',
    'day2-legacy-furia': 'Legacy won Cache before losing the next two maps. Both decider opponents have a map-level case; avoid a narrative-only favorite or underdog.',
}


def load_research(source: Path) -> dict:
    folder = source / RESEARCH
    report_path = folder / 'source-report.json'
    if not report_path.exists():
        return {'observed_at': None, 'pages': {}, 'report_path': RESEARCH.as_posix() + '/source-report.json'}
    report = json.loads(report_path.read_text())
    pages = {}
    for page in report['pages']:
        req = page['request']
        record = {'source_url': req['url'], 'observed_at': req['observed_at'], 'facts': None}
        original = page.get('original_response')
        if original and req.get('status') == 'ok':
            path = folder / original
            # Do not expose or trust a path outside this research directory.
            if path.resolve().parent != folder.resolve():
                raise ValueError('TWC original-response path escapes its research directory')
            raw = gzip.decompress(path.read_bytes())
            if hashlib.sha256(raw).hexdigest() != req.get('response_sha256'):
                raise ValueError('TWC original-response hash mismatch: ' + page['label'])
            text = raw.decode()
            if '/matches/' in req['url']:
                record['facts'] = parse_match(text)
            elif page['label'] == 'aurora-rebuild':
                soup = BeautifulSoup(text, 'html.parser')
                date = soup.select_one('.articleDate[data-unix]')
                dt = timestamp(date.get('data-unix')) if date else None
                body = soup.select_one('.newstext-con')
                article = body.get_text(' ', strip=True) if body else ''
                roster_names = ['kyxsan', 'Jimpphat', 'ash', 'MAJ3R', 'soulfly', 'Fabre']
                record['report_date'] = iso(dt)[:10] if dt else None
                record['rebuild_supported'] = all(name.casefold() in article.casefold() for name in roster_names)
        pages[page['label']] = record
    return {'observed_at': max((r['request']['observed_at'] for r in report['pages']), default=None),
            'pages': pages, 'report_path': RESEARCH.as_posix() + '/source-report.json'}


def derive(data: dict, source: Path, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    research = load_research(source)
    complete = data.get('complete_picks')
    if complete is None and (source / 'origination.json').exists():
        complete = json.loads((source / 'origination.json').read_text())
    if complete and complete.get('source_snapshot_at') != data.get('inventory_observed_at'):
        raise ValueError('TWC picks belong to a different inventory observation')
    full = {m['id']: m for m in (complete or {}).get('matches', [])}
    history = []
    for label, lesson in LESSONS.items():
        record = research['pages'].get(label) or {}
        facts = record.get('facts') or {}
        # Both the series header and every played-map row are original source
        # values. No reverse derivation of missing scores from other fields.
        history.append({'label': label, 'day': 1 if label.startswith('day1') else 2,
                        'teams': facts.get('teams'), 'score': facts.get('score'),
                        'maps': facts.get('maps') or [], 'finished': facts.get('finished', False),
                        'source_url': record.get('source_url'), 'observed_at': record.get('observed_at'),
                        'lesson': lesson if facts.get('score') else 'Historical values unverified; no match-specific conclusion inferred.'})
    day3 = []
    for label, expected_names, stage in DAY3:
        record = research['pages'].get(label) or {}
        expected_pair = {name_key(n) for n in expected_names}
        fixtures = [m for m in data['matches'] if name_key(m.get('competition') or '') == name_key(EVENT)
                    and {name_key(t.get('name') or '') for t in m['teams']} == expected_pair
                    and str(m.get('starts_at') or '').startswith(DAY)]
        match = fixtures[0] if len(fixtures) == 1 else None
        row = full.get(match['id']) if match else None
        if match and row and (row['teams'] != match['teams'] or row.get('starts_at') != match.get('starts_at')
                            or row.get('locks_at') != match.get('locks_at')):
            raise ValueError('TWC fixture facts differ from the complete-picks feed')
        a = row.get('origination') if row else None
        names = [t['name'] for t in match['teams']] if match else expected_names
        pick = row.get('pick_index') if row and a else None
        reason = None
        status = 'open'
        start = timestamp(match.get('starts_at')) if match else None
        lock = timestamp(match.get('locks_at')) if match else None
        if not match:
            status, reason = 'unresolved', 'No unique Hotspawn fixture for this pair and event date in this snapshot. No pick or probability inferred.'
        elif match.get('availability') == 'past' or (start and start <= now) or (lock and lock <= now):
            status, reason = 'closed', 'Closed for picks or past its scheduled start; any estimate is retained for audit, not a current pick. Result is not inferred.'
        elif not a:
            status, reason = 'unresolved', 'No supported probability in the complete-picks feed. See the source-by-source research trail.'
        elif (not data.get('coverage_complete') or not is_fresh(data.get('inventory_observed_at'), now)
              or not is_fresh(a.get('observed_at'), now)):
            status, reason = 'stale', 'Inventory or price freshness is unverified. This is a snapshot estimate, not a current pick.'
        elif not lock:
            status, reason = 'unverified-lock', 'Hotspawn lock deadline is unverified; confirm on the official lobby before choosing.'
        if a:
            p = a.get('probabilities')
            if not isinstance(p, list) or len(p) != 2 or not all(0 < x < 1 for x in p) or abs(sum(p) - 1) > 1e-7:
                raise ValueError('Invalid canonical TWC probability pair')
            expected_pick = None if abs(p[0] - p[1]) < 1e-8 else (0 if p[0] > p[1] else 1)
            if pick != expected_pick:
                raise ValueError('TWC default pick does not match the canonical higher-probability side')
        candidate = None
        if a and pick is not None and a['method'] in MONEY and status == 'open':
            dog = 1 - pick
            if 0.30 <= a['probabilities'][dog] < 0.50:
                candidate = {'team': names[dog], 'probability': a['probabilities'][dog],
                             'cost_per_base_point': round(a['probabilities'][pick] - a['probabilities'][dog], 8)}
        day3.append({'id': match['id'] if match else None, 'label': label, 'stage': stage,
                     'teams': names, 'starts_at': match.get('starts_at') if match else None,
                     'locks_at': match.get('locks_at') if match else None,
                     'source_url': match.get('source_url') if match else None,
                     'analysis': a, 'pick_index': pick, 'pick': names[pick] if pick is not None else None,
                     'status': status, 'limitation': reason, 'contrarian_candidate_at_build': candidate,
                     'research': (row or {}).get('research', []), 'hltv': record})
    return {'schema_version': 2, 'event': EVENT, 'event_day': DAY,
            'generated_at': data['generated_at'], 'evaluated_at': iso(now),
            'source_snapshot_at': data.get('inventory_observed_at'),
            'source_generated_at': (complete or {}).get('generated_at'),
            'research_observed_at': research['observed_at'], 'research_report': research['report_path'],
            'probability_policy': 'Exact copy of the audited complete-picks snapshot. No crowd polls, fan votes, outrights, historical narrative or Hotspawn percentages enter probabilities.',
            'day1_results': [r for r in history if r['day'] == 1],
            'day2_results': [r for r in history if r['day'] == 2],
            'day3_matches': day3,
            'roster_report': research['pages'].get('aurora-rebuild'),
            'roster_listings': {label: research['pages'].get(label) for label in ('day1-9z-aurora', 'day2-aurora-nip', 'day3-aurora-9z')},
            'unresolved': [r['label'] for r in day3 if not r['analysis']],
            'global_unresolved': (complete or {}).get('counts', {}).get('unresolved'),
            'limitations': ['All probabilities are estimates, not verified true win chances or guaranteed outcomes.',
                            'HLTV is an independent results/roster reporter, not primary tournament-organizer verification.',
                            'The historical review is dated; current quotes refresh with the canonical four-hour pipeline.',
                            'Roster onboarding, vetoes, illness, travel, actual rest hours and opponent ownership are not quantified.',
                            'The 30% underdog watch threshold is editorial and uncalibrated. It never changes the default pick.',
                            'A lower-probability pick reduces expected base points. Streak costs and leaderboard gains are not forecast.']}


def results_table(rows, prefix):
    from scripts.build import e, external, local_time, blank
    out = '<div class="table-scroll"><table class="simple-table twc-results"><caption>HLTV-reported series and played maps; interpretation is our analysis, not a new probability</caption><thead><tr><th>Match / result</th><th>Played maps</th><th>Lesson for the next pick / source</th></tr></thead><tbody>'
    for row in rows:
        names = ' vs '.join(row['teams']) if row['teams'] else 'Unverified match'
        score = '–'.join(str(x) for x in row['score']) if row['score'] else None
        maps = '<br>'.join(f'{e(m["map"])} {m["a"]}–{m["b"]}' for m in row['maps']) or blank()
        source = external(row['source_url'], 'HLTV match record') if row['source_url'] else blank()
        out += (f'<tr><th scope="row">{e(names)}<small>{e(score) if score else blank()} · HLTV-reported</small></th>'
                f'<td>{maps}</td><td>{e(row["lesson"])}<div class="evidence-links">{source}</div>'
                f'<small>Read {local_time(row["observed_at"])}</small></td></tr>')
    return out + '</tbody></table></div>'


def render(data: dict, prefix: str, source: Path) -> str:
    from scripts.build import e, heading, external, local_time, blank, badge
    report = derive(data, source)
    from scripts.twc_research import derive_day4
    guide = data.get('_twc_day4')
    if guide is None:
        guide = derive_day4(data, source, datetime.now(timezone.utc))
    report['day4'] = guide
    from scripts.day5 import derive as derive_day5, render as render_day5
    final_day = data.get('_twc_day5')
    if final_day is None:
        final_day = derive_day5(data, source, datetime.now(timezone.utc))
    report['day5'] = final_day
    data['_twc_report'] = report
    out = heading('Thunderpick World Championship 2026 · 18 October', 'TWC Day 5: picks & review',
                  'Final-day probabilities. Days 1–4 evidence. Explicit gaps, without invented odds.')
    out += (f'<section class="twc-brief" id="twc-summary"><p class="eyebrow">Executive summary</p>'
            '<h2>Keep the default. Make any upset play deliberate.</h2>'
            '<p>The default is the higher-probability side in the complete picks list below. '
            'For leaderboard catch-up, consider at most one optional underdog, only with a fresh money-backed line '
            'and a specific matchup case. A plausible upset is not evidence that a market is wrong.</p>'
            f'<nav class="briefing-links" aria-label="TWC sections"><a href="#day-five-picks">Day 5 picks</a><a href="#day-four-results">Day 4 results</a><a href="#day-five-unresolved">Final-day limitations</a><a href="#day-four-picks">Day 4 picks</a><a href="#day-three-results">Day 3 results</a><a href="#day-three-picks">Day 3 snapshot</a>'
            '<a href="#day-one-results">Day 1 results</a><a href="#day-two-results">Day 2 results</a>'
            '<a href="#roster-check">Roster &amp; rest check</a><a href="#unresolved">Unresolved &amp; limitations</a>'
            f'<a href="{prefix}origination/#picks">Every Hotspawn CS2 pick →</a></nav>'
            f'<p class="small">Inventory {local_time(report["source_snapshot_at"])} · pricing snapshot '
            f'{local_time(report["source_generated_at"])}. Times use the page timezone selector. '
            'All probabilities below regenerate with the same four-hour publisher as the full list.</p></section>')
    out += render_day5(final_day, prefix)
    out += render_day4(guide, prefix)
    out += '<details class="twc-history"><summary>Historical Day 3 probability snapshot &amp; audit</summary>'
    out += '<section class="content-section twc-section" id="day-three-picks"><div class="section-heading"><div><p class="eyebrow">Same numbers as the complete picks list</p><h2>Day 3 probability snapshot &amp; audit</h2></div></div><div class="twc-grid">'
    for row in report['day3_matches']:
        a, pick = row['analysis'], row['pick_index']
        inactive = row['status'] != 'open'
        out += (f'<article class="pick-card twc-card match-row" id="twc-{e(row["label"])}" '
                f'data-start="{e(row["starts_at"] or "")}" data-lock="{e(row["locks_at"] or "")}" '
                f'data-price-time="{e(a["observed_at"] if a else "")}"><p class="eyebrow">{e(row["stage"])}</p>'
                f'<h3>{e(" vs ".join(row["teams"]))}</h3><p>Start {local_time(row["starts_at"])}<br>'
                f'Hotspawn lock {local_time(row["locks_at"])}</p><span class="availability" data-availability>'
                f'{"Open for picks at build" if not inactive else e(row["status"])}</span>')
        for i, name in enumerate(row['teams']):
            value = f'{a["probabilities"][i] * 100:.1f}%' if a else '—'
            fair = f'<small>Calculated fair line {a["fair_decimal"][i]:.3f}</small>' if a else '<small>unverified · no default 50/50</small>'
            out += f'<div class="twc-prob {"twc-favorite" if i == pick else ""}"><span>{e(name)}{fair}</span><strong>{value}</strong></div>'
        if a and pick is not None:
            caption = f'{a["probabilities"][pick] * 100:.1f}% estimated series-win chance · default, not a guarantee'
            out += (f'<div class="pick-choice {"inactive-pick" if inactive else ""}" data-pick-choice><strong data-original="{e(row["pick"])}">'
                    f'{"Snapshot: " if inactive else "Default pick: "}{e(row["pick"])}</strong></div>'
                    f'<p class="pick-caption" data-pick-caption data-original="{e(caption)}">{e(row["limitation"] or caption)}</p>')
        elif a:
            out += '<p><strong>No directional edge.</strong> Equal estimate; no arbitrary side selected.</p>'
        else:
            out += '<p><strong class="unverified">Pick — unverified.</strong> No supported inputs; see limitations.</p>'
        if a:
            money = a['method'] in MONEY
            out += '<p>' + badge('External money line' if money else 'Uncalibrated rating model', 'green' if money else 'purple') + '</p>'
            out += f'<p class="small">{e(a["label"])}<br>Observed {local_time(a["observed_at"])}</p>'
            links = {q.get('source_url'): q.get('provider') or 'Pricing source' for q in a.get('quotes', []) if q.get('source_url')}
            links.setdefault(a['source_url'], a.get('source') or 'Analysis source')
            out += '<div class="evidence-links">' + ''.join(external(url, label) for url, label in links.items()) + '</div>'
        links = []
        if row['source_url']:
            links.append(external(row['source_url'], 'Hotspawn fixture'))
        if row['hltv'].get('source_url'):
            links.append(external(row['hltv']['source_url'], 'HLTV match listing'))
        if row['id']:
            links.append(f'<a href="{prefix}origination/#match-{e(row["id"])}">Full quote &amp; identity audit →</a>')
        out += '<div class="evidence-links">' + ''.join(links) + '</div>'
        candidate = row['contrarian_candidate_at_build']
        if candidate:
            out += (f'<aside class="twc-watch"><strong>Optional watch at build: {e(candidate["team"])}</strong>'
                    f'<p>{candidate["probability"] * 100:.1f}% estimated chance. Switching from the default costs '
                    f'{candidate["cost_per_base_point"]:.3f} expected points per 1 base point on offer, before streak effects. '
                    'Not a proven edge or an automatic switch. Re-check the timestamp, lock and lineup before submitting.</p></aside>')
        else:
            out += '<p class="small">No current underdog is promoted by this page: the 30% money-backed, fresh, unlocked screen must pass first.</p>'
        out += '</article>'
    out += '</div><p class="section-intro">The probability source, not a fan poll, decides the default. '
    out += (f'Use <a href="{prefix}strategy/">the points-aware leaderboard plan</a> for the whole card. '
            'This TWC screen is a transparent risk choice, not an assertion of profitable mispricing.</p></section>')
    out += '</details>'
    out += '<section class="content-section" id="day-one-results"><div class="section-heading"><div><p class="eyebrow">14 October · historical</p><h2>Day 1: the upset in context</h2></div></div>'
    out += results_table(report['day1_results'], prefix) + '</section>'
    out += '<section class="content-section" id="day-two-results"><div class="section-heading"><div><p class="eyebrow">15 October · historical</p><h2>Day 2: what changes for Day 3</h2></div></div>'
    out += results_table(report['day2_results'], prefix) + '</section>'
    out += ('<section class="content-section prose" id="decision-guide"><p class="eyebrow">Our interpretation · no numerical adjustment</p>'
            '<h2>Historical Day-3 decision context — not Day-4 instructions</h2><p><strong>9z has a concrete matchup case:</strong> the Day 1 win over Aurora '
            'and a Day 2 map against Falcons. The counterevidence is Aurora’s Day 2 sweep and the current favorite price. '
            'Do not double-count facts the market may already know.</p><p><strong>BetBoom is not automatically a bad upset choice:</strong> '
            'they recovered against PARIVISION. Whether their current line makes them a credible alternative is displayed above, '
            'not borrowed from a fan vote or from tournament outright odds. Legacy’s map against FURIA is counterevidence.</p>'
            '<p>The historical two-decider plan was to keep both defaults for expected points. If deliberately accepting more variance to catch up, '
            'limit this two-match card to one optional switch. Ownership, leaderboard deficit and streak state are unavailable, '
            'so no chance of climbing places is claimed.</p></section>')
    roster = report['roster_report'] or {}
    out += '<section class="content-section" id="roster-check"><div class="section-heading"><div><p class="eyebrow">Context is not causation</p><h2>Aurora roster &amp; rest check</h2></div></div><div class="table-scroll"><table class="simple-table"><caption>Source-backed roster context and explicit unverified values</caption><thead><tr><th>Check</th><th>Published finding / limitation</th><th>Source</th></tr></thead><tbody>'
    statement = (f'HLTV’s {roster.get("report_date") or "date-unverified"} report says kyxsan, Jimpphat and coach ash joined, replacing MAJ3R, soulfly and coach Fabre. This is a summer rebuild, not evidence of a new October change or the cause of this upset.'
                 if roster.get('rebuild_supported') else '— unverified. No roster-change claim inferred.')
    out += '<tr><th scope="row">Summer rebuild</th><td>' + e(statement) + '</td><td>' + (external(roster['source_url'], 'HLTV transfer report (secondary)') if roster.get('source_url') else blank()) + '</td></tr>'
    for label, title in [('day1-9z-aurora', 'Day 1 listed Aurora players'), ('day2-aurora-nip', 'Day 2 listed Aurora players'), ('day3-aurora-9z', 'Day 3 listed Aurora players (dated observation)')]:
        record = report['roster_listings'].get(label) or {}
        facts = record.get('facts') or {}
        roster_ = [r['roster'] for r in facts.get('lineups', []) if name_key(r['name']) == 'aurora' and r['roster']]
        value = ', '.join(roster_[0]) if len(roster_) == 1 else None
        out += f'<tr><th scope="row">{e(title)}</th><td>{e(value) if value else blank()}<small>Observed {local_time(record.get("observed_at"))}; a listing is not final lineup confirmation.</small></td><td>' + (external(record['source_url'], 'HLTV match lineup') if record.get('source_url') else blank()) + '</td></tr>'
    out += ('<tr><th scope="row">Onboarding effect / rest advantage / illness</th><td>— unverified. Both playing on Day 2 does not establish equal rest hours. '
            'No travel, training, illness or roster-causality premium is added.</td><td>' + external('https://www.hltv.org/results?event=8932', 'HLTV schedule/results for review') + '</td></tr>')
    out += '</tbody></table></div></section>'
    out += '<section class="content-section prose" id="unresolved"><p class="eyebrow amber-text">Every gap stays visible</p><h2>Unresolved picks &amp; limitations</h2>'
    for row in report['day3_matches']:
        if not row['analysis'] or row['status'] != 'open':
            out += f'<p><strong>{e(" vs ".join(row["teams"]))}:</strong> {e(row["limitation"] or "No supported current pick.")}</p>'
    if not report['unresolved']:
        out += '<p>Both historical Day-3 deciders have a supported estimate in this snapshot. Supported is not the same as current: check lock and freshness above.</p>'
    for row in guide['matches']:
        if not row['analysis'] or not row['state']['current']:
            out += f'<p><strong>Day 4 {e(" vs ".join(row["teams"]))}:</strong> {e(row["limitation"] or row["state"]["detail"])}</p>'
    if report['global_unresolved'] is not None:
        out += f'<p><strong>{report["global_unresolved"]} unresolved across the complete CS2 list</strong> at this inventory observation. Low tier is not a reason to omit a fixture; missing or ambiguous evidence is a reason to leave its probability blank.</p>'
    out += '<ul>' + ''.join(f'<li>{e(x)}</li>' for x in report['limitations']) + '</ul>'
    out += (f'<p><a href="{prefix}origination/#unresolved">Every unresolved match &amp; source-by-source limitations →</a><br>'
            f'<a href="{prefix}review/">Flagged for Review, including withdrawn editorial claims →</a><br>'
            f'<a href="{prefix}data/twc-day3-picks.json">This generated TWC view (JSON) ↓</a><br>'
            f'<a href="{prefix}data/{e(report["research_report"])}">Dated research manifest, excerpts &amp; original-response hashes ↓</a></p></section>')
    return out


def observation_for(observations, teams, starts_at):
    """The dated observation for an exact team pair and start, or None.

    Display-only context: it is never merged into a canonical or collected pair.
    """
    key = (frozenset(name_key(t) for t in teams or []), starts_at)
    for entry in observations or []:
        if (frozenset(name_key(t) for t in entry.get('teams') or []), entry.get('starts_at')) == key:
            return entry
    return None


def activity_line(provider):
    """Provider-reported odds depth and book freshness, from the JSON only."""
    from scripts.build import e, local_time
    activity = provider.get('activity') or {}
    bits = []
    if activity.get('listed_at'):
        bits.append('listed ' + local_time(activity['listed_at']))
    if activity.get('opened_at'):
        bits.append('opened ' + local_time(activity['opened_at']))
    if activity.get('book_updated_at'):
        bits.append('book updated ' + local_time(activity['book_updated_at']))
    if activity.get('changed_since_open') is False:
        bits.append('no reprice since it opened')
    elif activity.get('changed_since_open') is True:
        bits.append('repriced since it opened')
    for key, label, money in [('last_price', 'last trade', False), ('open_interest', 'open interest', False),
                              ('volume', 'traded', False)]:
        values = activity.get(key)
        if isinstance(values, list) and len(values) == 2 and all(isinstance(v, (int, float)) for v in values):
            bits.append(label + ' ' + ' / '.join(f'{v:,.2f}' for v in values))
    if isinstance(activity.get('volume_usd'), (int, float)):
        bits.append(f'volume ${activity["volume_usd"]:,.0f}')
    if isinstance(activity.get('liquidity_usd'), (int, float)):
        bits.append(f'liquidity ${activity["liquidity_usd"]:,.0f}')
    return ('<br><small>' + e(provider.get('provider')) + ': ' + e(' · '.join(bits)) + '.</small>') if bits else ''


def movement_html(row):
    """Verified movement, a dated no-reprice statement, or the honest blank state."""
    from scripts.build import e, local_time
    movement = row.get('movement') or {}
    points = movement.get('points')
    teams = row.get('teams') or []
    if points and len(points) == len(teams):
        change = ', '.join(f'{e(n)} {p:+.1f} pts' for n, p in zip(teams, points))
        return ('<p class="twc-movement"><strong>Verified line movement:</strong> ' + e(change)
                + ' against the previous validated read (' + e(local_time(movement.get('from')))
                + '). ' + e(movement.get('label') or '') + '</p>')
    if movement.get('detail'):
        return '<p class="twc-movement"><strong>Line movement:</strong> ' + e(movement['detail']) + '</p>'
    if row.get('movement_note'):
        return '<p class="twc-movement"><strong>Line movement:</strong> ' + e(row['movement_note']) + '</p>'
    return ''


def pairing_note(teams, day3_results):
    """Which Day-3 decider settled this slot, from the retained result only.

    No winner is inferred from a start time; a note appears only when the
    retained Day-3 record names the team as the higher scorer.
    """
    from scripts.build import e, external
    from scripts.domain import name_key
    notes = []
    for team in teams or []:
        for row in day3_results or []:
            names, score = row.get('teams') or [], row.get('score') or []
            if len(names) != 2 or len(score) != 2 or score[0] == score[1]:
                continue
            winner, loser = (names[0], names[1]) if score[0] > score[1] else (names[1], names[0])
            if name_key(winner) != name_key(team):
                continue
            link = external(row['source_url'], 'HLTV record') if row.get('source_url') else ''
            notes.append(f'<p class="twc-pairing"><strong>Slot settled on Day 3:</strong> {e(winner)} advanced by winning '
                         f'{score[0]}&#8211;{score[1]} against {e(loser)}. {link}</p>')
    return ''.join(notes)


def render_day4(guide, prefix):
    """Mobile-readable canonical picks with the shared fail-closed time guards."""
    from scripts.build import e, local_time, external, blank
    from scripts.pick_safety import card_attributes, status_html
    out = ('<section class="content-section twc-section" id="day-four-picks"><div class="section-heading"><div>'
           '<p class="eyebrow">17 October 2026 · canonical feed</p><h2>Day 4 probabilities &amp; default picks</h2></div></div>'
           '<p class="section-intro">Every TWC fixture dated 17 October in the Hotspawn inventory is included. '
           'Percentages below are copied, not re-estimated, from the complete picks list. '
           'A missing HLTV match or missing book does not remove a Hotspawn fixture.</p><div class="twc-grid">')
    for row in guide['matches']:
        fixture, state, a = row['fixture'], row['state'], row['analysis']
        current = '' if state['current'] else ' hidden'
        historical = ' hidden' if state['current'] else ''
        out += (f'<article class="pick-card twc-card twc-day4-card" id="twc-day4-{e(fixture["id"])}" {card_attributes(fixture, state)}>'
                f'<p class="eyebrow">Day 4 · Hotspawn fixture {e(fixture["id"])}</p><h3>{e(" vs ".join(row["teams"]))}</h3>'
                f'<p>Start {local_time(fixture.get("starts_at"))}<br>Hotspawn lock {local_time(fixture.get("locks_at"))}</p>')
        for i, name in enumerate(row['teams']):
            value = f'{a["probabilities"][i] * 100:.1f}%' if a else '—'
            out += f'<div class="twc-prob"><span>{e(name)}</span><strong>{value}</strong></div>'
        if a and row['pick']:
            out += (f'<p class="pick-choice" data-current-only{current}><strong>Default pick: {e(row["pick"])}</strong></p>'
                    f'<p class="pick-choice" data-historical-only{historical}><strong>Snapshot only: {e(row["pick"])}</strong></p>')
        elif a:
            # A genuinely even external market is complete data, not missing
            # data. Say so explicitly and do not invent a side.
            even = abs(a['probabilities'][0] - a['probabilities'][1]) < 1e-9
            out += ('<p class="pick-choice"><strong>No edge — ' + ('even line' if even else 'no directional side') + '.</strong></p>'
                    '<p class="pick-caption">' + ('Both sides are priced at exactly 50% by the external line, so this is a real coin flip; '
                                                  'no side is invented and no default 50/50 is substituted for a missing number. '
                                                  'A directional pick would need an independent second source with a different price.'
                                                  if even else
                                                  'The stored estimate has no directional side. See the pricing audit for the exact inputs.') + '</p>')
        else:
            out += '<p><strong>Pick — unverified.</strong> ' + e(row['limitation']) + '</p>'
        out += status_html(state)
        if a:
            out += f'<p class="small">{e(a["label"])}<br>Observed {local_time(a["observed_at"])}</p>'
            urls = {a['source_url']: a.get('source') or 'Pricing source'}
            urls.update({q['source_url']: q.get('provider') or 'Pricing source' for q in a.get('quotes', []) if q.get('source_url')})
            out += '<div class="evidence-links">' + ''.join(external(u, n) for u, n in urls.items()) + '</div>'
        out += '<div class="evidence-links">' + external(fixture['source_url'], 'Official Hotspawn fixture')
        if row['hltv']:
            out += external(row['hltv']['source_url'], 'HLTV fixture')
        else:
            out += '<span class="small">HLTV cross-check — unverified</span>'
        out += f'<a href="{prefix}origination/#match-{e(fixture["id"])}">All source attempts &amp; full pricing audit →</a></div>'
        alt = row['alternative']
        if alt:
            out += (f'<aside class="twc-watch" data-current-only{current}><strong>Optional risk candidate: {e(alt["team"])}</strong>'
                    f'<p>{alt["probability"] * 100:.1f}% estimated win chance. Switching costs '
                    f'{alt["cost_per_base_point"]:.3f} expected points per 1 base point, before streak effects. '
                    'Editorial 30% screen, not evidence of mispricing. No automatic switch.</p></aside>')
        out += '</article>'
    out += '</div>'
    if not guide['matches']:
        out += ('<p class="section-intro"><strong>No Day-4 TWC fixture is confirmed in the weekly Hotspawn snapshot.</strong> '
                'No pair, lock, price or default is invented for that inventory. Any validated tournament-card line is '
                'shown in the separate external-market table below, and the complete CS2 list remains available.</p>')
    out += (f'<p class="section-intro"><a href="{prefix}origination/#picks">Every updated CS2 pick →</a> · '
            f'<a href="{prefix}origination/#unresolved">All unresolved picks &amp; limitations →</a> · '
            + (f'<a href="{prefix}data/{e(guide["research_report"])}">Day-3/4 source manifest ↓</a>' if guide.get('research_available') else 'Day-3/4 source evidence unavailable — unverified') + '</p></section>')
    if guide['not_in_hotspawn_snapshot']:
        out += ('<section class="content-section twc-section" id="day-four-tournament-lines">'
                '<div class="section-heading"><div><p class="eyebrow">17 October · external markets only</p>'
                '<h2>Tournament-card lines (not in the weekly Hotspawn lobby inventory)</h2></div></div>'
                '<p class="section-intro">These fixtures are listed by HLTV and by the Thunderpick tournament '
                'pick&#8217;em, so they carry no weekly inventory lock. Their win probabilities come from external '
                'first-party markets only: the public Polymarket CS2 directory and CS2-tag event API with both '
                'original order books, and Kalshi&#8217;s public CS2 match-winner series. Each fixture must join on '
                'exact team names (or a competition-scoped, evidence-linked alias) and an exact start time, and both '
                'sides must publish a two-sided book no wider than 0.12. No Hotspawn percentage, directory estimate '
                'or fan vote is used anywhere.</p>')
        out += '<div class="table-scroll"><table class="simple-table twc-day4-lines"><caption>HLTV-listed Day-4 fixtures absent from the weekly inventory — probabilities recomputed from retained market originals</caption><thead><tr><th>Match &amp; start</th><th>Probability &amp; pick</th><th>Evidence &amp; limitations</th></tr></thead><tbody>'
        for r in guide['not_in_hotspawn_snapshot']:
            line = r.get('line') or {}
            probs = line.get('probabilities')
            cells = ''
            if probs:
                names = r['facts']['teams']
                pick = line.get('pick_index')
                picks = []
                for i, name in enumerate(names):
                    marker = ' ✓ pick' if i == pick else ''
                    picks.append(f'<div class="twc-prob{" twc-favorite" if i == pick else ""}">'
                                 f'<span>{e(name)}</span><strong>{probs[i] * 100:.1f}%</strong></div>')
                # An exactly even external book carries pick_index None. Indexing
                # the team list with None would crash the build; naming a side
                # would invent one. Say it is a coin flip and keep both prices.
                even = abs(probs[0] - probs[1]) < 1e-9
                if pick is None:
                    cells = (''.join(picks) + '<p class="pick-choice"><strong>No edge — '
                             + ('even line' if even else 'no directional side') + '.</strong></p>'
                             '<small>' + ('Both sides are priced at exactly 50% by the external line, so this is a '
                                          'real coin flip; no side is invented and no default 50/50 is substituted '
                                          'for a missing number.' if even else
                                          'The retained estimate has no directional side. See the pricing audit '
                                          'for the exact inputs.') + '</small>')
                else:
                    cells = (''.join(picks) + f'<p class="pick-choice"><strong>Default pick: {e(names[pick])}</strong></p>')
                cells += (f'<small>{e(line.get("label"))}<br>Observed {local_time(line.get("observed_at"))}. '
                          'Midpoints, not executable quotes.</small>')
                cells += movement_html(line)
                for provider in line.get('providers') or []:
                    cells += (f'<br><small>{e(provider["provider"])}: bid/ask '
                              f'{provider["bid"][0]:.3f}/{provider["ask"][0]:.3f} vs '
                              f'{provider["bid"][1]:.3f}/{provider["ask"][1]:.3f}</small>')
                    cells += activity_line(provider)
                dog = r.get('line_underdog')
                if dog and pick is not None:
                    if dog['passes_floor']:
                        cells += (f'<aside class="twc-watch"><strong>Optional contrarian slot: {e(dog["team"])}</strong>'
                                  f'<p>{dog["probability"] * 100:.1f}% priced chance — at or above the published 30% '
                                  f'money-backed floor. Switching costs {dog["cost_per_base_point"]:.3f} expected points '
                                  'per 1 base point, before streak effects. A defensible risk choice, not a proven edge.</p></aside>')
                    else:
                        cells += (f'<aside class="twc-watch"><strong>No upset play offered: {e(dog["team"])}</strong>'
                                  f'<p>{dog["probability"] * 100:.1f}% priced chance — below the published 30% underdog '
                                  'floor, so fading this favourite is the avoidable kind of contrarian. Keep the default.</p></aside>')
            else:
                observed = observation_for(guide.get('observations'), r['facts']['teams'], r['facts']['starts_at'])
                if observed:
                    names = r['facts']['teams']
                    median = observed.get('median') or []
                    pick = names[0] if median and median[0] >= median[1] else (names[1] if median else None)
                    cells = ''
                    for i, name in enumerate(names):
                        if i >= len(median):
                            continue
                        marker = ' ✓ lean' if name == pick else ''
                        cells += f'<div class="twc-prob"><span>{e(name)}{marker}</span><strong>{median[i] * 100:.1f}%</strong></div>'
                    if pick:
                        cells += (f'<p class="pick-choice"><strong>Dated lean: {e(pick)}</strong></p>'
                                  '<small>Dated market observation from this session\'s own research capture, not the '
                                  'publisher\'s collected evidence. The four-hour pipeline re-collects the same public '
                                  'endpoints and supersedes it; no Hotspawn or fan-vote input.</small>')
                    cells += movement_html(observed)
                    for provider in observed.get('providers') or []:
                        pairs = list(zip(provider.get('bid') or [], provider.get('ask') or [],
                                         provider.get('outcomes') or []))
                        detail = ' · '.join(f'{e(o)} {b:.3f}/{a:.3f}' for b, a, o in pairs)
                        cells += (f'<br><small>{e(provider["provider"])}: {detail} — observed '
                                  f'{local_time(provider.get("observed_at"))}'
                                  + (f', book updated {local_time(provider["book_updated_at"])}'
                                     if provider.get('book_updated_at') else '') + '</small>')
                        cells += activity_line(provider)
                    dog = observed.get('underdog') or {}
                    if dog:
                        if dog.get('passes_floor'):
                            cells += (f'<aside class="twc-watch"><strong>Optional contrarian slot: {e(dog["team"])}</strong>'
                                      f'<p>{dog["probability"] * 100:.1f}% observed chance — above the published 30% '
                                      f'floor. Switching costs {dog["cost_per_base_point"]:.3f} expected points per 1 '
                                      f'base point. {e(dog.get("reading") or "")}</p></aside>')
                        else:
                            cells += (f'<aside class="twc-watch"><strong>No upset play offered: {e(dog["team"])}</strong>'
                                      f'<p>{dog["probability"] * 100:.1f}% observed chance — below the published 30% '
                                      f'floor. {e(dog.get("reading") or "")}</p></aside>')
                else:
                    attempts = ''.join(f'<li>{e(a["provider"])}: {e(a["reason"])}</li>' for a in (line.get('attempts') or []))
                    unresolved = [n for n in r['facts']['teams'] if '/' in n and 'winner' in n.lower()]
                    reason = (f'HLTV still lists this semi-final slot as a bracket placeholder ({", ".join(unresolved)}). A market '
                              'cannot be joined to an unresolved slot, so no price or pick is invented for it.' if unresolved else
                              'No validated two-sided external line at this observation. No price or pick is invented; a source '
                              'failure is not evidence that no market exists.')
                    cells = blank() + '<small>' + e(reason) + '</small>' + (f'<ul class="small">{attempts}</ul>' if attempts else '')
            links = ''.join(external(p['source_url'], p['provider']) for p in (line.get('providers') or [])
                            if p.get('source_url'))
            links += external(r['source_url'], 'HLTV fixture')
            if guide['lines'].get('report_path'):
                links += f'<a href="{prefix}data/{e(guide["lines"]["report_path"])}">Retained market originals ↓</a>'
            out += (f'<tr><th scope="row">{e(" vs ".join(r["facts"]["teams"]))}'
                    f'<small>{local_time(r["facts"]["starts_at"])} · HLTV start</small>'
                    + pairing_note(r['facts']['teams'], guide.get('day3_results'))
                    + '</th>'
                    f'<td>{cells}</td><td>{links}<small>Read {local_time(r["observed_at"])}</small></td></tr>')
        out += '</tbody></table></div>'
        if guide['lines'].get('available'):
            out += (f'<p class="small">External lines observed {local_time(guide["lines"]["observed_at"])}: '
                    f'{guide["lines"]["resolved"]} of {guide["lines"]["total"]} Day-4 fixtures validated. '
                    'They refresh with the same four-hour publisher and are recomputed from the retained originals, '
                    'so a stale, wide or one-sided book publishes nothing.</p>')
        else:
            out += ('<p class="small">No retained external-market evidence for the Day-4 tournament card yet. '
                    'Probabilities stay blank until a validated book is collected.</p>')
    if guide['not_in_hotspawn_snapshot']:
        out += (f'<p class="section-intro">External lines refresh with the same four-hour publisher as the complete '
                f'list. <a href="{prefix}data/{e(guide["research_report"])}">Day-3/4 source manifest ↓</a> · '
                f'<a href="{prefix}origination/#picks">Every updated CS2 pick →</a></p></section>')
    out += '<section class="content-section" id="day-three-results"><div class="section-heading"><div><p class="eyebrow">16 October · source-checked, not inferred</p><h2>Day 3 results: evidence for Day 4</h2></div></div>'
    if guide['day3_results']:
        out += results_table(guide['day3_results'], prefix)
    else:
        out += '<p class="section-intro">Day-3 results — unverified in retained research. No winner is inferred from the start time, market price or earlier fixture.</p>'
    out += ('<p class="section-intro"><strong>How to use Days 1–3:</strong> compare actual played maps and the next opponent’s listed lineup, '
            'not just a win/loss streak. A close map or an upset can justify investigating an underdog; it cannot establish a probability adjustment. '
            'Prefer the externally priced favorite for expected base points. Only consider an optional underdog with a fresh money line, '
            'confirmed deadline and a specific matchup case. A roster rebuild, travel or rest advantage needs independent evidence; none is quantified here. '
            'Ownership, streak state and the points needed to catch the leaders are unknown, so a leaderboard-gain claim would be invented.</p></section>')
    return out
