"""Reproduce bounded protocol demonstrations with identified RTL evidence.

Run from the repository root: python -m tools.demo --all
Full waveforms, elaborated netlists and simulator output remain under build/demo.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PROTOCOLS = ("i2c", "microwire", "one_wire", "spi", "uart", "timed_stream")
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/demo"
NAMES = ("RX", "DECIDE", "RESPOND", "HANDOFF", "WAIT", "TX", "HALT", "CONTINUE")


def sha(path):
    path = Path(path)
    data = path.read_bytes()
    if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif"):
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def identity():
    files = [*ROOT.joinpath("src").glob("*.sv"), *ROOT.joinpath("motif").rglob("*.py"),
             ROOT / "tools/demo.py", ROOT / "tools/demo_render.py", ROOT / "tools/v3_trace.py",
             ROOT / "tools/exchange_decomposition.py", ROOT / "tools/unseen_protocol.py",
             ROOT / "tools/byte_exchange_falsification.py", ROOT / "tests/drivers.py", ROOT / "tests/i2c_driver.py",
             ROOT / "experiments/generalization/microwire_workload.json",
             ROOT / "experiments/exchange_decomposition/third_workload.json"]
    repair = ROOT / "experiments/temporal_qualification/configurations/one_wire_reset_presence.json"
    if repair.exists():
        files.append(repair)
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(files) if p.exists()}


def campaign_status():
    directory = ROOT / "experiments/temporal_qualification"
    freeze = directory / "frozen_v3_manifest.json"
    candidates = [directory / "campaign_result.json", directory / "cost_result.json",
                  directory / "synthesis.json", directory / "qualification.json"]
    evidence = {p.relative_to(ROOT).as_posix(): json.loads(p.read_text(encoding="utf-8"))
                for p in candidates if p.exists()}
    summary = evidence.get((directory / "campaign_result.json").relative_to(ROOT).as_posix(), {})
    status = summary.get("status") or summary.get("classification") or ("frozen" if freeze.exists() else "in progress; unfrozen")
    return {"status": status,
            "freeze_sha256_lf": sha(freeze) if freeze.exists() else None,
            "evidence": evidence,
            "physical": "No v3 physical claim is established by the demonstration package."}


def config_summary(config):
    from motif.transaction import Entry
    data = asdict(config)
    data["program"] = [f"0x{word:016x}" for word in config.program]
    data["entries"] = [{"pc": pc, "operation": NAMES[Entry.decode(word).opcode],
                        **asdict(Entry.decode(word))} for pc, word in enumerate(config.program)]
    data["program_host_bytes"] = "".join(word.to_bytes(8, "little").hex() for word in config.program)
    return data


def _host(engine, wire, byte=None, pop=False):
    old = engine.rx_fifo[0] if pop and engine.rx_fifo else None
    engine.host_push = byte is not None
    engine.host_data = byte or 0
    engine.host_pop = pop
    wire.hold(1)
    return old


def build_case(protocol):
    from tools.v3_trace import Recorder
    from tests.drivers import Wires
    from motif.protocols import spi, uart, timed_stream
    if protocol == "i2c":
        from motif.protocols.i2c import target
        from tests.i2c_driver import Bus
        engine = Recorder(target())
        bus = Bus(engine, spacing=32)
        bus.start()
        accepted = [bus.write(0xa4), bus.write(0x55), bus.write(0xaa)]
        received = [_host(engine, bus, pop=True) for _ in range(2)]
        _host(engine, bus, 0xa5)
        _host(engine, bus, 0x5a)
        bus.start()
        accepted.append(bus.write(0xa5))
        transmitted = [bus.read(ack=True), bus.read(ack=False)]
        bus.stop()
        expected = {"all_address_and_data_ack": True, "received": [0x55, 0xaa],
                    "transmitted": [0xa5, 0x5a], "released": True}
        observed = {"all_address_and_data_ack": all(accepted), "received": received,
                    "transmitted": transmitted, "released": not engine.active and not engine.last_oe}
        assert observed == expected, (expected, observed)
        return engine, expected, observed, [("SCL resolved", 1), ("SDA resolved", 2)]
    if protocol == "microwire":
        from tools import exchange_decomposition as previous
        previous.Recorder = Recorder
        engine, result = previous.microwire_case()
        expected = {"word": "0xa55a", "dummy_zero": True, "controller_owns_clock": True,
                    "output_event": "rising"}
        observed = {"word": result["observed_word_hex"], "dummy_zero": result["dummy_zero"],
                    "controller_owns_clock": result["clock_owned_by_controller"], "output_event": result["output_event"]}
        assert observed == expected
        return engine, expected, observed, [("CS", 0), ("CLK controller", 1), ("DI", 2), ("DO resolved", 3)]
    if protocol in ("spi", "uart", "timed_stream"):
        cfg = {"spi": lambda: spi.target(), "uart": lambda: uart.receiver(32),
               "timed_stream": lambda: timed_stream.receiver(16)}[protocol]()
        engine = Recorder(cfg)
        wire = Wires(engine)
        if protocol == "spi":
            wire.hold(p0=1, p1=0)
            _host(engine, wire, 0xa6)
            wire.hold(p0=0)
            received = 0
            for i in range(7, -1, -1):
                wire.hold(p2=(0x3c >> i) & 1)
                received = (received << 1) | ((wire.trace[-1]["data"] >> 3) & 1)
                wire.hold(p1=1)
                wire.hold(p1=0)
            wire.hold(p0=1)
            expected = {"target_received": 0x3c, "controller_received": 0xa6, "released": True}
            observed = {"target_received": _host(engine, wire, pop=True),
                        "controller_received": received, "released": not engine.active and not engine.last_oe}
        elif protocol == "uart":
            values = [0x55, 0xa6]
            for value in values:
                wire.uart(value, period=32)
            expected = {"received": values, "released": True}
            observed = {"received": [_host(engine, wire, pop=True) for _ in values], "released": not engine.active}
        else:
            values = [0x55, 0xaa]
            wire.hold(p0=1)
            wire.hold(4, p0=0, p2=1)
            for value in values:
                for i in range(7, -1, -1):
                    wire.hold(16, p2=(value >> i) & 1)
            wire.hold(8, p0=1)
            expected = {"received": values, "released": True}
            observed = {"received": [_host(engine, wire, pop=True) for _ in values], "released": not engine.active}
        assert observed == expected, (protocol, expected, observed)
        pins = [("frame", 0), ("clock", 1), ("RX", 2)]
        if protocol == "spi":
            pins.append(("TX pin input", 3))
        return engine, expected, observed, pins
    raise ValueError(protocol)


def one_wire_cases():
    from tools.v3_trace import Recorder
    from motif.transaction import configuration
    from tools import unseen_protocol as previous
    previous.Recorder = Recorder
    workload = json.loads((ROOT / "experiments/exchange_decomposition/third_workload.json").read_text())
    config_path = ROOT / "experiments/temporal_qualification/configurations/one_wire_reset_presence.json"
    if not config_path.exists():
        raise RuntimeError("The preregistered repaired 1-Wire configuration has not been produced yet")
    config = configuration(json.loads(config_path.read_text()))
    for name in ("nominal", "interrupted_non_reset"):
        case = next(c for c in workload["cases"] if c["name"] == name)
        engine, controller = previous.controller_case(workload, case, config)
        result = previous.oracle(controller, [bool(r["oe"] & 4) for r in engine.rows],
                                 [r["data"] for r in engine.rows], [r["oe"] for r in engine.rows], workload, case)
        assert result["passed"], result["errors"]
        yield name, engine, {"presence_pulses": case["expected_presence"], "wire_oracle_passed": True}, {
            "presence_pulses": len(result["observed_presence_cycles"]), "wire_oracle_passed": result["passed"]}, [("DQ resolved", 2)], {
                "controller_dq": controller, "wire_oracle": result, "case": case}


def cached_rows(directory, sources, stimulus_digest):
    path = directory / "result.json"
    if not path.exists():
        return None
    result = json.loads(path.read_text())
    if result.get("source_hashes") != sources or result.get("stimulus_sha256") != stimulus_digest:
        return None
    if not result.get("model_rtl_agreement"):
        return None
    for name, expected in result.get("artifact_hashes", {}).items():
        candidate = directory / name
        if not candidate.exists() or sha(candidate) != expected:
            return None
    rtl = directory / "rtl.jsonl"
    if not rtl.exists() or "rtl.jsonl" not in result.get("artifact_hashes", {}):
        return None
    return [json.loads(line) for line in rtl.read_text().splitlines()]


def demonstrate(protocol, name, engine, expected, observed, pins, reuse=False, extra=None):
    from tools.v3_trace import compare_rtl, executed_entries
    from tools.demo_render import waveform, timeline
    directory = OUTPUT / protocol / name
    directory.mkdir(parents=True, exist_ok=True)
    sources = identity()
    stimulus_digest = digest(engine.actions)
    rows = cached_rows(directory, sources, stimulus_digest) if reuse else None
    reused = rows is not None
    if rows is None:
        rows = compare_rtl(engine, directory)
    if len(rows) != len(engine.rows):
        raise AssertionError("Incomplete RTL trace")
    # compare_rtl enforces every normalized model/RTL field; wire-level assertions
    # above are independent of PC/entry implementation decisions.
    if extra and "controller_dq" in extra:
        from tools.unseen_protocol import oracle
        workload = json.loads((ROOT / "experiments/exchange_decomposition/third_workload.json").read_text())
        result = oracle(extra["controller_dq"], [bool(r["oe"] & 4) for r in rows],
                        [r["data"] for r in rows], [r["oe"] for r in rows], workload, extra["case"])
        if not result["passed"]:
            raise AssertionError(result["errors"])
    outputs = (engine.config.tx_pin, engine.config.clock_pin) if engine.config.hold_clock else (engine.config.tx_pin,)
    waveform(rows, directory, protocol + "/" + name, pins, outputs=outputs,
             controller=extra.get("controller_dq") if extra else None)
    timeline(rows, directory, protocol + "/" + name, executed_entries)
    interesting = [i for i, r in enumerate(rows) if r.get("events") or r.get("temporal_done")]
    if not interesting:
        interesting = [i for i, r in enumerate(rows) if r.get("motifs")]
    selected = sorted(set([0, max(0, len(rows)-1), *interesting[:12], *interesting[-12:]]))
    excerpts = [{"cycle": i, "pins": rows[i]["pins"], "oe": rows[i]["oe"], "data": rows[i]["data"],
                 "active": rows[i]["active"], "events": rows[i].get("events", 0),
                 "executed_entries": executed_entries(rows[i]), "temporal_count": rows[i].get("temporal_count", 0),
                 "temporal_done": rows[i].get("temporal_done", 0)} for i in selected]
    (directory / "trace_excerpt.json").write_text(json.dumps(excerpts, indent=2) + "\n")
    (directory / "configuration.json").write_text(json.dumps(config_summary(engine.config), indent=2) + "\n")
    result = {"schema_version": 1, "protocol": protocol, "case": name, "cycles": len(rows),
              "expected": expected, "observed": observed, "model_rtl_agreement": True,
              "passed": expected == observed, "source_hashes": sources, "stimulus_sha256": stimulus_digest,
              "rtl_trace_sha256": digest(rows), "configuration": config_summary(engine.config),
              "campaign": campaign_status(), "trace_excerpt": excerpts,
              "cached_artifacts_verified": reused}
    artifacts = [p for p in directory.iterdir() if p.is_file() and p.name not in ("result.json", "README.md")]
    result["artifact_hashes"] = {p.name: sha(p) for p in sorted(artifacts)}
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (directory / "README.md").write_text(
        f"# {protocol}: {name}\n\nPASS: {len(rows):,} cycles of independent model/RTL agreement.\n\n"
        f"Expected: `{json.dumps(expected)}`\n\nObserved: `{json.dumps(observed)}`\n\n"
        "[Configuration](configuration.json), [trace excerpt](trace_excerpt.json), [identified result](result.json).\n\n"
        "![RTL waveform](waveform.svg)\n\n![Actual ordered execution](timeline.svg)\n\n"
        "The timeline uses actual executor observations; idle means no evaluated entry. "
        "Legacy nontransaction modes have no table execution. Full traces and simulation logs remain build artifacts.\n",
        encoding="utf-8")
    print(f"PASS {protocol}/{name}: {len(rows):,} RTL cycles; expected = observed", flush=True)
    for item in excerpts[:4]:
        print(f"  cycle {item['cycle']:6}: pins={item['pins']:02x} oe={item['oe']:02x} "
              f"ordered PCs={item['executed_entries']} temporal={item['temporal_count']} done={item['temporal_done']}")
    return result


def schematics():
    from tools.demo_render import schematic, evolution
    directory = OUTPUT / "architecture"
    directory.mkdir(parents=True, exist_ok=True)
    files = " ".join(p.relative_to(ROOT).as_posix() for p in sorted(ROOT.joinpath("src").glob("*.sv")))
    netlist = directory / "elaborated.json"
    script = f"read_verilog -sv {files}; hierarchy -top tt_um_wellitsabhinav_motif; proc; opt; write_json {netlist.relative_to(ROOT).as_posix()}"
    result = subprocess.run([os.environ.get("YOSYS", "yosys"), "-Q", "-T", "-p", script], cwd=ROOT,
                            capture_output=True, text=True)
    (directory / "yosys.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Schematic elaboration failed; inspect build/demo/architecture/yosys.log")
    modules = json.loads(netlist.read_text())["modules"]
    def find(name):
        matches = [m for n, m in modules.items() if n == name or name in n.split("\\")]
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one elaborated {name}, found {len(matches)}")
        return matches[0]
    schematic(find("tt_um_wellitsabhinav_motif"), directory, "top", "MOTIF working source: top-level modules")
    schematic(find("motif_core"), directory, "architecture", "MOTIF working source: connected core modules")
    schematic(find("motif_transaction"), directory, "temporal", "Temporal qualification register and immediate connected logic", "temporal_count_o")
    schematic(find("motif_transaction"), directory, "transaction", "Transaction program counter and immediate connected logic", "pc_o")
    legacy = json.loads((ROOT / "experiments/generalization/promoted_motif_vocabulary.json").read_text())["source_sha"]
    v2 = json.loads((ROOT / "experiments/exchange_decomposition/frozen_v2_manifest.json").read_text())["source_sha"]
    versions = [("Legacy frozen BYTE_EXCHANGE", legacy), ("Frozen v2", v2)]
    inventories = []
    for label, rev in versions:
        paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", rev, "src"], cwd=ROOT, text=True).splitlines()
        names = []
        for path in paths:
            if path.endswith(".sv"):
                source = subprocess.check_output(["git", "show", rev + ":" + path], cwd=ROOT, text=True)
                names.extend(re.findall(r"\bmodule\s+(\w+)", source))
        full = subprocess.check_output(["git", "rev-parse", rev], cwd=ROOT, text=True).strip()
        inventories.append({"label": label, "identity": full, "modules": sorted(names)})
    inventories.append({"label": "Working v3 (qualification status separate)", "identity": digest(identity()),
                        "modules": sorted(re.findall(r"\bmodule\s+(\w+)", "\n".join(p.read_text() for p in ROOT.joinpath("src").glob("*.sv"))))})
    evolution(inventories, directory)
    (directory / "identity.json").write_text(json.dumps({"source_hashes": identity(), "netlist_sha256": sha(netlist),
        "yosys": result.stdout.splitlines()[:6], "command": script,
        "kind": "elaborated_logic_connectivity", "physical_claim": False}, indent=2) + "\n")
    print("PASS actual Yosys hierarchy and focused schematics", flush=True)


def historical_figures():
    """Render permanent v2 evidence only after matching its committed trace identity."""
    from tools.demo_render import waveform
    report_path = ROOT / "experiments/exchange_decomposition/third_result.json"
    source_report = json.loads(report_path.read_text())
    case = next(c for c in source_report["cases"] if c["name"] == "interrupted_non_reset")
    trace = ROOT / "build/exchange_decomposition/gate3/interrupted_non_reset/rtl.jsonl"
    expected = case["evidence_sha256_lf"]["rtl.jsonl"]
    if not trace.exists():
        print("UNAVAILABLE historical waveform: reproduce the pinned v2 gate-3 trace first", flush=True)
        return
    if sha(trace) != expected:
        raise RuntimeError("Historical v2 RTL trace identity disagrees with its committed evidence")
    rows = []
    with trace.open() as stream:
        for line in stream:
            row = json.loads(line)
            rows.append({key: row[key] for key in ("pins", "data", "oe", "active")})
    workload = json.loads((ROOT / "experiments/exchange_decomposition/third_workload.json").read_text())
    stimulus = next(c for c in workload["cases"] if c["name"] == "interrupted_non_reset")
    controller = [level for level, us in stimulus["segments_us"]
                  for _ in range(us * 1000 // workload["core_period_ns"])]
    if len(controller) != len(rows):
        raise RuntimeError("Historical trace length disagrees with pinned stimulus")
    directory = OUTPUT / "historical/v2_interrupted_low"
    directory.mkdir(parents=True, exist_ok=True)
    waveform(rows, directory, "Historical frozen v2: interrupted-low false presence", [("DQ resolved", 2)],
             outputs=(2,), controller=controller)
    # This historical trace does not observe actual chained PCs or temporal state.
    # These unavailable signals are deliberately absent from the figure.
    result = {"kind": "permanent_historical_counterexample", "classification": source_report["classification"],
              "source_report": report_path.relative_to(ROOT).as_posix(), "source_report_sha256_lf": sha(report_path),
              "rtl_trace_sha256_lf": expected, "oracle": case["oracle"],
              "executed_timeline": "unavailable in historical observation schema"}
    (directory / "identity.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS historical v2 figure: identity verified; original oracle failure preserved", flush=True)


def comparison_figures():
    """Keep the fresh configuration-only audit separate from historical evidence."""
    from tools.demo_render import waveform
    path = ROOT / "experiments/temporal_qualification/v2_composition_baseline.json"
    if not path.exists():
        return
    source = json.loads(path.read_text())
    probes = json.loads((ROOT / "experiments/temporal_qualification/v2_composition_probes.json").read_text())
    reports = {r["name"]: r for r in source["cases"]}
    for probe in probes["cases"]:
        name = probe["name"]
        report_item = reports[name]
        expected = report_item.get("evidence_sha256_lf", {}).get("rtl.jsonl")
        candidates = [ROOT / "build/temporal_baseline" / name / "rtl.jsonl",
                      ROOT / "build/v3_temporal_audit" / name / "rtl.jsonl"]
        trace = next((p for p in candidates if p.exists() and expected and sha(p) == expected), None)
        if trace is None:
            print(f"UNAVAILABLE comparison waveform {name}: identified RTL trace not present", flush=True)
            continue
        rows = []
        with trace.open() as stream:
            for line in stream:
                row = json.loads(line)
                rows.append({key: row[key] for key in ("pins", "data", "oe", "active")})
        controller = [level for level, count in probe["segments_cycles"] for _ in range(count)]
        if len(rows) != len(controller):
            raise RuntimeError("Configuration-only comparison trace length differs from committed probe")
        directory = OUTPUT / "comparison" / name
        directory.mkdir(parents=True, exist_ok=True)
        waveform(rows, directory, "V2 composition comparison: " + name, [("DQ resolved", 2)],
                 outputs=(2,), controller=controller)
        result = {"kind": "new_configuration_only_comparison", "source_commit": source["source_commit"],
                  "report_sha256_lf": sha(path), "rtl_trace_sha256_lf": expected,
                  "oracle": report_item["oracle"], "responsibility": probe["responsibility"],
                  "interpretation": "Bounded comparison evidence; historical classification remains unchanged"}
        (directory / "identity.json").write_text(json.dumps(result, indent=2) + "\n")
        print(f"PASS comparison figure {name}: original negative oracle preserved", flush=True)


def publish_figures(results):
    """Copy only selected reviewable figures and short evidence, never full traces."""
    destination = ROOT / "docs/demo/figures"
    destination.mkdir(parents=True, exist_ok=True)
    copied = {}
    candidates = []
    for item in results:
        directory = OUTPUT / item["protocol"] / item["case"]
        candidates += [p for p in directory.iterdir()
                       if p.suffix in (".svg", ".png") or p.name in ("configuration.json", "trace_excerpt.json")]
    for group in ("architecture", "historical", "comparison"):
        root = OUTPUT / group
        if root.exists():
            candidates += [p for p in root.rglob("*") if p.is_file() and
                           (p.suffix in (".svg", ".png") or p.name in
                            ("identity.json", "evolution.json", "top.json", "architecture.json", "temporal.json", "transaction.json"))]
    for source in candidates:
        relative = source.relative_to(OUTPUT)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied[relative.as_posix()] = sha(target)
    concise = {"schema_version": 1, "source_hashes": identity(), "campaign": campaign_status(),
        "demonstrations": [{key: item[key] for key in ("protocol", "case", "cycles", "expected", "observed",
            "model_rtl_agreement", "passed", "stimulus_sha256", "rtl_trace_sha256")} for item in results],
        "selected_artifact_sha256": copied,
        "hash_convention": "Text CRLF normalized to LF; raster image bytes hashed without normalization",
        "full_artifacts": "Reproduce with python -m tools.demo --all --schematics; generated under build/demo"}
    (destination.parent / "demonstrations.json").write_text(json.dumps(concise, indent=2) + "\n")
    print(f"Published {len(copied)} selected figures and short evidence under docs/demo", flush=True)


def unseen_demonstrations():
    """Consume late independent evidence without selecting a workload or changing semantics."""
    from motif.transaction import configuration
    from tools.v3_inventory import verify, MANIFEST
    from tools.v3_trace import FIELDS, executed_entries
    from tools.demo_render import waveform, timeline
    before = verify()
    input_directory = ROOT / "experiments/temporal_qualification/unseen"
    result_path, config_path = input_directory / "result.json", input_directory / "config.json"
    qualified = json.loads(result_path.read_text())
    if qualified.get("passed") is not True or qualified.get("frozen_before_after_identical") is not True:
        raise RuntimeError("Unseen qualification did not pass; its failure remains campaign evidence")
    if qualified.get("frozen_manifest_sha256_lf") != sha(ROOT / MANIFEST):
        raise RuntimeError("Unseen evidence identifies another semantic freeze")
    descriptions = qualified.get("demonstrations", [])
    if not descriptions:
        raise RuntimeError("Unseen qualification supplied no identified demonstration traces")
    common_config = json.loads(config_path.read_text())
    outputs = []
    for item in descriptions:
        name = item.get("name", "")
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]{0,79}", name):
            raise RuntimeError("Unseen demonstration name must be a bounded filename component")
        if item.get("oracle", {}).get("passed") is not True or item.get("expected") != item.get("observed"):
            raise RuntimeError(f"Unseen independent oracle failed: {name}")
        trace_directory = (ROOT / item["trace_directory"]).resolve()
        trace_directory.relative_to((ROOT / "build").resolve())
        hashes = item.get("evidence_sha256_lf", {})
        required = ("inputs.txt", "model.jsonl", "rtl.jsonl", "simulation.log")
        for filename in required:
            path = trace_directory / filename
            if not hashes.get(filename) or not path.is_file() or sha(path) != hashes[filename]:
                raise RuntimeError(f"Unseen {name} artifact identity differs: {filename}")
        rows = [json.loads(line) for line in (trace_directory / "rtl.jsonl").read_text().splitlines()]
        expected_rows = [json.loads(line) for line in (trace_directory / "model.jsonl").read_text().splitlines()]
        if not rows or len(rows) != len(expected_rows) or any(
                any(expected[field] != actual[field] for field in FIELDS)
                for expected, actual in zip(expected_rows, rows)):
            raise RuntimeError(f"Unseen {name} complete model/RTL comparison failed")
        cfg = configuration(item.get("configuration", common_config))
        directory = OUTPUT / "unseen" / name
        directory.mkdir(parents=True, exist_ok=True)
        pins = item.get("pins", [["frame input", cfg.frame_pin], ["clock input", cfg.clock_pin], ["RX input", cfg.rx_pin]])
        if any(not isinstance(label, str) or type(pin) is not int or not 0 <= pin < 8 for label, pin in pins):
            raise RuntimeError("Unseen plot pin labels must identify actual eight-pin inputs")
        waveform(rows, directory, "Frozen v3 unseen / " + name, pins, outputs=(cfg.tx_pin,))
        timeline(rows, directory, "Frozen v3 unseen / " + name, executed_entries)
        for filename in required:
            shutil.copyfile(trace_directory / filename, directory / filename)
        indices = sorted(set([0, len(rows) - 1, *[i for i, row in enumerate(rows) if row["events"]][:12]]))
        excerpt = [{"cycle": i, "pins": rows[i]["pins"], "oe": rows[i]["oe"], "data": rows[i]["data"],
                    "executed_entries": executed_entries(rows[i]), "temporal_count": rows[i]["temporal_count"]} for i in indices]
        (directory / "configuration.json").write_text(json.dumps(config_summary(cfg), indent=2) + "\n")
        (directory / "trace_excerpt.json").write_text(json.dumps(excerpt, indent=2) + "\n")
        output = {"schema_version": 1, "protocol": "unseen", "case": name, "cycles": len(rows),
                  "expected": item["expected"], "observed": item["observed"], "oracle": item["oracle"],
                  "model_rtl_agreement": True, "passed": True, "source_hashes": identity(),
                  "stimulus_sha256": hashes["inputs.txt"], "rtl_trace_sha256": digest(rows),
                  "configuration": config_summary(cfg), "trace_excerpt": excerpt, "campaign": campaign_status(),
                  "late_input_hashes_lf": {result_path.relative_to(ROOT).as_posix(): sha(result_path),
                                           config_path.relative_to(ROOT).as_posix(): sha(config_path)},
                  "artifact_hashes": hashes, "frozen_manifest_sha256_lf": sha(ROOT / MANIFEST)}
        (directory / "result.json").write_text(json.dumps(output, indent=2) + "\n")
        (directory / "README.md").write_text(f"# Unseen: {name}\n\nPASS: {len(rows):,} complete model/RTL cycles. "
            "Independent post-freeze oracle and input artifact identities were verified.\n\n"
            "[Result](result.json), [configuration](configuration.json), [excerpt](trace_excerpt.json).\n\n"
            "![RTL waveform](waveform.svg)\n\n![Ordered executor observations](timeline.svg)\n")
        outputs.append(output)
        print(f"PASS unseen/{name}: {len(rows):,} identified post-freeze RTL cycles", flush=True)
    if verify() != before:
        raise RuntimeError("Frozen semantic manifest changed while rendering unseen evidence")
    return outputs


def _report_html(text, source_directory):
    """Render report paragraphs with clickable evidence links without a web dependency."""
    def inline(value):
        escaped = html.escape(value)
        def link(match):
            target = html.unescape(match.group(2))
            if not re.match(r"^(?:https?://|#)", target):
                path = (source_directory / target).resolve()
                try:
                    path.relative_to(ROOT)
                except ValueError:
                    return match.group(0)
                target = os.path.relpath(path, OUTPUT).replace("\\", "/")
            return f"<a href='{html.escape(target, quote=True)}'>{match.group(1)}</a>"
        escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, escaped)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    output, fenced = [], False
    for block in re.split(r"\n\s*\n", text):
        if block.startswith("```"):
            output.append("<pre>" + html.escape(block.strip("`")) + "</pre>")
        elif block.startswith("#"):
            level = min(4, len(block) - len(block.lstrip("#")))
            output.append(f"<h{level}>" + inline(block.lstrip("# ")) + f"</h{level}>")
        elif all(line.startswith(("- ", "* ")) for line in block.splitlines()):
            output.append("<ul>" + "".join("<li>" + inline(line[2:]) + "</li>" for line in block.splitlines()) + "</ul>")
        else:
            output.append("<p>" + inline(block).replace("\n", "<br>") + "</p>")
    return output


def report(results):
    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>MOTIF demonstrations</title>",
             "<style>body{max-width:1100px;margin:40px auto;padding:0 22px;font:16px/1.5 system-ui;color:#172b39}"
             "img{max-width:100%}pre{white-space:pre-wrap;background:#eef3f7;padding:14px}"
             "table{border-collapse:collapse}td,th{padding:8px 12px;border:1px solid #cad6df}"
             "a{color:#205b8f}.status{background:#fff2cf;padding:15px}</style>",
             "<h1>MOTIF: reproducible protocol demonstrations</h1>",
             f"<p class='status'>Campaign: {html.escape(campaign_status()['status'])}. "
             "Demonstrations establish only the recorded bounded behavior and model/RTL agreement. "
             "Mapped cost, unseen generalization and physical closure are separate gates.</p>",
             "<p>Every waveform uses real RTL observations. Execution lanes use the actual ordered PCs "
             "observed inside the bounded executor. SVG files remain editable; full traces stay in build/demo.</p>",
             "<table><tr><th>Protocol/case</th><th>Cycles</th><th>Result</th><th>Evidence</th></tr>"]
    for item in results:
        base = item["protocol"] + "/" + item["case"]
        parts.append(f"<tr><td>{html.escape(base)}</td><td>{item['cycles']:,}</td><td>PASS</td>"
                     f"<td><a href='{base}/result.json'>Result and identities</a></td></tr>")
    parts.append("</table>")
    for item in results:
        base = item["protocol"] + "/" + item["case"]
        parts.extend([f"<h2>{html.escape(base)}</h2>",
            "<p>Expected and observed: " + html.escape(json.dumps(item["observed"])) + "</p>",
            f"<p><a href='{base}/configuration.json'>Configuration</a> · "
            f"<a href='{base}/trace_excerpt.json'>Trace excerpt</a> · "
            f"<a href='{base}/simulation.log'>Simulation log</a></p>",
            f"<img alt='Real RTL waveform' src='{base}/waveform.svg'>",
            f"<img alt='Actual ordered executor entries' src='{base}/timeline.svg'>"])
    if (OUTPUT / "architecture/architecture.svg").exists():
        parts.append("<h2>Actual elaborated structure</h2><p>These are Yosys-derived connectivity views. "
                     "They are unrelated to placement or routing.</p>")
        for name in ("architecture", "top", "transaction", "temporal", "evolution"):
            parts.append(f"<p><a href='architecture/{name}.json'>Editable evidence for {name}</a></p>"
                         f"<img alt='{name}' src='architecture/{name}.svg'>")
    comparison = OUTPUT / "comparison"
    if comparison.exists():
        parts.append("<h2>Fresh v2 configuration-only comparison</h2><p>The candidate passes the nine original "
                     "bounded cases and fails added persistence/restart/timing probes. This does not replace historical results "
                     "or establish configuration impossibility.</p>")
        for item in sorted(comparison.glob("*/identity.json")):
            base = item.parent.relative_to(OUTPUT).as_posix()
            parts.append(f"<p><a href='{base}/identity.json'>{html.escape(item.parent.name)} comparison identity</a></p>"
                         f"<img alt='Identified v2 composition comparison' src='{base}/waveform.svg'>")
    historical = ROOT / "experiments/exchange_decomposition/third_counterexample.json"
    if historical.exists():
        old = json.loads(historical.read_text())
        parts.append("<h2>Permanent historical failure</h2><p>The frozen v2 interrupted-low counterexample "
                     "is preserved unchanged. It is comparison evidence, not a v3 failure waveform.</p>"
                     "<pre>" + html.escape(json.dumps(old, indent=2)) + "</pre>")
        if (OUTPUT / "historical/v2_interrupted_low/waveform.svg").exists():
            parts.append("<p><a href='historical/v2_interrupted_low/identity.json'>Verified historical trace identity</a></p>"
                         "<img alt='Historical v2 interrupted-low false presence, not v3' "
                         "src='historical/v2_interrupted_low/waveform.svg'>")
    final_report = ROOT / "docs/research/v3_temporal_qualification/final_report.md"
    if final_report.exists():
        parts.append("<h2>Campaign A–Z report</h2><p>" 
                     "<a href='../../docs/research/v3_temporal_qualification/final_report.md'>Editable report and evidence links</a></p>")
        parts.extend(_report_html(final_report.read_text(encoding="utf-8"), final_report.parent))
    parts.append("</html>")
    (OUTPUT / "index.html").write_text("\n".join(parts) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    protocols = (*PROTOCOLS, "unseen") if (ROOT / "experiments/temporal_qualification/unseen/result.json").exists() else PROTOCOLS
    group.add_argument("--protocol", choices=protocols)
    group.add_argument("--all", action="store_true")
    parser.add_argument("--reuse", action="store_true", help="Reuse only traces with matching source, stimulus and artifact hashes")
    parser.add_argument("--schematics", action="store_true", help="Also elaborate actual Yosys connectivity views")
    parser.add_argument("--publish-figures", action="store_true", help="Copy selected figures and concise evidence to docs/demo")
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    frozen_before = None
    if (ROOT / "experiments/temporal_qualification/frozen_v3_manifest.json").exists():
        from tools.v3_inventory import verify
        try:
            frozen_before = verify()
        except Exception as exc:
            print(f"FAIL frozen source verification: {exc}", file=sys.stderr)
            return 1
    results, failures = [], []
    for protocol in protocols if args.all else (args.protocol,):
        try:
            if protocol == "unseen":
                results.extend(unseen_demonstrations())
            elif protocol == "one_wire":
                for name, engine, expected, observed, pins, extra in one_wire_cases():
                    results.append(demonstrate(protocol, name, engine, expected, observed, pins, args.reuse, extra))
            else:
                engine, expected, observed, pins = build_case(protocol)
                results.append(demonstrate(protocol, "bounded", engine, expected, observed, pins, args.reuse))
        except Exception as exc:
            failures.append({"protocol": protocol, "error": str(exc)})
            print(f"FAIL {protocol}: {exc}", file=sys.stderr, flush=True)
    if args.schematics:
        try:
            schematics()
        except Exception as exc:
            failures.append({"protocol": "schematics", "error": str(exc)})
            print(f"FAIL schematics: {exc}", file=sys.stderr)
    if args.all or args.protocol == "one_wire":
        try:
            historical_figures()
            comparison_figures()
        except Exception as exc:
            failures.append({"protocol": "historical_figure", "error": str(exc)})
            print(f"FAIL historical figure: {exc}", file=sys.stderr)
    if frozen_before is not None:
        try:
            if verify() != frozen_before:
                raise RuntimeError("Frozen manifest changed during demonstrations")
        except Exception as exc:
            failures.append({"protocol": "frozen_source_verification", "error": str(exc)})
            print(f"FAIL frozen source verification: {exc}", file=sys.stderr)
    report(results)
    if args.publish_figures and not failures:
        publish_figures(results)
    (OUTPUT / "result.json").write_text(json.dumps({"campaign": campaign_status(), "passed": not failures,
        "demonstrations": [{"protocol": r["protocol"], "case": r["case"], "passed": r["passed"]} for r in results],
        "failures": failures}, indent=2) + "\n")
    print("HTML: build/demo/index.html", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
