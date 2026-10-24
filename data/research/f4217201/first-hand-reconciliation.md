# Live Hotspawn CS2 reconciliation and no-line research — 2026-10-24

Session `arena-f4217201`. Every row below was read first-hand at the time printed;
every value links the official page it came from. No probability, pick or team alias
was written by hand in this dossier, and no value is inferred from a page that could
not be read.

This file is the human-readable side of `scripts/f4217201_probe.py`. The probe
re-runs the same reads on a GitHub runner and writes `live-reconciliation.json`
and `line-research.json` beside this file, so the claims below can be replayed
instead of trusted.

## 1. What the lobby showed, and what the published snapshot covered

| Check | Value | Source |
| --- | --- | --- |
| Lobby read at | 2026-10-24T07:47Z (cards), 08:06Z (second card block) | [Hotspawn lobby](https://play.hotspawn.com/lobby) |
| Future CS2 cards rendered | **25** | [Hotspawn lobby](https://play.hotspawn.com/lobby) |
| Published snapshot generated | **2026-10-23T20:10:00Z** | [deployed data/latest.json](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json) |
| Published snapshot age at the read | **~11.6 h** (outside the 8 h freshness bound) | both of the above |
| Published upcoming rows | 19 (17 with a pick, 2 unresolved) | [deployed data/latest.json](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json) |
| Rendered cards present in the snapshot | 16 | [Hotspawn lobby](https://play.hotspawn.com/lobby), [deployed data/latest.json](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json) |
| Rendered cards **not** in the snapshot | **9** (all CCT Europe Series #11/#12) | below |

The three other snapshot rows (paiN–Imperial, Alka–LOS NINOS, Chinggis Warriors–Rare
Atom) had already started and are no longer rendered as open cards. They are kept in
the snapshot as recent rows, so 19 snapshot rows − 3 started = 16 rendered matches.

## 2. The nine uncovered cards, researched in the order the brief asks for

Identity first (Hotspawn card → HLTV), then esportsbook/exchange lines. A price is
only called a line when the venue shows a two-sided prematch winner market with
non-zero volume; a $0.00 book or a crossed book (both sides above 50¢) is recorded
and **refused**, never averaged into a probability.

| Hotspawn fixture (official card) | Start (UTC) | HLTV identity | Exchange/book evidence read | Verdict |
| --- | --- | --- | --- | --- |
| [Acend vs FORZE Reload](https://www.hotspawn.com/matches/acend-vs-forze-reload-cct-europe-2026-series-11-1079658) `1079658` | 2026-10-24 08:00 | [CCT 2026 Europe Series 11](https://www.hltv.org/events/9442/cct-2026-europe-series-11) lists the Acend–FORZE Reload playoff match | [Polymarket `cs2-ace1-forzer-2026-10-24`](https://polymarket.com/event/cs2-ace1-forzer-2026-10-24): Acend 31¢ / FORZE Reload 70¢, **$139.22 vol** | **external line available** |
| [Spirit Academy vs Lavked](https://www.hotspawn.com/matches/spirit-academy-vs-lavked-cct-europe-2026-series-11-1079659) `1079659` | 2026-10-24 11:00 | [CCT 2026 Europe Series 11](https://www.hltv.org/events/9442/cct-2026-europe-series-11) (Spirit Academy in the Series #11 bracket) | [Polymarket `cs2-tsa-lavked-2026-10-24`](https://polymarket.com/event/cs2-tsa-lavked-2026-10-24): 66¢ / 35¢, **$72.12 vol** | **external line available** |
| [INOX Division vs BRUTE](https://www.hotspawn.com/matches/inox-division-vs-brute-cct-europe-2026-series-11-1079660) `1079660` | 2026-10-24 14:00 | [CCT 2026 Europe Series 11](https://www.hltv.org/events/9442/cct-2026-europe-series-11) shows the INOX Division–BRUTE semifinal | [Polymarket `cs2-inox-brute-2026-10-24`](https://polymarket.com/event/cs2-inox-brute-2026-10-24): 57¢ / 44¢, **$1.55K vol** | **external line available** |
| [Nuclear TigeRES vs ex-Zero Tenacity](https://www.hotspawn.com/matches/nuclear-tigeres-vs-ex-zero-tenacity-cct-europe-2026-series-11-1079661) `1079661` | 2026-10-24 17:00 | [CCT 2026 Europe Series 11](https://www.hltv.org/events/9442/cct-2026-europe-series-11) | [Polymarket `cs2-ntr-zerote-2026-10-24`](https://polymarket.com/event/cs2-ntr-zerote-2026-10-24): 65¢ / 36¢, **$50.16 vol** | **external line available** |
| [HAVU vs Azuolas](https://www.hotspawn.com/matches/havu-vs-azuolas-cct-europe-2026-series-12-1081152) `1081152` | 2026-10-24 11:00 | not located in the HLTV blocks read (limitation, not proof of absence) | no priced market in the CCT Europe board blocks read | **unresolved** |
| [Saint Sinners vs 6yuBoJlbl](https://www.hotspawn.com/matches/saint-sinners-vs-6yubojlbl-cct-europe-2026-series-12-1081153) `1081153` | 2026-10-24 14:00 | — | [Polymarket `cs2-6yuboj-ssins-2026-10-24`](https://polymarket.com/event/cs2-6yuboj-ssins-2026-10-24): 68¢ / 85¢ (**crossed**, sum 153) with **$0.00 vol** | **unresolved** — empty/crossed book refused |
| [BakS vs ILLYRIANS](https://www.hotspawn.com/matches/baks-vs-illyrians-cct-europe-2026-series-12-1081154) `1081154` | 2026-10-24 17:00 | — | [Polymarket `cs2-baks-ill4-2026-10-24`](https://polymarket.com/event/cs2-baks-ill4-2026-10-24): 72¢ / 67¢ (**crossed**, sum 139) with **$0.00 vol** | **unresolved** — empty/crossed book refused |
| [Spirit Academy vs LFO 10](https://www.hotspawn.com/matches/spirit-academy-vs-lfo-10-cct-europe-2026-series-12-1081156) `1081156` | 2026-10-25 12:00 | — | [Polymarket `cs2-tsa-skr2-2026-10-25`](https://polymarket.com/event/cs2-tsa-skr2-2026-10-25) names **Sökerorg**, not LFO 10: 93¢ / 93¢, **$0.00 vol** | **unresolved** — provider name conflict and a flat book |
| [FORZE Reload vs ex-RUSTEC](https://www.hotspawn.com/matches/forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158) `1081158` | 2026-10-25 14:00 | — | no priced market in the CCT Europe board blocks read | **unresolved** |

Times are the lobby's displayed start (US Eastern, UTC−4 in October) converted to
UTC and cross-checked against the Hotspawn fixture API's `scheduled_start_time`.

## 3. Limitations that decide how these rows are published

1. **A stale snapshot is not a missing market.** All nine cards are absent from the
   deployed snapshot because it was generated ~11.6 h earlier, before those Series
   #11/#12 markets opened. The publisher re-reads the lobby and every venue on each
   refresh; four of the nine now have a usable two-sided line, so the next successful
   publish should price them from that line rather than from a model.
2. **Zero-volume and crossed books are refused.** Series #12 cards show 68¢/85¢,
   72¢/67¢ and 93¢/93¢ at $0.00 volume. Those are not prices anyone can take; the
   site treats them as no line and keeps the fixture visible with its research trail.
3. **A provider name conflict blocks a join.** Polymarket's `cs2-tsa-skr2-2026-10-25`
   names *Sökerorg* where Hotspawn names *LFO 10*. Without an evidenced alias the
   identity join fails closed; the row stays unresolved rather than being matched on
   a guess.
4. **What was not readable is stated, not filled in.** HAVU–Azuolas and FORZE
   Reload–ex-RUSTEC were not found with a priced market in the board blocks read in
   this window. That is an observation about this read, not proof that no market
   exists; the runner probe retries the same pages and records the HTTP status and
   content hash for each.
5. **No Hotspawn popularity number is used.** The lobby's "% picked" shares (for
   example 17% Acend / 83% FORZE Reload) are community participation, never a
   probability input, and they appear nowhere in this dossier's verdicts.
6. **No probability is written here.** Prices above are quoted venue prices with
   their volume. Turning a price into a probability is the published origination
   ladder's job (de-vigged two-sided quote, then model rungs), and every published
   number carries its own source link.
