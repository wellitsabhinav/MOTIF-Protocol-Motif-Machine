# Protocol support

| Configuration | Model | RTL | Evidence |
|---|---|---|---|
| SPI target, mode 0, eight-bit MSB-first | yes | yes | Boundary/random model tests, cycle comparison and host-loaded RTL |
| UART receive, 8N1 | yes | yes | Model tests, bad stop/recovery, cycle comparison and host-loaded RTL |
| Externally framed timed byte stream | yes | yes | Configuration-only composition on unchanged shared RTL |
| I²C target, seven-bit RX/TX | yes | no | Address/data ACK/NACK, repeated START, stretching, abort/rearm, random traffic |

No other SPI modes, UART transmitter, analog electrical compliance or fabricated
silicon results are claimed.

I²C excludes ten-bit addressing, general call, controller operation and
multi-controller arbitration. A 100 kHz schedule at a nominal 50 MHz core is
tested, together with faster normalized cycle schedules. These tests do not
establish analog electrical compliance or silicon maximum frequency.
