# Spawn Scout — Hotspawn CS2 match intelligence

A mobile-first, source-linked GitHub Pages dashboard covering **every CS2 record returned by Hotspawn’s scheduled-fixture feed**, including academy and low-tier matches. Obvious picks and both teams’ calculated probabilities are shown only when supported by original external evidence; unresolved values remain blank.

**Live dashboard:** https://buffedlizard55-lab.github.io/MaltaProj3/

| View | What it contains |
| --- | --- |
| [Executive summary](https://buffedlizard55-lab.github.io/MaltaProj3/) | Coverage, direct links to the full picks list, upcoming matches and unresolved-pick limitations |
| [All match picks](https://buffedlizard55-lab.github.io/MaltaProj3/picks/) | Both probabilities, suggested team, method badge, searchable/filterable rows, source links and expandable evidence. Every non-archived fixture shows a pick or an explicit blank: featured exact-name estimates first, then clearly badged **Researched fallback** estimates from the audited research ladder |
| [Upset review & edge](https://buffedlizard55-lab.github.io/MaltaProj3/edge/) | Dated first-party review of day one at Thunderpick World Championship 2026 (9z 2-0 Aurora and the other three series, map by map), the verified Aurora roster rebuild behind that upset, official Valve standings for the current card, dated market observations and the seven rules applied before disagreeing with a market |
| [Coverage & original sources](https://buffedlizard55-lab.github.io/MaltaProj3/coverage/) | Inventory reconciliation, source health, complete past-start archive and JSON/CSV downloads |
| [Methodology](https://buffedlizard55-lab.github.io/MaltaProj3/methodology/) | Exact matching, formulas, thresholds, source policy and model limitations |
| [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/) | Missing inputs, failed source access, identity ambiguity, format/status conflicts and unresolved research trails |

The observation times and counts on the live site are authoritative for that published snapshot. For scale, the first fully replayed snapshot on **14 October 2026** contained **88 records: 28 future starts and 60 past-start records**, with **9 Polymarket estimates, 4 original bookmaker estimates, 8 Valve-model estimates and 7 unresolved future matches**. Past starts still labeled `scheduled` are retained as source anomalies, not invented results.

## Source and probability rules

1. **Complete inventory first.** Read both official [Hotspawn lobby](https://play.hotspawn.com/lobby) and [CS2 lobby](https://play.hotspawn.com/cs2-pickems) Angular hydration states, then reconcile their CS2 fixture IDs against the public fixture API used by Hotspawn’s client. No pagination was present in the inspected client. A changed schema, duplicate IDs or disagreement invalidates the completeness claim; it is not silently accepted as an empty or partial successful feed. New matches are rediscovered on every successful refresh.
2. **Never use Hotspawn “% picked.”** Community participation, offered points and crowd voting do not enter the calculations. Missing best-of formats, lineups and results are not inferred.
3. **Primary external market.** Discover candidates from [Polymarket’s CS2 directory](https://polymarket.com/esports/cs2) **and paginate the official CS2-tag event API to a terminal page** (bounded at 2,000 events; repeated pages/failures are explicitly flagged), verify an active, unique prematch **full-series match-winner** event with exact normalized team names and start time within 60 seconds, then obtain both original CLOB order books. Validate token/condition IDs, positive bid/ask size, noncrossed books, spread ≤0.12 and observation freshness. Normalize the two bid/ask midpoints. Directory percentages, map markets, props and outrights are not inputs. These are market-implied estimates, not verified true win probabilities.
4. **Research only missing primary matches.** Attempt [HLTV](https://www.hltv.org/matches) context first, then original esportsbook lines. The current split-anchor HLTV cards are parsed with sibling time/team context, and original HTML is saved and hash-checked for replay. Same-time records with one shared opponent but a different other team name are linked for review only—not silently treated as the same match. The public Thunderpick client uses a read-only **POST** `/api/matches` query with `{"gameIds":[6]}`; a failed GET does not establish that POST is unavailable. Require a unique exact fixture and prematch two-way series winner. Decimal odds are converted with `pᵢ = (1/oᵢ) / Σ(1/o)`. A single bookmaker is explicitly a single source, never described as consensus. Unsupported provider aliases stay unresolved.
5. **Explicit, higher-uncertainty model fallback.** Only after the primary, HLTV and bookmaker stages fail, use unique exact-name, five-player records from [Valve’s official regional standings repository](https://github.com/ValveSoftware/counter-strike_regional_standings). Reproduce the published Glicko expectation with fixed RD 75; use the latest applicable snapshot no older than 35 days. Raw official markdown and Git blob SHA are verified. This is an **uncalibrated research estimate**, not betting odds, and does not confirm today’s roster, stand-ins or veto. It never overrides a primary pick.
6. **Leave unsupported values blank.** Ambiguous names, stale/wide/one-sided markets, missing ratings or unavailable sources produce no fabricated probability or pick. Each such match remains in the list, unresolved section and review flags. Calculated fair decimal lines are illustrative reciprocals, not executable quotes.
7. **Scoped identity aliases, never fuzzy joins.** [`data/origination/aliases.json`](data/origination/aliases.json) is the reviewed registry that lets a provider display name ("Team Falcons", "BetBoom Team", "Aurora Gaming", "WBT") join a Hotspawn name. Every alias declares the exact competitions it applies to (`applies_to`), carries official https evidence, honours `must_not_match` exclusions, and is enforced in `scripts/originate.py` for market, bookmaker and model joins alike. An alias outside its declared competition never matches.
8. **Dated research is labeled as dated research.** The [upset review page](https://buffedlizard55-lab.github.io/MaltaProj3/edge/) (`data/edge-review.json`, built by `scripts/build_edge.py`) publishes day-one results, roster changes, official Valve standings and dated provider price observations for context. Every fact carries its own official source link and observation time. It is not refreshed by the four-hour pipeline, it never overwrites an automated estimate, and Hotspawn community percentages are never read — so "contrarian" here means disagreeing with the external market or ranking consensus only where verified evidence supports it, never crowd-fading.

HLTV directory research supports its observed split time/team links, joined only by the exact match URL. Repeated pinned cards are deduplicated; conflicting observations are rejected. Original HTML is retained as evidence. This confirms identities, not odds. For remaining gaps, each match now records the actual GG.BET, Pinnacle and Rivalry access-check limitations, not merely a global source-health warning. Unknown-start fixtures appear in the executive summary’s unresolved section, separate from the future-match count.

Every row links an official Hotspawn source. Every estimate links the original market, bookmaker or Valve record. [Full public snapshot](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json), [request manifest](https://buffedlizard55-lab.github.io/MaltaProj3/data/sources.json), saved first-party JSON evidence, and [CSV](https://buffedlizard55-lab.github.io/MaltaProj3/data/picks.csv) allow manual review and calculation replay. POST request payloads, observation times and response hashes are recorded without credentials.

## 15 October day-one review: the 9z–Aurora upset, verified

The executive summary teases and [`/edge/`](https://buffedlizard55-lab.github.io/MaltaProj3/edge/) publishes the full dated review. Every value below was read from the linked official source during the 2026-10-14 → 2026-10-15T10:26Z research window and is stored in [`data/edge-review.json`](data/edge-review.json) with its own observation time.

| Day-one series (14 Oct 2026, bo3) | Maps | Official source |
| --- | --- | --- |
| **9z 2-0 Aurora** (the upset: HLTV #17 vs #6; luchov 38-20, 97.4 ADR, 1.61 rating; +62 VRS points to 1571) | Inferno 13-11 · Nuke 13-1 | [HLTV series report](https://www.hltv.org/news/45718/9z-beat-aurora-2-0-to-kick-off-twc-2026) · [match page](https://www.hltv.org/matches/2399384/9z-vs-aurora-thunderpick-world-championship-2026) |
| Falcons 2-0 Ninjas in Pyjamas (needed OT on Ancient after leading 8-4) | Ancient 16-13 · Dust2 13-6 | [HLTV day-one report](https://www.hltv.org/news/45723/furia-fend-off-betboom-to-end-day-one-of-twc) · [results](https://www.hltv.org/results?event=8932) |
| Legacy 2-0 PARIVISION (blew 8-2 and 12-5 leads; OT on Mirage; arT's return) | Dust2 13-11 · Mirage 16-14 | [HLTV day-one report](https://www.hltv.org/news/45723/furia-fend-off-betboom-to-end-day-one-of-twc) |
| FURIA 2-0 BETBOOM (BETBOOM let 8-4 leads slip twice; KSCERATO 1.72) | Ancient 13-10 · Mirage 13-9 | [HLTV day-one report](https://www.hltv.org/news/45723/furia-fend-off-betboom-to-end-day-one-of-twc) |

Why the upset was not random: Aurora replaced its head coach, in-game leader and team language between 29 June and 8 July 2026 — kyxsan from Falcons as IGL, Jimpphat and coach ash in, MAJ3R/soulfly/Fabre out — per [HLTV's official transfer news](https://www.hltv.org/news/45082/official-aurora-complete-rebuild-with-kyxsan), while still carrying a top-six world ranking earned partly by the previous lineup. Current published lineup (XANTARES, woxic, Jimpphat, kyxsan, Wicadia; coach ash), HLTV #6 and VRS #5 were re-read from the [HLTV team page](https://www.hltv.org/team/11861/aurora) during the window. The seven review rules (rank lag, leadership churn, structural upsets, closing weakness, coin flips, symmetric rest, and the standing no-crowd-fade policy) are published with their evidence on the page.

Falcons' current five-player lineup was **not** verified inside the window; the page publishes Valve's dated official snapshot instead (karrigan, kyousuke, m0NESY, NiKo, TeSeS on 2026-10-05) and leaves the "current lineup" field blank. That gap weakens the 9z contrarian case and is published rather than smoothed over.

## Automatic operation: one publisher, every four hours

[`.github/workflows/pages.yml`](.github/workflows/pages.yml) runs on pushes to `main`, manual dispatch and at **00:17, 04:17, 08:17, 12:17, 16:17 and 20:17 UTC**. GitHub may delay scheduled jobs; this is not a real-time feed.

It restores the last verified snapshot from Actions cache, runs regression tests, discovers the full inventory, collects supported external evidence, **replays every row and calculation**, builds the dashboard and both clearly labeled historical archives, checks internal links/anchors/assets, and deploys one `site/` Pages artifact. A post-deploy check verifies the public HTML, full JSON, category pages, compatible old URLs and both archives. Production uses read-only source requests, not an account, API trading key or user action. Workflow permissions are `contents: read`, `actions: read`, `pages: write` and `id-token: write`. The job first waits for any platform legacy Pages build for the same commit, then attempts to configure Actions mode. If GitHub restricts that setting change, it records the actual mode and error on the review page and still publishes the verified artifact **after** the legacy publisher has finished. A running legacy publisher or unverifiable ordering blocks deployment, rather than risking a later stale overwrite.

- **Source failures do not manufacture fresh data.** Collection is staged and replayed before replacing last-good files. If inventory reconciliation fails after a partial download, old source evidence and analysis times remain intact; attempted responses get separate audit filenames. Retained coverage is marked unverified and clearly warned. Only a complete, replayed inventory is saved as the next cache fallback.
- **Unavailable picks do not block publication.** They are visibly unresolved. A broken build, inconsistent evidence or failed deployment does block it and must be fixed.
- **Staleness is explicit.** Inventory older than eight hours, failed inventory refreshes, expired quotes and past starts are visibly demoted. An open tab checks for newer snapshots without silently replacing the user’s current view. Malta/UTC/local timezone choices and actual observation dates are explicit.
- **No competing refresh writer.** The former six-hour `refresh.yml` is retired to a manual explanatory job; it no longer writes older datasets to `main` or deploys another artifact. Production snapshots are published with their evidence on Pages and cached, rather than growing Git history on each four-hour run.

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

**Verification:** 127 Python regression tests cover source contracts, exact identity, scoped alias joins, time/freshness, rejected markets, no-vig calculations, rating provenance, researched-fallback display rules, the dated edge-review contract and atomic source-failure handling, publication-mode restrictions and publisher ordering. 37 Playwright checks cover all six current pages at 320/390/768/1440px, one-tap phone navigation, search/filter/sort, every official row link, expandable evidence, timezone changes, stale behavior, no-JS content and axe WCAG A/AA checks at phone and desktop widths. Automated accessibility checks are not a claim of complete WCAG certification. The CI workflow independently installs the standard Playwright Chromium. In restricted local environments the test config uses npm-packaged Chromium and its bundled NSS libraries; it does not disable web security.

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
