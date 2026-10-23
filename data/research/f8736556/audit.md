# Public Hotspawn CS2 publication and pick-coverage audit — 23 October 2026

Observed 2026-10-23T10:00:08Z (github-actions-runner). This is a dated audit, not a replacement picks feed. Use the live executive summary and complete picks list for current picks.

## Where the updated picks are

- Executive summary: https://buffedlizard55-lab.github.io/MaltaProj3/
- Picks at a glance: https://buffedlizard55-lab.github.io/MaltaProj3/#picks-at-a-glance
- Every match, both probabilities and sources: https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks
- Unresolved picks and limitations inside the summary: https://buffedlizard55-lab.github.io/MaltaProj3/#unresolved-register
- Dedicated unresolved page: https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/
- Flagged for Review: https://buffedlizard55-lab.github.io/MaltaProj3/review/

## Publication parity (plain public URLs)

| Check | Result | Evidence |
| --- | --- | --- |
| page_and_plain_latest_are_one_snapshot | fail | executive-summary stamp='2026-10-23T09:23:57Z'; plain data/latest.json generated_at='2026-10-15T08:36:13Z' |
| complete_picks_cite_this_inventory_generation | pass | complete-picks source_generated_at='2026-10-15T08:36:13Z'; inventory generated_at='2026-10-15T08:36:13Z' |
| complete_picks_cite_this_inventory_observation | pass | complete-picks source_snapshot_at='2026-10-15T08:36:04Z'; inventory observed_at='2026-10-15T08:36:04Z' |
| published_inventory_is_inside_eight_hours | fail | inventory age at audit=193.399 hours |
| collector_asserts_complete_inventory | pass | coverage_complete=True |

Duplicate-slash/query reads are recorded in `audit.json` as cache diagnostics only. They do not turn a failing plain URL into a pass.

## Coverage at the published snapshot

- Active inventory rows: **17**
- Directional picks: **17**
- External-line rows: **12**
- Research-model rows (not betting lines): **5**
- Explicitly unresolved rows: **0**
- Rows with audit problems: **0**

## Unresolved picks & limitations

No fixture was explicitly unresolved in this published snapshot.

5 row(s) carry a research-model estimate rather than an external betting line. Those rows are separately listed in `line-source-research.md`; their percentages must not be described as bookmaker odds or calibrated market probabilities.

## Every active row checked

| Hotspawn ID | Fixture | Starts (UTC) | Basis | Probabilities | Pick | Source | Problems |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1079440 | MIBR vs BC.Game | 2026-10-15T10:00:00Z | No-vig bookmaker estimate | 54.9598% / 45.0402% | MIBR | https://thunderpick.io/api/matches | none |
| 1079442 | Heroic vs Envy | 2026-10-15T10:00:00Z | Market-implied estimate | 63.5000% / 36.5000% | Heroic | https://polymarket.com/event/cs2-hero-envy-2026-10-15 | none |
| 1080280 | ENCE vs BOJONG | 2026-10-15T10:00:00Z | Market-implied estimate | 74.5000% / 25.5000% | ENCE | https://polymarket.com/event/cs2-ence-bojong-2026-10-15 | none |
| 1080202 | 9z vs Falcons | 2026-10-15T11:00:00Z | Valve-rating research estimate | 15.7095% / 84.2905% | Falcons | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1080281 | WROTBERRY vs ENCE | 2026-10-15T12:00:00Z | Originated esportsbook line (no-vig) | 61.5385% / 38.4615% | WROTBERRY | https://thunderpick.io/esports/counter-strike | none |
| 1080203 | PARIVISION vs BetBoom | 2026-10-15T13:30:00Z | Valve-rating research estimate | 26.1922% / 73.8078% | BetBoom | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1080282 | EAC vs BOJONG | 2026-10-15T14:00:00Z | Valve-rating research estimate | 96.0955% / 3.9045% | EAC | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1080204 | Legacy vs FURIA | 2026-10-15T16:00:00Z | Market-implied estimate | 43.5000% / 56.5000% | FURIA | https://polymarket.com/event/cs2-lgc-furia-2026-10-15 | none |
| 1080283 | WROTBERRY vs BOJONG | 2026-10-15T16:00:00Z | Originated esportsbook line (no-vig) | 76.9231% / 23.0769% | WROTBERRY | https://thunderpick.io/esports/counter-strike | none |
| 1080284 | EAC vs ENCE | 2026-10-15T18:00:00Z | Valve-rating research estimate | 51.3996% / 48.6004% | EAC | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1080285 | Voca vs Phantom | 2026-10-16T08:00:00Z | Market-implied estimate | 44.5000% / 55.5000% | Phantom | https://polymarket.com/event/cs2-voc-pha-2026-10-16 | none |
| 1080286 | HAVU vs RoundsGG | 2026-10-16T10:00:00Z | Originated esportsbook line (no-vig) | 76.9231% / 23.0769% | HAVU | https://thunderpick.io/esports/counter-strike | none |
| 1080287 | Voca vs HAVU | 2026-10-16T12:00:00Z | Market-implied estimate | 65.5000% / 34.5000% | Voca | https://polymarket.com/event/cs2-voc-havu-2026-10-16 | none |
| 1080288 | Phantom vs RoundsGG | 2026-10-16T14:00:00Z | Market-implied estimate | 92.0000% / 8.0000% | Phantom | https://polymarket.com/event/cs2-pha-rgg-2026-10-16 | none |
| 1081120 | mellren vs Privateer | 2026-10-16T14:00:00Z | Valve-rating research estimate | 85.9893% / 14.0107% | mellren | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1080289 | RoundsGG vs Voca | 2026-10-16T16:00:00Z | Originated esportsbook line (no-vig) | 15.9420% / 84.0580% | Voca | https://thunderpick.io/esports/counter-strike | none |
| 1080290 | Phantom vs HAVU | 2026-10-16T18:00:00Z | Market-implied estimate | 70.5000% / 29.5000% | Phantom | https://polymarket.com/event/cs2-pha-havu-2026-10-16 | none |

## Limitations

- Hotspawn is used for fixture identity only; Hotspawn participation and HLTV fan votes are not probability inputs.
- HLTV evidence can confirm identity, schedule, format or ranking context; it is not treated as a two-sided bookmaker price.
- A book/aggregator outage, 403, challenge page or generic landing page proves only that this audit could not read a price there; it does not prove no market exists.
- Research-model percentages are uncalibrated estimates, not official odds and not betting advice.
- Fixtures and prices change. This dated audit must not replace the live four-hour publisher output.

## Findings

- Publication check failed: page_and_plain_latest_are_one_snapshot (executive-summary stamp='2026-10-23T09:23:57Z'; plain data/latest.json generated_at='2026-10-15T08:36:13Z')
- Publication check failed: published_inventory_is_inside_eight_hours (inventory age at audit=193.399 hours)
- Public executive-summary glance IDs do not exactly match active inventory IDs
- Hotspawn official inventory changed after publication: added=['1079193', '1079195', '1079198', '1079199', '1079200', '1079654', '1079655', '1079657', '1081148', '1081150', '1081605', '1081606', '1082693', '1082792', '1082793', '1082858', '1082859', '1082860', '1082861', '1082897', '1082898', '1082900', '1082901', '1082923', '1082924', '1082925', '1082926', '1082980', '1082996', '1083014', '1083025']; removed=['1079440', '1079442', '1080201', '1080202', '1080203', '1080204', '1080279', '1080280', '1080281', '1080282', '1080283', '1080284', '1080285', '1080286', '1080287', '1080288', '1080289', '1080290', '1081120']
