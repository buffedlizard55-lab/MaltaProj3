# Line research for the nine uncovered cards — 2026-10-24

Session `arena-da8067f5`. Read first-hand at **2026-10-24T06:47:00Z**. Scope: the nine live Hotspawn CS2 cards that had no published pick at 2026-10-24T06:35Z.

Prices are quoted verbatim at their source and timestamp. No probability, pick or alias is written by hand in this file. Hotspawn '% picked' and HLTV fan votes are never used.

## Fixtures with a two-sided external price (re-observed)

### 1079658 — Acend vs FORZE Reload (CCT Europe 2026 Series #11)

- Verdict: **two-sided external price observed**
- **Polymarket (Gamma API, original event)** — read 2026-10-24T06:46:00Z — quoted: `eventStartTime 2026-10-24T08:00:00Z; Map 1 market bestBid 0.35 / bestAsk 0.37 (Acend side); event volume 136.367821; liquidity 3353.3988` — [source](https://gamma-api.polymarket.com/events?slug=cs2-ace1-forzer-2026-10-24)
  - The event's own eventStartTime is 08:00Z, which is exactly the lobby's rendered 'Oct 24, 04:00' read as US Eastern (04:00 ET = 08:00Z).
- **Polymarket (public market page, moneyline)** — read 2026-10-24T06:47:00Z — quoted: `Moneyline $136 Vol: ace1 35c / forzer 69c` — [source](https://polymarket.com/esports/cs2/cct-europe/cs2-ace1-forzer-2026-10-24)
  - page render of the same event
- **EGamersWorld match page** — read 2026-10-24T06:47:00Z — quoted: `Acend 2.85 / FORZE Reload 1.34, Bo3, page title 'Acend VS FORZE Reload: 24.10.2026 at 08:00'` — [source](https://egamersworld.com/counterstrike/match/_rW8GEyWK/acend-vs-forze-reload-FZO8bqMyg)
  - Aggregated reference; the page title's 08:00 corroborates the 08:00Z start.
- **EGamersWorld CS2 matches index** — read 2026-10-24T06:44:00Z — quoted: `Acend 2.80 / FORZE Reload 1.35` — [source](https://egamersworld.com/counterstrike/matches)
  - index print 3 minutes earlier differs from the match page by 0.05/0.01; both recorded, neither averaged
- Limitation: Polymarket midpoints are not execution prices and fees are excluded.
- Limitation: The two EGamersWorld prints (index 2.80/1.35 at 06:44Z, match page 2.85/1.34 at 06:47Z) disagree slightly; neither is treated as more authoritative.
- Limitation: Only one first-party exchange and one aggregator were observed; this is not a multi-book consensus.

### 1079193 — FOKUS vs ex-6666 (NODWIN Clutch Series #13)

- Verdict: **already published as a market pick in the 2026-10-23T20:10Z snapshot (76.5% / 23.5%); re-observed here only for corroboration**
- **EGamersWorld CS2 matches index** — read 2026-10-24T06:44:00Z — quoted: `Fokus 1.23 / ex-6666 3.83` — [source](https://egamersworld.com/counterstrike/matches)
  - direction agrees with the published market pick; this is a different source and is not used to overwrite it
- Limitation: Corroboration only. The published percentage is unchanged and stays tied to its own saved quote.

## Fixtures with no compliant two-sided price at that read

- **1081152** — Only placeholder books observed today by arena-73bc57bd at 05:43Z (EGamersWorld 1.8/1.8). This session did not obtain a compliant two-sided price either.
- **1081153** — Both Polymarket sides 93-95c on $0.00 volume (not a normalisable two-team book); EGamersWorld 1.8/1.8 placeholder.
- **1081154** — Both Polymarket sides 93-94c on $0.00 volume; EGamersWorld 1.8/1.8 placeholder.
- **1081156** — Name conflict: Hotspawn 'LFO 10' vs Polymarket 'Sokerorg' for the same slot; EGamersWorld renders the opponent blank. No alias is invented.
- **1081158** — Polymarket mids sum to 165c (not a two-team book); EGamersWorld 1.8/1.8 placeholder.

These five stay **unresolved** unless a compliant source appears on the next refresh. They are not
filled with a 50/50 default, a Hotspawn crowd percentage or an HLTV fan vote; the site lists each one
in the separate *Unresolved picks & limitations* register with the sources that were tried.

## Sources

- <https://play.hotspawn.com/lobby>
- <https://polymarket.com/esports/cs2/cct-europe>
- <https://gamma-api.polymarket.com/events?slug=cs2-ace1-forzer-2026-10-24>
- <https://egamersworld.com/counterstrike/matches>
- <https://egamersworld.com/counterstrike/match/_rW8GEyWK/acend-vs-forze-reload-FZO8bqMyg>
- <https://www.hltv.org/matches>
