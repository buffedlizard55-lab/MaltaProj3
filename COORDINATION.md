# Shared coordination board

Session: `arena-4aae8328` · Branch: `arena/4aae8328-maltaproj3`

This session is fixed to the Arena branch above. No alternative session branches are created. The repository contained only `README.md` at initial inspection; no other task claims existed.

## Tasks

| Task | Status | Owner | File scope | Last update (UTC) |
| --- | --- | --- | --- | --- |
| Discover and verify Hotspawn CS2 match sources and external probabilities | done | arena-4aae8328 | `scripts/`, `tests/`, `data/`, `docs/` | 2026-10-14 |
| Mobile-first dashboard, picks, coverage, methodology, review pages | done | arena-4aae8328 | `index.html`, `picks/`, `coverage/`, `methodology/`, `review/`, `assets/` | 2026-10-14 |
| Automation, integration, validation and GitHub Pages publication | done | arena-4aae8328 (final integration) | `.github/`, `README.md`, `.gitignore`, dependency/configuration files, `COORDINATION.md` | 2026-10-14 |

This session’s claimed tasks are complete. The initial scopes were non-overlapping at first inspection; later concurrent integration overlaps and non-destructive handoffs are documented below. Historical boards are preserved unchanged. Unverified source data and unresolved matches are publication warnings, not hidden omissions or invented probabilities. Broken builds are blockers.

## Activity and handoffs

- 2026-10-14: Inspected repository and remote; only the 12-byte README existed. Claimed the tasks above before implementation. No existing source data, application, automation or featured-pick method was present to preserve.

## Verification and sources

Verified every Hotspawn CS2 fixture against both official lobby payloads and the public fixture API, with original observation times and saved evidence. All current estimates replay from original Polymarket order books, original Thunderpick POST prices or explicitly labeled official Valve-rating inputs. HLTV/access limitations and unsupported identities remain visible. Hotspawn participation/popularity is never a probability input. Full snapshot and evidence: <https://buffedlizard55-lab.github.io/MaltaProj3/coverage/>.

## Publication

PR [#3](https://github.com/buffedlizard55-lab/MaltaProj3/pull/3) merged at 05:35:34 UTC as `dc4d4818845598885a93a0dd5031465c7cc84d38`; publication repair [#11](https://github.com/buffedlizard55-lab/MaltaProj3/pull/11) merged at 05:45:09 UTC as `63f005bc6e1ea53496c6779ce9729997f2d5faf8`. Production [38518319041](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38518319041) **succeeded**, including public post-deploy verification, at **2026-10-14 05:46:22 UTC**. Live: <https://buffedlizard55-lab.github.io/MaltaProj3/>. Four-hour refresh is active. The repository’s Pages-mode restriction is published as a nonblocking review item; publisher ordering was verified.


---

## Preserved concurrent-session boards from main

The following records are preserved from main during integration. Their branch constraints describe their own sessions, not a change to this session’s fixed branch.

# Coordination Board

> **Repository session constraint:** Arena requires all work in this session to remain on
> `arena/5ebd8496-maltaproj3`. This is the integration branch for the work below.
>
> **Update rule:** Add an entry before changing a new file scope. Do not edit an active,
> overlapping scope owned by another session.

| Task | Status | Owner | File scope | Started (UTC) | Notes |
| --- | --- | --- | --- | --- | --- |
| Build and publish the verified CS2 match-picks GitHub Pages dashboard (root-site integration) | done | arena/5ebd8496-maltaproj3 | root site, `assets/`, `data/matches.json`, `data/review.json`, `scripts/refresh-data.mjs`, root Pages workflows | 2026-10-14 | Root dashboard is live. Exact public-market resolver refreshed 18/28 lines; remaining 10 are explicitly unresolved and linked to review. The separate `docs/` dashboard merged by session 83207e7b remains a documented non-destructive overlap (I-20), not the root-site production artifact. |

## Activity log

- **2026-10-14 — arena/5ebd8496-maltaproj3:** Created the coordination board and claimed the final integration scope. No pre-existing tasks or file ownership records were present.
- **2026-10-14 — arena/5ebd8496-maltaproj3:** Root-site implementation merged through PRs [#1](https://github.com/buffedlizard55-lab/MaltaProj3/pull/1), [#2](https://github.com/buffedlizard55-lab/MaltaProj3/pull/2), [#4](https://github.com/buffedlizard55-lab/MaltaProj3/pull/4), [#6](https://github.com/buffedlizard55-lab/MaltaProj3/pull/6), [#7](https://github.com/buffedlizard55-lab/MaltaProj3/pull/7), and [#9](https://github.com/buffedlizard55-lab/MaltaProj3/pull/9). Verified `node scripts/verify-site.mjs` locally and the successful production Pages run [38513917128](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38513917128). The public refresh run [38513621759](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38513621759) populated 18 independently sourced match-winner lines out of 28 schedule rows. Ten rows remain intentionally blank and are published through the root-site Flagged for Review flow. The root landing and full picks pages were manually rechecked after deploy.


---


Repo: `buffedlizard55-lab/MaltaProj3`
### Session 83207e7b board (added at merge)

Session ID: `83207e7b`
Session branch: `arena/83207e7b-maltaproj3` (all work is committed and pushed only to this branch; PR opened from it to `main`)

Status values: `unclaimed` · `in progress` · `done` · `needs review` (published on the Flagged for Review page; does not block merge)

Claim protocol: before editing a file, a session adds or updates its row here with its session ID and file scope, commits and pushes the claim, then runs `git pull --rebase` before each push. Small commits. Merge conflicts are logged under Conflicts. Shared outputs (`docs/`, `data/`, `scripts/`) are integrated only by the final integration session.

| Task ID | Task | Status | Owner (session) | File scope | Notes |
|---|---|---|---|---|---|
| T1 | Repo review | done | 83207e7b | `README.md`, `COORDINATION.md` | See I-01, I-02. |
| T2 | Hotspawn CS2 match capture | done (partial, see I-03 to I-05) | 83207e7b | `data/matches.json` | Source: https://play.hotspawn.com/lobby and linked match pages. |
| T3 | Outside market lines (Polymarket, Stake, Oddsportal) | done | 83207e7b | `data/matches.json` | Pinnacle and Thunderpick not usable (I-08, I-09). |
| T4 | HLTV ranking input (top 30, Oct 12 2026) | done | 83207e7b | `data/matches.json` | https://www.hltv.org/ranking/teams/2026/october/12 |
| T5 | Pick engine and unresolved logic | done | 83207e7b | `scripts/build_site.py` | Method on `docs/methodology.html`. |
| T6 | GitHub Pages site | done | 83207e7b | `docs/**`, `scripts/build_site.py`, `README.md` | Built from `data/matches.json`. |
| T7 | Integration: rebuild, link check, PR to main, merge, Pages check | in progress | 83207e7b | all | This session is the integration session. |
| T8 | Scheduled refresh (every 4–8 h) | needs review | — | (none created) | Cannot be scheduled from this session. See I-16. |

## Task log

### T1 — Repo review (done)
- `git status` at review: only `COORDINATION.md` was new.
- Branches: `main`, `arena/83207e7b-maltaproj3`. Remote `origin/main` at `8a3139f` (Initial commit).
- `README.md` contained one line (`# MaltaProj3`). No data, site, or coordination board existed before this session.
- GitHub Pages was already configured: built from branch `main`, path `/`.

### T2 — Hotspawn capture (done, partial)
- Lobby: https://play.hotspawn.com/lobby. Header says "68 matches this week"; tier counts and tournament filter counts sum to 88.
- The lobby is a rolling window. The capture holds 28 match cards with match-page links (or the lobby link where none was captured).

### T3 — Market lines (done)
- Polymarket: https://polymarket.com/esports/cs2/elisa-breakout, /stake-pulse, /thunderpick-world-championship, /cct-europe, and per-match pages.
- Stake: https://stake.com/de/sports/esports/counter-strike (German locale, decimal odds; first 10 CS2 events).
- Oddsportal: https://www.oddsportal.com/esports/counter-strike/counter-strike-thunderpick-world-championship/ (2 matches with odds).

### T4 — HLTV (done)
- Top 30 extracted with points. Teams outside the top 30 are "not ranked" (no points used).

### T5/T6 — Engine and site (done)
- `scripts/build_site.py` reads `data/matches.json` and writes `docs/`.

## Irregularities / flags (also published on the Flagged for Review page)

| ID | Item | Detail | Source link(s) | Status |
|---|---|---|---|---|
| I-01 | Repo state | No picks, site, or coordination file existed at session start. | https://github.com/buffedlizard55-lab/MaltaProj3 | needs review |
| I-02 | Branch naming | The task text names an integration branch to `main`; the session is fixed to `arena/83207e7b-maltaproj3`. The session branch is used for the PR. | — | needs review |
| I-03 | Match count mismatch | Lobby header says 68 matches this week; tier counts and tournament filter counts sum to 88. | https://play.hotspawn.com/lobby | needs review |
| I-04 | Coverage | Only 28 match cards were captured. The lobby is a rolling window, so the other matches are not covered by this snapshot. | https://play.hotspawn.com/lobby | needs review |
| I-05 | Lobby changes between fetches | Lobby times and the closing-soon list changed between fetches. The fetch tool returns no timestamp, so the snapshot date is the session date only. | https://play.hotspawn.com/lobby | needs review |
| I-06 | Time zones | The first lobby snapshot showed ET; later snapshots showed UTC. Times are shown in UTC, converted +4h from the ET snapshot. Cross-checked against Polymarket ET times and Stake UTC times. | https://polymarket.com/esports/cs2/cct-europe ; https://stake.com/de/sports/esports/counter-strike | needs review |
| I-07 | Missing match link | mellren vs Privateer Gaming (CCT Europe S12 Play-In, Oct 16) has no captured Hotspawn match link. | https://play.hotspawn.com/lobby | needs review |
| I-08 | Pinnacle unavailable | https://www.pinnacle.com/en/esports/counter-strike returned 404; https://www.pinnacle.com/en/esports returned HTTP 500. Not used. | https://www.pinnacle.com/en/esports | needs review |
| I-09 | Thunderpick unavailable | Thunderpick CS2 event pages returned only navigation (no match list or odds). Not used. | https://thunderpick.io/esports/cs2-betting/thunderpick-world-championship-2026/11024 | needs review |
| I-10 | Name mapping | Outside-source team names differ from Hotspawn (e.g., "Team Falcons"/"Falcons", "Aurora Gaming"/"Aurora", "Sashi Esport"/"Sashi", "WRAITH PCIFIC"/"PCIFIC", "BetBoom Team"/"BetBoom", "BC.Game Esports"/"BC.Game", "NIP"/"Ninjas in Pyjamas", "WBT"/"WROTBERRY"). Name containment used. Acronym-only mappings (WBT, EAC) are not used for picks. | https://polymarket.com/esports/cs2/cct-europe ; https://stake.com/de/sports/esports/counter-strike | needs review |
| I-11 | Polymarket price drift | The same market showed different prices in different fetches (ex-RUSTEC vs mellren 65/36 and 64/37; ENCE vs BOJONG 74/45 and 65/36; WBT vs EAC 48/52 and 56/60). | https://polymarket.com/esports/cs2/elisa-breakout | needs review |
| I-12 | Thin or unbalanced markets | Several Polymarket Elisa and CCT markets show $0.00 volume or implied totals outside 95–105%. Rule: a market is used only if volume is at least $50 and the implied total is within 95–105%. | https://polymarket.com/esports/cs2/elisa-breakout | needs review |
| I-13 | Model vs market disagreement | Heroic vs Envy: the market favours Heroic; the HLTV-points model favours Envy. The final line blends 70% market / 30% model; the pick stays Heroic with lower confidence. | https://polymarket.com/esports/cs2/stake-pulse ; https://www.hltv.org/ranking/teams/2026/october/12 | needs review |
| I-14 | Stake coverage | The Stake CS2 list shows 10 events per page ("Mehr laden" loads more). Six Hotspawn matches were on the first page; the rest were not captured. | https://stake.com/de/sports/esports/counter-strike | needs review |
| I-15 | Oddsportal coverage | Oddsportal has odds for 2 Hotspawn matches (9z–Aurora, Falcons–NiP). The Stake Pulse Beat III Oddsportal page showed no odds yet. | https://www.oddsportal.com/esports/counter-strike/counter-strike-thunderpick-world-championship/ | needs review |
| I-16 | Refresh not scheduled | A refresh every 4–8 hours was requested. It cannot be scheduled from this session. The snapshot date is shown on the site; a later session must rebuild it. | — | needs review |
| I-17 | HLTV team identity | "G2 Ares" (Hotspawn) is not confirmed as the HLTV team "G2" (#8). No HLTV points are applied to G2 Ares. | https://www.hltv.org/ranking/teams/2026/october/12 | needs review |
| I-18 | Hotspawn pick percentages | Hotspawn shows its own pick percentages. These are not used as a probability input anywhere in the model. | https://play.hotspawn.com/lobby | resolved (not used) |
| I-19 | Publication gap | `docs/` (this session's site) is merged but not in the Pages artifact built by `.github/workflows/pages.yml`, which publishes the root site only. Live `docs/` URL returns 404. Fix: one copy step in that workflow (owner: session arena/5ebd8496). | https://buffedlizard55-lab.github.io/MaltaProj3/ | needs review |
| I-20 | Two picks sites on main | Root site (session arena/5ebd8496; `data/matches.json`, 18 verified lines, 6-hour refresh) and `docs/` (session 83207e7b; `data/picks-model.json`, 14 picks, HLTV blend). The lines differ in places (e.g., Falcons–NiP, 9z–Aurora, ex-RUSTEC–mellren). Owner must pick the primary site. | https://buffedlizard55-lab.github.io/MaltaProj3/ | needs review |

## Handoffs / takeovers
- None.

## Conflicts
- C-1 (2026-10-14, session 83207e7b): `main` contained a separate Pages site from session arena/5ebd8496 (root `index.html`, `picks.html`, `assets/`, `data/matches.json`, `data/review.json`, `.github/workflows/pages.yml` and `refresh.yml`, `scripts/refresh-data.mjs`, `scripts/verify-site.mjs`). Both sessions claim the final integration. Resolution (non-destructive): their root site, workflows, `data/matches.json` and `data/review.json` are kept unchanged; this session's site is in `docs/` with data in `data/picks-model.json`; `README.md` and this board keep both sections. Overlap to be decided by the owner: which site is the published one. Until then, both are on `main`.
- C-2 (session 83207e7b): `scripts/__pycache__` was committed by mistake; removed and ignored in `.gitignore`.

## PR and merge
- PR #5 — `arena/83207e7b-maltaproj3` → `main`. Merged 2026-10-14 04:52:31 UTC, merge commit `cf49606`. Merge conflicts with `main` (another session's site) were resolved non-destructively (see C-1). Merge executed without waiting for approval; flagged items do not block merge.
- Pages check: the "Deploy GitHub Pages" workflow succeeded on `cf49606` (run completed success 04:52:34 UTC). The live root site loads its data (`data/matches.json`, `data/review.json`). `docs/` is not in the artifact (I-19), so its pages are not live.
- PR #8 records the above in this board (no change to site content).


## Rebase conflict log — arena-4aae8328

- 2026-10-14 05:07 UTC: `git rebase origin/main` found an add/add conflict in `COORDINATION.md`: concurrent sessions had each created a board from the empty baseline. Both boards are preserved in full. No task records or published review flags were discarded. This session continues only on `arena/4aae8328-maltaproj3`.


## Concurrent integration discovered — 2026-10-14

- While this session worked on its claimed scopes, two other sessions independently claimed and merged root/docs dashboards from the same empty baseline. Remote `main` now contains PRs #1/#2/#4/#5/#6/#7/#8/#9/#10. This session's original claim was pushed before any of those claims were present in this checkout.
- Root owner `arena/5ebd8496-maltaproj3` records its publication task **done** in main. The 83207e7b board records its implementation done and its integration row in progress, although its PR #5/#8 publication log records completed merges and nonblocking published review flags I-19/I-20. Request/handoff: preserve `docs/**`, `scripts/build_site.py`, `data/matches.json`, `data/review.json`, `data/picks-model.json` and all original root assets; do not have a second refresh job compete with the final Pages artifact.
- This session is integrating the reconciled 88-record inventory, validated live order books, original Thunderpick POST API prices and supported Valve-rating fallback. Its new asset names are `assets/scout.css`, `assets/scout.js`, `assets/scout-mark.svg` to avoid overwriting the root owner's `assets/styles.css` and `assets/app.js`. Legacy datasets and the other session's build script remain separate and are not silently treated as freshly verified inputs.
- PR #3: <https://github.com/buffedlizard55-lab/MaltaProj3/pull/3>. Before merging, fetch/rebase main, preserve both boards, record conflict resolution and validate the combined site and old links. Source coverage warnings do not block publication.

- The `.gitignore` add/add conflict was resolved by taking the union of both sessions’ patterns (plus `.venv/`). The final board-append conflict was resolved by preserving all main records and appending this session’s handoff notes. Existing application assets and datasets were not overwritten.

## Final production integration claim — arena-4aae8328 (2026-10-14 05:13 UTC)

| Task | Status | Owner | File scope | Integration boundary |
| --- | --- | --- | --- | --- |
| Unify the production entry point and scheduled Pages artifact | done | arena-4aae8328 | `index.html`, `picks/`, `coverage/`, `methodology/`, `review/`, legacy root HTML aliases, `.github/workflows/pages.yml`, `.github/workflows/refresh.yml`, `README.md`, `archive/root-session/`, new CI/browser configuration | Root owner records its task done in merged PR #10. Preserve original root pages/assets/data as an explicit historical archive before changing entry points. Do not edit `docs/**` pages, `scripts/build_site.py`, or the other sessions’ datasets. Their publication flags I-19/I-20 remain nonblocking review items until the combined artifact is validated. |

- The earlier integration's broad T7 `all` claim is recorded as a coordination overlap, not permission to delete or rewrite its files. Its actual implementation and merge records (#5/#8) are preserved; this integration does not alter that session's source files. Its HTML will be copied into the final artifact with an archive banner so there is one clearly designated current feed.
- Original HTTP discovery GETs to Thunderpick returned 403; the exact public-client **POST** `/api/matches` contract with `{"gameIds":[6]}` succeeded in run [38513997412](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38513997412). Four original bookmaker pairs passed strict identity/time/market checks. This corrects the initial access limitation without hiding the failed requests.
- Current verified snapshot: 88 source records = 28 future starts + 60 past starts. Nine supported Polymarket pairs, four original Thunderpick pairs and eight supported Valve-model estimates; seven unresolved. All 88 rows and every emitted calculation replayed successfully. Data is not a claim of 28 verified true win probabilities.

## Production integration verification — arena-4aae8328 (2026-10-14 05:25 UTC)

- Preserved the root session's original four HTML pages, original CSS/JS and original datasets under `archive/root-session/` before replacing any entry point. `docs/*.html`, the other sessions' scripts, assets and datasets remain unchanged. The generated artifact publishes both prior dashboards with archive banners and links back to the sole current feed. Old root `.html` URLs remain compatible.
- Local verification is complete: **40 Python regression tests pass**, every one of the **88 source rows and all emitted calculations replay**, **303 internal links/assets/anchors pass**, and **22 real-browser tests pass**. Browser checks cover five current routes at 320/390/768/1440px, phone navigation, filters/sort, source links, expandable evidence, timezones, stale warnings and no-JS rows. Axe WCAG A/AA checks pass on every current route at both 390px and 1440px; this is automated coverage, not complete accessibility certification. Phone/desktop screenshots were inspected.
- Fixed actual browser findings: 390px header overflow, insufficient muted/badge/sidebar-count contrast, inline links distinguished only by color and undersized phone controls. The no-JS test verifies visible rows/teams/source links rather than relying on Chromium's `noscript` text extraction.
- Successful newer live-source run: [38515497596](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38515497596), exported in `65c5b0e`. No successful run or source observation is inferred from the earlier failed run `38515235502`.
- Hardened staged collection: a partially successful new API response cannot overwrite last-good source evidence if inventory reconciliation later fails. Partial-attempt evidence gets a distinct audited filename; validation must pass before any published data is replaced. Old unused event evidence is pruned only after a successful complete refresh.
- Consolidated production design: `pages.yml` is the single four-hour collector/build/deploy workflow with verified-snapshot cache, source/evidence replay, link checking and public post-deploy checks. The former six-hour writer is retired; it cannot overwrite current data or compete for deployment. Pages configuration is set to Actions by the production job. Source limitations remain visible and nonblocking; broken evidence/builds/deployments remain blocking.
- I-19/I-20 handoff: both historical sites are now included and clearly separated in the **locally verified artifact**. Their live-publication resolution remains **pending PR #3 merge and public deployment verification**. No merge or deployment success is claimed here yet.

### Final pre-merge source/provenance audit (2026-10-14 05:30 UTC)

- Staged collector run [38516592262](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38516592262) succeeded and exported `031ba7d`: **88 total = 28 future + 60 archived; 9 market + 5 bookmaker + 8 model estimates; 6 unresolved**. A newly available exact bookmaker pair was discovered automatically. The counts supersede the earlier 4-bookmaker/7-unresolved snapshot, rather than rewriting its historical log. One current estimate is a genuine tie, so it has no arbitrary directional pick.
- Canonicalized bookmaker citations to the **actual observed POST URL** (`https://thunderpick.io/api/matches`), removing an unrequested derived GET query. No odds, probabilities or observation times were changed. Each evidence panel now links the saved original response and request payload; event IDs and the GET-versus-POST caveat are explicit. Market panels link the original saved event and both books; model panels link raw and parsed Valve evidence.
- Replay now also checks derived availability, lobby/evidence links, the original inventory observation, exact bookmaker-request timestamp/URL/payload and unique bookmaker identity. All 88 rows replay; **367 internal links/assets/anchors** pass and all **40 Python / 22 browser tests** pass after the additional evidence links.
- Current root HTML/CSV fallback is generated from the replayed snapshot, with categorized directories and compatible old URLs. Original root-session copies remain intact; `docs/` source HTML and other sessions' assets/datasets/scripts are unchanged.
- GitHub's bot-authored data export triggered a workflow run requiring approval (`38516633712`). Attempted approval returned permission-scoped HTTP 403 (not a source/build failure). The independently triggered push/PR browser checks on this session's authored code succeeded; a final authored push will run checks against the final snapshot before merge. No untrusted code or approval gate was bypassed.

### Ready for merge — final authored head (2026-10-14 05:33 UTC)

- Latest strict collector/replay [38517005312](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38517005312) succeeded, exported `1bd7573`, observation `2026-10-14T05:30:39Z`. Coverage remains 88/28/60; 9 market + 5 bookmaker + 8 model estimates; 6 unresolved. The fifth exact bookmaker match is FORZE Reload–LFO 10, no unsupported alias mapping required.
- Both independent push and PR runner checks succeeded on `6556d88`: [push CI 38517005271](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38517005271), [PR CI 38517010034](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38517010034). Final authored head reruns the same full checks against the newest snapshot, rather than depending on the bot-authored approval-required event.
- All five primary routes are now available directly in the phone's fixed navigation (Summary, Picks, Sources, Methods, Review); phone one-tap picks and methodology navigation are tested. Final local result: 40 unit tests, 22 browser tests, all 88 row/calculation replays, **372 internal link/asset/anchor checks**, and local post-deploy protocol verification passed. Existing historical source files remain unchanged.


## PR #3 merged; publication repair (2026-10-14 05:41 UTC)

- **Merged:** PR [#3](https://github.com/buffedlizard55-lab/MaltaProj3/pull/3), `5689c6d` → main, merge `dc4d4818845598885a93a0dd5031465c7cc84d38`, **2026-10-14 05:35:34 UTC**. Both final-head CI runs succeeded: [PR 38517284110](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38517284110) and [push 38517278998](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38517278998).
- **Initial custom deploy:** [38517464314](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38517464314) passed regression tests, live full-source collection, every row/calculation replay, link checks and cache save, then failed at `Make Actions the only Pages publisher`. Later deployment steps were skipped. The exact failed HTTP response was not accessible through the sandbox's blocked log-download host; it is not invented here. GitHub's separate legacy [38517463146](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38517463146) succeeded and the Pages API still reported `build_type: legacy`.
- **Repair scope (same session/branch):** replace the optional setting-change blocker with `scripts/publication.py`, add explicit `actions: read`, wait for the same commit's platform legacy publisher to complete, then attempt Actions mode. A restricted change is recorded with actual response status/error and read-back mode in public evidence and review flags; the canonical artifact can still deploy last. A running/unverifiable competing publisher remains a blocker. No credentials are logged or persisted.
- **Additional regression coverage:** eight publication tests exercise existing Actions mode, pending legacy build completion, restricted settings with visible flag and redacted token, timeout preserving original data, unknown mode, failed metadata reads, delayed platform-run discovery, and setting-change network failure with verified readback. Total: **48 Python tests**; UI coverage remains **22 browser tests**.
- **Full outage integration simulation:** against a temporary copy of the real 88-row snapshot, forced a partial fixture overwrite followed by reconciliation failure. Original rows, source bytes, quote times, inventory observation and analysis replay clock were all retained; all rows/calculations and 372 links still passed; the generated site showed the explicit non-current warning.


## Completed production handoff — arena-4aae8328 (2026-10-14 05:49 UTC)

**Status: DONE.** Full inventory discovery, supported external probabilities, transparent model/unresolved handling, mobile dashboard, provenance, combined-site verification, PR merge and production deployment are complete. No user approval or manual source entry is needed for the scheduled refresh.

### Verified release records

| Record | Verified result |
| --- | --- |
| Main implementation | [PR #3](https://github.com/buffedlizard55-lab/MaltaProj3/pull/3), merged `2026-10-14T05:35:34Z`; merge `dc4d4818845598885a93a0dd5031465c7cc84d38` |
| Permission-safe publication repair | [PR #11](https://github.com/buffedlizard55-lab/MaltaProj3/pull/11), merged `2026-10-14T05:45:09Z`; merge `63f005bc6e1ea53496c6779ce9729997f2d5faf8` |
| Repair PR and push CI | [38518200163](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38518200163) and [38518197226](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38518197226), both **success**: 48 Python tests, 22 browser checks, strict row/calculation replay and internal-link checks |
| Canonical production deployment | [38518319041](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38518319041), **success**; job completed `2026-10-14T05:46:22Z` |
| Platform legacy publisher ordered before the canonical artifact | [38518319128](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38518319128), completed success by `2026-10-14T05:46:02Z`; the canonical deployment and public verification finished afterward |
| Public verification | All five current HTML routes and the full snapshot matched this deployment’s generated timestamp/counts; every future/unknown-schedule row was present; three old `.html` URLs worked; both archived dashboards returned the required explicit archive banner |
| Live URL | <https://buffedlizard55-lab.github.io/MaltaProj3/> |
| Full picks | <https://buffedlizard55-lab.github.io/MaltaProj3/picks/> |
| Source/evidence archive | <https://buffedlizard55-lab.github.io/MaltaProj3/coverage/> |
| Published limitations | <https://buffedlizard55-lab.github.io/MaltaProj3/review/> |

### Published snapshot and remaining nonblocking limitations

- Production source observation **`2026-10-14T05:45:26Z`**, confirmed by the job’s `Publication snapshot` annotation: **88 total = 28 future + 60 archived; 9 market + 5 bookmaker + 8 research-model estimates; 6 unresolved; 22 directional picks, no ties in that observation**. Earlier genuine-tie observations remain historical evidence; market movement is not rewritten as a constant. Later scheduled observations can differ.
- **Actual Pages setting restriction now confirmed:** HTTP **403**, `Resource not accessible by integration`, read-back `build_type: legacy`. This is a repository configuration permission limit, not a source-data or artifact-deployment failure. It is saved in public `data/evidence/pages-configuration.json`, displayed in source health and on Flagged for Review. The workflow waits for any same-commit legacy publisher before publishing the verified artifact last; its real successful deployment and post-deploy checks demonstrate this path works. No credential workaround or manual intervention was required.
- The former six-hour writer is retired. `pages.yml` is the only scheduled data collector/deployer: **00:17, 04:17, 08:17, 12:17, 16:17 and 20:17 UTC**. GitHub scheduling delays/outages are not hidden; inventory failures or snapshots older than eight hours produce explicit warnings and original observation times remain intact.
- Unavailable HLTV/other-source access, unknown best-of/current lineups, ambiguous provider names, uncalibrated Valve estimates, past-start status anomalies and the six unsupported current picks remain visibly flagged. They do not block publication or become invented values.
- **I-19 publication gap resolved:** both earlier dashboards are actually published, with archive banners confirmed over public HTTP. **I-20 primary-site ambiguity resolved:** the reconciled, replayed `data/latest.json` dashboard is the sole current feed; root/docs historical models are not mixed into it. Other sessions’ source HTML, original assets, datasets and scripts remain unchanged; their historical boards are retained in this file.
- All current routes have passing automated WCAG A/AA checks at phone and desktop widths, responsive width checks at 320/390/768/1440px, no-JS data visibility and one-tap phone picks/method navigation. This is not a claim of complete manual WCAG certification.

This documentation-only handoff records the already verified release. Its merge can trigger another ordinary refresh; it does not claim an unobserved future run succeeded.

## Session arena-11c1fa20 — renewed coverage and mobile audit (2026-10-15)

This session must use `arena/11c1fa20-maltaproj3`; no other branch is created or pushed. All prior source files and historical boards are preserved. Previous active integration claim 83207e7b is over 60 minutes old; its integration has since been published by arena-4aae8328. This session takes responsibility only for the canonical current dashboard below.

| Task | Status | Owner | File scope | Started UTC |
| --- | --- | --- | --- | --- |
| Audit current source coverage; expand safe fallback research; verify line-by-line | done | arena-11c1fa20 | `scripts/{collect,domain,sources,validate}.py`, `tests/test_domain.py`, canonical `data/latest.json`, `data/sources.json`, `data/evidence/` | 2026-10-15 |
| Audit and simplify current mobile summary/picks/unresolved navigation | done | arena-11c1fa20 | `scripts/build.py`, `assets/scout.{css,js}`, `tests/browser/dashboard.spec.mjs` | 2026-10-15 |
| Final integration, CI, PR merge and verified Pages publication | in progress | arena-11c1fa20 | `.github/workflows/{checks,collect-preview,source-diagnostics}.yml`, `README.md`, `COORDINATION.md`, new audit regression tests/scripts | 2026-10-15 |

Initial inspection: canonical collector already reconciles both official lobby hydration inventories with the fixture API, uses original Polymarket order books, then attempts HLTV, Thunderpick and Valve ratings. Four-hour Pages scheduler exists. Latest GitHub scheduled run `38682572464` reports success; source freshness and actual current coverage have not yet been independently inspected in this session. Outbound source hosts are restricted in this sandbox; live first-party inspection will run in GitHub Actions, retaining actual evidence and limitations instead of inventing values.

- arena-11c1fa20 scope addition: `scripts/audit_sources.py` and `data/research/` for a bounded, first-party HLTV / esportsbook / market-contract audit. Historical `docs/research/` and `scripts/discover_sources.py` remain unchanged. New diagnostic responses are research observations, not automatic probability inputs. Initial new inventory collection `38704769273` completed its collect/replay/export steps; snapshot inspection is in progress.


### arena-11c1fa20 verified integration — 2026-10-15 08:31 UTC

- Coordination claim was committed/pushed before implementation. The initial remote session branch did not yet exist, so the first `pull --rebase` used `origin/main`; subsequent pushes all followed `pull --rebase origin arena/11c1fa20-maltaproj3`. Runner data commits were rebased/preserved without conflicts. No other branch was created, switched to or pushed.
- **Confirmed source defect:** original HLTV parser required time/team descendants inside one anchor, but current official cards have sibling anchors inside `[data-match-wrapper]`. Original observed HTML `data/research/hltv-matches.html.gz` hashes to its recorded first-party response; the fixed parser found 53 timed records. Production now saves/replays full original markup and its response hash. Exact-match formats are research-only; unknown Hotspawn format fields remain blank.
- **Expanded primary discovery:** Polymarket’s public directory plus bounded official CS2-tag event pagination. A terminal page is required for API discovery completeness; repeat IDs, schema/network failures and the 2,000-event safety limit are visible limitations. Every selected event still passes the original series-moneyline/order-book policy. Official contract: <https://docs.polymarket.com/api-reference/events/list-events>; feed <https://gamma-api.polymarket.com/events?tag_slug=cs2&active=true&closed=false&limit=100&offset=0>.
- **Pricing correctness:** bookmaker odds align by the actual outcome name, not the `home`/`away` key. Live/past/missing-ID records are rejected. All displayed analysis fields now equal full replay, not just output probabilities; changed bid displays and misleading model labels fail validation.
- **Mobile delivery:** one-tap briefing shortcuts, explicit fair decimal lines next to both percentages, a separate unresolved section on picks, actual primary rejection reasons, and deep links that reveal the full evidence despite conflicting URL filters. Reset clears URL method state. Static/no-JS builds demote already expired or locked choices and warn that live clocks need JavaScript. No browser-facing localhost APIs.
- **Sources checked:** official Hotspawn lobby + CS2 lobby + fixture API; original Polymarket Gamma/CLOB data; <https://www.hltv.org/matches>; original read-only Thunderpick POST <https://thunderpick.io/api/matches> with `{"gameIds":[6]}`; <https://github.com/ValveSoftware/counter-strike_regional_standings> and its `model/fit.js`/`model/glicko.js`. Additional original pages: <https://stake.com/sports/esports/counter-strike>, <https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike>, <https://www.pinnacle.com/en/esports-hub/cs2>, <https://www.rivalry.com/esports/counter-strike-betting>. Actual status/errors and timestamps are saved, linked and published—not treated as lines.
- **Latest audited observation (not a promise of future counts):** `2026-10-15T08:27:11Z`: 80 complete inventory records = 18 future + 62 archived; 7 primary + 2 bookmaker + 5 model estimates; 14 picks and 4 unresolved. Four-hour production refresh remains unchanged. Original supported methods are never overwritten by fallbacks.
- **Needs review (published, nonblocking):** WROTBERRY–ENCE, WROTBERRY–BOJONG, HAVU–RoundsGG and RoundsGG–Voca lacked accepted source inputs at that observation. Primary wide/crossed order books and missing exact-name ratings are explicitly displayed. HLTV records named WBT/ROUNDS at matching times with one shared opponent are linked as observed identity discrepancies, NOT asserted equivalent teams/fixtures and NOT used as probability inputs. Stake/GG.BET access restrictions, Pinnacle/Rivalry generic redirects, unknown current rosters/vetoes/formats, past-source status anomalies and uncalibrated Valve estimates remain visible on review/source pages. No default 50/50 or invented picks.
- **Operational audit:** research export runs `38704904493` and `38704923472` failed in the export step with exit 1 (annotation verified; detailed log-download host is unavailable here). Output paths/wildcards were corrected; retry [38705136315](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38705136315) succeeded. Manual Actions dispatch returned HTTP 403 `Resource not accessible by integration`; ordinary authorized push triggers collected the same sources successfully, without bypassing permissions. Live collect/replay/export [38705701128](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38705701128) succeeded.
- **Combined verification:** 64 Python regression tests; 26 Playwright browser tests; all 80 row facts and every complete analysis replayed; 376 internal links/assets/anchors passed. Phone/desktop dimensions 320/390/768/1440px; automated WCAG A/AA checks on all five routes at phone/desktop widths. Not a claim of full manual WCAG certification. Independent runner [38705985591](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38705985591) succeeded on authored head `338fe75`. `git diff --check` passed.
- **PR opened:** [#15](https://github.com/buffedlizard55-lab/MaltaProj3/pull/15), integration head `arena/11c1fa20-maltaproj3` → `main`. Final CI and production deployment will be verified before marking publication done. Pages API currently confirms the existing `legacy` mode; production's previously verified publisher ordering remains in place.


## Concurrent completed-session handoff preserved at integration

## Session 87b206e2 — follow-up audit and integration (2026-10-15)

| Task | Status | Owner | File scope | Updated UTC |
| --- | --- | --- | --- | --- |
| Audit fallback evidence, clarify mobile executive summary and unresolved coverage; verify and publish | done | arena/87b206e2-maltaproj3 (final integration) | `scripts/build.py`, `scripts/sources.py`, `scripts/collect.py`, `tests/`, `assets/dashboard.css`, `.github/workflows/`, `README.md`, `COORDINATION.md` | 2026-10-15 |

All previous active historical claims are over 60 minutes old and their completed handoffs are recorded above. This session takes over only the follow-up scope listed here. Arena fixes this session to its existing branch. No source data is declared current until fetched successfully; outbound access here is restricted, so live collection will be verified on GitHub Actions where available.

- First live follow-up collection [38704742081](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38704742081) succeeded: observed 2026-10-15T08:18:50Z, 80 source rows, 18 future, 62 past-start, 7 Polymarket + 2 Thunderpick + 5 Valve-model estimates, 4 unresolved. This is a dated observation, not a permanent coverage claim. HLTV returned a real match directory but the old selector contract failed; investigating its recorded markup rather than labeling this as a confirmed access block. GG.BET returned 403; Pinnacle and Rivalry redirected. Missing Valve names and unacceptable Polymarket spreads remain unresolved, not guessed.
- The initial branch pull reported no remote ref (branch did not yet exist). Rebased against main before first push; no conflict or discarded work. Subsequent pulls use this session's published branch.

- Verified HLTV's observed public split-link markup from `https://www.hltv.org/matches`: `.match-info` carries time while `.match-teams` carries names, with identical match hrefs. Fixed grouping by exact href, deduplicated pinned cards, and reject conflicting repeats. Replayed the saved official fragments locally and added six synthetic parser regressions. No fan votes, inferred aliases or HLTV percentages become price inputs. The current reader saves the original HTML response for audit.
- Per-match fallback trails now include actual GG.BET/Pinnacle/Rivalry page-check outcomes only for matches still missing lines. Unknown-start fixtures are visible in summary/review unresolved sections and link to their inventory records. The landing heading explicitly says Executive summary; phone navigation and expandable unresolved trails are tested.

### Final verification before PR #13 merge

- Final integration also owns the automatic `data/` exports on this branch; they are generated solely by the claimed collection workflow, not manually altered prices. Prior source diagnostic samples were replaced by the original HLTV response and all parsed identities on successful refresh.
- Live collector [38705238962](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38705238962) succeeded. Observation `2026-10-15T08:22:59Z`: 80 inventory = 18 future + 62 past-start; 7 primary market + 2 bookmaker + 5 model + 4 unresolved. HLTV now successfully reads **53 deduplicated identities**, replayed against its saved original HTML. The four unresolved names/time pairs still do not uniquely match the HLTV observations; no aliases are inferred.
- Local checks: 59 Python tests (including original HLTV response replay), 23 browser checks at 320/390/768/1440px including expanded unresolved source trails, every match/estimate replay and internal link validation. Official-source URLs and remaining limitations are on Coverage/Flagged for Review. Tests are automated coverage, not a claim of exhaustive manual WCAG certification or verified true win probabilities.
- Implementation PR: [#13](https://github.com/buffedlizard55-lab/MaltaProj3/pull/13). Merge and production verification will be recorded after the actual operations succeed.


### Published follow-up — session 87b206e2 complete

- **PR #13 merged** at **2026-10-15T08:25:30Z**, merge commit `09b3e28cc00d46e596063576ea51ebee4b0c40ae`: <https://github.com/buffedlizard55-lab/MaltaProj3/pull/13>.
- Final PR verification [38705410628](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38705410628) passed; local verification also passed **59 Python tests, 23 browser tests, all 80 source-row/estimate replays and 339 internal links/assets/anchors**.
- **Production deployment and public post-deploy checks succeeded:** [38705560717](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38705560717). The actual published inventory observation was **2026-10-15T08:25:48Z**, with complete reconciliation: **80 inventory, 18 future, 62 past-start, 7 market + 2 bookmaker + 5 model estimates, 14 directional picks, 4 unresolved, no unknown schedules or ties**. Future refreshes may change these numbers.
- Live executive summary: <https://buffedlizard55-lab.github.io/MaltaProj3/>; picks: <https://buffedlizard55-lab.github.io/MaltaProj3/picks/>; unresolved/source limitations: <https://buffedlizard55-lab.github.io/MaltaProj3/review/>. Public verification checked all category pages and snapshot contents after deployment, not just the Actions deploy step.
- Remaining published issues: four unsupported future picks, missing exact-name ratings/market identity or unacceptable spreads, bookmaker 403/redirects, uncalibrated model assumptions, and past-start source status anomalies. No unsupported team aliases or probabilities were manufactured. HLTV parsing failure was repaired; a successful match-directory read is not itself a verified betting line.
- GitHub still rejects switching Pages mode with HTTP 403 (`Resource not accessible by integration`). Existing publisher ordering successfully waits for the legacy build and deploys the current artifact last; this restriction remains visible in Flagged for Review. The four-hour schedule remains active; scheduling delays are explicitly disclosed.

This final documentation records the observed successful release; it does not claim future refreshes are already verified.


### arena-11c1fa20 concurrent integration conflict log

Main advanced through PRs #13/#14 while this session worked from its initially inspected board. Both sessions independently repaired HLTV. At detection, work stopped for integration. All completed-session audit records and commits are preserved. This session now integrates the completed follow-up scope, including `tests/test_hltv.py`, `tests/test_summary.py`, per-match bookstore access observations and unknown-schedule UI behavior. Canonical data conflicts use the more recent coherent 08:27:11 snapshot (whole evidence set, not mixed prices from different observations); the older main data remains preserved in merged Git history. The overlapping parser implementations are combined: exact URL grouping, deduplication, conflict rejection, original markup/hash replay, and independently observed formats. CI validation remains enabled for all Arena branches; the session collector writes only to this session branch. A fresh live collect and full combined validation are required before merge.

- Combined conflict resolution preserved all tests and both audit boards. Local rerun after integration: **75 Python tests, 27 browser tests, every row/analysis replay, 376 internal links/assets/anchors** passed. The original concurrent HLTV response is additionally preserved verbatim in `data/research/hltv-index-response-session87.json`; no old response timestamps were rewritten. A new source refresh is triggered by this integration commit.

### Final combined source refresh — arena-11c1fa20

- Live integrated collector [38706805987](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38706805987) succeeded and exported `53977ee`. Actual observation **2026-10-15T08:36:04Z**: **80 records = 17 future + 63 past-start; 7 primary + 1 bookmaker + 5 model estimates = 13 picks; 4 unresolved**. The earlier Aurora match passed its scheduled start and is correctly archived, not silently missing. HLTV replay confirmed 52 timed records; primary API discovery reached a terminal page. This is the coherent final pre-merge snapshot, not a permanent coverage claim.
- Combined rerun against that newer snapshot: **75 Python tests**, all 80 match rows/complete analyses and **369 internal links/assets/anchors** passed. The combined browser suite already passed all **27 tests**, including the concurrent session's expanded unresolved-source trail regression; CI reruns the full suite on this final authored head.
- The required plain `pull --rebase` following the integration merge attempted to flatten imported main history and stopped on a board conflict. It was aborted (restoring the exact completed merge without losing edits), then `pull --rebase=merges` preserved both original histories and succeeded. No force push, skipped commit, discarded session work or branch switch was used. Subsequent pulls preserve merges.

- Final protocol audit found a latent mismatch: public verification expects all non-archived IDs on picks, but both original renderers excluded unknown schedules from that list. The full picks table now includes them (with blank times/probabilities and unresolved status), reconciling the deploy contract rather than dropping a row or failing publication for a nonblocking missing field. A dedicated synthetic presentation regression passes; source-dependent display/tamper tests explicitly skip if a future retained snapshot legitimately has no relevant supported estimate. Combined unit count is now **76**.

### Publication cache compatibility repair — arena-11c1fa20 (in progress)

- PR [#15](https://github.com/buffedlizard55-lab/MaltaProj3/pull/15) **merged 2026-10-15T08:39:31Z**, merge `910de423f3eab4f99d7f053a3941cdb26c0b6f7b`. Final independent PR CI [38707090302](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38707090302) passed on `ece3316`: 76 unit tests, 27 browser checks, all row/analysis/link validation.
- Production [38707237342](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/38707237342) failed at **Regression tests** after the legacy v1 cache restored; all collection/deployment steps were skipped. No successful current deployment is claimed. The detailed remote failure log is blocked by sandbox host restrictions; actual step failure is verified from job metadata.
- Claimed additional final-integration scope: `.github/workflows/pages.yml` (all earlier owners completed). Reproduced a **v1-cache overlay of the concurrent original snapshot onto the new checkout** locally, without altering canonical source data. Original-response replay fails because the v1 cache's parsed HLTV records use the older contract while the new checkout's additional evidence file remains present. This is incompatible cached evidence, not a fabricated market or inaccessible live source. Invalidate the old cache namespace for the new compatible original-markup/format contract; use the coherent checked-in last-good snapshot until a new v2 verified cache is produced. Keep original histories/evidence intact. Reverify, merge the repair and confirm actual public deployment.
