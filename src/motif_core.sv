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
    output wire [2:0] rx_count_o,
    input wire exchange_i, two_wire_i, frame_active_high_i, hold_clock_i, pad_timing_check_i,
    input wire [1023:0] program_i,
    output wire [2:0] exchange_status_o
);
    wire [7:0] levels, rising, falling;
    wire valid;
    motif_event_frontend frontend(clk, rst_n, pins_i, levels, rising, falling, valid);
    reg [1:0] own_first, own_second, own_previous;
    always @(posedge clk) begin
        if (!rst_n) begin own_first<=0; own_second<=0; own_previous<=0; end
        else begin
            own_first<={pad_oe_o[rx_pin_i],pad_oe_o[clock_pin_i]};
            own_second<=own_first; own_previous<=own_second;
        end
    end
    wire clock_stable_high = levels[clock_pin_i] && !rising[clock_pin_i];
    wire release_event = two_wire_i ? clock_stable_high && rising[rx_pin_i] :
                         active_o && !frame_falling_i && levels[frame_pin_i] != frame_active_high_i;
    wire acquire = valid && (two_wire_i ? clock_stable_high && falling[rx_pin_i] &&
                   !(own_second[1] || own_previous[1]) : !active_o && (frame_active_high_i && !frame_falling_i ? rising[frame_pin_i] : falling[frame_pin_i]));
    wire pin_progress = rising[rx_pin_i] || falling[rx_pin_i] ||
                    rising[frame_pin_i] || falling[frame_pin_i] ||
                    (!timer_mode_i && (rising[clock_pin_i] || falling[clock_pin_i]));
    wire progress = exchange_i ? (rising[clock_pin_i] || falling[clock_pin_i]) &&
                    !(own_second[0] || own_previous[0]) : pin_progress;
    wire tripped, expire;
    wire [1:0] own_changes = own_second ^ own_previous;
    wire pad_timing = exchange_i && pad_timing_check_i && active_o && !tripped &&
        ((falling[clock_pin_i] && own_changes[0] && own_second[0]) ||
         (clock_stable_high && (rising[rx_pin_i] || falling[rx_pin_i]) && own_changes[1]));
    motif_watchdog watchdog(clk, rst_n, active_o, acquire, progress, abort_i || pad_timing, watchdog_i, tripped, expire);
    wire [2:0] timer_event;
    wire timer_bit;
    wire end_sample = timer_event == 2 || timer_event == 4 || timer_event == 5;
    wire inhibit = !enable_i || abort_i || pad_timing || release_event || (tripped && !acquire) || expire;
    wire mismatch, composition_fault, transaction_end;
    wire clear_external = inhibit || acquire || end_sample;
    wire clear = clear_external || mismatch || composition_fault || transaction_end;
    wire ex_rx_fire, ex_tx_fire, ex_tx_load, ex_rx_push, turnaround, drive_enable, drive_value, stretch;
    wire [15:0] field_value, field_next, field_override, completed_field;
    wire [3:0] field_count, field_count_override;
    wire [4:0] field_length;
    wire field_complete, field_timer, waiting_timer;
    wire [10:0] primitive_fires;
    wire [19:0] primitive_events;
    wire [15:0] temporal_count, executed_pcs;
    wire temporal_started, temporal_done;
    wire [2:0] executed_count;
    wire desired_role, current_role, accepted, captured_response, halted;
    wire [15:0] pending_field;
    wire tx_overflow, tx_underflow, rx_full, rx_empty, rx_overflow, rx_underflow;
    wire [3:0] exchange_phase;
    wire [7:0] exchange_rx_data;
    reg pending_timer_start;
    always @(posedge clk) begin
        if (!rst_n || clear) pending_timer_start<=0;
        else pending_timer_start<=exchange_i && turnaround;
    end
    wire timer_start = enable_i && !inhibit && !mismatch && !composition_fault && !transaction_end && ((exchange_i && pending_timer_start) || (acquire && timer_mode_i));
    motif_timed_sample timer(clk, rst_n, inhibit || end_sample || mismatch || composition_fault || transaction_end || (exchange_i && !timer_mode_i && timer_event == 3), timer_start,
                            levels[rx_pin_i], validate_start_i, validate_stop_i, period_i, timer_event, timer_bit);
    wire rx_fire = exchange_i ? ex_rx_fire : active_o && !clear && (timer_mode_i ? timer_event == 3 : rising[clock_pin_i]);
    wire [7:0] rx_next;
    wire rx_terminal, rx_complete;
    wire tx_fire = exchange_i ? ex_tx_fire : active_o && !clear && transmit_i && falling[clock_pin_i];
    wire [7:0] tx_value, tx_head;
    wire [3:0] tx_remaining;
    wire tx_bit, tx_terminal, tx_empty, tx_full;
    wire tx_load = exchange_i ? ex_tx_load : enable_i && !inhibit && transmit_i && (acquire || tx_terminal);
    motif_transaction exchange(clk,rst_n,clear_external,exchange_i && acquire && !inhibit && !end_sample,exchange_i && active_o && !inhibit,
        rising[clock_pin_i],falling[clock_pin_i],levels[rx_pin_i],lsb_i,transmit_i,program_i,
        field_value,field_count,tx_value,tx_head,tx_remaining,rx_full,tx_empty,timer_event==3,timer_bit,
        ex_rx_fire,ex_tx_fire,ex_tx_load,ex_rx_push,field_override,field_count_override,field_length,field_timer,
        exchange_rx_data,turnaround,mismatch,composition_fault,transaction_end,field_complete,completed_field,
        primitive_fires,primitive_events,exchange_phase,desired_role,current_role,accepted,captured_response,pending_field,
        drive_enable,drive_value,stretch,halted,waiting_timer,
        temporal_count,temporal_started,temporal_done,executed_pcs,executed_count);
    wire collision;
    wire [7:0] reference_rx_value, reference_rx_next;
    wire [2:0] reference_rx_count;
    wire reference_rx_terminal, reference_rx_complete;
    wire field_terminal, field_registered_complete;
    wire receive_bit = exchange_i ? (field_timer ? timer_bit : levels[rx_pin_i]) :
                       (timer_mode_i ? timer_bit : levels[rx_pin_i]);
    motif_shift_rx_count #(.WIDTH(16),.COUNT_WIDTH(4)) rx(clk,rst_n,clear,
        rx_fire && (!REFERENCE || exchange_i),receive_bit,lsb_i,
        field_value,field_count,field_next,field_terminal,field_registered_complete,
        exchange_i,field_complete,field_override,field_count_override);
    assign rx_value_o = REFERENCE && !exchange_i ? reference_rx_value : field_value[7:0];
    assign rx_count_o = REFERENCE && !exchange_i ? reference_rx_count : field_count[2:0];
    assign rx_next = REFERENCE && !exchange_i ? reference_rx_next : field_next[7:0];
    assign rx_terminal = REFERENCE && !exchange_i ? reference_rx_terminal : field_terminal;
    assign rx_complete = REFERENCE && !exchange_i ? reference_rx_complete : field_registered_complete;
    generate if(REFERENCE)begin: sequential
        motif_sequential_shift shifts(clk,rst_n,clear,inhibit || end_sample || mismatch || composition_fault || transaction_end,rx_fire,tx_fire,tx_load,
            receive_bit,lsb_i,tx_empty ? fill_i : tx_head,
            reference_rx_value,tx_value,reference_rx_count,tx_remaining,reference_rx_next,reference_rx_terminal,tx_terminal,tx_bit,reference_rx_complete,collision);
    end else begin: compound
        motif_shift_tx tx(clk,rst_n,inhibit || end_sample || mismatch || composition_fault || transaction_end,tx_load,tx_fire,lsb_i,
                          tx_empty ? fill_i : tx_head,tx_value,tx_remaining,tx_bit,tx_terminal);
        assign reference_rx_value=0;assign reference_rx_next=0;assign reference_rx_count=0;
        assign reference_rx_terminal=0;assign reference_rx_complete=0;assign collision=0;
    end endgenerate
    motif_fifo tx_fifo(clk, rst_n, host_tx_push_i, tx_load && !tx_empty, host_tx_data_i,
                       tx_head, tx_fifo_count_o, tx_full, tx_empty, tx_overflow, tx_underflow);
    reg [7:0] validated_byte;
    wire rx_push = enable_i && !inhibit && (exchange_i ? ex_rx_push :
                   (rx_terminal && !validate_stop_i) || (active_o && timer_event == 4));
    motif_fifo rx_fifo(clk, rst_n, rx_push, host_rx_pop_i,
                       exchange_i ? exchange_rx_data : validate_stop_i ? validated_byte : rx_next, host_rx_data_o,
                       rx_fifo_count_o, rx_full, rx_empty, rx_overflow, rx_underflow);
    reg framing_error, fill_underflow, timeout_status;
    always @(posedge clk) begin
        if (!rst_n) begin
            active_o <= 0; validated_byte <= 0; framing_error <= 0; fill_underflow <= 0; timeout_status <= 0;
        end else begin
            if (inhibit || end_sample || mismatch || composition_fault || transaction_end) active_o <= 0;
            else if (acquire) active_o <= 1;
            if (rx_terminal) validated_byte <= rx_next;
            if (timer_event == 2 || timer_event == 5) framing_error <= 1;
            if (tx_load && tx_empty) fill_underflow <= 1;
            if (expire) timeout_status <= 1;
        end
    end
    wire [7:0] requests = exchange_i ? (active_o ?
        ((drive_enable && (!open_drain_i[tx_pin_i] || !drive_value) ? (8'b1 << tx_pin_i) : 8'b0) | (stretch ? (8'b1 << clock_pin_i) : 8'b0)) : 8'b0) :
        active_o && transmit_i ? (8'b1 << tx_pin_i) : 8'b0;
    wire [7:0] requested_data = exchange_i ? (drive_enable && drive_value && !open_drain_i[tx_pin_i] ? (8'b1 << tx_pin_i) : 8'b0) : (tx_bit ? requests : 8'b0);
    wire safe_output_assignment = tx_pin_i != frame_pin_i && tx_pin_i != clock_pin_i && tx_pin_i != rx_pin_i;
    wire [7:0] ownership = exchange_i ? (active_o ? ((8'b1 << tx_pin_i) |
        (transmit_i && hold_clock_i ? (8'b1 << clock_pin_i) : 8'b0)) : 8'b0) :
        active_o && transmit_i && safe_output_assignment ? (8'b1 << tx_pin_i) : 8'b0;
    wire raw_kill = !rst_n || !enable_i || abort_i || (!two_wire_i && !frame_falling_i && pins_i[frame_pin_i] != frame_active_high_i);
    wire [2:0] violations;
    motif_pad_guardian guardian(requested_data, requests, ownership, open_drain_i, 8'b0,
                                raw_kill, tripped, pad_data_o, pad_oe_o, violations);
    reg guard_fault;
    reg mismatch_status, pad_timing_status, composition_status;
    always @(posedge clk) begin
        if (!rst_n) begin mismatch_status<=0; pad_timing_status<=0; composition_status<=0; end
        else begin
            if (mismatch) mismatch_status<=1;
            if (composition_fault) composition_status<=1;
            if (pad_timing) pad_timing_status<=1;
        end
    end
    assign exchange_status_o={composition_status,pad_timing_status,mismatch_status};
    always @(posedge clk) begin
        if(!rst_n)guard_fault<=0;
        else if(|violations)guard_fault<=1;
    end
    assign status_o = {collision, timeout_status, framing_error, fill_underflow, rx_overflow,
                       tx_overflow, rx_underflow, guard_fault};
    wire _unused = &{rx_complete, tx_value, tx_remaining, tx_full, tx_underflow, rx_full, rx_empty, exchange_phase, field_next[15:8], field_length, completed_field, waiting_timer, primitive_fires, primitive_events, desired_role, current_role, accepted, captured_response, halted, pending_field, temporal_count, temporal_started, temporal_done, executed_pcs, executed_count, 1'b0};
endmodule
