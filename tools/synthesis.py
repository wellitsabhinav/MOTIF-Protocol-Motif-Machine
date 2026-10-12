import json
import os
import subprocess
import re
import argparse
import hashlib
import urllib.request
import shutil
from pathlib import Path


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def executable_identity(command):
    located = shutil.which(command)
    if located is None and Path(command).is_file():
        located = str(Path(command).resolve())
    return {"command": Path(command).name, "sha256": file_hash(located) if located else None}


def configuration_widths(source_root=Path(".")):
    """Count allocated host configuration declarations, excluding diagnostics/glue."""
    text = (Path(source_root) / "src/tt_um_wellitsabhinav_motif.sv").read_text()
    names = {"control", "pins_low", "pins_high", "period", "watchdog", "fill", "open_drain", "transaction_control", "transaction_program"}
    widths = {}
    for match in re.finditer(r"\breg\s*(?:\[(\d+):(\d+)\]\s*)?([^;]+);", text):
        width = abs(int(match[1]) - int(match[2])) + 1 if match[1] else 1
        for declaration in match[3].split(","):
            name = declaration.strip().split("=", 1)[0].strip()
            if name in names:
                widths[name] = width
    if "transaction_program" not in widths:
        return {"historical_configuration": 78}
    if widths.keys() != names:
        raise ValueError("Unaccounted host configuration declarations")
    return widths


def yosys_path(path):
    return '"' + Path(path).as_posix().replace('"', '\\"') + '"'


def synthesize(top, destination, library=None, source_root=Path("."), source_sha=None):
    source_root, destination = Path(source_root), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rtl_sources = sorted((source_root / "src").glob("*.sv"))
    files = " ".join(yosys_path(path) for path in rtl_sources)
    abc = os.environ.get("YOSYS_ABC")
    script = f"read_verilog -sv {files}; synth -top {top} -noabc; "
    if library:
        script += f"dfflibmap -liberty {yosys_path(library)}; "
    script += "abc" + (f" -exe {yosys_path(abc)}" if abc else "") + (f" -liberty {yosys_path(library)}" if library else "") + "; "
    script += f"clean; write_json {yosys_path(destination.with_suffix('.netlist.json'))}; "
    script += f"write_verilog {yosys_path(destination.with_suffix('.netlist.v'))}; "
    script += "clean; stat" + (f" -liberty {yosys_path(library)}" if library else "") + " -json"
    result = subprocess.run([os.environ.get("YOSYS", "yosys"), "-Q", "-T", "-p", script], capture_output=True, text=True)
    directory = destination.parent
    destination.with_suffix('.log').write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError("Synthesis failed; inspect " + str(directory))
    offset = result.stdout.rfind('\n{\n   "creator"')
    if offset < 0:
        raise RuntimeError("Synthesis JSON not found")
    stats, _ = json.JSONDecoder().raw_decode(result.stdout[offset:].lstrip())
    modules = {}
    for name, info in stats["modules"].items():
        modules[name] = {key: value for key, value in info.items() if key in ("num_cells", "num_cells_by_type", "num_wire_bits", "num_memories", "num_memory_bits", "area")}
    report = {"schema_version": 2, "kind": "technology_mapped_cell_area" if library else "generic_unmapped_cell_count", "top": top,
              "yosys": stats["creator"], "modules": modules, "design": stats.get("design", {}),
              "limitations": "Generic Boolean mapping; no technology area, critical path, placed timing or routing evidence"}
    if library:
        text = library.read_text()
        matches = list(re.finditer(r'\bcell\s*\(\s*"?([^\s"\)]+)"?\s*\)\s*\{', text))
        sequential = {}
        for index, match in enumerate(matches):
            body = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)]
            if re.search(r'\b(?:ff|latch)\s*\(', body):
                area = re.search(r'\barea\s*:\s*([\d.eE+-]+)', body)
                sequential[match.group(1)] = float(area.group(1))
        types = report['design']['num_cells_by_type']
        seq_area = sum(count * sequential[name] for name, count in types.items() if name in sequential)
        report.update(library=library.name, area_units="square micrometres", register_count=sum(count for name, count in types.items() if name in sequential),
                      sequential_area=seq_area, combinational_area=report['design']['area'] - seq_area,
                      mux_cells={name: count for name, count in types.items() if "mux" in name},
                      sequential_cell_count=sum(count for name, count in types.items() if name in sequential),
                      combinational_cell_count=report['design']['num_cells'] - sum(count for name, count in types.items() if name in sequential),
                      allocated_configuration_bits=sum(configuration_widths(source_root).values()),
                      configuration_widths=configuration_widths(source_root), library_sha256=file_hash(library),
                      limitations="Nominal typical-cell mapping only; no CTS, placement, routing, extracted timing or silicon evidence")
    report["source_sha"] = source_sha or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    report["rtl_source_hashes"] = {p.relative_to(source_root).as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                                   for p in rtl_sources}
    report["tools"] = {"yosys": executable_identity(os.environ.get("YOSYS", "yosys")),
                       "abc": executable_identity(abc) if abc else {"command": "yosys-default", "sha256": None}}
    report["netlist_sha256"] = {destination.with_suffix(suffix).name: file_hash(destination.with_suffix(suffix)) for suffix in (".netlist.json", ".netlist.v")}
    report["synthesis_command_sha256"] = hashlib.sha256(script.encode()).hexdigest()
    report["scope"] = "Current connected implementation; synthesis alone does not qualify protocol behavior or a matched reference"
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(top, report["design"].get("num_cells"), "cells", report["design"].get("area", "unmapped"))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmos5l", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("build/synthesis/current"),
                        help="Current-source reports; historical checked-in subset reports are not overwritten")
    args = parser.parse_args()
    library = None
    if args.cmos5l:
        lock = json.loads(Path("flow-lock.json").read_text())
        library = Path("build/pdk/sg13cmos5l_stdcell_typ_1p20V_25C.lib")
        library.parent.mkdir(parents=True, exist_ok=True)
        url = "https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/" + lock["pdk"]["revision"] + "/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/lib/" + library.name
        urllib.request.urlretrieve(url, library)
    prefix = "mapped" if library else "synthesis"
    synthesize("tt_um_wellitsabhinav_motif", args.output_dir / (prefix + "_motif.json"), library)
    synthesize("motif_reference_top", args.output_dir / (prefix + "_reference.json"), library)
