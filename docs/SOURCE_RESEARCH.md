# Source research log

Research date: 2026-10-14 UTC (updated 2026-10-22 UTC). Only public, unauthenticated source data is requested. No access-control or bot-challenge bypass is implemented.

## Initial findings (2026-10-14)

- Repository audit: only `README.md` existed at baseline. There was no pre-existing featured-pick algorithm, match data, or application to reuse.
- Match authority: <https://play.hotspawn.com/lobby> and the CS2-specific lobby <https://play.hotspawn.com/cs2-pickems>. Hotspawn pick percentages are community participation, **not** odds and are excluded from probability inputs.
- Hotspawn rules: <https://play.hotspawn.com/how-it-works> states that picks lock five minutes before scheduled start. The lobby/API must be checked for actual lock timestamps rather than assuming a rule.
- The human-readable lobby initially showed a larger filter count than the number of visible upcoming cards. Coverage verification must distinguish historical, locked, upcoming, and paginated records.
- External CS2 prediction-market directory: <https://polymarket.com/esports/cs2>. Public API and pagination documentation: <https://docs.polymarket.com/api-reference/events/list-events> and <https://docs.polymarket.com/market-data/discover-markets>. A quoted contract price is not an independent bookmaker quote; any normalized probability is labeled analysis.
- HLTV official match directory: <https://www.hltv.org/matches>. Team statistics/rankings can inform explicitly labeled model estimates, not verified bookmaker lines or verified win probabilities.
- Official esportsbook pages under investigation: <https://thunderpick.io/esports/counter-strike> and <https://www.pinnacle.com/en/esports-hub/cs2>. Availability, identity, market scope and paired prices must be verified before use.

## Hotspawn reverse engineering (2026-10-22)

### The inventory of record

- **Public scheduled-fixture API** (the same array Hotspawn's own client fetches):
  `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1`
  Returns an unpaginated JSON array of CS2 records with `id`, `participants*_name`, `competition_name`, `scheduled_start_time`, `lock_time`, `status`, `best_of`, `tier`, etc. Every record with `sport_alias=cs2` is kept. Duplicate `id` values or an empty array invalidates the refresh. No pagination was present in the inspected client (`scripts/sources.py:hotspawn`).
  Evidence per refresh: `data/evidence/hotspawn-fixtures.json` and reconciliation record `data/evidence/hotspawn-context.json`.

- **Rendered lobby hydration cross-check** — the two public pages embed the same fixture list in an Angular `ng-state` hydration block:
  * `https://play.hotspawn.com/lobby` (all games)
  * `https://play.hotspawn.com/cs2-pickems` (CS2-filtered)
  The collector reads that block from each page (`scripts/sources.py:fetch_fresh_page` + `hydration()`) and requires the same ID set as the API. A readable page that disagrees fails the refresh closed. When no rendered page can be read (observed HTTP 403 on both pages at 07:16Z on 17 Oct 2026 while the API answered 200 four hours earlier), the validated, duplicate-free API array is published with `inventory_crosscheck: "unavailable"` and a visible notice instead of a reconciliation claim (`scripts/build.py` coverage section). New matches are rediscovered on every successful refresh.

- **Lock rule verification:** `https://play.hotspawn.com/how-it-works` describes tier points and a lock 5 minutes before start. The dashboard respects **per-fixture explicit `lock_time`** from the API, not an assumed rule, and the browser re-checks lock/start before displaying "Pick" vs "Locked" (`assets/scout.js`).

- **Permalink per fixture:** `https://www.hotspawn.com/matches/<slug>-<id>` (e.g., MIBR vs BC.Game 1079440). Links are stored per `id` from the lobby/CS2 pages and reused as the primary Hotspawn source link per row.

### External probability inputs

- **Polymarket (primary):** directory `https://polymarket.com/esports/cs2` plus paginated official CS2-tag event API `https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2…` (bounded at 2,000 events). Only a unique prematch full-series match-winner event with exact normalized team names and start time within 60 s is used. Both original CLOB order books are validated (`bid/ask` size, noncrossed, spread ≤0.12) and the two bid/ask midpoints are normalized. Evidence: `data/evidence/polymarket-*.json`.
- **HLTV (identity & model only):** `https://www.hltv.org/matches` split-anchor cards are parsed with sibling time/team context; original HTML is saved and hash-checked. HLTV's betting-analytics page exposes only score-handicap prices and a fan vote, not a two-sided prematch moneyline, so HLTV is **not** used as an odds source. HLTV world ranking `https://www.hltv.org/ranking/teams` is used as a last-resort research model when at least one team appears on the same dated weekly ranking (≤14 days old); unranked side gets floor 0.0 with a low-confidence label.
- **Esportsbooks first-party:** Thunderpick `https://thunderpick.io/api/matches` POST `{"gameIds":[6]}`, Bovada coupon `https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2…`, Pinnacle guest board `https://guest.api.arcadia.pinnacle.com/0.1` (period 0, Yes/No & Odd/Even rejected). GG.BET / Rivalry / Stake are public-access checks that never fabricate prices. All require unique exact fixture + prematch two-way series winner; decimal odds are de-vigged with `pᵢ = (1/oᵢ)/Σ(1/o)`.
- **Relay & consensus:** bo3.gg `https://bo3.gg` second-hand `bet_updates` block is used only when no first-party line exists, never folded into a first-party consensus. Kalshi `https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXCS2GAME` is an exchange source with the same spread gating.
- **Valve official ratings:** `https://github.com/ValveSoftware/counter-strike_regional_standings` — latest snapshot ≤35 days old, exactly one complete five-player roster per team; Glicko expectation with fixed RD 75; raw markdown and Git blob SHA verified.
- **Network model (own line):** Bradley-Terry MAP over finished bo3.gg series (120-day window, anchored on Valve points) with fail-closed gates (graph size, anchor count, sample size, 1σ interval).

### Refresh cadence

- Primary: `17 */4 * * *` (00:17, 04:17, 08:17, 12:17, 16:17, 20:17 UTC)
- Catch-up: `47 2-22/4 * * *` (02:47, 06:47, …) so one dropped slot still leaves a refresh inside ~4 h.
- Workflow: `.github/workflows/pages.yml` — `collect` → `originate --live` → `coverage_probe` → `fbdc97d6_probe` → `build` → `verify_live` → `deploy` → `re-read after legacy window`. The legacy Pages build can overwrite with the checked-in 15-Oct root; `republish-last-verified` (isolated artifact `github-pages-interim`) restores the last verified snapshot in ~20 s.
- Browser freshness guard: `site/assets/scout.js` watches `data/latest.json` and shows a "newer snapshot available" reload prompt; after 8 h the stale banner appears.

## Verification rules

1. Every match row carries the original Hotspawn lobby/match URL and an observation timestamp.
2. Missing or ambiguous identities, match start times, series lengths or markets remain null and are flagged.
3. A paired, prematch series-winner market must align with both teams and the match date/time before deriving probabilities. Map, handicap, outright and total markets are excluded.
4. All model outputs are distinguished from verified source facts. No model is emitted without verified inputs; no arbitrary 50/50 replacement fills gaps.
5. A source failure never becomes an empty successful feed or a claim that no markets exist.

## Low-tier pick coverage (2026-10-22)

- Featured exact-name method alone resolves market/bookmaker picks for top-tier fixtures. Low-tier fixtures (e.g., CCT Europe, Elisa BreakOut, DFRAG, VRS academy) often have no Polymarket/Thunderpick entry because the exchange never listed them.
- Ladder then tries, **in order**, for each pick-less fixture: HLTV match-directory identity (to verify the fixture exists elsewhere), then original esportsbook lines, then aggregated reference, then Valve five-player rating model, then network line, then HLTV world-ranking model (with unranked-floor), then wide-book guidance. The first compliant price or model wins; no Hotspawn votes are used.
- Every active fixture in the 2026-10-15 checked-in snapshot (17/17) now carries a directional pick: 12 from external lines, 5 from research models, 0 unresolved. The 4 fixtures the featured method left blank are documented in `data/research/75aa5b56/pick-coverage.md` with the exact HLTV page, book probe, and reference/model that closed each row.
- Model-only rows are badged **Model**/**Researched**/**No betting line** (purple) and listed separately under **Picks without a betting line · limitations** in the executive summary, with the money sources that failed. No model-only row is described as a betting line.

## Environment/access limitations

Direct requests to Hotspawn, HLTV and Polymarket from the coding sandbox failed at TLS because outbound hosts are restricted. Source verification runs on GitHub Actions with ordinary public HTTP access. Web-retrieval tools were used to inspect the official lobby, HLTV match pages and Polymarket documentation independently. Source artifacts/Actions log downloads also use hosts unavailable to this sandbox, so temporary diagnostic evidence is exported to this session's fixed branch for review; it is not a new source of truth.

