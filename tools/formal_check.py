import os
import subprocess
from pathlib import Path


def run():
    directory = Path("build/formal")
    directory.mkdir(parents=True, exist_ok=True)
    executable = os.environ.get("YOSYS", "yosys")
    help_result = subprocess.run([executable, "-Q", "-T", "-p", "help chformal"], capture_output=True, text=True, check=True)
    # New frontends retain posedge assertions as triggered $check cells.
    # async2sync registers their original enable/predicate on the same edge,
    # matching the older frontend's $assert representation. The DUT and all
    # properties remain unchanged; no clocks are removed and no checks skipped.
    # See Yosys passes/sat/async2sync.cc (single-edge $check conversion).
    lower = "async2sync; chformal -lower; " if "-lower" in help_result.stdout else ""
    cases = {
        "guardian": "read_verilog -formal -sv src/motif_pad_guardian.sv formal/guardian.sv; prep -top guardian_properties; flatten; sat -prove-asserts -verify",
        "watchdog": "read_verilog -formal -sv src/motif_watchdog.sv formal/watchdog.sv; prep -top watchdog_properties; flatten; sat -seq 24 -set-init-zero -set-assumes -prove-asserts -verify",
    }
    for threshold in range(1,5):
        cases[f"temporal_{threshold}"] = (
            "read_verilog -formal -sv src/motif_transaction.sv formal/temporal.sv; "
            f"chparam -set THRESHOLD {threshold} temporal_properties; prep -top temporal_properties; "
            "flatten; sat -seq 12 -set-init-zero -prove-asserts -verify")
    for name, script in cases.items():
        script = script.replace("flatten; sat", "flatten; " + lower + "sat")
        result = subprocess.run([executable, "-Q", "-T", "-p", script], capture_output=True, text=True)
        (directory / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode or "SUCCESS" not in result.stdout:
            print((result.stdout + result.stderr)[-4000:])
            raise RuntimeError(name + " formal check failed; inspect build/formal")
        print("PASS", name, "unrestricted combinational proof" if name == "guardian" else
              "12-step temporal safety proof" if name.startswith("temporal_") else "24-step bounded proof, limits 1..15")


if __name__ == "__main__":
    run()
