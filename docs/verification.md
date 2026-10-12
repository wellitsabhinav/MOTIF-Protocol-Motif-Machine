# Verification

Run `python -m pip install -e '.[test]'` and `python -m pytest -q` from the repository
root. Python 3.11 or later is supported. Tests operate wires through the frontend,
not through protocol-specific receive shortcuts.

SPI seeds are 7, 41 and 20261012, with 200 frames per seed. Assertion failures
report the seed and frame index. Guardian randomized requests use seed 141 and
5,000 requests. Directed tests cover raw deselection with stale OE, conflicting
owners, open-drain requests, timeout, partial-frame abort, FIFO bounds, reset,
UART stop failure and recovery without reset.

CI installs the package and runs the same tests. RTL differential verification,
formal proof coverage and synthesis are recorded separately in
`rtl-verification.md`; physical coverage is recorded in `physical.md`. No
formal result is implied by simulation. Heavy physical jobs are manually
dispatched. Generated runs, traces and waveforms remain untracked.

I²C random seeds are 19 and 20261012, with 80 write/read transaction pairs per
seed. The independent controller resolves both parties' open-drain requests.
Directed tests cover header/data NACK, controller ACK/NACK, repeated START,
mid-address and mid-data termination, reset, FIFO pressure, stretching, long
controller-low waits, timeout and subsequent recovery. The sequential SPI
reference uses seed 908 and 150 additional equivalent full-duplex frames.

`python -m tools.accounting` reproduces the public bounded-encoding estimates
and firing counts. Estimates are not allocated RTL storage or synthesized area.
The sequential reference covers SPI only and uses fused sample/shift/count. It
executes 19 operations for one complete eight-bit frame, including two TX loads
and one FIFO enqueue. At the tested spacing both architectures sustain identical
wire throughput; the reference enqueues a completed RX byte one cycle later.
These results do not establish a multi-protocol area or throughput advantage.

The current accounting deduplicates byte-exchange suboperations into one motif
firing per type per cycle. It includes address-constant matching and UART byte
validation storage in byte routes and lists host FIFO routes separately. Named
model event-interface groups are not physical wire or selector counts. Per-motif
metadata identifies shared storage/configuration groups so they are not summed
twice. RTL mux cells and hierarchy area provide separate implementation evidence.
The union of defined model mappings provisions 18 named event-interface groups,
seven byte connections and two host connections. Active mappings use 5..8 event
groups and 1..4 byte connections. These estimates are not physical routing counts.
Configuration and pad-request validation reject values without bounded encodings.
Clock-stretch tests keep controller SCL released high as TX data becomes ready,
then verify target-held low through setup for both first-bit values. The earlier
test pulled controller SCL low again and missed premature target release. The
corrected mapping reuses timed sampling for the setup interval and reruns the
full suite with an independent controller that honors stretched clock periods.
The current suite has 73 tests. Adversarial requests also cover receive-only
ownership, aliased target outputs, delayed self-generated START after abort,
own clock truncation and own SDA activity attempting to postpone timeout.
The sequential SPI reference now also passes the same reset, partial-abort,
completed-RX/queued-TX preservation, watchdog and fresh-frame rearm contract.
SPI boundary patterns additionally compare both models at two, three and four
cycles per fixture phase, with MOSI setup, clock high and clock low held in
separate phases. This exercises synchronization and spacing boundaries.
