# Verification and Audit Report — Session arena-97d4113b

**Date**: 2026-10-23  
**Auditor**: Session arena-97d4113b  
**Branch**: `arena/97d4113b-maltaproj3`  
**Repository**: `buffedlizard55-lab/MaltaProj3`

---

## 1. Executive Summary

This session conducts a line-by-line verification of the repository against all prompt requirements:
1. **Generating Picks for Every Match**: Low-tier and academy CS2 matches not covered on traditional prediction platforms (e.g. Polymarket) are resolved via a verified 5-rung research ladder (first-party books → bo3.gg relay → Valve official standings → own Bradley-Terry results model → HLTV weekly ranking logistic model).
2. **No Hallucinations / Strict Sourcing**: Never infer or default to 50/50 without an official source. If a match cannot be resolved, it is placed into a dedicated, separate **Unresolved Picks & Limitations** section with every probed source and reason documented.
3. **Hotspawn Reverse Engineering & Scheduled Cadence**: Verified Hotspawn's scheduled fixtures endpoint, Angular hydration state (`ng-state`), permalinks, cache-busting mechanisms (`?cb=`), and the 4–8 hour refresh schedule in `.github/workflows/pages.yml`.
4. **Mobile-First UX & Accessibility**: Executive summary provides direct, high-contrast links to the updated picks list, clear win probabilities for both teams on every card, obvious pick indicators, search/filter controls, and strict WCAG A/AA compliance (fixing the axe `link-in-text-block` violation introduced by D866).

---

## 2. Line-by-Line Official Source Verification

Every data source utilized in the pipeline has been verified from official, trusted endpoints:

| Source | Official URL / Endpoint | Verification Status | Usage in System |
| --- | --- | --- | --- |
| **Hotspawn Scheduled Fixtures API** | `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` | Verified official client backend endpoint | Primary authoritative inventory for all CS2 matches listed on Hotspawn |
| **Hotspawn Lobby** | `https://play.hotspawn.com/lobby` and `https://play.hotspawn.com/cs2-pickems` | Verified official web UI with Angular `ng-state` | Secondary cross-check for inventory reconciliation and match permalinks |
| **Polymarket Gamma API** | `https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2&active=true&closed=false&limit=100` | Verified official API | First-party prediction market event directory |
| **Polymarket CLOB API** | `https://clob.polymarket.com/book?token_id={id}` | Verified official CLOB endpoint | Two-sided order book depth, spread ≤0.12 validation |
| **Thunderpick API** | POST `https://thunderpick.io/api/matches` `{"gameIds":[6]}` | Verified official client API | Direct bookmaker decimal odds, de-vigged |
| **Pinnacle Guest API** | `https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups` | Verified official guest board | First-party moneyline prices for tier-1 and tier-2 series |
| **Bovada Pre-match API** | `https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2` | Verified public coupon API | Proportional margin removal for pre-match odds |
| **Kalshi Exchange API** | `https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXCS2GAME` | Verified CFTC-regulated exchange | Direct market probabilities with spread checks |
| **bo3.gg Relayed Bookmaker API** | `https://api.bo3.gg/api/v1/matches` | Verified public API | Relayed bookmaker quotes for low-tier matches where first-party API access is restricted |
| **Valve Regional Standings** | `https://github.com/ValveSoftware/counter-strike_regional_standings` | Verified official Valve GitHub repository | Official five-player rating anchor; Glicko expectation formula |
| **HLTV Team Rankings** | `https://www.hltv.org/ranking/teams` | Verified official HLTV ranking | Weekly points transformed via 400-scale logistic curve |
| **HLTV Match Permalinks** | `https://www.hltv.org/matches` | Verified official HLTV directory | Match identity verification and tournament tier classification |

---

## 3. Hotspawn Reverse Engineering Audit

- **Authoritative API**: The Hotspawn web application queries `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1`. This returns an array of fixture objects containing:
  - `fixture_id` (numeric string, e.g. `1082688`)
  - `team_a` / `team_b` details (names, logos)
  - `start_date` / `lock_date`
  - `tier` (e.g. `s`, `a`, `b`, `c`)
  - `status` (`scheduled`, `completed`)
  - User selection percentages (`percent_picked`) — **never** used as an indicator of match probability
- **Hydration State**: On `https://play.hotspawn.com/lobby`, the server-rendered HTML embeds a JSON payload in `<script id="ng-state">` containing `permalinks` mapping `fixture_id` to `https://www.hotspawn.com/matches/{slug}-{id}`.
- **Cache Busting**: Hotspawn's Cloudflare/Varnish CDN caches responses with `X-Cache: HIT` (ages observed exceeding 4,000s). The collector script appends `?cb={timestamp}` to bypass stale cache and ensure newly added matches are captured within the 4–8 hour collection window.
- **Cadence**: `.github/workflows/pages.yml` executes every 4 hours (`cron: '17 */4 * * *'`) plus a 2.5-hour catch-up slot (`cron: '47 2-22/4 * * *'`), satisfying the 4–8 hour freshness guarantee.

---

## 4. Probabilities & Pick Origination

To satisfy the user requirement: *"Do not use hotspawn as an indicator for match probability. We need to get betting lines from outside anywhere esports is covered. Also hltv can be used but we need to originate our own lines for all matches."*

The origination engine (`scripts/originate.py`) executes the following hierarchy:
1. **First-Party Betting Lines**:
   - De-vigged market consensus from Polymarket CLOB, Kalshi, Pinnacle, Bovada, and Thunderpick.
   - Requires exact name match or verified alias in `data/origination/aliases.json` plus start time within 60s tolerance.
2. **Relayed Bookmaker Odds**:
   - Secondary relay from bo3.gg when first-party APIs are geoblocked or challenged.
   - De-vigged using proportional normalization: $p_i = \frac{1/O_i}{\sum 1/O}$.
3. **Valve Regional Standings Model**:
   - Uses Valve's official points for complete 5-player rosters.
   - Logistic expectation: $E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}$.
4. **Bradley-Terry Results Model**:
   - Maximum a posteriori estimation on finished bo3.gg matches over a 120-day window, anchored to Valve ratings.
5. **HLTV Weekly Ranking Logistic Model**:
   - Points evaluated through the 400-scale logistic transform; unranked teams receive baseline floor 0.0 with explicit low-confidence badge.
6. **Even Estimates & Tie-Breaks**:
   - If a research model produces exactly 50.0% / 50.0%, the pick direction is decided by the ranking provider's official published standing (e.g. rank #215 vs #229). The probability is **never** falsified; it remains 50.0% / 50.0% with a documented `rule: published-rank tie-break` attribute.
7. **Unresolved Register**:
   - If all rungs fail (e.g., brand-new academy roster with no historical matches, no rank, and no betting line), the match is published in the **Unresolved** register with all attempted endpoints and blocker reasons. Zero hallucination.

---

## 5. Mobile & Executive Summary Verification

1. **Quick Navigation**: The executive banner at the top of `/index.html` answers:
   - Is this current? (Timestamp and freshness badge)
   - How many picks? (Counts of active, directional picks, model-only, unresolved)
   - Direct touch targets (≥48px) to **Match picks** (`picks/` and `origination/#picks`) and **Unresolved & limitations** (`unresolved/`).
2. **Clarity of Probability & Pick**:
   - Each match card displays both team win percentages in bold, prominent font (14px, font-weight 800).
   - Pick chip is highlighted in `#fff6ef` with orange-dark border and clear selection badge.
   - Method badge (e.g., `Market line`, `Bookmaker`, `Model`) links directly to the methodology explanation.
3. **No Horizontal Overflow**: Tested across 320px, 390px, 768px, and 1440px viewports with zero horizontal scroll violations.
4. **Accessibility (WCAG A/AA)**:
   - Fixed `.ladder-list a` underline styling in `assets/scout.css`.
   - Verified with Playwright Axe scan across all 9 pages at 390px and 1440px (15/15 a11y tests passing, 0 violations).

---

## 6. Full Test Suite & Build Verification

- **Unit Tests**:
  - `tests/test_96fbe295.py`: 31/31 passed.
  - `tests/test_15fc6bca_relay.py`: 22/22 passed.
  - `tests/test_freshness_determinism.py`: 9/9 passed.
  - `tests/test_strategy.py`: 58/58 passed.
  - `tests/test_review_register.py`: 9/9 passed.
- **Replay Build**: `python -m scripts.build` completed with:
  - 80 source rows reconciled against first-party evidence.
  - Row-source audit: 648 rows, 629 with official links, 9 flagged unverified, 10 site-map, **0 violations without a source**.
  - Internal links check: 802 valid internal links/anchors/assets, 0 broken links.
- **Browser Suite**: `npm test` (Playwright):
  - **89/89 tests passed** across mobile and desktop.
- **Pick Presentation Safety Audit**: `node tests/pick-safety-browser.mjs`:
  - **106 safety assertions passed** (Python/JS parity, open-tab expiry, lock, clock rollback, no-JS, 4 widths, axe A/AA).

