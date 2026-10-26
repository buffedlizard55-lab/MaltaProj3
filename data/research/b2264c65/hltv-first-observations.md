# Session `arena-b2264c65` — HLTV-First & Esportsbook Research for Non-Featured Matches (2026-10-26T01:10:00Z)

Per user scope, external source discovery ran **only** for the 10 open Hotspawn CS2 fixtures not resolved via the featured exact-name money path (`1079201, 1081159, 1081160, 1093218, 1082861, 1081162, 1081163, 1081164, 1082792, 1082793`).

## `b2264c65-1079201-hltv-bovada-upgrade` — Fixtures `1079201`
- **Primary URL**: https://www.hltv.org/matches/2399116/nemesis-vs-inox-division-nodwin-clutch-series-13 (`HTTP 200`)
- **Verdict**: featured model row upgraded to first-party Bovada moneyline (31.25% / 68.75% Nemesis) by extending Team Nemesis -> Nemesis to NODWIN Clutch Series #13
- **Excerpt (`70a227caa29ea0fe…`)**: HLTV 2399116 (2026-10-26T09:00:00Z BO3 Round of 16): Nemesis [VRS #26: mag1k3Y, r3salt, Sdaim, SELLTER, tex1y] vs INOX Division [VRS #98: FenomeN, finW, k0s + substitutes m1QUSE, gooddeph; Stake US Sweepstake promo only]; Bovada event 32756569 (market 539110949): Team Nemesis 1.363636 vs INOX Division 3.00 at 2026-10-26T09:00:00Z; EGW YBEqdQgeA omits EGWxxxBOT average prose.
- **Reason**: Featured exact-name path fell back to Oct 5 Valve ratings (12.35% / 87.65%) because Bovada prints Team Nemesis; extending the existing Team Nemesis -> Nemesis alias to NODWIN Clutch Series #13 binds Bovada 32756569 cleanly.

## `b2264c65-1093218-hltv-thunderpick-bovada-consensus` — Fixtures `1093218`
- **Primary URL**: https://www.hltv.org/matches/2399119/nuclear-tigeres-vs-unity-nodwin-clutch-series-13 (`HTTP 200`)
- **Verdict**: featured model row upgraded to two-book first-party consensus (58.28% / 41.72% Nuclear TigeRES) via scoped Team UNiTY and UNiTY esports aliases
- **Excerpt (`d4c2a26848b39b66…`)**: HLTV 2399119 (2026-10-26T18:00:00Z BO3 Round of 16): Nuclear TigeRES [flouzer, senka, m1QUSE, z1k4, Re1GN] vs UNiTY [KWERTZZ, 2high, M1key, Sn0w, Dytor]; Thunderpick 2888791: Nuclear TigeRES 1.58 vs Team UNiTY 2.20; Bovada 32759181: Nuclear Tigeres 1.606061 vs Unity Esports 2.25; EGW hjhNR8HG_ omits EGWxxxBOT prose.
- **Reason**: Exact-name collector missed Team UNiTY / Unity Esports; originate.py upgrades 1093218 to median consensus across Thunderpick (58.20%) and Bovada (58.35%).

## `b2264c65-1081159-hltv-widebooks-bo3form` — Fixtures `1081159`
- **Primary URL**: https://www.hltv.org/matches/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12 (`HTTP 200`)
- **Verdict**: featured blank resolved via own bo3.gg results-based model (39.04% / 60.96% ex-6666) via Sokerorg -> LFO 10; Entropy -> LFO 10 not added due to 3/5 incomplete roster
- **Excerpt (`997ce9cd19169ea1…`)**: HLTV 2399509 & team 14084 (2026-10-26T12:00:00Z BO3): LFO 10 lists 3-player core dottie, flaw, Sapec (3/5 of Valve #156 Entropy: dottie, flaw, Sapec, tevsii, Toshas) + 2 TBA silhouettes vs ex-6666 (skcH, kL1o, amster, rendysky, stefienson = 4/5 of Valve #127 6666); Polymarket 1255951 spread 0.53 (0.05/0.58) and Kalshi spread 0.56 (0.37/0.93) exceed 0.15; EGW KmXWxVkdr prints 1.8/1.8 with LFO 10 omitted.
- **Reason**: All money books are wider than 0.15 or missing, EGW is a 1.8/1.8 placeholder, and LFO 10 has only 3 confirmed players on HLTV so aliasing Valve #156 Entropy would overstate identity.

## `b2264c65-cct-eu12-valve-rows-1081160-1081162-1081163-1081164` — Fixtures `1081160, 1081162, 1081163, 1081164`
- **Primary URL**: https://www.hltv.org/matches/2399510/havu-vs-illyrians-cct-2026-europe-series-12 (`HTTP 200`)
- **Verdict**: no actionable external betting line exists yet; all four resolve cleanly via unique complete 5-player Valve 2026-10-05 rows with Lavked stand-ins flagged
- **Excerpt (`90deb9463e6d18a6…`)**: HLTV confirms BO3 Swiss Round 3 with Stake US Sweepstake promo only; Polymarket books are crossed or >0.12 wide and Thunderpick/Bovada/Smarkets list none of the four; EGW 7VBYmMdiw, x-XIGxRpk, EXM8MvTDwW (naming Saint Sinners as 5x noName), and LokE-EvKOn all print 1.8/1.8 placeholders; Valve 2026-10-05 resolves HAVU #124 (937) vs Illyrians #141 (862), ex-RUSTEC #92 (1066, 5-man over #152 4-man) vs Spirit Academy #115 (981), BAKS #100 (1044) vs Saint Sinners #158 (810), and Inner Circle Academy #94 (1064) vs Lavked #143 (862; HLTV subs takanashi, FREXEMP).
- **Reason**: 1.8/1.8 EGW placeholders and wide/crossed exchange books are refused; Valve Glicko estimates stand until pre-match books tighten on a subsequent 4h refresh.

## `b2264c65-1082861-rooster-abyssal-standins` — Fixtures `1082861`
- **Primary URL**: https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026 (`HTTP 200`)
- **Verdict**: no valid external money line yet; Valve model (47.76% / 52.24% Abyssal) retained with cross-team stand-in foggers flagged on /review/
- **Excerpt (`88036c461fb454e9…`)**: HLTV 2399891 (2026-10-27T03:00:00Z BO3 LAN): Rooster [SkulL, rekonz, chelleos + substitutes TjP, foggers] vs Abyssal [Forleks, zune, dangeR, vinhy, blood]; EGW P1tTp3RAg8 prints 1.8/1.8 placeholder; Thunderpick/Bovada list no quote and Polymarket book exceeds spread cap; Valve 2026-10-05 lists Rooster #205 (718) vs Abyssal #195 (734, including foggers).
- **Reason**: Identical 1.8/1.8 EGW placeholder and wide exchange books cannot price a match; no manual roster adjustment is invented.

## `b2264c65-moscow-cyber-games-1082792-1082793` — Fixtures `1082792, 1082793`
- **Primary URL**: https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026 (`HTTP 200`)
- **Verdict**: 1082792 resolved via Polymarket 87.0% / 13.0% HOTU; 1082793 retained on Valve model (17.82% / 82.18% 1WIN) with roster-turnover warning
- **Excerpt (`7a30867bdc33566c…`)**: 1082792 (2026-10-31T09:00:00Z BO3 LAN): Polymarket 1241313 (cs2-hotu-the9-2026-10-31) quotes HOTU vs The Huns Esports at 0.87 / 0.13 via scoped The Huns Esports -> The Huns alias, while EGW SfdtzDhiK shows 1.8/1.8. 1082793 (2026-10-31T13:00:00Z BO3 LAN): EGW 4hTvdd1uN shows 1.8/1.8 and Polymarket spread exceeds cap five days ahead; Valve 2026-10-05 prices 5star #80 (1110) vs 1WIN #38 (1383) -> 17.82% / 82.18% 1WIN with 0/5 HLTV lineup overlap flagged.
- **Reason**: 1082792 binds first-party Polymarket via scoped alias; 1082793 has only 1.8/1.8 EGW placeholder and wide early exchange book.

