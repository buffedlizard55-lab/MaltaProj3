
## S522-C6B8-001 — reference captures checked against actual inventory

At main `06618b31` (PR #265), C6B8 has 7 schema-valid EGW reference entries, but the unchanged production gate against its own 31-row inventory accepts only **3** and rejects **4** for exact-start drift. Direct recheck of the three accepts finds **one** linked page with the quoted price (1083122, 2.92/1.33) and **two** linked pages showing 1.8/1.8 (1082861 and 1082792). Five of six rejected placeholder rows also have team/start mismatches. The capture is not registered in production and this audit changes no prices. Full row-by-row evidence: `c6b8-reference-integration-review.{json,md}`; four flags are published in `flags.json`.

## S522-COUNTS-001 — 719 missing-card count reconciliation

The 719 file has **9** missing cards: **4** with reference lines and **5** without. All five blanks are CCT #12. The fifth priced row in the full 25-card file is `1079193`, already published, so it cannot be counted among the nine. The board/prose statements “5 of 9” and “four CCT #12 cards” are therefore flagged as documentation inconsistencies; the active 719 records were not edited and no probability changed.

## Active candidate checkpoints — 2026-10-24T07:23Z

- **PR #238 `6d55f34a`:** independent S522 archive run passed **84 targeted tests (2 skipped)** and build/replay (**825 rows / 0 sourceless / 833 links / acceptance 9 pass, 1 info, 0 fail**). The strict EGW tests survive, but the PR is conflicted and both Thunderpick admission and `domain.no_vig` still reject only `<=1`; this is not a final merge candidate.
- **CD37 `730561f9`:** the owner reports a disposable `>1.01` prototype producing **25/25 picks, 14 external-line + 11 research-model**, with `1082860` rerunning to the existing HLTV ranking model at **52.300959% / 47.699041%** and explicit unranked-floor limitation. It also reports 166+32 unit tests and 117/117 browser passes. S522 did not rerun that prototype; it is not live collection, merge, or deployment evidence. The real head still needs the boundary and a fresh featured collection.

## S522-TESTDEP-001 — merge-blocking missing test dependency

Main `06f56c2b` and PR #237 `0baf556d` both fail `tests.test_b97af12f_reconciliation` at import with `ModuleNotFoundError: pytest`; the workflows install only a requirements file that does not declare it. Reported to #237 and #267. With pytest installed only in the ignored local virtualenv, #237 `0baf556d` passed **85 targeted tests (2 skips)** and built **831 rows / 0 sourceless / 829 links**. That local workaround is not a runner fix and does not clear final integration.

## S522-FRESH31-001 — retained 31-row replay, one acceptance blocker

PR #246 `85d2a06c` now retains a 31-row candidate and original evidence. Current main `4b278f4e` passes **92 featured source rows** and **31/31 complete rows**: 31 picks, 0 unresolved, 20 external-line, 11 research-model, 0 missing source links. CD37 exits 1 on exactly `1082860` (raw 1.001/12). The candidate is therefore a verified coverage artifact but **not acceptance-clean and not deployed**. Full tables: `fresh-31-replay.{json,md}`; copied independent reconciliation: `fresh-31-cd37-reconciliation.json`.
