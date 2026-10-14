"""Physical extraction must preserve incompleteness and evidence identity."""
import json

import pytest

from tools.v3_physical_metrics import EXPECTED_CORNERS, summarize


SHA = "1" * 40
ARTIFACTS = [{"id": 7, "name": "fixture_only", "archive_sha256_raw": "2" * 64}]


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value), encoding="utf-8")
    return target


def extract(root, **kwargs):
    return summarize(root, 11, SHA, ARTIFACTS, {"jobs": []}, **kwargs)


def test_missing_metrics_and_jobs_cannot_become_zero_or_pass(tmp_path):
    report = extract(tmp_path)
    assert report["extraction_scope"]["metrics_status"] == "no_metrics_available"
    assert set(report["corners"]) == set(EXPECTED_CORNERS)
    assert all(value is None for value in report["measurements"].values())
    assert all(value is None for c in report["corners"].values() for value in c.values())
    assert report["global_route"]["total_overflow"] is None
    assert report["workflow_conclusion"] is None
    assert report["qualification"]["decision"] is None
    assert report["unavailable_reasons"]["measurements.magic_drc"] == "no_available_metric_source"


def test_last_numbered_stage_is_partial_and_pending_stage_is_identified(tmp_path):
    write(tmp_path, "9-stage/state_out.json", {"metrics": {"route__wirelength": 90}})
    write(tmp_path, "10-stage/state_out.json", {"metrics": {"route__wirelength": 100}})
    write(tmp_path, "11-stage/state_in.json", {"metrics": {"route__wirelength": 999}})
    report = extract(tmp_path)
    assert report["measurements"]["detailed_wirelength_um"] == 100
    assert report["extraction_scope"]["metrics_status"] == "partial_unfinished_stage_metrics"
    assert report["extraction_scope"]["metrics_source"] == "10-stage/state_out.json"
    assert report["stages"][-1]["status"] == "started_without_valid_state_out"
    assert report["stages"][-1]["verified_execution_conclusion"] is None
    assert report["input_files"]["10-stage/state_out.json"]["sha256_raw"]


def test_final_metrics_precede_stage_and_extra_corners_are_preserved(tmp_path):
    write(tmp_path, "55-openroad-stapostpnr/state_out.json", {"metrics": {"route__wirelength": 90}})
    write(tmp_path, "final/metrics.json", {
        "route__wirelength": 101,
        "timing__setup__ws__corner:extra_corner": -0.1,
        "timing__hold__wns__corner:nom_typ_1p20V_25C": 0,
    })
    report = extract(tmp_path)
    assert report["extraction_scope"]["metrics_status"] == "final_metrics_available"
    assert report["measurements"]["detailed_wirelength_um"] == 101
    assert report["corners"]["extra_corner"]["setup_worst_slack_ns"] == -0.1
    assert report["corners"]["nom_typ_1p20V_25C"]["hold_wns_ns"] == 0
    assert report["corners"]["nom_typ_1p20V_25C"]["setup_wns_ns"] is None
    assert report["qualification"]["decision"] is None


def test_nonfinite_invalid_and_absent_fields_remain_null(tmp_path):
    write(tmp_path, "final/metrics.json", {
        "route__wirelength": float("nan"),
        "route__vias": float("inf"),
        "design__instance__area__stdcell": "unknown",
        "route__drc_errors": True,
        "timing__setup__ws__corner:nom_fast_1p32V_m40C": float("-inf"),
    })
    report = extract(tmp_path)
    assert report["measurements"]["detailed_wirelength_um"] is None
    assert report["measurements"]["vias"] is None
    assert report["measurements"]["stdcell_area_um2"] is None
    assert report["measurements"]["detailed_route_drc"] is None
    assert report["corners"]["nom_fast_1p32V_m40C"]["setup_worst_slack_ns"] is None
    assert "nonfinite" in report["unavailable_reasons"]["measurements.vias"]
    json.dumps(report, allow_nan=False)


def test_drc_aliases_keep_distinct_tools_and_conflicts_unavailable(tmp_path):
    write(tmp_path, "final/metrics.json", {"route__drc_error__count": 3, "magic__drc_errors": 0})
    report = extract(tmp_path)
    assert report["measurements"]["detailed_route_drc"] == 3
    assert report["measurements"]["magic_drc"] == 0
    assert report["measurements"]["klayout_drc"] is None
    write(tmp_path, "final/metrics.json", {"route__drc_error__count": 3, "route__drc_errors": 0})
    report = extract(tmp_path)
    assert report["measurements"]["detailed_route_drc"] is None
    assert report["unavailable_reasons"]["measurements.detailed_route_drc"] == "conflicting_or_invalid_alias_values"


def test_timing_report_fallback_retains_actual_stage_and_does_not_hide_nan(tmp_path):
    corner = "nom_typ_1p20V_25C"
    write(tmp_path, "final/metrics.json", {"timing__setup__ws__corner:" + corner: float("nan")})
    directory = tmp_path / "31-openroad-stamidpnr" / corner
    directory.mkdir(parents=True)
    (directory / "ws.max.rpt").write_text(corner + ": 5.0\n", encoding="utf-8")
    (directory / "wns.min.rpt").write_text(corner + ": -0.25\n", encoding="utf-8")
    report = extract(tmp_path)
    assert report["corners"][corner]["setup_worst_slack_ns"] is None
    assert report["corners"][corner]["hold_wns_ns"] == -0.25
    assert report["extraction_scope"]["timing_report_stage"] == "31-openroad-stamidpnr"
    assert report["metric_sources"]["corners." + corner + ".hold_wns_ns"]["path"].endswith("wns.min.rpt")


def test_global_overflow_comes_from_real_final_congestion_table(tmp_path):
    directory = tmp_path / "39-openroad-globalrouting"
    directory.mkdir()
    (directory / "openroad-globalrouting.log").write_text(
        "Final congestion report:\nMetal2 100 30 30.00% 2 / 3 / 5\nTotal 200 50 25.00% 2 / 3 / 5\n", encoding="utf-8")
    report = extract(tmp_path)
    assert report["global_route"]["total_overflow"] == 5
    assert report["global_route"]["layers"]["Metal2"]["maximum_vertical_overflow"] == 3
    assert report["extraction_scope"]["metrics_status"] == "no_metrics_available"


def test_failed_jobs_are_retained_and_identity_mismatch_is_rejected(tmp_path):
    jobs = {"jobs": [{"id": 23, "name": "precheck", "run_id": 11, "head_sha": SHA, "status": "completed", "conclusion": "failure", "steps": []}]}
    report = summarize(tmp_path, 11, SHA, ARTIFACTS, jobs)
    assert report["jobs"][0]["conclusion"] == "failure"
    assert report["qualification"]["decision"] is None
    jobs["jobs"][0]["head_sha"] = "3" * 40
    with pytest.raises(ValueError, match="different workflow run/source"):
        summarize(tmp_path, 11, SHA, ARTIFACTS, jobs)


def test_malformed_final_metrics_uses_partial_state_and_records_problem(tmp_path):
    write(tmp_path, "10-stage/state_out.json", {"metrics": {"route__vias": 12}})
    path = tmp_path / "final/metrics.json"
    path.parent.mkdir()
    path.write_text("{interrupted", encoding="utf-8")
    report = extract(tmp_path)
    assert report["measurements"]["vias"] == 12
    assert report["extraction_scope"]["fallback_reason"] == "final_metrics_invalid"
    assert "final/metrics.json" in report["input_problems"]


def test_empty_final_metrics_are_not_labeled_as_final_measurements(tmp_path):
    write(tmp_path, "10-stage/state_out.json", {"metrics": {"route__vias": 12}})
    write(tmp_path, "final/metrics.json", {})
    report = extract(tmp_path)
    assert report["measurements"]["vias"] == 12
    assert report["extraction_scope"]["metrics_status"] == "partial_unfinished_stage_metrics"
    assert report["extraction_scope"]["fallback_reason"] == "final_metrics_empty"
