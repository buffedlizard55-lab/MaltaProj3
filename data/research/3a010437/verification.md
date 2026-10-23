# Independent verification of every published pick (session arena-3a010437)



Re-read started **2026-10-23T10:02:40Z** and finished **2026-10-23T10:02:43Z** against the snapshot collected at **2026-10-15T08:36:13Z** (17 active rows).

Each row is compared with the original source that row itself cites. Nothing is corrected here: the deltas are published so a reader can see them.

| Verdict | Rows |
| --- | --- |
| `identity_mismatch` | 12 |
| `model_not_a_line` | 5 |

## Sources used for this re-read

- Official Hotspawn fixtures API: `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` — 92 records at 2026-10-23T10:02:39Z (HTTP 200). Every row's fixture id, both team names and scheduled start time are compared with this response.
- Price rows: the row's own published `source_api` (Polymarket Gamma event) or its cited URL. A reachable non-Polymarket surface is reported as reachability only; its price is not re-derived here.
- Rendered Hotspawn match page (one probe, `https://www.hotspawn.com/matches/mibr-vs-bc-game-stake-pulse-beat-iii-1079440`): HTTP 200, title "MIBR Vs BC.Game Counter-Strike 2 Match At Stake Pulse Beat III - 1079440 - Hotspawn", readable. Identity therefore comes from the fixture API, not from the rendered page.
- Live inventory delta: 92 official records vs 80 in the audited snapshot; 31 id(s) in the API are not in the snapshot (observed 2026-10-23T10:02:44Z).

| # | Match | Method | Pick | Published | Identity (official API) | Re-read from the row's own source | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | MIBR vs BC.Game | bookmaker | MIBR | 0.550 / 0.450 | not_in_inventory | 200 reachability only · https://thunderpick.io/api/matches @ 2026-10-23T10:02:40Z | `identity_mismatch` |
| 2 | Heroic vs Envy | market | Heroic | 0.635 / 0.365 | not_in_inventory | Heroic 1.0 (+0.365 vs published); Envy 0.0 (-0.365 vs published) · `https://gamma-api.polymarket.com/events/1140039` @ 2026-10-23T10:02:40Z | `identity_mismatch` |
| 3 | ENCE vs BOJONG | market | ENCE | 0.745 / 0.255 | not_in_inventory | ENCE 1.0 (+0.255 vs published); BOJONG 0.0 (-0.255 vs published) · `https://gamma-api.polymarket.com/events/1173312` @ 2026-10-23T10:02:41Z | `identity_mismatch` |
| 4 | 9z vs Falcons | model | Falcons | 0.157 / 0.843 | not_in_inventory | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 5 | WROTBERRY vs ENCE | bookmaker | WROTBERRY | 0.615 / 0.385 | not_in_inventory | 200 reachability only · https://thunderpick.io/esports/counter-strike @ 2026-10-23T10:02:41Z | `identity_mismatch` |
| 6 | PARIVISION vs BetBoom | model | BetBoom | 0.262 / 0.738 | not_in_inventory | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 7 | EAC vs BOJONG | model | EAC | 0.961 / 0.039 | not_in_inventory | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 8 | Legacy vs FURIA | market | FURIA | 0.435 / 0.565 | not_in_inventory | Legacy 0.0 (-0.435 vs published); FURIA 1.0 (+0.435 vs published) · `https://gamma-api.polymarket.com/events/1190748` @ 2026-10-23T10:02:41Z | `identity_mismatch` |
| 9 | WROTBERRY vs BOJONG | bookmaker | WROTBERRY | 0.769 / 0.231 | not_in_inventory | 200 reachability only · https://thunderpick.io/esports/counter-strike @ 2026-10-23T10:02:41Z | `identity_mismatch` |
| 10 | EAC vs ENCE | model | EAC | 0.514 / 0.486 | not_in_inventory | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 11 | Voca vs Phantom | market | Phantom | 0.445 / 0.555 | not_in_inventory | Voca 0.0 (-0.445 vs published); Phantom 1.0 (+0.445 vs published) · `https://gamma-api.polymarket.com/events/1173317` @ 2026-10-23T10:02:41Z | `identity_mismatch` |
| 12 | HAVU vs RoundsGG | bookmaker | HAVU | 0.769 / 0.231 | not_in_inventory | 200 reachability only · https://thunderpick.io/esports/counter-strike @ 2026-10-23T10:02:42Z | `identity_mismatch` |
| 13 | Voca vs HAVU | market | Voca | 0.655 / 0.345 | not_in_inventory | Voca 0.0 (-0.655 vs published); HAVU 1.0 (+0.655 vs published) · `https://gamma-api.polymarket.com/events/1173319` @ 2026-10-23T10:02:42Z | `identity_mismatch` |
| 14 | Phantom vs RoundsGG | market | Phantom | 0.920 / 0.080 | not_in_inventory | Phantom 1.0 (+0.080 vs published); RoundsGG 0.0 (-0.080 vs published) · `https://gamma-api.polymarket.com/events/1173321` @ 2026-10-23T10:02:42Z | `identity_mismatch` |
| 15 | mellren vs Privateer | model | mellren | 0.860 / 0.140 | not_in_inventory | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 16 | RoundsGG vs Voca | bookmaker | Voca | 0.159 / 0.841 | not_in_inventory | 200 reachability only · https://thunderpick.io/esports/counter-strike @ 2026-10-23T10:02:42Z | `identity_mismatch` |
| 17 | Phantom vs HAVU | market | Phantom | 0.705 / 0.295 | not_in_inventory | Phantom 1.0 (+0.295 vs published); HAVU 0.0 (-0.295 vs published) · `https://gamma-api.polymarket.com/events/1173323` @ 2026-10-23T10:02:42Z | `identity_mismatch` |

## Flagged for review

- **MIBR vs BC.Game** (`1079440`, `identity_mismatch`) — https://thunderpick.io/api/matches
- **Heroic vs Envy** (`1079442`, `identity_mismatch`) — https://polymarket.com/event/cs2-hero-envy-2026-10-15
- **ENCE vs BOJONG** (`1080280`, `identity_mismatch`) — https://polymarket.com/event/cs2-ence-bojong-2026-10-15
- **WROTBERRY vs ENCE** (`1080281`, `identity_mismatch`) — https://thunderpick.io/esports/counter-strike
- **Legacy vs FURIA** (`1080204`, `identity_mismatch`) — https://polymarket.com/event/cs2-lgc-furia-2026-10-15
- **WROTBERRY vs BOJONG** (`1080283`, `identity_mismatch`) — https://thunderpick.io/esports/counter-strike
- **Voca vs Phantom** (`1080285`, `identity_mismatch`) — https://polymarket.com/event/cs2-voc-pha-2026-10-16
- **HAVU vs RoundsGG** (`1080286`, `identity_mismatch`) — https://thunderpick.io/esports/counter-strike
- **Voca vs HAVU** (`1080287`, `identity_mismatch`) — https://polymarket.com/event/cs2-voc-havu-2026-10-16
- **Phantom vs RoundsGG** (`1080288`, `identity_mismatch`) — https://polymarket.com/event/cs2-pha-rgg-2026-10-16
- **RoundsGG vs Voca** (`1080289`, `identity_mismatch`) — https://thunderpick.io/esports/counter-strike
- **Phantom vs HAVU** (`1080290`, `identity_mismatch`) — https://polymarket.com/event/cs2-pha-havu-2026-10-16
