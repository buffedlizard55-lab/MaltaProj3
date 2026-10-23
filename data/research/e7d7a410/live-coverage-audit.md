# arena-e7d7a410 — live coverage audit

Audited **2026-10-23T05:57:04Z** against the inventory observed **2026-10-23T05:29:12Z** (snapshot 2026-10-23T05:29:35Z, picks feed 2026-10-23T05:29:49Z).

| Check | Result |
| --- | --- |
| Active Hotspawn CS2 fixtures | **30** |
| With a pick and no defect | **30** |
| Without a pick | **0** |
| Defective rows | **0** |
| Resolved by an external money line | **21** |
| Model-only estimate (no betting line) | **9** |
| Featured exact-name method left blank (resolved by the complete feed) | **6** |
| Complete-feed rows with no active fixture | **0** |

Money methods: bookmaker 4, consensus 2, market 15. Model methods: model 9.

No defective row: every active fixture has two probabilities in (0, 1) summing to 1, a pick at the favourite, an https source, and the same team names and start time as the inventory.

## Picks without an external betting line

Each row keeps a labelled research estimate, the source actually used and the reason no market was bound. It is never presented as a betting price.

| Fixture | Competition | Start | Pick | Estimate | Source |
| --- | --- | --- | --- | --- | --- |
| Phantom Academy vs Banda chuya | CCT Europe 2026 Challengers #8 | 2026-10-23T11:00:00Z | Banda chuya | Banda chuya 52.5% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| Acend vs UNiTY | NODWIN Clutch Series #13 | 2026-10-25T09:00:00Z | Acend | Acend 54.2% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| Metizport vs BakS | NODWIN Clutch Series #13 | 2026-10-25T12:00:00Z | Metizport | Metizport 79.9% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| Infinite vs BRUTE | NODWIN Clutch Series #13 | 2026-10-25T15:00:00Z | Infinite | Infinite 69.0% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| Color vs ex-Zero Tenacity | NODWIN Clutch Series #13 | 2026-10-25T18:00:00Z | Color | Color 73.6% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| Ground Zero vs Off Chops | DFRAG Invitational 2026 | 2026-10-26T03:00:00Z | Off Chops | Off Chops 55.5% | [Own network model (bo3.gg results graph)](https://bo3.gg/matches) |
| Rooster vs Abyssal | DFRAG Invitational 2026 | 2026-10-27T03:00:00Z | Abyssal | Abyssal 52.2% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| HOTU vs The Huns | Moscow Cyber Games 2026 | 2026-10-31T09:00:00Z | HOTU | HOTU 94.1% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| 5star vs 1WIN | Moscow Cyber Games 2026 | 2026-10-31T13:00:00Z | 1WIN | 1WIN 82.2% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |

- `1081605` Phantom Academy vs Banda chuya: None
- `1082996` Acend vs UNiTY: None
- `1079198` Metizport vs BakS: None
- `1079199` Infinite vs BRUTE: None
- `1079200` Color vs ex-Zero Tenacity: None
- `1082858` Ground Zero vs Off Chops: None
- `1082861` Rooster vs Abyssal: None
- `1082792` HOTU vs The Huns: None
- `1082793` 5star vs 1WIN: None

## Inventory basis

Every CS2 record returned by Hotspawn’s scheduled-fixture API, reconciled with both official lobby payloads. Future starts are separate from past-start source anomalies. Coverage is not a claim that all rows have verified probabilities.. Cross-check: complete.
