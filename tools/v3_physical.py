"""Physical eligibility, immutable attempt intents and exact source correspondence.

This module never launches a flow. The official pinned Linux workflow owns P&R.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from tools.unseen_receipt import validate
from tools.v3_inventory import verify, sha, MANIFEST

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = Path("experiments/temporal_qualification/physical")
INPUTS = ("src/config.json", "info.yaml", "flow-lock.json", ".github/workflows/gds.yml")


def committed(source, path):
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("A complete identified source commit is required")
    return subprocess.check_output(["git", "show", source + ":" + path], cwd=ROOT)


def preflight(source):
    frozen = verify()
    logical = json.loads(Path("experiments/temporal_qualification/unseen/logical_result.json").read_text())
    validate(logical)
    # A workflow checkout must contain every protected byte, not only RTL.
    matches = {path: sha(committed(source, path)) == digest for path, digest in frozen["source_hashes"].items()}
    if not all(matches.values()):
        raise ValueError("Physical source differs from frozen semantics: " + ", ".join(p for p, equal in matches.items() if not equal))
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", source], cwd=ROOT, text=True).splitlines()
    runtime = {path for path in names if (path.startswith("src/") and path.endswith(".sv"))
               or (path.startswith("motif/") and path.endswith(".py"))}
    expected_runtime = {path for path in frozen["source_hashes"] if path.startswith(("src/", "motif/"))}
    if runtime != expected_runtime:
        raise ValueError("Identified physical source runtime inventory differs from frozen v3")
    config = json.loads(committed(source, "src/config.json"))
    info = committed(source, "info.yaml").decode()
    if config.get("CLOCK_PERIOD") != 20 or not re.search(r'\btiles:\s*[\"\']?6x4[\"\']?', info):
        raise ValueError("Physical allocation/clock exceeds the immutable 6x4/20ns contract")
    hashes = {path: sha(committed(source, path)) for path in INPUTS}
    if any(hashes[path] != frozen["physical_input_hashes"][path] for path in INPUTS if path != "src/config.json"):
        raise ValueError("Pinned physical workflow, tile description or tool lock changed")
    return {"schema_version": 3, "source_sha": source,
            "frozen_manifest_sha256_lf": sha(MANIFEST.read_bytes()), "preregistration": frozen["preregistration"],
            "unseen_result_sha256_lf": sha(Path("experiments/temporal_qualification/unseen/logical_result.json").read_bytes()),
            "selection_commit": logical["selection_commit"], "selection_sha256_lf": logical["selection_sha256_lf"],
            "all_protected_source_bytes_equal": True, "rtl_source_hashes_lf": frozen["rtl_hashes"],
            "physical_input_hashes_lf": hashes, "tile": "6x4", "clock_period_ns": 20,
            "pinned_flow": json.loads(committed(source, "flow-lock.json"))}


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def intent(source, diagnosis=None):
    data = preflight(source)
    existing = sorted(DIRECTORY.glob("attempt_*_intent.json"))
    number = len(existing) + 1
    if number > 3:
        raise ValueError("The initial attempt plus two diagnosed revisions is exhausted")
    frozen = verify()
    if number == 1:
        if data["physical_input_hashes_lf"] != frozen["physical_input_hashes"]:
            raise ValueError("Initial attempt must retain the separately recorded original physical inputs")
        if diagnosis:
            raise ValueError("Initial attempt is not a flow revision")
    else:
        if diagnosis is None:
            raise ValueError("A prior failed attempt and diagnosed flow-setting change are required")
        diagnosed = json.loads(Path(diagnosis).read_text())
        previous = DIRECTORY / f"attempt_{number-1}_result.json"
        if not previous.is_file() or json.loads(previous.read_text()).get("physical_qualified") is not False:
            raise ValueError("A revision requires retained failed physical qualification evidence")
        if diagnosed.get("previous_attempt") != number - 1 or not diagnosed.get("failure") or not diagnosed.get("permitted_setting_changes"):
            raise ValueError("Flow revision diagnosis is incomplete")
        data["diagnosis"] = {"path": Path(diagnosis).as_posix(), "sha256_lf": sha(Path(diagnosis).read_bytes())}
        prior = json.loads(existing[-1].read_text())
        if prior["physical_input_hashes_lf"]["src/config.json"] == data["physical_input_hashes_lf"]["src/config.json"]:
            raise ValueError("A new flow attempt must implement the diagnosed setting revision")
    data.update(attempt=number, flow_setting_revision=number-1, semantic_changes=False,
                status="prepared_before_dispatch", maximum_attempts=3)
    path = DIRECTORY / f"attempt_{number}_intent.json"
    if path.exists():
        raise ValueError("Refusing to overwrite an immutable physical attempt intent")
    write(path, data)
    print("PREPARED", number, "source", source, "intent SHA-256", sha(path.read_bytes()))
    return data


def correspondence(source, run_id, artifact_metadata, extracted, output):
    data = preflight(source)
    artifact = json.loads(Path(artifact_metadata).read_text())
    root = Path(extracted).resolve()
    expected_archive = artifact["digest"].removeprefix("sha256:")
    archive = Path(artifact["local_archive_path"])
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_archive:
        raise ValueError("Downloaded physical artifact differs from its published ZIP digest")
    if artifact["workflow_run"]["id"] != run_id or artifact["workflow_run"]["head_sha"] != source:
        raise ValueError("Physical artifact identifies a different workflow run/source")
    # Bind actual extracted physical files; private full data remains ignored.
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            if not path.resolve().is_relative_to(root):
                raise ValueError("Physical artifact contains an outside-directory link")
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    data.update(workflow_head_sha=source,
                source={"role": "materialized_identified_workflow_commit",
                        "derivation": "Independent git show of every protected source at the official workflow's exact head SHA; not claimed as bundled build sources"},
                artifact={"id": artifact["id"], "name": artifact["name"], "archive_sha256_raw": expected_archive,
                          "workflow_run_url": f"https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/{run_id}"},
                files_sha256_raw=files,
                expected_corners=["nom_fast_1p32V_m40C", "nom_typ_1p20V_25C", "nom_slow_1p08V_125C"])
    write(output, data)
    print("PASS exact protected-source and physical artifact correspondence", len(files), "identified files")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--intent", action="store_true")
    parser.add_argument("--diagnosis", type=Path)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--artifact-metadata", type=Path)
    parser.add_argument("--extracted", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.intent:
        intent(args.source_sha, args.diagnosis)
    elif args.run_id:
        if not all((args.artifact_metadata, args.extracted, args.output)):
            parser.error("Correspondence requires artifact metadata, extraction and output paths")
        correspondence(args.source_sha, args.run_id, args.artifact_metadata, args.extracted, args.output)
    else:
        preflight(args.source_sha)
        print("PASS physical eligibility, exact frozen source, pinned 6x4 and 20ns settings")


if __name__ == "__main__":
    main()
