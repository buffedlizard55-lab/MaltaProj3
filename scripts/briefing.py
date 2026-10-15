"""Evidence-constrained editorial briefing; never changes a probability or pick."""
from __future__ import annotations

import html
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


def review_note(prefix):
    return f'''<section class="content-section" id="day-one-review"><h2>Day-one result &amp; roster review — unverified</h2>
<p>The reported 9z win over Aurora and a recent Aurora roster change are user-reported leads, not verified findings in this dataset. Winner, score, event day, changed player, change date, current lineup and rest advantage remain <strong>— unverified</strong>. No probability adjustment is applied.</p>
<p>The saved Hotspawn feed is a scheduled-fixture inventory, not a completed-results feed. A past start or a team rating does not establish a winner. The current source collection does not verify official roster announcements, travel or rest. No causal explanation for the reported upset is asserted.</p>
<p>Review sources: <a class="source-link" href="https://play.hotspawn.com/lobby">Official Hotspawn inventory</a> · <a class="source-link" href="https://github.com/ValveSoftware/counter-strike_regional_standings">Official Valve rating/roster snapshots</a> · <a class="source-link" href="https://www.hltv.org/results">HLTV results research (secondary)</a>. These are research destinations, not citations confirming the reported result or roster change. <a class="internal-link" href="{prefix}coverage/">Observed source evidence →</a></p></section>'''


def render(data, prefix):
    matches = data.get('complete_picks', {}).get('matches', [])
    out = '''<section class="content-section" id="contrarian"><h2>Contrarian, not reckless</h2>
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
    out += f'<p>Read the <a class="internal-link" href="{prefix}review/#day-one-review">day-one result &amp; Aurora roster verification limitations</a>. An unexpected winner is possible even with a well-estimated favorite; one result does not validate a new strategy.</p></section>'
    return out
