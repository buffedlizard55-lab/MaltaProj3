# TWC Day 4 first-party check — arena-449bdbba (task D4-1 / D4-2)

Status: **research record only**. Nothing here changes the published site, `data/latest.json`, the picks pipeline, or any shared output. Shared outputs are for the integration session (see `COORDINATION.md`).

Checked: 2026-10-17, sandbox clock after 09:44:08Z (UTC). Machine-readable record: [`day4-first-party-check.json`](day4-first-party-check.json).

## 1. Day-4 semifinals (verified facts)

| Match | Start (UTC) | Format | Market (Polymarket match winner, display) | De-vigged (our calc.) | Source |
| --- | --- | --- | --- | --- | --- |
| FURIA vs Aurora | 14:00Z (10:00 ET / 16:00 Malta) | Bo3 LAN, semifinal | FURIA 53¢ · Aurora Gaming 48¢ · vol $74.7K | FURIA 52.4% · Aurora 47.6% | [HLTV match](https://www.hltv.org/matches/2399414/furia-vs-aurora-thunderpick-world-championship-2026) · [Polymarket TWC list](https://polymarket.com/esports/cs2/thunderpick-world-championship) · [Gamma event](https://gamma-api.polymarket.com/events?slug=cs2-furia-aur1-2026-10-17) |
| Falcons vs BetBoom | 17:00Z (13:00 ET / 19:00 Malta) | Bo3 LAN, semifinal | Falcons 73¢ · BetBoom 28¢ · vol $274K | Falcons 72.3% · BetBoom 27.7% | [HLTV match](https://www.hltv.org/matches/2399415/falcons-vs-betboom-thunderpick-world-championship-2026) · [Polymarket TWC list](https://polymarket.com/esports/cs2/thunderpick-world-championship) · [Gamma event](https://gamma-api.polymarket.com/events?slug=cs2-fal2-bb3-2026-10-17) |

- The live site's Day-4 card shows **FURIA 50.0% / Aurora 50.0%**. The first-party match-winner display is 53¢ / 48¢. An equal split is an implicit 50/50, which the board's own rule forbids. **Flagged (D4-2 #1).**
- De-vig method: `p_i = (1/o_i) / Σ(1/o_j)` on displayed decimal odds (1.89/2.08 and 1.37/3.57). These are indicative. The pipeline should use CLOB midpoints.
- Hotspawn lobby (fetched after 09:44Z) shows community picks of **FURIA 82% / Aurora 18%**. These are ownership, not probability. They are not used in any calculation below.

## 2. Aurora: roster change and form

- Latest roster change found: **July 2026**. HLTV's rebuild report (8 Jul 2026) describes Jimpphat, kyxsan and coach ash replacing MAJ3R, soulfly and Fabre ([HLTV](https://www.hltv.org/news/45082/official-aurora-complete-rebuild-with-kyxsan)). Liquipedia lists Jimpphat and ash joining 2026-07-03 and kyxsan 2026-07-08 ([Liquipedia](https://liquipedia.net/counterstrike/Aurora_Gaming)).
- **No October 2026 roster change was found** in the sources checked. The lineup shown on HLTV's team page is XANTARES, woxic, Wicadia, Jimpphat, kyxsan, with coach ash ([HLTV team](https://www.hltv.org/team/11861/aurora)).
- So the "new players need onboarding" argument is about 14 weeks old by Day 4. It is not a fresh-roster signal.
- Head to head at this event (both HLTV-reported):
  - Day 1 (14 Oct): 9z 2-0 Aurora (Inferno 13-11, Nuke 13-1).
  - Day 3 (16 Oct): **Aurora 2-0 9z** (Cache 13-11, Inferno 13-4). Source: [HLTV news 45736](https://www.hltv.org/news/45736/aurora-beat-9z-to-secure-third-consecutive-top-four-appearance).
- The Day-1 upset was reversed in the rematch. Two series are too few to show a trend.

## 3. Contrarian guidance (our reasoning, not a verified edge)

**Points rule.** Hotspawn says you earn points for each correct pick, more for higher tiers, with a streak bonus. It does **not** say points depend on how many players picked a side ([how-it-works](https://play.hotspawn.com/how-it-works)). Being contrarian therefore does not earn more points. It only changes rank: a winning minority pick gains on the crowd, and a losing one costs you a streak.

**FURIA vs Aurora.** The market is nearly even (52.4 / 47.6). Backing Aurora costs about **0.34 expected points** against backing FURIA, using a 7-point pick and ignoring the streak bonus. That is a small cost for taking the side only 18% of players chose. This is the only Day-4 match where the contrarian side is near a coin flip, so it is the only one that passes the "contrarian but not stupid" test. It is a leaderboard decision, not a probability edge. The roster and form evidence above does not justify more than that.

**Falcons vs BetBoom.** The market has Falcons at about 72%. Taking BetBoom costs roughly 0.45 × points in expectation (about 3 points on a 7-point pick). That is not a "contrarian but not stupid" pick. Default: Falcons.

**Caveat on the crowd figure.** The 18% ownership is the only reason Aurora is a contrarian option. Hotspawn's community percentage is not a probability input, and this sheet does not use it as one.

## 4. Irregularities flagged for the integration owner (D4-2)

1. **Implicit 50/50 on FURIA vs Aurora** on the live TWC and executive-summary cards, against a 53/48 first-party display. Either show the market-derived split with its source or leave it blank.
2. **Mixed status signals.** The live site says "Do not treat these as current picks" and "snapshot needs attention", yet the Day-4 card labels Falcons "Default pick".
3. **Lobby count vs published count.** The Hotspawn lobby header says "187 matches this week". The published inventory is 96 records / 34 upcoming. The CS2-only count was not verified in this session. A coverage audit is needed before claiming full coverage.
4. **Checked-in snapshot is stale.** `data/latest.json` in `main` is dated 2026-10-15T08:36Z. The live Pages copy is dated 2026-10-17T07:16Z. The repository copy is a fixture, not the live feed. Anyone reading the repo sees old data.
5. **Refresh timing.** Scheduled runs at 04:25Z and 07:12Z ran, and the 08:17Z slot did not appear in the run list. This is the documented GitHub delay behaviour, but it means the next run (~10:47Z per the catch-up slot) is needed to clear the stale warning.
6. **Count mismatch inside the live page.** The executive summary says "Retained snapshot picks: 25 / 34" and the TWC/executive block says "26/34 with probabilities". One of these is wrong. Not resolved here.
7. **Lock time**: Hotspawn's rules say 5 minutes; the fixture data uses 6 minutes. This is already flagged as RR-03 and is not changed here.

## 5. What is NOT done

- **Every-match coverage with picks.** Not achieved in this session. The sandbox shell cannot reach the source hosts, and the pipeline (which replays every price from saved first-party evidence) runs only in GitHub Actions. Adding picks by hand would break the replay rule. The live site currently shows 25 of 34 upcoming matches with probabilities and 8 unresolved. Those 8 are listed on the site's unresolved section.
- **Unresolved-match research** (HLTV → esportsbooks → lines). Not done in this session. It needs a dedicated pass per match and a pipeline replay.
- **Automated 4-8 hour refresh.** Already runs (`pages.yml`, cron every 4 h with catch-up slot). This session did not change it.
- **Mobile layout.** Not re-tested in a browser this session. The executive summary is dense on phones (long single-row tables). A mobile pass belongs in the integration session.
- **Pull request and merge.** Not opened. Per the board rules, this session has no scope to merge into `main` on its own, and no site output was changed.

## 6. Links for manual review

- Hotspawn lobby: https://play.hotspawn.com/lobby
- Hotspawn how-it-works: https://play.hotspawn.com/how-it-works
- HLTV TWC event: https://www.hltv.org/events/8932/thunderpick-world-championship-2026
- HLTV FURIA vs Aurora: https://www.hltv.org/matches/2399414/furia-vs-aurora-thunderpick-world-championship-2026
- HLTV Falcons vs BetBoom: https://www.hltv.org/matches/2399415/falcons-vs-betboom-thunderpick-world-championship-2026
- HLTV Aurora team: https://www.hltv.org/team/11861/aurora
- HLTV Aurora beat 9z: https://www.hltv.org/news/45736/aurora-beat-9z-to-secure-third-consecutive-top-four-appearance
- HLTV Aurora rebuild: https://www.hltv.org/news/45082/official-aurora-complete-rebuild-with-kyxsan
- Liquipedia Aurora: https://liquipedia.net/counterstrike/Aurora_Gaming
- Polymarket TWC list: https://polymarket.com/esports/cs2/thunderpick-world-championship
- Polymarket FURIA vs Aurora (gamma): https://gamma-api.polymarket.com/events?slug=cs2-furia-aur1-2026-10-17
- Polymarket Falcons vs BetBoom (gamma): https://gamma-api.polymarket.com/events?slug=cs2-fal2-bb3-2026-10-17
