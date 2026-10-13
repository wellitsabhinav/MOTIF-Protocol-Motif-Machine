"""Require the complete original and selected runtime tests on one routed file."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from tools.host_check import expected_test_names
from tools.v3_inventory import verify, sha, MANIFEST
from tools.v3_physical import preflight


def read_receipt(directory):
    directory = Path(directory)
    verify()
    workflow = json.loads((directory / "workflow.json").read_text())
    identity = json.loads((directory / "netlist_identity.json").read_text())
    if (type(workflow.get("id")) is not int or workflow["id"] <= 0
            or workflow.get("status") != "completed" or workflow.get("conclusion") != "success"
            or workflow.get("path") != ".github/workflows/gds.yml"):
        raise ValueError("Routed netlist requires an identified successful official physical workflow")
    if not isinstance(identity.get("sha256_raw"), str) or not re.fullmatch(r"[0-9a-f]{64}", identity["sha256_raw"]):
        raise ValueError("A complete routed-netlist SHA-256 is required")
    preflight(workflow["head_sha"])
    qualified = json.loads(Path("experiments/temporal_qualification/unseen/runtime_host_result.json").read_text())
    expected = {"tools/lin_host_check.py", "test/lin_runtime.py", "tools/lin_unseen.py", "tools/lin_oracle.py",
                "experiments/temporal_qualification/unseen/config.json",
                "experiments/temporal_qualification/unseen/selected_workload.json"}
    if (qualified.get("passed") is not True or qualified.get("stage") != "unseen-runtime-host"
            or qualified.get("frozen_before_after_identical") is not True
            or qualified.get("evaluation_before_after_identical") is not True
            or qualified.get("frozen_manifest_sha256_lf") != sha(MANIFEST.read_bytes())
            or set(qualified.get("evaluation_source_hashes", {})) != expected):
        raise ValueError("A complete passing unchanged-semantic qualified runtime subset is required")
    current = {path: sha(Path(path).read_bytes()) for path in qualified["evaluation_source_hashes"]}
    if current != qualified["evaluation_source_hashes"]:
        raise ValueError("Routed test configuration/stimulus/oracle differs from the qualified runtime subset")
    netlist = (directory / identity["path"]).resolve()
    netlist.relative_to(directory.resolve())
    if hashlib.sha256(netlist.read_bytes()).hexdigest() != identity["sha256_raw"]:
        raise ValueError("Routed netlist changed during its functional checks")
    if hashlib.sha256((directory / "compiled_netlist.v").read_bytes()).hexdigest() != identity["sha256_raw"]:
        raise ValueError("The netlist actually compiled differs from the identified downloaded netlist")
    inventory = []
    for filename, expected in (("original_results.xml", expected_test_names()),
                               ("lin_results.xml", {"runtime_lin_unseen"})):
        tests = ET.parse(directory / filename).getroot().findall(".//testcase")
        if len(tests) != len(expected) or {test.get("name") for test in tests} != expected:
            raise ValueError("Required routed test roster omitted/duplicated: " + filename)
        for test in tests:
            if any(test.find(tag) is not None for tag in ("failure", "error", "skipped")):
                raise ValueError("Routed functional test failed/skipped: " + test.get("name"))
            inventory.append({"name": test.get("name"), "passed": True})
    result = {"schema_version": 3, "passed": True, "build_run_id": workflow["id"],
              "source_sha": workflow["head_sha"], "netlist_sha256_raw": identity["sha256_raw"],
              "frozen_manifest_sha256_lf": sha(MANIFEST.read_bytes()), "tests": inventory,
              "evaluation_source_hashes": current,
              "input_sha256_raw": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                   for name in ("workflow.json", "netlist_identity.json", "compiled_netlist.v", "original_results.xml", "lin_results.xml")},
              "scope": "Zero-delay functional checks on the identified routed netlist. STA is separate."}
    return result


def run(directory):
    directory = Path(directory)
    result = read_receipt(directory)
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("PASS six required routed functional tests on one identified netlist")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    run(parser.parse_args().directory)
