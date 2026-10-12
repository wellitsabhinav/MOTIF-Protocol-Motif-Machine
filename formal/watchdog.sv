module watchdog_properties(input wire clk);
    (* anyconst *) reg [3:0] limit;
    reg initialized=0;
    reg [4:0] elapsed=0;
    wire tripped,expire;
    motif_watchdog watchdog(clk,initialized,1'b1,1'b0,1'b0,1'b0,{12'b0,limit},tripped,expire);
    always @(posedge clk) begin
        initialized<=1;
        if(elapsed<20)elapsed<=elapsed+1'b1;
    end
    always @* begin
        assume(limit!=0);
        if(elapsed>=16)assert(tripped);
    end
endmodule
