# Run MOTIF and inspect its evidence

MOTIF is an executable digital model and synthesizable RTL for bounded programmable serial I/O. V3 passes logical and cost qualification and has an immutable semantic freeze. Its independently selected LIN prefix passes the unseen logical gate. Physical attempt 2 failed setup timing; the final attempt exceeded the official six-hour execution limit during detailed routing without a physical archive. All three attempts are exhausted and the campaign stops with physical qualification unestablished. See [campaign evidence](research/v3_temporal_qualification/final_report.md) and the [demonstration guide](demo/README.md). Historical v2 and earlier physical results retain their original scope.

## Dependencies

Use Python 3.11 or newer and run commands from the repository root. Model tests use pytest. RTL comparisons require Icarus Verilog and VVP; lint requires Verilator. Formal checks and schematics require Yosys and ABC. Rendering uses matplotlib and Pillow. The pinned Linux tool installation in `.github/workflows/ci.yml` is the canonical reference.

```sh
python -m pip install -e '.[test]'
python -m pip install matplotlib==3.9.2 Pillow==11.0.0
python -m pip install -r test/requirements.txt
python -m pytest -q
```

On Windows, write the package option as `".[test]"`. Set `IVERILOG`, `VVP`, `YOSYS` and `YOSYS_ABC` to executable paths if they are outside PATH. An Icarus distribution with its backend in a separate directory also needs `IVERILOG_BASE`. These variables name local tools; no tool installation belongs in Git.

## Demonstrations

```sh
python -m tools.demo --protocol i2c
python -m tools.demo --protocol microwire
python -m tools.demo --protocol one_wire
python -m tools.demo --protocol spi
python -m tools.demo --protocol uart
python -m tools.demo --protocol timed_stream
python -m tools.demo --all --schematics
```

For the frozen architecture's independently selected LIN break/sync workload,
first recreate its identified local traces and oracle receipt:

```sh
python -m tools.lin_unseen
python -m tools.lin_host_check
python -m tools.demo --protocol unseen
python -m tools.demo --all --reuse
```

The unseen invocation validates the full 34-case model/RTL and independent
wire-level gate before rendering four selected cases. `unseen/result.json` is
a generated local hook because it names generated trace artifacts;
`unseen/logical_result.json` is the committed concise qualification receipt.
`python -m tools.unseen_receipt --verify-artifacts` rejects incomplete, failed
or stale receipts. The fixed 20 kbit/s LIN profile recognizes only a digital
break/sync prefix and emits an experiment FIFO token while keeping all pads
released. It does not add autobaud, PID/data/checksum processing or a physical
transceiver.

Open `build/demo/index.html` in a browser. Each demonstration reports expected and observed behavior and compares every normalized model/RTL observation. The output directory contains a configuration summary, trace excerpt, complete traces, simulation logs, waveforms, and the actual ordered execution timeline. SVG figures are editable; PNG copies are convenient previews. `--reuse` accepts cached traces only after checking the current source identity, deterministic stimulus identity and every recorded artifact hash. A failed oracle, comparison or requested rendering returns a nonzero exit status.

The transaction timeline shows the four executor slots in order. An idle lane means that slot evaluated no entry. Legacy SPI, UART and timed-stream modes use direct generic actors and have no transaction-table execution. A plotted empty transaction timeline for these modes records that fact.

## Configure the model and host

```python
from motif import Engine
from motif.protocols.i2c import target
from motif.transaction import host_bytes

config = target(address=0x52)
engine = Engine(config)
table = host_bytes(config.program)  # 128 bytes, little-endian within each entry
```

Call `engine.step(pins)` once per core clock. The wire-level drivers in `tests/` provide controller examples. The hardware host is a dedicated SPI mode-0 port; disable the engine before changing configuration. Write the sixteen 64-bit entries as 128 bytes at register addresses 128–255. Read [host interface](host-interface.md) for pin assignments, configuration registers, status and FIFO accesses.

V3 retains the sixteen entries and eight opcodes. Temporal qualification uses tagged WAIT entries: RX level persistence or constant delay, a 1–65,535 observation threshold, and restart or alternate behavior on interruption. This responsibility is distinct from the shared timed sampler. Helpers and the precise contract are documented in the v3 preregistration; do not change the contract to accommodate a failed workload.

## Verification and synthesis

```sh
python -m tools.rtl_check
python -m tools.formal_check
python -m tools.frozen_manifest --historical
python -m tools.historical_snapshot --check-freeze
```

The freeze checks compare pinned historical source inventories. A changed v3 working tree does not replace historical sources. V3 campaign gates also require the unchanged I²C stimulus, Microwire oracle, temporal properties and repaired 1-Wire wire-level oracle. The campaign runner and its result files are the source of truth for reached gates.

Run the v3 gates in order. These commands retain complete reports and traces under `build/v3_temporal_qualification/` and return nonzero on failed qualification:

```sh
python -m tools.temporal_campaign --stage model
python -m tools.temporal_campaign --stage temporal
python -m tools.temporal_campaign --stage repair
python -m tools.temporal_campaign --stage regression
```

The regression stage includes the pinned cocotb runtime tests. To obtain a separate runtime receipt, run `python -m tools.host_check --output build/v3_temporal_qualification/cocotb.json --build-dir build/v3_temporal_qualification/host`. If regression uses `--skip-cocotb`, this separate complete passing receipt must match the same source bytes before freezing.

Run matched v2/v3 synthesis only after all logical gates and runtime checks pass:

```sh
python -m tools.temporal_campaign --stage synthesis
```

The synthesis gate checks the pinned CMOS5L library and identical mapping-tool identities, the absolute mapped-area limit, the 10% growth cap and declared storage budgets. A failed budget blocks freeze and later unseen or physical evaluation. `--model-only` results are diagnostic and cannot qualify a freeze. Once a v3 freeze exists, `python -m tools.temporal_campaign --stage freeze-check` verifies its protected source and evidence boundary.

Synthesis measures circuit cost. It does not establish placed timing, routing closure or fabricated hardware behavior. Yosys-derived top-level and focused transaction/temporal schematics generated by `--schematics` use actual elaborated connectivity. The full elaborated JSON and logs remain under `build/demo/architecture/`.

`python docs/demo/render_cost.py --receipt-commit 2be40c4 --output-dir build/demo/cost_fresh`
recreates the selected cost figures from committed matched receipts. Use a fresh
output directory. The JSON preserves measured source/tool/library identities;
mapped cells, declared bits and physical observations have separate scopes.

## Freeze, unseen evaluation and physical views

The v3 experiment may freeze only after its logical and cost gates pass. The unseen workload must be researched and selected after that freeze, with an independent wire-level oracle committed before its configuration. Never change frozen semantics to repair unseen results or substitute another candidate after failure.

Only an unseen logical pass makes the pinned Linux CMOS5L flow eligible. Physical reports and floorplan, placement, routing or GDS views must identify actual v3 artifacts. The committed attempt-2 views bind its actual archive and failed timing result and are labelled UNQUALIFIED. The campaign retains a 6×4 allocation, 20 ns target and at most three diagnosed attempts; missing metrics remain unavailable.

Full generated simulation and physical outputs stay outside Git. Concise source, results, trace excerpts and selected figures may be committed; large reproducible outputs belong in CI artifacts or releases.

Read [v3 physical reproduction](v3_physical_reproduction.md) for exact attempt,
archive, metric, routed-test and rendering commands. After the unseen traces
have been recreated, `python -m tools.v3_delivery --output build/delivery/plain_html`
validates all eleven demonstrations and creates an offline HTML package with
linked editable sources, figures and concise evidence. Its manifest hashes
every packaged file. Full raw traces, netlists and physical archives remain
separately identified artifacts. The unseen CI workflow publishes this package
under `motif-v3-plain-html-demonstration-package`.

The [verified clean HTML package](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38473966248/artifacts/11853572292)
contains all eleven demonstrations, a readable A–Z report with evidence links,
and the identified unqualified attempt-2 gallery. Extract it and open `index.html`.
Its [download verification](../experiments/temporal_qualification/delivery_cffe8f6.json)
checks all 517 file hashes and local HTML links. The final physical run is
was recorded separately as active at that earlier receipt's scope. The
[final diagnosis](research/v3_temporal_qualification/physical_attempt_3_diagnosis.md)
records the subsequent cancellation and fixed attempt-limit stop.
