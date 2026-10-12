"""Extract a small portable summary from official CMOS5L flow artifacts."""
import argparse
import json
import math
import re
from pathlib import Path


def summarize(root, run_id, source_sha, scope=None):
    root = Path(root)
    metrics = json.loads((root / "final/metrics.json").read_text())
    placement = next(root.glob("*-openroad-globalplacement/openroad-globalplacement.log")).read_text()
    routing = next(root.glob("*-openroad-globalrouting/openroad-globalrouting.log")).read_text()
    sta = next(root.glob("*-openroad-stapostpnr"))
    corners = {}
    for directory in sorted(sta.iterdir()):
        if not directory.is_dir():
            continue
        suffix = "__corner:" + directory.name
        corner = {field: metrics["timing__" + key + suffix] for field, key in {
            "setup_worst_slack_ns": "setup__ws", "hold_worst_slack_ns": "hold__ws",
            "setup_wns_ns": "setup__wns", "hold_wns_ns": "hold__wns",
            "setup_tns_ns": "setup__tns", "hold_tns_ns": "hold__tns",
            "setup_violations": "setup_vio__count", "hold_violations": "hold_vio__count"}.items()}
        report = (directory / "max.rpt").read_text()
        corner["first_reported_setup_path"] = {
            "startpoint": re.search(r"^Startpoint: (.+)$", report, re.M)[1],
            "endpoint": re.search(r"^Endpoint: (.+)$", report, re.M)[1]}
        corners[directory.name] = corner
    layers = {}
    table = routing.rsplit("Final congestion report:", 1)[1]
    for match in re.finditer(r"^(Metal\d+|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)", table, re.M):
        layers[match[1]] = dict(zip(("resources", "demand", "usage_percent", "maximum_horizontal_overflow", "maximum_vertical_overflow", "total_overflow"),
                                   (int(match[2]), int(match[3]), float(match[4]), int(match[5]), int(match[6]), int(match[7]))))
    fields = {"stdcell_count": "design__instance__count__stdcell", "stdcell_area_um2": "design__instance__area__stdcell",
              "register_count": "design__instance__count__class:sequential_cell", "core_area_um2": "design__core__area",
              "stdcell_utilization": "design__instance__utilization__stdcell", "detailed_wirelength_um": "route__wirelength",
              "global_wirelength_um": "global_route__wirelength", "vias": "route__vias", "detailed_route_drc": "route__drc_errors",
              "magic_drc": "magic__drc_error__count", "lvs_errors": "design__lvs_error__count",
              "max_fanout_violations": "design__max_fanout_violation__count", "max_slew_violations": "design__max_slew_violation__count",
              "max_cap_violations": "design__max_cap_violation__count", "hold_buffer_count": "design__instance__count__hold_buffer",
              "timing_repair_buffer_area_um2": "design__instance__area__class:timing_repair_buffer"}
    result = {"schema_version": 1, "kind": "routed_cmos5l_subset", "source_sha": source_sha,
              "workflow_run_url": f"https://github.com/wellitsabhinav/MOTIF-Protocol-Motif-Machine/actions/runs/{run_id}",
              "clock_period_ns": 20, "tile_size": "6x4", "die_bbox_um": metrics["design__die__bbox"],
              "scope": scope or "SPI target, UART receive and externally framed timed stream; I2C model only; reference has no routed comparison",
              "measurements": {field: metrics[key] for field, key in fields.items()}, "corners": corners,
              "global_route_layers": layers,
              "placement_weighted_congestion": float(re.search(r"final weighted congestion: ([\d.]+)", placement)[1]),
              "limitations": "STA under official template constraints; zero-delay gate simulation is separate. Average layer usage does not bound local concentration. Cell area excludes filler; tile allocation is not optimized."}
    assert all(math.isfinite(value) for value in result["measurements"].values())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory")
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", default="reports/physical_motif.json")
    parser.add_argument("--scope", help="Explicit tested protocol scope; does not change historical reports")
    args = parser.parse_args()
    result = summarize(args.run_directory, args.run_id, args.source_sha, args.scope)
    Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(args.output)
