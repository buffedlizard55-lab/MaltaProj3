# Live coverage + gap-source probe — a pick for every Hotspawn CS2 fixture

Observed 2026-10-26T01:27:03Z (live, GitHub Actions runner). Facts only: this file records what each source served. No probability, pick or alias is written here; the publisher's ladder stays the only path to a published number.

## Hotspawn inventory reconciliation

| Fact | Value |
| --- | --- |
| fixture-API records | 81 |
| open CS2 fixtures | 19 |
| rendered-lobby crosscheck | complete |
| open ids missing from the deployed site | none |
| open fixtures with a published pick | 19 of 19 |
| open fixtures with **no** pick | 0 |
| picks priced by a real market or book | 10 |
| picks resting on a research model | 9 |

## Every open fixture

| Fixture | Starts | Method on the deployed site | Pick | Priced by money? |
| --- | --- | --- | --- | --- |
| Ground Zero vs Off Chops | 2026-10-26T03:00:00Z | market | Off Chops | yes |
| NEXVOID vs Alter Ego | 2026-10-26T03:00:00Z | bookmaker | NEXVOID | yes |
| INOX Division vs Nemesis | 2026-10-26T09:00:00Z | model | Nemesis | no |
| LFO 10 vs ex-6666 | 2026-10-26T12:00:00Z | model | ex-6666 | no |
| FOKUS vs ex-Zero Tenacity | 2026-10-26T12:00:00Z | bookmaker | FOKUS | yes |
| HAVU vs ILLYRIANS | 2026-10-26T15:00:00Z | model | HAVU | no |
| Metizport vs BRUTE | 2026-10-26T15:00:00Z | bookmaker | Metizport | yes |
| Nuclear TigeRES vs UNiTY | 2026-10-26T18:00:00Z | model | Nuclear TigeRES | no |
| FlyQuest vs Staqued | 2026-10-27T03:00:00Z | market | FlyQuest | yes |
| Rooster vs Abyssal | 2026-10-27T03:00:00Z | model | Abyssal | no |
| B8 vs K27 | 2026-10-27T08:00:00Z | market | B8 | yes |
| Alliance vs FaZe | 2026-10-27T11:00:00Z | market | FaZe | yes |
| ex-RUSTEC vs Spirit Academy | 2026-10-27T12:00:00Z | model | ex-RUSTEC | no |
| BakS vs Saint Sinners | 2026-10-27T15:00:00Z | model | BakS | no |
| Luminosity vs HOTU | 2026-10-27T17:00:00Z | market | Luminosity | yes |
| Inner Circle Academy vs Lavked | 2026-10-27T18:00:00Z | model | Inner Circle Academy | no |
| Envy vs GamerLegion | 2026-10-27T20:00:00Z | market | GamerLegion | yes |
| HOTU vs The Huns | 2026-10-31T09:00:00Z | market | HOTU | yes |
| 5star vs 1WIN | 2026-10-31T13:00:00Z | model | 1WIN | no |

## Surfaces tried for the fixtures no money line prices

| Surface | HTTP | Status | Rows parsed | Fixtures whose names appear |
| --- | --- | --- | --- | --- |
| hltv-matches | 200 | ok | 43 | 9 |
| smarkets-events | 200 | ok | 37 | 3 |
| pinnacle-matchups | 200 | ok | 13 | 0 |
| thunderpick-matches | 200 | ok | 49 | 1 |
| kalshi-events | 200 | ok | 0 | 7 |
| bovada-cs2 | 200 | ok | 22 | 2 |
| rivalry-api | 502 | error | 0 | 0 |
| ggbet-api | 403 | error | 0 | 0 |
| betexplorer | 404 | error | 0 | 0 |
| 1xbet-linefeed | 203 | error | 0 | 0 |
| betcet | None | error | 0 | 0 |
| esportsbetting | 200 | ok | 0 | 0 |
| bo3gg-matches | 200 | ok | 0 | 0 |
| egamersworld-matches | 403 | error | 0 | 0 |

## Exact-name joins found for the gap fixtures

Each row is a price the *source* published, with the project's own margin contract applied. A row marked `not bound` means the surface answered but published no price for that fixture.

- **Ground Zero vs Off Chops** (2026-10-26T03:00:00Z, DFRAG Invitational 2026, tier b) — deployed method: market
  - no surface published an exact-name two-team row this hour
- **NEXVOID vs Alter Ego** (2026-10-26T03:00:00Z, DFRAG Invitational 2026, tier b) — deployed method: bookmaker
  - no surface published an exact-name two-team row this hour
- **INOX Division vs Nemesis** (2026-10-26T09:00:00Z, NODWIN Clutch Series #13, tier b) — deployed method: model
  - no surface published an exact-name two-team row this hour
- **LFO 10 vs ex-6666** (2026-10-26T12:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: model
  - no surface published an exact-name two-team row this hour
- **FOKUS vs ex-Zero Tenacity** (2026-10-26T12:00:00Z, NODWIN Clutch Series #13, tier b) — deployed method: bookmaker
  - no surface published an exact-name two-team row this hour
- **HAVU vs ILLYRIANS** (2026-10-26T15:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: model
  - no surface published an exact-name two-team row this hour
- **Metizport vs BRUTE** (2026-10-26T15:00:00Z, NODWIN Clutch Series #13, tier b) — deployed method: bookmaker
  - no surface published an exact-name two-team row this hour
- **Nuclear TigeRES vs UNiTY** (2026-10-26T18:00:00Z, NODWIN Clutch Series #13, tier b) — deployed method: model
  - no surface published an exact-name two-team row this hour
- **FlyQuest vs Staqued** (2026-10-27T03:00:00Z, DFRAG Invitational 2026, tier b) — deployed method: market
  - no surface published an exact-name two-team row this hour
- **Rooster vs Abyssal** (2026-10-27T03:00:00Z, DFRAG Invitational 2026, tier b) — deployed method: model
  - smarkets-events → ['Rooster', 'Abyssal'] @ None · exact-names-and-start · usable: False (None) · [https://smarkets.com/sport/esports/cs-go/dfrag-invitational/group-b/2026/10/27/03-00/rooster-vs-abyssal](https://smarkets.com/sport/esports/cs-go/dfrag-invitational/group-b/2026/10/27/03-00/rooster-vs-abyssal) at 2026-10-26T01:27:07Z
- **B8 vs K27** (2026-10-27T08:00:00Z, Tesla Cup 2026, tier b) — deployed method: market
  - no surface published an exact-name two-team row this hour
- **Alliance vs FaZe** (2026-10-27T11:00:00Z, Tesla Cup 2026, tier b) — deployed method: market
  - no surface published an exact-name two-team row this hour
- **ex-RUSTEC vs Spirit Academy** (2026-10-27T12:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: model
  - no surface published an exact-name two-team row this hour
- **BakS vs Saint Sinners** (2026-10-27T15:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: model
  - no surface published an exact-name two-team row this hour
- **Luminosity vs HOTU** (2026-10-27T17:00:00Z, Tesla Cup 2026, tier b) — deployed method: market
  - no surface published an exact-name two-team row this hour
- **Inner Circle Academy vs Lavked** (2026-10-27T18:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: model
  - no surface published an exact-name two-team row this hour
- **Envy vs GamerLegion** (2026-10-27T20:00:00Z, Tesla Cup 2026, tier b) — deployed method: market
  - no surface published an exact-name two-team row this hour
- **HOTU vs The Huns** (2026-10-31T09:00:00Z, Moscow Cyber Games 2026, tier b) — deployed method: market
  - no surface published an exact-name two-team row this hour
- **5star vs 1WIN** (2026-10-31T13:00:00Z, Moscow Cyber Games 2026, tier b) — deployed method: model
  - no surface published an exact-name two-team row this hour

## Limitations of this probe

- A single hour of observation. Prices move; the four-hour ladder re-reads every source.
- HTTP 403/redirect surfaces (Cloudflare-protected books) are recorded as unreachable, not as "no market".
- Rows joined `name-only` are for review only: without a published start time the project never binds a price to a fixture.
- No number in this file is published as a pick. Only `scripts/originate.py` may do that, with its own strict contract and its own dated evidence.
