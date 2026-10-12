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
    raise NotImplementedError("RTL qualification is implemented after model feasibility")


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--model-only",action="store_true")
    parser.add_argument("--output",type=Path,default=Path("build/exchange_decomposition/model.json"))
    args=parser.parse_args()
    if args.model_only: model_validation(args.output)
