# Live coverage + gap-source probe — a pick for every Hotspawn CS2 fixture

Observed 2026-10-26T01:00:58Z (live, GitHub Actions runner). Facts only: this file records what each source served. No probability, pick or alias is written here; the publisher's ladder stays the only path to a published number.

## Hotspawn inventory reconciliation

| Fact | Value |
| --- | --- |
| fixture-API records | 81 |
| open CS2 fixtures | 19 |
| rendered-lobby crosscheck | complete |
| open ids missing from the deployed site | ['1082858', '1082859', '1079201', '1081159', '1079202', '1081160', '1079203', '1093218', '1082860', '1082861', '1082897', '1082898', '1081162', '1081163', '1082900', '1081164', '1082901', '1082792', '1082793'] |
| open fixtures with a published pick | 0 of 19 |
| open fixtures with **no** pick | 19 |
| picks priced by a real market or book | 0 |
| picks resting on a research model | 0 |

## Every open fixture

| Fixture | Starts | Method on the deployed site | Pick | Priced by money? |
| --- | --- | --- | --- | --- |
| Ground Zero vs Off Chops | 2026-10-26T03:00:00Z | — | — | no |
| NEXVOID vs Alter Ego | 2026-10-26T03:00:00Z | — | — | no |
| INOX Division vs Nemesis | 2026-10-26T09:00:00Z | — | — | no |
| LFO 10 vs ex-6666 | 2026-10-26T12:00:00Z | — | — | no |
| FOKUS vs ex-Zero Tenacity | 2026-10-26T12:00:00Z | — | — | no |
| HAVU vs ILLYRIANS | 2026-10-26T15:00:00Z | — | — | no |
| Metizport vs BRUTE | 2026-10-26T15:00:00Z | — | — | no |
| Nuclear TigeRES vs UNiTY | 2026-10-26T18:00:00Z | — | — | no |
| FlyQuest vs Staqued | 2026-10-27T03:00:00Z | — | — | no |
| Rooster vs Abyssal | 2026-10-27T03:00:00Z | — | — | no |
| B8 vs K27 | 2026-10-27T08:00:00Z | — | — | no |
| Alliance vs FaZe | 2026-10-27T11:00:00Z | — | — | no |
| ex-RUSTEC vs Spirit Academy | 2026-10-27T12:00:00Z | — | — | no |
| BakS vs Saint Sinners | 2026-10-27T15:00:00Z | — | — | no |
| Luminosity vs HOTU | 2026-10-27T17:00:00Z | — | — | no |
| Inner Circle Academy vs Lavked | 2026-10-27T18:00:00Z | — | — | no |
| Envy vs GamerLegion | 2026-10-27T20:00:00Z | — | — | no |
| HOTU vs The Huns | 2026-10-31T09:00:00Z | — | — | no |
| 5star vs 1WIN | 2026-10-31T13:00:00Z | — | — | no |

## Surfaces tried for the fixtures no money line prices

| Surface | HTTP | Status | Rows parsed | Fixtures whose names appear |
| --- | --- | --- | --- | --- |
| hltv-matches | 200 | ok | 43 | 19 |
| smarkets-events | 200 | ok | 36 | 11 |
| pinnacle-matchups | 200 | ok | 0 | 2 |
| thunderpick-matches | 200 | ok | 0 | 9 |
| kalshi-events | 200 | ok | 0 | 16 |
| bovada-cs2 | 200 | ok | 22 | 8 |
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

- **Ground Zero vs Off Chops** (2026-10-26T03:00:00Z, DFRAG Invitational 2026, tier b) — deployed method: unresolved
  - smarkets-events → ['Ground Zero', 'Off Chops'] @ None · exact-names-and-start · usable: False (None) · [https://smarkets.com/sport/esports/cs-go/dfrag-invitational/group-a/2026/10/26/03-00/ground-zero-vs-off-chops](https://smarkets.com/sport/esports/cs-go/dfrag-invitational/group-a/2026/10/26/03-00/ground-zero-vs-off-chops) at 2026-10-26T01:01:01Z
- **NEXVOID vs Alter Ego** (2026-10-26T03:00:00Z, DFRAG Invitational 2026, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **INOX Division vs Nemesis** (2026-10-26T09:00:00Z, NODWIN Clutch Series #13, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **LFO 10 vs ex-6666** (2026-10-26T12:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **FOKUS vs ex-Zero Tenacity** (2026-10-26T12:00:00Z, NODWIN Clutch Series #13, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **HAVU vs ILLYRIANS** (2026-10-26T15:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **Metizport vs BRUTE** (2026-10-26T15:00:00Z, NODWIN Clutch Series #13, tier b) — deployed method: unresolved
  - bovada-cs2 → ['Metizport', 'Brute'] @ None · name-only-review-only · usable: False (None) · [https://www.bovada.lv/sports/esports/counter-strike](https://www.bovada.lv/sports/esports/counter-strike) at 2026-10-26T01:01:02Z
- **Nuclear TigeRES vs UNiTY** (2026-10-26T18:00:00Z, NODWIN Clutch Series #13, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **FlyQuest vs Staqued** (2026-10-27T03:00:00Z, DFRAG Invitational 2026, tier b) — deployed method: unresolved
  - smarkets-events → ['FlyQuest', 'Staqued'] @ None · exact-names-and-start · usable: False (None) · [https://smarkets.com/sport/esports/cs-go/dfrag-invitational/group-b/2026/10/27/03-00/flyquest-vs-staqued](https://smarkets.com/sport/esports/cs-go/dfrag-invitational/group-b/2026/10/27/03-00/flyquest-vs-staqued) at 2026-10-26T01:01:01Z
- **Rooster vs Abyssal** (2026-10-27T03:00:00Z, DFRAG Invitational 2026, tier b) — deployed method: unresolved
  - smarkets-events → ['Rooster', 'Abyssal'] @ None · exact-names-and-start · usable: False (None) · [https://smarkets.com/sport/esports/cs-go/dfrag-invitational/group-b/2026/10/27/03-00/rooster-vs-abyssal](https://smarkets.com/sport/esports/cs-go/dfrag-invitational/group-b/2026/10/27/03-00/rooster-vs-abyssal) at 2026-10-26T01:01:01Z
- **B8 vs K27** (2026-10-27T08:00:00Z, Tesla Cup 2026, tier b) — deployed method: unresolved
  - smarkets-events → ['B8', 'K27'] @ None · exact-names-and-start · usable: False (None) · [https://smarkets.com/sport/esports/cs-go/tesla-cup/group-a/2026/10/27/08-00/b8-vs-k27](https://smarkets.com/sport/esports/cs-go/tesla-cup/group-a/2026/10/27/08-00/b8-vs-k27) at 2026-10-26T01:01:01Z
  - bovada-cs2 → ['B8', 'K27'] @ None · name-only-review-only · usable: False (None) · [https://www.bovada.lv/sports/esports/counter-strike](https://www.bovada.lv/sports/esports/counter-strike) at 2026-10-26T01:01:02Z
- **Alliance vs FaZe** (2026-10-27T11:00:00Z, Tesla Cup 2026, tier b) — deployed method: unresolved
  - smarkets-events → ['Alliance', 'FaZe'] @ None · exact-names-and-start · usable: False (None) · [https://smarkets.com/sport/esports/cs-go/tesla-cup/group-a/2026/10/27/11-00/alliance-vs-faze](https://smarkets.com/sport/esports/cs-go/tesla-cup/group-a/2026/10/27/11-00/alliance-vs-faze) at 2026-10-26T01:01:01Z
- **ex-RUSTEC vs Spirit Academy** (2026-10-27T12:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **BakS vs Saint Sinners** (2026-10-27T15:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **Luminosity vs HOTU** (2026-10-27T17:00:00Z, Tesla Cup 2026, tier b) — deployed method: unresolved
  - smarkets-events → ['Luminosity', 'HOTU'] @ None · exact-names-and-start · usable: False (None) · [https://smarkets.com/sport/esports/cs-go/tesla-cup/group-b/2026/10/27/17-00/luminosity-vs-hotu](https://smarkets.com/sport/esports/cs-go/tesla-cup/group-b/2026/10/27/17-00/luminosity-vs-hotu) at 2026-10-26T01:01:01Z
  - bovada-cs2 → ['Luminosity', 'HOTU'] @ None · name-only-review-only · usable: False (None) · [https://www.bovada.lv/sports/esports/counter-strike](https://www.bovada.lv/sports/esports/counter-strike) at 2026-10-26T01:01:02Z
- **Inner Circle Academy vs Lavked** (2026-10-27T18:00:00Z, CCT Europe 2026 Series #12, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **Envy vs GamerLegion** (2026-10-27T20:00:00Z, Tesla Cup 2026, tier b) — deployed method: unresolved
  - smarkets-events → ['Envy', 'GamerLegion'] @ None · exact-names-and-start · usable: False (None) · [https://smarkets.com/sport/esports/cs-go/tesla-cup/group-b/2026/10/27/20-00/envy-vs-gamerlegion](https://smarkets.com/sport/esports/cs-go/tesla-cup/group-b/2026/10/27/20-00/envy-vs-gamerlegion) at 2026-10-26T01:01:01Z
  - bovada-cs2 → ['Envy', 'GamerLegion'] @ None · name-only-review-only · usable: False (None) · [https://www.bovada.lv/sports/esports/counter-strike](https://www.bovada.lv/sports/esports/counter-strike) at 2026-10-26T01:01:02Z
- **HOTU vs The Huns** (2026-10-31T09:00:00Z, Moscow Cyber Games 2026, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour
- **5star vs 1WIN** (2026-10-31T13:00:00Z, Moscow Cyber Games 2026, tier b) — deployed method: unresolved
  - no surface published an exact-name two-team row this hour

## Limitations of this probe

- A single hour of observation. Prices move; the four-hour ladder re-reads every source.
- HTTP 403/redirect surfaces (Cloudflare-protected books) are recorded as unreachable, not as "no market".
- Rows joined `name-only` are for review only: without a published start time the project never binds a price to a fixture.
- No number in this file is published as a pick. Only `scripts/originate.py` may do that, with its own strict contract and its own dated evidence.
