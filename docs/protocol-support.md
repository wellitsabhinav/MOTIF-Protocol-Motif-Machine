# Protocol support

| Configuration | Model | RTL | Evidence |
|---|---|---|---|
| SPI target, mode 0, eight-bit MSB-first | yes | no | Boundary and 600 seeded full-duplex frames |
| UART receive, 8N1 | yes | no | Boundary values, bad stop, subsequent recovery |
| Externally framed timed byte stream | yes | no | Configuration composition test |
| I²C target | planned | no | Not yet qualified |

No other SPI modes, UART transmitter, analog electrical compliance or fabricated
silicon results are claimed.
