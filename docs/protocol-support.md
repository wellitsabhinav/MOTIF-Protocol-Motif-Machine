# Protocol support

| Configuration | Model | RTL | Evidence |
|---|---|---|---|
| SPI target, mode 0, eight-bit MSB-first | yes | yes | Boundary/random model tests, cycle comparison and host-loaded RTL |
| UART receive, 8N1 | yes | yes | Model tests, bad stop/recovery, cycle comparison and host-loaded RTL |
| Externally framed timed byte stream | yes | yes | Configuration-only composition on unchanged shared RTL |
| I²C target, seven-bit RX/TX | yes | yes | 48 cases, 88,287 model/RTL cycles, runtime host testing and qualified routed CMOS5L implementation |

No other SPI modes, UART transmitter, analog electrical compliance or fabricated
silicon results are claimed.

The first three RTL configurations also pass functional simulation of the routed
netlist. Their shared CMOS5L subset passes 50 MHz STA, DRC/LVS and official
precheck. Those historical measurements exclude I²C RTL and a routed sequential
reference. The expanded implementation also qualifies I²C with timing, DRC/LVS,
official precheck and routed-netlist host tests. See [the qualification and reuse
results](generalization.md). Bounded Microwire READ failed the frozen exchange
interface and is not supported; no unseen-protocol qualification is claimed.

I²C excludes ten-bit addressing, general call, controller operation and
multi-controller arbitration. A 100 kHz schedule at a nominal 50 MHz core is
tested, together with faster normalized cycle schedules. These tests do not
establish analog electrical compliance or silicon maximum frequency.
