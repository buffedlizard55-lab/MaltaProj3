# Live Hotspawn CS2 lobby vs the published site — dated observation

**Session:** arena-e619b921 · **Observed:** 2026-10-24T06:35:00Z (08:35 Europe/Malta) · **Method:** page fetch of the public lobby (`play.hotspawn.com/cs2-pickems`), the cited Hotspawn match pages, HLTV, Polymarket and EGamersWorld. Not the GitHub runner.

**Role of this record:** inventory and line-source evidence only. No probability, pick or alias is written here. Crowd "% picked" percentages are never read as a probability.

## 1. What the lobby listed

| Counter on the page | Value read verbatim |
| --- | --- |
| Header | "224 matches this week" |
| Tier filter | "All tiers (88) · B (43) · C (45)" |
| Tournament filter | "All tournaments (88)" over 17 tournaments |
| Cards rendered in Closing Soon + Upcoming | **25** |

The header count (224) and the filter totals (88) do not agree, and earlier dated sessions recorded a different pair again (68 vs 88 on 2026-10-23T09:52Z, 203 vs 92 on 2026-10-23T09:47Z). This is a Hotspawn-side counter inconsistency; the 25 rendered cards are what is compared below. The discrepancy is published as a review flag.

## 2. Coverage result

| Measure | Count |
| --- | --- |
| Live cards at the observation | 25 |
| Cards present in the published snapshot (2026-10-23T20:10:00Z) | 16 |
| **Cards with no row in the published snapshot** | **9** |
| Published rows whose start had already passed | 3 |

The nine uncovered cards are all CCT Europe 2026 Series #11/#12 fixtures scheduled **after** the last successful collect. The publisher failed before collecting three times in a row — `pages.yml` runs [40037957529](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40037957529), [40048429858](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40048429858), [40063011446](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40063011446), each at the `Regression tests (repository fixtures, before any cache restore)` step — so at the observation the published snapshot was **10h25m** old, beyond its own 8-hour bound.

This record does not add those nine rows. The four-hour collector does, on its next successful run.

## 3. The nine uncovered cards, and what the books actually published

Order tried for each: Hotspawn card and match page for identity and start → HLTV → Polymarket → EGamersWorld (named bookmaker aggregate). Prices are quoted **verbatim**; the reviewed ladder replays or rejects them, this file converts nothing.

| Hotspawn | Fixture | Competition | Lobby card (US Eastern) | Start (UTC) | First-party price found | Usable? |
| --- | --- | --- | --- | --- | --- | --- |
| [1079658](https://www.hotspawn.com/matches/acend-vs-forze-reload-cct-europe-2026-series-11-1079658) | Acend vs FORZE Reload | CCT Europe #11 | Oct 24, 04:00 | 2026-10-24T08:00Z *(verified)* | [Polymarket](https://polymarket.com/esports/cs2/cct-europe/cs2-ace1-forzer-2026-10-24) Acend 33¢ / FORZE Reload 68¢ | yes |
| [1079659](https://www.hotspawn.com/matches/spirit-academy-vs-lavked-cct-europe-2026-series-11-1079659) | Spirit Academy vs Lavked | CCT Europe #11 | Oct 24, 07:00 | 2026-10-24T11:00Z *(verified)* | [Polymarket](https://polymarket.com/esports/cs2/cct-europe/cs2-tsa-lavked-2026-10-24) Spirit Academy 66¢ / Lavked 35¢ | yes |
| [1079660](https://www.hotspawn.com/matches/inox-division-vs-brute-cct-europe-2026-series-11-1079660) | INOX Division vs BRUTE | CCT Europe #11 | Oct 24, 10:00 | 2026-10-24T14:00Z *(verified)* | [Polymarket](https://polymarket.com/esports/cs2/cct-europe/cs2-inox-brute-2026-10-24) INOX Division 55¢ / Brute 46¢ | yes |
| [1079661](https://www.hotspawn.com/matches/nuclear-tigeres-vs-ex-zero-tenacity-cct-europe-2026-series-11-1079661) | Nuclear TigeRES vs ex-Zero Tenacity | CCT Europe #11 | Oct 24, 13:00 | 2026-10-24T17:00Z *(derived)* | [EGW](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK) Thunderpick 1.45 / 2.51 | yes (aggregate) |
| [1081152](https://www.hotspawn.com/matches/havu-vs-azuolas-cct-europe-2026-series-12-1081152) | HAVU vs Azuolas | CCT Europe #12 | Oct 24, 07:00 | 2026-10-24T11:00Z *(derived)* | EGW 1.8 / 1.8 — identical | **no** (placeholder) |
| [1081153](https://www.hotspawn.com/matches/saint-sinners-vs-6yubojlbl-cct-europe-2026-series-12-1081153) | Saint Sinners vs 6yuBoJlbl | CCT Europe #12 | Oct 24, 10:00 | 2026-10-24T14:00Z *(derived)* | EGW 1.8 / 1.8 — identical | **no** (placeholder) |
| [1081154](https://www.hotspawn.com/matches/baks-vs-illyrians-cct-europe-2026-series-12-1081154) | BakS vs ILLYRIANS | CCT Europe #12 | Oct 24, 13:00 | 2026-10-24T17:00Z *(derived)* | EGW 1.8 / 1.8 — identical | **no** (placeholder) |
| [1081156](https://www.hotspawn.com/matches/spirit-academy-vs-lfo-10-cct-europe-2026-series-12-1081156) | Spirit Academy vs LFO 10 | CCT Europe #12 | Oct 25, 08:00 | 2026-10-25T12:00Z *(derived)* | EGW 1.8 / 1.8 and the opponent name renders **blank** | **no** (placeholder + provider defect) |
| [1081158](https://www.hotspawn.com/matches/forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158) | FORZE Reload vs ex-RUSTEC | CCT Europe #12 | Oct 25, 14:00 | 2026-10-25T18:00Z *(derived)* | EGW 1.8 / 1.8 — identical | **no** (placeholder) |

*Verified* = the UTC start was read from a source that renders UTC for that fixture (the Hotspawn match page for 1079658; the Polymarket event cards for 1079659 and 1079660). *Derived* = the lobby card time plus the documented +4h US-Eastern offset, which 16 published rows independently confirm (e.g. the 04:00 card and the 08:00Z API start of 1079193). The collector's API epoch is authoritative on the next refresh and supersedes every derived value here.

### HLTV first

HLTV was tried before the books. For the published DFRAG fixture used as the control, [HLTV 2399888](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026) confirms the identity, the event and **"Best of 3 (LAN)"**, and its Betting block carries a single Stake US sweepstakes promo row with *"No promocode available"* — **no bookmaker decimal odds**. Its fan poll (Ground Zero 42.9% / Off Chops 57.1%) is recorded as excluded evidence, never as a probability.

Limitation, stated plainly: in this session the per-match HLTV Betting block was read first-hand only for that fixture. The other eight live cards were checked for identity through their Hotspawn pages and priced through Polymarket/EGamersWorld. The runner re-tries HLTV for every fixture on every refresh, where it records HTTP 403 (documented since earlier sessions).

## 4. What this means for "a pick for every match"

* **4 of the 9** already have a usable two-sided price (three first-party Polymarket books and one named-bookmaker aggregate). The ladder prices them automatically on the next collect — no hand-written number is needed.
* **5 of the 9** have no usable price anywhere reachable: EGamersWorld publishes the identical `1.8 / 1.8` on all five, which is not a market, and one of them renders the opponent name blank. Those five fall to the research-model rung (Valve points, then the own Bradley–Terry network fit), which is explicitly labelled as uncalibrated on the page, and each keeps its limitation text.
* Nothing here overrides a first-party price, and no fixture is given a default 50/50.

## 5. Limitations of this record

1. One observation window (06:33Z–06:50Z) read by page fetch; a later refresh supersedes it.
2. Five start times are derived from the lobby card and labelled per row.
3. The Hotspawn header counter (224) disagrees with its own filter totals (88); the counter is not used.
4. EGW placeholders and the blank team name are rejected, not converted.
5. No probability, pick or alias is written by this record.

## 6. Second finding: a published 1.00 price

While re-reading the rendered build, one money-backed row shows a decimal price of exactly **1.00**:

| Hotspawn | Fixture | Published line | Published estimate | Source of the number |
| --- | --- | --- | --- | --- |
| [1082860](https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860) | FlyQuest vs Staqued (DFRAG Invitational 2026, 2026-10-27T03:00Z) | `line 1.00 / 12.00` | FlyQuest **92.3%**, fair 1.083 | Thunderpick, labelled "No-vig bookmaker estimate" |

The arithmetic is right — 1/1.00 = 1.0000 plus 1/12.00 = 0.0833 gives 92.3% — but a decimal price of exactly 1.00 returns no profit, so no book offers it on a live two-way market. It behaves like the identical-pair placeholders this project already rejects; it is not caught here because the pair is not identical and the implied 8.3% margin looks normal.

I could **not** re-read the original value: `https://thunderpick.io/api/matches` answered `{"statusCode":200,"ok":true,"data":{"matches":[]}}` when checked, so the collector's 2026-10-23T20:09Z quote is the only record. Raised as **needs review**, not as a confirmed provider error. The other two bookmaker rows in the same build carry ordinary two-way prices (1.22 / 3.80 and 1.60 / 2.17), so this is one row, not the whole rung.

Requested owner (logged, not edited here): the paired-price rung should reject any leg at or below 1.01 before margin removal, and publish the rejection reason the way the identical-pair gate does.
