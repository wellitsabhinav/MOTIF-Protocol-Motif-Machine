"""Immutable logical v3 boundary and separately identified physical inputs."""
import argparse
import hashlib
import json
import subprocess
import re
from pathlib import Path

DIRECTORY = Path("experiments/temporal_qualification")
PREREGISTRATION = Path("docs/research/v3_temporal_qualification/preregistration.json")
MANIFEST = DIRECTORY / "frozen_v3_manifest.json"
PHYSICAL_FILES = ("src/config.json", "info.yaml", "flow-lock.json", ".github/workflows/gds.yml")
REQUIRED_REPORTS = ("model", "temporal", "repair", "regression", "cocotb", "synthesis", "accounting")


def sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def semantic_inventory():
    files = list(Path("src").rglob("*.sv")) + list(Path("motif").rglob("*.py"))
    files += list(Path("tools").glob("*.py")) + list(Path("tests").rglob("*.py"))
    files += list(Path("test").glob("*.sv")) + list(Path("test").glob("*.v")) + list(Path("test").glob("*.py"))
    files += list(Path("formal").glob("*.sv"))
    files += [Path(name) for name in ("pyproject.toml", "test/requirements.txt", "test/Makefile", ".github/workflows/ci.yml")]
    files += [PREREGISTRATION]
    files += list((DIRECTORY / "configurations").glob("*.json"))
    return {path.as_posix(): sha(path.read_bytes()) for path in sorted(set(files)) if path.is_file()}


def physical_inventory():
    return {name: sha(Path(name).read_bytes()) for name in PHYSICAL_FILES}


def preregistration_identity():
    commits = subprocess.check_output(["git", "log", "--reverse", "--format=%H", "--", PREREGISTRATION.as_posix()], text=True).splitlines()
    if not commits:
        raise ValueError("Preregistration must be committed before campaign execution")
    commit = commits[0]
    original = subprocess.check_output(["git", "show", f"{commit}:{PREREGISTRATION.as_posix()}"])
    if sha(original) != sha(PREREGISTRATION.read_bytes()):
        raise ValueError("Immutable v3 preregistration changed after its first commit")
    return {"commit": commit, "sha256_lf": sha(original)}


def report_identity():
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    return {"source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "source_sha_role": "Parent commit of measured working-tree sources; source_hashes identify the tested bytes" if dirty else "Committed source revision; source_hashes identify the tested bytes",
            "working_tree_dirty": dirty,
            "source_hashes": semantic_inventory(), "preregistration": preregistration_identity(),
            "physical_input_hashes": physical_inventory()}


def declared_accounting():
    from tools.synthesis import configuration_widths
    previous = json.loads(Path("experiments/exchange_decomposition/frozen_v2_manifest.json").read_text())
    groups = dict(previous["state_widths_declared"])
    additions = {}
    for path in sorted(Path("src").glob("*.sv")):
        current = path.read_text()
        original = subprocess.check_output(["git", "show", f"490a50c:{path.as_posix()}"], text=True)
        old_state = set(re.findall(r"\b(\w+)\s*(?:\[[^;]+?\])?\s*<=", original))
        new_state = set(re.findall(r"\b(\w+)\s*(?:\[[^;]+?\])?\s*<=", current))
        declarations = {}
        for match in re.finditer(r"\b(?:output\s+)?reg\s*(?:\[(\d+):(\d+)\]\s*)?([\w\s,]+?)(?=[;\r\n])", current):
            width = abs(int(match[1])-int(match[2]))+1 if match[1] else 1
            for name in match[3].split(','):
                declarations[name.strip()] = width
        for name in new_state-old_state:
            if name not in declarations: raise ValueError("Cannot account added registered state: "+name)
            writers = [block for block in re.split(r"\balways\b", current)[1:] if re.search(r"\b"+name+r"\s*<=", block)]
            if len(writers) != 1: raise ValueError("Added state has conflicting writers: "+name)
            additions[path.as_posix()+":"+name] = declarations[name]
        if old_state-new_state: raise ValueError("Unexpected removal of historical registered state")
    added_bits = sum(additions.values())
    groups["transaction"] += added_bits
    widths = configuration_widths()
    expected = {"src/motif_transaction.sv:temporal_count_o":16,
                "src/motif_transaction.sv:temporal_started_o":1,
                "src/motif_transaction.sv:temporal_done_o":1}
    if additions != expected: raise ValueError("Added registered state differs from the preregistered allocation")
    return {"schema_version": 3, "configuration_bits": sum(widths.values()), "configuration_widths": widths,
            "table_bits": widths["transaction_program"], "temporal_state_bits": added_bits,
            "added_register_inventory": additions,
            "temporal_state": {"count": 16, "started": 1, "registered_complete": 1},
            "declared_state_widths": groups, "declared_total_register_bits": sum(groups.values()),
            "delta_declared_register_bits_vs_v2": sum(groups.values()) - sum(previous["state_widths_declared"].values()),
            "transaction_state_bits_declared": groups["transaction"],
            "sequencing": {"entries": 16, "entry_bits": 64, "maximum_immediate_entries_per_cycle": 4},
            "counting_contract": "Declared sequential state groups include architectural/support/diagnostic storage; combinational execution observations add no sequential state. Configuration is counted once, not once per primitive. Mapped sequential cells are separate.",
            "state_inventory_basis": "Frozen v2 state inventory plus the explicitly audited single-writer 16-bit count and two one-bit lifecycle registers; no inferred width count for combinational reg variables."}


def verify():
    frozen = json.loads(MANIFEST.read_text())
    actual = semantic_inventory()
    # New independent tests/oracles/renderers are permitted, but the existing
    # sources and every runtime source are immutable.
    changed = [name for name, digest in frozen["source_hashes"].items() if actual.get(name) != digest]
    runtime = {name: value for name, value in actual.items() if name.startswith(("src/", "motif/"))}
    expected_runtime = {name: value for name, value in frozen["source_hashes"].items() if name.startswith(("src/", "motif/"))}
    if changed or runtime != expected_runtime:
        raise ValueError("Frozen v3 semantic boundary changed: " + ", ".join(sorted(set(changed) | (runtime.keys() ^ expected_runtime.keys()))))
    if preregistration_identity() != frozen["preregistration"]:
        raise ValueError("Frozen v3 preregistration identity changed")
    for name, metadata in frozen["qualification_reports"].items():
        if sha(Path(metadata["path"]).read_bytes()) != metadata["sha256_lf"]:
            raise ValueError("Frozen qualification report changed: " + name)
    return frozen


def expected_temporal_names():
    names = {f"level{level}_t{threshold}_delta{delta}" for level in (0, 1)
             for threshold in (1, 2, 4, 16, 65535) for delta in (-1, 0, 1)}
    names |= {f"level{level}_interrupt{gap}_{policy}" for level in (0, 1)
              for gap in (1, 2, 3) for policy in ("restart", "branch")}
    names |= {f"level{level}_{kind}" for level in (0, 1) for kind in ("multiple_interruptions", "long_idle")}
    names |= {"constant_delay", "registered_timer_end_precedes_repeated_acquisition"}
    names |= {"lifecycle_" + kind for kind in ("reset", "abort", "disable", "watchdog", "release")}
    names |= {f"chained_qualifications_bridges{bridges}" for bridges in (0, 3)}
    return names


def expected_repair_names():
    original = json.loads(Path("experiments/exchange_decomposition/third_workload.json").read_text())
    names = {case["name"] for case in original["cases"]}
    names |= {"startup_interrupted_non_reset", "restart_then_valid", "valid_590us"}
    names |= {f"legal_phase_low{low}_idle{idle}" for low in (24000, 29500, 48000) for idle in (8, 9)}
    return names


def validate_gate(name, report):
    if not report.get("passed") or report.get("stage") != name or report.get("model_only"):
        raise ValueError("Missing complete passing gate: " + name)
    if name in ("temporal", "repair"):
        cases = report.get("cases", [])
        if not cases or report.get("total_compared_cycles", 0) <= 0:
            raise ValueError("RTL comparisons missing from " + name)
        expected = expected_temporal_names() if name == "temporal" else expected_repair_names()
        if len(cases) != len(expected) or {case.get("name") for case in cases} != expected:
            raise ValueError("Required unique case set incomplete: " + name)
        if any(case.get("model_rtl_agreement") is not True or not case.get("oracle", {}).get("passed") for case in cases):
            raise ValueError("Independent oracle/RTL qualification incomplete: " + name)
        if name == "repair" and sum(case.get("original_historical_case") is True for case in cases) != 9:
            raise ValueError("Original nine repair cases are incomplete")
    if name == "regression":
        i2c = report.get("i2c", {})
        cases = i2c.get("cases", [])
        if len(cases) != 48 or i2c.get("total_compared_cycles") != 88287:
            raise ValueError("Original I2C regression is incomplete")
        if any(case.get("model_rtl_agreement") is not True or case.get("historical_v2_visible_equivalence") is not True for case in cases):
            raise ValueError("I2C historical/differential comparison incomplete")
        microwire = report.get("microwire", {})
        if microwire.get("model_rtl_agreement") is not True or microwire.get("observed_word_hex") != "0xa55a":
            raise ValueError("Microwire exact-word comparison incomplete")
    if name in ("model", "regression") and (not report.get("checks") or any(check.get("passed") is not True or check.get("exit_code") != 0 for check in report["checks"])):
        raise ValueError("Required command checks missing/failed: " + name)
    if name in ("model", "regression"):
        command_names = [check.get("name") for check in report["checks"]]
        required = {"model-tests"} if name == "model" else {"all-tests", "rtl-existing-modes", "formal-existing", "rtl-lint"}
        if len(command_names) != len(set(command_names)) or not required <= set(command_names):
            raise ValueError("Required command-name set incomplete: " + name)
    if name == "cocotb":
        from tools.host_check import expected_test_names
        runtime = report.get("runtime_details", report)
        tests = runtime.get("tests", [])
        if {test.get("name") for test in tests} != expected_test_names() or any(test.get("passed") is not True for test in tests):
            raise ValueError("Complete runtime cocotb receipt required")
    if name == "synthesis":
        budget = json.loads(PREREGISTRATION.read_text())["budgets"]
        if report.get("area_ratio_vs_matched_v2", float("inf")) > budget["maximum_area_ratio"] or report.get("mapped_v3", {}).get("design", {}).get("area", float("inf")) > budget["maximum_mapped_area_um2"]:
            raise ValueError("Mapped area budget gate failed")


def freeze():
    if MANIFEST.exists():
        raise ValueError("Refusing to overwrite immutable v3 freeze")
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("Commit complete qualification evidence before v3 freeze")
    identity = report_identity()
    reports = {}
    for name in REQUIRED_REPORTS:
        path = DIRECTORY / f"{name}.json"
        report = json.loads(path.read_text())
        validate_gate(name, report)
        if report.get("source_hashes") != identity["source_hashes"]:
            raise ValueError("Stale qualification source hashes: " + name)
        if report.get("preregistration") != identity["preregistration"]:
            raise ValueError("Stale preregistration identity: " + name)
        reports[name] = {"path": path.as_posix(), "sha256_lf": sha(path.read_bytes())}
    accounting = declared_accounting()
    budget = json.loads(PREREGISTRATION.read_text())["budgets"]
    if accounting["configuration_bits"] != budget["configuration_bits"] or accounting["table_bits"] != budget["table_bits"]:
        raise ValueError("Configuration/table budget exceeded")
    if accounting["delta_declared_register_bits_vs_v2"] > budget["maximum_added_declared_state_bits"]:
        raise ValueError("Declared state budget exceeded")
    data = {"schema_version": 3, "architecture_version": 3, **identity, "qualification_reports": reports,
            "rtl_hashes": {name: digest for name, digest in identity["source_hashes"].items() if name.startswith("src/")},
            "model_hashes": {name: digest for name, digest in identity["source_hashes"].items() if name.startswith("motif/")},
            "configuration_format_hash": identity["source_hashes"]["motif/transaction.py"],
            "compiler_tool_hashes": {name: digest for name, digest in identity["source_hashes"].items() if name.startswith("tools/")},
            "accounting": accounting,
            "unseen_workload": {"selected": False, "research_started": False},
            "allowed_after_freeze": "New independent declarative configuration/testbench/oracle/stimulus/rendering/docs only; no existing protected-source/model/compiler/harness/test/oracle/report changes.",
            "physical_boundary": "Initial physical inputs are identified separately. At most the preregistered nonsemantic flow-setting revisions may produce separately hashed physical implementation manifests; semantic hashes remain unchanged."}
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("FROZEN v3", sha(MANIFEST.read_bytes()))
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--check-preregistration", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.check_preregistration:
        print("PASS immutable v3 preregistration", json.dumps(preregistration_identity(), sort_keys=True))
    else:
        verify()
        print("PASS frozen v3 semantic source, compiler, tool, test and evidence boundary")


if __name__ == "__main__":
    main()
