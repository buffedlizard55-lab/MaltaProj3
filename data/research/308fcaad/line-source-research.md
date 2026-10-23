# Line-source research sweep — session arena-308fcaad — 2026-10-23, 06:20–07:05Z

**Scope:** the 9 active Hotspawn CS2 fixtures that carry a research-model pick with a
"No betting line" limitation in the live snapshot (`generated_at 2026-10-23T06:17:47Z`,
[unresolved register](https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/)).
**Method:** HLTV first (identity/ranking — HLTV publishes no prematch price and its fan
vote is excluded by policy), then esportsbook and exchange surfaces. Read-only; nothing
below is a probability or a pick.

**Client note:** this sweep ran through Arena's sandbox fetch client. That client read
HLTV.org directly; the GitHub Actions runner's own sweep at 06:19Z was 403-challenged by
Cloudflare on the same pages. Both facts are true of their respective clients and the
site publishes both.

## Per-fixture findings

| Fixture (Hotspawn id) | HLTV (identity, no price) | bo3.gg / Thunderpick relay | Polymarket | Result |
| --- | --- | --- | --- | --- |
| Phantom Academy vs Banda chuya (1081605, 11:00Z 23 Oct) | [match 2399699](https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8) | not listed as a priced fixture ([CCT Challengers 8](https://bo3.gg/tournaments/cct-europe-2026-challengers-8/matches) shows Phantom Academy vs los kogutos, unpriced) | public search returns only the closed Oct 22 event vs Falcons Force — no event for this pairing ([search](https://gamma-api.polymarket.com/public-search?q=Phantom%20Academy)) | no line; Valve-model pick + limitation stands |
| Acend vs UNiTY (1082996, 25 Oct) | [match 2399112](https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13) | listed (R16), no odds posted ([NODWIN matches](https://bo3.gg/tournaments/nodwin-clutch-series-13/matches)) | — | no line yet; retried every 4 h |
| Metizport vs BakS (1079198, 25 Oct) | [match 2399113](https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13) | listed (R16), no odds posted | — | no line yet; retried every 4 h |
| Infinite vs BRUTE (1079199, 25 Oct) | [match 2399114](https://www.hltv.org/matches/2399114/infinite-vs-brute-nodwin-clutch-series-13) — fan vote 40/60 excluded by policy | listed (R16), no odds posted | [event 1238706](https://polymarket.com/event/cs2-inf6-brute-2026-10-25) exists; Map-1 book (market 6072806) spread **0.92** (0.04/0.96), prices 0.5/0.5 — wide, recorded not used | wide book; Valve-model pick stands |
| Color vs ex-Zero Tenacity (1079200, 25 Oct) | [match 2399115](https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13) | listed (R16), no odds posted | — | no line yet; retried every 4 h |
| Ground Zero vs Off Chops (1082858, 26 Oct) | [match 2399888](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026) | listed (group A opening), no odds posted ([DFRAG matches](https://bo3.gg/tournaments/dfrag-invitational-2026/matches)) | [event 1237427](https://polymarket.com/event/cs2-gz1-offcho-2026-10-25) Map-1 book (market 6066506) spread **0.87** (0.06/0.93), prices 0.495/0.505 — wide | wide book; bo3.gg network pick stands |
| Rooster vs Abyssal (1082861, 27 Oct) | [match 2399891](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026) | listed (group B opening), no odds posted | — | no line yet; retried every 4 h |
| HOTU vs The Huns (1082792, 31 Oct) | [match 2399437](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) | no tournament page under `moscow-cyber-games-2026` (404) | — | no line; Valve-model pick stands |
| 5star vs 1WIN (1082793, 31 Oct) | [match 2399438](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026) | same 404 | — | no line; Valve-model pick stands |

## Why the limitations are the market's, not the pipeline's

In the same events and on the same day, books **did** price near-date matches —
FOKUS vs ex-6666 1.17/4.40 and Nuclear TigeRES vs FORZE Reload 1.58/2.20 (NODWIN R16,
Oct 24), NEXVOID vs Alter Ego 1.61/2.14 and FlyQuest vs Staqued 1.00/12.00 (DFRAG
openers). The pipeline's relay rung and featured Polymarket collector pick those up
automatically — the six fixtures the featured method left blank this refresh already got
sourced picks that way (two medians of independent money sources, a prediction-market
line, two Valve ratings, one bo3.gg network estimate). The nine rows above stay
model-only only while no book lists them; every four-hour refresh retries all of them.

## Result

**No new two-sided prematch price found** for any of the 9 fixtures in this window.
No probability, pick or alias was changed. `leads` is empty. Structured record:
[line-source-research.json](line-source-research.json).
