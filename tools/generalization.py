"""Deterministic gate experiments; generated traces stay in ignored build output."""
import argparse
import hashlib
import json
import os
import platform
import random
import subprocess
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

from motif import Engine
from motif.protocols.i2c import target
from tests.i2c_driver import Bus
from tools.accounting import normalize
from tools.frozen_manifest import INITIAL, PROMOTED, digest, inventory, verify

PHASES = ["rx", "decide", "ack_setup", "ack_hold", "tx", "controller_ack", "stretch", "settle", "idle"]
MOTIFS = ["FRAME_ACQUIRE", "FRAME_RELEASE", "RESET_COUNTER", "SHIFT_RX_COUNT", "SHIFT_TX", "TIMED_SAMPLE", "BYTE_EXCHANGE"]
EVENTS = ["frame_start", "byte_complete", "address_match", "address_miss", "receive_nack", "turnaround_begin",
          "data_mismatch", "tx_complete", "transmit_nack", "pad_timing_fault"]
FIELDS = ["pins", "levels", "rising", "falling", "motifs", "events", "byte", "rx_value", "rx_count",
          "tx_value", "tx_remaining", "active", "data", "oe", "rx_fifo_count", "tx_fifo_count", "rx_head",
          "phase", "ack", "stretch", "guardian_tripped", "status", "exchange_status", "rx_push", "tx_pop"]


def bits(names, vocabulary):
    return sum(1 << i for i, name in enumerate(vocabulary) if name in names)


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Recorder(Engine):
    """Explicit synchronous host scheduling around an unchanged independent model.

    Host writes become visible after this cycle's actor tick, like motif_fifo.
    Pop validity uses pre-tick count, including an empty snapshot during enqueue.
    """
    def __init__(self, config):
        super().__init__(config)
        self.rows = []
        self.actions = []
        self.host_push = self.host_pop = False
        self.host_data = 0

    def step(self, pins, reset=False, abort=False, requests=None):
        if requests is not None:
            raise ValueError("Executor request injection is not a hardware interface")
        old_rx, old_tx = len(self.rx_fifo), len(self.tx_fifo)
        row = super().step(pins, reset, abort)
        rx_push = len(self.rx_fifo) > old_rx and not reset
        tx_pop = len(self.tx_fifo) < old_tx and not reset
        if not reset:
            if self.host_pop and old_rx:
                self.rx_fifo.popleft()
            if self.host_push:
                self.tx_fifo.append(self.host_data)
        faults = set(row["faults"])
        status = int(bool(faults & {"ownership", "drive_high", "conflict"})) | (int("rx_overflow" in faults) << 3) | (int("tx_underflow" in faults) << 4) | (int(bool(faults & {"invalid_start", "invalid_stop"})) << 5) | (int("timeout" in faults) << 6)
        normalized = dict(zip(FIELDS, [pins, row["levels"], row["rising"], row["falling"],
            bits({normalize(f) for f in row["fires"]}, MOTIFS), bits(row["events"], EVENTS),
            row["byte"] if row["byte"] is not None else -1, row["rx_value"], row["rx_count"], row["tx_value"], row["tx_remaining"],
            int(row["active"]), row["data"], row["oe"], len(self.rx_fifo), len(self.tx_fifo), self.rx_fifo[0] if self.rx_fifo else 0,
            PHASES.index(self.exchange.phase), int(self.exchange.ack), int(self.exchange.stretch), int(self.guardian.tripped), status,
            int("data_mismatch" in faults) | (int("pad_timing" in faults) << 1), int(rx_push), int(tx_pop)]))
        self.rows.append(normalized)
        self.actions.append([pins, int(reset), int(abort), int(self.host_push), int(self.host_pop), self.host_data])
        self.host_push = self.host_pop = False
        return row


class RecordedBus(Bus):
    def host(self, push=None, pop=False):
        value = self.engine.rx_fifo[0] if pop and self.engine.rx_fifo else None
        assert not self.engine.host_push and not self.engine.host_pop
        self.engine.host_push = push is not None
        self.engine.host_pop = pop
        self.engine.host_data = push or 0
        self.hold(1)
        return value

    def reset(self):
        pins = (255 & ~6) | ((self.scl and not bool(self.output["oe"] & 2)) << 1) | ((self.sda and not bool(self.output["oe"] & 4)) << 2)
        self.output = self.engine.step(pins, reset=True)
        assert self.output["oe"] == 0
        self.hold(8)


def cases():
    result = []

    def make(name, config=None, spacing=8):
        engine = Recorder(config or target())
        bus = RecordedBus(engine, spacing)
        result.append((name, engine))
        return bus

    for setup in (13, 63):
        bus = make(f"random_setup_{setup}", target(setup_cycles=setup))
        rng = random.Random(20261012)
        for _ in range(16):
            payload = [rng.randrange(256) for _ in range(3)]
            bus.start(); assert bus.write(0xa4)
            for byte in payload: assert bus.write(byte)
            assert [bus.host(pop=True) for _ in payload] == payload
            for byte in payload: bus.host(push=byte)
            bus.start(); assert bus.write(0xa5)
            assert [bus.read(ack=i < 2) for i in range(3)] == payload
            bus.stop()
        assert not bus.engine.active

    for opts in ({"ack_address": False}, {"ack_data": False}, {}):
        bus = make("policy_" + stable_hash(opts)[:8], target(**opts))
        bus.start(); assert not bus.write(0xa6); bus.stop()
        bus.start(); assert bus.write(0xa4) == opts.get("ack_address", True)
        assert bus.write(85) == (opts.get("ack_address", True) and opts.get("ack_data", True))
        bus.stop()

    bus = make("fifo_full")
    bus.start(); assert bus.write(0xa4)
    for i in range(4): assert bus.write(i)
    assert not bus.write(99)
    assert [bus.host(pop=True) for _ in range(4)] == list(range(4))
    bus.stop()

    bus = make("starvation_fifo_ready")
    bus.start(); assert bus.write(0xa5)
    bus.hold(200, scl=1)
    assert bus.output["oe"] & 2
    bus.host(push=170)
    assert bus.read(ack=True) == 170
    bus.hold(80, scl=1)
    assert bus.output["oe"] & 2
    bus.host(push=85)
    assert bus.read() == 85
    bus.stop()

    for bits_count in (0, 1, 4, 7):
        for termination in ("start", "stop", "reset"):
            bus = make(f"partial_{bits_count}_{termination}")
            bus.start(); assert bus.write(0xa4)
            for bit in [1, 0, 1, 0, 1, 0, 1][:bits_count]:
                bus.hold(scl=0, sda=bit); bus.clock_high()
            getattr(bus, termination)()
            # START/STOP drivers can supply an eighth clock at this boundary.
            # Already accepted bytes survive release, as documented by the model.
            while bus.engine.rx_fifo:
                bus.host(pop=True)
            if termination != "start": bus.stop(); bus.start()
            assert bus.write(0xa4) and bus.write(85)
            assert bus.host(pop=True) == 85
            bus.stop()

    bus = make("timeout_recovery", target(watchdog=64, setup_cycles=13))
    bus.start(); assert bus.write(0xa4); bus.hold(80, scl=0)
    assert not bus.engine.active and "timeout" in bus.output["faults"]
    bus.stop(); bus.start(); assert bus.write(0xa4) and bus.write(0); bus.stop()
    bus.start(); assert bus.write(0xa5); bus.hold(90, scl=1)
    assert not bus.engine.active and not bus.output["oe"]

    bus = make("reset_idle_and_stretch")
    bus.reset(); bus.start(); assert bus.write(0xa5)
    bus.hold(10, scl=1); bus.reset(); bus.stop(); bus.start()
    assert bus.write(0xa4) and bus.write(255); bus.stop()

    bus = make("first_bit_mismatch")
    bus.start(); assert bus.write(0xa5)
    bus.hold(scl=1, sda=0); bus.host(push=255); bus.hold(90)
    assert "data_mismatch" in bus.output["faults"] and not bus.engine.active
    bus.stop(); bus.start(); assert bus.write(0xa4) and bus.write(85); bus.stop()

    for offset in range(5):
        bus = make(f"coincident_start_stop_{offset}")
        bus.hold(scl=0, sda=1); bus.hold(1, scl=1)
        bus.hold(offset + 1, sda=0); bus.hold(8)
        bus.hold(1, scl=0, sda=1); bus.hold(8)
        bus.stop(); bus.start(); assert bus.write(0xa4) and bus.write(0); bus.stop()

    bus = make("abort_pending_timer")
    bus.host(push=85); bus.start(); assert bus.write(0xa5)
    bus.output = bus.engine.step(249, abort=True)
    bus.hold(90); assert not bus.engine.active and not bus.output["oe"]
    bus.stop(); bus.start(); assert bus.write(0xa4) and bus.write(170); bus.stop()

    bus = make("standard_mode", spacing=250)
    bus.start(); assert bus.write(0xa4) and bus.write(170); bus.stop()

    bus = make("receive_only", replace(target(), transmit=False))
    bus.start(); assert not bus.write(0xa5); bus.stop()
    bus.start(); assert bus.write(0xa4) and bus.write(170); bus.stop()

    for limit in (1, 2, 4, 64):
        bus = make(f"malformed_boundaries_watchdog_{limit}", target(watchdog=limit, setup_cycles=13))
        rng = random.Random(19)
        for cycle in range(1200):
            if cycle % 97 == 0:
                bus.reset()
            else:
                bus.hold(1, scl=rng.randrange(2), sda=rng.randrange(2))
        bus.reset()

    for offset in (0, 1, 2, 13, 62, 63, 64, 65):
        bus = make(f"stop_request_pending_timer_{offset}")
        bus.start(); assert bus.write(0xa5)
        bus.hold(scl=1, sda=0)
        bus.host(push=255)
        bus.hold(offset + 1)
        bus.hold(1, sda=1)
        bus.hold(80)
        # A STOP request during stretch is not a wire STOP while resolved SCL
        # is low. After release a stable-high SDA cannot retroactively STOP.
        bus.output = bus.engine.step(255, abort=True)
        bus.hold(8); assert not bus.engine.active and not bus.output["oe"]
        bus.stop(); bus.start(); assert bus.write(0xa4) and bus.write(85); bus.stop()

    for spacing in (3, 4, 5):
        bus = make(f"ninth_clock_spacing_{spacing}", target(setup_cycles=13), spacing)
        bus.start(); assert bus.write(0xa4) and bus.write(0xff); bus.stop()
        bus.host(push=0); bus.start(); assert bus.write(0xa5); assert bus.read() == 0; bus.stop()

    bus = make("reset_mid_header")
    bus.start()
    for bit in (1, 0, 1, 0): bus.hold(scl=0, sda=bit); bus.clock_high()
    bus.reset(); bus.stop(); bus.start(); assert bus.write(0xa4) and bus.write(170); bus.stop()

    bus = make("own_pad_timing_fault_and_recovery")
    bus.start()
    for bit in range(7, -1, -1):
        bus.hold(scl=0, sda=(0xa4 >> bit) & 1); bus.clock_high()
    # A one-cycle low clock returns high before ACK reaches the wire. The
    # synchronized own SDA change must trip, rather than become a self START.
    bus.hold(1, scl=0, sda=1); bus.hold(1, scl=1); bus.hold(10)
    assert "pad_timing" in bus.output["faults"] and not bus.engine.active and not bus.output["oe"]
    bus.stop(); bus.start(); assert bus.write(0xa4) and bus.write(85); bus.stop()

    # Preserve synchronous FIFO decisions when host readiness changes exactly
    # on an actor boundary. No model host API is treated as same-edge bypass.
    bus = make("simultaneous_host_rx_decision")
    bus.start(); assert bus.write(0xa4)
    for byte in (1, 2, 3, 4): assert bus.write(byte)
    for bit in range(7, -1, -1):
        bus.hold(scl=0, sda=(99 >> bit) & 1)
        bus.hold(1, scl=1)
        if bit == 0:
            bus.hold(2)
            assert bus.engine.exchange.phase == "decide"
            assert bus.host(pop=True) == 1
        bus.hold(5)
    bus.hold(scl=0, sda=1); bus.clock_high()
    assert bus.data == 1, "Full-at-decision FIFO must NACK despite concurrent host pop"
    bus.hold(scl=0); bus.stop()
    assert list(bus.engine.rx_fifo) == [2, 3, 4]
    return result


def bench(config, vector_path, count):
    # Diagnostic observations are hierarchy reads in a testbench, not new RTL state.
    return f"""module tb;
reg clk=0,rst_n=0,abort_in=0,push=0,pop=0;
reg [7:0] pins=255,host_data=0;
wire [7:0] rx_head,pad_data,pad_oe,status,rx_value;
wire [2:0] rx_count,tx_count,bit_count;wire active;wire [1:0] ex_status;
motif_core core(clk,rst_n,1'b1,abort_in,pins,1'b{int(config.frame=='falling')},1'b0,1'b{int(config.transmit)},1'b{int(config.lsb_first)},1'b{int(config.validate_start)},1'b{int(config.validate_stop)},
3'd{config.frame_pin},3'd{config.clock_pin},3'd{config.rx_pin},3'd{config.tx_pin},16'd{config.period},16'd{config.watchdog},8'd{config.fill},8'd{config.open_drain},
push,pop,host_data,rx_head,pad_data,pad_oe,rx_count,tx_count,status,active,rx_value,bit_count,
1'b1,1'b{int(config.frame=='two_wire')},1'b{int(config.ack_address)},1'b{int(config.ack_data)},7'd{config.address},ex_status);
integer fd,scan,n,reset_in,pins_in,push_in,pop_in,data_in,abort_value;
integer lv,ri,fa,fires,events,byte_value,rx_push,tx_pop;
initial begin
#4;clk=1;#1;clk=0;rst_n=1;
fd=$fopen("{vector_path.as_posix()}","r");
for(n=0;n<{count};n=n+1)begin
scan=$fscanf(fd,"%d %d %d %d %d %d\\n",pins_in,reset_in,abort_value,push_in,pop_in,data_in);
if(scan!=6)$fatal(1,"bad input vector");
pins=pins_in[7:0];rst_n=!reset_in;abort_in=abort_value[0];push=push_in[0];pop=pop_in[0];host_data=data_in[7:0];#4;
lv=core.levels;ri=core.rising;fa=core.falling;fires=0;events=0;byte_value=-1;
rx_push=core.rx_push && !core.rx_full;tx_pop=core.tx_load && !core.tx_empty;
if(core.pad_timing)events=events|512;
if(!rst_n || core.inhibit)fires=6;
else if(core.acquire)begin fires=5;events=events|1;end
else if(active)begin
if(core.ex_rx_fire)begin fires=fires|8;if(bit_count==7)begin events=events|2;byte_value=core.rx_next;end end
if(core.ex_tx_fire)begin fires=fires|16;if(core.tx_remaining==1)events=events|128;end
if(core.ex_tx_load)fires=fires|16;
if(core.exchange.phase_o==1)begin
if(core.exchange.header)begin fires=fires|64;events=events|(core.exchange.ack_next ? 4:8);end
else if(!core.exchange.ack_next)events=events|16;
end
if((core.exchange.phase_o==2 || core.exchange.phase_o==3) && core.falling[{config.clock_pin}])fires=fires|64;
if(core.exchange.phase_o==6 && !core.tx_empty)fires=fires|64;
if(core.exchange.phase_o==7 && core.timer_event==3)begin fires=fires|64;if(core.mismatch)begin events=events|64;fires=fires|6;end end
if(core.exchange.phase_o==5)begin
if(core.rising[{config.clock_pin}] || core.falling[{config.clock_pin}])fires=fires|64;
if(!core.rising[{config.clock_pin}] && core.falling[{config.clock_pin}] && !core.exchange.controller_ack)events=events|256;
end
if(core.ex_tx_fire && core.tx_remaining==1)fires=fires|64;
if(core.turnaround)events=events|32;
// Timer expiry emits a registered event consumed on the following tick.
if(!core.pending_timer_start && core.timer.running && core.timer.left==1 && core.exchange.phase_next==7)fires=fires|32;
end
clk=1;#1;
if(pad_data!==0 || (pad_oe & ~8'd{config.open_drain})!=0)$fatal(1,"open-drain or ownership violation");
$display("ROW %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",
pins,lv,ri,fa,fires,events,byte_value,rx_value,bit_count,core.tx_value,core.tx_remaining,active,pad_data,pad_oe,
rx_count,tx_count,rx_head,core.exchange.phase_o,core.exchange.ack,core.stretch,core.tripped,status,ex_status,rx_push,tx_pop);
clk=0;#1;
end
$finish;end endmodule
"""


def simulate(source, directory):
    directory.mkdir(parents=True, exist_ok=True)
    tb, output = directory / "tb.sv", directory / "tb.vvp"
    tb.write_text(source, encoding="utf-8")
    command = [os.environ.get("IVERILOG", "iverilog")]
    if os.environ.get("IVERILOG_BASE"):
        command += ["-B", os.environ["IVERILOG_BASE"]]
    command += ["-g2012", "-s", "tb", "-o", str(output)] + [str(p) for p in sorted(Path("src").glob("*.sv"))] + [str(tb)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode: raise RuntimeError(result.stderr)
    result = subprocess.run([os.environ.get("VVP", "vvp"), str(output)], capture_output=True, text=True)
    (directory / "simulation.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode: raise RuntimeError(result.stdout + result.stderr)
    return [dict(zip(FIELDS, map(int, line[4:].split()))) for line in result.stdout.splitlines() if line.startswith("ROW ")]


def write_trace(path, rows):
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def gate1(destination, synthesize=False):
    if PROMOTED.exists():
        verify(PROMOTED)
    version_command = [os.environ.get("IVERILOG", "iverilog")]
    if os.environ.get("IVERILOG_BASE"):
        version_command += ["-B", os.environ["IVERILOG_BASE"]]
    version = subprocess.run(version_command + ["-V"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    result = {"schema_version": 1, "gate": 1, "seed": 20261012, "python": platform.python_version(),
              "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "source_hashes": inventory(), "iverilog": version,
              "working_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()),
              "initial_manifest_sha256": digest(INITIAL.read_bytes()), "cases": [], "divergences": [],
              "host_scheduling": "Synchronous host actions after actor tick; model source unchanged",
              "physical_status": "not established by logical tests"}
    if PROMOTED.exists(): result["promoted_manifest_sha256"] = digest(PROMOTED.read_bytes())
    for name, engine in cases():
        directory = Path("build/generalization/gate1") / name
        directory.mkdir(parents=True, exist_ok=True)
        vectors = directory / "inputs.txt"
        vectors.write_text("".join(" ".join(map(str, a)) + "\n" for a in engine.actions), encoding="utf-8")
        actual = simulate(bench(engine.config, vectors, len(engine.rows)), directory)
        write_trace(directory / "model.jsonl", engine.rows)
        write_trace(directory / "rtl.jsonl", actual)
        if len(actual) != len(engine.rows): raise AssertionError("Incomplete RTL trace")
        for cycle, (expected, observed) in enumerate(zip(engine.rows, actual)):
            differences = {key: [expected[key], observed[key]] for key in FIELDS if expected[key] != observed[key]}
            if differences:
                result["divergences"].append({"case": name, "cycle": cycle, "classification": "unclassified", "differences": differences})
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                raise AssertionError(f"{name} cycle {cycle}: {differences}; see {directory}")
        counts = Counter(m for row in actual for i, m in enumerate(MOTIFS) if row["motifs"] & (1 << i))
        result["cases"].append({"name": name, "configuration": asdict(engine.config), "configuration_sha256": stable_hash(asdict(engine.config)),
                               "cycles": len(actual), "trace_sha256": stable_hash(actual), "motif_firings": dict(counts),
                               "maximum_motif_types_per_cycle": max(row["motifs"].bit_count() for row in actual),
                               "model_rtl_agreement": True})
        print("PASS I2C", name, len(actual), "cycles", flush=True)
    result["classification"] = "MOTIF_I2C_LOGICAL_QUALIFICATION_PASSED"
    result["total_compared_cycles"] = sum(c["cycles"] for c in result["cases"])
    if synthesize:
        from tools.synthesis import synthesize as run_synthesis
        library = Path("build/pdk/sg13cmos5l_stdcell_typ_1p20V_25C.lib")
        synthesis_path = destination.parent / "synthesis.json"
        run_synthesis("tt_um_wellitsabhinav_motif", synthesis_path, library if library.exists() else None)
        data = json.loads(synthesis_path.read_text())
        data.update(allocated_configuration_bits=78, source_sha=result["source_sha"], source_hashes=result["source_hashes"])
        if library.exists():
            data.update(library_sha256=digest(library.read_bytes()), pdk_revision=json.loads(Path("flow-lock.json").read_text())["pdk"]["revision"])
        synthesis_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        result["synthesis"] = {"kind": data["kind"], "cells": data["design"]["num_cells"], "area_um2": data["design"].get("area"),
                               "register_count": data.get("register_count"), "sequential_area_um2": data.get("sequential_area"),
                               "combinational_area_um2": data.get("combinational_area"), "yosys": data["yosys"]}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--synthesize", action="store_true")
    args = parser.parse_args()
    destination = args.output or Path(f"build/generalization/gate{args.gate}/result.json")
    if args.gate == 1:
        gate1(destination, args.synthesize)
    else:
        raise SystemExit("Later gates require a qualified promoted baseline")


if __name__ == "__main__":
    main()
