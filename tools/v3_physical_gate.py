"""Physical closure is distinct from logical and matched nominal-cost results."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from tools.host_check import expected_test_names
from tools.v3_inventory import verify, sha, MANIFEST
from tools.v3_physical import preflight, correspondence_data
from tools.v3_physical_metrics import EXPECTED_CORNERS, summarize
from tools.v3_routed_receipt import read_receipt


def decision(metrics, correspondence, routed):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    require(metrics.get("workflow_status") == "completed" and metrics.get("workflow_conclusion") == "success",
            "Official physical workflow has not completed successfully")
    require(metrics.get("extraction_scope", {}).get("metrics_status") == "final_metrics_available",
            "Final identified physical metrics are unavailable")
    jobs = {job["name"]: job for job in metrics.get("jobs", [])}
    for name in ("gds", "precheck", "gl_test"):
        require(jobs.get(name, {}).get("status") == "completed" and jobs.get(name, {}).get("conclusion") == "success",
                "Required official job unavailable/failed: " + name)
    for corner in sorted(set(EXPECTED_CORNERS) | set(metrics.get("corners", {}))):
        values = metrics.get("corners", {}).get(corner, {})
        for name in ("setup_worst_slack_ns", "hold_worst_slack_ns", "setup_wns_ns", "hold_wns_ns", "setup_tns_ns", "hold_tns_ns"):
            value = values.get(name)
            required_value = value == 0 if name.endswith("_tns_ns") else type(value) in (int, float) and value >= 0
            require(type(value) in (int, float) and math.isfinite(value) and required_value,
                    "Missing/negative timing result: " + corner + "/" + name)
    measured = metrics.get("measurements", {})
    for name in ("detailed_route_drc", "magic_drc", "lvs_errors"):
        require(type(measured.get(name)) in (int, float) and measured[name] == 0,
                "Missing/nonzero physical check: " + name)
    overflow = metrics.get("global_route", {}).get("total_overflow")
    require(type(overflow) in (int, float) and overflow == 0, "Global-route overflow is nonzero/unavailable")
    for name in ("antenna_violating_nets", "antenna_violating_pins", "route_antenna_violations"):
        value = measured.get(name)
        if value is not None:
            require(type(value) in (int, float) and math.isfinite(value) and value == 0,
                    "Invalid/nonzero reported antenna violations: " + name)
    require(correspondence.get("source_sha") == metrics.get("source_sha") and correspondence.get("all_protected_source_bytes_equal") is True,
            "Exact protected-source correspondence is missing")
    required = expected_test_names() | {"runtime_lin_unseen"}
    tests = routed.get("tests", [])
    require(routed.get("passed") is True and len(tests) == len(required)
            and {test.get("name") for test in tests} == required and all(test.get("passed") is True for test in tests),
            "Complete six-test routed functional receipt is missing/failed")
    require(routed.get("source_sha") == metrics.get("source_sha") and routed.get("build_run_id") == metrics.get("workflow_run_id"),
            "Routed tests identify another physical run/source")
    digest = routed.get("netlist_sha256_raw")
    require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
            and digest in correspondence.get("files_sha256_raw", {}).values(),
            "Routed netlist is not bound by the downloaded-artifact correspondence")
    return {"physical_qualified": not errors, "errors": errors,
            "scope": "Pinned 6x4/20ns official flow, three-corner STA, precheck, exact source correspondence and bounded zero-delay routed tests; no analog/silicon or complete protocol claim."}


def run(args):
    frozen = verify()
    metrics = json.loads(args.metrics.read_text())
    identities = preflight(metrics["source_sha"])
    values, hashes = {}, {}
    for role in ("artifacts", "jobs", "workflow", "source_correspondence"):
        path = getattr(args, role)
        raw = path.read_bytes()
        values[role], hashes[role] = json.loads(raw), hashlib.sha256(raw).hexdigest()
    replay = summarize(args.run_directory, metrics["workflow_run_id"], metrics["source_sha"],
                       values["artifacts"], values["jobs"], workflow_metadata=values["workflow"],
                       source_correspondence=values["source_correspondence"], metadata_raw_hashes=hashes,
                       scope=metrics["extraction_scope"]["scope"])
    if replay != metrics:
        raise ValueError("Physical report is stale or differs from independent current-input extraction")
    correspondence = values["source_correspondence"]
    if correspondence_data(metrics["source_sha"], metrics["workflow_run_id"],
                           args.physical_artifact_metadata, args.artifact_directory) != correspondence:
        raise ValueError("Physical source correspondence differs from the actual published archive and extracted bytes")
    if (correspondence.get("rtl_source_hashes_lf") != frozen["rtl_hashes"]
            or correspondence.get("frozen_manifest_sha256_lf") != sha(MANIFEST.read_bytes())):
        raise ValueError("Physical correspondence identifies another frozen boundary")
    routed = {"passed": False, "status": "unavailable", "reason": "No completed routed functional evidence supplied"}
    if args.routed_receipt is not None:
        if args.routed_directory is None:
            raise ValueError("Routed receipt replay requires its actual extracted directory")
        routed = json.loads(args.routed_receipt.read_text())
        try:
            if read_receipt(args.routed_directory) != routed:
                raise ValueError("Routed functional receipt differs from the actual identified netlist and XML results")
        except (ValueError, OSError) as error:
            routed = {"passed": False, "status": "invalid", "reason": str(error)}
    elif args.routed_directory is not None:
        raise ValueError("Routed directory requires an explicit routed receipt")
    result = {"schema_version": 3, **decision(metrics, correspondence, routed),
              "source_sha": metrics["source_sha"], "workflow_run_id": metrics["workflow_run_id"],
              "workflow_status": metrics["workflow_status"], "workflow_conclusion": metrics["workflow_conclusion"],
              "frozen_manifest_sha256_lf": sha(MANIFEST.read_bytes()), "preregistration": frozen["preregistration"],
              "physical_input_hashes_lf": identities["physical_input_hashes_lf"],
              "metrics_sha256_lf": sha(args.metrics.read_bytes()),
              "routed_receipt_sha256_lf": sha(args.routed_receipt.read_bytes()) if args.routed_receipt else None,
              "routed_evidence": routed}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(("PASS" if result["physical_qualified"] else "FAIL") + " physical qualification")
    for error in result["errors"]:
        print(error)
    return 0 if result["physical_qualified"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    for name in ("metrics", "artifacts", "jobs", "workflow", "source-correspondence", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--routed-receipt", type=Path)
    parser.add_argument("--routed-directory", type=Path)
    parser.add_argument("--physical-artifact-metadata", type=Path, required=True)
    parser.add_argument("--artifact-directory", type=Path, required=True)
    raise SystemExit(run(parser.parse_args()))
