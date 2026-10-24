# Unresolved & low-tier guidance — 9 new pickable cards not priced like the featured picks (2026-10-24)

Session **arena-ebd1ed70**. Research window **2026-10-24 06:20–06:55 UTC**, read first-hand through the
agent page fetcher (the sandbox shell has no general egress). Machine-readable record:
[`source-ladder-2026-10-24.json`](./source-ladder-2026-10-24.json). Lobby roster:
[`live-lobby-2026-10-24.json`](./live-lobby-2026-10-24.json).

## Why these nine

The Hotspawn CS2 Pick'em lobby ([play.hotspawn.com/cs2-pickems](https://play.hotspawn.com/cs2-pickems))
rendered **25 pickable cards** at the observation (9 *Closing Soon* + 16 *Upcoming*; tier filter
"All tiers (88)", 224 matches this week). The published snapshot (`2026-10-23T20:10:00Z`) covers 16 of
them. The nine cards below are new in the lobby since that snapshot — all low-tier CCT Europe Series
#11/#12 group-play fixtures, exactly the class the brief says is not covered on Polymarket. For each,
the brief's ladder was run by hand: **HLTV first**, then **esportsbooks / esports betting lines**.

Hotspawn "% picked" values, HLTV fan votes and bo3.gg predictor counts appear in the evidence as
excluded observations only. They are never used as probabilities.

## Method (per fixture)

1. **HLTV match page** — identity, Best-of format, displayed ranks, the page's own **Betting** block.
2. **EGamersWorld** — CS2 matches index + match page (published bookmaker pairs where they exist;
   the identical `1.8 / 1.8` pair is EGW's placeholder banner and is **rejected** by the pipeline's
   fail-closed gate).
3. **bo3.gg** — Thunderpick-relayed decimal pairs on the match cards.
4. **thunderpick.io guest API** — `{"matches":[]}` at observation (board empty).
5. **Polymarket** — exact team-pair + start search; only past CCT markets found (see JSON record).

Percentages below are **computed** (no-vig normalisation of a published decimal pair) or explicitly
absent. No probability, pick or alias was written by hand.

## A. Resolvable from published prices (4) — guided picks with computed percentages

| Fixture | HLTV | Published pair (EGW / bo3.gg) | No-vig (computed) | Guided pick |
| --- | --- | --- | --- | --- |
| **Acend vs FORZE Reload** (1079658, 24 Oct 08:00Z) | [event 9442](https://www.hltv.org/events/9442/cct-2026-europe-series-11) | 2.8 / 1.35 · 2.87 / 1.35 | Acend 32.5% / FORZE Reload 67.5% (bo3.gg 32.0/68.0) | **FORZE Reload** |
| **Spirit Academy vs Lavked** (1079659, 24 Oct 11:00Z) | [event 9457](https://www.hltv.org/events/9457/cct-2026-europe-series-12) | 1.49 / 2.47 · 1.49 / 2.45 | Spirit Academy 62.4% / Lavked 37.6% (bo3.gg 62.2/37.8) | **Spirit Academy** |
| **INOX Division vs BRUTE** (1079660, 24 Oct 14:00Z) | [event 9442](https://www.hltv.org/events/9442/cct-2026-europe-series-11) | 1.75 / 1.96 · 1.75 / 1.97 | INOX Division 52.8% / BRUTE 47.2% (bo3.gg 53.0/47.0) | **INOX Division** (low confidence — book within 0.21 of even) |
| **Nuclear TigeRES vs ex-Zero Tenacity** (1079661, 24 Oct 17:00Z) | [event 9442](https://www.hltv.org/events/9442/cct-2026-europe-series-11) | 1.49 / 2.47 · 1.45 / 2.51 | Nuclear TigeRES 62.4% / ex-ZTN 37.6% (bo3.gg 63.4/36.6) | **Nuclear TigeRES** |

Sources: EGW index rows ([egamersworld.com/counterstrike/matches](https://egamersworld.com/counterstrike/matches),
read 06:35Z) with match-page links in the JSON record; bo3.gg match cards
([bo3.gg/matches](https://bo3.gg/matches)). Both references are aggregated/relayed, **not** first-party
quotes; the automated EGW rung (`scripts/egw_live.py`) will pick these four up on the next collect
under the same placeholder/freshness gates. Limitation: Spirit Academy–Lavked's price runs against
the 21/10 H2H (Lavked 2-1) — recorded, not "fixed".

## B. No compliant line anywhere checked (5) — direction + limitations only

These five have **no two-sided book anywhere in the ladder**: HLTV's Betting block carries only the
Stake US sweepstake promo row ("No promocode available"); EGW shows the rejected 1.8/1.8 placeholder
(or no opponent identity at all); bo3.gg prints no pair; thunderpick.io's guest board is empty; no
live Polymarket series moneyline exists for the exact pair+start.

| Fixture | HLTV (first rung) | Direction (evidence) | Limitations |
| --- | --- | --- | --- |
| **HAVU vs Azuolas** (1081152, 24 Oct 11:00Z) | [2399502](https://www.hltv.org/matches/2399502/havu-vs-azuolas-cct-2026-europe-series-12) Bo3, Swiss R3 0-2 (loser eliminated); HAVU #101 / Azuolas #175 (event view) | **HAVU** — HLTV rank gap, EGW ratings 204 vs 688, last-10 wins 4 vs 1 | Both arrive 0-2 on 3-loss streaks; no price to convert; percentage must come from the automated model rung (Valve VRS / results-fit) at refresh |
| **Saint Sinners vs 6yuBoJlbl** (1081153, 24 Oct 14:00Z) | [2399503](https://www.hltv.org/matches/2399503/6yubojlbl-vs-saint-sinners-cct-2026-europe-series-12) Bo3, Swiss R3 1-1; 6yuBoJlbl HLTV #177 / VRS #127 | **Saint Sinners (weak)** — EGW ranks #588 vs #691 | HLTV event rows favour 6yuBoJlbl (#123 vs #133) — sources disagree; coin-flip class; Saint Sinners lineup unlisted on EGW; no price anywhere |
| **BakS vs ILLYRIANS** (1081154, 24 Oct 17:00Z) | [2399504](https://www.hltv.org/matches/2399504/baks-vs-illyrians-cct-2026-europe-series-12) Bo3, Swiss R3 1-1; BAKS #96 / Illyrians #126 | **BakS** — ranks on both HLTV (#96 v #126) and EGW (#193 v #452), plus 20/10 H2H (Illyrians 1-2 BakS, [HLTV](https://www.hltv.org/team/11719/illyrians)) | Single recent H2H is thin; EGW calls the team "BakS eSports" (slug join binds "baks", alias implicit) |
| **Spirit Academy vs LFO 10** (1081156, 25 Oct 12:00Z) | [2399506](https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12) Bo3, Swiss R3 1-1; Spirit Academy #115 / LFO 10 #176 | **Spirit Academy** — rank gap 61 places | EGW lists the opponent as unnamed ("Spirit Academy VS ", slug `spirit-academy-vs-zgh7PZE301`) so the EGW rung can never bind this fixture; HLTV's Valve ranking page showed **two "LFO 10" rows** on 20 Oct (749 pts #122 / 580 pts #200) — identity irregularity flagged, any model join must fail closed |
| **FORZE Reload vs ex-RUSTEC** (1081158, 25 Oct 18:00Z) | [2399508](https://www.hltv.org/matches/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12) Bo3, Swiss R3 2-0 (winner to playoffs); FORZE Reload HLTV #80 / ex-RUSTEC #94 | **FORZE Reload** — HLTV (#78/#80 v #94) and EGW (#121 v #258) rank gaps; last two bo3 H2H 2-0 FORZE (≈8 weeks ago) | Both 2-0 in-form; H2H stale; no price anywhere, so no market-implied probability exists |

### Limitations of generating picks for these five (plain words)

1. **There is no betting line to trust.** Everything reachable either prints no odds (HLTV promo-only
   block) or prints the same placeholder pair `1.8/1.8` for every match (EGW's banner) — a pair that
   carries no information and is rejected on purpose.
2. **The percentage has to come from a model, not a market.** The automated ladder's Valve-VRS /
   results-fit rungs are the only legitimate percentage sources here; they run at each refresh and
   publish an explicitly uncalibrated estimate. This dossier therefore gives a **direction** with its
   evidence, not an invented number.
3. **Thin identity data.** Saint Sinners has no published lineup on EGW; LFO 10 is unnamed on EGW and
   collides with two Valve standing rows; "BakS" vs "BakS eSports" joins only by slug. Any of these
   can make the model rung fail closed — which is correct behaviour, not a bug to paper over.
4. **Poor form on both sides in some cards** (HAVU–Azuolas is an elimination match between 0-2 teams).
   Direction can still be evidenced, but confidence is low and is labelled as such.
5. **Time-window caveat.** Books appear late on low-tier cards; the automated EGW rung + 4-hour
   publisher retry every refresh, so these five can gain a real line later. This record is a dated
   observation (06:35Z), not a permanent claim.

## Irregularities flagged for review

* **EGW identity failure** on 1081156 (opponent unnamed) — see table.
* **Two "LFO 10" rows** on HLTV's Valve ranking page (20 Oct edition) — see table.
* **EGW placeholder economics**: 1.8/1.8 on five of nine cards while bo3.gg/EGW carry real prices on
  four — the placeholder is an EGW listing default, not a market.
* **bo3.gg predictor counts** ("12 - 0", "21 - 2" …) are popularity counts; excluded from every
  calculation here.
