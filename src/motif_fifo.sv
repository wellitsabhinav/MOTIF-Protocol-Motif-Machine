`default_nettype none
module motif_fifo (
    input wire clk, rst_n, push_i, pop_i,
    input wire [7:0] data_i,
    output wire [7:0] data_o,
    output reg [2:0] count_o,
    output wire full_o, empty_o,
    output reg overflow_o, underflow_o
);
    reg [7:0] memory [0:3];
    reg [1:0] read_ptr, write_ptr;
    wire pop = pop_i && !empty_o;
    wire push = push_i && (!full_o || pop);
    assign full_o = count_o == 4;
    assign empty_o = count_o == 0;
    assign data_o = empty_o ? 8'b0 : memory[read_ptr];
    always @(posedge clk) begin
        if (!rst_n) begin
            count_o <= 0; read_ptr <= 0; write_ptr <= 0; overflow_o <= 0; underflow_o <= 0;
        end else begin
            if (push) begin memory[write_ptr] <= data_i; write_ptr <= write_ptr + 1'b1; end
            if (pop) read_ptr <= read_ptr + 1'b1;
            case ({push, pop})
                2'b10: count_o <= count_o + 1'b1;
                2'b01: count_o <= count_o - 1'b1;
                default: count_o <= count_o;
            endcase
            if (push_i && !push) overflow_o <= 1;
            if (pop_i && !pop) underflow_o <= 1;
        end
    end
endmodule
