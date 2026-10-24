# E57 integrated candidate verification

Recorded 2026-10-24T07:56Z. The production candidate was built from `b66e402` (including `main@89fd1a7`); the final integration also carries the test/research-only delta through `main@0f1eeef`. **All local release gates passed. PR checks were queued at record time; merge and deployment remain pending.**

## Inventory and picks

- Official lobby: <https://play.hotspawn.com/cs2-pickems>, independently read at 06:24Z.
- Featured source snapshot: 2026-10-24T05:57:56Z, 88 source rows and 25 active fixtures.
- Complete origination regenerated at 07:36:33Z with the integrated 80-entry alias registry preserved: **25/25 directional picks, zero unresolved**.
- Methods: **13 market, 2 bookmaker, 1 reviewed aggregate, 9 model**.
- The exact 25 official lobby IDs match the candidate. Hotspawn popularity is not an input.

## Independent replay and build

`final-candidate-audit.{json,md}` independently replays all 25 rows: **25 passed, 0 failed**. This includes official Hotspawn identities, exchange/book arithmetic, Valve's official RD-75 formula and standings, the nine-series form fit, and the reviewed EGW reference. The baseline 25-row network/form audit remains in `candidate-audit.{json,md}`.

The final fresh build passed:

| Check | Result |
| --- | ---: |
| Source rows reconciled | 88 |
| Rendered row-source audit | 936 |
| Rows with official source links | 917 |
| Explicitly flagged unverified | 9 |
| Source-less rows | **0** |
| Acceptance | **10 pass / 0 info / 0 fail** |
| Internal links, assets and anchors | **923 passed** |

The deterministic replay-fixture build also passed after integrating `main`: 80 source rows, 851 audited rows (832 official, 9 explicitly unverified, 10 site-map), zero source-less rows, acceptance 9 pass / 1 info / 0 fail, and 834 internal links.

## Phone and browser verification

`npm test` against the exact fresh final build: **122/122 passed**, zero failed, skipped or flaky (433.92 seconds). Coverage includes 320/390px phones, summary and complete-picks navigation, no-JavaScript rendering, stale/locked pick retirement, findings filters, and automated WCAG A/AA scans.

## Python regression status

The initial full discovery ran 1,353 tests and found nine live-collection errors caused by a missing `egw_live` import, plus two assertions that treated the new “Needs review” filter button as a finding badge. Those defects were fixed and their affected suites rerun. After all production/main conflict resolutions, the complete local discovery passed **1,525/1,525 tests** in 1,020.156 seconds. A further **264/264** affected tests passed around the stricter original-response EGW parser and summary/publisher integration. The final `main` delta added research and tests only; its **44/44 new tests passed** (including the new pyflakes import guard). GitHub's two PR checks were still queued behind the repository backlog at record time, not failed; the publisher reruns regression before deployment.

## Reviewed reference and expiry

Ground Zero–Off Chops uses EGW's match-page aggregate `3.44/1.24`, not a hand-entered probability. Proportional margin removal produces Ground Zero `0.264957264957…` and Off Chops `0.735042735042…`; the directional pick is Off Chops. The capture is a third-party bookmaker average, not a first-party quote. It was observed at 06:29:25Z and must expire at 14:29:25Z under the existing eight-hour gate; it cannot be renewed by assertion.

Source: <https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d>

A replay proves retained-evidence consistency and arithmetic, not future executability or model calibration. HLTV display-clock timezones remain unverified; UTC starts come from Hotspawn's official response. No merge or live deployment is claimed by this record.
