"""Render the dated 'Upset review & contrarian edge' page from data/edge-review.json.

This page is deliberately separate from the automated picks pipeline:

* it publishes a *dated* first-party research review (day-one results, roster
  changes, market observations) where every displayed value carries its own
  official source link and observation time,
* it never overwrites a featured or researched estimate produced by
  ``scripts.collect`` / ``scripts.originate``,
* anything that could not be confirmed from an official source renders as
  '— unverified' instead of being inferred,
* Hotspawn community percentages are never read, so no crowd-fade advice is
  produced; 'contrarian' here means disagreeing with the external market or
  ranking consensus only when verified evidence supports it.

Usage: python -m scripts.build_edge [--source data] [--output site]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.build import PAGES, badge, blank, e, external, heading, icon, local_time
from scripts.domain import timestamp
from scripts.validate import require

EDGE_SCHEMA = 1
REQUIRED_KEYS = ['schema_version', 'title', 'prepared_at', 'research_window', 'policy',
                 'event', 'headline', 'day_one', 'roster_watch', 'edge_rules', 'day_two', 'limitations']


def load_edge(path: Path) -> dict:
    data = json.loads(path.read_text())
    for key in REQUIRED_KEYS:
        require(key in data, f'edge-review.json is missing {key!r}')
    require(data['schema_version'] == EDGE_SCHEMA, 'Unsupported edge-review schema')
    for key in ['prepared_at', 'research_window']:
        pass
    require(timestamp(data['prepared_at']) is not None, 'edge-review.json needs a prepared_at timestamp')
    window = data['research_window']
    require(timestamp(window.get('from')) is not None and timestamp(window.get('to')) is not None,
            'edge-review.json needs a research window with both ends')
    for group in ['day_one', 'day_two', 'roster_watch', 'edge_rules']:
        require(isinstance(data[group], list), f'edge-review.json {group} must be a list')
    for key in ('day_three', 'day_three_results', 'day_four'):
        if key not in data:
            continue
        require(isinstance(data[key], list), f'edge-review.json {key} must be a list')
        for row in data[key]:
            require(row.get('sources'), 'every reviewed match needs at least one official source link')
            for src in row['sources']:
                require(str(src.get('url', '')).startswith('https://'), 'edge-review sources must be https links')
                require(src.get('observed_at'), 'edge-review sources must carry an observation time')
            market = row.get('market')
            if market is not None:
                require(market.get('observed_at'), 'market observations must carry an observation time')
                for field in ('event_url', 'api_url'):
                    if market.get(field):
                        require(str(market[field]).startswith('https://'), 'market links must be https links')
    for row in data.get('group_stage_record', {}).get('series', []):
        require(row.get('sources'), 'every group-stage series needs an official source link')
        require(str(row.get('url', '')).startswith('https://www.hltv.org/matches/'),
                'every group-stage series must link its own HLTV match page')
    for block in (data.get('day_four_refresh', {}).get('fixtures', []),):
        for row in block:
            require(row.get('sources'), 'every dated semifinal observation needs an official source link')
            market = row.get('market') or {}
            if market:
                require(market.get('observed_at'), 'a dated market observation needs an observation time')
                require(str(market.get('api_url', '')).startswith('https://'), 'a market observation needs its provider record link')
    five = data.get('day_five_card') or {}
    bracket = five.get('bracket_status')
    require(bracket in ('open', 'resolved'), 'day_five_card needs an explicit bracket_status')
    for row in five.get('matches', []):
        if bracket == 'open':
            # Fail closed: an unplayed match cannot carry a team, a probability or a pick.
            require(row.get('teams') in (None, []), 'day-five teams must stay blank while the bracket is open')
            require(row.get('probabilities') is None and row.get('pick') is None,
                    'day-five fixtures must not carry a probability or a pick before their semifinal finishes')
            continue
        # Resolved: every published value needs its own official source, and a
        # price without a dated first-party market record stays blank. The
        # labelled Valve-model fallback is never written into `probabilities`.
        teams = row.get('teams')
        require(isinstance(teams, list) and len(teams) == 2 and all(isinstance(t, str) and t.strip() for t in teams)
                and len({str(t).strip().lower() for t in teams}) == 2,
                'a resolved day-five row needs exactly two distinct team names')
        require(timestamp(row.get('starts_at')) is not None, 'a resolved day-five row needs a verified start time')
        require(row.get('best_of') in (3, 5), 'a resolved day-five row needs its published best-of format')
        require(str(row.get('url', '')).startswith('https://www.hltv.org/matches/'),
                'a resolved day-five row must link its own HLTV match page')
        sources = row.get('sources') or []
        require(sources, 'a resolved day-five row needs at least one official source link')
        for src_ in sources:
            require(str(src_.get('url', '')).startswith('https://'), 'edge-review sources must be https links')
            require(src_.get('observed_at'), 'edge-review sources must carry an observation time')
        market = row.get('market')
        if market is not None:
            require(market.get('observed_at'), 'market observations must carry an observation time')
            require(str(market.get('api_url', '' )).startswith('https://'), 'a market observation needs its provider record link')
        probs = row.get('probabilities')
        if probs is not None:
            require(market is not None, 'day-five probabilities require their own dated provider record')
            require(isinstance(probs, list) and len(probs) == 2
                    and all(isinstance(x, (int, float)) and 0 < x < 1 for x in probs)
                    and abs(sum(probs) - 1) < 0.02, 'day-five probabilities must be a normalised pair')
        model = row.get('model_estimate')
        if model is not None:
            require(model.get('method') == 'model', 'day-five model estimates must say method= model')
            require(str(model.get('source_url', '')).startswith('https://'), 'model estimates need their official source link')
            require(str(model.get('formula_source', '')).startswith('https://'), 'model estimates need the published formula link')
            require(model.get('snapshot_date'), 'model estimates need their rating snapshot date')
            pair = model.get('probabilities')
            require(isinstance(pair, list) and len(pair) == 2
                    and all(isinstance(x, (int, float)) and 0 < x < 1 for x in pair)
                    and abs(sum(pair) - 1) < 0.02, 'day-five model estimates must be a normalised pair')
        pick = row.get('pick')
        if pick is not None:
            require(pick in teams, 'day-five pick must be one of the two verified teams')
            require(row.get('pick_basis'), 'day-five pick needs its stated basis')
            require(model is not None or probs is not None, 'day-five pick needs an estimate to stand on')
        score = row.get('score')
        if score is not None:
            require(score.get('suggested') and score.get('basis'), 'a day-five score slip needs its suggestion and basis')
            require(str(score.get('source_url', '')).startswith('https://'), 'a day-five score slip needs its source link')
        watch = row.get('contrarian_watch')
        if watch is not None:
            require(watch.get('team') in teams, 'a contrarian watch must name one of the two verified teams')
            require(watch.get('case') and watch.get('screen'), 'a contrarian watch needs its case and its screen')
    if 'day_five_guidance' in data:
        guide = data['day_five_guidance']
        require(isinstance(guide.get('principles'), list) and guide['principles'],
                'day_five_guidance.principles must be a non-empty list')
        require(guide.get('sources'), 'day_five_guidance needs its evidence links')
        for src_ in guide['sources']:
            require(str(src_.get('url', '')).startswith('https://'), 'edge-review sources must be https links')
            require(src_.get('observed_at'), 'edge-review sources must carry an observation time')
    for group in ('semifinal_results',):
        for row in five.get(group) or []:
            require(row.get('sources'), 'every day-five recap row needs an official source link')
            for src_ in row['sources']:
                require(str(src_.get('url', '')).startswith('https://'), 'edge-review sources must be https links')
                require(src_.get('observed_at'), 'edge-review sources must carry an observation time')
    if 'day_four_guidance' in data:
        block = data['day_four_guidance']
        require(isinstance(block.get('principles'), list) and block['principles'],
                'day_four_guidance.principles must be a non-empty list')
        require(block.get('sources'), 'day_four_guidance needs its evidence links')
        for src in block['sources']:
            require(str(src.get('url', '')).startswith('https://'), 'edge-review sources must be https links')
            require(src.get('observed_at'), 'edge-review sources must carry an observation time')
    for row in data['day_one'] + data['day_two']:
        require(row.get('sources'), 'every reviewed match needs at least one official source link')
        for src in row['sources']:
            require(str(src.get('url', '')).startswith('https://'), 'edge-review sources must be https links')
            require(src.get('observed_at'), 'edge-review sources must carry an observation time')
    for rule in data['edge_rules']:
        require(rule.get('id') and rule.get('title') and rule.get('body'), 'every edge rule needs id, title and body')
        require(rule.get('sources'), 'every edge rule needs its evidence links')
    return data


def source_list(sources, prefix=''):
    out = '<div class="evidence-links">'
    for src in sources:
        label = src.get('source') or 'Source'
        observed = src.get('observed_at')
        stamp = f' <small>observed {e(observed)}</small>' if observed else ''
        out += external(src['url'], label) if not stamp else external(src['url'], label)
    out += '</div>'
    return out


def source_lines(sources):
    out = '<ul class="limitations">'
    for src in sources:
        detail = src.get('detail') or ''
        out += f'<li>{e(detail)} {external(src["url"], src.get("source") or "Source")}'
        if src.get('observed_at'):
            out += f' <span class="tiny muted">observed {local_time(src["observed_at"])}</span>'
        out += '</li>'
    return out + '</ul>'


def maps_text(row):
    maps = row.get('maps') or []
    if not maps:
        return blank()
    return e(' · '.join(f'{m["map"]} {m["a"]}-{m["b"]}' for m in maps))


def day_one_section(data):
    out = ['<section class="content-section" id="day-one"><div class="section-heading"><div>'
           '<p class="eyebrow">Official results, not recollections</p><h2>Day one: every series, every map</h2></div>'
           + badge('HLTV verified', 'green') + '</div>',
           '<p class="section-intro">Four series, four 2-0 scorelines — with one reported upset. Historical rankings are context, not price calibration. '
           'Map scores, standout ratings and lineups below are HLTV’s published values for these specific series.</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-one results at Thunderpick '
           'World Championship 2026 with official source links</caption><thead><tr><th scope="col">Series</th>'
           '<th scope="col">Score &amp; maps</th><th scope="col">What the result actually said</th></tr></thead><tbody>']
    for row in data['day_one']:
        flag = badge('Upset', 'amber') if row.get('upset') else badge('Favorite won', 'neutral')
        lineup = ''
        for key, label in [('verified_lineup_a', row['team_a']), ('verified_lineup_b', row['team_b'])]:
            values = row.get(key)
            lineup += f'<p class="tiny"><strong>{e(label)}</strong>: ' + (e(', '.join(values)) if values else '— <small>unverified</small>') + '</p>'
        standout = f'<p class="tiny"><strong>Standout</strong>: {e(row["standout"])}</p>' if row.get('standout') else ''
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} {e(row["score"])} {e(row["team_b"])}</strong>'
                   f'<small>{e(row["date"])} · {e(row["group"])} · {e(row.get("best_of") or "bo unverified")} {flag}</small></th>'
                   f'<td>{maps_text(row)}<small>Series {e(row["score"])}</small></td>'
                   f'<td><p>{e(row["read"])}</p>{lineup}{standout}{source_lines(row["sources"])}'
                   f'{external(row["url"], "HLTV match page")}</td></tr>')
    out.append('</tbody></table></div></section>')
    return ''.join(out)


def roster_section(data):
    out = ['<section class="content-section" id="rosters"><div class="section-heading"><div>'
           '<p class="eyebrow">Roster changes, onboarding and rest</p><h2>Who changed, and what remains unverified</h2></div>'
           + badge('Official transfer news', 'green') + '</div>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Verified roster changes and '
           'lineup continuity for the reviewed teams</caption><thead><tr><th scope="col">Team</th>'
           '<th scope="col">Verified lineup &amp; ranking</th><th scope="col">Change and what it means</th>'
           '</tr></thead><tbody>']
    for row in data['roster_watch']:
        lineup = e(', '.join(row['current_lineup'])) if row.get('current_lineup') else '— <small>unverified</small>'
        coach = e(row['coach']) if row.get('coach') else '— <small>unverified</small>'
        ranks = e(row['rankings']) if row.get('rankings') else '— <small>unverified</small>'
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team"])}</strong><small>{badge(row["status"], "amber" if "not verified" in row["status"] or "Rebuilt" in row["status"] else "green")}</small></th>'
                   f'<td><p><strong>Lineup</strong>: {lineup}</p><p class="tiny"><strong>Coach</strong>: {coach}</p>'
                   f'<p class="tiny"><strong>Rankings</strong>: {ranks}</p>'
                   f'{external(row["url"], "HLTV team page")}</td>'
                   f'<td><p>{e(row["change"])}</p><p class="tiny"><strong>So what:</strong> {e(row["so_what"])}</p>'
                   + valve_snapshot_note(row.get('valve_snapshot')) +
                   f'{source_lines(row["sources"])}</td></tr>')
    out.append('</tbody></table></div></section>')
    return ''.join(out)


def rules_section(data):
    out = ['<section class="content-section resolution-steps" id="rules"><div class="section-heading"><div>'
           '<p class="eyebrow">Contrarian, but not stupid</p><h2>The seven rules this review applies</h2></div>'
           + badge('Evidence required', 'neutral') + '</div>']
    for rule in data['edge_rules']:
        out.append(f'<article class="resolution-step"><span>{e(rule["id"])}</span><div><h2>{e(rule["title"])}</h2>'
                   f'<p>{e(rule["body"])}</p>')
        if rule.get('sources'):
            out.append('<div class="evidence-links">' + ''.join(external(s['url'], s.get('source') or 'Source') for s in rule['sources']) + '</div>')
        out.append('</div></article>')
    out.append('</section>')
    return ''.join(out)


def day_two_section(data, inventory):
    by_id = {str(m['id']): m for m in inventory.get('matches', [])}
    out = ['<section class="content-section" id="day-two"><div class="section-heading"><div>'
           '<p class="eyebrow">Applying the review to the current card</p><h2>Day two: lines, reads and confidence</h2></div>'
           '<a class="internal-link" href="../picks/">Open the full picks list →</a></div>',
           '<p class="section-intro">Provider prices below are dated observations from Polymarket’s official Gamma record, '
           'shown as context. The current calculated estimates for these fixtures live on the '
           '<a href="../picks/">match picks page</a> and in the '
           '<a href="../origination/#picks">complete researched picks list</a>.</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-two fixtures with observed '
           'market prices, assessment and official sources</caption><thead><tr><th scope="col">Fixture &amp; start</th>'
           '<th scope="col">Observed market price</th><th scope="col">Review read</th></tr></thead><tbody>']
    for row in data['day_two']:
        fixture = by_id.get(str(row['hotspawn_id']))
        hotspawn_link = external(fixture['source_url'], 'Hotspawn fixture') if fixture else '<span class="unverified">— <small>Hotspawn row not in this snapshot</small></span>'
        lock = f'<small>Pick lock {local_time(fixture["locks_at"])}</small>' if fixture and fixture.get('locks_at') else '<small>Pick lock — <small>unverified</small></small>'
        market = row.get('market') or {}
        prices = market.get('prices') or {}
        price_rows = ''.join(f'<div class="prob-line"><span>{e(name)}</span><strong>{value * 100:.1f}%</strong></div>'
                             for name, value in prices.items()) or blank()
        observed = f'<small>{e(market.get("provider") or "Provider")} · observed {local_time(market["observed_at"])}</small>' if market.get('observed_at') else ''
        state = badge('Market open' if market.get('market_open') else 'Market closed', 'green' if market.get('market_open') else 'amber')
        note = f'<p class="tiny">{e(market["note"])}</p>' if market.get('note') else ''
        links = ''.join(external(url, label) for url, label in
                        [(market.get('event_url'), 'Polymarket event'), (market.get('api_url'), 'Gamma record')] if url)
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                   f'<small>{e(row["competition"])} · {e(row["slot"])}</small>'
                   f'<small>Start {local_time(row["starts_at"])}</small>{lock}'
                   f'<small>Hotspawn ID {e(row["hotspawn_id"])} · HLTV match {e(row["hltv_match_id"])}</small></th>'
                   f'<td>{price_rows}{observed}{state}{note}<div class="evidence-links">{links}</div></td>'
                   f'<td><p>{e(row["assessment"])}</p><p class="tiny"><strong>Status at observation:</strong> {e(row["status_at_observation"])}</p>'
                   f'{source_lines(row["sources"])}{external(row["hltv_url"], "HLTV match page")}'
                   f'<div class="evidence-links">{hotspawn_link}</div></td></tr>')
    out.append('</tbody></table></div>')
    discrepancy = data.get('time_discrepancy')
    if discrepancy:
        out.append('<div class="limitations-callout"><strong>Start-time discrepancy, recorded not smoothed</strong>'
                   f'<p>{e(discrepancy["detail"])}</p><div class="inline-links">'
                   + ''.join(external(s['url'], s.get('source') or 'Source') for s in discrepancy.get('sources', []))
                   + '</div></div>')
    out.append('</section>')
    return ''.join(out)

def day_three_section(data, inventory):
    out = ['<section class="content-section" id="day-three"><div class="section-heading"><div>'
           '<p class="eyebrow">Looking ahead to day three</p><h2>Day three: elimination matches and what day two changed</h2></div>'
           + badge('HLTV schedule', 'green') + '</div>',
           '<p class="section-intro">These fixtures are not in the Hotspawn scheduled-fixture feed captured on 14 Oct 2026, '
           'so no Hotspawn link or pick is produced for them. Market prices were not captured in this window and are left '
           'unpriced rather than estimated. Assessments below rest only on the verified day-one and day-two results above.</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-three elimination fixtures '
           'with HLTV links and review reads</caption><thead><tr><th scope="col">Fixture &amp; start</th>'
           '<th scope="col">Observed market price</th><th scope="col">Review read</th></tr></thead><tbody>']
    for row in data.get('day_three', []):
        market = row.get('market') or {}
        prices = market.get('prices') or {}
        price_rows = ''.join(f'<div class="prob-line"><span>{e(name)}</span><strong>{value * 100:.1f}%</strong></div>'
                             for name, value in prices.items()) or blank()
        observed = f'<small>{e(market.get("provider") or "Provider")} · observed {local_time(market["observed_at"])}</small>' if market.get('observed_at') else '<small>— unverified (not captured)</small>'
        links = ''.join(external(url, label) for url, label in
                        [(market.get('event_url'), 'Polymarket event'), (market.get('api_url'), 'Gamma record')] if url)
        hotspawn_link = '<span class="unverified">— <small>Hotspawn row not in this snapshot</small></span>'
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                   f'<small>{e(row["competition"])} · {e(row["slot"])}</small>'
                   f'<small>Start {local_time(row["starts_at"])}</small>'
                   f'<small>HLTV match {e(row["hltv_match_id"])}</small></th>'
                   f'<td>{price_rows}{observed}<div class="evidence-links">{links}</div></td>'
                   f'<td><p>{e(row["assessment"])}</p><p class="tiny"><strong>Status at observation:</strong> {e(row["status_at_observation"])}</p>'
                   f'{source_lines(row["sources"])}{external(row["hltv_url"], "HLTV match page")}'
                   f'<div class="evidence-links">{hotspawn_link}</div></td></tr>')
    out.append('</tbody></table></div></section>')
    return ''.join(out)


def day_three_results_section(review):
    rows = review.get('day_three_results') or []
    if not rows:
        return ''
    out = ['<section class="content-section" id="day-three-results"><div class="section-heading"><div>'
           '<p class="eyebrow">Group stage closed</p><h2>Day-three results</h2></div>'
           + badge('16 October 2026', 'green') + '</div>',
           '<p class="section-intro">Verified results only. A series still in progress at the research cutoff is shown as '
           'in progress — never completed by guess.</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-three results at Thunderpick '
           'World Championship 2026 with official sources</caption><thead><tr>'
           '<th scope="col">Series</th><th scope="col">Result at observation</th><th scope="col">Reading</th>'
           '</tr></thead><tbody>']
    for row in rows:
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                   f'<small>{e(row["slot"])} · {local_time(row["starts_at"])}</small></th>'
                   f'<td>{e(row.get("status_at_observation") or "")}</td>'
                   f'<td>{e(row.get("assessment") or "")}{source_lines(row.get("sources") or [])}'
                   + (f'{external(row["hltv_url"], "HLTV match page")}' if row.get('hltv_url') else '<span class="unverified">unverified</span>')
                   + '</td></tr>')
    out.append('</tbody></table></div></section>')
    return ''.join(out)


def _activity_text(provider):
    """Provider-reported odds depth, rendered only from recorded fields."""
    activity = provider.get('activity') or {}
    bits = []
    if activity.get('listed_at'):
        bits.append('listed ' + str(activity['listed_at']))
    if activity.get('opened_at'):
        bits.append('opened ' + str(activity['opened_at']))
    if activity.get('book_updated_at'):
        bits.append('book updated ' + str(activity['book_updated_at']))
    if activity.get('changed_since_open') is False:
        bits.append('no reprice since it opened')
    elif activity.get('changed_since_open') is True:
        bits.append('repriced since it opened')
    for key, label in [('last_price', 'last trade'), ('open_interest', 'open interest'), ('volume', 'traded')]:
        values = activity.get(key)
        if isinstance(values, list) and len(values) == 2 and all(isinstance(v, (int, float)) for v in values):
            bits.append(label + ' ' + ' / '.join(f'{v:,.2f}' for v in values))
    if isinstance(activity.get('volume_usd'), (int, float)):
        bits.append(f'volume ${activity["volume_usd"]:,.0f}')
    if isinstance(activity.get('liquidity_usd'), (int, float)):
        bits.append(f'liquidity ${activity["liquidity_usd"]:,.0f}')
    return ' · '.join(bits)


def day_four_section(review):
    rows = review.get('day_four') or []
    if not rows:
        return ''
    out = ['<section class="content-section" id="day-four"><div class="section-heading"><div>'
           '<p class="eyebrow">Day four</p><h2>Semifinal card with dated market observations</h2></div>'
           + badge('17 October 2026', 'amber') + '</div>',
           '<p class="section-intro">Prices below are historical observations with their own timestamps — some from thin '
           'markets — and never the Hotspawn "% picked" or fan votes. The <a href="../picks/">live picks page</a> supersedes '
           'them at every refresh.</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-four semifinal matchups with '
           'dated market observations and official sources</caption><thead><tr>'
           '<th scope="col">Series</th><th scope="col">Dated market observation</th><th scope="col">Status &amp; reading</th>'
           '</tr></thead><tbody>']
    for row in rows:
        market = row.get('market') or {}
        prices = market.get('prices') or {}
        price_text = '<span class="unverified">no verified market at the dated observation</span>'
        if prices:
            bits = ' · '.join(f'{e(name)} {value * 100:.1f}%' for name, value in prices.items())
            price_text = (f'<strong>{e(market.get("provider") or "")}</strong><small>{e(market.get("note") or "")}</small>'
                          f'<p class="tiny">{bits} · observed {e(market.get("observed_at") or "")}</p>')
            if market.get('event_url'):
                price_text += external(market['event_url'], 'market event')
            if market.get('api_url'):
                price_text += external(market['api_url'], 'official market record')
            if market.get('fair_decimal'):
                price_text += ('<p class="tiny">Reference line ' + ' · '.join(
                    f'{e(name)} {value:.2f}' for name, value in market['fair_decimal'].items())
                    + f'. {e(market.get("fair_decimal_note") or "")}</p>')
            for provider in market.get('providers') or []:
                detail = _activity_text(provider)
                if detail:
                    price_text += f'<p class="tiny">{e(provider.get("provider"))}: {e(detail)}</p>'
            movement = market.get('line_movement') or {}
            if movement.get('detail'):
                price_text += f'<p class="tiny"><strong>Line movement:</strong> {e(movement["detail"])}</p>'
            elif movement.get('points'):
                price_text += f'<p class="tiny"><strong>Line movement:</strong> {e(str(movement["points"]))}</p>'
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                   f'<small>{e(row["slot"])} · {local_time(row["starts_at"])}</small>'
                   + (f'{external(row["hltv_url"], "HLTV match page")}' if row.get('hltv_url') else '') + '</th>'
                   f'<td>{price_text}</td>'
                   f'<td>{e(row.get("status_at_observation") or "")}<br>{e(row.get("assessment") or "")}'
                   f'{source_lines(row.get("sources") or [])}</td></tr>')
    out.append('</tbody></table></div>')
    guidance = review.get('day_four_guidance') or {}
    if guidance.get('principles'):
        out.append('<div class="evidence-box" id="day-four-guidance"><p class="eyebrow">Strategy notes</p>'
                   f'<h3>{e(guidance.get("title") or "Day-four guidance")}</h3><ul>'
                   + ''.join(f'<li>{e(item)}</li>' for item in guidance['principles']) + '</ul>'
                   + source_list(guidance.get('sources') or []) + '</div>')
    out.append('</section>')
    return ''.join(out)


def group_stage_section(review):
    """The completed ten-series group stage, straight from HLTV's results page."""
    record = review.get('group_stage_record') or {}
    rows = record.get('series') or []
    if not rows:
        return ''
    summary = record.get('summary') or {}
    out = ['<section class="content-section" id="group-stage-record"><div class="section-heading"><div>'
           '<p class="eyebrow">Group stage closed</p><h2>All ten series, as HLTV published them</h2></div>'
           + badge(local_time(record.get('observed_at')) if record.get('observed_at') else 'undated', 'green') + '</div>',
           '<p class="section-intro">' + e(record.get('note') or '') + '</p>',
           '<div class="table-scroll"><table class="simple-table" id="group-stage-series"><caption class="sr-only">Every '
           'completed group-stage series at Thunderpick World Championship 2026 with its HLTV result</caption><thead><tr>'
           '<th scope="col">Series</th><th scope="col">Result</th><th scope="col">What it means for a pick’ems card</th>'
           '</tr></thead><tbody>']
    for row in rows:
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                   f'<small>Day {e(row["day"])} · {e(row["group"])} · {e(row["slot"])} · {e(row["date"])}</small></th>'
                   f'<td><strong>{e(row["winner"])} {e(row["score"])}</strong>'
                   f'<small>{e(row["maps_played"])} maps · bo3</small>'
                   + external(row['url'], 'HLTV match page') + '</td>'
                   f'<td>{"Sweep — the exact-score half of the card was the differentiator." if row["score"] in ("2-0", "0-2") else "Third map — a score pick of 2-0 paid nothing even with the right team."}'
                   f'{source_lines(row.get("sources") or [])}</td></tr>')
    out.append('</tbody></table></div>')
    out.append('<div class="limitations-callout"><p><strong>'
               f'{e(summary.get("sweeps"))} of {e(summary.get("series_completed"))} series ended 2-0</strong> — '
               f'{e(round((summary.get("sweep_rate") or 0) * 100))}% — and {e(summary.get("decided_in_third_map"))} went to a third map. '
               f'{e(summary.get("reading") or "")}</p>'
               f'<p class="tiny">Qualified: {e(", ".join(summary.get("qualified") or []))}. '
               f'Eliminated: {e(", ".join(summary.get("eliminated") or []))}. '
               f'{external(record["source_url"], "HLTV results for event 8932")}</p></div>')
    load = record.get('map_load') or []
    if load:
        out.append('<div class="table-scroll"><table class="simple-table" id="group-stage-load"><caption>Maps played by the '
                   'four semifinalists (counted from published series scores)</caption><thead><tr><th scope="col">Team</th>'
                   '<th scope="col">Series · maps</th><th scope="col">Rest before the semifinal</th></tr></thead><tbody>')
        for row in load:
            out.append('<tr>'
                       f'<th scope="row">{e(row["team"])}</th>'
                       f'<td>{e(row["series_played"])} series · {e(row["maps_played"])} maps<small>{e(row["days_played"])}</small></td>'
                       f'<td>{e(row["rest_before_semifinal"])}{source_lines(record.get("sources") or [])}</td></tr>')
        out.append('</tbody></table></div>'
                   f'<p class="tiny">{e(record.get("map_load_note") or "")} The rest read is weighed against the priced '
                   'card in <a class="internal-link" href="#day-four-refresh">the dated semifinal section</a>.</p>')
    out.append('</section>')
    return ''.join(out)


def day_four_refresh_section(review):
    """The two semifinals with the provider record read for each, dated and single-sourced."""
    block = review.get('day_four_refresh') or {}
    rows = block.get('fixtures') or []
    if not rows:
        return ''
    out = ['<section class="content-section" id="day-four-refresh"><div class="section-heading"><div>'
           '<p class="eyebrow">Dated refresh · not a pipeline pick</p><h2>Semifinal card, read from the provider record</h2></div>'
           + badge(local_time(block['observed_at']) if block.get('observed_at') else 'undated', 'amber') + '</div>',
           '<p class="section-intro">' + e(block.get('policy') or '') + '</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-four semifinals with dated '
           'first-party market observations</caption><thead><tr><th scope="col">Series</th>'
           '<th scope="col">Dated market observation</th><th scope="col">Reading</th></tr></thead><tbody>']
    for row in rows:
        market = row.get('market') or {}
        probs = market.get('derived_probabilities') or {}
        best = max(probs, key=probs.get) if probs else None
        cells = []
        for name in (row['team_a'], row['team_b']):
            value = probs.get(name)
            if isinstance(value, (int, float)):
                favored = ' favored' if name == best and max(probs.values()) - min(probs.values()) > 0.05 else ''
                cells.append(f'<div class="prob-line{favored}"><span class="prob-team">{e(name)}'
                             f'<small class="fair-line">Fair line {1 / value:.3f}</small></span>'
                             f'<strong>{value * 100:.1f}%</strong></div>')
            else:
                cells.append(f'<div class="prob-line"><span>{e(name)}</span>{blank()}</div>')
        prob_pair = ('<p class="tiny muted">Estimated win chance from the record above — market-implied, not a verified '
                     'true probability. No default 50/50 is applied to a blank side.</p>') + ''.join(cells)
        price_text = '<span class="unverified">no verified market at this observation</span>'
        if probs:
            price_text = (f'<strong>{e(market.get("provider") or "")}</strong>'
                          f'<p class="tiny">bid/ask {e(market.get("best_bid"))}/{e(market.get("best_ask"))} · '
                          f'spread {e(market.get("spread"))} · last trade {e(market.get("last_trade_price"))} · '
                          f'volume ${e(market.get("volume_usd"))} · liquidity ${e(market.get("liquidity_usd"))}</p>'
                          f'<p class="tiny">Provider record updated {e(market.get("provider_updated_at") or "— unverified")} · '
                          f'read {local_time(market["observed_at"])} · event {e(market.get("event_id") or "—")}'
                          + (f' · market {e(market.get("market_id"))}' if market.get('market_id') else '')
                          + (f' · condition {e(market.get("condition_id"))}' if market.get('condition_id') else ' · market/condition id not re-read: blank')
                          + '</p>'
                          + f'<small>{e(market.get("note") or "")}</small>'
                          + (external(market['api_url'], 'official market record') if market.get('api_url') else '')
                          + (external(market['public_url'], 'market page') if market.get('public_url') else ''))
        statements = ''.join(
            f'<li>{e(x["text"])}<small>{e(x["reading"])} · {local_time(x["observed_at"])}</small>{external(x["url"], "HLTV analytics")}</li>'
            for x in row.get('hltv_statements') or [])
        check = row.get('cross_check') or {}
        cross = ''
        if check.get('prices'):
            values = ' · '.join(f'{e(name)} {v * 100:.1f}%' for name, v in check['prices'].items())
            cross = ('<p class="tiny">Cross-check against this page’s Day-4 record'
                     + (f', read {local_time(check["observed_at"])}' if check.get('observed_at') else '')
                     + f' from {e(check.get("providers") or "other providers")}: {values}. {e(check.get("detail") or "")} '
                     + '<a class="internal-link" href="#day-four">Day-4 record ↓</a></p>')
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                   f'<small>{e(row["slot"])} · {local_time(row["starts_at"])} UTC · {e(row["format"])}</small>'
                   + external(row['hltv_url'], 'HLTV match page')
                   + f'<small>{e(row.get("start_time_basis") or "")}</small></th>'
                   f'<td>{price_text}{prob_pair}{cross}</td>'
                   f'<td>{e(row.get("assessment") or "")}{("<ul>" + statements + "</ul>") if statements else ""}'
                   f'{source_lines(row.get("sources") or [])}</td></tr>')
    out.append('</tbody></table></div></section>')
    return ''.join(out)


def day_five_section(review):
    block = review.get('day_five_card') or {}
    rows = block.get('matches') or []
    if not rows:
        return ''
    resolved = block.get('bracket_status') == 'resolved'
    if not resolved:
        out = ['<section class="content-section" id="day-five-card"><div class="section-heading"><div>'
               '<p class="eyebrow">Blank on purpose</p><h2>Day five: bracket still open</h2></div>'
               + badge(local_time(block['observed_at']) if block.get('observed_at') else 'undated', 'amber') + '</div>',
               '<p class="section-intro">' + e(block.get('note') or '') + '</p>',
               '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-five fixtures left '
               'unresolved because their semifinalists are not decided</caption><thead><tr><th scope="col">Fixture</th>'
               '<th scope="col">Status at observation</th><th scope="col">Pick &amp; probability</th></tr></thead><tbody>']
        for row in rows:
            out.append('<tr>'
                       f'<th scope="row"><strong>{e(row["slot"])}</strong>'
                       f'<small>bo{e(row.get("best_of"))} · Sunday 18 October 2026 (UTC start not confirmed from an official source)</small>'
                       + external(row['url'], 'HLTV match page') + '</th>'
                       f'<td>{e(row.get("status") or "")}</td>'
                       f'<td><span class="unverified">Teams: — unverified · Pick: — unverified · Probability: — unverified</span></td></tr>')
        out.append('</tbody></table></div>')
        out.append('<ul>' + ''.join(f'<li>{e(x)}</li>' for x in block.get('limitations') or []) + '</ul>')
        out.append(f'<p class="tiny">{external(block["source_url"], "HLTV event schedule")}</p></section>')
        return ''.join(out)

    out = ['<section class="content-section" id="day-five-card"><div class="section-heading"><div>'
           '<p class="eyebrow">Final day · Sunday 18 October 2026</p><h2>Day five: the final day</h2></div>'
           + badge(local_time(block['observed_at']) if block.get('observed_at') else 'undated', 'green') + '</div>',
           '<p class="section-intro">' + e(block.get('note') or '') + '</p>']

    semis = block.get('semifinal_results') or []
    if semis:
        out.append('<div class="table-scroll"><table class="simple-table" id="day-five-recap"><caption class="sr-only">Day-four semifinal '
                   'results, as HLTV published them</caption><thead><tr><th scope="col">Semifinal</th>'
                   '<th scope="col">Result &amp; maps</th><th scope="col">Reading</th></tr></thead><tbody>')
        for row in semis:
            maps = ' · '.join(f'{e(m["map"])} {m["a"]}-{m["b"]}' for m in row.get('maps') or [])
            out.append('<tr>'
                       f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                       f'<small>{e(row["slot"])} · 17 Oct 2026</small>'
                       + external(row['hltv_url'], 'HLTV match page') + '</th>'
                       f'<td><strong>{e(row["team_a"])} {e(row["score"])} {e(row["team_b"])}</strong><small>{maps}</small></td>'
                       f'<td><p>{e(row.get("reading") or "")}</p>{source_lines(row.get("sources") or [])}</td></tr>')
        out.append('</tbody></table></div>')

    scan = block.get('market_scan') or {}
    if scan:
        probes = ''.join(f'<li>{e(p.get("provider") or "")} — {e(p.get("outcome") or "")}'
                         f'<small>{e(p.get("detail") or "")} · read {local_time(p["observed_at"])}</small>'
                         + external(p['url'], 'probe record') + '</li>'
                         for p in scan.get('probes') or [])
        out.append('<div class="limitations-callout" id="day-five-market-scan"><p class="eyebrow">External market scan</p>'
                   f'<p><strong>{e(scan.get("question") or "")}</strong> {e(scan.get("reading") or "")}</p>'
                   f'<ul>{probes}</ul><p class="tiny">{e(scan.get("would_count") or "")}</p></div>')

    out.append('<div class="table-scroll"><table class="simple-table" id="day-five-matches"><caption class="sr-only">Day-five fixtures with '
               'labelled fallback estimates, default picks, score context and official sources</caption><thead><tr>'
               '<th scope="col">Series</th><th scope="col">Estimate &amp; default pick</th>'
               '<th scope="col">Score, contrarian watch &amp; evidence</th></tr></thead><tbody>')
    for row in rows:
        names = row.get('teams') or []
        model = row.get('model_estimate') or {}
        probs = row.get('probabilities')
        pair = probs if probs is not None else (model.get('probabilities') if model else None)
        basis_label = 'External money line' if probs is not None else 'Valve-model fallback (uncalibrated research estimate)'
        cells = []
        if pair:
            best = max(range(2), key=lambda i: pair[i]) if abs(pair[0] - pair[1]) >= 1e-8 else None
            for i, name in enumerate(names):
                value = pair[i]
                favored = ' favored' if i == best else ''
                cells.append(f'<div class="prob-line{favored}"><span class="prob-team">{e(name)}'
                             f'<small class="fair-line">Fair line {1 / value:.3f}</small></span>'
                             f'<strong>{value * 100:.1f}%</strong></div>')
        else:
            cells.append('<div class="prob-line"><span>Both teams</span>'
                         '<span class="unverified">— unverified (no estimate could be established)</span></div>')
        prob_pair = (f'<p class="tiny muted">{e(basis_label)} — market-implied or model-estimated, not a verified '
                     'true probability. No default 50/50 is applied to a blank side.</p>') + ''.join(cells)
        money_line = ('<p class="tiny"><strong>External money line:</strong> '
                      + (f'{e((row.get("market") or {}).get("provider") or "provider record")} · read '
                         f'{local_time((row.get("market") or {}).get("observed_at"))}'
                         if row.get('market') else
                         '<span class="unverified">— unverified (no full-series book listed at the market scan)</span>')
                      + '</p>')
        if model:
            inputs = ' · '.join(f'{e(i["name"])} {i["points"]} pts (#{i["standing"]}, snapshot {e(i.get("snapshot_date") or model.get("snapshot_date") or "")})'
                                for i in model.get('inputs') or [])
            money_line += (f'<p class="tiny">{e(model.get("label") or "Model fallback")}: {inputs}'
                           f' · RD {e(model.get("rd_assumption"))} · snapshot {e(model.get("snapshot_date") or "")}</p>'
                           + external(model.get('formula_source', ''), 'published formula')
                           + (f'<a href="../{e(model.get("evidence_file"))}">Saved Valve evidence ↓</a>'
                              if model.get('evidence_file') else ''))
        pick = row.get('pick')
        pick_text = (f'<p><span class="glance-pick-label">Default pick</span><strong>{e(pick)}</strong></p>'
                     f'<p class="tiny">{e(row.get("pick_basis") or "")}</p>') if pick else \
                    '<p><span class="unverified">Pick: — unverified</span></p>'
        score = row.get('score') or {}
        if score:
            score_text = (f'<p><strong>Score slip (editorial): {e(score.get("suggested"))}</strong></p>'
                          f'<p class="tiny">{e(score.get("basis") or "")}</p>'
                          + (external(score['source_url'], 'HLTV analytics') if score.get('source_url') else ''))
        else:
            score_text = ('<p><strong>Score slip:</strong> <span class="unverified">— not published</span></p>'
                          f'<p class="tiny">{e(row.get("score_limitation") or "")}</p>')
        watch = row.get('contrarian_watch') or {}
        watch_text = ''
        if watch:
            cost = watch.get('cost_per_base_point')
            cost_text = (f' Expected-point cost of the risk versus the default pick: {cost:.3f} per base point on offer.'
                         if isinstance(cost, (int, float)) else '')
            watch_text = (f'<div class="evidence-box"><p class="eyebrow">Contrarian watch · {e(watch.get("team") or "")}</p>'
                          f'<p>{e(watch.get("case") or "")}</p><p class="tiny">{e(watch.get("screen") or "")}{cost_text}</p>'
                          + (external(watch['source_url'], 'source') if watch.get('source_url') else '')
                          + f'<p class="tiny">Read {local_time(watch.get("observed_at")) if watch.get("observed_at") else "— unverified"}</p></div>')
        context = ''.join(f'<li>{e(x)}</li>' for x in row.get('context') or [])
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(names[0])} vs {e(names[1])}</strong>'
                   f'<small>{e(row.get("slot") or "")} · bo{e(row.get("best_of"))} · {local_time(row.get("starts_at"))} UTC · '
                   f'{e(row.get("format") or "")}</small>'
                   + external(row['url'], 'HLTV match page')
                   + f'<small>{e(row.get("status") or "")}</small>'
                   + f'<small>{e(row.get("start_time_basis") or "")}</small></th>'
                   f'<td>{money_line}{prob_pair}{pick_text}</td>'
                   f'<td>{score_text}{watch_text}'
                   + (f'<ul class="tiny">{context}</ul>' if context else '')
                   + f'{source_lines(row.get("sources") or [])}</td></tr>')
    out.append('</tbody></table></div>')

    guidance = review.get('day_five_guidance') or {}
    if guidance.get('principles'):
        out.append('<div class="evidence-box" id="day-five-guidance"><p class="eyebrow">Final-day strategy notes</p>'
                   f'<h3>{e(guidance.get("title") or "Day-five guidance")}</h3><ul>'
                   + ''.join(f'<li>{e(item)}</li>' for item in guidance['principles']) + '</ul>'
                   + ('<p class="tiny"><strong>Screens applied:</strong> ' + ' · '.join(e(x) for x in guidance.get('screens') or []) + '</p>'
                      if guidance.get('screens') else '')
                   + source_list(guidance.get('sources') or []) + '</div>')

    prior = block.get('prior_observation') or {}
    if prior:
        out.append(f'<p class="tiny"><strong>Dated history</strong> — {local_time(prior.get("observed_at"))}: '
                   f'{e(prior.get("state") or prior.get("note") or "")}</p>')
    out.append('<ul>' + ''.join(f'<li>{e(x)}</li>' for x in block.get('limitations') or []) + '</ul>')
    out.append(f'<p class="tiny">{external(block["source_url"], "HLTV event schedule")}</p></section>')
    return ''.join(out)


def score_slip_section(review):
    block = review.get('score_slip_evidence') or {}
    if not block:
        return ''
    out = ['<section class="content-section" id="score-slip"><div class="section-heading"><div>'
           '<p class="eyebrow">Team plus score</p><h2>' + e(block.get('title') or 'Score-line evidence') + '</h2></div>'
           + badge(local_time(block['observed_at']) if block.get('observed_at') else 'undated', 'neutral') + '</div>',
           '<p class="section-intro">' + e(block.get('policy') or '') + '</p>',
           '<div class="table-scroll"><table class="simple-table"><caption>Series-score frequency by team, as published on '
           'HLTV’s match analytics page</caption><thead><tr><th scope="col">Team</th><th scope="col">Sample</th>'
           '<th scope="col">Frequency of each series score</th></tr></thead><tbody>']
    for row in block.get('hltv_frequencies') or []:
        freqs = ' · '.join(f'{e(label)} {value * 100:.1f}%' for label, value in row.get('rows') or [])
        out.append('<tr>'
                   f'<th scope="row">{e(row["team"])}</th>'
                   f'<td>{e(row["series_count"])} series · {e(row["map_count"])} maps<small>past 3 months, all events</small></td>'
                   f'<td>{e(freqs)}{external(row["source_url"], "HLTV match analytics")}'
                   f'<small>read {local_time(row["observed_at"])}</small></td></tr>')
    out.append('</tbody></table></div>')
    rate = block.get('event_base_rate') or {}
    if rate:
        out.append('<div class="limitations-callout"><p><strong>This event’s own base rate</strong> — '
                   f'{e(rate.get("detail"))}</p><p>{e(rate.get("reading"))}</p>'
                   + external(rate['source_url'], 'HLTV results for event 8932')
                   + f'<small> read {local_time(rate["observed_at"])}</small></div>')
    out.append('<p class="tiny">The ten series behind that base rate are listed row by row in '
               '<a class="internal-link" href="#group-stage-series">All ten series, as HLTV published them</a>; '
               'what the same sweep rate is worth against a specific priced line is in '
               '<a class="internal-link" href="#day-four-refresh">the dated semifinal card</a>.</p>')
    out.append('<ul>' + ''.join(f'<li>{e(x)}</li>' for x in block.get('limitations') or []) + '</ul></section>')
    return ''.join(out)


def valve_snapshot_note(snapshot):
    if not snapshot:
        return ''
    roster = ', '.join(snapshot.get('roster') or []) or '— unverified'
    return ('<div class="evidence-box"><p class="eyebrow">Official rating snapshot</p>'
            f'<p class="tiny"><strong>Valve standings {e(snapshot.get("snapshot_date") or "undated")}</strong>: '
            f'#{e(snapshot.get("standing"))} · {e(snapshot.get("points"))} points · {e(roster)}</p>'
            f'<p class="tiny">{e(snapshot.get("caveat") or "")}</p>'
            f'{external(snapshot["source_url"], "Valve official standings")}</div>')


def saved_evidence_link(evidence_file: str, data_dir) -> str:
    """Link the saved evidence file only if this snapshot actually has it; otherwise say so (blank and flagged)."""
    if data_dir is not None and not (Path(data_dir) / str(evidence_file).removeprefix('data/')).exists():
        return '<span class="unverified">saved evidence file not present in this snapshot (the Valve source was unreachable) — unverified</span>'
    return f'<a href="../{e(evidence_file)}">Saved first-party evidence ↓</a>'


def standings_section(data, data_dir=None):
    block = data.get('valve_standings')
    if not block or not block.get('rows'):
        return ''
    out = ['<section class="content-section" id="standings"><div class="section-heading"><div>'
           '<p class="eyebrow">Official rating inputs</p><h2>Valve standings for the day-two field</h2></div>'
           + badge('Valve snapshot ' + str(block.get('snapshot_date') or ''), 'purple') + '</div>',
           f'<p class="section-intro">{e(block["note"])}</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Valve regional standings '
           'snapshot for the day-two teams, with rosters and official source</caption><thead><tr>'
           '<th scope="col">Team</th><th scope="col">Standing &amp; points</th><th scope="col">Published roster</th>'
           '</tr></thead><tbody>']
    for row in block['rows']:
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["name"])}</strong><small>Snapshot {e(row["snapshot_date"])}</small></th>'
                   f'<td>#{e(row["standing"])}<small>{e(row["points"])} points</small></td>'
                   f'<td>{e(", ".join(row["roster"]))}{external(row["source_url"], "Valve record")}</td></tr>')
    out.append('</tbody></table></div><div class="inline-links downloads">'
               + external(block['source_url'], 'Valve official standings')
               + saved_evidence_link(block.get('evidence_file', 'data/evidence/valve-ratings.json'), data_dir)
               + '</div></section>')
    return ''.join(out)


def edge_review(data, prefix, edge_path: Path):
    review = load_edge(edge_path)
    window = review['research_window']
    out = heading('Dated first-party research', review['title'],
                  'What day one at Thunderpick World Championship 2026 actually told us — the 9z upset over Aurora, the roster '
                  'context (not proven causation), and the rules we apply before disagreeing with a market.')
    out += ('<div class="limitations-callout"><strong>This review is dated research, not a live feed.</strong>'
            f'<p>Prepared {local_time(review["prepared_at"])}. Research window {local_time(window["from"])} → {local_time(window["to"])}. '
            'Market prices on this page are historical observations with their own timestamps. Current probabilities stay on the '
            f'<a href="{prefix}picks/">match picks page</a>. {e(review["policy"])}</p>'
            f'<div class="inline-links"><a href="{prefix}picks/">Current picks →</a>'
            f'<a href="{prefix}origination/#picks">Complete researched picks →</a>'
            f'<a href="{prefix}twc-picks/">Current TWC probabilities &amp; Days 1–2 review →</a>'
            f'<a href="{prefix}review/">Flagged for Review →</a></div></div>')
    out += ('<section class="content-section"><div class="section-heading"><div><p class="eyebrow">The upset</p>'
            '<h2>9z 2-0 Aurora</h2></div>' + badge('Day one · Group A', 'amber') + '</div>'
            f'<div class="prose"><p>{e(review["headline"]["text"])}</p>{source_lines(review["headline"]["sources"])}'
            f'<p class="tiny">{e(review["event"]["name"])} · {e(review["event"]["dates"])} · {e(review["event"]["location"])} · '
            f'{e(review["event"]["teams"])} teams · {external(review["event"]["url"], "HLTV event page")}</p>'
            f'<p class="tiny">{e(review["event"]["format_note"])}</p></div></section>')
    out += day_one_section(review)
    out += roster_section(review)
    out += rules_section(review)
    out += day_two_section(review, data)
    out += day_three_section(review, data)
    out += day_three_results_section(review)
    out += day_four_section(review)
    out += group_stage_section(review)
    out += day_four_refresh_section(review)
    out += score_slip_section(review)
    out += day_five_section(review)
    refresh = review.get('session_refresh') or {}
    if refresh:
        out += ('<section class="content-section prose" id="edge-refresh-note"><p class="eyebrow">Dated research note</p>'
                '<h2>What this session changed</h2>'
                f'<p><strong>Session {e(refresh.get("session"))}</strong>, prepared {local_time(refresh.get("prepared_at"))}. '
                f'{e(refresh.get("reads") or "")}</p><p>{e(refresh.get("what_changed") or "")}</p>'
                f'<p class="tiny">{e(refresh.get("not_touched") or "")}</p>'
                f'<p>{external("https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/edge-review.json", "This page’s data file")}</p></section>')
    day3_path = edge_path.parent / 'day3-guide.json'
    if day3_path.exists():
        from scripts.build_day3 import load_day3, render_section
        out += render_section(load_day3(day3_path), prefix)
    out += standings_section(review, edge_path.parent)
    disambig_path = edge_path.parent / 'research' / 'f392649f' / 'lineup-disambiguation.json'
    valve_path = edge_path.parent / 'research' / '6426358d' / 'valve-ratings-2026-10-05.json'
    if disambig_path.exists() and valve_path.exists():
        from scripts.lineup_disambiguation import load_disambiguation, render_disambiguation_section
        out += render_disambiguation_section(load_disambiguation(disambig_path, valve_path), prefix)
    out += ('<section class="content-section prose" id="edge-limitations"><p class="eyebrow">What this review cannot tell you</p>'
            '<h2>Limitations</h2><ul>' + ''.join(f'<li>{e(x)}</li>' for x in review['limitations']) + '</ul>'
            f'<p>{external("https://www.hltv.org/results?event=8932", "HLTV official event results")} '
            f'{external("https://docs.polymarket.com/api-reference/market-data/get-order-book", "Polymarket official market-data contract")} '
            f'<a href="{prefix}methodology/">How current probabilities are calculated →</a></p></section>')
    return out


def build(source: Path, output: Path):
    data = json.loads((source / 'latest.json').read_text())
    review = load_edge(source / 'edge-review.json')
    target = output / 'edge'
    target.mkdir(parents=True, exist_ok=True)
    body = edge_review(data, '../', source / 'edge-review.json')
    from scripts.build import shell
    (target / 'index.html').write_text(shell(data, 'edge', body, '../'))
    return target / 'index.html', review


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('site'))
    args = parser.parse_args()
    path, review = build(args.source, args.output)
    print(f'Built {path} · {len(review["day_one"])} day-one series · {len(review["day_two"])} day-two fixtures · '
          f'{len(review.get("day_three", []))} day-three fixtures reviewed · '
          f'{len(review.get("day_three_results", []))} day-three results · {len(review.get("day_four", []))} day-four rows')
