import os
import random
import shutil
import subprocess
from collections import deque
from dataclasses import replace
from pathlib import Path

from motif import Engine
from motif.guardian import Guardian, Request
from motif.motifs import ShiftRXCount, ShiftTX
from motif.protocols import spi, uart, timed_stream
from tests.drivers import Wires


def simulate(name, source):
    directory = Path("build/rtl")
    directory.mkdir(parents=True, exist_ok=True)
    tb = directory / (name + ".sv")
    output = directory / (name + ".vvp")
    tb.write_text(source, encoding="utf-8")
    command = [os.environ.get("IVERILOG", "iverilog")]
    if os.environ.get("IVERILOG_BASE"):
        command += ["-B", os.environ["IVERILOG_BASE"]]
    command += ["-g2012", "-s", "tb", "-o", str(output)]
    command += [str(path) for path in sorted(Path("src").glob("*.sv"))] + [str(tb)]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise RuntimeError(compiled.stdout + compiled.stderr)
    result = subprocess.run([os.environ.get("VVP", "vvp"), str(output)], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    if "PASS" not in result.stdout:
        raise AssertionError(result.stdout)
    print(result.stdout.strip())


def primitive_vectors(seed=322):
    rng = random.Random(seed)
    rx, tx = ShiftRXCount(), ShiftTX()
    lines = []
    for cycle in range(2000):
        clear, fire, load, bit, lsb, value = rng.randrange(20) == 0, bool(rng.randrange(2)), rng.randrange(7) == 0, rng.randrange(2), rng.randrange(2), rng.randrange(256)
        rx.lsb_first = tx.lsb_first = bool(lsb)
        complete = False
        if clear:
            rx.clear()
            tx.value = tx.remaining = 0
        else:
            if fire:
                complete = rx.fire(bit) is not None
            if load:
                tx.load(value)
            elif fire:
                tx.fire()
        lines.append(f"clear={int(clear)}; fire={int(fire)}; load={int(load)}; bit_in={bit}; lsb={lsb}; value=8'd{value}; #4; clk=1; #1; if (rx_value !== 8'd{rx.value} || rx_count !== 3'd{rx.count} || complete !== 1'b{int(complete)} || tx_value !== 8'd{tx.value} || remaining !== 4'd{tx.remaining}) $fatal(1, \"shift mismatch seed {seed} cycle {cycle}\"); clk=0; #1;")
    return """module tb;
reg clk=0, rst_n=0, clear=0, fire=0, load=0, bit_in=0, lsb=0;
reg [7:0] value=0;
wire [7:0] rx_value, rx_next, tx_value;
wire [2:0] rx_count; wire [3:0] remaining; wire complete, rt, tt, tx_bit;
motif_shift_rx_count rx(clk,rst_n,clear,fire,bit_in,lsb,rx_value,rx_count,rx_next,rt,complete);
motif_shift_tx tx(clk,rst_n,clear,load,fire,lsb,value,tx_value,remaining,tx_bit,tt);
initial begin #4;clk=1;#1;clk=0;rst_n=1;
""" + "\n".join(lines) + '\n$display("PASS shifts: 2000 vectors, seed 322");$finish;end endmodule\n'


def guardian_vectors(seed=141):
    rng = random.Random(seed)
    lines = []
    for cycle in range(4000):
        data, oe, own, od, conflict = [rng.randrange(256) for _ in range(5)]
        kill, fatal = rng.randrange(2), rng.randrange(2)
        guard = Guardian(od)
        guard.tripped = bool(fatal)
        requests = [Request(0, pin, (data >> pin) & 1) for pin in range(8) if oe & (1 << pin)]
        requests += [Request(0, pin, 0) for pin in range(8) if oe & conflict & (1 << pin)]
        expected_data, expected_oe = guard.apply(requests, {0: own}, bool(kill))
        lines.append(f"data=8'd{data};oe=8'd{oe};own=8'd{own};od=8'd{od};conflict=8'd{conflict};kill={kill};fatal={fatal};#1;if(out_data!==8'd{expected_data} || out_oe!==8'd{expected_oe})$fatal(1,\"guardian seed {seed} vector {cycle}\");")
    return """module tb;
reg [7:0] data,oe,own,od,conflict;reg kill,fatal;
wire [7:0] out_data,out_oe;wire [2:0] violations;
motif_pad_guardian g(data,oe,own,od,conflict,kill,fatal,out_data,out_oe,violations);
initial begin
""" + "\n".join(lines) + '\n$display("PASS guardian: 4000 vectors, seed 141");$finish;end endmodule\n'


class RecordedEngine(Engine):
    def __init__(self, config):
        super().__init__(config)
        self.rows = []
        self.host_push = self.host_pop = False
        self.host_data = 0

    def push_tx(self, byte):
        super().push_tx(byte)
        self.host_push, self.host_data = True, byte

    def pop_rx(self):
        byte = super().pop_rx()
        self.host_pop = byte is not None
        return byte

    def step(self, pins, reset=False, abort=False, requests=None):
        inputs = (pins, reset, abort, self.host_push, self.host_pop, self.host_data)
        trace = super().step(pins, reset, abort, requests)
        self.rows.append((inputs, trace, len(self.rx_fifo), len(self.tx_fifo), self.rx_fifo[0] if self.rx_fifo else 0))
        self.host_push = self.host_pop = False
        return trace


def core_vectors(config, name, reference=False, spacing=8):
    engine = RecordedEngine(config)
    wire = Wires(engine, spacing=spacing)
    if name == "spi":
        rng = random.Random(117)
        for _ in range(24):
            expected_rx, expected_tx = rng.randrange(256), rng.randrange(256)
            assert wire.spi(expected_rx, expected_tx) == expected_tx
            assert engine.pop_rx() == expected_rx
            wire.hold()
        wire.hold(p0=0)
        wire.hold(p1=1)
        engine.step(wire.pins, abort=True)
        wire.hold(p0=1)
        if config.watchdog:
            wire.hold(p0=0)
            wire.hold(100)
            assert not engine.active and not wire.trace[-1]["oe"]
            wire.hold(p0=1)
            wire.hold(p0=0)
            assert engine.active
    elif name == "uart":
        for value in [0, 255, 85, 170, 37]:
            wire.uart(value, period=config.period)
            assert engine.pop_rx() == value
            wire.hold()
        wire.uart(85, period=config.period, stop=0)
        wire.uart(170, period=config.period)
        assert engine.pop_rx() == 170
        wire.hold()
    elif name == "concurrent":
        engine.push_tx(170)
        wire.hold(p0=1, p1=0)
        wire.hold(4, p0=0)
        for cycle in range(160):
            wire.hold(1, p1=((cycle + 3) // 2) % 2, p2=(cycle // 16) % 2)
        assert any("SHIFT_RX_COUNT" in row["fires"] and "SHIFT_TX" in row["fires"] for row in wire.trace)
        wire.hold(p0=1)
    else:
        wire.hold(p0=1)
        wire.hold(4, p0=0)
        for value in [85, 170]:
            for index in range(7, -1, -1):
                wire.hold(config.period, p2=(value >> index) & 1)
        wire.hold(p0=1)
    lines = []
    collision = False
    for index, (inputs, trace, rx_level, tx_level, head) in enumerate(engine.rows):
        pins, reset, abort, push, pop, data = inputs
        faults = set(trace["faults"])
        status = int(bool(faults & {"ownership", "drive_high", "conflict"})) | (int("rx_overflow" in faults) << 3) | (int("tx_underflow" in faults) << 4) | (int(bool(faults & {"invalid_start", "invalid_stop"})) << 5) | (int("timeout" in faults) << 6)
        lines.append(f"pins=8'd{pins};rst_n={int(not reset)};abort_in={int(abort)};push={int(push)};pop={int(pop)};host_data=8'd{data};#4;clk=1;#1;if(rx_value!==8'd{trace['rx_value']} || bit_count!==3'd{trace['rx_count']} || active!==1'b{int(trace['active'])} || pad_data!==8'd{trace['data']} || pad_oe!==8'd{trace['oe']} || status!==8'd{status} || rx_count!==3'd{rx_level} || tx_count!==3'd{tx_level} || rx_head!==8'd{head})$fatal(1,\"{name} core mismatch cycle {index}: rx=%d cnt=%d active=%b oe=%h FIFO=%d head=%h status=%h\",rx_value,bit_count,active,pad_oe,rx_count,rx_head,status);clk=0;#1;")
        if name == "concurrent" and reference:
            collision |= "SHIFT_RX_COUNT" in trace["fires"] and "SHIFT_TX" in trace["fires"]
            prefix = lines[-1].split("if(rx_value", 1)[0]
            lines[-1] = prefix + f"if(status[7]!==1'b{int(collision)} || rx_value!==8'd{trace['rx_value']} || bit_count!==3'd{trace['rx_count']} || rx_count!==3'd{rx_level} || rx_head!==8'd{head})$fatal(1,\"reference collision/RX contract cycle {index}\");clk=0;#1;"
    header = f"""module tb;
reg clk=0,rst_n=0,abort_in=0,push=0,pop=0;reg [7:0] pins=255,host_data=0;
wire [7:0] rx_head,pad_data,pad_oe,status,rx_value;
wire [2:0] rx_count,tx_count,bit_count;wire active;wire [1:0] ex_status;
motif_core #(.REFERENCE({int(reference)})) core(clk,rst_n,1'b1,abort_in,pins,1'b{int(config.frame=='falling')},1'b{int(config.sample=='timer')},1'b{int(config.transmit)},1'b{int(config.lsb_first)},1'b{int(config.validate_start)},1'b{int(config.validate_stop)},3'd{config.frame_pin},3'd{config.clock_pin},3'd{config.rx_pin},3'd{config.tx_pin},16'd{config.period},16'd{config.watchdog},8'd{config.fill},8'd{config.open_drain},push,pop,host_data,rx_head,pad_data,pad_oe,rx_count,tx_count,status,active,rx_value,bit_count,1'b0,1'b0,1'b1,1'b1,7'h52,ex_status);
initial begin #4;clk=1;#1;clk=0;rst_n=1;
"""
    label = "reference collision/RX contract" if name == "concurrent" and reference else name + " core"
    return header + "\n".join(lines) + f'\n$display("PASS {label}: {len(lines)} model/RTL cycles");$finish;end endmodule\n'


def fifo_vectors(seed=73):
    rng = random.Random(seed)
    queue = deque()
    overflow = underflow = False
    lines = []
    for cycle in range(1200):
        reset, push, pop = rng.randrange(40) == 0, bool(rng.randrange(2)), bool(rng.randrange(2))
        data = rng.randrange(256)
        if reset:
            queue.clear()
            overflow = underflow = False
        else:
            removed = pop and bool(queue)
            if removed:
                queue.popleft()
            elif pop:
                underflow = True
            if push:
                if len(queue) < 4:
                    queue.append(data)
                else:
                    overflow = True
        head = queue[0] if queue else 0
        lines.append(f"rst_n={int(not reset)};push={int(push)};pop={int(pop)};data=8'd{data};#4;clk=1;#1;if(count!==3'd{len(queue)} || head!==8'd{head} || overflow!==1'b{int(overflow)} || underflow!==1'b{int(underflow)})$fatal(1,\"FIFO seed {seed} cycle {cycle}\");clk=0;#1;")
    return """module tb;
reg clk=0,rst_n=0,push=0,pop=0;reg [7:0] data=0;
wire [7:0] head;wire [2:0] count;wire full,empty,overflow,underflow;
motif_fifo fifo(clk,rst_n,push,pop,data,head,count,full,empty,overflow,underflow);
initial begin #4;clk=1;#1;clk=0;rst_n=1;
""" + "\n".join(lines) + '\n$display("PASS FIFO: 1200 vectors, seed 73");$finish;end endmodule\n'


def run():
    simulate("shifts", primitive_vectors())
    simulate("guardian", guardian_vectors())
    simulate("fifo", fifo_vectors())
    for name, config in [("spi", spi.target()), ("uart", uart.receiver(32)), ("timed_stream", timed_stream.receiver(16))]:
        simulate(name, core_vectors(config, name))
        simulate(name + "_reference", core_vectors(config, name, reference=True))
    simulate("host", Path("test/host_tb.sv").read_text(encoding="utf-8"))
    simulate("host_reference", Path("test/host_tb.sv").read_text(encoding="utf-8").replace("tt_um_wellitsabhinav_motif dut", "motif_reference_top dut"))
    simulate("watchdog_core", core_vectors(replace(spi.target(), watchdog=32), "spi"))
    simulate("concurrent_core", core_vectors(replace(timed_stream.receiver(16), transmit=True), "concurrent"))
    simulate("concurrent_reference", core_vectors(replace(timed_stream.receiver(16), transmit=True), "concurrent", reference=True))
    for spacing in (2, 3, 4):
        for reference in (False, True):
            simulate(f"spi_spacing_{spacing}_{int(reference)}", core_vectors(spi.target(), "spi", reference=reference, spacing=spacing))


if __name__ == "__main__":
    run()
