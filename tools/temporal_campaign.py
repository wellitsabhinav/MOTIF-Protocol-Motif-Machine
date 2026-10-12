"""Fail-closed v3 training/regression/cost gates with portable evidence identities."""
import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

from motif.transaction import configuration
from tools import exchange_decomposition as previous
from tools.unseen_protocol import oracle
from tools.v3_inventory import DIRECTORY, PREREGISTRATION, declared_accounting, report_identity, sha
from tools.v3_trace import Recorder, compare_rtl, MOTIFS

BUILD = Path("build/v3_temporal_qualification")
ROOT = Path(__file__).resolve().parents[1]


def write_report(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(data, indent=2, allow_nan=False) + "\n").encode()
    path.write_bytes(encoded)
    if data.get("passed") is False:
        failures = path.parent / "failures"
        failures.mkdir(parents=True, exist_ok=True)
        preserved = failures / (path.stem + "_" + sha(encoded) + ".json")
        if not preserved.exists():
            preserved.write_bytes(encoded)


def summary(name, engine):
    counts = {motif: sum(bool(row["motifs"] & (1 << index)) for row in engine.rows) for index, motif in enumerate(MOTIFS)}
    return {"name": name, "cycles": len(engine.rows), "configuration": asdict(engine.config),
            "primitive_firings": counts, "maximum_primitive_types_per_cycle": max(row["motifs"].bit_count() for row in engine.rows),
            "ordered_execution_observations": True}


def evidence(directory):
    return {name: sha((Path(directory) / name).read_bytes()) for name in ("inputs.txt", "model.jsonl", "rtl.jsonl")}


def i2c_cases():
    from tools import generalization
    original = generalization.Recorder
    generalization.Recorder = Recorder
    try:
        return generalization.cases()
    finally:
        generalization.Recorder = original


def microwire_case():
    original = previous.Recorder
    previous.Recorder = Recorder
    try:
        return previous.microwire_case()
    finally:
        previous.Recorder = original


def repair_specification():
    workload = json.loads((ROOT / "experiments/exchange_decomposition/third_workload.json").read_text())
    config = configuration(json.loads((ROOT / DIRECTORY / "configurations/one_wire_reset_presence.json").read_text()))
    return workload, config


def extension_cases(workload):
    """Additional preregistered training probes, never relabelled as unseen."""
    ns = workload["core_period_ns"]
    cases = [
        {"name": "startup_interrupted_non_reset", "segments_cycles": [[1, 8], [0, 5], [1, 1], [0, 23999], [1, 60000]], "expected_presence": 0},
        {"name": "restart_then_valid", "segments_cycles": [[1, 8], [0, 5000], [1, 50], [0, 24000], [1, 60000]], "expected_presence": 1},
        {"name": "valid_590us", "segments_us": [[1, 1000], [0, 590], [1, 1000]], "expected_presence": 1},
    ]
    for low in (24000, 29500, 48000):
        for idle in (8, 9):
            cases.append({"name": f"legal_phase_low{low}_idle{idle}", "segments_cycles": [[1, idle], [0, low], [1, 60000]], "expected_presence": 1})
    return cases


def controller_case(workload, case, config):
    if "watchdog_cycles" in case:
        config = replace(config, watchdog=case["watchdog_cycles"])
    engine = Recorder(config)
    controller = []
    reset_cycle = case.get("reset_us_from_start", -1) * 1000 // workload["core_period_ns"]
    segments = case.get("segments_cycles")
    if segments is None:
        segments = []
        for level, duration in case["segments_us"]:
            cycles, remainder = divmod(duration * 1000, workload["core_period_ns"])
            if remainder:
                raise ValueError("Nonintegral training timing")
            segments.append((level, cycles))
    for level, cycles in segments:
        for _ in range(cycles):
            cycle = len(controller)
            previous_row = engine.rows[-1] if engine.rows else {"oe": 0}
            resolved = bool(level) and not bool(previous_row["oe"] & 4)
            engine.step(248 | (7 if resolved else 0), reset=cycle == reset_cycle)
            controller.append(level)
    engine.controller = controller
    engine.controller_case = case
    return engine


def evaluate_repair(engine, rows, workload, case):
    result = oracle(engine.controller, [bool(row["oe"] & 4) for row in rows],
                    [row["data"] for row in rows], [row["oe"] for row in rows], workload, case)
    if case.get("require_timeout") and not any(row["status"] & 64 for row in rows):
        result["passed"] = False
        result["errors"].append("Watchdog timeout absent")
    return result


def repair_cases(include_extra=True):
    workload, config = repair_specification()
    cases = [*workload["cases"], *(extension_cases(workload) if include_extra else [])]
    for case in cases:
        engine = controller_case(workload, case, config)
        yield case["name"], engine, evaluate_repair(engine, engine.rows, workload, case)


def repair_case(name="nominal"):
    workload, config = repair_specification()
    case = next(case for case in [*workload["cases"], *extension_cases(workload)] if case["name"] == name)
    engine = controller_case(workload, case, config)
    return engine, evaluate_repair(engine, engine.rows, workload, case)


def repair(output_dir=BUILD, model_only=False):
    output_dir = Path(output_dir)
    identity = report_identity()
    workload, _ = repair_specification()
    report = {"schema_version": 3, "stage": "model-repair" if model_only else "repair", **identity,
              "training_workload": workload["workload"], "historical_unseen_relabelled_training": True,
              "historical_wire_stimuli_sha256_lf": sha(Path("experiments/exchange_decomposition/third_workload.json").read_bytes()),
              "independent_oracle_source_sha256_lf": sha(Path("tools/unseen_protocol.py").read_bytes()),
              "host_actions_during_traffic": 0, "cases": [], "passed": False}
    try:
        for name, engine, model_result in repair_cases():
            directory = output_dir / "repair" / name
            rows = engine.rows if model_only else compare_rtl(engine, directory)
            oracle_result = evaluate_repair(engine, rows, workload, engine.controller_case)
            case_report = {**summary(name, engine), "oracle": oracle_result,
                           "model_oracle": model_result, "model_rtl_agreement": None if model_only else True,
                           "original_historical_case": name in {case["name"] for case in workload["cases"]}}
            if not model_only:
                case_report["evidence_sha256_lf"] = evidence(directory)
            report["cases"].append(case_report)
            print(("PASS" if oracle_result["passed"] else "FAIL") + " training " + name, flush=True)
        report["total_compared_cycles"] = sum(case["cycles"] for case in report["cases"]) if not model_only else 0
        report["passed"] = all(case["oracle"]["passed"] for case in report["cases"])
    except Exception as failure:
        report["failure"] = str(failure)
        write_report(output_dir / ("model_repair.json" if model_only else "repair.json"), report)
        raise
    write_report(output_dir / ("model_repair.json" if model_only else "repair.json"), report)
    if not report["passed"]:
        raise AssertionError("Preregistered repair training oracle failed; negative evidence retained")
    return report


def run_command(name, command, directory):
    print("RUN " + name, flush=True)
    result = subprocess.run(command, capture_output=True, text=True)
    path = Path(directory) / (name + ".log")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.stdout:
        print(result.stdout[-4000:].rstrip(), flush=True)
    metadata = {"name": name, "command": [Path(command[0]).name, *command[1:]], "exit_code": result.returncode,
                "passed": result.returncode == 0, "log_sha256_lf": sha(path.read_bytes())}
    if result.returncode:
        print(result.stderr[-4000:], flush=True)
    return metadata


def model(output_dir=BUILD):
    report = {"schema_version": 3, "stage": "model", **report_identity()}
    check = run_command("model-tests", [sys.executable, "-m", "pytest", "-q", "tests/model", "tests/adversarial"], output_dir)
    report.update(checks=[check], passed=check["passed"])
    write_report(Path(output_dir) / "model.json", report)
    if not report["passed"]:
        raise AssertionError("Model qualification failed")
    return report


def temporal(output_dir=BUILD, model_only=False):
    from tools.temporal_vectors import cases, verify_expected
    report = {"schema_version": 3, "stage": "temporal", **report_identity(), "cases": [], "passed": False, "model_only": model_only}
    destination = Path(output_dir) / ("model_temporal.json" if model_only else "temporal.json")
    try:
        for name, engine, expectation in cases():
            directory = Path(output_dir) / "temporal" / name
            rows = engine.rows if model_only else compare_rtl(engine, directory)
            result = verify_expected(rows, expectation)
            record = {"name": name, "cycles": len(rows), "oracle": result,
                      "model_rtl_agreement": None if model_only else True}
            if not model_only: record["evidence_sha256_lf"] = evidence(directory)
            report["cases"].append(record)
            print(("PASS" if result["passed"] else "FAIL")+" temporal "+name, flush=True)
            if not result["passed"]: raise AssertionError(result["errors"])
        report["passed"] = True
        report["total_compared_cycles"] = sum(r["cycles"] for r in report["cases"]) if not model_only else 0
    except Exception as failure:
        report["failure"] = str(failure); write_report(destination, report); raise
    write_report(destination, report)
    return report


def regression(output_dir=BUILD, skip_cocotb=False, cocotb_only=False):
    from tools.historical_snapshot import execute, V2_SNAPSHOT
    directory = Path(output_dir)
    report = {"schema_version": 3, "stage": "cocotb" if cocotb_only else "regression", **report_identity(),
              "checks": [], "passed": False, "cocotb_required_before_freeze": True}
    destination = directory / ("cocotb.json" if cocotb_only else "regression.json")
    host_command = [sys.executable, "-m", "tools.host_check", "--output", str(directory / "cocotb.json"), "--build-dir", str(directory / "host")]
    commands = [("cocotb-runtime", host_command)] if cocotb_only else [
        ("all-tests", [sys.executable, "-m", "pytest", "-q"]),
        ("rtl-existing-modes", [sys.executable, "-m", "tools.rtl_check"]),
        ("formal-existing", [sys.executable, "-m", "tools.formal_check"]),
        ("rtl-lint", [os.environ.get("VERILATOR", "verilator"), "--lint-only", "--top-module", "tt_um_wellitsabhinav_motif", "-Wall", *map(str, sorted(Path("src").glob("*.sv")))]),
    ]
    if not cocotb_only and not skip_cocotb:
        commands.append(("cocotb-runtime", host_command))
    try:
        for name, command in commands:
            check = run_command(name, command, directory)
            report["checks"].append(check)
            if not check["passed"]:
                raise AssertionError("Required regression failed: " + name)
        if not cocotb_only:
            snapshot, source = execute("tools.generalization", ["--gate", "1", "--baseline", "v2"])
            old_directory = snapshot / "build/exchange_decomposition/gate1"
            projection = ["pins", "levels", "rising", "falling", "byte", "rx_value", "rx_count", "tx_value", "tx_remaining", "active", "data", "oe",
                          "rx_fifo_count", "tx_fifo_count", "rx_head", "status", "exchange_status", "rx_push", "tx_pop"]
            i2c_reports = []
            for name, engine in i2c_cases():
                actual = compare_rtl(engine, directory / "regression/i2c" / name)
                old_actions = [list(map(int, line.split())) for line in (old_directory / name / "inputs.txt").read_text().splitlines()]
                if old_actions != [action[:6] for action in engine.actions]:
                    raise AssertionError("Historical I2C stimulus changed: " + name)
                with (old_directory / name / "rtl.jsonl").open() as stream:
                    old_rows = [json.loads(line) for line in stream]
                if len(old_rows) != len(actual):
                    raise AssertionError("Historical I2C trace length changed: " + name)
                for cycle, (old, current) in enumerate(zip(old_rows, actual)):
                    if any(old[field] != current[field] for field in projection):
                        raise AssertionError(f"Historical I2C visible regression {name} cycle {cycle}")
                i2c_reports.append({**summary(name, engine), "model_rtl_agreement": True, "historical_v2_visible_equivalence": True,
                                    "evidence_sha256_lf": evidence(directory / "regression/i2c" / name)})
                print("PASS v3 I2C " + name, flush=True)
            if len(i2c_reports) != 48:
                raise AssertionError("Original 48 I2C cases must all remain present")
            report["i2c"] = {"cases": i2c_reports, "total_compared_cycles": sum(case["cycles"] for case in i2c_reports), "historical_source_sha": source}
            engine, oracle_result = microwire_case()
            actual = compare_rtl(engine, directory / "regression/microwire")
            observed = sum((((actual[index]["data"] >> 3) & 1) if actual[index]["oe"] & 8 else 1) << (15 - bit)
                           for bit, index in enumerate(oracle_result["sample_indices"]))
            if observed != 0xa55a or any(row["oe"] & 7 for row in actual):
                raise AssertionError("Microwire independent exact-word/ownership oracle failed")
            report["microwire"] = {**summary("bounded_93LC46_x16_READ", engine), **oracle_result,
                                   "model_rtl_agreement": True, "evidence_sha256_lf": evidence(directory / "regression/microwire")}
        report["passed"] = True
        report["cocotb"] = "passed" if cocotb_only or not skip_cocotb else "separate_passing_receipt_required"
    except Exception as failure:
        report["failure"] = str(failure)
        if cocotb_only and (directory / "cocotb.json").is_file():
            report["runtime_details"] = json.loads((directory / "cocotb.json").read_text())
        write_report(destination, report)
        raise
    if cocotb_only:
        report["runtime_details"] = json.loads((directory / "cocotb.json").read_text())
    write_report(destination, report)
    return report


def synthesis(output_dir=BUILD):
    from tools.synthesis import synthesize, file_hash
    from tools.historical_snapshot import prepare
    directory = Path(output_dir)
    identity = report_identity()
    snapshot, snapshot_sha = prepare()
    lock = json.loads(Path("flow-lock.json").read_text())
    library = Path("build/pdk/sg13cmos5l_stdcell_typ_1p20V_25C.lib")
    if not library.is_file():
        import urllib.request
        library.parent.mkdir(parents=True, exist_ok=True)
        url = "https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/" + lock["pdk"]["revision"] + "/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/lib/" + library.name
        urllib.request.urlretrieve(url, library)
    expected_library_sha = json.loads(Path("experiments/exchange_decomposition/synthesis.json").read_text())["library_sha256"]
    if file_hash(library) != expected_library_sha:
        raise AssertionError("Pinned CMOS5L typical library identity differs from frozen v2")
    report = {"schema_version": 3, "stage": "synthesis", **identity, "passed": False}
    try:
        current = synthesize("tt_um_wellitsabhinav_motif", directory / "synthesis/mapped_v3.json", library)
        old = synthesize("tt_um_wellitsabhinav_motif", directory / "synthesis/mapped_v2.json", library, source_root=snapshot, source_sha=snapshot_sha)
        if current["library_sha256"] != old["library_sha256"] or current["tools"] != old["tools"]:
            raise AssertionError("Matched mapping library/tool identities differ")
        budgets = json.loads(PREREGISTRATION.read_text())["budgets"]
        ratio = current["design"]["area"] / old["design"]["area"]
        accounting = declared_accounting()
        report.update(mapped_v3=current, mapped_v2={**old, "source_sha": snapshot_sha},
                      area_ratio_vs_matched_v2=ratio, area_delta_um2=current["design"]["area"] - old["design"]["area"],
                      sequential_cell_delta=current["sequential_cell_count"] - old["sequential_cell_count"],
                      combinational_cell_delta=current["combinational_cell_count"] - old["combinational_cell_count"],
                      budgets=budgets, accounting=accounting,
                      passed=ratio <= budgets["maximum_area_ratio"] and current["design"]["area"] <= budgets["maximum_mapped_area_um2"])
    except Exception as failure:
        report["failure"] = str(failure)
        write_report(directory / "synthesis.json", report)
        raise
    write_report(directory / "synthesis.json", report)
    write_report(directory / "accounting.json", {"schema_version": 3, "stage": "accounting", **identity, **accounting,
                                               "passed": accounting["configuration_bits"] == budgets["configuration_bits"] and accounting["table_bits"] == budgets["table_bits"] and accounting["delta_declared_register_bits_vs_v2"] <= budgets["maximum_added_declared_state_bits"]})
    if not report["passed"]:
        raise AssertionError("Preregistered mapped area budget exceeded; measured negative retained")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("model", "temporal", "repair", "regression", "synthesis", "freeze-check"), default="regression")
    parser.add_argument("--output-dir", type=Path, default=BUILD)
    parser.add_argument("--model-only", action="store_true")
    parser.add_argument("--skip-cocotb", action="store_true", help="Require a separate source-matched passing cocotb receipt before freeze")
    parser.add_argument("--cocotb-only", action="store_true")
    args = parser.parse_args()
    if args.stage == "model":
        model(args.output_dir)
    elif args.stage == "temporal":
        temporal(args.output_dir, args.model_only)
    elif args.stage == "repair":
        repair(args.output_dir, args.model_only)
    elif args.stage == "synthesis":
        synthesis(args.output_dir)
    elif args.stage == "freeze-check":
        from tools.v3_inventory import verify
        verify()
    else:
        regression(args.output_dir, args.skip_cocotb, args.cocotb_only)


if __name__ == "__main__":
    main()
