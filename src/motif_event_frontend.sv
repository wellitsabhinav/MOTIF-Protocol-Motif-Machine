`default_nettype none
module motif_event_frontend (
    input wire clk, rst_n,
    input wire [7:0] pins_i,
    output wire [7:0] levels_o, rising_o, falling_o,
    output wire valid_o
);
    reg [7:0] first, second, previous;
    reg [1:0] warmup;
    always @(posedge clk) begin
        if (!rst_n) begin
            first <= 8'hff; second <= 8'hff; previous <= 8'hff; warmup <= 0;
        end else begin
            first <= pins_i; second <= first; previous <= second;
            if (warmup != 2) warmup <= warmup + 1'b1;
        end
    end
    assign levels_o = second;
    assign valid_o = warmup == 2;
    assign rising_o = valid_o ? second & ~previous : 8'b0;
    assign falling_o = valid_o ? previous & ~second : 8'b0;
endmodule
