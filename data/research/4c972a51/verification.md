# Session arena-4c972a51 — verification record

Branch `arena/4c972a51-maltaproj3`, branched from `main` at `285a0d9` (merge of PR #162).
Every number below is copied from a dated artifact in this directory or from the live
Hotspawn endpoint; nothing is estimated. Times are UTC.

## 1. What the published site said when this session started

| Reading | Value | Source |
| --- | --- | --- |
| Live snapshot at 07:37Z | 33 active fixtures, 33 with a pick, 15 external-line, 18 research-model, 0 unresolved | `https://buffedlizard55-lab.github.io/MaltaProj3/` |
| Live `data/latest.json` at 07:37Z | `inventory 96, upcoming 33, market 10, bookmaker 1, model 12, unresolved 10, picks 23` | `https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json` |
| Match-picks page sentence | "33 of 33 matches below carry a pick … 11 come from an external market … 12 more from the audited research ladder … 0 remain blank" — 11 + 12 = 23, ten short of 33 | `https://buffedlizard55-lab.github.io/MaltaProj3/picks/` |

The ten-fixture discrepancy is *not* ten missing picks: the header counted every displayed
row (featured pick plus researched fallback) while the sentence added the featured-only
counters from `latest.json`. Fixed in `scripts/build.py` and published on the Flagged for
Review page as `4c972a51-picks-count-arithmetic`.

## 2. Live inventory, collected by the publishing runner

Artifact: `live/latest.json` (snapshot `2026-10-22T07:36:53Z`), `live/origination.json`.

| Check | Result |
| --- | --- |
| Hotspawn CS2 records reconciled | **107** records, **107** unique fixture ids, 0 unknown schedules (`counts.inventory`) |
| Active (open or locked) | **46**; past-start retained separately: **61** |
| Featured method | 16 market, 4 bookmaker, 15 model, **11 unresolved** |
| Complete researched list | **46 / 46** with probabilities, **45 / 46** with a directional pick before the tie-break, **0** without any estimate |
| Rung that resolved the 46 rows | market 16 · bookmaker 8 · consensus 2 · model 20 (Valve 15, HLTV ranking 3, network 2) · relay 2 · alias-joined 4 |
| Fixture with no side | `1082926` Isurus vs Hacha — HLTV rank 215 vs 229 with **2.0 points each**, exactly 50.0% / 50.0% |

The one missing side was a genuine exact tie, not a missing source. `scripts/originate.py`
now sets the direction from the ranking provider's own published order (215 before 229),
changes no probability, and records the rule on the row. Pinned by
`tests/test_4c972a51_tiebreak.py` (8 tests).

## 3. Source research — HLTV first, then esportsbooks

Artifact: `source-probe.json` (49 surfaces, runner egress `2026-10-22T07:38:14Z`),
`live-diagnostic.json` (resolver output `2026-10-22T07:38:00Z`).

| Question | Verified answer | Evidence |
| --- | --- | --- |
| Does HLTV publish a price? | No. Identity, results and a weekly ranking only | `https://www.hltv.org/matches` |
| Is HLTV readable by the runner? | Intermittently. The collector saved **73** HLTV records at `07:36:50Z`; the probe's match list, ranking and RSS all returned **403** at `07:38:14Z` | `live/latest.json` → `sources`, `source-probe.json` |
| Do esportsbooks cover the low-tier fixtures? | GG.BET, Stake, Marathonbet, Coolbet, Bet365 and Betfair refused automated access (403); Betano, Betnacional, Esportes da Sorte and KTO answered with identical 7,001-byte script shells; 1xBet returned a 203 challenge; OddsPortal rate-limited (429) | `source-probe.json` |
| Which sources actually price fixtures? | Polymarket (Gamma + CLOB), Pinnacle guest board, Kalshi, Thunderpick POST, bo3.gg relay, plus the Valve rating table and the bo3.gg results graph for models | `live/origination.json` → `sources`, `counts` |
| Can a blank be closed by another book? | Not in this snapshot: every active fixture already had an estimate. The source matrix is published as a capability check on `/unresolved/#source-matrix` | `source-probe.md` |

No access control was bypassed: every request is an unauthenticated GET/POST to a public
endpoint with an ordinary browser user agent, and every refusal is recorded.

## 4. Site verification

| Check | Result |
| --- | --- |
| `python -m scripts.build` on the checked-in snapshot | PASS, 80 source rows replayed |
| Row-source audit | 609 rows, 591 with an official link, 9 flagged unverified, 9 site-map, **0 without a source** |
| Internal links/anchors | **784** checked, 0 broken |
| New page | `/unresolved/` renders 4 status cards, the register, the dated 49-surface matrix, the resolution ladder and the tie-break rule |
| Navigation | desktop sidebar, phone bottom bar (`Summary · Picks · Unresolved · Edge · Sources · Review`) and the executive-summary banner all link the new page |
| Phone width | layout reuses the existing 320/390/768 px contracts; the probe matrix is a list, not a table, so it cannot force horizontal scroll; CI runs the Chromium 320/390/768/1440 px and axe WCAG A/AA checks on this branch |
| Unit tests (affected modules) | 204 + 99 + 23 tests pass, including 8 new tie-break tests |

## 5. Flags for manual review

Published from `flags.json` on the Flagged for Review page:

1. `4c972a51-picks-count-arithmetic` — the arithmetic defect above.
2. `4c972a51-even-estimate-tiebreak` — new tie-break rule; no probability changed.
3. `4c972a51-unranked-floor-thin-edge` — fixture `1082919` carries a 0.14-point edge from HLTV's unranked floor; labelled low confidence, published as-is.
4. `4c972a51-hltv-blocked-and-priceless` — intermittent HLTV access; no prices published.
5. `4c972a51-book-surfaces-are-shells` — most bookmaker pages return no usable match list.

## 6. Publication record

Filled in after the pull request is merged and the Pages deployment is confirmed.
