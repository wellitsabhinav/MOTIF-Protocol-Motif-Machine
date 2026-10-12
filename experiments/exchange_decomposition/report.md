# One-cycle exchange decomposition — technical report

## A. Executive classification

`MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL`.
One preregistered decomposition preserves I²C and expresses the frozen Microwire
READ. Subsequently selected 1-Wire initialization passes eight of nine cases;
interrupted short lows expose missing continuous duration qualification. The
campaign stops without a second semantic repair or v2 physical run.

## B. Legacy falsification preservation

The permanent legacy result remains `MOTIF_BYTE_EXCHANGE_PROTOCOL_SPECIFIC`.
Expected A55A, closest observed A5FF: mandatory CONTROLLER_ACK releases the
second byte's output. All six historical configurations and their oracle,
manifests, source hashes, traces and physical reports remain unchanged in
`experiments/generalization/` and `reports/`.

`python -m tools.generalization --gate 2 --baseline legacy` runs an isolated
snapshot of `7a74a1772dd178e498228667b54ec6a2fd39373a`, independent of current
production sources. Its Git object/source identity is checked. Ignored build
artifacts were inventoried before work; no evidence was deleted. Complete traces
are reproducible from committed pinned inputs rather than dependent on local
untracked files. The source audit records artifact retention decisions.

## C. Source decomposition

[The exhaustive audit](source_audit.md) covers all nine legacy states, every
registered variable, transition and combinational output, framing priority,
timer and provenance pipeline, FIFO decisions, host validation, watchdog and
guardian. Audit commit `67962e1` precedes preregistration and implementation.

The failure coupled bounded field qualification, role choice, ownership,
response clocks and readiness/settling. Waiting is independent: FIFO readiness
and first-bit settling exist without a response clock. Six established motif
types remain shared; four operations replace the monolithic transaction macro.

## D. Preregistered architecture

Immutable preregistration commit:
`d3ca35e2221f8e7654f4c42fa79ab7992e8ee8d8`.
The [machine contract](preregistered_architecture.json) and
[portable rationale](design_rationale.md) precede model and RTL.

| Primitive | Actual operation | State/interface dependencies |
|---|---|---|
| FIELD_DECISION | Masked equality of a bounded field, acceptance/policy/readiness, role retention/fixed/field-bit selection; optional accepted low-byte enqueue | 16-bit pending field, accepted and desired-role bits; pre-edge FIFO state |
| DIRECTION_HANDOFF | Change ownership; RX releases, TX loads a queued byte and presents its first bit; optional registered timer request | Current/desired role, shared byte TX, drive bits; no implied response slot |
| BOUNDARY_RESPONSE | Emit constant or acceptance-derived bit, release, or capture a bit and branch on a separate completion event | Captured response and drive bits; independent trigger/completion selection |
| WAIT_POLICY | Wait for TX readiness, RX space, registered timer event or input level; optional hold request and resolved TX-bit validation | Desired role/hold, FIFO readiness, shared timer; no pulse-duration accumulator |

Each operation is describable without a protocol name, and its RTL behavior
matches that description. There is no fixed address width, ninth phase, per-byte
ACK obligation or word-TX special case inside these operations. The production
circuit has no protocol-name branches, dedicated transaction FSMs or legacy
fallback. Inherited two-wire framing and own-pad timing predicates remain
protocol-shaped integration support and are not claimed as arbitrary routing.

The table contains sixteen 64-bit entries and eight opcodes: shared RX/TX,
four operations, HALT and CONTINUE. HALT/CONTINUE are composition support, not
extra primitive types. Triggers are ALWAYS, rising, falling and registered
timer sample. CHAIN only follows ALWAYS successors; at most four distinct
entries execute per cycle. Revisit, fifth entry or conflicting FIFO/TX work is
fatal. Higher-priority framing/reset/disable/abort/watchdog/guardian rules apply.
Receive fields are 1–16 bits; byte FIFOs and byte TX storage remain unchanged.
Successive TX loads can continue without a response slot.

The version-2 host interface retains non-exchange controls, FIFO and status
addresses. Addresses 9/10 are retired, not translated; 21 identifies version 2,
22 controls generic transactions and 128–255 hold the table. Configuration is
writable only while disabled. See [host interface](../../docs/host-interface.md).

## E. I²C regression

[I²C evidence](i2c_logical.json): all 48 original cases, identical stimuli,
88,287 cycles of full v2 model/RTL comparison and legacy externally visible
equivalence. The original awkward cases/assertions remain: repeated START,
ACK policies, ninth clocks, pressure/starvation, simultaneous host decisions,
malformed clocks, reset/abort/timeout, first-bit mismatch and own-pad recovery.
Full-at-decision RX rejects despite a concurrent pop; empty-at-decision TX sees
a concurrent push on the next cycle.

Eight synthetic probes cover field lengths 1/8/9/16 in both orders (5,704 cycles).
They are not protocol users. The suite has 109 passing tests, including the
original 83 behavioral tests and new contract/oracle tests. Existing SPI, UART,
timed-stream, reference, host, FIFO concurrency and spacing RTL regressions pass.
Three runtime host tests pass, including I²C starvation/repeated START and
back-to-back Microwire. Lint is clean. Guardian combinational assertions pass;
watchdog limits 1–15 have a 24-step bounded proof, not an unbounded theorem.

Fast CI is green for the frozen architecture at
[the freeze source](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38272001392).
Synthesis succeeds. [Corrections](corrections.json) distinguish ordinary model,
RTL, simulator and reporting defects from semantics; architectural semantic
changes after preregistration are empty. No I²C regression remains.

## F. Microwire result

The unchanged [93LC46 x16 READ source](https://ww1.microchip.com/downloads/en/devicedoc/21712B.pdf)
and historical command/word oracle still require A55A. V2 observes **A55A** in
1,970 matched model/RTL cycles. Independent checks cover active-high CS, dummy
zero, continuous sixteen-bit output, documented rising-edge advancement,
separate DI/DO and zero target clock-drive cycles. All data is preloaded.

The composition receives a nine-bit command, decides with mask/value, emits a
dummy zero, waits for readiness, hands off and transmits two successive FIFO
bytes. No Microwire RTL was added; all behavior uses the preregistered vocabulary.
Result: `MOTIF_EXCHANGE_DECOMPOSITION_I2C_MICROWIRE_REUSE_CONFIRMED`.
See [complete evidence](microwire_result.json).

## G. Frozen v2 architecture and accounting

Freeze commit `b5675757c7a8405fd8dd40168a2370b3edd69a65`, protecting the circuit
qualified at `f0da6a72cb62b6083196872e4f3f140cceb9135d`.
Manifest SHA-256 (LF normalized):
`9e95be597dbbab1fa267d5936b878386eedba972884acd8a8e5d653e22aadfd7`.
Canonical sorted RTL-inventory JSON SHA-256:
`c976575dc6ae6838340d616d3ef7050667cdcf4c95c896fa7297552594aa6678`.
Individual hashes/interfaces are in [the manifest](frozen_v2_manifest.json).
All model/RTL, host decoder, packing, routing, ownership, physical inputs and
generic trace compiler are protected. Before/after checks pass unchanged.

| Allocated item | Bits/capacity | Accounting treatment |
|---|---:|---|
| Primitive vocabulary | 10 types | Six established, four new; eight opcodes are a different count |
| Action table | 16 × 64 = 1024 bits | Configuration/control cost, counted once |
| Other configuration | 72 bits | Total configuration 1096 bits |
| Transaction registers | 28 bits | Includes PC 4, halted 1, pending field 16, seven one-bit fields; current-role diagnostic may optimize out |
| Shared RX / shared TX | 21 / 12 bits | RX widening and byte TX retained; counted once |
| Timer / watchdog / frontend / FIFOs | 26 / 17 / 26 / 82 bits | Support machinery, not primitive-local sums |
| Host SPI / lifecycle/provenance/diagnostics / host diagnostics | 47 / 23 / 2 bits | Support costs |
| Total declared registers including configuration | 1380 bits | Distinct from 1385 technology-mapped sequential cells |
| Immediate action bound | 4 entries/cycle | Separate from primitive-type firings |

[Final accounting](final_accounting.json) reports configured dependencies,
registered PC observations, per-frame firings and active configuration/state
fields separately. Closed frame epochs include aborted and repeated-start
epochs; they are not all successful transactions. Immediate chained entries
can be invisible in registered PC observations. Logical interface groups are
not physical wire counts or arbitrary programmable routes; state dependencies
are not power/activity measurements.

| Training workload | Event interface groups | Data interface groups | Observed max primitive types/cycle | New RTL relative to implemented v2 |
|---|---:|---:|---:|---:|
| I²C | 11 | 9 | 4 | 0 |
| Microwire READ | 8 | 7 | 3 | 0 |
| SPI target | 7 | 6 | 3 | 0 |
| UART RX | 5 | 5 | 2 | 0 |
| Timed stream | 5 | 4 | 2 | 0 |

Group counts include possible immediate-chain dependencies, not proof that every
alternate branch fired. Per Microwire transaction, firings are acquire 1,
release 1, reset-count 2, RX 9, TX 16, decision 1, handoff 2, response 1, wait 1,
timer 0. Across 444 closed I²C frame epochs, ranges are RX 0–48, TX 0–27,
decision 0–6, handoff 0–5, response 0–12, wait 0–434 and timer 0–3.
Zero new protocol-specific transaction modules/lines were added. This count
does not erase inherited two-wire framing/provenance logic in `motif_core.sv`
or the separate diagnostic sequential SPI reference.

I²C references 27 transaction-state bits and Microwire 25, excluding the
diagnostic current-role bit and unused capture/hold state; all 28 are allocated
globally. SPI/UART/timed-stream use no transaction program state. Their receive
dependency is 11 bits within the globally allocated 21-bit RX group; SPI also
uses the 12-bit TX group, while UART/timed-stream use the 26-bit timer. Frontend,
FIFO, watchdog (when enabled), framing and host support costs remain shared.
All modes still allocate the complete 1096-bit global configuration bank.
Per example frame, SPI fires RX 8 and TX 9 (including load), UART fires RX 8
and timer 10, and timed stream fires RX 8 and timer 8; each has acquire 1,
release 1 and reset-count 2. These examples are checked against historical
recipe counts in the current model and complement the retained RTL regressions.

## H. Unseen protocol

[Candidate matrix and rationale](third_selection.md) compare 1-Wire, PS/2,
ISO7816 T=0 and Microchip SWI primary documentation. Selection commit `4959350`
follows the freeze, and precedes configuration/oracle commit `e525af4`.
The selected [workload](third_workload.json) is only reset/presence initialization,
with continuous reset low ≥480 µs, release-relative delay 15–60 µs and target
low 60–240 µs. The 960 µs upper bound is experimental, not a normative maximum.
No complete 1-Wire device or data exchange is claimed.

Three passive input routes observe the same wired-AND DQ; only one open-drain
output can drive. No synthetic clock, pulse-qualifying wrapper or active host
sequencing is used. Four FF FIFO tokens preload timer-handoff support. The
[configuration](configurations/one_wire_reset_presence.json) and independent
controller/measurement oracle are outside the frozen implementation boundary.

| Case | Independent oracle | Model/RTL agreement |
|---|---|---|
| Nominal 500 µs reset | Pass | Exact |
| Shortest legal 480 µs | Pass | Exact |
| Longest bounded 960 µs | Pass | Exact |
| Back-to-back resets | Pass | Exact |
| Unusual legal long idle / 700 µs reset | Pass | Exact |
| Short 100 µs non-reset pulse | Pass: silence | Exact |
| 200 µs low, 1 µs high, 300 µs low | **Fail: false presence** | Exact |
| System reset during qualification | Pass: silence | Exact |
| Configured watchdog abort | Pass: timeout and silence | Exact |

All 1,302,050 cycles agree. The false presence starts at 1524.94 µs and lasts
119.86 µs despite neither continuous controller low reaching 480 µs. The high
gap is detected by the frontend but missed between timer field samples. The
single active instruction cannot simultaneously restart/reject an elapsed-low
qualification. Source inspection identifies one missing generic responsibility:
continuous input-level duration qualification with interruption handling.
No new operation was implemented. [Analysis](third_analysis.md),
[result/hashes](third_result.json) and [counterexample windows](third_counterexample.json)
preserve the negative. The malformed-input silence requirement was committed
before implementation and is stronger than the source's legal timing description;
it is not a claim about undefined silicon behavior. This is a bounded attempted
composition plus source diagnosis, not an exhaustive search proof over all tables.

## I. Physical qualification

**NOT_REACHED for v2.** Third-workload logical qualification failed. V2 placement,
utilization, setup/hold WNS/TNS, wirelength, vias, overflow, routed/Magic DRC,
LVS, official precheck and routed-netlist host tests have no results. Missing
measurements are not zeros. No optimization or constraints change was performed.

V2 [typical-library synthesis](synthesis.json) reports 12,546 cells,
1,385 sequential cells and 194,376.3318 µm². Generic mapping reports 19,228 cells.
The mapped library hash matches the earlier mapped report. These results exclude
placement, timing and routing. The historical 3,209-cell, 47,805.8 µm² routed
I²C circuit remains valid for its source, not this repaired circuit.

## J. Semantic reuse table

Only independently qualified bounded users receive a checkmark.

| Primitive | SPI | UART RX | Timed stream | I²C | Microwire READ | Unseen |
|---|---|---|---|---|---|---|
| FRAME_ACQUIRE | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| FRAME_RELEASE | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| RESET_COUNTER | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| SHIFT_RX_COUNT | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| SHIFT_TX | ✓ | — | — | ✓ | ✓ | — |
| TIMED_SAMPLE | — | ✓ | ✓ | ✓ | — | — |
| FIELD_DECISION | — | — | — | ✓ | ✓ | — |
| DIRECTION_HANDOFF | — | — | — | ✓ | ✓ | — |
| BOUNDARY_RESPONSE | — | — | — | ✓ | ✓ | — |
| WAIT_POLICY | — | — | — | ✓ | ✓ | — |

Validated configuration-only users: five. Training I²C and Microwire influenced
the decomposition; their reuse is confirmed, but is weaker evidence than an
unseen success. Failed attempts and synthetic probes are excluded. Existing
SPI/UART/timed-stream recipes remain non-transaction modes. Their allocated
support machinery is still counted; unused table state is not an area saving.

## K. Architecture comparison

| Property | Legacy BYTE_EXCHANGE | Decomposed v2 |
|---|---:|---:|
| Primitive types | 7 | 10 |
| Transaction state | 18 bits | 28 bits |
| Configuration | 78 bits | 1096 bits, including 1024 table bits |
| I²C qualified | Yes | Yes, identical legacy stimuli/visible behavior |
| Frozen Microwire oracle | A5FF, fails | A55A, passes |
| Unseen workload | Not reached | PARTIAL, interrupted-pulse failure |
| Protocol-specific transaction assumptions | Fixed address/direction and ACK phases | None inside the four operations; inherited framing/timer routes remain limited |
| Validated config-only users | 4 | 5 |
| Typical mapped cell area | 35,976.6792 µm² | 194,376.3318 µm² |
| Mapped sequential cells | 347 | 1385 |
| Routed qualification | Historical source passes | Not reached |

Mapped area grows about 5.40× and sequential cells about 3.99×. This is a visible
cost of configuration and bounded sequencing, not an established efficiency
advantage. Declared state, mapped sequential cells and routed register counts
are different measurements. No matched new reference or PPA study was run.

## L. Negative evidence

The six legacy Microwire failures, mandatory ACK counterexample, implementation
correction record, unseen interrupted-pulse failure and missing v2 physical
results are retained. Successful legal presence timing does not erase failure
of the precommitted malformed contract. No workload switching, oracle relaxation,
second semantic repair or post-result refreeze occurred.

## M. Evidence strength

The four operations demonstrate reuse across two training workloads. The frozen
unseen attempt establishes a temporal limit, so unrestricted generalization and
physical implementability of this enlarged circuit remain unconfirmed.

## N. Recommended next actions

1. Close this campaign with its PARTIAL result and immutable evidence.
2. If continuing research, preregister a separate duration-qualification study
   with a fresh independent workload before adding semantics or optimizing PPA.

## Reproduction

```sh
python -m pytest -q
python -m tools.generalization --gate 2 --baseline legacy
python -m tools.generalization --gate 1 --baseline v2
python -m tools.generalization --gate 2 --baseline v2
python -m tools.generalization --gate 3 --baseline v2
python -m tools.unseen_result
python -m tools.exchange_decomposition --check-preregistration
python -m tools.exchange_decomposition --check-freeze
python -m tools.accounting
python -m tools.campaign_report
python -m tools.rtl_check
python -m tools.formal_check
python -m tools.synthesis --cmos5l --output-dir build/exchange_decomposition/current_synthesis
```

Negative-result reproduction is a passing regression when it matches the
committed failure; the independent protocol oracle continues to report failure.
Text hashes normalize CRLF to LF. Generated vectors, full traces, simulator logs
and physical tool installations stay in ignored build output. CI retains trace
artifacts for 14 days; committed inputs and hashes support later regeneration.
