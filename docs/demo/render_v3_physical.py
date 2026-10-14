"""Render identified v3 physical artifacts without running a physical flow.

This is a presentation tool, not a qualification gate. Its input receipt binds
the workflow's exact source commit, frozen RTL and each physical file used.
Missing measurements and views remain unavailable; no layout is invented.
See physical_views.md for the receipt format and an invocation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import html
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
KINDS = ("floorplan", "placement", "routing", "gds")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
MEASUREMENTS = {
    "stdcell_count": "design__instance__count__stdcell",
    "stdcell_area_um2": "design__instance__area__stdcell",
    "register_count": "design__instance__count__class:sequential_cell",
    "core_area_um2": "design__core__area",
    "stdcell_utilization": "design__instance__utilization__stdcell",
    "detailed_wirelength_um": "route__wirelength",
    "global_wirelength_um": "global_route__wirelength",
    "vias": "route__vias",
    "detailed_route_drc": "route__drc_errors",
    "magic_drc": "magic__drc_error__count",
    "lvs_errors": "design__lvs_error__count",
    "antenna_violating_nets": "antenna__violating__nets",
    "antenna_violating_pins": "antenna__violating__pins",
    "route_antenna_violations": "route__antenna_violation__count",
}
TIMING = {
    "setup_worst_slack_ns": "setup__ws", "hold_worst_slack_ns": "hold__ws",
    "setup_wns_ns": "setup__wns", "hold_wns_ns": "hold__wns",
    "setup_tns_ns": "setup__tns", "hold_tns_ns": "hold__tns",
    "setup_violations": "setup_vio__count", "hold_violations": "hold_vio__count",
}


def digest(data, lf=False):
    return hashlib.sha256(data.replace(b"\r\n", b"\n") if lf else data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative_file(root, name):
    """Only files inside the explicit extracted artifact directory are inputs."""
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("Expected a relative artifact file path")
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Missing or outside-directory artifact file: " + name)
    return path


class IdentifiedFiles:
    def __init__(self, root, hashes):
        self.root = root.resolve()
        self.hashes = hashes
        self.used = {}
        if not isinstance(hashes, dict):
            raise ValueError("Correspondence requires files_sha256_raw")

    def read(self, name):
        path = relative_file(self.root, name)
        expected = self.hashes.get(name)
        if not isinstance(expected, str) or not SHA256.fullmatch(expected):
            raise ValueError("Physical file has no identified raw SHA-256: " + name)
        data = path.read_bytes()
        actual = digest(data)
        if actual != expected:
            raise ValueError("Physical artifact hash mismatch: " + name)
        self.used[name] = {"sha256_raw": actual, "bytes": len(data)}
        return data

    def available(self, predicate):
        # Discover only receipt-bound inputs, never arbitrary nearby files.
        return sorted(name for name in self.hashes if predicate(name))


def validate_identity(directory, manifest_path, manifest_sha, receipt_path, source_sha):
    if not GIT_SHA.fullmatch(source_sha) or not SHA256.fullmatch(manifest_sha):
        raise ValueError("Source SHA and manifest SHA-256 must be complete lowercase hashes")
    manifest_bytes = manifest_path.read_bytes()
    if digest(manifest_bytes, lf=True) != manifest_sha:
        raise ValueError("Explicit frozen manifest identity does not match its bytes")
    manifest = json.loads(manifest_bytes)
    if manifest.get("architecture_version") != 3:
        raise ValueError("An architecture version 3 frozen manifest is required")
    expected = {name: value for name, value in manifest["source_hashes"].items()
                if name.startswith("src/") and name.endswith(".sv")}
    if not expected:
        raise ValueError("Frozen manifest has no RTL inventory")
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    if receipt.get("source_sha") != source_sha or receipt.get("workflow_head_sha") != source_sha:
        raise ValueError("Receipt must identify the exact workflow source commit")
    if receipt.get("frozen_manifest_sha256_lf") != manifest_sha:
        raise ValueError("Receipt identifies a different frozen semantic manifest")
    if receipt.get("rtl_source_hashes_lf") != expected:
        raise ValueError("Receipt RTL inventory differs from frozen v3 (exact LF equality required)")
    artifact = receipt.get("artifact", {})
    if (not isinstance(artifact.get("id"), int) or artifact["id"] <= 0
            or not artifact.get("name") or not SHA256.fullmatch(artifact.get("archive_sha256_raw", ""))
            or not re.fullmatch(r"https://github\.com/[^/]+/[^/]+/actions/runs/\d+", artifact.get("workflow_run_url", ""))):
        raise ValueError("A workflow URL, artifact ID/name and archive SHA-256 are required")
    source = receipt.get("source", {})
    role = source.get("role")
    roles = {"bundled_workflow_sources", "materialized_identified_workflow_commit"}
    if role not in roles:
        raise ValueError("Receipt must distinguish bundled RTL from materialized workflow-commit RTL")
    if role == "bundled_workflow_sources" and not source.get("directory"):
        raise ValueError("Bundled source identity requires its actual extracted directory")
    if role == "materialized_identified_workflow_commit" and not source.get("derivation"):
        raise ValueError("Materialized sources require a recorded derivation")
    if source.get("directory"):
        source_root = (directory / source["directory"]).resolve()
        if not source_root.is_relative_to(directory.resolve()) or not source_root.is_dir():
            raise ValueError("Source directory must be inside the identified artifact directory")
        source_files = list(source_root.rglob("*.sv"))
        if any(not p.resolve().is_relative_to(source_root) for p in source_files):
            raise ValueError("RTL source symlink points outside the identified source directory")
        actual_names = {"src/" + p.relative_to(source_root).as_posix() for p in source_files}
        if actual_names != expected.keys():
            raise ValueError("Extracted RTL file set differs from the frozen inventory")
        actual = {name: digest((source_root / name.removeprefix("src/")).read_bytes(), lf=True)
                  for name in expected}
        method = "hashes read from the explicitly identified " + role + " directory"
    else:
        names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", source_sha], cwd=ROOT, text=True).splitlines()
        names = {name for name in names if name.startswith("src/") and name.endswith(".sv")}
        if names != expected.keys():
            raise ValueError("Identified workflow commit RTL set differs from the frozen inventory")
        actual = {name: digest(subprocess.check_output(["git", "show", f"{source_sha}:{name}"], cwd=ROOT), lf=True)
                  for name in expected}
        method = "independent git show of the receipt's exact workflow_head_sha"
    if actual != expected:
        raise ValueError("Physical source RTL hashes differ from frozen v3")
    if source.get("directory") and role == "materialized_identified_workflow_commit":
        # Verify materialization against the named commit, not just against a
        # matching working tree. No declaration-only exception is accepted.
        for name, value in actual.items():
            committed = subprocess.check_output(["git", "show", f"{source_sha}:{name}"], cwd=ROOT)
            if digest(committed, lf=True) != value:
                raise ValueError("Materialized RTL does not match the identified workflow commit")
    return receipt, {
        "source_sha": source_sha, "workflow_head_sha": source_sha,
        "frozen_manifest_sha256_lf": manifest_sha,
        "correspondence_receipt_sha256_raw": digest(receipt_bytes),
        "source_role": role, "source_verification": method,
        "rtl_source_hashes_lf": actual, "exact_rtl_correspondence": True,
        "artifact": artifact,
    }


def finite_number(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Non-finite or non-numeric physical metric")
    return value


def metric_inventory(files, receipt):
    path = receipt.get("metrics_path")
    if not path:
        matches = files.available(lambda n: n.endswith("/final/metrics.json") or n == "final/metrics.json")
        if len(matches) > 1:
            raise ValueError("Multiple final metrics inputs; specify metrics_path")
        path = matches[0] if matches else None
    raw = json.loads(files.read(path)) if path else {}
    corners = sorted({k.split("__corner:", 1)[1] for k in raw if k.startswith("timing__") and "__corner:" in k})
    # Explicitly retain expected corners when their reports are absent.
    corners = sorted(set(corners) | set(receipt.get("expected_corners", [])))
    result = {
        "source": path, "scope": "final metrics" if path else "unavailable",
        "measurements": {name: finite_number(raw.get(key)) for name, key in MEASUREMENTS.items()},
        "corners": {corner: {name: finite_number(raw.get("timing__" + key + "__corner:" + corner))
                             for name, key in TIMING.items()} for corner in corners},
        "global_route_overflow": None,
        "official_precheck": receipt.get("checks", {}).get("official_precheck"),
        "routed_netlist_functional_tests": receipt.get("checks", {}).get("routed_netlist_functional_tests"),
        "note": "Direct artifact measurements and receipt check statuses; no physical closure decision is made by this renderer.",
    }
    logs = files.available(lambda n: n.endswith("/openroad-globalrouting.log"))
    if len(logs) == 1:
        text = files.read(logs[0]).decode("utf-8")
        table = text.rsplit("Final congestion report:", 1)[-1] if "Final congestion report:" in text else ""
        layers = {}
        for match in re.finditer(r"^(Metal\d+|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)", table, re.M):
            layers[match[1]] = dict(zip(("resources", "demand", "usage_percent", "maximum_horizontal_overflow", "maximum_vertical_overflow", "total_overflow"),
                                      (int(match[2]), int(match[3]), float(match[4]), int(match[5]), int(match[6]), int(match[7]))))
        result["global_route_layers"] = layers or None
        result["global_route_overflow"] = layers.get("Total", {}).get("total_overflow")
        result["global_route_log"] = logs[0]
    else:
        result["global_route_layers"] = None
        result["global_route_log"] = None
    return result


def stage_inventory(files):
    stages = []
    for name in files.available(lambda n: n.endswith("/state_out.json")):
        state = json.loads(files.read(name))
        stages.append({"path": name.rsplit("/", 1)[0], "state_out_sha256_raw": files.used[name]["sha256_raw"],
                       "status": "state_out_available", "metrics": state.get("metrics"),
                       "note": "A published state file does not by itself prove workflow/job success."})
    return stages


def section(text, name):
    match = re.search(r"^" + name + r"\s+\d+\s*;(.*?)^END " + name + r"\b", text, re.M | re.S)
    return match[1] if match else ""


def parse_def(data):
    """Extract actual DEF coordinates; never invent LEF widths or GDS polygons."""
    text = data.decode("utf-8")
    units = re.search(r"\bUNITS DISTANCE MICRONS\s+(\d+)\s*;", text)
    die = re.search(r"\bDIEAREA\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*;", text)
    design = re.search(r"\bDESIGN\s+(\S+)\s*;", text)
    if not units or not die or not design:
        raise ValueError("DEF requires declared units, design and rectangular DIEAREA")
    scale = int(units[1])
    if scale <= 0:
        raise ValueError("Invalid DEF distance units")
    rows = []
    for m in re.finditer(r"^ROW\s+\S+\s+\S+\s+(-?\d+)\s+(-?\d+)\s+\S+\s+DO\s+(\d+)\s+BY\s+(\d+)\s+STEP\s+(-?\d+)\s+(-?\d+)\s*;", text, re.M):
        x, y, nx, ny, dx, dy = map(int, m.groups())
        for iy in range(ny):
            rows.append([[x / scale, (y + iy * dy) / scale], [(x + (nx - 1) * dx) / scale, (y + iy * dy) / scale]])
    origins = []
    for statement in section(text, "COMPONENTS").split(";"):
        m = re.search(r"^\s*-\s+(\S+)\s+(\S+).*?\+\s+(?:PLACED|FIXED|COVER)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)", statement, re.S)
        if m:
            origins.append({"instance": m[1], "master": m[2], "x_um": int(m[3]) / scale, "y_um": int(m[4]) / scale, "orientation": m[5]})
    pins = []
    for statement in section(text, "PINS").split(";"):
        m = re.search(r"^\s*-\s+(\S+).*?\+\s+(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)", statement, re.S)
        if m:
            pins.append({"name": m[1], "x_um": int(m[2]) / scale, "y_um": int(m[3]) / scale})
    paths = defaultdict(list)
    unsupported = 0
    for statement in section(text, "NETS").split(";"):
        for m in re.finditer(r"(?:\+\s+(?:ROUTED|FIXED|COVER)|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW\s+|\+\s+(?:ROUTED|FIXED|COVER)|$)", statement, re.S):
            body = m[2].split("RECT", 1)[0]
            points = []
            previous = None
            for point in re.finditer(r"\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+-?\d+)?\s*\)", body):
                if previous is None and "*" in point.groups():
                    unsupported += 1
                    break
                current = tuple(previous[i] if value == "*" else int(value) for i, value in enumerate(point.groups()))
                points.append([current[0] / scale, current[1] / scale])
                previous = current
            if len(points) > 1:
                paths[m[1]].extend([[a, b] for a, b in zip(points, points[1:])])
    return {"design": design[1], "units_per_um": scale, "die_bbox_um": [int(v) / scale for v in die.groups()],
            "row_site_origin_spans_um": rows, "component_origins": origins, "pin_origins": pins,
            "signal_path_segments_um": dict(paths), "unsupported_initial_wildcards": unsupported}


def save_figure(fig, directory, kind):
    svg = directory / f"{kind}.svg"
    fig.savefig(svg, metadata={"Date": None})
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8", newline="\n")
    fig.savefig(directory / f"{kind}.png", dpi=160, metadata={"Software": "MOTIF identified physical artifact renderer"})


def render_def(geometry, kind, directory, source_path, source_sha):
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams.update({"svg.hashsalt": "motif-identified-physical", "svg.fonttype": "none", "text.parse_math": False})
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Rectangle
    if kind == "placement" and not geometry["component_origins"]:
        return None, "DEF has no placed component origins"
    if kind == "routing" and not geometry["signal_path_segments_um"]:
        return None, "DEF has no routed signal paths"
    fig, ax = plt.subplots(figsize=(12, 7))
    x1, y1, x2, y2 = geometry["die_bbox_um"]
    ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, edgecolor="#152a35", linewidth=1.2))
    if kind == "floorplan":
        ax.add_collection(LineCollection(geometry["row_site_origin_spans_um"], colors="#8dafbb", linewidths=.3))
        caption = "Actual DIEAREA, spans between first/last row site origins, and placed pin origins; cell/row physical widths are not inferred."
    elif kind == "placement":
        points = geometry["component_origins"]
        ax.scatter([p["x_um"] for p in points], [p["y_um"] for p in points], s=2, color="#246e57", alpha=.55, rasterized=False)
        caption = f"Actual placed component origins ({len(points):,}); symbols are points, not inferred cell footprints."
    else:
        palette = ("#ad3e49", "#315cb0", "#228063", "#99761c", "#904ca3", "#197d88")
        for i, (layer, paths) in enumerate(sorted(geometry["signal_path_segments_um"].items())):
            ax.add_collection(LineCollection(paths, colors=palette[i % len(palette)], linewidths=.25, alpha=.5, label=f"{layer}: {len(paths):,} segments"))
        ax.legend(loc="lower right", fontsize=7, framealpha=.95)
        caption = "Actual NETS routed path centerlines; wire widths, via cuts, RECT patches and SPECIALNETS power geometry are omitted."
    pins = geometry["pin_origins"]
    if pins:
        ax.scatter([p["x_um"] for p in pins], [p["y_um"] for p in pins], s=9, marker="s", color="#222222")
    margin = max(x2 - x1, y2 - y1) * .025
    ax.set_xlim(x1 - margin, x2 + margin)
    ax.set_ylim(y1 - margin, y2 + margin)
    ax.set_aspect("equal")
    ax.set_xlabel("x (µm)")
    ax.set_ylabel("y (µm)")
    ax.set_title(f"MOTIF {kind} — identified DEF coordinates\n{geometry['design']} · source {source_sha[:12]}", fontsize=12)
    fig.text(.02, .025, caption + "\nArtifact: " + source_path, fontsize=7, va="bottom", wrap=True)
    fig.tight_layout(rect=(0, .08, 1, 1))
    save_figure(fig, directory, kind)
    plt.close(fig)
    return [f"{kind}.svg", f"{kind}.png"], caption


def choose_view(files, receipt, kind):
    recipe = receipt.get("views", {}).get(kind)
    if recipe is not None:
        if not isinstance(recipe, dict) or set(recipe) - {"image", "geometry"}:
            raise ValueError("View recipe accepts only image and geometry paths")
        return recipe
    def choose(predicate):
        matches = files.available(predicate)
        if len(matches) > 1:
            raise ValueError(f"Multiple {kind} inputs; identify one explicitly in receipt.views")
        return matches[0] if matches else None
    if kind == "gds":
        return {"image": choose(lambda n: "/final/render/" in n and n.endswith((".png", ".svg"))),
                "geometry": choose(lambda n: "/final/gds/" in n and n.endswith(".gds"))}
    stages = {"floorplan": "-openroad-floorplan/", "placement": "-openroad-detailedplacement/", "routing": "-openroad-detailedrouting/"}
    stage = stages[kind]
    return {"image": choose(lambda n: stage in n and n.endswith((".png", ".svg"))),
            "geometry": choose(lambda n: stage in n and n.endswith(".def"))}


def render_view(files, recipe, kind, output, identity):
    geometry_path, image_path = recipe.get("geometry"), recipe.get("image")
    result = {"status": "unavailable", "geometry": geometry_path, "image": image_path, "outputs": None, "reason": None}
    if kind == "gds" and not geometry_path:
        result["reason"] = "No identified GDS geometry; a nearby image cannot establish a v3 GDS view"
        return result
    geometry_bytes = files.read(geometry_path) if geometry_path else None
    if kind == "gds" and geometry_bytes and not geometry_bytes.startswith(b"\x00\x06\x00\x02"):
        raise ValueError("Identified GDS has no GDSII HEADER record")
    if image_path:
        data = files.read(image_path)
        suffix = Path(image_path).suffix.lower()
        if suffix == ".png":
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Identified PNG has an invalid signature")
        elif suffix == ".svg":
            if b"<svg" not in data[:10000]:
                raise ValueError("Identified SVG has no SVG root")
        else:
            raise ValueError("Existing physical views must be PNG or SVG")
        filename = kind + "_artifact" + suffix
        (output / filename).write_bytes(data)
        result.update(status="available", outputs=[filename], reason="Unmodified image from the identified physical artifact")
        return result
    if geometry_path and kind != "gds" and Path(geometry_path).suffix.lower() == ".def":
        geometry = parse_def(geometry_bytes)
        outputs, caption = render_def(geometry, kind, output, geometry_path, identity["source_sha"])
        result.update(status="available" if outputs else "unavailable", outputs=outputs, reason=caption,
                      coordinate_inventory={"design": geometry["design"], "die_bbox_um": geometry["die_bbox_um"],
                                            "row_count": len(geometry["row_site_origin_spans_um"]),
                                            "placed_component_count": len(geometry["component_origins"]),
                                            "placed_pin_count": len(geometry["pin_origins"]),
                                            "route_segments_by_layer": {k: len(v) for k, v in geometry["signal_path_segments_um"].items()},
                                            "unsupported_initial_wildcards": geometry["unsupported_initial_wildcards"]})
        return result
    result["reason"] = "Identified GDS exists but no official rendered image is available" if kind == "gds" and geometry_path else "No identified image or supported DEF geometry for this stage"
    return result


def write_html(report, output):
    esc = html.escape
    pieces = ["<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>MOTIF identified v3 physical views</title>",
              "<style>body{max-width:1100px;margin:2em auto;padding:0 1em;font:16px system-ui;color:#172d37}img{max-width:100%;height:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eff3f5;padding:1em}figure{margin:2em 0}figcaption{font-size:.9em}a{color:#175f86}</style>",
              "<h1>MOTIF v3 identified physical views</h1><p>Source correspondence is verified. This renderer makes no physical qualification decision. Unavailable inputs remain unavailable.</p>",
              "<p>Workflow: <a href='" + esc(report["identity"]["artifact"]["workflow_run_url"], quote=True) + "'>identified run</a> · source <code>" + esc(report["identity"]["source_sha"]) + "</code></p>"]
    for kind, view in report["views"].items():
        pieces.append("<h2>" + esc(kind.title()) + "</h2>")
        if view["outputs"]:
            image = next((p for p in view["outputs"] if p.endswith(".png")), view["outputs"][0])
            pieces.append("<figure><img src='" + esc(image, quote=True) + "' alt='Identified " + esc(kind) + " view'><figcaption>" + esc(view["reason"]) + "</figcaption></figure>")
        else:
            pieces.append("<p>Unavailable: " + esc(view["reason"]) + "</p>")
    pieces.append("<h2>Direct metric inventory</h2><p>Null means unavailable. Check statuses are quoted from the correspondence receipt; missing checks are not passes.</p><pre>" + esc(json.dumps(report["metrics"], indent=2, allow_nan=False)) + "</pre><p><a href='physical_views.json'>Full identity and file inventory</a></p></html>")
    (output / "index.html").write_text("\n".join(pieces) + "\n", encoding="utf-8", newline="\n")


def run(directory, source_sha, manifest_path, manifest_sha, receipt_path, output, require_views=()):
    directory, output = directory.resolve(), output.resolve()
    if not directory.is_dir():
        raise ValueError("Explicit artifact directory does not exist")
    if output == directory or output.is_relative_to(directory):
        raise ValueError("Keep rendered output outside the immutable artifact directory")
    receipt, identity = validate_identity(directory, manifest_path, manifest_sha, receipt_path, source_sha)
    files = IdentifiedFiles(directory, receipt.get("files_sha256_raw"))
    if output.exists() and any(output.iterdir()):
        previous_path = output / "physical_views.json"
        if not previous_path.is_file() or read_json(previous_path).get("identity") != identity:
            raise ValueError("Nonempty output directory belongs to a different or unidentified attempt; choose a fresh output directory")
        previous = read_json(previous_path)
        expected_outputs = {"index.html", "physical_views.json", *previous.get("output_files_sha256_raw", {})}
        if {p.name for p in output.iterdir()} != expected_outputs:
            raise ValueError("Output directory contains stale or unexpected files; choose a fresh output directory")
    output.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "kind": "identified_v3_physical_views", "identity": identity,
              "classification": "presentation_only", "metrics": metric_inventory(files, receipt),
              "stages": stage_inventory(files), "views": {}}
    for kind in KINDS:
        report["views"][kind] = render_view(files, choose_view(files, receipt, kind), kind, output, identity)
    report["used_files"] = files.used
    report["output_files_sha256_raw"] = {p.name: digest(p.read_bytes()) for kind in KINDS for name in report["views"][kind]["outputs"] or [] for p in [output / name]}
    (output / "physical_views.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    write_html(report, output)
    missing = [name for name in require_views if report["views"][name]["status"] != "available"]
    if missing:
        raise ValueError("Required physical views unavailable: " + ", ".join(missing))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-directory", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256-lf", required=True)
    parser.add_argument("--correspondence", required=True, type=Path)
    parser.add_argument("--output", default=Path("build/demo/physical_v3"), type=Path)
    parser.add_argument("--require-view", choices=KINDS, action="append", default=[])
    args = parser.parse_args()
    try:
        report = run(args.artifact_directory, args.source_sha, args.manifest, args.manifest_sha256_lf, args.correspondence, args.output, args.require_view)
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print("FAIL identified physical rendering: " + str(exc), file=sys.stderr)
        return 1
    available = [name for name, view in report["views"].items() if view["status"] == "available"]
    print("PASS source identity; available views: " + (", ".join(available) or "none") + "; physical closure is not assessed")
    print(args.output / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
