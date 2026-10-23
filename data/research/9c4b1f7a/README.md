# Session arena-9c4b1f7a — snapshot re-verification, 23 October 2026

Scope: independently re-check the *published* snapshot rather than trusting the
build, then fix what failed. The published snapshot at review time was
`generated_at 2026-10-23T09:23:57Z` (inventory 92, upcoming 30, archived 62).

| Check | Result |
| --- | --- |
| Hotspawn lobby → snapshot reconciliation | 30 rendered future cards = 30 active fixtures; 29 lobbied IDs match exactly, the 30th (`1081606`, JiJieHao vs Eternal Fire, no permalink) is matched from Hotspawn's own fixture array |
| A pick for every active fixture | 30 / 30 directional; 22 external-line, 8 research-model, 0 blank |
| Ratings arithmetic | All six ratings-only picks recompute exactly from the official 2026-10-05 Valve standings (fixed RD 75, g = 0.972821) |
| Money-line provenance | Isurus–Hacha consensus median 76.2 % reproduced from its four stored prices; NTR–ILL 84.5/15.5 consistent with the live 86¢/16¢ book |
| Lock-time display | Hotspawn 11:00 UTC = 13:00 Europe/Malta; the lobby's 07:00 is US Eastern for the same instant |
| Phone summary betting line | New `.glance-line` chip prints the stored price; models print nothing |

Files:

* `verification-2026-10-23.json` — every check with its sources and outcome.
* `flags.json` — the irregularities, published on **Flagged for Review**.
* `repo-review.json` — the session review register rendered on **Flagged for Review**.

Nothing in this directory is a probability input. Every figure quoted here is
either reproduced from the site's own stored evidence or read from an official
source, and every page that could not be opened is named as such rather than
guessed around.

## Second pass — 2026-10-23T10:52Z: the refresh that disowned its own picks

At 10:14:05Z the collector succeeded and published 92 CS2 records / 30 active
fixtures, all 30 with a pick. At 10:43:14Z the next build (triggered by the merge
of PR #221) re-ran the collector; the **fixture API answered 403** to that
runner. The refresh failed closed, retained the 10:14 snapshot, and every page
then displayed *"Do not treat these as current picks"* beside those 30 untouched
picks. The same API URL answered 200 from the review environment minutes later,
so the refusal was an access failure on one surface, not a changed or empty feed.

Fix (`scripts/sources.py`, `scripts/collect.py`, `scripts/validate.py`,
`scripts/build.py`): the rendered lobby pages embed the identical
`/api/v1/fixtures` array in their `ng-state` block. When the API is refused, that
array is now used as the inventory, saved as
`data/evidence/hotspawn-rendered-fixtures.json`, the failed attempt stays in the
request manifest, and the cycle is labelled *fixture API refused, lobby pages
agree* (`rendered`) or *one lobby page read* (`rendered-partial`). Two readable
pages that disagree, an empty page, or no readable page at all still fail closed.
`validate.check_inventory()` replays a rendered snapshot from that saved payload
and refuses any claim of API rows. Eleven new tests cover both paths.

Residual limit: if the API **and** both rendered pages are refused in the same
round, the site still keeps the last-good snapshot with the stale warning. That
is correct — nothing is reconstructed from memory.

| Second-pass check | Result |
| --- | --- |
| Was any pick, probability or timestamp altered by the fallback? | No. The fallback only changes which public surface supplies the same official fixture array |
| Can a rendered snapshot be replayed? | Yes — from `hotspawn-rendered-fixtures.json`, with `api_ids` required to be empty and the failed attempt required in the manifest |
| Does a disagreement still fail closed? | Yes — two readable pages with different ID sets, an empty page, or an all-refused round |
| Full suite after the change | see the PR body; `scripts.build` and the row-source audit re-run locally |
