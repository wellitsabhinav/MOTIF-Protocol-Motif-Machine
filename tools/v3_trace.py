"""Versioned v3 differential observations; historical v2 traces remain untouched."""
import json
import os
import subprocess
from pathlib import Path

from tools.exchange_decomposition import Recorder as PreviousRecorder
from tools.exchange_decomposition import FIELDS as PREVIOUS_FIELDS
from tools.exchange_decomposition import MOTIFS as PREVIOUS_MOTIFS
from tools.exchange_decomposition import EVENTS as PREVIOUS_EVENTS

MOTIFS = [*PREVIOUS_MOTIFS, "TEMPORAL_QUALIFY"]
EVENTS = [*PREVIOUS_EVENTS, "temporal_start", "temporal_interrupt", "temporal_qualified"]
FIELDS = [*PREVIOUS_FIELDS, "timer_running", "timer_left", "timer_event", "pending_timer_start",
          "temporal_count", "temporal_started", "temporal_done", "executed_count", "executed_pcs"]
TIMER_EVENTS = {None: 0, "start_valid": 1, "invalid_start": 2, "sample": 3, "stop_valid": 4, "invalid_stop": 5}


def mask(names, vocabulary):
    return sum(1 << vocabulary.index(name) for name in set(names) if name in vocabulary)


def executed_entries(row):
    """Decode actual execution order, rather than infer possible configured paths."""
    return [(row["executed_pcs"] >> (4 * index)) & 15 for index in range(row["executed_count"])]


class Recorder(PreviousRecorder):
    def step(self, pins, reset=False, abort=False, requests=None):
        result = super().step(pins, reset, abort, requests)
        exchange = self.exchange
        entries = list(exchange.executed_entries)
        if len(entries) > 4 or any(not 0 <= entry < 16 for entry in entries):
            raise AssertionError("Execution diagnostics exceed the frozen four-stage bound")
        observed = self.rows[-1]
        observed["motifs"] = mask(["SHIFT_TX" if name == "SHIFT_TX_LOAD" else name for name in result["fires"]], MOTIFS)
        observed["events"] = mask(result["events"], EVENTS)
        observed.update(timer_running=int(self.timer.running), timer_left=self.timer.left if self.timer.running else 0,
                        timer_event=TIMER_EVENTS[self.pending], pending_timer_start=int(self.pending_timer_start),
                        temporal_count=exchange.temporal_count, temporal_started=int(exchange.temporal_started),
                        temporal_done=int(exchange.temporal_done), executed_count=len(entries),
                        executed_pcs=sum(entry << (4 * index) for index, entry in enumerate(entries)))
        self.actions[-1].append(int(self.enabled))
        return result


def bench(config, vectors, count):
    packed = sum(word << (64 * index) for index, word in enumerate(config.program))
    observations = ["pins", "lv", "ri", "fa", "fires", "events", "byte_value", "core.field_value", "core.field_count" if config.exchange else "bit_count", "core.tx_value",
                    "core.tx_remaining", "active", "pad_data", "pad_oe", "rx_count", "tx_count", "rx_head", "core.exchange.pc_o", "core.exchange.halted_o",
                    "core.exchange.pending_field_o", "core.exchange.desired_role_o", "core.exchange.role_o", "core.exchange.accepted_o", "core.exchange.response_o",
                    "core.exchange.drive_enable_o", "core.exchange.drive_value_o", "core.exchange.hold_o", "core.tripped", "status", "ex_status", "rx_push", "tx_pop",
                    "core.timer.running", "core.timer.running ? core.timer.left : 0", "core.timer_event", "core.pending_timer_start",
                    "core.exchange.temporal_count_o", "core.exchange.temporal_started_o", "core.exchange.temporal_done_o", "executed_count", "executed_pcs"]
    return f'''module tb;
reg clk=0,rst_n=0,abort_in=0,push=0,pop=0,enabled=1;
reg [7:0] pins=255,host_data=0;
wire [7:0] rx_head,pad_data,pad_oe,status,rx_value;
wire [2:0] rx_count,tx_count,bit_count,ex_status;wire active;
motif_core core(clk,rst_n,enabled,abort_in,pins,1'b{int(config.frame == 'falling')},1'b{int(config.sample == 'timer')},1'b{int(config.transmit)},1'b{int(config.lsb_first)},1'b{int(config.validate_start)},1'b{int(config.validate_stop)},
3'd{config.frame_pin},3'd{config.clock_pin},3'd{config.rx_pin},3'd{config.tx_pin},16'd{config.period},16'd{config.watchdog},8'd{config.fill},8'd{config.open_drain},
push,pop,host_data,rx_head,pad_data,pad_oe,rx_count,tx_count,status,active,rx_value,bit_count,
1'b{int(config.exchange)},1'b{int(config.frame == 'two_wire')},1'b{int(config.frame_active_high)},1'b{int(config.hold_clock)},1'b{int(config.pad_timing_check)},1024'h{packed:0256x},ex_status);
integer fd,scan,n,reset_in,pins_in,push_in,pop_in,data_in,abort_value,enabled_in;
integer lv,ri,fa,fires,events,byte_value,rx_push,tx_pop,executed_count,executed_pcs;
reg [63:0] next_instruction;
initial begin
#4;clk=1;#1;clk=0;rst_n=1;
fd=$fopen("{vectors.as_posix()}","r");
for(n=0;n<{count};n=n+1)begin
scan=$fscanf(fd,"%d %d %d %d %d %d %d\\n",pins_in,reset_in,abort_value,push_in,pop_in,data_in,enabled_in);
if(scan!=7)$fatal(1,"bad v3 input vector");
pins=pins_in[7:0];rst_n=!reset_in;abort_in=abort_value[0];push=push_in[0];pop=pop_in[0];host_data=data_in[7:0];enabled=enabled_in[0];#4;
lv=core.levels;ri=core.rising;fa=core.falling;fires=0;events=0;byte_value=-1;
rx_push=core.rx_push && !core.rx_full;tx_pop=core.tx_load && !core.tx_empty;
executed_count=core.exchange.executed_count_o;executed_pcs=core.exchange.executed_pcs_o;
if(core.pad_timing)events=events|65536;
if(!rst_n || core.inhibit || core.end_sample)fires=6;
else if(core.acquire)begin
fires=5|(core.primitive_fires & 1024);events=events|1|core.primitive_events;
if(!1'b{int(config.exchange)} && 1'b{int(config.transmit)})fires=fires|16;
end
else if(active)begin
if(1'b{int(config.exchange)})begin
fires=core.primitive_fires;events=events|core.primitive_events;
if(core.field_complete)byte_value=core.completed_field;
end else begin
if(core.rx_fire)fires=fires|8;
if(core.tx_fire || core.tx_load)fires=fires|16;
if(core.rx_terminal)byte_value=core.rx_next;
if(core.tx_terminal)events=events|2048;
end
if(core.mismatch || core.composition_fault || core.transaction_end)fires=fires|6;
end
if(rst_n && !core.timer.start_i && !core.timer.clear_i && core.timer.running && core.timer.left==1)fires=fires|32;
clk=1;#1;
$display("ROW {' '.join(['%0d'] * len(FIELDS))}",{','.join(observations)});
clk=0;#1;
end
$finish;end endmodule
'''


def compare_rtl(engine, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    vectors = directory / "inputs.txt"
    vectors.write_text("".join(" ".join(map(str, action)) + "\n" for action in engine.actions), encoding="utf-8", newline="\n")
    source, output = directory / "tb.sv", directory / "tb.vvp"
    source.write_text(bench(engine.config, vectors, len(engine.rows)), encoding="utf-8", newline="\n")
    command = [os.environ.get("IVERILOG", "iverilog")]
    if os.environ.get("IVERILOG_BASE"):
        command.extend(["-B", os.environ["IVERILOG_BASE"]])
    command.extend(["-g2012", "-s", "tb", "-o", str(output)])
    command.extend(str(path) for path in sorted(Path("src").glob("*.sv")))
    command.append(str(source))
    compiled = subprocess.run(command, capture_output=True, text=True)
    (directory / "compile.log").write_text(compiled.stdout + compiled.stderr, encoding="utf-8")
    if compiled.returncode:
        raise RuntimeError("V3 elaboration failed: " + compiled.stderr[-4000:])
    simulated = subprocess.run([os.environ.get("VVP", "vvp"), str(output)], capture_output=True, text=True)
    (directory / "simulation.log").write_text(simulated.stdout + simulated.stderr, encoding="utf-8")
    if simulated.returncode:
        raise RuntimeError("V3 simulation failed: " + (simulated.stdout + simulated.stderr)[-4000:])
    actual = [dict(zip(FIELDS, map(int, line[4:].split()))) for line in simulated.stdout.splitlines() if line.startswith("ROW ")]
    for filename, rows in (("model.jsonl", engine.rows), ("rtl.jsonl", actual)):
        with (directory / filename).open("w", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
    if len(actual) != len(engine.rows):
        raise AssertionError("Incomplete v3 differential trace")
    for cycle, (expected, observed) in enumerate(zip(engine.rows, actual)):
        differences = {field: [expected[field], observed[field]] for field in FIELDS if expected[field] != observed[field]}
        if differences:
            failure = {"case": directory.name, "cycle": cycle, "differences": differences,
                       "window": actual[max(0, cycle - 4):cycle + 5]}
            (directory / "divergence.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
            raise AssertionError(f"V3 model/RTL divergence {directory.name} cycle {cycle}: {differences}")
    return actual
