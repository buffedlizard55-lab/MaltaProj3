# HLTV-first research for fixtures without a betting line — arena-f1277d3b

Read first-hand **2026-10-24** (session window ~05:20–06:10Z) through egress that reaches
`hltv.org`. Target set: every active fixture in the published
`2026-10-23T20:10:00Z` snapshot whose pick rests only on a labelled research
model, plus the two the featured method left unresolved — **7 of 19** active
fixtures, all still prematch (Oct 25–31). Machine-readable record with lineups,
countdowns and verbatim notes: `hltv-first-research.json` (same directory).
Esportsbook/exchange surfaces are in the companion runner sweep
`line-source-research.{json,md}`.

**No probability, pick or alias is written by this research.** HLTV fan polls
and Hotspawn "% picked" were seen and excluded by policy.

| Hotspawn | Fixture (event, start UTC) | HLTV page | Format | HLTV # / VRS # read | HLTV Betting block | Published pick (research model) | Ranking cross-check |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1082996 | Acend vs UNiTY (NODWIN Clutch Series #13, Oct 25 09:00) | [2399112](https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13) | Bo3 (Online) | Acend #131/#75 · UNiTY #86/#60 | Stake US sweepstake promo only — no odds | Acend 54.2% / UNiTY 45.8% (Valve) | ⚠️ Both displayed orders place UNiTY higher — flagged, not overridden |
| 1079198 | Metizport vs BakS (NODWIN Clutch Series #13, Oct 25 12:00) | [2399113](https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13) | Bo3 (Online) | Metizport #59/#67 · BAKS #99/#100 | promo only — no odds | Metizport 79.9% (Valve) | agrees in direction |
| 1079200 | Color vs ex-Zero Tenacity (NODWIN Clutch Series #13, Oct 25 18:00) | [2399115](https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13) | Bo3 (Online) | Color Unranked/#73 · ex-ZT #67/#92 | promo only — no odds | Color 73.6% (Valve) | VRS order agrees; HLTV rank alone would hit the documented unranked-floor case |
| 1082858 | Ground Zero vs Off Chops (DFRAG Invitational 2026, Oct 26 03:00) | [2399888](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026) | Bo3 (LAN) | GZ #143/#131 · Off Chops #142/#132 | promo only — no odds | Off Chops 55.1% (complete list; featured blank) | the two orders disagree by one place — near-tie |
| 1082861 | Rooster vs Abyssal (DFRAG Invitational 2026, Oct 27 03:00) | [2399891](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026) | Bo3 (LAN) | Rooster Unranked/#154 · Abyssal #128/#130 | promo only — no odds | Abyssal 52.2% (Valve) | agrees in direction |
| 1082792 | HOTU vs The Huns (Moscow Cyber Games 2026, Oct 31 09:00) | [2399437](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) | Bo3 (LAN) | HOTU #38/#38 · The Huns #134/#123 | promo only — no odds | HOTU 94.1% (complete list; featured blank — name ambiguity) | agrees in direction; % stays an uncalibrated model output |
| 1082793 | 5star vs 1WIN (Moscow Cyber Games 2026, Oct 31 13:00) | [2399438](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026) | Bo3 (LAN) | 1win #14/#18 · 5star #36/#64 | promo only — no odds | 1WIN 82.2% (Valve) | agrees in direction |

## Limitations for generating picks for these fixtures

- HLTV confirms identity, event and Bo3 format for all 7, but its Betting block
  on every page is a single sweepstake promotion row ("No promocode
  available") — **zero two-sided bookmaker odds**, so HLTV cannot originate a
  betting line for them. Its fan poll is a crowd poll, never a probability.
- The published percentages therefore remain **labelled, uncalibrated
  research-model estimates** (Valve official ratings / own network model) with
  the per-card limitations: dated rating snapshot, current lineups, stand-ins
  (two pages display "Substitute" cells) and map vetoes unverified.
- A row upgrades automatically only when the four-hour ladder replays a
  compliant two-sided external line from saved first-party evidence
  (Polymarket/Kalshi/Smarkets/Thunderpick/Bovada/Pinnacle, bo3.gg-relayed
  bookmaker prices, or the EGamersWorld reference). Absence today is not proof
  no market exists; low-tier books often open near start time.
- The target snapshot is stale because the publisher stalled (see
  `flags.json`: `f1277d3b-publisher-stalled-wall-clock-test`); fixtures
  Hotspawn added after 2026-10-23T20:10:00Z get picks on the first successful
  refresh after the fix merges.

## Addendum — fresh lobby fixtures (2026-10-24T06:09Z sweep)

The companion runner sweep's fresh collection (25 active) added five
model-only fixtures Hotspawn listed after the frozen snapshot; all five HLTV
pages were then read first-hand (~06:10–06:18Z). Every one is **Bo3 (Online),
CCT 2026 Europe Series 12**, and every Betting block is again promo-only with
**no two-sided odds**: [1081152 HAVU vs Azuolas](https://www.hltv.org/matches/2399502/havu-vs-azuolas-cct-2026-europe-series-12) ·
[1081153 Saint Sinners vs 6yuBoJlbl](https://www.hltv.org/matches/2399503/6yubojlbl-vs-saint-sinners-cct-2026-europe-series-12) ·
[1081154 BakS vs ILLYRIANS](https://www.hltv.org/matches/2399504/baks-vs-illyrians-cct-2026-europe-series-12) ·
[1081156 Spirit Academy vs LFO 10](https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12) ·
[1081158 FORZE Reload vs ex-RUSTEC](https://www.hltv.org/matches/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12).
Details and the sweep summary (Polymarket 439 events, 8 bound all
placeholder-wide; Smarkets 3 targets bound, none inside ceilings; Pinnacle
guest 22,927 matchups, 0 hits; **0 money-line leads**) are in
`hltv-first-addendum.json` and `line-source-research.{json,md}`.
In the same fresh collection, 1079200 (Color vs ex-Zero Tenacity) was resolved
by the ladder above the research-model rungs — the automatic upgrade path, no
session input involved.
