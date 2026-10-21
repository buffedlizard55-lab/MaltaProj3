# Session arena-6e92015a — research dossier (2026-10-21)

Scope claimed on the board: integrate the two stalled PRs (#120 network rung, #121
phone summary), then work the fixtures the deployed complete-picks ladder left
unresolved at 20:20Z — **1081597 benched gods vs TitanFlow** and **1082860
FlyQuest vs Staqued** — through the HLTV-first, then-books research ladder, with
a runner-side probe recording the primary evidence. PR #132 (session 093e722e)
owns the other fixtures; nothing here duplicates it.

## Outcome in one paragraph

One of the two blanks is now closed and the other is closed *around*: the merged
network rung resolved **1081597** (TitanFlow 78.3% / benched gods 21.7%, published
with a low-confidence badge and a wide interval — flagged
[below](#1081597--benched-gods-vs-titanflow-resolved-by-the-network-rung)), and
**1082860** stays blank with every rung's blocker named and evidenced
([below](#1082860--flyquest-vs-staqued-stays-blank-full-trail)). A fresh ladder
replay on the merged tree at 2026-10-21T20:49:16Z reads: **13 active, 12 resolved,
1 unresolved** (2 market, 9 model of which 2 network, 1 consensus, 2 alias-joined).
The one blank is published in its own unresolved section with its limitations, per
the standing brief.

## 1081597 — benched gods vs TitanFlow: resolved by the network rung

- **Fixture:** CCT Europe 2026 Challengers #8, starts 2026-10-22T11:00:00Z
  ([Hotspawn](https://www.hotspawn.com/matches/benched-gods-vs-titanflow-cct-europe-2026-challengers-8-1081597)).
- **Why it was blank:** neither side has a Valve rating row (benched gods maps to
  multiple candidate rosters) nor an HLTV world-ranking row; no exchange or book
  priced it at probe time.
- **What resolved it:** the Bradley–Terry network model over bo3.gg finished
  series (network-bt-1, merged from PR #120 / session 541cd43a). Inputs:
  [benched gods](https://bo3.gg/teams/22240) 775.7 pts (SE 62.4, 60 series) vs
  [TitanFlow](https://bo3.gg/teams/25277) 999.1 pts (SE 155.5, 9 series), both
  unanchored; identity bridge start-time + team name; graph 4,650 matches, 269
  anchors; evidence `live-bo3-graph.json` hash-checked by the pipeline.
- **Published estimate:** TitanFlow **78.3%** / benched gods **21.7%**, pick
  TitanFlow, low-confidence, 95% interval [3.9%, 65.5%] on the underdog side.
- **Why it is flagged:** both sides unanchored and TitanFlow's thin history (9
  series, SE 155.5) make the *magnitude* soft even where the direction is firm.
  A first-party price before the 10:54Z lock supersedes the model. Pinnacle's
  board carried a "CCT Europe Challengers" league at 14:00Z that was gone by
  20:37Z — league rotation makes this a per-run re-check.

## 1082860 — FlyQuest vs Staqued: stays blank (full trail)

- **Fixture:** DFRAG Invitational 2026 Group B opener, starts 2026-10-27T03:00:00Z,
  Best of 3, LAN at The DFRAG Studio, Brisbane
  ([Hotspawn lobby](https://play.hotspawn.com/cs2-pickems#fixture-1082860)).
- **Identity — confirmed, not the blocker.** HLTV match
  [2399890](https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026)
  (captured on the runner: 326,841 bytes, `evidence/hltv-match-1082860.gz`) names
  both teams, the event ([9414](https://www.hltv.org/events/9414/dfrag-invitational-2026))
  and "Best of 3". Teams: [FlyQuest 12774](https://www.hltv.org/team/12774/flyquest),
  [Staqued 13997](https://www.hltv.org/team/13997/staqued). The event's official
  ruleset (LAN Oct 26–Nov 1, FACEIT platform, Valve-license compliant) is published
  by the organiser at
  [dfrag-tv/vrs-event-announcements](https://github.com/dfrag-tv/vrs-event-announcements/blob/main/dmg-cs2-ruleset-invitational-lan-2026.md).
- **Money rungs — all empty at 2026-10-21T20:49:58Z.** Polymarket gamma: 407 active
  CS2 events, zero mentioning the fixture. Kalshi: 41 events, no match-winner
  market. Thunderpick: 3 status rows, no line. Bovada: 42,739-byte coupon, no line.
  Pinnacle: 175 CS2 matchup rows, no fixture hit.
- **Aggregated reference — rejected by policy.** EGamersWorld lists the fixture
  ([match page](https://egamersworld.com/counterstrike/match/4kaAQWgKEx/flyquest-vs-staqued-zawJ-Q52S3),
  URL recorded in the reviewed-capture registry `egw-urls.json`), but the rendered
  page shows identical 1.8/1.8 prices, which `scripts/reference_odds.py` rejects
  as placeholders; the runner-side fetch of that page returned a Cloudflare
  interstitial (honest capture: `evidence/egw-match-1082860.gz`).
- **Model rungs — blocked by Staqued's record.** Valve: no rating row. HLTV
  ranking: no world-ranking entry (page exists, ranking row does not). bo3.gg
  results model: 1 anchored series in 120 days (needs 8). Network model: 2
  finished series in the window (needs 6). FlyQuest is fully rated; every model
  rung requires both sides, so no default 50/50 is published.
- **Limitation, stated on the site:** this is a LAN group opener six days out;
  books typically post closer to the start. Re-checked every 4-hourly run.

## Probe design and its own two fixes

`.github/workflows/6e92015a-probe.yml` + `scripts/s6e92015a_probe.py` run on
GitHub's runner (the only environment with provider egress), triggered by pushes
to the session branch, guarded to skip its own `research(6e92015a)` report
commits. Everything is read-only GET/POST; every response is saved, hashed and
listed in `request-manifest.json`; no probability, pick or alias is written by the
probe. Fixes made after the first run:

1. **Blanks union (run 1 under-reported).** The workflow restores tracked data
   before the probe reads it, so run 1 saw the stale tracked snapshot with zero
   blanks and probed nothing. The probe now unions the *deployed* release
   (`evidence/live-origination-json.gz`, downloaded from the live site) with the
   *fresh* ladder copy (`fresh-origination.json`, generated after the restore),
   and records both sides in `probe.json → blank_sources`.
2. **EGW fixture URLs (run 1 could not capture fixture pages).** EGW's match list
   is a JS shell with no links; the probe now reads reviewed URLs from
   `egw-urls.json` and marks their provenance (`reviewed capture` vs
   `matches list`).

`probe.json` also records, per blank fixture, a `resolution_options` list: for
each ladder rung, whether it could price the fixture and exactly what evidence
would be required — the checklist any future session can pick up.

## Verification on the merged tree

- Python suite: **795 tests OK** (one #121 regression test adapted to main's
  label text, rationale documented in the test).
- Playwright: **85 checks OK** at 320/390/768/1440px, after repairing two real
  defects the browser suite caught in the #120 phone strip: dimmed-label contrast
  3.43:1 → 5.4:1 (WCAG A/AA), and picks-at-a-glance fold position 1,559px →
  1,469px at 320px (contract: < 1,500px).
- `scripts.build`: 542 rows, 695 internal links/assets/anchors OK.
- `scripts.audit_rows --strict`: 0 violations (528 official, 5 flagged, 9
  site-map, 0 without a source).

## Flags raised

All five are in [`flags.json`](flags.json) and render on
[Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/):
the 1082860 blank (warning), the 1081597 low-confidence network pick (warning),
EGW capture limits (notice), the live site serving the 2026-10-15 fallback at
probe time (notice — upstream collection failure, not silent), and the PR
takeover/integration record (notice).
