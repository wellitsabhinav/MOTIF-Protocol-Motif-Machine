`default_nettype none
module motif_watchdog (
    input wire clk, rst_n, active_i, acquire_i, progress_i, abort_i,
    input wire [15:0] limit_i,
    output reg tripped_o,
    output wire expire_o
);
    reg [15:0] age;
    assign expire_o = active_i && !acquire_i && !progress_i && limit_i != 0 && age >= limit_i - 1'b1;
    always @(posedge clk) begin
        if (!rst_n) begin age <= 0; tripped_o <= 0; end
        else begin
            if (acquire_i) begin age <= 0; tripped_o <= 0; end
            else if (!active_i || progress_i) age <= 0;
            else if (limit_i != 0 && age < limit_i) age <= age + 1'b1;
            if (abort_i || expire_o) tripped_o <= 1;
        end
    end
endmodule
