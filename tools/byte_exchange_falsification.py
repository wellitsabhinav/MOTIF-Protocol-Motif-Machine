"""A fixed independent Microwire oracle against the frozen existing interface."""
import json
import platform
import subprocess
from dataclasses import asdict, replace
from pathlib import Path

from motif import Config
from motif.protocols.i2c import target
from tools.frozen_manifest import PROMOTED, digest, inventory, verify


def oracle(address, word):
    # Published x16 READ command: start, opcode 10, six address bits.
    # The dummy zero is at the final address clock, followed by 16 data clocks.
    if not 0 <= address < 64 or not 0 <= word < 65536:
        raise ValueError("Outside the bounded Microwire oracle")
    return ([1, 1, 0] + [(address >> i) & 1 for i in range(5, -1, -1)],
            [(word >> i) & 1 for i in range(15, -1, -1)])


def run(destination):
    from tools.generalization import Recorder, bench, simulate, stable_hash, write_trace
    frozen = verify(PROMOTED)
    physical = json.loads(Path("experiments/generalization/gate1_physical.json").read_text())
    if any(value != "success" for value in physical["checks"].values()):
        raise ValueError("Gate 1 physical qualification incomplete")
    workload_path = Path("experiments/generalization/microwire_workload.json")
    workload = json.loads(workload_path.read_text())
    command, expected_bits = oracle(workload["memory_address"], workload["response_word"])
    result = {"schema_version": 1, "gate": 2, "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "frozen_source_sha": frozen["source_sha"], "manifest_sha256": digest(PROMOTED.read_bytes()),
              "source_hashes": inventory(), "workload_sha256": digest(workload_path.read_bytes()), "python": platform.python_version(),
              "oracle": {"command_bits": command, "response_bits": expected_bits, "word_hex": hex(workload["response_word"])},
              "new_rtl": False, "existing_rtl_modified": False, "configuration_rejections": [], "attempts": [],
              "scope": "Existing configuration interface; diagnostic relaxations are not compliant implementations"}
    try:
        Config(exchange=True, rx_pin=2, tx_pin=3, clock_pin=1, open_drain=6)
    except ValueError as exc:
        result["configuration_rejections"].append({"request": "Separate Microwire DI and DO", "reason": str(exc)})
    else:
        raise AssertionError("Frozen exchange unexpectedly accepted separate DI/DO")

    for mode in ("level", "falling", "two_wire"):
        for lsb in (False, True):
            # Match the first eight captured command bits as favorably as possible.
            # In LSB mode C0 becomes 03, permitting the frozen bit-zero TX role.
            first_word = 3 if lsb else 0xc0
            cfg = replace(target(setup_cycles=13), frame=mode, lsb_first=lsb, address=first_word >> 1)
            engine = Recorder(cfg)
            cs, clock, data = 0, 0, 1
            sample_indices = []

            def hold(cycles=32, new_cs=None, new_clock=None, new_data=None):
                nonlocal cs, clock, data
                if new_cs is not None: cs = new_cs
                if new_clock is not None: clock = new_clock
                if new_data is not None: data = new_data
                for _ in range(cycles):
                    oe = engine.last_oe
                    pins = 248 | cs | ((clock and not (oe & 2)) << 1) | ((data and not (oe & 4)) << 2)
                    engine.step(pins)

            hold(16)
            for value in (workload["response_word"] >> 8, workload["response_word"] & 255):
                engine.host_push, engine.host_data = True, value
                hold(1)
            hold(new_cs=1)
            for i, bit in enumerate(command):
                hold(new_clock=0, new_data=bit)
                hold(new_clock=1)
                hold(new_clock=0, new_data=1 if i == 8 else bit)
            for _ in expected_bits:
                hold(new_clock=1, new_data=1)
                sample_indices.append(len(engine.rows) - 1)
                hold(new_clock=0)
            hold(new_cs=0)
            name = f"microwire_{mode}_{int(lsb)}"
            directory = Path("build/generalization/gate2") / name
            directory.mkdir(parents=True, exist_ok=True)
            vectors = directory / "inputs.txt"
            vectors.write_text("".join(" ".join(map(str, a)) + "\n" for a in engine.actions), encoding="utf-8")
            actual = simulate(bench(cfg, vectors, len(engine.rows)), directory)
            if actual != engine.rows:
                for cycle, pair in enumerate(zip(engine.rows, actual)):
                    if pair[0] != pair[1]: raise AssertionError(f"Gate 2 model/RTL divergence {name} cycle {cycle}: {pair}")
                raise AssertionError("Incomplete diagnostic trace")
            write_trace(directory / "model.jsonl", engine.rows)
            write_trace(directory / "rtl.jsonl", actual)
            observed_bits = [int(not (actual[i]["oe"] & 4)) for i in sample_indices]
            observed_word = sum(bit << (15 - i) for i, bit in enumerate(observed_bits))
            assert observed_bits != expected_bits, "Unexpected candidate success: review rather than preclassify"
            first_mismatch = next(i for i, pair in enumerate(zip(expected_bits, observed_bits)) if pair[0] != pair[1])
            result["attempts"].append({"name": name, "configuration": asdict(cfg), "configuration_sha256": stable_hash(asdict(cfg)),
                "controller_half_phase_cycles": 32, "host_preload_only": True, "cycles": len(actual), "trace_sha256": stable_hash(actual),
                "expected_word_hex": hex(workload["response_word"]), "observed_word_hex": hex(observed_word),
                "first_mismatched_response_bit": first_mismatch,
                "counterexample": {"expected_bit": expected_bits[first_mismatch], "observed_bit": observed_bits[first_mismatch],
                                   "rtl_row": actual[sample_indices[first_mismatch]]},
                "clock_oe_cycles": sum(bool(row["oe"] & 2) for row in actual), "model_rtl_agreement": True, "protocol_passed": False})
            print("CONFIRMED counterexample", name, hex(observed_word), "expected", hex(workload["response_word"]), flush=True)
    closest = next(a for a in result["attempts"] if a["name"] == "microwire_falling_1")
    assert closest["observed_word_hex"] == "0xa5ff"
    assert closest["first_mismatched_response_bit"] == 8
    assert closest["counterexample"]["rtl_row"]["phase"] == 5
    result.update(classification="MOTIF_BYTE_EXCHANGE_PROTOCOL_SPECIFIC", source_audit_category="C: protocol-specific macro",
                  decisive_failure="After eight transmitted bits, frozen RTL unconditionally enters CONTROLLER_ACK and releases data. Microwire requires the next data bit without a ninth-clock acknowledgement; expected D7=0 is observed as released 1.",
                  boundary_verified_after_experiment=bool(verify(PROMOTED)),
                  gate3={"status": "UNATTEMPTED", "reason": "Campaign stop condition: demonstrated Gate 2 failure"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
