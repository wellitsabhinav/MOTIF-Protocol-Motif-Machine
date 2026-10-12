`default_nettype none
module motif_pad_guardian (
    input wire [7:0] request_data_i, request_oe_i, ownership_i, open_drain_i, conflict_i,
    input wire kill_i, fatal_i,
    output wire [7:0] data_o, oe_o,
    output wire [2:0] violation_o
);
    // Only this block can authorize final pad output-enable.
    assign oe_o = request_oe_i & ownership_i & ~conflict_i &
                  ~(open_drain_i & request_data_i) & {8{!kill_i && !fatal_i}};
    assign data_o = request_data_i & oe_o & ~open_drain_i;
    assign violation_o[0] = !kill_i && !fatal_i && |(request_oe_i & ~ownership_i);
    assign violation_o[1] = |(request_oe_i & open_drain_i & request_data_i);
    assign violation_o[2] = |(request_oe_i & conflict_i);
endmodule
