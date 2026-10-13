"""Pinned runtime host check for the new independent unseen test module."""
import argparse
import json
import os
import platform
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from tools.host_check import cocotb_runtime
from tools.v3_inventory import verify, sha, MANIFEST
from tools.synthesis import executable_identity

ROOT = Path(__file__).resolve().parents[1]


def run(output=Path("build/v3_temporal_qualification/unseen_host/result.json")):
    before = verify()
    output = Path(output)
    build = output.resolve().parent
    build.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 3, "stage": "unseen-runtime-host", "passed": False,
              "frozen_manifest_sha256_lf": sha(MANIFEST.read_bytes()),
              "python_version": platform.python_version(),
              "simulator": {"iverilog": executable_identity(os.environ.get("IVERILOG", "iverilog")),
                            "vvp": executable_identity(os.environ.get("VVP", "vvp"))},
              "evaluation_source_hashes": {path: sha((ROOT / path).read_bytes()) for path in
                  ("tools/lin_host_check.py", "test/lin_runtime.py", "tools/lin_unseen.py", "tools/lin_oracle.py",
                   "experiments/temporal_qualification/unseen/config.json",
                   "experiments/temporal_qualification/unseen/selected_workload.json")},
              "runtime_test_sha256_lf": sha((ROOT / "test/lin_runtime.py").read_bytes()),
              "selected_cases": ["nominal", "one_cycle_high_split", "pending_sync_recovery", "back_to_back"],
              "scope": "Actual host table/configuration load, receive-only pads and independent posttraffic FIFO drain; dense early-token timing is established separately by the full core differential gate."}
    try:
        cocotb, get_runner = cocotb_runtime()
        report["cocotb_version"] = cocotb.__version__
        sys.path.insert(0, str(ROOT / "test"))
        sys.path.insert(1, str(ROOT))
        arguments = []
        if os.environ.get("IVERILOG_BASE"):
            base = Path(os.environ["IVERILOG_BASE"])
            if not base.is_absolute():
                base = ROOT / base
            arguments = ["-B", os.path.relpath(base.resolve(), build)]
        runner = get_runner("icarus")
        runner.build(sources=[*sorted((ROOT / "src").glob("*.sv")), ROOT / "test/tb.v"],
                     hdl_toplevel="tb", build_dir=build, build_args=arguments,
                     always=True, waves=False, log_file=build / "compile.log")
        result = runner.test(test_module="lin_runtime", hdl_toplevel="tb", hdl_toplevel_lang="verilog",
                             build_dir=build, test_dir=build, seed=20261013, waves=False,
                             results_xml=str(build / "results.xml"), log_file=build / "simulation.log")
        tests = ET.parse(result).getroot().findall(".//testcase")
        report["tests"] = [{"name": test.get("name"), "passed": not any(test.find(tag) is not None
                             for tag in ("failure", "error", "skipped"))} for test in tests]
        report["passed"] = len(tests) == 1 and report["tests"] == [{"name": "runtime_lin_unseen", "passed": True}]
        report["results_sha256_lf"] = sha(Path(result).read_bytes())
        report["simulation_log_sha256_lf"] = sha((build / "simulation.log").read_bytes())
        report["frozen_before_after_identical"] = verify() == before
        report["evaluation_before_after_identical"] = all(sha((ROOT / path).read_bytes()) == digest
                           for path, digest in report["evaluation_source_hashes"].items())
        if not report["passed"] or not report["frozen_before_after_identical"] or not report["evaluation_before_after_identical"]:
            raise AssertionError("Required unseen runtime host test failed/omitted")
    except Exception as failure:
        report["failure"] = str(failure)
        raise
    finally:
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        attempts = build / "attempts"
        attempts.mkdir(exist_ok=True)
        (attempts / (sha(output.read_bytes()) + ".json")).write_bytes(output.read_bytes())
    print("PASS selected LIN runtime host cases", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("build/v3_temporal_qualification/unseen_host/result.json"))
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
