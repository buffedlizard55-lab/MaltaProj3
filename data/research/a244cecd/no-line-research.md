# arena-a244cecd — HLTV-first, then exchange research for the 7 model-only fixtures (2026-10-24)

Observed 2026-10-24 05:28Z–05:50Z from Arena platform egress (HLTV returns 403 to the GitHub runner, so it is read here).
**Leads and limitations only — no probability, pick or alias was written by hand.** Hotspawn "% picked" and HLTV fan polls are excluded.
Machine-readable record: [`no-line-research.json`](no-line-research.json) · flags: [`flags.json`](flags.json) (auto-published on `/review/`).

| Hotspawn | Fixture | HLTV (read first) | Polymarket series market | Smarkets | Result |
| --- | --- | --- | --- | --- | --- |
| [1082996](https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996) | Acend vs UNiTY | [BO3 online, no odds](https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13) | [6072790](https://gamma-api.polymarket.com/markets/6072790) 0.11/0.94 (spread 0.83) | [172971947](https://api.smarkets.com/v3/markets/172971947/quotes/) spreads 0.161/0.164, leans UNiTY | no compliant line; direction conflict with model |
| [1079198](https://www.hotspawn.com/matches/metizport-vs-baks-nodwin-clutch-series-13-1079198) | Metizport vs BakS | [BO3 online, no odds](https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13) | [6072799](https://gamma-api.polymarket.com/markets/6072799) 0.55/0.86 (0.31) | — | no compliant line |
| [1079200](https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200) | Color vs ex-Zero Tenacity | [BO3 online, no odds](https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13) | [6072812](https://gamma-api.polymarket.com/markets/6072812) 0.47/0.62 (**0.15 = ceiling**) | — | lead for next refresh (pipeline decides) |
| [1082858](https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858) | Ground Zero vs Off Chops | [BO3 LAN, no odds](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026) | [6066508](https://gamma-api.polymarket.com/markets?id=6066508) GZ 0.13/0.45 (0.32) | [172960355](https://api.smarkets.com/v3/markets/172960355/quotes/) spreads 0.161/0.167 | no compliant line |
| [1082861](https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861) | Rooster vs Abyssal | [BO3 LAN, no odds](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026) | [6066525](https://gamma-api.polymarket.com/markets/6066525) 0.04/0.96 (0.92) | — | no compliant line |
| [1082792](https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792) | HOTU vs The Huns | [BO3 LAN SF, no odds](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) | not located | — | no market yet (7 days out) |
| [1082793](https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793) | 5star vs 1WIN | [BO3 LAN SF, no odds](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026) | not located | — | no market yet (7 days out) |

Irregularity: Polymarket 6072788 and 6066523, cited in earlier notes for Acend–UNiTY and Rooster–Abyssal, are **Map 1 Winner** markets (`child_moneyline`), not series markets. The pipeline already ignores map markets, so no published pick changed.
