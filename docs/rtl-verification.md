# RTL verification and comparison

`python -m tools.rtl_check` generates identical model/RTL stimuli in ignored
build output. It checks 2,000 RX/TX primitive vectors (seed 322), 4,000 guardian
vectors (seed 141), and cycle traces for SPI (5,401 cycles, seed 117), UART
(2,568 cycles) and a timed stream (276 cycles). Both the compound datapath and
single-issue reference receive the same integration traces. A pin-level host test
loads all three configurations into unchanged RTL and exchanges FIFO data.

`python -m tools.formal_check` proves six guardian combinational assertions for
unrestricted request/ownership/mode/conflict inputs. Reset, frame release and
fatal suppression are modeled by the guardian's trusted kill inputs. The proof
does not establish that an arbitrary source of ownership is itself trustworthy.
The top-level framing path is separately exercised by simulation.

The watchdog result is a 24-step bounded proof with stable nonzero limits 1..15,
continuous active framing and no progress/reset after initialization. It is not
an unbounded liveness proof for all sixteen-bit limits. The first harness run
failed because SAT assumptions were not enabled; enabling the harness assumptions
resolved that tooling issue without changing the watchdog implementation.

The RTL reference shares one shift datapath between RX and TX and can issue only
one shift/load per cycle. It retains competent fused receive/count and automatic
FIFO enqueue. Clock-driven SPI edges cannot request RX and TX shifts together;
the tested receive-only timed mappings also avoid collisions. Other mixed timed
RX/TX configurations can collide and are outside its qualified coverage. A
collision reports status. Host, frontend, FIFOs, configuration and guardian are
identical between RTL variants. The RTL reference improves on the initial Python
reference's separate FIFO operation; no enqueue latency advantage is claimed
against this refined reference.

The pinned OSS CAD Suite performs lint, bare RTL simulation and formal checks.
Cocotb uses Python 3.11, cocotb 2.0.1 and Tiny Tapeout's Icarus 13.0 package,
matching the official gate-test tooling. The suite's bundled development cocotb
and simulator passed assertions but crashed at shutdown, so they are not used
for cocotb qualification.

`python -m tools.synthesis` reproduces generic Boolean cell counts by hierarchy.
These counts are not technology area or timing. The current local result has 1,467
compound-design cells and 1,455 reference cells. That small difference and equal
tested throughput do not establish an implementation advantage. CMOS5L mapping
and placement/routing are a separate qualification step. I²C remains model-only.

Additional qualification checks 1,200 randomized FIFO transactions (seed 73),
including reset, simultaneous push/pop, full and empty conditions. A 5,525-cycle
SPI trace with a 32-cycle watchdog confirms timeout suppression and rearm only
after a fresh frame edge. Total integration comparisons now cover 22,015 cycles,
in addition to primitive vectors and the host transactions.

A concurrent host/protocol test reproduces an empty-read race: a byte arriving
after the read snapshot was previously consumed without being returned. The
host now captures data validity with the response and commits a FIFO pop only
for a valid snapshot. The test confirms the late byte is retained for the next
read in both RTL variants. The cocotb version exercises the same case.
Host tests also load an output assignment that aliases the framing input and
confirm released pads with a retained guardian fault in both RTL variants.
