`default_nettype none
module motif_core #(parameter REFERENCE=0) (
    input wire clk, rst_n, enable_i, abort_i,
    input wire [7:0] pins_i,
    input wire frame_falling_i, timer_mode_i, transmit_i, lsb_i, validate_start_i, validate_stop_i,
    input wire [2:0] frame_pin_i, clock_pin_i, rx_pin_i, tx_pin_i,
    input wire [15:0] period_i, watchdog_i,
    input wire [7:0] fill_i, open_drain_i,
    input wire host_tx_push_i, host_rx_pop_i,
    input wire [7:0] host_tx_data_i,
    output wire [7:0] host_rx_data_o, pad_data_o, pad_oe_o,
    output wire [2:0] rx_fifo_count_o, tx_fifo_count_o,
    output wire [7:0] status_o,
    output reg active_o,
    output wire [7:0] rx_value_o,
    output wire [2:0] rx_count_o
);
    wire [7:0] levels, rising, falling;
    wire valid;
    motif_event_frontend frontend(clk, rst_n, pins_i, levels, rising, falling, valid);
    wire release_event = active_o && !frame_falling_i && levels[frame_pin_i];
    wire acquire = valid && !active_o && falling[frame_pin_i];
    wire progress = rising[rx_pin_i] || falling[rx_pin_i] ||
                    rising[frame_pin_i] || falling[frame_pin_i] ||
                    (!timer_mode_i && (rising[clock_pin_i] || falling[clock_pin_i]));
    wire tripped, expire;
    motif_watchdog watchdog(clk, rst_n, active_o, acquire, progress, abort_i, watchdog_i, tripped, expire);
    wire [2:0] timer_event;
    wire timer_bit;
    wire end_sample = timer_event == 2 || timer_event == 4 || timer_event == 5;
    wire inhibit = !enable_i || abort_i || release_event || (tripped && !acquire) || expire;
    wire clear = inhibit || acquire || end_sample;
    motif_timed_sample timer(clk, rst_n, inhibit || end_sample, acquire && !inhibit && enable_i && timer_mode_i,
                            levels[rx_pin_i], validate_start_i, validate_stop_i, period_i, timer_event, timer_bit);
    wire rx_fire = active_o && !clear && (timer_mode_i ? timer_event == 3 : rising[clock_pin_i]);
    wire [7:0] rx_next;
    wire rx_terminal, rx_complete;
    wire tx_fire = active_o && !clear && transmit_i && falling[clock_pin_i];
    wire [7:0] tx_value, tx_head;
    wire [3:0] tx_remaining;
    wire tx_bit, tx_terminal, tx_empty, tx_full;
    wire tx_load = enable_i && !inhibit && transmit_i && (acquire || tx_terminal);
    wire collision;
    generate if(REFERENCE)begin: sequential
        motif_sequential_shift shifts(clk,rst_n,clear,inhibit || end_sample,rx_fire,tx_fire,tx_load,
            timer_mode_i ? timer_bit : levels[rx_pin_i],lsb_i,tx_empty ? fill_i : tx_head,
            rx_value_o,tx_value,rx_count_o,tx_remaining,rx_next,rx_terminal,tx_terminal,tx_bit,rx_complete,collision);
    end else begin: compound
        motif_shift_rx_count rx(clk,rst_n,clear,rx_fire,timer_mode_i ? timer_bit : levels[rx_pin_i],
                                lsb_i,rx_value_o,rx_count_o,rx_next,rx_terminal,rx_complete);
        motif_shift_tx tx(clk,rst_n,inhibit || end_sample,tx_load,tx_fire,lsb_i,
                          tx_empty ? fill_i : tx_head,tx_value,tx_remaining,tx_bit,tx_terminal);
        assign collision=0;
    end endgenerate
    wire tx_overflow, tx_underflow, rx_full, rx_empty, rx_overflow, rx_underflow;
    motif_fifo tx_fifo(clk, rst_n, host_tx_push_i, tx_load && !tx_empty, host_tx_data_i,
                       tx_head, tx_fifo_count_o, tx_full, tx_empty, tx_overflow, tx_underflow);
    reg [7:0] validated_byte;
    wire rx_push = enable_i && !inhibit && ((rx_terminal && !validate_stop_i) || (active_o && timer_event == 4));
    motif_fifo rx_fifo(clk, rst_n, rx_push, host_rx_pop_i,
                       validate_stop_i ? validated_byte : rx_next, host_rx_data_o,
                       rx_fifo_count_o, rx_full, rx_empty, rx_overflow, rx_underflow);
    reg framing_error, fill_underflow, timeout_status;
    always @(posedge clk) begin
        if (!rst_n) begin
            active_o <= 0; validated_byte <= 0; framing_error <= 0; fill_underflow <= 0; timeout_status <= 0;
        end else begin
            if (inhibit || end_sample) active_o <= 0;
            else if (acquire) active_o <= 1;
            if (rx_terminal) validated_byte <= rx_next;
            if (timer_event == 2 || timer_event == 5) framing_error <= 1;
            if (tx_load && tx_empty) fill_underflow <= 1;
            if (expire) timeout_status <= 1;
        end
    end
    wire [7:0] requests = active_o && transmit_i ? (8'b1 << tx_pin_i) : 8'b0;
    wire [7:0] requested_data = tx_bit ? requests : 8'b0;
    wire [7:0] ownership = active_o ? (8'b1 << tx_pin_i) : 8'b0;
    wire raw_kill = !rst_n || !enable_i || abort_i || (!frame_falling_i && pins_i[frame_pin_i]);
    wire [2:0] violations;
    motif_pad_guardian guardian(requested_data, requests, ownership, open_drain_i, 8'b0,
                                raw_kill, tripped, pad_data_o, pad_oe_o, violations);
    reg guard_fault;
    always @(posedge clk) begin
        if(!rst_n)guard_fault<=0;
        else if(|violations)guard_fault<=1;
    end
    assign status_o = {collision, timeout_status, framing_error, fill_underflow, rx_overflow,
                       tx_overflow, rx_underflow, guard_fault};
    wire _unused = &{rx_complete, tx_value, tx_remaining, tx_full, tx_underflow, rx_full, rx_empty, 1'b0};
endmodule
