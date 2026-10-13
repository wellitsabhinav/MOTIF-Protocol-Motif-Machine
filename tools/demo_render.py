"""Render identified simulation rows and real elaborated connectivity.

No waveforms or schematic edges are inferred from configuration successors.
SVG is the editable figure source; PNG is a rendering of the same data.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _plotting():
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["svg.hashsalt"] = "motif-identified-demo"
        matplotlib.rcParams["svg.fonttype"] = "none"
        matplotlib.rcParams["text.parse_math"] = False
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Demo figures require matplotlib: python -m pip install matplotlib") from exc
    return plt


def _save(fig, directory, name):
    svg = Path(directory) / f"{name}.svg"
    fig.savefig(svg, metadata={"Date": None})
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8", newline="\n")
    fig.savefig(Path(directory) / f"{name}.png", dpi=160,
                metadata={"Software": "MOTIF identified simulation renderer"})


def _changes(values):
    if not values:
        return [], []
    xs, ys = [0], [values[0]]
    for i, value in enumerate(values[1:], 1):
        if value != ys[-1]:
            xs.append(i)
            ys.append(value)
    xs.append(len(values))
    ys.append(ys[-1])
    return xs, ys


def waveform(rows, directory, title, pins, cycle_ns=20, window=None, outputs=(), controller=None, annotations=None):
    """Transition compression retains every transition, including one-cycle pulses."""
    plt = _plotting()
    start, end = window or (0, len(rows))
    signals = [(label, [(r["pins"] >> pin) & 1 for r in rows]) for label, pin in pins]
    if controller is not None:
        signals.insert(0, ("controller DQ", controller))
    annotations = annotations or {}
    if "rx_pin" in annotations:
        signals.append(("synchronized RX", [(r["levels"] >> annotations["rx_pin"]) & 1 for r in rows]))
    for pin in outputs:
        signals += [(f"target OE pin {pin}", [(r["oe"] >> pin) & 1 for r in rows]),
                    (f"target DATA pin {pin}", [(r["data"] >> pin) & 1 for r in rows])]
    signals += [("active", [r["active"] for r in rows])]
    for label, key in (("temporal started", "temporal_started"), ("temporal completion", "temporal_done"),
                       ("shared timer running", "timer_running")):
        if rows and key in rows[0]:
            signals.append((label, [r[key] for r in rows]))
    has_count = bool(rows and "temporal_count" in rows[0])
    fig, axes = plt.subplots(len(signals) + int(has_count), 1, sharex=True,
                             figsize=(13, max(7.8, .62 * len(signals) + 2)),
                             gridspec_kw={"height_ratios": [1] * len(signals) + ([1.7] if has_count else [])})
    fig.suptitle(title + f" — RTL observations; {cycle_ns} ns core cycles", fontsize=13)
    for ax, (name, values) in zip(axes, signals):
        xs, ys = _changes(values)
        ax.step(xs, ys, where="post", linewidth=1.2, color="#205b8f")
        ax.set_yticks([0, 1])
        ax.set_ylim(-.15, 1.2)
        ax.set_ylabel(name, rotation=0, ha="right", va="center", fontsize=8)
        ax.grid(axis="x", color="#e3e9ee")
        if annotations.get("highlight"):
            first, last, _ = annotations["highlight"]
            ax.axvspan(first, last, color="#e8af46", alpha=.24)
    ax = axes[-1]
    if has_count:
        xs, ys = _changes([r["temporal_count"] for r in rows])
        ax.step(xs, ys, where="post", color="#c76726", linewidth=1.1)
        ax.set_ylabel("temporal count", rotation=0, ha="right", va="center", fontsize=8)
        if not any(ys):
            ax.set_ylim(-.1, 1.1)
            ax.set_yticks([0, 1])
        if annotations.get("reset_threshold"):
            threshold = annotations["reset_threshold"]
            ax.axhline(threshold, color="#a95327", linestyle="--", linewidth=.9)
            ax.set_ylim(-threshold * .03, threshold * 1.18)
            ax.text(.01, .88, f"Configured reset threshold: {threshold:,} observations ({threshold * cycle_ns / 1000:g} µs)",
                    transform=ax.transAxes, fontsize=8, color="#8c421d")
    ax.grid(color="#e3e9ee")
    ax.set_xlabel(f"core cycle (1 cycle = {cycle_ns} ns)")
    ax.set_xlim(start, max(start + 1, end))
    if annotations.get("highlight"):
        first, last, label = annotations["highlight"]
        axes[0].annotate(label, xy=((first + last) / 2, 1), xycoords="data",
                         xytext=(.55, .45), textcoords="axes fraction", fontsize=8, color="#865314",
                         arrowprops={"arrowstyle": "->", "color": "#a66d1e"})
    notes = annotations.get("notes", "")
    if notes:
        fig.text(.17, .012, notes, fontsize=9, color="#205b8f")
    fig.tight_layout(rect=(.04, .035 if notes else 0, 1, .96))
    suffix = "waveform" if window is None else f"waveform_{start}_{end}"
    _save(fig, directory, suffix)
    plt.close(fig)


def timeline(rows, directory, title, entries):
    """Each lane is an actual executor chain slot sampled before the clock edge."""
    plt = _plotting()
    fig, axes = plt.subplots(5, 1, sharex=True, figsize=(13, 7),
                             gridspec_kw={"height_ratios": [1, 1, 1, 1, 1.4]})
    fig.suptitle(title + " — actual ordered entries evaluated by RTL", fontsize=13)
    executed = [entries(r) for r in rows]
    for slot, ax in enumerate(axes[:4]):
        values = [pcs[slot] if slot < len(pcs) else -3 for pcs in executed]
        xs, ys = _changes(values)
        ax.step(xs, ys, where="post", linewidth=1, color=["#205b8f", "#168067", "#c76726", "#884ca0"][slot])
        ax.set_ylabel(f"chain slot {slot + 1}\nPC", rotation=0, ha="right", va="center", fontsize=8)
        ax.set_ylim(-3.8, 15.8)
        ax.set_yticks([-3, 0, 4, 8, 12, 15], labels=["idle", "0", "4", "8", "12", "15"])
        ax.grid(color="#e3e9ee")
    xs, ys = _changes([r.get("temporal_count", 0) for r in rows])
    axes[-1].step(xs, ys, where="post", linewidth=1.1, color="#c76726")
    if not any(ys):
        axes[-1].set_ylim(-.1, 1.1)
        axes[-1].set_yticks([0, 1])
    axes[-1].set_ylabel("temporal count", rotation=0, ha="right", va="center", fontsize=8)
    axes[-1].set_xlabel("core cycle; idle means no entry evaluated in that chain slot")
    axes[-1].grid(color="#e3e9ee")
    axes[-1].set_xlim(0, max(1, len(rows)))
    fig.tight_layout(rect=(.04, 0, 1, .96))
    _save(fig, directory, "timeline")
    plt.close(fig)


def connectivity(module, focus=None, max_cells=32):
    """Select cells by actual Yosys port-direction and net-bit connectivity."""
    cells = module.get("cells", {})
    names = module.get("netnames", {})
    visible = {name: cell for name, cell in cells.items()
               if not cell["type"].startswith("$") or cell["type"].startswith("$paramod")}
    if focus is not None:
        focus_bits = {b for name, net in names.items() if focus in name for b in net["bits"] if isinstance(b, int)}
        visible = {name: cell for name, cell in cells.items()
                   if any(focus_bits.intersection(bits) for bits in cell["connections"].values())}
        if len(visible) > max_cells:
            raise RuntimeError(f"Focus {focus!r} has {len(visible)} cells; specify a narrower named net")
    drivers, sinks = {}, {}
    for name, cell in visible.items():
        for port, bits in cell["connections"].items():
            target = drivers if cell.get("port_directions", {}).get(port) == "output" else sinks
            for bit in bits:
                if isinstance(bit, int):
                    target.setdefault(bit, set()).add((name, port))
    edges = {}
    for bit in drivers.keys() & sinks.keys():
        for source, out in drivers[bit]:
            for target, inp in sinks[bit]:
                if source != target:
                    edges.setdefault((source, target, out, inp), set()).add(bit)
    return visible, edges


def schematic(module, directory, name, title, focus=None):
    """Editable connectivity schematic from Yosys JSON, with every retained edge real."""
    plt = _plotting()
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    cells, edges = connectivity(module, focus)
    ordered = sorted(cells, key=lambda n: ("dff" not in cells[n]["type"].lower(), n))
    if not ordered:
        raise RuntimeError(f"No elaborated cells found for {title}")
    columns = 2 if len(ordered) < 12 else 3
    per_column = (len(ordered) + columns - 1) // columns
    positions = {n: (i // per_column * 5, -(i % per_column) * 1.7) for i, n in enumerate(ordered)}
    fig, ax = plt.subplots(figsize=(15, max(5, per_column * 1.05)))
    for (source, target, out, inp), bits in edges.items():
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        arrow = FancyArrowPatch((x1 + 1.85, y1), (x2 - 1.85, y2), arrowstyle="->",
                                mutation_scale=9, color="#8093a3", alpha=.55,
                                connectionstyle="arc3,rad=.09", linewidth=.75)
        ax.add_patch(arrow)
    for node, (x, y) in positions.items():
        ax.add_patch(FancyBboxPatch((x - 1.85, y - .5), 3.7, 1,
                                  boxstyle="round,pad=.03", facecolor="#f2f7fb", edgecolor="#205b8f"))
        kind = cells[node]["type"]
        if kind.startswith("$paramod"):
            kind = next((part for part in kind.split("\\") if part.startswith(("motif_", "tt_um_"))), kind)
        label = node
        if node.startswith("$"):
            identifier = re.findall(r"\$(\d+)", node)
            label = kind.lstrip("$") + (" · cell " + identifier[-1] if identifier else "")
            outputs = [bits for port, bits in cells[node]["connections"].items()
                       if cells[node].get("port_directions", {}).get(port) == "output"]
            aliases = [name for name, net in module.get("netnames", {}).items()
                       if not name.startswith("$") and any(net["bits"] == bits for bits in outputs)]
            if aliases:
                preferred = next((name for name in aliases if focus and focus in name), min(aliases, key=len))
                label = preferred
        if len(label) > 43:
            label = label[:19] + "…" + label[-20:]
        ax.text(x, y + .12, label, fontsize=7, ha="center", va="center")
        ax.text(x, y - .2, kind, fontsize=7, ha="center", color="#205b8f")
    ax.set_xlim(-2.4, (columns - 1) * 5 + 2.4)
    ax.set_ylim(-per_column * 1.7 + .5, 1.5)
    ax.axis("off")
    fig.suptitle(title + "\nYosys elaborated connectivity; omitted ports and logic are listed in source JSON", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .94))
    _save(fig, directory, name)
    plt.close(fig)
    selection = {"title": title, "focus_net_substring": focus,
                 "cells": {n: {"type": c["type"], "connections": c["connections"],
                                "port_directions": c.get("port_directions", {})} for n, c in cells.items()},
                 "edges": [{"source": s, "target": t, "output": o, "input": i, "bit_ids": sorted(bits)}
                           for (s, t, o, i), bits in edges.items()]}
    (Path(directory) / f"{name}.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")


def evolution(inventories, directory):
    plt = _plotting()
    fig, axes = plt.subplots(1, len(inventories), figsize=(15, 6))
    for ax, item in zip(axes, inventories):
        ax.axis("off")
        text = item["label"] + "\n" + item["identity"][:12] + "\n\n" + "\n".join(item["modules"])
        ax.text(.05, .92, text, va="top", fontsize=9, family="monospace",
                bbox={"boxstyle": "round,pad=1", "facecolor": "#f2f7fb", "edgecolor": "#205b8f"})
    fig.suptitle("Legacy → v2 → working v3: actual module inventories\nInventory differences document structure, not protocol qualification", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, .9))
    _save(fig, directory, "evolution")
    plt.close(fig)
    (Path(directory) / "evolution.json").write_text(json.dumps(inventories, indent=2) + "\n", encoding="utf-8")
