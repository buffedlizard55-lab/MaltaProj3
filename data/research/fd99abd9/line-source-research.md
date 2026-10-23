# Line-source research for fixtures without a betting line — arena-fd99abd9

Observed 2026-10-23T05:21:21+00:00 (github-actions-runner). Targets: 12 fixtures with no external line in snapshot 2026-10-22T14:05:51Z (live published snapshot).

HLTV first, then esportsbooks/aggregators. A reachable page is not a price.

| Fixture | Current basis | bo3.gg bound | Two-sided relay price | Pinnacle lists it | Verdict |
| --- | --- | --- | --- | --- | --- |
| Donstu vs Banda chuya (CCT Europe 2026 Challengers #8) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| UNiTY vs Apogee Betclic (Stake Ranked Episode 6: Closed Qualifier) | Research model estimate (HLTV world ranking) | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| NEXVOID vs Rare Atom (VOID Autumn Cup 2026) | Valve-rating research estimate | https://bo3.gg/matches/nexvoid-vs-rare-atom-23-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| Nuclear TigeRES vs ILLYRIANS (CCT Europe 2026 Series #11) | Valve-rating research estimate | https://bo3.gg/matches/nuclear-tigeres-vs-illyrians-23-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| FORZE Reload vs LFO 10 (CCT Europe 2026 Series #12) | Research model estimate (HLTV world ranking) | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| BORRACHEIROS vs QUINTESSÊNCIA (CCT South America 2026 Series #7) | Valve-rating research estimate | https://bo3.gg/matches/borracheiros-vs-quintessencia-23-10-2026 | yes | no | NEW LEAD: two-sided relayed price found — reviewed ladder must replay it before any pick changes |
| ex-RUSTEC vs Saint Sinners (CCT Europe 2026 Series #12) | Valve-rating research estimate | https://bo3.gg/matches/ex-rustec-vs-saint-sinners-23-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| Ground Zero vs Off Chops (DFRAG Invitational 2026) | Own network estimate (bo3.gg results graph) | https://bo3.gg/matches/ground-zero-vs-off-chops-26-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| FlyQuest vs Staqued (DFRAG Invitational 2026) | Research model estimate (HLTV world ranking · unranked floor) | https://bo3.gg/matches/flyquest-vs-staqued-27-10-2026 | yes | no | NEW LEAD: two-sided relayed price found — reviewed ladder must replay it before any pick changes |
| Rooster vs Abyssal (DFRAG Invitational 2026) | Valve-rating research estimate | https://bo3.gg/matches/rooster-vs-abyssal-27-10-2026 | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| HOTU vs The Huns (Moscow Cyber Games 2026) | Research model estimate (Valve official ratings) | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| 5star vs 1WIN (Moscow Cyber Games 2026) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |

## Surfaces probed

| Source | HTTP | Teams found | Challenge |
| --- | --- | --- | --- |
| HLTV match listing (https://www.hltv.org/matches) | 403 | — | just a moment, challenge-platform, enable javascript and cookies, cloudflare |
| HLTV world ranking (https://www.hltv.org/ranking/teams) | 403 | — | just a moment, challenge-platform, enable javascript and cookies, cloudflare |
| GG.BET CS2 (https://gg.bet/en/counter-strike) | 403 | — | — |
| BetBoom CS2 (https://betboom.ru/sport/cs2) | 401 | — | captcha |
| Stake CS2 (https://stake.com/sports/esports/cs2) | 403 | — | just a moment, challenge-platform, enable javascript and cookies, cloudflare |
| BC.Game CS2 (https://bc.game/sports/esports) | 200 | — | challenge-platform |
| 1xBet CS2 (https://1xbet.com/en/line/counter-strike-2) | 203 | — | challenge-platform |
| Marathonbet CS2 (https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/) | 403 | — | challenge-platform, attention required, captcha, cloudflare |
| Betway esports (https://www.betway.com/en/sports/esports/counter-strike-2) | 404 | — | — |
| DraftKings CS2 (https://sportsbook.draftkings.com/leagues/esports/counter-strike-2) | 200 | — | — |
| OddsPortal CS2 (https://www.oddsportal.com/esports/counter-strike/) | 200 | — | captcha |
| EGamersWorld CS2 matches (https://egamersworld.com/counterstrike/matches) | 403 | — | challenge-platform, attention required, captcha, cloudflare |
| Pinnacle CS2 page (https://www.pinnacle.com/en/esports/counter-strike-2) | 404 | — | — |
| Rivalry CS2 (https://www.rivalry.com/betting/counter-strike) | 200 | — | challenge-platform, cloudflare |
| Thunderpick CS2 (https://thunderpick.io/esports/counter-strike) | 200 | — | cloudflare |
| Bovada CS2 (https://www.bovada.lv/sports/esports/counter-strike-2) | 200 | — | captcha |

Pinnacle guest API: 20409 esports matchups, 0 target-fixture hits

**New money-line leads: 2** of 12 target fixtures.

Featured-method unresolved (for audit): 4 fixture(s) — WROTBERRY vs ENCE (1080281), WROTBERRY vs BOJONG (1080283), HAVU vs RoundsGG (1080286), RoundsGG vs Voca (1080289).
