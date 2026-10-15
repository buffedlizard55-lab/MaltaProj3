# arena-de176356 — coverage, cadence and repo-review audit

Observation clock: **2026-10-15 ~10:10 UTC**. Branch: `arena/de176356-maltaproj3`. Read-only evidence; no site template, workflow, pricing input or shared dataset was edited.

## What this session covers and does not cover

| Request | Status in this session |
| --- | --- |
| Repo review, line by line, irregularities flagged | **DE-1 done** — `repo-review-register.json`, 15 items, each with a measured value and a source link. |
| Full Hotspawn CS2 coverage of listed matches | **DE-2 done** — all 17 upcoming lobby entries match the stored inventory by ID, competition and start minute. |
| Refresh every 4–8 hours | **DE-3 done** — measured; **not met reliably** (see below). Fix requested from the workflow owner. |
| Day-one (9z vs Aurora) review, Aurora roster change, contrarian guidance | **Not started here.** Claimed by `arena-50c01ba9` (10:04 UTC) and, overlapping, by `arena-3c292a02` (commit `c7c673e`). Logged as R-DE-1 and R-DE-4. |
| Executive summary links, unresolved section, mobile navigation | Built earlier and live. Picks-first navigation is claimed by `arena-50c01ba9`. Not changed here. |

## DE-2: Hotspawn coverage reconciliation

- Live lobby (`https://play.hotspawn.com/cs2-pickems`) lists **17 upcoming** CS2 matches, from Oct 15 10:00 UTC to Oct 16 18:00 UTC. Each has a View Match link ID.
- All 17 match the stored fixture evidence on ID, competition and start minute (`coverage-reconciliation.json`).
- Stored inventory: 80 records. Lobby tournament filters total 78. The difference is exactly two matches that had already started by the lobby read: **1080279** (WROTBERRY vs EAC, 08:00Z) and **1080201** (Aurora vs Ninjas in Pyjamas, 08:30Z). Only the Elisa BreakOut (12 vs 11) and Thunderpick WC 2026 (4 vs 3) counts differ.
- Hotspawn's own header says **"72 matches this week"** while its tier and tournament filters total **78**. Flagged as RR-04; the site does not use the header.
- **Day-one gap:** the fixture feed returns only currently scheduled fixtures. `status=finished` returns `[]`. So finished matches such as **9z vs Aurora (14 Oct 2026)** cannot appear in the Hotspawn inventory. Results must come from a results source (HLTV).

## DE-3: refresh cadence

- Cron in `pages.yml`: `17 */4 * * *` (six slots a day: 00:17, 04:17, 08:17, 12:17, 16:17, 20:17 UTC).
- Scheduled runs in the GitHub history: **13:43, 20:12, 23:14 (14 Oct)** and **04:39 (15 Oct)** UTC. First scheduled run 14 Oct 13:43 UTC.
- Slots with a scheduled run within ±2 h: **4 of 6**. Missing: **16:17 (14 Oct)** and **08:17 (15 Oct)**.
- Largest completed gap: **6.48 h**. At audit time, **5.51 h** since the last scheduled run. The 8-hour staleness limit would be reached about 12:39 UTC if no run starts.
- GitHub documents that scheduled runs "can be delayed during periods of high loads" and "some queued jobs may be dropped". This repository is public, so scheduled workflows are disabled after 60 days without repository activity.
- Requested: the `pages.yml` owner adds redundancy (R-DE-3). I did not change the workflow, because it is a shared output.

## Lock-time discrepancy (user-facing)

Hotspawn's official help page says picks lock **5 minutes** before start. All **80 of 80** saved fixture records lock **6 minutes** (360 s) before start. Submit at least 6 minutes before the scheduled start. See RR-03.

## Limitations of this audit

- Hotspawn pages were read through the read-only fetch tool. Lobby entries were transcribed from those fetches, each with its link ID. Nothing was inferred.
- The sandbox cannot reach Polymarket, HLTV or Hotspawn directly, so no price was re-collected. Probabilities in the live data are not re-verified here.
- The Playwright suite was listed, not run. The Python suite was run: 100 tests, OK.
- No Thunderpick developer documentation was found. The Thunderpick endpoint is treated as unofficial (RR-11).
- The Aurora roster-change claim was **not** researched here. It belongs to the day-one claims above.

## Requests logged on COORDINATION.md

- R-DE-1 → `arena-50c01ba9` and `arena-3c292a02`: day-one facts to use (HLTV, 9z 2-0 Aurora, 14/10/2026) and the day-one-only limitation (RR-06).
- R-DE-2 → integration owner: publish the register and this report on the Flagged for Review page.
- R-DE-3 → `pages.yml` owner: add redundancy to the schedule (RR-08).
- R-DE-4 → `arena-50c01ba9` / `arena-3c292a02`: the two claims overlap on `scripts/build.py` and the day-one review. Decide one owner.
