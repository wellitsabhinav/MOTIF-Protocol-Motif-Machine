# MOTIF — Protocol Motif Machine

MOTIF explores bounded compound operations for programmable serial I/O. Sampling,
shifting, counting, framing, decisions and responses compose through a fixed
sixteen-entry table. An independent pad guardian controls final output enables.

The **v3 temporal qualification campaign is in progress and unfrozen**. Its
proposed tagged WAIT responsibility measures continuous synchronized RX levels
or elapsed delays while retaining the existing timed sampler and table format.
Logical behavior, circuit cost, unseen generalization and physical closure are
separate gates; a demonstration does not establish all four.

![Actual Yosys-derived connected core modules](docs/demo/figures/architecture/architecture.png)

Run an identified wire-level demonstration and inspect the resulting waveforms:

```sh
python -m pip install -e '.[test]'
python -m pip install matplotlib==3.9.2 Pillow==11.0.0
python -m tools.demo --protocol i2c
python -m tools.demo --all --schematics
```

Open `build/demo/index.html`. The package generates actual RTL waveforms, ordered
executor timelines, configurations, expected/observed results, trace excerpts
and Yosys-derived schematics. It validates model/RTL agreement and returns a
nonzero exit code on a failed check. Reproduction requires Icarus/VVP; schematics
also require Yosys. Full traces and netlists remain ignored build artifacts.
See [getting started](docs/GETTING_STARTED.md) and the
[demonstration guide](docs/demo/README.md).

The bounded profiles cover SPI mode-0 target, UART 8N1 receive, framed timed
stream, seven-bit I²C target and Microwire 93LC46 x16 READ. V3 additionally trains
against the previously selected 1-Wire reset/presence workload. No ROM commands,
data slots, analog compliance or silicon results are established by that test.

Historical evidence stays unchanged. Frozen v2 preserves all 48 I²C cases and
returns Microwire A55A, then passes eight of nine selected 1-Wire initialization
cases. An interrupted short-low sequence incorrectly produces presence:
`MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL`. The earlier BYTE_EXCHANGE
A5FF failure also remains permanent evidence. Read the
[v2 decomposition report](experiments/exchange_decomposition/report.md),
[historical campaign](docs/generalization.md), and
[v3 research records](docs/research/v3_temporal_qualification/).

V2 has no routed physical qualification. Earlier CMOS5L artifacts qualify only
their identified earlier sources. V3 physical work requires an unseen logical
pass after its semantic freeze; no v3 GDS image is supplied before that gate.
See [physical evidence](docs/physical.md).

```sh
python -m pytest -q
python -m tools.rtl_check
python -m tools.formal_check
```

The model and helpers live in `motif/`, synthesizable sources in `src/`, and
wire-level/adversarial checks in `tests/`. Read
[architecture](docs/architecture.md), [execution semantics](docs/execution-model.md),
[host interface](docs/host-interface.md) and [verification](docs/verification.md)
for exact contracts and limits. The dedicated SPI host loads configurations only
while disabled; RX/TX FIFOs connect the host to the protocol engine.

License: Apache-2.0. See [LICENSE](LICENSE).
