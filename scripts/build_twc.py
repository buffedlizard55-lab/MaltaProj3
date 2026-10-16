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
    data['_twc_report'] = report
    out = heading('Thunderpick World Championship 2026 · 17 October', 'TWC Day 4: picks & review',
                  'One probability feed. Days 1–3 evidence. Every listed Day-4 match, without invented odds.')
    out += (f'<section class="twc-brief" id="twc-summary"><p class="eyebrow">Executive summary</p>'
            '<h2>Keep the default. Make any upset play deliberate.</h2>'
            '<p>The default is the higher-probability side in the complete picks list below. '
            'For leaderboard catch-up, consider at most one optional underdog, only with a fresh money-backed line '
            'and a specific matchup case. A plausible upset is not evidence that a market is wrong.</p>'
            f'<nav class="briefing-links" aria-label="TWC sections"><a href="#day-four-picks">Day 4 picks</a><a href="#day-three-results">Day 3 results</a><a href="#day-three-picks">Day 3 snapshot</a>'
            '<a href="#day-one-results">Day 1 results</a><a href="#day-two-results">Day 2 results</a>'
            '<a href="#roster-check">Roster &amp; rest check</a><a href="#unresolved">Unresolved &amp; limitations</a>'
            f'<a href="{prefix}origination/#picks">Every Hotspawn CS2 pick →</a></nav>'
            f'<p class="small">Inventory {local_time(report["source_snapshot_at"])} · pricing snapshot '
            f'{local_time(report["source_generated_at"])}. Times use the page timezone selector. '
            'All probabilities below regenerate with the same four-hour publisher as the full list.</p></section>')
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
        else:
            out += '<p><strong>Pick — unverified.</strong> ' + ('Equal estimate; no arbitrary direction.' if a else e(row['limitation'])) + '</p>'
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
        out += '<p class="section-intro"><strong>No Day-4 TWC fixture is confirmed in this Hotspawn snapshot.</strong> No pair, lock, price or default is invented. The complete CS2 list remains available below.</p>'
    if guide['not_in_hotspawn_snapshot']:
        out += '<div class="table-scroll"><table class="simple-table"><caption>HLTV-listed Day-4 fixtures not uniquely matched to the Hotspawn weekly inventory — not playable picks here</caption><thead><tr><th>Match</th><th>HLTV start</th><th>Hotspawn probability / pick</th><th>Source</th></tr></thead><tbody>'
        for r in guide['not_in_hotspawn_snapshot']:
            out += f'<tr><th scope="row">{e(" vs ".join(r["facts"]["teams"]))}</th><td>{local_time(r["facts"]["starts_at"])}</td><td>{blank()}<small>No unique exact pair/time join to the weekly inventory; placeholder opponents are not confirmed. No price or lock inferred. Separate tournament picks may differ.</small></td><td>{external(r["source_url"], "HLTV fixture")}<small>Read {local_time(r["observed_at"])}</small></td></tr>'
        out += '</tbody></table></div>'
    out += (f'<p class="section-intro"><a href="{prefix}origination/#picks">Every updated CS2 pick →</a> · '
            f'<a href="{prefix}origination/#unresolved">All unresolved picks &amp; limitations →</a> · '
            + (f'<a href="{prefix}data/{e(guide["research_report"])}">Day-3/4 source manifest ↓</a>' if guide.get('research_available') else 'Day-3/4 source evidence unavailable — unverified') + '</p></section>')
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
