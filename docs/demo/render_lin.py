"""Focused plots from the identified complete frozen-v3 LIN RTL evidence."""
import json
from pathlib import Path

from tools.demo_render import waveform
from tools.unseen_receipt import validate
from tools.v3_inventory import verify, sha, MANIFEST


def main():
    before = verify()
    receipt = validate(json.loads(Path("experiments/temporal_qualification/unseen/logical_result.json").read_text()))
    outputs = []
    for name, window in (("one_cycle_high_split", (34995, 35012)), ("nominal", (79248, 79265))):
        case = next(case for case in receipt["cases"] if case["name"] == name)
        trace = Path(case["trace_directory"]) / "rtl.jsonl"
        if sha(trace.read_bytes()) != case["evidence_sha256_lf"]["rtl.jsonl"]:
            raise RuntimeError("Identified RTL trace changed")
        rows = [json.loads(line) for line in trace.read_text().splitlines()]
        directory = Path("build/demo/unseen") / name
        waveform(rows, directory, "Frozen v3 LIN " + name + " / core observations", [("LIN RX", 2)],
                 window=window, outputs=(3,), annotations={"rx_pin": 2})
        outputs.append({"case": name, "window_core_cycles": window,
                        "rtl_trace_sha256_lf": case["evidence_sha256_lf"]["rtl.jsonl"],
                        "artifacts": {path.name: sha(path.read_bytes()) for path in directory.glob(f"waveform_{window[0]}_{window[1]}.*")},
                        "observations": [{"cycle": index, **rows[index]} for index in range(*window)]})
    path = Path("build/demo/unseen/focused_views.json")
    path.write_text(json.dumps({"frozen_manifest_sha256_lf": sha(MANIFEST.read_bytes()), "views": outputs}, indent=2) + "\n")
    if verify() != before:
        raise RuntimeError("Rendering changed the frozen boundary")
    print("PASS identified LIN interruption and acceptance zooms")


if __name__ == "__main__":
    main()
