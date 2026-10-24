# CD37 PR #273 integrated verification

Recorded 2026-10-24T07:40:14Z on immutable head [`3598c9b5`](https://github.com/buffedlizard55-lab/MaltaProj3/commit/3598c9b5b41b8fa9ca9049f84220daf0b91711f4), with merge base `275771bd`. PR: [#273](https://github.com/buffedlizard55-lab/MaltaProj3/pull/273).

## Local gates on the actual integrated tree

| Check | Result |
| --- | --- |
| Non-actionable price gate | `domain.no_vig` rejects either leg `<= 1.01`; the retained `1.001 / 12.00` case has a direct regression test |
| EGW source safety | **4/4 required checks pass**: loader, original-response replay, independent provider start and exact identity. [JSON](egw-integration-pr273.json) |
| Targeted Python | **150/150 passed** across the new price gate, domain, CD37 audits, origination upgrade and source integrity |
| Build/source replay | **80 source rows passed** |
| Rendered sources | **834 rows**: 815 official-linked, 9 explicitly unverified, 10 site-map, **0 source-less** |
| Acceptance | **9 pass / 1 info / 0 fail** |
| Links/assets/anchors | **829 passed**; nine current Pages views |
| Full Playwright | **117/117 passed in 6.5m**, including phones, no-JS, WCAG, category pages and PR #237 landmarks |

## Older full-suite result, kept distinct

The earlier disposable fixture tree completed **1,415 tests: 1,413 pass / 2 fail**. The failures were stale implementation-signature assertions: one expected a direct summary-block call and one expected the old one-argument EGW loader. PR #237's final merged code deliberately changed those contracts. Both complete affected modules pass **25/25** on PR #273. This does **not** turn the older run into a green full-discovery result; current full Python CI remains authoritative.

## Candidate versus publication

The stored-evidence simulation remains 25/25 resolved, 14 external-line and 11 research-model after rejecting only the invalid featured quote and running the normal ladder. It is not a live collection. See [combined prototype](combined-prototype.md).

No merge, fresh deployment or public-readback is claimed at this checkpoint. Older manual publisher run [40074120319](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40074120319) was queued on unsafe main `06f56c2b`; cancellation returned GitHub 403, so it was not stopped. The fixed publisher must supersede any output, followed by a complete public row/link/phone verification.
