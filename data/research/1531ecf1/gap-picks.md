# Gap picks — arena-1531ecf1

Observed 2026-10-23T10:20:00Z on `arena-session-fetch` (human-readable page fetch, not the GitHub runner; the runner sweep supersedes this record when it lands).

Dated research and gap picks. Only a bound two-sided prematch price or the documented Valve-rating research model may produce the probabilities recorded here. Hotspawn crowd percentages and HLTV fan votes are never inputs.

Policy: HLTV first (identity, format, started/finished state only), then esportsbooks and esports betting-line services (bo3.gg bookmaker relay, Smarkets, Thunderpick, Pinnacle guest board, book-surface sweep). Resolution reuses scripts/originate.py's reviewed ladder. An even estimate never receives an invented side.

## Lobby fixtures missing from the published snapshot

- **NEXVOID vs Rare Atom** (VOID Autumn Cup 2026) — status `finished` — no pick — the pick window has closed: HLTV shows this fixture finished (NEXVOID 0 - 2 Rare Atom at 2026-10-23T09:55Z), so no prematch pick can be generated now. Earlier prematch pick: NEXVOID 62.2% (Valve-rating research estimate; published in the 2026-10-23T04:58Z research record). Nothing is manufactured after lock.
    - HLTV first (identity & state) · checked: https://www.hltv.org/matches/2399587/nexvoid-vs-rare-atom-macemedia-void-autumn-cup-2026 — match finished 0-2. Fan votes recorded as identity evidence only, never converted into a probability.
- **FORZE Reload vs LFO 10** (CCT Europe 2026 Series #12) — status `started` — no pick — the pick window has closed: HLTV shows this fixture in progress (FORZE Reload 2 - 0 LFO 10 at 2026-10-23T09:55Z). Earlier prematch pick: FORZE Reload 51.0% (HLTV world ranking; published in the 2026-10-23T04:58Z research record). Nothing is manufactured after lock.
    - HLTV first (identity & state) · checked: https://www.hltv.org/matches/2399499/forze-reload-vs-lfo-10-cct-2026-europe-series-12 — match in progress 2-0.
- **JiJieHao vs Eternal Fire** (DraculaN Season 7) — status `covered` as fixture 1081606 — not missing: the same pairing carries a Polymarket market-line pick in the published snapshot. The lobby card had no permalink at the 04:58Z observation (id left blank rather than guessed); the name pair and competition match exactly. False gap, not a missing pick.

Counts: 0 lobby fixtures missing and still open, 2 closed since the last collect, 1 false gap covered by the snapshot.

## Runner follow-up

`.github/workflows/1531ecf1-probe.yml` re-runs this research on the GitHub runner (which has egress to Hotspawn, HLTV and the books) for every fixture the featured method cannot resolve, including the no-line/model rows, and commits a `github-actions-runner` record to the same paths. That record supersedes this one by `observed_at`.
