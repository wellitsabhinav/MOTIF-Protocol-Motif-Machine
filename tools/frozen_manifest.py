"""Immutable experiment inventories; hashes use Git's LF text convention."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from tools.accounting import CONFIG_WIDTHS, STATE_WIDTHS, report

DIRECTORY = Path("experiments/generalization")
INITIAL = DIRECTORY / "frozen_motif_vocabulary.json"
PROMOTED = DIRECTORY / "promoted_motif_vocabulary.json"


def digest(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def inventory(root=Path(".")):
    files = list((root / "src").rglob("*.sv")) + list((root / "src").rglob("*.json"))
    files += list((root / "motif").rglob("*.py"))
    files += [root / p for p in ("info.yaml", "flow-lock.json", ".github/workflows/gds.yml")]
    return {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in sorted(files)}


def git_inventory(sha):
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", sha], text=True).splitlines()
    names = [p for p in names if (p.startswith("src/") and p.endswith((".sv", ".json")))
             or (p.startswith("motif/") and p.endswith(".py"))
             or p in ("info.yaml", "flow-lock.json", ".github/workflows/gds.yml")]
    return {p: digest(subprocess.check_output(["git", "show", f"{sha}:{p}"])) for p in names}


def compare(expected, actual):
    added = sorted(actual.keys() - expected.keys())
    removed = sorted(expected.keys() - actual.keys())
    changed = sorted(p for p in actual.keys() & expected.keys() if actual[p] != expected[p])
    if added or removed or changed:
        raise ValueError(f"Frozen boundary violation: added={added}, removed={removed}, changed={changed}")


def verify(path, historical=False, root=Path(".")):
    data = json.loads(path.read_text(encoding="utf-8"))
    actual = git_inventory(data["source_sha"]) if historical else inventory(root)
    compare(data["source_hashes"], actual)
    if data.get("parent_manifest"):
        parent = Path(data["parent_manifest"])
        if digest(parent.read_bytes()) != data["parent_manifest_sha256"]:
            raise ValueError("Initial manifest changed after promotion")
    return data


def freeze(path, parent=None):
    if path.exists():
        raise ValueError("Refusing to overwrite an immutable manifest")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    sources = inventory()
    compare(git_inventory(sha), sources)
    usage = report()
    locations = {
        "FRAME_ACQUIRE": ("motif/engine.py", "Engine.step", "src/motif_core.sv", "motif_core"),
        "FRAME_RELEASE": ("motif/engine.py", "Engine._release/step", "src/motif_core.sv", "motif_core"),
        "RESET_COUNTER": ("motif/motifs/shift.py", "ShiftRXCount.clear", "src/motif_shift_rx_count.sv", "motif_shift_rx_count"),
        "SHIFT_RX_COUNT": ("motif/motifs/shift.py", "ShiftRXCount.fire", "src/motif_shift_rx_count.sv", "motif_shift_rx_count"),
        "SHIFT_TX": ("motif/motifs/shift.py", "ShiftTX", "src/motif_shift_tx.sv", "motif_shift_tx"),
        "TIMED_SAMPLE": ("motif/motifs/timed.py", "TimedSample", "src/motif_timed_sample.sv", "motif_timed_sample"),
        "BYTE_EXCHANGE": ("motif/motifs/exchange.py", "ByteExchange", "src/motif_byte_exchange.sv", "motif_byte_exchange"),
    }
    aliases = {"SHIFT_TX_LOAD": "SHIFT_TX", **{name: "BYTE_EXCHANGE" for name in
               ("MATCH_FIRST_WORD", "OPEN_DRAIN_ACK", "OPEN_DRAIN_ACK_SAMPLE", "TURNAROUND", "STRETCH_UNTIL_READY")}}
    entries = []
    routed_fields = {
        "FRAME_ACQUIRE": ["frame", "frame_pin", "clock_pin", "rx_pin", "exchange"],
        "FRAME_RELEASE": ["frame", "frame_pin", "clock_pin", "rx_pin", "exchange", "watchdog"],
        "RESET_COUNTER": [],
        "SHIFT_RX_COUNT": ["rx_pin", "clock_pin", "sample", "lsb_first", "exchange"],
        "SHIFT_TX": ["tx_pin", "clock_pin", "transmit", "lsb_first", "fill", "exchange"],
        "TIMED_SAMPLE": ["period", "validate_start", "validate_stop", "rx_pin", "sample", "exchange"],
        "BYTE_EXCHANGE": ["address", "ack_address", "ack_data", "transmit", "lsb_first", "exchange", "period", "rx_pin", "tx_pin", "clock_pin", "open_drain"],
    }
    for name, fields in usage["motifs"].items():
        model, actor, rtl, module = locations[name]
        assumptions = []
        if name == "BYTE_EXCHANGE":
            assumptions = ["seven-bit first-word match with bit zero selecting direction", "fixed eight-bit data and ninth-clock ACK",
                           "active-low controller ACK continues TX; NACK terminates", "shared open-drain data and distinct external clock",
                           "FIFO readiness stretches clock; resolved first bit checked after shared timer expiry"]
        elif name == "TIMED_SAMPLE":
            assumptions = ["optional low start and high stop validation around eight samples"]
        elif name.startswith("FRAME_"):
            assumptions = ["fixed level/falling acquisition modes; two-wire framing exists in model" + (" and RTL" if parent else " only")]
        entries.append({"name": name, "source_sha": sha, "model_source": model, "model_actor": actor,
                        "rtl_source": rtl if rtl in sources else None, "rtl_module": module if rtl in sources else None,
                        "configuration_fields": fields["configuration_fields"], "state_groups": [fields["storage_group"]],
                        "input_events": fields["input_events"], "output_events": fields["output_events"],
                        "data_inputs": fields["data_inputs"], "data_outputs": fields["data_outputs"],
                        "protocol_users": fields["protocols"], "contains_protocol_specific_assumptions": bool(assumptions),
                        "assumptions": assumptions})
        if parent:
            entries[-1]["configuration_fields_from_initial_accounting"] = fields["configuration_fields"]
            entries[-1]["configuration_fields"] = routed_fields[name]
            header = Path(rtl).read_text().split(");", 1)[0]
            entries[-1]["rtl_port_declarations"] = re.findall(r"(?:input|output)\s+[^,;]+(?:,[^\n;]+)?", header)
    data = {"schema_version": 1, "baseline": "model_faithful_i2c_promotion" if parent else "initial_model_and_rtl_subset",
            "source_sha": sha, "hash_convention": "SHA-256 of text with CRLF normalized to LF",
            "control_boundary": "All motif/model sources, synthesizable integration, pin/configuration logic and physical flow inputs; existing interface only",
            "motifs": entries, "firing_aliases": aliases, "configuration_widths": CONFIG_WIDTHS,
            "state_groups_model_estimates": STATE_WIDTHS, "source_hashes": sources,
            "support_components": ["frontend", "fixed event/data integration", "FIFO", "guardian", "watchdog", "host/configuration", "guarded drive history"],
            "exchange_phases": ["rx", "decide", "ack_setup", "ack_hold", "tx", "controller_ack", "stretch", "settle", "idle"],
            "counting_contract": usage["counting_contract"]}
    if parent:
        data.update(parent_manifest=parent.as_posix(), parent_manifest_sha256=digest(parent.read_bytes()),
                    transition="Gate 1 promoted existing model machinery; no Gate 2/3 experiment uses the initial RTL-only subset")
        data["metadata_refinement"] = "Promoted per-motif configuration fields include routed dependencies; the original accounting-field inventory and full initial configuration schema remain preserved. This refines metadata, not available hardware controls."
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", choices=("initial", "promoted"))
    parser.add_argument("--historical", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        freeze(INITIAL if args.freeze == "initial" else PROMOTED, None if args.freeze == "initial" else INITIAL)
    else:
        path = PROMOTED if PROMOTED.exists() else INITIAL
        verify(path, historical=args.historical)
        print("PASS frozen boundary", path)


if __name__ == "__main__":
    main()
