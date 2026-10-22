# Live inventory verification — arena-75aa5b56 (2026-10-22)

- **Source:** `data/evidence/hotspawn-fixtures.json` at `inventory_observed_at 2026-10-15T08:36:04Z`, reconciled with both rendered lobby pages (`data/evidence/hotspawn-context.json`: `crosscheck: complete`, `verified_pages: [lobby, cs2]`, `records: 80`).
- **Counts in that snapshot:** inventory 80 · upcoming 17 · archived 63 · `coverage_complete: true` (reconciliation record linked from Coverage & Sources: `site/data/evidence/hotspawn-context.json`).
- **Hotspawn contract re-checked in code (`scripts/sources.py:hotspawn`):** the public fixture API is read as an unpaginated array; lobby and CS2 lobby HTML are parsed from the `ng-state` hydration block; duplicate IDs, empty arrays and schema changes fail closed; a 5 s retry handles inter-request churn; when no HTML can be read the API array is published with `unavailable` cross-check marker rather than inventing a reconciliation.
- **Live drift:** hotspawn schedules new fixtures continuously (observed +21 fixtures between 20:39Z and 01:09Z on 22 Oct by session c1fa150f). The 4-hour publisher (`17 */4 * * *` plus catch-up `47 2-22/4 * * *`) rediscovers them automatically; the browser guard (`assets/scout.js`) surfaces a "newer verified snapshot" reload when `data/latest.json` advances.
- **Lock rule:** verified at <https://play.hotspawn.com/how-it-works> (tier points, 5-minute lock, streak bonus). The dashboard honours each fixture's explicit `lock_time` from the API, not an assumed offset.

# What a later session must re-check

- Hit the same fixture API and both lobby URLs in the same round, compare ID sets, and persist the three raw payloads.
- Confirm `data/latest.json:generated_at` is inside the 4-hour window and `data/sources.json` records a successful Hotspawn observation; otherwise publish the stale warning and never restamp old observations.
