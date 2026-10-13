"""Deterministic wire-level temporal probes with independently specified markers."""
from motif import Config
from motif.transaction import Entry, program, temporal_wait, delay_wait, RESPOND, HALT, CONTINUE, CHAIN
from tools.v3_trace import Recorder


def probe(name, bits, threshold=4, level=0, policy="restart", delay=False,
          expected_match_start=None, lifecycle=None):
    entry = delay_wait(threshold, next=1, chain=True) if delay else temporal_wait(
        level, threshold, policy, next=1, alternate=2, chain=True)
    cfg = Config(frame="level", transmit=False, watchdog=4 if lifecycle == "watchdog" else 0,
                 program=program([entry, Entry(RESPOND, next=3, value=0), Entry(HALT), Entry(HALT, flags=2)]))
    engine = Recorder(cfg)
    samples = [(1, 1, False)] * 8 + [(0, bit, False) for bit in bits]
    markers = []
    if expected_match_start is not None:
        markers = [[8 + expected_match_start + 2 + threshold, len(samples)]]
    reset_cycles, abort_cycles, disabled_cycles = set(), set(), set()
    if lifecycle:
        # A partial first epoch is cancelled. A short second epoch must not
        # inherit its progress; the third independently valid epoch must work.
        samples = [(1, 1, False)] * 8 + [(0, level, False)] * (2 if lifecycle != "watchdog" else 12)
        event = 11
        if lifecycle == "reset": reset_cycles.add(event)
        if lifecycle == "abort": abort_cycles.add(event)
        if lifecycle == "disable": disabled_cycles.add(event)
        if lifecycle not in ("watchdog", "release"):
            samples += [(0, 1-level, False)] * 8
        samples += [(1, 1, False)] * 10
        samples += [(0, level, lifecycle == "watchdog")] * (threshold-1)
        samples += [(0, 1-level, lifecycle == "watchdog")] * 4
        samples += [(1, 1, False)] * 10
        valid_start = len(samples)
        samples += [(0, level, lifecycle == "watchdog")] * (threshold+8)
        markers = [[valid_start + 2 + threshold, len(samples)]]
    samples += [(1, 1, False)] * 8
    for cycle, (frame, bit, progress) in enumerate(samples):
        engine.enabled = cycle not in disabled_cycles
        pins = 255
        if not frame: pins &= ~1
        if not bit: pins &= ~4
        if progress and cycle % 2: pins &= ~2
        engine.step(pins, reset=cycle in reset_cycles, abort=cycle in abort_cycles)
    return name, engine, {"marker_intervals": markers, "marker_pin": 3,
                           "basis": "Declared external sample runs, two-cycle frontend and registered completion; no PC/qualification-state oracle"}


def cases():
    for level in (0, 1):
        other = 1-level
        for threshold in (1, 2, 4, 16, 65535):
            for delta in (-1, 0, 1):
                length = threshold + delta
                bits = [level] * length + [other] * 8
                yield probe(f"level{level}_t{threshold}_delta{delta}", bits, threshold, level,
                            expected_match_start=0 if length >= threshold else None)
        for gap_start in (1, 2, 3):
            bits = [level]*gap_start + [other] + [level]*4 + [other]*8
            yield probe(f"level{level}_interrupt{gap_start}_restart", bits, level=level,
                        expected_match_start=gap_start+1)
            yield probe(f"level{level}_interrupt{gap_start}_branch", bits, level=level, policy="branch")
        yield probe(f"level{level}_multiple_interruptions", [level, other, level, level, other]+[level]*4+[other]*8,
                    level=level, expected_match_start=5)
        yield probe(f"level{level}_long_idle", [other]*100+[level]*4+[other]*8,
                    level=level, expected_match_start=100)
    yield probe("constant_delay", [0, 1]*8, delay=True, expected_match_start=0)
    for lifecycle in ("reset", "abort", "disable", "watchdog", "release"):
        yield probe("lifecycle_"+lifecycle, [], threshold=8, lifecycle=lifecycle)
    for bridges in (0, 3):
        entries = [delay_wait(1, next=1, chain=True)]
        entries += [Entry(CONTINUE, next=i+2, flags=CHAIN) for i in range(bridges)]
        entries += [delay_wait(1, next=bridges+2, chain=True), Entry(RESPOND, next=bridges+3), Entry(HALT, flags=2)]
        engine = Recorder(Config(frame="level", transmit=False, program=program(entries)))
        for cycle in range(28):
            engine.step(255 if cycle < 8 or cycle >= 24 else 254)
        yield f"chained_qualifications_bridges{bridges}", engine, {"marker_intervals": [[13, 24]], "marker_pin": 3,
            "basis": "Two registered qualifications separated by the mandatory second-entry deferral; first acquisition raw8+frontend2, marker at13"}
    yield timer_end_acquisition_case()


def timer_end_acquisition_case():
    """Validation end and repeated acquisition coincide at observation cycle29."""
    engine = Recorder(Config(
        frame="two_wire", sample="timer", period=2, validate_stop=True,
        transmit=False, rx_pin=2, tx_pin=2, open_drain=4,
        program=program([delay_wait(100, next=1, chain=True),
                         Entry(RESPOND, next=2, value=0), Entry(HALT, flags=2)])))
    for cycle in range(40):
        pins = 255
        if cycle == 8 or cycle >= 27:
            pins &= ~4
        if cycle in (9, 10):
            pins &= ~2
        engine.step(pins)
    return "registered_timer_end_precedes_repeated_acquisition", engine, {
        "marker_intervals": [], "marker_pin": 2,
        "basis": "First acquisition observes rawDQfall8 at10; 2-cycle timer validates stop at28. Registered validation end overrides the repeated acquisition at29, cancelling the partial100-observation qualification before it can emit a marker.",
    }


def verify_expected(rows, expectation):
    pin = 1 << expectation["marker_pin"]
    observed, start = [], None
    for cycle, row in enumerate([*rows, {"oe": 0}]):
        low = bool(row["oe"] & pin)
        if low and start is None: start = cycle
        if not low and start is not None:
            observed.append([start, cycle]); start = None
    errors = []
    if observed != expectation["marker_intervals"]:
        errors.append(f"Expected marker intervals {expectation['marker_intervals']}, observed {observed}")
    if any(row["oe"] & ~pin or row["oe"] & row["data"] & pin for row in rows):
        errors.append("Illegal output ownership or high marker drive")
    return {"passed": not errors, "errors": errors, "expected": expectation,
            "observed_marker_intervals": observed}


if __name__ == "__main__":
    for name, engine, expectation in cases():
        result = verify_expected(engine.rows, expectation)
        print(("PASS" if result["passed"] else "FAIL"), name, result["errors"], flush=True)
        if not result["passed"]: raise SystemExit(1)
