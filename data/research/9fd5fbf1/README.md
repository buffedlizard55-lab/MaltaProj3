# Session arena-9fd5fbf1 — 23 October 2026 live coverage research

Dated, source-linked observations only. **No probability in this folder is a pick.**

| File | What it is |
| --- | --- |
| [live-coverage.json](live-coverage.json) | Live Hotspawn lobby / API vs the public 2026-10-22T14:05Z snapshot, plus HLTV-first then book lookups for fixtures the snapshot does not contain |
| [flags.json](flags.json) | Review-page findings (auto-loaded) |

## Method

1. Read the public snapshot (`generated_at 2026-10-22T14:05:35Z`) and the live [Hotspawn lobby](https://play.hotspawn.com/lobby) / scheduled-fixture API.
2. For every Closing Soon / Upcoming CS2 card, record Hotspawn id + permalink when the lobby published one.
3. Try [HLTV matches](https://www.hltv.org/matches) first for identity (and analytics pages where they exist). HLTV ranking/form is **not** converted into a win probability here.
4. Then look for a two-sided prematch price on Polymarket Gamma (exact slug lookups) and bo3.gg match pages. A missing or affiliate-only block is recorded as a limitation, never as “no market exists”.
5. Hotspawn crowd participation and HLTV fan votes are excluded.

## Result (2026-10-23T04:58Z)

- Public complete-picks list: **37 active, 37 directional picks, 0 unresolved** — but that list is the 14:05Z snapshot, not today’s lobby.
- Live lobby cards **not in that snapshot** (official Hotspawn permalinks): 1081605, 1083014, 1082693, 1079193, 1079195, 1082996, 1079198, 1079199, 1079200.
- JiJieHao vs Eternal Fire is on the lobby without a permalink; HLTV 2399638 confirms the pairing; Hotspawn id left blank.
- No new two-sided money line was verified for those gaps in this window. The executive summary now lists them under **Live Hotspawn fixtures missing from this snapshot** with source links, not invented percentages.

Publisher repair (date-bound relay / root-publish tests) is owned by concurrent session `arena-19de9c79` and is not edited here.
