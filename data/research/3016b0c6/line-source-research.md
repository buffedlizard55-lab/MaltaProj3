# Line-source research for fixtures without a betting line — arena-3016b0c6

Observed 2026-10-22T07:39:57+00:00 (github-actions-runner). Targets: 18 fixtures with no external line in snapshot 2026-10-22T05:37:07Z (live published snapshot).

HLTV first, then esportsbooks/aggregators. A reachable page is not a price.

| Fixture | Current basis | bo3.gg bound | Two-sided relay price | Pinnacle lists it | Verdict |
| --- | --- | --- | --- | --- | --- |
| BakS vs Azuolas (CCT Europe 2026 Series #12) | Valve-rating research estimate | https://bo3.gg/matches/baks-esports-vs-azuolas-22-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| Butterfly vs Lavked (CCT Europe 2026 Series #11) | Valve-rating research estimate | https://bo3.gg/matches/butterfly-vs-lavked-22-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| benched gods vs TitanFlow (CCT Europe 2026 Challengers #8) | Own network estimate (bo3.gg results graph) | https://bo3.gg/matches/benched-gods-vs-titanflow-22-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| Nemesis vs WW (CIS LAN Championship #9) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| Donstu vs Banda chuya (CCT Europe 2026 Challengers #8) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| 6yuBoJlbl vs ex-6666 (CCT Europe 2026 Series #12) | Research model estimate (Valve official ratings) | https://bo3.gg/matches/6yubojlbl-vs-ex-6666-22-10-2026 | yes | no | NEW LEAD: two-sided relayed price found — reviewed ladder must replay it before any pick changes |
| Lynn Vision vs Chinggis Warriors (VOID Autumn Cup 2026) | Research model estimate (Valve official ratings) | https://bo3.gg/matches/lynn-vision-vs-chinggis-warriors-23-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| ex-Zero Tenacity vs ex-RUSTEC (CCT Europe 2026 Series #11) | Valve-rating research estimate | https://bo3.gg/matches/ex-zero-tenacity-vs-ex-rustec-23-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| Nuclear TigeRES vs ILLYRIANS (CCT Europe 2026 Series #11) | Valve-rating research estimate | https://bo3.gg/matches/nuclear-tigeres-vs-illyrians-23-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| FORZE Reload vs LFO 10 (CCT Europe 2026 Series #12) | Research model estimate (HLTV world ranking) | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| BakS vs BRUTE (CCT Europe 2026 Series #11) | Research model estimate (Valve official ratings) | https://bo3.gg/matches/brute-vs-baks-esports-23-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| ex-RUSTEC vs Saint Sinners (CCT Europe 2026 Series #12) | Valve-rating research estimate | https://bo3.gg/matches/ex-rustec-vs-saint-sinners-23-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| Ground Zero vs Off Chops (DFRAG Invitational 2026) | Own network estimate (bo3.gg results graph) | https://bo3.gg/matches/ground-zero-vs-off-chops-26-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| NEXVOID vs Alter Ego (DFRAG Invitational 2026) | Valve-rating research estimate | https://bo3.gg/matches/nexvoid-vs-alter-ego-26-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| FlyQuest vs Staqued (DFRAG Invitational 2026) | Research model estimate (HLTV world ranking · unranked floor) | https://bo3.gg/matches/flyquest-vs-staqued-27-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| Rooster vs Abyssal (DFRAG Invitational 2026) | Valve-rating research estimate | https://bo3.gg/matches/rooster-vs-abyssal-27-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| HOTU vs The Huns (Moscow Cyber Games 2026) | Research model estimate (Valve official ratings) | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| 5star vs 1WIN (Moscow Cyber Games 2026) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |

## Surfaces probed

| Source | HTTP | Teams found | Challenge |
| --- | --- | --- | --- |
| HLTV match listing (https://www.hltv.org/matches) | 403 | — | just a moment, challenge-platform, enable javascript and cookies |
| HLTV world ranking (https://www.hltv.org/ranking/teams) | 403 | — | just a moment, challenge-platform, enable javascript and cookies |
| GG.BET CS2 (https://gg.bet/en/counter-strike) | 200 | — | just a moment, captcha |
| BetBoom CS2 (https://betboom.ru/sport/cs2) | 401 | — | captcha |
| Stake CS2 (https://stake.com/sports/esports/cs2) | 403 | — | just a moment, challenge-platform, enable javascript and cookies |
| BC.Game CS2 (https://bc.game/sports/esports) | 200 | — | challenge-platform |
| 1xBet CS2 (https://1xbet.com/en/line/counter-strike-2) | 404 | — | challenge-platform |
| Marathonbet CS2 (https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/) | 403 | — | challenge-platform, enable javascript and cookies |
| Betway esports (https://www.betway.com/en/sports/esports/counter-strike-2) | 404 | — | — |
| DraftKings CS2 (https://sportsbook.draftkings.com/leagues/esports/counter-strike-2) | 200 | — | — |
| OddsPortal CS2 (https://www.oddsportal.com/esports/counter-strike/) | 200 | — | captcha |
| EGamersWorld CS2 matches (https://egamersworld.com/counterstrike/matches) | 403 | — | just a moment, challenge-platform, enable javascript and cookies |
| Pinnacle CS2 page (https://www.pinnacle.com/en/esports/counter-strike-2) | 404 | — | — |

Pinnacle guest API: 16201 esports matchups, 0 target-fixture hits

**New money-line leads: 1** of 18 target fixtures.
