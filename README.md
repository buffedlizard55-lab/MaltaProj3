# Spawn Scout — Hotspawn CS2 match intelligence

A mobile-first, source-linked GitHub Pages dashboard covering **every CS2 record returned by Hotspawn’s scheduled-fixture feed**, including academy and low-tier matches. Obvious picks and both teams’ calculated probabilities are shown only when supported by original external evidence; unresolved values remain blank.

**Live dashboard:** https://buffedlizard55-lab.github.io/MaltaProj3/

| View | What it contains |
| --- | --- |
| [Executive summary](https://buffedlizard55-lab.github.io/MaltaProj3/) | **Picks at a glance** (a phone-first index above the fold: every active fixture with **both** teams' win probability, the obvious pick, the **observed price** behind it — bid/ask in cents for exchanges, decimal odds for bookmakers, "median of *N* books" for a consensus and nothing at all for a research model — a Market line / Model / Researched badge and links to its evidence), coverage, complete-pick counts, the separate **Picks without a betting line** register (each model-only pick with the money sources that failed and why), unresolved-pick limitations, upcoming matches, the Day 1 contrarian review and a map of every page |
| [Complete match picks](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks) | The phone-first list: every non-archived fixture with both probabilities, one obvious pick, lock times and expandable evidence |
| [Leaderboard plan](https://buffedlizard55-lab.github.io/MaltaProj3/strategy/) | One plan pick per open fixture from our own external-line probabilities, the few underdogs worth an upset play (with their expected-point cost), a separate unresolved section, the Thunderpick tournament pick'em (team plus score), Hotspawn's verified scoring contract and Days 1–2 results cross-checked against Hotspawn's own API |
| [All match picks](https://buffedlizard55-lab.github.io/MaltaProj3/picks/) | Both probabilities, suggested team, method badge, searchable/filterable rows, source links and expandable evidence. Every non-archived fixture shows a pick or an explicit blank: featured exact-name estimates first, then clearly badged **Researched fallback** estimates from the audited research ladder |
| [Day 1 contrarian review](https://buffedlizard55-lab.github.io/MaltaProj3/#contrarian) | Source-linked 9z–Aurora upset review, Aurora rebuild context and a strictly bounded 9z–Falcons watch that never overrides the primary pick |
| [Upset review & edge](https://buffedlizard55-lab.github.io/MaltaProj3/edge/) | Dated first-party deep dive: day one at Thunderpick World Championship 2026 (9z 2-0 Aurora and the other three series, map by map), Aurora roster context (not a proven cause of the upset), official Valve standings for the current card, dated market observations and the seven rules applied before disagreeing with a market |
| [TWC Day 5 picks](https://buffedlizard55-lab.github.io/MaltaProj3/twc-picks/) | Final-day fixtures from the **same complete-picks snapshot**, plus separately labelled HLTV tournament fixtures and replayed external lines. Days 1–4 results, both probabilities, obvious defaults, bounded underdog screens and unresolved limitations. No invented finalists, deadlines, exact scores or narrative probability adjustments |
| [Coverage & original sources](https://buffedlizard55-lab.github.io/MaltaProj3/coverage/) | Inventory reconciliation, source health, complete past-start archive and JSON/CSV downloads |
| [Methodology](https://buffedlizard55-lab.github.io/MaltaProj3/methodology/) | Exact matching, formulas, thresholds, source policy and model limitations |
| [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/) | Missing inputs, failed source access, identity ambiguity, format/status conflicts and unresolved research trails |

The observation times and counts on the live site are authoritative for that published snapshot. For scale, the first fully replayed snapshot on **14 October 2026** contained **88 records: 28 future starts and 60 past-start records**, with **9 Polymarket estimates, 4 original bookmaker estimates, 8 Valve-model estimates and 7 unresolved future matches**. Past starts still labeled `scheduled` are retained as source anomalies, not invented results.

### Published snapshot file (session ca7e10e5)

Every page links and fetches **`/snapshot.json`**, a byte-identical build output of the same observation that is rendered on the page. The tracked `data/latest.json` in this repository is the CI replay fixture; it is deliberately never copied into the published branch root, because rewriting it would break the deterministic replay and the regression tests that assert against it. On 2026-10-23 a legacy root build served that fixture (2026-10-15) under a current page (2026-10-23) — 192.8 hours apart — so the downloadable file was split out and is now carried into the root by `scripts/root_publish.py`. The evidence for that read is in [`data/research/ca7e10e5/`](data/research/ca7e10e5/published-and-coverage.md).

## Source and probability rules

1. **Complete inventory first, and keep a valid official inventory usable.** The public scheduled-fixture API used by Hotspawn’s own client is the authoritative scheduled inventory. The rendered [Hotspawn lobby](https://play.hotspawn.com/lobby) and [CS2 lobby](https://play.hotspawn.com/cs2-pickems) hydration states are an independent cross-check; when either page is readable it must agree with the API exactly, and a readable page that disagrees still fails the refresh closed. When *no* rendered page can be read (observed HTTP 403 on both pages at 07:16Z on 17 October 2026, while the same API had answered 200 four hours earlier), the validated, duplicate-free API array is published with `inventory_crosscheck: "unavailable"`, a visible notice and a review flag instead of a reconciliation claim, so source-backed picks are not discarded over a secondary page. No pagination was present in the inspected client. A changed schema, duplicate IDs or an empty array still invalidates the refresh; it is never accepted as an empty or partial successful feed. New matches are rediscovered on every successful refresh.
2. **Never use Hotspawn “% picked.”** Community participation, offered points and crowd voting do not enter the calculations. Missing best-of formats, lineups and results are not inferred.
3. **Primary external market.** Discover candidates from [Polymarket’s CS2 directory](https://polymarket.com/esports/cs2) **and paginate the official CS2-tag event API to a terminal page** (bounded at 2,000 events; repeated pages/failures are explicitly flagged), verify an active, unique prematch **full-series match-winner** event with exact normalized team names and start time within 60 seconds, then obtain both original CLOB order books. Validate token/condition IDs, positive bid/ask size, noncrossed books, spread ≤0.12 and observation freshness. Normalize the two bid/ask midpoints. Directory percentages, map markets, props and outrights are not inputs. These are market-implied estimates, not verified true win probabilities.
4. **Research only missing primary matches.** Attempt [HLTV](https://www.hltv.org/matches) context first, then original esportsbook lines. The current split-anchor HLTV cards are parsed with sibling time/team context, and original HTML is saved and hash-checked for replay. Same-time records with one shared opponent but a different other team name are linked for review only—not silently treated as the same match. The public Thunderpick client uses a read-only **POST** `/api/matches` query with `{"gameIds":[6]}`; a failed GET does not establish that POST is unavailable. Require a unique exact fixture and prematch two-way series winner. Decimal odds are converted with `pᵢ = (1/oᵢ) / Σ(1/o)`. A single bookmaker is explicitly a single source, never described as consensus. Unsupported provider aliases stay unresolved.
5. **Explicit, higher-uncertainty model fallback.** Only after the primary, HLTV and bookmaker stages fail, use unique exact-name, five-player records from [Valve’s official regional standings repository](https://github.com/ValveSoftware/counter-strike_regional_standings). Name-matching rows that are not complete five-player records are excluded *before* the uniqueness test (so one complete row plus an incomplete remnant resolves), while a name with several complete five-player rows is resolved only by a fresh, fixture-bound HLTV lineup that identifies exactly one of them: either all five players match, or a unique four-of-five core matches with a documented one-player change (published as a roster-change identity join, not a current-lineup rating). Otherwise it stays blank. Reproduce the published Glicko expectation with fixed RD 75; use the latest applicable snapshot no older than 35 days. Raw official markdown and Git blob SHA are verified. This is an **uncalibrated research estimate**, not betting odds, and does not confirm today’s roster, stand-ins or veto. It never overrides a primary pick.
6. **Leave unsupported values blank.** Ambiguous names, stale/wide/one-sided markets, missing ratings or unavailable sources produce no fabricated probability or pick. Each such match remains in the list, unresolved section and review flags. Calculated fair decimal lines are illustrative reciprocals, not executable quotes.
7. **More independent money sources for the gaps (session c07e1b40).** For fixtures the featured methods leave blank, `scripts/originate.py` also reads [Kalshi](https://docs.kalshi.com/api-reference/market/get-markets) CS2 match-winner books (a CFTC-regulated exchange with an officially documented public API; scheduled start parsed from the contract rules and cross-checked with the event ticker; both yes books must be two-sided and no wider than 0.15 in this fallback ladder, with anything above 0.12 published as **thin**) and [Bovada](https://www.bovada.lv/sports/esports/counter-strike-2)'s public prematch series moneylines (margin removed proportionally). The featured exact-name collector keeps its strict 0.12 ceiling and is never widened by the fallback. The same exact-name/registry and 60-second start rules apply, in-play observations are excluded, and the originated line is the **median across independent providers** (Polymarket, Kalshi, Thunderpick, Bovada — one vote each). Rejected wide books are shown on the unresolved cards for guidance only. Every quote is replayed from its saved original response before the site is built.
8. **Scoped identity aliases, never fuzzy joins.** [`data/origination/aliases.json`](data/origination/aliases.json) is the reviewed registry that lets a provider display name ("Team Falcons", "BetBoom Team", "Aurora Gaming", "WBT") join a Hotspawn name. Every alias declares the exact competitions it applies to (`applies_to`), carries official https evidence, honours `must_not_match` exclusions, and is enforced in `scripts/originate.py` for market, bookmaker and model joins alike. An alias outside its declared competition never matches.
9. **Dated research is labeled as dated research.** The [upset review page](https://buffedlizard55-lab.github.io/MaltaProj3/edge/) (`data/edge-review.json`, built by `scripts/build_edge.py`) publishes day-one results, roster changes, official Valve standings and dated provider price observations for context. Every fact carries its own official source link and observation time. It is not refreshed by the four-hour pipeline, it never overwrites an automated estimate, and Hotspawn community percentages are never read — so "contrarian" here means disagreeing with the external market or ranking consensus only where verified evidence supports it, never crowd-fading.

HLTV directory research supports its observed split time/team links, joined only by the exact match URL. Repeated pinned cards are deduplicated; conflicting observations are rejected. Original HTML is retained as evidence. This confirms identities, not odds. For remaining gaps, each match now records the actual GG.BET, Pinnacle and Rivalry access-check limitations, not merely a global source-health warning. Unknown-start fixtures appear in the executive summary’s unresolved section, separate from the future-match count.

Every row links an official Hotspawn source. Every estimate links the original market, bookmaker or Valve record. [Full public snapshot](https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json), [request manifest](https://buffedlizard55-lab.github.io/MaltaProj3/data/sources.json), [contrarian review evidence](https://buffedlizard55-lab.github.io/MaltaProj3/data/contrarian.json), saved first-party JSON evidence, and [CSV](https://buffedlizard55-lab.github.io/MaltaProj3/data/picks.csv) allow manual review and calculation replay. POST request payloads, observation times and response hashes are recorded without credentials.

## 15 October day-one review: the HLTV-reported 9z–Aurora upset

The executive summary teases and [`/edge/`](https://buffedlizard55-lab.github.io/MaltaProj3/edge/) publishes the full dated review. The dated source reporting below was read during the 2026-10-14 → 2026-10-15T10:26Z research window and is stored in [`data/edge-review.json`](data/edge-review.json) with its own observation time. HLTV reports are attributed journalism, not primary organizer/club confirmation; the guide consequences are qualitative interpretations, not demonstrated causes or numerical probability inputs.

| Day-one series (14 Oct 2026, bo3) | Maps | Official source |
| --- | --- | --- |
| **9z 2-0 Aurora** (the upset: HLTV #17 vs #6; luchov 38-20, 97.4 ADR, 1.61 rating; +62 VRS points to 1571) | Inferno 13-11 · Nuke 13-1 | [HLTV series report](https://www.hltv.org/news/45718/9z-beat-aurora-2-0-to-kick-off-twc-2026) · [match page](https://www.hltv.org/matches/2399384/9z-vs-aurora-thunderpick-world-championship-2026) |
| Falcons 2-0 Ninjas in Pyjamas (needed OT on Ancient after leading 8-4) | Ancient 16-13 · Dust2 13-6 | [HLTV day-one report](https://www.hltv.org/news/45723/furia-fend-off-betboom-to-end-day-one-of-twc) · [results](https://www.hltv.org/results?event=8932) |
| Legacy 2-0 PARIVISION (blew 8-2 and 12-5 leads; OT on Mirage; arT's return) | Dust2 13-11 · Mirage 16-14 | [HLTV day-one report](https://www.hltv.org/news/45723/furia-fend-off-betboom-to-end-day-one-of-twc) |
| FURIA 2-0 BETBOOM (BETBOOM let 8-4 leads slip twice; KSCERATO 1.72) | Ancient 13-10 · Mirage 13-9 | [HLTV day-one report](https://www.hltv.org/news/45723/furia-fend-off-betboom-to-end-day-one-of-twc) |

**Roster context—not a demonstrated cause of the upset.** [HLTV's 8 July rebuild report](https://www.hltv.org/news/45082/official-aurora-complete-rebuild-with-kyxsan) describes Jimpphat, kyxsan and coach ash replacing MAJ3R, soulfly and Fabre. It corroborates a summer rebuild, not a new October change, measured fatigue or proof that the rebuild caused this result. The HLTV-published lineup (XANTARES, woxic, Jimpphat, kyxsan, Wicadia; coach ash), HLTV #6 and VRS #5 were dated observations from the [HLTV team page](https://www.hltv.org/team/11861/aurora) during that research window, not confirmation of today's lineup. The review's seven qualitative guardrails remain linked to their sources; no numerical rebuild/rest/veto adjustment is inferred.

Falcons' current five-player lineup was **not** verified inside the window; the page publishes Valve's dated official snapshot instead (karrigan, kyousuke, m0NESY, NiKo, TeSeS on 2026-10-05) and leaves the "current lineup" field blank. That gap weakens the 9z contrarian case and is published rather than smoothed over.

## Day 2 results → Day 3 guide (16 October deciders)

Read from [HLTV's official event results](https://www.hltv.org/results?event=8932) and match pages on 2026-10-15 (22:26–22:35Z window; stored in [`data/day3-guide.json`](data/day3-guide.json), rendered by `scripts/build_day3.py` at [`/edge/#day-three-guide`](https://buffedlizard55-lab.github.io/MaltaProj3/edge/#day-three-guide)):

| Day-two series (15 Oct 2026, bo3) | Maps | Dated guide interpretation—not a probability input |
| --- | --- | --- |
| Aurora 2-0 Ninjas in Pyjamas (Group A elimination; NiP out) | Cache 13-9 · Dust2 13-7 | Different sweep outcomes are form context; no numerical rebuild discount is inferred |
| 9z 1-2 Falcons (Group A winners'; Falcons to semi-final) | Nuke 9-13 · Mirage 13-8 · Dust2 9-13 | 9z took a map off the group winner; one series does not establish that the earlier upset was non-random |
| PARIVISION 1-2 BETBOOM (Group B elimination; PARIVISION out) | Ancient 13-10 · Anubis 4-13 · Mirage 7-13 | BetBoom survive after three maps; no unsupported relative-opponent-strength adjustment is applied |
| Legacy 1-2 FURIA (Group B winners'; FURIA to semi-final) | Cache 13-10 · Inferno 5-13 · Mirage 8-13 | Legacy took a map off FURIA; this alone does not calibrate a comparative form advantage |

**Historical 15 October advisory—not current picks.** Day 3 (16 Oct, both bo3 deciders): **Aurora vs 9z** (14:00 UTC per Polymarket's Gamma record; provider prices Aurora 0.69 / 9z 0.31 at 22:23Z, thin) and **Legacy vs BETBOOM** (17:00 UTC; market created 22:25Z with zero trades, so **no probability is published**). Guidance: primary Aurora with **9z as the single designated contrarian flip** for leaderboard climbers (head-to-head 2-0 two days ago + map off Falcons, against Aurora's Day 2 reset and ~2:1 market price); Legacy is a labeled low-confidence *form lean only* in the unpriced decider. Rest is symmetric — all four teams played Day 2 — and no new roster change was verified for Day 3. The current [Day 4 guide](https://buffedlizard55-lab.github.io/MaltaProj3/twc-picks/#day-four-picks) and complete-picks snapshot are authoritative; this older advisory is retained as dated history, not reissued after the results.

## 21 October session arena-dbaf7692: a pick or an explicit limitation for every match

- **One ranked team is now enough.** The HLTV world-ranking rung used to refuse any
  fixture where one side had no published row — the normal CCT/DFRAG low-tier case. It
  now gives the unranked side HLTV's floor of 0.0 points, labels the estimate
  **HLTV world ranking · unranked floor**, and publishes a low-confidence limitation.
  Both sides unranked still stays blank, ambiguous names still fail closed, and the rung
  never overrides a money or Valve estimate.
- **The executive summary lists every pick-less fixture**, including an even estimate
  that has probabilities but no side ("Even estimate · no side"). A blank never shows a
  probability and never gets a default 50/50. Each card links the sources actually tried
  and the full research trail.
- **Research-first evidence for the current gaps** is in
  [`data/research/dbaf7692/coverage-dossier.json`](data/research/dbaf7692/coverage-dossier.json):
  HLTV first, then Polymarket, Kalshi, Thunderpick, Bovada, Pinnacle and EGamersWorld,
  with the exact blocker per fixture. HLTV match pages currently answer HTTP 403 to
  GitHub runners, so HLTV is never used as a live odds source and no HLTV-sourced price
  is claimed. HLTV's "Pick a winner" fan vote and Hotspawn's "% picked" remain excluded.
- **Pending public snapshot fix:** the repository's Pages site is still in the platform's
  legacy build mode (the configuration API returns HTTP 403 to the workflow token), so a
  push-triggered legacy build can briefly republish the checked-in 15 October pages after
  the current artifact deploys. The workflow now re-verifies the public snapshot 75
  seconds later and republishes the verified artifact if that happened. The setting
  itself still needs a repository owner with Pages admin.

## 22 October session arena-fbdc97d6: provenance you can check, and both probabilities on a phone

- **The executive summary now names the real source behind every researched pick.** The
  "Unresolved picks & limitations" copy used to print one hard-coded sentence saying every
  featured blank had been priced by "a verified Thunderpick paired-price book". Checked against the
  published rows it was wrong: across the 21–22 October snapshots the researched rows were priced by
  the Kalshi exchange, the Valve official ratings, the bo3.gg results models and the HLTV world
  ranking, and never by one bookmaker. The sentence is now generated per row by
  `scripts/build.py::researched_method` and shows the source with a link for each fixture, so the
  text cannot drift from the data again (`tests/test_build.py::ResearchProvenanceTests`).
- **A bo3.gg network row is no longer labelled "Valve official ratings".** Four fixtures in the
  22 October 01:20Z snapshot were priced by the bo3.gg network fit while their label named Valve.
  `scripts/originate.py` now labels each research-model row by the rung that produced it
  (`model_label`, `network_limitation`) and the network limitation is the one that is published
  (`tests/test_fbdc97d6_labels.py`).
- **Both published probabilities are visible in the phone index.** Each row of *Picks at a glance*
  shows the pick with its percentage and the opponent's published percentage beside it, without
  recalculating anything (`glance()`, `assets/scout.css`).
- **Current findings come first on Flagged for Review.** The live findings register now opens the
  page; the dated registers from earlier sessions are kept verbatim inside one collapsed block
  labelled "not current findings".
- **A dated line-source sweep is published under the unresolved register.** 22 esportsbook,
  exchange and aggregator surfaces were probed read-only from the GitHub runner on
  `2026-10-22T01:29Z`: 7 answered HTTP 200, 15 refused, were deleted or timed out. HLTV, EGamersWorld,
  GG.BET, BetBoom, 1xBet and Marathonbet block the automated runner (an HLTV match page and the
  ranking page were read by hand on the same day, so HLTV remains a verification source, never an
  odds feed). Oddspedia's CS2 page answers HTTP 410. bo3.gg does publish a named Thunderpick block
  with both coefficients, but on that sweep it existed only for the five fixtures that already had a
  first-party line, so it closes no blank and is **not** wired into the pricing ladder — it is
  documented as an independent cross-check.
- **Coverage in the 2026-10-22T02:08Z snapshot:** 97 inventory records, 62 past starts, **35 active
  fixtures, 35 with probabilities, 34 with a directional pick, 0 without a line, 1 exact 50/50
  estimate published with no side** (ex-Zero Tenacity vs ex-RUSTEC, identical official points).
  Row-source audit on that live snapshot: 334 rows, 326 with an official link, 8 site-map rows,
  **0 without a source**.

## 22 October session arena-f60683a4: current picks first on a phone, and sourced limitations for the model-only card

- **The phone jump bar now starts with the picks on this page.** `start_here()` used to list a
  18 October Day-5 archive as a current destination, which on a 390 px screen pushed *Picks at a
  glance* below five navigation cards. The first jump is now `#picks-at-a-glance`; the complete
  list, leaderboard plan, unresolved trails and the no-betting-line register follow; the Day-5
  archive stays on the site map. Phone CSS puts that picks jump full-width and the other four
  destinations in a two-column grid (`assets/scout.css`, `tests/test_f60683a4.py`).
- **Every active Hotspawn CS2 fixture in the 2026-10-22T05:37Z snapshot already had a sourced
  pick (33/33, 0 blank).** Eighteen of those are research models, not betting lines. HLTV match
  pages still do not publish a two-sided prematch book this project can replay (the BAKS vs
  Azuolas betting module was casino advertising plus a fan vote, which stays excluded). Dated
  research: [`data/research/f60683a4/low-tier-line-research.json`](data/research/f60683a4/low-tier-line-research.json).
- **Two featured-blank fixtures had a Polymarket series listing at 07:32Z that the 05:37Z
  snapshot did not use as a money line** (Nemesis vs WW, Gamma event 1232386, start 11:30 UTC
  matching Hotspawn; Butterfly vs Lavked, event 1232201, previously rejected as a wide/crossed
  book). Directory cents are recorded as directory displays, not originated probabilities, and
  are flagged on [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/)
  so the next four-hour live collect can retry the books. No snapshot row was hand-edited.

## 23 October session arena-46ade650: a new exchange line source for the low-tier matches, and a dated sweep for every fixture without a betting line

- **The four-hour publisher stalled for nineteen hours on two date-pinned tests, and is green again.**
  Scheduled runs [39845991470](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39845991470),
  [39861117407](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39861117407),
  [39871371551](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39871371551) and
  [39881298806](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39881298806) all failed at the
  regression-test gate before they could collect, build or deploy: the bo3.gg relay test's fixture had already
  started, and the root-publish check-mode test was pinned to a snapshot that had crossed the twelve-hour age
  limit. Session `308fcaad` fixed both on `main` while this session was diagnosing them; this session dropped
  its duplicate edit and kept `main`'s versions, which are the ones published.
- **A new independent money source: the Smarkets exchange.** The brief asks for a line rather than a rating
  model wherever a real betting market exists, including academy and tier-3 matches that Polymarket, Kalshi and
  the big books skip. [Smarkets](https://smarkets.com/sport/esports/cs-go) publishes a public, documented
  read-only API ([docs.smarkets.com](https://docs.smarkets.com/)) that lists CS2 as `csgo_match`, including CCT
  Europe, United21, Circuit X and DFRAG fixtures. `scripts/smarkets_lines.py` binds both team names plus a start
  inside the same 60-second window, saves the original events/markets/contracts/quotes responses, and converts
  Smarkets' 1/10000 quotes into 0–1 probabilities. The rung uses the existing ladder rules unchanged: two-sided
  books only, no wider than 15 cents, anything wider than 12 cents flagged **thin**, one independent vote in the
  median, and every published quote replays from its saved capture in `scripts/build_origination.py`. An
  unreachable exchange records a reason and prices nothing. First runner capture (2026-10-23T05:17Z): **11**
  fixtures bound, **8** with a two-sided quote, e.g. ex-Zero Tenacity–ex-RUSTEC (0.4545/0.578 vs 0.4202/0.5435)
  and Inner Circle Academy–Spirit Academy; the capture was re-read independently from the exchange's own API and
  matched exactly.
- **A fresh, dated sweep for every fixture without a line.** The runner probe (2026-10-23T05:18Z, freshly
  collected snapshot 05:17:16Z) re-researched the **9** active fixtures that carried only a research-model pick,
  in brief order: HLTV first, then esportsbooks and aggregators, adding Rivalry, Betano, Betsson, Unibet,
  Oddspedia, 22bet, Bet365 and the HLTV search endpoint to the surfaces earlier sessions tried. Recorded
  answers: HLTV 403 (Cloudflare), Bet365 403, EGamersWorld 403, Oddspedia 410, Betsson 202, Unibet 503, Rivalry
  and 22bet served challenge pages, and the Pinnacle guest board listed none of the nine. No two-sided price was
  readable on any of them, so those picks remain labelled research estimates with their limitations published.
  Evidence: [`data/research/46ade650/line-source-research.json`](data/research/46ade650/line-source-research.json),
  `.md`, and the exchange capture beside them.

## Automatic operation: one publisher, every four hours

[`.github/workflows/pages.yml`](.github/workflows/pages.yml) runs on pushes to `main`, manual dispatch and at **00:17, 04:17, 08:17, 12:17, 16:17 and 20:17 UTC**, plus catch-up slots at **02:47, 06:47, 10:47, 14:47, 18:47 and 22:47 UTC**. GitHub may delay or drop scheduled jobs under load (on 15 Oct 2026 only 04:39, 13:26 and 19:53 UTC were delivered — an 8.8-hour gap), so the catch-up slots keep a single dropped run from pushing the data past the 8-hour bound. This is not a real-time feed.

It restores the last verified snapshot from Actions cache, runs regression tests, discovers the full inventory, collects supported external evidence, **replays every row and calculation**, builds the dashboard and both clearly labeled historical archives, checks internal links/anchors/assets, and deploys one `site/` Pages artifact. A post-deploy check verifies the public HTML, full JSON, category pages, compatible old URLs and both archives. Production uses read-only source requests, not an account, API trading key or user action. Workflow permissions are `contents: read`, `actions: read`, `pages: write` and `id-token: write`. The job first waits for any platform legacy Pages build for the same commit, then attempts to configure Actions mode. If GitHub restricts that setting change, it records the actual mode and error on the review page and still publishes the verified artifact **after** the legacy publisher has finished. A running legacy publisher or unverifiable ordering blocks deployment, rather than risking a later stale overwrite.

- **Source failures do not manufacture fresh data.** Collection is staged and replayed before replacing last-good files. If inventory reconciliation fails after a partial download, old source evidence and analysis times remain intact; attempted responses get separate audit filenames. Retained coverage is marked unverified and clearly warned. Only a complete, replayed inventory is saved as the next cache fallback.
- **Unavailable picks do not block publication.** They are visibly unresolved. A broken build, inconsistent evidence or failed deployment does block it and must be fixed.
- **A failed fresh replay no longer freezes the site.** Scheduled runs on 2026-10-15 (13:26Z and 19:53Z) failed at the build/replay step and left the previous deployment in place with no new publication. The publisher now preserves the exact last-good snapshot pair (featured + originated, with its evidence) before collecting; if the fresh snapshot fails the full replay, it republishes that verified pair unchanged — original timestamps, stale warnings and all — and never caches the fallback as verified. No probability is repaired, relabeled or invented in the process.
- **Staleness is explicit.** Inventory older than eight hours, failed inventory refreshes, expired quotes and past starts are visibly demoted. An open tab checks for newer snapshots without silently replacing the user’s current view. Malta/UTC/local timezone choices and actual observation dates are explicit.
- **No competing refresh writer.** The former six-hour `refresh.yml` is retired to a manual explanatory job; it no longer writes older datasets to `main` or deploys another artifact. Production snapshots are published with their evidence on Pages and cached, rather than growing Git history on each four-hour run.

## Verified code release — 17 October 2026

[PR #71](https://github.com/buffedlizard55-lab/MaltaProj3/pull/71) merged at 02:02:09 UTC; [actual canonical production 38993321846](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38993321846) completed successfully at 02:07:33 UTC, including fresh source replay, deployment and public HTML/JSON/probability parity. Inventory observed 02:05:45 UTC: **96 source records  / 34 upcoming / 62 archived**. The complete list had **25 supported estimates (15 external-money lines, 10 explicitly uncalibrated rating models), 24 directional picks, 1 no-edge row and 9 unresolved fixtures**. Both Day 4 semifinal fixtures were covered. The published row audit passed **517 rows  / 509 official-source-linked + 8 navigation / 0 violations**. These are dated observations, not a promise that later refreshes retain those counts or prices.

The release preserves the canonical source serializer and adds actual-Client round-trip tests, endpoint/method/original-blob provenance guards, conservative source expiry and selected-page clock/immutable-evidence checks. Every session's source-linked findings now load without a hardcoded session allowlist. [Exact QA and release evidence](data/research/5b642a83/final-release-verification.json) distinguishes local 555/72/106 results from actual live coverage. Sleep/travel/roster causal adjustments stay unverified; unknown prices stay blank and an observed 50/50 line does not force a pick.

## Local development and verification

Python 3.12+ and Node 22+ are used in CI.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci

.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m scripts.build
npm test

# Optional live collection where the public source hosts are reachable:
.venv/bin/python -m scripts.collect
.venv/bin/python -m scripts.build

# Preview from a project root, without hardcoded browser-facing localhost APIs:
.venv/bin/python -m http.server 8000 --bind 0.0.0.0 --directory site
```

`site/`, virtual environments, dependency trees, caches, browser reports and screenshots are ignored. Do not run the generator with the repository root as its output; keep other sessions’ source files unchanged. The checked-in current HTML is a fallback snapshot; the published artifact is rebuilt from validated data on every production run.

**Verification:** 555 Python regression tests cover source contracts, exact identity, scoped alias joins, time/freshness, rejected markets, no-vig calculations, rating provenance, researched-fallback display rules, the dated edge-review contract, the source-linked contrarian guardrails, the complete-picks/alternative-watch briefing and atomic source-failure handling, publication-mode restrictions, publisher ordering, retained-evidence replay, the group-stage/semifinal review contract and the blank-pick coverage dossier. 72 Playwright checks cover all seven current pages at 320/390/768/1440px, one-tap phone navigation, search/filter/sort, every official row link, expandable evidence, timezone changes, stale behavior, no-JS content, the Day 1–5 review sections and axe WCAG A/AA checks at phone and desktop widths. A separate browser audit contributes 106 pick-presentation assertions for Python/JavaScript parity, expiry, locking, clock rollback, no-JS behavior, four widths and axe A/AA. Automated accessibility checks are not a claim of complete WCAG certification. The CI workflow independently installs the standard Playwright Chromium. In restricted local environments the test config uses npm-packaged Chromium and its bundled NSS libraries; it does not disable web security.

## 16 October: leaderboard plan, tournament pick'em and the row-source audit

**Leaderboard plan** ([`strategy/`](https://buffedlizard55-lab.github.io/MaltaProj3/strategy/), built by [`scripts/build_strategy.py`](scripts/build_strategy.py), rules in [`data/strategy-rules.json`](data/strategy-rules.json)). It decides only *which side to submit*; every probability still comes from the external-line pipeline and Hotspawn "% picked" is never a probability. The default is the most likely winner. An **upset play** (the underdog) is recommended only when all of these hold: the line is money-backed (not the Valve model) and under 8 hours old; the underdog is at least 30% in our own probability; the match is worth 3+ Hotspawn points; the crowd is not already on the underdog (10+ pickers on record and at least half on it, because that cannot move you past anyone); and at most 2 plays per UTC day, ranked by points × underdog probability × the share of the field you would pass. Each upset card shows what it costs in expected points. Hotspawn awards points for correct picks only, so that cost is `points × (favorite − underdog probability)`; the upside is variance. Fixtures with no probability stay in a separate **Unresolved picks & limitations** section with the research trail, never a default 50/50.

**Thunderpick World Championship tournament pick'em.** Hotspawn runs a second contest for the event: 7 points for the correct team **plus 5 for the correct series score**, 15 fixtures over 8 teams, no stage multiplier configured, prizes of $1500 / $750 / $375 / $125 × 7, a daily "Crystal Ball" kills question and player props ([tournament page](https://play.hotspawn.com/tournaments/thunderpick-world-championships)). The plan page adds a score slip to researched best-of-three fixtures. That slip is **our own model**, not a source fact: it solves the series price for one per-map chance (assumed equal on every map) and is labelled uncalibrated. Crystal Ball scoring and player props are published as unverified, not guessed.

**Reverse-engineered contract.** [`data/research/1112299f/`](data/research/1112299f/) holds dated, source-linked readings: [`hotspawn-contract.json`](data/research/1112299f/hotspawn-contract.json) (scoring, lock lead time 5 min on the rules page against 360 s in the API, the exact weekly window from the weekly-prizes API, the endpoints the pages hydrate), [`hotspawn-tournament.json`](data/research/1112299f/hotspawn-tournament.json), [`twc-results.json`](data/research/1112299f/twc-results.json) (HLTV results cross-checked against Hotspawn's own API: 8 of 8 series agree) and [`lobby-probe.json`](data/research/1112299f/lobby-probe.json), the runner-side probe output. The probe found that **Hotspawn's server-rendered lobby pages are CDN-cached** (70–90 minutes old, `X-Cache: HIT`) while the fixture API is live, which is why the old strict "lobby = CS2 lobby = API" check could freeze the inventory for hours. The collector now requests fresh renders (`?cb=<epoch>`, `X-Cache: MISS`), retries once, and names the differing fixture IDs and cache state when it still disagrees. These research files are **not** refreshed by the four-hour pipeline.

**Model estimates yield to verified money lines.** The featured exact-name collector can miss a market listed under a display name (Polymarket's "Aurora Gaming" for Aurora) and then fall to the uncalibrated Valve model. `scripts/originate.py::resolve_match` now runs the alias-aware money research for those fixtures too and replaces the model with a verified Polymarket / Kalshi / Thunderpick / Bovada line (or their per-provider consensus) when one passes every existing spread, freshness, start-time and alias-scope check; otherwise the featured model is kept exactly as before. The row is marked `upgraded_from_featured_model`, replayed from its saved first-party responses by the validator, and labelled on the picks and plan pages. This is the only permitted change to a featured estimate. Featured money-backed estimates are never touched.

**Authenticated GitHub API calls.** Both collectors read Valve's public standings through `api.github.com`. Unauthenticated calls from a GitHub-hosted runner were measured answering HTTP 403 with `x-ratelimit-remaining: 0` of 60 (GitHub documents 60 per hour per originating IP address, shared with other jobs), while the workflow's own `GITHUB_TOKEN` got HTTP 200 with a limit of 5000. An exhausted quota silently removed every Valve model estimate and the saved ratings file, and an unconditional link then failed the build. `scripts/github_auth.py` now attaches the token to `https://api.github.com` requests only (never another host, never written to a manifest or evidence file), the collect and originate steps of `pages.yml` and `origination.yml` pass it, and the edge page links the saved ratings only when the file exists.

**Row-source audit** ([`scripts/audit_rows.py`](scripts/audit_rows.py)). Every table row and pick card in the built site must carry a link to an allow-listed official source or an explicit "unverified" marker; the only exemption is the site-map table, keyed to its caption. The build writes `data/row-source-audit.json` and warns on violations without blocking a refresh; pull-request checks run it with `--strict`. Its first run on the merged site found eight Day-3 standings rows with no source; they now link the HLTV bracket.

```sh
python -m scripts.build_strategy --source data --output site   # also runs inside scripts.build
python -m scripts.audit_rows --site site --strict
python -m scripts.lobby_probe --rounds 3 --out /tmp/probe.json  # read-only, public GETs only
```

At the time of writing (2026-10-17) the integrated tree passes 618 Python tests, 85 Playwright checks and 106 independent pick-safety browser assertions (the leaderboard plan has its own spec at 320/390/768/1440 px with axe WCAG A/AA at phone and desktop widths, as do the Day-4/Day-5 review sections). `scripts.build` replays 80 source rows, validates 608 internal links/assets/anchors, and the strict row audit accepts 396 rows (388 official-source rows plus 8 site-map navigation rows, 0 violations). These counts move with every session — re-measure with `.venv/bin/python -m unittest discover -s tests`, `npm test`, `node tests/pick-safety-browser.mjs` and a `scripts.build` run rather than trusting this sentence. **Non-blocking platform restriction:** GitHub Pages remains in legacy mode because the workflow token gets HTTP 403 when attempting the repository setting change. The sole publisher detects that mode, waits for the platform build, and publishes the verified artifact afterward; no user input is required.

## Preserved concurrent-session work

The original root and independent `docs/` dashboards used different observation times, matching rules and model weights. They are **not silently mixed into the current feed** or relabeled as freshly verified.

- [Original root-session archive](https://buffedlizard55-lab.github.io/MaltaProj3/archive/root-session/): original HTML, JS/CSS and datasets preserved in [`archive/root-session/`](archive/root-session/). The other session’s original `assets/app.js`, `assets/styles.css`, `data/matches.json`, `data/review.json` and maintenance scripts remain unchanged for provenance.
- [Independent docs-session archive](https://buffedlizard55-lab.github.io/MaltaProj3/docs/): source pages remain unchanged in [`docs/`](docs/), with `data/picks-model.json` and `scripts/build_site.py` preserved. It originally used 14 picks/14 unresolved and a 70/30 external-market/HLTV-points blend; those historical figures are not the current model.
- The production build adds unmistakable archive banners and current-feed links to the **artifact copies**, not the other sessions’ source HTML. The old `picks.html`, `methodology.html` and `flagged.html` URLs lead to current categorized pages.
- Claims, handoffs, source irregularities, checks, PR/merge/deployment records and publication-gap resolution are recorded in [`COORDINATION.md`](COORDINATION.md).

Independent informational analysis only. No bets or Hotspawn picks are placed. Estimates are not guarantees; 18+ where applicable.


## 15 October coverage audit

- Corrected a verified HLTV parsing defect: team names and time are in sibling anchors. Successful research now exposes exact fixture identity and HLTV’s independently published format without filling Hotspawn’s unknown format field.
- Expanded primary discovery beyond the displayed directory with official Gamma pagination. Original moneyline and two-book validation policies remain unchanged.
- Corrected bookmaker outcome alignment to use each price’s actual team name, not its container key; past-start and missing-ID records are rejected.
- Complete analysis replay now checks **all displayed quote values, labels, limitations and inputs**, not only final percentages. Tampering tests cover changed bid displays and misleading model labels.
- Added phone briefing shortcuts, calculated fair decimal lines beside both percentages, an unresolved section on the full picks page, explicit market rejection reasons and review-only differing-name records. Research links open the actual evidence panel even with a conflicting bookmarked filter; clearing filters clears URL state too. Static/no-JS builds demote already stale or locked choices.
- Live first-party research confirmed Stake/GG.BET access restrictions and Pinnacle/Rivalry generic redirects; none are treated as actual prices. These outcomes are rechecked by the fallback collector and published in source health/review. Historical source-audit evidence: `data/research/report.json`; the current request manifest and source timestamps take precedence.

Latest counts change with collection. The site’s executive summary distinguishes inventory coverage, market estimates, higher-uncertainty models and unresolved rows. There is no promise of invented picks for unsupported fixtures, no default 50/50 and no requirement for user input.


## 16 October integration: one TWC feed, exact lineup proof

- `/twc-picks/` is generated with every deployment, not copied from a manually authored page. Its JSON is
  `data/twc-day3-picks.json` (schema 2), a **view** of `data/origination.json`, never a second pricing source.
  The summary’s Day-3 shortcut and sidebar both lead to it. Stale or locked values remain snapshot estimates.
- Fixed live alias-aware research skipping fixtures already given a featured **model** estimate. Supported
  market/bookmaker lines can replace only that lowest-rung model, never a featured money line. The summary,
  searchable picks, TWC view, complete list and CSV all use the same selected estimate; old featured values
  remain visible as an audit reference, not as a competing current recommendation.
- Aliased Polymarket collection now uses the same unique full-series, prematch, accepting-orders contract
  as the featured method and requires positive-size levels. New summary observations are replayed against
  the full saved original event and both CLOB books (including token, condition, timestamp, spread and size),
  not merely against another derived bid/ask summary.
- For unresolved same-name Valve rosters, the complete-picks ladder can use freshly fetched original HLTV
  match markup: both teams and epoch start must match the fixture; all five unique player names must match
  **exactly one** complete Valve row. Four-of-five overlaps, duplicate exact lineups, stale pages or failed
  access do not resolve a pick. This selects an identity, not a form premium or a calibrated win probability.
- Dated research: [`coverage-review.json`](data/research/6426358d/coverage-review.json) covers all nine gaps
  at 07:23 UTC and the 07:29 UTC follow-up (42 active / 35 estimates / 7 unresolved). Original compressed
  HLTV responses and hashes are retained in `data/research/6426358d/observed-0723/`. These are dated audit
  counts; the published dashboard timestamps and current counts remain authoritative.
- Withdrawn commentary is explicitly recorded on Flagged for Review: a historical in-play price was called
  prematch, calendar dates were treated as equal rest, and the summer roster change was presented as a
  causal probability discount. No such adjustments enter the refreshed probabilities. Historical market
  observations retain their own timestamps. HLTV reports are attributed to HLTV, not relabeled organizer proof.


Concurrent-session handoffs are preserved: open-tab/closed-pick guards and independent safety tests
from P are integrated. M’s historical ≥3/5-core dossier remains downloadable for provenance, but its
partial-overlap scenarios are **not** a second current probability feed. The review page flags this policy
conflict (including a withdrawn 403-row claim; the original Git blob contains 380 rows). Its dated Valve
inputs are pinned and replayed from the original response, independently of later live-cache refreshes.

## Day 4 TWC handoff (17 October 2026)

The mobile executive summary links directly to **[Day 4 picks and review](https://buffedlizard55-lab.github.io/MaltaProj3/twc-picks/#day-four-picks)**,
**[every CS2 pick](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks)** and
**[unresolved picks and limitations](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#unresolved)**.
Day-4 probabilities are exact copies of the canonical complete-picks feed, not a separate editorial model.
The Day-3 JSON's schema-2 fields remain compatible; `day4` is additive, and `data/twc-day4-picks.json`
provides the dedicated view. Historical Day-3 prices are expandable and clearly separate from current choices.

The sole scheduled Pages publisher now also runs `python -m scripts.twc_research`. It reads normal public
HLTV event/match pages and Hotspawn tournament metadata, retains compressed originals and SHA-256 hashes,
and replays results from those originals. An unfinished series has no inferred winner. A newly listed HLTV
fixture absent from the reconciled Hotspawn weekly inventory has no invented probability, deadline or pick.
Tournament listings and weekly picks are explicitly different scopes; placeholder opponents are not confirmed teams.
A tournament fixture count is not proof of complete playable coverage.

Live research is distinct from dated `data/research/8a6a5a84/` evidence (19:35Z on 16 October).
That observation confirmed Aurora 2–0 9z, but **did not** confirm a BETBOOM–Legacy series winner.
It found 21 active weekly fixtures, 13 supported estimates and eight unresolved. These are dated diagnostics,
not permanent live counts. Missing lines, ambiguous aliases, absent Valve ratings and partial roster proofs
remain blank. HLTV is an independent reporter, not primary organizer verification. Roster integration,
health, actual rest, ownership and leaderboard-gain probabilities are not invented or added to win estimates.

Day-4 cards reuse the existing shared safety guards: default and optional-underdog labels retire together
when inventory or price expires, a lock/start passes, or eligibility is unverified, including tab focus/resume.
Source percentages remain for audit. No-JavaScript labels describe build time only; a device clock is not a trusted
server clock. The four-hour refresh is a GitHub Actions schedule target, not a guaranteed delivery SLA.

Local verification commands (Python 3.11+):

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m scripts.build
.venv/bin/python -m scripts.audit_rows --site site --strict
PYTHON=.venv/bin/python npm test
```

## 17 October session arena-7831412c: restore usable picks after the Hotspawn 403

The canonical publisher run
[39012768749](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39012768749)
completed at 07:17Z but published `coverage_complete: false`. The collect step took
two seconds and the inventory source reported `403 Client Error: Forbidden` for
`https://play.hotspawn.com/lobby`, so the site relabelled every otherwise
source-backed estimate "Inventory unverified" and the leaderboard plan reported
**0 currently usable** lines. The same 04:27Z snapshot had recorded HTTP 200 for the
lobby, the CS2 lobby and the public fixture API, and the live
[`data/sources.json`](https://buffedlizard55-lab.github.io/MaltaProj3/data/sources.json)
still shows those responses. The outage was in the rendered HTML, not in the
official fixture list.

What changed, and why each piece is verifiable:

1. **Inventory authority (`scripts/sources.py`, `scripts/collect.py`).** The public
   fixture array is read first in each round and must be a non-empty,
   duplicate-free array. Both rendered pages are then read; if any page is
   readable it must match the API exactly or the refresh fails closed, exactly as
   before. Only when *no* page is readable is the API array published, and it is
   published with `inventory_crosscheck: "unavailable"`, the actual per-page error,
   a warning flag (`inventory-crosscheck`) and a `::notice` annotation. An HTTP 200
   response that carries no Hotspawn app state is treated as an unreadable
   challenge page; a page that does carry app state but breaks the contract still
   fails closed. `scripts/validate.py` re-verifies the API row set, the cross-check
   marker, and every page claimed as read, on every build.
2. **Visible provenance (`scripts/build.py`).** The executive summary and the
   coverage page state whether the inventory is a three-response reconciliation,
   a partial cross-check or API-only, and the hero kicker changes accordingly. A
   blocked page never silently becomes "reconciled".
3. **Picks at a glance.** The executive summary now opens with a compact index of
   active fixtures (upcoming picks first, then every unresolved fixture, then
   recent context) with the selected team, its probability, the source link and a
   deep link into the full evidence. It is a view over the same canonical
   selection, adds no probability and re-orders nothing by opinion. At 390 px the
   first pick and its sources now appear within the first screen instead of after
   roughly 2,800 px of page.
4. **Honest even lines (`scripts/build_twc.py`).** A genuinely even external line
   (50.0% / 50.0%) is now labelled "No edge — even line" with the reason, instead
   of the vague "Pick — unverified", which wrongly implied missing data. No side
   is invented.
5. **The same guard for unlisted fixtures (`scripts/build_twc.py`).** The
   tournament-card table for HLTV-listed Day-4 fixtures absent from the weekly
   inventory still assumed a directional `pick_index`. An exactly even external
   book stores `pick_index: null`, so that path would have raised `TypeError`
   instead of publishing. It now prints both 50.0% prices with "No edge — even
   line" and never names a side. A new test covers it.

Verification performed on this tree before and after the release PR: **578 Python
tests** pass, **78 Playwright checks** pass (including two new phone-width glance
checks), **106 independent pick-safety browser assertions** pass (Python/JS parity,
expiry, lock, clock rollback, 320/390/768/1440 px and axe WCAG A/AA),
`scripts.build` replays 80 source rows, validates all internal links/anchors, and
the strict row audit reports 0 violations. The branch's own read-only
[origination audit](https://github.com/buffedlizard55-lab/MaltaProj3/actions/workflows/origination.yml)
reported `{"records": 93, "crosscheck": "complete", "verified_pages": ["lobby", "cs2"]}`
on commit `d136c0d`, confirming the reconciled path still runs normally when the
HTML is readable.

Sources used for this change: the Hotspawn public fixture API and lobby pages
listed above; HLTV match pages for the Day-1–Day-3 facts already displayed
(`2399384`–`2399415`, for example
[9z vs Aurora](https://www.hltv.org/matches/2399384/9z-vs-aurora-thunderpick-world-championship-2026));
the official
[Valve regional standings](https://github.com/ValveSoftware/counter-strike_regional_standings)
for rating-model inputs; Polymarket, Kalshi, Thunderpick and Bovada for prices.
No new probability, alias or editorial adjustment is introduced by this session.

Flagged for review: the intermittent HTTP 403 on the rendered Hotspawn pages is
recorded on `/review/` with the exact response text. The site continues to treat
Hotspawn percentages as non-inputs, and every still-unresolved fixture remains
listed with its reason rather than a default 50/50.

### Release and live verification (17 October, 11:00Z)

- PR [#79](https://github.com/buffedlizard55-lab/MaltaProj3/pull/79) merged to
  `main` as `0318219`. Both required checks were green on the PR: `originate`
  (1m20s) and "Rows, build, links, mobile and accessibility" (5m16s).
- `Refresh and deploy CS2 dashboard` and `pages build and deployment` both
  completed successfully for `0318219`, and the deployed artifacts were then
  fetched directly rather than trusting the job status.
- Live [`snapshot.json`](https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json) (the downloadable build output every page links to)
  was generated at `2026-10-17T10:49:22Z` with `coverage_complete: true`,
  `inventory_crosscheck: "complete"`, 93 fixtures (32 upcoming), 24 priced with
  probabilities and 8 explicitly unresolved. Production therefore exercised the
  normal three-response reconciliation path, not the API-only fallback.
- The deployed executive summary renders `#picks-at-a-glance` with 18 rows
  including every unresolved fixture, links each row to its Hotspawn page, source
  and full evidence, and shows `FURIA vs Aurora` as "No edge — even line" rather
  than inventing a side. The `/review/` and `/twc-picks/` pages are live with their
  source links.


## Final day and refresh repair — 17 October 2026

The [Day-5 guide](https://buffedlizard55-lab.github.io/MaltaProj3/twc-picks/#day-five-picks)
now leads the TWC view, with a one-tap executive-summary link. Its JSON is
`data/twc-day5-picks.json`. Existing Day-3/4 anchors and exports remain available
as historical context. Day-4 results are replayed from original HLTV HTML;
HLTV is explicitly an independent reporter, not the tournament organizer.

The collector revisits playoff URLs discovered in hash-verified original HLTV
pages even when the current event page no longer links completed rounds. These
are discovery leads only: no retained team, score or time becomes a new fact.
Final-day exchange evidence is retained separately from Day-4 evidence and
recomputed from original books. All weekly fixtures remain in the canonical
complete list regardless of tier. Independent tournament lines cannot invent a
Hotspawn entry or lock, and missing sources remain blank in the dedicated
[final-day limitations](https://buffedlizard55-lab.github.io/MaltaProj3/twc-picks/#day-five-unresolved).

An eight-hour clock-dependent regression assertion blocked four scheduled jobs
before collection. The test now pins its synthetic clock and tests the opposite
stale case too; runtime freshness checks are unchanged. New final-day checks
cover canonical equality, missing probabilities, no inferred results, no-JS
snapshot-only display, per-fixture public JSON/HTML parity, and phone WCAG A/AA.


For Day-5 tournament fixtures left unpriced by the exchange stage, the collector
also attempts original Thunderpick and Bovada full-series two-way lines. It
reuses the reviewed parsers, exact pair/start matching and proportional no-vig
formula. Every response is saved and hash/origin/time checked at replay. This
fallback never changes an existing canonical estimate; unsupported entries
remain explicitly unresolved. Raw paired decimal odds are shown alongside
supported final-day bookmaker estimates for manual review.

## 17 October session arena-534ae9e5: make the publisher unable to expire again, and publish the repository review

**The publisher failure was a single wall-clock assertion, and the fix had to outlast it.**
The four scheduled runs
[39038670350](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39038670350),
[39045650525](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39045650525),
[39054246287](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39054246287) and
[39058407711](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39058407711) all failed
at "Regression tests (repository fixtures, before any cache restore)", while the last successful
scheduled run
[39031549764](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39031549764) completed at
about 12:20Z. `scripts/build.py::shell` decided staleness with `datetime.now(timezone.utc)` against a
fixture whose `inventory_observed_at` was hard-coded to `2026-10-17T04:27:55Z`, so the eight-hour
window closed at **2026-10-17T12:27:55Z** — exactly when the successful run stopped. Because the
regression tests run *before* the cache restore and before collection, one expired assertion froze
the whole refresh.

Pinning one test is not enough: the same wall clock is read in `matches_table`, `glance`, `summary`,
`picks`, `coverage`, `scripts.build.build` and `scripts.build_twc.render`. All of them now take an
explicit reference time, and **one build passes a single reference time to every page**, so a page
can never disagree with itself about freshness and a test can pin the whole site to a known instant.

`tests/test_freshness_determinism.py` makes that permanent. It asserts the injection contract, and
re-runs the repository's time-sensitive test modules with the production clock **pinned to four
absolute instants** that bracket the fixture that broke the publisher — before the observation,
inside the eight-hour window, just after the window closed, and well after the tournament. The
instants are absolute on purpose: a guard that shifted the clock relative to "now" would stop
detecting the bomb once the real clock had moved past it, which is exactly when the bomb has
already broken the publisher. The first draft of this guard used a relative shift, did not catch an
already-expired bomb, and was corrected before it was committed.

**A line-by-line repository review is published.** The
[Flagged for Review page](https://buffedlizard55-lab.github.io/MaltaProj3/review/) now carries a
second register, `data/research/534ae9e5/repo-review.json`, with eight reviewed items and an
https source link for every one:

| Item | Area | Status | Summary |
| --- | --- | --- | --- |
| 534-01 | publisher / regression gate | fixed | The expired wall-clock assertion that froze the four-hour refresh. |
| 534-02 | tournament coverage | fixed | The final day of the tournament was published nowhere. |
| 534-03 | workflow permissions | **needs review** | `.github/workflows/collect-preview.yml` still requests `contents: write` and commits to the finished session branch `arena/11c1fa20-maltaproj3`. It cannot reach `main` and publishes nothing, but it is a write-capable leftover. **Deliberately left unchanged** — removing a workflow is the owner's decision. |
| 534-04 | documentation | fixed | The README's measured counts no longer matched the tree. |
| 534-05 | archive separation | verified | `docs/` and `archive/root-session/` are banner-marked in the artifact and the retired root URLs redirect. |
| 534-06 | exported data | verified | `data/picks.csv`: 80 rows, every row carries a Hotspawn source, every priced row carries an analysis source, unresolved rows stay blank. |
| 534-07 | identity registry | verified | 17 aliases, all evidenced and competition-scoped. |
| 534-08 | platform | platform limitation | GitHub Pages stays in legacy build mode (HTTP 403 on the setting change); the publisher orders the two steps itself. |

Rendering more than one register exposed a defect that a single register could not show: the
page-wide lineup-disambiguation block was emitted once per register, repeating its element ids and
breaking the in-page anchors that point at them. It is now rendered once for the page, and
`tests/test_review_register.py` fails if any element id is repeated.

**Integration.** Session `arena-ed853bdd` published the final-day view (`scripts/day5.py`,
`scripts/twc_books.py`) on `main` first, so that implementation stays canonical and this session
added only what was missing: the reference-time injection, the guard, the second review register
and the repeated-id fix. The board at
[`COORDINATION.md`](https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/COORDINATION.md)
records the claim, the scope extensions, the completion evidence and the merge result.

## 19 October session arena-c03ef201: a researched pick for every match

The standing brief asks for a pick or win probability for **every** Hotspawn-listed CS2 match — including low-tier matches no exchange or sportsbook lists — always from verified external sources (HLTV first, then esportsbooks and esports betting lines), never from Hotspawn “% picked”, with unresolved picks and limitations published as their own executive-summary section and every table row carrying an official source link.

**What this session added (all additive; featured money lines are never overwritten):**

1. **Pinnacle guest-board money rung.** `scripts/pinnacle_lines.py` now backs a general first-party bookmaker rung: two-way **series period 0** moneylines only (periods ≥ 1 are per-map prices and are never used), American prices converted to decimal, and a participant-text guard that rejects “Yes/No”, “Odd/Even” and score-grid specials before any price is read (a latent defect the session probe exposed; regression-tested). Prices keyed by participant id are realigned onto participant order. The board joined the money ladder as an independent provider vote (observed live 2026-10-19: Nemesis–Nuclear TigeRES priced by Pinnacle alone at 55.9/44.1).
2. **HLTV world-ranking research model.** `scripts/hltv_ranking.py` publishes the same uncalibrated 400-scale logistic transform as the Valve rung, over HLTV’s official weekly ranking points (`/ranking/teams`, publication dated by HLTV’s own slug, 14-day ceiling, both teams on the same publication). It runs only when the Valve roster model has no row — exactly the low-tier gap — and never overrides money, aggregated or Valve estimates. Observed live: Apogee Betclic–Spirit Academy resolved 50.7/49.3 after Valve failed on ambiguous short names.
3. **Wide-book indicative guidance (last resort).** When the only observed two-sided books fail every spread ceiling (observed up to 0.90 wide), the **narrowest** such book’s midpoint is published as `method: guidance` — amber “Guidance only” badges everywhere, excluded from `MONEY_METHODS` and from the leaderboard plan’s upset rules, each row showing its exact bid/ask spread, and an exactly-even midpoint published as “No edge · Even”. Observed live: Lynn Vision–Morningstar 75/25 (Polymarket book, 0.35 spread) and Lavked–ex-6666 ~50/50 (Kalshi book, 0.90 spread).
4. **Reviewed identity joins.** `data/origination/aliases.json` gained two competition-scoped entries — “Betclic” → “Apogee Betclic” and “Aurora Young Blud” → “Aurora YB”, both for Stake Ranked Episode 6: Closed Qualifier only — on the same documented same-slot/shared-opponent evidence class as the earlier WBT join, flagged for manual confirmation on the Flagged for Review page.
5. **Runner research workflow.** `.github/workflows/c03ef201-research.yml` runs the full live pipeline on GitHub’s runner (the only environment with provider egress) and commits only dated reports and hash-checked originals to `data/research/c03ef201/`. `workflow_dispatch` remains HTTP 403 for this token, so a push trigger is used with a guard that skips the workflow’s own report commits.

**Result on the 2026-10-19T05:29Z snapshot: 31 of 34 active fixtures carry a researched estimate; 3 stay intentionally blank** (ex-6666–Privateer, The Last Resort–LFO 10, Chinggis Warriors–WXM — each has one team with an official HLTV page but no ranking entry, no Valve row and no price anywhere). The executive summary’s [Unresolved picks & limitations](https://buffedlizard55-lab.github.io/MaltaProj3/#unresolved) section, the [complete list](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks) and the [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/) page publish those three with their full research trails and official links; nothing is filled with a guess. Every new rung replays from saved originals before the site builds (708-test suite green).

## 22 October session arena-7e8bed83: every-match coverage is now enforced, not just built

- **New post-deploy invariant.** `scripts/coverage_audit.py` checks the complete picks list row by row: counts must equal the rows, every resolved fixture has two probabilities in (0, 1) summing to 1, a known ladder method, https source/evidence links and a pick that is exactly the higher-probability team (an exactly even estimate names no side), and every unresolved fixture has no pick but an https-linked HLTV-first research trail plus published limitations. `scripts/verify_live.py` now fails the deployment verification if the public data violates this — a silent blank can no longer reach phones unnoticed. Hotspawn "% picked" and HLTV fan votes must stay explicitly unused in the published policy.
- **Live audit (2026-10-21T23:42Z snapshot).** Featured exact-name method: 7 picks / 5 unresolved of 12 active. Complete researched list: **12/12 resolved, 12 directional picks, 0 unresolved**. Recorded with sources in [`data/research/7e8bed83/live-audit.json`](data/research/7e8bed83/live-audit.json); findings and the legacy-Pages platform limitation are on the [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/) page. The executive summary keeps its phone-first banner, Picks at a glance and separate [Unresolved picks & limitations](https://buffedlizard55-lab.github.io/MaltaProj3/#unresolved) section, which correctly reports zero only while the complete list is fully resolved.

## 22 October session arena-3a5448de: every-match coverage re-researched, one unresolved register

- **Live coverage re-verified from the runner** (2026-10-22T08:04–08:06Z): 43 active Hotspawn CS2 fixtures, 43 with sourced probabilities, **42 with a directional pick, 0 blank**, and 1 resolved-but-even fixture with no side (Isurus vs Hacha, HLTV points 2.0 vs 2.0). Evidence: [`data/research/3a5448de/live-research.json`](data/research/3a5448de/live-research.json) and [`findings.md`](data/research/3a5448de/findings.md).
- **For the 19 fixtures the featured method could not resolve with a money line, sources were researched in the brief's order — HLTV first, then esportsbooks/betting lines.** HLTV listing/ranking answer HTTP 403 to the runner and publish no prematch price (fan vote excluded). Stake, GG.BET, Marathonbet, EGamersWorld, BetBoom, 1xBet, DraftKings, Betway, Oddspedia (410) and Luckbox gave no usable surface; OddsPortal and Rivalry answered 200 but listed none of the target teams; bo3.gg bound 14 of 19 fixtures but published a bookmaker block for none of them. bo3.gg's team `rank` field has no published strength methodology in its record, so it was recorded as a rejected lead, **not** wired. No probability, pick or alias changed; the model-only fixtures keep their labelled research estimates and failed-source trails, retried every four hours.
- **The executive summary now has exactly one "Unresolved picks & limitations" section.** It previously rendered that title twice with different counts (the complete-list register vs a featured-method table), with phone shortcuts pointing at both. The bottom section is now "Featured-method gaps, before research fallback" and every summary shortcut lands on the single register (`#unresolved-register`), which also contains *Picks without a betting line · limitations* and the dated line-source sweep.

### Verification notes for this session (arena-3a5448de)
- **The full dashboard check is green again.** `Validate dashboard` had no successful run in the last 100 attempts; its failure log lives on a storage host that restricted environments cannot read, so nobody could see the failing test. This session made the browser step self-describing (JSON reporter, failure artifact, and one `::error` annotation per failing test with its selector and measured contrast). That exposed a real 2.23:1 color-contrast failure on all seven pages at 1440px: the sidebar flag-count badge's base colour was only readable because of a later override. The base declaration is now `#f6d4aa` (≈10:1) and a test locks it.
- **Checks on the merged head:** `Rows, build, links, mobile and accessibility` pass, `originate` pass.
- **Flagged for Review** carries the Isurus–Hacha even estimate and the dated no-new-source record with links.

## 22 October session arena-aae76fb3: the phone row names the source it links

The live snapshot at 05:37Z already resolved **33 of 33** active Hotspawn CS2 fixtures (15 from a
money source, 18 from a labelled research model, 0 unresolved). This session found and fixed two
places where the *rendering* was less honest than the data behind it:

- **A consensus line was published as “Bookmaker”.** `glance()` chose its link text with a ternary
  chain that only understood `market`, `model`, `reference` and `guidance`; every other money method
  fell through to `Bookmaker`. UPGRADE–Virtus.pro is a median of **Bovada + Pinnacle**, and its link
  read “Bookmaker” over a single Bovada URL; UNiTY–Apogee was the same over a Polymarket URL. New
  `analysis_source_label()` reads each row's own `source` and `source_url` and names the destination
  (Polymarket, Kalshi, Thunderpick, Bovada, Pinnacle, EGamersWorld, Valve, HLTV ranking, bo3.gg) or
  the provider count for a consensus. It never invents a provider the record does not name.
- **A researched money line was badged only “Researched”.** That marker stays — it is the audit trail
  for a fallback row — but a money-backed fallback now also carries its basis badge (`Consensus`,
  `Bookmaker`, `Market line`, `Aggregated`). Model and guidance rows keep the single purple marker.
- **The executive-summary tile no longer reads “0 without a line · 18 model-only”.** That tile was
  rewritten on `main` by session `arena-4c972a51` (PR #174) to `{unresolved} without a pick ·
  {model} from research models · why + sources`, linking a dedicated `/unresolved/` page. This
  session preserves that wording and adds a regression test so “without a line” cannot return.

**Independent re-verification** (dated, first-party, in
[`data/research/aae76fb3/verification.json`](data/research/aae76fb3/verification.json)): 23 of the 33
published fixtures matched the rendered [Hotspawn lobby](https://play.hotspawn.com/lobby)
name-for-name and start-time-for-start-time at 07:36Z, including the four cards with no “View Match”
link; eight later DFRAG/Tesla Cup fixtures appeared on the lobby after the snapshot's observation
time and are picked up by the next four-hour run (freshness, not a gap); six model probabilities were
recomputed from [Valve's official 2026-10-05 standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md)
and all six reproduce to the published one-decimal figure (BakS 73.37%→73.4%, Butterfly 77.42%→77.4%,
Nemesis 91.83%→91.8%, Donstu 40.46%→40.5%, Nuclear TigeRES 93.00%→93.0%, 6yuBoJlbl 62.60%→62.6%);
and the [HLTV UNiTY–Betclic page](https://www.hltv.org/matches/2399784/unity-vs-betclic-stake-ranked-episode-6-closed-qualifier)
confirms the fixture identity. No probability, pick, alias or source capture was changed.

Integration onto `main` at `1cab862` surfaced one red test that PR #174 left behind:
`tests/test_review_flags.py` demanded a byte-identical published `data/latest.json`, which
contradicted the reconciliation keys `write_reconciled_snapshot()` was adding. `main` has since
fixed the renderer itself (`81139b1`, PR #181): the reconciliation counts are published as
`data/reconciled-counts.json` and `data/latest.json` stays byte-for-byte identical to the collector's
artifact. This session therefore keeps the original strict test rather than a relaxed one — both the
source and the published snapshot must match the collector byte for byte, and the renderer, the data
and every finding are untouched.

**A red pipeline that was not this branch's fault.** While the PR waited, `checks.yml` had 193
failures and 7 successes in the previous three hours across every session's branch. The public run
page could not name the failing test (job logs live on a host this environment cannot reach), so the
browser step now publishes each failure as an annotation
([`scripts/playwright-annotations.mjs`](scripts/playwright-annotations.mjs)). It immediately named a
real defect: at 1440 px the sidebar's last link (`.sidebar-repo`, "Open-source & auditable") overflowed
the fixed sidebar and was painted at y=860 in an 844 px viewport, outside its own navy panel — 2.23:1
against the page background and not clickable. Session `arena-ca4d2a02` reached the same conclusion
and its fix is the one on `main` (`c536501`); this branch keeps that fix, adds
`overscroll-behavior:contain`, and pins the behaviour with
[`tests/browser/sidebar_fit.spec.mjs`](tests/browser/sidebar_fit.spec.mjs). The job cap is 45 minutes
because the identical commit took 12 minutes idle and 25m52s on a loaded runner. `5cc2673` passed the
full check job, and the merged head passed it again in 9m32s.


### Publisher recovery verified — 23 October 2026, 06:30Z

The four-hour publisher is running again. Scheduled run `39906935915` passed the pre-collection regression step, deployed, and synced the verified build into the branch root; the public site now shows **"Source snapshot available · 23 Oct 2026, 08:17 Europe/Malta"** with 94 inventory records, 32 upcoming fixtures, **32 with a pick and 0 unresolved**. Two independent regressions had stopped it on 22–23 October: the date-bound `tests/test_96fbe295.py` check (PR #191) and a literal `% picked` in the low-tier copy that `tests/test_f4eb8ae3.py` forbids (PR #193).

A read-only runner probe at **06:15:55Z** re-audited every active fixture: 32/32 with a pick, 0 defects, 23 external money lines and 9 model-only estimates. Fresh research at **06:16:13Z** re-checked all nine unpriced fixtures and found no new two-sided prematch price, so no probability, pick or alias changed. The full repository suite on the merged head passes: **1012 tests, OK (675 s)**.

## 23 October session arena-e7d7a410: a fresh live audit, the unresolved register, and the publisher that stopped on a date

**What was measured, on a runner, not asserted.** The coding sandbox has no egress to Hotspawn,
HLTV or any bookmaker, so this session added a read-only workflow
([`.github/workflows/e7d7a410-probe.yml`](.github/workflows/e7d7a410-probe.yml), removed before
merge) that runs the repository’s own collectors and then
[`scripts/e7d7a410_audit.py`](scripts/e7d7a410_audit.py). At **2026-10-23T05:08:16Z**, against the
live inventory observed at 05:07:07Z:

| Check | Result |
| --- | --- |
| Active Hotspawn CS2 fixtures | **30** |
| With a directional pick | **30** |
| Without a pick / defective rows | **0 / 0** |
| Resolved by an external money line | **21** (15 market, 4 bookmaker, 2 consensus) |
| Resolved by a labelled research model | **9** (8 Valve standings, 1 own bo3.gg results network) |
| Rows with two probabilities that sum to 1 and an official `https` source | **30 of 30** |

The featured exact-name method alone left **6** of those 30 blank (`data/latest.json`: 24 picks,
6 unresolved). The published ladder resolved all six — **no price was invented and no probability
was shifted**. The dated snapshot and the line-by-line table are published in
[`data/research/e7d7a410/live-coverage-audit.md`](data/research/e7d7a410/live-coverage-audit.md)
with the raw `latest.json` / `origination.json` beside it.

**HLTV first, then esportsbooks — for the nine fixtures with no betting line.** The audited
read-only probe was reused unchanged; its runner observations at 05:31:08Z are in
[`data/research/e7d7a410/line-sources/live-research.md`](data/research/e7d7a410/line-sources/live-research.md).
HLTV’s match listing and ranking both answered **403** to the runner (it publishes no prematch price
in any case), EGamersWorld 403, DraftKings 200 with no target price, Stake 403, OddsPortal 200 with the teams listed,
Rivalry 200 with the teams listed, GG.BET 403, BetBoom 401, 1xBet 203, Marathonbet 403, Betway 404,
Oddspedia 410, bo3.gg 200 with **8 of 9 fixtures bound by both names and start but a two-sided
relay quote for none**, and Pinnacle’s guest API 200 with **no price for any target fixture**.
**No new two-sided prematch price existed, so no probability, pick or alias changed.** All nine keep
their model estimate, its source link and this limitation, listed one row at a time on the
executive summary under *Picks without a betting line*.

**Why the deployed site looked incomplete.** The last successful publish (`2026-10-22T13:21Z`)
carried 37 fixtures; the fresh inventory carries 30 active fixtures, six of today’s having appeared
after that observation — Phantom Academy vs Banda chuya (1081605), JiJieHao vs Eternal Fire,
Isurus vs Hacha (1082926), K27 vs Virtus.pro (1083014), BESTIA vs Galorys and BESTIA Academy vs RED
Canids — plus the later FOKUS vs ex-6666 and 24–31 October card. The cause was not the pick method:
`pages.yml`’s `verify-and-deploy` job has failed **before collection** since 14:05Z on 22 October
(runs 39792708185, 39807044948, 39845991470, 39861117407, 39871371551, 39881298806) on a single
date-bound assertion, `tests/test_96fbe295.py::test_check_mode_reports_a_current_root_and_then_drift`.
That test pins a build to 2026-10-22T08:40Z and calls the publisher without a clock, so the
publisher’s correct twelve-hour guard refuses it once the calendar moves on. PR #190 (session
`arena-4ac63e41`) fixes it by injecting `now`; this session verified that head locally (31/31
tests pass) and did not edit its files. The whole repository suite otherwise passes offline:
**995 tests, 1 failure — exactly that test**.

**Phone summary and unresolved section.** The executive summary already leads with a jump bar, a
full *Picks at a glance* list showing both teams’ probabilities and a separate
`#unresolved-register`; the dedicated `/unresolved/` page carries every pickless or model-only row
with the sources actually tried. Nothing in that layout needed a change to meet the brief; this
session verified it in the built HTML and left the rendering untouched.

## 23 October session arena-f8736556: plain-URL parity, probability replay and legacy publisher ordering

**Start on a phone:** [Executive summary](https://buffedlizard55-lab.github.io/MaltaProj3/) → [Picks at a glance](https://buffedlizard55-lab.github.io/MaltaProj3/#picks-at-a-glance) → [every match, both probabilities and evidence](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks). The separate unresolved/limitations register is inside the summary at [`#unresolved-register`](https://buffedlizard55-lab.github.io/MaltaProj3/#unresolved-register), with a dedicated [Unresolved picks](https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/) page and dated findings on [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/).

- **Independent public audit:** [`scripts/f8736556_audit.py`](scripts/f8736556_audit.py) reads the plain public HTML, plain `data/latest.json` / `data/origination.json`, and the linked top-level `snapshot.json` when a deployment publishes it. Query-string and duplicate-slash reads are recorded only as cache diagnostics and never make a stale plain URL pass. At **2026-10-23T12:09:25Z**, the HTML and both legacy-path JSON feeds described the same snapshot (`generated_at 2026-10-23T11:18:01Z`; inventory observed `2026-10-23T11:17:42Z`): **27 active fixtures, 27 directional picks, 20 external-line rows, 7 research-model rows and 0 unresolved**. The pre-merge deployment did not yet publish `snapshot.json` (404 recorded in the audit).
- **Line-by-line replay:** every one of those 27 probabilities was recomputed from the quote/input fields retained in the complete-picks feed — order-book midpoints, bookmaker no-vig odds, provider medians, official rating points or the network rating scale — with **27 passes, 0 unsupported and 0 failures**. Each row's identity, start, lock, competition, Hotspawn source, probability pair, argmax pick and pricing source were also joined back to the inventory. Full table: [`data/research/f8736556/audit.md`](data/research/f8736556/audit.md).
- **Inventory timing, not hidden:** the collector asserted `coverage_complete=true` for the 11:17:42Z inventory. By 12:09:27Z Hotspawn's first-party API had added fixture `1083045` (Chinggis Warriors vs Rare Atom, 2026-10-24T03:00:00Z), so that new fixture was not in the 11:18 publication and is recorded as a refresh-timing finding for the next four-hour collect to resolve or explicitly leave unresolved.
- **Fallback-only line research:** only the seven rows then without an external money line were re-researched, HLTV first and then esportsbook/aggregator/exchange surfaces (23 surfaces plus the Pinnacle guest API and bo3.gg). HLTV returned a Cloudflare 403 to the runner; no fixture-bound two-sided price was readable, so **0 leads** were promoted and no probability or pick changed. The seven research-model rows and their limitations are in [`data/research/f8736556/line-source-research.md`](data/research/f8736556/line-source-research.md). Model percentages remain explicitly uncalibrated and are not described as bookmaker odds.
- **Publication race found and ordered:** at 10:00:08Z current HTML sat beside 15 October plain JSON because a legacy Pages build landed after the interim artifact deployment; a later legacy build also landed during a fresh artifact verification. The workflow now waits for the latest `main` legacy build before the interim and fresh artifact deployments, recovers once by waiting/redeploying/re-verifying if the first public verification fails, and honors GitHub's `building` status when the dynamic-run listing lags. Deterministic tracked `data/*` replay fixtures are still never copied into the branch root.
- **Remaining platform limitation:** the official Pages API still reports `build_type: legacy` from `main:/`; the attempted change to `build_type: workflow` returned HTTP 403 (`Resource not accessible by integration`). This session therefore does not claim Actions is the sole configured publisher. A repository owner can remove the race at its source by selecting GitHub Actions in Pages settings. The dated incident remains on Flagged for Review: [`publication-race-incident.json`](data/research/f8736556/publication-race-incident.json).
## 23 October session arena-a7128fdd: HLTV is reachable, Polymarket does list the low-tier matches, and four placeholder prices were refused

**The reachability conclusion in the board history was wrong, and it is corrected with a first-hand read.**
Ten session sweeps recorded HLTV as `403 · automated access refused` and concluded that no external evidence
exists for the fixtures the featured method cannot price. That is a property of the *GitHub runner's* network
path. Read directly at 2026-10-23T09:47Z–10:50Z, `https://www.hltv.org/matches` and individual match pages
answer **HTTP 200** and render in full. Two match pages were read end to end:
[2399849 K27 vs Virtus.pro](https://www.hltv.org/matches/2399849/k27-vs-virtuspro-winline-mpkbk-cis-lan-season-9)
and [2399699 Phantom Academy vs Banda Chuya](https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8).
To be precise about what was *not* wrong: the site copy already qualifies the runner's status ("HLTV match pages
are listed with the status the runner received"), so no published sentence misled anyone. What changes is the
operational conclusion — a session that can read HLTV should read it.

**What HLTV does and does not publish.** It publishes the best-of format Hotspawn leaves `null`, both
five-player lineups that the Valve-standings identity join needs, both world and VRS ranks, and explicit
stand-in warnings ("Virtus.pro is playing with stand-in: Patsi instead of F0R3VER"). It publishes **no
two-sided prematch price**: the Betting block on both pages carried only a Stake social-casino promotion, and
the betting-analytics page renders the template value `1.23` in every bookmaker cell (labelled eOddset and
Betway). Its "Pick a winner" widget is a fan vote, excluded by rule 2.

**The brief's "not covered on polymarket" is not quite what is happening.** Read directly,
[Polymarket's DFRAG Invitational directory](https://polymarket.com/esports/cs2/dfrag-invitational) lists
exactly three CS2 events and labels all three **$0 vol**. Two bind to Hotspawn fixtures by exact team names
*and* start time — `cs2-gz1-offcho-2026-10-25` (Ground Zero vs Off Chops, Oct 25 11:00 PM ET =
2026-10-26T03:00:00Z = Hotspawn 1082858) and `cs2-rstr-abyssa-2026-10-26` (Rooster vs Abyssal, Oct 26
11:00 PM ET = 2026-10-27T03:00:00Z = Hotspawn 1082861). So these matches *are* covered; they simply have no
liquidity, which is why rule 3's positive bid/ask and non-crossed-book tests cannot pass. Rooster vs Abyssal
displays `2.00x / 2.00x` at `50% / 50%` — an unpriced listing default. Adopting it would publish exactly the
50/50 fabrication the repository forbids, so it was refused.

**Four shapes of fake price were read, quoted verbatim, and refused.** EGamersWorld's `1.8 / 1.8` on both
sides, HLTV analytics' repeated `1.23`, Polymarket's unpriced `2.00x / 2.00x`, and the HLTV fan votes
(`33.6% / 66.4%`, `77.6% / 22.4%`) plus esports-news.co.uk's own `43% / 57%` power rating. Any of them would
have become a fabricated probability under a naive read. `scripts/reference_odds.py`'s identical-price
rejection and eight-hour freshness test are what already keep the first class out; the rest are kept out by
rules 2 and 3 and are now documented with their URLs in
[`data/research/a7128fdd/direct-observations.md`](data/research/a7128fdd/direct-observations.md).

**Nothing was priced, so nothing changed.** Across the 8 model-only fixtures: **0** new two-sided prices,
**7** fixtures that gained official identity or format evidence, **0** probabilities, **0** picks and **0**
aliases changed — and **0** identity conflicts actually found, against **1** real registry gap
(`los kogutos` → `Banda Chuya`, below). The new register renders on the executive summary *and* on `/unresolved/` as
`#direct-observations`, through `scripts/build.py::load_direct_observations` — deliberately the complement of
the runner-only `load_no_line_research`, and deliberately **ineligible** to feed the priced ladder. Its
Markdown sibling is generated from its JSON by `python -m scripts.a7128fdd_render_evidence` (`--check` fails on
drift), so the prose cannot disagree with the numbers.

**Three of this session's own claims were wrong and are corrected on the record, not deleted.**
1. *"Hotspawn 1081605 says Banda chuya but three surfaces say los kogutos"* — wrong, and so was the first
   correction (*"Hotspawn is corroborated and the aggregators are out of line"*). The accurate reading: **`los
   kogutos` IS `Banda Chuya`.** Read first-hand back to back, [bo3.gg's `los kogutos` team
   page](https://bo3.gg/teams/los-kogutos) lists starters **maaryy, tomiko, mwlky, AdrieN, showk** (all Poland,
   coach pako) — the same five players HLTV lists for Banda Chuya on match 2399699 — and the results match
   exactly (DONSTU 2-1 on 22 Oct, 2-0 ex-6666 on 20 Oct, 2-0 Revise on 17 Oct on both sites). So **no identity
   conflict exists anywhere**: Hotspawn 1081605, HLTV 2399699 (whose US-Eastern `07:00` display resolves to
   **11:00 UTC** by its own countdown, matching Hotspawn's `starts_at` to the minute), bo3.gg and
   esports-news.co.uk all describe one match. The real, actionable finding is a **registry gap**: `los kogutos`
   appears nowhere in `data/origination/aliases.json`, so `scripts.originate.resolve_name` cannot bind a bo3.gg
   or esports-news.co.uk quote for this fixture and rule 4's esportsbook rung stays unreachable for it *by name*.
   Nothing is lost today (bo3.gg shows `All odds are on` with no numbers, `bet_updates=null`), and the registry
   is another session's reviewed file, so it was **not** edited here — the cross-scope request is logged in
   `COORDINATION.md` with everything needed to add it in one step. Session `arena-81c1058a` reached the same
   identity independently from bo3.gg's side and recorded it on the board; this session adds the HLTV-side
   five-player and three-result corroboration.
2. *"'Team Abyssal' is an unregistered alias."* Wrong, because the registry was not consulted before flagging.
   [`data/origination/aliases.json`](data/origination/aliases.json) has held `Team Abyssal → Abyssal` scoped to
   DFRAG Invitational 2026 since 2026-10-23T06:26:00Z, with bo3.gg 132606, HLTV 2399891 and Hotspawn 1082861
   evidence and `must_not_match` guards. EGamersWorld is now recorded as a **fourth** corroborating surface via
   its schema.org JSON-LD `startDate 2026-10-27T03:00:00.000Z`. A test pins both corrections against the
   registry itself so neither wrong claim can return silently.

**Independent re-derivation of published probabilities.** Six priced rows were re-derived from second surfaces
using the repository's own rule `pᵢ = (1/oᵢ) / Σ(1/o)`, binding both sides through
`scripts.originate.resolve_name` against the reviewed registry rather than an ad-hoc normaliser — which matters
because `domain.name_key` deliberately keeps diacritics, so `Los Niños ≠ LOS NINOS` unless the registry says
otherwise. Result: **6 rows checked, 0 name bindings unresolved, 2 exact four-decimal reproductions** —
1082923 (bo3.gg ALKA 1.30 / Los Niños 3.20 → 0.7111 / 0.2889) and 1082980 (bo3.gg WBT Academy 1.49 / LPH 2.45
→ 0.6218 / 0.3782). Those two prove the ladder reads its relay board and de-vigs it exactly as documented. The
other four agree in direction and differ slightly because they come from a different surface than the one that
priced the row. **0 published values changed.** See
[`data/research/a7128fdd/verification.md`](data/research/a7128fdd/verification.md).

**One divergence is flagged and explicitly not adjudicated.** For 1081605 the published Valve-rating estimate
favours Banda chuya (0.4748 / 0.5252) while HLTV's VRS display puts Phantom Academy 9 points *ahead*
(777pt #167 vs 768pt #169) and the fan vote says 77.6%. The ladder prices from Valve's own regional-standings
file at a dated snapshot; HLTV's VRS column is HLTV's rendering on its own refresh; and Banda Chuya being
HLTV-Unranked with a VRS rank is exactly the case the "unranked floor" rung exists for. Settling the direction
needs Valve's standings file at the snapshot the ladder used, which this session did not read, so no value was
changed and no conclusion is drawn. It is on [/review/](https://buffedlizard55-lab.github.io/MaltaProj3/review/)
as `a7128fdd-1081605-vrs-direction-divergence`.

**Also verified, and now closed:** acceptance-audit check #9 (the rendered page stamp and the downloadable
`data/latest.json` must be one observation) was the last standing **FAIL** in session `arena-3149e7ae`'s
published-root audits at 05:05Z, 07:25Z and 08:20Z. Read back from the live published root at 09:45Z, both
carry `2026-10-23T09:23:57Z`. Local re-run: `9 pass · 1 info · 0 fail`, the single info being the age of the
checked-in 15 October replay fixture rather than a live defect.

**Live coverage at research time** (runner run
[39934809201](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39934809201), snapshot
`2026-10-23T09:52:16Z`): **30 active fixtures, 30 with a directional pick, 0 with no pick**; 22 money-backed
and 8 model-only. The compact manifest this session added (`python -m scripts.a7128fdd_manifest`) is what
names those 8 and their exact binding facts; it reads the two feeds the pipeline already produced and prices
nothing.
