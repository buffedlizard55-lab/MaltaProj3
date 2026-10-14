# Shared coordination board

Session: `arena-4aae8328` · Branch: `arena/4aae8328-maltaproj3`

This session is fixed to the Arena branch above. No alternative session branches are created. The repository contained only `README.md` at initial inspection; no other task claims existed.

## Tasks

| Task | Status | Owner | File scope | Last update (UTC) |
| --- | --- | --- | --- | --- |
| Discover and verify Hotspawn CS2 match sources and external probabilities | in progress | arena-4aae8328 | `scripts/`, `tests/`, `data/`, `docs/` | 2026-10-14 |
| Mobile-first dashboard, picks, coverage, methodology, review pages | in progress | arena-4aae8328 | `index.html`, `picks/`, `coverage/`, `methodology/`, `review/`, `assets/` | 2026-10-14 |
| Automation, integration, validation and GitHub Pages publication | in progress | arena-4aae8328 (final integration) | `.github/`, `README.md`, `.gitignore`, dependency/configuration files, `COORDINATION.md` | 2026-10-14 |

All scopes are claimed by this session and are non-overlapping. Other sessions must log requests here rather than editing claimed files. Unverified source data and unresolved matches are publication warnings, not hidden omissions or invented probabilities. Broken builds are blockers.

## Activity and handoffs

- 2026-10-14: Inspected repository and remote; only the 12-byte README existed. Claimed the tasks above before implementation. No existing source data, application, automation or featured-pick method was present to preserve.

## Verification and sources

Pending source discovery. Target match authority: <https://play.hotspawn.com/lobby>. External prices and HLTV research must carry original source URLs, timestamps and evidence. Hotspawn participation/popularity is never a probability input.

## Publication

Pull request, merge, build/deploy results and live URL will be recorded here after verification.


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
