#!/usr/bin/env python3
"""Build the Hotspawn CS2 picks site (docs/) from data/picks-model.json.

Pipeline
  1. Each outside market is de-vigged to two-way probabilities (normalised to 100%).
     Polymarket: usable only if volume >= $50 and implied total within 95-105%.
     Stake / Oddsportal: decimal two-way odds, normalised.
  2. Market consensus = equal-weight mean of usable sources.
  3. HLTV points model = team points share, only if both teams are in the HLTV top 30.
  4. Our line = 70% market consensus + 30% HLTV model (market only when no HLTV model).
  5. Pick = higher line. Matches with no usable market are listed as Unresolved.
Hotspawn pick percentages are never read by this script.

Run:  python3 scripts/build_site.py          (writes docs/)
      python3 scripts/build_site.py --check  (also checks internal links)
"""
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "picks-model.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs"
SNAP = DATA["snapshot"]
HLTV_URL = SNAP["hltv_ranking"]
LOBBY = SNAP["hotspawn_lobby"]
STAKE_URL = SNAP["stake_listing"]
MODEL_WEIGHT = 0.30
HLTV = {t["team"].lower(): t for t in DATA["hltv_top30"]}
PAGES = [
    ("index.html", "Summary"),
    ("picks.html", "Picks"),
    ("unresolved.html", "Unresolved"),
    ("matches.html", "All matches"),
    ("analysis.html", "Analysis"),
    ("methodology.html", "Methodology"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for Review"),
]


def esc(s):
    return html.escape(str(s), quote=True)


def a_link(url, text):
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(text)}</a>'


# ---------------------------------------------------------------- probabilities
def norm2(x, y):
    t = x + y
    return 100.0 * x / t, 100.0 * y / t


def pm_status(pm):
    """Return (usable, reason). Polymarket values are cents (sum ~100 when fair)."""
    if pm is None:
        return False, "No Polymarket market captured."
    total = pm["a"] + pm["b"]
    vol = pm.get("volume_usd") or 0
    reasons = []
    if vol < 50:
        reasons.append(f"Volume ${vol:,.2f} (below $50 rule)")
    if not (95 <= total <= 105):
        reasons.append(f"Implied total {total}% (outside 95–105%)")
    return (not reasons), "; ".join(reasons)


def sources_for(m):
    """List of usable market sources: (label, pA, pB, raw, url)."""
    out, notes = [], []
    pm = m.get("pm")
    ok, why = pm_status(pm)
    if ok:
        pa, pb = norm2(pm["a"], pm["b"])
        out.append(("Polymarket", pa, pb, f"{pm['a']}¢ / {pm['b']}¢", pm["url"]))
    elif pm:
        notes.append(f"Polymarket excluded: {why}.")
    if m.get("op"):
        o = m["op"]
        pa, pb = norm2(1 / o["odds_a"], 1 / o["odds_b"])
        out.append(("Oddsportal", pa, pb, f"{o['odds_a']} / {o['odds_b']}", o["url"]))
    if m.get("stake"):
        s = m["stake"]
        pa, pb = norm2(1 / s["odds_a"], 1 / s["odds_b"])
        out.append(("Stake", pa, pb, f"{s['odds_a']} / {s['odds_b']}", s["url"]))
    return out, notes


def compute(m):
    srcs, notes = sources_for(m)
    res = {"sources": srcs, "notes": notes, "market": None, "model": None,
           "final_a": None, "final_b": None, "resolved": False}
    if srcs:
        mkt = sum(s[1] for s in srcs) / len(srcs)
        res["market"] = mkt
        ra = HLTV.get((m.get("hltv_a") or "").lower()) if m.get("hltv_a") else None
        rb = HLTV.get((m.get("hltv_b") or "").lower()) if m.get("hltv_b") else None
        if ra and rb:
            model = 100.0 * ra["points"] / (ra["points"] + rb["points"])
            res["model"] = model
            fa = (1 - MODEL_WEIGHT) * mkt + MODEL_WEIGHT * model
        else:
            fa = mkt
        res["final_a"] = round(fa, 1)
        res["final_b"] = round(100 - fa, 1)
        res["resolved"] = True
    else:
        # Unresolved: record why each market is unusable
        if m.get("pm") is None:
            notes.append(m.get("pm_note") or "No outside market (Polymarket, Oddsportal, Stake) captured.")
        if m.get("stake") is None and m.get("op") is None and m.get("pm") is not None:
            pass
    return res


def pick_of(m, r):
    if not r["resolved"]:
        return None
    if r["final_a"] >= r["final_b"]:
        return m["a"], r["final_a"], m["b"], r["final_b"]
    return m["b"], r["final_b"], m["a"], r["final_a"]


def confidence(r, pct):
    n = len(r["sources"])
    margin = abs(pct - 50)
    if n >= 2 and margin >= 20:
        return "High"
    if (n >= 2 and margin >= 10) or (n == 1 and margin >= 20):
        return "Medium"
    return "Low"


def hltv_short(m):
    ra = HLTV.get((m.get("hltv_a") or "").lower()) if m.get("hltv_a") else None
    rb = HLTV.get((m.get("hltv_b") or "").lower()) if m.get("hltv_b") else None
    if ra and rb:
        return f"#{ra['rank']} {ra['team']} ({ra['points']} pts) vs #{rb['rank']} {rb['team']} ({rb['points']} pts)"
    return None


def build_rows():
    rows = []
    for m in DATA["matches"]:
        r = compute(m)
        rows.append((m, r))
    return rows


# ---------------------------------------------------------------- page chrome
CSS = """
:root{--bg:#0f1420;--card:#171e2e;--ink:#e8edf7;--mute:#9aa6bd;--acc:#4cc9f0;--ok:#51cf66;--warn:#ffd43b;--bad:#ff6b6b;--line:#273149}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
a{color:var(--acc)}
header.top{background:#0b0f19;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px}
.brand{font-weight:700;padding:12px 0 6px;font-size:16px}
nav ul{list-style:none;margin:0;padding:0 0 10px;display:flex;gap:6px;overflow-x:auto;-webkit-overflow-scrolling:touch}
nav a{display:block;white-space:nowrap;padding:6px 10px;border-radius:999px;background:var(--card);color:var(--ink);text-decoration:none;font-size:13px;border:1px solid var(--line)}
nav a.on{background:var(--acc);color:#04111a;border-color:var(--acc)}
main{padding:18px 0 40px}
h1{font-size:22px;margin:8px 0 6px}
h2{font-size:18px;margin:26px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
.lede{color:var(--mute);margin:0 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi{font-size:26px;font-weight:700}
.kpi small{display:block;font-size:12px;color:var(--mute);font-weight:500}
.btns{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:10px 0}
.btns a{display:block;padding:14px;border-radius:12px;background:var(--card);border:1px solid var(--line);text-decoration:none;color:var(--ink)}
.btns a b{color:var(--acc);display:block;margin-bottom:4px}
.btns a span{color:var(--mute);font-size:13px}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:10px;overflow:hidden;font-size:13px}
th,td{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#1d2740;font-weight:600;color:#cdd7ea;position:sticky;top:0}
td.blank{color:var(--warn);font-style:italic}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600}
.High{background:#1f4d2c;color:#b7f5c4}.Medium{background:#4d4319;color:#ffeaa0}.Low{background:#4a2020;color:#ffc2c2}
.flag{color:var(--warn);font-weight:600}
.note{color:var(--mute);font-size:13px}
.pick{font-weight:700;color:var(--ok)}
ul.clean{padding-left:18px}
ul.clean li{margin:4px 0}
footer{color:var(--mute);font-size:12px;border-top:1px solid var(--line);padding:14px 0 30px}
@media (max-width:720px){
  h1{font-size:19px}
  table.resp thead{display:none}
  table.resp, table.resp tbody, table.resp tr, table.resp td{display:block;width:100%}
  table.resp tr{border-bottom:1px solid var(--line);padding:8px 4px}
  table.resp td{border:0;padding:3px 6px}
  table.resp td::before{content:attr(data-label);display:block;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute)}
}
"""


def page(name, title, body, active):
    items = []
    for f, t in PAGES:
        cls = ' class="on"' if f == active else ""
        items.append(f'<li><a href="{esc(f)}"{cls}>{esc(t)}</a></li>')
    nav = "".join(items)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · Hotspawn CS2 Picks</title>
<style>{CSS}</style></head>
<body>
<header class="top"><div class="wrap">
<div class="brand">Hotspawn CS2 Picks · snapshot {esc(SNAP['session_date_utc'])} (UTC)</div>
<nav aria-label="Site"><ul>{nav}</ul></nav>
</div></header>
<main class="wrap">{body}</main>
<footer class="wrap">Probabilities are our own lines built from outside betting markets and HLTV ranking points. Hotspawn pick percentages are not used. Not financial or betting advice. Snapshot is not auto-refreshed (see Flagged for Review, I-16).</footer>
</body></html>
"""


def table(headers, rows, cls="resp"):
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    trs = []
    for r in rows:
        tds = []
        for i, cell in enumerate(r):
            label = headers[i] if i < len(headers) else ""
            if isinstance(cell, tuple) and cell[0] == "BLANK":
                tds.append(f'<td class="blank" data-label="{esc(label)}">{cell[1]}</td>')
            else:
                tds.append(f'<td data-label="{esc(label)}">{cell}</td>')
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div style="overflow-x:auto"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'


def BLANK(text="Not captured ⚑"):
    return ("BLANK", esc(text))


def fmt(x):
    return "" if x is None else f"{x:.1f}"


def hs_link(m):
    return a_link(m["hs_url"], "Hotspawn")


def src_links(m, r):
    parts = [hs_link(m)]
    for label, _, _, _, url in r["sources"]:
        parts.append(a_link(url, label))
    if m.get("pm") and not any(s[0] == "Polymarket" for s in r["sources"]):
        parts.append(a_link(m["pm"]["url"], "Polymarket (excluded)"))
    if m.get("hltv_a") and m.get("hltv_b"):
        parts.append(a_link(HLTV_URL, "HLTV"))
    return " · ".join(parts)


def input_text(r):
    bits = []
    for label, pa, pb, raw, _ in r["sources"]:
        bits.append(f"{label} {raw} → {pa:.1f}/{pb:.1f}")
    if r["model"] is not None:
        bits.append(f"HLTV model {r['model']:.1f}/{100 - r['model']:.1f}")
    return "; ".join(bits)


# ---------------------------------------------------------------- pages
def build_all():
    rows = build_rows()
    resolved = [(m, r) for m, r in rows if r["resolved"]]
    unresolved = [(m, r) for m, r in rows if not r["resolved"]]
    flagged_matches = [(m, r) for m, r in rows if m.get("flags") or r["notes"]]
    total = len(rows)
    n_res, n_unres = len(resolved), len(unresolved)
    model_used = sum(1 for m, r in resolved if r["model"] is not None)
    disagree = []
    for m, r in resolved:
        if r["model"] is not None:
            market_fav = m["a"] if r["market"] >= 50 else m["b"]
            model_fav = m["a"] if r["model"] >= 50 else m["b"]
            if market_fav != model_fav:
                disagree.append((m, r))
    # Top picks by confidence then margin
    def key(item):
        m, r = item
        p, pct, _, _ = pick_of(m, r)
        return (-{"High": 3, "Medium": 2, "Low": 1}[confidence(r, pct)], -abs(pct - 50))
    top = sorted(resolved, key=key)[:5]

    # ---- index / summary
    top_list = "".join(
        f"<li><span class='pick'>{esc(pick_of(m,r)[0])}</span> over {esc(pick_of(m,r)[2])} "
        f"({pick_of(m,r)[1]:.1f}%) · {esc(m['tournament'])} · {esc(m['start_utc'])} UTC</li>"
        for m, r in top
    )
    summary_body = f"""
<h1>Hotspawn CS2 picks — executive summary</h1>
<p class="lede">Every Counter-Strike 2 match we could capture from the Hotspawn lobby, with a pick and a win probability per team.
Probabilities come from outside betting markets (Polymarket, Oddsportal, Stake) and HLTV world-ranking points. Hotspawn's own pick percentages are not used anywhere.</p>
<div class="grid">
  <div class="card"><div class="kpi">{total}<small>matches captured</small></div></div>
  <div class="card"><div class="kpi">{n_res}<small>with picks</small></div></div>
  <div class="card"><div class="kpi">{n_unres}<small>unresolved (see limitations)</small></div></div>
  <div class="card"><div class="kpi">{len(DATA['matches'])}/68<small>matches captured vs lobby header</small></div></div>
</div>
<div class="btns">
  <a href="picks.html"><b>Picks →</b><span>{n_res} matches with a pick and win % per team, source link on every row</span></a>
  <a href="unresolved.html"><b>Unresolved →</b><span>{n_unres} matches with no usable outside line, and why</span></a>
  <a href="matches.html"><b>All matches →</b><span>Every captured match with each source's raw prices</span></a>
  <a href="analysis.html"><b>Analysis →</b><span>Market vs model comparison, HLTV ranking input</span></a>
  <a href="flagged.html"><b>Flagged for Review →</b><span>Irregularities and data-quality flags (do not block publishing)</span></a>
  <a href="methodology.html"><b>Methodology →</b><span>How each line is built, rules and thresholds</span></a>
</div>
<h2>Key findings</h2>
<ul class="clean">
  <li><b>Coverage is partial.</b> The Hotspawn lobby header says 68 matches this week, but its tier and tournament counts sum to 88. We captured {len(DATA['matches'])} match cards. Matches outside the captured window are not on this site (see Flagged, I-03 and I-04).</li>
  <li><b>{n_res} picks</b> have at least one usable outside market. {model_used} of them also use the HLTV points model (both teams in HLTV's top 30).</li>
  <li><b>{n_unres} matches are unresolved</b>: no usable outside line (most are Elisa BreakOut and CCT Play-In matches with $0 Polymarket volume), or a team we could not tie to a market or ranking. See the Unresolved page.</li>
  <li><b>Model vs market disagreements:</b> {len(disagree)} match(es). Where they disagree we keep the blended pick and lower its confidence. Details on the Analysis page.</li>
  <li><b>Highest-confidence picks</b> (both sources agree and the margin is large):</li>
</ul>
<ul class="clean">{top_list}</ul>
<h2>Limitations</h2>
<ul class="clean">
  <li>Snapshot date is {esc(SNAP['session_date_utc'])}; the fetch tool returns no timestamp, so the lobby and prices may have moved since capture. This site is not auto-refreshed; a 4–8 hour refresh is not scheduled (I-16).</li>
  <li>Polymarket prices changed between fetches for several markets (I-11). Only markets with $50+ volume and an implied total of 95–105% are used.</li>
  <li>Pinnacle and Thunderpick were not usable from this environment (I-08, I-09).</li>
  <li>Team names differ across sources; acronym-only matches (for example WBT for WROTBERRY) are not used for picks (I-10).</li>
  <li>Lobby times are shown in UTC, converted from the ET snapshot (+4h). Cross-checked against Polymarket and Stake times (I-06).</li>
</ul>
"""
    write("index.html", "Summary", summary_body, "index.html")

    # ---- picks
    head = ["#", "Start (UTC)", "Tournament", "Match", "Pick", "Pick win %", "Opponent %", "Confidence", "Inputs (raw → normalised %)", "Source links"]
    prow = []
    for m, r in sorted(resolved, key=lambda x: x[0]["n"]):
        team, pct, opp, opct = pick_of(m, r)
        conf = confidence(r, pct)
        flag = ' <span class="flag">⚑</span>' if m.get("flags") or r["notes"] else ""
        prow.append([
            str(m["n"]), esc(m["start_utc"]), esc(m["tournament"]),
            esc(f"{m['a']} vs {m['b']}") + flag,
            f'<span class="pick">{esc(team)}</span>',
            f"{pct:.1f}", f"{opct:.1f}",
            f'<span class="pill {conf}">{conf}</span>',
            esc(input_text(r)), src_links(m, r),
        ])
    picks_body = f"""
<h1>Picks</h1>
<p class="lede">{n_res} matches with a pick. Win % is our blended line (70% outside market consensus, 30% HLTV points model where both teams are ranked). Times are UTC. ⚑ = see Flagged for Review.</p>
<p class="note">Hotspawn pick percentages are not used. Matches not listed here are on the <a href="unresolved.html">Unresolved</a> page.</p>
{table(head, prow)}
"""
    write("picks.html", "Picks", picks_body, "picks.html")

    # ---- unresolved
    uhead = ["#", "Start (UTC)", "Tournament", "Match", "Why unresolved", "What would resolve it", "Source links"]
    urow = []
    for m, r in sorted(unresolved, key=lambda x: x[0]["n"]):
        reasons = []
        pm_ok, pm_why = pm_status(m.get("pm"))
        if m.get("pm") is None:
            reasons.append(m.get("pm_note") or "No Polymarket market captured.")
        elif not pm_ok:
            reasons.append(f"Polymarket: {pm_why}.")
        if m.get("pm") and m["pm"].get("note"):
            reasons.append(m["pm"]["note"])
        if not (m.get("hltv_a") and m.get("hltv_b")):
            reasons.append("Not both teams in HLTV top 30 (no ranking model).")
        if m.get("stake") is None and m.get("op") is None:
            reasons.append("No Stake or Oddsportal line captured.")
        if m["hs_match_id"] is None:
            reasons.append("No Hotspawn match link captured (I-07).")
        resolve = "A Polymarket market with $50+ volume and 95–105% implied total, or a Stake/Oddsportal line, plus HLTV ranking for both teams."
        if m["n"] in (14, 16, 18):
            resolve += " Also confirm WBT = WROTBERRY (I-10)."
        if m["n"] == 13:
            resolve = "Polymarket or Stake market for FORZE Reload vs LFO 10 (current markets are different opponents)."
        if m["n"] == 26:
            resolve = "Polymarket volume ≥ $50 with a 95–105% total, plus a Hotspawn match link (I-07)."
        urow.append([
            str(m["n"]), esc(m["start_utc"]), esc(m["tournament"]), esc(f"{m['a']} vs {m['b']}"),
            "<br>".join(esc(x) for x in reasons),
            esc(resolve),
            hs_link(m) + (" · " + a_link(m["pm"]["url"], "Polymarket") if m.get("pm") else ""),
        ])
    unres_body = f"""
<h1 id="unresolved">Unresolved</h1>
<p class="lede">{n_unres} matches have no usable outside line, so no pick is published. They are listed here with the reason and what would resolve each one.</p>
<h2>Limitations</h2>
<ul class="clean">
  <li>Most unresolved matches are Elisa BreakOut and CCT Play-In matches with $0.00 Polymarket volume. Their implied totals are also outside 95–105%, so the prices are not reliable.</li>
  <li>Teams in these matches are mostly outside HLTV's top 30 (no ranking input), and most have no Stake or Oddsportal line in our captures.</li>
  <li>Some names cannot be mapped confidently across sources (WBT/WROTBERRY, EAC, BOJONG), so we do not use acronym-only matches.</li>
  <li>Lobby times and Polymarket prices changed between fetches (I-05, I-11). Unresolved status reflects the snapshot only.</li>
</ul>
<h2>Matches</h2>
{table(uhead, urow)}
"""
    write("unresolved.html", "Unresolved", unres_body, "unresolved.html")

    # ---- all matches
    mhead = ["#", "Start (UTC)", "Tournament", "Match", "Hotspawn", "Polymarket (¢ a / b · volume)", "Stake (decimal)", "Oddsportal (decimal)", "HLTV points", "Status"]
    mrow = []
    for m, r in sorted(rows, key=lambda x: x[0]["n"]):
        pm = m.get("pm")
        if pm:
            ok, _ = pm_status(pm)
            pmtxt = a_link(pm["url"], f"{pm['a']} / {pm['b']} · ${pm['volume_usd']:,.2f}") + ("" if ok else ' <span class="flag">⚑ excluded</span>')
        else:
            pmtxt = BLANK("No market ⚑")
        st = m.get("stake")
        sttxt = a_link(st["url"], f"{st['odds_a']} / {st['odds_b']}") if st else BLANK("Not captured ⚑")
        op = m.get("op")
        optxt = a_link(op["url"], f"{op['odds_a']} / {op['odds_b']}") if op else BLANK("Not captured ⚑")
        ra = HLTV.get((m.get("hltv_a") or "").lower()) if m.get("hltv_a") else None
        rb = HLTV.get((m.get("hltv_b") or "").lower()) if m.get("hltv_b") else None
        if ra or rb:
            ta = str(ra["points"]) if ra else "—"
            tb = str(rb["points"]) if rb else "—"
            hltvtxt = a_link(HLTV_URL, f"{ta} / {tb}")
        else:
            hltvtxt = BLANK("Not ranked ⚑")
        status = "Picked" if r["resolved"] else "Unresolved"
        mrow.append([
            str(m["n"]), esc(m["start_utc"]), esc(m["tournament"]), esc(f"{m['a']} vs {m['b']}"),
            hs_link(m), pmtxt, sttxt, optxt, hltvtxt,
            f"<b>{status}</b>",
        ])
    matches_body = f"""
<h1>All matches</h1>
<p class="lede">Every match captured from the Hotspawn lobby ({len(rows)} of 68 listed in the header), with the raw outside prices we used. Blank cells are values we could not verify and are flagged ⚑.</p>
{table(mhead, mrow)}
"""
    write("matches.html", "All matches", matches_body, "matches.html")

    # ---- analysis
    hl_rows = []
    for t in DATA["hltv_top30"]:
        hl_rows.append([str(t["rank"]), esc(t["team"]), str(t["points"]), a_link(HLTV_URL, "HLTV ranking")])
    hl_html = table(["Rank", "Team", "Points", "Source"], hl_rows)
    mk_rows = []
    for m, r in resolved:
        team, pct, opp, opct = pick_of(m, r)
        mk_rows.append([
            esc(f"{m['a']} vs {m['b']}"),
            fmt(r["market"]) if r["market"] is not None else BLANK()[1],
            fmt(r["model"]) if r["model"] is not None else BLANK("n/a — not both ranked")[1],
            f"<b>{pct:.1f}</b> {esc(team)}",
            (esc("Disagree") if (r["model"] is not None and ((m['a'] if r['market']>=50 else m['b']) != (m['a'] if r['model']>=50 else m['b']))) else ("Agree" if r["model"] is not None else "—")),
            src_links(m, r),
        ])
    analysis_body = f"""
<h1>Analysis</h1>
<p class="lede">How the market consensus and HLTV model compare for each resolved match, and the HLTV ranking input used.</p>
<h2>Market vs model, per resolved match</h2>
<p class="note">Market = mean of usable outside sources for team A (first name shown). Model = HLTV points share for team A. Our line = 70% market + 30% model.</p>
{table(["Match", "Market consensus % (team A)", "HLTV model % (team A)", "Our line", "Model vs market", "Source links"], mk_rows)}
<h2>HLTV world ranking, top 30 (Oct 12 2026)</h2>
<p class="note">Teams outside the top 30 are not ranked for this model. Every row links to the HLTV ranking page.</p>
{hl_html}
"""
    write("analysis.html", "Analysis", analysis_body, "analysis.html")

    # ---- methodology
    method = f"""
<h1>Methodology</h1>
<p class="lede">How each number on this site is produced. The build script is <code>scripts/build_site.py</code>; the raw inputs are in <code>data/picks-model.json</code>.</p>
<ol class="clean">
  <li><b>Match list.</b> Every match card captured from the Hotspawn lobby (<a href="{esc(LOBBY)}">play.hotspawn.com/lobby</a>). Times are converted to UTC. Hotspawn's own pick percentages are not read and not used.</li>
  <li><b>Polymarket.</b> Two-way prices in cents. Used only if volume is at least $50 and the two prices sum to 95–105. Normalised to 100%.</li>
  <li><b>Stake.</b> Two-way decimal odds from the Stake CS2 listing (German locale). Converted to implied probability (1/odds), normalised to 100%.</li>
  <li><b>Oddsportal.</b> Two-way decimal odds from the Oddsportal event page, normalised the same way. Where Oddsportal names no bookmaker, that is noted.</li>
  <li><b>Market consensus.</b> Equal-weight mean of the usable market sources for a match.</li>
  <li><b>HLTV model.</b> Team points share from the HLTV world ranking (Oct 12 2026), only when both teams are in the top 30: points_A / (points_A + points_B).</li>
  <li><b>Our line.</b> 70% market consensus + 30% HLTV model when both teams are ranked; market consensus alone otherwise. Shown to one decimal; the two teams sum to 100.</li>
  <li><b>Pick.</b> The team with the higher line. Confidence: High = at least two sources and a margin of 20+ points; Medium = at least two sources and 10–20 points, or one source and 20+ points; Low = everything else.</li>
  <li><b>Unresolved.</b> A match with no usable market source. These are not guessed or filled in.</li>
  <li><b>Name matching.</b> Team names are matched by name or containment (for example "Team Falcons" to "Falcons"). Acronym-only matches (WBT to WROTBERRY, EAC) are not used for picks.</li>
  <li><b>Verification.</b> Each captured value has a source link on the table row. Values that could not be verified are left blank and flagged ⚑.</li>
</ol>
<p class="note">Known weaknesses: market prices change between fetches; a 70/30 blend is a judgment call (I-13); the HLTV points share is a simple model, not a match simulation.</p>
"""
    write("methodology.html", "Methodology", method, "methodology.html")

    # ---- sources
    src_rows = [
        ["Hotspawn lobby (match list)", LOBBY, "Match list, times, tournaments, match links"],
        ["Hotspawn match page (example)", "https://www.hotspawn.com/matches/gothic-vs-lavked-cct-europe-2026-series-11-1079621", "Confirms match page format and UTC start"],
        ["Polymarket CS2 category: CCT Europe", SNAP["polymarket_pages"]["cct_europe"], "Moneyline prices, volume (CCT and Play-In matches)"],
        ["Polymarket CS2 category: Stake Pulse", SNAP["polymarket_pages"]["stake_pulse"], "Moneyline prices, volume (Stake Pulse Beat III)"],
        ["Polymarket CS2 category: Thunderpick World Championship", SNAP["polymarket_pages"]["thunderpick_wc"], "Moneyline prices, volume (TP World Championship)"],
        ["Polymarket CS2 category: Elisa BreakOut", SNAP["polymarket_pages"]["elisa_breakout"], "Moneyline prices, volume (Elisa BreakOut)"],
        ["Polymarket: Legacy vs PARIVISION match page", SNAP["polymarket_pages"]["legacy_parivision_match"], "Moneyline 57/44, volume"],
        ["Stake CS2 listing (German locale)", STAKE_URL, "Two-way decimal odds, first 10 CS2 events"],
        ["Oddsportal: Thunderpick World Championship", SNAP["oddsportal_thunderpick_wc"], "Two-way decimal odds for 9z–Aurora and Falcons–NiP"],
        ["Oddsportal: Stake Pulse Beat III", SNAP["oddsportal_stake_pulse"], "Checked; no odds published at capture"],
        ["HLTV world ranking, Oct 12 2026", HLTV_URL, "Team points for the top 30"],
        ["Pinnacle esports (not used)", "https://www.pinnacle.com/en/esports", "Not reachable (404 / HTTP 500)"],
        ["Thunderpick CS2 event pages (not used)", "https://thunderpick.io/esports/cs2-betting/thunderpick-world-championship-2026/11024", "Navigation only; no match list or odds at capture"],
    ]
    src_html = table(["Source", "URL", "Used for"], [[esc(a), a_link(b, b), esc(c)] for a, b, c in src_rows])
    write("sources.html", "Sources", f"""
<h1>Sources</h1>
<p class="lede">Every page fetched for this snapshot. Each row links to the source.</p>
{src_html}
""", "sources.html")

    # ---- flagged
    flag_items = [
        ("I-01", "Repo state", "The repo had no picks, site, or coordination file at session start.", HLTV_URL),
        ("I-02", "Branch naming", "Task text names a merge to main; the session is fixed to arena/83207e7b-maltaproj3, which is the PR source.", LOBBY),
        ("I-03", "Match count mismatch", "Lobby header says 68 matches; tier and tournament counts sum to 88.", LOBBY),
        ("I-04", "Coverage", f"{len(DATA['matches'])} match cards captured. The lobby is a rolling window; the rest are not on this site.", LOBBY),
        ("I-05", "Lobby changes", "Lobby times and closing-soon labels changed between fetches; the fetch returns no timestamp.", LOBBY),
        ("I-06", "Time zones", "The first lobby snapshot was in ET; later snapshots were UTC. Converted +4h; cross-checked against Polymarket and Stake.", STAKE_URL),
        ("I-07", "Missing match link", "mellren vs Privateer Gaming (Oct 16) has no captured Hotspawn match link.", LOBBY),
        ("I-08", "Pinnacle unavailable", "Pinnacle paths returned 404 or HTTP 500. Not used.", "https://www.pinnacle.com/en/esports"),
        ("I-09", "Thunderpick unavailable", "Thunderpick CS2 pages returned navigation only. Not used.", "https://thunderpick.io/esports/cs2-betting/thunderpick-world-championship-2026/11024"),
        ("I-10", "Name mapping", "Team names differ across sources (Team Falcons/Falcons, Aurora Gaming/Aurora, Sashi Esport/Sashi, WRAITH PCIFIC/PCIFIC, BetBoom Team/BetBoom, BC.Game Esports/BC.Game, NIP/Ninjas in Pyjamas, WBT/WROTBERRY). Acronym-only matches are not used.", "https://polymarket.com/esports/cs2/elisa-breakout"),
        ("I-11", "Polymarket price drift", "Same markets showed different prices across fetches (for example ENCE vs BOJONG 65/36, 74/45, 75/46). Latest readings are used, with earlier readings in notes.", "https://polymarket.com/esports/cs2/elisa-breakout"),
        ("I-12", "Thin or unbalanced markets", "Many Elisa and CCT markets have $0.00 volume or implied totals outside 95–105%. Excluded.", "https://polymarket.com/esports/cs2/elisa-breakout"),
        ("I-13", "Model vs market disagreement", "Heroic vs Envy: market favours Heroic, HLTV points favour Envy. Blended pick is Heroic, with lower confidence.", "https://polymarket.com/esports/cs2/stake-pulse"),
        ("I-14", "Stake coverage", "Stake's CS2 list shows 10 events per page; only six Hotspawn matches were on it.", STAKE_URL),
        ("I-15", "Oddsportal coverage", "Oddsportal has odds for two Hotspawn matches only.", SNAP["oddsportal_thunderpick_wc"]),
        ("I-16", "No automatic refresh", "A 4–8 hour refresh was requested. It is not scheduled from this session; the snapshot date is shown on every page.", LOBBY),
        ("I-17", "G2 Ares identity", "'G2 Ares' (Hotspawn) is not confirmed as HLTV's G2 (#8). No HLTV points applied.", HLTV_URL),
        ("I-18", "Hotspawn pick percentages", "Hotspawn shows its own pick percentages; they are not used anywhere in the model.", LOBBY),
    ]
    frows = [[esc(i), esc(t), esc(d), a_link(u, "Source")] for i, t, d, u in flag_items]
    mrows = []
    for m, r in flagged_matches:
        bits = ", ".join(m.get("flags") or [])
        extra = " ".join(esc(x) for x in r["notes"])
        mrows.append([str(m["n"]), esc(f"{m['a']} vs {m['b']}"), esc(bits), extra or "—", hs_link(m)])
    flagged_body = f"""
<h1>Flagged for Review</h1>
<p class="lede">Irregularities and data-quality items. They are published here and do not block publishing or merging.</p>
<h2>Site and process</h2>
{table(["ID", "Item", "Detail", "Source"], frows)}
<h2>Matches with flags</h2>
{table(["#", "Match", "Flag IDs", "Notes", "Source"], mrows)}
"""
    write("flagged.html", "Flagged for Review", flagged_body, "flagged.html")

    # static and marker
    (OUT / ".nojekyll").write_text("")
    print(f"built {len(PAGES)} pages: {n_res} picks, {n_unres} unresolved, {total} matches")


def write(name, title, body, active):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(page(name, title, body, active), encoding="utf-8")


def check_links():
    bad = []
    ids = {}
    for f in OUT.glob("*.html"):
        ids[f.name] = set(re.findall(r'id="([^"]+)"', f.read_text(encoding="utf-8")))
    for f in OUT.glob("*.html"):
        for href in re.findall(r'href="([^"]+)"', f.read_text(encoding="utf-8")):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target, _, frag = href.partition("#")
            tname = target or f.name
            if not (OUT / tname).exists():
                bad.append(f"{f.name}: missing {href}")
            elif frag and frag not in ids.get(tname, set()):
                bad.append(f"{f.name}: missing anchor {href}")
    return bad


if __name__ == "__main__":
    build_all()
    if "--check" in sys.argv:
        problems = check_links()
        if problems:
            print("\n".join(problems))
            sys.exit(1)
        print("links ok")
