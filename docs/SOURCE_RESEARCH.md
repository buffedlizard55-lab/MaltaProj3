# Source research log

Research date: 2026-10-14 UTC. Only public, unauthenticated source data is requested. No access-control or bot-challenge bypass is implemented.

## Initial findings

- Repository audit: only `README.md` existed at baseline. There was no pre-existing featured-pick algorithm, match data, or application to reuse.
- Match authority: <https://play.hotspawn.com/lobby> and the CS2-specific lobby <https://play.hotspawn.com/cs2-pickems>. Hotspawn pick percentages are community participation, **not** odds and are excluded from probability inputs.
- Hotspawn rules: <https://play.hotspawn.com/how-it-works> states that picks lock five minutes before scheduled start. The lobby/API must be checked for actual lock timestamps rather than assuming a rule.
- The human-readable lobby initially showed a larger filter count than the number of visible upcoming cards. Coverage verification must distinguish historical, locked, upcoming, and paginated records.
- External CS2 prediction-market directory: <https://polymarket.com/esports/cs2>. Public API and pagination documentation: <https://docs.polymarket.com/api-reference/events/list-events> and <https://docs.polymarket.com/market-data/discover-markets>. A quoted contract price is not an independent bookmaker quote; any normalized probability is labeled analysis.
- HLTV official match directory: <https://www.hltv.org/matches>. Team statistics/rankings can inform explicitly labeled model estimates, not verified bookmaker lines or verified win probabilities.
- Official esportsbook pages under investigation: <https://thunderpick.io/esports/counter-strike> and <https://www.pinnacle.com/en/esports-hub/cs2>. Availability, identity, market scope and paired prices must be verified before use.

## Environment/access limitations

Direct requests to Hotspawn, HLTV and Polymarket from the coding sandbox failed at TLS because outbound hosts are restricted. Source verification runs on GitHub Actions with ordinary public HTTP access. Web-retrieval tools were used to inspect the official lobby, HLTV match pages and Polymarket documentation independently. Source artifacts/Actions log downloads also use hosts unavailable to this sandbox, so temporary diagnostic evidence is exported to this session's fixed branch for review; it is not a new source of truth.

## Verification rules

1. Every match row carries the original Hotspawn lobby/match URL and an observation timestamp.
2. Missing or ambiguous identities, match start times, series lengths or markets remain null and are flagged.
3. A paired, prematch series-winner market must align with both teams and the match date/time before deriving probabilities. Map, handicap, outright and total markets are excluded.
4. All model outputs are distinguished from verified source facts. No model is emitted without verified inputs; no arbitrary 50/50 replacement fills gaps.
5. A source failure never becomes an empty successful feed or a claim that no markets exist.

This log will be expanded with observed API contracts, verification results and limitations before publication.
