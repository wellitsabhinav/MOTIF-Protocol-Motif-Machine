# Protocol support

| Configuration | Model | RTL | Evidence |
|---|---|---|---|
| SPI target, mode 0, eight-bit MSB-first | yes | no | Boundary and 600 seeded full-duplex frames |
| UART receive, 8N1 | yes | no | Boundary values, bad stop, subsequent recovery |
| Externally framed timed byte stream | yes | no | Configuration composition test |
| I²C target, seven-bit RX/TX | yes | no | Address/data ACK/NACK, repeated START, stretching, abort/rearm, random traffic |

No other SPI modes, UART transmitter, analog electrical compliance or fabricated
silicon results are claimed.

I²C excludes ten-bit addressing, general call, controller operation and
multi-controller arbitration. A 100 kHz schedule at a nominal 50 MHz core is
tested, together with faster normalized cycle schedules. These tests do not
establish analog electrical compliance or silicon maximum frequency.
