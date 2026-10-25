# Session arena-27ac20d6 — HLTV-first research for the fixtures without a featured line (2026-10-25)

**Question from the brief.** Generate a pick for *every* Hotspawn CS2 match — including low-tier
cards and matches betting sites do not cover — researching HLTV first, then esportsbook lines,
for anything the featured method cannot resolve; keep a separate unresolved-picks section with
limitations inside the executive summary; make the picks findable in one tap on a phone.

**Where the site already stands (verified, not assumed).** The published snapshot
(`2026-10-25T05:12:25Z`, 79-fixture inventory) has 18 active fixtures. The featured exact-name
method prices 16 of them (9 Polymarket, 2 Thunderpick, 5 Valve-model) and leaves **2 raw
unresolved**. The researched layer then resolves those 2 and upgrades 2 model rows to
money-backed consensus lines, so the executive summary at
<https://buffedlizard55-lab.github.io/MaltaProj3/> shows **18/18 with a directional pick, 0
unresolved** — with a separate *Unresolved picks & limitations* register on the same page
(`#unresolved-register`), a *picks without a betting line* register, and a fallback register.
This session independently researched the 2 raw-unresolved fixtures HLTV-first — from an
environment HLTV does not 403 — and machine-checked the summary contract. No probability, pick
or alias is written here; every row records what a named source published, with its link and
observation time. Full machine-readable dossier: [`research.json`](research.json); re-runnable
checks: [`scripts/27ac20d6_verify.py`](../../../scripts/27ac20d6_verify.py); flags:
[`flags.json`](flags.json).

---

## 1082792 — HOTU vs The Huns · Moscow Cyber Games 2026 · 31 Oct 2026, 09:00 UTC

Published: **HOTU 98.2%** (own network estimate over bo3.gg finished series) ·
[detail card](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#match-1082792).
Featured method left it unresolved: the Polymarket book is 43¢ wide (project ceiling 15¢) and the
Valve rung cannot choose between two same-name rosters.

| # | Source (link for manual review) | Observed (UTC) | What it actually published | Verdict |
| --- | --- | --- | --- | --- |
| 1 | [HLTV match page 2399437](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) | 14:17 | Bo3 (LAN) semi-final, 31 Oct. HOTU (HLTV #38 / VRS #38): dwushka, frontales, mizu, n0rb3r7, kade0. The Huns (HLTV #134 / **VRS #122**): Bart4k, controlez, bexyz, Cozen, DarkMeister. Betting panel: no numeric odds pair. Fan vote 76.0% / 24.0%. | Identity: The Huns' core = 4/5 of Valve's 944-pt row (#122; DarkMeister for Annihilation), 2/5 of the 701-pt row; HLTV's own VRS link resolves the team to #122. Fan vote is sentiment, never a probability. |
| 2 | [Valve VRS standings 2026-10-05](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) (committed at `data/evidence/valve-ratings.json`) | 14:25 | HOTU once (#31, 1437 pts). The Huns twice (#122, 944; #213, 701). Project formula (RD 75) replay: HOTU **94.1%** vs the #122 core, **98.4%** vs the #213 core. | Cross-check. Against the HLTV-verified core the project's own model reads ~4 points below the published 98.2%. Direction agrees. |
| 3 | [Polymarket event cs2-hotu-the9-2026-10-31](https://polymarket.com/event/cs2-hotu-the9-2026-10-31) | 14:40 | Market exists (BO3 semifinal, 31 Oct 5:00 AM ET = 09:00Z, resolves via hltv.org). Moneyline best asks **92¢ / 53¢**, $690 volume — the asks sum to 145%, so neither is a probability. Pipeline's 05:12Z book: 0.50/0.93 vs 0.07/0.50 (spread 0.43), rejected under the 0.15 ceiling. | No readable line; book shape says HOTU strong favourite. No midpoint quoted. |
| 4 | [EGamersWorld match page](https://egamersworld.com/counterstrike/match/EkalRNMvVx/hotu-vs-the-huns-esports-SfdtzDhiK) | 14:18 | Fixture + both lineups confirmed. Header odds **1.8 / 1.8** — the placeholder pair the pipeline's reviewed capture already rejects. | No usable line; independent read agrees with the rejection. |
| 5 | [bo3.gg](https://bo3.gg/matches) (the pick's own cited source site) | 14:47 | No fixture page at the canonical slug (`hotu-vs-the-huns-31-10-2026` → 404). The card's rating links [teams/2720](https://bo3.gg/teams/2720) and [teams/9127](https://bo3.gg/teams/9127) also return 404. | Model inputs are captured inside the repo, but a reader cannot verify at the source → **flagged**. |

**Fixture verdict.** The pick direction (HOTU) is corroborated by every source. The 98.2%
magnitude is single-sourced from the uncalibrated network fit; the project's Valve model on the
HLTV-verified roster says 94.1%, and no usable money line exists today. **Flagged for review**
(`27ac20d6-1082792-magnitude`); the number is left untouched — the 4-hour ladder re-prices this
fixture on every refresh, so if Polymarket's book tightens before 31 Oct a market line replaces
the model figure automatically. The identity blocker is now evidence-backed resolvable by a
majority-core rule (4/5 + HLTV's own VRS #122 link) — logged as a ladder change request
(`27ac20d6-huns-identity-resolvable`), not applied from this session.

**Limitations.** Not an exact-five HLTV proof (one player differs from the #122 row), so the
strict ladder refusal remains correct today. Cross-check points are the 2026-10-05 file; HLTV's
live VRS mirror already ranks HOTU #38 — points have drifted. Hotspawn's best-of was unverified
and stays blank in the snapshot; HLTV lists Bo3.

## 1081156 — Spirit Academy vs LFO 10 · CCT Europe 2026 Series #12 · 25 Oct 2026, 12:00 UTC (locked 11:54)

Published: **Spirit Academy 69.9%**, median of Polymarket + Kalshi + Smarkets + Bovada via the
verified alias Sokerorg → LFO 10 ·
[detail card](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#match-1081156).
Featured method: no exact-name Polymarket fixture; "LFO 10: no exact-name Valve rating found".
The match had already started when this session began — provenance only, no re-pricing.

| # | Source | Observed (UTC) | What it published | Verdict |
| --- | --- | --- | --- | --- |
| 1 | [HLTV team profile 14084 (LFO 10)](https://www.hltv.org/team/14084/lfo-10) | 14:42 | Swedish team; starters dottie / flaw / Sapec, each "10 days" on the team (core formed ≈15 Oct); HLTV #167; VRS mirror **#156** (25 Oct). | Identity confirmed; the Valve blocker was a standings-vintage artifact — the team postdates the 2026-10-05 file. |
| 2 | [HLTV event 9457 (CCT S12)](https://www.hltv.org/events/9457/cct-2026-europe-series-12) | 14:35 | Both teams listed; 25/10 bo3 pairing present; LFO 10 already played BAKS (2–1) and FORZE Reload (0–2) in the event. | Fixture corroborated on HLTV. |
| 3 | [Valve standings 2026-10-05](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) (committed evidence) | 14:25 | 380 rows: Spirit Academy #115 (981 pts) — roster matches HLTV's five starters; LFO 7/8/9 present, **LFO 10 absent**. | The snapshot's blocker reproduces exactly; the refusal to guess a numbered stack was correct. |
| 4 | Alias corroboration across the card's own books: [Polymarket cs2-tsa-skr2](https://polymarket.com/event/cs2-tsa-skr2-2026-10-25), [Smarkets spirit-academy-vs-sokerorg](https://smarkets.com/sport/esports/cs-go/cct-europe/group-stage/2026/10/25/12-00/spirit-academy-vs-sokerorg), [bo3.gg spirit-academy-vs-sokerorg](https://bo3.gg/matches/spirit-academy-vs-sokerorg-25-10-2026) | 14:32 | Five first-party URLs name the team "Sokerorg/SKR" for this exact fixture ("söker org" = Swedish for *looking for org* = LFO; HLTV's LFO 10 is a Swedish stack). | The registry alias the consensus rests on is independently plausible; the registry evidence remains the authority. |

**Fixture verdict.** Identity and blocker fully explained; the published resolution (verified
alias into four independent money sources) behaved as documented. Info flag
(`27ac20d6-lfo10-vrs-now-exists`): with a post-15-Oct standings file the name resolves exactly,
retiring this blocker for future LFO 10 fixtures.

## Model-row replay (no new numbers — provenance only)

| Fixture | Published | Replay from committed official standings | Result |
| --- | --- | --- | --- |
| 1082793 5star vs 1WIN | 1WIN 82.2% | 1110 vs 1383 pts, project formula | reproduces 82.2% |
| 1082861 Rooster vs Abyssal | Abyssal 52.2% | 718 vs 734 pts | reproduces 52.2% |
| 1082996 Acend vs UNiTY | UNiTY 61.4% (consensus) | raw snapshot shows the featured Valve pick (Acend); the card documents the upgrade to a verified money line verbatim | explained on its own card — layers differ by design |

Provenance note: the two Thunderpick rows (1082859, 1082860) link to the generic
`thunderpick.io/api/matches` endpoint and the committed Thunderpick evidence capture predates
both fixtures; the durable record of the lines (1.60/2.20; 1.001/12.00) is each card's quote
block (`27ac20d6-thunderpick-generic-link`, info).

## Executive-summary contract (the "site is confusing" ask)

Machine-checked against the committed root build (`index.html`, the bytes the legacy Pages
builder serves) by `scripts/27ac20d6_verify.py` — 9 pass / 0 fail / 1 info
([`verification.json`](verification.json)):

| Requirement from the brief | Where it lives | Check |
| --- | --- | --- |
| Visit the site → find the updated picks immediately, on a phone | `#picks-at-a-glance`: all 18 active fixtures, pick bolded, both teams' % | glance ⇔ snapshot open-set parity; every row marked + sourced + anchored |
| Executive summary with in-site links to the picks | banner links: picks ↓, unresolved ↓, coverage/refresh →, methodology → | link presence check |
| Separate section for unresolved picks + limitations, inside the summary | `#unresolved-register` (+ no-line and fallback registers) names both raw-unresolved fixtures with their limitations | register names + limitations-language check |
| Probability for each team, pick obvious | every row shows both percentages or an explicit unresolved/even label | row-shape check |

One honest caveat the summary itself prints: at read time the snapshot was ~9.7 h old — past the
published 8-hour bound — so the page leads with "Do not treat these as current picks." That is
the frozen four-hour publisher, owned by PR #328 / PR #332 (opened 13:42Z / 14:01Z today); this
session does not duplicate their fix and re-checks freshness after one merges (task 27AC-3).

## Irregularities flagged for review (do not block)

1. **`27ac20d6-1082792-magnitude` (warning)** — 98.2% is single-sourced; Valve cross-check 94.1%.
2. **`27ac20d6-bo3-team-links-404` (warning)** — the card's bo3.gg rating links are dead (404).
3. **`27ac20d6-huns-identity-resolvable` (info)** — majority-core disambiguation evidence for a future ladder rung.
4. **`27ac20d6-lfo10-vrs-now-exists` (info)** — LFO 10 blocker was standings vintage; self-heals on a newer file.
5. **`27ac20d6-thunderpick-generic-link` (info)** — generic API source link limits after-the-fact verification.

Change requests for owners of shared files (logged in `COORDINATION.md`, not edited here):
fix the bo3.gg team-link route in `scripts/originate.py`; consider a majority-core lineup
disambiguation rung in the collector ladder using a sourced event lineup.
