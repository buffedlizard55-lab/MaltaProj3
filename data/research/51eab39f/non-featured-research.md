# Session `arena-51eab39f` — HLTV-First & Esportsbook Research for Non-Featured Matches (`2026-10-26T01:30:00Z`)

External fallback research was executed strictly for the **13** open Hotspawn CS2 matches not resolved by the exact-name featured Polymarket path, following the required priority order: **HLTV first**, then **external exchanges and esportsbooks** (`Polymarket CLOB`, `Kalshi KXCS2GAME`, `Smarkets v3 csgo_match`, `Thunderpick`, `Bovada`), and finally **official Valve VRS (`2026-10-05`) / `bo3.gg` series-form** where no valid two-sided moneyline existed. Hotspawn crowd pick percentages were never used.

## `1082859` — NEXVOID vs Alter Ego (DFRAG Invitational 2026, `2026-10-26T03:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026](https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026) — HLTV match 2399889 confirms BO3 Group A Opening Match at 2026-10-26T03:00:00Z (DFRAG Invitational 2026).
- **Published pick**: **NEXVOID** (`59.16%` / `40.84%` via `bookmaker` — Thunderpick)
- **External lines & models checked**:
  - **Polymarket CLOB** (`rejected`): Order book spread exceeded the 0.15 fallback ceiling at snapshot time. ([source](https://gamma-api.polymarket.com/events?tag_slug=cs2&active=true&closed=false&limit=100))
  - **Thunderpick** (`accepted_primary`): Pre-match two-way match-winner decimal odds 1.56 / 2.26 (sum implied 1.0835, within 0.85..1.35). ([source](https://thunderpick.io/esports/cs2/dfrag-invitational-2026/nexvoid-vs-alter-ego-2870940))
  - **Kalshi KXCS2GAME** (`corroborating_exchange`): KXCS2GAME-26OCT252300AENEX quotes Alter Ego NO bid/ask 0.55/0.57 (implied NEXVOID 0.56), directionally matching Thunderpick. ([source](https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXCS2GAME&status=open&with_nested_markets=true&limit=200))

## `1079201` — INOX Division vs Nemesis (NODWIN Clutch Series #13, `2026-10-26T09:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399116/nemesis-vs-inox-division-nodwin-clutch-series-13](https://www.hltv.org/matches/2399116/nemesis-vs-inox-division-nodwin-clutch-series-13) — HLTV match 2399116 confirms BO3 Quarter-final #1 at 2026-10-26T09:00:00Z (NODWIN Clutch Series 13).
- **Published pick**: **Nemesis** (`12.35%` / `87.65%` via `model` — Valve official standings)
- **External lines & models checked**:
  - **Smarkets Exchange** (`corroborating_unjoined_alias`): Event 45401462 lists Team Nemesis vs INOX Division at 2026-10-26T09:00:00Z; two-sided book 0.6494/0.7752 vs 0.2273/0.3425 (spread 0.1258 <= 0.15) implies 71.43% Team Nemesis / 28.57% INOX Division; unjoined at 01:04:30Z because Team Nemesis -> Nemesis was not yet scoped to NODWIN Clutch Series #13. ([source](https://api.smarkets.com/v3/markets/173680174/quotes/))
  - **Bovada** (`corroborating_unjoined_alias`): Event 32756569 Moneyline quotes Team Nemesis 1.363636 (-275) vs INOX Division 3.00 (+200), implying 68.75% Nemesis / 31.25% INOX Division. ([source](https://www.bovada.lv/esports/counter-strike-2/nodwin-clutch-series/team-nemesis-inox-division-202610260500))
  - **Valve official standings** (`accepted_primary`): INOX Division (#82, 1105 pts) vs Nemesis (#29, 1455 pts) on 2026-10-05 global table -> 12.35% / 87.65% Nemesis. ([source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md))

## `1079202` — FOKUS vs ex-Zero Tenacity (NODWIN Clutch Series #13, `2026-10-26T12:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399117/fokus-vs-ex-zero-tenacity-nodwin-clutch-series-13](https://www.hltv.org/matches/2399117/fokus-vs-ex-zero-tenacity-nodwin-clutch-series-13) — HLTV match 2399117 confirms BO3 Quarter-final #2 at 2026-10-26T12:00:00Z (NODWIN Clutch Series 13).
- **Published pick**: **FOKUS** (`68.24%` / `31.76%` via `bookmaker` — Thunderpick)
- **External lines & models checked**:
  - **Smarkets Exchange** (`rejected_schedule_mismatch`): Smarkets event 45401463 lists start_datetime 2026-10-26T18:00:00Z (+6h vs HLTV/Hotspawn 12:00:00Z); rejected by 60s start-time tolerance. ([source](https://smarkets.com/event/45401463/sport/esports/cs-go/nodwin-clutch-series/playoffs/2026/10/26/18-00/fokus-vs-ex-zero-tenacity))
  - **Thunderpick** (`accepted_primary`): Two-way pre-match match-winner odds 1.35 / 2.90 -> 68.24% FOKUS / 31.76% ex-Zero Tenacity. ([source](https://thunderpick.io/esports/cs2/nodwin-clutch-series-13/fokus-vs-ex-zero-tenacity-2888795))
  - **Bovada** (`corroborating_bookmaker`): Event 32770566 lists FokuS Esports 1.363636 (-275) vs Ex-Zero Tenacity 3.00 (+200) -> 68.75% FOKUS. ([source](https://www.bovada.lv/esports/counter-strike-2/nodwin-clutch-series/fokus-esports-ex-zero-tenacity-202610260800))

## `1081159` — LFO 10 vs ex-6666 (CCT Europe 2026 Series #12, `2026-10-26T12:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12](https://www.hltv.org/matches/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12) — HLTV match 2399509 confirms BO3 Swiss Round 4 (1-2) at 2026-10-26T12:00:00Z; LFO 10 (#14084: Sapec, L00m1, dottie, flaw, Mann3n) vs ex-6666 (#14100: skcH, kL1o, amster, rendysky, stefienson — 4/5 core of Valve #126 6666).
- **Published pick**: **ex-6666** (`39.04%` / `60.96%` via `model` — Own results-based model (bo3.gg series results))
- **External lines & models checked**:
  - **Polymarket CLOB** (`rejected_wide_spread`): Market #1255951 spread 0.53 > 0.15 fallback ceiling. ([source](https://polymarket.com/event/cs2-skr-6666-2026-10-26))
  - **Kalshi KXCS2GAME** (`rejected_wide_spread`): KXCS2GAME-26OCT260800EXSKR spread 0.56 > 0.15 fallback ceiling. ([source](https://kalshi.com/markets/kxcs2game/counterstrike-2-game/kxcs2game-26oct260800exskr))
  - **Own results-based model (bo3.gg series results)** (`accepted_primary_low_confidence`): LFO 10 (Sokerorg) has no published 5-player Valve row; MAP fit over n=10 anchored BO series yields 825 pts (posterior SD 114.7) vs ex-6666 Valve 923 pts -> 39.04% / 60.96% ex-6666 (1-SD interval [0.2586, 0.5382] crosses 50%). ([source](https://bo3.gg/matches/sokerorg-vs-ex-6666-26-10-2026))

## `1079203` — Metizport vs BRUTE (NODWIN Clutch Series #13, `2026-10-26T15:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399118/metizport-vs-brute-nodwin-clutch-series-13](https://www.hltv.org/matches/2399118/metizport-vs-brute-nodwin-clutch-series-13) — HLTV match 2399118 confirms BO3 Quarter-final #3 at 2026-10-26T15:00:00Z (NODWIN Clutch Series 13).
- **Published pick**: **Metizport** (`61.54%` / `38.46%` via `bookmaker` — Thunderpick)
- **External lines & models checked**:
  - **Smarkets Exchange** (`rejected_schedule_mismatch`): Smarkets event 45402088 lists start_datetime 2026-10-26T12:00:00Z (-3h vs HLTV/Hotspawn 15:00:00Z); rejected by 60s start-time tolerance. ([source](https://smarkets.com/event/45402088/sport/esports/cs-go/nodwin-clutch-series/playoffs/2026/10/26/12-00/metizport-vs-brute))
  - **Thunderpick** (`accepted_primary`): Two-way pre-match match-winner odds 1.50 / 2.40 -> 61.54% Metizport / 38.46% BRUTE. ([source](https://thunderpick.io/esports/cs2/nodwin-clutch-series-13/metizport-vs-brute-2889134))
  - **Bovada** (`corroborating_bookmaker`): Event 32773971 Moneyline quotes Metizport 1.571429 (-175) vs Brute 2.350 (+135), opened after 01:04:30Z capture (lastModified 2026-10-26T00:46Z/coupon refresh), corroborating Metizport. ([source](https://www.bovada.lv/esports/counter-strike-2/nodwin-clutch-series/metizport-brute-202610261100))

## `1081160` — HAVU vs ILLYRIANS (CCT Europe 2026 Series #12, `2026-10-26T15:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399510/havu-vs-illyrians-cct-2026-europe-series-12](https://www.hltv.org/matches/2399510/havu-vs-illyrians-cct-2026-europe-series-12) — HLTV match 2399510 confirms BO3 Swiss Round 4 (1-2) at 2026-10-26T15:00:00Z (CCT 2026 Europe Series 12).
- **Published pick**: **HAVU** (`60.35%` / `39.65%` via `model` — Valve official standings)
- **External lines & models checked**:
  - **Polymarket CLOB** (`rejected_wide_spread`): Two-sided order-book spread exceeded 0.15 ceiling; Smarkets and Bovada carried no CCT Europe Series #12 moneyline. ([source](https://gamma-api.polymarket.com/events?tag_slug=cs2&active=true&closed=false&limit=100))
  - **Valve official standings** (`accepted_primary`): HAVU (#124, 937 pts) vs ILLYRIANS (#141, 862 pts) on 2026-10-05 global table -> 60.35% HAVU / 39.65% ILLYRIANS. ([source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md))

## `1093218` — Nuclear TigeRES vs UNiTY (NODWIN Clutch Series #13, `2026-10-26T18:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399119/nuclear-tigeres-vs-unity-nodwin-clutch-series-13](https://www.hltv.org/matches/2399119/nuclear-tigeres-vs-unity-nodwin-clutch-series-13) — HLTV match 2399119 confirms BO3 Quarter-final #4 at 2026-10-26T18:00:00Z (NODWIN Clutch Series 13).
- **Published pick**: **Nuclear TigeRES** (`58.28%` / `41.72%` via `consensus` — Consensus across Thunderpick, Bovada)
- **External lines & models checked**:
  - **Smarkets Exchange** (`rejected_schedule_mismatch`): Smarkets event 45401619 lists start_datetime 2026-10-26T15:00:00Z (-3h vs HLTV/Hotspawn 18:00:00Z); rejected by 60s start-time tolerance. ([source](https://smarkets.com/event/45401619/sport/esports/cs-go/nodwin-clutch-series/playoffs/2026/10/26/15-00/nuclear-tigeres-vs-unity-esports))
  - **Thunderpick** (`accepted_consensus_leg`): Joined via scoped alias UNiTY esports -> UNiTY. ([source](https://thunderpick.io/esports/cs2/nodwin-clutch-series-13/nuclear-tigeres-vs-unity-esports-2888791))
  - **Bovada** (`accepted_consensus_leg`): Event 32759181 Moneyline 1.606061 (-165) / 2.250 (+125); median normalized consensus with Thunderpick -> 58.28% Nuclear TigeRES / 41.72% UNiTY. ([source](https://www.bovada.lv/esports/counter-strike-2/nodwin-clutch-series/nuclear-tigeres-unity-esports-202610261400))

## `1082861` — Rooster vs Abyssal (DFRAG Invitational 2026, `2026-10-27T03:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026) — HLTV match 2399891 confirms BO3 Group B Opening Match at 2026-10-27T03:00:00Z (DFRAG Invitational 2026).
- **Published pick**: **Abyssal** (`47.76%` / `52.24%` via `model` — Valve official standings)
- **External lines & models checked**:
  - **Smarkets Exchange** (`rejected_wide_spread`): Event 45398349 quotes Rooster 0.3546/0.5155 (spread 0.1609 > 0.15) and Abyssal 0.4808/0.6452 (spread 0.1644 > 0.15); normalized midpoint 43.59% / 56.41% Abyssal corroborates direction. ([source](https://api.smarkets.com/v3/markets/173454669/quotes/))
  - **Polymarket CLOB** (`rejected_wide_spread`): Two-sided spread exceeded 0.15 fallback ceiling. ([source](https://gamma-api.polymarket.com/events?tag_slug=cs2&active=true&closed=false&limit=100))
  - **Valve official standings** (`accepted_primary`): Rooster (#107, 1020 pts) vs Abyssal (#101, 1036 pts) on 2026-10-05 global table -> 47.76% Rooster / 52.24% Abyssal. ([source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md))

## `1081162` — ex-RUSTEC vs Spirit Academy (CCT Europe 2026 Series #12, `2026-10-27T12:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399512/ex-rustec-vs-spirit-academy-cct-2026-europe-series-12](https://www.hltv.org/matches/2399512/ex-rustec-vs-spirit-academy-cct-2026-europe-series-12) — HLTV match 2399512 confirms BO3 Swiss Round 5 (2-2) at 2026-10-27T12:00:00Z (CCT 2026 Europe Series 12).
- **Published pick**: **ex-RUSTEC** (`61.68%` / `38.32%` via `model` — Valve official standings)
- **External lines & models checked**:
  - **Polymarket CLOB** (`rejected_wide_spread`): Spread > 0.15; no Bovada or Smarkets CCT Europe Series #12 moneyline. ([source](https://gamma-api.polymarket.com/events?tag_slug=cs2&active=true&closed=false&limit=100))
  - **Valve official standings** (`accepted_primary`): ex-RUSTEC (#92 complete 5-player row, 1066 pts) vs Spirit Academy (#115, 981 pts) -> 61.68% ex-RUSTEC / 38.32% Spirit Academy. ([source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md))

## `1081163` — BakS vs Saint Sinners (CCT Europe 2026 Series #12, `2026-10-27T15:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399513/baks-vs-saint-sinners-cct-2026-europe-series-12](https://www.hltv.org/matches/2399513/baks-vs-saint-sinners-cct-2026-europe-series-12) — HLTV match 2399513 confirms BO3 Swiss Round 5 (2-2) at 2026-10-27T15:00:00Z (CCT 2026 Europe Series 12).
- **Published pick**: **BakS** (`78.76%` / `21.24%` via `model` — Valve official standings)
- **External lines & models checked**:
  - **Smarkets & Bovada** (`not_listed`): Neither Smarkets nor Bovada listed CCT Europe Series #12 Swiss Round 5 fixtures. ([source](https://api.smarkets.com/v3/events/?state=new&state=upcoming&type=csgo_match&with_new_type=true&limit=100))
  - **Valve official standings** (`accepted_primary`): BakS (#100, 1044 pts) vs Saint Sinners (#158, 810 pts) -> 78.76% BakS / 21.24% Saint Sinners. ([source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md))

## `1081164` — Inner Circle Academy vs Lavked (CCT Europe 2026 Series #12, `2026-10-27T18:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399514/inner-circle-academy-vs-lavked-cct-2026-europe-series-12](https://www.hltv.org/matches/2399514/inner-circle-academy-vs-lavked-cct-2026-europe-series-12) — HLTV match 2399514 confirms BO3 Swiss Round 5 (2-2) at 2026-10-27T18:00:00Z (CCT 2026 Europe Series 12).
- **Published pick**: **Inner Circle Academy** (`75.61%` / `24.39%` via `model` — Valve official standings)
- **External lines & models checked**:
  - **Smarkets & Bovada** (`not_listed`): Neither Smarkets nor Bovada listed CCT Europe Series #12 Swiss Round 5 fixtures. ([source](https://api.smarkets.com/v3/events/?state=new&state=upcoming&type=csgo_match&with_new_type=true&limit=100))
  - **Valve official standings** (`accepted_primary`): Inner Circle Academy (#94, 1064 pts) vs Lavked (#143, 862 pts) -> 75.61% Inner Circle Academy / 24.39% Lavked. ([source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md))

## `1082792` — HOTU vs The Huns (Moscow Cyber Games 2026, `2026-10-31T09:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) — HLTV match 2399437 confirms BO3 LAN Semi-final at 2026-10-31T09:00:00Z (GLuck Moscow Cyber Games 2026); HOTU (#11581: dwushka, frontales, mizu, n0rb3r7, kade0) vs The Huns (#12510: Bart4k, controlez, bexyz, Cozen, DarkMeister — 4/5 core of Valve #112 The Huns Esports).
- **Published pick**: **HOTU** (`87.00%` / `13.00%` via `market` — Polymarket CLOB)
- **External lines & models checked**:
  - **Polymarket CLOB** (`accepted_primary`): Joined via scoped alias The Huns Esports -> The Huns; two-sided CLOB books 0.82/0.92 and 0.08/0.18 (spread 0.10 <= 0.15) -> 87.00% HOTU / 13.00% The Huns. ([source](https://polymarket.com/event/cs2-hotu-thehun-2026-10-31))

## `1082793` — 5star vs 1WIN (Moscow Cyber Games 2026, `2026-10-31T13:00:00Z`)
- **HLTV first**: [https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026) — HLTV match 2399438 confirms BO3 LAN Semi-final at 2026-10-31T13:00:00Z (GLuck Moscow Cyber Games 2026).
- **Published pick**: **1WIN** (`17.82%` / `82.18%` via `model` — Valve official standings)
- **External lines & models checked**:
  - **Polymarket, Smarkets & Bovada** (`not_listed_or_illiquid`): No two-sided moneyline within the 0.15 spread ceiling across Polymarket, Kalshi, Smarkets, Thunderpick, or Bovada five days ahead of LAN start. ([source](https://api.smarkets.com/v3/events/?state=new&state=upcoming&type=csgo_match&with_new_type=true&limit=100))
  - **Valve official standings** (`accepted_primary`): 5star (#80, 1110 pts) vs 1WIN (#38, 1383 pts) on 2026-10-05 global table -> 17.82% 5star / 82.18% 1WIN. ([source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md))
