"""V2 qualification; oracle/stimulus is outside the runtime vocabulary."""
import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from motif import Config, Engine
from motif.transaction import Entry, program, RX, DECIDE, RESPOND, HANDOFF, WAIT, TX, HALT, RISING, CHAIN
from tools.byte_exchange_falsification import oracle

DIRECTORY = Path("experiments/exchange_decomposition")
MOTIFS = ["FRAME_ACQUIRE", "FRAME_RELEASE", "RESET_COUNTER", "SHIFT_RX_COUNT", "SHIFT_TX", "TIMED_SAMPLE",
          "FIELD_DECISION", "DIRECTION_HANDOFF", "BOUNDARY_RESPONSE", "WAIT_POLICY"]
EVENTS = ["frame_start", "field_complete", "decision_accept", "decision_reject", "response_emit", "response_release",
          "response_capture", "response_continue", "response_terminate", "wait_complete", "turnaround_begin",
          "tx_complete", "transaction_halt", "data_mismatch", "composition_fault", "frame_terminate", "pad_timing_fault"]
FIELDS = ["pins", "levels", "rising", "falling", "motifs", "events", "byte", "rx_value", "rx_count", "tx_value",
          "tx_remaining", "active", "data", "oe", "rx_fifo_count", "tx_fifo_count", "rx_head", "pc", "halted",
          "pending_field", "desired_role", "role", "accepted", "response", "drive_enable", "drive_value", "hold",
          "guardian_tripped", "status", "exchange_status", "rx_push", "tx_pop"]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def mask(names, vocabulary):
    return sum(1 << vocabulary.index(n) for n in set(names) if n in vocabulary)


class Recorder(Engine):
    def __init__(self, config):
        super().__init__(config)
        self.rows, self.actions = [], []
        self.host_push = self.host_pop = False
        self.host_data = 0

    def step(self, pins, reset=False, abort=False, requests=None):
        if requests is not None:
            raise ValueError("Oracle cannot inject hardware behavior")
        old_rx, old_tx = len(self.rx_fifo), len(self.tx_fifo)
        row = super().step(pins, reset, abort)
        rx_push = len(self.rx_fifo) > old_rx and not reset
        tx_pop = len(self.tx_fifo) < old_tx and not reset
        if not reset:
            if self.host_pop and old_rx:
                self.rx_fifo.popleft()
            if self.host_push and (old_tx < self.fifo_depth or tx_pop):
                self.tx_fifo.append(self.host_data)
        faults = set(row["faults"])
        status = int(bool(faults & {"ownership", "drive_high", "conflict"})) | (int("rx_overflow" in faults) << 3) | (int("tx_underflow" in faults) << 4) | (int(bool(faults & {"invalid_start", "invalid_stop"})) << 5) | (int("timeout" in faults) << 6)
        ex = self.exchange
        fires = ["SHIFT_TX" if f == "SHIFT_TX_LOAD" else f for f in row["fires"]]
        values = [pins, row["levels"], row["rising"], row["falling"], mask(fires, MOTIFS), mask(row["events"], EVENTS),
                  row["byte"] if row["byte"] is not None else -1, row["rx_value"], row["rx_count"], row["tx_value"], row["tx_remaining"],
                  int(row["active"]), row["data"], row["oe"], len(self.rx_fifo), len(self.tx_fifo), self.rx_fifo[0] if self.rx_fifo else 0,
                  ex.pc, int(ex.halted), ex.pending_field, ex.desired_role, ex.role, int(ex.accepted), int(ex.response),
                  int(ex.drive_enable), int(ex.drive_value), int(ex.hold), int(self.guardian.tripped), status,
                  int("data_mismatch" in faults) | (int("pad_timing" in faults) << 1) | (int("composition_fault" in faults) << 2), int(rx_push), int(tx_pop)]
        self.rows.append(dict(zip(FIELDS, values)))
        self.actions.append([pins, int(reset), int(abort), int(self.host_push), int(self.host_pop), self.host_data])
        self.host_push = self.host_pop = False
        return row


def i2c_cases():
    from tools import generalization as previous
    previous.Recorder = Recorder
    return previous.cases()


def microwire_config():
    words = program([
        Entry(RX, RISING, 1, argument=9),
        Entry(DECIDE, next=2, alternate=15, argument=2, value=384, mask=511, flags=1 | 16 | CHAIN),
        Entry(RESPOND, next=3, argument=0, value=0, flags=CHAIN),
        Entry(WAIT, next=4, flags=CHAIN),
        Entry(HANDOFF, RISING, 5, argument=2),
        Entry(TX, RISING, 6, flags=1),
        Entry(HANDOFF, RISING, 7, argument=2),
        Entry(TX, RISING, 8, flags=1),
        Entry(HALT, flags=2),
    ])
    return Config(program=words, frame_active_high=True, tx_pin=3, period=13)


def microwire_case():
    workload = json.loads(Path("experiments/generalization/microwire_workload.json").read_text())
    command, expected = oracle(workload["memory_address"], workload["response_word"])
    engine = Recorder(microwire_config())
    cs, clock, data = 0, 0, 1
    indices = []

    def hold(cycles=32, new_cs=None, new_clock=None, new_data=None):
        nonlocal cs, clock, data
        if new_cs is not None: cs = new_cs
        if new_clock is not None: clock = new_clock
        if new_data is not None: data = new_data
        for _ in range(cycles):
            do = ((engine.rows[-1]["data"] >> 3) & 1) if engine.rows and engine.last_oe & 8 else 1
            engine.step(240 | cs | (clock << 1) | (data << 2) | (do << 3))

    hold(16)
    for byte in (workload["response_word"] >> 8, workload["response_word"] & 255):
        engine.host_push, engine.host_data = True, byte
        hold(1)
    hold(new_cs=1)
    for i, bit in enumerate(command):
        hold(new_clock=0, new_data=bit)
        hold(new_clock=1)
        if i == len(command) - 1:
            assert engine.last_oe & 8 and not engine.rows[-1]["data"] & 8, "Frozen oracle requires dummy zero"
        hold(new_clock=0, new_data=1 if i == 8 else bit)
    for bit in expected:
        hold(new_clock=1, new_data=1)
        indices.append(len(engine.rows) - 1)
        observed = ((engine.rows[-1]["data"] >> 3) & 1) if engine.last_oe & 8 else 1
        assert observed == bit, (len(indices)-1, bit, observed)
        old_output = engine.rows[-1]["data"] & 8
        hold(new_clock=0)
        assert engine.rows[-1]["data"] & 8 == old_output, "DO must not advance on falling clock"
    hold(new_cs=0)
    assert not engine.last_oe and not engine.active
    assert all(not row["oe"] & 7 for row in engine.rows), "Controller owns CS, CLK and DI"
    observed = [((engine.rows[i]["data"] >> 3) & 1) if engine.rows[i]["oe"] & 8 else 1 for i in indices]
    assert observed == expected
    return engine, {"command_bits": command, "expected_word_hex": "0xa55a", "observed_word_hex": hex(sum(bit << (15-i) for i, bit in enumerate(observed))), "dummy_zero": True, "clock_owned_by_controller": True, "output_event": "rising", "sample_indices": indices}


def summary(name, engine):
    return {"name": name, "cycles": len(engine.rows), "configuration": asdict(engine.config), "trace_sha256": digest(engine.rows),
            "primitive_firings": {n: sum(bool(r["motifs"] & (1 << i)) for r in engine.rows) for i, n in enumerate(MOTIFS)},
            "maximum_primitive_types_per_cycle": max(r["motifs"].bit_count() for r in engine.rows)}


def primitive_probes():
    """Synthetic contract probes; these are never counted as protocol users."""
    result=[]
    for length in (1,8,9,16):
        for lsb in (False,True):
            field=((1<<length)-1)//3 | (1<<(length-1))
            words=program([
                Entry(RX,RISING,1,argument=length),
                Entry(DECIDE,next=2,alternate=15,argument=3|((length-1)<<2),value=field,mask=(1<<length)-1,flags=1|8|16|CHAIN),
                Entry(RESPOND,next=3,flags=CHAIN),
                Entry(WAIT,next=4,flags=CHAIN),
                Entry(HANDOFF,RISING,5),
                Entry(TX,RISING,6,flags=1),
                Entry(HALT,flags=2),
            ])
            engine=Recorder(Config(program=words,frame_active_high=True,lsb_first=lsb,period=13))
            cs=clock=0;data=1
            def hold(cycles=16):
                for _ in range(cycles):
                    do=(engine.rows[-1]["data"]>>3)&1 if engine.rows and engine.last_oe&8 else 1
                    engine.step(240|cs|(clock<<1)|(data<<2)|(do<<3))
            hold();engine.host_push=True;engine.host_data=0xa6;hold(1)
            cs=1;hold()
            indices=range(length) if lsb else range(length-1,-1,-1)
            for index in indices:
                clock=0;data=(field>>index)&1;hold();clock=1;hold();clock=0;hold()
            assert engine.exchange.accepted and engine.exchange.pending_field==field
            response_indices=range(8) if lsb else range(7,-1,-1)
            for index in response_indices:
                clock=1;hold()
                assert engine.last_oe&8 and ((engine.rows[-1]["data"]>>3)&1)==((0xa6>>index)&1)
                clock=0;hold()
            cs=0;hold()
            assert not engine.last_oe
            result.append((f"field_{length}_{'lsb' if lsb else 'msb'}",engine))
    return result


def model_validation(destination):
    cases = i2c_cases()
    mic, oracle_result = microwire_case()
    result = {"schema_version": 2, "stage": "independent_model_feasibility", "source_sha": subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
              "preregistration_sha256": hashlib.sha256((DIRECTORY / "preregistered_architecture.json").read_bytes().replace(b"\r\n",b"\n")).hexdigest(),
              "model_hashes": {p.as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n",b"\n")).hexdigest() for p in sorted(Path("motif").rglob("*.py"))},
              "i2c_cases": [summary(n,e) for n,e in cases], "i2c_total_cycles": sum(len(e.rows) for _,e in cases),
              "microwire": {**summary("bounded_93LC46_x16_READ",mic), **oracle_result}, "third_protocol": "UNSELECTED"}
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+"\n")
    print("PASS independent model:",len(cases),"I2C cases",result["i2c_total_cycles"],"cycles; Microwire",oracle_result["observed_word_hex"])
    return result


def run(gate, output=None, synthesize=False):
    destination=Path(output) if output else Path(f"build/exchange_decomposition/gate{gate}/result.json")
    if gate==1:
        from tools.legacy_baseline import run as legacy_run, SNAPSHOT
        legacy_run(1)
        cases=i2c_cases()
        reports=[]
        projection=["pins","levels","rising","falling","byte","rx_value","rx_count","tx_value","tx_remaining","active","data","oe",
                    "rx_fifo_count","tx_fifo_count","rx_head","status","rx_push","tx_pop"]
        for name,engine in cases:
            directory=Path("build/exchange_decomposition/gate1")/name
            actual=compare_rtl(engine,directory)
            legacy_directory=Path("build/legacy")/SNAPSHOT/"build/generalization/gate1"/name
            old_actions=[list(map(int,line.split())) for line in (legacy_directory/"inputs.txt").read_text().splitlines()]
            if old_actions!=engine.actions: raise AssertionError(f"Changed historical stimulus: {name}")
            old_rows=[json.loads(line) for line in (legacy_directory/"rtl.jsonl").read_text().splitlines()]
            for cycle,(old,new) in enumerate(zip(old_rows,actual)):
                differences={key:[old[key],new[key]] for key in projection if old[key]!=new[key]}
                if old["exchange_status"]!=(new["exchange_status"] & 3): differences["exchange_status"]=[old["exchange_status"],new["exchange_status"]]
                if differences: raise AssertionError(f"Legacy external regression {name} cycle {cycle}: {differences}")
            reports.append({**summary(name,engine),"model_rtl_agreement":True,"legacy_external_equivalence":True})
            print("PASS v2 I2C",name,len(actual),"cycles",flush=True)
        probes=[]
        for name,engine in primitive_probes():
            compare_rtl(engine,Path("build/exchange_decomposition/primitives")/name)
            probes.append({**summary(name,engine),"model_rtl_agreement":True,"protocol_user":False})
            print("PASS generic field/direction probe",name,flush=True)
        result={"schema_version":2,"gate":1,"classification":"MOTIF_I2C_LOGICAL_QUALIFICATION_PASSED", "cases":reports,"primitive_probes":probes,
                "total_compared_cycles":sum(r["cycles"] for r in reports),"legacy_snapshot":SNAPSHOT}
    elif gate==2:
        engine,oracle_result=microwire_case()
        actual=compare_rtl(engine,Path("build/exchange_decomposition/gate2/microwire"))
        expected=oracle(0,0xa55a)[1]
        observed=[((actual[i]["data"]>>3)&1) if actual[i]["oe"]&8 else 1 for i in oracle_result["sample_indices"]]
        if observed!=expected: raise AssertionError("Frozen Microwire oracle failed in RTL")
        result={"schema_version":2,"gate":2,"classification":"MOTIF_EXCHANGE_DECOMPOSITION_I2C_MICROWIRE_REUSE_CONFIRMED",
                "microwire":{**summary("bounded_93LC46_x16_READ",engine),**oracle_result,"model_rtl_agreement":True},
                "new_semantics_after_preregistration":False,"clock_drive_cycles":sum(bool(r["oe"]&2) for r in actual)}
        print("PASS v2 Microwire A55A, independent oracle and full model/RTL trace",flush=True)
    else:
        raise SystemExit("Gate 3 requires frozen v2 and a subsequently committed selection")
    result["source_sha"]=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    result["preregistration_sha256"]=hashlib.sha256((DIRECTORY/"preregistered_architecture.json").read_bytes().replace(b"\r\n",b"\n")).hexdigest()
    result["rtl_hashes"]={p.as_posix():hashlib.sha256(p.read_bytes().replace(b"\r\n",b"\n")).hexdigest() for p in sorted(Path("src").glob("*.sv"))}
    if synthesize:
        from tools.synthesis import synthesize as synthesis
        synthesis("tt_um_wellitsabhinav_motif",destination.parent/"synthesis.json")
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+"\n")
    return result


def bench(config,vectors,count):
    packed=sum(word<<(64*i) for i,word in enumerate(config.program))
    observations=["pins","lv","ri","fa","fires","events","byte_value","core.field_value","core.field_count","core.tx_value",
                  "core.tx_remaining","active","pad_data","pad_oe","rx_count","tx_count","rx_head","core.exchange.pc_o","core.exchange.halted_o",
                  "core.exchange.pending_field_o","core.exchange.desired_role_o","core.exchange.role_o","core.exchange.accepted_o","core.exchange.response_o",
                  "core.exchange.drive_enable_o","core.exchange.drive_value_o","core.exchange.hold_o","core.tripped","status","ex_status","rx_push","tx_pop"]
    return f'''module tb;
reg clk=0,rst_n=0,abort_in=0,push=0,pop=0;
reg [7:0] pins=255,host_data=0;
wire [7:0] rx_head,pad_data,pad_oe,status,rx_value;
wire [2:0] rx_count,tx_count,bit_count,ex_status;wire active;
motif_core core(clk,rst_n,1'b1,abort_in,pins,1'b{int(config.frame=='falling')},1'b{int(config.sample=='timer')},1'b{int(config.transmit)},1'b{int(config.lsb_first)},1'b{int(config.validate_start)},1'b{int(config.validate_stop)},
3'd{config.frame_pin},3'd{config.clock_pin},3'd{config.rx_pin},3'd{config.tx_pin},16'd{config.period},16'd{config.watchdog},8'd{config.fill},8'd{config.open_drain},
push,pop,host_data,rx_head,pad_data,pad_oe,rx_count,tx_count,status,active,rx_value,bit_count,
1'b1,1'b{int(config.frame=='two_wire')},1'b{int(config.frame_active_high)},1'b{int(config.hold_clock)},1'b{int(config.pad_timing_check)},1024'h{packed:0256x},ex_status);
integer fd,scan,n,reset_in,pins_in,push_in,pop_in,data_in,abort_value;
integer lv,ri,fa,fires,events,byte_value,rx_push,tx_pop;
reg [63:0] next_instruction;
initial begin
#4;clk=1;#1;clk=0;rst_n=1;
fd=$fopen("{vectors.as_posix()}","r");
for(n=0;n<{count};n=n+1)begin
scan=$fscanf(fd,"%d %d %d %d %d %d\\n",pins_in,reset_in,abort_value,push_in,pop_in,data_in);
if(scan!=6)$fatal(1,"bad input vector");
pins=pins_in[7:0];rst_n=!reset_in;abort_in=abort_value[0];push=push_in[0];pop=pop_in[0];host_data=data_in[7:0];#4;
lv=core.levels;ri=core.rising;fa=core.falling;fires=0;events=0;byte_value=-1;
rx_push=core.rx_push && !core.rx_full;tx_pop=core.tx_load && !core.tx_empty;
if(core.pad_timing)events=events|65536;
if(!rst_n || core.inhibit)fires=6;
else if(core.acquire)begin fires=5;events=events|1;end
else if(active)begin
fires=core.primitive_fires;events=events|core.primitive_events;
if(core.field_complete)byte_value=core.completed_field;
if(core.mismatch || core.composition_fault || core.transaction_end)fires=fires|6;
next_instruction=core.exchange.program_i[core.exchange.pc_next*64 +: 64];
if(!core.pending_timer_start && core.timer.running && core.timer.left==1 &&
   (1'b{int(config.sample=='timer')} || (next_instruction[2:0]==4 && next_instruction[14:13]==2 && !core.exchange.halted_next)))fires=fires|32;
end
clk=1;#1;
$display("ROW {' '.join(['%0d']*len(FIELDS))}",{','.join(observations)});
clk=0;#1;
end
$finish;end endmodule
'''


def compare_rtl(engine,directory):
    directory.mkdir(parents=True,exist_ok=True)
    vectors=directory/"inputs.txt"
    vectors.write_text("".join(" ".join(map(str,a))+"\n" for a in engine.actions))
    tb=directory/"tb.sv";out=directory/"tb.vvp"
    tb.write_text(bench(engine.config,vectors,len(engine.rows)))
    command=[os.environ.get("IVERILOG","iverilog")]
    if os.environ.get("IVERILOG_BASE"): command.extend(["-B",os.environ["IVERILOG_BASE"]])
    command.extend(["-g2012","-s","tb","-o",str(out)])
    command.extend(str(p) for p in sorted(Path("src").glob("*.sv")))
    command.append(str(tb))
    compiled=subprocess.run(command,capture_output=True,text=True)
    if compiled.returncode: raise RuntimeError(compiled.stderr)
    simulation=subprocess.run([os.environ.get("VVP","vvp"),str(out)],capture_output=True,text=True)
    (directory/"simulation.log").write_text(simulation.stdout+simulation.stderr)
    if simulation.returncode: raise RuntimeError(simulation.stdout[-2000:]+simulation.stderr)
    actual=[dict(zip(FIELDS,map(int,line[4:].split()))) for line in simulation.stdout.splitlines() if line.startswith("ROW ")]
    for filename,rows in (("model.jsonl",engine.rows),("rtl.jsonl",actual)):
        (directory/filename).write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows))
    if len(actual)!=len(engine.rows): raise AssertionError("Incomplete v2 trace")
    for cycle,(expected,observed) in enumerate(zip(engine.rows,actual)):
        differences={key:[expected[key],observed[key]] for key in FIELDS if expected[key]!=observed[key]}
        if differences: raise AssertionError(f"Model/RTL divergence {directory.name} cycle {cycle}: {differences}")
    return actual


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--model-only",action="store_true")
    parser.add_argument("--gate",type=int,choices=(1,2,3))
    parser.add_argument("--check-preregistration",action="store_true")
    parser.add_argument("--freeze",action="store_true")
    parser.add_argument("--check-freeze",action="store_true")
    parser.add_argument("--accounting",action="store_true")
    parser.add_argument("--output",type=Path,default=Path("build/exchange_decomposition/model.json"))
    args=parser.parse_args()
    if args.model_only: model_validation(args.output)
    elif args.gate: run(args.gate,args.output)
    elif args.check_preregistration:
        path=DIRECTORY/"preregistered_architecture.json"
        historical=subprocess.check_output(["git","show","d3ca35e2221f8e7654f4c42fa79ab7992e8ee8d8:"+path.as_posix()])
        if path.read_bytes().replace(b"\r\n",b"\n")!=historical: raise SystemExit("Preregistration changed")
        print("PASS immutable preregistration")
    elif args.freeze:
        from tools.v2_inventory import freeze
        freeze()
    elif args.check_freeze:
        from tools.v2_inventory import verify
        verify();print("PASS frozen v2 implementation and trace compiler")
    elif args.accounting:
        from tools.v2_inventory import accounting
        result=accounting()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+"\n")
