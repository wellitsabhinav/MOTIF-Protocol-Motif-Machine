"""Reproduce the v2 configuration-only temporal audit from immutable sources.

The worker imports the archived v2 model, trace compiler and oracle. Current v3
model/RTL edits therefore cannot change the comparison baseline. Generated
sources, vectors and full traces stay under build/; only concise evidence is
selected for Git by the campaign owner.
"""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PINNED_V2 = "490a50c3e03f1be96784fd27f9d64b718c2aa5cc"
EVIDENCE = ROOT / "experiments" / "temporal_qualification"


def archived_source(destination):
    archive = subprocess.check_output(
        ["git", "archive", "--format=zip", PINNED_V2], cwd=ROOT
    )
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for member in bundle.infolist():
            (destination / member.filename).resolve().relative_to(destination.resolve())
        bundle.extractall(destination)
    return destination


def worker(options):
    # The script itself lives in the current checkout; imports must come from
    # the frozen archive, which is the worker's explicit working directory.
    sys.path.insert(0, str(Path.cwd()))
    from tools.exchange_decomposition import Recorder, compare_rtl, digest, summary
    from tools.unseen_protocol import check_selection, controller_case, oracle
    from tools.v2_inventory import verify, sha
    from motif.transaction import configuration

    before = verify()
    workload = check_selection()
    cfg = configuration(json.loads(options.configuration.read_text()))
    probes = json.loads(options.probes.read_text())
    if probes["core_period_ns"] != workload["core_period_ns"]:
        raise ValueError("Probe clock differs from the immutable oracle clock")

    def probe_case(case):
        engine, controller = Recorder(cfg), []
        for level, cycles in case["segments_cycles"]:
            if level not in (0, 1) or type(cycles) is not int or cycles < 1:
                raise ValueError("Probe segments require binary levels and positive cycles")
            for _ in range(cycles):
                cycle = len(controller)
                engine.host_push, engine.host_data = 8 <= cycle < 12, 255
                resolved = bool(level) and not bool(engine.last_oe & 4)
                engine.step(248 | (7 if resolved else 0))
                controller.append(level)
        return engine, controller

    cases = [(case, True) for case in workload["cases"]]
    cases.extend((case, False) for case in probes["cases"])
    reports = []
    options.output.mkdir(parents=True, exist_ok=True)
    for case, original in cases:
        engine, controller = (
            controller_case(workload, case, cfg) if original else probe_case(case)
        )
        directory = options.output / case["name"]
        actual = engine.rows if options.model_only else compare_rtl(engine, directory)
        result = oracle(
            controller, [bool(row["oe"] & 4) for row in actual],
            [row["data"] for row in actual], [row["oe"] for row in actual],
            workload, case,
        )
        if case.get("require_timeout") and not any(row["status"] & 64 for row in actual):
            result["passed"] = False
            result["errors"].append("Watchdog timeout absent")
        report = {
            **summary(case["name"], engine), "stimulus": case,
            "original_case": original, "expected_oracle_pass": original,
            "oracle": result,
            "model_rtl_agreement": None if options.model_only else True,
        }
        if not options.model_only:
            report["evidence_sha256_lf"] = {
                name: sha((directory / name).read_bytes())
                for name in ("inputs.txt", "model.jsonl", "rtl.jsonl", "simulation.log")
            }
        if "windows_cycles" in case:
            report["trace_windows"] = {
                name: [{"cycle": cycle, "controller_level": controller[cycle], **actual[cycle]}
                       for cycle in range(start, end)]
                for name, (start, end) in case["windows_cycles"].items()
            }
        reports.append(report)
        (options.output / "partial_result.json").write_text(
            json.dumps(reports, indent=2) + "\n", newline="\n"
        )
        label = "PASS" if result["passed"] else "EXPECTED_NEGATIVE" if not original else "FAIL"
        print(f"{label} v2 composition {case['name']}: {len(actual)} cycles; {result['errors']}", flush=True)
        del engine, actual, controller

    after = verify()
    if before != after:
        raise ValueError("Frozen baseline changed during comparison")
    result = {
        "schema_version": 1,
        "classification": "V2_CONFIGURATION_ONLY_NINE_CASE_REPAIR_WITH_PERSISTENCE_LIMITS",
        "source_commit": PINNED_V2,
        "frozen_manifest_sha256_lf": sha(Path("experiments/exchange_decomposition/frozen_v2_manifest.json").read_bytes()),
        "frozen_before_after_identical": True,
        "source_hashes": before["source_hashes"],
        "trace_compiler_hashes": before["trace_compiler_hashes"],
        "oracle_source_sha256_lf": sha(Path("tools/unseen_protocol.py").read_bytes()),
        "workload_sha256_lf": sha(Path("experiments/exchange_decomposition/third_workload.json").read_bytes()),
        "candidate_configuration": json.loads(options.configuration.read_text()),
        "candidate_configuration_sha256": digest(__import__("dataclasses").asdict(cfg)),
        "probe_input_sha256_lf": sha(options.probes.read_bytes()),
        "cases": reports,
        "total_compared_cycles": sum(report["cycles"] for report in reports),
        "original_cases_passed": all(report["oracle"]["passed"] for report in reports if report["original_case"]),
        "added_probes_all_preserve_negative": all(not report["oracle"]["passed"] for report in reports if not report["original_case"]),
        "model_only": options.model_only,
        "semantics_changed": False,
        "historical_classification": "MOTIF_V2_UNSEEN_PROTOCOL_GENERALIZATION_PARTIAL",
        "interpretation": "This is a new bounded composition audit, not a replacement of the historical campaign or a proof over all programs.",
    }
    (options.output / "result.json").write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    if not result["original_cases_passed"] or not result["added_probes_all_preserve_negative"]:
        raise AssertionError("The expected bounded repair or preserved negative evidence changed")
    print(f"PASS v2 composition audit: {result['total_compared_cycles']} cycles; nine original passes and three preserved negatives", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "temporal_baseline")
    parser.add_argument("--configuration", type=Path, default=EVIDENCE / "configurations" / "v2_dual_source_response.json")
    parser.add_argument("--probes", type=Path, default=EVIDENCE / "v2_composition_probes.json")
    parser.add_argument("--model-only", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    options.output = options.output.resolve()
    options.configuration = options.configuration.resolve()
    options.probes = options.probes.resolve()
    if options.worker:
        worker(options)
        return
    frozen = archived_source(options.output / "frozen_v2")
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    base = environment.get("IVERILOG_BASE")
    if base:
        base_path = Path(base).resolve()
        environment["IVERILOG_BASE"] = os.path.relpath(base_path, frozen)
    elif os.name == "nt" and (ROOT / ".tools" / "ivl").is_dir():
        environment["IVERILOG_BASE"] = os.path.relpath(ROOT / ".tools" / "ivl", frozen)
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker",
               "--output", str(options.output), "--configuration", str(options.configuration),
               "--probes", str(options.probes)]
    if options.model_only:
        command.append("--model-only")
    subprocess.run(command, cwd=frozen, env=environment, check=True)


if __name__ == "__main__":
    main()
