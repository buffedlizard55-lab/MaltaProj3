# Final-integration review — arena-52212e8e

Observation checkpoint: **2026-10-24T06:30:37Z**. This is a read-only review while the active publisher, source-safety and mobile sessions finish. No probability, pick, alias or production source file was changed.

## Current public state vs current lobby

- The [deployed executive summary](https://buffedlizard55-lab.github.io/MaltaProj3/) visibly warns that its snapshot needs attention. It reports **19 active / 19 directional picks / 12 external-line / 7 research-model / 0 unresolved** for its older inventory observation (**23 Oct 2026, 22:09 Europe/Malta**).
- Both rendered chunks of the official [Hotspawn CS2 lobby](https://play.hotspawn.com/cs2-pickems) were read. **Closing Soon + Upcoming contain 25 future fixture cards**. Hotspawn's community selection percentages were ignored.
- A fresh runner capture linked from [PR #246's evidence](https://github.com/buffedlizard55-lab/MaltaProj3/blob/arena/89c00d8a-maltaproj3/data/research/89c00d8a/live/origination.json) has **25 active / 25 resolved / 25 directional picks / 0 unresolved** at source snapshot `2026-10-24T05:57:37Z` (13 market, 2 bookmaker, 10 model, 1 network, 0 aggregated reference). This shows that the current coverage blocker is publishing the verified fresh build, not a need to invent values.

## Baseline verification on `bdb4fc9`

| Check | Result |
| --- | --- |
| Saved-evidence replay / build | PASS; 80 source rows replayed |
| Row-source audit | 770 rows; **0 without a source**; 9 explicitly flagged unverified |
| Acceptance audit | 9 pass · 1 info · **0 fail** |
| Internal links/assets/anchors | **829 PASS** |
| Targeted unit tests | **130 passed**, 2 skipped |

The first attempt lacked the sandbox's Python dependencies. After installing the repository's pinned `requirements.txt` into its ignored `.venv`, the results above were reproduced. That environment setup issue is not counted as a repository failure.

## Integration irregularity caught before merge

At [PR #245 head `4975f671`](https://github.com/buffedlizard55-lab/MaltaProj3/pull/245), the combined EGW code is weaker than the dedicated safety implementation at [PR #237 head `ced36cb3`](https://github.com/buffedlizard55-lab/MaltaProj3/pull/237):

1. `egw_live.load_live()` accepts a synthetic **derived-only** JSON capture without original HTML or a successful original-request manifest (reproduced: one entry accepted).
2. The saved excerpt is generated prose, not literal source markup.
3. `originate.run()` does not add `egw_live.load_live(...)` to `reference_rows`, so the automatic capture does not enter the pricing ladder.
4. The publication replay checks only the static reviewed reference capture for `family=reference`.
5. The 29 adversarial tests in `tests/test_be019782_egw_safety.py` on #237 are absent from #245.

This was reported to the active owner in [PR #245's integration comment](https://github.com/buffedlizard55-lab/MaltaProj3/pull/245#issuecomment-6380923705). No owned file was edited here. The dedicated #237 implementation passed **147 targeted tests** and a full local build (**776 rows / 0 sourceless / 826 links / acceptance 9 pass, 1 info, 0 fail**); that safer implementation and its tests should survive the final merge.

## Mobile verification

The combined phone UI at #245 was tested separately from the EGW concern. **12 Playwright checks passed**, covering:

- complete-picks finder and navigation at **320, 390, 768 and 1440 px**;
- every complete pick readable and source-linked at **320 and 390 px**;
- executive-summary links to the complete feed;
- no-JavaScript access to picks and sources;
- coverage cadence and workflow links on phones.

## EGW source limitation verified first-hand

The [EGW CS2 index](https://egamersworld.com/counterstrike/matches) and a [Fokus–ex-6666 match page](https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/fokus-vs-ex-6666-YL1WJpBDm) publish teams and decimal prices, but the extracted visible date/time does not prove a UTC instant. The match page's title and body also expose different clock representations. No timezone was guessed and no Hotspawn start was copied into provider evidence. Refusing such a row until original markup independently proves the start is the correct fail-closed behaviour.

## Fresh replay and research-only coverage

- The [25-row replay report](fresh-25-replay.md) lists every fresh pick, both independently originated probabilities, method, official Hotspawn link and model/line source. **25/25 passed both production saved-evidence validators; 0 unresolved; 15 external-line; 10 research-model; 0 missing source links.** A later independent CD37 acceptance audit rejects **one row (`1082860`)** for its raw 1.001/12 non-actionable quote, so the candidate is not acceptance-clean until that quote is rejected and the ladder rerun. The 10 model rows have a separate limitations register in that report.
- The [research coverage review](research-coverage-review.md) checks those 10 rows against the dated HLTV-first/esportsbook sweeps on PRs #237 and #246. All **10/10** are covered by both records; both recorded **0 eligible new money-line leads**, leaving **0 unclaimed residual fixtures**. Broad or rejected books remain limitations rather than probabilities to copy.
- An older manual Ground Zero–Off Chops EGW dossier records prices but not a timezone-qualified provider start or original response body. Its historical percentage was **not** used to overwrite the fresh validated network-model row. This is a provenance limitation, not a claim that the source price was fabricated.

## Latest integration checkpoints

- `origin/main` `4a6c112a` was merged locally with the complete shared board preserved. The first ordinary `pull --rebase` attempted to flatten that merge and stopped on a board conflict; the rebase was aborted without losing the merge, then `pull --rebase=merges` completed and the same merge commit `682530bf` pushed as a fast-forward.
- PR #237 head `013eed255e3386cf7fd99c56aa150829a75ab292` retains `tests/test_be019782_egw_safety.py`. **99 targeted tests passed (2 skipped)** and its standalone build passed (**786 rows / 0 sourceless / 827 internal links**).
- The current combined review branch passed **50 targeted tests**, build/replay, **783 rows / 0 sourceless**, acceptance **9 pass / 1 info / 0 fail**, and **827 internal links**. After the research register was added, its build and **21** review/audit/source tests also passed (**784 rows / 0 sourceless / 827 links**).
- **Historical import blocker independently reproduced and now resolved:** at 06:49Z, `tests.test_f9d0a5a2`, `tests.test_origination_upgrade` and `tests.test_source_integrity` ran **81 tests with 9 errors**, all `NameError: egw_live is not defined` in `live_collect`. PR #246 head `a52407d9fe08c65c67690f11161fdb89bf74cbe4` passed the identical **81/81** suites. Main `a0c08fa6` has now integrated the import and regression guards through PRs #252/#257, so this specific crash is resolved.
- **Full browser checkpoint:** PR #237 head `013eed255e3386cf7fd99c56aa150829a75ab292` passed **108/108 Playwright tests in 6.3 minutes**, including phone/tablet/desktop layouts, no-JavaScript behavior and automated WCAG scans. The fixture subprocesses were rerun with the repository virtualenv on `PATH`; an earlier system-Python dependency setup failure was not counted as a product result.
- **Full Python checkpoint:** on that same pinned `013eed25` tree, `python -m unittest discover -s tests` completed with **1,362 tests in 1,157.823 seconds: OK** (exit 0). This is not a claim about newer heads; the final integrated head still needs its own checks.
- **Newer safety-head checkpoint:** PR #237 `8ed62fa2d05746243e981511b2a9b23de8a1abfd` passed **213 targeted tests (2 skipped)**, retained **0 derived-only EGW rows / no quote** in the adversarial probe, and built with **804 audited rows / 0 sourceless / 827 internal links / acceptance 9 pass, 1 info, 0 fail**. Its newest commits carry `[skip ci]`, so these local results are recorded rather than assuming CI ran.
- **Source-precision correction:** the retained raw Thunderpick response in PR #246 records FlyQuest–Staqued event `2872333`, market `240164875`, as **1.001 / 12**, not exactly 1.00 / 12 (raw SHA-256 `a1ed97aee7c99b14f3aa05cef4647742abb593d80ee026f2b48e328448d986b8`). PR #246 head `67d13568` nevertheless renders `line 1.00 / 12.00` because the summary rounds to two decimals. The exact-1.00 premise in merged flag `e619b921-thunderpick-decimal-price-of-1-00-published` is therefore unsupported by the original response. Reported at [PR #246](https://github.com/buffedlizard55-lab/MaltaProj3/pull/246#issuecomment-6381190173) and [PR #256](https://github.com/buffedlizard55-lab/MaltaProj3/pull/256#issuecomment-6381190305). The extreme near-1 price remains a limitation; no replacement price, probability or pick was written by hand.

## Final acceptance gates

1. **Original-response EGW replay.** On main `a0c08fa6`, a synthetic valid-schema derived-only EGW entry was accepted and `reference_odds.quote` produced a quote without original EGW HTML or a successful request manifest. PR #237 head `5600a3a2` rejected the identical input (**0 rows / no quote**). This was [reported to the active owner](https://github.com/buffedlizard55-lab/MaltaProj3/pull/237#issuecomment-6381127387). The import fix alone is not a substitute for the safe replay boundary.
2. **Newer 31+ inventory.** The [31-fixture inventory review](latest-31-inventory-review.md) computes six exact Hotspawn IDs added after the 25-row certificate, with none removed. The `06:15Z` manifest reports **31/31 picks, 0 unresolved, 18 money-backed and 13 research-only**; all 13 have dated research and **0 eligible new leads**. Its scratch original evidence was not retained, so final sign-off requires the successful Pages root-synced `data/latest.json`, `data/origination.json` and evidence tree, followed by replay and a then-current inventory comparison.
3. **Actionable price admission + exact source display.** CD37 independently owns the candidate gate requiring every bookmaker decimal leg to be **>1.01**; it rejects `1082860` in the 25-row candidate. The final ladder must reject that quote before no-vig and produce a valid sourced fallback or explicit unresolved entry. The build must also avoid rounding any retained 1.001 source value into an apparent 1.00 fact, and the review register must not repeat the corrected exact-1.00 claim as verified. No replacement price, pick or probability is hand-authored; the actual final quote comes from retained deployment-time evidence.

## Machine-readable record

See [`integration-review.json`](integration-review.json), [`fresh-25-replay.json`](fresh-25-replay.json), [`research-coverage-review.json`](research-coverage-review.json) and [`latest-31-inventory-review.json`](latest-31-inventory-review.json) for exact heads, counts, commands, source links and findings.

## C6B8 merged-research integration audit — 2026-10-24T07:14:33Z

- Merged main `06618b31` (PR #265) without rewriting its historical research. The new [C6B8 reference integration review](c6b8-reference-integration-review.md) uses C6B8's own 31-row `live-coverage.json`, not fixtures constructed from each reference entry.
- **Seven schema-valid EGW entries → three exact-inventory gate accepts and four start-mismatch rejects.** The rejects are `1082858`, `1082996`, `1079198`, and `1079200`; their captured/provider starts must not be overwritten with Hotspawn values.
- Direct official-page recheck of the three accepts: `1083122` displays **2.92/1.33** and its bookmaker-average sentence; `1082861` and `1082792` display **1.8/1.8**, while their captured prices are attributed only to the EGW index. Those two require exact index evidence and a reviewable source association before production use. EGW title/body clock labels differ and no unnamed timezone was inferred.
- Five of six rejected equal-side placeholder rows also have inventory team/start mismatches. They have no pricing effect because they are rejected, but the identities remain flagged against reuse.
- C6B8's capture path is not registered in production `CAPTURE_PATHS`; this audit added no path and changed no production pick, price, probability, or alias. Four source-linked findings were added to `flags.json`.
- Verification on the merged tree: **106 targeted tests passed**, including the new real-inventory reference-gate regression, C6B8 checks, and incoming watchdog contracts. Build/replay passed: **828 audited rows / 0 sourceless / 829 internal links / acceptance 9 pass, 1 info, 0 fail**. Watchdog network dispatch in tests was stubbed; this is not evidence of a live Pages recovery.
