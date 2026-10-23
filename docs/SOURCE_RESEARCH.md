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


## D866 — full coverage, picks for every match, mobile-first exec summary (2026-10-23)

### Live lobby reverse engineering (2026-10-23)

Fetched via fetch_page tool (allowed host, not via restricted python requests):

- **Lobby**: https://play.hotspawn.com/lobby
  - Header: "This week 197 matches this week" (all games), "Tier All tiers (92) B (40) C (52)" and later "93" with Chinggis Warriors added — count fluctuates as Hotspawn adds fixtures.
  - Closing Soon: fixtures with lock countdown (e.g., "Locking soon 00:01:49", "Locks in 03:01:49"), points (2 pts Tier C, 3 pts Tier B ×1.5), stage "Waiting For Information", multiplier ×1.25, "Sign in for streaks", View Match link to https://www.hotspawn.com/matches/{slug}-{id}, team logos from https://phpstack-1372681-6459848.cloudwaysapps.com/teams/{id}.svg, % picked (community, never used for probability — e.g., NEXVOID 76% vs Rare Atom 24%, FORZE Reload 97% vs LFO 10 3%).
  - Upcoming: similar with "Locks in 1d 3h 1m" etc.
  - Filters: Tier, Tournament (CCT Europe Challengers #4 (8), CCT South America Series #3 (8), DraculaN Season 7 (7), NODWIN Clutch Series #13 (6), Urban Riga Open #5 (12), VOID Autumn Cup (2), etc.), Team (list with counts: 6666 (3), Acend (4), FORZE Reload (2), etc.).
  - Leaderboard and prizes.

- **CS2 lobby**: https://play.hotspawn.com/cs2-pickems — same, CS2-only, 93 fixtures observed on 2026-10-23.

- **How we get full list**: the public scheduled-fixture API `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` is the same array Hotspawn's own client fetches. The collector in `scripts/sources.py:hotspawn()` reads both lobby pages' Angular `ng-state` hydration block (`id='ng-state'`) which contains the fixture array and `permalinks` dict mapping fixture_id → hotspawn.com match URL. It uses cache-busting `?cb=timestamp` to avoid CDN stale (X-Cache HIT Age 4000-5000s observed). It requires same ID set as API; disagreement fails closed. When both pages 403 (observed 2026-10-17T07:16Z), API-only mode publishes with `crosscheck: unavailable` instead of discarding usable inventory. New matches are rediscovered every 4h refresh.

- **Why counts differ**: lobby header says 68 matches this week but tier/tournament counts sum to 88 in old snapshot; live 197 total, 92-93 CS2. The discrepancy is because Hotspawn counts all games, not just CS2, and filters are dynamic. Our inventory uses the API array, not the header count, so we have full coverage of CS2 records returned by the API.

- **Lock times**: per-fixture explicit `lock_time` from API, not assumed 5-minute rule, and browser re-checks lock/start before displaying "Pick" vs "Locked" (`assets/scout.js`, `assets/glance-lock.js`).

### Picks for every match — ladder verified 2026-10-23

The ladder already resolves every active fixture in checked-in snapshot (17/17) and live snapshot 2026-10-22 (43 active, 42 picks, 0 unresolved, 1 even no-side). For 93 live fixtures, refresh will re-discover.

**Additional esportsbook sources probed for low-tier (this session + prior probes)**:

- GG.BET https://gg.bet/en/counter-strike — 403 Cloudflare → 200 flaky on re-run, no fixture/price found, flagged not relied. Prior probe 3016b0c6, 3a5448de.
- BetBoom https://betboom.ru/sport/cs2 — 401/403 blocked.
- Stake https://stake.com/sports/esports/cs2 — 403 blocked.
- BC.Game https://bc.game/sports/esports — 200 landing, no price.
- 1xBet https://1xbet.com/en/line/counter-strike-2 — 203/404.
- Marathonbet https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/ — 403.
- Betway https://www.betway.com/en/sports/esports/counter-strike-2 — 404.
- DraftKings https://sportsbook.draftkings.com/leagues/esports/counter-strike-2 — 200 landing, no price.
- OddsPortal https://www.oddsportal.com/esports/counter-strike/ — 200 landing, no structured price.
- EGamersWorld https://egamersworld.com/counterstrike/matches — 403 blocked.
- Pinnacle page https://www.pinnacle.com/en/esports/counter-strike-2 — 404, guest API used instead: https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups (16,201 matchups seen in prior probe, 0 target fixtures at that moment, but used when it does match).
- Rivalry https://www.rivalry.com/esports/counter-strike-betting — refused.
- Odds aggregators (OddsPapi, odds-api.io) — third-party, not first-party, not used as primary per policy. Documented for manual review: https://oddspapi.io/blog/esports-odds-api-guide-how-to-get-pinnacle-cs2-lol-data-for-free/ (median 86 books per CS2 fixture sampled Aug 2026, Pinnacle sharp, Polymarket tightest margin 0.99%).

**Why low-tier still needs model**: many academy/CCT Play-In/Elisa BreakOut fixtures never appear on any first-party bookmaker or exchange. No two-sided prematch price exists anywhere reachable. In those cases, Valve rating or HLTV ranking provides researched estimate with explicit limitation, never default 50/50.

### Mobile-first executive summary — improvements (D866)

- Viewport meta already present: width=device-width, initial-scale=1.
- New CSS in assets/scout.css (D866 block):
  - glance-row border-left 4px color-coded (green #b5d5c5 for market/bookmaker/consensus, purple #d9c8f0 for model, orange default), hover orange, pick team highlighted with #fff6ef background + bold orange-dark.
  - glance-prob 14px bold with background, glance-other 11px with muted background, both larger on phone.
  - exec-banner override: label/desc/meta now visible on phone (previously hidden to keep above fold), sub visible, 48px tap targets.
  - start-here jump bar: on phone, grid 1 column, descriptions visible, first card full-width orange (Picks on this page), 48-56px tap targets, no horizontal overflow (main overflow-x hidden).
  - mobile-status shortcuts: 56px min-height, 12px padding, border-radius 12px, box-shadow, orange for picks, amber for unresolved.
  - tables: on phone, rows as cards with border-radius 12px, box-shadow, overflow-x auto touch.

- Executive summary now contains:
  - exec-banner: "Executive summary — start here on your phone", "Every Hotspawn CS2 pick, one tap away", description, 3 actions (Updated picks — all matches with count, Featured picks feed, Unresolved & limitations with counts), meta with inventory time, snapshot, refresh cadence, links to coverage, methodology, picks at a glance, research trails.
  - start-here: 5 links (Picks on this page, All match picks, Leaderboard plan, Unresolved, Blanks in this summary) with icons, descriptions visible on phone.
  - picks-at-a-glance: phone-first index of every active fixture with both win probabilities, pick, method badge, source links, Find a pick search (sticky on phone, 48px input, live count, empty-state).
  - low-tier-coverage section: new, explains HLTV → esportsbooks → Valve → own models → HLTV ranking ladder, with official links, and notes unresolved handling.
  - unresolved-register: canonical register with title, counts, per-fixture blocker.
  - no-line-register: picks without betting line, with why no line exists.
  - hero: "All the matches. One clear view." with counts and buttons.
  - briefing-links: shortcuts to full picks, leaderboard, final day review, next matches, contrarian, upset review, Day 5, market-backed alternatives, unresolved.
  - site-map: table of every page and what it contains, one tap from here.

- Verification: build passes 646 rows audited (627 official-source-linked, 9 flagged unverified, 10 site-map, 0 without source), 798 internal links OK, 9 views.

### Unresolved picks & limitations — separate section

- Every active fixture without a pick is listed in `/unresolved/` with exact blocker, every source tried, dated reachability matrix, order resolver works through.
- Executive summary contains `#unresolved-register` (featured-method gaps before fallback) and `#no-line-register` (model-only picks without betting line, with why).
- Each unresolved row in complete_picks (origination.json) has `research` array with stage, source_url, status, detail, observed_at.

### Refresh every 4-8 hours

- Workflow `.github/workflows/pages.yml` already runs every 4h (cron 17 */4 * * *) plus catch-up 47 2-22/4 * * *. Verified in repo.
- Browser freshness guard shows "Snapshot needs attention" after 8h and "newer snapshot available" reload prompt.

### Sources — official verified trusted

- Hotspawn lobby: https://play.hotspawn.com/lobby
- CS2 lobby: https://play.hotspawn.com/cs2-pickems
- Fixtures API: https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1
- How it works: https://play.hotspawn.com/how-it-works
- Polymarket CS2: https://polymarket.com/esports/cs2
- Polymarket Gamma: https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2&active=true&closed=false&limit=100&offset=0
- Polymarket CLOB: https://clob.polymarket.com/book?token_id=
- Polymarket docs: https://docs.polymarket.com/api-reference/events/list-events
- HLTV matches: https://www.hltv.org/matches
- HLTV ranking: https://www.hltv.org/ranking/teams and https://www.hltv.org/ranking/teams/2026/october/12
- Thunderpick API: https://thunderpick.io/api/matches
- Thunderpick page: https://thunderpick.io/esports/counter-strike
- Valve standings repo: https://github.com/ValveSoftware/counter-strike_regional_standings
- bo3.gg API: https://api.bo3.gg/api/v1 and https://bo3.gg/matches/
- Kalshi events: https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXCS2GAME
- Kalshi docs: https://docs.kalshi.com/api-reference/market/get-markets
- Bovada coupon: https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2?marketFilterId=def&preMatchOnly=true&lang=en
- Pinnacle guest: https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups
- Pinnacle esports hub: https://www.pinnacle.com/en/esports-hub/cs2
- Pinnacle API: https://www.pinnacle.com/en/api
- Odds aggregator reference (manual review, not primary): https://oddspapi.io/blog/esports-odds-api-guide-how-to-get-pinnacle-cs2-lol-data-for-free/

