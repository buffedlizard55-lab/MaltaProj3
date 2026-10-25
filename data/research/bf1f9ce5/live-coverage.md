# Live Hotspawn CS2 lobby & API coverage reconciliation — arena-bf1f9ce5

- Observed at: `2026-10-25T13:57:50Z` (`github-actions-runner`)
- Deployed `snapshot.json` generated at: `2026-10-25T05:12:25Z` (`79` total, `18` active)
- Cached `/lobby`: `80` CS2 fixtures (tiers `{'C': 47, 'B': 33}`)
- Cache-busted `/lobby?cb=1792936670`: `78` CS2 fixtures (tiers `{'C': 47, 'B': 31}`)
- Official scheduled API: `78` CS2 fixtures (`17` active open/locked)
- Fresh `collect` + `originate --live` active coverage: `17/17` picks (`0` unresolved)

## Active Hotspawn CS2 fixtures & verified sources

| ID | Starts (UTC) | Competition | Match | Fresh Basis | Pick | In 05:12Z Deployed? | Hotspawn | HLTV |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1085542` | `2026-10-25T14:00:00Z` | CCT Europe 2026 Series #11 | ex-Zero Tenacity vs Spirit Academy | Valve-rating research estimate | ex-Zero Tenacity (61.7% vs 38.3%) | yes | https://www.hotspawn.com/matches/ex-zero-tenacity-vs-spirit-academy-cct-europe-2026-series-11-1085542 | — |
| `1079199` | `2026-10-25T15:00:00Z` | NODWIN Clutch Series #13 | Infinite vs BRUTE | Market-implied estimate | BRUTE (56.5% vs 43.5%) | yes | https://www.hotspawn.com/matches/infinite-vs-brute-nodwin-clutch-series-13-1079199 | — |
| `1086696` | `2026-10-25T16:00:00Z` | CCT South America 2026 Series #7 | BORRACHEIROS vs RED Canids Academy | Market-implied estimate | RED Canids Academy (57.5% vs 42.5%) | **NEW since 05:12Z** | https://play.hotspawn.com/cs2-pickems#fixture-1086696 | — |
| `1079200` | `2026-10-25T18:00:00Z` | NODWIN Clutch Series #13 | Color vs ex-Zero Tenacity | Market-implied estimate | Color (50.5% vs 49.5%) | yes | https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200 | — |
| `1081158` | `2026-10-25T18:00:00Z` | CCT Europe 2026 Series #12 | FORZE Reload vs ex-RUSTEC | Market-implied estimate | FORZE Reload (56.5% vs 43.5%) | yes | https://www.hotspawn.com/matches/forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158 | — |
| `1082697` | `2026-10-25T18:00:00Z` | Circuit X Curitiba #4 | BESTIA vs paiN | Market-implied estimate | paiN (58.5% vs 41.5%) | **NEW since 05:12Z** | https://www.hotspawn.com/matches/pain-vs-bestia-circuit-x-curitiba-4-1082697 | — |
| `1086697` | `2026-10-25T19:00:00Z` | CCT South America 2026 Series #7 | Projeto do KinGui vs Yawara | Originated consensus line (median of independent money sources) | Projeto do KinGui (65.4% vs 34.6%) | **NEW since 05:12Z** | https://play.hotspawn.com/cs2-pickems#fixture-1086697 | — |
| `1082858` | `2026-10-26T03:00:00Z` | DFRAG Invitational 2026 | Ground Zero vs Off Chops | Own network estimate (bo3.gg results graph) | Off Chops (55.0% vs 45.0%) | yes | https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858 | https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026 |
| `1082859` | `2026-10-26T03:00:00Z` | DFRAG Invitational 2026 | NEXVOID vs Alter Ego | No-vig bookmaker estimate | NEXVOID (57.9% vs 42.1%) | yes | https://www.hotspawn.com/matches/nexvoid-vs-alter-ego-dfrag-invitational-2026-1082859 | https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026 |
| `1082860` | `2026-10-27T03:00:00Z` | DFRAG Invitational 2026 | FlyQuest vs Staqued | Market-implied estimate | FlyQuest (92.5% vs 7.5%) | yes | https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860 | — |
| `1082861` | `2026-10-27T03:00:00Z` | DFRAG Invitational 2026 | Rooster vs Abyssal | Valve-rating research estimate | Abyssal (52.2% vs 47.8%) | yes | https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861 | https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026 |
| `1082897` | `2026-10-27T08:00:00Z` | Tesla Cup 2026 | B8 vs K27 | Market-implied estimate | B8 (59.5% vs 40.5%) | yes | https://www.hotspawn.com/matches/b8-vs-k27-tesla-cup-2026-1082897 | — |
| `1082898` | `2026-10-27T11:00:00Z` | Tesla Cup 2026 | Alliance vs FaZe | Market-implied estimate | FaZe (62.5% vs 37.5%) | yes | https://www.hotspawn.com/matches/alliance-vs-faze-tesla-cup-2026-1082898 | — |
| `1082900` | `2026-10-27T17:00:00Z` | Tesla Cup 2026 | Luminosity vs HOTU | Market-implied estimate | Luminosity (52.5% vs 47.5%) | yes | https://www.hotspawn.com/matches/luminosity-vs-hotu-tesla-cup-2026-1082900 | — |
| `1082901` | `2026-10-27T20:00:00Z` | Tesla Cup 2026 | Envy vs GamerLegion | Market-implied estimate | GamerLegion (54.5% vs 45.5%) | yes | https://www.hotspawn.com/matches/envy-vs-gamerlegion-tesla-cup-2026-1082901 | — |
| `1082792` | `2026-10-31T09:00:00Z` | Moscow Cyber Games 2026 | HOTU vs The Huns | Research model estimate (Valve official ratings) | HOTU (94.1% vs 5.9%) | yes | https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792 | https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026 |
| `1082793` | `2026-10-31T13:00:00Z` | Moscow Cyber Games 2026 | 5star vs 1WIN | Valve-rating research estimate | 1WIN (82.2% vs 17.8%) | yes | https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793 | https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026 |
