# Logic depth and cones

[Controlled graph table](logic_depth_table.md) reports v2/v3, temporal controls
and the completed probes. Graph analysis follows actual connectivity, resolves
Yosys net aliases, stops at sequential Q/input boundaries and rejects
combinational cycles. Depth is a maximum topological gate count, not STA slack
or a sensitizable functional path proof. Buffers are excluded from logic depth;
mapped mux depth counts mux2/mux4 cells only, not equivalent AOI/OAI networks.

Actual attempt-2 synthesis has maximum 65 logic levels and 12 mapped mux levels;
final physical netlist has 66 and 12. This flow synthesized after flattening.
The matched qualification recipe maps **hierarchically**, then flattens for STA:
v2/v3 maxima are 79/81, with 27/21 mapped mux levels. These are different
netlists/recipes, not inconsistent measurements of the same graph. Their
individual hashes are in the receipts.

Major cones are tabulated in `*_graph.json`: each of the twenty deepest endpoint
cones has cell count, boundary-source count, named source examples and hierarchy.
They reach RX/TX FIFO memory/control, receive assembly, transaction state and
host/configuration response/control. Shared cones overlap and cannot be summed
as a hierarchy-area decomposition. Host readback and configuration validation
remain large wrapper responsibilities; their mapped v3 area is 103,246.6932 µm²
(49.11%). Transaction is 79,695.4788 µm² (37.91%); FIFO module is 3,518.1216 µm²
**per instance**, two instances in the top. Other module areas are in mapping
receipts; module-local area excludes child instances.

P2 reduces graph depth to 41 and mux depth to eight, and transaction mapping
to 25,146.6768 µm² / 1,271 cells from 79,695.4788 / 5,517. The unchanged wrapper
still costs 103,246.6932 µm². This localizes the benefit to the execution cone
rather than erasing the host, table storage or generic programmability.
