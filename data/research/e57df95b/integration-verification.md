# E57 integrated candidate verification

Recorded 2026-10-24T07:01:17Z. **Local candidate passed; full-tree CI and deployment are still pending.**

## Inventory and picks

- Official lobby: <https://play.hotspawn.com/cs2-pickems>, independently read at 06:24Z.
- Featured source snapshot: 2026-10-24T05:57:56Z, 88 source rows and 25 active fixtures.
- Complete origination regenerated at 06:39:03Z: **25/25 directional picks, zero unresolved**.
- Methods: **13 market, 2 bookmaker, 1 reviewed aggregate, 9 model**.
- The exact 25 official lobby IDs match the candidate. Hotspawn popularity is not an input.

## Independent replay and build

`final-candidate-audit.{json,md}` independently replays all 25 rows: **25 passed, 0 failed**. This includes official Hotspawn identities, exchange/book arithmetic, Valve's official RD-75 formula and standings, the nine-series form fit, and the reviewed EGW reference. The baseline 25-row network/form audit remains in `candidate-audit.{json,md}`.

The final fresh build passed:

| Check | Result |
| --- | ---: |
| Source rows reconciled | 88 |
| Rendered row-source audit | 878 |
| Rows with official source links | 859 |
| Explicitly flagged unverified | 9 |
| Source-less rows | **0** |
| Acceptance | **10 pass / 0 info / 0 fail** |
| Internal links, assets and anchors | **922 passed** |

The deterministic replay-fixture build also passed: 80 source rows, 793 audited rows, zero source-less rows, acceptance 9 pass / 1 info / 0 fail, and 831 internal links.

## Phone and browser verification

`npm test` against the fresh final build: **118/118 passed**, zero failed, skipped or flaky (334.77 seconds). Coverage includes 320/390px phones, summary and complete-picks navigation, no-JavaScript rendering, stale/locked pick retirement, findings filters, and automated WCAG A/AA scans.

## Python regression status

The initial full discovery ran 1,353 tests and found nine live-collection errors caused by a missing `egw_live` import, plus two assertions that treated the new “Needs review” filter button as a finding badge. The import was restored and the badge assertions scoped to the actual row badge. The affected command reran **116 tests, all passing**, including live collection and multi-clock determinism; 76 focused integration tests also passed. The full-tree rerun remains a CI merge gate and is not claimed locally.

## Reviewed reference and expiry

Ground Zero–Off Chops uses EGW's match-page aggregate `3.44/1.24`, not a hand-entered probability. Proportional margin removal produces Ground Zero `0.264957264957…` and Off Chops `0.735042735042…`; the directional pick is Off Chops. The capture is a third-party bookmaker average, not a first-party quote. It was observed at 06:29:25Z and must expire at 14:29:25Z under the existing eight-hour gate; it cannot be renewed by assertion.

Source: <https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d>

A replay proves retained-evidence consistency and arithmetic, not future executability or model calibration. HLTV display-clock timezones remain unverified; UTC starts come from Hotspawn's official response.
