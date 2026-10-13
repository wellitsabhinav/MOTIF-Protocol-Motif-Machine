"""Physical eligibility, immutable attempt intents and exact source correspondence.

This module never launches a flow. The official pinned Linux workflow owns P&R.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import subprocess
import zipfile

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
        failed = json.loads(previous.read_text())
        dispatch = json.loads((DIRECTORY / f"attempt_{number-1}_dispatch.json").read_text())
        if (failed.get("workflow_status") != "completed" or failed.get("workflow_run_id") != dispatch["run_id"]
                or failed.get("source_sha") != dispatch["source_sha"]):
            raise ValueError("A revision requires completed failure evidence bound to the preceding immutable dispatch")
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


def correspondence_data(source, run_id, artifact_metadata, extracted):
    data = preflight(source)
    artifact = json.loads(Path(artifact_metadata).read_text())
    root = Path(extracted).resolve()
    expected_archive = artifact["digest"].removeprefix("sha256:")
    archive = Path(artifact["local_archive_path"])
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_archive:
        raise ValueError("Downloaded physical artifact differs from its published ZIP digest")
    if artifact["workflow_run"]["id"] != run_id or artifact["workflow_run"]["head_sha"] != source:
        raise ValueError("Physical artifact identifies a different workflow run/source")
    archive_files = {}
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            name = entry.orig_filename
            parts = PurePosixPath(name).parts
            if (name != entry.filename or not parts or name.startswith("/") or "\\" in name or ":" in name or ".." in parts
                    or (entry.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("Physical ZIP contains an unsafe member: " + name)
            if entry.is_dir():
                continue
            if name in archive_files:
                raise ValueError("Physical ZIP contains a duplicate member: " + name)
            archive_files[name] = hashlib.sha256(bundle.read(entry)).hexdigest()
    # Bind actual extracted physical files; private full data remains ignored.
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("Physical artifact contains an outside-directory link")
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if files != archive_files:
        raise ValueError("Extracted physical inventory differs from the published archive bytes")
    source_record = {"role": "materialized_identified_workflow_commit",
                     "derivation": "Independent git show of every protected source at the official workflow's exact head SHA; not claimed as bundled build sources"}
    if (root / "src").is_dir():
        bundled = {path.relative_to(root).as_posix(): sha(path.read_bytes()) for path in (root / "src").rglob("*.sv")}
        if bundled != data["rtl_source_hashes_lf"]:
            raise ValueError("Bundled workflow RTL differs from the frozen exact source inventory")
        source_record = {"role": "bundled_workflow_sources", "directory": "src",
                         "derivation": "Actual published archive source bytes also equal every frozen RTL hash and the identified Git commit"}
    data.update(workflow_head_sha=source,
                source=source_record,
                artifact={"id": artifact["id"], "name": artifact["name"], "archive_sha256_raw": expected_archive,
                          "workflow_run_url": f"https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/{run_id}"},
                files_sha256_raw=files,
                expected_corners=["nom_fast_1p32V_m40C", "nom_typ_1p20V_25C", "nom_slow_1p08V_125C"])
    return data


def correspondence(source, run_id, artifact_metadata, extracted, output):
    data = correspondence_data(source, run_id, artifact_metadata, extracted)
    write(output, data)
    print("PASS exact protected-source and physical artifact correspondence", len(data["files_sha256_raw"]), "identified files")
    return data


def record_dispatch(number, workflow):
    path = DIRECTORY / f"attempt_{number}_intent.json"
    prepared = json.loads(path.read_text())
    run = json.loads(Path(workflow).read_text())
    if (run.get("head_sha") != prepared["source_sha"] or run.get("path") != ".github/workflows/gds.yml"
            or run.get("event") != "workflow_dispatch" or run.get("run_attempt") != 1
            or run.get("repository", {}).get("full_name") != "wellitsabhinav/MOTIF-Protocol-Motif-Machine"):
        raise ValueError("Official dispatch does not match its immutable intent or repeats a run")
    preflight(run["head_sha"])
    data = {"schema_version": 3, "attempt": number, "intent_sha256_lf": sha(path.read_bytes()),
            "run_id": run["id"], "run_attempt": run["run_attempt"], "source_sha": run["head_sha"],
            "workflow_url": run["html_url"], "workflow_id": run["workflow_id"],
            "created_at": run["created_at"], "flow_setting_revision": number-1,
            "frozen_manifest_sha256_lf": prepared["frozen_manifest_sha256_lf"],
            "preregistration": prepared["preregistration"],
            "snapshot_sha256_lf": sha(Path(workflow).read_bytes())}
    output = DIRECTORY / f"attempt_{number}_dispatch.json"
    if output.exists() and json.loads(output.read_text()) != data:
        raise ValueError("Refusing to overwrite an immutable physical dispatch")
    write(output, data)
    print("RECORDED physical attempt", number, "run", run["id"], "exact source", run["head_sha"])
    return data


def record_failure(number, workflow, jobs, artifacts):
    """Retain an actual terminal failure when no physical archive was published."""
    prepared = json.loads((DIRECTORY / f"attempt_{number}_intent.json").read_text())
    dispatch = json.loads((DIRECTORY / f"attempt_{number}_dispatch.json").read_text())
    values = {role: json.loads(Path(path).read_text()) for role, path in
              (("workflow", workflow), ("jobs", jobs), ("artifacts", artifacts))}
    run = values["workflow"]
    identities = preflight(prepared["source_sha"])
    if (run.get("id") != dispatch["run_id"] or run.get("head_sha") != dispatch["source_sha"]
            or run.get("status") != "completed" or run.get("conclusion") not in
               ("failure", "cancelled", "timed_out", "action_required", "startup_failure")
            or run.get("path") != ".github/workflows/gds.yml" or run.get("run_attempt") != 1):
        raise ValueError("Status-only failure requires the completed unsuccessful identified physical dispatch")
    rows = values["jobs"]["jobs"]
    failures = [job for job in rows if job.get("name") in ("gds", "precheck", "gl_test")
                and job.get("status") == "completed" and job.get("conclusion") not in ("success", "skipped", None)]
    if not failures or any(job.get("run_id") != run["id"] for job in rows):
        raise ValueError("No terminal required-job failure belongs to the identified run")
    archives = values["artifacts"]["artifacts"]
    if any(item.get("name") in ("GDS_logs", "tt_submission") for item in archives):
        raise ValueError("Published physical archives require normal artifact/partial-metric extraction")
    data = {"schema_version": 3, "physical_qualified": False, "attempt": number,
            "source_sha": run["head_sha"], "workflow_run_id": run["id"],
            "workflow_status": run["status"], "workflow_conclusion": run["conclusion"],
            "workflow_url": run["html_url"], "failure_scope": "terminal official failure without published physical archives",
            "errors": [job["name"] + ": " + job["conclusion"] for job in failures],
            "measurements": None, "corners": None, "routed_evidence": None,
            "unavailable_reason": "No physical archive was published; no measured value or artifact identity is invented",
            "jobs": rows, "published_artifacts": archives,
            "frozen_manifest_sha256_lf": identities["frozen_manifest_sha256_lf"],
            "preregistration": identities["preregistration"],
            "physical_input_hashes_lf": identities["physical_input_hashes_lf"],
            "metadata_sha256_raw": {role: hashlib.sha256(Path(path).read_bytes()).hexdigest() for role, path in
              (("workflow", workflow), ("jobs", jobs), ("artifacts", artifacts))}}
    output = DIRECTORY / f"attempt_{number}_result.json"
    if output.exists() and json.loads(output.read_text()) != data:
        raise ValueError("Refusing to overwrite retained terminal failure evidence")
    write(output, data)
    print("FAIL identified physical attempt", number, "without published physical archives")
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
    parser.add_argument("--record-dispatch", type=int)
    parser.add_argument("--record-failure", type=int)
    parser.add_argument("--workflow", type=Path)
    parser.add_argument("--jobs", type=Path)
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    if args.record_failure:
        if not all((args.workflow, args.jobs, args.artifacts)):
            parser.error("Terminal failure recording requires actual workflow, jobs and artifact-list metadata")
        record_failure(args.record_failure, args.workflow, args.jobs, args.artifacts)
        return 1
    elif args.record_dispatch:
        if not args.workflow:
            parser.error("Dispatch recording requires identified workflow metadata")
        record_dispatch(args.record_dispatch, args.workflow)
    elif args.intent:
        intent(args.source_sha, args.diagnosis)
    elif args.run_id:
        if not all((args.artifact_metadata, args.extracted, args.output)):
            parser.error("Correspondence requires artifact metadata, extraction and output paths")
        correspondence(args.source_sha, args.run_id, args.artifact_metadata, args.extracted, args.output)
    else:
        preflight(args.source_sha)
        print("PASS physical eligibility, exact frozen source, pinned 6x4 and 20ns settings")


if __name__ == "__main__":
    raise SystemExit(main())
