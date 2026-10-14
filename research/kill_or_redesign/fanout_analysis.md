# Fanout and control distribution

[Pre-layout ranking](pre_fanout.md) and [post-route ranking](post_fanout.md)
each identify twenty nets. Machine records include driver, sink examples/types,
distinct cell count, buffer sinks, predecessor cone and named-source categories.
Fanout is input-pin count; constant ties, power and clocks are excluded.
Propagation delay is not a property of fanout count alone; path receipts supply
measured cell/net delay where the net is on a selected STA path. A net ranking
does not assign a fabricated startpoint/endpoint or nanosecond delay to every net.

Attempt-2 pre-layout maximum is 922, from `_14990_/Y` on `_06437_`, with reset
as its named boundary source. Other nets have 474/473 loads and PC decode on the
typical worst path has 197 loads. Large root and table-selector loads amplify
cell delay well before placement. Post-route maximum nonclock fanout is 13;
buffering has already reduced distribution cost, yet slow WNS is −26.75 ns.

The matched hierarchical v3 raw netlist has maximum live nonclock fanout 1,220
on reset. Its PC bit 0 drives 274 pins. The common fanout-eight experiment adds
2,619 buf_4 cells and 38,015.3088 µm², +18.0817% versus frozen raw area.
P2 needs 1,542 such buffers / 22,382.4384 µm². These arbitrary balanced trees
are an optimistic circuit test, not a placed buffering solution. Constants and
ideal clocks are outside the tree. Actual post-route buffer topology is retained
in the archive; no geometric wire-length reduction is inferred from this probe.

Distribution is a material amplifier, but even with bounded loads and zero RC,
v3's continuing PC execution path violates slow timing by 4.285170 ns. P1
registers an initial read but leaves this multi-action control cone. P4 moves
global qualification to commit and proves equivalent; its missing mapping result
prevents a quantitative timing claim. See the timeouts in experiments.md.
