`default_nettype none
module motif_timed_sample (
    input wire clk, rst_n, clear_i, start_i, bit_i, validate_start_i, validate_stop_i,
    input wire [15:0] period_i,
    output reg [2:0] event_o,
    output reg sampled_bit_o
);
    reg running;
    reg [1:0] phase;
    reg [15:0] left;
    reg [2:0] samples;
    always @(posedge clk) begin
        event_o <= 0;
        if (!rst_n) begin running <= 0; phase <= 0; left <= 0; samples <= 0; sampled_bit_o <= 0; end
        else if (start_i) begin
            running <= 1; samples <= 0;
            phase <= validate_start_i ? 0 : 1;
            left <= validate_start_i ? period_i >> 1 : period_i;
        end else if (clear_i) running <= 0;
        else if (running) begin
            if (left > 1) left <= left - 1'b1;
            else begin
                left <= period_i;
                sampled_bit_o <= bit_i;
                case (phase)
                    0: begin
                        if (bit_i) begin event_o <= 2; running <= 0; end
                        else begin event_o <= 1; phase <= 1; end
                    end
                    1: begin
                        event_o <= 3; samples <= samples + 1'b1;
                        if (samples == 7 && validate_stop_i) phase <= 2;
                    end
                    2: begin event_o <= bit_i ? 4 : 5; running <= 0; end
                    default: running <= 0;
                endcase
            end
        end
    end
endmodule
