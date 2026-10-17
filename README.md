# Spawn Scout — Hotspawn CS2 match intelligence

A mobile-first, source-linked GitHub Pages dashboard covering **every CS2 record returned by Hotspawn’s scheduled-fixture feed**, including academy and low-tier matches. Obvious picks and both teams’ calculated probabilities are shown only when supported by original external evidence; unresolved values remain blank.

**Live dashboard:** https://buffedlizard55-lab.github.io/MaltaProj3/

| View | What it contains |
| --- | --- |
| [Executive summary](https://buffedlizard55-lab.github.io/MaltaProj3/) | **Picks at a glance** (a phone-first, one-line-per-fixture index that opens above the fold and links every row to its full evidence), coverage, complete-pick counts, upcoming matches, the Day 1 contrarian review, a map of every page, and unresolved-pick limitations |
| [Complete match picks](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks) | The phone-first list: every non-archived fixture with both probabilities, one obvious pick, lock times and expandable evidence |
| [Leaderboard plan](https://buffedlizard55-lab.github.io/MaltaProj3/strategy/) | One plan pick per open fixture from our own external-line probabilities, the few underdogs worth an upset play (with their expected-point cost), a separate unresolved section, the Thunderpick tournament pick'em (team plus score), Hotspawn's verified scoring contract and Days 1–2 results cross-checked against Hotspawn's own API |
| [All match picks](https://buffedlizard55-lab.github.io/MaltaProj3/picks/) | Both probabilities, suggested team, method badge, searchable/filterable rows, source links and expandable evidence. Every non-archived fixture shows a pick or an explicit blank: featured exact-name estimates first, then clearly badged **Researched fallback** estimates from the audited research ladder |
| [Day 1 contrarian review](https://buffedlizard55-lab.github.io/MaltaProj3/#contrarian) | Source-linked 9z–Aurora upset review, Aurora rebuild context and a strictly bounded 9z–Falcons watch that never overrides the primary pick |
| [Upset review & edge](https://buffedlizard55-lab.github.io/MaltaProj3/edge/) | Dated first-party deep dive: day one at Thunderpick World Championship 2026 (9z 2-0 Aurora and the other three series, map by map), Aurora roster context (not a proven cause of the upset), official Valve standings for the current card, dated market observations and the seven rules applied before disagreeing with a market |
| [TWC Day 4 & Day 5 picks](https://buffedlizard55-lab.github.io/MaltaProj3/twc-picks/) | The semifinals and the **final day** regenerated from the **same complete-picks snapshot**: both probabilities, default picks, optional underdog screens and expected-point costs, the third-place decider and grand final with their verified participants, the Days 1–4 result ladder that guides them, Days 1–2 results replayed from original HLTV pages, roster/rest verification and unresolved limitations. No fan votes, outrights or narrative probability adjustments |
| [Coverage & original sources](https://buffedlizard55-lab.github.io/MaltaProj3/coverage/) | Inventory reconciliation, source health, complete past-start archive and JSON/CSV downloads |
| [Methodology](https://buffedlizard55-lab.github.io/MaltaProj3/methodology/) | Exact matching, formulas, thresholds, source policy and model limitations |
| [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/) | Missing inputs, failed source access, identity ambiguity, format/status conflicts and unresolved research trails |

The observation times and counts on the live site are authoritative for that published snapshot. For scale, the first fully replayed snapshot on **14 October 2026** contained **88 records: 28 future starts and 60 past-start records**, with **9 Polymarket estimates, 4 original bookmaker estimates, 8 Valve-model estimates and 7 unresolved future matches**. Past starts still labeled `scheduled` are retained as source anomalies, not invented results.

## Source and probability rules

1. **Complete inventory first, and keep a valid official inventory usable.** The public scheduled-fixture API used by Hotspawn’s own client is the authoritative scheduled inventory. The rendered [Hotspawn lobby](https://play.hotspawn.com/lobby) and [CS2 lobby](https://play.hotspawn.com/cs2-pickems) hydration states are an independent cross-check; when either page is readable it must agree with the API exactly, and a readable page that disagrees still fails the refresh closed. When *no* rendered page can be read (observed HTTP 403 on both pages at 07:16Z on 17 October 2026, while the same API had answered 200 four hours earlier), the validated, duplicate-free API array is published with `inventory_crosscheck: "unavailable"`, a visible notice and a review flag instead of a reconciliation claim, so source-backed picks are not discarded over a secondary page. No pagination was present in the inspected client. A changed schema, duplicate IDs or an empty array still invalidates the refresh; it is never accepted as an empty or partial successful feed. New matches are rediscovered on every successful refresh.
2. **Never use Hotspawn “% picked.”** Community participation, offered points and crowd voting do not enter the calculations. Missing best-of formats, lineups and results are not inferred.
3. **Primary external market.** Discover candidates from [Polymarket’s CS2 directory](https://polymarket.com/esports/cs2) **and paginate the official CS2-tag event API to a terminal page** (bounded at 2,000 events; repeated pages/failures are explicitly flagged), verify an active, unique prematch **full-series match-winner** event with exact normalized team names and start time within 60 seconds, then obtain both original CLOB order books. Validate token/condition IDs, positive bid/ask size, noncrossed books, spread ≤0.12 and observation freshness. Normalize the two bid/ask midpoints. Directory percentages, map markets, props and outrights are not inputs. These are market-implied estimates, not verified true win probabilities.
4. **Research only missing primary matches.** Attempt [HLTV](https://www.hltv.org/matches) context first, then original esportsbook lines. The current split-anchor HLTV cards are parsed with sibling time/team context, and original HTML is saved and hash-checked for replay. Same-time records with one shared opponent but a different other team name are linked for review only—not silently treated as the same match. The public Thunderpick client uses a read-only **POST** `/api/matches` query with `{"gameIds":[6]}`; a failed GET does not establish that POST is unavailable. Require a unique exact fixture and prematch two-way series winner. Decimal odds are converted with `pᵢ = (1/oᵢ) / Σ(1/o)`. A single bookmaker is explicitly a single source, never described as consensus. Unsupported provider aliases stay unresolved.
5. **Explicit, higher-uncertainty model fallback.** Only after the primary, HLTV and bookmaker stages fail, use unique exact-name, five-player records from [Valve’s official regional standings repository](https://github.com/ValveSoftware/counter-strike_regional_standings). Name-matching rows that are not complete five-player records are excluded *before* the uniqueness test (so one complete row plus an incomplete remnant resolves), while a name with several complete five-player rows stays rejected as ambiguous. Reproduce the published Glicko expectation with fixed RD 75; use the latest applicable snapshot no older than 35 days. Raw official markdown and Git blob SHA are verified. This is an **uncalibrated research estimate**, not betting odds, and does not confirm today’s roster, stand-ins or veto. It never overrides a primary pick.
6. **Leave unsupported values blank.** Ambiguous names, stale/wide/one-sided markets, missing ratings or unavailable sources produce no fabricated probability or pick. Each such match remains in the list, unresolved section and review flags. Calculated fair decimal lines are illustrative reciprocals, not executable quotes.
7. **More independent money sources for the gaps (session c07e1b40).** For fixtures the featured methods leave blank, `scripts/originate.py` also reads [Kalshi](https://docs.kalshi.com/api-reference/market/get-markets) CS2 match-winner books (a CFTC-regulated exchange with an officially documented public API; scheduled start parsed from the contract rules and cross-checked with the event ticker; both yes books must be ≤0.12 wide) and [Bovada](https://www.bovada.lv/sports/esports/counter-strike-2)'s public prematch series moneylines (margin removed proportionally). The same exact-name/registry and 60-second start rules apply, in-play observations are excluded, and the originated line is the **median across independent providers** (Polymarket, Kalshi, Thunderpick, Bovada — one vote each). Rejected wide books are shown on the unresolved cards for guidance only. Every quote is replayed from its saved original response before the site is built.
8. **Scoped identity aliases, never fuzzy joins.** [`data/origination/aliases.json`](data/origination/aliases.json) is the reviewed registry that lets a provider display name ("Team Falcons", "BetBoom Team", "Aurora Gaming", "WBT") join a Hotspawn name. Every alias declares the exact competitions it applies to (`applies_to`), carries official https evidence, honours `must_not_match` exclusions, and is enforced in `scripts/originate.py` for market, bookmaker and model joins alike. An alias outside its declared competition never matches.
9. **Dated research is labeled as dated research.** The [upset review page](https://buffedlizard55-lab.github.io/MaltaProj3/edge/) (`data/edge-review.json`, built by `scripts/build_edge.py`) publishes day-one results, roster changes, official Valve standings and dated provider price observations for context. Every fact carries its own official source link and observation time. It is not refreshed by the four-hour pipeline, it never overwrites an automated estimate, and Hotspawn community percentages are never read — so "contrarian" here means disagreeing with the external market or ranking consensus only where verified evidence supports it, never crowd-fading.

HLTV directory research supports its observed split time/team links, joined only by the exact match URL. Repeated pinned cards are deduplicated; conflicting observations are rejected. Original HTML is retained as evidence. This confirms identities, not odds. For remaining gaps, each match now records the actual GG.BET, Pinnacle and Rivalry access-check limitations, not merely a global source-health warning. Unknown-start fixtures appear in the executive summary’s unresolved section, separate from the future-match count.

Every row links an official Hotspawn source. Every estimate links the original market, bookmaker or Valve record. [Full public snapshot](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json), [request manifest](https://buffedlizard55-lab.github.io/MaltaProj3/data/sources.json), [contrarian review evidence](https://buffedlizard55-lab.github.io/MaltaProj3/data/contrarian.json), saved first-party JSON evidence, and [CSV](https://buffedlizard55-lab.github.io/MaltaProj3/data/picks.csv) allow manual review and calculation replay. POST request payloads, observation times and response hashes are recorded without credentials.

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

At the time of writing (2026-10-17) the integrated tree passes 613 Python tests, 79 Playwright checks and 106 independent pick-safety browser assertions (the leaderboard plan has its own spec at 320/390/768/1440 px with axe WCAG A/AA at phone and desktop widths, as do the Day-4/Day-5 review sections). `scripts.build` replays 80 source rows, validates 607 internal links/assets/anchors, and the strict row audit accepts 406 rows (398 official-source rows plus 8 site-map navigation rows, 0 violations). These counts move with every session — re-measure with `.venv/bin/python -m unittest discover -s tests`, `npm test`, `node tests/pick-safety-browser.mjs` and a `scripts.build` run rather than trusting this sentence. **Non-blocking platform restriction:** GitHub Pages remains in legacy mode because the workflow token gets HTTP 403 when attempting the repository setting change. The sole publisher detects that mode, waits for the platform build, and publishes the verified artifact afterward; no user input is required.

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
- Live [`data/latest.json`](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json)
  was generated at `2026-10-17T10:49:22Z` with `coverage_complete: true`,
  `inventory_crosscheck: "complete"`, 93 fixtures (32 upcoming), 24 priced with
  probabilities and 8 explicitly unresolved. Production therefore exercised the
  normal three-response reconciliation path, not the API-only fallback.
- The deployed executive summary renders `#picks-at-a-glance` with 18 rows
  including every unresolved fixture, links each row to its Hotspawn page, source
  and full evidence, and shows `FURIA vs Aurora` as "No edge — even line" rather
  than inventing a side. The `/review/` and `/twc-picks/` pages are live with their
  source links.

## 17 October session arena-534ae9e5: unblock the four-hour publisher and publish the final day

**The publisher was blocked and the public site was frozen.** The scheduled runs
[39038670350](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39038670350),
[39045650525](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39045650525),
[39054246287](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39054246287) and
[39058407711](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39058407711) all
failed at the step "Regression tests (repository fixtures, before any cache restore)", while the
last successful scheduled run
[39031549764](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39031549764)
completed at about 12:20Z. The cause was a single wall-clock-dependent assertion:
`scripts/build.py::shell` decided staleness with `datetime.now(timezone.utc)` against a fixture
whose `inventory_observed_at` was hard-coded to `2026-10-17T04:27:55Z`, so the eight-hour
freshness window closed at **2026-10-17T12:27:55Z** — exactly when the successful run stopped.
Because the regression tests run *before* the cache restore and before collection, that one
expired assertion stopped every refresh.

The fix makes the reference time an injected argument rather than moving the fixture's date
forward. `shell`, `matches_table`, `glance`, `summary`, `picks`, `coverage`,
`scripts.build_origination.pick_row` and `scripts.build.build` now take an explicit reference
time, and one build passes a single reference time to every page, so a page can never disagree
with itself about freshness. `tests/test_freshness_determinism.py` makes that permanent: it
checks the injectability contract and re-runs the repository's time-sensitive test modules with
the production clock **pinned to four absolute instants** that bracket the fixture which broke
the publisher. Because the instants are absolute, the guard keeps working no matter when it
runs; it fails on the old wall-clock form at three of the four.

**The final day of the tournament is now published.** The site carried the Day 3 and Day 4
views but nothing for **18 October 2026**, the last day. HLTV lists the third-place decider
([match 2399416](https://www.hltv.org/matches/2399416/thunderpick-world-championship-2026-3rd-place-decider-match-thunderpick-world-championship-2026),
11:30Z) and the grand final
([match 2399417](https://www.hltv.org/matches/2399417/thunderpick-world-championship-2026-grand-final-thunderpick-world-championship-2026),
15:00Z). Both are decided by the 17 October semifinals, so the retained original pages publish no
participants yet.

- `scripts/twc_research.py::derive_day5` finds the two final-day series from **HLTV's own page
  titles** ("Grand Final", "3rd Place Decider Match") and their published start times.
- A participant is used only when the source publishes it, or **derived from a verified semifinal
  final score** and then labelled as a derivation with the semifinal pages it came from. An
  undecided series keeps its participants blank and receives no placeholder, no default 50/50 and
  no tournament outright price.
- `scripts/build_twc.py::render_day5` publishes the final-day cards, the **verified Days 1–4
  ladder** (every series a retained original has finished, with its published score and source
  link) and a guide that states plainly what those results can and cannot do.
- `scripts/verify_live.py::verify_day5` checks the deployed page against the published JSON:
  every percentage on the page must exist in the JSON, and a series without participants must
  show no percentage at all.
- `data/twc-day5-picks.json` is the machine-readable view, exported with the other two.

The Day-1–4 results are **context, never a probability premium**: a 2–0 series score is not a win
rate, a comeback is not momentum, and the 30% underdog screen is an editorial floor, not a
calibrated edge. The default pick stays the higher-probability side of the external line.

A line-by-line repository review is published on the
[Flagged for Review page](https://buffedlizard55-lab.github.io/MaltaProj3/review/) with the
source links for every item, including one item left for the owner: the retired
`.github/workflows/collect-preview.yml` still requests `contents: write` and commits to a finished
session's branch. It cannot reach `main`, so it publishes nothing, and it was deliberately not
removed by this session.
