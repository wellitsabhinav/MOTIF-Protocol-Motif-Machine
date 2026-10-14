# Critical paths

[Timing table](timing_table.md) and `evidence/{pre,post}_*_paths.json` contain
the worst twenty reported setup paths **per corner per stage**, 120 paths in
total. Each records start/end state names, arrival/required/slack, incremental
data delay, cell/buffer/mapped-mux counts, maximum path fanout, source hierarchy,
named-net-supported functional categories and a cell-type histogram. The report
may contain more paths; selected paths are sorted by slack. All selected paths
are in the `clk` group; semantic endpoint families are more useful than this
single clock-group label.

Typical pre-layout launches from `core.exchange.pc_o[0]` and reaches receive
assembly (`core.exchange.rx_value_i[9]` is the synthesis alias of the shared
RX state), at 48.400967 ns arrival and −28.746559 ns slack. Its wire arcs are
zero. Slow pre-layout reaches `temporal_done_o`, 76.338318 ns arrival and
−56.760189 ns slack. This does not prove that temporal state creates the
problem: the input cone includes the interpreter's table and continuation logic.

Post-route typical/slow launch from table bit 928: entry 14, raw word bit 32,
VALUE bit 11. The destination is RX FIFO word 3 bits 1/3 respectively.
Typical data increments sum to 29.275279 ns: 26.063588 cell and 3.211693
net/input arcs. Slow sums to 46.118392 ns: 43.600155 and 2.518237 ns. Clock
latency and external input budgets are excluded from those incremental sums.
Arrival times and WNS therefore are not simply `20 - data delay`.

The paths contain 63/62 non-buffer combinational gates, plus 31/30 buffers.
The earlier report's 64/63 non-buffer *output-cell* arcs included launch Q;
this study consistently excludes the launch flop from combinational depth.
Cell-delay fractions are approximately 89.0% and 94.5%. Cell delays depend on
loading/slew, so they are not all immutable intrinsic gate delay.

The structural classification is table/configuration → executor/control →
FIFO decision/data. Named intermediate predicates and temporal logic are recorded
when present. Opcode and exact unrolled-stage attribution is **unknown** where
ABC removed the names; Boolean-decomposed muxes are not counted as mux cells.
No decorative cell-to-source attribution is invented.

The new common-buffer, zero-wire v3 slow analysis still fails. Even after
excluding static configuration launches and frontend warmup **for diagnosis
only**, PC → RX FIFO takes 23.858648 ns and has −4.285170 ns slack across 64
non-buffer gates. This rejects an explanation based only on startup/reset/static
configuration constraints. Those diagnostic launch filters do not change the
full-top acceptance result. Reproduce selected-launch queries with
`tournament.py`'s exported netlists and the source signal/driver identities in
`v3_pc_slow_paths.json` and `v3_steady_slow_paths.json`.
