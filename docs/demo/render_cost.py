"""Render committed cost receipts without synthesis or semantic changes.

python docs/demo/render_cost.py --output-dir build/demo/cost_review

Every run uses a fresh output directory.  The selected SVG/PNG and editable
metric JSON can then be copied to docs/demo/figures/cost/.  An optional physical
receipt must be an identified v3 measurement-extractor receipt, supplied with
its expected raw SHA-256 and exact source SHA.  Physical values get a separate
chart and are never compared with the nominal mapped-area budget.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import textwrap
import uuid

ROOT = Path(__file__).resolve().parents[2]
SYNTHESIS = "experiments/temporal_qualification/synthesis.json"
V3_ACCOUNTING = "experiments/temporal_qualification/accounting.json"
V2_ACCOUNTING = "experiments/exchange_decomposition/final_accounting.json"
V2_MANIFEST = "experiments/exchange_decomposition/frozen_v2_manifest.json"
COLORS = {"legacy": "#89959c", "v2": "#507d9b", "v3": "#287c63"}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def committed_json(commit, path):
    raw = git("show", f"{commit}:{path}")
    return json.loads(raw), {
        "path": path,
        "receipt_checkout_commit": commit,
        "receipt_git_blob_sha256_raw": sha256(raw),
        "receipt_sha256_lf": sha256(raw.replace(b"\r\n", b"\n")),
    }


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value, label):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0, f"Invalid nonnegative metric: {label}")
    return value


def metric(label, units, scope, values, provenance):
    return {"label": label, "units": units, "scope": scope, "values": values,
            "provenance": provenance, "axis_minimum": 0,
            "unavailable": {"legacy": "No comparable pinned mapped/accounting receipt in this matched comparison"}}


def nominal_inventory(commit):
    synthesis, synth_id = committed_json(commit, SYNTHESIS)
    v3_account, v3_id = committed_json(commit, V3_ACCOUNTING)
    v2_account, v2_id = committed_json(commit, V2_ACCOUNTING)
    v2_manifest, manifest_id = committed_json(commit, V2_MANIFEST)
    require(synthesis.get("passed") is True and v3_account.get("passed") is True,
            "Committed matched synthesis/accounting gate is not recorded as passed")
    mapped = {name: synthesis["mapped_" + name] for name in ("v2", "v3")}
    for name, report in mapped.items():
        require(report.get("kind") == "technology_mapped_cell_area", "A matched technology-area receipt is required")
        require(report.get("area_units") == "square micrometres", "Unknown mapped-area units")
        require(report["sequential_cell_count"] + report["combinational_cell_count"] == report["design"]["num_cells"],
                f"Mapped {name} cell classes do not sum to its total")
        for key in ("source_sha", "library_sha256", "rtl_source_hashes", "tools", "synthesis_command_sha256"):
            require(bool(report.get(key)), f"Mapped {name} is missing pinned identity {key}")
    for key in ("top", "library", "library_sha256", "yosys", "tools"):
        require(mapped["v2"][key] == mapped["v3"][key], f"Canonical remap identities differ: {key}")
    require(mapped["v2"]["rtl_source_hashes"] == v2_manifest["rtl_hashes"],
            "Matched v2 RTL identities differ from its frozen accounting inventory")
    require(v2_account["declared_state_widths"] == v2_manifest["state_widths_declared"],
            "V2 declared-state accounting differs from its identified frozen inventory")
    for name, account in (("v2", v2_account), ("v3", v3_account)):
        require(sum(account["declared_state_widths"].values()) == account["declared_total_register_bits"],
                f"Declared {name} storage groups do not sum to their total")
        require(account["configuration_bits"] == mapped[name]["allocated_configuration_bits"],
                f"Declared {name} configuration allocation differs from the matched receipt")
    require(all(v3_account[key] == value for key, value in synthesis["accounting"].items()),
            "Standalone v3 accounting differs from the matched synthesis receipt")
    require(v3_account["declared_total_register_bits"] - v2_account["declared_total_register_bits"]
            == v3_account["delta_declared_register_bits_vs_v2"], "Declared register delta is inconsistent")
    area_ratio = mapped["v3"]["design"]["area"] / mapped["v2"]["design"]["area"]
    require(math.isclose(area_ratio, synthesis["area_ratio_vs_matched_v2"], rel_tol=1e-12),
            "Matched area ratio does not agree with the receipt")
    accounts = {"v2": v2_account, "v3": v3_account}
    def values(getter):
        return {"legacy": None, **{name: finite(getter(name), name) for name in ("v2", "v3")}}
    metrics = [
        metric("Mapped standard-cell area", "µm²", "CMOS5L typical library; full matched top; before place/route",
               values(lambda name: mapped[name]["design"]["area"]), {"receipt": SYNTHESIS, "field": "mapped_{version}.design.area"}),
        metric("Mapped sequential cells", "cells", "Mapped sequential cell instances; not declared register bits",
               values(lambda name: mapped[name]["sequential_cell_count"]), {"receipt": SYNTHESIS, "field": "mapped_{version}.sequential_cell_count"}),
        metric("Mapped combinational cells", "cells", "Mapped combinational cell instances; full matched top",
               values(lambda name: mapped[name]["combinational_cell_count"]), {"receipt": SYNTHESIS, "field": "mapped_{version}.combinational_cell_count"}),
        metric("Total declared registers", "bits", "Architectural/support/diagnostic state, including configuration once",
               values(lambda name: accounts[name]["declared_total_register_bits"]), {"v2_receipt": V2_ACCOUNTING, "v3_receipt": V3_ACCOUNTING, "field": "declared_total_register_bits"}),
        metric("Allocated configuration", "bits", "Global configuration allocation; includes the transaction table",
               values(lambda name: accounts[name]["configuration_bits"]), {"v2_receipt": V2_ACCOUNTING, "v3_receipt": V3_ACCOUNTING, "field": "configuration_bits"}),
        metric("Transaction table", "bits", "16 entries × 64 bits; subset of allocated configuration",
               values(lambda name: v2_account["program_bits"] if name == "v2" else v3_account["table_bits"]),
               {"v2_receipt": V2_ACCOUNTING, "v2_field": "program_bits", "v3_receipt": V3_ACCOUNTING, "v3_field": "table_bits"}),
    ]
    identity_keys = ("source_sha", "rtl_source_hashes", "tools", "yosys", "top", "library", "library_sha256", "netlist_sha256", "synthesis_command_sha256")
    return {
        "schema_version": 1, "kind": "presentation_of_committed_matched_cost_receipts",
        "classification": "presentation_only", "receipt_checkout_commit": commit,
        "renderer_sha256_raw": sha256(Path(__file__).read_bytes()),
        "receipts": [synth_id, v2_id, v3_id, manifest_id],
        "measured_source_identities": {name: {key: report[key] for key in identity_keys} for name, report in mapped.items()},
        "accounting_identities": {"v2": {"frozen_inventory_source_sha": v2_manifest["source_sha"], "rtl_hashes": v2_manifest["rtl_hashes"]},
                                  "v3": {"receipt_source_sha": v3_account["source_sha"], "receipt_source_sha_role": v3_account["source_sha_role"],
                                         "source_hashes": v3_account["source_hashes"]}},
        "matched_area_change_percent": (area_ratio - 1) * 100,
        "nominal_mapped_budget": synthesis["budgets"], "metrics": metrics,
        "limitations": ["Nominal technology mapping does not establish physical closure or protocol qualification.",
                        "Legacy has no comparable pinned receipt in this matched cost series and is unavailable, never zero.",
                        "Table bits are included in configuration, which is included once in total declared registers; these panels are not additive.",
                        "The receipt checkout commit is distinct from each actual measured source commit."],
    }


def plotting():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none",
                         "svg.hashsalt": "motif-committed-cost", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.edgecolor": "#bbc7ca",
                         "text.color": "#233d43", "axes.labelcolor": "#425960",
                         "xtick.color": "#425960", "ytick.color": "#425960"})
    return plt


def save(figure, directory, name, report):
    outputs = {}
    for extension in ("svg", "png"):
        path = directory / f"{name}.{extension}"
        figure.savefig(path, dpi=160, facecolor="white", metadata={"Creator": "MOTIF committed-receipt cost renderer", "Date": None} if extension == "svg" else None)
        if extension == "svg":
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        outputs[path.name] = sha256(path.read_bytes())
    report["output_files_sha256_raw"] = outputs
    (directory / f"{name}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


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
            ax.text(index, maximum * .48, "Unavailable", color=COLORS.get(name, "#89959c"), ha="center", fontsize=9)
        else:
            ax.bar(index, value, width=.55, color=COLORS.get(name, "#287c63"), zorder=3)
            label = f"{value:,.2f}" if record["units"] in ("µm²", "µm") else f"{value:,.0f}"
            ax.text(index, value + maximum * .055, label, ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(range(len(versions)), ["Legacy" if name == "legacy" else name.upper() for name in versions])
    ax.set_xlim(-.65, len(versions) - .35)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.set_ylabel(record["units"])
    ax.set_title(record["label"], loc="left", fontsize=11, fontweight="bold", pad=15)
    ax.text(0, -0.27, textwrap.fill(record["scope"], width=48), transform=ax.transAxes,
            fontsize=8, color="#5d7278", va="top")


def render_nominal(report, output):
    plt = plotting()
    figure, axes = plt.subplots(2, 3, figsize=(14.4, 9.5))
    for axis, record in zip(axes.flat, report["metrics"]):
        panel(axis, record, ("legacy", "v2", "v3"))
    figure.subplots_adjust(left=.07, right=.975, top=.81, bottom=.18, hspace=.80, wspace=.34)
    figure.text(.065, .945, "MOTIF: measured cost of the temporal extension", fontsize=20, fontweight="bold")
    figure.text(.065, .900, "Canonical matched v2/v3 remap · same pinned Yosys/ABC, top and CMOS5L typical library", fontsize=11)
    storage = report["metrics"][3]["values"]
    config = report["metrics"][4]["values"]
    table = report["metrics"][5]["values"]
    allocation = "configuration/table allocation unchanged" if config["v2"] == config["v3"] and table["v2"] == table["v3"] else "configuration/table changes shown below"
    figure.text(.065, .860, f"Mapped area {report['matched_area_change_percent']:+.2f}% · declared storage {storage['v3'] - storage['v2']:+,} bits · {allocation}", fontsize=11, color="#287c63")
    sources = report["measured_source_identities"]
    figure.text(.065, .070, f"Measured source: v2 {sources['v2']['source_sha'][:12]} · v3 {sources['v3']['source_sha'][:12]} | Receipt checkout {report['receipt_checkout_commit'][:12]}", fontsize=8, color="#5d7278")
    figure.text(.065, .045, "Mapped cost only: no placement/routing/CTS or timing-closure claim. Legacy: no comparable pinned receipt.", fontsize=8, color="#5d7278")
    figure.text(.065, .020, "Storage panels are not additive: table ⊂ configuration ⊂ total declared registers. Full identities and editable values: cost_summary.json.", fontsize=8, color="#5d7278")
    save(figure, output, "cost_summary", report)
    plt.close(figure)


def physical_inventory(path, expected_hash, expected_source):
    raw = path.read_bytes()
    require(expected_hash is not None and re.fullmatch(r"[0-9a-f]{64}", expected_hash), "An expected physical receipt SHA-256 is required")
    require(sha256(raw) == expected_hash, "Physical receipt raw SHA-256 differs from its supplied identity")
    data = json.loads(raw)
    require(data.get("kind") == "motif_v3_identified_physical_measurements", "Not an identified v3 physical metric receipt")
    require(expected_source is not None and re.fullmatch(r"[0-9a-f]{40}", expected_source)
            and data.get("source_sha") == expected_source, "Physical receipt differs from its supplied source SHA")
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
                   ("detailed_wirelength_um", "Detailed routed wirelength", "µm"),
                   ("hold_buffer_count", "Hold-repair buffers", "cells")]
    records = []
    for key, label, units in definitions:
        value = data.get("measurements", {}).get(key)
        reason = data.get("unavailable_reasons", {}).get("measurements." + key, "Metric is absent from the identified extraction")
        if value is not None:
            value = finite(value, key)
        records.append({"label": label, "units": units, "scope": "Identified v3 flow extraction; " + scope["metrics_status"],
                        "values": {"v3": value}, "unavailable_reason": reason if value is None else None,
                        "axis_minimum": 0, "provenance": data.get("metric_sources", {}).get("measurements." + key)})
    return {"schema_version": 1, "kind": "presentation_of_identified_v3_physical_cost_receipt",
            "classification": "presentation_only", "receipt_path": path.as_posix(), "receipt_sha256_raw": expected_hash,
            "source_sha": data["source_sha"], "workflow_run_id": data["workflow_run_id"],
            "artifacts": data["artifacts"], "extraction_scope": scope, "metrics": records,
            "physical_receipt": data, "renderer_sha256_raw": sha256(Path(__file__).read_bytes()),
            "limitations": ["Physical extraction is a separate scope from nominal mapping; no comparison with the nominal 10% mapped-area cap.",
                            "Intermediate metrics remain intermediate; extraction alone makes no physical qualification decision.",
                            "Absent metrics are unavailable, never substituted with zero."]}


def render_physical(report, output):
    plt = plotting()
    figure, axes = plt.subplots(2, 3, figsize=(14.4, 9.5))
    for axis, record in zip(axes.flat, report["metrics"]):
        panel(axis, record, ("v3",))
    figure.subplots_adjust(left=.07, right=.975, top=.80, bottom=.18, hspace=.80, wspace=.34)
    figure.text(.065, .945, "MOTIF v3: identified physical cost observations", fontsize=20, fontweight="bold")
    scope = report["extraction_scope"]
    figure.text(.065, .90, f"Run {report['workflow_run_id']} · source {report['source_sha'][:12]} · {scope['metrics_status']}", fontsize=11)
    figure.text(.065, .86, "Actual extraction: " + str(scope.get("metrics_source")), fontsize=10, color="#5d7278")
    figure.text(.065, .065, "Physical observations have their own flow-stage scope. They are not compared with the nominal mapped-area budget.", fontsize=9, color="#5d7278")
    figure.text(.065, .035, "An identified extraction does not establish physical closure. Unavailable metrics are not zero. Full receipt: physical_cost.json.", fontsize=9, color="#5d7278")
    save(figure, output, "physical_cost", report)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt-commit", default="HEAD")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--physical-receipt", type=Path)
    parser.add_argument("--physical-receipt-sha256")
    parser.add_argument("--physical-source-sha")
    args = parser.parse_args()
    commit = git("rev-parse", "--verify", args.receipt_commit + "^{commit}").decode().strip()
    output = args.output_dir or ROOT / "build/demo" / ("cost_" + commit[:12] + "_" + uuid.uuid4().hex[:8])
    require(not output.exists() or not any(output.iterdir()), "Output directory must be fresh and empty")
    nominal = nominal_inventory(commit)
    physical = physical_inventory(args.physical_receipt, args.physical_receipt_sha256, args.physical_source_sha) if args.physical_receipt else None
    require(args.physical_receipt or not (args.physical_receipt_sha256 or args.physical_source_sha), "Physical identity arguments require a physical receipt")
    output.mkdir(parents=True, exist_ok=True)
    render_nominal(nominal, output)
    if physical:
        render_physical(physical, output)
    print("PASS committed matched receipt identities and metric consistency; no synthesis or qualification run")
    print(output.resolve())


if __name__ == "__main__":
    main()
