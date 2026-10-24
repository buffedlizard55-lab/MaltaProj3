# Fallback-pick research — session arena-3877d48d (read 2026-10-24T16:19Z–16:30Z)

**Question.** Every active Hotspawn CS2 fixture already has a pick, but 15 of the 23 do **not** come
from the featured Polymarket order book: 5 consensus lines, 5 single-bookmaker lines, 1 aggregated
reference and 4 research models. The brief asks for an independently researched way to price those
fixtures — HLTV first, then esportsbooks and betting lines — and for the limits of each method to be
published. This file records what those outside sources actually showed. It does **not** write a
probability, a pick or an alias; the publisher's ladder is still the only path to a published number.

Snapshot reconciled against: `snapshot.json` generated **2026-10-24T14:24:32Z** (inventory observed
14:24:12Z) — 84 records, 23 open, 23 with a directional pick, 0 unresolved, 19 priced by an outside
money source and 4 by a research model.

## Hotspawn inventory (official)

| Check | Result | Source |
| --- | --- | --- |
| Lobby CS2 filter, read 16:19Z | 84 matches this week (B 35 · C 49) — same total as the snapshot inventory | <https://play.hotspawn.com/lobby> |
| Open fixtures still pickable | 22 of 23; `1083121` (Projeto do KinGui vs MEIA NOITE, 16:00Z) had passed its lock | <https://play.hotspawn.com/lobby> |
| Every remaining open fixture | has a pick on the published site (`/origination/#picks`) | <https://buffedlizard55-lab.github.io/MaltaProj3/origination/> |

## Outside research, per fallback fixture

| Fixture (Hotspawn id) | Published method | Outside read | Verdict |
| --- | --- | --- | --- |
| Ground Zero vs Off Chops (`1082858`) | aggregated reference | [EGamersWorld](https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d) displays **3.44 / 1.24** and names Off Chops the bookmaker favourite at 1.24 | Confirms the published 73.5% reference pick |
| FlyQuest vs Staqued (`1082860`) | single bookmaker (Thunderpick) | same page family displays **1.001 / 12.00**; tips text quotes the average as **1.008 / 11.832** | Near-lock quote, returns < 2%; 92.3% is arithmetically right but not actionable. The old row printed “1.00” — a presentation bug now fixed |
| Acend vs UNiTY (`1082996`) | research model | EGamersWorld displays **1.80 / 1.80**, identical to three other unpriced fixtures | Refused as an identical-decimal placeholder |
| Rooster vs Abyssal (`1082861`) | research model | EGamersWorld displays **1.80 / 1.80** | Same placeholder; refused |
| HOTU vs The Huns (`1082792`) | research model | EGamersWorld displays **1.80 / 1.80**; Polymarket event 1241313 already refused for a 0.43 spread | Same placeholder; refused |
| 5star vs 1WIN (`1082793`) | research model | EGamersWorld displays **1.80 / 1.80** | Same placeholder; refused |
| Acend vs UNiTY (`1082996`) | research model | [Polymarket event 1238703](https://polymarket.com/event/cs2-ace1-unity-2026-10-25) is **active**, `eventStartTime` **2026-10-25T09:00:00Z** = the Hotspawn start; map-1 book 0.03 / 0.97 | Bindable fixture the publisher reported as unmatched — retry the series book on the next collect |
| HOTU vs The Huns (`1082792`) | research model | [HLTV 2399437](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) displays **77.1% HOTU / 22.9% The Huns** | HLTV's own estimate, not a line. Our 94.1% is materially more confident → publish the gap |
| 5star vs 1WIN (`1082793`) | research model | [HLTV 2399438](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026) displays **81.6% 1win / 18.4% 5star** | Cross-check agrees with the published 82.2% |
| Spirit Academy vs LFO 10 (`1081156`) | single bookmaker (Bovada) | [HLTV event 9457](https://www.hltv.org/events/9457/cct-2026-europe-series-12) lists Spirit Academy vs **LFO 10** (Sweden) on 25 Oct; the Bovada page names the opponent **Sokerorg** at 08:00 ET (12:00Z) | Provider name differs; scoped alias join, flagged |
| FORZE Reload vs ex-RUSTEC (`1081158`) | single bookmaker (Bovada) | Bovada URL path says **series-11** while Hotspawn lists CCT Europe Series #12 | Label mismatch flagged, not rewritten |

## Limitations recorded

1. **EGamersWorld blocks the runner.** The read-only probe in `probe.json` recorded **HTTP 403** on all
   ten match pages from `ubuntu-24.04` at 16:26Z, while the browser-class read in this session returned
   prices. The 14:24Z build still resolved one reference row, so the block is new or intermittent. It is
   a source limitation, never evidence that no market exists.
2. **Identical-decimal placeholders are not markets.** Four unrelated fixtures displaying `1.80 / 1.80`
   are refused under the existing placeholder rule. No line was manufactured from them.
3. **A near-lock is a price, not a probability estimate.** FlyQuest `1.001` implies ~92.3% after margin
   removal; the row is labelled with that limit.
4. **HLTV percentages are HLTV's model**, not betting odds. They are published as cross-checks only and
   are never an input to a pick.
5. **Model-only picks stay model-only** until a compliant money rung resolves them. Nothing here was
   hand-written into a probability.

## Artifacts

- `data/research/3877d48d/findings.json` — the same rows, rendered on `/unresolved/#independent-verification`.
- `data/research/3877d48d/probe.json` — read-only runner sweep (HTTP status, byte count, SHA-256, literal
  `<time datetime>`/`startDate` values and decimal tokens per page).
- `scripts/3877d48d_probe.py`, `.github/workflows/3877d48d-probe.yml` — the probe. It writes evidence
  only; it cannot write a pick.
