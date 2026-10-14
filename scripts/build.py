"""Build accessible, dependency-light static Pages subpages from verified JSON."""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.domain import timestamp, is_fresh
from scripts.validate import check_data, check_links

REPO = 'https://github.com/buffedlizard55-lab/MaltaProj3'
LOBBY = 'https://play.hotspawn.com/lobby'
PAGES = {'summary': ('Executive summary', 'index.html', 'overview'), 'picks': ('Match picks', 'picks/index.html', 'target'), 'coverage': ('Coverage & sources', 'coverage/index.html', 'layers'), 'methodology': ('Methodology', 'methodology/index.html', 'book'), 'review': ('Flagged for Review', 'review/index.html', 'flag')}
ICONS = {
    'overview': '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    'target': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    'layers': '<path d="m12 3 10 5-10 5L2 8l10-5Z"/><path d="m2 12 10 5 10-5M2 16l10 5 10-5"/>',
    'book': '<path d="M12 5v16M3 3h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5v16h-5a4 4 0 0 0-4 2 4 4 0 0 0-4-2H3V3Z"/>',
    'flag': '<path d="M5 21V3h8l1 3h6v10h-7l-1-3H5"/>',
    'arrow': '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    'external': '<path d="M14 3h7v7m0-7L10 14M10 3H4a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-6"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
}


def e(value):
    return html.escape(str(value), quote=True)


def icon(key, cls=''):
    return f'<svg class="icon {e(cls)}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[key]}</svg>'


def external(url, text, cls='source-link'):
    return f'<a class="{e(cls)}" href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(text)}{icon("external")}</a>'


def local_time(value, date_only=False):
    dt = timestamp(value)
    if not dt:
        return '<span class="unverified">— <small>unverified</small></span>'
    fmt = '%d %b %Y' if date_only else '%d %b, %H:%M'
    return f'<time datetime="{e(value)}" data-time="{e(value)}" data-format="{"date" if date_only else "full"}">{dt.astimezone(ZoneInfo("Europe/Malta")).strftime(fmt)}</time>'


def badge(text, kind='neutral'):
    return f'<span class="badge {e(kind)}">{e(text)}</span>'


def blank():
    return '<span class="unverified">— <small>unverified</small></span>'


def heading(eyebrow, title, description, extra=''):
    return f'<header class="page-heading"><div><p class="eyebrow">{e(eyebrow)}</p><h1>{e(title)}</h1><p class="page-description">{e(description)}</p></div>{extra}</header>'


def match_name(m):
    return ' vs '.join(t['name'] or 'Unverified team' for t in m['teams'])


def evidence(m, prefix):
    a = m['analysis']
    body = '<div class="evidence-box"><p class="eyebrow">Source observations</p><dl class="fact-list">'
    for label, value in [('Hotspawn status', e(m['source_status']) if m['source_status'] else blank()), ('Scheduled start', local_time(m['starts_at'])), ('Pick lock', local_time(m['locks_at'])), ('Best of (Hotspawn)', e(m['best_of']) if m['best_of'] is not None else blank()), ('Inventory observed', local_time(m['observed_at']))]:
        body += f'<div><dt>{label}</dt><dd>{value}</dd></div>'
    body += '</dl><div class="evidence-links">' + external(m['source_url'], 'Hotspawn match') + external(m['source_api'], 'Original fixture API') + f'<a href="{prefix}data/evidence/hotspawn-fixtures.json">Saved fixture evidence ↓</a></div>'
    if a:
        body += f'<h4>{e(a["label"])}</h4><p>Observed {local_time(a["observed_at"])}. Calculated fair lines: <strong>{e(a["fair_decimal"][0])} / {e(a["fair_decimal"][1])}</strong> (not quoted bookmaker odds).</p>'
        if a['method'] == 'market':
            body += '<div class="mini-table-wrap"><table class="mini-table"><caption>Original bid/ask observations</caption><thead><tr><th>Team</th><th>Bid / ask</th><th>Source</th></tr></thead><tbody>'
            for t, q in zip(m['teams'], a['quotes']):
                body += f'<tr><th scope="row">{e(t["name"])}</th><td>{q["bid"]:.3f} / {q["ask"]:.3f}</td><td>{external(a["source_api"], "Polymarket API")}</td></tr>'
            body += '</tbody></table></div>'
        elif a['method'] == 'model':
            body += f'<p>Rating snapshot: <strong>{e(a["snapshot_date"])}</strong>. Roster lists below belong to that snapshot, not a confirmed current lineup.</p><div class="mini-table-wrap"><table class="mini-table"><caption>Published model inputs</caption><thead><tr><th>Team</th><th>Points</th><th>Source</th></tr></thead><tbody>'
            for r in a['inputs']:
                body += f'<tr><th scope="row">{e(r["name"])}</th><td>{r["points"]}</td><td>{external(r["source_url"], "Valve")}</td></tr>'
            body += '</tbody></table></div>'
            for r in a['inputs']:
                body += f'<p class="tiny"><strong>{e(r["name"])}</strong>: {e(", ".join(r["roster"]))}</p>'
        elif a['method'] == 'bookmaker':
            for q in a['quotes']:
                body += f'<p>Quoted decimal odds: {e(q["odds"][0])} / {e(q["odds"][1])}. {external(q["source_url"], q["provider"])}</p>'
        body += '<ul class="limitations">' + ''.join(f'<li>{e(x)}</li>' for x in a['limitations']) + '</ul>' + external(a['source_url'], a['source'])
    if m['research']:
        body += '<h4>Resolution trail</h4><ol class="research-trail">'
        for r in m['research']:
            body += f'<li><strong>{e(r["stage"])}</strong> · {e(r["status"])}<p>{e(r["detail"])}</p>{external(r["source_url"], "Original source")}</li>'
        body += '</ol>'
    body += '</div>'
    return f'<details class="row-details"><summary>Evidence &amp; analysis <span aria-hidden="true">+</span></summary>{body}</details>'


def matches_table(matches, prefix, *, table_id='match-list', filters=False):
    if not matches:
        return '<div class="empty-state">No verified future fixtures in this snapshot. Check the <a href="' + prefix + 'coverage/">source status</a> before assuming there are no matches.</div>'
    out = f'<div class="matches-wrap"><table class="matches-table" id="{table_id}"><caption class="sr-only">Hotspawn CS2 match picks. Percentages are calculated estimates, never guaranteed outcomes. Times are Europe/Malta unless changed.</caption><thead><tr><th scope="col">Match &amp; start</th><th scope="col">Win probabilities</th><th scope="col">Our pick</th><th scope="col">Basis &amp; verification</th></tr></thead><tbody>'
    now = datetime.now(timezone.utc)
    for m in matches:
        a, pick = m['analysis'], m['pick_index']
        method = a['method'] if a else 'unresolved'
        names = [t['name'] or 'Unverified team' for t in m['teams']]
        confidence = max(a['probabilities']) if a else 0
        search = ' '.join(names + [m['competition'] or '', method]).casefold()
        out += f'<tr id="match-{e(m["id"])}" class="match-row" data-record-id="{e(m["id"])}" data-search="{e(search)}" data-method="{method}" data-tournament="{e(m["competition"] or "Unverified tournament")}" data-confidence="{confidence}" data-start="{e(m["starts_at"] or "")}" data-lock="{e(m["locks_at"] or "")}" data-price-time="{e(a["observed_at"] if a else "")}">'
        tier = ('Tier ' + str(m['tier']).upper()) if m['tier'] else 'Tier unverified'
        out += f'<td class="match-cell"><span class="competition">{e(m["competition"] or "Unverified tournament")}</span><div class="team-pair"><strong>{e(names[0])}</strong><span class="versus">vs</span><strong>{e(names[1])}</strong></div><div class="match-subline">{local_time(m["starts_at"])}<span class="dot-separator">·</span><span>{e(tier)}</span></div><span class="availability" data-availability>{"Open for picks" if m["availability"] == "open" else "Locked" if m["availability"] == "locked" else "Lock time unverified"}</span></td>'
        out += '<td class="probability-cell" data-label="Win probabilities">'
        if a:
            for i, (name, p) in enumerate(zip(names, a['probabilities'])):
                out += f'<div class="prob-line {"favored" if i == pick else ""}"><span>{e(name)}</span><strong>{p * 100:.1f}%</strong></div>'
            out += f'<div class="prob-bar" aria-hidden="true"><span class="bar-a" style="width:{a["probabilities"][0] * 100:.4f}%"></span><span class="bar-b" style="width:{a["probabilities"][1] * 100:.4f}%"></span></div><span class="tiny muted">Calculated · full-series winner</span>'
        else:
            out += '<div class="prob-line"><span>' + e(names[0]) + '</span>' + blank() + '</div><div class="prob-line"><span>' + e(names[1]) + '</span>' + blank() + '</div><p class="tiny muted">Insufficient verified inputs. No default 50/50.</p>'
        out += '</td><td class="pick-cell" data-label="Our pick">'
        if a and pick is not None:
            out += f'<div class="pick-choice" data-pick-choice>{icon("check")}<strong>{e(names[pick])}</strong></div><p class="pick-caption" data-pick-caption>{max(a["probabilities"]) * 100:.1f}% estimated win chance</p>'
        elif a:
            out += '<strong class="muted">No directional edge</strong><p class="pick-caption">Equal estimate; no arbitrary pick.</p>'
        else:
            out += '<strong class="unresolved-text">Not yet resolved</strong><p class="pick-caption">See the research trail.</p>'
        out += '</td><td class="basis-cell" data-label="Basis &amp; sources">'
        out += badge({'market': 'Market-backed', 'bookmaker': 'Bookmaker line', 'model': 'Research model', 'unresolved': 'Unresolved'}[method], {'market': 'green', 'bookmaker': 'green', 'model': 'purple', 'unresolved': 'amber'}[method])
        out += '<div class="row-source-links">' + external(m['source_url'], 'Hotspawn')
        if a:
            out += external(a['source_url'], 'Market' if method == 'market' else 'Valve' if method == 'model' else 'Bookmaker')
        out += '</div>' + evidence(m, prefix) + '</td></tr>'
    out += '</tbody></table><p id="filter-empty" class="empty-state" hidden>No matches fit these filters. <button type="button" class="text-button" data-reset>Clear filters</button></p></div>' if filters else '</tbody></table></div>'
    return out


def unresolved_table(data, prefix):
    rows = [m for m in data['matches'] if m['availability'] in {'open', 'locked', 'unknown_lock'} and m['analysis'] is None]
    if not rows:
        return '<p class="positive-note">Every future-start fixture in this snapshot has a supported probability estimate. Research estimates still carry the limitations below.</p>'
    out = '<div class="table-scroll"><table class="simple-table unresolved-table"><caption class="sr-only">Every unresolved future match and the missing evidence</caption><thead><tr><th scope="col">Match</th><th scope="col">Why no pick?</th><th scope="col">Review</th></tr></thead><tbody>'
    for m in rows:
        reason = next((r['detail'] for r in reversed(m['research']) if r['status'] == 'unresolved'), 'No verified inputs are available')
        out += f'<tr><th scope="row">{e(match_name(m))}<small>{local_time(m["starts_at"])}</small></th><td>{e(reason)}<p class="tiny">Primary market, HLTV and original esportsbook checks did not produce an accepted series line. Missing probabilities remain blank.</p></td><td>{external(m["source_url"], "Hotspawn source")}<a class="internal-link" href="{prefix}picks/#match-{e(m["id"])}">Full research trail →</a></td></tr>'
    return out + '</tbody></table></div>'


def summary(data, prefix):
    c = data['counts']
    active = [m for m in data['matches'] if m['availability'] in {'open', 'locked', 'unknown_lock'}]
    p = round(100 * (c['upcoming'] - c['unresolved']) / c['upcoming']) if c['upcoming'] else 0
    ring = f'<div class="coverage-dial"><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="50" class="dial-track"/><circle cx="60" cy="60" r="50" class="dial-progress" stroke-dasharray="{p * 3.14159:.3f} 314.159"/></svg><div><strong>{c["upcoming"] - c["unresolved"]}<span>/{c["upcoming"]}</span></strong><small>with probabilities</small></div></div>'
    out = heading('Counter-Strike 2 intelligence', 'The matchday briefing.', 'Every Hotspawn CS2 fixture, independently researched. Your picks are one tap away.')
    out += f'<section class="hero" aria-labelledby="briefing-title"><div class="hero-copy"><span class="hero-kicker"><span class="status-dot"></span>{"FULL INVENTORY RECONCILED" if data["coverage_complete"] else "INVENTORY NOT VERIFIED"}</span><h2 id="briefing-title">All the matches.<br>One clear view.</h2><p><strong>{c["upcoming"]} future matches.</strong> {c["market"] + c["bookmaker"]} market-backed estimates, {c["model"]} research estimates, and {c["unresolved"]} unresolved. No Hotspawn popularity scores. No made-up odds.</p><div class="hero-actions"><a class="button primary" href="{prefix}picks/">See all match picks {icon("arrow")}</a><a class="hero-secondary" href="#unresolved">Unresolved &amp; limitations ↓</a></div></div>{ring}</section>'
    out += '<div class="metrics">'
    cards = [('Future matches', c['upcoming'], f'{c["inventory"]} source records · {c["archived"]} past starts', 'target', 'coverage/'), ('Market-backed', c['market'] + c['bookmaker'], 'Original external market observations', 'layers', 'picks/?basis=market'), ('Research estimates', c['model'], 'Valve ratings · higher uncertainty', 'book', 'picks/?basis=model'), ('Unresolved picks', c['unresolved'], 'Missing inputs stay blank', 'flag', 'review/#unresolved')]
    for title, value, subtitle, sym, url in cards:
        out += f'<a class="metric-card" href="{prefix}{url}"><div class="metric-top"><span>{title}</span>{icon(sym)}</div><strong>{value:02d}</strong><p>{e(subtitle)}</p></a>'
    out += '</div>'
    out += '<section class="content-section"><div class="section-heading"><div><p class="eyebrow">The short version</p><h2>What to know before you pick</h2></div>' + badge('Read-only analysis', 'neutral') + '</div><div class="briefing-notes">'
    out += f'<div><span class="note-number">01</span><p><strong>Start with the full picks list.</strong> Both team probabilities, the suggested team, lock time and original evidence are shown together. {external(LOBBY, "Submit picks on Hotspawn")}</p></div><div><span class="note-number">02</span><p><strong>Know what backs the number.</strong> Green means an external market; purple means an uncalibrated rating model used only when the primary method failed. Neither is a guarantee.</p></div><div><span class="note-number">03</span><p><strong>Check the timestamp.</strong> Automatic checks are scheduled every four hours. GitHub may delay a run. After eight hours without a successful observation, the site warns you not to treat the snapshot as current.</p></div></div></section>'
    out += '<section class="content-section"><div class="section-heading"><div><p class="eyebrow">On the radar</p><h2>Next matches</h2></div><a class="internal-link" href="' + prefix + 'picks/">All match picks ' + icon('arrow') + '</a></div>'
    out += matches_table(active[:5], prefix, table_id='next-matches') + '</section>'
    out += '<section class="content-section" id="unresolved"><div class="section-heading"><div><p class="eyebrow amber-text">Coverage gaps, not hidden omissions</p><h2>Unresolved picks &amp; limitations</h2></div><a class="internal-link" href="' + prefix + 'review/">All review flags ' + icon('arrow') + '</a></div>'
    out += unresolved_table(data, prefix)
    out += f'<div class="limitations-callout"><strong>What the numbers cannot confirm</strong><p>HLTV or bookmakers can block unattended access. Provider team names can differ. Rating snapshots do not confirm today’s lineup or map vetoes. {c["archived"]} past-start Hotspawn records are preserved separately, not sold as current picks. Unverified best-of formats and source status conflicts are listed for review.</p><div class="inline-links"><a href="{prefix}coverage/">Coverage &amp; source status →</a><a href="{prefix}methodology/">How probabilities are calculated →</a><a href="{prefix}review/">Flagged for Review →</a></div></div></section>'
    return out


def picks(data, prefix):
    c = data['counts']
    active = [m for m in data['matches'] if m['availability'] in {'open', 'locked', 'unknown_lock'}]
    out = heading('The complete future-match list', 'Match picks & probabilities', 'See both sides. Know the pick. Check the evidence. Full-series estimates only; no map, handicap or popularity-derived lines.', '<a class="button secondary" href="' + prefix + 'data/picks.csv">Download CSV ↓</a>')
    out += '<div class="info-strip">' + icon('clock') + '<span>Snapshot observed ' + local_time(data.get('inventory_observed_at')) + '. Lock times come from each Hotspawn fixture. Picks are not submitted automatically.</span></div>'
    out += '<section class="content-section picks-section" aria-label="Searchable match list"><div class="filter-bar"><label class="search-box">' + icon('search') + '<span class="sr-only">Search teams or tournaments</span><input id="match-search" type="search" placeholder="Search teams or tournaments…" autocomplete="off"></label><label class="select-field"><span>Tournament</span><select id="tournament-filter"><option value="all">All tournaments</option>'
    for tournament in sorted(set(m['competition'] or 'Unverified tournament' for m in active)):
        out += f'<option value="{e(tournament)}">{e(tournament)}</option>'
    out += '</select></label><label class="select-field"><span>Sort by</span><select id="match-sort"><option value="start">Soonest first</option><option value="confidence">Highest estimated chance</option><option value="team">Team name</option></select></label></div><div class="filter-second"><div class="filter-tabs" role="group" aria-label="Probability basis">'
    for value, label, count in [('all', 'All matches', c['upcoming']), ('market', 'Market-backed', c['market'] + c['bookmaker']), ('model', 'Research', c['model']), ('unresolved', 'Unresolved', c['unresolved'])]:
        out += f'<button type="button" data-basis="{value}" aria-pressed="{"true" if value == "all" else "false"}">{label}<span>{count}</span></button>'
    out += f'</div><p id="filter-count" aria-live="polite">{len(active)} matches</p></div><noscript><p class="limitations-callout">JavaScript is off. Every row and source remains visible; interactive search and live freshness checks are unavailable.</p></noscript>'
    out += matches_table(active, prefix, filters=True) + '</section><div class="legend"><span>' + badge('Market-backed', 'green') + ' Independent external prices</span><span>' + badge('Research model', 'purple') + ' Uncalibrated rating estimate</span><span>' + badge('Unresolved', 'amber') + ' No supported probability</span></div>'
    out += f'<p class="muted small">Showing future-start fixtures at the last inventory check. Past-start records remain available in the <a href="{prefix}coverage/#archive">complete source archive</a>. Fair decimal lines are calculated in each row’s evidence panel; they are not executable bookmaker quotes.</p>'
    return out


def coverage(data, prefix):
    c = data['counts']
    out = heading('Nothing quietly left out', 'Coverage & original sources', 'Inventory coverage and probability coverage are different. This page reconciles both, and keeps past-start source anomalies visible.')
    out += f'<div class="coverage-summary"><div><span class="eyebrow">Source inventory</span><strong>{c["inventory"]} / {c["inventory"] if data["coverage_complete"] else "?"}</strong><p>{"CS2 records reconciled across three official responses" if data["coverage_complete"] else "Complete current coverage is unverified"}</p></div><div><span class="eyebrow">Future probabilities</span><strong>{c["upcoming"] - c["unresolved"]} / {c["upcoming"]}</strong><p>{c["market"] + c["bookmaker"]} market · {c["model"]} model · {c["unresolved"]} unresolved</p></div><div><span class="eyebrow">Automatic refresh</span><strong>4 hours</strong><p>Scheduled at 00:17, 04:17, 08:17, 12:17, 16:17, 20:17 UTC. Not a real-time feed.</p></div></div>'
    out += '<section class="content-section"><div class="section-heading"><div><p class="eyebrow">First-party checks</p><h2>Source health</h2></div><a class="internal-link" href="' + prefix + 'data/sources.json">Request manifest ↓</a></div><div class="table-scroll"><table class="simple-table source-table"><caption class="sr-only">Latest source attempts, outcomes and limitations</caption><thead><tr><th>Original source</th><th>Status / observed</th><th>What was actually confirmed</th></tr></thead><tbody>'
    for s in data['sources']:
        out += '<tr><th scope="row">' + external(s['url'], s['name']) + '</th><td>' + badge('Available' if s['status'] == 'ok' else 'Limited / unavailable', 'green' if s['status'] == 'ok' else 'amber') + '<small>' + local_time(s['observed_at']) + '</small></td><td>' + e(s['detail']) + (f'<small>{s["records"]} structured records</small>' if s['records'] is not None else '') + '</td></tr>'
    out += '</tbody></table></div></section><section class="content-section"><div class="section-heading"><div><p class="eyebrow">Reproducible, not just plausible</p><h2>Verification ledger</h2></div></div><div class="table-scroll"><table class="simple-table"><caption class="sr-only">Automated inventory and calculation verification</caption><thead><tr><th>Check</th><th>Published result</th><th>Original source / evidence</th></tr></thead><tbody>'
    ledger = [('Fixture identity reconciliation', f'{c["inventory"]} unique CS2 IDs. Both lobby payloads and the unpaginated official fixture array are compared.', 'https://play.hotspawn.com/cs2-pickems', 'Hotspawn CS2 lobby'), ('Line-by-line facts', 'Every match ID, team, competition, schedule, explicit lock, format and source status is replayed against saved source JSON.', 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1', 'Original fixture API'), ('Probability calculations', 'Every output probability, fair line and selected team is recalculated. Unknown inputs cannot become a pick.', 'https://docs.polymarket.com/api-reference/market-data/get-order-book', 'Official order book contract'), ('Rating input integrity', 'Model points and rosters are reparsed from original Valve markdown and checked against its Git blob SHA.', 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'Valve official repository')]
    for title, detail, url, label in ledger:
        out += f'<tr><th scope="row">{e(title)}</th><td>{e(detail)}</td><td>{external(url, label)}</td></tr>'
    out += '</tbody></table></div><div class="inline-links downloads"><a href="' + prefix + 'data/latest.json">Full snapshot JSON ↓</a><a href="' + prefix + 'data/evidence/hotspawn-context.json">Inventory reconciliation ↓</a><a href="' + prefix + 'data/picks.csv">Picks CSV ↓</a></div></section>'
    out += f'<section class="content-section" id="archive"><div class="section-heading"><div><p class="eyebrow">Preserved, not misrepresented</p><h2>Past-start source archive <span class="heading-count">{c["archived"]}</span></h2></div></div><p class="section-intro">These records still exist in Hotspawn’s scheduled feed, but their scheduled starts are in the past. “Scheduled” is the source’s value, not a verified present status. Results, current picks and retrospective probabilities are not invented.</p><div class="table-scroll"><table class="simple-table archive-table"><caption class="sr-only">Every past-start CS2 record retained from the original Hotspawn feed</caption><thead><tr><th>Match / tournament</th><th>Scheduled start</th><th>Source status</th><th>Original source</th></tr></thead><tbody>'
    for m in data['matches']:
        if m['availability'] != 'past':
            continue
        out += f'<tr><th scope="row">{e(match_name(m))}<small>{e(m["competition"] or "Unverified tournament")} · ID {e(m["id"])}</small></th><td>{local_time(m["starts_at"])}</td><td>{e(m["source_status"] or "")}<small>Current result/status unverified</small></td><td>{external(m["source_url"], "Hotspawn source")}</td></tr>'
    out += '</tbody></table></div></section>'
    unknown = [m for m in data['matches'] if m['availability'] == 'unknown']
    if unknown:
        out += '<section class="content-section"><h2>Unverified schedules</h2>' + matches_table(unknown, prefix, table_id='unknown-schedules') + '</section>'
    return out


def methodology(data, prefix):
    out = heading('A number needs a reason', 'How we resolve a pick', 'Source facts stay separate from analysis. No Hotspawn community percentage, popularity, score or Pick’em point multiplier enters a probability calculation.')
    steps = [('01', 'Verify the full match inventory', 'Read the public lobby, CS2 lobby and the same public fixture array used by Hotspawn’s client. Reconcile every CS2 ID. Keep old or inconsistent records in the archive rather than dropping them.', LOBBY, 'Official lobby'), ('02', 'Use the primary external market', 'Discover CS2 games from Polymarket’s own directory. Confirm the event, exact two team names, start time within 60 seconds, unique active series moneyline, accepting-orders state, token IDs and condition ID. Read both original order books. No map or handicap markets.', 'https://docs.polymarket.com/api-reference/market-data/get-order-book', 'Official order book documentation'), ('03', 'Research only primary-method gaps', 'For those matches only, try HLTV’s official match directory, then original esportsbook lines. Thunderpick has a paired-price adapter; GG.BET, Pinnacle and Rivalry are public-access checks and do not fabricate prices if a validated contract is unavailable. HTTP 403, redirects and schema failures are visible limitations—not proof of no market.', 'https://www.hltv.org/matches', 'HLTV official match directory'), ('04', 'Model only supported rating inputs—or leave blank', 'If no accepted external line exists, read the latest official global Valve snapshot on or before today. Require exactly one matching team name and a complete five-player roster for each team. Reject ambiguous names, missing teams and snapshots older than 35 days. Otherwise publish an explicitly uncalibrated rating estimate. If any requirement fails, publish the match as unresolved.', 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'Valve official standings')]
    out += '<section class="content-section resolution-steps">'
    for n, title, description, url, label in steps:
        out += f'<article class="resolution-step"><span>{n}</span><div><h2>{title}</h2><p>{e(description)}</p>{external(url, label)}</div></article>'
    out += '</section><section class="content-section prose"><p class="eyebrow">Our calculations, not source facts</p><h2>From observations to percentages</h2><h3>Prediction-market estimate</h3><p>For each outcome, take the best positive-size bid and ask from its own book. The midpoint is <code>m = (best bid + best ask) / 2</code>. Normalize the paired midpoints with <code>P(A) = mA / (mA + mB)</code> and <code>P(B) = 1 − P(A)</code>. Require valid two-sided books, a spread of no more than 12 cents per outcome, matching token/condition IDs, and source timestamps no older than eight hours. Directory percentages and Gamma’s last-price defaults are not used.</p><p>These are indicative midpoints, not guaranteed execution quotes or “true” win probabilities. Trading fees, slippage and position size are excluded. A single prediction market is not independent bookmaker consensus. ' + external('https://docs.polymarket.com/api-reference/market-data/get-order-book', 'Inspect the official book schema') + '</p><h3>Original bookmaker estimate</h3><p>For a verified pair of decimal odds <code>dA, dB</code>, calculate <code>qA = 1/dA</code>, <code>qB = 1/dB</code>, then remove proportional margin with <code>P(A) = qA / (qA + qB)</code>. Only active, two-outcome, prematch match-winner lines are accepted. Implied-probability sums outside 0.85–1.35 are rejected as a data-quality policy. Different mirrors of one book count as one source family; independent families, if present, are combined using the median normalized probability.</p><h3>Valve-rating research estimate</h3><p>The published Valve model uses a Glicko-style expected score. We implement <code>g = 1 / √(1 + 3(ln(10)/400)² × RD² / π²)</code> and <code>P(A) = 1 / (1 + 10^(g × (RB − RA) / 400))</code>. Points <code>RA, RB</code> are sourced facts; <code>RD = 75</code> is a fixed assumption following Valve’s fit example, not a measured uncertainty for today’s roster.</p><p>' + external('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/fit.js', 'Valve fit example') + ' ' + external('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/glicko.js', 'Valve expected-score implementation') + '</p><div class="limitations-callout"><strong>Important model limitations</strong><p>This deployment has not been backtested or calibrated. A historic name-matched roster is not proof of today’s lineup. Stand-ins, roster changes, map vetoes, team form since the snapshot and bookmaker information are not added without verification. This model does not override a valid primary market pick and is never labeled a verified betting line.</p></div><h3>Our fair line and the pick</h3><p>The fair decimal line is <code>1/P</code>; it is a calculated reference, not odds offered by any bookmaker. The suggested team has the higher unrounded probability. An exactly equal estimate has no directional pick. Missing data is not replaced with 50/50. Displayed percentages are rounded to one decimal place; the downloadable data retains higher precision.</p></section>'
    out += '<section class="content-section prose"><p class="eyebrow">Operational boundaries</p><h2>Freshness, identity &amp; blank values</h2><ul><li>Refreshes are scheduled every four hours in UTC. GitHub Actions schedules are best-effort, not a real-time service-level guarantee.</li><li>The inventory observation time, price observation time, source book timestamp and rating snapshot date remain distinct. A failed refresh never resets successful-observation timestamps.</li><li>After eight hours, the browser displays a stale warning and disables “current pick” language. After a fixture’s explicit lock time, it is labeled closed for picks. A past scheduled start is not treated as a verified final result.</li><li>Matching is Unicode/case/whitespace-equivalent exact naming plus start time within 60 seconds. Abbreviations, sponsor aliases and fuzzy matches are not guessed. Duplicate Valve names are rejected, even when one looks more likely.</li><li>Unverified factual values remain blank and labeled “unverified.” Calculated probabilities and fair lines are visibly identified as analysis; they are not filled-in source facts.</li><li>Access controls, robots restrictions and challenges are not bypassed. No login, paid API key, user input or betting account is required for this read-only dashboard.</li><li>Every published probability is replayed from saved first-party evidence before deployment. Every match row links back to Hotspawn; pricing and model inputs carry their own original-source links.</li></ul><p>' + external('https://play.hotspawn.com/how-it-works', 'Hotspawn rules for manual review') + f' · <a href="{prefix}review/">See all flagged limitations →</a></p></section>'
    return out


def review(data, prefix):
    out = heading('Transparent by design', 'Flagged for Review', 'Unresolved matches, blocked sources and inconsistent official fields are published here. They do not block publication; they do block unsupported claims.')
    out += '<section class="content-section" id="unresolved"><div class="section-heading"><div><p class="eyebrow amber-text">No evidence, no invented pick</p><h2>Unresolved future matches</h2></div></div>' + unresolved_table(data, prefix) + '</section>'
    out += '<section class="content-section"><div class="section-heading"><div><p class="eyebrow">Research &amp; integrity register</p><h2>All findings</h2></div><span class="muted small">Source-linked, not silently corrected</span></div><div class="table-scroll"><table class="simple-table review-table"><caption class="sr-only">Source-linked irregularities and analysis limitations</caption><thead><tr><th>Finding</th><th>Limitation / handling</th><th>Original sources</th></tr></thead><tbody>'
    for f in data['flags']:
        out += f'<tr id="flag-{e(f["id"])}"><th scope="row">{badge("Notice" if f["severity"] == "notice" else "Needs review", "purple" if f["severity"] == "notice" else "amber")}<strong>{e(f["title"])}</strong>' + (f'<small>{len(f["match_ids"])} affected source records</small>' if f['match_ids'] else '') + f'</th><td>{e(f["detail"])}</td><td><div class="evidence-links">'
        for i, url in enumerate(dict.fromkeys(f['source_urls'])):
            label = 'Hotspawn' if 'hotspawn' in url or 'cloudwaysapps' in url else 'Valve' if 'ValveSoftware' in url else 'Polymarket' if 'polymarket' in url else 'HLTV' if 'hltv.org' in url else urlparse_host(url)
            out += external(url, label)
        out += '</div></td></tr>'
    return out + '</tbody></table></div></section>'


def urlparse_host(url):
    from urllib.parse import urlparse
    return urlparse(url).netloc


def shell(data, key, body, prefix):
    title = PAGES[key][0]
    nav = ''
    for k, (label, path, sym) in PAGES.items():
        href = prefix + ('' if k == 'summary' else k + '/')
        if k == 'summary':
            href = prefix + 'index.html'
        nav += f'<a class="nav-link {"active" if k == key else ""}" href="{href}"' + (' aria-current="page"' if k == key else '') + f'>{icon(sym)}<span>{label}</span>' + (f'<span class="nav-count">{len(data["flags"])}</span>' if k == 'review' else '') + '</a>'
    mobile = ''.join(f'<a href="{prefix + "index.html" if k == "summary" else prefix + k + "/"}"' + (' aria-current="page"' if key == k else '') + f'>{icon(PAGES[k][2])}<span>{label}</span></a>' for k, label in [('summary', 'Summary'), ('picks', 'Picks'), ('coverage', 'Coverage'), ('review', 'Review')])
    inventory = data.get('inventory_observed_at') or ''
    stale = not data['coverage_complete'] or not is_fresh(inventory, datetime.now(timezone.utc))
    freshness = 'Snapshot needs attention' if stale else 'Source snapshot available'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)} · Spawn Scout</title><meta name="description" content="Every Hotspawn CS2 match, independent probabilities, clear picks and original evidence. Mobile-friendly, read-only analysis with visible coverage gaps."><meta name="theme-color" content="#142534"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'"><link rel="icon" href="{prefix}assets/scout-mark.svg" type="image/svg+xml"><link rel="stylesheet" href="{prefix}assets/scout.css"><script src="{prefix}assets/scout.js" defer></script></head>
<body data-page="{key}" data-inventory-time="{e(inventory)}" data-inventory-complete="{str(data['coverage_complete']).lower()}" data-snapshot-generated="{e(data['generated_at'])}" data-data-url="{prefix}data/latest.json"><a class="skip-link" href="#main">Skip to content</a>
<aside class="sidebar"><a class="brand" href="{prefix}index.html" aria-label="Spawn Scout home"><span class="brand-mark"><svg viewBox="0 0 28 28" aria-hidden="true"><path d="M5 4h9v9H5zM17 4h7v7h-7zM5 16h7v8H5z"/><path d="m16 17 8-4v11h-8z"/></svg></span><span>spawn<span class="brand-light">scout</span><small>CS2 MATCH INTELLIGENCE</small></span></a><p class="nav-label">YOUR DASHBOARD</p><nav aria-label="Main navigation">{nav}</nav><div class="sidebar-bottom"><div class="sidebar-note"><span class="status-dot"></span><strong>Independent analysis</strong><p>Hotspawn tells us who plays.<br>External sources inform the pick.</p></div>{external(LOBBY, 'Open Hotspawn lobby', 'sidebar-external')}<a class="sidebar-repo" href="{REPO}">Open-source &amp; auditable {icon('external')}</a></div></aside>
<div class="workspace"><header class="topbar"><div class="mobile-brand"><a href="{prefix}index.html">spawn<strong>scout</strong><span>CS2</span></a></div><div class="desktop-crumb">Workspace <span>/</span> <strong>{e(title)}</strong></div><div class="topbar-tools"><span class="refresh-pill">{icon('clock')} Checks every 4h</span><label class="timezone-control"><span class="sr-only">Display timezone</span><select id="timezone"><option value="Europe/Malta">Malta time</option><option value="UTC">UTC</option><option value="local">Device time</option></select></label></div></header>
<main id="main" tabindex="-1"><div class="snapshot-line"><span class="freshness-label" data-freshness><span class="status-dot"></span>{freshness}</span><span>Inventory checked {local_time(data.get('inventory_observed_at'))} <span data-zone-label>Malta</span></span></div><div id="stale-warning" class="stale-warning" role="status" {'' if stale else 'hidden'}><strong>Do not treat these as current picks.</strong> The inventory check failed or the successful snapshot is older than eight hours. Original timestamps are preserved. <a href="{prefix}coverage/">Check source status →</a></div><div id="new-snapshot" class="new-snapshot" hidden>A newer verified snapshot is available. <button type="button" id="load-update">Load updated picks →</button></div>{body}<footer class="footer"><div><strong>Better context. Clearer picks.</strong><p>Independent Hotspawn CS2 research · Not affiliated with Hotspawn, HLTV, Valve or any betting provider.</p><p>Estimates, not guarantees. No bets or picks are placed. Informational use only. 18+ where applicable.</p></div><div><a href="{prefix}methodology/">Methodology</a><a href="{prefix}review/">Flagged for Review</a><a href="{prefix}data/latest.json">Open data ↓</a><span class="tiny muted">Built {local_time(data['generated_at'])}</span></div></footer></main></div><nav class="mobile-nav" aria-label="Mobile navigation">{mobile}</nav></body></html>'''


def build(source: Path, output: Path):
    data = check_data(source)
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'assets').resolve() != Path('assets').resolve():
        shutil.copytree('assets', output / 'assets', dirs_exist_ok=True)
    if (output / 'data').resolve() != source.resolve():
        shutil.copytree(source, output / 'data', dirs_exist_ok=True)
    (output / '.nojekyll').touch()
    renderers = {'summary': summary, 'picks': picks, 'coverage': coverage, 'methodology': methodology, 'review': review}
    for key, (_, path, _) in PAGES.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        prefix = './' if key == 'summary' else '../'
        target.write_text(shell(data, key, renderers[key](data, prefix), prefix))
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['hotspawn_id', 'team_a', 'team_b', 'starts_at_utc', 'locks_at_utc', 'source_status', 'availability_at_snapshot', 'team_a_probability_calculated', 'team_b_probability_calculated', 'suggested_team', 'basis', 'price_or_model_observed_at', 'rating_snapshot_date', 'original_hotspawn_source', 'analysis_source'])
    for m in data['matches']:
        a = m['analysis']
        # Defend downloads against formula injection in source-controlled team names.
        safe = lambda x: ("'" + str(x)) if str(x).startswith(('=', '+', '-', '@')) else x
        writer.writerow([safe(x) for x in [m['id'], m['teams'][0]['name'] or '', m['teams'][1]['name'] or '', m['starts_at'] or '', m['locks_at'] or '', m['source_status'] or '', m['availability'], a['probabilities'][0] if a else '', a['probabilities'][1] if a else '', m['teams'][m['pick_index']]['name'] if m['pick_index'] is not None else '', a['method'] if a else '', a['observed_at'] if a else '', a.get('snapshot_date', '') if a else '', m['source_url'], a['source_url'] if a else '']])
    (output / 'data/picks.csv').write_text(stream.getvalue())
    check_links(output)
    print(f'Built five source-linked Pages views in {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('site'))
    args = parser.parse_args()
    build(args.data, args.output)
