# Frozen-vocabulary qualification

This page records the **historical legacy campaign**. Its BYTE_EXCHANGE negative
result is permanent. The subsequent, separately preregistered
[v2 decomposition campaign](../experiments/exchange_decomposition/report.md)
confirms I²C/Microwire reuse, then stops with an unseen duration-qualification
counterexample. Current v2 physical qualification was not reached.

This campaign tests whether serial behavior composes through the existing
hardware vocabulary. It does not optimize area, timing, allocation or benchmark
scores. A required change to frozen hardware is a negative result.

## Control boundary

The initial inventory records source commit
`cecd76bc4eabab27c8df5aa00675dec05b1bf78c`. It separates seven conceptual motif
types from their firing aliases and from support/integration components. The
initial BYTE_EXCHANGE implementation is model-only. Gate 1 promotes that existing
model; the separate promoted inventory freezes source
`47954e7` and its resulting RTL/fixed integration before reuse tests. Neither
inventory is overwritten.

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
The expanded pinned official flow
[passes at its recorded source SHA](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38230818123).
Its routed implementation contains 3,209 standard cells, 350 sequential cells
and 47,805.8 µm² standard-cell area. At the unchanged 50 MHz target, worst setup
slack is +6.5010 ns and worst hold slack +0.1256 ns, with zero setup/hold WNS/TNS
at all three corners. Detailed routing uses 98,152 µm of wire and 18,424 vias,
with zero overflow, routed/Magic DRC and LVS errors. Official precheck and both
host-loaded gate tests pass. Residual max-fanout reports contain 22 violations;
the flow reports no max-slew/capacitance violations. No PPA optimization was done.

One semantic divergence was corrected in RTL: an active acquisition with no
external progress contributes a watchdog age cycle after rearming, as the model
specifies. A separate Linux Icarus repair moved one net declaration before its
first use, without changing the circuit. Raw source identity and that specific
declaration-only correspondence are reported separately; the existing CI artifact
retest retains its strict source-equality check.

## Gate 2: frozen exchange reuse

The [independent Microwire oracle](https://ww1.microchip.com/downloads/en/devicedoc/21712B.pdf)
specifies a bounded x16 READ at address zero: nine command bits, a dummy zero at
the final address clock, then a continuous sixteen-bit response. Two FIFO bytes
preload word A55A. No EEPROM storage or programming is implemented.

All three existing frame modes and both serial orders were tested against the
unchanged RTL. Separate DI/DO is rejected by the existing exchange configuration.
Shared open-drain data and falling-frame prearming are deliberately generous
diagnostics; they do not establish compliant Microwire framing/electrical behavior.

| Existing frame mode | MSB-order result | LSB-order result | Required word |
|---|---|---|---|
| Level | FFFF | FFFF | A55A |
| Falling | FF7F | A5FF | A55A |
| Two-wire | FFFF | FFFF | A55A |

The closest configuration emits A5 correctly. After eight TX bits, however,
the RTL unconditionally enters CONTROLLER_ACK and releases SDA. At the next data
clock the oracle requires D7=0; the RTL outputs released 1, with the second FIFO
byte still ready. The frame/order tests match the unchanged model cycle by cycle.
This is an architecture mismatch with the workload, not an RTL/model divergence.

The source audit classifies BYTE_EXCHANGE as **C: protocol-specific macro**.
Seven-bit-plus-direction first-word interpretation, ninth-clock response and
per-byte controller ACK are structural. Existing constants, policies and timer
settings do not bypass those states. Result:
`MOTIF_BYTE_EXCHANGE_PROTOCOL_SPECIFIC`. This does not prove that no other second
workload could fit the macro; it establishes the documented structural limits
and failure of this independent workload.

No frozen source changed during Gate 2. Gate 3 is **unattempted**, as required
by the stop condition. No generic decomposition or unseen-protocol hardware was
added. Reuse metrics count only validated configurations: six of seven motif
types have multiple current users; BYTE_EXCHANGE has one. These type counts are
not RTL-area fractions, and shared storage groups are counted once.

## Reproduction and evidence

```sh
python -m pytest -q
python -m tools.frozen_manifest --historical
python -m tools.generalization --gate 1
python -m tools.generalization --gate 2
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

Gate 2 exits successfully when its recorded negative counterexamples are
reproduced. A changed hardware boundary fails integrity checking; an unexpected
workload success requires review and is not silently assigned a classification.
The CLI declines Gate 3 after the documented Gate 2 stop condition.
