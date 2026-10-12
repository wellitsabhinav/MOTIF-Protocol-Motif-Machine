import json
import os
import subprocess
from pathlib import Path


def synthesize(top, destination):
    files = " ".join(path.as_posix() for path in sorted(Path("src").glob("*.sv")))
    abc = os.environ.get("YOSYS_ABC")
    script = f"read_verilog -sv {files}; synth -top {top} -noabc; "
    script += f"abc -exe {Path(abc).as_posix()}; " if abc else "abc; "
    script += "clean; stat -json"
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
        modules[name] = {key: value for key, value in info.items() if key in ("num_cells", "num_cells_by_type", "num_wire_bits", "num_memories", "num_memory_bits")}
    report = {"schema_version": 1, "kind": "generic_unmapped_cell_count", "top": top,
              "yosys": stats["creator"], "modules": modules, "design": stats.get("design", {}),
              "limitations": "Generic Boolean mapping; no technology area, critical path, placed timing or routing evidence"}
    Path(destination).parent.mkdir(exist_ok=True)
    Path(destination).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(top, report["design"].get("num_cells"), "generic cells")


if __name__ == "__main__":
    synthesize("tt_um_wellitsabhinav_motif", "reports/synthesis_motif.json")
    synthesize("motif_reference_top", "reports/synthesis_reference.json")
