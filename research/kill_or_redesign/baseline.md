# Baseline and provenance

Baseline commit: `9e4c500d1cc38c5b008babd245580d1b7d7e542d`. Frozen v2 for
controlled reproduction: `490a50c3e03f1be96784fd27f9d64b718c2aa5cc`. Frozen v3
RTL matches all manifest LF hashes. The inventory of original tracked inputs is
in [input_identity.json](evidence/input_identity.json). No production input was
changed. Analysis accepts the raw attempt-2 ZIP only when its SHA-256 equals
`5cdff1a5201ebad89713da86188c8bd5b0b7d93afa1737752023c6b7d5e2a7d0`.

| Existing claim | Checked evidence | Result |
|---|---|---|
| Logical qualification | temporal `pytest_final.json`, `temporal.json`, `repair.json`, `regression.json`, `cocotb.json` | Historical 160 tests, 55 temporal fixtures, 18 repaired 1-Wire cases; passing receipts |
| Unseen LIN | `unseen/logical_result.json` and independent `tools/lin_oracle.py` | 34 cases, 3,210,266 compared cycles, pass |
| Matched cost | `synthesis.json`, local raw netlists, identical new mapping | v2 194,376.3318; v3 210,241.9746 µm²; +8.1623327% |
| Attempt 2 | authenticated archive, extracted raw reports/netlist/logs | Routing/GDS reached; setup fails all corners |
| Attempt 3 | raw decoded terminal log, official limit annotation and observations | Six-hour cancellation; incomplete routing; no final physical archive |
| Current tests | `python -m pytest -q`, this study | 422 passed in 30.94 seconds; frozen RTL unchanged |

Raw source locations are under `build/v3_physical/attempt_2/artifacts/runs/wokwi/`.
Pre-layout is `12-openroad-staprepnr`; extracted post-route is
`55-openroad-stapostpnr`. The reference netlists are synthesis `.nl.v` and
`final/nl/*.nl.v`. Reports remain ignored; selected paths and hashes are committed.
The same archive contains DEF, floorplan, placement/routing databases and GDS.
Their availability establishes geometry, not closure.

Attempt-2 setup WNS: fast −0.5328040382, typical −9.7645645444, slow
−26.7513805346 ns. Respective TNS: −53.6000202, −1859.0249581,
−5172.5225247 ns, with 188/198/202 violating setup endpoints. Physical status
remains **UNQUALIFIED**. These agree with raw STA, not just README prose.

Live public CI inspection found completed successful baseline `ci` run
38511322613 and unseen run 38511322602. `v3-routed-tests` 38511322531 also
completed successfully as a workflow; this is not a routed qualification pass
(its gated job can skip). No new workflow was dispatched. Original qualification
receipts and negative results were not overwritten.
