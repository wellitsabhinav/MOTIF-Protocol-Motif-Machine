# Congestion and physical plausibility

Attempt 2's raw global-routing log reports total overflow 7,782, including
Metal3 7,655 at 90.15% resource use. It nevertheless completed detailed routing
with zero recorded routing DRC, Magic DRC, LVS and antenna violations. Core
area is 902,417.242 µm². Final standard-cell area is 263,349.27 µm²,
29.18% core utilization, 20,178 standard cells and 1,401 sequential cells.
Low overall utilization therefore does not establish local routability or timing.
Cell-count tables include physical-only fillers separately; the raw final
Verilog parser's 82,276 instances must not be called functional logic cells.

Attempt 3's decoded terminal log records synthesis/floorplan cell area
235,561.74 µm² and 17,195 cells. After post-CTS repair: 305,701.0 µm² and
22,984 cells. Global route reports Metal3 demand 249,764 against 194,422
resources (128.46%) and overflow 70,660; total overflow 71,352. That is
9.1688 times attempt 2's total overflow, under changed mapping. The final
observed partial detailed-route violation count is 270,448 before cancellation;
it is **not final DRC**. The official six-hour annotation establishes the limit.

Attempt 2 already fails pre-layout with ideal wires. Routing is consequently
not the origin of this failure. It raises net delay and slew/loading penalties,
and timing repair increases local routing demand. The attempt-3 comparison
supports an interaction between mapping, buffering and congestion; it cannot
isolate the causal effect of each setting or prove an inevitable routing failure.

No new physical run was launched. P2's timing kernel is promising but has a
demonstrated atomicity defect; P3/P4 have no completed mapping measurement. None
passes the study's combined semantic/synthesis gate for routing. Placing the
known defective P2 cut would consume compute without qualifying the specified
replacement. Physical plausibility rests on its large timing/area/depth margins,
not on a new post-placement, CTS, route or GDS result.
