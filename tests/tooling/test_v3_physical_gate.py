"""Fixture-only closure decisions; these are not physical attempt evidence.

All measurements, identities and official-job metadata below are generated
test fixtures. The complete fixture uses the real extractor's output format
so integration mismatches cannot be hidden by manually inventing a status.
"""
from copy import deepcopy
import json

import pytest

from tools.v3_physical_gate import decision
from tools.v3_physical_metrics import EXPECTED_CORNERS, summarize

SOURCE = "f" * 40
RUN_ID = 711
NETLIST_HASH = "a" * 64
REQUIRED_ROUTED = (
    "runtime_protocol_configurations", "runtime_i2c_qualification",
    "runtime_microwire_qualification", "runtime_one_wire_training",
    "runtime_temporal_validation", "runtime_lin_unseen",
)
TIMING_FIELDS = (
    "setup_worst_slack_ns", "hold_worst_slack_ns", "setup_wns_ns",
    "hold_wns_ns", "setup_tns_ns", "hold_tns_ns",
)


@pytest.fixture
def complete(tmp_path):
    raw = {
        "route__drc_errors": 0, "magic__drc_error__count": 0,
        "design__lvs_error__count": 0,
        "antenna__violating__nets": 0, "antenna__violating__pins": 0,
        "route__antenna_violation__count": 0, "global_route__overflow": 0,
    }
    for corner in EXPECTED_CORNERS:
        for name, value in {"setup__ws": .5, "hold__ws": .1, "setup__wns": 0,
                            "hold__wns": 0, "setup__tns": 0, "hold__tns": 0}.items():
            raw["timing__" + name + "__corner:" + corner] = value
    directory = tmp_path / "fixture_only_official_flow_shape"
    (directory / "final").mkdir(parents=True)
    (directory / "final/metrics.json").write_text(json.dumps(raw), encoding="utf-8")
    jobs = {"jobs": [{"name": name, "status": "completed", "conclusion": "success",
                      "run_id": RUN_ID, "head_sha": SOURCE, "steps": []}
                     for name in ("gds", "precheck", "gl_test")]}
    metrics = summarize(directory, RUN_ID, SOURCE,
                        [{"id": 17, "name": "FIXTURE_ONLY_NOT_A_PHYSICAL_ARTIFACT", "archive_sha256_raw": "b" * 64}],
                        jobs, workflow_metadata={"id": RUN_ID, "head_sha": SOURCE, "status": "completed", "conclusion": "success"})
    correspondence = {
        "source_sha": SOURCE, "all_protected_source_bytes_equal": True,
        "files_sha256_raw": {"fixture_only/netlist.v": NETLIST_HASH},
    }
    routed = {"passed": True, "source_sha": SOURCE, "build_run_id": RUN_ID,
              "netlist_sha256_raw": NETLIST_HASH,
              "tests": [{"name": name, "passed": True} for name in REQUIRED_ROUTED]}
    return metrics, correspondence, routed


def assert_rejected(complete, reason):
    result = decision(*complete)
    assert result["physical_qualified"] is False
    assert any(reason in error for error in result["errors"]), result["errors"]


def test_complete_fixture_uses_actual_extractor_format_and_qualifies(complete):
    metrics, _, _ = complete
    assert metrics["extraction_scope"]["metrics_status"] == "final_metrics_available"
    result = decision(*complete)
    assert result["physical_qualified"] is True, result["errors"]
    assert result["errors"] == []


@pytest.mark.parametrize("status", [None, "no_metrics_available", "partial_unfinished_stage_metrics"])
def test_missing_or_partial_metrics_block_closure(complete, status):
    complete[0]["extraction_scope"]["metrics_status"] = status
    assert_rejected(complete, "Final identified physical metrics")


@pytest.mark.parametrize("job_name", ["gds", "precheck", "gl_test"])
@pytest.mark.parametrize("condition", ["missing", "in_progress", "failed"])
def test_each_official_job_must_be_completed_and_successful(complete, job_name, condition):
    jobs = complete[0]["jobs"]
    if condition == "missing":
        complete[0]["jobs"] = [job for job in jobs if job["name"] != job_name]
    else:
        job = next(job for job in jobs if job["name"] == job_name)
        if condition == "in_progress":
            job.update(status="in_progress", conclusion=None)
        else:
            job.update(status="completed", conclusion="failure")
    assert_rejected(complete, "Required official job unavailable/failed: " + job_name)


@pytest.mark.parametrize("status,conclusion", [(None, None), ("in_progress", None), ("completed", "failure")])
def test_workflow_itself_must_be_completed_and_successful(complete, status, conclusion):
    complete[0].update(workflow_status=status, workflow_conclusion=conclusion)
    assert_rejected(complete, "Official physical workflow")


@pytest.mark.parametrize("corner", EXPECTED_CORNERS)
def test_missing_expected_corner_blocks_closure(complete, corner):
    complete[0]["corners"].pop(corner)
    assert_rejected(complete, "Missing/negative timing result: " + corner)


@pytest.mark.parametrize("field", TIMING_FIELDS)
@pytest.mark.parametrize("value", [None, -.001, float("nan"), float("inf"), False])
def test_timing_requires_finite_nonnegative_numeric_values(complete, field, value):
    corner = EXPECTED_CORNERS[0]
    complete[0]["corners"][corner][field] = value
    assert_rejected(complete, "Missing/negative timing result: " + corner + "/" + field)


@pytest.mark.parametrize("field", ["setup_tns_ns", "hold_tns_ns"])
def test_positive_total_negative_slack_is_not_a_valid_closed_result(complete, field):
    corner = EXPECTED_CORNERS[0]
    complete[0]["corners"][corner][field] = .001
    assert_rejected(complete, "Missing/negative timing result: " + corner + "/" + field)


def test_negative_timing_in_an_extra_actual_corner_is_not_ignored(complete):
    values = deepcopy(complete[0]["corners"][EXPECTED_CORNERS[0]])
    values["hold_wns_ns"] = -.001
    complete[0]["corners"]["fixture_extra_corner"] = values
    assert_rejected(complete, "Missing/negative timing result: fixture_extra_corner/hold_wns_ns")


@pytest.mark.parametrize("field", ["detailed_route_drc", "magic_drc", "lvs_errors"])
@pytest.mark.parametrize("value", [None, 1, False, float("nan")])
def test_required_physical_error_counts_must_be_numeric_zero(complete, field, value):
    complete[0]["measurements"][field] = value
    assert_rejected(complete, "Missing/nonzero physical check: " + field)


@pytest.mark.parametrize("value", [None, 1, False, float("nan")])
def test_global_route_overflow_must_be_numeric_zero(complete, value):
    complete[0]["global_route"]["total_overflow"] = value
    assert_rejected(complete, "Global-route overflow")


@pytest.mark.parametrize("field", ["antenna_violating_nets", "antenna_violating_pins", "route_antenna_violations"])
@pytest.mark.parametrize("value", [1, False, float("nan")])
def test_reported_antenna_counts_must_be_numeric_zero(complete, field, value):
    complete[0]["measurements"][field] = value
    assert_rejected(complete, "antenna violations: " + field)


@pytest.mark.parametrize("condition", ["missing", "truncated", "duplicate", "failed", "not_passed"])
def test_complete_routed_roster_is_required(complete, condition):
    routed = complete[2]
    if condition == "missing":
        routed.pop("tests")
    elif condition == "truncated":
        routed["tests"].pop()
    elif condition == "duplicate":
        routed["tests"][-1] = deepcopy(routed["tests"][0])
    elif condition == "failed":
        routed["tests"][0]["passed"] = False
    else:
        routed["passed"] = False
    assert_rejected(complete, "Complete six-test routed functional receipt")


@pytest.mark.parametrize("condition", ["other_source", "missing_source", "not_equal", "missing_equality"])
def test_exact_source_correspondence_is_required(complete, condition):
    correspondence = complete[1]
    if condition == "other_source":
        correspondence["source_sha"] = "c" * 40
    elif condition == "missing_source":
        correspondence.pop("source_sha")
    elif condition == "not_equal":
        correspondence["all_protected_source_bytes_equal"] = False
    else:
        correspondence.pop("all_protected_source_bytes_equal")
    assert_rejected(complete, "Exact protected-source correspondence")


@pytest.mark.parametrize("condition", ["source", "run", "missing_source", "missing_run"])
def test_routed_tests_must_identify_same_build_run_and_source(complete, condition):
    routed = complete[2]
    if condition == "source":
        routed["source_sha"] = "c" * 40
    elif condition == "run":
        routed["build_run_id"] += 1
    elif condition == "missing_source":
        routed.pop("source_sha")
    else:
        routed.pop("build_run_id")
    assert_rejected(complete, "Routed tests identify another physical run/source")


@pytest.mark.parametrize("condition", ["other_hash", "missing_hash", "missing_binding"])
def test_routed_netlist_must_be_bound_by_physical_correspondence(complete, condition):
    if condition == "other_hash":
        complete[2]["netlist_sha256_raw"] = "d" * 64
    elif condition == "missing_hash":
        complete[2].pop("netlist_sha256_raw")
    else:
        complete[1].pop("files_sha256_raw")
    assert_rejected(complete, "Routed netlist is not bound")


@pytest.mark.parametrize("invalid_digest", [None, "not-a-sha256", "a" * 63])
def test_matching_invalid_netlist_digests_do_not_establish_artifact_identity(complete, invalid_digest):
    complete[2]["netlist_sha256_raw"] = invalid_digest
    complete[1]["files_sha256_raw"] = {"fixture_only/netlist.v": invalid_digest}
    assert_rejected(complete, "Routed netlist is not bound")
