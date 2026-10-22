# Session `arena-3cf793ef` — independent live verification and outside-line research

Read-only verification run on **22 October 2026, 07:36–08:20 UTC** by Arena session
`arena-3cf793ef`. Nothing in this directory feeds a probability, a pick or a match record into
the canonical pipeline. Every figure below is either (a) copied from a published file with its
observation time, or (b) recomputed from an official source whose exact URL is given.

Two other sessions were working on `scripts/build.py`, `scripts/originate.py` and
`assets/scout.css` at the same time (see `COORDINATION.md`), so this session changed no shared
code and published no competing page. Its job was the part the runners cannot do: **read the live
sources directly and check the published numbers against them.**

## 1. Live Hotspawn inventory (`data/research/3cf793ef/live/hotspawn-fixtures.json`)

Source: the scheduled-fixture API Hotspawn's own client calls —
`https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1`,
fetched from the GitHub runner at `2026-10-22T07:36Z` by `scripts/3cf793ef_research.py`.

| Measure | Value | Note |
| --- | --- | --- |
| Records returned | **107** | |
| Unique ids | 107 | **0 duplicates**, so the feed is not silently double-counting |
| Tier B / tier C | 47 / 60 | no other tier value |
| Start in the future | **46** | earliest `2026-10-22T08:00Z`, latest `2026-10-31T13:00Z` |
| Past start still returned as `scheduled` | 61 | preserved as source anomalies, never sold as current picks |
| `best_of` published by Hotspawn | 0 | format stays blank, as the methodology requires |
| Community "% picked" published | 83 | **never used** as a probability input |

## 2. Published snapshot at `2026-10-22T05:36:57Z` (`live/published-*.json`)

`data/latest.json` from the live site: inventory 96, upcoming 33, archived 63, picks 23,
market 10, bookmaker 1, model 12, unresolved 10. `data/origination.json` from the same
deployment: active 33, resolved 33, **with_pick 33, unresolved 0**.

## 3. Coverage drift between the live feed and that snapshot

| Finding | Detail |
| --- | --- |
| Fixtures in the snapshot still present in the live feed | 32 of 33 |
| Fixture in the snapshot that the live feed no longer returns | `1081597` (benched gods vs TitanFlow) — it locked at 10:54Z, so this is normal retirement, not a data error |
| Live fixtures the snapshot does not list at all | **14** (below) — they were added to Hotspawn between 05:36Z and 07:36Z, so the next scheduled refresh picks them up; they are not a ladder failure |

The 14 newer fixtures, with the outside evidence this session could find for each:

| Fixture (Hotspawn id) | Competition | Start (UTC) | Outside price found | Own-line (Valve) recomputation |
| --- | --- | --- | --- | --- |
| FaZe vs BC.Game (`1081599`) | DraculaN Season 7 | 22 Oct 13:00 | **1.77 / 1.94** → FaZe 52.3% | FaZe 71.5% |
| SinnerS vs Eternal Fire (`1081603`) | DraculaN Season 7 | 22 Oct 16:00 | **1.83 / 1.90** → SinnerS 50.9% | Eternal Fire 59.7% |
| Projeto do KinGui vs Martians (`1082919`) | CCT South America 2026 Series #7 | 22 Oct 13:00 | none | both teams absent from the Valve snapshot |
| MEIA NOITE vs Procyon (`1082920`) | CCT South America 2026 Series #7 | 22 Oct 16:00 | none | Procyon 71.9% |
| your end vs Yawara (`1082921`) | CCT South America 2026 Series #7 | 22 Oct 19:00 | none | Yawara 81.4% |
| Low Cortisol BR vs Grêmio (`1082922`) | CCT South America 2026 Series #7 | 22 Oct 22:00 | none | Low Cortisol BR 66.2% |
| Alka vs LOS NINOS (`1082923`) | CCT South America 2026 Series #7 | 23 Oct 13:00 | none | LOS NINOS absent from the Valve snapshot |
| BORRACHEIROS vs QUINTESSÊNCIA (`1082924`) | CCT South America 2026 Series #7 | 23 Oct 16:00 | none | QUINTESSÊNCIA 52.4% |
| BESTIA Academy vs RED Canids Academy (`1082925`) | CCT South America 2026 Series #7 | 23 Oct 19:00 | none | RED Canids Academy absent from the Valve snapshot |
| Isurus vs Hacha (`1082926`) | CCT South America 2026 Series #7 | 23 Oct 22:00 | none | Hacha absent from the Valve snapshot |
| B8 vs K27 (`1082897`) | CIS LAN Championship #9 | 27 Oct 08:00 | none | B8 66.2% |
| Alliance vs FaZe (`1082898`) | CIS LAN Championship #9 | 27 Oct 11:00 | none | Alliance 50.1% |
| Luminosity vs HOTU (`1082900`) | CIS LAN Championship #9 | 27 Oct 17:00 | none | Luminosity 64.9% |
| Envy vs GamerLegion (`1082901`) | CIS LAN Championship #9 | 27 Oct 20:00 | none | Envy absent from the Valve snapshot |

Sources: the price column is `outside-lines-2026-10-22T0740Z.json` (bo3.gg match centre,
`https://bo3.gg/matches/current`, read at 07:40Z, relaying a named partner sportsbook's
**two-way decimal** price); the last column is
`valve-verification.json` recomputed from
`https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md`.

**Why this matters for pick selection.** For `1081603` the two bases disagree about the
*side*: the book makes SinnerS the marginal favourite (50.9%), the Valve ratings make Eternal
Fire a clear favourite (59.7%). A model-only fallback would publish the opposite pick from the
book. For `1081599` they agree on the side but not the confidence (52.3% vs 71.5%). Where a real
money line exists it must win over a research model — which is what the ladder is documented to
do, and what the next refresh will exercise for these two fixtures.

## 4. Verification of every Valve-sourced probability (`valve-verification.json`)

The published snapshot carries 14 rows whose stated source is Valve's official standings.
Each was recomputed with `scripts/3cf793ef_valve_check.py` from the same official markdown
(`valve-standings-2026-10-05.md`, archived byte-for-byte) with the documented formula
`p = 1 / (1 + 10 ** (g * (points_b − points_a) / 400))`,
`g = 1 / sqrt(1 + 3 · (ln10/400)² · RD² / π²)`, fixed `RD = 75`, and the rule that only a
complete five-player roster counts (the file also carries incomplete remnant rows: `Banda Chuya`
once with five players and once with two, `ex-RUSTEC` twice with different rosters, `BRUTE` twice
with two different five-player lineups).

**Result: 14 of 14 reproduced, 0 mismatches, tolerance ±0.002.**

| How it was reproduced | Rows | Meaning |
| --- | --- | --- |
| Direct from the summary table | 10 | points, roster and snapshot all agree; the formula returns the published value to 8 decimals |
| Duplicate name, candidate pair identified | 3 | `Lynn Vision`, `HOTU`, `BRUTE` each have two five-player rows; exactly one candidate pair reproduces the published value |
| Valve's per-roster detail file | 1 | `ex-Zero Tenacity vs ex-RUSTEC` — Valve rounded both sides to 1066, so the published row used `1065.6` and `1066.4` from the linked detail markdown |

| Fixture | Valve points (A / B) | Published | Recomputed |
| --- | --- | --- | --- |
| BakS vs Azuolas | 1044 / 863 | 73.37% | 73.37% |
| Donstu vs Banda chuya | 732 / 801 (five-player rows only) | 40.46% | 40.46% |
| ex-RUSTEC vs Saint Sinners | 1066 / 810 | 80.75% | 80.75% |
| Nemesis vs WW | 1455 / 1023 | 91.83% | 91.83% |
| ex-Zero Tenacity vs ex-RUSTEC | 1065.6 / 1066.4 (detail files) | 49.89% | 49.89% |
| 6yuBoJlbl vs ex-6666 | 1015 / 923, via the reviewed `6666 → ex-6666` alias | 62.60% | 62.60% |

The equal-points row is the interesting one, because it is the only place where the official
**summary** table is not enough. Both rosters show 1066 there; the exact `Final Rank Value` lives
in the per-roster detail markdown. Both detail files are archived in `details/`, and their Git blob
SHAs (`076d8f1d…`, `658080b7…`) match the `detail_sha` recorded in the published row — so the bytes
that were checked are provably the bytes Valve served.

### 4.1 One rule, two implementations (new finding)

`scripts/domain.py:valve_analysis` fails closed when two complete five-player rows share a name
("multiple Valve rosters share this name"). `scripts/originate.py:model_estimate` instead
disambiguates that case with a fresh HLTV lineup proof: exactly one row must share all five
players, or exactly one must share four of five (a single roster change), and the proof is
published as `lineup_disambiguation` with the HLTV match URL and its observation time.

Both behaviours are defensible, but they are **not the same rule**, and the difference is visible
in output: 3 of the 14 published Valve rows (`1081871`, `1079657`, `1082792`) exist only because
the originating path is the lenient one. If the ladder ever moved to the `domain` helper those
three fixtures would become blank instead of priced, and if HLTV is unreachable the
`originate` path fails closed and they go blank too. Recommendation: state the two-step rule
(Valve points + HLTV lineup proof) in `methodology/` and use one implementation for both feeds.

Manual spot check of that proof: `https://www.hltv.org/matches/2399334/brute-vs-baks-cct-2026-europe-series-11`
was read at 08:42Z and lists **BRUTE vs BAKS**, CCT 2026 Europe Series 11, Bo3, 23 Oct 13:00
(HLTV renders US Eastern), with the same five-player BRUTE core the published row claims. The
page also shows HLTV's own community vote (80% / 20%). That number is a vote, not a price, and it
is not an input anywhere in this pipeline.

## 5. External line evidence (`outside-lines-2026-10-22T0740Z.json`)

`https://bo3.gg/matches/current` displayed a two-way decimal pair for eight of the fixtures on
the live Hotspawn list at 07:40Z. Margin removed by proportional normalisation
(`pᵢ = (1/oᵢ) / Σ(1/o)`), the same formula the ladder documents:

| Fixture | Decimal pair | No-vig | Published snapshot (other venue) |
| --- | --- | --- | --- |
| Bushido Wildcats vs ex-6666 | 2.35 / 1.56 | 39.9% / 60.1% | 32.0% / 68.0% (Polymarket) |
| GenOne vs Spirit Academy | 2.03 / 1.71 | 45.7% / 54.3% | 47.5% / 52.5% (Polymarket) |
| FORZE Reload vs Just Players | 1.38 / 2.80 | 67.0% / 33.0% | 66.5% / 33.5% (Polymarket) |
| JiJieHao vs Nexus | 1.44 / 2.63 | 64.6% / 35.4% | 63.5% / 36.5% (Polymarket) |
| Acend vs ex-6666 | 1.61 / 2.12 | 56.8% / 43.2% | 51.5% / 48.5% (Polymarket) |
| UNiTY vs Apogee Betclic | 2.10 / 1.65 | 44.0% / 56.0% | 41.8% / 58.2% (consensus) |
| FaZe vs BC.Game | 1.77 / 1.94 | 52.3% / 47.7% | *not yet in the snapshot* |
| SinnerS vs Eternal Fire | 1.83 / 1.90 | 50.9% / 49.1% | *not yet in the snapshot* |

Two different venues pricing the same fixture are **not** a consensus and are not averaged
here. CCT South America 2026 Series #7 carries no price at all on that page ("All odds are on"
means no odds are listed), and `https://bo3.gg/tournaments/cis-lan-championship-9` reports
"There are currently no matches related to CIS LAN Championship 9", so those fixtures have no
bookmaker line to find.

## 6. Irregularities flagged for review

**A claim this session made and then disproved is kept here on purpose.** Reading the raw
`data/latest.json` suggested that `1082770` (UPGRADE vs Virtus.pro) and `1081148` (Inner Circle
Academy vs Spirit Academy) published a Valve model where a money line existed. The **rendered**
pages were then read at 09:10Z and they are correct: the summary shows Virtus.pro 60.6% (Bovada +
Pinnacle consensus) and Spirit Academy 51.4% (Thunderpick relayed by bo3.gg), both matching
`/origination/`. The raw-JSON reading was the mistake.

What does remain, and is worth fixing:

1. **The published audit snapshot disagrees with the published page.** The `data/latest.json` the
   site serves still holds `analysis.method = "model"` for those two fixtures — 33.31% UPGRADE /
   66.69% Virtus.pro and 61.42% Inner Circle Academy / 38.58% Spirit Academy — and it carries no
   `fallbacks` map. That is deliberate (`scripts/build.py`: *"the published latest.json remains the
   untouched source-directory copy"*): the upgrade is attached while the pages are rendered. The
   effect is still worth stating, because the page links that file as **"Full snapshot JSON ↓"**:
   for `1081148` the snapshot implies the **opposite pick** from the row beside it. The rendered
   page is right; the file a reader is invited to audit does not reflect it. A one-line caption on
   the download, or publishing the resolved record, would close the gap.
2. **Badge wording.** An upgraded, money-backed row renders the purple **Researched** badge while its
   own evidence link says **Bookmaker**. Cosmetic, but it is the one visible badge/source mismatch.
3. **`1081597` is published but no longer listed by Hotspawn** (see §3) — normal retirement, but the
   "33 of 33" figure describes the snapshot, not Hotspawn at read time.
4. **CIS LAN Championship #9 is invisible to bo3.gg** and five CCT South America fixtures are
   unpriced everywhere reachable, so those rows can only ever be research estimates. Their limitation
   text should say so per fixture instead of in one generic sentence.

## 7. Limits of this session

* The sandbox shell can only reach `github.com`, `api.github.com`, `codeload.github.com`,
  npm and PyPI. Hotspawn, HLTV, Polymarket and every sportsbook were read through the agent's
  page reader, not `requests`, so the raw bytes are not stored here — only quoted values, URLs
  and observation times. The runner-side capture in `live/` *is* raw.
* No HLTV page was used as a price. HLTV publishes rankings and results, not two-way prematch
  odds; it refuses the GitHub runners (HTTP 403, recorded in `data/research/fbdc97d6/`) but was
  readable through the agent's page reader, which is how the BRUTE lineup proof above was checked.
  It is an identity and ranking source only, never a probability input.
* Nothing here is a betting instruction, and no probability was invented to fill a blank.

## Reproduce

```bash
python -m scripts.3cf793ef_research            # live inventory + published snapshot (needs network)
python -m scripts.3cf793ef_valve_check         # recompute every Valve-sourced row
```

## 8. A CI blocker this session fixed (phone budget)

Nothing in the pick pipeline, but it stopped every PR from merging, so it is recorded here.
Two "start here" blocks landed from different sessions: `.exec-banner` (session `75aa5b56`) and
`nav.start-here` (session `a56f3474`). On a 320 px phone they stacked to **664 px**, which pushed
`#picks-at-a-glance` to `y = 1505` — five pixels past the `expect(box.y).toBeLessThan(1500)` budget
in `tests/browser/dashboard.spec.mjs`. Run `39744249774` failed on exactly that assertion, and a
re-run was impossible (`run 39744249774 cannot be rerun; its workflow file may be broken`).

Fix: one additive rule at the **end** of `assets/scout.css` (so it wins the cascade against both
earlier blocks) that compacts the nav into a two-column strip at ≤700 px, with `min-width:0` and
`overflow-wrap:anywhere` so it cannot overflow 320 px. Same five links, same text. Measured after
the change: nav 519 px, `#picks-at-a-glance` at `y = 1352` (320 px) and `y = 1365` (390 px).
Full browser suite: **85/85 passing**. No JS, markup or copy was touched.
