`default_nettype none
module motif_shift_rx_count (
    input wire clk, rst_n, clear_i, fire_i, bit_i, lsb_i,
    output reg [7:0] value_o,
    output reg [2:0] count_o,
    output wire [7:0] next_value_o,
    output wire terminal_o,
    output reg complete_o
);
    assign next_value_o = lsb_i ? {bit_i, value_o[7:1]} : {value_o[6:0], bit_i};
    assign terminal_o = fire_i && count_o == 7 && !clear_i;
    always @(posedge clk) begin
        complete_o <= 1'b0;
        if (!rst_n || clear_i) begin value_o <= 0; count_o <= 0; end
        else if (fire_i) begin
            value_o <= next_value_o;
            count_o <= count_o + 1'b1;
            complete_o <= count_o == 7;
        end
    end
endmodule
