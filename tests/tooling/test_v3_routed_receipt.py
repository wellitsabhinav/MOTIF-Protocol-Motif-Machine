"""Synthetic receipt replay fixtures, never real physical qualification evidence."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

import tools.v3_routed_receipt as routed

SOURCE = "f" * 40
ORIGINAL_TESTS = (
    "runtime_protocol_configurations", "runtime_i2c_qualification",
    "runtime_microwire_qualification", "runtime_one_wire_training",
    "runtime_temporal_validation",
)
EVALUATION_PATHS = (
    "tools/lin_host_check.py", "test/lin_runtime.py", "tools/lin_unseen.py",
    "tools/lin_oracle.py", "experiments/temporal_qualification/unseen/config.json",
    "experiments/temporal_qualification/unseen/selected_workload.json",
)
QUALIFIED = "experiments/temporal_qualification/unseen/runtime_host_result.json"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def update_json(path, update):
    value = json.loads(path.read_text())
    update(value)
    write_json(path, value)


def xml(path, names, marker=None):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="FIXTURE_ONLY")
    for index, name in enumerate(names):
        test = ET.SubElement(suite, "testcase", name=name)
        if marker and index == 0:
            ET.SubElement(test, marker)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    # The hardcoded qualified-receipt path is isolated by changing cwd, rather
    # than intercepting Path.read_bytes or touching campaign receipts.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(routed, "verify", lambda: {"fixture_only": True})
    def preflight(source):
        if source != SOURCE:
            raise ValueError("Fixture source is not the qualified source")
        return {"fixture_only": True}
    monkeypatch.setattr(routed, "preflight", preflight)
    manifest = tmp_path / "fixture_only_manifest.json"
    manifest.write_text('{"fixture_only":true}\n', encoding="utf-8")
    monkeypatch.setattr(routed, "MANIFEST", manifest)
    inventory = {}
    for name in EVALUATION_PATHS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture-only evaluation source: " + name + "\n", encoding="utf-8")
        inventory[name] = routed.sha(path.read_bytes())
    write_json(tmp_path / QUALIFIED, {
        "schema_version": 3, "stage": "unseen-runtime-host", "passed": True,
        "frozen_manifest_sha256_lf": routed.sha(manifest.read_bytes()),
        "evaluation_source_hashes": inventory,
        "runtime_test_sha256_lf": inventory["test/lin_runtime.py"],
        "selected_cases": ["nominal", "one_cycle_high_split", "pending_sync_recovery", "back_to_back"],
        "tests": [{"name": "runtime_lin_unseen", "passed": True}],
        "frozen_before_after_identical": True, "evaluation_before_after_identical": True,
    })
    directory = tmp_path / "fixture_only_routed_artifact"
    netlist = directory / "tt_submission/fixture_only.nl.v"
    netlist.parent.mkdir(parents=True)
    netlist.write_text("module fixture_only; endmodule\n", encoding="utf-8")
    (directory / "compiled_netlist.v").write_bytes(netlist.read_bytes())
    write_json(directory / "workflow.json", {
        "id": 711, "head_sha": SOURCE, "status": "completed", "conclusion": "success",
        "path": ".github/workflows/gds.yml", "event": "workflow_dispatch", "run_attempt": 1,
        "repository": {"full_name": "wellitsabhinav/MOTIF-Protocol-Motif-Machine"},
    })
    write_json(directory / "netlist_identity.json", {
        "path": netlist.relative_to(directory).as_posix(),
        "sha256_raw": hashlib.sha256(netlist.read_bytes()).hexdigest(),
    })
    xml(directory / "original_results.xml", ORIGINAL_TESTS)
    xml(directory / "lin_results.xml", ["runtime_lin_unseen"])
    return directory


def test_complete_synthetic_replay_is_pure_and_binds_all_inputs(fixture):
    receipt = routed.read_receipt(fixture)
    assert receipt["passed"] is True
    assert receipt["source_sha"] == SOURCE
    assert receipt["build_run_id"] == 711
    assert len(receipt["tests"]) == 6
    assert set(receipt["evaluation_source_hashes"]) == set(EVALUATION_PATHS)
    assert set(receipt["input_sha256_raw"]) == {"workflow.json", "netlist_identity.json", "compiled_netlist.v", "original_results.xml", "lin_results.xml"}
    assert not (fixture / "result.json").exists()


def test_run_writes_only_the_replayed_fixture_receipt(fixture):
    receipt = routed.run(fixture)
    assert json.loads((fixture / "result.json").read_text()) == receipt


@pytest.mark.parametrize("filename,names", [
    ("original_results.xml", ORIGINAL_TESTS), ("lin_results.xml", ("runtime_lin_unseen",)),
])
@pytest.mark.parametrize("condition", ["omitted", "duplicate", "skipped", "error", "failure"])
def test_incomplete_duplicate_or_failed_xml_is_rejected(fixture, filename, names, condition):
    if condition == "omitted":
        xml(fixture / filename, names[:-1])
    elif condition == "duplicate":
        xml(fixture / filename, [*names, names[0]])
    else:
        xml(fixture / filename, names, condition)
    with pytest.raises(ValueError, match="roster|failed/skipped"):
        routed.read_receipt(fixture)


def test_changed_netlist_bytes_are_rejected(fixture):
    identity = json.loads((fixture / "netlist_identity.json").read_text())
    (fixture / identity["path"]).write_text("module altered_fixture; endmodule\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Routed netlist changed"):
        routed.read_receipt(fixture)


def test_compiled_netlist_must_equal_identified_downloaded_netlist(fixture):
    (fixture / "compiled_netlist.v").write_text("module different_compilation_fixture; endmodule\n", encoding="utf-8")
    with pytest.raises(ValueError, match="netlist actually compiled differs"):
        routed.read_receipt(fixture)


def test_missing_compiled_netlist_cannot_authorize_replay(fixture):
    (fixture / "compiled_netlist.v").unlink()
    with pytest.raises(OSError):
        routed.read_receipt(fixture)


@pytest.mark.parametrize("value", [None, False, "not-a-sha256", "a" * 63, "A" * 64])
def test_invalid_netlist_digest_is_rejected(fixture, value):
    update_json(fixture / "netlist_identity.json", lambda data: data.update(sha256_raw=value))
    with pytest.raises(ValueError, match="SHA-256"):
        routed.read_receipt(fixture)


@pytest.mark.parametrize("field,value", [
    ("id", None), ("id", 0), ("id", -1), ("id", True), ("id", "711"),
    ("status", "in_progress"), ("status", None), ("conclusion", "failure"),
    ("conclusion", None), ("path", ".github/workflows/ci.yml"), ("path", None),
])
def test_wrong_official_workflow_identity_or_state_is_rejected(fixture, field, value):
    update_json(fixture / "workflow.json", lambda data: data.update({field: value}))
    with pytest.raises(ValueError, match="successful official physical workflow"):
        routed.read_receipt(fixture)


def test_unqualified_workflow_source_is_rejected_by_preflight(fixture):
    update_json(fixture / "workflow.json", lambda data: data.update(head_sha="e" * 40))
    with pytest.raises(ValueError, match="qualified source"):
        routed.read_receipt(fixture)


@pytest.mark.parametrize("path", EVALUATION_PATHS)
def test_stale_qualified_configuration_stimulus_or_oracle_bytes_are_rejected(fixture, path):
    Path(path).write_text("altered fixture evaluation bytes\n", encoding="utf-8")
    with pytest.raises(ValueError, match="qualified runtime subset"):
        routed.read_receipt(fixture)


@pytest.mark.parametrize("field", ["passed", "frozen_before_after_identical", "evaluation_before_after_identical"])
def test_failed_runtime_qualification_cannot_authorize_routed_replay(fixture, field):
    update_json(Path(QUALIFIED), lambda data: data.update({field: False}))
    with pytest.raises(ValueError, match="qualified|qualification|runtime|evaluation"):
        routed.read_receipt(fixture)


@pytest.mark.parametrize("condition", ["empty", "omitted_source"])
def test_incomplete_qualified_source_inventory_is_rejected(fixture, condition):
    def mutate(data):
        if condition == "empty":
            data["evaluation_source_hashes"] = {}
        else:
            data["evaluation_source_hashes"].pop("test/lin_runtime.py")
    update_json(Path(QUALIFIED), mutate)
    with pytest.raises(ValueError, match="qualified|qualification|runtime|evaluation"):
        routed.read_receipt(fixture)


@pytest.mark.parametrize("absolute", [False, True])
def test_netlist_path_cannot_escape_its_identified_directory(fixture, absolute):
    outside = fixture.parent / "outside_fixture_only.nl.v"
    outside.write_text("module fixture_only; endmodule\n", encoding="utf-8")
    update_json(fixture / "netlist_identity.json", lambda data: data.update(
        path=str(outside) if absolute else "../outside_fixture_only.nl.v",
        sha256_raw=hashlib.sha256(outside.read_bytes()).hexdigest()))
    with pytest.raises(ValueError):
        routed.read_receipt(fixture)
