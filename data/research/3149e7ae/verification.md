# Brief-line verification of the published site — 2026-10-23T05:00Z

Session `arena-3149e7ae`. Everything below was read back from the repository and the
published branch root through the official GitHub contents API, then re-checked against a
local build of the checked-in data. Nothing here is inferred, and no value was filled in.

## What was checked, and where the evidence lives

| Brief line | Check | Result | Evidence |
| --- | --- | --- | --- |
| "I want picks for every match listed on hotspawn" | every listed fixture states an active count, renders that many rows, and the reconciled snapshot agrees | **pass** — 37 stated, 37 rendered, 37 active in the snapshot | `acceptance-published-2026-10-23T0505Z.json` |
| "give probability to win for the team to win … obvious what the pick is" | every glance row names a pick, shows both percentages, the pair sums to 100, and links an official/primary source | **pass** — 37/37 | same file, `glance_rows` |
| "a separate section for any unresolved picks and the limitations … in the executive summary" | `#unresolved-register` exists inside the executive summary, its heading names unresolved picks, and it carries the limitations of generating them | **pass** — 5 limitations, 0 pick-less cards at this snapshot | same file, `unresolved_register` |
| "an executive summary that provides links within our site to where an updated list of picks can be found" | in-site links to the complete list (`origination/#picks`), the picks page and the unresolved section all resolve to built pages | **pass** | same file, `exec_links` |
| "easily readable and accessible on phone and mobile device" | every page declares a device-width viewport; the glance index is a list styled by `assets/scout.css` with a small-screen media query | **pass** — 11 published pages | same file, `mobile` |
| "updated … every 4-8 hours" | the scheduled entries in `.github/workflows/pages.yml` never leave a gap above 8 h, and the snapshot declares a 4 h interval with an 8 h stale bound | **pass** — largest gap 2.5 h | same file, `cadence` |
| "Every table row must have a source link … if a value can't be confirmed … leave it blank and flag it" | the built row-source audit reports no row without a source | **pass** (local build) — 646 rows, 627 official links, 9 explicitly flagged unverified, 0 without a source | `acceptance-local-build-2026-10-23T0505Z.json` |
| "It should be up to date" | the page the reader sees and the JSON they download are the same observation | **FAIL** — page `2026-10-22T14:05:35Z`, root `data/latest.json` `2026-10-15T08:36:13Z`, 173.5 h apart | `acceptance-published-2026-10-23T0505Z.json`, `snapshot_consistency` |
| "regularly check for updates" | the published snapshot's age is stated | **info** — 14.9 h old at 05:00Z and the page correctly warns the reader | same file, `freshness` |

## Sources used (all official, all re-readable)

- Published executive summary: <https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/index.html>
- Published downloadable snapshot: <https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/latest.json>
- Published pages checked: `picks/`, `unresolved/`, `origination/`, `review/`, `coverage/`,
  `methodology/`, `edge/`, `twc-picks/`, `final-day/`, `strategy/` (same repository, `main`, commit
  `cd95411`), plus `assets/scout.css`
- Refresh schedule: <https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/.github/workflows/pages.yml>
- Failing scheduled runs (freshness cause): <https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39881298806>,
  <https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39871371551>,
  <https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39861117407>,
  <https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39845991470>

## Irregularities and limitations (published on /review/)

1. The published page was 14.9 h old at 05:00Z and said so; every scheduled refresh after
   2026-10-22T14:05Z failed in the regression-test step. Flagged, with the run ids.
2. The published root `data/latest.json` disagrees with the page it sits under by 173.5 h.
   Flagged; the fix lives in `scripts/root_publish.py`, owned by another live session
   (`arena-308fcaad`), so the request is logged in `COORDINATION.md` rather than edited here.
3. 12 of 37 listed fixtures had no external betting line and carry labelled research estimates.
   This is the "low tier / not covered" class in the brief; it is a limitation of the source
   coverage, not a missing pick, and it is published next to the picks.
4. Not verifiable from this environment: the rendered convenience of the site on a physical
   phone (no browser or mobile network here). What is verified is the markup and the stylesheet
   that the phone layout depends on. The repository's Playwright suite runs at 320/390 px in CI.

## Reproduce

```bash
python -m scripts.build                                    # writes site/ plus data/acceptance-audit.json|md
python -m scripts.acceptance_audit --site site --strict    # exit 1 if a brief line is not met
python -m unittest tests.test_3149e7ae_acceptance           # the audit's own failure modes
```
