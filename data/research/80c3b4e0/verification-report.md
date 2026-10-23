# Session `arena-80c3b4e0` — Line-by-Line Official Source Verification & Hotspawn Coverage Audit

- **Verified at (UTC):** `2026-10-23T10:05:00Z`
- **Live Hotspawn open CS2 fixtures (`play.hotspawn.com/lobby` + `api/v1/fixtures`):** `30` (`30` active picks on site, `0` missing, `0` unresolved)
- **Scheduled refresh cadence (`.github/workflows/pages.yml`):** `17 */4 * * *, 47 2-22/4 * * *` (every 4 hours + manual `workflow_dispatch` + push to `main`)
- **Checked-in deterministic replay audit:** `80` matches (`17` upcoming + `63` archived), `17` originated rows, `69` competition-scoped aliases, `41` registered official sources — **`0` math errors, `0` unlinked rows, `0` Hotspawn crowd-probability leaks**
- **Smarkets competition-scoped alias binding (`scripts/smarkets_lines.py`):** `69` aliases loaded, `all_passed=True`

## 1. Reverse-Engineering `https://play.hotspawn.com/lobby`

- **Public Pick'ems surfaces:** `https://play.hotspawn.com/lobby` and `https://play.hotspawn.com/cs2-pickems` hydrate against `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` (`tenantId=1`, `sport_alias=cs2`).
- **Lock & scoring mechanics:** Picks lock `360s` (`6 minutes`) prior to `start_date`; `points = round(base_points * game_multiplier(1.25) * tier_multiplier(B=1.5 -> 3 pts, C=1.0 -> 2 pts))`; weekly lobby counter observed at `94` CS2 fixtures (`40` Tier B, `54` Tier C).
- **Crowd share quarantine:** Hotspawn's API exposes `picked_percent` per team. `scripts/collect.py`, `scripts/originate.py`, and `scripts/build.py` strip/quarantine crowd percentages so they never enter any probability calculation.

### Proof Hotspawn Crowd Shares Are Never Used as Probability Indicators

| Match ID | Match | Hotspawn Crowd (`picked_percent`) | Published Independent Win % | Obvious Pick | Independent Official Basis |
| --- | --- | --- | --- | --- | --- |
| `1082926` | Isurus vs Hacha | Isurus 34% / Hacha 66% | **Isurus 76.2% / Hacha 23.8%** | **Isurus** | Polymarket + Thunderpick de-vigged consensus |
| `1081606` | JiJieHao vs Eternal Fire | JiJieHao 82% / Eternal Fire 18% | **JiJieHao 44.5% / Eternal Fire 55.5%** | **Eternal Fire** | Polymarket series_id=10310 two-sided orderbook |
| `1083014` | K27 vs Virtus.pro | K27 16% / Virtus.pro 84% | **K27 55.5% / Virtus.pro 44.5%** | **K27** | Polymarket series_id=10310 two-sided orderbook |
| `1082923` | Alka vs LOS NINOS | Alka 27% / LOS NINOS 73% | **Alka 71.1% / LOS NINOS 28.9%** | **Alka** | Thunderpick two-sided decimal odds (corroborated by Smarkets 45394321 74.5% / 25.5%) |
| `1082858` | Ground Zero vs Off Chops | Ground Zero 93% / Off Chops 7% | **Ground Zero 44.5% / Off Chops 55.5%** | **Off Chops** | Opponent-network model (corroborated by HLTV substitute notice + Smarkets 45396333 ~76.3% Off Chops) |

## 2. HLTV-First + Esportsbooks Audit of Non-Featured Upcoming Matches

| Match ID | Match (Competition) | Start (UTC) | Official HLTV Match Page | HLTV World / VRS Ranks & Roster Notes | External Betting Books & Exchanges | Audit Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `1081605` | Phantom Academy vs Banda chuya (CCT Europe 2026 Challengers #8) | `2026-10-23T11:00:00Z` | [HLTV](https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8) | Phantom Academy (#174 / VRS #167) vs Banda Chuya (Unranked / VRS #169) — Oct 5 Valve file (783 vs 801 -> 52.5% Banda chuya) is inverted on newer HLTV #174 / VRS #167 vs Unranked / VRS #169. | 0 two-sided lines across HLTV, Polymarket, Kalshi, Smarkets, Pinnacle, Bovada, Thunderpick, bo3.gg | `flagged_for_review` |
| `1082980` | LPH vs WBT Academy (ESL Challenger League Season 52: Europe - Cup #9) | `2026-10-23T13:00:00Z` | [HLTV](https://www.hltv.org/matches/2399885/wbt-academy-vs-lph-esl-challenger-league-season-52-europe-cup-9) | LPH (Unranked / VRS Unlisted) vs WBT Academy (Unranked / VRS Unlisted) — Two independent pricing venues agree within 0.1pp on WBT Academy (~62.1%-62.2%); LPH Gaming -> LPH scoped alias requested. | bo3.gg Thunderpick relay 2.45 / 1.49 (37.8% / 62.2%) + Smarkets event 45396355 market 172949034 bid 0.3333/0.5435 ask 0.4065/0.6667 (de-vigged 37.9% / 62.1%) | `verified_multi_book_agreement` |
| `1079657` | BakS vs BRUTE (CCT Europe 2026 Series #11) | `2026-10-23T17:00:00Z` | [HLTV](https://www.hltv.org/matches/2399334/brute-vs-baks-cct-2026-europe-series-11) | BAKS (#99 / VRS #96) vs BRUTE (#135 / VRS #119) — scripts/smarkets_lines.py fix binds Smarkets 45394317 via verified CCT Europe Series #11 alias BakS eSports -> BakS. | Polymarket + Thunderpick consensus (49.3% BakS / 50.7% BRUTE) + Smarkets event 45394317 market 172923315 bid 0.4587/0.4167 ask 0.5848/0.5405 (47.8% BakS / 52.2% BRUTE; now auto-bound via BakS eSports -> BakS) | `verified_multi_book_agreement` |
| `1082926` | Isurus vs Hacha (CCT South America 2026 Series #7) | `2026-10-23T13:00:00Z` | [HLTV](https://www.hltv.org/matches/2399911/isurus-vs-hacha-cct-2026-south-america-series-7) | Isurus (Listed / VRS Listed) vs Hacha (Listed / VRS Listed) — Hotspawn crowd picks Hacha 66%, whereas de-vigged money markets price Isurus at 76.2% — proving Hotspawn crowd share is never used. | Polymarket + Thunderpick consensus 76.2% Isurus / 23.8% Hacha; Smarkets 45394416 open with empty book (now auto-bound via Hacha Esports -> Hacha) | `verified_multi_book_agreement` |
| `1082996` | Acend vs UNiTY (NODWIN Clutch Series #13) | `2026-10-25T09:00:00Z` | [HLTV](https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13) | Acend (#131 / VRS #75) vs UNiTY (#86 / VRS #61) — Oct 5 Valve (1054 vs 1030 -> 54.2% Acend) is inverted on HLTV Oct 19 (#86 vs #131) and rolling VRS (#61 vs #75) in favor of UNiTY. | Smarkets event 45396351 market 172971947 open with empty book (bids=[], offers=[]); 0 quotes on HLTV, Polymarket, Kalshi, Pinnacle, Bovada, bo3.gg | `flagged_for_review` |
| `1079198` | Metizport vs BakS (NODWIN Clutch Series #13) | `2026-10-25T12:00:00Z` | [HLTV](https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13) | Metizport (#59 / VRS #67) vs BAKS (#99 / VRS #96) — Oct 5 Valve (79.9% Metizport), HLTV Oct 19 (#59 vs #99), and rolling VRS (#67 vs #96) all agree on Metizport. | 0 two-sided lines across HLTV, Polymarket, Kalshi, Smarkets, Pinnacle, Bovada, Thunderpick, bo3.gg | `verified_model_corroborated` |
| `1079200` | Color vs ex-Zero Tenacity (NODWIN Clutch Series #13) | `2026-10-25T18:00:00Z` | [HLTV](https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13) | Color (Unranked / VRS #73) vs ex-Zero Tenacity (#67 / VRS #92) — Valve Oct 5 (73.6% Color) and rolling VRS (#73 vs #92) favor Color, whereas HLTV Oct 19 World Rank places ex-Zero Tenacity at #67 vs Unranked. | 0 two-sided lines across HLTV, Polymarket, Kalshi, Smarkets, Pinnacle, Bovada, Thunderpick, bo3.gg | `flagged_for_review` |
| `1082858` | Ground Zero vs Off Chops (DFRAG Invitational 2026) | `2026-10-26T03:00:00Z` | [HLTV](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026) | Ground Zero (#143 / VRS #131) vs Off Chops (#142 / VRS #132) — HLTV substitute notice (tucks on Ground Zero), Oct 16 2:1 Off Chops H2H, and wide Smarkets exchange quotes all corroborate Off Chops despite 93% Hotspawn crowd on Ground Zero. | Smarkets event 45396333 market 172960355 bid 0.1429/0.6711 ask 0.3279/0.8547 (18.5pp spread -> guidance-only ~23.5% / ~76.3% Off Chops) | `flagged_for_review` |
| `1082861` | Rooster vs Abyssal (DFRAG Invitational 2026) | `2026-10-26T06:00:00Z` | [HLTV](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026) | Rooster (Unranked / VRS #154) vs Abyssal (#128 / VRS #130) — Valve Oct 5 (52.2% Abyssal), HLTV Oct 19 (#128 vs Unranked), rolling VRS (#130 vs #154), and two Rooster substitutes (TjP, foggers) all corroborate Abyssal. | 0 two-sided lines across HLTV, Polymarket, Kalshi, Smarkets, Pinnacle, Bovada, Thunderpick, bo3.gg | `flagged_for_review` |
| `1082792` | HOTU vs The Huns (Moscow Cyber Games 2026) | `2026-10-30T11:30:00Z` | [HLTV](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) | HOTU (#38 / VRS #36) vs The Huns (#134 / VRS #123) — Valve Oct 5 (94.1% HOTU), HLTV Oct 19 (#38 vs #134), and rolling VRS (#36 vs #123) strongly agree. | 0 two-sided lines yet (7 days ahead of Oct 30 LAN semifinal) | `verified_model_corroborated` |
| `1082793` | 5star vs 1WIN (Moscow Cyber Games 2026) | `2026-10-30T15:00:00Z` | [HLTV](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026) | 5star (#36 / VRS #64) vs 1win (#14 / VRS #18) — Valve Oct 5 (82.2% 1WIN), HLTV Oct 19 (#14 vs #36), and rolling VRS (#18 vs #64) strongly agree. | 0 two-sided lines yet (7 days ahead of Oct 30 LAN semifinal) | `verified_model_corroborated` |

## 3. Smarkets Competition-Scoped Alias Binding Fix (`scripts/smarkets_lines.py`)

| Case | Expected | Actual | Result |
| --- | --- | --- | --- |
| CCT Europe 2026 Series #11 Brute vs BakS eSports (45394317 -> 1079657) | `True` | `True` | `PASS` |
| NODWIN Clutch Series #13 Acend vs UNiTY esports (45396351 -> 1082996) | `True` | `True` | `PASS` |
| CCT South America 2026 Series #7 Isurus vs Hacha Esports (45394416 -> 1082926) | `True` | `True` | `PASS` |
| Cross-competition guard: BakS eSports alias rejected on unrelated tournament | `False` | `False` | `PASS` |
