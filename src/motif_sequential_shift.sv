`default_nettype none
module motif_sequential_shift (
    input wire clk,rst_n,rx_clear_i,tx_clear_i,rx_fire_i,tx_fire_i,tx_load_i,bit_i,lsb_i,
    input wire [7:0] load_data_i,
    output reg [7:0] rx_value_o,tx_value_o,
    output reg [2:0] rx_count_o,
    output reg [3:0] remaining_o,
    output wire [7:0] rx_next_o,
    output wire rx_terminal_o,tx_terminal_o,tx_bit_o,
    output reg rx_complete_o,collision_o
);
    // Comparison datapath: one shared shift path and one issue per cycle.
    wire [7:0] operand = rx_fire_i ? rx_value_o : tx_value_o;
    wire incoming = rx_fire_i && bit_i;
    wire [7:0] shifted = lsb_i ? {incoming,operand[7:1]} : {operand[6:0],incoming};
    assign rx_next_o = shifted;
    assign rx_terminal_o = rx_fire_i && rx_count_o==7 && !rx_clear_i;
    assign tx_terminal_o = tx_fire_i && remaining_o==1 && !tx_clear_i && !rx_fire_i;
    assign tx_bit_o = lsb_i ? tx_value_o[0] : tx_value_o[7];
    always @(posedge clk) begin
        rx_complete_o<=0;
        if(!rst_n)begin
            rx_value_o<=0;tx_value_o<=0;rx_count_o<=0;remaining_o<=0;collision_o<=0;
        end else begin
            if(rx_clear_i)begin rx_value_o<=0;rx_count_o<=0;end
            else if(rx_fire_i)begin
                rx_value_o<=shifted;rx_count_o<=rx_count_o+1'b1;rx_complete_o<=rx_count_o==7;
            end
            if(tx_clear_i)begin tx_value_o<=0;remaining_o<=0;end
            else if(!rx_fire_i)begin
                if(tx_load_i)begin tx_value_o<=load_data_i;remaining_o<=8;end
                else if(tx_fire_i && remaining_o!=0)begin tx_value_o<=shifted;remaining_o<=remaining_o-1'b1;end
            end
            if(rx_fire_i && (tx_fire_i || tx_load_i))collision_o<=1;
        end
    end
endmodule
