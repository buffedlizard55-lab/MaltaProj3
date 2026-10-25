# Session arena-824a2780 — line-by-line verification of the published CS2 picks

**Review clock:** 2026-10-25T14:5xZ. **Snapshot verified:** `2026-10-25T14:23:33Z`, the build
`main` root-synced after PR #331. **Checker:** `scripts/824a2780_verify.py` (this session),
asserted by `tests/test_824a2780_verification.py`.

Nothing below is transcribed by hand: the table is printed by the checker from the published
data, and the checker is proven to have teeth by four tamper tests (a changed probability, a
changed midpoint, a Hotspawn-attributed price and a flipped pick are each rejected).

Every number on this page is dated to that observation. Hotspawn's scheduled inventory is
re-collected every four hours and rows leave it once they start, so the live list will differ:
the durable artefacts are the checker and its tests, which re-derive whichever rows are live
(`python -m scripts.824a2780_verify --check`).

This page also keeps the independent check of the **previous** observation
(`2026-10-25T05:12:25Z`), because that is the build during which the four-hour publisher was
stopped, and the difference between the two is itself evidence that the rules work.

## What was verified, and against what

| Check | Method | Result (14:23:33Z build) |
| --- | --- | --- |
| Inventory and counts | Re-counted every row and compared with `counts` | 78 records = 16 active + 62 archived; 13 with a side, 3 without; no duplicate id; every row names two teams and an https fixture source |
| Every priced row replays | Recomputed both probabilities from the row's own published inputs | **13 / 13 exact** (10 exchange midpoint-normalised, 1 no-vig decimal odds, 2 Valve Glicko) |
| Valve rating inputs | Fetched the official file the rows cite ([`standings_global_2026_10_05.md`](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md), blob `2aa2805`, read 2026-10-25T13:2xZ; it is still the newest published table) and matched standing, points and roster | **4 / 4 inputs match** — Rooster #205 718, Abyssal #195 734, 5star #80 1110, 1WIN #38 1383 |
| Valve formula | Recomputed `g` (RD 75 → 0.9728209910486895) and `p = 1/(1+10^(gΔ/400))` independently of the code path | Both model rows reproduce to < 1e-6 |
| Every pick is the favourite | Compared `pick_index` with the row's own two probabilities | **13 / 13** name the strict favourite; no side on a tie |
| Every blank is justified | Re-read the research trail and the limitation of each pick-less row, then checked the reason against the primary source | **3 / 3** carry 8 named sources each and a reason that holds (below) |
| No crowd input | Rejected any analysis whose source is Hotspawn or that carries a "% picked"/crowd field | 0 occurrences |
| Site coverage | Every active id on the built `picks/` page; every pick-less id in the unresolved register; both linked from the executive summary | 16 / 16 and 3 / 3 |
| Row and link audits | `scripts.audit_rows --site site --strict`, the build's own link checker | 0 rows without a source, 0 broken links |
| Phone layout and accessibility | Playwright at 320, 375, 390, 768 and 1440 px with axe WCAG 2A/2AA | 0 horizontal overflow, 0 violations |

Reproduce:

```
python -m scripts.824a2780_verify --site . --rows data/research/824a2780/rows.json --check
```

## Every active Hotspawn CS2 fixture, replayed

| Hotspawn id | Fixture | Start (UTC) | Method | Published (team 1 / team 2) | Pick | Replay | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1079199 | Infinite vs BRUTE | 10-25 15:00Z | market | 44.5% / 55.5% | BRUTE | replayed | https://polymarket.com/event/cs2-inf6-brute-2026-10-25 |
| 1086696 | BORRACHEIROS vs RED Canids Academy | 10-25 16:00Z | market | 43.5% / 56.5% | RED Canids Academy | replayed | https://polymarket.com/event/cs2-chama-reda-2026-10-25 |
| 1079200 | Color vs ex-Zero Tenacity | 10-25 18:00Z | market | 50.5% / 49.5% | Color | replayed | https://polymarket.com/event/cs2-color-zerote-2026-10-25 |
| 1081158 | FORZE Reload vs ex-RUSTEC | 10-25 18:00Z | market | 56.5% / 43.5% | FORZE Reload | replayed | https://polymarket.com/event/cs2-forzer-rustec-2026-10-25 |
| 1082697 | BESTIA vs paiN | 10-25 18:00Z | market | 41.5% / 58.5% | paiN | replayed | https://polymarket.com/event/cs2-pain-bst-2026-10-25 |
| 1086697 | Projeto do KinGui vs Yawara | 10-25 19:00Z | blank | — | — | replayed | — |
| 1082858 | Ground Zero vs Off Chops | 10-26 03:00Z | blank | — | — | replayed | — |
| 1082859 | NEXVOID vs Alter Ego | 10-26 03:00Z | bookmaker | 57.9% / 42.1% | NEXVOID | replayed | https://thunderpick.io/api/matches |
| 1082860 | FlyQuest vs Staqued | 10-27 03:00Z | market | 92.5% / 7.5% | FlyQuest | replayed | https://polymarket.com/event/cs2-fly-staque-2026-10-26 |
| 1082861 | Rooster vs Abyssal | 10-27 03:00Z | model | 47.8% / 52.2% | Abyssal | replayed | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md |
| 1082897 | B8 vs K27 | 10-27 08:00Z | market | 59.5% / 40.5% | B8 | replayed | https://polymarket.com/event/cs2-b8-k271-2026-10-27 |
| 1082898 | Alliance vs FaZe | 10-27 11:00Z | market | 37.5% / 62.5% | FaZe | replayed | https://polymarket.com/event/cs2-all-faze-2026-10-27 |
| 1082900 | Luminosity vs HOTU | 10-27 17:00Z | market | 52.5% / 47.5% | Luminosity | replayed | https://polymarket.com/event/cs2-lg6-hotu-2026-10-27 |
| 1082901 | Envy vs GamerLegion | 10-27 20:00Z | market | 45.5% / 54.5% | GamerLegion | replayed | https://polymarket.com/event/cs2-envy-gl1-2026-10-27 |
| 1082792 | HOTU vs The Huns | 10-31 09:00Z | blank | — | — | replayed | — |
| 1082793 | 5star vs 1WIN | 10-31 13:00Z | model | 17.8% / 82.2% | 1WIN | replayed | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md |

`blank` means the dashboard publishes no probability and no pick for that fixture; it is listed
in the site's *Unresolved picks & limitations* register with the sources that failed.

## The three fixtures with no pick, and why (checked against the primary source)

**1086697 · Projeto do KinGui vs Yawara · CCT South America 2026 Series #7 · 2026-10-25T19:00Z.**
Eight sources tried: Polymarket (no exact-name, exact-start fixture), HLTV (`/matches` 403 in
this run), Thunderpick (no validated paired prematch price), GG.BET (403), Pinnacle and Rivalry
(generic landing pages), Stake (403) and the Valve research model. The model refused because
**`Projeto do KinGui` has no row in Valve's published table** — verified: the file lists
`Yawara` once (#147, 845) and no KinGui row, under any spelling (`KinGui`, `Kingu`). Note that
HLTV names a different team, `Tropa do KinGui`; this dashboard does **not** treat those as the
same team without official proof, which is exactly why the row stays blank.

**1082858 · Ground Zero vs Off Chops · DFRAG Invitational 2026 · 2026-10-26T03:00Z.** The
Polymarket book for this fixture is now recorded as *crossed or wider than 12 cents*, so the
exchange rung fails closed; the other seven sources failed as above, and the model refused
because **`Off Chops` has no Valve row** (verified: `Ground Zero` is #136, 878; no `Off Chops`
row exists). On the earlier `05:12:25Z` observation this same fixture *was* priced 25.0% / 75.0%
from two-sided quotes 0.22–0.28 / 0.72–0.78 — the ladder re-decides every refresh, and a book
that widens is not carried forward as if it were still tight.

**1082792 · HOTU vs The Huns · Moscow Cyber Games 2026 · 2026-10-31T09:00Z.** Same eight
sources, same refusals. Valve publishes **two** complete five-player rosters under the name
`The Huns`: #122 (944 points, Annihilation/Bart4k/bexyz/controlez/Cozen) and #213 (701 points,
Bart4k/controlez/nin9/sk0R/xerolte). Nothing in the published data says which one plays on
31 October, so the ambiguity is real and is published as the limitation. `HOTU` is present once
(#31, 1437).

None of the three is priced by invention, and none is dropped: all three appear on the site with
their pick-less state, their 8 named sources and their limitation.

## Irregularity carried forward for review (`824A-R02`)

**1082860 · FlyQuest vs Staqued · Thunderpick · 2026-10-27T03:00Z** (active on the
`05:12:25Z` observation, no longer in the `14:23:33Z` inventory). The published pair
92.3% / 7.7% is arithmetically correct for the quote `1.001 / 12.00`, but `1.001` is a
bookmaker **minimum price**, so the favourite's implied probability is clipped by the odds
floor. The row's limitation ("margin removed by proportional normalization; a single source is
not a consensus") does not mention the floor. Published as observed and flagged, not changed.

## Limits of this verification (stated, not hidden)

* This session's sandbox had **no outbound access** to `play.hotspawn.com`, `hltv.org`,
  `polymarket.com`, `thunderpick.io` or any esportsbook (`curl` returned `000` for each). Every
  price-level claim above therefore replays the **first-party captures the CI refresh stored**
  in `snapshot.json` and `data/evidence/`. The only live fetch made was the official Valve
  repository over `api.github.com`. No price, lineup or probability was invented.
* The publisher that produced the `14:23:33Z` snapshot was red at the regression gate from
  08:17Z (runs 40174233578 and 40196457503). That failure was reproduced by this session at
  13:26Z and is fixed on `main` by PR #326 (an equivalent guard, adopted here verbatim); the
  check that would catch a repeat is the always-on invariant in
  `tests/test_b72154e1_guided_picks.py` plus this session's replay tests.
* HLTV is intermittently reachable from the runner: `/matches` is recorded unavailable in these
  snapshots while the same workflow's source-audit manifest recorded HTTP 200 at 07:55Z. A blank
  caused by a 403 is a source-access limitation and is published as one.
* Browser verification ran locally against a build of this snapshot and is re-run by the pull
  request's own check against the deployed pages.
