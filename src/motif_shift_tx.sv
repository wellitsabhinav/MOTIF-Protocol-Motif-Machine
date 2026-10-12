`default_nettype none
module motif_shift_tx (
    input wire clk, rst_n, clear_i, load_i, fire_i, lsb_i,
    input wire [7:0] load_data_i,
    output reg [7:0] value_o,
    output reg [3:0] remaining_o,
    output wire bit_o,
    output wire terminal_o
);
    assign bit_o = lsb_i ? value_o[0] : value_o[7];
    assign terminal_o = fire_i && remaining_o == 1 && !clear_i;
    always @(posedge clk) begin
        if (!rst_n || clear_i) begin value_o <= 0; remaining_o <= 0; end
        else if (load_i) begin value_o <= load_data_i; remaining_o <= 8; end
        else if (fire_i && remaining_o != 0) begin
            value_o <= lsb_i ? {1'b0, value_o[7:1]} : {value_o[6:0], 1'b0};
            remaining_o <= remaining_o - 1'b1;
        end
    end
endmodule
