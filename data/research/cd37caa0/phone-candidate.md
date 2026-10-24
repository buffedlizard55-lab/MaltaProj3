# CD37 fresh-candidate phone and browser verification

## Candidate under test

The scratch builds used the dated PR #246 runner evidence from immutable head [`50bb201`](https://github.com/buffedlizard55-lab/MaltaProj3/commit/50bb2017c3edb3eed2c540830d327f2d9de732e2): inventory observed **2026-10-24T05:57:37Z**, **25 active / 25 resolved**, 15 external-line rows and 10 research-model rows. The evidence was copied into otherwise disposable trees; production data was not overwritten. The independent [coverage reconciliation](coverage-reconciliation.md) confirms that these 25 IDs match the official lobby and differ from the older 19-row deployment.

## Results

| Code under test | Build and source audit | Browser result |
| --- | --- | --- |
| Main base [`bdb4fc9`](https://github.com/buffedlizard55-lab/MaltaProj3/commit/bdb4fc92a30989e93263d7ef3842cda045fe6571) + fresh evidence | PASS: 88 replayed rows; 855 rendered row-source entries, zero source-less; 10/10 acceptance checks; 924 links/assets/anchors | Initial spec: 2 passed / 3 failed. Every failure was the same duplicate `no-line-research` ID on `/`; no phone overflow was found before that assertion stopped the test. |
| PR #237 [`013eed2`](https://github.com/buffedlizard55-lab/MaltaProj3/commit/013eed255e3386cf7fd99c56aa150829a75ab292) + fresh evidence | PASS: 88 replayed rows; 871 row-source entries, zero source-less; 10/10 acceptance checks; 925 links/assets/anchors | CD37 spec **5/5 passed**. |
| PR #246 [`50bb201`](https://github.com/buffedlizard55-lab/MaltaProj3/commit/50bb2017c3edb3eed2c540830d327f2d9de732e2) + fresh evidence | PASS: 88 replayed rows; 857 row-source entries, zero source-less; 10/10 acceptance checks; 920 links/assets/anchors | Entire Playwright suite **109/109 passed**, including the five CD37 tests. The final clock-aware revision of the CD37 spec then passed **5/5** again. |

The candidate spec is [`tests/browser/cd37caa0_candidate.spec.mjs`](../../../tests/browser/cd37caa0_candidate.spec.mjs). At **320px and 390px** it checks:

- the summary's one-tap link to the complete list and the separate unresolved/no-line registers;
- the actual feed count, one card per fixture ID, both rendered probabilities, the directional pick when one exists, and explicit blanks for unresolved rows;
- Hotspawn's official match URL and the independent analysis URL on every sourced card;
- current versus historical labels from the snapshot/line observation times, including a no-JavaScript path;
- unique fragment IDs, no horizontal overflow, and a 390px WCAG A/AA scan.

Static HTML contains both current and historical spans for no-JavaScript/runtime safety. The test checks **visible** elements; it does not mistake hidden fallback text for a stale pick.

## Suite triage and limits

An exploratory full-suite run on the PR #237 tree produced 83 passes, 7 failures and 23 tests not run. Four fixture-setup failures were caused by the local command omitting `PYTHONPATH=/tmp/cd37/pydeps`; the remaining dated assertions were among the fresh-data browser corrections present in PR #246. That run is not represented as a green suite. The corrected PR #246 run is the 109/109 result above.

PR #237 and PR #246 later advanced to `5600a3a2e31d93fe3f86b81cdf31157a2b313fee` and `67d135687e679a4ac3ae005e5c83f039422e11e2`. The archived browser result is not transferred to those new heads. Their EGW behavior was re-audited separately: current #237 passes all four required checks; current #246 passes loader wiring but fails original-response replay, independent provider start and exact team identity. Browser success never waives those defects.

**No Pages deployment or merge is claimed by this report.** It establishes candidate build/phone readiness only. Final integration must rerun the checks on the exact merged head and then verify the public deployment.
