`default_nettype none
// Four protocol-neutral operations, composed by the preregistered bounded table.
module motif_transaction (
    input wire clk, rst_n, clear_i, run_i, rising_i, falling_i, bit_i, lsb_i, transmit_i,
    input wire [1023:0] program_i,
    input wire [15:0] rx_value_i,
    input wire [3:0] rx_count_i,
    input wire [7:0] tx_value_i, tx_head_i,
    input wire [3:0] tx_remaining_i,
    input wire rx_full_i, tx_empty_i, settled_i, settled_bit_i,
    output reg rx_fire_o, tx_fire_o, tx_load_o, rx_push_o,
    output reg [15:0] rx_next_o,
    output reg [3:0] rx_count_next_o,
    output reg [4:0] rx_length_o,
    output reg rx_timer_o,
    output reg [7:0] rx_data_o,
    output reg turnaround_o, mismatch_o, fault_o, terminate_o, field_complete_o,
    output reg [15:0] completed_field_o,
    output reg [9:0] fires_o,
    output reg [16:0] events_o,
    output reg [3:0] pc_o,
    output reg desired_role_o, role_o, accepted_o, response_o,
    output reg [15:0] pending_field_o,
    output reg drive_enable_o, drive_value_o, hold_o, halted_o,
    output wire waiting_timer_o
);
    localparam RX=3'd0, DECIDE=3'd1, RESPOND=3'd2, HANDOFF=3'd3,
               WAIT=3'd4, TX=3'd5, HALT=3'd6, CONTINUE=3'd7;
    reg [3:0] pc_next;
    reg desired_next, role_next, accepted_next, response_next, enable_next, value_next, hold_next, halted_next;
    reg [15:0] pending_next;
    reg [63:0] word;
    reg [2:0] op;
    reg [1:0] trigger;
    reg [3:0] successor, alternate;
    reg [7:0] argument;
    reg [15:0] constant, field_mask, visited;
    reg [10:0] flags;
    reg [1:0] decision;
    reg [5:0] handoff;
    reg [4:0] response_result;
    reg [2:0] wait_result;
    reg [15:0] rx_mask;
    reg execute, triggered, capture, sample_event, complete_event, advanced, predicate;
    reg [3:0] previous_pc;
    integer stage;
    integer loads, pushes, shifts;
    wire [63:0] current_word = program_i[pc_o*64 +: 64];
    assign waiting_timer_o = !halted_o && current_word[2:0] == WAIT && current_word[14:13] == 2;

    function event_active;
        input [1:0] source;
        input rise, fall, sample;
        begin
            case(source)
                0: event_active=1;
                1: event_active=rise;
                2: event_active=fall;
                3: event_active=sample;
            endcase
        end
    endfunction

    function [1:0] field_decision;
        input [15:0] field, expected, mask_value;
        input [5:0] arg;
        input policy_enable, require_space, require_permission;
        input retained_role, full, permission;
        reg selected, accepted;
        begin
            case(arg[1:0])
                0: selected=retained_role;
                1: selected=0;
                2: selected=1;
                3: selected=field[arg[5:2]];
            endcase
            accepted=policy_enable && ((field & mask_value)==(expected & mask_value)) &&
                     (!require_space || !full) && (!require_permission || permission || !selected);
            field_decision={selected,accepted};
        end
    endfunction

    function [5:0] direction_handoff;
        input [1:0] selector;
        input retained_role, permission, empty, first_bit, begin_timer;
        reg selected, fault;
        begin
            selected=selector==0 ? retained_role : selector==2;
            fault=selected && (!permission || empty);
            direction_handoff={fault,selected && begin_timer,selected,selected,selected,first_bit};
        end
    endfunction

    function [4:0] boundary_response;
        input [1:0] mode;
        input [2:0] policy;
        input constant_bit, accepted, captured, input_bit, sample, complete, old_enable, old_value;
        reg advance, branch, enable_value, data_value, capture_value;
        begin
            advance=0;branch=1;enable_value=old_enable;data_value=old_value;capture_value=captured;
            if(mode==2) begin
                if(sample) capture_value=input_bit ^ policy[0];
                else if(complete) begin advance=1;branch=captured;enable_value=0;end
            end else begin
                advance=1;
                if(mode==3)enable_value=0;
                else begin enable_value=1;data_value=(mode==1 ? accepted : constant_bit) ^ policy[0];end
                branch=policy[1] ? accepted : policy[2] ? captured : 1'b1;
            end
            boundary_response={advance,branch,enable_value,data_value,capture_value};
        end
    endfunction

    function [2:0] wait_policy;
        input [1:0] mode;
        input [1:0] policy;
        input desired, empty, full, settled, sample_bit, tx_bit, input_bit, constant_bit;
        reg ready, hold_value, mismatch;
        begin
            case(mode)
                0:ready=!desired || !empty;
                1:ready=!full;
                2:ready=settled;
                3:ready=input_bit==constant_bit;
            endcase
            hold_value=policy[0] && desired;
            if(ready && mode!=0)hold_value=0;
            mismatch=mode==2 && policy[1] && settled && sample_bit!=tx_bit;
            wait_policy={mismatch,hold_value,ready};
        end
    endfunction

    always @* begin
        pc_next=pc_o;desired_next=desired_role_o;role_next=role_o;accepted_next=accepted_o;response_next=response_o;
        pending_next=pending_field_o;enable_next=drive_enable_o;value_next=drive_value_o;hold_next=hold_o;halted_next=halted_o;
        rx_fire_o=0;tx_fire_o=0;tx_load_o=0;rx_push_o=0;rx_data_o=pending_field_o[7:0];
        rx_next_o=rx_value_i;rx_count_next_o=rx_count_i;rx_length_o=8;rx_timer_o=0;
        turnaround_o=0;mismatch_o=0;fault_o=0;terminate_o=0;field_complete_o=0;completed_field_o=0;
        fires_o=0;events_o=0;visited=0;loads=0;pushes=0;shifts=0;
        word=0;op=0;trigger=0;successor=0;alternate=0;argument=0;constant=0;field_mask=0;flags=0;
        decision=0;handoff=0;response_result=0;wait_result=0;rx_mask=0;
        triggered=0;capture=0;sample_event=0;complete_event=0;advanced=0;predicate=0;previous_pc=0;
        execute=run_i && !clear_i && !halted_o;
        for(stage=0;stage<4;stage=stage+1)begin
            if(execute)begin
                word=program_i[pc_next*64 +: 64];op=word[2:0];trigger=word[4:3];successor=word[8:5];alternate=word[12:9];
                argument=word[20:13];constant=word[36:21];field_mask=word[52:37];flags=word[63:53];
                sample_event=event_active(trigger,rising_i,falling_i,settled_i);complete_event=event_active(constant[1:0],rising_i,falling_i,settled_i);
                capture=op==RESPOND && argument[1:0]==2;
                triggered=sample_event || (capture && complete_event);
                if(!triggered)execute=0;
                else if(visited[pc_next])begin fault_o=1;execute=0;end
                else begin
                    visited[pc_next]=1;previous_pc=pc_next;advanced=0;
                    case(op)
                        RX:begin
                            fires_o[3]=1;rx_fire_o=1;rx_length_o=argument[4:0];rx_timer_o=trigger==3;
                            if(argument[4:0]==0 || argument[4:0]>16)fault_o=1;
                            else begin
                                rx_mask=16'hffff >> (5'd16-argument[4:0]);
                                rx_next_o=lsb_i ? (rx_next_o >> 1) | ({15'b0,(trigger==3 ? settled_bit_i : bit_i)} << (argument[4:0]-1'b1)) :
                                          ((rx_next_o << 1) | {15'b0,(trigger==3 ? settled_bit_i : bit_i)}) & rx_mask;
                                if({1'b0,rx_count_next_o}==argument[4:0]-1'b1)begin
                                    rx_count_next_o=0;pending_next=rx_next_o;pc_next=successor;advanced=1;
                                    field_complete_o=1;completed_field_o=rx_next_o;events_o[1]=1;
                                end else rx_count_next_o=rx_count_next_o+1'b1;
                            end
                        end
                        DECIDE:begin
                            fires_o[6]=1;
                            decision=field_decision(pending_next,constant,field_mask,argument[5:0],flags[0],flags[2],flags[3],desired_next,rx_full_i,transmit_i);
                            desired_next=decision[1];accepted_next=decision[0];
                            if(decision[0] && flags[1])begin rx_push_o=1;rx_data_o=pending_next[7:0];pushes=pushes+1;end
                            events_o[decision[0] ? 2:3]=1;
                            pc_next=decision[0] || !flags[4] ? successor : alternate;advanced=1;
                        end
                        RESPOND:begin
                            fires_o[8]=1;
                            response_result=boundary_response(argument[1:0],flags[2:0],constant[0],accepted_next,response_next,
                                bit_i,sample_event,complete_event,enable_next,value_next);
                            enable_next=response_result[2];value_next=response_result[1];response_next=response_result[0];
                            if(response_result[4])begin
                                pc_next=response_result[3] ? successor : alternate;advanced=1;
                                if(capture)events_o[response_result[3] ? 7:8]=1;
                                else events_o[argument[1:0]==3 ? 5:4]=1;
                            end else if(capture && sample_event)events_o[6]=1;
                        end
                        HANDOFF:begin
                            fires_o[7]=1;
                            handoff=direction_handoff(argument[1:0],desired_next,transmit_i,tx_empty_i,
                                lsb_i ? tx_head_i[0] : tx_head_i[7],flags[0]);
                            role_next=handoff[3];
                            if(handoff[5])fault_o=1;
                            else if(handoff[3])begin
                                tx_load_o=1;loads=loads+1;fires_o[4]=1;enable_next=1;value_next=handoff[0];
                                turnaround_o=handoff[4];if(handoff[4])events_o[10]=1;
                                pc_next=successor;
                            end else begin enable_next=0;hold_next=0;pc_next=alternate;end
                            advanced=1;
                        end
                        WAIT:begin
                            fires_o[9]=1;
                            wait_result=wait_policy(argument[1:0],flags[1:0],desired_next,tx_empty_i,rx_full_i,settled_i,
                                settled_bit_i,lsb_i ? tx_value_i[0] : tx_value_i[7],bit_i,constant[0]);
                            hold_next=wait_result[1];
                            if(wait_result[2])mismatch_o=1;
                            else if(wait_result[0])begin pc_next=successor;advanced=1;events_o[9]=1;end
                        end
                        TX:begin
                            fires_o[4]=1;tx_fire_o=1;shifts=shifts+1;
                            if(tx_remaining_i==0)fault_o=1;
                            else begin
                                enable_next=1;value_next=lsb_i ? tx_value_i[1] : tx_value_i[6];
                                if(tx_remaining_i==(flags[0] ? 4'd2:4'd1))begin
                                    if(flags[1])enable_next=0;
                                    if(flags[2])response_next=0;
                                    pc_next=successor;advanced=1;events_o[11]=1;
                                end
                            end
                        end
                        HALT:begin
                            halted_next=1;
                            if(!flags[1])begin enable_next=0;hold_next=0;end
                            if(flags[0])begin terminate_o=1;events_o[15]=1;end
                            events_o[12]=1;execute=0;
                        end
                        CONTINUE:begin
                            case(argument[2:0])
                                0:predicate=1;1:predicate=accepted_next;2:predicate=response_next;
                                3:predicate=desired_next;4:predicate=rx_full_i;5:predicate=tx_empty_i;
                                default:begin predicate=0;fault_o=1;end
                            endcase
                            pc_next=predicate ? successor : alternate;advanced=1;
                        end
                        default:begin end
                    endcase
                    if(loads>1 || pushes>1 || shifts>1 || (loads!=0 && shifts!=0))fault_o=1;
                    if(fault_o || mismatch_o || halted_next)execute=0;
                    else if(!advanced || !flags[10] || program_i[pc_next*64+3 +: 2]!=0)execute=0;
                    else if(pc_next==previous_pc || visited[pc_next] || stage==3)begin fault_o=1;execute=0;end
                end
            end
        end
        if(mismatch_o || fault_o || terminate_o)begin
            rx_fire_o=0;tx_fire_o=0;tx_load_o=0;rx_push_o=0;turnaround_o=0;
            if(mismatch_o)events_o[13]=1;
            if(fault_o)events_o[14]=1;
        end
    end
    always @(posedge clk)begin
        if(!rst_n || clear_i || mismatch_o || fault_o || terminate_o)begin
            pc_o<=0;desired_role_o<=0;role_o<=0;accepted_o<=0;response_o<=0;pending_field_o<=0;
            drive_enable_o<=0;drive_value_o<=0;hold_o<=0;halted_o<=0;
        end else begin
            pc_o<=pc_next;desired_role_o<=desired_next;role_o<=role_next;accepted_o<=accepted_next;response_o<=response_next;
            pending_field_o<=pending_next;drive_enable_o<=enable_next;drive_value_o<=value_next;hold_o<=hold_next;halted_o<=halted_next;
        end
    end
    wire _unused=&{argument[7:6],flags[9:5],handoff[2:1],current_word,tx_value_i[5:2],tx_head_i[6:1],1'b0};
endmodule
