# CD37 corrected combined-tree prototype

**Status: disposable verification only.** This was not a live collection, PR, merge or deployment. The tree used `main` [`52091c5`](https://github.com/buffedlizard55-lab/MaltaProj3/commit/52091c5c3aac9fbd53cc9e9400a37026a1c27ea9), selected safety changes from PR #237 [`5600a3a`](https://github.com/buffedlizard55-lab/MaltaProj3/commit/5600a3a2e31d93fe3f86b81cdf31157a2b313fee), fresh-data browser corrections from PR #246 [`50bb201`](https://github.com/buffedlizard55-lab/MaltaProj3/commit/50bb2017c3edb3eed2c540830d327f2d9de732e2), and the CD37 audits.

## What was combined

- PR #237's original-HTML/manifest EGW replay, independent provider start, exact team identity, loader with fixtures + registry, fixture-bound publication replay, summary freshness/landmark changes and duplicate-ID validation.
- A single source-admission boundary: `domain.no_vig()` requires **both decimal legs > 1.01**, matching the existing reviewed reference policy and the relay documentation.
- PR #246's fresh-data browser assertions and the CD37 candidate/reconciliation checks.
- Current `main`'s newer scoped aliases and review findings were retained.

## Data correction and replay

The input was the dated 05:57Z candidate evidence. A simulation cleared only featured analyses whose own stored quotes had a leg `<= 1.01`; exactly `1082860` matched. Normal origination then replayed all saved evidence. No team, start, alias, pick or probability was hand-written.

`1082860` changed from the invalid Thunderpick `1.001 / 12.00` money line to the existing engine's **HLTV ranking research model**:

| Fixture | FlyQuest | Staqued | Direction | Method and limitation |
| --- | ---: | ---: | --- | --- |
| [1082860](https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860) | 52.300959% | 47.699041% | FlyQuest | [HLTV ranking](https://www.hltv.org/ranking/teams), uncalibrated and low confidence. Staqued has no ranking row, so the model uses its stated 0.0-point floor; lineups, stand-ins, form and veto remain unverified. |

The corrected complete feed became **25 active / 25 resolved / 0 unresolved**, with **14 external-line and 11 research-model rows**. The independent reconciler reported **zero validation-problem rows**. The featured feed legitimately has one fewer bookmaker pick; featured and complete coverage remain distinct.

## Verification

| Check | Result |
| --- | --- |
| CD37 EGW gate | **4/4 required checks pass**; sibling-price markup remains an informational zero-entry limitation |
| Source replay/build | **88 source rows passed** |
| Rendered row-source audit | **892 rows**: 873 official-linked, 9 explicitly unverified, 10 site-map, **0 source-less** |
| Brief acceptance audit | **10 pass / 0 info / 0 fail** |
| Internal links/assets/anchors | **929 passed** |
| Relevant unit suites on fresh/isolated fixtures | **166/166 passed** |
| Dated origination-upgrade suite on its original fixtures | **32/32 passed** |
| Full Playwright suite on corrected 25-row build | **117/117 passed** |

The 166 tests cover domain behavior, EGW collector/replay safety, summary landmarks, CD37 reconciliation/EGW audits, the publisher import guard and source integrity. The separate 32-test run avoids pretending that dated fixture-specific tests belong to a different live slate.

A later full discovery on this older fixture tree completed **1,415 tests: 1,413 pass / 2 fail**. Both failures were stale implementation-signature assertions: the old direct summary-block call and old one-argument EGW loader. PR #237's final merged code intentionally changed those contracts; both complete affected modules pass **25/25** on PR #273. The older run is not represented as green; see `integration-verification.md`.

## Remaining integration work

The actual owners still need to incorporate the price boundary and rerun a **real** collection. The simulation cannot prove a provider's current response or a Pages deployment. Moving heads must be audited again: PR #237 `eeb9bc86` still passed EGW at 07:11Z but had not added the `> 1.01` boundary; PR #246 `67d1356` still failed three EGW checks. The green prototype is evidence that a compatible combination exists, not permission to merge a different or older head blindly.
