`default_nettype none
// Faithful RTL promotion of motif/motifs/exchange.py, not a generic sequencer.
module motif_byte_exchange (
    input wire clk, rst_n, clear_i, run_i, rising_i, falling_i, bit_i, lsb_i,
    input wire [6:0] address_i,
    input wire ack_address_i, ack_data_i, transmit_i,
    input wire [7:0] rx_next_i, tx_value_i, tx_head_i,
    input wire [2:0] rx_count_i,
    input wire [3:0] tx_remaining_i,
    input wire rx_full_i, tx_empty_i, settled_i, settled_bit_i,
    output reg rx_fire_o, tx_fire_o, tx_load_o, rx_push_o,
    output wire [7:0] rx_data_o,
    output reg turnaround_o,
    output wire mismatch_o,
    output reg drive_low_o, stretch_o,
    output reg [3:0] phase_o
);
    localparam RX=0, DECIDE=1, ACK_SETUP=2, ACK_HOLD=3, TX=4,
               CONTROLLER_ACK=5, STRETCH=6, SETTLE=7, IDLE=8;
    reg header, next_role, ack, controller_ack;
    reg [7:0] pending_byte;
    reg [3:0] phase_next;
    reg header_next, role_next, ack_next, controller_next, drive_next, stretch_next;
    reg [7:0] pending_next;
    reg prepare_tx;
    wire tx_bit = lsb_i ? tx_value_i[0] : tx_value_i[7];
    assign mismatch_o = run_i && phase_o == SETTLE && settled_i && settled_bit_i != tx_bit;
    assign rx_data_o = pending_byte;
    always @* begin
        phase_next=phase_o; header_next=header; role_next=next_role;
        ack_next=ack; controller_next=controller_ack;
        drive_next=drive_low_o; stretch_next=stretch_o; pending_next=pending_byte;
        rx_fire_o=0; tx_fire_o=0; tx_load_o=0; rx_push_o=0; turnaround_o=0; prepare_tx=0;
        if (run_i && !clear_i) begin
            case (phase_o)
                STRETCH: if (!tx_empty_i) prepare_tx=1;
                SETTLE: if (settled_i) begin
                    phase_next=settled_bit_i == tx_bit ? TX : IDLE;
                    stretch_next=0;
                    if (settled_bit_i != tx_bit) drive_next=0;
                end
                RX: if (rising_i) begin
                    rx_fire_o=1;
                    if (rx_count_i == 7) begin pending_next=rx_next_i; phase_next=DECIDE; end
                end
                DECIDE: begin
                    if (header) begin
                        ack_next=pending_byte[7:1] == address_i && ack_address_i && (transmit_i || !pending_byte[0]);
                        role_next=pending_byte[0]; header_next=0;
                    end else begin
                        ack_next=ack_data_i && !rx_full_i;
                        rx_push_o=ack_data_i && !rx_full_i;
                    end
                    phase_next=ACK_SETUP;
                end
                ACK_SETUP: if (falling_i) begin drive_next=ack; phase_next=ACK_HOLD; end
                ACK_HOLD: if (falling_i) begin
                    drive_next=0;
                    if (!ack) phase_next=IDLE;
                    else if (next_role) prepare_tx=1;
                    else phase_next=RX;
                end
                TX: if (falling_i) begin
                    tx_fire_o=1;
                    if (tx_remaining_i == 1) begin
                        phase_next=CONTROLLER_ACK; drive_next=0; controller_next=0;
                    end else drive_next=!(lsb_i ? tx_value_i[1] : tx_value_i[6]);
                end
                CONTROLLER_ACK: begin
                    if (rising_i) controller_next=!bit_i;
                    else if (falling_i) begin
                        if (controller_ack) prepare_tx=1;
                        else phase_next=IDLE;
                    end
                end
                default: begin end
            endcase
            if (prepare_tx) begin
                stretch_next=1;
                if (tx_empty_i) begin phase_next=STRETCH; drive_next=0; end
                else begin
                    tx_load_o=1; phase_next=SETTLE;
                    drive_next=!(lsb_i ? tx_head_i[0] : tx_head_i[7]);
                    turnaround_o=1;
                end
            end
        end
    end
    always @(posedge clk) begin
        if (!rst_n || clear_i) begin
            phase_o<=RX; header<=1; next_role<=0; ack<=0; controller_ack<=0;
            pending_byte<=0; drive_low_o<=0; stretch_o<=0;
        end else begin
            phase_o<=phase_next; header<=header_next; next_role<=role_next; ack<=ack_next;
            controller_ack<=controller_next; pending_byte<=pending_next;
            drive_low_o<=drive_next; stretch_o<=stretch_next;
        end
    end
    wire _unused = &{tx_value_i[5:2],tx_head_i[6:1],1'b0};
endmodule
