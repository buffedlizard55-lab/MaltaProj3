# CD37 first-hand source observations — 2026-10-24

## Scope and observation clock

These are dated platform-side page reads, not a deployment attestation and not a new probability feed. The match pages were rechecked at **2026-10-24T06:32Z**. This fetch path does not expose a trustworthy per-response machine timestamp, so no more precise observation time is claimed. Hotspawn participation percentages and HLTV fan votes were read only as excluded interface content and were never used as probabilities.

The accompanying [25-row candidate reconciliation](coverage-reconciliation.md) replays a fresh runner candidate. It does not claim that these observations have been incorporated into that candidate or deployed to Pages.

## Official Hotspawn lobby cross-check

Source: <https://play.hotspawn.com/lobby>

- The rendered lobby showed **88** total CS2 inventory cards, with **9 Closing Soon + 16 Upcoming = 25 active fixtures**.
- Every one of the 25 `View Match` URLs matched a fixture ID in the candidate reconciliation. This first-hand check confirms the public IDs `1079658`, `1079659`, `1081152`, `1081153`, `1081154`, `1081156`, `1081158`, and the other 18 IDs in the report. Earlier scratch labels in the `108305x`/`108306x` range are **not** used: they are not the public fixture IDs in the rendered lobby.
- The official scheduled-fixture API is retained in the candidate evidence as `hotspawn-fixtures`, observed by the runner at `2026-10-24T05:57:37Z`, HTTP 200, response SHA-256 `58cd064d36ea6af29ec606cdddbd5e0fc343558d8fbbc9e0c8ec0cd1cc134ec2`: <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1>.
- Hotspawn is the inventory source only. Its “% picked” values are not a probability input.

## HLTV first, then external-line review

### Ground Zero–Off Chops (`1082858`)

1. HLTV match <https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026> confirms the two teams, DFRAG Invitational 2026, **Best of 3 (LAN)**, Group A opening match. Its Betting table contained a Stake sweepstakes promotion, not two decimal bookmaker prices. Its fan poll is excluded.
2. EGamersWorld match <https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d> independently displayed:
   - title/About: `26.10.2026 at 03:00`, BO3, Ground Zero vs Off Chops;
   - bookmaker-average text: Off Chops favourite at `1.24`, Ground Zero outsider at `3.44`;
   - `Betting odds` → `Prematch` → **Vave**: Ground Zero `3.44`, Off Chops `1.24`.
3. This is a current third-party aggregated/relayed **line lead**, not a first-party Vave observation. It must still pass the reviewed exact-identity, provider-start, freshness, non-identical-price and no-vig gates before automation may use it. No probability or pick was hand-written here, and the candidate’s existing model estimate was not overwritten.

### Acend–UNiTY (`1082996`)

1. HLTV match <https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13> confirms Acend vs UNiTY, NODWIN Clutch Series 13, Best of 3 (Online), Round of 16. The Betting table showed only a promotion; the fan poll is excluded.
2. The EGW index read earlier in this session showed a non-identical pair (`2.44/1.48`), but the corresponding match page <https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/acend-vs-unity-esports-iwaKSVfgf> displayed **Acend `1.8` / UNITY Esports `1.8`** at 06:32Z.
3. The match page’s About section had no bookmaker prediction sentence, and no `Betting odds` prematch book table followed it. The index pair and match-page placeholder therefore do **not** form a consistent same-page quote. Neither was admitted.

### Metizport–BakS (`1079198`)

1. HLTV match <https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13> confirms Metizport vs BAKS, NODWIN Clutch Series 13, Best of 3 (Online), Round of 16. Its Betting table had only a promotion; its fan poll is excluded.
2. The EGW index showed `1.34/2.85`, while match page <https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/metizport-vs-baks-esports-qOJcZA7Wgq> displayed **Metizport `1.8` / BakS eSports `1.8`** at 06:32Z.
3. The About section had no bookmaker prediction sentence and no prematch book table followed it. No quote was admitted from the conflicting surfaces.

### Rooster–Abyssal (`1082861`)

1. HLTV match <https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026> confirms Rooster vs Abyssal, DFRAG Invitational 2026, Best of 3 (LAN), Group B opening match. Its Betting table showed only a promotion; its fan poll is excluded.
2. The EGW index showed `2.1/1.66`, while match page <https://egamersworld.com/counterstrike/match/4kaAQWgKEx/rooster-vs-team-abyssal-P1tTp3RAg8> displayed **Rooster `1.8` / Team Abyssal `1.8`** at 06:32Z.
3. The About section had no bookmaker prediction sentence and no prematch book table followed it. No quote was admitted. `Team Abyssal` is not silently rewritten here; any automated join must use the reviewed competition-scoped alias registry.

## Parser and integration consequences

- A parser that reads only the match anchor can safely return **no quote** when EGW renders prices in sibling links. That is a coverage limitation, not evidence that a price exists or does not exist elsewhere.
- An index-only number must not be paired with a start copied from Hotspawn. Provider teams and a provider-originated, timezone-bearing start must be proved independently.
- At base commit `bdb4fc9`, `scripts/originate.py::run()` writes `live-egw-reference.json` but never calls `egw_live.load_live()`, so the automated entries cannot affect a pick. PR #237 contains an original-HTML/manifest replay and loader; the issue was logged on `COORDINATION.md` and review comments were left on PRs #245 and #246 rather than editing their claimed files.
- The four-hour pipeline must retain a working replayed loader if the EGW rung is described as active. Otherwise it must be described as disabled. In either case the existing labelled research-model fallbacks remain visible; no blank is filled with an inferred number.

## Remaining limitations

- The 25/25 candidate has **10 model/no-external-line rows**, not 25 money-line rows. Their HLTV and model source links are in the reconciliation report.
- The candidate is not acceptance-clean: `1082860` FlyQuest–Staqued carries Thunderpick `1.001 / 12.00`, observed by the runner at `2026-10-24T05:57:54Z`, and the resulting 92.3006% / 7.6994% is arithmetically consistent but based on a non-actionable leg. The independent reconciler now rejects every money-quote leg `<= 1.01`; this row must be rerun through the fallback ladder or marked unresolved, not hand-adjusted. Official fixture: <https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860>; provider surface: <https://thunderpick.io/api/matches>.
- This session did not obtain raw EGW HTML from the GitHub runner. No claim is made that a real-markup match-page parser is complete.
- No first-party Vave page was read. EGW’s named-book table is third-party evidence, not a direct Vave feed.
- The deployed site still has to be checked after integration. Candidate coverage, source reachability, and Pages deployment are separate facts.
