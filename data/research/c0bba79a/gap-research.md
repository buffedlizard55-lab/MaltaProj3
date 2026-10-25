# Gap-pick research (HLTV first, then esportsbooks) — arena-c0bba79a, 2026-10-25

Scope per the brief: research **only** the matches that cannot be resolved the same way as the
featured exact-name market picks. Order enforced: **HLTV first, then esportsbooks/exchanges.**
All reads are first-hand through the platform page fetcher at the stated times. Hotspawn
`% picked` and HLTV fan votes are recorded as excluded and never enter a probability.
**No probability, pick or alias was hand-written by this session**; every number below is either
a verbatim quote of a source page or a pointer to what the publisher's own ladder will do.

## Why these fixtures needed non-featured research

The deployed `2026-10-25T05:12:25Z` snapshot leaves two featured rows unresolved
(`1081156`, `1082792`), prices five rows from research models instead of a market line
(`1082996`, `1079198`, `1085542`, `1082861`, `1082793`), and does not contain three live lobby
fixtures at all (`1086696`, `1082697`, `1086697`, see `live-reconciliation.json`). This dossier
covers those fixtures only.

## Per-fixture verdicts (this session's own reads, 2026-10-25T14:16Z–14:30Z)

### 1086696 — BORRACHEIROS vs RED Canids Academy (today 16:00Z, CCT South America 2026 Series #7, tier C)
- **HLTV first:** event [9452 CCT 2026 South America Series 7](https://www.hltv.org/events/9452/cct-2026-south-america-series-7)
  read first-hand: Oct 13th–Oct 25th 2026, $15,000, 24 teams, South America (Online); the playoff
  bracket renders both **BORRACHEIROS** and **RED Canids Academy** as semifinalists (R16:
  BORRACHEIROS 2–0 QUINTESSÊNCIA, RED Canids Academy over Isurus in the quarter-final leg shown).
  HLTV publishes **no two-way price** on the event page (identity/format only).
- **Then books/exchanges:** Polymarket `public-search?q=BORRACHEIROS` and `?q=RED%20Canids`
  surfaced only the closed Oct 24 quarter-final events — no open first-party market at read time.
  EGamersWorld match page
  https://egamersworld.com/counterstrike/match/0U32SId-H/borracheiros-vs-red-canids-academy-5tMfbA07u
  carries the EGWxxxBOT bookmaker-average sentence **2.1 / 1.62** — already captured hash-checked
  in PR #332's `data/research/0db056f7/reference-odds.json` (observed 2026-10-25T13:40:00Z) and
  registered in `scripts/reference_odds.py::CAPTURE_PATHS`; the publisher's reference rung replays
  it to a no-vig pair and a directional pick. This session did **not** re-capture (the capture is
  owned by that PR) and did not verify the EGW body first-hand (EGW answers 403 to this sandbox's
  fetcher as well — recorded as a limitation, never as "no market").
- **Verdict:** resolved via the registered EGW aggregate capture on the next publisher run;
  limitation: aggregator price, may lag late moves; tier-C SA fixture, thin coverage.

### 1082697 — BESTIA vs paiN (today 18:00Z, Circuit X Curitiba #4, tier C)
- **HLTV first:** Circuit X Curitiba Season 4 lower-bracket final is covered on HLTV (event/match
  pages for the circuit, e.g. matches 2399818/2399816 for both teams' event form, read by the
  owning session and re-confirmed here at event level); HLTV shows no two-way price.
- **Then books/exchanges:** Polymarket event
  [`1249433` cs2-pain-bst-2026-10-25](https://polymarket.com/event/cs2-pain-bst-2026-10-25)
  re-read first-hand via `https://gamma-api.polymarket.com/events/1249433` at **14:18Z**:
  - title `Counter-Strike: paiN vs BESTIA (BO3) - Circuit X Curitiba Playoffs`,
  - `eventStartTime 2026-10-25T18:00:00Z` — **exact match with Hotspawn's scheduled start (0 s delta)**,
  - outcome names exactly `paiN` / `BESTIA` (both sides exact-name matches),
  - Match Winner market: `outcomePrices ["0.585","0.415"]`, liquidity `$95,350.95`, volume `$42,304.43`,
    `bestBid/bestAsk` tight, `active:true, closed:false`,
  - event-level liquidity `$150,597.36`, resolution source HLTV.
- **Verdict:** the featured exact-name method itself binds this market on the next publisher run
  (no fallback needed). Limitation: the match description says "initially scheduled ... 3:00 PM ET"
  (= 19:00Z wording) while its own `eventStartTime`/`gameStartTime` are 18:00Z and Hotspawn says
  18:00Z — recorded as a rule-text wording quirk; the machine timestamps agree with Hotspawn, so
  the join uses the API start, never the sentence.

### 1086697 — Projeto do KinGui vs Yawara (today 19:00Z, CCT South America 2026 Series #7, tier C)
- **HLTV first:** team page [13151 Tropa do KinGui](https://www.hltv.org/team/13151/tropa-do-kingui)
  read first-hand at 14:2xZ: FAQ states *"The next matches for Tropa do KinGui will be against:
  25 Oct vs. Yawara"* linking HLTV match
  [2399918](https://www.hltv.org/matches/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7)
  — the identity binding for Hotspawn's `Projeto do KinGui` (competition-scoped alias
  `Tropa do KinGui → Projeto do KinGui` already exists in `data/origination/aliases.json`, proven by
  HLTV 2399904/2399913 + Polymarket 1232953 + bo3.gg). HLTV shows **no world ranking** for the
  team (peak #164, current `-`) and publishes **no odds** on the team page.
- **Then books/exchanges:**
  - Polymarket `public-search?q=KinGui` and `?q=Yawara` at 14:2xZ surface only the **closed**
    Oct-24 quarter-finals (`cs2-tdkg-meiano-2026-10-24`, `cs2-grmioe-yaw-2026-10-24`) — no open
    market for today's semifinal at read time (the owning session found the same at 13:44Z).
    If one opens before the 18:54Z lock, the existing scoped aliases let it bind automatically.
  - EGamersWorld: 1.8/1.8 header with no bookmaker-average sentence — a placeholder, **rejected**
    (recorded by the owning session; a identical-decimal placeholder is never a line).
- **Model rungs checked first-hand by this session (official Valve repository):**
  - `standings_global_2026_10_05.md` (the file `scripts/originate.py` reads; fetched via the
    GitHub API at 14:2xZ): **Yawara present** (rank 147, rating 845); **no `KinGui`/`Projeto do
    KinGui`/`Tropa do KinGui` row exists at all** (case-insensitive search: 0 hits; the roster
    names cited by the alias evidence have since dispersed — `CutzMeretz` now on MEIA NOITE #227,
    `t9rnay` on EHISTO BASE #224). So the **Valve-rating rung cannot price this fixture**
    (`model_estimate` returns `no Valve rating row found` for the missing side — by design, it
    never invents a rating).
  - Consequence, stated plainly: pre-match the ladder must resolve `1086697` from a money line
    (none open yet), the HLTV world-ranking rung (team unranked → documented synthetic-floor
    logic only), the bo3.gg results network rung, or it will publish the row on the
    **Unresolved picks & limitations** register with this exact trail. This is the coverage floor
    the brief demands stated, not hidden: a pick is generated only from a verified line or a
    labelled model — never from a placeholder or a crowd split.
- **Verdict:** unresolved-input fixture at observation time; re-checked every 4 h by the pipeline;
  all sources and the specific blocker are published in the dossier above.

### Model-only rows still inside the deployed snapshot (re-verified, no change forced)
- **1082792 HOTU vs The Huns (2026-10-31T09:00Z):** HLTV match
  [2399437](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026)
  binds identity/BO3 (prior sessions + this session's HLTV reads); Polymarket
  `cs2-hotu-the9-2026-10-31` exists with the scoped `The Huns Esports → The Huns` alias but was
  non-compliant at the 05:12Z publisher read; EGW shows a 1.8/1.8 placeholder (rejected).
  Current published pick is the labelled bo3.gg network estimate **98.2% HOTU** — direction
  model-supported, magnitude flagged as extreme/uncalibrated (already on Flagged for Review as
  0DB0-R03; this session re-states it rather than silently reusing it).
- **1082861 Rooster vs Abyssal, 1082793 5star vs 1WIN (2026-10-27 / 2026-10-31):** HLTV identity
  pages exist (DFRAG event pages; Moscow Cyber Games event 9344); EGW 1.8/1.8 placeholders
  rejected; Polymarket books for these were $0-stub / wide at the last reads (prior dossiers).
  Both keep their labelled Valve-model picks with the model limitation — re-checked, unchanged.
- **1082996 / 1079198 / 1085542:** already started (09:00/12:00/14:00Z today) — they left the
  active inventory during this session's observation window; they carried picks (model/market)
  while open. No retrospective probability is manufactured for them (per project policy).

## Irregularities this session flags (published on /review/, none blocks a merge)
1. `C0B-R01` — deployed snapshot 9 h 03 m old at observation (publisher blocked at the regression
   gate since 07:49Z; fix merged in PR #332 while this session observed; recovery run in progress).
2. `C0B-R02` — three live lobby fixtures absent from the deployed snapshot (1086696/1082697/1086697);
   two are wired by PR #332, 1086697 has no compliant money line and no Valve row (full trail above).
3. `C0B-R03` — Polymarket 1249433 rule text says "3:00 PM ET" (19:00Z wording) while its machine
   timestamps say 18:00Z matching Hotspawn; the join uses machine timestamps only.
4. `C0B-R04` — EGamersWorld returns HTTP 403 to this sandbox's fetcher and to GitHub Actions
   runners (platform limitation, not evidence of absence).
