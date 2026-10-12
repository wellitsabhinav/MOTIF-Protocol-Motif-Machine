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
formal proofs, synthesis and physical qualification are future milestones. No
formal result is implied by simulation. Heavy physical jobs will be manually
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
Configuration and pad-request validation reject values without bounded encodings.
