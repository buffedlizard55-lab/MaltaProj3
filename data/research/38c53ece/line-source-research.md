# Dated low-tier line research — 23 October 2026

Observed 2026-10-23T05:16:32.618732+00:00; fresh runner snapshot 2026-10-23T05:15:40Z. **Not a deployment claim.**

## Executive findings

- Official Hotspawn API: 92 records; both rendered lobby pages reconciled by the collector. Independent later API read had the same IDs.
- Complete list: **30 active fixtures, 30 directional picks, zero unresolved probabilities** at this observation. **21 external-line estimates; nine uncalibrated model estimates**, not betting lines. Saved-source replay and the complete site build passed on the runner.
- Only the nine no-line fixtures were targeted below. HLTV was attempted first, then esportsbooks and betting-line services. No new paired price verified; no pick was changed by this audit.
- Pinnacle guest API: 20,181 matchup records, none matched the target team pairs. No bo3 relay quote was found for these fixtures. HTTP success, a brand name appearing on a page, or a ranking position alone is not verified odds.
- Public deployment separately returned October 15 JSON at 05:15 UTC. See `publication-drift/audit.json`. This report deliberately does not confuse fresh collection with successful publication.

## Model-only fixtures and limitations

| Fixture | Existing model input | Limitation | Original fixture |
| --- | --- | --- | --- |
| Phantom Academy vs Banda chuya | [Source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) | Uncalibrated model, no new money line verified; roster/veto uncertainty. | [Hotspawn](https://www.hotspawn.com/matches/phantom-academy-vs-banda-chuya-cct-europe-2026-challengers-8-1081605) |
| Acend vs UNiTY | [Source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) | Uncalibrated model, no new money line verified; roster/veto uncertainty. | [Hotspawn](https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996) |
| Metizport vs BakS | [Source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) | Uncalibrated model, no new money line verified; roster/veto uncertainty. | [Hotspawn](https://www.hotspawn.com/matches/metizport-vs-baks-nodwin-clutch-series-13-1079198) |
| Infinite vs BRUTE | [Source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) | Uncalibrated model, no new money line verified; roster/veto uncertainty. | [Hotspawn](https://www.hotspawn.com/matches/infinite-vs-brute-nodwin-clutch-series-13-1079199) |
| Color vs ex-Zero Tenacity | [Source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) | Uncalibrated model, no new money line verified; roster/veto uncertainty. | [Hotspawn](https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200) |
| Ground Zero vs Off Chops | [Source](https://bo3.gg/matches) | Uncalibrated model, no new money line verified; roster/veto uncertainty. | [Hotspawn](https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858) |
| Rooster vs Abyssal | [Source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) | Uncalibrated model, no new money line verified; roster/veto uncertainty. | [Hotspawn](https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861) |
| HOTU vs The Huns | [Source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) | Uncalibrated model, no new money line verified; roster/veto uncertainty. | [Hotspawn](https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792) |
| 5star vs 1WIN | [Source](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) | Uncalibrated model, no new money line verified; roster/veto uncertainty. | [Hotspawn](https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793) |

## Source checks

| Original source | HTTP observed | Interpretation |
| --- | --- | --- |
| [HLTV match listing](https://www.hltv.org/matches) | 403 | Access/extraction observation only; not a two-sided price. |
| [HLTV world ranking](https://www.hltv.org/ranking/teams) | 403 | Access/extraction observation only; not a two-sided price. |
| [GG.BET CS2](https://gg.bet/en/counter-strike) | 403 | Access/extraction observation only; not a two-sided price. |
| [BetBoom CS2](https://betboom.ru/sport/cs2) | 401 | Access/extraction observation only; not a two-sided price. |
| [Stake CS2](https://stake.com/sports/esports/cs2) | 403 | Access/extraction observation only; not a two-sided price. |
| [BC.Game CS2](https://bc.game/sports/esports) | 200 | Access/extraction observation only; not a two-sided price. |
| [1xBet CS2](https://1xbet.com/en/line/counter-strike-2) | 203 | Access/extraction observation only; not a two-sided price. |
| [Marathonbet CS2](https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/) | 403 | Access/extraction observation only; not a two-sided price. |
| [Betway esports](https://www.betway.com/en/sports/esports/counter-strike-2) | 404 | Access/extraction observation only; not a two-sided price. |
| [DraftKings CS2](https://sportsbook.draftkings.com/leagues/esports/counter-strike-2) | 404 | Access/extraction observation only; not a two-sided price. |
| [OddsPortal CS2](https://www.oddsportal.com/esports/counter-strike/) | 429 | Access/extraction observation only; not a two-sided price. |
| [EGamersWorld CS2 matches](https://egamersworld.com/counterstrike/matches) | 403 | Access/extraction observation only; not a two-sided price. |
| [Pinnacle CS2 page](https://www.pinnacle.com/en/esports/counter-strike-2) | 404 | Access/extraction observation only; not a two-sided price. |

## Verification and manual review

- [Successful fresh collection, origination, replay, row/link audit](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39904094215).
- Full original responses: `official-inventory-response.json`, `published-inventory.json`, `published-complete-picks.json` (the last two filenames are compatibility names; this record explicitly uses a **runner collection**, not the public deployment).
- [Current picks](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks) · [Unresolved and limitations](https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/) · [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/).
- Refresh schedule is four-hourly with catch-up slots, not a guarantee of source availability or GitHub runner timing.
- No Hotspawn participation percentage, offered points or fan vote entered the probabilities. Missing official values remain blank.
