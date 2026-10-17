"""Final-day presentation of replayed sources, never a new probability model.

Weekly Hotspawn fixtures retain canonical probabilities. Independently listed
HLTV fixtures may display replayed external lines but never acquire an invented
Hotspawn entry, lock, result, roster premium or score prediction.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from scripts import twc_research, twc_lines
from scripts.domain import iso, name_key
from scripts.pick_safety import presentation

DAY = '2026-10-18'
MONEY = {'market', 'bookmaker', 'consensus'}


def derive(data, source: Path, now=None):
    now = now or datetime.now(timezone.utc)
    guide = twc_research.derive_day4(data, source, now, target_day=DAY,
                                   line_report=twc_lines.DAY5_REPORT)
    research = twc_research.load(source)
    history = []
    for record in research['pages']:
        facts = record['facts']
        start = str(facts.get('starts_at') or '')
        if start[:10] not in {'2026-10-14', '2026-10-15', '2026-10-16', '2026-10-17'}:
            continue
        history.append({'teams': facts['teams'], 'starts_at': facts['starts_at'],
                        'score': facts.get('score') if facts.get('finished') else None,
                        'finished': facts.get('finished', False), 'maps': facts.get('maps') or [],
                        'lineups': facts.get('lineups') or [],
                        'source_url': record['source_url'], 'observed_at': record['observed_at'],
                        'lesson': 'Completed series are context, not an independent win probability or a causal roster/rest effect.'
                                  if facts.get('finished') and facts.get('score') else
                                  'Result unverified. Neither the scheduled start nor the bracket establishes a winner.'})
    cards = []
    for row in guide['matches']:
        # Never replace a canonical estimate. Only a canonical blank may display
        # a separately replayed tournament line, still bound to the official lock.
        line = row['analysis'] or row.get('line')
        fixture = dict(row['fixture'], origination=line)
        state = presentation(fixture, data.get('inventory_observed_at'), data.get('coverage_complete'), now)
        cards.append(_card(fixture, row.get('hltv'), line, state, 'weekly', history))
    for record in guide['not_in_hotspawn_snapshot']:
        facts = record['facts']
        fixture = {'id': 'hltv-' + record['source_url'].split('/')[4],
                   'teams': [{'name': n} for n in facts['teams']], 'starts_at': facts['starts_at'],
                   'locks_at': None, 'availability': 'unknown', 'source_url': record['source_url'],
                   'origination': record.get('line')}
        state = presentation(fixture, data.get('inventory_observed_at'), data.get('coverage_complete'), now)
        cards.append(_card(fixture, record, record.get('line'), state, 'hltv-only', history))
    represented = {r['source_url'].split('/')[4] for r in research['pages']
                   if str(r['facts'].get('starts_at') or '').startswith(DAY)}
    missing = []
    # Labels come from retained source URL text, not an inferred finalist or time.
    for url in sorted(twc_research.retained_discovery_urls(source)):
        match_id = url.split('/')[4]
        if match_id not in {'2399416', '2399417'} or match_id in represented:
            continue
        missing.append({'source_url': url, 'slot': 'Grand final' if match_id == '2399417' else 'Third-place decider',
                        'reason': 'No usable source-replayed final-day fixture in this observation. Teams, UTC start, format, probabilities and pick remain unverified; no semifinal winner is inferred.'})
    return {'schema_version': 1, 'event_day': DAY, 'evaluated_at': iso(now),
            'source_snapshot_at': data.get('inventory_observed_at'),
            'source_generated_at': (data.get('complete_picks') or {}).get('generated_at'),
            'cards': cards, 'missing_slots': missing, 'day4_results': [r for r in history if r['starts_at'].startswith('2026-10-17')],
            'unresolved_ids': [r['fixture']['id'] for r in cards if not (r.get('analysis') or {}).get('probabilities')],
            'lines_report': guide['lines'].get('report_path'), 'research_report': guide['research_report'],
            'counts': {'listed': len(cards), 'supported_estimates': sum(bool((c.get('analysis') or {}).get('probabilities')) for c in cards),
                       'current_picks': sum(c['state']['current'] and c['pick_index'] is not None for c in cards),
                       'unresolved': sum(not (c.get('analysis') or {}).get('probabilities') for c in cards),
                       'unverified_slots': len(missing)},
            'policy': 'Exact canonical estimates or separately replayed external tournament lines; no Hotspawn percentages, inferred bracket, score pick, rest or roster adjustment.'}


def _card(fixture, record, line, state, scope, history):
    names = [t['name'] for t in fixture['teams']]
    p = (line or {}).get('probabilities')
    pick = None if not p or abs(p[0] - p[1]) < 1e-8 else (0 if p[0] > p[1] else 1)
    dog = None
    if pick is not None and line.get('method') in MONEY:
        other = 1 - pick
        if 0.30 <= p[other] < 0.50:
            dog = {'team': names[other], 'probability': p[other],
                   'cost_per_base_point': round(p[pick] - p[other], 8)}
    context = [h for h in history if h['finished'] and h['score'] and
               {name_key(n) for n in h['teams']} & {name_key(n) for n in names}]
    return {'fixture': fixture, 'teams': names, 'scope': scope, 'analysis': line if p else None,
            'attempts': (line or {}).get('attempts') or [], 'state': state, 'pick_index': pick,
            'pick': names[pick] if pick is not None else None, 'underdog_screen': dog,
            'hltv': record, 'context': context}


def summary(guide, prefix):
    c = guide['counts']
    return (f'<section class="limitations-callout" id="final-day-summary" aria-label="TWC final-day coverage">'
            '<strong>Day 5 · 18 October: final-day picks</strong>'
            f'<p>{c["listed"]} source-listed fixtures · {c["supported_estimates"]} supported estimates · '
            f'{c["current_picks"]} confirmed current weekly picks · {c["unresolved"]} unresolved lines · '
            f'{c["unverified_slots"]} unverified bracket slots. Tournament research is separate from weekly lobby coverage; '
            'a line does not confirm a Hotspawn entry or lock.</p>'
            f'<p><a href="{prefix}twc-picks/#day-five-picks">Day 5 probabilities &amp; picks →</a> · '
            f'<a href="{prefix}twc-picks/#day-four-results">Day 4 results →</a> · '
            f'<a href="{prefix}twc-picks/#day-five-unresolved">Final-day unresolved picks &amp; limitations →</a></p></section>')


def render(guide, prefix):
    from scripts.build import e, external, local_time, blank
    from scripts.build_twc import results_table
    from scripts.pick_safety import card_attributes, status_html
    out = ('<section class="content-section twc-section" id="day-five-picks">'
           '<div class="section-heading"><div><p class="eyebrow">18 October 2026 · final day</p>'
           '<h2>Day 5 probabilities &amp; picks</h2></div></div>'
           '<p>Higher-probability team by default. Keep an underdog to at most one deliberate catch-up choice, '
           'only after checking a fresh money-backed line and confirmed entry deadline. The 30% screen is editorial, '
           'not a calibrated edge. We do not know opponents’ selections or your leaderboard deficit, so we cannot '
           'claim that any choice maximizes your chance of winning the leaderboard.</p>'
           '<p>Blank means unverified, not 50/50. A supported equal line has no directional pick. '
           'No exact-score recommendation is derived from match-winner odds, especially for a different best-of format.</p>'
           '<noscript><style>#day-five-picks [data-current-only]{display:none!important} '
           '#day-five-picks [data-historical-only]{display:block!important}</style><p>JavaScript is off. '
           'These are dated snapshot estimates only; live lock and freshness retirement is unavailable. '
           'Check the original source and Hotspawn deadline before choosing.</p></noscript>'
           '<div class="twc-grid">')
    for row in guide['cards']:
        fixture, a, state = row['fixture'], row['analysis'], row['state']
        p = a['probabilities'] if a else None
        current = '' if state['current'] else ' hidden'
        historic = ' hidden' if state['current'] else ''
        out += (f'<article class="twc-day5-card twc-card-base" id="twc-day5-{e(fixture["id"])}" '
                f'{card_attributes(fixture, state)}><h3>{e(" vs ".join(row["teams"]))}</h3>'
                f'<p>{local_time(fixture["starts_at"])} · '
                + ('Weekly Hotspawn fixture' if row['scope'] == 'weekly' else 'HLTV-listed · Hotspawn entry &amp; lock unverified') + '</p>')
        facts = (row.get('hltv') or {}).get('facts') or {}
        out += f'<p>Best of {e(facts["best_of"])}</p>' if facts.get('best_of') else '<p>Best-of format: — unverified</p>'
        for i, name in enumerate(row['teams']):
            value = f'{p[i]*100:.1f}%' if p else '—'
            out += f'<div class="twc-prob"><span>{e(name)}</span><strong>{value}</strong></div>'
        direction = e(row['pick']) if row['pick'] else ('No edge — even line' if p else '— unverified')
        out += (f'<p data-current-only{current}><strong>Default pick: {direction}</strong></p>'
                f'<p data-historical-only{historic}><strong>Snapshot lean: {direction}</strong><br>'
                'Not a confirmed current pick. Check the source time and entry deadline.</p>' + status_html(state))
        if a:
            out += f'<p class="small">{e(a.get("label") or a.get("method"))} · observed {local_time(a.get("observed_at"))}. Estimates, not guarantees.</p>'
        dog = row['underdog_screen']
        if dog:
            out += (f'<aside class="twc-watch" data-current-only{current}><strong>Optional underdog screen: {e(dog["team"])}</strong>'
                    f'<p>{dog["probability"]*100:.1f}% priced chance. Switching sacrifices {dog["cost_per_base_point"]:.3f} '
                    'expected points per 1 base point, before streak effects. This passes the probability floor only; '
                    'the results below are context, not proof of mispricing.</p></aside>')
        out += '<div class="evidence-links">' + external(fixture['source_url'], 'Hotspawn fixture' if row['scope'] == 'weekly' else 'HLTV-reported fixture')
        if row.get('hltv'):
            out += external(row['hltv']['source_url'], 'HLTV match record')
        for provider in (a or {}).get('providers') or []:
            if provider.get('source_url'):
                out += external(provider['source_url'], provider.get('provider') or 'External line')
        if a and a.get('source_url'):
            out += external(a['source_url'], a.get('provider') or 'Pricing source')
        if row['scope'] == 'weekly':
            out += f'<a href="{prefix}origination/#match-{e(fixture["id"])}">Canonical pick &amp; research →</a>'
        out += '</div>'
        if row['context']:
            out += '<details><summary>Days 1–4 matchup context · no probability adjustment</summary><ul>'
            for r in row['context']:
                out += (f'<li>{local_time(r["starts_at"])} · {e(" vs ".join(r["teams"]))} '
                        f'{e("–".join(map(str,r["score"])))} · {external(r["source_url"], "HLTV result")}</li>')
            out += '</ul><p>Scheduled starts do not establish actual finishing times, sleep or recovery. '
            out += 'Roster continuity does not prove onboarding is complete. Neither is assigned an arbitrary percentage.</p></details>'
        out += '</article>'
    out += '</div>'
    if not guide['cards']:
        out += '<p>No usable source-replayed Day-5 fixture yet. No finalist, probability or pick is inferred. Known unresolved slots are listed below.</p>'
    out += '</section><section class="content-section" id="day-four-results"><h2>Day 4 results: what changes for the final day?</h2>'
    if guide['day4_results']:
        out += results_table(guide['day4_results'], prefix)
    else:
        out += '<p>Day-4 result values are unverified in this snapshot. Do not extrapolate winners from the bracket or old prices.</p>'
    out += ('<p>The Day-1 9z upset is a reason to consider plausible underdogs, not to fade Aurora automatically. '
            'Read the linked Day-2 recovery and Day-3 rematch alongside Day-4 results. Recent roster changes widen uncertainty; '
            'they are not a quantified disadvantage or a verified cause of an upset. We do not double-count public results '
            'by adding a narrative premium to an already updated market price. A losing favorite or winning long shot '
            'does not, by itself, prove a prematch probability was wrong; do not rewrite the underdog screen after seeing the result.</p>'
            '<p>The Aurora rebuild report is dated <strong>8 July 2026</strong>, not tournament week: '
            + external('https://www.hltv.org/news/45082/official-aurora-complete-rebuild-with-kyxsan', 'HLTV transfer report (secondary)') +
            '. It supports summer roster context, not an assumed last-minute onboarding disadvantage.</p>'
            '<p><a href="#day-one-results">Day 1 review</a> · <a href="#day-two-results">Day 2 review</a> · '
            '<a href="#day-three-results">Day 3 results</a> · <a href="#roster-check">Roster &amp; rest evidence</a></p></section>')
    out += '<section class="content-section" id="day-five-unresolved"><h2>Final-day unresolved picks &amp; limitations</h2>'
    out += '<div class="table-scroll"><table class="simple-table"><caption>Missing inputs stay blank; each limitation links its original fixture source</caption><thead><tr><th>Fixture / slot</th><th>Limitation &amp; source</th></tr></thead><tbody>'
    limitations = []
    for row in guide['cards']:
        if row['state']['current'] and row['analysis']:
            continue
        reason = row['state']['detail']
        if row['scope'] == 'hltv-only':
            reason += ' This HLTV fixture has not been matched to the weekly Hotspawn inventory; a tournament entry deadline is unverified.'
        attempts = ' '.join(f'{x.get("provider")}: {x.get("reason")}' for x in row['attempts'])
        limitations.append((' vs '.join(row['teams']), reason + ' ' + attempts, row['fixture']['source_url']))
    limitations.extend((r['slot'], r['reason'], r['source_url']) for r in guide['missing_slots'])
    for name, reason, url in limitations:
        out += f'<tr><th scope="row">{e(name)}</th><td>{e(reason)} {external(url, "Original source")}</td></tr>'
    out += '</tbody></table></div>'
    if not limitations:
        out += '<p>No fixture-specific missing input was found in this snapshot; the scope and model limitations still apply.</p>'
    out += ('<p>HLTV is an independent reporter, not organizer confirmation. All historical scores remain labelled HLTV-reported. '
            'External lines require an exact fixture and two valid sides; source outages, ambiguous names and missing books '
            'never produce a default probability. Roster onboarding, vetoes, health, travel, exact rest and leaderboard ownership '
            'are not verified probability inputs.</p>'
            f'<p><a href="{prefix}origination/#unresolved">Every unresolved CS2 match →</a> · '
            f'<a href="{prefix}review/">Flagged for Review →</a> · '
            f'<a href="{prefix}data/twc-day5-picks.json">Day-5 data ↓</a> · '
            f'<a href="{prefix}data/{e(guide["research_report"])}">Source originals manifest ↓</a>')
    if guide.get('lines_report'):
        out += f' · <a href="{prefix}data/{e(guide["lines_report"])}">External line originals ↓</a>'
    return out + '</p></section>'
