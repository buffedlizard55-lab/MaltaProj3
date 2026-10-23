# Line-source research for fixtures without a betting line — arena-46ade650

Observed 2026-10-23T04:57:52Z (github-actions-runner). Targets: 9 fixtures with no external line in snapshot 2026-10-23T04:57:03Z (freshly collected in this run).

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
| Betano CS2 (https://www.betano.com/esports/counter-strike-2/) | ConnectionError: HTTPSConnectionPool(host='www.betano.mx', port=443): Max retries exceeded with url: /esports/counter-strike-2/ (Caused by NameResolutionError("HTTPSConnection(host='www.betano.mx', port=443): Failed to resolve 'www.betano.mx' ([Errno | — | — |
| Betsson CS2 (https://www.betsson.com/en/sports/esports/counter-strike) | 202 | — | — |
| Unibet CS2 (https://www.unibet.com/betting/sports/filter/counter_strike_2) | 503 | — | — |
| Oddspedia CS2 (https://oddspedia.com/esports/counter-strike) | 410 | Color, Infinite | challenge-platform, captcha |
| 22bet CS2 (https://22bet.com/line/counter-strike-2) | 200 | Color | captcha |
| Bet365 esports (https://www.bet365.com/#/AS/B18/) | 403 | Color | — |
| HLTV search endpoint (https://www.hltv.org/search?query=counter-strike) | 403 | Color | just a moment, challenge-platform, enable javascript and cookies |
| bo3.gg matches (https://bo3.gg/matches) | 200 | Color, Infinite | captcha |
| EGamersWorld CS2 odds (https://egamersworld.com/counter-strike/betting) | 403 | Color | just a moment, challenge-platform, enable javascript and cookies |

Pinnacle guest API: 20055 esports matchups, 0 target-fixture hits

**New money-line leads: 0** of 9 target fixtures.
