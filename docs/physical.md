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

The MOTIF hierarchy has the following typical-corner cell areas. The two FIFO
instances are included; module-local glue is separate from child modules.

| Component | Cell area (µm²) |
|---|---:|
| RX/TX shifters and counts | 2,315.0988 |
| Event frontend | 1,756.3392 |
| Two four-byte FIFOs | 7,036.2432 |
| Dedicated host SPI | 3,759.4368 |
| Pad guardian and watchdog | 3,129.3108 |
| Timed sampling | 3,152.8980 |
| Core selection/control glue | 2,828.6118 |
| Configuration/top-level glue | 6,452.1576 |

Core selection, timed control and configuration/top-level glue occupy about 41%
of this mapping; the shifters occupy about 8%. These groups include required
configuration and connected routing, rather than isolated actor estimates.

Initial placement/routing qualification is in progress. Routed timing,
congestion and precheck outcomes will be recorded after the workflow completes.
The first completed layout passed DRC/LVS and precheck. Gate-level elaboration
required adding the pinned PDK's `sg13cmos5l_udp.v` primitive models to the test
source list. A later ownership correction supersedes that RTL snapshot; the
current source requires a new physical run before qualification.
The pinned CMOS5L cells use delayed timing-check wires that Icarus does not
drive. `tools/prepare_gate_models.py` generates an ignored functional copy with
those wires connected to the corresponding ports, preserving PDK attribution
and logic. Timing-check specify blocks are removed from that functional copy
to prevent simulator-dependent bidirectional port coercion. Gate tests are
zero-delay functional simulation; extracted timing
is qualified separately by the flow's STA reports.

After downloading the workflow's `GDS_logs` artifact to ignored build output,
`python -m tools.physical_report <run-directory> --run-id <id> --source-sha <sha>`
extracts the compact report. Supply the directory containing `final/metrics.json`.
It separates standard-cell area from the full tile and filler area, reports
corner slacks, checks and routing layers, and records the qualified source.
The manually dispatched `gate-test` workflow can retest an existing layout
artifact after test-tool repairs. It first verifies that synthesizable sources,
flow configuration, tile description and version lock match the completed build.
