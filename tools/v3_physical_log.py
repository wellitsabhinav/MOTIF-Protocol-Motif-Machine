"""Capture partial physical observations from an identified decoded job log.

This reporting tool never qualifies a physical result. Log progress, next-step
entry times and resizer tables do not replace final metrics or corner STA.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re


def capture(log, workflow, jobs):
    raw = Path(log).read_bytes()
    lines = raw.decode("utf-8-sig").splitlines()
    run = json.loads(Path(workflow).read_text())
    job_rows = json.loads(Path(jobs).read_text())["jobs"]
    job = next(row for row in job_rows if row["name"] == "gds")
    if job["run_id"] != run["id"] or job["head_sha"] != run["head_sha"]:
        raise ValueError("Job and workflow source identities differ")
    observations, stages, excerpts = [], [], []
    stage = None
    repair_mode = None
    corners_loaded = []
    for index, line in enumerate(lines):
        match = re.match(r"(\d{4}-\d\d-\d\dT\S+Z)\s+(.*)", line)
        if not match:
            continue
        timestamp, body = match.groups()
        entry = re.search(r"Running '([^']+)'", body)
        if entry:
            stage = {"name": entry[1], "entered_at": timestamp,
                     "log_line": index + 1, "next_step_entered_at": None,
                     "entry_to_next_step_seconds": None}
            if stages:
                prior = stages[-1]
                prior["next_step_entered_at"] = timestamp
                prior["entry_to_next_step_seconds"] = round((
                    datetime.fromisoformat(timestamp) -
                    datetime.fromisoformat(prior["entered_at"])).total_seconds(), 6)
            stages.append(stage)
            repair_mode = None
            corners_loaded = []
        timing_corner = re.search(r"Reading timing models for corner ([\w.]+)", body)
        if timing_corner:
            if timing_corner[1] not in corners_loaded:
                corners_loaded.append(timing_corner[1])
        patterns = (
            ("core_area_um2", r"Core area:\s+([\d.]+) um\^2"),
            ("placement_utilization_percent", r"Utilization:\s+([\d.]+) %"),
            ("placement_target_density", r"Placement target density:\s+([\d.]+)"),
            ("global_wirelength_um", r"Total wirelength:\s+(\d+) um"),
            ("partial_detail_wirelength_um", r"Total wire length = (\d+) um"),
            ("partial_detail_vias", r"Total number of vias = (\d+)"),
            ("partial_detail_violations", r"Number of violations = (\d+)"),
            ("partial_antenna_violations", r"Found (\d+) antenna violations"),
        )
        values = {}
        for key, pattern in patterns:
            found = re.search(pattern, body)
            if found:
                values[key] = float(found[1]) if "." in found[1] else int(found[1])
        congestion = re.match(r"(Metal\d+|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)", body)
        if congestion:
            values["global_congestion"] = dict(zip(
                ("layer", "resource", "demand", "usage_percent", "max_horizontal_overflow",
                 "max_vertical_overflow", "total_overflow"),
                (congestion[1], int(congestion[2]), int(congestion[3]), float(congestion[4]),
                 int(congestion[5]), int(congestion[6]), int(congestion[7]))))
        cells = re.match(r"Total\s+(\d+)\s+([\d.]+)\s*$", body)
        if cells:
            values.update(partial_cells=int(cells[1]), partial_cell_area_um2=float(cells[2]))
        progress = re.search(r"Completing (\d+)% with (\d+) violations", body)
        if progress:
            values.update(partial_detail_completion_percent=int(progress[1]),
                          partial_detail_violations=int(progress[2]))
        mode = re.search(r"repair_timing .*?-(setup|hold)\b", body)
        if mode:
            repair_mode = mode[1]
        if body.strip().startswith("final |") and repair_mode:
            fields = [field.strip() for field in body.split("|")]
            # These two pinned resizer tables wrap in the decoded Actions log.
            if repair_mode == "setup" and len(fields) == 8:
                tail = lines[index + 1].split("Z", 1)[-1].strip()
                remaining = [field.strip() for field in tail.split("|")]
                if len(remaining) >= 4:
                    values["partial_resizer_setup"] = {
                        "wns_ns": float(fields[-1]), "tns_ns": float(remaining[1]),
                        "violating_endpoints": int(remaining[2]),
                        "corner": corners_loaded[0] if len(corners_loaded) == 1 else None,
                        "corners_loaded": list(corners_loaded),
                        "scope": "resizer progress with estimated parasitics; rows have no individual corner label"}
            elif repair_mode == "hold" and len(fields) == 8:
                values["partial_resizer_hold"] = {
                    "wns_ns": float(fields[5]), "tns_ns": float(fields[6]),
                    "corner": corners_loaded[0] if len(corners_loaded) == 1 else None,
                    "corners_loaded": list(corners_loaded),
                    "scope": "resizer progress with estimated parasitics; rows have no individual corner label"}
        cancellation = "##[error]The operation was canceled" in body
        if values or cancellation:
            observations.append({"timestamp": timestamp, "log_line": index + 1,
                                 "stage": stage["name"] if stage else None, **values,
                                 **({"cancellation_message": True} if cancellation else {})})
            excerpts.append(f"{index + 1}: {line.rstrip()}")
            if "partial_resizer_setup" in values:
                excerpts.append(f"{index + 2}: {lines[index + 1].rstrip()}")
        elif entry or "OpenROAD will use None threads" in body:
            excerpts.append(f"{index + 1}: {line.rstrip()}")
    result = {"schema_version": 3, "workflow_run_id": run["id"], "source_sha": run["head_sha"],
              "workflow_status": run["status"], "workflow_conclusion": run["conclusion"],
              "job_id": job["id"], "job_started_at": job["started_at"],
              "job_completed_at": job["completed_at"], "log_sha256_raw": hashlib.sha256(raw).hexdigest(),
              "log_bytes": len(raw), "log_lines": len(lines), "stages": stages,
              "observations": observations, "final_metrics": None, "cancellation_cause": None,
              "scope": "Partial decoded log observations only; step intervals include transition overhead; no final STA, DRC, LVS, source-archive or physical qualification claim"}
    return result, "\n".join(excerpts) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--jobs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--excerpt", required=True, type=Path)
    args = parser.parse_args()
    data, excerpt = capture(args.log, args.workflow, args.jobs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    args.excerpt.write_text(excerpt, encoding="utf-8", newline="\n")
    print("RECORDED partial observations", len(data["stages"]), "steps; final metrics unavailable")


if __name__ == "__main__":
    main()
