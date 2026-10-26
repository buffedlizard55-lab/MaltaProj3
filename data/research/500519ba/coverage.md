# Live coverage audit — session arena-500519ba

Observed **2026-10-26T02:20:24Z** (UTC) on a GitHub Actions runner.

Read-only audit. No probability, pick or alias is written here; scripts/originate.py remains the only path to a published number. A refused source is a limitation of this runner, never proof that a market does not exist. Hotspawn "% picked" and HLTV fan votes are never read as inputs.

## Counts

| Measure | Value |
| --- | --- |
| `api_records` | 81 |
| `api_records_cache_busted` | 0 |
| `api_read_used` | cache_buster_refused |
| `api_cache_buster_status` | 400 |
| `lobby_linked_fixtures` | 19 |
| `cs2_lobby_linked_fixtures` | 19 |
| `live_open` | 19 |
| `fresh_ladder_picked` | 19 |
| `fresh_ladder_unpicked` | 0 |
| `deployed_snapshot_present` | 19 |
| `deployed_snapshot_missing` | 0 |
| `deployed_snapshot_unpicked` | 2 |
| note | the cache-buster parameter was refused by the fixture API (HTTP 400); the unmodified array was used and reconciled against both rendered lobbies |

Deployed snapshot `2026-10-26T01:33:57Z`; fresh run `2026-10-26T02:19:22Z` / origination `2026-10-26T02:19:36Z`.

## Sources read

| Source | Status | Bytes | SHA-256 | Cache |
| --- | --- | --- | --- | --- |
| `fixtures_api` | 200 | 63331 | `60f0e5b67e289dfb` | {'date': 'Mon, 26 Oct 2026 02:20:25 GMT'} |
| `fixtures_api_cache_busted` | 400 | 83 | `20aebe9d2aadb376` | {'date': 'Mon, 26 Oct 2026 02:20:25 GMT'} |
| `lobby` | 200 | 309948 | `b61f72971f99f044` | {'age': '0', 'x-cache': 'MISS', 'date': 'Mon, 26 Oct 2026 02:20:26 GMT'} |
| `cs2_lobby` | 200 | 309009 | `da0274fc18e9ba6c` | {'age': '0', 'x-cache': 'MISS', 'date': 'Mon, 26 Oct 2026 02:20:27 GMT'} |
| `deployed_snapshot` | 200 | 219290 | `f8dcd4d7b1b2ad32` | {'cache-control': 'max-age=600', 'age': '0', 'x-cache': 'MISS', 'date': 'Mon, 26 Oct 2026 02:20:27 GMT'} |
| `hltv_matches` | 403 | 5626 | `8096fc7eaec7f321` | {'date': 'Mon, 26 Oct 2026 02:20:27 GMT'} |
| `hltv_ranking` | 403 | 5665 | `fb63f7b0f2ef60b6` | {'date': 'Mon, 26 Oct 2026 02:20:27 GMT'} |
| `polymarket_events` | 200 | 530504 | `87ff19882d09ed9e` | {'cache-control': 'public, max-age=300', 'x-cache': 'Miss from cloudfront', 'date': 'Mon, 26 Oct 2026 02:20:27 GMT'} |
| `thunderpick` | 200 | 50 | `2e3108e9a0e96f2d` | {'cache-control': 'no-cache, no-store, max-age=0, must-revalidate', 'cf-cache-status': 'DYNAMIC', 'date': 'Mon, 26 Oct 2026 02:20:28 GMT'} |
| `bo3` | 200 | 12827 | `4397d447bdea88d1` | {'cf-cache-status': 'DYNAMIC', 'date': 'Mon, 26 Oct 2026 02:20:28 GMT'} |
| `egamersworld` | 403 | 5776 | `31a223b4119a6193` | {'cache-control': 'private, max-age=0, no-store, no-cache, must-revalidate, post-check=0, pre-check=0', 'date': 'Mon, 26 Oct 2026 02:20:28 GMT'} |

## Every open Hotspawn CS2 fixture

| Fixture | Teams | Starts (UTC) | Tier | Pick | Probabilities | Method | Source | In deployed snapshot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [1082858](https://www.hotspawn.com/matches/x-1082858) | Ground Zero vs Off Chops | 2026-10-26T03:00:00Z | b | Off Chops | 22.0% / 78.0% | market | https://polymarket.com/event/cs2-gz1-offcho-2026-10-25 | yes — Off Chops |
| [1082859](https://www.hotspawn.com/matches/x-1082859) | NEXVOID vs Alter Ego | 2026-10-26T03:00:00Z | b | NEXVOID | 52.9% / 47.1% | market | https://kalshi.com/markets/kxcs2game/counterstrike-2-game/kxcs2game-26oct252300aenex | yes — NEXVOID |
| [1079201](https://www.hotspawn.com/matches/x-1079201) | INOX Division vs Nemesis | 2026-10-26T09:00:00Z | b | Nemesis | 12.3% / 87.7% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | yes — Nemesis |
| [1079202](https://www.hotspawn.com/matches/x-1079202) | FOKUS vs ex-Zero Tenacity | 2026-10-26T12:00:00Z | b | FOKUS | 63.0% / 37.0% | market | https://polymarket.com/event/cs2-fokus-zerote-2026-10-26 | yes — FOKUS |
| [1081159](https://www.hotspawn.com/matches/x-1081159) | LFO 10 vs ex-6666 | 2026-10-26T12:00:00Z | b | ex-6666 | 39.0% / 61.0% | model | https://bo3.gg/matches/sokerorg-vs-ex-6666-26-10-2026 | yes — no pick |
| [1079203](https://www.hotspawn.com/matches/x-1079203) | Metizport vs BRUTE | 2026-10-26T15:00:00Z | b | Metizport | 59.0% / 41.0% | market | https://polymarket.com/event/cs2-mzp-brute-2026-10-26 | yes — Metizport |
| [1081160](https://www.hotspawn.com/matches/x-1081160) | HAVU vs ILLYRIANS | 2026-10-26T15:00:00Z | b | HAVU | 60.3% / 39.7% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | yes — HAVU |
| [1093218](https://www.hotspawn.com/matches/x-1093218) | Nuclear TigeRES vs UNiTY | 2026-10-26T18:00:00Z | b | Nuclear TigeRES | 58.3% / 41.7% | consensus | https://polymarket.com/event/cs2-ntr-unity-2026-10-26 | yes — Nuclear TigeRES |
| [1082860](https://www.hotspawn.com/matches/x-1082860) | FlyQuest vs Staqued | 2026-10-27T03:00:00Z | b | FlyQuest | 93.0% / 7.0% | market | https://polymarket.com/event/cs2-fly-staque-2026-10-26 | yes — FlyQuest |
| [1082861](https://www.hotspawn.com/matches/x-1082861) | Rooster vs Abyssal | 2026-10-27T03:00:00Z | b | Abyssal | 47.8% / 52.2% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | yes — Abyssal |
| [1082897](https://www.hotspawn.com/matches/x-1082897) | B8 vs K27 | 2026-10-27T08:00:00Z | b | B8 | 59.5% / 40.5% | market | https://polymarket.com/event/cs2-b8-k271-2026-10-27 | yes — B8 |
| [1082898](https://www.hotspawn.com/matches/x-1082898) | Alliance vs FaZe | 2026-10-27T11:00:00Z | b | FaZe | 34.0% / 66.0% | market | https://polymarket.com/event/cs2-all-faze-2026-10-27 | yes — FaZe |
| [1081162](https://www.hotspawn.com/matches/x-1081162) | ex-RUSTEC vs Spirit Academy | 2026-10-27T12:00:00Z | b | ex-RUSTEC | 61.7% / 38.3% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | yes — ex-RUSTEC |
| [1081163](https://www.hotspawn.com/matches/x-1081163) | BakS vs Saint Sinners | 2026-10-27T15:00:00Z | b | BakS | 78.8% / 21.2% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | yes — BakS |
| [1082900](https://www.hotspawn.com/matches/x-1082900) | Luminosity vs HOTU | 2026-10-27T17:00:00Z | b | Luminosity | 52.5% / 47.5% | market | https://polymarket.com/event/cs2-lg6-hotu-2026-10-27 | yes — Luminosity |
| [1081164](https://www.hotspawn.com/matches/x-1081164) | Inner Circle Academy vs Lavked | 2026-10-27T18:00:00Z | b | Inner Circle Academy | 75.6% / 24.4% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | yes — Inner Circle Academy |
| [1082901](https://www.hotspawn.com/matches/x-1082901) | Envy vs GamerLegion | 2026-10-27T20:00:00Z | b | GamerLegion | 45.5% / 54.5% | market | https://polymarket.com/event/cs2-envy-gl1-2026-10-27 | yes — GamerLegion |
| [1082792](https://www.hotspawn.com/matches/x-1082792) | HOTU vs The Huns | 2026-10-31T09:00:00Z | b | HOTU | 87.0% / 13.0% | market | https://polymarket.com/event/cs2-hotu-the9-2026-10-31 | yes — no pick |
| [1082793](https://www.hotspawn.com/matches/x-1082793) | 5star vs 1WIN | 2026-10-31T13:00:00Z | b | 1WIN | 17.8% / 82.2% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | yes — 1WIN |

## Fixtures the ladder left blank

None: every open fixture carries a pick with both probabilities and a source link.

## Gaps against the deployed snapshot

None

