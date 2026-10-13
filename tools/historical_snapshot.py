"""Replay the immutable v2 campaign in a plain archived source tree."""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

V2_SNAPSHOT = "490a50c"
ROOT = Path(__file__).resolve().parents[1]
ALLOWED_MODULES = {"tools.exchange_decomposition", "tools.generalization", "tools.unseen_result", "tools.synthesis", "tools.frozen_manifest"}


def prepare():
    identity = subprocess.check_output(["git", "rev-parse", V2_SNAPSHOT], cwd=ROOT, text=True).strip()
    destination = ROOT / "build" / "historical" / "v2" / identity
    destination.mkdir(parents=True, exist_ok=True)
    archive = subprocess.check_output(["git", "archive", "--format=tar", identity], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(destination, filter="data")
    runner = destination / "_historical_runner.py"
    runner.write_text('''import os, runpy, subprocess, sys
original = subprocess.check_output
source_root = os.path.abspath(os.getcwd())
def pinned_revision(command, *args, **kwargs):
    directory = os.path.abspath(kwargs.get("cwd", os.getcwd()))
    if list(command) == ["git", "rev-parse", "HEAD"] and directory == source_root:
        value = os.environ["MOTIF_HISTORICAL_SOURCE_SHA"] + "\\n"
        return value if kwargs.get("text") or kwargs.get("universal_newlines") else value.encode()
    if list(command) == ["git", "rev-parse", "--git-path", "objects"] and directory == source_root:
        live = os.environ["MOTIF_HISTORICAL_LIVE_REPOSITORY"]
        return original(["git", "-C", live, "rev-parse", "--path-format=absolute", "--git-path", "objects"], *args, **kwargs)
    if command[0] == "git" and directory == source_root:
        return original(["git", "-C", os.environ["MOTIF_HISTORICAL_LIVE_REPOSITORY"], *command[1:]], *args, **kwargs)
    return original(command, *args, **kwargs)
subprocess.check_output = pinned_revision
module = sys.argv[1]
sys.argv = [module, *sys.argv[2:]]
runpy.run_module(module, run_name="__main__")
''', encoding="utf-8", newline="\n")
    return destination, identity


def execute(module, arguments=()):
    if module not in ALLOWED_MODULES:
        raise ValueError("Unsupported historical reproduction module")
    destination, identity = prepare()
    environment = os.environ.copy()
    environment["MOTIF_HISTORICAL_SOURCE_SHA"] = identity
    environment["MOTIF_HISTORICAL_LIVE_REPOSITORY"] = str(ROOT)
    if environment.get("IVERILOG_BASE"):
        base = Path(environment["IVERILOG_BASE"])
        if not base.is_absolute():
            base = ROOT / base
        environment["IVERILOG_BASE"] = os.path.relpath(base.resolve(), destination)
    if environment.get("YOSYS_ABC"):
        abc = Path(environment["YOSYS_ABC"])
        if not abc.is_absolute():
            abc = ROOT / abc
        environment["YOSYS_ABC"] = os.path.relpath(abc.resolve(), destination)
    subprocess.run([sys.executable, "_historical_runner.py", module, *map(str, arguments)],
                   cwd=destination, env=environment, check=True)
    return destination, identity


def run(gate, output=None, synthesize=False):
    result_path = Path(output).resolve() if output else ROOT / "build" / "historical" / "v2" / f"gate{gate}" / "result.json"
    command = ["--gate", str(gate), "--baseline", "v2", "--output", str(result_path)]
    if synthesize:
        command.append("--synthesize")
    execute("tools.generalization", command)
    if gate == 3:
        execute("tools.unseen_result", ["--result", result_path])
    result = json.loads(result_path.read_text())
    frozen = json.loads((ROOT / "experiments/exchange_decomposition/frozen_v2_manifest.json").read_text())
    hashes = result.get("frozen_source_hashes")
    if hashes is not None and hashes != frozen["source_hashes"]:
        raise AssertionError("Historical replay used another frozen implementation")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=int, choices=(1, 2, 3))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-freeze", action="store_true")
    parser.add_argument("--check-preregistration", action="store_true")
    parser.add_argument("--synthesis", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("build/historical/v2/synthesis"))
    args = parser.parse_args()
    if args.gate:
        run(args.gate, args.output)
    elif args.synthesis:
        execute("tools.synthesis", ["--cmos5l", "--output-dir", args.output_dir.resolve()])
    else:
        execute("tools.exchange_decomposition", ["--check-preregistration" if args.check_preregistration else "--check-freeze"])
        print("PASS immutable historical v2 snapshot", V2_SNAPSHOT)


if __name__ == "__main__":
    main()
