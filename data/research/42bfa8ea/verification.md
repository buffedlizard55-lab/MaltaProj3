# Session 42bfa8ea — live coverage, row replays and one wrong claim on the summary

Observed **2026-10-23, 09:52Z–10:10Z** by reading the public Hotspawn lobby, the public site and the
polymarket public API. This is a dated page reading, not a runner capture; the four-hour GitHub Actions
pipeline remains the authority for the published snapshot.

## 1. Inventory: does the site carry every live lobby fixture?

| Check | Observation | Source |
| --- | --- | --- |
| Hotspawn weekly counter | "203 matches this week" | https://play.hotspawn.com/cs2-pickems |
| Hotspawn CS2 tier filter | "All tiers (92)" | https://play.hotspawn.com/cs2-pickems |
| Future fixtures rendered in *Closing Soon* + *Upcoming* | 28, enumerated one by one in `live-coverage.json` | https://play.hotspawn.com/cs2-pickems |
| Site snapshot | built 2026-10-23T09:24Z: 30 active, 30 with a pick, 22 external-line, 8 research-model, 0 unresolved | https://buffedlizard55-lab.github.io/MaltaProj3/ |
| Result | **all 28 lobby fixtures are on the site with a pick**, plus two Hotspawn-API fixtures that are not in the rendered lobby lists (`1082980` LPH vs WBT Academy, `1083025` Imperial vs paiN) | this record |

The lobby prints start times in US Eastern. The site prints Europe/Malta. The apparent six-hour gap
between "07:00" on the lobby and "13:00" on the site is the time-zone difference, not a schedule
conflict: both are 2026-10-23T11:00Z, and Polymarket's market for fixture 1081148 records
`gameStartTime 2026-10-23 11:00:00+00`
(https://gamma-api.polymarket.com/markets?slug=cs2-innerc-tsa-2026-10-23). Europe/Malta also leaves
summer time at 03:00 on 25 October, so the site's local times from that date are UTC+1.

## 2. Row replays: are the published probabilities what the cited book says?

Five rows re-read from the cited Polymarket series market. A replay confirms the published number
against the source; a book that moved after the snapshot is reported as a move, never as a new pick.

| Fixture | Site | Cited Polymarket series market | Read at | Result |
| --- | --- | --- | --- | --- |
| 1081606 JiJieHao vs Eternal Fire | 44.5 / 55.5 | 0.445 / 0.555 | 10:02Z | **confirmed** |
| 1079195 Nuclear TigeRES vs FORZE Reload | 59.0 / 41.0 | 0.595 / 0.405 | 10:04Z | confirmed within a half-cent move |
| 1083014 K27 vs Virtus.pro | 55.5 / 44.5 | 0.56 / 0.44 | 10:04Z | confirmed within a half-cent move |
| 1081148 Inner Circle Academy vs Spirit Academy | 44.5 / 55.5 | 0.435 / 0.565 | 10:04Z | consistent; last price moved one cent after the snapshot |
| 1082861 Rooster vs Abyssal | 47.8 / 52.2 (model) | 0.50 / 0.50 on $116.52 liquidity | 10:06Z | not usable as a price; matches the published wide-book blocker |

Links: https://gamma-api.polymarket.com/markets?slug=cs2-jjh-ef1-2026-10-23 ·
https://gamma-api.polymarket.com/markets?slug=cs2-ntr-forzer-2026-10-24 ·
https://gamma-api.polymarket.com/markets?slug=cs2-k271-vp-2026-10-23 ·
https://gamma-api.polymarket.com/markets?slug=cs2-innerc-tsa-2026-10-23 ·
https://gamma-api.polymarket.com/markets?slug=cs2-rstr-abyssa-2026-10-26

## 3. Limitations, stated rather than papered over

- **Eight of 30** active fixtures have no external two-sided line at this observation and publish a
  labelled, uncalibrated model estimate: Phantom Academy–Banda chuya, Acend–UNiTY, Metizport–BakS,
  Color–ex-Zero Tenacity, Ground Zero–Off Chops, Rooster–Abyssal, HOTU–The Huns, 5star–1WIN.
- **HLTV is not an odds source.** It answers 403 to automated runners and, when readable by a person,
  publishes rankings, form and a fan vote — never a two-sided prematch price. It is used for identity
  and ranking only. https://www.hltv.org/matches
- **Smarkets** lists several of these fixtures; the ladder re-reads its exchange books every refresh and
  rejects thin or crossed markets. https://api.smarkets.com/v3/events/?type=csgo_match&states=upcoming
- No probability, average or pick was recalculated in this record.

## 4. Irregularity found and fixed

The executive summary advertised **JiJieHao vs Eternal Fire** as having *no pick in this build*
("Live Hotspawn fixtures missing from this snapshot — 3 not in this build") while the same page carried
its pick at row 4 of **Picks at a glance** (Eternal Fire 55.5%, market line). The gap check compared
only the featured snapshot, so a fixture resolved on the complete researched list — or one whose lobby
card had no permalink — could never drop out.

Fixed in `scripts/build.py`: the check now reads the complete researched list by Hotspawn id **and** by
normalised team pair, the block is labelled a dated observation with its observation time, and the count
reads "N missing at that observation". `tests/test_9fd5fbf1.py` pins the resolved-row and unmatched-pair
cases. Published on the **Flagged for Review** page as `42bfa8ea-stale-live-coverage-claim`.

## 5. Phone summary change in this session

The executive summary's unresolved section is now a compact digest: counts, each pick without a betting
line with its pick, its blocker and one tap to the evidence, the limitations in plain words and a link to
the full register. The per-stage research chips, the 22-surface source sweep and the dated per-fixture
record stay published in full on `/unresolved/`, so the phone summary no longer repeats ~50 KB of tables
above the picks. No value, pick or source changed.
