"""Extract identified official-flow evidence without deciding qualification.

Input is an extracted single LibreLane run directory. Final metrics take
precedence; a last available stage state is labeled partial/unfinished. Missing
and nonfinite measurements remain null with their reasons. Nothing is run and
no historical report or frozen campaign input is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

EXPECTED_CORNERS = ("nom_fast_1p32V_m40C", "nom_typ_1p20V_25C", "nom_slow_1p08V_125C")
MEASUREMENTS = {
    "stdcell_count": ("design__instance__count__stdcell",),
    "stdcell_area_um2": ("design__instance__area__stdcell",),
    "register_count": ("design__instance__count__class:sequential_cell",),
    "core_area_um2": ("design__core__area",),
    "stdcell_utilization": ("design__instance__utilization__stdcell",),
    "detailed_wirelength_um": ("route__wirelength",),
    "global_wirelength_um": ("global_route__wirelength",),
    "vias": ("route__vias",),
    "detailed_route_drc": ("route__drc_errors", "route__drc_error__count", "route__drc_errors__count"),
    "magic_drc": ("magic__drc_error__count", "magic__drc_errors"),
    "klayout_drc": ("klayout__drc_error__count", "klayout__drc_errors"),
    "lvs_errors": ("design__lvs_error__count",),
    "antenna_violating_nets": ("antenna__violating__nets",),
    "antenna_violating_pins": ("antenna__violating__pins",),
    "route_antenna_violations": ("route__antenna_violation__count",),
    "hold_buffer_count": ("design__instance__count__hold_buffer",),
    "timing_repair_buffer_area_um2": ("design__instance__area__class:timing_repair_buffer",),
    "max_fanout_violations": ("design__max_fanout_violation__count",),
    "max_slew_violations": ("design__max_slew_violation__count",),
    "max_cap_violations": ("design__max_cap_violation__count",),
}
TIMING = {
    "setup_worst_slack_ns": "setup__ws", "hold_worst_slack_ns": "hold__ws",
    "setup_wns_ns": "setup__wns", "hold_wns_ns": "hold__wns",
    "setup_tns_ns": "setup__tns", "hold_tns_ns": "hold__tns",
    "setup_violations": "setup_vio__count", "hold_violations": "hold_vio__count",
}
TIMING_REPORTS = {
    "setup_worst_slack_ns": "ws.max.rpt", "hold_worst_slack_ns": "ws.min.rpt",
    "setup_wns_ns": "wns.max.rpt", "hold_wns_ns": "wns.min.rpt",
    "setup_tns_ns": "tns.max.rpt", "hold_tns_ns": "tns.min.rpt",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def natural_stage_key(path):
    return tuple((int(m[1]), m[2]) if (m := re.match(r"(\d+)-(.*)", part)) else (-1, part)
                 for part in Path(path).parts)


class Inputs:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.records = {}
        self.problems = {}
        if not self.root.is_dir():
            raise ValueError("Explicit flow run directory does not exist")

    def read(self, path):
        path = Path(path)
        absolute = path.resolve()
        if not absolute.is_relative_to(self.root) or not absolute.is_file():
            raise ValueError("Physical input lies outside the explicit flow directory: " + str(path))
        name = absolute.relative_to(self.root).as_posix()
        data = absolute.read_bytes()
        self.records[name] = {"sha256_raw": digest(data), "bytes": len(data)}
        return data

    def json(self, path):
        data = self.read(path)
        try:
            value = json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            self.problems[Path(path).relative_to(self.root).as_posix()] = "invalid_json: " + str(exc)
            return None
        if not isinstance(value, dict):
            self.problems[Path(path).relative_to(self.root).as_posix()] = "json_root_is_not_an_object"
            return None
        return value

    def relative(self, path):
        return Path(path).relative_to(self.root).as_posix()


def number(value):
    """Preserve unavailable values, including JSON's permissive NaN/Infinity."""
    if value is None:
        return None, "value_is_null"
    if isinstance(value, bool):
        return None, "boolean_is_not_a_numeric_measurement"
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            return None, "nonfinite_value: " + str(value)
        return value, None
    if isinstance(value, str) and re.fullmatch(NUMBER, value.strip()):
        converted = float(value)
        return (converted, None) if math.isfinite(converted) else (None, "nonfinite_numeric_string")
    return None, "unsupported_numeric_value: " + str(value)


def numeric_field(metrics, keys, source, label, origins, unavailable):
    existing = [key for key in keys if key in metrics]
    if not existing:
        unavailable[label] = "metric_not_present" if source else "no_available_metric_source"
        return None
    # A present but invalid primary key must not be replaced by a convenient
    # alias. Conflicting valid aliases also do not silently select a result.
    values = [(key, *number(metrics[key])) for key in existing]
    origins[label] = {"path": source, "keys": existing}
    if values[0][2]:
        unavailable[label] = values[0][2]
        return None
    if any(reason or value != values[0][1] for _, value, reason in values[1:]):
        unavailable[label] = "conflicting_or_invalid_alias_values"
        return None
    return values[0][1]


def artifacts_identity(artifacts):
    if isinstance(artifacts, dict):
        artifacts = artifacts.get("artifacts", [artifacts])
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("At least one explicit downloaded artifact identity is required")
    result = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("Artifact identity must be an object")
        archive_hash = artifact.get("archive_sha256_raw", artifact.get("sha256"))
        if (not isinstance(artifact.get("id"), int) or isinstance(artifact["id"], bool)
                or artifact["id"] <= 0 or not artifact.get("name")
                or not isinstance(archive_hash, str) or not SHA256.fullmatch(archive_hash)):
            raise ValueError("Artifact ID, name and raw archive SHA-256 are required")
        record = {"id": artifact["id"], "name": artifact["name"], "archive_sha256_raw": archive_hash}
        for key in ("extraction_scope", "archive_bytes", "download_url"):
            if key in artifact:
                record[key] = artifact[key]
        result.append(record)
    if len({a["id"] for a in result}) != len(result):
        raise ValueError("Duplicate artifact ID")
    return result


def normalized_jobs(metadata, run_id, source_sha):
    if isinstance(metadata, list):
        jobs = metadata
    elif isinstance(metadata, dict):
        jobs = metadata.get("jobs", [])
        if metadata.get("head_sha") not in (None, source_sha):
            raise ValueError("Jobs metadata names a different source commit")
        if metadata.get("run_id") not in (None, run_id):
            raise ValueError("Jobs metadata names a different workflow run")
    else:
        raise ValueError("Jobs metadata must be an object or list")
    if not isinstance(jobs, list):
        raise ValueError("Jobs metadata jobs field must be a list")
    result = []
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("Each job must be an object")
        if job.get("run_id") not in (None, run_id) or job.get("head_sha") not in (None, source_sha):
            raise ValueError("A job names a different workflow run/source")
        result.append({key: job.get(key) for key in ("id", "name", "status", "conclusion", "html_url", "started_at", "completed_at")} | {
            "steps": [{key: step.get(key) for key in ("name", "number", "status", "conclusion", "started_at", "completed_at")}
                      for step in job.get("steps", [])],
        })
    return result


def stages_and_metrics(inputs):
    candidates = sorted((p for p in inputs.root.rglob("*") if p.is_dir() and re.match(r"^\d+-", p.name)),
                        key=lambda p: natural_stage_key(p.relative_to(inputs.root)))
    stages, available = [], []
    for path in candidates:
        state_in, state_out = path / "state_in.json", path / "state_out.json"
        incoming = inputs.json(state_in) if state_in.is_file() else None
        outgoing = inputs.json(state_out) if state_out.is_file() else None
        logs = sorted(p for p in path.glob("*.log") if p.is_file())
        for log in logs:
            inputs.read(log)
        status = "state_out_available" if outgoing is not None else "started_without_valid_state_out" if state_in.is_file() or logs or state_out.is_file() else "directory_only"
        stages.append({"path": inputs.relative(path), "status": status,
                       "state_in_present": state_in.is_file(), "state_out_present": state_out.is_file(),
                       "state_in_valid": incoming is not None, "state_out_valid": outgoing is not None,
                       "logs": [inputs.relative(log) for log in logs], "verified_execution_conclusion": None})
        if outgoing is not None and isinstance(outgoing.get("metrics"), dict) and outgoing["metrics"]:
            available.append((state_out, outgoing["metrics"]))
    final = inputs.root / "final/metrics.json"
    final_exists = final.is_file()
    final_metrics = inputs.json(final) if final_exists else None
    if final_metrics:
        return stages, final_metrics, inputs.relative(final), "final_metrics_available", None
    final_problem = "final_metrics_empty" if final_metrics == {} else "final_metrics_invalid" if final_exists else "final_metrics_missing"
    if available:
        path, metrics = available[-1]
        return stages, metrics, inputs.relative(path), "partial_unfinished_stage_metrics", final_problem
    return stages, {}, None, "no_metrics_available", final_problem if final_exists else "no_final_or_stage_metrics"


def timing_report_sources(inputs):
    stages = sorted((p for p in inputs.root.rglob("*") if p.is_dir() and re.match(r"^\d+-openroad-sta", p.name)),
                    key=lambda p: natural_stage_key(p.relative_to(inputs.root)))
    # Restrict fallback to the last actual STA stage. Earlier corner reports
    # cannot be blended with a later stage and relabeled as final timing.
    return stages[-1] if stages else None


def corner_inventory(inputs, metrics, source, origins, unavailable):
    timing_stage = timing_report_sources(inputs)
    actual = {key.split("__corner:", 1)[1] for key in metrics if key.startswith("timing__") and "__corner:" in key}
    if timing_stage:
        actual |= {p.name for p in timing_stage.iterdir() if p.is_dir() and any(p.glob("*.rpt"))}
    corners = {}
    for corner in sorted(set(EXPECTED_CORNERS) | actual):
        record = {}
        for field, key in TIMING.items():
            label = "corners." + corner + "." + field
            metric_key = "timing__" + key + "__corner:" + corner
            value = numeric_field(metrics, (metric_key,), source, label, origins, unavailable)
            # Only an absent key permits report fallback; a recorded NaN or
            # invalid value remains unavailable instead of being hidden.
            report = timing_stage / corner / TIMING_REPORTS[field] if timing_stage and field in TIMING_REPORTS else None
            if metric_key not in metrics and report is not None and report.is_file():
                text = inputs.read(report).decode("utf-8", errors="replace")
                matches = re.findall(r"^" + re.escape(corner) + r":\s*(\S+)\s*$", text, re.M)
                if len(matches) == 1:
                    value, reason = number(matches[0])
                    origins[label] = {"path": inputs.relative(report), "keys": [corner + ":"]}
                    if reason:
                        unavailable[label] = reason
                    else:
                        unavailable.pop(label, None)
                else:
                    unavailable[label] = "timing_report_has_no_unique_corner_value"
            record[field] = value
        corners[corner] = record
    return corners, inputs.relative(timing_stage) if timing_stage else None


def routing_inventory(inputs, metrics, source, origins, unavailable):
    label = "global_route.total_overflow"
    value = numeric_field(metrics, ("global_route__overflow", "global_route__overflow__total"), source, label, origins, unavailable)
    logs = sorted(inputs.root.rglob("openroad-globalrouting*.log"), key=lambda p: natural_stage_key(p.relative_to(inputs.root)))
    layers = None
    selected = logs[-1] if logs else None
    if selected:
        text = inputs.read(selected).decode("utf-8", errors="replace")
        table = text.rsplit("Final congestion report:", 1)[-1] if "Final congestion report:" in text else ""
        found = {}
        for match in re.finditer(r"^(Metal\d+|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)", table, re.M):
            found[match[1]] = dict(zip(("resources", "demand", "usage_percent", "maximum_horizontal_overflow", "maximum_vertical_overflow", "total_overflow"),
                                     (int(match[2]), int(match[3]), float(match[4]), int(match[5]), int(match[6]), int(match[7]))))
        layers = found or None
        if not any(key in metrics for key in ("global_route__overflow", "global_route__overflow__total")) and "Total" in found:
            value = found["Total"]["total_overflow"]
            origins[label] = {"path": inputs.relative(selected), "keys": ["Final congestion report: Total"]}
            unavailable.pop(label, None)
        elif not found and value is None:
            unavailable[label] = "no_final_congestion_table"
    return {"total_overflow": value, "layers": layers, "source_log": inputs.relative(selected) if selected else None}


def summarize(run_directory, run_id, source_sha, artifacts, jobs_metadata, *, scope=None,
              workflow_metadata=None, source_correspondence=None, metadata_raw_hashes=None):
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0 or not isinstance(source_sha, str) or not GIT_SHA.fullmatch(source_sha):
        raise ValueError("A positive run ID and exact 40-character source commit are required")
    artifact_records = artifacts_identity(artifacts)
    jobs = normalized_jobs(jobs_metadata, run_id, source_sha)
    workflow = workflow_metadata or {}
    if workflow.get("id") not in (None, run_id) or workflow.get("head_sha") not in (None, source_sha):
        raise ValueError("Workflow metadata disagrees with the explicit run/source identity")
    inputs = Inputs(run_directory)
    stages, metrics, source, metric_status, fallback_reason = stages_and_metrics(inputs)
    origins, unavailable = {}, {}
    measurements = {field: numeric_field(metrics, aliases, source, "measurements." + field, origins, unavailable)
                    for field, aliases in MEASUREMENTS.items()}
    corners, timing_stage = corner_inventory(inputs, metrics, source, origins, unavailable)
    global_route = routing_inventory(inputs, metrics, source, origins, unavailable)
    correspondence = source_correspondence
    if correspondence is not None:
        if not isinstance(correspondence, dict):
            raise ValueError("Source correspondence input must be an object")
        for key in ("source_sha", "workflow_head_sha", "physical_source_sha"):
            if key in correspondence and correspondence[key] != source_sha:
                raise ValueError("Source correspondence identifies a different workflow commit")
    raw_hashes = metadata_raw_hashes or {}
    if any(not isinstance(value, str) or not SHA256.fullmatch(value) for value in raw_hashes.values()):
        raise ValueError("Metadata raw hashes must be complete SHA-256 values")
    for role in ("artifacts", "jobs"):
        if role not in raw_hashes:
            unavailable["metadata_raw_hashes." + role] = "caller_supplied_structured_metadata_has_no_recorded_raw_payload_hash"
    return {
        "schema_version": 1, "kind": "motif_v3_identified_physical_measurements",
        "source_sha": source_sha, "workflow_run_id": run_id,
        "workflow_run_url": workflow.get("html_url"),
        "workflow_status": workflow.get("status"), "workflow_conclusion": workflow.get("conclusion"),
        "artifacts": artifact_records,
        "extraction_scope": {"directory_label": inputs.root.name, "scope": scope or "single explicit official flow run directory",
                             "metrics_status": metric_status, "metrics_source": source,
                             "fallback_reason": fallback_reason, "timing_report_stage": timing_stage},
        "measurements": measurements, "corners": corners, "global_route": global_route,
        "stages": stages, "jobs": jobs, "source_correspondence": correspondence,
        "metric_sources": origins, "unavailable_reasons": unavailable,
        "input_files": inputs.records, "input_problems": inputs.problems,
        "metadata_raw_hashes": raw_hashes,
        "qualification": {"decision": None, "reason": "Measurement extraction only; the separate attempt ledger must verify eligibility, official precheck, routed functional tests, exact source correspondence and closure."},
        "limitations": ["A state_out file is published state, not proof of job success.",
                        "Final metrics presence does not establish completed workflow or physical qualification.",
                        "Unfinished stage measurements and timing reports retain their actual stage identity.",
                        "Zero-delay routed simulation and STA are distinct checks; missing values are unavailable."],
    }


def read_metadata(path):
    data = path.read_bytes()
    return json.loads(data), digest(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--artifacts", required=True, type=Path, help="Downloaded artifact IDs/names/raw archive hashes as JSON")
    parser.add_argument("--jobs", required=True, type=Path, help="Recorded workflow jobs metadata as JSON")
    parser.add_argument("--workflow", type=Path, help="Optional recorded workflow metadata as JSON")
    parser.add_argument("--source-correspondence", type=Path)
    parser.add_argument("--scope")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        values, raw_hashes = {}, {}
        for key in ("artifacts", "jobs", "workflow", "source_correspondence"):
            path = getattr(args, key)
            if path:
                values[key], raw_hashes[key] = read_metadata(path)
        report = summarize(args.run_directory, args.run_id, args.source_sha, values["artifacts"], values["jobs"],
                           scope=args.scope, workflow_metadata=values.get("workflow"),
                           source_correspondence=values.get("source_correspondence"), metadata_raw_hashes=raw_hashes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    except (ValueError, OSError) as exc:
        print("FAIL physical measurement extraction: " + str(exc), file=sys.stderr)
        return 1
    print("Recorded " + report["extraction_scope"]["metrics_status"] + "; qualification decision remains unavailable")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
