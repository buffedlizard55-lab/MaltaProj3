# CD37 EGamersWorld integration gate

Read-only audit of immutable candidate heads. The probe uses synthetic markup only for safety tests; it does not publish any of the synthetic values as a pick or probability. Production source observations are in [source-observations.md](source-observations.md).

| Audited tree | Required result | Live evidence loaded | Original response replay | No copied Hotspawn start | No substring identity | Sibling-price markup |
| --- | --- | --- | --- | --- | --- | --- |
| [`bdb4fc9` — main base](https://github.com/buffedlizard55-lab/MaltaProj3/commit/bdb4fc92a30989e93263d7ef3842cda045fe6571) | **FAIL (4)** | fail | fail | fail: one entry emitted without a provider time | fail: `Spirit Academy/LFO 10` matched synthetic `Spirit/LFO` | info: zero entries |
| [`013eed2` — PR #237](https://github.com/buffedlizard55-lab/MaltaProj3/commit/013eed255e3386cf7fd99c56aa150829a75ab292) | **PASS** | pass | pass | pass | pass | info: zero entries |
| [`4975f67` — PR #245](https://github.com/buffedlizard55-lab/MaltaProj3/commit/4975f671a4a20543e48f2866e3053ff32c5fe770) | **FAIL (2)** | fail | fail | pass | pass | info: zero entries |

## Acceptance consequence

A final integrated tree must pass every required check in `scripts/cd37caa0_egw_audit.py`. In particular, it is not enough for `scripts/egw_live.py` to contain a safe parser: `scripts/originate.py::run()` must actually load the replayed entries into `reference_rows`.

The `real-sibling-price-markup` result is deliberately **informational**, not a requirement to guess at prices. Current anchor-only parsing returns no entry when EGW places prices in sibling links. That fail-closed behavior is preferable to a fabricated quote, but it must not be reported as successful real-markup price capture.

## Reproduce

```bash
python -m scripts.cd37caa0_egw_audit --root /path/to/tree --out report.json
```

The command exits non-zero on a required failure. The local sandbox probe used BeautifulSoup from an isolated `/tmp` dependency directory; normal project CI installs the repository requirements.

Machine-readable reports:

- [main base](egw-integration-main.json)
- [PR #237 head](egw-integration-pr237.json)
- [PR #245 head](egw-integration-pr245.json)

## Moving-head recheck — 2026-10-24 06:55Z

Both integration branches advanced after the first audit, so they were archived and tested again by immutable SHA:

| Current tree | Required result | Loader | Original replay | Independent provider start | Exact identity |
| --- | --- | --- | --- | --- | --- |
| [`5600a3a` — PR #237](https://github.com/buffedlizard55-lab/MaltaProj3/commit/5600a3a2e31d93fe3f86b81cdf31157a2b313fee) | **PASS** | pass | pass | pass | pass |
| [`67d1356` — PR #246](https://github.com/buffedlizard55-lab/MaltaProj3/commit/67d135687e679a4ac3ae005e5c83f039422e11e2) | **FAIL (3)** | pass | fail | fail: synthetic no-timestamp entry emitted | fail: Academy/sister-team confusion emitted |

PR #246's newer head therefore fixes the previously reported loader omission, but **does not make the older EGW implementation safe**. Its loader consumes saved derived entries without original-HTML/manifest replay, and its parser still copies the Hotspawn start and uses substring identity. The same older path is now present on `main` at `a0c08fa6d013705e1a84498cd85b295f86463306` after the concurrent integration merges. This is a cross-scope regression warning, not a probability change made by this session.

Follow-up comments were posted to [PR #246](https://github.com/buffedlizard55-lab/MaltaProj3/pull/246#issuecomment-6381130106) and [PR #237](https://github.com/buffedlizard55-lab/MaltaProj3/pull/237#issuecomment-6381130374). Final integration must preserve PR #237's safer `egw_live.py` and its replaying `load_live(evidence_dir, matches, registry)` call rather than accepting the older implementation during a conflict resolution.

Current-head machine reports: [PR #237](egw-integration-pr237-current.json) and [PR #246](egw-integration-pr246-current.json).
