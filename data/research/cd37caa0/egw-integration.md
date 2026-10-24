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
