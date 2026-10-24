# Hotspawn CS2 Pick'ems — every live card vs the published picks

Session `arena-73bc57bd`. Lobby read **2026-10-24T05:31Z** (25 future cards); published rows read from the deployed branch root (**19** rows, snapshot `2026-10-23T20:10:00Z`).

## Coverage in one line

**16 of 25** future Hotspawn CS2 cards already carry a pick on the published site; **9** do not. Those 9 are all CCT Europe 2026 Series #11/#12 cards, and the cause is the publish pipeline, not a missing source: the scheduled publisher has failed four consecutive runs (latest 40063011446) at *Regression tests*, so no collection has been published since 2026-10-23T19:57:15Z.

The published rows were parsed from the deployed page at **2026-10-24T05:38Z** and frozen in `data/research/73bc57bd/published-rows-2026-10-24.json` (19 rows, page sha256 recorded), so this statement stays auditable after the next successful refresh replaces that page.

## Cards without a published pick

| # | Card | Tournament | Lobby time (as rendered) | HLTV identity | Line evidence read today | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Acend vs FORZE Reload** — [Hotspawn](https://www.hotspawn.com/matches/acend-vs-forze-reload-cct-europe-2026-series-11-1079658) | CCT Europe 2026 Series #11 | Oct 24, 04:00 | [CCT 2026 Europe Series 11](https://www.hltv.org/matches/2399335/acend-vs-forze-reload-cct-2026-europe-series-11) · bo3 · Quarterfinal | Polymarket: Acend 3.23x 31¢ / FORZE Reload 1.43x 70¢ ([source](https://polymarket.com/esports/cs2/cct-europe/cs2-ace1-forzer-2026-10-24), read 05:45Z); EGamersWorld (odds block labelled 'by Thunderpick'): Acend 2.87 / FORZE Reload 1.35 ([source](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK), read 05:42Z); EGamersWorld (match list): Acend 2.85 / FORZE Reload 1.34 ([source](https://egamersworld.com/counterstrike/matches), read 05:33Z) | two-sided external price observed |
| 2 | **HAVU vs Azuolas** — [Hotspawn](https://www.hotspawn.com/matches/havu-vs-azuolas-cct-europe-2026-series-12-1081152) | CCT Europe 2026 Series #12 | Oct 24, 07:00 | [CCT 2026 Europe Series 12](https://www.hltv.org/matches/2399502/havu-vs-azuolas-cct-2026-europe-series-12) · bo3 | EGamersWorld (match list and event schedule): HAVU 1.8 / Azuolas 1.8 ([source](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-12-HiXMAaC8L), read 05:43Z) | placeholder or one-sided books only |
| 3 | **Spirit Academy vs Lavked** — [Hotspawn](https://www.hotspawn.com/matches/spirit-academy-vs-lavked-cct-europe-2026-series-11-1079659) | CCT Europe 2026 Series #11 | Oct 24, 07:00 | [CCT 2026 Europe Series 11](https://www.hltv.org/matches/2399336/spirit-academy-vs-lavked-cct-2026-europe-series-11) · bo3 · Quarterfinal | Polymarket: Spirit Academy 1.49x 67¢ / Lavked 2.86x 35¢ ([source](https://polymarket.com/esports/cs2/cct-europe/cs2-tsa-lavked-2026-10-24), read 05:45Z); Polymarket (event card on the same page): Spirit Academy 01.52x 66% / Lavked 02.94x 34% ([source](https://polymarket.com/esports/cs2/cct-europe), read 05:44Z); EGamersWorld (odds block labelled 'by Thunderpick'): Spirit Academy 1.49 / Lavked 2.45 ([source](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK), read 05:42Z); EGamersWorld (match list): Spirit Academy 1.49 / Lavked 2.54 ([source](https://egamersworld.com/counterstrike/matches), read 05:33Z) | two-sided external price observed |
| 4 | **Saint Sinners vs 6yuBoJlbl** — [Hotspawn](https://www.hotspawn.com/matches/saint-sinners-vs-6yubojlbl-cct-europe-2026-series-12-1081153) | CCT Europe 2026 Series #12 | Oct 24, 10:00 | not enumerated | Polymarket: 6yuBoJlbl 1.06x 94¢ / Saint Sinners 1.05x 95¢ ([source](https://polymarket.com/esports/cs2/cct-europe/cs2-6yuboj-ssins-2026-10-24), read 05:45Z); EGamersWorld (event schedule): 6yuBoJlbl 1.8 / Saint Sinners 1.8 ([source](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-12-HiXMAaC8L), read 05:43Z) | placeholder or one-sided books only |
| 5 | **INOX Division vs BRUTE** — [Hotspawn](https://www.hotspawn.com/matches/inox-division-vs-brute-cct-europe-2026-series-11-1079660) | CCT Europe 2026 Series #11 | Oct 24, 10:00 | not enumerated | EGamersWorld (odds block labelled 'by Thunderpick'): INOX Division 1.76 / Brute 1.94 ([source](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK), read 05:42Z); Polymarket: INOX Division 1.64x 61¢ / Brute 1.79x 56¢ ([source](https://polymarket.com/esports/cs2/cct-europe/cs2-inox-brute-2026-10-24), read 05:45Z) | two-sided external price observed |
| 6 | **BakS vs ILLYRIANS** — [Hotspawn](https://www.hotspawn.com/matches/baks-vs-illyrians-cct-europe-2026-series-12-1081154) | CCT Europe 2026 Series #12 | Oct 24, 13:00 | not enumerated | Polymarket: BakS eSports 1.06x 94¢ / ILLYRIANS 1.08x 93¢ ([source](https://polymarket.com/esports/cs2/cct-europe/cs2-baks-ill4-2026-10-24), read 05:46Z); EGamersWorld (event schedule): BakS eSports 1.8 / ILLYRIANS 1.8 ([source](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-12-HiXMAaC8L), read 05:47Z) | placeholder or one-sided books only |
| 7 | **Nuclear TigeRES vs ex-Zero Tenacity** — [Hotspawn](https://www.hotspawn.com/matches/nuclear-tigeres-vs-ex-zero-tenacity-cct-europe-2026-series-11-1079661) | CCT Europe 2026 Series #11 | Oct 24, 13:00 | not enumerated | EGamersWorld (odds block labelled 'by Thunderpick'): Nuclear TigeRES 1.44 / ex-Zero Tenacity 2.5 ([source](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-11-_rW8GEyWK), read 05:42Z); Polymarket: Nuclear TigeRES 1.49x 67¢ / ex-Zero Tenacity 2.33x 43¢ ([source](https://polymarket.com/esports/cs2/cct-europe/cs2-ntr-zerote-2026-10-24), read 05:46Z) | two-sided external price observed |
| 8 | **Spirit Academy vs LFO 10** — [Hotspawn](https://www.hotspawn.com/matches/spirit-academy-vs-lfo-10-cct-europe-2026-series-12-1081156) | CCT Europe 2026 Series #12 | Oct 25, 08:00 | not enumerated | EGamersWorld (event schedule): Spirit Academy 1.8 / 1.8 (opponent name rendered blank in the read segment) ([source](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-12-HiXMAaC8L), read 05:47Z); Polymarket (different opponent name): Spirit Academy 1.08x 93¢ / Sökerorg 1.06x 94¢ ([source](https://polymarket.com/esports/cs2/cct-europe/cs2-tsa-skr2-2026-10-25), read 05:46Z) | placeholder or one-sided books only |
| 9 | **FORZE Reload vs ex-RUSTEC** — [Hotspawn](https://www.hotspawn.com/matches/forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158) | CCT Europe 2026 Series #12 | Oct 25, 14:00 | not enumerated | Polymarket: FORZE Reload 1.43x 70¢ / ex-RUSTEC 1.05x 95¢ ([source](https://polymarket.com/esports/cs2/cct-europe/cs2-forzer-rustec-2026-10-25), read 05:46Z); EGamersWorld (event schedule): FORZE Reload 1.8 / ex-RUSTEC 1.8 ([source](https://egamersworld.com/counterstrike/event/cct-europe-2026-series-12-HiXMAaC8L), read 05:47Z) | placeholder or one-sided books only |

### Limitations recorded for those cards

- **Acend vs FORZE Reload** — Two reads of the same EGamersWorld block 9 minutes apart differ by 0.02 at the top and 0.01 at the bottom; both are recorded, neither is averaged.
- **Acend vs FORZE Reload** — Polymarket midpoints are not execution prices and fees are excluded.
- **HAVU vs Azuolas** — Identical 1.8/1.8 is the aggregator's unfilled placeholder and is rejected by the repository's pricing policy; it is recorded, not priced.
- **HAVU vs Azuolas** — No Polymarket market for this pair was present in the CCT Europe listing segments read at 05:44-05:47Z; absence is not proof that none exists.
- **Spirit Academy vs Lavked** — The card and table views of the same Polymarket page differ by 1-2 cents within the same read; both are recorded.
- **Saint Sinners vs 6yuBoJlbl** — Both sides quoted at 94-95¢ on $0.00 volume cannot be normalised into a two-team book.
- **Saint Sinners vs 6yuBoJlbl** — No HLTV match page was enumerated for this fixture in this session.
- **INOX Division vs BRUTE** — The Polymarket mids sum to 117¢ on $0.00 volume, i.e. a book with no traded liquidity; it is recorded as thin, not used as a probability.
- **INOX Division vs BRUTE** — No HLTV match page was enumerated for this fixture in this session.
- **BakS vs ILLYRIANS** — Both sides quoted at 93-94¢ on $0.00 volume.
- **BakS vs ILLYRIANS** — No HLTV match page was enumerated for this fixture in this session.
- **Nuclear TigeRES vs ex-Zero Tenacity** — Polymarket shows $0.00 volume; treated as a quoted book, not as traded consensus.
- **Nuclear TigeRES vs ex-Zero Tenacity** — No HLTV match page was enumerated for this fixture in this session.
- **Spirit Academy vs LFO 10** — Name conflict: Hotspawn lists the opponent as 'LFO 10', Polymarket lists 'Sökerorg' for the same 25 Oct 08:00 slot. No alias is created here; an exact-name join must not be assumed.
- **Spirit Academy vs LFO 10** — EGamersWorld renders the opponent as blank in the read segment, so even its pairing is unverified.
- **Spirit Academy vs LFO 10** — Both books are placeholders (identical 1.8/1.8 and 93-94¢ on $0.00 volume).
- **FORZE Reload vs ex-RUSTEC** — Polymarket mids sum to 165¢, which is not a two-team market.
- **FORZE Reload vs ex-RUSTEC** — No HLTV match page was enumerated for this fixture in this session.

## Cards that already carry a published pick

| # | Card | Tournament | Lobby time | Published snapshot line | Method | Pick price observed |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **FOKUS vs ex-6666** — [Hotspawn](https://www.hotspawn.com/matches/fokus-vs-ex-6666-nodwin-clutch-series-13-1079193) | NODWIN Clutch Series #13 | Oct 24, 04:00 | 76.5% / 23.5% | market | 2026-10-23T20:09:50Z |
| 2 | **Nuclear TigeRES vs FORZE Reload** — [Hotspawn](https://www.hotspawn.com/matches/nuclear-tigeres-vs-forze-reload-nodwin-clutch-series-13-1079195) | NODWIN Clutch Series #13 | Oct 24, 10:00 | 62.5% / 37.5% | market | 2026-10-23T20:09:50Z |
| 3 | **Acend vs UNiTY** — [Hotspawn](https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996) | NODWIN Clutch Series #13 | Oct 25, 05:00 | 54.2% / 45.8% | model | 2026-10-23T20:09:59Z |
| 4 | **Metizport vs BakS** — [Hotspawn](https://www.hotspawn.com/matches/metizport-vs-baks-nodwin-clutch-series-13-1079198) | NODWIN Clutch Series #13 | Oct 25, 08:00 | 79.9% / 20.1% | model | 2026-10-23T20:09:59Z |
| 5 | **Infinite vs BRUTE** — [Hotspawn](https://www.hotspawn.com/matches/infinite-vs-brute-nodwin-clutch-series-13-1079199) | NODWIN Clutch Series #13 | Oct 25, 11:00 | 48.0% / 52.0% | market | 2026-10-23T20:09:51Z |
| 6 | **Color vs ex-Zero Tenacity** — [Hotspawn](https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200) | NODWIN Clutch Series #13 | Oct 25, 14:00 | 73.6% / 26.4% | model | 2026-10-23T20:09:59Z |
| 7 | **Ground Zero vs Off Chops** — [Hotspawn](https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858) | DFRAG Invitational 2026 | Oct 25, 23:00 | 44.9% / 55.1% | model | 2026-10-23T20:10:09Z |
| 8 | **NEXVOID vs Alter Ego** — [Hotspawn](https://www.hotspawn.com/matches/nexvoid-vs-alter-ego-dfrag-invitational-2026-1082859) | DFRAG Invitational 2026 | Oct 25, 23:00 | 57.6% / 42.4% | bookmaker | 2026-10-23T20:09:57Z |
| 9 | **FlyQuest vs Staqued** — [Hotspawn](https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860) | DFRAG Invitational 2026 | Oct 26, 23:00 | 92.3% / 7.7% | bookmaker | 2026-10-23T20:09:57Z |
| 10 | **Rooster vs Abyssal** — [Hotspawn](https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861) | DFRAG Invitational 2026 | Oct 26, 23:00 | 47.8% / 52.2% | model | 2026-10-23T20:09:59Z |
| 11 | **B8 vs K27** — [Hotspawn](https://www.hotspawn.com/matches/b8-vs-k27-tesla-cup-2026-1082897) | Tesla Cup 2026 | Oct 27, 04:00 | 62.0% / 38.0% | market | 2026-10-23T20:09:54Z |
| 12 | **Alliance vs FaZe** — [Hotspawn](https://www.hotspawn.com/matches/alliance-vs-faze-tesla-cup-2026-1082898) | Tesla Cup 2026 | Oct 27, 07:00 | 35.0% / 65.0% | market | 2026-10-23T20:09:55Z |
| 13 | **Luminosity vs HOTU** — [Hotspawn](https://www.hotspawn.com/matches/luminosity-vs-hotu-tesla-cup-2026-1082900) | Tesla Cup 2026 | Oct 27, 13:00 | 52.5% / 47.5% | market | 2026-10-23T20:09:55Z |
| 14 | **Envy vs GamerLegion** — [Hotspawn](https://www.hotspawn.com/matches/envy-vs-gamerlegion-tesla-cup-2026-1082901) | Tesla Cup 2026 | Oct 27, 16:00 | 46.5% / 53.5% | market | 2026-10-23T20:09:56Z |
| 15 | **HOTU vs The Huns** — [Hotspawn](https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792) | Moscow Cyber Games 2026 | Oct 31, 05:00 | 94.1% / 5.9% | model | 2026-10-23T20:10:21Z |
| 16 | **5star vs 1WIN** — [Hotspawn](https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793) | Moscow Cyber Games 2026 | Oct 31, 09:00 | 17.8% / 82.2% | model | 2026-10-23T20:09:59Z |

## Published rows that are no longer future lobby cards

| Card | Published line | Method | Start (UTC, from the fixture row) |
| --- | --- | --- | --- |
| **paiN vs Imperial** | 35.0% / 65.0% | market | 2026-10-23T21:00:00Z |
| **Alka vs LOS NINOS** | 75.7% / 24.3% | bookmaker | 2026-10-23T22:00:00Z |
| **Chinggis Warriors vs Rare Atom** | 59.0% / 41.0% | market | 2026-10-24T03:00:00Z |

## Independent cross-check of a published pick

**FOKUS vs ex-6666** — published **FOKUS 76.5% / ex-6666 23.5%** (fair decimal 1.307 / 4.255, price read 2026-10-23T20:09:50Z).

- Live exchange: fokus 79¢ / 6666 22¢; card 79% / 22%; $141.39 Vol ([Polymarket](https://polymarket.com/esports/cs2/nodwin-clutch-series/cs2-fokus-66661-2026-10-24), read 05:46Z)
- Second source: Fokus 1.23 / ex-6666 3.83 (no-vig 75.7% / 24.3% by proportional normalisation) ([EGamersWorld](https://egamersworld.com/counterstrike/matches), read 05:34Z)
- The published 76.5/23.5 sits inside a 3.5-point band between two independent sources read 7.5 hours later (exchange 79/22, bookmaker 75.7/24.3). The pick is unchanged; this is drift, not a discrepancy.

## Phone check, measured not asserted

Build: local `python -m scripts.build` output (site/), which renders the checked-in deterministic fixture (80 inventory / 17 active), not the live 19-row snapshot. Method: Playwright + the repository's bundled chromium against `python -m http.server --directory site`, viewport 320x800 and 390x800; overflow = documentElement.scrollWidth - clientWidth; firstPick = offsetTop of the first pick row; navTarget = the smaller dimension of each nav/button/summary element.

| Page | Width | Horizontal overflow | First pick row | Page height | Nav targets | Smallest |
| --- | --- | --- | --- | --- | --- | --- |
| `/` | 320 px | 0 px | 1146 px down | 33317 px | 34 | 17 px |
| `/` | 390 px | 0 px | 1006 px down | 29671 px | 34 | 17 px |
| `/picks/` | 320 px | 0 px | 2837 px down | 12505 px | 30 | 25 px |
| `/picks/` | 390 px | 0 px | 2643 px down | 11948 px | 30 | 25 px |
| `/unresolved/` | 320 px | 0 px | 57762 px down | 59182 px | 8 | 48 px |
| `/unresolved/` | 390 px | 0 px | 55348 px down | 56567 px | 8 | 48 px |
| `/review/` | 320 px | 0 px | 244606 px down | 247024 px | 123 | 25 px |
| `/review/` | 390 px | 0 px | 206622 px down | 208766 px | 123 | 25 px |

- No horizontal overflow anywhere: 0 px at 320 and 390 on all four checked pages.
- A pick is reachable in one tap from the summary: the first glance row starts 1,146 px (320) / 1,006 px (390) down, after 50 in-site pick links.
- The summary is 33,317 px (320) / 29,671 px (390) tall with the 17-row fixture — roughly 40 phone screens — so the page is navigable but very long.
- The picks list page puts its first row 2,837 px (320) / 2,643 px (390) down: the coverage paragraph, stale banner and the two call-to-action blocks sit above the table.
- The Flagged for Review page is 247,024 px (320) / 208,766 px (390) tall because it renders every session register ever published; the current session's register is appended last, so a phone reader must scroll past all earlier registers to reach it.
- One nav target measures 17 px on its smaller side at both widths (the icon-only nav link); axe WCAG A/AA checks still pass in this build, but it is below the 24 px WCAG 2.2 target-size guidance.

- Limitation: Measurements are of the local fixture build, not the live site; the live 19-row snapshot is taller by two rows and adds its own dated blocks.
- Limitation: The smallest-target figure counts only nav/button/summary elements, not inline text links inside sentences.

## Why the site is behind, with the primary sources

| Run | Started (UTC) | Result |
| --- | --- | --- |
| [40015434337](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40015434337) | 2026-10-23T19:57:15Z | success |
| [40028653350](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40028653350) | 2026-10-23T21:41:56Z | failure — Regression tests (repository fixtures, before any cache restore) |
| [40037957529](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40037957529) | 2026-10-23T23:08:44Z | failure |
| [40048429858](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40048429858) | 2026-10-24T01:08:36Z | failure |
| [40063011446](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40063011446) | 2026-10-24T04:36:29Z | failure — Regression tests (repository fixtures, before any cache restore) |

Reproduced locally at 2026-10-24T05:49:00Z on `main` 2f966a91 with `.venv/bin/python -m unittest tests.test_ca7e10e5_snapshot -v` → **FAILED (failures=1, errors=3)**:

- `ERROR: test_an_older_build_is_still_refused - PublishRefused: snapshot 2026-10-23T09:23:57+00:00 is 20.2h old (limit 12.0h)`
- `ERROR: test_snapshot_json_is_published - PublishRefused: snapshot 2026-10-23T09:23:57+00:00 is 20.2h old (limit 12.0h)`
- `ERROR: test_the_replay_fixture_is_still_never_published - PublishRefused: snapshot 2026-10-23T09:23:57+00:00 is 20.2h old (limit 12.0h)`
- `FAIL: test_the_built_executive_summary_contains_it_once - AssertionError: 2 != 1 (two id="no-line-research" blocks on the built executive summary)`

Both defects are claimed by other sessions on the coordination board at the time of writing, so this dossier records them rather than editing the claimed files.

## Policy actually applied

- Hotspawn "% picked" used as a probability: **False**.
- HLTV fan votes used: **False**.
- Probabilities written by hand: **False**.
- Picks written by hand: **False**.
- Provider aliases created: **False**.
- Lobby times are recorded verbatim as Hotspawn renders them (US Eastern) and are never converted in this dossier; UTC starts are published only where the site's own fixture row already carries data-start.
- A market that did not appear in a read segment is recorded as not observed, never as non-existent.

## Limitations of this dossier

- Lobby cards are recorded in the timezone Hotspawn renders (US Eastern) and are not converted here.
- A market that did not appear in a read segment is "not observed", never "non-existent".
- No probability, pick or provider alias is produced by this dossier; the uncovered cards are inputs for the existing pricing ladder.
- The 25 rendered cards are the future cards in the lobby at read time; Hotspawn paginates the wider weekly inventory, so a card added after 05:31Z is outside this observation.
