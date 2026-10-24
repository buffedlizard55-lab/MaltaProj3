# Coverage and line audit — every CS2 card the Hotspawn lobby showed (arena-2ed65c56, 2026-10-24)

Read first-hand on **2026-10-24T06:31Z–06:38Z**. Machine-readable record:
[`live-coverage.json`](live-coverage.json). Review flags:
[`flags.json`](flags.json) (published on `/review/`).

## 1. What the lobby actually listed

[The CS2 lobby](https://play.hotspawn.com/lobby) reported **88 CS2 pick'em cards this
week** (43 tier B, 45 tier C) and rendered **25 closing-soon / upcoming cards**.
Those 25 are the cards compared row by row here — the 88 is a filter count, not a
list, and is not treated as itemised coverage.

Card times on the lobby render in **America/New_York (UTC-4)**. That offset is not an
assumption: all **16** cards that also exist in the published snapshot map to the
snapshot's UTC start time with exactly a +4h shift (`1079193` 04:00 → 08:00Z,
`1082897` 04:00 → 08:00Z, `1082792` 05:00 → 09:00Z, …). The offset is then applied
to the nine cards that are *not* in the snapshot.

## 2. Published snapshot vs the lobby

| | Count |
| --- | --- |
| Cards the lobby rendered | 25 |
| Present in the published snapshot (`2026-10-23T20:10:00Z`) | 16 |
| **Absent from the published snapshot** | **9** |

All nine missing cards are **CCT Europe 2026 Series #11 / #12**, and every one starts
within about eleven hours of the read. They are missing because the last successful
collect predates them and the refreshes since then did not run — not because the
dashboard filters them out.

| Hotspawn id | Card | Start (UTC) | Hotspawn page | External two-sided line read | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1079658 | Acend vs FORZE Reload | 24 Oct 08:00 | [page](https://www.hotspawn.com/matches/acend-vs-forze-reload-cct-europe-2026-series-11-1079658) | Acend 2.80 / FORZE Reload 1.35 | **Guided pick FORZE Reload 67.5%** (32.5% Acend) |
| 1079659 | Spirit Academy vs Lavked | 24 Oct 11:00 | [page](https://www.hotspawn.com/matches/spirit-academy-vs-lavked-cct-europe-2026-series-11-1079659) | Spirit Academy 1.49 / Lavked 2.47 | **Guided pick Spirit Academy 62.4%** (37.6% Lavked) |
| 1081152 | HAVU vs Azuolas | 24 Oct 11:00 | [page](https://www.hotspawn.com/matches/havu-vs-azuolas-cct-europe-2026-series-12-1081152) | 1.80 / 1.80 | **Blank — placeholder refused** |
| 1081153 | Saint Sinners vs 6yuBoJlbl | 24 Oct 14:00 | [page](https://www.hotspawn.com/matches/saint-sinners-vs-6yubojlbl-cct-europe-2026-series-12-1081153) | none found | Blank — unverified |
| 1079660 | INOX Division vs BRUTE | 24 Oct 14:00 | [page](https://www.hotspawn.com/matches/inox-division-vs-brute-cct-europe-2026-series-11-1079660) | none found | Blank — unverified |
| 1081154 | BakS vs ILLYRIANS | 24 Oct 17:00 | [page](https://www.hotspawn.com/matches/baks-vs-illyrians-cct-europe-2026-series-12-1081154) | none found | Blank — unverified |
| 1079661 | Nuclear TigeRES vs ex-Zero Tenacity | 24 Oct 17:00 | [page](https://www.hotspawn.com/matches/nuclear-tigeres-vs-ex-zero-tenacity-cct-europe-2026-series-11-1079661) | none found | Blank — unverified |
| 1081156 | Spirit Academy vs LFO 10 | 25 Oct 12:00 | [page](https://www.hotspawn.com/matches/spirit-academy-vs-lfo-10-cct-europe-2026-series-12-1081156) | none found | Blank — unverified |
| 1081158 | FORZE Reload vs ex-RUSTEC | 25 Oct 18:00 | [page](https://www.hotspawn.com/matches/forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158) | none found | Blank — unverified |

### How the guided percentages were produced

Decimal odds → proportional no-vig: `pᵢ = (1/oᵢ) / Σ(1/o)`.

* 1079658: `1/2.80 = 0.35714`, `1/1.35 = 0.74074`, sum `1.09788` → Acend **32.5%**,
  FORZE Reload **67.5%** (overround **9.79%**).
* 1079659: `1/1.49 = 0.67114`, `1/2.47 = 0.40486`, sum `1.07600` → Spirit Academy
  **62.4%**, Lavked **37.6%** (overround **7.60%**).
* 1081152: `1/1.80 = 0.5556` twice → a perfect 50/50 template, i.e. **no priced
  line at all**; refused, so the pick stays blank.

`tests/test_2ed65c56_research.py` recomputes every published percentage from the
decimal odds stored in the record, so a hand-edited number cannot survive the suite.

## 3. What the official pages did and did not publish

[The Hotspawn fixture page for 1079658](https://www.hotspawn.com/matches/acend-vs-forze-reload-cct-europe-2026-series-11-1079658)
confirms the pairing, the tournament and the 08:00 24 Oct start, and lists both
lineups (FORZE Reload: Lack1, KusMe, NickelBack; Acend: SPELLAN, Skrimo, REDSTAR,
AwaykeN). It publishes **no odds**, **no pick/ban data** ("No pick/ban data
available") and an **empty map breakdown**. Hotspawn's own "% picked" figures on the
lobby (17% / 83% for this card) are community participation and are **never** used as
a probability.

[HLTV's match index](https://www.hltv.org/matches) lists these tournaments
(CCT Europe #11/#12 are not in HLTV's front-page filter set for today) and is used in
this repo as identity/format evidence, never as an odds feed. For the two cards
above the external two-sided line came from
[EGamersWorld's public CS2 match list](https://egamersworld.com/counterstrike/matches),
which displays named-bookmaker prices.

## 4. Verification of one already-published row

The published snapshot prices **FOKUS vs ex-6666 (1079193)** at 76.5% / 23.5% from
Polymarket's order-book midpoints at 2026-10-23T20:09:34Z. An independent surface
read at 06:33Z published FOKUS 1.23 / ex-6666 3.83, which no-vig gives **75.7% /
24.3%** (overround 7.41%). The two independent observations agree within **0.8
points** — the row is corroborated, not merely self-consistent.

## 5. Limitations — stated, not smoothed over

1. The 25 compared cards are the ones the lobby **rendered**; the 88-card weekly
   total is a filter count and is not itemised here.
2. HLTV was not re-read for all 25 cards in this window; where it was not read, no
   claim is made about it.
3. EGamersWorld shows an **aggregated** bookmaker price, not a first-party quote, and
   a single reference is never a consensus. It never overrides a first-party line.
4. Identical numbers on both sides are a template placeholder and are refused.
5. Six of the nine missing cards had **no** usable external price in this window;
   their pick stays blank and is flagged unverified. Nothing is filled with a 50/50.
6. Absence from the snapshot is a **coverage gap of the last collect**, not proof
   that no market exists.

## 6. Why the snapshot was stale (irregularity)

`pages.yml` failed at its regression step on four consecutive scheduled runs
(40037957529, 40048429858, 40063011446; the 21:41Z run 40028653350 on 23 Oct also
failed), and the push run for PR #240's merge (40069088115) was still queued at the
time of this read. The executive summary therefore rendered **"Snapshot needs
attention"** while serving the 2026-10-23T20:10:00Z snapshot, older than its own
eight-hour bound. The regression fix is on `main` (`bdb4fc9`); this session verifies
the next successful run rather than assuming it.
