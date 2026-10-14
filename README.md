# Spawn Scout — Hotspawn CS2 match intelligence

A mobile-first, source-linked GitHub Pages dashboard covering **every CS2 record returned by Hotspawn’s scheduled-fixture feed**, including academy and low-tier matches. Obvious picks and both teams’ calculated probabilities are shown only when supported by original external evidence; unresolved values remain blank.

**Live dashboard:** https://buffedlizard55-lab.github.io/MaltaProj3/

| View | What it contains |
| --- | --- |
| [Executive summary](https://buffedlizard55-lab.github.io/MaltaProj3/) | Coverage, direct links to the full picks list, upcoming matches and unresolved-pick limitations |
| [All match picks](https://buffedlizard55-lab.github.io/MaltaProj3/picks/) | Both probabilities, suggested team, method badge, searchable/filterable rows, source links and expandable evidence |
| [Coverage & original sources](https://buffedlizard55-lab.github.io/MaltaProj3/coverage/) | Inventory reconciliation, source health, complete past-start archive and JSON/CSV downloads |
| [Methodology](https://buffedlizard55-lab.github.io/MaltaProj3/methodology/) | Exact matching, formulas, thresholds, source policy and model limitations |
| [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/) | Missing inputs, failed source access, identity ambiguity, format/status conflicts and unresolved research trails |

The observation times and counts on the live site are authoritative for that published snapshot. For scale, the first fully replayed snapshot on **14 October 2026** contained **88 records: 28 future starts and 60 past-start records**, with **9 Polymarket estimates, 4 original bookmaker estimates, 8 Valve-model estimates and 7 unresolved future matches**. Past starts still labeled `scheduled` are retained as source anomalies, not invented results.

## Source and probability rules

1. **Complete inventory first.** Read both official [Hotspawn lobby](https://play.hotspawn.com/lobby) and [CS2 lobby](https://play.hotspawn.com/cs2-pickems) Angular hydration states, then reconcile their CS2 fixture IDs against the public fixture API used by Hotspawn’s client. No pagination was present in the inspected client. A changed schema, duplicate IDs or disagreement invalidates the completeness claim; it is not silently accepted as an empty or partial successful feed. New matches are rediscovered on every successful refresh.
2. **Never use Hotspawn “% picked.”** Community participation, offered points and crowd voting do not enter the calculations. Missing best-of formats, lineups and results are not inferred.
3. **Primary external market.** Discover candidates from [Polymarket’s CS2 directory](https://polymarket.com/esports/cs2), verify an active, unique prematch **full-series match-winner** event with exact normalized team names and start time within 60 seconds, then obtain both original CLOB order books. Validate token/condition IDs, positive bid/ask size, noncrossed books, spread ≤0.12 and observation freshness. Normalize the two bid/ask midpoints. Directory percentages, map markets, props and outrights are not inputs. These are market-implied estimates, not verified true win probabilities.
4. **Research only missing primary matches.** Attempt [HLTV](https://www.hltv.org/matches) context first, then original esportsbook lines. The public Thunderpick client uses a read-only **POST** `/api/matches` query with `{"gameIds":[6]}`; a failed GET does not establish that POST is unavailable. Require a unique exact fixture and prematch two-way series winner. Decimal odds are converted with `pᵢ = (1/oᵢ) / Σ(1/o)`. A single bookmaker is explicitly a single source, never described as consensus. Unsupported provider aliases stay unresolved.
5. **Explicit, higher-uncertainty model fallback.** Only after the primary, HLTV and bookmaker stages fail, use unique exact-name, five-player records from [Valve’s official regional standings repository](https://github.com/ValveSoftware/counter-strike_regional_standings). Reproduce the published Glicko expectation with fixed RD 75; use the latest applicable snapshot no older than 35 days. Raw official markdown and Git blob SHA are verified. This is an **uncalibrated research estimate**, not betting odds, and does not confirm today’s roster, stand-ins or veto. It never overrides a primary pick.
6. **Leave unsupported values blank.** Ambiguous names, stale/wide/one-sided markets, missing ratings or unavailable sources produce no fabricated probability or pick. Each such match remains in the list, unresolved section and review flags. Calculated fair decimal lines are illustrative reciprocals, not executable quotes.

Every row links an official Hotspawn source. Every estimate links the original market, bookmaker or Valve record. [Full public snapshot](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json), [request manifest](https://buffedlizard55-lab.github.io/MaltaProj3/data/sources.json), saved first-party JSON evidence, and [CSV](https://buffedlizard55-lab.github.io/MaltaProj3/data/picks.csv) allow manual review and calculation replay. POST request payloads, observation times and response hashes are recorded without credentials.

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

**Verification:** 48 Python regression tests cover source contracts, exact identity, time/freshness, rejected markets, no-vig calculations, rating provenance and atomic source-failure handling, publication-mode restrictions and publisher ordering. 22 Playwright checks cover all five current pages at 320/390/768/1440px, one-tap phone navigation, search/filter/sort, every official row link, expandable evidence, timezone changes, stale behavior, no-JS content and axe WCAG A/AA checks at phone and desktop widths. Automated accessibility checks are not a claim of complete WCAG certification. The CI workflow independently installs the standard Playwright Chromium. In restricted local environments the test config uses npm-packaged Chromium and its bundled NSS libraries; it does not disable web security.

## Preserved concurrent-session work

The original root and independent `docs/` dashboards used different observation times, matching rules and model weights. They are **not silently mixed into the current feed** or relabeled as freshly verified.

- [Original root-session archive](https://buffedlizard55-lab.github.io/MaltaProj3/archive/root-session/): original HTML, JS/CSS and datasets preserved in [`archive/root-session/`](archive/root-session/). The other session’s original `assets/app.js`, `assets/styles.css`, `data/matches.json`, `data/review.json` and maintenance scripts remain unchanged for provenance.
- [Independent docs-session archive](https://buffedlizard55-lab.github.io/MaltaProj3/docs/): source pages remain unchanged in [`docs/`](docs/), with `data/picks-model.json` and `scripts/build_site.py` preserved. It originally used 14 picks/14 unresolved and a 70/30 external-market/HLTV-points blend; those historical figures are not the current model.
- The production build adds unmistakable archive banners and current-feed links to the **artifact copies**, not the other sessions’ source HTML. The old `picks.html`, `methodology.html` and `flagged.html` URLs lead to current categorized pages.
- Claims, handoffs, source irregularities, checks, PR/merge/deployment records and publication-gap resolution are recorded in [`COORDINATION.md`](COORDINATION.md).

Independent informational analysis only. No bets or Hotspawn picks are placed. Estimates are not guarantees; 18+ where applicable.
