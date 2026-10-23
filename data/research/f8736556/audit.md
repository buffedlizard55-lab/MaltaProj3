# Public Hotspawn CS2 publication and pick-coverage audit — 23 October 2026

Observed 2026-10-23T12:07:06Z (github-actions-runner). This is a dated audit, not a replacement picks feed. Use the live executive summary and complete picks list for current picks.

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
| page_and_plain_latest_are_one_snapshot | pass | executive-summary stamp='2026-10-23T11:18:01Z'; plain data/latest.json generated_at='2026-10-23T11:18:01Z' |
| complete_picks_cite_this_inventory_generation | pass | complete-picks source_generated_at='2026-10-23T11:18:01Z'; data/latest.json generated_at='2026-10-23T11:18:01Z' |
| complete_picks_cite_this_inventory_observation | pass | complete-picks source_snapshot_at='2026-10-23T11:17:42Z'; data/latest.json observed_at='2026-10-23T11:17:42Z' |
| published_inventory_is_inside_eight_hours | pass | data/latest.json age at audit=0.818 hours |
| collector_asserts_complete_inventory | pass | coverage_complete=True in data/latest.json |

Duplicate-slash/query reads are recorded in `audit.json` as cache diagnostics only. They do not turn a failing plain URL into a pass.

## Coverage at the published snapshot

- Active inventory rows: **27**
- Directional picks: **27**
- External-line rows: **20**
- Research-model rows (not betting lines): **7**
- Explicitly unresolved rows: **0**
- Rows with audit problems: **0**

## Unresolved picks & limitations

No fixture was explicitly unresolved in this published snapshot.

7 row(s) carry a research-model estimate rather than an external betting line. Those rows are separately listed in `line-source-research.md`; their percentages must not be described as bookmaker odds or calibrated market probabilities.

## Every active row checked

| Hotspawn ID | Fixture | Starts (UTC) | Basis | Probabilities | Pick | Source | Problems |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1081606 | JiJieHao vs Eternal Fire | 2026-10-23T13:00:00Z | Market-implied estimate | 44.5000% / 55.5000% | Eternal Fire | https://polymarket.com/event/cs2-jjh-ef1-2026-10-23 | none |
| 1082926 | Isurus vs Hacha | 2026-10-23T13:00:00Z | Originated consensus line (median of independent money sources) | 70.7388% / 29.2612% | Isurus | https://polymarket.com/event/cs2-isg-hachae-2026-10-23 | none |
| 1082980 | LPH vs WBT Academy | 2026-10-23T13:00:00Z | Esportsbook line relayed by bo3.gg (Thunderpick, no-vig) | 37.8173% / 62.1827% | WBT Academy | https://bo3.gg/matches/lph-gaming-vs-wbt-academy-23-10-2026 | none |
| 1083014 | K27 vs Virtus.pro | 2026-10-23T13:00:00Z | Market-implied estimate | 56.5000% / 43.5000% | K27 | https://polymarket.com/event/cs2-k271-vp-2026-10-23 | none |
| 1082924 | BORRACHEIROS vs QUINTESSÊNCIA | 2026-10-23T16:00:00Z | Market-implied estimate | 64.0000% / 36.0000% | BORRACHEIROS | https://polymarket.com/event/cs2-chama-quin-2026-10-23 | none |
| 1079657 | BakS vs BRUTE | 2026-10-23T17:00:00Z | Originated consensus line (median of independent money sources) | 49.2439% / 50.7561% | BRUTE | https://polymarket.com/event/cs2-brute-baks-2026-10-23 | none |
| 1081150 | ex-RUSTEC vs Saint Sinners | 2026-10-23T17:00:00Z | Market-implied estimate | 66.0000% / 34.0000% | ex-RUSTEC | https://polymarket.com/event/cs2-rustec-ssins-2026-10-23 | none |
| 1082693 | BESTIA vs Galorys | 2026-10-23T18:00:00Z | Market-implied estimate | 56.5000% / 43.5000% | BESTIA | https://polymarket.com/event/cs2-bst-gls1-2026-10-23 | none |
| 1082925 | BESTIA Academy vs RED Canids Academy | 2026-10-23T19:00:00Z | Market-implied estimate | 40.5000% / 59.5000% | RED Canids Academy | https://polymarket.com/event/cs2-bsta-reda-2026-10-23 | none |
| 1083025 | paiN vs Imperial | 2026-10-23T21:00:00Z | Market-implied estimate | 30.5000% / 69.5000% | Imperial | https://polymarket.com/event/cs2-pain-imp11-2026-10-23 | none |
| 1082923 | Alka vs LOS NINOS | 2026-10-23T22:00:00Z | No-vig bookmaker estimate | 71.1111% / 28.8889% | Alka | https://thunderpick.io/api/matches | none |
| 1079193 | FOKUS vs ex-6666 | 2026-10-24T08:00:00Z | Market-implied estimate | 76.0000% / 24.0000% | FOKUS | https://polymarket.com/event/cs2-fokus-66661-2026-10-24 | none |
| 1079195 | Nuclear TigeRES vs FORZE Reload | 2026-10-24T14:00:00Z | Market-implied estimate | 61.0000% / 39.0000% | Nuclear TigeRES | https://polymarket.com/event/cs2-ntr-forzer-2026-10-24 | none |
| 1082996 | Acend vs UNiTY | 2026-10-25T09:00:00Z | Valve-rating research estimate | 54.1902% / 45.8098% | Acend | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1079198 | Metizport vs BakS | 2026-10-25T12:00:00Z | Valve-rating research estimate | 79.8606% / 20.1394% | Metizport | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1079199 | Infinite vs BRUTE | 2026-10-25T15:00:00Z | Market-implied estimate | 45.5000% / 54.5000% | BRUTE | https://polymarket.com/event/cs2-inf6-brute-2026-10-25 | none |
| 1079200 | Color vs ex-Zero Tenacity | 2026-10-25T18:00:00Z | Valve-rating research estimate | 73.5907% / 26.4093% | Color | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1082858 | Ground Zero vs Off Chops | 2026-10-26T03:00:00Z | Own network estimate (bo3.gg results graph) | 44.9231% / 55.0769% | Off Chops | https://bo3.gg/matches | none |
| 1082859 | NEXVOID vs Alter Ego | 2026-10-26T03:00:00Z | No-vig bookmaker estimate | 57.5597% / 42.4403% | NEXVOID | https://thunderpick.io/api/matches | none |
| 1082860 | FlyQuest vs Staqued | 2026-10-27T03:00:00Z | No-vig bookmaker estimate | 92.3006% / 7.6994% | FlyQuest | https://thunderpick.io/api/matches | none |
| 1082861 | Rooster vs Abyssal | 2026-10-27T03:00:00Z | Valve-rating research estimate | 47.7615% / 52.2385% | Abyssal | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1082897 | B8 vs K27 | 2026-10-27T08:00:00Z | Market-implied estimate | 62.0000% / 38.0000% | B8 | https://polymarket.com/event/cs2-b8-k271-2026-10-27 | none |
| 1082898 | Alliance vs FaZe | 2026-10-27T11:00:00Z | Market-implied estimate | 34.0000% / 66.0000% | FaZe | https://polymarket.com/event/cs2-all-faze-2026-10-27 | none |
| 1082900 | Luminosity vs HOTU | 2026-10-27T17:00:00Z | Market-implied estimate | 55.0000% / 45.0000% | Luminosity | https://polymarket.com/event/cs2-lg6-hotu-2026-10-27 | none |
| 1082901 | Envy vs GamerLegion | 2026-10-27T20:00:00Z | Market-implied estimate | 46.5000% / 53.5000% | GamerLegion | https://polymarket.com/event/cs2-envy-gl1-2026-10-27 | none |
| 1082792 | HOTU vs The Huns | 2026-10-31T09:00:00Z | Research model estimate (Valve official ratings) | 94.0521% / 5.9479% | HOTU | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |
| 1082793 | 5star vs 1WIN | 2026-10-31T13:00:00Z | Valve-rating research estimate | 17.8169% / 82.1831% | 1WIN | https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md | none |

## Limitations

- Hotspawn is used for fixture identity only; Hotspawn participation and HLTV fan votes are not probability inputs.
- HLTV evidence can confirm identity, schedule, format or ranking context; it is not treated as a two-sided bookmaker price.
- A book/aggregator outage, 403, challenge page or generic landing page proves only that this audit could not read a price there; it does not prove no market exists.
- Research-model percentages are uncalibrated estimates, not official odds and not betting advice.
- Fixtures and prices change. This dated audit must not replace the live four-hour publisher output.

## Findings

- Hotspawn official inventory changed after publication: added=['1083045']; removed=[]
