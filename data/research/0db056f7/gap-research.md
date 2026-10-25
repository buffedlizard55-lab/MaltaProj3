# Gap-pick research — arena-0db056f7 (2026-10-25)

Scope per the brief: research **only** the matches that cannot be resolved the same way as the
featured picks — HLTV first, then esportsbooks / exchanges. Hotspawn `% picked` and HLTV fan
votes are never used as probability inputs. No probability below was hand-written into the
pipeline; the only wired number is the hash-checked EGamersWorld capture in
[`reference-odds.json`](reference-odds.json), which the publisher replays itself.

## Why these fixtures had no pick on the live site at all

The live site was frozen on the `2026-10-25T05:12:25Z` snapshot: `pages.yml` runs
`40174233578` (07:49Z) and `40196457503` (13:11Z) both failed at the *Regression tests* step
(`republish-last-verified` succeeded, so the site kept serving the last verified build,
visibly stale). The Hotspawn API read at `2026-10-25T13:38Z`
(`https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1`)
carries three fixtures that are **not in the deployed 79-fixture snapshot**:

| Fixture | Match | Competition | Starts (UTC) | Tier |
| --- | --- | --- | --- | --- |
| 1086696 | BORRACHEIROS vs RED Canids Academy | CCT South America 2026 Series #7 | 2026-10-25T16:00:00Z | C |
| 1082697 | BESTIA vs paiN | Circuit X Curitiba #4 | 2026-10-25T18:00:00Z | C |
| 1086697 | Projeto do KinGui vs Yawara | CCT South America 2026 Series #7 | 2026-10-25T19:00:00Z | C |

## Per-fixture results (HLTV first, then books/exchanges)

### 1086696 — BORRACHEIROS vs RED Canids Academy (today 16:00Z) — RESOLVED via EGW capture
- **HLTV:** fixture confirmed in *CCT 2026 South America Series 7* (event 9452), semifinal, BO3.
- **Polymarket:** `public-search?q=BORRACHEIROS` / `?q=RED%20Canids` at 13:44Z surfaced only the
  Oct 24 quarter-finals (`cs2-ln-chama-2026-10-24`, `cs2-reda-isg-2026-10-24`, both closed) — no
  verified first-party exact-name market for today's semifinal.
- **EGamersWorld:** match page
  https://egamersworld.com/counterstrike/match/0U32SId-H/borracheiros-vs-red-canids-academy-5tMfbA07u
  carries the EGWxxxBOT bookmaker-average sentence, and its header odds agree with it:
  BORRACHEIROS **2.1** / RED Canids Academy **1.62** (page countdown 2:20:08 at read ⇒ 16:00Z start ✓).
  Captured in `reference-odds.json` at `2026-10-25T13:40:00Z` (SHA-256-checked excerpt).
  Publisher replay: no-vig **43.5% / 56.5% → pick RED Canids Academy** (aggregated rung; any
  first-party line opening before the 15:54Z lock outranks it automatically).
- **Limitations:** EGW is an aggregation of bookmaker prices, not a first-party quote; it can lag
  late line moves. Tier-C South American fixture; thin coverage everywhere.

### 1082697 — BESTIA vs paiN (today 18:00Z) — RESOLVES on the money ladder (no capture needed)
- **HLTV:** Circuit X Curitiba Season 4 lower-bracket final; both teams' event form is on HLTV
  (e.g. matches 2399818, 2399816).
- **Polymarket:** event **1249433** (`cs2-pain-bst-2026-10-25`) lists exact names *paiN / BESTIA*,
  `eventStartTime 2026-10-25T18:00:00Z`, ≈$155k liquidity, tight books → the featured exact-name
  method binds it on the next publisher run.
- **Bovada:** lists *paiN Gaming vs Bestia*; the competition-scoped alias `paiN Gaming → paiN`
  (Circuit X Curitiba #4) already exists in `data/origination/aliases.json`.
- **EGamersWorld:** header 1.76/1.91 and tip page 1.64/2.15 disagree and no EGWxxxBOT sentence is
  published → recorded as **rejected** in `reference-odds.json` (not needed; reference rung never
  replaces a first-party line).
- **Limitations:** none beyond the frozen-publisher delay; resolves automatically once publishing resumes.

### 1086697 — Projeto do KinGui vs Yawara (today 19:00Z) — NO compliant line found (yet)
- **HLTV:** covered under CCT 2026 South America Series 7 (event 9452).
- **EGamersWorld:** 1.8/1.8 header, no bookmaker-average sentence → placeholder, **rejected**.
- **Polymarket:** no Oct 25 event surfaced for either team name at 13:44Z. If one opens, the
  existing scoped aliases `Yawara Esports → Yawara` and `Tropa do KinGui → Projeto do KinGui`
  (CCT South America 2026 Series #7) let it bind.
- **Fallback:** the publisher's Valve-rating / bo3.gg network rungs decide if no money line appears;
  if neither model can price it, the row stays explicitly unresolved with this trail.
- **Limitations:** tier-C fixture between two low-coverage rosters; books may simply never price it.
  This is the coverage floor the brief asks to state plainly: *a pick is generated only from a
  verified line or a labelled model — never from a placeholder or a crowd split.*

### 1082792 — HOTU vs The Huns (2026-10-31T09:00Z) — model-only; extreme estimate flagged
- **HLTV:** match **2399437** (GLuck Moscow Cyber Games 2026, event 9344) confirms teams/time/BO3.
- **EGamersWorld:** 1.8 placeholder → **rejected**. **Polymarket:** `cs2-hotu-the9-2026-10-31` exists
  and alias `The Huns Esports → The Huns` is already wired, but the book was non-compliant at the
  05:12Z publisher read. Official event site (esports.gamehubmoscow.ru) lists HOTU #27 vs
  The Huns Esports #152.
- **Current published pick:** bo3.gg network model **98.2% HOTU**. **Flagged:** 98.2% is an extreme,
  uncalibrated network estimate for a LAN BO3 six days out; treat the direction (HOTU) as
  model-supported and the magnitude as unreliable until a book prices it. Re-checked every 4h run.
- **Limitations:** featured method also blocked by Valve-identity ambiguity ("multiple Valve rosters
  share this name") for The Huns in the featured snapshot; the complete-pick layer resolves identity
  via the scoped alias + HLTV 2399437 instead.

### 1082861 — Rooster vs Abyssal (2026-10-27T03:00:00Z) — model-only
- **HLTV:** DFRAG coverage exists (event pages/match pages for the DFRAG circuit).
- **EGamersWorld:** 1.8 placeholder → **rejected**. **Polymarket:** event exists at **$0.00 volume**
  with a 50/50 stub → not a compliant two-sided price.
- **Current published pick:** Valve-rating model, Abyssal 52.2% / Rooster 47.8% (near coin-flip;
  earlier sessions also flagged two stand-ins on the Rooster HLTV lineup — see COORDINATION c2a74e33).
- **Limitations:** oceanic tier-B fixture ~37h out at research time; books often price DFRAG only in
  the final hours. Every publisher run re-checks the money ladder first.

### 1082793 — 5star vs 1WIN (2026-10-31T13:00:00Z) — model-only
- **HLTV:** match **2399438** confirms the fixture (HLTV fan percentages exist there but are never
  used as inputs here).
- **EGamersWorld:** 1.8/1.8 placeholder → **rejected**. **Polymarket:** $0.00-volume stub (1.04x).
- **Current published pick:** Valve-rating model, 1WIN 82.2% / 5star 17.8% (#38 vs #80 in the
  retained official standings read).
- **Limitations:** six days out; expect real lines closer to the LAN. Until then the number is a
  labelled research estimate, not a bettable price.

## Method notes & reachability (2026-10-25, 13:38–13:50Z)
- Sandbox direct egress to Hotspawn/HLTV/Polymarket/EGW is unavailable (`curl` → `000`); all reads
  above were first-hand browser fetches of the original pages/APIs, matching the project's
  "original response" rule as closely as this environment allows. GitHub Actions gets HTTP 403 from
  egamersworld.com (documented `egw_live_error: 403`), which is why EGW evidence enters only as a
  dated, hash-checked manual capture with an 8-hour freshness gate.
- Sources actually read: Hotspawn fixtures API (full inventory), HLTV matches/event/team pages,
  Polymarket Gamma (`public-search`, event 1249433), EGamersWorld match + tip pages for all six
  fixtures, Bovada CS2 board (via search index), official Moscow Cyber Games site, Liquipedia
  (bracket corroboration only, never a price source).
- Nothing was inferred: where a page showed a placeholder (1.8/1.8, $0 stubs), the fixture is
  recorded as *no compliant line today*, not as a price.
