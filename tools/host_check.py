"""Cross-platform cocotb runtime-host qualification without shell make rules."""
import argparse
import ast
import importlib.util
import json
import os
import platform
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.v3_inventory import report_identity, sha
from tools.synthesis import executable_identity

ROOT = Path(__file__).resolve().parents[1]


def cocotb_runtime():
    if importlib.util.find_spec("cocotb") is None:
        local = ROOT / ".tools/py"
        if local.is_dir():
            sys.path.insert(0, str(local))
    import cocotb
    from cocotb_tools.runner import get_runner
    if cocotb.__version__ != "2.0.1":
        raise RuntimeError("Runtime qualification requires pinned cocotb 2.0.1")
    return cocotb, get_runner


def expected_test_names():
    tree = ast.parse((ROOT / "test/test.py").read_text())
    return {node.name for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
            and any(isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "cocotb"
                    and decorator.func.attr == "test" for decorator in node.decorator_list)}


def run(output=Path("build/v3_temporal_qualification/cocotb.json"), build_dir=Path("build/v3_temporal_qualification/host")):
    output, build_dir = Path(output), Path(build_dir).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 3, "stage": "cocotb", **report_identity(), "passed": False,
              "python_version": platform.python_version(),
              "simulator": {"iverilog": executable_identity(os.environ.get("IVERILOG", "iverilog")),
                            "vvp": executable_identity(os.environ.get("VVP", "vvp"))},
              "runner": "pinned cocotb_tools.runner.get_runner('icarus')"}
    failure = None
    try:
        cocotb, get_runner = cocotb_runtime()
        report["cocotb_version"] = cocotb.__version__
        sys.path.insert(0, str(ROOT / "test"))
        sys.path.insert(1, str(ROOT))
        runner = get_runner("icarus")
        arguments = []
        if os.environ.get("IVERILOG_BASE"):
            base = Path(os.environ["IVERILOG_BASE"])
            if not base.is_absolute():
                base = ROOT / base
            arguments = ["-B", os.path.relpath(base.resolve(), build_dir)]
        sources = [*sorted((ROOT / "src").glob("*.sv")), ROOT / "test/tb.v"]
        runner.build(sources=sources, hdl_toplevel="tb", build_dir=build_dir,
                     build_args=arguments, always=True, waves=False, log_file=build_dir / "compile.log")
        results = runner.test(test_module="test", hdl_toplevel="tb", hdl_toplevel_lang="verilog",
                              build_dir=build_dir, test_dir=build_dir, seed=20261012,
                              results_xml=str(build_dir / "results.xml"), waves=False,
                              log_file=build_dir / "simulation.log")
        root = ET.parse(results).getroot()
        cases = root.findall(".//testcase")
        observed_names = {case.get("name") for case in cases}
        expected = expected_test_names()
        report["tests"] = [{"name": case.get("name"), "passed": case.find("failure") is None and case.find("error") is None and case.find("skipped") is None}
                           for case in cases]
        report["expected_test_names"] = sorted(expected)
        report["results_sha256_lf"] = sha(Path(results).read_bytes())
        report["simulation_log_sha256_lf"] = sha((build_dir / "simulation.log").read_bytes())
        report["passed"] = bool(expected) and observed_names == expected and all(case["passed"] for case in report["tests"])
        if not report["passed"]:
            raise AssertionError("Runtime host tests failed, were skipped or were omitted")
    except BaseException as error:
        failure = error
        report["failure"] = str(error)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    if failure is not None:
        raise RuntimeError("Runtime host qualification failed; evidence: " + str(output)) from failure
    print("PASS runtime host qualification: " + ", ".join(case["name"] for case in report["tests"]))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("build/v3_temporal_qualification/cocotb.json"))
    parser.add_argument("--build-dir", type=Path, default=Path("build/v3_temporal_qualification/host"))
    args = parser.parse_args()
    run(args.output, args.build_dir)


if __name__ == "__main__":
    main()
