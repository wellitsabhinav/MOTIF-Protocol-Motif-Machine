"""Select modest, explicitly unqualified previews of identified physical views.

Consumes only render_v3_physical.py output plus the identified metric receipt.
The image wrapper adds a status banner and optionally reduces preview size;
it never infers layout geometry. Full images, route SVG and raw geometry stay
in build/. Floorplan retains vector SVG; other dense views select PNG only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import textwrap
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
from matplotlib import font_manager

FROZEN_MANIFEST = Path(__file__).resolve().parents[2] / "experiments/temporal_qualification/frozen_v3_manifest.json"
FROZEN_MANIFEST_SHA256_LF = "71d5b07b5524fb6fa702357291eb35f52eccc5861111f7824b6fb9ead98a3047"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verified_preregistration(manifest_path, view_manifest_hash):
    """Read preregistration only after the actual source/view boundary matches."""
    raw = manifest_path.read_bytes()
    actual = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    require(actual == view_manifest_hash == FROZEN_MANIFEST_SHA256_LF,
            "Frozen manifest LF hash differs from the identified physical view/source boundary")
    manifest = json.loads(raw)
    require(manifest.get("architecture_version") == 3, "Expected the frozen v3 manifest")
    preregistration = manifest.get("preregistration", {})
    require(re.fullmatch(r"[0-9a-f]{40}", preregistration.get("commit", ""))
            and re.fullmatch(r"[0-9a-f]{64}", preregistration.get("sha256_lf", "")),
            "Frozen preregistration identity is absent or invalid")
    return dict(preregistration), actual


def wrapper_png(source, target, kind, identity, run_id):
    image = Image.open(source).convert("RGB")
    original = image.size
    image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    width = max(image.width, 1000)
    canvas = Image.new("RGB", (width, image.height + 142), "white")
    canvas.paste(image, ((width - image.width) // 2, 108))
    draw = ImageDraw.Draw(canvas)
    font_path = font_manager.findfont("DejaVu Sans")
    title = ImageFont.truetype(font_path, 25)
    detail = ImageFont.truetype(font_path, 17)
    draw.text((24, 16), f"UNQUALIFIED · MOTIF attempt 2 {kind}", fill="#a44737", font=title)
    draw.text((24, 53), f"Run {run_id} · source {identity['source_sha'][:12]} · official GDS job failure", fill="#374e56", font=detail)
    draw.text((24, 78), "Final GDS availability is not physical closure; precheck and routed tests were skipped.", fill="#5b6e75", font=detail)
    draw.text((24, canvas.height - 27), "Actual identified artifact preview; scope and complete hashes are in identity.json.", fill="#5b6e75", font=detail)
    canvas.save(target, optimize=True)
    return {"source_dimensions_px": list(original), "selected_layout_dimensions_px": list(image.size),
            "selected_canvas_dimensions_px": list(canvas.size),
            "transformation": "Uniform downscale to at most 1600 pixels using Lanczos (never upscale); add status banner and footer"}


def wrapper_svg(source, target, identity, run_id):
    namespace = "http://www.w3.org/2000/svg"
    ET.register_namespace("", namespace)
    root = ET.parse(source).getroot()
    viewbox = [float(value) for value in root.attrib["viewBox"].split()]
    x, y, width, height = viewbox
    require(x == 0 and y == 0, "Expected a zero-origin Matplotlib SVG viewBox")
    header = 86
    children = list(root)
    group = ET.Element("{" + namespace + "}g", {"transform": f"translate(0,{header})"})
    for child in children:
        if child.tag.rsplit("}", 1)[-1] not in ("metadata", "defs"):
            root.remove(child)
            group.append(child)
    root.append(group)
    root.set("viewBox", f"0 0 {width} {height + header}")
    root.set("height", f"{height + header}pt")
    background = ET.Element("{" + namespace + "}rect", {"x": "0", "y": "0", "width": str(width), "height": str(header), "fill": "white"})
    root.insert(0, background)
    for position, text, size, color in (
        (29, "UNQUALIFIED · MOTIF attempt 2 floorplan", 18, "#a44737"),
        (51, f"Run {run_id} · source {identity['source_sha'][:12]} · official GDS job failure", 11, "#374e56"),
        (70, "Final layout presence is not closure; precheck and routed tests were skipped.", 10, "#5b6e75"),
    ):
        element = ET.SubElement(root, "{" + namespace + "}text", {"x": "18", "y": str(position), "font-family": "DejaVu Sans", "font-size": str(size), "fill": color})
        element.text = text
    ET.ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)
    target.write_bytes(target.read_bytes().replace(b"\r\n", b"\n"))
    return {"transformation": "Retain original vector geometry unchanged inside translated group; add 86-point UNQUALIFIED status header"}


def select(view_report_path, metrics_path, output, source_sha, run_id, manifest_path=FROZEN_MANIFEST):
    require(not output.exists() or not any(output.iterdir()), "Selection output must be fresh and empty")
    report = json.loads(view_report_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    identity = report["identity"]
    require(identity.get("exact_rtl_correspondence") is True, "Physical views have no verified RTL correspondence")
    require(identity.get("source_sha") == source_sha == metrics.get("source_sha"), "View/metric source identities differ")
    preregistration, manifest_hash = verified_preregistration(manifest_path, identity.get("frozen_manifest_sha256_lf"))
    correspondence = metrics.get("source_correspondence", {})
    require(correspondence.get("source_sha") == source_sha
            and correspondence.get("frozen_manifest_sha256_lf") == manifest_hash
            and correspondence.get("preregistration") == preregistration,
            "Physical metric source correspondence differs from the frozen view/preregistration identity")
    require(metrics.get("workflow_run_id") == run_id, "Metric run identity differs")
    require(identity["artifact"]["workflow_run_url"].endswith("/" + str(run_id)), "View run identity differs")
    matching = [item for item in metrics["artifacts"] if item["id"] == identity["artifact"]["id"]]
    require(len(matching) == 1 and matching[0]["archive_sha256_raw"] == identity["artifact"]["archive_sha256_raw"], "View/metric archive identities differ")
    jobs = {job["name"]: job.get("conclusion") for job in metrics.get("jobs", [])}
    require(jobs.get("gds") == "failure" and jobs.get("precheck") == "skipped" and jobs.get("gl_test") == "skipped", "This attempt-2 presentation requires the recorded failed/skipped job statuses")
    output.mkdir(parents=True, exist_ok=True)
    selected = {"schema_version": 1, "kind": "selected_identified_unqualified_physical_previews", "classification": "presentation_only",
                "presentation_status": "UNQUALIFIED", "attempt": 2, "workflow_run_id": run_id, "identity": identity,
                "frozen_manifest_sha256_lf": manifest_hash, "preregistration": preregistration,
                "preregistration_binding": "Read from the immutable freeze manifest after its LF hash matched both the identified view and physical metric source correspondence",
                "recorded_job_conclusions": jobs, "view_report_sha256_raw": digest(view_report_path),
                "metrics_receipt_sha256_raw": digest(metrics_path), "selector_sha256_raw": digest(Path(__file__)),
                "views": {}, "output_files_sha256_raw": {},
                "limitations": ["The official GDS job failed; final GDS availability does not establish physical closure.",
                                "Official precheck and routed functional tests were skipped.",
                                "Dense views select raster previews; full generated vector views and actual geometry remain in build/."]}
    directory = view_report_path.parent
    for kind in ("floorplan", "placement", "routing", "gds"):
        view = report["views"][kind]
        require(view["status"] == "available", "Identified view is unavailable: " + kind)
        pngs = [name for name in view["outputs"] if name.endswith(".png")]
        require(len(pngs) == 1, "Expected one actual rendered PNG for " + kind)
        source = directory / pngs[0]
        require(digest(source) == report["output_files_sha256_raw"][source.name], "Rendered input PNG differs from identified report")
        target = output / f"{kind}.png"
        transform = wrapper_png(source, target, kind, identity, run_id)
        inputs = {name: report["used_files"][name] for name in (view.get("geometry"), view.get("image")) if name}
        selected["views"][kind] = {**view, "selected_outputs": [target.name], "input_files": inputs,
                                   "source_rendered_png_sha256_raw": digest(source), "preview_transform": transform}
        selected["output_files_sha256_raw"][target.name] = digest(target)
        if kind == "floorplan":
            svg = directory / "floorplan.svg"
            require(digest(svg) == report["output_files_sha256_raw"][svg.name], "Rendered input floorplan SVG differs from report")
            selected_svg = output / "floorplan.svg"
            selected["views"][kind]["vector_transform"] = wrapper_svg(svg, selected_svg, identity, run_id)
            selected["views"][kind]["source_rendered_svg_sha256_raw"] = digest(svg)
            selected["views"][kind]["selected_outputs"].append(selected_svg.name)
            selected["output_files_sha256_raw"][selected_svg.name] = digest(selected_svg)
    (output / "identity.json").write_text(json.dumps(selected, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view-report", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--manifest", type=Path, default=FROZEN_MANIFEST)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.source_sha), "Exact source SHA is required")
    select(args.view_report, args.metrics, args.output_dir, args.source_sha, args.run_id, args.manifest)
    print("PASS identified physical previews selected and visibly labeled UNQUALIFIED; no closure decision")


if __name__ == "__main__":
    main()
