# Every Hotspawn CS2 card, 2026-10-24T06:26Z — 25 upcoming, 9 with no published pick

**Session:** arena-719a314a · **Read at:** 2026-10-24T06:26:00Z ·
**Sources:** [Hotspawn lobby](https://play.hotspawn.com/lobby),
[first-party fixture API](https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1),
[published snapshot](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json),
[published picks](https://buffedlizard55-lab.github.io/MaltaProj3/picks/),
[unresolved register](https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/),
[saved fixture evidence](https://buffedlizard55-lab.github.io/MaltaProj3/data/evidence/hotspawn-fixtures.json),
[HLTV](https://www.hltv.org/matches), [EGamersWorld CS2 matches](https://egamersworld.com/counterstrike/matches),
[EGamersWorld CCT Europe #11](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK),
[EGamersWorld CCT Europe #12](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-12-HiXMAaC8L).

## Why this page exists

The brief asks for a pick, or an explicit reason, for **every** match Hotspawn lists for
Counter-Strike 2 — including low-tier cards that no prediction market covers. This dossier
is the dated, line-by-line audit of that requirement against the site as it is served right
now, and the research that closes every gap it finds.

## Headline numbers

| Measure | Count | Source |
| --- | --- | --- |
| Upcoming CS2 cards on the Hotspawn lobby at 06:26Z | **25** | [lobby](https://play.hotspawn.com/lobby) |
| Cards present in the published snapshot (generated 2026-10-23T20:10Z) | **16** | [latest.json](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json), [picks](https://buffedlizard55-lab.github.io/MaltaProj3/picks/) |
| Cards with **no published pick** — the gap this dossier closes | **9** | nine ids below |
| Gap cards that carry a two-sided prematch price | **5** | EGamersWorld → Thunderpick |
| Gap cards with no usable price (placeholder only) | **4** | EGamersWorld CCT #12 schedule |

The published snapshot resolves 19 of 19 *active* fixtures (17 published picks + 2 researched
fallbacks), so the missing coverage is **not** a pick-quality problem: those nine cards were
never in the snapshot at all. The publisher had been failing its pre-collection regression
step since 2026-10-23, which is why the inventory stopped growing (see flag
`719a314a-publisher-duplicate-anchor`).

## The nine cards with no published pick

All nine are CCT Europe 2026 Series #11 / #12 cards. Times are UTC; the conversion from the
lobby clock is verified on all sixteen cards that also carry a first-party fixture-API epoch
(lobby clock + 4 h = epoch, exactly, 16/16).

| Hotspawn fixture | Match | Competition | Starts (UTC) | Pick | Probability | Price basis |
| --- | --- | --- | --- | --- | --- | --- |
| [1079658](https://play.hotspawn.com/cs2-pickems#fixture-1079658) | Acend vs FORZE Reload | CCT Europe #11 | 2026-10-24T08:00Z | **FORZE Reload** | 32.0 / **68.0** | [Thunderpick 2.87 / 1.35](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK) |
| [1079659](https://play.hotspawn.com/cs2-pickems#fixture-1079659) | Spirit Academy vs Lavked | CCT Europe #11 | 2026-10-24T11:00Z | **Spirit Academy** | **62.2** / 37.8 | [Thunderpick 1.49 / 2.45](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK) |
| [1079660](https://play.hotspawn.com/cs2-pickems#fixture-1079660) | INOX Division vs BRUTE | CCT Europe #11 | 2026-10-24T14:00Z | **INOX Division** | **52.4** / 47.6 | [Thunderpick 1.76 / 1.94](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK) |
| [1079661](https://play.hotspawn.com/cs2-pickems#fixture-1079661) | Nuclear TigeRES vs ex-Zero Tenacity | CCT Europe #11 | 2026-10-24T17:00Z | **Nuclear TigeRES** | **63.4** / 36.6 | [Thunderpick 1.45 / 2.51](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK) |
| [1081152](https://play.hotspawn.com/cs2-pickems#fixture-1081152) | HAVU vs Azuolas | CCT Europe #12 | 2026-10-24T11:00Z | *blank* | — | no usable price |
| [1081153](https://play.hotspawn.com/cs2-pickems#fixture-1081153) | Saint Sinners vs 6yuBoJlbl | CCT Europe #12 | 2026-10-24T14:00Z | *blank* | — | no usable price |
| [1081154](https://play.hotspawn.com/cs2-pickems#fixture-1081154) | BakS vs ILLYRIANS | CCT Europe #12 | 2026-10-24T17:00Z | *blank* | — | no usable price |
| [1081156](https://play.hotspawn.com/cs2-pickems#fixture-1081156) | Spirit Academy vs LFO 10 | CCT Europe #12 | 2026-10-25T12:00Z | *blank* | — | no usable price |
| [1081158](https://play.hotspawn.com/cs2-pickems#fixture-1081158) | FORZE Reload vs ex-RUSTEC | CCT Europe #12 | 2026-10-25T18:00Z | *blank* | — | no usable price |

### How each probability was produced

Only the four CCT #11 cards and one NODWIN card carry a two-sided price. The arithmetic is
proportional (no-vig) normalisation of the quoted decimal pair, and nothing else:

```
p1 = (1/o1) / (1/o1 + 1/o2)      p2 = (1/o2) / (1/o1 + 1/o2)
```

For 1079658: 1/2.87 = 0.348432, 1/1.35 = 0.740741, sum 1.089173 →
Acend 31.99 %, FORZE Reload 68.01 % (published as 32.0 / 68.0). Every card's arithmetic is
replayed by `scripts/719a314a_live_coverage.py` from the stored quotes; a mismatch fails the
check.

## The four cards with no usable price — limitations stated

EGamersWorld's *CCT Europe 2026 Series #12* schedule lists the same **1.8 / 1.8** pair for
these fixtures. This repository already documents that pair as a placeholder rather than a
market and rejects it (`tests/test_43110640_egw_live.py`), because two identical prices give
a 111 % book with no information. What was checked, in the brief's order:

| Surface | Result | Evidence |
| --- | --- | --- |
| HLTV (identity, format, ranks) | Fixture exists, BO3; CCT 2026 Europe Series 12 event page lists `HAVU … 24/10/26 13:00 … Azuolas … bo3` | [HLTV event 9457](https://www.hltv.org/events/9457/cct-2026-europe-series-12) |
| HLTV betting block | No bookmaker odds published for these cards | [HLTV matches](https://www.hltv.org/matches) |
| EGamersWorld / Thunderpick | Placeholder 1.8 / 1.8 — rejected, not converted | [EGW CCT #12](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-12-HiXMAaC8L) |
| Polymarket | CCT Europe series markets exist historically (e.g. `cs2-lavked-havu-2026-10-22`), but no confirmed two-sided book for these four cards at read time | [Polymarket CS2](https://polymarket.com/esports/cs2) |

Consequence: these four rows stay **blank** on purpose. A blank is never replaced with 50/50,
with a Hotspawn "% picked" figure, or with an HLTV fan vote. Each four-hour refresh retries
them, and a market that opens later is picked up automatically.

## Cross-check against an independent session

Session `arena-73bc57bd` read the same lobby at 2026-10-24T05:31Z and the fixture API at 05:39Z,
independently reached the **same** count (9 of 25 upcoming cards uncovered) and the same card list,
and recorded the same EGamersWorld *"by Thunderpick"* pairs for Acend/FORZE Reload 2.87/1.35,
Spirit Academy/Lavked 1.49/2.45 and INOX Division/Brute 1.76/1.94 — merged as PR #241
([record](https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/research/73bc57bd/inventory-reconciliation-2026-10-24.json)).
Their dossier records leads only and writes no pick or probability; the picks and no-vig percentages
here are this session's replay of the quoted pairs.

One pair differs: for Nuclear TigeRES vs ex-Zero Tenacity this read of the CCT #11 event page shows
**1.45 / 2.51**, where their record shows 1.49 / 2.33 plus a Polymarket-derived 67¢ / 43¢ segment.
Both are aggregator displays captured minutes apart, so the board moved between reads. Neither is a
first-party bookmaker response, and the ladder must replay whichever it can fetch at refresh time —
which is exactly why these five rows are labelled reference estimates, not market picks.

## Irregularities found while doing this (published on Flagged for Review)

1. **The publisher was stalled by one duplicated element id** — the executive summary rendered
   `id="no-line-research"` twice, so `tests/test_ca7e10e5_snapshot.py` failed the pre-collection
   regression step on every scheduled run. Fixed on `main` by PR #241 (`e360f4c`, session
   `arena-73bc57bd`); this branch carries that fix unchanged and adds the regression test that pins
   it, `tests/test_719a314a_duplicate_anchors.py`.
2. **Nine live cards were never collected** — the CCT Europe fixtures are in the lobby but not in
   `2026-10-23T20:10Z` snapshot or its saved fixture evidence. They are the whole gap.
3. **The lobby clock is not UTC** — it reads UTC−4 in this observation; using it as a start time
   without conversion would mis-schedule every pick lock by four hours.

## What happens next, without manual input

The four-hour publisher re-collects the fixture API, re-runs the ladder (Polymarket →
Thunderpick → aggregated references → Valve ratings → results-network model) and rebuilds the
site; the nine cards appear there as soon as a refresh succeeds, with either a money-backed
pick or a labelled research estimate, and the four blanks above listed on `/unresolved/` with
their reason. This dossier is the dated evidence for that claim, not a substitute for it.
