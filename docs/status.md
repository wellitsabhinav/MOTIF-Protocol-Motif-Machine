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
