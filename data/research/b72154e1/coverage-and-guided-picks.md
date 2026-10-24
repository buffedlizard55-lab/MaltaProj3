# Picks for every match — live coverage re-verification (arena-b72154e1, 2026-10-24)

**What you asked:** every Hotspawn CS2 match must have a pick, including low-tier
matches Polymarket and the big books skip. For anything the normal ladder cannot
price, research HLTV first, then esportsbooks, and publish the unresolved set
with its limitations in the executive summary. Machine-readable record:
[`coverage-and-guided-picks.json`](coverage-and-guided-picks.json).

## Where to find the picks on the site (phone-first)

1. Open the site → **Executive summary** at the top of the home page.
2. **"Picks at a glance"** is the first jump on a phone: every active match,
   the pick bolded, win % for both teams.
3. **"Complete picks list"** (`/origination/#picks`) has all rows with sources.
4. **"Unresolved / no betting line"** (`/unresolved/`) is the separate section
   for fixtures no compliant line prices yet, each with its research trail and
   limitations. Guided picks from this dossier appear on **Flagged for
   Review** (`/review/`) so the phone view never shows a blank row without an
   explanation one tap away.

## Coverage at 2026-10-24T06:30Z (verified line by line)

- Published snapshot `2026-10-23T20:10Z`: **19 active · 17 picks · 2 unresolved**.
- Live Hotspawn lobby read first-hand today: **25 open CS2 cards**. Nine were
  added after the snapshot, so they have no published pick until the next
  automated collect. The post-merge publisher run
  [40069088115](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40069088115)
  has been **queued, job not started, since 06:09Z** — that queue, not missing
  analysis, is what currently delays full coverage. The 4-hour schedule +
  catch-up slots in `pages.yml` remain the automatic mechanism; no manual
  input is needed from you.

## Group A — no pick in the snapshot (HLTV first, then esportsbooks)

### 1082858 Ground Zero vs Off Chops — guided pick: **Off Chops 73.5%**
- HLTV [2399888](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026):
  BO3 confirmed, **no bookmaker odds** (promo only). Fan vote excluded.
- [EGamersWorld](https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d),
  re-read first-hand today: **3.44 / 1.24** → no-vig **26.5 / 73.5**.
  Re-confirms arena-43110640. *Limitations:* single aggregated reference;
  Hotspawn crowd (93% Ground Zero) is not a probability and is ignored.

### 1082792 HOTU vs The Huns — guided pick: **HOTU** (model 94.1%, direction only)
- HLTV [2399437](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026):
  BO3 semi, HOTU #38 vs The Huns #134, **no odds**.
- EGW still **1.8/1.8 placeholder** (rejected); Polymarket $0 volume.
- *Limitation:* no betting line exists anywhere reachable; the Valve-points
  model number is uncalibrated — trust "HOTU", not "94.1%".

## Group B — research-model picks re-checked against HLTV/EGW

| Fixture | Published pick | HLTV-first check | Esportsbook check |
| --- | --- | --- | --- |
| Acend–UNiTY (1082996) | Acend 54.2% | HLTV ranks lean UNiTY; VRS near-even → low confidence | EGW 1.8 placeholder |
| Metizport–BakS (1079198) | Metizport 79.9% | Valve pts 1238 vs 1021 agree | EGW 1.8 placeholder |
| Color–ex-ZT (1079200) | Color 73.6% | VRS #73 vs #92 agree (read first-hand) | EGW placeholder; cached pair ambiguous, unused |
| Rooster–Abyssal (1082861) | Abyssal 52.2% | No priced HLTV block | Cached EGW 2.1/1.66 (Oct 19) agrees; guidance only |
| 5star–1WIN (1082793) | 1WIN 82.2% | HLTV #14 vs unranked-top side agrees | EGW 1.8/1.8 placeholder |

None of the five has a readable two-sided betting line today; all stay
labelled **research estimates**, which is the honest label the brief requires.

## Group C — live on Hotspawn, not yet published (9 cards)

- **1079658 Acend vs FORZE Reload** — EGW index first-hand today: 2.8/1.35 →
  guided **FORZE Reload 67.5%**.
- The other eight (1081152, 1079659, 1081153, 1079660, 1081154, 1079661,
  1081156, 1081158) await the next collect. No odds are invented for them.
  EGW demonstrably lists same-day low-tier fixtures with real pairs
  (e.g. Fokus 1.23/3.83, cross-checking our published FOKUS 76.5% within
  0.8 pt), so the `egw_live` rung is expected to price most automatically.

## Limitations for generating these picks (executive-summary wording)

1. **HLTV shows no usable prematch book** for these tiers: its Betting block
   carries sweepstakes promos, and its "Pick a winner" percentages are fan
   votes — we never convert them into probabilities.
2. **EGW placeholders:** a lone "1.8" or identical 1.8/1.8 means "no line
   yet", not 50/50; our gates reject them.
3. **$0-volume prediction markets** (Polymarket listings for HOTU–The Huns,
   Rooster–Abyssal, Color–ex-ZT) display multipliers, not tradeable
   two-sided books; they are recorded, never priced.
4. **Research-model numbers are uncalibrated**: direction is the product;
   the percentage is a rating transform, labelled as such everywhere.
5. **Freshness depends on the 4-hour publisher actually running**: a queued
   run (as at 06:09Z today) freezes coverage at the last verified snapshot
   with stale warnings shown, rather than fabricating fresh rows.
