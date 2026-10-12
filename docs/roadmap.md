# Roadmap

- M0 complete: executable model, SPI target, UART receive, framing and guardian tests.
- M1 digital gate complete: I²C target behavior, motif accounting and a limited sequential reference.
- M2 subset complete: RTL core and model correspondence for integrated SPI/UART/timed-stream operation.
- Early M3 subset complete: connected synthesis, routed timing, layout checks and functional gate simulation.
- M4: further protocol RTL coverage and complete submission integration.

The controlled v2 decomposition campaign stops at PARTIAL: I²C and Microwire
reuse is confirmed, but unseen continuous duration qualification fails. The
frozen circuit receives no second semantic repair or physical optimization in
this campaign. Any subsequent architecture research requires a new preregistered
experiment and independent workload; current v2 routed qualification is not reached.
