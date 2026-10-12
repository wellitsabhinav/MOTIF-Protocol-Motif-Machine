`default_nettype none
module motif_shift_rx_count #(parameter WIDTH=8, COUNT_WIDTH=3) (
    input wire clk, rst_n, clear_i, fire_i, bit_i, lsb_i,
    output reg [WIDTH-1:0] value_o,
    output reg [COUNT_WIDTH-1:0] count_o,
    output wire [WIDTH-1:0] next_value_o,
    output wire terminal_o,
    output reg complete_o,
    input wire external_i, external_complete_i,
    input wire [WIDTH-1:0] external_value_i,
    input wire [COUNT_WIDTH-1:0] external_count_i
);
    assign next_value_o = lsb_i ? (value_o >> 1) | (WIDTH'(bit_i) << 7) :
                                ((value_o << 1) | WIDTH'(bit_i)) & WIDTH'(255);
    assign terminal_o = fire_i && (external_i ? external_complete_i : count_o == 7) && !clear_i;
    always @(posedge clk) begin
        complete_o <= 1'b0;
        if (!rst_n || clear_i) begin value_o <= 0; count_o <= 0; end
        else if (fire_i) begin
            value_o <= external_i ? external_value_i : next_value_o;
            count_o <= external_i ? external_count_i : COUNT_WIDTH'(count_o[2:0] + 3'd1);
            complete_o <= external_i ? external_complete_i : count_o == 7;
        end
    end
endmodule
