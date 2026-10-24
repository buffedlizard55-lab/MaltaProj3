
## S522-C6B8-001 — reference captures checked against actual inventory

At main `06618b31` (PR #265), C6B8 has 7 schema-valid EGW reference entries, but the unchanged production gate against its own 31-row inventory accepts only **3** and rejects **4** for exact-start drift. Direct recheck of the three accepts finds **one** linked page with the quoted price (1083122, 2.92/1.33) and **two** linked pages showing 1.8/1.8 (1082861 and 1082792). Five of six rejected placeholder rows also have team/start mismatches. The capture is not registered in production and this audit changes no prices. Full row-by-row evidence: `c6b8-reference-integration-review.{json,md}`; four flags are published in `flags.json`.
