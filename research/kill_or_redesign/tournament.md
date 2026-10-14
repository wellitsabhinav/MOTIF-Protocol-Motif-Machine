| Variant | Area µm² | Δ area vs v3 | Worst delay ns | WNS ns | Logic depth | Max fanout | Critical path type | Extra state | Latency change |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| v2 | 194376.3318 | -7.5464% | 21.101425 | -5.527946 | 60 | 8 | ena → core.rx_fifo.memory[1][0] | -18 | historical |
| v3 | 210241.9746 | +0.0000% | 21.295191 | -5.721711 | 65 | 8 | ena → core.rx_fifo.memory[1][0] | +0 | 0 |
| elided | 200468.4444 | -4.6487% | 22.430523 | -6.857043 | 63 | 8 | ena → core.rx_fifo.memory[1][0] | -18 | temporal absent |
| state_clamp | 203209.8516 | -3.3448% | 22.102160 | -6.528680 | 60 | 8 | ena → core.rx_fifo.memory[1][0] | -18 | temporal absent |
| p1 | 217871.1486 | +3.6288% | 20.699827 | -5.126348 | 65 | 8 | ena → core.rx_fifo.memory[1][0] | +64 | cache alignment pending |
| p2 | 155669.5098 | -25.9570% | 5.748525 | +9.824954 | 27 | 8 | ena → core.tx_fifo.memory[1][0] | +66 | chains spread across cycles |
| p3 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | mapping timeout | 9 | FIFO +1 cycle |
| p4 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | mapping timeout | 0 | 0; exact relation proved |

Area is raw matched mapping, before fixed buffers. Timing is slow PVT, the worst
**constrained setup** path after the common fixed tree. Its data delay excludes
the 4 ns external input budget; a register-launched path can have a longer data
delay but better slack. No waived input/configuration/reset path is used.
Graph-wide depth/mux maxima differ from depth on the worst timed path.
P3/P4's timeouts are missing measurements, not evidence of bad timing.
