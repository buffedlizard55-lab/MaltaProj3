# Live coverage audit — session arena-500519ba

Observed **2026-10-26T03:47:43Z** (UTC) on a GitHub Actions runner.

Read-only audit. No probability, pick or alias is written here; scripts/originate.py remains the only path to a published number. A refused source is a limitation of this runner, never proof that a market does not exist. Hotspawn "% picked" and HLTV fan votes are never read as inputs.

## Counts

| Measure | Value |
| --- | --- |
| `api_records` | 80 |
| `api_records_cache_busted` | 0 |
| `api_read_used` | cache_buster_refused |
| `api_cache_buster_status` | 400 |
| `lobby_linked_fixtures` | 17 |
| `cs2_lobby_linked_fixtures` | 17 |
| `live_open` | 17 |
| `fresh_ladder_picked` | 17 |
| `fresh_ladder_unpicked` | 0 |
| `deployed_snapshot_present` | 17 |
| `deployed_snapshot_missing` | 0 |
| `deployed_snapshot_unpicked` | 2 |
| note | the cache-buster parameter was refused by the fixture API (HTTP 400); the unmodified array was used and reconciled against both rendered lobbies |

Deployed snapshot `2026-10-26T03:14:52Z`; fresh run `2026-10-26T03:46:53Z` / origination `2026-10-26T03:47:06Z`.

## Sources read

| Source | Status | Bytes | SHA-256 | Cache |
| --- | --- | --- | --- | --- |
| `fixtures_api` | 200 | 62563 | `12d142bd5e37b967` | {'date': 'Mon, 26 Oct 2026 03:47:44 GMT'} |
| `fixtures_api_cache_busted` | 400 | 83 | `20aebe9d2aadb376` | {'date': 'Mon, 26 Oct 2026 03:47:44 GMT'} |
| `lobby` | 200 | 292055 | `6a1f85f849d8d6c4` | {'age': '0', 'x-cache': 'MISS', 'date': 'Mon, 26 Oct 2026 03:47:45 GMT'} |
| `cs2_lobby` | 200 | 291160 | `06f60d439056b6dc` | {'age': '0', 'x-cache': 'MISS', 'date': 'Mon, 26 Oct 2026 03:47:46 GMT'} |
| `deployed_snapshot` | 200 | 217573 | `dabc63b525421b92` | {'cache-control': 'max-age=600', 'age': '0', 'x-cache': 'MISS', 'date': 'Mon, 26 Oct 2026 03:47:47 GMT'} |
| `hltv_matches` | 403 | 5626 | `97025eed8df43b03` | {'date': 'Mon, 26 Oct 2026 03:47:47 GMT'} |
| `hltv_ranking` | 403 | 5644 | `7fa5b0f099dcc641` | {'date': 'Mon, 26 Oct 2026 03:47:47 GMT'} |
| `polymarket_events` | 200 | 530649 | `177095c1b2b07cb0` | {'cache-control': 'public, max-age=300', 'x-cache': 'Miss from cloudfront', 'date': 'Mon, 26 Oct 2026 03:47:47 GMT'} |
| `thunderpick` | 200 | 50 | `2e3108e9a0e96f2d` | {'cache-control': 'no-cache, no-store, max-age=0, must-revalidate', 'cf-cache-status': 'DYNAMIC', 'date': 'Mon, 26 Oct 2026 03:47:47 GMT'} |
| `bo3` | 200 | 12827 | `4397d447bdea88d1` | {'cf-cache-status': 'DYNAMIC', 'date': 'Mon, 26 Oct 2026 03:47:48 GMT'} |
| `egamersworld` | 403 | 5774 | `4aa78dafbb5e2615` | {'cache-control': 'private, max-age=0, no-store, no-cache, must-revalidate, post-check=0, pre-check=0', 'date': 'Mon, 26 Oct 2026 03:47:48 GMT'} |

## Every open Hotspawn CS2 fixture

| Fixture | Teams | Starts (UTC) | Tier | Pick | Probabilities | Method | Source | In deployed snapshot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [1079201](https://www.hotspawn.com/matches/x-1079201) | INOX Division vs Nemesis | 2026-10-26T09:00:00Z | b | Nemesis | 25.4% / 74.6% | consensus | https://polymarket.com/event/cs2-nem-inox-2026-10-26 | yes — Nemesis |
| [1079202](https://www.hotspawn.com/matches/x-1079202) | FOKUS vs ex-Zero Tenacity | 2026-10-26T12:00:00Z | b | FOKUS | 62.0% / 38.0% | market | https://polymarket.com/event/cs2-fokus-zerote-2026-10-26 | yes — FOKUS |
| [1081159](https://www.hotspawn.com/matches/x-1081159) | LFO 10 vs ex-6666 | 2026-10-26T12:00:00Z | b | ex-6666 | 39.0% / 61.0% | model | https://bo3.gg/matches/sokerorg-vs-ex-6666-26-10-2026 | yes — no pick |
| [1079203](https://www.hotspawn.com/matches/x-1079203) | Metizport vs BRUTE | 2026-10-26T15:00:00Z | b | Metizport | 59.0% / 41.0% | market | https://polymarket.com/event/cs2-mzp-brute-2026-10-26 | yes — Metizport |
| [1081160](https://www.hotspawn.com/matches/x-1081160) | HAVU vs ILLYRIANS | 2026-10-26T15:00:00Z | b | HAVU | 53.5% / 46.5% | market | https://polymarket.com/event/cs2-havu-ill4-2026-10-26 | yes — HAVU |
| [1093218](https://www.hotspawn.com/matches/x-1093218) | Nuclear TigeRES vs UNiTY | 2026-10-26T18:00:00Z | b | Nuclear TigeRES | 58.3% / 41.7% | consensus | https://polymarket.com/event/cs2-ntr-unity-2026-10-26 | yes — Nuclear TigeRES |
| [1082860](https://www.hotspawn.com/matches/x-1082860) | FlyQuest vs Staqued | 2026-10-27T03:00:00Z | b | FlyQuest | 92.0% / 8.0% | market | https://polymarket.com/event/cs2-fly-staque-2026-10-26 | yes — FlyQuest |
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

