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

## Machine-readable record

See [`integration-review.json`](integration-review.json) for exact heads, counts, commands, source links and findings.
