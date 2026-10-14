"""Render actual identified v3 physical metrics without changing nominal cost figures.

The receipt, source commit and raw receipt hash must be supplied explicitly.
Missing values are unavailable; signed timing metrics use a visible zero reference.
Physical stage values are never compared with the nominal mapped-area cap.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import textwrap

from render_cost import COLORS, sha256, require, finite, plotting, save

FROZEN_MANIFEST = Path(__file__).resolve().parents[2] / "experiments/temporal_qualification/frozen_v3_manifest.json"
FROZEN_MANIFEST_SHA256_LF = "71d5b07b5524fb6fa702357291eb35f52eccc5861111f7824b6fb9ead98a3047"


def verified_preregistration(manifest_path, source_manifest_hash):
    """Bind presentation evidence to the actual immutable source boundary."""
    raw = manifest_path.read_bytes()
    actual = sha256(raw.replace(b"\r\n", b"\n"))
    require(actual == source_manifest_hash == FROZEN_MANIFEST_SHA256_LF,
            "Frozen manifest LF hash differs from the identified physical source boundary")
    manifest = json.loads(raw)
    require(manifest.get("architecture_version") == 3, "Expected the frozen v3 manifest")
    preregistration = manifest.get("preregistration", {})
    require(re.fullmatch(r"[0-9a-f]{40}", preregistration.get("commit", ""))
            and re.fullmatch(r"[0-9a-f]{64}", preregistration.get("sha256_lf", "")),
            "Frozen preregistration identity is absent or invalid")
    return dict(preregistration), actual


def panel(ax, record, versions):
    from matplotlib.ticker import MaxNLocator, StrMethodFormatter
    present = [record["values"][name] for name in versions if record["values"][name] is not None]
    maximum = max(present, default=1) or 1
    ax.set_ylim(0, maximum * 1.30)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#e3eaeb", linewidth=.7)
    for index, name in enumerate(versions):
        value = record["values"][name]
        if value is None:
            ax.text(index, maximum * .48, "Unavailable", color="#89959c", ha="center", fontsize=9)
        else:
            ax.bar(index, value, width=.55, color=COLORS.get(name, "#287c63"), zorder=3)
            label = f"{value:,.2f}" if record["units"] in ("µm²", "µm", "%") else f"{value:,.0f}"
            ax.text(index, value + maximum * .055, label, ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(range(len(versions)), ["Legacy" if name == "legacy" else name.upper() for name in versions])
    ax.set_xlim(-.65, len(versions) - .35)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.set_ylabel(record["units"])
    ax.set_title(record["label"], loc="left", fontsize=11, fontweight="bold", pad=15)
    ax.text(0, -0.27, textwrap.fill(record["scope"], width=48), transform=ax.transAxes,
            fontsize=8, color="#5d7278", va="top")


def physical_inventory(path, expected_hash, expected_source, manifest_path=FROZEN_MANIFEST):
    raw = path.read_bytes()
    require(expected_hash is not None and re.fullmatch(r"[0-9a-f]{64}", expected_hash), "An expected physical receipt SHA-256 is required")
    require(sha256(raw) == expected_hash, "Physical receipt raw SHA-256 differs from its supplied identity")
    data = json.loads(raw)
    require(data.get("kind") == "motif_v3_identified_physical_measurements", "Not an identified v3 physical metric receipt")
    require(expected_source is not None and re.fullmatch(r"[0-9a-f]{40}", expected_source)
            and data.get("source_sha") == expected_source, "Physical receipt differs from its supplied source SHA")
    correspondence = data.get("source_correspondence", {})
    require(correspondence.get("source_sha") == expected_source,
            "Physical metric receipt lacks matching source correspondence")
    preregistration, manifest_hash = verified_preregistration(manifest_path, correspondence.get("frozen_manifest_sha256_lf"))
    require(correspondence.get("preregistration") == preregistration,
            "Physical source correspondence preregistration differs from the frozen manifest")
    require(isinstance(data.get("workflow_run_id"), int) and data["workflow_run_id"] > 0, "Physical run identity is missing")
    require(bool(data.get("artifacts")), "Physical artifact identities are missing")
    for artifact in data["artifacts"]:
        require(artifact.get("id") and artifact.get("name") and re.fullmatch(r"[0-9a-f]{64}", artifact.get("archive_sha256_raw", "")), "Physical artifact lacks ID/name/raw archive hash")
    scope = data.get("extraction_scope", {})
    require(scope.get("metrics_status") in ("final_metrics_available", "partial_unfinished_stage_metrics", "no_metrics_available"), "Physical extraction scope is unidentified")
    definitions = [("stdcell_area_um2", "Physical standard-cell area", "µm²"),
                   ("core_area_um2", "Core area", "µm²"),
                   ("stdcell_count", "Physical standard cells", "cells"),
                   ("register_count", "Physical sequential cells", "cells"),
                   ("stdcell_utilization", "Standard-cell utilization", "%"),
                   ("detailed_wirelength_um", "Detailed routed wirelength", "µm"),
                   ("global_wirelength_um", "Global-route wirelength", "µm"),
                   ("vias", "Detailed-route vias", "vias"),
                   ("global_route_overflow", "Global-route overflow", "overflow count"),
                   ("hold_buffer_count", "Hold-repair buffers", "cells"),
                   ("timing_repair_buffer_area_um2", "Timing-repair buffer area", "µm²"),
                   ("klayout_drc", "KLayout DRC", "violations")]
    records = []
    for key, label, units in definitions:
        value = data.get("global_route", {}).get("total_overflow") if key == "global_route_overflow" else data.get("measurements", {}).get(key)
        reason = data.get("unavailable_reasons", {}).get("measurements." + key, "Metric is absent from the identified extraction")
        if value is not None:
            value = finite(value, key)
            if key == "stdcell_utilization":
                require(value <= 1, "Utilization receipt is not a dimensionless fraction")
                value *= 100  # The receipt's utilization is a dimensionless fraction.
        origin = data.get("metric_sources", {}).get("global_route.total_overflow" if key == "global_route_overflow" else "measurements." + key)
        stage_scope = data.get("global_route", {}).get("source_log") if key == "global_route_overflow" else scope.get("metrics_source")
        records.append({"key": key, "label": label, "units": units, "scope": "Actual source: " + str(stage_scope),
                        "values": {"v3": value}, "unavailable_reason": reason if value is None else None,
                        "axis_minimum": 0, "provenance": origin,
                        "conversion": "receipt fraction × 100" if key == "stdcell_utilization" else None})
    return {"schema_version": 1, "kind": "presentation_of_identified_v3_physical_cost_receipt",
            "classification": "presentation_only", "receipt_path": path.as_posix(), "receipt_sha256_raw": expected_hash,
            "source_sha": data["source_sha"], "workflow_run_id": data["workflow_run_id"],
            "frozen_manifest_sha256_lf": manifest_hash, "preregistration": preregistration,
            "preregistration_binding": "Read from the immutable freeze manifest after its LF hash matched the identified physical source correspondence",
            "artifacts": data["artifacts"], "extraction_scope": scope, "metrics": records,
            "corners": data.get("corners", {}), "timing_metric_sources": {key: value for key, value in data.get("metric_sources", {}).items() if key.startswith("corners.")},
            "presentation_status": "UNQUALIFIED", "workflow_status": data.get("workflow_status"), "workflow_conclusion": data.get("workflow_conclusion"),
            "receipt_metadata_sha256_raw": data.get("metadata_raw_hashes", {}),
            "measurement_values_original": data.get("measurements", {}),
            "input_files": data.get("input_files", []),
            "unavailable_reasons": data.get("unavailable_reasons", {}),
            "renderer_sha256_raw": sha256(Path(__file__).read_bytes()),
            "limitations": ["Physical extraction is a separate scope from nominal mapping; no comparison with the nominal 10% mapped-area cap.",
                            "Intermediate metrics remain intermediate; extraction alone makes no physical qualification decision.",
                            "Absent metrics are unavailable, never substituted with zero."]}


def render_physical(report, output):
    plt = plotting()
    figure, axes = plt.subplots(4, 3, figsize=(14.4, 15.5))
    for axis, record in zip(axes.flat, report["metrics"]):
        panel(axis, record, ("v3",))
    figure.subplots_adjust(left=.07, right=.975, top=.86, bottom=.095, hspace=.80, wspace=.34)
    figure.text(.065, .965, "MOTIF v3: actual physical metrics — UNQUALIFIED", fontsize=20, fontweight="bold", color="#a44737")
    scope = report["extraction_scope"]
    figure.text(.065, .931, f"Run {report['workflow_run_id']} · source {report['source_sha'][:12]} · {scope['metrics_status']}", fontsize=11)
    figure.text(.065, .906, "Official workflow conclusion: " + str(report.get("workflow_conclusion")) + "; final artifact availability does not establish physical closure.", fontsize=10, color="#a44737")
    figure.text(.065, .035, "Physical flow metrics have their own stage scope; no comparison with the nominal mapped-area cap. Missing metrics are unavailable.", fontsize=9, color="#5d7278")
    figure.text(.065, .016, "Utilization converts the receipt fraction to percent. Full values, sources and identities: physical_cost.json.", fontsize=9, color="#5d7278")
    save(figure, output, "physical_cost", report)
    plt.close(figure)
    render_physical_timing(report, output)


def render_physical_timing(report, output):
    """Signed corner slacks retain a visible zero reference and all actual values."""
    plt = plotting()
    corners = report["corners"]
    order = [name for name in ("nom_fast_1p32V_m40C", "nom_typ_1p20V_25C", "nom_slow_1p08V_125C") if name in corners]
    order += sorted(set(corners) - set(order))
    labels = {"nom_fast_1p32V_m40C": "Fast\n1.32 V · −40 °C", "nom_typ_1p20V_25C": "Typical\n1.20 V · 25 °C", "nom_slow_1p08V_125C": "Slow\n1.08 V · 125 °C"}
    definitions = [("setup_wns_ns", "Setup worst negative slack"), ("setup_tns_ns", "Setup total negative slack"),
                   ("hold_wns_ns", "Hold worst negative slack"), ("hold_tns_ns", "Hold total negative slack")]
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 9.5))
    records = []
    for axis, (key, title) in zip(axes.flat, definitions):
        values = [corners[name].get(key) for name in order]
        for value in values:
            require(value is None or isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), "Nonfinite corner timing metric")
        low = min([0] + [value for value in values if value is not None])
        high = max([0] + [value for value in values if value is not None])
        span = max(abs(low), abs(high), 1)
        axis.set_ylim(low - span * .23, high + span * .23)
        axis.set_axisbelow(True)
        axis.grid(axis="y", color="#e3eaeb", linewidth=.7)
        axis.axhline(0, color="#657e85", linewidth=1)
        for index, value in enumerate(values):
            if value is None:
                axis.text(index, span * .05, "Unavailable", ha="center", color="#89959c", fontsize=9)
            else:
                axis.bar(index, value, width=.5, color="#b45948" if value < 0 else "#287c63", zorder=3)
                offset = -span * .035 if value < 0 else span * .035
                axis.text(index, value + offset, f"{value:,.3f}", ha="center", va="top" if value < 0 else "bottom", fontweight="bold")
        axis.set_xticks(range(len(order)), [labels.get(name, name) for name in order])
        axis.set_xlim(-.65, max(len(order) - .35, .65))
        axis.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=13)
        axis.set_ylabel("ns")
        records.append({"key": key, "label": title, "units": "ns", "values": {name: corners[name].get(key) for name in order}, "zero_reference": True})
    figure.subplots_adjust(left=.075, right=.97, top=.81, bottom=.15, hspace=.46, wspace=.25)
    figure.text(.07, .945, "MOTIF attempt 2: corner timing — UNQUALIFIED", fontsize=20, fontweight="bold", color="#a44737")
    figure.text(.07, .899, f"Run {report['workflow_run_id']} · source {report['source_sha'][:12]} · {report['extraction_scope']['metrics_status']}", fontsize=11)
    figure.text(.07, .855, "Setup and hold WNS/TNS from identified final metrics; negative values show violations relative to zero.", fontsize=10)
    figure.text(.07, .06, "WNS/TNS are shown as recorded; missing metrics remain unavailable. Full precision and corner identities are in JSON.", fontsize=9, color="#5d7278")
    timing = {key: value for key, value in report.items() if key not in ("metrics", "output_files_sha256_raw", "physical_receipt")}
    timing["metrics"] = records
    save(figure, output, "physical_timing", timing)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--physical-receipt', required=True, type=Path)
    parser.add_argument('--physical-receipt-sha256', required=True)
    parser.add_argument('--physical-source-sha', required=True)
    parser.add_argument('--manifest', type=Path, default=FROZEN_MANIFEST)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    require(not args.output_dir.exists() or not any(args.output_dir.iterdir()), 'Output directory must be fresh and empty')
    report = physical_inventory(args.physical_receipt, args.physical_receipt_sha256, args.physical_source_sha, args.manifest)
    report['shared_plotting_helper_sha256_raw'] = sha256(Path(__file__).with_name('render_cost.py').read_bytes())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    render_physical(report, args.output_dir)
    print('PASS identified physical metric receipt; figures labeled UNQUALIFIED; no qualification decision or synthesis run')
    print(args.output_dir.resolve())


if __name__ == '__main__':
    main()
