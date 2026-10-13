"""Reject incomplete or stale unseen receipts before physical eligibility."""
import argparse
import json
import re
from pathlib import Path

from tools.lin_unseen import selected, cases, SELECTION_COMMIT, SELECTION_SHA
from tools.v3_inventory import verify, sha, MANIFEST


def validate(report, artifacts=False):
    verify()
    selection = selected()
    expected = {case["name"]: case["expected_tokens"] for case in cases(selection)}
    if (report.get("passed") is not True or report.get("qualification_complete") is not True
            or report.get("model_only") is not False or report.get("stage") != "unseen"
            or report.get("workload") != selection["workload"]
            or report.get("frozen_before_after_identical") is not True
            or report.get("evaluation_before_after_identical") is not True):
        raise ValueError("A complete passing unchanged-semantic unseen gate is required")
    if (report.get("selection_commit") != SELECTION_COMMIT or report.get("selection_sha256_lf") != SELECTION_SHA
            or report.get("frozen_manifest_sha256_lf") != sha(MANIFEST.read_bytes())
            or report.get("configuration_sha256_lf") != sha(Path("experiments/temporal_qualification/unseen/config.json").read_bytes())):
        raise ValueError("Unseen receipt identifies different immutable inputs or configuration")
    hashes = report.get("evaluation_source_hashes", {})
    required = {"tools/lin_unseen.py", "tools/lin_oracle.py", "tests/model/test_lin_oracle.py"}
    if set(hashes) != required or any(sha(Path(path).read_bytes()) != digest for path, digest in hashes.items()):
        raise ValueError("Unseen evaluation sources are stale or incomplete")
    rows = report.get("cases", [])
    if len(rows) != len(expected) or {row.get("name") for row in rows} != set(expected):
        raise ValueError("The 34 unique committed unseen cases are incomplete")
    for row in rows:
        wanted = expected[row["name"]]
        if (row.get("cycles", 0) <= 0 or row.get("model_rtl_agreement") is not True
                or row.get("expected") != wanted or row.get("observed") != wanted
                or row.get("configuration_writes_during_traffic") != 0
                or row.get("host_reads_during_traffic") != 0):
            raise ValueError("Unseen case behavior/agreement is incomplete: " + row["name"])
        for label in ("oracle", "model_oracle"):
            result = row.get(label, {})
            tokens = result.get("expected", [])
            acceptances = result.get("observed_acceptances", [])
            if (not {"passed", "errors", "expected", "observed_acceptances"} <= result.keys()
                    or not isinstance(tokens, list) or not isinstance(acceptances, list)
                    or result.get("passed") is not True or result.get("errors") != []
                    or [token.get("value") for token in tokens] != wanted or len(acceptances) != len(wanted)):
                raise ValueError("Independent oracle evidence is incomplete: " + row["name"])
            if any(not token["earliest"] <= observed["cycle"] <= token["latest"]
                   for token, observed in zip(tokens, acceptances)):
                raise ValueError("Recorded acceptance is outside the unchanged electrical window")
        evidence = row.get("evidence_sha256_lf", {})
        if (set(evidence) != {"inputs.txt", "model.jsonl", "rtl.jsonl", "simulation.log"}
                or any(not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                       for digest in evidence.values())):
            raise ValueError("Unseen full comparison artifact identities are incomplete")
        if artifacts:
            directory = Path(row["trace_directory"]).resolve()
            directory.relative_to(Path("build").resolve())
            if any(sha((directory / name).read_bytes()) != digest for name, digest in evidence.items()):
                raise ValueError("Unseen generated artifact identity changed")
    if report.get("total_compared_cycles") != sum(row["cycles"] for row in rows):
        raise ValueError("Unseen compared-cycle inventory is incomplete")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, default=Path("experiments/temporal_qualification/unseen/logical_result.json"))
    parser.add_argument("--verify-artifacts", action="store_true")
    args = parser.parse_args()
    report = validate(json.loads(args.receipt.read_text()), args.verify_artifacts)
    print(f"PASS independent unseen gate receipt: {len(report['cases'])} cases, {report['total_compared_cycles']:,} compared cycles")


if __name__ == "__main__":
    main()
