"""Post-freeze LIN prefix configuration, electrical fixtures and fail-closed gate.

Expected values come from lin_oracle, which does not import this configuration.
Existing v3 runtime, compiler, harness and qualification evidence are immutable.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess

from motif import Config
from motif.transaction import (Entry, RX, DECIDE, RESPOND, HANDOFF, WAIT,
                               TIMER, CHAIN, program, temporal_wait, delay_wait, configuration)
from tools.v3_inventory import verify, sha, MANIFEST
from tools.v3_trace import Recorder, compare_rtl, executed_entries

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = Path("experiments/temporal_qualification/unseen")
BUILD = Path("build/v3_temporal_qualification/unseen")
SELECTION_COMMIT = "5f67d888df07a7e76f814a8df9984394a951f7ac"
SELECTION_SHA = "f3e6d9b7661d61f07b390f0225deb43eeb03e5819dfd2d2191efc628d1a61663"


def selected():
    path = DIRECTORY / "selected_workload.json"
    committed = subprocess.check_output(["git", "show", f"{SELECTION_COMMIT}:{path.as_posix()}"], cwd=ROOT)
    if sha((ROOT / path).read_bytes()) != SELECTION_SHA or sha(committed) != SELECTION_SHA:
        raise ValueError("The committed electrical selection contract changed")
    data = json.loads((ROOT / path).read_text())
    if data["workload"] != "LIN_BREAK_SYNC_ENTRY" or data["configuration_written"] is not False:
        raise ValueError("Selection must precede every unseen configuration")
    if data["frozen_manifest_sha256_lf"] != sha((ROOT / MANIFEST).read_bytes()):
        raise ValueError("Selection identifies another semantic freeze")
    return data


def candidate():
    """Sixteen slots; all timing values belong to this bounded configuration."""
    words = program([
        temporal_wait(0, 27500, next=1, chain=True),
        Entry(WAIT, argument=3, value=1, next=2, flags=CHAIN),
        temporal_wait(0, 3750, "branch", next=3, alternate=8, chain=True),
        Entry(RX, argument=1, next=4, flags=CHAIN),
        Entry(DECIDE, argument=1, mask=1, value=0, next=5, alternate=0, flags=1 | 16),
        Entry(RX, argument=1, next=6, flags=CHAIN),
        Entry(DECIDE, argument=1, mask=1, value=0, next=7, alternate=0, flags=1 | 16 | CHAIN),
        temporal_wait(0, 23749, "branch", next=1, alternate=0, chain=True),
        delay_wait(1250, next=9, chain=True),
        Entry(RX, argument=1, next=10, flags=CHAIN),
        Entry(DECIDE, argument=1, mask=1, value=1, next=11, alternate=0, flags=1 | 16),
        Entry(HANDOFF, argument=2, next=12, flags=1 | CHAIN),
        Entry(RESPOND, argument=3, next=13, flags=CHAIN),
        Entry(HANDOFF, argument=1, next=14, alternate=14, flags=CHAIN),
        Entry(RX, TIMER, argument=8, next=15, flags=CHAIN),
        Entry(DECIDE, argument=1, mask=255, value=85, next=0, alternate=0,
              flags=1 | 2 | 4 | 16 | CHAIN),
    ])
    return Config(program=words, frame="falling", frame_pin=2, clock_pin=1,
                  rx_pin=2, tx_pin=3, sample="timer", period=2500,
                  transmit=True, lsb_first=False, open_drain=8)


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def configure():
    verify()
    selected()
    config = asdict(candidate())
    config["program"] = [f"0x{word:016x}" for word in config["program"]]
    path = DIRECTORY / "config.json"
    if path.exists() and json.loads(path.read_text()) != config:
        raise ValueError("Refusing to overwrite an existing candidate without preserving its attempt")
    write(path, config)
    verify()
    print("CONFIGURED LIN break/sync prefix; selection commit " + SELECTION_COMMIT)


def cases(selection):
    cases = list(selection["acceptance_cases"])
    sweep = selection["deterministic_sweep"]
    for low in sweep["break_lengths_cycles"]:
        for phase in sweep["initial_high_phase_offsets_cycles"]:
            cases.append({"name": f"legal_low{low}_phase{phase}", "kind": "prefix",
                          "low_cycles": low, "sync": sweep["sync"], "phase": phase,
                          "expected_tokens": sweep["expected_tokens_each"]})
    if len(cases) != 34 or len({case["name"] for case in cases}) != 34:
        raise ValueError("Committed unique 34-case set is incomplete")
    return cases


def schedule(selection, case):
    """Raw held wire levels and lifecycle inputs only; no hardware internals."""
    scope = selection["bounded_electrical_scope"]
    bit, delimiter = scope["nominal_bit_cycles"], scope["delimiter_cycles"]
    line = [1] * (selection["host_and_oracle_inputs"]["initial_high_cycles"] + case.get("phase", 0))
    controls = {}

    def hold(level, cycles):
        line.extend([level] * cycles)

    def serial(value, stop=1, glitch=0):
        hold(0, bit)
        for index in range(8):
            level = (value >> index) & 1
            if index == 0 and glitch:
                hold(1, glitch)
                hold(level, bit - glitch)
            else:
                hold(level, bit)
        hold(stop, bit)

    def prefix(low=32500, value=85, stop=1, glitch=0):
        hold(0, low)
        hold(1, delimiter)
        serial(value, stop, glitch)

    kind = case["kind"]
    if kind == "prefix":
        prefix(case["low_cycles"], case["sync"], case.get("stop", 1), case.get("first_data_high_pulse_cycles", 0))
    elif kind == "split":
        for level, cycles in case["segments_cycles"]:
            hold(level, cycles)
        hold(1, delimiter)
        serial(case["sync"])
    elif kind == "unqualified_bytes":
        for value in case["bytes"]:
            serial(value)
            hold(1, case["high_gap_cycles"])
    elif kind == "restart":
        for level, cycles in case["initial_segments_cycles"]:
            hold(level, cycles)
        prefix(case["low_cycles"], case["sync"])
    elif kind == "false_then_valid":
        if case["false_kind"] == "split":
            hold(0, 15000)
            hold(1, 50)
            hold(0, 15000)
            hold(1, delimiter)
            serial(85)
        else:
            prefix(value=0)
        hold(1, case["high_gap_cycles"])
        prefix()
    elif kind == "pending_then_new":
        hold(0, case["first_break_cycles"])
        hold(1, delimiter)
        prefix(case["second_break_cycles"])
    elif kind == "stale_header":
        prefix(value=0)
        hold(1, case["high_gap_cycles"])
        serial(85)
    elif kind == "two_prefixes":
        prefix()
        hold(1, case["high_gap_cycles"])
        prefix()
    elif kind == "lifecycle":
        controls[len(line) + case["control_offset_into_break"]] = case["control"]
        prefix()
    else:
        raise ValueError("Unsupported committed electrical case " + kind)
    return line, controls


def model_case(selection, case, config):
    from tools.lin_oracle import LinContract, reference
    line, controls = schedule(selection, case)
    contract = LinContract.from_selection(selection)
    expected = reference(line, controls, contract)
    if [token.value for token in expected] != case["expected_tokens"]:
        raise ValueError("Fixture disagrees with the committed independent electrical expectation: " + case["name"])
    traffic_end = len(line)
    line.extend([1] * (selection["host_and_oracle_inputs"]["posttraffic_high_cycles"] + 8 * len(expected) + 16))
    # Allow the inclusive latency endpoint, then read from PRE-edge occupancy.
    drain_cycles = [traffic_end + 5001 + 8 * index for index in range(len(expected))]
    engine = Recorder(config)
    for cycle, level in enumerate(line):
        control = controls.get(cycle)
        engine.enabled = control != "disable"
        engine.host_push = 8 <= cycle < 12
        engine.host_data = 255
        engine.host_pop = cycle in drain_cycles
        engine.step(255 if level else 251, reset=control == "reset", abort=control == "abort")
    return engine, line, controls, traffic_end, drain_cycles, expected


def evaluate(rows, line, controls, traffic_end, drain_cycles, selection):
    from tools.lin_oracle import LinContract, FifoSample, HostRead, evaluate as independent
    samples = [FifoSample(cycle=index, count=row["rx_fifo_count"], head=row["rx_head"])
               for index, row in enumerate(rows)]
    reads = [HostRead(cycle=cycle, value=rows[cycle-1]["rx_head"] if rows[cycle-1]["rx_fifo_count"] else None)
             for cycle in drain_cycles]
    return independent(line_levels=line, lifecycle_cuts=controls,
                       contract=LinContract.from_selection(selection), fifo_samples=samples,
                       host_reads=reads, target_oe=[row["oe"] for row in rows], traffic_end=traffic_end)


def run(model_only=False, case_name=None, output=BUILD, publish_receipt=False):
    before = verify()
    selection = selected()
    config = configuration(json.loads((DIRECTORY / "config.json").read_text()))
    all_cases = cases(selection)
    chosen = [case for case in all_cases if case_name is None or case["name"] == case_name]
    if not chosen:
        raise ValueError("Unknown committed case " + str(case_name))
    report = {"schema_version": 3, "workload": selection["workload"], "stage": "unseen",
              "model_only": model_only, "qualification_complete": case_name is None and not model_only,
              "selection_commit": SELECTION_COMMIT, "selection_sha256_lf": SELECTION_SHA,
              "frozen_commit": selection["frozen_commit"], "frozen_manifest_sha256_lf": sha(MANIFEST.read_bytes()),
              "configuration_sha256_lf": sha((DIRECTORY / "config.json").read_bytes()),
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "source_commit_role": "Parent commit when new evaluation files are uncommitted; evaluation_source_hashes identify executed bytes",
              "evaluation_source_hashes": {path: sha(Path(path).read_bytes()) for path in
                  ("tools/lin_unseen.py", "tools/lin_oracle.py", "tests/model/test_lin_oracle.py")},
              "cases": [], "demonstrations": [], "passed": False}
    output = Path(output)
    trace_root = output / sha(json.dumps({"config": report["configuration_sha256_lf"],
                                        "evaluation": report["evaluation_source_hashes"]}, sort_keys=True).encode())[:16]
    failures = []
    try:
        for case in chosen:
            engine, line, controls, traffic_end, drains, expected = model_case(selection, case, config)
            model_oracle = evaluate(engine.rows, line, controls, traffic_end, drains, selection)
            directory = trace_root / case["name"]
            rows = engine.rows if model_only else compare_rtl(engine, directory)
            rtl_oracle = evaluate(rows, line, controls, traffic_end, drains, selection)
            observed = [rows[cycle-1]["rx_head"] if rows[cycle-1]["rx_fifo_count"] else None for cycle in drains]
            result = {"name": case["name"], "cycles": len(rows), "expected": case["expected_tokens"],
                      "observed": observed, "model_oracle": model_oracle.to_dict(), "oracle": rtl_oracle.to_dict(),
                      "model_rtl_agreement": None if model_only else True,
                      "host_fifo_preload": [255] * 4, "configuration_writes_during_traffic": 0,
                      "host_reads_during_traffic": 0, "lifecycle_cuts": controls,
                      "traffic_end": traffic_end, "drain_cycles": drains,
                      "wire_sha256_lf": sha(bytes(line)),
                      "maximum_entries_executed_per_cycle": max(row["executed_count"] for row in rows)}
            if not model_only:
                result["evidence_sha256_lf"] = {name: sha((directory / name).read_bytes()) for name in
                                                ("inputs.txt", "model.jsonl", "rtl.jsonl", "simulation.log")}
                result["trace_directory"] = directory.as_posix()
            report["cases"].append(result)
            passed = model_oracle.passed and rtl_oracle.passed and observed == case["expected_tokens"]
            if not passed:
                failures.append(case["name"])
            print(("PASS" if passed else "FAIL") + " unseen " + case["name"] + " " + str(len(rows)) + " cycles", flush=True)
            if not passed:
                print(json.dumps(rtl_oracle.to_dict(), indent=2), flush=True)
            if not model_only and case["name"] in ("nominal", "one_cycle_high_split", "pending_sync_recovery", "back_to_back"):
                report["demonstrations"].append({**result, "pins": [["LIN RX (normalized)", 2]]})
        report["passed"] = not failures
        report["failed_cases"] = failures
        report["total_compared_cycles"] = 0 if model_only else sum(case["cycles"] for case in report["cases"])
        report["frozen_before_after_identical"] = verify() == before
        report["evaluation_before_after_identical"] = all(sha(Path(path).read_bytes()) == digest
                                for path, digest in report["evaluation_source_hashes"].items())
        if not report["frozen_before_after_identical"]:
            raise RuntimeError("Unseen work changed the frozen semantics")
        if not report["evaluation_before_after_identical"]:
            raise RuntimeError("Evaluation sources changed while the gate was running")
    except BaseException as failure:
        report["failure"] = str(failure)
        report["failure_type"] = type(failure).__name__
        report["passed"] = False
        report["frozen_before_after_identical"] = verify() == before
        raise
    finally:
        write(output / "result.json", report)
        # Content-addressed attempts remain reproducible even after a revised configuration.
        attempt = sha(json.dumps(report, sort_keys=True).encode())
        write(output / "attempts" / (attempt + ".json"), report)
        write(output / "attempts" / (attempt + "_config.json"), asdict(config))
    if failures:
        raise AssertionError("Committed unseen electrical oracle failed: " + ", ".join(failures))
    if report["qualification_complete"]:
        write(DIRECTORY / "result.json", report)
        if publish_receipt:
            write(DIRECTORY / "logical_result.json", report)
        print("PASS unseen logical gate; frozen semantics unchanged; physical eligibility established", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--model-only", action="store_true")
    parser.add_argument("--case")
    parser.add_argument("--publish-receipt", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=BUILD)
    args = parser.parse_args()
    if args.configure:
        configure()
    else:
        run(args.model_only, args.case, args.output_dir, args.publish_receipt)


if __name__ == "__main__":
    main()
