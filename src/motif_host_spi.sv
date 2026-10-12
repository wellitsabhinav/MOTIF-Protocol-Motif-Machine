`default_nettype none
module motif_host_spi (
    input wire clk, rst_n, sclk_i, cs_n_i, mosi_i,
    input wire [7:0] read_data_i,
    output reg miso_o, write_o, read_o,
    output reg [7:0] address_o,
    output wire [7:0] write_data_o
);
    reg [2:0] first, second;
    reg previous;
    reg [7:0] receive, command;
    reg [6:0] transmit;
    reg [4:0] count;
    wire rising = second[0] && !previous;
    wire falling = !second[0] && previous;
    wire [7:0] shifted = {receive[6:0], second[2]};
    assign write_data_o = receive[7:0];
    always @(posedge clk) begin
        write_o <= 0; read_o <= 0;
        if (!rst_n) begin
            first <= 3'b010; second <= 3'b010; previous <= 0;
            receive <= 0; transmit <= 0; command <= 0; count <= 0; address_o <= 0; miso_o <= 0;
        end else begin
            first <= {mosi_i, cs_n_i, sclk_i}; second <= first; previous <= second[0];
            if (second[1]) begin count <= 0; receive <= 0; miso_o <= 0; end
            else begin
                if (rising && count < 24) begin
                    receive <= shifted; count <= count + 1'b1;
                    if (count == 7) command <= shifted[7:0];
                    if (count == 15) address_o <= shifted[7:0];
                    if (count == 23) begin write_o <= command == 2; read_o <= command == 1; end
                end
                if (falling) begin
                    if (count == 16) begin transmit <= read_data_i[6:0]; miso_o <= read_data_i[7]; end
                    else if (count > 16 && count < 24) begin
                        transmit <= {transmit[5:0], 1'b0}; miso_o <= transmit[6];
                    end
                end
            end
        end
    end
endmodule
