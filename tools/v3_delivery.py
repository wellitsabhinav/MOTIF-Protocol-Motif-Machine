"""Package validated demonstrations and their linked source/evidence as plain HTML."""
import argparse
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

from tools.unseen_receipt import validate
from tools.v3_inventory import verify, sha, MANIFEST

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL = "docs/demo/figures/physical/attempt_2"
ATTEMPTS = "experiments/temporal_qualification/physical"
DEMO_ROOTS = {"i2c", "microwire", "one_wire", "spi", "uart", "timed_stream", "unseen",
              "architecture", "historical", "comparison"}


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


def physical_gallery(destination, commit):
    """Validate and copy only committed, modest attempt-2 previews and receipts."""
    blobs = {}

    def blob(name):
        if name not in blobs:
            blobs[name] = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT)
        return blobs[name]

    def document(name):
        return json.loads(blob(name))

    def require(condition, message):
        if not condition:
            raise ValueError("Physical gallery: " + message)

    manifest_name = (MANIFEST if MANIFEST.is_absolute() else ROOT / MANIFEST).relative_to(ROOT).as_posix()
    manifest = document(manifest_name)
    frozen = sha(blob(manifest_name))
    preregistration = manifest["preregistration"]
    identity_name = PHYSICAL + "/identity.json"
    cost_name = PHYSICAL + "/physical_cost.json"
    timing_name = PHYSICAL + "/physical_timing.json"
    result_name = ATTEMPTS + "/attempt_2_result.json"
    metrics_name = ATTEMPTS + "/attempt_2_metrics.json"
    correspondence_name = ATTEMPTS + "/attempt_2_source_correspondence.json"
    selected = document(identity_name)
    cost, timing = document(cost_name), document(timing_name)
    result, metrics = document(result_name), document(metrics_name)
    correspondence = document(correspondence_name)
    identity = selected["identity"]
    source = identity.get("source_sha", "")
    run_id = selected.get("workflow_run_id")
    require(re.fullmatch(r"[0-9a-f]{40}", source) and identity.get("workflow_head_sha") == source,
            "exact selected workflow/source identity is absent")
    require(isinstance(run_id, int) and run_id > 0, "selected run identity is absent")
    require(identity.get("exact_rtl_correspondence") is True and correspondence.get("all_protected_source_bytes_equal") is True,
            "exact source correspondence is not recorded")
    require(identity.get("frozen_manifest_sha256_lf") == frozen, "selected source identifies a different freeze")
    expected_rtl = {name: value for name, value in manifest["source_hashes"].items()
                    if name.startswith("src/") and name.endswith(".sv")}
    require(identity.get("rtl_source_hashes_lf") == correspondence.get("rtl_source_hashes_lf") == expected_rtl,
            "selected/retained RTL correspondence differs from the freeze")
    for name, report in ((identity_name, selected), (cost_name, cost), (timing_name, timing),
                         (result_name, result), (correspondence_name, correspondence)):
        require(report.get("frozen_manifest_sha256_lf") == frozen and report.get("preregistration") == preregistration,
                "freeze/preregistration differs in " + name)
    for report in (cost, timing, result, metrics, correspondence):
        require(report.get("source_sha") == source, "retained report source differs from selected views")
    for report in (cost, timing, result, metrics):
        require(report.get("workflow_run_id") == run_id, "retained report run differs from selected views")
    require(correspondence.get("workflow_head_sha") == source, "retained workflow source differs")
    for report in (selected, cost, timing):
        require(report.get("presentation_status") == "UNQUALIFIED", "physical figure is not labeled UNQUALIFIED")
    require(result.get("physical_qualified") is False and result.get("workflow_conclusion") == "failure"
            and metrics.get("workflow_conclusion") == "failure", "attempt-2 failure is not retained")
    jobs = {job["name"]: job.get("conclusion") for job in metrics.get("jobs", [])}
    require(jobs.get("gds") == "failure" and jobs.get("precheck") == "skipped" and jobs.get("gl_test") == "skipped",
            "official failed/skipped job statuses differ")
    require(any(value.get("setup_wns_ns") is not None and value["setup_wns_ns"] < 0
                for value in metrics.get("corners", {}).values()), "failed setup timing is not retained")
    metrics_hash = hashlib.sha256(blob(metrics_name)).hexdigest()
    require(selected.get("metrics_receipt_sha256_raw") == cost.get("receipt_sha256_raw")
            == timing.get("receipt_sha256_raw") == metrics_hash and result.get("metrics_sha256_lf") == sha(blob(metrics_name)),
            "selected figures do not bind the retained metric receipt")
    correspondence_hash = hashlib.sha256(blob(correspondence_name)).hexdigest()
    require(identity.get("correspondence_receipt_sha256_raw") == correspondence_hash,
            "selected views do not bind the retained source/archive correspondence")
    require(metrics.get("source_correspondence") == correspondence, "metric/source correspondence differs")
    artifact = identity["artifact"]
    require(artifact == correspondence.get("artifact") and artifact.get("workflow_run_url", "").endswith("/" + str(run_id)),
            "selected archive/run correspondence differs")
    matches = [item for item in metrics.get("artifacts", []) if item.get("id") == artifact.get("id")]
    require(len(matches) == 1 and all(matches[0].get(key) == artifact.get(key) for key in ("id", "name", "archive_sha256_raw")),
            "metric archive identity differs from selected views")
    require(re.fullmatch(r"[0-9a-f]{64}", artifact.get("archive_sha256_raw", "")), "archive SHA-256 is absent")
    require(cost.get("measurement_values_original") == metrics.get("measurements")
            and cost.get("corners") == timing.get("corners") == metrics.get("corners"),
            "selected numeric/corner values differ from retained metrics")
    for record in cost.get("metrics", []):
        key = record["key"]
        value = metrics["global_route"].get("total_overflow") if key == "global_route_overflow" else metrics["measurements"].get(key)
        if key == "stdcell_utilization" and value is not None:
            value *= 100
        require(record.get("values", {}).get("v3") == value, "selected chart metric differs: " + key)
    for record in timing.get("metrics", []):
        require(record.get("values") == {corner: values.get(record["key"]) for corner, values in metrics["corners"].items()},
                "selected corner chart differs: " + record["key"])
    expected_images = {"floorplan.png", "floorplan.svg", "placement.png", "routing.png", "gds.png",
                       "physical_cost.png", "physical_cost.svg", "physical_timing.png", "physical_timing.svg"}
    images = {}
    for report in (selected, cost, timing):
        for name, expected in report.get("output_files_sha256_raw", {}).items():
            require(name in expected_images, "unexpected preview output: " + name)
            raw = blob(PHYSICAL + "/" + name)
            require(len(raw) <= 3_000_000 and hashlib.sha256(raw).hexdigest() == expected,
                    "committed preview size/hash differs: " + name)
            if name.endswith(".svg"):
                require(b"\r\n" not in raw, "committed SVG must retain exact LF bytes")
            require(name not in images or images[name] == expected, "conflicting preview output identity")
            images[name] = expected
    require(images.keys() == expected_images, "complete selected preview set is missing")
    require(set(selected.get("views", {})) == {"floorplan", "placement", "routing", "gds"}, "selected view scopes are incomplete")
    for view in selected["views"].values():
        require(view.get("status") == "available", "selected actual physical view is unavailable")
        for name, record in view.get("input_files", {}).items():
            require(record.get("sha256_raw") == correspondence["files_sha256_raw"].get(name),
                    "view geometry/image origin differs from archive correspondence")
    source_checks = (("docs/demo/select_physical_views.py", selected.get("selector_sha256_raw")),
                     ("docs/demo/render_physical_metrics.py", cost.get("renderer_sha256_raw")),
                     ("docs/demo/render_physical_metrics.py", timing.get("renderer_sha256_raw")),
                     ("docs/demo/render_cost.py", cost.get("shared_plotting_helper_sha256_raw")))
    for name, expected in source_checks:
        require(hashlib.sha256(blob(name)).hexdigest() == expected, "selected presentation source differs: " + name)
    later = document(ATTEMPTS + "/attempt_3_dispatch.json")
    intent_name = ATTEMPTS + "/attempt_3_intent.json"
    intent = document(intent_name)
    require(later.get("attempt") == intent.get("attempt") == intent.get("maximum_attempts") == 3
            and isinstance(later.get("run_id"), int) and later["run_id"] > 0
            and re.fullmatch(r"[0-9a-f]{40}", later.get("source_sha", "")),
            "separate final attempt/run/source identity is absent")
    require(later.get("source_sha") == intent.get("source_sha") and later.get("intent_sha256_lf") == sha(blob(intent_name)),
            "separate final dispatch/intent identity differs")
    for report in (later, intent):
        require(report.get("frozen_manifest_sha256_lf") == frozen and report.get("preregistration") == preregistration,
                "separate final dispatch identifies another frozen/preregistered scope")
    # Only selected committed figures and their retained receipts enter the
    # gallery; raw GDS/DEF/netlists and full generated route SVG stay outside.
    for name, raw in blobs.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    audit = {"schema_version": 3, "kind": "committed_source_specific_physical_gallery", "presentation_status": "UNQUALIFIED",
             "attempt": 2, "source_sha": source, "workflow_run_id": run_id, "artifact": artifact,
             "frozen_manifest_sha256_lf": frozen, "preregistration": preregistration,
             "receipt_checkout_commit": commit, "metric_receipt_sha256_raw": metrics_hash,
             "correspondence_receipt_sha256_raw": correspondence_hash,
             "selected_files_sha256_raw": {name: hashlib.sha256(raw).hexdigest() for name, raw in blobs.items()},
             "recorded_job_conclusions": jobs, "views": selected["views"],
             "separate_final_dispatch": {key: later[key] for key in ("attempt", "run_id", "source_sha", "workflow_url")},
             "qualification_claim": False}
    (destination / "physical_gallery.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8", newline="\n")
    return audit


def copy_demo_presentations(destination):
    for source in (ROOT / "build/demo").rglob("*"):
        relative = source.relative_to(ROOT / "build/demo")
        if len(relative.parts) == 1 and relative.name not in {"index.html", "result.json"}:
            continue
        if len(relative.parts) > 1 and relative.parts[0] not in DEMO_ROOTS:
            continue
        if (not source.is_file() or (source.suffix.lower() not in (".html", ".md", ".json", ".svg", ".png")
                                   and source.name != "simulation.log") or source.name == "elaborated.json"):
            continue
        target = destination / "build/demo" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def render_report(text, source_directory):
    """Render the report's headings, paragraphs, links and tables without dependencies."""
    def inline(value):
        tokens = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^\s)]+)\)|\*\*([^*]+)\*\*")
        rendered, cursor = [], 0
        for match in tokens.finditer(value):
            rendered.append(escape(value[cursor:match.start()]))
            code, label, target, strong = match.groups()
            if code is not None:
                rendered.append("<code>" + escape(code) + "</code>")
            elif label is not None:
                url = urlsplit(target)
                if not url.scheme and not url.netloc and url.path:
                    target = posixpath.normpath(source_directory + "/" + url.path)
                    if url.query:
                        target += "?" + url.query
                    if url.fragment:
                        target += "#" + url.fragment
                rendered.append(f"<a href='{escape(target, quote=True)}'>{escape(label)}</a>")
            else:
                rendered.append("<strong>" + escape(strong) + "</strong>")
            cursor = match.end()
        rendered.append(escape(value[cursor:]))
        return "".join(rendered)

    output, paragraph, table = [], [], []

    def flush():
        if paragraph:
            output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()
        if table:
            if len(table) < 2 or not all(re.fullmatch(r":?-+:?", value.strip()) for value in table[1]):
                raise ValueError("Report table has no valid Markdown separator")
            output.append("<div class='table'><table><thead><tr>" + "".join("<th>" + inline(value) + "</th>" for value in table[0]) + "</tr></thead><tbody>")
            for row in table[2:]:
                if len(row) != len(table[0]):
                    raise ValueError("Report table has inconsistent columns")
                output.append("<tr>" + "".join("<td>" + inline(value) + "</td>" for value in row) + "</tr>")
            output.append("</tbody></table></div>")
            table.clear()

    for line in text.splitlines():
        if not line.strip():
            flush()
        elif line.startswith("#"):
            flush()
            match = re.fullmatch(r"(#{1,6}) (.+)", line)
            if not match:
                raise ValueError("Unsupported report heading")
            level, title = len(match[1]), match[2]
            anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            output.append(f"<h{level} id='{anchor}'>" + inline(title) + f"</h{level}>")
        elif line.startswith("|"):
            if paragraph:
                flush()
            table.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        else:
            if table:
                flush()
            if line.startswith(("```", "- ", "> ")):
                raise ValueError("Unsupported report block; extend the presentation renderer explicitly")
            paragraph.append(line.strip())
    flush()
    return "\n".join(output)


def write_landing(destination, gallery):
    report_path = "docs/research/v3_temporal_qualification/final_report.md"
    report_text = (destination / report_path).read_text(encoding="utf-8")
    (destination / "report.html").write_text(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'><title>MOTIF A–Z report</title>"
        "<style>body{max-width:1180px;margin:35px auto;padding:0 22px;font:16px/1.5 system-ui;color:#243d45}"
        "a{color:#175d79}code{overflow-wrap:anywhere}h2{margin-top:2em}.table{overflow-x:auto}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #dbe4e4;padding:10px;text-align:left}</style>"
        "</head><body><nav><a href='index.html'>Evidence landing page</a> · "
        f"<a href='{report_path}'>Original Markdown report</a></nav><h1>MOTIF A–Z campaign report</h1>"
        "<p>This rendering retains the report's recorded statuses and evidence links. The original editable source is linked above.</p>"
        + render_report(report_text, str(Path(report_path).parent).replace("\\", "/"))
        + "</body></html>\n", encoding="utf-8", newline="\n")
    figure_names = (("floorplan", "Floorplan", gallery["views"]["floorplan"]["reason"]),
                    ("placement", "Placement", gallery["views"]["placement"]["reason"]),
                    ("routing", "Routing", gallery["views"]["routing"]["reason"]),
                    ("gds", "Official GDS image", "Actual official final PNG; presence of a GDS file does not establish physical closure."),
                    ("physical_cost", "Physical metrics", "Final metrics plus identified global-route overflow; missing metrics remain unavailable."),
                    ("physical_timing", "Corner timing", "Actual three-corner setup/hold WNS and TNS; this attempt failed setup timing."))
    cards = "".join(f"<figure><a href='{PHYSICAL}/{name}.png'><img loading='lazy' src='{PHYSICAL}/{name}.png' alt='{escape(title)} — unqualified attempt 2'></a><figcaption><strong>{escape(title)}</strong><p>{escape(scope)}</p></figcaption></figure>"
                    for name, title, scope in figure_names)
    later = gallery["separate_final_dispatch"]
    body = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>MOTIF evidence package</title><style>
body{{max-width:1180px;margin:40px auto;padding:0 24px;font:16px/1.55 system-ui,sans-serif;color:#243d45;background:#f8faf9}}
a{{color:#175d79}}h1{{font-size:2.3rem;line-height:1.15}}h2{{margin-top:2rem}}.nav,.gallery{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}}
.card,figure{{background:white;border:1px solid #dbe4e4;border-radius:10px;padding:22px;margin:0}}.card h2{{margin-top:0}}.status{{background:#fff0eb;border-left:5px solid #ac4939;padding:18px 22px}}
.status strong{{color:#9a3829}}img{{display:block;max-width:100%;height:auto;margin:auto}}figcaption p{{font-size:.9rem;color:#536a70}}code{{font-size:.85rem;overflow-wrap:anywhere}}
.identity{{font-size:.9rem;color:#536a70}}.links{{display:flex;gap:16px;flex-wrap:wrap}}footer{{margin:35px 0;font-size:.9rem;color:#536a70}}
@media(max-width:750px){{.nav,.gallery{{grid-template-columns:1fr}}body{{padding:0 16px}}h1{{font-size:1.9rem}}}}
</style></head><body><header><p>MOTIF · reproducible evidence</p><h1>Explore the validated demonstrations and recorded outcomes</h1>
<p>Eleven reached demonstrations pass their bounded model/RTL checks. Logical behavior, mapped cost and physical closure retain separate evidence and scopes.</p></header>
<nav class='nav' aria-label='Evidence entry points'><section class='card'><h2>Validated demonstrations</h2><p>Real RTL waveforms, ordered execution, configurations, source identities and case receipts.</p>
<a href='build/demo/index.html'>Open all eleven demonstrations</a> · <a href='build/demo/result.json'>Demo result and identities</a></section>
<section class='card'><h2>A–Z campaign report</h2><p>The retained engineering record explains the qualification gates, counterexamples, costs and physical outcomes.</p>
<a href='report.html'>Read the A–Z report</a> · <a href='{report_path}'>Original report source</a></section></nav>
<section aria-labelledby='physical-title'><h2 id='physical-title'>Physical attempt 2: identified real views</h2>
<div class='status'><strong>UNQUALIFIED — this source failed physical timing.</strong><p>The official GDS job failed. Official precheck and routed functional tests were skipped. Final layout availability is not physical closure.</p>
<p class='identity'>Run <code>{gallery['workflow_run_id']}</code> · source <code>{gallery['source_sha']}</code><br>Archive <code>{escape(gallery['artifact']['name'])} / {gallery['artifact']['id']}</code> · SHA-256 <code>{gallery['artifact']['archive_sha256_raw']}</code></p></div>
<p>These figures belong only to attempt 2. A separate final attempt 3 was dispatched as run <code>{later['run_id']}</code> at source <code>{later['source_sha']}</code>; the attempt-2 gallery establishes no outcome for that run.</p>
<p class='links'><a href='{ATTEMPTS}/attempt_2_result.json'>Retained failure result</a><a href='{ATTEMPTS}/attempt_2_metrics.json'>Actual metric receipt</a><a href='{ATTEMPTS}/attempt_2_source_correspondence.json'>Source/archive correspondence</a><a href='{ATTEMPTS}/attempt_3_dispatch.json'>Separate final dispatch</a><a href='physical_gallery.json'>Validated gallery identities</a></p>
<div class='gallery'>{cards}</div></section>
<footer><p>Frozen semantic boundary <code>{gallery['frozen_manifest_sha256_lf']}</code><br>Preregistration <code>{gallery['preregistration']['commit']}</code> · SHA-256 <code>{gallery['preregistration']['sha256_lf']}</code></p>
<p>This offline package contains selected modest previews. Full traces, mapped netlists, raw physical layouts and full route vectors remain separately identified artifacts.</p></footer></body></html>\n"""
    (destination / "index.html").write_text(body, encoding="utf-8", newline="\n")


def run(destination):
    before = verify()
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    public_receipt = ROOT / "experiments/temporal_qualification/unseen/logical_result.json"
    current_receipt = ROOT / "experiments/temporal_qualification/unseen/result.json"
    validate(json.loads(public_receipt.read_text()))
    validate(json.loads(current_receipt.read_text()), artifacts=True)
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
    # Simulator logs can differ across pinned reproduction environments. Keep
    # the public measured receipt and bind the current, fully validated one.
    shutil.copyfile(current_receipt, destination / current_receipt.relative_to(ROOT))
    # Complete raw traces remain in separately identified simulation artifacts.
    # Keep the browser package readable and include only presentation inputs.
    copy_demo_presentations(destination)
    gallery = physical_gallery(destination, source_commit)
    write_landing(destination, gallery)
    check_html(destination)
    if verify() != before:
        raise ValueError("Frozen semantic boundary changed during packaging")
    inventory = {path.relative_to(destination).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(destination.rglob("*")) if path.is_file()}
    receipt = {"schema_version": 3, "kind": "validated_plain_html_delivery", "passed": True,
               "source_commit": source_commit,
               "working_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
               "source_commit_role": "Checkout ancestry; the per-file manifest identifies the packaged bytes",
               "frozen_manifest_sha256_lf": sha(MANIFEST.read_bytes()), "demonstrations": rows,
               "public_unseen_receipt_sha256_lf": sha(public_receipt.read_bytes()),
               "current_unseen_receipt_sha256_lf": sha(current_receipt.read_bytes()),
               "physical_gallery": gallery,
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
