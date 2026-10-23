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
