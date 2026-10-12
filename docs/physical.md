# CMOS5L qualification

The manually dispatched `gds` workflow uses the pinned official Tiny Tapeout
CMOS5L flow for a 6×4 design at an internal 50 MHz target. It builds GDS, runs
the official precheck and gate-level host test, and checks the datasheet.
Versions and process revision are recorded in `flow-lock.json`.

The qualified RTL scope is SPI target, UART receive and the timed-stream example.
I²C remains model-only. A successful subset build cannot establish complete
multi-protocol physical qualification. Physical artifacts are workflow outputs,
not tracked source files or local PDK installations.

`python -m tools.synthesis --cmos5l` reproduces a small typical-corner mapping
comparison using the pinned 1.20 V, 25 °C library. It publishes cell area,
sequential/combinational area, register count, mux cells and hierarchy. These
mapped results exclude placement, CTS, routing and timing. Host/configuration,
core control, timers, protection, FIFOs and shifters are reported separately;
the numbers do not establish a general architecture advantage.

The current typical mapping reports 1,736 cells and 30,430.0962 µm² for MOTIF,
versus 1,721 cells and 30,508.4556 µm² for the reference. MOTIF has 309 registers,
67 configuration bits, 15,137.5392 µm² sequential area and 15,292.5570 µm²
combinational area. The small difference is not an established cost advantage.

Initial placement/routing qualification is in progress. Routed timing,
congestion and precheck outcomes will be recorded after the workflow completes.
The first completed layout passed DRC/LVS and precheck. Gate-level elaboration
required adding the pinned PDK's `sg13cmos5l_udp.v` primitive models to the test
source list. A later ownership correction supersedes that RTL snapshot; the
current source requires a new physical run before qualification.
The pinned CMOS5L cells use delayed timing-check wires that Icarus does not
drive. `tools/prepare_gate_models.py` generates an ignored functional copy with
those wires connected to the corresponding ports, preserving PDK attribution
and logic. Gate tests are zero-delay functional simulation; extracted timing
is qualified separately by the flow's STA reports.
