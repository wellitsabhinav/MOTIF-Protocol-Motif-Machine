# Status

Current coverage: M0/M1 digital model behavior is qualified; integrated
SPI/UART/timed-stream RTL is qualified; early CMOS5L physical checks pass for that
subset. The suite has 78 model/control-boundary tests, the existing 34,351 subset
comparison cycles, and 88,287 I²C model/RTL cycles. The I²C RTL promotion is
logically qualified; its expanded physical qualification is in progress. No
general cost advantage or unseen-protocol generalization is established.

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
CMOS5L qualification is running; BYTE_EXCHANGE reuse is not yet established.
