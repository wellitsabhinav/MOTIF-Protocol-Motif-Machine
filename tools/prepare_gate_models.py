"""Prepare pinned PDK cells for zero-delay Icarus functional simulation.

Icarus does not drive delayed timing-check arguments from $setuphold/$recrem.
Connect those internal wires to their ports and remove specify blocks from
the functional copy. Keep the original license and UDP logic; the generated
copy stays in simulation output.
This adapter provides functional evidence only. Routed timing uses separate STA.
"""
import re
import sys
from pathlib import Path


def prepare(source, destination):
    text = Path(source).read_text(encoding="utf-8")
    def connect(match):
        names = re.findall(r"\bdelayed_([A-Za-z][A-Za-z0-9_]*)\b", match.group(0))
        return match.group(0) + "\n" + "\n".join(f"assign delayed_{name} = {name};" for name in names)
    text, count = re.subn(r"\bwire\s+delayed_[^;]+;", connect, text)
    if not count:
        raise ValueError("Pinned cell model has no delayed timing-check wires")
    text = re.sub(r"\bspecify\b.*?\bendspecify\b", "", text, flags=re.S)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    print(f"Prepared functional model: {count} delayed-wire groups")


if __name__ == "__main__":
    prepare(*sys.argv[1:])
