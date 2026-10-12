# Protocol support

| Configuration | Model | RTL | Evidence |
|---|---|---|---|
| SPI target, mode 0, eight-bit MSB-first | yes | yes | Boundary/random model tests, cycle comparison and host-loaded RTL |
| UART receive, 8N1 | yes | yes | Model tests, bad stop/recovery, cycle comparison and host-loaded RTL |
| Externally framed timed byte stream | yes | yes | Configuration-only composition on unchanged shared RTL |
| I²C target, seven-bit RX/TX | yes | yes | V2: 48 cases, 88,287 cycles, legacy visible equivalence and runtime host testing |
| Microwire 93LC46 x16 READ at address zero | yes | yes | V2: unchanged A55A oracle, dummy zero, continuous output, active-high CS, controller-only clock |
| 1-Wire reset/presence initialization | partial | partial | Frozen v2: eight of nine cases; interrupted short lows cause false presence |

No other SPI modes, UART transmitter, analog electrical compliance or fabricated
silicon results are claimed.

Historical versions of the first three configurations pass routed simulation,
50 MHz STA, DRC/LVS and official precheck. The earlier BYTE_EXCHANGE circuit
also physically qualifies I²C, then fails Microwire with A5FF. Those results do
not qualify v2. The repaired circuit has synthesis evidence; its unseen failure
stops the physical gate. See [historical results](generalization.md) and the
[v2 report](../experiments/exchange_decomposition/report.md).

Microwire scope is one preloaded bounded READ; EEPROM storage/programming and
analog compliance are excluded. The unseen subset excludes ROM commands,
search, temperature data and complete 1-Wire transactions. Its malformed-input
silence contract was committed before implementation; unspecified DS18B20 silicon
behavior is not inferred. It is excluded from validated-user counts.

I²C excludes ten-bit addressing, general call, controller operation and
multi-controller arbitration. A 100 kHz schedule at a nominal 50 MHz core is
tested, together with faster normalized cycle schedules. These tests do not
establish analog electrical compliance or silicon maximum frequency.
