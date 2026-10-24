# arena-b97af12f — phone and link verification

Observed **2026-10-24T06:52Z** from an offline local build **after rebasing onto `origin/main` `a0c08fa`**. The build is written to `/tmp/b97-site2`, not over the legacy Pages root.

- Build: `index.html` 168,942 bytes; **828 internal links/assets/anchors verified**; row-source audit **807 rows / 0 without a source / 9 flagged unverified**; acceptance audit **9 pass / 1 info / 0 fail**; exactly **one** `id="no-line-research"` after main's duplicate-id fix.
- Phone: viewport meta present; `nav.mobile-status` links to `./origination/#picks` and `./origination/#unresolved`; executive summary links to the complete picks, unresolved register and Flagged for Review page.
- Dated record: the summary renders B97's `live-coverage.json` with the “dated observation, not a live claim” disclaimer.
- Tests: `tests/test_b97af12f_mobile.py` + `tests/test_b97af12f_reconciliation.py` — **12 passed** after the rebase.

## Logged, not edited (other session owns the file)

1. B97's **pre-rebase** local build (06:45Z, 171,996-byte summary, 829 links) contained **two** `id="no-line-research"` blocks. After `git pull --rebase origin main` the merged duplicate-id guard makes it unique. B97 records the earlier observation as `b97af12f-duplicate-no-line-research-anchor` but never edits `scripts/build.py` or its tests.
2. The checked-in `data/latest.json` is **2026-10-15T08:36:13Z**, while the cache-busted live Pages summary served the **2026-10-23T20:10Z** snapshot with a staleness warning. A local build therefore compares B97's 31 future API rows against the older 80-row file and labels all 31 “missing from this build”. This is a build artifact, not proof that the live site lost 31 picks. Recorded as `b97af12f-local-snapshot-older-than-live-site`; the newest publisher run must still be checked before final integration.

Manual review: [live summary](https://buffedlizard55-lab.github.io/MaltaProj3/?cb=b9710646) · [unresolved register](https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/) · [complete picks](https://buffedlizard55-lab.github.io/MaltaProj3/picks/) · [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/).
