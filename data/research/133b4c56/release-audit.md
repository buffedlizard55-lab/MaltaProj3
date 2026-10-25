# Independent release audit — 25 October 2026

**Owner:** `arena-133b4c56`  
**Observed:** 2026-10-25 13:48 UTC  
**Status:** verified against checked-in artifacts, build/test output and the official GitHub Actions run; live Hotspawn was not re-fetched during this audit.

## Coverage and unresolved cases

The saved source snapshot `snapshot.json` (generated 05:12:25 UTC) contains 79 fixtures, 18 open, 16 featured-method picks and 2 featured-method gaps. The homepage snapshot reports 18/18 complete-ladder picks: the featured gaps are separately resolved by other research, not by Hotspawn crowd rates:

| Match | Complete-list value shown | Research limitation | Official match / research links |
|---|---|---|---|
| Spirit Academy–LFO 10 (1081156) | 69.9% / 30.1%, median consensus of four money sources | No exact Valve rating; only competition-scoped identity links support the sportsbook listings. Estimate is sourced from a median, not a new line independently quoted by every book. | [Hotspawn fixture](https://www.hotspawn.com/matches/spirit-academy-vs-lfo-10-cct-europe-2026-series-12-1081156) · [Polymarket](https://polymarket.com/event/cs2-tsa-skr2-2026-10-25) · [Kalshi](https://kalshi.com/markets/kxcs2game/counterstrike-2-game/kxcs2game-26oct250800skrtsa) · [Smarkets](https://smarkets.com/sport/esports/cs-go/cct-europe/group-stage/2026/10/25/12-00/spirit-academy-vs-sokerorg) · [Bovada](https://www.bovada.lv/esports/counter-strike-2/cct-europe/series-12/spirit-academy-sokerorg-202610250800) |
| HOTU–The Huns (1082792) | 98.2% / 1.8%, explicitly labelled research model | Multiple Valve rosters match “The Huns”; identity remains ambiguous. Wide Polymarket spread was not used; the bo3.gg results graph is a model, not bookmaker price. | [Hotspawn fixture](https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792) · [HLTV match page](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) · [bo3.gg match results](https://www.bo3.gg/matches) · [Polymarket market](https://polymarket.com/esports/cs2/moscow-cyber-games/cs2-hotu-the9-2026-10-31) |

Hotspawn fixture discovery endpoint saved in the repository: [scheduled CS2 fixtures API](https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1). The saved research says HLTV was inaccessible (403) and names the failed/ambiguous line checks. Do not interpret a blocked endpoint as proof that no line exists. The unresolved page and detail links expose these limitations. No fan-vote or crowd-pick share feeds the probabilities.

## Production refresh blocker and repair

The official scheduled run [40196457503](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40196457503) failed at the regression-test step at 13:30:53 UTC. It never reached collection or the fresh deployment. Re-running all tests locally found one failure in `tests/test_b72154e1_guided_picks.py`: the dossier's historical “unresolved” classification for 1082858 had been asserted against the new 05:12 snapshot, where Polymarket had since resolved it.

The historical assertion failure was independently reproduced, then fixed upstream by session `arena-04174d83` in [PR #326](https://github.com/buffedlizard55-lab/MaltaProj3/pull/326), merged at 13:51:27 UTC. Its historical classification is pinned to the dossier's named `published_snapshot.generated_at`; the newer snapshot can therefore advance without changing a price, pick, model, or source evidence. This audit branch does not duplicate that code change. After the merge, the focused module passed **7 tests**. The post-merge publisher run 40199536037 was queued at observation time; deployment is not yet confirmed.

## Mobile and quality checks

- The Executive Summary provides direct links to on-page picks, the full match list, unresolved details and the leaderboard plan; it includes a responsive viewport declaration, “checks every 4h,” and explicit stale-snapshot warning behavior.
- After building to `site/`, Playwright passed **128/128** tests at 320, 390, 768 and 1440 pixels, including no-JS and automated WCAG A/AA scans. The standalone pick safety audit passed **106** assertions.
- `scripts.build` passed its internal arithmetic/source replay, internal-link checks and acceptance audit (**9 pass, 1 info, 0 fail**); strict row-source audit on the generated current site reported **0 violations**.
- The direct root-only row audit before rebuilding found two violations limited to internal audit-note rows in the older `twc-final/index.html` view; these were not match or probability rows. This stays flagged rather than being hidden.

## Reproducibility and freshness limitation

At observation, top-level `snapshot.json` was 2026-10-25 05:12:25 UTC, but checked-in `data/latest.json` was 2026-10-15 08:36:13 UTC and `data/origination.json` 2026-10-15 09:31:24 UTC (`live_collection=false`). `scripts.build` reads the latter pair as local fixture inputs. Therefore a local build from this repository snapshot does **not** reproduce the top-level 25 October pages without the workflow's newly collected artifact pair. This is a reproducibility gap, not proof the hosted workflow deployed those 15 October files. The scheduled production run's regression failure also meant the latest successful inventory exceeded the eight-hour freshness bound at audit time; existing client warning behavior must be honored. See the linked run and `data/research/133b4c56/release-audit.json` for machine-readable details.
