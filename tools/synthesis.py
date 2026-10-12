import json
import os
import subprocess
import re
import argparse
import hashlib
import urllib.request
from pathlib import Path


def synthesize(top, destination, library=None):
    files = " ".join(path.as_posix() for path in sorted(Path("src").glob("*.sv")))
    abc = os.environ.get("YOSYS_ABC")
    script = f"read_verilog -sv {files}; synth -top {top} -noabc; "
    if library:
        script += f"dfflibmap -liberty {library.as_posix()}; "
    script += "abc" + (f" -exe {Path(abc).as_posix()}" if abc else "") + (f" -liberty {library.as_posix()}" if library else "") + "; "
    script += "clean; stat" + (f" -liberty {library.as_posix()}" if library else "") + " -json"
    result = subprocess.run([os.environ.get("YOSYS", "yosys"), "-Q", "-T", "-p", script], capture_output=True, text=True)
    directory = Path("build/synthesis")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (top + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError("Synthesis failed; inspect build/synthesis")
    offset = result.stdout.rfind('\n{\n   "creator"')
    if offset < 0:
        raise RuntimeError("Synthesis JSON not found")
    stats, _ = json.JSONDecoder().raw_decode(result.stdout[offset:].lstrip())
    modules = {}
    for name, info in stats["modules"].items():
        modules[name] = {key: value for key, value in info.items() if key in ("num_cells", "num_cells_by_type", "num_wire_bits", "num_memories", "num_memory_bits", "area")}
    report = {"schema_version": 1, "kind": "technology_mapped_cell_area" if library else "generic_unmapped_cell_count", "top": top,
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
                      allocated_configuration_bits=1096 if Path("src/motif_transaction.sv").exists() else 78,
                      limitations="Nominal typical-cell mapping only; no CTS, placement, routing, extracted timing or silicon evidence")
    report["source_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    report["rtl_source_hashes"] = {p.as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                                   for p in sorted(Path("src").glob("*.sv"))}
    report["scope"] = "Current connected implementation; synthesis alone does not qualify protocol behavior or a matched reference"
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(top, report["design"].get("num_cells"), "cells", report["design"].get("area", "unmapped"))


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
