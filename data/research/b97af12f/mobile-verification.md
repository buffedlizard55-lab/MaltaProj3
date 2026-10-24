# arena-b97af12f — phone and link verification

Observed **2026-10-24T06:45Z** from an offline local build of the checked-in data. The build is deliberately written to `/tmp/b97-site`, not over the legacy Pages root.

- Build: `index.html` 171,996 bytes; **829 internal links/assets/anchors verified**; row-source audit **777 rows / 0 without a source / 9 flagged unverified**; acceptance audit **9 pass / 1 info / 0 fail**.
- Phone: viewport meta present; `nav.mobile-status` links to `./origination/#picks` and `./origination/#unresolved`; executive summary links to the complete picks, unresolved register and Flagged for Review page.
- Dated record: the summary renders B97's `live-coverage.json` with the “dated observation, not a live claim” disclaimer.
- Tests: `tests/test_b97af12f_mobile.py` + `tests/test_b97af12f_reconciliation.py` — **12 passed**.

## Logged, not edited (other session owns the file)

1. The built summary still contains **two** elements with `id="no-line-research"`. PR #248 owns the duplicate-id guard and the phone findings register; B97 records it as `b97af12f-duplicate-no-line-research-anchor` rather than editing `scripts/build.py`.
2. The checked-in `data/latest.json` is **2026-10-15T08:36:13Z**, while the cache-busted live Pages summary served the **2026-10-23T20:10Z** snapshot with a staleness warning. A local build therefore compares B97's 31 future API rows against the older 80-row file and labels all 31 “missing from this build”. This is a build artifact, not proof that the live site lost 31 picks. Recorded as `b97af12f-local-snapshot-older-than-live-site`; publisher run `40071396534` was still pending at 06:46Z.

Manual review: [live summary](https://buffedlizard55-lab.github.io/MaltaProj3/?cb=b9710646) · [unresolved register](https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/) · [complete picks](https://buffedlizard55-lab.github.io/MaltaProj3/picks/) · [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/) · [PR #248](https://github.com/buffedlizard55-lab/MaltaProj3/pull/248).
