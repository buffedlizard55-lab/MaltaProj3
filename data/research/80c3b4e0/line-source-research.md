# Line-source research for fixtures without a betting line — arena-80c3b4e0

Observed 2026-10-23T10:16:21Z (github-actions-runner). Targets: 8 fixtures with no external line in snapshot 2026-10-23T10:15:03Z (freshly collected in this run).

HLTV first, then esportsbooks and exchanges (with competition-scoped Smarkets alias binding).

| Fixture | Current basis | HLTV match | bo3.gg bound | Smarkets exchange | Pinnacle | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Phantom Academy vs Banda chuya (CCT Europe 2026 Challengers #8) | Valve-rating research estimate | https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8 | — | — | no | No two-sided price on any surface probed; published HLTV/Valve/network research estimate stands |
| Acend vs UNiTY (NODWIN Clutch Series #13) | Valve-rating research estimate | https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13 | https://bo3.gg/matches/acend-cs2-vs-unity-25-10-2026 | Acend vs UNiTY esports (empty book) | no | EXCHANGE EVENT OPEN (EMPTY BOOK): Smarkets bound via scoped alias; awaiting two-sided liquidity |
| Metizport vs BakS (NODWIN Clutch Series #13) | Valve-rating research estimate | https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13 | https://bo3.gg/matches/metizport-vs-baks-esports-25-10-2026 | — | no | No two-sided price on any surface probed; published HLTV/Valve/network research estimate stands |
| Color vs ex-Zero Tenacity (NODWIN Clutch Series #13) | Valve-rating research estimate | https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13 | https://bo3.gg/matches/color-vs-ex-zero-tenacity-25-10-2026 | — | no | No two-sided price on any surface probed; published HLTV/Valve/network research estimate stands |
| Ground Zero vs Off Chops (DFRAG Invitational 2026) | Own network estimate (bo3.gg results graph) | https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026 | https://bo3.gg/matches/ground-zero-vs-off-chops-26-10-2026 | Ground Zero vs Off Chops (empty book) | no | EXCHANGE EVENT OPEN (EMPTY BOOK): Smarkets bound via scoped alias; awaiting two-sided liquidity |
| Rooster vs Abyssal (DFRAG Invitational 2026) | Valve-rating research estimate | https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026 | https://bo3.gg/matches/rooster-vs-abyssal-27-10-2026 | — | no | No two-sided price on any surface probed; published HLTV/Valve/network research estimate stands |
| HOTU vs The Huns (Moscow Cyber Games 2026) | Research model estimate (Valve official ratings) | https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026 | — | — | no | No two-sided price on any surface probed; published HLTV/Valve/network research estimate stands |
| 5star vs 1WIN (Moscow Cyber Games 2026) | Valve-rating research estimate | https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026 | — | — | no | No two-sided price on any surface probed; published HLTV/Valve/network research estimate stands |

## Smarkets exchange board (with competition-scoped alias binding)

Evidence: `data/origination/evidence/live-smarkets-cs.json` (observed 2026-10-23T10:15:12Z) — 15 fixture(s) bound (3 via competition-scoped aliases), 12 with a two-sided quote.
- `1079655` Nuclear TigeRES vs ILLYRIANS — https://smarkets.com/sport/esports/cs-go/cct-europe/playoffs/2026/10/23/11-00/nuclear-tigeres-vs-illyrians
- `1081148` Inner Circle Academy vs Spirit Academy — https://smarkets.com/sport/esports/cs-go/cct-europe/group-stage/2026/10/23/11-00/inner-circle-academy-vs-spirit-academy
- `1081606` JiJieHao vs Eternal Fire — https://smarkets.com/sport/esports/cs-go/draculan/playoffs/2026/10/23/13-00/jijiehao-vs-eternal-fire
- `1082926` Isurus vs Hacha Esports [alias: Hacha Esports -> Hacha] — https://smarkets.com/sport/esports/cs-go/cct-south-america/playoffs/2026/10/23/13-00/isurus-vs-hacha-esports
- `1083014` K27 vs Virtus.pro — https://smarkets.com/sport/esports/cs-go/cis-lan-championship/playoffs/2026/10/23/13-00/k27-vs-virtus-pro
- `1082924` BORRACHEIROS vs QUINTESSÊNCIA — https://smarkets.com/sport/esports/cs-go/cct-south-america/playoffs/2026/10/23/16-00/borracheiros-vs-quintessencia
- `1079657` Brute vs BakS eSports [alias: BakS eSports -> BakS] — https://smarkets.com/sport/esports/cs-go/cct-europe/playoffs/2026/10/23/17-00/brute-vs-baks-esports
- `1081150` ex-RUSTEC vs Saint Sinners — https://smarkets.com/sport/esports/cs-go/cct-europe/group-stage/2026/10/23/17-00/ex-rustec-vs-saint-sinners
- `1082693` BESTIA vs Galorys — https://smarkets.com/sport/esports/cs-go/circuit-x/playoffs/2026/10/23/18-00/bestia-vs-galorys
- `1082925` BESTIA Academy vs RED Canids Academy — https://smarkets.com/sport/esports/cs-go/cct-south-america/playoffs/2026/10/23/19-00/bestia-academy-vs-red-canids-academy
- `1083025` paiN vs Imperial — https://smarkets.com/sport/esports/cs-go/circuit-x/playoffs/2026/10/23/21-00/pain-vs-imperial
- `1079193` FOKUS vs ex-6666 — https://smarkets.com/sport/esports/cs-go/nodwin-clutch-series/playoffs/2026/10/24/08-00/fokus-vs-ex-6666
- `1079195` Nuclear TigeRES vs FORZE Reload — https://smarkets.com/sport/esports/cs-go/nodwin-clutch-series/playoffs/2026/10/24/14-00/nuclear-tigeres-vs-forze-reload
- `1082996` Acend vs UNiTY esports [alias: UNiTY esports -> UNiTY] — https://smarkets.com/sport/esports/cs-go/nodwin-clutch-series/playoffs/2026/10/25/09-00/acend-vs-unity-esports
- `1082858` Ground Zero vs Off Chops — https://smarkets.com/sport/esports/cs-go/dfrag-invitational/group-a/2026/10/26/03-00/ground-zero-vs-off-chops

**Money-line / exchange-quote leads: 0** of 8 target fixtures.
