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
PAGES = {'summary': ('Executive summary', 'index.html', 'overview'), 'picks': ('Match picks', 'picks/index.html', 'target'), 'unresolved': ('Unresolved picks', 'unresolved/index.html', 'flag'), 'edge': ('Upset review & edge', 'edge/index.html', 'trend'), 'twc': ('TWC Day 5 picks', 'twc-picks/index.html', 'target'), 'final': ('Final day review', 'final-day/index.html', 'clock'), 'coverage': ('Coverage & sources', 'coverage/index.html', 'layers'), 'methodology': ('Methodology', 'methodology/index.html', 'book'), 'review': ('Flagged for Review', 'review/index.html', 'flag')}
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
        elif a['method'] == 'model' and a.get('family') == 'form':
            body += (f'<p class="notice-inline"><strong>Own results-based estimate.</strong> One team has no '
                     f'complete five-player row in the official Valve table, so its rating was fitted to '
                     f'{e(a.get("n_series"))} finished series against officially rated opponents '
                     f'(posterior SD {e(a.get("rating_sd"))} points). This is a research model, not a '
                     'bookmaker price.</p><div class="mini-table-wrap"><table class="mini-table">'
                     '<caption>Published model inputs</caption><thead><tr><th>Team</th><th>Fitted points</th>'
                     '<th>Source</th></tr></thead><tbody>')
            for r in a['inputs']:
                label = 'bo3.gg series' if 'results-based' in str(r.get('source') or '') else 'Valve'
                body += (f'<tr><th scope="row">{e(r["name"])}</th><td>{e(r["points"])}</td>'
                         f'<td>{external(r["source_url"], label)}</td></tr>')
            body += '</tbody></table></div>'
            samples = a.get('samples') or []
            if samples:
                body += ('<details class="sample-detail"><summary>Series used in the fit '
                         f'({len(samples)} shown)</summary><ul class="sample-list">')
                for s in samples:
                    result = 'W' if s.get('won') else 'L'
                    body += (f'<li><span class="sample-result {result.lower()}">{result}</span> '
                             f'{e(s.get("date"))} · {external(s.get("source_url"), e(s.get("opponent") or "Opponent"))}'
                             f' <span class="tiny muted">BO{e(s.get("bo"))}</span></li>')
                body += '</ul></details>'
            body += (f'<div class="evidence-links">{external(a.get("source_url"), "bo3.gg fixture")}'
                     f'<a href="{prefix}data/origination.json">Saved origination evidence ↓</a></div>')
        elif a['method'] == 'model' and a.get('family') == 'network':
            body += (f'<p class="notice-inline"><strong>Own network estimate.</strong> Neither side has a '
                     'complete official rating row and no money line prices this fixture, so both ratings come '
                     f"from a Bradley–Terry fit over {e(a.get('graph_matches'))} finished bo3.gg series anchored on "
                     f"Valve's official points for {e(a.get('graph_anchors'))} teams. Research model, not a bookmaker price.</p>"
                     '<div class="mini-table-wrap"><table class="mini-table"><caption>Published model inputs</caption>'
                     '<thead><tr><th>Team</th><th>Fitted points (SE)</th><th>Series</th><th>Source</th></tr></thead><tbody>')
            for r in a['inputs']:
                body += (f'<tr><th scope="row">{e(r["name"])}</th><td>{e(r["points"])} '
                         f'{("± " + str(e(r.get("se")))) if r.get("se") is not None else ""}</td>'
                         f'<td>{e(r.get("series"))}</td><td>{external(r["source_url"], "bo3.gg team")}</td></tr>')
            body += '</tbody></table></div>'
            body += (f'<p class="tiny">Rating-difference SD {e(a.get("rating_sd_diff"))} points · one-sigma '
                     f'probability interval {a["interval"][0]:.3f}–{a["interval"][1]:.3f} · graph size '
                     f'{e(a.get("graph_matches"))} series · {e(a.get("graph_anchors"))} anchored teams.</p>')
            body += (f'<div class="evidence-links">{external("https://bo3.gg/matches", "bo3.gg results")}'
                     f'<a href="{prefix}data/origination.json">Saved origination evidence ↓</a></div>')
        elif a['method'] == 'model':
            body += f'<p>Rating snapshot: <strong>{e(a["snapshot_date"])}</strong>. Roster lists below belong to that snapshot, not a confirmed current lineup.</p><div class="mini-table-wrap"><table class="mini-table"><caption>Published model inputs</caption><thead><tr><th>Team</th><th>Points</th><th>Source</th></tr></thead><tbody>'
            for r in a['inputs']:
                body += f'<tr><th scope="row">{e(r["name"])}</th><td>{r["points"]}</td><td>{external(r["source_url"], "Valve")}</td></tr>'
            body += '</tbody></table></div>'
            for r in a['inputs']:
                body += f'<p class="tiny"><strong>{e(r["name"])}</strong>: {e(", ".join(r["roster"] or []))}</p>'
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
                 'ladder. Featured money lines are preserved; an upgraded model remains above only as an audit reference.</p>')
        for q in o.get('quotes') or []:
            facts = []
            odds, bid, ask = q.get('odds'), q.get('bid'), q.get('ask')
            if odds:
                facts.append(f'decimal odds {e(odds[0])} / {e(odds[1])}')
            if bid and ask:
                facts.append(f'bid/ask {bid[0]:.3f}/{ask[0]:.3f} vs {bid[1]:.3f}/{ask[1]:.3f}')
            if not facts:
                facts.append('price observation recorded in the saved evidence')
            ident = (f'Retained sentence SHA-256: <code>{e(q.get("excerpt_sha256"))}</code>. '
                     if q.get('family') == 'reference' else
                     f'Original event ID: <strong>{e(q.get("event_id") or "unverified")}</strong>. ')
            body += (f'<p>{e(q.get("provider") or "Provider")} ({e(q.get("family") or "source")}): '
                     + ' · '.join(facts) + '. ' + ident
                     + external(q.get('source_url') or o['source_url'], (q.get('provider') or 'Provider') + ' record') + '</p>')
        for r in o.get('inputs') or []:
            input_label = 'HLTV ranking input' if o.get('source') == 'HLTV world ranking' else 'Valve rating input'
            roster_note = (f', roster {e(", ".join(r.get("roster") or []))}' if r.get('roster') else '')
            rank_note = (f', rank {e(r.get("rank"))}' if r.get('rank') is not None else '')
            unranked_note = (' <strong>unranked</strong> — HLTV publishes no row, so the model uses its floor of 0.0 points'
                             if r.get('unranked') else '')
            body += (f'<p class="tiny">{input_label}: <strong>{e(r["name"])}</strong> {e(r["points"])} points'
                     f'{rank_note}, snapshot {e(r.get("snapshot_date") or "unverified")}{roster_note}.{unranked_note} '
                     + (external(r.get('source_url') or o.get('source_url'), 'Source record') if (r.get('source_url') or o.get('source_url')) else '<span class="unverified">source link unverified</span>') + '</p>')
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


def matches_table(matches, prefix, *, table_id='match-list', filters=False, fallbacks=None, now=None):
    fallbacks = fallbacks or {}
    if not matches:
        return '<div class="empty-state">No verified future fixtures in this snapshot. Check the <a href="' + prefix + 'coverage/">source status</a> before assuming there are no matches.</div>'
    out = f'<div class="matches-wrap"><table class="matches-table" id="{table_id}"><caption class="sr-only">Hotspawn CS2 match picks. Percentages are calculated estimates, never guaranteed outcomes. Times are Europe/Malta unless changed.</caption><thead><tr><th scope="col">Match &amp; start</th><th scope="col">Win probabilities</th><th scope="col">Our pick</th><th scope="col">Basis &amp; verification</th></tr></thead><tbody>'
    now = now or datetime.now(timezone.utc)
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
            out += badge({'market': 'Market-backed', 'bookmaker': 'Bookmaker line', 'reference': 'Aggregated line', 'model': 'Research model', 'guidance': 'Wide-book guidance', 'unresolved': 'Unresolved'}[method], {'market': 'green', 'bookmaker': 'green', 'reference': 'green', 'model': 'purple', 'guidance': 'amber', 'unresolved': 'amber'}[method])
        out += '<div class="row-source-links">' + external(m['source_url'], 'Hotspawn')
        if a:
            out += external(a['source_url'], 'Market' if method == 'market' else model_source_label(a) if method == 'model' else 'Aggregated odds' if method == 'reference' else 'Wide book' if method == 'guidance' else 'Bookmaker API')
        if researched:
            out += f'<a class="source-link" href="{prefix}origination/#match-{e(m["id"])}">Audit trail{icon("arrow")}</a>'
        out += '</div>' + evidence(m, prefix, fallback) + '</td></tr>'
    out += '</tbody></table><p id="filter-empty" class="empty-state" hidden>No matches fit these filters. <button type="button" class="text-button" data-reset>Clear filters</button></p></div>' if filters else '</tbody></table></div>'
    return out


#: The methods whose probabilities come from a two-sided money market or a
#: published bookmaker price. Anything else is a research model, and the site
#: must say so on the row itself instead of only in the methodology page.
MONEY_METHODS = frozenset({'market', 'bookmaker', 'consensus', 'reference'})

#: Short, honest labels for the badge that follows every resolved glance row.
METHOD_BADGES = {
    'market': ('Market line', 'green'),
    'bookmaker': ('Bookmaker', 'green'),
    'consensus': ('Consensus', 'green'),
    'reference': ('Aggregated', 'green'),
    'guidance': ('Wide book', 'amber'),
}


def basis_badge(analysis, researched=False):
    """One readable label for what produced a row's probabilities.

    A phone reader must be able to tell a betting line from a research estimate
    without opening the evidence box. The classes are the existing badge tones,
    so no new colour contract is introduced.
    """
    if researched:
        return '<span class="badge purple">Researched</span>'
    label, tone = METHOD_BADGES.get((analysis or {}).get('method'), ('Model', 'purple'))
    return f'<span class="badge {tone}">{e(label)}</span>'


def model_source_label(analysis: dict) -> str:
    url = str((analysis or {}).get('source_url') or '')
    source = str((analysis or {}).get('source') or '')
    if 'hltv.org' in url or 'HLTV' in source:
        return 'HLTV ranking'
    if 'bo3.gg' in url or 'results-based' in source.lower():
        return 'bo3.gg results'
    return 'Valve'


def researched_method(match: dict) -> tuple[str, str, str]:
    """Short, data-derived provenance for one researched (featured-blank) row.

    Returns ``(what produced the number, source name, source URL)``. It reads
    only the published origination record; it never re-prices anything and
    never claims a provider that the row does not name.
    """
    o = match.get('origination') or {}
    method = str(o.get('method') or '')
    label = str(o.get('label') or '')
    source = str(o.get('source') or '')
    url = str(o.get('source_url') or '')
    if method == 'market':
        return 'a prediction-market line', source or 'Prediction market', url
    if method == 'bookmaker':
        return 'an esportsbook line', source or 'Esportsbook', url
    if method == 'consensus':
        return 'a median of independent money sources', source or 'Independent sources', url
    if method == 'reference':
        return 'an aggregated bookmaker average', source or 'Aggregated bookmaker', url
    if method == 'guidance':
        return 'a wide-book guidance quote (no pick)', source or 'Esportsbook', url
    if method == 'model':
        lowered = f'{source} {label}'.lower()
        if 'hltv' in lowered:
            return 'the HLTV world-ranking model', source or 'HLTV world ranking', url
        if 'network' in lowered:
            return 'the bo3.gg results network model', source or 'bo3.gg series results', url
        if 'bo3' in lowered or 'results-based' in lowered:
            return 'the bo3.gg results model', source or 'bo3.gg series results', url
        if 'valve' in lowered:
            return 'the Valve rating model', source or 'Valve official standings', url
    return label or method or 'a researched estimate', source or 'Research source', url


def selected_fallback(m, fallbacks):
    """One displayed probability basis: preserve money lines, upgrade only models or non-directional ties."""
    row = fallbacks.get(str(m['id']))
    if not row or not row.get('origination'):
        return None
    a = m.get('analysis')
    if a is None or ((a.get('method') == 'model' or (m.get('pick_index') is None and row.get('pick_index') is not None))
                     and row.get('upgraded_from_featured_model')
                     and row['origination']['method'] in {'market', 'bookmaker', 'consensus', 'reference'}):
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


def exec_banner(data, prefix):
    """Executive-summary banner that answers 'where are the updated picks?'.

    The brief requires the executive summary to contain internal links to the
    updated picks list and to be obvious on a phone. This banner is the first
    content block after the page heading; it contains only links and counts,
    never a probability or a pick, and every href is an internal site link
    that was verified by the link audit. Session 75aa5b56 makes the link text
    explicitly name the destination page and the phone tap target size meets
    44 px (verified by tests/test_75aa5b56.py).
    """
    complete = data.get('complete_picks') or {}
    cc = complete.get('counts') or {}
    active = cc.get('active', data['counts'].get('upcoming', 0))
    with_pick = cc.get('with_pick', 0)
    unresolved = cc.get('unresolved', data['counts'].get('unresolved', 0))
    model = (cc.get('model', 0) + cc.get('guidance', 0)) if complete else data['counts'].get('model', 0)
    generated = local_time(complete.get('generated_at')) if complete.get('generated_at') else local_time(data.get('inventory_observed_at'))
    return (
        f'<section class="exec-banner" aria-label="Where to find the updated picks">'
        f'<p class="exec-banner-label">Executive summary — start here on your phone</p>'
        f'<h3>Every Hotspawn CS2 pick, one tap away</h3>'
        f'<p class="exec-banner-desc">Picks live on their own pages with full probabilities, evidence and lock times. All links below stay inside this site and are thumb-friendly on mobile (≥44 px).</p>'
        f'<div class="exec-banner-actions">'
        f'<a class="primary" href="{prefix}origination/#picks" aria-label="Open the updated picks list with every match and both probabilities"><span class="label">Updated picks — all matches<span class="sub">{with_pick} of {active} with a pick · both teams\' % shown</span></span><span aria-hidden="true">→</span></a>'
        f'<a class="secondary" href="{prefix}picks/" aria-label="Open the searchable featured-picks audit"><span class="label">Featured picks feed<span class="sub">Searchable audit · method filters</span></span><span aria-hidden="true">→</span></a>'
        f'<a class="tertiary" href="{prefix}unresolved/" aria-label="Open the unresolved picks page with every source tried and why each is still missing a pick"><span class="label">Unresolved &amp; limitations<span class="sub">{unresolved} without a pick · {model} from research models · why + sources</span></span><span aria-hidden="true">→</span></a>'
        f'</div>'
        f'<p class="exec-banner-meta">Inventory {local_time(data.get("inventory_observed_at"))} · snapshot {generated} · refresh every 4 h (catch-up 2.5 h later keeps it inside 8 h) · <a href="{prefix}coverage/">coverage &amp; refresh status →</a> · <a href="{prefix}methodology/">how the list is built →</a> · <a href="{prefix}#picks-at-a-glance">picks at a glance ↓</a> · <a href="{prefix}origination/#unresolved">every research trail →</a></p>'
        f'</section>'
    )


def start_here(data, prefix):
    """A phone-first jump bar directly under the page title.

    The brief asked for one place on the phone that says where the picks are.
    This block links only; it adds no probability, no pick and no fixture.
    """
    complete = data.get('complete_picks')
    cc = (complete or {}).get('counts') or {}
    active = cc.get('active') or data['counts']['upcoming']
    unresolved = cc.get('unresolved', data['counts']['unresolved'])
    with_pick = cc.get('with_pick')
    # Session f60683a4: the first jump on a phone must be the picks on this
    # page. The Day-5 TWC archive (18 Oct) stays on the site map; putting a
    # four-day-old review in this bar buried the current card.
    items = [
        (prefix + '#picks-at-a-glance', 'Picks on this page', 'target',
         'Every active fixture with both win probabilities and the obvious pick.',
         'picks-here'),
        (prefix + 'origination/#picks', 'All match picks', 'target',
         'Both team win probabilities where sourced; unresolved fixtures stay blank and are listed separately.',
         ''),
        (prefix + 'strategy/', 'Leaderboard plan', 'layers',
         'One plan pick per open fixture and the underdogs worth a play.',
         ''),
        (prefix + 'origination/#unresolved', f'Unresolved ({unresolved})', 'flag',
         'Fixtures with no compliant external price, and the reason for each.',
         ''),
        (prefix + '#unresolved-register', 'Blanks in this summary', 'flag',
         'This page lists every pick without a line, its blocker and the sources actually tried.',
         ''),
    ]
    out = ('<nav class="start-here" id="start-here" aria-label="Start here — where the picks are">'
           '<p class="start-here-label">Start here · where the picks are</p><ul>')
    for href, title, sym, detail, extra in items:
        klass = f' class="{e(extra)}"' if extra else ''
        out += (f'<li><a href="{e(href)}"{klass}>{icon(sym)}<strong>{e(title)}</strong>'
                f'<span>{e(detail)}</span></a></li>')
    out += '</ul>'
    if with_pick is not None:
        resolved = cc.get('resolved', active - unresolved)
        without_direction = max(0, resolved - with_pick)
        pick_word = 'pick' if with_pick == 1 else 'picks'
        counts = [f'{with_pick} directional {pick_word} from {active} active fixtures']
        if without_direction:
            estimate_word = 'estimate' if without_direction == 1 else 'estimates'
            verb = 'has' if without_direction == 1 else 'have'
            counts.append(f'{without_direction} resolved {estimate_word} {verb} no directional pick')
        if unresolved:
            fixture_word = 'fixture' if unresolved == 1 else 'fixtures'
            counts.append(f'{unresolved} unresolved {fixture_word}')
        out += (f'<p class="tiny muted" style="padding:10px 2px 0">'
                + '; '.join(e(part) for part in counts) +
                '. Missing estimates stay blank; open the complete list for every match and its research trail.</p>')
    return out + '</nav>'


def glance(data, prefix, now=None):
    """Phone-first one-glance index of every active fixture's selected pick.

    The executive summary previously put the first match card ~2,800 px down a
    phone page. This section is a compact index over the same canonical
    selection used by the full table: featured estimate first, then an audited
    researched fallback. It adds no probability, no pick and no fixture.
    Unresolved fixtures are never dropped from this index; only resolved rows
    are capped, with an explicit link to the complete list.
    """
    fallbacks = data.get('fallbacks') or {}
    active = [m for m in data['matches'] if m['availability'] in {'open', 'locked', 'unknown_lock'}]
    if not active:
        return ''
    now = now or datetime.now(timezone.utc)

    def basis(m):
        fallback = selected_fallback(m, fallbacks)
        fb = (fallback or {}).get('origination')
        return (fb, fallback.get('pick_index'), True) if fb else (m['analysis'], m['pick_index'], False)

    def upcoming(m):
        start = timestamp(m.get('starts_at'))
        return bool(start and start > now)

    open_rows = [m for m in active if basis(m)[0] and upcoming(m)]
    resolved_rest = [m for m in active if basis(m)[0] and not upcoming(m)]
    # A resolved-but-stale row and a truly unresolved row must not be merged:
    # the summary must never omit the name of a match that has no estimate.
    blank_rows = [m for m in active if not basis(m)[0] and upcoming(m)]
    past_blank_rows = [m for m in active if not basis(m)[0] and not upcoming(m)]
    # Complete index: every upcoming pick, then every unresolved fixture, then
    # recent resolved rows for context. The earlier ten-row cap hid an active
    # fixture from the phone summary (5star–1WIN on 2026-10-21, hidden while it
    # was the thirteenth row), which contradicts the brief that the summary must
    # lead to a pick for every listed match. Nothing is re-priced or re-ordered
    # by opinion; the ordering is only grouping.
    shown, seen = [], set()
    for group, limit in ((open_rows, None), (blank_rows + past_blank_rows, None), (resolved_rest, None)):
        for m in (group if limit is None else group[:limit]):
            if m['id'] not in seen:
                shown.append(m)
                seen.add(m['id'])
    hidden = len(active) - len(shown)
    picks = sum(1 for m in active if basis(m)[0] and basis(m)[1] is not None)

    rows = ''
    for m in shown:
        names = [t['name'] or 'Unverified team' for t in m['teams']]
        a, pick, researched = basis(m)
        detail = f'{prefix}origination/#match-{e(m["id"])}'
        links = external(m['source_url'], 'Hotspawn')
        if a:
            links += external(a['source_url'], 'Market' if a['method'] == 'market' else model_source_label(a) if a['method'] == 'model' else 'Aggregated odds' if a['method'] == 'reference' else 'Wide book' if a['method'] == 'guidance' else 'Bookmaker')
        links += f'<a class="source-link" href="{detail}">Full detail{icon("arrow")}</a>'
        if a and pick is not None:
            lock = timestamp(m['locks_at'])
            start = timestamp(m.get('starts_at'))
            # A started fixture is closed even if its lock time was not stored; the
            # browser repeats this check (assets/glance-lock.js) so a page built before
            # the lock or start passed never keeps advertising "Pick".
            closed = (lock is not None and lock <= now) or (start is not None and start <= now)
            # Both teams' win probabilities, always, so a phone reader never has
            # to open the evidence box to learn the other side of the pick. The
            # picked team keeps the emphasised number and the "Pick" label; the
            # opponent's complementary estimate follows in muted text.
            other = 1 - pick
            choice = (f'<span class="glance-pick-label{" is-closed" if closed else ""}" data-glance-pick>{"Locked" if closed else "Pick"}</span>'
                      f'<strong>{e(names[pick])}</strong><span class="glance-prob">{a["probabilities"][pick] * 100:.1f}%</span>'
                      f'<span class="glance-other">{e(names[other])} {a["probabilities"][other] * 100:.1f}%</span>'
                      + basis_badge(a, researched))

        elif a:
            choice = ('<span class="glance-pick-label">No edge</span><strong>Even</strong>'
                      '<span class="glance-prob">no side</span>'
                      f'<a class="internal-link" href="{prefix}#unresolved-register">Why</a>')
        else:
            choice = ('<span class="glance-pick-label unresolved-text">Unresolved</span>'
                      f'<a class="internal-link" href="{prefix}origination/#unresolved">Why</a>')
        closed_attr = ''
        if a and pick is not None:
            closed_attr = (f' data-glance-starts="{e(m.get("starts_at") or "")}"'
                           f' data-glance-locks="{e(m.get("locks_at") or "")}"'
                           f' data-glance-closed="{"true" if closed else "false"}"')
        search_text = ' '.join([names[0], names[1], m['competition'] or '']).lower()
        rows += (f'<li class="glance-row" data-glance-id="{e(m["id"])}" data-search="{e(search_text)}"{closed_attr}>'
                 f'<div class="glance-match"><strong>{e(names[0])} <span class="versus">vs</span> {e(names[1])}</strong>'
                 f'<span class="glance-time">{e(m["competition"] or "Unverified tournament")} · {local_time(m["starts_at"])}</span></div>'
                 f'<div class="glance-choice">{choice}</div>'
                 f'<div class="glance-links">{links}</div></li>')
    note = (f'<p class="tiny muted glance-foot">Showing {len(shown)} of {len(active)} active fixtures; every unresolved fixture is included. '
            f'<a class="internal-link" href="{prefix}origination/#unresolved">Unresolved &amp; limitations →</a></p>'
            if hidden else
            f'<p class="tiny muted glance-foot">All {len(active)} active fixtures are listed. '
            f'<a class="internal-link" href="{prefix}origination/#picks">Open the complete audited list →</a> '
            f'<a class="internal-link" href="{prefix}origination/#unresolved">Unresolved picks &amp; limitations →</a></p>')
    money_picks = sum(1 for m in active if basis(m)[0] and basis(m)[1] is not None
                      and basis(m)[0].get('method') in MONEY_METHODS)
    model_picks = picks - money_picks
    # The link to the no-line register must only exist when that register does,
    # otherwise the summary would carry an anchor that goes nowhere.
    no_line = any(basis(m)[0] and basis(m)[0].get('method') not in MONEY_METHODS for m in active)
    no_line_link = (f'<a class="internal-link" href="{prefix}#no-line-register">picks without a betting line</a>'
                    if no_line else 'the research-model rows')
    return ('<section class="content-section" id="picks-at-a-glance"><div class="section-heading"><div>'
            '<p class="eyebrow">Every pick, one tap away</p><h2>Picks at a glance</h2></div>'
            f'<a class="internal-link" href="{prefix}origination/#picks">Full audited list {icon("arrow")}</a></div>'
            f'<p class="section-intro"><strong>{len(active)}</strong> active Hotspawn CS2 fixtures in this snapshot, '
            f'<strong>{picks}</strong> with a directional pick — <strong>{money_picks}</strong> from an external betting line, '
            f'<strong>{model_picks}</strong> from a research model — and <strong>{len(blank_rows) + len(past_blank_rows)}</strong> explicitly unresolved. '
            'Every row shows both teams\' win probability, the pick, and what produced the number. '
            'A missing estimate is never filled with a default 50/50; model-only rows are listed with their limitations under '
            f'{no_line_link}.</p>'
            # Phone findability (session 3016b0c6): type a team/tournament and
            # only matching glance rows stay visible. Progressive enhancement
            # only — with no JavaScript every row stays visible; it never
            # re-prices or recalculates anything.
            '<div class="glance-finder"><label for="glance-search">Find a pick — type a team or tournament</label>'
            '<input id="glance-search" type="search" inputmode="search" autocomplete="off" '
            'placeholder="e.g. Spirit Academy" aria-controls="glance-list">'
            '<p class="glance-count" id="glance-count" role="status"></p>'
            '<p class="glance-empty" id="glance-empty" hidden>No match in this snapshot uses that name. '
            'Clear the search to see every pick, or open the complete list.</p></div>'
            '<ol class="glance-list" id="glance-list">' + rows + '</ol>' + note + '</section>')


def _brief_blank_reason(match: dict) -> str:
    """One plain-language blocker for the executive-summary index.

    Derived only from the published research trail; it never re-prices a row,
    adds a probability or promotes a rejected quote into a pick.
    """
    detail = ' '.join(str(r.get('detail') or '') for r in (match.get('research') or [])
                      if r.get('status') != 'resolved')
    lowered = detail.lower()
    if 'spread' in lowered and 'exceeds' in lowered:
        return 'book too wide'
    if 'multiple valve rosters' in lowered:
        return 'ambiguous rating'
    if 'no valve rating row' in lowered or 'complete five-player' in lowered:
        return 'no rating'
    if 'no alias-verified' in lowered:
        return 'no external line'
    return 'no verified line'


def source_probe_block(data, prefix):
    """What each source class actually answered for the blank fixtures.

    The brief asked for the *limitations* of generating picks on the unresolved
    rows, not only their names. This block republishes the dated, read-only
    probe: which esportsbook/aggregator surfaces answered, what HLTV returned
    from the runner, and whether bo3.gg could identify each side at all. It
    never converts a status code into a probability.
    """
    probe = data.get('_source_probe') or {}
    fixtures = probe.get('blank_fixtures') or []
    providers = probe.get('providers') or []
    if not fixtures and not providers:
        return ''
    status_of = lambda entry: (entry.get('request') or {}).get('http_status')
    reachable = [p for p in providers if status_of(p) == 200]
    refused = [p for p in providers if status_of(p) != 200]
    blank_by_id = {str(m.get('id')): m for m in
                   (data.get('complete_picks') or {}).get('matches') or [] if m.get('origination') is None}
    rows = ''
    for fixture in fixtures:
        teams = fixture.get('teams') or []
        hltv_codes = sorted({status_of(h) for h in (fixture.get('hltv') or []) if status_of(h)})
        hltv_url = next((h.get('request', {}).get('url') for h in (fixture.get('hltv') or [])
                         if str(h.get('request', {}).get('url', '')).startswith('https://www.hltv.org/matches/')), None)
        lookups = (fixture.get('bo3') or {}).get('team_lookup') or []
        found = [l for l in lookups if l.get('id')]
        bo3_cell = ('<br>'.join(
            f'{"✓" if l.get("id") else "✕"} {e(l.get("name"))}'
            + (f' <span class="tiny muted">bo3 id {e(l.get("id"))}</span>' if l.get('id') else
               ' <span class="tiny muted">not listed</span>') for l in lookups) or blank())
        bet = (fixture.get('bo3') or {}).get('bet')
        bet_cell = ('bookmaker price published' if bet else
                    'no bookmaker price block' if (fixture.get('bo3') or {}).get('bound') else
                    'fixture not listed on bo3.gg')
        blank_row = blank_by_id.get(str(fixture.get('hotspawn_id'))) or {}
        blocker = _brief_blank_reason(blank_row) if blank_row else ''
        detail = next((r.get('detail') for r in (blank_row.get('research') or [])
                       if r.get('status') == 'unresolved' and r.get('stage') != 'Origination result'), '')
        links = (external(fixture.get('hotspawn_source_url'), 'Hotspawn')
                 + (external(hltv_url, 'HLTV') if hltv_url else '')
                 + ''.join(external(f'https://bo3.gg/teams/{l["id"]}', 'bo3.gg') for l in found[:2]))
        rows += (f'<tr><th scope="row">{e(" vs ".join(teams))}'
                 f'<small>{e(fixture.get("competition") or "Unverified tournament")}</small></th>'
                 f'<td>{" / ".join(str(c) for c in hltv_codes) if hltv_codes else "no verified HLTV match URL"}</td>'
                 f'<td>{bo3_cell}</td><td>{e(bet_cell)}</td>'
                 f'<td>{e(blocker) if blocker else blank()}'
                 + (f'<small class="tiny muted">{e(str(detail)[:220])}</small>' if detail else '')
                 + f'<div class="row-source-links">{links}</div></td></tr>')
    provider_line = ' '.join(
        f'<span class="tried-chip {"resolved" if status_of(p) == 200 else "unresolved"}">'
        f'{e(p.get("label"))} · {e(status_of(p) if status_of(p) is not None else "no response")}</span>'
        for p in providers[:18])
    observed = probe.get('generated_at')
    return ('<div class="source-probe" id="source-probe">'
            '<h3>Why these picks are missing · sources tried</h3>'
            f'<p class="section-intro">Read-only sweep on {local_time(observed)}: '
            f'<strong>{len(reachable)}</strong> of <strong>{len(providers)}</strong> esportsbook/aggregator '
            f'surfaces answered HTTP 200 and <strong>{len(refused)}</strong> refused an automated request '
            '(403/404/429/5xx/203). HLTV match pages are listed with the status the runner received; '
            'HLTV and several books block unattended access, which is a source limitation, not evidence '
            'that no market exists. bo3.gg answered for its results graph. '
            f'This sweep covers the {len(fixtures)} fixture(s) blank at that moment; every refresh retries '
            'every source, so a later market or model can close a row.</p>'
            '<div class="table-scroll"><table class="simple-table source-probe-table">'
            '<caption class="sr-only">Per-fixture source availability behind each blank pick</caption>'
            '<thead><tr><th scope="col">Fixture</th><th scope="col">HLTV</th>'
            '<th scope="col">bo3.gg identity</th><th scope="col">Published price</th>'
            '<th scope="col">Blocker</th></tr></thead><tbody>' + rows + '</tbody></table></div>'
            f'<p class="tiny muted probe-chips">{provider_line}</p>'
            f'<p class="tiny">Evidence file: <a href="{prefix}data/research/541cd43a/provider-probe.json">'
            'dated source probe ↓</a></p></div>')


#: Stage names that describe a money source. A reason drawn from one of these
#: actually explains why no betting line exists; a "checked" identity stage does
#: not, even though it is also a limitation.
_MONEY_STAGE_HINTS = ('market', 'exchange', 'esportsbook', 'book', 'aggregat', 'reference',
                      'polymarket', 'kalshi', 'thunderpick', 'bovada', 'pinnacle',
                      'gg.bet', 'rivalry', 'stake')


def _no_line_reason(match: dict) -> str:
    """Why no betting line exists for a resolved, model-only fixture.

    Reads only the published research trail. A failed money-source stage is
    preferred, because "HLTV confirmed the fixture" is not an explanation for a
    missing price; the identity stage is only used when no money stage has a
    detail. Nothing here is inferred, and an access failure is reported as an
    access failure, not as proof that no market exists.
    """
    def usable(entry):
        stage = str(entry.get('stage') or '').lower()
        return (entry.get('status') != 'resolved'
                and 'model' not in stage and 'identity' not in stage
                and str(entry.get('detail') or '').strip())

    trail = [e for e in match.get('research') or [] if usable(e)]
    failed_money = [e for e in trail
                    if e.get('status') in {'unresolved', 'unavailable'}
                    and any(hint in str(e.get('stage') or '').lower() for hint in _MONEY_STAGE_HINTS)]
    for entry in failed_money or trail:
        detail = str(entry['detail']).strip()
        return detail if len(detail) <= 190 else detail[:187].rstrip() + '…'
    return 'No provider returned a usable two-sided prematch price for this fixture.'


def no_line_register(data, prefix):
    """Picks that exist but have no external betting line behind them.

    The brief asks for a separate section covering the fixtures that cannot be
    resolved the same way as the featured picks, together with the limitations
    that produced the fallback. A blank register is not enough: a fixture can
    carry a researched estimate and still have no market, and the reader
    deserves to see that distinction on the executive summary.
    """
    complete = data.get('complete_picks') or {}
    rows = [m for m in (complete.get('matches') or [])
            if (m.get('origination') or {}).get('method') not in MONEY_METHODS
            and (m.get('origination') or {}).get('method') is not None]
    if not rows:
        return ''
    active = (complete.get('counts') or {}).get('active') or data.get('counts', {}).get('upcoming')
    cards = ''
    for m in rows:
        o = m['origination']
        names = [t.get('name') or 'Unverified team' for t in m.get('teams') or []]
        pick = m.get('pick_index')
        probs = o.get('probabilities') or []
        badge = 'Wide book · guidance only' if o.get('method') == 'guidance' else 'No betting line'
        tone = 'amber' if o.get('method') == 'guidance' else 'purple'
        if pick is not None and len(probs) == 2:
            other = 1 - pick
            choice = (f'<span class="glance-pick-label">Pick</span><strong>{e(names[pick])}</strong>'
                      f'<span class="glance-prob">{probs[pick] * 100:.1f}%</span>'
                      f'<span class="glance-other">{e(names[other])} {probs[other] * 100:.1f}%</span>')
        else:
            choice = ('<span class="glance-pick-label">No edge</span><strong>Even</strong>'
                      '<span class="glance-prob">no side</span>')
        tried = []
        seen = set()
        for entry in m.get('research') or []:
            stage = str(entry.get('stage') or '')
            if not stage or stage in seen or ('model' in stage.lower() and entry.get('status') == 'resolved'):
                continue
            seen.add(stage)
            tried.append(f'<span class="tried-chip {e(str(entry.get("status") or "unknown"))}">'
                         f'{e(stage)} · {e(str(entry.get("status") or "unknown"))}</span>')
            if len(tried) >= 5:
                break
        source = external(o.get('source_url') or m.get('source_url') or 'https://play.hotspawn.com/lobby',
                          model_source_label(o) if o.get('method') != 'guidance' else 'Wide book')
        source += external(m.get('source_url') or 'https://play.hotspawn.com/lobby', 'Hotspawn fixture')
        # Link the money sources that actually failed, so the reader can check the
        # claim that no line exists instead of taking the register's word for it.
        linked = {o.get('source_url'), m.get('source_url')}
        for entry in m.get('research') or []:
            if len([x for x in linked if x]) >= 5:
                break
            url = str(entry.get('source_url') or '')
            if not url.startswith('https://') or url in linked:
                continue
            if url.count('/') < 3 or url.rstrip('/').endswith(('.com', '.io', '.org', '.gg', '.bet', '.lv')):
                continue  # a bare directory/homepage adds no evidence beyond the fixture link
            linked.add(url)
            source += external(url, 'HLTV' if 'hltv.org' in url else 'Polymarket' if 'polymarket' in url
                               else 'Kalshi' if 'kalshi' in url else 'Market checked')
        cards += (f'<li class="no-line-card" id="no-line-{e(m.get("id"))}">'
                  f'<div class="unresolved-summary-head"><span class="comp">{e(m.get("competition") or "Unverified tournament")} · {local_time(m.get("starts_at"))}</span>'
                  f'<span class="badge {tone}">{e(badge)}</span></div>'
                  f'<h3>{e(names[0])} <span class="versus">vs</span> {e(names[1])}</h3>'
                  f'<p class="no-line-choice">{choice}</p>'
                  f'<p class="no-line-model">{e(o.get("label") or "Research model estimate")} '
                  f'<span class="tiny muted">· uncalibrated estimate, not a betting price</span></p>'
                  f'<p class="no-line-why"><strong>Why there is no line:</strong> {e(_no_line_reason(m))}</p>'
                  f'<div class="unresolved-tried">{"".join(tried)}</div>'
                  f'<p class="unresolved-links">{source}'
                  f'<a class="internal-link" href="{prefix}origination/#match-{e(m.get("id"))}">Full trail {icon("arrow")}</a></p>'
                  '</li>')
    return ('<div class="no-line-register" id="no-line-register">'
            '<h3 id="no-line-title">Picks without a betting line · limitations</h3>'
            f'<p class="section-intro">These <strong>{len(rows)}</strong> of <strong>{active}</strong> active fixtures carry a '
            'pick that no external sportsbook, exchange or market listed for us at the last refresh. They stay in the list — '
            'the brief asks for a pick or an explicit reason for every match — but each one is a '
            '<strong>research estimate</strong>: an uncalibrated rating or results model, not a price you could have bet. '
            'The model, the money sources tried and the blocked reason are shown for each. Every four-hour refresh retries '
            'all of them, so a row here can gain a real line later.</p>'
            '<ul class="unresolved-summary-list no-line-list">' + cards + '</ul></div>')


def line_sources_block(data, prefix):
    """Dated record of which line sources answered, for every reader.

    Session fbdc97d6 captured a read-only sweep of the esportsbook and
    aggregator surfaces from the GitHub runner. The brief asks for the
    *limitations* of generating a pick and for the sources to be reviewable,
    so the sweep is published with its status codes. It adds no probability and
    no pick; a 200 here is not a price.
    """
    record = data.get('_line_sources') or {}
    sources = record.get('sources') or []
    if not sources:
        return ''
    reachable = [s for s in sources if s.get('http_status') == 200]
    blocked = [s for s in sources if s.get('http_status') != 200]
    rows = ''
    for s in sources:
        status = s.get('http_status')
        kind = 'resolved' if status == 200 else 'unresolved'
        label = str(status) if status is not None else 'no response'
        listed = s.get('fixtures_listed') or []
        names = ', '.join(listed[:4]) + (f' +{len(listed) - 4} more' if len(listed) > 4 else '')
        rows += (f'<li class="line-source-row"><span class="tried-chip {kind}">{e(label)}</span>'
                 f'<a class="source-link" href="{e(s.get("url"))}" target="_blank" rel="noopener noreferrer">'
                 f'{e(s.get("name"))}{icon("external")}</a>'
                 f'<span class="line-source-note">{e(s.get("note") or "")}'
                 + (f' <span class="tiny muted">Mentioned on the page: {e(names)}</span>' if names else '')
                 + '</span></li>')
    return ('<div class="line-sources" id="line-sources">'
            '<h3>Line sources checked — dated sweep</h3>'
            f'<p class="tiny">Read-only sweep recorded from {e(record.get("environment") or "an automated runner")} at '
            f'{local_time(record.get("observed_at"))} and re-run by the four-hour pipeline when it can: '
            f'<strong>{len(reachable)}</strong> of '
            f'<strong>{len(sources)}</strong> surfaces answered HTTP 200 and <strong>{len(blocked)}</strong> '
            'refused, deleted or timed out. A reachable page is never a price by itself — only a two-sided '
            'first-party line or a published official rating may produce a number. '
            f'<a class="internal-link" href="{prefix}data/research/fbdc97d6/line-sources.json">Full record (JSON) ↓</a></p>'
            f'<ul class="line-source-list">{rows}</ul></div>')


def no_line_research_block(data, prefix):
    """Dated per-fixture research for matches with no betting line (3016b0c6).

    HLTV was tried first, then esportsbooks/aggregators, for every fixture the
    featured method left on a research model. This block publishes the dated
    outcome only: which fixtures still had no two-sided price anywhere
    reachable, and any *lead* (a bound two-sided relay quote) that the
    reviewed ladder must replay on the next refresh before a pick can change.
    Coefficients are quoted verbatim as evidence, never converted here.
    """
    record = data.get('_no_line_research') or {}
    fixtures = record.get('per_fixture') or []
    if not fixtures:
        return ''
    leads = [f for f in fixtures if f.get('money_line_lead')]
    # A dated sweep is never allowed to override the current complete-picks
    # snapshot. If the four-hour resolver has since consumed the lead, say so
    # and link to the current card; otherwise keep it clearly as a lead.
    current_rows = {str(m.get('id')): m for m in
                    ((data.get('complete_picks') or {}).get('matches') or [])}
    lead_rows = ''
    for f in leads:
        current = current_rows.get(str(f.get('id'))) or {}
        current_o = current.get('origination') or {}
        current_money = (current_o.get('method') in MONEY_METHODS
                         or current_o.get('family') == 'relay')
        bet = f.get('bo3_bet') or {}
        t1, t2 = bet.get('team_1') or {}, bet.get('team_2') or {}
        detail = (f"{e(bet.get('provider') or 'bookmaker')} via bo3.gg: "
                  f"{e(t1.get('name') or '')} {e(t1.get('coeff'))} / "
                  f"{e(t2.get('name') or '')} {e(t2.get('coeff'))}") if bet else 'Pinnacle guest board lists the fixture'
        url = f.get('bo3_bound_url')
        link = external(url, 'bo3.gg fixture') if url else ''
        if bet.get('path'):
            # Keep the second-hand origin transparent and give a reviewer the
            # bookmaker's own event link as well as the relay page. The quote
            # stays a lead until the first-party collector replays it.
            link += external(bet['path'], 'Thunderpick market')
        if current_money:
            current_label = current_o.get('label') or current_o.get('source') or 'external money line'
            status_note = (f'This dated lead was subsequently superseded in the current complete-picks '
                           f'snapshot by {e(current_label)}. Open the current match card; the dated relay '
                           'is not shown as a second pick.')
            link += f'<a class="internal-link" href="{prefix}origination/#match-{e(f.get("id"))}">Current card →</a>'
        else:
            status_note = ('Recorded as a lead only. The reviewed first-party ladder must replay it on a '
                           'later refresh before any pick changes; consult the current match card, not this dated lead.')
            if str(f.get('id')) in current_rows:
                link += f'<a class="internal-link" href="{prefix}origination/#match-{e(f.get("id"))}">Current card →</a>'
            elif f.get('hotspawn_url'):
                link += external(f['hotspawn_url'], 'Hotspawn fixture')
        lead_rows += (f'<li class="line-source-row"><span class="tried-chip resolved">dated lead</span>'
                      f'<strong>{e(" vs ".join(f.get("teams") or []))}</strong> '
                      f'<span class="line-source-note">{detail} · {status_note}</span>{link}</li>')
    leads_html = f'<ul class="line-source-list">{lead_rows}</ul>' if lead_rows else '<p class="tiny">No new money-line lead was found for any of them on that sweep.</p>'
    return ('<div class="line-sources" id="no-line-research">'
            '<h3>Fixtures without a betting line — latest dated research</h3>'
            f'<p class="tiny">On {local_time(record.get("observed_at"))} every fixture then carrying only a '
            f'research-model pick (<strong>{len(fixtures)}</strong>) was re-researched in brief order: '
            'HLTV first (identity/ranking; it publishes no two-sided price and answered the runner with a '
            'Cloudflare 403), then GG.BET, BetBoom, Stake, BC.Game, 1xBet, Marathonbet, Betway, DraftKings, '
            'OddsPortal, EGamersWorld, the Pinnacle guest board and the bo3.gg bookmaker relay. '
            f'<strong>{len(leads)}</strong> new money-line lead(s) found; the rest had no two-sided prematch '
            'price on any reachable surface, so their model picks and limitations stand. '
            f'<a class="internal-link" href="{prefix}data/research/3016b0c6/line-source-research.md">Full dated record ↓</a> '
            f'<a class="internal-link" href="{prefix}data/research/3016b0c6/line-source-research.json">JSON ↓</a></p>'
            + leads_html + '</div>')


#: Session 4c972a51's dated runner sweep. The file is evidence, not a feed: it
#: records what each candidate source answered on one afternoon so the published
#: limitations can be reviewed instead of asserted.
SESSION_PROBE = Path('data/research/4c972a51/source-probe.json')

#: What a status code means for a reader. Never a price, never a probability.
_STATUS_MEANING = {
    200: 'answered',
    203: 'challenge/redirect shell',
    401: 'credentials required',
    403: 'automated access refused',
    404: 'page not found',
    410: 'page permanently removed',
    429: 'rate-limited',
    503: 'service unavailable',
}


def _status_chip(status, error=None) -> str:
    if status == 200:
        return '<span class="tried-chip resolved">200 · answered</span>'
    if status is None:
        return '<span class="tried-chip unresolved">no response</span>'
    meaning = _STATUS_MEANING.get(status, 'refused or unusable')
    return f'<span class="tried-chip unresolved">{e(status)} · {e(meaning)}</span>'


def session_probe_block(data, prefix):
    """The full, dated reachability matrix behind the unresolved limitations.

    Rendered from ``data/research/4c972a51/source-probe.json``: 49 independent
    surfaces grouped by how a price could legitimately be used, each with its
    own link and the status the GitHub runner received. It publishes no
    probability, no pick and no inference from a failed request; a 403 is
    reported as refused access, never as proof that no market exists.
    """
    probe = data.get('_session_probe') or {}
    surfaces = probe.get('surfaces') or []
    if not surfaces:
        return ''
    groups = [
        ('The exact endpoints the resolver calls', {'ladder'},
         'Probed with the same method and payload the four-hour pipeline uses. A green row means the '
         'ladder’s own source answered, not merely that its host is online.'),
        ('First-party esportsbooks & exchanges', {'book', 'exchange'},
         'A bookmaker price is the first choice; only a two-sided prematch line can become a pick.'),
        ('Aggregators & odds comparisons', {'aggregator'},
         'An aggregator is a cross-check unless it publishes its own two-sided price.'),
        ('Identity, ratings & results', {'ratings'},
         'These sources can identify a fixture or feed a research model; none of them publishes a price.'),
    ]
    answered = [s for s in surfaces if s.get('status') == 200]
    refused = [s for s in surfaces if s.get('status') != 200]
    hltv = [s for s in surfaces if str(s.get('name', '')).startswith('hltv')]
    hltv_blocked = [s for s in hltv if s.get('status') != 200]
    html_shells = [s for s in answered
                   if s.get('kind') in {'book', 'exchange'} and (s.get('bytes') or 0) < 90_000
                   and 'json' not in str(s.get('content_type') or '').lower()]
    body = []
    for title, kinds, note in groups:
        rows = []
        for s in surfaces:
            if s.get('kind') not in kinds:
                continue
            name = s.get('name')
            url = s.get('url')
            detail = []
            if s.get('bytes') is not None:
                detail.append(f"{int(s['bytes']):,} bytes")
            if s.get('json_items'):
                detail.append(f"{s['json_items']} JSON items")
            elif s.get('json_keys'):
                detail.append('JSON keys: ' + ', '.join(s['json_keys'][:4]))
            if s.get('teams_present'):
                detail.append('mentions ' + ', '.join(s['teams_present'][:3]))
            if s.get('error'):
                detail.append(str(s['error'])[:120])
            rows.append(
                f'<li class="probe-source"><div class="probe-source-head">'
                f'<a class="source-link" href="{e(url)}" target="_blank" rel="noopener noreferrer">'
                f'{e(name)}{icon("external")}</a>{_status_chip(s.get("status"), s.get("error"))}</div>'
                f'<p class="probe-source-url">{e(url)}</p>'
                f'<p class="probe-source-detail">{e(" · ".join(detail)) if detail else "no detail recorded"}</p></li>')
        if not rows:
            continue
        body.append('<h3>' + e(title) + '</h3>'
                    f'<p class="tiny muted">{e(note)}</p>'
                    '<ul class="probe-source-list">' + ''.join(rows) + '</ul>')
    if not body:
        return ''
    observations = []
    if hltv:
        observations.append(
            f'HLTV was tried first, as the brief asks: <strong>{len(hltv_blocked)} of {len(hltv)}</strong> '
            'HLTV paths refused the automated request. HLTV publishes no prematch price even when a person '
            'can read it, so it is used for fixture identity and its published ranking only — never as a '
            'probability or a betting line in itself.')
    if html_shells:
        observations.append(
            f'<strong>{len(html_shells)}</strong> of the bookmaker pages that answered HTTP 200 returned a '
            'script shell with no match list in the HTML, so they yield no price without a documented API.')
    observations.append(
        f'<strong>{len(answered)}</strong> of <strong>{len(surfaces)}</strong> surfaces answered HTTP 200; '
        f'<strong>{len(refused)}</strong> refused, disappeared, were rate-limited or timed out. A refusal is '
        'recorded as a source limitation and never as evidence that no market exists.')
    if probe.get('unresolved_fixtures') == 0:
        observations.append(
            'This sweep ran when every active fixture already had a pick, so the source matrix below is a '
            'standing capability check rather than a list of blockers for one match.')
    return ('<section class="content-section session-probe" id="source-matrix" '
            'aria-labelledby="source-matrix-title">'
            '<div class="section-heading"><div><p class="eyebrow">Dated evidence · read-only</p>'
            '<h2 id="source-matrix-title">Sources checked, and what each one answered</h2></div>'
            f'<a class="internal-link" href="{prefix}data/research/4c972a51/source-probe.json">Raw probe (JSON) ↓</a></div>'
            f'<p class="section-intro">Every independent surface the resolver can reach, probed from the same '
            f'GitHub runner that publishes this site at {local_time(probe.get("observed_at"))}. '
            f'The probe writes status codes and excerpts only — it can never publish a probability. '
            'No access control was bypassed.</p>'
            '<ul class="probe-observations">'
            + ''.join(f'<li>{line}</li>' for line in observations)
            + '</ul>' + ''.join(body) + '</section>')


def unresolved_page(data, prefix, now=None):
    """A dedicated, phone-first page for every fixture without a pick.

    The brief asks for a separate section for unresolved picks and the
    limitations of generating them. The executive summary keeps its compact
    register; this page is the full, linkable destination: the live count, every
    blank with its blockers, the picks that rest on a research model rather than
    a betting line, and the dated source matrix behind all of it.
    """
    complete = data.get('complete_picks') or {}
    cc = complete.get('counts') or {}
    counts = data.get('counts') or {}
    active = cc.get('active', counts.get('upcoming', 0))
    with_pick = cc.get('with_pick')
    resolved = cc.get('resolved')
    unresolved = cc.get('unresolved', counts.get('unresolved', 0))
    no_side = max(0, (resolved or 0) - (with_pick or 0)) if resolved is not None else 0
    observed = complete.get('generated_at') or data.get('generated_at')
    if unresolved == 0 and no_side == 0:
        headline = f'Every one of the {active} active Hotspawn CS2 fixtures has a pick'
        lede = ('Nothing is blank in this snapshot. The sections below stay published so the method and the '
                'source limitations can be reviewed before a fixture ever needs them.')
    else:
        headline = f'{unresolved} fixture(s) without a pick, {no_side} without a side'
        lede = ('These are the matches the ladder could not price from a betting line or a rating. Each one '
                'carries the exact blocker and the sources that were actually tried.')
    cards = [
        ('Active fixtures', active, 'Hotspawn CS2 matches open, locked or with an unverified start'),
        ('With a pick', with_pick if with_pick is not None else max(0, active - unresolved),
         'A directional team plus both win probabilities'),
        ('No pick', unresolved, 'No compliant input survived the ladder — listed below'),
        ('No side', no_side, 'Probabilities published, but exactly even and no published order to break it'),
    ]
    card_html = ''.join(
        f'<div class="metric-card"><div class="metric-top">{e(label)}</div>'
        f'<strong>{e(value)}</strong><p>{e(note)}</p></div>' for label, value, note in cards)
    out = heading('Coverage gaps & limits', 'Unresolved picks & limitations',
                  'What is missing, why it is missing, and what was tried. Read this before treating any blank as a no-market signal.')
    out += (f'<p class="page-description" id="unresolved-status"><strong>{e(headline)}.</strong> {e(lede)} '
            f'Snapshot observed {local_time(observed)}.</p>')
    out += f'<div class="metrics unresolved-metrics">{card_html}</div>'
    out += ('<div class="limitations-callout" id="how-to-read"><strong>How to read this page</strong>'
            '<ul><li><strong>No pick</strong> means no compliant input produced a number. A blank is never '
            'replaced with a default 50/50.</li>'
            '<li><strong>No side</strong> means both probabilities are published and exactly even; the pick '
            'column shows “Even” unless the ranking provider itself orders the two teams.</li>'
            '<li><strong>Model-only</strong> means the number comes from a labelled research model, not from a '
            'bookmaker. It is a pick, but it is not a betting line.</li>'
            '<li>Every four-hour refresh retries every source. A fixture listed here can gain a market later; '
            'reload rather than treating this page as permanent.</li></ul></div>')
    out += unresolved_register(data, prefix, title='Every fixture without a pick, and why')
    out += session_probe_block(data, prefix)
    out += ('<section class="content-section prose" id="ladder"><p class="eyebrow">Our method, in order</p>'
            '<h2>What has to fail before a match is published as unresolved</h2>'
            '<ol class="ladder-list">'
            '<li><strong>Featured exact-name market</strong> — Polymarket series-winner order books, both sides, '
            'fresh and inside the spread ceiling.</li>'
            '<li><strong>Other first-party exchanges and books</strong> — Kalshi match-winner books, Thunderpick '
            'paired prices, Bovada and Pinnacle series moneylines.</li>'
            '<li><strong>Relayed bookmaker quote</strong> — a two-sided price published by bo3.gg, labelled as a '
            'relay and only used when no first-party quote exists.</li>'
            '<li><strong>Aggregated reference</strong> — a dated, reviewed bookmaker-average capture.</li>'
            '<li><strong>Valve official rating model</strong> — complete five-player rows from Valve’s published '
            'regional standings; uncalibrated, labelled.</li>'
            '<li><strong>Own results model</strong> — a Bradley–Terry fit over finished bo3.gg series, anchored on '
            'Valve points, failing closed on thin graphs.</li>'
            '<li><strong>HLTV world-ranking model</strong> — the published weekly points through a 400-scale '
            'logistic transform; unranked sides get HLTV’s floor and an explicit low-confidence label.</li>'
            '<li><strong>Wide-book guidance</strong> — a midpoint of a book too wide to accept, badged as guidance '
            'and never counted as money-backed.</li>'
            '<li><strong>Unresolved</strong> — the honest blank, with the blocker and the sources tried.</li>'
            '</ol>'
            '<p>When a research model lands on exactly 50/50, the pick is set by the ranking provider’s own '
            'published order (for example HLTV rank 215 vs 229) and the row says so. That rule changes the '
            'direction only — never a probability.</p>'
            f'<p><a class="internal-link" href="{prefix}methodology/">Full methodology →</a> '
            f'<a class="internal-link" href="{prefix}coverage/">Source status &amp; refresh →</a> '
            f'<a class="internal-link" href="{prefix}origination/#picks">All match picks →</a></p></section>')
    return out


def unresolved_register(data, prefix, title='Unresolved picks &amp; limitations'):
    """A separate, phone-first register of every fixture without a pick.

    The brief asked for the unresolved picks and their limitations to be a
    section of their own inside the executive summary, not a footnote. This
    renderer reads only the published research trail: it never re-prices a
    row, never averages a rejected book and never converts a missing value
    into a default 50/50.
    """
    complete = data.get('complete_picks') or {}
    if complete.get('matches') is not None:
        rows = [m for m in (complete.get('matches') or []) if m.get('origination') is None]
        # A resolved-but-even estimate has a probability pair but no side. It is a
        # pick-less fixture too, so it belongs in this register: the brief asks for
        # every match to show either a pick or an explicit limitation.
        no_side = [m for m in (complete.get('matches') or [])
                   if m.get('origination') is not None and m.get('pick_index') is None]
    else:
        # The featured-only fallback exists for a site built without the complete
        # researched list. It must NOT run when that list exists and resolved every
        # fixture: doing so showed featured-method rejections as "unresolved" beside
        # a summary that said every fixture had a pick (session 541cd43a).
        rows = [m for m in data.get('matches') or []
                if m.get('availability') in {'open', 'locked', 'unknown_lock'} and not m.get('analysis')]
        no_side = []
    total_pickless = len(rows) + len(no_side)
    active = (complete.get('counts') or {}).get('active') or data.get('counts', {}).get('upcoming')
    out = ['<section class="content-section unresolved-register" id="unresolved-register" '
           'aria-labelledby="unresolved-register-title">'
           '<div class="section-heading"><div><p class="eyebrow">Separate register · no guesswork</p>'
           f'<h2 id="unresolved-register-title">{title}</h2></div>'
           f'<a class="internal-link" href="{prefix}origination/#unresolved">Full research trails {icon("arrow")}</a></div>']
    if not total_pickless:
        closed = [m for m in (complete.get('matches') or []) if m.get('featured_method') is None and m.get('origination') is not None]
        extra = ''
        if closed:
            # Session fbdc97d6: this sentence used to claim every featured blank
            # had been resolved by one "verified Thunderpick paired-price book".
            # The published data says otherwise (Kalshi, Valve ratings, the
            # bo3.gg results network, the HLTV ranking), so the provenance is
            # now read from each row instead of being hard-coded.
            counts = {}
            items = []
            for m in closed:
                n = [t.get('name') or 'Unverified' for t in m.get('teams') or []]
                label, source, url = researched_method(m)
                counts[label] = counts.get(label, 0) + 1
                link = (f'<a class="source-link" href="{e(url)}" target="_blank" rel="noopener noreferrer">'
                        f'{e(source)}{icon("external")}</a>' if url else '')
                items.append(f'<li><a class="internal-link" href="{prefix}origination/#match-{e(m.get("id"))}">'
                             f'{e(n[0])} vs {e(n[1])}</a> <span class="method-note">· {e(label)}</span> {link}</li>')
            summary = ', '.join(f'{count} from {label}' for label, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])))
            money_methods = {'market', 'bookmaker', 'consensus', 'reference'}
            kinds = {(m.get('origination') or {}).get('method') in money_methods for m in closed}
            if kinds == {True}:
                nature = ('These are external money lines — one provider each unless a row says it is a median of '
                          'independent sources — never a multi-book consensus.')
            elif kinds == {False}:
                nature = ('These are labelled research estimates, not bookmaker lines: no reachable book priced these '
                          'fixtures at the observation time.')
            else:
                nature = ('These are a mix of external money lines and labelled research estimates; each row states '
                          'which one it is.')
            extra = (f'<p class="tiny" style="margin-top:10px">In this snapshot the featured exact-name method left '
                     f'<strong>{len(closed)}</strong> fixture(s) without a pick. Each now carries a researched estimate '
                     f'from a named source, read from the published rows: <strong>{e(summary)}</strong>. {nature} '
                     'Every figure keeps its own source and limitation on the origination card. No line is invented.</p>'
                     '<ul class="researched-methods">' + ''.join(items) + '</ul>')
        out.append('<div class="ok-note"><strong>No unresolved fixtures in this snapshot.</strong> '
                   f'All {active} active Hotspawn CS2 fixtures carry a sourced estimate as of '
                   f'{local_time(complete.get("generated_at") or data.get("generated_at"))}. '
                   'This is a dated observation: the inventory refreshes every four hours and new '
                   'fixtures can appear before a market opens.</div>' + extra)
    else:
        parts = []
        if rows:
            noun = 'fixture' if len(rows) == 1 else 'fixtures'
            parts.append(f'<strong>{len(rows)}</strong> {noun} with <strong>no verified pick</strong>')
        if no_side:
            noun = 'estimate' if len(no_side) == 1 else 'estimates'
            parts.append(f'<strong>{len(no_side)}</strong> {noun} with probabilities but <strong>no side</strong>')
        out.append('<p class="section-intro">' + ' and '.join(parts) + f', out of {active} active Hotspawn CS2 '
                   'fixtures in this snapshot. Each card names the blocker and links the sources actually '
                   'tried. A blank stays blank; an unavailable source is never treated as proof that no '
                   'market exists, and an even estimate is never given an invented side.</p>')
        out.append('<ul class="unresolved-summary-list">')
        for m in rows + no_side:
            even = m.get('origination') is not None
            names = [t.get('name') or 'Unverified team' for t in m.get('teams') or []]
            trail = [r for r in m.get('research') or [] if r.get('stage') != 'Origination result']
            tried = []
            seen = set()
            for r in trail:
                label = str(r.get('stage') or '')
                key = (label, r.get('status'))
                if key in seen:
                    continue
                seen.add(key)
                tried.append(f'<span class="tried-chip {e(r.get("status") or "unknown")}">'
                             f'{e(label)} · {e(r.get("status") or "unknown")}</span>')
            source_links = external(m.get('source_url') or 'https://play.hotspawn.com/lobby', 'Hotspawn fixture')
            used = {m.get('source_url')}
            for r in trail:
                url = str(r.get('source_url') or '')
                if not url.startswith('https://') or url in used:
                    continue
                used.add(url)
                host = 'HLTV' if 'hltv.org' in url else 'Valve' if 'ValveSoftware' in url else 'Source'
                source_links += external(url, host)
                if len(used) >= 4:
                    break
            tried_html = ''.join(tried) or '<span class="tried-chip unresolved">No source returned a usable pair</span>'
            badge_text = 'Even estimate · no side' if even else 'No verified pick'
            if even:
                reason = 'Equal estimate: no side is supportable at these prices'
            else:
                reason = _brief_blank_reason(m)
            out.append(f'<li class="unresolved-summary-card{" is-even" if even else ""}" id="unresolved-summary-{e(m.get("id"))}">'
                       f'<div class="unresolved-summary-head"><span class="comp">{e(m.get("competition") or "Unverified tournament")}</span>'
                       f'<span class="badge {"neutral" if even else "amber"}">{e(badge_text)}</span></div>'
                       f'<h3>{e(names[0])} <span class="versus">vs</span> {e(names[1])}</h3>'
                       f'<p class="unresolved-when">{local_time(m.get("starts_at"))} · '
                       f'<strong>{e(reason)}</strong></p>'
                       f'<div class="unresolved-tried">{tried_html}</div>'
                       f'<p class="unresolved-links">{source_links}'
                       f'<a class="internal-link" href="{prefix}origination/#match-{e(m.get("id"))}">Full trail {icon("arrow")}</a></p>'
                       '</li>')
        out.append('</ul>')
    out.append(no_line_register(data, prefix))
    out.append(source_probe_block(data, prefix))
    out.append(line_sources_block(data, prefix))
    out.append(no_line_research_block(data, prefix))
    out.append('<div class="limitations-callout unresolved-limits"><strong>Limitations that apply to every row above</strong>'
               '<ul>'
               '<li>Only a two-sided first-party price or official rating can produce a number. Hotspawn '
               'participation percentages and HLTV “Pick a winner” fan votes are never inputs.</li>'
               '<li>Thin or wide books are recorded for guidance but rejected as picks; an outage or a 403 is '
               'not evidence that no market exists.</li>'
               '<li>Display names are joined only through the reviewed alias registry; unregistered names stay unmatched.</li>'
               '<li>The Valve-rating fallback is explicitly uncalibrated and is used only when no money source resolves a fixture.</li>'
               '<li>Every four-hour refresh retries all sources, so this register shrinks when a market opens — '
               'reload the page rather than treating this list as permanent.</li>'
               '</ul></div></section>')
    return ''.join(out)


def summary(data, prefix, now=None):
    c = data['counts']
    active = [m for m in data['matches'] if m['availability'] in {'open', 'locked', 'unknown_lock'}]
    complete = data.get('complete_picks')
    cc = complete['counts'] if complete else None
    total = cc['active'] if cc else c['upcoming']
    resolved = cc['resolved'] if cc else c['upcoming'] - c['unresolved']
    money = (cc['market'] + cc['bookmaker'] + cc['consensus'] + cc.get('reference', 0)) if cc else (c['market'] + c['bookmaker'] + c.get('reference', 0))
    models = cc['model'] if cc else c['model']
    guidance = cc.get('guidance', 0) if cc else 0
    unresolved = cc['unresolved'] if cc else c['unresolved']
    p = round(100 * resolved / total) if total else 0
    ring = f'<div class="coverage-dial"><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="50" class="dial-track"/><circle cx="60" cy="60" r="50" class="dial-progress" stroke-dasharray="{p * 3.14159:.3f} 314.159"/></svg><div><strong>{resolved}<span>/{total}</span></strong><small>with probabilities</small></div></div>'
    out = heading('Counter-Strike 2 intelligence', 'Executive summary', 'Every Hotspawn CS2 fixture, independently researched. Your picks are one tap away.')
    # Session f60683a4: the glance index itself has to sit above the fold on a
    # phone (Playwright 320/390). The jump bar leads; the banner of extra
    # destinations follows the picks so #picks-at-a-glance is not buried
    # under three stacked 44px action rows.
    out += start_here(data, prefix)
    out += glance(data, prefix, now=now)
    out += exec_banner(data, prefix)
    out += unresolved_register(data, prefix)
    if complete:
        if not data['coverage_complete']:
            coverage_label = 'Picks in the retained snapshot'
        elif cc['active'] == 0:
            coverage_label = 'No active matches in this snapshot'
        elif cc['unresolved'] == 0 and cc['resolved'] == cc['active'] and cc['with_pick'] == cc['active']:
            coverage_label = 'Directional picks for every active match'
        elif cc['unresolved'] == 0 and cc['resolved'] == cc['active']:
            coverage_label = 'Win probabilities for every active match'
        elif cc['unresolved'] > 0:
            coverage_label = 'Pick coverage &amp; unresolved matches'
        else:
            coverage_label = 'Pick coverage needs reconciliation'
        no_direction = cc['resolved'] - cc['with_pick']
        if no_direction == 1:
            direction_note = ' 1 resolved estimate has no directional pick.'
        elif no_direction > 1:
            direction_note = f' {no_direction} resolved estimates have no directional pick.'
        else:
            direction_note = ''
        blanks = [m for m in (complete.get('matches') or []) if m.get('origination') is None]
        blank_line = ''
        if blanks:
            items = []
            for m in blanks[:8]:
                names = [t.get('name') or 'Unverified team' for t in (m.get('teams') or [])]
                items.append(f'<a class="internal-link" href="{prefix}origination/#match-{e(m["id"])}">'
                             f'{e(names[0])} vs {e(names[1])}</a> <span class="tiny muted">({e(_brief_blank_reason(m))})</span>')
            more = f' <span class="tiny muted">+{len(blanks) - len(items)} more in the full list</span>' if len(blanks) > len(items) else ''
            blank_line = ('<p class="tiny"><strong>No pick yet (' + str(len(blanks)) + '):</strong> '
                          + ' · '.join(items) + more + '. Every blank carries its source trail and the exact reason; '
                          'an unavailable source is never treated as proof that no market exists.</p>')
        guidance_note = f', {guidance} wide-book guidance' if guidance else ''
        out += (f'<section class="limitations-callout" id="picks-status" aria-label="Complete pick coverage">'
                f'<h2>{coverage_label}: {cc["with_pick"]} / {cc["active"]}</h2>'
                f'<p>{cc["resolved"]} with probabilities ({money} external-line, {models} research-model{guidance_note}); '
                f'{cc["unresolved"]} unresolved in the complete researched list.{direction_note} '
                f'Estimate snapshot: {local_time(complete["generated_at"])}.</p>'
                + blank_line +
                f'<p><a class="internal-link" href="{prefix}origination/#picks">All matches, both probabilities &amp; picks →</a> '
                f'<a class="internal-link" href="{prefix}origination/#unresolved">Unresolved picks &amp; limitations →</a> '
                f'<a class="internal-link" href="{prefix}twc-picks/#day-five-picks">Day 5 final-day picks →</a> '
                f'<a class="internal-link" href="{prefix}review/">Review flags →</a> '
                f'<a class="internal-link" href="#contrarian">Day-one review →</a></p></section>')
    out += f'<section class="hero" aria-labelledby="briefing-title"><div class="hero-copy"><span class="hero-kicker"><span class="status-dot"></span>{({"complete": "FULL INVENTORY RECONCILED", "partial": "FULL API INVENTORY · ONE LOBBY PAGE UNREADABLE", "unavailable": "FULL API INVENTORY · LOBBY HTML CROSS-CHECK UNAVAILABLE"}.get(data.get("inventory_crosscheck", "complete"), "FULL API INVENTORY · HTML CROSS-CHECK UNAVAILABLE")) if data["coverage_complete"] else "INVENTORY NOT VERIFIED"}</span><h2 id="briefing-title">All the matches.<br>One clear view.</h2><p><strong>{total} active fixtures.</strong> {money} external-line estimates, {models} research-model estimates{f", {guidance} wide-book guidance" if guidance else ""}, and {unresolved} unresolved in the complete list. No Hotspawn popularity scores. No made-up odds.</p><div class="hero-actions"><a class="button primary" href="{prefix}origination/#picks">See all match picks {icon("arrow")}</a><a class="hero-secondary" href="{prefix}strategy/">Leaderboard plan →</a><a class="hero-secondary" href="#unresolved">Unresolved &amp; limitations ↓</a><a class="hero-secondary" href="{prefix}twc-picks/">TWC Day 5: picks &amp; review →</a><a class="hero-secondary" href="{prefix}edge/#day-five-card">Day 5 final-day picks →</a></div></div>{ring}</section>'
    out += '<nav class="briefing-links" aria-label="Briefing shortcuts"><a href="' + prefix + 'origination/#picks">Full updated picks</a><a href="' + prefix + 'strategy/">Leaderboard plan</a><a href="' + prefix + 'final-day/">Final day review</a><a href="#next-matches-section">Next matches</a><a href="#contrarian">Contrarian review</a><a href="' + prefix + 'edge/">Upset review &amp; edge</a><a href="' + prefix + 'edge/#day-five-card">Day 5 final-day picks</a><a href="' + prefix + 'twc-picks/">Day 5 pick guide</a><a href="#upset-watchlist">Market-backed alternatives</a><a href="#unresolved">Unresolved &amp; limitations</a></nav>'
    if data.get('_twc_day5') is not None:
        from scripts.day5 import summary as final_day_summary
        out += final_day_summary(data['_twc_day5'], prefix)
    day4 = data.get('_twc_day4')
    if day4 is not None:
        confirmed = len(day4['matches'])
        unresolved4 = sum(not r['analysis'] for r in day4['matches'])
        pending = len(day4['not_in_hotspawn_snapshot'])
        lines4 = day4.get('lines') or {}
        if lines4.get('available'):
            line_note = (f'{lines4["resolved"]} of {lines4["total"]} tournament-card fixture(s) priced from external '
                         'Polymarket/Kalshi books; the rest stay blank with their observed reason.')
        else:
            line_note = ('No retained external tournament-card book yet, so those playoff probabilities stay blank '
                         'rather than guessed.')
        inventory_scope = ('in the last reconciled Hotspawn snapshot' if data['coverage_complete']
                           else 'in the retained Hotspawn snapshot; current coverage is unverified')
        tournament_link = (f'<a href="{prefix}twc-picks/#day-four-tournament-lines">Tournament-card lines →</a> '
                           if pending else '')
        out += (f'<section class="limitations-callout" aria-label="TWC Day 4 coverage"><h2>TWC final day · where the picks are</h2>'
                f'<p><a href="{prefix}edge/#day-five-card"><strong>Day-5 final-day picks (Sun 18 Oct) →</strong></a> '
                f'<a href="{prefix}edge/#day-five-guidance">Days 1–4 reviewed → final-day strategy →</a> '
                f'<a href="{prefix}edge/#day-five-market-scan">Final-day prices, sources &amp; rejected lines →</a></p>'
                f'<p>{confirmed} playoff fixture(s) {inventory_scope}; {unresolved4} without a supported estimate. '
                f'{pending} HLTV listing(s) not uniquely matched to that inventory. Unconfirmed opponents, lock times and prices stay blank; '
                'a tournament listing is not silently treated as a weekly lobby fixture. '
                f'{line_note} '
                f'<a href="{prefix}twc-picks/#day-four-picks">Day 4 picks &amp; fixture limitations →</a> '
                f'{tournament_link}'
                f'<a href="{prefix}twc-picks/#day-three-results">Day 3 source-checked results →</a></p></section>')
    if c['unknown_schedule']:
        out += f'<div class="limitations-callout"><strong>{c["unknown_schedule"]} additional matches have unverified schedules.</strong> They cannot safely be matched to betting lines and are not included in the future-match count. <a href="#unresolved">See unresolved schedules and limitations →</a></div>'
    out += '<p class="muted small">The metrics below describe the original featured method only. The next-match preview uses the same selected estimates as the complete list, including researched fallbacks. Featured observations remain available for audit.</p>'
    out += '<div class="metrics">'
    cards = [('Future matches', c['upcoming'], f'{c["inventory"]} source records · {c["archived"]} past starts', 'target', 'coverage/'), ('Featured market', c['market'] + c['bookmaker'], 'Original external market observations', 'layers', 'picks/?basis=market'), ('Featured model', c['model'], 'Valve ratings · higher uncertainty', 'book', 'picks/?basis=model'), ('Featured rejections', c['unresolved'], 'Check complete-list fallbacks above', 'flag', 'review/#unresolved')]
    for title, value, subtitle, sym, url in cards:
        out += f'<a class="metric-card" href="{prefix}{url}"><div class="metric-top"><span>{title}</span>{icon(sym)}</div><strong>{value:02d}</strong><p>{e(subtitle)}</p></a>'
    out += '</div>'
    out += '<section class="content-section"><div class="section-heading"><div><p class="eyebrow">The short version</p><h2>What to know before you pick</h2></div>' + badge('Read-only analysis', 'neutral') + '</div><div class="briefing-notes">'
    out += f'<div><span class="note-number">01</span><p><strong>Start with the full picks list.</strong> Both team probabilities, the suggested team, lock time and original evidence are shown together. {external(LOBBY, "Submit picks on Hotspawn")}</p></div><div><span class="note-number">02</span><p><strong>Know what backs the number.</strong> Green means an external market; purple means an uncalibrated rating model used only when the primary method failed. Neither is a guarantee.</p></div><div><span class="note-number">03</span><p><strong>Check the timestamp.</strong> Automatic checks are scheduled every four hours. GitHub may delay a run. After eight hours without a successful observation, the site warns you not to treat the snapshot as current.</p></div></div></section>'
    out += '<section class="content-section" id="next-matches-section"><div class="section-heading"><div><p class="eyebrow">On the radar</p><h2>Next matches</h2></div><a class="internal-link" href="' + prefix + 'origination/#picks">All match picks ' + icon('arrow') + '</a></div>'
    out += matches_table(active[:5], prefix, table_id='next-matches', fallbacks=data.get('fallbacks'), now=now) + '</section>'
    out += contrarian_review(data, prefix)
    out += '<section class="content-section" id="unresolved"><div class="section-heading"><div><p class="eyebrow amber-text">Coverage gaps, not hidden omissions</p><h2>Unresolved picks &amp; limitations</h2></div><a class="internal-link" href="' + prefix + 'review/">All review flags ' + icon('arrow') + '</a></div>'
    out += f'<p><a class="internal-link" href="{prefix}origination/#unresolved">Complete-list unresolved picks &amp; limitations →</a>. Original featured-method rejections remain in the <a class="internal-link" href="{prefix}review/#unresolved">audit register</a>; supported fallbacks may resolve them in the complete list.</p>'
    unresolved_data = {'matches': [dict(m, analysis=m['origination']) for m in complete['matches']]} if complete else data
    out += unresolved_table(unresolved_data, prefix)
    probe = data.get('coverage_probe') or {}
    if probe:
        pc = probe.get('counts') or {}
        blanks = pc.get('unresolved_fixtures') or 0
        lead = probe.get('headline') or (f'{blanks} blank fixture(s) documented')
        where = 'the GitHub runner' if probe.get('environment') == 'github-actions-runner' else 'a local checkout'
        detail = (f'{e(pc.get("with_provider_lead"))} of them have a provider listing that the strict join rejected for a '
                  f'named reason, and {e(pc.get("display_name_only"))} are blocked by display-name differences alone — the one '
                  'class of gap a reviewed alias can close, and the only class where a lead is published with the listing it came from.'
                  if blanks else
                  'The dossier is republished on every refresh, so a blank can never appear without a record beside it.')
        out += ('<div class="limitations-callout"><p class="eyebrow">Coverage probe · every blank, one by one</p>'
                f'<p><strong>{e(lead)}</strong> {detail} The dossier was written by the probe script against {where} at '
                f'{local_time(probe.get("generated_at"))} ({e(probe.get("mode"))}); it never writes a probability, a pick or an '
                'alias, and it does not overwrite the collector’s own reasons above.</p>'
                f'<p><a class="internal-link" href="{prefix}data/research/8fa2b226/coverage-probe.json">Full probe dossier (JSON) ↓</a>'
                + ''.join(f' <a class="source-link" href="{e(x.get("url"))}" target="_blank" rel="noopener noreferrer">{e(x.get("name"))}: {e(x.get("status"))}</a>'
                          for x in (probe.get('book_probes') or [])[:5])
                + ('' if (probe.get('book_probes') or []) else ' <span class="tiny muted">no endpoint probes in this mode</span>')
                + f'</p><p class="tiny">{e((probe.get("policy") or "")[:420])}</p>'
                + '<p class="tiny">' + e('; '.join((probe.get('limitations') or [])[:2])) + '</p></div>')
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
        ('Unresolved picks & limitations', 'unresolved/', 'Every active match without a pick, the exact blocker, every '
         'source tried, the dated reachability matrix and the order the resolver works through.', 
         f'{still_blank} without a pick · {with_pick} with a pick'),
        ('Leaderboard plan', 'strategy/', 'What to submit to climb the Hotspawn leaderboard: one plan pick per match, the few underdogs '
         'the lines say have a real shot, the points at stake, Hotspawn\'s scoring rules and the unresolved fixtures.',
         'Contrarian, not stupid'),
        ('TWC Day 5 picks & review', 'twc-picks/', 'Final-day probabilities, Days 1–4 results, canonical picks and separate tournament research with explicit source gaps.', 'No fan votes or narrative probability adjustments'),
        ('Final day review', 'final-day/', 'Days 1–4 read series by series with an official link per row, the verified Aurora roster timeline, the two 18 October fixtures, dated external line observations and the contrarian shortlist.', 'Dated research · read-only'),
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


def picks(data, prefix, now=None):
    c = data['counts']
    fallbacks = data.get('fallbacks') or {}
    active = [m for m in data['matches'] if m['availability'] != 'past']
    basis = [effective_basis(m, fallbacks) for m in active]
    shown = {'all': len(active),
             'market': sum(1 for b, _ in basis if b in ('market', 'bookmaker', 'consensus', 'reference')),
             'model': sum(1 for b, _ in basis if b == 'model'),
             'guidance': sum(1 for b, _ in basis if b == 'guidance'),
             'unresolved': sum(1 for b, _ in basis if b == 'unresolved')}
    researched = sum(1 for _, fb in basis if fb)
    with_pick = shown['all'] - shown['unresolved']
    out = heading('Every non-archived match', 'Match picks & probabilities', 'See both sides. Know the pick. Check the evidence. Full-series estimates only; no map, handicap or popularity-derived lines.', '<a class="button secondary" href="' + prefix + 'data/picks.csv">Download CSV ↓</a>')
    # Session 4c972a51: the sentence used to add the *featured* counts (11 money
    # + 12 researched) while the header counted every displayed row (33), so the
    # arithmetic did not add up and a reader could think ten matches had no pick.
    # Every number here now comes from the same displayed-basis tally the filter
    # chips use, and the parts always sum to `shown['all']`.
    out += (f'<div class="info-strip">{icon("check")}<span><strong>{with_pick} of {shown["all"]} matches below carry a pick.</strong> '
            f'{shown["market"]} come from an external market, esportsbook or aggregated bookmaker line'
            + (f', {shown["model"]} from a labelled research model, badged <strong>Research model</strong>' if shown["model"] else '')
            + (f', {shown["guidance"]} from wide-book guidance only' if shown['guidance'] else '')
            + f', and {shown["unresolved"]} remain blank because no supported evidence exists. '
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
    out += matches_table(active, prefix, filters=True, fallbacks=fallbacks, now=now) + '</section><div class="legend"><span>' + badge('Market-backed', 'green') + ' Independent external prices</span><span>' + badge('Research model', 'purple') + ' Uncalibrated rating estimate</span><span>' + badge('Researched fallback', 'purple') + ' Featured method rejected the fixture; audited research ladder produced this estimate</span><span>' + badge('Unresolved', 'amber') + ' No supported probability</span></div>'
    out += f'<p class="muted small">Showing future-start and unknown-schedule fixtures at the last inventory check. Past-start records remain available in the <a href="{prefix}coverage/#archive">complete source archive</a>. Fair decimal lines are calculated in each row’s evidence panel; they are not executable bookmaker quotes.</p>'
    out += '<section class="content-section" id="unresolved"><div class="section-heading"><div><p class="eyebrow amber-text">Every gap stays visible</p><h2>Unresolved picks &amp; limitations</h2></div><a class="internal-link" href="' + prefix + 'review/">All flagged findings →</a></div>' + unresolved_table(data, prefix) + '</section>'
    return out


def write_reconciled_snapshot(snapshot_path, data, out_path=None):
    """Publish featured-vs-researched count reconciliation without mutating latest.json.

    ``counts.*`` describes the featured exact-name method alone, while ``data/latest.json``
    must remain byte-for-byte identical to the canonical collector artifact attested by
    SHA-256 and ``tests/test_review_flags.py``. Writing ``data/reconciled-counts.json``
    publishes both count dictionaries side by side without rewriting ``latest.json``.
    """
    if not snapshot_path.exists() or not data.get('complete_picks'):
        return
    snapshot = json.loads(snapshot_path.read_text())
    cc = data['complete_picks'].get('counts') or {}
    featured = snapshot.get('counts') or {}
    reconciled = {
        'generated_at': snapshot.get('generated_at'),
        'inventory_observed_at': snapshot.get('inventory_observed_at'),
        'featured_method_counts': {
            k: featured.get(k) for k in
            ('upcoming', 'market', 'bookmaker', 'consensus', 'model', 'unresolved', 'picks')},
        'complete_coverage_counts': {
            k: (cc.get(k) or 0) for k in
            ('active', 'resolved', 'with_pick', 'market', 'bookmaker', 'consensus',
             'reference', 'model', 'guidance', 'unresolved')},
        'counts_note': (
            'counts.* and featured_method_counts describe the featured exact-name method only. '
            'complete_coverage_counts describe the researched list every page renders: one row per '
            'active Hotspawn fixture, with a market, bookmaker, consensus or reference price where one '
            'was found and a labelled research-model estimate where none was. A fixture is unresolved '
            'only when neither list can produce a number.'),
    }
    target = out_path if out_path is not None else snapshot_path.parent / 'reconciled-counts.json'
    target.write_text(json.dumps(reconciled, ensure_ascii=False, indent=2) + '\n')


def _reconciled(data):
    """One short, arithmetic-free sentence pointing at the researched list.

    The two lists disagree by design (the featured method is exact-name only);
    saying so in the same card stops a reader from reading the featured
    counters as the site's coverage.
    """
    cc = (data.get('complete_picks') or {}).get('counts') or {}
    if not cc:
        return ''
    return (f'; the researched list has {cc.get("with_pick", 0)} of {cc.get("active", 0)} '
            f'with a pick and {cc.get("unresolved", 0)} unresolved')


def coverage(data, prefix, now=None):
    c = data['counts']
    out = heading('Nothing quietly left out', 'Coverage & original sources', 'Inventory coverage and probability coverage are different. This page reconciles both, and keeps past-start source anomalies visible.')
    out += f'<div class="coverage-summary"><div><span class="eyebrow">Source inventory</span><strong>{c["inventory"]} / {c["inventory"] if data["coverage_complete"] else "?"}</strong><p>{("CS2 records reconciled across three official responses" if data.get("inventory_crosscheck", "complete") == "complete" else "CS2 records from the official fixture API; lobby HTML cross-check " + ("partial" if data.get("inventory_crosscheck") == "partial" else "unavailable")) if data["coverage_complete"] else "Complete current coverage is unverified"}</p></div><div><span class="eyebrow">Future probabilities</span><strong>{c["upcoming"] - c["unresolved"]} / {c["upcoming"]}</strong><p>{c["market"] + c["bookmaker"]} market · {c.get("reference", 0)} aggregated · {c["model"]} model · {c["unresolved"]} unresolved in the featured method{_reconciled(data)}</p></div><div><span class="eyebrow">Automatic refresh</span><strong>4 hours</strong><p>Primary target: 00:17, 04:17, 08:17, 12:17, 16:17, 20:17 UTC. Catch-up slots: 02:47, 06:47, 10:47, 14:47, 18:47, 22:47 UTC. GitHub may delay or drop runs; source access can fail. Not a real-time feed. <a href="{REPO}/blob/main/.github/workflows/pages.yml">Official refresh workflow →</a></p></div></div>'
    out += ('<section class="content-section" id="hotspawn-integration"><div class="section-heading"><div>'
            '<p class="eyebrow">Reverse-engineered, read-only</p><h2>How the Hotspawn list is read</h2></div>'
            '<a class="internal-link" href="' + prefix + 'data/evidence/hotspawn-context.json">Reconciliation record ↓</a></div>'
            '<div class="resolution-steps" style="padding-top:0">'
            '<article class="resolution-step"><span>A</span><div><h2>Authoritative fixture array</h2>'
            '<p>The same public scheduled-fixture API that feeds Hotspawn\u2019s own client is the inventory of record. '
            'Every CS2 record in it is kept \u2014 upcoming, past-start and unknown-schedule alike \u2014 so newly listed matches appear on the next successful refresh.</p>'
            + external('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1', 'Original fixture API') + '</div></article>'
            '<article class="resolution-step"><span>B</span><div><h2>Two rendered pages cross-check it</h2>'
            '<p>Both public lobby pages embed the fixture list in an Angular hydration block (<code>ng-state</code>). The collector reads that block from each page and requires the same unpaginated ID set as the API. '
            'A readable page that disagrees fails the refresh closed; when no page can be read the API array is published with an explicit \u201cunavailable\u201d cross-check marker instead of a reconciliation claim. '
            'A cache-busting query string requests a fresh server render because the CDN can serve stale HTML.</p>'
            + external(LOBBY, 'Official lobby') + ' ' + external('https://play.hotspawn.com/cs2-pickems', 'Official CS2 lobby') + '</div></article>'
            '<article class="resolution-step"><span>C</span><div><h2>Fail-closed contract</h2>'
            '<p>Duplicate IDs, an empty array or a changed schema invalidates the refresh \u2014 it is never accepted as an empty or partial feed. '
            'Picks lock 5 minutes before each fixture\u2019s scheduled start per Hotspawn\u2019s own rules page; per-fixture lock timestamps take precedence on this dashboard.</p>'
            + external('https://play.hotspawn.com/how-it-works', 'Hotspawn lock rules for manual review') + '</div></article>'
            '<article class="resolution-step"><span>D</span><div><h2>4\u20138 hour freshness bound</h2>'
            '<p>Primary refresh slots run every four hours with catch-up slots 2.5 hours later, so one dropped run still leaves data inside the eight-hour bound. '
            'After eight hours without a successful observation the site warns against treating the snapshot as current, and original timestamps are never restamped.</p>'
            f'<a href="{REPO}/blob/main/.github/workflows/pages.yml">Official refresh workflow \u2192</a></div></article>'
            '</div></section>')
    out += '<section class="content-section"><div class="section-heading"><div><p class="eyebrow">First-party checks</p><h2>Source health</h2></div><a class="internal-link" href="' + prefix + 'data/sources.json">Request manifest ↓</a></div><div class="table-scroll"><table class="simple-table source-table"><caption class="sr-only">Latest source attempts, outcomes and limitations</caption><thead><tr><th>Original source</th><th>Status / observed</th><th>What was actually confirmed</th></tr></thead><tbody>'
    for s in data['sources']:
        out += '<tr><th scope="row">' + external(s['url'], s['name']) + '</th><td>' + badge('Available' if s['status'] == 'ok' else 'Limited / unavailable', 'green' if s['status'] == 'ok' else 'amber') + '<small>' + local_time(s['observed_at']) + '</small></td><td>' + e(s['detail']) + (f'<small>{s["records"]} structured records</small>' if s['records'] is not None else '') + '</td></tr>'
    out += '</tbody></table></div></section><section class="content-section"><div class="section-heading"><div><p class="eyebrow">Reproducible, not just plausible</p><h2>Verification ledger</h2></div></div><div class="table-scroll"><table class="simple-table"><caption class="sr-only">Automated inventory and calculation verification</caption><thead><tr><th>Check</th><th>Published result</th><th>Original source / evidence</th></tr></thead><tbody>'
    inventory_ledger = (f'{c["inventory"]} unique CS2 IDs in the last reconciled snapshot.'
                        if data['coverage_complete'] else
                        f'Retained snapshot only: {c["inventory"]} CS2 IDs; current coverage is unverified.')
    ledger = [('Fixture identity reconciliation', inventory_ledger, 'https://play.hotspawn.com/cs2-pickems', 'Hotspawn CS2 lobby'), ('Line-by-line facts', 'Every match ID, team, competition, schedule, explicit lock, format and source status is replayed against saved source JSON.', 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1', 'Original fixture API'), ('Probability calculations', 'Every output probability, fair line and selected team is recalculated. Unknown inputs cannot become a pick.', 'https://docs.polymarket.com/api-reference/market-data/get-order-book', 'Official order book contract'), ('Rating input integrity', 'Model points and rosters are reparsed from original Valve markdown and checked against its Git blob SHA.', 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'Valve official repository')]
    for title, detail, url, label in ledger:
        if title == 'Fixture identity reconciliation':
            detail = e(detail) + ' Inventory observed: ' + local_time(data.get('inventory_observed_at'))
        else:
            detail = e(detail)
        out += f'<tr><th scope="row">{e(title)}</th><td>{detail}</td><td>{external(url, label)}</td></tr>'
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
        out += '<section class="content-section" id="unknown-schedules"><h2>Unverified schedules</h2>' + matches_table(unknown, prefix, table_id='unknown-schedules', now=now) + '</section>'
    return out


def methodology(data, prefix):
    out = heading('A number needs a reason', 'How we resolve a pick', 'Source facts stay separate from analysis. No Hotspawn community percentage, popularity, score or Pick’em point multiplier enters a probability calculation.')
    steps = [('01', 'Verify the full match inventory', 'Read the public lobby, CS2 lobby and the same public fixture array used by Hotspawn’s client. Reconcile every CS2 ID. Keep old or inconsistent records in the archive rather than dropping them.', LOBBY, 'Official lobby'), ('02', 'Use the primary external market', 'Discover CS2 games from Polymarket’s directory and paginate its official CS2-tag event API to a terminal page. A repeated page, schema change, access failure or the bounded 2,000-event limit is published as a discovery limitation. Confirm the event, exact two team names, start time within 60 seconds, unique active series moneyline, accepting-orders state, token IDs and condition ID. Read both original order books. No map or handicap markets.', 'https://docs.polymarket.com/api-reference/market-data/get-order-book', 'Official order book documentation'), ('03', 'Research only primary-method gaps', 'For those matches only, try HLTV’s official match directory, then original esportsbook lines. HLTV’s sibling time/team cards are replayed from saved original markup; differing provider names stay flagged, not silently aliased. Thunderpick, Bovada and Pinnacle have paired-price adapters — Pinnacle through its own public guest market board, two-way series period 0 only, with “Yes/No”, “Odd/Even” and score-grid specials rejected by participant text. GG.BET, Rivalry and Stake are public-access checks and do not fabricate prices if a validated contract is unavailable. HTTP 403, redirects and schema failures are visible limitations—not proof of no market.', 'https://www.hltv.org/matches', 'HLTV official match directory'), ('04', 'Model only supported rating inputs', 'If no accepted external line exists, read the latest official global Valve snapshot on or before today. Require exactly one matching team name and a complete five-player roster for each team. Reject missing teams and snapshots older than 35 days. The complete-picks fallback can disambiguate several same-name five-player rows only when a fresh, exact-fixture HLTV lineup identifies exactly one row: all five players match, or a unique four-of-five core matches with a documented one-player change and the row is labeled a roster-change identity join. Two plausible rows, a three-of-five overlap or an unbound lineup fail closed; no strongest-row guess. Otherwise publish an explicitly uncalibrated rating estimate. If any requirement fails, continue to the last-resort rungs.', 'https://github.com/ValveSoftware/counter-strike_regional_standings', 'Valve official standings'), ('05', 'Last-resort researched rungs — or the honest blank', 'When the Valve roster model has no row either, three clearly labelled rungs remain before anything is published as unresolved. First, our own network line: a Bradley–Terry fit over finished bo3.gg series in a bounded 120-day window, anchored on official Valve points, that fails closed — and refuses to price — whenever its graph, anchor count, per-side sample size or uncertainty gates are not met. Second, the HLTV world-ranking research model: if at least one team appears on the same dated official HLTV weekly ranking publication (no older than 14 days), the published points go through the same 400-scale logistic transform as the Valve model — an uncalibrated research estimate, never a betting line. When exactly one side has a published row, the unranked side is given HLTV’s floor of 0.0 points and the row is labelled ‘unranked floor’ with a low-confidence limitation; when neither side has a row the fixture stays unresolved. Third, wide-book indicative guidance: when the only observed two-sided books are far wider than every spread ceiling, the narrowest such book’s midpoint is published as guidance only, unmistakably badged and never counted as a money-backed pick. If even that fails, the match is published as unresolved with its full research trail.', 'https://www.hltv.org/ranking/teams', 'HLTV official world ranking')]
    out += '<section class="content-section resolution-steps">'
    for n, title, description, url, label in steps:
        out += f'<article class="resolution-step"><span>{n}</span><div><h2>{title}</h2><p>{e(description)}</p>{external(url, label)}</div></article>'
    out += '</section><section class="content-section prose"><p class="eyebrow">Our calculations, not source facts</p><h2>From observations to percentages</h2><h3>Prediction-market estimate</h3><p>For each outcome, take the best positive-size bid and ask from its own book. The midpoint is <code>m = (best bid + best ask) / 2</code>. Normalize the paired midpoints with <code>P(A) = mA / (mA + mB)</code> and <code>P(B) = 1 − P(A)</code>. Require valid two-sided books, a spread of no more than 12 cents per outcome in the featured exact-name path, matching token/condition IDs, and source timestamps no older than eight hours. The fallback origination ladder runs only when the featured method produced no pick; it accepts a two-sided book up to 15 cents and flags anything wider than 12 cents as <strong>thin</strong>, so a marginal, two-sided book is used with an explicit limitation instead of being silently promoted or discarded. Directory percentages and Gamma’s last-price defaults are not used.</p><p>These are indicative midpoints, not guaranteed execution quotes or “true” win probabilities. Trading fees, slippage and position size are excluded. A single prediction market is not independent bookmaker consensus. ' + external('https://docs.polymarket.com/api-reference/market-data/get-order-book', 'Inspect the official book schema') + '</p><h3>Original bookmaker estimate</h3><p>For a verified pair of decimal odds <code>dA, dB</code>, calculate <code>qA = 1/dA</code>, <code>qB = 1/dB</code>, then remove proportional margin with <code>P(A) = qA / (qA + qB)</code>. Only active, two-outcome, prematch match-winner lines are accepted. Implied-probability sums outside 0.85–1.35 are rejected as a data-quality policy. Different mirrors of one book count as one source family; independent families, if present, are combined using the median normalized probability.</p><h3>Valve-rating research estimate</h3><p>The published Valve model uses a Glicko-style expected score. We implement <code>g = 1 / √(1 + 3(ln(10)/400)² × RD² / π²)</code> and <code>P(A) = 1 / (1 + 10^(g × (RB − RA) / 400))</code>. Points <code>RA, RB</code> are sourced facts; <code>RD = 75</code> is a fixed assumption following Valve’s fit example, not a measured uncertainty for today’s roster.</p><p>' + external('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/fit.js', 'Valve fit example') + ' ' + external('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/glicko.js', 'Valve expected-score implementation') + '</p><div class="limitations-callout"><strong>Important model limitations</strong><p>This deployment has not been backtested or calibrated. A historic name-matched roster is not proof of today’s lineup. Stand-ins, roster changes, map vetoes, team form since the snapshot and bookmaker information are not added without verification. This model does not override a valid primary market pick and is never labeled a verified betting line.</p></div><h3>Our own network line (research fit)</h3><p>Some low-tier fixtures have no money line, no aggregated reference and no complete official rating rows — but the brief still asks us to originate our own line. For those fixtures only, a maximum-a-posteriori Bradley–Terry fit over finished series published by bo3.gg (a bounded 120-day window) places both teams on the same 400-point logistic scale through anchored teams that hold official Valve points; teams without official points share a division-anchor median with a weak prior and are labelled unanchored. This rung never overrides a money line, an aggregated reference price or a complete official-row estimate, and it never publishes anything when its gates fail: fewer than 300 usable series in the graph, fewer than 10 anchored teams, fewer than 6 finished series for either side in the window, or a rating-difference one-sigma interval wider than 300 points all leave the fixture to the next rung, with the published reason. Every priced row lists its two rating inputs, sample sizes, standard error, interval and evidence hash so the arithmetic can be replayed. It is a research model, never a bookmaker price.</p><h3>HLTV world-ranking research estimate</h3><p>Many low-tier teams never appear in Valve’s regional standings, but they do appear in HLTV’s official weekly world ranking. For fixtures where every money source, the aggregated reference, the Valve roster model and our own network line all failed, the teams’ published HLTV points go through the same 400-scale logistic transform: <code>P(A) = 1 / (1 + 10^((points_B − points_A) / 400))</code>. Both teams must appear on the same dated publication, read from the saved official ranking pages, and the publication must be no older than 14 days. When exactly one side has a published row — the common low-tier case — the unranked side is assigned HLTV’s floor of 0.0 points, the estimate is labelled <strong>unranked floor</strong> and carries an explicit low-confidence limitation; a floor is an assumption, not a measured rating. If neither side has a row the estimate is refused and the fixture stays unresolved. This is the same evidence class as the Valve rung — an explicitly uncalibrated research model, not betting odds. It never overrides a money, aggregated or Valve estimate, and it does not confirm today’s lineup, stand-ins, form or veto. Every input row links its own HLTV ranking page.</p>' + external('https://www.hltv.org/ranking/teams', 'HLTV official world ranking') + '<h3>Wide-book indicative guidance (last resort)</h3><p>Some low-tier fixtures are listed on an exchange, but the only two-sided books are so wide (observed spreads up to 0.90) that they fail every published acceptance ceiling. The brief still asks for a researched percentage, so when — and only when — every compliant rung above failed, the midpoint of the <em>narrowest</em> observed too-wide book is published as <strong>guidance only</strong>. It is badged in amber everywhere it appears, never counted as a money-backed pick, never used by the leaderboard plan’s upset rules, and each row shows the exact bid/ask spread it came from. An exactly even midpoint shows “No edge · Even” instead of a fabricated side. Guidance is a last-resort observation of thin money — not a validated price.</p><h3>Our fair line and the pick</h3><p>The fair decimal line is <code>1/P</code>; it is a calculated reference, not odds offered by any bookmaker. The suggested team has the higher unrounded probability. An exactly equal estimate has no directional pick unless the ranking provider itself publishes an order for the two teams: in that case the pick is the side the same official publication ranks higher, the row records the rule and both published positions, and neither probability changes. Without such a published order the side stays blank and the fixture is listed on <a class="internal-link" href="../unresolved/">Unresolved picks &amp; limitations</a>. Missing data is not replaced with 50/50. Displayed percentages are rounded to one decimal place; the downloadable data retains higher precision.</p></section>'
    out += '<section class="content-section prose"><p class="eyebrow">Operational boundaries</p><h2>Freshness, identity &amp; blank values</h2><ul><li>Refreshes are scheduled every four hours in UTC. GitHub Actions schedules are best-effort, not a real-time service-level guarantee.</li><li>The executive summary counts money-line picks and research-model picks separately, prints both teams&#39; probability on every row, and publishes every model-only pick with the money sources that failed in <em>Picks without a betting line</em>. A research model is never presented as a betting line.</li><li>The inventory observation time, price observation time, source book timestamp and rating snapshot date remain distinct. A failed refresh never resets successful-observation timestamps.</li><li>After eight hours, the browser displays a stale warning and disables “current pick” language. After a fixture’s explicit lock time, it is labeled closed for picks. A past scheduled start is not treated as a verified final result.</li><li>Matching is Unicode/case/whitespace-equivalent exact naming plus start time within 60 seconds. Abbreviations, sponsor aliases and fuzzy matches are not guessed. Ambiguous Valve names are rejected unless the complete-picks fallback replays a fresh, exact-fixture HLTV proof matching exactly one entire five-player roster, or exactly one four-of-five core with a documented one-player change (labeled as a roster-change identity join). Two plausible rows, a three-of-five overlap or an unbound lineup still fail closed.</li><li>Unverified factual values remain blank and labeled “unverified.” Calculated probabilities and fair lines are visibly identified as analysis; they are not filled-in source facts.</li><li>Access controls, robots restrictions and challenges are not bypassed. No login, paid API key, user input or betting account is required for this read-only dashboard.</li><li>Every published probability is replayed from saved first-party evidence before deployment. Every match row links back to Hotspawn; pricing and model inputs carry their own original-source links.</li></ul><p>' + external('https://play.hotspawn.com/how-it-works', 'Hotspawn rules for manual review') + f' · <a href="{prefix}review/">See all flagged limitations →</a></p></section>'
    return out


def flags_table(flags):
    """Render the source-linked findings register, including supersede links."""
    out = '<section class="content-section"><div class="section-heading"><div><p class="eyebrow">Research &amp; integrity register</p><h2>All findings</h2></div><span class="muted small">Source-linked, not silently corrected</span></div><div class="table-scroll"><table class="simple-table review-table"><caption class="sr-only">Source-linked irregularities and analysis limitations</caption><thead><tr><th>Finding</th><th>Limitation / handling</th><th>Original sources</th></tr></thead><tbody>'
    # A later session can settle an earlier finding. Keeping both rows without a
    # link leaves the review page arguing with itself, so a resolving flag names
    # the findings it supersedes and those rows say so in place.
    resolving = {}
    for f in flags:
        for target in f.get('supersedes') or []:
            resolving.setdefault(str(target), f['id'])
    for f in flags:
        resolver = resolving.get(f['id'])
        if resolver:
            label = badge('Superseded', 'purple') + f'<small>Answered by <a href="#flag-{e(resolver)}">a later finding</a></small>'
        else:
            label = badge('Notice' if f['severity'] == 'notice' else 'Needs review', 'purple' if f['severity'] == 'notice' else 'amber') + (f'<small>{len(f["match_ids"])} affected source records</small>' if f['match_ids'] else '')
        out += f'<tr id="flag-{e(f["id"])}"' + (' class="superseded-flag"' if resolver else '') + f'><th scope="row">{label}<strong>{e(f["title"])}</strong></th><td>{e(f["detail"])}</td><td><div class="evidence-links">'
        for url in dict.fromkeys(f['source_urls']):
            label = 'Hotspawn' if 'hotspawn' in url or 'cloudwaysapps' in url else 'Valve' if 'ValveSoftware' in url else 'Polymarket' if 'polymarket' in url else 'HLTV' if 'hltv.org' in url else urlparse_host(url)
            out += external(url, label)
        out += '</div></td></tr>'
    return out + '</tbody></table></div></section>'


def review(data, prefix):
    out = heading('Transparent by design', 'Flagged for Review', 'Unresolved matches, blocked sources and inconsistent official fields are published here. They do not block publication; they do block unsupported claims.')
    out += f'<div class="limitations-callout"><strong>Additional identity research and fallback picks</strong><p>Exact-name rejections below are retained for audit. <a style="text-decoration:underline" href="{prefix}origination/#picks">See newly researched fallback picks</a> and <a style="text-decoration:underline" href="{prefix}origination/#aliases">the source-linked alias review registry</a>. These associations do not independently confirm current rosters; Valve estimates remain uncalibrated.</p></div>'
    # Session fbdc97d6: the current, source-linked findings used to render at the
    # very bottom of this page, after many screens of dated registers from
    # earlier sessions. A phone reader had to scroll past all of it to see the
    # live warnings. Current findings come first; the dated history is retained
    # verbatim inside one collapsed block below.
    out += flags_table(data['flags'])
    history = review_note(prefix, data.get('day_one_audit'))
    if data.get('repo_audit'):
        history += audit_register(data['repo_audit'], prefix)
    if data.get('session_reviews'):
        from scripts.review_register import render_all as session_register
        history += session_register(data['session_reviews'], prefix, data.get('session_review_paths'))
    if history:
        out += ('<details class="archive-register" id="dated-registers"><summary>'
                'Dated registers from earlier sessions · retained for audit, not current findings</summary>'
                f'<p class="tiny muted">Everything below is an earlier session’s dated record. It is kept unchanged '
                'for provenance; the findings at the top of this page are the current ones.</p>' + history + '</details>')
    out += '<section class="content-section" id="unresolved"><div class="section-heading"><div><p class="eyebrow amber-text">No evidence, no invented pick</p><h2>Unresolved future matches</h2></div></div>' + unresolved_table(data, prefix) + '</section>'
    return out


def urlparse_host(url):
    from urllib.parse import urlparse
    return urlparse(url).netloc


def shell(data, key, body, prefix, now=None):
    title = PAGES[key][0]
    nav = ''
    for k, (label, path, sym) in PAGES.items():
        href = prefix + ('' if k == 'summary' else 'origination/#picks' if k == 'picks' else str(Path(path).parent) + '/')
        if k == 'summary':
            href = prefix + 'index.html'
        nav += f'<a class="nav-link {"active" if k == key else ""}" href="{href}"' + (' aria-current="page"' if k == key else '') + f'>{icon(sym)}<span>{label}</span>' + (f'<span class="nav-count">{len(data["flags"])}</span>' if k == 'review' else '') + '</a>'
    mobile = ''.join(f'<a href="{prefix + "index.html" if k == "summary" else prefix + ("origination/#picks" if k == "picks" else k + "/")}"' + (' aria-current="page"' if key == k else '') + f'>{icon(PAGES[k][2])}<span>{label}</span></a>' for k, label in [('summary', 'Summary'), ('picks', 'Picks'), ('unresolved', 'Unresolved'), ('edge', 'Edge'), ('coverage', 'Sources'), ('review', 'Review')])
    # Phone-first status strip: two one-tap destinations, present on every page.
    # Session 541cd43a — the brief asks to be able to reach an updated picks list
    # from a phone without hunting. Counts are the same canonical counts the
    # summary shows; the strip adds no probability and no fixture.
    _cc = (data.get('complete_picks') or {}).get('counts') or {}
    # Some rendered views are built from a minimal fixture that has no counts
    # block at all (the freshness tests render one); never index it directly.
    _counts = data.get('counts') or {}
    _active = _cc.get('active') or _counts.get('upcoming') or 0
    _with_pick = _cc.get('with_pick')
    if _with_pick is None:
        _with_pick = max(0, _active - (_cc.get('unresolved', _counts.get('unresolved') or 0)))
    _unresolved = _cc.get('unresolved', _counts.get('unresolved') or 0)
    mobile_status = (f'<nav class="mobile-status" aria-label="Picks and unresolved shortcuts">'
                     f'<a class="mobile-status-picks" href="{prefix}origination/#picks">'
                     f'<strong>{e(_with_pick)}</strong><span>picks ready'
                     f'<span class="ms-dim"> of {e(_active)}</span></span></a>'
                     f'<a class="mobile-status-blank" href="{prefix}origination/#unresolved">'
                     f'<strong>{e(_unresolved)}</strong><span>unresolved<span class="ms-dim"> · why</span></span></a>'
                     '</nav>')
    inventory = data.get('inventory_observed_at') or ''
    stale = not data['coverage_complete'] or not is_fresh(inventory, now or datetime.now(timezone.utc))
    freshness = 'Snapshot needs attention' if stale else 'Source snapshot available'
    crosscheck = data.get('inventory_crosscheck', 'complete')
    crosscheck_note = ''
    if data['coverage_complete'] and crosscheck != 'complete':
        scope = 'one rendered lobby page' if crosscheck == 'partial' else 'both rendered lobby pages'
        crosscheck_note = (f'<div class="limitations-callout" role="status" id="inventory-crosscheck"><strong>Lobby HTML cross-check unavailable.</strong> '
                           f'{e(scope.capitalize())} could not be read this cycle, so the inventory is the complete public Hotspawn fixture API array rather than a three-response reconciliation. '
                           f'Picks remain tied to that API snapshot and keep their own observation times. '
                           f'<a href="{prefix}coverage/">Source status →</a></div>')
    extra_css = f'<link rel="stylesheet" href="{prefix}assets/twc.css">' if key == 'twc' else ''
    safety_attrs = ''
    if key == 'twc':
        from scripts.pick_safety import body_attributes
        safety_attrs = body_attributes(inventory, data['coverage_complete'])
        extra_css += f'<script src="{prefix}assets/pick-safety.js" defer></script>'
    if key == 'summary':
        extra_css += f'<script src="{prefix}assets/glance-lock.js" defer></script>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)} · Spawn Scout</title><meta name="description" content="Every Hotspawn CS2 match, independent probabilities, clear picks and original evidence. Mobile-friendly, read-only analysis with visible coverage gaps."><meta name="theme-color" content="#142534"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'"><link rel="icon" href="{prefix}assets/scout-mark.svg" type="image/svg+xml"><link rel="stylesheet" href="{prefix}assets/scout.css">{extra_css}<script src="{prefix}assets/scout.js" defer></script></head>
<body {safety_attrs} data-page="{key}" data-inventory-time="{e(inventory)}" data-inventory-complete="{str(data['coverage_complete']).lower()}" data-snapshot-generated="{e(data['generated_at'])}" data-data-url="{prefix}data/latest.json"><a class="skip-link" href="#main">Skip to content</a>
<aside class="sidebar"><a class="brand" href="{prefix}index.html" aria-label="Spawn Scout home"><span class="brand-mark"><svg viewBox="0 0 28 28" aria-hidden="true"><path d="M5 4h9v9H5zM17 4h7v7h-7zM5 16h7v8H5z"/><path d="m16 17 8-4v11h-8z"/></svg></span><span>spawn<span class="brand-light">scout</span><small>CS2 MATCH INTELLIGENCE</small></span></a><p class="nav-label">YOUR DASHBOARD</p><nav aria-label="Main navigation">{nav}</nav><div class="sidebar-bottom"><div class="sidebar-note"><span class="status-dot"></span><strong>Independent analysis</strong><p>Hotspawn tells us who plays.<br>External sources inform the pick.</p></div>{external(LOBBY, 'Open Hotspawn lobby', 'sidebar-external')}<a class="sidebar-repo" href="{REPO}">Open-source &amp; auditable {icon('external')}</a></div></aside>
<div class="workspace"><header class="topbar"><div class="mobile-brand"><a href="{prefix}index.html">spawn<strong>scout</strong><span>CS2</span></a></div><div class="desktop-crumb">Workspace <span>/</span> <strong>{e(title)}</strong></div><div class="topbar-tools"><span class="refresh-pill">{icon('clock')} Checks every 4h</span><label class="timezone-control"><span class="sr-only">Display timezone</span><select id="timezone"><option value="Europe/Malta">Malta time</option><option value="UTC">UTC</option><option value="local">Device time</option></select></label></div></header>
<main id="main" tabindex="-1">{mobile_status}<div class="snapshot-line"><span class="freshness-label" data-freshness><span class="status-dot"></span>{freshness}</span><span>Inventory checked {local_time(data.get('inventory_observed_at'))} <span data-zone-label>Malta</span></span></div><div id="stale-warning" class="stale-warning" role="status" {'' if stale else 'hidden'}><strong>Do not treat these as current picks.</strong> The inventory check failed or the successful snapshot is older than eight hours. Original timestamps are preserved. <a href="{prefix}coverage/">Check source status →</a></div><div id="new-snapshot" class="new-snapshot" hidden>A newer verified snapshot is available. <button type="button" id="load-update">Load updated picks →</button></div>{crosscheck_note}{body}<footer class="footer"><div><strong>Better context. Clearer picks.</strong><p>Independent Hotspawn CS2 research · Not affiliated with Hotspawn, HLTV, Valve or any betting provider.</p><p>Estimates, not guarantees. No bets or picks are placed. Informational use only. 18+ where applicable.</p></div><div><a href="{prefix}methodology/">Methodology</a><a href="{prefix}review/">Flagged for Review</a><a href="{prefix}data/latest.json">Open data ↓</a><span class="tiny muted">Built {local_time(data['generated_at'])}</span></div></footer></main></div><nav class="mobile-nav" aria-label="Mobile navigation">{mobile}</nav></body></html>'''


def picks_csv(data):
    """Export the exact probability basis and direction selected by the HTML table."""
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
    return stream.getvalue()


def build(source: Path, output: Path, now=None):
    # A single reference time for the whole site: a page can never disagree with
    # itself about freshness, and a test can pin the site to a known instant.
    now = now or datetime.now(timezone.utc)
    data = check_data(source)
    contrarian_data = load_review(source / 'contrarian.json')
    data['_contrarian'] = derive_context(data, contrarian_data)
    validate_context(data, data['_contrarian'])
    if (source / 'origination.json').exists():
        data['complete_picks'] = json.loads((source / 'origination.json').read_text())
        # Preserve featured money lines; show researched values for blanks or
        # explicitly verified money-backed replacements of the lowest-rung model.
        data['fallbacks'] = {str(r['id']): r for r in data['complete_picks'].get('matches') or [] if r.get('origination')}
    # Session 541cd43a: the dated, read-only source sweep behind the unresolved
    # register (HLTV, bo3.gg, esportsbook surfaces). Rendering it is the only use;
    # no value in it ever becomes a probability.
    line_sources_path = source / 'research/fbdc97d6/line-sources.json'
    if line_sources_path.exists():
        try:
            data['_line_sources'] = json.loads(line_sources_path.read_text())
        except ValueError:
            data['_line_sources'] = None
    # Session 3016b0c6: per-fixture research for matches with no betting line
    # (HLTV first, then esportsbooks/aggregators). Dated evidence only; a lead
    # recorded there is not a price and never becomes a pick in this renderer.
    no_line_path = source / 'research/3016b0c6/line-source-research.json'
    if no_line_path.exists():
        try:
            data['_no_line_research'] = json.loads(no_line_path.read_text())
        except ValueError:
            data['_no_line_research'] = None
    session_probe_path = source / 'research/4c972a51/source-probe.json'
    if session_probe_path.exists():
        try:
            data['_session_probe'] = json.loads(session_probe_path.read_text())
        except ValueError:
            data['_session_probe'] = None
    probe_path = source / 'research/541cd43a/provider-probe.json'
    if probe_path.exists():
        try:
            data['_source_probe'] = json.loads(probe_path.read_text())
        except ValueError:
            data['_source_probe'] = None
    if (source / 'research/day-one-audit.json').exists():
        data['day_one_audit'] = json.loads((source / 'research/day-one-audit.json').read_text())
    # Session findings share the dated, source-linked review schema. Discover all
    # retained session files so a new completed audit cannot silently be omitted
    # by a hardcoded allowlist. Extend only the in-memory rendering list; the
    # published latest.json remains the untouched source-directory copy.
    have = {f['id'] for f in data['flags']}
    for findings in sorted((source / 'research').glob('*/flags.json')):
        for finding in json.loads(findings.read_text()):
            if finding['id'] not in have:
                data['flags'].append(finding)
                have.add(finding['id'])
    # Session arena-8fa2b226's coverage dossier: why each blank stayed blank, which providers were checked.
    if (source / 'research/8fa2b226/coverage-probe.json').exists():
        data['coverage_probe'] = json.loads((source / 'research/8fa2b226/coverage-probe.json').read_text())
    if (source / 'research/de176356/repo-review-register.json').exists():
        data['repo_audit'] = json.loads((source / 'research/de176356/repo-review-register.json').read_text())
    from scripts.review_register import REGISTERS
    session_reviews, session_review_paths = [], []
    for relative in REGISTERS:
        candidate = source / relative
        if not candidate.exists():
            continue
        session_reviews.append(json.loads(candidate.read_text()))
        session_review_paths.append(relative)
    if session_reviews:
        data['session_reviews'] = session_reviews
        data['session_review_paths'] = session_review_paths
    from scripts.twc_research import derive_day4
    data['_twc_day4'] = derive_day4(data, source, now)
    from scripts.day5 import derive as derive_day5
    data['_twc_day5'] = derive_day5(data, source, now)
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'assets').resolve() != Path('assets').resolve():
        shutil.copytree('assets', output / 'assets', dirs_exist_ok=True)
    if (output / 'data').resolve() != source.resolve():
        shutil.copytree(source, output / 'data', dirs_exist_ok=True)
    # Publish the reconciliation beside the raw counts. `counts.*` describes the
    # featured exact-name method alone; every page on this site shows the
    # researched list. Before this block the downloaded JSON said "10
    # unresolved" while the page said "0", and both were true of different
    # lists. A reader must never have to guess which list a number belongs to.
    write_reconciled_snapshot(output / 'data/latest.json', data)
    (output / '.nojekyll').touch()
    from scripts import build as _self
    from scripts.build_edge import edge_review
    from scripts.build_twc import render as twc_review
    edge_path = source / 'edge-review.json'
    _self.EDGE_SOURCE = edge_path
    from scripts.build_final_day import render as final_day_render
    renderers = {'summary': lambda d, pfx: summary(d, pfx, now=now),
                 'picks': lambda d, pfx: picks(d, pfx, now=now),
                 'unresolved': lambda d, pfx: unresolved_page(d, pfx, now=now),
                 'coverage': lambda d, pfx: coverage(d, pfx, now=now),
                 'methodology': methodology, 'review': review,
                 'edge': lambda d, pfx: edge_review(d, pfx, edge_path),
                 'twc': lambda d, pfx: twc_review(d, pfx, source, now=now),
                 'final': lambda d, pfx: final_day_render(d, pfx, edge_path, source)}
    for key, (_, path, _) in PAGES.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        prefix = './' if key == 'summary' else '../'
        target.write_text(shell(data, key, renderers[key](data, prefix), prefix, now=now))
    (output / 'data/picks.csv').write_text(picks_csv(data))
    if data.get('_twc_report'):
        (output / 'data/twc-day3-picks.json').write_text(json.dumps(data['_twc_report'], ensure_ascii=False, indent=2) + '\n')
        (output / 'data/twc-day4-picks.json').write_text(json.dumps(data['_twc_report']['day4'], ensure_ascii=False, indent=2) + '\n')
        (output / 'data/twc-day5-picks.json').write_text(json.dumps(data['_twc_report']['day5'], ensure_ascii=False, indent=2) + '\n')
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
