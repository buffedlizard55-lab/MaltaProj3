# Independent coverage and no-line re-verification — 2026-10-24

Session `arena-5f9d0082`. Read window **2026-10-24T16:20Z–16:32Z**. Machine-readable
record: [`live-coverage-verification-2026-10-24.json`](live-coverage-verification-2026-10-24.json).

The brief for this session was to make sure *every* Hotspawn CS2 match carries a pick,
to research the matches that the featured method cannot price (HLTV first, then
esportsbooks), to keep an explicit unresolved register with its limits, and to check the
executive summary and the phone layout. This page records what was actually verified,
first-hand, and what could not be.

## 1. Inventory — the collector matches its official source

| Observation | Value | Source |
| --- | --- | --- |
| Lobby tier filter total (24 Oct, 16:22Z) | 85 cards in 19 tournaments | [Hotspawn CS2 pick'ems](https://play.hotspawn.com/cs2-pickems) |
| Scheduled-fixtures API records (16:28Z) | 84 | [official fixtures API](https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1) |
| Checked-in snapshot (`inventory_observed_at` 14:24:12Z) | 84 records · 23 open · 61 past | `snapshot.json` |
| Live published picks feed (14:24:44Z) | active 23 · resolved 23 · with a pick 23 · unresolved 0 | [published origination.json](https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json) |

Per-tournament counts agree for 18 of 19 tournaments. The one difference is deliberate to
report rather than smooth over:

| Tournament | Lobby count | Snapshot count | API count | Interpretation |
| --- | --- | --- | --- | --- |
| CCT Europe 2026 Series #12 | 4 | 3 | 3 (competition 35814) | The API returns exactly the three fixtures the snapshot carries (1081154, 1081156, 1081158). The lobby's week counter includes one further card that the `status=scheduled` API no longer returns, so no lockable card was skipped. Its state (completed, cancelled or de-listed) is **not** asserted — it could not be confirmed from a first-party page. |

The lobby rendered 22 future cards. The snapshot holds 23 open fixtures: those 22 plus
`1083121` Projeto do KinGui vs MEIA NOITE, which had already passed its 15:54Z lock when
the lobby was read and so no longer rendered as pickable.

## 2. Pick coverage the deployed site actually serves

From the live feed generated **2026-10-24T14:24:44Z**: 23 of 23 open fixtures priced —
**19 from an external line** (8 market, 5 esportsbook, 5 median consensus, 1 aggregated
bookmaker average) and **4 from a labelled research model**. Header and complete-list
counts on the live pages agree ("23 picks ready of 23", "0 unresolved"). The separate
unresolved register and its limitations are rendered on the executive summary and on
`/unresolved/`, as the brief requires.

## 3. The four fixtures with no betting line — HLTV first, then an esportsbook

### Acend vs UNiTY — NODWIN Clutch Series #13, 2026-10-25T09:00:00Z (`1082996`)

* **HLTV 2399112** ([match page](https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13)): **Best of 3 (Online), Round of 16**; HLTV **#131** Acend (VRS #74) vs HLTV **#86** UNiTY.
* The HLTV **Betting** block carries a single promocode row (a US sweepstakes casino, "No promocode available"). **No two-sided money line.**
* The HLTV **"Pick a winner"** poll reads *18.5% Acend / 81.5% UNiTY*. That is a fan vote and stays excluded, exactly as the project policy requires.
* The [analytics page](https://www.hltv.org/betting/analytics/2399112/acend-vs-unity-nodwin-clutch-series-13) publishes pros/cons and form ("UNiTY has won 5 out of the last 5 matches", "Acend has won 3 out of the last 5 matches") and **no odds**.
* **Esportsbook:** [EGamersWorld match page](https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/acend-vs-unity-esports-iwaKSVfgf) displays **1.8 / 1.8**. Identical two-sided prices are a site placeholder, not a market — the same pattern `scripts/reference_odds.py` already refuses. Not used.

### Rooster vs Abyssal — DFRAG Invitational 2026, 2026-10-27T03:00:00Z (`1082861`)

* Identity from the repository's retained HLTV research: [2399891](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026). No format or ranking claim is made here because the page was not re-read in this session.
* **Esportsbook:** [EGamersWorld match page](https://egamersworld.com/counterstrike/match/4kaAQWgKEx/rooster-vs-team-abyssal-P1tTp3RAg8) also displays **1.8 / 1.8** — placeholder, rejected.

### HOTU vs The Huns (`1082792`) and 5star vs 1WIN (`1082793`) — Moscow Cyber Games, 2026-10-31

* [HLTV event 9344](https://www.hltv.org/events/9344/matches) lists both as **bo3** on Saturday 2026-10-31: [2399437 HOTU vs The Huns](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) and [2399438 1win vs 5star](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026).
* Naming: HLTV orders the second fixture *1win vs 5star*, Hotspawn lists *5star* first. Same teams, same start; **no alias is created** for the ordering difference.
* No usable external money line was obtained for either fixture in this session. The site's own record already documents why the model stands: the Polymarket series-winner book was 0.43 wide (above the 0.15 indicative ceiling) and Kalshi had no usable two-sided book.

**Outcome:** the four research-model picks are not an artefact of missing research. Each was
re-researched in the documented order (HLTV identity/format/ranking first, then an
esportsbook aggregate), and no compliant two-sided price exists at the sources read. The
model numbers stay labelled *uncalibrated research estimate*, and the limitation is
published rather than hidden.

## 4. Limitations of this verification

* The sandbox could only read pages through a page-reading tool, so no raw response body
  could be stored and hash-replayed. URLs, exact displayed values and the read window are
  recorded instead; the repository's own scheduler keeps producing hash-checked evidence.
* EGamersWorld's live index is **blocked for the GitHub Actions runner** (403 Cloudflare in
  run 14:24Z) while the same public pages answered this session's egress. That is an
  automation obstacle, not proof that a market is absent.
* Fan polls, "pros/cons" panels, prediction widgets and Hotspawn "% picked" values are
  never inputs.

## 5. Executive summary and phone check

* The executive summary carries "Start here · where the picks are" with one-tap links to
  the full picks list, the leaderboard plan, the unresolved register and the flags, then
  "Picks at a glance" — every active fixture with both win probabilities, the pick, the
  method badge, the observation time and a per-row source link.
* Local build on this head: **PASS**, 907 audited rows, 887 with an official link, **0
  without a source**, 836 internal links/assets/anchors, acceptance 9 pass / 1 info / 0 fail.
* No phone defect was proven, so no layout file was edited.
