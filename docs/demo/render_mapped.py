"""Render the already measured CMOS5L netlist; never run synthesis.

python docs/demo/render_mapped.py
Full mapped netlists stay in build/. Selected connectivity JSON/SVG/PNG lives
under docs/demo/figures/mapped and retains measurement/source/tool identities.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.demo_render import _plotting, _save


def raw_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blackbox(module):
    value = module.get("attributes", {}).get("blackbox", 0)
    return bool(int(value, 2) if isinstance(value, str) else value)


def directions_from_library(path):
    """Read actual Liberty pin directions when mapped JSON omits cell metadata."""
    text = Path(path).read_text()
    def block(start):
        depth = 1
        for end in range(start, len(text)):
            depth += (text[end] == "{") - (text[end] == "}")
            if depth == 0:
                return text[start:end]
        raise ValueError("Unbalanced pinned Liberty cell")
    directions = {}
    for match in re.finditer(r'\bcell\s*\(\s*"?([^\s"\)]+)"?\s*\)\s*\{', text):
        body = block(match.end())
        pins = {}
        for pin in re.finditer(r'\bpin\s*\(\s*"?([^\s"\)]+)"?\s*\)\s*\{', body):
            absolute = match.end() + pin.end()
            value = re.search(r'\bdirection\s*:\s*"?(input|output|inout)"?\s*;', block(absolute))
            if value:
                pins[pin[1]] = value[1]
        directions[match[1]] = pins
    return directions


def module_label(name):
    return next((part for part in name.split("\\") if part.startswith(("motif_", "tt_um_"))), name)


def hierarchy(modules, top):
    counts = {}
    def leaves(name, stack=()):
        if name in counts:
            return counts[name]
        if name in stack:
            raise ValueError("Recursive module hierarchy in measured netlist")
        total = 0
        for cell in modules[name].get("cells", {}).values():
            kind = cell["type"]
            total += leaves(kind, (*stack, name)) if kind in modules and not blackbox(modules[kind]) else 1
        counts[name] = total
        return total
    nodes, edges = [], []
    def walk(kind, path, parent=None, depth=0):
        child_cells = [(name, cell) for name, cell in modules[kind].get("cells", {}).items()
                       if cell["type"] in modules and not blackbox(modules[cell["type"]])]
        direct = len(modules[kind].get("cells", {})) - len(child_cells)
        node = {"path": path, "module": kind, "depth": depth, "leaf_cells": leaves(kind), "direct_leaf_cells": direct}
        nodes.append(node)
        if parent is not None:
            edges.append([parent, path])
        for instance, cell in sorted(child_cells):
            walk(cell["type"], path + "/" + instance, path, depth + 1)
    walk(top, top)
    return nodes, edges


def render_hierarchy(nodes, edges, directory):
    plt = _plotting()
    from matplotlib.patches import FancyBboxPatch
    depths = sorted({n["depth"] for n in nodes})
    levels = {depth: [n for n in nodes if n["depth"] == depth] for depth in depths}
    height = max(len(group) for group in levels.values())
    positions = {}
    for depth, group in levels.items():
        for row, node in enumerate(group):
            positions[node["path"]] = (depth * 5, -(row - (len(group) - 1) / 2) * 1.5)
    fig, ax = plt.subplots(figsize=(max(13, len(depths) * 4.7), max(5, height * .8)))
    for source, target in edges:
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        ax.plot([x1 + 1.95, x2 - 1.95], [y1, y2], color="#8497a6", linewidth=.9)
    for node in nodes:
        x, y = positions[node["path"]]
        ax.add_patch(FancyBboxPatch((x - 1.95, y - .52), 3.9, 1.04, boxstyle="round,pad=.04",
                                   facecolor="#edf6f2", edgecolor="#217758"))
        ax.text(x, y + .24, node["path"].rsplit("/", 1)[-1], fontsize=8, ha="center")
        ax.text(x, y, module_label(node["module"]), fontsize=7.5, ha="center", color="#217758")
        ax.text(x, y - .26, f"{node['leaf_cells']:,} mapped leaf cells; {node['direct_leaf_cells']:,} direct", fontsize=7.5, ha="center")
    ax.set_xlim(-2.4, max(depths) * 5 + 2.4)
    ax.set_ylim(-height * .8 - 1, height * .8 + 1)
    ax.axis("off")
    fig.suptitle("Measured CMOS5L v3: actual mapped hierarchy and leaf-cell counts\nHierarchy edges are actual module instances; individual standard cells are counted, not drawn here", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .92))
    _save(fig, directory, "hierarchy")
    plt.close(fig)


def focus(module, name, bit_index, max_neighbors=8):
    nets = module["netnames"]
    if name not in nets or len(nets[name]["bits"]) <= bit_index:
        raise ValueError("Named mapped state net is unavailable: " + name)
    bit = nets[name]["bits"][bit_index]
    if not isinstance(bit, int):
        raise ValueError("Selected mapped state bit was optimized to a constant")
    cells = module.get("cells", {})
    drivers, sinks = {}, {}
    for cell_name, cell in cells.items():
        for port, bits in cell["connections"].items():
            direction = cell["port_directions"].get(port)
            if direction not in ("input", "output"):
                raise ValueError(f"Missing actual mapped port direction: {cell['type']}.{port}")
            target = drivers if direction == "output" else sinks
            for net in bits:
                if isinstance(net, int):
                    target.setdefault(net, set()).add((cell_name, port))
    owners = sorted(drivers.get(bit, set()))
    if len(owners) != 1:
        raise ValueError("Selected state bit lacks a unique mapped-cell driver")
    owner, output_port = owners[0]
    fanin = set()
    for port, bits in cells[owner]["connections"].items():
        if cells[owner]["port_directions"][port] == "input":
            for net in bits:
                fanin.update(cell for cell, _ in drivers.get(net, set()))
    fanout_all = {cell for cell, _ in sinks.get(bit, set()) if cell != owner}
    fanout = set(sorted(fanout_all)[:max_neighbors])
    selected = {owner, *fanin, *fanout}
    edges = {}
    for net in drivers.keys() & sinks.keys():
        for source, output in drivers[net]:
            for target, inp in sinks[net]:
                if source in selected and target in selected and source != target:
                    edges.setdefault((source, output, target, inp), set()).add(net)
    boundaries = []
    for cell in sorted(selected):
        for port, bits in cells[cell]["connections"].items():
            direction = cells[cell]["port_directions"][port]
            for net in bits:
                connected = drivers.get(net, set()) if direction == "input" else sinks.get(net, set())
                outside = [(c, p) for c, p in connected if c not in selected]
                if outside or not connected or not isinstance(net, int):
                    aliases = [n for n, info in nets.items() if not n.startswith("$") and net in info["bits"]]
                    boundaries.append({"cell": cell, "port": port, "direction": direction, "bit": net,
                                       "public_aliases": aliases, "omitted_connected_ports": outside})
    return {"focus_net": name, "bit_index": bit_index, "bit_id": bit, "owner": owner, "owner_output": output_port,
            "selected_cells": {n: cells[n] for n in sorted(selected)},
            "edges": [{"source": s, "output": o, "target": t, "input": i, "bit_ids": sorted(bits)}
                      for (s, o, t, i), bits in sorted(edges.items())],
            "direct_fanin_cells": sorted(fanin), "selected_fanout_cells": sorted(fanout),
            "total_direct_fanout_cells": len(fanout_all), "omitted_module_cells": len(cells) - len(selected),
            "boundary_ports": boundaries}


def render_focus(selection, directory, filename, title):
    plt = _plotting()
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    owner = selection["owner"]
    fanin = selection["direct_fanin_cells"]
    fanout = [n for n in selection["selected_fanout_cells"] if n not in fanin]
    positions = {owner: (0, 0)}
    for column, group in ((-5, fanin), (5, fanout)):
        for row, cell in enumerate(group):
            positions[cell] = (column, -(row - (len(group) - 1) / 2) * 1.55)
    height = max(3, len(fanin), len(fanout))
    fig, ax = plt.subplots(figsize=(17, max(5.5, height * .9)))
    for edge in selection["edges"]:
        x1, y1 = positions[edge["source"]]
        x2, y2 = positions[edge["target"]]
        ax.add_patch(FancyArrowPatch((x1 + 1.95, y1), (x2 - 1.95, y2), arrowstyle="->", mutation_scale=9,
                                    color="#6d8793", linewidth=.9, connectionstyle="arc3,rad=.03"))
        if edge["source"] == owner or edge["target"] == owner:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + .08,
                    f"{edge['output']} → {edge['input']}\nbits {','.join(map(str, edge['bit_ids']))}",
                    fontsize=7, ha="center", color="#49636e")
    for cell, (x, y) in positions.items():
        data = selection["selected_cells"][cell]
        ax.add_patch(FancyBboxPatch((x - 1.95, y - .5), 3.9, 1, boxstyle="round,pad=.03",
                                   facecolor="#e5f4ea" if cell == owner else "#f2f7f4", edgecolor="#217758"))
        identifier = cell.rsplit("$", 1)[-1]
        label = f"{selection['focus_net']}[{selection['bit_index']}]" if cell == owner else "cell " + identifier
        ax.text(x, y + .19, label, ha="center", fontsize=8)
        ax.text(x, y - .12, data["type"], ha="center", fontsize=7.5, color="#217758")
    ax.text(-7.1, -height * .85 - .15,
            f"Selected {len(positions)} actual mapped cells; {selection['omitted_module_cells']:,} module cells omitted. "
            f"{len(fanout)} of {selection['total_direct_fanout_cells']} direct fanout cells shown.\n"
            "Clock/reset and other boundary net identities are preserved in the matching JSON; no boundary logic is inferred.",
            fontsize=8, va="top", color="#49636e")
    ax.set_xlim(-7.5, 7.5)
    ax.set_ylim(-height * .85 - 1, height * .85 + .6)
    ax.axis("off")
    fig.suptitle(title + "\nMeasured CMOS5L standard-cell connectivity; arrows show actual named ports and net-bit IDs", fontsize=12)
    fig.tight_layout(rect=(0, .015, 1, .93))
    _save(fig, directory, filename)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netlist", type=Path, default=ROOT / "build/v3_temporal_qualification/synthesis/mapped_v3.netlist.json")
    parser.add_argument("--report", type=Path, default=ROOT / "build/v3_temporal_qualification/synthesis/mapped_v3.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/demo/figures/mapped")
    args = parser.parse_args()
    if not args.netlist.is_file() or not args.report.is_file():
        raise SystemExit("UNAVAILABLE: measured v3 mapped netlist/report have not been produced; no alternate synthesis is run")
    report = json.loads(args.report.read_text())
    if report.get("kind") != "technology_mapped_cell_area" or report["netlist_sha256"].get(args.netlist.name) != raw_sha(args.netlist):
        raise ValueError("Measured mapped-netlist identity or kind disagrees with its report")
    for filename, expected in report["rtl_source_hashes"].items():
        actual = hashlib.sha256((ROOT / filename).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != expected:
            raise ValueError("Measured RTL differs from current source: " + filename)
    data = json.loads(args.netlist.read_text())
    modules = data["modules"]
    missing = any(not c.get("port_directions") for m in modules.values() for c in m.get("cells", {}).values())
    if missing:
        library = ROOT / "build/pdk" / report["library"]
        if raw_sha(library) != report["library_sha256"]:
            raise ValueError("Pin-direction library differs from the measured library")
        directions = directions_from_library(library)
        for module in modules.values():
            for cell in module.get("cells", {}).values():
                if not cell.get("port_directions"):
                    cell["port_directions"] = directions.get(cell["type"],
                        {name: port["direction"] for name, port in modules.get(cell["type"], {}).get("ports", {}).items()})
    directory = args.output_dir
    directory.mkdir(parents=True, exist_ok=True)
    provenance = {"kind": "selected_measured_technology_mapped_connectivity", "netlist_sha256": raw_sha(args.netlist),
                  "measurement_report_sha256": raw_sha(args.report), "rtl_source_hashes": report["rtl_source_hashes"],
                  "source_sha": report["source_sha"], "tools": report["tools"], "yosys": report["yosys"],
                  "library_sha256": report["library_sha256"], "renderer_sha256": raw_sha(Path(__file__)),
                  "scope": "Measured nominal mapped logic; no placement, routing, timing closure or physical qualification claim"}
    nodes, edges = hierarchy(modules, report["top"])
    render_hierarchy(nodes, edges, directory)
    (directory / "hierarchy.json").write_text(json.dumps({**provenance, "nodes": nodes, "edges": edges}, indent=2) + "\n", newline="\n")
    transactions = [(name, module) for name, module in modules.items() if name == "motif_transaction" or "motif_transaction" in name.split("\\")]
    if len(transactions) != 1:
        raise ValueError("Expected one measured transaction module")
    module_name, module = transactions[0]
    for net, filename, title in (("pc_o", "transaction_bit0", "Transaction program counter bit 0 and neighboring mapped cells"),
                                  ("temporal_count_o", "temporal_bit0", "Temporal qualification counter bit 0 and neighboring mapped cells")):
        selected = focus(module, net, 0)
        render_focus(selected, directory, filename, title)
        (directory / f"{filename}.json").write_text(json.dumps({**provenance, "module": module_name, **selected}, indent=2) + "\n", newline="\n")
    files = {p.name: raw_sha(p) for p in directory.iterdir() if p.is_file() and p.name != "identity.json"}
    (directory / "identity.json").write_text(json.dumps({**provenance, "selected_artifacts_sha256": files}, indent=2) + "\n", newline="\n")
    print("PASS measured mapped hierarchy and state-bit neighborhoods; identities preserved; no synthesis run")


if __name__ == "__main__":
    main()
