`default_nettype none
module tt_um_wellitsabhinav_motif #(parameter REFERENCE=0) (
    input wire [7:0] ui_in, uio_in,
    output wire [7:0] uo_out, uio_out, uio_oe,
    input wire ena, clk, rst_n
);
    wire write, read, host_miso, read_valid;
    wire [2:0] rx_count, tx_count;
    wire [7:0] address, write_data, rx_data, status;
    reg [7:0] read_data;
    motif_host_spi host(clk, rst_n, ui_in[0], ui_in[1], ui_in[2], read_data,
                         address != 8'h11 || rx_count != 0,
                         host_miso, write, read, address, read_valid, write_data);
    reg [6:0] control;
    reg [5:0] pins_low, pins_high;
    reg [15:0] period, watchdog;
    reg [7:0] fill, open_drain;
    reg [4:0] transaction_control;
    reg [1023:0] transaction_program;
    reg config_rejected, empty_read;
    reg invalid_program;
    reg [63:0] entry;
    integer slot;
    always @* begin
        invalid_program=0;entry=0;
        for(slot=0;slot<16;slot=slot+1)begin
            entry=transaction_program[slot*64 +: 64];
            if(entry[2:0]==0 && (entry[17:13]==0 || entry[17:13]>16))invalid_program=1;
            if(entry[2:0]==7 && entry[15:13]>5)invalid_program=1;
            if(entry[2:0]==4 && entry[53] && !transaction_control[3])invalid_program=1;
            if(entry[2:0]==4 && entry[55] &&
               (entry[4:3]!=0 || entry[20:15]!=0 || entry[14:13]<2 || entry[52:37]==0 ||
                entry[36:22]!=0 || entry[54:53]!=0 || entry[62:57]!=0 ||
                (entry[14:13]==2 && (entry[21] || entry[56]))))invalid_program=1;
        end
    end
    wire invalid_exchange = (transaction_control[1] && !transaction_control[0]) ||
        (transaction_control[0] && (invalid_program ||
          pins_low[5:3] == pins_high[2:0] || pins_high[5:3] == pins_low[5:3] ||
          pins_high[5:3] == pins_low[2:0] ||
          (pins_high[2:0] == pins_high[5:3] && !open_drain[pins_high[2:0]]) ||
          (transaction_control[3] && !open_drain[pins_low[5:3]])));
    always @(posedge clk) begin
        if (!rst_n) begin
            control <= 7'h08; pins_low <= 6'h08; pins_high <= 6'h1a;
            period <= 434; watchdog <= 0; fill <= 255; open_drain <= 0; config_rejected <= 0; empty_read <= 0;
            transaction_control<=0;transaction_program<=0;
        end else begin
          if(read && address == 8'h11 && !read_valid)empty_read<=1;
          if (write) begin
            if (address == 0) begin
                if ((!control[0] || !write_data[0]) && !(write_data[0] && invalid_exchange)) control <= write_data[6:0];
                else config_rejected <= 1;
            end else if (address==9 || address==10)config_rejected<=1;
            else if (address < 9 || address==22 || address[7]) begin
                if (control[0]) config_rejected <= 1;
                else case (address)
                    1: pins_low <= write_data[5:0];
                    2: pins_high <= write_data[5:0];
                    3: period[7:0] <= write_data;
                    4: period[15:8] <= write_data;
                    5: fill <= write_data;
                    6: open_drain <= write_data;
                    7: watchdog[7:0] <= write_data;
                    8: watchdog[15:8] <= write_data;
                    22: transaction_control <= write_data[4:0];
                    default: if(address[7])transaction_program[address[6:0]*8 +: 8]<=write_data;
                endcase
            end
          end
        end
    end
    wire active;
    wire [7:0] rx_value;
    wire [2:0] bit_count;
    wire [2:0] exchange_status;
    wire enable = control[0] && ena && period >= 2 && !invalid_exchange;
    motif_core #(.REFERENCE(REFERENCE)) core(clk, rst_n, enable, 1'b0, uio_in, control[1], control[2], control[3],
                     control[4], control[5], control[6], pins_low[2:0], pins_low[5:3],
                     pins_high[2:0], pins_high[5:3], period, watchdog, fill, open_drain,
                     write && address == 8'h10, read && address == 8'h11 && read_valid, write_data,
                     rx_data, uio_out, uio_oe, rx_count, tx_count, status, active, rx_value, bit_count,
                     transaction_control[0],transaction_control[1],transaction_control[2],transaction_control[3],transaction_control[4],transaction_program,exchange_status);
    always @* begin
        read_data = 0;
        case (address)
            0: read_data = {1'b0, control};
            1: read_data = {2'b0, pins_low};
            2: read_data = {2'b0, pins_high};
            3: read_data = period[7:0];
            4: read_data = period[15:8];
            5: read_data = fill;
            6: read_data = open_drain;
            7: read_data = watchdog[7:0];
            8: read_data = watchdog[15:8];
            8'h11: read_data = rx_data;
            8'h12: read_data = status | {6'b0, empty_read, config_rejected};
            8'h13: read_data = {1'b0, active, tx_count, rx_count};
            8'h14: read_data = {5'b0,exchange_status};
            8'h15: read_data = 3;
            8'h16: read_data = {3'b0,transaction_control};
            default: if(address[7])read_data=transaction_program[address[6:0]*8 +: 8];
        endcase
    end
    assign uo_out = {7'b0, host_miso};
    wire _unused = &{ui_in[7:3], rx_value, bit_count, entry, 1'b0};
endmodule
