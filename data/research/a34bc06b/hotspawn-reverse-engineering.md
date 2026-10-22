# Hotspawn CS2 Pick'em Reverse-Engineering & 35/35 Origination Dossier (`arena-a34bc06b`)

**Observed & verified:** `2026-10-22T01:06Z – 01:28Z`

## 1. Hotspawn CS2 Pick'em Architecture & Automated 4-Hour Refresh

1. **Lobby & Hydration Surface (`https://play.hotspawn.com/lobby`, `https://play.hotspawn.com/cs2-pickems`):**
   - Server-rendered React/PHP shell hydrating against the first-party JSON API `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1`.
   - Pick'em rules (`https://play.hotspawn.com/how-it-works`) lock picks **6 minutes** prior to scheduled `starts_at` (`locks_at = starts_at - 6 min`).
   - API records retain `status="scheduled"` after match start until settlement; `scripts/collect.py` classifies past-start records (`starts_at <= now`) as `availability="past"` and never manufactures retrospective prematch probabilities.
   - Crowd selection shares and Pick'em point values are stripped at ingestion and never used as probability inputs (`tests/test_domain.py::SourceSafetyTests::test_crowd_percent_and_points_are_not_inputs`).
2. **Automated Refresh Cadence (`.github/workflows/pages.yml`):**
   - Runs every **4 hours** (`17 */4 * * *` plus `47 2-22/4 * * *` catch-up cron, keeping snapshots strictly inside the 8-hour `MAX_PRICE_AGE_HOURS` window), plus on every push to `main` and `workflow_dispatch`.
   - Executes: regression test suite -> `scripts.collect` -> `scripts.originate --live` -> `scripts.coverage_probe --live` -> `scripts.twc_research` -> `scripts.build` (which runs `validate.py`, `build_origination`, `audit_rows`, and `deployment_audit`) -> Pages artifact deploy -> `scripts.verify_live` + 75s legacy-publisher guard.

## 2. Independent Line Origination & Gap Resolution Across All 35 Active CS2 Fixtures

1. **Multi-Book Money Consensus Unlocked via Verified Competition-Scoped Aliases (`data/origination/aliases.json`):**
   - `1082882 UNiTY vs Apogee Betclic` (`Stake Ranked Episode 6: Closed Qualifier`, `2026-10-22T14:00:00Z`, HLTV `2399784`): upgraded from uncalibrated model (`39.8% / 60.2%`) to a **3-provider money consensus** combining Polymarket (`1231280`), Thunderpick (`2865424`: `2.35 / 1.52`), and Bovada (`32573371`: `2.400 / 1.540541`).
   - `1079189 FORZE Reload vs Just Players` (`NODWIN Clutch Series #13`, `2026-10-22T11:00:00Z`, HLTV `2399106`): unlocked Kalshi (`Just_Players`) + Bovada (`JPlay`) for **full 5-provider consensus**.
   - `1082180 Sangal vs Metizport` (`Stake Ranked Episode 6: Closed Qualifier`, `2026-10-22T16:30:00Z`, HLTV `2399785`): unlocked Bovada (`Sangal Esports`) for **full 5-provider consensus**.
   - Scoped `6666 -> ex-6666` extended to `NODWIN Clutch Series #13` (`1079188`, HLTV `2399105`) and `CCT Europe 2026 Series #12` (`1081146`, HLTV `2399496`).
2. **SHA-256 Hash-Verified Aggregated Bookmaker Average (`scripts/reference_odds.py` + `data/research/a34bc06b/reference-odds.json`):**
   - `1079188 Bushido Wildcats vs ex-6666` (`2026-10-22T08:00:00Z`): `2.26 / 1.55` -> **`40.7% / 59.3%` pick `ex-6666`** (fixing the prior `51.5%` wrong-side uncalibrated network estimate).
   - `1082769 K27 vs NEXORA` (`2026-10-22T17:30:00Z`, HLTV `2399846`): `1.021 / 8.1` -> **`88.8% / 11.2%` pick `K27`** (replacing uncalibrated `98.4%` network fit while holding out `16:00Z` clock-skewed Bovada/Kalshi quotes).
   - Explicitly rejected `1.8 / 1.8` placeholders documented for `1079654`, `1081596`, `1082882`, and `1081148`.
3. **Git-SHA1-Verified Official Valve `Final Rank Value` Tie Resolution (`scripts/sources.py`, `scripts/domain.py`, `scripts/collect.py`, `scripts/validate.py`):**
   - `1079654 ex-Zero Tenacity vs ex-RUSTEC` (`CCT Europe 2026 Series #11`, `2026-10-23T08:00:00Z`, HLTV `2399331`): summary standings rounded both complete 5-player rosters to `1066`. Fetching and verifying the Git SHA-1 blobs of Valve's linked detail files (`0093--ex-zero_tenacity--...md` = **`1065.6`** vs `0092--ex-rustec--...md` = **`1066.4`**) resolves **`ex-RUSTEC` (`50.1%` vs `49.9%`, fair decimal `1.996` vs `2.004`)**, bringing live active coverage to **`35 / 35` (`100.0%`) directional picks** with zero unverified numbers.
