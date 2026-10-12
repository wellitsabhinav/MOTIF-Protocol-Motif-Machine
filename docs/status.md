# Status

Current v2 coverage: SPI/UART/timed-stream regressions pass; I²C retains 48 cases
and 88,287 cycles of legacy visible equivalence. Bounded Microwire READ returns
A55A through the four preregistered operations. The suite has 109 tests. Frozen
v2 matches model/RTL on 1,302,050 unseen initialization cycles but fails the
interrupted-short-pulse oracle: `MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL`.
The campaign stops without another repair. V2 synthesis passes; v2 physical
qualification is not reached. No general cost advantage or unrestricted protocol
generalization is established. The entries below preserve earlier scopes.

2026-10-12 — M0 executable model established. The suite independently verifies
shared SPI target and UART receive behavior, framing, compound receive/count,
transmit, and pad protection. The initial run passed 22 tests. I²C qualification
is the next implementation milestone. RTL and physical evidence remain pending.

2026-10-12 — I²C target model qualified for the documented seven-bit exchange
behaviors. Shared shifters and FIFOs support target receive/transmit, repeated
START, ninth-clock handoff, stretching and automatic framing recovery. A bounded
exchange actor was added. Motif accounting and a fixed SPI sequential reference
are reproducible. RTL correspondence and physical cost remain unqualified.

2026-10-12 — Integrated SPI/UART/timed-stream RTL matches model traces and passes
host-loaded configuration/data tests. The same traces qualify a shared-shift
single-issue reference. Guardian electrical properties have a complete
combinational proof; watchdog limits 1..15 have a 24-step bounded result.
Synthesis produces generic cell counts, without technology-area/timing claims.
A stale framing-level reacquisition bug was fixed and regression-tested.

2026-10-12 — Nominal CMOS5L mapping and a manually gated physical flow are
reproducible. Concurrent host/protocol
testing exposed an empty-read race; response validity is now captured with the
data so a late-arriving byte remains queued. The corrected RTL passes both
comparison variants and Linux CI. Physical qualification is in progress.

2026-10-12 — The model suite passes 73 tests. I²C stretched-clock setup now uses
the shared timer and samples resolved SDA before release. Guarded drive history
rejects delayed self-generated START and detects own clock/data timing faults.
Only external SCL activity resets an enabled I²C inactivity watchdog. RTL output
ownership requires transmit enable and a separate output pin. The corrected
source passes native trace, host and lint checks; physical qualification is being
repeated because the previous completed layout used the earlier ownership rule.

2026-10-12 — Corrected subset layout passes routed timing at 50 MHz, DRC/LVS and
official precheck. Routed standard-cell area is 40,546.4 µm²; worst setup/hold
slacks are +8.0293/+0.1269 ns. A simulation-only PDK adapter repair passes the
Linux gate retest against the same layout after checking physical source equality.
Nominal component comparison and routed measurements are published separately.
Residual max-fanout reports, timing-repair cost and I²C model-only coverage remain
explicit limitations. Submission and fabrication are future milestones.

2026-10-12 — The frozen-vocabulary campaign records an immutable initial
inventory and promotes the existing nine-phase I²C model into shared RTL.
Forty-eight deterministic cases cover exchange policies, causal protection,
FIFO timing and recovery without changing the independent model. A repeated
acquisition watchdog discrepancy was corrected in RTL. A declaration-order
compatibility repair passed Linux CI and was merged separately. Expanded
CMOS5L qualification passes synthesis/P&R, three-corner setup/hold timing,
routed/Magic DRC, LVS, official precheck and both routed-netlist host tests.
The promoted vocabulary and integration are frozen independently of the initial
inventory. Six framing/order configurations fail bounded Microwire READ; the
closest returns A5FF instead of A55A because controller ACK is mandatory after
eight TX bits. BYTE_EXCHANGE is classified as a protocol-specific macro. Gate 3
is unattempted under that historical campaign's stop condition; frozen sources are unchanged.

2026-10-12 — One controlled v2 decomposition separates field decision, direction
handoff, boundary response and waiting. Audit and immutable preregistration
precede the independent model and RTL. I²C retains legacy behavior and the unchanged
Microwire oracle passes. After freeze, a separately committed 1-Wire initialization
subset passes eight of nine cases. Timer fields miss a one-microsecond high
interruption and produce false presence. No frozen source changes; the PARTIAL
result stops the physical gate. See the
[decomposition report](../experiments/exchange_decomposition/report.md).
