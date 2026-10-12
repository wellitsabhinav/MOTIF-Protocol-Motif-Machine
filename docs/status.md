# Status

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

2026-10-12 — The model suite passes 70 tests. I²C stretched-clock setup now uses
the shared timer and samples resolved SDA before release. Guarded drive history
rejects delayed self-generated START and detects own clock/data timing faults.
Only external SCL activity resets an enabled I²C inactivity watchdog. RTL output
ownership requires transmit enable and a separate output pin. The corrected
source passes native trace, host and lint checks; physical qualification is being
repeated because the previous completed layout used the earlier ownership rule.
