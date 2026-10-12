# Historical CMOS5L subset qualification

This page preserves the original SPI/UART/timed-stream measurements. The
[expanded I²C qualification](generalization.md) has separate measurements and
passes the same pinned official flow, precheck and routed-netlist tests.

The manually dispatched `gds` workflow uses the pinned official Tiny Tapeout
CMOS5L flow for a 6×4 design at an internal 50 MHz target. It builds GDS, runs
the official precheck and gate-level host test, and checks the datasheet.
Versions and process revision are recorded in `flow-lock.json`.

This historical RTL scope is SPI target, UART receive and the timed-stream example.
I²C was model-only in that build. A successful subset build cannot establish complete
multi-protocol physical qualification. Physical artifacts are workflow outputs,
not tracked source files or local PDK installations.

`python -m tools.synthesis --cmos5l` maps the current source using the pinned
1.20 V, 25 °C library and writes ignored `build/synthesis/current` output. Use
`--output-dir` to retain a separate current report. Reproduce the historical
subset comparison by checking out its recorded revision first; the command no
longer overwrites historical checked-in reports. It publishes cell area,
sequential/combinational area, register count, mux cells and hierarchy. These
mapped results exclude placement, CTS, routing and timing. Host/configuration,
core control, timers, protection, FIFOs and shifters are reported separately;
the numbers do not establish a general architecture advantage.

The historical typical mapping reports 1,736 cells and 30,430.0962 µm² for MOTIF,
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

The [completed corrected build](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38218975479)
reports 2,641 standard cells, 308 sequential cells and 40,546.4 µm² standard-cell
area after placement, CTS and timing repair. Utilization is 4.493% of the
902,417 µm² core; the 6×4 allocation has not been reduced or optimized.
Timing-repair buffers account for 8,883.3 µm², including 476 hold buffers.
This routed result is separate from the nominal hierarchy comparison above.

| STA corner | Worst setup slack (ns) | Worst hold slack (ns) |
|---|---:|---:|
| Fast, 1.32 V, −40 °C | +10.2543 | +0.1269 |
| Typical, 1.20 V, 25 °C | +9.4339 | +0.3124 |
| Slow, 1.08 V, 125 °C | +8.0293 | +0.6478 |

Setup/hold WNS and TNS are zero at all three corners under the official template
constraints. The first reported worst setup path is reset input to guarded
`uio_out[7]`; the constraints assign 4 ns external input/output delays. These
results do not establish a maximum external protocol clock or silicon frequency.

Detailed routing uses 84,540 µm of wire and 15,564 vias. Global routing has zero
overflow; average derated-resource demand is 2.23%, mostly Metal3 (63% of demand)
and Metal2 (36%). Placement weighted congestion is 0.7942. The layout preview
shows active circuitry concentrated in one corner of the allocation. Average
layer utilization does not bound every local route concentration.

Detailed-route DRC, Magic DRC and LVS report zero errors. Residual reports include
19 max-fanout violations, with zero max-slew/capacitance violations. The template
uses fallback SDC; its build-time KLayout DRC step is disabled. The official
precheck separately ran KLayout DRC and passed. The original workflow retains its failed gate-job
history; the successful linked gate retest supersedes that simulation-tool failure.

The [Linux gate retest](https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/38224260567)
passes the host-loaded SPI/UART/timed-stream test against this routed artifact.
The original gate job failed on PDK simulation-model setup. Adding primitive
models repaired elaboration; removing timing-check blocks from the functional
copy repaired reset-time unknown values in Icarus 13. The retest verifies physical
source equality before using the existing artifact; RTL was unchanged by that repair.
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
The manually dispatched `ci` workflow can retest an existing layout artifact
when its optional `build_run_id` input is supplied. It first verifies that
synthesizable sources,
flow configuration, tile description and version lock match the completed build.
