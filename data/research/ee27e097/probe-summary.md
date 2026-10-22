# Line-source probe — 2026-10-22T07:51:05+00:00

Environment: github-actions-runner (ubuntu-24.04), plus a headless Chromium context

| Surface | HTTP | Note |
| --- | --- | --- |
| [EGamersWorld CS2 match listing](https://egamersworld.com/counterstrike/matches) | 403 | Cloudflare challenge to the runner (requests). A person can load the page; its listing odds are unverified and can contradict its own match page — see egamersworld-observation.json. Page title at the runner: 'Just a moment...'. |
| [EGamersWorld match page (Bushido Wildcats vs ex-6666)](https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/bushido-wildcats-vs-ex-6666-Xs452MP7y) | 403 | Cloudflare challenge to the runner (requests). Read by hand for the observation record; most low-tier pages print a 1.8/1.8 placeholder. Page title at the runner: 'Just a moment...'. |
| [BetExplorer CS2](https://www.betexplorer.com/esports/counter-strike-2/) | 404 | No CS2 page at this address (HTTP 404). Not used. |
| [Oddspedia CS2](https://oddspedia.com/esports/counter-strike) | 410 | Permanently deleted (HTTP 410); the previous sweep recorded the same status. Page title at the runner: 'The resource you have requested has been permanently deleted'. |
| [OddsPortal CS2](https://www.oddsportal.com/esports/counter-strike/) | 200 | Answered HTTP 200 on the retry and HTTP 503 on the first sweep. The delivered page is a client-side shell: it names bookmakers but contains no prematch coefficient, so no price can be extracted without reverse-engineering an undocumented API. Not used. Page title at the runner: 'Counter-Strike Betting Odds, eSports | OddsPortal'. |
| [HLTV match listing](https://www.hltv.org/matches) | 403 | Cloudflare challenge to the automated runner. HLTV publishes identity, rankings and a fan vote, not a two-sided prematch price, so it is never an odds input. Page title at the runner: 'Just a moment...'. |
| [bo3.gg public match API (relayed bookmaker quotes)](https://bo3.gg/matches) | 200 | Public match API answered. It relays a named bookmaker quote (Thunderpick) for a subset of upcoming fixtures; the ladder already consumes it through the relay rung. A fixture without that block has no relayed price. |
| [Hotspawn lobby (inventory only)](https://play.hotspawn.com/lobby) | 200 | The authoritative scheduled inventory, independent of any price. Page title at the runner: "Pick'ems Lobby | Hotspawn Play". |
| [EGamersWorld CS2 listing — headless Chromium](https://egamersworld.com/counterstrike/matches) | 403 | A real Chromium context (UTC timezone, desktop user agent) still received the security-verification interstitial, so automation cannot use EGamersWorld as a live price feed. Manual, dated captures remain the only reviewed use of that site. |
| [bo3.gg relay coverage on the same observation](https://api.bo3.gg/api/v1/matches) | 200 | 100 upcoming fixtures read; 23 carried a named bookmaker quote block. Only those can produce a relayed line. |
