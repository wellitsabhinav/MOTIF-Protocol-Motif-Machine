module guardian_properties;
    (* anyconst *) reg [7:0] request_data,request_oe,ownership,open_drain,conflict;
    (* anyconst *) reg reset_n,release_frame,fatal;
    wire [7:0] data,oe;
    wire [2:0] violations;
    motif_pad_guardian guardian(request_data,request_oe,ownership,open_drain,conflict,
                                 !reset_n || release_frame,fatal,data,oe,violations);
    always @* begin
        assert((oe & ~ownership)==0);
        assert((oe & open_drain & data)==0);
        assert((oe & open_drain & request_data)==0);
        assert((oe & conflict)==0);
        assert((data & ~oe)==0);
        if(!reset_n || release_frame || fatal)assert(oe==0 && data==0);
    end
endmodule
