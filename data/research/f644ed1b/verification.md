# Current-snapshot audit — arena-f644ed1b

Audit date: 26 October 2026 UTC. No probabilities or fixture identities were changed.

## What was actually checked

| Check | Result | Primary evidence |
| --- | --- | --- |
| Published capture | 25 October 23:03:48 UTC; 72 inventory rows, 10 upcoming | [Immutable captured snapshot](https://github.com/buffedlizard55-lab/MaltaProj3/blob/cfd58e113c76dc82e6482aec17d1b57a9491cadf/snapshot.json) |
| Priced rows | Six exchange, one bookmaker, two Valve model; all nine replay with zero arithmetic errors using the existing independent `824a2780_verify` checker | Each row's provider URL is retained in [rows.json](rows.json) |
| Safety contract | All ten upcoming rows pass the new fixture-independent audit; mutated NaN/boolean probabilities, future/naive observation times, crowd provenance, crossed quotes and a fabricated unresolved pick are rejected | [Checker](../../../scripts/f644ed1b_audit.py), [tests](../../../tests/test_f644ed1b_audit.py) |
| Rating inputs | Rooster 718; Abyssal 734; 5star 1110; 1win 1383 match official file fetched during this session | [Valve official file](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md), [captured file](valve-2026-10-05.md) |
| Featured unresolved | HOTU–The Huns: Valve has two different same-name rosters at 944 and 701 points. The featured-data row remains blank. A separately badged complete-picks research model is not an observed betting line | Same Valve file; [HLTV match URL in captured research](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) |
| Refresh | GitHub reports scheduled run successful | [Run 40240728081](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40240728081) |
| Pages | GitHub reports legacy deployment successful and Pages API status built | [Run 40243418535](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40243418535) |

## Local build and verification boundary

The default local build validates the repository's **historical replay fixture**, not the newer
root published snapshot. It passes the source audit with no unsourced rows and checks 870
internal links/assets/anchors after the three new findings are registered. The two selected
phone navigation/sidebar suites pass all eight tests on that build, including the no-JavaScript
path. The full-suite results are recorded on the coordination board.

An attempt to build the newer root snapshot against the old fixture evidence was correctly
refused (`Inventory observation timestamp restamped`). No evidence timestamp was rewritten.
Downloading the successful publisher's matched Pages artifact was also blocked: GitHub's
artifact download redirects outside this sandbox's allowed hosts. Consequently this session
**does not claim** a full raw-evidence rebuild of the newer snapshot or a live browser read
of the public Pages host. Existing successful publisher status is reported separately from
our local checks.

The first registration build exposed a missing review-register metadata field; that was fixed
before the passing build. No source-access error was converted to a fabricated percentage.

## Reproduce

```sh
python -m scripts.f644ed1b_audit --snapshot snapshot.json --output /tmp/safety.json
python -m scripts.824a2780_verify --check
.venv/bin/python -m scripts.build
.venv/bin/python -m scripts.audit_rows --site site --strict
npx playwright test
```

The first two checks inspect captured published rows; the default build checks the historical
CI fixture. Live identity, current lineups and predictive calibration remain unverified here.
