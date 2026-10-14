MOTIF_REDESIGN

## 1. Executive decision

Replace MOTIF's direct four-action table-to-side-effect execution with registered
predecode, one generic operation per clock and atomic side-effect commit. Keep
the programmable vocabulary; stop trying to close the current execution path by
changing flow settings.

The failure precedes routing. Attempt 2's typical pre-layout arrival is
48.400967 ns; its final typical/slow WNS is −9.764565/−26.751381 ns. Under a
common optimistic fanout-eight tree and zero-wire model, even the continuing
v3 PC path still violates slow timing by 4.285170 ns. Frozen v2 has essentially
the same problem; temporal elision does not rescue it.

The P2 registered-predecode/serial-execution kernel retains the table and generic
opcodes, reduces raw mapped area by 25.956979%, and reaches +9.824954 ns slow
full-top WNS. It passes selected independent Microwire, 1-Wire and LIN checks and
a closed-loop nominal I²C transaction. This is substantial evidence for a bounded
architectural escape, sufficient to reject killing the programmable concept now.

P2 also fails a generic atomic-termination counterexample. The recommended
replacement therefore includes explicit event snapshots, bounded chain tracking,
deferred FIFO/pad commit and a continuously clocked temporal observer; it is not
the measured P2 cut shipped unchanged. Its allocated additional state is 160
bits, with no new configuration bits.

The study ends here. No new physical job was justified by a fully correct probe;
MOTIF remains physically unqualified. Redesign is a recommendation supported by
a measured kernel and an explicit implementation contract, not a claim of ASIC
closure or completed production RTL.

## 2. Root cause

Four dependent indirect table reads, operand/predicate decisions and action/fault
reconvergence occur between the same pair of register edges. Global validity,
lifecycle and watchdog control are distributed through this execution before
distant FIFO capture. The final paths have 63/62 non-buffer gates, and
89.0%/94.5% cell-arc delay at typical/slow PVT. Fanout, mapping and congestion
amplify the structure; they are not sufficient explanations for its origin.
See [critical paths](critical_path_analysis.md), [depth](logic_depth_analysis.md)
and [bottlenecks](architecture_bottlenecks.md).

## 3. Evidence

- Authenticated raw attempt-2 archive; 120 selected pre/post setup paths and
  twenty ranked high-fanout nets at each stage, with source/measurement hashes.
- Exact reproduced frozen mapped areas: v2 194,376.3318 and v3 210,241.9746 µm².
  The official +8.1623327% temporal cost result remains valid.
- Slow common-buffer WNS: v2 −5.527946, v3 −5.721711, temporal elision
  −6.857043, state clamp −6.528680 ns. No temporal-removal rescue.
- P2 raw area 155,669.5098 µm²; 9,086 cells / 1,468 FFs; buffered ideal-wire
  area 178,051.9482 µm²; slow register-launched worst slack +10.680643 ns.
  Graph maximum depth falls 81 → 41; mapped mux maximum 21 → 8.
- Closed-loop P2 I²C: 4,154 cycles, four ACKs, RX 55 AA, TX A5 5A, repeated
  START, controller NACK and final release. Selected Microwire A55A, three
  1-Wire wire cases and nominal LIN pass. SPI/UART/timed-stream fixed actor
  traces remain equal. This is a bounded plausibility check, not full regression.
- Atomic negative: two generic entries leave RX occupancy 1 in P2 versus 0
  in frozen v3. P4's complete transition relation is proved equivalent, but
  P3/P4 have no timing/area result after 180-second mapping limits.

Receipts: [tournament](evidence/tournament.json), [semantic checks](evidence/p2_semantic_sanity.json),
[live I²C](evidence/p2_i2c_live.json), [P4 proof](evidence/p4_equivalence.json),
[input identity](evidence/input_identity.json).

## 4. Hypotheses falsified

H6 as the dominant cause is rejected: v2 and both temporal-removal controls fail.
H5 as a routing-only origin is rejected by raw ideal-wire pre-PNR failure.
H4 as a fanout-only explanation is rejected by fixed-load PC-path failure.
H1 cannot justify KEEP: known flow revisions did not qualify the design, and
ideal bounded fanout still fails. This does **not** prove that every possible
synthesis recipe/constraint formulation is incapable of improving it.
H2/H3 are strongly supported by P2's timing and localized transaction-area
reduction. H7, that generic programmability necessarily costs too much, is not
supported: P2 keeps the vocabulary/table and is smaller. [Full dispositions](hypotheses.md).

## 5. Current architecture assessment

The fixed programmable responsibilities have demonstrated bounded logical
generalization. The implementation's single-cycle chaining/control arrangement
is structurally poor for the chosen physical target. The evidence distinguishes
that arrangement from the temporal abstraction and from table storage itself.
Neither universal protocol coverage nor universal physical impossibility is
claimed. Existing formal/oracle results remain research assets, not an ASIC pass.

## 6. Rescue experiment results

See the complete [comparison table](tournament.md). Raw mapped area is compared
on one recipe; typical/slow timing is compared both raw and with identical fixed
buffers. No favorable variant is substituted into the official frozen results.
P1 changes little; P2 removes the dependent execution repetitions; P3/P4 are
incomplete measurements. No combinations were run.

| Variant | Area µm² | Δ area vs v3 | Worst delay ns | WNS ns | Logic depth | Max fanout | Critical path type | Extra state | Latency change |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| v2 | 194376.3318 | -7.5464% | 21.101425 | -5.527946 | 60 | 8 | ena → core.rx_fifo.memory[1][0] | -18 | historical |
| v3 | 210241.9746 | +0.0000% | 21.295191 | -5.721711 | 65 | 8 | ena → core.rx_fifo.memory[1][0] | +0 | 0 |
| elided | 200468.4444 | -4.6487% | 22.430523 | -6.857043 | 63 | 8 | ena → core.rx_fifo.memory[1][0] | -18 | temporal absent |
| state_clamp | 203209.8516 | -3.3448% | 22.102160 | -6.528680 | 60 | 8 | ena → core.rx_fifo.memory[1][0] | -18 | temporal absent |
| p1 | 217871.1486 | +3.6288% | 20.699827 | -5.126348 | 65 | 8 | ena → core.rx_fifo.memory[1][0] | +64 | cache alignment pending |
| p2 | 155669.5098 | -25.9570% | 5.748525 | +9.824954 | 27 | 8 | ena → core.tx_fifo.memory[1][0] | +66 | chains spread across cycles |
| p3 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | mapping timeout | 9 | FIFO +1 cycle |
| p4 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | mapping timeout | 0 | 0; exact relation proved |

Area is raw matched mapping, before fixed buffers. Timing is slow PVT, the worst
**constrained setup** path after the common fixed tree. Its data delay excludes
the 4 ns external input budget; a register-launched path can have a longer data
delay but better slack. No waived input/configuration/reset path is used.
Graph-wide depth/mux maxima differ from depth on the worst timed path.
P3/P4's timeouts are missing measurements, not evidence of bad timing.

## 7. Physical plausibility

P2 has meaningful slow-corner margin without wire RC, and much less execution
logic and buffering demand. Its buffered area is already 15.310942% below frozen
raw v3. The remaining specified registers have an estimated 4,604.9472 µm²
cell cost, leaving substantial room for shallow commit/control logic under the
10% preferred cap of 231,266.1721 µm² (15% hard cap 241,778.2708).
This is an inference; clock tree, real wire/slew, placement and congestion are
unmeasured for the replacement. Arbitrary buffer grouping is optimistic.

No defective probe was routed. Attempt 3 shows why a timing-driven netlist can
become congested even at low nominal utilization. The next separate redesign
must keep these numerical caps and terminate physical work by global route if
placement/CTS timing or overflow is unhealthy. [Physical analysis](congestion_analysis.md).

## 8. Competition value

If starting today, **we would not choose the current four-action architecture**.
We would choose a small registered programmable serial engine, retaining useful
compound field, handoff, response and temporal operations only behind bounded
execution/commit stages. This offers a clear demonstration and verification
story while preserving post-fabrication configuration for UART, SPI, I²C and
bounded stretch responsibilities. Separate protocol-specific RTL is rejected.

The [official competition announcement](https://blog.janestreet.com/protocol-emulator-asic-competition/)
requires a programmable open-source emulator, starts with UART/SPI/I²C, and uses
the current 6×4 CMOS5L allocation. It does not mandate MOTIF's 50 MHz target.
We retain 20 ns as the fixed study gate. Novelty matters only alongside physical
implementation and demonstrable verification. Commit count, past effort and
attachment to the project play no role in this choice.

[RP2040's primary datasheet, section 3.2.2](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf)
describes deterministic sequential PIO instruction execution and explicit stalls.
It supports the structural idea of bounded per-instruction work; it supplies no
CMOS5L timing or area guarantee for MOTIF. No competing project's README is used
as physical evidence.

## 9. Recommended action

Adopt the **F/E/C microarchitecture with a resident temporal observer** specified
in [candidate_redesigns.md](candidate_redesigns.md). Keep 16×64 external table
semantics and the eight protocol-neutral operations. Add the 66-bit µop register,
event snapshots, four-entry visited/action accounting and deferred atomic
FIFO/pad/timer commit. Keep the guardian independent. Version the changed
latency/arrival contract; do not claim binary cycle compatibility.

Permit one separately scoped implementation of this exact replacement, with
<=160 added allocated state bits, zero configuration growth, <=10% preferred /
<=15% hard mapped-area growth, clean or demonstrably small slow-corner synthesis
violation, and all original temporal/1-Wire/LIN/I²C/Microwire/SPI/UART acceptance
cases. A naked P2 cut cannot satisfy that gate. If the integrated design breaches
those caps or still routes pathologically, stop MOTIF as a competition entry;
do not reopen a flow-knob campaign. No implementation or physical continuation
is performed in this study.
