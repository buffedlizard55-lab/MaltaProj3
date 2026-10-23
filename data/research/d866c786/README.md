# D866 — full coverage, picks for every match, mobile-first exec summary

Date: 2026-10-23 UTC
Branch: arena/d866c786-maltaproj3

## Goal

User brief: generate picks for every Hotspawn CS2 match, including low-tier/academy matches not covered on Polymarket. Look for information sources to guide pick selections only for matches that cannot be resolved in same way as featured picks. Try HLTV, then esportsbooks and betting lines. Create separate section for unresolved picks and limitations, include in executive summary. Site must be mobile-friendly, easy to find picks, probabilities obvious. Reverse engineer https://play.hotspawn.com/lobby so we have full list updated every 4-8 hours.

## Live lobby reverse engineering (2026-10-23)

Fetched via fetch_page tool (allowed host):
- URL: https://play.hotspawn.com/lobby
- Title: Pick'ems Lobby | Hotspawn Play
- Observed: 197 matches this week (all games), CS2 filter 92-93 fixtures (text says "Tier All tiers (92) B (40) C (52)" and later 93 with Chinggis Warriors). The count fluctuates as Hotspawn adds fixtures.
- Structure:
  - Closing Soon: list of fixtures with lock countdown, points (2 pts Tier C, 3 pts Tier B ×1.5), stage "Waiting For Information", multiplier ×1.25, View Match link to https://www.hotspawn.com/matches/{slug}-{id}, team logos from https://phpstack-1372681-6459848.cloudwaysapps.com/teams/{id}.svg, % picked (community, never used for probability).
  - Upcoming: similar, with locks in days/hours.
  - Filters: Tier (All/B/C), Tournament (list of tournaments with counts), Team (list of teams with counts).
  - Leaderboard and prizes.

- CS2 lobby: https://play.hotspawn.com/cs2-pickems — same structure, CS2-only, 93 fixtures observed.

- Inventory of record: public scheduled-fixture API `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` returns unpaginated JSON array. Each record: id, participants*_id, participants*_name, competition_name, competition_id, scheduled_start_time, lock_time, status, best_of, tier, lock_offset_sec, etc. Duplicate id or empty array invalidates refresh.

- Rendered lobby hydration cross-check: Angular ng-state script id='ng-state' contains fixture array and permalinks dict (fixture_id → https://www.hotspawn.com/matches/...). Collector reads both lobby and CS2 lobby with cache-busting ?cb=timestamp to avoid CDN stale (X-Cache HIT Age 4000-5000s observed). Requires same ID set as API; disagreement fails closed. When both pages 403 (observed 2026-10-17T07:16Z), API-only mode publishes with crosscheck: unavailable.

- Permalink: https://www.hotspawn.com/matches/{slug}-{id} — primary Hotspawn source link per row.

- Refresh cadence: pages.yml cron '17 */4 * * *' and catch-up '47 2-22/4 * * *' — every 4h, 2.5h catch-up keeps inside 8h stale bound. Workflow: collect → originate --live → coverage_probe → build → verify_live → deploy → re-read after legacy window. Browser freshness guard in scout.js watches data/latest.json.

## Picks for every match — ladder

Existing ladder (verified):

1. **Polymarket** — directory + Gamma paginated CS2-tag API, exact-name + 60s start tolerance, both CLOB order books validated (spread ≤0.12, noncrossed, positive size, freshness ≤8h), normalized midpoints. Source: https://polymarket.com/esports/cs2, https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2, https://clob.polymarket.com/book?token_id=

2. **Thunderpick** — POST https://thunderpick.io/api/matches {"gameIds":[6]}, prematch two-way series winner, exact team/time, decimal odds de-vigged pᵢ=(1/oᵢ)/Σ(1/o). Evidence: data/evidence/thunderpick-matches.json

3. **Kalshi** — CFTC-regulated exchange, https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXCS2GAME&status=open&with_nested_markets=true, both yes books two-sided ≤0.15, thin >0.12 flagged. Docs: https://docs.kalshi.com/api-reference/market/get-markets

4. **Bovada** — public coupon https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2?marketFilterId=def&preMatchOnly=true&lang=en, margin removed proportionally.

5. **Pinnacle guest** — https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups + /leagues/{id}/markets/straight, period-0 series moneylines only, Yes/No & Odd/Even rejected. Source: https://www.pinnacle.com/en/esports-hub/cs2

6. **bo3.gg relay** — https://api.bo3.gg/api/v1 second-hand bet_updates block, used only when no first-party line, never folded into consensus, start tolerance 60s, exact-name or reviewed-alias join. Source: https://bo3.gg/matches/{slug}

7. **Valve regional standings** — https://github.com/ValveSoftware/counter-strike_regional_standings, latest ≤35 days, exactly one complete five-player roster per team, Glicko expectation with RD 75: p=1/(1+10**((pts_b-pts_a)/400)), raw markdown + blob SHA verified.

8. **Own network model** — Bradley-Terry MAP over finished bo3.gg series (120-day window, anchored on Valve points), fail-closed gates (graph size, anchor count, sample size, 1σ interval). Source: https://bo3.gg/matches + Valve table.

9. **Form model** — results-based estimate when one team has no complete five-player row in Valve table, rating fitted to finished series against officially rated opponents (bo3.gg). Source: https://bo3.gg/matches + Valve.

10. **HLTV world ranking** — https://www.hltv.org/ranking/teams, official weekly ranking, ≤14 days old, same dated publication required for both sides, points logistic transform same 400-scale, unranked side floor 0.0 with low-confidence label. Source: https://www.hltv.org/ranking/teams/2026/october/12 (example, 972 points for Spirit #1). Evidence saved as data/origination/evidence/live-hltv-ranking.json.

**Result**: checked-in snapshot 2026-10-15: 17 active, 17 with directional pick (12 external line, 5 research model, 0 unresolved). Featured method alone left 4 blank; fallback resolved them. Live snapshot 2026-10-22: 43 active, 42 picks, 0 unresolved in complete list, 1 even no-side (Isurus–Hacha). Live lobby 2026-10-23: 92-93 fixtures — refresh will re-discover.

**Additional esportsbook sources researched for low-tier (this session)**:

- GG.BET https://gg.bet/en/counter-strike — public esportsbook, Cloudflare challenge, no structured price extracted without bypass (status 403→200 flaky, no fixture/price found, flagged not relied). [Source: prior probe 3016b0c6, 3a5448de]
- BetBoom https://betboom.ru/sport/cs2 — 401/403, blocked.
- Stake https://stake.com/sports/esports/cs2 — 403, blocked.
- BC.Game https://bc.game/sports/esports — 200 landing page, no target fixture price.
- 1xBet https://1xbet.com/en/line/counter-strike-2 — 203/404, blocked.
- Marathonbet https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/ — 403.
- Betway https://www.betway.com/en/sports/esports/counter-strike-2 — 404.
- DraftKings https://sportsbook.draftkings.com/leagues/esports/counter-strike-2 — 200 landing, no price.
- OddsPortal https://www.oddsportal.com/esports/counter-strike/ — 200 landing, no structured price.
- EGamersWorld https://egamersworld.com/counterstrike/matches — 403, blocked.
- Pinnacle page https://www.pinnacle.com/en/esports/counter-strike-2 — 404, guest API used instead.
- Rivalry https://www.rivalry.com/esports/counter-strike-betting — refused.
- Bovada already wired, Thunderpick already wired.
- Odds API aggregators (OddsPapi, odds-api.io) — third-party, not first-party, not used as primary source per policy (must be original bookmaker price, not aggregated). Documented for manual review: https://oddspapi.io/blog/esports-odds-api-guide-how-to-get-pinnacle-cs2-lol-data-for-free/ (Pinnacle sharp, Polymarket tightest margin, median 86 books per CS2 fixture sampled Aug 2026).

**Why low-tier still needs model**: many academy/CCT Play-In/Elisa BreakOut fixtures never appear on any first-party bookmaker or exchange (e.g., 6666 vs ex-6666, Phantom Academy vs Banda chuya). No two-sided prematch price exists anywhere reachable. In those cases, Valve rating or HLTV ranking provides a researched estimate with explicit limitation, never a default 50/50.

## Unresolved picks & limitations — separate section

- Every active fixture without a pick is listed in `/unresolved/` with exact blocker, every source tried, dated reachability matrix, order resolver works through.
- Executive summary contains:
  - `#picks-at-a-glance` — phone-first index of every active fixture with both win probabilities, pick, method badge, source link.
  - `#unresolved-register` — featured-method gaps before research fallback, with missing evidence per row.
  - `#no-line-register` — picks without a betting line (model-only), with why no line exists (book too wide, ambiguous rating, no rating, no external line) and sources that failed.
  - `exec-banner` — start-here banner with internal links to updated picks, featured feed, unresolved & limitations, all ≥44px tap targets, verified by link audit.
  - `start-here` jump bar — one place on phone that says where picks are, with Picks on this page (full-width orange), All match picks, Leaderboard plan, Unresolved, Blanks in this summary.

## Mobile friendliness

- Viewport meta: width=device-width, initial-scale=1 (in index.html).
- CSS media queries: 1600px, 1200px, 1000px, 850px, 700px, 375px, 450px.
- Mobile nav: fixed bottom nav with 6 items (Summary, Picks, Unresolved, Edge, Sources, Review), ≥44px min-height, scrollable, backdrop blur.
- Glance list: grid, border-left 4px color-coded (green for market/bookmaker/consensus, purple for model, orange default), hover/focus border orange, pick team highlighted with background #fff6ef + border #f0dcc8 + bold orange-dark, probabilities larger (14px bold) with background, other team muted with background.
- Find-a-pick search: sticky on ≤700px, 48px input, live count, empty-state.
- Tables: on ≤700px, thead hidden, rows block, cards with border-radius 12px, box-shadow, no horizontal overflow, -webkit-overflow-scrolling touch.
- Tap targets: filter tabs 44px, timezone select 40px, row-details summary 44px, source links 28px min-height, briefing links 44px.
- No horizontal overflow: main overflow-x hidden, content-section overflow hidden, table-scroll overflow-x auto.

## Verification

- Build: `python -m scripts.build` — PASS 80 source rows reconciled, 646 rows audited (627 official-source-linked, 9 flagged unverified, 10 site-map, 0 without source), 792 internal links OK, 9 views.
- Every table row must have source link to official site (Hotspawn + line provider or Valve/HLTV). If value can't be confirmed, leave blank and flag as unverified — never infer.
- Row-source audit: data/row-source-audit.json (generated by build) checks every row has official link.
- Link audit: checks 792 internal links/assets/anchors.

## Sources used — official verified

- Hotspawn lobby: https://play.hotspawn.com/lobby
- CS2 lobby: https://play.hotspawn.com/cs2-pickems
- Fixtures API: https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1
- How it works: https://play.hotspawn.com/how-it-works
- Polymarket CS2 directory: https://polymarket.com/esports/cs2
- Polymarket Gamma API: https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2&active=true&closed=false&limit=100&offset=0
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
- Pinnacle API docs: https://www.pinnacle.com/en/api
- Odds aggregator reference (manual review, not used as primary): https://oddspapi.io/blog/esports-odds-api-guide-how-to-get-pinnacle-cs2-lol-data-for-free/

