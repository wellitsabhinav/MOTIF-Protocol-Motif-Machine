"""A passing partial or duplicated receipt must never unlock the freeze gate."""
import pytest

from tools.v3_inventory import expected_temporal_names, validate_gate


def temporal_receipt():
    cases = [{"name": name, "model_rtl_agreement": True, "oracle": {"passed": True}}
             for name in sorted(expected_temporal_names())]
    return {"stage": "temporal", "passed": True, "cases": cases, "total_compared_cycles": len(cases)}


def test_duplicate_cannot_replace_timer_boundary_counterexample():
    receipt = temporal_receipt()
    validate_gate("temporal", receipt)
    index = next(i for i, case in enumerate(receipt["cases"]) if case["name"] == "registered_timer_end_precedes_repeated_acquisition")
    receipt["cases"][index] = receipt["cases"][0]
    with pytest.raises(ValueError, match="unique case set"):
        validate_gate("temporal", receipt)


def test_passing_partial_temporal_receipt_cannot_unlock_freeze():
    receipt = temporal_receipt()
    receipt["cases"] = receipt["cases"][:1]
    with pytest.raises(ValueError, match="unique case set"):
        validate_gate("temporal", receipt)


def test_model_only_receipt_cannot_unlock_rtl_gate():
    receipt = temporal_receipt()
    receipt["model_only"] = True
    with pytest.raises(ValueError, match="complete passing gate"):
        validate_gate("temporal", receipt)
