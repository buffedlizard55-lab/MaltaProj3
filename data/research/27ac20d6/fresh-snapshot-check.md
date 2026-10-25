# Addendum — the fresh 2026-10-25T14:23:33Z snapshot (task 27AC-3)

Written 2026-10-25T14:45Z, after PR #332 ("Unfreeze the 4-hour publisher, cover the 3 new lobby
fixtures", arena-0db056f7) merged at 14:20Z and the publisher's root-publish landed on `main`.
All reads below are from the rebased tree (`snapshot.json`, `index.html`,
`origination/index.html`) plus one HLTV check; no probability is written here.

## Freshness

- Root `snapshot.json`: `generated_at 2026-10-25T14:23:33Z` — 0.2 h old at re-verify time,
  inside the published 8-hour bound (the 05:12Z snapshot the main dossier covers was 9.2 h old).
- Counts: inventory 78 · upcoming 16 · market 10 · bookmaker 1 · model 2 · **raw unresolved 3** ·
  featured picks 13.
- Published executive summary on the new build: **16 active fixtures, 16 with a directional
  pick, 0 explicitly unresolved** (12 from an external betting line, 4 from a research model).
- `scripts/27ac20d6_verify.py` on the new tree: 6 pass / 0 fail / 3 skip / 1 info — the
  snapshot-bound figure checks skip by design; the structural summary contract passes unchanged.
- Note from PR #341: at its merge the live Pages artefact was one build behind the repo root;
  the live site is re-checked separately after this session's own merge.

## The three new lobby fixtures (all covered)

| Fixture | Match | Published pick | Basis on its card |
| --- | --- | --- | --- |
| 1086696 | BORRACHEIROS vs RED Canids Academy, CCT SA #7, today 16:00Z | RED Canids Academy 56.5% | Featured Polymarket market line (43–44¢ / 56–57¢) |
| 1082697 | BESTIA vs paiN, Circuit X Curitiba #4, today 18:00Z | paiN 58.5% | Featured Polymarket market line (41–42¢ / 58–59¢) |
| 1086697 | Projeto do KinGui vs Yawara, CCT SA #7, today 19:00Z | Projeto do KinGui 65.1% | Researched consensus — Polymarket + Smarkets via verified aliases (Tropa do KinGui → Projeto do KinGui; Yawara Esports → Yawara) |

HLTV identity check for 1086697 (2026-10-25T14:4x): HLTV event
[9452 (CCT 2026 South America Series 7)](https://www.hltv.org/events/9452/cct-2026-south-america-series-7)
lists the team as **Tropa do KinGui** (VRS South America #146) — the exact alias the pipeline's
verified registry (PR #185) used to join Hotspawn's "Projeto do KinGui" to the books; Yawara is
in the same event on HLTV (beat Grêmio 2–0 on 25 Oct). EGamersWorld's page for the fixture again
shows the 1.8 header pair already flagged as a placeholder pattern by session 3877d48d; it is not
used. Identity corroborated; the consensus inputs remain the card's own captured evidence.

## The three raw-unresolved fixtures in the fresh snapshot

| Fixture | Why the featured method blinked | Published resolution | This session's note |
| --- | --- | --- | --- |
| 1086697 KinGui vs Yawara | No exact-name featured fixture | 2-source money consensus (above) | Alias HLTV-corroborated (above) |
| 1082858 Ground Zero vs Off Chops | All three books breached the 0.15 spread ceiling this run — Polymarket 0.21, Kalshi 0.29, Smarkets 0.19 (card's own captures; each still quoted Off Chops as favourite) | Own network model: **Off Chops 55.0%** | Direction unchanged from this morning's featured market pick (Off Chops); the model magnitude is cooler than every rejected book. Same single-source caution as flag `27ac20d6-1082792-magnitude`; recorded, not re-priced |
| 1082792 HOTU vs The Huns | As in the main dossier | Own network model: **HOTU 98.2%** (unchanged) | Main dossier + flags apply verbatim to the fresh build |

## Conclusion for 27AC-3

The unfreeze worked: a fresh snapshot inside the bound, every one of the 16 active fixtures —
including the three new lobby fixtures — carries a published pick, and the three fixtures the
featured method could not price carry a documented blocker trail plus a labelled researched
resolution. No takeover of PR #328/#332's work was needed.
