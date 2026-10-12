`default_nettype none
module temporal_properties #(parameter THRESHOLD=3) (input wire clk);
    (* anyseq *) reg rst_n, clear, predicate_bit;
    wire [15:0] count;
    wire started, done;
    wire [3:0] pc;
    localparam [63:0] QUALIFIER=(64'(THRESHOLD)<<37) | (64'd4<<53) | (64'd3<<13) | (64'd1<<5) | (64'd15<<9) | 64'd4;
    motif_transaction dut(.clk(clk),.rst_n(rst_n),.clear_i(clear),.acquire_i(1'b0),.run_i(1'b1),
        .rising_i(1'b0),.falling_i(1'b0),.bit_i(predicate_bit),.lsb_i(1'b0),.transmit_i(1'b0),
        .program_i({{15{64'd6}},QUALIFIER}),.rx_value_i(16'd0),.rx_count_i(4'd0),
        .tx_value_i(8'd0),.tx_head_i(8'd0),.tx_remaining_i(4'd0),.rx_full_i(1'b0),.tx_empty_i(1'b1),
        .settled_i(1'b0),.settled_bit_i(1'b0),.pc_o(pc),.temporal_count_o(count),
        .temporal_started_o(started),.temporal_done_o(done));
    reg past_valid=0;
    always @(posedge clk)begin
        past_valid<=1;
        assert(count<=THRESHOLD);
        assert(!done || (started && count==THRESHOLD));
        assert(count==0 || started);
        if(past_valid)begin
            if($past(!rst_n || clear))assert(count==0 && !started && !done);
            if($past(rst_n && !clear && pc==0 && !done && predicate_bit))
                assert(count==0 && !started && !done);
            if($past(rst_n && !clear && pc==0 && !done && !predicate_bit))
                assert(count<=$past(count)+1);
            if($past(rst_n && !clear && done))assert(count==0 && !done);
        end
    end
endmodule
