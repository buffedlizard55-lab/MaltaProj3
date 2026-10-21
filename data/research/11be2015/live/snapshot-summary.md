## 11B branch live snapshot
- generated_at: `2026-10-21T20:39:42Z`
- inventory_observed_at: `2026-10-21T20:39:32Z`
- coverage_complete: `True` run_status: `partial-picks`
- counts: `{"archived": 62, "bookmaker": 0, "inventory": 75, "market": 2, "model": 5, "no_edge": 0, "picks": 7, "unknown_schedule": 0, "unresolved": 6, "upcoming": 13}`
- origination counts: `{"active": 13, "alias_joined": 2, "bookmaker": 0, "consensus": 1, "guidance": 0, "market": 2, "model": 8, "reference": 0, "resolved": 11, "unresolved": 2, "with_pick": 10}`
- unresolved ids: `['1081597', '1082860']`

| id | start (UTC) | match | featured method | pick | probabilities | complete method |
| --- | --- | --- | --- | --- | --- | --- |
| 1082837 | 2026-10-21T22:00:00Z | Zetta vs LOS NINOS | unresolved |  |  | consensus | 11.8% / 88.2% | pick_index=1 |
| 1081870 | 2026-10-22T05:00:00Z | Vitalem Aerem vs Rare Atom | model | Rare Atom | 26.2% / 73.8% | model | 26.2% / 73.8% | pick_index=1 |
| 1081597 | 2026-10-22T11:00:00Z | benched gods vs TitanFlow | unresolved |  |  | unresolved |  | pick_index=None |
| 1081600 | 2026-10-22T13:45:00Z | Donstu vs Banda chuya | model | Banda chuya | 40.5% / 59.5% | model | 40.5% / 59.5% | pick_index=1 |
| 1082688 | 2026-10-22T14:00:00Z | Imperial vs Turma do Pagode | market | Imperial | 77.0% / 23.0% | market | 77.0% / 23.0% | pick_index=0 |
| 1082689 | 2026-10-22T14:00:00Z | BESTIA vs ShindeN | market | BESTIA | 52.5% / 47.5% | market | 52.5% / 47.5% | pick_index=0 |
| 1082882 | 2026-10-22T14:00:00Z | UNiTY vs Apogee Betclic | unresolved |  |  | model | 38.6% / 61.4% | pick_index=1 |
| 1082858 | 2026-10-26T03:00:00Z | Ground Zero vs Off Chops | unresolved |  |  | model | 50.0% / 50.0% | pick_index=None |
| 1082859 | 2026-10-26T03:00:00Z | NEXVOID vs Alter Ego | model | NEXVOID | 72.8% / 27.2% | model | 72.8% / 27.2% | pick_index=0 |
| 1082860 | 2026-10-27T03:00:00Z | FlyQuest vs Staqued | unresolved |  |  | unresolved |  | pick_index=None |
| 1082861 | 2026-10-27T03:00:00Z | Rooster vs Abyssal | model | Abyssal | 47.8% / 52.2% | model | 47.8% / 52.2% | pick_index=1 |
| 1082792 | 2026-10-31T09:00:00Z | HOTU vs The Huns | unresolved |  |  | model | 94.1% / 5.9% | pick_index=0 |
| 1082793 | 2026-10-31T13:00:00Z | 5star vs 1WIN | model | 1WIN | 17.8% / 82.2% | model | 17.8% / 82.2% | pick_index=1 |

### Flags in this snapshot
- `past-scheduled` (warning): Past-start records still marked scheduled
- `missing-format` (warning): Hotspawn series format is unverified
- `lock-policy` (warning): Published lock rule differs from fixture data
- `source-gg-bet-esportsbook` (warning): GG.BET esportsbook: source limitation
- `source-pinnacle-esportsbook` (warning): Pinnacle esportsbook: source limitation
- `source-rivalry-esportsbook` (warning): Rivalry esportsbook: source limitation
- `source-stake-esportsbook` (warning): Stake esportsbook: source limitation
- `model-limitations` (notice): Research estimates are not verified betting odds
- `unresolved-1082837` (warning): Unresolved: Zetta vs LOS NINOS
- `unresolved-1081597` (warning): Unresolved: benched gods vs TitanFlow
- `unresolved-1082882` (warning): Unresolved: UNiTY vs Apogee Betclic
- `unresolved-1082858` (warning): Unresolved: Ground Zero vs Off Chops
- `unresolved-1082860` (warning): Unresolved: FlyQuest vs Staqued
- `unresolved-1082792` (warning): Unresolved: HOTU vs The Huns
- `legacy-snapshots` (notice): Earlier session snapshots are archived, not the current feed

### Source health
- Hotspawn match inventory: ok (All CS2 fixture IDs reconciled across the lobby, CS2 lobby and public fixture array. No client-side pagination is used by the inspected public client.)
- Polymarket CS2: ok (Public directory plus paginated official CS2-tag events used for discovery. Every selected fixture is rechecked against its original Gamma event and both order books; directory/outcome prices are never probability inputs.)
- HLTV fallback research: ok (Split-anchor match cards parsed and saved for replay. Exact fixture identities and independently published series formats only. Fan votes are not probabilities; no bookmaker line is accepted without original-source prices.)
- Thunderpick esportsbook: ok (Only active prematch CS2 match-winner markets with exact team/time alignment and two decimal odds are eligible.)
- GG.BET esportsbook: unavailable (ggbet-cs2: 403 Client Error: Forbidden for url: https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike)
- Pinnacle esportsbook: unavailable (Redirected to a generic landing page; no match-level betting lines verified.)
- Rivalry esportsbook: unavailable (Redirected to a generic landing page; no match-level betting lines verified.)
- Stake esportsbook: unavailable (stake-cs2: 403 Client Error: Forbidden for url: https://stake.com/sports/esports/counter-strike)
- Valve official rating fallback: ok (Used only after primary markets, HLTV research and book checks fail to resolve a match. Duplicate team names, incomplete rosters or snapshots older than 35 days are rejected. Probabilities are labeled uncalibrated research estimates.)
