"""Audit the single declaration-order repair without weakening gate-retest checks.

This report is separate evidence. The CI artifact-retest job still demands its
original strict git diff check; this module does not authorize a retest bypass.
"""
import argparse
import json
import subprocess
from pathlib import Path

from tools.frozen_manifest import compare, git_inventory, inventory

DECLARATION = "    wire tx_overflow, tx_underflow, rx_full, rx_empty, rx_overflow, rx_underflow;\n"


def declaration_correspondence(old, new):
    old, new = old.replace("\r\n", "\n"), new.replace("\r\n", "\n")
    if old.count(DECLARATION) != 1 or new.count(DECLARATION) != 1:
        raise ValueError("Repair declaration missing or duplicated")
    if old.replace(DECLARATION, "") != new.replace(DECLARATION, ""):
        raise ValueError("Change exceeds declaration relocation")


def report(source_sha):
    original, current = git_inventory(source_sha), inventory()
    original_core = original.pop("src/motif_core.sv")
    current_core = current.pop("src/motif_core.sv")
    compare(original, current)
    old = subprocess.check_output(["git", "show", f"{source_sha}:src/motif_core.sv"]).decode()
    new = Path("src/motif_core.sv").read_text()
    declaration_correspondence(old, new)
    return {"schema_version": 1, "physical_source_sha": source_sha,
            "current_source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "raw_source_equality": original_core == current_core, "all_other_boundary_sources_equal": True,
            "permitted_difference": "One existing uninitialized wire declaration moved before its first use",
            "declaration_insensitive_source_equality": True, "original_core_sha256": original_core, "current_core_sha256": current_core,
            "limitations": "Circuit correspondence for this specific declaration-only repair. Not raw source identity and not permission to bypass the CI gate-retest source-equality requirement."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", default="build/generalization/gate1/physical_correspondence.json", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report(args.source_sha), indent=2) + "\n", encoding="utf-8")
    print("PASS declaration-only circuit correspondence; raw SHA remains separate")
