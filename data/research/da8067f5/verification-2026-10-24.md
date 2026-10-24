# Independent verification pass — 2026-10-24 (session arena-da8067f5)

Everything below was checked against the official source named in the row. Nothing is inferred.

## 1. Published model probability `HOTU 94.1% / The Huns 5.9%` (fixture 1082792)

| Step | Value | Source |
| --- | --- | --- |
| HOTU points | **1437**, standing 31 | [Valve global standings 2026-10-05](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) (read 2026-10-24T06:55Z) |
| The Huns points | **944**, standing 122 (roster Annihilation, Bart4k, bexyz, controlez, Cozen) | same file |
| Transform | `g = 1/sqrt(1 + 3(ln10/400)^2 RD^2/pi^2)`, RD = 75 → **g = 0.972821** | [Valve model/fit.js](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/fit.js) |
| Recompute | `P(HOTU) = 1/(1+10^(g(944-1437)/400)) = 0.94065` → **94.1%** | arithmetic from the two official rows above |

**Result: the published 94.1 / 5.9 replays exactly.** The other row carrying the same team name (701 points) would
give 98.4%, so the roster join that selected 944 is material; it is documented in the site's methodology page and in
`COORDINATION.md` (session arena-9c4b1f7a's arithmetic check).

## 2. Official points for the remaining live fixtures found in the same file

Read from the same 2026-10-05 file, for the nine cards that had no published pick at 06:35Z:

| Team | Standing | Points |
| --- | --- | --- |
| HAVU | 124 | 937 |
| Ground Zero | 136 | 878 |
| Azuolas | 140 | 863 |
| Illyrians | 141 | 862 |
| Lavked | 143 | 862 |
| ex-RUSTEC | 152 | 824 |
| Alter Ego | 155 | 819 |

Not present in the rows read so far: Saint Sinners, 6yuBoJlbl, BakS, Spirit Academy, LFO 10, INOX Division, ex-6666,
FOKUS, Acend, FORZE Reload, ex-Zero Tenacity, Nuclear TigeRES, Color, Metizport, Infinite, UNiTY, NEXVOID, Off Chops,
FlyQuest, Staqued, Rooster, Abyssal, B8, K27, Alliance, FaZe, Luminosity, HOTU(see above), 5star, 1WIN, Envy,
GamerLegion. **"Not present in the rows read" is not "unranked"** — this session read 4 of the file's 10 chunks; the
collector reads the whole file, so it is authoritative and this note is not.

## 3. Start-time convention (lobby vs UTC)

| Claim | Evidence |
| --- | --- |
| The lobby's rendered "Oct 24, 04:00" is US Eastern, not UTC | Polymarket Gamma event `1239213` (`cs2-ace1-forzer-2026-10-24`) carries `startTime` **2026-10-24T08:00:00Z** and its resolution text says "initially scheduled for October 24, 2026 at 10:00 AM ET"; EGamersWorld's match page title reads "24.10.2026 at **08:00**". 04:00 ET = 08:00Z. |

Sources: <https://gamma-api.polymarket.com/events?slug=cs2-ace1-forzer-2026-10-24>,
<https://egamersworld.com/counterstrike/match/_rW8GEyWK/acend-vs-forze-reload-FZO8bqMyg>,
<https://play.hotspawn.com/lobby> (rendered card, read 2026-10-24T06:35Z).

## 4. What this pass did **not** verify

- The nine uncovered cards' eventual picks: they do not exist until the publisher runs again (see the session's
  DA-1 fix). Nothing is predicted here.
- Any row of the published snapshot outside the two model inputs above; the deployed rows carry their own saved
  quotes and are replayed by `scripts/build.py` on every publish.
