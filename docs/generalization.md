# Frozen-vocabulary qualification

This campaign tests whether serial behavior composes through the existing
hardware vocabulary. It does not optimize area, timing, allocation or benchmark
scores. A required change to frozen hardware is a negative result.

## Control boundary

The initial inventory records source commit
`cecd76bc4eabab27c8df5aa00675dec05b1bf78c`. It separates seven conceptual motif
types from their firing aliases and from support/integration components. The
initial BYTE_EXCHANGE implementation is model-only. Gate 1 promotes that existing
model; a separate promoted inventory will freeze the resulting RTL and fixed
integration before reuse tests. Neither inventory is overwritten.

The boundary includes all model and RTL sources, configuration/pin logic,
guardian, FIFO, timer, drive provenance and physical flow inputs. Reuse tests may
use the existing hardware configuration interface only. A new wrapper,
programmable scheduler or conditional datapath is outside this experiment.

## Gate 1: I²C

The RTL uses the existing RX/TX shifters, four-byte FIFOs, shared sample timer,
frontend and pad guardian. The port adds the model's fixed nine-phase exchange
and six-bit guarded-drive history. This promotes existing protocol-specific
machinery; it does not demonstrate that the exchange is generic.

The 48 cases compare 88,287 normalized cycles against the unchanged model.
They cover address/data ACK policies, reads/writes, ninth clocks, repeated START,
FIFO full/empty, stretching, malformed traffic, timing boundaries, reset, abort,
watchdog recovery, resolved first-bit mismatch and own-pad timing protection.
The separate host test loads configuration and exchanges data while stretching.

Nominal typical CMOS5L synthesis reports 2,170 cells, 347 register bits and
35,976.6792 µm² cell area. This is not a routed measurement or a functionally
matched reference comparison. The original subset reports remain unchanged.
The expanded pinned official flow is
[running at its recorded source SHA](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38230818123).

One semantic divergence was corrected in RTL: an active acquisition with no
external progress contributes a watchdog age cycle after rearming, as the model
specifies. A separate Linux Icarus repair moved one net declaration before its
first use, without changing the circuit. Raw source identity and that specific
declaration-only correspondence are reported separately; the existing CI artifact
retest retains its strict source-equality check.

## Reproduction and evidence

```sh
python -m pytest -q
python -m tools.frozen_manifest --historical
python -m tools.generalization --gate 1
python -m tools.rtl_check
python -m tools.formal_check
```

Use `--synthesize` on the Gate 1 command for separate synthesis evidence. With
the pinned typical library in ignored build output it reports nominal area;
otherwise it reports generic cell counts. Physical qualification remains a
separate manually dispatched workflow at the unchanged 6×4 allocation and 50 MHz
target. Gate tests are zero-delay functional tests; STA qualifies routed timing.

Compact results are in `experiments/generalization`. Generated normalized traces
and simulator output stay under ignored build output or CI artifacts. Latency
metrics include controller/FIFO waits; logical route counts are interface groups,
not physical wires or programmable routing resources. Shared storage is counted
once. Analog electrical compliance and fabricated silicon remain unqualified.
