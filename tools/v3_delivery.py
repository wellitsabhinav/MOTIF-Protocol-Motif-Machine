"""Package validated demonstrations and their linked source/evidence as plain HTML."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

from tools.unseen_receipt import validate
from tools.v3_inventory import verify, sha, MANIFEST

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.targets.append(value)


def check_html(root):
    missing = []
    for page in root.rglob("*.html"):
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        for target in parser.targets:
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            path = (page.parent / unquote(url.path)).resolve()
            if not path.is_relative_to(root.resolve()) or not path.exists():
                missing.append(page.relative_to(root).as_posix() + " -> " + target)
    if missing:
        raise ValueError("Standalone HTML has missing/outside links: " + "; ".join(missing))


def run(destination):
    before = verify()
    validate(json.loads((ROOT / "experiments/temporal_qualification/unseen/logical_result.json").read_text()), artifacts=True)
    subprocess.run([sys.executable, "-m", "tools.demo", "--all", "--reuse"], cwd=ROOT, check=True)
    demo = json.loads((ROOT / "build/demo/result.json").read_text())
    expected = {("i2c", "bounded"), ("microwire", "bounded"), ("one_wire", "nominal"),
                ("one_wire", "interrupted_non_reset"), ("spi", "bounded"), ("uart", "bounded"),
                ("timed_stream", "bounded"), *(('unseen', name) for name in
                  ("nominal", "one_cycle_high_split", "pending_sync_recovery", "back_to_back"))}
    rows = demo.get("demonstrations", [])
    if (demo.get("passed") is not True or demo.get("failures") != [] or len(rows) != len(expected)
            or {(row["protocol"], row["case"]) for row in rows} != expected
            or not all(row.get("passed") is True for row in rows)):
        raise ValueError("All eleven reached, identified demonstrations must pass before packaging")
    destination = destination.resolve()
    destination.relative_to((ROOT / "build").resolve())
    if destination == (ROOT / "build").resolve() or destination.exists():
        raise ValueError("Choose a fresh dedicated directory below build/; existing delivery is preserved")
    destination.mkdir(parents=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, tracked):
        source = ROOT / name
        if source.is_file():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    # Complete raw traces remain in separately identified simulation artifacts.
    # Keep the browser package readable and include only presentation inputs.
    for source in (ROOT / "build/demo").rglob("*"):
        if (not source.is_file() or (source.suffix.lower() not in (".html", ".md", ".json", ".svg", ".png")
                                   and source.name != "simulation.log")
                or source.name == "elaborated.json"):
            continue
        target = destination / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (destination / "index.html").write_text(
        "<!doctype html><html lang='en'><meta charset='utf-8'><title>MOTIF evidence</title>"
        "<meta http-equiv='refresh' content='0;url=build/demo/index.html'>"
        "<a href='build/demo/index.html'>Open the validated MOTIF demonstrations and A–Z report</a></html>\n",
        encoding="utf-8", newline="\n")
    check_html(destination)
    if verify() != before:
        raise ValueError("Frozen semantic boundary changed during packaging")
    inventory = {path.relative_to(destination).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(destination.rglob("*")) if path.is_file()}
    receipt = {"schema_version": 3, "kind": "validated_plain_html_delivery", "passed": True,
               "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "working_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
               "source_commit_role": "Checkout ancestry; the per-file manifest identifies the packaged bytes",
               "frozen_manifest_sha256_lf": sha(MANIFEST.read_bytes()), "demonstrations": rows,
               "files_sha256_raw": inventory,
               "scope": "Source/evidence snapshot and actual validated presentation artifacts; full simulator traces/netlists/layouts are separate CI artifacts. Git history is required for pinned historical reproduction."}
    (destination / "delivery_manifest.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("PASS eleven demonstrations and standalone HTML links;", len(inventory), "identified files")
    print(destination / "index.html")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
