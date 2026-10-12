`default_nettype none
module motif_reference_top (
    input wire [7:0] ui_in,uio_in,
    output wire [7:0] uo_out,uio_out,uio_oe,
    input wire ena,clk,rst_n
);
    tt_um_wellitsabhinav_motif #(.REFERENCE(1)) reference_engine(ui_in,uio_in,uo_out,uio_out,uio_oe,ena,clk,rst_n);
endmodule
