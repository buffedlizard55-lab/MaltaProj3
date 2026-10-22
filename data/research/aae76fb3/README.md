# Session arena-aae76fb3 — verification record

This folder holds the dated, read-only audit behind the 2026-10-22 session that fixed two
phone-summary labelling defects. It contains **no** probability input, price capture, alias or
pick: `verification.json` only records what was checked against first-party sources and what was
found. Nothing here is read by the build.

| File | Contents |
| --- | --- |
| `verification.json` | Snapshot under test (generated 2026-10-22T05:37:07Z, 33 active / 33 picks / 0 unresolved), the Hotspawn lobby sample check, six Valve model rows replayed from the official standings file (SHA-256 recorded), HLTV match-identity checks, the Polymarket corroboration, and the two label defects fixed in this session |

## Sources used (all first-party)

- Hotspawn rendered lobby — <https://play.hotspawn.com/lobby> (read 2026-10-22T07:36Z)
- Hotspawn public scheduled-fixture API — <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1>
- Valve official regional standings, 2026-10-05 —
  <https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md>
  (retrieved through the GitHub Contents API, SHA-256 `df96e7fc3cd91a2687ec08cac0128e50cc4e4e55346581679572e881d79ae61b`)
- HLTV match pages (read by hand; the automated runner receives HTTP 403) —
  <https://www.hltv.org/matches/2399784/unity-vs-betclic-stake-ranked-episode-6-closed-qualifier>,
  <https://www.hltv.org/matches/2399105/bushido-wildcats-vs-ex-6666-nodwin-clutch-series-13>
- Polymarket event — <https://polymarket.com/esports/cs2/stake-ranked/cs2-unity-bca-2026-10-22>

## Limits of this audit

- The deployed evidence originals (saved provider responses) were **not** re-downloaded: the
  Actions artifact endpoint is not reachable from the sandbox. Their replay is enforced by the
  publisher (`scripts/validate.py`, `scripts/audit_rows.py`, `tests/test_source_integrity.py`) and
  by the post-deploy verification step.
- 23 of the 33 published fixtures were matched against the lobby by hand; the publisher's own
  three-way reconciliation covered all of them at the observation instant.
- Map vetoes, stand-ins and current lineups remain unverified, exactly as each model row states.
