# arena-3e64f4fb verification — every published pick, both layers

- Snapshot (featured layer): `2026-10-25T23:03:48Z` (inventory observed `2026-10-25T23:03:30Z`)
- Origination (complete list): `2026-10-25T23:04:02Z`
- Active fixtures: **10**; errors: **0**; warnings: **1**

| Check | Errors | Detail |
| --- | --- | --- |
| inventory | 0 | `{"detail": {"inventory": 72, "upcoming": 10, "archived": 62, "market": 6, "bookmaker": 1, "model": 2, "unresolved": 1, "picks": 9}}` |
| featured | 0 | `{"priced": 9, "blank": ["1082792"]}` |
| complete | 0 | `{"priced": 10, "blank": []}` |
| cross_layer | 0 | `{"researched_resolutions": ["1082792"]}` |
| summary | 0 | `{"sections": ["picks-at-a-glance", "unresolved-register", "no-line-register", "fallback-register"], "percentages_missing_verbatim": [], "broken_links": [], "missing_downloads": ["./data/evidence/polymarket-book-1231333-0` |

| Fixture | Teams | Starts (UTC) | Featured | Complete | Probabilities | Pick | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1082858 | Ground Zero vs Off Chops | 2026-10-26T03:00:00Z | market-midpoint | market-midpoint (market) | 20.0% / 80.0% | **Off Chops** | https://polymarket.com/event/cs2-gz1-offcho-2026-10-25 |
| 1082859 | NEXVOID vs Alter Ego | 2026-10-26T03:00:00Z | bookmaker-no-vig | bookmaker-no-vig (bookmaker) | 57.5% / 42.5% | **NEXVOID** | https://thunderpick.io/api/matches |
| 1082860 | FlyQuest vs Staqued | 2026-10-27T03:00:00Z | market-midpoint | market-midpoint (market) | 92.5% / 7.5% | **FlyQuest** | https://polymarket.com/event/cs2-fly-staque-2026-10-26 |
| 1082861 | Rooster vs Abyssal | 2026-10-27T03:00:00Z | valve-glicko | valve-glicko (model) | 47.8% / 52.2% | **Abyssal** | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md |
| 1082897 | B8 vs K27 | 2026-10-27T08:00:00Z | market-midpoint | market-midpoint (market) | 59.5% / 40.5% | **B8** | https://polymarket.com/event/cs2-b8-k271-2026-10-27 |
| 1082898 | Alliance vs FaZe | 2026-10-27T11:00:00Z | market-midpoint | market-midpoint (market) | 37.5% / 62.5% | **FaZe** | https://polymarket.com/event/cs2-all-faze-2026-10-27 |
| 1082900 | Luminosity vs HOTU | 2026-10-27T17:00:00Z | market-midpoint | market-midpoint (market) | 52.5% / 47.5% | **Luminosity** | https://polymarket.com/event/cs2-lg6-hotu-2026-10-27 |
| 1082901 | Envy vs GamerLegion | 2026-10-27T20:00:00Z | market-midpoint | market-midpoint (market) | 45.5% / 54.5% | **GamerLegion** | https://polymarket.com/event/cs2-envy-gl1-2026-10-27 |
| 1082792 | HOTU vs The Huns | 2026-10-31T09:00:00Z | blank | market-midpoint (market) | 87.0% / 13.0% | **HOTU** | https://polymarket.com/event/cs2-hotu-the9-2026-10-31 |
| 1082793 | 5star vs 1WIN | 2026-10-31T13:00:00Z | valve-glicko | valve-glicko (model) | 17.8% / 82.2% | **1WIN** | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md |

## Warnings
- summary: evidence downloads linked from the executive summary are absent from the checked-in root (served by the artifact deployment, would 404 from a branch-root serve): ./data/evidence/polymarket-book-1231333-0.json, ./data/evidence/polymarket-book-1231333-1.json, ./data/evidence/polymarket-book-1237427-0.json, ./data/evidence/polymarket-book-1237427-1.json, ./data/evidence/polymarket-book-1237429-0.json, ./data/evidence/polymarket-book-1237429-1.json, ./data/evidence/polymarket-event-1231333.json, ./data/evidence/polymarket-event-1237427.json, ./data/evidence/polymarket-event-1237429.json
