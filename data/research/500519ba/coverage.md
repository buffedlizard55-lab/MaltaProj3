# Live coverage audit — session arena-500519ba

Observed **2026-10-26T01:07:00Z** (UTC) on a GitHub Actions runner.

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
| `deployed_snapshot_present` | 10 |
| `deployed_snapshot_missing` | 9 |
| `deployed_snapshot_unpicked` | 1 |
| note | the cache-buster parameter was refused by the fixture API (HTTP 400); the unmodified array was used and reconciled against both rendered lobbies |

Deployed snapshot `2026-10-25T23:03:48Z`; fresh run `2026-10-26T01:04:36Z` / origination `2026-10-26T01:04:51Z`.

## Sources read

| Source | Status | Bytes | SHA-256 | Cache |
| --- | --- | --- | --- | --- |
| `fixtures_api` | 200 | 63325 | `0df7f1fd98b6053f` | {'date': 'Mon, 26 Oct 2026 01:07:00 GMT'} |
| `fixtures_api_cache_busted` | 400 | 83 | `20aebe9d2aadb376` | {'date': 'Mon, 26 Oct 2026 01:07:00 GMT'} |
| `lobby` | 200 | 309942 | `8e8f62d7bb73dcaa` | {'age': '0', 'x-cache': 'MISS', 'date': 'Mon, 26 Oct 2026 01:07:01 GMT'} |
| `cs2_lobby` | 200 | 309003 | `95dcbac4ef071b43` | {'age': '0', 'x-cache': 'MISS', 'date': 'Mon, 26 Oct 2026 01:07:02 GMT'} |
| `deployed_snapshot` | 200 | 163362 | `1c8a8c9af0c5ca6e` | {'cache-control': 'max-age=600', 'age': '0', 'x-cache': 'MISS', 'date': 'Mon, 26 Oct 2026 01:07:02 GMT'} |
| `hltv_matches` | 403 | 5626 | `5d4f33358c59e83a` | {'date': 'Mon, 26 Oct 2026 01:07:02 GMT'} |
| `hltv_ranking` | 403 | 5644 | `5e60da8426462433` | {'date': 'Mon, 26 Oct 2026 01:07:02 GMT'} |
| `polymarket_events` | 200 | 530208 | `745fadfc69a6dedf` | {'cache-control': 'public, max-age=300', 'x-cache': 'Miss from cloudfront', 'date': 'Mon, 26 Oct 2026 01:07:03 GMT'} |
| `thunderpick` | 200 | 50 | `2e3108e9a0e96f2d` | {'cache-control': 'no-cache, no-store, max-age=0, must-revalidate', 'cf-cache-status': 'DYNAMIC', 'date': 'Mon, 26 Oct 2026 01:07:03 GMT'} |
| `bo3` | 200 | 12827 | `4397d447bdea88d1` | {'cf-cache-status': 'DYNAMIC', 'date': 'Mon, 26 Oct 2026 01:07:03 GMT'} |
| `egamersworld` | 403 | 5774 | `7338882ee022fa16` | {'cache-control': 'private, max-age=0, no-store, no-cache, must-revalidate, post-check=0, pre-check=0', 'date': 'Mon, 26 Oct 2026 01:07:03 GMT'} |

## Every open Hotspawn CS2 fixture

| Fixture | Teams | Starts (UTC) | Tier | Pick | Probabilities | Method | Source | In deployed snapshot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [1082858](https://www.hotspawn.com/matches/x-1082858) | Ground Zero vs Off Chops | 2026-10-26T03:00:00Z | b | Off Chops | 20.5% / 79.5% | market | https://polymarket.com/event/cs2-gz1-offcho-2026-10-25 | yes — Off Chops |
| [1082859](https://www.hotspawn.com/matches/x-1082859) | NEXVOID vs Alter Ego | 2026-10-26T03:00:00Z | b | NEXVOID | 59.2% / 40.8% | bookmaker | https://thunderpick.io/api/matches | yes — NEXVOID |
| [1079201](https://www.hotspawn.com/matches/x-1079201) | INOX Division vs Nemesis | 2026-10-26T09:00:00Z | b | Nemesis | 12.3% / 87.7% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | no |
| [1079202](https://www.hotspawn.com/matches/x-1079202) | FOKUS vs ex-Zero Tenacity | 2026-10-26T12:00:00Z | b | FOKUS | 68.2% / 31.8% | bookmaker | https://thunderpick.io/api/matches | no |
| [1081159](https://www.hotspawn.com/matches/x-1081159) | LFO 10 vs ex-6666 | 2026-10-26T12:00:00Z | b | ex-6666 | 39.0% / 61.0% | model | https://bo3.gg/matches/sokerorg-vs-ex-6666-26-10-2026 | no |
| [1079203](https://www.hotspawn.com/matches/x-1079203) | Metizport vs BRUTE | 2026-10-26T15:00:00Z | b | Metizport | 61.5% / 38.5% | bookmaker | https://thunderpick.io/api/matches | no |
| [1081160](https://www.hotspawn.com/matches/x-1081160) | HAVU vs ILLYRIANS | 2026-10-26T15:00:00Z | b | HAVU | 60.3% / 39.7% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | no |
| [1093218](https://www.hotspawn.com/matches/x-1093218) | Nuclear TigeRES vs UNiTY | 2026-10-26T18:00:00Z | b | Nuclear TigeRES | 58.3% / 41.7% | consensus | https://thunderpick.io/esports/counter-strike | no |
| [1082860](https://www.hotspawn.com/matches/x-1082860) | FlyQuest vs Staqued | 2026-10-27T03:00:00Z | b | FlyQuest | 92.5% / 7.5% | market | https://polymarket.com/event/cs2-fly-staque-2026-10-26 | yes — FlyQuest |
| [1082861](https://www.hotspawn.com/matches/x-1082861) | Rooster vs Abyssal | 2026-10-27T03:00:00Z | b | Abyssal | 47.8% / 52.2% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | yes — Abyssal |
| [1082897](https://www.hotspawn.com/matches/x-1082897) | B8 vs K27 | 2026-10-27T08:00:00Z | b | B8 | 59.5% / 40.5% | market | https://polymarket.com/event/cs2-b8-k271-2026-10-27 | yes — B8 |
| [1082898](https://www.hotspawn.com/matches/x-1082898) | Alliance vs FaZe | 2026-10-27T11:00:00Z | b | FaZe | 34.0% / 66.0% | market | https://polymarket.com/event/cs2-all-faze-2026-10-27 | yes — FaZe |
| [1081162](https://www.hotspawn.com/matches/x-1081162) | ex-RUSTEC vs Spirit Academy | 2026-10-27T12:00:00Z | b | ex-RUSTEC | 61.7% / 38.3% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | no |
| [1081163](https://www.hotspawn.com/matches/x-1081163) | BakS vs Saint Sinners | 2026-10-27T15:00:00Z | b | BakS | 78.8% / 21.2% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | no |
| [1082900](https://www.hotspawn.com/matches/x-1082900) | Luminosity vs HOTU | 2026-10-27T17:00:00Z | b | Luminosity | 52.5% / 47.5% | market | https://polymarket.com/event/cs2-lg6-hotu-2026-10-27 | yes — Luminosity |
| [1081164](https://www.hotspawn.com/matches/x-1081164) | Inner Circle Academy vs Lavked | 2026-10-27T18:00:00Z | b | Inner Circle Academy | 75.6% / 24.4% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | no |
| [1082901](https://www.hotspawn.com/matches/x-1082901) | Envy vs GamerLegion | 2026-10-27T20:00:00Z | b | GamerLegion | 45.5% / 54.5% | market | https://polymarket.com/event/cs2-envy-gl1-2026-10-27 | yes — GamerLegion |
| [1082792](https://www.hotspawn.com/matches/x-1082792) | HOTU vs The Huns | 2026-10-31T09:00:00Z | b | HOTU | 87.0% / 13.0% | market | https://polymarket.com/event/cs2-hotu-the9-2026-10-31 | yes — no pick |
| [1082793](https://www.hotspawn.com/matches/x-1082793) | 5star vs 1WIN | 2026-10-31T13:00:00Z | b | 1WIN | 17.8% / 82.2% | model | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | yes — 1WIN |

## Fixtures the ladder left blank

None: every open fixture carries a pick with both probabilities and a source link.

## Gaps against the deployed snapshot

1079201, 1079202, 1081159, 1079203, 1081160, 1093218, 1081162, 1081163, 1081164

