"""Synthetic ZIP/ledger fixtures; these are never physical campaign evidence."""
import hashlib
import json
from pathlib import Path
import stat
import warnings
import zipfile

import pytest

import tools.v3_physical as physical

SOURCE = "f" * 40
REVISION = "e" * 40
RUN_ID = 711
RTL = b"module fixture_only; endmodule\n"


def raw_hash(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def mutate_json(path, update):
    data = json.loads(path.read_text())
    update(data)
    write_json(path, data)


@pytest.fixture
def environment(tmp_path, monkeypatch):
    ledger = tmp_path / "fixture_only_ledger"
    ledger.mkdir()
    monkeypatch.setattr(physical, "DIRECTORY", ledger)
    def committed(source, path):
        if source not in (SOURCE, REVISION):
            raise ValueError("Unknown fixture-only commit")
        if path == "src/config.json":
            return json.dumps({"CLOCK_PERIOD": 20, "PL_TARGET_DENSITY_PCT": 60 if source == SOURCE else 61}).encode()
        return ("fixture-only pinned physical input " + path).encode()
    monkeypatch.setattr(physical, "committed", committed)
    def preflight(source):
        return {"schema_version": 3, "source_sha": source,
                "frozen_manifest_sha256_lf": "c" * 64,
                "preregistration": {"commit": "d" * 40, "sha256_lf": "d" * 64},
                "all_protected_source_bytes_equal": True,
                "rtl_source_hashes_lf": {"src/fixture_core.sv": physical.sha(RTL)},
                "physical_input_hashes_lf": {path: physical.sha(committed(source, path)) for path in physical.INPUTS}}
    monkeypatch.setattr(physical, "preflight", preflight)
    baseline = preflight(SOURCE)
    monkeypatch.setattr(physical, "verify", lambda: {"physical_input_hashes": baseline["physical_input_hashes_lf"]})
    return {"root": tmp_path, "ledger": ledger, "baseline": baseline}


@pytest.fixture
def bundle(environment):
    root = environment["root"]
    extracted = root / "fixture_only_extracted"
    extracted.mkdir()
    files = {"src/fixture_core.sv": RTL, "runs/wokwi/final/metrics.json": b'{"fixture_only":true}\n'}
    archive, metadata = root / "fixture_only.zip", root / "fixture_only_artifact.json"
    def rebuild(extra=(), file_map=None):
        members = files if file_map is None else file_map
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "w") as zip_out:
                for name, value in members.items():
                    zip_out.writestr(name, value)
                for name, value in extra:
                    if isinstance(name, str) and "\\" in name:
                        # ZipInfo normally normalizes Windows separators at
                        # construction. Preserve the actual unsafe ZIP header
                        # to test the raw-name rejection on every platform.
                        entry = zipfile.ZipInfo("fixture_raw_member")
                        entry.filename = entry.orig_filename = name
                        name = entry
                    zip_out.writestr(name, value)
        write_json(metadata, {"id": 817, "name": "FIXTURE_ONLY_NOT_A_PHYSICAL_ARTIFACT",
                              "digest": "sha256:" + raw_hash(archive.read_bytes()),
                              "local_archive_path": str(archive),
                              "workflow_run": {"id": RUN_ID, "head_sha": SOURCE}})
    rebuild()
    for name, value in files.items():
        path = extracted / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return {"archive": archive, "metadata": metadata, "extracted": extracted,
            "files": files, "rebuild": rebuild}


def correspondence(bundle):
    return physical.correspondence_data(SOURCE, RUN_ID, bundle["metadata"], bundle["extracted"])


def test_exact_synthetic_archive_and_bundled_source_identity(bundle):
    result = correspondence(bundle)
    assert result["source"]["role"] == "bundled_workflow_sources"
    assert result["files_sha256_raw"] == {name: raw_hash(value) for name, value in bundle["files"].items()}
    assert result["artifact"]["archive_sha256_raw"] == raw_hash(bundle["archive"].read_bytes())


@pytest.mark.parametrize("condition", ["wrong_digest", "changed_archive"])
def test_zip_raw_digest_must_match_published_identity(bundle, condition):
    if condition == "wrong_digest":
        mutate_json(bundle["metadata"], lambda value: value.update(digest="sha256:" + "0" * 64))
    else:
        with bundle["archive"].open("ab") as output:
            output.write(b"fixture-only unexpected suffix")
    with pytest.raises(ValueError, match="published ZIP digest"):
        correspondence(bundle)


@pytest.mark.parametrize("condition", ["modified", "missing", "added"])
def test_extracted_inventory_must_equal_archive_members_exactly(bundle, condition):
    path = bundle["extracted"] / "runs/wokwi/final/metrics.json"
    if condition == "modified":
        path.write_bytes(b"changed fixture bytes")
    elif condition == "missing":
        path.unlink()
    else:
        (bundle["extracted"] / "unpublished_fixture.txt").write_bytes(b"not in ZIP")
    with pytest.raises(ValueError, match="Extracted physical inventory differs"):
        correspondence(bundle)


def test_duplicate_zip_member_is_rejected(bundle):
    bundle["rebuild"](extra=[("src/fixture_core.sv", RTL)])
    with pytest.raises(ValueError, match="duplicate member"):
        correspondence(bundle)


@pytest.mark.parametrize("name", ["../outside.txt", "/absolute.txt", "nested\\file.txt", "D:ads.txt", "nested/../../outside.txt"])
def test_unsafe_zip_paths_are_rejected_without_extracting_them(bundle, name):
    bundle["rebuild"](extra=[(name, b"fixture-only unsafe path")])
    if name == "nested\\file.txt":
        # A Windows extractor would normalize this safe in-fixture destination.
        # Identity must still reject the original backslash-bearing member.
        target = bundle["extracted"] / "nested/file.txt"
        target.parent.mkdir()
        target.write_bytes(b"fixture-only unsafe path")
    with pytest.raises(ValueError, match="unsafe member"):
        correspondence(bundle)


def test_zip_symlink_member_is_rejected_without_creating_a_link(bundle):
    link = zipfile.ZipInfo("fixture_symlink")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    bundle["rebuild"](extra=[(link, b"src/fixture_core.sv")])
    with pytest.raises(ValueError, match="unsafe member"):
        correspondence(bundle)


def test_nested_added_bundled_rtl_is_not_ignored(bundle):
    extra = "src/nested/added_fixture.sv"
    data = b"module added_fixture; endmodule\n"
    bundle["rebuild"](extra=[(extra, data)])
    path = bundle["extracted"] / extra
    path.parent.mkdir()
    path.write_bytes(data)
    with pytest.raises(ValueError, match="Bundled workflow RTL differs"):
        correspondence(bundle)


@pytest.mark.parametrize("field,value", [("id", RUN_ID + 1), ("head_sha", REVISION)])
def test_archive_metadata_must_identify_same_run_and_source(bundle, field, value):
    mutate_json(bundle["metadata"], lambda data: data["workflow_run"].update({field: value}))
    with pytest.raises(ValueError, match="different workflow run/source"):
        correspondence(bundle)


@pytest.fixture
def failed_attempt(environment):
    root, ledger = environment["root"], environment["ledger"]
    write_json(ledger / "attempt_1_intent.json", environment["baseline"] | {"attempt": 1})
    write_json(ledger / "attempt_1_dispatch.json", {"run_id": RUN_ID, "source_sha": SOURCE})
    workflow, jobs, artifacts = root / "fixture_workflow.json", root / "fixture_jobs.json", root / "fixture_artifacts.json"
    write_json(workflow, {"id": RUN_ID, "head_sha": SOURCE, "status": "completed", "conclusion": "failure",
                          "path": ".github/workflows/gds.yml", "run_attempt": 1,
                          "html_url": "https://github.com/fixture/fixture/actions/runs/711"})
    write_json(jobs, {"jobs": [{"name": "gds", "status": "completed", "conclusion": "failure", "run_id": RUN_ID}]})
    write_json(artifacts, {"artifacts": []})
    return environment | {"workflow": workflow, "jobs": jobs, "artifacts": artifacts}


def failure(fixture):
    return physical.record_failure(1, fixture["workflow"], fixture["jobs"], fixture["artifacts"])


def test_terminal_status_only_failure_records_unavailable_measurements(failed_attempt):
    result = failure(failed_attempt)
    assert result["physical_qualified"] is False
    assert result["workflow_status"] == "completed"
    assert result["measurements"] is None and result["corners"] is None
    assert set(result["metadata_sha256_raw"]) == {"workflow", "jobs", "artifacts"}
    assert json.loads((failed_attempt["ledger"] / "attempt_1_result.json").read_text()) == result


@pytest.mark.parametrize("field,value", [
    ("status", "in_progress"), ("status", "queued"), ("conclusion", "success"),
    ("id", RUN_ID + 1), ("head_sha", REVISION), ("path", ".github/workflows/ci.yml"), ("run_attempt", 2),
])
def test_status_only_failure_refuses_unfinished_or_different_dispatch(failed_attempt, field, value):
    mutate_json(failed_attempt["workflow"], lambda data: data.update({field: value}))
    with pytest.raises(ValueError, match="completed unsuccessful identified physical dispatch"):
        failure(failed_attempt)


@pytest.mark.parametrize("name", ["GDS_logs", "tt_submission"])
def test_status_only_failure_refuses_published_physical_archives(failed_attempt, name):
    write_json(failed_attempt["artifacts"], {"artifacts": [{"id": 817, "name": name}]})
    with pytest.raises(ValueError, match="require normal artifact/partial-metric extraction"):
        failure(failed_attempt)


@pytest.mark.parametrize("condition", ["unfinished_job", "successful_job", "wrong_run"])
def test_status_only_failure_requires_terminal_required_job_on_same_run(failed_attempt, condition):
    def mutate(data):
        job = data["jobs"][0]
        if condition == "unfinished_job":
            job.update(status="in_progress", conclusion=None)
        elif condition == "successful_job":
            job.update(conclusion="success")
        else:
            job.update(run_id=RUN_ID + 1)
    mutate_json(failed_attempt["jobs"], mutate)
    with pytest.raises(ValueError, match="terminal required-job failure"):
        failure(failed_attempt)


@pytest.fixture
def revision(failed_attempt):
    failure(failed_attempt)
    diagnosis = failed_attempt["root"] / "fixture_diagnosis.json"
    write_json(diagnosis, {"previous_attempt": 1, "failure": "fixture-only terminal placement failure",
                           "permitted_setting_changes": [{"setting": "PL_TARGET_DENSITY_PCT", "before": 60, "after": 61}]})
    return failed_attempt | {"diagnosis": diagnosis}


def test_next_intent_accepts_completed_bound_failure_and_diagnosed_revision(revision):
    result = physical.intent(REVISION, revision["diagnosis"])
    assert result["attempt"] == 2 and result["flow_setting_revision"] == 1
    assert result["semantic_changes"] is False
    assert result["physical_input_hashes_lf"]["src/config.json"] != revision["baseline"]["physical_input_hashes_lf"]["src/config.json"]


@pytest.mark.parametrize("field,value", [("workflow_status", "in_progress"), ("workflow_run_id", RUN_ID + 1), ("source_sha", REVISION)])
def test_next_intent_refuses_unfinished_or_mismatched_previous_failure(revision, field, value):
    mutate_json(revision["ledger"] / "attempt_1_result.json", lambda data: data.update({field: value}))
    with pytest.raises(ValueError, match="completed failure evidence bound"):
        physical.intent(REVISION, revision["diagnosis"])


def test_next_intent_requires_actual_setting_change(revision):
    with pytest.raises(ValueError, match="implement the diagnosed setting revision"):
        physical.intent(SOURCE, revision["diagnosis"])


@pytest.mark.parametrize("changes", [
    [{"setting": "PL_TARGET_DENSITY_PCT", "before": 59, "after": 61}],
    [{"setting": "PL_TARGET_DENSITY_PCT", "before": 60, "after": 62}],
    [{"setting": "OPENROAD_THREADS", "before": None, "after": 4}],
    [{"setting": "PL_TARGET_DENSITY_PCT", "before": 60, "after": 61},
     {"setting": "OPENROAD_THREADS", "before": None, "after": 4}],
    [{"setting": "PL_TARGET_DENSITY_PCT", "before": 60, "after": 61}] * 2,
])
def test_next_intent_refuses_undeclared_or_misstated_setting_changes(revision, changes):
    mutate_json(revision["diagnosis"], lambda data: data.update(permitted_setting_changes=changes))
    with pytest.raises(ValueError, match="Actual flow setting changes differ"):
        physical.intent(REVISION, revision["diagnosis"])


@pytest.mark.parametrize("changes", ["PL_TARGET_DENSITY_PCT", ["PL_TARGET_DENSITY_PCT"], [{"setting": "PL_TARGET_DENSITY_PCT"}]])
def test_next_intent_requires_structured_before_after_setting_changes(revision, changes):
    mutate_json(revision["diagnosis"], lambda data: data.update(permitted_setting_changes=changes))
    with pytest.raises(ValueError, match="enumerate setting names and before/after values"):
        physical.intent(REVISION, revision["diagnosis"])


def test_attempt_cap_refuses_a_fourth_intent(environment):
    for number in range(1, 4):
        write_json(environment["ledger"] / f"attempt_{number}_intent.json", environment["baseline"])
    with pytest.raises(ValueError, match="initial attempt plus two diagnosed revisions is exhausted"):
        physical.intent(REVISION)


def test_initial_intent_retains_original_physical_inputs(environment):
    result = physical.intent(SOURCE)
    assert result["attempt"] == 1 and result["flow_setting_revision"] == 0
    assert result["physical_input_hashes_lf"] == environment["baseline"]["physical_input_hashes_lf"]


def test_initial_intent_refuses_preemptive_flow_setting_revision(environment):
    with pytest.raises(ValueError, match="Initial attempt must retain"):
        physical.intent(REVISION)
