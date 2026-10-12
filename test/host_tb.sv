`timescale 1ns/1ps
module tb;
    reg clk=0,rst_n=0,ena=1;
    reg [7:0] ui=8'h02,pins=8'hff;
    wire [7:0] uo,pad_data,pad_oe;
    tt_um_wellitsabhinav_motif dut(.ui_in(ui),.uio_in(pins),.uo_out(uo),.uio_out(pad_data),
                                 .uio_oe(pad_oe),.ena(ena),.clk(clk),.rst_n(rst_n));
    reg [7:0] discard,result,protocol_rx;
    integer index;
    task tick(input integer cycles);
        integer n;
        begin for(n=0;n<cycles;n=n+1)begin clk=0;#5;clk=1;#5;end clk=0;end
    endtask
    task host_byte(input [7:0] data,output [7:0] received);
        integer bit_index;
        begin
            received=0;
            for(bit_index=7;bit_index>=0;bit_index=bit_index-1)begin
                ui[0]=0;ui[2]=data[bit_index];tick(8);
                ui[0]=1;tick(8);received={received[6:0],uo[0]};
                ui[0]=0;tick(8);
            end
        end
    endtask
    task host_write(input [7:0] address,input [7:0] data);
        begin ui[1]=0;tick(8);host_byte(2,discard);host_byte(address,discard);host_byte(data,discard);ui[1]=1;tick(8);end
    endtask
    task host_read(input [7:0] address,output [7:0] data);
        begin ui[1]=0;tick(8);host_byte(1,discard);host_byte(address,discard);host_byte(0,data);ui[1]=1;tick(8);end
    endtask
    initial begin
        tick(4);rst_n=1;tick(8);
        if(pad_oe!==0)$fatal(1,"reset/disabled pad state");
        host_read(3,result);if(result!==8'hb2)$fatal(1,"host configuration read %h",result);
        host_write(2,2);host_write(0,9);
        pins[1]=0;pins[0]=0;tick(8);
        if(pad_oe!==0)$fatal(1,"aliased output gained ownership");
        host_read(18,result);if(!result[0])$fatal(1,"aliased output fault not retained");
        rst_n=0;tick(4);pins=8'hff;rst_n=1;tick(8);
        host_write(0,9);host_write(8'h10,8'ha5);
        pins[1]=0;tick(8);pins[0]=0;tick(8);protocol_rx=0;
        for(index=7;index>=0;index=index-1)begin
            pins[2]=(8'h55>>index)&1;tick(8);
            pins[1]=1;tick(8);protocol_rx={protocol_rx[6:0],pad_data[3]};
            pins[1]=0;tick(8);
        end
        pins[0]=1;#1;if(pad_oe!==0)$fatal(1,"raw frame release");tick(8);
        if(protocol_rx!==8'ha5)$fatal(1,"SPI TX %h",protocol_rx);
        host_read(8'h11,result);if(result!==8'h55)$fatal(1,"SPI RX %h",result);
        host_write(3,17);host_read(3,result);if(result!==8'hb2)$fatal(1,"configuration changed while enabled");
        host_write(0,8);host_write(6,8);host_write(0,9);
        pins[0]=0;tick(8);if(pad_oe[3]!==0)$fatal(1,"open-drain high drive");pins[0]=1;tick(8);
        host_read(18,result);if(!result[0])$fatal(1,"guard fault not retained");
        host_write(0,8);host_write(6,0);host_write(1,10);host_write(3,32);host_write(4,0);host_write(0,8'h77);
        pins[2]=1;tick(32);pins[2]=0;tick(32);
        for(index=0;index<8;index=index+1)begin pins[2]=(8'h25>>index)&1;tick(32);end
        pins[2]=1;tick(40);host_read(8'h11,result);if(result!==8'h25)$fatal(1,"UART RX %h",result);
        if(pad_oe!==0)$fatal(1,"UART receive drove pads");
        host_write(0,0);host_write(3,4);host_write(0,8'h77);
        fork
            begin host_read(17,result);end
            begin
                repeat(420)@(negedge clk);pins[2]=0;repeat(4)@(negedge clk);
                for(integer inject_bit=0;inject_bit<8;inject_bit=inject_bit+1)begin
                    pins[2]=(8'h25>>inject_bit)&1;repeat(4)@(negedge clk);
                end
                pins[2]=1;repeat(8)@(negedge clk);
            end
        join
        if(result!==0)$fatal(1,"empty read snapshot changed");
        host_read(17,result);if(result!==8'h25)$fatal(1,"RX byte arriving during empty host read was lost: %h",result);
        host_write(0,0);host_write(1,8);host_write(3,16);host_write(0,5);
        pins[0]=1;tick(8);pins[0]=0;tick(4);
        for(index=7;index>=0;index=index-1)begin pins[2]=(8'haa>>index)&1;tick(16);end
        pins[0]=1;tick(8);host_read(8'h11,result);if(result!==8'haa)$fatal(1,"timed stream RX %h",result);
        ena=0;#1;if(pad_oe!==0)$fatal(1,"disable did not release");
        $display("PASS host: runtime SPI/UART/timed-stream configuration, FIFO data and raw release");$finish;
    end
endmodule
