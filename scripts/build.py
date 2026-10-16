"""Build accessible, dependency-light static Pages subpages from verified JSON."""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.domain import timestamp, is_fresh
from scripts.validate import check_data, check_links
from scripts.contrarian import derive_context, load_review, validate_context
from scripts.briefing import render as contrarian_briefing, review_note, audit_register

REPO = 'https://github.com/buffedlizard55-lab/MaltaProj3'
LOBBY = 'https://play.hotspawn.com/lobby'
# Overridable by build() so the executive summary links the review that ships
# with this exact data directory.
EDGE_SOURCE = Path('data/edge-review.json')
PAGES = {'summary': ('Executive summary', 'index.html', 'overview'), 'picks': ('Match picks', 'picks/index.html', 'target'), 'edge': ('Upset review & edge', 'edge/index.html', 'trend'), 'twc': ('TWC Day 3 picks', 'twc-picks/index.html', 'target'), 'coverage': ('Coverage & sources', 'coverage/index.html', 'layers'), 'methodology': ('Methodology', 'methodology/index.html', 'book'), 'review': ('Flagged for Review', 'review/index.html', 'flag')}
ICONS = {
    'overview': '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    'target': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    'layers': '<path d="m12 3 10 5-10 5L2 8l10-5Z"/><path d="m2 12 10 5 10-5M2 16l10 5 10-5"/>',
    'book': '<path d="M12 5v16M3 3h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5v16h-5a4 4 0 0 0-4 2 4 4 0 0 0-4-2H3V3Z"/>',
    'flag': '<path d="M5 21V3h8l1 3h6v10h-7l-1-3H5"/>',
    'arrow': '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    'external': '<path d="M14 3h7v7m0-7L10 14M10 3H4a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-6"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'trend': '<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
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


def evidence(m, prefix, fallback=None):
    a = m['analysis']
    body = '<div class="evidence-box"><p class="eyebrow">Source observations</p><dl class="fact-list">'
    for label, value in [('Hotspawn status', e(m['source_status']) if m['source_status'] else blank()), ('Scheduled start', local_time(m['starts_at'])), ('Pick lock', local_time(m['locks_at'])), ('Best of (Hotspawn)', e(m['best_of']) if m['best_of'] is not None else blank()), ('Inventory observed', local_time(m['observed_at']))]:
        body += f'<div><dt>{label}</dt><dd>{value}</dd></div>'
    body += '</dl><div class="evidence-links">' + external(m['source_url'], 'Hotspawn match') + external(m['source_api'], 'Original fixture API') + f'<a href="{prefix}data/evidence/hotspawn-fixtures.json">Saved fixture evidence ↓</a></div>'
    if a:
        body += f'<h4>{"Featured model reference (replaced below) · " if fallback and fallback.get("upgraded_from_featured_model") else ""}{e(a["label"])}</h4><p>Observed {local_time(a["observed_at"])}. Calculated fair lines: <strong>{e(a["fair_decimal"][0])} / {e(a["fair_decimal"][1])}</strong> (not quoted bookmaker odds).</p>'
        if a['method'] == 'market':
            body += '<div class="mini-table-wrap"><table class="mini-table"><caption>Original bid/ask observations</caption><thead><tr><th>Team</th><th>Bid / ask</th><th>Source</th></tr></thead><tbody>'
            for t, q in zip(m['teams'], a['quotes']):
                body += f'<tr><th scope="row">{e(t["name"])}</th><td>{q["bid"]:.3f} / {q["ask"]:.3f}</td><td>{external(a["source_api"], "Polymarket API")}</td></tr>'
            body += '</tbody></table></div>'
            body += '<div class="evidence-links">' + ''.join(f'<a href="{prefix}data/evidence/polymarket-{kind}-{a["event_id"]}{suffix}.json">{label} ↓</a>' for kind, suffix, label in [('event', '', 'Saved event'), ('book', '-0', 'First order book'), ('book', '-1', 'Second order book')]) + '</div>'
        elif a['method'] == 'model':
            body += f'<p>Rating snapshot: <strong>{e(a["snapshot_date"])}</strong>. Roster lists below belong to that snapshot, not a confirmed current lineup.</p><div class="mini-table-wrap"><table class="mini-table"><caption>Published model inputs</caption><thead><tr><th>Team</th><th>Points</th><th>Source</th></tr></thead><tbody>'
            for r in a['inputs']:
                body += f'<tr><th scope="row">{e(r["name"])}</th><td>{r["points"]}</td><td>{external(r["source_url"], "Valve")}</td></tr>'
            body += '</tbody></table></div>'
            for r in a['inputs']:
                body += f'<p class="tiny"><strong>{e(r["name"])}</strong>: {e(", ".join(r["roster"]))}</p>'
            body += f'<div class="evidence-links"><a href="{prefix}data/evidence/valve-standings-response.json">Original Valve response ↓</a><a href="{prefix}data/evidence/valve-ratings.json">Parsed official inputs ↓</a></div>'
        elif a['method'] == 'bookmaker':
            for q in a['quotes']:
                body += f'<p>Quoted decimal odds: {e(q["odds"][0])} / {e(q["odds"][1])}. {external(q["source_url"], q["provider"])}</p>'
                body += f'<p>Original event ID: <strong>{e(q["event_id"])}</strong>. Source uses a read-only POST with <code>{{"gameIds":[6]}}</code>; opening that endpoint as a browser GET does not reproduce the recorded request.</p><div class="evidence-links"><a href="{prefix}data/evidence/thunderpick-matches.json">Saved original bookmaker response ↓</a><a href="{prefix}data/sources.json">Request method &amp; payload ↓</a></div>'
        body += '<ul class="limitations">' + ''.join(f'<li>{e(x)}</li>' for x in a['limitations']) + '</ul>' + external(a['source_url'], a['source'])
    if fallback and fallback.get('origination') and (not a or fallback.get('upgraded_from_featured_model')):
        o = fallback['origination']
        body += (f'<h4>Researched fallback · {e(o.get("label") or o["method"])}</h4>'
                 f'<p>Observed {local_time(o["observed_at"])}. Calculated fair lines: '
                 f'<strong>{e(o["fair_decimal"][0])} / {e(o["fair_decimal"][1])}</strong> (not quoted bookmaker odds). '
                 'The featured exact-name method rejected this fixture; this estimate comes from the audited research '
                 'ladder and never overwrites a featured value.</p>')
        for q in o.get('quotes') or []:
            facts = []
            odds, bid, ask = q.get('odds'), q.get('bid'), q.get('ask')
            if odds:
                facts.append(f'decimal odds {e(odds[0])} / {e(odds[1])}')
            if bid and ask:
                facts.append(f'bid/ask {bid[0]:.3f}/{ask[0]:.3f} vs {bid[1]:.3f}/{ask[1]:.3f}')
            if not facts:
                facts.append('price observation recorded in the saved evidence')
            body += (f'<p>{e(q.get("provider") or "Provider")} ({e(q.get("family") or "source")}): '
                     + ' · '.join(facts)
                     + f'. Original event ID: <strong>{e(q.get("event_id") or "unverified")}</strong>. '
                     + external(q.get('source_url') or o['source_url'], (q.get('provider') or 'Provider') + ' record') + '</p>')
        for r in o.get('inputs') or []:
            body += (f'<p class="tiny">Valve rating input: <strong>{e(r["name"])}</strong> {e(r["points"])} points, '
                     f'snapshot {e(r.get("snapshot_date") or "unverified")}, roster {e(", ".join(r.get("roster") or []))}. '
                     + (external(r.get('source_url') or o.get('source_url'), 'Valve record') if (r.get('source_url') or o.get('source_url')) else '<span class="unverified">source link unverified</span>') + '</p>')
        aliases = fallback.get('aliases_used') or []
        if aliases:
            body += ('<p class="tiny"><strong>Identity joins</strong>: '
                     + e('; '.join(f'{a_["alias"]} → {a_["canonical"]} ({a_["kind"]})' for a_ in aliases))
                     + '. Each join carries its own official evidence links in the '
                     f'<a href="{prefix}origination/#aliases">alias registry</a>.</p>')
        if o.get('limitations'):
            body += '<ul class="limitations">' + ''.join(f'<li>{e(x)}</li>' for x in o['limitations']) + '</ul>'
        body += external(o['source_url'], o.get('source') or 'Research source')
        body += (f'<div class="evidence-links"><a href="{prefix}origination/#match-{e(m["id"])}">'
                 'Full researched audit trail →</a></div>')
    if m['research']:
        if any(r['stage'].startswith('HLTV') and r['status'] != 'unavailable' for r in m['research']):
            body += '<div class="evidence-links"><a href="' + prefix + 'data/evidence/hltv-page.json">Original HLTV markup ↓</a><a href="' + prefix + 'data/evidence/hltv-research.json">Replayed HLTV identities ↓</a></div>'
        body += '<h4>Resolution trail</h4><ol class="research-trail">'
        for r in m['research']:
            body += f'<li><strong>{e(r["stage"])}</strong> · {e(r["status"])}<p>{e(r["detail"])}</p>{external(r["source_url"], "Original source")}</li>'
        body += '</ol>'
    body += '</div>'
    return f'<details class="row-details"><summary>Evidence &amp; analysis <span aria-hidden="true">+</span></summary>{body}</details>'


def matches_table(matches, prefix, *, table_id='match-list', filters=False, fallbacks=None):
    fallbacks = fallbacks or {}
    if not matches:
        return '<div class="empty-state">No verified future fixtures in this snapshot. Check the <a href="' + prefix + 'coverage/">source status</a> before assuming there are no matches.</div>'
    out = f'<div class="matches-wrap"><table class="matches-table" id="{table_id}"><caption class="sr-only">Hotspawn CS2 match picks. Percentages are calculated estimates, never guaranteed outcomes. Times are Europe/Malta unless changed.</caption><thead><tr><th scope="col">Match &amp; start</th><th scope="col">Win probabilities</th><th scope="col">Our pick</th><th scope="col">Basis &amp; verification</th></tr></thead><tbody>'
    now = datetime.now(timezone.utc)
    for m in matches:
        a, pick = m['analysis'], m['pick_index']
        fallback = selected_fallback(m, fallbacks)
        fb = (fallback or {}).get('origination')
        if fb:
            a, pick = fb, fallback.get('pick_index')
            researched = True
        else:
            researched = False
        method = a['method'] if a else 'unresolved'
        names = [t['name'] or 'Unverified team' for t in m['teams']]
        confidence = max(a['probabilities']) if a else 0
        search = ' '.join(names + [m['competition'] or '', method, 'researched fallback' if researched else '']).casefold()
        out += f'<tr id="match-{e(m["id"])}" class="match-row" data-record-id="{e(m["id"])}" data-search="{e(search)}" data-method="{method}" data-tournament="{e(m["competition"] or "Unverified tournament")}" data-confidence="{confidence}" data-start="{e(m["starts_at"] or "")}" data-lock="{e(m["locks_at"] or "")}" data-price-time="{e(a["observed_at"] if a else "")}" data-researched-fallback="{str(researched).lower()}">'
        tier = ('Tier ' + str(m['tier']).upper()) if m['tier'] else 'Tier unverified'
        start_time, lock_time = timestamp(m['starts_at']), timestamp(m['locks_at'])
        availability = 'Past start · status unverified' if start_time and start_time <= now else 'Closed for picks' if lock_time and lock_time <= now else 'Open for picks' if lock_time else 'Lock time unverified'
        out += f'<td class="match-cell"><span class="competition">{e(m["competition"] or "Unverified tournament")}</span><div class="team-pair"><strong>{e(names[0])}</strong><span class="versus">vs</span><strong>{e(names[1])}</strong></div><div class="match-subline">{local_time(m["starts_at"])}<span class="dot-separator">·</span><span>{e(tier)}</span></div><span class="availability" data-availability>{availability}</span></td>'
        out += '<td class="probability-cell" data-label="Win probabilities">'
        if a:
            for i, (name, p) in enumerate(zip(names, a['probabilities'])):
                out += f'<div class="prob-line {"favored" if i == pick else ""}"><span class="prob-team">{e(name)}<small class="fair-line">Fair line {a["fair_decimal"][i]:.3f}</small></span><strong>{p * 100:.1f}%</strong></div>'
            out += f'<div class="prob-bar" aria-hidden="true"><span class="bar-a" style="width:{a["probabilities"][0] * 100:.4f}%"></span><span class="bar-b" style="width:{a["probabilities"][1] * 100:.4f}%"></span></div><span class="tiny muted">{"Researched fallback · " if researched else ""}Calculated · full-series winner</span>'
        else:
            out += '<div class="prob-line"><span>' + e(names[0]) + '</span>' + blank() + '</div><div class="prob-line"><span>' + e(names[1]) + '</span>' + blank() + '</div><p class="tiny muted">Insufficient verified inputs. No default 50/50.</p>'
        out += '</td><td class="pick-cell" data-label="Our pick">'
        if a and pick is not None:
            lock, start = timestamp(m['locks_at']), timestamp(m['starts_at'])
            closed = (lock is not None and lock <= now) or (start is not None and start <= now)
            expired = not is_fresh(m['observed_at'], now) or not is_fresh(a['observed_at'], now)
            inactive = expired or closed or lock is None
            caption = f'{max(a["probabilities"]) * 100:.1f}% estimated win chance' + ((' · money line replaced the featured model' if fallback.get('upgraded_from_featured_model') else ' · researched fallback, featured method rejected this fixture') if researched else '')
            status = 'Stale / unverified freshness · not a current pick' if expired else 'Closed for picks · estimate retained for audit' if closed else 'Lock unverified · confirm on Hotspawn' if lock is None else caption
            out += f'<div class="pick-choice {"inactive-pick" if inactive else ""}" data-pick-choice>{icon("check")}<strong data-original="{e(names[pick])}">{"Snapshot: " if inactive else ""}{e(names[pick])}</strong></div><p class="pick-caption" data-pick-caption data-original="{e(caption)}">{e(status)}</p>'

        elif a:
            out += '<strong class="muted">No directional edge</strong><p class="pick-caption">Equal estimate; no arbitrary pick.</p>'
        else:
            out += '<strong class="unresolved-text">Not yet resolved</strong><p class="pick-caption">See the research trail.</p>'
        out += '</td><td class="basis-cell" data-label="Basis &amp; sources">'
        if researched:
            out += badge('Researched fallback', 'purple')
        else:
            out += badge({'market': 'Market-backed', 'bookmaker': 'Bookmaker line', 'model': 'Research model', 'unresolved': 'Unresolved'}[method], {'market': 'green', 'bookmaker': 'green', 'model': 'purple', 'unresolved': 'amber'}[method])
        out += '<div class="row-source-links">' + external(m['source_url'], 'Hotspawn')
        if a:
            out += external(a['source_url'], 'Market' if method == 'market' else 'Valve' if method == 'model' else 'Bookmaker API')
        if researched:
            out += f'<a class="source-link" href="{prefix}origination/#match-{e(m["id"])}">Audit trail{icon("arrow")}</a>'
        out += '</div>' + evidence(m, prefix, fallback) + '</td></tr>'
    out += '</tbody></table><p id="filter-empty" class="empty-state" hidden>No matches fit these filters. <button type="button" class="text-button" data-reset>Clear filters</button></p></div>' if filters else '</tbody></table></div>'
    return out


def selected_fallback(m, fallbacks):
    """One displayed probability basis: preserve money lines, upgrade only models."""
    row = fallbacks.get(str(m['id']))
    if not row or not row.get('origination'):
        return None
    a = m.get('analysis')
    if a is None or (a.get('method') == 'model' and row.get('upgraded_from_featured_model')
                     and row['origination']['method'] in {'market', 'bookmaker', 'consensus'}):
        return row
    return None


def effective_basis(m, fallbacks):
    """Return (method, is_researched_fallback) for what this row actually displays."""
    fb = selected_fallback(m, fallbacks)
    if fb:
        return fb['origination']['method'], True
    if m['analysis']:
        return m['analysis']['method'], False
    return 'unresolved', False


def unresolved_table(data, prefix):
    fallbacks = data.get('fallbacks') or {}
    rows = [m for m in data['matches'] if m['availability'] != 'past' and m['analysis'] is None]
    resolved_elsewhere = [m for m in rows if (fallbacks.get(str(m['id'])) or {}).get('origination')]
    still_blank = [m for m in rows if m not in resolved_elsewhere]
    if not rows:
        return '<p class="positive-note">No unresolved non-archived fixtures in this snapshot. This is not a guarantee of current source coverage; check source health and freshness above.</p>'
    head = ''
    if resolved_elsewhere:
        head = ('<p class="section-intro">' + f'{len(resolved_elsewhere)} of these {len(rows)} fixtures were rejected by the '
                'featured exact-name method but do carry an independently researched estimate, shown in the list above with a '
                '<strong>Researched fallback</strong> badge and its own audit trail. '
                f'{len(still_blank)} remain without any supported probability and stay blank below.</p>')
    out = head + '<div class="table-scroll"><table class="simple-table unresolved-table"><caption class="sr-only">Every unresolved future or unknown-schedule match and the missing evidence</caption><thead><tr><th scope="col">Match</th><th scope="col">Why the featured method produced no pick</th><th scope="col">Review</th></tr></thead><tbody>'
    for m in rows:
        unknown = m['availability'] == 'unknown'
        reason = ('Scheduled start is unverified; a safe team/time market join cannot be made.' if unknown else next((r['detail'] for r in reversed(m['research']) if r['status'] == 'unresolved'), 'No verified inputs are available'))
        primary = next((r for r in m['research'] if r['stage'].startswith('Primary') and r['status'] != 'resolved'), None)
        primary_note = '<p class="tiny"><strong>Primary-market limitation:</strong> ' + e(primary['detail']) + ' ' + external(primary['source_url'], 'Primary source') + '</p>' if primary else ''
        identity_notes = ''.join('<p class="identity-note">' + e(r['detail']) + ' ' + external(r['source_url'], 'HLTV record for review') + '</p>' for r in m['research'] if r['stage'] == 'HLTV identity review')
        trail = ''
        if m['research']:
            trail = '<details><summary>Sources tried &amp; limitations</summary><ol class="research-trail">'
            for r in m['research']:
                trail += f'<li><strong>{e(r["stage"])}</strong> · {e(r["status"])}<p>{e(r["detail"])}</p>{external(r["source_url"], "Original source")}</li>'
            trail += '</ol></details>'
        target = 'coverage/#unknown-schedules' if unknown else 'picks/#match-' + m['id']
        fb = (fallbacks.get(str(m['id'])) or {}).get('origination')
        fallback_note = ''
        if fb:
            names = [x['name'] or 'Unverified team' for x in m['teams']]
            fb_row = fallbacks[str(m['id'])]
            chosen = names[fb_row['pick_index']] if fb_row.get('pick_index') is not None else 'no directional pick'
            fallback_note = ('<p class="tiny"><strong>Researched fallback available:</strong> '
                             + e(fb.get('label') or fb['method']) + ' · ' + e(f'{fb["probabilities"][0] * 100:.1f}% / {fb["probabilities"][1] * 100:.1f}%')
                             + ' · pick ' + e(chosen) + ', observed ' + local_time(fb['observed_at']) + '. '
                             + external(fb['source_url'], fb.get('source') or 'Research source')
                             + f' <a class="internal-link" href="{prefix}origination/#match-{e(m["id"])}">Audit trail →</a></p>')
        out += f'<tr><th scope="row">{e(match_name(m))}<small>{local_time(m["starts_at"])}</small></th><td>{e(reason)}{fallback_note}{primary_note}{identity_notes}<p class="tiny">Missing probabilities remain blank. An unavailable source is not proof that no betting market exists.</p>{trail}</td><td>{external(m["source_url"], "Hotspawn source")}<a class="internal-link" href="{prefix}{e(target)}">Full research trail →</a></td></tr>'
    return out + '</tbody></table></div>'


def _source_links(urls, labels=None):
    labels = labels or {}
    return '<div class="evidence-links">' + ''.join(external(url, labels.get(url, urlparse_host(url))) for url in dict.fromkeys(urls)) + '</div>'


def contrarian_review(data, prefix):
    """Render the dated upset review without changing the canonical pick table."""
    context = data.get('_contrarian')
    if not context:
        return ''
    historical = context['historical']
    roster = context['roster']
    current = context['current']
    profile = context['profile']
    old_p = historical['pre_match_probabilities']
    map_text = ', '.join(f"{m['map']} {m['score']}" for m in historical['result']['maps'])
    out = '<section class="content-section" id="contrarian"><div class="section-heading"><div><p class="eyebrow">Day 1 review · source-linked</p><h2>Contrarian, not careless</h2></div><a class="internal-link" href="' + prefix + 'picks/">Current picks ' + icon('arrow') + '</a></div>'
    out += '<p class="section-intro">A recent upset can reveal a blind spot, but it is not permission to invent a new probability. This review keeps the primary line intact and preserves a historical, team-specific watch. It does not establish that the underdog is underpriced; the separate market-backed alternatives screen uses stricter evidence criteria. Hotspawn popularity is not used.</p>'
    out += '<div class="table-scroll"><table class="simple-table contrarian-table"><caption class="sr-only">Day 1 upset review, roster context and current contrarian watch</caption><thead><tr><th scope="col">Review item</th><th scope="col">Evidence &amp; verification limits</th><th scope="col">Implication for picks</th></tr></thead><tbody>'
    out += '<tr><th scope="row">9z vs Aurora<small>14 Oct 2026 · ' + e(historical['event']) + '</small></th><td><strong>HLTV reports 9z won ' + e(historical['result']['series_score']) + '.</strong> ' + e(map_text) + '. Organizer result and original historical price: — unverified. The preserved session archive lists a prior estimate, but its original order book was not retained here; it is not treated as a verified closing line.' + _source_links(historical['source_urls'], {historical['source_urls'][0]: 'Hotspawn fixture', historical['source_urls'][1]: 'HLTV match', historical['source_urls'][2]: 'HLTV result report', historical['source_urls'][3]: 'Polymarket line'}) + '</td><td>One high-profile miss is a reason to inspect identity, roster and map context—not to discard external prices. The result is historical context, not a new current win rate.</td></tr>'
    out += '<tr><th scope="row">Aurora roster context<small>' + 'Summer rebuild · report date unverified' + '</small></th><td>' + e(roster['context']) + _source_links(roster['source_urls'], {roster['source_urls'][0]: 'HLTV roster report'}) + external('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md', 'Official dated Valve roster') + '</td><td>This is a secondary-source report, not a verified primary announcement here. The official dated snapshots are compared on the review page. It does not prove fatigue, poor preparation or a current stand-in, so this dashboard makes no roster, rest or veto adjustment without a current source.</td></tr>'
    if current['status'] == 'contrarian-watch':
        current_probability = f"{current['watch_probability'] * 100:.1f}%"
        current_text = '<strong>' + e(current['watch_team']) + ' watch vs ' + e(current['teams'][1] if current['teams'][0] == current['watch_team'] else current['teams'][0]) + '.</strong> Current canonical estimate: ' + current_probability + ' for ' + e(current['watch_team']) + ' (' + e(current['primary_method']) + '); primary pick remains ' + e(current['primary_pick'] or 'unresolved') + '.'
        current_labels = {current['source_urls'][0]: 'Hotspawn current fixture', current['source_urls'][1]: 'Valve rating input', profile['source_urls'][0]: 'HLTV day-one report', profile['source_urls'][1]: 'HLTV match report'}
        current_text += _source_links(current['source_urls'], current_labels)
        implication = 'This is historical team-specific, model-only context, not proof of a pricing edge or admission to the market-backed screen. It is not a replacement pick: use the primary pick unless leaderboard strategy explicitly accepts the model risk.'
    else:
        current_text = '<strong>No current exact-pair watch.</strong> The next scheduled fixture did not meet the strict 9z–Falcons identity and probability rule.' + _source_links(current['source_urls'])
        implication = 'No contrarian selection is published when the evidence or current probability is missing. The primary pick engine remains authoritative.'
    out += '<tr><th scope="row">Current watch<small>editorial model-watch threshold ≤ ' + f'{profile["max_probability"] * 100:.0f}%' + ' for the underdog</small></th><td>' + current_text + '</td><td>' + e(implication) + '</td></tr>'
    out += '</tbody></table></div>'
    out += '<div class="limitations-callout"><strong>Guardrail for climbing the leaderboard</strong><p>Prefer one or two source-backed contrarian watches over a blanket “fade the favorite” rule. Require a recent result against a strong opponent plus a current independent probability. Do not treat a roster-change headline, rest assumption or Hotspawn crowd share as a numeric edge. Full limitations and the machine-readable review are linked in <a class="source-link" style="text-decoration:underline" href="' + prefix + 'data/contrarian.json">the review evidence ↓</a>.</p></div></section>'
    return out


def summary(data, prefix):
    c = data['counts']
    active = [m for m in data['matches'] if m['availability'] in {'open', 'locked', 'unknown_lock'}]
    complete = data.get('complete_picks')
    cc = complete['counts'] if complete else None
    total = cc['active'] if cc else c['upcoming']
    resolved = cc['resolved'] if cc else c['upcoming'] - c['unresolved']
    money = cc['market'] + cc['bookmaker'] + cc['consensus'] if cc else c['market'] + c['bookmaker']
    models = cc['model'] if cc else c['model']
    unresolved = cc['unresolved'] if cc else c['unresolved']
    p = round(100 * resolved / total) if total else 0
    ring = f'<div class="coverage-dial"><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="50" class="dial-track"/><circle cx="60" cy="60" r="50" class="dial-progress" stroke-dasharray="{p * 3.14159:.3f} 314.159"/></svg><div><strong>{resolved}<span>/{total}</span></strong><small>with probabilities</small></div></div>'
    out = heading('Counter-Strike 2 intelligence', 'Executive summary', 'Every Hotspawn CS2 fixture, independently researched. Your picks are one tap away.')
    if complete:
        coverage_label = 'Complete picks' if data['coverage_complete'] else 'Retained snapshot picks'
        out += f'<section class="limitations-callout" aria-label="Complete pick coverage"><h2>{coverage_label}: {cc["with_pick"]} / {cc["active"]}</h2><p>{cc["unresolved"]} unresolved in the complete researched list. Estimate snapshot: {local_time(complete["generated_at"])}. <a class="internal-link" href="{prefix}origination/#picks">All matches, both probabilities &amp; picks →</a> <a class="internal-link" href="{prefix}origination/#unresolved">Unresolved picks &amp; limitations →</a></p><p><a class="internal-link" href="#contrarian">Day-one review →</a></p></section>'
    out += f'<section class="hero" aria-labelledby="briefing-title"><div class="hero-copy"><span class="hero-kicker"><span class="status-dot"></span>{"FULL INVENTORY RECONCILED" if data["coverage_complete"] else "INVENTORY NOT VERIFIED"}</span><h2 id="briefing-title">All the matches.<br>One clear view.</h2><p><strong>{total} active fixtures.</strong> {money} external-line estimates, {models} research-model estimates, and {unresolved} unresolved in the complete list. No Hotspawn popularity scores. No made-up odds.</p><div class="hero-actions"><a class="button primary" href="{prefix}origination/#picks">See all match picks {icon("arrow")}</a><a class="hero-secondary" href="{prefix}strategy/">Leaderboard plan →</a><a class="hero-secondary" href="#unresolved">Unresolved &amp; limitations ↓</a><a class="hero-secondary" href="{prefix}twc-picks/">TWC Day 3: picks &amp; review →</a></div></div>{ring}</section>'
    out += '<nav class="briefing-links" aria-label="Briefing shortcuts"><a href="' + prefix + 'origination/#picks">Full updated picks</a><a href="' + prefix + 'strategy/">Leaderboard plan</a><a href="#next-matches-section">Next matches</a><a href="#contrarian">Contrarian review</a><a href="' + prefix + 'edge/">Upset review &amp; edge</a><a href="' + prefix + 'twc-picks/">Day 3 pick guide</a><a href="#upset-watchlist">Market-backed alternatives</a><a href="#unresolved">Unresolved &amp; limitations</a></nav>'
    if c['unknown_schedule']:
        out += f'<div class="limitations-callout"><strong>{c["unknown_schedule"]} additional matches have unverified schedules.</strong> They cannot safely be matched to betting lines and are not included in the future-match count. <a href="#unresolved">See unresolved schedules and limitations →</a></div>'
    out += '<p class="muted small">The metrics and next-match preview below describe the original featured method only. The complete list above adds researched fallbacks without rewriting these audit records.</p>'
    out += '<div class="metrics">'
    cards = [('Future matches', c['upcoming'], f'{c["inventory"]} source records · {c["archived"]} past starts', 'target', 'coverage/'), ('Featured market', c['market'] + c['bookmaker'], 'Original external market observations', 'layers', 'picks/?basis=market'), ('Featured model', c['model'], 'Valve ratings · higher uncertainty', 'book', 'picks/?basis=model'), ('Featured rejections', c['unresolved'], 'Check complete-list fallbacks above', 'flag', 'review/#unresolved')]
    for title, value, subtitle, sym, url in cards:
        out += f'<a class="metric-card" href="{prefix}{url}"><div class="metric-top"><span>{title}</span>{icon(sym)}</div><strong>{value:02d}</strong><p>{e(subtitle)}</p></a>'
    out += '</div>'
    out += '<section class="content-section"><div class="section-heading"><div><p class="eyebrow">The short version</p><h2>What to know before you pick</h2></div>' + badge('Read-only analysis', 'neutral') + '</div><div class="briefing-notes">'
    out += f'<div><span class="note-number">01</span><p><strong>Start with the full picks list.</strong> Both team probabilities, the suggested team, lock time and original evidence are shown together. {external(LOBBY, "Submit picks on Hotspawn")}</p></div><div><span class="note-number">02</span><p><strong>Know what backs the number.</strong> Green means an external market; purple means an uncalibrated rating model used only when the primary method failed. Neither is a guarantee.</p></div><div><span class="note-number">03</span><p><strong>Check the timestamp.</strong> Automatic checks are scheduled every four hours. GitHub may delay a run. After eight hours without a successful observation, the site warns you not to treat the snapshot as current.</p></div></div></section>'
    out += '<section class="content-section" id="next-matches-section"><div class="section-heading"><div><p class="eyebrow">On the radar</p><h2>Next matches</h2></div><a class="internal-link" href="' + prefix + 'picks/">All match picks ' + icon('arrow') + '</a></div>'
    out += matches_table(active[:5], prefix, table_id='next-matches', fallbacks=data.get('fallbacks')) + '</section>'
    out += contrarian_review(data, prefix)
    out += '<section class="content-section" id="unresolved"><div class="section-heading"><div><p class="eyebrow amber-text">Coverage gaps, not hidden omissions</p><h2>Unresolved picks &amp; limitations</h2></div><a class="internal-link" href="' + prefix + 'review/">All review flags ' + icon('arrow') + '</a></div>'
    out += f'<p><a class="internal-link" href="{prefix}origination/#unresolved">Complete-list unresolved picks &amp; limitations →</a>. Original featured-method rejections remain in the <a class="internal-link" href="{prefix}review/#unresolved">audit register</a>; supported fallbacks may resolve them in the complete list.</p>'
    unresolved_data = {'matches': [dict(m, analysis=m['origination']) for m in complete['matches']]} if complete else data
    out += unresolved_table(unresolved_data, prefix)
    out += f'<div class="limitations-callout"><strong>What the numbers cannot confirm</strong><p>HLTV or bookmakers can block unattended access. Provider team names can differ. Rating snapshots do not confirm today’s lineup or map vetoes. {c["archived"]} past-start Hotspawn records are preserved separately, not sold as current picks. Unverified best-of formats and source status conflicts are listed for review.</p><div class="inline-links"><a href="{prefix}coverage/">Coverage &amp; source status →</a><a href="{prefix}methodology/">How probabilities are calculated →</a><a href="{prefix}review/">Flagged for Review →</a></div></div></section>'
    out += '<section class="content-section"><h2>Researched fallback picks</h2><p>Provider-name discrepancies can prevent exact-name market joins. <a style="text-decoration:underline" href="./origination/#picks">Open the full researched picks list</a> for featured picks plus independently sourced fallbacks. <a style="text-decoration:underline" href="./origination/#unresolved">Unresolved picks &amp; limitations</a> and <a style="text-decoration:underline" href="./origination/#aliases">identity evidence</a> remain visible. Featured money lines are preserved; a verified money line can replace a model-only estimate.</p></section>'
    out += contrarian_briefing(data, prefix)
    out += where_everything_lives(data, prefix)
    return out


def where_everything_lives(data, prefix):
    """One obvious map of the site: which list to use for what."""
    fallbacks = data.get('fallbacks') or {}
    upcoming = [m for m in data['matches'] if m['availability'] != 'past']
    basis = [effective_basis(m, fallbacks) for m in upcoming]
    with_pick = sum(1 for b, _ in basis if b != 'unresolved')
    researched = sum(1 for _, fb in basis if fb)
    still_blank = len(upcoming) - with_pick
    rows = [
        ('Complete match picks', 'origination/#picks', 'The list to use on your phone: every non-archived Hotspawn CS2 '
         'fixture with both probabilities, one obvious pick, lock times and expandable evidence.',
         'Featured estimates plus researched fallbacks'),
        ('Leaderboard plan', 'strategy/', 'What to submit to climb the Hotspawn leaderboard: one plan pick per match, the few underdogs '
         'the lines say have a real shot, the points at stake, Hotspawn\'s scoring rules and the unresolved fixtures.',
         'Contrarian, not stupid'),
        ('TWC Day 3 picks & review', 'twc-picks/', 'Both deciders from the same refreshed probability feed, Days 1–2 results and source-backed roster context.', 'No fan votes or narrative probability adjustments'),
        ('Featured method picks', 'picks/', 'The audit list for the featured exact-name method, with searchable '
         'filters, researched-fallback badges and the unresolved research trails.',
         f'{with_pick} picks · {researched} researched fallbacks · {still_blank} blank'),
        ('Upset review & edge', 'edge/', 'Dated first-party review of the day-one Thunderpick World Championship '
         'results, Aurora roster context (not a proven cause of the upset), dated Valve standings and the seven rules applied '
         'before disagreeing with a market.', 'Research review · not a live feed'),
        ('Coverage & sources', 'coverage/', 'Inventory reconciliation, source health, the complete past-start archive '
         'and JSON/CSV downloads.', 'Every original request'),
        ('Methodology', 'methodology/', 'Exact matching rules, formulas, thresholds, source policy and model limits.',
         'How each number is produced'),
        ('Flagged for Review', 'review/', 'Missing inputs, blocked sources, identity ambiguity and format conflicts.',
         f'{len(data["flags"])} open flags'),
    ]
    out = ('<section class="content-section" id="site-map"><div class="section-heading"><div>'
           '<p class="eyebrow">No hunting</p><h2>Where every list lives</h2></div>'
           + badge('One tap from here', 'neutral') + '</div>'
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Every page on this site and '
           'what it contains</caption><thead><tr><th scope="col">Page</th><th scope="col">What it contains</th>'
           '</tr></thead><tbody>')
    for title, url, detail, meta in rows:
        out += (f'<tr><th scope="row"><a href="{prefix}{e(url)}">{e(title)} →</a><small>{e(meta)}</small></th>'
                f'<td>{e(detail)}</td></tr>')
    return out + '</tbody></table></div></section>'


def picks(data, prefix):
    c = data['counts']
    fallbacks = data.get('fallbacks') or {}
    active = [m for m in data['matches'] if m['availability'] != 'past']
    basis = [effective_basis(m, fallbacks) for m in active]
    shown = {'all': len(active),
             'market': sum(1 for b, _ in basis if b in ('market', 'bookmaker', 'consensus')),
             'model': sum(1 for b, _ in basis if b == 'model'),
             'unresolved': sum(1 for b, _ in basis if b == 'unresolved')}
    researched = sum(1 for _, fb in basis if fb)
    with_pick = shown['all'] - shown['unresolved']
    out = heading('Every non-archived match', 'Match picks & probabilities', 'See both sides. Know the pick. Check the evidence. Full-series estimates only; no map, handicap or popularity-derived lines.', '<a class="button secondary" href="' + prefix + 'data/picks.csv">Download CSV ↓</a>')
    out += (f'<div class="info-strip">{icon("check")}<span><strong>{with_pick} of {shown["all"]} matches below carry a pick.</strong> '
            f'{c["market"] + c["bookmaker"]} come from the featured exact-name market or bookmaker method'
            + (f', {researched} more from the audited research ladder, badged <strong>Researched fallback</strong>, ' if researched else ', ')
            + f'and {shown["unresolved"]} remain blank because no supported evidence exists. '
            f'<a href="{prefix}origination/#picks">Complete researched picks view →</a> '
            f'<a href="{prefix}edge/">Day-one upset review &amp; contrarian edge →</a></span></div>')
    out += f'<div class="limitations-callout"><strong>Need a pick for rows unresolved below?</strong> <a style="text-decoration:underline" href="{prefix}origination/#picks">Complete researched picks: featured estimates plus source-backed fallbacks →</a> <a style="text-decoration:underline" href="{prefix}origination/#unresolved">Remaining limitations →</a> <a style="text-decoration:underline" href="{prefix}index.html#contrarian">Day 1 contrarian review →</a></div>'
    out += '<div class="info-strip">' + icon('clock') + '<span>Snapshot observed ' + local_time(data.get('inventory_observed_at')) + '. Lock times come from each Hotspawn fixture. Picks are not submitted automatically. <a href="#unresolved">Jump to unresolved picks &amp; limitations ↓</a></span></div>'
    out += '<section class="content-section picks-section" aria-label="Searchable match list"><div class="filter-bar"><label class="search-box">' + icon('search') + '<span class="sr-only">Search teams or tournaments</span><input id="match-search" type="search" placeholder="Search teams or tournaments…" autocomplete="off"></label><label class="select-field"><span>Tournament</span><select id="tournament-filter"><option value="all">All tournaments</option>'
    for tournament in sorted(set(m['competition'] or 'Unverified tournament' for m in active)):
        out += f'<option value="{e(tournament)}">{e(tournament)}</option>'
    out += '</select></label><label class="select-field"><span>Sort by</span><select id="match-sort"><option value="start">Soonest first</option><option value="confidence">Highest estimated chance</option><option value="team">Team name</option></select></label></div><div class="filter-second"><div class="filter-tabs" role="group" aria-label="Probability basis">'
    for value, label, count in [('all', 'All matches', shown['all']), ('market', 'Market-backed', shown['market']), ('model', 'Research', shown['model']), ('unresolved', 'Unresolved', shown['unresolved'])]:
        out += f'<button type="button" data-basis="{value}" aria-pressed="{"true" if value == "all" else "false"}">{label}<span>{count}</span></button>'
    out += f'</div><p id="filter-count" aria-live="polite">{len(active)} matches</p></div><noscript><p class="limitations-callout">JavaScript is off. Every row and source remains visible; interactive search and live freshness/lock checks are unavailable. Status reflects build time only; confirm the published observation and Hotspawn countdown before choosing a team.</p></noscript>'
    out += matches_table(active, prefix, filters=True, fallbacks=fallbacks) + '</section><div class="legend"><span>' + badge('Market-backed', 'green') + ' Independent external prices</span><span>' + badge('Research model', 'purple') + ' Uncalibrated rating estimate</span><span>' + badge('Researched fallback', 'purple') + ' Featured method rejected the fixture; audited research ladder produced this estimate</span><span>' + badge('Unresolved', 'amber') + ' No supported probability</span></div>'
    out += f'<p class="muted small">Showing future-start and unknown-schedule fixtures at the last inventory check. Past-start records remain available in the <a href="{prefix}coverage/#archive">complete source archive</a>. Fair decimal lines are calculated in each row’s evidence panel; they are not executable bookmaker quotes.</p>'
    out += '<section class="content-section" id="unresolved"><div class="section-heading"><div><p class="eyebrow amber-text">Every gap stays visible</p><h2>Unresolved picks &amp; limitations</h2></div><a class="internal-link" href="' + prefix + 'review/">All flagged findings →</a></div>' + unresolved_table(data, prefix) + '</section>'
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
    reconciliation = '<a href="' + prefix + 'data/evidence/hotspawn-context.json">Inventory reconciliation ↓</a>' if data.get('inventory_observed_at') else ''
    out += '</tbody></table></div><div class="inline-links downloads"><a href="' + prefix + 'data/latest.json">Full snapshot JSON ↓</a>' + reconciliation + '<a href="' + prefix + 'data/picks.csv">Picks CSV ↓</a></div></section>'
    out += f'<section class="content-section" id="archive"><div class="section-heading"><div><p class="eyebrow">Preserved, not misrepresented</p><h2>Past-start source archive <span class="heading-count">{c["archived"]}</span></h2></div></div><p class="section-intro">These records still exist in Hotspawn’s scheduled feed, but their scheduled starts are in the past. “Scheduled” is the source’s value, not a verified present status. Results, current picks and retrospective probabilities are not invented.</p><div class="table-scroll"><table class="simple-table archive-table"><caption class="sr-only">Every past-start CS2 record retained from the original Hotspawn feed</caption><thead><tr><th>Match / tournament</th><th>Scheduled start</th><th>Source status</th><th>Original source</th></tr></thead><tbody>'
    for m in data['matches']:
        if m['availability'] != 'past':
            continue
        primary = next((r for r in m['research'] if r['stage'].startswith('Primary') and r['status'] != 'resolved'), None)
        primary_note = '<p class="tiny"><strong>Primary-market limitation:</strong> ' + e(primary['detail']) + ' ' + external(primary['source_url'], 'Primary source') + '</p>' if primary else ''
        identity_notes = ''.join('<p class="identity-note">' + e(r['detail']) + ' ' + external(r['source_url'], 'HLTV record for review') + '</p>' for r in m['research'] if r['stage'] == 'HLTV identity review')
        out += f'<tr><th scope="row">{e(match_name(m))}<small>{e(m["competition"] or "Unverified tournament")} · ID {e(m["id"])}</small></th><td>{local_time(m["starts_at"])}</td><td>{e(m["source_status"] or "")}<small>Current result/status unverified</small></td><td>{external(m["source_url"], "Hotspawn source")}</td></tr>'
    out += '</tbody></table></div></section>'
    out += f'<div class="limitations-callout"><strong>Earlier session outputs, preserved for review</strong><p>These archived dashboards use older observation times and different identity/model rules. They are not the current picks feed and are not independently reverified by this pipeline.</p><div class="inline-links"><a href="{prefix}docs/index.html">Earlier research snapshot →</a><a href="{prefix}archive/root-session/index.html">Earlier root dashboard →</a></div></div>'
    unknown = [m for m in data['matches'] if m['availability'] == 'unknown']
    if unknown:
        out += '<section class="content-section" id="unknown-schedules"><h2>Unverified schedules</h2>' + matches_table(unknown, prefix, table_id='unknown-schedules') + '</section>'
    return out


def methodology(data, prefix):
    out = heading('A number needs a reason', 'How we resolve a pick', 'Source facts stay separate from analysis. No Hotspawn community percentage, popularity, score or Pick’em point multiplier enters a probability calculation.')
    steps = [('01', 'Verify the full match inventory', 'Read the public lobby, CS2 lobby and the same public fixture array used by Hotspawn’s client. Reconcile every CS2 ID. Keep old or inconsistent records in the archive rather than dropping them.', LOBBY, 'Official lobby'), ('02', 'Use the primary external market', 'Discover CS2 games from Polymarket’s directory and paginate its official CS2-tag event API to a terminal page. A repeated page, schema change, access failure or the bounded 2,000-event limit is published as a discovery limitation. Confirm the event, exact two team names, start time within 60 seconds, unique active series moneyline, accepting-orders state, token IDs and condition ID. Read both original order books. No map or handicap markets.', 'https://docs.polymarket.com/api-reference/market-data/get-order-book', 'Official order book documentation'), ('03', 'Research only primary-method gaps', 'For those matches only, try HLTV’s official match directory, then original esportsbook lines. HLTV’s sibling time/team cards are replayed from saved original markup; differing provider names stay flagged, not silently aliased. Thunderpick has a paired-price adapter; GG.BET, Pinnacle, Rivalry and Stake are public-access checks and do not fabricate prices if a validated contract is unavailable. HTTP 403, redirects and schema failures are visible limitations—not proof of no market.', 'https://www.hltv.org/matches', 'HLTV official match directory'), ('04', 'Model only supported rating inputs—or leave blank', 'If no accepted external line exists, read the latest official global Valve snapshot on or before today. Require exactly one matching team name and a complete five-player roster for each team. Reject missing teams and snapshots older than 35 days. The complete-picks fallback can disambiguate several same-name five-player rows only when a fresh, exact-fixture HLTV lineup matches exactly one whole five-player roster; no partial overlap or strongest-row guess. Otherwise publish an explicitly uncalibrated rating estimate. If any requirement fails, publish the match as unresolved.', 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'Valve official standings')]
    out += '<section class="content-section resolution-steps">'
    for n, title, description, url, label in steps:
        out += f'<article class="resolution-step"><span>{n}</span><div><h2>{title}</h2><p>{e(description)}</p>{external(url, label)}</div></article>'
    out += '</section><section class="content-section prose"><p class="eyebrow">Our calculations, not source facts</p><h2>From observations to percentages</h2><h3>Prediction-market estimate</h3><p>For each outcome, take the best positive-size bid and ask from its own book. The midpoint is <code>m = (best bid + best ask) / 2</code>. Normalize the paired midpoints with <code>P(A) = mA / (mA + mB)</code> and <code>P(B) = 1 − P(A)</code>. Require valid two-sided books, a spread of no more than 12 cents per outcome, matching token/condition IDs, and source timestamps no older than eight hours. Directory percentages and Gamma’s last-price defaults are not used.</p><p>These are indicative midpoints, not guaranteed execution quotes or “true” win probabilities. Trading fees, slippage and position size are excluded. A single prediction market is not independent bookmaker consensus. ' + external('https://docs.polymarket.com/api-reference/market-data/get-order-book', 'Inspect the official book schema') + '</p><h3>Original bookmaker estimate</h3><p>For a verified pair of decimal odds <code>dA, dB</code>, calculate <code>qA = 1/dA</code>, <code>qB = 1/dB</code>, then remove proportional margin with <code>P(A) = qA / (qA + qB)</code>. Only active, two-outcome, prematch match-winner lines are accepted. Implied-probability sums outside 0.85–1.35 are rejected as a data-quality policy. Different mirrors of one book count as one source family; independent families, if present, are combined using the median normalized probability.</p><h3>Valve-rating research estimate</h3><p>The published Valve model uses a Glicko-style expected score. We implement <code>g = 1 / √(1 + 3(ln(10)/400)² × RD² / π²)</code> and <code>P(A) = 1 / (1 + 10^(g × (RB − RA) / 400))</code>. Points <code>RA, RB</code> are sourced facts; <code>RD = 75</code> is a fixed assumption following Valve’s fit example, not a measured uncertainty for today’s roster.</p><p>' + external('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/fit.js', 'Valve fit example') + ' ' + external('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/glicko.js', 'Valve expected-score implementation') + '</p><div class="limitations-callout"><strong>Important model limitations</strong><p>This deployment has not been backtested or calibrated. A historic name-matched roster is not proof of today’s lineup. Stand-ins, roster changes, map vetoes, team form since the snapshot and bookmaker information are not added without verification. This model does not override a valid primary market pick and is never labeled a verified betting line.</p></div><h3>Our fair line and the pick</h3><p>The fair decimal line is <code>1/P</code>; it is a calculated reference, not odds offered by any bookmaker. The suggested team has the higher unrounded probability. An exactly equal estimate has no directional pick. Missing data is not replaced with 50/50. Displayed percentages are rounded to one decimal place; the downloadable data retains higher precision.</p></section>'
    out += '<section class="content-section prose"><p class="eyebrow">Operational boundaries</p><h2>Freshness, identity &amp; blank values</h2><ul><li>Refreshes are scheduled every four hours in UTC. GitHub Actions schedules are best-effort, not a real-time service-level guarantee.</li><li>The inventory observation time, price observation time, source book timestamp and rating snapshot date remain distinct. A failed refresh never resets successful-observation timestamps.</li><li>After eight hours, the browser displays a stale warning and disables “current pick” language. After a fixture’s explicit lock time, it is labeled closed for picks. A past scheduled start is not treated as a verified final result.</li><li>Matching is Unicode/case/whitespace-equivalent exact naming plus start time within 60 seconds. Abbreviations, sponsor aliases and fuzzy matches are not guessed. Ambiguous Valve names are rejected unless the complete-picks fallback replays a fresh, exact-fixture HLTV proof matching exactly one entire five-player roster. Four-of-five overlap is not sufficient.</li><li>Unverified factual values remain blank and labeled “unverified.” Calculated probabilities and fair lines are visibly identified as analysis; they are not filled-in source facts.</li><li>Access controls, robots restrictions and challenges are not bypassed. No login, paid API key, user input or betting account is required for this read-only dashboard.</li><li>Every published probability is replayed from saved first-party evidence before deployment. Every match row links back to Hotspawn; pricing and model inputs carry their own original-source links.</li></ul><p>' + external('https://play.hotspawn.com/how-it-works', 'Hotspawn rules for manual review') + f' · <a href="{prefix}review/">See all flagged limitations →</a></p></section>'
    return out


def review(data, prefix):
    out = heading('Transparent by design', 'Flagged for Review', 'Unresolved matches, blocked sources and inconsistent official fields are published here. They do not block publication; they do block unsupported claims.')
    out += f'<div class="limitations-callout"><strong>Additional identity research and fallback picks</strong><p>Exact-name rejections below are retained for audit. <a style="text-decoration:underline" href="{prefix}origination/#picks">See newly researched fallback picks</a> and <a style="text-decoration:underline" href="{prefix}origination/#aliases">the source-linked alias review registry</a>. These associations do not independently confirm current rosters; Valve estimates remain uncalibrated.</p></div>'
    out += review_note(prefix, data.get('day_one_audit'))
    if data.get('repo_audit'):
        out += audit_register(data['repo_audit'], prefix)
    if data.get('session_review'):
        from scripts.review_register import render as session_register
        out += session_register(data['session_review'], prefix)
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
        href = prefix + ('' if k == 'summary' else 'origination/#picks' if k == 'picks' else str(Path(path).parent) + '/')
        if k == 'summary':
            href = prefix + 'index.html'
        nav += f'<a class="nav-link {"active" if k == key else ""}" href="{href}"' + (' aria-current="page"' if k == key else '') + f'>{icon(sym)}<span>{label}</span>' + (f'<span class="nav-count">{len(data["flags"])}</span>' if k == 'review' else '') + '</a>'
    mobile = ''.join(f'<a href="{prefix + "index.html" if k == "summary" else prefix + ("origination/#picks" if k == "picks" else k + "/")}"' + (' aria-current="page"' if key == k else '') + f'>{icon(PAGES[k][2])}<span>{label}</span></a>' for k, label in [('summary', 'Summary'), ('picks', 'Picks'), ('edge', 'Edge'), ('coverage', 'Sources'), ('methodology', 'Methods'), ('review', 'Review')])
    inventory = data.get('inventory_observed_at') or ''
    stale = not data['coverage_complete'] or not is_fresh(inventory, datetime.now(timezone.utc))
    freshness = 'Snapshot needs attention' if stale else 'Source snapshot available'
    extra_css = f'<link rel="stylesheet" href="{prefix}assets/twc.css">' if key == 'twc' else ''
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)} · Spawn Scout</title><meta name="description" content="Every Hotspawn CS2 match, independent probabilities, clear picks and original evidence. Mobile-friendly, read-only analysis with visible coverage gaps."><meta name="theme-color" content="#142534"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'"><link rel="icon" href="{prefix}assets/scout-mark.svg" type="image/svg+xml"><link rel="stylesheet" href="{prefix}assets/scout.css">{extra_css}<script src="{prefix}assets/scout.js" defer></script></head>
<body data-page="{key}" data-inventory-time="{e(inventory)}" data-inventory-complete="{str(data['coverage_complete']).lower()}" data-snapshot-generated="{e(data['generated_at'])}" data-data-url="{prefix}data/latest.json"><a class="skip-link" href="#main">Skip to content</a>
<aside class="sidebar"><a class="brand" href="{prefix}index.html" aria-label="Spawn Scout home"><span class="brand-mark"><svg viewBox="0 0 28 28" aria-hidden="true"><path d="M5 4h9v9H5zM17 4h7v7h-7zM5 16h7v8H5z"/><path d="m16 17 8-4v11h-8z"/></svg></span><span>spawn<span class="brand-light">scout</span><small>CS2 MATCH INTELLIGENCE</small></span></a><p class="nav-label">YOUR DASHBOARD</p><nav aria-label="Main navigation">{nav}</nav><div class="sidebar-bottom"><div class="sidebar-note"><span class="status-dot"></span><strong>Independent analysis</strong><p>Hotspawn tells us who plays.<br>External sources inform the pick.</p></div>{external(LOBBY, 'Open Hotspawn lobby', 'sidebar-external')}<a class="sidebar-repo" href="{REPO}">Open-source &amp; auditable {icon('external')}</a></div></aside>
<div class="workspace"><header class="topbar"><div class="mobile-brand"><a href="{prefix}index.html">spawn<strong>scout</strong><span>CS2</span></a></div><div class="desktop-crumb">Workspace <span>/</span> <strong>{e(title)}</strong></div><div class="topbar-tools"><span class="refresh-pill">{icon('clock')} Checks every 4h</span><label class="timezone-control"><span class="sr-only">Display timezone</span><select id="timezone"><option value="Europe/Malta">Malta time</option><option value="UTC">UTC</option><option value="local">Device time</option></select></label></div></header>
<main id="main" tabindex="-1"><div class="snapshot-line"><span class="freshness-label" data-freshness><span class="status-dot"></span>{freshness}</span><span>Inventory checked {local_time(data.get('inventory_observed_at'))} <span data-zone-label>Malta</span></span></div><div id="stale-warning" class="stale-warning" role="status" {'' if stale else 'hidden'}><strong>Do not treat these as current picks.</strong> The inventory check failed or the successful snapshot is older than eight hours. Original timestamps are preserved. <a href="{prefix}coverage/">Check source status →</a></div><div id="new-snapshot" class="new-snapshot" hidden>A newer verified snapshot is available. <button type="button" id="load-update">Load updated picks →</button></div>{body}<footer class="footer"><div><strong>Better context. Clearer picks.</strong><p>Independent Hotspawn CS2 research · Not affiliated with Hotspawn, HLTV, Valve or any betting provider.</p><p>Estimates, not guarantees. No bets or picks are placed. Informational use only. 18+ where applicable.</p></div><div><a href="{prefix}methodology/">Methodology</a><a href="{prefix}review/">Flagged for Review</a><a href="{prefix}data/latest.json">Open data ↓</a><span class="tiny muted">Built {local_time(data['generated_at'])}</span></div></footer></main></div><nav class="mobile-nav" aria-label="Mobile navigation">{mobile}</nav></body></html>'''


def build(source: Path, output: Path):
    data = check_data(source)
    contrarian_data = load_review(source / 'contrarian.json')
    data['_contrarian'] = derive_context(data, contrarian_data)
    validate_context(data, data['_contrarian'])
    if (source / 'origination.json').exists():
        data['complete_picks'] = json.loads((source / 'origination.json').read_text())
        # Researched fallbacks are only displayed for fixtures the featured
        # exact-name method left blank; featured estimates are never rewritten.
        data['fallbacks'] = {str(r['id']): r for r in data['complete_picks'].get('matches') or [] if r.get('origination')}
    if (source / 'research/day-one-audit.json').exists():
        data['day_one_audit'] = json.loads((source / 'research/day-one-audit.json').read_text())
    # Session 1112299f's dated findings go through the same Flagged for Review table. This only extends the
    # in-memory list used for rendering; the published latest.json is the source directory copy and is untouched.
    # Session e6c0f47d's first-party unresolved-pick re-verification joins the same table the same way.
    for findings in (source / 'research/1112299f/flags.json', source / 'research/e6c0f47d/flags.json', source / 'research/6426358d/flags.json'):
        if findings.exists():
            have = {f['id'] for f in data['flags']}
            data['flags'] = data['flags'] + [f for f in json.loads(findings.read_text()) if f['id'] not in have]
    if (source / 'research/de176356/repo-review-register.json').exists():
        data['repo_audit'] = json.loads((source / 'research/de176356/repo-review-register.json').read_text())
    if (source / 'research/c07e1b40/repo-review.json').exists():
        data['session_review'] = json.loads((source / 'research/c07e1b40/repo-review.json').read_text())
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'assets').resolve() != Path('assets').resolve():
        shutil.copytree('assets', output / 'assets', dirs_exist_ok=True)
    if (output / 'data').resolve() != source.resolve():
        shutil.copytree(source, output / 'data', dirs_exist_ok=True)
    (output / '.nojekyll').touch()
    from scripts import build as _self
    from scripts.build_edge import edge_review
    from scripts.build_twc import render as twc_review
    edge_path = source / 'edge-review.json'
    _self.EDGE_SOURCE = edge_path
    renderers = {'summary': summary, 'picks': picks, 'coverage': coverage, 'methodology': methodology,
                 'review': review, 'edge': lambda d, pfx: edge_review(d, pfx, edge_path),
                 'twc': lambda d, pfx: twc_review(d, pfx, source)}
    for key, (_, path, _) in PAGES.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        prefix = './' if key == 'summary' else '../'
        target.write_text(shell(data, key, renderers[key](data, prefix), prefix))
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['hotspawn_id', 'team_a', 'team_b', 'starts_at_utc', 'locks_at_utc', 'source_status', 'availability_at_snapshot', 'team_a_probability_calculated', 'team_b_probability_calculated', 'suggested_team', 'basis', 'price_or_model_observed_at', 'rating_snapshot_date', 'original_hotspawn_source', 'analysis_source'])
    for m in data['matches']:
        fb = selected_fallback(m, data.get('fallbacks') or {})
        a = fb['origination'] if fb else m['analysis']
        pick_index = fb.get('pick_index') if fb else m['pick_index']
        # Defend downloads against formula injection in source-controlled team names.
        safe = lambda x: ("'" + str(x)) if str(x).startswith(('=', '+', '-', '@')) else x
        writer.writerow([safe(x) for x in [m['id'], m['teams'][0]['name'] or '', m['teams'][1]['name'] or '', m['starts_at'] or '', m['locks_at'] or '', m['source_status'] or '', m['availability'], a['probabilities'][0] if a else '', a['probabilities'][1] if a else '', m['teams'][pick_index]['name'] if pick_index is not None else '', a['method'] if a else '', a['observed_at'] if a else '', a.get('snapshot_date', '') if a else '', m['source_url'], a['source_url'] if a else '']])
    (output / 'data/picks.csv').write_text(stream.getvalue())
    if data.get('_twc_report'):
        (output / 'data/twc-day3-picks.json').write_text(json.dumps(data['_twc_report'], ensure_ascii=False, indent=2) + '\n')
    # Preserve the old root URLs without exposing a competing current feed.
    aliases = {'picks.html': 'picks/', 'methodology.html': 'methodology/', 'flagged.html': 'review/'}
    for old, target in aliases.items():
        (output / old).write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="0;url=./{target}"><title>Updated dashboard location</title></head><body><main><h1>This page has moved</h1><p><a href="./{target}">Open the current CS2 dashboard</a></p></main></body></html>')
    # Other sessions’ files remain unchanged in Git. Only generated artifact
    # copies receive an unmistakable archive banner.
    for source_dir, dest_dir, back in [(Path('docs'), output / 'docs', '../'), (Path('archive/root-session'), output / 'archive/root-session', '../../')]:
        if not source_dir.exists():
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        if source_dir.name == 'root-session':
            shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
        for source_page in source_dir.glob('*.html'):
            text = source_page.read_text()
            banner = f'<aside role="note" style="padding:18px;background:#fff0cf;border:2px solid #9b6b20;color:#382509;font:14px/1.7 system-ui"><strong>Archived session snapshot — not the current picks feed.</strong> Original values and timestamps are retained for review, not independently reverified or relabeled as current. <a style="color:#74310c;text-decoration:underline" href="{back}index.html">Open the current executive summary</a> · <a style="color:#74310c;text-decoration:underline" href="{back}review/">Current verification limitations</a></aside>'
            text = re.sub(r'(<body\b[^>]*>)', lambda m: m.group(1) + banner, text, count=1, flags=re.I)
            (dest_dir / source_page.name).write_text(text)
    if (source / 'origination.json').exists():
        from scripts.build_origination import build as build_originated
        build_originated(source, output)
    # Browser-test fixtures (site/_fixture) are never part of the published site or its link check.
    shutil.rmtree(output / '_fixture', ignore_errors=True)
    # TWC is generated by the same renderer loop and snapshot as every other
    # current view. Never overlay it with the former hand-authored root page.
    # Leaderboard plan: its own builder and stylesheet. It is derived, optional output, so a failure here
    # degrades to a placeholder page and a loud annotation instead of blocking the data refresh.
    from scripts.build_strategy import build as build_strategy, placeholder as strategy_placeholder
    try:
        build_strategy(source, output)
    except Exception as exc:
        print(f'::warning title=Leaderboard plan not built::{type(exc).__name__}: {exc}')
        strategy_placeholder(output, f'{type(exc).__name__}: {exc}')
    # Row-level official-source audit of what was just built: report, never block.
    try:
        from scripts.audit_rows import audit_site
        audit = audit_site(output)
        (output / 'data').mkdir(parents=True, exist_ok=True)
        (output / 'data/row-source-audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False) + '\n')
        totals = audit['totals']
        print(f"Row-source audit: {totals['rows']} rows, {totals['ok']} with an official link, {totals['flagged']} flagged unverified, {totals['navigation']} site-map, {totals['violation']} without a source")
        if totals['violation']:
            print(f"::warning title=Rows without an official source::{totals['violation']} table rows or pick cards carry neither an official link nor an unverified flag; see data/row-source-audit.json")
    except Exception as exc:  # the audit is a report; it must never stop a data refresh
        print(f'::warning title=Row-source audit not run::{type(exc).__name__}: {exc}')
    check_links(output)
    print(f'Built {len(PAGES)} current Pages views, compatible old URLs and explicitly archived session views in {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('site'))
    args = parser.parse_args()
    build(args.data, args.output)
