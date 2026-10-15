"""Evidence-constrained editorial briefing; never changes a probability or pick."""
from __future__ import annotations

import html
import hashlib
from datetime import datetime, timezone

from scripts.domain import is_fresh, timestamp


def e(value):
    return html.escape(str(value), quote=True)


def candidates(matches, now=None, inventory_observed_at=None):
    """Editorial 30–50% screen, not a calibrated edge/ownership model.

    Only current, unlocked money-backed pairs qualify. Model-only, stale,
    suspended-by-collector, tied and unsupported rows cannot enter this screen.
    """
    now = now or datetime.now(timezone.utc)
    result = []
    if not is_fresh(inventory_observed_at, now):
        return result
    for m in matches:
        a = m.get('origination')
        if not a or a['method'] not in {'market', 'bookmaker', 'consensus'}:
            continue
        if not is_fresh(a.get('observed_at'), now):
            continue
        start, lock = timestamp(m.get('starts_at')), timestamp(m.get('locks_at'))
        if not start or not lock or min(start, lock) <= now:
            continue
        if m.get('availability') != 'open':
            continue
        p = a['probabilities']
        underdog = 0 if p[0] < p[1] else 1
        if .30 <= p[underdog] < .50:
            result.append((m, underdog))
    return sorted(result, key=lambda item: (-item[0]['origination']['probabilities'][item[1]], item[0]['id']))


def validate_audit(audit):
    """Replay inspected official roster rows against the original Git blobs."""
    for snapshot in audit['valve_roster_snapshots']:
        raw = snapshot['original_markdown'].encode()
        digest = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
        if digest != snapshot['git_blob_sha'] or snapshot['aurora_row'] not in raw.decode().splitlines():
            raise ValueError('Day-one official roster evidence does not replay')
        if snapshot['aurora_row'].split('|')[3].strip() != 'Aurora':
            raise ValueError('Day-one roster evidence refers to another team')
        expected = 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_' + snapshot['date'].replace('-', '_') + '.md'
        if snapshot['source_url'] != expected:
            raise ValueError('Day-one roster evidence has an unsupported source URL')
    return audit


def reviewed_note(prefix, audit):
    validate_audit(audit)
    out = f'''<section class="content-section" id="day-one-review"><h2>Day-one review: 9z vs Aurora</h2>
<p><strong>Primary organizer result: — unverified.</strong> Secondary-source corroboration: HLTV reports <a class="source-link" href="https://www.hltv.org/news/45718/9z-beat-aurora-2-0-to-kick-off-twc-2026">9z beat Aurora 2–0 at Thunderpick World Championship 2026</a>, also listed on its <a class="source-link" href="https://www.hltv.org/matches/2399384/9z-vs-aurora-thunderpick-world-championship-2026">match page</a>. This is not relabeled as primary organizer verification. A historical prematch price was not captured here, so upset magnitude, closing-line value and retrospective pick accuracy remain — unverified.</p>
<p><strong>What the report supports:</strong> HLTV describes 9z taking control on Inferno and Aurora struggling on Nuke. It also reports that Aurora had beaten 9z at EPL 24. That supports treating match-specific conditions as important, not assuming a prior head-to-head winner must repeat. This single result does not calibrate our model or establish a profitable contrarian strategy.</p>
<h3>Aurora roster check — official dated snapshots</h3><p>Valve’s 6 July snapshot lists MAJ3R, soulfly, Wicadia, woxic and XANTARES; its 3 August, 7 September and 5 October snapshots instead list Jimpphat, kyxsan, Wicadia, woxic and XANTARES. This verifies a difference in published roster listings, not the precise transfer/announcement date. The last three snapshots list the same five names. They do not confirm the match-day lineup, a change after 5 October, player onboarding, or the absence of a later change. <strong>Recent change date/player, rest and travel advantage: — unverified.</strong> The independently checked <a class="source-link" href="https://www.hltv.org/news/45082/official-aurora-complete-rebuild-with-kyxsan">HLTV rebuild report</a> attributes the additions of Jimpphat, kyxsan and coach ash to Aurora announcements. That secondary report corroborates the summer rebuild, not a new October change or its causal effect on this loss; no numerical probability adjustment is applied.</p>
<div class="table-scroll"><table class="simple-table"><caption>Official historical Aurora roster entries — not current-lineup confirmation</caption><thead><tr><th scope="col">Snapshot date</th><th scope="col">Published roster</th><th scope="col">Official source</th></tr></thead><tbody>'''
    for snapshot in audit['valve_roster_snapshots']:
        roster = snapshot['aurora_row'].split('|')[4].strip()
        out += f'<tr><th scope="row">{e(snapshot["date"])}</th><td>{e(roster)}</td><td><a class="source-link" href="{e(snapshot["source_url"])}">Valve original standings</a></td></tr>'
    out += f'''</tbody></table></div><p>Research inspected {e(audit['reviewed_at'])}. <a class="source-link" href="{e(audit['research_run_url'])}">Live source research audit</a> · <a class="internal-link" href="{prefix}data/research/day-one-audit.json">Saved original Valve content, hashes and HLTV source excerpts ↓</a>. The date-filtered HLTV results endpoint was blocked; the normal results page and discovered report were accessible. No access-control bypass was used.</p>
<p><strong>Practical decision:</strong> do not automatically fade Aurora or chase 9z after this result. Use the next fixture’s independently sourced probabilities. Current roster announcements, substitutions, map veto, comparable rest and scoring/ownership evidence must support any deviation from the default pick. A plausible upset is not necessarily an undervalued pick.</p></section>'''
    return out


def review_note(prefix, audit=None):
    if audit:
        return reviewed_note(prefix, audit)
    return f'''<section class="content-section" id="day-one-review"><h2>Day-one result &amp; roster review — unverified</h2>
<p>The reported 9z win over Aurora and a recent Aurora roster change are user-reported leads, not verified findings in this dataset. Winner, score, event day, changed player, change date, current lineup and rest advantage remain <strong>— unverified</strong>. No probability adjustment is applied.</p>
<p>The saved Hotspawn feed is a scheduled-fixture inventory, not a completed-results feed. A past start or a team rating does not establish a winner. The current source collection does not verify official roster announcements, travel or rest. No causal explanation for the reported upset is asserted.</p>
<p>Review sources: <a class="source-link" href="https://play.hotspawn.com/lobby">Official Hotspawn inventory</a> · <a class="source-link" href="https://github.com/ValveSoftware/counter-strike_regional_standings">Official Valve rating/roster snapshots</a> · <a class="source-link" href="https://www.hltv.org/results">HLTV results research (secondary)</a>. These are research destinations, not citations confirming the reported result or roster change. <a class="internal-link" href="{prefix}coverage/">Observed source evidence →</a></p></section>'''


def render(data, prefix):
    matches = data.get('complete_picks', {}).get('matches', [])
    out = '''<section class="content-section" id="upset-watchlist"><h2>Contrarian, not reckless</h2>
<p><strong>Default: retain the higher-probability pick.</strong> With equal points for either winner, expected base points are probability × match points. Choosing a less likely winner reduces expected base points; it can be a tournament-risk choice, not a proven edge. Opponent ownership, exact streak state and leaderboard position are not collected, so no leaderboard-gain forecast or automatic contrarian override is justified.</p>
<p><a class="source-link" href="https://play.hotspawn.com/how-it-works">Official scoring overview</a> describes tier points and streak bonuses; it does not establish a crowd-fading bonus. Never use Hotspawn popularity to estimate win probability. A roster announcement alone is not evidence of the direction or size of a probability change.</p>
<p><strong>Upset watchlist:</strong> current, unlocked, externally priced underdogs estimated at 30% to below 50%, ordered by estimated win probability. This is an editorial screen evaluated at page build, not a live feed, validated cutoff, recommendation to switch, or claim of mispricing. Reopen the complete list before submitting. Model-only lines are excluded. Verify lineups, substitutions, map pool/veto, format and comparable rest before considering a switch; those factors are not automatically quantified here.</p>'''
    rows = candidates(matches, inventory_observed_at=data.get('complete_picks', {}).get('source_snapshot_at'))
    if rows:
        out += '<div class="table-scroll"><table class="simple-table"><caption>Market-backed underdogs — alternatives, not default picks</caption><thead><tr><th scope="col">Match / alternative</th><th scope="col">Estimated chance</th><th scope="col">Evidence</th></tr></thead><tbody>'
        for m, i in rows:
            a = m['origination']
            names = [t['name'] or 'Unverified team' for t in m['teams']]
            out += f'<tr><th scope="row">{e(" vs ".join(names))}<small>Alternative: {e(names[i])}</small><small>Scheduled {e(m["starts_at"])} · locks {e(m["locks_at"])}</small></th><td>{a["probabilities"][i] * 100:.1f}%<small>{e(a["label"])} · observed {e(a["observed_at"])}</small></td><td><a class="source-link" href="{e(m["source_url"])}">Official fixture</a><a class="source-link" href="{e(a["source_url"])}">Original pricing source</a><a class="internal-link" href="{prefix}origination/#match-{e(m["id"])}">Both sides &amp; default pick →</a></td></tr>'
        out += '</tbody></table></div>'
    else:
        out += '<p>No current unlocked market-backed match passes this screen at build time. No model estimate or stale line is promoted to fill the watchlist.</p>'
    out += f'<p>Read the <a class="internal-link" href="{prefix}review/#day-one-review">day-one postmortem &amp; official Aurora roster snapshot check</a>. An unexpected winner is possible even with a well-estimated favorite; one result does not validate a new strategy.</p></section>'
    return out


def audit_register(audit, prefix):
    """Publish inherited audit claims without silently certifying their values."""
    out = '<section class="content-section" id="repo-audit"><h2>Independent repo, coverage &amp; cadence audit</h2>'
    out += f'<p>Dated concurrent audit: {e(audit["audit_clock_utc"])}. These are reported findings, not live coverage figures or blanket primary-source verification. Exact unconfirmed values remain unverified; original observations are expandable for manual review. <a class="internal-link" href="{prefix}data/research/de176356/repo-review-register.json">Original audit register ↓</a></p>'
    out += '<p><strong>Current handling:</strong> use each fixture’s displayed lock deadline rather than assuming the help-page offset; the saved fixture evidence uses six minutes while the help page says five. The inventory is scheduled fixtures, not completed results. Four-hour refresh is a schedule target, not a GitHub delivery guarantee; the dated audit’s largest measured gap was 6.48 hours (within eight hours). Freshness warnings remain active. No second competing publisher was added. The two day-one scopes have now been integrated without dropping either source trail.</p>'
    out += '<div class="table-scroll"><table class="simple-table"><caption>Dated audit register — reported observations and verification limits</caption><thead><tr><th scope="col">Item / area</th><th scope="col">Verified current value</th><th scope="col">Reported issue &amp; review sources</th></tr></thead><tbody>'
    for item in audit['items']:
        out += f'<tr id="audit-{e(item["id"])}"><th scope="row">{e(item["id"])}<small>{e(item["area"])}</small></th><td><span class="unverified">— <small>unverified as a current value</small></span></td><td><details><summary>Reported finding &amp; dated measurement</summary><p>{e(item["finding"])}</p><p>{e(item["measured"])}</p><p>Original audit request: {e(item["action"])}</p></details>'
        for url in item['sources']:
            out += f'<a class="source-link" href="{e(url)}">Original review source</a> '
        out += '</td></tr>'
    return out + '</tbody></table></div></section>'
