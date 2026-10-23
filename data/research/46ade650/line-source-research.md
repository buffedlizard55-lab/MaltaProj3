# Line-source research for fixtures without a betting line — arena-46ade650

Observed 2026-10-23T06:46:53Z (github-actions-runner). Targets: 9 fixtures with no external line in snapshot 2026-10-23T06:45:22Z (freshly collected in this run).

HLTV first, then esportsbooks/aggregators. A reachable page is not a price.

| Fixture | Current basis | bo3.gg bound | Two-sided relay price | Pinnacle lists it | Verdict |
| --- | --- | --- | --- | --- | --- |
| Phantom Academy vs Banda chuya (CCT Europe 2026 Challengers #8) | Valve-rating research estimate | — | no | no | No two-sided price on any surface probed; the published research estimate and its limitation stand |
| Acend vs UNiTY (NODWIN Clutch Series #13) | Valve-rating research estimate | https://bo3.gg/matches/acend-cs2-vs-unity-25-10-2026 | no | no | No two-sided price on any surface probed; the published research estimate and its limitation stand |
| Metizport vs BakS (NODWIN Clutch Series #13) | Valve-rating research estimate | https://bo3.gg/matches/metizport-vs-baks-esports-25-10-2026 | no | no | No two-sided price on any surface probed; the published research estimate and its limitation stand |
| Infinite vs BRUTE (NODWIN Clutch Series #13) | Research model estimate (Valve official ratings) | https://bo3.gg/matches/infinite-gaming-vs-brute-25-10-2026 | no | no | No two-sided price on any surface probed; the published research estimate and its limitation stand |
| Color vs ex-Zero Tenacity (NODWIN Clutch Series #13) | Valve-rating research estimate | https://bo3.gg/matches/color-vs-ex-zero-tenacity-25-10-2026 | no | no | No two-sided price on any surface probed; the published research estimate and its limitation stand |
| Ground Zero vs Off Chops (DFRAG Invitational 2026) | Own network estimate (bo3.gg results graph) | https://bo3.gg/matches/ground-zero-vs-off-chops-26-10-2026 | no | no | No two-sided price on any surface probed; the published research estimate and its limitation stand |
| Rooster vs Abyssal (DFRAG Invitational 2026) | Valve-rating research estimate | https://bo3.gg/matches/rooster-vs-abyssal-27-10-2026 | no | no | No two-sided price on any surface probed; the published research estimate and its limitation stand |
| HOTU vs The Huns (Moscow Cyber Games 2026) | Research model estimate (Valve official ratings) | — | no | no | No two-sided price on any surface probed; the published research estimate and its limitation stand |
| 5star vs 1WIN (Moscow Cyber Games 2026) | Valve-rating research estimate | — | no | no | No two-sided price on any surface probed; the published research estimate and its limitation stand |

## Surfaces probed

| Source | HTTP | Teams found | Challenge |
| --- | --- | --- | --- |
| Rivalry CS2 (https://www.rivalry.com/esports/counter-strike-2) | 200 | Color | challenge-platform |
| Betano CS2 (https://www.betano.com/esports/counter-strike-2/) | 200 | Color | challenge-platform |
| Betsson CS2 (https://www.betsson.com/en/sports/esports/counter-strike) | 202 | — | — |
| Unibet CS2 (https://www.unibet.com/betting/sports/filter/counter_strike_2) | 503 | — | — |
| Oddspedia CS2 (https://oddspedia.com/esports/counter-strike) | 410 | Color, Infinite | challenge-platform, captcha |
| 22bet CS2 (https://22bet.com/line/counter-strike-2) | 203 | — | captcha, access denied |
| Bet365 esports (https://www.bet365.com/#/AS/B18/) | 403 | Color | just a moment, challenge-platform, enable javascript and cookies |
| HLTV search endpoint (https://www.hltv.org/search?query=counter-strike) | 403 | Color | just a moment, challenge-platform, enable javascript and cookies |
| bo3.gg matches (https://bo3.gg/matches) | 200 | Color, Infinite | captcha |
| EGamersWorld CS2 odds (https://egamersworld.com/counter-strike/betting) | 403 | — | challenge-platform, attention required, captcha |

## Smarkets exchange board

Evidence: `data/origination/evidence/live-smarkets-cs.json` (observed 2026-10-23T06:45:34Z) — 12 fixture(s) bound, 9 with a two-sided quote.
- `1079654` ex-Zero Tenacity vs ex-RUSTEC — https://smarkets.com/sport/esports/cs-go/cct-europe/playoffs/2026/10/23/08-00/ex-zero-tenacity-vs-ex-rustec
- `1079655` Nuclear TigeRES vs ILLYRIANS — https://smarkets.com/sport/esports/cs-go/cct-europe/playoffs/2026/10/23/11-00/nuclear-tigeres-vs-illyrians
- `1081148` Inner Circle Academy vs Spirit Academy — https://smarkets.com/sport/esports/cs-go/cct-europe/group-stage/2026/10/23/11-00/inner-circle-academy-vs-spirit-academy
- `1081606` JiJieHao vs Eternal Fire — https://smarkets.com/sport/esports/cs-go/draculan/playoffs/2026/10/23/13-00/jijiehao-vs-eternal-fire
- `1083014` K27 vs Virtus.pro — https://smarkets.com/sport/esports/cs-go/cis-lan-championship/playoffs/2026/10/23/13-00/k27-vs-virtus-pro
- `1082924` BORRACHEIROS vs QUINTESSÊNCIA — https://smarkets.com/sport/esports/cs-go/cct-south-america/playoffs/2026/10/23/16-00/borracheiros-vs-quintessencia
- `1081150` ex-RUSTEC vs Saint Sinners — https://smarkets.com/sport/esports/cs-go/cct-europe/group-stage/2026/10/23/17-00/ex-rustec-vs-saint-sinners
- `1082693` BESTIA vs Galorys — https://smarkets.com/sport/esports/cs-go/circuit-x/playoffs/2026/10/23/18-00/bestia-vs-galorys
- `1082925` BESTIA Academy vs RED Canids Academy — https://smarkets.com/sport/esports/cs-go/cct-south-america/playoffs/2026/10/23/19-00/bestia-academy-vs-red-canids-academy
- `1083025` paiN vs Imperial — https://smarkets.com/sport/esports/cs-go/circuit-x/playoffs/2026/10/23/21-00/pain-vs-imperial
- `1079193` FOKUS vs ex-6666 — https://smarkets.com/sport/esports/cs-go/nodwin-clutch-series/playoffs/2026/10/24/08-00/fokus-vs-ex-6666
- `1079195` Nuclear TigeRES vs FORZE Reload — https://smarkets.com/sport/esports/cs-go/nodwin-clutch-series/playoffs/2026/10/24/14-00/nuclear-tigeres-vs-forze-reload

Pinnacle guest API: 20664 esports matchups, 0 target-fixture hits

**New money-line leads: 0** of 9 target fixtures.
