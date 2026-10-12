"""Execute permanent evidence in an isolated, pinned historical checkout."""
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

SNAPSHOT = "7a74a1772dd178e498228667b54ec6a2fd39373a"


def run(gate, output=None, synthesize=False):
    root = Path(__file__).resolve().parents[1]
    destination = root / "build" / "legacy" / SNAPSHOT
    destination.mkdir(parents=True, exist_ok=True)
    archive = subprocess.check_output(["git", "archive", "--format=tar", SNAPSHOT], cwd=root)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(destination, filter="data")
    subprocess.run(["git", "init", "--quiet", str(destination)], check=True)
    objects = subprocess.check_output(["git", "rev-parse", "--git-path", "objects"], cwd=root, text=True).strip()
    alternates = destination / ".git" / "objects" / "info" / "alternates"
    alternates.parent.mkdir(parents=True, exist_ok=True)
    alternates.write_bytes((root / objects).resolve().as_posix().encode() + b"\n")
    subprocess.run(["git", "update-ref", "HEAD", SNAPSHOT], cwd=destination, check=True)
    subprocess.run(["git", "read-tree", SNAPSHOT], cwd=destination, check=True)
    env = os.environ.copy()
    if env.get("IVERILOG_BASE"):
        base = Path(env["IVERILOG_BASE"])
        if not base.is_absolute():
            base = root / base
        env["IVERILOG_BASE"] = os.path.relpath(base.resolve(), destination)
    if output is None:
        output = root / "build" / "generalization" / "legacy" / f"gate{gate}" / "result.json"
    output = Path(output).resolve()
    command = [sys.executable, "-m", "tools.generalization", "--gate", str(gate), "--output", str(output)]
    if synthesize:
        command.append("--synthesize")
    subprocess.run(command, cwd=destination, env=env, check=True)
    data = json.loads(output.read_text())
    if data["source_sha"] != SNAPSHOT:
        raise AssertionError("Historical fixture provenance is not the pinned snapshot")
    if gate == 2 and data["classification"] != "MOTIF_BYTE_EXCHANGE_PROTOCOL_SPECIFIC":
        raise AssertionError("Historical negative result changed")
    return data
