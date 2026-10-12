import os
import subprocess
from pathlib import Path


def run():
    directory = Path("build/formal")
    directory.mkdir(parents=True, exist_ok=True)
    cases = {
        "guardian": "read_verilog -formal -sv src/motif_pad_guardian.sv formal/guardian.sv; prep -top guardian_properties; flatten; sat -prove-asserts -verify",
        "watchdog": "read_verilog -formal -sv src/motif_watchdog.sv formal/watchdog.sv; prep -top watchdog_properties; flatten; sat -seq 24 -set-init-zero -set-assumes -prove-asserts -verify",
    }
    for name, script in cases.items():
        result = subprocess.run([os.environ.get("YOSYS", "yosys"), "-Q", "-T", "-p", script], capture_output=True, text=True)
        (directory / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode or "SUCCESS" not in result.stdout:
            raise RuntimeError(name + " formal check failed; inspect build/formal")
        print("PASS", name, "unrestricted combinational proof" if name == "guardian" else "24-step bounded proof, limits 1..15")


if __name__ == "__main__":
    run()
